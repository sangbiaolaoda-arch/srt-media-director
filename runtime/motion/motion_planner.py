"""motion_planner.py — Motion Compiler 的核心。

输入：Composition + DSL（含 Visual Claim / Grammar / Focal / Relationship / 角色）
输出：带完整 motion_policy 的 RenderPlan（每个可见元素都有明确的运动决策）

原则：
  · Agent 决定视觉意图；Runtime 决定动画实现（type/duration/delay/easing）。
  · motion_policy 缺失 ≠ static：缺失时由本模块推断补全（source=inferred）。
  · 允许并鼓励静态（背景/装饰默认 static）。
  · 动画必须能解释语义作用（reason 字段），否则降级。
"""
from .sequencing import build_sequence
from .entrance import timing as entrance_timing
from .transition import camera_for, beat_transition
from .continuity import link_beats
from .state_change import detect_state_change, state_motion
from .semantics import (ROLE_PREFERENCE, ROLE_WEIGHT, NO_MOTION_ROLES,
                        GRAMMAR_RELATION_MOTION, normalize_role)
from .motion_registry import (MOTION_PRIMITIVES, VALID_MOTIONS, is_valid_motion,
                              supports, primitive)

MOTION_POLICY_SCHEMA = {
    "type": "Motion Registry 中的合法原语（含 static）",
    "source": "explicit | intent | inferred | continuity",
    "role": "语义角色",
    "duration": "秒，由重要性/时长/密度推导",
    "delay": "秒，由序列 rank 推导",
    "easing": "来自 Registry",
    "reason": "语义解释：为什么这样出现",
}

# Agent 可选的 motion_intent → 具体原语（Agent 只表意，Runtime 定实现）
INTENT_MAP = {
    "emerge": "emerge", "reveal": "reveal", "reappear": "fade",
    "focus": "emerge", "contrast_then_focus": "emerge",
    "accumulate_then_reveal": "reveal", "morph": "transform",
    "establish": "fade", "slide": "slide", "draw": "draw", "grow": "grow",
    "static": "static", "pop": "scale", "rise": "slide", "fade": "fade",
}

DEFAULT_BUDGET = {"max_primary_motion": 1, "max_secondary_motion": 3,
                  "allow_background_motion": False}

_PRIMARY = ("emerge", "scale", "reveal", "expand", "converge", "diverge", "grow", "rotate")


def _is_connector(el):
    return el.get("type") in ("connector", "path", "line") or el.get("semantic_role") == "relationship"


def intent_to_motion(intent):
    if not intent:
        return None
    return INTENT_MAP.get(str(intent).strip().lower())


