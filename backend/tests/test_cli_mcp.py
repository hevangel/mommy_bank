"""CLI and MCP surfaces run against the in-process ASGI app (full parity smoke)."""
from __future__ import annotations

import asyncio
import json

import pytest
from typer.testing import CliRunner

import mommybank.cli as cli_mod
from mommybank import mcp_server

from .conftest import ADMIN_PASSWORD, ADMIN_USERNAME, gen_password, unique_name


@pytest.fixture()
def runner(monkeypatch, tmp_path, asgi_api_client):
    monkeypatch.setattr(cli_mod, "_TOKEN_FILE", tmp_path / "token.json")
    monkeypatch.delenv("MOMMYBANK_TOKEN", raising=False)
    monkeypatch.delenv("MOMMYBANK_USERNAME", raising=False)
    monkeypatch.delenv("MOMMYBANK_PASSWORD", raising=False)
    return CliRunner()


def _login(runner):
    result = runner.invoke(cli_mod.app, ["login", ADMIN_USERNAME, "--password", ADMIN_PASSWORD])
    assert result.exit_code == 0, result.output
    return result


def test_cli_login_and_whoami(runner):
    _login(runner)
    result = runner.invoke(cli_mod.app, ["whoami"])
    assert result.exit_code == 0, result.output
    assert ADMIN_USERNAME in result.output


def test_cli_full_bank_flow(runner, asgi_api_client):
    _login(runner)
    kid = unique_name("cli")
    pw = gen_password()
    r = runner.invoke(cli_mod.app, [
        "create-user", kid, "--display-name", "CLI Kid", "--ui-mode", "kid",
        "--password", pw, "--avatar", "🦊",
    ])
    assert r.exit_code == 0, r.output
    r = runner.invoke(cli_mod.app, ["deposit", kid, "--amount", "20", "--note", "chores"])
    assert r.exit_code == 0, r.output
    r = runner.invoke(cli_mod.app, ["balance", kid])
    assert r.exit_code == 0
    assert "$20.00" in r.output
    r = runner.invoke(cli_mod.app, ["withdraw", kid, "--cents", "500"])
    assert r.exit_code == 0
    r = runner.invoke(cli_mod.app, ["grant-time", kid, "--minutes", "45"])
    assert r.exit_code == 0
    r = runner.invoke(cli_mod.app, ["convert", kid, "--dollars", "1"])
    assert r.exit_code == 0, r.output
    r = runner.invoke(cli_mod.app, ["balance", kid])
    assert "14.00" in r.output  # 20.00 - 5.00 withdrew - 1.00 converted
    r = runner.invoke(cli_mod.app, ["transactions", kid, "--limit", "10"])
    assert r.exit_code == 0
    assert "deposit" in r.output and "convert_out" in r.output
    r = runner.invoke(cli_mod.app, ["overview"])
    assert r.exit_code == 0
    r = runner.invoke(cli_mod.app, ["quote"])
    assert r.exit_code == 0 and "min per $1" in r.output


def test_cli_settings_and_rules(runner, asgi_api_client):
    _login(runner)
    r = runner.invoke(cli_mod.app, ["settings"])
    assert r.exit_code == 0 and "savings_apr_percent" in r.output
    r = runner.invoke(cli_mod.app, ["set-setting", "savings_apr_percent", "7.3"])
    assert r.exit_code == 0
    r = runner.invoke(cli_mod.app, ["settings"])
    assert "7.3" in r.output
    r = runner.invoke(cli_mod.app, ["add-rule", "CLI rule", "--days", "5,6", "--start", "07:00",
                                    "--end", "09:00", "--rate", "14", "--priority", "30"])
    assert r.exit_code == 0, r.output
    r = runner.invoke(cli_mod.app, ["rules"])
    assert "CLI rule" in r.output
    rule_id = next(line.split()[0][1:] for line in r.output.splitlines() if "CLI rule" in line)
    r = runner.invoke(cli_mod.app, ["update-rule", rule_id, "--rate", "14.5"])
    assert r.exit_code == 0
    r = runner.invoke(cli_mod.app, ["delete-rule", rule_id])
    assert r.exit_code == 0


