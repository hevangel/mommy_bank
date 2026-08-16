"""Interest accrual through the API (lazy, on read/touch)."""
from __future__ import annotations

from datetime import timedelta

from mommybank.db import SessionLocal, utcnow
from mommybank.models import Account


def _backdate(account_id: int, days: int) -> None:
    db = SessionLocal()
    try:
        acct = db.get(Account, account_id)
        acct.last_interest_at = utcnow() - timedelta(days=days)
        db.commit()
    finally:
        db.close()


def test_interest_appears_on_read(client, admin_headers, make_kid):
    import math

    kid = make_kid()
    acct = kid["account_id"]
    client.post(f"/api/v1/accounts/{acct}/deposit", json={"amount_cents": 10000}, headers=admin_headers)
    _backdate(acct, 10)
    r = client.get(f"/api/v1/accounts/{acct}", headers=admin_headers)
    data = r.json()
    expected = int(10000 * ((1 + 6.7 / 100 / 365) ** 10 - 1))
    assert data["money_cents"] == 10000 + expected
    # projections are computed on the post-accrual balance
    balance = 10000 + expected
    assert data["next_day_interest_cents"] == math.floor(balance * (6.7 / 100 / 365))
    assert data["next_week_interest_cents"] == math.floor(balance * ((1 + 6.7 / 100 / 365) ** 7 - 1))
    assert data["next_year_interest_cents"] == math.floor(balance * ((1 + 6.7 / 100 / 365) ** 365 - 1))
    # ledger has the interest row
    rows = client.get(f"/api/v1/accounts/{acct}/transactions", headers=admin_headers).json()
    interest_rows = [t for t in rows if t["kind"] == "interest"]
    assert len(interest_rows) == 1
    assert interest_rows[0]["delta"] == expected
    assert interest_rows[0]["created_by"] is None  # system


def test_interest_idempotent_on_second_read(client, admin_headers, make_kid):
    kid = make_kid()
    acct = kid["account_id"]
    client.post(f"/api/v1/accounts/{acct}/deposit", json={"amount_cents": 10000}, headers=admin_headers)
    _backdate(acct, 3)
    first = client.get(f"/api/v1/accounts/{acct}", headers=admin_headers).json()["money_cents"]
    second = client.get(f"/api/v1/accounts/{acct}", headers=admin_headers).json()["money_cents"]
    assert first == second


def test_no_interest_on_zero_balance(client, admin_headers, make_kid):
    kid = make_kid()
    _backdate(kid["account_id"], 30)
    data = client.get(f"/api/v1/accounts/{kid['account_id']}", headers=admin_headers).json()
    assert data["money_cents"] == 0
