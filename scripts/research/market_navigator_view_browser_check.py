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
from engine.market_navigator_price_confirmation import ClosedBar, LevelRule, qualified_observation


def synthetic_wire() -> dict:
    cutoff = "2026-10-21T20:01:00Z"
    receipt = Receipt("fixture:visual", "fixture-v1", "2026-10-21T20:00:00Z",
                      "2026-10-21T20:00:01Z", "2026-10-21T20:00:02Z",
                      "2026-10-21T20:05:00Z")
    # The first scenario is a complete end-to-end deterministic confirmation:
    # three wholly synthetic completed daily bars -> typed owner-verifier
    # fixture -> binary ratio observation -> the existing Python compositor
    # -> request-bound wire -> JS admission -> bilingual DOM. This intentionally
    # does not validate any operational market receipt or real strategy.
    sample_closes = (99.0, 101.0, 102.0)
    sample_days = ("2026-10-19", "2026-10-20", "2026-10-21")
    original_bars = tuple(
        ClosedBar(
            subject="SPY:ARCX", horizon="swing", generation_ref="fixture:visual-generation",
            receipt_ref=f"fixture:bar:{index}", revision="fixture:visual-generation",
            session_ref=f"fixture:session:{day}", sequence=17 + index,
            begins_at=f"{day}T19:55:00Z", ends_at=f"{day}T20:00:00Z",
            available_at=f"{day}T20:00:02Z", valid_until="2026-10-21T20:05:00Z",
            open=sample_closes[index-1] if index else sample_closes[0],
            high=max(sample_closes[index-1] if index else sample_closes[0],
                     sample_closes[index])+0.5,
            low=min(sample_closes[index-1] if index else sample_closes[0],
                    sample_closes[index])-0.5,
            close=sample_closes[index], unit="USD", completed=True,
        ) for index, day in enumerate(sample_days)
    )
    level_rule = LevelRule("SPY:ARCX", "swing", "cross_above", 100, "USD", 2,
                           "fixture:reclaim-original", "2026-10-18T13:00:00Z",
                           "2026-10-21T20:04:00Z")
    derived = Receipt("fixture:completed-bar-proof", "fixture:visual-generation",
                      "2026-10-21T20:00:00Z", "2026-10-21T20:00:01Z",
                      "2026-10-21T20:00:02Z", "2026-10-21T20:05:00Z")
    confirmed_reclaim = qualified_observation(
        rule=level_rule, as_of=cutoff, bars=original_bars, expected_last_sequence=19,
        verify_owner=lambda *_: True, receipt=derived, key="confirmed_reclaim")
    assert confirmed_reclaim is not None and confirmed_reclaim.value == 1.0
    observations = (
        Observation("price", "SPY:ARCX", "price", 100.00, "USD", ("swing",), receipt),
        confirmed_reclaim,
        Observation("breadth", "SPY:ARCX", "breadth", None, "percent", ("swing",), receipt),
    )
    scenarios = (
        Scenario("holding", "SPY:ARCX", "swing", "2026-10-18T13:00:00Z", "fixture:rule1",
                 "2026-10-21T20:04:00Z", (Condition("confirmed_reclaim", "gte", 1, "ratio"),),
                 (Condition("confirmed_reclaim", "lt", 1, "ratio"),),
                 ("confirmed_reclaim",), ("breadth",)),
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
    assert next(row for row in context["observations"] if row["key"] == "confirmed_reclaim")["value"] == 1.0
    assert next(row for row in context["scenarios"] if row["key"] == "holding")["status"] == "conditions_met"
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
                    page.on("request", lambda request: requests.append(request.url)
                            if not request.url.startswith("http://localhost/") else None)
                    # An intercepted localhost navigation supplies a secure origin
                    # for Web Crypto (about:blank has no subtle digest). It makes
                    # no real network call or backend request.
                    page.route("http://localhost/**", lambda route: route.fulfill(
                        status=200,content_type="text/html",
                        body='<main id="navigator"></main>'))
                    page.goto("http://localhost/navigator-synthetic", wait_until="domcontentloaded")
                    assert page.evaluate("isSecureContext && !!crypto.subtle")
                    page.add_style_tag(path=str(_ROOT / "templates/market_navigator_view.css"))
                    page.add_script_tag(path=str(_ROOT / "templates/market_navigator_client.js"))
                    page.add_script_tag(path=str(_ROOT / "templates/market_navigator_view.js"))
                    page.add_script_tag(path=str(_ROOT / "templates/market_navigator_mount.js"))
                    output = page.evaluate("""async ({wire,language,theme}) => {
                      const storage = [];
                      ['getItem','setItem','removeItem','clear'].forEach(name => {
                        Storage.prototype[name] = function(){storage.push(name);throw new Error('browser storage accessed');};
                      });
                      window.__navigatorScope='fixture:principal-A';
                      window.__navigatorReads=0;
                      const surface=window.MastermindNavigatorMount.createSurface(
                        document.querySelector('#navigator'), {getScope:()=>window.__navigatorScope});
                      window.__navigatorSurface=surface;
                      surface.rebind({
                        scope_key:'fixture:principal-A',
                        subject:'SPY:ARCX',horizon:'swing',as_of:wire.requested_as_of,
                        subjectLabel:'SPY · NYSE Arca',language,theme,
                        read:async request => {
                          window.__navigatorReads++;
                          return {...wire,request_id:request.request_id};
                        }
                      });
                      if (window.__navigatorReads!==0) throw Error('auto-read violated');
                      await surface.activate();
                      if (window.__navigatorReads!==1) throw Error('extra source read');
                      return {storage,html:document.body.innerText};
                    }""", {"wire":wire, "language":language,"theme":theme})
                    assert not output["storage"]
                    assert not failures and not requests, (failures, requests)
                    assert page.locator(".mnv-path").count() == 3
                    assert page.locator(".mnv-path-state").count() == 3
                    assert page.locator(".mnv-path-diagnosis").count() == 3
                    summaries=page.locator(".mnv-path-diagnosis").all_inner_texts()
                    assert all(summaries)
                    assert not any("buy" in summary.lower() or "%" in summary
                                   for summary in summaries)
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
                    page.locator('.mnv-path[data-scenario-key="holding"] .mnv-summary').click()
                    assert "confirmed reclaim" in page.locator(
                        '.mnv-path[data-scenario-key="holding"] .mnv-condition-list').first.inner_text().lower()
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
                    page.evaluate("""async () => {
                      window.__navigatorScope='fixture:principal-B';
                      const result=await window.__navigatorSurface.activate();
                      if (result!==false || window.__navigatorReads!==1)
                        throw Error('scope-switch leaked or read');
                    }""")
                    assert page.locator(".mnv-path").count() == 0
                    results.append({"width":width,"language":language,"theme":theme,
                                    "no_overflow":True,"paths":3,"focus_return":True,
                                    "withdraws_stale":True,"account_scope_denial":True,
                                    "source_reads":1,"storage_accesses":0,"network_requests":0})
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
