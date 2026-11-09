from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tests.macro_workspace_browser_support import write_preview, render_workspace
from scripts.capture_page_evidence import serve_site_dir
from playwright.sync_api import sync_playwright

work = ROOT / "research/ux_polish/macro-workspace-20261109/test-work"
site = write_preview(work / "site")
baseline = subprocess.check_output(["git", "show", "9a13c64bf69f782332afa29efb09fe48ee30b857:templates/dashboard.html.j2"], cwd=ROOT).decode()
(site / "baseline.html").write_text(render_workspace(_template_source=baseline))
server, port = serve_site_dir(site)
results = {}
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for route in ["baseline", "macro"]:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.add_init_script("""localStorage.setItem('theme','light');localStorage.removeItem('themeAuto');localStorage.setItem('lang','en');
            window.__uxShifts=[];new PerformanceObserver(list=>{for(const e of list.getEntries())if(!e.hadRecentInput)window.__uxShifts.push({t:e.startTime,value:e.value,sources:e.sources.map(s=>({node:s.node?.tagName+'#'+s.node?.id+'.'+s.node?.className,prev:s.previousRect.toJSON(),next:s.currentRect.toJSON()}))});}).observe({type:'layout-shift',buffered:true});""")
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{port}/{route}.html", wait_until="load")
            page.wait_for_timeout(1200)
            results[route] = page.evaluate("""() => ({
              shifts:window.__uxShifts,
              samples:['body','#regime-radar','#sx-events-v2 .mx5-card-face','.mx5-timeline','.mx5-tl-items','.mx5-tl-item','#sx-evidence .mx5-card-face','.macro-driver-hint','.site-nav'].map(q=>{
                const e=document.querySelector(q);if(!e)return {q};
                const c=getComputedStyle(e),r=e.getBoundingClientRect();return {q,rect:r.toJSON(),display:c.display,flex:c.flex,align:c.alignItems,justify:c.justifyContent,gap:c.gap,height:c.height,minHeight:c.minHeight,padding:c.padding,margin:c.margin,background:c.background,animation:c.animationName};
              }),
              bodyBefore:getComputedStyle(document.body,'::before').background,
              bodyAfter:getComputedStyle(document.body,'::after').background
            })""")
            results[route]["page_errors"] = errors
            page.screenshot(path=str(work / (route + "-viewport.png")))
            page.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
(work / "layout-diagnostics.json").write_text(json.dumps(results, indent=2))
for route, data in results.items():
    print(route, "CLS", sum(x["value"] for x in data["shifts"]), "errors", data["page_errors"])
    print("shifts", json.dumps(data["shifts"], ensure_ascii=False)[:8500])
    print("samples", json.dumps(data["samples"], ensure_ascii=False)[:5000])
    print("backgrounds", data["bodyBefore"], data["bodyAfter"])
