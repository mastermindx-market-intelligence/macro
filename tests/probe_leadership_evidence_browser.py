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
        from engine import i18n
        return str(i18n.t(en, zh))

    block = re.sub(r"\{\{\s*t\(\s*'((?:[^'\\]|\\.)*)'\s*,\s*'((?:[^'\\]|\\.)*)'\s*\)\s*\}\}", _t, src[i:j])
    return block


def _payload(*, with_cycles: bool = False) -> dict:
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
                 "xDomain": [2025.0, 2027.0], "xDomainDefault": [2025.0, 2027.0],
                 "window_years": 2,
                 "rs_history": {"schema": "sector_cycles.rs_history.v1", "as_of": AS_OF,
                                "mode": "reconstructed_price_history",
                                "naturally_observed": False, "basis": "tr",
                                "benchmark": "SPY"}},
        "sectors": rows,
        "phases": sector_cycles.PHASES,
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
    central = {"as_of": AS_OF, "measured_read": measured, "sectors": [], "baskets": [], "market": {}}
    return {"central": central, "cycles": cycles} if with_cycles else central


def _full_page_html() -> str:
    """Reuse the existing full-template fixture renderer with production escaping."""
    from unittest.mock import patch
    from scripts import capture_us_stocks_compression_evidence as capture
    from engine import i18n

    env = capture._env()
    env.autoescape = True
    env.globals["t"] = i18n.t
    with patch.object(capture, "_env", return_value=env):
        return capture.render_sector_central_page()


def _html(locale: str, theme: str, *, full_page: bool = False) -> str:
    if full_page:
        return _full_page_html()
    panel = _panel_js()
    state_boot = next(block for block in re.findall(r"<script>(.*?)</script>",
                       PAGE.read_text(encoding="utf-8"), re.S)
                      if "var th=localStorage.getItem(\'theme\')" in block)
    handoff = PROPHET.read_text(encoding="utf-8")
    payload = json.dumps(_payload(), ensure_ascii=False)
    return (
        "<!doctype html><html lang=\"{lang}\" data-lang=\"{lang}\" data-theme=\"{theme}\">"
        "<head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Sector Central · leadership evidence probe</title>"
        "<script>{state_boot}</script>"
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
             payload=payload, handoff=handoff, panel=panel, state_boot=state_boot)


