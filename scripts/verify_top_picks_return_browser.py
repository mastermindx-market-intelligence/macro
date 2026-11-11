#!/usr/bin/env python3
"""Bounded browser proof of Top Picks controls, native return and incumbent ownership.

Uses the committed generated page and exact served assets on loopback. Company
and Terminal destinations are labelled fixtures; this does not accept D07,
authentication, live data, production or whole-programme journeys.
"""
from __future__ import annotations

import argparse
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
KEY = "mmx.topPicks.v1"
SECTOR = "Information Technology"


class Server(ThreadingHTTPServer):
    mutation = ""
    load_gate = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        path = urlsplit(self.path).path
        status, mime = 200, "text/html; charset=utf-8"
        if path == "/discovery.html":
            source = (SITE / "discovery.html").read_text()
            if self.server.mutation:
                source = source.replace('<script src="discovery.js', "<script>" + self.server.mutation + "</script>\n" + '<script src="discovery.js', 1)
            if self.server.load_gate is not None:
                source = source.replace("</body>", '<img src="/deferred-proof.svg" alt="" width="1" height="1"></body>')
            source = source.replace("</body>", '<aside style="position:fixed;bottom:6px;right:6px;z-index:2147483647;padding:5px 8px;border-radius:5px;background:#242332;color:white;font:11px sans-serif">D04 local proof · committed ranking snapshot</aside></body>')
            body = source.encode()
        elif path == "/deferred-proof.svg":
            self.server.load_gate.wait(8)
            mime, body = "image/svg+xml", b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"></svg>'
        elif path == "/stock.html":
            body = b'<!doctype html><title>D04 company destination fixture</title><h1>Company destination fixture</h1><p>URL and native return proof only.</p><button onclick="history.back()">Back</button>'
        elif path == "/frame.html":
            body = b'<!doctype html><iframe title="Shared owner fixture" src="/discovery.html" width="1000" height="800"></iframe>'
        elif path.startswith("/api/"):
            status, mime, body = 403, "application/json", b"{}"
        else:
            target = (SITE / path.lstrip("/")).resolve()
            if SITE.resolve() in target.parents and target.is_file():
                body = target.read_bytes()
                mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            else:
                status, mime, body = 404, "text/plain", b"Fixture resource absent"
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass


