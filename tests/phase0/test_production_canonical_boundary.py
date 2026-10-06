"""P0 — Production Path Canonical 收敛：边界 + 等价门禁（机器可执行）。

证明三件事：

  1. 生产入口 ``pipeline.py`` 的 import 闭包 **不** 触达 legacy motion producer
     （``motion`` / ``motion_runtime`` / ``scene``），且 **确实** 触达
     ``motion_canonical``（canonical 真正在产线上，而非仅存在）；
  2. ``entrance_planner`` 是 :mod:`motion_canonical.entrance` 的 **薄委托层**
     （motion 词表对齐部署契约、min_gap 正确转发、输出与 canonical 一致）；
  3. canonical entrance 产出的 entrance-plan **通过部署 schema**
     （enter/exit motion 落在部署枚举内 → 回归 `carry_over` / `fade_out` 漂移即 fail）。
"""
import ast
import json
import os
import sys

import jsonschema
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNTIME = os.path.join(ROOT, "runtime")
sys.path.insert(0, RUNTIME)

import common  # noqa: E402
import entrance_planner  # noqa: E402
import motion_canonical.entrance as CANON  # noqa: E402

LEGACY_PRODUCERS = {"motion", "motion_runtime", "scene"}


# --------------------------------------------------------------------------- closure
def _local_module_path(name):
    """解析 ``runtime/`` 下的本地模块/包文件；非本地返回 None。"""
    parts = name.split(".")
    direct = os.path.join(RUNTIME, *parts) + ".py"
    if os.path.isfile(direct):
        return direct
    pkg = os.path.join(RUNTIME, *parts, "__init__.py")
    if os.path.isfile(pkg):
        return pkg
    if len(parts) > 1:
        top_pkg = os.path.join(RUNTIME, parts[0], "__init__.py")
        if os.path.isfile(top_pkg):
            return top_pkg
    return None


def _imports_of(path):
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), path)
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


def _closure(entry_module):
    seen, stack = set(), [entry_module]
    while stack:
        mod = stack.pop()
        if mod in seen:
            continue
        seen.add(mod)
        path = _local_module_path(mod)
        if not path:
            continue
        for dep in _imports_of(path):
            if _local_module_path(dep) or _local_module_path(dep.split(".")[0]):
                stack.append(dep)
    return seen


def test_production_closure_excludes_legacy_includes_canonical():
    closure = _closure("pipeline")
    assert "entrance_planner" in closure
    assert "motion_canonical" in closure, closure
    assert not (closure & LEGACY_PRODUCERS), sorted(closure & LEGACY_PRODUCERS)
    assert not any(m == "observer" or m.startswith("observer.") for m in closure), closure


# --------------------------------------------------------------------------- delegate
def test_entrance_planner_is_thin_delegate():
    # 委托目标就是 canonical entrance 模块本身（无第二份算法）
    assert entrance_planner._canon is CANON
    # 无重复算法定义：plan/audit 源码不出现已删除的 _WAVE 表刻画
    import inspect
    src = inspect.getsource(entrance_planner)
    assert "PHASES = {" not in src
    assert "_WAVE = {" not in src
    # min_gap 正确转发：委托输出 == canonical(生产 G_MIN_WAVE_GAP)
    dsl = _dsl()
    assert entrance_planner.plan(dsl) == CANON.plan(dsl, common.G_MIN_WAVE_GAP)
    ent = entrance_planner.plan(dsl)
    assert entrance_planner.audit(ent) == CANON.audit(ent, common.G_MIN_WAVE_GAP)


# --------------------------------------------------------------------------- schema
def test_canonical_entrance_output_is_schema_valid():
    schema = json.load(open(os.path.join(ROOT, "schemas", "entrance-plan.schema.json")))
    plan = entrance_planner.plan(_dsl())
    jsonschema.validate(plan, schema)  # carry_over / fade_out 漂移在此 fail
    for b in plan["beats"]:
        for lc in b["lifecycle"].values():
            assert lc["enter"]["motion"] in ("fade", "rise", "pop", "inherit")
            if lc["exit"]:
                assert lc["exit"]["motion"] in ("fade", "sink", "shrink")


def test_carry_over_serializes_as_inherit():
    """跨拍共享 motif 主体：重新入场被抑制 → 序列化为部署 token "inherit"。"""
    plan = entrance_planner.plan(_dsl())
    second = plan["beats"][1]["lifecycle"]["m"]
    assert second["enter"]["motion"] == "inherit"
    assert second["exit"] is None


def _dsl():
    """两拍：第二拍沿用 motif=m1（触发 carry-over→inherit），并含 note（fade 退场）。"""
    beats = [
        {"beat_id": "beat_01", "start_sec": 0.0, "end_sec": 4.0,
         "strategy": "explanation", "relations": [], "elements": [
             {"id": "bg", "role": "ambient", "slot": "backdrop", "type": "rect"},
             {"id": "t", "role": "primary", "slot": "title", "type": "text"},
             {"id": "m", "role": "primary", "slot": "cause", "type": "motif", "motif": "m1"},
         ]},
        {"beat_id": "beat_02", "start_sec": 4.0, "end_sec": 8.0,
         "strategy": "explanation", "relations": [], "elements": [
             {"id": "note", "role": "primary", "slot": "note_right", "type": "text"},
             {"id": "m", "role": "primary", "slot": "cause", "type": "motif", "motif": "m1"},
         ]},
    ]
    return {"beats": beats}
