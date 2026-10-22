"""Visible Chromium smoke of Navigator's *inert* consumer/view; no live data/auth.
No network, disk cache, user storage, subscriptions or backend service is used.
Only the explicit output report and optional screenshots are written.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from engine.market_navigator import Condition, Observation, Receipt, Scenario, compose
from engine.market_navigator_response import bind_response


def synthetic_wire() -> dict:
    cutoff = "2026-10-21T20:01:00Z"
    receipt = Receipt("fixture:visual", "fixture-v1", "2026-10-21T20:00:00Z",
                      "2026-10-21T20:00:01Z", "2026-10-21T20:00:02Z",
                      "2026-10-21T20:05:00Z")
    observations = (
        Observation("price", "SPY:ARCX", "price", 100.00, "USD", ("swing",), receipt),
        Observation("breadth", "SPY:ARCX", "breadth", None, "percent", ("swing",), receipt),
    )
    scenarios = (
        Scenario("holding", "SPY:ARCX", "swing", "2026-10-21T19:00:00Z", "fixture:rule1",
                 "2026-10-21T20:04:00Z", (Condition("price", "gte", 99, "USD"),),
                 (Condition("price", "lt", 98, "USD"),), ("price",), ("breadth",)),
        Scenario("extension", "SPY:ARCX", "swing", "2026-10-21T19:00:00Z", "fixture:rule2",
                 "2026-10-21T20:04:00Z", (Condition("price", "gt", 102, "USD"),),
                 (Condition("price", "lt", 98, "USD"),), ("price",), ()),
        Scenario("participation", "SPY:ARCX", "swing", "2026-10-21T19:00:00Z", "fixture:rule3",
                 "2026-10-21T20:04:00Z", (Condition("breadth", "gt", 50, "percent"),),
                 (Condition("price", "lt", 98, "USD"),), ("breadth",), ("price",)),
    )
    context = compose(
        subject="SPY:ARCX", horizon="swing", as_of=cutoff, observations=observations,
        scenarios=scenarios,
        market_state={"schema": "market_state.v1", "market": "us",
                      "is_display_only": True, "verdict": "MIXED", "asof": "2026-10-21",
                      "freshness": {"stale": False, "any_input_stale": False},
                      "input_vintages": {}, "stale_inputs": [], "degraded_components": []},
        market_state_receipt=receipt, expected_market_session="2026-10-21",
        canonical_session_complete=True,
    )
    return bind_response(context, request_id="navigator-1", expected_subject="SPY:ARCX",
                         expected_horizon="swing", requested_as_of=cutoff)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--screenshots", type=Path, default=None)
    args = parser.parse_args()
    wire = synthetic_wire()
    from playwright.sync_api import sync_playwright
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for width in (1440, 390):
            for language in ("en", "zh"):
                for theme in ("dark", "light"):
                    page = browser.new_page(viewport={"width":width,"height":900},device_scale_factor=1)
                    failures: list[str] = []
                    requests: list[str] = []
                    page.on("pageerror", lambda error: failures.append(str(error)))
                    page.on("request", lambda request: requests.append(request.url))
                    page.set_content('<main id="navigator"></main>')
                    page.add_style_tag(path=str(_ROOT / "templates/market_navigator_view.css"))
                    page.add_script_tag(path=str(_ROOT / "templates/market_navigator_client.js"))
                    page.add_script_tag(path=str(_ROOT / "templates/market_navigator_view.js"))
                    output = page.evaluate("""async ({wire,language,theme}) => {
                      const storage = [];
                      ['getItem','setItem','removeItem','clear'].forEach(name => {
                        Storage.prototype[name] = function(){storage.push(name);throw new Error('browser storage accessed');};
                      });
                      const view = window.MastermindNavigatorView.createView(
                        document.querySelector('#navigator'), {language,theme,subjectLabel:'SPY · NYSE Arca'});
                      const client = window.MastermindNavigatorClient.createController({
                        render:view.render,
                        read:async request => ({...wire,request_id:request.request_id})
                      });
                      await client.load({subject:'SPY:ARCX',horizon:'swing',as_of:wire.requested_as_of});
                      return {storage,html:document.body.innerText};
                    }""", {"wire":wire, "language":language,"theme":theme})
                    assert not output["storage"]
                    assert not failures and not requests, (failures, requests)
                    assert page.locator(".mnv-path").count() == 3
                    assert page.locator(".mnv-path-state").count() == 3
                    assert "probability" not in page.locator(".mnv-regime").inner_text().lower()
                    assert page.locator(".mnv-regime").count() == 1
                    assert 'SPY' in page.locator('.mnv-meta').inner_text()
                    assert page.locator(".mnv").get_attribute("lang") == language
                    assert page.locator(".mnv").get_attribute("data-theme") == theme
                    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
                    assert page.locator(".mnv-summary").count() == 3
                    if args.screenshots is not None:
                        args.screenshots.mkdir(parents=True,exist_ok=True)
                        page.screenshot(path=str(args.screenshots / f"{width}-{language}-{theme}.png"),full_page=True)
                    page.locator(".mnv-summary").first.click()
                    assert page.locator(".mnv-condition-list li").count() >= 2
                    assert page.locator(".mnv-evidence-list").count() >= 2
                    page.get_by_role("button",name=("Switch to Chinese" if language=="en" else "Switch to English")).click()
                    assert page.locator(".mnv").get_attribute("lang") != language
                    assert page.locator(".mnv-controls button").first.evaluate("(n)=>n===document.activeElement")
                    assert page.locator('.mnv-path-details[open]').count() == 1
                    page.locator(".mnv-controls button").last.click()
                    assert page.locator('.mnv-path-details[open]').count() == 1
                    assert page.locator(".mnv").get_attribute("data-theme") != theme
                    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
                    page.evaluate("""() => {document.querySelector('#navigator').replaceChildren();
                      const v = window.MastermindNavigatorView.createView(
                        document.querySelector('#navigator'),{language:'en',theme:'dark'});
                      v.render({status:'unavailable',data:null});}""")
                    assert page.locator(".mnv-path").count() == 0
                    assert "unavailable" in page.locator(".mnv-empty-title").inner_text()
                    results.append({"width":width,"language":language,"theme":theme,
                                    "no_overflow":True,"paths":3,"focus_return":True,
                                    "withdraws_stale":True,"storage_accesses":0,"network_requests":0})
                    page.close()
        version = browser.version
        browser.close()
    report = {"schema":"market_navigator.view_browser_proof/v1",
              "evidence_class":"SYNTHETIC_LOCAL_BROWSER","browser":version,
              "production_proof":False,"paper_applied":False,"signed_in":False,
              "paths_are_unranked":True,"no_trading_authority":True,
              "cases":results,"passed":len(results),"backend_reads":0,
              "limitations":"Synthetic conditions and source receipts; no actual source entitlement, saved state, alert, Paper or production."}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"passed":len(results),"browser":version,"output":str(args.output)}))


if __name__ == "__main__":
    main()
