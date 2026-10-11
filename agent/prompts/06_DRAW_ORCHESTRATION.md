# Phase 6 — Draw orchestration around the existing pure engine
Read first: AGENTS.md, docs/decisions.md, docs/draw-protocol/draw-protocol-v1.md (§6), docs/design/database-design.md §5.
The pure engine (`backend/app/draws/engine.py`), vectors and standalone verifiers **already exist and are frozen**;
do not modify their behaviour. Build only the orchestration: pool lock transaction and snapshot, planned entropy round
(`drand_round_at_or_after`), entropy fetch from allow-listed sources with two-relay agreement and no fallback,
`draw_stage` crash-safe resume under an advisory lock, execution job, seed reveal, verification package storage, the
two-person retry rule, incident alerts when entropy is late.
Tests: crash between every stage then resume produces the identical result; double execute yields one result set;
relays disagreeing aborts; nothing readable to `app_api` role before reveal; no endpoint accepts winner input.
