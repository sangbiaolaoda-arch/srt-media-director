"""State Graph — 状态 + 迁移（Phase 2 · 第三优先级）。

一个镜头不是「元素 + 一堆动画」，而是：
    State A → Transition → State B
Agent 描述 start / overload / collapse，而不是 translate/animation-delay。

State 记录「该状态下每个节点的可见性与属性」，可 apply() 到场景以渲染该帧；
Transition 记录两个状态间的语义动作，交由 Motion Compiler 翻译。
"""
from __future__ import annotations


class State:
    def __init__(self, name):
        self.name = name
        self.visible = {}          # id -> bool
        self.group_count = {}      # group_id -> n（expand/collapse 目标）
        self.attrs = {}            # id -> {scale/...}
        self.notes = []

    # 语义操作（只记录意图，不写 CSS）
    def show(self, *ids):
        for i in ids:
            self.visible[i] = True
        return self

    def hide(self, *ids):
        for i in ids:
            self.visible[i] = False
        return self

    def expand(self, group_id, n):
        self.group_count[group_id] = n
        return self

    def collapse(self, group_id, keep=1):
        self.group_count[group_id] = keep
        return self

    def transform(self, nid, **kw):
        self.attrs.setdefault(nid, {}).update(kw)
        return self

    def note(self, txt):
        self.notes.append(txt)
        return self

    def apply(self, graph):
        """把该状态落到一份可渲染的场景快照（深拷贝后修改）。"""
        snap = graph.clone(graph.scene_id)
        for nid, vis in self.visible.items():
            if snap.has(nid):
                snap.get(nid).visible = vis
        for gid, n in self.group_count.items():
            if snap.has(gid):
                snap.expand(gid, n) if n > len(snap.get(gid).children) \
                    else snap.collapse(gid, n)
        for nid, attrs in self.attrs.items():
            if snap.has(nid):
                n = snap.get(nid)
                for k, v in attrs.items():
                    setattr(n, k, v)
        return snap

    def to_dict(self):
        return {"name": self.name, "visible": self.visible,
                "group_count": self.group_count, "attrs": self.attrs,
                "notes": self.notes}


class StateGraph:
    def __init__(self, scene_id):
        self.scene_id = scene_id
        self.states = {}
        self.order = []
        self.edges = []

    def state(self, name):
        if name not in self.states:
            self.states[name] = State(name)
            self.order.append(name)
        return self.states[name]

    def get(self, name):
        return self.states[name]

    def transition(self, a, b, actions=None):
        """记录一条语义迁移边。actions: [(action, opts) | action, ...]"""
        edge = {"from": a, "to": b, "actions": list(actions or [])}
        self.edges.append(edge)
        return edge

    def validate(self):
        issues = []
        for e in self.edges:
            for side in ("from", "to"):
                if e[side] not in self.states:
                    issues.append({"severity": "err",
                                   "code": "TRANSITION_STATE_MISSING",
                                   "msg": "transition references nonexistent state %r"
                                          % e[side]})
        return {"status": "FAIL" if issues else "PASS", "issues": issues,
                "states": len(self.states), "edges": len(self.edges)}

    def to_dict(self):
        return {"scene_id": self.scene_id,
                "states": {k: v.to_dict() for k, v in self.states.items()},
                "order": self.order, "edges": self.edges}