def saved(**over):
    value = {"version": 1, "path": "/discovery.html", "tab": "sector", "side": "weak",
             "sector": SECTOR, "hideStretch": True, "asOf": "2026-11-03", "position": None}
    value.update(over)
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "ux-evidence/d04-top-picks-return-20261104")
    args = ap.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    server = Server(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    cases, shots, errors, failures = [], [], [], []
    responses = []

    def passed(name, **details):
        cases.append({"name": name, "passed": True, **details})

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--disable-features=BackForwardCache"])
        browser_version = browser.version

        def context(width=1440, lang="en", theme="dark", seed=None, extra="", touch=False):
            ctx = browser.new_context(viewport={"width": width, "height": 900 if width > 560 else 844},
                                      locale="zh-CN" if lang == "zh" else "en-US", reduced_motion="reduce",
                                      has_touch=touch, is_mobile=touch and width <= 560)
            fixture = """<!doctype html><title>D04 Terminal destination fixture</title>
            <h1>Controlled Terminal destination</h1><p>Symbol transport only.</p>
            <p id="fixture-symbol"></p><button id="fixture-close">Return</button>
            <script>
            const parentOrigin=PARENT_ORIGIN;
            let symbol=new URLSearchParams(location.search).get('sym')||'';
            function paint(){document.querySelector('#fixture-symbol').textContent=symbol;
              parent.postMessage({source:'mastermind-terminal',type:'terminal:visual-ready',symbol,path:'/terminal'},parentOrigin);}
            addEventListener('message',e=>{if(e.source===parent&&e.origin===parentOrigin&&e.data?.source==='mastermind-dashboard'&&e.data.type==='terminal:set-symbol'){symbol=String(e.data.symbol);paint();}});
            document.querySelector('#fixture-close').onclick=()=>parent.postMessage({source:'mastermind-terminal',type:'terminal:close'},parentOrigin);
            paint();</script>""".replace("PARENT_ORIGIN", json.dumps(origin))

            def route_local(route):
                u = urlsplit(route.request.url)
                if u.netloc == urlsplit(origin).netloc:
                    route.continue_()
                elif u.netloc == "127.0.0.1:3100" and u.path == "/terminal":
                    route.fulfill(status=200, content_type="text/html", body=fixture)
                else:
                    route.abort()

            ctx.route("**/*", route_local)
            init = f"localStorage.setItem('lang',{json.dumps(lang)});localStorage.setItem('theme',{json.dumps(theme)});"
            if seed is not None:
                init += "if(location.pathname==='/discovery.html'&&!sessionStorage.__d04Seeded){sessionStorage.__d04Seeded='1';history.replaceState(JSON.parse(" + json.dumps(json.dumps(seed)) + "),'');}"
            init += "window.__d04Pushes=[];const push=history.pushState.bind(history);history.pushState=function(s,...a){window.__d04Pushes.push({overlay:!!s?.__mdxTerminalOverlay,local:!!s?.['mmx.topPicks.v1']});return push(s,...a)};"
            ctx.add_init_script(init + extra)
            page = ctx.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("response", lambda r: responses.append({"url": r.url, "status": r.status}) if urlsplit(r.url).path in {"/discovery.js", "/discovery-controls.css"} else None)
            return ctx, page

        def ready(page):
            page.locator('[data-discovery-key]').first.wait_for(state="attached")
            page.wait_for_function("document.querySelector('#discovery-filter-status').textContent.length>0")

        def settle(page):
            page.evaluate("() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))")

        def state(page):
            return page.evaluate(f"history.state?.[{json.dumps(KEY)}]")

        def shot(page, name):
            path = out / (name + ".png")
            page.screenshot(path=str(path))
            shots.append(path.name)

        def row_key(link):
            return link.get_attribute("data-discovery-key")

        def assert_geometry(page):
            geometry = page.evaluate("""() => ({
              width:document.documentElement.scrollWidth, viewport:innerWidth,
              controls:[...document.querySelectorAll('.tabs .tabbtn,.segbtn,.secsel,.filt'+(innerWidth<=760?',a[data-discovery-key]':''))]
                .filter(e=>e.getClientRects().length)
                .map(e=>({id:e.id||e.className,height:e.getBoundingClientRect().height,width:e.getBoundingClientRect().width}))
            })""")
            assert geometry["width"] <= geometry["viewport"], geometry
            assert all(x["height"] >= 44 and x["width"] >= 44 for x in geometry["controls"]), geometry
            return geometry

        try:
            for width in (1440, 390):
                for lang in ("en", "zh"):
                    for theme in ("dark", "light"):
                        server.mutation = ""
                        name = f"{width}-{lang}-{theme}"
                        ctx, page = context(width, lang, theme, {"incumbent": {"keep": ["exact", 3]}}, touch=width < 560)
                        exact = origin + "/discovery.html?study=a%2Fb&study=c+d#saved-context"
                        page.goto(exact, wait_until="domcontentloaded"); ready(page)
                        page.locator('#discovery-tab-global').focus()
                        page.keyboard.press("End")
                        expect(page.locator('#discovery-tab-sector')).to_have_attribute("aria-selected", "true")
                        page.keyboard.press("Home")
                        expect(page.locator('#discovery-tab-global')).to_be_focused()
                        page.locator('#hideStretch').check()
                        assert page.locator('#tab-global tr[data-grade="stretched"]:visible,#tab-global tr[data-grade="parabolic"]:visible').count() == 0
                        page.locator('#seg-weak').click()
                        expect(page.locator('#seg-weak')).to_have_attribute("aria-pressed", "true")
                        page.locator('#discovery-tab-sector').click()
                        page.locator('#secsel').select_option(SECTOR)
                        current = page.locator('[data-grp="seclist"]:visible')
                        assert current.get_attribute('data-sector') == SECTOR
                        assert current.locator('tr[data-grade][hidden]').count() == 0
                        assert current.locator('tr[data-grade]').count() == 24
                        region_names = current.locator('.discovery-scroll').evaluate_all("els=>els.map(e=>e.getAttribute('aria-label'))")
                        assert len(set(region_names)) == 2, region_names
                        page.locator('#discovery-tab-sectors').click()
                        expect(page.locator('#tab-sectors')).to_be_visible()
                        page.locator('#discovery-tab-sector').click()
                        expect(page.locator('#secsel')).to_have_value(SECTOR)
                        page.evaluate("window.setLang(document.documentElement.dataset.lang==='zh'?'en':'zh')")
                        expect(page.locator('#secsel')).to_have_value(SECTOR)
                        page.evaluate(f"window.setLang({json.dumps(lang)})")
                        page.locator('#secsel').scroll_into_view_if_needed(); settle(page)
                        geometry = assert_geometry(page)
                        shot(page, "top-picks-" + name)
                        passed("controls-filter-scope-aria-locale-" + name, geometry=geometry, sector_rows=24)
                        link = current.locator('a[data-discovery-key]').nth(5)
                        key = row_key(link); href = link.get_attribute('href'); ticker = json.loads(key)[3]
                        link.scroll_into_view_if_needed(); link.focus()
                        link.evaluate("el=>window.__d04Origin=el")
                        length = page.evaluate("history.length")
                        if width > 560:
                            link.press("Enter")
                        else:
                            link.tap()
                        page.wait_for_function("window.MDXTerminalOverlay?.isOpen()")
                        guard = page.evaluate("history.state")
                        assert guard["dashboardState"][KEY]["position"]["key"] == key
                        assert KEY not in guard
                        expect(page.frame_locator('#mm-terminal-overlay .mmto-frame').locator('#fixture-symbol')).to_have_text(ticker)
                        page.wait_for_function("document.querySelector('#mm-terminal-overlay').classList.contains('is-ready')")
                        page.wait_for_timeout(220)
                        page.evaluate("history.back()")
                        page.wait_for_function("!window.MDXTerminalOverlay.isOpen()&&!history.state?.__mdxTerminalOverlay")
                        assert page.evaluate("window.__d04Origin.isConnected")
                        assert page.evaluate("window.__d04Pushes.every(x=>x.overlay&&!x.local)")
                        if width > 560:
                            expect(link).to_be_focused()
                        passed("incumbent-overlay-return-" + name, key=key, destination=href)
                        # The unchanged native URL is also a supported hard-navigation path.
                        link.scroll_into_view_if_needed(); link.focus()
                        page.goto(origin + "/" + href)
                        page.go_back(wait_until="domcontentloaded"); ready(page); settle(page)
                        expect(page.locator('#secsel')).to_have_value(SECTOR)
                        assert page.evaluate("document.activeElement.getAttribute('data-discovery-key')") == key
                        assert state(page)["position"]["key"] == key
                        passed("native-document-back-" + name, key=key, destination=href,
                               navigation="explicit same-origin company URL after focused source link")
                        assert page.url == exact
                        assert state(page)["hideStretch"] and state(page)["side"] == "weak"
                        assert page.evaluate("history.state.incumbent") == {"keep": ["exact", 3]}
                        assert page.evaluate("history.scrollRestoration") == "auto"
                        shot(page, "return-" + name)
                        ctx.close()

            # Narrow native return is exercised separately from the incumbent phone overlay.
            server.mutation = ""
            ctx, page = context(320, "zh", "light", touch=True)
            page.goto(origin + "/discovery.html"); ready(page)
            page.locator('#seg-weak').click(); page.locator('#hideStretch').check()
            link = page.locator('#g-weak a[data-discovery-key]:visible').nth(3)
            link.scroll_into_view_if_needed(); link.focus()
            key = row_key(link); href = link.get_attribute('href')
            page.goto(origin + "/" + href)
            page.go_back(wait_until="domcontentloaded"); ready(page); settle(page)
            assert state(page)["side"] == "weak" and state(page)["hideStretch"]
            assert page.evaluate("document.activeElement.getAttribute('data-discovery-key')") == key
            assert_geometry(page); shot(page, "native-return-320-zh-light")
            passed("narrow-native-return", key=key, navigation="explicit same-origin company URL after focused source link")
            ctx.close()

            # Updated source order/time, removed origin row, and removed source sector.
            for mode in ("reordered", "missing-row", "missing-sector"):
                server.mutation = ""
                ctx, page = context(seed={"incumbent": 17})
                page.goto(origin + "/discovery.html"); ready(page)
                page.locator('#discovery-tab-sector').click(); page.locator('#secsel').select_option(SECTOR)
                link = page.locator('[data-grp="seclist"]:visible a[data-discovery-key]').nth(4)
                key = row_key(link); href = link.get_attribute("href")
                link.scroll_into_view_if_needed(); link.focus()
                page.goto(origin + "/" + href)
                if mode == "reordered":
                    server.mutation = "document.body.dataset.discoveryAsof='2026-11-04';const s=document.querySelector('#secsel');[...s.options].reverse().forEach(o=>s.append(o));const p=document.querySelector('[data-grp=seclist]').parentNode;[...p.querySelectorAll('[data-grp=seclist]')].reverse().forEach(x=>p.append(x));"
                elif mode == "missing-row":
                    server.mutation = "const g=[...document.querySelectorAll('[data-grp=seclist]')].find(e=>e.dataset.sector===" + json.dumps(SECTOR) + ");[...g.querySelectorAll('a')].filter(a=>a.getAttribute('href')===" + json.dumps(href) + ").forEach(a=>a.closest('tr').remove());"
                else:
                    server.mutation = "[...document.querySelector('#secsel').options].filter(o=>o.value===" + json.dumps(SECTOR) + ").forEach(o=>o.remove());[...document.querySelectorAll('[data-grp=seclist]')].filter(e=>e.dataset.sector===" + json.dumps(SECTOR) + ").forEach(e=>e.remove());"
                page.go_back(wait_until="domcontentloaded"); ready(page); settle(page)
                note = page.locator('#discovery-return-status').inner_text()
                if mode == "reordered":
                    expect(page.locator('#secsel')).to_have_value(SECTOR)
                    assert page.locator('[data-grp=seclist]:visible').get_attribute("data-sector") == SECTOR
                    assert "source date has changed" in note
                    assert page.evaluate("document.activeElement.getAttribute('data-discovery-key')") == key
                else:
                    expect(page.locator('#secsel')).to_be_focused()
                    assert "no longer" in note
                    if mode == "missing-sector":
                        expect(page.locator('#secsel')).to_have_value("")
                        assert page.locator('[data-grp=seclist]:visible').count() == 0
                shot(page, mode); passed(mode, note=note, original_key=key)
                ctx.close()

            # Malformed owned state cannot select arbitrary DOM or break controls.
            server.mutation = ""
            invalid = [
                ("version", {"version": 9}), ("path", {"path": "/another.html"}),
                ("tab", {"tab": "untrusted"}), ("side", {"side": "untrusted"}),
                ("sector-size", {"sector": "x" * 161}), ("filter-type", {"hideStretch": "yes"}),
                ("source-type", {"asOf": 9}),
                ("position", {"position": {"key": "bad", "focus": "bad", "offset": 0, "x": -1, "y": 0, "tableLeft": 0}}),
            ]
            for label, over in invalid:
                ctx, page = context(seed={"incumbent": {"keep": True}, KEY: saved(**over)})
                page.goto(origin + "/discovery.html"); ready(page); settle(page)
                assert page.locator('#discovery-return-status').is_visible()
                assert page.evaluate("history.state.incumbent.keep") is True
                page.locator('#discovery-tab-global').click()
                page.locator('#hideStretch').check()
                passed("invalid-owned-" + label)
                ctx.close()

            for label, seed, extra in [
                ("foreign-string", "foreign", ""),
                ("foreign-array", [1, "foreign"], ""),
                ("replace-failure", {"incumbent": 7}, "if(location.pathname==='/discovery.html')history.replaceState=function(){throw new Error('test write refusal')};"),
            ]:
                ctx, page = context(seed=seed, extra=extra)
                page.goto(origin + "/discovery.html"); ready(page)
                page.locator('#hideStretch').check()
                assert page.evaluate("history.state") == seed
                assert "cannot retain" in page.locator('#discovery-return-status').inner_text()
                passed(label)
                ctx.close()

            # Standalone adapter opts out before frame handshake and under an installed shell.
            ctx, page = context(seed={"incumbent": "frame"})
            page.goto(origin + "/frame.html")
            frame = page.frame_locator('iframe')
            frame.locator('#discovery-filter-status').wait_for()
            frame.locator('#discovery-tab-sector').click()
            frame.locator('#secsel').select_option(SECTOR)
            child = page.frames[1]
            assert child.evaluate("history.state") == {"incumbent": "frame"}
            passed("framed-early-opt-out")
            ctx.close()
            ctx, page = context(seed={"incumbent": "shell"}, extra="window.MMXSharedShell={fixture:true};")
            page.goto(origin + "/discovery.html"); ready(page)
            page.locator('#hideStretch').check()
            assert page.evaluate("history.state") == {"incumbent": "shell"}
            passed("shared-shell-opt-out")
            ctx.close()

            # Delay animation callbacks, then transfer focus/control ownership before release.
            position = {"key": "", "focus": "control:seg-weak", "offset": 0, "x": 0, "y": 800, "tableLeft": 0}
            extra = "const raf=requestAnimationFrame.bind(window);window.__d04Frames=[];window.requestAnimationFrame=cb=>{window.__d04Frames.push(cb);return window.__d04Frames.length};window.__releaseD04=()=>{window.requestAnimationFrame=raf;window.__d04Frames.splice(0).forEach(cb=>raf(cb))};"
            ctx, page = context(seed={KEY: saved(tab="global", hideStretch=False, position=position)}, extra=extra)
            page.goto(origin + "/discovery.html"); ready(page)
            page.evaluate("document.querySelector('#hideStretch').focus();document.querySelector('#hideStretch').checked=true;document.querySelector('#hideStretch').dispatchEvent(new Event('change',{bubbles:true}));scrollTo(0,123);window.__laterPanelTop=document.querySelector('body > .panel').getBoundingClientRect().top;window.__releaseD04()")
            settle(page)
            expect(page.locator('#hideStretch')).to_be_focused()
            expect(page.locator('#hideStretch')).to_be_checked()
            assert page.evaluate("Math.abs(document.querySelector('body > .panel').getBoundingClientRect().top-window.__laterPanelTop)") < 3
            passed("later-deliberate-focus-and-filter-preserved", visual_anchor_preserved=True,
                   note="Raw scroll pixels may change as the incumbent header changes geometry; visible content position and focus are the invariant.")
            ctx.close()

            # Same-document native fragment traversal keeps each entry distinct.
            server.mutation = ""
            ctx, page = context()
            page.goto(origin + "/discovery.html?keep=a%2Fb"); ready(page)
            page.locator('#discovery-tab-sector').click(); page.locator('#secsel').select_option("Energy")
            page.evaluate("location.hash='second-entry'")
            page.wait_for_function("location.hash==='#second-entry'")
            settle(page)
            page.locator('#discovery-tab-global').click(); page.locator('#seg-weak').click(); page.locator('#hideStretch').check()
            page.evaluate("history.back()"); page.wait_for_function("location.hash===''"); settle(page)
            expect(page.locator('#discovery-tab-sector')).to_have_attribute("aria-selected", "true")
            expect(page.locator('#secsel')).to_have_value("Energy")
            assert state(page)["tab"] == "sector"
            page.evaluate("history.forward()"); page.wait_for_function("location.hash==='#second-entry'"); settle(page)
            expect(page.locator('#discovery-tab-global')).to_have_attribute("aria-selected", "true")
            expect(page.locator('#seg-weak')).to_have_attribute("aria-pressed", "true")
            expect(page.locator('#hideStretch')).to_be_checked()
            assert page.evaluate("location.search") == "?keep=a%2Fb"
            passed("same-document-native-back-forward")
            ctx.close()

            # Modified key chords belong to the browser/OS, not the ARIA tab chooser.
            ctx, page = context()
            page.goto(origin + "/discovery.html"); ready(page)
            page.locator('#discovery-tab-sectors').click()
            for modifier in ("altKey", "ctrlKey", "metaKey", "shiftKey"):
                cancelled = page.locator('#discovery-tab-sectors').evaluate(
                    "(el,modifier)=>{const e=new KeyboardEvent('keydown',{key:'ArrowLeft',bubbles:true,cancelable:true,[modifier]:true});el.dispatchEvent(e);return e.defaultPrevented}", modifier)
                assert not cancelled, modifier + " chord was consumed by page tabs"
                expect(page.locator('#discovery-tab-sectors')).to_have_attribute("aria-selected", "true")
            passed("modified-key-chords-preserve-browser-ownership",
                   limitation="Checks event ownership, not OS/browser-chrome shortcut execution.")
            ctx.close()

            # Native same-document history owns scroll, even after a stale stock-origin capture.
            ctx, page = context()
            page.goto(origin + "/discovery.html?keep=scroll"); ready(page)
            stock = page.locator('#g-strong [data-discovery-key]').nth(2)
            stock.focus(); settle(page)
            page.mouse.wheel(0, 420); settle(page)
            panel = page.locator("body > .panel").first
            original_top = panel.evaluate("el=>el.getBoundingClientRect().top")
            captured_y = state(page)["position"]["y"]
            assert abs(page.evaluate("scrollY") - captured_y) > 200
            page.evaluate("location.hash='scroll-second-entry'")
            page.wait_for_function("location.hash==='#scroll-second-entry'"); settle(page)
            page.mouse.wheel(0, 380); settle(page)
            page.evaluate("history.back()")
            page.wait_for_function("location.hash===''"); settle(page)
            returned_top = panel.evaluate("el=>el.getBoundingClientRect().top")
            assert abs(returned_top - original_top) < 3, f"Native fragment return shifted content by {returned_top - original_top:.1f}px"
            assert page.evaluate("location.search") == "?keep=scroll"
            passed("native-fragment-viewport-owner", visual_anchor_delta=returned_top - original_top)
            ctx.close()

            # Table focus works without a company anchor; real global overflow also retains horizontal position.
            for tab, selector in (("sectors", "#tab-sectors .discovery-scroll"), ("global", "#g-strong .discovery-scroll")):
                ctx, page = context(390, "en", "light", touch=True)
                page.goto(origin + "/discovery.html"); ready(page)
                page.locator('#discovery-tab-' + tab).click()
                table = page.locator(selector)
                table.scroll_into_view_if_needed(); table.focus()
                table.evaluate("el=>el.scrollLeft=el.scrollWidth-el.clientWidth")
                left = table.evaluate("el=>el.scrollLeft")
                if tab == "global":
                    assert left > 0
                page.goto(origin + "/stock.html#AAPL")
                page.go_back(wait_until="domcontentloaded"); ready(page); settle(page)
                expect(table).to_be_focused()
                assert abs(table.evaluate("el=>el.scrollLeft") - left) < 2
                assert state(page)["position"]["table"]
                shot(page, tab + "-table-return-390-en-light")
                passed(tab + "-table-focus-return", scroll_left=left, horizontal_return_exercised=left > 0)
                ctx.close()

            # Scroll after controller activation but before pageshow must win.
            server.load_gate = threading.Event()
            position = {"key": "", "focus": "", "offset": 0, "x": 0, "y": 800, "tableLeft": 0}
            ctx, page = context(seed={KEY: saved(tab="global", position=position)})
            page.goto(origin + "/discovery.html", wait_until="domcontentloaded"); ready(page)
            assert page.evaluate("document.readyState") != "complete"
            page.mouse.wheel(0, 250); page.wait_for_function("scrollY>100")
            settle(page)
            user_y = page.evaluate("scrollY")
            user_top = page.locator("body > .panel").first.evaluate("el=>el.getBoundingClientRect().top")
            server.load_gate.set(); page.wait_for_load_state("load"); settle(page)
            assert abs(page.locator("body > .panel").first.evaluate("el=>el.getBoundingClientRect().top") - user_top) < 3
            assert "later focus and position" in page.locator('#discovery-return-status').inner_text()
            passed("pre-pageshow-deliberate-scroll-preserved", scroll_y=user_y)
            ctx.close(); server.load_gate = None

            for empty_kind in ("filtered", "unsupplied"):
                server.mutation = ("document.querySelectorAll('#tab-global tr[data-grade]').forEach(e=>e.dataset.grade='stretched');"
                                   if empty_kind == "filtered" else "document.querySelectorAll('#tab-global tr[data-grade]').forEach(e=>e.remove());")
                ctx, page = context()
                page.goto(origin + "/discovery.html"); ready(page)
                page.locator('#hideStretch').check()
                note = page.locator('#discovery-filter-status').inner_text()
                assert ("All names are hidden" in note) if empty_kind == "filtered" else ("No ranked names are supplied" in note)
                page.locator('#discovery-tab-sector').click()
                assert page.locator('[data-grp=seclist]:visible tr[data-grade]').count() == 24
                passed("empty-state-" + empty_kind, message=note)
                ctx.close()
            server.mutation = ""

            assert not errors, errors
            assert any(x["status"] == 200 and "discovery.js?v=" in x["url"] for x in responses)
            passed("served-fingerprinted-assets", source_js_sha256=hashlib.sha256((SITE / "discovery.js").read_bytes()).hexdigest())
        except Exception as exc:
            failures.append({"type": type(exc).__name__, "message": str(exc), "context": page.evaluate("()=>({url:location.href,note:document.querySelector('#discovery-return-status')?.textContent,active:document.activeElement?.id,key:document.activeElement?.getAttribute('data-discovery-key'),history:history.state})")})
            try:
                shot(page, "failure")
            except Exception:
                pass
            raise
        finally:
            report = {
                "schema": "d04.top_picks_return.browser.v1",
                "observed_at_utc": datetime.now(timezone.utc).isoformat(),
                "browser": browser_version,
                "source_sha256": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in
                    ["templates/discovery.html.j2", "templates/discovery.js", "templates/discovery-controls.css",
                     "site/discovery.html", "site/discovery.js", "site/discovery-controls.css",
                     "scripts/build_discovery.py", "scripts/verify_top_picks_return_browser.py"]},
                "method": "Actual generated page and assets, committed ranking snapshot, same-origin labelled company fixture, incumbent Terminal overlay with labelled message fixture; changed-source cases inject declared mutations before page controller initialization.",
                "limitations": ["Not D07 content/authentication, live data, account persistence, shared-shell full-state transport, production or whole-D04 acceptance.",
                                "Fresh-document traversal is forced by disabling Chromium BFCache. Retained-document proof covers the incumbent overlay only.",
                                "Native traversal explicitly opens the existing company URL after source focus; ordinary keyboard activation and phone taps are separately tested through the incumbent overlay at all matrix widths."],
                "passed": len(cases), "cases": cases, "screenshots": shots, "page_errors": errors,
                "failures": failures, "all_passed": not failures and not errors,
            }
            (out / "browser-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
            browser.close()
            server.shutdown()
            print(json.dumps({"passed": len(cases), "screenshots": len(shots), "failures": failures, "page_errors": errors, "report": str(out / "browser-report.json")}), flush=True)


if __name__ == "__main__":
    main()
