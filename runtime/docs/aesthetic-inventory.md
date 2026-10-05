# Aesthetic Inventory — audit of post-process grading (P2)

Scope: everything in the runtime that applies a *visual finish* to a finished
frame — background gradient, radial vignette, film grain, letterbox bars, and
the luminance metrics the observer uses to judge them. Baseline: commit
`652c843` (Procedural normalization complete, CI green).

Goal: the post-process **grade** must be deterministic and single-sourced. Today
the *theme data* is single-sourced (`common.THEME`), but the grade **code** is
implemented twice — once in PIL for the raster reference, once in canvas JS for
the HTML player — and the two use different falloff models. A "cinematic look"
claim needs one implementation both surfaces share.

---

## 1. Findings — where grading lives

| Area | File | What it does | Reads from |
|------|------|--------------|------------|
| Theme data | `runtime/common.py` | `THEME` dict (bg_top/bottom, vignette, grain, letterbox) | — single source |
| Raster grade | `runtime/raster_renderer.py` | `_theme_bg` vertical gradient, `_vignette_mask` radial mask, `_grain_tile` seeded tiles, `_apply_grade` (vignette→grain→letterbox), `ink_stats` bar | `THEME`, `PALETTES` |
| Player grade | `runtime/html_adapter.py` | `drawBG` linear gradient, `VIG=createRadialGradient(...)`, `BAR=Math.round(H*THEME.letterbox)` in JS | `THEME` (injected via JSON) |
| Observer metrics | `runtime/observer/pixel.py` | `_luma`, region mean/variance, background luma, fingerprint | own (independent) |

**Not grade (out of scope):** `observer/pixel.py` luminance metrics — the observer
must stay independent of the producer (it is the *measurement*, not the *look*);
`entrance_planner`/`motion_canonical` timing.

---

## 2. Divergences found

### D1 — the vignette has **two different falloff models**
```
raster_renderer._vignette_mask:  value = 255 * strength * d²      (d = dist/half-diagonal, d² model, no inner radius)
html_adapter (JS):               createRadialGradient(cx,cy, r*0.45, cx,cy, r)  (linear falloff starting at 0.45 of r)
```
"Same vignette", two shapes. If either is tuned, the raster reference and the
HTML player diverge. **Severity: material.**

### D2 — the vignette **inner ratio `0.45` is hardcoded in the JS only**
`...r*0.45...` appears once, in the player; the PIL path has no equivalent
parameter. A magic number owned by one surface. **Severity: minor.**

### D3 — the **letterbox** formula is written twice
`int(round(H * THEME["letterbox"]))` (PIL) and `Math.round(H*THEME.letterbox)`
(JS) — same today by inspection, but nothing keeps them equal. **Severity: minor.**

### D4 — no grade contract / gate
Nothing fails when a renderer hardcodes a grade literal instead of reading the
canonical spec. **Severity: material** (regressions are silent).

---

## 3. Normalization target

New package `runtime/aesthetic_canonical/` (stdlib-only leaf; PIL used lazily):

| Module | Owns |
|--------|------|
| `grade.py` | `VIGNETTE_INNER_RATIO`, `vignette_strength/letterbox_px/grain_strength/gradient_stops`, `vignette_falloff`, `vignette_mask_pil`, `js_grade_literals` |
| `audit.py` | `grade_consumers()`, `hardcoded_grade_literals()`, `divergence()` |
| `__init__.py` | boundary guard |

**One model:** the canonical vignette is a normalized falloff that is already 0
inside `VIGNETTE_INNER_RATIO*r_max` and rises linearly to `strength` at `r_max`
— i.e. the JS model. PIL is refactored to the same model. Because every current
theme has `vignette = 0.0` and `letterbox = 0.0`, the rendered output is
unchanged; this removes the duplicate model without touching pixels.

**Boundary rule:** the package must not import a renderer or the observer; it
takes the theme mapping as an argument. The observer keeps its own `_luma`.

---

## 4. Migration map (behaviour-preserving)

| # | From | To | Invariant |
|---|------|----|-----------|
| A1 | `raster_renderer._vignette_mask` body | `aesthetic_canonical.grade.vignette_mask_pil(320,180,THEME)` + resize | identical mask (strength=0 → all-zero either way) |
| A2 | `raster_renderer` letterbox `int(round(H*THEME["letterbox"]))` | `grade.letterbox_px(H, THEME)` | identical int |
| A3 | `raster_renderer` grain blend `THEME["grain"]/255.0` | `grade.grain_strength(THEME)/255.0` | identical float |
| A4 | `html_adapter` JS `r*0.45` | interpolate `grade.VIGNETTE_INNER_RATIO` | identical JS literal |
| A5 | `html_adapter` JS `Math.round(H*THEME.letterbox)` | keep expression; audit-verified against `grade.letterbox_px` | identical |

### Deliberately **not** migrated
* `raster_renderer._theme_bg` uses `PALETTES` (per-beat emotion palettes), the JS
  uses `THEME.bg_top/bottom`. These are intentionally different surfaces (raster
  mood palettes vs. flat player background); unifying them is a product decision,
  not a dedup. Tracked, not silently changed.
* `observer/pixel.py` luminance — the observer stays independent.

---

## 5. Self-proof

* `tests/phase0/test_aesthetic_canonical.py` — falloff monotonicity/zero-inside-inner,
  letterbox parity, mask shape, boundary guard.
* `runtime/self_test.py` gate 25 — canonical package importable, both renderers
  consume it, no hardcoded grade literal remains.
* `contracts/aesthetic_semantics.v1.json` — boundary + map.
