"""Style lock / style bible gates."""
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


@gate("10. 风格锁定（token 外颜色/线宽/字体报错）")
def g10():
    import style_guard
    _, dsl = _example_dsl()
    render_plan, _, _, _ = composition_planner.plan(dsl)
    entrance = entrance_planner.plan(dsl)
    tmp = tempfile.mkdtemp()
    try:
        path = html_adapter.compile(dsl, render_plan, entrance, "self-test", tmp)
        audit = style_guard.scan(ROOT, path)
        assert audit["status"] == "PASS", audit["issues"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@gate("14. Style Bible（视频级视觉人格随内容推导，非固定风格）")
def g14():
    import style_bible
    vp, dsl = _example_dsl()
    assert "style_bible" in vp["global_visual_grammar"]
    _, beats = _example_beats()
    bible = style_bible.derive_style_bible(beats)
    v = style_bible.validate_bible(bible)
    assert v["status"] == "PASS", v["issues"]
    for k in style_bible.REQUIRED_KEYS:
        assert k in bible, k
    # 人格由内容推导：更长句子的内容应得出非 sparse 的 density
    b2 = style_bible.derive_style_bible(
        [{"narration": "这是一句明显更长的叙述文本用于改变密度档位", "semantic_role": "explanation"}])
    assert b2["density"] in style_bible.DENSITIES
