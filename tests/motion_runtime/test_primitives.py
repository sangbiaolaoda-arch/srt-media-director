"""L1 Primitive Tests — 每一个底层语义运动都必须稳定。

Runtime Hardening · 测试金字塔 L1。
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

from runtime.motion_runtime import (PRIMITIVES, PRIMITIVE_TYPES, SceneCtx,
                                     make, audit_contracts)
from runtime.motion_runtime.contracts import CHANNEL_NEUTRAL

ALL_TYPES = list(PRIMITIVE_TYPES)


def ctx_two():
    # source 在左上，target 在右下
    return SceneCtx(boxes={"source": (0, 0, 100, 100), "target": (300, 300, 100, 100)})


@pytest.mark.parametrize("mtype", ALL_TYPES)
def test_primitive_has_contract(mtype):
    pd = PRIMITIVES[mtype]
    assert pd.contract.motion_type == mtype
    assert pd.contract.validate() == []
    assert pd.produces, "primitive %s must declare produced channels" % mtype


@pytest.mark.parametrize("mtype", ALL_TYPES)
def test_primitive_starts_at_neutral(mtype):
    """p=0 时，除显式退场类外，通道应为中性（无运动）。"""
    p = make(mtype, "source", target="target")
    c = p.contract()
    if mtype in ("DISCONNECT", "DRAW", "ACTIVATE"):
        pytest.skip("entrance/exit primitives are non-neutral at p=0 by design")
    ch = p.sample(ctx_two(), 0.0)["source"]
    for k, v in ch.items():
        if k == "state":
            continue
        assert abs(v - CHANNEL_NEUTRAL[k]) < 1e-9, "%s.%s=%s at p=0" % (mtype, k, v)


@pytest.mark.parametrize("mtype", ALL_TYPES)
def test_primitive_is_deterministic(mtype):
    """同一输入必须产生完全相同的采样（确定性）。"""
    p = make(mtype, "source", target="target")
    a = p.sample(ctx_two(), 0.5)
    b = p.sample(ctx_two(), 0.5)
    assert a == b


@pytest.mark.parametrize("mtype", ALL_TYPES)
def test_primitive_progress_monotonic(mtype):
    p = make(mtype, "source", target="target")
    ps = [p.progress_at(t) for t in (0.0, 0.25, 0.5, 0.75, 1.0)]
    # 在起始时刻 progress 恰为 0（原语生效的边界），随后单调不减并在末尾到达 1
    assert ps[0] == 0.0
    non_none = [x for x in ps if x is not None]
    assert non_none == sorted(non_none)
    assert non_none[-1] == 1.0


def test_move_translates_by_offset():
    p = make("MOVE", "source", params={"offset": (40, -20)}, duration=1.0, start=0.0)
    end = p.sample(ctx_two(), 1.0)["source"]
    assert abs(end["dx"] - 40) < 1e-6 and abs(end["dy"] + 20) < 1e-6


def test_scale_changes_scale():
    p = make("SCALE", "source", params={"from": 1.0, "to": 2.0}, duration=1.0)
    assert abs(p.sample(ctx_two(), 1.0)["source"]["scale"] - 2.0) < 1e-6


def test_follow_keeps_lag():
    """FOLLOW 应持续响应 target，且保留 lag 落后量。"""
    p = make("FOLLOW", "source", target="target", duration=1.0,
             params={"lag": 0.2, "strength": 1.0})
    s = p.sample(ctx_two(), 1.0)["source"]
    # source 向 target 移动，但未完全到达
    assert s["dx"] > 0 and s["dy"] > 0
    assert s["dx"] < 300 and s["dy"] < 300


def test_connect_progress_reaches_one():
    p = make("CONNECT", "source", target="target", duration=1.0)
    assert abs(p.sample(ctx_two(), 1.0)["source"]["connect"] - 1.0) < 1e-6
    assert abs(p.sample(ctx_two(), 0.0)["source"]["connect"] - 0.0) < 1e-6


def test_disconnect_reverses_connect():
    p = make("DISCONNECT", "source", target="target", duration=1.0)
    assert abs(p.sample(ctx_two(), 0.0)["source"]["connect"] - 1.0) < 1e-6
    assert abs(p.sample(ctx_two(), 1.0)["source"]["connect"] - 0.0) < 1e-6


def test_repel_moves_away_from_target():
    p = make("REPEL", "source", target="target", duration=1.0,
             params={"reach": 50.0})
    s = p.sample(ctx_two(), 1.0)["source"]
    # target 在 source 右下方 → 应向左上被排斥
    assert s["dx"] < 0 and s["dy"] < 0


def test_audit_contracts_all_pass():
    a = audit_contracts()
    assert a["status"] == "PASS", a["issues"]
    assert a["count"] == len(ALL_TYPES)
