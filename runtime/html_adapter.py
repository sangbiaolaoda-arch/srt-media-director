"""Stage 6b — HTML adapter v4.2：与 raster_renderer 同语义的电影感双侧实现。

v4.2 变化（对应 raster 端，保持双侧一致）：
- 画布背景：纵向渐变（THEME.bg_top → bg_bottom）+ 径向暗角 + 遮幅黑边；
  胶片颗粒仅光栅端实现（播放器端以 CSS 噪点近似成本高且收益低，差异已在
  meta 注明）；
- 排版主角化：标题/关键词/金句/数字走衬线字体栈（Noto Serif CJK →
  Songti SC → SimSun），强调元素带 shadowBlur 柔光，eyebrow 加 letterSpacing；
- motif 水印化：单 motif 放大 2.2 倍垫在文字之下（alpha 0.15），多 motif
  对照保持构图盒子、alpha 0.55；
- boxed 描边框 → 上下细金线（accent rule）；shape 面板 → 径向光晕；
- 淡入淡出一律与主题底色混合（暗色主题下不再是与米色纸面混合）。

产物是编译结果、只读；修任何一拍都改上游 DSL 重新编译（CORE-20）。
"""
import json
import os

import svg_art
from common import CANVAS_W as W, CANVAS_H as H, COLORS, PALETTES, THEME, ensure_dir
from aesthetic_canonical import grade as _grade

_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<style>
  body{margin:0;background:#0B0906;display:flex;flex-direction:column;
       align-items:center;justify-content:center;min-height:100vh;
       font-family:"Noto Sans CJK SC","PingFang SC","Microsoft YaHei",sans-serif;}
  #cv{background:#17130E;border-radius:4px;max-width:96vw;height:auto;
      box-shadow:0 18px 60px rgba(0,0,0,.65);}
  #cap{color:#B8AD99;margin-top:14px;font-size:19px;min-height:28px;
       max-width:1180px;text-align:center;letter-spacing:1px;}
  #meta{color:#5c5548;margin-top:6px;font-size:12px;}
</style>
</head>
<body>
<canvas id="cv" width="__W__" height="__H__"></canvas>
<div id="cap"></div>
<div id="meta">__TITLE__ · SRT Media Director v4.4 cinema · 颗粒仅光栅端</div>
<script>
"use strict";
const W=__W__, H=__H__, TRANS=0.45;
const COLORS=__COLORS__;
const THEME=__THEME__;
const PALETTES=__PALETTES__;
const ARTS=__ARTS__;
const BEATS=__BEATS__;
const SANS='"Noto Sans CJK SC","PingFang SC","Microsoft YaHei",sans-serif';
const SERIF='"Noto Serif CJK SC","Songti SC","STSong","SimSun",serif';
const SERIF_SLOTS={title:1,keyword:1,word_left:1,word_right:1,
                   cause:1,result:1,delta:1,number:1};
const cv=document.getElementById("cv"), ctx=cv.getContext("2d");
const scene=document.createElement("canvas"); scene.width=W; scene.height=H;
const sctx=scene.getContext("2d");
const pcv=document.createElement("canvas"); pcv.width=W; pcv.height=H;
const pctx=pcv.getContext("2d");
const cap=document.getElementById("cap");
const BAR=THEME.letterbox_px;

function clamp01(v){return v<0?0:v>1?1:v;}
function ease(t){t=clamp01(t);return t*t*(3-2*t);}
function hx(c){if(c.charAt(0)==="#")return [parseInt(c.slice(1,3),16),
  parseInt(c.slice(3,5),16),parseInt(c.slice(5,7),16)];
  const m=c.match(/\\d+/g);return [+m[0],+m[1],+m[2]];}
function mix(c1,c2,t){const a=hx(c1),b=hx(c2),k=clamp01(t);
  return "rgb("+a.map(function(v,i){return Math.round(v+(b[i]-v)*k);}).join(",")+")";}
function mixa(c1,c2,t,alpha){const a=hx(c1),b=hx(c2),k=clamp01(t);
  return "rgba("+a.map(function(v,i){return Math.round(v+(b[i]-v)*k);}).join(",")
    +","+alpha+")";}
function fade(c,a){return mix(THEME.bg_top,c,a);}
function roleColor(el){
  if(el.colorRole==="ink")return THEME.ink;
  if(el.colorRole==="neutral")return THEME.muted;
  return COLORS[el.colorRole]||THEME.ink;}
