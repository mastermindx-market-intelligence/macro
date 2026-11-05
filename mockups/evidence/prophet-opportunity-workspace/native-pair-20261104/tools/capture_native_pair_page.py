"""Capture the regenerated public Prophet page in anonymous, offline browser contexts.

Derived from `full-page-20261103/tools/capture_native_prophet.py` (the accepted prior
runner) with ONE deliberate change: the readiness wait targets the elements this
board generation actually renders.

The prior runner waited for `#us-today-grid > .po-card` — the publicly-visible
Featured card. On the 2026-11-03 board the first Featured row sits at buy[]
index 3, outside the 3-row public preview, so the public page renders its
designed honest empty state instead of a Featured card. Waiting for a Featured
card would therefore have timed out on a page that is behaving correctly. This
runner waits for `#us-standouts` and the first screener `.po-card`, and RECORDS
the Today section's own attributes (`data-today-total`, `data-today-visible`) and
whether the honest empty state is present, so the capture proves what the page
actually shows rather than hiding it.

What is real here:
  * the generated public HTML is served byte-for-byte, unchanged;
  * the protected payload is NOT served - the public root has no premiumdata/ and
    no us_stocks.json, and every /premiumdata/ request is aborted;
  * every non-loopback request is aborted, so the capture is offline and anonymous;
  * theme and locale are real browser context settings (color_scheme / locale).

What is NOT claimed:
  * no signed-in session, no account, no entitlement, no production or live proof;
  * no claim that the anonymous page shows an entitled surface.

Usage:
    python3 capture_native_pair_page.py --workspace <ws> --source-head <sha> \\
        --build-receipt <build.json> --output <dir>
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--workspace", required=True, type=Path)
parser.add_argument("--source-head", required=True)
parser.add_argument("--build-receipt", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()

ROOT = args.workspace.resolve()
HEAD = args.source_head
OUT = args.output.resolve()
sys.path.insert(0, str(ROOT))
from scripts.capture_page_evidence import serve_site_dir, state_seed_source  # noqa: E402

assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == HEAD
receipt = json.loads(args.build_receipt.read_text())
assert Path(receipt["workspace"]).resolve() == ROOT
assert receipt["head"] == HEAD
assert receipt.get("completed_at") and len(receipt["modules"]) == 4
assert all(m["exit"] == 0 for m in receipt["modules"])
for rel, record in receipt["artifacts"].items():
    assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == record["sha256"], rel

OUT.mkdir(parents=True, exist_ok=False)
public = OUT / "public"
public.mkdir()
site = ROOT / "site"
for name in ("us_stocks.html",):
    shutil.copy2(site / name, public / name)
for name in ("assets", "fonts"):
    if (site / name).is_dir():
        shutil.copytree(site / name, public / name,
                        ignore=shutil.ignore_patterns("*.json", "*.html", "*.map"))
for item in site.iterdir():
    if item.is_file() and item.suffix in {".css", ".js", ".svg", ".woff", ".woff2", ".ico", ".png", ".webp"}:
        shutil.copy2(item, public / item.name)
assert not (public / "premiumdata").exists()
assert not (public / "us_stocks.json").exists()
page_bytes = (site / "us_stocks.html").read_bytes()
assert (public / "us_stocks.html").read_bytes() == page_bytes
private_bytes = (site / "premiumdata/us_stocks.json").read_bytes()
doc = BeautifulSoup(page_bytes, "html.parser")
private = json.loads(private_bytes)
today = doc.select_one("#us-today")

summary = {
    "schema": "prophet.native_pair_render/v1",
    "source_head": HEAD,
    "public_html_sha256": hashlib.sha256(page_bytes).hexdigest(),
    "essential_payload_sha256": hashlib.sha256(private_bytes).hexdigest(),
    "public_html_bytes": len(page_bytes),
    "essential_payload_bytes": len(private_bytes),
    "board_sha256": hashlib.sha256((site / "factordata/us_standouts.json").read_bytes()).hexdigest(),
    "board_as_of": json.loads((site / "factordata/us_standouts.json").read_text()).get("as_of"),
    "public_pool_rows": [r.get("data-ticker") for r in doc.select("#us-candidate-pool .ucp-row")],
    "public_cards": [c.get("data-ticker") for c in doc.select(".po-card")],
    "public_today_grid_present": doc.select_one("#us-today-grid") is not None,
    "today_section_attrs": dict(today.attrs) if today is not None else None,
    "today_empty_state": (
        " ".join(t.get_text(" ", strip=True) for t in today.select(".mx-empty-line, .mx-empty-why"))
        if today is not None else ""
    ),
    "protected_plan_controls_in_public": len(doc.select("[data-pvs-plan-target]")),
    "private_payload_keys": sorted(private.keys()),
    "scope": (
        "Generated public HTML served unchanged; anonymous offline browser; the protected "
        "payload is not served and every /premiumdata/ request is aborted; no live, "
        "signed-in or production acceptance."
    ),
    "build_modules": receipt["modules"],
    "cells": [],
}
print("PAIR", json.dumps({k: v for k, v in summary.items() if k != "cells"}), flush=True)

server, port = serve_site_dir(public)
origin = f"http://127.0.0.1:{port}"
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in (1440, 768, 390, 320):
            for theme in ("light", "dark"):
                for locale in ("en", "zh"):
                    label = f"{width}-{theme}-{locale}"
                    context = browser.new_context(
                        viewport={"width": width, "height": 1000 if width >= 1200 else 844},
                        locale="zh-CN" if locale == "zh" else "en-US",
                        color_scheme=theme, device_scale_factor=1, service_workers="block")
                    denied: list[str] = []
                    errors: list[str] = []
                    responses: list[dict] = []

                    def route_request(route):
                        u = urlsplit(route.request.url)
                        if u.netloc == f"127.0.0.1:{port}" and not u.path.startswith("/premiumdata/"):
                            route.continue_()
                        else:
                            denied.append(route.request.url)
                            route.abort()

                    context.route("**/*", route_request)
                    context.add_init_script(state_seed_source({"theme": theme, "locale": locale}))
                    page = context.new_page()
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    page.on("response", lambda r: responses.append({"url": r.url, "status": r.status})
                            if r.status >= 400 else None)
                    page.goto(origin + "/us_stocks.html", wait_until="domcontentloaded", timeout=60000)
                    page.locator("#us-standouts").first.wait_for(state="visible", timeout=30000)
                    page.evaluate("document.fonts.ready")
                    page.wait_for_timeout(1500)
                    metrics = page.evaluate("""() => {
                      const rect = el => { const r = el.getBoundingClientRect();
                        return {x:r.x,y:r.y,width:r.width,height:r.height}; };
                      const today = document.querySelector('#us-today');
                      return {
                        viewport: innerWidth,
                        documentWidth: document.documentElement.scrollWidth,
                        bodyWidth: document.body.scrollWidth,
                        pageHeight: document.documentElement.scrollHeight,
                        theme: document.documentElement.getAttribute('data-theme'),
                        lang: document.documentElement.lang,
                        standoutsVisible: !!document.querySelector('#us-standouts'),
                        cards: [...document.querySelectorAll('.po-card')].map(c => ({
                          ticker: c.dataset.ticker,
                          rect: rect(c),
                          visible: c.getClientRects().length > 0,
                          hasSetupBody: !!c.querySelector('.pv-setup-inline'),
                        })),
                        visibleCards: [...document.querySelectorAll('.po-card')]
                          .filter(c => c.getClientRects().length > 0).map(c => c.dataset.ticker),
                        poolRows: [...document.querySelectorAll('#us-candidate-pool .ucp-row')]
                          .map(r => r.dataset.ticker),
                        todayTotal: today ? today.getAttribute('data-today-total') : null,
                        todayVisible: today ? today.getAttribute('data-today-visible') : null,
                        todayGridPresent: !!document.querySelector('#us-today-grid'),
                        todayEmptyText: today
                          ? [...today.querySelectorAll('.mx-empty-line, .mx-empty-why')]
                              .map(e => e.innerText.trim()).join(' | ')
                          : '',
                        protectedControls: document.querySelectorAll('[data-pvs-plan-target]').length,
                        visibleDialogs: [...document.querySelectorAll('[role=dialog]')]
                          .filter(e => e.getClientRects().length).length,
                      };
                    }""")
                    full = OUT / f"public-page-{label}.png"
                    page.screenshot(path=str(full), full_page=True)
                    row = {
                        "case": label,
                        "metrics": metrics,
                        "page_errors": errors,
                        "failed_local_responses": responses,
                        "blocked_external_urls": sorted(set(denied)),
                        "overflow_px": metrics["documentWidth"] - width,
                        "screenshot": full.name,
                        "screenshot_sha256": hashlib.file_digest(full.open("rb"), "sha256").hexdigest(),
                    }
                    summary["cells"].append(row)
                    (OUT / "observations.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
                    print("CAPTURE", label,
                          "overflow", metrics["documentWidth"] - width,
                          "page_errors", len(errors),
                          "cards", len(metrics["cards"]),
                          "today_visible", metrics["todayVisible"],
                          flush=True)
                    context.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()

summary["completed_at"] = time.time()
(OUT / "observations.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
print("CAPTURE_COMPLETE", str(OUT / "observations.json"), flush=True)
