# Testing & QA

## Strategy

| Layer | Tool | What it covers |
|---|---|---|
| Unit (services) | pytest | interest math (compounding, rounding, idempotence), exchange-rule matching (weekday/weekend, windows, cross-midnight, priority), conversion math, loan lifecycle + debt cap, settings defaults/coercion |
| API integration | pytest + FastAPI `TestClient` | auth (login fail/success, JWT, change password), role permissions (kid can't deposit, can read own, can't read others), money ops + ledger invariants (`balance_after` correct, no overdraft), screen ops, convert flow end-to-end (quote → convert → two ledger rows), loans API, settings/rules CRUD + admin gate, overview aggregates |
| Frontend unit | vitest + @testing-library/react | money/duration formatters, Login form behavior, BalanceCard rendering per ui_mode (teen vs toddler), exchange quote card, users page validation |
| Frontend build | `tsc -b && vite build` | type-safety + production bundle |
| E2E (manual, scripted) | browser automation on the live dev stack | the QA pass below — real clicks through every screen on desktop **and** mobile viewport |

No test contains usable credentials: passwords are generated with `secrets` at test time; the test DB is a throwaway SQLite file.

## How to run

```bash
# backend
cd backend
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"   # Windows; linux: .venv/bin/pip
.venv/Scripts/python -m pytest -q

# frontend
cd frontend
npm ci
npm run test        # vitest, watch=false
npm run build       # tsc + vite production build
```

## QA pass (executed on the live site)

- Stack under test: uvicorn (SQLite in `backend/data/qa.db`) + Vite dev server proxying `/api`, fresh seed with demo kids.
- Browser automation walked: admin login → overview → create kid → deposit → grant time → exchange quote → convert (kid self-service) → ledger check → loan enable → borrow → repay → settings changes → rule CRUD → toddler dashboard → mobile viewport pass → kid read-only enforcement in UI (no admin nav, mutation buttons hidden).
- Screenshots: [`qa/screenshots/`](../qa/screenshots/) · findings & fixes: see *QA Report* below.

## QA Report

Full report with per-test-point evidence: [`../qa/QA_REPORT.md`](../qa/QA_REPORT.md)
(screenshots in [`../qa/screenshots/`](../qa/screenshots/)).

**Result: PASS** — 13/13 scripted GUI test points passed on desktop + mobile
viewports; 3 bugs discovered during the pass (stale animated totals under
throttled rAF, partial settings PATCH response, wrong landing page after
account switch) were fixed and re-verified live; CLI and MCP additionally
smoke-tested against the live server (login, overview, deposit, quote,
deduct-time).
