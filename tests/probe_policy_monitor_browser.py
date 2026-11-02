#!/usr/bin/env python3
"""Policy Monitor browser probe — real template render, real browser.

Renders templates/dashboard.html.j2 through the same Jinja environment
scripts/build_site.py uses, with the REAL payloads (site/policy_lever.json and
data/regime/latest.json), serves the rendered page from a local HTTP server and
drives Chromium through the shared mx5OpenDlg controller to capture the Policy
Monitor card face and the open dialog.

Matrices captured (per the frozen packet):
    theme (dark / light) x language (en / zh) x viewport (1440 / 390)
plus the populated / partial / missing data states.

This is NOT a stand-alone mockup: the page is the production template rendered
with production payloads, and the dialog is opened through the page's own
controller.

Usage:
    python3 tests/probe_policy_monitor_browser.py --out research/evidence/<dir>

It is a probe, not a pytest module (the `probe_` prefix keeps it out of
collection, matching tests/probe_ew_p4_descriptive_ui_browser.py).
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import shutil
import socket
import socketserver
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import jinja2  # noqa: E402

from engine import i18n  # noqa: E402
from lib import policy_monitor_view as pmv  # noqa: E402

THEMES = ("dark", "light")
LANGS = ("en", "zh")
SIZES = ((1440, 1000), (390, 844))


# --------------------------------------------------------------------------- #
# render
# --------------------------------------------------------------------------- #

def _env() -> jinja2.Environment:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")),
                             autoescape=True)
    env.filters["min"] = lambda seq: min(seq)
    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    env.globals["pm_view"] = pmv.build_view
    return env


def _vm(policy_lever, latest) -> dict:
    return dict(
        latest=latest,
        mtf=None, macro_catalysts=[], event_strip=[], event_risk=None,
        prediction_markets=None, narrative_regime=None, ndi=None,
        macro_news=None, macro_brief=None, macro_news_disclaimer="",
        macro_news_disclaimer_zh="", alerts=[], pb=None, month_name="October",
        commodities=[], sector_timing={},
        action_board={"hold": [], "avoid": [], "notable": [], "buy": []},
        top_setups=[], us_standouts={"buy": [], "eligible": 0},
        us_board_outcomes=None, market_gamma=None,
        components_confirming=[], components_contradicting=[],
        flip_plain=None, internals=[], size_style=[], breadth_div=None,
        breadth_panel=None, adv_breadth=None, sector_setups=None,
        generated_utc="2026-10-30 06:00", chart_liquidity=None,
        chart_credit_breadth=None, market_tiles=[], vix=None, chart_vix=None,
        positioning=[], holdings_changes=[], holdings_threshold=5.0,
        accumulation=[], flows_html="", health=[], factor_leadership=None,
        nowcast_hist=None, stance=None, index_health=[], alloc_card=None,
        risk_model=None, chart_risk_model=None, chart_curve=None,
        chart_vix_term=None, cross_asset=None, fear_euphoria=None,
        regime_snap=None, market_state=None, signal_stack=None,
        vol_shock=None, froth_fragility=None, fear_greed=None,
        sector_heat=None, dispersion_regime=None,
        policy_lever=policy_lever,
    )


def _real_payloads() -> tuple[dict, dict]:
    pl = json.loads((ROOT / "site" / "policy_lever.json").read_text(encoding="utf-8"))
    lt = json.loads((ROOT / "data" / "regime" / "latest.json").read_text(encoding="utf-8"))
    return pl, lt


def _partial_payloads() -> tuple[dict, dict]:
    """Populated but incomplete: one missing horizon, one missing arming block,
    and a stale lever caption — the states the packet calls out."""
    pl, lt = _real_payloads()
    lt = json.loads(json.dumps(lt))
    lt["fed_path"]["implied"]["m3"] = None
    lt["fed_path"]["implied"]["m6"] = None
    pl = json.loads(json.dumps(pl))
    for lv in pl.get("levers", []):
        if lv.get("asset") is None:
            lv["arming"] = None
    pl["jawboning"]["n_30d"] = 0
    return pl, lt


def _missing_payloads() -> tuple[dict, dict]:
    """All-null: no state, no path, no counts, no levers."""
    return ({"schema": "policy_lever.v1", "as_of": "2026-10-30"},
            {"date": "2026-10-30", "fed_path": {}, "fed_stance": None})


STATES = {
    "populated": _real_payloads,
    "partial": _partial_payloads,
    "missing": _missing_payloads,
}

# The populated state gets the full matrix; the degraded states get one
# desktop and one mobile shape each — enough to show the honest degraded face.
_FULL_MATRIX = [(t, l, s) for t in THEMES for l in LANGS for s in SIZES]
_REDUCED_MATRIX = [("dark", "en", SIZES[0]), ("light", "zh", SIZES[1])]


def _shapes(state: str):
    return _FULL_MATRIX if state == "populated" else _REDUCED_MATRIX


def render(state: str) -> str:
    pl, lt = STATES[state]()
    return _env().get_template("dashboard.html.j2").render(**_vm(pl, lt), mode="macro")


# --------------------------------------------------------------------------- #
# serve
# --------------------------------------------------------------------------- #

class _Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D102 - silence the probe server
        pass


def _git(*args: str) -> str:
    import subprocess
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), *args],
                                       text=True).strip()
    except Exception:  # noqa: BLE001 - evidence metadata only
        return "unknown"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _stage(tmp: Path, html: str) -> Path:
    """A served directory that resolves the page's relative asset references."""
    tmp.mkdir(parents=True, exist_ok=True)
    for src in (ROOT / "templates", ROOT / "site"):
        for item in src.iterdir():
            if item.name in ("macro.html", "us_stocks.html"):
                continue
            link = tmp / item.name
            if link.exists() or link.is_symlink():
                continue
            try:
                link.symlink_to(item)
            except OSError:
                pass
    (tmp / "macro.html").write_text(html, encoding="utf-8")
    return tmp


