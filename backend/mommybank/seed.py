"""First-run bootstrap: settings defaults, admin, optional demo kids, example rules.

Passwords are never hard-coded: they come from env or are generated and
printed once to the console.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from .config import get_config
from .db import utcnow
from .models import Account, ExchangeRule, User
from .security import generate_password, hash_password
from .services import ledger, settings as settings_svc

DEMO_KIDS = [
    # username, display, ui_mode, avatar, money_cents, days_ago, screen_seconds
    ("teen", "Big Bro", "teen", "🧑‍🚀", 15000, 20, 5400),
    ("kid", "Lil Sis", "kid", "🐰", 4000, 10, 2700),
    ("toddler", "Tiny Tot", "toddler", "🐻", 1250, 3, 1800),
]


def _banner(lines: list[str]) -> None:
    width = max(len(x) for x in lines) + 4
    print("\n" + "=" * width)
    for line in lines:
        print(f"  {line}")
    print("=" * width + "\n")


def seed(db: Session) -> None:
    cfg = get_config()
    settings_svc.ensure_defaults(db)

    # ---- exchange rules (only on a fresh rules table)
    if db.query(ExchangeRule).count() == 0:
        import json

        db.add_all([
            ExchangeRule(name="Bedtime peak", priority=5, days=json.dumps([0, 1, 2, 3, 4, 5, 6]),
                         start_minute=19 * 60, end_minute=22 * 60, minutes_per_dollar=7.0),
            ExchangeRule(name="After-school off-peak", priority=10, days=json.dumps([0, 1, 2, 3, 4]),
                         start_minute=15 * 60, end_minute=18 * 60, minutes_per_dollar=12.0),
            ExchangeRule(name="Weekend morning bonus", priority=20, days=json.dumps([5, 6]),
                         start_minute=7 * 60, end_minute=11 * 60, minutes_per_dollar=15.0),
        ])

    announced: list[str] = []

    # ---- admin
    if db.query(User).filter(User.role == "admin").count() == 0:
        password = cfg.admin_password_env or generate_password()
        db.add(User(
            username=cfg.admin_username.strip().lower(),
            password_hash=hash_password(password),
            display_name="Mommy & Daddy",
            role="admin",
            ui_mode="teen",
            avatar="👩‍💼",
            can_convert=False,
        ))
        if cfg.admin_password_env:
            announced.append(f"admin login: {cfg.admin_username}  (password from MOMMYBANK_ADMIN_PASSWORD)")
        else:
            announced.append(f"admin login: {cfg.admin_username}  password: {password}")
            announced.append("(set MOMMYBANK_ADMIN_PASSWORD to choose your own)")

    # ---- optional demo kids
    if cfg.seed_demo:
        demo_password = cfg.demo_password_env or generate_password()
        for username, display, ui_mode, avatar, money, days_ago, screen in DEMO_KIDS:
            if db.query(User).filter(User.username == username).one_or_none() is not None:
                continue
            now = utcnow()
            user = User(
                username=username,
                password_hash=hash_password(demo_password),
                display_name=f"{display} (demo)",
                role="user",
                ui_mode=ui_mode,
                avatar=avatar,
                can_convert=ui_mode != "toddler",
                can_borrow=False,
            )
            db.add(user)
            db.flush()
            past = now - timedelta(days=days_ago)
            account = Account(user_id=user.id, last_interest_at=past)
            db.add(account)
            db.flush()
            # backdated opening history so charts & interest look alive
            ledger.append_tx(db, account, "money", "deposit", money,
                             note="Starting balance", created_at=past)
            ledger.append_tx(db, account, "screen", "grant", screen,
                             note="Starting screen time", created_at=past)
        if any(db.query(User).filter(User.username == u).one_or_none() for u, *_ in DEMO_KIDS):
            if cfg.demo_password_env:
                announced.append("demo kids logins: teen / kid / toddler  (password from MOMMYBANK_DEMO_PASSWORD)")
            else:
                announced.append(f"demo kids logins: teen / kid / toddler  password: {demo_password}")

    db.commit()
    if announced:
        _banner(announced)
