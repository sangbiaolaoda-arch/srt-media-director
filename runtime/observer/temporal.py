"""Independent Temporal (ordering) projection (Final Practical Closeout Directive, P2).

The production chain's Temporal layer decides *when* an element is allowed to be
visible. The presence observer only ever sampled inside and after an element's
alive window; the motion, camera and relation observers ask about shape,
magnification and links. None of them noticed the two time-ordering facts a
World-State must guarantee:

* **Onset.** An element must paint *nothing* before its enter cue. Ink before
  ``enter.at`` is a spoilt reveal.
* **Precedence.** A dependency ``D`` named in an element ``E``'s
  ``enter.after`` must already be painting when ``E`` enters. If ``E`` appears
  while ``D`` has no ink, ``E`` references something not yet on screen.

This module is the *expected* side. Like :mod:`observer.projection`,
:mod:`observer.motion`, :mod:`observer.camera` and :mod:`observer.relation`, it
is driven by a declarative, auditable artifact
(``contracts/temporal_projection.v1.json``) and **MUST NOT** import the renderer
or read the player's embedded ``BEATS``.

Pure, browser-free and deterministic: given the upstream entrance lifecycle, it
returns the time-ordering claims the player *should* satisfy.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
CONTRACT_PATH = os.path.join(_ROOT, "contracts", "temporal_projection.v1.json")

_EPS = 1e-9


def contract_path() -> str:
    return os.environ.get("TEMPORAL_PROJECTION_CONTRACT", CONTRACT_PATH)


def load_contract(path: Optional[str] = None) -> Dict[str, Any]:
    with open(path or contract_path(), encoding="utf-8") as f:
        return json.load(f)


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else (hi if v > hi else v)


def onset_time(lc: Dict[str, Any], start: float, end: float,
               contract: Optional[Dict[str, Any]] = None) -> Optional[float]:
    """A probe time *before* this element's enter cue, or ``None`` if the element
    enters at the very start of the beat (no observable pre-roll window)."""
    c = contract or load_contract()
    margin = float((c.get("claims") or {}).get("onset", {}).get("margin_sec", 0.35))
    en = (lc or {}).get("enter") or {}
    if "at" not in en:
        return None
    at = float(en["at"])
    if at - start < margin:
        return None
    return round(clamp(at - margin, start, end), 3)


def precedence_claims(lifecycle: Dict[str, Dict[str, Any]], start: float, end: float,
                      contract: Optional[Dict[str, Any]] = None
                      ) -> List[Dict[str, Any]]:
    """For each ``enter.after`` dependency with a real lead, a claim that the
    dependency is already painting when its dependent enters."""
    c = contract or load_contract()
    cc = (c.get("claims") or {}).get("precedence", {})
    min_lead = float(cc.get("min_lead_sec", 0.4))
    lag = float(cc.get("probe_lag_sec", 0.2))
    out: List[Dict[str, Any]] = []
    for eid, lc in (lifecycle or {}).items():
        en = (lc or {}).get("enter") or {}
        at = en.get("at")
        if at is None:
            continue
        at = float(at)
        for dep in (en.get("after") or []):
            dlc = (lifecycle or {}).get(dep)
            if not dlc:
                continue
            den = (dlc or {}).get("enter") or {}
            if "at" not in den:
                continue
            lead = at - float(den["at"])
            if lead < min_lead - _EPS:
                continue
            t = clamp(at + lag, start, min(end, at + 0.5))
            out.append({"dep": dep, "dependent": eid, "t": round(t, 3), "lead": round(lead, 3)})
    return out


def observable(lifecycle: Dict[str, Any],
               contract: Optional[Dict[str, Any]] = None) -> bool:
    """Whether any time-ordering claim can be formed for this beat."""
    c = contract or load_contract()
    if not lifecycle:
        return False
    has_enter = any(((lc or {}).get("enter") or {}).get("at") is not None
                    for lc in lifecycle.values())
    return bool(has_enter)
