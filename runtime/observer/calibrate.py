"""Browser fidelity-threshold calibration (Phase 0, step 8).

Procedure (v4 §53 step 8):

  1. Render a fixed world state to HTML.
  2. Observe it ``reps`` times with the real browser.
  3. For every node, measure the absolute deviation between observed geometry
     and the *declared* layout (what the runtime asked the engine to draw).
  4. Derive thresholds from the p99 of that deviation, and record the actual
     sample size ``n`` and the observed maxima.

The output is an honest artifact: it states exactly how many observations it
came from. A full ``--reps 1000`` run is a scheduled job; smaller runs are
valid and self-labelled by their ``n``.

Pure derivation (:func:`derive`) is browser-free and unit-testable; only
:func:`collect` touches the browser.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

from . import browser, projection, render, thresholds
from world_state import compiler


def environment_fingerprint(binary: Optional[str] = None,
                            extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Describe the measurement environment so a calibration is auditable.

    A calibrated threshold is only meaningful for the environment it was measured
    in. We therefore record the browser build, the available font families, the
    OS/arch and the Python version, and fold them into a single stable
    ``environment_hash``. Two calibrations with different hashes are not
    comparable ground truth (Directive v5 §53 step 8).
    """
    env: Dict[str, Any] = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "system": platform.system(),
        "python": platform.python_version(),
    }
    binp = binary or browser.find_browser()
    if binp:
        env["browser_path"] = binp
        try:
            r = subprocess.run([binp, "--version"], capture_output=True,
                               text=True, timeout=20)
            env["browser_version"] = ((r.stdout or "") + (r.stderr or "")).strip()
        except Exception:  # noqa: BLE001
            env["browser_version"] = None
    try:
        out = subprocess.run(["fc-list"], capture_output=True, text=True,
                             timeout=20).stdout
        fams = sorted({ln.split(":")[1].strip() for ln in out.splitlines()
                       if ":" in ln and len(ln.split(":")) > 1})
        env["font_count"] = len(fams)
        env["fonts_hash"] = hashlib.sha256(
            "\n".join(fams).encode("utf-8")).hexdigest()
        env["cjk_fonts_present"] = any(
            ("CJK" in f or "Noto Sans SC" in f or "Hei" in f or "宋" in f
             or "黑" in f) for f in fams)
    except Exception:  # noqa: BLE001
        env["font_count"] = None
        env["fonts_hash"] = None
        env["cjk_fonts_present"] = None
    if extra:
        env.update(extra)
    payload = json.dumps(env, sort_keys=True, ensure_ascii=False)
    env["environment_hash"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return env


def _p99(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, max(0, int(math.ceil(0.99 * len(s))) - 1))
    return s[idx]


def geometry_deltas(observed: Dict[str, Any],
                    expected_layout: Dict[str, Dict[str, float]]) -> List[float]:
    """Per-node max |observed - declared| over x, y, w, h."""
    deltas: List[float] = []
    got = {n["id"]: n for n in observed.get("nodes", [])}
    for oid, geo in expected_layout.items():
        n = got.get(oid)
        if n is None:
            deltas.append(float("inf"))
            continue
        deltas.append(max(abs(n["x"] - geo["x"]), abs(n["y"] - geo["y"]),
                          abs(n["w"] - geo["w"]), abs(n["h"] - geo["h"])))
    return deltas


def derive(expected_layout: Dict[str, Dict[str, float]],
           observations: List[Dict[str, Any]], reps: int,
           environment: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Browser-free derivation of the threshold set from raw observations."""
    all_deltas: List[float] = []
    visibility_stable = True
    missing_nodes = 0
    edge_sets = []
    for obs in observations:
        deltas = geometry_deltas(obs, expected_layout)
        all_deltas.extend(deltas)
        missing_nodes += sum(1 for d in deltas if d == float("inf"))
        visible = {n["id"]: (n.get("visibility") != "hidden"
                             and n.get("display") != "none"
                             and float(n.get("opacity", 1)) > 0)
                   for n in obs.get("nodes", [])}
        if set(visible) != set(expected_layout.keys()):
            visibility_stable = False
        edge_sets.append(frozenset(
            (e["source"], e["target"], e["type"]) for e in obs.get("edges", [])))

    finite = [d for d in all_deltas if d != float("inf")]
    p99 = _p99(finite)
    mx = max(finite) if finite else 0.0
    tol = round(max(1.0, p99 + 0.5), 3)

    edge_stable = len(set(edge_sets)) <= 1 if edge_sets else True
    out = {
        "version": "1",
        "source": "calibrated",
        "n": reps,
        "geometry_tol_px": tol,
        "area_min_px2": 1.0,
        "opacity_min": 0.01,
        "p99_geometry_delta_px": round(p99, 4),
        "max_geometry_delta_px": round(mx, 4),
        "missing_nodes": missing_nodes,
        "visibility_stable": visibility_stable,
        "edge_stable": edge_stable,
    }
    # Auditability (Directive v5 §53 step 8): a calibrated number is only ground
    # truth for the environment it was measured in. Record that environment and
    # its hash so a reader can tell whether two calibrations are comparable.
    if environment is not None:
        out["environment"] = environment
        out["environment_hash"] = environment.get("environment_hash")
    return out


def collect(html_path: str, expected_layout: Dict[str, Dict[str, float]],
            reps: int, observe=None) -> List[Dict[str, Any]]:
    """Observe ``html_path`` ``reps`` times. Requires a real browser."""
    observe = observe or browser.observe
    out: List[Dict[str, Any]] = []
    for _ in range(reps):
        out.append(observe(html_path))
    return out


def calibrate_from_world_state(ws, outdir: str, reps: int,
                               observe=None) -> Dict[str, Any]:
    html = render.render_world_state(ws, os.path.join(outdir, "calib.html"))
    # Expected geometry comes from the INDEPENDENT projection, never from the
    # renderer's own layout function (Final Directive v5 §1, §4, §66).
    expected = projection.expected_layout(ws)
    obs = collect(html, expected, reps, observe=observe)
    env = environment_fingerprint(extra={"reps_requested": reps,
                                         "observations_collected": len(obs)})
    return derive(expected, obs, reps, environment=env)


def _anchor(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv: Optional[List[str]] = None) -> int:
    # allow `python -m runtime.observer.calibrate` from the repo root
    _rt = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _rt not in sys.path:
        sys.path.insert(0, _rt)
    ap = argparse.ArgumentParser(description="Calibrate browser fidelity thresholds.")
    ap.add_argument("--anchor", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "cases", "cause_effect", "anchor.json"))
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--out", default=thresholds.calibrated_path())
    args = ap.parse_args(argv)

    if not browser.available():
        print("no functional browser available; calibration skipped (honest).")
        return 2

    import tempfile
    ws = compiler.compile_world_state(_anchor(args.anchor))
    with tempfile.TemporaryDirectory(prefix="calib-") as d:
        thr = calibrate_from_world_state(ws, d, args.reps)
    path = thresholds.save(thr, args.out)
    print("calibrated: n=%d p99=%.4fpx tol=%.3fpx env=%s -> %s"
          % (thr["n"], thr["p99_geometry_delta_px"], thr["geometry_tol_px"],
             (thr.get("environment_hash") or "n/a")[:12], path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
