#!/usr/bin/env python3
"""Confluence protocol and action proof using actual old/new page code.
Controlled auth and HTTP fixtures; no production entitlement or deployment claim.
"""
from __future__ import annotations
import argparse, copy, hashlib, http.server, importlib.util, json, re
import socketserver, sys, threading, traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_confluence_screener import build_context, build_premium_payload, render_html
from scripts.verify_confluence_screener_browser import AUTH
from engine import i18n

spec = importlib.util.spec_from_file_location("compat_fixture", ROOT / "tests/test_confluence_screener_page.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
LEGACY = ROOT / "tests/fixtures/confluence_legacy_template_f9588ff5.html.j2"
LEGACY_BLOB = "8e18461db98d7141d573cd047aa8637189ad4250"
FETCH_OBSERVER = """(() => {
  const original = window.fetch;
  window.__compatJsonReads = 0;
  window.fetch = function(...args) {
    return original.apply(this, args).then(response => {
      if (new URL(typeof args[0] === 'string' ? args[0] : args[0].url, location.href).pathname === '/premiumdata/confluence_screener.json') {
        const read = response.json.bind(response);
        response.json = () => read().then(value => { window.__compatJsonReads += 1; return value; });
      }
      return response;
    });
  };
})();"""

def file_meta(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "blob": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browser-executable")
    parser.add_argument("--case-prefix", action="append", default=[])
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    assert file_meta(LEGACY)["blob"] == LEGACY_BLOB
    raw = copy.deepcopy(fixture._make_raw())
    zero = copy.deepcopy(raw)
    zero["combos"]["long"] = []
    changed = copy.deepcopy(raw)
    changed["combos"]["long"][1]["legs"] = [1, 2]
    changed["combos"]["long"][1]["active_now"] = ["NEWERA"]
    payload = build_premium_payload(raw, {"GATEDBB": "Protected fixture B", "GATEDCC": "Protected fixture C"})
    changed_payload = build_premium_payload(changed, {"NEWERA": "Different recipe fixture"})
    assert payload["built"] == changed_payload["built"]
    assert payload["source_generation"]["sha256"] != changed_payload["source_generation"]["sha256"]
    prior_bound = copy.deepcopy(payload)
    prior_bound["schema"] = "tier_payload.v1"
    prior_unbound = copy.deepcopy(prior_bound)
    del prior_unbound["source_generation"]
    del prior_unbound["source_status"]
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    legacy_html = re.sub(r"(?m)^[ \t]+$", "", env.from_string(LEGACY.read_text()).render(**build_context(raw, {})))
    pages = {
        "legacy": legacy_html.encode(),
        "current": render_html(ROOT, build_context(raw, {})).encode(),
        "zero": render_html(ROOT, build_context(zero, {})).encode(),
        "unavailable": render_html(ROOT, build_context(None, {})).encode(),
    }
    expected_cta = build_context(zero, {})["cta_url"]
    page_hits = []

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(ROOT / "site"), **kw)
        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path.startswith("/premiumdata/"):
                self.send_response(403)
                self.end_headers()
                return
            if parsed.path == "/confluence_screener.html":
                key = parse_qs(parsed.query).get("fixture", ["current"])[0]
                body = pages[key]
                page_hits.append(self.path)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()
        def log_message(self, *_):
            pass

    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = "http://127.0.0.1:" + str(server.server_address[1])
    cases, captures, errors = [], [], []
    context_count = 0

    def record(name, fn):
        if args.case_prefix and not any(name.startswith(prefix) for prefix in args.case_prefix):
            return
        case = {"name": name, "observations": []}
        try:
            fn(case["observations"])
            case["status"] = "PASS"
        except Exception as exc:
            case.update(status="FAIL", error=str(exc), trace=traceback.format_exc(limit=3))
        cases.append(case)

    try:
        with sync_playwright() as pw:
            opts = {"headless": True}
            if args.browser_executable:
                opts["executable_path"] = args.browser_executable
            browser = pw.chromium.launch(**opts)
            version = browser.version

            def opened(key, width, lang, theme, response):
                nonlocal context_count
                context_count += 1
                context = browser.new_context(
                    viewport={"width": width, "height": 900 if width > 500 else 844},
                    device_scale_factor=1, reduced_motion="reduce",
                    is_mobile=width <= 500, has_touch=width <= 500)
                context.route("**/*", lambda route: route.continue_() if urlsplit(route.request.url).hostname == "127.0.0.1" else route.abort())
                context.add_init_script("localStorage.setItem('lang'," + json.dumps(lang) + ");localStorage.setItem('theme'," + json.dumps(theme) + ");")
                context.add_init_script(FETCH_OBSERVER)
                page = context.new_page()
                page.set_default_timeout(6000)
                local_errors = []
                page.on("pageerror", lambda error: (local_errors.append(str(error)), errors.append(str(error))))
                ctl = {"armed": False, "body": copy.deepcopy(response), "requests": [], "initial_requests": 0}
                def reply(route):
                    if not ctl["armed"]:
                        ctl["initial_requests"] += 1
                        route.fulfill(status=403, content_type="application/json", body="{}")
                        return
                    ctl["requests"].append({"url": route.request.url, "method": route.request.method})
                    route.fulfill(content_type="application/json", body=json.dumps(ctl["body"]))
                page.route("**/premiumdata/confluence_screener.json", reply)
                url = origin + "/confluence_screener.html?fixture=" + key + "&keep=a&keep=b#return-point"
                page.goto(url, wait_until="load")
                page.evaluate(AUTH)
                page.wait_for_function("document.querySelector('.wrap') !== null")
                ctl["armed"] = True
                return context, page, ctl, local_errors

            def settle_response(page, previous=0):
                page.wait_for_function("n => window.__compatJsonReads > n", arg=previous)
                page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")

            def observation(page, ctl, label):
                value = page.evaluate("""() => ({
                  url: location.href,
                  locked: document.querySelectorAll('.locked[data-confluence-combo]').length,
                  hydrated: document.querySelectorAll('[data-confluence-hydrated]').length,
                  paidLinks: Array.from(document.querySelectorAll('.lc.gated a.tkr')).map(n => n.getAttribute('href')),
                  state: document.querySelector('#confluence-access-status')?.getAttribute('data-state') || null,
                  publicLinks: Array.from(document.querySelector('.lc.free')?.querySelectorAll('a.tkr') || []).map(n=>n.getAttribute('href')),
                  activeTag: document.activeElement?.tagName,
                  activeHref: document.activeElement?.getAttribute('href') || null
                })""")
                value.update(phase=label, requests=len(ctl["requests"]), schema=ctl["body"].get("schema"))
                return value

            def locked_snapshot(page, ctl, obs, label, expected_state=None):
                value = observation(page, ctl, label)
                obs.append(value)
                assert value["locked"] == 2 and value["hydrated"] == 0 and not value["paidLinks"], value
                assert value["publicLinks"] == ["stocks/FREEAA.html"], value
                if expected_state:
                    assert value["state"] == expected_state, value
                return value

            for width, lang, theme in ((1440, "en", "dark"), (320, "zh", "light")):
                suffix = str(width) + "-" + lang
                def legacy_case(obs, width=width, lang=lang, theme=theme):
                    context, page, ctl, local_errors = opened("legacy", width, lang, theme, changed_payload)
                    try:
                        before = page.locator(".lc.gated").all_inner_texts()
                        page.evaluate("window.__d04Auth('owner-A','SIGNED_IN')")
                        settle_response(page)
                        value = locked_snapshot(page, ctl, obs, "frozen-old-reader/new-generation-payload")
                        assert page.locator(".lc.gated").all_inner_texts() == before
                        assert len(ctl["requests"]) == 1 and not local_errors
                        value["same_clock_changed_recipe"] = True
                    finally:
                        context.close()
                record("old_reader_rejects_new_payload-" + suffix, legacy_case)

                for name, body in (("prior_bound_v1", prior_bound), ("legacy_unbound_v1", prior_unbound)):
                    def rejection(obs, width=width, lang=lang, theme=theme, body=body, name=name):
                        context, page, ctl, local_errors = opened("current", width, lang, theme, body)
                        try:
                            page.evaluate("window.__d04Auth('owner-A','SIGNED_IN')")
                            settle_response(page)
                            locked_snapshot(page, ctl, obs, name, "invalid")
                            assert len(ctl["requests"]) == 1 and not local_errors
                            if name == "prior_bound_v1":
                                ctl["body"] = copy.deepcopy(payload)
                                before_reads = page.evaluate("window.__compatJsonReads")
                                retry = page.locator("#confluence-check-access")
                                expect(retry).to_be_visible()
                                retry.focus()
                                retry.press("Enter")
                                settle_response(page, before_reads)
                                value = observation(page, ctl, "valid-retry-after-version-rejection")
                                obs.append(value)
                                assert value["state"] == "loaded" and value["hydrated"] == 2, value
                                assert value["activeHref"] == "stocks/GATEDBB.html", value
                                assert len(ctl["requests"]) == 2 and not local_errors
                        finally:
                            context.close()
                    record("new_reader_rejects_" + name + "-" + suffix, rejection)

                def success(obs, width=width, lang=lang, theme=theme):
                    context, page, ctl, local_errors = opened("current", width, lang, theme, payload)
                    try:
                        page.evaluate("window.__d04Auth('owner-A','SIGNED_IN')")
                        settle_response(page)
                        value = observation(page, ctl, "matching-new-pair")
                        obs.append(value)
                        assert value["state"] == "loaded" and value["hydrated"] == 2 and value["locked"] == 0, value
                        assert value["paidLinks"] == ["stocks/GATEDBB.html", "stocks/GATEDCC.html"], value
                        page.locator('[data-confluence-combo="L0002"] a.tkr').focus()
                        page.evaluate("window.__d04Auth(null,'SIGNED_OUT')")
                        locked_snapshot(page, ctl, obs, "signout-retains-public-evidence")
                        assert page.evaluate("document.activeElement.closest('[data-confluence-combo]')?.getAttribute('data-confluence-combo')") == "L0002"
                        assert len(ctl["requests"]) == 1 and not local_errors
                    finally:
                        context.close()
                record("matching_pair_and_signout-" + suffix, success)

                def mismatch_retry(obs, width=width, lang=lang, theme=theme):
                    context, page, ctl, local_errors = opened("current", width, lang, theme, changed_payload)
                    try:
                        page.evaluate("window.__d04Auth('owner-A','SIGNED_IN')")
                        settle_response(page)
                        locked_snapshot(page, ctl, obs, "same-clock-different-recipe", "mismatch")
                        ctl["body"] = copy.deepcopy(payload)
                        before_url = page.url
                        reload = page.locator("#confluence-reload-access")
                        expect(reload).to_be_visible()
                        expect(page.locator("#confluence-check-access")).to_be_hidden()
                        reload.focus()
                        with page.expect_navigation(wait_until="load"):
                            reload.press("Enter")
                        assert page.url == before_url
                        page.evaluate(AUTH)
                        page.evaluate("window.__d04Auth('owner-A','SIGNED_IN')")
                        settle_response(page)
                        value = observation(page, ctl, "valid-recovery-after-existing-reload")
                        obs.append(value)
                        assert value["state"] == "loaded" and value["hydrated"] == 2, value
                        assert value["paidLinks"] == ["stocks/GATEDBB.html", "stocks/GATEDCC.html"], value
                        assert len(ctl["requests"]) == 2 and not local_errors
                    finally:
                        context.close()
                record("generation_mismatch_and_existing_reload-" + suffix, mismatch_retry)

            for width, lang, theme in ((390, "en", "dark"), (320, "zh", "light")):
                for key in ("zero", "unavailable"):
                    def action_case(obs, width=width, lang=lang, theme=theme, key=key):
                        context, page, ctl, local_errors = opened(key, width, lang, theme, payload)
                        try:
                            expected = ("Open Mastermind" if lang == "en" else "打开 Mastermind") if key == "zero" else ("Reload page" if lang == "en" else "重新加载页面")
                            target = page.locator('[data-source-state="available-empty"] a.btn') if key == "zero" else page.locator("#confluence-reload-page")
                            target.scroll_into_view_if_needed()
                            value = target.evaluate("""n => {
                              const r=n.getBoundingClientRect();
                              return {text:n.innerText.trim(),href:n.getAttribute('href'),tag:n.tagName,
                                x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,
                                viewport:innerWidth,documentWidth:document.documentElement.scrollWidth};
                            }""")
                            obs.append({"phase":key+"-action","expected_label":expected,**value})
                            assert value["text"] == expected, value
                            assert value["height"] >= 44 and value["right"] <= width and value["x"] >= 0, value
                            assert value["documentWidth"] <= width, value
                            file = key + "-action-" + str(width) + "-" + lang + ".png"
                            page.locator(".empty").screenshot(path=str(out / file))
                            captures.append({"file":file,"width":width,"lang":lang,"theme":theme,"fixture":key})
                            if key == "zero":
                                assert value["href"] == expected_cta
                                hits = []
                                def app_navigation(route):
                                    hits.append({"url":route.request.url,"method":route.request.method})
                                    route.fulfill(content_type="text/html", body="<!doctype html><title>App destination fixture</title><h1>Application destination fixture</h1>")
                                page.route("https://app.mastermind-x.com/**", app_navigation)
                                with page.expect_navigation(wait_until="load"):
                                    target.click()
                                assert hits == [{"url":expected_cta,"method":"GET"}], hits
                                obs.append({"phase":"native-app-navigation","intercepted_fixture":True,"requests":hits})
                            else:
                                before_url = page.url
                                before_hits = len(page_hits)
                                with page.expect_navigation(wait_until="load"):
                                    target.click()
                                assert page.url == before_url
                                assert len(page_hits) == before_hits + 1
                                expect(page.locator('[data-source-state="unavailable"]')).to_have_count(1)
                                obs.append({"phase":"native-reload","url_preserved":True,"document_requests":1})
                            assert not ctl["requests"] and not local_errors
                        finally:
                            context.close()
                    record(key + "_action-" + str(width) + "-" + lang, action_case)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()

    for capture in captures:
        capture.update(file_meta(out / capture["file"]))
    paths = ["scripts/build_confluence_screener.py","templates/confluence_screener.html.j2",
             "tests/test_confluence_screener_page.py","scripts/verify_confluence_screener_browser.py",
             "scripts/verify_confluence_compatibility_browser.py",
             "tests/fixtures/confluence_legacy_template_f9588ff5.html.j2",
             "site/confluence_screener.html","site/premiumdata/confluence_screener.json"]
    report = {"schema":"confluence_compat_browser/v1","observed_at":datetime.now(timezone.utc).isoformat(),
              "browser":version,"contexts":context_count,"cases":cases,"page_errors":errors,
              "selection":{"case_prefix":args.case_prefix,"status":"SELECTED" if cases else "NO_CASES_SELECTED"},
              "passed":sum(c["status"]=="PASS" for c in cases),"failed":sum(c["status"]=="FAIL" for c in cases),
              "captures":captures,"sources":{p:file_meta(ROOT/p) for p in paths},
              "legacy_source":{"commit":"f9588ff57391350bbd7225a7bbe56eb589d5a47d","blob":LEGACY_BLOB},
              "scope":"Actual template/controller/production renderer with synthetic data, controlled auth/HTTP and intercepted app destination. No production entitlement, full shared shell or deployment claim.",
              "observer":"Fetch JSON-read completion is observed without changing the returned payload. Two animation frames settle existing controller continuations; no fixed sleep."}
    (out/"browser-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"passed":report["passed"],"failed":report["failed"],"contexts":context_count,
                      "page_errors":len(errors),"selection":report["selection"],"report":str(out/"browser-report.json"),
                      "failures":[{"name":c["name"],"error":c["error"][:500]} for c in cases if c["status"]=="FAIL"]},ensure_ascii=False))
    return 2 if not cases else (1 if report["failed"] else 0)

if __name__ == "__main__":
    raise SystemExit(main())
