from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InstallState(Base):
    __tablename__ = "install_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    setup_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    deployment_name: Mapped[str] = mapped_column(String(120), default="ATeam")
    require_login: Mapped[bool] = mapped_column(Boolean, default=False)
    model_backend: Mapped[str] = mapped_column(String(40), default="stub")
    brand_name: Mapped[str] = mapped_column(String(120), default="ATeam")
    accent_color: Mapped[str] = mapped_column(String(16), default="#EDAA4B")
    logo_path: Mapped[str] = mapped_column(String(255), default="/static/img/logo.png")
    monthly_cap_usd: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="staff")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    prefix: Mapped[str] = mapped_column(String(16), unique=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_by: Mapped[str] = mapped_column(String(80), default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AppSecret(Base):
    __tablename__ = "app_secrets"
    __table_args__ = (UniqueConstraint("name", name="uq_app_secret_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    value: Mapped[str] = mapped_column(Text, default="")


class ConnectorState(Base):
    __tablename__ = "connector_state"
    __table_args__ = (UniqueConstraint("name", name="uq_connector_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mode: Mapped[str] = mapped_column(String(16), default="stub")


class SpendEvent(Base):
    __tablename__ = "spend_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(40))
    amount_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EmailSink(Base):
    __tablename__ = "email_sink"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    to_addr: Mapped[str] = mapped_column(String(200))
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DemoRecord(Base):
    """Seeded row used by the backup/restore check."""

    __tablename__ = "demo_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    note: Mapped[str] = mapped_column(Text)