# ── the probe ────────────────────────────────────────────────────────────────
def run(output: Path, *, full_page: bool = False) -> dict:
    from playwright.sync_api import sync_playwright

    output.mkdir(parents=True, exist_ok=True)
    report = {
        "scope": ("full_template_and_native_router_with_synthetic_owner_data" if full_page
                  else "isolated_shipped_panel_source_with_engine_dossier"),
        "production_authenticated": False,
        "source_revision": _revision(),
        "page_sha256": hashlib.sha256(PAGE.read_bytes()).hexdigest(),
        "cells": [],
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            cells = ([(VIEWPORTS[0], "en", "dark"), (VIEWPORTS[2], "zh", "light")]
                     if full_page else [(v, locale, theme) for v in VIEWPORTS
                                        for locale in LOCALES for theme in THEMES])
            for (name, width, height), locale, theme in cells:
                cell = _cell(browser, output, name, width, height, locale, theme,
                             full_page=full_page)
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


def _route(page, locale: str, theme: str, *, full_page: bool = False,
           requests: list | None = None):
    """Local document/data and exact referenced source assets; external requests abort."""
    import mimetypes
    from urllib.parse import urlsplit

    payload = _payload(with_cycles=True)
    body = _html(locale, theme, full_page=full_page)
    assets = {urlsplit(s).path.lstrip("/") for s in
              re.findall(r"""(?:src|href)=["']([^"']+)""", body)
              if not urlsplit(s).netloc and
              urlsplit(s).path.endswith((".js", ".css", ".svg", ".ico", ".png"))}
    assets.update({"product-nav-icons.css", "account.js", "terminal_overlay.js",
                   "fonts/Inter-400.woff2", "fonts/Inter-600.woff2", "fonts/Inter-700.woff2"})
    asset_cache: dict[str, bytes | None] = {}
    data = {
        "sector_central_data.js": "window.SECTOR_CENTRAL=" + json.dumps(payload["central"]) + ";",
        "sector_cycles_data.js": "window.SECTOR_CYCLES=" + json.dumps(payload["cycles"]) + ";",
    }

    def handler(route):
        url = urlsplit(route.request.url)
        if url.netloc != "leadership-evidence.test" or url.scheme != "http":
            if requests is not None:
                requests.append({"url": route.request.url, "state": "external_aborted"})
            route.abort()
            return
        name = url.path.lstrip("/")
        if name == "sector_central.html":
            route.fulfill(status=200, content_type="text/html; charset=utf-8", body=body)
        elif full_page and name in data:
            route.fulfill(status=200, content_type="application/javascript", body=data[name])
        elif full_page and name in assets and ".." not in Path(name).parts:
            if name not in asset_cache:
                source = ROOT / "templates" / name
                asset_cache[name] = source.read_bytes() if source.is_file() else None
                if asset_cache[name] is None and not name.endswith("_data.js"):
                    # The existing builder owns compiled shared assets in tracked
                    # site/. Read those exact source bytes even in a sparse checkout.
                    import subprocess
                    result = subprocess.run(["git", "show", "HEAD:site/" + name],
                                            cwd=ROOT, capture_output=True)
                    if result.returncode == 0:
                        asset_cache[name] = result.stdout
            if asset_cache[name] is not None:
                route.fulfill(status=200, content_type=mimetypes.guess_type(name)[0]
                              or "application/octet-stream", body=asset_cache[name])
                return
            if requests is not None:
                requests.append({"path": name, "state": "fixture_asset_unavailable"})
            route.fulfill(status=404, body="")
        else:
            if requests is not None:
                requests.append({"path": name, "state": "outside_fixture_scope"})
            route.fulfill(status=404, content_type="application/json", body="{}")

    return handler


def _cell(browser, output: Path, name: str, width: int, height: int,
          locale: str, theme: str, *, full_page: bool = False) -> dict:
    from playwright.sync_api import Error as PWError

    page = browser.new_page(viewport={"width": width, "height": height})
    errors: list[str] = []
    console: list[str] = []
    page.on("pageerror", lambda e: errors.append(getattr(e, "stack", str(e))))
    page.on("console", lambda m: console.append(f"{m.type}: {m.text}")
            if m.type in ("error", "warning") else None)
    problems: list[str] = []
    requests: list[dict] = []
    journey: dict = {}
    try:
        page.add_init_script("localStorage.setItem('lang'," + json.dumps(locale) +
                             ");localStorage.setItem('theme'," + json.dumps(theme) + ");")
        page.route("**/*", _route(page, locale, theme, full_page=full_page, requests=requests))
        page.goto("http://leadership-evidence.test/sector_central.html" +
                  ("?g=XLE#si-measured" if full_page else ""), wait_until="load")
        if full_page:
            page.wait_for_selector('.si-view[data-view="map"].on', timeout=10000)
            page.wait_for_selector('.si-view-btn[data-view="map"][aria-current="page"]',
                                   timeout=10000)
            journey["deep_link_opens_native_map"] = page.locator("#si-measured").is_visible()
            if not journey["deep_link_opens_native_map"]:
                problems.append("native map route did not expose the measured panel")
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
        if not facts["summary_focus_visible"]:
            problems.append("the disclosure has no visible keyboard focus")
        if (facts["summary_outline_style"] in ("none", "hidden") or
                float(facts["summary_outline_width"].removesuffix("px")) < 2):
            problems.append("the disclosure keyboard outline is missing or under 2px")
        if not facts["details_open"]:
            problems.append("the source-details disclosure did not open")
        if not facts["evidence_text"].strip():
            problems.append("no leadership evidence rendered")
        if errors:
            problems.append("page errors: " + " | ".join(errors))
        # The full fixture deliberately withholds unrelated data organs and records
        # their resource errors. Script exceptions and every target assertion still fail.
        if not full_page and [c for c in console if c.startswith("error")]:
            problems.append("console errors: " + " | ".join(console))
        shot = output / f"{name}-{locale}-{theme}.png"
        page.screenshot(path=str(shot), full_page=True)
        detail = output / f"{name}-{locale}-{theme}--detail.png"
        page.locator("#mr-detail").screenshot(path=str(detail))
        if full_page:
            page.click('#mr-list button[data-g="XLK"]')
            page.wait_for_function("() => new URL(location.href).searchParams.get('g') === 'XLK'")
            journey["selection_updates_existing_url"] = True
            page.go_back()
            page.wait_for_selector('#mr-list button[data-g="XLE"][aria-pressed="true"]')
            page.go_forward()
            page.wait_for_selector('#mr-list button[data-g="XLK"][aria-pressed="true"]')
            page.reload(wait_until="load")
            page.wait_for_selector('#mr-list button[data-g="XLK"][aria-pressed="true"]')
            journey["back_forward_reload_preserve_selection"] = True
            page.locator('.si-view-btn[data-view="overview"]').click(timeout=5000)
            page.wait_for_selector('.si-view[data-view="overview"].on')
            page.locator('a[data-si-workflow="explore"]').click(timeout=5000)
            page.wait_for_selector('.si-view[data-view="map"].on')
            page.locator("#si-measured").scroll_into_view_if_needed()
            journey["existing_workflow_returns_to_map"] = page.locator("#mr-detail .mr-ev").is_visible()
            from engine import leadership_rotation_context as lrc
            empty = lrc.measured_group_read({}, include_sector_dossiers=True)
            page.evaluate("""read => {
                window.SECTOR_CENTRAL.measured_read = read;
                document.dispatchEvent(new Event('langchange'));
            }""", empty)
            page.wait_for_selector('#mr-detail .mr-ev[data-ev-state="ok"]')
            journey["native_empty_keeps_eleven_rows"] = page.locator("#si-measured .mr-row").count() == 11
            page.locator("#mr-detail .mr-ev-sum").click()
            journey["native_empty_has_source_reason"] = "source_session_missing_or_invalid" in page.locator("#mr-detail .mr-ev").inner_text()
            page.evaluate("""read => {
                window.SECTOR_CENTRAL.measured_read = read;
                document.dispatchEvent(new Event('langchange'));
            }""", _payload()["measured_read"])
            page.wait_for_selector('#mr-detail .mr-ev[data-ev-state="ok"]')
            journey["restored_packet_disclosure_closed"] = not page.locator("#mr-detail details.mr-ev-det").evaluate("el => el.open")
            if not all(journey.values()):
                problems.append("full-page journey assertion failed: " + json.dumps(journey))
            if errors and not any(p.startswith("page errors:") for p in problems):
                problems.append("page errors: " + " | ".join(errors))
        return {
            "viewport": name, "width": width, "height": height,
            "locale": locale, "theme": theme,
            "screenshot": shot.name, "detail_screenshot": detail.name,
            "page_errors": errors, "console": console,
            "facts": facts, "journey": journey, "request_boundaries": requests,
            "problems": problems,
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
    ap.add_argument("--full-page", action="store_true",
                    help="exercise the full native template/router at desktop EN and phone ZH")
    args = ap.parse_args(argv)
    report = run(Path(args.output), full_page=args.full_page)
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
