"""Motion Casebook Tests — 把 Casebook 变成真正的 Runtime Test Suite。

Runtime Hardening · 测试金字塔 L2/L3：14 个核心语义运动场景。每个案例都检查
关键帧、身份、连接线、关系与确定性。
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

from runtime.motion_runtime import casebook
from runtime.motion_runtime.casebook import CASE_NAMES, build_case, check_case


def test_14_cases_defined():
    assert len(CASE_NAMES) == 14


@pytest.mark.parametrize("name", CASE_NAMES)
def test_case_builds_and_passes(name):
    res = check_case(name)
    assert res["status"] == "PASS", [c for c in res["checks"] if c["status"] == "FAIL"]


@pytest.mark.parametrize("name", CASE_NAMES)
def test_case_is_deterministic(name):
    rt, _ = build_case(name)
    assert rt.sample(0.6) == rt.sample(0.6)


def test_run_all_is_green():
    r = casebook.run_all()
    assert r["status"] == "PASS", r["cases"]


def test_generate_writes_required_files(tmp_path):
    out = os.path.join(str(tmp_path), "casebook")
    summary = casebook.generate(out)
    assert summary["status"] == "PASS"
    for name in ("01_hierarchy", "10_camera_follow", "14_relationship_orchestra"):
        cdir = os.path.join(out, name)
        for fn in ("case.json", "expected.json", "scene.html",
                   "motion-map.json", "metrics.json"):
            p = os.path.join(cdir, fn)
            assert os.path.exists(p), p
        with open(os.path.join(cdir, "case.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["name"] == name
        assert "scene" in data and "timeline" in data


def test_hierarchy_case_moves_child_with_parent():
    """Case 01：移动父级 group，子级 person 的世界坐标必须同步平移。"""
    rt, _ = build_case("01_hierarchy")
    # 采样用 SceneCtx 计算，这里直接验证 world transform 继承
    before = rt.scene.world_center("person")
    rt.scene.get("group").x += 200
    after = rt.scene.world_center("person")
    assert abs((after[0] - before[0]) - 200) < 1e-9


def test_camera_follow_case_tracks_attention():
    rt, _ = build_case("10_camera_follow")
    assert rt.camera.attention == "choice_b"


def test_cause_effect_event_causality():
    rt, _ = build_case("12_cause_effect")
    tl = rt.events.schedule()
    assert any(e["event"] == "e_cause" for e in tl)
    assert any(e["event"] == "e_effect" for e in tl)
    ct = next(e["t"] for e in tl if e["event"] == "e_cause")
    et = next(e["t"] for e in tl if e["event"] == "e_effect")
    assert et >= ct
