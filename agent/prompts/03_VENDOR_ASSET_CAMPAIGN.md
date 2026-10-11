# Phase 3 — Vendors, assets, campaign lifecycle
Read first: AGENTS.md, docs/decisions.md, docs/design/api-and-states.md, docs/design/permissions-matrix.md.
Implement vendor onboarding/approval, asset registration and verification (custody type + evidence, D-04), campaigns,
campaign prizes and rules, and the full state machine from `api-and-states.md` §1 with `campaign_status_history`.
Transitions are enforced in the service **and** by trigger T1. Activation creates the `draws` row, generates the seed
(engine `generate_seed`), stores it encrypted, and exposes the commitment publicly.
Tests: every allowed and every forbidden transition; vendor isolation (cannot touch another vendor's data);
self-approval blocked; entry-mode gate (PAID_ENTRY cannot activate without an approval row); audit event per transition.
