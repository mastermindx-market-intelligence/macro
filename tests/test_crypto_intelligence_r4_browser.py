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
    def create(lang="en", width=1440, at="2026-10-18T12:00:00Z", start="#scenarios?h=30"):
        context = _context(browser, page_url, viewport={"width": width, "height": 900 if width > 400 else 844})
        request.addfinalizer(context.close)
        page = context.new_page()
        page.set_default_timeout(4500)
        _freeze_time(page, at)
        page.add_init_script(
            "localStorage.setItem('lang'," + json.dumps(lang) + ");"
            "localStorage.setItem('theme'," + json.dumps("dark" if lang == "en" else "light") + ");"
        )
        page.goto(page_url + "?lang=" + lang + start, wait_until="load")
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
    assert page.locator("#cri-dialog-body").get_by_text(saved[0]["condition_en"], exact=True).is_visible()
    assert page.locator('[data-drawer-disclosure="saved-evidence"] > summary').inner_text().startswith("Original evidence")
    assert saved[0]["as_of"] in page.locator("#cri-dialog-body").inner_text()
    assert str(saved[0]["horizon_days"]) + " days" in page.locator("#cri-dialog-body").inner_text()
    page.locator("#cri-dialog-body details").last.evaluate("(element) => element.open = true")
    assert "Stale at capture" in page.locator("#cri-dialog-body").inner_text()
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


def _wait_drawer(page, panel, title):
    page.wait_for_function(
        """expected => new URLSearchParams(location.hash.split('?')[1]).get('panel') === expected.panel &&
          document.getElementById('cri-dialog').open &&
          document.getElementById('cri-dialog-title').textContent === expected.title""",
        arg={"panel": panel, "title": title},
    )


def _wait_closed(page):
    page.wait_for_function("""() => !document.getElementById('cri-dialog').open &&
      !new URLSearchParams(location.hash.split('?')[1]).has('panel')""")


def _open_saved_from_list(page, target, lang="en"):
    page.locator('#crypto-intelligence [data-open="saved"]').click()
    label = target["title_" + lang] + " · 30" + (" days" if lang == "en" else "天") + " · " + target["as_of"]
    page.locator("#cri-dialog-body").get_by_role("button", name=label, exact=True).click()


def _review_saved(page, lang="en"):
    page.locator("#cri-dialog-body").get_by_role(
        "button", name="Historical review" if lang == "en" else "历史检验", exact=True,
    ).click()


def _saved_parent(page, lang="en", detached=False):
    label = ("Open saved case" if detached else "← Saved case") if lang == "en" else ("打开已存情景" if detached else "← 已存情景")
    control = page.locator("#cri-dialog").get_by_role("button", name=label, exact=True)
    assert control.count() == 1, "Historical review needs the correct explicit same-case destination"
    return control


def _long_frozen(page):
    target = _frozen(_scenario(page))
    family = target["issue_evidence"]["families"][0]
    target["issue_evidence"]["families"] = [
        dict(family, id=f"synthetic-{i}", label_en=f"Original evidence {i + 1}", label_zh=f"原始证据{i + 1}")
        for i in range(12)
    ]
    return target


@pytest.mark.parametrize("lang,width", [("en", 1440), ("zh", 390), ("en", 320)])
def test_r4_saved_journey_restores_the_exact_outer_horizon(snapshot_page, lang, width):
    page = snapshot_page(lang, width, start="#scenarios?h=7&window=30&q=BTC&filter=all&sort=symbol")
    target = _long_frozen(page)
    _seed(page, [target])
    original_url, original_history, original_raw = page.url, page.evaluate("history.length"), _raw(page)
    opener = page.locator('#crypto-intelligence [data-open="saved"]')
    _open_saved_from_list(page, target, lang)
    assert page.evaluate("new URLSearchParams(location.hash.split('?')[1]).get('h')") == "30"
    assert target["as_of"] in page.locator("#cri-dialog-body").inner_text()
    assert target["condition_" + lang] in page.locator("#cri-dialog-body").text_content()
    for disclosure in page.locator("#cri-dialog-body details").all():
        disclosure.locator("summary").click()
    review = page.locator("#cri-dialog-body").get_by_role("button", name="Historical review" if lang == "en" else "历史检验", exact=True)
    review.scroll_into_view_if_needed()
    review.focus()
    saved_scroll = page.locator("#cri-dialog").evaluate("node => node.scrollTop")
    review.click()
    assert page.evaluate("new URLSearchParams(location.hash.split('?')[1]).get('h')") == "30"
    assert target["as_of"] in page.locator("#cri-dialog-body").inner_text()
    child_history = page.evaluate("history.length")
    _saved_parent(page, lang).click()
    _wait_drawer(page, "saved-item:" + target["revision"], target["title_" + lang])
    assert page.evaluate("history.length") == child_history == original_history + 3
    assert page.evaluate("new URLSearchParams(location.hash.split('?')[1]).get('h')") == "30"
    assert page.locator("#cri-dialog-body details").evaluate_all("nodes => nodes.every(node => node.open)")
    assert review.evaluate("node => document.activeElement === node")
    assert abs(page.locator("#cri-dialog").evaluate("node => node.scrollTop") - saved_scroll) <= 1
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.locator("#cri-dialog").evaluate("node => node.scrollWidth <= node.clientWidth + 1")
    header_controls = page.locator(".cri-dialog-header button")
    assert header_controls.count() == 2
    for control in header_controls.all():
        assert control.bounding_box()["height"] >= 44
    _capture(page, "navigation-return-" + str(width) + "-" + lang)

    page.go_back()
    _wait_drawer(page, "saved", "Saved snapshots" if lang == "en" else "已存快照")
    assert page.evaluate("new URLSearchParams(location.hash.split('?')[1]).get('h')") == "7"
    page.go_forward()
    _wait_drawer(page, "saved-item:" + target["revision"], target["title_" + lang])
    assert page.evaluate("new URLSearchParams(location.hash.split('?')[1]).get('h')") == "30"
    assert page.locator("#cri-dialog-body details").evaluate_all("nodes => nodes.every(node => node.open)")
    page.locator("#cri-dialog-close").click()
    _wait_closed(page)
    assert page.url == original_url
    assert opener.evaluate("node => document.activeElement === node")
    assert _raw(page) == original_raw and _writes(page) == 0


def test_r4_detached_saved_item_still_has_a_real_review_parent(snapshot_page):
    page = snapshot_page(width=390, start="#scenarios?h=7")
    target = _frozen(_scenario(page))
    _seed(page, [target])
    _open_saved(page, target["revision"])
    _review_saved(page)
    assert page.evaluate("history.state.detachedOrigin") is True
    before_history = page.evaluate("history.length")
    _saved_parent(page).click()
    _wait_drawer(page, "saved-item:" + target["revision"], target["title_en"])
    assert page.evaluate("history.length") == before_history
    assert page.evaluate("new URLSearchParams(location.hash.split('?')[1]).get('h')") == "30"
    page.locator("#cri-dialog-close").click()
    _wait_closed(page)
    assert page.evaluate("new URLSearchParams(location.hash.split('?')[1]).get('h')") == "30"
    assert _writes(page) == 0


@pytest.mark.parametrize("lang,width", [("en", 1440), ("zh", 320)])
def test_r4_truly_detached_review_opens_exact_saved_case_by_replace(snapshot_page, lang, width):
    page = snapshot_page(lang, width, start="#scenarios?h=7&window=30")
    target = _frozen(_scenario(page))
    _seed(page, [target])
    _open_saved(page, target["revision"], "memory-saved")
    before_history = page.evaluate("history.length")
    _saved_parent(page, lang, detached=True).click()
    _wait_drawer(page, "saved-item:" + target["revision"], target["title_" + lang])
    assert page.evaluate("history.length") == before_history
    assert page.evaluate("new URLSearchParams(location.hash.split('?')[1]).get('h')") == "30"
    assert target["as_of"] in page.locator("#cri-dialog-body").inner_text()
    page.locator("#cri-dialog-close").click()
    _wait_closed(page)
    assert page.evaluate("new URLSearchParams(location.hash.split('?')[1]).get('h')") == "30"
    assert _writes(page) == 0


@pytest.mark.parametrize("width", [1440, 320])
def test_r4_saved_locale_keeps_disclosure_focus_and_reading_position(snapshot_page, width):
    page = snapshot_page(width=width)
    target = _long_frozen(page)
    _seed(page, [target])
    _open_saved_from_list(page, target)
    for disclosure in page.locator("#cri-dialog-body details").all():
        disclosure.locator("summary").click()
    evidence_summary = page.locator("#cri-dialog-body details").last.locator("summary")
    evidence_summary.focus()
    page.locator("#cri-dialog").evaluate("node => node.scrollTop = 240")
    before_scroll = page.locator("#cri-dialog").evaluate("node => node.scrollTop")
    assert before_scroll > 0
    before_url, before_history, before_raw = page.url, page.evaluate("history.length"), _raw(page)
    for lang in ("zh", "en"):
        page.locator("html").evaluate("(node, lang) => node.dataset.lang = lang", lang)
        page.wait_for_function("title => document.getElementById('cri-dialog-title').textContent === title", arg=target["title_" + lang])
        assert page.locator("#cri-dialog-body details").evaluate_all("nodes => nodes.length === 2 && nodes.every(node => node.open)")
        assert evidence_summary.evaluate("node => document.activeElement === node")
        assert abs(page.locator("#cri-dialog").evaluate("node => node.scrollTop") - before_scroll) <= 1
        assert page.url == before_url and page.evaluate("history.length") == before_history
        assert _raw(page) == before_raw and _writes(page) == 0


@pytest.mark.parametrize("failure", ["missing", "duplicate", "unreadable"])
def test_r4_saved_parent_rechecks_the_requested_record_before_return(snapshot_page, failure):
    page = snapshot_page(start="#scenarios?h=7")
    target = _frozen(_scenario(page))
    _seed(page, [target])
    _open_saved_from_list(page, target)
    _review_saved(page)
    parent = _saved_parent(page)
    if failure == "unreadable":
        page.evaluate("() => __snapshotNativeSet.call(localStorage,__snapshotKey,'{unreadable')")
    else:
        _seed(page, [] if failure == "missing" else [target, deepcopy(target)])
    before_raw, before_url, before_history = _raw(page), page.url, page.evaluate("history.length")
    parent.click()
    if failure == "unreadable":
        assert page.url == before_url
        assert page.locator("#cri-dialog-title").inner_text() == "Saved snapshots unavailable"
        assert page.locator("#cri-dialog-title").evaluate("node => document.activeElement===node")
        assert target["as_of"] not in page.locator("#cri-dialog-body").inner_text()
    else:
        assert page.url == before_url
        assert page.locator("#cri-dialog-title").inner_text() == "Scenario unavailable"
        assert page.locator("#cri-dialog-title").evaluate("node => document.activeElement===node")
        assert target["as_of"] not in page.locator("#cri-dialog-body").inner_text()
        page.locator("#cri-dialog-body").get_by_role("button", name="Open saved snapshots", exact=True).click()
        _wait_drawer(page, "saved", "Saved snapshots")
        assert page.evaluate("history.length") == before_history
    assert _raw(page) == before_raw and _writes(page) == 0


