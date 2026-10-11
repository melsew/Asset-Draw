"""Generate the Mermaid ER diagram from registered SQLAlchemy models."""
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import PrimaryKeyConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.db import Base

for model_module in (
    "app.users.models",
    "app.auth.models",
    "app.vendors.models",
    "app.assets.models",
    "app.campaigns.models",
    "app.entries.models",
    "app.payments.models",
    "app.draws.models",
    "app.audit.models",
    "app.notifications.models",
):
    __import__(model_module)


def generate() -> str:
    lines = [
        "# Asset-Draw Entity Relationship Diagram",
        "",
        "Generated from SQLAlchemy model metadata. Regenerate with `python scripts/generate_er_diagram.py`.",
        "",
        "```mermaid",
        "erDiagram",
    ]
    tables = sorted(Base.metadata.tables.values(), key=lambda table: table.name)

    for table in tables:
        lines.append(f"    {table.name} {{")
        for column in table.columns:
            sql_type = column.type.compile(dialect=postgresql.dialect())
            keys = []
            if column.primary_key:
                keys.append("PK")
            if column.foreign_keys:
                keys.append("FK")
            suffix = f" {' '.join(keys)}" if keys else ""
            lines.append(f"        {sql_type} {column.name}{suffix}")
        lines.append("    }")

    relationships: set[tuple[str, str, str, bool, bool]] = set()
    for table in tables:
        unique_key_sets = {
            frozenset(column.name for column in constraint.columns)
            for constraint in table.constraints
            if isinstance(constraint, (PrimaryKeyConstraint, UniqueConstraint))
        }
        unique_key_sets.update(
            frozenset(index.columns.keys())
            for index in table.indexes
            if index.unique
        )
        for constraint in table.foreign_key_constraints:
            foreign_key_columns = frozenset(column.name for column in constraint.columns)
            unique = foreign_key_columns in unique_key_sets
            for element in constraint.elements:
                parent = element.column.table.name
                child = table.name
                optional = any(column.nullable for column in constraint.columns)
                relationships.add((parent, child, element.parent.name, unique, optional))

    for parent, child, label, unique, optional in sorted(relationships):
        parent_cardinality = "o|" if optional else "||"
        child_cardinality = "o|" if unique else "o{"
        lines.append(
            f'    {parent} {parent_cardinality}--{child_cardinality} {child} : "{label}"'
        )

    lines.extend(("```", ""))
    return "\n".join(lines)


if __name__ == "__main__":
    target = ROOT / "docs" / "design" / "er-diagram.md"
    target.write_text(generate(), encoding="utf-8")
    print(f"Generated {target.relative_to(ROOT)}")