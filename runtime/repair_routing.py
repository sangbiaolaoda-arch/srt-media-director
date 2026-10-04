"""Stage 6 — 故障 → 修复层路由 + 单变量重拍预算（v6.0）。

借鉴 Seedance 的「诊断树 + 单变量重拍」：
症状 → 归属层 → 修复动作。每次返工只改**一个**变量；每拍尝试预算默认 3，
超过就阻断并报告，绝不无限循环。
"""

RETRY_BUDGET = 3

# 症状 → (归属层, 修复动作)
ROUTING = [
    ("遮住字幕看不懂这拍", "visual_claim", "重写命题，不动布局"),
    ("元素重叠", "layout", "换模板或调参数"),
    ("越界", "layout", "换模板或调参数"),
    ("本该同时出现的元素错开", "entrance", "调波次，不动布局"),
    ("转场突兀", "transition", "补 carried 或改 cut 理由"),
    ("元素跳变", "transition", "补 carried 或改 cut 理由"),
    ("风格漂移", "token", "修 token 或注入逻辑"),
    ("hold 过短", "contract", "延长该拍或缩短文案"),
    ("断句生硬", "semantic", "调语义分组约束"),
]

# 检查代码 → 归属层
CODE_LAYER = {
    "HOLD_TOO_SHORT": "contract",
    "PATH_TOO_LONG": "contract",
    "PRIMARY_NOT_IN_PATH": "contract",
    "AMBIENT_ON_PRIMARY": "contract",
    "AMBIENT_OVER_AMP": "contract",
    "CARRY_NOT_IN_PREV": "transition",
    "CARRY_POS_DRIFT": "transition",
    "EMPTY_DISSOLVE": "transition",
    "CUT_NO_DIFF": "transition",
    "TRANSITION_TYPE": "transition",
    "TRANSITION_NO_REASON": "transition",
    "CLICHE_CLAIM": "visual_claim",
    "STYLE_COLOR": "token",
    "STYLE_FONT": "token",
    "STYLE_STROKE": "token",
    "REP_TEMPLATE_ENTROPY": "layout",
    "OVERLAP": "layout",
    "OUT_OF_BOUNDS": "layout",
}


class RepairBudget:
    """每拍修复尝试计数；超过预算即阻断。"""

    def __init__(self, budget=RETRY_BUDGET):
        self.budget = budget
        self.tries = {}

    def attempt(self, beat_id):
        n = self.tries.get(beat_id, 0) + 1
        self.tries[beat_id] = n
        return n <= self.budget

    def exhausted(self):
        return {b: n for b, n in self.tries.items() if n > self.budget}

    def report(self):
        return {"budget": self.budget, "tries": dict(self.tries),
                "exhausted": self.exhausted()}


def route(issue):
    """把一个 issue 映射到修复层与动作。"""
    code = issue.get("code", "")
    layer = CODE_LAYER.get(code)
    if layer:
        for symptom, lay, act in ROUTING:
            if lay == layer:
                return {"code": code, "layer": layer, "action": act}
        return {"code": code, "layer": layer, "action": "按层修复"}
    msg = issue.get("msg", "")
    for symptom, lay, act in ROUTING:
        if symptom in msg:
            return {"code": code, "layer": lay, "action": act}
    return {"code": code, "layer": "unknown", "action": "人工定位"}


def route_all(issues):
    return [route(i) for i in issues]


def table_md():
    md = ["# 故障 → 修复层路由表", "",
          "| 症状 | 归属层 | 修复动作 |", "|---|---|---|"]
    for s, l, a in ROUTING:
        md.append("| %s | %s | %s |" % (s, l, a))
    md += ["", "规则：每次返工只改一个变量；每拍尝试预算 %d 次，超过即阻断。" % RETRY_BUDGET]
    return "\n".join(md) + "\n"
