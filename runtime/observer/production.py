"""Production render-chain observer (Final Practical Closeout Directive, P0/P2).

The Phase-0 observer (:mod:`observer.browser`) reads ``[data-node]`` boxes from a
*synthetic* WorldState HTML. The real deliverable, however, is the compiled
``film/index.html``: a **canvas** player whose picture is painted by
``drawBeat(ctx, beat, t, exclude, overrides)`` from an embedded ``BEATS`` model.
A DOM probe sees nothing there — every element lives in pixels.

This module closes that gap. It drives a real Chromium over the *production*
artifact and asks canvas-native questions:

* **Presence (P0).** For each element the upstream plan declares, does the
  running player actually paint ink at the declared box during its declared life?
  We render the beat twice — once whole, once with the element excluded — and
  diff the pixels inside the box.
* **Transform / Motion (P2).** Does the element *arrive with the motion the
  director authored*? For elements carrying ``rise`` / ``pop`` / ``sink`` /
  ``shrink``, we probe the element early and settled and check that the painted
  ink actually moves down (rise/sink) or shrinks (pop/shrink) per the independent
  Motion projection (:mod:`observer.motion`), never per the player's own code.

The whole chain is therefore falsifiable end to end:

    SRT → Beat → Director → Composition → Motion → HTML Adapter →
    film/index.html → Chromium → Observer → Validator

The *expectation* comes from the upstream plan artifacts (``visual-dsl.json`` +
``render-plan.json`` + ``entrance-plan.json``) plus the independent motion
contract — never from the player's embedded ``BEATS``. The player under test is
asked only "what did you draw?", not "what should you have drawn?".

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

from . import browser, camera, motion, taxonomy

# Minimum painted pixels (inside the declared box) that count as "the element was
# actually drawn". Deliberately small: this is a presence test, not an aesthetic
# one; real text/motif/chart/connector elements paint far more.
INK_MIN_PX = 12
# A pixel is "element ink" when the two renders differ by more than this L1 sum
# over RGB (background gradient + antialiasing stay well under it).
INK_DIFF = 24
# Max painted pixels allowed to remain in a box whose element has exited.
INK_ABSENT_MAX_PX = 4

# Transform (motion) measurement tolerances.
MOTION_MIN_SHIFT_PX = 3.0      # a rise/sink must move the ink at least this far
MOTION_MAX_AREA_RATIO = 0.85   # a pop/shrink must reduce the ink area below this

# Camera (viewport) measurement: a pixel carries content when it differs from the
# flat background by at least CONTENT_DIFF (L1 RGB). The measured composite
# magnification must match the independent Camera projection within CAMERA_TOL.
CONTENT_DIFF = 30
CAMERA_TOL = 0.03
# The camera is a uniform scale about the centre, so the scene/composite extent
# ratio is robust to coarse sampling; stride the scan to keep observation cheap.
CAM_SCAN_STRIDE = 3

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
    // Stop the player's own animation loop: render() re-schedules itself via
    // requestAnimationFrame, so driving render() by hand would spawn a new
    // self-perpetuating loop per probe and blow the virtual-time budget. The
    // observer drives render() deterministically to exact times instead.
    window.requestAnimationFrame=function(){return 0;};
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

    function contentBBox(data){
      var br=data[0], bg=data[1], bb=data[2];
      var step=%(cam_stride)d;
      var minx=1e9,miny=1e9,maxx=-1,maxy=-1,cnt=0;
      for(var py=0;py<H;py+=step){
        var row=py*W;
        for(var px=0;px<W;px+=step){
          var j=(row+px)*4;
          var dd=Math.abs(data[j]-br)+Math.abs(data[j+1]-bg)+Math.abs(data[j+2]-bb);
          if(dd>%(content_diff)d){
            cnt++;
            if(px<minx)minx=px; if(py<miny)miny=py;
            if(px>maxx)maxx=px; if(py>maxy)maxy=py;
          }
        }
      }
      if(maxx<0)return null;
      return {x:minx,y:miny,w:maxx-minx+step,h:maxy-miny+step,cnt:cnt};
    }

    function measureCamera(beat,t){
      // Drive the player's own render() to time t. It draws the beat onto `scene`
      // with NO camera, then composites it onto `ctx` WITH the camera (a uniform
      // scale about the centre). One render() therefore yields both extents.
      var nowRef=1e9;
      try{ lastIdx=-1; hasPrev=false; T0=nowRef - t*1000; render(nowRef); }
      catch(e){ return {error:'render_failed:'+String(e)}; }
      var sb=contentBBox(sctx.getImageData(0,0,W,H).data);
      if(!sb||sb.cnt<%(ink_min)d)return {error:'no_scene_content'};
      var cb=contentBBox(ctx.getImageData(0,0,W,H).data);
      if(!cb||cb.cnt<%(ink_min)d)return {error:'no_composite_content'};
      var zw=cb.w/sb.w, zh=cb.h/sb.h;
      return {zoom:(zw+zh)/2.0, zw:zw, zh:zh, sb:sb, cb:cb,
              clipped:(cb.x<=0||cb.y<=0||cb.x+cb.w>=W||cb.y+cb.h>=H)};
    }

    function compute(){
      var out=[];
      for(var s=0;s<PROBES.length;s++){
        var sm=PROBES[s];
        var bi=byId[sm.beat_id];
        if(bi===undefined){ out.push({id:sm.id,t:sm.t,present:sm.present,probe:sm.probe,phase:sm.phase,error:'beat_not_found'}); continue; }
        var beat=BEATS[bi];
        if(sm.probe==='camera'){
          var zr=measureCamera(beat, sm.t);
          if(zr.error){ out.push({id:sm.id,beat_id:sm.beat_id,t:sm.t,probe:'camera',phase:sm.phase,error:zr.error}); }
          else { out.push({id:sm.id,beat_id:sm.beat_id,t:sm.t,probe:'camera',phase:sm.phase,zoom:zr.zoom,zw:zr.zw,zh:zr.zh,sb:zr.sb,cb:zr.cb,clipped:zr.clipped}); }
          continue;
        }
        var x=Math.max(0,Math.floor(sm.box.x));
        var y=Math.max(0,Math.floor(sm.box.y));
        var w=Math.min(W-x, Math.ceil(sm.box.w));
        var h=Math.min(H-y, Math.ceil(sm.box.h));
        if(w<=0||h<=0){ out.push({id:sm.id,t:sm.t,present:sm.present,probe:sm.probe,phase:sm.phase,error:'empty_box'}); continue; }
        drawBeat(pctx, beat, sm.t, null, null);
        var excl=new Set(); excl.add(sm.id);
        drawBeat(pctx2, beat, sm.t, excl, null);
        var A=pctx.getImageData(0,0,W,H).data;
        var B=pctx2.getImageData(0,0,W,H).data;
        var gink=0, gminx=1e9, gminy=1e9, gmaxx=-1, gmaxy=-1, bink=0;
        for(var j=0;j<A.length;j+=4){
          var d=Math.abs(A[j]-B[j])+Math.abs(A[j+1]-B[j+1])+Math.abs(A[j+2]-B[j+2]);
          if(d>%(ink_diff)d){
            var pix=j/4, px=pix%%W, py=(pix-px)/W;
            gink++;
            if(px<gminx)gminx=px; if(py<gminy)gminy=py;
            if(px>gmaxx)gmaxx=px; if(py>gmaxy)gmaxy=py;
            if(px>=x&&px<x+w&&py>=y&&py<y+h)bink++;
          }
        }
        out.push({id:sm.id, beat_id:sm.beat_id, t:sm.t, present:sm.present,
                  probe:sm.probe, phase:sm.phase,
                  ink:bink, gink:gink,
                  gbbox:(gmaxx<0? null : {x:gminx,y:gminy,w:gmaxx-gminx+1,h:gmaxy-gminy+1}),
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
""" % {"attr": repr(_ATTR), "probes": "__PROBES__", "ink_diff": INK_DIFF, "content_diff": CONTENT_DIFF, "ink_min": INK_MIN_PX, "cam_stride": CAM_SCAN_STRIDE}


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


