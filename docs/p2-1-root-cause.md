# P2-1 Root Cause — Visual Director / Visual Grammar systemic composition repetition

Baseline: `main == 8a9fa50` (unmodified). Evidence: `docs/real-srt-quality-eval/quality-eval-report.json`
(21 real SRT cases, 73 beats).

## Baseline symptom (measured, not guessed)

| metric | value |
|---|---|
| cases with distinct_strategies ≤ 2 | **15 / 21** |
| beats using `single_focus` | 37 / 73 (51%) |
| beats using `cause_effect` | 23 / 73 (32%) |
| `single_focus` + `cause_effect` together | **60 / 73 (82%)** |
| `center_cluster` / `comparison` / `before_after` / `left_to_right_flow` | 6 / 4 / 2 / 1 |

Typical collapsed cases (histogram): `e03-mrna-vaccine {single_focus:4, cause_effect:1}`,
`d02-market-share {single_focus:3, comparison:1}`, `a01-time {single_focus:4}`,
`r02-repetitive-structure {single_focus:5}`.

## The decision chain (exact code path)

`visual_director._direct_beat(beat, …)` (runtime/visual_director.py:429–444):

1. `encoding = decide_encoding(beat, …)`
2. `strategy = visual_grammar.composition_strategy(beat, encoding)`  ← **one value**
3. explicit override wins: `strategy = ov.get("strategy", strategy)`
4. R8 fallback: `if not explicit and strategy == prev_strategy:` → pick the **first**
   entry of a fixed `ROTATION` list that differs from `prev_strategy`.

`visual_grammar.composition_strategy(beat, encoding)` (runtime/visual_grammar.py:141–162):

```
etype = encoding["type"]
if etype in ENCODING_STRATEGY:          # part_to_whole / change_over_time / semantic_color_pair
    return ENCODING_STRATEGY[etype]
role_default = SEMANTIC_DEFAULT.get(role, DEFAULT_STRATEGY)   # DEFAULT_STRATEGY = "single_focus"
if role_default != DEFAULT_STRATEGY:
    return role_default
if any(pair in PRIMARY_RELATIONS):  return "cause_effect"    # answer_to / conclusion
if any(pair in SECONDARY_RELATIONS): return "comparison"     # concession
return DEFAULT_STRATEGY                                     # "single_focus"
```

## Answers to the seven review questions

1. **Where is strategy decided?** In `visual_grammar.composition_strategy`, called by
   `visual_director._direct_beat`. The final value can still be altered by (a) an explicit
   `ov["strategy"]` override and (b) the **R8 fixed `ROTATION`** fallback.

2. **Does `visual_grammar` actually participate?** Yes (P2 delegation is real), but only as a
   **single-value, deterministic returner**. There is no candidate set and no evaluation.

3. **What collapses to `single_focus`?** Every beat whose
   `encoding.type ∉ {part_to_whole, change_over_time, semantic_color_pair}` **and**
   `role ∉ SEMANTIC_DEFAULT` (special roles) **and** whose `semantic_pairs ∉ {answer_to,
   conclusion, concession}` — i.e. the whole **default branch**.

4. **Which roles/relations repeat most?** `explanation` / `turning_point` / `conclusion`
   roles with a static encoding and no relations — they all take the default branch →
   `single_focus`. That is 51% of all beats.

5. **Where do the 15/21 repeats come from?** Two coupled mechanisms, both deterministic:
   - **Grammar mapping collapse** — the default branch funnels most semantics into one value
     (`single_focus`);
   - **Rotation fallback** — when a beat happens to equal the previous one, R8 picks the
     *first* fixed `ROTATION` entry that differs, which is almost always `cause_effect`.
     Together they produce the single_focus↔cause_effect alternation (82%).

6. **Is there a fixed "same semantics → fixed strategy" hard map?** Yes.
   `ENCODING_STRATEGY` and `SEMANTIC_DEFAULT` are fixed one-to-one maps, and the default
   branch is a single constant.

7. **Is repetition caused by the absence of free composition?** Yes. Because the layer can
   only emit **one** strategy per beat, it has no way to express "the same relationship in a
   different but equally valid spatial form". The only variation available is the arbitrary
   R8 rotation — which is not semantically guided.

## Conclusion — the specific defect, not "too few templates"

There are 6 templates and they are not the bottleneck. The defect is **decision structure**:
a **single-value, fixed-mapping chooser** plus an **arbitrary rotation fallback**. The correct
fix is to let the *grammar* own a **semantically-valid candidate set** per relationship, and
let the *director* choose among candidates that are all reasonable — using continuity and
recent-history only as tie-breakers, never to override semantic correctness.

Priority (fixed by design): **semantic correctness > composition validity > continuity > diversity**.

## Non-goals (per P2-1)

- No new composition templates; no random shuffle; no per-case rules; no forcing an
  unreasonable layout to raise diversity; no Anti-PPT threshold change; no touching
  Motion / Renderer / Primitive State.
