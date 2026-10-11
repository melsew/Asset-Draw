#!/usr/bin/env python3
"""Standalone Asset-Draw verifier for protocol asset-draw/v1.

Deliberately INDEPENDENT of the backend: standard library only, written from
docs/draw-protocol/draw-protocol-v1.md. Usage:  python verify_draw.py package.json
Exit code 0 = PASS, 1 = FAIL, 2 = unreadable input.
"""
import hashlib
import hmac
import json
import re
import sys


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def verify(pkg: dict) -> tuple[bool, list[tuple[str, bool, str]]]:
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> bool:
        checks.append((name, bool(ok), detail))
        return bool(ok)

    try:
        cid, did = pkg["campaign_id"], pkg["draw_id"]
        entries = pkg["entry_numbers"]
        ent = pkg["entropy"]
        seed = bytes.fromhex(pkg["seed"])
        prizes = pkg["prizes"]
    except (KeyError, TypeError, ValueError) as e:
        check("package is well-formed", False, f"{type(e).__name__}: {e}")
        return False, checks

    if not check("protocol version", pkg.get("protocol") == "asset-draw/v1", str(pkg.get("protocol"))):
        return False, checks
    uuid_re = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    if not check("identifiers are canonical UUIDs", uuid_re.match(str(cid)) and uuid_re.match(str(did))):
        return False, checks
    ascending = (
        isinstance(entries, list)
        and len(entries) > 0
        and all(type(n) is int for n in entries)
        and all(a < b for a, b in zip([0] + entries, entries))
    )
    if not check("entry numbers are positive, strictly ascending", ascending):
        return False, checks
    if not check("seed is 32 bytes", len(seed) == 32):
        return False, checks
    if not check(
        "entropy fields are valid",
        re.fullmatch(r"[a-z0-9][a-z0-9:_./-]{0,127}", str(ent.get("source", "")))
        and type(ent.get("round")) is int
        and ent["round"] >= 1
        and re.fullmatch(r"(?:[0-9a-f]{2})+", str(ent.get("value", ""))),
    ):
        return False, checks

    pool = f"asset-draw/pool/v1\n{cid}\n{len(entries)}\n" + ",".join(map(str, entries))
    ph = _sha(pool.encode("ascii"))
    check("pool hash matches the published entry list", ph == pkg.get("pool_hash"))
    commit = _sha(b"asset-draw/seed/v1\n" + seed)
    check("seed matches the commitment published before the draw", commit == pkg.get("seed_commitment"))

    remaining = list(entries)
    expected_indexes = list(range(len(prizes)))
    if not check("prize indexes are 0..k-1 in order", [p.get("prize_index") for p in prizes] == expected_indexes):
        return False, checks
    if not check("not more prizes than entries", 0 < len(prizes) <= len(entries)):
        return False, checks

    for k, p in enumerate(prizes):
        msg = (
            f"asset-draw/v1\ncampaign_id={cid}\ndraw_id={did}\npool_hash={ph}\n"
            f"entropy_source={ent['source']}\nentropy_round={ent['round']}\n"
            f"entropy_value={ent['value']}\nprize_index={k}"
        ).encode("ascii")
        n = len(remaining)
        limit = ((1 << 64) // n) * n
        idx = None
        for counter in range(256):
            block = hmac.new(seed, msg + b"\x00" + counter.to_bytes(4, "big"), hashlib.sha256).digest()
            x = int.from_bytes(block[:8], "big")
            if x < limit:
                idx = x % n
                break
        if idx is None:
            check(f"prize {k}: index derivation", False, "rejection sampling exhausted")
            return False, checks
        winner = remaining[idx]
        check(f"prize {k}: pool size", p.get("remaining_count") == n, f"expected {n}")
        check(f"prize {k}: winner index", p.get("winner_index") == idx, f"expected {idx}")
        check(f"prize {k}: winning entry number", p.get("winning_entry_number") == winner, f"expected {winner}")
        del remaining[idx]

    return all(ok for _, ok, _ in checks), checks


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: verify_draw.py package.json", file=sys.stderr)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as f:
            pkg = json.load(f)
    except (OSError, ValueError) as e:
        print(f"cannot read package: {e}", file=sys.stderr)
        return 2
    ok, checks = verify(pkg)
    for name, passed, detail in checks:
        print(("PASS  " if passed else "FAIL  ") + name + (f"  ({detail})" if detail and not passed else ""))
    print("\nRESULT: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
