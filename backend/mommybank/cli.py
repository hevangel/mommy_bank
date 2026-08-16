"""Mommy Bank CLI — everything the GUI can do, from the terminal.

Token cache: ~/.mommybank/token.json  (or MOMMYBANK_URL + MOMMYBANK_TOKEN env)
"""
from __future__ import annotations

import json as _json
import os
from pathlib import Path

import typer

from .api_client import ApiError, MommyBankClient, dollars_to_cents

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Mommy Bank family bank CLI")

_TOKEN_FILE = Path.home() / ".mommybank" / "token.json"


def _load_client() -> MommyBankClient:
    token = os.environ.get("MOMMYBANK_TOKEN", "")
    base = os.environ.get("MOMMYBANK_URL", "")
    if not token and _TOKEN_FILE.exists():
        try:
            saved = _json.loads(_TOKEN_FILE.read_text())
            token = saved.get("token", "")
            base = base or saved.get("base_url", "")
        except (ValueError, OSError):
            pass
    return MommyBankClient(base_url=base or None, token=token)


def _save_token(client: MommyBankClient) -> None:
    _TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    _TOKEN_FILE.write_text(_json.dumps({"base_url": client.base_url, "token": client.token}))


def _die(e: Exception) -> None:
    typer.secho(str(e), fg=typer.colors.RED, err=True)
    raise typer.Exit(code=2)


def _fmt_money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) / 100:,.2f}"


def _fmt_dur(seconds: int) -> str:
    if seconds < 0:
        return "-"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m{ s:02d}s" if s else f"{m}m"


