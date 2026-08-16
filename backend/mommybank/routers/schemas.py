"""Pydantic request models."""
from __future__ import annotations

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordIn(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=4, max_length=128)


class UserCreateIn(BaseModel):
    username: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=4, max_length=128)
    display_name: str = Field(min_length=1, max_length=64)
    role: str = Field(default="user", pattern=r"^(admin|user)$")
    ui_mode: str = Field(default="teen", pattern=r"^(teen|kid|toddler)$")
    avatar: str = Field(default="🐷", max_length=16)
    email: str | None = None
    can_convert: bool | None = None
    can_borrow: bool | None = False


class UserPatchIn(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=64)
    ui_mode: str | None = Field(default=None, pattern=r"^(teen|kid|toddler)$")
    avatar: str | None = Field(default=None, max_length=16)
    email: str | None = None
    can_convert: bool | None = None
    can_borrow: bool | None = None
    is_active: bool | None = None
    role: str | None = Field(default=None, pattern=r"^(admin|user)$")
    password: str | None = Field(default=None, min_length=4, max_length=128)


class AmountCentsIn(BaseModel):
    amount_cents: int = Field(gt=0, le=2_000_000_000)
    note: str = Field(default="", max_length=200)


class AmountSecondsIn(BaseModel):
    amount_seconds: int = Field(gt=0, le=10_000_000)
    note: str = Field(default="", max_length=200)


class ConvertIn(BaseModel):
    amount_cents: int = Field(gt=0, le=2_000_000_000)
    note: str = Field(default="", max_length=200)


class AdjustIn(BaseModel):
    ledger: str = Field(pattern=r"^(money|screen)$")
    amount: int  # signed
    note: str = Field(default="", max_length=200)


class BorrowIn(BaseModel):
    account_id: int
    amount_cents: int = Field(gt=0, le=2_000_000_000)
    note: str = Field(default="", max_length=200)


class RepayIn(BaseModel):
    amount_cents: int = Field(gt=0, le=2_000_000_000)
    note: str = Field(default="", max_length=200)


class SettingsPatchIn(BaseModel):
    savings_apr_percent: float | None = None
    interest_enabled: bool | None = None
    borrow_enabled: bool | None = None
    borrow_apr_percent: float | None = None
    borrow_limit_cents: int | None = None
    exchange_base_minutes_per_dollar: float | None = None
    min_convert_cents: int | None = None
    currency_symbol: str | None = None
    timezone: str | None = None


class RuleIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    days: list[int] = Field(min_length=1, max_length=7)
    start_minute: int = Field(ge=0, le=1439)
    end_minute: int = Field(ge=1, le=1440)
    minutes_per_dollar: float = Field(gt=0, le=1000)
    priority: int = Field(default=100, ge=0, le=10_000)
    is_active: bool = True


class RulePatchIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    days: list[int] | None = None
    start_minute: int | None = Field(default=None, ge=0, le=1439)
    end_minute: int | None = Field(default=None, ge=1, le=1440)
    minutes_per_dollar: float | None = Field(default=None, gt=0, le=1000)
    priority: int | None = Field(default=None, ge=0, le=10_000)
    is_active: bool | None = None