// v6.1：主体文字走加深色，避免浅底上「文字像背景」。
function textColor(el){
  const r=el.colorRole;
  if(r==="ink")return THEME.ink;
  if(r==="neutral")return THEME.muted;
  const k="text_"+r;
  return THEME[k]||COLORS[r]||THEME.ink;}
function rr(c2,x,y,w,h,r){c2.beginPath();c2.moveTo(x+r,y);
  c2.arcTo(x+w,y,x+w,y+h,r);c2.arcTo(x+w,y+h,x,y+h,r);
  c2.arcTo(x,y+h,x,y,r);c2.arcTo(x,y,x+w,y,r);c2.closePath();}

// ---- 主题基底（渐变底 + 暗角，缓存一次） ----
let BG=null, VIG=null;
function ensureGrade(){
  if(BG)return;
  BG=ctx.createLinearGradient(0,0,0,H);
  BG.addColorStop(0,THEME.bg_top);BG.addColorStop(1,THEME.bg_bottom);
  const r=Math.hypot(W/2,H/2);
  VIG=ctx.createRadialGradient(W/2,H/2,r*THEME.vignette_inner,W/2,H/2,r);
  VIG.addColorStop(0,"rgba(0,0,0,0)");
  VIG.addColorStop(1,"rgba(0,0,0,"+THEME.vignette+")");
}
function applyGrade(c2){
  c2.save();
  c2.fillStyle=VIG;c2.fillRect(0,0,W,H);
  c2.fillStyle="#000";
  c2.fillRect(0,0,W,BAR);c2.fillRect(0,H-BAR,W,BAR);
  c2.restore();
}

// ---- SVG 画法预加载（与光栅渲染器同一套 svg_art 字符串） ----
const IMG={}, loads=[];
for(const beat of BEATS)for(const el of beat.elements){
  if(!el.art)continue;
  const key=el.art+"|"+el.color;
  if(IMG[key])continue;
  const svg=(ARTS[el.art]||"").split("{COLOR}").join(el.color);
  const im=new Image(); IMG[key]=im;
  loads.push(new Promise(function(res){im.onload=res;im.onerror=res;
    im.src="data:image/svg+xml;charset=utf-8,"+encodeURIComponent(svg);}));
}

// ---- lifecycle 驱动的元素状态（与 raster_renderer._state 同语义） ----
function beatState(beat,t){
  const st={}, ev={};
  for(const eid in beat.lifecycle){
    const lc=beat.lifecycle[eid], en=lc.enter;
    if(en.motion==="inherit"){st[eid]={alpha:1,dy:0,scale:1};continue;}
    const a=ease((t-en.at)/Math.max(en.dur,0.01));
    let dy=0,scale=1;
    if(a<1){ if(en.motion==="rise")dy=(1-a)*26; else if(en.motion==="pop")scale=0.55+0.45*a; }
    let alpha=a;
    const x=lc.exit;
    if(x&&t>=x.at){
      const q=ease((t-x.at)/Math.max(x.dur,0.01));
      alpha=a*(1-q);
      if(x.motion==="sink")dy+=q*34; else if(x.motion==="shrink")scale*=1-0.55*q;
    }
    st[eid]={alpha:alpha,dy:dy,scale:scale};
  }
  for(const e of beat.events){
    const p=clamp01((t-e.at)/0.9);
    for(const tg of e.targets){(ev[tg]=ev[tg]||[]).push([e.action,p]);}
  }
  return [st,ev];
}

function scaledBox(b,k,margin){
  const cx=b.x+b.w/2, cy=b.y+b.h/2;
  let w=Math.min(b.w*k,W*(1-2*margin)), h=Math.min(b.h*k,H*(1-2*margin));
  return {x:cx-w/2,y:cy-h/2,w:w,h:h};
}

