"""Browser behavior and geometry of the shipping search and Macro panel owners.

Synthetic, offline fixtures only. MM_REQUIRE_BROWSER=1 makes missing browser
dependencies a failure in the existing CI catalog. Baseline runs can supply
MMX_POLISH_SOURCE_ROOT containing the original template bytes.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from urllib.parse import urlsplit
import os

import pytest

if os.environ.get("MM_REQUIRE_BROWSER") == "1":
    from playwright.sync_api import sync_playwright, expect
else:
    pw = pytest.importorskip("playwright.sync_api")
    sync_playwright, expect = pw.sync_playwright, pw.expect

from tests.macro_polish_browser_support import ROOT, assets, rows


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as owner:
        instance = owner.chromium.launch(headless=True)
        yield instance
        instance.close()


class Fixture:
    def __init__(self, browser, *, case="ready", width=1440, height=900,
                 theme="dark", lang="en", motion="no-preference", touch=False):
        self.context = browser.new_context(
            viewport={"width": width, "height": height},
            reduced_motion=motion, has_touch=touch, is_mobile=touch,
        )
        self.assets = assets()
        self.case, self.calls, self.held, self.errors = case, Counter(), [], []
        self.context.route("**/*", self.route)
        self.page = self.context.new_page()
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.goto("http://macro.test/macro.html", wait_until="domcontentloaded")
        self.page.evaluate("([theme,lang])=>{setTheme(theme);setLang(lang)}", [theme, lang])
        expect(self.page.locator(".search-trigger")).to_be_visible()

    def route(self, route):
        url = urlsplit(route.request.url)
        if url.hostname != "macro.test":
            route.abort()
            return
        path = url.path.lstrip("/")
        if path.endswith("/index.json"):
            market = {"stockdata": "us", "chinastockdata": "cn",
                      "hkstockdata": "hk", "canadastockdata": "ca",
                      "intlstockdata": "intl"}[path.split("/")[0]]
            self.calls[market] += 1
            if self.case == "delayed" and market == "intl":
                self.held.append(route)
                return
            if self.case == "retry" and self.calls[market] <= 2:
                route.fulfill(status=503, content_type="application/json", body="{}")
                return
            route.fulfill(content_type="application/json", body=json.dumps(rows(market)))
        elif path in self.assets:
            body, mime = self.assets[path]
            route.fulfill(content_type=mime, body=body)
        elif path.startswith("fonts/") and (ROOT / "templates" / path).is_file():
            route.fulfill(path=ROOT / "templates" / path)
        else:
            route.fulfill(status=404, body="offline fixture: asset unavailable")

    def search(self, value="a"):
        self.page.locator(".search-trigger").click()
        field = self.page.locator(".ticker-input")
        expect(field).to_be_focused()
        field.fill(value)
        return field

    def ready(self):
        self.search()
        expect(self.page.locator("[data-result-index]")).to_have_count(8)

    def close(self):
        self.context.close()


@pytest.fixture
def make(browser):
    opened = []

    def create(**kwargs):
        instance = Fixture(browser, **kwargs)
        opened.append(instance)
        return instance

    yield create
    for instance in opened:
        instance.close()


def test_search_page_buttons_enter_space_and_focus(make):
    f = make()
    f.ready()
    page2 = f.page.get_by_role("button", name="Results page 2", exact=True)
    page2.press("Enter")
    expect(f.page.locator("[data-result-index]").first).to_have_attribute("aria-label", "Open A009 in Terminal")
    expect(f.page.locator(".search-trigger")).to_have_attribute("aria-expanded", "true")
    expect(page2).to_be_focused()
    expect(page2).to_have_attribute("aria-current", "page")
    f.page.get_by_role("button", name="Results page 3", exact=True).press("Space")
    expect(f.page.locator("[data-result-index]").first).to_have_attribute("aria-label", "Open A017 in Terminal")
    assert not f.errors


@pytest.mark.parametrize("activation", ["Enter", "Space", "assistive-click", "tap"])
def test_result_has_one_native_activation_path(make, activation):
    f = make(touch=activation == "tap", width=390 if activation == "tap" else 1440)
    f.ready()
    row = f.page.locator("[data-result-index]").first
    if activation == "assistive-click":
        row.evaluate("(button)=>button.click()")
    elif activation == "tap":
        row.tap()
    else:
        row.press(activation)
    expect(f.page.locator(".nav-search")).not_to_have_class(re.compile(r".*\bopen\b.*"))
    assert f.page.evaluate("window.__navigations") == [{"url": "stock.html#A001", "mode": "push"}]


def test_pointer_activates_on_release_and_ignores_secondary_press(make):
    f = make()
    f.ready()
    row = f.page.locator("[data-result-index]").first
    row.click(button="right")
    assert f.page.evaluate("window.__navigations") == []
    rect = row.bounding_box()
    f.page.mouse.move(rect["x"] + 20, rect["y"] + 20)
    f.page.mouse.down()
    assert f.page.evaluate("window.__navigations") == []
    f.page.mouse.up()
    assert len(f.page.evaluate("window.__navigations")) == 1


def test_escape_from_pagination_and_tab_departure(make):
    f = make()
    f.ready()
    f.page.get_by_role("button", name="Results page 2", exact=True).press("Escape")
    expect(f.page.locator(".search-trigger")).to_be_focused()
    expect(f.page.locator(".ticker-input")).to_have_attribute("aria-expanded", "false")
    f.ready()
    f.page.locator("#outside").focus()
    expect(f.page.locator(".search-trigger")).to_have_attribute("aria-expanded", "false")
    expect(f.page.locator("#outside")).to_be_focused()


@pytest.mark.parametrize("width,height", [(1440, 900), (390, 568)])
def test_keyboard_selection_is_announced_and_scrolls_only_results(make, width, height):
    f = make(width=width, height=height)
    f.ready()
    field = f.page.locator(".ticker-input")
    y = f.page.evaluate("scrollY")
    for _ in range(8):
        field.press("ArrowDown")
    active_id = field.get_attribute("aria-activedescendant")
    assert active_id
    selected = f.page.locator("#" + active_id)
    expect(selected).to_have_attribute("aria-selected", "true")
    assert selected.get_attribute("data-result-index") == "7"
    bounds = f.page.evaluate("""() => {
      const active=document.getElementById(document.querySelector('.ticker-input').getAttribute('aria-activedescendant'));
      const box=document.querySelector('.ticker-dropdown'), head=box.querySelector('.search-drop-head'), pager=box.querySelector('.search-pagination');
      return {row:active.getBoundingClientRect().toJSON(),box:box.getBoundingClientRect().toJSON(),
              head:head.getBoundingClientRect().toJSON(),pager:pager.getBoundingClientRect().toJSON(), y:scrollY};
    }""")
    assert bounds["row"]["top"] >= bounds["head"]["bottom"] - 1
    assert bounds["row"]["bottom"] <= bounds["pager"]["top"] + 1
    assert bounds["y"] == y


@pytest.mark.parametrize("index", [1, 7])
@pytest.mark.parametrize("focus_target", ["input", "row"])
def test_late_library_keeps_selected_identity_and_focused_result(make, index, focus_target):
    f = make(case="delayed")
    f.ready()
    field = f.page.locator(".ticker-input")
    for _ in range(index + 1):
        field.press("ArrowDown")
    if focus_target == "row":
        f.page.locator(f'[data-result-index="{index}"]').focus()
    assert len(f.held) == 1
    f.held.pop().fulfill(content_type="application/json",
                         body=json.dumps([{"t": "A000", "n": "Alpha Earlier", "v": 99999}]))
    ticker = f"A{index + 1:03}"
    selected = f.page.get_by_role("option", name=f"Open {ticker} in Terminal", exact=True)
    expect(selected).to_have_attribute("aria-selected", "true")
    expect(selected if focus_target == "row" else field).to_be_focused()
    assert field.get_attribute("aria-activedescendant") == selected.get_attribute("id")
    if index == 7:
        expect(f.page.get_by_role("button", name="Results page 2", exact=True)).to_have_attribute("aria-current", "page")
    (selected if focus_target == "row" else field).press("Enter")
    assert f.page.evaluate("window.__navigations[0].url").endswith("#" + ticker)


def test_retry_is_keyboard_operable_and_returns_focus_after_repaint(make):
    f = make(case="retry")
    f.search()
    retry = f.page.locator("[data-search-retry]")
    expect(retry).to_be_enabled(timeout=7000)
    assert "No ticker or company matches" not in f.page.locator(".ticker-dropdown").inner_text()
    retry.press("Enter")
    expect(f.page.locator("[data-result-index]")).to_have_count(8)
    expect(f.page.locator(".ticker-input")).to_be_focused()
    assert dict(f.calls) == {"us": 3, "cn": 3, "hk": 3, "ca": 3, "intl": 3}


def test_composition_and_language_keep_search_intent(make):
    f = make()
    f.ready()
    field = f.page.locator(".ticker-input")
    field.dispatch_event("compositionstart")
    field.fill("Ａ")
    field.press("Enter")
    field.press("Escape")
    assert f.page.evaluate("window.__navigations") == []
    expect(f.page.locator(".search-trigger")).to_have_attribute("aria-expanded", "true")
    field.dispatch_event("compositionend")
    expect(f.page.locator("[data-result-index]")).to_have_count(8)
    field.press("ArrowDown")
    f.page.evaluate("setLang('zh')")
    expect(field).to_have_attribute("aria-label", "搜索股票代码或公司")
    expect(f.page.locator('[aria-selected="true"] .ticker-name')).to_contain_text("示例公司1")
    expect(field).to_be_focused()


@pytest.mark.parametrize("theme,lang,width,height", [
    ("dark", "en", 1440, 900), ("light", "zh", 390, 844), ("dark", "zh", 568, 320)
])
def test_panel_has_one_scroll_body_stable_header_and_immediate_contents(make, theme, lang, width, height):
    f = make(theme=theme, lang=lang, width=width, height=height)
    f.page.locator("#fixture-dialog-open").click()
    expect(f.page.locator(".mx5-dlg")).to_have_class(re.compile(r".*mx5-dlg-in.*"))
    f.page.wait_for_function("document.querySelector('.mx5-dlg-panel').getAnimations().length === 0")
    geometry = f.page.evaluate("""() => {
      const panel=document.querySelector('.mx5-dlg-panel'), body=document.querySelector('.mx5-dlg-body');
      const head=document.querySelector('.mx5-dlg-header'), close=document.querySelector('.mx5-dlg-close');
      const child=getComputedStyle(body.firstElementChild);
      return {panel:panel.getBoundingClientRect().toJSON(),overflow:getComputedStyle(panel).overflowY,
        bodyOverflow:getComputedStyle(body).overflowY,head:head.getBoundingClientRect().toJSON(),
        close:close.getBoundingClientRect().toJSON(),childOpacity:child.opacity, childTransition:child.transitionDuration,
        childDelay:child.transitionDelay, width:innerWidth,height:innerHeight};
    }""")
    assert geometry["overflow"] == "hidden"
    assert geometry["bodyOverflow"] == "auto"
    assert geometry["childOpacity"] == "1"
    assert all(float(value.rstrip("s")) == 0 for value in geometry["childDelay"].split(", "))
    assert geometry["close"]["width"] >= 44
    assert geometry["panel"]["height"] <= height * 0.85 + 1
    top = f.page.locator(".mx5-dlg-header").bounding_box()["y"]
    f.page.locator(".mx5-dlg-body").evaluate("(body)=>{body.scrollTop=500}")
    assert f.page.locator(".mx5-dlg-header").bounding_box()["y"] == pytest.approx(top, abs=1)
    assert f.page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    f.page.locator(".mx5-dlg-close").click()
    expect(f.page.locator(".mx5-dlg")).not_to_be_visible()
    expect(f.page.locator("#fixture-dialog-open")).to_be_focused()


def test_reduced_motion_and_readable_results(make):
    f = make(motion="reduce", width=390, lang="zh", theme="light")
    f.ready()
    values = f.page.locator("[data-result-index]").first.evaluate("""row=>({
      animation:getComputedStyle(row).animationName,opacity:getComputedStyle(row).opacity,
      nameSize:parseFloat(getComputedStyle(row.querySelector('.ticker-name')).fontSize),
      scrollWidth:document.documentElement.scrollWidth,width:innerWidth
    })""")
    assert values["animation"] == "none"
    assert values["opacity"] == "1"
    assert values["nameSize"] >= 12
    assert values["scrollWidth"] <= values["width"]
    f.page.locator(".search-esc").click()
    f.page.locator("#fixture-dialog-open").click()
    motion = f.page.locator(".mx5-dlg-panel").evaluate("e=>({transform:getComputedStyle(e).transform,duration:getComputedStyle(e).transitionDuration})")
    assert motion["transform"] in ("none", "matrix(1, 0, 0, 1, 0, 0)")
    assert motion["duration"] == "0s"


def test_dialog_link_keeps_modified_native_navigation(make):
    f = make()
    modifier = "Meta" if "Mac" in f.page.evaluate("navigator.platform") else "Control"
    with f.context.expect_page(timeout=5000) as opened:
        f.page.locator("#fixture-native-link").click(modifiers=[modifier])
    child = opened.value
    child.wait_for_load_state("domcontentloaded")
    assert child.url.endswith("/macro.html#dlg-events")
    expect(f.page.locator(".mx5-dlg")).not_to_be_visible()
    expect(child.locator(".mx5-dlg")).to_be_visible()
    child.close()
    f.page.locator("#fixture-native-link").press("Enter")
    expect(f.page.locator(".mx5-dlg")).to_be_visible()
    assert not f.page.url.endswith("#dlg-events")
