"""runtime/motion_runtime/scene.py — Scene Graph（Runtime Hardening · P0）。

Scene Graph 只负责一件事：**谁属于谁**（层级隶属），不表达语义关系（那是 Relation Graph）。

必须支持：parent / children / local_transform / world_transform / visibility /
identity / z_index。

父级移动时：

    parent transform
            ↓
    children world transform

必须自动继承 —— **禁止**依赖重复修改每个 child 的绝对坐标。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# --- canonical delegation bootstrap (single source of truth) ---------------
# 2D affine transform lives in exactly one place: geometry.matrix. This module
# no longer owns matrix math; it delegates. See runtime/docs/motion-inventory.md.
import os as _os
import sys as _sys
_RUNTIME_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _RUNTIME_DIR not in _sys.path:
    _sys.path.insert(0, _RUNTIME_DIR)
from geometry import matrix as _geom  # noqa: E402

Mat = Tuple[float, float, float, float, float, float]  # a,b,c,d,e,f
IDENTITY_M: Mat = _geom.IDENTITY


def mat_mul(m1: Mat, m2: Mat) -> Mat:
    """世界矩阵合成：world = parent @ local（委托 geometry.matrix 唯一真相源）。"""
    return _geom.mat_mul(m1, m2)


def mat_apply(m: Mat, x: float, y: float) -> Tuple[float, float]:
    return _geom.mat_apply(m, x, y)


def local_matrix(node: "Node") -> Mat:
    """local = T(x,y) @ R(rotation) @ S(scale)（委托 geometry.matrix）。"""
    return _geom.mat_from_parts(node.x, node.y, node.rotation, node.scale)


@dataclass
class Node:
    id: str
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0
    scale: float = 1.0
    rotation: float = 0.0
    opacity: float = 1.0
    z_index: int = 0
    visible: bool = True
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "x": round(self.x, 4), "y": round(self.y, 4),
                "w": self.w, "h": self.h, "scale": round(self.scale, 6),
                "rotation": round(self.rotation, 6), "opacity": round(self.opacity, 6),
                "z_index": self.z_index, "visible": self.visible,
                "parent": self.parent, "children": list(self.children)}

    def copy(self) -> "Node":
        return Node(self.id, self.x, self.y, self.w, self.h, self.scale,
                    self.rotation, self.opacity, self.z_index, self.visible,
                    self.parent, list(self.children))


class SceneGraph:
    """层级场景图：world_transform 由父子链自动合成。"""

    def __init__(self, root: str = "root"):
        self.root = root
        self.nodes: Dict[str, Node] = {}
        self.nodes[root] = Node(id=root, w=1920, h=1080)

    # ---------------------------------------------------------- 结构
    def add(self, nid: str, parent: Optional[str] = None, x: float = 0.0, y: float = 0.0,
            w: float = 0.0, h: float = 0.0, z_index: int = 0, **kw) -> Node:
        if nid in self.nodes:
            raise ValueError("node already exists: %s" % nid)
        n = Node(id=nid, x=x, y=y, w=w, h=h, z_index=z_index, parent=parent, **kw)
        self.nodes[nid] = n
        self.nodes[parent or self.root].children.append(nid)
        return n

    def has(self, nid: str) -> bool:
        return nid in self.nodes

    def get(self, nid: str) -> Node:
        return self.nodes[nid]

    def reparent(self, child: str, new_parent: str) -> None:
        c = self.nodes[child]
        if c.parent and child in self.nodes[c.parent].children:
            self.nodes[c.parent].children.remove(child)
        c.parent = new_parent
        self.nodes[new_parent].children.append(child)

    # ---------------------------------------------------------- 变换
    def chain(self, nid: str) -> List[str]:
        out, cur = [], nid
        while cur is not None:
            out.append(cur)
            cur = self.nodes[cur].parent
        return list(reversed(out))

    def world_matrix(self, nid: str) -> Mat:
        m = IDENTITY_M
        for n in self.chain(nid):
            m = mat_mul(m, local_matrix(self.nodes[n]))
        return m

    def world_opacity(self, nid: str) -> float:
        o = 1.0
        for n in self.chain(nid):
            o *= self.nodes[n].opacity
        return o

    def world_visible(self, nid: str) -> bool:
        return all(self.nodes[n].visible for n in self.chain(nid))

    def world_box(self, nid: str) -> Tuple[float, float, float, float]:
        m = self.world_matrix(nid)
        n = self.nodes[nid]
        pts = [mat_apply(m, 0, 0), mat_apply(m, n.w, 0),
               mat_apply(m, n.w, n.h), mat_apply(m, 0, n.h)]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    def world_center(self, nid: str) -> Tuple[float, float]:
        x, y, w, h = self.world_box(nid)
        return (x + w / 2.0, y + h / 2.0)

    # ---------------------------------------------------------- 采样/克隆
    def boxes(self) -> Dict[str, Tuple[float, float, float, float]]:
        return {nid: self.world_box(nid) for nid in self.nodes}

    def clone(self) -> "SceneGraph":
        g = SceneGraph(self.root)
        g.nodes = {nid: n.copy() for nid, n in self.nodes.items()}
        return g

    def snapshot(self) -> dict:
        return {nid: {"box": [round(v, 4) for v in self.world_box(nid)],
                      "world_opacity": round(self.world_opacity(nid), 6),
                      "visible": self.world_visible(nid),
                      "z_index": self.nodes[nid].z_index}
                for nid in self.nodes}

    def ids(self) -> List[str]:
        return list(self.nodes.keys())

    def count(self) -> int:
        return len(self.nodes)


def nearby(a: Tuple[float, float], b: Tuple[float, float], eps: float = 1e-6) -> bool:
    return abs(a[0] - b[0]) <= eps and abs(a[1] - b[1]) <= eps
