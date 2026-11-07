#!/usr/bin/env python3
"""Finite Chromium proof of the actual standalone heatmap and native history.

Serves the generated page/assets, synthetic populated feeds, and a labelled
detail destination on loopback. It never uses production credentials or data.
The detail fixture proves the incumbent click URL and native Back boundary;
Access cases additionally serve an explicitly labelled Terminal message fixture
at the existing local Terminal origin to verify symbol transport and overlay return.
Neither fixture establishes D07 content, production authentication or acceptance.
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
sys.path.insert(0, str(ROOT))
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
                prior = saved()
                prior["views"]["sp500"]["presentation"] = "list"
                initial = json.dumps({KEY: prior}).replace("<", "\\u003c")
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

        def context(width=1365, lang="en", theme="dark", seed=None, extra="", touch=False, terminal_fixture=False):
            ctx = browser.new_context(viewport={"width": width, "height": 900 if width > 560 else 844}, reduced_motion="reduce", locale="zh-CN" if lang == "zh" else "en-US", has_touch=touch, is_mobile=touch and width <= 560)
            fixture = """<!doctype html><html><title>D04 Terminal message fixture</title><body>
              <h1>Controlled Terminal destination</h1><p>Symbol transport only; no account or market data.</p>
              <p id="fixture-symbol"></p><button id="fixture-close">Return to heatmap</button>
              <script>
              const parentOrigin = PARENT_ORIGIN;
              let symbol = new URLSearchParams(location.search).get('sym') || '';
              window.__receivedSymbols = [];
              function paint() {
                document.getElementById('fixture-symbol').textContent = symbol;
                parent.postMessage({source:'mastermind-terminal',type:'terminal:visual-ready',symbol,path:'/terminal'},parentOrigin);
              }
              addEventListener('message',event=>{
                if(event.source!==parent || event.origin!==parentOrigin || event.data?.source!=='mastermind-dashboard' || event.data.type!=='terminal:set-symbol')return;
                symbol=String(event.data.symbol);window.__receivedSymbols.push(symbol);paint();
              });
              function closeFixture(){parent.postMessage({source:'mastermind-terminal',type:'terminal:close'},parentOrigin)}
              document.getElementById('fixture-close').onclick=closeFixture;
              addEventListener('keydown',event=>{if(event.key==='Escape')closeFixture()});
              paint();
              </script></body></html>""".replace("PARENT_ORIGIN", json.dumps(origin))
            def route_local(route):
                url = urlsplit(route.request.url)
                if url.netloc == urlsplit(origin).netloc:
                    route.continue_()
                elif terminal_fixture and url.netloc == "127.0.0.1:3100" and url.path == "/terminal":
                    route.fulfill(status=200, content_type="text/html", body=fixture)
                else:
                    route.abort()
            ctx.route("**/*", route_local)
            init = f"try{{localStorage.setItem('theme',{json.dumps(theme)});localStorage.setItem('lang',{json.dumps(lang)});}}catch(e){{}}"
            if seed is not None:
                init += f"if(location.pathname==='/sector_heatmap.html') history.replaceState({json.dumps(seed)},'');"
            init += "window.__hmAdds=0;window.__hmRemoves=0;const add=document.addEventListener.bind(document),remove=document.removeEventListener.bind(document);document.addEventListener=function(n,...a){if(n==='hm-refresh')window.__hmAdds++;return add(n,...a)};document.removeEventListener=function(n,...a){if(n==='hm-refresh')window.__hmRemoves++;return remove(n,...a)};"
            init += "window.__d04HistoryPushes=[];const push=history.pushState.bind(history);history.pushState=function(s,...a){window.__d04HistoryPushes.push({overlay:!!s?.__mdxTerminalOverlay,d04:!!s?.['mmx.usHeatmap.v1']});return push(s,...a)};"
            ctx.add_init_script(init + extra)
            page = ctx.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            return ctx, page

        def ready(page):
            page.locator('#heatmap-full [data-hm-key]').first.wait_for()

        def remember(name, detail=None):
            cases.append({"name": name, "status": "PASS", "detail": detail})

        def access_feeds():
            server.reset()
            tiny = copy.deepcopy(server.payloads["sp500"]["tiles"][0])
            tiny.update(t="TINY", name="Small supplied company", name_zh="微型来源公司", size=0.000000001)
            tiny["perf"] = {"1D": None, "5D": 7.25, "1M": 10.0}
            server.payloads["sp500"]["tiles"].append(tiny)
            server.payloads["sp500"]["n_tiles"] = len(server.payloads["sp500"]["tiles"])
            tile = server.payloads["themes"]["tiles"][0]
            tile["members"] = [{"t": f"MEM{i:02d}", "name": f"Complete supplied member {i}", "name_zh": f"完整来源成员 {i}",
                                "perf": {"1D": None if i == 39 else i / 10, "5D": i / 5, "1M": i / 3}} for i in range(40)]
            for theme in server.payloads["themes"]["tiles"]:
                theme["size"] = len(theme["members"])
            return tiny, tile

        def overlay_round_trip(page, link, ticker, width, touch=False):
            exact = page.url
            link.evaluate("el=>window.__accessOrigin=el")
            page.evaluate("window.__accessPriorFrame=document.querySelector('#mm-terminal-overlay .mmto-frame')")
            before_length = page.evaluate("history.length")
            before_pushes = page.evaluate("window.__d04HistoryPushes.length")
            before_y = page.evaluate("scrollY")
            if touch:
                link.tap()
            else:
                link.focus()
                link.press("Enter")
            page.wait_for_function("window.MDXTerminalOverlay.isOpen()")
            frame = page.frame_locator('#mm-terminal-overlay .mmto-frame')
            expect(frame.locator('#fixture-symbol')).to_have_text(ticker)
            target = page.locator('#mm-terminal-overlay .mmto-newtab').get_attribute("href")
            assert f"sym={ticker}" in target, target
            if page.evaluate("!!window.__accessPriorFrame"):
                assert page.evaluate("window.__accessPriorFrame===document.querySelector('#mm-terminal-overlay .mmto-frame')") == (width > 700)
            page.wait_for_function("document.querySelector('#mm-terminal-overlay').classList.contains('is-ready')")
            page.wait_for_timeout(220)  # Normal return follows the incumbent 180ms focus callback.
            guard = page.evaluate("history.state")
            assert "__mdxTerminalOverlay" in guard and KEY in guard["dashboardState"]
            pushes = page.evaluate("window.__d04HistoryPushes")
            assert len(pushes) == before_pushes + 1 and pushes[-1] == {"overlay":True,"d04":False}, pushes
            assert page.url == exact
            page.evaluate("history.back()")
            page.wait_for_function("!window.MDXTerminalOverlay.isOpen() && !history.state?.__mdxTerminalOverlay")
            assert link.evaluate("el=>el===window.__accessOrigin && el.isConnected")
            assert page.url == exact
            # A second open after Back replaces the native forward slot.
            assert page.evaluate("history.length") <= before_length + 1
            assert page.evaluate("window.__d04HistoryPushes.length") == before_pushes + 1
            if width > 700:
                expect(link).to_be_focused()
            # The incumbent phone owner intentionally does not refocus the row.
            # It owns close, guard traversal and delayed scroll restoration.
            assert page.evaluate("!document.documentElement.classList.contains('mm-terminal-lock')")
            return {"symbol": ticker, "same_origin_node": True, "desktop_focus": width > 700,
                    "history_owner": "MDXTerminalOverlay", "scroll_before_activation": before_y}

        def assert_access_geometry(page):
            result = page.evaluate("""() => ({
              viewport:innerWidth, width:document.documentElement.scrollWidth,
              targets:[...document.querySelectorAll('#heatmap-full button,#heatmap-full input,#heatmap-full summary,#heatmap-full a.hm-mrow')]
                .filter(e=>e.getClientRects().length && !e.closest('details:not([open]) .hm-member-list'))
                .map(e=>({label:e.getAttribute('aria-label')||e.textContent.trim().slice(0,80),
                  width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}))
            })""")
            assert result["width"] <= result["viewport"], result
            assert all(t["width"] >= 44 and t["height"] >= 44 for t in result["targets"]), result
            return result

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
            expect(page.locator('.hm-search input')).to_be_visible()
            expect(page.locator('.hm-search input')).to_have_value("AAPL")
            assert page.locator('.hm-mrow').count() == 1
            expect(page.locator('.hm-list-status')).to_contain_text("显示 1 个")
            page.screenshot(path=str(out / "mobile-retained-query.png")); shots.append("mobile-retained-query.png")
            remember("mobile-retained-query-applied"); ctx.close()

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
                assert target.locator('.hm-presentation').count() == 0
                assert target.locator('.hm-us-access').count() == 0
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
            expect(page.locator('.hm-search input')).to_have_value("AAPL")
            assert page.locator('.hm-mrow').count() == 1
            expect(page.locator('.hm-list-status')).to_contain_text("1 of 36")
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


            tiny, theme_tile = access_feeds()
            ctx, page = context(1440, terminal_fixture=True)
            page.goto(origin + "/sector_heatmap.html", wait_until="domcontentloaded"); ready(page)
            assert page.locator('.hm-tile[data-hm-key="TINY"]').count() == 0
            # Start at the heatmap's first native control and traverse to List.
            page.locator('[data-hm-map="sp500"]').focus()
            for _ in range(12):
                if page.evaluate("document.activeElement.getAttribute('data-hm-presentation')==='list'"):
                    break
                page.keyboard.press("Tab")
            assert page.evaluate("document.activeElement.getAttribute('data-hm-presentation')==='list'")
            page.keyboard.press("Enter")
            supplied = sorted(x["t"] for x in server.payloads["sp500"]["tiles"])
            assert sorted(page.locator('.hm-tm a.hm-mrow').evaluate_all("els=>els.map(e=>e.dataset.hmKey)")) == supplied
            summary_before = page.locator('.hx-stats').inner_text()
            page.keyboard.press("Tab")
            expect(page.locator('.hm-search input')).to_be_focused()
            page.keyboard.type("TINY")
            expect(page.locator('.hm-tm a.hm-mrow')).to_have_count(1)
            expect(page.locator('.hm-list-status')).to_contain_text("1 of 37")
            assert page.locator('.hx-stats').inner_text() == summary_before
            row = page.locator('.hm-tm a[href="stock.html#TINY"]')
            row.scroll_into_view_if_needed()
            detail = overlay_round_trip(page, row, "TINY", 1440)
            expect(page.locator('.hm-search input')).to_have_value("TINY")
            expect(page.locator('[data-hm-presentation="list"]')).to_have_attribute("aria-pressed", "true")
            page.locator('.hm-search input').fill("微型来源公司")
            expect(page.locator('.hm-tm a.hm-mrow')).to_have_count(1)
            page.locator('.hm-search input').fill("NO-SUCH-COMPANY")
            expect(page.locator('.hm-empty')).to_contain_text("No matches")
            expect(page.locator('.hm-list-status')).to_contain_text("0 of 37")
            page.locator('.hm-search input').fill("")
            assert sorted(page.locator('.hm-tm a.hm-mrow').evaluate_all("els=>els.map(e=>e.dataset.hmKey)")) == supplied
            page.locator('[data-tf="1D"]').focus(); page.keyboard.press("ArrowRight")
            expect(page.locator('[data-tf="5D"]')).to_have_attribute("aria-selected", "true")
            expect(page.locator('[data-tf="5D"]')).to_be_focused()
            page.evaluate("window.scrollTo(0,document.querySelector('.hm-bar').getBoundingClientRect().top+scrollY-90)")
            page.screenshot(path=str(out / "accessible-dense-list-desktop.png"), animations="disabled"); shots.append("accessible-dense-list-desktop.png")
            remember("culled-company-keyboard-list-query-detail-return", {**detail, "supplied_rows": len(supplied), "matched_rows_and_full_scope": True})
            ctx.close()

            access_feeds(); ctx, page = context(1440, terminal_fixture=True)
            page.goto(origin + "/sector_heatmap.html", wait_until="domcontentloaded"); ready(page)
            page.locator('[data-hm-map="themes"]').focus(); page.keyboard.press("Enter")
            page.locator('.hm-thtile').first.wait_for()
            page.locator('[data-hm-presentation="list"]').focus(); page.keyboard.press("Enter")
            disclosure = page.locator('details[data-hm-disclosure="theme-0"]')
            disclosure.locator('summary').focus(); page.keyboard.press("Enter")
            expect(disclosure).to_have_attribute("open", "")
            expect(disclosure.locator('.hm-member-row')).to_have_count(40)
            assert set(disclosure.locator('.hm-member-row').evaluate_all("els=>els.map(e=>e.getAttribute('href'))")) == {f"stock.html#MEM{i:02d}" for i in range(40)}
            expect(disclosure.locator('a[href="stock.html#MEM39"] .hm-mpc')).to_have_text("No data")
            expect(disclosure.locator('a[href="stock.html#MEM00"] .hm-mpc')).to_contain_text("0.00%")
            page.locator('.hm-search input').fill("MEM39")
            expect(page.locator('details.hm-members')).to_have_count(1)
            expect(disclosure.locator('.hm-member-row')).to_have_count(1)
            member = disclosure.locator('a[href="stock.html#MEM39"]')
            member.scroll_into_view_if_needed()
            detail = overlay_round_trip(page, member, "MEM39", 1440)
            assert page.evaluate(f"history.state[{json.dumps(KEY)}].views.themes.presentation") == "list"
            page.locator('[data-hm-map="sp500"]').click(); ready(page)
            page.locator('[data-hm-map="themes"]').click()
            expect(page.locator('.hm-search input')).to_have_value("MEM39")
            expect(disclosure).to_have_attribute("open", "")
            page.locator('.hm-search input').fill("")
            expect(disclosure.locator('.hm-member-row')).to_have_count(40)
            page.evaluate("window.scrollTo(0,document.querySelector('.hm-bar').getBoundingClientRect().top+scrollY-90)")
            page.screenshot(path=str(out / "accessible-theme-members-desktop.png"), animations="disabled"); shots.append("accessible-theme-members-desktop.png")
            remember("complete-theme-members-keyboard-search-overlay-return", {**detail, "supplied_members": 40, "missing_not_zero": True})
            ctx.close()

            for width, lang, theme in [(w,l,t) for w in (320,390,1440) for l in ("en","zh") for t in ("dark","light")] + [(900,"en","light"),(900,"zh","dark")]:
                access_feeds(); ctx, page = context(width, lang, theme, touch=True, terminal_fixture=True)
                page.goto(origin + "/sector_heatmap.html", wait_until="domcontentloaded"); ready(page)
                assert page.evaluate("navigator.maxTouchPoints>0 && matchMedia('(pointer:coarse)').matches")
                if width > 560:
                    page.locator('[data-hm-presentation="list"]').tap()
                page.locator('.hm-search input').tap()
                page.locator('.hm-search input').fill("TINY")
                expect(page.locator('.hm-tm a.hm-mrow')).to_have_count(1)
                page.locator('[data-tf="5D"]').tap()
                page.locator('[data-s="move"]').tap()
                row = page.locator('.hm-tm a[href="stock.html#TINY"]'); row.scroll_into_view_if_needed()
                stock_detail = overlay_round_trip(page, row, "TINY", width, touch=True)
                expect(page.locator('.hm-search input')).to_have_value("TINY")
                page.locator('[data-hm-map="themes"]').tap()
                if width > 560:
                    page.locator('.hm-thtile').first.wait_for(); page.locator('[data-hm-presentation="list"]').tap()
                disclosure = page.locator('details[data-hm-disclosure="theme-0"]')
                disclosure.locator('summary').tap()
                expect(disclosure.locator('.hm-member-row')).to_have_count(40)
                page.locator('.hm-search input').fill("MEM39")
                member = disclosure.locator('a[href="stock.html#MEM39"]'); member.scroll_into_view_if_needed()
                member_detail = overlay_round_trip(page, member, "MEM39", width, touch=True)
                expect(disclosure).to_have_attribute("open", "")
                expect(page.locator('.hm-search input')).to_have_value("MEM39")
                geometry = assert_access_geometry(page)
                page.evaluate("window.scrollTo(0,document.querySelector('.hm-bar').getBoundingClientRect().top+scrollY-90)")
                name = f"accessible-touch-{width}-{lang}-{theme}"
                page.screenshot(path=str(out / (name + ".png")), animations="disabled"); shots.append(name + ".png")
                remember(name, {"stock":stock_detail,"theme_member":member_detail,"geometry":geometry,"physical_device":False})
                ctx.close()

            access_feeds(); ctx, page = context(1440, terminal_fixture=True)
            page.goto(origin + "/sector_heatmap.html", wait_until="domcontentloaded"); ready(page)
            page.locator('[data-hm-presentation="list"]').click()
            row = page.locator('.hm-tm a[href="stock.html#NVDA"]')
            row.focus()
            page.evaluate("document.documentElement.dataset.theme='light';document.dispatchEvent(new Event('themechange'))")
            expect(row).to_be_focused()
            page.evaluate("document.documentElement.dataset.lang='zh';document.dispatchEvent(new Event('langchange'))")
            expect(row).to_be_focused()
            expect(page.locator('.hm-search input')).to_have_attribute("aria-label","查找公司或主题成员")
            expect(page.locator('[data-hm-presentation="list"]')).to_have_attribute("aria-pressed","true")
            row.evaluate("el=>window.__stableListRow=el")
            page.set_viewport_size({"width":900,"height":900})
            page.wait_for_timeout(220)  # Exercise the existing 150ms resize callback.
            page.wait_for_function("document.querySelector('.hm-tm a[href=\"stock.html#NVDA\"]')===window.__stableListRow")
            expect(row).to_be_focused()
            # A true document reload restores the same logical row and List choice.
            page.reload(wait_until="domcontentloaded"); ready(page)
            expect(page.locator('[data-hm-presentation="list"]')).to_have_attribute("aria-pressed","true")
            expect(page.locator('.hm-tm a[href="stock.html#NVDA"]')).to_be_focused()
            remember("list-live-theme-language-resize-and-native-reload-focus")
            ctx.close()

            access_feeds()
            invalid = saved()
            invalid["views"]["sp500"].update(presentation={"invalid":True},expanded=[None,{},7,"theme-0"])
            ctx, page = context(seed={KEY:invalid})
            page.goto(origin + "/sector_heatmap.html", wait_until="domcontentloaded"); ready(page)
            expect(page.locator('[data-hm-presentation="map"]')).to_have_attribute("aria-pressed","true")
            page.locator('[data-hm-presentation="list"]').click()
            assert page.evaluate(f"history.state[{json.dumps(KEY)}].views.sp500.expanded") == ["theme-0"]
            remember("optional-presentation-and-disclosure-state-validation")
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
                      "scope": "Local generated page with synthetic feeds; labelled same-origin detail and cross-origin local Terminal message fixtures; bfcache disabled",
                      "passed": len(cases), "cases": cases, "screenshots": shots, "page_errors": errors,
                      "sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}}
            (out / "browser-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            print(json.dumps({"passed": len(cases), "report": str(out / "browser-report.json"), "screenshots": len(shots), "page_errors": errors}, ensure_ascii=False))


    if args.canonical:
        server.reset(); server.canonical = True
        from scripts import capture_page_evidence as cap
        canonical = ROOT / "mockups/evidence/d04-us-heatmap-return-20261104"
        canonical.mkdir(parents=True, exist_ok=True)
        driver = cap.playwright_page_driver(settle_ms=1200)
        try:
            result = cap.run_capture(rows=cap.synthesize_rows(["/sector_heatmap.html"], []), driver=driver,
                base_url=origin, output_dir=canonical / "evidence", manifest_dir=canonical,
                viewports=["desktop", "mobile"], locales=["en", "zh"], themes=["dark", "light"],
                delay_ms=0, timeout_s=20, generated_at=datetime.now(timezone.utc).isoformat(),
                target=cap.site_dir_target(SITE), selection={"routes": ["/sector_heatmap.html"], "scene": "Explicit synthetic public feed and prior native-history List entry; real focus/hover interactions, no account data or CSS forcing"},
                force_states=cap.parse_force_states(["list-focus:focus(.hm-tm a.hm-mrow)", "list-hover:hover(.hm-tm a.hm-mrow)"]))
        finally:
            driver.close()
            server.shutdown(); server.server_close()
        (canonical / "manifest.json").write_text(json.dumps(result["manifest"], ensure_ascii=False, indent=2) + "\n")
        (canonical / "smells.json").write_text(json.dumps(result["smells"], ensure_ascii=False, indent=2) + "\n")
        assert result["manifest"]["totals"]["states_captured"] == 24, result["manifest"]["totals"]
        report["canonical_visual_matrix"] = result["manifest"]["totals"]
        (out / "browser-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
        print(json.dumps({"canonical":result["manifest"]["totals"]}))

if __name__ == "__main__":
    main()
