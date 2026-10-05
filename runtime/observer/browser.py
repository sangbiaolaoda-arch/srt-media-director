"""Chromium CLI observer — real geometry from a real engine, no bindings.

The probe is injected into a copy of the target HTML; after layout it walks
``[data-node]`` elements and records ``getBoundingClientRect`` + computed
style, plus ``[data-rel]`` edges, into a single ``data-tabbit-observed``
attribute. ``--dump-dom`` returns the post-script DOM; we parse the attribute
back out. This is genuine browser ground truth (layout, visibility, stacking),
which the repo's screenshot-only renderer never produced.
"""
from __future__ import annotations

import glob
import html
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

_SYSTEM_CANDIDATES = [
    "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
    "/usr/bin/chrome",
]

_OBSERVED_ATTR = "data-tabbit-observed"

_PROBE = r"""
(function(){
  function px(v){ return Math.round(v*1000)/1000; }
  var nodes = [];
  var els = document.querySelectorAll('[data-node]');
  for (var i=0;i<els.length;i++){
    var e = els[i], r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    nodes.push({
      id: e.getAttribute('data-node'),
      x: px(r.left + window.scrollX), y: px(r.top + window.scrollY),
      w: px(r.width), h: px(r.height),
      opacity: parseFloat(cs.opacity || '1'),
      visibility: cs.visibility, display: cs.display,
      z: parseInt(cs.zIndex || '0', 10) || 0,
      focus: e.getAttribute('data-focus') === 'true'
    });
  }
  var edges = [];
  var rels = document.querySelectorAll('[data-rel]');
  for (var j=0;j<rels.length;j++){
    var q = rels[j];
    edges.push({
      source: q.getAttribute('data-rel-source'),
      target: q.getAttribute('data-rel-target'),
      type: q.getAttribute('data-rel-type'),
      phase: q.getAttribute('data-rel-phase')
    });
  }
  var payload = {
    nodes: nodes, edges: edges,
    viewport: {w: window.innerWidth, h: window.innerHeight}
  };
  document.documentElement.setAttribute(%(attr)s,
      JSON.stringify(payload));
})();
""" % {"attr": repr(_OBSERVED_ATTR)}


def find_browser() -> Optional[str]:
    """Locate a usable Chromium/Chrome binary, or return None."""
    env = os.environ.get("CHROMIUM_BIN")
    if env and os.path.exists(env):
        return env
    for p in _SYSTEM_CANDIDATES:
        if os.path.exists(p):
            return p
    patterns = [
        os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
        os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-*/chrome-linux/headless_shell"),
        "/root/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
    ]
    for pat in patterns:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


def available() -> bool:
    return find_browser() is not None


def _inject(html_text: str, probe: str) -> str:
    marker = "</body>"
    idx = html_text.rfind(marker)
    script = "<script>%s</script>" % probe
    if idx == -1:
        return html_text + script
    return html_text[:idx] + script + html_text[idx:]


def _extract(dumped: str) -> Optional[str]:
    # the attribute value is HTML-escaped inside the dumped DOM.
    needle = _OBSERVED_ATTR + '="'
    i = dumped.find(needle)
    if i == -1:
        return None
    i += len(needle)
    j = dumped.find('"', i)
    if j == -1:
        return None
    return html.unescape(dumped[i:j])


def observe(html_path: str, *, width: int = 680, height: int = 382,
            timeout: int = 60) -> Dict[str, Any]:
    """Observe ``html_path`` and return raw geometry, or an honest empty result."""
    binary = find_browser()
    if not binary:
        return {"available": False, "backend": None, "nodes": [], "edges": [],
                "viewport": {"w": width, "h": height}}

    with open(html_path, encoding="utf-8") as f:
        html_text = f.read()

    tmpdir = tempfile.mkdtemp(prefix="observer-")
    try:
        probe_path = os.path.join(tmpdir, "probe.html")
        with open(probe_path, "w", encoding="utf-8") as f:
            f.write(_inject(html_text, _PROBE))
        profile = os.path.join(tmpdir, "profile")
        cmd = [
            binary, "--headless", "--no-sandbox", "--disable-gpu",
            "--disable-dev-shm-usage", "--hide-scrollbars",
            "--user-data-dir=" + profile,
            "--window-size=%d,%d" % (width, height),
            "--virtual-time-budget=2000",
            "--dump-dom", "file://" + os.path.abspath(probe_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        raw = _extract(proc.stdout)
        if raw is None:
            return {"available": True, "backend": os.path.basename(binary),
                    "nodes": [], "edges": [],
                    "viewport": {"w": width, "h": height},
                    "error": "probe attribute not found in dumped DOM"}
        import json
        payload = json.loads(raw)
        payload.update({"available": True, "backend": os.path.basename(binary)})
        return payload
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def observe_timeline(ws, outdir: str, *, width: int = 680, height: int = 382,
                     timeout: int = 60):
    """Render every keyframe of ``ws`` and observe each. Returns
    ``(observations, available)`` where observations is ``[(t, observed), ...]``.

    If no browser is available the replayed observations are empty, honestly.
    """
    from . import render
    frames = render.render_timeline(ws, outdir)
    observations = []
    available = find_browser() is not None
    for path, t in frames:
        obs = observe(path, width=width, height=height, timeout=timeout)
        observations.append((t, obs))
    return observations, available
