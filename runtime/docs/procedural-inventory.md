# Procedural Inventory — audit of procedural generation (P1)

Scope: everything in the runtime that *generates* content (layout rules,
lattice/loop drawing, seeded randomness) rather than *declaring* it. Baseline:
commit `ddd4ee5` (Motion normalization complete, CI green).

Goal of the normalization: **procedural generation must be deterministic and
single-sourced.** "Seeded, cross-machine reproducible" is a claim the project
already makes (`tests/test_golden.py` docstring); a claim needs exactly one
implementation to audit against.

---

## 1. Findings — where procedural code lives

| Area | File | What it generates | Randomness | Determinism |
|------|------|-------------------|-----------|-------------|
| Layout rules | `runtime/ref_frame.py` | `cols(n)` columns, `rows(n)` rows, `stroke(role)`, `type_scale(name)` | none | pure arithmetic |
| Layout adapter | `runtime/compiler/layout.py` | `solve_slots` / `solve_rows` delegate to `ref_frame` | none | pure |
| Compiler | `runtime/composition_compiler.py` | `slots = R.cols(n)` card row | none | pure |
| Decor generators | `runtime/svg_art.py` | 24 motifs + 17 decor; **lattice-type** decor use hand-rolled double loops (`_dot_grid`, `_halftone`, `_plus_field`) | none | pure (uses `math.sin/cos`, no RNG) |
| Grain tiles | `runtime/raster_renderer.py:74` | 8 film-grain tiles | `random.Random(20261003)` | seeded |
| Decor scatter | `runtime/visual_director.py:261` | ambient decor selection + jitter | `random.Random(20261003)` (default) | seeded |
| Per-beat seed | `runtime/visual_director.py:149` | `_seed_for(beat)` = `int(md5(beat_id\|narration)[:8],16)` | md5 | seeded |

**Not procedural (out of scope):** `primitives/*` (declarative drawing atoms —
owned by `primitive_catalog.v1`), `geometry/*` (space), `timeline/*` (time),
`motion_canonical/*` (motion timing).

---

## 2. Divergences found

### D1 — the video-level seed is hard-coded in **two** producers
```
runtime/raster_renderer.py:74   rnd = random.Random(20261003)
runtime/visual_director.py:261  rng = rng if rng is not None else random.Random(20261003)
```
Two independent copies of `20261003`. If one changes, the L3 raster probe
(`raster_renderer`) and the HTML player (`visual_director` → `svg_art`) render
different pictures while both still claim determinism. **Severity: material.**

### D2 — the per-beat seed recipe is an inline expression
`visual_director._seed_for` recomputes `int(hashlib.md5(...)[:8], 16)` inline; any
other module wanting the same "stable per-beat seed" must copy it. **Severity: minor.**

### D3 — layout arithmetic is only *partly* shared
`ref_frame.cols/rows` hold the "n → slots" rule, but `svg_art`'s lattice decor
re-derives "index → (x, y)" with hand-written `for r ... for c ...` loops. Same
concept (regular distribution), two homes. **Severity: minor.**

### D4 — no determinism contract / gate
There is a determinism *test* for the world-state layer
(`tests/phase0/test_determinism.py`) but **no** machine check that (a) the
video-level seed has a single source, and (b) no producer outside the canonical
package constructs its own RNG. **Severity: material** (regressions are silent).

---

## 3. Normalization target

New package `runtime/procedural_canonical/` (stdlib-only leaf):

| Module | Owns |
|--------|------|
| `rng.py` | `DEFAULT_SEED`, `stable_seed(text)`, `default_rng()`, `beat_key(beat)`, `rng_for_beat(beat)`, `rng_for_key(key)` |
| `layout.py` | `slots(n,x0,total,gap)`, `stacks(n,y0,total,gap)`, `lattice(n_cols,n_rows,x0,y0,dx,dy)` |
| `audit.py` | `determinism_probe()`, `seed_sources()`, `summary()` |
| `__init__.py` | boundary guard (`assert_boundaries` / `boundary_report`) |

**Boundary rule:** `ref_frame` consumes `layout` (it delegates `cols`/`rows`), so
`procedural_canonical` must never import `ref_frame` (cycle) nor any producer —
it stays a stdlib-only leaf. See `boundary_report()`.

---

## 4. Migration map (must be behaviour-preserving)

| # | From | To | Invariant |
|---|------|----|-----------|
| M1 | `ref_frame.cols(n)` body | `layout.slots(n, MARGIN, CONTENT_W, COL_GAP)` | identical floats |
| M2 | `ref_frame.rows(n,y0,total,h_gap)` | `layout.stacks(n, y0, total, h_gap)` | identical floats |
| M3 | `svg_art._dot_grid` loops | `layout.lattice(5,4,10,12,20,25)` | byte-identical SVG |
| M4 | `svg_art._halftone` loops | `layout.lattice(6,5,14,20,12,14)` | byte-identical SVG (radius from index) |
| M5 | `svg_art._plus_field` loops | `layout.lattice(3,3,22,22,28,28)` | byte-identical SVG |
| M6 | `raster_renderer` seed `20261003` | `procedural_canonical.rng.default_rng()` | identical stream |
| M7 | `visual_director._decor` default seed | `procedural_canonical.rng.default_rng()` | identical stream |
| M8 | `visual_director._seed_for(beat)` | `procedural_canonical.rng.stable_seed(beat_key(beat))` | identical int |

### Deliberately **not** migrated
* `_scatter` / `_cross_hatch` / `_spiral` in `svg_art` — not regular lattices
  (hard-coded point list / clipped diagonals / polar spiral). Forcing them into
  `lattice()` would be a semantic lie; they stay as declarative drawing inside
  `svg_art`.
* `raster_renderer` vignette — pure `math.hypot` field, no randomness.

---

## 5. Self-proof

* `tests/phase0/test_procedural_canonical.py` — RNG reproducibility, hash-seed
  independence, layout equivalence with the reference frame, lattice byte-identity.
* `runtime/self_test.py` gate 24 — canonical package importable, no producer
  constructs its own RNG (static scan), determinism probe passes.
* `contracts/procedural_semantics.v1.json` — declares the boundary and the map.
