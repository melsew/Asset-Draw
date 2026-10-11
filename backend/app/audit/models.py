import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Identity, Index, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.columns import UUIDPK, created_at, uuid_pk
from app.core.db import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    seq: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False, unique=True)
    id: Mapped[uuid.UUID] = uuid_pk()
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPK, ForeignKey("users.id"))
    actor_type: Mapped[str] = mapped_column(String(24), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUIDPK)
    request_id: Mapped[str | None] = mapped_column(String(64))
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    old_state_hash: Mapped[str | None] = mapped_column(String(64))
    new_state_hash: Mapped[str | None] = mapped_column(String(64))
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, nullable=False)
    prev_hash: Mapped[str | None] = mapped_column(String(64))
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = created_at()
    __table_args__ = (
        CheckConstraint(
            "old_state_hash IS NULL OR old_state_hash ~ '^[0-9a-f]{64}$'",
            name="old_state_hash_format",
        ),
        CheckConstraint(
            "new_state_hash IS NULL OR new_state_hash ~ '^[0-9a-f]{64}$'",
            name="new_state_hash_format",
        ),
        CheckConstraint(
            "prev_hash IS NULL OR prev_hash ~ '^[0-9a-f]{64}$'", name="prev_hash_format"
        ),
        CheckConstraint("row_hash ~ '^[0-9a-f]{64}$'", name="row_hash_format"),
        Index("ix_audit_logs_entity_type_entity_id", "entity_type", "entity_id"),
        Index("ix_audit_logs_seq", "seq"),
    )