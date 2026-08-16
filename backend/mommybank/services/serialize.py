"""JSON serializers shared by routers (and thus CLI/MCP via HTTP)."""
from __future__ import annotations

from ..db import iso
from ..models import Account, ExchangeRule, Loan, Transaction, User
from . import interest


def user_dict(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "display_name": u.display_name,
        "role": u.role,
        "ui_mode": u.ui_mode,
        "avatar": u.avatar,
        "email": u.email,
        "can_convert": bool(u.can_convert),
        "can_borrow": bool(u.can_borrow),
        "is_active": bool(u.is_active),
        "created_at": iso(u.created_at),
    }


def account_dict(a: Account) -> dict:
    return {
        "id": a.id,
        "user_id": a.user_id,
        "username": a.user.username,
        "display_name": a.user.display_name,
        "avatar": a.user.avatar,
        "ui_mode": a.user.ui_mode,
        "can_convert": bool(a.user.can_convert),
        "can_borrow": bool(a.user.can_borrow),
        "money_cents": a.money_cents,
        "screen_seconds": a.screen_seconds,
        "last_interest_at": iso(a.last_interest_at),
        "created_at": iso(a.created_at),
    }


def tx_dict(t: Transaction, created_by_name: str | None = None) -> dict:
    return {
        "id": t.id,
        "account_id": t.account_id,
        "ledger": t.ledger,
        "kind": t.kind,
        "delta": t.delta,
        "balance_after": t.balance_after,
        "note": t.note,
        "meta": t.meta_dict,
        "created_by": t.created_by,
        "created_by_name": created_by_name,
        "created_at": iso(t.created_at),
    }


def loan_dict(l: Loan) -> dict:
    return {
        "id": l.id,
        "account_id": l.account_id,
        "username": l.account.user.username,
        "principal_cents": l.principal_cents,
        "outstanding_cents": l.outstanding_cents,
        "apr_percent": l.apr_percent,
        "status": l.status,
        "created_at": iso(l.created_at),
        "repaid_at": iso(l.repaid_at) if l.repaid_at else None,
        "next_day_interest_cents": 0 if l.status != "active" else interest.next_day_interest_cents(
            l.outstanding_cents, l.apr_percent
        ),
    }


def rule_dict(r: ExchangeRule) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "priority": r.priority,
        "days": r.days_list,
        "start_minute": r.start_minute,
        "end_minute": r.end_minute,
        "minutes_per_dollar": float(r.minutes_per_dollar),
        "is_active": bool(r.is_active),
    }
