"""Visual DSL — Agent 面向的可编译视觉场景（Phase 2 · 第十六优先级）。

目标不是「Agent 写 HTML」，而是「Agent 编排一个可编译的视觉场景」：

    scene("choice_overload")
      person = element("person").at("center").weight("primary")
      choices = group("choices").around(person).weight("secondary")
      relation(choices, person, "surround")
      state("start").show(person).show(choices.first())
      state("overload").expand(choices, 6)
      state("collapse").collapse(choices, 1)
      transition("start","overload").expand(choices).stagger(choices)
      camera.focus(person)

DSL 只描述「画什么 / 为什么 / 关系 / 如何变化」，不写 x/y、不写 CSS。
"""
from __future__ import annotations

from .scene_graph import SceneGraph
from .relation_graph import RelationGraph
from .state_graph import StateGraph
from .transitions import Transition
from . import timeline as TL
from . import composition


class _Node:
    def __init__(self, dsl, node):
        self.dsl = dsl
        self.node = node

    @property
    def id(self):
        return self.node.id

    def at(self, slot):
        self.node.data["slot"] = slot
        composition.place(self.node, slot, self.dsl.canvas)
        return self

    def weight(self, w):
        self.node.weight = w
        return self

    def size(self, w, h):
        self.node.w, self.node.h = float(w), float(h)
        return self

    def text(self, t):
        self.node.text = t
        return self

    def reason(self, r):
        self.node.reason = r
        return self

    def semantic(self, role):
        self.node.semantic_role = role
        return self

    def child(self, kind, cid, x=0.0, y=0.0, w=40.0, h=40.0, **kw):
        c = self.dsl.graph.add(self.node.id, cid, kind=kind, x=x, y=y,
                               w=w, h=h, weight=kw.pop("weight", self.node.weight),
                               role=kw.pop("role", None),
                               text=kw.pop("text", None), **kw)
        return _Node(self.dsl, c)

    def around(self, target):
        self.dsl.relations.add(self.node.id, target.id
                               if hasattr(target, "id") else target, "surround")
        return self

    def first(self):
        return self.children()[0] if self.children() else None

    def children(self):
        return [c.id for c in self.node.children]


class _Camera:
    def __init__(self, dsl):
        self.dsl = dsl

    def focus(self, target):
        self.dsl.camera_focus = target.id if hasattr(target, "id") else target
        return self


class DSL:
    def __init__(self, scene_id, canvas=(680, 382)):
        self.scene_id = scene_id
        self.canvas = canvas
        self.graph = SceneGraph(scene_id)
        self.relations = RelationGraph(scene_id)
        self.states = StateGraph(scene_id)
        self.timeline = TL.TimelineGraph()
        self.transitions = []
        self.camera_focus = None
        self._seq = 0

    # -------------------------------------------------------------- 元素
    def element(self, kind, eid=None):
        self._seq += 1
        eid = eid or ("%s_%02d" % (kind, self._seq))
        n = self.graph.add(self.scene_id, eid, kind=kind, w=80.0, h=80.0,
                           weight="support")
        return _Node(self, n)

    def group(self, eid=None):
        self._seq += 1
        eid = eid or ("group_%02d" % self._seq)
        n = self.graph.add(self.scene_id, eid, kind="group", w=0.0, h=0.0,
                           weight="support")
        return _Node(self, n)

    # -------------------------------------------------------------- 关系
    def relation(self, a, b, rtype, **opts):
        self.relations.add(a.id if hasattr(a, "id") else a,
                           b.id if hasattr(b, "id") else b, rtype, **opts)
        return self

    def surround(self, a, b):  return self.relation(a, b, "surround")
    def point_to(self, a, b):  return self.relation(a, b, "point_to")
    def attach_to(self, a, b): return self.relation(a, b, "attach_to")

    # -------------------------------------------------------------- 状态
    def state(self, name):
        return self.states.state(name)

    def transition(self, a, b):
        t = Transition(a, b)
        self.transitions.append(t)
        return t

    # -------------------------------------------------------------- 时间
    def enter(self, node, **kw):
        nid = node.id if hasattr(node, "id") else node
        return self.timeline.add(nid, kw.pop("action", "appear"), **kw)

    def camera(self):
        return _Camera(self)

    def compile(self):
        return {"scene_id": self.scene_id, "canvas": self.canvas,
                "graph": self.graph, "relations": self.relations,
                "states": self.states, "timeline": self.timeline,
                "transitions": self.transitions, "camera_focus": self.camera_focus}


def scene(scene_id, canvas=(680, 382)):
    return DSL(scene_id, canvas)
