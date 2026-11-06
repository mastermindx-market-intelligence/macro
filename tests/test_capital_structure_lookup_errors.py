#!/usr/bin/env python3
"""Behaviour-level regression tests for the F09 ticker-lookup error
classification in ``capital_structure.js``.

The live bug: an authenticated AAPL lookup that returned HTTP 404 "ticker not
covered" was reported by the desk as "Ticker lookup is temporarily
unavailable", a false outage claim that also left the previously selected
issuer looking like the failed query.

These tests execute the real script under Node in a bounded fake DOM/fetch
harness and drive the actual ``resolveTicker`` code path -- the search input
receives a value and an Enter keydown, exactly as a reader would send -- then
reads the rendered notice back out of the fake DOM. No assertion inspects the
script source, and no expected string is derived from it: the buggy revision
runs through the identical harness and fails the error-classification cases,
which is the red control.

Harness contract
----------------
* ``document.readyState`` is ``'loading'`` while the script is evaluated, so
  the desk registers ``init`` behind the ``DOMContentLoaded`` listener stub;
  the harness then fires that listener once, as a browser would, and the desk
  initialises through its own production path (cacheUi/bind/load).
* ``fetch`` is routed: ``/coverage`` and ``/overview`` return a small fresh
  projection containing Microsoft (``msft-1``) and Apple (``aapl-1``), so the
  desk auto-selects ``msft-1`` and renders its dossier before any lookup is
  attempted.
* The resolver endpoint answers with the scenario's HTTP status (or a network
  rejection, or an envelope body), so each classification branch of
  ``resolveTicker`` is exercised for real, and every request URL is recorded
  so the request path/encoding can be asserted unchanged.

Run: ``python3 test_capital_structure_lookup_errors.py``. Set
``CAPITAL_STRUCTURE_JS`` to test a specific revision; the default is
``capital_structure.js`` beside this file.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

API_BASE = "/api/capital-structure/v1"

# Rendered notice strings, keyed by classification and UI language. These are
# the customer-facing contracts under test, asserted against what the desk
# actually wrote into the status region of the fake DOM.
EXPECTED = {
    "covered_absent": {
        "en": 'No observed issuer matched ticker "{ticker}"',
        "zh": "没有已观察发行人匹配代码“{ticker}”",
    },
    "invalid": {
        "en": '"{ticker}" is not a valid ticker symbol',
        "zh": "“{ticker}”不是有效的股票代码",
    },
    "ambiguous": {
        "en": 'Ticker "{ticker}" matches more than one observed issuer; refine the search to choose one.',
        "zh": "代码“{ticker}”匹配多个已观察发行人，请细化搜索后再选择。",
    },
    "sign_in": {
        "en": "Sign in with an eligible account to search tickers.",
        "zh": "请使用符合条件的账户登录后搜索代码。",
    },
    "temporary": {
        "en": "Ticker lookup is temporarily unavailable",
        "zh": "代码查找暂时不可用",
    },
}

HARNESS_JS = r"""
'use strict';

// Bounded fake DOM/fetch harness for one scenario:
//   node harness.js <capital_structure.js> <scenario.json>
// Prints one JSON line describing what the desk rendered and requested.

const fs = require('fs');
const vm = require('vm');

function fail(message) {
  process.stderr.write('HARNESS ERROR: ' + message + '\n');
  process.exit(3);
}

const jsPath = process.argv[2];
const scenarioPath = process.argv[3];
if (!jsPath || !scenarioPath) fail('usage: node harness.js <capital_structure.js> <scenario.json>');

const scenario = JSON.parse(fs.readFileSync(scenarioPath, 'utf8'));
const source = fs.readFileSync(jsPath, 'utf8');

class FakeClassList {
  constructor() { this.tokens = new Set(); }
  add() { for (let i = 0; i < arguments.length; i += 1) this.tokens.add(arguments[i]); }
  remove() { for (let i = 0; i < arguments.length; i += 1) this.tokens.delete(arguments[i]); }
  toggle(token, force) {
    const has = this.tokens.has(token);
    const next = force === undefined ? !has : Boolean(force);
    if (next) this.tokens.add(token); else this.tokens.delete(token);
    return next;
  }
  contains(token) { return this.tokens.has(token); }
}

