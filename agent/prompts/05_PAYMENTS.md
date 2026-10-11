# Phase 5 — Payments (behind the D-01/D-02 gates)
Read first: AGENTS.md, docs/decisions.md, docs/design/security.md, docs/design/database-design.md §4.
Implement the `PaymentProvider` interface, a mock provider (refuses to start when ENVIRONMENT=production, tested), and
the Chapa adapter only if D-02 credentials exist. Initialize, signature-verified webhook, server-side re-verification of
status/amount/currency/campaign/merchant reference, idempotency, event log, reconciliation job, refunds workflow.
Paid entry stays behind the per-campaign `entry_mode_approvals` gate; code existing is not approval.
Tests: duplicate/replayed webhooks create no second payment or entry; forged signature rejected; wrong amount/currency
rejected; frontend-supplied success is ignored; late success after hold expiry goes to the refund/manual-review queue.
