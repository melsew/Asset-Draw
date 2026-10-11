import ast
import pathlib
import sys

import pytest

from app.draws import engine as e
from tests.draw_helpers import ROOT, load_vectors

CID = "3f2b8c1e-5a47-4d0e-9b6a-1c2d3e4f5a6b"
DID = "a1b2c3d4-e5f6-4789-8abc-def012345678"
ENT = e.Entropy("drand:test-chain", 4242, "9f" * 32)
SEED = bytes.fromhex("01" * 32)


# ---- committed vectors: the protocol's regression evidence -------------------------------------
@pytest.mark.parametrize("vec", load_vectors()["vectors"], ids=lambda v: v["name"])
def test_engine_reproduces_committed_vector(vec):
    entropy = e.Entropy(vec["entropy"]["source"], vec["entropy"]["round"], vec["entropy"]["value"])
    seed = bytes.fromhex(vec["seed_hex"])
    results = e.run_draw(seed, vec["campaign_id"], vec["draw_id"], vec["package"]["entry_numbers"],
                         entropy, vec["prize_count"])
    pkg = e.build_verification_package(seed, vec["campaign_id"], vec["draw_id"],
                                       vec["package"]["entry_numbers"], entropy, results)
    assert pkg == vec["package"]


def test_committed_vectors_equal_a_fresh_regeneration():
    sys.path.insert(0, str(ROOT / "scripts"))
    import generate_draw_vectors as gen

    assert gen.build() == load_vectors(), "protocol output changed: needs a NEW protocol version"


# ---- properties ---------------------------------------------------------------------------------
def test_same_inputs_same_winner_and_seed_changes_result_space():
    entries = list(range(1, 101))
    a = e.run_draw(SEED, CID, DID, entries, ENT, 3)
    b = e.run_draw(SEED, CID, DID, entries, ENT, 3)
    assert a == b
    winners = {e.run_draw(bytes([i]) * 32, CID, DID, entries, ENT, 1)[0].winning_entry_number for i in range(40)}
    assert len(winners) > 10  # different seeds spread across the pool


def test_every_input_influences_the_winner():
    entries = list(range(1, 1001))
    base = e.run_draw(SEED, CID, DID, entries, ENT, 1)[0]
    variants = [
        e.run_draw(SEED, "00000000-0000-4000-8000-000000000001", DID, entries, ENT, 1)[0],
        e.run_draw(SEED, CID, "00000000-0000-4000-8000-000000000002", entries, ENT, 1)[0],
        e.run_draw(SEED, CID, DID, entries, e.Entropy(ENT.source, ENT.round + 1, ENT.value_hex), 1)[0],
        e.run_draw(SEED, CID, DID, entries, e.Entropy(ENT.source, ENT.round, "9e" * 32), 1)[0],
        e.run_draw(SEED, CID, DID, entries[:-1], ENT, 1)[0],
    ]
    # With 1000 entries a coincidental match per variant is 0.1%; all five matching is impossible in practice.
    assert sum(v.winning_entry_number == base.winning_entry_number for v in variants) <= 1


def test_winners_are_distinct_and_all_from_the_pool():
    entries = [3, 9, 27, 81, 243, 729]
    res = e.run_draw(SEED, CID, DID, entries, ENT, 6)
    assert sorted(r.winning_entry_number for r in res) == entries


def test_selection_is_statistically_uniform():
    n, trials = 7, 14000
    counts = [0] * n
    for i in range(trials):
        seed = i.to_bytes(4, "big") * 8
        counts[e.unbiased_index(seed, b"m", n)] += 1
    expected = trials / n
    chi2 = sum((c - expected) ** 2 / expected for c in counts)
    assert chi2 < 22.46  # 6 degrees of freedom, p = 0.001 -> a false alarm is a 1-in-1000 event


def test_rejection_branch_advances_the_counter(monkeypatch):
    # n = 2**63 + 1 -> limit == n, so a first block >= n must be rejected and the next block used.
    n = (1 << 63) + 1
    blocks = {0: b"\xff" * 32, 1: (5).to_bytes(8, "big") + b"\x00" * 24}
    monkeypatch.setattr(e, "_block", lambda seed, msg, c: blocks[c])
    assert e.unbiased_index(SEED, b"m", n) == 5


