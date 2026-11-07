"""Isolated real-browser probe for the Sector Central leadership-evidence
addendum (PSL-3). NOT authenticated production acceptance.

Run: python3 tests/probe_leadership_evidence_browser.py --output /tmp/psl4-evidence

What is under test is the SHIPPED source, not a mock of it: the measured
panel's own ``<style>`` block and the ``mr-panel`` JavaScript region are read
verbatim out of ``templates/sector_central.html.j2``, the design tokens come
from ``templates/theme.css``, and the measured read is the frozen artifact with
the actual engine's dated addendum attached. Every request is fulfilled
locally or aborted. No credentials, no collectors, no sends, no production
page, and nothing under ``site/`` or ``data/`` is written.

The receipts are literal: console/page errors, the horizontal-overflow
measurement at each viewport, the disclosure target height and the focus-ring
computation are read out of the live document and written to the receipt JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "templates" / "sector_central.html.j2"
THEME = ROOT / "templates" / "theme.css"
PROPHET = ROOT / "templates" / "_sector_prophet_context.js.j2"
FIXTURE = ROOT / "tests" / "fixtures" / "leadership_rotation" / "measured_read_v1.json"

START = "/* mr-panel:start */"
END = "/* mr-panel:end */"

#: desktop, tablet, phone, and the 320px floor the responsive law names.
VIEWPORTS = [("desktop", 1440, 900), ("tablet", 834, 1112),
             ("phone", 390, 844), ("small", 320, 640)]
LOCALES = ["en", "zh"]
THEMES = ["dark", "light"]

AS_OF = "2026-10-09"
H21 = {"XLB": -0.6, "XLC": 1.1, "XLE": 2.4, "XLF": 0.3, "XLI": -0.2,
       "XLK": -0.5, "XLP": -1.0, "XLV": 0.2, "XLY": 1.7}
H63 = {"XLB": -1.4, "XLC": 2.3, "XLE": 4.1, "XLF": 1.2, "XLI": -0.7,
       "XLK": 0.0, "XLP": -2.2, "XLV": 0.9, "XLY": 3.3}


# ── the shipped source, read out of the repository ────────────────────────────
def _style_block() -> str:
    """The measured panel's own stylesheet block, verbatim."""
    src = PAGE.read_text(encoding="utf-8")
    for m in re.finditer(r"<style>(.*?)</style>", src, re.S):
        if ".mr-listbox" in m.group(1):
            return m.group(1)
    raise SystemExit("the measured panel style block was not found")


def _panel_js() -> str:
    src = PAGE.read_text(encoding="utf-8")
    i = src.index(START)
    return src[i:src.index(END, i) + len(END)]


def _markup(locale: str) -> str:
    """The shipped #si-measured markup with its Jinja labels resolved."""
    src = PAGE.read_text(encoding="utf-8")
    i = src.index('<section class="rvx-sec mr-sec" id="si-measured"')
    j = src.index("</section>", i) + len("</section>")

    def _t(m):
        en, zh = m.group(1), m.group(2)
        return (zh if locale == "zh" else en).replace("'", "’")

    block = re.sub(r"\{\{\s*t\(\s*'((?:[^'\\]|\\.)*)'\s*,\s*'((?:[^'\\]|\\.)*)'\s*\)\s*\}\}", _t, src[i:j])
    return block