const ORDER={decor:-1,shape:0,motif:1,chart:1,connector:2,text:3};
function drawBeat(c2,beat,t,exclude,overrides){
  const stEv=beatState(beat,t), st=stEv[0], ev=stEv[1];
  c2.clearRect(0,0,W,H);
  const pal=PALETTES[beat.palette]||PALETTES.night;
  const bg2=c2.createLinearGradient(0,0,0,H);
  bg2.addColorStop(0,pal.top);bg2.addColorStop(1,pal.bottom);
  c2.fillStyle=bg2; c2.fillRect(0,0,W,H);
  const nMotifs=beat.elements.filter(function(e){return e.type==="motif";}).length;
  const els=beat.elements.slice().sort(function(a,b){
    return (ORDER[a.type]!=null?ORDER[a.type]:9)-(ORDER[b.type]!=null?ORDER[b.type]:9);});
  for(const el of els){
    if(exclude&&exclude.has(el.id))continue;
    const s=st[el.id]; if(!s||s.alpha<=0)continue;
    let b=beat.boxes[el.id]; if(!b)continue;
    if(overrides&&overrides[el.id])b=overrides[el.id];
    b={x:b.x,y:b.y+s.dy,w:b.w,h:b.h};
    const a=s.alpha, evs=ev[el.id]||[], ACC=COLORS_accent();
    if(el.type==="decor"){
      if(el.text){ // 幽灵大字：衬线特大号，暗底上的浅色淡字
        const fs=beat.fonts[el.id]||{size:90};
        c2.fillStyle=mixa(THEME.bg_top,THEME.ink,THEME.ghost_alpha*a,1);
        c2.font="700 "+Math.round(fs.size)+"px "+SERIF;
        c2.textAlign="center";c2.textBaseline="middle";
        c2.fillText(el.text,b.x+b.w/2,b.y+b.h/2);
      }else if(el.art){
        const im=IMG[el.art+"|"+THEME.muted]; if(!im||!im.complete)continue;
        c2.globalAlpha=a*0.38;
        c2.drawImage(im,b.x,b.y,b.w,b.h);
        c2.globalAlpha=1;
      }
    }else if(el.type==="shape"){
      const base=el.tone==="negative_soft"?COLORS.negative:
                 el.tone==="positive_soft"?COLORS.positive:THEME.muted;
      const cx=b.x+b.w/2, cy=b.y+b.h/2, r=Math.max(b.w,b.h)*0.62;
      const g=c2.createRadialGradient(cx,cy,0,cx,cy,r);
      g.addColorStop(0,mixa(THEME.bg_top,base,0.16*a,1));
      g.addColorStop(1,mixa(THEME.bg_top,base,0,1));
      c2.fillStyle=g; c2.fillRect(b.x-r*0.3,b.y-r*0.3,b.w+r*0.6,b.h+r*0.6);
    }else if(el.type==="motif"){
      const col=el.color;
      const im=IMG[(el.art||el.motif||"compass")+"|"+col]; if(!im||!im.complete)continue;
      { // v5.1：按构图盒子画前景插图，不再放大成背景水印
        const k=nMotifs===1?0.92:0.55;
        const w=b.w*s.scale,h=b.h*s.scale;
        c2.globalAlpha=a*k;
        c2.drawImage(im,b.x+(b.w-w)/2,b.y+(b.h-h)/2,w,h);
      }
      c2.globalAlpha=1;
    }else if(el.type==="connector"){
      let p=1; for(const pr of evs)if(pr[0]==="draw")p=pr[1];
      const y=b.y+b.h/2,x0=b.x,x1=b.x+b.w*p;
      if(x1-x0>=4){
        c2.strokeStyle=fade(ACC,a*0.85);c2.lineWidth=3;c2.lineCap="round";
        c2.beginPath();c2.moveTo(x0,y);c2.lineTo(x1,y);c2.stroke();
        if(p>0.85){const s2=b.h*0.30;c2.fillStyle=fade(ACC,a*0.85);
          c2.beginPath();c2.moveTo(x1,y);c2.lineTo(x1-s2,y-s2*0.62);
          c2.lineTo(x1-s2,y+s2*0.62);c2.closePath();c2.fill();}
      }
    }else if(el.type==="chart"){
      const ch=el.chart,cx=b.x+b.w/2,cy=b.y+b.h/2;
      if(ch.kind==="donut"){
        let p=1; for(const pr of evs)if(pr[0]==="chart_fill")p=pr[1];
        const r=Math.min(b.w,b.h)/2*0.96;
        c2.fillStyle=mix(THEME.bg_top,THEME.ink,0.14*a);
        c2.beginPath();c2.arc(cx,cy,r,0,Math.PI*2);c2.fill();
        const frac=clamp01(ch.value/100)*p;
        if(frac>0){c2.fillStyle=fade(COLORS.info,a);
          c2.beginPath();c2.moveTo(cx,cy);
          c2.arc(cx,cy,r,-Math.PI/2,-Math.PI/2+Math.PI*2*frac);
          c2.closePath();c2.fill();}
        c2.fillStyle=THEME.bg_bottom;
        c2.beginPath();c2.arc(cx,cy,r*0.62,0,Math.PI*2);c2.fill();
      }else{
        let p=1; for(const pr of evs)if(pr[0]==="bars_grow")p=pr[1];
        const baseY=b.y+b.h*0.88,topY=b.y+b.h*0.10,full=baseY-topY,
              hi=Math.max(ch.before,ch.after,1e-9),bw=b.w*0.13;
        [ch.before,ch.after].forEach(function(v,i){
          const h2=full*(v/hi)*p,cx2=b.x+b.w*(0.32+0.26*i);
          c2.fillStyle=i===1?fade(COLORS.positive,a):fade(THEME.muted,a);
          c2.fillRect(cx2-bw/2,baseY-h2,bw,h2);
          c2.fillStyle=THEME.ink;c2.font="20px "+SANS;
          c2.textAlign="center";c2.textBaseline="middle";
          c2.fillText(String(v),cx2,baseY+14);
        });
        c2.strokeStyle=THEME.muted;c2.lineWidth=2;
        c2.beginPath();c2.moveTo(b.x+b.w*0.12,baseY);
        c2.lineTo(b.x+b.w*0.88,baseY);c2.stroke();
      }
    }else if(el.type==="text"){
      const fs=beat.fonts[el.id]||{size:26,bold:false};
      const serif=!!SERIF_SLOTS[el.slot];
      let col=textColor(el);
      for(const pr of evs){
        if(pr[0]==="color_wash")col=mix(THEME.ink,textColor(el),pr[1]);
      }
      let size=fs.size;
      for(const pr of evs){
        if(pr[0]==="pulse"&&pr[1]>0&&pr[1]<1)
          size=size*(1+0.06*Math.sin(pr[1]*Math.PI));
      }
      size=Math.round(size*s.scale);
      const isPrimary=el.role==="primary"||el.emphasis;
      const bold=(fs.bold||el.emphasis)?"700 ":"400 ";
      c2.font=bold+size+"px "+(serif?SERIF:SANS);
      c2.textAlign="center";c2.textBaseline="middle";
      if(el.slot==="eyebrow"&&"letterSpacing" in c2)c2.letterSpacing="5px";
      const ink=fade(col,a);
      if(el.boxed){ // 细金线替代描边框
        const cx=b.x+b.w/2,hw=b.w*0.28,rc=fade(ACC,a);
        c2.strokeStyle=rc;c2.lineWidth=2;
        [b.y+b.h*0.04,b.y+b.h*0.96].forEach(function(y){
          c2.beginPath();c2.moveTo(cx-hw,y);c2.lineTo(cx+hw,y);c2.stroke();
          c2.fillStyle=rc;
          c2.beginPath();c2.arc(cx-hw,y,2.5,0,Math.PI*2);c2.fill();
          c2.beginPath();c2.arc(cx+hw,y,2.5,0,Math.PI*2);c2.fill();
        });
      }
      if(isPrimary){ // 强调柔光
        c2.save();
        c2.shadowColor=mixa(THEME.bg_top,el.emphasis?ACC:col,0.85,1);
        c2.shadowBlur=18;
        c2.fillStyle=mixa(THEME.bg_top,col,a,0.55);
        c2.fillText(el.text,b.x+b.w/2,b.y+b.h/2);
        c2.restore();
      }
      c2.fillStyle=ink;
      c2.fillText(el.text,b.x+b.w/2,b.y+b.h/2);
      if("letterSpacing" in c2)c2.letterSpacing="0px";
    }
  }
}
function COLORS_accent(){return THEME.accent;}

