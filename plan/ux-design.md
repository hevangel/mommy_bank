# UX Design

## Personas → UI modes (per-user property, parent-set)

| Mode | Who | Design principles |
|---|---|---|
| `teen` | Teenage boy (primary) | Real-bank feel: dense balances, ledger tables, sparkline charts, loan & interest detail, exact numbers. Copy treats him like an adult: "APR 6.7%, compounded daily". |
| `kid` | Elementary kid | Same information, bigger type, simpler words ("Your money grew 🌱 +12¢ today"), big tappable buttons, fewer columns, fun first. Tables collapse to cards. |
| `toddler` | Pre-schooler | **Read-only picture book**: one giant piggy + one giant clock, balances as huge numbers/stars, "Ask Mommy or Daddy 💕". No tables, no jargon, sticker rewards for saving milestones. |

Parents use the normal `teen`-grade UI (admin views are always full-detail regardless of mode).

## Look & feel

- **Art direction**: soft pastel "storybook bank" — cream background, pink piggy mascot, mint/lavender/sky/butter accents, deep-plum ink text, rounded-3xl cards, chunky shadows, gentle animations (floating pig, wiggling coins, star sparkles on deposit).
- **Mascot**: *Penny* the piggy — parameterized SVG with moods (`happy`, `wow`, `sleepy`, `celebrate`, `think`) used contextually (login, empty states, conversion success, toddler night).
- **Custom SVG icon set** (no icon library): coin stack, piggy-face logo, TV/screen-time, clock, rocket (borrow), sprout (interest), star (rewards), whale/bunny/bear avatars, wave background.
- Palette (Tailwind extend):
  - `piggy`  #F17FB6 · `piggysoft` #FDE7F1 · `mint` #63C9A8 · `mintsoft` #E2F7EF
  - `sky` #6FB8E8 · `skysoft` #E3F1FB · `butter` #F5C445 · `buttersoft` #FCF1D4
  - `lav` #A78BFA · `lavsoft` #EFE8FD · `ink` #3B3355 · `cream` #FFF9F2
- Typography: system UI stack, tabular numerals for money; toddler mode uses 5xl–7xl numbers.

## Responsive strategy

- Mobile-first; bottom tab bar (Home / Bank / Time / Settings-or-Admin); single column; action sheets become bottom sheets.
- ≥1024px: left sidebar nav, 2–3 column dashboard grids, sticky ledger table headers.
- Touch targets ≥44px everywhere (toddler mode: ≥72px).

## Screens

1. **Login** — centered card, Penny mascot waving, username/password, playful error wiggle. Demo hint box (when demo seeded) listing demo logins.
2. **Kid dashboard** (`/`):
   - *Hero*: two big balance cards — Piggy Bank 💰 (money, today's growth) and Screen Time 📺 (h m, "at today's rate your $X = Y minutes").
   - *Exchange strip*: current rate + active rule ("⭐ After-school bonus: 12 min/$ until 6pm") + Convert button (if permitted).
   - *My loans* card (teen, if any): outstanding, daily cost, Repay button.
   - *Recent activity* list with icons; teen gets sparkline of last 30 entries.
   - *Toddler mode*: replaces all of the above with two giant cards + sticker row (1 ⭐ per $5 saved).
3. **Account detail** (`/account/:id`; kid sees own, admin any): full ledger with ledger filter tabs (💰 Money / 📺 Time / 🏦 Debt), running balance, and — admin only — action panel (deposit, withdraw, grant/deduct time, adjust) and per-kid settings shortcut.
4. **Admin overview** (`/overview`): kid cards grid (avatar, balances, debt badge, last activity), quick-action buttons (＋ Deposit, ⏱ Grant time), bank totals, "who owes what".
5. **Users** (`/users`): create kid (name, emoji avatar picker, ui_mode picker with live preview, permissions), reset password, deactivate.
6. **Settings** (`/settings`): grouped cards — Interest (APR, on/off), Borrowing (on/off, APR, cap), Exchange (base rate, timezone), Currency symbol; exchange-rules editor table (add/edit/delete, 24h time inputs, weekday toggles, rate, priority, active switch).
7. **404 / empty states** — mascot + friendly copy.

## Feedback & motion

- Toasts for every mutation ("Deposited $20.00 to Big Bro ✅"); coin-drop animation on money cards after deposit.
- Destructive actions (withdraw/deduct/delete rule) ask confirm modals.
- All money animates count-up on change (300ms); interest growth rows get 🌱.
- `prefers-reduced-motion` disables animations.

## Accessibility

- Semantic landmarks, labelled inputs, focus rings, AA contrast on ink/cream, full keyboard operability, numbers with `aria-label`s spelled out ("12 dollars 34 cents").
