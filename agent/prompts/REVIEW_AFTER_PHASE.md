# Review prompt — run in a fresh session after every phase (do not change code)
Review the repository against `docs/decisions.md`, the draw protocol, the spec and `docs/design/`. Read the actual files
and run the tests; do not trust reports. Check: requirements coverage, database-enforced invariants, authorization,
transaction safety, idempotency, concurrency tests, security, scope creep, undocumented decisions, and whether any file
was overwritten or duplicated by parallel work. Return PASS / FAIL / HIGH-RISK items with exact files and lines, and
the tests that should be added.
