"""Aesthetic normalization gates."""
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


@gate("25. Aesthetic 归一（后处理 grade 单一模型 + 双侧共享）")
def g25():
    """AESTHETIC NORMALIZATION · P2 的机器证据门禁。

    验证：① 唯一 Canonical Aesthetic 包可导入且边界守卫 PASS；
          ② 暗角模型唯一（内径 0.45，内圈为 0，边缘到 strength，单调）；
          ③ 遮幅/颗粒参数单一入口；
          ④ 光栅(raster_renderer)与播放器(html_adapter)都消费 canonical grade；
          ⑤ 无残留硬编码 grade 字面量；观察者亮度保持独立；
          ⑥ 契约 contracts/aesthetic_semantics.v1.json 存在。
    """
    import aesthetic_canonical as AC
    from aesthetic_canonical import grade as G, audit as _aud

    br = AC.boundary_report()
    assert br["status"] == "PASS", br
    AC.assert_boundaries()

    assert abs(G.VIGNETTE_INNER_RATIO - 0.45) < 1e-9
    assert G.vignette_falloff(0.0) == 0.0
    assert G.vignette_falloff(G.VIGNETTE_INNER_RATIO) == 0.0
    assert G.vignette_falloff(1.0) == 1.0
    assert G.letterbox_px(720, {"letterbox": 0.06}) == 43

    div = _aud.divergence()
    assert div["both_surfaces_consume"], div
    assert _aud.hardcoded_grade_literals() == [], _aud.hardcoded_grade_literals()

    import inspect
    import observer.pixel as _px
    assert "aesthetic_canonical" not in inspect.getsource(_px)

    import json as _json
    _root = ROOT
    with open(os.path.join(_root, "contracts", "aesthetic_semantics.v1.json")) as fh:
        _c = _json.load(fh)
    assert _c["contract_id"] == "aesthetic_semantics.v1"
    assert _c["vignette"]["inner_ratio"] == 0.45
