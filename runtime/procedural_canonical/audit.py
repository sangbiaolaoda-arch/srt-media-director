"""audit.py — procedural divergences as measured evidence, not promises.

PROCEDURAL NORMALIZATION · P1
-----------------------------
Two questions, both answerable from code:

  1. **determinism** — does the same seed / same beat always yield the same
     random stream? (A picture claim is only meaningful if the numbers behind it
     are reproducible.)
  2. **single-source-of-truth** — does any producer still hard-code a seed, or
     call ``random.Random(...)`` / ``random.*`` outside this package? Such a call
     is a second, undocumented seed policy.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List

from . import rng

# A literal seed arg, e.g. random.Random(20261003) -- the exact fork we removed.
_HARDCODED_SEED = re.compile(r"random\.Random\(\s*\d")
# Any raw module-level random use outside this package (constructor / helpers).
_RAW_RANDOM = re.compile(r"\brandom\.(?:Random|random|randint|randrange|uniform|"
                         r"choice|choices|shuffle|seed|sample|gauss)\b")


def determinism_probe(reps: int = 3, n: int = 8) -> Dict[str, Any]:
    """Repeatedly sample the default and per-beat streams; report reproducibility."""
    default_streams, beat_streams = [], []
    beat = {"beat_id": "b01", "narration": "注意力被反复打断"}
    for _ in range(reps):
        r = rng.default_rng()
        default_streams.append([r.randint(0, 10 ** 9) for _ in range(n)])
        rb = rng.rng_for_beat(beat)
        beat_streams.append([rb.randint(0, 10 ** 9) for _ in range(n)])
    return {
        "default_reproducible": len({tuple(s) for s in default_streams}) == 1,
        "beat_reproducible": len({tuple(s) for s in beat_streams}) == 1,
        "default_stream": default_streams[0],
        "beat_stream": beat_streams[0],
        "hash_seed_independent": _hash_seed_independent(beat),
    }


def _hash_seed_independent(beat: dict) -> bool:
    """stable_seed must not depend on PYTHONHASHSEED (unlike builtin hash())."""
    import subprocess
    import sys
    code = ("import sys; sys.path.insert(0, %r); "
            "from procedural_canonical import rng; "
            "print(rng.stable_seed(%r))" % (
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                rng.beat_key(beat)))
    outs = set()
    for hs in ("0", "1", "999"):
        env = dict(os.environ, PYTHONHASHSEED=hs)
        try:
            out = subprocess.run([sys.executable, "-c", code],
                                 capture_output=True, text=True, timeout=60, env=env)
            outs.add(out.stdout.strip())
        except Exception as exc:  # pragma: no cover
            return False
    return len(outs) == 1


def seed_sources(runtime_dir: str = None) -> List[Dict[str, Any]]:
    """Static scan: ``Random(<literal>)`` or raw ``random.*`` outside this package.

    Empty list = every seed flows through :mod:`procedural_canonical.rng`.
    """
    if runtime_dir is None:
        runtime_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pkg = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
    hits: List[Dict[str, Any]] = []
    for root, _dirs, files in os.walk(runtime_dir):
        if "__pycache__" in root:
            continue
        # This package is the sanctioned home for seed construction.
        if os.path.basename(root) == pkg:
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(root, fn)
            with open(path, encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    if _HARDCODED_SEED.search(line) or _RAW_RANDOM.search(line):
                        hits.append({"file": os.path.relpath(path, runtime_dir),
                                     "line": lineno, "code": line.strip()})
    return hits


def summary() -> Dict[str, Any]:
    hits = seed_sources()
    probe = determinism_probe()
    return {
        "seed_sources_outside_canonical": len(hits),
        "hits": hits,
        "default_reproducible": probe["default_reproducible"],
        "beat_reproducible": probe["beat_reproducible"],
        "hash_seed_independent": probe["hash_seed_independent"],
    }
