"""Design-only whole-page composition; NOT a canonical production render.

The frozen #6685 page is a read-only canvas. The new row is rendered from the
real shared workspace reader/view plus this branch's candidate projection.
A loopback response composes them only for visual review; it writes no site data.
"""
from __future__ import annotations
import argparse
import copy
import functools
import hashlib
import json
import sys
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, StrictUndefined
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from lib.macro_economic_backdrop import build_economic_backdrop


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canvas-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--scenario", choices=("normal", "stale-growth"), default="normal")
    args = parser.parse_args()
    canvas = args.canvas_root.resolve()
    out = args.out.resolve()
    if canvas in out.parents or out == canvas:
        raise ValueError("Never write to the read-only canvas")
    out.mkdir(parents=True, exist_ok=False)
    design = Path(__file__).resolve().parent
    base_bytes = (canvas / "site/macro.html").read_bytes()
    base_hash = hashlib.sha256(base_bytes).hexdigest()
    assert base_hash == "b63e24b134deaa97598ce80db0435f24b2e48d65db00e606dcbb16af6bd24bc7"
    stamp = datetime.now(timezone.utc).isoformat()
    data_root = canvas / "site/macrodata"
    if args.scenario == "stale-growth":
        from tests.test_macro_economic_backdrop import _snapshots, _publish
        synthetic = _snapshots()
        synthetic["growth_real_economy"]["availability"]["state"] = "STALE_SOURCE"
        data_root = _publish(out / "fixture-macrodata", synthetic)
    cards = build_economic_backdrop(data_root, page_built_at=stamp)
    assert len(cards) == 3
    if args.scenario == "normal":
        assert all(c["facts"] for c in cards)
    else:
        assert cards[0]["tone"] == "unavailable" and not cards[0]["facts"]
        assert all(c["facts"] for c in cards[1:])
    env = Environment(loader=FileSystemLoader(design), autoescape=True, undefined=StrictUndefined)
    row = env.from_string('{% import "section.html.j2" as row %}{{ row.economic_backdrop(cards) }}').render(cards=cards)
    document = BeautifulSoup(base_bytes, "html.parser")
    target = document.select_one("#sx-markets-v2")
    assert target is not None and document.select_one(".ebd") is None
    target.insert_after(BeautifulSoup(row, "html.parser"))
    link = document.new_tag("link", rel="stylesheet", href="economic-backdrop-preview.css")
    document.head.append(link)
    page = str(document).encode()
    css = (design / "section.css.j2").read_text()
    (out / "preview.html").write_bytes(page)
    (out / "cards.json").write_text(json.dumps(cards, ensure_ascii=False, indent=2))
    report = {"classification": "DESIGN_COMPOSITION_NOT_CANONICAL_RENDER_NOT_PRODUCTION",
              "at": stamp, "scenario": args.scenario, "canvas_sha256": base_hash, "cases": [],
              "projection_sha256": hashlib.sha256((ROOT / "lib/macro_economic_backdrop.py").read_bytes()).hexdigest(),
              "row_sha256": hashlib.sha256(row.encode()).hexdigest()}

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            pass
        def do_GET(self):
            path = urlparse(self.path).path
            if path in ("/macro.html", "/economic-backdrop-preview.css"):
                body = page if path == "/macro.html" else css.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8" if path == "/macro.html" else "text/css; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                super().do_GET()
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(canvas / "site")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            for width in ((1440, 768, 390) if args.scenario == "normal" else (390,)):
                for theme, lang in (("dark", "en"), ("light", "en"), ("dark", "zh"), ("light", "zh")):
                    context = browser.new_context(viewport={"width": width, "height": 1000}, reduced_motion="reduce")
                    context.route("**/*", lambda route: route.continue_() if urlparse(route.request.url).hostname == "127.0.0.1" else route.abort())
                    tab = context.new_page()
                    errors = []
                    console_errors = []
                    tab.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
                    tab.on("pageerror", lambda error: errors.append(str(error)))
                    tab.goto(f"http://127.0.0.1:{server.server_port}/macro.html", wait_until="load")
                    tab.evaluate("([t,l])=>{document.documentElement.dataset.theme=t;document.documentElement.dataset.lang=l;document.documentElement.lang=l;}", [theme, lang])
                    tab.locator(".ebd").wait_for(state="visible")
                    tab.evaluate("document.fonts.ready")
                    section = tab.locator(".ebd")
                    facts = {"width": width, "theme": theme, "language": lang,
                             "height": section.bounding_box()["height"],
                             "overflow": tab.evaluate("document.documentElement.scrollWidth > innerWidth + 1"),
                             "card_count": tab.locator(".ebd-card").count(),
                             "source_ids": [c["source"]["digest"] for c in cards],
                             "link_heights": tab.locator(".ebd-go").evaluate_all("els=>els.map(e=>e.getBoundingClientRect().height)")}
                    facts["css_diagnostic"] = tab.evaluate("""() => ({row:getComputedStyle(document.querySelector('.ebd-row')).display,
                        col:getComputedStyle(document.querySelector('.ebd')).gridColumn,
                        sheets:Array.from(document.styleSheets).map(s=>s.href),
                        previewRules:Array.from(document.styleSheets).filter(s=>s.href && s.href.includes('economic-backdrop-preview')).map(s=>({disabled:s.disabled,media:s.media.mediaText,rules:Array.from(s.cssRules).map(r=>r.cssText)})),
                        links:Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(l=>l.href)})""")
                    facts["console_errors"] = console_errors
                    if facts["css_diagnostic"]["row"] != "grid":
                        report["style_failure"] = facts
                        raise AssertionError("Preview CSS did not apply")
                    assert facts["card_count"] == 3 and not facts["overflow"]
                    positions = tab.evaluate("""() => {const r=s=>document.querySelector(s).getBoundingClientRect();return {market_bottom:r('#sx-markets-v2').bottom,row_top:r('.ebd').top,row_bottom:r('.ebd').bottom,actions_top:r('#sx-evidence').top}}""")
                    facts["placement"] = positions
                    assert positions["market_bottom"] <= positions["row_top"]
                    assert positions["row_bottom"] <= positions["actions_top"]
                    if width == 1440:
                        assert facts["height"] <= 240, facts
                    assert min(facts["link_heights"]) >= 44
                    if width < 900:
                        assert min(facts["link_heights"]) >= 44
                    section.screenshot(path=str(out / f"row-{width}-{theme}-{lang}.png"))
                    tab.evaluate("window.scrollTo(0,0)")
                    tab.screenshot(path=str(out / f"home-{width}-{theme}-{lang}.png"), full_page=False)
                    control = tab.locator(".ebd-rc > summary").first
                    control.focus()
                    tab.keyboard.press("Enter")
                    assert tab.locator(".ebd-rc").first.get_attribute("open") is not None
                    tab.keyboard.press("Enter")
                    assert tab.locator(".ebd-rc").first.get_attribute("open") is None
                    facts["keyboard_receipt"] = True
                    facts["page_errors"] = errors
                    assert not errors, errors
                    report["cases"].append(facts)
                    context.close()
            browser.close()
        report["status"] = "PASS"
        return 0
    finally:
        server.shutdown()
        assert hashlib.sha256((canvas / "site/macro.html").read_bytes()).hexdigest() == base_hash
        (out / "receipt.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps({"status": report.get("status", "INCOMPLETE"), "cases": len(report["cases"]),
                          "heights": [c["height"] for c in report["cases"]], "receipt": str(out / "receipt.json")}))


if __name__ == "__main__":
    raise SystemExit(main())
