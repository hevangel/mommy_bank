from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import create_token, get_current_user, hash_password, verify_password
from ..services.accounts import account_view
from ..services.serialize import user_dict
from .schemas import ChangePasswordIn, LoginIn

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username.strip().lower()).one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong username or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is deactivated")
    token = create_token(db, user)
    out = {"token": token, "user": user_dict(user)}
    if user.account is not None:
        out["account"] = account_view(db, user.account)
    return out


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    out = {"user": user_dict(user)}
    if user.account is not None:
        out["account"] = account_view(db, user.account)
    return out


@router.post("/change-password", status_code=204)
def change_password(
    body: ChangePasswordIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Old password is wrong")
    user.password_hash = hash_password(body.new_password)
    db.commit()
