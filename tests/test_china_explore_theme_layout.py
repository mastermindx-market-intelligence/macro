"""Exercise the China Explore template and renderer together in an offline browser."""
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = "https://china.test/sector_central_china.html"
NAME = "Advanced Manufacturing and Semiconductor Equipment"
ZH_NAME = "先进制造与半导体设备及上游材料产业链"


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        chromium = playwright.chromium.launch()
        yield chromium
        chromium.close()


@pytest.fixture(scope="module")
def html():
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    return env.get_template("sector_central_china.html.j2").render()


def payload():
    theme = dict(id="long_name", name=NAME, name_zh=ZH_NAME, rank=1, score=73,
                 label="dominant", label_en="DOMINANT", label_zh="领涨",
                 reco="accumulate", reco_en="ACCUMULATE", reco_zh="增持",
                 rs_pctile=0.99, components={}, perf={"20d": {"rel": 0.12}})
    return {"as_of": "2026-11-02", "benchmark_label": "CSI 300", "benchmark_label_zh": "沪深300",
            "categories": [], "baskets": [{"id": theme["id"], "name": NAME, "members": []}],
            "chart": {"dates": ["2026-10-29", "2026-10-30", "2026-11-02"],
                      "bench": [100, 101, 102], "baskets": {"long_name": [100, 105, 110]}},
            "theme_intel": {"themes": [theme]}}


def load(page, html, data, status=200):
    def serve(route):
        url = urlsplit(route.request.url)
        if url.netloc != "china.test":
            return route.abort()
        if url.path == "/sector_central_china.html":
            return route.fulfill(content_type="text/html", body=html)
        if url.path == "/chinabasketdata/baskets.json":
            return route.fulfill(status=status, json=data)
        file = ROOT / "site" / url.path.lstrip("/")
        if file.is_file() and file.resolve().is_relative_to((ROOT / "site").resolve()):
            return route.fulfill(path=file)
        return route.fulfill(status=404, body="")

    page.route("**/*", serve)
    page.goto(PAGE + "#explore", wait_until="domcontentloaded")


@pytest.mark.parametrize("width,lang", [(320, "en"), (390, "zh"), (1493, "en")])
def test_long_theme_and_chart_fit_with_no_entry(browser, html, width, lang):
    page = browser.new_page(viewport={"width": width, "height": 900}, locale=lang)
    try:
        load(page, html, payload())
        card = page.locator("#theme-long_name")
        name = card.locator(".nm")
        expect(name).to_have_text(NAME + ZH_NAME)
        expect(name.locator(".l-" + lang)).to_be_visible()
        expect(card.locator(".treco")).to_contain_text("no entry")
        expect(card.locator(".trend svg")).to_be_visible()
        assert card.evaluate("""card => {
            const name = card.querySelector('.nm'), rect = card.getBoundingClientRect();
            const spark = card.querySelector('.trend svg').getBoundingClientRect();
            const range = document.createRange();
            range.selectNodeContents(Array.from(name.children).find(label => label.getClientRects().length));
            return name.scrollWidth <= name.clientWidth + 1 &&
                Array.from(range.getClientRects()).every(line => line.right <= card.querySelector('.sc').getBoundingClientRect().left + 1) &&
                spark.width > 0 && spark.left >= rect.left && spark.right <= rect.right &&
                document.documentElement.scrollWidth <= window.innerWidth;
        }""")
        card.locator("summary").focus()
        page.keyboard.press("Enter")
        expect(card.locator("details")).to_have_attribute("open", "")
        expect(name).to_have_attribute("href", "basket_china/long_name.html")
    finally:
        page.close()


@pytest.mark.parametrize("kind", ["no_series", "empty", "error"])
def test_theme_data_states(browser, html, kind):
    data = payload()
    data.pop("chart")
    if kind == "empty":
        data["theme_intel"]["themes"] = []
    page = browser.new_page(locale="en-US")
    try:
        load(page, html, data, 503 if kind == "error" else 200)
        if kind == "no_series":
            expect(page.locator("#theme-long_name .trend")).to_contain_text("No trend data")
            expect(page.locator("#theme-long_name .trend svg")).to_have_count(0)
        else:
            status = page.locator("#theme-desk-status")
            expect(status).to_be_visible()
            expect(status).to_contain_text("No themes ranked" if kind == "empty" else "could not load")
    finally:
        page.close()
