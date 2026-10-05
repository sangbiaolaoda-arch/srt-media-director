"""Deterministic serialization & normalization (Phase 0).

Two jobs:

1. **Canonical bytes** so the same world state always yields the same hash.
   Runtime determinism is a precondition for the validator being meaningful:
   if the Runtime is not deterministic, "the runtime produced X" is not a
   falsifiable claim.

2. **Constraint-set normalization** so SPEC comparison between the
   human-authored ``expected_semantic`` and the contract-derived expectation is
   order-independent and shape-independent.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, List, Set

# Bump when the canonicalization scheme changes; hashes are only comparable
# within one CANON_VERSION.
CANON_VERSION = "1"


def canonical_json(obj: Any) -> str:
    """Stable JSON: sorted keys, no insignificant whitespace, UTF-8 safe."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def world_state_hash(ws_dict: Dict[str, Any]) -> str:
    """Short, stable hash of a world-state dict (for provenance/reproducibility)."""
    payload = "%s|%s" % (CANON_VERSION, canonical_json(ws_dict))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def norm_constraint(c: Dict[str, Any]) -> str:
    """A stable, comparable key for one *hard* constraint.

    Raises on an unknown ``kind`` so a typo in a contract cannot silently
    become an unenforced no-op.
    """
    kind = c["kind"]
    if kind == "relation_direction":
        return "relation_direction|%s|%s|%s" % (
            c["relation_type"], c["source"], c["target"])
    if kind == "temporal_precedence":
        return "temporal_precedence|%s|%s" % (c["before"], c["after"])
    if kind == "final_focus":
        return "final_focus|%s" % (c["object"],)
    raise ValueError("unknown hard-constraint kind: %r" % (kind,))


def norm_constraint_set(cs: Iterable[Dict[str, Any]]) -> Set[str]:
    return {norm_constraint(c) for c in cs}


def norm_staging(c: Dict[str, Any]) -> str:
    kind = c["kind"]
    if kind == "phase_sequence":
        return "phase_sequence|%s|%s|%s|%s" % (
            c["relation_type"], c["source"], c["target"], ">".join(c["sequence"]))
    raise ValueError("unknown soft-constraint kind: %r" % (kind,))


def norm_staging_set(cs: Iterable[Dict[str, Any]]) -> Set[str]:
    return {norm_staging(c) for c in cs}


def load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
