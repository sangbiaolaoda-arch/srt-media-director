"""Scene Graph — 真正的场景树（Phase 2 · 第一优先级）。

解决「谁属于谁」：结构、父子、变换继承。

节点带稳定 ID；父节点变化时，子节点自动继承 position / scale / rotation /
opacity / visibility / transform，Agent 不需要重算每个子元素的 x/y。

坐标约定：
- node.x / node.y 是「父节点局部像素空间」的偏移（不含自身 scale）。
- 世界原点 = 父世界原点 + (x,y) * 父的累积 scale。
- 世界尺寸 = (w,h) * 自身累积 scale。
因此 parent.move() 会自动带动整棵子树。
"""
from __future__ import annotations

import copy
import math

WEIGHTS = ("primary", "secondary", "support", "decoration")
# 语义容器：Scene → Background/Typography/Elements/Charts/Camera
LAYERS = ("background", "typography", "elements", "charts", "camera")


class SceneNode:
    def __init__(self, nid, kind="element", x=0.0, y=0.0, w=0.0, h=0.0,
                 scale=1.0, rotation=0.0, opacity=1.0, visible=True,
                 weight="support", role=None, text=None, style=None,
                 data=None, semantic_role=None, reason=None):
        self.id = nid
        self.kind = kind
        self.x, self.y, self.w, self.h = float(x), float(y), float(w), float(h)
        self.scale = float(scale)
        self.rotation = float(rotation)
        self.opacity = float(opacity)
        self.visible = bool(visible)
        self.weight = weight
        self.role = role
        self.text = text
        self.style = dict(style or {})
        self.data = dict(data or {})
        self.semantic_role = semantic_role
        self.reason = reason
        self.parent = None
        self.children = []

    # ---------------------------------------------------------------- 结构
    def add(self, child):
        if child.parent is not None:
            child.parent.children.remove(child)
        child.parent = self
        self.children.append(child)
        return child

    def remove(self, child):
        if child in self.children:
            self.children.remove(child)
            child.parent = None

    def descendants(self):
        out = []
        for c in self.children:
            out.append(c)
            out.extend(c.descendants())
        return out

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()

    def find(self, nid):
        for n in self.walk():
            if n.id == nid:
                return n
        return None

    # ------------------------------------------------------------ 变换继承
    def world_scale(self):
        s = self.scale
        n = self.parent
        while n is not None:
            s *= n.scale
            n = n.parent
        return s

    def world_origin(self):
        if self.parent is None:
            return (self.x, self.y)
        px, py = self.parent.world_origin()
        ps = self.parent.world_scale()
        return (px + self.x * ps, py + self.y * ps)

    def world_rotation(self):
        r = self.rotation
        n = self.parent
        while n is not None:
            r += n.rotation
            n = n.parent
        return r

    def world_opacity(self):
        o = self.opacity
        n = self.parent
        while n is not None:
            o *= n.opacity
            n = n.parent
        return o

    def world_box(self):
        ox, oy = self.world_origin()
        s = self.world_scale()
        return [ox, oy, self.w * s, self.h * s]

    def world_center(self):
        x, y, w, h = self.world_box()
        return (x + w / 2.0, y + h / 2.0)

    # ------------------------------------------------------------ 变更操作
    def move(self, dx=0.0, dy=0.0):
        self.x += dx
        self.y += dy
        return self

    def set_pos(self, x=None, y=None):
        if x is not None:
            self.x = float(x)
        if y is not None:
            self.y = float(y)
        return self

    def scale_by(self, k):
        self.scale *= float(k)
        return self

    def rotate(self, deg):
        self.rotation += float(deg)
        return self

    def show(self):
        self.visible = True
        return self

    def hide(self):
        self.visible = False
        return self

    # ------------------------------------------------------------ 序列化
    def to_dict(self):
        return {
            "id": self.id, "kind": self.kind, "weight": self.weight,
            "role": self.role, "text": self.text,
            "local": {"x": self.x, "y": self.y, "w": self.w, "h": self.h,
                      "scale": self.scale, "rotation": self.rotation,
                      "opacity": self.opacity, "visible": self.visible},
            "world_box": [round(v, 2) for v in self.world_box()],
            "style": self.style, "data": self.data,
            "semantic_role": self.semantic_role, "reason": self.reason,
            "children": [c.to_dict() for c in self.children],
        }


