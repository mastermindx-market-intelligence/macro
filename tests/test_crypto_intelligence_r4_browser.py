"""Headless real-browser acceptance for the isolated Crypto R4 candidate.

Optional browser tooling: pytest skips only when Playwright/Chromium is not
installed. Run explicitly before release; unit tests alone are not visual proof.
"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading
from urllib.parse import quote, urlsplit

import pytest

playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Error, sync_playwright

SITE = Path(__file__).resolve().parents[1] / "site"
KEY = "mmx.crypto.r4.scenarios.v1"
_OBSERVATIONS = {"contexts": 0, "pages": 0, "page_errors": [], "blocked_external_requests": 0, "blocked_websockets": 0}


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        try:
            instance = p.chromium.launch(headless=True, executable_path=os.environ.get("MMX_CHROMIUM_EXECUTABLE"))
        except Error as exc:
            if os.environ.get("MMX_CHROMIUM_EXECUTABLE"):
                pytest.fail(f"Requested Chromium could not launch: {exc}")
            pytest.skip(f"Chromium not installed for R4 browser test: {exc}")
        _OBSERVATIONS["browser"] = instance.version
        yield instance
        instance.close()
        if os.environ.get("MMX_CRYPTO_SNAPSHOT_REPORT"):
            out = Path(os.environ["MMX_CRYPTO_SNAPSHOT_REPORT"])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(_OBSERVATIONS, ensure_ascii=False, indent=2) + "\n")
        assert _OBSERVATIONS["page_errors"] == [], _OBSERVATIONS["page_errors"]



@pytest.fixture(scope="module")
def page_url():
    """Exercise browser storage on an isolated HTTP origin, not file://."""
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(SITE)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/crypto-r4.html"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _observe_page(page):
    _OBSERVATIONS["pages"] += 1
    page.on("pageerror", lambda error: _OBSERVATIONS["page_errors"].append(str(error)))


def _configure_context(context, page_url):
    fixture = urlsplit(page_url)
    def route_request(route):
        target = urlsplit(route.request.url)
        if (target.scheme, target.netloc) == (fixture.scheme, fixture.netloc):
            route.continue_()
        else:
            _OBSERVATIONS["blocked_external_requests"] += 1
            route.abort()

    def block_socket(route):
        _OBSERVATIONS["blocked_websockets"] += 1
        route.close()

    context.route("**/*", route_request)
    context.route_web_socket("**/*", block_socket)
    context.on("page", _observe_page)
    _OBSERVATIONS["contexts"] += 1
    return context


def _context(browser, page_url, **options):
    return _configure_context(browser.new_context(**options), page_url)


def _page(browser, page_url, **options):
    page = browser.new_page(**options)
    _configure_context(page.context, page_url)
    _observe_page(page)
    return page


def _freeze_time(page, at="2026-10-18T12:00:00Z"):
    # Only Date is fixed; native timers, input and layout keep running.
    page.clock.set_fixed_time(datetime.fromisoformat(at.replace("Z", "+00:00")))


def _capture(page, name):
    if os.environ.get("MMX_CRYPTO_SNAPSHOT_CAPTURE_DIR"):
        out = Path(os.environ["MMX_CRYPTO_SNAPSHOT_CAPTURE_DIR"])
        out.mkdir(parents=True, exist_ok=True)
        page.locator("#cri-dialog").screenshot(path=str(out / (name + ".png")))


@pytest.fixture
def snapshot_page(browser, page_url, request):
    def create(lang="en", width=1440, at="2026-10-18T12:00:00Z"):
        context = _context(browser, page_url, viewport={"width": width, "height": 900 if width > 400 else 844})
        request.addfinalizer(context.close)
        page = context.new_page()
        page.set_default_timeout(4500)
        _freeze_time(page, at)
        page.add_init_script(
            "localStorage.setItem('lang'," + json.dumps(lang) + ");"
            "localStorage.setItem('theme'," + json.dumps("dark" if lang == "en" else "light") + ");"
        )
        page.goto(page_url + "?lang=" + lang + "#scenarios?h=30", wait_until="load")
        assert page.evaluate("new Date().toISOString()") == at.replace("Z", ".000Z")
        page.evaluate("""key => {
          window.__snapshotKey = key;
          window.__snapshotNativeGet = Storage.prototype.getItem;
          window.__snapshotNativeSet = Storage.prototype.setItem;
          window.__snapshotWrites = 0;
          Storage.prototype.setItem = function(k, value) {
            if (k === key) window.__snapshotWrites += 1;
            return window.__snapshotNativeSet.call(this, k, value);
          };
        }""", KEY)
        return page
    return create


