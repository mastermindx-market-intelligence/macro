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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
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


def _html(locale: str, theme: str, *, full_page: bool = False,
          native_generation: bool = False) -> str:
    if full_page:
        rendered = _full_page_html()
        return rendered if native_generation else rendered.replace(
            'data-sector-generation="native"', 'data-sector-generation="component"')
    panel = _panel_js()
    state_boot = next(block for block in re.findall(r"<script>(.*?)</script>",
                       PAGE.read_text(encoding="utf-8"), re.S)
                      if "var th=localStorage.getItem(\'theme\')" in block)
    handoff = PROPHET.read_text(encoding="utf-8")
    payload = json.dumps({"as_of":"1900-01-01"} if native_generation else _payload(), ensure_ascii=False)
    # The existing component-only cases deliberately isolate the renderer.
    # The native transport cases retain the actual shipped markup/activation.
    markup = _markup(locale)
    if not native_generation:
        markup = markup.replace('data-sector-generation="native"', 'data-sector-generation="component"')
    auth = ("window.MDXAuth={hasSession:function(){return false;}};"
            if native_generation else "")
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
        "<script>window.SECTOR_CENTRAL = {payload};{auth}</script>"
        "<script>{handoff}</script><script>{panel}</script>"
        "</body></html>"
    ).format(lang=locale, theme=theme, theme_css=THEME.read_text(encoding="utf-8"),
             panel_css=_style_block(), markup=markup,
             payload=payload, handoff=handoff, panel=panel, state_boot=state_boot, auth=auth)


# ── the probe ────────────────────────────────────────────────────────────────
def run(output: Path, *, full_page: bool = False, generation_wire: Path | None = None) -> dict:
    if generation_wire is not None:
        return _run_native_wire(output, generation_wire, full_page=full_page)
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

    # Source hashes identify an isolated qualification snapshot without
    # pretending it is a committed or deployed revision.
    if (ROOT / "snapshot-source-hashes.json").is_file():
        return "isolated_source_snapshot:" + hashlib.sha256(
            (ROOT / "snapshot-source-hashes.json").read_bytes()).hexdigest()
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _route(page, locale: str, theme: str, *, full_page: bool = False,
           requests: list | None = None, native_generation: bool = False):
    """Local document/data and exact referenced source assets; external requests abort."""
    import mimetypes
    from urllib.parse import urlsplit

    payload = _payload(with_cycles=True)
    body = _html(locale, theme, full_page=full_page, native_generation=native_generation)
    if native_generation:
        payload["central"]["as_of"] = "1900-01-01"
    assets = {urlsplit(s).path.lstrip("/") for s in
              re.findall(r"""(?:src|href)=["']([^"']+)""", body)
              if not urlsplit(s).netloc and
              urlsplit(s).path.endswith((".js", ".css", ".svg", ".ico", ".png"))}
    assets.update({"product-nav-icons.css", "account.js", "terminal_overlay.js", "nav_market.js",
                   "fonts/Inter-400.woff2", "fonts/Inter-500.woff2", "fonts/Inter-600.woff2",
                   "fonts/Inter-700.woff2", "fonts/Inter-800.woff2"})
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
        elif name in assets and ".." not in Path(name).parts:
            if name not in asset_cache:
                source = ROOT / "templates" / name
                asset_cache[name] = source.read_bytes() if source.is_file() else None
                if asset_cache[name] is None and (ROOT / "site" / name).is_file():
                    asset_cache[name] = (ROOT / "site" / name).read_bytes()
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



def _exact_browser_parent(name="complete", *, partial=False):
    from engine.sector_native_view import _measured_read
    if partial:
        from test_sector_native_view import _exact_owner_case
        packet = _exact_owner_case("absolute_percent_overflow")
    else:
        packet = json.loads((ROOT / "tests/fixtures/leadership_rotation" /
            f"sector_window_measurements.{name}.v1.json").read_text())
    read = json.loads(FIXTURE.read_text())
    read["generation"].update(session_end=packet["end_session"],cohort_id=packet["cohort_id"],
        price_basis=packet["price_basis"],benchmark=packet["benchmark"])
    read["sector_window_measurements"] = packet
    return _measured_read(read,packet["end_session"])