def test_rejection_exhaustion_raises(monkeypatch):
    monkeypatch.setattr(e, "_block", lambda seed, msg, c: b"\xff" * 32)
    with pytest.raises(e.DrawError):
        e.unbiased_index(SEED, b"m", (1 << 63) + 1)


def test_index_is_in_range_for_edge_sizes():
    for n in (1, 2, 3, 2**32, 2**63 + 1, 2**64):
        assert 0 <= e.unbiased_index(SEED, b"m", n) < n


# ---- seed / commitment ---------------------------------------------------------------------------
def test_generated_seeds_are_32_bytes_and_unique():
    seeds = {e.generate_seed() for _ in range(50)}
    assert len(seeds) == 50 and all(len(s) == 32 for s in seeds)


def test_commitment_is_stable_and_seed_sensitive():
    assert e.seed_commitment(SEED) == e.seed_commitment(SEED)
    assert e.seed_commitment(SEED) != e.seed_commitment(bytes.fromhex("02" * 32))
    with pytest.raises(e.DrawError):
        e.seed_commitment(b"short")


# ---- input validation: ambiguity is refused, never guessed ---------------------------------------
@pytest.mark.parametrize(
    "entries",
    [[], [2, 1], [1, 1], [0, 1], [-1, 2], [1, 2.0], [True, 2], ["1"]],
)
def test_invalid_pools_are_rejected(entries):
    with pytest.raises(e.DrawError):
        e.canonical_pool(CID, entries)


@pytest.mark.parametrize("cid", ["", "3F2B8C1E-5A47-4D0E-9B6A-1C2D3E4F5A6B", "not-a-uuid", "3f2b8c1e5a474d0e9b6a1c2d3e4f5a6b"])
def test_non_canonical_uuids_are_rejected(cid):
    with pytest.raises(e.DrawError):
        e.pool_hash(cid, [1, 2, 3])


@pytest.mark.parametrize(
    "entropy",
    [e.Entropy("", 1, "aa"), e.Entropy("x\ny", 1, "aa"), e.Entropy("drand", 0, "aa"),
     e.Entropy("drand", 1, ""), e.Entropy("drand", 1, "AA"), e.Entropy("drand", 1, "abc")],
)
def test_invalid_entropy_is_rejected(entropy):
    with pytest.raises(e.DrawError):
        e.run_draw(SEED, CID, DID, [1, 2, 3], entropy, 1)


def test_prize_count_bounds():
    with pytest.raises(e.DrawError):
        e.run_draw(SEED, CID, DID, [1, 2], ENT, 3)
    with pytest.raises(e.DrawError):
        e.run_draw(SEED, CID, DID, [1, 2], ENT, 0)


def test_pool_encoding_is_exactly_as_documented():
    assert e.canonical_pool(CID, [1, 10, 100]) == f"asset-draw/pool/v1\n{CID}\n3\n1,10,100".encode()


def test_numeric_not_lexicographic_order_is_enforced():
    # the schema bug the review found: text order would give [1, 10, 2]
    with pytest.raises(e.DrawError):
        e.canonical_pool(CID, [1, 10, 2])


# ---- drand round arithmetic ----------------------------------------------------------------------
def test_drand_round_at_or_after():
    g, p = 1_000_000, 30
    assert e.drand_round_at_or_after(g - 5, g, p) == 1
    assert e.drand_round_at_or_after(g, g, p) == 1
    assert e.drand_round_at_or_after(g + 1, g, p) == 2
    assert e.drand_round_at_or_after(g + 30, g, p) == 2
    assert e.drand_round_at_or_after(g + 31, g, p) == 3
    with pytest.raises(e.DrawError):
        e.drand_round_at_or_after(g, g, 0)


# ---- isolation: the engine must stay pure --------------------------------------------------------
def test_engine_imports_only_the_standard_library():
    src = pathlib.Path(e.__file__).read_text()
    allowed = {"__future__", "hashlib", "hmac", "re", "secrets", "collections", "dataclasses"}
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    assert mods <= allowed, f"engine imports non-stdlib/unapproved modules: {mods - allowed}"
