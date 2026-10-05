"""runtime/motion_runtime/conflict.py — Motion Conflict Solver（Runtime Hardening · P0）。

一个对象可能同时受到 FOLLOW / REPULSION / TARGET / CAMERA / LAYOUT / EMPHASIS 影响。
**禁止 last-animation-wins。** 必须建立明确的：

    priority  优先级
    blend     融合模式（add / override / max / min / weighted）
    ownership 归属（同一 owner 的新约束替换旧约束）
    strength  加权强度（weighted 时使用）

同一 (node, channel) 上的多个贡献按确定性规则融合：

    1. override：最高 priority 的贡献独占该通道；
    2. max / min：取极值；
    3. weighted：按 strength 加权平均；
    4. add：全部相加（默认，表达「约束叠加」）。

Conflict Solver 是确定性的：相同输入 + 相同顺序 => 相同输出。若存在无法安全融合的
冲突（例如两个 override 同优先级但取值不同），产出 conflict report 供 Critic/Repair 使用。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .contracts import CHANNEL_NEUTRAL

BLEND_MODES = ("add", "override", "max", "min", "weighted")

# 乘性通道：多来源应以**乘积**融合（scale/opacity 是乘子，不是增量）
MULTIPLICATIVE = ("scale", "opacity")


@dataclass
class Contribution:
    """一条通道贡献。"""

    node: str
    channel: str
    value: float
    priority: int = 0
    blend: str = "add"
    owner: Optional[str] = None
    strength: float = 1.0
    source: Optional[str] = None   # 谁贡献的（原语名/关系名），用于解释
    order: int = 0                 # 稳定排序用

    def to_dict(self) -> dict:
        return {"node": self.node, "channel": self.channel, "value": self.value,
                "priority": self.priority, "blend": self.blend, "owner": self.owner,
                "strength": self.strength, "source": self.source}


class ConflictSolver:
    """把多来源贡献融合成每个节点的确定姿态增量。"""

    def resolve(self, contributions: List[Contribution]):
        # 稳定排序：priority 升序 → order 升序
        ordered = sorted(enumerate(contributions),
                         key=lambda kv: (kv[1].priority, kv[1].order, kv[0]))
        grouped: Dict[str, Dict[str, List[Contribution]]] = {}
        for _, c in ordered:
            grouped.setdefault(c.node, {}).setdefault(c.channel, []).append(c)

        resolved: Dict[str, Dict[str, float]] = {}
        report: List[dict] = []
        for node, channels in grouped.items():
            out = resolved.setdefault(node, {})
            for channel, cs in channels.items():
                value, conflicts = self._resolve_channel(channel, cs)
                out[channel] = value
                for conf in conflicts:
                    report.append(conf)
        return {"transforms": resolved, "conflicts": report}

    @staticmethod
    def _resolve_channel(channel: str, cs: List[Contribution]):
        conflicts: List[dict] = []
        multi = channel in MULTIPLICATIVE
        overrides = [c for c in cs if c.blend == "override"]
        others = [c for c in cs if c.blend != "override"]

        if overrides:
            top = max(overrides, key=lambda c: (c.priority, c.order))
            same_prio = [c for c in overrides if c.priority == top.priority]
            vals = [c.value for c in same_prio]
            if len(same_prio) > 1 and (max(vals) - min(vals)) > 1e-9:
                conflicts.append({
                    "code": "OVERRIDE_TIE", "channel": channel,
                    "priority": top.priority,
                    "values": vals,
                    "owners": [c.owner or c.source for c in same_prio],
                    "msg": "unresolved override tie on channel %r at priority %d"
                           % (channel, top.priority)})
            if multi:
                gain = 1.0
                for c in others:
                    if c.blend == "add":
                        gain *= c.value
                return top.value * gain, conflicts
            gain = sum(c.value for c in others if c.blend == "add")
            return top.value + gain, conflicts

        add_vals = [c.value for c in cs if c.blend == "add"]
        weighted = [c for c in cs if c.blend == "weighted"]
        wsum = sum(max(0.0, c.strength) for c in weighted)
        wavg = (sum(c.value * max(0.0, c.strength) for c in weighted) / wsum
                if wsum > 0 else 0.0)
        if multi:
            base = 1.0
            for v in add_vals:
                base *= v
            value = base * wavg if weighted else base
        else:
            base = sum(add_vals)
            value = base + wavg
        maxs = [c.value for c in cs if c.blend == "max"]
        mins = [c.value for c in cs if c.blend == "min"]
        if maxs:
            value = max(value, max(maxs))
        if mins:
            value = min(value, min(mins))
        return value, conflicts

    # ---------------------------------------------------------- 应用
    @staticmethod
    def apply(scene, resolved: Dict[str, Dict[str, float]]):
        """把融合结果落到场景图节点（相对增量）。返回被改动的节点 id。"""
        changed = []
        for nid, chans in resolved.items():
            if not scene.has(nid):
                continue
            n = scene.get(nid)
            if "dx" in chans:
                n.x += chans["dx"]
            if "dy" in chans:
                n.y += chans["dy"]
            if "scale" in chans:
                n.scale *= chans["scale"]
            if "rotation" in chans:
                n.rotation += chans["rotation"]
            if "opacity" in chans:
                n.opacity *= chans["opacity"]
            changed.append(nid)
        return changed


def base_channels(node: str) -> Dict[str, float]:
    """某节点在无任何运动时的中性通道（= 不变）。"""
    return {k: CHANNEL_NEUTRAL[k] for k in CHANNEL_NEUTRAL}
