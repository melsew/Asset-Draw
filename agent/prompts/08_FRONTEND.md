# Phase 8 — Frontend
Read first: AGENTS.md, docs/design/api-and-states.md, docs/design/permissions-matrix.md.
Mobile-first, Amharic-first, all strings in `frontend/src/i18n/*.json` (never hard-coded; the key-parity test must stay
green). Routes as in spec §17. Install shadcn/ui now (deferred from Phase 0). Access token in memory only. Accessible
forms, clean API-error handling, low-bandwidth friendly. The UI never decides status, payment success, or winners.
Playwright E2E: register → participate → entry shown → results → verification PASS.
