"""Generated-artifact contract gates."""
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


@gate("9. 生成后契约（end_state / transition 三类型 / hold 下限 / 视线路径 / ambient）")
def g9():
    import contracts
    from common import CANVAS_W, CANVAS_H
    _, dsl = _example_dsl()
    render_plan, _, _, _ = composition_planner.plan(dsl)
    entrance = entrance_planner.plan(dsl)
    cbeats = contracts.derive(dsl, render_plan, entrance, CANVAS_W, CANVAS_H)
    audit = contracts.validate(dsl, cbeats, CANVAS_W, CANVAS_H)
    assert audit["status"] == "PASS", audit["issues"]
    for i, c in enumerate(cbeats):
        es = c["end_state"]
        assert set(es) >= {"visible", "positions", "hold_ms"}, c["beat_id"]
        assert len(c["attention_path"]) <= 4, c["beat_id"]
        assert c["primary"] in c["attention_path"], (c["beat_id"], c["primary"])
        tr = c["transition_in"]
        assert tr["type"] in contracts.TRANSITION_TYPES, tr
        assert tr["reason"], c["beat_id"]
        if i > 0 and tr["type"] == "dissolve":
            assert tr["carried"], c["beat_id"]
        if i > 0 and tr["type"] == "cut":
            assert tr.get("composition_changed"), c["beat_id"]
    # 负例：hold 过短应被阻断
    bad = {"beats": [dict(dsl["beats"][0])]}
    bad_c = [{"beat_id": dsl["beats"][0]["beat_id"], "primary": None,
              "attention_path": [], "ambient": {},
              "end_state": {"visible": [], "positions": {}, "hold_ms": 0},
              "transition_in": {"type": "cut", "carried": [], "reason": "x"}}]
    ba = contracts.validate(bad, bad_c, CANVAS_W, CANVAS_H)
    assert any(i["code"] == "HOLD_TOO_SHORT" for i in ba["issues"]), ba["issues"]
