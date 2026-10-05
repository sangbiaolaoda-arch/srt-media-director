"""Canonical motion tests (MOTION UNIFICATION · P0 — PHASE 4).

Machine evidence that Motion is truly normalized:

  1. exactly ONE canonical motion package exists and its vocabulary resolves
     every legacy spelling (motion / motion_runtime / scene / production);
  2. motion does not re-implement easing or geometry — its easing & progress
     delegate to timeline.easing and its transform delegates to geometry.matrix,
     with ZERO numerical drift against the canonical sources;
  3. the boundary guard proves canonical motion never imports the legacy
     producers (motion_runtime / scene);
  4. the contract ``motion_semantics.v2`` exists and its category set matches the
     code vocabulary.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "runtime"))

import motion_canonical as MC  # noqa: E402
from timeline import easing as T_EASING  # noqa: E402
from geometry import matrix as G_MATRIX  # noqa: E402

CONTRACT = os.path.join(ROOT, "contracts", "motion_semantics.v2.json")


# --------------------------------------------------------------------------- 1
def test_contract_exists_and_declares_categories():
    with open(CONTRACT) as fh:
        c = json.load(fh)
    assert c["contract_id"] == "motion_semantics.v2"
    assert c["implementation"] == "runtime/motion_canonical"
    for cat in c["categories"]:
        if cat.startswith("_"):
            continue
        assert cat in MC.vocabulary.CATEGORIES, cat
    assert c["action_count_floor"] <= len(MC.vocabulary.ACTIONS)


def test_single_canonical_vocabulary_resolves_all_legacy_spellings():
    # production chain vocabulary must resolve to canonical actions
    assert MC.vocabulary.canonical("fade") == "fade"
    assert MC.vocabulary.canonical("rise") == "rise"
    assert MC.vocabulary.canonical("pop") == "pop"
    assert MC.vocabulary.canonical("inherit") == "carry_over"
    assert MC.vocabulary.canonical("sink") == "sink"
    assert MC.vocabulary.canonical("shrink") == "shrink"
    # motion_runtime uppercase primitives must resolve
    for n in ("MOVE", "SCALE", "ROTATE", "MORPH", "FADE_IN", "EMPHASIZE",
              "DEEMPHASIZE", "FOLLOW", "DRAW", "REVEAL"):
        assert MC.vocabulary.is_canonical(MC.vocabulary.canonical(n)), n
    # motion/ registry names must resolve
    for n in ("emerge", "slide", "wipe", "grow", "converge", "diverge",
              "collapse", "carry_over", "static", "none"):
        assert MC.vocabulary.is_canonical(MC.vocabulary.canonical(n)), n


def test_vocabulary_audit_is_clean():
    a = MC.vocabulary.audit()
    assert a["status"] == "PASS", a["issues"]
    assert a["canonical_actions"] >= 45


# --------------------------------------------------------------------------- 2
def test_easing_delegates_to_timeline_with_zero_drift():
    for p in [i / 50.0 for i in range(51)]:
        for name in ("linear", "easeIn", "easeOut", "easeInOut",
                     "easeOutCubic", "easeInCubic", "easeInOutCubic",
                     "easeOutBack", "easeInOutBack"):
            assert MC.easing.evaluate(name, p) == pytest.approx(
                T_EASING.evaluate(name, p), abs=1e-12), (name, p)


def test_motion_runtime_easings_are_delegated_not_reimplemented():
    from motion_runtime import contracts as C
    for p in [i / 50.0 for i in range(51)]:
        for key, fn in C.EASINGS.items():
            assert fn(p) == pytest.approx(T_EASING.evaluate(key, p), abs=1e-12), (key, p)


def test_progress_delegates_to_timeline_pr():
    for t in [i / 20.0 for i in range(21)]:
        assert MC.progress.progress(t, 0.0, 2.0, "easeOutCubic") == pytest.approx(
            T_EASING.pr(t, 0.0, 2.0, "easeOutCubic"), abs=1e-12)


def test_transform_delegates_to_geometry_with_zero_drift():
    ch = {"dx": 3.0, "dy": -4.0, "scale": 2.0, "rotation": 30.0}
    got = MC.transform.channels_to_matrix(x=1, y=2, channels=ch)
    exp = G_MATRIX.mat_from_parts(1 + 3.0, 2 + (-4.0), 0 + 30.0, 1 * 2.0)
    for a, b in zip(got, exp):
        assert a == pytest.approx(b, abs=1e-12)
    # world box delegated too
    box = MC.transform.world_box(G_MATRIX.mat_from_parts(10, 0, 45, 1), 4, 2)
    assert box == G_MATRIX.world_box(G_MATRIX.mat_from_parts(10, 0, 45, 1), 4, 2)


def test_motion_runtime_scene_default_delegates_to_geometry():
    from motion_runtime.scene import local_matrix
    from motion_runtime.scene import Node
    n = Node(id="n", x=10, y=5, w=1, h=1, scale=2, rotation=30)
    got = local_matrix(n)
    exp = G_MATRIX.mat_from_parts(10, 5, 30, 2)
    for a, b in zip(got, exp):
        assert a == pytest.approx(b, abs=1e-12)


# --------------------------------------------------------------------------- 3
def test_boundary_guard_blocks_legacy_producers():
    r = MC.boundary_report()
    assert r["status"] == "PASS", r["legacy_motion_imported"]
    MC.assert_boundaries()


def test_canonical_motion_does_not_import_observer():
    src_dir = os.path.join(ROOT, "runtime", "motion_canonical")
    for fn in os.listdir(src_dir):
        if not fn.endswith(".py"):
            continue
        with open(os.path.join(src_dir, fn)) as fh:
            text = fh.read()
        assert "import observer" not in text
        assert "from observer" not in text


# --------------------------------------------------------------------------- extras
def test_entrance_lifecycle_matches_production_vocabulary():
    """Canonical entrance produces the production motion names (resolved)."""
    beat = {"beat_id": "beat_01", "start_sec": 0.0, "end_sec": 5.0,
            "elements": [
                {"id": "bg", "role": "ambient", "slot": "backdrop", "type": "rect"},
                {"id": "t", "role": "primary", "slot": "title", "type": "text"},
                {"id": "s", "role": "primary", "slot": "cause", "type": "motif"},
            ],
            "relations": [], "strategy": "explanation"}
    life = MC.entrance.build_lifecycle(beat, set(), set(), 1)
    motions = {v["enter"]["motion"] for v in life.values()}
    # all resolved to canonical actions
    for m in motions:
        assert MC.vocabulary.is_canonical(m), m
    assert life["bg"]["enter"]["motion"] == "fade"      # decor wave
    assert life["t"]["enter"]["motion"] == "rise"        # top wave
    assert life["s"]["enter"]["motion"] == "pop"         # subject wave


def test_continuity_marks_carry_over_not_reentrance():
    beats = [
        {"beat_id": "beat_01", "elements": [{"id": "m", "motif": "m1",
                                             "semantic_role": "focal", "type": "motif"}]},
        {"beat_id": "beat_02", "elements": [{"id": "m", "motif": "m1",
                                             "semantic_role": "focal", "type": "motif",
                                             "value": 2}]},
    ]
    MC.continuity.link_beats(beats)
    pol = beats[1]["elements"][0]["motion_policy"]
    assert pol["type"] in ("continue", "transform")
    assert pol["source"] == "continuity"


def test_validate_reports_missing_policy_as_error():
    plan = {"beats": [{"beat_id": "beat_01", "elements": [
        {"id": "x", "visible": True, "semantic_role": "focal",
         "motion_policy": None}]}]}
    res = MC.validate.validate_motion(plan, autocomp=False)
    assert res["status"] == "FAIL"
    assert res["motion_missing"] == 1


def test_validate_antippt_flags_decorative_motion():
    plan = {"beats": [{"beat_id": "beat_01", "elements": [
        {"id": "bg", "visible": True, "semantic_role": "decoration",
         "motion_policy": {"type": "pop", "reason": "oops"}}]}]}
    res = MC.validate.validate_motion(plan, autocomp=False)
    codes = {i["code"] for i in res["issues"]}
    assert "DECORATIVE_MOTION" in codes
