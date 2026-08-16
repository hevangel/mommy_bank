"""Account operations: deposits, withdrawals, screen-time grants, conversion."""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..db import utcnow
from ..models import Account, Loan, User
from . import exchange, interest, ledger, loans as loans_svc, settings as settings_svc
from .settings import BankError
from .serialize import account_dict


def accrue(db: Session, account: Account, now=None) -> None:
    interest.accrue_savings(db, account, now or utcnow())


def deposit(db: Session, account: Account, amount_cents: int, note: str, actor: User) -> dict:
    if amount_cents <= 0:
        raise BankError("Amount must be positive")
    accrue(db, account)
    tx = ledger.append_tx(db, account, "money", "deposit", amount_cents, note=note, created_by=actor.id)
    return {"transaction": tx.id, "money_cents": account.money_cents}


def withdraw(db: Session, account: Account, amount_cents: int, note: str, actor: User) -> dict:
    if amount_cents <= 0:
        raise BankError("Amount must be positive")
    accrue(db, account)
    if account.money_cents < amount_cents:
        raise BankError("Insufficient funds")
    tx = ledger.append_tx(db, account, "money", "withdraw", -amount_cents, note=note, created_by=actor.id)
    return {"transaction": tx.id, "money_cents": account.money_cents}


def grant_time(db: Session, account: Account, amount_seconds: int, note: str, actor: User) -> dict:
    if amount_seconds <= 0:
        raise BankError("Amount must be positive")
    accrue(db, account)
    tx = ledger.append_tx(db, account, "screen", "grant", amount_seconds, note=note, created_by=actor.id)
    return {"transaction": tx.id, "screen_seconds": account.screen_seconds}


def deduct_time(db: Session, account: Account, amount_seconds: int, note: str, actor: User) -> dict:
    if amount_seconds <= 0:
        raise BankError("Amount must be positive")
    accrue(db, account)
    if account.screen_seconds < amount_seconds:
        raise BankError("Insufficient screen time")
    tx = ledger.append_tx(db, account, "screen", "deduct", -amount_seconds, note=note, created_by=actor.id)
    return {"transaction": tx.id, "screen_seconds": account.screen_seconds}


def adjust(db: Session, account: Account, ledger_name: str, amount: int, note: str, actor: User) -> dict:
    """Explicit correction (signed) on money or screen balances."""
    if ledger_name not in ("money", "screen"):
        raise BankError("adjust supports money or screen ledgers")
    accrue(db, account)
    tx = ledger.append_tx(db, account, ledger_name, "adjust", amount, note=note or "Correction", created_by=actor.id)
    key = "money_cents" if ledger_name == "money" else "screen_seconds"
    return {"transaction": tx.id, key: getattr(account, key)}


def convert(db: Session, account: Account, amount_cents: int, note: str, actor: User) -> dict:
    """Money -> screen time at the currently effective rate."""
    if amount_cents < int(settings_svc.get(db, "min_convert_cents")):
        raise BankError("Amount is below the minimum conversion size")
    accrue(db, account)
    if account.money_cents < amount_cents:
        raise BankError("Insufficient funds")
    now = utcnow()
    rate, rule = exchange.resolve_rate(db, now)
    seconds = exchange.convert_seconds(amount_cents, rate)
    if seconds <= 0:
        raise BankError("That amount converts to less than a second")
    meta = {
        "rate_minutes_per_dollar": rate,
        "rule": rule.name if rule else None,
        "seconds": seconds,
        "cents": amount_cents,
    }
    at = now
    ledger.append_tx(
        db, account, "money", "convert_out", -amount_cents,
        note=note or f"Converted to {seconds // 60} min of screen time",
        created_by=actor.id, meta=meta, created_at=at,
    )
    ledger.append_tx(
        db, account, "screen", "convert_in", seconds,
        note=note or f"Converted from ${amount_cents / 100:.2f}",
        created_by=actor.id, meta=meta, created_at=at,
    )
    return {
        "money_cents": account.money_cents,
        "screen_seconds": account.screen_seconds,
        "seconds": seconds,
        "rate_minutes_per_dollar": rate,
        "rule": rule.name if rule else None,
    }


def account_view(db: Session, account: Account, now=None) -> dict:
    """Balances after lazy accrual + projections + debt summary."""
    now = now or utcnow()
    accrue(db, account, now)
    apr = float(settings_svc.get(db, "savings_apr_percent"))
    debt = loans_svc.total_outstanding(db, account, now)
    active_loans = (
        db.query(Loan).filter(Loan.account_id == account.id, Loan.status == "active").all()
    )
    data = {
        **account_dict(account),
        "next_day_interest_cents": interest.next_day_interest_cents(account.money_cents, apr),
        "next_week_interest_cents": interest.compound_interest_cents(account.money_cents, apr, 7),
        "next_year_interest_cents": interest.compound_interest_cents(account.money_cents, apr, 365),
        "savings_apr_percent": apr,
        "debt_cents": debt,
        "active_loans": len(active_loans),
    }
    return data
