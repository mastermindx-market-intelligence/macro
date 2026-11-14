"""Real builder + browser contracts. All browser requests are served locally or held."""
from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.sync_api import sync_playwright

from scripts import build_tech_lab as builder
from scripts.tech_lab_entry_evidence import load_entry_evidence

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as runtime:
        instance = runtime.chromium.launch()
        yield instance
        instance.close()


def build_html(tmp_path, monkeypatch, unavailable=False):
    (tmp_path / "templates").symlink_to(ROOT / "templates", target_is_directory=True)
    monkeypatch.setattr(builder.config, "ROOT", tmp_path)
    payload = load_entry_evidence(ROOT)
    assert payload["available"] and payload["cohort"]["available"]
    if unavailable:
        payload = {"available": False, "cohort": {"available": False},
                   "reason_code": '<img src=x onerror="window.evidenceInjected=true">'}
    monkeypatch.setattr(builder, "load_entry_evidence", lambda root: payload)
    assert builder.main() == 0
    return (tmp_path / "site/tech_lab.html").read_text()


def local_requests(page, html):
    pending = []
    assets = (ROOT / "templates").resolve()

    def serve(route):
        parsed = urlparse(route.request.url)
        if parsed.hostname != "lab-proof.test":
            route.abort()
        elif parsed.path == "/tech_lab.html":
            route.fulfill(status=200, content_type="text/html", body=html)
        elif parsed.path.startswith("/factordata/"):
            # Never settle the live requests: static research must boot independently.
            pending.append(route)
        else:
            path = (assets / parsed.path.lstrip("/")).resolve()
            if path.is_relative_to(assets) and path.is_file():
                route.fulfill(status=200, content_type=mimetypes.guess_type(path.name)[0]
                              or "application/octet-stream", body=path.read_bytes())
            else:
                route.fulfill(status=404, body="Unavailable in isolated browser proof")
    page.route("**/*", serve)
    return pending


@pytest.mark.parametrize("width,height", [(1440, 1000), (390, 844)])
def test_real_page_static_context_horizons_keyboard_and_mobile(
        tmp_path, monkeypatch, browser, width, height):
    html = build_html(tmp_path, monkeypatch)
    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    pending = local_requests(page, html)
    page.goto("http://lab-proof.test/tech_lab.html#entry-evidence", wait_until="domcontentloaded")
    panel = page.locator("#tab-entry-evidence")
    assert panel.is_visible()
    assert page.locator("#tb-entry-evidence").get_attribute("aria-selected") == "true"
    assert page.locator('[data-er-cohort="available"]').is_visible()
    assert "23,065" in panel.inner_text() and "22,860" in panel.inner_text()
    assert page.locator('[data-er-results="21"] tbody tr').count() == 12
    assert page.locator('[data-er-results="63"] tbody tr').count() == 12
    assert page.locator(".er-contrasts tbody tr").count() == 11
    assert page.locator('[data-er-view="21"]').is_visible()
    assert not page.locator('[data-er-view="63"]').is_visible()
    page.locator('[data-er-horizon="63"]').click()
    assert page.locator('[data-er-view="63"]').is_visible()
    assert not page.locator('[data-er-view="21"]').is_visible()
    assert "Secondary description" in page.locator('[data-er-view="63"]').inner_text()
    page.locator('[data-er-horizon="21"]').click()
    assert "56.16%" in page.locator('[data-er-view="21"]').inner_text()
    assert page.locator("#tl-legacy-data-note").is_hidden()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    page.locator("#tb-entry-evidence").focus()
    page.keyboard.press("ArrowRight")
    assert page.locator("#tb-siglab").get_attribute("aria-selected") == "true"
    page.keyboard.press("Home")
    assert page.locator("#tb-screener").get_attribute("aria-selected") == "true"
    page.keyboard.press("End")
    assert page.locator("#tb-test").get_attribute("aria-selected") == "true"
    page.locator("#tb-entry-evidence").click()
    page.evaluate("""() => {
      document.documentElement.dataset.lang='zh';
      document.documentElement.dataset.theme='dark';
      document.dispatchEvent(new CustomEvent('langchange',{detail:'zh'}));
    }""")
    assert page.locator("#er-title .l-zh").is_visible()
    assert not page.locator("#er-title .l-en").is_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    assert pending, "Live requests were not exercised"
    assert errors == []
    context.close()


def test_unavailable_evidence_stays_escaped_and_never_becomes_a_sample(
        tmp_path, monkeypatch, browser):
    html = build_html(tmp_path, monkeypatch, unavailable=True)
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    local_requests(page, html)
    page.goto("http://lab-proof.test/tech_lab.html#entry-evidence", wait_until="domcontentloaded")
    panel = page.locator("#tab-entry-evidence")
    assert panel.is_visible()
    assert panel.locator('[data-er-state="unavailable"]').is_visible()
    assert panel.locator("table,.er-metrics,img").count() == 0
    assert "No statistics, sample results" in panel.inner_text()
    assert page.evaluate("window.evidenceInjected !== true")
    context.close()
