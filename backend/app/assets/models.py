import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.columns import UUIDPK, created_at, in_list, updated_at, uuid_pk
from app.core.db import Base

ASSET_STATUSES = ("DRAFT", "SUBMITTED", "VERIFIED", "REJECTED", "WITHDRAWN")
CUSTODY_TYPES = ("ESCROW", "VENDOR_CONTRACT", "PLATFORM_CUSTODY")


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[uuid.UUID] = uuid_pk()
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("vendors.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    declared_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="ETB")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="DRAFT")
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()
    __table_args__ = (
        CheckConstraint("declared_value > 0", name="value_positive"),
        CheckConstraint("currency = 'ETB'", name="currency_etb"),
        CheckConstraint(in_list("status", ASSET_STATUSES), name="status_valid"),
        Index("ix_assets_vendor_id", "vendor_id"),
    )


class AssetVerification(Base):
    """Append-only record of each verification decision and the custody evidence
    behind it (D-04).
    """

    __tablename__ = "asset_verifications"
    id: Mapped[uuid.UUID] = uuid_pk()
    asset_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("assets.id"), nullable=False)
    verified_by: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("users.id"), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    custody_type: Mapped[str | None] = mapped_column(String(32))
    evidence_ref: Mapped[str | None] = mapped_column(String(512))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()
    __table_args__ = (
        CheckConstraint(in_list("result", ("APPROVED", "REJECTED")), name="result_valid"),
        CheckConstraint(
            "custody_type IS NULL OR "
            + in_list("custody_type", CUSTODY_TYPES),
            name="custody_valid",
        ),
        CheckConstraint(
            "result = 'REJECTED' OR (custody_type IS NOT NULL AND evidence_ref IS NOT NULL)",
            name="approval_needs_custody_evidence",
        ),
        Index("ix_asset_verifications_asset_id", "asset_id"),
    )
