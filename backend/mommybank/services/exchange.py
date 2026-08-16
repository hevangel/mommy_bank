"""Money -> screen-time exchange: base rate + peak/off-peak rule windows."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..models import ExchangeRule
from . import settings as settings_svc


def _tz(db: Session) -> ZoneInfo:
    name = str(settings_svc.get(db, "timezone") or "UTC")
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("UTC")


def _local(db: Session, at_utc: datetime) -> datetime:
    aware = at_utc.replace(tzinfo=ZoneInfo("UTC"))
    return aware.astimezone(_tz(db))


def _rule_matches(rule: ExchangeRule, weekday: int, minute: int) -> bool:
    if not rule.is_active:
        return False
    if weekday not in rule.days_list:
        return False
    start, end = rule.start_minute, rule.end_minute
    if start <= end:
        return start <= minute < end
    # window crosses midnight (e.g. 20:00 -> 06:00)
    return minute >= start or minute < end


def resolve_rate(db: Session, at_utc: datetime) -> tuple[float, ExchangeRule | None]:
    """Highest-priority (lowest number) active rule matching now, else base rate."""
    base = float(settings_svc.get(db, "exchange_base_minutes_per_dollar"))
    local = _local(db, at_utc)
    weekday, minute = local.weekday(), local.hour * 60 + local.minute
    rules = db.query(ExchangeRule).filter(ExchangeRule.is_active.is_(True)).all()
    rules.sort(key=lambda r: (r.priority, r.id))
    for rule in rules:
        if _rule_matches(rule, weekday, minute):
            return float(rule.minutes_per_dollar), rule
    return base, None


def _window_end_local(rule: ExchangeRule, local: datetime) -> datetime:
    """Local datetime when the matched window ends (today or tomorrow)."""
    minute = local.hour * 60 + local.minute
    end_h, end_m = divmod(rule.end_minute, 60)
    if rule.start_minute <= rule.end_minute:
        day = local
    else:
        # crossing midnight: evening part ends tomorrow, morning part ends today
        day = local + timedelta(days=1) if minute >= rule.start_minute else local
    return day.replace(hour=end_h, minute=end_m, second=0, microsecond=0)


def convert_seconds(cents: int, minutes_per_dollar: float) -> int:
    """$1 (=100 cents) at rate r -> r minutes; return whole seconds (floored)."""
    if cents <= 0:
        return 0
    return int(cents * minutes_per_dollar * 60 / 100)


def _rate_at(db: Session, rules: list[ExchangeRule], base: float, weekday: int, minute: int) -> float:
    for rule in rules:
        if _rule_matches(rule, weekday, minute):
            return float(rule.minutes_per_dollar)
    return base


def quote(db: Session, now_utc: datetime | None = None) -> dict:
    """Current rate, matched rule, when it ends, and the next rate change."""
    from ..db import utcnow

    now_utc = now_utc or utcnow()
    base = float(settings_svc.get(db, "exchange_base_minutes_per_dollar"))
    rate, rule = resolve_rate(db, now_utc)
    local = _local(db, now_utc)

    out = {
        "rate": rate,
        "base_rate": base,
        "rule": None,
        "until": None,
        "next_change": None,
        "local_time": local.isoformat(),
        "timezone": str(settings_svc.get(db, "timezone") or "UTC"),
    }
    if rule is not None:
        end_local = _window_end_local(rule, local)
        out["rule"] = {"id": rule.id, "name": rule.name, "minutes_per_dollar": float(rule.minutes_per_dollar)}
        out["until"] = end_local.isoformat()

    # scan the next 24h minute-by-minute for the first rate change (cheap, exact)
    rules = db.query(ExchangeRule).filter(ExchangeRule.is_active.is_(True)).all()
    rules.sort(key=lambda r: (r.priority, r.id))
    cur_rate = rate
    scan = local.replace(second=0, microsecond=0)
    for i in range(1, 24 * 60 + 1):
        m = scan + timedelta(minutes=i)
        r = _rate_at(db, rules, base, m.weekday(), m.hour * 60 + m.minute)
        if r != cur_rate:
            out["next_change"] = {"at": m.isoformat(), "rate": r}
            break
    return out
