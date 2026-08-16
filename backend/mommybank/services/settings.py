"""Typed access to the settings table with safe defaults."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from ..models import Setting

DEFAULTS: dict[str, Any] = {
    "savings_apr_percent": 6.7,
    "interest_enabled": True,
    "borrow_enabled": False,
    "borrow_apr_percent": 10.0,
    "borrow_limit_cents": 5000,
    "exchange_base_minutes_per_dollar": 10.0,
    "min_convert_cents": 1,
    "currency_symbol": "$",
    "timezone": "UTC",
}

_TYPES: dict[str, type] = {
    "savings_apr_percent": float,
    "interest_enabled": bool,
    "borrow_enabled": bool,
    "borrow_apr_percent": float,
    "borrow_limit_cents": int,
    "exchange_base_minutes_per_dollar": float,
    "min_convert_cents": int,
    "currency_symbol": str,
    "timezone": str,
}


class BankError(Exception):
    """Business-rule violation -> HTTP 400."""


def _coerce(key: str, value: Any) -> Any:
    if key not in _TYPES:
        raise BankError(f"Unknown setting: {key}")
    t = _TYPES[key]
    if t is float:
        return float(value)
    if t is int:
        return int(value)
    if t is bool:
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)
    return str(value)


def _validate(key: str, value: Any) -> Any:
    if key in ("savings_apr_percent", "borrow_apr_percent") and not (0 <= value <= 100):
        raise BankError(f"{key} must be between 0 and 100")
    if key == "borrow_limit_cents" and value < 0:
        raise BankError("borrow_limit_cents must be >= 0")
    if key == "exchange_base_minutes_per_dollar" and not (0 < value <= 1000):
        raise BankError("exchange_base_minutes_per_dollar must be in (0, 1000]")
    if key == "min_convert_cents" and value < 1:
        raise BankError("min_convert_cents must be >= 1")
    if key == "currency_symbol" and not (1 <= len(value) <= 3):
        raise BankError("currency_symbol must be 1-3 characters")
    if key == "timezone":
        from zoneinfo import ZoneInfo

        try:
            ZoneInfo(value)
        except Exception:
            raise BankError(f"Unknown timezone: {value}")
    return value


def get_all(db: Session) -> dict[str, Any]:
    out = dict(DEFAULTS)
    for row in db.query(Setting).all():
        if not row.key.startswith("_"):
            try:
                out[row.key] = json.loads(row.value)
            except (ValueError, TypeError):
                continue
    return out


def get(db: Session, key: str) -> Any:
    default = DEFAULTS.get(key)
    row = db.get(Setting, key)
    if row is None:
        return default
    try:
        return json.loads(row.value)
    except (ValueError, TypeError):
        return default


def set_many(db: Session, updates: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, raw in updates.items():
        if key.startswith("_"):
            raise BankError("Read-only setting")
        value = _validate(key, _coerce(key, raw))
        clean[key] = value
    for key, value in clean.items():
        row = db.get(Setting, key)
        if row is None:
            row = Setting(key=key, value=json.dumps(value))
            db.add(row)
        else:
            row.value = json.dumps(value)
    db.flush()
    return {k: get(db, k) for k in clean}


def ensure_defaults(db: Session) -> None:
    """Insert any missing defaults on first run (idempotent)."""
    for key, value in DEFAULTS.items():
        if db.get(Setting, key) is None:
            db.add(Setting(key=key, value=json.dumps(value)))
    db.flush()
