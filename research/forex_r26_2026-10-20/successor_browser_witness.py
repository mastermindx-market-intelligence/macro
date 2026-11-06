"""Successor R26 proof: real builder/Jinja + local Chromium, synthetic market inputs.

No live market collection, account writes, ledger writes or network delivery.
This evidence is deliberately distinct from deployed Macro-origin acceptance.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path.cwd()
OUT = Path(__file__).resolve().parent / "successor_evidence"
OUT.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location("r26_workspace_witness", ROOT / "tests/test_forex_r26_workspace.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
cases = {}
for name, params in (("current", {}), ("missing_risk", {"missing_risk": True}),
                     ("older_risk", {"risk_date": "2026-10-20"})):
    with pytest.MonkeyPatch.context() as mp:
        snapshot, path, context = fixture.render_case(OUT / name, mp, **params)
    html = path.read_text()
    for asset in set(re.findall(r'(?:src|href)="([^"?#]+)(?:[^"]*)"', html)):
        candidate = ROOT / "templates" / asset
        if "/" not in asset and asset.endswith((".css", ".js")) and candidate.is_file():
            (path.parent / asset).write_bytes(candidate.read_bytes())
    cases[name] = (snapshot, path)

tracked = ["scripts/build_forex.py", "lib/forex_r26_consumer.py", "templates/forex.html.j2",
           "templates/forex_r26_workspace.html.j2", "templates/forex_r26.css", "templates/forex_r26.js",
           "tests/test_forex_r26_workspace.py"]
hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in tracked}
report = {"status": "RUNNING", "scope": "actual builder and Jinja; synthetic market inputs; local Chromium; all HTTP(S) blocked",
          "production_acceptance": False, "source_sha256": hashes, "cases": [], "errors": []}
try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for viewport, width, height in (("desktop", 1440, 1050), ("tablet", 834, 1112), ("mobile", 390, 844)):
            for lang in ("en", "zh"):
                for theme in ("light", "dark"):
                    ident = f"{viewport}-{lang}-{theme}"
                    context = browser.new_context(viewport={"width": width, "height": height}, reduced_motion="reduce", locale="en-US")
                    requests, errors = [], []
                    def block(route):
                        requests.append({"url": route.request.url, "method": route.request.method})
                        route.abort()
                    context.route("http://**/*", block)
                    context.route("https://**/*", block)
                    page = context.new_page()
                    page.on("pageerror", lambda err: errors.append(str(err)))
                    snapshot, path = cases["current"]
                    page.goto(path.as_uri() + "?review_fixture=synthetic", wait_until="load")
                    page.evaluate("([lang,theme])=>{document.documentElement.setAttribute('data-lang',lang);document.documentElement.setAttribute('data-theme',theme)}", [lang,theme])
                    page.wait_for_timeout(100)
                    root = page.locator("#forex-workspace")
                    assert root.is_visible()
                    assert json.loads(page.locator("#forex-r26-consumer").text_content()) == snapshot["r26_consumer"]
                    captures = []
                    def capture(state):
                        overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
                        if overflow:
                            offenders = page.evaluate("Array.from(document.querySelectorAll('body *')).filter(e=>e.getBoundingClientRect().right>innerWidth+1).slice(0,12).map(e=>({tag:e.tagName,cls:e.className,width:e.getBoundingClientRect().width,right:e.getBoundingClientRect().right}))")
                            raise AssertionError(f"{ident}/{state}: overflow {offenders}")
                        target = OUT / f"{ident}-{state}.png"
                        page.screenshot(path=str(target), full_page=False)
                        captures.append(target.name)
                    capture("today")
                    root.locator("[data-fxr-destination='explore']").click()
                    root.locator("#fxr-search").fill("JPY")
                    assert root.locator("[data-fxr-search-row]:visible").count() == 1
                    root.locator("[data-fxr-view='explore'] [data-fxr-open-pair='USDJPY']").click()
                    assert root.locator("[data-fxr-pair='USDJPY']").is_visible()
                    article = root.locator("[data-fxr-pair='USDJPY']")
                    assert "q=JPY" in page.url and "review_fixture=synthetic" in page.url
                    assert article.locator("[data-fxr-panel='outlook']").is_visible()
                    assert "Leaning lower" in article.locator(".fxr-decision").text_content()
                    capture("outlook")
                    outlook = article.locator("[data-fxr-pair-tab='outlook']")
                    outlook.focus()
                    page.keyboard.press("ArrowRight")
                    assert article.locator("[data-fxr-panel='drivers']").is_visible()
                    assert article.locator("[data-fxr-pair-tab='drivers']").evaluate("(e)=>e===document.activeElement")
                    article.locator("[data-fxr-pair-tab='history']").click()
                    assert article.locator("[data-fxr-panel='history']").is_visible()
                    assert "JPY: Trend turned up" in article.locator("[data-fxr-panel='history']").text_content()
                    article.locator("[data-fxr-pair-tab='impact']").click()
                    assert article.locator("[data-fxr-panel='impact']").is_visible()
                    if viewport == "mobile":
                        capture("impact")
                    root.locator("#fxr-back").click()
                    assert root.locator("[data-fxr-view='explore']").is_visible()
                    assert root.locator("#fxr-search").input_value() == "JPY"
                    root.locator("#fxr-search").fill("")
                    root.locator("[data-fxr-compare-pair='EURUSD']").check()
                    root.locator("[data-fxr-compare-pair='USDJPY']").check()
                    root.locator("[data-fxr-compare-pair='AUDUSD']").click()
                    assert not root.locator("[data-fxr-compare-pair='AUDUSD']").is_checked()
                    root.locator("#fxr-compare").click()
                    assert root.locator("#fxr-compare-dialog").is_visible()
                    assert root.locator("#fxr-compare-body > section").count() == 2
                    page.keyboard.press("Escape")
                    assert not root.locator("#fxr-compare-dialog").is_visible()
                    assert root.locator("#fxr-compare").evaluate("(e)=>e===document.activeElement")
                    root.locator("[data-fxr-view='explore'] [data-fxr-open-pair='USDJPY']").click()
                    article.locator("[data-fxr-source]").first.click()
                    assert root.locator("#fxr-source-dialog").is_visible()
                    page.keyboard.press("Escape")
                    assert not root.locator("#fxr-source-dialog").is_visible()
                    before_storage = page.evaluate("JSON.stringify(Object.fromEntries(Object.entries(localStorage)))")
                    article.locator("[data-fxr-prepare]").first.click()
                    form = root.locator("#fxr-rule-form")
                    form.locator("[name='threshold']").fill("145.6")
                    form.locator("[name='consecutive']").fill("2")
                    form.locator("[name='operator']").select_option("lt")
                    expiry = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")
                    form.locator("[name='expires_at']").fill(expiry)
                    form.locator("[type='submit']").click()
                    assert root.locator("#fxr-rule-review").is_visible()
                    rule = json.loads(root.locator("#fxr-rule-json").text_content())
                    assert rule["threshold"] == 145.6 and rule["consecutive"] == 2 and rule["operator"] == "lt"
                    assert rule["feed"] is rule["condition_id"] is rule["revision"] is None
                    assert rule["active"] is False and rule["saved"] is False and rule["state"] == "prepared"
                    assert rule["expires_at"] == expiry + ":00.000Z"
                    capture("condition")
                    root.locator("#fxr-keep-rule").click()
                    assert root.locator("[data-fxr-view='my_watches']").is_visible()
                    assert root.locator("#fxr-prepared-list article").count() == 1
                    assert before_storage == page.evaluate("JSON.stringify(Object.fromEntries(Object.entries(localStorage)))")
                    page.reload(wait_until="load")
                    assert root.locator("[data-fxr-view='my_watches']").is_visible()
                    assert root.locator("#fxr-prepared-section").is_hidden()
                    assert not any("forex_r26" in err for err in errors), errors
                    assert not any(re.search(r"(forex.*watch|price-close|watch.*activate)", request["url"], re.I) for request in requests)
                    report["cases"].append({"id": ident, "viewport": [width,height], "lang": lang, "theme": theme,
                        "status": "PASS", "html_json_parity": True, "tab_keyboard": True, "modal_escape_focus": True,
                        "quote_orientation": True, "history_basis": True, "search_context_retained": True,
                        "comparison": True, "exact_condition": rule, "no_watch_persistence": True,
                        "no_watch_delivery": True, "horizontal_overflow": False, "screenshots": captures,
                        "blocked_external_requests": len(requests), "page_errors": errors})
                    (OUT / "browser.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
                    print("PASS", ident, flush=True)
                    context.close()
        for name in ("missing_risk","older_risk"):
            context = browser.new_context(viewport={"width":1440,"height":1050}, reduced_motion="reduce")
            context.route("http://**/*", lambda route: route.abort())
            context.route("https://**/*", lambda route: route.abort())
            page = context.new_page()
            snapshot,path = cases[name]
            page.goto(path.as_uri(), wait_until="load")
            assert snapshot["r26_consumer"]["current_read"]["available"] is False
            assert page.locator("#fxr-today .fxr-hero h2").inner_text() == "A current read needs fresh evidence."
            assert page.locator("#fxr-today .fxr-pair-row").count() == 6
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
            page.screenshot(path=str(OUT / (name + "-desktop.png")))
            report["cases"].append({"id":name,"status":"PASS","current_read_withheld":True,"dated_quotes_retained":True,
                                    "screenshot":name+"-desktop.png"})
            context.close()
        browser.close()
    report["status"] = "PASS"
except BaseException as error:
    report["status"] = "FAIL"
    report["errors"].append(repr(error))
    raise
finally:
    report["source_unchanged"] = hashes == {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in tracked}
    (OUT / "browser.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({"status":report["status"],"cases":len(report["cases"]),"source_unchanged":report["source_unchanged"],"errors":report["errors"]}, indent=2))
