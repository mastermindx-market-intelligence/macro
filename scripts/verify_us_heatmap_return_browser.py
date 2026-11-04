#!/usr/bin/env python3
"""Finite Chromium proof of the actual standalone heatmap and native history.

Serves the generated page/assets, synthetic populated feeds, and a labelled
detail destination on loopback. It never uses production credentials or data.
The detail fixture proves the incumbent click URL and native Back boundary;
it does not establish D07 detail-page or cross-origin integration acceptance.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import mimetypes
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
KEY = "mmx.usHeatmap.v1"


def feed(themes=False):
    groups = [("Technology", "科技"), ("Healthcare", "医疗"), ("Financial", "金融")]
    rows = []
    for i in range(36):
        ticker = ["AAPL", "MSFT", "NVDA"][i] if i < 3 else f"FIX{i:02d}"
        rows.append({"t": ticker if not themes else f"theme-{i}",
                     "name": f"Fixture company {i}" if not themes else f"Fixture theme {i}",
                     "name_zh": f"示例公司 {i}" if not themes else f"示例主题 {i}",
                     "sector": groups[i // 12][0], "industry": "Software - Infrastructure",
                     "size": 1000 - i * 17,
                     "members": [{"t": ticker, "perf": {"1D": i / 10, "5D": i / 5, "1M": i / 3}}],
                     "perf": {"1D": (i % 9 - 4) / 2, "5D": (i % 11 - 5) * 1.3, "1M": i - 15}})
    return {"asof": "2026-11-03", "generated_utc": "2026-11-04 05:00",
            "source": "D04_SYNTHETIC_FIXTURE", "market": "us", "currency": "USD",
            "map_type": "themes" if themes else "sectors", "size_basis": "members" if themes else "marketcap",
            "default_tf": "1D", "stock_url": "stock.html#", "n_tiles": len(rows),
            "timeframes": [{"key": k, "en": en, "zh": zh, "available": True}
                           for k, en, zh in [("1D", "1 day", "1天"), ("5D", "1 week", "1周"), ("1M", "1 month", "1月")]],
            "sectors": [{"key": en, "en": en, "zh": zh} for en, zh in groups], "tiles": rows}


def saved(tf="5D", query="", key="AAPL"):
    return {"version": 1, "path": "/sector_heatmap.html", "map": "sp500",
            "views": {"sp500": {"tf": tf, "sort": "move", "query": query,
                                  "observation": "D04_SYNTHETIC_FIXTURE|2026-11-03||2026-11-04 05:00"}},
            "position": {"map": "sp500", "key": key, "group": "Technology", "offset": 140,
                         "x": 0, "y": 700, "focus": None}}


class Server(ThreadingHTTPServer):
    def reset(self):
        self.payloads = {"sp500": feed(), "themes": feed(True)}
        self.gates = {}
        self.errors = set()
        self.requests_seen = []
        self.canonical = False
        self.snapshot = False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        path = urlsplit(self.path).path
        self.server.requests_seen.append(path)
        status, mime = 200, "text/html; charset=utf-8"
        if path.startswith("/marketdata/") and "heatmap.json" in path:
            key = "themes" if "themes" in path else "sp500"
            gate = self.server.gates.get(key)
            if gate:
                gate.wait(8)
            status = 503 if key in self.server.errors else 200
            body = json.dumps(self.server.payloads[key]).encode()
            mime = "application/json"
        elif path == "/stock.html":
            body = b'<!doctype html><html><title>D04 detail fixture</title><body><h1>Company destination fixture</h1><p>URL and native history proof only.</p><button onclick="history.back()">Back</button></body></html>'
        elif path == "/frame.html":
            body = b'<!doctype html><iframe title="Heatmap ownership fixture" src="/sector_heatmap.html" width="1200" height="850"></iframe>'
        elif path in ("/sector_heatmap.html", "/regional-fixture.html"):
            text = (SITE / "sector_heatmap.html").read_text()
            if path == "/regional-fixture.html":
                text = text.replace('data-hm-history="us-v1"', '')
            if self.server.canonical:
                initial = json.dumps({KEY: saved()}).replace("<", "\\u003c")
                text = text.replace("<head>", "<head><script>history.replaceState(" + initial + ",'');</script>", 1)
            label = "committed feed snapshot" if self.server.snapshot else "simulated market data"
            text = text.replace("</body>", '<aside style="position:fixed;bottom:8px;right:8px;z-index:2147483647;padding:6px 10px;border-radius:5px;background:#242332;color:#fff;font:11px sans-serif">D04 local proof · ' + label + '</aside></body>')
            body = text.encode()
        elif path.startswith("/api/"):
            status, mime, body = 403, "application/json", b'{}'
        else:
            target = (SITE / path.lstrip("/")).resolve()
            if SITE.resolve() in target.parents and target.is_file():
                body = target.read_bytes()
                mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            else:
                status, mime, body = 404, "text/plain", b"Fixture resource absent"
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "ux-evidence/d04-us-heatmap-return-20261104")
    parser.add_argument("--canonical", action="store_true", help="Also run the unchanged canonical visual-capture owner for its eight-cell receipt")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    server = Server(("127.0.0.1", 0), Handler)
    server.reset()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    cases, shots, errors = [], [], []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--disable-features=BackForwardCache"])
        version = browser.version

        def context(width=1365, lang="en", theme="dark", seed=None, extra=""):
            ctx = browser.new_context(viewport={"width": width, "height": 900 if width > 560 else 844}, reduced_motion="reduce", locale="zh-CN" if lang == "zh" else "en-US")
            ctx.route("**/*", lambda route: route.continue_() if urlsplit(route.request.url).netloc == urlsplit(origin).netloc else route.abort())
            init = f"try{{localStorage.setItem('theme',{json.dumps(theme)});localStorage.setItem('lang',{json.dumps(lang)});}}catch(e){{}}"
            if seed is not None:
                init += f"if(location.pathname==='/sector_heatmap.html') history.replaceState({json.dumps(seed)},'');"
            init += "window.__hmAdds=0;window.__hmRemoves=0;const add=document.addEventListener.bind(document),remove=document.removeEventListener.bind(document);document.addEventListener=function(n,...a){if(n==='hm-refresh')window.__hmAdds++;return add(n,...a)};document.removeEventListener=function(n,...a){if(n==='hm-refresh')window.__hmRemoves++;return remove(n,...a)};"
            ctx.add_init_script(init + extra)
            page = ctx.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            return ctx, page

        def ready(page):
            page.locator('#heatmap-full [data-hm-key]').first.wait_for()

        def remember(name, detail=None):
            cases.append({"name": name, "status": "PASS", "detail": detail})

        try:
            for width in (1365, 390):
                for lang in ("en", "zh"):
                    for theme in ("dark", "light"):
                        server.reset()
                        ctx, page = context(width, lang, theme)
                        exact = origin + "/sector_heatmap.html?study=a%2Fb&study=c+d#heatmap-full"
                        page.goto(exact, wait_until="domcontentloaded")
                        ready(page)
                        page.evaluate("history.replaceState({incumbent:{keep:['exact',3]}},'')")
                        page.locator('[data-tf="5D"]').click()
                        if width > 560:
                            page.locator('.hm-search input').fill(" AAPL ")
                        else:
                            page.locator('[data-s="move"]').click()
                        item = page.locator('[data-hm-key="AAPL"]').first
                        item.scroll_into_view_if_needed()
                        before_length = page.evaluate("history.length")
                        before_y = page.evaluate("scrollY")
                        page.evaluate("window.__returnNode=document.querySelector('.hm-host .hm-tm')")
                        item.click()
                        if width > 560:
                            page.wait_for_url("**/stock.html#AAPL")
                            page.go_back(wait_until="domcontentloaded")
                        else:
                            page.wait_for_function("window.MDXTerminalOverlay.isOpen()")
                            guard = page.evaluate("history.state")
                            assert "__mdxTerminalOverlay" in guard and KEY not in guard
                            assert guard["dashboardState"][KEY]["position"]["key"] == "AAPL"
                            page.evaluate("history.back()")
                            page.wait_for_function("!window.MDXTerminalOverlay.isOpen()")
                            assert page.evaluate("window.__returnNode===document.querySelector('.hm-host .hm-tm')")
                        ready(page)
                        expect(page.locator('[data-tf="5D"]')).to_have_class("hm-tf on")
                        assert page.url == exact
                        state = page.evaluate("history.state")
                        assert state["incumbent"] == {"keep": ["exact", 3]}
                        assert state[KEY]["views"]["sp500"]["tf"] == "5D"
                        assert page.evaluate("history.length") == before_length + 1
                        if width > 560:
                            expect(page.locator('.hm-search input')).to_have_value(" AAPL ")
                        else:
                            expect(page.locator('[data-s="move"]')).to_have_class("hm-sortb on")
                        # Actual logical item identity, not a serialized row index.
                        anchor = state[KEY]["position"]
                        assert anchor["key"] == "AAPL"
                        if width > 560:
                            page.wait_for_function("document.querySelector('.hm-return-note').textContent.length>0")
                            page.wait_for_function("([key,offset])=>Math.abs(document.querySelector('[data-hm-key=\"'+key+'\"]').getBoundingClientRect().top-offset)<8", arg=["AAPL", anchor["offset"]])
                        else:
                            page.wait_for_function("y=>Math.abs(scrollY-y)<2", arg=before_y)
                        name = f"{'document' if width > 560 else 'overlay'}-return-{width}-{lang}-{theme}"
                        page.screenshot(path=str(out / (name + ".png")))
                        shots.append(name + ".png")
                        if width > 560:
                            page.go_forward(wait_until="domcontentloaded")
                            assert page.url.endswith("/stock.html#AAPL")
                        else:
                            # The incumbent overlay's guard does not reopen on
                            # Forward. D04 must leave that owner state untouched.
                            page.evaluate("history.forward()")
                            page.wait_for_function("history.state && history.state.__mdxTerminalOverlay")
                            assert page.evaluate("window.__returnNode===document.querySelector('.hm-host .hm-tm')")
                            expect(page.locator('[data-tf="5D"]')).to_have_class("hm-tf on")
                        remember(name, {"exact_url": True, "logical_anchor": "AAPL", "extra_D04_history_entries": 0})
                        ctx.close()

            server.reset()
            ctx, page = context(390)
            page.goto(origin + "/sector_heatmap.html", wait_until="domcontentloaded"); ready(page)
            page.locator('[data-tf="5D"]').click(); page.locator('[data-s="move"]').click()
            page.locator('[data-hm-map="themes"]').click()
            page.locator('.hm-thtile,.hm-mrow-th').first.wait_for()
            page.locator('[data-tf="1M"]').click(); page.locator('[data-s="az"]').click()
            page.locator('[data-hm-map="sp500"]').click(); ready(page)
            expect(page.locator('[data-tf="5D"]')).to_have_class("hm-tf on")
            expect(page.locator('[data-s="move"]')).to_have_class("hm-sortb on")
            assert not page.locator('.hm-host').evaluate("el=>el.classList.contains('hm-themes')")
            page.locator('[data-hm-map="themes"]').click()
            expect(page.locator('[data-tf="1M"]')).to_have_class("hm-tf on")
            expect(page.locator('[data-s="az"]')).to_have_class("hm-sortb on")
            remember("per-map-controls-and-class-cleanup"); ctx.close()

            server.reset(); server.gates["sp500"] = threading.Event()
            ctx, page = context()
            page.goto(origin + "/sector_heatmap.html", wait_until="domcontentloaded")
            page.locator('[data-hm-map="themes"]').click()
            page.locator('.hm-thtile').first.wait_for()
            page.locator('[data-hm-map="sp500"]').click()
            server.gates["sp500"].set(); ready(page)
            assert page.evaluate("window.__hmAdds-window.__hmRemoves") == 1
            remember("A-B-A-delayed-response-single-live-view"); ctx.close()

            for unavailable in ("disabled", "removed", "all"):
                server.reset()
                if unavailable == "removed": server.payloads["sp500"]["timeframes"] = [t for t in server.payloads["sp500"]["timeframes"] if t["key"] != "5D"]
                else:
                    for tf in server.payloads["sp500"]["timeframes"]:
                        if unavailable == "all" or tf["key"] == "5D": tf["available"] = False
                ctx, page = context(seed={KEY: saved(), "foreign": 7})
                page.goto(origin + "/sector_heatmap.html", wait_until="domcontentloaded")
                expect(page.locator('.hm-return-note')).to_contain_text("unavailable")
                expect(page.locator('.hm-return-note')).to_contain_text("No timeframe is currently available. Your settings are retained." if unavailable == "all" else "Choose an available timeframe.")
                assert page.locator('[data-hm-key]').count() == 0
                assert page.evaluate(f"history.state[{json.dumps(KEY)}].views.sp500.tf") == "5D"
                page.screenshot(path=str(out / f"timeframe-{unavailable}.png")); shots.append(f"timeframe-{unavailable}.png")
                if unavailable != "all":
                    page.locator('[data-tf="1D"]').click(); ready(page)
                    assert page.evaluate(f"history.state[{json.dumps(KEY)}].views.sp500.tf") == "1D"
                remember("timeframe-explicit-choice-" + unavailable); ctx.close()

            server.reset()
            server.payloads["sp500"]["tiles"] = [x for x in server.payloads["sp500"]["tiles"] if x["t"] != "AAPL"]
            server.payloads["sp500"]["generated_utc"] = "2026-11-04 07:00"
            ctx, page = context(seed={KEY: saved()})
            page.goto(origin + "/sector_heatmap.html", wait_until="domcontentloaded"); ready(page)
            expect(page.locator('.hm-return-note')).to_contain_text("Returned to its group")
            expect(page.locator('.hm-return-note')).to_contain_text("observation time has changed")
            remember("changed-feed-missing-item-group-fallback"); ctx.close()

            server.reset(); server.gates["sp500"] = threading.Event()
            ctx, page = context(seed={KEY: saved()})
            page.goto(origin + "/sector_heatmap.html", wait_until="domcontentloaded")
            page.evaluate("const b=document.createElement('button');b.id='d04-user-focus';b.textContent='Continue my work';document.body.prepend(b)")
            page.locator('#d04-user-focus').click()
            server.gates["sp500"].set(); ready(page)
            expect(page.locator('#d04-user-focus')).to_be_focused()
            expect(page.locator('.hm-return-note')).to_contain_text("left where you moved")
            remember("late-load-preserves-deliberate-user-focus"); ctx.close()

            server.reset()
            ctx, page = context(390, "zh", "light", seed={KEY: saved(query="AAPL")})
            page.goto(origin + "/sector_heatmap.html", wait_until="domcontentloaded"); ready(page)
            expect(page.locator('.hm-return-note')).to_contain_text("不应用于移动端列表")
            assert page.locator('.hm-mrow').count() == 36
            page.screenshot(path=str(out / "mobile-retained-query.png")); shots.append("mobile-retained-query.png")
            remember("mobile-retained-query-limitation-visible"); ctx.close()

            for label, seed in [("primitive", "other-owner"), ("array", [1, 2]), ("malformed", {KEY: {"version": 999}, "foreign": 7})]:
                server.reset(); ctx, page = context(seed=seed)
                page.goto(origin + "/sector_heatmap.html", wait_until="domcontentloaded"); ready(page)
                page.locator('[data-tf="5D"]').click()
                state = page.evaluate("history.state")
                if label != "malformed":
                    assert state == seed
                    expect(page.locator('.hm-return-note')).to_contain_text("cannot retain")
                else: assert state["foreign"] == 7
                remember("foreign-history-" + label); ctx.close()

            for name in ("regional", "embedded", "shared-shell"):
                server.reset()
                extra = "window.MMXSharedShell={navigate:()=>true};" if name == "shared-shell" else ""
                ctx, page = context(extra=extra)
                path = "/regional-fixture.html" if name == "regional" else "/frame.html" if name == "embedded" else "/sector_heatmap.html"
                page.goto(origin + path, wait_until="domcontentloaded")
                target = page.frame_locator('iframe') if name == "embedded" else page
                target.locator('.hm-tf').first.wait_for()
                target.locator('[data-tf="5D"]').click()
                assert target.locator('.hm-return-note').count() == 0
                state = page.frames[1].evaluate("history.state") if name == "embedded" else page.evaluate("history.state")
                assert state is None
                remember("return-owner-opt-out-" + name); ctx.close()

            server.reset(); ctx, page = context()
            page.goto(origin + "/sector_heatmap.html", wait_until="domcontentloaded"); ready(page)
            page.locator('[data-tf="5D"]').click()
            page.evaluate("location.hash='heatmap-full'")
            expect(page.locator('[data-tf="5D"]')).to_have_class("hm-tf on")
            page.locator('[data-tf="1M"]').click()
            page.evaluate("history.back()")
            page.wait_for_url(origin + "/sector_heatmap.html")
            expect(page.locator('[data-tf="5D"]')).to_have_class("hm-tf on")
            page.evaluate("history.forward()")
            page.wait_for_url("**/sector_heatmap.html#heatmap-full")
            expect(page.locator('[data-tf="1M"]')).to_have_class("hm-tf on")
            remember("native-fragment-entry-configuration-back-forward"); ctx.close()

            server.reset(); ctx, page = context()
            page.goto(origin + "/sector_heatmap.html", wait_until="domcontentloaded"); ready(page)
            page.locator('[data-tf="5D"]').click(); page.locator('.hm-search input').fill("AAPL")
            page.locator('[data-hm-key="AAPL"]').first.click(); page.wait_for_url("**/stock.html#AAPL")
            page.set_viewport_size({"width": 390, "height": 844})
            page.go_back(wait_until="domcontentloaded"); ready(page)
            expect(page.locator('[data-tf="5D"]')).to_have_class("hm-tf on")
            expect(page.locator('.hm-return-note')).to_contain_text("inactive in the mobile list")
            assert page.locator('.hm-mrow').count() == 36
            remember("document-return-across-responsive-layout"); ctx.close()

            for state_name in ("empty", "error"):
                server.reset()
                if state_name == "empty": server.payloads["sp500"]["tiles"] = []
                else: server.errors.add("sp500")
                ctx, page = context(seed={KEY: saved()})
                page.goto(origin + "/sector_heatmap.html", wait_until="domcontentloaded")
                expect(page.locator('.hm-host .hm-empty')).to_contain_text("No heatmap data" if state_name == "empty" else "Could not load")
                expect(page.locator('.hm-return-note')).not_to_contain_text("View settings restored")
                assert page.evaluate(f"history.state[{json.dumps(KEY)}].views.sp500.tf") == "5D"
                remember("unavailable-payload-retains-intent-" + state_name); ctx.close()

            server.reset(); server.snapshot = True
            server.payloads = {key: json.loads((SITE / f"marketdata/{key}_heatmap.json").read_text()) for key in ("sp500", "themes")}
            ctx, page = context(1440)
            page.goto(origin + "/sector_heatmap.html", wait_until="domcontentloaded"); ready(page)
            for map_key in ("sp500", "themes"):
                if map_key == "themes": page.locator('[data-hm-map="themes"]').click(); page.locator('.hm-thtile').first.wait_for()
                expect(page.locator(f'[data-hm-map="{map_key}"]')).to_have_attribute("aria-selected", "true")
                assert len(server.payloads[map_key]["tiles"]) > 0
                assert page.locator('[data-hm-key]').count() > 0
            page.locator('[data-hm-map="sp500"]').click(); ready(page)
            expect(page.locator('[data-hm-map="sp500"]')).to_have_attribute("aria-selected", "true")
            assert not page.locator('.hm-host').evaluate("el=>el.classList.contains('hm-themes')")
            page.screenshot(path=str(out / "committed-feed-desktop.png"), animations="disabled"); shots.append("committed-feed-desktop.png")
            remember("committed-feed-renderer-compatibility", {key: {"tiles": len(value["tiles"]), "asof": value.get("asof"), "source": value.get("source")} for key,value in server.payloads.items()})
            ctx.close()

        finally:
            import sys
            if sys.exc_info()[0] and not page.is_closed():
                try:
                    failure = page.evaluate("({url:location.href,state:history.state,note:document.querySelector('.hm-return-note')?.textContent,active:document.activeElement?.outerHTML.slice(0,500),scrollY:scrollY,items:[...document.querySelectorAll('[data-hm-key]')].slice(0,3).map(e=>({key:e.dataset.hmKey,top:e.getBoundingClientRect().top}))})")
                    (out / 'failure.json').write_text(json.dumps(failure,ensure_ascii=False,indent=2)+'\n')
                    page.screenshot(path=str(out / 'failure.png'),timeout=8000)
                except Exception:
                    pass
            browser.close()
            if not args.canonical or sys.exc_info()[0]:
                server.shutdown(); server.server_close()
            paths = ["templates/heatmap.js", "site/heatmap.js", "templates/sector_heatmap.html.j2", "site/sector_heatmap.html", "scripts/verify_us_heatmap_return_browser.py"]
            report = {"observed_at_utc": datetime.now(timezone.utc).isoformat(), "browser": version,
                      "scope": "Local generated page with synthetic feeds and labelled same-origin detail fixture; bfcache disabled",
                      "passed": len(cases), "cases": cases, "screenshots": shots, "page_errors": errors,
                      "sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}}
            (out / "browser-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps({"passed": len(cases), "report": str(out / "browser-report.json"), "screenshots": len(shots), "page_errors": errors}, ensure_ascii=False))


    if args.canonical:
        server.reset(); server.canonical = True
        sys.path.insert(0, str(ROOT))
        from scripts import capture_page_evidence as cap
        canonical = ROOT / "mockups/evidence/d04-us-heatmap-return-20261104"
        canonical.mkdir(parents=True, exist_ok=True)
        driver = cap.playwright_page_driver(settle_ms=1200)
        try:
            result = cap.run_capture(rows=cap.synthesize_rows(["/sector_heatmap.html"], []), driver=driver,
                base_url=origin, output_dir=canonical / "evidence", manifest_dir=canonical,
                viewports=["desktop", "mobile"], locales=["en", "zh"], themes=["dark", "light"],
                delay_ms=0, timeout_s=20, generated_at=datetime.now(timezone.utc).isoformat(),
                target=cap.site_dir_target(SITE), selection={"routes": ["/sector_heatmap.html"], "scene": "Explicit synthetic public feed and prior native-history entry; no account data or CSS forcing"})
        finally:
            driver.close()
            server.shutdown(); server.server_close()
        (canonical / "manifest.json").write_text(json.dumps(result["manifest"], ensure_ascii=False, indent=2) + "\n")
        (canonical / "smells.json").write_text(json.dumps(result["smells"], ensure_ascii=False, indent=2) + "\n")
        assert result["manifest"]["totals"]["states_captured"] == 8, result["manifest"]["totals"]
        report["canonical_visual_matrix"] = result["manifest"]["totals"]
        (out / "browser-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
        print(json.dumps({"canonical":result["manifest"]["totals"]}))

if __name__ == "__main__":
    main()
