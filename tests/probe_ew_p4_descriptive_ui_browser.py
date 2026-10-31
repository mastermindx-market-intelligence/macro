"""Isolated browser probe for the EW-P4.T1 descriptive observation UI; NOT a CI
test and NOT authenticated production acceptance.

Run: python3 tests/probe_ew_p4_descriptive_ui_browser.py --output research/evidence/ew_p4_descriptive_ui_20261031

Every request is fulfilled locally from committed sources and fixtures, or
aborted and recorded. No credentials, collectors or sends. Two harnesses:

  Radar — the envelope band rendered through the real dashboard template helpers
          (tests.test_macro_risk_dialog._vm/_render/_dlg), wrapped with
          templates/theme.css + the band CSS exactly as dashboard.html.j2
          includes them, under <html data-theme data-lang>.
  SC    — the production templates/rotation_events.js on a page with a stubbed
          fetch serving the fixture wrapper through early_context.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.test_macro_risk_dialog import _dlg, _render, _vm  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "ew_p4_observation"
BASE = "1d253e1d25f22c61d1bcf8126b13b0229f26ccbd"
SESSION = "2026-10-30"
CLOCK = "2026-10-31T12:00:00Z"
ORIGIN = "ew-p4-descriptive.test"

RADAR_STATES = ("partial", "conflicting", "unavailable", "withdrawn", "corrected", "unreadable")
STATE_FIXTURE = {
    "partial": "partial_window_mismatch", "conflicting": "conflict_20s",
    "unavailable": None, "withdrawn": "withdrawn", "corrected": "corrected",
    "unreadable": "malformed_ratio",
}
# P4: Sector Central state shots (390/en/dark). "stale" has no latest_observation
# and an early_context 10 sessions older than the rotation_events as_of.
SC_STATES = ("stale", "withdrawn", "corrected", "unreadable")
SC_STALE_AS_OF = "2026-10-20"
SC_STATE_FIXTURE = {"stale": None, "withdrawn": "withdrawn", "corrected": "corrected",
                    "unreadable": "malformed_ratio"}


def fixture(name: str) -> dict:
    return json.loads((FIX / f"{name}.json").read_text(encoding="utf-8"))


def envelope(wrapper: dict | None) -> dict:
    env = deepcopy(fixture("journey_c_envelope_1d253e1d"))
    env["source_session"] = SESSION
    env["as_of"] = SESSION
    rc = deepcopy(env["rotation_context"])
    rc.update({"coverage": "FRESH", "as_of": SESSION, "usable": True})
    if wrapper is not None:
        rc["latest_observation"] = deepcopy(wrapper)
    env["rotation_context"] = rc
    return env


@lru_cache(maxsize=1)
def _dashboard_styles() -> str:
    """Every inline <style> block of the real dashboard render, so the harness
    page styles the dialog exactly as the shipped page does (responsive rules
    included). The band CSS rides along inside these blocks, matching how
    dashboard.html.j2 includes it."""
    html = _render(_vm())
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S))


def _dlg_element(html: str) -> str:
    """The whole #dlg-risk element, opening tag included. tests' _dlg slices
    from the id attribute (fine for string asserts, malformed as markup), so
    back up to the real opening <div> for the browser harness."""
    i = html.index('id="dlg-risk"')
    start = html.rfind("<div", 0, i)
    rest = html[start:]
    j = rest.find('id="dlg-policy"')
    if j > 0:
        end = rest.rfind("<div", 0, j)
        rest = rest[: end if end > 0 else j]
    return rest


def radar_html(env: dict, lang: str, theme: str) -> str:
    theme_css = (ROOT / "templates" / "theme.css").read_text(encoding="utf-8")
    dlg = _dlg_element(_render(_vm(risk_envelope=env)))
    # The real dialog is display:none until JS opens it (mx5-dlg.open). Show it
    # in normal flow so the harness screenshots the dialog content without the
    # fixed overlay geometry; the backdrop click-catcher is hidden with it.
    # P1: also remove the dialog's own max-height/overflow clip so the WHOLE band
    # (undo, Study disclosure, policy footer included) lands in the screenshot.
    # Static harness only — the live dialog keeps its scroll geometry.
    harness_css = ("#dlg-risk{display:block!important;position:static!important;}"
                   ".mx5-dlg-backdrop{display:none!important}"
                   "#dlg-risk,#dlg-risk *{max-height:none!important}"
                   '#dlg-risk,#dlg-risk .mx5-dlg-body,#dlg-risk [class*="body"],#dlg-risk [class*="scroll"]'
                   "{overflow:visible!important;height:auto!important}")
    return (f'<!doctype html><html lang="{lang}" data-lang="{lang}" data-theme="{theme}">'
            '<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<style>{theme_css}</style>"
            f"<style>{_dashboard_styles()}</style>"
            f"<style>{harness_css}</style></head>"
            f'<body class="page-macro" style="padding:16px">{dlg}</body></html>')


def _sc_pair(wrapper: dict) -> dict | None:
    """P3: one defensive_sector pair row that AGREES with a validated observation —
    same num/den, same 2-session window, same three values — in the exact object
    shape earlyContextHtml() reads (copied from the passing fixtures R()/W() in
    tests/rotation_early_context_ui.test.cjs; no invented keys). Returns None when
    the wrapper is not a qualified comparison (withdrawal, unreadable values,
    mismatched window): those states legitimately have no registered pair."""
    n = wrapper.get("notification") or {}
    if n.get("kind") not in ("observed_change", "reversal", "correction"):
        return None
    vals, win = n.get("values") or {}, wrapper.get("window_2s") or {}
    try:
        num = float(vals["numerator_return_pct"])
        den = float(vals["denominator_return_pct"])
        rel = float(vals["ratio_return_pct"])
        start, end = str(win["start"]), str(win["end"])
        sessions = vals["sessions"]
    except (KeyError, TypeError, ValueError):
        return None
    if not isinstance(sessions, int) or isinstance(sessions, bool) or sessions != 2 or end != SESSION:
        return None
    if abs(((1 + num / 100) / (1 + den / 100) - 1) * 100 - rel) > 1e-6:
        return None  # e.g. malformed_ratio: an unreadable record is not registered evidence
    return {
        "schema": "ratio_lens.short_horizon.v1", "pair_id": n.get("pair_id"),
        "context_group": "defensive_sector", "num": n.get("num"), "den": n.get("den"),
        "name_en": "Staples / technology", "name_zh": "必需消费 / 科技",
        "requested_as_of": SESSION, "value_as_of": SESSION, "eligible_2s": True,
        "interpretation": "UNTRUSTED",
        "absolute_2s": {"receiver_state": "UP" if num > 0 else "DOWN",
                        "donor_state": "UP" if den > 0 else "DOWN"},
        "reason_codes": [],
        "horizons": {"2s": {"eligible": True, "sessions": 2, "start": start, "end": end,
                            "numerator_return_pct": num, "denominator_return_pct": den,
                            "ratio_return_pct": rel, "reason_codes": [], "shape": "UNTRUSTED"}},
        "lineage": {"status": "COMPLETE", "roots": ["marketdata/rotation_events.json@1d253e1d"]},
    }


def sc_payload(wrapper: dict | None, early_as_of: str = SESSION) -> bytes:
    """P3: the early_context card agrees with the observation it sits under — a
    qualified observation comes with its registered defensive comparison and a
    VERIFIED availability, instead of 'No registered defensive comparisons'
    UNKNOWN next to a qualified record."""
    av = (wrapper or {}).get("availability") or {}
    if av.get("status") == "VERIFIED":
        early_av = {"status": "VERIFIED",
                    "available_at": av.get("available_at")
                    or (wrapper.get("notification") or {}).get("observed_at")}
    else:
        early_av = {"status": "UNKNOWN", "available_at": None}
    pair = _sc_pair(wrapper) if wrapper is not None else None
    early = {
        "schema": "rotation_early_context/v1", "definition_id": "rotation_early_context/1",
        "display_only": True, "as_of": early_as_of, "state": None,
        "pairs": [pair] if pair else [],
        "reason_codes": [], "availability": early_av,
        "lineage": {"status": "UNKNOWN", "roots": [], "revisions": {}, "dependency_groups": ["equity_price"]},
        "latest_observation": deepcopy(wrapper),
    }
    return json.dumps({"schema": "rotation_events/v2", "as_of": SESSION, "active": [],
                       "early_context": early}).encode("utf-8")


def sc_html(lang: str, theme: str) -> str:
    theme_css = (ROOT / "templates" / "theme.css").read_text(encoding="utf-8")
    return (f'<!doctype html><html lang="{lang}" data-lang="{lang}" data-theme="{theme}">'
            '<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<style>{theme_css}</style></head>"
            '<body style="padding:16px"><main style="max-width:1080px;margin:auto">'
            '<p style="font-size:12px">Component QA · synthetic fixture · not a live market signal</p>'
            '<div id="rc-events-mount"></div></main>'
            '<script src="/rotation_events.js"></script></body></html>')


def contact_sheet(out: Path, name: str, pngs: list[str], title: str) -> str:
    cells = "".join(
        f'<figure><img src="/shots/{p}"><figcaption>{p}</figcaption></figure>' for p in pngs)
    html = ('<!doctype html><html><head><meta charset="utf-8"><style>'
            "body{margin:0;padding:12px;font:12px Arial,sans-serif;background:#e8ecf2}"
            "h1{font-size:15px}"
            ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px}"
            "figure{margin:0;background:#fff;padding:6px;border:1px solid #c6cedb}"
            "img{width:100%;height:auto;display:block;border:1px solid #d8dfe8}"
            "figcaption{font-size:10px;color:#556;margin-top:4px;word-break:break-all}"
            "</style></head><body>"
            f"<h1>{title}</h1><div class='grid'>{cells}</div></body></html>")
    (out / name).write_text(html, encoding="utf-8")
    return name


def tab_to(page, selector: str) -> dict:
    """Real keyboard Tab navigation to the study summary, then Enter to open it."""
    for _ in range(40):
        if page.evaluate("() => { const a = document.activeElement; return a && a.matches(%s); }" % json.dumps(selector)):
            break
        page.keyboard.press("Tab")
    else:
        return {"reached": False}
    outline = page.evaluate(
        "() => getComputedStyle(document.activeElement).outlineStyle")
    page.keyboard.press("Enter")
    opened = page.evaluate(
        "() => { const s = document.activeElement; return !!(s && s.parentElement && s.parentElement.hasAttribute('open')); }")
    return {"reached": True, "outline_style": outline, "opened_by_enter": opened,
            "focus_outline": outline != "none"}


def assert_band_unclipped(page, label: str) -> None:
    """P1: fail the case loudly if the band (or its nearest clipping ancestor)
    still hides any of its content — scrollHeight must fit inside clientHeight."""
    info = page.evaluate(
        """() => {
            const el = document.querySelector('#risk-envelope-band');
            if (!el) return {missing: true, clipped: []};
            const clipped = [];
            if (el.scrollHeight > el.clientHeight + 1)
                clipped.push('#risk-envelope-band ' + el.scrollHeight + '>' + el.clientHeight);
            let a = el.parentElement;
            while (a && a !== document.documentElement) {
                if (getComputedStyle(a).overflowY !== 'visible') {
                    if (a.scrollHeight > a.clientHeight + 1)
                        clipped.push((a.id ? '#' + a.id : String(a.className)) + ' ' + a.scrollHeight + '>' + a.clientHeight);
                    break;
                }
                a = a.parentElement;
            }
            return {missing: false, clipped};
        }""")
    assert info is not None and not info.get("missing"), f"{label}: #risk-envelope-band missing"
    assert not info["clipped"], f"{label}: band clipped by scroll geometry: {info['clipped']}"


def open_radar_disclosures(page) -> None:
    """P2: open every disclosure that holds evidence — the brief AND the study."""
    page.evaluate("() => document.querySelector('details.gde-disc').setAttribute('open','')")
    page.evaluate("() => { const d = document.querySelector('details.gde-ew-study'); if (d) d.setAttribute('open',''); }")


def run(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    shots = output / "shots"
    shots.mkdir(exist_ok=True)
    band_tmpl = (ROOT / "templates" / "_risk_envelope_band.html.j2").read_bytes()
    rc_js = (ROOT / "templates" / "rotation_events.js").read_bytes()
    source_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    fixtures_sha = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(FIX.glob("*.json"))}
    report = {
        "scope": "EW-P4.T1 descriptive early-warning observation UI (consumer-only), two hosts, synthetic fixtures",
        "production_authenticated": False,
        "source_revision": source_revision,
        "base": BASE,
        "capture_mode": "dialog_unclipped_static_harness",
        "capture_mode_note": "#dlg-risk rendered in normal flow with its max-height/overflow removed so the whole band is captured; live dialog scrolls",
        "script_sha256": hashlib.sha256(rc_js).hexdigest(),
        "band_template_sha256": hashlib.sha256(band_tmpl).hexdigest(),
        "fixtures": fixtures_sha,
        "cases": [], "blocked_requests": [],
    }
    journey_b = fixture("journey_b_both_fell")
    journey_c_env = fixture("journey_c_envelope_1d253e1d")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            # ── matrix: 3 case-families × lang × theme × width = 36 shots ──
            families = [
                ("radar", "stale", lambda lang, theme: radar_html(journey_c_env, lang, theme)),
                ("radar", "observed", lambda lang, theme: radar_html(envelope(journey_b), lang, theme)),
                ("sc", "observed", sc_html),
            ]
            keyboard_done: dict[tuple, dict] = {}
            for surface, state, pagefn in families:
                for lang in ("en", "zh"):
                    for theme in ("dark", "light"):
                        for width in (1280, 390, 320):
                            page = browser.new_page(viewport={"width": width, "height": 1000})
                            errors: list[str] = []
                            page.on("pageerror", lambda e: errors.append(str(e)))
                            page.add_init_script(f"Date.now = () => Date.parse('{CLOCK}');")
                            html = pagefn(lang, theme)
                            content = {
                                "/": ("text/html", html.encode("utf-8")),
                                "/rotation_events.js": ("text/javascript", rc_js),
                                "/theme.css": ("text/css", b"/* inlined */"),
                                "/marketdata/rotation_events.json": ("application/json", sc_payload(journey_b)),
                                "/marketdata/sector_fragmentation.json": ("application/json", b"{}"),
                            }

                            def route(r):
                                u = urlparse(r.request.url)
                                if u.hostname == ORIGIN and u.path in content:
                                    typ, body = content[u.path]
                                    r.fulfill(status=200, content_type=typ, body=body)
                                else:
                                    report["blocked_requests"].append(r.request.url)
                                    r.abort()

                            page.route("**/*", route)
                            page.goto(f"http://{ORIGIN}/", wait_until="networkidle")
                            if surface == "radar":
                                el = page.locator("#risk-envelope-band")
                                el.wait_for()
                                open_radar_disclosures(page)  # P2: every radar case, stale included
                                assert_band_unclipped(page, f"{surface}/{state}/{lang}/{theme}/{width}")
                                target = el
                            else:
                                page.wait_for_function(
                                    "() => { const e = document.querySelector('#rc-ew');"
                                    " return e && e.getAttribute('data-ew-state') !== 'loading'; }")
                                page.evaluate("() => { const d = document.querySelector('details.rc-ew-study'); if (d) d.setAttribute('open',''); }")  # P2
                                if state == "observed":
                                    # P3: a qualified observation must not sit over an
                                    # "empty early context" contradiction, and its registered
                                    # comparison row must actually render.
                                    ec_text = page.locator("#rc-early-context").text_content() or ""
                                    assert "No registered defensive comparisons" not in ec_text, \
                                        f"sc observed {lang}/{theme}/{width}: early context contradicts the observation"
                                    assert "XLP / XLK" in ec_text and "ROW_" not in ec_text, \
                                        f"sc observed {lang}/{theme}/{width}: registered pair row did not render: {ec_text[:400]}"
                                target = page.locator("#rc-events")
                            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), \
                                f"horizontal overflow {surface}/{lang}/{theme}/{width}"
                            name = f"{surface}-{state}-{lang}-{theme}-{width}.png"
                            target.screenshot(path=str(shots / name))
                            kb = None
                            if width in (320, 390, 1280) and (surface, width) not in keyboard_done:
                                if surface == "radar":
                                    # close the study first so Enter demonstrably opens it
                                    page.evaluate("() => { const d = document.querySelector('details.gde-ew-study'); if (d) d.removeAttribute('open'); }")
                                    kb = tab_to(page, "details.gde-ew-study > summary")
                                else:
                                    page.evaluate("() => { const d = document.querySelector('details.rc-ew-study'); if (d) d.removeAttribute('open'); }")
                                    kb = tab_to(page, ".rc-ew-study > summary")
                                if kb.get("reached"):
                                    keyboard_done[(surface, width)] = kb
                            report["cases"].append({
                                "surface": surface, "state": state, "lang": lang, "theme": theme,
                                "width": width, "screenshot": f"shots/{name}",
                                "sha256": hashlib.sha256((shots / name).read_bytes()).hexdigest(),
                                "no_horizontal_overflow": True, "page_errors": errors,
                                "keyboard_details": (keyboard_done.get((surface, width)) if kb else None),
                                "focus_outline": bool(kb and kb.get("focus_outline")) if kb else None,
                            })
                            assert not errors, errors
                            page.close()

            # ── six extra Radar states at 390/en/dark = 6 shots ──
            for state in RADAR_STATES:
                wrapper_name = STATE_FIXTURE[state]
                env = envelope(fixture(wrapper_name) if wrapper_name else None)
                page = browser.new_page(viewport={"width": 390, "height": 1000})
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.add_init_script(f"Date.now = () => Date.parse('{CLOCK}');")
                html_bytes = radar_html(env, "en", "dark").encode("utf-8")

                def route2(r, _request=None, *, body=html_bytes):
                    u = urlparse(r.request.url)
                    if u.hostname == ORIGIN and u.path == "/":
                        r.fulfill(status=200, content_type="text/html", body=body)
                    else:
                        report["blocked_requests"].append(r.request.url)
                        r.abort()

                page.route("**/*", route2)
                page.goto(f"http://{ORIGIN}/", wait_until="networkidle")
                el = page.locator("#risk-envelope-band")
                el.wait_for()
                rendered_state = page.get_attribute("#gde-ew", "data-ew-state")
                assert rendered_state == state, f"{state}: rendered {rendered_state}"
                open_radar_disclosures(page)  # P2: state shots carry their Study rows too
                assert_band_unclipped(page, f"radar/{state}/en/dark/390")
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                name = f"radar-{state}-en-dark-390.png"
                el.screenshot(path=str(shots / name))
                report["cases"].append({
                    "surface": "radar", "state": state, "lang": "en", "theme": "dark", "width": 390,
                    "screenshot": f"shots/{name}",
                    "sha256": hashlib.sha256((shots / name).read_bytes()).hexdigest(),
                    "no_horizontal_overflow": True, "page_errors": errors,
                    "keyboard_details": None, "focus_outline": None,
                })
                assert not errors, errors
                page.close()

            # ── P4: four Sector Central states at 390/en/dark = 4 shots ──
            for state in SC_STATES:
                wrapper_name = SC_STATE_FIXTURE[state]
                payload = (sc_payload(None, early_as_of=SC_STALE_AS_OF) if wrapper_name is None
                           else sc_payload(fixture(wrapper_name)))
                page = browser.new_page(viewport={"width": 390, "height": 1000})
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.add_init_script(f"Date.now = () => Date.parse('{CLOCK}');")
                content = {
                    "/": ("text/html", sc_html("en", "dark").encode("utf-8")),
                    "/rotation_events.js": ("text/javascript", rc_js),
                    "/theme.css": ("text/css", b"/* inlined */"),
                    "/marketdata/rotation_events.json": ("application/json", payload),
                    "/marketdata/sector_fragmentation.json": ("application/json", b"{}"),
                }

                def route4(r):
                    u = urlparse(r.request.url)
                    if u.hostname == ORIGIN and u.path in content:
                        typ, body = content[u.path]
                        r.fulfill(status=200, content_type=typ, body=body)
                    else:
                        report["blocked_requests"].append(r.request.url)
                        r.abort()

                page.route("**/*", route4)
                page.goto(f"http://{ORIGIN}/", wait_until="networkidle")
                page.wait_for_function(
                    "() => { const e = document.querySelector('#rc-ew');"
                    " return e && e.getAttribute('data-ew-state') !== 'loading'; }")
                rendered_state = page.get_attribute("#rc-ew", "data-ew-state")
                assert rendered_state == state, f"sc {state}: rendered {rendered_state}"
                page.evaluate("() => { const d = document.querySelector('details.rc-ew-study'); if (d) d.setAttribute('open',''); }")  # P2
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                name = f"sc-{state}-en-dark-390.png"
                page.locator("#rc-events").screenshot(path=str(shots / name))
                report["cases"].append({
                    "surface": "sc", "state": state, "lang": "en", "theme": "dark", "width": 390,
                    "screenshot": f"shots/{name}",
                    "sha256": hashlib.sha256((shots / name).read_bytes()).hexdigest(),
                    "no_horizontal_overflow": True, "page_errors": errors,
                    "keyboard_details": None, "focus_outline": None,
                })
                assert not errors, errors
                page.close()

            # ── 3 matrix contact sheets + 1 Sector Central state sheet ──
            sheets = {}
            for surface, state, _p in families:
                pngs = sorted(x.name for x in shots.iterdir()
                              if x.name.startswith(f"{surface}-{state}-") and x.suffix == ".png")
                sheets[f"{surface}-{state}"] = contact_sheet(
                    output, f"contact-{surface}-{state}.html", pngs,
                    f"EW-P4 {surface} / {state} — {len(pngs)} shots (en+zh × dark+light × 1280/390/320)")
            sc_pngs = [f"sc-{s}-en-dark-390.png" for s in SC_STATES]
            sheets["sc-states"] = contact_sheet(
                output, "contact-sc-states.html", sc_pngs,
                f"EW-P4 sc states — {len(sc_pngs)} shots (stale/withdrawn/corrected/unreadable · en/dark/390)")
            report["contact_sheets"] = sheets
            # screenshot each contact sheet for reviewers who only read PNGs
            for sheet_name in sheets.values():
                page = browser.new_page(viewport={"width": 1280, "height": 1000})
                pngs_glob = sorted(x.name for x in shots.iterdir() if x.suffix == ".png")
                content = {"/": (output / sheet_name).read_bytes(),
                           **{f"/shots/{n}": (shots / n).read_bytes() for n in pngs_glob}}

                def route3(r):
                    u = urlparse(r.request.url)
                    if u.hostname == ORIGIN and u.path in content:
                        r.fulfill(status=200, content_type="image/png" if u.path.endswith(".png") else "text/html",
                                  body=content[u.path])
                    else:
                        report["blocked_requests"].append(r.request.url)
                        r.abort()

                page.route("**/*", route3)
                page.goto(f"http://{ORIGIN}/", wait_until="networkidle")
                png = sheet_name.replace(".html", ".png")
                page.screenshot(path=str(output / png), full_page=True)
                page.close()
        finally:
            browser.close()
    (output / "receipt.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="research/evidence/ew_p4_descriptive_ui_20261031")
    args = ap.parse_args()
    report = run(Path(args.output))
    print(f"{len(report['cases'])} shots -> {args.output}")
    print(f"keyboard cases: {[ (k, v) for k, v in [(c['surface'] + '@' + str(c['width']), c['keyboard_details']) for c in report['cases'] if c['keyboard_details']] ]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
