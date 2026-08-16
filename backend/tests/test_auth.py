"""Auth API: login, tokens, me, change password, inactive users."""
from __future__ import annotations

from .conftest import ADMIN_PASSWORD, ADMIN_USERNAME, gen_password


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_login_success_and_shape(client):
    resp = client.post("/api/v1/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200
    data = resp.json()
    assert data["token"]
    assert data["user"]["role"] == "admin"
    assert "password_hash" not in data["user"]


def test_login_wrong_password(client):
    resp = client.post("/api/v1/auth/login", json={"username": ADMIN_USERNAME, "password": "nope-" + gen_password()})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/api/v1/auth/login", json={"username": "ghost-" + gen_password(), "password": "whatever"})
    assert resp.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer bogus"}).status_code == 401


def test_me_roundtrip(client, admin_headers, make_kid):
    resp = client.get("/api/v1/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["username"] == ADMIN_USERNAME
    assert data["user"]["role"] == "admin"
    # admins are the parents — they manage accounts but don't own one
    assert "account" not in data
    kid = make_kid()
    resp = client.get("/api/v1/auth/me", headers=kid["headers"])
    assert "money_cents" in resp.json()["account"]


def test_change_password(client, make_kid):
    kid = make_kid()
    new_pw = gen_password()
    r = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "wrong-" + gen_password(), "new_password": new_pw},
        headers=kid["headers"],
    )
    assert r.status_code == 400
    r = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": kid["password"], "new_password": new_pw},
        headers=kid["headers"],
    )
    assert r.status_code == 204
    r = client.post("/api/v1/auth/login", json={"username": kid["username"], "password": new_pw})
    assert r.status_code == 200


def test_inactive_user_cannot_login(client, admin_headers, make_kid):
    kid = make_kid()
    uid_resp = client.get("/api/v1/users", headers=admin_headers)
    target = next(u for u in uid_resp.json() if u["username"] == kid["username"])
    r = client.patch(f"/api/v1/users/{target['id']}", json={"is_active": False}, headers=admin_headers)
    assert r.status_code == 200
    r = client.post("/api/v1/auth/login", json={"username": kid["username"], "password": kid["password"]})
    assert r.status_code == 403
    # old token also rejected
    r = client.get("/api/v1/auth/me", headers=kid["headers"])
    assert r.status_code == 401