class FakeElement {
  constructor(tag) {
    this.tagName = String(tag || 'div').toUpperCase();
    this.attributes = Object.create(null);
    this.listeners = Object.create(null);
    this.childNodes = [];
    this.textContent = '';
    this.value = '';
    this.hidden = false;
    this.disabled = false;
    this.className = '';
    this.classList = new FakeClassList();
    this.offsetParent = null;
    this._innerHTML = '';
  }
  get innerHTML() { return this._innerHTML; }
  set innerHTML(value) { this._innerHTML = String(value); this.childNodes = []; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return Object.prototype.hasOwnProperty.call(this.attributes, name) ? this.attributes[name] : null; }
  removeAttribute(name) { delete this.attributes[name]; }
  addEventListener(type, handler) { (this.listeners[type] = this.listeners[type] || []).push(handler); }
  removeEventListener(type, handler) {
    const list = this.listeners[type] || [];
    const at = list.indexOf(handler);
    if (at !== -1) list.splice(at, 1);
  }
  dispatch(type, event) {
    const payload = event || {};
    payload.type = type;
    payload.target = payload.target || this;
    if (!payload.preventDefault) payload.preventDefault = function () {};
    if (!payload.stopPropagation) payload.stopPropagation = function () {};
    (this.listeners[type] || []).slice().forEach((handler) => handler(payload));
    return payload;
  }
  focus() {}
  querySelector() { return null; }
  querySelectorAll() { return []; }
  closest() { return null; }
}

const elements = Object.create(null);
function byId(id) {
  if (!elements[id]) {
    const node = new FakeElement('div');
    node.id = id;
    elements[id] = node;
  }
  return elements[id];
}

const docListeners = Object.create(null);
const documentElement = new FakeElement('html');
documentElement.setAttribute('data-lang', scenario.lang === 'zh' ? 'zh' : 'en');
const siteNav = new FakeElement('nav');

const fakeDocument = {
  readyState: 'loading',
  documentElement: documentElement,
  body: new FakeElement('body'),
  activeElement: null,
  getElementById: byId,
  querySelector(selector) { return selector === '.site-nav' ? siteNav : null; },
  querySelectorAll() { return []; },
  createElement(tag) { return new FakeElement(tag); },
  addEventListener(type, handler) { (docListeners[type] = docListeners[type] || []).push(handler); },
  removeEventListener() {}
};

const windowListeners = Object.create(null);
const historyCalls = [];
const fakeWindow = {
  location: { href: 'https://desk.example.com/capital-structure', origin: 'https://desk.example.com' },
  history: {
    pushState(stateObj, title, url) { historyCalls.push(['pushState', String(url)]); },
    replaceState(stateObj, title, url) { historyCalls.push(['replaceState', String(url)]); }
  },
  addEventListener(type, handler) { (windowListeners[type] = windowListeners[type] || []).push(handler); },
  removeEventListener() {},
  requestAnimationFrame(handler) { return setTimeout(handler, 0); }
};

const ISSUERS = {
  'msft-1': { ticker: 'MSFT', name: 'Microsoft Corporation', cik: '789019' },
  'aapl-1': { ticker: 'AAPL', name: 'Apple Inc.', cik: '320193' }
};

function overviewRecord(id) {
  const known = ISSUERS[id];
  return {
    issuer_id: id,
    identity: { issuer_id: id, ticker: known.ticker, name: known.name, cik: known.cik, aliases: [known.name] },
    latest_observed_event: {
      form: '10-K',
      lifecycle_state: 'filed',
      classification_state: 'classified',
      filing_date: '2026-10-01',
      clocks: { sec_accepted_at: '2026-10-01T14:03:00Z', mastermind_observed_at: '2026-10-02T09:12:00Z' }
    },
    review: { state: 'classified' }
  };
}

function recordEnvelope(id) {
  const overview = overviewRecord(id);
  return {
    record: Object.assign({}, overview, {
      coverage: { event_count: 2, classified_event_count: 2, review_count: 0 },
      what_changed: [],
      timeline: []
    })
  };
}

const fetchCalls = [];

function okResponse(body) {
  return { ok: true, status: 200, json() { return Promise.resolve(body); } };
}
function statusResponse(status) {
  return { ok: false, status: status, json() { return Promise.resolve({}); } };
}

