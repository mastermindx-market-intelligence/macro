#!/usr/bin/env python3
"""Compare query-only Theme rendering with the accepted renderer on real assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from playwright.sync_api import sync_playwright
from scripts.verify_us_heatmap_return_browser import Handler, Server, SITE, KEY
from scripts.verify_us_heatmap_lifecycle_browser import list_ready, settle

BASE = "3acd4fb0efe00793fc9987f1a6e45a512b26e5dd"
PROJECTION = """key => {
  const root=document.querySelector('#heatmap-full'),tm=root.querySelector('.hm-tm');
  const text=e=>(e?.textContent||'').replace(/\\s+/g,' ').trim();
  const view=history.state?.[key]?.views?.themes||{};
  return {
    rows:[...tm.querySelectorAll('[data-hm-key]')].map(e=>({
      key:e.getAttribute('data-hm-key'),group:e.getAttribute('data-hm-group'),
      text:text(e),href:e.getAttribute('href'),open:e.matches('summary')?e.parentElement.open:null
    })),
    headers:[...tm.querySelectorAll('.hm-mhd')].map(e=>text(e)),
    empty:text(tm.querySelector('.hm-empty')),status:text(root.querySelector('.hm-list-status')),
    summary:text(root.querySelector('.hx-stats')),
    controls:{tf:view.tf,sort:view.sort,query:view.query,presentation:view.presentation,expanded:[...(view.expanded||[])].sort()},
    focus:document.activeElement?.getAttribute('data-hm-key')
  };
}"""

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,default=ROOT/"ux-evidence/d04-us-heatmap-return-20261104/list-reuse")
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    baseline=subprocess.check_output(["git","show",BASE+":templates/heatmap.js"],cwd=ROOT,text=True)
    candidate=(ROOT/"templates/heatmap.js").read_text()
    assert candidate==(ROOT/"site/heatmap.js").read_text()
    server=Server(("127.0.0.1",0),Handler);server.reset();server.snapshot=True
    server.payloads={k:json.loads((SITE/f"marketdata/{k}_heatmap.json").read_text()) for k in ("sp500","themes")}
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    origin=f"http://127.0.0.1:{server.server_port}"
    theme=server.payloads["themes"]["tiles"][0]
    queries=["a","ap","aapl","",theme["t"],"",theme.get("name_zh","半导体")[:2],"no-such-company",""]
    report={"schema":"d04.us_theme_query_reuse.v1","observed_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "baseline_commit":BASE,"baseline_js_sha256":hashlib.sha256(baseline.encode()).hexdigest(),
        "source_sha256":{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in
            ("templates/heatmap.js","site/heatmap.js","site/sector_heatmap.html","scripts/verify_us_heatmap_list_reuse_browser.py")},
        "method":"Reference context intercepts only heatmap.js with accepted baseline bytes; candidate uses the actual generated page and served assets. Same committed public-shaped snapshots and all other assets. Compare rendered row identities/order/text/links, group counts, empty/summary state and selected control state.",
        "limitations":["Local Chromium comparison, not production destination/auth, field performance or whole-D04 acceptance.",
            "No memory-retention conclusion from locator-driven parity contexts; use the separate clean by-value CDP probe.",
            "Refresh notification verifies full-render invalidation with the same supplied snapshot; it is not live-feed freshness proof."],
        "contexts":[],"failures":[]}
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=["--disable-features=BackForwardCache"])
            report["browser"]=browser.version
            for width,lang,theme_name in [(1440,"en","dark"),(390,"zh","light"),(320,"en","light")]:
                observations={}
                result={"width":width,"lang":lang,"theme":theme_name,"variants":{},"comparisons":[]}
                for variant in ("reference","candidate"):
                    errors=[]
                    ctx=browser.new_context(viewport={"width":width,"height":900 if width>560 else 844},
                        reduced_motion="reduce",has_touch=width<=560,is_mobile=width<=560)
                    def route(r):
                        u=urlsplit(r.request.url)
                        if u.netloc!=urlsplit(origin).netloc:r.abort()
                        elif variant=="reference" and u.path=="/heatmap.js":
                            r.fulfill(status=200,content_type="application/javascript",body=baseline)
                        else:r.continue_()
                    ctx.route("**/*",route)
                    ctx.add_init_script("localStorage.setItem('theme',"+json.dumps(theme_name)+");localStorage.setItem('lang',"+json.dumps(lang)+");")
                    page=ctx.new_page();page.on("pageerror",lambda e:errors.append(str(e)))
                    with page.expect_response(lambda r:urlsplit(r.url).path=="/heatmap.js") as incoming:
                        page.goto(origin+"/sector_heatmap.html",wait_until="domcontentloaded")
                    served=hashlib.sha256(incoming.value.body()).hexdigest()
                    expected=report["baseline_js_sha256"] if variant=="reference" else report["source_sha256"]["templates/heatmap.js"]
                    assert served==expected
                    page.locator('[data-hm-map="themes"]').click()
                    list_ready(page,"themes",len(server.payloads["themes"]["tiles"]))
                    states={}
                    def save(label):
                        settle(page);states[label]=page.evaluate(PROJECTION,KEY)
                    def query(q,label):
                        page.locator(".hm-search input").fill(q);save(label)
                    save("initial")
                    for i,q in enumerate(queries):
                        query(q,f"query-{i}")
                        if q=="aapl" and variant=="candidate":
                            name=f"reuse-{width}-{lang}-{theme_name}.png"
                            page.screenshot(path=str(args.out/name));result["screenshot"]=name
                    page.evaluate("document.querySelectorAll('details.hm-members').forEach(e=>{e.open=true})")
                    page.wait_for_function("k=>(history.state[k]?.views.themes?.expanded.length||0)===document.querySelectorAll('details.hm-members').length",arg=KEY)
                    for i,q in enumerate(["a","","aapl",""]):query(q,f"expanded-{i}")
                    page.locator(".hm-tfs button:not([disabled])").last.click();save("timeframe")
                    query("aapl","timeframe-query");query("","timeframe-clear")
                    page.locator('.hm-sort [data-s="az"]').click();save("sort")
                    query("a","sort-query");query("","sort-clear")
                    page.evaluate("document.documentElement.dataset.theme='dark';document.dispatchEvent(new Event('themechange'))")
                    save("theme");query("aapl","theme-query");query("","theme-clear")
                    page.evaluate("document.documentElement.dataset.lang='zh';document.dispatchEvent(new Event('langchange'))")
                    save("language");query("aapl","language-query");query("","language-clear")
                    page.evaluate("document.dispatchEvent(new CustomEvent('hm-refresh'))")
                    save("refresh");query("aapl","refresh-query");query("","refresh-clear")
                    page.evaluate("""() => {
                      window.__d04ProbeRow=[...document.querySelectorAll('.hm-member-row')].find(e=>JSON.parse(e.getAttribute('data-hm-key'))[1]==='AAPL');
                      const row=window.__d04ProbeRow;row.closest('details').open=true;
                    }""")
                    settle(page)
                    key=page.evaluate("window.__d04ProbeRow.getAttribute('data-hm-key')")
                    page.evaluate("""() => {
                      window.__d04ProbeRow.focus({preventScroll:true});
                      const input=document.querySelector('.hm-search input');input.value='aapl';input.dispatchEvent(new Event('input',{bubbles:true}));
                    }""")
                    save("logical-focus")
                    identity=page.evaluate("window.__d04ProbeRow.isConnected && document.activeElement===window.__d04ProbeRow")
                    focus_ok=states["logical-focus"]["focus"]==key
                    observations[variant]=states
                    result["variants"][variant]={"steps":len(states),"page_errors":errors,
                        "served_script_sha256":served,"script_url":incoming.value.url,"logical_focus_preserved":focus_ok,
                        "original_matching_row_and_focus_retained":identity}
                    if errors or not focus_ok or (variant=="candidate" and not identity):
                        report["failures"].append({"width":width,"variant":variant,"page_errors":errors,"focus_ok":focus_ok,"identity":identity})
                    ctx.close()
                for label,reference in observations["reference"].items():
                    current=observations["candidate"][label];same=reference==current
                    result["comparisons"].append({"step":label,"same":same,"rows":len(current["rows"]),
                        "reference_sha256":digest(reference),"candidate_sha256":digest(current)})
                    if not same:
                        differing=[k for k in reference if reference[k]!=current[k]]
                        report["failures"].append({"width":width,"step":label,"fields":differing,
                            "reference_controls":reference["controls"],"candidate_controls":current["controls"]})
                report["contexts"].append(result)
                (args.out/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
                print(json.dumps({"width":width,"comparisons":len(result["comparisons"]),
                    "equal":sum(x["same"] for x in result["comparisons"]),"failures_so_far":len(report["failures"])}),flush=True)
            browser.close()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
    report["all_passed"]=not report["failures"]
    (args.out/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"report":str(args.out/"report.json"),"all_passed":report["all_passed"]}),flush=True)
    return 0 if report["all_passed"] else 1

if __name__=="__main__":
    raise SystemExit(main())
