# Phase 4 — Eligibility and entry engine
Read first: AGENTS.md, docs/decisions.md, docs/design/database-design.md §3.
Implement eligibility rules, `POST /campaigns/{id}/participate` with a required idempotency key, PENDING holds with
expiry, confirmation that allocates the integer `entry_number` from `campaign_counters`, per-user limits, and the
expiry job. Only FREE/PROMOTIONAL are activatable.
Tests (must run against real PostgreSQL): N parallel requests never exceed `max_entries`; duplicate qualification and
retried idempotency keys create one entry; numbers are unique and contiguous among confirmed entries; expired holds free
capacity; no entry can be created or changed after POOL_LOCKED (trigger T3 attacked directly).