def test_r4_locale_change_does_not_restore_a_removed_saved_case(snapshot_page):
    page = snapshot_page(width=390)
    target = _long_frozen(page)
    _seed(page, [target])
    _open_saved_from_list(page, target)
    for disclosure in page.locator("#cri-dialog-body details").all():
        disclosure.locator("summary").click()
    _seed(page, [])
    page.locator("html").evaluate("node => node.dataset.lang='zh'")
    page.wait_for_function("() => document.getElementById('cri-dialog-title').textContent === '情景暂不可用'")
    assert page.locator("#cri-dialog-title").evaluate("node => document.activeElement===node")
    assert page.locator("#cri-dialog-body details").count() == 0
    assert target["as_of"] not in page.locator("#cri-dialog-body").inner_text()
    recovery = page.locator("#cri-dialog-body").get_by_role("button", name="查看已存快照", exact=True)
    assert recovery.count() == 1
    recovery.click()
    _wait_drawer(page, "saved", "已存快照")
    assert _raw(page) == "[]" and _writes(page) == 0


@pytest.mark.parametrize("opener_state", ["hidden", "removed"])
def test_r4_close_falls_back_to_the_restored_active_view_heading(snapshot_page, opener_state):
    page = snapshot_page(start="#scenarios?h=7&window=30")
    target = _frozen(_scenario(page))
    _seed(page, [target])
    original_url = page.url
    _open_saved_from_list(page, target)
    _review_saved(page)
    page.locator('#crypto-intelligence [data-open="saved"]').evaluate(
        "(node, state) => { if(state==='removed') node.remove(); else node.hidden=true; }", opener_state,
    )
    page.locator("#cri-dialog-close").click()
    _wait_closed(page)
    assert page.url == original_url
    assert page.evaluate("""() => {
      const active=document.activeElement;
      return active.matches('h1,h2') && active.closest('[data-view="scenarios"]') &&
        active.getClientRects().length > 0;
    }""")
    assert _writes(page) == 0


def test_r4_saved_parent_focus_callback_keeps_its_new_destination(snapshot_page):
    page = snapshot_page(start="#scenarios?h=7")
    target = _long_frozen(page)
    _seed(page, [target])
    _open_saved_from_list(page, target)
    for disclosure in page.locator("#cri-dialog-body details").all():
        disclosure.locator("summary").click()
    _review_saved(page)
    parent = _saved_parent(page)
    page.evaluate("""() => {
      let done=false;
      document.addEventListener('focusin', event => {
        if(done || event.target.textContent!=='Historical review' ||
           !document.getElementById('cri-dialog-body').contains(event.target)) return;
        done=true;
        document.querySelector('#crypto-intelligence [data-open="evidence:liquidity_flows"]').click();
        window.__navigationNewFocus=document.querySelector('#cri-dialog-body summary');
        __navigationNewFocus.focus();
      });
    }""")
    parent.click()
    _wait_drawer(page, "evidence:liquidity_flows", "Evidence behind the view")
    assert page.evaluate("__navigationNewFocus.isConnected && document.activeElement===__navigationNewFocus")
    assert _writes(page) == 0


def test_r4_legacy_saved_parent_horizon_is_repaired_in_the_same_entry(snapshot_page):
    page = snapshot_page(start="#scenarios?h=7&window=30")
    target = _frozen(_scenario(page))
    _seed(page, [target])
    original_url = page.url
    _open_saved_from_list(page, target)
    depth = page.evaluate("history.state.depth")
    # Reproduce an old parent entry whose visible saved case was 30-day but URL was 7-day.
    page.evaluate("""() => {
      const params=new URLSearchParams(location.hash.split('?')[1]);params.set('h','7');
      history.replaceState(history.state,'','#scenarios?'+params.toString());
    }""")
    before_history = page.evaluate("history.length")
    _review_saved(page)
    assert page.evaluate("new URLSearchParams(history.state.previous.split('?')[1]).get('h')") == "30"
    assert page.evaluate("history.length") == before_history + 1
    _saved_parent(page).click()
    _wait_drawer(page, "saved-item:" + target["revision"], target["title_en"])
    assert page.evaluate("history.state.depth") == depth
    assert page.evaluate("new URLSearchParams(location.hash.split('?')[1]).get('h')") == "30"
    assert page.locator("#cri-dialog-body").get_by_role("button", name="Historical review", exact=True).evaluate("node => document.activeElement===node")
    page.locator("#cri-dialog-close").click()
    _wait_closed(page)
    assert page.url == original_url and _writes(page) == 0


def test_r4_same_url_history_entries_restore_their_own_reading_state(snapshot_page):
    page = snapshot_page(width=390)
    target = _long_frozen(page)
    _seed(page, [target])
    _open_saved_from_list(page, target)
    for disclosure in page.locator("#cri-dialog-body details").all():
        disclosure.locator("summary").click()
    summary = page.locator("#cri-dialog-body details").last.locator("summary")
    summary.focus()
    page.locator("#cri-dialog").evaluate("node => node.scrollTop=240")
    page.locator("html").evaluate("node => node.dataset.lang='zh'")
    page.wait_for_function("title => document.getElementById('cri-dialog-title').textContent===title", arg=target["title_zh"])
    retained = page.evaluate("history.state.reading")
    assert retained["scroll"] == 240 and len(retained["disclosures"]) == 2
    first_depth = page.evaluate("history.state.depth")
    page.evaluate("""() => {
      const next=structuredClone(history.state);
      next.depth+=1;next.previous=location.hash;
      next.reading={...next.reading,disclosures:[],focus:'review',scroll:0};
      history.pushState(next,'',location.href);
    }""")
    page.go_back()
    page.wait_for_function("depth => history.state.depth===depth", arg=first_depth)
    page.go_forward()
    page.wait_for_function("() => [...document.querySelectorAll('#cri-dialog-body details')].every(node=>!node.open)")
    review = page.locator("#cri-dialog-body").get_by_role("button", name="历史检验", exact=True)
    assert review.evaluate("node => document.activeElement===node")
    assert page.locator("#cri-dialog").evaluate("node => node.scrollTop") == 0
    page.go_back()
    page.wait_for_function("() => [...document.querySelectorAll('#cri-dialog-body details')].every(node=>node.open)")
    assert summary.evaluate("node => document.activeElement===node")
    assert page.locator("#cri-dialog").evaluate("node => node.scrollTop") == 240
    assert _writes(page) == 0


def test_r4_saved_case_disappearing_during_back_does_not_restore_stale_content(snapshot_page):
    page = snapshot_page(start="#scenarios?h=7&window=30")
    target = _long_frozen(page)
    _seed(page, [target])
    original_url = page.url
    _open_saved_from_list(page, target)
    for disclosure in page.locator("#cri-dialog-body details").all():
        disclosure.locator("summary").click()
    _review_saved(page)
    parent = _saved_parent(page)
    page.evaluate("""() => {
      const back = history.back.bind(history);
      window.__snapshotParentBackCalls = 0;
      history.back = function() {
        history.back = back;
        __snapshotParentBackCalls++;
        __snapshotNativeSet.call(localStorage,__snapshotKey,'[]');
        return back();
      };
    }""")
    parent.click()
    _wait_drawer(page, "saved-item:" + target["revision"], "Scenario unavailable")
    assert page.evaluate("__snapshotParentBackCalls") == 1
    assert page.locator("#cri-dialog-title").evaluate("node => document.activeElement===node")
    assert page.locator("#cri-dialog-body details").count() == 0
    assert target["as_of"] not in page.locator("#cri-dialog-body").inner_text()
    assert page.locator("#cri-dialog-body").get_by_role("button", name="Open saved snapshots", exact=True).count() == 1
    assert _raw(page) == "[]" and _writes(page) == 0
    page.locator("#cri-dialog-close").click()
    _wait_closed(page)
    assert page.url == original_url


@pytest.mark.parametrize("destination", ["saved", "scenario", "saved-retry-focus"])
def test_r4_storage_preflight_yields_to_newer_navigation_or_focus(snapshot_page, destination):
    page = snapshot_page()
    if destination == "saved-retry-focus":
        page.evaluate("() => __snapshotNativeSet.call(localStorage,__snapshotKey,'{unreadable')")
        page.locator('#crypto-intelligence [data-open="saved"]').click()
        assert page.locator("#cri-dialog-title").inner_text() == "Saved snapshots unavailable"
        page.evaluate("() => __snapshotNativeSet.call(localStorage,__snapshotKey,'[]')")
    else:
        page.locator('#crypto-intelligence [data-open="evidence:liquidity_flows"]').first.evaluate("node => node.click()")
        page.locator("#cri-dialog-body summary").focus()
    page.evaluate("""destination => {
      let fired=false;
      Storage.prototype.getItem=function(key) {
        if(key===__snapshotKey && !fired) {
          fired=true;
          if(destination==='saved-retry-focus') {
            window.__preflightFocus=document.getElementById('cri-dialog-close');
            __preflightFocus.focus();
          } else {
            document.querySelector('#crypto-intelligence [data-open="evidence:macro_backdrop"]').click();
            window.__preflightFocus=document.querySelector('#cri-dialog-body summary');
            __preflightFocus.focus();
          }
        }
        return __snapshotNativeGet.call(this,key);
      };
    }""", destination)
    if destination == "saved-retry-focus":
        before_url = page.url
        retry = page.locator("#cri-dialog-body").get_by_role("button", name="Try reading again", exact=True)
        retry.click()
        assert page.url == before_url
        assert page.locator("#cri-dialog-title").inner_text() == "Saved snapshots unavailable"
        assert retry.count() == 1
    else:
        selector = '#crypto-intelligence [data-open="saved"]' if destination == "saved" else '#crypto-intelligence [data-open="scenario:continuation"]'
        page.locator(selector).first.evaluate("node => node.click()")
        _wait_drawer(page, "evidence:macro_backdrop", "Evidence behind the view")
        assert page.locator("#cri-dialog-body [data-snapshot-action]").count() == 0
        assert "Saved in this browser" not in page.locator("#cri-dialog-body").inner_text()
    assert page.evaluate("__preflightFocus.isConnected && document.activeElement===__preflightFocus")
    assert _writes(page) == 0


