"""scene_test.py — Phase 2 场景编译层的独立验证套件。

与 spec_test.py / self_test.py 相互独立，不与既有门禁耦合。每项驱动一个
scene 模块：既证明合规输入通过，又证明违规输入被拦（门禁「会咬人」）。
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

_P, _F = [], []


def chk(name, cond):
    (_P if cond else _F).append(name)
    print(("  PASS  " if cond else "  FAIL  ") + name)
    return cond


def t_scene_graph():
    from scene.scene_graph import SceneGraph
    g = SceneGraph("s")
    p = g.add("s", "person", x=100, y=50, w=40, h=40)
    h = g.add("person", "head", x=10, y=0, w=20, h=20)
    b0 = h.world_box()
    p.move(30, 10)
    b1 = h.world_box()
    chk("scene: 子随父动 (move)",
        abs(b1[0] - b0[0] - 30) < 1e-6 and abs(b1[1] - b0[1] - 10) < 1e-6)
    p.scale = 2.0
    chk("scene: 缩放继承 (scale)", abs(h.world_scale() - 2.0) < 1e-6
        and abs(h.world_box()[2] - 40) < 1e-6)
    p.opacity = 0.5
    chk("scene: 不透明度继承", abs(h.world_opacity() - 0.5) < 1e-6)
    cl = g.clone("t")
    chk("scene: clone 保留 id 与结构",
        cl.has("person") and cl.has("head") and cl.get("head").parent.id == "person")


def t_relation():
    from scene.scene_graph import SceneGraph
    from scene.relation_graph import RelationGraph
    g = SceneGraph("s")
    g.add("s", "a", w=40, h=40)
    g.add("s", "b", w=40, h=40)
    r = RelationGraph("s")
    r.right_of("a", "b")
    chk("relation: 已知类型通过", r.validate(g)["status"] == "PASS")
    r.inside("x", "b")
    res = r.validate(g)
    chk("relation: 未解析端点被拦",
        res["status"] == "FAIL" and any(i["code"] == "RELATION_UNRESOLVED"
                                        for i in res["issues"]))
    try:
        r.add("a", "b", "not_a_type")
        ok = False
    except ValueError:
        ok = True
    chk("relation: 未知关系类型报错", ok)


def t_solver():
    from scene.scene_graph import SceneGraph
    from scene.relation_graph import RelationGraph
    from scene.constraint_solver import ConstraintSolver
    g = SceneGraph("s")
    a = g.add("s", "choice", w=60, h=40)
    b = g.add("s", "person", w=60, h=40)
    b.set_pos(200, 150)
    r = RelationGraph("s")
    r.right_of("choice", "person", gap=30)
    ConstraintSolver(g, r, (680, 382)).solve()
    ax, ay, aw, ah = a.world_box()
    bx, by, bw, bh = b.world_box()
    chk("solver: right_of 放在右侧", ax > bx + bw - 1 and abs(ay - by) < 30)
    # 移动锚点 → 重新求解后跟随
    b.set_pos(100, 100)
    ConstraintSolver(g, r, (680, 382)).solve()
    chk("solver: 锚点移动后重算", a.world_box()[0] < ax)


def t_motion():
    from scene import motion_compiler as MC
    e = MC.compile_action("expand")
    chk("motion: expand 含 stagger+channels",
        e.get("stagger") and "scale" in e.get("channels", {}))
    c = MC.compile_action("collapse", duration=0.7)
    chk("motion: 覆盖 duration", c["duration"] == 0.7)
    try:
        MC.compile_action("nope"); ok = False
    except ValueError:
        ok = True
    chk("motion: 未知动作报错", ok)


def t_state_transition():
    from scene import dsl
    d = dsl.scene("s")
    d.element("person", eid="person").weight("primary").at("center").size(60, 60)
    grp = d.group("choices").weight("secondary")
    grp.child("chip", "c1", w=40, h=30)
    d.state("start").show("person").show("c1")
    d.state("overload").show("person").expand("choices", 3)
    d.transition("start", "overload").expand(grp).stagger(grp)
    ctx = d.compile()
    chk("state: 迁移引用存在", ctx["states"].validate()["status"] == "PASS")
    snap = ctx["states"].get("overload").apply(ctx["graph"])
    chk("state: expand 改变子元素数量",
        len([c for c in snap.get("choices").children if c.visible]) == 3)
    m = ctx["transitions"][0].to_motion()
    chk("transition: 语义动作→动画", m["motions"] and m["motions"][0]["action"] == "expand")
    ctx["states"].transition("ghost", "start")
    chk("state: 未定义状态被拦",
        ctx["states"].validate()["status"] == "FAIL")


def t_timeline():
    from scene.timeline import TimelineGraph
    t = TimelineGraph()
    t.add("person", "slide", dur=0.5)
    t.add("choices", "surround", after="person", dur=0.6)
    t.add("arrow", "draw", after="choices", dur=0.4)
    s = t.schedule()
    chk("timeline: after 依次排布",
        s["person"]["start"] < s["choices"]["start"] < s["arrow"]["start"])
    t.add("bad", "appear", after="missing")
    chk("timeline: 悬空锚点被拦",
        any(i["code"] == "TIMELINE_DANGLING" for i in t.audit()["issues"]))


def t_entrance():
    from scene import entrance as EN
    good = [EN.make("a", "fade", start=0.0, duration=0.4, reason="主入场")]
    chk("entrance: 完整计划通过", EN.audit(good)["status"] == "PASS")
    bad = [{"id": "a", "entrance": {"method": "fade", "start": 0,
                                    "duration": 0.4, "easing": "easeOut"}}]
    chk("entrance: 缺 reason 被拦",
        EN.audit(bad)["status"] == "FAIL")
    chk("entrance: 可见节点无计划被拦",
        EN.audit([], visible_ids=["x"])["status"] == "FAIL")


def t_weight_composition():
    from scene.scene_graph import SceneGraph
    from scene import visual_weight as VW, composition as C
    g = SceneGraph("s")
    g.add("s", "a", w=40, h=40, weight="support")
    g.add("s", "b", w=40, h=40, weight="support")
    res = VW.audit(g)
    chk("weight: 无 primary 告警",
        any(i["code"] == "WEIGHT_NO_PRIMARY" for i in res["issues"]))
    n = g.add("s", "c", w=80, h=60)
    C.place(n, "center", (680, 382))
    chk("composition: center 定位", n.data.get("explicit_pos") is True
        and abs(n.world_box()[0] - (680 * 0.5 - 40)) < 1e-6)


def t_render_plan_and_validator():
    from scene import dsl, render_plan, validator
    d = dsl.scene("s")
    p = d.element("person", eid="person").weight("primary").at("center").size(120, 150)
    p.child("head", "p_head", x=40, y=0, w=40, h=40)
    grp = d.group("choices").weight("secondary")
    grp.child("chip", "c1", w=70, h=40)
    d.surround(grp, p)
    d.state("start").show("person").show("c1")
    d.enter("person", action="slide", duration=0.5)
    d.enter("choices", action="surround", after="person", duration=0.6)
    plan = render_plan.compile(d.compile())
    chk("render_plan: 生成根节点像素盒子",
        "person" in plan["boxes"] and "choices" in plan["boxes"])
    chk("render_plan: 生成帧", len(plan["frames"]) == 1)
    chk("validator: 合规计划 PASS", validator.validate(plan)["status"] == "PASS")
    plan["entrances"] = [e for e in plan["entrances"] if e["id"] != "person"]
    v = validator.validate(plan)
    chk("validator: 缺 Entrance 被拦",
        v["status"] == "FAIL" and any(i["code"] == "MISSING_ENTRANCE"
                                      for i in v["errors"]))


def t_continuity_runtime():
    from scene.scene_graph import SceneGraph
    from scene import continuity as CT, visual_runtime as VR
    prev = SceneGraph("s1")
    prev.add("s1", "person", w=40, h=40, weight="primary")
    nxt = SceneGraph("s2")
    res = CT.carry(prev, nxt, ["person"])
    chk("continuity: 沿用实体（不重建）",
        res["carried"] == ["person"] and nxt.has("person"))
    res2 = CT.carry(prev, nxt, ["person"])
    chk("continuity: 已存在则复用", "person" in res2["reused"])
    spec = VR.to_spec(prev)
    chk("runtime: 场景→SVG spec 非空",
        len(spec["elements"]) >= 1 and "<" in spec["elements"][0]["svg"])


def main():
    print("== SCENE-TEST (Phase 2 场景编译层) ==")
    for fn in (t_scene_graph, t_relation, t_solver, t_motion, t_state_transition,
               t_timeline, t_entrance, t_weight_composition,
               t_render_plan_and_validator, t_continuity_runtime):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            _F.append(fn.__name__ + ":EXC")
            print("  FAIL  %s raised %r" % (fn.__name__, e))
    print("\n== SUMMARY: %d passed, %d failed ==" % (len(_P), len(_F)))
    if _F:
        print("FAILED:", ", ".join(_F))
        return 1
    print("SCENE-TEST VERIFIED \u2714")
    return 0


if __name__ == "__main__":
    sys.exit(main())
