"""Canonical 2D affine transform vocabulary (code-capability upgrade).

The project already composes transforms, but the *same* "world transform" was
computed by more than one subsystem with different math:

* ``motion_runtime.scene``  -- 6-tuple affine ``(a,b,c,d,e,f)``; ``world_box``
  maps the four corners of a node, so **rotation is honoured**.
* ``scene.scene_graph``     -- scalar inheritance; ``world_box`` is
  ``[ox, oy, w*s, h*s]`` and ``world_origin`` offsets by *parent scale only*,
  so **rotation is ignored** (``world_rotation`` is computed but never applied).
* ``scene.state_graph``     -- records transform attributes but computes no
  geometry of its own.

So when a node is rotated, the two scene systems disagree about its world box --
exactly the case that makes local coordinate systems and nested scenes useful.
This module is the single source of truth for that algebra::

    local = T(x, y) @ R(rotation) @ S(scale)
    world = parent_world @ local
    box   = axis-aligned bounds of the 4 transformed corners

Pure, browser-free, deterministic, no project imports.
"""
from __future__ import annotations

import json
import math
import os
from typing import Optional, Tuple

Mat = Tuple[float, float, float, float, float, float]  # a,b,c,d,e,f

IDENTITY: Mat = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
CONTRACT_PATH = os.path.join(_ROOT, "contracts", "transform_vocabulary.v1.json")


# ------------------------------------------------------------------ algebra


def mat_mul(m1: Mat, m2: Mat) -> Mat:
    """World composition ``m1 @ m2`` (apply ``m2`` first, then ``m1``)."""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (a1 * a2 + c1 * b2,
            b1 * a2 + d1 * b2,
            a1 * c2 + c1 * d2,
            b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1,
            b1 * e2 + d1 * f2 + f1)


def mat_apply(m: Mat, x: float, y: float) -> Tuple[float, float]:
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def mat_translate(dx: float, dy: float) -> Mat:
    return (1.0, 0.0, 0.0, 1.0, float(dx), float(dy))


def mat_rotate(deg: float) -> Mat:
    rad = math.radians(deg)
    cos, sin = math.cos(rad), math.sin(rad)
    return (cos, sin, -sin, cos, 0.0, 0.0)


def mat_scale(kx: float, ky: Optional[float] = None) -> Mat:
    if ky is None:
        ky = kx
    return (float(kx), 0.0, 0.0, float(ky), 0.0, 0.0)


def mat_from_parts(x: float = 0.0, y: float = 0.0, rotation: float = 0.0,
                   scale: float = 1.0, scale_y: Optional[float] = None) -> Mat:
    """``local = T(x, y) @ R(rotation) @ S(scale)`` (uniform scale by default)."""
    if scale_y is None:
        scale_y = scale
    rad = math.radians(rotation)
    cos, sin = math.cos(rad), math.sin(rad)
    return (cos * scale, sin * scale, -sin * scale_y, cos * scale_y,
            float(x), float(y))


def mat_invert(m: Mat) -> Mat:
    a, b, c, d, e, f = m
    det = a * d - b * c
    if det == 0.0:
        raise ZeroDivisionError("singular transform cannot be inverted")
    ia = d / det
    ib = -b / det
    ic = -c / det
    id_ = a / det
    ie = (c * f - d * e) / det
    if_ = (b * e - a * f) / det
    return (ia, ib, ic, id_, ie, if_)


def compose(*mats: Mat) -> Mat:
    """Left-to-right composition: ``compose(A, B, C)`` == ``A @ B @ C``."""
    m = IDENTITY
    for nxt in mats:
        m = mat_mul(m, nxt)
    return m


def world_box(m: Mat, w: float, h: float) -> Tuple[float, float, float, float]:
    """Axis-aligned bounds ``(x, y, w, h)`` of a ``w x h`` box under ``m``."""
    pts = [mat_apply(m, 0.0, 0.0), mat_apply(m, w, 0.0),
           mat_apply(m, w, h), mat_apply(m, 0.0, h)]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def chain_world_matrix(parts) -> Mat:
    """Compose a root->leaf chain of ``(x, y, rotation, scale)`` parts."""
    m = IDENTITY
    for x, y, rotation, scale in parts:
        m = mat_mul(m, mat_from_parts(x, y, rotation, scale))
    return m


def load_contract(path: Optional[str] = None) -> dict:
    with open(path or CONTRACT_PATH, encoding="utf-8") as f:
        return json.load(f)