def _layout_frozen(page):
    data = page.evaluate("JSON.parse(document.getElementById('cri-data').textContent)")
    target = _frozen(data["scenarios"]["30"][0])
    target["issue_evidence"] = {
        "bitcoin_as_of": data["as_of"],
        "market_as_of": data["market_as_of"],
        "families": [
            {key: family.get(key) for key in ("id", "label_en", "label_zh", "state_en", "state_zh", "quality", "snapshot_as_of", "source")}
            for family in data["families"]
        ],
    }
    return target


def _layout_bounds(page):
    return page.locator("#cri-dialog").evaluate("""dialog => {
      const header=dialog.querySelector('.cri-dialog-header').getBoundingClientRect();
      const active=document.activeElement.getBoundingClientRect();
      return {viewport:innerWidth, documentWidth:document.documentElement.scrollWidth,
        dialogWidth:dialog.clientWidth, contentWidth:dialog.scrollWidth,
        headerBottom:header.bottom, activeTop:active.top, activeBottom:active.bottom,
        viewportBottom:innerHeight};
    }""")


@pytest.mark.parametrize("lang,width,theme,motion", [
    ("en", 1440, "dark", "no-preference"), ("zh", 1440, "light", "no-preference"),
    ("en", 390, "light", "no-preference"), ("zh", 390, "dark", "no-preference"),
    ("en", 320, "dark", "reduce"), ("zh", 320, "light", "reduce"),
])
def test_r4_frozen_layout_frontloads_the_complete_condition(snapshot_page, lang, width, theme, motion):
    page = snapshot_page(lang, width, start="#scenarios?h=7")
    page.emulate_media(reduced_motion=motion)
    page.locator("html").evaluate("(node, theme) => node.dataset.theme=theme", theme)
    target = _layout_frozen(page)
    _seed(page, [target])
    before = _raw(page)
    _open_saved_from_list(page, target, lang)
    if (lang, width) in [("en", 1440), ("zh", 390), ("en", 320)]:
        _capture(page, f"layout-saved-{lang}-{width}-{theme}")
    condition = page.locator("#cri-dialog-body").get_by_text(target["condition_" + lang], exact=True)
    assert condition.is_visible(), "The complete original condition must be visible without expanding details."
    assert condition.evaluate("node => !node.closest('details')")
    assert page.locator("#cri-dialog-body").get_by_role("heading", name="Original condition" if lang == "en" else "原始条件", exact=True).count() == 1
    assert page.locator(".cri-saved-status").inner_text() == ("At cutoff · " if lang == "en" else "快照时 · ") + target["progress_" + lang]
    meta = page.locator(".cri-saved-meta").inner_text()
    assert target["asset"] in meta and target["as_of"] in meta and str(target["horizon_days"]) in meta
    assert ("cutoff" if lang == "en" else "截止") in meta
    disclosures = page.locator("#cri-dialog-body details")
    assert disclosures.count() == 2 and disclosures.evaluate_all("nodes => nodes.every(node => !node.open)")
    case = page.locator('[data-drawer-disclosure="case-details"]')
    evidence = page.locator('[data-drawer-disclosure="saved-evidence"]')
    assert case.locator("summary").inner_text() == ("Original case details" if lang == "en" else "原始情景详情")
    assert evidence.locator("summary").inner_text().startswith("Original evidence" if lang == "en" else "原始证据")
    assert "6" in evidence.locator("summary").inner_text()
    assert not page.locator("#cri-dialog-body").get_by_text(target["sequence_" + lang], exact=True).is_visible()
    assert not page.locator("#cri-dialog-body").get_by_role("heading", name="Next check" if lang == "en" else "下一步检查", exact=True).count()
    review = page.locator('[data-drawer-focus="review"]')
    assert review.evaluate("node => node.getBoundingClientRect().height") >= 48
    assert review.evaluate("node => node.getBoundingClientRect().bottom <= innerHeight"), "The primary action should fit the closed saved case."
    sizes = page.locator('#cri-dialog .cri-dialog-header button, #cri-dialog-body summary, #cri-dialog-body button').evaluate_all(
        "nodes => nodes.map(node => {const b=node.getBoundingClientRect();return {width:b.width,height:b.height}})")
    assert all(size["height"] >= 44 for size in sizes), sizes
    metrics = _layout_bounds(page)
    assert metrics["documentWidth"] <= metrics["viewport"] and metrics["contentWidth"] <= metrics["dialogWidth"]
    case.locator("summary").focus()
    page.keyboard.press("Enter")
    assert case.evaluate("node => node.open")
    assert case.locator("summary").evaluate("node => document.activeElement===node")
    case_text = case.inner_text()
    for key in ("sequence", "invalidation", "counter", "next_check"):
        assert target[key + "_" + lang] in case_text
    assert target["expires"] in case_text
    assert target["levels"]["start"] in case_text and target["levels"]["end"] in case_text
    assert "60" in case_text and "$64,681" in case_text and "$86,595" in case_text
    page.keyboard.press("Space")
    assert not case.evaluate("node => node.open")
    evidence.locator("summary").focus()
    page.keyboard.press("Space")
    assert evidence.evaluate("node => node.open")
    assert evidence.locator("summary").evaluate("node => document.activeElement===node")
    evidence_text = evidence.inner_text()
    for family in target["issue_evidence"]["families"]:
        assert family["label_" + lang] in evidence_text and family["state_" + lang] in evidence_text
        assert family["snapshot_as_of"] in evidence_text
    assert ("Stale at capture" if lang == "en" else "保存时已过时") in evidence_text
    assert ("Snapshot only" if lang == "en" else "仅快照") in evidence_text
    assert target["issue_evidence"]["bitcoin_as_of"] in evidence_text
    assert target["issue_evidence"]["market_as_of"] in evidence_text
    assert "snapshot_only" not in evidence_text
    assert ("Snapshot " if lang == "en" else "快照 ") in evidence_text
    if (lang, width) in [("en", 1440), ("zh", 390)]:
        _capture(page, f"layout-evidence-{lang}-{width}-{theme}")
    if motion == "reduce":
        effects = page.locator("#cri-dialog").evaluate("""dialog => [...dialog.querySelectorAll('*')].map(node => {
          const s=getComputedStyle(node);return {animation:s.animationName,transition:s.transitionDuration};
        })""")
        assert all(item["animation"] == "none" and all(float(value.strip().removesuffix("s")) == 0 for value in item["transition"].split(",")) for item in effects)
    assert _raw(page) == before and _writes(page) == 0


def test_r4_frozen_expiry_is_distinct_from_original_progress(snapshot_page):
    page = snapshot_page(width=320, at="2026-12-01T12:00:00Z")
    target = _layout_frozen(page)
    target["progress_en"] = "Original demand was still unconfirmed"
    _seed(page, [target])
    before = _raw(page)
    _open_saved(page, target["revision"])
    state = page.locator(".cri-saved-status").inner_text()
    assert state.startswith("Expired") and "At cutoff" not in state
    case = page.locator('[data-drawer-disclosure="case-details"]')
    case.locator("summary").click()
    assert "Progress at cutoff" in case.inner_text() and target["progress_en"] in case.inner_text()
    assert target["expires"] in case.inner_text()
    assert page.locator('[data-snapshot-action="remove"]').is_enabled()
    assert _raw(page) == before and _writes(page) == 0


@pytest.mark.parametrize("lang,width", [("en", 320), ("zh", 390)])
def test_r4_frozen_legacy_layout_keeps_the_case_without_inventing_evidence(snapshot_page, lang, width):
    page = snapshot_page(lang, width)
    target = _layout_frozen(page)
    del target["issue_evidence"]
    _seed(page, [target])
    before = _raw(page)
    _open_saved(page, target["revision"])
    assert page.locator("#cri-dialog-body").get_by_text(target["condition_" + lang], exact=True).is_visible()
    assert page.locator('[data-drawer-disclosure="saved-evidence"]').count() == 0
    assert ("Evidence digest was not preserved" if lang == "en" else "旧快照未保存原始证据摘要") in page.locator("#cri-dialog-body").inner_text()
    assert page.locator("#cri-dialog-body details").count() == 1
    assert target["as_of"] in page.locator("#cri-dialog-body").inner_text()
    assert _raw(page) == before and _writes(page) == 0
    if lang == "en":
        _capture(page, "layout-legacy-en-320")


@pytest.mark.parametrize("lang,width", [("en", 320), ("zh", 390)])
def test_r4_saved_review_disclosure_keeps_qualifications_and_locale_focus(snapshot_page, lang, width):
    page = snapshot_page(lang, width, start="#scenarios?h=7")
    target = _layout_frozen(page)
    if lang == "en":
        target["asset"] = "TEST-ASSET"
    _seed(page, [target])
    before = _raw(page)
    _open_saved_from_list(page, target, lang)
    _review_saved(page, lang)
    _capture(page, f"layout-review-{lang}-{width}")
    assert target["asset"] in page.locator("#cri-dialog-body").inner_text()
    assert target["as_of"] in page.locator("#cri-dialog-body").inner_text()
    assert ("No performance result is available for this saved case." if lang == "en" else "此已存情景尚无可用的表现检验结果。") in page.locator("#cri-dialog-body").inner_text()
    details = page.locator('[data-drawer-disclosure="review-requirements"]')
    assert details.count() == 1 and not details.evaluate("node => node.open")
    summary = details.locator("summary")
    assert summary.inner_text() == ("What would qualify a comparison" if lang == "en" else "什么样的比较才合格")
    assert not details.get_by_text("Point-in-time history" if lang == "en" else "时点历史", exact=True).is_visible()
    summary.focus()
    page.keyboard.press("Enter")
    assert details.evaluate("node => node.open")
    assert details.locator("dt").count() == 4
    before_history, before_url = page.evaluate("history.length"), page.url
    other = "zh" if lang == "en" else "en"
    page.locator("html").evaluate("(node, lang) => node.dataset.lang=lang", other)
    page.wait_for_function("(lang) => document.getElementById('cri-dialog-title').textContent===(lang==='zh'?'历史检验':'Historical review')", arg=other)
    details = page.locator('[data-drawer-disclosure="review-requirements"]')
    assert details.evaluate("node => node.open")
    assert details.locator("summary").evaluate("node => document.activeElement===node")
    assert page.url == before_url and page.evaluate("history.length") == before_history
    assert details.locator("dt").count() == 4
    metrics = _layout_bounds(page)
    assert metrics["activeTop"] >= metrics["headerBottom"] - 1, metrics
    assert metrics["documentWidth"] <= metrics["viewport"] and metrics["contentWidth"] <= metrics["dialogWidth"]
    assert _raw(page) == before and _writes(page) == 0


