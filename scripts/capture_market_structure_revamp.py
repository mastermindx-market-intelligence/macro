#!/usr/bin/env python3
"""Capture the real Market Structure template with a specified, dated artifact.

Local preview evidence only: no Paper or production-deployment claim. Does not
change the source artifact, hide shared chrome, or write to the live site tree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_market_structure_page import render  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "snapshot.html").write_text(render(ROOT, fixture=args.fixture))
    (out / "empty.html").write_text(render(ROOT, fixture=out / "unavailable.json"))
    (out / "dated.html").write_text(render(ROOT, fixture=args.fixture,
                                         now=datetime(2026, 10, 20, 22, tzinfo=timezone.utc)))

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def translate_path(self, path):
            relative = unquote(urlsplit(path).path).lstrip("/")
            roots = (out, ROOT / "templates", ROOT / "site") if relative.split("?")[0] in {
                "market_structure.js", "market_structure.css"
            } else (out, ROOT / "site", ROOT / "templates")
            for root in roots:
                candidate = (root / relative).resolve()
                if candidate.is_relative_to(root.resolve()) and candidate.is_file():
                    return str(candidate)
            return str(out / "__missing__")

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_port}"
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    result = {"evidence_kind": "LOCAL_TEMPLATE_PREVIEW_NOT_PAPER_NOT_PRODUCTION",
              "created_at": datetime.now(timezone.utc).isoformat(),
              "artifact_sha256": hashlib.sha256(args.fixture.read_bytes()).hexdigest(),
              "artifact_asof": json.loads(args.fixture.read_text()).get("asof"),
              "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in [ROOT / "templates" / f"market_structure.{suffix}" for suffix in ("html.j2", "css", "js")]
                                + [ROOT / "lib/market_structure_view.py", ROOT / "scripts/build_market_structure_page.py"]},
              "cells": [], "interactions": {}}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for width, height, size in [(1440, 1100, "desktop"), (390, 1100, "mobile")]:
                for theme in ("dark", "light"):
                    for lang in ("en", "zh"):
                        name = f"{size}-{theme}-{lang}"
                        ctx = browser.new_context(viewport={"width": width, "height": height},
                                                  device_scale_factor=1, locale="zh-CN" if lang == "zh" else "en-US",
                                                  color_scheme=theme, reduced_motion="reduce", accept_downloads=True)
                        ctx.add_init_script("localStorage.setItem('theme'," + json.dumps(theme) + ");"
                                            "localStorage.removeItem('themeAuto');localStorage.setItem('lang'," + json.dumps(lang) + ");")
                        page = ctx.new_page()
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.goto(base + "/snapshot.html", wait_until="domcontentloaded")
                        page.wait_for_function("document.getElementById('market-structure').dataset.chartStatus")
                        page.evaluate("document.fonts.ready")
                        page.screenshot(path=str(out / f"{name}.png"), full_page=True, animations="disabled")
                        page.screenshot(path=str(out / f"{name}-top.png"), animations="disabled")
                        check = page.evaluate("""() => ({
                            width:innerWidth, scrollWidth:document.documentElement.scrollWidth,
                            theme:document.documentElement.dataset.theme, lang:document.documentElement.dataset.lang,
                            headingCount:document.querySelectorAll('main h1').length,
                            canvases:document.querySelectorAll('main canvas').length,
                            chartError:document.getElementById('market-structure').dataset.chartError || null,
                            chartStatus:document.getElementById('market-structure').dataset.chartStatus,
                            rangeTargets:Array.from(document.querySelectorAll('[data-range]')).every(b=>b.getBoundingClientRect().height>=40),
                            navPresent:!!document.querySelector('.site-nav'),
                            ageWarningVisible:!document.getElementById('msp-age-warning').hidden
                        })""")
                        check.update(name=name, screenshot=f"{name}.png", errors=errors)
                        check["pass"] = (check["scrollWidth"] <= width and check["headingCount"] == 1 and
                                         check["chartStatus"] == "ready" and not check["chartError"] and
                                         check["rangeTargets"] and check["navPresent"] and not errors)
                        result["cells"].append(check)
                        if name == "desktop-dark-en":
                            page.locator('[data-chart="gamma"][data-range="21"]').click()
                            page.locator('#gamma-scrub').focus()
                            page.keyboard.press("Home")
                            first = page.locator('#gamma-readout').inner_text()
                            page.keyboard.press("ArrowRight")
                            second = page.locator('#gamma-readout').inner_text()
                            page.locator('[data-observations="gamma"] > summary').click()
                            rows = page.locator('#gamma-table tbody tr').count()
                            pressed = page.locator('[data-chart="gamma"][aria-pressed="true"]').get_attribute('data-range')
                            with page.expect_download() as download:
                                page.locator('[data-download="gamma"]').click()
                            download.value.save_as(str(out / 'selected-gamma.csv'))
                            csv_lines = (out / 'selected-gamma.csv').read_text().splitlines()
                            page.locator('#msp-fund-series').select_option('cta_score')
                            result["interactions"].update(range_selected=pressed, table_sessions=rows,
                                keyboard_changed_session=first != second, csv_rows=len(csv_lines)-1,
                                fund_series=page.locator('#msp-fund-series').input_value(),
                                range_persisted=page.evaluate("localStorage.getItem('msp-gex-range')"))
                            page.screenshot(path=str(out / 'observations-open.png'), full_page=True, animations="disabled")
                            page.goto(base + "/empty.html", wait_until="domcontentloaded")
                            page.wait_for_function("document.getElementById('market-structure').dataset.chartStatus")
                            result["interactions"]["empty_disabled"] = page.locator('[data-range]:not([disabled])').count() == 0
                            result["interactions"]["empty_rendered"] = 'incomplete' in page.locator('h1').inner_text()
                            page.screenshot(path=str(out / 'empty.png'), full_page=True, animations="disabled")
                        ctx.close()
                        print(name, "PASS" if check["pass"] else "FAIL", json.dumps(check, ensure_ascii=False), flush=True)
            # Check a cached page aging past the next expected session, using a
            # test clock. This is deliberately labelled synthetic timing proof.
            ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
            ctx.add_init_script("""{
                const RealDate=Date; window.__testNow=Date.parse('2026-10-20T22:00:00Z');
                class TestDate extends RealDate { constructor(...args){super(...(args.length?args:[window.__testNow]));} static now(){return window.__testNow;} }
                window.Date=TestDate;localStorage.setItem('lang','en');localStorage.setItem('theme','dark');
            }""")
            page = ctx.new_page()
            page.goto(base + "/dated.html", wait_until="domcontentloaded")
            page.wait_for_function("document.getElementById('market-structure').dataset.chartStatus")
            before = page.locator('#msp-age-warning').is_visible()
            page.evaluate("window.__testNow=Date.parse('2026-10-26T22:00:00Z');document.dispatchEvent(new Event('visibilitychange'))")
            after = page.locator('#msp-age-warning').is_visible()
            archived = page.locator('#msp-week-status').inner_text()
            result["interactions"].update(cache_ages_without_reload=(not before and after), expired_week_on_cached_page='Archived' in archived)
            ctx.close()
            browser.close()
    finally:
        httpd.shutdown()
    i = result["interactions"]
    result["pass"] = all(c["pass"] for c in result["cells"]) and all([
        i.get('range_selected') == '21', i.get('table_sessions') == 21,
        i.get('keyboard_changed_session'), i.get('csv_rows') == 21,
        i.get('fund_series') == 'cta_score', i.get('range_persisted') == '21',
        i.get('empty_disabled'), i.get('empty_rendered'), i.get('cache_ages_without_reload'),
        i.get('expired_week_on_cached_page')])
    (out / "evidence.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"pass": result["pass"], "interactions": i, "out": str(out)}, ensure_ascii=False), flush=True)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
