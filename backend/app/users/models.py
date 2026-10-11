import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.columns import UUIDPK, created_at, in_list, updated_at, uuid_pk
from app.core.db import Base

ROLE_NAMES = (
    "SUPER_ADMIN", "ADMIN", "CAMPAIGN_MANAGER", "FINANCE",
    "AUDITOR", "VENDOR", "CUSTOMER_SUPPORT", "PARTICIPANT",
)
USER_STATUSES = ("ACTIVE", "SUSPENDED", "DISABLED")


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text)  # null for OTP-only participants
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="ACTIVE")
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()
    __table_args__ = (
        CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name="has_contact"),
        CheckConstraint(r"phone IS NULL OR phone ~ '^\+[1-9][0-9]{6,14}$'", name="phone_e164"),
        CheckConstraint(in_list("status", USER_STATUSES), name="status_valid"),
        Index("uq_users_email_lower", func.lower(email), unique=True),
    )


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    __table_args__ = (CheckConstraint(in_list("name", ROLE_NAMES), name="name_valid"),)


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("roles.id"), primary_key=True)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("users.id"))
    granted_at: Mapped[datetime] = created_at()
