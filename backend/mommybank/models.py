"""SQLAlchemy models. Money = integer cents, screen time = integer seconds."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, utcnow


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user")  # admin|user
    ui_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="teen")  # teen|kid|toddler
    avatar: Mapped[str] = mapped_column(String(16), nullable=False, default="🐷")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)  # reserved: Cloudflare/Gmail identity
    can_convert: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    can_borrow: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    account: Mapped["Account | None"] = relationship(back_populates="user", uselist=False)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    money_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    screen_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_interest_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    user: Mapped[User] = relationship(back_populates="account")
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="account", order_by="Transaction.id.desc()"
    )
    loans: Mapped[list["Loan"]] = relationship(back_populates="account")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    ledger: Mapped[str] = mapped_column(String(8), nullable=False)  # money|screen|debt
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)  # signed
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    meta: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    account: Mapped[Account] = relationship(back_populates="transactions")

    @property
    def meta_dict(self) -> dict:
        import json

        return json.loads(self.meta or "{}")


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    principal_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    outstanding_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    apr_percent: Mapped[float] = mapped_column(nullable=False)
    last_accrual_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")  # active|repaid
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    repaid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    account: Mapped[Account] = relationship(back_populates="loans")


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded


class ExchangeRule(Base):
    __tablename__ = "exchange_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    days: Mapped[str] = mapped_column(Text, nullable=False, default="[0,1,2,3,4,5,6]")  # JSON list of ints
    start_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=1439)
    minutes_per_dollar: Mapped[float] = mapped_column(nullable=False, default=10.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    @property
    def days_list(self) -> list[int]:
        import json

        return json.loads(self.days)
