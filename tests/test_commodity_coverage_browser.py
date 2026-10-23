"""Opt-in coverage journeys in a fresh headless Chromium, served on loopback.

Run from this staging root (existing dependencies/browser only; no installation):
  python3 tests/test_commodity_coverage_browser.py \
    --frozen-page /absolute/path/to/copied/revision-six/commodities.html \
    --frozen-page-sha256 <independently-recorded-64-character-page-sha256>

Optionally pass --chromium-executable /absolute/path/to/an/installed/chromium.
Dependencies: Jinja2, Playwright Python, an installed Chromium, and the existing
test_commodity_decision_workspace.py fixture module beside this file. The harness
starts an ephemeral loopback server; it uses no existing server, user browser,
profile, credentials, external requests, Git access, or site writes. Normal
unittest discovery skips this explicit browser qualification.
The CLI fails on missing dependencies, skipped cases, or a mismatched input hash.

These synthetic SSR/browser journeys and frozen-payload compatibility are not
production acceptance, visual parity, or proof of current publication economics.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import re
import sys
from threading import Thread
import unittest
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parents[1]
OPTIONS = None
PAYLOAD = re.compile(r'<script\b[^>]*\bid="cw-data"[^>]*>(.*?)</script>', re.S)


def payload_text(html):
    matches = PAYLOAD.findall(html)
    if len(matches) != 1:
        raise AssertionError("Expected exactly one real cw-data payload")
    return matches[0]


class ConfiguredCoverageBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if OPTIONS is None:
            raise unittest.SkipTest("Run this opt-in browser file directly with the frozen-page arguments")
        from jinja2 import DictLoader, Environment, StrictUndefined
        from playwright.sync_api import sync_playwright

        sys.path.insert(0, str(ROOT))
        fixture_path = ROOT / "tests/test_commodity_decision_workspace.py"
        spec = importlib.util.spec_from_file_location("coverage_browser_fixtures", fixture_path)
        fixtures = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixtures)

        cls.source_bytes = {path: (ROOT / path).read_bytes() for path in (
            "engine/commodity_decision_workspace.py", "engine/commodity_workspace_adapter.py",
            "templates/_commodity_decision_workspace.html.j2", "templates/commodity-workspace.js",
            "templates/commodity-workspace.css", "tests/test_commodity_decision_workspace.py",
            "tests/test_commodity_coverage_browser.py")}
        # Render the exact template bytes recorded below, with its normal strict
        # Jinja and localization semantics. Never replace SSR with a payload swap.
        env = Environment(loader=DictLoader({"_commodity_decision_workspace.html.j2":
            cls.source_bytes["templates/_commodity_decision_workspace.html.j2"].decode("utf-8")}),
            autoescape=True, undefined=StrictUndefined)
        macro = '{% macro t(en,zh) %}<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh }}</span>{% endmacro %}'
        template = env.from_string(macro + '{% include "_commodity_decision_workspace.html.j2" %}')
        cls.workspaces = {case: fixtures.coverage_presentation_fixture(case)
                          for case in ("absent_energy", "misclassified_oil")}
        frozen_bytes = OPTIONS.frozen_page.read_bytes()
        actual_hash = sha256(frozen_bytes).hexdigest()
        if actual_hash != OPTIONS.frozen_page_sha256:
            raise AssertionError(f"Frozen input SHA256 mismatch: observed {actual_hash}")
        cls.frozen_payload = payload_text(frozen_bytes.decode("utf-8"))
        frozen = json.loads(cls.frozen_payload)
        if frozen.get("projection_revision") != 6 or "universe" in frozen:
            raise AssertionError("Supply an actual frozen revision-six publication without the new roster")
        cls.workspaces["frozen"] = frozen
        cls.components = {}
        for case, workspace in cls.workspaces.items():
            before = deepcopy(workspace)
            cls.components[case] = template.render(commodity_workspace=workspace)
            if workspace != before or json.loads(payload_text(cls.components[case])) != before:
                raise AssertionError(f"SSR mutated the workspace in {case}")
        if payload_text(cls.components["frozen"]) != cls.frozen_payload:
            raise AssertionError("Actual revision-six payload bytes changed during template rendering")
        cls.receipt = {
            "scope": "isolated_component_ssr_and_browser",
            "frozen_page_sha256": actual_hash,
            "frozen_payload_sha256": sha256(cls.frozen_payload.encode("utf-8")).hexdigest(),
            "source_sha256": {path: sha256(body).hexdigest() for path, body in cls.source_bytes.items()},
            "component_sha256": {case: sha256(component.encode("utf-8")).hexdigest()
                                 for case, component in cls.components.items()},
            "synthetic_cases": ["absent_energy", "misclassified_oil"],
            "shared_shell_qualified": False, "normal_publication_renderer_qualified": False,
            "production_acceptance": False, "visual_parity_acceptance": False,
        }

        documents = {"/consumer.js": ("text/javascript", cls.source_bytes["templates/commodity-workspace.js"]),
                     "/consumer.css": ("text/css", cls.source_bytes["templates/commodity-workspace.css"])}
        for case, component in cls.components.items():
            # Only a host shell and language visibility: no synthetic product
            # styles, controls, economic readings, or script stubs are inserted.
            html = ('<!doctype html><html lang="en" data-lang="en"><head><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1">'
                    '<link rel="icon" href="data:,">'
                    '<style>html[data-lang="en"] .l-zh{display:none}html[data-lang="zh"] .l-en{display:none}</style>'
                    '<link rel="stylesheet" href="/consumer.css"></head><body class="page-commod cw-enabled">'
                    '<main class="wrap">' + component + '</main><script src="/consumer.js"></script></body></html>')
            documents[f"/{case}.html"] = ("text/html", html.encode("utf-8"))

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                entry = documents.get(urlsplit(self.path).path)
                if entry is None:
                    self.send_error(404)
                    return
                content_type, body = entry
                self.send_response(200)
                self.send_header("Content-Type", content_type + "; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                pass

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.server.daemon_threads = True
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.server.shutdown)
        cls.origin = f"http://127.0.0.1:{cls.server.server_port}"
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        launch = {"headless": True}
        if OPTIONS.chromium_executable:
            launch["executable_path"] = str(OPTIONS.chromium_executable)
        cls.browser = cls.playwright.chromium.launch(**launch)
        cls.addClassCleanup(cls.browser.close)
        cls.receipt["browser_version"] = cls.browser.version

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1280, "height": 900}, service_workers="block")
        self.addCleanup(self.context.close)
        self.errors, self.external_requests, self.failed_responses, self.failed_requests = [], [], [], []
        self.page = self.context.new_page()
        self.page.set_default_timeout(5000)
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.on("response", lambda response: self.failed_responses.append(
            {"status": response.status, "path": urlsplit(response.url).path})
            if response.status >= 400 else None)
        self.page.on("requestfailed", lambda request: self.failed_requests.append(
            {"path": urlsplit(request.url).path, "failure": request.failure}))

        def local_only(route):
            if route.request.url.startswith(self.origin + "/"):
                route.continue_()
            else:
                self.external_requests.append(route.request.url)
                route.abort()
        self.page.route("**/*", local_only)

    def tearDown(self):
        self.receipt.setdefault("journeys", []).append({
            "test": self._testMethodName, "page_errors": self.errors,
            "external_requests": self.external_requests,
            "failed_responses": self.failed_responses, "failed_requests": self.failed_requests,
        })
        self.assertEqual(self.errors, [], "Uncaught page errors")
        self.assertEqual(self.external_requests, [], "The isolated component attempted an external request")
        self.assertEqual(self.failed_responses, [], "Failed local HTTP responses")
        self.assertEqual(self.failed_requests, [], "Failed browser requests")

    def open(self, case, fragment):
        self.page.goto(f"{self.origin}/{case}.html{fragment}", wait_until="load")

    def family(self):
        return parse_qs(urlsplit(self.page.url).fragment.partition("?")[2]).get("family", ["all"])[0]

    def assert_missing_energy(self):
        from playwright.sync_api import expect
        expect(self.page.locator('[data-cw-family="energy"]')).to_have_attribute("aria-pressed", "true")
        expect(self.page.locator('[data-cw-browse-coverage]')).to_have_attribute("data-coverage-state", "missing")
        expect(self.page.locator('[data-cw-coverage-members]')).to_have_text("0 of 4 configured members present")
        expect(self.page.locator('[data-cw-coverage-prices]')).to_have_text("0 of 4 identity-matched one-month values")
        expect(self.page.locator('[data-cw-universe-empty]')).to_be_visible()
        expect(self.page.locator('[data-cw-universe-empty] h3')).to_have_text("Configured members are missing from this snapshot")
        expect(self.page.locator('[data-cw-universe-empty] p')).to_contain_text("does not imply zero performance or a neutral state")
        expect(self.page.locator('[data-cw-universe-row]:visible')).to_have_count(0)
        self.assertEqual(self.family(), "energy")

    def test_absent_energy_ssr_is_missing_without_fake_prices_or_zero_breadth(self):
        html = self.components["absent_energy"]
        self.assertIn("This family is missing from the snapshot.", html)
        self.assertIn("本快照缺少这一类别", html)
        self.assertRegex(html, r'data-cw-members-present>\s*0 / 4')
        self.assertRegex(html, r'data-cw-prices-available>\s*0 / 4')
        self.assertNotIn("0 / 0", html)
        self.assertNotRegex(html, r'data-cw-universe-row="(?:oil|natgas|gasoline|heating_oil)"')
        self.assertEqual(len(self.workspaces["absent_energy"]["assets"]), 13)

    def test_absent_energy_direct_url_and_native_back_keep_selected_family(self):
        from playwright.sync_api import expect
        self.open("absent_energy", "#cw/explore/gold?view=universe&family=energy&compare=oil%2Cgold&window=1m")
        self.assert_missing_energy()
        expect(self.page.locator('[data-cw-compare][value="oil"]')).to_have_count(0)
        expect(self.page.locator('[data-cw-compare][value="gold"]')).to_be_checked()
        self.page.locator('[data-cw-family="precious"]').click()
        expect(self.page.locator('[data-cw-universe-row]:visible')).to_have_count(4)
        self.assertEqual(self.family(), "precious")
        self.page.go_back()
        self.assert_missing_energy()

    def test_overview_family_entry_and_recovery_transfer_visible_keyboard_focus(self):
        from playwright.sync_api import expect
        self.open("absent_energy", "#cw/overview/gold")
        entry = self.page.locator('#cw-panel-overview [data-cw-family-open="energy"]')
        expect(entry).to_be_visible()
        entry.press("Enter")
        self.assert_missing_energy()
        selected = self.page.locator('[data-cw-family="energy"]')
        expect(selected).to_be_visible()
        expect(selected).to_be_focused()
        self.page.locator('[data-cw-universe-empty] [data-cw-reset-filters]').press("Enter")
        expect(self.page.locator('[data-cw-family="all"]')).to_have_attribute("aria-pressed", "true")
        expect(self.page.locator('[data-cw-universe-row]:visible')).to_have_count(13)
        search = self.page.locator('[data-cw-search]')
        expect(search).to_be_visible()
        expect(search).to_be_focused()
        self.assertEqual(self.family(), "all")

    def test_mismatched_identity_is_unconfirmed_while_its_real_zero_stays_inspectable(self):
        from playwright.sync_api import expect
        self.open("misclassified_oil", "#cw/explore/oil?view=universe&family=energy")
        expect(self.page.locator('[data-cw-browse-coverage]')).to_have_attribute("data-coverage-state", "inconsistent")
        expect(self.page.locator('[data-cw-coverage-members]')).to_have_text("1 of 1 configured members present")
        expect(self.page.locator('[data-cw-coverage-prices]')).to_have_text("0 of 1 identity-matched one-month values")
        expect(self.page.locator('[data-cw-universe-empty]')).to_be_visible()
        expect(self.page.locator('[data-cw-universe-empty] p')).to_contain_text("Member identities disagree")
        expect(self.page.locator('[data-cw-universe-empty]')).not_to_contain_text("have no published observations")
        self.page.locator('[data-cw-universe-empty] [data-cw-reset-filters]').click()
        expect(self.page.locator('[data-cw-universe-row]:visible')).to_have_count(1)
        self.page.locator('[data-cw-universe-row="oil"] [data-cw-inspect="oil:1m"]').click()
        expect(self.page.locator('[data-cw-inspector]')).to_have_attribute("open", "")
        expect(self.page.locator('[data-cw-inspector-value]')).to_contain_text("0.0%")

    def test_actual_frozen_revision_six_payload_survives_ssr_and_navigation_byte_for_byte(self):
        from playwright.sync_api import expect
        self.assertEqual(payload_text(self.components["frozen"]), self.frozen_payload)
        self.open("frozen", "#cw/overview/oil")
        self.page.locator('#cw-tab-explore').click()
        self.page.locator('[data-cw-family="energy"]').click()
        expect(self.page.locator('[data-cw-browse-coverage]')).to_have_attribute("data-coverage-state", "unknown")
        expect(self.page.locator('[data-cw-coverage-members]')).to_contain_text("expected membership unconfirmed")
        self.page.locator('#cw-tab-compare').click()
        self.page.go_back()
        expect(self.page.locator('[data-cw-family="energy"]')).to_have_attribute("aria-pressed", "true")
        observed = self.page.locator('#cw-data').text_content()
        self.assertEqual(observed, self.frozen_payload)
        self.assertEqual(sha256(observed.encode("utf-8")).hexdigest(), self.receipt["frozen_payload_sha256"])
        self.assertEqual(json.loads(observed)["projection_revision"], 6)
        self.assertNotIn("universe", json.loads(observed))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-page", type=Path, required=True)
    parser.add_argument("--frozen-page-sha256", required=True)
    parser.add_argument("--chromium-executable", type=Path)
    OPTIONS = parser.parse_args()
    if not OPTIONS.frozen_page.is_absolute() or not re.fullmatch(r"[0-9a-f]{64}", OPTIONS.frozen_page_sha256):
        parser.error("Supply an absolute frozen-page path and its independently recorded lowercase SHA256")
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ConfiguredCoverageBrowser))
    receipt = dict(getattr(ConfiguredCoverageBrowser, "receipt", {}))
    receipt.update(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped))
    print("COVERAGE_BROWSER_RECEIPT " + json.dumps(receipt, sort_keys=True))
    raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)
