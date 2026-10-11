# Phase 9 — QA and security
Run the full unit, integration, concurrency, E2E and security suites plus static analysis and dependency/image scans.
Attack list: RBAC on every endpoint (matrix-driven), IDOR, webhook replay/forgery, race conditions on entries,
draw crash/resume, audit-chain tamper, PII leakage in logs/evidence/URLs, rate limits, CORS/headers, upload validation,
backup and restore. Fix unambiguous findings; list the rest with severity. Produce `docs/security/report.md`.
