"""Browser conformance for the actual stocks template, using synthetic inputs only.

No request reaches a market, account, service or production endpoint. The output
proves presentation and refresh behavior, never data admission or live delivery.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


def fixtures() -> tuple[dict, dict]:
    roster = ["DEMO"] + [f"TEST{i:02d}" for i in range(1, 15)]
    row = {
        "state": "UPTURN_CONFIRMED", "k": 3,
        "monthly_phase": "below_water_rising", "since": "2026-10-14",
        "legs": {"d_macd": True, "d3_confluence": True,
                 "w_macd": "cross", "w2_macd": False},
        "trend": {x: {"pos": True, "bars_since_cross": 2}
                  for x in ["d", "d3", "w", "w2"]}, "basket_ids": [],
    }
    mtf = {"schema": "mtf_upturn.v1", "as_of": "2026-11-03",
           "universe_n": 15, "evaluated_n": 15, "failed_n": 0,
           "cohort": {"confirmed": roster, "watch": []},
           "tickers": {x: row for x in roster}}
    clock = "2026-11-03T20:45:00Z"
    timing = {
        "state": "confirmed", "live": True, "assessed_at": clock,
        "trigger": 100, "invalidation": 97.5, "chase_above": 101.5,
        "distance_pct": 0.4, "quote_asof": "2026-11-03T20:30:00Z",
        "confirmed_at": "2026-11-03T20:30:00Z", "confirmed_known_at": clock,
        "structure_3h": {"state": "confirmed", "asof": "2026-11-03T20:30:00Z",
                         "checks": [{"id": k, "status": "pass"} for k in
                                    ["h3_complete", "h3_higher_low", "h3_reclaim"]]},
        "trigger_30m": {"state": "confirmed", "asof": "2026-11-03T20:30:00Z",
                        "checks": [{"id": k, "status": "pass"} for k in
                                   ["m30_close", "invalidation"]]},
        "checks": [{"id": k, "status": "pass"} for k in
                   ["parent_valid", "no_chase", "data_quality"]],
    }
    pivot = {"schema": "prophet.pivot_checklist/v1", "assessed_at": clock,
             "valid_until": "2026-11-03T20:51:00Z", "source_admitted": True,
             "input_kind": "OBSERVED_MARKET", "feed_delay_min": 15,
             "tickers": {"DEMO": timing}, "recent_events": [
                 {"event_id": "synthetic-forming", "kind": "pivot_checklist", "ticker": "DEMO",
                  "state": "forming", "at": "2026-11-03T19:45:00Z"},
                 {"event_id": "synthetic-testing", "kind": "pivot_checklist", "ticker": "DEMO",
                  "state": "testing", "at": "2026-11-03T20:15:00Z"},
                 {"event_id": "synthetic-close", "kind": "pivot_checklist", "ticker": "DEMO",
                  "state": "confirmed", "at": clock}]}

    # OBSERVED_MARKET here exercises the presentation gate with a simulated
    # admitted response. This fixture is never passed to a producer or publisher.
    artifact = {"schema": "prophet_live.states/v1", "status": "dark",
                "reason": "no_pack", "states": {},
                "proof_class": "SYNTHETIC_CONFORMANCE",
                "meta": {"pass_ts": clock, "session_et": "2026-11-03",
                         "pack_as_of": "2026-11-02", "states": {}, "dark_counts": {}},
                "pivot_checklist": pivot}
    return mtf, artifact


def capture(root: Path, out: Path, executable: str | None = None) -> dict:
    from playwright.sync_api import sync_playwright
    from scripts.capture_us_stocks_compression_evidence import render_stocks_page

    out.mkdir(parents=True, exist_ok=True)
    html = render_stocks_page()
    mtf, artifact = fixtures()
    observations = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=executable)
        try:
            for width in [1440, 390]:
                for theme in ["light", "dark"]:
                    for lang in ["en", "zh"]:
                        context = browser.new_context(viewport={"width": width, "height": 900})
                        context.add_init_script(
                            "localStorage.setItem('theme', " + json.dumps(theme) + ");"
                            "localStorage.setItem('lang', " + json.dumps(lang) + ");")
                        # Isolated browser fixture only. Exercise the real tier
                        # resolver with a synthetic native session and /api/me reply.
                        context.add_init_script("""
                            const fixtureAuth={user:()=>({id:'fixture-user'}),hasSession:()=>true,
                              client:()=>Promise.resolve({auth:{getSession:()=>Promise.resolve({data:{session:{
                                user:{id:'fixture-user'},access_token:'synthetic-invalid-token'}}})}}),
                              onChange:()=>{},open:()=>{}};
                            Object.defineProperty(window,'MDXAuth',{configurable:true,
                              get:()=>fixtureAuth,set:()=>{}});
                        """)
                        page = context.new_page()
                        page.clock.install(time=datetime(2026, 11, 3, 20, 45, tzinfo=timezone.utc))
                        requests: list[str] = []
                        errors: list[str] = []
                        page.on("pageerror", lambda e: errors.append(str(e)))

                        def respond(route):
                            path = urlparse(route.request.url).path
                            requests.append(path)
                            if path == "/api/me":
                                route.fulfill(json={"id":"fixture-user","tier":"pro"})
                            elif path == "/us_stocks.html":
                                route.fulfill(body=html, content_type="text/html")
                            elif path == "/stockdata/mtf_upturn.json":
                                route.fulfill(json=mtf)
                            elif path == "/live/prophet_live.json":
                                route.fulfill(json=artifact)
                            elif path.endswith(".json"):
                                route.fulfill(json={})
                            else:
                                for folder in ["templates", "site"]:
                                    base = root / folder
                                    asset = base / path.lstrip("/")
                                    if asset.is_file() and asset.resolve().is_relative_to(base.resolve()):
                                        route.fulfill(body=asset.read_bytes(), content_type=
                                                      mimetypes.guess_type(asset.name)[0] or
                                                      "application/octet-stream")
                                        return
                                route.fulfill(body="", content_type="text/plain")

                        page.route("**/*", respond)
                        page.goto("http://pivot.test/us_stocks.html", wait_until="load")
                        page.locator('[data-pvt-symbol="DEMO"]').wait_for(state="visible")
                        page.wait_for_function("document.documentElement.dataset.accessTier==='pro'")
                        details = page.locator('[data-pvt-symbol="DEMO"]')
                        count = page.locator("[data-pvt-row]:visible").count()
                        assert count == 12, {"folded_rows": count, "errors": errors}
                        details.locator("summary").click()
                        page.locator('.pvt-dialog[open]').wait_for(state='visible')
                        assert page.locator("[data-pvt-row]:visible").count() == 12
                        assert page.locator("[data-pvt-heading]").count() == 1
                        assert details.evaluate("e=>e.open")
                        page.evaluate("""document.querySelector('#dash-mtf-section h2').prepend(
                            document.createTextNode('SYNTHETIC TEST · '))""")
                        shot = f"{width}-{theme}-{lang}.png"
                        page.screenshot(path=str(out / shot))
                        # The long mobile disclosure remains scrollable with its close control visible.
                        if width == 390:
                            dialog = page.locator('.pvt-dialog')
                            dialog.evaluate("e=>e.scrollTop=e.scrollHeight")
                            assert page.locator('.pvt-dialog .pvt-footnote').is_visible()
                            assert page.locator('.pvt-close').is_visible()
                            for target in ['.pvt-dialog .pvt-footnote', '.pvt-close']:
                                box = page.locator(target).bounding_box()
                                assert box and box['y'] >= 0 and box['y'] + box['height'] <= 900
                            assert dialog.evaluate("e=>e.scrollWidth<=e.clientWidth+1")
                            dialog.evaluate("e=>e.scrollTop=0")
                        # Refresh while open preserves a single dialog and its focus.
                        page.evaluate("value => {value.pivot_checklist.tickers.DEMO.distance_pct=0.5; document.dispatchEvent(new CustomEvent('prophet:live-update', {detail:value}));}", artifact)
                        assert page.locator('.pvt-dialog[open]').count() == 1
                        assert page.locator('.pvt-dialog .pvt-history li').count() == 3
                        assert page.locator('.pvt-dialog .pvt-context .dash-mtf-leg').count() == 4
                        page.keyboard.press("Escape")
                        assert not page.locator('.pvt-dialog[open]').count()
                        assert details.locator("summary").evaluate("e=>document.activeElement===e")
                        details.locator("summary").click()
                        page.locator('.pvt-dialog[open]').wait_for(state='visible')
                        page.evaluate("window.dispatchEvent(new Event('mmx-access-tier'))")
                        assert not page.locator('.pvt-dialog[open]').count()
                        page.locator(".dash-mtf-more").click()
                        assert page.locator("[data-pvt-row]:visible").count() == 15, page.evaluate("""() => ({total:document.querySelectorAll('[data-pvt-row]').length,rows:Array.from(document.querySelectorAll('[data-pvt-row]')).map(x=>[x.dataset.pvtRow,getComputedStyle(x).display]),wrap:document.querySelector('.dash-mtf-collapse').className,button:document.querySelector('.dash-mtf-more').outerHTML})""")
                        page.locator(".dash-mtf-more").click()
                        assert page.locator("[data-pvt-row]:visible").count() == 12
                        assert not details.evaluate("e=>e.open")
                        page.clock.fast_forward(361001)
                        assert "Update overdue" in details.text_content()
                        assert not page.locator(".pvt-state-confirmed").count()
                        assert not any("pivot" in url for url in requests), requests
                        assert not errors, errors
                        observations.append({"width": width, "theme": theme, "lang": lang,
                                             "screenshot": shot, "fold": "PASS",
                                             "expiry": "PASS", "history": "PASS",
                                             "dialog_focus_escape_access_change": "PASS", "errors": errors})
                        context.close()
        finally:
            browser.close()
    receipt = {"proof_class": "SYNTHETIC_CONFORMANCE", "surface": "actual stocks template",
               "market_data_proof": False, "production_delivery_proof": False,
               "access_context": "simulated Pro account; no real authentication",
               "observations": observations}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browser", default=None)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(capture(root, args.out, args.browser), indent=2))


if __name__ == "__main__":
    main()
