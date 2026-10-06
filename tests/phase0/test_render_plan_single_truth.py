"""P1 — Render Plan 单一真相门禁（机器可执行）。

锁定不变量：**Render Plan 是两个渲染器唯一的几何真相**。

  1. 生产入口 ``pipeline`` 的 import 闭包 **不含** 平行几何系统
     （``compiler`` / ``composition_compiler`` / ``scene``）；几何只在
     ``composition_planner.plan`` 计算一次。
  2. 两个渲染器都以 ``render_plan`` 为几何输入契约
     （``html_adapter.compile(dsl, render_plan, ...)``、
     ``raster_renderer.render_previews(dsl, render_plan, ...)``）。
  3. HTML 播放器内嵌的 boxes **字节等于** render-plan 的 boxes（消费而非重算）。
  4. 光栅渲染器 **数据驱动** 于 render-plan 的 boxes（改 box → 输出像素随之改变）。
  5. render-plan 通过 ``schemas/render-plan.schema.json``。
"""
import ast
import inspect
import json
import os
import sys
import tempfile

import jsonschema
import pytest
from PIL import ImageChops

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNTIME = os.path.join(ROOT, "runtime")
sys.path.insert(0, RUNTIME)

import beat_planner  # noqa: E402
import composition_planner  # noqa: E402
import entrance_planner  # noqa: E402
import html_adapter  # noqa: E402
import raster_renderer  # noqa: E402
import srt_parser  # noqa: E402
import visual_director  # noqa: E402

PARALLEL_GEOMETRY = ("compiler", "composition_compiler", "scene")
GOLDEN_SRT = os.path.join(ROOT, "tests", "golden", "01-minimal", "case.srt")
GOLDEN_OV = os.path.join(ROOT, "tests", "golden", "01-minimal", "director_overrides.json")


# ------------------------------------------------------------------ closure
def _path(name):
    parts = name.split(".")
    f = os.path.join(RUNTIME, *parts) + ".py"
    if os.path.isfile(f):
        return f
    pkg = os.path.join(RUNTIME, *parts, "__init__.py")
    if os.path.isfile(pkg):
        return pkg
    if len(parts) > 1:
        top = os.path.join(RUNTIME, parts[0], "__init__.py")
        if os.path.isfile(top):
            return top
    return None


def _imports(f):
    tree = ast.parse(open(f, encoding="utf-8").read(), f)
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            out.add(n.module)
    return out


def _closure(entry):
    seen, stack = set(), [entry]
    while stack:
        m = stack.pop()
        if m in seen:
            continue
        seen.add(m)
        f = _path(m)
        if not f:
            continue
        for d in _imports(f):
            if _path(d) or _path(d.split(".")[0]):
                stack.append(d)
    return seen


def test_production_closure_has_single_geometry_producer():
    closure = _closure("pipeline")
    assert "composition_planner" in closure
    leaked = [m for m in closure
              if m in PARALLEL_GEOMETRY or m.split(".")[0] in PARALLEL_GEOMETRY]
    assert not leaked, "parallel geometry producers in production closure: %s" % leaked


def test_both_renderers_take_render_plan():
    assert "render_plan" in inspect.signature(html_adapter.compile).parameters
    assert "render_plan" in inspect.signature(raster_renderer.render_previews).parameters


# ------------------------------------------------------------------ layers
@pytest.fixture(scope="module")
def layers():
    ov = visual_director.load_overrides(GOLDEN_OV) if os.path.isfile(GOLDEN_OV) else {}
    analysis = srt_parser.analyze(GOLDEN_SRT)
    beats = beat_planner.plan_beats(analysis["cues"])
    _, dsl = visual_director.direct(beats, ov)
    render_plan, _intent, _fp, audit = composition_planner.plan(dsl)
    assert audit["status"] == "PASS"
    entrance = entrance_planner.plan(dsl)
    return dsl, render_plan, entrance


def test_html_player_boxes_equal_render_plan(layers):
    dsl, render_plan, entrance = layers
    plans = {b["beat_id"]: b for b in render_plan["beats"]}
    payload = html_adapter._payload(dsl, render_plan, entrance)
    for beat in payload:
        assert beat["boxes"] == plans[beat["id"]]["boxes"]


def test_raster_renderer_is_data_driven_from_render_plan(layers):
    dsl, render_plan, entrance = layers
    beat = dsl["beats"][0]
    pb = dict(next(b for b in render_plan["beats"] if b["beat_id"] == beat["beat_id"]))
    pe = next(b for b in entrance["beats"] if b["beat_id"] == beat["beat_id"])
    dur = beat["end_sec"] - beat["start_sec"]
    t = beat["start_sec"] + 0.8 * dur
    base = raster_renderer.draw_frame(beat, pb, pe, t)
    # 平移一个可见元素的 box；若渲染器数据驱动于 render-plan，输出必随之变化。
    eid = next(iter(pb["boxes"]))
    pb2 = {k: (dict(v) if k == "boxes" else v) for k, v in pb.items()}
    pb2["boxes"] = {k: dict(v) for k, v in pb["boxes"].items()}
    box = pb2["boxes"][eid]
    box["x"] = min(0.02, max(box.get("x", 0.5) - 0.3, 0.0))
    pb2["boxes"][eid] = box
    moved = raster_renderer.draw_frame(beat, pb2, pe, t)
    assert ImageChops.difference(base.convert("RGB"), moved.convert("RGB")).getbbox() is not None


def test_render_plan_is_schema_valid(layers):
    _, render_plan, _ = layers
    schema = json.load(open(os.path.join(ROOT, "schemas", "render-plan.schema.json")))
    jsonschema.validate(render_plan, schema)
