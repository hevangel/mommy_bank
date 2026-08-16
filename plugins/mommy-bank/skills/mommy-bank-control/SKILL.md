---
name: mommy-bank-control
description: Use when the user mentions Mommy Bank, pocket money, allowance, kids' savings, screen time rules/balance, piggy bank, depositing/withdrawing for a kid, money-to-screen-time exchange rates, interest rates, borrowing/loans against allowance, or managing family bank accounts. Covers MCP tools, CLI, and REST, plus admin vs kid permissions.
---

# Controlling Mommy Bank

Mommy Bank is a family bank with two currencies: **money (integer cents)** and
**screen time (integer seconds)**. Parents (admins) manage everything; kids are
read-only except opt-in `can_convert` / `can_borrow`. Every balance change lands
in an append-only ledger. Full docs: `plan/api.md` in the
[hevangel/mommy_bank](https://github.com/hevangel/mommy_bank) repo.

## Ground rules (read first)

1. **Units**: every API/CLI amount that touches money is **cents** in MCP/REST
   (`amount_cents`); the CLI also accepts dollars (`--amount 12.50` or `--cents 1250`).
   Screen time is **seconds** in MCP/REST (`amount_seconds`), minutes in the CLI
   (`--minutes 30`). When the user says "$5", that is `amount_cents: 500`.
2. **Never ask for or echo a real password in chat.** Credentials come from env
   (`MOMMYBANK_USERNAME` / `MOMMYBANK_PASSWORD` / `MOMMYBANK_TOKEN`) or the
   CLI token cache (`~/.mommybank/token.json`) — the user manages them.
3. **Confirm before destructive/spendy actions** (withdraw, deduct-time,
   delete-rule, borrow for someone). Deposits and grants are safe defaults.
4. The bank runs on **http://127.0.0.1:8971** by default (`MOMMYBANK_URL` to
   override; docker maps host 8971 → container 8000).
5. **Check health first** if anything fails: `GET /api/health`. If down, the
   server isn't running (see repo README) — don't retry blindly.

## Choosing a surface (in order)

1. **MCP tools** (this plugin registers the `mommybank` MCP server) — preferred.
   Tool names mirror the CLI: `mommybank_overview`, `mommybank_balance`,
   `mommybank_deposit`, `mommybank_withdraw`, `mommybank_grant_time`,
   `mommybank_deduct_time`, `mommybank_convert`, `mommybank_quote`,
   `mommybank_borrow`, `mommybank_repay`, `mommybank_loans`,
   `mommybank_transactions`, `mommybank_users`, `mommybank_create_user`,
   `mommybank_set_user`, `mommybank_settings`, `mommybank_set_setting`,
   `mommybank_rules`, `mommybank_add_rule`, `mommybank_update_rule`,
   `mommybank_delete_rule`, plus `mommybank_login` / `mommybank_whoami`.
   Auth: env credentials are used automatically; otherwise call
   `mommybank_login` once per session.
2. **CLI** (`python -m mommybank.cli …`, console script `mommybank`) — same
   operations, human-readable output; login caches a token.
3. **REST** (`/api/v1/…` with `Authorization: Bearer <token>`) — fallback;
   Swagger at `/docs`. Useful one-off: `curl -s $URL/api/health`.

## Recipes

**Who am I / who's in the family** → `mommybank_whoami`, `mommybank_users`,
`mommybank_overview` (admin: every kid's money, screen time, debt).

**Weekly allowance, $20 to `teen`** →
`mommybank_deposit(username="teen", amount_cents=2000, note="weekly allowance")`.

**Screen-time reward, 45 minutes to `kid`** →
`mommybank_grant_time(username="kid", amount_seconds=2700, note="great week")`.

**"How much screen time would $5 buy?"** → `mommybank_quote` first (returns the
current rate, which peak/off-peak rule applies, when it ends, and the next
change). Then, if the kid may convert (`can_convert`):
`mommybank_convert(username, amount_cents=500)`.

**Raise savings interest to 8% APR** →
`mommybank_set_setting(key="savings_apr_percent", value="8.0")`.
Booleans are strings: `"true"` / `"false"`. Keys: `savings_apr_percent`,
`interest_enabled`, `borrow_enabled`, `borrow_apr_percent`, `borrow_limit_cents`,
`exchange_base_minutes_per_dollar`, `min_convert_cents`, `currency_symbol`,
`timezone` (IANA name — exchange windows are evaluated in this timezone, not
the server clock).

**"Screens cost double at bedtime"** → add a peak rule (fewer minutes per $1):
`mommybank_add_rule(name="Bedtime peak", days=[0,1,2,3,4,5,6],
start_minute=1140, end_minute=1320, minutes_per_dollar=5, priority=5)`.
Minutes are local minute-of-day (19:00 = 1140); `end` is exclusive;
`end <= start` crosses midnight. Lowest `priority` number wins; no rule match →
base rate. Review with `mommybank_rules`, tweak with `mommybank_update_rule`.

**Enable borrowing for a trustworthy teen** → two switches, both required:
`mommybank_set_setting(key="borrow_enabled", value="true")` (bank-wide) and
`mommybank_set_user(username="teen", can_borrow=true)` (per kid). Then the teen
borrows via `mommybank_borrow(username, amount_cents, note="new game")`; repay with
`mommybank_repay(loan_id, amount_cents, note=...)` (partial ok, capped by balance).
Debt cap default 5000 cents; loan APR is frozen at borrow time.

**Add the new kid** → `mommybank_create_user(username="lilsis",
display_name="Lil Sis", password=<from user/env>, ui_mode="kid"|"teen"|"toddler",
avatar="🐰")`. Age guide: `toddler` = read-only picture view (auto no-convert);
`kid` = simple; `teen` = full detail. Forgot a password →
`mommybank_set_user(username, password=<new>)`.

**Audit trail** → `mommybank_transactions(username, ledger="money"|"screen"|"debt",
limit=50)`; every row records `delta`, `balance_after`, who did it, and metadata
(the exchange rate used, the loan id).

## Gotchas

- Interest (default 6.7% APR, compounded daily) accrues **lazily** when an
  account is read — balances you see are always settled; there is no cron job.
- A kid logging in sees only their own account; kid tokens still can't touch
  `/settings` (kids read rates via `mommybank_quote`).
- Tokens expire after 12h — re-login on 401 rather than asking the user again.
- First-run admin password comes from `MOMMYBANK_ADMIN_PASSWORD` or is printed
  once in the server logs — never generated or stored by the agent.
- The MCP server needs the `mommybank` Python package importable
  (`pip install -e backend` in the repo) and the bank reachable at
  `MOMMYBANK_URL`.
