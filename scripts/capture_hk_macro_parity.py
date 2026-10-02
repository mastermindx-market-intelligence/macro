"""Real Chromium acceptance for #8112; frozen native inputs, no collectors.

Uses the existing p0_evidence.v2 visual manifest and ordinary assertions. The
native regime/market-state snapshots come from --source-ref; other VM fields
are explicit test fixtures, not a claimed production build. US and China are
the committed rendered references. Run from an isolated, site-enabled tree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import io
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.capture_page_evidence import serve_site_dir, parse_force_state, _apply_interaction_force
from scripts.capture_debt_maturity_evidence import content_address_png
from scripts.capture_hk_tier1_shell import _STATE_SEED_SCRIPT, _APPLY_STATE_SCRIPT
from tests.test_hk_tier1_shell import _render

OUT = ROOT / "mockups/evidence/hk-macro-parity-8112"
VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def prepare(ref, scratch):
    snapshots, inputs = {}, {}
    for name, path in (("latest", "data/hk_regime/latest.json"),
                       ("market_state", "data/hk_market_state/latest.json")):
        raw = subprocess.check_output(["git", "show", f"{ref}:{path}"], cwd=ROOT)
        snapshots[name] = json.loads(raw)
        inputs[path] = digest(raw)
    # Same field projection as build_hk._sector_cards, with cycle state absent:
    # this fixture does not compute or invent unavailable cycle analysis.
    sectors = [dict(name=r["ticker"], rank=r.get("rank"),
                    mom20=r.get("mom_20d_pct"), mom60=r.get("mom_60d_pct"),
                    above200=r.get("above_200d_trend"), dir=None)
               for r in snapshots["latest"]["sector_rs"]]
    scratch.mkdir(parents=True, exist_ok=True)
    from engine.hk_signal_stack import build_hk_signal_stack
    from engine.hk_tier1 import plain_flip_line
    ms = snapshots["market_state"]
    ms["flip_plain_en"], ms["flip_plain_zh"] = plain_flip_line(ms)
    import pandas as pd
    from scripts.build_hk import _ilx
    history_path = "data/hk_market_state/score_log.parquet"
    raw = subprocess.check_output(["git", "show", f"{ref}:{history_path}"], cwd=ROOT)
    inputs[history_path] = digest(raw)
    history = pd.read_parquet(io.BytesIO(raw)).sort_values("date").tail(11).to_dict(orient="records")
    native_chart = (snapshots["latest"].get("conditions") or {}).get("charts", {}).get("fear_euphoria")
    if native_chart:
        snapshots["latest"]["fear_euphoria"]["chart_html"] = _ilx(
            native_chart, "var(--info)", height=160, aria_en="Fear to euphoria sentiment")
    # Explicit layout exemplars exercise every inherited table, including long
    # names. These are fixture rows, never represented as current observations.
    index_health = [dict(ticker=ticker, label=en, label_zh=zh, price=price, chg=change,
                         dd=-8.5, rsi=48, above50=True, dist200=2.1)
        for ticker, en, zh, price, change in (
            ("^HSI", "Hang Seng", "恒生指数", 25000, 0.2),
            ("^HSCE", "Hang Seng China Enterprises", "恒生中国企业指数", 8800, -0.1),
            ("^HSCC", "Hong Kong technology index", "香港科技指数", 5600, 0),
            ("000001.SS", "Shanghai", "上证指数", 3800, 0.5))]
    tables = dict(index_health=index_health,
        adr_bridge=dict(composite=dict(bellwether_implied_open_pct=0.4), names=[
            dict(hk_name_en="Alibaba Group Holding — long-name layout fixture", hk_name_zh="阿里巴巴集团控股有限公司 — 长名称排版样本", implied_open_gap_pct=0.4),
            dict(hk_name_en="Tencent", hk_name_zh="腾讯", implied_open_gap_pct=-0.2)]),
        event_strip=[dict(name_en="Hong Kong employment and labour market release", name_zh="香港就业及劳动力市场数据公布", md="09-30", importance="high")],
        catalyst_strip=[dict(name_en="Stock Connect and international index review", name_zh="互联互通及国际指数审议", date="2026-09-30")],
        breadth=dict(pct_above_50=55), full_breadth=dict(adv=123, dec=456, n_members=789, asof="2026-09-25"))
    html = _render(**snapshots, sectors=sectors, ms_history=history, **tables,
                   signal_stack=build_hk_signal_stack(snapshots["latest"]))
    (scratch / "hk.html").write_text(html)
    (scratch / "hk-unavailable.html").write_text(_render(
        latest={}, market_state={}, sectors=[], vhsi=None))
    for asset in (ROOT / "site").iterdir():
        target = scratch / asset.name
        if not target.exists():
            target.symlink_to(asset, target_is_directory=asset.is_dir())
    return {"source_ref": ref, "inputs": inputs, "rendered_html_sha256": digest(html.encode()),
            "construction_inputs": {str(p.relative_to(ROOT)): digest(p.read_bytes())
                for p in [ROOT / "templates/hk.html.j2", Path(__file__),
                          ROOT / "tests/test_hk_tier1_shell.py"]},
            "source_dates": {"regime": snapshots["latest"].get("date"),
                             "market_state": snapshots["market_state"].get("asof")}}


def shot(page, selector, state, out):
    # Capture the shared search's real reduced-motion idle state, not an
    # arbitrary frame of its JS typewriter. Interactions run with motion on.
    page.emulate_media(reduced_motion="reduce")
    page.wait_for_timeout(1400)
    idle = page.locator(".idle-ticker").first
    idle_text = idle.text_content() if idle.count() else None
    search = page.locator(".ticker-input")
    assert all(not value for value in search.evaluate_all("es=>es.map(e=>e.value)")), "unexpected search input"
    # Fixed overlays must be captured at the actual viewport. Enlarging the
    # viewport for an element screenshot exposes the page below a scrollport.
    png = (page.screenshot(type="png", animations="disabled") if "dlg-panel" in selector
           else page.locator(selector).first.screenshot(type="png", animations="disabled"))
    name, sha, width, height = content_address_png(png, out)
    page.emulate_media(reduced_motion="no-preference")
    return dict(state, captured=True, file=name, sha256=sha, bytes=len(png),
                width=width, height=height,
                capture_reduced_motion=True, idle_ticker=idle_text, search_value="",
                applied_theme=page.locator("html").get_attribute("data-theme"),
                applied_locale=page.locator("html").get_attribute("data-lang"))


def panel_visibility(dlg):
    """Check visible panel corners, centre and close control, not just centre."""
    return dlg.locator(".hkx-dlg-panel").evaluate("""p=>{
        const r=p.getBoundingClientRect(),left=Math.max(0,r.left)+20,right=Math.min(innerWidth,r.right)-20;
        const top=Math.max(0,r.top)+20,bottom=Math.min(innerHeight,r.bottom)-20;
        const close=p.querySelector('.hkx-dlg-close').getBoundingClientRect();
        const points=[[left,top],[right,top],[left,bottom],[right,bottom],[(left+right)/2,(top+bottom)/2],
                      [close.x+close.width/2,close.y+close.height/2]];
        return points.filter(([x,y])=>x>=0&&x<innerWidth&&y>=0&&y<innerHeight).map(([x,y])=>{
            const hit=document.elementFromPoint(x,y);return {x,y,inside:p.contains(hit)};
        });
    }""")


def show(page, url, theme, locale):
    page.emulate_media(reduced_motion="no-preference")
    response = page.goto(url, wait_until="load")
    assert response and response.ok
    page.evaluate(_APPLY_STATE_SCRIPT, {"theme": theme, "locale": locale})
    page.wait_for_timeout(1300)  # let the existing theme/ink transitions finish


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--quick", action="store_true", help="one diagnostic cell; never a complete evidence receipt")
    args = parser.parse_args()
    ref = subprocess.check_output(["git", "rev-parse", args.source_ref], cwd=ROOT, text=True).strip()
    provenance = prepare(ref, args.scratch.resolve())
    OUT.mkdir(parents=True, exist_ok=True)
    httpd, port = serve_site_dir(args.scratch.resolve())
    base = f"http://127.0.0.1:{port}"
    pages, checks, failures = {}, [], []

    def capture(page, key, selector, state, route="/hk.html"):
        record = pages.setdefault(key, dict(page_id=key, route=route, registry_route=route,
            selector=selector, states=[], metrics={}, console_errors=[], failed_responses=[], gaps=[]))
        record["states"].append(shot(page, selector, state, OUT))

    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            for viewport, (width, height) in VIEWPORTS.items():
                for locale in ("en", "zh"):
                    for theme in ("dark", "light"):
                        if args.quick and (viewport, locale, theme) != ("desktop", "en", "dark"):
                            continue
                        state = dict(viewport=viewport, viewport_width=width, viewport_height=height,
                                     locale=locale, theme=theme, access="anonymous", force_state=None)
                        ctx = browser.new_context(viewport={"width": width, "height": height},
                            color_scheme=theme, locale="zh-CN" if locale == "zh" else "en-US",
                            has_touch=viewport == "mobile", is_mobile=viewport == "mobile")
                        ctx.add_init_script(f"({_STATE_SEED_SCRIPT})({json.dumps(state)})")
                        page = ctx.new_page()
                        exceptions = []
                        page.on("pageerror", lambda e: exceptions.append(str(e)))
                        try:
                            show(page, base + "/hk.html", theme, locale)
                            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), "horizontal page overflow"
                            capture(page, "hk-overview", "body", state)
                            inert_before = page.locator("[inert]").count()
                            ids = page.locator(".hkx-dlg").evaluate_all("els=>els.map(e=>e.id)")
                            assert len(ids) == 15, ids
                            assert page.locator("table.hkx-mt").count() == 5, "all five tables must be populated"
                            for index, panel_id in enumerate(ids):
                                is_read = panel_id in ("hkx-dlg-read", "hkx-dlg-risk")
                                popup = "hkx-pop-signals" if panel_id == "hkx-dlg-read" else "hkx-pop-risk"
                                if is_read:
                                    trigger = page.locator(f'[aria-controls="{popup}"]')
                                    trigger.click()
                                    assert trigger.get_attribute("aria-expanded") == "true"
                                    geometry = page.locator("#"+popup).evaluate("e=>({left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right})")
                                    assert geometry["left"] >= 0 and geometry["right"] <= width, "popup viewport containment"
                                    if panel_id == "hkx-dlg-risk" and viewport == "desktop":
                                        position = trigger.bounding_box()
                                        assert geometry["left"] >= position["x"] - 1, "risk popup trigger anchoring"
                                candidates = page.locator(f'[onclick*="hkxOpenDlg(\'{panel_id}\'"]')
                                opener = next(candidates.nth(i) for i in range(candidates.count()) if candidates.nth(i).is_visible())
                                if not is_read:
                                    trigger = opener
                                if viewport == "mobile":
                                    opener.tap()
                                else:
                                    opener.focus()
                                    page.keyboard.press("Enter" if index % 2 else "Space")
                                dlg = page.locator("#" + panel_id)
                                dlg.wait_for(state="visible")
                                page.wait_for_timeout(450)
                                assert dlg.get_attribute("role") == "dialog", panel_id + " role"
                                assert dlg.get_attribute("aria-modal") == "true"
                                assert dlg.evaluate("d=>d.contains(document.activeElement)"), panel_id + " entry focus"
                                assert page.evaluate("document.body.style.overflow==='hidden'"), panel_id + " scroll lock"
                                # Explicit positive control: this selector must really
                                # open the shared tooltip before dismissal is evidence.
                                lens_control = None
                                if panel_id == "hkx-dlg-risk":
                                    help_trigger = dlg.locator("span.help.help-upgraded").first
                                    assert help_trigger.count(), "risk help trigger exists"
                                    help_trigger.focus()
                                    page.locator(".lens-pop.open").wait_for(state="visible")
                                    dlg.locator(".hkx-dlg-close").focus()
                                    page.wait_for_function("!document.querySelector('.lens-pop.open')")
                                    lens_control = dict(opened=True, dismissed=True, trigger="span.help.help-upgraded")
                                # Reverse wrap from the close button, then forward wrap.
                                page.keyboard.press("Shift+Tab")
                                assert dlg.evaluate("d=>d.contains(document.activeElement)"), panel_id + " reverse trap"
                                page.keyboard.press("Tab")
                                assert dlg.evaluate("d=>d.contains(document.activeElement)"), panel_id + " forward trap"
                                scroll = dlg.evaluate("""d=>[d,d.querySelector('.hkx-dlg-panel')].map(e=>{
                                    const row={height:e.clientHeight,total:e.scrollHeight,overflow:getComputedStyle(e).overflowY};
                                    e.scrollTop=e.scrollHeight;row.reached=e.scrollTop;e.scrollTop=0;return row;
                                })""")
                                for area in scroll:
                                    if area["overflow"] in ("auto", "scroll") and area["total"] > area["height"]:
                                        assert area["reached"] > 0, panel_id + " scroll reachability"
                                table_metrics = dlg.locator(".hkx-table-scroll").evaluate_all("""els=>els.map(e=>({
                                    width:e.clientWidth, content:e.scrollWidth, table:getComputedStyle(e.querySelector('table')).display,
                                    contained:e.getBoundingClientRect().right<=innerWidth+1
                                }))""")
                                assert all(t["table"] == "table" and t["contained"] for t in table_metrics), panel_id + " table containment"
                                details = dlg.locator("details summary").first
                                if details.count():
                                    details.click()
                                    assert details.evaluate("e=>e.parentElement.open"), panel_id + " disclosure"
                                    details.click()
                                gauge_detail = dlg.locator(".hkx-fe-leg > summary").first
                                if gauge_detail.count():
                                    gauge_detail.click()
                                    assert gauge_detail.evaluate("e=>e.parentElement.open"), "native gauge disclosure"
                                    gauge_detail.click()
                                dlg.evaluate("d=>{d.scrollTop=0;d.querySelector('.hkx-dlg-panel').scrollTop=0;}")
                                # Focus traversal can disclose the shared LENS help sheet.
                                # Return to the close control and leave the help trigger;
                                # wait for its ordinary focusout/pointerleave dismissal.
                                # A covered modal is not acceptable visual evidence.
                                dlg.locator(".hkx-dlg-close").focus()
                                page.mouse.move(0, 0)
                                page.wait_for_function("!document.querySelector('.lens-pop.open')")
                                page.wait_for_timeout(250)
                                assert dlg.evaluate("d=>d.contains(document.activeElement)"), "capture focus owner"
                                points = panel_visibility(dlg)
                                assert len(points) >= 5 and all(p["inside"] for p in points), panel_id + " panel perimeter"
                                chrome = page.evaluate("""()=>({
                                    wrapper_z:Number(getComputedStyle(document.querySelector('.hkx-wrap')).zIndex),
                                    search_z:Number(getComputedStyle(document.querySelector('.nav-search')).zIndex),
                                    search_inert:!!document.querySelector('.nav-search').closest('[inert]'),
                                    search_value:document.querySelector('.ticker-input').value,
                                    launchers:[...document.querySelectorAll('#mmb-boot,#mmb-launch')].map(e=>({
                                        id:e.id,visibility:getComputedStyle(e).visibility,inert:!!e.closest('[inert]')}))
                                })""")
                                assert chrome["wrapper_z"] > chrome["search_z"] and chrome["search_inert"] and not chrome["search_value"]
                                assert chrome["launchers"] and all(x["visibility"] == "hidden" and x["inert"] for x in chrome["launchers"])
                                sector_colors = None
                                if panel_id == "hkx-dlg-sector":
                                    sector_colors = dlg.locator('table[data-research-table="sectors"] td.hkx-up,table[data-research-table="sectors"] td.hkx-dn').evaluate_all("es=>es.map(e=>({sign:e.classList.contains('hkx-up')?'up':'down',color:getComputedStyle(e).color}))")
                                    assert len({x["color"] for x in sector_colors}) == 2, "signed sector values have distinct computed colours"
                                capture(page, panel_id, "#" + panel_id + " .hkx-dlg-panel", state)
                                charts = dlg.locator(".ilx")
                                assert charts.evaluate_all("els=>els.every(e=>e.classList.contains('ilx-in'))"), panel_id + " chart reveal"
                                if panel_id == "hkx-dlg-markets" and viewport == "desktop":
                                    expand = page.locator("#hk-hm-embed .hm-sc-exp")
                                    expand.click()
                                    nested = page.locator(".hm-ov.open")
                                    nested.wait_for()
                                    assert nested.evaluate("d=>d.contains(document.activeElement)"), "nested heatmap entry focus"
                                    page.keyboard.press("Shift+Tab")
                                    assert nested.evaluate("d=>d.contains(document.activeElement)"), "nested heatmap trap"
                                    page.keyboard.press("Escape")
                                    page.locator(".hm-ov").wait_for(state="detached")
                                    assert dlg.is_visible(), "nested Escape must preserve parent"
                                    assert page.evaluate("document.body.style.overflow==='hidden'"), "parent lock after nested close"
                                    assert expand.evaluate("e=>e===document.activeElement"), "nested heatmap focus return"
                                    checks.append(dict(state, nested_heatmap=True, focus_trap=True, focus_return=True, parent_lock=True))
                                if index % 3 == 0:
                                    page.keyboard.press("Escape")
                                elif index % 3 == 1:
                                    dlg.locator(".hkx-dlg-close").click()
                                else:
                                    dlg.locator(".hkx-dlg-backdrop").click(position={"x": 2, "y": 2})
                                dlg.wait_for(state="hidden")
                                assert trigger.evaluate("e=>e===document.activeElement"), panel_id + " return focus"
                                assert page.evaluate("document.body.style.overflow!== 'hidden'"), panel_id + " unlock"
                                assert page.locator("[inert]").count() == inert_before, panel_id + " inert cleanup"
                                assert page.locator("#mmb-boot").is_visible(), "copilot restored after close"
                                checks.append(dict(state, panel=panel_id, opened_by="tap" if viewport == "mobile" else "keyboard",
                                                   entry_focus=True, focus_trap=True, focus_return=True, scroll=scroll, tables=table_metrics,
                                                   capture_focus_inside=True, lens_absent=True, lens_positive_control=lens_control,
                                                   panel_probe=points, chrome=chrome, copilot_restored=True, sector_colors=sector_colors))
                            # Popup focus/Escape and concrete hover/focus states in both themes.
                            pop_trigger = page.locator('[aria-controls="hkx-pop-signals"]')
                            pop_trigger.click()
                            threshold = page.locator("#hkx-pop-signals details summary")
                            if threshold.count():
                                threshold.click()
                            page.keyboard.press("Escape")
                            assert pop_trigger.get_attribute("aria-expanded") == "false"
                            assert pop_trigger.evaluate("e=>e===document.activeElement")
                            if viewport == "desktop" and locale == "en":
                                for force in ("hover", "focus"):
                                    if force == "focus": page.mouse.move(0, 0)
                                    applied = _apply_interaction_force(page, parse_force_state(f"btn-{force}:{force}(.hkx-hbtn)"))
                                    assert applied == "btn-" + force
                                    page.wait_for_function("!document.querySelector('.lens-pop.open')")
                                    hero_clear = page.locator('.hkx-hbtn').first.evaluate("""e=>{const r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}""")
                                    assert hero_clear, "hero force-state unobscured"
                                    checks.append(dict(state, force_state=applied, hero_unobscured=True, lens_absent=True))
                                    capture(page, "hk-overview", "body", dict(state, force_state=applied, applied_force_state=applied))
                            assert not exceptions, exceptions
                            for route, key in (("/macro.html", "us-reference"), ("/china.html", "china-reference")):
                                show(page, base + route, theme, locale)
                                capture(page, key, "body", state, route)
                            print(f"PASS {viewport}/{locale}/{theme}: 15 panels + US/China reference", flush=True)
                        except Exception as exc:
                            traceback.print_exc()
                            failures.append(dict(state, reason=str(exc), exceptions=exceptions))
                            page.screenshot(path=str(OUT / f"failure-{viewport}-{locale}-{theme}.png"))
                            print(f"FAIL {viewport}/{locale}/{theme}: {exc}", flush=True)
                        finally:
                            ctx.close()
            # Narrow-phone/tablet and reduced-motion/rapid reopen regression.
            for width in (320, 430, 768):
                for theme in ("dark", "light"):
                    ctx = browser.new_context(viewport={"width": width, "height": 900}, reduced_motion="reduce")
                    page = ctx.new_page()
                    try:
                        show(page, base + "/hk.html", theme, "zh")
                        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), "stress page overflow"
                        trigger = page.locator("#hkx-sentiment")
                        trigger.click()
                        page.keyboard.press("Escape")
                        # Exercise the same controller's transition cancellation, not an alternate opener.
                        page.evaluate("hkxOpenDlg('hkx-dlg-sentiment',document.querySelector('#hkx-sentiment'))")
                        page.wait_for_timeout(450)
                        assert page.locator("#hkx-dlg-sentiment").is_visible()
                        assert page.evaluate("document.body.style.overflow==='hidden'")
                        assert page.locator("#hkx-dlg-sentiment .ilx").evaluate_all("els=>els.every(e=>e.classList.contains('ilx-in'))")
                        page.locator("#hkx-dlg-sentiment .hkx-dlg-close").click()
                        page.locator("#hkx-dlg-sentiment").wait_for(state="hidden")
                        assert trigger.evaluate("e=>e===document.activeElement")
                        checks.append(dict(stress_width=width, theme=theme, locale="zh", reduced_motion=True, rapid_reopen=True))
                        show(page, base + "/hk-unavailable.html", theme, "zh")
                        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
                        assert "unavailable" in page.locator("#hkx-sentiment").text_content().lower()
                    except Exception as exc:
                        failures.append(dict(stress_width=width, theme=theme, reason=str(exc)))
                    finally:
                        ctx.close()
            browser.close()
    finally:
        httpd.shutdown()
    manifest = dict(schema="mastermind.p0_evidence.v2", generated_at=datetime.now(timezone.utc).isoformat(),
        tool=dict(module_ref="scripts/capture_hk_macro_parity.py", module_sha256=digest(Path(__file__).read_bytes())),
        target=dict(kind="fixture_render", **provenance),
        axes=dict(viewports={k:list(v) for k,v in VIEWPORTS.items()}, locales=["en","zh"], themes=["dark","light"], access=["anonymous"],
                  force_states=[parse_force_state(f"btn-{kind}:{kind}(.hkx-hbtn)").as_payload() for kind in ("hover", "focus")]),
        honesty=dict(page="Frozen native regime/market-state and sector RS plus ordinary test VM; remaining data are fixtures or unavailable. US/China are committed site references. Not a canonical build or production receipt."),
        outcome="captured" if not failures and not args.quick else "partial", pages=list(pages.values()))
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+"\n")
    (OUT / "interactions.json").write_text(json.dumps(dict(pass_all=not failures, checks=checks, failures=failures), indent=2)+"\n")
    (OUT / "EVIDENCE.yml").write_text("schema: mastermind.page_evidence_receipt.v1\nchanged_paths:\n  - templates/hk.html.j2\nmanifest: mockups/evidence/hk-macro-parity-8112/manifest.json\n")
    print(f"{len(checks)} interaction cases; {len(failures)} failures", flush=True)
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
