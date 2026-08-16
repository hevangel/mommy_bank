"""Money -> screen time conversion: quote, rates, rules, permissions."""
from __future__ import annotations


def _add_always_rule(client, admin_headers, rate: float, priority: int = 1) -> int:
    r = client.post(
        "/api/v1/exchange-rules",
        json={
            "name": f"test-rule-{rate}", "days": [0, 1, 2, 3, 4, 5, 6],
            "start_minute": 0, "end_minute": 1439, "minutes_per_dollar": rate,
            "priority": priority,
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_quote_shape(client, admin_headers):
    r = client.get("/api/v1/exchange/quote", headers=admin_headers)
    assert r.status_code == 200
    q = r.json()
    assert q["base_rate"] == 10.0
    assert q["rate"] > 0
    assert "timezone" in q and "local_time" in q
    # public borrow state for the kid UI
    assert q["borrow_enabled"] is False
    assert q["borrow_apr_percent"] == 10.0


def test_convert_uses_current_rate(client, admin_headers, make_kid):
    kid = make_kid()
    acct = kid["account_id"]
    client.post(f"/api/v1/accounts/{acct}/deposit", json={"amount_cents": 200}, headers=admin_headers)
    q = client.get("/api/v1/exchange/quote", headers=kid["headers"]).json()
    r = client.post(f"/api/v1/accounts/{acct}/convert", json={"amount_cents": 100}, headers=kid["headers"])
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["rate_minutes_per_dollar"] == q["rate"]
    assert data["seconds"] == int(100 * q["rate"] * 60 / 100)
    assert data["money_cents"] == 100
    assert data["screen_seconds"] == data["seconds"]


def test_convert_pair_ledger_rows(client, admin_headers, make_kid):
    kid = make_kid()
    acct = kid["account_id"]
    client.post(f"/api/v1/accounts/{acct}/deposit", json={"amount_cents": 500}, headers=admin_headers)
    q = client.get("/api/v1/exchange/quote", headers=kid["headers"]).json()
    expected_seconds = int(200 * q["rate"] * 60 / 100)
    client.post(f"/api/v1/accounts/{acct}/convert", json={"amount_cents": 200}, headers=kid["headers"])
    rows = client.get(f"/api/v1/accounts/{acct}/transactions", headers=admin_headers).json()
    kinds = {t["kind"]: t for t in rows}
    assert kinds["convert_out"]["delta"] == -200
    assert kinds["convert_out"]["balance_after"] == 300
    assert kinds["convert_in"]["delta"] == expected_seconds
    assert kinds["convert_in"]["balance_after"] == expected_seconds
    meta = kinds["convert_out"]["meta"]
    assert meta["rate_minutes_per_dollar"] == q["rate"]
    assert meta["seconds"] == expected_seconds


def test_convert_applies_active_rule_rate(client, admin_headers, make_kid):
    kid = make_kid()
    acct = kid["account_id"]
    rule_id = _add_always_rule(client, admin_headers, rate=12.0)
    try:
        client.post(f"/api/v1/accounts/{acct}/deposit", json={"amount_cents": 100}, headers=admin_headers)
        r = client.post(f"/api/v1/accounts/{acct}/convert", json={"amount_cents": 100}, headers=kid["headers"])
        assert r.json()["seconds"] == 720  # $1 -> 12 min
        assert r.json()["rule"] == "test-rule-12.0"
    finally:
        client.delete(f"/api/v1/exchange-rules/{rule_id}", headers=admin_headers)


def test_convert_insufficient_funds(client, admin_headers, make_kid):
    kid = make_kid()
    r = client.post(f"/api/v1/accounts/{kid['account_id']}/convert", json={"amount_cents": 1}, headers=kid["headers"])
    assert r.status_code == 400


def test_convert_denied_without_permission(client, admin_headers, make_kid):
    kid = make_kid(ui_mode="toddler", can_convert=False)
    acct = kid["account_id"]
    client.post(f"/api/v1/accounts/{acct}/deposit", json={"amount_cents": 100}, headers=admin_headers)
    r = client.post(f"/api/v1/accounts/{acct}/convert", json={"amount_cents": 100}, headers=kid["headers"])
    assert r.status_code == 403
    # admin may convert on the kid's behalf
    r = client.post(f"/api/v1/accounts/{acct}/convert", json={"amount_cents": 100}, headers=admin_headers)
    assert r.status_code == 200


def test_kid_cannot_convert_for_other(client, admin_headers, make_kid):
    a, b = make_kid(), make_kid()
    client.post(f"/api/v1/accounts/{b['account_id']}/deposit", json={"amount_cents": 100}, headers=admin_headers)
    r = client.post(f"/api/v1/accounts/{b['account_id']}/convert", json={"amount_cents": 100}, headers=a["headers"])
    assert r.status_code == 403