@pytest.mark.parametrize("kind,lang,width", [
    ("missing", "en", 320), ("unreadable", "en", 320),
    ("missing", "zh", 390), ("unreadable", "zh", 390),
])
def test_r4_saved_recovery_actions_have_clear_targets_and_spacing(snapshot_page, kind, lang, width):
    page = snapshot_page(lang, width)
    target = _layout_frozen(page)
    if kind == "unreadable":
        page.evaluate("() => __snapshotNativeSet.call(localStorage,__snapshotKey,'{unreadable')")
        page.locator('#crypto-intelligence [data-open="saved"]').click()
    else:
        _open_saved(page, target["revision"])
    group = page.locator(".cri-drawer-actions")
    assert group.count() == 1 and group.locator("button").count() == 2
    bounds = group.locator("button").evaluate_all("nodes => nodes.map(node => {const b=node.getBoundingClientRect();return {x:b.x,y:b.y,right:b.right,bottom:b.bottom,height:b.height}})")
    assert bounds[0]["height"] >= 48 and bounds[1]["height"] >= 44, bounds
    assert bounds[1]["x"] - bounds[0]["right"] >= 7.5 or bounds[1]["y"] - bounds[0]["bottom"] >= 7.5, bounds
    if (kind, lang) in [("missing", "en"), ("unreadable", "zh")]:
        _capture(page, f"layout-recovery-{kind}-{lang}-{width}")
    before_history = page.evaluate("history.length")
    if kind == "unreadable":
        _seed(page, [])
    group.locator("button").first.focus()
    page.keyboard.press("Enter")
    _wait_drawer(page, "saved", "Saved snapshots" if lang == "en" else "已存快照")
    assert page.evaluate("history.length") == before_history and _writes(page) == 0
    metrics = _layout_bounds(page)
    assert metrics["documentWidth"] <= metrics["viewport"] and metrics["contentWidth"] <= metrics["dialogWidth"]


@pytest.mark.parametrize("lang,width", [("en", 320), ("zh", 1440)])
def test_r4_current_scenario_retains_its_existing_reading_order(snapshot_page, lang, width):
    page = snapshot_page(lang, width)
    _open_scenario(page)
    source = _scenario(page)
    assert page.locator("#cri-dialog-body").get_by_role("heading", name="Next check" if lang == "en" else "下一步检查", exact=True).count() == 1
    assert page.locator("#cri-dialog-body").get_by_text(source["sequence_" + lang], exact=True).is_visible()
    assert page.locator("#cri-dialog-body").get_by_text(source["invalidation_" + lang], exact=True).is_visible()
    assert page.locator("#cri-dialog-body details").count() == 1
    assert page.locator("#cri-dialog-body summary").inner_text() == ("Conditions and evidence" if lang == "en" else "条件与证据")
    assert not page.locator("#cri-dialog-body").get_by_text(source["condition_" + lang], exact=True).is_visible()
    if os.environ.get("MMX_CRYPTO_LAYOUT_CURRENT_PROOF"):
        out = Path(os.environ["MMX_CRYPTO_LAYOUT_CURRENT_PROOF"])
        out.mkdir(parents=True, exist_ok=True)
        proof = page.locator("#cri-dialog").evaluate("""dialog => ({
          html:dialog.outerHTML,
          rows:[...dialog.querySelectorAll('h2,h3,p,summary,button')].map(node => {
            const b=node.getBoundingClientRect();return {text:node.textContent,x:b.x,y:b.y,width:b.width,height:b.height};
          })
        })""")
        (out / f"current-{lang}-{width}.json").write_text(json.dumps(proof, ensure_ascii=False, indent=2) + "\n")


@pytest.mark.parametrize("lang,at", [("en", "2026-12-01T12:00:00Z"), ("zh", "2026-10-18T12:00:00Z")])
def test_r4_frozen_missing_progress_is_not_reconstructed(snapshot_page, lang, at):
    page = snapshot_page(lang, 320, at=at)
    target = _layout_frozen(page)
    del target["progress_" + lang]
    target.pop("levels", None)
    _seed(page, [target])
    before = _raw(page)
    _open_saved(page, target["revision"])
    if lang == "en":
        assert page.locator(".cri-saved-status").inner_text().startswith("Expired")
        case = page.locator('[data-drawer-disclosure="case-details"]')
        case.locator("summary").click()
        assert "Progress at cutoff" in case.inner_text() and "Not preserved" in case.inner_text()
        assert "Conditional · confirmation pending" not in case.inner_text()
    else:
        assert page.locator(".cri-saved-status").inner_text() == "原始进展暂无"
        assert "条件路径 · 等待确认" not in page.locator("#cri-dialog-body").inner_text()
    assert _raw(page) == before and _writes(page) == 0


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_r4_frozen_remove_keeps_semantic_focus_across_locale(snapshot_page, lang):
    page = snapshot_page(lang, 320)
    target = _layout_frozen(page)
    _seed(page, [target])
    before = _raw(page)
    _open_saved_from_list(page, target, lang)
    remove = page.locator('[data-snapshot-action="remove"]')
    remove.focus()
    before_url, before_history = page.url, page.evaluate("history.length")
    other = "zh" if lang == "en" else "en"
    page.locator("html").evaluate("(node, lang) => node.dataset.lang=lang", other)
    page.wait_for_function("(title) => document.getElementById('cri-dialog-title').textContent===title", arg=target["title_" + other])
    assert page.locator('[data-snapshot-action="remove"]').evaluate("node => document.activeElement===node")
    assert page.url == before_url and page.evaluate("history.length") == before_history
    assert _raw(page) == before and _writes(page) == 0


@pytest.mark.parametrize("digest", [
    {"families": "unreadable"},
    {"families": [None, [], {}, 4]},
])
def test_r4_frozen_present_unreadable_digest_is_distinct_from_legacy_absence(snapshot_page, digest):
    page = snapshot_page(width=390)
    target = _layout_frozen(page)
    target["issue_evidence"] = digest
    _seed(page, [target])
    before = _raw(page)
    _open_saved(page, target["revision"])
    text = page.locator("#cri-dialog-body").inner_text()
    assert "The saved evidence digest is incomplete or unreadable." in text
    assert "Evidence digest was not preserved" not in text
    assert page.locator("#cri-dialog-body").get_by_text(target["condition_en"], exact=True).is_visible()
    assert page.locator('[data-drawer-disclosure="saved-evidence"]').count() == 0
    assert _raw(page) == before and _writes(page) == 0


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_r4_frozen_partial_evidence_does_not_certify_malformed_fields(snapshot_page, lang):
    page = snapshot_page(lang, 320)
    target = _layout_frozen(page)
    family = deepcopy(target["issue_evidence"]["families"][0])
    family["label_" + lang] = {"malformed": True}
    family["snapshot_as_of"] = "2026-02-30"
    family["quality"] = {"malformed": True}
    invalid = dict(family, **{"state_" + lang: {"malformed": True}})
    target["issue_evidence"] = {"bitcoin_as_of": {"invalid": "clock"}, "market_as_of": "2026-02-30", "families": [family, invalid, {}, None]}
    _seed(page, [target])
    before = _raw(page)
    _open_saved(page, target["revision"])
    evidence = page.locator('[data-drawer-disclosure="saved-evidence"]')
    assert ("1 captured reading" if lang == "en" else "1项留存读数") in evidence.locator("summary").inner_text()
    evidence.locator("summary").click()
    text = evidence.inner_text()
    assert family["id"] in text and family["state_" + lang] in text
    assert ("Some saved evidence entries could not be read." if lang == "en" else "部分已存证据条目无法读取。") in text
    assert ("Snapshot date unavailable" if lang == "en" else "快照日期暂无") in text
    assert ("Quality unavailable" if lang == "en" else "质量未知") in text
    assert "[object Object]" not in text and "2026-02-30" not in text
    assert _raw(page) == before and _writes(page) == 0


# Comparison uses the retained view projection. Synthetic variants below exercise
# unavailable/empty/zero states through the existing renderer, without producers.
@pytest.fixture
def comparison_page(browser, page_url, request, tmp_path):
    created = 0
    def create(lang="en", width=390, variant="retained", start="#markets", javascript=True, touch=False):
        nonlocal created
        view = json.loads((SITE / "crypto_intelligence_r4.json").read_text())
        if variant == "mixed":
            eth, sol = deepcopy(view["assets"])
            eth["relative_90d_pct"] = 0.0
            sol.update(relative_90d_pct=None, relative_en="Building history", relative_zh="积累历史中")
            btc = dict(eth, symbol="BTC", name="Bitcoin", price=100.0, relative_90d_pct=None,
                       relative_en="Building history", relative_zh="积累历史中")
            view["assets"] = [sol, eth, btc]
        elif variant == "two-relative":
            view["assets"][0]["relative_90d_pct"] = 0.0
            view["assets"][1].update(relative_90d_pct=None, relative_en="Building history", relative_zh="积累历史中")
        elif variant == "projected-relative":
            from lib.crypto_intelligence_view import build_view
            from test_crypto_intelligence_r4 import relative_integrity_inputs
            view = build_view(*relative_integrity_inputs())
        elif variant in ("quote-invalid", "quote-small"):
            from lib.crypto_intelligence_view import build_view
            from test_crypto_intelligence_r4 import quote_clarity_inputs
            view = build_view(*quote_clarity_inputs(variant))
        elif variant == "identity-clarity":
            from lib.crypto_intelligence_view import build_view
            from test_crypto_intelligence_r4 import relative_integrity_inputs
            view = build_view(*relative_integrity_inputs())
            assets = {asset["symbol"]: asset for asset in view["assets"]}
            assets["BTC"]["name"] = " btc "
            assets["XRP"]["name"] = None
            view["assets"] = [assets[symbol] for symbol in ("BTC", "XRP", "ETH", "SOL")]
        elif variant in ("missing", "empty"):
            view["assets"] = []
            view["contracts"]["asset_states"] = "accepted" if variant == "empty" else "missing_or_schema_mismatch"
            if variant == "missing":
                view["asset_as_of"] = None
        elif variant != "retained":
            raise AssertionError(variant)
        context = _context(browser, page_url, viewport={"width": width, "height": 844},
                           java_script_enabled=javascript, is_mobile=touch, has_touch=touch)
        request.addfinalizer(context.close)
        page = context.new_page()
        page.set_default_timeout(4500)
        _freeze_time(page)
        page.add_init_script(
            "localStorage.setItem('lang'," + json.dumps(lang) + ");"
            "localStorage.setItem('theme'," + json.dumps("dark" if lang == "en" else "light") + ");"
            "window.__comparisonWrites=0;"
            "const originalSet=Storage.prototype.setItem;"
            "Storage.prototype.setItem=function(k,v){if(k===" + json.dumps(KEY) +
            ")window.__comparisonWrites++;return originalSet.call(this,k,v);};"
        )
        if variant != "retained" or not javascript:
            from scripts.build_crypto_intelligence_r4 import render_view
            created += 1
            rendered = tmp_path / ("rendered-" + str(created))
            render_view(view, rendered)
            markup = (rendered / "crypto-r4.html").read_text()
            if not javascript:
                # Inspect the server-rendered Markets subtree with CSS language
                # selected, without relying on client-side routing.
                markup = markup.replace('data-view="markets" hidden', 'data-view="markets"')
                markup = markup.replace('<html lang="en"', '<html lang="en" data-lang="' + lang + '"')
            page.route("**/crypto-r4.html?*", lambda route: route.fulfill(
                status=200, content_type="text/html; charset=utf-8", body=markup))
        page.goto(page_url + "?lang=" + lang + start, wait_until="load")
        if javascript:
            page.wait_for_function("document.getElementById('crypto-intelligence').dataset.renderedAddress===location.href")
        return page, view
    return create