function fakeFetch(url) {
  const target = String(url);
  fetchCalls.push(target);
  const plan = scenario.fetch || {};
  if (target.indexOf("/issuers/resolve?ticker=PREVIOUS_MISSING") !== -1) return Promise.resolve(statusResponse(404));
  if (target.indexOf('/coverage') !== -1) {
    return Promise.resolve(okResponse({
      freshness: 'fresh',
      horizon_state: 'current',
      as_of: '2026-10-19T00:00:00Z',
      generated_at: '2026-10-19T00:00:00Z',
      issuer_count: 2
    }));
  }
  if (target.indexOf('/overview') !== -1) {
    return Promise.resolve(okResponse({
      items: [overviewRecord('msft-1'), overviewRecord('aapl-1')],
      page: { next_cursor: '' }
    }));
  }
  if (target.indexOf('/issuers/resolve') !== -1) {
    if (plan.resolve === 'network') return Promise.reject(new TypeError('Failed to fetch'));
    if (plan.resolve === 'status') return Promise.resolve(statusResponse(plan.status));
    return Promise.resolve(okResponse(plan.resolveBody));
  }
  const match = /\/issuers\/([^/?]+)(\/events)?/.exec(target);
  if (match) {
    const id = decodeURIComponent(match[1]);
    if (!Object.prototype.hasOwnProperty.call(ISSUERS, id)) return Promise.resolve(statusResponse(404));
    if (match[2]) return Promise.resolve(okResponse({ items: [], next_cursor: '' }));
    return Promise.resolve(okResponse(recordEnvelope(id)));
  }
  return Promise.resolve(statusResponse(404));
}

const context = vm.createContext({
  window: fakeWindow,
  document: fakeDocument,
  fetch: fakeFetch,
  URL: URL,
  setTimeout: setTimeout,
  clearTimeout: clearTimeout
});
vm.runInContext(source, context, { filename: 'capital_structure.js' });

// The desk registered init behind DOMContentLoaded because the harness presents
// readyState 'loading'. Fire it once, like the browser, so init/cacheUi/bind/
// load all run through the production path.
fakeDocument.readyState = 'complete';
(docListeners.DOMContentLoaded || []).forEach((handler) => handler());

function flush() {
  return new Promise((resolve) => {
    let ticks = 0;
    function tick() {
      ticks += 1;
      if (ticks >= 40) { resolve(); return; }
      setTimeout(tick, 0);
    }
    tick();
  });
}