def _as_json(obj) -> None:
    typer.echo(_json.dumps(obj, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------- auth


@app.command()
def login(
    username: str = typer.Argument(...),
    password: str = typer.Option("", "--password", "-p", help="Omit to be prompted"),
):
    """Log in and cache the token locally."""
    if not password:
        password = typer.prompt("Password", hide_input=True)
    client = MommyBankClient()
    try:
        data = client.login(username, password)
    except ApiError as e:
        _die(e)
    _save_token(client)
    typer.secho(f"Welcome, {data['user']['display_name']}! 🐷", fg=typer.colors.GREEN)


@app.command()
def whoami():
    """Show the logged-in user."""
    client = _load_client()
    try:
        me = client.me()
    except ApiError as e:
        _die(e)
    _as_json(me)


@app.command()
def change_password():
    """Change your own password."""
    client = _load_client()
    old = typer.prompt("Old password", hide_input=True)
    new = typer.prompt("New password", hide_input=True, confirmation_prompt=True)
    try:
        client.change_password(old, new)
    except ApiError as e:
        _die(e)
    typer.secho("Password changed ✅", fg=typer.colors.GREEN)


# ---------------------------------------------------------------- viewing


@app.command()
def overview():
    """Admin: all kids' balances + bank totals."""
    client = _load_client()
    try:
        data = client.overview()
    except ApiError as e:
        _die(e)
    for a in data["accounts"]:
        debt = f"  debt {_fmt_money(a['debt_cents'])}" if a["debt_cents"] else ""
        typer.echo(
            f"{a['avatar']} {a['display_name']:<18} money {_fmt_money(a['money_cents']):>10}"
            f"  time {_fmt_dur(a['screen_seconds']):>8}{debt}"
        )
    t = data["totals"]
    typer.secho(
        f"\nBank totals: money {_fmt_money(t['money_cents'])} · "
        f"screen time {_fmt_dur(t['screen_seconds'])} · debt {_fmt_money(t['debt_cents'])}",
        fg=typer.colors.CYAN,
    )


@app.command()
def balance(username: str = typer.Argument(None)):
    """Show balance(s). No argument = everything you may see."""
    client = _load_client()
    try:
        accounts = client.accounts()
    except ApiError as e:
        _die(e)
    if username:
        target = username.strip().lower()
        accounts = [a for a in accounts if a["username"] == target]
        if not accounts:
            _die(ApiError(404, f"No visible account for {username!r}"))
    for a in accounts:
        typer.echo(
            f"{a['avatar']} {a['display_name']:<18} money {_fmt_money(a['money_cents']):>10}  "
            f"screen {_fmt_dur(a['screen_seconds']):>8}  "
            f"(next week +{_fmt_money(a['next_week_interest_cents'])}, "
            f"next year +{_fmt_money(a['next_year_interest_cents'])} interest)"
        )


@app.command()
def quote():
    """Current money→screen-time exchange rate."""
    client = _load_client()
    try:
        q = client.quote()
    except ApiError as e:
        _die(e)
    rule = f" ({q['rule']['name']})" if q["rule"] else " (base rate)"
    typer.echo(f"Rate: {q['rate']} min per $1{rule}")
    if q.get("until"):
        typer.echo(f"Until: {q['until']}")
    if q.get("next_change"):
        typer.echo(f"Next change: {q['next_change']['at']} → {q['next_change']['rate']} min/$")


# ---------------------------------------------------------------- money & time


def _amount_cents(amount: str, cents: int) -> int:
    if cents:
        return cents
    if not amount:
        _die(ApiError(400, "Provide --amount DOLLARS or --cents"))
    try:
        return dollars_to_cents(amount)
    except ValueError as e:
        _die(e)


def _seconds(minutes: float, seconds: int) -> int:
    if seconds:
        return seconds
    if minutes:
        return int(minutes * 60)
    _die(ApiError(400, "Provide --minutes or --seconds"))


@app.command()
def deposit(
    username: str,
    amount: str = typer.Option("", "--amount", "-a", help="Dollars, e.g. 12.50"),
    cents: int = typer.Option(0, "--cents"),
    note: str = typer.Option("", "--note", "-n"),
):
    """Admin: deposit money."""
    client = _load_client()
    try:
        res = client.deposit(client.account_id(username), _amount_cents(amount, cents), note)
    except (ApiError, ValueError) as e:
        _die(e)
    typer.secho(f"Deposited → new balance {_fmt_money(res['money_cents'])} 💰", fg=typer.colors.GREEN)


@app.command()
def withdraw(
    username: str,
    amount: str = typer.Option("", "--amount", "-a"),
    cents: int = typer.Option(0, "--cents"),
    note: str = typer.Option("", "--note", "-n"),
):
    """Admin: withdraw money."""
    client = _load_client()
    try:
        res = client.withdraw(client.account_id(username), _amount_cents(amount, cents), note)
    except (ApiError, ValueError) as e:
        _die(e)
    typer.secho(f"Withdrew → new balance {_fmt_money(res['money_cents'])}", fg=typer.colors.GREEN)


@app.command()
def grant_time(
    username: str,
    minutes: float = typer.Option(0.0, "--minutes", "-m"),
    seconds: int = typer.Option(0, "--seconds"),
    note: str = typer.Option("", "--note", "-n"),
):
    """Admin: grant screen time."""
    client = _load_client()
    try:
        res = client.grant_time(client.account_id(username), _seconds(minutes, seconds), note)
    except (ApiError, ValueError) as e:
        _die(e)
    typer.secho(f"Granted → {_fmt_dur(res['screen_seconds'])} of screen time 📺", fg=typer.colors.GREEN)


@app.command()
def deduct_time(
    username: str,
    minutes: float = typer.Option(0.0, "--minutes", "-m"),
    seconds: int = typer.Option(0, "--seconds"),
    note: str = typer.Option("", "--note", "-n"),
):
    """Admin: deduct screen time."""
    client = _load_client()
    try:
        res = client.deduct_time(client.account_id(username), _seconds(minutes, seconds), note)
    except (ApiError, ValueError) as e:
        _die(e)
    typer.secho(f"Deducted → {_fmt_dur(res['screen_seconds'])} left", fg=typer.colors.GREEN)


@app.command()
def convert(
    username: str,
    dollars: str = typer.Option("", "--dollars", "--amount", "-a"),
    cents: int = typer.Option(0, "--cents"),
    note: str = typer.Option("", "--note", "-n"),
):
    """Convert money → screen time at the current rate (kid self-service if allowed)."""
    client = _load_client()
    try:
        res = client.convert(client.account_id(username), _amount_cents(dollars, cents), note)
    except (ApiError, ValueError) as e:
        _die(e)
    typer.secho(
        f"Converted at {res['rate_minutes_per_dollar']} min/$ → +{res['seconds'] // 60} min "
        f"(now {_fmt_dur(res['screen_seconds'])}) 📺",
        fg=typer.colors.GREEN,
    )


# ---------------------------------------------------------------- loans


@app.command()
def borrow(
    username: str,
    amount: str = typer.Option("", "--amount", "-a"),
    cents: int = typer.Option(0, "--cents"),
    note: str = typer.Option("", "--note", "-n"),
):
    """Borrow money (opens a loan at the borrow APR)."""
    client = _load_client()
    try:
        loan = client.borrow(client.account_id(username), _amount_cents(amount, cents), note)
    except (ApiError, ValueError) as e:
        _die(e)
    typer.secho(
        f"Loan #{loan['id']}: borrowed {_fmt_money(loan['principal_cents'])} at "
        f"{loan['apr_percent']}% APR → owes {_fmt_money(loan['outstanding_cents'])} 🚀",
        fg=typer.colors.GREEN,
    )


@app.command()
def repay(
    loan_id: int,
    amount: str = typer.Option("", "--amount", "-a"),
    cents: int = typer.Option(0, "--cents"),
    note: str = typer.Option("", "--note", "-n"),
):
    """Repay a loan (partial allowed)."""
    client = _load_client()
    try:
        res = client.repay(loan_id, _amount_cents(amount, cents), note)
    except (ApiError, ValueError) as e:
        _die(e)
    typer.secho(
        f"Repaid {_fmt_money(res['repaid_cents'])} → owes {_fmt_money(res['loan']['outstanding_cents'])}",
        fg=typer.colors.GREEN,
    )


@app.command()
def loans(username: str = typer.Argument(None)):
    """List loans (yours, or any account for admins)."""
    client = _load_client()
    try:
        account_id = client.account_id(username) if username else None
        rows = client.loans(account_id)
    except ApiError as e:
        _die(e)
    if not rows:
        typer.echo("No loans 🎉")
        return
    for l in rows:
        typer.echo(
            f"#{l['id']} {l['username']:<10} {_fmt_money(l['principal_cents'])} @ {l['apr_percent']}% APR  "
            f"owes {_fmt_money(l['outstanding_cents'])}  {l['status']}"
        )


# ---------------------------------------------------------------- history


@app.command()
def transactions(
    username: str = typer.Argument(...),
    ledger: str = typer.Option("", "--ledger", "-l", help="money|screen|debt"),
    limit: int = typer.Option(20, "--limit"),
    as_json: bool = typer.Option(False, "--json"),
):
    """Show the ledger for an account."""
    client = _load_client()
    try:
        rows = client.transactions(client.account_id(username), ledger or None, limit)
    except ApiError as e:
        _die(e)
    if as_json:
        _as_json(rows)
        return
    for t in rows:
        amt = _fmt_money(t["delta"]) if t["ledger"] != "screen" else _fmt_dur(abs(t["delta"]))
        typer.echo(f"{t['created_at'][:16]}  {t['ledger']:<6} {t['kind']:<12} {amt:>10}  {t['note']}")


# ---------------------------------------------------------------- admin: users


@app.command(name="users")
def users_cmd(as_json: bool = typer.Option(False, "--json")):
    """Admin: list users."""
    client = _load_client()
    try:
        rows = client.users()
    except ApiError as e:
        _die(e)
    if as_json:
        _as_json(rows)
        return
    for u in rows:
        flags = ("convert" if u["can_convert"] else "") + (" borrow" if u["can_borrow"] else "")
        typer.echo(
            f"{u['avatar']} {u['username']:<12} {u['display_name']:<20} {u['role']:<5} "
            f"{u['ui_mode']:<8} {flags} {'' if u['is_active'] else '(inactive)'}"
        )


@app.command(name="create-user")
def create_user(
    username: str,
    display_name: str = typer.Option(..., "--display-name", "-n"),
    password: str = typer.Option("", "--password", "-p", help="Omit to be prompted"),
    role: str = typer.Option("user", "--role"),
    ui_mode: str = typer.Option("teen", "--ui-mode", help="teen|kid|toddler"),
    avatar: str = typer.Option("🐷", "--avatar"),
    can_convert: bool = typer.Option(None, "--can-convert/--no-can-convert"),
    can_borrow: bool = typer.Option(False, "--can-borrow/--no-can-borrow"),
):
    """Admin: create a user (account is created automatically)."""
    client = _load_client()
    if not password:
        password = typer.prompt("Password", hide_input=True, confirmation_prompt=True)
    fields = {
        "username": username,
        "password": password,
        "display_name": display_name,
        "role": role,
        "ui_mode": ui_mode,
        "avatar": avatar,
        "can_borrow": can_borrow,
    }
    if can_convert is not None:
        fields["can_convert"] = can_convert
    try:
        user = client.create_user(**fields)
    except ApiError as e:
        _die(e)
    typer.secho(f"Created {user['avatar']} {user['username']} ({user['ui_mode']} mode) ✅", fg=typer.colors.GREEN)


@app.command(name="set-user")
def set_user(
    username: str,
    display_name: str = typer.Option(None, "--display-name", "-n"),
    ui_mode: str = typer.Option(None, "--ui-mode"),
    avatar: str = typer.Option(None, "--avatar"),
    password: str = typer.Option("", "--password", "-p", help="Reset password (omit to keep)"),
    role: str = typer.Option(None, "--role"),
    can_convert: bool = typer.Option(None, "--can-convert/--no-can-convert"),
    can_borrow: bool = typer.Option(None, "--can-borrow/--no-can-borrow"),
    activate: bool = typer.Option(None, "--activate/--deactivate"),
):
    """Admin: update a user."""
    client = _load_client()
    uid = next((u["id"] for u in client.users() if u["username"] == username.strip().lower()), None)
    if uid is None:
        _die(ApiError(404, f"No user {username!r}"))
    fields: dict = {}
    for key, val in (
        ("display_name", display_name), ("ui_mode", ui_mode), ("avatar", avatar),
        ("role", role), ("can_convert", can_convert), ("can_borrow", can_borrow),
    ):
        if val is not None:
            fields[key] = val
    if activate is not None:
        fields["is_active"] = activate
    if password:
        fields["password"] = password
    if not fields:
        _die(ApiError(400, "Nothing to update"))
    try:
        client.patch_user(uid, **fields)
    except ApiError as e:
        _die(e)
    typer.secho(f"Updated {username} ✅", fg=typer.colors.GREEN)


# ---------------------------------------------------------------- admin: settings & rules


@app.command()
def settings(as_json: bool = typer.Option(False, "--json")):
    """Admin: show bank settings."""
    client = _load_client()
    try:
        data = client.settings()
    except ApiError as e:
        _die(e)
    if as_json:
        _as_json(data)
        return
    for k, v in data.items():
        typer.echo(f"{k:<34} {v}")


@app.command(name="set-setting")
def set_setting(key: str, value: str):
    """Admin: change one setting, e.g. set-setting savings_apr_percent 8.0"""
    client = _load_client()
    try:
        client.set_settings({key: value})
    except ApiError as e:
        _die(e)
    typer.secho(f"{key} = {value} ✅", fg=typer.colors.GREEN)


def _parse_hhmm(text: str) -> int:
    try:
        h, m = text.strip().split(":")
        minute = int(h) * 60 + int(m)
    except ValueError:
        raise ValueError(f"Time must be HH:MM, got {text!r}")
    if not (0 <= minute <= 1439):
        raise ValueError("Time out of range")
    return minute


def _parse_days(text: str) -> list[int]:
    out = []
    for part in text.split(","):
        d = int(part.strip())
        if not (0 <= d <= 6):
            raise ValueError("Days are 0=Mon … 6=Sun")
        out.append(d)
    return out


@app.command()
def rules():
    """List exchange rate rules."""
    client = _load_client()
    try:
        rows = client.rules()
    except ApiError as e:
        _die(e)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for r in rows:
        days = ",".join(day_names[d] for d in r["days"])
        typer.echo(
            f"#{r['id']} {r['name']:<26} {r['minutes_per_dollar']:>5.1f} min/$  {days:<30} "
            f"{r['start_minute'] // 60:02d}:{r['start_minute'] % 60:02d}-"
            f"{r['end_minute'] // 60:02d}:{r['end_minute'] % 60:02d}  "
            f"prio {r['priority']}  {'on' if r['is_active'] else 'OFF'}"
        )


@app.command(name="add-rule")
def add_rule(
    name: str,
    days: str = typer.Option("0,1,2,3,4,5,6", "--days", help="0=Mon … 6=Sun, comma-separated"),
    start: str = typer.Option(..., "--start", help="HH:MM local"),
    end: str = typer.Option(..., "--end", help="HH:MM local (exclusive; earlier than start = crosses midnight)"),
    rate: float = typer.Option(..., "--rate", help="minutes per dollar"),
    priority: int = typer.Option(100, "--priority", help="lower wins"),
    inactive: bool = typer.Option(False, "--inactive"),
):
    """Admin: add a peak/off-peak exchange rule."""
    client = _load_client()
    try:
        fields = {
            "name": name, "days": _parse_days(days), "start_minute": _parse_hhmm(start),
            "end_minute": _parse_hhmm(end) if _parse_hhmm(end) > 0 else 1440,
            "minutes_per_dollar": rate, "priority": priority, "is_active": not inactive,
        }
        client.create_rule(**fields)
    except (ApiError, ValueError) as e:
        _die(e)
    typer.secho(f"Rule '{name}' added ✅", fg=typer.colors.GREEN)


@app.command(name="update-rule")
def update_rule(
    rule_id: int,
    name: str = typer.Option(None, "--name"),
    days: str = typer.Option(None, "--days"),
    start: str = typer.Option(None, "--start"),
    end: str = typer.Option(None, "--end"),
    rate: float = typer.Option(None, "--rate"),
    priority: int = typer.Option(None, "--priority"),
    active: bool = typer.Option(None, "--active/--inactive"),
):
    """Admin: update an exchange rule."""
    client = _load_client()
    fields: dict = {}
    if name is not None:
        fields["name"] = name
    if days is not None:
        fields["days"] = _parse_days(days)
    if start is not None:
        fields["start_minute"] = _parse_hhmm(start)
    if end is not None:
        fields["end_minute"] = _parse_hhmm(end) if _parse_hhmm(end) > 0 else 1440
    if rate is not None:
        fields["minutes_per_dollar"] = rate
    if priority is not None:
        fields["priority"] = priority
    if active is not None:
        fields["is_active"] = active
    if not fields:
        _die(ApiError(400, "Nothing to update"))
    try:
        client.patch_rule(rule_id, **fields)
    except ApiError as e:
        _die(e)
    typer.secho(f"Rule #{rule_id} updated ✅", fg=typer.colors.GREEN)


@app.command(name="delete-rule")
def delete_rule(rule_id: int):
    """Admin: delete an exchange rule."""
    client = _load_client()
    try:
        client.delete_rule(rule_id)
    except ApiError as e:
        _die(e)
    typer.secho(f"Rule #{rule_id} deleted 🗑️", fg=typer.colors.GREEN)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
