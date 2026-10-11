# API and state transitions

Base path `/api/v1`. Errors use one JSON shape `{error:{code,message,request_id}}`. Every mutating endpoint
writes an audit event. The frontend is never authoritative for status, payment success or winners.

## 1. Campaign state machine (server-side; enforced again by trigger T1)
| From → To | Actor | Trigger | Guard |
|---|---|---|---|
| DRAFT → SUBMITTED | VENDOR (own) | `POST /campaigns/{id}/submit` | required fields; vendor `APPROVED`; ≥1 prize asset |
| SUBMITTED → UNDER_REVIEW | CAMPAIGN_MANAGER | `POST /admin/campaigns/{id}/start-review` | — |
| UNDER_REVIEW → APPROVED | ADMIN | `POST /admin/campaigns/{id}/approve` | ≠ vendor's own user; rules reviewed |
| UNDER_REVIEW → REJECTED | ADMIN | `POST /admin/campaigns/{id}/reject` | reason |
| APPROVED → ASSET_VERIFIED | ADMIN | `POST /admin/assets/{id}/verify` (all prizes) | custody type + evidence (D-04) |
| ASSET_VERIFIED → SCHEDULED | CAMPAIGN_MANAGER | `POST /admin/campaigns/{id}/schedule` | dates valid; entry-mode gate (A-16) |
| SCHEDULED → ACTIVE | SYSTEM at `start_at` (or CAMPAIGN_MANAGER early) | job `activate_due_campaigns` | creates `draws` row, seed, published commitment |
| ACTIVE → SUSPENDED / SUSPENDED → ACTIVE | ADMIN | `POST /admin/campaigns/{id}/suspend`, `/resume` | reason; holds keep expiring |
| SCHEDULED/ACTIVE → CANCELLED | ADMIN | `POST /admin/campaigns/{id}/cancel` | reason; refund workflow if any paid entries |
| ACTIVE → ENTRY_CLOSED | SYSTEM at `end_at` or when full (CAMPAIGN_MANAGER may close early) | job `close_entries` | pending holds resolved or expired |
| ENTRY_CLOSED → POOL_LOCKED | SYSTEM at `draw_at − margin` (or CAMPAIGN_MANAGER) | job/`POST /draws/{id}/lock` | ≥ prizes entries; records planned entropy round |
| POOL_LOCKED → DRAWING | SYSTEM when planned round is published (ADMIN ≠ locker may retry) | job `execute_due_draw` / `POST /draws/{id}/execute` | protocol §6 |
| DRAWING → DRAW_COMPLETED | SYSTEM | end of execution | results persisted, package published |
| DRAW_COMPLETED → WINNER_VERIFIED | AUDITOR or ADMIN | `POST /draws/{id}/record-verification` | stored verifier result = PASS |
| WINNER_VERIFIED → PRIZE_DELIVERED | CAMPAIGN_MANAGER | `POST /admin/winners/{id}/fulfillment` | delivery evidence |
| PRIZE_DELIVERED → COMPLETED | CAMPAIGN_MANAGER | same, when all prizes delivered | — |
No other transition exists. Nobody supplies or edits a winner.

## 2. Endpoints
**Auth**: `POST /auth/otp/request`, `/auth/otp/verify` (participants) · `POST /auth/login`, `/auth/mfa/verify` (staff) · `/auth/refresh`, `/auth/logout` · `POST /auth/register` (staff invited by ADMIN only).
**Users**: `GET/PATCH /users/me` · `GET /users/me/entries`.
**Vendors**: `POST /vendors` · `GET/PATCH /vendors/me` · `POST /vendors/me/documents` · admin: `POST /admin/vendors/{id}/approve|reject|suspend`.
**Assets**: `POST/GET /assets` · `GET/PATCH /assets/{id}` · `POST /assets/{id}/submit-verification` · admin verify (above).
**Campaigns**: `GET /campaigns` (public: ACTIVE and later) · `POST /campaigns` · `GET/PATCH /campaigns/{id}` (PATCH only in DRAFT) · transitions in §1.
**Participation**: `POST /campaigns/{id}/participate` (returns entry or payment redirect; idempotency key header required) · `GET /entries/{id}`.
**Payments**: `POST /payments/{provider}/initialize` · `GET /payments/{id}` · `POST /payments/webhook/{provider}` (signature-verified, idempotent) · `GET /payments/callback/{provider}` (informational only).
**Draws**: `GET /draws/{id}` · `POST /draws/{id}/lock` · `POST /draws/{id}/execute` · `POST /draws/{id}/record-verification`.
**Public** (no auth, rate-limited, cacheable): `GET /public/campaigns/{id}` (includes seed commitment) · `GET /public/draws/{id}` · `GET /public/draws/{id}/verification` (the §5 package, only after reveal).
**Admin** (read): `/admin/vendors|assets|campaigns|payments|draws|winners|audit|reports` · `GET /admin/audit/verify-chain`.
