# Asset-Draw Draw Protocol — `asset-draw/v1` (normative)

Status: **normative**. The reference implementation is `backend/app/draws/engine.py`; the independent verifiers are
`verifier/verify_draw.py` and `verifier/js/verify.mjs`. All three must agree with every vector in
`tests/vectors/draw_v1.json`. Any change to byte-level behaviour requires a **new protocol version**
(`asset-draw/v2`) and a new vector file. Vectors are never regenerated to make a failing test pass.

## 1. Goals and threat model
The operator (Asset-Draw staff, the University, a vendor, or a database administrator) must not be able to
choose, predict, or re-roll the winner, and any member of the public must be able to check the result with no
access to our systems. Personal data never appears in evidence; only entry *numbers* do.

Attacks this protocol is designed to defeat: choosing a favourable seed after seeing the pool (**re-rolling**);
adding or removing entries after the seed is known (**grinding**); biased index selection (**modulo bias**);
substituting the winner after the fact; running the draw twice and keeping one result.

## 2. Primitives and encodings
SHA-256, HMAC-SHA256. Hex is lowercase. Text is ASCII/UTF-8 with `\n` (0x0A) line ends and no trailing newline
unless stated. Integers are decimal ASCII with no sign, padding or separators. Seeds are 32 bytes from the
operating-system CSPRNG.

## 3. Objects
- **Seed commitment** = `SHA-256("asset-draw/seed/v1\n" || seed)` (raw seed bytes).
- **Canonical pool** (ASCII) = `"asset-draw/pool/v1\n" + campaign_id + "\n" + N + "\n" + n1,n2,...,nN`
  where entry numbers are positive integers, **strictly ascending**, comma-separated, and `N` is their count.
  `pool_hash = SHA-256(canonical pool)`. The pool is the set of entries in status `CONFIRMED` at lock time.
- **Entropy** = `{source, round, value}`: public randomness nobody in the system controls. `source` matches
  `^[a-z0-9][a-z0-9:_./-]{0,127}$` (e.g. `drand:<chain_hash>`), `round` ≥ 1, `value` even-length lowercase hex.
- **Draw message for prize k** (ASCII) — exactly eight lines joined by `\n`:
  ```
  asset-draw/v1
  campaign_id=<uuid>
  draw_id=<uuid>
  pool_hash=<64 hex>
  entropy_source=<source>
  entropy_round=<round>
  entropy_value=<hex>
  prize_index=<k>
  ```
  UUIDs are lowercase, hyphenated.

## 4. Winner selection
For prize index `k = 0, 1, …, P-1` over the *remaining* ascending pool (size `n`; earlier winners removed):
1. `limit = floor(2^64 / n) * n`.
2. For `counter = 0, 1, 2, …` (at most 256): `block = HMAC-SHA256(key = seed, msg = message_k || 0x00 || counter as uint32 big-endian)`;
   `x = first 8 bytes of block as big-endian uint64`.
3. If `x < limit` then `winner_index = x mod n`; stop. Otherwise continue (rejection sampling removes modulo bias).
4. `winning_entry_number = remaining[winner_index]`; delete it from `remaining`.

`P` must satisfy `1 ≤ P ≤ N`. Prizes are drawn in ascending `prize_index`.

## 5. Verification package (public JSON)
```json
{ "protocol": "asset-draw/v1", "campaign_id": "…", "draw_id": "…",
  "entry_numbers": [1,2,3], "pool_hash": "…", "seed_commitment": "…", "seed": "…",
  "entropy": {"source": "…", "round": 4242, "value": "…"},
  "prizes": [{"prize_index": 0, "remaining_count": 3, "winner_index": 1, "winning_entry_number": 2}] }
```
A verifier recomputes: pool hash, seed commitment, and for every prize the remaining-pool size, index and entry
number. It must report a named PASS/FAIL per check and never throw on bad evidence. It never needs the database.

## 6. Lifecycle rules (operational — enforced by the platform, evidenced publicly)
1. **Commit early.** When a campaign becomes `ACTIVE`, the platform generates the seed, stores it **encrypted**
   (`draw_secrets`, readable only by the worker DB role), and immediately publishes `seed_commitment` on the
   campaign page. The commitment is immutable.
2. **Lock the pool.** When entries close, a transaction snapshots the `CONFIRMED` entries, computes `pool_hash`,
   and publishes it together with the **planned entropy round** *before* that round exists. The planned round
   is the first round published at least `ENTROPY_SAFETY_MARGIN_SECONDS` (default 120) after `pool_locked_at`
   (helper: `drand_round_at_or_after`). After lock, no entry can be created, changed or cancelled.
3. **Fetch entropy.** Only from the allow-listed source(s) in configuration, for exactly the planned round,
   confirmed by at least two independent relays that return identical values. A local or substitute value is
   **never** used. If the source is unavailable the draw waits and raises an incident alert.
4. **Execute once.** Execution is by the scheduler; a human may only retry (never supply inputs), and the
   retrying user must differ from the user who triggered the lock. One `draw_results` row per
   `(draw_id, prize_index)` (unique), stage-tracked so a crash resumes without redrawing.
5. **Reveal.** After results are persisted, reveal the seed and publish the package. The seed is never
   readable by API roles before reveal.
6. **Independent check.** A recorded `WINNER_VERIFIED` transition requires a PASS from the standalone verifier
   run against the stored package, and stores the result.

## 7. Public page must also show (not checkable offline)
`pool_locked_at`, planned entropy round and its beacon publication time (so viewers can see the round did not
exist at lock), and a link to the beacon's public API so anyone can compare `entropy.value`. Offline
verification proves the arithmetic; the beacon comparison proves the entropy was not chosen.

## 8. What the protocol does not do
It does not prove prize custody, legality, or that participants are real people; those are governed by asset
verification (D-04), the entry-mode gate (D-01) and eligibility rules. It does not use a blockchain.

## 9. Change control
Vectors: `tests/vectors/draw_v1.json`, generated by `scripts/generate_draw_vectors.py`; a test asserts the file
equals a fresh regeneration. Editing the engine, generator and vectors together in one commit is a protocol
change and requires the owner's written approval and a version bump.
