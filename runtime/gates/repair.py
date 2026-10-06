"""Repair-routing gates."""
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


@gate("12. 故障路由（症状 → 修复层 → 单变量预算）")
def g12():
    import repair_routing
    r = repair_routing.route({"code": "CARRY_NOT_IN_PREV", "msg": "x"})
    assert r["layer"] == "transition", r
    r = repair_routing.route({"code": "STYLE_COLOR", "msg": "x"})
    assert r["layer"] == "token", r
    r = repair_routing.route({"code": "HOLD_TOO_SHORT", "msg": "x"})
    assert r["layer"] == "contract", r
    b = repair_routing.RepairBudget(budget=2)
    assert b.attempt("beat_01") and b.attempt("beat_01")
    assert not b.attempt("beat_01"), "第 3 次应超预算"
    assert "beat_01" in b.exhausted()
