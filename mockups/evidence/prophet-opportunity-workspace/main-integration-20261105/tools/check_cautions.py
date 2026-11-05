"""Verify real anonymous Screener disclosure behavior from the exact native-generated Prophet HTML."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse, datetime, hashlib, json, shutil, subprocess, sys, tempfile
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--workspace", required=True, type=Path)
parser.add_argument("--source-head", required=True)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
ROOT = args.workspace.resolve()
OUT = args.output.resolve()
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip() == args.source_head
sys.path.insert(0,str(ROOT))
from scripts.capture_page_evidence import serve_site_dir, state_seed_source

OUT.mkdir(exist_ok=False)
site = ROOT/"site"
summary = {
    "source_head": args.source_head,
    "scope": "Exact native-generated HTML and CSS; source_head identifies the clean build input; anonymous offline Chromium; no protected data served, account writes, live authentication, Paper edits or deployment.",
    "page_sha256": hashlib.sha256((site/"us_stocks.html").read_bytes()).hexdigest(),
    "css_sha256": hashlib.sha256((site/"assets/css/60dc406b.css").read_bytes()).hexdigest(),
    "cells": [],
    "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
def flush():
    (OUT/"observations.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n")

with tempfile.TemporaryDirectory(prefix="prophet-caution-public-") as temp:
    public = Path(temp)
    shutil.copy2(site/"us_stocks.html",public/"us_stocks.html")
    for name in ("assets","fonts"):
        if (site/name).is_dir():
            shutil.copytree(site/name,public/name,ignore=shutil.ignore_patterns("*.json","*.html","*.map"))
    for item in site.iterdir():
        if item.is_file() and item.suffix in {".css",".js",".svg",".woff",".woff2",".ico",".png",".webp"}:
            shutil.copy2(item,public/item.name)
    assert not (public/"premiumdata").exists()
    assert not (public/"us_stocks.json").exists()
    server, port = serve_site_dir(public)
    origin=f"http://127.0.0.1:{port}"
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch()
            summary["browser_version"]=browser.version
            for width in (1440,768,390,320):
                for theme in ("light","dark"):
                    for locale in ("en","zh"):
                        label=f"{width}-{theme}-{locale}"
                        context=browser.new_context(viewport={"width":width,"height":1000 if width>=1200 else 844},
                            locale="zh-CN" if locale=="zh" else "en-US",color_scheme=theme,
                            device_scale_factor=1,service_workers="block",reduced_motion="reduce")
                        denied=[]; errors=[]; failed_local=[]
                        def route_request(route):
                            u=urlsplit(route.request.url)
                            if u.netloc==f"127.0.0.1:{port}" and not u.path.startswith("/premiumdata/") and not u.path.endswith(".json"):
                                route.continue_()
                            else:
                                denied.append(route.request.url)
                                route.abort()
                        context.route("**/*",route_request)
                        context.add_init_script(state_seed_source({"theme":theme,"locale":locale}))
                        page=context.new_page()
                        page.on("pageerror",lambda error: errors.append(str(error)))
                        page.on("response",lambda response: failed_local.append({"url":response.url,"status":response.status}) if response.status>=400 else None)
                        page.goto(origin+"/us_stocks.html",wait_until="domcontentloaded")
                        page.locator("#us-src-btn-cand").click()
                        control=page.locator("#po-screener-1 .po-cautions > summary")
                        control.wait_for(state="visible")
                        page.evaluate("document.fonts.ready")
                        page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
                        metrics=page.evaluate("""() => {
                            const visible=element=>element.getClientRects().length>0;
                            const rect=element=>{const r=element.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}};
                            return {
                                viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,bodyWidth:document.body.scrollWidth,
                                theme:document.documentElement.getAttribute('data-theme'),lang:document.documentElement.lang,
                                reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches,
                                protectedControls:document.querySelectorAll('[data-pvs-plan-target]').length,
                                controls:[...document.querySelectorAll('.po-cautions > summary')].filter(visible).map(element=>({
                                    card:element.closest('.po-card')?.id,rect:rect(element),display:getComputedStyle(element).display,
                                    listStyle:getComputedStyle(element).listStyleType,text:element.innerText
                                })),
                                cards:[...document.querySelectorAll('.po-card')].filter(visible).map(element=>({
                                    id:element.id,rect:rect(element),clientWidth:element.clientWidth,scrollWidth:element.scrollWidth
                                }))
                            };
                        }""")
                        assert metrics["documentWidth"]<=width,(label,"horizontal overflow",metrics)
                        assert metrics["theme"]==theme,(label,"theme")
                        assert metrics["lang"].startswith(locale),(label,"locale",metrics["lang"])
                        assert metrics["reducedMotion"],(label,"reduced motion")
                        assert metrics["protectedControls"]==0,(label,"protected control exposed")
                        assert metrics["controls"],(label,"no visible caution controls")
                        for item in metrics["controls"]:
                            assert item["rect"]["width"]>=44 and item["rect"]["height"]>=44,(label,"undersized touch target",item)
                            assert item["display"]=="list-item" and item["listStyle"]=="disclosure-closed",(label,"native marker lost",item)
                        for item in metrics["cards"]:
                            assert item["scrollWidth"]<=item["clientWidth"]+1,(label,"card overflow",item)
                        control.focus()
                        page.keyboard.press("Enter")
                        opened=control.evaluate("element=>element.parentElement.open")
                        focus=control.evaluate("""element=>({
                            active:document.activeElement===element,
                            visible:element.matches(':focus-visible'),
                            outlineStyle:getComputedStyle(element).outlineStyle,
                            outlineWidth:getComputedStyle(element).outlineWidth,
                            outlineColor:getComputedStyle(element).outlineColor,
                            boxShadow:getComputedStyle(element).boxShadow
                        })""")
                        assert opened and focus["active"] and focus["visible"],(label,"keyboard open or focus failed",focus)
                        page.keyboard.press("Space")
                        closed=not control.evaluate("element=>element.parentElement.open")
                        assert closed,(label,"keyboard close failed")
                        page.locator("#po-screener-1").scroll_into_view_if_needed()
                        screenshot=OUT/f"screener-card-{label}.png"
                        page.locator("#po-screener-1").screenshot(path=str(screenshot))
                        viewport=None
                        if (width,theme,locale) in {(1440,"light","en"),(1440,"dark","en"),(390,"light","en"),(390,"dark","zh"),(768,"light","zh"),(320,"light","en")}:
                            viewport=OUT/f"screener-view-{label}.png"
                            page.screenshot(path=str(viewport),full_page=False)
                        # Screenshot after actual keyboard expansion as well as collapsed state.
                        expanded=None
                        if (width,theme,locale) in {(390,"dark","zh"),(320,"light","en")}:
                            control.focus()
                            page.keyboard.press("Enter")
                            expanded=OUT/f"screener-expanded-{label}.png"
                            page.locator("#po-screener-1").screenshot(path=str(expanded))
                            page.keyboard.press("Space")
                        assert not errors,(label,"page errors",errors)
                        row={"case":label,"metrics":metrics,"keyboard":{"enter_opens":opened,"space_closes":closed,"focus":focus},
                            "page_errors":errors,"failed_local_responses":failed_local,"blocked_urls":sorted(set(denied)),
                            "screenshot":screenshot.name,"screenshot_sha256":hashlib.sha256(screenshot.read_bytes()).hexdigest(),
                            "viewport_screenshot":viewport.name if viewport else None,
                            "expanded_screenshot":expanded.name if expanded else None}
                        summary["cells"].append(row)
                        flush()
                        print("PASS",label,"controls",len(metrics["controls"]),"min_height",min(item["rect"]["height"] for item in metrics["controls"]),
                              "overflow",metrics["documentWidth"]-width,"keyboard",opened and closed,flush=True)
                        context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
summary["completed_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
summary["passed_cells"]=len(summary["cells"])
flush()
assert summary["passed_cells"]==16
print("COMPLETE",str(OUT/"observations.json"),flush=True)
