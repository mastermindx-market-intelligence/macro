"""Measure first-load layout on the unchanged native public artifact; no account or live-network proof."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse, hashlib, json, sys
from playwright.sync_api import sync_playwright
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--workspace",type=Path,required=True)
parser.add_argument("--site",type=Path,required=True)
parser.add_argument("--output",type=Path,required=True)
parser.add_argument("--source-head",required=True)
parser.add_argument("--expected-html-sha",required=True)
args=parser.parse_args()
ROOT=args.workspace.resolve()
sys.path.insert(0,str(ROOT))
from scripts.capture_page_evidence import serve_site_dir,state_seed_source
import subprocess
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==args.source_head
assert not (args.site/"premiumdata").exists()
assert not (args.site/"us_stocks.json").exists()
digest=hashlib.sha256((args.site/"us_stocks.html").read_bytes()).hexdigest()
assert digest==args.expected_html_sha,(digest,args.expected_html_sha)
assert not args.output.exists()
server,port=serve_site_dir(args.site)
observe="""(() => {
window.__prophetLoad={supported:PerformanceObserver.supportedEntryTypes.includes('layout-shift'),entries:[]};
if(!window.__prophetLoad.supported)return;
new PerformanceObserver(list=>{for(const e of list.getEntries()){
if(e.hadRecentInput)continue;
window.__prophetLoad.entries.push({value:e.value,time:e.startTime,sources:e.sources.map(s=>({
node:s.node?(s.node.tagName+'#'+s.node.id+'.'+String(s.node.className).slice(0,150)):null,
previous:{x:s.previousRect.x,y:s.previousRect.y,w:s.previousRect.width,h:s.previousRect.height},
current:{x:s.currentRect.x,y:s.currentRect.y,w:s.currentRect.width,h:s.currentRect.height}}))});
}}).observe({type:'layout-shift',buffered:true});
})();"""
report={"source_head":args.source_head,"public_html_sha256":digest,"post_font_observation_ms":2500,
"scope":"fresh anonymous offline contexts; native initial theme/locale; no post-load state forcing; first-load lab measurements","runs":[]}
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch()
  for width in (1440,390):
   for repeat in range(1,4):
    context=browser.new_context(viewport={"width":width,"height":900 if width==1440 else 844},locale="en-US",color_scheme="light",service_workers="block")
    context.route("**/*",lambda route:route.continue_() if urlsplit(route.request.url).netloc==f"127.0.0.1:{port}" else route.abort())
    context.add_init_script(state_seed_source({"theme":"light","locale":"en"}))
    context.add_init_script(observe)
    page=context.new_page()
    page.goto(f"http://127.0.0.1:{port}/us_stocks.html",wait_until="domcontentloaded")
    page.locator("#us-today-grid > .po-card").first.wait_for(state="visible")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(2500)
    metrics=page.evaluate("""() => ({...window.__prophetLoad,
    firstCardY:document.querySelector('#us-today-grid > .po-card').getBoundingClientRect().y,
    documentWidth:document.documentElement.scrollWidth,
    nav:document.querySelector('.site-nav')?.outerHTML.slice(0,160)})""")
    entries=sorted(metrics["entries"],key=lambda e:e["time"])
    total=sum(e["value"] for e in entries);maximum=0;window_total=0;first=last=None
    for e in entries:
     if first is None or e["time"]-last>=1000 or e["time"]-first>=5000:
      first=e["time"];window_total=0
     window_total+=e["value"];last=e["time"];maximum=max(maximum,window_total)
    row={"width":width,"repeat":repeat,"cumulative_shift":total,"max_session_window_cls":maximum,**metrics}
    report["runs"].append(row);args.output.write_text(json.dumps(report,indent=2))
    print(json.dumps({"width":width,"repeat":repeat,"cls":round(maximum,5),"sum":round(total,5),"first_card_y":metrics["firstCardY"],"entries":len(entries)}),flush=True)
    context.close()
  browser.close()
finally:
 server.shutdown();server.server_close()
print("MEASUREMENTS",str(args.output),flush=True)
