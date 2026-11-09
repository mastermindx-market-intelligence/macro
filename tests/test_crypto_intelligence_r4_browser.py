"""Headless real-browser acceptance for the isolated Crypto R4 candidate.

Optional browser tooling: pytest skips only when Playwright/Chromium is not
installed. Run explicitly before release; unit tests alone are not visual proof.
"""
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Error, sync_playwright

PAGE = (Path(__file__).resolve().parents[1] / "site" / "crypto-r4.html").as_uri()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        try:
            instance = p.chromium.launch(headless=True)
        except Error as exc:
            pytest.skip(f"Chromium not installed for R4 browser test: {exc}")
        yield instance
        instance.close()


def test_r4_four_views_locales_themes_and_mobile_layout(browser):
    for width in (1440, 390):
        context = browser.new_context(viewport={"width": width, "height": 844}, is_mobile=width == 390, has_touch=width == 390, device_scale_factor=2 if width == 390 else 1)
        page = context.new_page()
        page.set_default_timeout(4500)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(PAGE, wait_until="load")
        for theme in ("light", "dark"):
            for lang in ("en", "zh"):
                page.locator("html").evaluate(
                    "(element, attrs) => { element.dataset.theme = attrs.theme; element.dataset.lang = attrs.lang; }",
                    {"theme": theme, "lang": lang},
                )
                for view in ("overview", "bitcoin", "markets", "scenarios"):
                    page.locator(f'.cri-tabs [data-route="{view}"]').click()
                    assert page.locator("section[data-view]:visible").count() == 1
                    assert page.locator(f'.cri-tabs [data-route="{view}"][aria-current="page"]').count() == 1
                    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                    assert page.evaluate("document.body.scrollWidth <= window.innerWidth")
                assert ("加密" in page.locator("h1").inner_text()) is (lang == "zh")
        assert errors == [], errors
        context.close()


def test_r4_horizon_deep_link_drawer_history_and_chart_window(browser):
    context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
    page = context.new_page()
    page.set_default_timeout(4500)
    page.goto(PAGE + "#scenarios?h=30")
    assert page.locator('.cri-tabs [data-route="scenarios"][aria-current="page"]').count() == 1
    assert page.locator('[data-horizon="30"][aria-pressed="true"]').count() >= 1
    page.locator('[data-open="scenario:continuation"]:visible').first.click()
    assert page.locator("#cri-dialog").evaluate("(element) => element.open")
    assert "h=30" in page.evaluate("location.hash")
    page.locator("#cri-dialog-close").click()
    assert not page.locator("#cri-dialog").evaluate("(element) => element.open")
    assert "panel=" not in page.evaluate("location.hash")
    page.locator('.cri-tabs [data-route="bitcoin"]').click()
    page.locator('[data-chart-window="30"]:visible').first.click()
    assert "window=30" in page.evaluate("location.hash")
    page.reload()
    assert page.locator('[data-chart-window="30"][aria-pressed="true"]').count() >= 1
    context.close()


def test_r4_saved_snapshot_retains_horizon_and_original_cutoff(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.set_default_timeout(4500)
    # Synthetic time anchored to the dated demonstration artifact, not market time.
    page.add_init_script("""() => {
      const NativeDate = Date;
      const fixedNow = new NativeDate('2026-10-18T12:00:00Z').getTime();
      class TestDate extends NativeDate {
        constructor(...args) { super(...(args.length ? args : [fixedNow])); }
        static now() { return fixedNow; }
      }
      window.Date = TestDate;
    }""")
    page.goto(PAGE + "#scenarios?h=30")
    page.locator('[data-open="scenario:continuation"]:visible').first.click()
    assert not page.locator('[data-snapshot-action="toggle"]').is_disabled()
    original_cutoff = page.locator("#cri-dialog-body .cri-note").first.inner_text()
    page.locator('[data-snapshot-action="toggle"]').click()
    saved = page.evaluate('JSON.parse(localStorage.getItem("mmx.crypto.r4.scenarios.v1"))')
    assert len(saved) == 1
    assert saved[0]["issue_evidence"]["bitcoin_as_of"] == "2026-10-17"
    assert saved[0]["issue_evidence"]["market_as_of"] == "2026-10-15"
    assert any(f["quality"] == "stale" for f in saved[0]["issue_evidence"]["families"])
    assert page.locator("#cri-toast").is_visible()
    assert page.locator("#cri-toast").evaluate("""element => {const b=element.getBoundingClientRect();return element.contains(document.elementFromPoint(b.x+b.width/2,b.y+b.height/2))}""")
    page.reload()
    assert page.locator("#cri-dialog").evaluate("(element) => element.open")
    page.locator("#cri-dialog-close").click()
    page.locator('[data-open="saved"]').click()
    page.locator('#cri-dialog-body button').last.click()
    assert "original conditions" in page.locator("#cri-dialog-body").inner_text()
    assert "Original evidence snapshot" in page.locator("#cri-dialog-body").inner_text()
    assert original_cutoff in page.locator("#cri-dialog-body").inner_text()
    page.locator("#cri-dialog-body details").last.evaluate("(element) => element.open = true")
    assert "stale" in page.locator("#cri-dialog-body").inner_text()
    page.locator("#cri-dialog-body").get_by_role("button", name="Historical review").click()
    assert "30 days" in page.locator("#cri-dialog-body").inner_text()
    assert "No qualified comparison yet" in page.locator("#cri-dialog-body").inner_text()
    page.close()


def test_r4_deep_link_and_older_snapshots_fail_open_with_honest_copy(browser):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.set_default_timeout(4500)
    page.goto(PAGE + "#overview?panel=scenario%3Aabsent")
    assert page.locator("#cri-dialog").evaluate("(element) => element.open")
    assert "Scenario unavailable" in page.locator("#cri-dialog-title").inner_text()
    page.locator("#cri-dialog-close").click()

    # Old device records may have scenario conditions without source-quality digest.
    scenario = page.evaluate("""() => JSON.parse(document.getElementById("cri-data").textContent).scenarios["30"][0]""")
    page.evaluate(
        """(entry) => localStorage.setItem("mmx.crypto.r4.scenarios.v1", JSON.stringify([entry]))""",
        scenario,
    )
    from urllib.parse import quote
    page.goto(PAGE + "#overview?panel=" + quote("saved-item:" + scenario["revision"]))
    assert "Evidence digest was not preserved" in page.locator("#cri-dialog-body").inner_text()
    assert scenario["as_of"] in page.locator("#cri-dialog-body").inner_text()
    page.close()


def test_r4_long_evidence_drawer_scrolls_on_short_mobile(browser):
    context = browser.new_context(
        viewport={"width": 390, "height": 568},
        is_mobile=True, has_touch=True, device_scale_factor=2,
    )
    page = context.new_page()
    page.goto(PAGE + "#overview?panel=evidence%3Aliquidity_flows")
    metrics = page.locator("#cri-dialog").evaluate("""element => {
      const before=element.scrollTop, contentHeight=element.scrollHeight, viewportHeight=element.clientHeight;
      element.scrollTop=element.scrollHeight;
      return {before, after:element.scrollTop, contentHeight, viewportHeight};
    }""")
    assert metrics["contentHeight"] > metrics["viewportHeight"]
    assert metrics["after"] > metrics["before"], metrics
    context.close()
