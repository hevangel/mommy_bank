# AGENTS.md — instructions for AI coding agents

You are about to change **Mommy Bank**, a family bank where the currencies are
money (integer **cents**) and screen time (integer **seconds**). Read this file
before touching anything. Design docs live in [`plan/`](plan/) — start with
[plan/architecture.md](plan/architecture.md) and [plan/database-schema.md](plan/database-schema.md).

## The one-paragraph mental model

Parents (`role=admin`) manage kids (`role=user`, ages `teen`/`kid`/`toddler`).
Every balance change is an append-only ledger row (`ledger` = money|screen|debt)
with signed `delta` + `balance_after`. Interest (default 6.7% APR, daily
compound) accrues **lazily** — never in a background job. Money converts to
screen time at a rate resolved from the rule table in the configured timezone.
Three surfaces — web GUI, CLI, MCP server — are all thin clients over the same
`/api/v1` REST endpoints.

## Hard rules (invariants you must not break)

1. **Money is integer cents, screen time is integer seconds.** No floats in
   balances or the ledger. Rates are float only during calculation; floor results.
2. **Every balance change writes exactly one `transactions` row** via
   `services/ledger.py::append_tx` — never mutate balances directly.
3. **No overdraft**: money and screen balances stay ≥ 0. Debt lives in `loans`,
   never as a negative money balance.
4. **Interest accrues on touch**: any endpoint that reads or mutates an account
   calls `services/interest.py::accrue_savings` (and `accrue_loan` for loans)
   first. Adding a new endpoint that touches balances? Call `accrue`.
5. **Loans capture their APR at borrow time** — changing the setting later must
   never rewrite existing debt.
6. **Kids are read-only** except the two per-user permissions `can_convert` and
   `can_borrow`. Enforce in routers (`ensure_access`, `require_admin`), never in
   the frontend only.
7. **SQL is parameter-bound via SQLAlchemy only** — no string-assembled SQL, no
   raw `text()` with interpolation. (A repo security hook rejects it anyway.)
8. **No credential literals anywhere** — source, tests, examples. Passwords come
   from env vars or `security.generate_password()`; tests generate their own.
9. **MCP SDK stays `mcp>=1.2,<2.0`** — v2 removed the FastMCP API this server uses.
10. **The last active admin cannot be deactivated or demoted** (guard exists in
    the users router — keep it working).

## Layout map

```
backend/mommybank/
  main.py            app factory, SPA static hosting, BankError → HTTP 400 handler
  routers/           HTTP layer only: auth deps + Pydantic validation (schemas.py)
  services/          ALL business logic (interest, ledger, exchange, loans, settings, accounts)
  api_client.py      typed REST client — shared by cli.py AND mcp_server.py
  cli.py             typer CLI (GUI parity: every mutation needs a command)
  mcp_server.py      FastMCP tools (GUI parity: every mutation needs a tool)
  seed.py            first-run defaults; idempotent; prints generated passwords once
frontend/src/
  api/               typed fetch client + AuthContext (token in localStorage)
  components/art/    hand-drawn SVGs (Piggy mascot with moods, icons, scenes) — keep it cute
  pages/             Login, Dashboard (dispatches teen/kid/toddler), Account, Overview, Users, Settings
  pages/dashboard/   the three age-mode dashboards + shared.tsx widgets
plan/                design docs — update when architecture changes
qa/                  QA report + screenshots from the browser test pass
```

Layering: `routers → services → models`. Routers never do math; services never
import FastAPI. New features follow the same path and then get mirrored in
`api_client.py` → `cli.py` + `mcp_server.py` (the parity requirement).

## Environment & commands

Windows dev box (Git Bash). **Port 8971, not 8000** — 8000 is taken on this
machine; vite proxies `/api` there and compose maps `8971:8000`.

```bash
# backend (venv at backend/.venv)
cd backend
.venv/Scripts/python -m pytest                              # all 68 tests, must be green
.venv/Scripts/python -m uvicorn mommybank.main:app --port 8971 --reload

# frontend
cd frontend
npm test                                                    # vitest, 19 tests
npm run build                                               # tsc strict + production bundle — must pass
npm run dev                                                 # :5173, proxies /api → :8971

# docker
docker compose up --build -d                                # → http://localhost:8971
```

Test DB is a throwaway temp file (see `tests/conftest.py`); settings reset to
defaults between tests — keep it that way when adding fixtures. Run the *full*
backend and frontend suites before declaring done; for GUI changes, also do a
quick browser pass on the dev stack (fresh demo DB: `MOMMYBANK_SEED_DEMO=1`).

## Conventions & gotchas

- Exchange rules: `start <= minute < end`; `end <= start` means the window
  crosses midnight. Lowest `priority` number wins. Evaluated in the `timezone`
  *setting* (IANA), not the server clock.
- The quote endpoint doubles as the public "bank state" channel for kids
  (borrow flags) — kids can't read `/settings`.
- Frontend: Tailwind flat color aliases (`bg-piggysoft`) AND nested names
  (`text-piggy-deep`) both exist; TS is strict (`noUnusedLocals`); modals are
  long — make sure action buttons stay reachable (scroll) on small screens.
- This repo is also a **plugin marketplace** (`.claude-plugin/marketplace.json`
  → `plugins/mommy-bank`): MCP server + the `mommy-bank-control` skill. If you
  add/rename an API endpoint, CLI command, or MCP tool, update that skill's
  tool list and recipes in the same PR.
- `CountUp` must always land on the final value even if rAF is throttled
  (occluded tab) — there's a safety timeout; don't remove it.
- Conventional commits, small PRs, human review merges (see CONTRIBUTING.md —
  humans direct and review, AI writes the code).
- SQLite is single-process by design: run uvicorn with the default one worker.
  WAL mode + foreign keys are set in `db.py`.

## When you add a feature

1. Service function + unit test (math and edge cases belong in `tests/`).
2. Router + Pydantic schema + API test (permissions: admin vs kid vs anonymous).
3. `api_client.py` method → CLI command → MCP tool (all three, same semantics).
4. Frontend: typed API + UI in the matching age-mode component(s).
5. Update `plan/` docs if the schema/API surface changed; bump nothing else.
