# API, CLI & MCP Reference

Base URL: `/api/v1`. Auth: `Authorization: Bearer <jwt>` except `/auth/login` and `/health`.
Interactive OpenAPI docs: `/docs` (Swagger) when the backend runs.

Roles: 🔑 admin only · 🙂 self (own account) · 👁 any authenticated user.

## REST endpoints

### Auth
| Method | Path | Role | Body → Result |
|---|---|---|---|
| POST | `/auth/login` | — | `{username, password}` → `{token, user}` |
| GET | `/auth/me` | 👁 | → current user + account summary |
| POST | `/auth/change-password` | 👁 | `{old_password, new_password}` → 204 |

### Users
| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/users` | 🔑 | list (no hashes) |
| POST | `/users` | 🔑 | `{username, password, display_name, role?, ui_mode?, avatar?, can_convert?, can_borrow?}` — auto-creates account |
| PATCH | `/users/{id}` | 🔑 | any of `display_name, ui_mode, avatar, can_convert, can_borrow, is_active, password` (reset) |

### Accounts & balances
| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/accounts` | 🔑/self | admin: all; user: own |
| GET | `/accounts/{id}` | 🔑/self | balances **after lazy interest accrual**, projected next-day interest, debt summary |
| GET | `/overview` | 🔑 | admin dashboard aggregate (all kids + totals) |

### Money & screen-time operations (admin unless noted)
| Method | Path | Body |
|---|---|---|
| POST | `/accounts/{id}/deposit` | `{amount_cents, note?}` — money in |
| POST | `/accounts/{id}/withdraw` | `{amount_cents, note?}` — money out (no overdraft) |
| POST | `/accounts/{id}/grant-time` | `{amount_seconds, note?}` — screen time in |
| POST | `/accounts/{id}/deduct-time` | `{amount_seconds, note?}` — screen time out |
| POST | `/accounts/{id}/adjust` | `{ledger: money\|screen\|debt, amount, note?}` — explicit correction |
| POST | `/accounts/{id}/convert` | `{amount_cents, note?}` — money→time at current rate; **self allowed if `can_convert`** |
| GET | `/accounts/{id}/transactions` | `?ledger=&limit=&offset=` (self or admin) |
| GET | `/exchange/quote` | 👁 → current rate, matched rule, next windows |

### Loans
| Method | Path | Role | Notes |
|---|---|---|---|
| POST | `/loans/borrow` | 🔑/self(`can_borrow`) | `{account_id, amount_cents, note?}` — needs global `borrow_enabled`, respects debt cap |
| POST | `/loans/{id}/repay` | 🔑/self | `{amount_cents, note?}` — partial ok, uses money balance |
| GET | `/loans` | 🔑/self | `?account_id=` filter; outstanding accrues lazily |

### Settings & exchange rules
| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/settings` | 👁 | kids can see rates (values only) |
| PATCH | `/settings` | 🔑 | any subset of typed keys (see schema doc) |
| GET | `/exchange-rules` | 👁 | list |
| POST | `/exchange-rules` | 🔑 | `{name, days[], start_minute, end_minute, minutes_per_dollar, priority?, is_active?}` |
| PATCH | `/exchange-rules/{id}` | 🔑 | partial update |
| DELETE | `/exchange-rules/{id}` | 🔑 | |

Error shape: `{"detail": "message"}` with proper 4xx; 401 unauthenticated, 403 forbidden, 404 missing, 422 validation / insufficient funds.

## CLI (`mommybank`, from `backend/`)

Token cache `~/.mommybank/token.json`; or `MOMMYBANK_URL` + `MOMMYBANK_TOKEN` env.
Amounts: money as decimal dollars (`--amount 12.50` → 1250 cents) or `--cents`; time as `--minutes`/`--seconds`.

```
mommybank login USERNAME [--password ...]      mommybank whoami
mommybank overview                             mommybank balance [USERNAME]
mommybank deposit USERNAME --amount 20 --note allowance
mommybank withdraw USERNAME --amount 5
mommybank grant-time USERNAME --minutes 60
mommybank deduct-time USERNAME --minutes 15
mommybank convert USERNAME --dollars 2         # money→time at current rate (or --cents)
mommybank quote                                # current exchange rate + rule
mommybank borrow USERNAME --amount 10 --note "new game"
mommybank repay LOAN_ID --amount 5 --note "birthday money"
mommybank loans [USERNAME]
mommybank transactions USERNAME [--ledger money] [--limit 20]
mommybank users                                # list
mommybank create-user NAME --role user --ui-mode kid [--avatar 🐳] [--password ...]
mommybank set-user NAME --can-convert/--no-can-convert --can-borrow/--no-can-borrow \
                      --ui-mode teen --password ... --activate/--deactivate
mommybank settings [--json]                    # show
mommybank set-setting KEY VALUE                # e.g. savings_apr_percent 8.0
mommybank rules                                # list exchange rules
mommybank add-rule "Bedtime peak" --days 0,1,2,3,4,5,6 --start 19:00 --end 22:00 --rate 7 --priority 5
mommybank update-rule ID --rate 6 [--active/--inactive]
mommybank delete-rule ID
mommybank change-password
```

Exit codes: 0 ok, 1 usage/auth error, 2 API error (message on stderr).

## MCP server (`python -m mommybank.mcp_server`, stdio transport)

Config env: `MOMMYBANK_URL` (default `http://127.0.0.1:8000`); credentials via
`MOMMYBANK_TOKEN`, or `MOMMYBANK_USERNAME`/`MOMMYBANK_PASSWORD` (auto-login on
connect), or call the `mommybank_login` tool first.

Tools (mirror the CLI 1:1):
`mommybank_login`, `mommybank_whoami`, `mommybank_overview`, `mommybank_balance`,
`mommybank_deposit`, `mommybank_withdraw`, `mommybank_grant_time`,
`mommybank_deduct_time`, `mommybank_convert`, `mommybank_quote`,
`mommybank_borrow`, `mommybank_repay`, `mommybank_loans`, `mommybank_transactions`,
`mommybank_users`, `mommybank_create_user`, `mommybank_set_user`,
`mommybank_settings`, `mommybank_set_setting`, `mommybank_rules`,
`mommybank_add_rule`, `mommybank_update_rule`, `mommybank_delete_rule`.

Example client config (Claude Desktop / ZCode MCP):

```json
{
  "mcpServers": {
    "mommybank": {
      "command": "python",
      "args": ["-m", "mommybank.mcp_server"],
      "env": {
        "MOMMYBANK_URL": "http://host.docker.internal:8000",
        "MOMMYBANK_USERNAME": "admin",
        "MOMMYBANK_PASSWORD": "env-provided-secret"
      }
    }
  }
}
```
