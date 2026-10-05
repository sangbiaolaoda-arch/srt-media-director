"""runtime/motion_runtime/connector.py — 动态 Connector（Runtime Hardening · P1）。

Connector 不允许只保存静态 x1/y1/x2/y2 —— 必须绑定 source anchor / target anchor：

    A 移动 → connector 自动更新
    B resize → connector 自动重新计算

必须可测试的场景：source move / target move / source resize / target resize /
group transform / camera transform。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Tuple

from .scene import SceneGraph, mat_apply


def _anchor_point(scene: SceneGraph, nid: str, fx: float, fy: float) -> Tuple[float, float]:
    """节点局部锚点 (fx,fy ∈ [0,1]) 经过 world transform 后的世界坐标。"""
    n = scene.get(nid)
    m = scene.world_matrix(nid)
    return mat_apply(m, n.w * fx, n.h * fy)


@dataclass
class DynamicConnector:
    id: str
    source: str
    target: str
    source_anchor: Tuple[float, float] = (1.0, 0.5)  # 默认从 source 右中出发
    target_anchor: Tuple[float, float] = (0.0, 0.5)  # 到达 target 左中
    progress: float = 1.0  # 0..1，可由 CONNECT/DISCONNECT/TRANSFER 驱动

    def recompute(self, scene: SceneGraph) -> dict:
        x1, y1 = _anchor_point(scene, self.source, *self.source_anchor)
        x2, y2 = _anchor_point(scene, self.target, *self.target_anchor)
        # progress 影响可见长度（0 => 收到 source 端）
        ex = x1 + (x2 - x1) * self.progress
        ey = y1 + (y2 - y1) * self.progress
        return {"id": self.id, "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "ex": ex, "ey": ey,
                "length": math.hypot(x2 - x1, y2 - y1),
                "visible_length": math.hypot(ex - x1, ey - y1)}

    def to_dict(self) -> dict:
        return {"id": self.id, "source": self.source, "target": self.target,
                "source_anchor": list(self.source_anchor),
                "target_anchor": list(self.target_anchor), "progress": self.progress}


class ConnectorRuntime:
    def __init__(self):
        self._conns: dict = {}

    def bind(self, cid: str, source: str, target: str, **kw) -> DynamicConnector:
        c = DynamicConnector(id=cid, source=source, target=target, **kw)
        self._conns[cid] = c
        return c

    def get(self, cid: str) -> DynamicConnector:
        return self._conns[cid]

    def all(self):
        return list(self._conns.values())

    def recompute_all(self, scene: SceneGraph) -> dict:
        return {cid: c.recompute(scene) for cid, c in self._conns.items()}
