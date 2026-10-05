"""Canonical progress / time-parameterization — delegated to :mod:`timeline`.

The runtime already fixed time-parameterization as ``timeline.easing.pr``.
Motion does not re-derive easing fractions; it only *uses* them to turn a motion
span into progress values.
"""
from __future__ import annotations

from typing import Any

from timeline import easing as _easing

from . import easing as _easing_reexport  # keep the canonical easing module wired


def progress(t: float, start: float, end: float, easing: Any = "linear") -> float:
    """Eased progress of span ``[start, end]`` at time ``t`` (delegates to timeline)."""
    return _easing.pr(t, start, end, easing)


# Explicit alias so callers can read intent even when the easing is implicit.
pr = progress


def raw_progress(t: float, start: float, end: float) -> float:
    """Linear (un-eased) fraction, clamped to [0, 1]; instantaneous span -> step."""
    if end <= start:
        return 1.0 if t >= end else 0.0
    r = (t - start) / (end - start)
    return 0.0 if r < 0.0 else (1.0 if r > 1.0 else r)


def channel_at(channels: dict, p: float) -> dict:
    """Interpolate a ``{channel: (from, to)}`` table at eased/raw progress ``p``.

    This is pure state-over-time: it never touches easing curves (callers pass an
    already-eased ``p`` when they want easing) and never touches geometry.
    """
    out = {}
    for ch, span in (channels or {}).items():
        if isinstance(span, (tuple, list)) and len(span) == 2:
            frm, to = float(span[0]), float(span[1])
            out[ch] = frm + (to - frm) * p
        else:
            out[ch] = span
    return out
