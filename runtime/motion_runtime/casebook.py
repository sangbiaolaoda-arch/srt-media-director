"""runtime/motion_runtime/casebook.py — Motion Casebook（Runtime Hardening · P1）。

把 Casebook 升级成真正的 Runtime Test Suite。每个 Case 产出：

    case.json       案例定义（scene + motions + relations + camera + timeline）
    expected.json   期望（不变量 + 关键帧断言）
    scene.html      可独立打开的浏览器验证页（含关键帧数据供 Playwright 检查）
    motion-map.json 语义运动 → 通道 的映射
    metrics.json    关键帧指标（position/scale/rotation/opacity/state/connector/
                    identity/relationship）
    bad/            失败版本存档（Regression 资料）

时间由事件/因果驱动：Case 10/12/14 使用事件图驱动注意力与相机。
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple

from .camera import Camera
from .connector import ConnectorRuntime
from .contracts import MotionPrimitive, PRIMITIVES, make
from .events import Event, EventGraph
from .relations import Relation
from .runtime import MotionRuntime
from .scene import SceneGraph

CASE_NAMES = [
    "01_hierarchy", "02_connect", "03_point_target", "04_surround", "05_follow",
    "06_state_trigger", "07_relation_conflict", "08_constraint_reflow",
    "09_chart_cascade", "10_camera_follow", "11_shared_identity",
    "12_cause_effect", "13_choice_to_cage", "14_relationship_orchestra",
]


# ---------------------------------------------------------------- 案例构造
def _base_scene() -> SceneGraph:
    g = SceneGraph()
    g.add("group", parent="root", x=120, y=120)
    g.add("person", parent="group", x=0, y=0, w=120, h=200)
    g.add("choice_a", parent="root", x=620, y=180, w=140, h=56)
    g.add("choice_b", parent="root", x=620, y=300, w=140, h=56)
    g.add("choice_c", parent="root", x=620, y=420, w=140, h=56)
    g.add("chart", parent="root", x=820, y=200, w=200, h=160)
    g.add("cage", parent="root", x=980, y=300, w=260, h=260)
    return g


def build_case(name: str) -> Tuple[MotionRuntime, dict]:
    g = _base_scene()
    rt = MotionRuntime(g)
    exp: dict = {"invariants": ["Identity", "Parent", "Motion", "Relation", "State"],
                 "keyframe_asserts": []}

    if name == "01_hierarchy":
        rt.add(make("MOVE", "group", duration=1.0, trigger="t0",
                    params={"offset": (200, 60)}))

    elif name == "02_connect":
        rt.connectors.bind("c_person_choice", "person", "choice_a")
        rt.add(make("CONNECT", "choice_a", target="person", duration=1.0,
                    trigger="link", params={}))
        exp["keyframe_asserts"].append({"at": 1.0, "node": "choice_a",
                                        "channel": "connect", "min": 1.0})

    elif name == "03_point_target":
        rt.add(make("DRAW", "choice_b", target="chart", duration=1.0, trigger="point"),
               make("FOLLOW", "chart", target="choice_b", duration=1.0, trigger="point"))
        # DRAW 在 source=choice_b 上产出 connect/opacity；FOLLOW 让 chart 朝 choice_b 靠近
        exp["keyframe_asserts"].append({"at": 1.0, "node": "choice_b", "channel": "connect", "min": 0.99})
        exp["keyframe_asserts"].append({"at": 1.0, "node": "chart", "channel": "dx", "max": -20})

    elif name == "04_surround":
        for i, sid in enumerate(["choice_a", "choice_b", "choice_c"]):
            rt.add(make("SURROUND", sid, target="cage", duration=1.0, trigger="enclose",
                        params={"angle": i * 2.09, "radius_from": 300, "radius_to": 150}))
        exp["keyframe_asserts"].append({"at": 1.0, "node": "choice_a", "channel": "dx", "max": 0})

    elif name == "05_follow":
        rt.add(make("FOLLOW", "chart", target="choice_c", duration=1.0, trigger="t0",
                    params={"lag": 0.2}))
        # chart 在 choice_c 右侧 → 跟随产生向左（负 dx）的位移
        exp["keyframe_asserts"].append({"at": 1.0, "node": "chart", "channel": "dx", "max": -20})

    elif name == "06_state_trigger":
        rt.states.initial("person", "inactive")
        rt.add(make("ACTIVATE", "person", duration=1.0, trigger="activate",
                    params={"to_state": "active"}))
        rt.states.fire("person", "activate")
        exp["keyframe_asserts"].append({"at": 1.0, "node": "person", "channel": "opacity", "min": 0.9})

    elif name == "07_relation_conflict":
        rt.add(make("FOLLOW", "person", target="choice_a", duration=1.0, trigger="t0"),
               make("REPEL", "person", target="choice_a", duration=1.0, trigger="t0",
                    params={"reach": 40}))
        exp["invariants"].append("ConflictDeterministic")

    elif name == "08_constraint_reflow":
        rt.add(make("COMPRESS", "choice_c", target="cage", duration=1.0, trigger="constrain",
                    params={"to_scale": 0.6}),
               make("MOVE", "choice_c", duration=1.0, trigger="constrain",
                    params={"offset": (40, 0)}))
        exp["keyframe_asserts"].append({"at": 1.0, "node": "choice_c", "channel": "scale", "max": 0.7})

    elif name == "09_chart_cascade":
        rt.add(make("EXPAND", "chart", duration=0.6, trigger="data", params={"to_scale": 1.4}),
               make("MOVE", "person", duration=0.6, trigger="data", delay=0.3,
                    params={"offset": (30, 0)}),
               make("MOVE", "choice_a", duration=0.6, trigger="data", delay=0.6,
                    params={"offset": (20, 0)}))
        exp["keyframe_asserts"].append({"at": 1.0, "node": "chart", "channel": "scale", "min": 1.2})

    elif name == "10_camera_follow":
        rt.add(make("MOVE", "choice_b", duration=1.0, trigger="t0",
                    params={"offset": (100, 0)}))
        rt.camera.focus(g, "person")
        rt.camera.attention_transfer(g, "choice_b", weight=1.0)
        exp["camera_asserts"] = [{"focus": "choice_b"}]

    elif name == "11_shared_identity":
        rt.add(make("MOVE", "person", duration=1.0, trigger="t0",
                    params={"offset": (0, 40)}),
               make("SCALE", "person", duration=1.0, trigger="t0",
                    params={"from": 1.0, "to": 1.1}))
        exp["identity_asserts"] = ["person"]

    elif name == "12_cause_effect":
        rt.events.add(Event(id="e_cause", emit_at=0.0, signal="cause_fired"))
        rt.events.add(Event(id="e_effect", emit_at=5.0, signal="effect_done"))
        rt.add_relation(Relation(source="person", target="chart",
                                 relation_type="CAUSE", lifecycle="STRENGTHEN",
                                 trigger="person.activate"))
        rt.add(make("TRANSFER", "person", target="chart", duration=1.0, trigger="person.activate"))
        exp["event_asserts"] = ["e_effect after e_cause"]

    elif name == "13_choice_to_cage":
        rt.add(make("MOVE", "choice_c", target="cage", duration=1.2, trigger="trap",
                    params={"offset": (300, -60)}),
               make("COMPRESS", "choice_c", target="cage", duration=1.2, trigger="trap",
                    params={"to_scale": 0.7}))
        exp["keyframe_asserts"].append({"at": 1.0, "node": "choice_c", "channel": "dx", "min": 0})

    elif name == "14_relationship_orchestra":
        for cid in ("choice_a", "choice_b", "choice_c"):
            rt.add(make("FOLLOW", cid, target="cage", duration=1.2, trigger="converge",
                        params={"lag": 0.25, "strength": 0.8}))
        rt.add_relation(Relation(source="person", target="cage",
                                 relation_type="SURROUND", lifecycle="PROPAGATE",
                                 trigger="person.activate"))
        rt.camera.reframe(g, ["choice_a", "choice_b", "choice_c", "cage"])

    else:
        raise ValueError("unknown case: %s" % name)

    return rt, exp


# ---------------------------------------------------------------- 指标
def _metrics(rt: MotionRuntime, duration: float = 1.2) -> dict:
    frames = rt.sample_frames(duration, keyframes=[0.0, 0.25, 0.5, 0.75, 1.0])
    key = []
    for f in frames:
        snap = {}
        for node, ch in f["transforms"].items():
            snap[node] = {k: round(v, 5) for k, v in ch.items() if k != "state"}
        key.append({"t": f["t"], "nodes": snap, "camera_zoom": f["camera"]["zoom"]})
    conns = {}
    for c in rt.connectors.all():
        conns[c.id] = c.recompute(rt.scene)
    return {
        "frames": key,
        "connector_count": len(rt.connectors.all()),
        "connector_endpoints": {k: {kk: round(vv, 4) for kk, vv in v.items() if kk in ("x1", "y1", "x2", "y2")}
                                for k, v in conns.items()},
        "identity_ids": sorted(rt.identity._ids),
        "relation_count": len(rt.relations.all()),
        "camera": rt.camera.to_dict(),
        "conflicts": rt.sample(duration)["conflicts"],
        "deterministic": True,
    }


def check_case(name: str) -> dict:
    rt, exp = build_case(name)
    duration = max([p.time_range()[1] for p in rt.primitives] or [1.0])
    duration = max(duration, 1.0)
    metrics = _metrics(rt, duration)
    checks = []
    # 不变量
    v = rt.validate(t_end=duration + 0.1)
    checks.append({"check": "invariants", "status": v["status"], "failed": v["failed"]})
    # 确定性
    det = rt.sample(duration) == rt.sample(duration)
    checks.append({"check": "deterministic", "status": "PASS" if det else "FAIL"})
    # 关键帧断言
    final = {n: {k: vv for k, vv in ch.items() if k != "state"}
             for n, ch in rt.sample(duration)["transforms"].items()}
    for a in exp.get("keyframe_asserts", []):
        node = a.get("node")
        ch = a["channel"]
        val = final.get(node, {}).get(ch, 0.0)
        ok = True
        if "min" in a:
            ok = ok and val >= a["min"]
        if "max" in a:
            ok = ok and val <= a["max"]
        checks.append({"check": "kf:%s.%s" % (node, ch), "value": round(val, 5),
                       "status": "PASS" if ok else "FAIL"})
    # 相机断言
    for a in exp.get("camera_asserts", []):
        ok = rt.camera.focus_id == a["focus"] or rt.camera.attention == a["focus"]
        checks.append({"check": "camera:%s" % a["focus"],
                       "status": "PASS" if ok else "FAIL"})
    # 事件因果
    for _ in exp.get("event_asserts", []):
        tl = rt.events.schedule()
        cause_t = next((e["t"] for e in tl if e["event"] == "e_cause"), None)
        effect_t = next((e["t"] for e in tl if e["event"] == "e_effect"), None)
        ok = cause_t is not None and effect_t is not None and effect_t >= cause_t
        checks.append({"check": "event_causality", "status": "PASS" if ok else "FAIL"})
    failed = [c for c in checks if c["status"] == "FAIL"]
    return {"case": name, "status": "PASS" if not failed else "FAIL",
            "checks": checks, "metrics": metrics, "expected": exp}


# ---------------------------------------------------------------- scene.html
def _scene_html(name: str, rt: MotionRuntime, metrics: dict, duration: float) -> str:
    boxes = rt.scene.boxes()
    rects = []
    for nid, (x, y, w, h) in boxes.items():
        if nid == "root":
            continue
        rects.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                     'fill="none" stroke="#7db7ff" stroke-width="1"/>'
                     '<text x="%.1f" y="%.1f" fill="#cfe3ff" font-size="12">%s</text>'
                     % (x, y, w, h, x + 4, y + 14, nid))
    keyframes = json.dumps(metrics["frames"], ensure_ascii=False)
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            "<title>motion-runtime case %s</title>"
            "<style>body{margin:0;background:#0b0f14}#svg{background:#0b0f14}"
            "</style></head><body>"
            "<svg id='svg' xmlns='http://www.w3.org/2000/svg' width='100%%' "
            "height='100%%' viewBox='0 0 1400 720'>%s</svg>"
            "<script type='application/json' id='keyframes'>%s</script>"
            "<script>window.__CASE__=%s;window.__DURATION__=%s;"
            "window.__KEYFRAMES__=%s;</script>"
            "</body></html>"
            % (name, "".join(rects), keyframes,
               json.dumps(name), json.dumps(duration), keyframes))


# ---------------------------------------------------------------- 生成
def generate(outdir: str, duration: float = 1.2) -> dict:
    os.makedirs(outdir, exist_ok=True)
    summary = {"cases": [], "passed": 0, "failed": 0, "names": CASE_NAMES}
    for name in CASE_NAMES:
        rt, exp = build_case(name)
        res = check_case(name)
        cdir = os.path.join(outdir, name)
        os.makedirs(cdir, exist_ok=True)
        case_json = {
            "name": name,
            "scene": {nid: node.to_dict() for nid, node in rt.scene.nodes.items()},
            "motions": [p.to_dict() for p in rt.primitives],
            "relations": [r.to_dict() for r in rt.relations.all()],
            "connectors": [c.to_dict() for c in rt.connectors.all()],
            "camera": rt.camera.to_dict(),
            "events": rt.events.audit(),
            "timeline": rt.timeline(),
        }
        motion_map = {p.motion_type: list(PRIMITIVES[p.motion_type].produces)
                      for p in rt.primitives}
        def _w(fn, obj):
            with open(os.path.join(cdir, fn), "w", encoding="utf-8") as fh:
                json.dump(obj, fh, ensure_ascii=False, indent=2)
        _w("case.json", case_json)
        _w("expected.json", exp)
        _w("motion-map.json", motion_map)
        _w("metrics.json", res["metrics"])
        with open(os.path.join(cdir, "scene.html"), "w", encoding="utf-8") as fh:
            fh.write(_scene_html(name, rt, res["metrics"], duration))
        if res["status"] != "PASS":
            bad = os.path.join(outdir, "bad", name)
            os.makedirs(bad, exist_ok=True)
            with open(os.path.join(bad, "report.json"), "w", encoding="utf-8") as fh:
                json.dump(res, fh, ensure_ascii=False, indent=2)
        summary["cases"].append({"case": name, "status": res["status"],
                                 "failed": [c["check"] for c in res["checks"]
                                            if c["status"] == "FAIL"]})
        summary["passed" if res["status"] == "PASS" else "failed"] += 1
    summary["status"] = "PASS" if summary["failed"] == 0 else "FAIL"
    return summary


def run_all() -> dict:
    out = []
    for name in CASE_NAMES:
        r = check_case(name)
        out.append({"case": name, "status": r["status"],
                    "failed": [c["check"] for c in r["checks"] if c["status"] == "FAIL"]})
    failed = [c for c in out if c["status"] != "PASS"]
    return {"status": "PASS" if not failed else "FAIL", "count": len(out),
            "cases": out, "failed": len(failed)}


if __name__ == "__main__":  # pragma: no cover
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "casebook"
    print(json.dumps(generate(target), ensure_ascii=False, indent=2))
