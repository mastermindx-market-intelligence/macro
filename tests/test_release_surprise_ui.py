"""Release Radar component browser proof over explicitly synthetic source data.

Run screenshots locally with:
  python -m tests.test_release_surprise_ui --outdir <evidence-directory>
The pure source assertions run in ordinary CI; browser proof needs an installed
Playwright runtime and a dedicated headless Chrome (never a logged-in profile).
"""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from engine.release_surprise_confirmation import authority

ROOT = Path(__file__).resolve().parents[1]


def evidence_fixture():
    now = datetime.now(timezone.utc)
    known = (now - timedelta(hours=1)).isoformat()
    return {"schema": "release_surprise_confirmation.v1", "asof": now.isoformat(),
            "status": "available_descriptive", "display_only": True, "authority": authority(),
            "reason_codes": [], "paired_period_count": 3,
            "latest_pairs": [
                {"pair_id": "cpi_headline_ppi_headline", "period": "2026-10", "known_at": known,
                 "quadrant": "cpi_hot_ppi_cold", "agreement": False, "freshness": "current",
                 "display_derived_allowed": True, "authority": authority()},
                {"pair_id": "cpi_core_ppi_headline", "period": "2026-10", "known_at": known,
                 "quadrant": "neutral_or_mixed_neutral", "agreement": None, "freshness": "current",
                 "display_derived_allowed": True, "authority": authority()},
            ]}


def test_radar_uses_existing_fetch_and_no_new_action_plane():
    script = (ROOT / "templates/release_surprise_confirmation.js").read_text()
    dashboard = (ROOT / "templates/dashboard.html.j2").read_text()
    assert 'include "_release_surprise_confirmation.html.j2"' in dashboard
    assert "window.MMXReleaseSurprise.render(" in dashboard
    for forbidden in ("fetch(", "setInterval(", "localStorage", "sessionStorage", ".innerHTML", "eval("):
        assert forbidden not in script
    assert "textContent" in script and "display_derived_allowed" in script
    partial = (ROOT / "templates/_release_surprise_confirmation.html.j2").read_text()
    assert '<details class="mx-disc">' in partial and "<summary>" in partial
    assert 'class="l-en"' in partial and 'class="l-zh"' in partial
    assert "not a trading signal" in partial


def test_component_compiles_in_native_template_loader():
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")))
    rendered = env.get_template("_release_surprise_confirmation.html.j2").render()
    assert "MMXReleaseSurprise" in rendered
    assert "consensus" not in rendered.lower()  # incumbent MRI-R5 display vocabulary


def test_confirmation_is_single_visible_dialog_child_not_offscreen_host():
    from bs4 import BeautifulSoup
    from tests.test_release_radar_render import _render
    page = BeautifulSoup(_render("macro"), "html.parser")
    comparisons = page.select("#rr-confirmation")
    assert len(comparisons) == 1
    assert comparisons[0].find_parent(id="dlg-events") is not None
    assert comparisons[0].find_parent(id="rr-content") is None
    dashboard = (ROOT / "templates/dashboard.html.j2").read_text()
    assert "snapshot once its visible comparison node exists" in dashboard
    assert "payload && payload.surprise_confirmation" in dashboard


