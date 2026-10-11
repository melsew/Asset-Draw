import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.columns import UUIDPK, created_at, in_list, updated_at, uuid_pk
from app.core.db import Base

VENDOR_STATUSES = ("PENDING", "APPROVED", "SUSPENDED", "REJECTED")


class Vendor(Base):
    __tablename__ = "vendors"
    id: Mapped[uuid.UUID] = uuid_pk()
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="PENDING")
    contact_email: Mapped[str | None] = mapped_column(String(320))
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()
    __table_args__ = (CheckConstraint(in_list("status", VENDOR_STATUSES), name="status_valid"),)


class VendorUser(Base):
    __tablename__ = "vendor_users"
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("vendors.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("users.id"), primary_key=True)
    role_in_vendor: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="STAFF"
    )
    created_at: Mapped[datetime] = created_at()
    __table_args__ = (
        CheckConstraint(in_list("role_in_vendor", ("OWNER", "STAFF")), name="role_valid"),
    )


class VendorDocument(Base):
    __tablename__ = "vendor_documents"
    id: Mapped[uuid.UUID] = uuid_pk()
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("vendors.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("users.id"))
    created_at: Mapped[datetime] = created_at()
    __table_args__ = (CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="sha256_format"),)
