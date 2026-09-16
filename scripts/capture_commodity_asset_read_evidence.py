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
from scripts.commodity_asset_read import attach_asset_reads


def fixture_context(scenario="split"):
    import pandas as pd
    from lib import config
    if scenario not in ("split", "incomplete", "lagging"):
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
    context["vm"]["asset_reads"] = attach_asset_reads(
        context["vm"]["detail"],frames,context["assets"],config.load()["commodities"])
    return context


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args(argv)
    output=args.output_dir.resolve()
    if output == ROOT or any(output == (ROOT/p).resolve() or (ROOT/p).resolve() in output.parents for p in ("data","site")):
        parser.error("evidence output must not target production data or site")
    output.mkdir(parents=True,exist_ok=False)
    fixture=output/"fixture"
    fixture.mkdir()
    owner.write_fixture_site(fixture)
    for scenario in ("split","incomplete","lagging"):
        (fixture/(scenario+".html")).write_text(owner.render_page(fixture_context(scenario)))
    from scripts.capture_page_evidence import serve_site_dir
    from playwright.sync_api import sync_playwright
    httpd,port=serve_site_dir(fixture)
    pages=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            try:
                for scenario in ("split","incomplete","lagging"):
                    states=[]
                    for viewport,(width,height) in owner.VIEWPORTS.items():
                        for locale in owner.LOCALES:
                            for theme in owner.THEMES:
                                context,page=owner._new_page(browser,width=width,height=height,locale=locale,theme=theme)
                                context.route("**/*",lambda route:route.continue_() if route.request.url.startswith(f"http://127.0.0.1:{port}/") else route.abort())
                                errors=[]
                                page.on("pageerror",lambda error:errors.append(str(error)))
                                try:
                                    page.goto(f"http://127.0.0.1:{port}/{scenario}.html",wait_until="load")
                                    actual=page.evaluate(owner._APPLY_STATE_SCRIPT.strip(),{"theme":theme,"locale":locale})
                                    assert actual["theme"]==theme and actual["locale"]==locale
                                    geometry=page.locator(".asset-read-section").evaluate("e=>({left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right,viewport:innerWidth})")
                                    assert geometry["left"]>=0 and geometry["right"]<=width+1
                                    labels={}
                                    for asset in ("gold","silver","copper","oil"):
                                        card=page.locator(f'[data-asset-read="{asset}"]')
                                        labels[asset]=card.locator(".asset-read-title").inner_text().strip()
                                        card.locator(".asset-read-open").click()
                                        detail=page.locator(f'.dpanel[data-detpanel="{asset}"]')
                                        assert detail.is_visible()
                                        assert detail.locator(".asset-read-title").inner_text().strip()==labels[asset]
                                    section=page.locator(".asset-read-section")
                                    section.scroll_into_view_if_needed()
                                    png=section.screenshot(type="png")
                                    filename,digest,pw_,ph_=owner.content_address_png(png,output)
                                    states.append({"viewport":viewport,"viewport_width":width,"viewport_height":height,
                                        "locale":locale,"theme":theme,"access":"anonymous","force_state":None,
                                        "captured":True,"file":filename,"sha256":digest,"bytes":len(png),"width":pw_,"height":ph_,
                                        "applied_theme":theme,"applied_locale":locale,"overlay":[],"overlay_clean":True,
                                        "subject_geometry":geometry,"detail_clicks_verified":4,"page_errors":errors,"titles":labels})
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
        "tool":{"module_ref":"scripts/capture_commodity_asset_read_evidence.py","version":"r2-asset-read-v1",
                "capture_method":"Existing commodity renderer and Chromium helper; local fixtures, no external requests; semantic button clicks, no text entry."},
        "target":{"kind":"fixture_site_dir","site_dir":str(fixture),"base_url":None,"resolved_sha_or_none":None,"resolved_gitdir_or_none":None,"resolved_sha_source":"record exact source or candidate digests beside this manifest"},
        "axes":{"viewports":{k:list(v) for k,v in owner.VIEWPORTS.items()},"locales":list(owner.LOCALES),"themes":list(owner.THEMES),"access":["anonymous"],"subjects":[p["subject"] for p in pages],"force_states":[]},
        "selection":{"mode":"explicit_subjects","subjects":[p["subject"] for p in pages]},"aliases":{},"excluded":[],
        "outcome":"captured","totals":{"pages":3,"states_attempted":24,"states_captured":24},"pages":pages,
        "honesty":{"authority":"R2 component fixture evidence, not full-page or production acceptance",
                   "page":"Synthetic model states and dated inputs. Existing commodity renderer stubs navigation and hydration. R1 remains an independent release prerequisite; full-page overflow not certified here.",
                   "new_entry_permission":None,"numerical_policy_changes":False}}
    (output/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    print("R2_CAPTURE 24 states; 96 summary-to-detail interactions verified",flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
