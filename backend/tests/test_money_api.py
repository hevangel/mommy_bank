"""Money & screen-time operations, permissions, ledger invariants."""
from __future__ import annotations


def test_admin_deposit_withdraw_flow(client, admin_headers, make_kid):
    kid = make_kid()
    acct = kid["account_id"]
    r = client.post(f"/api/v1/accounts/{acct}/deposit", json={"amount_cents": 5000, "note": "allowance"},
                    headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["money_cents"] == 5000
    r = client.post(f"/api/v1/accounts/{acct}/withdraw", json={"amount_cents": 1200, "note": "candy"},
                    headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["money_cents"] == 3800
    r = client.get(f"/api/v1/accounts/{acct}", headers=admin_headers)
    assert r.json()["money_cents"] == 3800


def test_withdraw_no_overdraft(client, admin_headers, make_kid):
    kid = make_kid()
    acct = kid["account_id"]
    client.post(f"/api/v1/accounts/{acct}/deposit", json={"amount_cents": 100}, headers=admin_headers)
    r = client.post(f"/api/v1/accounts/{acct}/withdraw", json={"amount_cents": 101}, headers=admin_headers)
    assert r.status_code == 400
    assert "Insufficient" in r.json()["detail"]


def test_deposit_rejects_nonpositive(client, admin_headers, make_kid):
    kid = make_kid()
    r = client.post(f"/api/v1/accounts/{kid['account_id']}/deposit", json={"amount_cents": 0}, headers=admin_headers)
    assert r.status_code == 422


def test_kid_cannot_deposit_or_withdraw(client, make_kid):
    kid = make_kid()
    for path, body in (
        (f"/api/v1/accounts/{kid['account_id']}/deposit", {"amount_cents": 100}),
        (f"/api/v1/accounts/{kid['account_id']}/withdraw", {"amount_cents": 100}),
        (f"/api/v1/accounts/{kid['account_id']}/grant-time", {"amount_seconds": 60}),
        (f"/api/v1/accounts/{kid['account_id']}/deduct-time", {"amount_seconds": 60}),
        (f"/api/v1/accounts/{kid['account_id']}/adjust", {"ledger": "money", "amount": 100}),
    ):
        r = client.post(path, json=body, headers=kid["headers"])
        assert r.status_code == 403, (path, r.status_code)


def test_grant_and_deduct_time(client, admin_headers, make_kid):
    kid = make_kid()
    acct = kid["account_id"]
    r = client.post(f"/api/v1/accounts/{acct}/grant-time", json={"amount_seconds": 3600}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["screen_seconds"] == 3600
    r = client.post(f"/api/v1/accounts/{acct}/deduct-time", json={"amount_seconds": 600}, headers=admin_headers)
    assert r.json()["screen_seconds"] == 3000
    r = client.post(f"/api/v1/accounts/{acct}/deduct-time", json={"amount_seconds": 9999}, headers=admin_headers)
    assert r.status_code == 400


def test_adjust_signed(client, admin_headers, make_kid):
    kid = make_kid()
    acct = kid["account_id"]
    client.post(f"/api/v1/accounts/{acct}/deposit", json={"amount_cents": 500}, headers=admin_headers)
    r = client.post(f"/api/v1/accounts/{acct}/adjust", json={"ledger": "money", "amount": -200, "note": "typo fix"},
                    headers=admin_headers)
    assert r.json()["money_cents"] == 300
    r = client.post(f"/api/v1/accounts/{acct}/adjust", json={"ledger": "money", "amount": 50}, headers=admin_headers)
    assert r.json()["money_cents"] == 350
    # adjust cannot drive balance negative
    r = client.post(f"/api/v1/accounts/{acct}/adjust", json={"ledger": "money", "amount": -100000}, headers=admin_headers)
    assert r.status_code == 400


def test_ledger_rows_and_balance_after(client, admin_headers, make_kid):
    kid = make_kid()
    acct = kid["account_id"]
    client.post(f"/api/v1/accounts/{acct}/deposit", json={"amount_cents": 1000}, headers=admin_headers)
    client.post(f"/api/v1/accounts/{acct}/withdraw", json={"amount_cents": 250}, headers=admin_headers)
    client.post(f"/api/v1/accounts/{acct}/grant-time", json={"amount_seconds": 1200}, headers=admin_headers)
    rows = client.get(f"/api/v1/accounts/{acct}/transactions", headers=admin_headers).json()
    by_ledger = {}
    for t in rows:
        by_ledger.setdefault(t["ledger"], []).append(t)
    assert [t["balance_after"] for t in by_ledger["money"]] == [750, 1000]  # newest first
    assert by_ledger["screen"][0]["balance_after"] == 1200
    assert rows[0]["created_by_name"]  # auditor recorded


def test_ledger_filter_and_pagination(client, admin_headers, make_kid):
    kid = make_kid()
    acct = kid["account_id"]
    client.post(f"/api/v1/accounts/{acct}/deposit", json={"amount_cents": 100}, headers=admin_headers)
    client.post(f"/api/v1/accounts/{acct}/grant-time", json={"amount_seconds": 60}, headers=admin_headers)
    rows = client.get(f"/api/v1/accounts/{acct}/transactions", params={"ledger": "money"}, headers=admin_headers).json()
    assert all(t["ledger"] == "money" for t in rows) and len(rows) == 1
    rows = client.get(f"/api/v1/accounts/{acct}/transactions", params={"limit": 1}, headers=admin_headers).json()
    assert len(rows) == 1
    bad = client.get(f"/api/v1/accounts/{acct}/transactions", params={"ledger": "gold"}, headers=admin_headers)
    assert bad.status_code == 422


def test_kid_reads_own_only(client, admin_headers, make_kid):
    kid_a, kid_b = make_kid(), make_kid()
    # kid sees only own account in the list
    r = client.get("/api/v1/accounts", headers=kid_a["headers"])
    assert [a["id"] for a in r.json()] == [kid_a["account_id"]]
    # kid cannot read another kid's account or ledger
    assert client.get(f"/api/v1/accounts/{kid_b['account_id']}", headers=kid_a["headers"]).status_code == 403
    assert (
        client.get(f"/api/v1/accounts/{kid_b['account_id']}/transactions", headers=kid_a["headers"]).status_code
        == 403
    )
    # admin sees both
    r = client.get("/api/v1/accounts", headers=admin_headers)
    assert {a["id"] for a in r.json()} >= {kid_a["account_id"], kid_b["account_id"]}


def test_admin_overview_totals(client, admin_headers, make_kid):
    kid_a, kid_b = make_kid(), make_kid()
    client.post(f"/api/v1/accounts/{kid_a['account_id']}/deposit", json={"amount_cents": 1000}, headers=admin_headers)
    client.post(f"/api/v1/accounts/{kid_b['account_id']}/deposit", json={"amount_cents": 500}, headers=admin_headers)
    client.post(f"/api/v1/accounts/{kid_a['account_id']}/grant-time", json={"amount_seconds": 600}, headers=admin_headers)
    r = client.get("/api/v1/overview", headers=admin_headers)
    totals = r.json()["totals"]
    assert totals["money_cents"] >= 1500
    assert totals["screen_seconds"] >= 600
    assert client.get("/api/v1/overview", headers=kid_a["headers"]).status_code == 403
