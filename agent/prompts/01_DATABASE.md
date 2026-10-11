# Phase 1 — Database (models and migrations)
Read first: AGENTS.md, docs/decisions.md, docs/design/database-design.md.
Existing models (users, roles, user_roles, refresh_sessions, vendors, vendor_users, vendor_documents, assets,
asset_verifications) are kept; add the rest of §2–§5. Then:
1. Generate the initial Alembic migration(s); they must apply from an empty PostgreSQL 16 database in CI.
2. Add the triggers/constraints T1–T9 (§6) and DB roles (§7) as migrations.
3. For **every** invariant write a test that attempts the forbidden write against a real PostgreSQL and asserts it fails
   (entries after POOL_LOCKED, UPDATE on append-only tables, second draw result for a prize, forged audit hash, etc.).
4. Generate a Mermaid ER diagram from the models into `docs/design/er-diagram.md`.
Do not implement endpoints. Acceptance: migrations from empty DB, all invariant tests pass, `ruff` clean.
