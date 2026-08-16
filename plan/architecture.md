# Architecture

## System overview

```
                    ┌────────────────────────────────────────────┐
                    │                Browser (SPA)               │
                    │   Vite + React + TS + Tailwind (responsive)│
                    └───────────────┬────────────────────────────┘
                                    │ HTTPS (JWT Bearer)
        ┌───────────────────────────┼──────────────────────────────┐
        │                           │                              │
┌───────▼────────┐         ┌────────▼────────┐            ┌────────▼────────┐
│  REST API      │         │  CLI (typer)    │            │  MCP server     │
│  FastAPI       │◄────────│  mommybank …    │            │  FastMCP stdio  │
│  /api/v1/*     │         └─────────────────┘            └─────────────────┘
│                │                 ^                              ^
│  routers ──────│                 └──── shared api_client.py ────┘
│  services ─────│
│  SQLAlchemy ───│──►  SQLite (data/mommybank.db, WAL)  [Docker volume]
└────────────────┘
```

One source of truth: **everything is a REST call**. The SPA, the CLI and the MCP
server are all thin clients over the same `/api/v1` endpoints, so permission
rules, interest math and audit apply identically no matter who acts.

## Backend layering

- **routers/** — HTTP concerns only: auth deps, request validation (Pydantic), status codes.
- **services/** — pure business logic, unit-testable without HTTP:
  - `interest.py` — compound interest math, lazy accrual for savings and loans.
  - `ledger.py` — append-only transaction writes with `balance_after` snapshots.
  - `exchange.py` — exchange-rate resolution (base rate + rule matching in the configured timezone), conversion math.
  - `loans.py` — borrow/repay state machine, debt cap.
  - `settings.py` — typed settings access with defaults.
- **models.py** — SQLAlchemy 2.x declarative models; all SQL is parameter-bound by the ORM (no string-built SQL anywhere).
- **security.py** — bcrypt hashing; JWT (HS256) with expiry; FastAPI dependencies `get_current_user` / `require_admin`.

### App lifecycle

- `create_app()` builds the FastAPI app: CORS (dev origins), `/api/v1` routers, `/api/health`, and — when `frontend/dist` exists — static SPA serving with an index.html fallback for client-side routes.
- On startup: create tables if missing, run first-run seed (idempotent).
- Uvicorn serves everything in production/Docker; in dev, Vite dev server proxies `/api` to uvicorn (`vite.config.ts` server.proxy).

## Auth model

| Concern | Design |
|---|---|
| Password storage | bcrypt (cost configurable via `MOMMYBANK_BCRYPT_ROUNDS`, default 10) |
| Tokens | PyJWT HS256, 12h expiry, payload `{sub, role, exp, iat}`; client keeps it in `localStorage`, sends `Authorization: Bearer` |
| JWT secret | `MOMMYBANK_SECRET` env, else auto-generated once and stored in the `settings` table (survives restarts, never printed) |
| Roles | `admin` (parent) — everything; `user` (kid) — read own account + two opt-in actions |
| Kid permissions | `can_convert`, `can_borrow` columns on `users`, parent-toggled |
| Change password | any authenticated user, own account only |
| First-run admin | `MOMMYBANK_ADMIN_PASSWORD` env or random → printed to console once |
| Cloudflare/Gmail (future prod) | optional: when `MOMMYBANK_CF_TEAM_DOMAIN` + `MOMMYBANK_CF_AUD` are set, requests carrying a valid `Cf-Access-Jwt-Assertion` are authenticated against Cloudflare's JWKS; the verified email maps to an existing user (see deployment.md). Password auth stays available. |

## Interest engine

- **Savings**: APR `savings_apr_percent` (default 6.7), daily rate `r = apr/365`.
  On every account touch, `whole_days = floor(elapsed_since_last_interest_at / 24h)`;
  if `whole_days > 0` and balance > 0:
  `interest_cents = floor(balance * ((1+r)^days − 1))`, written as a ledger entry
  (kind `interest`), balance updated, `last_interest_at += days*24h` (remainder preserved).
- **Loans**: same lazy accrual per loan on `outstanding_cents` at the loan's own
  `apr_percent` (captured at borrow time, so later settings changes don't rewrite old debt),
  kind `loan_interest` on the `debt` ledger.
- Design notes: idempotent by construction (accrual always advances the cursor);
  deterministic and replay-safe; no background thread needed; whole days only
  (sub-day precision would make balances jittery).

## Exchange engine

- Base rate: `exchange_base_minutes_per_dollar` (default 10).
- Rules table rows: `{name, days:[0..6], start_minute, end_minute, minutes_per_dollar, priority, is_active}`.
- Resolution at time *t* (converted into the configured `timezone` setting via `zoneinfo`):
  active rules where `t.weekday() ∈ days` and `start ≤ minute_of_day < end`
  (if `end ≤ start` the window crosses midnight and matches on both sides);
  lowest `priority` number wins; no match → base rate.
- Conversion: `seconds = floor(cents * minutes_per_dollar * 60 / 100)`, requires
  `cents ≥ min_convert_cents`; the applied rate/rule is stored in the transaction `meta` JSON.

## Money & time representation

- Money: integer **cents** everywhere (API accepts `amount_cents`); formatting client-side.
- Screen time: integer **seconds** everywhere.
- The ledger stores signed `delta` + `balance_after` per row → the ledger *is* the audit trail; balances are always reconstructible.

## Frontend architecture

- **AuthContext** — login/logout, token persistence, current user; `api/client.ts` is a tiny typed fetch wrapper.
- **Routing** (`react-router-dom`): `/login`, `/` (dashboard: renders by role + ui_mode), `/account/:id` (detail + ledger + admin actions), `/overview` (admin), `/users` (admin), `/settings` (admin).
- **UI modes**: `teen` (tables, charts, full detail), `kid` (bigger type, simpler labels, emoji-forward), `toddler` (giant balances, mascot, stickers, zero tables). One `DashboardPage` dispatches to mode components.
- **Responsive**: mobile → bottom tab bar + stacked cards; ≥`lg` → sidebar + multi-column.
- **Art**: `components/art/` — parameterized SVG React components (piggy mascot with moods, coin stacks, TV, rocket, sprout, stars, wave background) + CSS keyframe animations (float, wiggle, coin-drop). No binary assets; everything recolors via Tailwind classes/currentColor.

## API/CLI/MCP parity

`services` ↔ `routers` ↔ `api_client.py`:

- `api_client.py` is the single typed REST client used by both `cli.py` (typer) and `mcp_server.py` (FastMCP). Every mutation the GUI can perform has a 1:1 CLI command and MCP tool (full tables in [api.md](api.md)).
- CLI token cache: `~/.mommybank/token.json`; MCP accepts `MOMMYBANK_TOKEN` or `MOMMYBANK_USERNAME`/`MOMMYBANK_PASSWORD` env, or an explicit `mommybank_login` tool call.

## Configuration (env)

| Var | Default | Purpose |
|---|---|---|
| `MOMMYBANK_DB` | `./data/mommybank.db` | SQLite path |
| `MOMMYBANK_SECRET` | (auto, persisted in DB) | JWT signing secret |
| `MOMMYBANK_ADMIN_PASSWORD` | (random, printed once) | First-run admin password |
| `MOMMYBANK_SEED_DEMO` | `0` | Seed demo kids (teen/kid/toddler) |
| `MOMMYBANK_DEMO_PASSWORD` | (random, printed once) | Password for demo kids |
| `MOMMYBANK_BCRYPT_ROUNDS` | `10` | bcrypt cost |
| `MOMMYBANK_CORS_ORIGINS` | `http://localhost:5173` | Comma-separated dev origins |
| `MOMMYBANK_STATIC_DIR` | `../frontend/dist` (dev) / `/app/frontend/dist` (image) | SPA build location |
| `MOMMYBANK_CF_TEAM_DOMAIN`, `MOMMYBANK_CF_AUD` | unset | Enable Cloudflare Access JWT auth |

No credentials are hard-coded in source, examples, or tests; secrets come from env or are generated at first run.
