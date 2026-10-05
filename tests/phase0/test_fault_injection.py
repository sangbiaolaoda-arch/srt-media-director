"""Phase 0 fault-injection suite.

The whole point of Phase 0 is *falsifiability*: the validator must be provably
able to tell these five situations apart. If any of these assertions fails, the
loop is not trustworthy yet and Phase 0 is not done.

  Exp1  correct spec + correct runtime        -> PASS
  Exp2  REVERSED spec + correct runtime       -> SPEC_FAIL
  Exp3  correct spec + REVERSED runtime       -> RUNTIME_FAIL
  Exp4  correct spec + staging dropped        -> PASS (staging DRIFT, soft)
  Exp5  REVERSED spec + REVERSED runtime      -> AMBIGUOUS + evidence_request(4)
"""
import copy
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from world_state import compiler, serializer, validator  # noqa: E402
from entailment import load_contract  # noqa: E402

CASES = os.path.join(ROOT, "cases", "cause_effect")


def _load(name):
    with open(os.path.join(CASES, name), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def anchor():
    return _load("anchor.json")


@pytest.fixture
def contract():
    return load_contract("causes.v1")


@pytest.fixture
def expected_semantic():
    return _load("expected_semantic.json")


@pytest.fixture
def expected_staging():
    return _load("expected_staging.json")


def _reverse_semantic(exp):
    """Flip a SEMANTIC expectation's direction-bearing constraints."""
    out = copy.deepcopy(exp)
    flipped = []
    for c in out["hard_constraints"]:
        c = copy.deepcopy(c)
        if c["kind"] == "relation_direction":
            c["source"], c["target"] = c["target"], c["source"]
        elif c["kind"] == "temporal_precedence":
            c["before"], c["after"] = c["after"], c["before"]
        elif c["kind"] == "final_focus":
            c["object"] = "pressure"  # wrong endpoint
        flipped.append(c)
    out["hard_constraints"] = flipped
    return out


# --- the five experiments ---------------------------------------------------


def test_exp1_correct_is_pass(anchor, contract, expected_semantic, expected_staging):
    ws = compiler.compile_world_state(anchor)
    r = validator.validate(anchor, contract, expected_semantic, expected_staging, ws)
    assert r["verdict"] == "PASS", r
    assert r["spec_ok"] and r["runtime_ok"]
    assert r["staging"] == "OK"
    assert "evidence_request" not in r


def test_exp2_reversed_spec_is_spec_fail(anchor, contract, expected_semantic, expected_staging):
    bad_spec = _reverse_semantic(expected_semantic)
    ws = compiler.compile_world_state(anchor)  # runtime is correct
    r = validator.validate(anchor, contract, bad_spec, expected_staging, ws)
    assert r["verdict"] == "SPEC_FAIL", r
    assert not r["spec_ok"] and r["runtime_ok"]
    assert r["spec_diff"]["missing_in_expected"]  # the reversed direction is caught


def test_exp3_reversed_runtime_is_runtime_fail(anchor, contract, expected_semantic, expected_staging):
    ws = compiler.compile_world_state(anchor, reverse_direction=True)
    r = validator.validate(anchor, contract, expected_semantic, expected_staging, ws)
    assert r["verdict"] == "RUNTIME_FAIL", r
    assert r["spec_ok"] and not r["runtime_ok"]
    assert r["runtime_violations"]


def test_exp4_staging_drop_is_pass_with_drift(anchor, contract, expected_semantic, expected_staging):
    ws = compiler.compile_world_state(anchor, drop_staging=True)
    r = validator.validate(anchor, contract, expected_semantic, expected_staging, ws)
    assert r["verdict"] == "PASS", r
    assert r["staging"] == "DRIFT", r


def test_exp5_double_fault_is_ambiguous(anchor, contract, expected_semantic, expected_staging):
    bad_spec = _reverse_semantic(expected_semantic)
    ws = compiler.compile_world_state(anchor, reverse_direction=True)
    r = validator.validate(anchor, contract, bad_spec, expected_staging, ws)
    assert r["verdict"] == "AMBIGUOUS", r
    assert not r["spec_ok"] and not r["runtime_ok"]
    req = r["evidence_request"]
    assert len(req["questions"]) == 4, req


# --- determinism / canonicalization ----------------------------------------


def test_runtime_is_deterministic(anchor):
    h1 = serializer.world_state_hash(compiler.compile_world_state(anchor).to_dict())
    h2 = serializer.world_state_hash(compiler.compile_world_state(anchor).to_dict())
    assert h1 == h2


def test_verdict_reproducible(anchor, contract, expected_semantic, expected_staging):
    ws = compiler.compile_world_state(anchor)
    a = validator.validate(anchor, contract, expected_semantic, expected_staging, ws)
    b = validator.validate(anchor, contract, expected_semantic, expected_staging, ws)
    assert a == b


def test_constraint_normalization_is_order_independent(expected_semantic):
    cs = expected_semantic["hard_constraints"]
    s1 = serializer.norm_constraint_set(cs)
    s2 = serializer.norm_constraint_set(list(reversed(cs)))
    assert s1 == s2


def test_contracts_are_data_only():
    from entailment import available
    assert available() == ["causes.v1", "connects.v1", "follows.v1"]
