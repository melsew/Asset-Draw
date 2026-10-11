import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.columns import UUIDPK, created_at, in_list, uuid_pk
from app.core.db import Base

ENTRY_STATUSES = ("PENDING", "CONFIRMED", "CANCELLED", "EXPIRED", "REFUNDED")


class Entry(Base):
    __tablename__ = "entries"
    id: Mapped[uuid.UUID] = uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("campaigns.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("users.id"), nullable=False)
    entry_number: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("payments.id"))
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = created_at()
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint(in_list("status", ENTRY_STATUSES), name="status_valid"),
        CheckConstraint(
            "status <> 'CONFIRMED' OR entry_number IS NOT NULL",
            name="confirmed_has_entry_number",
        ),
        CheckConstraint("entry_number IS NULL OR entry_number > 0", name="entry_number_positive"),
        Index(
            "uq_entries_campaign_entry_number",
            "campaign_id",
            "entry_number",
            unique=True,
            postgresql_where="entry_number IS NOT NULL",
        ),
        Index(
            "uq_entries_source_reference",
            "campaign_id",
            "source_type",
            "source_reference",
            unique=True,
            postgresql_where="source_reference IS NOT NULL",
        ),
        Index("ix_entries_campaign_id_status", "campaign_id", "status"),
        Index("ix_entries_user_id", "user_id"),
    )


class EligibilityRecord(Base):
    __tablename__ = "eligibility_records"
    id: Mapped[uuid.UUID] = uuid_pk()
    entry_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("entries.id"))
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("campaigns.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("users.id"), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = created_at()
    __table_args__ = (
        CheckConstraint(in_list("result", ("PASS", "FAIL")), name="result_valid"),
        Index("ix_eligibility_records_campaign_id_user_id", "campaign_id", "user_id"),
    )