# Database design (authoritative design; Alembic migrations are the mechanism)

Conventions (already used by existing models, keep them): UUID primary keys via `gen_random_uuid()`;
`TIMESTAMPTZ` UTC; `NUMERIC(18,2)` money with `currency = 'ETB'` CHECK; enumerations as `VARCHAR` + CHECK
built with `in_list()`; deterministic constraint names (`NAMING_CONVENTION`); no hard deletes of financial or
draw evidence. There is **no** separate `schema.sql`; the ER diagram is generated from the models.

## 1. Implemented models (Phase 1)
The SQLAlchemy metadata includes the identity, vendor, asset, campaign, entry, payment, draw/evidence, audit,
fulfillment, and notification tables below. The initial Alembic revision creates the full schema from an empty
PostgreSQL database; the following revision adds the T1–T9 triggers and the least-privilege database roles.
The ER diagram is generated from the ORM metadata at `docs/design/er-diagram.md`.

The PostgreSQL invariant tests require `TEST_DATABASE_URL` to point to an isolated database whose name contains
`test`. They apply the current Alembic head themselves. Never set this variable to a database containing data
that must be retained.

## 2. To add — identity extras
- `otp_challenges(id, phone, code_hash, expires_at, attempts int, consumed_at, ip_address, created_at)`; code is 6 digits, stored hashed, ≤5 attempts, 5-minute TTL.
- `staff_mfa(user_id PK→users, totp_secret_encrypted, enabled_at, recovery_code_hashes text[])`.

## 3. To add — campaigns and entries
- `campaigns(id, vendor_id, title, description, entry_mode CHECK IN(FREE,PROMOTIONAL,PURCHASE,PAID_ENTRY,REFERRAL), entry_price NUMERIC(18,2) NULL, max_entries INT NOT NULL CHECK>0, per_user_limit INT NOT NULL DEFAULT 1, start_at, end_at, draw_at, status CHECK IN(state list), created_by, created_at, updated_at)`; `CHECK(entry_mode IN ('PURCHASE','PAID_ENTRY') OR entry_price IS NULL)`; `CHECK(end_at > start_at)`.
- `campaign_prizes(campaign_id, prize_index INT ≥0, asset_id, PRIMARY KEY(campaign_id, prize_index), UNIQUE(asset_id))`. One asset per prize; MVP campaigns usually have prize 0 only.
- `campaign_rules(id, campaign_id, rule_type, params JSONB)` — eligibility rules (A-10).
- `campaign_status_history(id, campaign_id, from_status, to_status, actor_user_id NULL, actor_type CHECK IN(USER,SYSTEM), reason, created_at)` — append-only.
- `entry_mode_approvals(id, campaign_id, entry_mode, approved_by, approved_at, legal_reference NOT NULL)` — required before a campaign with `PURCHASE`/`PAID_ENTRY` can be `ACTIVE` (A-16).
- `campaign_counters(campaign_id PK, next_entry_number BIGINT NOT NULL DEFAULT 1)` — row-locked to allocate numbers.
- `entries(id, campaign_id, user_id, entry_number INT NULL, status CHECK IN(PENDING,CONFIRMED,CANCELLED,EXPIRED,REFUNDED), expires_at NULL, payment_id NULL, source_type, source_reference NULL, created_at, confirmed_at)`:
  - `entry_number` is an **integer** assigned only at confirmation from `campaign_counters` (never text; text ordering breaks the canonical pool).
  - `UNIQUE(campaign_id, entry_number) WHERE entry_number IS NOT NULL`.
  - `UNIQUE(campaign_id, source_type, source_reference) WHERE source_reference IS NOT NULL` (duplicate qualification).
  - `CHECK(status <> 'CONFIRMED' OR entry_number IS NOT NULL)`.
  - `PENDING` holds count toward capacity until `expires_at`; a Celery job expires them. Capacity and per-user limits are checked while holding the `campaign_counters` row lock.
- `eligibility_records(id, entry_id NULL, campaign_id, user_id, rule_type, result, evidence JSONB, created_at)`.

## 4. To add — payments (phase 5; tables can exist earlier)
- `payments(id, user_id, campaign_id, provider, merchant_reference UNIQUE, provider_reference NULL, amount NUMERIC(18,2) CHECK>0, currency CHECK='ETB', status CHECK IN(INITIATED,PENDING,SUCCEEDED,FAILED,EXPIRED,REFUNDED), verified_at, created_at, updated_at)`, `UNIQUE(provider, provider_reference) WHERE provider_reference IS NOT NULL`.
- `payment_events(id, payment_id NULL, provider, provider_event_id NULL, event_type, payload_sha256, received_at)`, `UNIQUE(provider, provider_event_id) WHERE provider_event_id IS NOT NULL`, `UNIQUE(provider, payload_sha256)` fallback. Append-only.
- `refunds(id, payment_id, amount, reason, status, requested_by, approved_by, created_at)`.