def _payload() -> dict:
    """The frozen measured read plus the ACTUAL engine's dated addendum."""
    sys.path.insert(0, str(ROOT))
    from engine import leadership_rotation_context as lrc
    from engine import sector_cycles

    rows = []
    for ticker, info in sorted(sector_cycles.SECTORS.items()):
        if ticker == "XLRE":
            continue
        rows.append({
            "id": ticker.lower(), "ticker": ticker, "kind": "sector",
            "name": info["name"], "name_zh": info["name_zh"],
            "group": info["group"], "accent": info["accent"],
            "now": {"rs_21d": H21.get(ticker), "rs_63d": H63.get(ticker),
                    "thin_history": ticker == "XLU"},
            "series_provenance": {
                "schema": "sector_cycles.series_provenance.v1",
                "structure_basis": "tr", "rs_basis": "tr",
                "membership": "single_instrument", "point_in_time": True,
                "benchmark": "SPY",
                "history_mode": "reconstructed_price_history"},
        })
    cycles = {
        "meta": {"asOf": AS_OF, "benchmark": "SPY",
                 "rs_history": {"schema": "sector_cycles.rs_history.v1", "as_of": AS_OF,
                                "mode": "reconstructed_price_history",
                                "naturally_observed": False, "basis": "tr",
                                "benchmark": "SPY"}},
        "sectors": rows,
    }
    dossier = lrc.measured_group_read(cycles, include_sector_dossiers=True)["sector_dossiers"]
    measured = json.loads(FIXTURE.read_text(encoding="utf-8"))
    measured["sector_dossiers"] = dossier
    # The addendum and the frozen read must agree on every measured identity —
    # the engine guarantees it; assert it here so the probe cannot photograph a
    # disagreement.
    legacy = {g["group_id"]: g["current"] for g in measured["groups"]}
    for row in dossier["groups"]:
        cur = legacy.get(row["group_id"], {})
        for window, field in ((21, "rs_21d"), (63, "rs_63d")):
            value = row["relative_wealth_pct"][field]
            assert value == cur.get(field), (row["group_id"], field, value, cur.get(field))
    return {"as_of": AS_OF, "measured_read": measured}


def _html(locale: str, theme: str) -> str:
    panel = _panel_js()
    handoff = PROPHET.read_text(encoding="utf-8")
    payload = json.dumps(_payload(), ensure_ascii=False)
    return (
        "<!doctype html><html lang=\"{lang}\" data-lang=\"{lang}\" data-theme=\"{theme}\">"
        "<head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Sector Central · leadership evidence probe</title>"
        "<style>{theme_css}</style><style>{panel_css}</style>"
        "<style>body{{margin:0;background:var(--bg);color:var(--text);"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Noto Sans SC',sans-serif}}"
        ".probe-wrap{{max-width:1180px;margin:0 auto;padding:16px}}"
        ".probe-note{{font-size:12px;color:var(--muted);margin:0 0 12px;line-height:1.5}}</style>"
        "</head><body><div class=\"probe-wrap\">"
        "<p class=\"probe-note\">Component probe · the shipped measured-panel source · "
        "synthetic producer inputs · not a live market signal or production acceptance</p>"
        "{markup}</div>"
        "<script>window.SECTOR_CENTRAL = {payload};</script>"
        "<script>{handoff}</script><script>{panel}</script>"
        "</body></html>"
    ).format(lang=locale, theme=theme, theme_css=THEME.read_text(encoding="utf-8"),
             panel_css=_style_block(), markup=_markup(locale),
             payload=payload, handoff=handoff, panel=panel)


