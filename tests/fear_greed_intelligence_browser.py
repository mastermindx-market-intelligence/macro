"""Reproduce the actual Fear/Greed dashboard path with immutable data and real assets.

Anonymous component specimens are explicit presentation fixtures for the canonical
capture tool, not production routes. Full-page checks use the existing isolated
registration simulation; no real credentials, protected endpoint or account is used.
Run: .venv/bin/python tests/fear_greed_intelligence_browser.py --output /tmp/macro-fg-proof
"""
from __future__ import annotations

import argparse
from functools import lru_cache, partial
import hashlib
import http.server
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import threading
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def prepare(output: Path, source_ref: str) -> dict:
    from engine.fear_greed_intelligence import compute_intelligence
    from lib.site_assets import copy_asset
    from tests.risk_radar_workspace_browser import render_fixture
    from tests.test_fear_greed import _make_min_fg, _render_fg_macro_signals

    output = output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("Browser preview must be outside the repository")
    output.mkdir(parents=True, exist_ok=True)
    source_sha = subprocess.check_output(["git", "rev-parse", source_ref + "^{commit}"], cwd=ROOT, text=True).strip()
    source_hashes = {}

    @lru_cache(maxsize=16)
    def pinned_read(category, name):
        path = f"data/{category}/{name}.parquet"
        result = subprocess.run(["git", "show", f"{source_sha}:{path}"], cwd=ROOT, capture_output=True)
        if result.returncode:
            return None
        source_hashes[path] = hashlib.sha256(result.stdout).hexdigest()
        return pd.read_parquet(BytesIO(result.stdout))

    with patch("engine.fear_greed_intelligence.store.read", side_effect=pinned_read):
        intelligence = compute_intelligence(as_of="2026-10-16")
    input_path = output / "candidate-intelligence.json"
    input_path.write_text(json.dumps(intelligence, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    receipt = render_fixture(output, source_sha, intelligence_path=input_path)
    receipt["intelligence_input_sha256"] = source_hashes
    receipt["candidate_engine_sha256"] = {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in ("engine/vol_velocity.py", "engine/fear_greed_intelligence.py", "engine/fear_greed.py")
    }
    # Same production asset emitter, into this preview only, with exact candidate sources.
    for asset in (ROOT / "templates").iterdir():
        if asset.is_file() and asset.suffix in {".css", ".js", ".svg", ".ico"}:
            target = output / asset.name
            if target.is_symlink():
                target.unlink()
            if asset.suffix in {".css", ".js"}:
                copy_asset(asset.name, asset, output)
            else:
                target.write_bytes(asset.read_bytes())
    fonts = ROOT / "templates/fonts"
    if fonts.exists() and not (output / "fonts").exists():
        (output / "fonts").symlink_to(fonts, target_is_directory=True)
    component = (output / "risk-radar-component.html").read_text()
    setup = ('<script>window.addEventListener("DOMContentLoaded",function(){'
             'document.querySelector(".rkw-explore [data-rkw-view=sentiment]").click();'
             '});</script>')
    (output / "fear-greed-component.html").write_text(component.replace("</body>", setup + "</body>"))
    deep_setup = setup.replace('});</script>',
                              'document.querySelectorAll(".fgi-details").forEach(function(d){d.open=true;});'
                              '});</script>')
    (output / "fear-greed-deep-component.html").write_text(component.replace("</body>", deep_setup + "</body>"))
    study = _render_fg_macro_signals({**_make_min_fg(), "intelligence": intelligence})
    (output / "study-component.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
        'content="width=device-width,initial-scale=1"><link rel="stylesheet" href="theme.css">'
        '<link rel="stylesheet" href="fear_greed_intelligence.css"></head><body>' + study + '</body></html>')
    (output / "source-inputs.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def check(output: Path) -> dict:
    from playwright.sync_api import sync_playwright

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(output)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    passed, errors, metrics = [], [], []
    shots = output / "interaction-shots"
    shots.mkdir(exist_ok=True)
    expected = json.loads((output / "candidate-intelligence.json").read_text())

    def record(name, result):
        if not result:
            raise AssertionError(name)
        passed.append(name)

    try:
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            for width, height, viewport in ((1440, 900, "desktop"), (390, 844, "mobile")):
                for language in ("en", "zh"):
                    for theme in ("dark", "light"):
                        cell = f"{viewport}-{language}-{theme}"
                        context = browser.new_context(viewport={"width": width, "height": height})
                        context.route("**/*", lambda route: route.continue_()
                                      if route.request.url.startswith(origin + "/") else route.abort())
                        page = context.new_page()
                        page.on("pageerror", lambda e: errors.append(str(e)))
                        page.goto(origin + "/macro.html", wait_until="domcontentloaded")
                        page.wait_for_selector("#dlg-risk.rkw-ready", state="attached")
                        page.evaluate("""([language,theme])=>{
                            document.documentElement.dataset.lang=language;
                            document.documentElement.lang=language==='zh'?'zh-Hans':'en';
                            document.documentElement.dataset.theme=theme;
                            window.MMXAccessPreview={isAnon:function(){return false;}};
                        }""", [language, theme])
                        trigger = page.locator('[onclick*="mx5OpenDlg"][onclick*="dlg-risk"]').first
                        trigger.click()
                        page.wait_for_selector("#dlg-risk.mx5-dlg-in")
                        page.locator('.rkw-explore button[data-rkw-view="sentiment"]').click()
                        fgi = page.locator("#fear-greed-dynamics")
                        fgi.wait_for(state="visible")
                        page.wait_for_timeout(300)  # Let the existing inspector transition settle.
                        record(cell + " actual Risk Radar navigation", page.locator("#rkw-inspector-title").inner_text().strip()
                               == ("Fear & Greed" if language == "en" else "恐惧与贪婪"))
                        record(cell + " versioned payload", fgi.get_attribute("data-fgi-version") == expected["schema"])
                        record(cell + " sentiment and VIX clocks", expected["as_of"] in fgi.inner_text()
                               and expected["dynamics"]["as_of"] in fgi.inner_text())
                        record(cell + " correct direction", fgi.locator(".fgi-state").get_attribute("data-fgi-phase")
                               == expected["dynamics"]["phase"])
                        record(cell + " native details initially closed", not fgi.locator(".fgi-details").first.evaluate("e=>e.open"))
                        nav_bounds = page.locator('.rkw-context-nav button').evaluate_all(
                            "buttons=>buttons.every(b=>b.scrollWidth<=b.clientWidth+1)")
                        record(cell + " navigation text fits each button", nav_bounds)
                        page.screenshot(path=str(shots / (cell + "-summary.png")))
                        for detail in fgi.locator(".fgi-details").all():
                            detail.locator("summary").click()
                            record(cell + " disclosure opens", detail.evaluate("e=>e.open"))
                        record(cell + " three volatility paths", fgi.locator(".fgi-vol-trails svg").count() == 3)
                        record(cell + " seven measures explained", fgi.locator("tbody tr").count() == 7)
                        record(cell + " six independent family votes", fgi.locator(".fgi-families > div").count() == 6)
                        record(cell + " proxy provenance visible", ("not the official Cboe" if language == "en" else "不是 Cboe 官方") in fgi.inner_text())
                        boxes = page.locator("#dlg-risk .mx5-dlg-body").evaluate("""e=>({
                            scrollWidth:e.scrollWidth,clientWidth:e.clientWidth,
                            documentWidth:document.documentElement.scrollWidth,viewport:innerWidth})""")
                        record(cell + " no document horizontal overflow", boxes["documentWidth"] <= width + 1)
                        record(cell + " no dialog horizontal overflow", boxes["scrollWidth"] <= boxes["clientWidth"] + 1)
                        metrics.append({"cell": cell, **boxes})
                        fgi.locator(".fgi-state").scroll_into_view_if_needed()
                        page.screenshot(path=str(shots / (cell + "-detail.png")))
                        page.keyboard.press("Escape")
                        record(cell + " Escape returns to overview", page.locator(".rkw-overview").is_visible())
                        page.keyboard.press("Escape")
                        page.wait_for_selector("#dlg-risk.open", state="hidden")
                        record(cell + " dialog close restores focus", trigger.evaluate("e=>document.activeElement===e"))
                        context.close()
            # The source-backed study specimen exercises the shared partial and real anchor.
            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(origin + "/study-component.html", wait_until="domcontentloaded")
            record("study destination anchor exists", page.locator("#fear-greed-detail").count() == 1)
            record("study meter matches engine", float(page.locator(".fgi-meter").get_attribute("value")) == expected["score"])
            context.close()
            browser.close()
        record("no JavaScript exceptions", not errors)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    result = {"passed": len(passed), "checks": passed, "metrics": metrics, "page_errors": errors,
              "scope": "candidate production template and controller; isolated source-backed fixtures; not a deployed claim"}
    (output / "ui-checks.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-ref", default="HEAD")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args()
    receipt = prepare(args.output, args.source_ref)
    result = {"source_ref": receipt["source_ref"], "output": str(args.output)}
    if not args.build_only:
        result.update(check(args.output))
    print(json.dumps({k: v for k, v in result.items() if k != "checks"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
