"""M2 — Anti-laziness machine constraints (can the system catch a lazy agent?).

Each test simulates the cheapest shortcut and asserts the system REJECTS it, plus
the positive controls. This is the machine teeth behind the process principles:
stages can't be skipped, agents can't self-certify, judges are sealed, missing
info is UNRESOLVED (not silently defaulted), lazy paths are detected, and a PASS
requires all three verification layers.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

from verification import adversarial, claims, defaults, judge_guard, stages, threelayer  # noqa: E402


# ------------------------------------------------------------------ stage machine
def _full_evidence():
    return {
        "PLANNED": {"task_contract": "c"}, "GENERATED": {"artifact_path": "a"},
        "VERIFIED": {"validator_report": "v"}, "RENDERED": {"render_report": "r"},
        "EVALUATED": {"evaluation": "e"}, "ACCEPTED": {"verdict": "P"},
    }


def test_stage_machine_runs_in_order_only():
    m = stages.StageMachine()
    for stage in stages.STAGE_ORDER:
        r = m.submit(stage, "do %s" % stage, _full_evidence()[stage])
        assert r.verdict == "UNRESOLVED"          # agent submission is never PASS
        assert r.next == ("DONE" if stage == "ACCEPTED"
                          else stages.STAGE_ORDER[stages.STAGE_ORDER.index(stage) + 1])


def test_stage_cannot_skip():
    m = stages.StageMachine()
    with pytest.raises(stages.StageOrderError):
        m.submit("GENERATED", "x", {"artifact_path": "a"})   # PLANNED not done first


def test_stage_requires_evidence():
    m = stages.StageMachine()
    with pytest.raises(stages.MissingEvidence):
        m.submit("PLANNED", "x", {})                          # no task_contract


# ------------------------------------------------------------------ claims
def test_agent_cannot_self_certify_status():
    with pytest.raises(claims.AgentSelfCertification):
        claims.AgentOutput("agent_claim", "done", {"verdict": "PASS"})
    with pytest.raises(claims.AgentSelfCertification):
        claims.AgentOutput("artifact", "ok", {"approved": True})


def test_agent_may_state_unresolved():
    out = claims.AgentOutput("agent_claim", "not sure", {"verdict": "UNRESOLVED"})
    assert out.to_dict()["data"]["verdict"] == "UNRESOLVED"


def test_only_independent_judge_issues_verdict():
    with pytest.raises(claims.Unauthorized):
        claims.issue_verdict("svc", "PASS", by="agent", evidence=["e"])
    assert claims.issue_verdict("svc", "PASS", by="validator", evidence=["e"]).verdict == "PASS"


def test_stage_promote_is_judge_only():
    m = stages.StageMachine()
    m.submit("PLANNED", "x", {"task_contract": "c"})
    with pytest.raises(claims.Unauthorized):
        m.promote("PLANNED", "PASS", by="agent")
    assert m.promote("PLANNED", "PASS", by="validator").verdict == "PASS"


# ------------------------------------------------------------------ no silent fallback
def test_unregistered_missing_is_unresolved():
    with pytest.raises(defaults.Unresolved):
        defaults.resolve("some.random.field", None)


def test_registered_default_is_logged():
    ledger = []
    val = defaults.resolve("entrance.min_gap", None, reason="unspecified", ledger=ledger)
    assert val == "G_MIN_WAVE_GAP"
    assert ledger and ledger[0]["event"] == "DEFAULT_APPLIED" and ledger[0]["reason"]


def test_present_value_needs_no_ledger():
    ledger = []
    assert defaults.resolve("entrance.min_gap", 0.25, reason="unspecified", ledger=ledger) == 0.25
    assert ledger == []


def test_missing_enter_motion_is_flagged_not_defaulted():
    dsl = {"beats": [{"beat_id": "b1", "elements": [{"id": "e1"}, {"id": "e2"}]}]}
    entrance = {"beats": [{"beat_id": "b1", "lifecycle": {"e1": {"enter": {"motion": "fade"}}}}]}
    issues = defaults.audit_entrance_completeness(dsl, entrance)
    assert issues == [{"beat": "b1", "element": "e2", "issue": "missing_enter_motion"}]


# ------------------------------------------------------------------ adversarial
def _lazy(dsl=None, entrance=None, changed=None):
    return adversarial.scan(dsl=dsl, entrance=entrance, changed_paths=changed)


def test_all_same_composition_caught():
    dsl = {"beats": [{"beat_id": "b%d" % i, "strategy": "single_focus"} for i in range(4)]}
    assert _lazy(dsl=dsl)[0]["lazy_path"] == "all_same_composition"


def test_all_fade_caught():
    entrance = {"beats": [
        {"lifecycle": {("e%d" % i): {"enter": {"motion": "fade"}}}}
        for i in range(4)
    ]}
    assert any(f["lazy_path"] == "all_fade" for f in _lazy(entrance=entrance))


def test_single_motif_caught():
    dsl = {"beats": [
        {"beat_id": "b1", "strategy": "single_focus",
         "elements": [{"id": "m", "type": "motif", "motif": "m1"}]},
        {"beat_id": "b2", "strategy": "comparison",
         "elements": [{"id": "m", "type": "motif", "motif": "m1"}]},
        {"beat_id": "b3", "strategy": "cause_effect",
         "elements": [{"id": "m", "type": "motif", "motif": "m1"}]},
        {"beat_id": "b4", "strategy": "before_after",
         "elements": [{"id": "m", "type": "motif", "motif": "m1"}]},
    ]}
    assert any(f["lazy_path"] == "single_motif" for f in _lazy(dsl=dsl))


def test_filler_decorations_caught():
    dsl = {"beats": [{"beat_id": "b1", "elements": [
        {"id": "t", "type": "text", "role": "primary"},
        {"id": "d1", "role": "decoration"}, {"id": "d2", "role": "decoration"},
        {"id": "d3", "role": "filler"}]}]}
    assert any(f["lazy_path"] == "filler_decorations" for f in _lazy(dsl=dsl))


def test_wall_of_text_caught():
    dsl = {"beats": [{"beat_id": "b1", "elements": [
        {"id": "t%d" % i, "type": "text"} for i in range(5)]}]}
    assert any(f["lazy_path"] == "wall_of_text" for f in _lazy(dsl=dsl))


def test_no_meaningful_change_caught():
    els = [{"id": "e1"}, {"id": "e2"}]
    dsl = {"beats": [{"beat_id": "b1", "elements": els},
                     {"beat_id": "b2", "elements": els}]}
    assert any(f["lazy_path"] == "no_meaningful_change" for f in _lazy(dsl=dsl))


def test_test_only_change_caught():
    assert _lazy(changed=["tests/phase0/x.py"])[0]["lazy_path"] == "test_only_change"
    assert _lazy(changed=["runtime/x.py"]) == []


def _good():
    dsl = {"beats": [
        {"beat_id": "b1", "strategy": "single_focus",
         "elements": [{"id": "t1", "type": "text"}, {"id": "m1", "type": "motif", "motif": "m1"}]},
        {"beat_id": "b2", "strategy": "comparison",
         "elements": [{"id": "t2", "type": "text"}, {"id": "m2", "type": "motif", "motif": "m2"}]},
        {"beat_id": "b3", "strategy": "cause_effect",
         "elements": [{"id": "t3", "type": "text"}, {"id": "m3", "type": "motif", "motif": "m3"}]},
        {"beat_id": "b4", "strategy": "before_after",
         "elements": [{"id": "t4", "type": "text"}, {"id": "m4", "type": "motif", "motif": "m4"}]},
    ]}
    entrance = {"beats": [
        {"lifecycle": {"t1": {"enter": {"motion": "fade"}}, "m1": {"enter": {"motion": "rise"}}}},
        {"lifecycle": {"t2": {"enter": {"motion": "pop"}}, "m2": {"enter": {"motion": "inherit"}}}},
        {"lifecycle": {"t3": {"enter": {"motion": "rise"}}, "m3": {"enter": {"motion": "pop"}}}},
        {"lifecycle": {"t4": {"enter": {"motion": "fade"}}, "m4": {"enter": {"motion": "rise"}}}},
    ]}
    return dsl, entrance


def test_clean_curated_content_has_no_findings():
    dsl, entrance = _good()
    assert _lazy(dsl=dsl, entrance=entrance) == []


# ------------------------------------------------------------------ sealed judges
def test_judge_guard_detects_modification(monkeypatch):
    monkeypatch.setattr(judge_guard, "_hash", lambda p: "TAMPERED")
    r = judge_guard.verify()
    assert r["ok"] is False and r["changed"]


def test_judge_guard_has_no_unsealed_changes():
    r = judge_guard.verify()
    assert r["ok"] is True, r


# ------------------------------------------------------------------ three layers
def test_pass_requires_all_three_layers():
    led = threelayer.empty_ledger()
    v, reasons = threelayer.verdict(led, by="validator")
    assert v == "UNRESOLVED" and reasons


def test_three_layers_with_evidence_passes():
    led = threelayer.empty_ledger()
    threelayer.record(led, "tests", "pytest", "ok")
    threelayer.record(led, "real_srt", "probe", "legacy==canonical")
    threelayer.record(led, "evaluation", "review-report", "PENDING")
    v, reasons = threelayer.verdict(led, by="validator")
    assert v == "PASS" and reasons == []
