# services/models.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Integer, String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from services.db import Base


# -------------------------
# Users
# -------------------------
class User(Base, UserMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    plan: Mapped[str] = mapped_column(String(50), default="free")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return bool(self.password_hash) and check_password_hash(self.password_hash, raw_password)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} email={self.email!r} plan={self.plan!r}>"


# -------------------------
# Webhook 原始事件（審計/重放/對帳）
# -------------------------
class WebhookEvent(Base):
    """
    保存從 Stripe 收到的原始事件。
    - 以 event_id 做唯一性，避免重送事件造成重複。
    - payload 使用 JSON 欄位（若你的 SQLite 沒有 JSON1，可改成 Text 並自行 dumps）。
    """
    __tablename__ = "webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WebhookEvent id={self.id} event_id={self.event_id!r} type={self.type!r}>"


# -------------------------
# 付款紀錄（後台清單 / 報表來源）
# -------------------------
class Payment(Base):
    """
    付款歸檔表，對應一次成功的 checkout.session.completed。
    - 以 stripe_session_id 去重，避免重送事件新增多筆。
    - amount_twd 以「元」保存（Webhook 傳回的 amount_total/100）。
    """
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stripe_session_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    course_id: Mapped[str] = mapped_column(String(64), default="unknown")
    amount_twd: Mapped[int] = mapped_column(Integer)  # 金額（元）
    status: Mapped[str] = mapped_column(String(32), default="unknown")  # e.g. "paid"
    buyer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Payment id={self.id} session={self.stripe_session_id!r} "
            f"course={self.course_id!r} amount_twd={self.amount_twd} status={self.status!r}>"
        )
