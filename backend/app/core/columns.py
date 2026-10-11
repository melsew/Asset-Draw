"""Column helpers shared by all models."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

UUIDPK = UUID(as_uuid=True)


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUIDPK, primary_key=True, server_default=text("gen_random_uuid()"))


def created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


def updated_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


def in_list(column: str, values: tuple[str, ...]) -> str:
    """SQL for a CHECK constraint restricting a column to a fixed set of strings."""
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"
