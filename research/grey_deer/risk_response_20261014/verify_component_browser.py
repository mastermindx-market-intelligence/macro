"""Offline real-browser proof of the existing risk component, not production proof.

Render the real Jinja page fixture, keep its styles/data, strip unrelated scripts,
block network, then run the actual risk-envelope live client against a controlled
same-session partial-warning feed. No market observation or performance is inferred.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from playwright.sync_api import sync_playwright
    from tests.test_risk_envelope_radar_integration import source_envelope, render

    settled = source_envelope()
    settled["source_session"] = "2026-10-14"
    settled["measured_state"].update(verdict="MIXED", score=50, as_of="2026-10-14")
    settled["hazard_summary"].update(stage=None, stage_reason="required_coverage_unavailable")
    for source in settled["provenance"]["sources"]:
        source["as_of"] = "2026-10-14"
    settled["provenance"]["sources"][1]["coverage"] = "MISSING"
    html = render(settled)
    # Keep only inert JSON scripts; no unrelated runtime or external dependency.
    html = re.sub(r"<script\b([^>]*)>.*?</script>",
                  lambda match: match.group(0) if 'type="application/json"' in match.group(1) else "",
                  html, flags=re.S | re.I)
    live = json.loads(json.dumps(settled))
    live.update(source_session="2026-10-15", revision="live_provisional", precedence="live",
                live_active=True, built="2026-10-15 15:00:00 UTC", stale_after_min=5,
                overlays={"settled_bundle_id": settled["bundle_id"]},
                live_transition={"candidate_stage": None, "stable_stage": None, "pending": None})
    for source in live["provenance"]["sources"]:
        source["as_of"] = "2026-10-15"
    source_js = (ROOT / "templates/risk_envelope_live.js").read_text()
    cases = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, channel="chrome")
        try:
            for theme in ("dark", "light"):
                for language in ("en", "zh"):
                    for width in (1440, 390):
                        page = browser.new_page(viewport={"width": width, "height": 1000})
                        page.route("**/*", lambda route: route.abort())
                        page.set_content(html, wait_until="domcontentloaded")
                        page.evaluate("([theme,language])=>{document.documentElement.setAttribute('data-theme',theme);document.documentElement.setAttribute('lang',language);document.body.classList.add('page-macro','mx4-grid');}", [theme, language])
                        suffix = ".l-en" if language == "en" else ".l-zh"
                        hint = page.locator("#gde-button-context " + suffix)
                        expected = "Warning · partial read" if language == "en" else "警告 · 信息不全"
                        assert hint.text_content() == expected
                        assert page.locator("#gde-button-context").get_attribute("data-gde-stage") == "UNKNOWN"
                        page.evaluate("feed=>{window.__riskProofFeed=feed;Date.now=()=>Date.parse('2026-10-15T15:01:00Z');window.fetch=()=>Promise.resolve({ok:true,json:()=>Promise.resolve(window.__riskProofFeed)});}", live)
                        page.add_script_tag(content=source_js)
                        page.wait_for_function("document.getElementById('gde-live-cause').textContent.includes('Credit stress: building')")
                        live_expected = ("Live: " if language == "en" else "实时：") + expected
                        assert hint.text_content() == live_expected
                        assert page.locator("#gde-button-context").get_attribute("data-gde-stage") == "UNKNOWN"
                        assert page.locator("#gde-live-reading").get_attribute("hidden") is None
                        cases.append({"theme": theme, "language": language, "width": width,
                                      "settled_warning": True, "live_warning": True,
                                      "aggregate_stage": "UNKNOWN", "native_cause": True})
                        page.close()
        finally:
            browser.close()
    print(json.dumps({"kind": "offline_real_chromium_component_proof", "cases": cases,
                      "passed": len(cases), "network_blocked": True,
                      "production": False, "full_application": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
