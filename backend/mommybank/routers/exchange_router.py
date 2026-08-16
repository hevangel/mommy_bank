from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ExchangeRule, User
from ..security import get_current_user, require_admin
from ..services import exchange, settings as settings_svc
from ..services.serialize import rule_dict
from .schemas import RuleIn, RulePatchIn

router = APIRouter(tags=["exchange"])


@router.get("/exchange/quote")
def quote(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    out = exchange.quote(db)
    # public bank state kids can see (drives the borrow button in the UI)
    out["borrow_enabled"] = bool(settings_svc.get(db, "borrow_enabled"))
    out["borrow_apr_percent"] = float(settings_svc.get(db, "borrow_apr_percent"))
    out["borrow_limit_cents"] = int(settings_svc.get(db, "borrow_limit_cents"))
    return out


@router.get("/exchange-rules")
def list_rules(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rules = db.query(ExchangeRule).order_by(ExchangeRule.priority, ExchangeRule.id).all()
    return [rule_dict(r) for r in rules]


def _validate_days(days: list[int]) -> list[int]:
    clean = sorted({d for d in days if 0 <= d <= 6})
    if not clean:
        raise HTTPException(status_code=422, detail="days must contain 0-6 (Mon=0)")
    return clean


@router.post("/exchange-rules", status_code=201)
def create_rule(
    body: RuleIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    import json

    rule = ExchangeRule(
        name=body.name.strip(),
        priority=body.priority,
        days=json.dumps(_validate_days(body.days)),
        start_minute=body.start_minute,
        end_minute=body.end_minute,
        minutes_per_dollar=body.minutes_per_dollar,
        is_active=body.is_active,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule_dict(rule)


@router.patch("/exchange-rules/{rule_id}")
def patch_rule(
    rule_id: int,
    body: RulePatchIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    import json

    rule = db.get(ExchangeRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    updates = body.model_dump(exclude_unset=True)
    if "days" in updates and updates["days"] is not None:
        updates["days"] = json.dumps(_validate_days(updates["days"]))
    for field, value in updates.items():
        if value is not None:
            setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule_dict(rule)


@router.delete("/exchange-rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    rule = db.get(ExchangeRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
