"""Production render-chain observer (Final Practical Closeout Directive, P0).

The Phase-0 observer (:mod:`observer.browser`) reads ``[data-node]`` boxes from a
*synthetic* WorldState HTML. The real deliverable, however, is the compiled
``film/index.html``: a **canvas** player whose picture is painted by
``drawBeat(ctx, beat, t, exclude, overrides)`` from an embedded ``BEATS`` model.
A DOM probe sees nothing there — every element lives in pixels.

This module closes that gap. It drives a real Chromium over the *production*
artifact and asks a canvas-native question: **for each element the upstream plan
declares, does the running player actually paint ink at the declared box during
the element's declared life?** It does that by rendering the beat twice — once
whole, once with the element excluded — and diffing the pixels inside the box.

That makes the whole chain falsifiable end to end:

    SRT → Beat → Director → Composition → Motion → HTML Adapter →
    film/index.html → Chromium → Observer → Validator

The *expectation* comes from the upstream plan artifacts (``visual-dsl.json`` +
``render-plan.json`` + ``entrance-plan.json``) via :func:`build_samples`, never
from the player's own embedded ``BEATS``. The player under test is asked only
"what did you draw?", not "what should you have drawn?".

Two design points keep the verdict honest rather than overfit:

* **Multi-time sampling.** Elements reveal progressively (a connector grows as
  its ``draw`` event advances; chart bars grow). One fixed probe time would
  misfire on those. We therefore probe several times spanning each element's
  declared alive window and take the maximum ink.
* **Type-aware obligation.** Semantic content (text / chart / motif / connector
  / shape) *must* paint. ``decor`` is theme- and asset-dependent (e.g. a ghost
  heading whose alpha comes from ``THEME.ghost_alpha``, which may be 0), so it is
  reported as advisory and never fails the contract.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional

from . import browser, taxonomy

# Minimum painted pixels (inside the declared box) that count as "the element was
# actually drawn". Deliberately small: this is a presence test, not an aesthetic
# one; real text/motif/chart/connector elements paint far more.
INK_MIN_PX = 12
# A pixel is "element ink" when the two renders differ by more than this L1 sum
# over RGB (background gradient + antialiasing stay well under it).
INK_DIFF = 24
# Max painted pixels allowed to remain in a box whose element has exited.
INK_ABSENT_MAX_PX = 4

# Element types that MUST paint (the film's semantic content).
CONTENT_TYPES = {"text", "chart", "motif", "connector", "shape"}
# Theme/asset-dependent types: reported, never failing.
ADVISORY_TYPES = {"decor"}

_ATTR = "data-tabbit-production"

_PROBE_TEMPLATE = r"""
(function(){
  function report(o){
    try{
      var s=JSON.stringify(o);
      var b=btoa(unescape(encodeURIComponent(s)));
      document.documentElement.setAttribute(%(attr)s, b);
    }catch(e){
      document.documentElement.setAttribute(%(attr)s, 'ERR');
    }
  }
  try{
    if(typeof BEATS==='undefined'||typeof drawBeat!=='function'||typeof W==='undefined'){
      report({available:false, error:'production runtime globals missing (BEATS/drawBeat/W)'});
      return;
    }
    var PROBES = %(probes)s;
    var byId={};
    for(var i=0;i<BEATS.length;i++){ byId[BEATS[i].id]=i; }
    var pc=document.createElement('canvas'); pc.width=W; pc.height=H;
    var pctx=pc.getContext('2d');
    var pc2=document.createElement('canvas'); pc2.width=W; pc2.height=H;
    var pctx2=pc2.getContext('2d');

    function imagesReady(){
      for(var k in IMG){ var im=IMG[k]; if(im && im.src && !im.complete){ return false; } }
      return true;
    }

    function compute(){
      var out=[];
      for(var s=0;s<PROBES.length;s++){
        var sm=PROBES[s];
        var bi=byId[sm.beat_id];
        if(bi===undefined){ out.push({id:sm.id, t:sm.t, present:sm.present, error:'beat_not_found'}); continue; }
        var beat=BEATS[bi];
        var x=Math.max(0,Math.floor(sm.box.x));
        var y=Math.max(0,Math.floor(sm.box.y));
        var w=Math.min(W-x, Math.ceil(sm.box.w));
        var h=Math.min(H-y, Math.ceil(sm.box.h));
        if(w<=0||h<=0){ out.push({id:sm.id, t:sm.t, present:sm.present, error:'empty_box'}); continue; }
        drawBeat(pctx, beat, sm.t, null, null);
        var excl=new Set(); excl.add(sm.id);
        drawBeat(pctx2, beat, sm.t, excl, null);
        var A=pctx.getImageData(x,y,w,h).data;
        var B=pctx2.getImageData(x,y,w,h).data;
        var ink=0, minx=1e9, miny=1e9, maxx=-1, maxy=-1;
        for(var j=0;j<A.length;j+=4){
          var d=Math.abs(A[j]-B[j])+Math.abs(A[j+1]-B[j+1])+Math.abs(A[j+2]-B[j+2]);
          if(d>%(ink_diff)d){
            ink++;
            var pix=j/4, px=pix%%w, py=(pix-px)/w;
            if(px<minx)minx=px; if(py<miny)miny=py;
            if(px>maxx)maxx=px; if(py>maxy)maxy=py;
          }
        }
        out.push({id:sm.id, beat_id:sm.beat_id, t:sm.t, present:sm.present, ink:ink,
                  bbox: (maxx<0? null : {x:minx,y:miny,w:maxx-minx+1,h:maxy-miny+1}),
                  region:{x:x,y:y,w:w,h:h}});
      }
      report({available:true, backend:'chromium', samples:out,
              viewport:{w:W,h:H}, beats:BEATS.length});
    }

    var tries=0;
    function go(){
      tries++;
      if(!imagesReady() && tries<200){ setTimeout(go, 15); return; }
      compute();
    }
    go();
  }catch(e){
    report({available:false, error:String(e)});
  }
})();
""" % {"attr": repr(_ATTR), "probes": "__PROBES__", "ink_diff": INK_DIFF}


def _kind(el_type: str) -> str:
    if el_type in CONTENT_TYPES:
        return "must"
    if el_type in ADVISORY_TYPES:
        return "advisory"
    return "must"


def _times(start: float, end: float, enter_at: float, enter_dur: float,
           exit_at: Optional[float], exit_dur: float) -> List[float]:
    """Probe times spanning the element's declared alive window."""
    win_start = min(end - 0.001, max(start, enter_at + enter_dur + 0.05))
    if exit_at is not None:
        win_end = max(win_start, exit_at - 0.05)
    else:
        win_end = end - 0.05
    if win_end < win_start:
        win_start = win_end = (enter_at + enter_dur + end) / 2.0
    times = [win_start, (win_start + win_end) / 2.0, win_end]
    seen: List[float] = []
    for t in times:
        if start - 0.001 <= t <= end + 0.001 and all(abs(t - u) > 0.02 for u in seen):
            seen.append(round(t, 3))
    return seen or [round(min(max(enter_at, start), end - 0.001), 3)]


