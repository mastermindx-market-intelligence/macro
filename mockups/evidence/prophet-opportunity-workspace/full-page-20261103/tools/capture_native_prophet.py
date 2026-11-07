"""Capture the normal Prophet producer output in anonymous, offline browser contexts."""
from pathlib import Path
from urllib.parse import urlsplit
import hashlib, json, shutil, subprocess, sys, time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--workspace", required=True, type=Path)
parser.add_argument("--source-head", required=True)
parser.add_argument("--build-receipt", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
parser.add_argument("--asset-receipt", type=Path)
args = parser.parse_args()
ROOT = args.workspace.resolve()
HEAD = args.source_head
OUT = args.output.resolve()
sys.path.insert(0, str(ROOT))
from scripts.capture_page_evidence import serve_site_dir, state_seed_source

assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip() == HEAD
receipt = json.loads(args.build_receipt.read_text())
assert Path(receipt["workspace"]).resolve() == ROOT
asset_receipt = json.loads(args.asset_receipt.read_text()) if args.asset_receipt else None
if asset_receipt:
    assert asset_receipt["source_head"] == HEAD and asset_receipt["base_build_head"] == receipt["head"]
    assert asset_receipt["base_receipt_sha256"] == hashlib.sha256(args.build_receipt.read_bytes()).hexdigest()
    assert asset_receipt.get("completed_at") and all(step["exit"] == 0 for step in asset_receipt["steps"])
    assert asset_receipt["protected_and_model_unchanged"] and asset_receipt["shared_javascript_unchanged"]
    assert set(asset_receipt["source_delta"]) == {"templates/theme.css", "site/theme.css"}
    assert set(subprocess.check_output(["git","diff","--name-only",receipt["head"],HEAD],cwd=ROOT,text=True).splitlines()) == set(asset_receipt["source_delta"])
    for rel, record in asset_receipt["artifacts"].items():
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() == record["sha256"], rel
else:
    assert receipt["head"] == HEAD
    for rel, record in receipt["artifacts"].items():
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() == record["sha256"], rel
assert receipt.get("completed_at") and len(receipt["modules"]) == 4
assert all(m["exit"] == 0 for m in receipt["modules"])
OUT.mkdir(exist_ok=False)
public = OUT / "public"
public.mkdir()
site = ROOT / "site"
for name in ("us_stocks.html", "chat.html", "vector.html"):
    shutil.copy2(site / name, public / name)
for name in ("assets","fonts"):
    if (site / name).is_dir():
        shutil.copytree(site/name, public/name,
                        ignore=shutil.ignore_patterns("*.json","*.html","*.map"))
for item in site.iterdir():
    if item.is_file() and item.suffix in {".css",".js",".svg",".woff",".woff2",".ico",".png",".webp"}:
        shutil.copy2(item,public/item.name)
assert not (public / "premiumdata").exists()
assert not (public / "us_stocks.json").exists()
page_bytes = (site / "us_stocks.html").read_bytes()
assert (public / "us_stocks.html").read_bytes() == page_bytes
private_bytes = (site / "premiumdata/us_stocks.json").read_bytes()
doc = BeautifulSoup(page_bytes, "html.parser")
private = json.loads(private_bytes)
summary = {
    "source_head": HEAD,
    "base_build_source_head": receipt["head"],
    "static_asset_followup": asset_receipt,
    "public_html_sha256": hashlib.sha256(page_bytes).hexdigest(),
    "essential_payload_sha256": hashlib.sha256(private_bytes).hexdigest(),
    "public_html_bytes": len(page_bytes),
    "essential_payload_bytes": len(private_bytes),
    "public_today_articles": len(doc.select("#us-today-grid > article")),
    "public_rich_cards": len(doc.select("#us-today-grid > .po-card")),
    "public_pool_rows": len(doc.select("#us-candidate-pool .ucp-row")),
    "private_top_level": {k:type(v).__name__ for k,v in private.items()},
    "scope": "Normal producer HTML unchanged; anonymous offline browser; no premium payload served; no live/authenticated acceptance.",
    "build_modules": receipt["modules"],
    "cells": []
}
print("PAIR",json.dumps({k:v for k,v in summary.items() if k!="cells"}),flush=True)
server,port = serve_site_dir(public)
origin = f"http://127.0.0.1:{port}"
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in (1440,768,390,320):
            for theme in ("light","dark"):
                for locale in ("en","zh"):
                    label = f"{width}-{theme}-{locale}"
                    context = browser.new_context(
                        viewport={"width":width,"height":1000 if width>=1200 else 844},
                        locale="zh-CN" if locale=="zh" else "en-US",
                        color_scheme=theme,device_scale_factor=1,service_workers="block")
                    denied=[]; errors=[]; responses=[]
                    def route_request(route):
                        u=urlsplit(route.request.url)
                        if u.netloc==f"127.0.0.1:{port}" and not u.path.startswith("/premiumdata/"):
                            route.continue_()
                        else:
                            denied.append(route.request.url)
                            route.abort()
                    context.route("**/*",route_request)
                    context.add_init_script(state_seed_source({"theme":theme,"locale":locale}))
                    page=context.new_page()
                    page.on("pageerror",lambda e:errors.append(str(e)))
                    page.on("response",lambda r:responses.append({"url":r.url,"status":r.status}) if r.status>=400 else None)
                    page.goto(origin+"/us_stocks.html",wait_until="domcontentloaded",timeout=60000)
                    # Public Featured may correctly expose 0 of 12. A missing
                    # card is not a browser timeout: bind to the native pair's
                    # verified public membership, and inspect the explicit
                    # access-empty region instead of fabricating a card.
                    if summary["public_today_articles"] == 0:
                        page.locator("#us-today .mx-today-access-empty").wait_for(state="visible",timeout=30000)
                        assert page.locator("#us-today-grid > .po-card").count() == 0
                        assert page.locator("#us-today .mx-today-access-cta").is_visible()
                    else:
                        page.locator("#us-today-grid > .po-card").first.wait_for(state="visible",timeout=30000)
                    page.evaluate("document.fonts.ready")
                    page.wait_for_timeout(1500)
                    metrics=page.evaluate("""() => {
                      const grid=document.querySelector('#us-today-grid');
                      const empty=document.querySelector('#us-today .mx-today-access-empty');
                      const cards=grid?[...grid.querySelectorAll(':scope > .po-card')]:[];
                      const rect=el=>{if(!el)return null;const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}};
                      return {
                        viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,
                        bodyWidth:document.body.scrollWidth,pageHeight:document.documentElement.scrollHeight,
                        h1:document.querySelector('h1')?.innerText,
                        theme:document.documentElement.getAttribute('data-theme'),
                        lang:document.documentElement.lang,
                        grid:rect(grid),columns:grid?getComputedStyle(grid).gridTemplateColumns:null,
                        empty:empty?{rect:rect(empty),text:empty.innerText.slice(0,300)}:null,
                        protectedControls:document.querySelectorAll('[data-pvs-plan-target]').length,
                        cards:cards.map(c=>({ticker:c.dataset.ticker,rect:rect(c),text:c.innerText.slice(0,250)})),
                        headings:[...document.querySelectorAll('h1,h2,h3')].filter(e=>e.getClientRects().length).map(e=>({text:e.innerText,y:e.getBoundingClientRect().y})),
                        visibleDialogs:[...document.querySelectorAll('[role=dialog]')].filter(e=>e.getClientRects().length).length
                      };
                    }""")
                    full=OUT/f"normal-page-{label}.png"
                    page.screenshot(path=str(full),full_page=True)
                    if (width,theme,locale) in {(1440,"light","en"),(1440,"dark","en"),(390,"light","en"),(390,"dark","zh"),(768,"light","zh"),(320,"light","en")}:
                        page.screenshot(path=str(OUT/f"normal-top-{label}.png"),full_page=False)
                    row={"case":label,"metrics":metrics,"page_errors":errors,
                         "failed_local_responses":responses,"blocked_external_urls":sorted(set(denied)),
                         "screenshot":full.name,"screenshot_sha256":hashlib.file_digest(full.open("rb"),"sha256").hexdigest()}
                    assert metrics["protectedControls"] == 0, (label,"protected Plan control in public HTML")
                    assert metrics["documentWidth"] <= width, (label,"horizontal overflow",metrics["documentWidth"])
                    assert not errors, (label,"page errors",errors)
                    assert bool(metrics["empty"]) == (summary["public_today_articles"] == 0), (label,"public state mismatch")
                    summary["cells"].append(row)
                    (OUT/"observations.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False))
                    first_y=round(metrics["cards"][0]["rect"]["y"],1) if metrics["cards"] else None
                    print("CAPTURE",label,"access_empty",bool(metrics["empty"]),"first_card_y",first_y,
                          "overflow",metrics["documentWidth"]-width,"page_errors",len(errors),flush=True)
                    context.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
summary["completed_at"]=time.time()
(OUT/"observations.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False))
print("CAPTURE_COMPLETE",str(OUT/"observations.json"),flush=True)
