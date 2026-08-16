from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db, utcnow
from ..models import Account, User
from ..security import hash_password, require_admin
from ..services.serialize import user_dict
from .schemas import UserCreateIn, UserPatchIn

router = APIRouter(prefix="/users", tags=["users"])


def _default_can_convert(ui_mode: str) -> bool:
    return ui_mode != "toddler"


@router.get("")
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [user_dict(u) for u in db.query(User).order_by(User.id).all()]


@router.post("", status_code=201)
def create_user(body: UserCreateIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    username = body.username.strip().lower()
    if db.query(User).filter(User.username == username).one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(
        username=username,
        password_hash=hash_password(body.password),
        display_name=body.display_name.strip(),
        role=body.role,
        ui_mode=body.ui_mode,
        avatar=body.avatar or "🐷",
        email=body.email or None,
        can_convert=body.can_convert if body.can_convert is not None else _default_can_convert(body.ui_mode),
        can_borrow=bool(body.can_borrow),
    )
    db.add(user)
    db.flush()
    db.add(Account(user_id=user.id, last_interest_at=utcnow()))
    db.commit()
    db.refresh(user)
    return user_dict(user)


def _guard_last_admin(db: Session, target: User, *, changing_role: bool, deactivating: bool) -> None:
    if not (changing_role or deactivating):
        return
    admins = db.query(User).filter(User.role == "admin", User.is_active.is_(True)).all()
    others = [a for a in admins if a.id != target.id]
    if target.role == "admin" and target.is_active and not others:
        raise HTTPException(status_code=400, detail="Cannot remove the last active admin")


@router.patch("/{user_id}")
def patch_user(
    user_id: int,
    body: UserPatchIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    updates = body.model_dump(exclude_unset=True)
    _guard_last_admin(
        db, target,
        changing_role="role" in updates and updates["role"] != "admin",
        deactivating="is_active" in updates and updates["is_active"] is False,
    )
    if "password" in updates:
        pw = updates.pop("password")
        target.password_hash = hash_password(pw)
    for field in ("display_name", "ui_mode", "avatar", "email", "can_convert", "can_borrow", "is_active", "role"):
        if field in updates and updates[field] is not None:
            setattr(target, field, updates[field])
    db.commit()
    db.refresh(target)
    return user_dict(target)
