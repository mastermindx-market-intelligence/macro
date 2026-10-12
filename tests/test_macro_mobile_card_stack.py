"""Responsive regression for the Macro AI Brief / Alerts Centre grid cards.

The tablet ID rules once outranked the <=700px .sx full-width rule, leaving
two unreadable half-width columns on iPhone-sized screens.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _rack_css() -> str:
    template = (ROOT / "templates" / "dashboard.html.j2").read_text()
    match = re.search(r'<style id="mx4-css">(.*?)</style>', template, re.S)
    assert match, "Macro rack styles must exist in the page template"
    return match.group(1)


def test_mobile_span_cannot_be_overridden_by_tablet_card_ids() -> None:
    css = _rack_css()
    tablet = re.search(r"@media\(max-width:1099px\)\{(.*?)\n\}", css, re.S)
    mobile = re.search(r"@media\(max-width:700px\)\{(.*?)\n\}", css, re.S)
    assert tablet and mobile
    assert "body.page-macro.mx4-grid .sx{grid-column:span 6;}" in tablet.group(1)
    assert "body.page-macro.mx4-grid .sx," in mobile.group(1)
    assert "grid-column:span 12;" in mobile.group(1)
    # These more-specific tablet selectors must not reintroduce the bug.
    assert "#sx-news-v2{grid-column:span 6;}" not in tablet.group(1)
    assert "#sx-aibrief-v2{grid-column:span 6;}" not in tablet.group(1)


def test_ai_brief_and_alerts_card_geometry_across_breakpoints() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    css = _rack_css()
    html = (
        '<!doctype html><html><head>'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<style>body{margin:8px}.sx{min-width:0;box-sizing:border-box}</style>'
        f'<style>{css}</style></head>'
        '<body class="page-macro mx4-grid"><div class="mx4-rack">'
        '<section class="sx" id="sx-aibrief-v2">'
        '<div class="sxg-face">AI Brief QQQ USO NVDA XLF: 5 high-impact items.</div>'
        '</section><section class="sx" id="sx-news-v2">'
        '<div class="sxg-face">Alerts Centre: major event on deck.</div>'
        '</section></div></body></html>'
    )
    from playwright.sync_api import Error, sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Error as exc:
            pytest.skip(f"Chromium is not installed for this optional visual test: {exc}")
        try:
            page = browser.new_page()
            page.set_content(html)
            for width in (320, 375, 390, 430, 700, 701, 768, 1024, 1200):
                page.set_viewport_size({"width": width, "height": 900})
                bounds = page.evaluate("""() => {
                    const rect = sel => {
                      const r = document.querySelector(sel).getBoundingClientRect();
                      return {x:r.x, y:r.y, width:r.width, height:r.height};
                    };
                    return {
                      rack: rect('.mx4-rack'),
                      brief: rect('#sx-aibrief-v2'),
                      alerts: rect('#sx-news-v2'),
                      overflow: document.documentElement.scrollWidth > innerWidth + 1
                    };
                }""")
                rack, brief, alerts = (
                    bounds["rack"], bounds["brief"], bounds["alerts"]
                )
                assert not bounds["overflow"], (width, bounds)
                if width <= 700:
                    assert brief["width"] >= rack["width"] - 2, (width, bounds)
                    assert alerts["width"] >= rack["width"] - 2, (width, bounds)
                    assert alerts["y"] >= brief["y"] + brief["height"] - 1, (
                        width, bounds
                    )
                elif width < 1100:
                    assert abs(brief["y"] - alerts["y"]) <= 1, (width, bounds)
                    assert brief["width"] < rack["width"] * 0.6
                    assert alerts["width"] < rack["width"] * 0.6
        finally:
            browser.close()
