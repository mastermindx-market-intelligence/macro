"""Capture the asset-read journey with the existing commodity renderer/browser helpers.

Synthetic fixtures only. No vendor requests, model calibration or production
writes. This supplements, and does not replace, R1 full-page release evidence.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import capture_commodities_w6_evidence as owner
from scripts.commodity_asset_read import attach_asset_reads, calibration_evidence


def fixture_context(scenario="split"):
    import pandas as pd
    from lib import config
    if scenario not in ("split", "incomplete", "lagging", "calibration"):
        raise ValueError("unknown asset-read fixture")
    context = owner.fixture_vm()
    context["as_of"] = "Synthetic R2 fixture"
    context["built"] = "Synthetic R2 fixture — not a live market update"
    specs = {
        "gold": (0.0, "high_risk", "bear", "SELL", "AVOID", ("D", "3D")),
        "silver": (0.0, "high_risk", "bear", "BUY", "WAIT", ("D", "3D")),
        "copper": (0.5, "high_risk", "neutral", "HOLD", "CAUTION", ("D",)),
        "oil": (1.0, "low_risk", "bull", "BUY", "TREND-FOLLOW", ()),
    }
    frames = {}
    assets = {a["key"]:a for a in context["assets"]}
    for d in context["vm"]["detail"]:
        name = d["name"]
        if name not in specs:
            continue
        alloc, risk, mom, action, grade, down = specs[name]
        day = "2026-09-12" if scenario == "lagging" and name == "gold" else "2026-09-15"
        values = {"close":100.0,"alloc_optimal":alloc,"risk_regime":risk,
                  "momentum_state":mom,"ts_trend":"up","driver_score":-0.4}
        if scenario == "incomplete" and name == "gold":
            values["alloc_optimal"] = None
        frames[name] = pd.DataFrame([values], index=pd.to_datetime([day]))
        d["mtf_rows"] = [
            {"key":k,"label":en,"label_zh":zh,"trend":"down" if k in down else "up",
             "macd":"neg" if k in down else "pos","rsi14":40 if k in down else 60,
             "rsi5":None,"stoch":None}
            for k,en,zh in (("D","Daily","日线"),("3D","3-session","三交易日"),("W","Weekly","周线"))
        ]
        d["verdict"] = {"grade":grade,"headline":"Synthetic timeframe assessment",
                        "headline_zh":"模拟周期判断"}
        assets[name]["conviction"] = {"action":action,"score":-30 if action=="SELL" else 30 if action=="BUY" else 0}
    if scenario == "calibration":
        # These are explicit fixture parameters, not measurements or fitted models.
        for name, quality in (("gold", False), ("silver", True), ("copper", None), ("oil", None)):
            calibration = {} if name == "copper" else {
                "meta": {"horizons": [63,126]},
                "assets": {name: {"weights": {"trend": 1.0}, "score_reliable": quality}},
            }
            assets[name]["conviction"]["calibration_evidence"] = calibration_evidence(name, calibration)
    context["vm"]["asset_reads"] = attach_asset_reads(
        context["vm"]["detail"],frames,context["assets"],config.load()["commodities"])
    return context


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--full-page",action="store_true",help="Capture the whole synthetic page with requested-viewport checks; requires R1")
    parser.add_argument("--include-calibration",action="store_true",help="Also prove parameter-source disclosures with explicit synthetic calibration")
    args=parser.parse_args(argv)
    scenarios=("split","incomplete","lagging") + (("calibration",) if args.include_calibration else ())
    output=args.output_dir.resolve()
    if output == ROOT or any(output == (ROOT/p).resolve() or (ROOT/p).resolve() in output.parents for p in ("data","site")):
        parser.error("evidence output must not target production data or site")
    output.mkdir(parents=True,exist_ok=False)
    fixture=output/"fixture"
    fixture.mkdir()
    owner.write_fixture_site(fixture)
    for scenario in scenarios:
        (fixture/(scenario+".html")).write_text(owner.render_page(fixture_context(scenario)))
    from scripts.capture_page_evidence import serve_site_dir
    from playwright.sync_api import sync_playwright
    httpd,port=serve_site_dir(fixture)
    pages=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            try:
                for scenario in scenarios:
                    states=[]
                    for viewport,(width,height) in owner.VIEWPORTS.items():
                        for locale in owner.LOCALES:
                            for theme in owner.THEMES:
                                context,page=owner._new_page(browser,width=width,height=height,locale=locale,theme=theme,touch=args.full_page and width==390)
                                context.route("**/*",lambda route:route.continue_() if route.request.url.startswith(f"http://127.0.0.1:{port}/") else route.abort())
                                errors=[]
                                page.on("pageerror",lambda error:errors.append(str(error)))
                                try:
                                    page.goto(f"http://127.0.0.1:{port}/{scenario}.html",wait_until="load")
                                    actual=page.evaluate(owner._APPLY_STATE_SCRIPT.strip(),{"theme":theme,"locale":locale})
                                    assert actual["theme"]==theme and actual["locale"]==locale
                                    geometry=page.locator(".asset-read-section").evaluate("e=>({left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right,viewport:innerWidth})")
                                    assert geometry["left"]>=0 and geometry["right"]<=width+1
                                    document_geometry = None
                                    if args.full_page:
                                        document_geometry = page.evaluate("({width:innerWidth,scroll:document.documentElement.scrollWidth})")
                                        document_geometry["viewport_width"] = width
                                        owner.assert_document_fits(document_geometry)
                                    labels={}
                                    evidence_states={}
                                    for asset in ("gold","silver","copper","oil"):
                                        card=page.locator(f'[data-asset-read="{asset}"]')
                                        labels[asset]=card.locator(".asset-read-title").inner_text().strip()
                                        card_evidence=card.locator("[data-model-evidence]")
                                        evidence_states[asset]=card_evidence.get_attribute("data-model-evidence")
                                        if scenario == "calibration":
                                            card_evidence.locator("summary").click()
                                        card.locator(".asset-read-open").click()
                                        detail=page.locator(f'.dpanel[data-detpanel="{asset}"]')
                                        assert detail.is_visible()
                                        assert detail.locator(".asset-read-title").inner_text().strip()==labels[asset]
                                        detail_evidence=detail.locator("[data-model-evidence]")
                                        assert detail_evidence.get_attribute("data-model-evidence")==evidence_states[asset]
                                        if scenario == "calibration":
                                            detail_evidence.locator("summary").click()
                                            assert detail_evidence.inner_text().strip()==card_evidence.inner_text().strip()
                                        if args.full_page:
                                            owner.assert_document_fits({**page.evaluate("({width:innerWidth,scroll:document.documentElement.scrollWidth})"),"viewport_width":width})
                                    section=page.locator(".asset-read-section")
                                    overlay = page.evaluate(owner._OVERLAY_PROBE.strip()) or []
                                    assert not overlay, "unexpected screenshot overlay"
                                    if args.full_page:
                                        page.locator('[data-asset-read="gold"] .asset-read-open').click()
                                        page.evaluate("window.scrollTo(0,0)")
                                        png=page.screenshot(full_page=True,animations="disabled")
                                    else:
                                        section.scroll_into_view_if_needed()
                                        png=section.screenshot(type="png")
                                    filename,digest,pw_,ph_=owner.content_address_png(png,output)
                                    states.append({"viewport":viewport,"viewport_width":width,"viewport_height":height,
                                        "locale":locale,"theme":theme,"access":"anonymous","force_state":None,
                                        "captured":True,"file":filename,"sha256":digest,"bytes":len(png),"width":pw_,"height":ph_,
                                        "applied_theme":theme,"applied_locale":locale,"overlay":overlay,"overlay_clean":True,
                                        "document_geometry":document_geometry,
                                        "subject_geometry":geometry,"detail_clicks_verified":4,"calibration_details_verified":4,"model_evidence_statuses":evidence_states,"page_errors":errors,"titles":labels})
                                    assert not errors
                                finally:
                                    context.close()
                    pages.append({"page_id":"commodities.html#r2-"+scenario,"route":"/"+scenario+".html",
                                  "registry_route":"/commodities.html","route_kind":"asset_read_fixture",
                                  "subject":"r2-"+scenario,"states":states,"metrics":{},"console_errors":[],"failed_responses":[],"gaps":[]})
            finally:
                browser.close()
    finally:
        httpd.shutdown()
    manifest={"schema":"mastermind.p0_evidence.v2","generated_at":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "tool":{"module_ref":"scripts/capture_commodity_asset_read_evidence.py","version":"r2-asset-read-calibration-v3",
                "capture_method":"Existing commodity renderer and Chromium helper; local fixtures, no external requests; semantic button clicks, no text entry."},
        "target":{"kind":"fixture_site_dir","site_dir":str(fixture),"base_url":None,"resolved_sha_or_none":None,"resolved_gitdir_or_none":None,"resolved_sha_source":"record exact source or candidate digests beside this manifest"},
        "axes":{"viewports":{k:list(v) for k,v in owner.VIEWPORTS.items()},"locales":list(owner.LOCALES),"themes":list(owner.THEMES),"access":["anonymous"],"subjects":[p["subject"] for p in pages],"force_states":[]},
        "selection":{"mode":"explicit_subjects","subjects":[p["subject"] for p in pages]},"aliases":{},"excluded":[],
        "outcome":"captured","totals":{"pages":len(pages),"states_attempted":sum(len(p["states"]) for p in pages),"states_captured":sum(len(p["states"]) for p in pages)},"pages":pages,
        "honesty":{"authority":("Whole-page synthetic fixture, not production" if args.full_page else "R2 component fixture evidence, not full-page or production acceptance"),
                   "full_page":args.full_page,"synthetic_calibration_scenario":args.include_calibration,
                   "page":"Synthetic model states and dated inputs. Existing commodity renderer stubs navigation and hydration. R1 remains an independent release prerequisite. Full-page geometry is certified only when full_page is true; navigation and external hydration are never certified by this fixture.",
                   "new_entry_permission":None,"numerical_policy_changes":False}}
    (output/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    count=sum(len(p["states"]) for p in pages)
    print(f"R2_CAPTURE {count} states; {4*count} summary-to-detail and calibration identities verified",flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
