"""Risk of Ruin current-generation proof in real Chromium.

The committed full page and local assets run unchanged. The harness buffers only
messages computed by its genuine Blob Worker; it never substitutes the simulator
or invents a successful response. Critical edit/delivery snapshots are captured
in one browser task, before the 150 ms debounce can hide an obsolete result.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import subprocess
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

if os.environ.get("MM_REQUIRE_BROWSER") == "1":
    from playwright.sync_api import sync_playwright
else:
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
PAGE_PATH = "tools/calculators/risk-of-ruin.html"
TEMPLATE_PATH = "templates/calculators/risk_of_ruin.html.j2"
PLAN = {"winrate": "100", "payoff": "1", "riskpct": "2", "ruindd": "50", "trades": "500"}

# All test controls are outside product code. A capture listener delays genuine
# native responses; a marked MessageEvent redelivers exactly those same values.
CONTROLS = r"""
(() => {
  const NativeWorker = window.Worker;
  const nativePost = NativeWorker.prototype.postMessage;
  const nativeTerminate = NativeWorker.prototype.terminate;
  const nativeDispatch = EventTarget.prototype.dispatchEvent;
  const nativeCreateURL = URL.createObjectURL.bind(URL);
  const nativeRevokeURL = URL.revokeObjectURL.bind(URL);
  const releasedEvents = new WeakSet();
  const workers = [], blobs = [];
  const gate = window.__ror = {
    mode: __MODE__, posted: [], held: [], released: [], events: [],
    expectedNativeError: false, throwNextPost: __MODE__ === "post_throw"
  };
  URL.createObjectURL = function(blob) {
    const url = nativeCreateURL(blob);
    blobs.push({url, text: blob.text()});
    return url;
  };
  class DeliveryControlledWorker extends NativeWorker {
    constructor(url, options) {
      super(url, options);
      const entry = {worker:this, url:String(url), terminated:false};
      workers.push(entry);
      gate.events.push({kind:"native_worker_created", url:String(url)});
      this.addEventListener("message", event => {
        if (releasedEvents.has(event)) return;
        event.stopImmediatePropagation();
        gate.held.push({data:structuredClone(event.data), trusted:event.isTrusted});
        gate.events.push({kind:"native_message_held", id:event.data.id, trusted:event.isTrusted});
      }, true);
      this.addEventListener("error", event => {
        const expected = gate.expectedNativeError && event.isTrusted;
        gate.events.push({kind:event.isTrusted ? "native_error" : "injected_late_error",
                         trusted:event.isTrusted, expected, message:event.message});
        if (expected) {
          gate.expectedNativeError = false;
          // Suppress only the deliberately induced parent-window error report.
          // Do not stop propagation: the application's onerror must still run.
          event.preventDefault();
        }
      }, true);
    }
    postMessage(message, ...rest) {
      if (gate.throwNextPost) {
        gate.throwNextPost = false;
        gate.events.push({kind:"injected_post_throw", id:message.id});
        throw new DOMException("Test-controlled postMessage failure", "DataCloneError");
      }
      gate.posted.push(structuredClone(message));
      return nativePost.call(this, message, ...rest);
    }
    terminate() {
      const entry = workers.find(item => item.worker === this);
      if (entry) entry.terminated = true;
      gate.events.push({kind:"application_terminate"});
      return nativeTerminate.call(this);
    }
  }
  window.Worker = gate.mode === "unavailable" ? undefined : DeliveryControlledWorker;
  gate.snapshot = function() {
    const el = id => document.getElementById(id);
    const text = id => el(id).textContent.trim();
    return {
      main:text("out-main"), plain:text("out-plain"), expectancy:text("out-exp"),
      drawdown:text("out-dd"), accounts:text("out-m"), trades:text("out-n"),
      copyDisabled:el("copy-result").disabled,
      copyText:el("copy-result").innerText.trim(),
      copied:el("copied").classList.contains("show"),
      language:document.documentElement.getAttribute("data-lang") || "en",
      postedCount:gate.posted.length
    };
  };
  gate.edit = function(values) {
    for (const [id, value] of Object.entries(values)) {
      const input = document.getElementById(id);
      input.value = value;
      input.dispatchEvent(new Event("input", {bubbles:true}));
    }
    return gate.snapshot();
  };
  gate.release = function(id) {
    const held = gate.held.find(item => item.data.id === id);
    if (!held || !held.trusted) throw new Error("No genuine native result for " + id);
    const event = new MessageEvent("message", {data:structuredClone(held.data)});
    releasedEvents.add(event);
    gate.released.push(structuredClone(held.data));
    nativeDispatch.call(workers[0].worker, event);
    return gate.snapshot();
  };
  gate.crashNativeWorker = function() {
    gate.expectedNativeError = true;
    gate.events.push({kind:"test_control_invalid_worker_payload"});
    // The real unchanged worker executes simulate(null), producing its own
    // trusted error event. This is not a synthetic error-event substitute.
    nativePost.call(workers[0].worker, {id:-991, sim:null});
  };
  gate.lateError = function() {
    nativeDispatch.call(workers[0].worker,
                        new ErrorEvent("error", {message:"Test-controlled late error"}));
    return gate.snapshot();
  };
  gate.receipt = async function() {
    const sources = [];
    for (const entry of workers) {
      const captured = blobs.find(item => item.url === entry.url);
      if (!captured) throw new Error("Native worker source was not captured");
      sources.push({url:entry.url, source:await captured.text});
    }
    return {mode:gate.mode, posted:gate.posted, held:gate.held,
            released:gate.released, events:gate.events, sources,
            workers:workers.length, snapshot:gate.snapshot(),
            secureContext:isSecureContext,
            nativeClipboard:!!(navigator.clipboard &&
                               navigator.clipboard.readText && navigator.clipboard.writeText)};
  };
  gate.cleanup = function() {
    let terminated = 0;
    for (const entry of workers) {
      if (!entry.terminated) {
        nativeTerminate.call(entry.worker);
        entry.terminated = true;
        terminated++;
      }
    }
    for (const entry of blobs) nativeRevokeURL(entry.url);
    return {workers:workers.length, terminatedAtCleanup:terminated,
            allTerminated:workers.every(entry => entry.terminated),
            revokedObjectURLs:blobs.length};
  };
})();
"""


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def site_server():
    class ReadOnlyHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(ReadOnlyHandler, directory=str(SITE))
    )
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive(), "Loopback test server did not stop"


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch(headless=True)
        try:
            yield instance
        finally:
            instance.close()


class Case:
    def __init__(self, browser, origin, name, mode):
        self.browser = browser
        self.origin = origin
        self.name = name
        self.mode = mode
        self.context = None
        self.page = None
        self.page_errors = []
        self.failed_assets = []
        self.external_requests = []
        self.loaded_assets = set()
        self.observations = {}
        self.complete = False
        self.source_hashes = {
            TEMPLATE_PATH: sha256(ROOT / TEMPLATE_PATH),
            "site/" + PAGE_PATH: sha256(SITE / PAGE_PATH),
        }

    def start(self):
        self.context = self.browser.new_context(
            locale="en-US", permissions=["clipboard-read", "clipboard-write"],
            service_workers="block",
        )
        self.context.add_init_script(CONTROLS.replace("__MODE__", json.dumps(self.mode)))

        def route(request_route):
            url = request_route.request.url
            if url.startswith(self.origin + "/") or url.startswith("blob:" + self.origin + "/"):
                request_route.continue_()
            else:
                self.external_requests.append(url)
                request_route.abort()

        self.context.route("**/*", route)
        self.page = self.context.new_page()
        self.page.on("pageerror", lambda error: self.page_errors.append(str(error)))

        def response_received(response):
            request = response.request
            if not response.url.startswith(self.origin + "/"):
                return
            relative = unquote(urlsplit(response.url).path).lstrip("/")
            if response.status >= 400 and request.resource_type in ("script", "stylesheet", "document"):
                self.failed_assets.append({"path": relative, "status": response.status})
            if response.ok and (SITE / relative).is_file():
                self.loaded_assets.add(relative)

        self.page.on("response", response_received)
        response = self.page.goto(self.origin + "/" + PAGE_PATH, wait_until="domcontentloaded")
        assert response is not None and response.status == 200
        self.page.wait_for_function("!!window.__ror && !!document.getElementById('copy-result')")
        assert self.page.evaluate(
            "() => isSecureContext && !!navigator.clipboard && "
            "typeof navigator.clipboard.readText === 'function' && "
            "typeof navigator.clipboard.writeText === 'function'"
        ), "Real clipboard APIs in a secure context are required"
        assert self.page.locator("#out-main").is_visible()

    def edit(self, values):
        return self.page.evaluate("(values) => __ror.edit(values)", values)

    def snapshot(self):
        return self.page.evaluate("() => __ror.snapshot()")

    def held(self, count):
        self.page.wait_for_function("(count) => __ror.held.length >= count", arg=count)
        records = self.page.evaluate("() => __ror.held")
        assert all(record["trusted"] for record in records), records
        return records[count - 1]["data"]

    def release(self, result):
        return self.page.evaluate("(id) => __ror.release(id)", result["id"])

    def remember(self, label, value):
        self.observations[label] = value
        return value

    def clipboard_write(self, value):
        self.page.evaluate("(value) => navigator.clipboard.writeText(value)", value)

    def clipboard_read(self):
        return self.page.evaluate("() => navigator.clipboard.readText()")

    def copy_current(self, expected):
        self.page.locator("#copy-result").click()
        self.page.wait_for_function("() => document.getElementById('copied').classList.contains('show')")
        value = self.clipboard_read()
        assert value == expected
        self.remember("native_clipboard_readback", value)
        return value

    def finish(self):
        evidence = None
        cleanup = None
        try:
            if self.page is not None and not self.page.is_closed():
                evidence = self.page.evaluate("() => __ror.receipt()")
                for source in evidence["sources"]:
                    raw = source.pop("source").encode()
                    source.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                cleanup = self.page.evaluate("() => __ror.cleanup()")
        finally:
            if self.context is not None:
                self.context.close()
        source_unchanged = all(sha256(ROOT / path) == digest for path, digest in self.source_hashes.items())
        unexpected_worker_errors = [] if evidence is None else [
            event for event in evidence["events"]
            if event["kind"] == "native_error" and not event["expected"]
        ]
        proof = {
            "schema": "macro.risk_of_ruin.browser.v1",
            "case": self.name, "mode": self.mode, "owner": "calculator-input-integrity",
            "outcome": "assertions_completed" if self.complete and source_unchanged
                       and cleanup is not None and cleanup["allTerminated"]
                       and not self.page_errors and not self.failed_assets
                       and not unexpected_worker_errors else "failure",
            "github": {key: os.environ.get(key) for key in (
                "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_HEAD_REF",
            )},
            "checkout_head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "chromium": self.browser.version,
            "playwright": importlib.metadata.version("playwright"),
            "served_path": "site/" + PAGE_PATH,
            "source_sha256": self.source_hashes,
            "source_unchanged": source_unchanged,
            "local_asset_sha256": {path: sha256(SITE / path) for path in sorted(self.loaded_assets)},
            "blocked_external_requests": self.external_requests,
            "page_errors": self.page_errors, "failed_required_assets": self.failed_assets,
            "unexpected_worker_errors": unexpected_worker_errors,
            "observations": self.observations, "browser_evidence": evidence,
            "cleanup": cleanup,
            "boundary": "Genuine native worker calculations with test-controlled response delivery; "
                        "injected transport failure is labeled separately. Native clipboard readback "
                        "does not revoke a write initiated before an input edit.",
        }
        print("RISK_OF_RUIN_BROWSER_PROOF " + json.dumps(proof, sort_keys=True), flush=True)
        assert source_unchanged
        assert not self.page_errors, self.page_errors
        assert not self.failed_assets, self.failed_assets
        assert not unexpected_worker_errors, unexpected_worker_errors
        assert cleanup is not None and cleanup["allTerminated"]


@pytest.fixture
def open_case(browser, site_server, request):
    cases = []

    def create(mode="hold"):
        case = Case(browser, site_server, request.node.name, mode)
        cases.append(case)
        case.start()
        return case

    try:
        yield create
    finally:
        for case in reversed(cases):
            case.finish()


def assert_invalidated(snapshot):
    assert snapshot["main"] == "—"
    assert snapshot["copyDisabled"]
    assert not snapshot["copied"]
    assert snapshot["expectancy"] == "—"
    assert snapshot["drawdown"] == "—"
    assert snapshot["accounts"] == "—"
    assert snapshot["trades"] == "—"
    assert snapshot["plain"] == "Calculating risk for the current inputs…"


def assert_held_pending(case, result, winrate):
    snapshot = case.snapshot()
    assert snapshot["main"] == "—" and snapshot["copyDisabled"]
    assert snapshot["plain"] == "Calculating risk for the current inputs…"
    assert snapshot["expectancy"] == ("+1.00 R" if winrate == 100 else "-1.00 R")
    posted = case.page.evaluate("() => __ror.posted")
    request = next(item for item in posted if item["id"] == result["id"])
    assert request["sim"]["M"] == 10000
    assert request["sim"]["N"] == 500
    assert request["sim"]["seed"] == 0x9E3779B9
    assert request["sim"]["winP"] == winrate / 100
    assert result["ruinPct"] == (0 if winrate == 100 else 100)
    return snapshot


def assert_settled(snapshot, winrate):
    risk = "0.00%" if winrate == 100 else "100.0%"
    expectancy = "+1.00 R" if winrate == 100 else "-1.00 R"
    assert snapshot["main"] == risk
    assert snapshot["expectancy"] == expectancy
    assert snapshot["drawdown"] == "50%"
    assert snapshot["accounts"] == "10,000"
    assert snapshot["trades"] == "500"
    assert not snapshot["copyDisabled"]
    assert "About " + risk + " of 10,000 simulated accounts" in snapshot["plain"]
    assert ("a positive edge" if winrate == 100 else "a negative edge") in snapshot["plain"]


def report_line(winrate):
    return ("Risk of ruin: " + ("0.00%" if winrate == 100 else "100.0%")
            + " (over 500 trades, 50% ruin line) · expectancy "
            + ("+1.00" if winrate == 100 else "-1.00") + " R — mastermind-x.com")


def test_pending_copy_current_completion_and_language(open_case):
    case = open_case()
    assert_invalidated(case.edit(PLAN))
    old = case.held(1)
    case.remember("first_genuine_result_held", assert_held_pending(case, old, 100))
    assert_settled(case.release(old), 100)
    case.copy_current(report_line(100))
    case.clipboard_write("pending-copy-sentinel")
    immediate = case.page.evaluate("""() => {
      const state = __ror.edit({winrate:"0"});
      document.getElementById("copy-result").click();
      return state;
    }""")
    assert_invalidated(immediate)
    case.remember("immediate_edit_and_native_disabled_click", immediate)
    assert case.clipboard_read() == "pending-copy-sentinel"
    current = case.held(2)
    case.remember("recomputation_still_withheld", assert_held_pending(case, current, 0))
    # Native click while recomputing must still preserve the real clipboard.
    case.page.evaluate("() => document.getElementById('copy-result').click()")
    assert case.clipboard_read() == "pending-copy-sentinel"
    final = case.release(current)
    assert_settled(final, 0)
    case.remember("current_result", final)
    case.copy_current(report_line(0))
    case.page.locator("#gear-btn").click()
    case.page.locator('#gear-pop [data-set-lang="zh"]').click()
    assert case.page.locator("html").get_attribute("data-lang") == "zh"
    assert case.page.locator("#copy-result").inner_text().strip() == "复制结果"
    assert "胜率" in case.page.locator(".ci-l").first.inner_text()
    assert_settled(case.snapshot(), 0)
    case.page.locator('#gear-pop [data-set-lang="en"]').click()
    assert case.page.locator("#copy-result").inner_text().strip() == "Copy result"
    assert_settled(case.snapshot(), 0)
    case.remember("language_roundtrip", {"zh_copy": "复制结果", "en_copy": "Copy result"})
    case.complete = True


def test_obsolete_success_during_valid_edit_debounce(open_case):
    case = open_case()
    case.edit(PLAN)
    old = case.held(1)
    assert_held_pending(case, old, 100)
    immediate = case.page.evaluate("""(id) => {
      __ror.edit({winrate:"0"});
      __ror.release(id);
      return __ror.snapshot();
    }""", old["id"])
    assert_invalidated(immediate)
    assert immediate["postedCount"] == 1
    case.remember("single_task_edit_release_snapshot", immediate)
    current = case.held(2)
    assert_held_pending(case, current, 0)
    final = case.release(current)
    assert_settled(final, 0)
    case.remember("final", final)
    case.complete = True


def test_obsolete_success_after_invalid_edit_and_recovery(open_case):
    case = open_case()
    case.edit(PLAN)
    old = case.held(1)
    assert_held_pending(case, old, 100)
    immediate = case.page.evaluate("""(id) => {
      __ror.edit({winrate:"101"});
      __ror.release(id);
      return __ror.snapshot();
    }""", old["id"])
    assert_invalidated(immediate)
    case.remember("single_task_invalid_edit_release_snapshot", immediate)
    case.page.wait_for_function(
        "() => document.getElementById('out-plain').textContent.includes('win rate between 0 and 100')"
    )
    invalid = case.snapshot()
    assert invalid["main"] == "—" and invalid["expectancy"] == "—"
    assert invalid["copyDisabled"] and invalid["postedCount"] == 1
    case.remember("invalid_input_settled", invalid)
    assert_invalidated(case.edit({"winrate": "0"}))
    current = case.held(2)
    assert_held_pending(case, current, 0)
    assert_settled(case.release(current), 0)
    case.complete = True


def test_reversed_real_results_cannot_replace_current_copy(open_case):
    case = open_case()
    case.edit(PLAN)
    old = case.held(1)
    assert_held_pending(case, old, 100)
    case.edit({"winrate": "0"})
    current = case.held(2)
    assert_held_pending(case, current, 0)
    final = case.release(current)
    assert_settled(final, 0)
    assert case.release(old) == final
    assert case.release(current) == final
    case.remember("new_then_old_then_duplicate_current", final)
    case.copy_current(report_line(0))
    case.complete = True


def test_actual_worker_error_falls_back_to_current_form(open_case):
    case = open_case()
    case.edit(PLAN)
    old = case.held(1)
    assert_held_pending(case, old, 100)
    immediate = case.page.evaluate("""() => {
      __ror.edit({winrate:"0"});
      __ror.crashNativeWorker();
      return __ror.snapshot();
    }""")
    assert_invalidated(immediate)
    case.page.wait_for_function("""() =>
      __ror.events.some(event => event.kind === "native_error" && event.trusted)
      && !document.getElementById("copy-result").disabled
    """)
    final = case.snapshot()
    assert_settled(final, 0)
    events = case.page.evaluate("() => __ror.events")
    assert sum(event["kind"] == "native_error" and event["expected"] for event in events) == 1
    assert sum(event["kind"] == "application_terminate" for event in events) == 1
    assert case.release(old) == final
    case.remember("current_form_native_error_fallback", final)
    case.complete = True


def test_synchronous_postmessage_failure_and_late_error(open_case):
    case = open_case("post_throw")
    case.edit(dict(PLAN, winrate="0"))
    case.page.wait_for_function("() => !document.getElementById('copy-result').disabled")
    final = case.snapshot()
    assert_settled(final, 0)
    events = case.page.evaluate("() => __ror.events")
    assert sum(event["kind"] == "injected_post_throw" for event in events) == 1
    assert sum(event["kind"] == "application_terminate" for event in events) == 1
    assert case.page.evaluate("() => __ror.lateError()") == final
    assert case.page.evaluate("() => __ror.held.length") == 0
    case.remember("injected_transport_failure_fallback", final)
    case.complete = True


def test_unavailable_worker_keeps_existing_synchronous_result(open_case):
    case = open_case("unavailable")
    case.edit(dict(PLAN, winrate="0"))
    case.page.wait_for_function("() => !document.getElementById('copy-result').disabled")
    final = case.snapshot()
    assert_settled(final, 0)
    assert case.page.evaluate("() => __ror.events.length") == 0
    case.remember("unavailable_worker_fallback", final)
    case.copy_current(report_line(0))
    case.complete = True


def test_rapid_valid_invalid_edits_only_commit_final_generation(open_case):
    case = open_case()
    case.edit(PLAN)
    original = case.held(1)
    assert_settled(case.release(original), 100)
    immediate = case.page.evaluate("""() =>
      ["0", "101", "50", "0"].map(winrate => __ror.edit({winrate}))
    """)
    for snapshot in immediate:
        assert_invalidated(snapshot)
        assert snapshot["postedCount"] == 1
    case.remember("same_task_rapid_edits", immediate)
    current = case.held(2)
    assert_held_pending(case, current, 0)
    final = case.release(current)
    assert_settled(final, 0)
    assert final["postedCount"] == 2
    case.remember("only_final_generation_completed", final)
    case.complete = True
