from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import require_admin
from ..services import settings as settings_svc
from .schemas import SettingsPatchIn

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def get_settings(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return settings_svc.get_all(db)


@router.patch("")
def patch_settings(
    body: SettingsPatchIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    settings_svc.set_many(db, updates)
    db.commit()
    # full settings back so clients never see a partial object
    return settings_svc.get_all(db)
