"""Borrowing lifecycle: permissions, cap, interest, repay."""
from __future__ import annotations

from datetime import timedelta

from mommybank.db import SessionLocal, utcnow
from mommybank.models import Loan


def _enable_borrowing(client, admin_headers, limit_cents=5000, apr=10.0):
    r = client.patch(
        "/api/v1/settings",
        json={"borrow_enabled": True, "borrow_limit_cents": limit_cents, "borrow_apr_percent": apr},
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text


def _backdate_loan(loan_id: int, days: int) -> None:
    db = SessionLocal()
    try:
        loan = db.get(Loan, loan_id)
        loan.last_accrual_at = utcnow() - timedelta(days=days)
        db.commit()
    finally:
        db.close()


def test_borrow_disabled_by_default(client, admin_headers, make_kid):
    kid = make_kid(ui_mode="teen", can_borrow=True)
    r = client.post("/api/v1/loans/borrow",
                    json={"account_id": kid["account_id"], "amount_cents": 1000}, headers=kid["headers"])
    assert r.status_code == 400
    assert "disabled" in r.json()["detail"]


def test_borrow_needs_kid_permission(client, admin_headers, make_kid):
    _enable_borrowing(client, admin_headers)
    kid = make_kid(can_borrow=False)
    r = client.post("/api/v1/loans/borrow",
                    json={"account_id": kid["account_id"], "amount_cents": 1000}, headers=kid["headers"])
    assert r.status_code == 400  # BankError: not allowed
    # admin can always borrow on the kid's account
    r = client.post("/api/v1/loans/borrow",
                    json={"account_id": kid["account_id"], "amount_cents": 1000}, headers=admin_headers)
    assert r.status_code == 201


def test_borrow_and_debt_cap(client, admin_headers, make_kid):
    _enable_borrowing(client, admin_headers, limit_cents=2000)
    kid = make_kid(can_borrow=True)
    acct = kid["account_id"]
    r = client.post("/api/v1/loans/borrow", json={"account_id": acct, "amount_cents": 1500}, headers=kid["headers"])
    assert r.status_code == 201, r.text
    loan = r.json()
    assert loan["outstanding_cents"] == 1500
    assert loan["apr_percent"] == 10.0
    # money landed in the account
    data = client.get(f"/api/v1/accounts/{acct}", headers=kid["headers"]).json()
    assert data["money_cents"] == 1500
    assert data["debt_cents"] == 1500
    # exceeding the cap is refused
    r = client.post("/api/v1/loans/borrow", json={"account_id": acct, "amount_cents": 1000}, headers=kid["headers"])
    assert r.status_code == 400
    assert "cap" in r.json()["detail"]


def test_loan_interest_accrues(client, admin_headers, make_kid):
    _enable_borrowing(client, admin_headers, limit_cents=20000)
    kid = make_kid(can_borrow=True)
    r = client.post("/api/v1/loans/borrow",
                    json={"account_id": kid["account_id"], "amount_cents": 10000}, headers=kid["headers"])
    loan_id = r.json()["id"]
    _backdate_loan(loan_id, 10)
    rows = client.get("/api/v1/loans", headers=kid["headers"]).json()
    loan = next(l for l in rows if l["id"] == loan_id)
    expected = int(10000 * ((1 + 10.0 / 100 / 365) ** 10 - 1))
    assert loan["outstanding_cents"] == 10000 + expected
    # debt ledger row written
    txs = client.get(f"/api/v1/accounts/{kid['account_id']}/transactions",
                     params={"ledger": "debt"}, headers=kid["headers"]).json()
    assert any(t["kind"] == "loan_interest" for t in txs)


def test_repay_partial_then_full(client, admin_headers, make_kid):
    _enable_borrowing(client, admin_headers)
    kid = make_kid(can_borrow=True)
    acct = kid["account_id"]
    loan_id = client.post("/api/v1/loans/borrow",
                          json={"account_id": acct, "amount_cents": 1000}, headers=kid["headers"]).json()["id"]
    r = client.post(f"/api/v1/loans/{loan_id}/repay", json={"amount_cents": 400}, headers=kid["headers"])
    assert r.status_code == 200
    assert r.json()["repaid_cents"] == 400
    assert r.json()["loan"]["outstanding_cents"] == 600
    assert r.json()["loan"]["status"] == "active"
    # repay more than outstanding -> capped, loan closes
    r = client.post(f"/api/v1/loans/{loan_id}/repay", json={"amount_cents": 99999}, headers=kid["headers"])
    assert r.json()["repaid_cents"] == 600
    assert r.json()["loan"]["status"] == "repaid"
    assert r.json()["loan"]["outstanding_cents"] == 0
    # money was spent on repayment
    data = client.get(f"/api/v1/accounts/{acct}", headers=kid["headers"]).json()
    assert data["money_cents"] == 0
    assert data["debt_cents"] == 0


def test_repay_capped_by_balance(client, admin_headers, make_kid):
    _enable_borrowing(client, admin_headers)
    kid = make_kid(can_borrow=True)
    acct = kid["account_id"]
    loan_id = client.post("/api/v1/loans/borrow",
                          json={"account_id": acct, "amount_cents": 1000}, headers=kid["headers"]).json()["id"]
    # spend the borrowed money first
    client.post(f"/api/v1/accounts/{acct}/withdraw", json={"amount_cents": 900}, headers=admin_headers)
    r = client.post(f"/api/v1/loans/{loan_id}/repay", json={"amount_cents": 1000}, headers=kid["headers"])
    assert r.json()["repaid_cents"] == 100
    assert r.json()["loan"]["status"] == "active"


def test_kid_cannot_borrow_for_other(client, admin_headers, make_kid):
    _enable_borrowing(client, admin_headers)
    a, b = make_kid(can_borrow=True), make_kid(can_borrow=True)
    r = client.post("/api/v1/loans/borrow",
                    json={"account_id": b["account_id"], "amount_cents": 100}, headers=a["headers"])
    assert r.status_code == 403


def test_borrow_repay_notes_recorded(client, admin_headers, make_kid):
    _enable_borrowing(client, admin_headers)
    kid = make_kid(can_borrow=True)
    acct = kid["account_id"]
    loan_id = client.post("/api/v1/loans/borrow",
                          json={"account_id": acct, "amount_cents": 1000, "note": "new game"},
                          headers=kid["headers"]).json()["id"]
    txs = client.get(f"/api/v1/accounts/{acct}/transactions",
                     params={"ledger": "money"}, headers=kid["headers"]).json()
    borrow_tx = next(t for t in txs if t["kind"] == "borrow")
    assert "new game" in borrow_tx["note"]
    assert f"Loan #{loan_id}" in borrow_tx["note"]

    client.post(f"/api/v1/accounts/{acct}/deposit", json={"amount_cents": 1000}, headers=admin_headers)
    client.post(f"/api/v1/loans/{loan_id}/repay",
                json={"amount_cents": 400, "note": "birthday money"}, headers=kid["headers"])
    txs = client.get(f"/api/v1/accounts/{acct}/transactions",
                     params={"ledger": "money"}, headers=kid["headers"]).json()
    repay_tx = next(t for t in txs if t["kind"] == "repay")
    assert "birthday money" in repay_tx["note"]
    assert f"Repay loan #{loan_id}" in repay_tx["note"]

    # without a note the system text is still recorded
    client.post(f"/api/v1/loans/{loan_id}/repay", json={"amount_cents": 100}, headers=kid["headers"])
    txs = client.get(f"/api/v1/accounts/{acct}/transactions",
                     params={"ledger": "money"}, headers=kid["headers"]).json()
    repay_tx = next(t for t in txs if t["kind"] == "repay" and t["id"] != repay_tx["id"])
    assert repay_tx["note"] == f"Repay loan #{loan_id}"
