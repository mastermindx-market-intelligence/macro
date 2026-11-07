#!/usr/bin/env python3
"""Finite local density/lifecycle probe; timings are lab observations, not field Web Vitals."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from playwright.sync_api import expect, sync_playwright
from scripts.verify_us_heatmap_return_browser import Handler, Server, SITE, KEY

INSTRUMENT = r"""
(() => {
  const p = window.__d04Perf = {actions:[], arm:null, adds:0, removes:0, writes:0, boxes:0, htmlWrites:0, htmlMs:0, longtasks:[]};
  const add = document.addEventListener.bind(document), remove = document.removeEventListener.bind(document);
  document.addEventListener = function(n,...a){if(n==='hm-refresh')p.adds++;return add(n,...a)};
  document.removeEventListener = function(n,...a){if(n==='hm-refresh')p.removes++;return remove(n,...a)};
  const replace = history.replaceState.bind(history);
  history.replaceState = function(...a){p.writes++;return replace(...a)};
  const box = Element.prototype.getBoundingClientRect;
  Element.prototype.getBoundingClientRect = function(...a){
    if(this.hasAttribute('data-hm-key'))p.boxes++;
    return box.apply(this,a);
  };
  const html=Object.getOwnPropertyDescriptor(Element.prototype,'innerHTML');
  Object.defineProperty(Element.prototype,'innerHTML',{...html,set(value){
    const owned=this.classList.contains('hm-tm'),start=performance.now();
    try{html.set.call(this,value)}finally{if(owned){p.htmlWrites++;p.htmlMs+=performance.now()-start}}
  }});
  const intervals=new Set(), interval=window.setInterval.bind(window), clear=window.clearInterval.bind(window);
  window.setInterval=function(...a){const id=interval(...a);intervals.add(id);return id};
  window.clearInterval=function(id){intervals.delete(id);return clear(id)};
  p.sample=()=>({hm_refresh_listeners:p.adds-p.removes,hm_adds:p.adds,hm_removes:p.removes,
    active_intervals:intervals.size,dom_elements:document.querySelectorAll('*').length,
    heatmap_nodes:document.querySelectorAll('#heatmap-full *').length,
    keyed_rows:document.querySelectorAll('#heatmap-full [data-hm-key]').length,
    frame_count:document.querySelectorAll('#mm-terminal-overlay iframe').length,
    history_writes:p.writes,box_reads:p.boxes});
  for(const type of ['input','click'])add(type,event=>{
    const arm=p.arm;
    if(!arm||arm.type!==type||!event.target.closest(arm.selector))return;
    p.arm=null;
    const t=performance.now(),writes=p.writes,boxes=p.boxes,htmlWrites=p.htmlWrites,htmlMs=p.htmlMs;
    queueMicrotask(()=>requestAnimationFrame(()=>requestAnimationFrame(()=>{
      p.actions.push({label:arm.label,event:type,next_frame_ms:performance.now()-t,
        history_writes:p.writes-writes,keyed_box_reads:p.boxes-boxes,
        list_html_writes:p.htmlWrites-htmlWrites,list_html_ms:p.htmlMs-htmlMs});
    })));
  },true);
  try{new PerformanceObserver(list=>p.longtasks.push(...list.getEntries().map(e=>({start_ms:e.startTime,duration_ms:e.duration})))).observe({type:'longtask',buffered:true})}catch(e){}
  const observer=new MutationObserver(()=>{
    if(document.querySelector('#heatmap-full [data-hm-key]')){
      observer.disconnect();
      requestAnimationFrame(()=>requestAnimationFrame(()=>{p.first_heatmap_frame_ms=performance.now()}));
    }
  });
  observer.observe(document,{subtree:true,childList:true});
})();
"""

def settle(page):
    page.evaluate("() => new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")

def action(page, selector, label, value=None, cdp=None):
    metrics_before={x['name']:x['value'] for x in cdp.send("Performance.getMetrics")['metrics']} if cdp else {}
    before=page.evaluate("window.__d04Perf.actions.length")
    page.evaluate("a=>{window.__d04Perf.arm=a}", {
        "selector":selector,"label":label,"type":"input" if value is not None else "click"})
    if value is None:
        page.locator(selector).click()
    else:
        page.locator(selector).fill(value)
    page.wait_for_function("n=>window.__d04Perf.actions.length>n",arg=before)
    result=page.evaluate("window.__d04Perf.actions.at(-1)")
    if cdp:
        metrics_after={x['name']:x['value'] for x in cdp.send("Performance.getMetrics")['metrics']}
        result["browser_duration_delta_ms"]={key:1000*(metrics_after.get(key,0)-metrics_before.get(key,0))
            for key in ("ScriptDuration","LayoutDuration","RecalcStyleDuration","TaskDuration")}
    return result

def list_ready(page, key, expected):
    expect(page.locator(f'[data-hm-map="{key}"]')).to_have_attribute("aria-selected","true")
    page.locator("#heatmap-full [data-hm-key]").first.wait_for()
    page.locator(".hm-search input").wait_for(state="visible")
    if page.locator('[data-hm-presentation="list"]').is_visible():
        page.locator('[data-hm-presentation="list"]').click()
    selector='.hm-tm details.hm-members' if key=="themes" else '.hm-tm a.hm-mrow'
    expect(page.locator(selector)).to_have_count(expected)
    settle(page)

def overlay(page):
    link=page.locator('.hm-tm a.hm-mrow').first
    link.focus()
    before=link.get_attribute('data-hm-key')
    link.press("Enter")
    page.wait_for_function("window.MDXTerminalOverlay && window.MDXTerminalOverlay.isOpen() && document.querySelector('#mm-terminal-overlay').classList.contains('is-ready')")
    page.wait_for_timeout(220)
    page.evaluate("history.back()")
    page.wait_for_function("!window.MDXTerminalOverlay.isOpen() && !history.state?.__mdxTerminalOverlay")
    page.wait_for_timeout(110)
    assert page.locator('.hm-tm a.hm-mrow').first.get_attribute('data-hm-key')==before
    assert page.evaluate("!document.documentElement.classList.contains('mm-terminal-lock')")
    settle(page)

def snapshot(page, cdp, label, requests):
    settle(page)
    # The retaining-path diagnostic found old rows rooted by DevTools console.
    # Release debugger-owned console handles before measuring application retention.
    cdp.send("Runtime.discardConsoleEntries")
    cdp.send("HeapProfiler.collectGarbage")
    stats=page.evaluate("window.__d04Perf.sample()")
    stats.update(cdp.send("Memory.getDOMCounters"))
    stats["retired_tm_collected"]=page.evaluate("window.__d04OldTm ? window.__d04OldTm.deref()===undefined : null")
    metrics={x['name']:x['value'] for x in cdp.send("Performance.getMetrics")['metrics']}
    stats.update(label=label,js_heap_used_bytes=metrics.get("JSHeapUsedSize"),
                 heatmap_requests={key:sum(f"/marketdata/{key}_heatmap.json" in x for x in requests) for key in ("sp500","themes")})
    return stats


def clean_retention(page, cdp, origin, width, cycles, skip_overlay, requests):
    """Profile collection without locator/expect target handles retained by the driver."""
    cdp.send("Page.enable"); cdp.send("Runtime.enable")
    cdp.send("Page.navigate", {"url": origin + "/sector_heatmap.html"})
    def ev(expression):
        result=cdp.send("Runtime.evaluate",{"expression":expression,"returnByValue":True,"awaitPromise":True})
        assert "exceptionDetails" not in result,result
        return result["result"].get("value")
    ev("""window.__d04Wait=predicate=>new Promise((resolve,reject)=>{
      const timeout=setTimeout(()=>{clearInterval(timer);reject(Error('Heatmap state unavailable'))},15000);
      const timer=setInterval(()=>{if(predicate()){clearInterval(timer);clearTimeout(timeout);resolve(true)}},16)
    });__d04Wait(()=>document.querySelector('#heatmap-full [data-hm-key]'))""")
    ev("""window.__d04SelectClean=async function(key){
      document.querySelector('[data-hm-map="'+key+'"]').click();
      await __d04Wait(()=>document.querySelector('.hm-search input')&&document.querySelector('#heatmap-full [data-hm-key]'));
      const button=document.querySelector('[data-hm-presentation="list"]');
      if(button.getClientRects().length)button.click();
      await __d04Wait(()=>document.querySelectorAll(key==='themes'?'.hm-tm details.hm-members':'.hm-tm a.hm-mrow').length===(key==='themes'?268:503));
      await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
      return true;
    };window.__d04OverlayClean=async function(){
      document.querySelector('.hm-tm a.hm-mrow').click();
      await __d04Wait(()=>window.MDXTerminalOverlay&&MDXTerminalOverlay.isOpen()&&document.querySelector('#mm-terminal-overlay').classList.contains('is-ready'));
      await new Promise(r=>setTimeout(r,220));
      history.back();
      await __d04Wait(()=>!MDXTerminalOverlay.isOpen()&&!history.state?.__mdxTerminalOverlay);
      await new Promise(r=>setTimeout(r,330));
      return !document.documentElement.classList.contains('mm-terminal-lock');
    };true""")
    def select(key):ev("__d04SelectClean("+json.dumps(key)+")")
    def close_round():
        if not skip_overlay:assert ev("__d04OverlayClean()")
    samples=[]
    def snap(label):
        cdp.send("Runtime.discardConsoleEntries");cdp.send("HeapProfiler.collectGarbage")
        value=cdp.send("Memory.getDOMCounters")
        value.update(ev("({live:document.querySelectorAll('*').length,heatmap_nodes:document.querySelectorAll('#heatmap-full *').length,keyed_rows:document.querySelectorAll('#heatmap-full [data-hm-key]').length,frame_count:document.querySelectorAll('#mm-terminal-overlay iframe').length,retired_tm_collected:window.__d04OldTm?window.__d04OldTm.deref()===undefined:null})"))
        metrics={x["name"]:x["value"] for x in cdp.send("Performance.getMetrics")["metrics"]}
        value.update(label=label,js_heap_used_bytes=metrics.get("JSHeapUsedSize"),
            heatmap_requests={key:sum(f"/marketdata/{key}_heatmap.json" in x for x in requests) for key in ("sp500","themes")})
        samples.append(value)
    select("sp500");select("themes");select("sp500");close_round();snap("warmed")
    ev("(()=>{window.__d04OldTm=new WeakRef(document.querySelector('.hm-tm'))})()")
    for cycle in range(1,cycles+1):
        select("themes");select("sp500");close_round()
        if cycle in {1,cycles//2,cycles}:snap(f"cycle-{cycle}")
    base,end=samples[0],samples[-1]
    return {"width":width,"method":"CDP by-value document actions; no Playwright locator/expect target handles or event/timing wrappers. Controlled Terminal fixture when enabled; programmatic actions are lifecycle proof, not new trusted-input acceptance.",
        "lifecycle":samples,"lifecycle_deltas":{k:end[k]-base[k] for k in ("live","heatmap_nodes","documents","nodes","jsEventListeners","js_heap_used_bytes")},
        "invariants":{"stable_live_heatmap_nodes":all(v["heatmap_nodes"]==base["heatmap_nodes"] for v in samples),
            "retired_view_collected":all(v["retired_tm_collected"] for v in samples[1:]),
            "no_retained_dom_growth":all(v["nodes"]<=base["nodes"]+16 for v in samples[1:]),
            "no_event_listener_growth":all(v["jsEventListeners"]<=base["jsEventListeners"] for v in samples[1:]),
            "no_extra_heatmap_requests":end["heatmap_requests"]==base["heatmap_requests"]}}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,default=ROOT/"ux-evidence/d04-us-heatmap-return-20261104/performance-report.json")
    parser.add_argument("--widths",type=int,nargs="+",default=[1440,390,320])
    parser.add_argument("--cycles",type=int,default=8)
    parser.add_argument("--cpu-rate",type=float,default=4)
    parser.add_argument("--skip-overlay",action="store_true")
    parser.add_argument("--retention-only",action="store_true")
    args=parser.parse_args()
    assert args.cycles>0 and args.cpu_rate>=1
    server=Server(("127.0.0.1",0),Handler); server.reset(); server.snapshot=True
    server.payloads={key:json.loads((SITE/f"marketdata/{key}_heatmap.json").read_text()) for key in ("sp500","themes")}
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    origin=f"http://127.0.0.1:{server.server_port}"
    report={"schema":"d04.us_heatmap_lifecycle.v1","mode":"clean-retention" if args.retention_only else "instrumented-timing","observed_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "source_sha256":{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in
            ("templates/heatmap.js","site/heatmap.js","templates/sector_heatmap.html.j2","site/sector_heatmap.html","scripts/verify_us_heatmap_lifecycle_browser.py")},
        "environment":{"os":platform.mac_ver()[0],"machine":platform.machine(),
            "cpu":subprocess.check_output(["sysctl","-n","machdep.cpu.brand_string"],text=True).strip(),
            "cpu_throttle_rate":args.cpu_rate,"overlay_round_trips":not args.skip_overlay,"network":"loopback, no network throttling; external requests blocked",
            "terminal_fixture":"Existing MM_TERMINAL_BASE configured to match committed app-origin links; that origin is fulfilled by a labelled fixture without network/account/data access."},
        "method":"Input/click capture to second animation frame; real generated assets and committed snapshots. CDP counters at identical warmed S&P List state after discarding debugger console handles and forced GC. Diagnostic wrappers count history writes, keyed geometry reads, refresh listeners, intervals and list innerHTML assignment duration. Per-action CDP script/layout/style/task deltas include driver input preparation and must not be summed with overlapping event/assignment measurements.",
        "limitations":["Local instrumented lab proxy, not field INP/LCP/CLS, physical devices, production Terminal, sustained polling cadence or whole A063 acceptance.",
            "CPU throttling is a controlled stress condition, not an equivalence to named hardware.","Bounded-cycle counters cannot prove absence of every memory leak."],
        "data":{k:{"tiles":len(v['tiles']),"member_contexts":sum(len(t.get('members',[])) for t in v['tiles']),"asof":v.get("asof"),"source":v.get("source")} for k,v in server.payloads.items()},
        "viewports":[]}
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=["--disable-features=BackForwardCache"])
            report["environment"]["browser"]=browser.version
            for width in args.widths:
                errors=[]; console_events=[]
                ctx=browser.new_context(viewport={"width":width,"height":900 if width>560 else 844},
                    locale="en-US",reduced_motion="reduce",has_touch=width<=560,is_mobile=width<=560)
                fixture="""<!doctype html><html><title>D04 controlled Terminal lifecycle fixture</title><body>
                    <h1>Controlled symbol destination; no account or market data</h1><script>
                    const target=PARENT;function ready(){parent.postMessage({source:'mastermind-terminal',type:'terminal:visual-ready',path:'/terminal',symbol:new URLSearchParams(location.search).get('symbol')||new URLSearchParams(location.search).get('sym')||''},target)}
                    addEventListener('message',e=>{if(e.source===parent&&e.origin===target&&e.data?.source==='mastermind-dashboard'&&e.data.type==='terminal:set-symbol')ready()});ready();
                    </script></body></html>""".replace("PARENT",json.dumps(origin))
                def route(r):
                    u=urlsplit(r.request.url)
                    if u.netloc==urlsplit(origin).netloc:r.continue_()
                    elif u.netloc=="app.mastermind-x.com" and u.path=="/terminal":r.fulfill(status=200,content_type="text/html",body=fixture)
                    else:r.abort()
                ctx.route("**/*",route)
                ctx.add_init_script("window.MM_TERMINAL_BASE='https://app.mastermind-x.com/terminal';localStorage.setItem('theme','dark');localStorage.setItem('lang','en');"+("" if args.retention_only else INSTRUMENT))
                page=ctx.new_page();page.on("pageerror",lambda e:errors.append(str(e)))
                page.on("console",lambda m:console_events.append({"type":m.type,"text":m.text[:500]}))
                cdp=ctx.new_cdp_session(page);cdp.send("Performance.enable")
                cdp.send("Emulation.setCPUThrottlingRate",{"rate":args.cpu_rate})
                if args.retention_only:
                    result=clean_retention(page,cdp,origin,width,args.cycles,args.skip_overlay,server.requests_seen)
                    result["page_errors"]=errors
                    result["invariants"]["no_page_errors"]=not errors
                    report["viewports"].append(result)
                    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2)+"\n")
                    print(json.dumps({"width":width,"retention_deltas":result["lifecycle_deltas"],"invariants":result["invariants"]}),flush=True)
                    ctx.close()
                    continue
                page.goto(origin+"/sector_heatmap.html",wait_until="domcontentloaded")
                page.locator('#heatmap-full [data-hm-key]').first.wait_for()
                page.wait_for_function("!!window.__d04Perf.first_heatmap_frame_ms")
                result={"width":width,"initial_heatmap_frame_ms":page.evaluate("window.__d04Perf.first_heatmap_frame_ms"),"actions":[],"lifecycle":[]}
                for key in ("sp500","themes"):
                    page.locator(f'[data-hm-map="{key}"]').click()
                    list_ready(page,key,len(server.payloads[key]["tiles"]))
                    for query in ("a","ap","aapl","","technology","no-such-company",""):
                        result["actions"].append(action(page,'.hm-search input',f"{key}:query:{query or 'clear'}",query,cdp))
                    list_ready(page,key,len(server.payloads[key]["tiles"]))
                    if key=="themes":
                        assert page.locator('.hm-member-row').count()==report["data"]["themes"]["member_contexts"]
                        page.evaluate("document.querySelectorAll('details.hm-members').forEach(e=>{e.open=true})")
                        page.wait_for_function("k=>(history.state[k]?.views.themes?.expanded.length||0)===document.querySelectorAll('details.hm-members').length",arg=KEY)
                        settle(page)
                        for query in ("a",""):
                            result["actions"].append(action(page,'.hm-search input',f"themes-expanded:query:{query or 'clear'}",query,cdp))
                        page.evaluate("document.querySelectorAll('details.hm-members').forEach(e=>{e.open=false})")
                        page.wait_for_function("k=>(history.state[k]?.views.themes?.expanded.length||0)===0",arg=KEY)
                    if width>560:
                        result["actions"].append(action(page,'[data-hm-presentation="map"]',f"{key}:show-map",cdp=cdp))
                        result["actions"].append(action(page,'[data-hm-presentation="list"]',f"{key}:show-list",cdp=cdp))
                page.locator('[data-hm-map="sp500"]').click();list_ready(page,"sp500",503)
                if not args.skip_overlay:overlay(page)
                result["lifecycle"].append(snapshot(page,cdp,"warmed",server.requests_seen))
                page.evaluate("window.__d04OldTm=new WeakRef(document.querySelector('.hm-tm'))")
                for cycle in range(1,args.cycles+1):
                    result["actions"].append(action(page,'[data-hm-map="themes"]',"cycle:themes",cdp=cdp))
                    list_ready(page,"themes",268)
                    result["actions"].append(action(page,'[data-hm-map="sp500"]',"cycle:sp500",cdp=cdp))
                    list_ready(page,"sp500",503)
                    if not args.skip_overlay:overlay(page)
                    if cycle in {1,args.cycles//2,args.cycles}:
                        result["lifecycle"].append(snapshot(page,cdp,f"cycle-{cycle}",server.requests_seen))
                result["retired_tm_collected"]=page.evaluate("window.__d04OldTm.deref()===undefined")
                result["page_errors"]=errors
                result["console_events"]=console_events
                result["longtasks"]=page.evaluate("window.__d04Perf.longtasks")
                result["timing_summary"]={"samples":len(result["actions"]),
                    "median_next_frame_ms":statistics.median(a["next_frame_ms"] for a in result["actions"]),
                    "maximum_next_frame_ms":max(a["next_frame_ms"] for a in result["actions"])}
                base,end=result["lifecycle"][0],result["lifecycle"][-1]
                result["lifecycle_deltas"]={k:end[k]-base[k] for k in
                    ("hm_refresh_listeners","active_intervals","dom_elements","heatmap_nodes","documents","nodes","jsEventListeners","js_heap_used_bytes")}
                result["invariants"]={"one_live_heatmap_refresh_listener":all(s["hm_refresh_listeners"]==1 for s in result["lifecycle"]),
                    "stable_intervals":all(s["active_intervals"]==base["active_intervals"] for s in result["lifecycle"]),
                    "stable_live_heatmap_nodes":all(s["heatmap_nodes"]==base["heatmap_nodes"] for s in result["lifecycle"]),
                    "no_extra_heatmap_requests":end["heatmap_requests"]==base["heatmap_requests"],
                    "no_page_errors":not errors}
                result["retention_qualification"]="UNQUALIFIED: locator/expect actions retain targets under DevTools console in the measured driver. Use --retention-only for clean by-value collection proof; raw counters are retained here."

                report["viewports"].append(result)
                args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2)+"\n")
                print(json.dumps({"width":width,"timing":result["timing_summary"],"deltas":result["lifecycle_deltas"],"invariants":result["invariants"]}),flush=True)
                ctx.close()
            browser.close()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
    report["all_invariants_passed"]=all(all(v["invariants"].values()) for v in report["viewports"])
    args.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"report":str(args.out),"all_invariants_passed":report["all_invariants_passed"]}),flush=True)
    return 0 if report["all_invariants_passed"] else 1

if __name__=="__main__":
    raise SystemExit(main())
