"""Unit tests for the pure service logic: interest math and exchange rules."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from contextlib import contextmanager

import pytest

from mommybank.db import SessionLocal, utcnow
from mommybank.models import Account, ExchangeRule, User
from mommybank.security import hash_password
from mommybank.services import exchange, interest, settings as settings_svc
from mommybank.services.settings import BankError


def _utc(h: int, m: int = 0, wd_offset: int = 0) -> datetime:
    """A UTC datetime; wd_offset shifts days so tests pick a weekday."""
    base = datetime(2026, 8, 10, h, m, tzinfo=timezone.utc)  # a Monday
    return base + timedelta(days=wd_offset)


def _mk_account(db, username="svc") -> Account:
    user = User(
        username=username + str(utcnow().timestamp()),
        password_hash=hash_password("x" * 12),
        display_name=username,
    )
    db.add(user)
    db.flush()
    acct = Account(user_id=user.id, last_interest_at=utcnow())
    db.add(acct)
    db.commit()
    return acct


def _mk_rule(db, name, days, start, end, rate, priority=100, active=True) -> ExchangeRule:
    rule = ExchangeRule(
        name=name, priority=priority, days=json.dumps(days), start_minute=start,
        end_minute=end, minutes_per_dollar=rate, is_active=active,
    )
    db.add(rule)
    db.commit()
    return rule


@contextmanager
def isolated_rules(db):
    """Snapshot & remove every rule so tests assert against a clean slate,
    then restore the original rules afterwards."""
    snap = [
        dict(name=r.name, priority=r.priority, days=r.days, start_minute=r.start_minute,
             end_minute=r.end_minute, minutes_per_dollar=r.minutes_per_dollar, is_active=r.is_active)
        for r in db.query(ExchangeRule).all()
    ]
    db.query(ExchangeRule).delete()
    db.commit()
    try:
        yield
    finally:
        db.query(ExchangeRule).delete()
        db.commit()
        for s in snap:
            db.add(ExchangeRule(**s))
        db.commit()


# ---------------------------------------------------------------- interest math


def test_compound_interest_matches_formula():
    apr = 6.7
    for days in (1, 5, 30, 365):
        expected = int(10000 * ((1 + apr / 100 / 365) ** days - 1))
        assert interest.compound_interest_cents(10000, apr, days) == expected


def test_compound_interest_sanity_values():
    # ~$100 at 6.7% APR daily for 30 days ≈ 55c
    got = interest.compound_interest_cents(10000, 6.7, 30)
    assert 54 <= got <= 56
    # ~$100 for a full year ≈ $6.93
    got_year = interest.compound_interest_cents(10000, 6.7, 365)
    assert 690 <= got_year <= 695


def test_compound_interest_edges():
    assert interest.compound_interest_cents(0, 6.7, 10) == 0
    assert interest.compound_interest_cents(10000, 6.7, 0) == 0
    assert interest.compound_interest_cents(10, 6.7, 1) == 0  # floored below a cent


def test_whole_days_elapsed():
    now = datetime(2026, 8, 10, 12, 0)
    assert interest.whole_days_elapsed(now - timedelta(days=3), now) == 3
    assert interest.whole_days_elapsed(now - timedelta(days=2, hours=23), now) == 2
    assert interest.whole_days_elapsed(now - timedelta(hours=23, minutes=59), now) == 0
    assert interest.whole_days_elapsed(now + timedelta(days=1), now) == 0  # future cursor


def test_accrue_savings_idempotent():
    db = SessionLocal()
    try:
        acct = _mk_account(db)
        acct.money_cents = 10000
        now = utcnow()
        acct.last_interest_at = now - timedelta(days=2)
        db.commit()
        first = interest.accrue_savings(db, acct, now)
        assert first == interest.compound_interest_cents(10000, 6.7, 2)
        assert acct.money_cents == 10000 + first
        again = interest.accrue_savings(db, acct, now)
        assert again == 0
        assert acct.money_cents == 10000 + first
    finally:
        db.close()


def test_accrue_savings_respects_disable():
    db = SessionLocal()
    try:
        settings_svc.set_many(db, {"interest_enabled": False})
        acct = _mk_account(db)
        acct.money_cents = 10000
        acct.last_interest_at = utcnow() - timedelta(days=5)
        db.commit()
        assert interest.accrue_savings(db, acct, utcnow()) == 0
        assert acct.money_cents == 10000
    finally:
        settings_svc.set_many(db, {"interest_enabled": True})
        db.close()


# ---------------------------------------------------------------- exchange rules


def test_no_rules_falls_back_to_base_rate():
    db = SessionLocal()
    try:
        rate, rule = exchange.resolve_rate(db, _utc(12))
        assert rate == 10.0
        assert rule is None
    finally:
        db.close()


def test_weekday_window_matches():
    db = SessionLocal()
    try:
        with isolated_rules(db):
            _mk_rule(db, "after-school", [0, 1, 2, 3, 4], 15 * 60, 18 * 60, 12.0)
            rate, rule = exchange.resolve_rate(db, _utc(16, 0))  # Monday 16:00
            assert (rate, rule.name) == (12.0, "after-school")
            rate, rule = exchange.resolve_rate(db, _utc(16, 0, wd_offset=5))  # Saturday
            assert (rate, rule) == (10.0, None)
            rate, rule = exchange.resolve_rate(db, _utc(19, 0))  # outside window
            assert (rate, rule) == (10.0, None)
    finally:
        db.close()


def test_cross_midnight_window():
    db = SessionLocal()
    try:
        with isolated_rules(db):
            _mk_rule(db, "night", [0, 1, 2, 3, 4, 5, 6], 20 * 60, 6 * 60, 5.0)
            rate, _ = exchange.resolve_rate(db, _utc(23, 30))
            assert rate == 5.0
            rate, _ = exchange.resolve_rate(db, _utc(3, 0))
            assert rate == 5.0
            rate, _ = exchange.resolve_rate(db, _utc(12, 0))
            assert rate == 10.0
    finally:
        db.close()


def test_priority_lowest_number_wins_and_inactive_ignored():
    db = SessionLocal()
    try:
        with isolated_rules(db):
            _mk_rule(db, "weak", [0], 0, 1439, 11.0, priority=50)
            r2 = _mk_rule(db, "strong", [0], 0, 1439, 7.0, priority=5)
            rate, rule = exchange.resolve_rate(db, _utc(12, 0))  # Monday
            assert (rate, rule.name) == (7.0, "strong")
            r2.is_active = False
            db.commit()
            rate, rule = exchange.resolve_rate(db, _utc(12, 0))
            assert (rate, rule.name) == (11.0, "weak")
    finally:
        db.close()


def test_convert_seconds_math():
    assert exchange.convert_seconds(100, 10.0) == 600  # $1 -> 10 min
    assert exchange.convert_seconds(150, 10.0) == 900  # $1.50 -> 15 min
    assert exchange.convert_seconds(100, 12.5) == 750
    assert exchange.convert_seconds(1, 15.0) == 9  # floors
    assert exchange.convert_seconds(0, 10.0) == 0


def test_quote_shape():
    db = SessionLocal()
    try:
        with isolated_rules(db):
            _mk_rule(db, "all-day", [0, 1, 2, 3, 4, 5, 6], 0, 1439, 13.0)
            q = exchange.quote(db, _utc(9, 30))
            assert q["rate"] == 13.0
            assert q["rule"]["name"] == "all-day"
            assert q["until"] is not None
    finally:
        db.close()


# ---------------------------------------------------------------- settings


def test_settings_validation():
    db = SessionLocal()
    try:
        with pytest.raises(BankError):
            settings_svc.set_many(db, {"savings_apr_percent": -1})
        with pytest.raises(BankError):
            settings_svc.set_many(db, {"timezone": "Mars/Olympus"})
        with pytest.raises(BankError):
            settings_svc.set_many(db, {"_jwt_secret": "nope"})
        out = settings_svc.set_many(db, {"savings_apr_percent": "8.5"})  # string coercion
        assert out["savings_apr_percent"] == 8.5
        settings_svc.set_many(db, {"savings_apr_percent": 6.7})
    finally:
        db.close()
