"""Mommy Bank MCP server — every GUI capability as a tool for AI agents.

Run:  python -m mommybank.mcp_server        (stdio transport)

Auth: MOMMYBANK_TOKEN env, or MOMMYBANK_USERNAME/MOMMYBANK_PASSWORD env
(auto-login at startup), or call the mommybank_login tool first.
"""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from .api_client import MommyBankClient

mcp = FastMCP("mommybank", instructions=(
    "Mommy Bank is a family bank with two currencies: money (integer cents) and "
    "screen time (integer seconds). Admins (parents) deposit/withdraw and configure "
    "interest, borrowing and money→screen-time exchange rates with peak/off-peak "
    "rules; kids have read-only access plus optional self-service convert/borrow. "
    "Call mommybank_login first unless credentials come from the environment."
))

_client = MommyBankClient()


def _auto_login_from_env() -> None:
    if _client.token:
        return
    username = os.environ.get("MOMMYBANK_USERNAME", "")
    password = os.environ.get("MOMMYBANK_PASSWORD", "")
    if username and password:
        _client.login(username, password)


def _client_ready() -> MommyBankClient:
    _auto_login_from_env()
    if not _client.token:
        raise RuntimeError("Not logged in: call mommybank_login or set MOMMYBANK_USERNAME/MOMMYBANK_PASSWORD")
    return _client


# ------------------------------------------------------------------ tools


@mcp.tool()
def mommybank_login(username: str, password: str) -> dict:
    """Log in to Mommy Bank. Admins get full control; kids get read access."""
    return _client.login(username, password)


@mcp.tool()
def mommybank_whoami() -> dict:
    """Who am I logged in as, with account summary."""
    return _client_ready().me()


@mcp.tool()
def mommybank_overview() -> dict:
    """Admin overview: every kid's balances and the bank totals."""
    return _client_ready().overview()


@mcp.tool()
def mommybank_balance(username: str | None = None) -> dict:
    """Balance for one kid (or all visible accounts when username omitted)."""
    client = _client_ready()
    if username is None:
        return {"accounts": client.accounts()}
    acct = client.account(client.account_id(username))
    return acct


@mcp.tool()
def mommybank_deposit(username: str, amount_cents: int, note: str = "") -> dict:
    """Admin: deposit money (integer cents) into a kid's account."""
    client = _client_ready()
    return client.deposit(client.account_id(username), amount_cents, note)


@mcp.tool()
def mommybank_withdraw(username: str, amount_cents: int, note: str = "") -> dict:
    """Admin: withdraw money (integer cents) from a kid's account."""
    client = _client_ready()
    return client.withdraw(client.account_id(username), amount_cents, note)


@mcp.tool()
def mommybank_grant_time(username: str, amount_seconds: int, note: str = "") -> dict:
    """Admin: grant screen time (integer seconds)."""
    client = _client_ready()
    return client.grant_time(client.account_id(username), amount_seconds, note)


@mcp.tool()
def mommybank_deduct_time(username: str, amount_seconds: int, note: str = "") -> dict:
    """Admin: deduct screen time (integer seconds)."""
    client = _client_ready()
    return client.deduct_time(client.account_id(username), amount_seconds, note)


@mcp.tool()
def mommybank_convert(username: str, amount_cents: int, note: str = "") -> dict:
    """Convert money→screen time at the current rate (kid self-service if permitted)."""
    client = _client_ready()
    return client.convert(client.account_id(username), amount_cents, note)


@mcp.tool()
def mommybank_quote() -> dict:
    """Current exchange rate, which rule applies, and the next rate change."""
    return _client_ready().quote()


@mcp.tool()
def mommybank_borrow(username: str, amount_cents: int) -> dict:
    """Open a loan: adds money now, accrues interest at the borrow APR."""
    client = _client_ready()
    return client.borrow(client.account_id(username), amount_cents)


@mcp.tool()
def mommybank_repay(loan_id: int, amount_cents: int) -> dict:
    """Repay a loan (partial allowed, capped by balance and debt)."""
    return _client_ready().repay(loan_id, amount_cents)


@mcp.tool()
def mommybank_loans(username: str | None = None) -> list:
    """List loans (all visible, or one kid's)."""
    client = _client_ready()
    return client.loans(client.account_id(username) if username else None)


@mcp.tool()
def mommybank_transactions(username: str, ledger: str | None = None, limit: int = 50) -> list:
    """Ledger entries for an account; ledger: money|screen|debt."""
    client = _client_ready()
    return client.transactions(client.account_id(username), ledger, limit)


@mcp.tool()
def mommybank_users() -> list:
    """Admin: list all users."""
    return _client_ready().users()


@mcp.tool()
def mommybank_create_user(
    username: str,
    display_name: str,
    password: str,
    role: str = "user",
    ui_mode: str = "teen",
    avatar: str = "🐷",
    can_convert: bool | None = None,
    can_borrow: bool = False,
) -> dict:
    """Admin: create a user (ui_mode: teen|kid|toddler)."""
    fields = {
        "username": username, "password": password, "display_name": display_name,
        "role": role, "ui_mode": ui_mode, "avatar": avatar, "can_borrow": can_borrow,
    }
    if can_convert is not None:
        fields["can_convert"] = can_convert
    return _client_ready().create_user(**fields)


@mcp.tool()
def mommybank_set_user(username: str, **fields) -> dict:
    """Admin: update a user. Fields: display_name, ui_mode, avatar, password,
    role, can_convert, can_borrow, is_active."""
    client = _client_ready()
    uid = next((u["id"] for u in client.users() if u["username"] == username.strip().lower()), None)
    if uid is None:
        raise RuntimeError(f"No user {username!r}")
    return client.patch_user(uid, **fields)


@mcp.tool()
def mommybank_settings() -> dict:
    """Admin: current bank settings (interest, borrowing, exchange, timezone)."""
    return _client_ready().settings()


@mcp.tool()
def mommybank_set_setting(key: str, value: str) -> dict:
    """Admin: change one setting, e.g. key='savings_apr_percent' value='8.0'.

    Keys: savings_apr_percent, interest_enabled, borrow_enabled, borrow_apr_percent,
    borrow_limit_cents, exchange_base_minutes_per_dollar, min_convert_cents,
    currency_symbol, timezone. Booleans as 'true'/'false'."""
    return _client_ready().set_settings({key: value})


@mcp.tool()
def mommybank_rules() -> list:
    """List peak/off-peak exchange rules."""
    return _client_ready().rules()


@mcp.tool()
def mommybank_add_rule(
    name: str,
    days: list[int],
    start_minute: int,
    end_minute: int,
    minutes_per_dollar: float,
    priority: int = 100,
    is_active: bool = True,
) -> dict:
    """Admin: add an exchange rule. days: 0=Mon…6=Sun. Minutes are local-time
    minute-of-day; end is exclusive; end <= start crosses midnight."""
    return _client_ready().create_rule(
        name=name, days=days, start_minute=start_minute, end_minute=end_minute,
        minutes_per_dollar=minutes_per_dollar, priority=priority, is_active=is_active,
    )


@mcp.tool()
def mommybank_update_rule(rule_id: int, **fields) -> dict:
    """Admin: update an exchange rule (any of name, days, start_minute,
    end_minute, minutes_per_dollar, priority, is_active)."""
    return _client_ready().patch_rule(rule_id, **fields)


@mcp.tool()
def mommybank_delete_rule(rule_id: int) -> str:
    """Admin: delete an exchange rule."""
    _client_ready().delete_rule(rule_id)
    return f"Rule {rule_id} deleted"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
