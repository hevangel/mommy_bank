"""User management API."""
from __future__ import annotations

from .conftest import ADMIN_USERNAME, gen_password, unique_name


def test_users_list_admin_only(client, admin_headers, make_kid):
    assert client.get("/api/v1/users", headers=make_kid()["headers"]).status_code == 403
    r = client.get("/api/v1/users", headers=admin_headers)
    assert r.status_code == 200
    assert any(u["username"] == ADMIN_USERNAME for u in r.json())


def test_create_kid_defaults(client, admin_headers):
    username = unique_name()
    password = gen_password()
    r = client.post(
        "/api/v1/users",
        json={"username": username, "password": password, "display_name": "Test Kid"},
        headers=admin_headers,
    )
    assert r.status_code == 201
    user = r.json()
    assert user["ui_mode"] == "teen"
    assert user["can_convert"] is True  # teen default
    assert user["can_borrow"] is False
    # account auto-created and user can log in
    login = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    assert "account" in login.json()


def test_create_toddler_defaults_no_convert(client, admin_headers):
    r = client.post(
        "/api/v1/users",
        json={"username": unique_name(), "password": gen_password(), "display_name": "Tiny",
              "ui_mode": "toddler", "avatar": "🐥"},
        headers=admin_headers,
    )
    assert r.status_code == 201
    assert r.json()["can_convert"] is False
    assert r.json()["avatar"] == "🐥"


def test_create_duplicate_username(client, admin_headers):
    username = unique_name()
    body = {"username": username, "password": gen_password(), "display_name": "One"}
    assert client.post("/api/v1/users", json=body, headers=admin_headers).status_code == 201
    body2 = {"username": username, "password": gen_password(), "display_name": "Two"}
    assert client.post("/api/v1/users", json=body2, headers=admin_headers).status_code == 400


def test_create_kid_forbidden_for_kid(client, make_kid):
    r = client.post(
        "/api/v1/users",
        json={"username": unique_name(), "password": gen_password(), "display_name": "Sneaky"},
        headers=make_kid()["headers"],
    )
    assert r.status_code == 403


def test_patch_user_fields_and_password_reset(client, admin_headers, make_kid):
    kid = make_kid()
    users = client.get("/api/v1/users", headers=admin_headers).json()
    uid = next(u["id"] for u in users if u["username"] == kid["username"])
    new_pw = gen_password()
    r = client.patch(
        f"/api/v1/users/{uid}",
        json={"ui_mode": "kid", "can_borrow": True, "password": new_pw, "display_name": "Renamed"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ui_mode"] == "kid"
    assert body["can_borrow"] is True
    assert body["display_name"] == "Renamed"
    login = client.post("/api/v1/auth/login", json={"username": kid["username"], "password": new_pw})
    assert login.status_code == 200


def test_last_admin_guard(client, admin_headers):
    users = client.get("/api/v1/users", headers=admin_headers).json()
    admin = next(u for u in users if u["username"] == ADMIN_USERNAME)
    # cannot deactivate the only admin
    assert client.patch(f"/api/v1/users/{admin['id']}", json={"is_active": False}, headers=admin_headers).status_code == 400
    assert client.patch(f"/api/v1/users/{admin['id']}", json={"role": "user"}, headers=admin_headers).status_code == 400
    # but a second admin can be created and then the guard no longer blocks… (first admin removable by other admin)


def test_patch_missing_user_404(client, admin_headers):
    assert client.patch("/api/v1/users/999999", json={"display_name": "X"}, headers=admin_headers).status_code == 404