// ---- 主循环：跨拍溶解（上一拍末态离屏快照溶出）+ 交接主体位置插值 + 镜头 ----
let lastIdx=-1, hasPrev=false, carriedPrev=new Set(), prevMap={};
function render(now){
  const total=BEATS[BEATS.length-1].end;
  const t=((now-T0)/1000)%total;
  let idx=BEATS.findIndex(function(b){return t<b.end;}); if(idx<0)idx=BEATS.length-1;
  const beat=BEATS[idx];
  if(idx!==lastIdx){
    if(lastIdx>=0){
      const pb=BEATS[lastIdx], curM={};
      for(const el of beat.elements)if(el.type==="motif"&&el.motif)curM[el.motif]=el.id;
      carriedPrev=new Set(); prevMap={};
      for(const pel of pb.elements)if(pel.type==="motif"&&curM[pel.motif]){
        carriedPrev.add(pel.id); prevMap[curM[pel.motif]]=pb.boxes[pel.id];}
      drawBeat(pctx,pb,pb.end,carriedPrev,null);
      hasPrev=true;
    }
    cap.textContent=beat.narration||"";
    lastIdx=idx;
  }
  const q=ease((t-beat.start)/TRANS);
  let overrides=null;
  if(q<1&&hasPrev){
    overrides={};
    for(const cid in prevMap){const pa=prevMap[cid],pb2=beat.boxes[cid];
      overrides[cid]={x:pa.x+(pb2.x-pa.x)*q, y:pa.y+(pb2.y-pa.y)*q,
                      w:pa.w+(pb2.w-pa.w)*q, h:pa.h+(pb2.h-pa.h)*q};}
  }
  drawBeat(sctx,beat,t,null,overrides);
  if(q<1&&hasPrev){sctx.globalAlpha=1-q;sctx.drawImage(pcv,0,0);sctx.globalAlpha=1;}
  let z=1; const cam=beat.camera||{};
  if(cam.mode==="push_in"){const dur=beat.end-beat.start;
    z=1+0.06*clamp01((t-beat.start-0.45*dur)/(0.35*dur));}
  ctx.clearRect(0,0,W,H);
  ctx.save();ctx.translate(W/2,H/2);ctx.scale(z,z);ctx.translate(-W/2,-H/2);
  ctx.drawImage(scene,0,0);ctx.restore();
  applyGrade(ctx); // 暗角 + 遮幅（颗粒仅光栅端）
  requestAnimationFrame(render);
}