def _comparison_storage_untouched(page):
    assert page.evaluate("window.__comparisonWrites") == 0
    assert page.evaluate("key=>localStorage.getItem(key)", KEY) is None


@pytest.mark.parametrize("sort,expected", [
    (None, ["ETH", "SOL"]), ("unknown", ["ETH", "SOL"]),
    ("relative", ["SOL", "ETH"]), ("return", ["SOL", "ETH"]), ("symbol", ["ETH", "SOL"]),
])
def test_r4_comparison_default_order_is_neutral_and_explicit_sorts_survive(comparison_page, sort, expected):
    suffix = "" if sort is None else "?sort=" + sort
    page, view = comparison_page(start="#markets" + suffix)
    before = page.url
    rows = page.locator("#cri-market-table tbody tr")
    assert rows.evaluate_all("nodes=>nodes.map(node=>node.dataset.assetRow)") == expected
    assert page.locator("#cri-sort").input_value() == (sort if sort in ("relative", "return", "symbol") else "default")
    assert page.url == before
    assert page.locator("#cri-sort option").all_text_contents() == ["Default order", "Ratio change", "Price change", "Symbol"]
    assert page.evaluate("JSON.parse(document.getElementById('cri-data').textContent).assets") == view["assets"]
    _comparison_storage_untouched(page)


@pytest.mark.parametrize("lang,width,touch", [("en", 1440, False), ("en", 390, False), ("zh", 320, False), ("zh", 320, True)])
def test_r4_comparison_full_cohort_keeps_filtered_origin_and_narrow_context(comparison_page, lang, width, touch):
    origin = "#markets?h=30&window=30&q=ETH&filter=all&sort=return&keep=proof"
    page, view = comparison_page(lang, width, start=origin, touch=touch)
    assert page.locator("#cri-market-table tbody tr:visible").count() == 1
    opener = page.locator('[data-view="markets"] [data-open="comparison"]').first
    assert opener.inner_text().startswith("Compare all 2 assets" if lang == "en" else "比较全部2项资产")
    opener.click()
    _wait_drawer(page, "comparison", "Compare assets" if lang == "en" else "比较资产")
    assert page.locator(".cri-comparison-scope").inner_text() == ("All 2 assets in this snapshot" if lang == "en" else "本快照中的全部2项资产")
    assert page.locator(".cri-comparison-table thead th").all_text_contents()[1:] == [a["symbol"] for a in view["assets"]]
    rows = page.locator(".cri-comparison-table tbody tr")
    assert rows.nth(0).locator("td").all_text_contents() == [a["as_of"] for a in view["assets"]]
    assert rows.nth(1).locator("td").all_text_contents() == ["+2.6%", "+8.8%"]
    assert rows.nth(2).locator("td").all_text_contents() == ["+0.7%", "+7.6%"]
    labels = rows.locator("th").all_text_contents()
    assert labels[1:3] == (["Asset/BTC ratio change", "Price change"] if lang == "en" else ["资产/BTC比值变化", "价格涨跌"])
    body_text = page.locator("#cri-dialog-body").inner_text()
    assert "same published horizon" not in body_text and "0% by definition" not in body_text
    assert "90D" not in body_text and "90天相对" not in body_text
    basis = page.locator("#cri-dialog-body [data-comparison-basis]")
    assert basis.count() == 1 and not basis.evaluate("node=>node.open")
    assert ("Paired window not supplied" if lang == "en" else "未提供配对区间") in basis.locator("summary").inner_text()
    assert not basis.get_attribute("id")
    assert page.locator("#cri-market-basis").count() == 1
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    _capture(page, f"comparison-all-{lang}-{width}" + ("-touch" if touch else ""))
    wrap = page.locator(".cri-comparison-scroll")
    if width <= 390:
        assert page.locator("#cri-dialog").evaluate("node=>Math.abs(node.getBoundingClientRect().width-innerWidth)<1")
        if wrap.evaluate("node=>node.scrollWidth>node.clientWidth"):
            sticky = rows.nth(1).locator("th")
            left_before = sticky.bounding_box()["x"]
            wrap.focus()
            page.keyboard.press("ArrowRight")
            page.wait_for_function("document.querySelector('.cri-comparison-scroll').scrollLeft>0")
            assert abs(sticky.bounding_box()["x"] - left_before) < 1
            assert wrap.evaluate("node=>document.activeElement===node")
            wrap.evaluate("node=>node.scrollLeft=0")
    if touch:
        assert page.locator("#cri-dialog").evaluate("node=>Math.abs(node.getBoundingClientRect().height-innerHeight)<1")
    summary = basis.locator("summary")
    summary.focus()
    page.keyboard.press("Enter")
    assert basis.evaluate("node=>node.open")
    detail = basis.inner_text()
    assert "90" in detail and "91" in detail and "30" in detail
    assert ("need not equal calendar days" if lang == "en" else "不一定等于日历天数") in detail
    assert ("cannot be verified" if lang == "en" else "无法核验") in detail
    page.keyboard.press("Space")
    assert not basis.evaluate("node=>node.open")
    page.locator("#cri-dialog-close").click()
    page.wait_for_function("(hash)=>location.hash===hash&&!document.getElementById('cri-dialog').open", arg=origin)
    assert opener.evaluate("node=>document.activeElement===node")
    assert page.locator("#cri-search").input_value() == "ETH"
    assert page.locator("#cri-sort").input_value() == "return"
    assert page.locator("#cri-market-table tbody tr:visible").count() == 1
    _comparison_storage_untouched(page)


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_r4_comparison_reset_moves_focus_before_hiding_recovery(comparison_page, lang):
    page, _ = comparison_page(lang, 320, start="#markets?h=30&window=30&q=absent&filter=leaders&sort=relative&keep=proof")
    reset = page.locator("#cri-reset")
    assert reset.is_visible()
    assert page.locator('[data-view="markets"] [data-open="comparison"]').first.is_visible()
    reset.focus()
    page.keyboard.press("Enter")
    assert page.evaluate("location.hash") == "#markets?h=30&window=30&keep=proof"
    assert page.locator("#cri-search").evaluate("node=>document.activeElement===node")
    assert not reset.is_visible()
    assert page.locator("#cri-sort").input_value() == "default"
    assert page.locator("#cri-market-table tbody tr:visible").count() == 2
    _comparison_storage_untouched(page)


@pytest.mark.parametrize("interruption", ["navigation", "language", "focus"])
def test_r4_comparison_reset_yields_to_a_new_focus_destination(comparison_page, interruption):
    page, _ = comparison_page(start="#markets?q=absent&h=30&keep=proof")
    page.evaluate("""kind=>{
      document.getElementById('cri-search').addEventListener('focus',()=>{
        if(kind==='navigation')document.querySelector('.cri-tabs [data-route="bitcoin"]').click();
        if(kind==='language')document.documentElement.dataset.lang='zh';
        if(kind==='focus')document.getElementById('cri-sort').focus();
      },{once:true});
    }""", interruption)
    page.locator("#cri-reset").click()
    assert "q=absent" in page.evaluate("location.hash")
    assert "h=30" in page.evaluate("location.hash") and "keep=proof" in page.evaluate("location.hash")
    if interruption == "navigation":
        assert page.locator('[data-view="bitcoin"]').is_visible()
    elif interruption == "language":
        page.wait_for_function("document.getElementById('crypto-intelligence').dataset.renderedLanguage==='true'")
        assert page.locator("#cri-market-empty").is_visible()
    else:
        assert page.locator("#cri-sort").evaluate("node=>document.activeElement===node")
    _comparison_storage_untouched(page)


@pytest.mark.parametrize("variant,lang", [("missing", "en"), ("missing", "zh"), ("empty", "en"), ("empty", "zh")])
def test_r4_comparison_missing_and_empty_assets_are_not_filter_failures(comparison_page, variant, lang):
    page, _ = comparison_page(lang, 320, variant, "#markets?q=absent&h=30&window=30&panel=comparison")
    expected = ("Asset data unavailable" if lang == "en" else "资产数据暂无") if variant == "missing" else ("No assets in this snapshot" if lang == "en" else "本快照暂无资产")
    assert page.locator("#cri-dialog-body").get_by_role("heading", name=expected, exact=True).count() == 1
    assert page.locator(".cri-comparison-table").count() == 0
    assert page.locator("#cri-dialog-body [data-comparison-basis]").count() == 0
    page.locator("#cri-dialog-close").click()
    assert page.evaluate("location.hash") == "#markets?q=absent&h=30&window=30"
    assert page.locator("#cri-market-empty-title").inner_text() == expected
    assert page.locator("#cri-market-empty").is_visible()
    assert not page.locator("#cri-reset").is_visible()
    assert not page.locator("#cri-market-table").is_visible()
    assert not page.locator("#cri-market-controls").is_visible()
    assert page.locator("#cri-empty-coverage").is_visible()
    assert page.locator(".cri-tabs").is_visible()
    page.locator("#cri-empty-coverage").click()
    _wait_drawer(page, "coverage", "Data and coverage" if lang == "en" else "数据与覆盖")
    _comparison_storage_untouched(page)


