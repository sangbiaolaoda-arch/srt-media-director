"""relation_library.py — 50 GSAP inter-element dynamic-relationship specs.

Additive capability library. This captures *how two or more elements on the
stage move with respect to each other* — the "interaction density" the
methodology doc argues matters more than raw motion density. It is distinct
from ``runtime/motion_runtime/relations.py`` (which plans logical relations);
this catalog is a **browser-ready motion vocabulary** for the front-end.

Each spec::

    {"id", "name", "from_role", "to_role", "type",
     "semantic",     # what relationship this motion realises
     "steps": [ ... ]  # ordered gsap operations, source -> target
    }

A "step" is ``{"op": <op>, "target": "source|target|link|group", ...params}``
where ``op`` ∈ {tween, follow, chain, delay, sync}. The emitter turns each
step into a real GSAP call. No renderer dependency; deterministic.
"""
from __future__ import annotations

from typing import Dict, List

_RELATIONS: List[Dict] = []


def _r(rid, name, fro, to, rtype, semantic, steps):
    _RELATIONS.append({
        "id": rid, "name": name, "from_role": fro, "to_role": to,
        "type": rtype, "semantic": semantic, "steps": steps,
    })


def _s(op, target, **kw):
    d = {"op": op, "target": target}
    d.update(kw)
    return d


