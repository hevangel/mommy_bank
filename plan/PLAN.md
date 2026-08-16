# Mommy Bank — Master Plan

> A family bank where the currency is **money** and **screen time**.
> Parents (admins) run the bank; kids (users) watch their savings grow.

Status: **BUILT, TESTED & QA'd** — 68 backend tests + 19 frontend tests green, 13-point browser QA pass (3 bugs found → fixed → re-verified), Docker image validated. See [testing-and-qa.md](testing-and-qa.md) and [../qa/QA_REPORT.md](../qa/QA_REPORT.md).

## 1. Product goals

- A real-feeling online banking website for one family:
  - **Money account** per kid: deposits, withdrawals, interest.
  - **Screen-time account** per kid: grants, deductions, money→minutes conversion.
  - **Interest**: daily compounding, admin-configurable (default **6.7% APR**).
  - **Borrowing** (optional, off by default): admin-configurable rate, default **10% APR** daily compounding, with a debt cap.
  - **Money→screen-time exchange**: default **$1 = 10 minutes**, with **peak / off-peak rules** (weekday/weekend + intra-day windows, e.g. bedtime = expensive, weekend morning = bonus).
- Three age experiences from one codebase: **teen** (full detail), **kid** (simplified, big buttons), **toddler** (giant read-only numbers + stickers).
- Roles: **admin (parent)** — full control; **user (kid)** — read-only, plus *opt-in* self-service actions (convert money→time, borrow) controlled per kid by the parent.
- Works on desktop and mobile browsers.
- Every GUI capability is also available via **CLI** and **MCP server** (for AI agents like Claude/ZCode).
- Runs locally for development (`vite` dev server + `uvicorn`) and in **Docker** (single container, SQLite on a volume) for easy EC2 deployment.

## 2. Tech stack (decisions)

| Layer | Choice | Why |
|---|---|---|
| Backend | **Python 3.11 + FastAPI** | Async-friendly, automatic OpenAPI docs, Pydantic validation, standard for MCP ecosystem |
| DB | **SQLite** (via SQLAlchemy 2.x ORM) | Zero-ops, single file on a Docker volume, plenty for a family. Parameter-bound SQL everywhere via ORM |
| Auth | Password login (bcrypt) + **JWT** bearer tokens (PyJWT) | Simple, stateless; secret from env or auto-generated & persisted in DB |
| Frontend | **Vite + React 18 + TypeScript** | Requested Vite; React ecosystem + TS safety. State = React context + fetch (no heavy state lib) |
| Styling | **Tailwind CSS 3** | Rapid responsive (mobile-first) styling, custom pastel palette |
| Art | **Hand-drawn SVG React components** (piggy mascot, coins, TV/clock, rocket, sprout) + CSS animations | Cute, zero image assets, themeable |
| Charts | Hand-rolled SVG sparkline/bars | No chart library, keeps bundle tiny |
| CLI | **Typer** talking to the REST API over `httpx` | Same API as GUI = one source of truth; works remotely |
| MCP | **FastMCP** (official `mcp` Python SDK), stdio transport, talks to the REST API | AI agents get every GUI capability |
| Tests | **pytest** (backend), **vitest + Testing Library** (frontend), **browser QA pass** | Layered test pyramid |
| Deploy | Multi-stage **Dockerfile** (node build → python runtime, uvicorn serves API + SPA), `docker-compose.yml` | Single container, volume for `/app/data` |

## 3. Key product decisions (made autonomously, easy to change)

