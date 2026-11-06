"""ROR-1 exact held #8132 browser consumer characterization (NO production network).

Loads the unmodified, Git-blob-verified candidate wh_banner.js in an about:blank
Chromium DOM. Synthetic feed data are supplied only through a mocked window.fetch.
Proves whether an additional per-market warning_projection is visible when the
legacy gated RR alert is null, and whether a long-open tab refreshes its feed.

These are characterization tests of the held candidate, NOT an approved repair,
authenticated customer proof or instruction to bypass the legacy gate.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import unittest

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent
SCRIPT = Path(os.environ.get("ROR1_BANNER_SOURCE") or str(ROOT / "source/pr8132/templates/wh_banner.js"))
EXPECTED_GIT_BLOB = "9362255160a6a7358014632c53dd865dad163ebe"
RESULTS: list[dict] = []


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _projection() -> dict:
    return {
        "schema": "mastermind.risk_warning_set/v1",
        "rows": [{
            "schema": "mastermind.risk_warning/v1",
            "market": "cn", "source_session": "2026-10-13",
            "expected_session": "2026-10-13", "status": "current",
            "attention": "critical", "state": "risk-off",
            "headline_en": "Synthetic China Risk-off",
            "headline_zh": "合成中国风险规避",
            "authority": {"display_only": True, "may_execute": False},
        }],
        "highest_attention": "critical",
        "coverage": {"expected": 1, "current": 1},
    }


def _source(*, extreme: bool) -> dict:
    legacy = ({
        "id": "rr-2026-10-13-risk-off",
        "asof": "2026-10-13", "headline_en": "Synthetic legacy severe alert",
        "headline_zh": "合成测试严重警报", "href": "macro.html",
        "score": 99, "reasons": [], "amplifiers": [], "ramp": [],
    } if extreme else None)
    return {
        "schema": "rr_banner.v1", "asof": "2026-10-13",
        "generated_at": "2026-10-13T16:32:31Z",
        "alert": legacy,
        "warning_projection": _projection(),
    }


class HeldClientVisibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not SCRIPT.is_file():
            raise FileNotFoundError("Provide a read-only exact #8132 candidate via ROR1_BANNER_SOURCE")
        cls.source = SCRIPT.read_bytes()
        assert _blob(cls.source) == EXPECTED_GIT_BLOB
        cls.runtime = sync_playwright().start()
        cls.browser = cls.runtime.chromium.launch(
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=True, args=["--no-sandbox"],
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.browser.close()
        cls.runtime.stop()

    def _page(self, *, extreme: bool):
        context = self.browser.new_context(
            viewport={"width": 390, "height": 844},
            reduced_motion="reduce",
        )
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.set_content(
            '<!doctype html><html data-lang="en"><head></head>'
            '<body><main>Offline synthetic warning test</main></body></html>'
        )
        page.evaluate("""feeds => {
          const store = new Map();
          Object.defineProperty(window, 'localStorage', {configurable:true,
            value:{getItem:k=>store.get(k)||null,
                   setItem:(k,v)=>store.set(k,String(v))}});
          window.__syntheticFeeds = feeds;
          window.__feedCalls = [];
          window.fetch = url => {
            window.__feedCalls.push(String(url));
            const item = String(url).endsWith('rr_banner.json')
              ? window.__syntheticFeeds.rr : window.__syntheticFeeds.wh;
            return Promise.resolve({ok: true, json: () => Promise.resolve(item)});
          };
        }""", {"rr": _source(extreme=extreme), "wh": {"alerts": []}})
        page.add_script_tag(content=self.source.decode("utf-8"))
        page.wait_for_timeout(160)
        return context, page, errors

    def test_projection_is_not_rendered_when_legacy_alert_is_null(self):
        context, page, errors = self._page(extreme=False)
        try:
            counts = page.evaluate("""() => ({
                calls:window.__feedCalls.slice(),
                bars:document.querySelectorAll('.whb').length,
                text:document.body.innerText
            })""")
            self.assertEqual(counts["bars"], 0)
            self.assertEqual(len(counts["calls"]), 2)
            self.assertNotIn("Synthetic China Risk-off", counts["text"])
            self.assertEqual(errors, [])
            RESULTS.append({
                "case":"critical_country_projection_without_legacy_alert",
                "dom_banner_count":counts["bars"],
                "initial_fetches":len(counts["calls"]),
                "country_attention_visible":False,
                "projection_issuer_proven":False,
                "production_proof":False,
            })
        finally:
            context.close()

    def test_new_legacy_risk_while_tab_stays_open_is_not_polled(self):
        context, page, errors = self._page(extreme=False)
        try:
            page.evaluate("""next => {
                window.__syntheticFeeds.rr = next;
                document.dispatchEvent(new Event('visibilitychange'));
                window.dispatchEvent(new Event('focus'));
            }""", _source(extreme=True))
            page.wait_for_timeout(420)
            counts = page.evaluate("""() => ({
                calls:window.__feedCalls.length,
                bars:document.querySelectorAll('.whb').length
            })""")
            self.assertEqual(counts, {"calls":2,"bars":0})
            self.assertEqual(errors, [])
            RESULTS.append({
                "case":"long_open_tab_does_not_pick_up_new_legacy_severe_alert",
                "fetches_after_changed_test_feed":counts["calls"],
                "dom_banner_count":counts["bars"],
                "production_proof":False,
            })
        finally:
            context.close()

    def test_existing_legacy_extreme_field_does_render_when_present_at_boot(self):
        context, page, errors = self._page(extreme=True)
        try:
            self.assertEqual(page.locator(".whb").count(), 1)
            self.assertEqual(page.locator(".whb-critical").count(), 1)
            self.assertIn("Synthetic legacy severe alert", page.locator(".whb").inner_text())
            self.assertEqual(errors, [])
            RESULTS.append({
                "case":"legacy_extreme_alert_present_at_boot",
                "dom_banner_count":1,
                "critical_style_count":1,
                "synthetic_only":True,
            })
        finally:
            context.close()


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2).result
    if result.wasSuccessful():
        receipt = {
            "schema":"ror1.held_browser_warning_client_gap.v1",
            "candidate_source":"Macro PR #8132 templates/wh_banner.js",
            "source_git_blob":EXPECTED_GIT_BLOB,
            "executed_cases":len(RESULTS),
            "tests_passed":result.testsRun,
            "observations":RESULTS,
            "qualifications":[
                "All browser data and HTML were local synthetic test doubles, not installed origin or entitled browser",
                "Test characterizes a held candidate not production: warning_projection is unconsumed",
                "The script's single initial feed fetch does not constitute a long-open refresh/notification subscription",
                "No changes to risk scores, publication, actual notifications or release holds"
            ],
        }
        encoded = json.dumps(receipt, indent=2, sort_keys=True)+"\n"
        print("RESEARCH_BROWSER_OBSERVATIONS",encoded)
        # An external path is required for output. Running a code-checkout test
        # must not silently write a new artifact into the production repo.
        selected = os.environ.get("ROR1_BROWSER_RECEIPT")
        if selected:
            out = Path(selected)
            if out.exists():
                raise FileExistsError(f"refuse overwrite {out}")
            out.write_text(encoded, encoding="utf-8")
            print("RESEARCH_RECEIPT",out,hashlib.sha256(out.read_bytes()).hexdigest())
