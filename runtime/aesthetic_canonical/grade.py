"""grade.py — the single source of truth for the post-process *look*.

AESTHETIC NORMALIZATION · P2
-----------------------------
The grade is the ordered finish applied to a finished frame:
``background gradient -> radial vignette -> film grain -> letterbox``.

Before this module the grade existed twice:

  * ``raster_renderer._vignette_mask``  value = 255 * strength * d²   (d² model)
  * ``html_adapter`` (JS)               createRadialGradient(..., r*0.45, ..., r)
  * ``... letterbox``                    int(round(H*letterbox)) twice

Two falloff shapes and a magic ``0.45`` owned only by the player. This module
owns ONE model and the parameters that feed it. The canonical vignette is the
player's model -- zero inside ``VIGNETTE_INNER_RATIO`` of the half-diagonal,
rising linearly to ``strength`` at the edge -- and the PIL mask now reproduces
it, so the two surfaces cannot drift.

It takes the theme mapping as an argument (no import of ``common`` / renderer),
so it stays a stdlib/PIL leaf.
"""
from __future__ import annotations

import math

# Canonical vignette inner ratio: fraction of the half-diagonal that stays clear.
VIGNETTE_INNER_RATIO = 0.45


# ---------------------------------------------------------------- parameters
def vignette_strength(theme: dict) -> float:
    return float(theme.get("vignette", 0.0))


def grain_strength(theme: dict) -> float:
    return float(theme.get("grain", 0.0))


def letterbox_frac(theme: dict) -> float:
    return float(theme.get("letterbox", 0.0))


def letterbox_px(height: int, theme: dict) -> int:
    """Top/bottom bar height in pixels. Single definition for both surfaces."""
    return int(round(height * letterbox_frac(theme)))


def gradient_stops(theme: dict):
    """(top, bottom) background colors for the flat player gradient."""
    return theme.get("bg_top"), theme.get("bg_bottom")


# ---------------------------------------------------------------- vignette model
def vignette_falloff(d_over_rmax: float, inner: float = VIGNETTE_INNER_RATIO) -> float:
    """Normalized vignette alpha factor in [0, 1].

    0 inside ``inner`` (centre stays clear), rising linearly to 1 at the edge.
    This is the model the canvas player already used (radial gradient starting at
    ``inner * r_max``); the PIL mask is aligned to it here.
    """
    if d_over_rmax <= inner:
        return 0.0
    return min(1.0, (d_over_rmax - inner) / (1.0 - inner))


def vignette_mask_pil(w: int, h: int, theme: dict):
    """L-mode mask where 0 = keep, 255 = darken by full strength.

    Reproduces the player's falloff. At the current ``vignette = 0.0`` theme the
    mask is all-zero, so this refactor does not change a single pixel.
    """
    from PIL import Image

    m = Image.new("L", (w, h), 0)
    cx, cy = w / 2.0, h / 2.0
    rmax = math.hypot(cx, cy)
    strength = vignette_strength(theme)
    if strength <= 0.0:
        return m
    for y in range(h):
        for x in range(w):
            t = vignette_falloff(math.hypot(x - cx, y - cy) / rmax)
            m.putpixel((x, y), int(255 * strength * t))
    return m


# ---------------------------------------------------------------- JS mirror
def js_grade_literals(theme: dict) -> dict:
    """The literals the canvas player must contain, so drift is auditable.

    The player builds ``createRadialGradient(cx,cy, r*inner, cx,cy, r)`` with a
    stop at ``rgba(0,0,0,strength)`` and letterbox ``Math.round(H*letterbox)``.
    """
    return {
        "inner_ratio": VIGNETTE_INNER_RATIO,
        "vignette": vignette_strength(theme),
        "letterbox": letterbox_frac(theme),
    }
