# Decision register

Precedence when documents disagree (highest first):
1. Approved amendments in this register
2. `docs/draw-protocol/draw-protocol-v1.md` (normative for anything about the draw)
3. `docs/Asset-Draw_MVP_Implementation_Specification.docx` (spec v1.0)
4. Documents in `docs/design/`
5. Existing code (code that disagrees with 1–4 is a **bug to report**, never a source of truth)

Approvals below were given by the product owner by delegation on 2026-09-29 ("proceed on the reviewer's
recommendations"). Items marked **OPEN** cannot be decided by engineering or by an AI agent.

## Open decisions (block the listed work)
| ID | Decision | Owner | Blocks | Default until decided |
|---|---|---|---|---|
| D-01 | Paid entry vs promotional/free entry; NLA licensing | Owner + legal counsel | Activating `PURCHASE`/`PAID_ENTRY`; Phase 5 production use | Only `FREE`/`PROMOTIONAL` can activate |
| D-02 | Payment provider account and API access (Chapa/Telebirr) | Owner | Phase 5 real provider | Mock provider, non-production only |
| D-03 | SMS/OTP provider | Owner | Phase 2 OTP in production | Console/mock SMS in dev only |
| D-04 | Prize custody/escrow acceptance criteria | Owner + legal | Campaign activation | `asset_verifications` requires custody type + evidence |
| D-06 | Independent audit authority and evidence they receive | Owner + University | Pilot | `AUDITOR` role, read-only |
| D-07 | Personal-data retention schedule | Owner + legal | Pilot | Never delete financial or draw evidence; PII purge is a later decision |
| D-08 | Fallback if the entropy beacon is unavailable for > N hours | Owner + auditor | Pilot | Draw waits; incident alert; no local substitute |
| D-09 | Beacon choice and chain hash to allow-list (drand chain) | Owner | Phase 6 production | Allow-list empty in production; test source only in dev |

## Approved amendments
| ID | Amendment | Status |
|---|---|---|
| A-01 | Seed generated at campaign `ACTIVE`, commitment published immediately | APPROVED — protocol §6.1 |
| A-02 | External entropy from a public beacon mixed into the draw message | APPROVED, **implemented** in engine |
| A-03 | Fully specified serialization, rejection sampling, published test vectors | APPROVED, **implemented** (engine + vectors) |
| A-04 | Multiple prizes with `prize_index`, earlier winners removed | APPROVED, **implemented** in engine; DB in design |
| A-05 | Crash-safe single execution: `draw_stage`, `UNIQUE(draw_id, prize_index)`, advisory lock | APPROVED — `design/database-design.md` |
| A-06 | Invariants enforced by PostgreSQL triggers/constraints | APPROVED — `design/database-design.md` §6 |
| A-07 | Hash-chained audit log | APPROVED — `design/database-design.md` §5 |
| A-08 | Entry reservation holds with expiry | APPROVED — `design/database-design.md` §3 |
| A-09 | Participants log in by phone + OTP; staff by email + password + TOTP | APPROVED (staff MFA = A-14) |
| A-10 | Per-user/per-phone entry limits via campaign rules | APPROVED |
| A-11 | Two-person rule: retrying user ≠ user who triggered lock; scheduler is default actor | APPROVED — protocol §6.4 |
| A-12 | Store UTC, display Africa/Addis_Ababa; Ethiopian calendar display is a later option | APPROVED |
| A-13 | This spec is canonical over the earlier Flutter/Next.js scaffold | APPROVED |
| A-14 | Mandatory TOTP MFA for every staff role | APPROVED |
| A-15 | Mock payment provider refuses to start when `ENVIRONMENT=production`; tested | APPROVED |
| A-16 | Paid-entry gate is per campaign via `entry_mode_approvals` (approver, date, legal reference), not one global flag | APPROVED |
| A-17 | Standalone verifiers (Python + JavaScript) independent of backend code | APPROVED, **implemented** |
| A-18 | Coding agent: any tool that reads `AGENTS.md`; primary workflow Claude Code (`CLAUDE.md` imports `AGENTS.md`); Kiro optional | APPROVED |
