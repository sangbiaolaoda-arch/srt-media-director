"""Phase 0 — the falsifiable loop generalized over every shipped contract.

CAUSES is covered in detail by test_fault_injection.py. Here we prove the same
loop is *contract-agnostic*: FOLLOWS and CONNECTS get the identical PASS /
SPEC_FAIL / RUNTIME_FAIL treatment, using their own contracts. This stops the
extra contracts from being dead data.
"""
import copy
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from world_state import compiler, validator  # noqa: E402
from entailment import load_contract  # noqa: E402

CASES = os.path.join(ROOT, "cases")


def _load(case, name):
    with open(os.path.join(CASES, case, name), encoding="utf-8") as f:
        return json.load(f)


def _reverse(exp):
    out = copy.deepcopy(exp)
    flipped = []
    for c in out["hard_constraints"]:
        c = copy.deepcopy(c)
        if c["kind"] == "relation_direction":
            c["source"], c["target"] = c["target"], c["source"]
        elif c["kind"] == "temporal_precedence":
            c["before"], c["after"] = c["after"], c["before"]
        elif c["kind"] == "final_focus":
            c["object"] = "__wrong__"
        flipped.append(c)
    out["hard_constraints"] = flipped
    return out


CASES_UNDER_TEST = {
    "cause_effect": "causes.v1",
    "follows_001": "follows.v1",
    "connects_001": "connects.v1",
}


@pytest.mark.parametrize("case,contract_id", list(CASES_UNDER_TEST.items()))
def test_correct_is_pass(case, contract_id):
    anchor = _load(case, "anchor.json")
    contract = load_contract(contract_id)
    ws = compiler.compile_world_state(anchor, contract=contract)
    r = validator.validate(anchor, contract, _load(case, "expected_semantic.json"),
                           _load(case, "expected_staging.json"), ws)
    assert r["verdict"] == "PASS", r


@pytest.mark.parametrize("case,contract_id", list(CASES_UNDER_TEST.items()))
def test_reversed_spec_is_spec_fail(case, contract_id):
    anchor = _load(case, "anchor.json")
    contract = load_contract(contract_id)
    ws = compiler.compile_world_state(anchor, contract=contract)
    r = validator.validate(anchor, contract, _reverse(_load(case, "expected_semantic.json")),
                           _load(case, "expected_staging.json"), ws)
    assert r["verdict"] == "SPEC_FAIL", r


@pytest.mark.parametrize("case,contract_id", list(CASES_UNDER_TEST.items()))
def test_reversed_runtime_is_runtime_fail(case, contract_id):
    anchor = _load(case, "anchor.json")
    contract = load_contract(contract_id)
    ws = compiler.compile_world_state(anchor, contract=contract, reverse_direction=True)
    r = validator.validate(anchor, contract, _load(case, "expected_semantic.json"),
                           _load(case, "expected_staging.json"), ws)
    assert r["verdict"] == "RUNTIME_FAIL", r


def test_derived_expected_matches_spec_for_all_contracts():
    for case, contract_id in CASES_UNDER_TEST.items():
        anchor = _load(case, "anchor.json")
        contract = load_contract(contract_id)
        derived = validator.derive_expected(anchor, contract)
        from world_state import serializer
        assert (serializer.norm_constraint_set(derived)
                == serializer.norm_constraint_set(
                    _load(case, "expected_semantic.json")["hard_constraints"]))
