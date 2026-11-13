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
    assert "MMXReleaseSurprise" in env.get_template("_release_surprise_confirmation.html.j2").render()


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    result = browser_proof(args.outdir)
    print(json.dumps({"checks": len(result["checks"]), "screenshots": len(result["screenshots"]), "page_errors": result["page_errors"]}))


if __name__ == "__main__":
    main()
