"""director_loop.py — 生成 → 截图 → Critic → 修复 的闭环。

    Agent(intent) → Compiler → RenderPlan/DSL → HTML/SVG → screenshot → PNG
        → Critic 判决 → PASS → 下一个 Beat
                      → FAIL → route() 找上游层 → 修复 intent/layout → 重新编译 → 重新截图

这正是解决「Agent 概念会、代码落不成」的那一环：每生成一个 Beat 就自动截图、
交给 Critic，PASS 才前进，FAIL 就带着修复目标层回到上游。
"""
import os

from common import ensure_dir
import compiler.composition as COMP
import compiler.constraints as CONS
import compiler.svg_compiler as SVGC
from render import screenshot as SHOT
from director import critic as CRITIC


def _auto_fix(intent, route_info, attempt):
    """按修复路由做一次上游修复（当前实现：调密度 / 去留白）。

    真实项目里这里是 Agent 用 Visual Intent 重新决策；此处给可复现的确定性修复：
      layout 问题 → 不动语义（由约束保证）
      intent 问题 → 若过密降密度，若空帧升密度/去 silence
    """
    fixed = dict(intent)
    if route_info.get("target_layer") == "intent":
        d = fixed.get("density", 0.5)
        if "CRITIC_OVERCROWDED" in route_info.get("issue_codes", []):
            fixed["density"] = round(max(0.2, d - 0.15 * attempt), 2)
        if "CRITIC_BLANK_FRAME" in route_info.get("issue_codes", []):
            fixed["density"] = round(min(0.9, d + 0.15 * attempt), 2)
            fixed["silence"] = False
    return fixed


def run_beat(intent, workdir, max_repair=2, prefer_backend=None, shot_scale=2):
    """跑一个 Beat 的闭环。返回完整轨迹（含每轮判决与修复）。"""
    workdir = ensure_dir(workdir)
    trace = []
    cur = intent
    for attempt in range(max_repair + 1):
        # 1) 编译
        spec, meta = COMP.compile_intent(cur)
        # 2) 编译期约束
        con = CONS.check(spec, cur)
        # 3) 渲染 → 截图
        png = os.path.join(workdir, "beat-%s-r%d.png" % (cur.get("beat_id", "b"), attempt))
        backend = None
        if con["status"] == "PASS":
            try:
                _, backend = SHOT.screenshot_spec(spec, png, scale=shot_scale, prefer=prefer_backend)
            except Exception as e:
                trace.append({"round": attempt, "stage": "render", "error": str(e)})
                break
        # 4) Critic（截图 + 结构）
        review = CRITIC.criticize(spec, png if backend else None, cur)
        rt = CRITIC.route(review["issues"])
        trace.append({"round": attempt, "stage": "review", "realization": meta.get("realization"),
                      "constraints": con["status"], "verdict": review["verdict"],
                      "issues": review["issues"], "raster": review["raster"],
                      "backend": backend, "route": rt})
        if con["status"] == "PASS" and review["verdict"] == "PASS":
            return {"beat_id": cur.get("beat_id"), "verdict": "PASS", "attempts": attempt + 1,
                    "png": png, "backend": backend, "trace": trace}
        # 5) 修复 → 回上游
        if attempt < max_repair:
            if con["status"] != "PASS":
                cur = _auto_fix(cur, {"target_layer": "layout",
                                      "issue_codes": [i["code"] for i in con["issues"]]}, attempt + 1)
            else:
                cur = _auto_fix(cur, rt, attempt + 1)
    return {"beat_id": intent.get("beat_id"), "verdict": "FAIL", "attempts": len(trace),
            "png": None, "backend": None, "trace": trace}


def run_intents(intents, workdir, **kw):
    """跑多个 Beat 的闭环，返回汇总。"""
    results = [run_beat(i, workdir, **kw) for i in intents]
    return {"passed": sum(1 for r in results if r["verdict"] == "PASS"),
            "total": len(results), "results": results}
