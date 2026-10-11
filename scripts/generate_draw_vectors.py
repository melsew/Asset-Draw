#!/usr/bin/env python3
"""Regenerate tests/vectors/draw_v1.json from the reference engine.

Vectors are VERSIONED EVIDENCE. Never regenerate them to make a failing test pass: a change in
output means the protocol changed, which requires a new protocol version (draw_v2.json).
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.draws import engine as e  # noqa: E402

CID = "3f2b8c1e-5a47-4d0e-9b6a-1c2d3e4f5a6b"
DID = "a1b2c3d4-e5f6-4789-8abc-def012345678"
ENT = e.Entropy("drand:test-chain", 4242, "9f" * 32)

CASES = [
    ("small_10_one_prize", "01" * 32, list(range(1, 11)), 1),
    ("gaps_three_prizes", "02" * 32, [1, 2, 3, 5, 8, 13, 21, 34, 55, 89], 3),
    ("large_1000_five_prizes", "03" * 32, list(range(1, 1001)), 5),
    ("single_entry", "04" * 32, [7], 1),
    ("every_entry_wins", "05" * 32, [10, 20, 30], 3),
]


def build() -> dict:
    vectors = []
    for name, seed_hex, entries, prizes in CASES:
        seed = bytes.fromhex(seed_hex)
        results = e.run_draw(seed, CID, DID, entries, ENT, prizes)
        pkg = e.build_verification_package(seed, CID, DID, entries, ENT, results)
        vectors.append(
            {
                "name": name,
                "seed_hex": seed_hex,
                "campaign_id": CID,
                "draw_id": DID,
                "entropy": {"source": ENT.source, "round": ENT.round, "value": ENT.value_hex},
                "prize_count": prizes,
                "package": pkg,
            }
        )
    return {"protocol": e.PROTOCOL_VERSION, "note": "TEST DATA ONLY. Seeds and entropy are fixed fakes.", "vectors": vectors}


if __name__ == "__main__":
    out = ROOT / "tests" / "vectors" / "draw_v1.json"
    out.write_text(json.dumps(build(), indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out}")
