# Asset-Draw — instructions for AI coding agents (tool-neutral)

Asset-Draw is a **transaction-integrity system**, not a website with a random-number button.

## Read first, in this order of authority
1. `docs/decisions.md` — approved amendments and OPEN decisions (an OPEN decision is never yours to make)
2. `docs/draw-protocol/draw-protocol-v1.md` — normative for anything about the draw
3. `docs/Asset-Draw_MVP_Implementation_Specification.docx` — spec v1.0
4. `docs/design/` — database design, API and state machine, permission matrix, security baseline
5. Existing code — code that disagrees with 1–4 is a **bug to report**, not a source of truth

## Working rules
1. One phase at a time (`agent/prompts/`). Never build the whole product in one turn.
2. **Before writing anything, inventory the repo** (`git status`, `git log`, list files). Other people and other
   AI sessions also write here. Never overwrite or delete a file you did not create in this task without
   reading it first; if two implementations of the same thing exist, stop and report the conflict.
3. Stack is locked (Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL, Redis, Celery;
   React + TypeScript + Vite, Tailwind, TanStack Query, React Router, react-i18next). No microservices,
   blockchain, or AI/ML features.
4. Every schema change is an Alembic migration that applies from an empty database. Invariants listed in
   `docs/design/database-design.md` §6 are enforced **in PostgreSQL**, with a test that attempts the forbidden write.
5. Money is `Decimal`/`NUMERIC`, currency ETB. Time is timezone-aware UTC. Primary keys are UUIDs.
6. There is **no** way for any human, role, endpoint, script or test fixture to choose, edit or influence a winner
   or any draw input. Do not add one, even "for testing" outside the pure engine's unit tests.
7. Do not change draw-protocol bytes, engine output, or `tests/vectors/` except through a protocol version bump
   approved in writing. Never regenerate vectors to make a test pass.
8. Payment success comes only from server-side provider verification. Webhooks are untrusted, signature-checked and
   idempotent. The mock provider must refuse to start in production.
9. `FREE`/`PROMOTIONAL` are the only entry modes that may activate until D-01 is closed and an
   `entry_mode_approvals` row exists for the campaign.
10. Security-critical code needs tests (authorization, concurrency, idempotency, tamper, replay). Never weaken,
    skip or delete a test to get green. Do not claim success without running the checks and showing results.
11. No secrets in git. No PII in logs, audit metadata, URLs or public evidence.
12. If a requirement is ambiguous or touches an OPEN decision, stop and report it; represent it as
    configuration, a feature flag, or an explicit blocker.

## Commands
- Backend: `cd backend && pytest -q && ruff check .`
- Verifiers: `node verifier/js/cli.mjs package.json` · `python verifier/verify_draw.py package.json`
- Frontend: `cd frontend && npm run typecheck && npm test && npm run build`
- Full stack: `cp .env.example .env && docker compose up --build`

## Report after every task
What changed and why · files changed · migrations added · exact commands run and results · open decisions or
blockers · recommended next step.
