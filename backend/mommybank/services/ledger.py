"""Append-only ledger writes. Every balance change leaves exactly one row."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from ..db import utcnow
from ..models import Account, Transaction
from .settings import BankError

LEDGERS = ("money", "screen", "debt")


def append_tx(
    db: Session,
    account: Account,
    ledger: str,
    kind: str,
    delta: int,
    *,
    note: str = "",
    created_by: int | None = None,
    meta: dict | None = None,
    balance_after: int | None = None,
    created_at=None,
) -> Transaction:
    if ledger not in LEDGERS:
        raise BankError(f"Unknown ledger: {ledger}")
    if ledger == "money":
        account.money_cents += delta
        if account.money_cents < 0:
            account.money_cents -= delta
            raise BankError("Insufficient funds")
        balance_after = account.money_cents
    elif ledger == "screen":
        account.screen_seconds += delta
        if account.screen_seconds < 0:
            account.screen_seconds -= delta
            raise BankError("Insufficient screen time")
        balance_after = account.screen_seconds
    elif balance_after is None:
        raise BankError("debt ledger entries must provide balance_after")
    tx = Transaction(
        account_id=account.id,
        ledger=ledger,
        kind=kind,
        delta=int(delta),
        balance_after=int(balance_after),
        note=note or "",
        created_by=created_by,
        meta=json.dumps(meta or {}),
        created_at=created_at or utcnow(),
    )
    db.add(tx)
    db.flush()
    return tx