@pytest.mark.parametrize("variant", ["missing", "empty"])
def test_r4_comparison_empty_server_reading_needs_no_javascript(comparison_page, variant):
    page, _ = comparison_page("en", 390, variant, javascript=False)
    expected = "Asset data unavailable" if variant == "missing" else "No assets in this snapshot"
    market = page.locator('[data-view="markets"]')
    assert market.is_visible()
    assert market.locator("#cri-market-empty-title").inner_text() == expected
    assert market.locator("#cri-market-empty").is_visible()
    assert not market.locator("#cri-reset").is_visible()
    assert not market.locator("#cri-market-table").is_visible()


@pytest.mark.parametrize("lang,width", [("en", 390), ("zh", 320)])
def test_r4_comparison_null_relative_does_not_erase_usable_asset_or_zero(comparison_page, lang, width):
    page, view = comparison_page(lang, width, "mixed")
    assert page.locator("#cri-market-table tbody tr").evaluate_all("nodes=>nodes.map(node=>node.dataset.assetRow)") == ["SOL", "ETH", "BTC"]
    sol = page.locator('[data-asset-row="SOL"]')
    ratio = sol.locator("td").nth(3).inner_text()
    assert ("Unavailable" if lang == "en" else "暂无") in ratio
    assert ("Building history" if lang == "en" else "积累历史中") in ratio
    assert page.locator('[data-asset-row="ETH"] td').nth(3).inner_text() == "0.0%"
    sol.locator('[data-open="asset:SOL"]').first.click()
    _wait_drawer(page, "asset:SOL", "Solana · SOL")
    content = page.locator("#cri-dialog-body").inner_text()
    assert "$104.19" in content
    assert ("Advancing" if lang == "en" else "上行") in content
    assert ("Stressed" if lang == "en" else "承压") in content
    assert ("Building history" if lang == "en" else "积累历史中") in content
    assert "90-day" not in content and "30-day" not in content and "90天" not in content
    page.locator("#cri-dialog-close").click()
    page.locator('[data-view="markets"] [data-open="comparison"]').click()
    row = page.locator(".cri-comparison-table tbody tr").nth(1)
    cells = row.locator("td").all_text_contents()
    assert "0.0%" == cells[1]
    assert all(("Unavailable" if lang == "en" else "暂无") in cells[i] for i in (0, 2))
    assert "0% by definition" not in page.locator("#cri-dialog-body").inner_text()
    assert page.evaluate("JSON.parse(document.getElementById('cri-data').textContent).assets") == view["assets"]
    _comparison_storage_untouched(page)


@pytest.mark.parametrize("lang", ["en", "zh"])
def test_r4_comparison_locale_refresh_keeps_surviving_asset_control(comparison_page, lang):
    page, _ = comparison_page(lang, 390)
    target = page.locator('[data-asset-row="ETH"] .cri-asset')
    target.focus()
    page.evaluate("""()=>{
      window.__comparisonRowMoves=0;
      new MutationObserver(records=>{window.__comparisonRowMoves+=records.filter(r=>r.type==='childList').length})
        .observe(document.querySelector('#cri-market-table tbody'),{childList:true});
    }""")
    before = page.url
    other = "zh" if lang == "en" else "en"
    page.locator("html").evaluate("(node,lang)=>node.dataset.lang=lang", other)
    page.wait_for_function("(lang)=>document.getElementById('crypto-intelligence').dataset.renderedLanguage===String(lang==='zh')", arg=other)
    assert target.evaluate("node=>document.activeElement===node")
    assert page.evaluate("window.__comparisonRowMoves") == 0
    assert page.url == before
    _comparison_storage_untouched(page)


@pytest.mark.parametrize("panel,focus", [("comparison", "summary"), ("comparison", "coverage"), ("asset:ETH", "summary"), ("asset:ETH", "coverage")])
def test_r4_comparison_basis_locale_and_coverage_keep_existing_navigation(comparison_page, panel, focus):
    page, _ = comparison_page(start="#markets?h=7&window=30&sort=symbol")
    opener = page.locator('[data-view="markets"] [data-open="' + panel + '"]').first
    opener.click()
    basis = page.locator("#cri-dialog-body [data-comparison-basis]")
    basis.locator("summary").click()
    target = basis.locator('[data-basis-focus="' + focus + '"]')
    target.focus()
    before_url, before_history = page.url, page.evaluate("history.length")
    page.locator("html").evaluate("node=>node.dataset.lang='zh'")
    page.wait_for_function("document.getElementById('crypto-intelligence').dataset.renderedLanguage==='true'")
    basis = page.locator("#cri-dialog-body [data-comparison-basis]")
    assert basis.evaluate("node=>node.open")
    assert basis.locator('[data-basis-focus="' + focus + '"]').evaluate("node=>document.activeElement===node")
    assert page.url == before_url and page.evaluate("history.length") == before_history
    basis.locator('[data-basis-focus="coverage"]').click()
    _wait_drawer(page, "evidence:participation", "判断背后的证据")
    assert page.evaluate("history.length") == before_history + 1
    assert page.evaluate("history.state.depth") == 2
    page.locator("#cri-dialog-close").click()
    page.wait_for_function("location.hash==='#markets?h=7&window=30&sort=symbol'&&!document.getElementById('cri-dialog').open")
    assert opener.evaluate("node=>document.activeElement===node")
    _comparison_storage_untouched(page)



@pytest.mark.parametrize("variant,lang", [("missing", "en"), ("missing", "zh"), ("empty", "en"), ("empty", "zh")])
def test_r4_comparison_asset_link_distinguishes_unavailable_source_from_absence(comparison_page, variant, lang):
    page, _ = comparison_page(lang, 320, variant, "#markets?h=30&panel=asset:ETH")
    assert page.locator("#cri-dialog-title").inner_text() == ("Asset unavailable" if lang == "en" else "资产暂不可用")
    text = page.locator("#cri-dialog-body").inner_text()
    unavailable = "This snapshot could not provide asset readings." if lang == "en" else "本快照无法提供资产读数。"
    absent = "This asset is not present in the snapshot." if lang == "en" else "本快照中没有此资产。"
    assert (unavailable if variant == "missing" else absent) in text
    assert (absent if variant == "missing" else unavailable) not in text
    assert page.locator("#cri-dialog-body").get_by_role("button", name="Data and coverage" if lang == "en" else "数据与覆盖", exact=True).count() == 1
    _comparison_storage_untouched(page)



@pytest.mark.parametrize("lang", ["en", "zh"])
def test_r4_comparison_basis_locale_preserves_scroll_when_close_keeps_focus(comparison_page, lang):
    page, _ = comparison_page(lang, 320)
    page.locator('[data-asset-row="ETH"] .cri-asset').click()
    basis = page.locator("#cri-dialog-body [data-comparison-basis]")
    basis.locator("summary").click()
    dialog = page.locator("#cri-dialog")
    before = dialog.evaluate("node=>{node.scrollTop=180;return node.scrollTop;}")
    assert before > 100
    close = page.locator("#cri-dialog-close")
    close.evaluate("node=>node.focus({preventScroll:true})")
    other = "zh" if lang == "en" else "en"
    page.locator("html").evaluate("(node,lang)=>node.dataset.lang=lang", other)
    page.wait_for_function("(lang)=>document.getElementById('crypto-intelligence').dataset.renderedLanguage===String(lang==='zh')", arg=other)
    assert close.evaluate("node=>document.activeElement===node")
    assert page.locator("#cri-dialog-body [data-comparison-basis]").evaluate("node=>node.open")
    metrics = dialog.evaluate("node=>({scroll:node.scrollTop,maximum:node.scrollHeight-node.clientHeight})")
    assert abs(metrics["scroll"] - min(before, metrics["maximum"])) <= 1, (before, metrics)
    _comparison_storage_untouched(page)



@pytest.mark.parametrize("lang,width", [("en", 390), ("zh", 320)])
def test_r4_comparison_pointer_close_keeps_settings_clear_and_owner_usable(comparison_page, lang, width):
    page, _ = comparison_page(lang, width)
    assert page.evaluate("matchMedia('(hover:hover) and (pointer:fine)').matches")
    page.locator("#cri-market-table tbody tr:visible .cri-asset").first.click()
    page.locator("#cri-dialog-close").click()
    page.wait_for_function("location.hash==='#markets'&&!document.getElementById('cri-dialog').open")
    page.evaluate("()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))")
    assert page.locator("#settings-pop").evaluate("node=>getComputedStyle(node).pointerEvents") == "none"
    page.locator('[data-view="markets"] [data-open="comparison"]').first.click()
    page.wait_for_function("document.getElementById('cri-dialog').open&&document.getElementById('cri-dialog-body').dataset.panel==='comparison'")
    assert page.evaluate("history.state.depth") == 1
    page.locator("#cri-dialog-close").click()
    page.wait_for_function("location.hash==='#markets'&&!document.getElementById('cri-dialog').open")
    assert page.locator("#settings-pop").evaluate("node=>getComputedStyle(node).pointerEvents") == "none"
    page.locator("#settings-open").hover()
    page.wait_for_function("getComputedStyle(document.getElementById('settings-pop')).pointerEvents==='auto'")
    page.locator("#settings-open").click()
    assert page.locator("#settings-open").get_attribute("aria-expanded") == "true"
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    _comparison_storage_untouched(page)



def _compact_matrix_metrics(page, name):
    metrics = page.locator(".cri-comparison-scroll").evaluate("""wrap=>{
      const box=wrap.getBoundingClientRect(),table=wrap.querySelector('table');
      function reading(cell) {
        const target=cell.firstChild, range=document.createRange();
        range.selectNodeContents(target);
        const boxes=[...range.getClientRects()].map(b=>({left:b.left,right:b.right,width:b.width,top:b.top,height:b.height}));
        const style=getComputedStyle(cell);
        return {text:target.textContent,boxes,fontSize:style.fontSize,fontFamily:style.fontFamily,
          cellWidth:cell.getBoundingClientRect().width,paddingLeft:style.paddingLeft,paddingRight:style.paddingRight};
      }
      return {viewport:innerWidth,left:box.left,right:box.right,clientWidth:wrap.clientWidth,scrollWidth:wrap.scrollWidth,
        headers:[...table.querySelectorAll('thead th')].slice(1).map(reading),
        rows:[...table.querySelectorAll('tbody tr')].map(row=>[...row.querySelectorAll('td')].map(reading)),
        measureWidth:table.querySelector('tbody th').getBoundingClientRect().width,
        bodyWidth:document.body.scrollWidth};
    }""")
    if os.environ.get("MMX_CRYPTO_COMPACT_METRICS"):
        out=Path(os.environ["MMX_CRYPTO_COMPACT_METRICS"])
        out.mkdir(parents=True,exist_ok=True)
        (out/(name+".json")).write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+"\n")
    return metrics


