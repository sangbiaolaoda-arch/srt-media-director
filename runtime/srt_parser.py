"""Stage 1 — SRT parsing.

SRT is the *single source of truth* for timing. The formal timeline must never
be re-estimated from character counts (skill: 01-srt-and-beats).
"""
import re

TIME_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)
NUM_RE = re.compile(r"\d+(?:\.\d+)?\s*%?")


def _sec(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt(path):
    """Parse an .srt file into cues + structural errors."""
    with open(path, encoding="utf-8-sig") as f:
        raw = f.read().replace("\r\n", "\n").strip()
    cues, errors = [], []
    for block in re.split(r"\n\s*\n", raw):
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        match, tidx = None, 0
        for i, line in enumerate(lines[:2]):
            match = TIME_RE.search(line)
            if match:
                tidx = i
                break
        if not match:
            errors.append({"code": "SRT_NO_TIME", "block": lines[0][:48]})
            continue
        g = match.groups()
        start, end = _sec(*g[:4]), _sec(*g[4:])
        if end <= start:
            errors.append({"code": "SRT_INVERTED", "block": lines[0][:48]})
            continue
        cues.append({
            "id": len(cues) + 1,
            "start": round(start, 3),
            "end": round(end, 3),
            "text": "".join(lines[tidx + 1:]),
        })
    for i in range(1, len(cues)):
        if cues[i]["start"] < cues[i - 1]["end"] - 1e-6:
            errors.append({"code": "SRT_OVERLAP", "cue": cues[i]["id"]})
    return {"cues": cues, "errors": errors}


def analyze(srt_path):
    """Produce srt-analysis.json: timing truth + surface features (no new facts)."""
    parsed = parse_srt(srt_path)
    cues = parsed["cues"]
    total = cues[-1]["end"] if cues else 0.0
    numbers = [
        {"cue_id": c["id"], "span": m.group(0)}
        for c in cues for m in NUM_RE.finditer(c["text"])
    ]
    gaps = [
        {"after_cue": cues[i]["id"], "sec": round(cues[i + 1]["start"] - cues[i]["end"], 3)}
        for i in range(len(cues) - 1)
        if cues[i + 1]["start"] - cues[i]["end"] > 0.05
    ]
    return {
        "timing_source": "srt",
        "source_file": srt_path,
        "total_duration_sec": total,
        "cues": cues,
        "numbers": numbers,
        "gaps": gaps,
        "errors": parsed["errors"],
    }
