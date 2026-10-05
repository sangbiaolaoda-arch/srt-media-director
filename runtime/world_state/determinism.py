"""Runtime determinism calibration (Falsifiability First v4, step 6).

Before any validator verdict can be trusted, "the runtime produced X" must be
a *reproducible* claim. This module measures whether repeated runs of the
runtime yield byte-identical canonical world states.

It also checks *canonicalization invariance*: the hash must not depend on JSON
key order or on ``PYTHONHASHSEED`` (set iteration order), otherwise the hash
would be a hidden source of non-determinism.
"""
from __future__ import annotations

import subprocess
import sys
from typing import Any, Dict, List, Optional

from . import compiler, serializer

# N repetitions. v4 asks for enough reps that p99-style claims are meaningful;
# calving the hashes is cheap, so 1000 is the default.
DEFAULT_REPS = 1000


def calibrate(anchor: Dict[str, Any], *,
              contract: Optional[Dict[str, Any]] = None,
              reps: int = DEFAULT_REPS,
              **faults: Any) -> Dict[str, Any]:
    """Run the runtime ``reps`` times and report hash uniqueness."""
    hashes: List[str] = []
    for _ in range(reps):
        ws = compiler.compile_world_state(anchor, contract=contract, **faults)
        hashes.append(serializer.world_state_hash(ws.to_dict()))
    unique: List[str] = sorted(set(hashes))
    return {
        "reps": reps,
        "unique_hashes": unique,
        "deterministic": len(unique) == 1,
    }


def canonicalization_invariant(anchor: Dict[str, Any], *,
                               contract: Optional[Dict[str, Any]] = None) -> bool:
    """Hash must be invariant to top-level key ordering."""
    ws = compiler.compile_world_state(anchor, contract=contract).to_dict()
    reordered = {k: ws[k] for k in reversed(list(ws.keys()))}
    return serializer.world_state_hash(ws) == serializer.world_state_hash(reordered)


def cross_process_hash(anchor_path: str, *, seed: str) -> str:
    """Compute the world-state hash in a *fresh* interpreter with a given
    ``PYTHONHASHSEED``. Used to prove the hash does not depend on set order.
    """
    code = (
        "import json,sys;"
        "sys.path.insert(0, 'runtime');"
        "from world_state import compiler, serializer;"
        "a=json.load(open(sys.argv[1], encoding='utf-8'));"
        "ws=compiler.compile_world_state(a);"
        "print(serializer.world_state_hash(ws.to_dict()))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code, anchor_path],
        capture_output=True, text=True, check=True,
        env={**__import__("os").environ, "PYTHONHASHSEED": seed},
        cwd=__import__("os").path.dirname(__import__("os").path.dirname(
            __import__("os").path.abspath(__file__))),
    )
    return out.stdout.strip()