# ── the probe ────────────────────────────────────────────────────────────────
def run(output: Path) -> dict:
    from playwright.sync_api import sync_playwright

    output.mkdir(parents=True, exist_ok=True)
    report = {
        "scope": "isolated_shipped_panel_source_with_engine_dossier",
        "production_authenticated": False,
        "source_revision": _revision(),
        "page_sha256": hashlib.sha256(PAGE.read_bytes()).hexdigest(),
        "cells": [],
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for name, width, height in VIEWPORTS:
                for locale in LOCALES:
                    for theme in THEMES:
                        cell = _cell(browser, output, name, width, height, locale, theme)
                        report["cells"].append(cell)
        finally:
            browser.close()
    failures = [c for c in report["cells"] if c["problems"]]
    report["outcome"] = "captured" if not failures else "problems_found"
    report["problem_count"] = len(failures)
    (output / "receipt.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def _revision() -> str:
    import subprocess

    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _route(page, locale: str, theme: str):
    """Fulfil the one local document; abort everything else. A real origin
    (not about:blank) so the panel's own history.pushState behaves as it does
    on the page."""
    body = _html(locale, theme)

    def handler(route):
        if route.request.url.startswith("http://leadership-evidence.test/"):
            route.fulfill(status=200, content_type="text/html; charset=utf-8", body=body)
        else:
            route.abort()

    return handler


def _cell(browser, output: Path, name: str, width: int, height: int,
          locale: str, theme: str) -> dict:
    from playwright.sync_api import Error as PWError

    page = browser.new_page(viewport={"width": width, "height": height})
    errors: list[str] = []
    console: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: console.append(f"{m.type}: {m.text}")
            if m.type in ("error", "warning") else None)
    problems: list[str] = []
    try:
        page.route("**/*", _route(page, locale, theme))
        page.goto("http://leadership-evidence.test/sector_central.html",
                  wait_until="load")
        page.wait_for_selector('#mr-list button[data-g="XLE"]', timeout=10000)
        page.click('#mr-list button[data-g="XLE"]')
        page.wait_for_selector("#mr-detail .mr-ev", timeout=10000)
        page.wait_for_selector("#mr-detail .mr-ev-sum", timeout=10000)
        # open the source-details disclosure — the deep state that must not
        # overflow at any width
        page.click("#mr-detail .mr-ev-sum")
        page.wait_for_function(
            "() => { var d = document.querySelector('details.mr-ev-det');"
            " return d && d.open; }", timeout=5000)
        page.keyboard.press("Tab")          # establish keyboard modality
        page.focus("#mr-detail .mr-ev-sum")
        facts = page.evaluate(
            """() => {
                var de = document.documentElement;
                var sum = document.querySelector('#mr-detail .mr-ev-sum');
                var wide = [];
                document.querySelectorAll('#si-measured *').forEach(function (el) {
                    var r = el.getBoundingClientRect();
                    if (r.width > 0 && (r.right > window.innerWidth + 0.5 || r.left < -0.5)) {
                        wide.push(el.tagName + '.' + (el.className || '') + ':' +
                                  Math.round(r.left) + '..' + Math.round(r.right));
                    }
                });
                var cs = getComputedStyle(sum);
                return {
                    scrollWidth: de.scrollWidth,
                    innerWidth: window.innerWidth,
                    horizontal_overflow: de.scrollWidth > window.innerWidth + 0.5,
                    elements_wider_than_viewport: wide.length,
                    wide_elements: wide.slice(0, 5),
                    summary_height: Math.round(sum.getBoundingClientRect().height),
                    summary_focus_visible: sum.matches(':focus-visible'),
                    summary_outline_width: cs.outlineWidth,
                    summary_outline_style: cs.outlineStyle,
                    evidence_text: (document.querySelector('#mr-detail .mr-ev') || {}).innerText || '',
                    details_open: !!(document.querySelector('details.mr-ev-det') || {}).open,
                    panel_rows: document.querySelectorAll('#mr-list .mr-row').length
                };
            }""")
        if facts["horizontal_overflow"]:
            problems.append("horizontal overflow with the source details open")
        if facts["elements_wider_than_viewport"]:
            problems.append("elements wider than the viewport: " + "; ".join(facts["wide_elements"]))
        if facts["summary_height"] < 44:
            problems.append(f"disclosure target is {facts['summary_height']}px, under 44px")
        if not facts["details_open"]:
            problems.append("the source-details disclosure did not open")
        if not facts["evidence_text"].strip():
            problems.append("no leadership evidence rendered")
        if errors:
            problems.append("page errors: " + " | ".join(errors))
        if [c for c in console if c.startswith("error")]:
            problems.append("console errors: " + " | ".join(console))
        shot = output / f"{name}-{locale}-{theme}.png"
        page.screenshot(path=str(shot), full_page=True)
        detail = output / f"{name}-{locale}-{theme}--detail.png"
        page.locator("#mr-detail").screenshot(path=str(detail))
        return {
            "viewport": name, "width": width, "height": height,
            "locale": locale, "theme": theme,
            "screenshot": shot.name, "detail_screenshot": detail.name,
            "page_errors": errors, "console": console,
            "facts": facts, "problems": problems,
        }
    except PWError as exc:
        problems.append(f"playwright: {exc}")
        if errors:
            problems.append("page errors: " + " | ".join(errors))
        if console:
            problems.append("console: " + " | ".join(console))
        return {"viewport": name, "width": width, "height": height, "locale": locale,
                "theme": theme, "page_errors": errors, "console": console,
                "problems": problems}
    finally:
        page.close()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default="/tmp/psl4-leadership-evidence")
    args = ap.parse_args(argv)
    report = run(Path(args.output))
    print(json.dumps({"outcome": report["outcome"],
                      "cells": len(report["cells"]),
                      "problems": report["problem_count"],
                      "receipt": str(Path(args.output) / "receipt.json")}, indent=1))
    for cell in report["cells"]:
        if cell["problems"]:
            print(f"  {cell['viewport']}/{cell['locale']}/{cell['theme']}: "
                  + " | ".join(cell["problems"]))
    return 1 if report["problem_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