def _exact_journey(page, output, name, locale, theme, *, full_page=False):
    """Actual native projection -> shipped panel, with source retirement and responsive proof."""
    def publish(parent):
        page.evaluate("""read => {
            window.SECTOR_CENTRAL={as_of:'2026-11-05',measured_read:read};
            document.dispatchEvent(new Event('langchange'));
        }""",parent)
    publish(_exact_browser_parent())
    page.wait_for_selector('#mr-exact [data-exact-state="available"]')
    page.locator('#mr-exact .mr-xselect[data-g="XLK"]').click()
    page.wait_for_selector('#mr-exact [data-exact-selected="XLK"]')
    assert page.locator('#mr-exact [data-exact-window]').count()==3
    assert page.locator('#mr-exact tr[data-exact-group]').count()==11
    assert page.locator('#mr-exact [data-exact-benchmark]').count()==3
    assert page.locator('#mr-exact .mr-xselect').count()==11
    for kind in ("compare","source"):
        page.locator(f'#mr-exact details[data-exact-disclosure="{kind}"] > summary').click()
    summary=page.locator('#mr-exact details[data-exact-disclosure="source"] > summary')
    page.keyboard.press("Tab")
    summary.focus()
    facts=page.evaluate("""() => {
        const root=document.querySelector('#mr-exact'),sum=root.querySelector('[data-exact-disclosure="source"] > summary');
        const css=getComputedStyle(sum);
        return {root_overflow:root.scrollWidth-root.clientWidth,
          page_overflow:document.documentElement.scrollWidth-window.innerWidth,
          summary_height:sum.getBoundingClientRect().height,
          focus_visible:sum.matches(':focus-visible'),outline_width:css.outlineWidth,
          rows:[...root.querySelectorAll('tr[data-exact-group]')].map(el=>el.dataset.exactGroup),
          value_count:root.querySelectorAll('[data-exact-value]').length};
    }""")
    assert facts["root_overflow"] <=1 and facts["page_overflow"]<=1,facts
    assert facts["summary_height"]>=44 and facts["focus_visible"],facts
    assert float(facts["outline_width"].removesuffix("px"))>=2,facts
    shot=output/f"{name}-{locale}-{theme}--exact-complete.png"
    page.locator("#mr-exact").screenshot(path=str(shot))
    other="zh" if locale=="en" else "en"
    native_controls = None
    if full_page:
        page.locator("#settings-open").click()
        page.locator("#set-lang-slot .lang-toggle").click()
        page.wait_for_function("lang => document.documentElement.getAttribute('data-lang') === lang", arg=other)
        other_theme = "light" if theme == "dark" else "dark"
        page.locator("#set-theme-" + other_theme).click()
        page.wait_for_function("theme => document.documentElement.getAttribute('data-theme') === theme", arg=other_theme)
        assert page.locator('#mr-exact [data-exact-selected="XLK"]').count()==1
        assert page.locator('#mr-exact details[open]').count()==2
        native_controls = {"language": other, "theme": other_theme,
                           "selection_retained": True, "disclosures_retained": True}
        page.locator("#set-theme-" + theme).click()
        page.locator("#set-lang-slot .lang-toggle").click()
        page.wait_for_function("lang => document.documentElement.getAttribute('data-lang') === lang", arg=locale)
        page.wait_for_function("theme => document.documentElement.getAttribute('data-theme') === theme", arg=theme)
        page.keyboard.press("Escape")
        page.locator('#mr-exact details[data-exact-disclosure="source"] > summary').focus()
    else:
        page.evaluate("""lang => {
            document.documentElement.setAttribute('data-lang',lang);
            document.dispatchEvent(new Event('langchange'));
        }""",other)
        assert page.locator('#mr-exact [data-exact-selected="XLK"]').count()==1
        assert page.locator('#mr-exact details[open]').count()==2
        page.evaluate("""lang => {
            document.documentElement.setAttribute('data-lang',lang);
            document.dispatchEvent(new Event('langchange'));
        }""",locale)
    # Valid native evidence remains selectable alongside a legacy invalid-state notice.
    read=_exact_browser_parent()
    read["groups"]=None
    publish(read)
    page.locator('#mr-exact .mr-xselect[data-g="XLE"]').click()
    assert page.locator('#mr-exact [data-exact-selected="XLE"]').count()==1
    assert page.locator('#mr-body .mr-invalid').count()==1
    # A genuine absolute percentage overflow leaves a finite relative value.
    publish(_exact_browser_parent(partial=True))
    page.locator('#mr-exact .mr-xselect[data-g="XLB"]').click()
    selected=page.locator('#mr-exact [data-exact-window="5"]')
    assert selected.locator('[data-exact-value="absolute"]').inner_text()=="—"
    assert selected.locator('[data-exact-value="relative"]').inner_text()=="+9900.00%"
    assert "+1.00e+307%" in page.locator('#mr-exact [data-exact-benchmark="5"]').inner_text()
    assert page.locator("#mr-exact").evaluate("el=>el.scrollWidth-el.clientWidth")<=1
    partial_shot=output/f"{name}-{locale}-{theme}--exact-partial.png"
    page.locator("#mr-exact").screenshot(path=str(partial_shot))
    # A blocked source is still an admitted document with all native identities.
    publish(_exact_browser_parent("unavailable"))
    assert page.locator('#mr-exact [data-exact-state="unavailable"]').count()==1
    assert page.locator('#mr-exact tr[data-exact-group]').count()==11
    page.locator('#mr-exact details[data-exact-disclosure="compare"] > summary').click()
    absolute_values=page.locator('#mr-exact [data-exact-value="absolute"]').all_text_contents()
    assert [text.strip() for text in absolute_values]==["—"]*36,absolute_values
    # Withdrawal then navigation must not revive either data or open disclosures.
    page.evaluate("""() => {
        delete window.SECTOR_CENTRAL.measured_read.sector_window_measurements;
        document.dispatchEvent(new Event('langchange'));
        history.replaceState(null,'','?g=XLK#map');
        window.dispatchEvent(new PopStateEvent('popstate'));
    }""")
    assert page.locator("#mr-exact").is_hidden()
    assert page.locator("#mr-exact").inner_html()==""
    publish(_exact_browser_parent())
    assert page.locator('#mr-exact details[open]').count()==0
    page.evaluate("""() => {
        window.SECTOR_CENTRAL.measured_read.sector_window_measurements.authority.may_trade=true;
        document.dispatchEvent(new Event('langchange'));
        window.dispatchEvent(new PopStateEvent('popstate'));
    }""")
    assert page.locator('#mr-exact [data-exact-state="invalid"]').count()==1
    assert page.locator('#mr-exact [data-exact-value]').count()==0
    return {"native_projection":True,"selection":True,"all_eleven":True,
        "legacy_independence":True,"partial_overflow":True,"blocked_source":True,
        "withdrawal_no_revival":True,"revision_closes_disclosure":True,
        "same_source_language_continuity":True,"native_settings_controls":native_controls,"facts":facts,
        "screenshots":[shot.name,partial_shot.name]}


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
        exact_journey = _exact_journey(page, output, name, locale, theme, full_page=full_page)
        if errors and not any(p.startswith("page errors:") for p in problems):
            problems.append("page errors: " + " | ".join(errors))
        return {
            "exact_journey": exact_journey,
            "viewport": name, "width": width, "height": height,
            "locale": locale, "theme": theme,
            "screenshot": shot.name, "detail_screenshot": detail.name,
            "page_errors": errors, "console": console,
            "facts": facts, "journey": journey, "request_boundaries": requests,
            "problems": problems,
        }
    except (PWError, AssertionError) as exc:
        import traceback
        problems.append(f"{type(exc).__name__}: {exc}")
        problems.append(traceback.format_exc(limit=3))
        if errors:
            problems.append("page errors: " + " | ".join(errors))
        if console:
            problems.append("console: " + " | ".join(console))
        return {"viewport": name, "width": width, "height": height, "locale": locale,
                "theme": theme, "page_errors": errors, "console": console,
                "request_boundaries": requests, "problems": problems}
    finally:
        page.close()


