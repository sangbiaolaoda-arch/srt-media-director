"""Canonical PRIMITIVE STATE vocabulary — single source of truth.

The element-level state animations that the entrance planner emits and both
renderers implement. Contract: ``contracts/primitive_states.v1.json``.
Enforced by ``tests/phase0/test_primitive_states.py``.

This module owns *only* the state-animation names. Shapes live in
``primitives.catalog``; enter/exit motion lives in ``motion_canonical``.
"""

# Per-element state animations (carried on interaction events, read per target).
STATE_ACTIONS = ("draw", "chart_fill", "bars_grow", "color_wash", "pulse")

# Beat-level pacing markers (type == "resolve", empty targets).
RESOLVE_ACTIONS = ("settle",)

ALL_ACTIONS = STATE_ACTIONS + RESOLVE_ACTIONS


def is_state_action(name):
    """True when ``name`` is a per-element state animation."""
    return name in STATE_ACTIONS


def is_known_action(name):
    """True when ``name`` is any declared primitive-state action."""
    return name in ALL_ACTIONS