def browser_proof(outdir: Path | None = None) -> dict:
    from jinja2 import Environment, FileSystemLoader
    from playwright.sync_api import sync_playwright

    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")))
    component = env.get_template("_release_surprise_confirmation.html.j2").render()
    theme = (ROOT / "templates/theme.css").read_text()
    html = ('<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<style>' + theme + '</style><style>'
            'body{margin:0;padding:20px;background:var(--bg);color:var(--text);font-family:var(--font-ui);}'
            'main{max-width:760px;margin:auto;} .panel{padding:20px;}'
            'html[data-lang="en"] .l-zh{display:none!important;}'
            'html[data-lang="zh"] .l-en{display:none!important;}'
            '</style></head><body class="page-macro"><main><section class="panel">'
            '<h2><span class="l-en">Release Radar</span><span class="l-zh">\u6570\u636e\u53d1\u5e03\u96f7\u8fbe</span></h2>'
            + component + '</section></main></body></html>')
    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)
    evidence, checks, screenshots = evidence_fixture(), [], []
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="chrome", headless=True)
        try:
            page = browser.new_page()
            page.route("**/*", lambda route: route.abort())
            errors = []
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            for theme_name in ("dark", "light"):
                for language in ("en", "zh"):
                    for width in (1280, 390):
                        page.set_viewport_size({"width": width, "height": 950})
                        page.set_content(html)
                        page.evaluate("([theme,lang]) => {document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang=lang;}", [theme_name, language])
                        page.evaluate("e => window.MMXReleaseSurprise.render(document.getElementById('rr-confirmation'),e)", evidence)
                        assert page.locator(".rr-confirmation-row").count() == 2
                        assert page.locator("#rr-confirmation").evaluate("n => n.scrollWidth <= n.clientWidth + 1")
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                        summary = page.locator("#rr-confirmation summary")
                        summary.focus()
                        summary.press("Enter")
                        assert page.locator("#rr-confirmation details").evaluate("n => n.open")
                        # Refresh must preserve investigation state and keyboard focus.
                        page.evaluate("e => window.MMXReleaseSurprise.render(document.getElementById('rr-confirmation'),e)", evidence)
                        assert page.locator("#rr-confirmation details").evaluate("n => n.open")
                        assert summary.evaluate("n => n === document.activeElement")
                        summary.press("Enter")
                        assert not page.locator("#rr-confirmation details").evaluate("n => n.open")
                        shot = f"macro-confirmation-{theme_name}-{language}-{width}.png"
                        if outdir:
                            page.locator("main").screenshot(path=str(outdir / shot))
                            screenshots.append(shot)
                        checks.append({"theme": theme_name, "language": language, "width": width,
                                       "no_horizontal_overflow": True, "keyboard_disclosure": True,
                                       "refresh_preserves_focus_and_disclosure": True})
            page.evaluate("document.documentElement.dataset.lang='en'")
            cases = [("missing", None, "unavailable"),
                     ("integrity", {**evidence, "status": "input_invalid", "latest_pairs": []}, "needs checking"),
                     ("stale", {**evidence, "asof": "2000-01-01T00:00:00Z"}, "fresh update"),
                     ("authority", {**evidence, "authority": {**authority(), "can_trade": True}}, "unavailable")]
            for name, data, expected in cases:
                page.evaluate("e => window.MMXReleaseSurprise.render(document.getElementById('rr-confirmation'),e)", data)
                assert expected in page.locator("[data-msc-state] .l-en").inner_text()
                assert page.locator(".rr-confirmation-row").count() == 0
                checks.append({"state": name, "refusal_visible": True})
            mixed = copy.deepcopy(evidence)
            mixed["latest_pairs"][1]["period"] = "2026-09"
            mixed["latest_pairs"][1]["freshness"] = "superseded_by_incomplete_period"
            page.evaluate("e => window.MMXReleaseSurprise.render(document.getElementById('rr-confirmation'),e)", mixed)
            assert "2026-09 (previous)" in page.locator(".rr-confirmation-row .l-en").all_inner_texts()[2]
            contradiction = copy.deepcopy(evidence)
            contradiction["latest_pairs"][0]["agreement"] = True
            page.evaluate("e => window.MMXReleaseSurprise.render(document.getElementById('rr-confirmation'),e)", contradiction)
            assert page.locator(".rr-confirmation-row").count() == 1
            injected = copy.deepcopy(evidence)
            injected["latest_pairs"][0]["period"] = '<img src=x onerror="window.__mscXss=1">'
            page.evaluate("e => window.MMXReleaseSurprise.render(document.getElementById('rr-confirmation'),e)", injected)
            assert page.locator("#rr-confirmation img").count() == 0
            assert page.evaluate("window.__mscXss || null") is None
            assert not errors, errors
        finally:
            browser.close()
    result = {"schema": "macro_surprise_component_browser_proof.v1", "evidence_class": "synthetic_ui_only",
              "scope": "actual_component_and_renderer_not_full_production_page", "checks": checks,
              "screenshots": screenshots, "page_errors": errors, "network_requests_allowed": False}
    if outdir:
        (outdir / "browser-proof.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def native_dialog_browser_proof(outdir: Path) -> dict:
    """Full rendered dashboard, local fixture routes; never live auth proof.

    The anonymous case retains the real access gate. The display case substitutes
    only its signed-in decision in this isolated fake origin, so it can exercise
    the real card click, dialog, MRI fetch and component without a credential.
    The authenticated API contract is tested separately in the API test suite.
    """
    import hashlib
    import mimetypes
    from urllib.parse import urlparse
    from playwright.sync_api import sync_playwright
    from tests.test_release_radar_render import _render

    outdir.mkdir(parents=True, exist_ok=True)
    html = _render("macro")
    evidence = evidence_fixture()
    payload = {"schema": "release_forecast.v2", "asof": evidence["asof"],
               "upcoming": [], "surprise_confirmation": evidence}
    errors, cases = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            for signed_in, width in ((False, 1280), (True, 1280), (True, 390)):
                requests = []
                page = browser.new_page(viewport={"width": width, "height": 1000})
                page.on("pageerror", lambda e: errors.append(str(e)))

                def route(request):
                    url = urlparse(request.request.url)
                    requests.append(url.path)
                    if url.hostname != "msc-native.test":
                        request.abort()
                        return
                    if url.path == "/":
                        request.fulfill(status=200, content_type="text/html", body=html)
                        return
                    if url.path == "/macrodata/release_forecast.json":
                        request.fulfill(status=200, content_type="application/json", body=json.dumps(payload))
                        return
                    for base in (ROOT / "templates", ROOT / "site"):
                        asset = (base / url.path.lstrip("/")).resolve()
                        if (asset.is_relative_to(base.resolve()) and asset.is_file()
                                and asset.suffix in {".css", ".js", ".svg", ".png", ".woff2"}):
                            request.fulfill(status=200, body=asset.read_bytes(), content_type=
                                mimetypes.guess_type(asset.name)[0] or "application/octet-stream")
                            return
                    request.fulfill(status=404, body="synthetic fixture resource unavailable")

                page.route("**/*", route)
                page.goto("http://msc-native.test/", wait_until="networkidle")
                assert not page.locator("#dlg-events").is_visible()
                if signed_in:
                    # Only the test origin gets a synthetic allowed decision.
                    # No production source, session, token or permission changes.
                    page.evaluate("window.MMXAccessPreview.isAnon = function(){return false;}")
                page.locator('[onclick="mx5OpenDlg(\'dlg-events\')"]').first.click()
                if not signed_in:
                    assert not page.locator("#dlg-events").is_visible()
                    page.locator("html.obm-lock").wait_for(state="attached", timeout=5000)
                    cases.append({"signed_in_decision_mocked": False, "width": width,
                                  "anonymous_gate_retained": True})
                    page.close()
                    continue
                comparison = page.locator("#rr-confirmation")
                # Native dialogs animate their panel/body. Geometry visibility
                # alone can screenshot a fully transparent transition frame.
                page.wait_for_function("""() => {
                    let node = document.getElementById('rr-confirmation');
                    if (!node || !document.querySelector('#dlg-events.mx5-dlg-in')) return false;
                    for (; node; node=node.parentElement) {
                        const style=getComputedStyle(node);
                        if (Number(style.opacity)<0.99 || style.display==='none' || style.visibility==='hidden') return false;
                    }
                    return true;
                }""", timeout=5000)
                comparison.scroll_into_view_if_needed()
                assert comparison.is_visible() and page.locator("#dlg-events").is_visible()
                assert "Consumer above; producer below" in comparison.inner_text()
                assert page.locator("#rr-confirmation").count() == 1
                assert requests.count("/macrodata/release_forecast.json") == 1
                summary = comparison.locator("summary")
                summary.focus()
                page.keyboard.press("Enter")
                assert comparison.locator("details").evaluate("node => node.open") is True
                dimensions = comparison.evaluate("""node => {
                    const r=node.getBoundingClientRect();
                    return {x:r.x,width:r.width,viewport:innerWidth,
                            client:node.clientWidth,scroll:node.scrollWidth};
                }""")
                assert dimensions["x"] >= -1
                assert dimensions["x"] + dimensions["width"] <= width + 1
                assert dimensions["scroll"] <= dimensions["client"] + 1
                filename = f"native-events-dialog-{width}.png"
                page.screenshot(path=str(outdir / filename), animations="disabled")
                cases.append({"signed_in_decision_mocked": True, "width": width,
                              "native_card_click": True, "visible": True,
                              "single_existing_mri_fetch": True, "keyboard_disclosure": True,
                              "dimensions": dimensions, "screenshot": filename})
                page.close()
        finally:
            browser.close()
    assert not errors, errors
    paths = ["templates/dashboard.html.j2", "templates/_release_surprise_confirmation.html.j2",
             "templates/release_surprise_confirmation.js", "tests/test_release_surprise_ui.py"]
    result = {"schema": "macro_surprise_native_dialog_proof.v1",
              "evidence_class": "synthetic_full_dashboard_ui",
              "live_authenticated_acceptance": False, "network_requests_allowed": False,
              "production_auth_modified": False, "cases": cases, "page_errors": errors,
              "input_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths}}
    (outdir / "native-dialog-proof.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--native-dialog", action="store_true")
    args = parser.parse_args()
    if args.native_dialog:
        result = native_dialog_browser_proof(args.outdir)
        print(json.dumps({"cases": len(result["cases"]), "page_errors": result["page_errors"],
                          "live_authenticated_acceptance": False}))
        return
    result = browser_proof(args.outdir)
    print(json.dumps({"checks": len(result["checks"]), "screenshots": len(result["screenshots"]), "page_errors": result["page_errors"]}))


if __name__ == "__main__":
    main()
