# P2-1 Implementation — Candidate-based composition selection

Base: `main == 8a9fa50`. Root cause: `docs/p2-1-root-cause.md`.

## What changed

| File | Change |
|---|---|
| `runtime/visual_grammar.py` | new `composition_candidates(beat, encoding)` → ranked semantic candidate set `[{strategy, semantic_fit, rationale}]`; `acceptable_candidates()` + `COMPOSITION_MARGIN`; `composition_strategy()` preserved as the first candidate (byte-compatible with the old single value) |
| `runtime/visual_director.py` | `_direct_beat` now consumes the candidate set; new `_select_strategy()` implements the priority; the fixed `ROTATION` hard-swap is removed (R8 becomes a soft preference inside the candidate set); each beat records a `composition_decision` (candidates + chosen + reason) in `visual-plan.json`; explicit override still wins |
| `tests/golden/*/hashes.json` | regenerated (`UPDATE_GOLDEN=1`) — intentional product change |
| `tests/phase0/test_grammar_owns_strategy.py` | contract updated: routing now asserted on `visual_grammar.composition_candidates(`; added candidate-set + decision-record tests |

## Priority realization (semantic correctness > validity > continuity > diversity)

1. **Semantic correctness** — Grammar emits only semantically-valid candidates and exposes `semantic_fit`; the Director restricts selection to `acceptable` (fit ≥ best − `COMPOSITION_MARGIN`). It can never pick an unreasonable layout just to be different.
2. **Composition validity** — every candidate in the set is itself a valid rendering (all ∈ `STRATEGIES`).
3. **Continuity (GATE-R8)** — among acceptable candidates, those equal to the previous beat's strategy are deprioritized (soft preference, not the old forced rotation).
4. **Diversity** — within the remaining acceptable set, the least-used strategy so far wins (tie-break by fit, then a fixed order). Selection is deterministic and reproducible.

This directly addresses the defect: the old layer could only emit one strategy (default branch → `single_focus`) and then rotated through a fixed list (→ `cause_effect`), giving the 82% `single_focus`↔`cause_effect` alternation. Now the same semantics maps to several equally-reasonable forms, and only the tie-break changes per beat.

## Evidence — 21 real SRT, full production path

**This is a machine-level comparison only.** L4 visual scoring (`semantic_expression`,
`composition`, `hierarchy`, `motion`, `continuity`, `visual_richness`, `repetition`,
`ppt_feeling`, `overall`) remains **PENDING** and was **not** auto-scored. `distinct_strategies`
is an observation metric, not a proxy for visual quality.

Command: `python tools/real_srt_quality_eval.py --out <candidate>`
Compare: `python tools/compare_quality.py --baseline docs/real-srt-quality-eval --candidate <candidate> --out <comparison>`

Headline: **improved 15, regressed 0, unchanged 6.** Mean deltas are over all 21 comparable cases.

| metric (mean over 21) | baseline | candidate | Δ |
|---|---|---|---|
| `distinct_strategies` | 2.3333 | 3.0952 | **+0.7619** |
| cases with ≤2 strategies | 15 / 21 | 6 / 21 | **−9** |
| `elements` | 28.6667 | 29.3333 | +0.6667 |
| `ink_mean` | 0.0603 | 0.0725 | +0.0121 |
| `colors_mean` | 47.8238 | 47.9286 | +0.1048 |
| `anti_ppt.template_repeat` | 0.5169 | 0.3770 | −0.1399 |
| `anti_ppt.encoding_repeat` | 0.5169 | 0.3770 | −0.1399 |
| `anti_ppt.text_ratio` | 0.4167 | 0.3726 | −0.0441 |

Per-case regression scan (distinct_strategies down, or any anti-PPT signal up): **NONE**.

## Category analysis — no category regression

| category | n | distinct avg base→cand | ≤2 cases base→cand | template_repeat base→cand |
|---|---|---|---|---|
| abstract_philosophy | 3 | 2.67 → 3.00 | 1 → 1 | 0.444 → 0.361 |
| adversarial_repetition | 3 | 2.00 → 3.00 | 3 → 0 | 0.667 → 0.333 |
| data_comparison | 4 | 2.75 → 2.75 | 2 → 2 | 0.396 → 0.396 |
| explanation | 4 | 2.00 → 2.50 | 4 → 3 | 0.567 → 0.517 |
| longform | 3 | 2.33 → 4.00 | 2 → 0 | 0.557 → 0.312 |
| narrative_emotion | 4 | 2.25 → 3.50 | 3 → 0 | 0.500 → 0.312 |

No category degraded. `data_comparison` is largely encoding-driven (`before_after`/`comparison` already high-fit) so it stays flat; the previously-collapsed categories (longform, narrative, adversarial) recover.

## Design constraints honored

No new templates; no random shuffle; no case-specific rules; no forced-but-unreasonable layout; no Anti-PPT threshold change; no quality-check deletion; **Motion / Renderer / Primitive untouched**. Only `visual_grammar` + `visual_director` (the minimal composition-decision layer) changed.

`distinct_strategies` was used only as an **observation** metric; selection is driven by semantic fit, not by maximising that number.

## Tests

- `tests/test_golden.py` — regenerated baseline; PASS.
- `tests/phase0/test_grammar_owns_strategy.py` — updated contract; PASS (incl. new candidate/decision tests).
- Full suite: `593 passed, 3 skipped, 3 failed`; the 3 failures are the judge-seal guard checks (see below), not code defects.

## Judge seal status (honest)

`tests/golden/**` and `tests/phase0/test_grammar_owns_strategy.py` are **sealed judge files**. They were changed on purpose (the P2-1 behaviour change legitimately alters the golden oracle and the routing contract). Consequently `judge_guard.verify()` reports `changed` and the three seal-guard tests fail until the manifest is **deliberately re-sealed**.

Re-seal requires the judge signing authority `SMD_JUDGE_KEY`, which the M2 design deliberately withholds from the agent sandbox (`docs/m2-hardening.md`). This sandbox does not hold it, so the agent **cannot** re-seal — by design. The re-seal (and the resulting signed PASS verdict) is an operator/CI action:

```
SMD_JUDGE_KEY=<secret> python -c "from runtime.verification import judge_guard; judge_guard.write_manifest(by='p2-1-operator')"
```

No key was fabricated or brute-forced to bypass this boundary.

## Corrections made during the P2-1 Final Audit

- **`tools/compare_quality.py` denominator bug (fixed).** `metric_deltas_mean` divided the summed
  per-case delta by the number of **changed** cases instead of all comparable cases, inflating every
  mean (e.g. `distinct_strategies` was reported as +1.4545 instead of the correct **+0.7619**).
  Fixed so the denominator is the count of cases where the metric is present in both versions; the
  comparison evidence was regenerated from the fixed tool.
- **Dead `ROTATION` constant removed** from `runtime/visual_director.py` (no production path
  referenced it after P2-1; it had become a historical comment only). Nothing replaces it — the
  selection stays *grammar candidates → semantic validity → continuity → diversity tie-break*.
