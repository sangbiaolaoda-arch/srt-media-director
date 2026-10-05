"""layout.py — procedural *layout* generators (the geometry half of procedural).

A "layout" is a rule that turns a count into positions, so a scene can
generalize to ``n`` the reference frames never drew (2/4/5 columns, vertical
stacks, regular lattices) instead of pasting hard-coded coordinates. The runtime
used to express these inline: ``ref_frame.cols`` / ``ref_frame.rows`` for slots,
and hand-rolled double loops in ``svg_art`` for dot lattices.

This module owns ONLY the arithmetic of even distribution and regular lattices.
It must not know about colors, fonts, stroke roles or drawing -- those are
``primitives`` / ``ref_frame`` concerns.

Behaviour-preservation
----------------------
``slots`` / ``stacks`` reproduce ``ref_frame.cols`` / ``ref_frame.rows`` exactly
(``cols(3)`` -> x = [48, 265, 482], w = 150). ``lattice`` reproduces the
row-major dot loops (``for r in rows: for c in cols``) so migrated SVG strings
stay byte-identical.
"""
from __future__ import annotations

from typing import List, Tuple


def slots(n: int, x0: float, total: float, gap: float) -> List[Tuple[float, float]]:
    """n equal-width columns: ``[(x, w), ...]`` with ``x_i = x0 + i*(w+gap)``.

    ``w = (total - gap*(n-1)) / n`` so that the first column starts at ``x0`` and
    the last ends at ``x0 + total``. Reproduces the reference frame's three-node
    row (``n=3`` -> w=150, x=[48,265,482]) and generalizes to any n.
    """
    if n < 1:
        raise ValueError("slots(n>=1)")
    w = (total - gap * (n - 1)) / n
    if w <= 0:
        raise ValueError("slots: n too large, width <= 0")
    return [(x0 + i * (w + gap), w) for i in range(n)]


def stacks(n: int, y0: float, total: float, gap: float) -> List[Tuple[float, float]]:
    """n equal-height rows: ``[(y, h), ...]`` (vertical twin of :func:`slots`)."""
    if n < 1:
        raise ValueError("stacks(n>=1)")
    h = (total - gap * (n - 1)) / n
    if h <= 0:
        raise ValueError("stacks: n too large, height <= 0")
    return [(y0 + i * (h + gap), h) for i in range(n)]


def lattice(n_cols: int, n_rows: int, x0: float, y0: float,
            dx: float, dy: float) -> List[Tuple[float, float]]:
    """Regular grid points, row-major: ``for r in range(n_rows) for c in range(n_cols)``.

    Reproduces the dot-lattice loops the decor generators hand-rolled (dot_grid /
    halftone / plus_field). Order is fixed row-major so generated SVG strings stay
    byte-identical after migration.
    """
    if n_cols < 1 or n_rows < 1:
        raise ValueError("lattice(n_cols>=1, n_rows>=1)")
    return [(x0 + c * dx, y0 + r * dy)
            for r in range(n_rows) for c in range(n_cols)]


def lattice_idx(n_cols: int, n_rows: int, x0: float, y0: float,
                dx: float, dy: float) -> List[Tuple[int, int, float, float]]:
    """Row-major lattice yielding ``(c, r, x, y)`` so callers can key off the index.

    Needed by decor whose *radius / size* depends on the cell index (e.g. the
    fading halftone dots: ``r = 3.2 - 0.5 * (c + r)``). Order is identical to
    :func:`lattice`, so migrated SVG strings stay byte-identical.
    """
    if n_cols < 1 or n_rows < 1:
        raise ValueError("lattice_idx(n_cols>=1, n_rows>=1)")
    return [(c, r, x0 + c * dx, y0 + r * dy)
            for r in range(n_rows) for c in range(n_cols)]
