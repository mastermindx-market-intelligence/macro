"""Capture the real AI Brief dialog through the existing page-evidence driver.

The surrounding dashboard is the repository's disclosed render-test fixture;
the brief itself is the unchanged committed site/master_brief.json. This recipe
clicks the real card, captures the actual dialog, and never edits page content.
"""
from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import urlsplit
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import capture_page_evidence as capture

parser = argparse.ArgumentParser()
parser.add_argument("--dialog-region", choices=("top", "lower"), required=True)
parser.add_argument("--interaction-receipt", type=Path, required=True)
args, remaining = parser.parse_known_args()
observations = []


class ScenarioPage:
    def __init__(self, page):
        self.page = page
        self.prepared = False

    def __getattr__(self, name):
        return getattr(self.page, name)

    def goto(self, url, **kwargs):
        parsed = urlsplit(url)
        assert parsed.hostname in {"127.0.0.1", "localhost"}, "fixture is loopback only"
        origin = f"{parsed.scheme}://{parsed.netloc}/"
        self.page.context.route("**/*", lambda route: route.continue_()
                                if route.request.url.startswith(origin) else route.abort())
        return self.page.goto(url, **kwargs)

    def evaluate(self, script, *values):
        if script.strip() == capture._OBSERVER_SCRIPT.strip() and not self.prepared:
            # Reuse the documented local-only boundary from
            # tests/risk_radar_workspace_browser.py. No account, cookie, token,
            # entitlement lookup or external request is involved.
            self.page.evaluate("window.MMXAccessPreview={isAnon:function(){return false;}}")
            self.page.locator('[onclick*="mx5OpenDlg"][onclick*="dlg-aibrief"]').first.click()
            dialog = self.page.locator("#dlg-aibrief")
            dialog.wait_for(state="visible")
            self.page.wait_for_timeout(500)
            if args.dialog_region == "lower":
                target = dialog.locator(".aib2-card--playbook")
                if target.count() == 0:
                    target = dialog.locator(".aib2-card").last
                target.scroll_into_view_if_needed()
                self.page.wait_for_timeout(200)
            measured = dialog.evaluate("""node => {
              const r = node.getBoundingClientRect();
              const panels = [...node.querySelectorAll('.aib2-stance,.aib2-lead,.aib2-card')]
                .filter(e => e.getBoundingClientRect().width > 0).map(e => {
                  const s = getComputedStyle(e);
                  return {classes:e.className,left:s.borderLeftWidth,right:s.borderRightWidth,
                    leftColor:s.borderLeftColor,rightColor:s.borderRightColor};
                });
              return {theme:document.documentElement.dataset.theme,
                locale:document.documentElement.dataset.lang,viewport:innerWidth,
                dialogLeft:r.left,dialogRight:r.right,panels};
            }""")
            assert measured["panels"], "The actual brief contains no visible panels"
            assert all(p["left"] == p["right"] and p["leftColor"] == p["rightColor"]
                       for p in measured["panels"]), measured
            assert measured["dialogLeft"] >= -1 and measured["dialogRight"] <= measured["viewport"] + 1, measured
            measured["region"] = args.dialog_region
            observations.append(measured)
            self.prepared = True
        return self.page.evaluate(script, *values)

    def screenshot(self, **kwargs):
        # A modal is a viewport surface; full-page capture would include the
        # irrelevant, blurred synthetic dashboard below the open dialog.
        return self.page.screenshot(**{**kwargs, "full_page": False})


class ScenarioContext:
    def __init__(self, context):
        self.context = context

    def __getattr__(self, name):
        return getattr(self.context, name)

    def new_page(self):
        return ScenarioPage(self.context.new_page())


class ScenarioBrowser:
    def __init__(self, browser):
        self.browser = browser

    def __getattr__(self, name):
        return getattr(self.browser, name)

    def new_context(self, **kwargs):
        return ScenarioContext(self.browser.new_context(**kwargs))


original_driver = capture.playwright_page_driver


def dialog_driver(**kwargs):
    driver = original_driver(**kwargs)
    driver._browser = ScenarioBrowser(driver._browser)
    return driver


capture.playwright_page_driver = dialog_driver
result = capture.main(remaining)
manifest_path = Path(remaining[remaining.index("--manifest") + 1])
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text())
    manifest.setdefault("honesty", {})["access"] = (
        "Local rendered fixture using the existing risk_radar_workspace_browser "
        "MMXAccessPreview test boundary; no real account/session and no external requests."
    )
    manifest["honesty"]["surrounding_dashboard"] = "Synthetic existing test VM; committed brief content."
    manifest.setdefault("tool", {})["driver_scenario"] = "real card click in local registered-state fixture"
    for page in manifest.get("pages", []):
        for state in page.get("states", []):
            state["access"] = "fixture_registered"
    manifest_path.write_bytes(capture.canonical_json_bytes(manifest))
args.interaction_receipt.parent.mkdir(parents=True, exist_ok=True)
args.interaction_receipt.write_text(json.dumps({
    "source_commit": "a739405d248e3e985c6215067878028f8403fad9",
    "scenario": "real AI Brief card click; actual dialog and scroll",
    "surrounding_dashboard": "existing synthetic dashboard render fixture",
    "brief": "unchanged committed site/master_brief.json",
    "capture_region": args.dialog_region,
    "observations": observations,
}, indent=2) + "\n")
raise SystemExit(result)
