"""Entailment contracts — audited, versioned, external to the runtime.

Each contract maps one Anchor predicate to the hard constraints a world state
must satisfy. Contracts are plain JSON *data* on purpose: they must be
reviewable (and challengeable) outside the runtime that they judge.

Phase 0 ships three predicates:
  * ``causes.v1``   — CAUSES
  * ``follows.v1``  — FOLLOWS
  * ``connects.v1`` — CONNECTS
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))


def load_contract(contract_id: str) -> Dict[str, Any]:
    """Load ``<contract_id>.json`` from this package directory."""
    path = os.path.join(_HERE, contract_id + ".json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def available() -> List[str]:
    return sorted(n[:-5] for n in os.listdir(_HERE) if n.endswith(".json"))


__all__ = ["load_contract", "available"]
