"""Settings & exchange-rule admin API."""
from __future__ import annotations


def test_settings_admin_only(client, admin_headers, make_kid):
    kid = make_kid()
    assert client.get("/api/v1/settings", headers=kid["headers"]).status_code == 403
    r = client.get("/api/v1/settings", headers=admin_headers)
    assert r.status_code == 200
    s = r.json()
    assert s["savings_apr_percent"] == 6.7
    assert s["borrow_enabled"] is False
    assert s["exchange_base_minutes_per_dollar"] == 10.0
    assert "_jwt_secret" not in s  # private keys never exposed


def test_settings_update_and_validation(client, admin_headers):
    r = client.patch("/api/v1/settings", json={"savings_apr_percent": 8.25, "currency_symbol": "HK$"},
                     headers=admin_headers)
    assert r.status_code == 200
    s = client.get("/api/v1/settings", headers=admin_headers).json()
    assert s["savings_apr_percent"] == 8.25
    assert s["currency_symbol"] == "HK$"
    r = client.patch("/api/v1/settings", json={"savings_apr_percent": 500}, headers=admin_headers)
    assert r.status_code == 400
    r = client.patch("/api/v1/settings", json={"timezone": "Not/AZone"}, headers=admin_headers)
    assert r.status_code == 400
    r = client.patch("/api/v1/settings", json={"timezone": "Asia/Hong_Kong", "savings_apr_percent": 6.7,
                                               "currency_symbol": "$"}, headers=admin_headers)
    assert r.status_code == 200


def test_rules_crud(client, admin_headers, make_kid):
    kid = make_kid()
    # create (admin only)
    assert client.post("/api/v1/exchange-rules", json={}, headers=kid["headers"]).status_code == 403
    r = client.post(
        "/api/v1/exchange-rules",
        json={"name": "QA rule", "days": [5, 6], "start_minute": 420, "end_minute": 660,
              "minutes_per_dollar": 15.0, "priority": 7},
        headers=admin_headers,
    )
    assert r.status_code == 201
    rule = r.json()
    assert rule["days"] == [5, 6]
    # invalid days rejected
    r = client.post("/api/v1/exchange-rules",
                    json={"name": "bad", "days": [9], "start_minute": 0, "end_minute": 60,
                          "minutes_per_dollar": 5},
                    headers=admin_headers)
    assert r.status_code == 422
    # list visible to kids too
    rows = client.get("/api/v1/exchange-rules", headers=kid["headers"]).json()
    assert any(x["id"] == rule["id"] for x in rows)
    # patch
    r = client.patch(f"/api/v1/exchange-rules/{rule['id']}", json={"minutes_per_dollar": 16.5, "is_active": False},
                     headers=admin_headers)
    assert r.json()["minutes_per_dollar"] == 16.5
    assert r.json()["is_active"] is False
    assert client.patch(f"/api/v1/exchange-rules/{rule['id']}", json={"rate": 1}, headers=kid["headers"]).status_code == 403
    # delete
    assert client.delete(f"/api/v1/exchange-rules/{rule['id']}", headers=admin_headers).status_code == 204
    assert client.delete(f"/api/v1/exchange-rules/{rule['id']}", headers=admin_headers).status_code == 404


def test_seeded_example_rules_exist(client, admin_headers):
    rows = client.get("/api/v1/exchange-rules", headers=admin_headers).json()
    names = {r["name"] for r in rows}
    assert {"Bedtime peak", "After-school off-peak", "Weekend morning bonus"} <= names
