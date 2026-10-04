"""validator.py — Motion Validator + Coverage + 反 PPT 检查（架构最关键一层）。

在 RenderPlan 进入 Renderer 之前执行：
    motion_policy != null 且 type 合法 → 通过
    缺失 → 自动补全 → 复检 → 通过；补全仍失败 → FAIL（绝不静默渲染成静态）
并检查动画「是否过度」（反 PPT）：同质化 / 同时运动过多 / 装饰性运动 / 密度过高等。
"""
from .motion_registry import VALID_MOTIONS, STATIC_LIKE, is_valid_motion
from .motion_planner import MotionPlanner

MOVING = tuple(m for m in VALID_MOTIONS if m not in STATIC_LIKE)


def _visible(els):
    return [e for e in els if e.get("visible", True)]


def coverage(plan):
    total = missing = static_explicit = moving = 0
    for bp in plan.get("beats", []):
        for e in _visible(bp.get("elements", [])):
            total += 1
            mp = e.get("motion_policy")
            if not mp or not mp.get("type"):
                missing += 1
            elif not is_valid_motion(mp["type"]):
                missing += 1
            elif mp["type"] in STATIC_LIKE:
                static_explicit += 1
            else:
                moving += 1
    cov = 1.0 if total == 0 else (total - missing) / total
    return {"motion_coverage": round(cov, 4), "motion_missing": missing,
            "static_explicit": static_explicit, "moving": moving, "visible": total}


class AntiPPTChecker:
    """反 PPT：不是「有动画就合格」，而是检查运动是否服务语义、是否过度。"""

    def __init__(self, repeat_ratio=0.7, max_concurrent=2, density_cap=4):
        self.repeat_ratio = repeat_ratio
        self.max_concurrent = max_concurrent
        self.density_cap = density_cap

    def check_beat(self, bp):
        issues = []
        els = _visible(bp.get("elements", []))
        moving = [e for e in els if e.get("motion_policy", {}).get("type") in MOVING]
        types = [e["motion_policy"]["type"] for e in moving]

        # 1) 同质化：绝大多数元素用同一种运动
        if len(types) >= 4:
            from collections import Counter
            top, cnt = Counter(types).most_common(1)[0]
            if cnt / len(types) >= self.repeat_ratio:
                issues.append(self._i(bp, "REPETITIVE_MOTION",
                                      "%d/%d 个运动元素都是 %s" % (cnt, len(types), top)))

        # 2) 同时运动过多：以 200ms 窗口统计并发入场
        windows = {}
        for e in moving:
            p = e["motion_policy"]
            w = round(p.get("delay", 0) / 0.2)
            windows.setdefault(w, []).append(e["id"])
        for w, ids in windows.items():
            if len(ids) > self.max_concurrent:
                issues.append(self._i(bp, "TOO_MANY_SIMULTANEOUS_MOTIONS",
                                      "%.1fs 附近 %d 个元素同时入场: %s" % (w * 0.2, len(ids), ids)))

        # 3) 运动总量过高
        cap = bp.get("motion_budget", {}).get("max_secondary_motion", 3) + \
            bp.get("motion_budget", {}).get("max_primary_motion", 1)
        if len(moving) > cap:
            issues.append(self._i(bp, "EXCESSIVE_MOTION",
                                  "运动元素 %d > 预算 %d" % (len(moving), cap)))

        # 4) 装饰性运动：背景/装饰不应动
        for e in els:
            if e.get("semantic_role") in ("background", "decoration"):
                if e.get("motion_policy", {}).get("type") in MOVING:
                    issues.append(self._i(bp, "DECORATIVE_MOTION",
                                          "背景/装饰元素 %s 发生了运动" % e["id"]))

        # 5) 焦点冲突：焦点元素应为 0 或 1 个
        focals = [e for e in els if e.get("semantic_role") == "focal"]
        if len(focals) > 1:
            issues.append(self._i(bp, "FOCAL_MOTION_CONFLICT",
                                  "焦点元素 %d 个（应唯一）" % len(focals)))

        # 6) 运动密度
        dur = bp.get("duration") or 1.0
        if len(moving) / max(dur, 0.1) > self.density_cap:
            issues.append(self._i(bp, "MOTION_DENSITY_TOO_HIGH",
                                  "运动密度 %.2f/s 过高" % (len(moving) / max(dur, 0.1))))

        # 7) 无语义用途：运动却没有 reason
        for e in moving:
            if not (e.get("motion_policy", {}).get("reason") or "").strip():
                issues.append(self._i(bp, "MOTION_WITHOUT_SEMANTIC_PURPOSE",
                                      "%s 的运动缺少语义解释" % e["id"]))
        return issues

    @staticmethod
    def _i(bp, code, msg):
        return {"severity": "warn", "layer": "motion", "code": code,
                "beat_id": bp.get("beat_id"), "msg": msg}


def validate_motion(plan, autocomp=True, budget=None, checker=None):
    """主入口。返回 {status, coverage..., issues, autocompleted}。"""
    checker = checker or AntiPPTChecker()
    issues = []
    autocompleted = []

    # 1) 先看缺失
    cov = coverage(plan)
    if cov["motion_missing"] > 0:
        if not autocomp:
            issues.append({"severity": "err", "layer": "motion",
                           "code": "MOTION_POLICY_MISSING",
                           "msg": "%d 个可见元素缺少 Motion Policy" % cov["motion_missing"]})
        else:
            planner = MotionPlanner(budget=budget)
            filled = planner.fill_missing(plan)
            autocompleted = [{"beat_id": b, "element": e} for b, e in filled]
            cov = coverage(plan)
            if cov["motion_missing"] > 0:
                issues.append({"severity": "err", "layer": "motion",
                               "code": "MOTION_POLICY_MISSING",
                               "msg": "自动补全后仍有 %d 个缺失" % cov["motion_missing"]})

    # 2) 非法类型
    for bp in plan.get("beats", []):
        for e in _visible(bp.get("elements", [])):
            mp = e.get("motion_policy") or {}
            if mp.get("type") and not is_valid_motion(mp["type"]):
                issues.append({"severity": "err", "layer": "motion",
                               "code": "MOTION_TYPE_UNKNOWN",
                               "beat_id": bp.get("beat_id"),
                               "msg": "%s 的类型 %r 不在 Registry" % (e["id"], mp["type"])})

    # 3) 反 PPT
    for bp in plan.get("beats", []):
        issues += checker.check_beat(bp)

    errs = [i for i in issues if i["severity"] == "err"]
    warns = [i for i in issues if i["severity"] == "warn"]
    status = "FAIL" if errs else "PASS"
    result = {"status": status, "motion_coverage": cov["motion_coverage"],
              "motion_missing": cov["motion_missing"],
              "static_explicit": cov["static_explicit"],
              "moving": cov["moving"], "visible": cov["visible"],
              "errors": errs, "warnings": warns, "issues": issues,
              "autocompleted": autocompleted}
    plan["validation"] = result
    return result
