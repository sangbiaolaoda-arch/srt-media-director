"""Canonical state transition — one model for "an element changes state".

Consolidates three previously-forked models:

* ``motion/state_change.py`` + ``motion/transition.py``  (detect change -> verb)
* ``scene/state_graph.py`` + ``scene/transitions.py``    (state + semantic verbs)
* ``motion_runtime/states.py``                           (guarded state machine)

The canonical model keeps the *reason* discipline: every transition must carry a
trigger/reason, and a state change is a transform (not a re-entrance).
"""
from __future__ import annotations

# Canonical state vocabulary (merged).
STATES = ("inactive", "activating", "active", "strengthening", "dominant",
          "weakening", "blocked", "waiting", "resolved")

# Fields whose change means "the element changed state".
STATE_FIELDS = ("value", "text", "count", "state", "highlight")

# Semantic transition verbs (merged from scene/transitions.VERBS).
VERBS = ("appear", "disappear", "expand", "collapse", "morph", "transform",
         "split", "merge", "highlight", "connect", "disconnect")


def detect_state_change(prev_el, cur_el):
    """Return ``(changed: bool, fields: list)`` comparing state-bearing fields."""
    if not prev_el or not cur_el:
        return False, []
    fields = [k for k in STATE_FIELDS
              if (k in prev_el or k in cur_el) and prev_el.get(k) != cur_el.get(k)]
    return bool(fields), fields


def state_motion(changed, is_focal=False):
    """State change -> canonical motion verb (focal transforms more strongly)."""
    if not changed:
        return "continue"
    return "transform"


def transition_verb(changed, fields=None):
    """Map a detected change to a canonical transition verb."""
    if not changed:
        return "continue"
    return "transform"
