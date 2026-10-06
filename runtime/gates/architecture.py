"""Runtime package architecture gates."""
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


@gate("19. Runtime 六包架构：director/compiler/render/validation/primitives/schemas 可导入且接线")
def g19():
    import os
    # (a) 目标架构的六个包必须存在且可导入
    import director, compiler, render, validation, primitives
    import schemas as SCH
    root = RUNTIME
    for pkg in ("director", "compiler", "render", "validation", "primitives", "schemas"):
        assert os.path.isdir(os.path.join(root, pkg)), "缺包 " + pkg
    # (b) 目标文件布局（用户给的结构）
    want = {
        "director": ["visual_intent.py", "grammar.py", "relationship.py"],
        "compiler": ["composition.py", "constraints.py", "layout.py", "svg_compiler.py"],
        "render": ["html_renderer.py", "playwright_renderer.py", "screenshot.py"],
        "validation": ["geometry.py", "typography.py", "safe_area.py", "visual_regression.py"],
        "primitives": ["text.py", "shape.py", "path.py", "chart.py", "connector.py", "motif.py"],
        "schemas": ["visual_intent.json", "visual_plan.json", "render_plan.json"],
    }
    for pkg, files in want.items():
        for f in files:
            assert os.path.exists(os.path.join(root, pkg, f)), "缺文件 %s/%s" % (pkg, f)
    # (c) 跨包接线可用：director → compiler → render → validation
    from director import grammar as G, relationship as REL, visual_intent as VI, critic as C
    assert len(G.GRAMMAR_OPS) == 12
    assert G.unknown_ops(["contrast", "bogus"]) == ["bogus"]
    assert REL.sinks([{"from": "a", "relation": "accumulate_into", "to": "b"},
                      {"from": "b", "relation": "crosses", "to": "c"}]) == ["c"]
    assert hasattr(VI, "derive") and hasattr(VI, "validate")
    from compiler import composition as CO, constraints as CON, layout as LAY, svg_compiler as SVGC
    assert CO.coverage() and all(CO.coverage().values())        # 每个语法都有实现可画
    assert LAY.safe_area()["margin"] == __import__("ref_frame").MARGIN
    from render import screenshot as SHOT
    be = SHOT.backends()
    assert set(be) == {"playwright", "chromium", "cairosvg"}, be
    assert any(be.values()), be                                  # 至少一个后端可用（如实探测）
    from validation import geometry, typography, safe_area
    assert callable(geometry.check) and callable(typography.check) and callable(safe_area.check)
    assert SCH.available() == ["render_plan", "visual_intent", "visual_plan"], SCH.available()
