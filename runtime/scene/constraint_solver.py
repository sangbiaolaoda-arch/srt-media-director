"""Constraint Solver — 语义约束 → 真实像素（Phase 2 · 第六优先级）。

Agent 只写语义约束（center / right_of / above / surround / between ...），
求解器算出真实坐标。父节点位置改变时，依赖它的节点自动重算。

算法：迭代松弛。每个根级节点先取显式位置（或默认中心），随后按关系把
「被约束节点」重新摆到「锚点节点」的相应方位，多轮直到收敛。子节点位置
由局部偏移 + 父变换继承决定，不参与关系求解。
"""
from __future__ import annotations

RELATIONAL = {"left_of", "right_of", "above", "below", "inside", "surround",
              "contain", "between", "near", "far", "attach_to", "follow",
              "point_to", "connect", "contrast"}


def _place(dx, dy, obstacle, mover, gap):
    """把 mover 放到相对 obstacle 的 (dx,dy) 主方向，间距 gap。"""
    ox, oy, ow, oh = obstacle
    mw, mh = mover[2], mover[3]
    if dx == 1 and dy == 0:      # right
        return [ox + ow + gap, oy + (oh - mh) / 2.0]
    if dx == -1 and dy == 0:     # left
        return [ox - gap - mw, oy + (oh - mh) / 2.0]
    if dx == 0 and dy == -1:     # above
        return [ox + (ow - mw) / 2.0, oy - gap - mh]
    if dy == 1 and dx == 0:      # below
        return [ox + (ow - mw) / 2.0, oy + oh + gap]
    return [ox, oy]


class ConstraintSolver:
    def __init__(self, scene, relations, canvas=(680, 382)):
        self.scene = scene
        self.rel = relations
        self.W, self.H = canvas

    # ---------------------------------------------------------------- 求解
    def solve(self, passes=6):
        graph = self.scene
        root_ids = [c.id for c in graph.root.children]

        # 1) 初始位置：显式位置优先，否则默认居中
        for nid in root_ids:
            n = graph.get(nid)
            if not n.data.get("explicit_pos"):
                # 保留声明的位置；无声明则先给中心
                if n.w == 0 and n.h == 0:
                    n.w, n.h = 80.0, 80.0
        # 2) 迭代松弛关系
        for _ in range(passes):
            for r in self.rel.relations:
                t = r["type"]
                if t not in RELATIONAL:
                    continue
                a = graph.get(r["a"])
                b = graph.get(r["b"])
                if a.parent is not graph.root:
                    continue  # 仅求解根级节点（子节点随父）
                gap = r.get("gap", self.rel.default_gap(t))
                abox = a.world_box()
                bbox = b.world_box()
                if t == "right_of":
                    a.set_pos(*_place(1, 0, bbox, abox, gap))
                elif t == "left_of":
                    a.set_pos(*_place(-1, 0, bbox, abox, gap))
                elif t == "above":
                    a.set_pos(*_place(0, -1, bbox, abox, gap))
                elif t == "below":
                    a.set_pos(*_place(0, 1, bbox, abox, gap))
                elif t in ("near",):
                    a.set_pos(*_place(1, 0, bbox, abox, gap))
                elif t in ("far",):
                    a.set_pos(*_place(1, 0, bbox, abox, gap))
                elif t == "contrast":
                    a.set_pos(bbox[0] + bbox[2] + gap,
                              bbox[1] + bbox[3] - abox[3])  # 对角对置
                elif t in ("inside", "contain"):
                    a.set_pos(bbox[0] + (bbox[2] - abox[2]) / 2.0,
                              bbox[1] + (bbox[3] - abox[3]) / 2.0)
                elif t == "attach_to":
                    a.set_pos(bbox[0], bbox[1] + bbox[3] + (r.get("dy") or 6))
                elif t in ("follow", "point_to", "connect"):
                    a.set_pos(bbox[0] + bbox[2] + gap, bbox[1])
                elif t == "between":
                    c = graph.get(r["c"])
                    cbox = c.world_box()
                    midx = (bbox[0] + cbox[0]) / 2.0
                    midy = (bbox[1] + cbox[1]) / 2.0
                    a.set_pos(midx, midy)
                elif t == "surround":
                    self._surround(a, bbox, r)
        # 3) 安全区夹取
        for nid in root_ids:
            n = graph.get(nid)
            if n.data.get("no_clamp"):
                continue
            w, h = n.world_box()[2], n.world_box()[3]
            n.x = max(8.0, min(n.x, self.W - w - 8.0))
            n.y = max(8.0, min(n.y, self.H - h - 8.0))
        return {nid: graph.get(nid).world_box() for nid in root_ids}

    def _surround(self, group, center_box, r):
        cx = center_box[0] + center_box[2] / 2.0
        cy = center_box[1] + center_box[3] / 2.0
        radius = r.get("radius", 150)
        vis = [c for c in group.children if c.visible]
        n = max(1, len(vis))
        import math
        for i, c in enumerate(vis):
            ang = -math.pi / 2 + 2 * math.pi * i / n
            c.set_pos(cx + radius * math.cos(ang) - c.w / 2.0,
                      cy + radius * math.sin(ang) - c.h / 2.0)

    def anchor_point(self, nid):
        return self.scene.get(nid).world_center()
