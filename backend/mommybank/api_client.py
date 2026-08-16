"""Typed REST client shared by the CLI and the MCP server.

Everything goes over the same /api/v1 endpoints as the GUI — one source of
truth for permissions, interest math and audit.
"""
from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def default_base_url() -> str:
    return os.environ.get("MOMMYBANK_URL", "http://127.0.0.1:8000").rstrip("/")


def dollars_to_cents(text: str) -> int:
    try:
        cents = (Decimal(text.strip()) * 100).quantize(Decimal("1"))
    except InvalidOperation:
        raise ValueError(f"Not a valid amount: {text!r}")
    if cents <= 0:
        raise ValueError("Amount must be positive")
    return int(cents)


class MommyBankClient:
    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = (base_url or default_base_url()).rstrip("/")
        self.token = token or os.environ.get("MOMMYBANK_TOKEN", "")
        self._client = httpx.Client(base_url=self.base_url, timeout=30)

    # ------------------------------------------------------------ plumbing
    def _request(self, method: str, path: str, **kwargs) -> Any:
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        resp = self._client.request(method, path, headers=headers, **kwargs)
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except ValueError:
                detail = resp.text
            raise ApiError(resp.status_code, str(detail))
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def get(self, path: str, params: dict | None = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, json: dict | None = None) -> Any:
        return self._request("POST", path, json=json)

    def patch(self, path: str, json: dict | None = None) -> Any:
        return self._request("PATCH", path, json=json)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    # ------------------------------------------------------------ auth
    def login(self, username: str, password: str) -> dict:
        data = self.post("/api/v1/auth/login", {"username": username, "password": password})
        self.token = data["token"]
        return data

    def me(self) -> dict:
        return self.get("/api/v1/auth/me")

    def change_password(self, old_password: str, new_password: str) -> None:
        self.post("/api/v1/auth/change-password", {"old_password": old_password, "new_password": new_password})

    # ------------------------------------------------------------ users
    def users(self) -> list:
        return self.get("/api/v1/users")

    def create_user(self, **fields) -> dict:
        return self.post("/api/v1/users", fields)

    def patch_user(self, user_id: int, **fields) -> dict:
        return self.patch(f"/api/v1/users/{user_id}", fields)

    def account_id(self, username: str) -> int:
        """Resolve a username to an account id (admin can address anyone)."""
        uname = username.strip().lower()
        for acct in self.get("/api/v1/accounts"):
            if acct["username"] == uname:
                return acct["id"]
        raise ApiError(404, f"No account for user {username!r}")

    # ------------------------------------------------------------ accounts
    def accounts(self) -> list:
        return self.get("/api/v1/accounts")

    def account(self, account_id: int) -> dict:
        return self.get(f"/api/v1/accounts/{account_id}")

    def overview(self) -> dict:
        return self.get("/api/v1/overview")

    def deposit(self, account_id: int, amount_cents: int, note: str = "") -> dict:
        return self.post(f"/api/v1/accounts/{account_id}/deposit", {"amount_cents": amount_cents, "note": note})

    def withdraw(self, account_id: int, amount_cents: int, note: str = "") -> dict:
        return self.post(f"/api/v1/accounts/{account_id}/withdraw", {"amount_cents": amount_cents, "note": note})

    def grant_time(self, account_id: int, amount_seconds: int, note: str = "") -> dict:
        return self.post(f"/api/v1/accounts/{account_id}/grant-time", {"amount_seconds": amount_seconds, "note": note})

    def deduct_time(self, account_id: int, amount_seconds: int, note: str = "") -> dict:
        return self.post(f"/api/v1/accounts/{account_id}/deduct-time", {"amount_seconds": amount_seconds, "note": note})

    def convert(self, account_id: int, amount_cents: int, note: str = "") -> dict:
        return self.post(f"/api/v1/accounts/{account_id}/convert", {"amount_cents": amount_cents, "note": note})

    def transactions(self, account_id: int, ledger: str | None = None, limit: int = 50) -> list:
        params = {"limit": limit}
        if ledger:
            params["ledger"] = ledger
        return self.get(f"/api/v1/accounts/{account_id}/transactions", params)

    # ------------------------------------------------------------ loans
    def borrow(self, account_id: int, amount_cents: int, note: str = "") -> dict:
        return self.post("/api/v1/loans/borrow", {
            "account_id": account_id, "amount_cents": amount_cents, "note": note,
        })

    def repay(self, loan_id: int, amount_cents: int, note: str = "") -> dict:
        return self.post(f"/api/v1/loans/{loan_id}/repay", {"amount_cents": amount_cents, "note": note})

    def loans(self, account_id: int | None = None) -> list:
        params = {"account_id": account_id} if account_id is not None else None
        return self.get("/api/v1/loans", params)

    # ------------------------------------------------------------ settings & rules
    def settings(self) -> dict:
        return self.get("/api/v1/settings")

    def set_settings(self, updates: dict) -> dict:
        return self.patch("/api/v1/settings", updates)

    def quote(self) -> dict:
        return self.get("/api/v1/exchange/quote")

    def rules(self) -> list:
        return self.get("/api/v1/exchange-rules")

    def create_rule(self, **fields) -> dict:
        return self.post("/api/v1/exchange-rules", fields)

    def patch_rule(self, rule_id: int, **fields) -> dict:
        return self.patch(f"/api/v1/exchange-rules/{rule_id}", fields)

    def delete_rule(self, rule_id: int) -> None:
        self.delete(f"/api/v1/exchange-rules/{rule_id}")
