"""runtime/motion_runtime/runtime.py — Runtime 集成层（Runtime Hardening · P0）。

把 Scene Graph / Relation Runtime / State Graph / Motion Primitives /
Conflict Solver / Camera / Timeline 串成**确定性**执行系统：

    scene (层级)  →  relation (语义关系)  →  primitives (语义运动)
                  →  conflict solver (约束融合)  →  final transform

确定性要求：给定相同输入，任意时刻 t 的采样结果完全一致（无随机、无 wall-clock）。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .camera import Camera
from .conflict import ConflictSolver, Contribution
from .connector import ConnectorRuntime
from .contracts import (MotionPrimitive, SceneCtx, PRIMITIVES)
from .events import EventGraph
from .identity import IdentityRegistry
from .invariants import run_all
from .relations import Relation, RelationRuntime
from .scene import SceneGraph
from .states import StateRuntime


class MotionRuntime:
    def __init__(self, scene: Optional[SceneGraph] = None, fps: float = 30.0):
        self.scene = scene or SceneGraph()
        self.fps = fps
        self.relations = RelationRuntime()
        self.states = StateRuntime()
        self.states.default_chain()
        self.connectors = ConnectorRuntime()
        self.camera = Camera()
        self.events = EventGraph()
        self.identity = IdentityRegistry()
        self.solver = ConflictSolver()
        self.primitives: List[MotionPrimitive] = []
        self.identity.register_all(self.scene.ids())

    # ---------------------------------------------------------- 装配
    def add(self, *prims: MotionPrimitive) -> "MotionRuntime":
        for p in prims:
            self.primitives.append(p)
            self.identity.register(p.source)
            if p.target:
                self.identity.register(p.target)
        return self

    def add_relation(self, rel: Relation) -> "MotionRuntime":
        self.relations.add(rel)
        return self

    # ---------------------------------------------------------- 上下文
    def _ctx(self, scene: SceneGraph) -> SceneCtx:
        return SceneCtx(boxes={nid: scene.world_box(nid) for nid in scene.ids()})

    def contributions_at(self, t: float, scene: Optional[SceneGraph] = None) -> List[Contribution]:
        scene = scene or self.scene
        ctx = self._ctx(scene)
        out: List[Contribution] = []
        for i, p in enumerate(self.primitives):
            sample = p.sample(ctx, t)
            if not sample:
                continue
            for node, chans in sample.items():
                for ch, val in chans.items():
                    if ch == "state":
                        continue
                    out.append(Contribution(node=node, channel=ch, value=val,
                                            priority=p.priority, blend=p.blend,
                                            owner=p.owner, strength=1.0,
                                            source=p.motion_type, order=i))
        return out

    def resolve_at(self, t: float, scene: Optional[SceneGraph] = None):
        return self.solver.resolve(self.contributions_at(t, scene))

    # ---------------------------------------------------------- 采样
    def sample(self, t: float) -> dict:
        """在时刻 t 求解所有运动，返回 {node: transform} + camera + conflicts。"""
        res = self.resolve_at(t)
        return {"t": round(t, 6), "transforms": res["transforms"],
                "camera": self.camera.to_dict(), "conflicts": res["conflicts"]}

    def sample_frames(self, duration: float, keyframes: Optional[List[float]] = None) -> List[dict]:
        """按归一化关键帧采样（0,25,50,75,100% + 可选 10/33/66/90%）。"""
        kf = keyframes if keyframes is not None else [0.0, 0.25, 0.5, 0.75, 1.0,
                                                      0.10, 0.33, 0.66, 0.90]
        frames = []
        for pct in sorted(set(round(k, 4) for k in kf)):
            frames.append(self.sample(pct * duration))
        return frames

    def timeline(self) -> List[dict]:
        """合并事件图 + 原语起止，产出确定性时间线。"""
        tl = []
        for ev in self.events.schedule():
            tl.append({"kind": "event", **ev})
        for p in self.primitives:
            s, e = p.time_range()
            tl.append({"kind": "motion", "motion": p.motion_type, "source": p.source,
                       "target": p.target, "start": round(s, 6), "end": round(e, 6),
                       "trigger": p.trigger, "reason": p.reason})
        tl.sort(key=lambda x: (x.get("start", x.get("t", 0.0)), x.get("motion", x.get("event", ""))))
        return tl

    # ---------------------------------------------------------- 校验
    def validate(self, t_end: Optional[float] = None) -> dict:
        if t_end is None:
            t_end = max([p.time_range()[1] for p in self.primitives] or [0.0]) + 0.1
        before = list(self.scene.ids())
        # 采样在 t_end 后场景 id 不变（结构稳定）
        after = list(self.scene.ids())
        ctx = self._ctx(self.scene)
        # 父子关系用于 Parent invariant
        pc = None
        for nid in self.scene.ids():
            if self.scene.get(nid).parent:
                pc = (nid, self.scene.get(nid).parent)
                break
        return run_all(scene=self.scene, before_ids=before, after_ids=after,
                       motions=self.primitives, primitives=self.primitives, ctx=ctx,
                       state_runtime=self.states, relation_runtime=self.relations,
                       t_end=t_end, parent_child=pc)

    def manifest(self) -> dict:
        return {
            "nodes": self.scene.count(),
            "primitives": [p.to_dict() for p in self.primitives],
            "relations": [r.to_dict() for r in self.relations.all()],
            "connectors": [c.to_dict() for c in self.connectors.all()],
            "camera": self.camera.to_dict(),
            "events": self.events.audit(),
            "deterministic": True,
        }
