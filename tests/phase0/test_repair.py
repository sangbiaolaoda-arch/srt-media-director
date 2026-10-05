"""Phase 0 step 10 — Repair tests.

The contract under test:

  PASS         -> NO_REPAIR_NEEDED
  SPEC_FAIL    -> propose spec fix -> re-validate -> RESOLVED
  RUNTIME_FAIL -> propose runtime fix -> re-validate -> RESOLVED
  AMBIGUOUS    -> BLOCKED + evidence request (never guesses)
  ineffective fix -> BLOCKED (a repair is another falsifiable claim)

The last case is the important one: it proves the re-verification gate really
blocks, so the loop cannot be closed by wishful thinking.
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
from repair import repair as R  # noqa: E402

CASES = os.path.join(ROOT, "cases")


def _load(case, name):
    with open(os.path.join(CASES, case, name), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def bundle():
    anchor = _load("cause_effect", "anchor.json")
    contract = load_contract("causes.v1")
    return {
        "anchor": anchor,
        "contract": contract,
        "expected_semantic": _load("cause_effect", "expected_semantic.json"),
        "expected_staging": _load("cause_effect", "expected_staging.json"),
    }


def _reverse(exp):
    out = copy.deepcopy(exp)
    for c in out["hard_constraints"]:
        if c["kind"] == "relation_direction":
            c["source"], c["target"] = c["target"], c["source"]
        elif c["kind"] == "temporal_precedence":
            c["before"], c["after"] = c["after"], c["before"]
        elif c["kind"] == "final_focus":
            c["object"] = "pressure"
    return out


def _call(bundle, ws, **kw):
    return R.repair(bundle["anchor"], bundle["contract"],
                    bundle["expected_semantic"], bundle["expected_staging"],
                    ws, **kw)


# --- the five repair outcomes ----------------------------------------------


def test_pass_needs_no_repair(bundle):
    ws = compiler.compile_world_state(bundle["anchor"], contract=bundle["contract"])
    out = _call(bundle, ws)
    assert out["status"] == "NO_REPAIR_NEEDED"
    assert out["diagnosis"]["category"] == "NO_FAULT"


def test_spec_fail_is_resolved_by_spec_fix(bundle):
    ws = compiler.compile_world_state(bundle["anchor"], contract=bundle["contract"])
    v = validator.validate(bundle["anchor"], bundle["contract"],
                           _reverse(bundle["expected_semantic"]),
                           bundle["expected_staging"], ws)
    assert v["verdict"] == "SPEC_FAIL"
    out = R.repair(bundle["anchor"], bundle["contract"],
                   _reverse(bundle["expected_semantic"]),
                   bundle["expected_staging"], ws, verdict=v)
    assert out["status"] == "RESOLVED"
    assert out["proposal"]["target"] == "spec"
    assert out["revalidation"]["verdict"] == "PASS"


def test_runtime_fail_is_resolved_by_runtime_fix(bundle):
    bad_ws = compiler.compile_world_state(bundle["anchor"], contract=bundle["contract"],
                                          reverse_direction=True)
    v = validator.validate(bundle["anchor"], bundle["contract"],
                           bundle["expected_semantic"], bundle["expected_staging"], bad_ws)
    assert v["verdict"] == "RUNTIME_FAIL"
    out = R.repair(bundle["anchor"], bundle["contract"],
                   bundle["expected_semantic"], bundle["expected_staging"],
                   bad_ws, verdict=v)
    assert out["status"] == "RESOLVED"
    assert out["proposal"]["target"] == "runtime"


def test_ambiguous_is_blocked_with_evidence_request(bundle):
    bad_ws = compiler.compile_world_state(bundle["anchor"], contract=bundle["contract"],
                                          reverse_direction=True)
    v = validator.validate(bundle["anchor"], bundle["contract"],
                           _reverse(bundle["expected_semantic"]),
                           bundle["expected_staging"], bad_ws)
    assert v["verdict"] == "AMBIGUOUS"
    out = R.repair(bundle["anchor"], bundle["contract"],
                   _reverse(bundle["expected_semantic"]),
                   bundle["expected_staging"], bad_ws, verdict=v)
    assert out["status"] == "BLOCKED"
    assert out["diagnosis"]["category"] == "UNATTRIBUTED"
    assert len(out["evidence_request"]["questions"]) == 4


def test_ineffective_repair_is_blocked(bundle):
    """A proposed fix that does not actually fix must be BLOCKED."""
    ws = compiler.compile_world_state(bundle["anchor"], contract=bundle["contract"])

    def bad_apply(proposal, anchor, contract, expected_semantic,
                  expected_staging, world_state):
        # pretend to fix the spec, but return the SAME broken spec
        return {"anchor": anchor, "contract": contract,
                "expected_semantic": _reverse(expected_semantic),
                "expected_staging": expected_staging, "world_state": world_state}

    v = validator.validate(bundle["anchor"], bundle["contract"],
                           _reverse(bundle["expected_semantic"]),
                           bundle["expected_staging"], ws)
    out = R.repair(bundle["anchor"], bundle["contract"],
                   _reverse(bundle["expected_semantic"]),
                   bundle["expected_staging"], ws, verdict=v, apply_fn=bad_apply)
    assert out["status"] == "BLOCKED"
    assert out["revalidation"]["verdict"] != "PASS"


def test_diagnose_rejects_unknown_verdict():
    with pytest.raises(ValueError):
        R.diagnose({"verdict": "MAYBE"})


def test_repair_does_not_mutate_inputs(bundle):
    before = json.dumps(bundle["expected_semantic"], sort_keys=True)
    ws = compiler.compile_world_state(bundle["anchor"], contract=bundle["contract"])
    v = validator.validate(bundle["anchor"], bundle["contract"],
                           _reverse(bundle["expected_semantic"]),
                           bundle["expected_staging"], ws)
    R.repair(bundle["anchor"], bundle["contract"],
             _reverse(bundle["expected_semantic"]),
             bundle["expected_staging"], ws, verdict=v)
    after = json.dumps(bundle["expected_semantic"], sort_keys=True)
    assert before == after


def test_repair_on_all_contracts(bundle):
    """RUNTIME_FAIL repair must close the loop for every shipped contract."""
    for case, cid in [("cause_effect", "causes.v1"),
                      ("follows_001", "follows.v1"),
                      ("connects_001", "connects.v1")]:
        anchor = _load(case, "anchor.json")
        contract = load_contract(cid)
        bad_ws = compiler.compile_world_state(anchor, contract=contract,
                                              reverse_direction=True)
        v = validator.validate(anchor, contract, _load(case, "expected_semantic.json"),
                               _load(case, "expected_staging.json"), bad_ws)
        assert v["verdict"] == "RUNTIME_FAIL"
        out = R.repair(anchor, contract, _load(case, "expected_semantic.json"),
                       _load(case, "expected_staging.json"), bad_ws, verdict=v)
        assert out["status"] == "RESOLVED", (case, out)
