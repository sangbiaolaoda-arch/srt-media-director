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
