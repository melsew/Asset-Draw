# Phase 7 — Public verification
Read first: AGENTS.md, docs/draw-protocol/draw-protocol-v1.md (§5, §7).
Implement the public endpoints (no auth, rate-limited, cacheable) exposing only safe data, downloadable package, and the
`/verify/:drawId` page that runs `verifier/js/verify.mjs` **in the browser** and shows named PASS/FAIL checks plus lock
time, planned entropy round and a link to compare the beacon value. The page must work with no login and no database
access beyond fetching the package. Tests: PASS on every vector, FAIL on tampered packages, no PII in responses.
