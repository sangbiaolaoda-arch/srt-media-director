"""SRT parsing and end-to-end pipeline gates."""
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


@gate("1. SRT 解析（时间真值）")
def g1():
    a = srt_parser.analyze(EXAMPLE_SRT)
    assert not a["errors"], a["errors"]
    assert len(a["cues"]) == 8, len(a["cues"])
    starts = [c["start"] for c in a["cues"]]
    assert starts == sorted(starts)
    assert abs(a["total_duration_sec"] - 38.0) < 0.01, a["total_duration_sec"]


@gate("8. 端到端流水线（30s 样例 / 全部产物 / 校验 PASS）")
def g8():
    import make_sample
    tmp = tempfile.mkdtemp()
    try:
        trimmed = os.path.join(tmp, "trimmed.srt")
        make_sample.trim_srt(EXAMPLE_SRT, trimmed, 30.0)
        report = pipeline.run(trimmed, os.path.join(tmp, "out"),
                              overrides_path=EXAMPLE_OVERRIDES,
                              render_previews=True, log=lambda *a: None)
        assert report["status"] == "PASS", json.dumps(report["issues"],
                                                      ensure_ascii=False)
        work = os.path.join(tmp, "out", "work")
        for f in ("srt-analysis.json", "beat-plan.json", "visual-plan.json",
                  "visual-dsl.json", "render-plan.json", "layout-intent.json",
                  "content-footprint.json", "layout-audit.json",
                  "entrance-plan.json", "validation-report.json"):
            assert os.path.exists(os.path.join(work, f)), f
        assert os.path.exists(os.path.join(tmp, "out", "film", "index.html"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