let T0=0;
Promise.all(loads).then(function(){
  ensureGrade();
  T0=performance.now();
  requestAnimationFrame(render);
});
</script>
</body>
</html>
"""


def _payload(dsl, render_plan, entrance):
    """合并三层产物为播放器数据（boxes/fonts 来自构图层，lifecycle/events
    来自编排层，元素语义来自 DSL）。v4.2 起附带 slot 与 colorRole，
    供排版分层（衬线/字距/柔光）使用。"""
    plans = {b["beat_id"]: b for b in render_plan["beats"]}
    ents = {b["beat_id"]: b for b in entrance["beats"]}
    beats = []
    for b in dsl["beats"]:
        bid = b["beat_id"]
        p, e = plans[bid], ents[bid]
        els = []
        for el in b["elements"]:
            d = {"id": el["id"], "type": el["type"], "role": el["role"],
                 "slot": el.get("slot", ""),
                 "colorRole": el.get("color_role", "ink"),
                 "color": THEME["ink"] if el.get("color_role") == "ink" else
                 THEME["muted"] if el.get("color_role") == "neutral" else
                 COLORS.get(el.get("color_role", "ink"), THEME["ink"])}
            for k in ("motif", "art", "text", "tone", "boxed", "emphasis"):
                if k in el:
                    d[k] = el[k]
            if el["type"] == "chart":
                d["chart"] = el["chart"]
            els.append(d)
        beats.append({"id": bid, "start": b["start_sec"], "end": b["end_sec"],
                      "narration": b["narration"],
                      "palette": b.get("palette", "night"),
                      "camera": b.get("camera", {}),
                      "elements": els,
                      "boxes": p["boxes"], "fonts": p["fonts"],
                      "lifecycle": e["lifecycle"], "events": e["events"]})
    return beats


def compile(dsl, render_plan, entrance, title, out_dir):
    """编译为自包含 index.html（产物只读，修改请回到上游 DSL 层）。"""
    ensure_dir(out_dir)
    beats = _payload(dsl, render_plan, entrance)
    html = (_TEMPLATE
            .replace("__TITLE__", title)
            .replace("__W__", str(W))
            .replace("__H__", str(H))
            .replace("__COLORS__", json.dumps(COLORS))
            .replace("__THEME__", json.dumps(dict(
                THEME,
                vignette_inner=_grade.VIGNETTE_INNER_RATIO,
                letterbox_px=_grade.letterbox_px(H, THEME))))
            .replace("__PALETTES__", json.dumps(PALETTES))
            .replace("__ARTS__", json.dumps(svg_art.ART))
            .replace("__BEATS__", json.dumps(beats, ensure_ascii=False)))
    path = os.path.join(out_dir, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path