class MotionPlanner:
    def __init__(self, budget=None):
        self.budget = dict(DEFAULT_BUDGET)
        if budget:
            self.budget.update(budget)
        self._used = {}            # 全局原语使用计数（用于反同质化）

    # ------------------------------------------------------------ 单个元素的运动决策
    def _decide(self, el, grammar, beat_used, focal_id):
        """返回 motion_policy 字典。核心：缺失→推断；显式→尊重。"""
        role = normalize_role(el.get("semantic_role") or el.get("role"))
        etype = el.get("type")
        mp = el.get("motion_policy") or {}
        explicit_type = mp.get("type")

        # 1) 显式且合法 → 尊重（含显式 static）
        if explicit_type and is_valid_motion(explicit_type):
            return {"type": explicit_type, "source": "explicit", "role": role,
                    "duration": mp.get("duration", 0.0),
                    "delay": mp.get("delay", 0.0),
                    "easing": mp.get("easing", primitive(explicit_type)["easing"]),
                    "reason": mp.get("reason") or primitive(explicit_type)["semantic"],
                    "explicit": True}

        # 2) 背景/装饰 → 明确 static（反 PPT：不为了「有动画」而运动）
        if role in NO_MOTION_ROLES and not self.budget["allow_background_motion"]:
            return {"type": "static", "source": "inferred", "role": role,
                    "duration": 0.0, "delay": 0.0, "easing": "linear",
                    "reason": "背景/装饰保持静止（运动是节奏的一部分）"}

        # 3) 元素被显式标 static
        if el.get("static") is True:
            return {"type": "static", "source": "explicit", "role": role,
                    "duration": 0.0, "delay": 0.0, "easing": "linear",
                    "reason": "显式声明静止"}

        # 4) 关系类元素 → 按语法决定连接如何建立
        if _is_connector(el):
            m = GRAMMAR_RELATION_MOTION.get(grammar[0], "draw")
            if not supports(m, etype):
                m = "fade"
            return {"type": m, "source": "inferred", "role": role or "relationship",
                    "duration": 0.6, "delay": 0.0, "easing": primitive(m)["easing"],
                    "reason": "关系建立（%s）" % grammar[0]}

        # 5) Agent 只给了 motion_intent → 转具体原语
        m = intent_to_motion(el.get("motion_intent"))
        if m:
            return {"type": m, "source": "intent", "role": role,
                    "duration": 0.0, "delay": 0.0, "easing": primitive(m)["easing"],
                    "reason": "按 motion_intent=%s 映射" % el.get("motion_intent")}

        # 6) 推断：角色候选里挑本拍最少用的（反同质化）
        from .semantics import candidates_for
        cands = [c for c in candidates_for(role, etype) if supports(c, etype)] or ["fade"]
        cands = sorted(cands, key=lambda c: (beat_used.get(c, 0) + self._used.get(c, 0), cands.index(c)))
        picked = cands[0]
        return {"type": picked, "source": "inferred", "role": role,
                "duration": 0.0, "delay": 0.0, "easing": primitive(picked)["easing"],
                "reason": "按角色=[%s] 推断（候选 %s）" % (role, cands[:3])}

    # ------------------------------------------------------------ 整片编译
    def compile_plan(self, dsl, composition=None, continuity=True):
        beats = dsl.get("beats", [])
        boxes_by_beat = {}
        if composition:
            for cb in composition.get("beats", []):
                boxes_by_beat[cb.get("beat_id")] = cb.get("boxes", {})

        plans = []
        for beat in beats:
            bid = beat["beat_id"]
            dur = beat.get("end_sec", 0) - beat.get("start_sec", 0)
            grammar = beat.get("grammar") or beat.get("grammar_ops") or ["establish"]
            focal_id = beat.get("focal_point")
            elements = beat.get("elements", [])
            boxes = boxes_by_beat.get(bid, {})
            if not boxes:
                boxes = {e["id"]: e.get("box") for e in elements if e.get("box")}

            seq = build_sequence(beat, elements, boxes)
            times = entrance_timing(seq, elements, dur)
            beat_used = {}

            out_els = []
            for el in elements:
                pol = self._decide(el, grammar, beat_used, focal_id)
                # 由 Runtime 补全 duration / delay（除非显式静态/延续）
                t = times.get(el["id"], {"at": 0.0, "dur": 0.4, "static": False})
                if pol["type"] not in ("static", "none", "carry_over", "continue", "handoff"):
                    if not pol.get("duration"):
                        pol["duration"] = t["dur"]
                    pol["delay"] = t["at"]
                else:
                    pol["duration"] = 0.0
                    pol["delay"] = 0.0
                beat_used[pol["type"]] = beat_used.get(pol["type"], 0) + 1
                self._used[pol["type"]] = self._used.get(pol["type"], 0) + 1

                box = el.get("box") or boxes.get(el["id"])
                out_els.append({
                    "id": el["id"], "type": el.get("type"),
                    "semantic_role": pol.get("role") or el.get("semantic_role"),
                    "visible": el.get("visible", True),
                    "box": list(box) if box else None,
                    "svg": el.get("svg"),
                    "motion_policy": pol,
                })

            # 叙事序列（scene → sequence → element motion）
            mseq = []
            for e in out_els:
                p = e["motion_policy"]
                mseq.append({"target": e["id"], "motion": p["type"],
                             "start": round(p["delay"], 3),
                             "duration": round(p["duration"], 3),
                             "easing": p["easing"], "reason": p.get("reason")})
            mseq.sort(key=lambda x: (x["start"], x["target"]))

            plans.append({
                "beat_id": bid, "start": beat.get("start_sec"), "end": beat.get("end_sec"),
                "duration": dur, "grammar": grammar, "focal_point": focal_id,
                "palette": beat.get("palette"), "strategy": beat.get("strategy"),
                "elements": out_els, "relations": beat.get("relations", []),
                "motion_sequence": mseq,
                "motion_budget": dict(self.budget),
                "camera": camera_for(beat),
            })

        trans = []
        for i in range(1, len(plans)):
            trans.append(dict(beat_transition(None, None, plans[i - 1], plans[i]),
                              **{"from": plans[i - 1]["beat_id"], "to": plans[i]["beat_id"]}))

        if continuity:
            link_beats(plans)

        return {"beats": plans, "transition": trans,
                "motion": {"sequence": [b for bp in plans for b in bp["motion_sequence"]]}}

    # ------------------------------------------------------------ 自动补全缺失
    def fill_missing(self, plan):
        """Validator 发现缺失后调用：为缺 motion_policy 的可见元素补全。"""
        filled = []
        for bp in plan.get("beats", []):
            grammar = bp.get("grammar") or ["establish"]
            focal_id = bp.get("focal_point")
            beat_used = {}
            for e in bp["elements"]:
                if e.get("motion_policy") and e["motion_policy"].get("type"):
                    continue
                pol = self._decide(e, grammar, beat_used, focal_id)
                t = {"at": 0.0, "dur": 0.4}
                pol["duration"] = pol.get("duration") or t["dur"]
                pol["delay"] = t["at"]
                e["motion_policy"] = pol
                filled.append((bp["beat_id"], e["id"]))
        return filled


def compile_plan(dsl, composition=None, budget=None, continuity=True):
    return MotionPlanner(budget=budget).compile_plan(dsl, composition, continuity)
