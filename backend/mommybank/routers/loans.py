from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db, utcnow
from ..models import Account, Loan, User
from ..security import get_current_user
from ..services import interest
from ..services import loans as loans_svc
from ..services.serialize import loan_dict
from .schemas import BorrowIn, RepayIn

router = APIRouter(prefix="/loans", tags=["loans"])


def _account_for(db: Session, user: User, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    if not user.is_admin and account.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your account")
    return account


@router.post("/borrow", status_code=201)
def borrow(
    body: BorrowIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = _account_for(db, user, body.account_id)
    loan = loans_svc.borrow(db, account, body.amount_cents, user, note=body.note)
    db.commit()
    return loan_dict(loan)


@router.post("/{loan_id}/repay")
def repay(
    loan_id: int,
    body: RepayIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")
    if not user.is_admin and loan.account.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your account")
    repaid = loans_svc.repay(db, loan, body.amount_cents, user, note=body.note)
    db.commit()
    return {"repaid_cents": repaid, "loan": loan_dict(loan)}


@router.get("")
def list_loans(
    account_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Loan).order_by(Loan.id.desc())
    if not user.is_admin:
        if user.account is None:
            return []
        account_id = user.account.id
    if account_id is not None:
        q = q.filter(Loan.account_id == account_id)
    loans = q.limit(200).all()
    for loan in loans:  # lazy accrual on read so numbers are current
        interest.accrue_loan(db, loan, utcnow())
    db.commit()
    return [loan_dict(l) for l in loans]
