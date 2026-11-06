"""Isolated real-script browser probe; NOT authenticated production acceptance.

Run: python3 tests/probe_rotation_early_context_browser.py --output /tmp/rotation-proof
Every request is fulfilled locally or aborted. No credentials, collectors or sends.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "eb5f608851a8d3ea8181953a28f271ec846240dd"
CSS = """
:root{--bg:#f6f7f9;--panel:#fff;--panel2:#f8fafc;--line:#d8dfe8;
--muted:#556170;--ink:#17212f;--link:#235ba8;--warn:#8b5200;--pos:#166534;--neg:#a52030;}
[data-theme=dark]{--bg:#111722;--panel:#192231;--panel2:#141e2b;--line:#344357;
--muted:#b0bac9;--ink:#ecf1f8;--link:#9bc9ff;--warn:#efbb72;--pos:#86dba6;--neg:#f49ca3;}
*{box-sizing:border-box}body{margin:0;padding:16px;background:var(--bg);color:var(--ink);font-family:Arial,sans-serif}
main{max-width:1080px;margin:auto}.qa-note{font-size:12px;line-height:1.5}.l-zh{display:none}
[data-lang=zh] .l-en{display:none}[data-lang=zh] .l-zh{display:inline}
"""


def run(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    script = (ROOT / "templates/rotation_events.js").read_bytes()
    snapshot = subprocess.check_output(
        ["git", "show", f"{SOURCE}:site/marketdata/rotation_events.json"], cwd=ROOT
    )
    report = {"scope": "isolated_existing_script_with_pinned_producer_snapshot",
              "production_authenticated": False, "source_revision": SOURCE,
              "script_sha256": hashlib.sha256(script).hexdigest(),
              "snapshot_sha256": hashlib.sha256(snapshot).hexdigest(), "cases": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for width, theme, lang in [(320,"light","en"),(390,"dark","en"),(1280,"light","en"),(390,"dark","zh")]:
                page = browser.new_page(viewport={"width": width, "height": 960})
                errors, intercepted, blocked = [], [], []
                page.on("pageerror", lambda e: errors.append(str(e)))
                # The clock is deliberately historical and explicit, not a live-market proof.
                page.add_init_script("Date.now = () => Date.parse('2026-10-22T20:00:00Z');")
                html = (f'<!doctype html><html lang="{lang}" data-lang="{lang}" data-theme="{theme}">'
                        f'<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>{CSS}</style></head>'
                        '<body><main><p class="qa-note">Component QA · retained October 20 source snapshot · not a live market signal or production acceptance</p>'
                        '<div id="rc-events-mount"></div></main><script src="/rotation_events.js"></script></body></html>')

                def route(r):
                    u = urlparse(r.request.url)
                    intercepted.append(u.path)
                    content = {"/": ("text/html", html), "/rotation_events.js": ("text/javascript", script),
                               "/marketdata/rotation_events.json": ("application/json", snapshot),
                               "/marketdata/sector_fragmentation.json": ("application/json", "{}")}
                    if u.hostname == "defensive-rotation.test" and u.path in content:
                        typ, body = content[u.path]
                        r.fulfill(status=200, content_type=typ, body=body)
                    else:
                        blocked.append(r.request.url)
                        r.abort()

                page.route("**/*", route)
                page.goto("http://defensive-rotation.test/", wait_until="networkidle")
                page.locator(".rc-ec-pair").first.wait_for()
                assert page.locator(".rc-ec-pair").count() == 4
                # Exercise both current theme fallbacks and future canonical tokens.
                assert page.locator(".rc-early-context").evaluate("e => getComputedStyle(e).borderTopLeftRadius") == "12px"
                assert page.locator(".rc-ec-pair").first.evaluate("e => getComputedStyle(e).borderTopLeftRadius") == "8px"
                page.evaluate("document.documentElement.style.setProperty('--r-card', '16px'); document.documentElement.style.setProperty('--r-ctl', '6px')")
                assert page.locator(".rc-early-context").evaluate("e => getComputedStyle(e).borderTopLeftRadius") == "16px"
                assert page.locator(".rc-ec-pair").first.evaluate("e => getComputedStyle(e).borderTopLeftRadius") == "6px"
                page.evaluate("document.documentElement.style.removeProperty('--r-card'); document.documentElement.style.removeProperty('--r-ctl')")
                assert not errors, errors
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "horizontal overflow"
                assert page.locator(".rc-ec-conflict").count() == 3
                assert "2026-10-20" in page.locator("#rc-early-context").inner_text()
                page.locator(".rc-ec-details summary").first.focus()
                page.keyboard.press("Enter")
                assert page.locator(".rc-ec-details").first.get_attribute("open") is not None
                assert "+17.93%" in page.locator(".rc-ec-details").first.inner_text()
                name = f"{width}-{theme}-{lang}.png"
                page.locator("#rc-early-context").screenshot(path=str(output / name))
                report["cases"].append({"width":width,"theme":theme,"language":lang,"pairs":4,"conflicts":3,
                    "page_errors":errors,"horizontal_overflow":False,"keyboard_details":True,"radius_fallback_and_token_override":True,
                    "intercepted_requests":intercepted,"blocked_requests":blocked,"screenshot":name})
                page.close()
        finally:
            browser.close()
    (output / "receipt.json").write_text(json.dumps(report, indent=2)+"\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2))
