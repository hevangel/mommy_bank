"""Borrowing: loans with per-loan APR captured at borrow time, lazy interest."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..db import utcnow
from ..models import Account, Loan, User
from . import interest, ledger, settings as settings_svc
from .settings import BankError


def total_outstanding(db: Session, account: Account, now=None) -> int:
    now = now or utcnow()
    total = 0
    for loan in db.query(Loan).filter(Loan.account_id == account.id, Loan.status == "active").all():
        interest.accrue_loan(db, loan, now)
        total += loan.outstanding_cents
    return total


def borrow(db: Session, account: Account, amount_cents: int, actor: User, now=None) -> Loan:
    now = now or utcnow()
    if amount_cents <= 0:
        raise BankError("Amount must be positive")
    if not settings_svc.get(db, "borrow_enabled"):
        raise BankError("Borrowing is disabled by the bank")
    if not actor.is_admin and not account.user.can_borrow:
        raise BankError("You are not allowed to borrow")
    limit = int(settings_svc.get(db, "borrow_limit_cents"))
    outstanding = total_outstanding(db, account, now)
    if outstanding + amount_cents > limit:
        raise BankError(
            f"Borrowing would exceed the debt cap "
            f"({outstanding + amount_cents} > {limit} cents outstanding)"
        )
    apr = float(settings_svc.get(db, "borrow_apr_percent"))
    loan = Loan(
        account_id=account.id,
        principal_cents=amount_cents,
        outstanding_cents=amount_cents,
        apr_percent=apr,
        last_accrual_at=now,
    )
    db.add(loan)
    db.flush()
    ledger.append_tx(
        db, account, "money", "borrow", amount_cents,
        note=f"Loan #{loan.id} received", created_by=actor.id, meta={"loan_id": loan.id},
    )
    ledger.append_tx(
        db, account, "debt", "borrow", amount_cents,
        note=f"Loan #{loan.id} opened", created_by=actor.id,
        meta={"loan_id": loan.id, "apr_percent": apr}, balance_after=loan.outstanding_cents,
    )
    return loan


def repay(db: Session, loan: Loan, amount_cents: int, actor: User, now=None) -> int:
    """Repay up to min(requested, outstanding, available money). Returns cents repaid."""
    now = now or utcnow()
    if amount_cents <= 0:
        raise BankError("Amount must be positive")
    if loan.status != "active":
        raise BankError("Loan is already repaid")
    interest.accrue_loan(db, loan, now)
    account = loan.account
    effective = min(amount_cents, loan.outstanding_cents, account.money_cents)
    if effective <= 0:
        raise BankError("Nothing to repay (no outstanding debt or no money available)")
    loan.outstanding_cents -= effective
    ledger.append_tx(
        db, account, "money", "repay", -effective,
        note=f"Repay loan #{loan.id}", created_by=actor.id, meta={"loan_id": loan.id},
    )
    ledger.append_tx(
        db, account, "debt", "repay", -effective,
        note=f"Repay loan #{loan.id}", created_by=actor.id,
        meta={"loan_id": loan.id}, balance_after=loan.outstanding_cents,
    )
    if loan.outstanding_cents == 0:
        loan.status = "repaid"
        loan.repaid_at = now
    return effective
