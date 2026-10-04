"""semantics.py — 语义 → 运动倾向 的知识表。

这里把所有「该动成什么样」的语义知识集中一处，供 Motion Planner 查询。
它是**候选策略**，不是固定映射：Planner 会结合语法/构图/节奏做最终选择。
"""

# 语义角色 → 候选入场原语（按偏好排序，非硬绑定）
ROLE_PREFERENCE = {
    "focal":        ("emerge", "scale", "reveal"),
    "supporting":   ("slide", "fade", "emerge"),
    "relationship": ("draw", "trace", "reveal"),
    "annotation":   ("fade", "slide"),
    "background":   ("static",),
    "decoration":   ("static",),
    "data":         ("grow", "count", "reveal"),
    "label":        ("fade",),
}

# 角色重要度（决定时长/延迟权重：0 轻 ~ 1 重）
ROLE_WEIGHT = {
    "background": 0.0, "decoration": 0.05, "annotation": 0.35, "label": 0.3,
    "supporting": 0.55, "data": 0.6, "relationship": 0.65, "focal": 1.0,
}

# 视觉语法 → 时序修饰（决定「按什么顺序、怎么分组」）
GRAMMAR_SEQUENCING = {
    "branching":     "sequential_stagger",   # 中心→分支逐个
    "accumulation":  "sequential_stagger",   # A→B→C→D 累积
    "causality":     "chain",                # A→link→B
    "progression":   "left_to_right",        # 沿 x 推进
    "trajectory":    "left_to_right",
    "contrast":      "split_two_groups",     # A … pause … B … 对比
    "juxtapose":     "split_two_groups",
    "hierarchy":     "focal_last",           # 焦点最后、更重
    "emphasis":      "focal_last",
    "establish":     "ambient_then_focal",
    "threshold":     "chain",
    "transition":    "ambient_then_focal",
    "abstract":      "ambient_then_focal",
}

# 语法 → 关系类元素的运动倾向（连接关系的动法）
GRAMMAR_RELATION_MOTION = {
    "causality":   "draw",
    "progression": "trace",
    "trajectory":  "trace",
    "hierarchy":   "draw",
    "contrast":    "reveal",
    "juxtapose":   "reveal",
}

# 反 PPT：装饰性 / 背景元素默认不允许运动
NO_MOTION_ROLES = ("background", "decoration")

# 角色别名：真实 pipeline 使用 primary/secondary/support/ambient，
# 与语义角色 focal/supporting/relationship/… 对齐（Agent 用什么词表都能被理解）。
ROLE_ALIAS = {
    "primary": "focal", "hero": "focal", "focal": "focal",
    "secondary": "supporting", "support": "supporting", "supporting": "supporting",
    "ambient": "background", "background": "background",
    "decor": "decoration", "decoration": "decoration",
    "connect": "relationship", "connector": "relationship", "relationship": "relationship",
    "note": "annotation", "annotation": "annotation",
    "data": "data", "label": "label",
}


def normalize_role(role):
    if not role:
        return None
    return ROLE_ALIAS.get(str(role).strip().lower(), role)


def candidates_for(role, element_type=None):
    """给定角色，返回候选原语（过滤掉不支持该元素类型的）。"""
    from .motion_registry import supports
    role = normalize_role(role)
    base = ROLE_PREFERENCE.get(role, ROLE_PREFERENCE["supporting"])
    out = [m for m in base if supports(m, element_type or "*")]
    return out or ["fade"]
