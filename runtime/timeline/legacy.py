"""Legacy easing adapters — behavior-preserving migration onto the canonical core.

Before migration, easing curve math was duplicated in several subsystems and the
*same name meant different curves*:

* ``motion.render._ease(name, p)``  -- linear / cubic / cubic / smoothstep
* ``raster_renderer._ease(p)``      -- smoothstep
* ``observer.motion.ease(p)``       -- smoothstep
* ``motion_runtime.contracts``      -- full Penner table (matched canonical)

This module removes the duplicated curve math: each subsystem's easing function
now *delegates* here, and every curve is evaluated by :mod:`timeline.easing`, the
single source of truth. The adapters are **byte-parity** with the old
implementations (same canonical curve for each legacy spelling), so golden and
pixel regression stay green:

* ``motion.render`` ``"ease-out"`` -> canonical ``easeOutCubic`` (== old 1-(1-p)^3)
* ``motion.render`` ``"ease-in"``  -> canonical ``easeInCubic``  (== old p^3)
* ``motion.render`` default/other  -> canonical ``smoothstep``   (== old p*p*(3-2p))
* ``raster_renderer`` / ``observer`` default -> canonical ``smoothstep``

The separate, deliberate *semantic* fixes (e.g. honouring a ``cubic-bezier``
string instead of ignoring it) are NOT applied here — they would change pixels
and are tracked by :func:`timeline.audit.diverging` for a reviewed change.
"""
from __future__ import annotations

from typing import Any

from . import easing

# Legacy spelling -> canonical curve. Values chosen to reproduce the OLD output
# exactly (see module docstring), NOT to "correct" it.
MOTION_RENDER_MAP = {
    "linear": "linear",
    "ease-out": "easeOutCubic",
    "ease-in": "easeInCubic",
    "ease-in-out": "smoothstep",
    "smoothstep": "smoothstep",
}
MOTION_RENDER_DEFAULT = "smoothstep"

SMOOTHSTEP = "smoothstep"


def canonical_for_legacy(name: Any, mapping: dict = None,
                         default: str = MOTION_RENDER_DEFAULT) -> str:
    """Canonical curve name that reproduces a legacy easing spelling."""
    m = mapping if mapping is not None else MOTION_RENDER_MAP
    if name is None:
        return default
    return m.get(str(name).strip(), default)


def render_legacy_ease(name: Any, p: float) -> float:
    """``motion.render._ease`` replacement (byte-parity, canonical-backed)."""
    return easing.evaluate(canonical_for_legacy(name, MOTION_RENDER_MAP,
                                                MOTION_RENDER_DEFAULT), p)


def raster_ease(p: float) -> float:
    """``raster_renderer._ease`` replacement (byte-parity: smoothstep)."""
    return easing.evaluate(SMOOTHSTEP, p)


def observer_ease(p: float) -> float:
    """``observer.motion.ease`` replacement (byte-parity: smoothstep)."""
    return easing.evaluate(SMOOTHSTEP, p)