def _clamp_time(t: float, start: float, end: float) -> float:
    return round(min(max(t, start), end - 0.001), 3)


def build_samples(dsl: Dict[str, Any], render_plan: Dict[str, Any],
                  entrance: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Expected probes, derived from the UPSTREAM plan layers.

    For every element we schedule presence probes at several times inside its
    declared alive window (``enter`` resolved → ``exit`` begins) and, when the
    element exits before the beat ends, one absence probe after the exit
    resolves. Elements carrying a transform motion additionally get a settle
    probe and an early probe so the Motion layer can be adjudicated. Neither the
    player nor its embedded ``BEATS`` is consulted.
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

            # --- transform / motion probes (P2) ---
            enter_motion = en.get("motion")
            exit_motion = (ex or {}).get("motion") if ex else None
            has_t = (enter_motion in motion.TRANSFORM_MOTIONS
                     or exit_motion in motion.TRANSFORM_MOTIONS)
            if not has_t:
                continue
            etype = el.get("type", "text")
            settle = enter_at + enter_dur + 0.12
            if exit_at is not None:
                settle = min(settle, exit_at - 0.06)
            settle = _clamp_time(settle, start, end)
            probes.append({"id": eid, "beat_id": bid, "t": settle,
                           "present": True, "kind": kind, "box": boxv,
                           "probe": "transform", "phase": "settle",
                           "el_type": etype, "motion": None,
                           "exp": motion.expected_transform(lc, settle)})
            if enter_motion in motion.TRANSFORM_MOTIONS:
                t_early = enter_at + max(0.05, 0.18 * max(enter_dur, 0.05))
                t_early = _clamp_time(t_early, start, end)
                probes.append({"id": eid, "beat_id": bid, "t": t_early,
                               "present": True, "kind": kind, "box": boxv,
                               "probe": "transform", "phase": "early",
                               "el_type": etype, "motion": enter_motion,
                               "exp": motion.expected_transform(lc, t_early)})
            if exit_motion in motion.TRANSFORM_MOTIONS:
                t_x = exit_at + max(0.05, 0.2 * max(exit_dur, 0.05))
                t_x = _clamp_time(t_x, start, end)
                probes.append({"id": eid, "beat_id": bid, "t": t_x,
                               "present": True, "kind": kind, "box": boxv,
                               "probe": "transform", "phase": "exit_early",
                               "el_type": etype, "motion": exit_motion,
                               "exp": motion.expected_transform(lc, t_x)})

        # --- camera (viewport) probes (P2) ---
        # Always one late probe; a second early probe only when the camera moves,
        # so the ramp and its direction are adjudicated without a redundant render
        # for every static beat.
        cam = b.get("camera")
        if camera.observable(cam):
            probe_times = [("late", end - 0.15)]
            if not camera.is_identity(cam):
                probe_times.append(("early", start + 0.5))
            for phase, ct in probe_times:
                ct = _clamp_time(ct, start, end)
                probes.append({"id": bid, "beat_id": bid, "t": ct,
                               "present": True, "probe": "camera", "phase": phase,
                               "exp": {"zoom": camera.expected_zoom(cam, start, end, ct)}})
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
            timeout: int = 300) -> Dict[str, Any]:
    """Observe the compiled player: what ink it actually paints. Browser-gated."""
    binary = browser.find_browser()
    if not binary or not browser.available():
        return {"available": False, "backend": None, "samples": [],
                "error": "no functional browser"}

    with open(film_html, encoding="utf-8") as f:
        html_text = f.read()

    # The probe understands only geometry/identity; expectation fields stay local.
    wire = [{k: v for k, v in p.items() if k != "exp"} for p in probes]
    probe = _PROBE_TEMPLATE.replace("__PROBES__", json.dumps(wire))
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
            "--virtual-time-budget=15000",
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


