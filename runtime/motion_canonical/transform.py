"""Canonical channel -> transform bridge — delegated to :mod:`geometry`.

Motion emits *channel deltas* (dx, dy, scale, rotation, opacity, connect,
emphasis). Turning those into a transform matrix or a world box is geometry's
job, so this module never computes matrix algebra itself.
"""
from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

from geometry import matrix as _matrix

# The canonical channel set (merged from motion_runtime.contracts CHANNELS).
CHANNELS: Tuple[str, ...] = ("dx", "dy", "scale", "rotation",
                             "opacity", "connect", "emphasis")

# Neutral value per channel: the identity delta for that channel.
CHANNEL_NEUTRAL: Dict[str, float] = {
    "dx": 0.0, "dy": 0.0, "scale": 1.0, "rotation": 0.0,
    "opacity": 1.0, "connect": 0.0, "emphasis": 0.0,
}

# Channels that carry spatial meaning (handled by geometry); the rest are
# non-spatial state (opacity / connect / emphasis).
SPATIAL_CHANNELS = ("dx", "dy", "scale", "rotation")


def neutral_channels() -> Dict[str, float]:
    return dict(CHANNEL_NEUTRAL)


def channels_to_matrix(x: float = 0.0, y: float = 0.0, rotation: float = 0.0,
                       scale: float = 1.0, scale_y: Optional[float] = None,
                       channels: Optional[dict] = None):
    """Compose a local ``T @ R @ S`` matrix from a base pose plus channel deltas.

    Delegates to :func:`geometry.matrix.mat_from_parts`.
    """
    ch = channels or {}
    dx = float(ch.get("dx", 0.0))
    dy = float(ch.get("dy", 0.0))
    dscale = float(ch.get("scale", 1.0))
    drot = float(ch.get("rotation", 0.0))
    return _matrix.mat_from_parts(x + dx, y + dy, rotation + drot,
                                  scale * dscale, scale_y)


def world_box(m, w: float, h: float) -> Tuple[float, float, float, float]:
    """Axis-aligned world box of a ``w x h`` box under matrix ``m`` (geometry)."""
    return _matrix.world_box(m, w, h)


def chain_world_matrix(parts: Sequence[Sequence[float]]):
    """Compose a root->leaf chain of ``(x, y, rotation, scale)`` (geometry)."""
    return _matrix.chain_world_matrix(parts)


def apply_opacity(base_opacity: float, channels: Optional[dict]) -> float:
    """Opacity is multiplicative in the channel convention."""
    ch = channels or {}
    return float(base_opacity) * float(ch.get("opacity", 1.0))


def spatial_delta(channels: Optional[dict]) -> dict:
    """Extract only the spatial channel deltas (non-spatial dropped)."""
    ch = channels or {}
    return {k: ch[k] for k in SPATIAL_CHANNELS if k in ch}
