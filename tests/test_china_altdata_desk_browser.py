"""Anonymous local-artifact browser contracts. No accounts, collectors or external requests.

Default CI uses synthetic data. CHINA_ALTDATA_VERIFY_BUILT=1 runs the same journeys
against this checkout's generated site and full sidecar, without modifying either.
"""
from contextlib import contextmanager
from functools import partial
import http.server
import json
import os
from pathlib import Path
import re
import socketserver
import threading
from urllib.parse import urlparse

import pytest
from playwright.sync_api import sync_playwright, expect
from tests.test_china_altdata_desk_ui import render

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture
def artifact(tmp_path):
    if os.environ.get("CHINA_ALTDATA_VERIFY_BUILT") == "1":
        site = ROOT / "site"
        desk = json.loads((site / "chinaaltdata/desk.json").read_text())
    else:
        site = tmp_path / "site"
        site.mkdir()
        html, desk = render()
        (site / "china_altdata.html").write_text(html)
        target = site / "chinaaltdata"
        target.mkdir()
        (target / "desk.json").write_text(json.dumps(desk))
        for asset in set(re.findall(r'(?:src|href)="([^"?#]+)', html)):
            source = ROOT / "templates" / asset
            if "/" not in asset and asset.endswith((".css", ".js")) and source.is_file():
                (site / asset).write_bytes(source.read_bytes())
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(site)))
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", desk
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@contextmanager
def local_page(base, width=1440, locale="en", theme="dark", data_handler=None):
    errors, external = [], []
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width":width,"height":900 if width>400 else 844},
                                      reduced_motion="reduce")
        context.add_init_script("localStorage.setItem('theme'," + json.dumps(theme) + ");"
                                "localStorage.removeItem('themeAuto');"
                                "localStorage.setItem('lang'," + json.dumps(locale) + ");")
        def route_request(route):
            url = route.request.url
            if not url.startswith(base + "/"):
                external.append(url)
                route.abort()
            elif data_handler and urlparse(url).path.endswith("/chinaaltdata/desk.json"):
                data_handler(route)
            else:
                route.continue_()
        context.route("**/*", route_request)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base + "/china_altdata.html", wait_until="networkidle")
        try:
            yield page, errors
        finally:
            context.close()
            browser.close()


@pytest.mark.parametrize("width,locale,theme", [(1440,"en","dark"),(390,"zh","light")])
def test_complete_research_journey(artifact, width, locale, theme):
    base, desk = artifact
    with local_page(base,width,locale,theme) as (page,errors):
        expect(page.locator("#ced-rows > tr")).to_have_count(8)
        page.locator("#companies").scroll_into_view_if_needed()
        expect(page.locator("#ced-search")).to_be_enabled(timeout=25000)
        expect(page.locator("#ced-load")).to_be_hidden()
        first = page.locator("#ced-rows .ced-ticker").first.inner_text()
        page.locator("#ced-next").click()
        expect(page.locator("#ced-page")).to_contain_text("2")
        assert page.locator("#ced-rows .ced-ticker").first.inner_text() != first
        target = next(r for r in reversed(desk["rows"]) if r["available"]>=2)
        query = target["ticker"].split(".")[0].translate(str.maketrans("0123456789","０１２３４５６７８９"))
        page.locator("#ced-search").fill(query)
        expect(page.locator("#ced-rows > tr")).to_have_count(1)
        expect(page.locator("#ced-rows .ced-ticker")).to_have_text(target["ticker"])
        page.locator("#ced-search").fill("no-such-company-zzzz")
        expect(page.locator("#ced-no-results")).to_be_visible()
        page.locator("#ced-reset").click()
        expect(page.locator("#ced-rows > tr")).to_have_count(8)
        expect(page.locator("#ced-search")).to_be_focused()
        page.locator("#ced-side").select_option("cautionary")
        for row in page.locator("#ced-rows > tr").all():
            assert ("Cautionary" if locale=="en" else "偏谨慎") in row.inner_text()
        page.locator("#ced-reset").click()
        trigger = page.locator("#ced-rows .ced-evidence-button").first
        trigger.click()
        expect(page.locator("#ced-detail")).to_be_visible()
        expect(page.locator("#ced-detail tbody tr")).to_have_count(7)
        href = page.locator("#ced-detail-body a").first.get_attribute("href")
        assert re.fullmatch(r"china_lookup\.html#\d{6}\.(SS|SZ|BJ)",href)
        page.keyboard.press("Escape")
        expect(page.locator("#ced-detail")).not_to_be_visible()
        expect(trigger).to_be_focused()
        page.locator("#ced-event-type").select_option("unlock")
        assert page.locator("#ced-events article").count() <= 8
        for item in page.locator("#ced-events .ced-badge").all():
            assert ("Share unlock" if locale=="en" else "限售解禁") in item.inner_text()
        page.evaluate("document.documentElement.dataset.lang='zh'")
        expect(page.locator("#ced-side option[value='cautionary']")).to_have_text("偏谨慎")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert not errors


@pytest.mark.parametrize("failure", ["network","schema","nested","vintage"])
def test_failed_load_preserves_preview_and_retry_recovers(artifact, failure):
    base, desk = artifact
    recovered = False
    def respond(route):
        if recovered:
            route.fulfill(status=200,content_type="application/json",body=json.dumps(desk))
        elif failure=="network":
            route.fulfill(status=503,body="temporarily unavailable")
        else:
            bad = json.loads(json.dumps(desk))
            if failure=="schema":
                bad["schema"]="invalid"
            elif failure=="nested":
                bad["rows"][0]["sources"][0]=None
            else:
                bad["generated_at"]="2000-01-01T00:00:00Z"
            route.fulfill(status=200,content_type="application/json",body=json.dumps(bad))
    with local_page(base,data_handler=respond) as (page,errors):
        page.locator("#companies").scroll_into_view_if_needed()
        expect(page.locator("#ced-load-error")).to_be_visible(timeout=25000)
        expect(page.locator("#ced-search")).to_be_disabled()
        expect(page.locator("#ced-rows > tr")).to_have_count(8)
        assert page.locator("#ced-rows a").first.get_attribute("href").startswith("china_lookup.html#")
        recovered = True
        page.locator("#ced-load").click()
        expect(page.locator("#ced-search")).to_be_enabled(timeout=25000)
        expect(page.locator("#ced-load-error")).to_be_hidden()
        assert not errors
