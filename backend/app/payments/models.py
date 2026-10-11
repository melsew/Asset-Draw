import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.columns import UUIDPK, created_at, in_list, updated_at, uuid_pk
from app.core.db import Base

PAYMENT_STATUSES = ("INITIATED", "PENDING", "SUCCEEDED", "FAILED", "EXPIRED", "REFUNDED")


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("users.id"), nullable=False)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("campaigns.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    merchant_reference: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    provider_reference: Mapped[str | None] = mapped_column(String(128))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="ETB")
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("currency = 'ETB'", name="currency_etb"),
        CheckConstraint(in_list("status", PAYMENT_STATUSES), name="status_valid"),
        Index(
            "uq_payments_provider_reference",
            "provider",
            "provider_reference",
            unique=True,
            postgresql_where="provider_reference IS NOT NULL",
        ),
        Index("ix_payments_campaign_id_user_id", "campaign_id", "user_id"),
    )


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    id: Mapped[uuid.UUID] = uuid_pk()
    payment_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("payments.id"))
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_event_id: Mapped[str | None] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    received_at: Mapped[datetime] = created_at()
    __table_args__ = (
        CheckConstraint("payload_sha256 ~ '^[0-9a-f]{64}$'", name="payload_hash_format"),
        Index(
            "uq_payment_events_provider_event_id",
            "provider",
            "provider_event_id",
            unique=True,
            postgresql_where="provider_event_id IS NOT NULL",
        ),
        Index("uq_payment_events_provider_payload", "provider", "payload_sha256", unique=True),
    )


class Refund(Base):
    __tablename__ = "refunds"
    id: Mapped[uuid.UUID] = uuid_pk()
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("payments.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("users.id"), nullable=False
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("users.id"))
    created_at: Mapped[datetime] = created_at()
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)