def _run_native_wire(output: Path, generation_wire: Path, *, full_page: bool = False) -> dict:
    """HTTP-backed shipped panel over exact mounted-API qualification bytes.

    This does not substitute an injected global for the production transport.
    The browser makes the real same-origin fetch, consumes the response stream,
    and runs the shipped receipt/child admission. Auth events are controlled
    fixtures; authenticated production acceptance remains a separate receipt.
    """
    from playwright.sync_api import sync_playwright, Error as PWError
    from urllib.parse import urlsplit, parse_qs

    raw = generation_wire.read_bytes()
    packet = json.loads(raw)
    assert packet["schema"] == "sector_generation.read/v1" and packet["audience"] == "preview"
    receipt = packet["projection"]["receipt"]
    classification = packet["projection"]["data"]["core"].get("captured_classification")
    output.mkdir(parents=True, exist_ok=True)
    report = {"scope":("full_template_router_native_fetch_over_mounted_api_bytes" if full_page
                       else "shipped_panel_native_fetch_over_mounted_api_bytes"),
        "production_authenticated":False, "controlled_auth_events":True,
        "source_revision":_revision(), "page_sha256":hashlib.sha256(PAGE.read_bytes()).hexdigest(),
        "wire_sha256":hashlib.sha256(raw).hexdigest(), "wire_bytes":len(raw),
        "generation_id":receipt["generation_id"], "content_sha256":receipt["content_sha256"],
        "source_session":packet["source_session"], "cells":[]}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for name, width, height in (VIEWPORTS if not full_page else [VIEWPORTS[0], VIEWPORTS[3]]):
                if report.get('aborted_after_first_failure'):break
                for locale in LOCALES:
                    if report.get('aborted_after_first_failure'):break
                    for theme in THEMES:
                        if full_page and (locale, theme) != (
                                ("en", "dark") if name == "desktop" else ("zh", "light")):
                            continue
                        if report.get('aborted_after_first_failure'):break
                        page = browser.new_page(viewport={"width":width,"height":height})
                        errors, requests, problems, asset_requests = [], [], [], []
                        state = {"status":200}
                        cell = {"viewport":name,"width":width,"height":height,"locale":locale,
                                "theme":theme,"problems":problems,"page_errors":errors,"requests":requests,
                                "asset_requests":asset_requests}
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        html = _html(locale, theme, full_page=full_page, native_generation=True)
                        full_route = (_route(page, locale, theme, full_page=True,
                                             requests=asset_requests, native_generation=True)
                                      if full_page else None)

                        def handler(route):
                            url = urlsplit(route.request.url)
                            if url.netloc != "leadership-evidence.test" or url.scheme != "http":
                                route.abort();return
                            if url.path == "/sector_central.html":
                                route.fulfill(status=200, content_type="text/html; charset=utf-8", body=html)
                            elif url.path == "/api/sector-generation":
                                requests.append({"method":route.request.method,"query":url.query,
                                                 "status":state["status"]})
                                assert parse_qs(url.query)=={"audience":["preview"]}
                                route.fulfill(status=state["status"],content_type="application/json; charset=utf-8",
                                    headers={"Cache-Control":"private, no-store","Vary":"Cookie"},
                                    body=raw if state["status"]==200 else b'{"detail":"unauthorized"}')
                            elif full_route is not None:
                                full_route(route)
                            else:
                                route.fulfill(status=404,body="")

                        try:
                            page.add_init_script("localStorage.setItem('lang',"+json.dumps(locale)+
                                ");localStorage.setItem('theme',"+json.dumps(theme)+");")
                            page.route("**/*",handler)
                            page.goto("http://leadership-evidence.test/sector_central.html?g=XLE#map",wait_until="load")
                            if full_page:
                                page.wait_for_selector('.si-view[data-view="map"].on')
                                assert page.locator('#si-measured').is_visible()
                            page.wait_for_selector('#si-measured[data-native-state="ready"]')
                            assert page.locator('#mr-list .mr-row').count()==11
                            page.locator('#mr-list .mr-row[data-g="XLK"]').click()
                            page.wait_for_selector('#mr-list .mr-row[data-g="XLK"][aria-pressed="true"]')
                            assert page.locator('#mr-exact [data-exact-selected="XLK"]').count()==1
                            assert page.locator('#mr-exact [data-exact-window]').count()==3
                            assert page.locator('#mr-exact [data-exact-group]').count()==11
                            assert page.locator('#mr-detail [data-ev-state="ok"]').count()==1
                            assert page.locator('#mr-context [data-dated-state="ok"]').count()==1
                            assert page.locator('#mr-context [data-dated-alternative]').count()==4
                            assert page.locator('#si-measured').get_attribute('data-native-generation')==receipt['generation_id']
                            assert page.locator('#si-measured').get_attribute('data-native-content')==receipt['content_sha256']
                            assert "1900-01-01" not in page.locator('#si-measured').inner_text()
                            summary=page.locator('#mr-context details > summary')
                            summary.click();page.keyboard.press('Tab');summary.focus()
                            facts=page.evaluate("""() => {
                              const root=document.querySelector('#mr-context'),sum=root.querySelector('details > summary');
                              return {page_overflow:document.documentElement.scrollWidth-innerWidth,
                                context_overflow:root.scrollWidth-root.clientWidth,
                                summary_height:sum.getBoundingClientRect().height,
                                focus_visible:sum.matches(':focus-visible'),outline_width:getComputedStyle(sum).outlineWidth,
                                history_points_visible:!!document.querySelector('#mr-hist svg'),
                                selected:document.querySelector('#mr-list [aria-pressed="true"]').dataset.g};
                            }""")
                            assert facts['page_overflow']<=1 and facts['context_overflow']<=1,facts
                            assert facts['summary_height']>=44 and facts['focus_visible'],facts
                            assert float(facts['outline_width'].removesuffix('px'))>=2,facts
                            shot=output/f'{name}-{locale}-{theme}--native-context.png'
                            page.locator('#mr-context').screenshot(path=str(shot))
                            cell.update(facts=facts,screenshot=shot.name)
                            if classification is not None:
                                cl = page.locator('#mr-classification')
                                assert cl.locator('[data-classification-state="ok"]').count() == 1
                                assert cl.locator('[data-classification-member]').count() == len(classification['configured_roster'])
                                cl_summary = cl.locator('details > summary')
                                cl_summary.click();page.keyboard.press('Tab');cl_summary.focus()
                                cl_facts = page.evaluate("""() => {
                                  const root=document.querySelector('#mr-classification'),sum=root.querySelector('summary');
                                  return {overflow:root.scrollWidth-root.clientWidth,
                                    page_overflow:document.documentElement.scrollWidth-innerWidth,
                                    summary_height:sum.getBoundingClientRect().height,
                                    focus_visible:sum.matches(':focus-visible'),outline_width:getComputedStyle(sum).outlineWidth};
                                }""")
                                assert cl_facts['overflow']<=1 and cl_facts['page_overflow']<=1,cl_facts
                                assert cl_facts['summary_height']>=44 and cl_facts['focus_visible'],cl_facts
                                assert float(cl_facts['outline_width'].removesuffix('px'))>=2,cl_facts
                                cl_shot=output/f'{name}-{locale}-{theme}--native-classification.png'
                                cl.screenshot(path=str(cl_shot))
                                cell['classification']={"facts":cl_facts,"screenshot":cl_shot.name,
                                    "screenshot_sha256":hashlib.sha256(cl_shot.read_bytes()).hexdigest(),
                                    "status":classification['status'],
                                    "configured_n":len(classification['configured_roster']),
                                    "missing_n":len(classification['missing_roster'])}
                            expected_radii = {'.mr-exact': '12px', '.mr-xselect': '8px',
                                              '.mr-xwindow': '8px'}
                            if classification is not None:
                                expected_radii['.mr-cl-members li'] = '8px'
                            radii = page.evaluate("""selectors => Object.fromEntries(selectors.map(
                              selector => [selector, [...document.querySelectorAll(selector)].map(
                                el => getComputedStyle(el).borderTopLeftRadius)]))""",
                                list(expected_radii))
                            for selector, expected in expected_radii.items():
                                assert radii[selector] and all(value == expected for value in radii[selector]), (
                                    selector, radii[selector], expected)
                            cell['computed_radii'] = radii
                            if full_page:
                                whole = output/f'{name}-{locale}-{theme}--native-whole-page.png'
                                page.screenshot(path=str(whole), full_page=True)
                                cell["full_template_screenshot"] = whole.name
                                cell["full_template_screenshot_sha256"] = hashlib.sha256(
                                    whole.read_bytes()).hexdigest()
                            other='zh' if locale=='en' else 'en'
                            if full_page:
                                page.locator("#settings-open").click()
                                page.locator("#set-lang-slot .lang-toggle").click()
                                page.wait_for_function(
                                    "lang => document.documentElement.getAttribute('data-lang') === lang",
                                    arg=other)
                                # The incumbent desktop popup dismisses on
                                # pointer leave, including a localized nav reflow.
                                # Make two explicit settings visits; never force
                                # a click through a closed/intercepted popup.
                                page.keyboard.press("Escape")
                                page.locator("#settings-open").click()
                                other_theme = "light" if theme == "dark" else "dark"
                                page.locator("#set-theme-" + other_theme).click()
                                page.wait_for_function(
                                    "theme => document.documentElement.getAttribute('data-theme') === theme",
                                    arg=other_theme)
                                page.keyboard.press("Escape")
                            else:
                                page.evaluate("""lang => {document.documentElement.setAttribute('data-lang',lang);
                                    document.dispatchEvent(new Event('langchange'));}""",other)
                            assert page.locator('#mr-list [data-g="XLK"][aria-pressed="true"]').count()==1
                            assert page.locator('#mr-context details[open]').count()==1
                            if classification is not None:
                                assert page.locator('#mr-classification details[open]').count()==1
                            assert len(requests)==1
                            if full_page:
                                page.locator('.si-view-btn[data-view="overview"]').click()
                                page.wait_for_selector('.si-view[data-view="overview"].on')
                                page.go_back()
                                page.wait_for_selector('.si-view[data-view="map"].on')
                                assert page.locator('#mr-list [data-g="XLK"][aria-pressed="true"]').count()==1
                                assert page.locator('#mr-context details[open]').count()==1
                                if classification is not None:
                                    assert page.locator('#mr-classification details[open]').count()==1
                                assert len(requests)==1
                            page.evaluate("window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{event:'SIGNED_OUT',user:null}}))")
                            page.wait_for_selector('#si-measured[data-native-state="unauthorized"]')
                            assert page.locator('#mr-list .mr-row').count()==0
                            assert page.locator('#mr-context [data-dated-alternative]').count()==0
                            assert page.locator('#mr-classification [data-classification-member]').count()==0
                            assert page.locator('#mr-exact [data-exact-value]').count()==0
                            page.locator('[data-native-retry]').click()
                            assert len(requests)==1  # Known signout cannot reuse cookies.
                            state['status']=401
                            page.evaluate("window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{event:'SIGNED_IN',user:{id:'controlled-account'}}}))")
                            page.wait_for_function("document.querySelector('#si-measured').dataset.nativeState==='unauthorized'")
                            assert len(requests)==2
                            assert page.locator('#mr-list .mr-row').count()==0
                            cell['journey']={"native_fetch":True,"one_receipt":True,"all_eleven":True,
                                "selection":True,"language_no_refetch":True,"signout_withdrawal":True,
                                "known_signout_retry_blocked":True,"http_401_withdrawal":True,
                                "full_template_router":full_page,"native_settings_controls":full_page,
                                "settings_visits_separate":full_page,
                                "classification_capture_displayed":classification is not None,
                                "browser_back_preserves_selection":full_page}
                            assert not errors,errors
                        except (PWError,AssertionError) as error:
                            problems.append(f'{type(error).__name__}: {error}')
                            failed = output/f'{name}-{locale}-{theme}--failure.png'
                            page.screenshot(path=str(failed), full_page=True)
                            cell["failure_screenshot"] = failed.name
                        finally:
                            page.close()
                        report['cells'].append(cell)
                        if problems:report['aborted_after_first_failure']=True
        finally:
            browser.close()
    report['problem_count']=sum(bool(cell['problems']) for cell in report['cells'])
    report['outcome']='captured' if not report['problem_count'] else 'problems_found'
    (output/'receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=1)+'\n')
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default="/tmp/psl4-leadership-evidence")
    ap.add_argument("--full-page", action="store_true",
                    help="exercise the full native template/router at desktop EN and phone ZH")
    ap.add_argument("--generation-wire", type=Path,
                    help="exercise native fetch using exact mounted-API response bytes from qualification")
    args = ap.parse_args(argv)
    report = run(Path(args.output), full_page=args.full_page, generation_wire=args.generation_wire)
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