1. **"6.7% daily compound" interpreted as 6.7% APR compounded daily** (daily rate = 6.7%/365). Likewise borrowing 10% APR compounded daily. A literal 6.7%-per-day rate would explode balances absurdly; APR is what a "real online bank" means.
2. **Interest accrues lazily on read/touch** (no background worker). Any time an account is fetched or mutated, whole elapsed 24h periods are settled and written to the ledger. Correct for a low-traffic family bank and perfect for serverless-ish deployment.
3. **Kids are read-only by default, with two opt-in self-service permissions**: `can_convert` (convert own money→screen time; on by default for teen/kid, off for toddler) and `can_borrow` (off by default for everyone). This preserves "user only has read access" while making the incentive loop (save money → convert to screen time) usable without the parent in the loop. Everything else (deposit/withdraw/grant/deduct/settings/users) is admin-only.
4. **Screen time is stored in seconds**, money in integer cents — no floats in the ledger, ever. Rates are float only at calculation time, results floored.
5. **Exchange is one-way** (money → time). If a parent needs to reverse, they deduct screen time and deposit money manually.
6. **Peak/off-peak rules**: a table of rules `{days-of-week, start–end minute-of-day, minutes-per-dollar, priority}`. Highest-priority active rule matching *now* (in the configured IANA timezone) wins; otherwise the base rate. Windows may cross midnight (e.g. 20:00→06:00). Seeded examples: after-school off-peak bonus, bedtime peak, weekend-morning bonus.
7. **Debt model**: borrowing credits money to the balance and opens a loan with its own APR; interest accrues on outstanding; repayments are partial-friendly. All debt movements are ledger entries (`debt` ledger) so the audit trail is one table.
8. **UI modes** (`teen` / `kid` / `toddler`) are a per-user property driving dashboard rendering only — same API, same data.
9. **First-run credentials are never hard-coded**: the initial admin password comes from `MOMMYBANK_ADMIN_PASSWORD` env var, or is generated randomly and printed **once** to the server console. Demo kids can be seeded with `MOMMYBANK_SEED_DEMO=1` (password also from env or random-printed).
10. **Cloudflare/Google auth is designed-for but off by default** (local password auth is the base layer). See [deployment.md](deployment.md#production-ec2--cloudflare) — the app can validate Cloudflare Access JWTs in front of the same user accounts when env flags are set.

## 4. Feature checklist

### Money bank
- [x] Deposit / withdraw / adjust (admin)
- [x] Daily compound interest, admin-set APR, lazy accrual, ledger entries with `balance_after`
- [x] Transaction history with filters, running-balance sparkline
- [x] Borrowing (admin-enabled + per-kid permission), loan list, partial repay, loan interest accrual, debt cap

### Screen-time bank
- [x] Grant / deduct time (admin)
- [x] Money→time conversion at the *current* effective rate, quote endpoint, rate breakdown shown before converting
- [x] Peak/off-peak exchange rules (weekday/weekend, intra-day windows, cross-midnight), admin CRUD
- [x] Time balance shown in age-appropriate units (h/m, minutes, giant clock)

### Access & management
- [x] SQLite password auth (bcrypt), JWT sessions, change-own-password
- [x] Admin user management: create kid, set UI mode + avatar emoji + permissions, reset password, deactivate
- [x] Settings: interest APR, borrow on/off + APR + cap, base exchange rate, currency symbol, timezone
- [x] Admin overview dashboard (all kids, balances, debt, recent activity)

### Surfaces (parity: GUI = CLI = MCP)
- [x] REST API (OpenAPI docs at `/docs`)
- [x] CLI: `mommybank login|whoami|overview|balance|deposit|withdraw|grant-time|deduct-time|convert|quote|borrow|repay|loans|transactions|users|create-user|set-user|settings|rules|...`
- [x] MCP server (`python -m mommybank.mcp_server`) with the same toolset

### Platform
- [x] Responsive desktop + mobile (bottom tab bar on mobile, sidebar on desktop)
- [x] Cute hand-drawn SVG mascot & icons, pastel theme, animations
- [x] Docker single-container build, compose file with volume + healthcheck
- [x] pytest suite (unit + API integration) and vitest suite; browser QA with screenshots

## 5. Repository layout

```
mommy_bank/
├── plan/                  # this plan + architecture, schema, API, UX, QA, deployment docs
├── backend/
│   ├── pyproject.toml     # installable package `mommybank` (API + CLI + MCP)
│   ├── mommybank/
│   │   ├── main.py        # FastAPI app factory, SPA static serving
│   │   ├── config.py      # env-driven settings
│   │   ├── db.py          # engine/session, pragmas (WAL, FK)
│   │   ├── models.py      # SQLAlchemy models
│   │   ├── security.py    # bcrypt, JWT, deps (get_current_user, require_admin)
│   │   ├── seed.py        # first-run bootstrap (settings, admin, demo kids, rules)
│   │   ├── services/      # interest, ledger, exchange, loans, settings (pure logic)
│   │   ├── routers/       # auth, users, accounts, transactions, loans, settings, exchange
│   │   ├── api_client.py  # shared httpx REST client (used by CLI + MCP)
│   │   ├── cli.py         # typer CLI
│   │   └── mcp_server.py  # FastMCP server (stdio)
│   └── tests/             # pytest suite
├── frontend/
│   └── src/
│       ├── api/           # typed REST client + auth context
│       ├── components/    # ui/ (cards, buttons, charts…) and art/ (SVG mascots/icons)
│       ├── pages/         # Login, Dashboard (3 modes), Account detail, Users, Settings, Overview
│       └── utils/         # money/duration formatting
├── qa/                    # QA script notes + screenshots from the browser pass
├── Dockerfile             # multi-stage: node build → python runtime
├── docker-compose.yml
└── README.md              # quickstart (local dev + docker)
```

## 6. Milestones (all completed)

1. Plan docs ✔
2. Backend: models + services (interest math, exchange rules, loans) + routers + seed ✔
3. Backend test suite green ✔
4. CLI + MCP server + smoke tests ✔
5. Frontend scaffold + art system + all pages ✔
6. Frontend tests + production build ✔
7. Docker build ✔
8. Browser QA pass on the live local site, bug fixes, screenshots, QA report ✔

## 7. Docs in this folder

- [architecture.md](architecture.md) — system design, auth model, interest engine, exchange engine
- [database-schema.md](database-schema.md) — ERD + every table/column, invariant list
- [api.md](api.md) — full REST reference + CLI + MCP tool reference
- [ux-design.md](ux-design.md) — personas, palette, screens, art direction
- [testing-and-qa.md](testing-and-qa.md) — test strategy, how to run, QA report + screenshots
- [deployment.md](deployment.md) — local dev, Docker, EC2 + Cloudflare Access (Gmail login) production path
