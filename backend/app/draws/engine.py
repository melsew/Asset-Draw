"""Asset-Draw draw engine, protocol asset-draw/v1.

PURE and ISOLATED by design: standard library only, no database, no network, no clock.
The normative specification is docs/draw-protocol/draw-protocol-v1.md. Any change to the
byte-level behaviour here requires a NEW protocol version and new test vectors.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from collections.abc import Sequence
from dataclasses import dataclass

PROTOCOL_VERSION = "asset-draw/v1"
SEED_BYTES = 32
MAX_REJECTION_ROUNDS = 256

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_SOURCE_RE = re.compile(r"^[a-z0-9][a-z0-9:_./-]{0,127}$")
_HEX_RE = re.compile(r"^(?:[0-9a-f]{2})+$")


class DrawError(ValueError):
    """Raised for any input that would make the draw ambiguous or unverifiable."""


@dataclass(frozen=True)
class Entropy:
    """Public randomness that neither the platform nor participants control (e.g. a drand round)."""

    source: str  # e.g. "drand:<chain_hash>"
    round: int
    value_hex: str  # lowercase hex of the beacon's randomness for that round


@dataclass(frozen=True)
class PrizeResult:
    prize_index: int
    remaining_count: int  # size of the pool this prize was drawn from
    winner_index: int  # 0-based index into that (ascending) remaining pool
    winning_entry_number: int


def _check_uuid(name: str, value: str) -> None:
    if not isinstance(value, str) or not _UUID_RE.match(value):
        raise DrawError(f"{name} must be a lowercase hyphenated UUID")


def _check_entropy(e: Entropy) -> None:
    if not _SOURCE_RE.match(e.source):
        raise DrawError("entropy source has invalid characters")
    if not isinstance(e.round, int) or isinstance(e.round, bool) or e.round < 1:
        raise DrawError("entropy round must be a positive integer")
    if not _HEX_RE.match(e.value_hex):
        raise DrawError("entropy value must be non-empty lowercase hex of even length")


def generate_seed() -> bytes:
    """32 bytes from the operating-system CSPRNG."""
    return secrets.token_bytes(SEED_BYTES)


def seed_commitment(seed: bytes) -> str:
    if len(seed) != SEED_BYTES:
        raise DrawError(f"seed must be exactly {SEED_BYTES} bytes")
    return hashlib.sha256(b"asset-draw/seed/v1\n" + seed).hexdigest()


def canonical_pool(campaign_id: str, entry_numbers: Sequence[int]) -> bytes:
    """Canonical byte encoding of the locked entry pool (protocol section 3)."""
    _check_uuid("campaign_id", campaign_id)
    prev = 0
    for n in entry_numbers:
        if not isinstance(n, int) or isinstance(n, bool) or n <= prev:
            raise DrawError("entry numbers must be positive integers in strictly ascending order")
        prev = n
    if not entry_numbers:
        raise DrawError("pool is empty")
    body = ",".join(str(n) for n in entry_numbers)
    return f"asset-draw/pool/v1\n{campaign_id}\n{len(entry_numbers)}\n{body}".encode("ascii")


def pool_hash(campaign_id: str, entry_numbers: Sequence[int]) -> str:
    return hashlib.sha256(canonical_pool(campaign_id, entry_numbers)).hexdigest()


def draw_message(
    campaign_id: str, draw_id: str, pool_hash_hex: str, entropy: Entropy, prize_index: int
) -> bytes:
    _check_uuid("campaign_id", campaign_id)
    _check_uuid("draw_id", draw_id)
    if not re.fullmatch(r"[0-9a-f]{64}", pool_hash_hex):
        raise DrawError("pool_hash must be 64 lowercase hex characters")
    _check_entropy(entropy)
    if not isinstance(prize_index, int) or isinstance(prize_index, bool) or prize_index < 0:
        raise DrawError("prize_index must be a non-negative integer")
    text = (
        f"{PROTOCOL_VERSION}\n"
        f"campaign_id={campaign_id}\n"
        f"draw_id={draw_id}\n"
        f"pool_hash={pool_hash_hex}\n"
        f"entropy_source={entropy.source}\n"
        f"entropy_round={entropy.round}\n"
        f"entropy_value={entropy.value_hex}\n"
        f"prize_index={prize_index}"
    )
    return text.encode("ascii")


def _block(seed: bytes, message: bytes, counter: int) -> bytes:
    return hmac.new(seed, message + b"\x00" + counter.to_bytes(4, "big"), hashlib.sha256).digest()


def unbiased_index(seed: bytes, message: bytes, n: int) -> int:
    """Uniform integer in [0, n) via HMAC-SHA256 counter stream and rejection sampling."""
    if not isinstance(n, int) or n < 1 or n > (1 << 64):
        raise DrawError("n must be an integer in [1, 2**64]")
    limit = ((1 << 64) // n) * n  # largest multiple of n not exceeding 2**64: removes modulo bias
    for counter in range(MAX_REJECTION_ROUNDS):
        x = int.from_bytes(_block(seed, message, counter)[:8], "big")
        if x < limit:
            return x % n
    raise DrawError("rejection sampling exhausted (astronomically unlikely; investigate)")


def run_draw(
    seed: bytes,
    campaign_id: str,
    draw_id: str,
    entry_numbers: Sequence[int],
    entropy: Entropy,
    prize_count: int,
) -> list[PrizeResult]:
    """Select one winning entry per prize. Earlier winners are removed from later pools."""
    ph = pool_hash(campaign_id, entry_numbers)
    if not isinstance(prize_count, int) or prize_count < 1:
        raise DrawError("prize_count must be at least 1")
    if prize_count > len(entry_numbers):
        raise DrawError("more prizes than eligible entries")
    remaining = list(entry_numbers)
    results: list[PrizeResult] = []
    for k in range(prize_count):
        msg = draw_message(campaign_id, draw_id, ph, entropy, k)
        idx = unbiased_index(seed, msg, len(remaining))
        results.append(PrizeResult(k, len(remaining), idx, remaining[idx]))
        del remaining[idx]
    return results


def build_verification_package(
    seed: bytes,
    campaign_id: str,
    draw_id: str,
    entry_numbers: Sequence[int],
    entropy: Entropy,
    results: Sequence[PrizeResult],
) -> dict:
    """Public evidence. Contains entry NUMBERS only: no names, phones, e-mails or payment data."""
    return {
        "protocol": PROTOCOL_VERSION,
        "campaign_id": campaign_id,
        "draw_id": draw_id,
        "entry_numbers": list(entry_numbers),
        "pool_hash": pool_hash(campaign_id, entry_numbers),
        "seed_commitment": seed_commitment(seed),
        "seed": seed.hex(),
        "entropy": {"source": entropy.source, "round": entropy.round, "value": entropy.value_hex},
        "prizes": [
            {
                "prize_index": r.prize_index,
                "remaining_count": r.remaining_count,
                "winner_index": r.winner_index,
                "winning_entry_number": r.winning_entry_number,
            }
            for r in results
        ],
    }


def drand_round_at_or_after(unix_time: int, genesis_time: int, period_seconds: int) -> int:
    """First drand round published at or after unix_time (round 1 is published at genesis)."""
    if period_seconds < 1:
        raise DrawError("period must be positive")
    if unix_time <= genesis_time:
        return 1
    return -(-(unix_time - genesis_time) // period_seconds) + 1