def _build() -> None:
    # --- following / leading -------------------------------------------------
    _r("r01", "跟随", "leader", "follower", "follow", "目标跟随源的位移",
       [_s("follow", "target", source="source", axis="xy")])
    _r("r02", "弹性跟随", "leader", "follower", "elastic_follow", "带阻尼的延迟跟随，表达从属",
       [_s("follow", "target", source="source", axis="xy", ease="power2.out", lag=0.12)])
    _r("r03", "尾随", "leader", "follower", "trailing", "明显滞后跟随，表达队列",
       [_s("follow", "target", source="source", axis="xy", delay=0.25)])
    _r("r04", "主从联动", "leader", "follower", "leader_led", "从属完全继承源的变换",
       [_s("sync", "target", source="source", props=["x", "y", "rotation", "scale"])])
    _r("r05", "多米诺", "leader", "follower", "domino", "依次倒下/触发，表达连锁",
       [_s("chain", "group", gap=0.08, from_first=True)])
    _r("r06", "链式传递", "leader", "follower", "cascade", "信号沿链逐级传递",
       [_s("chain", "group", gap=0.10, from_first=True, ease="power2.out")])
    # --- push / pull / attract ----------------------------------------------
    _r("r07", "推开", "source", "target", "push_out", "源变大把目标挤开",
       [_s("tween", "source", props={"scale": 1.15}, dur=0.5),
        _s("tween", "target", props={"x": "+=(w*0.12)"}, dur=0.5, ease="power2.out")])
    _r("r08", "吸引", "source", "target", "pull_in", "源把目标吸近",
       [_s("tween", "target", props={"x": "-=(d*0.4)"}, dur=0.6, ease="power3.out")])
    _r("r09", "磁吸贴附", "source", "target", "magnet_attach", "目标被吸附到源锚点",
       [_s("tween", "target", props={"x": "=snapX(source)", "y": "=snapY(source)"},
            dur=0.45, ease="back.out(1.6)")])
    _r("r10", "停靠", "source", "target", "dock", "目标滑入源的停靠位",
       [_s("tween", "target", props={"x": "=dockX(source)", "y": "=dockY(source)"}, dur=0.5)])
    _r("r11", "改挂父级", "source", "target", "reparent", "目标继承源坐标系后随源移动",
       [_s("sync", "target", source="source", props=["x", "y"])])
    _r("r12", "环绕", "source", "target", "orbit", "目标绕源做圆周运动",
       [_s("tween", "target", props={"rotation": 360}, dur=4.0, ease="none", pivot="source")])
    _r("r13", "卫星环绕", "source", "target", "satellite", "多个目标沿轨道环绕源",
       [_s("chain", "group", gap=0.3), _s("tween", "group",
            props={"rotation": 360}, dur=6.0, ease="none", pivot="source")])
    # --- mirrors / counters --------------------------------------------------
    _r("r14", "镜像", "source", "target", "mirror", "目标与源反向同步",
       [_s("tween", "target", props={"x": "=-source.x", "y": "=source.y"}, dur=0.5)])
    _r("r15", "反向移动", "source", "target", "counter", "目标与源相向/背向运动",
       [_s("tween", "target", props={"x": "=-delta.x"}, dur=0.5, ease="power2.inOut")])
    _r("r16", "继承变换", "source", "target", "inherit_transform", "目标复用源的最终变换",
       [_s("sync", "target", source="source", props=["x", "y", "scale", "rotation"])])
    _r("r17", "交接", "source", "target", "handoff", "主体权从源移交目标，源淡出",
       [_s("tween", "target", props={"opacity": 1, "scale": 1}, dur=0.5),
        _s("tween", "source", props={"opacity": 0}, dur=0.5, delay=0.2)])
    _r("r18", "交叉淡变", "source", "target", "crossfade_link", "两元素交叉淡入淡出",
       [_s("tween", "source", props={"opacity": 0}, dur=0.5),
        _s("tween", "target", props={"opacity": 1}, dur=0.5)])
    _r("r19", "共享形变", "source", "target", "morph_share", "两元素共享同一形变路径",
       [_s("tween", "group", props={"scale": 1.1}, dur=0.5),
        _s("tween", "source", props={"borderRadius": "50%"}, dur=0.5),
        _s("tween", "target", props={"borderRadius": "50%"}, dur=0.5)])
    _r("r20", "速度匹配切", "source", "target", "velocity_match", "切点时两元素速度一致",
       [_s("tween", "group", props={"x": "+=120"}, dur=0.4, ease="power2.in")])
    _r("r21", "甩镜", "source", "target", "whip_pan", "快速横移带出目标",
       [_s("tween", "group", props={"x": "-=(w*0.5)"}, dur=0.25, ease="power4.in")])
    # --- depth / camera ------------------------------------------------------
    _r("r22", "视差分层", "source", "target", "parallax", "前后景以不同速率移动",
       [_s("tween", "source", props={"x": "+=40"}, dur=1.0),
        _s("tween", "target", props={"x": "+=14"}, dur=1.0)])
    _r("r23", "钉住", "source", "target", "pin_lock", "目标在滚动中钉住不动",
       [_s("tween", "target", props={"positionSticky": True}, dur=0.0)])
    _r("r24", "吸附对齐", "source", "target", "snap_align", "目标吸附到对齐网格",
       [_s("tween", "target", props={"x": "=gridX()", "y": "=gridY()"}, dur=0.4, ease="back.out(1.4)")])
    _r("r25", "组内换位", "source", "target", "group_swap", "两元素交换位置",
       [_s("tween", "source", props={"x": "=targetX()", "y": "=targetY()"}, dur=0.6),
        _s("tween", "target", props={"x": "=sourceX()", "y": "=sourceY()"}, dur=0.6)])
    _r("r26", "错位跟随", "leader", "follower", "stagger_follow", "多目标错时跟随源",
       [_s("follow", "group", source="source", axis="x", stagger=0.08)])
    # --- connectors ----------------------------------------------------------
    _r("r27", "画线连接", "source", "target", "draw_connect", "在两者之间画出连线",
       [_s("tween", "link", props={"drawSVG": "0%->100%"}, dur=0.6)])
    _r("r28", "描迹关系", "source", "target", "trace", "沿关系路径描出",
       [_s("tween", "link", props={"strokeDashoffset": 0}, dur=0.7)])
    _r("r29", "光束发射", "source", "target", "beam", "源向目标发射光束",
       [_s("tween", "link", props={"opacity": 1, "scaleX": 1}, dur=0.3),
        _s("tween", "target", props={"filter": "brightness(1.4)"}, dur=0.3, delay=0.25)])
    _r("r30", "脉冲同步", "source", "target", "pulse_sync", "两元素同频脉冲",
       [_s("sync", "group", source="source", props=["scale"], repeat=3)])
    _r("r31", "呼吸同步", "source", "target", "breath_sync", "同拍呼吸（克制使用）",
       [_s("sync", "group", source="source", props=["opacity"], repeat=2)])
    # --- physics -------------------------------------------------------------
    _r("r32", "重力坠落", "source", "target", "gravity_drop", "目标受重力落下",
       [_s("tween", "target", props={"y": "+=160"}, dur=0.6, ease="bounce.out")])
    _r("r33", "弹簧回位", "source", "target", "spring_return", "目标弹回原位",
       [_s("tween", "target", props={"x": "=origin.x"}, dur=0.7, ease="elastic.out(1,0.4)")])
    _r("r34", "钟摆", "source", "target", "pendulum", "目标绕源做钟摆运动",
       [_s("tween", "target", props={"rotation": 24}, dur=1.0, ease="sine.inOut",
            repeat=1, yoyo=True, pivot="source")])
    _r("r35", "旋转缠绕", "source", "target", "swirl", "目标螺旋卷入源",
       [_s("tween", "target", props={"x": "=source.x", "y": "=source.y",
            "rotation": 540, "scale": 0.2}, dur=1.0, ease="power2.in")])
    _r("r36", "涡流", "source", "target", "vortex", "多目标卷入源形成涡流",
       [_s("chain", "group", gap=0.06), _s("tween", "group",
            props={"x": "=source.x", "y": "=source.y", "scale": 0.3},
            dur=1.0, ease="power3.in")])
    _r("r37", "螺旋进入", "source", "target", "spiral_in", "目标螺旋靠近源",
       [_s("tween", "target", props={"x": "=source.x", "y": "=source.y",
            "rotation": 360}, dur=1.1, ease="power2.inOut")])
    _r("r38", "排斥", "source", "target", "repel", "源把目标推开",
       [_s("tween", "target", props={"x": "+=90", "y": "-=40"}, dur=0.5,
            ease="power2.out")])
    _r("r39", "场吸引", "source", "target", "attract_field", "源形成力场吸引目标",
       [_s("tween", "group", props={"x": "=source.x", "y": "=source.y"}, dur=0.8,
            ease="power3.out", stagger=0.05)])
    _r("r40", "涟漪外扩", "source", "target", "ripple_out", "源触发涟漪推动目标",
       [_s("tween", "link", props={"scale": 2.2, "opacity": 0}, dur=0.8),
        _s("tween", "target", props={"scale": 1.05}, dur=0.8, delay=0.15)])
    _r("r41", "连锁锁定", "source", "target", "domino_lock", "前一个停稳后触发下一个",
       [_s("chain", "group", gap=0.12, ease="back.out(1.5)")])
    _r("r42", "回声", "source", "target", "echo", "目标延迟复制源的动作",
       [_s("follow", "target", source="source", axis="xy", delay=0.4, fade=True)])
    _r("r43", "拖影", "source", "target", "clone_trail", "目标成为源的拖影",
       [_s("sync", "target", source="source", props=["x", "y"], delay=0.15),
        _s("tween", "target", props={"opacity": 0.3}, dur=0.3)])
    _r("r44", "投射阴影", "source", "target", "shadow_cast", "目标随源变化投射阴影",
       [_s("sync", "target", source="source", props=["x"], delay=0.0),
        _s("tween", "target", props={"scaleY": 0.4, "opacity": 0.25}, dur=0.5)])
    _r("r45", "均分空间", "source", "target", "distribute", "多元素均分可用空间",
       [_s("chain", "group", gap=0.0), _s("tween", "group",
            props={"x": "=evenlySpaced()"}, dur=0.6, ease="power2.inOut")])
    _r("r46", "网格重排", "source", "target", "reflow", "元素随布局变化重排（Flip 思想）",
       [_s("tween", "group", props={"x": "=flipX()", "y": "=flipY()"}, dur=0.6,
            ease="power3.inOut")])
    _r("r47", "背后揭示", "source", "target", "reveal_behind", "源让开后露出目标",
       [_s("tween", "source", props={"opacity": 0.2, "scale": 1.1}, dur=0.5),
        _s("tween", "target", props={"opacity": 1, "scale": 1}, dur=0.5)])
    _r("r48", "遮挡", "source", "target", "occlude", "源移动遮挡目标",
       [_s("tween", "source", props={"x": "=target.x"}, dur=0.5, ease="power2.inOut")])
    _r("r49", "聚光跟随", "source", "target", "spotlight_follow", "聚光灯跟随源，目标随之显隐",
       [_s("follow", "link", source="source", axis="x"),
        _s("tween", "group", props={"filter": "brightness(1.15)"}, dur=0.4)])
    _r("r50", "镜头跟随", "source", "target", "camera_follow", "镜头跟随源，露出目标",
       [_s("tween", "group", props={"x": "=-source.x"}, dur=0.9, ease="power2.inOut")])


_build()
_BY_ID = {r["id"]: r for r in _RELATIONS}


def all_relations() -> List[Dict]:
    return list(_RELATIONS)


def by_type(rtype: str) -> List[Dict]:
    return [r for r in _RELATIONS if r["type"] == rtype]


def ids() -> List[str]:
    return [r["id"] for r in _RELATIONS]


def get(rid: str) -> Dict:
    return _BY_ID[rid]


def counts() -> Dict[str, int]:
    return {"total": len(_RELATIONS)}


def validate(spec: Dict) -> List[str]:
    errs: List[str] = []
    for key in ("id", "name", "from_role", "to_role", "type", "semantic", "steps"):
        if key not in spec:
            errs.append(f"missing {key}")
    if not spec.get("semantic"):
        errs.append("empty semantic")
    steps = spec.get("steps")
    if not isinstance(steps, list) or not steps:
        errs.append("steps must be a non-empty list")
    else:
        for st in steps:
            if st.get("op") not in ("tween", "follow", "chain", "delay", "sync"):
                errs.append(f"bad op: {st.get('op')}")
            if not st.get("target"):
                errs.append("step missing target")
    return errs
