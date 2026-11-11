from pathlib import Path
import sys
from datetime import date, timedelta

# Regenerate in macro at the source pin recorded in BUILD_CONTRACT.md.
repo = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo))
from lib.illus import illus

base = Path(__file__).parent
dates = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(18)]
values = [18, 22, 20, 26, 24, 32, 35, 31, 38, 40, 36, 45, 48, 44, 51, 53, 50, 56]
figure = illus({"dates": dates, "vals": values}, kind="area", height=260,
    accent="var(--ink)", value_fmt="{:.0f}", unit_en="demo points",
    aria_en="Illustrative design fixture, rising from 18 to 56 demo points. Not market data.")
empty = illus({"dates": [], "vals": []}, kind="line", height=260,
    aria_en="No history yet. No values are plotted.")
html = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mastermind · Motion and state specimen</title>
<style>
@@CSS@@
:root{color-scheme:dark;--bg:#080808;--panel:#121212;--line:#292929;--text:#F3F3F3;--muted:#B8B8B8;--quiet:#949494;--ink:#A8C2AD;--up:#A8C2AD;--down:#DEA4A5;--info:#A7B4C2;--warn:#C9B99B}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 Inter,system-ui,sans-serif}
button,input{font:inherit}button{cursor:pointer;min-height:44px;border:1px solid var(--line);border-radius:9px;padding:10px 17px;background:var(--panel);color:var(--text)}
button:hover{background:#222}button:focus-visible,a:focus-visible,input:focus-visible{outline:2px solid #C9B99B;outline-offset:4px}
button:disabled{cursor:default;opacity:.55}a{color:#C9B99B}main{max-width:1200px;margin:auto;padding:42px 36px 80px}
.brand{display:flex;justify-content:space-between;gap:20px;border-bottom:1px solid var(--line);padding-bottom:24px;font-size:13px;letter-spacing:.12em}
.brand span:last-child{color:var(--quiet);letter-spacing:0}.eyebrow{font-size:12px;letter-spacing:.13em;color:#C9B99B;text-transform:uppercase}
h1{font-size:clamp(36px,5vw,62px);line-height:1.08;letter-spacing:-.045em;max-width:850px;font-weight:550;margin:30px 0 20px}
.lede{max-width:680px;color:var(--muted);font-size:18px;margin:0 0 36px}.toolbar{display:flex;align-items:center;flex-wrap:wrap;gap:14px;justify-content:space-between;margin-bottom:24px}
.tabs{display:flex;padding:4px;gap:4px;border:1px solid var(--line);border-radius:12px}.tabs button{border:0;background:transparent}
.tabs button[aria-pressed="true"]{background:#292929}.controls{display:flex;align-items:center;gap:18px;font-size:14px}.controls label{display:flex;align-items:center;gap:9px;min-height:44px}
.stage{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(250px,1fr);border:1px solid var(--line);border-radius:18px;overflow:hidden}
.figure-panel{padding:30px;min-width:0;background:var(--panel)}.caption{display:flex;justify-content:space-between;gap:16px;font-size:13px;color:var(--quiet)}
.figure-title{font-size:23px;font-weight:550;letter-spacing:-.02em;margin:14px 0 0}.l-zh{display:none!important}.ilx{margin:20px 0 5px!important}
.ilx-empty{font-size:18px;opacity:1}.ilx-tag{font-size:16px}.timing{padding:30px}.step{display:flex;gap:17px;padding:19px 0;border-bottom:1px solid var(--line)}
.step:last-child{border:0}.step b{font-size:14px;font-weight:500;color:#C9B99B}.step h3{font-size:18px;font-weight:550;margin:0 0 6px}.step p{font-size:14px;color:var(--muted);margin:0}.timing .eyebrow{margin-bottom:5px}
.status{min-height:28px;margin-top:16px;color:var(--quiet);font-size:14px}.details{margin-top:30px;border-top:1px solid var(--line);padding-top:24px}
.details-head{display:flex;justify-content:space-between;align-items:center;gap:20px}.details-head h2{font-size:22px;line-height:1.3;font-weight:550;margin:0}
#detailsPanel{padding:24px 0 0;max-width:800px;color:var(--muted)}#detailsPanel p{margin:0 0 15px}
[hidden]{display:none!important}footer{margin-top:42px;color:var(--quiet);font-size:13px;max-width:900px}
body.reduce .ilx *{animation:none!important;transition:none!important}
body.reduce .ilx-path{stroke-dashoffset:0!important;stroke-dasharray:none!important}
body.reduce .ilx-area,body.reduce .ilx-water,body.reduce .ilx-ref,body.reduce .ilx-band,body.reduce .ilx-tag,body.reduce .ilx-d,body.reduce .ilx-reflab,body.reduce .ilx-bandlab,body.reduce .ilx-chips{opacity:1!important}
body.reduce .ilx-dot,body.reduce .ilx-bar{transform:none!important}
@media(max-width:700px){main{padding:24px 20px 54px}.brand{font-size:11px}.brand span:last-child{max-width:120px;text-align:right}.toolbar{align-items:flex-start}.controls{width:100%;justify-content:space-between}.stage{grid-template-columns:1fr}.figure-panel,.timing{padding:23px}.figure-panel{border-bottom:1px solid var(--line)}.caption{flex-wrap:wrap}.details-head{align-items:flex-start}h1{margin-top:30px}.tabs{width:100%}.tabs button{flex:1}}
</style></head><body><main>
<header class="brand"><strong>MASTERMIND</strong><span>DESIGN SPECIMEN · 08 NOV 2026</span></header>
<h1>Motion that carries meaning.</h1>
<p class="lede">A single reveal, then stillness. Missing history stays empty. Reduced motion lands directly on the same final state.</p>
<div class="toolbar">
<div class="tabs" aria-label="Illustration state"><button id="settledButton" aria-pressed="true" data-view="settled">Settled data</button><button id="emptyButton" aria-pressed="false" data-view="empty">Missing history</button></div>
<div class="controls"><button id="replayButton">Replay specimen</button><label><input id="reduceMotion" type="checkbox"> Reduce motion</label></div>
</div>
<section class="stage" aria-label="Signal Ink motion specimen">
<div class="figure-panel">
<div class="caption"><span>SIGNAL INK · EXISTING RENDERER</span><span>Illustrative fixture</span></div>
<h2 class="figure-title" id="figureTitle">One series. One clear arrival.</h2>
<div id="settledPanel">@@SETTLED@@</div><div id="emptyPanel" hidden>@@EMPTY@@</div>
<p class="status" id="status" role="status">Design data only · no live market feed</p>
</div>
<div class="timing"><div class="eyebrow">Choreography</div>
<div class="step"><b>01</b><div><h3>Draw</h3><p>950 ms. The stroke reveals from left to right.</p></div></div>
<div class="step"><b>02</b><div><h3>Reveal the area</h3><p>600 ms. A quiet fill supports the shape.</p></div></div>
<div class="step"><b>03</b><div><h3>Settle</h3><p>The endpoint lands and stays still. No pulse that implies fresh data.</p></div></div>
</div></section>
<section class="details">
<div class="details-head"><h2>How this reaches the product</h2><button id="detailsButton" aria-expanded="false" aria-controls="detailsPanel">Show build notes</button></div>
<div id="detailsPanel" hidden>
<p>Use <code>lib/illus.py</code> with the existing <code>templates/illus.css</code> and <code>templates/illus.js</code>. This file embeds their output from the pinned source; it does not introduce a second chart renderer.</p>
<p>In-page figures reveal once. Opening an evidence dialog may reveal its chart again after the dialog entrance settles. Closing it restores focus to the invoking control. Reduced motion skips the choreography and shows the same final data.</p>
<p>Read the producer’s availability and timestamps before rendering. An empty or insufficient series shows an honest null. Interactive candles, crosshairs and zoom remain on the existing Terminal chart stack.</p>
<p>This specimen uses an explicitly synthetic index to demonstrate motion. It is not a market series, forecast, score, performance result, or live product path.</p>
</div></section>
<footer>Source: Macro <code>338a10852dcefa5d2bd07e5c6be0955c2b1e83fd</code> · <code>docs/ILLUSTRATIONS.md</code><br>Replay is an explicit specimen control. Product charts do not loop. No network requests, account writes or runtime commands are made by this page.</footer>
</main>
<script>@@JS@@</script>
<script>
(function(){
'use strict';
var media=window.matchMedia('(prefers-reduced-motion: reduce)');
var reduce=document.getElementById('reduceMotion');
var replay=document.getElementById('replayButton');
var current='settled';
function reduced(){return media.matches||reduce.checked}
function applyMotion(){
 document.body.classList.toggle('reduce',reduced());
 replay.disabled=current==='empty'||reduced();
 replay.title=reduced()?'Reduced motion shows the final state.':'Replay this design specimen.';
}
reduce.checked=media.matches;
reduce.addEventListener('change',applyMotion);
if(media.addEventListener)media.addEventListener('change',applyMotion);
document.querySelectorAll('[data-view]').forEach(function(button){
 button.addEventListener('click',function(){
 current=button.dataset.view;
 document.querySelectorAll('[data-view]').forEach(function(b){b.setAttribute('aria-pressed',String(b===button))});
 document.getElementById('settledPanel').hidden=current!=='settled';
 document.getElementById('emptyPanel').hidden=current!=='empty';
 document.getElementById('figureTitle').textContent=current==='settled'?'One series. One clear arrival.':'No history yet.';
 document.getElementById('status').textContent=current==='settled'?'Design data only · no live market feed':'No fabricated points, trend or animation.';
 applyMotion();
 if(current==='settled'&&window.ilxReveal)window.ilxReveal(document.getElementById('settledPanel'));
 });
});
replay.addEventListener('click',function(){
 if(replay.disabled)return;
 var figure=document.querySelector('#settledPanel .ilx');
 figure.classList.remove('ilx-in');
 void figure.offsetWidth;
 if(window.ilxReveal)window.ilxReveal(document.getElementById('settledPanel'));
});
var detailButton=document.getElementById('detailsButton'),panel=document.getElementById('detailsPanel');
detailButton.addEventListener('click',function(){
 var open=detailButton.getAttribute('aria-expanded')==='true';
 detailButton.setAttribute('aria-expanded',String(!open));
 detailButton.textContent=open?'Show build notes':'Hide build notes';
 panel.hidden=open;
});
document.addEventListener('keydown',function(e){
 if(e.key==='Escape'&&!panel.hidden){panel.hidden=true;detailButton.setAttribute('aria-expanded','false');detailButton.textContent='Show build notes';detailButton.focus();}
});
applyMotion();
})();
</script></body></html>"""
html=html.replace("@@CSS@@",(repo/"templates"/"illus.css").read_text()).replace("@@JS@@",(repo/"templates"/"illus.js").read_text()).replace("@@SETTLED@@",figure).replace("@@EMPTY@@",empty)
(base/"MOTION_SPECIMEN.html").write_text(html)
print("Built MOTION_SPECIMEN.html:",len(html),"characters")