def _scenario(page):
    return page.evaluate("JSON.parse(document.getElementById('cri-data').textContent).scenarios['30'][0]")


def _frozen(scenario):
    saved = deepcopy(scenario)
    saved["saved_at"] = "2026-10-17T22:00:00Z"
    saved["issue_evidence"] = {
        "bitcoin_as_of": "2026-10-16", "market_as_of": "2026-10-14",
        "families": [{"id": "fixture-original", "label_en": "Original evidence",
                      "label_zh": "原始证据", "state_en": "Retained", "state_zh": "保留",
                      "quality": "stale", "snapshot_as_of": "2026-10-14",
                      "source": "Synthetic retained evidence; not a current observation."}],
    }
    return saved


def _seed(page, entries):
    page.evaluate("(entries) => __snapshotNativeSet.call(localStorage, __snapshotKey, JSON.stringify(entries))", entries)


def _raw(page):
    return page.evaluate("__snapshotNativeGet.call(localStorage, __snapshotKey)")


def _entries(page):
    return json.loads(_raw(page))


def _writes(page):
    return page.evaluate("__snapshotWrites")


def _open_scenario(page):
    page.locator('[data-open="scenario:continuation"]:visible').first.click()


def _open_panel(page, panel):
    page.evaluate("""panel => new Promise(resolve => {
      const parts = location.hash.slice(1).split("?"), params = new URLSearchParams(parts.slice(1).join("?"));
      params.set("panel", panel);
      const next = "#scenarios?" + params.toString();
      if (location.hash === next) { resolve(); return; }
      // The application's earlier hashchange listener renders synchronously.
      window.addEventListener("hashchange", () => resolve(), {once: true});
      location.hash = next;
    })""", panel)
    assert page.locator("#cri-dialog").evaluate("element => element.open")


def _open_saved(page, revision, kind="saved-item"):
    _open_panel(page, kind + ":" + revision)


def _assert_uncertain(page, lang="en"):
    text = page.locator("#cri-toast").inner_text()
    assert ("couldn’t be confirmed" if lang == "en" else "无法确认更改结果") in text
    assert ("Removed from this device." if lang == "en" else "已从本设备移除。") not in text
    assert ("Saved on this device." if lang == "en" else "已保存至本设备。") not in text


def test_r4_four_views_locales_themes_and_mobile_layout(browser, page_url):
    for width in (1440, 390):
        context = _context(browser, page_url, viewport={"width": width, "height": 844}, is_mobile=width == 390, has_touch=width == 390, device_scale_factor=2 if width == 390 else 1)
        page = context.new_page()
        page.set_default_timeout(4500)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(page_url, wait_until="load")
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


