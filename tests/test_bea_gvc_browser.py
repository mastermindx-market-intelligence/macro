"""Physical Chromium contracts for the shipped GMI UI, with hermetic source data.

Normal cases bridge through the REAL FastAPI handlers, auth/entitlement owners
mocked at their documented boundaries. Chart cases invoke a test-only CommonJS
export on a real NONPUBLIC candidate and retain its research-preview warning.
None of these are deployed, native-admission or genuine account-session proof.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright, expect
import pytest

from app import paywall
from app.main import app, require_user
from engine.market_ontology import bea_gvc_current as owner
from lib.dataos.registry import Registry
from tests.test_bea_gvc_current_descriptive import check, fake_rows

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://gmi-contract.invalid"
VIEW = "/api/gmi/bea/industry/5241X/view"


@pytest.fixture(scope="module")
def chromium():
    with sync_playwright() as tool:
        browser = tool.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def client(monkeypatch):
    app.dependency_overrides[require_user] = lambda: {
        "id": "11111111-1111-1111-1111-111111111111", "email": "fixture@example.invalid"}
    monkeypatch.setattr(paywall, "_store_entitlement", lambda _uid: (
        {"tier": "essential", "status": "active", "features": ["site_full"]}, True))
    monkeypatch.setattr("lib.dataos.registry.load_registry", lambda: Registry(()))
    paywall._ENT_CACHE.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()
    paywall._ENT_CACHE.clear()


def connect(page, client, *, source=None, component=False):
    seen = []
    def bridge(route):
        parsed = urlsplit(route.request.url)
        path = parsed.path + ("?" + parsed.query if parsed.query else "")
        response = client.get(path)
        body = response.content
        if component and parsed.path.endswith("/assets/view.js"):
            body = b"window.module={exports:{}};\n" + body
        if source is not None and parsed.path.startswith("/api/gmi/bea/industry/") and not parsed.path.endswith("/view"):
            code = parsed.path.rsplit("/", 1)[-1]
            status, payload = source(code)
            seen.append((parsed.path, status))
            route.fulfill(status=status, content_type="application/json", body=json.dumps(payload))
            return
        seen.append((parsed.path, response.status_code))
        headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
        route.fulfill(status=response.status_code, headers=headers, body=body)
    page.route("**/*", bridge)
    return seen


def capture(page, name):
    directory = os.environ.get("MMX_GMI_SCREENSHOT_DIR")
    if directory:
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(destination / (name + ".png")), full_page=True)


@pytest.mark.parametrize("width,theme", [(1440, "light"), (1440, "dark"), (390, "light"), (390, "dark")])
def test_actual_http_empty_state_is_responsive_and_source_free(chromium, client, width, theme):
    context = chromium.new_context(viewport={"width": width, "height": 1000},
                                   color_scheme="dark" if theme == "light" else "light")
    context.add_init_script("localStorage.setItem('theme'," + json.dumps(theme) + ")")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    seen = connect(page, client)
    page.goto(ORIGIN + VIEW, wait_until="networkidle")
    expect(page.locator("#bea-state-title")).to_have_text("Not yet available")
    expect(page.locator("#bea-data-deck")).to_be_hidden()
    expect(page.locator("#bea-region-change")).to_be_hidden()
    expect(page.locator("#bea-code")).to_have_value("5241X")
    assert page.locator("html").get_attribute("data-theme") == theme
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    assert "context.Not" not in page.locator(".reading-guide h2").inner_text()
    assert page.locator("#bea-region-bars .bar-row").count() == 0
    assert ("/api/gmi/bea/assets/view.css", 200) in seen
    assert ("/api/gmi/bea/assets/view.js", 200) in seen
    assert ("/api/gmi/bea/industry/5241X", 503) in seen
    page.locator("#bea-open-evidence").click()
    expect(page.locator("#bea-evidence")).to_have_attribute("open", "")
    expect(page.locator("#bea-reason-code")).to_have_text("SOURCE_UNREGISTERED")
    page.locator("#bea-evidence summary").click()
    capture(page, "after-unavailable-" + theme + "-" + str(width))
    assert not errors, errors
    context.close()


def signed_fixture():
    rows = fake_rows()
    values = [0, 4, 8, -3, 7, 12, 9, 15]
    for row in rows:
        world = values[row["accounting_year"] - 2017]
        row["world_import_million_USD"] = world
        row["canada_import_million_USD"] = -1
        row["china_import_million_USD"] = world + 1
        row["total_use_million_USD"] = 100 + (row["accounting_year"] - 2017) * 5
        row["quality_flags"] = (["WORLD_IMPORT_NONPOSITIVE"] if world <= 0 else []) + ["SOURCE_NEGATIVE_REGION_ADJUSTMENT"]
    return check(rows=rows)


@pytest.mark.parametrize("width,theme", [(1440,"light"), (1440,"dark"), (390,"light")])
def test_nonpublic_preview_signed_geometry_keyboard_and_accessible_values(chromium, client, width, theme):
    packet = signed_fixture()
    owner.candidate_packet_bytes(packet)
    context = chromium.new_context(viewport={"width": width, "height": 1100})
    context.add_init_script("localStorage.setItem('theme'," + json.dumps(theme) + ")")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    connect(page, client, component=True)
    page.goto(ORIGIN + VIEW, wait_until="networkidle")
    page.evaluate("p=>{module.exports.applyTheme(document,window);module.exports.renderResearchPreview(document,p)}", packet)
    expect(page.locator("#bea-state-title")).to_have_text("Research preview—not released")
    expect(page.locator("#bea-preview-notice")).to_contain_text("UNPUBLISHED")
    expect(page.locator("#bea-data-deck")).to_be_visible()
    assert page.locator("#bea-region-bars .bar-row").count() == 7
    assert page.locator("#bea-trend button").count() == 8
    assert page.locator("#bea-values-body tr").count() == 8
    zero = page.locator('#bea-trend button[data-year="2017"] .history-bar')
    assert zero.evaluate("e=>e.getBoundingClientRect().height") == 0
    negative = page.locator('#bea-trend button[data-year="2020"] .history-bar')
    assert negative.get_attribute("data-sign") == "negative"
    assert negative.evaluate("e=>e.getBoundingClientRect().top>=e.parentElement.getBoundingClientRect().top+e.parentElement.getBoundingClientRect().height/2-1")
    region = page.locator('#bea-region-bars .bar-fill[data-sign="negative"]').first
    assert region.evaluate("e=>e.getBoundingClientRect().right<=e.parentElement.getBoundingClientRect().left+e.parentElement.getBoundingClientRect().width/2+1")
    for b in page.locator("#bea-trend button").all():
        assert "USD millions" in b.get_attribute("aria-label")
    current = page.locator('#bea-years button[data-year="2024"]')
    current.focus()
    page.keyboard.press("ArrowLeft")
    expect(page.locator('#bea-years button[data-year="2023"]')).to_be_focused()
    expect(page.locator('#bea-years button[data-year="2023"]')).to_have_attribute("aria-pressed","true")
    expect(page.locator("#bea-world")).to_have_text("1,251")
    page.keyboard.press("Home")
    expect(page.locator("#bea-world")).to_have_text("0")
    expect(page.locator("#bea-yoy")).to_have_text("Not available")
    page.keyboard.press("End")
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.locator("#bea-preview-notice").evaluate("e=>e.textContent='SYNTHETIC TEST FIXTURE · UNPUBLISHED RESEARCH PREVIEW · NOT REAL BEA DATA'")
    capture(page, "after-SYNTHETIC-UNPUBLISHED-preview-" + theme + "-" + str(width))
    assert not errors, errors
    context.close()


def test_nonpublic_regional_change_mode_is_signed_and_retrospective(chromium, client):
    """Annual regional differences use the same May-2026 edition, never PIT."""
    packet = signed_fixture()
    page = chromium.new_page(viewport={"width": 1024, "height": 1000})
    connect(page, client, component=True)
    page.goto(ORIGIN + VIEW, wait_until="networkidle")
    page.evaluate(
        "p=>{module.exports.applyTheme(document,window);"
        "module.exports.renderResearchPreview(document,p)}", packet)
    expect(page.locator("#bea-region-level")).to_have_attribute("aria-pressed", "true")
    page.locator("#bea-region-change").click()
    expect(page.locator("#bea-region-change")).to_have_attribute("aria-pressed", "true")
    expect(page.locator("#bea-region-level")).to_have_attribute("aria-pressed", "false")
    expect(page.locator("#bea-negative-legend")).to_have_text("Decrease from prior year")
    expect(page.locator("#bea-positive-legend")).to_have_text("Increase from prior year")
    expect(page.locator("#bea-region-title")).to_have_text("Regional changes from 2023")
    expect(page.locator("#bea-region-bars .bar-row")).to_have_count(7)
    china = page.locator("#bea-region-bars .bar-row").nth(1)
    expect(china.locator(".bar-value")).to_have_text("+834")
    expect(china.locator(".bar-fill")).to_have_attribute("data-sign", "positive")
    expect(page.locator("#bea-region-shift")).to_contain_text("China")
    expect(page.locator("#bea-region-shift")).to_contain_text("+834")
    page.locator('#bea-years button[data-year="2020"]').click()
    expect(page.locator("#bea-region-title")).to_have_text("Regional changes from 2019")
    china = page.locator("#bea-region-bars .bar-row").nth(1)
    expect(china.locator(".bar-value")).to_have_text("−1,529")
    expect(china.locator(".bar-fill")).to_have_attribute("data-sign", "negative")
    page.locator("#bea-preview-notice").evaluate(
        "e=>e.textContent='SYNTHETIC TEST FIXTURE · UNPUBLISHED REGIONAL CHANGE · NOT REAL BEA DATA'")
    capture(page, "after-SYNTHETIC-unpublished-regional-change")
    assert china.locator(".bar-fill").evaluate(
        "e=>e.getBoundingClientRect().right<="
        "e.parentElement.getBoundingClientRect().left+"
        "e.parentElement.getBoundingClientRect().width/2+1")
    page.locator('#bea-years button[data-year="2017"]').click()
    expect(page.locator("#bea-region-title")).to_have_text("Regional change not available")
    expect(page.locator("#bea-region-bars .bar-row")).to_have_count(0)
    expect(page.locator("#bea-region-shift")).to_contain_text("No previous accounting year")
    page.locator("#bea-region-level").click()
    expect(page.locator("#bea-region-title")).to_have_text("Regional import allocation")
    expect(page.locator("#bea-negative-legend")).to_have_text("Negative adjustment")
    expect(page.locator("#bea-positive-legend")).to_have_text("Positive allocation")
    expect(page.locator("#bea-region-bars .bar-row")).to_have_count(7)
    canada = page.locator("#bea-region-bars .bar-row").first
    expect(canada.locator(".bar-value")).to_have_text("−139")
    assert "2026" in page.locator("#bea-region-note").inner_text()
    expect(page.locator("#bea-preview-notice")).to_contain_text("UNPUBLISHED")
    page.close()


@pytest.mark.parametrize("status,payload,title", [
    (401, {}, "Your session has expired"),
    (403, {}, "Premium access required"),
    (422, {}, "Use an exact industry code"),
    (502, {}, "Source service temporarily unavailable"),
    (503, {"detail":{"error":"BEA_SOURCE_REGISTRY_UNAVAILABLE"}}, "Source service temporarily unavailable"),
    (200, check(), "Research candidate—not published"),
    (200, {"status":"PUBLISHED_CURRENT_DESCRIPTIVE","may_publish":True}, "Source response could not be verified"),
])
def test_http_failures_and_candidates_never_render_numbers(chromium, client, status, payload, title):
    page = chromium.new_page()
    connect(page, client, source=lambda code:(status,payload))
    page.goto(ORIGIN + VIEW, wait_until="networkidle")
    expect(page.locator("#bea-state-title")).to_have_text(title)
    expect(page.locator("#bea-data-deck")).to_be_hidden()
    assert page.locator("#bea-region-bars .bar-row").count()==0
    page.close()


def test_latest_request_wins_even_when_transport_ignores_abort(chromium, client):
    page = chromium.new_page()
    page.add_init_script("window.pending=[];window.fetch=(url,options)=>new Promise(resolve=>pending.push({url,resolve,options}));")
    connect(page, client)
    page.goto(ORIGIN + VIEW, wait_until="domcontentloaded")
    page.wait_for_function("pending.length===1")
    page.locator("#bea-code").fill("OTHER")
    page.locator("#bea-inspect").click()
    page.wait_for_function("pending.length===2")
    latest = owner._unavailable("SOURCE_NOT_PRODUCED", "OTHER")
    old = owner._unavailable("SOURCE_RIGHTS_NOT_GRANTED", "5241X")
    page.evaluate("p=>pending[1].resolve(new Response(JSON.stringify(p),{status:503,headers:{'Content-Type':'application/json'}}))",latest)
    expect(page.locator("#bea-reason-code")).to_have_text("SOURCE_NOT_PRODUCED")
    page.evaluate("p=>pending[0].resolve(new Response(JSON.stringify(p),{status:503,headers:{'Content-Type':'application/json'}}))",old)
    page.wait_for_timeout(30)
    expect(page.locator("#bea-reason-code")).to_have_text("SOURCE_NOT_PRODUCED")
    expect(page.locator("#bea-code")).to_have_value("OTHER")
    assert page.evaluate("pending[0].options.signal.aborted")
    page.close()


def test_same_page_lookup_back_navigation_and_manual_retry(chromium, client):
    page=chromium.new_page()
    seen=connect(page,client)
    page.goto(ORIGIN+VIEW,wait_until="networkidle")
    expect(page.locator("#bea-state-title")).to_have_text("Not yet available")
    page.locator("#bea-code").fill("I001")
    page.locator("#bea-inspect").click()
    expect(page).to_have_url(ORIGIN+"/api/gmi/bea/industry/I001/view")
    expect(page.locator("#bea-reason-code")).to_have_text("SOURCE_UNREGISTERED")
    page.go_back()
    expect(page.locator("#bea-code")).to_have_value("5241X")
    expect(page.locator("#bea-state-title")).to_have_text("Not yet available")
    before=sum(path=="/api/gmi/bea/industry/5241X" for path,_ in seen)
    page.locator("#bea-retry").click()
    expect(page.locator("#bea-state-title")).to_have_text("Not yet available")
    assert sum(path=="/api/gmi/bea/industry/5241X" for path,_ in seen)==before+1
    page.close()


def test_invalid_response_does_not_claim_network_failure(chromium, client):
    page=chromium.new_page()
    seen=connect(page,client)
    def bad(route): route.fulfill(status=503,content_type="text/html",body="<p>upstream</p>")
    page.route("**/api/gmi/bea/industry/5241X",bad)
    page.goto(ORIGIN+VIEW,wait_until="networkidle")
    expect(page.locator("#bea-state-title")).to_have_text("The response could not be read")
    expect(page.locator("#bea-data-deck")).to_be_hidden()
    page.close()


def test_real_cookie_auth_reader_connects_html_css_js_and_data(chromium, client, monkeypatch):
    import base64
    from app.main import _SB_STORAGE_KEY
    uid = "11111111-1111-1111-1111-111111111111"
    app.dependency_overrides.pop(require_user, None)
    tokens = []
    def identity(token):
        tokens.append(token)
        if token == "fixture-valid-session":
            return paywall._Identity(uid=uid, email="fixture@example.invalid",
                record={"id":uid, "email":"fixture@example.invalid"}, status="ok")
        return paywall._Identity(uid=None, email="", record=None, status="invalid")
    monkeypatch.setattr(paywall, "_resolve_identity", identity)
    cookie = "base64-" + base64.urlsafe_b64encode(
        json.dumps({"access_token":"fixture-valid-session"}).encode()).decode().rstrip("=")
    client.cookies.set(_SB_STORAGE_KEY, cookie)
    page = chromium.new_page()
    try:
        seen = connect(page, client)
        page.goto(ORIGIN+VIEW, wait_until="networkidle")
        expect(page.locator("#bea-state-title")).to_have_text("Not yet available")
        for endpoint in (VIEW, "/api/gmi/bea/assets/view.css", "/api/gmi/bea/assets/view.js"):
            assert (endpoint,200) in seen
        assert ("/api/gmi/bea/industry/5241X",503) in seen
        assert tokens and set(tokens)=={"fixture-valid-session"}
        client.cookies.clear()
        assert client.get(VIEW).status_code==401
    finally:
        client.cookies.clear();page.close()


def test_asset_css_remains_paid_uncacheable_and_not_path_selectable(client, monkeypatch):
    response=client.get("/api/gmi/bea/assets/view.css")
    assert response.status_code==200
    assert response.headers["content-type"].startswith("text/css")
    assert response.headers["cache-control"]=="private, no-store"
    assert client.get("/api/gmi/bea/assets/view.css?path=/private").status_code==422
    monkeypatch.setattr(paywall,"_store_entitlement",lambda _uid:({"tier":"free","status":"none","features":[]},True))
    paywall._ENT_CACHE.clear()
    assert client.get("/api/gmi/bea/assets/view.css").status_code==403


def test_timeout_is_bounded_and_not_a_false_source_verdict(chromium, client):
    page=chromium.new_page()
    page.add_init_script("const realTimer=window.setTimeout.bind(window);window.setTimeout=(f,t,...a)=>realTimer(f,t===10000?30:t,...a);window.fetch=(url,options)=>new Promise((resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new DOMException('aborted','AbortError'))));")
    connect(page,client)
    page.goto(ORIGIN+VIEW,wait_until="domcontentloaded")
    expect(page.locator("#bea-state-title")).to_have_text("The availability check timed out")
    expect(page.locator("#bea-source-state")).to_have_text("Not confirmed")
    expect(page.locator("#bea-retry")).to_be_enabled()
    expect(page.locator("#bea-data-deck")).to_be_hidden()
    page.close()


def test_restoring_browser_back_cache_rechecks_without_duplicate_controller(chromium, client):
    page=chromium.new_page()
    seen=connect(page,client)
    page.goto(ORIGIN+VIEW,wait_until="networkidle")
    expect(page.locator("#bea-state-title")).to_have_text("Not yet available")
    source_path="/api/gmi/bea/industry/5241X"
    before=sum(path==source_path for path,_ in seen)
    page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}));window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}));")
    expect(page.locator("#bea-state-title")).to_have_text("Not yet available")
    assert sum(path==source_path for path,_ in seen)==before+1
    page.close()
