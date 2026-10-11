import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.columns import UUIDPK, created_at, in_list, uuid_pk
from app.core.db import Base

DRAW_STATUSES = ("SCHEDULED", "POOL_LOCKED", "DRAWING", "COMPLETED", "FAILED")
DRAW_STAGES = ("NONE", "ENTROPY_FETCHED", "RESULTS_PERSISTED", "SEED_REVEALED")


class Draw(Base):
    __tablename__ = "draws"
    id: Mapped[uuid.UUID] = uuid_pk()
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("campaigns.id"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="SCHEDULED")
    stage: Mapped[str] = mapped_column(String(24), nullable=False, server_default="NONE")
    seed_commitment: Mapped[str] = mapped_column(String(64), nullable=False)
    pool_locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("users.id"))
    planned_entropy_source: Mapped[str | None] = mapped_column(String(128))
    planned_entropy_round: Mapped[int | None] = mapped_column(BigInteger)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_by: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("users.id"))
    created_at: Mapped[datetime] = created_at()
    __table_args__ = (
        CheckConstraint(in_list("status", DRAW_STATUSES), name="status_valid"),
        CheckConstraint(in_list("stage", DRAW_STAGES), name="stage_valid"),
        CheckConstraint("seed_commitment ~ '^[0-9a-f]{64}$'", name="commitment_format"),
        CheckConstraint(
            "planned_entropy_round IS NULL OR planned_entropy_round >= 1",
            name="planned_round_positive",
        ),
        CheckConstraint(
            "(planned_entropy_source IS NULL) = (planned_entropy_round IS NULL)",
            name="planned_entropy_pair",
        ),
        Index("ix_draws_campaign_id", "campaign_id"),
    )


class DrawSecret(Base):
    __tablename__ = "draw_secrets"
    draw_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("draws.id"), primary_key=True
    )
    seed_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_id: Mapped[str] = mapped_column(String(128), nullable=False)
    revealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DrawSnapshot(Base):
    __tablename__ = "draw_snapshots"
    id: Mapped[uuid.UUID] = uuid_pk()
    draw_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("draws.id"), nullable=False, unique=True
    )
    entry_count: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_numbers: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    pool_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = created_at()
    __table_args__ = (
        CheckConstraint("entry_count > 0", name="entry_count_positive"),
        CheckConstraint("pool_hash ~ '^[0-9a-f]{64}$'", name="pool_hash_format"),
    )


class DrawEntropy(Base):
    __tablename__ = "draw_entropy"
    draw_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("draws.id"), primary_key=True
    )
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    round: Mapped[int] = mapped_column(BigInteger, nullable=False)
    value_hex: Mapped[str] = mapped_column(String(512), nullable=False)
    relays_confirmed: Mapped[int] = mapped_column(Integer, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        CheckConstraint("round >= 1", name="round_positive"),
        CheckConstraint("relays_confirmed >= 2", name="relay_quorum"),
        CheckConstraint("value_hex ~ '^([0-9a-f]{2})+$'", name="value_hex_format"),
    )


class DrawResult(Base):
    __tablename__ = "draw_results"
    id: Mapped[uuid.UUID] = uuid_pk()
    draw_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("draws.id"), nullable=False
    )
    prize_index: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_count: Mapped[int] = mapped_column(Integer, nullable=False)
    winner_index: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("entries.id"), nullable=False)
    created_at: Mapped[datetime] = created_at()
    __table_args__ = (
        UniqueConstraint("draw_id", "prize_index", name="uq_draw_results_draw_prize"),
        CheckConstraint("prize_index >= 0", name="prize_index_nonnegative"),
        CheckConstraint("remaining_count > 0", name="remaining_count_positive"),
        CheckConstraint(
            "winner_index >= 0 AND winner_index < remaining_count",
            name="winner_index_in_range",
        ),
    )


class VerificationRecord(Base):
    __tablename__ = "verification_records"
    id: Mapped[uuid.UUID] = uuid_pk()
    draw_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("draws.id"), nullable=False, unique=True
    )
    package: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    package_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    verifier_result: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        CheckConstraint("package_sha256 ~ '^[0-9a-f]{64}$'", name="package_hash_format"),
    )


class Winner(Base):
    __tablename__ = "winners"
    id: Mapped[uuid.UUID] = uuid_pk()
    draw_result_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("draw_results.id"), nullable=False, unique=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("users.id"), nullable=False)
    entry_id: Mapped[uuid.UUID] = mapped_column(UUIDPK, ForeignKey("entries.id"), nullable=False)
    created_at: Mapped[datetime] = created_at()


class PrizeFulfillment(Base):
    __tablename__ = "prize_fulfillments"
    id: Mapped[uuid.UUID] = uuid_pk()
    winner_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("winners.id"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="PENDING")
    evidence_ref: Mapped[str | None] = mapped_column(String(512))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    __table_args__ = (
        CheckConstraint(
            in_list("status", ("PENDING", "CONTACTED", "DELIVERED", "DISPUTED")),
            name="status_valid",
        ),
    )


class PrizeFulfillmentHistory(Base):
    __tablename__ = "prize_fulfillment_history"
    id: Mapped[uuid.UUID] = uuid_pk()
    fulfillment_id: Mapped[uuid.UUID] = mapped_column(
        UUIDPK, ForeignKey("prize_fulfillments.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_ref: Mapped[str | None] = mapped_column(String(512))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("users.id"))
    created_at: Mapped[datetime] = created_at()
    __table_args__ = (
        CheckConstraint(
            in_list("status", ("PENDING", "CONTACTED", "DELIVERED", "DISPUTED")),
            name="status_valid",
        ),
    )