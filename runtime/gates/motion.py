"""Motion runtime / normalization / canonicalization gates."""
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


@gate("21. Motion Runtime（语义运动不变量）")
def g21():
    """Runtime Hardening · 语义运动执行层的机器证据门禁。

    验证：① 每个 Motion Primitive 都拥有合法 Contract；
          ② Scene/Relation/State/Motion/Conflict 可端到端执行且**确定性**；
          ③ Motion Invariants 全部通过。
    """
    import motion_runtime as MR
    from motion_runtime import (MotionRuntime, SceneGraph, make, Relation,
                                audit_contracts)
    # ① 契约自检
    ac = audit_contracts()
    assert ac["status"] == "PASS", ac["issues"]
    assert ac["count"] >= 21, ac["count"]  # 21 个语义运动原语
    # ② 端到端执行（层级 + 关系 + 运动 + 冲突求解 + Camera）
    g = SceneGraph()
    g.add("group", parent="root", x=100, y=100)
    g.add("person", parent="group", x=0, y=0, w=120, h=200)
    g.add("choice", parent="root", x=600, y=200, w=140, h=60)
    rt = MotionRuntime(g)
    rt.add(make("MOVE", "group", duration=1.0, trigger="t0",
                params={"offset": (50, 0)}),
           make("FOLLOW", "person", target="choice", duration=1.0, trigger="t0",
                params={"lag": 0.2}))
    rt.add_relation(Relation(source="person", target="choice",
                             relation_type="CAUSE", lifecycle="STRENGTHEN",
                             trigger="person.activate"))
    # 确定性：相同输入必须产生完全相同的采样
    assert rt.sample(0.5) == rt.sample(0.5), "motion runtime must be deterministic"
    frames = rt.sample_frames(1.0)
    assert len(frames) >= 5, frames
    # ③ 不变量
    v = rt.validate()
    assert v["status"] == "PASS", v["failed"]
    # 冲突求解不是 last-wins：FOLLOW 位移必须保留
    tr = rt.sample(1.0)["transforms"]["person"]
    assert tr["dx"] > 50, tr


@gate("22. Motion 归一（单一 Canonical Motion，无重复真相源）")
def g22():
    """MOTION UNIFICATION · P0 的机器证据门禁。

    验证：① 唯一的 Canonical Motion 包可导入且词汇自审通过；
          ② Motion 不重复实现缓动 / 变换 —— 对 timeline.easing 与
             geometry.matrix 的委托零数值偏差；
          ③ 边界守卫证明 canonical motion 从不 import 旧生产实现；
          ④ 契约 contracts/motion_semantics.v2.json 存在且类别集合一致。
    """
    import motion_canonical as MC
    from timeline import easing as T_EASING
    from geometry import matrix as G_MATRIX

    # ① 词汇唯一真相源
    va = MC.vocabulary.audit()
    assert va["status"] == "PASS", va["issues"]
    assert va["canonical_actions"] >= 45, va["canonical_actions"]
    for n in ("fade", "rise", "pop", "inherit", "sink", "shrink",
              "MOVE", "SCALE", "ROTATE", "MORPH", "emerge", "wipe"):
        assert MC.vocabulary.is_canonical(MC.vocabulary.canonical(n)), n

    # ② 缓动 / 进度 / 变换委托零偏差
    for p in [i / 50.0 for i in range(51)]:
        assert MC.easing.evaluate("easeOutCubic", p) == \
            pytest_approx(T_EASING.evaluate("easeOutCubic", p)), p
    assert MC.progress.progress(0.5, 0.0, 2.0, "easeOutCubic") == \
        pytest_approx(T_EASING.pr(0.5, 0.0, 2.0, "easeOutCubic"))
    ch = {"dx": 3.0, "dy": -4.0, "scale": 2.0, "rotation": 30.0}
    got = MC.transform.channels_to_matrix(x=1, y=2, channels=ch)
    exp = G_MATRIX.mat_from_parts(1 + 3.0, 2 + (-4.0), 30.0, 2.0)
    for a, b in zip(got, exp):
        assert a == pytest_approx(b), (a, b)
    from motion_runtime import contracts as _C
    for key, fn in _C.EASINGS.items():
        assert fn(0.37) == pytest_approx(T_EASING.evaluate(key, 0.37)), key

    # ③ 边界守卫：不得 import 旧生产实现
    assert MC.boundary_report()["status"] == "PASS", MC.boundary_report()
    MC.assert_boundaries()

    # ④ 契约存在且类别一致
    import json
    root = ROOT
    with open(os.path.join(root, "contracts", "motion_semantics.v2.json")) as fh:
        c = json.load(fh)
    assert c["contract_id"] == "motion_semantics.v2"
    for cat in c["categories"]:
        if not cat.startswith("_"):
            assert cat in MC.vocabulary.CATEGORIES, cat


@gate("23. Motion Canonicalization（无重复缓动 / 矩阵 / 词汇真相源）")
def g23():
    """PHASE 7 门禁：证明 Motion 已真正归一。

    ① runtime/ 下除真相源目录(timeline/observer/motion_canonical/geometry)
       外，不得再出现缓动或矩阵数学的“指纹”；
    ② scene 语义动作的 easing 必须可被唯一真相源 timeline.easing 解析；
    ③ motion registry 的 CSS 缓动同样必须可解析；
    ④ 旧生产实现不得被 canonical motion 反向依赖（边界守卫 PASS）。
    """
    root = RUNTIME

    offenders = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        rel = os.path.relpath(dirpath, root)
        top = rel.split(os.sep)[0]
        if top in _MOTION_TRUTH_DIRS or top == "gates":
            continue  # 真相源目录允许持有数学
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            if fn in ("self_test.py", "gate_lib.py"):
                continue  # 门禁自身持有指纹字符串，不是重复实现
            p = os.path.join(dirpath, fn)
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
            for fp in _EASE_FINGERPRINTS + _MAT_FINGERPRINTS:
                if fp in text:
                    offenders.append((os.path.join(rel, fn), fp))
    assert not offenders, "重复的缓动/矩阵数学仍存在: %r" % offenders

    # ② scene 语义动作 easing 可解析
    import scene.motion_compiler as _mc
    ea = _mc.audit_easing()
    assert ea["status"] == "PASS", ea["unknown"]

    # ③ motion registry 的 CSS 缓动可解析
    from timeline import easing as _E
    import motion.motion_registry as _mr
    for v in _mr.MOTION_PRIMITIVES.values():
        e = v.get("easing")
        assert e is None or _E.is_known(e), e

    # ④ 边界守卫
    import motion_canonical as MC
    assert MC.boundary_report()["status"] == "PASS", MC.boundary_report()