class SceneGraph:
    def __init__(self, scene_id):
        self.scene_id = scene_id
        self.root = SceneNode(scene_id, kind="scene", x=0.0, y=0.0)
        self.index = {scene_id: self.root}

    # ---------------------------------------------------------------- 构建
    def add(self, parent_id, nid, **kw):
        parent = self.index.get(parent_id)
        if parent is None:
            raise KeyError("parent not found: %s" % parent_id)
        node = SceneNode(nid, **kw)
        parent.add(node)
        self.index[nid] = node
        return node

    def get(self, nid):
        return self.index[nid]

    def has(self, nid):
        return nid in self.index

    def by_kind(self, kind):
        return [n for n in self.root.walk() if n.kind == kind]

    def by_weight(self, weight):
        return [n for n in self.root.walk() if n.weight == weight]

    # ------------------------------------------------------------ 排版助手
    @staticmethod
    def arrange_row(group, gap=12.0, start_x=None):
        x = group.x if start_x is None else start_x
        for c in group.children:
            c.set_pos(x, group.y)
            x += c.w + gap
        return group

    @staticmethod
    def arrange_ring(group, radius=170.0, center=(340.0, 191.0)):
        cs = [c for c in group.children if c.visible]
        n = max(1, len(cs))
        cx, cy = center
        for i, c in enumerate(cs):
            ang = -math.pi / 2 + 2 * math.pi * i / n
            c.set_pos(cx + radius * math.cos(ang) - c.w / 2.0,
                      cy + radius * math.sin(ang) - c.h / 2.0)
        return group

    # ------------------------------------------------------ Group Animation
    def _template_child(self, group):
        for c in group.children:
            return c
        return None

    def expand(self, group_id, n):
        """把 group 扩到 n 个可见子元素（不足则克隆模板）。返回 group。"""
        g = self.index[group_id]
        tpl = self._template_child(g)
        while len(g.children) < n:
            base = tpl or SceneNode(g.id + "_t", kind="element", w=64, h=64)
            c = copy.deepcopy(base)
            c.id = "%s_%02d" % (g.id, len(g.children) + 1)
            c.parent = None
            c.children = []
            g.add(c)
            self.index[c.id] = c
        for i, c in enumerate(g.children):
            c.visible = i < n
        return g

    def collapse(self, group_id, keep=1):
        g = self.index[group_id]
        for i, c in enumerate(g.children):
            c.visible = i < keep
        return g

    def scatter(self, group_id, radius):
        g = self.index[group_id]
        return self.arrange_ring(g, radius=radius)

    def compress(self, group_id, factor=0.5):
        g = self.index[group_id]
        for c in g.children:
            if c.visible:
                c.scale_by(factor)
        return g

    # ------------------------------------------------------ Scene Continuity
    def clone(self, new_scene_id):
        """跨镜头复用同一世界（连续优先「变化」而非「重建」）。"""
        g = SceneGraph(new_scene_id)
        g.root = copy.deepcopy(self.root)
        g.root.id = new_scene_id
        g.index = {}
        for n in g.root.walk():
            g.index[n.id] = n
        return g

    def rekey(self, mapping):
        """把一批节点改名（如 person_01 沿用而非另建 person_02）。"""
        for old, new in mapping.items():
            if old in self.index:
                n = self.index.pop(old)
                n.id = new
                self.index[new] = n
        return self

    def to_dict(self):
        return {"scene_id": self.scene_id, "root": self.root.to_dict()}
