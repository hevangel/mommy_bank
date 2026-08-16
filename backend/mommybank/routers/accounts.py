from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Account, Transaction, User
from ..security import get_current_user, require_admin
from ..services import accounts as accounts_svc
from ..services.serialize import account_dict, tx_dict
from .schemas import AdjustIn, AmountCentsIn, AmountSecondsIn, ConvertIn

router = APIRouter(tags=["accounts"])


def get_account_or_404(db: Session, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


def ensure_access(user: User, account: Account) -> None:
    if not user.is_admin and account.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your account")


@router.get("/accounts")
def list_accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.is_admin:
        accounts = db.query(Account).order_by(Account.id).all()
    else:
        accounts = [user.account] if user.account else []
    return [accounts_svc.account_view(db, a) for a in accounts]


@router.get("/overview")
def overview(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    accounts = db.query(Account).order_by(Account.id).all()
    views = [accounts_svc.account_view(db, a) for a in accounts]
    return {
        "accounts": views,
        "totals": {
            "money_cents": sum(v["money_cents"] for v in views),
            "screen_seconds": sum(v["screen_seconds"] for v in views),
            "debt_cents": sum(v["debt_cents"] for v in views),
        },
    }


@router.get("/accounts/{account_id}")
def get_account(
    account_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = get_account_or_404(db, account_id)
    ensure_access(user, account)
    return accounts_svc.account_view(db, account)


def _admin_action(db: Session, user: User, account_id: int, fn) -> dict:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    account = get_account_or_404(db, account_id)
    result = fn(account)
    db.commit()
    return {**result, "account": account_dict(account)}


@router.post("/accounts/{account_id}/deposit")
def deposit(
    account_id: int,
    body: AmountCentsIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _admin_action(
        db, user, account_id,
        lambda a: accounts_svc.deposit(db, a, body.amount_cents, body.note, user),
    )


@router.post("/accounts/{account_id}/withdraw")
def withdraw(
    account_id: int,
    body: AmountCentsIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _admin_action(
        db, user, account_id,
        lambda a: accounts_svc.withdraw(db, a, body.amount_cents, body.note, user),
    )


@router.post("/accounts/{account_id}/grant-time")
def grant_time(
    account_id: int,
    body: AmountSecondsIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _admin_action(
        db, user, account_id,
        lambda a: accounts_svc.grant_time(db, a, body.amount_seconds, body.note, user),
    )


@router.post("/accounts/{account_id}/deduct-time")
def deduct_time(
    account_id: int,
    body: AmountSecondsIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _admin_action(
        db, user, account_id,
        lambda a: accounts_svc.deduct_time(db, a, body.amount_seconds, body.note, user),
    )


@router.post("/accounts/{account_id}/adjust")
def adjust(
    account_id: int,
    body: AdjustIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _admin_action(
        db, user, account_id,
        lambda a: accounts_svc.adjust(db, a, body.ledger, body.amount, body.note, user),
    )


@router.post("/accounts/{account_id}/convert")
def convert(
    account_id: int,
    body: ConvertIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = get_account_or_404(db, account_id)
    ensure_access(user, account)
    if not user.is_admin and not account.user.can_convert:
        raise HTTPException(status_code=403, detail="Converting is not allowed for this account")
    result = accounts_svc.convert(db, account, body.amount_cents, body.note, user)
    db.commit()
    return {**result, "account": account_dict(account)}


@router.get("/accounts/{account_id}/transactions")
def transactions(
    account_id: int,
    ledger: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = get_account_or_404(db, account_id)
    ensure_access(user, account)
    limit = max(1, min(limit, 500))
    if ledger is not None and ledger not in ("money", "screen", "debt"):
        raise HTTPException(status_code=422, detail="ledger must be money|screen|debt")
    q = db.query(Transaction).filter(Transaction.account_id == account_id)
    if ledger:
        q = q.filter(Transaction.ledger == ledger)
    rows = q.order_by(Transaction.id.desc()).offset(offset).limit(limit).all()
    names = {u.id: u.display_name for u in db.query(User).all()}
    return [tx_dict(t, names.get(t.created_by)) for t in rows]