# --------------------------------------------------------------------------- #
# capture
# --------------------------------------------------------------------------- #

def _capture(page, out_dir: Path, name: str, selector: str, *, pad: int = 12) -> dict:
    el = page.query_selector(selector)
    if el is None:
        raise SystemExit(f"selector not found: {selector}")
    el.scroll_into_view_if_needed()
    page.wait_for_timeout(150)
    box = el.bounding_box()
    if not box:
        raise SystemExit(f"selector has no box: {selector}")
    vw, vh = page.viewport_size["width"], page.viewport_size["height"]
    x = max(0.0, min(box["x"] - pad, vw - 1.0))
    y = max(0.0, min(box["y"] - pad, vh - 1.0))
    clip = {
        "x": round(x, 1),
        "y": round(y, 1),
        "width": round(min(box["width"] + 2 * pad, vw - x), 1),
        "height": round(min(box["height"] + 2 * pad, vh - y), 1),
    }
    if clip["width"] < 2 or clip["height"] < 2:
        raise SystemExit(f"clip too small for {selector}: {clip}")
    path = out_dir / f"{name}.png"
    page.screenshot(path=str(path), clip=clip)
    return {"file": path.name, "clip": clip, "bytes": path.stat().st_size}


def run(out_dir: Path, states=("populated",)) -> dict:
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    receipt = {"schema": "policy_monitor_browser_evidence.v1",
               "template": "templates/dashboard.html.j2",
               "normalizer": "lib/policy_monitor_view.py",
               "payloads": ["site/policy_lever.json", "data/regime/latest.json"],
               "command": "CI=1 python3 tests/probe_policy_monitor_browser.py "
                          "--out research/evidence/policy_monitor_upgrade_20261101 "
                          "--states populated,partial,missing",
               "resolved_sha": _git("rev-parse", "HEAD"),
               "template_blob": _git("hash-object", "templates/dashboard.html.j2"),
               "normalizer_blob": _git("hash-object", "lib/policy_monitor_view.py"),
               "face_fragment_blob": _git("hash-object", "templates/_policy_monitor_face.html.j2"),
               "dialog_fragment_blob": _git("hash-object", "templates/_policy_monitor_dialog.html.j2"),
               "stylesheet_blob": _git("hash-object", "templates/_policy_monitor.css.j2"),
               "harness_note": ("The macro page's detailed dialogs are the registration "
                                "benefit: the page's own MMXAccessPreview resolves an "
                                "anonymous visitor to the sign-in sheet, so the probe "
                                "resolves that preview as a signed-in tier before it "
                                "clicks the face. The page's own mx5OpenDlg/mx5CloseDlg "
                                "controller opens the real dialog; no markup or controller "
                                "code is patched."),
               "shapes": []}
    tmp = Path(tempfile.mkdtemp(prefix="policy-monitor-shots-"))
    port = _free_port()
    handler = functools.partial(_Handler, directory=str(tmp))
    server = socketserver.TCPServer(("127.0.0.1", port), handler)
    server.allow_reuse_address = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            for state in states:
                html = render(state)
                _stage(tmp / state, html)
                for theme, lang, (w, h) in _shapes(state):
                            page = browser.new_page(viewport={"width": w, "height": h},
                                                    device_scale_factor=1)
                            page.add_init_script(
                                "window.MMXAccessPreview = window.MMXAccessPreview || {};"
                                "window.MMXAccessPreview.isAnon = function(){ return false; };")
                            page.goto(f"http://127.0.0.1:{port}/{state}/macro.html",
                                      wait_until="load")
                            # The macro page's detailed dialogs are the
                            # registration benefit: the page's own access
                            # preview resolves an anonymous visitor to the
                            # sign-in sheet. The probe resolves the preview as
                            # a signed-in tier so the REAL controller opens the
                            # REAL dialog — the markup and the controller are
                            # untouched.
                            page.evaluate(
                                "() => { window.MMXAccessPreview = window.MMXAccessPreview || {};"
                                " window.MMXAccessPreview.isAnon = function(){ return false; }; }")
                            page.evaluate(
                                "([t,l]) => { document.documentElement.setAttribute('data-theme', t);"
                                " document.documentElement.setAttribute('data-lang', l); }",
                                [theme, lang])
                            page.wait_for_timeout(250)
                            tag = f"policy-{state}-{lang}-{theme}-{w}"
                            shot = {"state": state, "theme": theme, "lang": lang,
                                    "width": w, "height": h, "files": []}
                            shot["files"].append({
                                "kind": "card-face",
                                **_capture(page, out_dir, f"{tag}-face", "#sx-policy-v2")})
                            # open through the page's own controller
                            page.click("#sx-policy-v2 .mx5-card-face")
                            page.wait_for_selector("#dlg-policy.open", timeout=5000)
                            page.wait_for_timeout(900)
                            shot["files"].append({
                                "kind": "dialog",
                                **_capture(page, out_dir, f"{tag}-dialog", "#dlg-policy .mx5-dlg-panel")})
                            # at 390 the chart sits below the fold of the
                            # bottom sheet, so it gets its own scrolled capture
                            if w <= 390 and page.query_selector("#dlg-policy .plm-chartwrap"):
                                shot["files"].append({
                                    "kind": "chart",
                                    **_capture(page, out_dir, f"{tag}-chart",
                                              "#dlg-policy .plm-chartwrap")})
                            # the values table + the Fed projection table must be
                            # reachable in the live DOM
                            shot["table_rows"] = page.eval_on_selector_all(
                                "#dlg-policy .plm-table tbody tr", "els => els.length")
                            shot["fed_dot_rows"] = page.eval_on_selector_all(
                                "#dlg-policy .plm-src-table tbody tr", "els => els.length")
                            # close and reopen through the controller: no
                            # duplicated instances or listeners
                            page.click("#dlg-policy .mx5-dlg-close")
                            page.wait_for_timeout(500)
                            page.click("#sx-policy-v2 .mx5-card-face")
                            page.wait_for_selector("#dlg-policy.open", timeout=5000)
                            page.wait_for_timeout(300)
                            shot["reopen_ok"] = page.eval_on_selector_all(
                                "#dlg-policy", "els => els.length") == 1
                            # Escape closes and focus returns to the trigger
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(500)
                            shot["escape_closed"] = page.eval_on_selector_all(
                                "#dlg-policy.open", "els => els.length") == 0
                            shot["focus_returned"] = page.evaluate(
                                "() => document.activeElement && "
                                "document.activeElement.id === 'sx-policy-v2' ? true : "
                                "(document.activeElement && "
                                "document.activeElement.closest('#sx-policy-v2') ? true : false)")
                            # horizontal overflow must not appear at 390
                            shot["no_page_overflow"] = page.evaluate(
                                "() => document.documentElement.scrollWidth <= "
                                "document.documentElement.clientWidth + 1")
                            page.close()
                            receipt["shapes"].append(shot)
            browser.close()
    finally:
        server.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)
    (out_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    return receipt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="research/evidence/policy_monitor_upgrade_20261101")
    ap.add_argument("--states", default="populated")
    args = ap.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    receipt = run(out, states=tuple(args.states.split(",")))
    print(json.dumps({"files": len(list(out.glob("*.png"))),
                      "shapes": len(receipt["shapes"]),
                      "out": str(out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
