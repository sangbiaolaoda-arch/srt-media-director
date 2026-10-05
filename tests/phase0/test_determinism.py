"""Phase 0 step 6 — Runtime determinism calibration.

A verdict is only meaningful if "the runtime produced X" is reproducible.
These tests prove:

  * N repeated runs collapse to a single canonical hash;
  * the hash is invariant to top-level key ordering;
  * the hash is invariant to PYTHONHASHSEED (no set-order leakage).
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from world_state import compiler, determinism, serializer  # noqa: E402

CASES = os.path.join(ROOT, "cases")


def _anchor(case):
    with open(os.path.join(CASES, case, "anchor.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("case", ["cause_effect", "follows_001", "connects_001"])
def test_repeated_runs_single_hash(case):
    rep = determinism.calibrate(_anchor(case), reps=1000)
    assert rep["deterministic"], rep
    assert len(rep["unique_hashes"]) == 1


@pytest.mark.parametrize("case", ["cause_effect", "follows_001", "connects_001"])
def test_canonicalization_invariant(case):
    assert determinism.canonicalization_invariant(_anchor(case))


@pytest.mark.parametrize("seed", ["0", "12345"])
def test_hash_independent_of_python_hash_seed(seed):
    anchor_path = os.path.join(CASES, "cause_effect", "anchor.json")
    h = determinism.cross_process_hash(anchor_path, seed=seed)
    assert len(h) == 16, h
    # same value regardless of PYTHONHASHSEED
    h2 = determinism.cross_process_hash(anchor_path, seed="999")
    assert h == h2


def test_hash_stable_across_in_process_calls():
    a = _anchor("cause_effect")
    h1 = serializer.world_state_hash(compiler.compile_world_state(a).to_dict())
    h2 = serializer.world_state_hash(compiler.compile_world_state(a).to_dict())
    assert h1 == h2


# --- Directive v5 §24-§25: N=100 canonical-identical gate -------------------

@pytest.mark.parametrize("case", ["cause_effect", "follows_001", "connects_001"])
def test_gate_is_100_canonical_identical(case):
    """§24: 100/100 runs must collapse to one canonical world-state."""
    g = determinism.gate(_anchor(case))
    assert g["reps"] == 100
    assert g["canonical_identical"] is True
    assert g["status"] == determinism.DETERMINISM_PASS
    assert len(g["unique_hashes"]) == 1


def test_unstable_runtime_is_classified_env_unstable(monkeypatch):
    """§25: a non-deterministic runtime -> RUNTIME_ENV_UNSTABLE, never tolerance widening."""
    a = _anchor("cause_effect")

    # inject non-determinism into the runtime under test: alternate the
    # canonical serialization of the produced world-state.
    calls = {"n": 0}
    real = compiler.compile_world_state

    class FlakyWS:
        def __init__(self, inner, n):
            self._inner = inner
            self._n = n

        def to_dict(self):
            d = self._inner.to_dict()
            if self._n % 2 == 0:
                d["injected_nondeterminism"] = True
            return d

    def flaky(anchor, *args, **kwargs):
        calls["n"] += 1
        return FlakyWS(real(anchor, *args, **kwargs), calls["n"])

    monkeypatch.setattr(determinism.compiler, "compile_world_state", flaky)
    g = determinism.gate(a, reps=4)
    assert g["canonical_identical"] is False
    assert g["status"] == determinism.RUNTIME_ENV_UNSTABLE
