"""L4 review scaffold — the PREREQUISITE for any future L4 auto-aesthetic.

L4 (semantic / visual aesthetic review) may not be machine-faked (skills/09
VAL-01). Automating L4 requires enough HUMAN-scored data first, which does not
exist yet. This tool produces the machine-generated *scaffold* a human/agent
fills in: the real-content case list, the anti-PPT L4 prompts (skills/10
PPT-L4-1..4), and the contact sheet each case was judged from. Every verdict
starts PENDING; only a human/agent may flip it.

Contract: ``schemas/review-report.schema.json``.
Enforced by ``tests/phase0/test_l4_review_not_faked.py``.

Usage:
    python tools/l4_review_scaffold.py [--out PATH]
"""
import argparse
import json
import os
import sys

RUNTIME = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime")
REPO = os.path.dirname(RUNTIME)
sys.path.insert(0, RUNTIME)

SCHEMA = os.path.join(REPO, "schemas", "review-report.schema.json")

# The real-content corpus (mirrors tools/real_content_eval.py).
CORPUS = [
    ("examples/minimal/attention.srt", "contact-examples__minimal__attention.png"),
    ("examples/run/attention-30s.srt", "contact-examples__run__attention-30s.png"),
    ("examples/run/10月2日.srt", "contact-examples__run__10月2日.png"),
    ("examples/run/10月4日.srt", "contact-examples__run__10月4日.png"),
    ("examples/showcase/01-explanatory-tech/case.srt", "contact-examples__showcase__01-explanatory-tech__case.png"),
    ("examples/showcase/02-narrative-emotion/case.srt", "contact-examples__showcase__02-narrative-emotion__case.png"),
    ("examples/showcase/03-data-comparison/case.srt", "contact-examples__showcase__03-data-comparison__case.png"),
    ("examples/showcase/04-longform-3min/case.srt", "contact-examples__showcase__04-longform-3min__case.png"),
    ("tests/golden/01-minimal/case.srt", "contact-tests__golden__01-minimal__case.png"),
    ("tests/golden/02-numeric/case.srt", "contact-tests__golden__02-numeric__case.png"),
]

PROMPTS = {
    "_l4_intro": "L4 is human/agent work (skills/09 VAL-01). Fill each PENDING verdict after looking at the contact sheet / preview frames.",
    "ppt_l4_1_standalone_claim": "PPT-L4-1 cover-subtitles test: with subtitles covered, can you restate this beat's proposition from the frame alone?",
    "ppt_l4_2_template_diversity": "PPT-L4-2 template diversity: does the whole film use >=4 distinct composition templates?",
    "ppt_l4_3_graphic_necessity": "PPT-L4-3 graphic necessity: cover each non-text element; if understanding is unharmed, it is decoration.",
    "ppt_l4_4_memory_point": "PPT-L4-4 memory-point: can you recall at least one concrete frame (e.g. 'the 20% donut') after watching?",
}


def build_report(corpus=None):
    """Return a PENDING L4 review scaffold (schema-shaped) for the corpus."""
    cases = []
    for srt, sheet in (corpus if corpus is not None else CORPUS):
        cases.append({
            "srt": srt,
            "contact_sheet": sheet,
            "ppt_l4_1_standalone_claim": "PENDING",
            "ppt_l4_2_template_diversity": "PENDING",
            "ppt_l4_3_graphic_necessity": "PENDING",
            "ppt_l4_4_memory_point": "PENDING",
            "verdict": "PENDING",
            "notes": "",
        })
    return {
        "l4_status": "PENDING",
        "reviewer": None,
        "generated_from": "tools/l4_review_scaffold.py",
        "prompts": PROMPTS,
        "cases": cases,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/mnt/cos/artifacts/p0-real-content-eval/review-report.json")
    args = ap.parse_args()
    report = build_report()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(report, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("wrote %s (%d cases, all PENDING)" % (args.out, len(report["cases"])))


if __name__ == "__main__":
    main()
