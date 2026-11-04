#!/usr/bin/env python3
"""Finite, local-browser verification of the actual Confluence page handlers.

Uses the existing renderer and theme. Auth and protected HTTP responses are
explicit fixtures; this is not a production entitlement or deployment proof.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import http.server
import importlib.util
import json
import re
import socketserver
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_confluence_screener import build_context, build_premium_payload, render_html

spec = importlib.util.spec_from_file_location("confluence_fixture", ROOT / "tests/test_confluence_screener_page.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

AUTH = """() => {
  window.__d04User = null;
  window.__d04Expiry = Date.now() / 1000 + 3600;
  window.MDXAuth = {
    user: () => window.__d04User,
    hasSession: () => !!window.__d04User,
    client: () => Promise.resolve({auth:{getSession:()=>Promise.resolve({
      data:{session:window.__d04User ? {user:window.__d04User,expires_at:window.__d04Expiry} : null},error:null
    })}}),
    onChange: () => {},
    signOut: () => {window.__d04Auth(null, 'SIGNED_OUT');return Promise.resolve();}
  };
  window.__d04Auth = (id, event) => {
    window.__d04User = id ? {id:id} : null;
    window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:window.__d04User,event:event}}));
  };
}"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/d04-confluence-evidence")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    raw = copy.deepcopy(fixture._make_raw())
    raw["base"] = {"long": {"h21": {"wr_mc_test": 0.5669, "wr_mc_train": 0.5583}}}
    dense = copy.deepcopy(raw)
    dense["legs"].append({"tf": "W", "display_en": "Weekly momentum recovers while the longer trend remains constructive",
                           "display_zh": "周线动能回升且长期趋势维持建设性，保留完整条件名称"})
    dense["combos"]["long"][0]["legs"] = [0, 1, 2, 3]
    dense["combos"]["long"][0]["active_now"] = ["BRK.B", "ALPHA", "BETA", "GAMMA", "DELTA", "EPSILON"]
    dense["combos"]["long"][0]["name_en"] = "Golden cross + weekly uptrend + RSI recovery + long weekly condition"
    dense["combos"]["long"][0]["name_zh"] = "黄金交叉＋周线上升趋势＋日线动能恢复＋较长的周线确认条件"
    names = {t: "Synthetic International Semiconductor & Research Holdings" for t in dense["combos"]["long"][0]["active_now"]}
    zero = copy.deepcopy(raw)
    zero["combos"]["long"] = []
    real = json.loads((ROOT / "site/factordata/tech_confluence.json").read_text())
    sources = {"base": raw, "dense": dense, "zero": zero, "unavailable": None, "real": real}
    pages = {}
    for key, source in sources.items():
        html = render_html(ROOT, build_context(source, names if key == "dense" else {}))
        label_text = ("D04 local candidate · existing source artifact · no deployment or live entitlement proof"
                      if key == "real" else "D04 browser fixture · simulated data and access responses")
        label = '<div data-d04-fixture style="padding:8px 20px;font:13px system-ui;background:#fff8da;color:#493c17">' + label_text + '</div>'
        html = html.replace("<body>", "<body>" + label, 1)
        pages[key] = html.encode()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(ROOT / "site"), **kw)

        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path == "/confluence_screener.html":
                key = parse_qs(parsed.query).get("fixture", ["base"])[0]
                body = pages.get(key, pages["base"])
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if parsed.path.startswith("/stocks/") and parsed.path.endswith(".html"):
                body = b"<!doctype html><title>Company path fixture</title><h1>Company path fixture</h1>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()

        def log_message(self, *_args):
            pass

    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = "http://127.0.0.1:" + str(server.server_address[1])
    results, shots, layout = [], [], []
    payload = build_premium_payload(raw, {"GATEDBB": "Private fixture B", "GATEDCC": "Private fixture C"})

    def contrast_ratio(ink, panel):
        def luminance(color):
            rgb = [float(x) / 255 for x in re.findall(r"[0-9.]+", color)[:3]]
            assert len(rgb) == 3
            return sum(w * (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
                       for w, c in zip((0.2126, 0.7152, 0.0722), rgb))
        a, b = sorted((luminance(ink), luminance(panel)))
        return (b + 0.05) / (a + 0.05)

    def record(name, fn):
        try:
            detail = fn()
            results.append({"name": name, "status": "PASS", "detail": detail})
        except Exception as exc:
            results.append({"name": name, "status": "FAIL", "error": str(exc)[:1800],
                            "trace": traceback.format_exc(limit=3)[-2000:]})

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            version = browser.version

            def new_page(*, key="base", width=1440, theme="dark", lang="en", no_abort=False):
                context = browser.new_context(viewport={"width": width, "height": 900 if width > 500 else 844},
                                              device_scale_factor=1, is_mobile=width <= 500,
                                              has_touch=width <= 500, reduced_motion="reduce")
                context.route("**/*", lambda route: route.continue_() if urlsplit(route.request.url).hostname == "127.0.0.1" else route.abort())
                context.add_init_script("localStorage.setItem('theme'," + json.dumps(theme) + ");localStorage.setItem('lang'," + json.dumps(lang) + ");")
                if no_abort:
                    context.add_init_script("window.AbortController = undefined;")
                page = context.new_page()
                page.goto(origin + "/confluence_screener.html?fixture=" + key + "&keep=a&keep=b#return-point", wait_until="load")
                page.wait_for_function("document.querySelector('.wrap') !== null")
                page.evaluate(AUTH)
                return context, page

            def state(page, value):
                expect(page.locator("#confluence-access-status")).to_have_attribute("data-state", value)

            def assert_locked(page):
                expect(page.locator(".locked[data-confluence-combo]")).to_have_count(2)
                expect(page.locator("[data-confluence-hydrated]")).to_have_count(0)
                assert "GATEDBB" not in page.locator("body").inner_text()
                assert "GATEDCC" not in page.locator("body").inner_text()
                assert "Matching stocks loaded" not in page.locator("body").inner_text()

            def response_case(name, body=None, status=200, expected="invalid", abort=False):
                def run():
                    context, page = new_page()
                    try:
                        calls = []
                        def respond(route):
                            calls.append({"url":route.request.url, "method":route.request.method})
                            if abort:
                                route.abort()
                            else:
                                route.fulfill(status=status, content_type="application/json",
                                              body=body if isinstance(body, str) else json.dumps(body))
                        page.route("**/premiumdata/confluence_screener.json", respond)
                        page.evaluate("window.__d04Auth('owner-A','SIGNED_IN')")
                        state(page, expected)
                        assert_locked(page)
                        assert len(calls) == 1
                        if name in ("same_clock_different_generation", "denied_403"):
                            page.locator("#confluence-access-status").scroll_into_view_if_needed()
                            file = "access-" + name + "-1440-dark-en.png"
                            page.screenshot(path=str(out / file), full_page=False)
                            shots.append({"file":file,"width":1440,"theme":"dark","lang":"en","fixture":name})
                        return {"requests": len(calls), "state": expected}
                    finally:
                        context.close()
                record(name, run)

            broken = []
            b = copy.deepcopy(payload); b["source_generation"]["sha256"] = "0" * 64; broken.append(("same_clock_different_generation", b, "mismatch"))
            b = copy.deepcopy(payload); del b["source_generation"]; broken.append(("old_payload_no_receipt", b, "mismatch"))
            b = copy.deepcopy(payload); b["combos"] = b["combos"][:1]; broken.append(("missing_paid_row", b, "invalid"))
            b = copy.deepcopy(payload); b["combos"][1]["combo_id"] = b["combos"][0]["combo_id"]; broken.append(("duplicate_combo_id", b, "invalid"))
            b = copy.deepcopy(payload); b["combos"][1]["combo_id"] = "UNKNOWN"; broken.append(("unknown_combo_id", b, "invalid"))
            b = copy.deepcopy(payload); b["combos"][1]["active_tickers"] = None; broken.append(("missing_identity_array", b, "invalid"))
            b = copy.deepcopy(payload); b["combos"][1]["active_count"] = 2; broken.append(("count_mismatch", b, "invalid"))
            b = copy.deepcopy(payload); b["combos"][1]["active_tickers"][0]["ticker"] = "../private"; broken.append(("invalid_ticker_no_partial_commit", b, "invalid"))
            b = copy.deepcopy(payload); b["combos"][1]["active_tickers"][0]["name"] = {}; broken.append(("invalid_name_no_partial_commit", b, "invalid"))
            for name, body, expected in broken:
                response_case(name, body, expected=expected)
            response_case("null_json", None)
            response_case("invalid_json", "{bad-json")
            response_case("expired_401", {}, status=401, expected="expired")
            response_case("denied_403", {}, status=403, expected="denied")
            response_case("server_500", {}, status=500, expected="unavailable")
            response_case("network_failure", abort=True, expected="unavailable")

            def success_and_signout():
                context, page = new_page()
                try:
                    calls = []
                    def respond(route):
                        calls.append(1)
                        reversed_payload = copy.deepcopy(payload)
                        reversed_payload["combos"].reverse()
                        route.fulfill(content_type="application/json", body=json.dumps(reversed_payload))
                    page.route("**/premiumdata/confluence_screener.json", respond)
                    page.evaluate("window.__d04Auth('owner-A','SIGNED_IN')")
                    state(page, "loaded")
                    expect(page.locator("[data-confluence-hydrated]")).to_have_count(2)
                    assert page.locator('[data-confluence-combo="L0002"] a.tkr').get_attribute("href") == "stocks/GATEDBB.html"
                    assert page.locator('[data-confluence-combo="L0003"] a.tkr').get_attribute("href") == "stocks/GATEDCC.html"
                    file = "access-loaded-1440-dark-en.png"
                    page.locator(".lc.gated").first.scroll_into_view_if_needed()
                    page.screenshot(path=str(out / file), full_page=False)
                    shots.append({"file":file,"width":1440,"theme":"dark","lang":"en","fixture":"authorized_response"})
                    before = len(calls)
                    page.evaluate("window.__d04Auth('owner-A','PREFS_SAVED')")
                    page.wait_for_timeout(80)
                    assert len(calls) == before
                    page.locator('[data-confluence-combo="L0002"] a.tkr').focus()
                    page.evaluate("window.__d04Auth(null,'SIGNED_OUT')")
                    assert_locked(page)
                    assert page.evaluate("document.activeElement.closest('[data-confluence-combo]')?.dataset.confluenceCombo") == "L0002"
                    return {"reordered_response": "matched_by_id", "prefs_requests": 0, "signout": "public_walls_restored", "focus": "L0002"}
                finally:
                    context.close()
            record("success_reordered_payload_and_signout_focus", success_and_signout)

            def late_signout():
                context, page = new_page(no_abort=True)
                try:
                    held = []
                    page.route("**/premiumdata/confluence_screener.json", lambda route: held.append(route))
                    page.evaluate("window.__d04Auth('owner-A','SIGNED_IN')")
                    page.wait_for_function("document.querySelector('#confluence-access-status').dataset.state === 'checking'")
                    page.wait_for_timeout(100)
                    assert len(held) == 1
                    page.evaluate("window.__d04Auth(null,'SIGNED_OUT')")
                    held[0].fulfill(content_type="application/json", body=json.dumps(payload))
                    page.wait_for_timeout(150)
                    assert_locked(page)
                    state(page, "locked")
                    return {"abort_controller": "disabled_fixture", "late_response": "ignored"}
                finally:
                    context.close()
            record("late_success_after_signout_without_abort_support", late_signout)

            def account_switch():
                context, page = new_page(no_abort=True)
                try:
                    held = []
                    page.route("**/premiumdata/confluence_screener.json", lambda route: held.append(route))
                    page.evaluate("window.__d04Auth('owner-A','SIGNED_IN')")
                    page.wait_for_timeout(100)
                    assert len(held) == 1
                    page.evaluate("window.__d04Auth('owner-B','SIGNED_IN')")
                    page.wait_for_timeout(100)
                    assert len(held) == 2
                    held[1].fulfill(status=403, content_type="application/json", body="{}")
                    state(page, "denied")
                    held[0].fulfill(content_type="application/json", body=json.dumps(payload))
                    page.wait_for_timeout(100)
                    state(page, "denied")
                    assert_locked(page)
                    return {"requests": 2, "old_account_response": "ignored"}
                finally:
                    context.close()
            record("account_switch_late_success_cannot_override_denial", account_switch)

            def retry_recovery():
                context, page = new_page()
                try:
                    count = [0]
                    def respond(route):
                        count[0] += 1
                        route.fulfill(status=500 if count[0] == 1 else 200, content_type="application/json",
                                      body="{}" if count[0] == 1 else json.dumps(payload))
                    page.route("**/premiumdata/confluence_screener.json", respond)
                    page.evaluate("window.__d04Auth('owner-A','SIGNED_IN')")
                    state(page, "unavailable")
                    page.locator("#confluence-check-access").focus()
                    page.keyboard.press("Enter")
                    state(page, "loaded")
                    assert count[0] == 2
                    expect(page.locator("[data-confluence-hydrated]")).to_have_count(2)
                    assert page.evaluate("document.activeElement.getAttribute('href')") == "stocks/GATEDBB.html"
                    return {"requests": count[0], "keyboard_retry": "loaded"}
                finally:
                    context.close()
            record("explicit_keyboard_retry_recovers", retry_recovery)

            def retry_focus_ownership():
                context, page = new_page()
                try:
                    pending = []
                    page.route("**/premiumdata/confluence_screener.json", lambda route: pending.append(route))
                    page.evaluate("window.__d04Auth('owner-A','SIGNED_IN')")
                    page.wait_for_timeout(80)
                    pending.pop(0).fulfill(status=500, body="{}")
                    state(page, "unavailable")
                    retry = page.locator("#confluence-check-access")
                    retry.focus()
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(80)
                    target = page.locator(".lc.free a.tkr").first
                    target.focus()
                    pending.pop(0).fulfill(content_type="application/json", body=json.dumps(payload))
                    state(page, "loaded")
                    assert page.evaluate("document.activeElement.getAttribute('href')") == "stocks/FREEAA.html"

                    page.evaluate("window.__d04Auth('owner-A','TOKEN_REFRESHED')")
                    page.wait_for_timeout(80)
                    pending.pop(0).fulfill(status=500, body="{}")
                    state(page, "unavailable")
                    retry.focus()
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(80)
                    pending.pop(0).fulfill(status=500, body="{}")
                    state(page, "unavailable")
                    target.focus()
                    page.evaluate("window.__d04Auth('owner-A','TOKEN_REFRESHED')")
                    page.wait_for_timeout(80)
                    pending.pop(0).fulfill(content_type="application/json", body=json.dumps(payload))
                    state(page, "loaded")
                    assert page.evaluate("document.activeElement.getAttribute('href')") == "stocks/FREEAA.html"
                    return {"moved_focus": "preserved", "failed_retry_intent": "not_reused"}
                finally:
                    context.close()
            record("retry_focus_is_request_scoped_and_not_stolen", retry_focus_ownership)

            for expiry_value, expected in (("null", "unavailable"), ("Date.now()/1000-1", "expired")):
                def rejected_expiry(expiry_value=expiry_value, expected=expected):
                    context, page = new_page()
                    try:
                        calls = []
                        page.route("**/premiumdata/confluence_screener.json", lambda route: calls.append(route))
                        page.evaluate("window.__d04Expiry=" + expiry_value)
                        page.evaluate("window.__d04Auth('owner-A','SIGNED_IN')")
                        state(page, expected)
                        assert_locked(page)
                        assert len(calls) == 0
                        return {"state":expected,"private_requests":0}
                    finally:
                        context.close()
                record("session_deadline_" + expected, rejected_expiry)

            def late_response_after_expiry():
                context, page = new_page(no_abort=True)
                try:
                    pending = []
                    page.route("**/premiumdata/confluence_screener.json", lambda route: pending.append(route))
                    page.evaluate("window.__d04Expiry=Date.now()/1000+0.35;window.__d04Auth('owner-A','SIGNED_IN')")
                    page.wait_for_timeout(100)
                    assert len(pending) == 1
                    state(page, "expired")
                    pending[0].fulfill(content_type="application/json", body=json.dumps(payload))
                    page.wait_for_timeout(100)
                    state(page, "expired")
                    assert_locked(page)
                    assert page.evaluate("window.MDXAuth.user().id") == "owner-A"
                    return {"auth_event": "none_after_signin", "expired_response": "ignored"}
                finally:
                    context.close()
            record("silent_expiry_rejects_late_response_without_abort", late_response_after_expiry)

            def loaded_expiry():
                context, page = new_page()
                try:
                    page.route("**/premiumdata/confluence_screener.json", lambda route: route.fulfill(content_type="application/json", body=json.dumps(payload)))
                    page.evaluate("window.__d04Expiry=Date.now()/1000+0.6;window.__d04Auth('owner-A','SIGNED_IN')")
                    state(page, "loaded")
                    page.locator('[data-confluence-combo="L0002"] a.tkr').focus()
                    state(page, "expired")
                    assert_locked(page)
                    assert page.evaluate("document.activeElement.closest('[data-confluence-combo]')?.dataset.confluenceCombo") == "L0002"
                    return {"silent_expiry":"public_walls_restored","focus":"original_public_row"}
                finally:
                    context.close()
            record("silent_expiry_clears_loaded_names_and_restores_focus", loaded_expiry)

            def refreshed_deadline():
                context, page = new_page()
                try:
                    calls = []
                    def respond(route):
                        calls.append(1)
                        route.fulfill(content_type="application/json", body=json.dumps(payload))
                    page.route("**/premiumdata/confluence_screener.json", respond)
                    page.evaluate("window.__d04Expiry=Date.now()/1000+0.5;window.__d04Auth('owner-A','SIGNED_IN')")
                    state(page, "loaded")
                    page.evaluate("window.__d04Expiry=Date.now()/1000+10;window.__d04Auth('owner-A','TOKEN_REFRESHED')")
                    state(page, "loaded")
                    page.wait_for_timeout(650)
                    state(page, "loaded")
                    assert len(calls) == 2
                    expect(page.locator("[data-confluence-hydrated]")).to_have_count(2)
                    return {"requests":2,"superseded_deadline":"cancelled"}
                finally:
                    context.close()
            record("auth_owner_refresh_replaces_display_deadline", refreshed_deadline)

            def exact_company_return():
                context, page = new_page()
                try:
                    origin_url = page.url
                    page.locator(".lc.free a.tkr").first.click()
                    page.wait_for_url("**/stocks/FREEAA.html")
                    page.go_back(wait_until="load")
                    assert page.url == origin_url
                    expect(page.locator(".hero-state .l-en")).to_contain_text("4 active line-ups")
                    return {"return_url": page.url.replace(origin, "LOCAL_ORIGIN"), "company_path": "/stocks/FREEAA.html"}
                finally:
                    context.close()
            record("free_company_native_back_preserves_exact_url", exact_company_return)

            for theme in ("dark", "light"):
                for lang in ("en", "zh"):
                    for width in (1440, 390):
                        def visual(theme=theme, lang=lang, width=width):
                            context, page = new_page(key="dense", width=width, theme=theme, lang=lang)
                            try:
                                metrics = page.evaluate("""() => {
                                  const card=document.querySelector('.lc.free'), pair=card.querySelector('.lc-wr');
                                  const rates=[card.querySelector('.lc-wr-big'),card.querySelector('.lc-wr-old')];
                                  return {
                                    width:innerWidth, viewport:document.documentElement.clientWidth, scroll:document.documentElement.scrollWidth,
                                    theme:document.documentElement.dataset.theme,lang:document.documentElement.dataset.lang,
                                    pairWidth:pair.getBoundingClientRect().width,
                                    rateSizes:rates.map(x=>parseFloat(getComputedStyle(x).fontSize)),
                                    sampleSize:parseFloat(getComputedStyle(card.querySelector('.lc-sample')).fontSize),
                                    legs:card.querySelectorAll('.leg').length,
                                    rateRects:rates.map(x=>({x:x.getBoundingClientRect().x,right:x.getBoundingClientRect().right})),
                                    buttonMin:Math.min(...[...document.querySelectorAll('.btn,.tkr')].filter(x=>x.getBoundingClientRect().height).map(x=>x.getBoundingClientRect().height)),
                                    ink:getComputedStyle(card.querySelector('.lc-sample')).color, panel:getComputedStyle(card).backgroundColor,
                                    reduced:matchMedia('(prefers-reduced-motion:reduce)').matches
                                  };
                                }""")
                                assert metrics["width"] == width and metrics["scroll"] <= metrics["viewport"] + 1
                                assert metrics["theme"] == theme and metrics["lang"] == lang
                                assert metrics["rateSizes"][0] == metrics["rateSizes"][1] and metrics["rateSizes"][0] >= 28
                                assert metrics["sampleSize"] >= 12.5 and metrics["buttonMin"] >= 44
                                metrics["sampleContrast"] = round(contrast_ratio(metrics["ink"], metrics["panel"]), 2)
                                assert metrics["sampleContrast"] >= 4.5
                                assert metrics["legs"] == 4 and metrics["reduced"]
                                assert page.locator(".ticker-symbol").evaluate_all("(nodes)=>nodes.every(x=>getComputedStyle(x).whiteSpace === 'nowrap' && x.getBoundingClientRect().height < 28)")
                                assert all(r["x"] >= 0 and r["right"] <= width for r in metrics["rateRects"])
                                for other in (".l-en" if lang == "zh" else ".l-zh",):
                                    assert page.locator(".wrap " + other).evaluate_all("(nodes)=>nodes.every(x=>getComputedStyle(x).display==='none')")
                                file = f"dense-{width}-{theme}-{lang}.png"
                                page.screenshot(path=str(out / file), full_page=True)
                                if width == 390:
                                    cropfile = file.replace(".png", "-card.png")
                                    page.locator(".lc.free").screenshot(path=str(out / cropfile))
                                    shots.append({"file":cropfile,"width":width,"theme":theme,"lang":lang,"fixture":"dense_first_card"})
                                shots.append({"file": file, "theme": theme, "lang": lang, "width": width, "fixture": "dense"})
                                disclosure = page.locator(".lc.free .lc-method")
                                summary = disclosure.locator("summary")
                                if width <= 500:
                                    summary.tap()
                                else:
                                    summary.focus()
                                    page.keyboard.press("Enter")
                                expect(disclosure).to_have_attribute("open", "")
                                expect(disclosure.locator("p").first).to_be_visible()
                                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                                if width <= 500:
                                    detailfile = f"method-{width}-{theme}-{lang}.png"
                                    disclosure.screenshot(path=str(out / detailfile))
                                    shots.append({"file":detailfile,"width":width,"theme":theme,"lang":lang,"fixture":"native_method_touch"})
                                    summary.tap()
                                else:
                                    page.keyboard.press("Enter")
                                expect(disclosure).not_to_have_attribute("open", "")
                                assert page.evaluate("document.activeElement.tagName") == "SUMMARY"
                                layout.append(metrics)
                                return metrics
                            finally:
                                context.close()
                        record(f"visual_dense_{width}_{theme}_{lang}", visual)

            for key in ("zero", "unavailable"):
                def source_state(key=key):
                    context, page = new_page(key=key, width=390, theme="light", lang="zh")
                    try:
                        expected = "available-empty" if key == "zero" else "unavailable"
                        expect(page.locator("[data-source-state]")).to_have_attribute("data-source-state", expected)
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                        expect(page.locator(".lc")).to_have_count(0)
                        file = f"source-{key}-390-light-zh.png"
                        page.screenshot(path=str(out / file), full_page=True)
                        shots.append({"file": file, "width": 390, "theme": "light", "lang": "zh", "fixture": key})
                        return {"state": expected}
                    finally:
                        context.close()
                record("source_state_" + key, source_state)

            for width in (320, 820, 1024):
                def intermediate(width=width):
                    context, page = new_page(key="dense", width=width, theme="light", lang="zh")
                    try:
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                        pair = page.locator(".lc.free .lc-wr").bounding_box()
                        assert pair["x"] >= 0 and pair["x"] + pair["width"] <= width
                        return {"width": width, "no_horizontal_overflow": True}
                    finally:
                        context.close()
                record("responsive_" + str(width), intermediate)

            for theme in ("dark", "light"):
                context, page = new_page(key="real", theme=theme)
                try:
                    file = f"source-artifact-1440-{theme}-en.png"
                    page.screenshot(path=str(out / file), full_page=True)
                    shots.append({"file":file, "width":1440, "theme":theme, "lang":"en", "fixture":"committed_source_artifact",
                                  "source_generated_utc": real["generated_utc"]})
                finally:
                    context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()

    for shot in shots:
        data = (out / shot["file"]).read_bytes()
        shot["sha256"] = hashlib.sha256(data).hexdigest()
        shot["bytes"] = len(data)
    report = {"observed_at_utc":datetime.now(timezone.utc).isoformat(), "browser":version,
              "scope":"local actual renderer/theme/handlers; controlled auth and HTTP fixtures, no production account or deployment proof",
              "cases":results, "screenshots":shots, "layout":layout,
              "source_sha256":{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in
                               ["scripts/build_confluence_screener.py","templates/confluence_screener.html.j2",
                                "scripts/verify_confluence_screener_browser.py","tests/test_confluence_screener_page.py",
                                "templates/theme.js","site/theme.js","site/theme.css","site/confluence_screener.html",
                                "site/premiumdata/confluence_screener.json","site/factordata/tech_confluence.json"]},
              "passed":sum(x["status"]=="PASS" for x in results), "failed":sum(x["status"]=="FAIL" for x in results)}
    (out / "browser-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed":report["passed"],"failed":report["failed"],"screenshots":len(shots),
                      "report":str(out/"browser-report.json"),
                      "failures":[{"name":x["name"],"error":x.get("error")} for x in results if x["status"]=="FAIL"]},ensure_ascii=False))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
