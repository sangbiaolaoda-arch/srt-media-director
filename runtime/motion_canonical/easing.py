"""Canonical motion easing — thin delegation to :mod:`timeline.easing`.

Motion owns NO curve math. Every easing spelling used by the motion vocabulary
resolves and evaluates through the timeline single source of truth, so the same
name can never mean two different curves again.
"""
from __future__ import annotations

from typing import Any, Optional

from timeline import easing as _easing

# Canonical default when a spec omits easing: the honest identity curve.
DEFAULT = "linear"

# Motion-visible names are exactly the timeline vocabulary (re-exported).
canonical_names = _easing.canonical_names


def resolve(name: Any):
    """Canonical curve callable for ``name`` (or ``None`` if unknown)."""
    return _easing.resolve(name)


def curve(name: Any):
    """Canonical curve callable; unknown names degrade to linear."""
    return _easing.curve(name)


def evaluate(name: Any, p: float) -> float:
    """Eased value of progress ``p`` in [0, 1] under ``name``."""
    return _easing.evaluate(name, p)


def canonical_name(name: Any) -> Optional[str]:
    """Canonical identifier for ``name`` (normalizes bezier descriptors too)."""
    return _easing.canonical_name(name)


def is_known(name: Any) -> bool:
    return _easing.is_known(name)


def resolve_default(name: Any, default: str = DEFAULT) -> str:
    """Return ``name`` if it resolves, else ``default`` (never raises)."""
    if name is None or (isinstance(name, str) and name.strip() == ""):
        return default
    return canonical_name(name) or default
