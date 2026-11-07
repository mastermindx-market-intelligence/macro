"""Observe the six bounded early-navigation cases through the real fixture driver.

Default: 1440 EN/light cold + same-context reload, a separate 250 ms theme.js
delay, 900 ZH/dark, 901 ZH/light, and 1440 ZH/dark. A reload is not proof of an
HTTP-cache hit: Playwright routing can disable the cache; timings are recorded.

    python3 mockups/options_workspace_revamp/verify_early_navigation.py \
        --output early_navigation_report_r3.json

Optional production smoke: ONE 1440 EN/light cold case. Only the existing
loopback theme.js request is fulfilled with the actual generated site/theme.js
bytes. The five exact navigation-index URLs below use captured public R2
responses, checked against their capture manifest and known byte hashes. These
current supplemental catalogs are separate from the frozen Options fixture.
No index is invented or rewritten; missing or changed captures fail before
browser startup. All other routing remains canonical.
No fixture HTML, production source, or previous evidence is changed.

    python3 mockups/options_workspace_revamp/verify_early_navigation.py \
        --theme-bundle production --output early_navigation_production_report.json

Uses the existing server at 127.0.0.1:8768. Output must be a new local filename.
CLS/attribution are raw lab observations, never a production Web Vitals verdict.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlencode, urljoin, urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

import capture_canonical_evidence as fixture_capture
from inspect_layout_shift import TRACE_SCRIPT, fingerprint

URL = fixture_capture.ORIGIN + "/mockups/options_workspace_revamp/fixtures/published/workspace.html"
CASES = (
    ("1440-en-light-cold", 1440, "en", "light", 0, False),
    ("1440-en-light-context-reload", 1440, "en", "light", 0, True),
    ("1440-en-light-theme-delayed-250ms", 1440, "en", "light", 250, False),
    ("900-zh-dark", 900, "zh", "dark", 0, False),
    ("901-zh-light", 901, "zh", "light", 0, False),
    ("1440-zh-dark", 1440, "zh", "dark", 0, False),
)
CATALOG_DIRECTORY = "mockups/options_workspace_revamp/fixtures/search_catalogs"
SEARCH_INDEX_CACHE_DIR = ROOT / CATALOG_DIRECTORY
CATALOG_MANIFEST = CATALOG_DIRECTORY + "/manifest.json"
CATALOG_BASE = "https://pub-f7ffb4441c5f4ad983ca56ec7c651c61.r2.dev"
CATALOG_SOURCE_PIN = "ba7947223ae58f436d4cfadbedc28454b10483fc"
# Actual public responses captured on 2026-11-03; these are not invented data
# or a claim that the catalogs share the Options dataset's historical date.
CATALOG_CAPTURES = {
    "stockdata": (361399, 2949, "9651d499730174fe60c6599c6a833bf3a22776afbdee0ce1eb3be6cfff2b0c93"),
    "chinastockdata": (315566, 1770, "3c5016d1d1da030b23b82d81659c447f5edb0aa86fc95c848464721466ce73f6"),
    "hkstockdata": (26019, 163, "dd89d4abe6a7948ee0c2b8ee52b97bdcde9180e99e5a3bd5efa92abf91f63981"),
    "canadastockdata": (30556, 231, "0a9df45a768d62811696e89741f2b72e0b54e9bcb600128b663abd21b45d3cc9"),
    "intlstockdata": (176228, 989, "a89318ef8ef15f1e4f13376c60be4a6bd474af0017baa4e6763a8f587b0cc405"),
}
SEARCH_INDEX_FILES = {
    "/templates/" + market + "/index.json": CATALOG_DIRECTORY + "/" + market + "/index.json"
    for market in CATALOG_CAPTURES
}
SOURCES = (
    "templates/options.html.j2", "templates/theme.js", "site/theme.js",
    "templates/_site_nav.html.j2", "templates/theme.css", "site/theme.css",
    "scripts/build_options_command.py", "scripts/capture_page_evidence.py",
    "mockups/options_workspace_revamp/capture_canonical_evidence.py",
    "mockups/options_workspace_revamp/inspect_layout_shift.py",
    "mockups/options_workspace_revamp/fixture_assets.py",
    "mockups/options_workspace_revamp/verify_early_navigation.py",
    "mockups/options_workspace_revamp/fixtures/published/workspace.html",
    "mockups/options_workspace_revamp/fixtures/published/payloads.json",
    "mockups/options_workspace_revamp/fixtures/published/manifest.json",
) + (CATALOG_MANIFEST,) + tuple(SEARCH_INDEX_FILES.values())

# Selectors follow templates/theme.js: initNavSearch, initSettings,
# initMobileNav and initAdaptiveNav; main follows options.html.j2.
NAV_TRACE_SCRIPT = r"""
(() => {
  const audit = window.__oewEarlyNavAudit = {snapshots: [], truncated: false};
  const rect = el => {
    if (!el) return null;
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    return {x:r.x, y:r.y, top:r.top, right:r.right, bottom:r.bottom,
      left:r.left, width:r.width, height:r.height, display:s.display,
      visibility:s.visibility, opacity:s.opacity,
      visible:!!(r.width && r.height && s.display !== 'none' && s.visibility !== 'hidden')};
  };
  const snapshot = name => {
    const nav = document.querySelector('.site-nav, .topbar');
    const find = sel => nav && nav.querySelector(sel);
    const count = sel => document.querySelectorAll(sel).length;
    const active = document.activeElement;
    const value = {name, time:performance.now(), readyState:document.readyState,
      theme:document.documentElement.getAttribute('data-theme'),
      locale:document.documentElement.getAttribute('data-lang'),
      viewport:{width:innerWidth, height:innerHeight, scrollX, scrollY},
      scrollWidth:Math.max(document.documentElement.scrollWidth, document.body ? document.body.scrollWidth : 0),
      main:rect(document.querySelector('#options-workspace')), nav:rect(nav),
      search:rect(find('.nav-search')), controls:rect(find('.nav-ctrls')),
      links:rect(find('.nav-links')), toggle:rect(find('.nav-toggle')),
      settings:rect(document.getElementById('settings-open')),
      searchInput:rect(find('.ticker-input')), settingsPop:rect(document.getElementById('settings-pop')),
      layout:nav && nav.getAttribute('data-nav-layout'),
      adaptiveReady:nav && nav.getAttribute('data-adaptive-nav-ready'),
      counts:{nav:count('.site-nav, .topbar'), search:count('.nav-search'),
        enhancedSearch:count('.nav-search.ticker-search[data-ticker-search-ready="1"]'),
        controls:count('.nav-ctrls'), settingsOpen:count('#settings-open'),
        settingsPop:count('#settings-pop'), toggle:count('.nav-toggle')},
      active:active ? {tag:active.tagName, id:active.id, className:active.className} : null};
    if (audit.snapshots.length < 40) audit.snapshots.push(value); else audit.truncated = true;
    return value;
  };
  window.__oewEarlyNavSnapshot = snapshot;
  const mainObserver = new MutationObserver(() => {
    if (!document.getElementById('options-workspace')) return;
    snapshot('main-first-observed'); mainObserver.disconnect();
    requestAnimationFrame(() => snapshot('first-frame-with-main'));
  });
  mainObserver.observe(document, {subtree:true, childList:true});
  document.addEventListener('DOMContentLoaded', () => snapshot('DOMContentLoaded-before-later-handlers'), {once:true});
  window.addEventListener('load', () => snapshot('window-load'), {once:true});
})();
"""


class FixtureStructure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.order, self.scripts, self.preloads, self.main_order = 0, [], [], None

    def handle_starttag(self, tag, attrs):
        self.order += 1
        attrs = dict(attrs)
        if tag == "main" and attrs.get("id") == "options-workspace":
            self.main_order = self.order
        if tag == "script" and attrs.get("src"):
            src = urljoin(URL, attrs["src"])
            if urlsplit(src).path.endswith("/theme.js"):
                self.scripts.append({"url": src, "order": self.order, "attrs": attrs})
        if tag == "link" and attrs.get("rel") == "preload" and attrs.get("as") == "script":
            self.preloads.append(urljoin(URL, attrs.get("href", "")))


def same_origin(url):
    return urlsplit(url)[:2] == urlsplit(fixture_capture.ORIGIN)[:2]


def load_search_indices():
    cache_root = SEARCH_INDEX_CACHE_DIR.resolve()
    if not cache_root.is_relative_to(ROOT.resolve()):
        raise RuntimeError("Search catalog cache resolves outside the repository root")
    missing = [name for name in (CATALOG_MANIFEST, *SEARCH_INDEX_FILES.values()) if not (ROOT / name).is_file()]
    if missing:
        raise RuntimeError("Actual captured R2 catalog files are required before running: " + ", ".join(missing))
    manifest = json.loads((ROOT / CATALOG_MANIFEST).read_bytes())
    if not (manifest.get("schema") == "mastermind.options.search_catalog_capture.v1"
            and manifest.get("source_owner")
            and manifest.get("source_pin") == CATALOG_SOURCE_PIN
            and manifest.get("canonical_base") == CATALOG_BASE
            and manifest.get("production_files_modified") is False):
        raise RuntimeError("Search catalog capture manifest has unexpected schema or source provenance")
    records = manifest.get("records")
    if not isinstance(records, list) or len(records) != len(CATALOG_CAPTURES):
        raise RuntimeError("Search catalog capture manifest must contain exactly five records")
    by_url = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("url"), str) or record["url"] in by_url:
            raise RuntimeError("Search catalog capture contains a malformed or duplicate URL record")
        by_url[record["url"]] = record
    expected_urls = {CATALOG_BASE + "/" + market + "/index.json" for market in CATALOG_CAPTURES}
    if set(by_url) != expected_urls:
        raise RuntimeError("Search catalog capture URLs do not match the five canonical R2 catalog URLs")
    assets = {}
    for request_path, relative in SEARCH_INDEX_FILES.items():
        market = request_path.split("/")[2]
        canonical_url = CATALOG_BASE + "/" + market + "/index.json"
        record = by_url[canonical_url]
        expected_bytes, expected_count, expected_sha = CATALOG_CAPTURES[market]
        if not (record.get("status") == 200 and record.get("market")
                and record.get("path") == market + "/index.json"
                and record.get("bytes") == expected_bytes
                and record.get("count") == expected_count
                and record.get("sha256") == expected_sha
                and isinstance(record.get("content_type"), str)
                and "json" in record["content_type"].lower()
                and "etag" in record
                and isinstance(record.get("contains_nvda"), bool)):
            raise RuntimeError("Search catalog capture metadata mismatch: " + market)
        retrieved_at = datetime.fromisoformat(record["retrieved_at"].replace("Z", "+00:00"))
        if retrieved_at.tzinfo is None or (market == "stockdata" and record["contains_nvda"] is not True):
            raise RuntimeError("Search catalog capture lacks dated provenance or the observed US NVDA entry: " + market)
        capture_path = (cache_root / record["path"]).resolve()
        if not capture_path.is_relative_to(cache_root) or not capture_path.is_relative_to(ROOT.resolve()):
            raise RuntimeError("Search catalog response resolves outside its fixed cache directory: " + market)
        body = capture_path.read_bytes()
        sha256 = hashlib.sha256(body).hexdigest()
        if len(body) != expected_bytes or sha256 != expected_sha:
            raise RuntimeError("Captured search catalog bytes differ from manifest and accepted capture: " + market)
        json.loads(body)  # Validate, but fulfill the original bytes unchanged.
        assets[request_path] = {"body": body, "source_path": relative, "bytes": len(body),
            "sha256": sha256, "canonical_url": canonical_url,
            "content_type": record["content_type"], "capture_record": record,
            "git_blob_sha1": hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()}
    return assets, manifest


def route_failure(route, record, stage, error):
    detail = {"stage": stage, "url": route.request.url,
              "error": type(error).__name__ + ": " + str(error)}
    bounded_append(record, "route_errors", detail)
    print(json.dumps({"route_error": detail}), file=sys.stderr, flush=True)
    # Fail the original request promptly, without retrying its fulfillment.
    try:
        route.abort()
    except Exception as abort_error:
        detail["abort_error"] = type(abort_error).__name__ + ": " + str(abort_error)


def theme_asset_handler(delay_ms, production, body, current):
    # Playwright may pass (route, request) to two-argument callbacks. Keep the
    # returned callback strictly one-argument; capture the delay in this factory.
    def handle(route):
        record = current["record"]
        event = {"url": route.request.url, "requested_ms": delay_ms, "completed": False}
        started = time.monotonic()
        if delay_ms:
            record["delay_events"].append(event)
        try:
            if delay_ms:
                time.sleep(delay_ms / 1000)
                event["actual_wait_ms"] = (time.monotonic() - started) * 1000
            if production:
                route.fulfill(status=200, content_type="application/javascript", body=body)
            else:
                route.fallback()
            event["completed"] = True
        except Exception as error:
            route_failure(route, record, "theme-asset", error)
    return handle


def search_index_handler(assets, current):
    def handle(route):
        asset = assets.get(urlsplit(route.request.url).path) if same_origin(route.request.url) else None
        if asset is None:
            route.fallback()
            return
        record = current["record"]
        try:
            route.fulfill(status=200, content_type=asset["content_type"], body=asset["body"])
            bounded_append(record, "index_route_receipts", {"url": route.request.url,
                **{key: value for key, value in asset.items() if key != "body"}})
        except Exception as error:
            route_failure(route, record, "search-index", error)
    return handle


def check(record, name, passed, detail=None):
    record["checks"].append({"name": name, "passed": bool(passed), "detail": detail})


def bounded_append(record, key, value):
    values = record.setdefault(key, [])
    if len(values) < 150:
        values.append(value)
    else:
        record.setdefault("truncated_events", {})[key] = True


def snapshot(page, name):
    return page.evaluate("name => { window.__oewLayoutShiftSnapshot(name); return window.__oewEarlyNavSnapshot(name); }", name)


def wait_check(page, record, name, expression):
    try:
        page.wait_for_function(expression, timeout=4000)
        check(record, name, True)
    except Exception as error:
        check(record, name, False, type(error).__name__ + ": " + str(error))
        raise


def assert_geometry(record, geometry, prefix, required=("main", "search", "controls", "settings")):
    check(record, prefix + ":no-overflow", geometry["scrollWidth"] <= geometry["viewport"]["width"] + 1,
          {"scrollWidth": geometry["scrollWidth"], "viewport": geometry["viewport"]})
    for name in required:
        r = geometry.get(name)
        check(record, prefix + ":" + name + "-visible-within-width", r and r["visible"] and
              r["left"] >= -1 and r["right"] <= geometry["viewport"]["width"] + 1, r)


def interactions(page, record):
    record["phase"] = "interaction"
    trigger = page.locator('.nav-search.ticker-search .search-trigger')
    field = page.locator('.nav-search.ticker-search .ticker-input')
    trigger.click()
    wait_check(page, record, "search-pointer-open-and-input-focus", """() => {
      const b=document.querySelector('.nav-search.ticker-search'), i=b.querySelector('.ticker-input');
      return b.classList.contains('open') && b.querySelector('.search-trigger').getAttribute('aria-expanded')==='true' && document.activeElement===i;
    }""")
    field.fill("NVDA")
    check(record, "search-accepts-input", field.input_value() == "NVDA")
    # Expanded search may intentionally hide other navigation controls.
    assert_geometry(record, snapshot(page, "search-pointer-open"), "search-open", ("main", "search", "searchInput"))
    field.press("Escape")
    closed = """() => { const b=document.querySelector('.nav-search.ticker-search'), t=b.querySelector('.search-trigger');
      return !b.classList.contains('open') && t.getAttribute('aria-expanded')==='false' && document.activeElement===t; }"""
    wait_check(page, record, "search-escape-closes-and-restores-focus", closed)
    trigger.press("Enter")
    wait_check(page, record, "search-keyboard-opens", "() => document.activeElement===document.querySelector('.nav-search .ticker-input') && document.querySelector('.search-trigger').getAttribute('aria-expanded')==='true'")
    field.press("Escape")
    wait_check(page, record, "search-keyboard-escape-closes", closed)
    snapshot(page, "search-closed")

    gear = page.locator('#settings-open')
    opened = "() => document.querySelector('#settings-pop').classList.contains('open') && document.querySelector('#settings-open').getAttribute('aria-expanded')==='true' && document.activeElement===document.querySelector('#settings-pop')"
    settings_closed = "() => !document.querySelector('#settings-pop').classList.contains('open') && document.querySelector('#settings-open').getAttribute('aria-expanded')==='false' && document.activeElement===document.querySelector('#settings-open') && getComputedStyle(document.querySelector('#settings-pop')).visibility==='hidden'"
    gear.click()
    wait_check(page, record, "settings-pointer-opens-dialog", opened)
    snapshot(page, "settings-pointer-open")
    page.keyboard.press("Escape")
    wait_check(page, record, "settings-escape-closes-and-restores-focus", settings_closed)
    page.keyboard.press("Shift+Tab")
    wait_check(page, record, "settings-keyboard-leaves-control", "() => !document.querySelector('.nav-settings').contains(document.activeElement)")
    page.keyboard.press("Tab")
    wait_check(page, record, "settings-tab-opens-dialog", opened)
    snapshot(page, "settings-keyboard-open")
    page.keyboard.press("Escape")
    wait_check(page, record, "settings-keyboard-escape-closes", settings_closed)

    if record["viewport"]["width"] <= 900:
        page.locator('.nav-toggle').click()
        wait_check(page, record, "mobile-nav-opens", "() => document.querySelector('.nav-toggle').getAttribute('aria-expanded')==='true' && getComputedStyle(document.querySelector('.nav-links')).display!=='none'")
        snapshot(page, "mobile-navigation-open")
        page.keyboard.press("Escape")
        wait_check(page, record, "mobile-nav-escape-closes", "() => document.querySelector('.nav-toggle').getAttribute('aria-expanded')==='false' && getComputedStyle(document.querySelector('.nav-links')).display==='none'")
    assert_geometry(record, snapshot(page, "interactions-complete"), "after-interactions")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="early_navigation_report_r3.json")
    parser.add_argument("--theme-bundle", choices=("fixture", "production"), default="fixture",
                        help="fixture: six cases; production: one desktop smoke using actual built bytes")
    args = parser.parse_args(argv)
    output = (HERE / args.output).resolve()
    if output.parent != HERE or output.suffix != ".json" or output.exists():
        parser.error("--output must be a NEW JSON filename directly in this verifier's directory")
    cases = CASES[:1] if args.theme_bundle == "production" else CASES
    report = {"schema": "mastermind.options.early_navigation.v1", "generated_at": datetime.now(timezone.utc).isoformat(),
              "outcome": "pending", "url": URL, "theme_bundle": args.theme_bundle, "expected_cases": len(cases),
              "restrictions": {"authentication_supplied": False, "service_workers": "block",
                "network": "canonical fixture network guard; exact loopback theme asset plus five manifest-validated cached public R2 responses only; no catalog network fetch",
                "source_or_canonical_evidence_modified": False,
                "reload": "same context and page; no HTTP-cache-hit claim; resource timings retained",
                "cls": "raw instrumented lab observation; no numerical or production acceptance gate",
                "production_smoke": "built bytes at fixture asset URL; not production deployment or URL-placement proof"},
              "source_fingerprints": {name: fingerprint(ROOT / name) for name in SOURCES}, "cases": []}
    driver = context = page = None
    current, owners = {"record": None}, {}
    theme_responses, index_responses = {}, {}
    try:
        payloads = fixture_capture.load_current_fixture()
        search_assets, catalog_manifest = load_search_indices()
        report["navigation_index_capture_manifest"] = catalog_manifest
        report["navigation_index_sources"] = {request_path: {key: value for key, value in asset.items() if key != "body"}
            for request_path, asset in search_assets.items()}
        report["navigation_index_provenance"] = "Supplemental current public R2 catalog responses captured on 2026-11-03; original HTTP 200 metadata and bytes validated against the capture manifest and accepted SHA-256 values. The routing source pin identifies the data_base.js owner, not a frozen catalog dataset. Historical Options fixture payloads and their separate pin remain unchanged. This is mixed-source fixture evidence, not a fresh Options-data or production-deployment claim."
        structure = FixtureStructure()
        structure.feed((fixture_capture.SOURCE / "workspace.html").read_text(encoding="utf-8"))
        if len(structure.scripts) != 1:
            raise RuntimeError("Fixture must contain exactly one theme.js owner")
        owner = structure.scripts[0]
        a = owner["attrs"]
        if not (same_origin(owner["url"]) and "data-sync" in a and "data-nav-early" in a and
                "async" not in a and "defer" not in a and structure.main_order and owner["order"] < structure.main_order and
                owner["url"] in structure.preloads):
            raise RuntimeError("Fixture lacks the synchronous pre-main owner and matching script preload")
        path = urlsplit(owner["url"]).path
        if path not in ("/templates/theme.js", "/site/theme.js"):
            raise RuntimeError("Unexpected theme asset path; preserve the existing loopback boundary")
        report["fixture_structure"] = {"owner": owner, "main_order": structure.main_order, "preloads": structure.preloads}
        body_path = ROOT / ("site/theme.js" if args.theme_bundle == "production" else path.lstrip("/"))
        expected_body = body_path.read_bytes()
        expected_sha = hashlib.sha256(expected_body).hexdigest()
        report["served_theme_expected"] = {"file": str(body_path.relative_to(ROOT)), "sha256": expected_sha,
                                           "bytes": len(expected_body), "asset_url": owner["url"]}
        report["compiled_bundle_requested"] = args.theme_bundle == "production" or path == "/site/theme.js"
        from scripts import capture_page_evidence as canonical

        def request_owner(request):
            return owners.get(request) or current["record"]

        def on_request(request):
            if current["record"] is not None:
                owners[request] = current["record"]

        def on_response(response):
            record = request_owner(response.request)
            if record is None:
                return
            if response.status >= 400:
                bounded_append(record, "failed_responses", {"url": response.url, "status": response.status})
            if same_origin(response.url) and urlsplit(response.url).path == path:
                theme_responses.setdefault(record["id"], []).append(response)
            if same_origin(response.url) and urlsplit(response.url).path in search_assets:
                index_responses.setdefault(record["id"], []).append(response)

        def on_failed(request):
            record = request_owner(request)
            if record is not None:
                bounded_append(record, "failed_requests", {"url": request.url, "failure": request.failure,
                    "resource_type": request.resource_type, "external": not same_origin(request.url)})

        with fixture_capture.repository_directory():
            driver = fixture_capture.fixture_driver_factory(canonical, payloads)(headless=True, settle_ms=1300)
            report["browser_version"] = driver._browser.version
            for index, (case_id, width, locale, theme, delay_ms, reload) in enumerate(cases):
                case_url = URL + "?" + urlencode({"theme": theme, "lang": locale})
                record = {"id": case_id, "viewport": {"width": width, "height": 900},
                          "url": case_url,
                          "requested_state": {"theme": theme, "locale": locale}, "load_kind": "context-reload" if reload else "cold-context",
                          "phase": "load", "checks": [], "console_errors": [], "page_errors": [],
                          "failed_responses": [], "failed_requests": [], "delay_events": [],
                          "route_errors": [], "index_route_receipts": [], "outcome": "pending"}
                report["cases"].append(record)
                if not reload:
                    if context is not None:
                        context.close()
                    current["record"] = record
                    context = driver._browser.new_context(viewport=record["viewport"], user_agent=canonical.USER_AGENT,
                        locale="zh-CN" if locale == "zh" else "en-US", color_scheme=theme,
                        device_scale_factor=1, accept_downloads=False)
                    record["context_group"] = case_id
                    context.add_init_script(canonical.state_seed_source(record["requested_state"]))
                    context.add_init_script(canonical.timing_init_source())
                    context.add_init_script(TRACE_SCRIPT)
                    context.add_init_script(NAV_TRACE_SCRIPT)
                    index_pattern = r"^" + re.escape(fixture_capture.ORIGIN) + "(?:" + "|".join(re.escape(p) for p in SEARCH_INDEX_FILES) + r")(?:\?.*)?$"
                    context.route(re.compile(index_pattern), search_index_handler(search_assets, current))
                    if delay_ms or args.theme_bundle == "production":
                        bare = owner["url"].split("?", 1)[0]
                        context.route(re.compile(r"^" + re.escape(bare) + r"(?:\?.*)?$"),
                                      theme_asset_handler(delay_ms, args.theme_bundle == "production", expected_body, current))
                    page = context.new_page()
                    page.set_default_timeout(5000)
                    page.on("request", on_request)
                    page.on("response", on_response)
                    page.on("requestfailed", on_failed)
                    page.on("pageerror", lambda error: bounded_append(current["record"], "page_errors", str(error)))
                    page.on("console", lambda message: bounded_append(current["record"], "console_errors",
                        {"text": message.text, "location": message.location}) if message.type == "error" else None)
                else:
                    current["record"] = record
                    record["context_group"] = report["cases"][index - 1]["context_group"]
                    record["reloads_case"] = report["cases"][index - 1]["id"]
                    check(record, "successful-cold-predecessor", report["cases"][index - 1]["outcome"] == "passed")
                try:
                    response = page.reload(wait_until="load", timeout=30000) if reload else page.goto(case_url, wait_until="load", timeout=30000)
                    if response is None or not response.ok:
                        raise RuntimeError("Fixture navigation failed: " + str(response.status if response else None))
                    initial_geometry = snapshot(page, "goto-load-resolved")
                    record["initial_loaded_state"] = {"url": page.url, "theme": initial_geometry["theme"], "locale": initial_geometry["locale"]}
                    check(record, "requested-state-at-initial-load", initial_geometry["theme"] == theme and initial_geometry["locale"] == locale,
                          record["initial_loaded_state"])
                    page.wait_for_timeout(1300)
                    snapshot(page, "before-canonical-state-reapply")
                    record["applied_state"] = page.evaluate(canonical._APPLY_STATE_SCRIPT.strip(), record["requested_state"])
                    canonical._wait_transient_fx_gone(page)
                    page.wait_for_timeout(1300)
                    geometry = snapshot(page, "after-canonical-state-reapply")
                    record["canonical_timing_snapshot"] = page.evaluate(canonical._TIMING_SNAPSHOT_SCRIPT.strip())
                    record["pre_interaction_observation"] = page.evaluate("() => ({time:performance.now(), shiftCount:window.__oewLayoutShiftAudit.shiftCount, clsWithoutRecentInput:window.__oewLayoutShiftAudit.clsWithoutRecentInput})")
                    check(record, "single-nav-enhancements", all(v == 1 for v in geometry["counts"].values()), geometry["counts"])
                    check(record, "requested-state-applied", geometry["theme"] == theme and geometry["locale"] == locale,
                          {"theme": geometry["theme"], "locale": geometry["locale"]})
                    check(record, "adaptive-navigation-ready", geometry["adaptiveReady"] == "1")
                    check(record, "responsive-navigation", (geometry["layout"] is None and geometry["toggle"]["visible"] and not geometry["links"]["visible"]) if width <= 900 else
                          (geometry["layout"] in ("single", "stacked") and not geometry["toggle"]["visible"] and geometry["links"]["visible"]),
                          {k: geometry[k] for k in ("layout", "toggle", "links")})
                    assert_geometry(record, geometry, "rest")
                    interactions(page, record)
                    page.wait_for_timeout(300)
                except Exception as error:
                    record["error"] = type(error).__name__ + ": " + str(error)
                finally:
                    for key, expression in (("trace", "window.__oewLayoutShiftAudit || null"),
                                            ("navigation_trace", "window.__oewEarlyNavAudit || null"),
                                            ("resource_timings", "performance.getEntriesByType('resource').filter(x=>/\\/theme\\.js(?:\\?|$)/.test(x.name)).map(x=>({name:x.name,initiatorType:x.initiatorType,startTime:x.startTime,duration:x.duration,transferSize:x.transferSize,encodedBodySize:x.encodedBodySize,decodedBodySize:x.decodedBodySize,deliveryType:x.deliveryType||null}))"),
                                            ("navigation_type", "performance.getEntriesByType('navigation')[0]?.type || null")):
                        try:
                            record[key] = page.evaluate(expression)
                        except Exception as error:
                            record.setdefault("observation_errors", []).append(key + ": " + str(error))
                    record["served_theme_responses"] = []
                    for response in theme_responses.get(case_id, []):
                        try:
                            body = response.body()
                            record["served_theme_responses"].append({"url": response.url, "status": response.status,
                                "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
                        except Exception as error:
                            record.setdefault("observation_errors", []).append("theme-response-body: " + str(error))
                    served = record["served_theme_responses"]
                    check(record, "actual-served-theme-matches-source", bool(served) and all(x["sha256"] == expected_sha for x in served), served)
                    record["served_index_responses"] = []
                    for response in index_responses.get(case_id, []):
                        try:
                            body = response.body()
                            expected = search_assets[urlsplit(response.url).path]
                            record["served_index_responses"].append({"url": response.url, "status": response.status,
                                "source_path": expected["source_path"], "canonical_url": expected["canonical_url"], "bytes": len(body),
                                "sha256": hashlib.sha256(body).hexdigest(), "expected_sha256": expected["sha256"]})
                        except Exception as error:
                            record.setdefault("observation_errors", []).append("index-response-body: " + str(error))
                    served_indices = record["served_index_responses"]
                    check(record, "actual-navigation-indices-match-source", bool(served_indices) and
                          all(x["status"] == 200 and x["sha256"] == x["expected_sha256"] for x in served_indices), served_indices)
                    observed_index_paths = {urlsplit(x["url"]).path for x in served_indices}
                    check(record, "all-five-real-navigation-indices-observed", observed_index_paths == set(search_assets),
                          {"observed": sorted(observed_index_paths), "expected": sorted(search_assets)})
                    check(record, "no-route-handler-errors", not record["route_errors"], record["route_errors"])
                    if delay_ms:
                        check(record, "requested-delay-observed", bool(record["delay_events"]) and all(x["completed"] and x.get("actual_wait_ms", 0) >= delay_ms for x in record["delay_events"]), record["delay_events"])
                    if reload:
                        check(record, "actual-reload-navigation", record.get("navigation_type") == "reload", record.get("navigation_type"))
                    external_failed = {x["url"] for x in record["failed_requests"] if x["external"]}
                    record["expected_sandbox_console_errors"] = [x for x in record["console_errors"] if x.get("location", {}).get("url") in external_failed and ("Failed to load resource" in x["text"] or "net::ERR_" in x["text"])]
                    record["unexpected_console_errors"] = [x for x in record["console_errors"] if x not in record["expected_sandbox_console_errors"]]
                    check(record, "no-page-errors", not record["page_errors"], record["page_errors"])
                    check(record, "no-unexpected-console-errors", not record["unexpected_console_errors"], record["unexpected_console_errors"])
                    check(record, "no-loopback-http-errors", not any(same_origin(x["url"]) for x in record["failed_responses"]), record["failed_responses"])
                    check(record, "observers-complete", bool(record.get("trace")) and not record["trace"].get("observerErrors") and not record.get("observation_errors"))
                    nav_trace = record.get("navigation_trace") or {}
                    early = next((x for x in nav_trace.get("snapshots", []) if x["name"] == "DOMContentLoaded-before-later-handlers"), None)
                    check(record, "enhanced-before-dom-ready-fallback", early and early["adaptiveReady"] == "1" and
                          all(v == 1 for v in early["counts"].values()), early)
                    record["outcome"] = "passed" if not record.get("error") and all(x["passed"] for x in record["checks"]) else "failed"
                    record["phase"] = "complete"
            report["outcome"] = "passed" if len(report["cases"]) == len(cases) and all(x["outcome"] == "passed" for x in report["cases"]) else "failed"
    except Exception as error:
        report["outcome"] = "failed"
        report["error"] = type(error).__name__ + ": " + str(error)
    finally:
        for name, resource in (("context", context), ("driver", driver)):
            if resource is not None:
                try:
                    resource.close()
                except Exception as error:
                    report.setdefault("cleanup_errors", []).append(name + ": " + str(error))
        report["source_fingerprints_after"] = {name: fingerprint(ROOT / name) for name in SOURCES}
        report["sources_unchanged_during_run"] = report["source_fingerprints"] == report["source_fingerprints_after"]
        if not report["sources_unchanged_during_run"] or report.get("cleanup_errors"):
            report["outcome"] = "failed"
        report["compiled_bundle_smoke_passed"] = bool(report.get("compiled_bundle_requested") and report["outcome"] == "passed")
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({"outcome": report["outcome"], "report": str(output), "cases": [
        {"id": c["id"], "outcome": c["outcome"], "raw_cls": c.get("pre_interaction_observation", {}).get("clsWithoutRecentInput"),
         "failed_checks": [x["name"] for x in c["checks"] if not x["passed"]]} for c in report["cases"]]}))
    return 0 if report["outcome"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
