"""Existing banner regression tests in Chromium, with synthetic in-memory feeds.

Not an authenticated production-page or publisher proof. Browser CI must run
this module without skips before release. The two Python contract suites do not
require Playwright. RISK_WARNING_CHROMIUM may select an installed test browser.
"""
from pathlib import Path
import json
import os
import shutil

import pytest

playwright = pytest.importorskip("playwright.sync_api", reason="browser release lane requires Playwright")
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def browser():
    with playwright.sync_playwright() as runtime:
        executable = os.environ.get("RISK_WARNING_CHROMIUM") or shutil.which("chromium")
        browser = runtime.chromium.launch(executable_path=executable, headless=True,
                                           args=["--no-sandbox"])
        yield browser
        browser.close()


def open_case(browser, *, reduced=True, width=1440, lang="en", theme="dark",
              risk=True, news=True, old_dismissed=False):
    context = browser.new_context(viewport={"width": width, "height": 800},
                                  reduced_motion="reduce" if reduced else "no-preference")
    page = context.new_page()
    page.set_default_timeout(1500)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    rr = {"schema": "rr_banner.v1", "asof": "2026-09-25", "alert": {
        "id": "rr-2026-09-25-risk-off", "asof": "2026-09-25", "score": 99,
        "headline_en": "EXTREME RISK-OFF — synthetic stress",
        "headline_zh": "极高风险——合成测试", "href": "macro.html",
        "reasons": [], "amplifiers": [], "ramp": [],
    } if risk else None}
    wh = {"alerts": [{"id": "synthetic-news", "title": "Synthetic news notice",
                      "title_zh": "合成新闻提醒", "expires_at": "2099-01-01T00:00:00Z"}] if news else []}
    html = (f'<!doctype html><html data-lang="{lang}" data-theme="{theme}">'
            '<head><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<style>body{margin:0;padding:20px;font:16px system-ui;background:#10131a;color:#e8edf5}'
            'html[data-theme="light"] body{background:#f5f6f8;color:#18202c}'
            'main{padding-top:50px;min-height:1600px}h1{font-size:24px}</style></head>'
            '<body><main><h1>Synthetic warning-delivery test</h1>'
            '<p>This is an isolated regression fixture, not a production dashboard or current market call.</p>'
            '</main></body></html>')

    # No navigation or external network: exercise the real source against an
    # offline DOM and explicit feed/storage test doubles. This does not qualify
    # publication, transport, source-origin freshness or authorization.
    page.set_content(html)
    page.evaluate("""feeds => {
        const saved = new Map();
        if (feeds.oldDismissed) saved.set('rrb_dismissed', 'rr-2026-09-25-risk-off');
        Object.defineProperty(window, 'localStorage', {configurable: true, value: {
            getItem: key => saved.has(key) ? saved.get(key) : null,
            setItem: (key, value) => saved.set(key, String(value)),
            removeItem: key => saved.delete(key)
        }});
        window.fetch = url => Promise.resolve({ok: true, json: () => Promise.resolve(
            String(url).endsWith('rr_banner.json') ? feeds.rr : feeds.wh)});
    }""", {"rr": rr, "wh": wh, "oldDismissed": old_dismissed})
    page.add_script_tag(content=(ROOT / "templates/wh_banner.js").read_text())
    page.locator(".whb").wait_for(state="attached")
    return context, page, errors


def test_severe_risk_is_visible_first_even_with_news_and_reduced_motion(browser):
    context, page, errors = open_case(browser)
    try:
        assert page.locator(".whb-face-rr.is-active").count() == 1
        assert page.locator(".whb-critical").count() == 1
        assert not errors
    finally:
        context.close()


def test_severe_risk_never_alternates_out_behind_news(browser):
    context, page, errors = open_case(browser, reduced=False)
    try:
        assert page.locator(".whb-face-rr.is-active").count() == 1
        assert page.locator(".whb").evaluate("bar => !bar._whbTimer")
        assert not errors
    finally:
        context.close()


def test_acknowledgement_does_not_remove_active_severe_warning(browser):
    context, page, errors = open_case(browser)
    try:
        page.locator(".whb-x").click()
        assert page.locator(".whb-critical").count() == 1
        assert page.locator(".whb-x").get_attribute("aria-pressed") == "true"
        assert page.evaluate("localStorage.getItem('rrb_dismissed')") is None
        assert not errors
    finally:
        context.close()


def test_old_dismissal_cannot_silence_a_still_published_severe_warning(browser):
    context, page, errors = open_case(browser, old_dismissed=True)
    try:
        assert page.locator(".whb-face-rr.is-active").count() == 1
        assert not errors
    finally:
        context.close()


def test_reduced_motion_disables_dot_animation_as_well_as_scrolling(browser):
    context, page, errors = open_case(browser, news=False)
    try:
        assert page.locator(".whb-dot").evaluate("dot => getComputedStyle(dot, '::after').animationName") == "none"
        assert page.locator(".whb-risk-view").evaluate("view => getComputedStyle(view).maskImage") == "none"
        assert not errors
    finally:
        context.close()


def test_legacy_warning_exposes_its_issue_date_without_claiming_current_verification(browser):
    context, page, errors = open_case(browser, news=False)
    try:
        assert "2026-09-25" in page.locator(".whb").inner_text()
        assert "Last issued" in page.locator(".whb").inner_text()
        assert not errors
    finally:
        context.close()


def test_news_only_dismissal_is_preserved(browser):
    context, page, errors = open_case(browser, risk=False)
    try:
        assert page.locator(".whb-face-wh.is-active").count() == 1
        page.locator(".whb-x").click()
        assert page.locator(".whb").count() == 0
        assert page.evaluate("localStorage.getItem('whb_dismissed')") == "synthetic-news"
        assert not errors
    finally:
        context.close()


@pytest.mark.parametrize("width", [390, 1440])
@pytest.mark.parametrize("lang", ["en", "zh"])
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_severe_notice_is_readable_accessible_and_width_bounded(browser, width, lang, theme):
    context, page, errors = open_case(browser, width=width, lang=lang, theme=theme)
    try:
        assert page.locator(".whb-face-rr.is-active").count() == 1
        assert page.locator(".whb-x").get_attribute("aria-label") == (
            "确认风险警告（保持显示）" if lang == "zh" else "Acknowledge risk warning (keep visible)")
        assert page.locator(".whb-x").bounding_box()["width"] >= 40
        bounds = page.locator(".whb").bounding_box()
        assert abs(bounds["x"]) <= 1 and abs(bounds["width"] - width) <= 1
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.locator(".whb-x").focus()
        assert page.locator(".whb-x").evaluate("button => getComputedStyle(button).outlineStyle") != "none"
        page.keyboard.press("Enter")
        assert page.locator(".whb-critical").count() == 1
        assert not errors
    finally:
        context.close()


def test_template_and_site_source_copy_are_identical():
    assert (ROOT / "templates/wh_banner.js").read_bytes() == (ROOT / "site/wh_banner.js").read_bytes()
