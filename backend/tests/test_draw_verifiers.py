import copy
import json
import shutil
import subprocess

import pytest
import verify_draw as py_verifier

from tests.draw_helpers import ROOT, load_vectors

VECTORS = load_vectors()["vectors"]
NODE = shutil.which("node")


def _ok(pkg) -> bool:
    return py_verifier.verify(pkg)[0]


def _node_ok(pkg, tmp_path) -> bool:
    f = tmp_path / "pkg.json"
    f.write_text(json.dumps(pkg))
    r = subprocess.run([NODE, str(ROOT / "verifier" / "js" / "cli.mjs"), str(f)], capture_output=True, text=True)
    assert r.returncode in (0, 1), r.stderr
    return r.returncode == 0


def _mut(pkg, fn):
    p = copy.deepcopy(pkg)
    fn(p)
    return p


# Tampering that ALWAYS breaks a package (a hash or commitment no longer matches, or a claimed result is wrong).
def _always_fail(pkg):
    return {
        "changed entry": _mut(pkg, lambda p: p["entry_numbers"].__setitem__(0, p["entry_numbers"][0] + 10**6)),
        "dropped entry": _mut(pkg, lambda p: p.update(entry_numbers=p["entry_numbers"][:-1] or [1])),
        "changed seed": _mut(pkg, lambda p: p.update(seed="ab" * 32)),
        "changed commitment": _mut(pkg, lambda p: p.update(seed_commitment="0" * 64)),
        "changed pool hash": _mut(pkg, lambda p: p.update(pool_hash="0" * 64)),
        "changed campaign": _mut(pkg, lambda p: p.update(campaign_id="00000000-0000-4000-8000-000000000009")),
        "forged winner number": _mut(pkg, lambda p: p["prizes"][0].update(winning_entry_number=p["prizes"][0]["winning_entry_number"] + 1)),
        "forged winner index": _mut(pkg, lambda p: p["prizes"][0].update(winner_index=p["prizes"][0]["winner_index"] + 1)),
        "forged pool size": _mut(pkg, lambda p: p["prizes"][0].update(remaining_count=p["prizes"][0]["remaining_count"] + 1)),
        "wrong protocol": _mut(pkg, lambda p: p.update(protocol="asset-draw/v0")),
    }


# Tampering with inputs that only feed the HMAC message. A verifier can only notice these when the
# recomputed winners differ, which is near-certain for big pools but not guaranteed for tiny ones.
# (The authenticity of the entropy value itself is checked against the public beacon, not offline.)
def _message_only(pkg):
    return {
        "changed entropy value": _mut(pkg, lambda p: p["entropy"].update(value="00" * 32)),
        "changed entropy round": _mut(pkg, lambda p: p["entropy"].update(round=p["entropy"]["round"] + 1)),
        "changed draw id": _mut(pkg, lambda p: p.update(draw_id="00000000-0000-4000-8000-000000000009")),
    }


def _tampers(pkg):
    out = _always_fail(pkg)
    if len(pkg["entry_numbers"]) >= 100:
        out.update(_message_only(pkg))
    return out


@pytest.mark.parametrize("vec", VECTORS, ids=lambda v: v["name"])
def test_python_verifier_passes_valid_vectors(vec):
    assert _ok(vec["package"])


@pytest.mark.parametrize("vec", VECTORS, ids=lambda v: v["name"])
def test_python_verifier_fails_every_tamper(vec):
    for label, bad in _tampers(vec["package"]).items():
        assert not _ok(bad), f"{vec['name']}: '{label}' was accepted"


def test_python_verifier_rejects_malformed_input():
    for bad in ({}, {"campaign_id": 1}, None):
        try:
            assert not _ok(bad)
        except (AttributeError, TypeError):
            pass  # verify() is only ever called with parsed JSON objects


def test_unsorted_or_duplicate_entries_fail():
    pkg = copy.deepcopy(VECTORS[0]["package"])
    pkg["entry_numbers"] = [2, 1] + pkg["entry_numbers"][2:]
    assert not _ok(pkg)


@pytest.mark.skipif(NODE is None, reason="node not installed")
@pytest.mark.parametrize("vec", VECTORS, ids=lambda v: v["name"])
def test_js_and_python_verifiers_agree_on_valid_and_tampered_packages(vec, tmp_path):
    assert _node_ok(vec["package"], tmp_path) is True
    for label, bad in _tampers(vec["package"]).items():
        assert _node_ok(bad, tmp_path) == _ok(bad), f"{vec['name']} / {label}: verifiers disagree"
