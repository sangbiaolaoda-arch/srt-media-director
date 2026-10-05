"""runtime/motion_runtime/camera.py — Camera / Attention（Runtime Hardening · P1）。

Camera 不再只是 pan / zoom，而是 Scene-level object，目标是**控制观众当前应该关注什么**：

    focus / follow / pan / zoom / reframe / attention_transfer

    A dominant
     ↓
    A → B relation activates
     ↓
    attention transfers to B
     ↓
    camera follows B

Camera 必须参与 Timeline / Event Graph（提供触发式 API）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .scene import SceneGraph


@dataclass
class Camera:
    x: float = 0.0          # 相机中心（世界坐标）
    y: float = 0.0
    zoom: float = 1.0
    focus_id: Optional[str] = None
    attention: Optional[str] = None   # 当前注意力对象

    def to_dict(self) -> dict:
        return {"x": round(self.x, 4), "y": round(self.y, 4),
                "zoom": round(self.zoom, 6), "focus_id": self.focus_id,
                "attention": self.attention}

    # ---------------------------------------------------------- 操作
    def focus(self, scene: SceneGraph, nid: str, zoom: Optional[float] = None) -> dict:
        cx, cy = scene.world_center(nid)
        self.focus_id = nid
        self.attention = nid
        self.x, self.y = cx, cy
        if zoom is not None:
            self.zoom = zoom
        return self.to_dict()

    def follow(self, scene: SceneGraph, nid: str, weight: float = 1.0) -> dict:
        cx, cy = scene.world_center(nid)
        w = max(0.0, min(1.0, weight))
        self.x += (cx - self.x) * w
        self.y += (cy - self.y) * w
        self.focus_id = nid
        self.attention = nid
        return self.to_dict()

    def pan(self, dx: float, dy: float) -> dict:
        self.x += dx
        self.y += dy
        return self.to_dict()

    def zoom_to(self, z: float) -> dict:
        self.zoom = z
        return self.to_dict()

    def reframe(self, scene: SceneGraph, ids: List[str]) -> dict:
        """把一组对象重新框入视野：取包围盒中心与合适 zoom。"""
        boxes = [scene.world_box(i) for i in ids if scene.has(i)]
        if not boxes:
            return self.to_dict()
        x0 = min(b[0] for b in boxes)
        y0 = min(b[1] for b in boxes)
        x1 = max(b[0] + b[2] for b in boxes)
        y1 = max(b[1] + b[3] for b in boxes)
        self.x, self.y = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        span = max(x1 - x0, y1 - y0) or 1.0
        self.zoom = max(0.2, min(3.0, 600.0 / span))
        return self.to_dict()

    def attention_transfer(self, scene: SceneGraph, to_id: str, weight: float = 0.5) -> dict:
        """注意力从当前对象转移到 to_id（相机平滑跟随）。"""
        self.attention = to_id
        return self.follow(scene, to_id, weight=weight)


def attention_sequence(camera: Camera, scene: SceneGraph,
                       script: List[Tuple[float, str]]) -> List[dict]:
    """按事件脚本推进注意力时间线：script=[(weight, node_id), ...]。"""
    out = []
    for weight, nid in script:
        out.append(camera.attention_transfer(scene, nid, weight=weight))
    return out