def test_cli_loans_flow(runner, asgi_api_client):
    _login(runner)
    kid = unique_name("loan")
    runner.invoke(cli_mod.app, ["create-user", kid, "--display-name", "Loan Kid",
                                "--password", gen_password(), "--can-borrow"])
    runner.invoke(cli_mod.app, ["set-setting", "borrow_enabled", "true"])
    r = runner.invoke(cli_mod.app, ["borrow", kid, "--amount", "5"])
    assert r.exit_code == 0, r.output
    r = runner.invoke(cli_mod.app, ["loans", kid])
    assert "owes $5.00" in r.output
    loan_id = r.output.splitlines()[0].split()[0].lstrip("#")
    r = runner.invoke(cli_mod.app, ["repay", loan_id, "--amount", "2"])
    assert r.exit_code == 0 and "$3.00" in r.output
    runner.invoke(cli_mod.app, ["set-setting", "borrow_enabled", "false"])


def test_cli_error_exit_code(runner, asgi_api_client):
    _login(runner)
    r = runner.invoke(cli_mod.app, ["deposit", "ghost-user-zz", "--amount", "5"])
    assert r.exit_code == 2


# ---------------------------------------------------------------- MCP


def _parse_texts(texts: list[str]):
    parsed = []
    for t in texts:
        try:
            parsed.append(json.loads(t))
        except (ValueError, TypeError):
            return texts[0] if texts else None
    return parsed[0] if len(parsed) == 1 else parsed


def _call_tool(name: str, args: dict):
    result = asyncio.run(mcp_server.mcp.call_tool(name, args))
    # normalize across SDK versions: CallToolResult (.data/.structured_content) vs list[Content]
    data = getattr(result, "data", None)
    if data is not None:
        return data
    sc = getattr(result, "structured_content", None)
    if isinstance(sc, dict):
        return sc.get("result") if set(sc.keys()) == {"result"} else sc
    items = result if isinstance(result, list) else (getattr(result, "content", None) or [])
    texts = [c.text for c in items if isinstance(getattr(c, "text", None), str)]
    if texts:
        return _parse_texts(texts)
    return result


@pytest.fixture()
def mcp_logged_in(asgi_api_client, monkeypatch):
    client = asgi_api_client()
    client.login(ADMIN_USERNAME, ADMIN_PASSWORD)
    monkeypatch.setattr(mcp_server, "_client", client)
    return client


def test_mcp_login_tool(asgi_api_client, monkeypatch):
    fresh = asgi_api_client()
    monkeypatch.setattr(mcp_server, "_client", fresh)
    out = _call_tool("mommybank_login", {"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
    assert out["user"]["role"] == "admin"


def test_mcp_bank_flow(mcp_logged_in):
    kid = unique_name("mcp")
    out = _call_tool("mommybank_create_user", {
        "username": kid, "display_name": "MCP Kid", "password": gen_password(), "ui_mode": "teen",
    })
    assert out["username"] == kid
    out = _call_tool("mommybank_deposit", {"username": kid, "amount_cents": 3000, "note": "birthday"})
    assert out["money_cents"] == 3000
    out = _call_tool("mommybank_grant_time", {"username": kid, "amount_seconds": 1800})
    assert out["screen_seconds"] == 1800
    q = _call_tool("mommybank_quote", {})
    out = _call_tool("mommybank_convert", {"username": kid, "amount_cents": 100})
    assert out["seconds"] == int(100 * q["rate"] * 60 / 100)
    out = _call_tool("mommybank_balance", {"username": kid})
    assert out["money_cents"] == 2900
    out = _call_tool("mommybank_quote", {})
    assert out["rate"] > 0
    out = _call_tool("mommybank_transactions", {"username": kid, "limit": 10})
    assert isinstance(out, list) and len(out) >= 4
    out = _call_tool("mommybank_overview", {})
    assert "totals" in out
    out = _call_tool("mommybank_settings", {})
    assert "savings_apr_percent" in out
    out = _call_tool("mommybank_set_setting", {"key": "savings_apr_percent", "value": "6.9"})
    assert out["savings_apr_percent"] == 6.9
    _call_tool("mommybank_set_setting", {"key": "savings_apr_percent", "value": "6.7"})


def test_mcp_loans_flow(mcp_logged_in):
    kid = unique_name("mcpl")
    _call_tool("mommybank_create_user", {
        "username": kid, "display_name": "MCP Loan", "password": gen_password(), "can_borrow": True,
    })
    _call_tool("mommybank_set_setting", {"key": "borrow_enabled", "value": "true"})
    loan = _call_tool("mommybank_borrow", {"username": kid, "amount_cents": 2000})
    assert loan["outstanding_cents"] == 2000
    repaid = _call_tool("mommybank_repay", {"loan_id": loan["id"], "amount_cents": 500})
    assert repaid["loan"]["outstanding_cents"] == 1500
    _call_tool("mommybank_set_setting", {"key": "borrow_enabled", "value": "false"})
