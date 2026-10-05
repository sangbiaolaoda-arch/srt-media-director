"""Repair v5 (Phase 3) — verdict-driven repair + Improvement Gate + Rollback.

Directive v5 §46, §62, §64. Repair is driven strictly by the *verdict*, and it
only ever keeps a change that strictly improves the outcome (Improvement Gate).
A broken observer or a dead environment is NEVER auto-patched (§43, §46).
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
        "anchor": anchor, "contract": contract,
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


# --- §46: every v5 verdict maps to its own repair family --------------------

def test_all_v5_verdicts_are_diagnosable():
    for v, cat in [("PASS", R.CATEGORY_NO_FAULT),
                   ("SPEC_FAIL", R.CATEGORY_SPEC_DEFECT),
                   ("RUNTIME_FAIL", R.CATEGORY_RUNTIME_DEFECT),
                   ("RENDER_FAIL", R.CATEGORY_RENDER_DEFECT),
                   ("OBSERVATION_FAIL", R.CATEGORY_OBSERVATION_DEFECT),
                   ("ENVIRONMENT_FAIL", R.CATEGORY_ENVIRONMENT_DEFECT),
                   ("PERCEPTUAL_DRIFT", R.CATEGORY_PERCEPTUAL),
                   ("AMBIGUOUS", R.CATEGORY_UNATTRIBUTED)]:
        d = R.diagnose({"verdict": v})
        assert d["category"] == cat, (v, d)


def test_diagnose_still_rejects_unknown_verdict():
    with pytest.raises(ValueError):
        R.diagnose({"verdict": "MAYBE"})


# --- §43/§46: non-code faults are NOT auto-patched --------------------------

def test_dead_environment_is_not_auto_repaired(bundle):
    out = R.repair(bundle["anchor"], bundle["contract"], bundle["expected_semantic"],
                   bundle["expected_staging"],
                   compiler.compile_world_state(bundle["anchor"], contract=bundle["contract"]),
                   verdict={"verdict": "ENVIRONMENT_FAIL"})
    assert out["status"] == "UNREPAIRABLE"
    assert out["workflow"] == "BLOCKED"
    assert out["proposal"]["action"] == "restore_environment"
    assert "revalidation" not in out  # nothing was applied


def test_observer_drop_is_not_auto_repaired(bundle):
    out = R.repair(bundle["anchor"], bundle["contract"], bundle["expected_semantic"],
                   bundle["expected_staging"],
                   compiler.compile_world_state(bundle["anchor"], contract=bundle["contract"]),
                   verdict={"verdict": "OBSERVATION_FAIL", "problems": []})
    assert out["status"] == "BLOCKED"
    assert out["proposal"]["target"] == "observer"


def test_perceptual_drift_is_advisory_not_auto_patched(bundle):
    out = R.repair(bundle["anchor"], bundle["contract"], bundle["expected_semantic"],
                   bundle["expected_staging"],
                   compiler.compile_world_state(bundle["anchor"], contract=bundle["contract"]),
                   verdict={"verdict": "PERCEPTUAL_DRIFT"})
    assert out["status"] == "BLOCKED"
    assert out["proposal"]["target"] is None
    assert out["proposal"]["action"] == "flag_perceptual_drift"


# --- §64 H: a render defect is repairable and re-verified -------------------

def test_render_fail_is_repairable_and_reverified(bundle):
    """RENDER_FAIL -> propose renderer fix -> re-validate -> RESOLVED (with a fix provided)."""
    ws = compiler.compile_world_state(bundle["anchor"], contract=bundle["contract"])

    def good_render_apply(proposal, anchor, contract, expected_semantic,
                          expected_staging, world_state):
        return {"anchor": anchor, "contract": contract,
                "expected_semantic": expected_semantic,
                "expected_staging": expected_staging, "world_state": world_state}

    out = R.repair(bundle["anchor"], bundle["contract"], bundle["expected_semantic"],
                   bundle["expected_staging"], ws,
                   verdict={"verdict": "RENDER_FAIL"}, apply_fn=good_render_apply)
    assert out["proposal"]["target"] == "renderer"
    assert out["revalidation"]["verdict"] == "PASS"
    assert out["status"] == "RESOLVED"


# --- Improvement Gate + Rollback (§62) --------------------------------------

def test_gate_keeps_strict_improvement():
    g = R.improvement_gate(0.40, 0.55)
    assert g["decision"] == "KEEP"
    assert g["gain"] > 0


def test_gate_rolls_back_regression():
    g = R.improvement_gate(0.60, 0.55)
    assert g["decision"] == "ROLLBACK"


def test_gate_rolls_back_no_change():
    """Equal score is NOT an improvement -> rollback (no free passes)."""
    assert R.improvement_gate(0.5, 0.5)["decision"] == "ROLLBACK"


def test_min_gain_required():
    assert R.improvement_gate(0.5, 0.51, min_gain=0.05)["decision"] == "ROLLBACK"
    assert R.improvement_gate(0.5, 0.60, min_gain=0.05)["decision"] == "KEEP"


def test_repair_with_gate_selects_survivor():
    kept = R.repair_with_gate(0.3, 0.7, rollback_to="old", candidate="new")
    assert kept["survived"] == "new" and kept["workflow"] == "RESOLVED"
    rolled = R.repair_with_gate(0.7, 0.4, rollback_to="old", candidate="new")
    assert rolled["survived"] == "old" and rolled["workflow"] == "BLOCKED"


def test_workflow_state_layer_separation():
    assert R.workflow_state(R.STATUS_RESOLVED) == "RESOLVED"
    assert R.workflow_state(R.STATUS_BLOCKED) == "BLOCKED"
    assert R.workflow_state(R.STATUS_UNREPAIRABLE) == "BLOCKED"
