"""Raster + HTML renderer gates."""
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


@gate("6. 光栅探针（真实帧 / 墨水量 / 颜色数）")
def g6():
    _, dsl = _example_dsl()
    render_plan, _, _, _ = composition_planner.plan(dsl)
    entrance = entrance_planner.plan(dsl)
    tmp = tempfile.mkdtemp()
    try:
        report = raster_renderer.render_previews(dsl, render_plan, entrance, tmp)
        assert len(report) == len(dsl["beats"])
        for bid, r in report.items():
            assert 0.005 <= r["ink_ratio"] <= 0.65, (bid, r["ink_ratio"])
            assert r["distinct_colors"] >= 12, (bid, r["distinct_colors"])
            assert os.path.exists(r["frame"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@gate("7. HTML 适配器（编译产物包含全部 beat）")
def g7():
    _, dsl = _example_dsl()
    render_plan, _, _, _ = composition_planner.plan(dsl)
    entrance = entrance_planner.plan(dsl)
    tmp = tempfile.mkdtemp()
    try:
        path = html_adapter.compile(dsl, render_plan, entrance, "self-test", tmp)
        html = open(path, encoding="utf-8").read()
        for b in dsl["beats"]:
            assert b["beat_id"] in html
        assert "requestAnimationFrame" in html
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
