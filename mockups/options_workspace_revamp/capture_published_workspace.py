"""Full-shell visual QA against exact repository-published JSON blobs.
Ephemeral Chromium over loopback HTTP; external egress blocked. Never attaches
to the connected user browser and never writes site/ or data/.
"""
import argparse,json
from pathlib import Path
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright
HERE=Path(__file__).resolve().parent
SOURCE=HERE/"fixtures"/"published"
PAYLOADS=json.loads((SOURCE/"payloads.json").read_text())
ORIGIN="http://127.0.0.1:8768"
ap=argparse.ArgumentParser();ap.add_argument("--label",default="published-baseline");ap.add_argument("--full-matrix",action="store_true");args=ap.parse_args()
OUT=HERE/("visual-"+args.label);OUT.mkdir(exist_ok=True)
cases=[(1440,1000,"light","en","brief"),(1440,1000,"light","en","scanner"),(390,844,"dark","zh","ticker")]
if args.full_matrix:cases=[(w,h,t,l,m) for w,h in [(1440,1000),(390,844)] for t in ["light","dark"] for l in ["en","zh"] for m in ["brief","flow","scanner","ticker","leaders"]]
rows=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    for width,height,theme,lang,mode in cases:
        ctx=browser.new_context(viewport={"width":width,"height":height},service_workers="block",device_scale_factor=1)
        def handle(route):
            url=route.request.url.split("?")[0]
            key=next((k for k in PAYLOADS if url.endswith("/"+k)),None)
            if key:route.fulfill(status=200,content_type="application/json",body=json.dumps(PAYLOADS[key]))
            elif route.request.url.startswith(ORIGIN+"/"):route.continue_()
            else:route.abort()
        ctx.route("**/*",handle)
        page=ctx.new_page();errors=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        suffix="#ticker?t=SPY" if mode=="ticker" else "#"+mode
        url=ORIGIN+"/mockups/options_workspace_revamp/fixtures/published/workspace.html?"+urlencode({"theme":theme,"lang":lang})+suffix
        page.goto(url,wait_until="networkidle",timeout=20000)
        page.locator("#mode-"+mode+" .oew-skel").wait_for(state="detached",timeout=20000)
        page.wait_for_function("document.fonts.status === 'loaded'",timeout=5000)
        metrics=page.evaluate("""() => {
          const n=document.querySelector('nav'),m=document.querySelector('.oew-mode:not([hidden])'),orb=document.querySelector('#mmb-boot,#mmb-launch');
          const rect=e=>{if(!e)return null;const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}};
          return {viewport:innerWidth,scroll:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,
          theme:document.documentElement.dataset.theme,lang:document.documentElement.lang,nav:rect(n),assistant:rect(orb),
          heading:document.querySelector('h1')?.innerText,selected:document.querySelector('.oew-tab[aria-selected=true]')?.dataset.mode,
          dates:[...document.querySelectorAll('[role=tabpanel]:not([hidden]) .oew-asof')].map(e=>e.textContent.trim()),
          panels:[...document.querySelectorAll('[role=tabpanel]')].map(e=>({id:e.id,hidden:e.hidden}))};
        }""")
        name=f"{mode}-{width}-{theme}-{lang}"
        page.screenshot(path=str(OUT/(name+".png")),full_page=False)
        rows.append({"name":name,**metrics,"overflow":metrics["scroll"]>width+1,"errors":errors,"capture_scope":"full viewport including shared shell","source_fixture":"published Git snapshot; not live network"})
        ctx.close()
    browser.close()
report={"source_manifest":json.loads((SOURCE/"manifest.json").read_text()),"captures":rows}
(OUT/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps({"captures":len(rows),"overflow":[r["name"] for r in rows if r["overflow"]],"page_errors":[{"name":r["name"],"errors":r["errors"]} for r in rows if r["errors"]],"nav_height":[{"name":r["name"],"height":r["nav"]["h"] if r["nav"] else None} for r in rows]},indent=2))