@pytest.mark.parametrize("lang,width,touch", [
    ("en",320,False),("en",390,False),("zh",320,True),("zh",390,True)
])
def test_r4_compact_matrix_two_assets_fit_with_complete_dates_and_values(comparison_page,lang,width,touch):
    page,view=comparison_page(lang,width,touch=touch)
    page.locator('[data-view="markets"] [data-open="comparison"]').click()
    page.evaluate("()=>document.fonts.ready")
    metrics=_compact_matrix_metrics(page,f"two-{lang}-{width}")
    assert metrics["scrollWidth"] <= metrics["clientWidth"]+1,metrics
    assert metrics["bodyWidth"] <= width
    assert [x["text"] for x in metrics["headers"]] == ["ETH","SOL"]
    assert [x["text"] for x in metrics["rows"][0]] == [a["as_of"] for a in view["assets"]]
    assert [x["text"] for x in metrics["rows"][1]] == ["+2.6%","+8.8%"]
    assert [x["text"] for x in metrics["rows"][2]] == ["+0.7%","+7.6%"]
    # Dates, signed readings and asset headers stay whole; labels may wrap.
    for cell in metrics["headers"]+[cell for row in metrics["rows"][:3] for cell in row]:
        assert len(cell["boxes"]) == 1,cell
        assert metrics["left"] <= cell["boxes"][0]["left"] <= cell["boxes"][0]["right"] <= metrics["right"]+0.5,cell
    assert page.evaluate("JSON.parse(document.getElementById('cri-data').textContent).assets") == view["assets"]
    if width==320:
        _capture(page,f"compact-two-{lang}-{width}")
    _comparison_storage_untouched(page)


@pytest.mark.parametrize("lang,touch", [("en",False),("zh",True)])
def test_r4_compact_matrix_two_assets_keep_null_zero_and_history_readable(comparison_page,lang,touch):
    page,_=comparison_page(lang,320,"two-relative",touch=touch)
    page.locator('[data-view="markets"] [data-open="comparison"]').click()
    page.evaluate("()=>document.fonts.ready")
    metrics=_compact_matrix_metrics(page,f"two-relative-{lang}-320")
    assert metrics["scrollWidth"] <= metrics["clientWidth"]+1,metrics
    assert metrics["rows"][1][0]["text"]=="0.0%"
    missing=metrics["rows"][1][1]
    assert missing["text"]==("Unavailable" if lang=="en" else "暂无")
    assert len(missing["boxes"])==1,missing
    assert missing["boxes"][0]["right"] <= metrics["right"]+0.5
    state=page.locator(".cri-comparison-table tbody tr").nth(1).locator(".cri-measure-state")
    assert state.inner_text()==("Building history" if lang=="en" else "积累历史中")
    assert state.evaluate("node=>node.scrollWidth<=node.clientWidth")
    if lang=="en":
        _capture(page,"compact-null-en-320")
    _comparison_storage_untouched(page)


@pytest.mark.parametrize("lang,touch", [("en",False),("zh",True)])
def test_r4_compact_matrix_larger_cohort_keeps_native_scroll_and_measure_context(comparison_page,lang,touch):
    page,view=comparison_page(lang,320,"mixed",touch=touch)
    page.locator('[data-view="markets"] [data-open="comparison"]').click()
    page.evaluate("()=>document.fonts.ready")
    wrap=page.locator(".cri-comparison-scroll")
    metrics=_compact_matrix_metrics(page,f"three-{lang}-320")
    assert metrics["scrollWidth"] > metrics["clientWidth"]
    assert [x["text"] for x in metrics["headers"]] == [a["symbol"] for a in view["assets"]]
    sticky=page.locator(".cri-comparison-table tbody tr").nth(1).locator("th")
    initial=sticky.bounding_box()["x"]
    wrap.focus()
    for _ in range(16):
        page.keyboard.press("ArrowRight")
    page.wait_for_function("(()=>{const w=document.querySelector('.cri-comparison-scroll');return w.scrollLeft+w.clientWidth>=w.scrollWidth-1})()")
    assert abs(sticky.bounding_box()["x"]-initial)<1
    assert wrap.evaluate("node=>document.activeElement===node")
    last=page.locator(".cri-comparison-table thead th").last
    assert last.inner_text()=="BTC"
    assert last.bounding_box()["x"]+last.bounding_box()["width"] <= wrap.bounding_box()["x"]+wrap.bounding_box()["width"]+1
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    if lang=="zh":
        _capture(page,"compact-three-zh-320")
    _comparison_storage_untouched(page)


@pytest.mark.parametrize("lang,width,touch", [("en",390,False),("zh",320,True)])
def test_r4_relative_integrity_projection_reaches_overview_inspector_and_comparison(comparison_page,lang,width,touch):
    page,view=comparison_page(lang,width,"projected-relative",start="#overview",touch=touch)
    unavailable="Unavailable" if lang=="en" else "暂无"
    history="Building history" if lang=="en" else "积累历史中"
    leading="Leading Bitcoin" if lang=="en" else "领先比特币"
    tracking="Tracking Bitcoin" if lang=="en" else "跟随比特币"
    watch=page.locator('[data-view="overview"] .cri-watch-row')
    assert unavailable in watch.nth(0).inner_text()
    assert leading not in watch.nth(0).inner_text()
    assert tracking in watch.nth(1).inner_text()
    page.locator('.cri-tabs [data-route="markets"]').click()
    page.wait_for_function("location.hash==='#markets'")
    eth=page.locator('[data-asset-row="ETH"]')
    assert eth.locator("td").nth(3).inner_text()==unavailable
    assert eth.locator("td").nth(3).locator(".cri-measure-state").count()==0
    assert page.locator('[data-asset-row="SOL"] td').nth(3).inner_text()=="0.0%"
    btc=page.locator('[data-asset-row="BTC"]')
    assert history in btc.locator("td").nth(3).inner_text()
    assert leading not in btc.locator("td").nth(3).inner_text()
    eth.locator(".cri-asset").click()
    _wait_drawer(page,"asset:ETH","Ethereum · ETH")
    body=page.locator("#cri-dialog-body")
    assert body.locator(":scope > dl dd").nth(3).inner_text()==unavailable
    assert body.locator(":scope > dl dd").nth(4).inner_text()==unavailable
    assert "$2,400" in body.inner_text()
    assert ("Advancing" if lang=="en" else "上行") in body.inner_text()
    assert ("Stressed" if lang=="en" else "承压") in body.inner_text()
    if lang=="en":
        _capture(page,"relative-unavailable-en-390")
    page.locator("#cri-dialog-close").click()
    btc.locator(".cri-asset").click()
    _wait_drawer(page,"asset:BTC","BTC · BTC")
    assert page.locator("#cri-dialog-body > dl dd").nth(4).inner_text()==history
    if lang=="zh":
        _capture(page,"relative-history-zh-320")
    page.locator("#cri-dialog-close").click()
    page.locator('[data-view="markets"] [data-open="comparison"]').click()
    row=page.locator(".cri-comparison-table tbody tr").nth(1)
    assert row.locator("td").nth(0).inner_text()==unavailable
    assert row.locator("td").nth(1).inner_text()=="0.0%"
    assert history in row.locator("td").nth(2).inner_text()
    assert leading not in row.locator("td").nth(2).inner_text()
    assert row.locator("td").nth(3).inner_text()=="+10.0%"
    assert page.evaluate("JSON.parse(document.getElementById('cri-data').textContent).assets")==view["assets"]
    _comparison_storage_untouched(page)


@pytest.mark.parametrize("lang",["en","zh"])
def test_r4_relative_integrity_leaders_filter_uses_only_qualified_projection(comparison_page,lang):
    page,view=comparison_page(lang,390,"projected-relative",start="#markets?filter=leaders")
    rows=page.locator("#cri-market-table tbody tr:visible")
    assert rows.evaluate_all("nodes=>nodes.map(n=>n.dataset.assetRow)")==["XRP"]
    page.locator('[data-view="markets"] [data-open="comparison"]').click()
    assert page.locator(".cri-comparison-table thead th").all_text_contents()[1:]==["ETH","SOL","BTC","XRP"]
    page.locator("#cri-dialog-close").click()
    page.wait_for_function("location.hash==='#markets?filter=leaders'&&!document.getElementById('cri-dialog').open")
    assert rows.evaluate_all("nodes=>nodes.map(n=>n.dataset.assetRow)")==["XRP"]
    assert len(view["assets"])==4
    _comparison_storage_untouched(page)


@pytest.mark.parametrize("lang,width,touch", [("en", 390, False), ("zh", 320, True)])
@pytest.mark.parametrize("variant", ["quote-invalid", "quote-small"])
def test_r4_quote_clarity_server_and_inspector_agree_without_losing_asset_context(comparison_page, lang, width, touch, variant):
    page, view = comparison_page(lang, width, variant, start="#markets", touch=touch)
    unavailable = "Unavailable" if lang == "en" else "暂无"
    expected = ([unavailable, "$104.19", unavailable, "$2,413"] if variant == "quote-invalid" else
                ["$0.001", "<$0.00000001", "$0.00000002", "$0.00000003", "$0.01"])
    rows = page.locator("#cri-market-table tbody tr")
    assert rows.count() == len(expected) == len(view["assets"])
    assert rows.evaluate_all("nodes=>nodes.map(n=>n.dataset.assetRow)") == [a["symbol"] for a in view["assets"]]
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    for index, (asset, price) in enumerate(zip(view["assets"], expected)):
        row = rows.nth(index)
        assert row.locator("td").nth(1).inner_text() == price
        opener = row.locator(".cri-asset")
        opener.click()
        page.wait_for_function("(symbol)=>document.getElementById('cri-dialog').open&&document.getElementById('cri-dialog-body').dataset.panel==='asset:'+symbol", arg=asset["symbol"])
        readings = page.locator("#cri-dialog-body > dl dd")
        assert readings.nth(0).inner_text() == price
        assert readings.nth(1).inner_text() == asset["as_of"]
        visual = readings.nth(0).evaluate("""quote => {
            const row=quote.parentElement, observed=row.nextElementSibling;
            const label=observed.querySelector('dt'), date=observed.querySelector('dd');
            const q=quote.getBoundingClientRect(), d=date.getBoundingClientRect();
            const style=getComputedStyle(quote);
            return {font:style.fontSize, line:style.lineHeight, weight:style.fontWeight,
                quoteHeight:q.height, dateFont:getComputedStyle(date).fontSize,
                dateLabel:label.textContent, gap:label.getBoundingClientRect().top-q.bottom,
                divider:getComputedStyle(row).borderBottomWidth,
                fits:quote.scrollWidth<=quote.clientWidth, dateBelow:d.top>=q.bottom};
        }""")
        assert visual["font"] == "30px" and visual["line"] == "38px" and visual["weight"] == "600"
        assert visual["quoteHeight"] == 38 and visual["fits"] and visual["dateBelow"]
        assert visual["dateFont"] == "14px" and 7 <= visual["gap"] <= 9
        assert visual["divider"] == "0px"
        assert visual["dateLabel"] == ("Asset observation date" if lang == "en" else "资产观测日期")
        assert readings.nth(4).inner_text() == asset["relative_" + lang]
        assert readings.nth(5).inner_text() == asset["trend_" + lang]
        assert readings.nth(6).inner_text() == asset["risk_" + lang]
        assert page.locator("#cri-dialog-body").evaluate("n=>n.scrollWidth<=n.clientWidth")
        if (variant == "quote-invalid" and index == 0) or (variant == "quote-small" and index == 1):
            _capture(page, variant + "-" + lang + "-" + str(width))
        page.locator("#cri-dialog-close").click()
        page.wait_for_function("location.hash==='#markets'&&!document.getElementById('cri-dialog').open")
        assert opener.evaluate("n=>document.activeElement===n")
    assert page.locator('[data-asset-row="SOL"] td').nth(3).inner_text() == "0.0%"
    assert page.evaluate("JSON.parse(document.getElementById('cri-data').textContent).assets") == view["assets"]
    _comparison_storage_untouched(page)


