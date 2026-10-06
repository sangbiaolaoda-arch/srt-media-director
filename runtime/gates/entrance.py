"""Entrance / choreography gates."""
import json  # noqa: F401
import os  # noqa: F401
import shutil  # noqa: F401
import sys  # noqa: F401
import tempfile  # noqa: F401

from gate_lib import (  # noqa: F401
    GATES, gate, RUNTIME, ROOT, EXAMPLE_SRT, EXAMPLE_OVERRIDES,
    _example_beats, _example_dsl, pytest_approx,
    _MOTION_TRUTH_DIRS, _EASE_FINGERPRINTS, _MAT_FINGERPRINTS,
)

import beat_planner  # noqa: F401
import composition_planner  # noqa: F401
import entrance_planner  # noqa: F401
import html_adapter  # noqa: F401
import pipeline  # noqa: F401
import raster_renderer  # noqa: F401
import srt_parser  # noqa: F401
import svg_art  # noqa: F401
import visual_director  # noqa: F401


@gate("5. 入场编排（节奏预算 / handoff / G 门禁）")
def g5():
    _, dsl = _example_dsl()
    entrance = entrance_planner.plan(dsl)
    audit = entrance_planner.audit(entrance)
    assert audit["status"] == "PASS", audit["issues"]
    for b in entrance["beats"]:
        assert b["pacing"]["last_meaningful_event_ratio"] >= 0.8, b["beat_id"]
        assert b["handoff"], b["beat_id"]
    # v4.1：每元素 lifecycle —— enter.after 依赖 / 注解必退场 / 拍尾要干净
    for b in entrance["beats"]:
        life = b["lifecycle"]
        for cue in b["cues"]:
            for eid in cue["elements"]:
                assert "after" in life[eid]["enter"], (b["beat_id"], eid)
        for eid, lc in life.items():
            if "_note" in eid:
                assert lc["exit"], (b["beat_id"], eid)
        assert (any(lc["exit"] for lc in life.values())
                or any(lc["enter"]["motion"] == "inherit"
                       for lc in life.values())
                or b["handoff"]["type"] == "final_hold"), b["beat_id"]
    # v4.1：合成交接链——相邻拍共享 motif → 下一拍 inherit 免重入、本拍免退场
    synth = {"beats": []}
    for i, (s0, e0) in enumerate(((0.0, 4.0), (4.0, 8.0))):
        bid = "beat_%02d" % (i + 1)
        synth["beats"].append({
            "beat_id": bid, "start_sec": s0, "end_sec": e0,
            "strategy": "single_focus", "motion_policy": "required",
            "visual_claim": "x", "relations": [], "camera": {}, "carry_over": [],
            "elements": [
                {"id": "%s_hero" % bid, "slot": "hero", "type": "motif",
                 "role": "primary", "motif": "shield", "art": "shield",
                 "color_role": "positive"},
                {"id": "%s_note" % bid, "slot": "note", "type": "text",
                 "role": "support", "text": "n", "size": "note",
                 "color_role": "neutral"},
            ]})
    ent2 = entrance_planner.plan(synth)
    assert ent2["beats"][0]["handoff"]["type"] == "carry_over"
    assert ent2["beats"][0]["lifecycle"]["beat_01_hero"]["exit"] is None
    lc2 = ent2["beats"][1]["lifecycle"]["beat_02_hero"]
    assert lc2["enter"]["motion"] == "inherit" and lc2["exit"] is None
    a2 = entrance_planner.audit(ent2)
    assert a2["status"] == "PASS", a2["issues"]
