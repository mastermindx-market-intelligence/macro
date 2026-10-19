#!/usr/bin/env python3
"""Browser receipts for the existing Bonds template on an isolated HTTP route.

The payload is output from prepare-bonds-integration.py. Authentication responses
below are controlled test cases, not proof of production entitlement enforcement.
No external network route is allowed by this harness.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import subprocess
import threading
import time
import traceback
from urllib.parse import unquote, urlsplit

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[3]
PAYLOAD = "/macro-context-data/decision_workspaces.json"


def run(candidate: Path, output: Path) -> dict:
    candidate = candidate.resolve()
    output.mkdir(parents=True, exist_ok=True)
    pub_bytes = (candidate / "site" / PAYLOAD.lstrip("/")).read_bytes()
    pub = json.loads(pub_bytes)
    build = json.loads((candidate / "build-receipt.json").read_text())
    mode = {"status": 200, "body": pub_bytes, "type": "application/json; charset=utf-8"}
    served = []
    cache = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            path = unquote(urlsplit(self.path).path)
            served.append({"method": "GET", "path": path})
            if path == PAYLOAD:
                status, body, kind = mode["status"], mode["body"], mode["type"]
                if mode.get("delay", 0):
                    time.sleep(mode["delay"])
                self.send_response(status)
                self.send_header("Content-Type", kind)
                self.send_header("Cache-Control", "private, no-store")
                if status == 302:
                    self.send_header("Location", "/test-signin.html")
                if mode.get("content_length", True):
                    self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return
            relative = path.lstrip("/") or "bonds.html"
            if ".." in Path(relative).parts or path.startswith("/api/"):
                self.send_error(401)
                return
            local = candidate / "site" / relative
            template_asset = ROOT / "templates" / relative
            data = None
            if local.is_file():
                data = local.read_bytes()
            elif template_asset.is_file() and template_asset.suffix in (".js", ".css", ".woff", ".woff2", ".svg", ".png", ".ico"):
                data = template_asset.read_bytes()
            elif relative.startswith(("fonts/", "assets/")) or relative in ("favicon.svg", "favicon.ico", "world-110m.json"):
                if relative not in cache:
                    r = subprocess.run(
                        ["git", "-C", str(ROOT), "show", build["input_commit"] + ":site/" + relative],
                        capture_output=True,
                    )
                    cache[relative] = r.stdout if r.returncode == 0 else None
                data = cache[relative]
            if data is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", (mimetypes.guess_type(relative)[0] or "application/octet-stream") + ("; charset=utf-8" if relative.endswith((".html", ".css", ".js")) else ""))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            served.append({"method": "POST", "path": self.path})
            self.send_error(405)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = "http://127.0.0.1:" + str(server.server_port)
    tests, requests, external, errors = [], [], [], []
    report = {
        "schema": "r33.bonds_source_integration_browser.v1",
        "acceptance": "BUILT_NOT_PROVEN",
        "kind": "isolated_http_bonds_route_from_pinned_owner_inputs",
        "route": origin + "/bonds.html", "production_origin_observed": False,
        "input_commit": build["input_commit"],
        "publication_content_sha256": pub["publication"]["content_sha256"],
        "source_files": build["source_files"],
        "results": tests,
    }
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
        def gate(route):
            if route.request.url.startswith(origin + "/"):
                route.continue_()
            else:
                external.append(route.request.url)
                route.abort()
        context.route("**/*", gate)
        page = context.new_page()
        page.set_default_timeout(7000)
        page.on("request", lambda r: requests.append({"method": r.method, "url": r.url}))
        page.on("pageerror", lambda e: errors.append(str(e)))
        dialog = page.locator("#bonds-source-dialog")
        body = page.locator("#bonds-source-content")
        open_button = page.locator("#bonds-source-open")
        action = lambda name: body.locator('[data-source-action="' + name + '"]').first
        section = lambda name: body.locator('.source-tab[data-section="' + name + '"]').click()
        def idle():
            expect(body.locator(".source-metric").or_(body.locator(".source-empty"))).not_to_have_count(0)
            page.wait_for_function("""() => {
                const el = document.querySelector('#bonds-source-content');
                return el && el.getAttribute('aria-busy') !== 'true' &&
                    !/Reading site publication|Loading publication|Reading local publication|正在读取|正在载入/.test(el.innerText);
            }""")
        def normal():
            mode.update(status=200, body=pub_bytes, type="application/json; charset=utf-8", delay=0, content_length=True)
        def reload():
            action("reload-site").click()
            idle()
        def open_sources():
            if not dialog.is_visible():
                open_button.click()
            idle()
        def metrics():
            return body.locator(".source-metric")
        def check(name, fn):
            started = time.perf_counter()
            fn()
            tests.append({"name": name, "pass": True, "seconds": round(time.perf_counter() - started, 3)})
        def fit():
            bounds = dialog.bounding_box()
            assert bounds and bounds["x"] >= 0 and bounds["y"] >= 0
            assert bounds["x"] + bounds["width"] <= page.viewport_size["width"] + 1
            assert bounds["y"] + bounds["height"] <= page.viewport_size["height"] + 1
            assert dialog.evaluate("(e)=>e.scrollWidth <= e.clientWidth+1")
            assert body.evaluate("(e)=>e.scrollWidth <= e.clientWidth+1")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
        contrast_receipts = []
        def contrast(theme, lang, width):
            result = dialog.evaluate("""root => {
                const canvas=document.createElement('canvas');
                canvas.width=canvas.height=1;
                const ctx=canvas.getContext('2d',{willReadFrequently:true});
                function color(value){
                    ctx.clearRect(0,0,1,1);ctx.fillStyle=value;ctx.fillRect(0,0,1,1);
                    const a=Array.from(ctx.getImageData(0,0,1,1).data);return [a[0],a[1],a[2],a[3]/255];
                }
                const blend=(a,b)=>[0,1,2].map(i=>a[i]*a[3]+b[i]*(1-a[3])).concat(1);
                const luminance=c=>c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
                const results=[];
                const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
                let node;
                while(node=walker.nextNode()){
                    const el=node.parentElement,text=node.textContent.trim();
                    if(!text||!el.getClientRects().length||el.closest('.source-sr-only'))continue;
                    const closed=el.closest('details:not([open])');
                    if(closed&&!el.closest('summary'))continue;
                    const style=getComputedStyle(el);
                    if(style.visibility!=='visible'||Number(style.opacity)===0)continue;
                    const chain=[];let ancestor=el;
                    while(ancestor){chain.push(color(getComputedStyle(ancestor).backgroundColor));ancestor=ancestor.parentElement;}
                    let bg=[255,255,255,1];
                    for(let i=chain.length-1;i>=0;i--)bg=blend(chain[i],bg);
                    const fg=blend(color(style.color),bg),a=luminance(fg),b=luminance(bg);
                    const ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
                    const font=parseFloat(style.fontSize),weight=parseInt(style.fontWeight,10);
                    const required=font>=24||(font>=18.66&&weight>=700)?3:4.5;
                    results.push({text:text.slice(0,75),ratio:+ratio.toFixed(3),required});
                }
                return results;
            }""")
            failed = [x for x in result if x["ratio"] + .01 < x["required"]]
            assert not failed, failed
            contrast_receipts.append({"width":width,"theme":theme,"language":lang,
                                      "text_nodes":len(result),"minimum_ratio":min(x["ratio"] for x in result)})
        def import_obj(obj, name="publication.json"):
            raw = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
            body.locator("[data-source-file]").set_input_files(
                {"name": name, "mimeType": "application/json", "buffer": raw.encode()}
            )
            idle()
        def unavailable():
            expect(metrics()).to_have_count(0)
            expect(body.locator(".source-empty")).to_be_visible()

        try:
            page.goto(origin + "/bonds.html", wait_until="networkidle")
            baseline_errors = list(errors)
            baseline_external = list(external)
            storage = page.evaluate("JSON.stringify({local:{...localStorage},session:{...sessionStorage}})")
            hero = page.locator("#health .mx-vh-word").inner_text()
            check("Existing Bonds route renders without eager publication fetch", lambda: (
                expect(open_button).to_be_visible(),
                (_ for _ in ()).throw(AssertionError("eager fetch")) if any(r["path"] == PAYLOAD for r in served) else None,
            ))
            opened = time.perf_counter()
            open_sources()
            first_open_ms = round((time.perf_counter() - opened) * 1000)
            check("Actual generator bytes reach three dated metric cards on Bonds", lambda: (
                expect(metrics()).to_have_count(3),
                expect(body).to_contain_text("2026-10-16"),
                expect(body).to_contain_text("2026-10-17"),
                fit(),
            ))
            check("UTC build and owner assessment remain visibly distinct", lambda: (
                expect(body).to_contain_text(pub["publication"]["validation_date"]),
                expect(body).to_contain_text("publisher identity not authenticated"),
            ))
            section("dates")
            for label in ("Publication identity",):
                body.get_by_text(label, exact=True).click()
            check("Identity view exposes declared digest and real component clocks", lambda: (
                expect(body).to_contain_text(pub["publication"]["content_sha256"]),
                expect(body).to_contain_text(pub["publication"]["built_at"]),
                expect(body).to_contain_text("observation"),
            ))
            section("fields")
            search = body.locator("[data-source-search]")
            search.fill("premium")
            expected_rows = body.locator(".source-field-row:visible").count()
            assert expected_rows >= 1
            body.locator('[data-field="mechanism_evidence.term_premium"]').click()
            action("back").click()
            check("Field detail returns to the filtered result and keyboard invoker", lambda: (
                expect(search).to_have_value("premium"),
                expect(body.locator(".source-field-row:visible")).to_have_count(expected_rows),
                expect(body.locator('[data-field="mechanism_evidence.term_premium"]')).to_be_focused(),
            ))
            section("missing")
            check("Missing evidence preserves the three independent existing-owner gates", lambda: (
                expect(body.locator(".source-need")).to_have_count(3),
                expect(body).to_contain_text("No event result"),
            ))
            for code, label in ((401, "sign"), (403, "access"), (404, "publish"), (503, "unavailable")):
                mode.update(status=code, body=b'{"error":"test gate"}', type="application/json")
                reload()
                check("HTTP " + str(code) + " withholds old values", unavailable)
            for label, raw, kind in (
                ("Malformed JSON", b"{", "application/json"),
                ("Wrong media type", pub_bytes, "text/html"),
                ("Oversized response", b" " * 1500001, "application/json"),
                ("Redirected sign-in response", b"", "text/html"),
            ):
                mode.update(status=302 if label.startswith("Redirected") else 200, body=raw, type=kind)
                reload()
                check(label + " is unavailable without fallback", unavailable)
            assert not any(r["path"] == "/test-signin.html" for r in served)
            normal()
            reload()
            malformed = deepcopy(pub)
            malformed["schema"] = "macro_context.unknown.v999"
            import_obj(malformed)
            check("Unknown schema import clears prior site context", unavailable)
            normal()
            reload()
            body.locator("[data-source-file]").set_input_files(
                {"name": "bad-utf8.json", "mimeType": "application/json", "buffer": b'{"value":"\xff"}'}
            )
            idle()
            check("Malformed UTF-8 import is rejected with the precise text error", lambda: (
                unavailable(), expect(body).to_contain_text("UTF-8"),
            ))
            page.evaluate("""() => {
                window.r33OriginalFileBuffer=File.prototype.arrayBuffer;
                File.prototype.arrayBuffer=function(){return Promise.reject(new Error('test read failure'));};
            }""")
            try:
                body.locator("[data-source-file]").set_input_files(
                    {"name": "unreadable.json", "mimeType": "application/json", "buffer": b"{}"}
                )
                idle()
            finally:
                page.evaluate("() => { File.prototype.arrayBuffer=window.r33OriginalFileBuffer; }")
            check("File read failure stays distinct from invalid UTF-8", lambda: (
                unavailable(), expect(body.locator(".source-empty h3")).to_have_text("Could not read the imported file"),
            ))
            def loadbar_focus():
                body.locator("[data-source-file]").focus()
                import_obj(pub)
                expect(body.locator("[data-source-file]")).to_be_focused()
                reload()
                expect(action("reload-site")).to_be_focused()
            check("Import and reload preserve the keyboard loadbar control", loadbar_focus)
            flags = deepcopy(pub)
            for key, flag in zip(list(flags["publication"]["related_vintages"])[:3], (True, False, None)):
                flags["publication"]["related_vintages"][key]["reported"]["stale"] = flag
            import_obj(flags)
            page.evaluate("""() => {
                document.documentElement.dataset.lang='zh';
                document.dispatchEvent(new CustomEvent('langchange',{detail:'zh'}));
            }""")
            section("dates")
            body.get_by_text("相关宏观序列日期", exact=True).click()
            check("Owner stale true false and null remain distinct in Chinese", lambda: (
                expect(body).to_contain_text("上游已标记"),
                expect(body).to_contain_text("未标记"),
                expect(body).to_contain_text("未提供"),
            ))
            page.evaluate("""() => {
                document.documentElement.dataset.lang='en';
                document.dispatchEvent(new CustomEvent('langchange',{detail:'en'}));
            }""")
            normal()
            reload()
            zero = deepcopy(pub)
            zero["decision_workspaces"]["bonds"]["transmission"]["equities"]["hy_oas"] = 0
            import_obj(zero)
            check("Local import preserves numeric zero and unverified origin", lambda: (
                expect(metrics().first).to_contain_text("0.00"),
                expect(body).to_contain_text("Local import"),
            ))
            partial = deepcopy(pub)
            partial["decision_workspaces"]["bonds"]["mechanism_evidence"]["real_10y"] = None
            import_obj(partial)
            check("Missing scalar stays unavailable within an otherwise valid projection", lambda: (
                expect(metrics()).to_have_count(3),
                expect(metrics().nth(1)).to_contain_text("Unavailable"),
            ))
            injected = deepcopy(pub)
            injected["decision_workspaces"]["bonds"]["current_read"]["health"] = '<img src="https://invalid.example/leak" onerror="window.R33_INJECTED=1">'
            import_obj(injected, '<img onerror="window.NAME_INJECTED=1">.json')
            check("Imported strings and filename cannot execute markup", lambda: (
                expect(body.locator("img")).to_have_count(0),
                (_ for _ in ()).throw(AssertionError("injected")) if page.evaluate("Boolean(window.R33_INJECTED||window.NAME_INJECTED)") else None,
            ))
            future = deepcopy(pub)
            clock = future["publication"]["component_clocks"]["rates_credit"]
            clock.update(reported_value="2026-10-21", asof="2026-10-21", date_status="future",
                         age_days=(date.fromisoformat(pub["publication"]["validation_date"]) - date(2026, 10, 21)).days)
            import_obj(future)
            section("dates")
            check("Future source clock remains a disclosed limitation", lambda: expect(body).to_contain_text("future"))
            import_obj("{")
            check("Failed import stays unavailable until explicit site reload", unavailable)
            normal()
            reload()
            page.evaluate("""() => {
                window.r33OriginalFileBuffer=File.prototype.arrayBuffer;
                File.prototype.arrayBuffer=function(){return new Promise(r=>{window.r33ResolveFile=r;});};
            }""")
            body.locator("[data-source-file]").set_input_files(
                {"name": "delayed.json", "mimeType": "application/json", "buffer": b"{}"}
            )
            expect(metrics()).to_have_count(0)
            action("reload-site").click()
            idle()
            page.evaluate("(text)=>window.r33ResolveFile(new TextEncoder().encode(text).buffer)", json.dumps(zero))
            page.evaluate("() => { File.prototype.arrayBuffer=window.r33OriginalFileBuffer; }")
            check("A late file read cannot replace an explicit site reload", lambda: (
                expect(body).to_contain_text("Site publication"),
                expect(metrics().first).not_to_contain_text("0.00"),
            ))
            normal()
            context.route(origin + PAYLOAD, lambda route: route.abort("internetdisconnected"))
            reload()
            check("Disconnected source clears values and remains unavailable", unavailable)
            context.unroute(origin + PAYLOAD)
            normal()
            mode["body"] = ('"' + '界' * 500001 + '"').encode()
            mode["content_length"] = False
            reload()
            check("Stream byte cap rejects a multibyte body without Content-Length", lambda: (
                unavailable(),
                expect(body).to_contain_text("1.5 MB"),
            ))
            normal()
            reload()
            page.evaluate("""() => {
                window.r33RealDate=Date;
                window.Date=class extends window.r33RealDate {
                    constructor(...args){super(...(args.length?args:['2026-10-17T12:00:00Z']));}
                };
                document.dispatchEvent(new CustomEvent('langchange',{detail:'en'}));
            }""")
            check("Future owner assessment is disclosed against the viewer UTC clock", lambda: expect(body).to_contain_text("later than today"))
            page.evaluate("""() => {
                window.Date=window.r33RealDate;
                document.dispatchEvent(new CustomEvent('langchange',{detail:'en'}));
            }""")
            normal()
            mode["delay"] = 1.5
            action("reload-site").click()
            expect(body).to_have_attribute("aria-busy", "true")
            page.locator("#bonds-source-close").click()
            assert not page.evaluate("window.MMXSourceInspector.getState().pending")
            normal()
            open_sources()
            page.wait_for_timeout(1700)
            check("Closing a pending fetch permits a clean reopen and ignores the old response", lambda: (
                expect(metrics()).to_have_count(3),
                expect(body).to_contain_text("Site publication"),
            ))
            page.evaluate("""() => {
                window.r33OriginalFileBuffer=File.prototype.arrayBuffer;
                File.prototype.arrayBuffer=function(){return new Promise(r=>{window.r33ResolveFile=r;});};
            }""")
            body.locator("[data-source-file]").set_input_files(
                {"name":"close-during-read.json","mimeType":"application/json","buffer":b"{}"}
            )
            page.keyboard.press("Escape")
            assert not page.evaluate("window.MMXSourceInspector.getState().pending")
            open_sources()
            page.evaluate("(text)=>window.r33ResolveFile(new TextEncoder().encode(text).buffer)", json.dumps(zero))
            page.evaluate("() => { File.prototype.arrayBuffer=window.r33OriginalFileBuffer; }")
            check("Closing a pending import prevents its late result from changing the reopened source", lambda: (
                expect(body).to_contain_text("Site publication"),
                expect(metrics().first).not_to_contain_text("0.00"),
            ))
            normal()
            mode["delay"] = 13.5
            timed = time.perf_counter()
            action("reload-site").click()
            page.wait_for_function("!window.MMXSourceInspector.getState().pending", timeout=15000)
            assert 11.5 <= time.perf_counter()-timed <= 15
            check("A stalled source request becomes an explicit timeout", lambda: (
                unavailable(),
                expect(body).to_contain_text("timed out"),
            ))
            normal()
            reload()
            section("overview")
            for width in (1440, 1024, 768, 390):
                for theme in ("light", "dark"):
                    for lang in ("en", "zh"):
                        page.set_viewport_size({"width": width, "height": 900 if width >= 768 else 844})
                        page.evaluate("""({theme,lang})=>{
                            document.documentElement.dataset.theme=theme;
                            document.documentElement.dataset.lang=lang;
                            document.dispatchEvent(new CustomEvent('langchange',{detail:lang}));
                        }""", {"theme": theme, "lang": lang})
                        check(str(width) + "px " + theme + " " + lang + " inspector fits", fit)
                        contrast(theme, lang, width)
                        expect(page.locator("#bonds-source-title")).to_have_text("债券传导来源" if lang == "zh" else "Bonds transmission sources")
                        if width in (1440, 390):
                            page.screenshot(path=str(output / (str(width) + "-" + theme + "-" + lang + ".png")), full_page=False)
            page.evaluate("""()=>{
                document.documentElement.dataset.lang='en';
                document.dispatchEvent(new CustomEvent('langchange',{detail:'en'}));
            }""")
            for name in ("fields", "dates", "missing"):
                section(name)
                check("390px " + name + " progressive view fits", fit)
            section("overview")
            targets = dialog.locator("button:visible, input:visible, summary:visible")
            sizes = targets.evaluate_all("(els)=>els.map(e=>({tag:e.tagName,text:e.textContent.trim().slice(0,70),width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}))")
            assert all(x["width"] >= 43.5 and x["height"] >= 43.5 for x in sizes), sizes
            check("All visible inspector controls provide 44px targets", lambda: None)
            for _ in range(30):
                page.keyboard.press("Tab")
                assert dialog.evaluate("(e)=>e.contains(document.activeElement)")
            page.keyboard.press("Escape")
            check("Native dialog traps focus and Escape returns to the Bonds trigger", lambda: (
                expect(dialog).not_to_be_visible(),
                expect(open_button).to_be_focused(),
            ))
            assert page.locator("#health .mx-vh-word").inner_text() == hero
            assert page.evaluate("JSON.stringify({local:{...localStorage},session:{...sessionStorage}})") == storage
            assert not any(r["method"] != "GET" for r in served)
            assert not any(r["url"].endswith("/leak") for r in requests)
            assert errors == baseline_errors, errors
            check("Source inspection leaves host content, saved storage and write authority unchanged", lambda: None)
            report.update(passed=len(tests), failed=0, browser=browser.version,
                          first_open_ms=first_open_ms, baseline_page_errors=baseline_errors,
                          new_page_errors=errors[len(baseline_errors):], baseline_external_blocked=baseline_external,
                          external_blocked=external, requests=requests, server_requests=served,
                          visible_control_sizes=sizes, text_contrast=contrast_receipts)
        except Exception as exc:
            report.update(passed=len(tests), failed=1, error=str(exc), traceback=traceback.format_exc(),
                          page_errors=errors, requests=requests, server_requests=served)
            page.screenshot(path=str(output / "failure.png"), full_page=False)
            raise
        finally:
            report["screenshots"] = [
                {"path": x.name, "sha256": hashlib.sha256(x.read_bytes()).hexdigest()}
                for x in sorted(output.glob("*.png"))
            ]
            (output / "browser-receipt.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            context.close()
            browser.close()
            server.shutdown()
            server.server_close()
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.candidate, args.output_dir)
    print(json.dumps({k: result[k] for k in ("acceptance", "passed", "failed", "browser", "first_open_ms")}))
