"""Browser behavior over the real template, API router and producer fixtures."""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from tests.test_prophet_early_observations import seed

ROOT = Path(__file__).resolve().parents[1]


def test_discovery_has_an_authenticated_dashboard_consumer():
    assert (ROOT / "templates/_us_early_observations.html.j2").is_file(), "B03 has no product consumer"
    assert '{% include "_us_early_observations.html.j2" %}' in (ROOT / "templates/dashboard.html.j2").read_text()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        instance = p.chromium.launch()
        yield instance
        instance.close()


@pytest.fixture
def desk(browser, tmp_path, monkeypatch):
    import app.prophet_observations as mod
    monkeypatch.setattr(mod, "_DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(mod, "expected_last_session", lambda: date(2026, 10, 8))
    source, _, _, _ = seed(tmp_path, tuple(f"N{i:03}" for i in range(60)) + ("AMZN",))
    app = FastAPI()
    app.include_router(mod.router)
    app.dependency_overrides[mod.require_site_full_user] = lambda: {"id": "paid-fixture"}
    api = TestClient(app)
    fragment = Environment(loader=FileSystemLoader(ROOT / "templates")).get_template(
        "_us_early_observations.html.j2").render()
    css = (ROOT / "templates/theme.css").read_text()
    # The shared tokens deliberately do not define the page's body/panel base.
    # Use the actual dashboard base CSS, not a white browser-default canvas or
    # a second hand-authored art direction. Remaining board widgets are outside
    # this bounded component fixture; full-page acceptance remains a release gate.
    dashboard = (ROOT / "templates/dashboard.html.j2").read_text()
    base_css = dashboard.split("<style>", 1)[1].split(".sb-section-lbl", 1)[0]
    assert "body { background: var(--bg)" in base_css and ".panel {" in base_css
    css += "\n" + base_css
    # Same MDXAuth session interface as the live shell; no real credential.
    html = ('<!doctype html><html data-theme="dark" data-lang="en"><head><meta charset="utf-8"><style>'
            + css + '</style></head><body><main class="wrap">'
            + '<script>window.MDXAuth={client:async()=>({auth:{getSession:async()=>'
            + '({data:{session:{access_token:"fixture-only"}}})}})};</script>'
            + fragment + '</main></body></html>')
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    mode = {"status": None, "requests": 0}
    def route(request):
        path = urlsplit(request.request.url)
        if path.path == "/api/prophet/observations/v1":
            mode["requests"] += 1
            if mode["status"] is not None:
                request.fulfill(status=mode["status"], content_type="application/json", body='{}')
            else:
                response = api.get(path.path + "?" + path.query,
                                   headers={"Authorization": request.request.headers.get("authorization", "")})
                request.fulfill(status=response.status_code, content_type="application/json", body=response.text)
        elif path.path == "/":
            request.fulfill(content_type="text/html; charset=utf-8", body=html)
        else:
            request.abort()
    page.route("**/*", route)
    page.goto("http://prophet.test/")
    yield page, source, mode
    page.close()
    api.close()


def open_desk(page):
    page.locator("#us-early-observations > summary").click()
    page.wait_for_function("document.querySelector('#us-early-observations').dataset.state === 'ready'")


def test_server_search_finds_amzn_outside_loaded_page_and_is_not_an_episode(desk):
    page, _, mode = desk
    assert mode["requests"] == 0
    open_desk(page)
    assert page.locator("[data-eo-row]").count() == 8
    assert page.locator("[data-eo-rows]").inner_text().find("AMZN") == -1
    page.locator("#eo-search").fill("amzn")
    page.locator("[data-eo-search]").click()
    page.wait_for_function("document.querySelector('[data-eo-rows]').textContent.includes('AMZN')")
    assert page.locator("[data-eo-row]").count() == 1
    assert "61" in page.locator("[data-eo-counts]").inner_text()
    assert "40 featured" in page.locator("[data-eo-counts]").inner_text()
    assert "21 beyond the preview" in page.locator("[data-eo-counts]").inner_text()
    assert "Episode link unavailable" in page.locator("[data-eo-rows]").inner_text()
    page.locator("[data-eo-rows] summary").click()
    assert "MACD below signal" in page.locator("[data-eo-rows]").inner_text()
    assert "first-available time are not recorded here" in page.locator("[data-eo-rows]").inner_text()
    assert mode["requests"] == 2
    assert not page.locator("[data-eo-rows] button").count()


@pytest.mark.parametrize("status,state", [(401, "signed-out"), (403, "locked"), (503, "unavailable")])
def test_failures_clear_private_rows_and_offer_retry(desk, status, state):
    page, _, mode = desk
    open_desk(page)
    mode["status"] = status
    page.locator("[data-eo-retry]").click()
    page.wait_for_function(f"document.querySelector('#us-early-observations').dataset.state === '{state}'")
    assert page.locator("[data-eo-row]").count() == 0
    assert page.locator("[data-eo-retry]").is_visible()
    assert not page.locator("[data-eo-next]").is_enabled()
    mode["status"] = None
    page.locator("[data-eo-retry]").click()
    page.wait_for_function("document.querySelector('#us-early-observations').dataset.state === 'ready'")


def test_sign_out_clears_rows_before_any_next_request(desk):
    page, _, _ = desk
    open_desk(page)
    page.evaluate("""() => {
      window.MDXAuth.client = async()=>({auth:{getSession:async()=>({data:{session:null}})}});
      window.dispatchEvent(new Event('mdx-auth'));
    }""")
    page.wait_for_function("document.querySelector('#us-early-observations').dataset.state === 'signed-out'")
    assert page.locator("[data-eo-row]").count() == 0


def test_paging_keeps_one_snapshot_and_refresh_recovers_changed_source(desk):
    page, _, mode = desk
    open_desk(page)
    first = page.locator("[data-eo-row]").first.inner_text()
    page.locator("[data-eo-next]").click()
    page.wait_for_function("document.querySelector('[data-eo-prev]').disabled === false")
    assert page.locator("[data-eo-row]").first.inner_text() != first
    page.locator("[data-eo-prev]").click()
    page.wait_for_function("document.querySelector('[data-eo-prev]').disabled === true && document.querySelector('#us-early-observations').dataset.state === 'ready'")
    assert page.locator("[data-eo-row]").first.inner_text() == first
    mode["status"] = 409
    page.locator("[data-eo-next]").click()
    page.wait_for_function("document.querySelector('#us-early-observations').dataset.state === 'changed'")
    assert page.locator("[data-eo-row]").count() == 0
    assert not page.locator("[data-eo-next]").is_enabled()
    mode["status"] = None
    page.locator("[data-eo-retry]").click()
    page.wait_for_function("document.querySelector('#us-early-observations').dataset.state === 'ready'")
    assert page.locator("[data-eo-row]").first.inner_text() == first
    assert not page.locator("[data-eo-prev]").is_enabled()


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("lang", ["en", "zh"])
@pytest.mark.parametrize("width", [390, 768, 1440])
def test_theme_language_and_mobile_composition(desk, theme, lang, width, tmp_path):
    page, _, _ = desk
    page.set_viewport_size({"width": width, "height": 1100})
    page.evaluate("([t,l])=>{document.documentElement.dataset.theme=t;document.documentElement.dataset.lang=l}",
                  [theme, lang])
    open_desk(page)
    if lang == "zh":
        assert "观察源记录的潜在转向" in page.locator("#us-early-observations").inner_text()
    page.locator("[data-eo-rows] summary").first.click()
    assert ("MACD 低于信号线" if lang == "zh" else "MACD below signal") in page.locator("[data-eo-rows]").inner_text()
    canvas = page.evaluate("getComputedStyle(document.body).backgroundColor")
    assert canvas != "rgba(0, 0, 0, 0)"
    overflow = page.evaluate("""() => [...document.querySelectorAll('#us-early-observations *')]
      .map(e=>({tag:e.tagName,cls:e.className,x:e.getBoundingClientRect().x,
                width:e.getBoundingClientRect().width,text:e.textContent.slice(0,80)}))
      .filter(e=>e.x+e.width>innerWidth+1)""")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), json.dumps(overflow, ensure_ascii=False)
    search = page.locator("#eo-search").bounding_box()
    assert search and search["width"] > 150
    assert page.locator("[data-eo-row]").count() == 8
    other = ".l-zh" if lang == "en" else ".l-en"
    assert not page.locator("#us-early-observations " + other).first.is_visible()
    page.locator("#us-early-observations").screenshot(path=str(tmp_path / f"observations-{theme}-{lang}-{width}.png"))
