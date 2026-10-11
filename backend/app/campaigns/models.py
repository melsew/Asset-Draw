import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.columns import UUIDPK, created_at, in_list, updated_at, uuid_pk
from app.core.db import Base

CAMPAIGN_ENTRY_MODES = ("FREE", "PROMOTIONAL", "PURCHASE", "PAID_ENTRY", "REFERRAL")
CAMPAIGN_STATUSES = (
    "DRAFT",
    "SUBMITTED",
    "UNDER_REVIEW",
    "REJECTED",
    "APPROVED",
    "ASSET_VERIFIED",
    "SCHEDULED",
    "ACTIVE",
    "SUSPENDED",
    "CANCELLED",
    "ENTRY_CLOSED",
    "POOL_LOCKED",
    "DRAWING",
    "DRAW_COMPLETED",
    "WINNER_VERIFIED",
    "PRIZE_DELIVERED",
    "COMPLETED",
)


class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[uuid.UUID] = uuid_pk()
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("vendors.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    entry_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    max_entries: Mapped[int] = mapped_column(Integer, nullable=False)
    per_user_limit: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    draw_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="DRAFT")
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()
    __table_args__ = (
        CheckConstraint(in_list("entry_mode", CAMPAIGN_ENTRY_MODES), name="entry_mode_valid"),
        CheckConstraint(in_list("status", CAMPAIGN_STATUSES), name="status_valid"),
        CheckConstraint("max_entries > 0", name="max_entries_positive"),
        CheckConstraint("per_user_limit > 0", name="per_user_limit_positive"),
        CheckConstraint(
            "entry_mode IN ('PURCHASE', 'PAID_ENTRY') OR entry_price IS NULL",
            name="nonpaid_entry_price_null",
        ),
        CheckConstraint("end_at > start_at", name="dates_ordered"),
        Index("ix_campaigns_status", "status"),
        Index("ix_campaigns_start_at_end_at", "start_at", "end_at"),
    )


class CampaignPrize(Base):
    __tablename__ = "campaign_prizes"
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("campaigns.id"), primary_key=True
    )
    prize_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("assets.id"), nullable=False, unique=True
    )
    __table_args__ = (CheckConstraint("prize_index >= 0", name="prize_index_nonnegative"),)


class CampaignRule(Base):
    __tablename__ = "campaign_rules"
    id: Mapped[uuid.UUID] = uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("campaigns.id"), nullable=False
    )
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)


class CampaignStatusHistory(Base):
    __tablename__ = "campaign_status_history"
    id: Mapped[uuid.UUID] = uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("campaigns.id"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(24))
    to_status: Mapped[str] = mapped_column(String(24), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("users.id"))
    actor_type: Mapped[str] = mapped_column(String(8), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()
    __table_args__ = (
        CheckConstraint(in_list("actor_type", ("USER", "SYSTEM")), name="actor_type_valid"),
        CheckConstraint(in_list("to_status", CAMPAIGN_STATUSES), name="to_status_valid"),
        CheckConstraint(
            f"from_status IS NULL OR {in_list('from_status', CAMPAIGN_STATUSES)}",
            name="from_status_valid",
        ),
        Index("ix_campaign_status_history_campaign_id", "campaign_id"),
    )


class EntryModeApproval(Base):
    __tablename__ = "entry_mode_approvals"
    id: Mapped[uuid.UUID] = uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("campaigns.id"), nullable=False
    )
    entry_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    approved_by: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("users.id"), nullable=False
    )
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    legal_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    __table_args__ = (
        CheckConstraint(in_list("entry_mode", CAMPAIGN_ENTRY_MODES), name="entry_mode_valid"),
        Index("ix_entry_mode_approvals_campaign_id", "campaign_id"),
    )


class CampaignCounter(Base):
    __tablename__ = "campaign_counters"
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("campaigns.id"), primary_key=True
    )
    next_entry_number: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="1"
    )
    __table_args__ = (
        CheckConstraint("next_entry_number > 0", name="next_entry_number_positive"),
    )