def build_samples(dsl: Dict[str, Any], render_plan: Dict[str, Any],
                  entrance: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Expected paint probes, derived from the UPSTREAM plan layers.

    For every element we schedule presence probes at several times inside its
    declared alive window (``enter`` resolved → ``exit`` begins) and, when the
    element exits before the beat ends, one absence probe after the exit
    resolves. Neither the player nor its embedded ``BEATS`` is consulted.
    """
    plans = {b["beat_id"]: b for b in render_plan["beats"]}
    ents = {b["beat_id"]: b for b in entrance["beats"]}
    probes: List[Dict[str, Any]] = []
    for b in dsl["beats"]:
        bid = b["beat_id"]
        boxes = plans.get(bid, {}).get("boxes", {})
        lifecycle = ents.get(bid, {}).get("lifecycle", {})
        start = float(b["start_sec"])
        end = float(b["end_sec"])
        for el in b["elements"]:
            eid = el["id"]
            box = boxes.get(eid)
            if not box:
                continue
            lc = lifecycle.get(eid) or {}
            en = lc.get("enter") or {}
            enter_at = float(en.get("at", start))
            enter_dur = float(en.get("dur", 0.0))
            ex = lc.get("exit")
            exit_at = float(ex.get("at")) if ex else None
            exit_dur = float(ex.get("dur", 0.0)) if ex else 0.0
            boxv = {k: float(box[k]) for k in ("x", "y", "w", "h")}
            kind = _kind(el.get("type", "text"))
            for t in _times(start, end, enter_at, enter_dur, exit_at, exit_dur):
                probes.append({"id": eid, "beat_id": bid, "t": t, "present": True,
                               "kind": kind, "box": boxv})
            if ex is not None:
                abs_t = exit_at + exit_dur + 0.12
                if start <= abs_t < end - 0.001:
                    probes.append({"id": eid, "beat_id": bid, "t": round(abs_t, 3),
                                   "present": False, "kind": kind, "box": boxv})
    return probes


def _inject(html_text: str, probe: str) -> str:
    marker = "</body>"
    idx = html_text.rfind(marker)
    script = "<script>%s</script>" % probe
    if idx == -1:
        return html_text + script
    return html_text[:idx] + script + html_text[idx:]


def _extract(dumped: str) -> Optional[str]:
    needle = _ATTR + '="'
    i = dumped.find(needle)
    if i == -1:
        return None
    i += len(needle)
    j = dumped.find('"', i)
    if j == -1:
        return None
    raw = dumped[i:j]
    if raw == "ERR":
        return None
    try:
        return base64.b64decode(raw).decode("utf-8")
    except Exception:  # noqa: BLE001
        return None


def observe(film_html: str, probes: List[Dict[str, Any]], *,
            timeout: int = 120) -> Dict[str, Any]:
    """Observe the compiled player: what ink it actually paints. Browser-gated."""
    binary = browser.find_browser()
    if not binary or not browser.available():
        return {"available": False, "backend": None, "samples": [],
                "error": "no functional browser"}

    with open(film_html, encoding="utf-8") as f:
        html_text = f.read()

    probe = _PROBE_TEMPLATE.replace("__PROBES__", json.dumps(probes))
    tmpdir = tempfile.mkdtemp(prefix="prod-observer-")
    try:
        probe_path = os.path.join(tmpdir, "probe.html")
        with open(probe_path, "w", encoding="utf-8") as f:
            f.write(_inject(html_text, probe))
        profile = os.path.join(tmpdir, "profile")
        cmd = [
            binary, "--headless", "--no-sandbox", "--disable-gpu",
            "--disable-dev-shm-usage", "--hide-scrollbars",
            "--user-data-dir=" + profile,
            "--window-size=1280,720",
            "--virtual-time-budget=12000",
            "--dump-dom", "file://" + os.path.abspath(probe_path),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"available": False, "backend": binary, "samples": [],
                    "error": "observer timeout"}
        payload = _extract(proc.stdout or "")
        if payload is None:
            return {"available": False, "backend": binary, "samples": [],
                    "error": "production probe produced no payload"}
        data = json.loads(payload)
        data.setdefault("backend", binary)
        return data
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def verify(probes: List[Dict[str, Any]], observed: Dict[str, Any], *,
           dsl: Optional[Dict[str, Any]] = None,
           render_plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Adjudicate the observation against the upstream expectation."""
    if not observed.get("available", False):
        return {"verdict": taxonomy.ENVIRONMENT_FAIL,
                "fault_domain": taxonomy.fault_domain(taxonomy.ENVIRONMENT_FAIL),
                "available": False, "problems": [], "advisory": [],
                "note": observed.get("error", "no observation")}

    want: Dict[str, Dict[str, Any]] = {}
    for p in probes:
        w = want.setdefault(p["id"], {"kind": p["kind"], "present": False,
                                      "absence": False})
        if p["present"]:
            w["present"] = True
        else:
            w["absence"] = True

    present_ink: Dict[str, int] = {}
    absence_ink: Dict[str, int] = {}
    err: Dict[str, str] = {}
    for s in observed.get("samples", []):
        sid = s.get("id")
        if s.get("error"):
            err[sid] = s["error"]
            continue
        ink = int(s.get("ink", 0))
        if s.get("present"):
            present_ink[sid] = max(present_ink.get(sid, 0), ink)
        else:
            absence_ink[sid] = max(absence_ink.get(sid, 0), ink)

    problems: List[Dict[str, Any]] = []
    advisory: List[Dict[str, Any]] = []

    for eid, w in sorted(want.items()):
        if eid in err:
            problems.append({"kind": "probe_error", "detail": [eid, err[eid]]})
            continue
        if w["present"] and eid not in present_ink:
            problems.append({"kind": "element_never_probed", "detail": eid})
            continue
        if w["present"] and present_ink.get(eid, 0) < INK_MIN_PX:
            rec = {"kind": "element_not_painted", "detail": [eid, present_ink.get(eid, 0)],
                   "type": w["kind"]}
            (advisory if w["kind"] == "advisory" else problems).append(rec)
        if w["absence"] and absence_ink.get(eid, 0) > INK_ABSENT_MAX_PX:
            problems.append({"kind": "element_lingering_after_exit",
                             "detail": [eid, absence_ink.get(eid, 0)]})

    if render_plan is not None:
        want_beats = len(render_plan.get("beats", []))
        got_beats = observed.get("beats")
        if got_beats is not None and got_beats != want_beats:
            problems.append({"kind": "beat_count_mismatch",
                             "detail": [want_beats, got_beats]})

    verdict = taxonomy.PASS if not problems else taxonomy.RENDER_FAIL
    return {
        "verdict": verdict,
        "fault_domain": taxonomy.fault_domain(verdict),
        "available": True,
        "backend": observed.get("backend"),
        "beats": observed.get("beats"),
        "elements": len(want),
        "probes": len(probes),
        "painted": sum(1 for v in present_ink.values() if v >= INK_MIN_PX),
        "problems": problems,
        "advisory": advisory,
    }


def run(film_html: str, work_dir: str, *, observe_fn=None) -> Dict[str, Any]:
    """Observe + verify the compiled player against upstream work artifacts."""
    def _load(name):
        with open(os.path.join(work_dir, name), encoding="utf-8") as f:
            return json.load(f)

    dsl = _load("visual-dsl.json")
    render_plan = _load("render-plan.json")
    entrance = _load("entrance-plan.json")
    probes = build_samples(dsl, render_plan, entrance)
    obs = (observe_fn or observe)(film_html, probes)
    return verify(probes, obs, dsl=dsl, render_plan=render_plan)


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    _rt = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _rt not in sys.path:
        sys.path.insert(0, _rt)
    ap = argparse.ArgumentParser(description="Verify the compiled production player.")
    ap.add_argument("--film", default=os.path.join("sample", "film", "index.html"))
    ap.add_argument("--work", default=os.path.join("sample", "work"))
    ap.add_argument("--out", default=os.path.join("sample", "work",
                                                  "production-render-report.json"))
    args = ap.parse_args(argv)

    if not browser.available():
        print("no functional browser available; production contract NOT evaluated (honest).")
        return 2

    report = run(args.film, args.work)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    print("production-render-contract: %s (%d elements, %d probes, %d painted, "
          "%d problems, %d advisory) -> %s"
          % (report["verdict"], report.get("elements", 0), report.get("probes", 0),
             report.get("painted", 0), len(report.get("problems", [])),
             len(report.get("advisory", [])), args.out))
    for p in report.get("problems", [])[:12]:
        print("  [%s] %s" % (p["kind"], p["detail"]))
    for a in report.get("advisory", [])[:6]:
        print("  (advisory) [%s] %s" % (a["kind"], a["detail"]))
    return 0 if report["verdict"] == taxonomy.PASS else 1


if __name__ == "__main__":
    sys.exit(main())
