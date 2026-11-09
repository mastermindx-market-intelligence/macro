"""Browser proof for the full Jinja Macro workspace, using explicit fixture data."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

from scripts.capture_page_evidence import serve_site_dir
from tests.macro_workspace_browser_support import EVENT_NAMES, render_workspace, write_preview


@pytest.fixture(scope="module")
def site_url(tmp_path_factory):
    site = write_preview(tmp_path_factory.mktemp("macro-workspace"))
    for name, value in [("zero", 0), ("false", False), ("true", True),
                        ("negative", -1), ("over", 101), ("string", "35")]:
        (site / f"sentiment-{name}.html").write_text(render_workspace(fear_greed={"dial": value}))
    (site / "history-unavailable.html").write_text(render_workspace(ms_history=None))
    server, port = serve_site_dir(site)
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    server.server_close()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        instance = pw.chromium.launch()
        yield instance
        instance.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    context.add_init_script("localStorage.setItem('theme','light');localStorage.setItem('lang','en');")
    # A local, synthetic registered-reader fixture; no auth or real account is accessed.
    context.add_init_script("window.MMXAccessPreview={isAnon:()=>false};")
    view = context.new_page()
    errors = []
    view.on("pageerror", lambda error: errors.append(str(error)))
    yield view
    assert errors == [], errors
    context.close()


def capture_state(page, name):
    destination = os.environ.get("MACRO_WORKSPACE_SHOTS")
    if destination:
        directory = Path(destination)
        directory.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(directory / (name + ".png")), animations="disabled")


def load(page, site_url, route="macro.html"):
    page.goto(site_url + "/" + route)
    page.locator(".macro-section-links").wait_for()
    page.wait_for_timeout(150)


@pytest.mark.parametrize("width,theme,lang", [
    (1440, "light", "en"), (1440, "dark", "en"),
    (1440, "light", "zh"), (1440, "dark", "zh"),
    (390, "light", "en"), (390, "dark", "en"),
    (390, "light", "zh"), (390, "dark", "zh"),
    (768, "light", "en"), (320, "dark", "zh"),
])
def test_full_page_reading_order_and_fit(page, site_url, width, theme, lang):
    page.set_viewport_size({"width": width, "height": 900})
    page.add_init_script(f"localStorage.setItem('theme',{json.dumps(theme)});localStorage.setItem('lang',{json.dumps(lang)});")
    load(page, site_url)
    expect(page.locator("h1:visible")).to_have_count(1)
    assert page.locator("#macro-workspace h2:visible").count() == 6
    assert page.locator("#macro-workspace").evaluate(
        "(e)=>e.scrollWidth <= e.clientWidth + 1"
    )
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    ids = page.locator("#regime-radar,#sx-markets-v2,#macro-priorities,#macro-drivers,#macro-briefing,#sx-deep-context").evaluate_all("(els)=>els.map(e=>e.id)")
    assert ids == ["regime-radar", "sx-markets-v2", "macro-priorities", "macro-drivers", "macro-briefing", "sx-deep-context"]
    for en, zh in EVENT_NAMES:
        text = en if lang == "en" else zh
        expect(page.locator("#sx-events-v2 .mx5-tl-name").get_by_text(text, exact=True)).to_be_visible()
    assert page.locator("#sx-events-v2 .mx5-tl-date").evaluate_all(
        "(els)=>els.every(e=>getComputedStyle(e).whiteSpace==='nowrap')"
    )
    expect(page.locator(".macro-history-range")).to_be_visible()
    assert page.locator(".macro-history-readout").inner_text() == page.locator(".macro-history-range").get_attribute("aria-valuetext")
    assert page.locator(".macro-detail-button").count() == 9
    assert page.locator(".macro-detail-button").evaluate_all(
        "(els)=>els.every(e=>e.tagName==='BUTTON' && !e.parentElement.closest('[role=button]'))"
    )


def test_page_index_keeps_native_history_focus_and_location(page, site_url):
    load(page, site_url)
    nav = page.locator(".macro-section-links")
    nav.locator('[href="#macro-drivers"]').click()
    expect(page).to_have_url(site_url + "/macro.html#macro-drivers")
    expect(page.locator("#macro-drivers")).to_be_focused()
    expect(nav.locator('[href="#macro-drivers"]')).to_have_attribute("aria-current", "location")
    geometry = page.evaluate("""() => {
      const nav=document.querySelector('.macro-section-links').getBoundingClientRect();
      const section=document.querySelector('#macro-drivers').getBoundingClientRect();
      return {navTop:nav.top,navBottom:nav.bottom,sectionTop:section.top};
    }""")
    assert 0 <= geometry["navTop"] <= 12
    assert geometry["sectionTop"] > geometry["navBottom"]
    capture_state(page, "desktop-drivers-index")
    nav.locator('[href="#macro-briefing"]').click()
    expect(page.locator("#macro-briefing")).to_be_focused()
    capture_state(page, "desktop-briefing-index")
    page.go_back()
    expect(page).to_have_url(site_url + "/macro.html#macro-drivers")
    expect(nav.locator('[href="#macro-drivers"]')).to_have_attribute("aria-current", "location")
    page.locator("#macro-priorities").scroll_into_view_if_needed()
    page.evaluate("document.querySelector('#macro-priorities').scrollIntoView()")
    expect(nav.locator('[href="#macro-priorities"]')).to_have_attribute("aria-current", "location")
    assert page.url.endswith("#macro-drivers"), "passive indication must not write history"


def test_history_keyboard_live_replacement_and_recovery(page, site_url):
    load(page, site_url)
    control = page.locator(".macro-history-range")
    output = page.locator(".macro-history-readout")
    svg = page.locator(".mx5-sc-right .mx5-path-svg")
    original = json.loads(svg.get_attribute("data-points"))
    control.focus()
    control.press("Home")
    assert control.input_value() == "0"
    assert original[0]["md"] in output.inner_text()
    control.press("ArrowRight")
    selected = original[1]
    assert control.input_value() == "1"
    before_height = page.locator(".macro-history-heading").bounding_box()["height"]
    control.press("End")
    assert "36" in output.inner_text()
    control.press("Home")
    control.press("ArrowRight")
    # A new older point changes the ordinal; date retention must still choose the same reading.
    shifted = [dict(original[0], d="2026-08-14", md="Aug 14", mz="8月14日")] + original
    def live(rows):
        svg.evaluate("(el,rows)=>{el.setAttribute('data-points', JSON.stringify(rows));document.dispatchEvent(new Event('mx5pathlive'));}", rows)
    live(shifted)
    assert control.input_value() == "2"
    assert selected["md"] in output.inner_text()
    live([])
    expect(control).to_be_hidden()
    expect(page.locator(".mx5-sc-right")).to_be_focused()
    svg.hover()
    expect(page.locator(".mx5-path-tip")).not_to_have_class("mx5-path-tip show")
    page.evaluate("document.documentElement.setAttribute('data-lang','zh');document.dispatchEvent(new Event('langchange'));")
    live(shifted)
    expect(control).to_be_visible()
    assert control.input_value() == "2"
    assert selected["mz"] in output.inner_text()
    control.focus()
    control.press("End")
    latest = dict(original[-1], d="2026-11-09", md="Nov 9", mz="11月9日", s=40, live=True)
    live(shifted + [latest])
    assert control.input_value() == str(len(shifted))
    assert "盘中暂定" in output.inner_text()
    assert output.inner_text() == control.get_attribute("aria-valuetext")
    capture_state(page, "history-provisional-zh")
    control.press("Escape")
    assert "show" not in page.locator(".mx5-path-tip").get_attribute("class").split()
    assert page.locator(".macro-history-heading").bounding_box()["height"] == before_height


@pytest.mark.parametrize("dialog_id", [
    "dlg-markets", "dlg-evidence", "dlg-events", "dlg-fed",
    "dlg-sentiment", "dlg-sector", "dlg-policy", "dlg-aibrief", "dlg-news",
])
def test_native_detail_buttons_open_and_return_focus(page, site_url, dialog_id):
    load(page, site_url)
    button = page.locator(f'.macro-detail-button[aria-controls="{dialog_id}"]')
    button.click()
    dialog = page.locator("#" + dialog_id)
    expect(dialog).to_have_class(re.compile(r"\bopen\b"))
    page.keyboard.press("Escape")
    expect(dialog).not_to_have_class(re.compile(r"\bopen\b"))
    expect(button).to_be_focused()


def test_phone_driver_keyboard_focus_and_dialog_return(page, site_url):
    page.set_viewport_size({"width": 390, "height": 844})
    load(page, site_url)
    strip = page.locator(".macro-driver-grid")
    buttons = strip.locator(".macro-detail-button")
    buttons.nth(0).focus()
    buttons.nth(0).press("Tab")
    expect(buttons.nth(1)).to_be_focused()
    buttons.nth(1).press("Tab")
    expect(buttons.nth(2)).to_be_focused()
    box = buttons.nth(2).bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 390
    offset = strip.evaluate("(e)=>e.scrollLeft")
    buttons.nth(2).press("Enter")
    expect(page.locator("#dlg-sector")).to_have_class(re.compile(r"\bopen\b"))
    page.keyboard.press("Escape")
    expect(buttons.nth(2)).to_be_focused()
    assert abs(strip.evaluate("(e)=>e.scrollLeft") - offset) < 2
    expect(page.locator('.macro-section-links [href="#macro-drivers"]')).to_have_attribute("aria-current", "location")
    capture_state(page, "mobile-driver-dialog-return")


@pytest.mark.parametrize("name", ["false", "true", "negative", "over", "string"])
def test_invalid_sentiment_never_displays_neutral_or_zero(page, site_url, name):
    load(page, site_url, f"sentiment-{name}.html")
    expect(page.locator("#sx-v5-sentiment .mx5-sentiment-dial-wrap")).to_have_count(0)
    expect(page.locator("#sx-v5-sentiment .macro-card-unavailable")).to_be_visible()
    page.locator('.macro-detail-button[aria-controls="dlg-sentiment"]').click()
    expect(page.locator("#dlg-sentiment .sg-hero-num")).to_have_count(0)
    expect(page.locator("#dlg-sentiment .macro-card-unavailable")).to_be_visible()


def test_real_zero_sentiment_remains_a_reading(page, site_url):
    load(page, site_url, "sentiment-zero.html")
    expect(page.locator("#sx-v5-sentiment .mx5-sentiment-dial-wrap")).to_be_visible()
    page.locator('.macro-detail-button[aria-controls="dlg-sentiment"]').click()
    expect(page.locator("#dlg-sentiment .sg-hero-num")).to_have_text("0")


def test_unavailable_states_are_useful_and_do_not_fabricate_history(page, site_url):
    load(page, site_url, "unavailable.html")
    expect(page.locator("h1:visible")).to_have_count(1)
    expect(page.locator("#macro-outlook-title")).to_be_visible()
    assert "unavailable" in page.locator("#regime-radar").inner_text()
    expect(page.locator(".macro-history-range")).to_have_count(0)
    expect(page.locator("#sx-v5-sentiment .mx5-sentiment-dial-wrap")).to_have_count(0)
    load(page, site_url, "history-unavailable.html")
    assert "History is unavailable" in page.locator(".macro-history-empty").inner_text()
    assert "building" not in page.locator(".macro-history-empty").inner_text()


def test_server_rendered_workspace_still_reads_without_javascript(browser, site_url):
    context = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
    page = context.new_page()
    page.goto(site_url + "/macro.html")
    expect(page.locator("h1:visible")).to_be_visible()
    expect(page.locator("#regime-radar")).to_be_visible()
    expect(page.locator(".macro-history-control")).to_be_hidden()
    page.locator('.macro-section-links [href="#macro-drivers"]').click()
    expect(page).to_have_url(site_url + "/macro.html#macro-drivers")
    expect(page.locator("#macro-drivers")).to_be_in_viewport()
    context.close()


def test_phone_touch_history_and_native_detail_action(browser, site_url):
    context = browser.new_context(viewport={"width": 390, "height": 844},
                                  has_touch=True, is_mobile=True, reduced_motion="reduce")
    context.add_init_script("localStorage.setItem('theme','dark');localStorage.setItem('lang','en');window.MMXAccessPreview={isAnon:()=>false};")
    page = context.new_page()
    load(page, site_url)
    slider = page.locator(".macro-history-range")
    slider.scroll_into_view_if_needed()
    box = slider.bounding_box()
    page.touchscreen.tap(box["x"] + box["width"] * .45, box["y"] + box["height"] / 2)
    assert 0 < int(slider.input_value()) < int(slider.get_attribute("max"))
    assert page.locator(".macro-history-readout").inner_text() == slider.get_attribute("aria-valuetext")
    capture_state(page, "mobile-history-touch")
    button = page.locator('.macro-detail-button[aria-controls="dlg-events"]')
    button.tap()
    expect(page.locator("#dlg-events")).to_have_class(re.compile(r"\bopen\b"))
    page.locator("#dlg-events .mx5-dlg-close").tap()
    expect(button).to_be_focused()
    context.close()
