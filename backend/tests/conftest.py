"""Shared fixtures. Env is set BEFORE any mommybank import; credentials are
generated at runtime (never literal)."""
from __future__ import annotations

import os
import secrets
import tempfile

os.environ["MOMMYBANK_DB"] = os.path.join(tempfile.mkdtemp(prefix="mommybank-test-"), "bank.db")
os.environ["MOMMYBANK_BCRYPT_ROUNDS"] = "4"
os.environ["MOMMYBANK_SECRET"] = secrets.token_urlsafe(32)
os.environ["MOMMYBANK_SEED_DEMO"] = "0"
os.environ["MOMMYBANK_STATIC_DIR"] = os.path.join(tempfile.gettempdir(), "nonexistent-static")

ADMIN_USERNAME = "testadmin"
ADMIN_PASSWORD = secrets.token_urlsafe(12)
os.environ["MOMMYBANK_ADMIN_USERNAME"] = ADMIN_USERNAME
os.environ["MOMMYBANK_ADMIN_PASSWORD"] = ADMIN_PASSWORD

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from mommybank.db import SessionLocal  # noqa: E402
from mommybank.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    """Create tables + seed once, independent of any TestClient usage."""
    from mommybank.db import Base, get_engine
    from mommybank.seed import seed

    Base.metadata.create_all(get_engine())
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    yield


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_settings():
    """Fresh default settings before every test (prevents cross-test leaks)."""
    from mommybank.models import Setting
    from mommybank.services import settings as settings_svc

    db = SessionLocal()
    try:
        for row in db.query(Setting).all():
            if not row.key.startswith("_"):
                db.delete(row)
        db.commit()
        settings_svc.ensure_defaults(db)
        db.commit()
    finally:
        db.close()
    yield


def gen_password() -> str:
    return secrets.token_urlsafe(12)


@pytest.fixture(scope="session")
def admin_headers(client):
    resp = client.post("/api/v1/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['token']}"}


_counter = {"n": 0}


def unique_name(prefix: str = "kid") -> str:
    _counter["n"] += 1
    return f"{prefix}{_counter['n']}{secrets.token_hex(3)}"


@pytest.fixture()
def make_kid(client, admin_headers):
    """Create a kid via the admin API; returns (username, password, headers)."""

    def _make(ui_mode: str = "teen", can_convert: bool | None = None, can_borrow: bool = False):
        username, password = unique_name(), gen_password()
        body = {
            "username": username,
            "password": password,
            "display_name": username.title(),
            "ui_mode": ui_mode,
            "can_borrow": can_borrow,
        }
        if can_convert is not None:
            body["can_convert"] = can_convert
        resp = client.post("/api/v1/users", json=body, headers=admin_headers)
        assert resp.status_code == 201, resp.text
        resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
        assert resp.status_code == 200, resp.text
        headers = {"Authorization": f"Bearer {resp.json()['token']}"}
        account_id = resp.json()["account"]["id"]
        return {"username": username, "password": password, "headers": headers, "account_id": account_id}

    return _make


# ------------------------------------------------------- ASGI client for CLI/MCP


@pytest.fixture()
def asgi_api_client(monkeypatch):
    """Point MommyBankClient at the in-process ASGI app via TestClient (no socket)."""
    import mommybank.api_client as api_client_mod

    original_init = api_client_mod.MommyBankClient.__init__

    def patched(self, base_url=None, token=None):
        original_init(self, base_url="http://testserver", token=token)
        self._client = TestClient(app)  # httpx.Client wired to the ASGI app
        self.token = token or os.environ.get("MOMMYBANK_TOKEN", "")

    monkeypatch.setattr(api_client_mod.MommyBankClient, "__init__", patched)
    return api_client_mod.MommyBankClient
