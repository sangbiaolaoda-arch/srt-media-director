"""runtime/motion_runtime/relations.py — Relation Runtime（Runtime Hardening · P0）。

Relation Graph 负责「**谁影响谁**」，与 Scene Graph（谁属于谁）严格区分 ——
**不得**为了表达语义关系而改变 DOM hierarchy。

每个 relation 拥有：source / target / relation_type / strength / direction /
lifecycle / trigger。

Lifecycle：ESTABLISH → PROPAGATE → STRENGTHEN / WEAKEN → BREAK / RESOLVE。

关系本身必须**产生运动**，而不能退化成「A fade in, B fade in」。以 CAUSE 为例：

    A.activate
     ↓ relation.establish
     ↓ signal.propagate
     ↓ B.respond
     ↓ B.state_change
     ↓ relation.strengthen
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .contracts import MotionPrimitive

PHASES = ("ESTABLISH", "PROPAGATE", "STRENGTHEN", "WEAKEN", "BREAK", "RESOLVE")

RELATION_TYPES = ("CAUSE", "RESPOND", "POINT", "TARGET", "FOLLOW", "SURROUND",
                  "ATTRACT", "REPEL", "TRANSFER", "CONNECT")

# 关系类型 → 各生命周期阶段携带的运动原语（关系驱动运动）
RELATION_MOTION: Dict[str, Dict[str, List[str]]] = {
    "CAUSE": {"ESTABLISH": ["CONNECT"], "PROPAGATE": ["TRANSFER", "DRAW"],
              "STRENGTHEN": ["EMPHASIZE"]},
    "RESPOND": {"PROPAGATE": ["ACTIVATE"], "STRENGTHEN": ["EMPHASIZE"]},
    "POINT": {"ESTABLISH": ["CONNECT", "DRAW"], "PROPAGATE": ["TARGET"]},
    "TARGET": {"PROPAGATE": ["FOLLOW", "ATTRACT"]},
    "FOLLOW": {"ESTABLISH": ["CONNECT"], "PROPAGATE": ["FOLLOW"]},
    "SURROUND": {"ESTABLISH": ["CONNECT"], "PROPAGATE": ["SURROUND", "ATTRACT"]},
    "ATTRACT": {"ESTABLISH": ["CONNECT", "DRAW"], "PROPAGATE": ["ATTRACT"]},
    "REPEL": {"PROPAGATE": ["REPEL"]},
    "TRANSFER": {"ESTABLISH": ["CONNECT"], "PROPAGATE": ["TRANSFER", "DRAW"]},
    "CONNECT": {"ESTABLISH": ["CONNECT", "DRAW"]},
}

# 关系阶段 → 对 source/target 的作用对象
PHASE_AFFECTS = {
    "ESTABLISH": ("both",), "PROPAGATE": ("target",),
    "STRENGTHEN": ("target",), "WEAKEN": ("target",),
    "BREAK": ("both",), "RESOLVE": ("target",),
}


@dataclass
class Relation:
    source: str
    target: str
    relation_type: str = "CAUSE"
    strength: float = 1.0
    direction: str = "forward"       # forward | backward | bidirectional
    lifecycle: str = "ESTABLISH"
    trigger: Optional[str] = None
    id: Optional[str] = None
    reason: Optional[str] = None

    def __post_init__(self):
        if self.id is None:
            self.id = "%s->%s:%s" % (self.source, self.target, self.relation_type)

    def validate(self) -> List[str]:
        errs = []
        if not self.source:
            errs.append("relation requires source")
        if not self.target:
            errs.append("relation requires target")
        if self.relation_type not in RELATION_TYPES:
            errs.append("unknown relation_type: %s" % self.relation_type)
        if self.lifecycle not in PHASES:
            errs.append("unknown lifecycle: %s" % self.lifecycle)
        if not (0.0 <= self.strength <= 1.0):
            errs.append("strength must be in [0,1]")
        return errs

    def to_dict(self) -> dict:
        return {"id": self.id, "source": self.source, "target": self.target,
                "relation_type": self.relation_type, "strength": self.strength,
                "direction": self.direction, "lifecycle": self.lifecycle,
                "trigger": self.trigger, "reason": self.reason}


class RelationRuntime:
    """管理关系集合与它们的生命周期推进，并把关系编译成运动原语。"""

    def __init__(self):
        self._rels: Dict[str, Relation] = {}

    def add(self, rel: Relation) -> Relation:
        self._rels[rel.id] = rel
        return rel

    def get(self, rid: str) -> Relation:
        return self._rels[rid]

    def all(self) -> List[Relation]:
        return list(self._rels.values())

    def advance(self, rid: str, to_phase: str) -> Relation:
        rel = self._rels[rid]
        if to_phase not in PHASES:
            raise ValueError("bad phase: %s" % to_phase)
        rel.lifecycle = to_phase
        return rel

    def compile_relation(self, rel: Relation, start: float = 0.0,
                         duration: float = 0.5) -> List[MotionPrimitive]:
        """把某个关系在**当前生命周期阶段**编译为具体运动原语。

        关系驱动运动：先建立连接（ESTABLISH），再向 target 传播（PROPAGATE），
        然后按 strength 强化（STRENGTHEN）。
        """
        specs = RELATION_MOTION.get(rel.relation_type, {})
        stages = [rel.lifecycle]
        # 若处于终态，回放完整因果链以表达「关系本身产生运动」
        if rel.lifecycle in ("STRENGTHEN", "RESOLVE"):
            stages = ["ESTABLISH", "PROPAGATE", "STRENGTHEN"]
        elif rel.lifecycle == "WEAKEN":
            stages = ["ESTABLISH", "PROPAGATE", "WEAKEN"]
        elif rel.lifecycle == "BREAK":
            stages = ["ESTABLISH", "BREAK"]

        prims: List[MotionPrimitive] = []
        t = start
        step = duration / max(1, len(stages))
        for ph in stages:
            for mtype in specs.get(ph, []):
                affects = PHASE_AFFECTS.get(ph, ("target",))[0]
                src = rel.source if affects in ("both", "source") else rel.target
                tgt = rel.target if affects != "source" else rel.source
                prims.append(MotionPrimitive(
                    motion_type=mtype, source=src,
                    target=tgt if mtype != "SPLIT" else None,
                    start=t, duration=step,
                    params={"strength": rel.strength},
                    trigger=rel.trigger or ("relation:%s" % rel.relation_type),
                    reason="relation %s/%s" % (rel.relation_type, ph),
                    owner=rel.id))
                t += step
        return prims

    def compile_all(self, start: float = 0.0, duration: float = 1.0) -> List[MotionPrimitive]:
        out: List[MotionPrimitive] = []
        for rel in self._rels.values():
            out.extend(self.compile_relation(rel, start, duration))
        return out

    def audit(self) -> dict:
        issues = []
        for rel in self._rels.values():
            for e in rel.validate():
                issues.append({"relation": rel.id, "error": e})
        return {"status": "FAIL" if issues else "PASS", "count": len(self._rels),
                "issues": issues}