(async function main() {
  await flush();
  const loadedFetchCount = fetchCalls.length;
  if (scenario.prior_failure) {
    const priorSearch = byId('cs-search-input');
    priorSearch.value = 'PREVIOUS_MISSING';
    priorSearch.dispatch('input');
    priorSearch.dispatch('keydown', { key: 'Enter' });
    await flush();
  }
  const priorNotice = byId('cs-coverage-state').textContent;

  // Snapshot the desk exactly as the reader is about to press Enter: the
  // previously selected issuer is on screen and marked current in the rail.
  const preLookup = {
    dossierSymbol: byId('cs-issuer-symbol').textContent,
    dossierBodyHidden: byId('cs-dossier-body').hidden,
    railHtml: byId('cs-issuer-list').innerHTML
  };

  const search = byId('cs-search-input');
  search.value = scenario.ticker;
  search.dispatch('input');
  search.dispatch('keydown', { key: 'Enter' });
  await flush();

  const resolveIndex = fetchCalls.findIndex((url) => url.indexOf('/issuers/resolve') !== -1);
  const result = {
    priorNotice: priorNotice,
    lang: scenario.lang,
    ticker: scenario.ticker,
    loadedFetchCount: loadedFetchCount,
    preLookup: preLookup,
    resolveUrl: resolveIndex === -1 ? null : fetchCalls[resolveIndex],
    postResolveUrls: resolveIndex === -1 ? [] : fetchCalls.slice(resolveIndex + 1),
    noticeText: byId('cs-coverage-state').textContent,
    statusFresh: byId('cs-status').classList.contains('is-fresh'),
    statusDegraded: byId('cs-status').classList.contains('is-degraded'),
    dossierSymbol: byId('cs-issuer-symbol').textContent,
    dossierTitle: byId('cs-dossier-title-live').textContent,
    dossierBodyHidden: byId('cs-dossier-body').hidden,
    railHtml: byId('cs-issuer-list').innerHTML,
    historyCalls: historyCalls
  };
  process.stdout.write(JSON.stringify(result) + '\n');
})().catch((error) => {
  fail((error && (error.stack || error.message)) || String(error));
});
"""


class TickerLookupErrorClassification(unittest.TestCase):
    """Drives the real resolveTicker failure branches in a fake DOM."""

    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        if not cls.node:
            raise unittest.SkipTest("Node.js runtime is required to execute the desk script")
        override = os.environ.get("CAPITAL_STRUCTURE_JS")
        cls.desk_js = Path(override) if override else Path(__file__).resolve().parents[1] / "templates" / "capital_structure.js"
        if not cls.desk_js.is_file():
            raise AssertionError(f"desk script not found: {cls.desk_js}")
        cls._tmp = tempfile.TemporaryDirectory(prefix="cs-lookup-tests-")
        cls.harness_path = Path(cls._tmp.name) / "harness.js"
        cls.harness_path.write_text(HARNESS_JS, encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    # -- harness drivers -------------------------------------------------

    def run_desk(self, ticker, resolve_plan, lang="en", prior_failure=False):
        scenario_path = Path(self._tmp.name) / "scenario.json"
        scenario_path.write_text(
            json.dumps({"lang": lang, "ticker": ticker, "fetch": resolve_plan, "prior_failure": prior_failure}),
            encoding="utf-8",
        )
        proc = subprocess.run(
            [self.node, str(self.harness_path), str(self.desk_js), str(scenario_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            self.fail(
                f"harness exited {proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
            )
        try:
            return json.loads(proc.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError) as error:
            self.fail(f"harness produced no JSON result: {error}\nstdout:\n{proc.stdout}")

    def assertDeskLoadedWithPriorIssuer(self, result):
        """Before the lookup, the desk had loaded and selected msft-1."""
        self.assertGreaterEqual(
            result["loadedFetchCount"], 4, "coverage, overview, record and events must have loaded"
        )
        self.assertEqual(result["preLookup"]["dossierSymbol"], "MSFT")
        self.assertFalse(result["preLookup"]["dossierBodyHidden"])
        self.assertIn('data-issuer-id="msft-1"', result["preLookup"]["railHtml"])
        self.assertIn('aria-current="true"', result["preLookup"]["railHtml"])

    def assertPriorIssuerPreserved(self, result):
        """After a failed lookup the prior selection is still on screen."""
        self.assertEqual(result["dossierSymbol"], "MSFT")
        self.assertFalse(result["dossierBodyHidden"])

    def assertNotice(self, result, key, ticker, lang):
        expected = EXPECTED[key][lang].format(ticker=ticker)
        self.assertEqual(result["noticeText"], expected)
        self.assertFalse(result["statusFresh"])
        if key in ("temporary", "sign_in"):
            self.assertTrue(result["statusDegraded"], "systemic failures must render the degraded state")
        else:
            self.assertFalse(result["statusDegraded"], f"{key} is a query outcome, not an outage")

    # -- regression cases -------------------------------------------------

    def test_http_404_reports_coverage_absent_and_keeps_selected_issuer(self):
        for lang in ("en", "zh"):
            with self.subTest(lang=lang):
                result = self.run_desk("ZZZZ", {"resolve": "status", "status": 404}, lang=lang)
                self.assertDeskLoadedWithPriorIssuer(result)
                self.assertEqual(result["resolveUrl"], f"{API_BASE}/issuers/resolve?ticker=ZZZZ")
                # The old bug: this exact 404 was announced as a temporary outage.
                self.assertNotEqual(result["noticeText"], EXPECTED["temporary"][lang])
                self.assertNotice(result, "covered_absent", "ZZZZ", lang)
                # The dossier still shows the issuer selected before the failed
                # lookup, and the notice names ZZZZ, never MSFT.
                self.assertPriorIssuerPreserved(result)
                self.assertEqual(result["postResolveUrls"], [])

    def test_http_400_and_422_report_invalid_ticker(self):
        for status in (400, 422):
            for lang in ("en", "zh"):
                with self.subTest(status=status, lang=lang):
                    result = self.run_desk("NOT-A!", {"resolve": "status", "status": status}, lang=lang)
                    self.assertDeskLoadedWithPriorIssuer(result)
                    self.assertNotice(result, "invalid", "NOT-A!", lang)
                    self.assertPriorIssuerPreserved(result)
                    self.assertEqual(result["postResolveUrls"], [])

    def test_http_409_reports_ambiguity_and_selects_no_issuer(self):
        for lang in ("en", "zh"):
            with self.subTest(lang=lang):
                result = self.run_desk("ABC", {"resolve": "status", "status": 409}, lang=lang)
                self.assertDeskLoadedWithPriorIssuer(result)
                self.assertEqual(result["resolveUrl"], f"{API_BASE}/issuers/resolve?ticker=ABC")
                self.assertNotice(result, "ambiguous", "ABC", lang)
                # The prior selection stays, and no issuer record may be fetched
                # after an ambiguous answer: the desk must not choose for the reader.
                self.assertPriorIssuerPreserved(result)
                self.assertEqual(result["postResolveUrls"], [])

    def test_http_401_and_403_ask_for_an_eligible_account(self):
        for status in (401, 403):
            for lang in ("en", "zh"):
                with self.subTest(status=status, lang=lang):
                    result = self.run_desk("ZZZZ", {"resolve": "status", "status": status}, lang=lang)
                    self.assertDeskLoadedWithPriorIssuer(result)
                    self.assertNotice(result, "sign_in", "", lang)
                    self.assertPriorIssuerPreserved(result)
                    self.assertEqual(result["postResolveUrls"], [])

    def test_http_503_and_network_failures_report_temporary_outage(self):
        plans = [{"resolve": "status", "status": 503}, {"resolve": "network"}]
        for plan in plans:
            for lang in ("en", "zh"):
                with self.subTest(plan=plan, lang=lang):
                    result = self.run_desk("ZZZZ", plan, lang=lang)
                    self.assertDeskLoadedWithPriorIssuer(result)
                    self.assertNotice(result, "temporary", "", lang)
                    self.assertPriorIssuerPreserved(result)
                    self.assertEqual(result["postResolveUrls"], [])

    def test_valid_ticker_resolves_and_selects_the_issuer(self):
        for lang in ("en", "zh"):
            with self.subTest(lang=lang):
                resolve_body = {
                    "query": {"ticker": "AAPL"},
                    "issuer": {"issuer_id": "aapl-1"},
                }
                result = self.run_desk("AAPL", {"resolve": "ok", "resolveBody": resolve_body}, lang=lang)
                # msft-1 was selected before the lookup; the resolution then
                # replaces the dossier with the resolved issuer.
                self.assertGreaterEqual(result["loadedFetchCount"], 4)
                self.assertEqual(result["preLookup"]["dossierSymbol"], "MSFT")
                self.assertEqual(result["resolveUrl"], f"{API_BASE}/issuers/resolve?ticker=AAPL")
                self.assertEqual(
                    result["postResolveUrls"],
                    [
                        f"{API_BASE}/issuers/aapl-1",
                        f"{API_BASE}/issuers/aapl-1/events?limit=100",
                    ],
                )
                self.assertEqual(result["dossierSymbol"], "AAPL")
                self.assertEqual(result["dossierTitle"], "Apple Inc.")
                pushed = [url for _, url in result["historyCalls"] if "issuer=aapl-1" in url]
                self.assertTrue(pushed, "resolved selection must be written to the location")

    def test_success_after_failure_restores_actual_coverage_notice(self):
        for lang, expected in (("en", "Observed filing coverage is current"),
                               ("zh", "已观察披露覆盖范围为最新")):
            with self.subTest(lang=lang):
                result = self.run_desk("AAPL", {"resolve": "ok", "resolveBody": {
                    "issuer": {"issuer_id": "aapl-1"}}}, lang=lang, prior_failure=True)
                self.assertIn("PREVIOUS_MISSING", result["priorNotice"])
                self.assertEqual(result["noticeText"], expected)
                self.assertTrue(result["statusFresh"])
                self.assertEqual(result["dossierSymbol"], "AAPL")

    def test_resolve_request_encoding_is_unchanged(self):
        result = self.run_desk("A&P", {"resolve": "status", "status": 404})
        self.assertEqual(result["resolveUrl"], f"{API_BASE}/issuers/resolve?ticker=A%26P")
        self.assertNotice(result, "covered_absent", "A&P", "en")
        self.assertEqual(result["postResolveUrls"], [])

    def test_404_is_never_rendered_with_the_degraded_state(self):
        result = self.run_desk("ZZZZ", {"resolve": "status", "status": 404})
        self.assertFalse(result["statusDegraded"])
        self.assertFalse(result["statusFresh"])
        self.assertNotEqual(result["noticeText"], EXPECTED["temporary"]["en"])


if __name__ == "__main__":
    unittest.main()
