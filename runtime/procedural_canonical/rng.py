"""rng.py — the single source of truth for *deterministic randomness*.

PROCEDURAL NORMALIZATION · P1
-----------------------------
Procedural content (grain tiles, decor scatter, motif placement) must be
reproducible. Before this module the runtime had TWO truths for "what seed does
this frame use":

  * ``raster_renderer._grain_tile``       ``random.Random(20261003)``
  * ``visual_director._decor`` (default)  ``random.Random(20261003)``
  * ``visual_director._seed_for(beat)``   ``int(md5(beat_id|narration)[:8], 16)``

If the two ``20261003`` copies ever diverge, the L3 raster probe and the HTML
player render different pictures while both still claim to be deterministic.
This module owns exactly one policy:

  * the video-level default seed (``DEFAULT_SEED``);
  * a stable text->seed derivation (``stable_seed``) that is independent of
    ``PYTHONHASHSEED`` (builtin ``hash()`` is NOT used);
  * the per-beat seed recipe (``beat_key`` / ``rng_for_beat``).

It must NOT do layout, geometry or drawing -- those belong to ``layout`` /
``geometry`` / ``primitives``. Seeds only.
"""
from __future__ import annotations

import hashlib
import random

# The video-level seed. Was hard-coded in two producers; now single-sourced here.
DEFAULT_SEED = 20261003


def stable_seed(text) -> int:
    """Deterministic 32-bit seed from text, stable across processes / machines.

    Uses md5 -- not builtin ``hash()``, which is salted by ``PYTHONHASHSEED`` and
    therefore not reproducible across processes. Keeps the exact recipe the
    runtime already used for per-beat seeds so migration is behaviour-preserving.
    """
    return int(hashlib.md5(str(text).encode("utf-8")).hexdigest()[:8], 16)


def default_rng() -> random.Random:
    """Video-level RNG. Same seed everywhere -> same grain / decor baseline."""
    return random.Random(DEFAULT_SEED)


def rng_for_key(key) -> random.Random:
    """RNG from an arbitrary stable identity string."""
    return random.Random(stable_seed(key))


def beat_key(beat) -> str:
    """Stable identity string for a beat (``beat_id`` + ``narration``)."""
    return "%s|%s" % (beat.get("beat_id", ""), beat.get("narration", ""))


def rng_for_beat(beat) -> random.Random:
    """Per-beat RNG: the same beat always yields the same decor choices."""
    return random.Random(stable_seed(beat_key(beat)))
