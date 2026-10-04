"""relationship.py — 关系图（图，不是列表）。

Agent 用**有向关系图**表达元素间的语义关系，而不是散列元素。
    [{"from":"small_actions","relation":"accumulate_into","to":"trajectory"},
     {"from":"trajectory","relation":"crosses","to":"threshold"}]

这张图是 Runtime 决定「谁挨着谁、谁指向谁」的唯一依据——但图里仍然**没有坐标**。
"""

RELATIONS = ("accumulate_into", "crosses", "causes", "contrast_with", "precedes",
             "contains", "supports", "refines", "juxtaposes", "connects", "relate")


def build(edges):
    """规范化边列表（补默认 relation）。"""
    out = []
    for e in edges or []:
        out.append({"from": e.get("from"), "relation": e.get("relation", "relate"),
                    "to": e.get("to")})
    return out


def nodes(edges):
    """按首次出现顺序收集所有节点。"""
    ns = []
    for e in edges or []:
        for k in ("from", "to"):
            v = e.get(k)
            if v and v not in ns:
                ns.append(v)
    return ns


def validate(edges):
    """关系图契约：非空、每边三要素齐全、relation 合法。返回 issues（空 = PASS）。"""
    issues = []
    if not edges:
        issues.append({"code": "REL_EMPTY", "msg": "relationship 必须非空（图，不是列表）"})
        return issues
    for e in edges:
        if not all(k in e and e.get(k) for k in ("from", "relation", "to")):
            issues.append({"code": "REL_MALFORMED", "msg": "边缺 from/relation/to: %r" % (e,)})
        elif e["relation"] not in RELATIONS:
            issues.append({"code": "REL_UNKNOWN", "msg": "未知关系 %r" % e["relation"]})
    return issues


def out_edges(edges, node):
    """从某节点出发的边。"""
    return [e for e in edges if e.get("from") == node]


def sinks(edges):
    """只进不出的节点——天然的视觉焦点候选。"""
    src = {e.get("from") for e in edges or []}
    dst = {e.get("to") for e in edges or []}
    return [n for n in nodes(edges) if n in dst and n not in src]


def to_dot(edges, focal=None):
    """导出 Graphviz DOT（可视化 / 调试）。焦点节点加粗。"""
    lines = ["digraph relationship {"]
    for n in nodes(edges):
        attr = ' [penwidth=2.5, color="#C4452B"]' if n == focal else ""
        lines.append('  "%s"%s;' % (n, attr))
    for e in edges or []:
        lines.append('  "%s" -> "%s" [label="%s"];' % (e.get("from"), e.get("to"), e.get("relation")))
    lines.append("}")
    return "\n".join(lines)
