"""Render the illustrative Paper composition for local visual preflight only."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse, json, sys
from playwright.sync_api import sync_playwright
cli=argparse.ArgumentParser(description=__doc__)
cli.add_argument("--workspace",type=Path,required=True)
cli.add_argument("--source",type=Path,required=True)
cli.add_argument("--output",type=Path,required=True)
args=cli.parse_args()
ROOT=args.workspace.resolve()
sys.path.insert(0,str(ROOT))
from scripts.capture_page_evidence import serve_site_dir
BASE=args.source.resolve()
OUT=args.output.resolve()
OUT.mkdir(parents=True,exist_ok=False)
server,port=serve_site_dir(BASE)
observations=[]
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for label in ("1440-light-en","1440-dark-en","390-light-en","390-dark-zh"):
            width=int(label.split("-")[0])
            context=browser.new_context(viewport={"width":width,"height":900 if width==1440 else 844},device_scale_factor=1,service_workers="block")
            context.route("**/*",lambda route:route.continue_() if urlsplit(route.request.url).netloc==f"127.0.0.1:{port}" else route.abort())
            page=context.new_page()
            page.goto(f"http://127.0.0.1:{port}/{label}.html",wait_until="domcontentloaded")
            page.evaluate("document.fonts.ready")
            metrics=page.evaluate("""() => {
                const rect = e => {const r=e.getBoundingClientRect(); return {x:r.x,y:r.y,width:r.width,height:r.height}};
                return {viewport:innerWidth,width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,firstCard:rect(document.querySelector('[data-slot="R8 Card NVDA"]')),overflowNodes:[...document.querySelectorAll('[data-slot]')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({name:e.dataset.slot,rect:rect(e)}))};
            }""")
            page.screenshot(path=str(OUT/(label+".png")),full_page=True)
            page.screenshot(path=str(OUT/(label+"-top.png")))
            observations.append({"variant":label,**metrics})
            context.close()
        browser.close()
finally:
    server.shutdown()
(OUT/"observations.json").write_text(json.dumps({"scope":"Illustrative design preflight; not production or browser account acceptance","variants":observations},indent=2))
print(json.dumps(observations))