def _measure(sample: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """Painted-ink metrics (global bbox center-y and area) or ``None`` if unmeasured."""
    if not sample or int(sample.get("gink", 0)) < INK_MIN_PX:
        return None
    bb = sample.get("gbbox")
    if not bb:
        return None
    return {"cy": bb["y"] + bb["h"] / 2.0, "area": float(bb["w"]) * float(bb["h"])}


def verify(probes: List[Dict[str, Any]], observed: Dict[str, Any], *,
           dsl: Optional[Dict[str, Any]] = None,
           render_plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Adjudicate the observation against the upstream expectation."""
    if not observed.get("available", False):
        return {"verdict": taxonomy.ENVIRONMENT_FAIL,
                "fault_domain": taxonomy.fault_domain(taxonomy.ENVIRONMENT_FAIL),
                "available": False, "problems": [], "advisory": [],
                "note": observed.get("error", "no observation")}

    # --- presence dimension ---
    want: Dict[str, Dict[str, Any]] = {}
    for p in probes:
        if p.get("probe") in ("transform", "camera"):
            continue
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
        if s.get("probe") in ("transform", "camera"):
            continue
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

    # --- transform (motion) dimension ---
    want_t: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for p in probes:
        if p.get("probe") == "transform":
            want_t.setdefault(p["id"], {})[p["phase"]] = p
    obs_t: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for s in observed.get("samples", []):
        if s.get("probe") == "transform":
            obs_t.setdefault(s.get("id"), {})[s.get("phase")] = s

    transform_checked = 0
    transform_skipped = 0
    for eid, phases in sorted(want_t.items()):
        settle_exp = phases.get("settle")
        o_settle = obs_t.get(eid, {}).get("settle")
        if not settle_exp or not o_settle or o_settle.get("error"):
            problems.append({"kind": "motion_probe_missing", "detail": eid})
            continue
        m_settle = _measure(o_settle)
        if m_settle is None:
            advisory.append({"kind": "motion_unmeasurable", "detail": [eid, "settle"]})
            continue
        etype = settle_exp.get("el_type", "text")
        for phase in ("early", "exit_early"):
            exp = phases.get(phase)
            if not exp:
                continue
            name = exp.get("motion")
            # only adjudicate a motion whose channel is actually rendered for
            # this element type (contract-declared observability, not hardcoded).
            if not motion.observable(etype, name):
                transform_skipped += 1
                continue
            o = obs_t.get(eid, {}).get(phase)
            if not o or o.get("error"):
                problems.append({"kind": "motion_probe_missing",
                                 "detail": [eid, phase]})
                continue
            m = _measure(o)
            if m is None:
                advisory.append({"kind": "motion_unmeasurable", "detail": [eid, phase]})
                continue
            transform_checked += 1
            ok = True
            if name in ("rise", "sink"):
                need = max(MOTION_MIN_SHIFT_PX, 0.4 * float(exp["exp"]["dy"]))
                # the early frame must sit LOWER (larger center-y) than settled
                ok = m["cy"] >= m_settle["cy"] + need
            elif name in ("pop", "shrink"):
                ratio = m["area"] / max(1.0, m_settle["area"])
                ok = ratio <= MOTION_MAX_AREA_RATIO
            if not ok:
                problems.append({"kind": "motion_not_applied",
                                 "detail": [eid, phase, name,
                                            round(m["cy"], 1), round(m_settle["cy"], 1),
                                            round(m["area"], 1), round(m_settle["area"], 1)]})

    # --- camera (viewport) dimension ---
    want_cam: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for p in probes:
        if p.get("probe") == "camera":
            want_cam.setdefault(p["beat_id"], {})[p["phase"]] = p
    obs_cam: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for s in observed.get("samples", []):
        if s.get("probe") == "camera":
            obs_cam.setdefault(s.get("beat_id"), {})[s.get("phase")] = s

    camera_checked = 0
    for bid2, phases in sorted(want_cam.items()):
        measured: Dict[str, Dict[str, Any]] = {}
        bad = False
        for phase in sorted(phases):
            o = obs_cam.get(bid2, {}).get(phase)
            if not o or o.get("error"):
                problems.append({"kind": "camera_probe_missing",
                                 "detail": [bid2, phase, (o or {}).get("error")]})
                bad = True
                continue
            measured[phase] = o
        if bad:
            continue
        camera_checked += 1
        for phase, o in sorted(measured.items()):
            exp_z = float(phases[phase]["exp"]["zoom"])
            zw = float(o.get("zw", o.get("zoom", 1.0)))
            zh = float(o.get("zh", o.get("zoom", 1.0)))
            if not (abs(zw - exp_z) <= CAMERA_TOL or abs(zh - exp_z) <= CAMERA_TOL):
                problems.append({"kind": "camera_zoom_mismatch",
                                 "detail": [bid2, phase, round(zw, 4), round(zh, 4), round(exp_z, 4)]})
        if "early" in measured and "late" in measured:
            ze = max(float(measured["early"].get("zw", 1.0)), float(measured["early"].get("zh", 1.0)))
            zl = max(float(measured["late"].get("zw", 1.0)), float(measured["late"].get("zh", 1.0)))
            if zl + CAMERA_TOL < ze:
                problems.append({"kind": "camera_reversed", "detail": [bid2, round(ze, 4), round(zl, 4)]})

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
        "transform_checked": transform_checked,
        "transform_skipped": transform_skipped,
        "camera_checked": camera_checked,
        "camera_beats": len(want_cam),
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
          "%d motion-checks, %d problems, %d advisory) -> %s"
          % (report["verdict"], report.get("elements", 0), report.get("probes", 0),
             report.get("painted", 0), report.get("transform_checked", 0),
             len(report.get("problems", [])), len(report.get("advisory", [])), args.out))
    for p in report.get("problems", [])[:12]:
        print("  [%s] %s" % (p["kind"], p["detail"]))
    for a in report.get("advisory", [])[:6]:
        print("  (advisory) [%s] %s" % (a["kind"], a["detail"]))
    return 0 if report["verdict"] == taxonomy.PASS else 1


if __name__ == "__main__":
    sys.exit(main())
