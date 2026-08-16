"""Daily compound interest — lazy accrual on account/loan touch.

APR semantics: savings 6.7% means 6.7% per year, compounded daily
(daily rate = apr/365). Whole 24h periods only; sub-day remainder is kept.
Between two touches the balance is constant, so applying n whole days at once
with (1+r)^n is exactly equal to n daily applications.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..db import utcnow
from ..models import Account, Loan
from . import ledger, settings as settings_svc


def daily_rate(apr_percent: float) -> float:
    return apr_percent / 100.0 / 365.0


def compound_interest_cents(principal_cents: int, apr_percent: float, days: int) -> int:
    if principal_cents <= 0 or days <= 0:
        return 0
    factor = (1.0 + daily_rate(apr_percent)) ** days
    return int(principal_cents * (factor - 1.0))  # floor for positives


def next_day_interest_cents(principal_cents: int, apr_percent: float) -> int:
    return compound_interest_cents(principal_cents, apr_percent, 1)


def whole_days_elapsed(cursor: datetime, now: datetime) -> int:
    return max(0, int((now - cursor).total_seconds()) // 86400)


def accrue_savings(db: Session, account: Account, now: datetime | None = None) -> int:
    """Settle whole elapsed days of savings interest; returns cents granted."""
    now = now or utcnow()
    if not settings_svc.get(db, "interest_enabled"):
        account.last_interest_at = now
        return 0
    days = whole_days_elapsed(account.last_interest_at, now)
    if days <= 0:
        return 0
    apr = float(settings_svc.get(db, "savings_apr_percent"))
    granted = compound_interest_cents(account.money_cents, apr, days)
    account.last_interest_at = account.last_interest_at + timedelta(days=days)
    if granted > 0:
        ledger.append_tx(
            db,
            account,
            "money",
            "interest",
            granted,
            note=f"Interest for {days} day{'s' if days > 1 else ''} 🌱",
            created_by=None,
            meta={"apr_percent": apr, "days": days},
        )
    return granted


def accrue_loan(db: Session, loan: Loan, now: datetime | None = None) -> int:
    """Settle whole elapsed days of loan interest into outstanding; returns cents added."""
    now = now or utcnow()
    if loan.status != "active":
        return 0
    days = whole_days_elapsed(loan.last_accrual_at, now)
    if days <= 0:
        return 0
    added = compound_interest_cents(loan.outstanding_cents, loan.apr_percent, days)
    loan.last_accrual_at = loan.last_accrual_at + timedelta(days=days)
    if added > 0:
        loan.outstanding_cents += added
        ledger.append_tx(
            db,
            loan.account,
            "debt",
            "loan_interest",
            added,
            note=f"Loan #{loan.id} interest for {days} day{'s' if days > 1 else ''}",
            created_by=None,
            meta={"loan_id": loan.id, "apr_percent": loan.apr_percent, "days": days},
            balance_after=loan.outstanding_cents,
        )
    return added