@pytest.mark.parametrize("lang,width,touch", [("en", 390, False), ("zh", 320, True)])
def test_r4_asset_identity_is_clear_without_changing_search_routes_or_context(comparison_page, lang, width, touch):
    page, view = comparison_page(lang, width, "identity-clarity", start="#overview", touch=touch)
    watch = page.locator('[data-view="overview"] .cri-watch-row')
    assert watch.locator("strong").all_inner_texts() == ["BTC", "XRP"]
    assert watch.locator(".cri-subtle").count() == 0
    if os.environ.get("MMX_CRYPTO_SNAPSHOT_CAPTURE_DIR"):
        out = Path(os.environ["MMX_CRYPTO_SNAPSHOT_CAPTURE_DIR"])
        out.mkdir(parents=True, exist_ok=True)
        page.locator('[data-view="overview"] .cri-section').last.screenshot(
            path=str(out / ("identity-overview-" + lang + "-" + str(width) + ".png")))
    for index, symbol in enumerate(("BTC", "XRP")):
        opener = watch.nth(index).locator("button")
        opener.click()
        page.wait_for_function("(symbol)=>document.getElementById('cri-dialog').open&&document.getElementById('cri-dialog-body').dataset.panel==='asset:'+symbol", arg=symbol)
        assert page.locator("#cri-dialog-title").inner_text() == symbol
        page.locator("#cri-dialog-close").click()
        page.wait_for_function("location.hash==='#overview'&&!document.getElementById('cri-dialog').open")
        assert opener.evaluate("n=>document.activeElement===n")
    page.locator('[data-route="markets"]').first.click()
    page.wait_for_function("location.hash==='#markets'")
    rows = page.locator("#cri-market-table tbody tr")
    assert rows.evaluate_all("nodes=>nodes.map(n=>n.dataset.assetRow)") == ["BTC", "XRP", "ETH", "SOL"]
    labels = ["BTC", "XRP", "Ethereum ETH", "Solana SOL"]
    titles = ["BTC", "XRP", "Ethereum · ETH", "Solana · SOL"]
    for index, (label, title) in enumerate(zip(labels, titles)):
        row = rows.nth(index)
        # Accessible identity excludes the decorative initial and any duplicate fallback.
        opener = row.get_by_role("button", name=label, exact=True)
        assert opener.count() == 1
        assert " ".join(row.locator(".cri-asset > span").nth(1).inner_text().split()) == label
        assert row.locator(".cri-asset small").count() == (0 if index < 2 else 1)
        opener.click()
        page.wait_for_function("document.getElementById('cri-dialog').open")
        assert page.locator("#cri-dialog-title").inner_text() == title
        assert page.locator("#cri-dialog-body > dl dd").nth(1).inner_text() == view["assets"][index]["as_of"]
        if index == 0:
            _capture(page, "identity-inspector-" + lang + "-" + str(width))
        page.locator("#cri-dialog-close").click()
        page.wait_for_function("location.hash==='#markets'&&!document.getElementById('cri-dialog').open")
        assert opener.evaluate("n=>document.activeElement===n")
    for query, symbol, title in [("btc", "BTC", "BTC"), ("ethereum", "ETH", "Ethereum · ETH")]:
        page.locator("#cri-search").fill(query)
        page.wait_for_function("(symbol)=>Array.from(document.querySelectorAll('#cri-market-table tbody tr')).filter(n=>!n.hidden).map(n=>n.dataset.assetRow).join(',')===symbol", arg=symbol)
        opener = page.locator('[data-asset-row="' + symbol + '"] .cri-asset')
        opener.click()
        page.wait_for_function("document.getElementById('cri-dialog').open")
        assert page.locator("#cri-dialog-title").inner_text() == title
        page.locator("#cri-dialog-close").click()
        page.wait_for_function("!document.getElementById('cri-dialog').open")
        assert page.locator("#cri-search").input_value() == query
        assert opener.evaluate("n=>document.activeElement===n")
    page.locator("#cri-search").fill("")
    compare = page.locator("#cri-market-compare button")
    compare.click()
    page.wait_for_function("document.getElementById('cri-dialog-body').dataset.panel==='comparison'")
    assert page.locator(".cri-comparison-table thead th").all_inner_texts() == [
        "Measure" if lang == "en" else "指标", "BTC", "XRP", "ETH", "SOL"
    ]
    page.locator("#cri-dialog-close").click()
    page.wait_for_function("!document.getElementById('cri-dialog').open")
    assert compare.evaluate("n=>document.activeElement===n")
    page.locator('[data-route="overview"]').first.click()
    page.wait_for_function("location.hash==='#overview'")
    page.locator('[data-view="overview"] [data-open="coverage"]').first.click()
    page.wait_for_function("document.getElementById('cri-dialog-body').dataset.panel==='coverage'")
    assert page.locator("#cri-dialog-body > dl dd").first.evaluate("n=>getComputedStyle(n).fontSize") == "14px"
    assert page.locator("#cri-dialog-body .cri-asset-quote").count() == 0
    page.locator("#cri-dialog-close").click()
    page.wait_for_function("!document.getElementById('cri-dialog').open")
    assert page.evaluate("JSON.parse(document.getElementById('cri-data').textContent).assets") == view["assets"]
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    _comparison_storage_untouched(page)


# A requested current case must never become an unbound historical review.
@pytest.mark.parametrize("lang,width", [("en", 390), ("zh", 320)])
@pytest.mark.parametrize("panel", ["scenario:absent", "memory:absent", "memory:"])
def test_r4_missing_current_case_recovers_without_borrowing_review_context(snapshot_page, lang, width, panel):
    suffix = "?h=30&window=30&q=eth&filter=leaders&sort=return&panel=" + quote(panel)
    page = snapshot_page(lang=lang, width=width, start="#markets" + suffix)
    expected = "Scenario unavailable" if lang == "en" else "情景暂不可用"
    _wait_drawer(page, panel, expected)
    opaque = {"future": {"keep": [0, False, None]}}
    _seed(page, [opaque])
    before_raw, before_history = _raw(page), page.evaluate("history.length")
    content = page.locator("#cri-dialog-body")
    message = ("This scenario is not in the current snapshot for this horizon." if lang == "en"
               else "当前快照在此周期内没有这个情景。")
    assert content.get_by_text(message, exact=True).is_visible()
    text = content.inner_text()
    assert ("No qualified comparison yet" if lang == "en" else "暂无合格的历史比较") not in text
    assert ("Required before results" if lang == "en" else "结果发布前需要") not in text
    source = _scenario(page)
    assert source["as_of"] not in text and source["title_" + lang] not in text
    assert content.locator("[data-snapshot-action]").count() == 0
    recover = content.get_by_role("button", name="Browse scenarios" if lang == "en" else "浏览情景", exact=True)
    assert recover.is_enabled()
    assert recover.evaluate("n=>{const b=n.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth&&b.bottom<=innerHeight}")
    if panel != "memory:":
        _capture(page, "scenario-recovery-" + panel.split(":")[0] + "-" + lang + "-" + str(width))
    recover.focus()
    recover.press("Enter")
    _wait_closed(page)
    assert page.evaluate("history.length") == before_history
    assert page.evaluate("location.hash.split('?')[0]") == "#scenarios"
    assert page.evaluate("Object.fromEntries(new URLSearchParams(location.hash.split('?')[1]))") == {
        "h": "30", "window": "30", "q": "eth", "filter": "leaders", "sort": "return"
    }
    assert page.locator('.cri-tabs [data-route="scenarios"][aria-current="page"]').is_visible()
    assert page.locator("#scenarios-title").evaluate("n=>document.activeElement===n")
    opener = page.locator('[data-view="scenarios"] [data-case-horizon="30"] [data-open="scenario:continuation"]')
    opener.click()
    _wait_drawer(page, "scenario:continuation", source["title_" + lang])
    assert "30" + (" days" if lang == "en" else "天") in content.inner_text()
    page.keyboard.press("Escape")
    _wait_closed(page)
    assert opener.evaluate("n=>document.activeElement===n")
    assert "absent" not in page.evaluate("location.hash")
    assert _raw(page) == before_raw and _writes(page) == 0


@pytest.mark.parametrize("lang,width", [("en", 390), ("zh", 320)])
@pytest.mark.parametrize("panel", ["memory", "memory:continuation"])
def test_r4_generic_and_valid_current_reviews_remain_distinct(snapshot_page, lang, width, panel):
    page = snapshot_page(lang=lang, width=width, start="#scenarios?h=30&panel=" + quote(panel))
    _wait_drawer(page, panel, "Historical review" if lang == "en" else "历史检验")
    source = _scenario(page)
    content = page.locator("#cri-dialog-body")
    text = content.inner_text()
    assert ("No qualified comparison yet" if lang == "en" else "暂无合格的历史比较") in text
    assert source["as_of"] in text and ("30 days" if lang == "en" else "30天") in text
    assert (source["title_" + lang] in text) == (panel == "memory:continuation")
    assert content.get_by_role("button", name="Browse scenarios" if lang == "en" else "浏览情景", exact=True).count() == 0
    assert content.locator("[data-snapshot-action]").count() == 0
    page.keyboard.press("Escape")
    _wait_closed(page)
    assert page.locator("#scenarios-title").evaluate("n=>document.activeElement===n")
    assert _writes(page) == 0