## 5. To add — draw and evidence
- `draws(id, campaign_id UNIQUE, status CHECK IN(SCHEDULED,POOL_LOCKED,DRAWING,COMPLETED,FAILED), stage CHECK IN(NONE,ENTROPY_FETCHED,RESULTS_PERSISTED,SEED_REVEALED), seed_commitment CHAR(64) NOT NULL, pool_locked_at, locked_by NULL, planned_entropy_source, planned_entropy_round, executed_at, executed_by NULL, created_at)` — created when the campaign becomes `ACTIVE`, so the commitment predates the pool.
- `draw_secrets(draw_id PK, seed_ciphertext BYTEA, key_id, revealed_at)` — separate table and DB role (§7).
- `draw_snapshots(id, draw_id UNIQUE, entry_count, entry_numbers INT[], pool_hash CHAR(64), created_at)` — immutable.
- `draw_entropy(draw_id PK, source, round, value_hex, relays_confirmed INT ≥2, fetched_at)` — immutable.
- `draw_results(id, draw_id, prize_index, remaining_count, winner_index, entry_id, created_at, UNIQUE(draw_id, prize_index))` — immutable.
- `verification_records(id, draw_id UNIQUE, package JSONB, package_sha256, verifier_result JSONB, published_at)` — immutable.
- `winners(id, draw_result_id UNIQUE, user_id, entry_id, created_at)` — insert-only.
- `prize_fulfillments(id, winner_id, status CHECK IN(PENDING,CONTACTED,DELIVERED,DISPUTED), evidence_ref, updated_by, updated_at)` plus `prize_fulfillment_history` (append-only).
- `audit_logs(seq BIGSERIAL UNIQUE, id UUID PK, actor_user_id NULL, actor_type, action, entity_type, entity_id, request_id, ip_address INET, user_agent, old_state_hash, new_state_hash, metadata JSONB, prev_hash CHAR(64), row_hash CHAR(64), created_at)`; a trigger computes `row_hash = SHA-256(prev_hash || canonical row)` under an advisory lock; a nightly job verifies the chain and alerts on a break.
- `notifications`, `notification_templates` as in the spec.

## 6. Database-enforced invariants (Alembic migrations with tests that attempt the forbidden write)
| # | Rule |
|---|---|
| T1 | `campaigns.status` changes only along allowed transitions (`design/api-and-states.md`); every change writes `campaign_status_history` |
| T2 | Activation guards: asset `VERIFIED` with custody evidence; `FREE`/`PROMOTIONAL`, or an `entry_mode_approvals` row exists; `draws` row with commitment exists |
| T3 | No INSERT/UPDATE/DELETE on `entries` of a campaign once `POOL_LOCKED` or later |
| T4 | Entry insert/confirm only when campaign `ACTIVE`, within `max_entries` and per-user limit |
| T5 | Append-only (block UPDATE, DELETE, TRUNCATE): `audit_logs`, `draw_snapshots`, `draw_entropy`, `draw_results`, `verification_records`, `winners`, `asset_verifications`, `payment_events`, `campaign_status_history` |
| T6 | `draws`: `seed_commitment`, `pool_locked_at`, planned entropy are write-once; `stage` moves forward only |
| T7 | `draw_results` insert requires a snapshot and entropy row; entry must belong to the snapshot's `entry_numbers` |
| T8 | `winners` must correspond to a `draw_results` row of the same draw |
| T9 | Audit hash chain (§5) |

## 7. Database roles
`app_api` (no access to `draw_secrets`), `app_worker` (may read `draw_secrets` and write draw tables),
`app_migrator` (DDL only, used in deploy), `app_readonly_audit` (read-only, for AUDITOR tooling). The seed
encryption key comes from the environment/secret manager and never from the database.

## 8. Indexes
`campaigns(status)`, `campaigns(start_at,end_at)`, `entries(campaign_id,status)`, `entries(user_id)`,
`payments(campaign_id,user_id)`, `draws(campaign_id)`, `audit_logs(entity_type,entity_id)`, `audit_logs(seq)`,
`refresh_sessions(user_id)`, `refresh_sessions(family_id)`.
