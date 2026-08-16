# Database Schema (SQLite)

Money is stored as **integer cents**, screen time as **integer seconds**. No floats in balances.

## ERD

```mermaid
erDiagram
    users ||--o| accounts : "has one"
    users ||--o{ transactions : "created_by (auditor)"
    accounts ||--o{ transactions : "ledger entries"
    accounts ||--o{ loans : "borrows"
    settings {
        string key PK
        string value JSON
    }
    exchange_rules {
        int id PK
    }
```

## Tables

### `users`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `username` | TEXT UNIQUE NOT NULL | lowercase login name |
| `password_hash` | TEXT NOT NULL | bcrypt |
| `display_name` | TEXT NOT NULL | e.g. `Big Bro` |
| `role` | TEXT NOT NULL | `admin` \| `user` |
| `ui_mode` | TEXT NOT NULL DEFAULT `teen` | `teen` \| `kid` \| `toddler` |
| `avatar` | TEXT DEFAULT `🐷` | emoji shown on cards |
| `can_convert` | BOOLEAN DEFAULT depends on mode | kid may convert own money→time |
| `can_borrow` | BOOLEAN DEFAULT 0 | kid may open loans (also needs global borrow_enabled) |
| `is_active` | BOOLEAN DEFAULT 1 | deactivated users can't log in |
| `created_at` / `updated_at` | TEXT (ISO UTC) | |

### `accounts`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `user_id` | INTEGER UNIQUE FK→users | 1:1 |
| `money_cents` | INTEGER DEFAULT 0 | may be ≥ 0 only (debt lives in loans, not negative balance) |
| `screen_seconds` | INTEGER DEFAULT 0 | ≥ 0 |
| `last_interest_at` | TEXT (ISO UTC) | savings interest accrual cursor |
| `created_at` | TEXT | |

### `transactions` — append-only ledger, three ledgers in one table
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `account_id` | FK→accounts | |
| `ledger` | TEXT | `money` \| `screen` \| `debt` |
| `kind` | TEXT | `deposit`, `withdraw`, `adjust`, `interest`, `borrow`, `repay`, `loan_interest`, `convert_out`, `convert_in`, `grant`, `deduct` |
| `delta` | INTEGER | signed; money ledger = cents, screen = seconds, debt = cents of outstanding |
| `balance_after` | INTEGER | post-apply balance of that ledger |
| `note` | TEXT | free text shown in UI |
| `meta` | TEXT (JSON) | e.g. `{"rate": 12.0, "rule": "After-school bonus", "seconds": 720}` for conversions |
| `created_by` | FK→users NULL | NULL = system (interest) |
| `created_at` | TEXT (ISO UTC) | |

### `loans`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `account_id` | FK→accounts | |
| `principal_cents` | INTEGER | original amount |
| `outstanding_cents` | INTEGER | principal + accrued interest − repayments |
| `apr_percent` | REAL | rate captured at borrow time |
| `last_accrual_at` | TEXT | loan interest cursor |
| `status` | TEXT | `active` \| `repaid` |
| `created_at` / `repaid_at` | TEXT | |

### `exchange_rules`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT | e.g. `Bedtime peak` |
| `priority` | INTEGER | lower = wins |
| `days` | TEXT JSON `[0..6]` | Mon=0 … Sun=6 |
| `start_minute` | INTEGER 0–1439 | window start (local time) |
| `end_minute` | INTEGER 0–1439 | exclusive; `end ≤ start` → crosses midnight |
| `minutes_per_dollar` | REAL | effective rate while window matches |
| `is_active` | BOOLEAN | |
| `created_at` | TEXT | |

### `settings` — key/value (JSON-encoded values), typed accessor in services
| Key | Default | Meaning |
|---|---|---|
| `savings_apr_percent` | `6.7` | savings APR, daily compounding |
| `interest_enabled` | `true` | master switch for savings interest |
| `borrow_enabled` | `false` | master switch for loans |
| `borrow_apr_percent` | `10.0` | APR for new loans |
| `borrow_limit_cents` | `5000` | max total outstanding debt per account |
| `exchange_base_minutes_per_dollar` | `10.0` | fallback exchange rate |
| `min_convert_cents` | `1` | minimum conversion size |
| `currency_symbol` | `"$"` | display only |
| `timezone` | `"UTC"` | IANA name used to evaluate exchange rules |

## Seed data (first run, idempotent)

- settings above; admin user (env password or random-printed);
- optional demo kids (`MOMMYBANK_SEED_DEMO=1`): a teen, an elementary kid and a toddler with different `ui_mode`s;
- example exchange rules:
  - `After-school off-peak` Mon–Fri 15:00–18:00 → **12** min/$ (priority 10)
  - `Bedtime peak` every day 19:00–22:00 → **7** min/$ (priority 5)
  - `Weekend morning bonus` Sat–Sun 07:00–11:00 → **15** min/$ (priority 20)

## Invariants (enforced in services, covered by tests)

1. `accounts.money_cents ≥ 0` — withdraw/convert/repay check funds first; only borrowing *adds* money, debt tracked separately.
2. `accounts.screen_seconds ≥ 0` — deduct checks first.
3. Every balance change writes exactly one `transactions` row with correct `balance_after`.
4. Interest accrual is idempotent: cursor only advances by whole settled days.
5. `loans.outstanding_cents ≥ 0`; reaches 0 ⇒ status `repaid`.
6. Total outstanding debt per account ≤ `borrow_limit_cents` at borrow time.
7. Ledger rows are never updated or deleted (append-only; admin "adjust" is just an explicit correction entry).
8. All SQL goes through SQLAlchemy parameters — no string interpolation.
