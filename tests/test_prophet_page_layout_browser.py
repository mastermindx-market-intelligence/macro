"""Paper composition over the actual SSR template; synthetic data, not live proof."""
from pathlib import Path
import os
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright

from tests.test_dashboard_template_render import _base_vm, _env

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def layout_browser():
    with sync_playwright() as playwright:
        executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
        browser = playwright.chromium.launch(**({"executable_path": executable} if executable else {}))
        yield browser
        browser.close()


@pytest.fixture(scope="module")
def layout_html():
    vm = _base_vm()
    vm["market_state"] = {"color": "red", "label_en": "Risk-off", "label_zh": "避险"}
    for row in vm["us_standouts"]["buy"]:
        row["featured"] = True
    # The producer's declared shelf count selects Today; featured flags alone
    # deliberately leave the workspace on Candidates. This synthetic fixture
    # supplies that metadata without issuing any live selection receipt.
    vm["us_standouts"]["ranking"] = {"featured_count": len(vm["us_standouts"]["buy"])}
    return _env().get_template("dashboard.html.j2").render(**vm, mode="stocks")


@pytest.mark.parametrize("width", [320, 390, 820, 1440])
@pytest.mark.parametrize("theme,lang", [("light", "en"), ("dark", "en"), ("light", "zh"), ("dark", "zh")])
def test_paper_composition_first_paint(layout_browser, layout_html, width, theme, lang, tmp_path):
    # Normal first paint, with every external script/data request still aborted.
    # JavaScript-disabled navigation deliberately expands the no-JS site map;
    # that accessible fallback is not the collapsed mobile workspace.
    # No credentials or authenticated journey are exercised by this fixture.
    context = layout_browser.new_context(viewport={"width": width, "height": 1000})
    page = context.new_page()
    page.set_default_timeout(3000)

    def serve(route):
        path = urlsplit(route.request.url).path
        if path == "/us_stocks.html":
            route.fulfill(content_type="text/html; charset=utf-8", body=layout_html)
        elif path.endswith(".css") and (ROOT / "templates" / Path(path).name).is_file():
            route.fulfill(content_type="text/css", body=(ROOT / "templates" / Path(path).name).read_text())
        else:
            route.abort()

    page.route("**/*", serve)
    try:
        page.goto("http://prophet-layout.test/us_stocks.html", wait_until="load")
        page.evaluate("([theme,lang])=>{document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang=lang}", [theme, lang])
        assert page.locator("h1").count() == 1
        boxes = [page.locator(selector).bounding_box() for selector in (
            "#stocks-header", "#prophet-market-brief", "#prophet-workspace-nav", "#us-standouts"
        )]
        assert all(boxes)
        assert [box["y"] for box in boxes] == sorted(box["y"] for box in boxes)
        assert page.locator("#stocks-header").evaluate("e=>getComputedStyle(e).boxShadow") == "none"
        assert page.locator("#stocks-header").evaluate("e=>getComputedStyle(e).borderTopWidth") == "0px"
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "horizontal document overflow"
        assert page.locator("#prophet-workspace-nav").evaluate("e=>e.scrollWidth <= e.clientWidth || getComputedStyle(e).overflowX === 'auto'")
        for control in page.locator("#prophet-workspace-nav a").all():
            assert control.bounding_box()["height"] >= 44
        assert page.locator("#us-standouts").get_attribute("data-prophet-src") == "today"
        first_card = page.locator("#us-today-grid .po-card").first.bounding_box()
        assert first_card and first_card["y"] < (740 if width < 960 else 570), first_card
        risk = page.locator("#prophet-market-brief").inner_text()
        assert ("保住本金" if lang == "zh" else "defend capital") in risk
        assert ("defend capital" if lang == "zh" else "保住本金") not in risk
        page.screenshot(path=str(tmp_path / f"prophet-{width}-{theme}-{lang}.png"))
        # An empty note must not consume a row, but a native state update must
        # reveal the SAME warning region without reconstructing its content.
        if width == 1440 and theme == "light" and lang == "en":
            note = page.locator("#us-standouts .pbs-note")
            assert not note.is_visible()
            page.locator('[data-bs-note="behind"]').evaluate("e=>e.removeAttribute('hidden')")
            assert note.is_visible()
            assert "last night's confirmed picks" in note.inner_text()
        print(f"layout {width} {theme} {lang}: first_card_y={first_card['y']:.1f}; no overflow")
    finally:
        context.close()