def test_r4_horizon_deep_link_drawer_history_and_chart_window(browser, page_url):
    context = _context(browser, page_url, viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
    page = context.new_page()
    page.set_default_timeout(4500)
    page.goto(page_url + "#scenarios?h=30")
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


def test_r4_saved_snapshot_retains_horizon_and_original_cutoff(browser, page_url):
    page = _page(browser, page_url, viewport={"width": 1440, "height": 900})
    page.set_default_timeout(4500)
    # Synthetic time anchored to the dated demonstration artifact, not market time.
    _freeze_time(page)
    page.goto(page_url + "#scenarios?h=30")
    page.locator('[data-open="scenario:continuation"]:visible').first.click()
    assert not page.locator('[data-snapshot-action]').is_disabled()
    original_cutoff = page.locator("#cri-dialog-body .cri-note").first.inner_text()
    page.locator('[data-snapshot-action]').click()
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


def test_r4_deep_link_and_older_snapshots_fail_open_with_honest_copy(browser, page_url):
    page = _page(browser, page_url, viewport={"width": 390, "height": 844})
    page.set_default_timeout(4500)
    page.goto(page_url + "#overview?panel=scenario%3Aabsent")
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
    page.goto(page_url + "#overview?panel=" + quote("saved-item:" + scenario["revision"]))
    assert "Evidence digest was not preserved" in page.locator("#cri-dialog-body").inner_text()
    assert scenario["as_of"] in page.locator("#cri-dialog-body").inner_text()
    page.close()


def test_r4_long_evidence_drawer_scrolls_on_short_mobile(browser, page_url):
    context = _context(browser, page_url, 
        viewport={"width": 390, "height": 568},
        is_mobile=True, has_touch=True, device_scale_factor=2,
    )
    page = context.new_page()
    page.goto(page_url + "#overview?panel=evidence%3Aliquidity_flows")
    metrics = page.locator("#cri-dialog").evaluate("""element => {
      const before=element.scrollTop, contentHeight=element.scrollHeight, viewportHeight=element.clientHeight;
      element.scrollTop=element.scrollHeight;
      return {before, after:element.scrollTop, contentHeight, viewportHeight};
    }""")
    assert metrics["contentHeight"] > metrics["viewportHeight"]
    assert metrics["after"] > metrics["before"], metrics
    context.close()


@pytest.mark.parametrize("intent", ["save", "remove", "remove_expired"])
@pytest.mark.parametrize("lang,width", [("en", 1440), ("zh", 390)])
def test_r4_snapshot_buttons_keep_their_visible_intent_across_tabs(snapshot_page, page_url, intent, lang, width):
    page = snapshot_page(lang, width, "2026-12-01T12:00:00Z" if intent == "remove_expired" else "2026-10-18T12:00:00Z")
    source = _scenario(page)
    frozen = _frozen(source)
    opaque = {"format": "future", "payload": [0, False, None, {"keep": "exact"}]}
    if intent == "save":
        _open_scenario(page)
        action = page.locator("[data-snapshot-action]")
        # Include an oversized retained set: an idempotent Save must not trim it.
        retained = [opaque, frozen] + [dict(frozen, revision=f"other:{i}") for i in range(55)]
    else:
        _seed(page, [opaque, frozen])
        _open_saved(page, source["revision"])
        action = page.locator('[data-snapshot-action="remove"]')
        retained = [opaque]

    other = page.context.new_page()
    other.goto(page_url + "#overview", wait_until="load")
    other.evaluate("(value) => localStorage.setItem('mmx.crypto.r4.scenarios.v1', JSON.stringify(value))", retained)
    before = _raw(page)
    action.click()  # Native action on a control rendered before the other tab wrote.
    if intent == "remove":
        _capture(page, "stale-remove-" + str(width) + "-" + lang)
    assert _writes(page) == 0, "A stale explicit intent must complete without another write"
    assert _raw(page) == before, "Frozen evidence and unrelated records must remain byte-exact on no-op"
    message = page.locator("#cri-toast").inner_text()
    if intent == "save":
        assert ("Already saved" if lang == "en" else "已保存此快照") in message
        assert page.locator('[data-snapshot-action="remove"]').evaluate("element => document.activeElement === element")
    else:
        assert ("no longer saved" if lang == "en" else "已无此快照") in message
        assert page.evaluate("new URLSearchParams(location.hash.split('?')[1]).get('panel')") == "saved"
    other.close()


@pytest.mark.parametrize("lang,width", [("en", 1440), ("zh", 390)])
def test_r4_remove_all_exact_matches_preserves_the_full_collection(snapshot_page, lang, width):
    page = snapshot_page(lang, width)
    target = _frozen(_scenario(page))
    unrelated = [dict(target, revision=f"retained:{i}", saved_at=f"old-{i}") for i in range(60)]
    opaque = [None, "unrecognized", {"authority": "future", "revision": "future:1", "nested": [False, 0]}]
    original = [opaque[0], target] + unrelated[:50] + [opaque[1], dict(target, saved_at="duplicate")] + unrelated[50:] + [opaque[2]]
    _seed(page, original)
    _open_scenario(page)
    action = page.locator("[data-snapshot-action]")
    action.focus()
    page.keyboard.press("Enter")
    assert _writes(page) == 1
    assert _entries(page) == [opaque[0]] + unrelated[:50] + [opaque[1]] + unrelated[50:] + [opaque[2]]
    assert page.locator('[data-snapshot-action="save"]').evaluate("element => document.activeElement === element")


@pytest.mark.parametrize("failure,lang,width", [
    ("malformed", "en", 1440), ("object", "en", 1440), ("null", "en", 1440),
    ("empty", "en", 1440), ("access", "en", 1440), ("nonfinite", "en", 1440),
    ("malformed", "zh", 390),
])
def test_r4_unreadable_collection_is_not_empty_and_retry_only_reads(snapshot_page, page_url, failure, lang, width):
    page = snapshot_page(lang, width)
    revision = _scenario(page)["revision"]
    raw = {"malformed": "{bad-json", "object": "{}", "null": "null", "empty": "", "nonfinite": "[1e400]"}.get(failure, "[]")
    page.evaluate("(raw) => __snapshotNativeSet.call(localStorage, __snapshotKey, raw)", raw)
    if failure == "access":
        page.evaluate("""() => {
          Storage.prototype.getItem = function(key) {
            if (key === __snapshotKey) throw new DOMException("Synthetic read denial", "SecurityError");
            return __snapshotNativeGet.call(this, key);
          };
        }""")
    for panel in ("saved", "saved-item:" + revision, "memory-saved:" + revision):
        _open_panel(page, panel)
        assert ("couldn’t be read" if lang == "en" else "无法读取") in page.locator("#cri-dialog-body").inner_text()
        assert ("Nothing saved yet" if lang == "en" else "尚未保存") not in page.locator("#cri-dialog-body").inner_text()
        assert page.locator("[data-snapshot-action]").count() == 0
    if failure == "malformed":
        _capture(page, "unreadable-" + str(width) + "-" + lang)
    assert _writes(page) == 0
    assert _raw(page) == raw

    before_url, before_history = page.url, page.evaluate("history.length")
    page.evaluate("() => {Storage.prototype.getItem=__snapshotNativeGet;__snapshotNativeSet.call(localStorage,__snapshotKey,'[]')}")
    page.get_by_role("button", name="Try reading again" if lang == "en" else "重试读取", exact=True).click()
    assert page.url == before_url and page.evaluate("history.length") == before_history
    assert _writes(page) == 0 and _raw(page) == "[]"
    # A missing requested version remains unavailable; it never borrows current context.
    assert ("Scenario unavailable" if lang == "en" else "情景暂不可用") in page.locator("#cri-dialog-title").inner_text()
    assert _scenario(page)["as_of"] not in page.locator("#cri-dialog-body").inner_text()


@pytest.mark.parametrize("failure,lang,width", [
    ("throw_before", "en", 1440), ("write_then_throw", "en", 1440),
    ("drop", "en", 1440), ("readback_throw", "en", 1440), ("mismatch", "en", 1440),
    ("write_then_throw", "zh", 390),
])
def test_r4_uncertain_write_is_not_success_or_an_automatic_retry(snapshot_page, failure, lang, width):
    page = snapshot_page(lang, width)
    target = _frozen(_scenario(page))
    _seed(page, [target, {"opaque": "keep"}])
    _open_saved(page, target["revision"])
    before_url = page.url
    page.evaluate("""mode => {
      let attempted = false;
      Storage.prototype.setItem = function(key, value) {
        if (key !== __snapshotKey) return __snapshotNativeSet.call(this, key, value);
        __snapshotWrites += 1; attempted = true;
        if (mode === "throw_before") throw new DOMException("Synthetic quota failure", "QuotaExceededError");
        if (mode === "drop") return;
        __snapshotNativeSet.call(this, key, value);
        if (mode === "write_then_throw") throw new Error("Synthetic ambiguous completion");
        if (mode === "mismatch") __snapshotNativeSet.call(this, key, '[{"concurrent":"retained"}]');
      };
      Storage.prototype.getItem = function(key) {
        if (key === __snapshotKey && attempted && mode === "readback_throw") throw new Error("Synthetic readback failure");
        return __snapshotNativeGet.call(this, key);
      };
    }""", failure)
    page.locator('[data-snapshot-action="remove"]').click()
    _assert_uncertain(page, lang)
    assert _writes(page) == 1 and page.url == before_url
    assert page.locator('[data-snapshot-action="remove"]').evaluate("element => document.activeElement === element")
    if failure in ("throw_before", "write_then_throw"):
        _capture(page, "unconfirmed-" + failure + "-" + str(width) + "-" + lang)


def test_r4_confirmed_remove_can_be_followed_by_an_unreadable_list(snapshot_page):
    page = snapshot_page()
    target = _frozen(_scenario(page))
    _seed(page, [target])
    _open_saved(page, target["revision"])
    page.evaluate("""() => {
      let reads = 0;
      Storage.prototype.getItem = function(key) {
        if (key === __snapshotKey && ++reads >= 3) throw new Error("Synthetic later list read failure");
        return __snapshotNativeGet.call(this, key);
      };
    }""")
    page.locator('[data-snapshot-action="remove"]').click()
    assert _writes(page) == 1 and _entries(page) == []
    assert page.locator("#cri-toast").inner_text() == "Removed from this device."
    assert "couldn’t be read" in page.locator("#cri-dialog-body").inner_text()
    assert "No changes were made" not in page.locator("#cri-dialog-body").inner_text()
    assert page.evaluate("new URLSearchParams(location.hash.split('?')[1]).get('panel')") == "saved"


def test_r4_new_save_alone_applies_capacity_and_keeps_opaque_entries(snapshot_page):
    page = snapshot_page()
    source = _scenario(page)
    old = [dict(_frozen(source), revision=f"old:{i}") for i in range(51)]
    opaque = {"future": [None, False, 0, {"keep": "exact"}]}
    original = [opaque] + old[:1] + ["legacy"] + old[1:]
    _seed(page, original)
    _open_scenario(page)
    page.locator("[data-snapshot-action]").click()
    after = _entries(page)
    assert _writes(page) == 1 and len(after) == 52
    assert after[:-1] == [opaque, "legacy"] + old[2:]
    assert after[-1]["revision"] == source["revision"]
    assert after[-1]["as_of"] == source["as_of"] and after[-1]["horizon_days"] == 30
    assert after[-1]["saved_at"] == "2026-10-18T12:00:00.000Z"
    assert after[-1]["issue_evidence"]["bitcoin_as_of"] == "2026-10-17"


@pytest.mark.parametrize("kind", ["missing", "duplicates", "bad_horizon", "bad_date", "missing_condition", "wrong_authority"])
def test_r4_unusable_saved_version_never_borrows_current_context(snapshot_page, kind):
    page = snapshot_page()
    target = _frozen(_scenario(page))
    entries = [deepcopy(target)]
    if kind == "missing":
        entries = []
    elif kind == "duplicates":
        entries.append(dict(target, saved_at="another-copy"))
    elif kind == "bad_horizon":
        entries[0]["horizon_days"] = 90
    elif kind == "bad_date":
        entries[0]["as_of"] = "2026-02-30"
    elif kind == "missing_condition":
        del entries[0]["condition_en"]
    else:
        entries[0]["authority"] = "future"
    _seed(page, entries)
    before = _raw(page)
    for panel in ("saved-item", "memory-saved"):
        _open_saved(page, target["revision"], panel)
        assert page.locator("#cri-dialog-title").inner_text() == "Scenario unavailable"
        assert target["as_of"] not in page.locator("#cri-dialog-body").inner_text()
        assert "No qualified comparison yet" not in page.locator("#cri-dialog-body").inner_text()
    assert _writes(page) == 0 and _raw(page) == before


@pytest.mark.parametrize("intent", ["save", "remove"])
def test_r4_newer_focus_during_confirmation_survives(snapshot_page, intent):
    page = snapshot_page()
    source = _scenario(page)
    if intent == "remove":
        _seed(page, [_frozen(source)])
        _open_saved(page, source["revision"])
    else:
        _open_scenario(page)
    page.evaluate("""() => {
      let wrote = false;
      const set = Storage.prototype.setItem;
      Storage.prototype.setItem = function(key, value) {
        const result = set.call(this, key, value);
        if (key === __snapshotKey) wrote = true;
        return result;
      };
      Storage.prototype.getItem = function(key) {
        if (key === __snapshotKey && wrote) {
          wrote = false;
          const target = [...document.querySelectorAll('#cri-dialog-body button')].find(n => n.textContent === 'Historical review');
          window.__newerFocus = target; target.focus();
        }
        return __snapshotNativeGet.call(this, key);
      };
    }""")
    before_url = page.url
    page.locator("[data-snapshot-action]").click()
    assert _writes(page) == 1
    assert page.url == before_url
    assert page.evaluate("__newerFocus.isConnected && document.activeElement === __newerFocus")
    assert len(_entries(page)) == (1 if intent == "save" else 0)
    assert page.locator("#cri-toast").inner_text() == ("Saved on this device." if intent == "save" else "Removed from this device.")


@pytest.mark.parametrize("path", ["frozen-remove", "current-save"])
def test_r4_completion_focus_callbacks_keep_their_new_panel(snapshot_page, path):
    page = snapshot_page()
    source = _scenario(page)
    if path == "frozen-remove":
        _seed(page, [_frozen(source)])
        _open_saved(page, source["revision"])
    else:
        _open_scenario(page)
    page.evaluate("""path => {
      let done = false;
      document.addEventListener('focusin', event => {
        const target = event.target;
        const chosen = path === 'frozen-remove' ? target.id === 'cri-dialog-close' :
          target.hasAttribute('data-snapshot-action') && target.textContent === 'Remove snapshot';
        if (done || !chosen) return;
        done = true;
        document.querySelector('[data-open="evidence:liquidity_flows"]').click();
        window.__callbackFocus = document.querySelector('#cri-dialog-body summary');
        __callbackFocus.focus();
      });
    }""", path)
    page.locator("[data-snapshot-action]").click()
    assert _writes(page) == 1
    assert page.evaluate("new URLSearchParams(location.hash.split('?')[1]).get('panel')") == "evidence:liquidity_flows"
    assert page.evaluate("Boolean(window.__callbackFocus) && __callbackFocus.isConnected && document.activeElement === __callbackFocus")


def test_r4_programmatic_save_preserves_unrelated_focus_and_stale_save_stays_safe(snapshot_page):
    page = snapshot_page()
    _open_scenario(page)
    review = page.locator("#cri-dialog-body").get_by_role("button", name="Historical review", exact=True)
    review.focus()
    page.locator("[data-snapshot-action]").evaluate("element => element.click()")
    saved = _raw(page)
    assert _writes(page) == 1 and review.evaluate("element => document.activeElement === element")
    # The un-replaced stale Save remains an explicit Save when the user activates it.
    page.locator("[data-snapshot-action]").click()
    assert _writes(page) == 1 and _raw(page) == saved
    assert page.locator("#cri-toast").inner_text() == "Already saved on this device."


def test_r4_removing_last_usable_snapshot_does_not_claim_collection_unchanged(snapshot_page):
    page = snapshot_page(width=390)
    target = _frozen(_scenario(page))
    opaque = {"future": [0, False, None]}
    _seed(page, [target, opaque])
    _open_saved(page, target["revision"])
    page.locator('[data-snapshot-action="remove"]').click()
    assert _writes(page) == 1 and _entries(page) == [opaque]
    assert page.locator("#cri-toast").inner_text() == "Removed from this device."
    assert "No supported snapshots can be opened here." in page.locator("#cri-dialog-body").inner_text()
    assert "unchanged" not in page.locator("#cri-dialog-body").inner_text()
    _capture(page, "removed-preserved-opaque-390-en")
