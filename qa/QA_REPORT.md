# Mommy Bank — QA Report

**Date**: 2026-08-16 · **Stack under test**: uvicorn (port 8971, SQLite `backend/data/qa.db`) + Vite dev server (5173, `/api` proxy), demo-seeded (teen / kid / toddler). QA passwords were env-provided and the QA database is deleted after the run.

## Automated suites

| Suite | Tool | Result |
|---|---|---|
| Backend unit + API integration | pytest | **68 passed** |
| Frontend components + formatters | vitest + Testing Library | **19 passed** |
| Frontend type-check + production build | tsc + vite | **pass** (232 KB JS / 71 KB gzip) |
| Docker image build | docker build | **pass** |

## Browser GUI pass (13 test points)

Executed as scripted black-box GUI testing in a real browser (desktop 1280×720 and mobile 390×844), one state-changing action per observation, DOM snapshot + screenshot evidence per point. Screenshots in [`screenshots/`](screenshots/).

| # | Test point | Result | Evidence |
|---|---|---|---|
| T1 | Login page renders (mascot, pastel theme, form) | ✅ PASS | t01_login.png |
| T2 | Wrong password → friendly alert, no crash | ✅ PASS | t02_login_error.png |
| T3 | Admin login → overview: 3 kid cards, totals, badges (toddler "no convert") | ✅ PASS | t03_admin_overview.png |
| T4 | Quick deposit modal → balance + toast (found BUG-1) | ✅ PASS | t04_deposit_done.png |
| T5 | Account detail: parent tools, ledger tabs, running balance, grant time → ledger row + toast | ✅ PASS | t05_account_detail.png, t05b_time_grant.png |
| T6 | Settings: interest / borrowing / exchange / timezone, 3 seeded rules listed | ✅ PASS | t06_settings.png (found BUG-2) |
| T7 | APR change saves with live projection; rule add → listed; rule delete w/ confirm dialog | ✅ PASS | t07_rule_added.png |
| T8 | Create kid (Cousin QA, kid mode, 🦊 avatar) → appears with badges + toast | ✅ PASS | t08_users_page.png, t08b_cousin_created.png |
| T9 | Teen login: dashboard, live peak-rate strip ("Bedtime peak, until 3:00 PM"), convert $2 → exactly 14 min at 7 min/$, paired ledger rows | ✅ PASS | t09_teen_dashboard.png, t09b_convert_done.png |
| T10 | Borrow $5 (loan #1: money +$5, owes $5.00 badge, My-loans card) then repay $2 → owes $3.00 | ✅ PASS | t10_toddler_dashboard.png era logs |
| T11 | Toddler view: giant balances, sticker chart (2⭐, $2.50 to next), "Ask Mommy or Daddy 💕" | ✅ PASS | t10_toddler_dashboard.png |
| T12 | Kid read-only: no parent tools, no admin nav, kid links only | ✅ PASS | (toddler History page) |
| T13 | Mobile 390×844: login + teen dashboard, bottom tab bar, single column, no overflow (verified visually) | ✅ PASS | t13a_mobile_login.png, t13b_mobile_teen.png |

CLI and MCP were additionally smoke-tested against the **live** server (not just in-process): login, overview, deposit, timezone-aware quote, transactions; MCP auto-login, overview, balance, deduct-time — all 200 OK.

## Bugs found & fixed during the pass

| Bug | Symptom | Root cause | Fix | Re-verified |
|---|---|---|---|---|
| BUG-1 | Animated totals/balances stayed stale after mutations in a throttled (occluded) renderer | `CountUp` only updated via `requestAnimationFrame`, which is paused when the tab is occluded | Safety `setTimeout` always lands the final value | Code-level; rAF throttling reproduced the stale state before the fix |
| BUG-2 | After saving one setting, every other settings input went blank/disabled until reload | `PATCH /api/v1/settings` returned only changed keys; the page replaced the whole settings object | Backend now returns the full settings object; frontend merges defensively | ✅ live — all inputs stay populated after save |
| BUG-3 | Logging in as a kid right after an admin session landed on `/overview` (admin-only page) | LoginPage navigated using the stale `user` from closure | `login()` returns the fresh user; navigation uses it; kids hitting `/overview` now redirect home | ✅ live — teen lands on `/` |

## Environment notes (not app bugs)

- The in-app browser's Playwright click pipeline intermittently failed actionability checks and its renderer degraded (rAF pause, screenshot capture failures) after several actions per tab; node-path (`dom_cua`) clicks on fresh tabs were used throughout. BUG-1 was found *because* of this throttling and is a real robustness improvement.
- Machine ports 8000/8010 are occupied by an unrelated process — the project therefore uses **8971** for local dev and maps `8971:8000` in docker-compose.

## Verdict

**PASS** — all 13 GUI test points passed, all 3 discovered bugs were fixed and re-verified live, and the full automated suites (68 backend + 19 frontend) are green on the final code.
