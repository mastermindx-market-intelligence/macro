"""Bounded anonymous cold-load geometry trace; no product DOM/CSS mutation."""
from pathlib import Path
import json, hashlib, subprocess
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"research/intraday_flow_design_upgrade/startup_geometry_resume.json"
PROBE=r"""
(() => {
  window.__iftGeometry=[]; window.__iftShifts=[];
  function rect(s){const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,b:r.bottom,cls:e.className};}
  let last="", frames=0;
  function sample(){
    const g={nav:rect(".site-nav"),search:rect(".nav-search"),main:rect("#main-content"),header:rect(".ift-page-header"),stages:rect(".ift-overview")};
    const key=JSON.stringify(g);
    if(key!==last&&window.__iftGeometry.length<45){window.__iftGeometry.push({t:performance.now(),ready:document.readyState,fonts:document.fonts.status,...g});last=key;}
    if(frames++<180)requestAnimationFrame(sample);
  }
  requestAnimationFrame(sample);
  new PerformanceObserver(list=>{for(const e of list.getEntries()){if(!e.hadRecentInput)window.__iftShifts.push({t:e.startTime,value:e.value,sources:(e.sources||[]).map(s=>({tag:s.node&&s.node.tagName,id:s.node&&s.node.id,cls:s.node&&s.node.className,previous:s.previousRect.toJSON(),current:s.currentRect.toJSON()}))});}}).observe({type:"layout-shift",buffered:true});
})();
"""
rows=[]
with sync_playwright() as p:
    browser=p.chromium.launch()
    for width in (1440,390):
        c=browser.new_context(viewport={"width":width,"height":900 if width==1440 else 844},reduced_motion="reduce")
        c.add_init_script("localStorage.setItem('theme','light');localStorage.removeItem('themeAuto');localStorage.setItem('lang','en');")
        c.add_init_script(PROBE)
        page=c.new_page()
        page.goto("http://127.0.0.1:8767/intraday_flow.html",wait_until="networkidle")
        page.wait_for_timeout(1800)
        d=page.evaluate("({geometry:window.__iftGeometry,shifts:window.__iftShifts})")
        d["viewport"]=width
        d["cls_sum"]=sum(x["value"] for x in d["shifts"])
        rows.append(d)
        print(json.dumps({"viewport":width,"cls_sum":d["cls_sum"],"geometry_states":len(d["geometry"]),"shift_count":len(d["shifts"])}),flush=True)
        c.close()
    browser.close()
doc={"evidence_kind":"anonymous_lab_cold_load_geometry","head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"page_sha256":hashlib.sha256((ROOT/"site/intraday_flow.html").read_bytes()).hexdigest(),"working_tree_note":"HTML includes canonical make_optimizer asset-version/defer/preload normalization after the head commit; no product stylesheet or model change.","cases":rows}
OUT.write_text(json.dumps(doc,indent=2)+"\n")
print(str(OUT))
