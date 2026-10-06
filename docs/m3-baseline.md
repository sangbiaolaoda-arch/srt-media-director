# M3 — Real-Content Quality Improvement: baseline & findings

Base commit: `eb9674b`. This stage does **not** extend `runtime/verification/*`; it
points the (already built) real-content mechanism at *visual quality*.

## P0 — Production bug fixed from real content (`d01-gdp`)

**Symptom.** `tests/corpus/real-content/data_comparison/d01-gdp.srt` failed the
production path: `composition_planner` raised
`LayoutIntentIncomplete: text '×0.308824' (230x44) does not fit region 'delta' (179x…)`.

**Root cause (generic, not case-specific).** The `before_after` delta annotation is
produced in `visual_director.py` as `"×%g" % (after / before)`. `%g` uses 6
significant digits, so `0.3088235…` became the **8-glyph** label `×0.308824`, which
measures wider (230px) than the fixed `delta` region (179px) at `display_small` and
trips the (correct) Content-Footprint preflight. The same unbounded `"%g%"`
pattern existed on the `number` annotation and in `raster_renderer`'s numeric label.

**Fix (generic).** Added `common.format_compact_num(x)` — a bounded, human-legible
number formatter — and applied it at every on-canvas numeric-label producer
(`visual_director` number/delta, `raster_renderer` value). `0.3088235… → 0.31`,
`99.99 → 100`, `6.8 → 6.8`. No case bypass, no region enlargement, no silent font
shrink, no gate disabled, no element deleted.

**Regression.** `tests/phase0/test_label_bounds_regression.py` (formatter bounds,
delta-label-fits-region, and the exact corpus case renders PASS).

**Result:** `d01-gdp` PASS; **21/21** corpus cases pass the production path with no
new regressions.

## P0 — M3 baseline

`tools/real_srt_quality_eval.py` runs all 21 fixed cases (6 categories) through the
full production path and writes, per case: production status, render/contact sheet,
machine metrics (ink/colour/beats/elements/strategies/validator+l4) **and** the nine
L4 dimensions (all PENDING) plus the anti-PPT signals. Baseline artifact:
`docs/real-srt-quality-eval/` (contact sheets + `quality-eval-report.json`).

## Problem classification (研发层 requirement)

Real-content findings are classified, not just logged:

| Finding | Cases | Class | Action |
|---|---|---|---|
| Unbounded `%g` numeric label overflows fixed region | 1 (`d01-gdp`) | **layout bug** (generator) | fixed generically (`format_compact_num`) |
| ≤2 distinct composition strategies | 15 / 21 | **director weakness** (systemic) | root-cause fix in director/grammar (next) |
| 100 % of entering motions are plain `fade` | ~half of cases | **motion weakness** (systemic) | strengthen primitive state/transition |
| High text-dominant beats / template repeat | several | **quality (anti-PPT signal)** | L4 review + director diversity |

Rule for the next iterations: **one problem seen many times → fix the generating
mechanism, not the cases.** The 15/21 strategy repetition and the dominant-`fade`
motion are *systemic*, so they are addressed in the director/grammar and primitive
state layers (P2), never with per-case rules.

## P1 — Version comparison (baseline → candidate)

`tools/compare_quality.py` compares two `quality-eval-report.json` files and emits
`comparison/{machine-diff.json, score-diff.json, contact-sheet-before.png,
contact-sheet-after.png, summary.md}`. It answers, per case and per metric: which
cases improved, which regressed, which metrics moved, whether anything got better
locally but worse overall, and whether the effect is confined to a single category.
`score-diff` stays non-comparable until L4 scores stop being PENDING. "It feels
better" is never a valid sole conclusion.

## P1 — Anti-PPT as observable metrics

`_anti_ppt()` in the eval harness turns `ppt_feeling` into countable auxiliary
signals: text ratio, text-dominant beats, template repeat, max consecutive same
strategy, decoration ratio, fade-only motion ratio, static-beat ratio, encoding
repeat. These are **auxiliary evidence only** — a high value is not automatically
"PPT"; final judgement stays with L4 (never a hard threshold verdict).

## Honest status

- Engineering: **21/21** stable through the production path.
- Regression: full pytest green; golden unchanged.
- Quality: baseline captured; baseline→candidate comparison tooling ready.
- Human layer: 21-case L4 scaffold generated (all PENDING) — real scores still to be
  filled by human/agent review of the contact sheets. Not machine-faked.
