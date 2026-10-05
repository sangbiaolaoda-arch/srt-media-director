"""Relation Graph — 语义关系图（Phase 2 · 第二优先级）。

Scene Graph 解决「谁属于谁」；Relation Graph 解决
「谁和谁有什么意义上的关系」。

关系是 Runtime 可理解的数据，而不只是 Agent 自然语言。

分三类：
- 空间关系（可求解为几何约束）：left_of / right_of / above / below /
  inside / surround / contain / between / near / far
- 结构/连接关系（锚定 + 端点重算）：attach_to / follow / point_to / connect
- 语义关系（表达意义；可附带几何提示）：contrast / cause / result /
  block / depend_on / belong_to
"""
from __future__ import annotations

SPATIAL = {"left_of", "right_of", "above", "below", "inside", "surround",
           "contain", "between", "near", "far"}
STRUCTURAL = {"attach_to", "follow", "point_to", "connect"}
SEMANTIC = {"contrast", "cause", "result", "block", "depend_on", "belong_to"}
ALL_TYPES = SPATIAL | STRUCTURAL | SEMANTIC

# 关系 → 默认几何参数（由 Constraint Solver 消费）
_DEFAULT_GAP = {"left_of": 40, "right_of": 40, "above": 40, "below": 40,
                "near": 24, "far": 160}


class RelationGraph:
    def __init__(self, scene_id):
        self.scene_id = scene_id
        self.relations = []

    def add(self, a, b, rtype, **opts):
        if rtype not in ALL_TYPES:
            raise ValueError("unknown relation type: %s" % rtype)
        rel = {"a": a, "b": b, "type": rtype}
        rel.update(opts)
        self.relations.append(rel)
        return rel

    # 便捷构造
    def left_of(self, a, b, **o):    return self.add(a, b, "left_of", **o)
    def right_of(self, a, b, **o):   return self.add(a, b, "right_of", **o)
    def above(self, a, b, **o):      return self.add(a, b, "above", **o)
    def below(self, a, b, **o):      return self.add(a, b, "below", **o)
    def inside(self, a, b, **o):     return self.add(a, b, "inside", **o)
    def surround(self, a, b, **o):   return self.add(a, b, "surround", **o)
    def attach_to(self, a, b, **o):  return self.add(a, b, "attach_to", **o)
    def connect(self, a, b, **o):    return self.add(a, b, "connect", **o)
    def point_to(self, a, b, **o):   return self.add(a, b, "point_to", **o)
    def contrast(self, a, b, **o):   return self.add(a, b, "contrast", **o)

    def of_type(self, rtype):
        return [r for r in self.relations if r["type"] == rtype]

    def touching(self, nid):
        return [r for r in self.relations if r["a"] == nid or r["b"] == nid]

    def validate(self, graph):
        """结构校验：关系两端必须存在；调用关系必须已知。"""
        issues = []
        for r in self.relations:
            for side in ("a", "b"):
                if not graph.has(r[side]):
                    issues.append({"severity": "err", "code": "RELATION_UNRESOLVED",
                                   "relation": r,
                                   "msg": "relation %s->%s references missing node %r"
                                          % (r["a"], r["b"], r[side])})
            if r["type"] == "between":
                c = r.get("c")
                if not c or not graph.has(c):
                    issues.append({"severity": "err", "code": "RELATION_UNRESOLVED",
                                   "relation": r,
                                   "msg": "between requires existing third node"})
        return {"status": "FAIL" if issues else "PASS", "issues": issues,
                "count": len(self.relations)}

    def default_gap(self, rtype):
        return _DEFAULT_GAP.get(rtype, 32)

    def to_dict(self):
        return {"scene_id": self.scene_id, "relations": self.relations}
