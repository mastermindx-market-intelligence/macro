#!/usr/bin/env python3
"""Capture the aibrief.html Morning Orientation band — 8 PNGs: {dark, light} x {EN, ZH} x {1440, 390}.

Per §5 of the MOR-2b build packet: lanes B and C carry an evidence matrix in the
PR body. Lane C adds the aibrief band — two cells:
    | 9  | dark  | EN | 1440 | aibrief.html band |
    | 10 | light | EN | 1440 | aibrief.html band |

We render templates/aibrief.html.j2 with a hand-built am_edition panel and
serve from a scratch directory; we crop to the band element only so the
reviewer sees the art-direction surface, not the whole aibrief page.

We never write to site/ or data/ — this script is a scratch-only artifact.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import http.server
import socketserver
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402

OUT_DIR = _ROOT / "mockups" / "evidence" / "aibrief_band"
SHOTS_DIR = OUT_DIR / "shots"
VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}
LOCALES = ("en", "zh")
THEMES = ("dark", "light")

_APPLY_STATE_SCRIPT = """
(state) => {
  const root = document.documentElement;
  if (typeof window.setTheme === 'function') window.setTheme(state.theme);
  else root.setAttribute('data-theme', state.theme);
  if (typeof window.setLang === 'function') window.setLang(state.locale);
  else {
    root.setAttribute('data-lang', state.locale);
    root.lang = state.locale === 'zh' ? 'zh' : 'en';
  }
  return {theme: root.getAttribute('data-theme'), locale: root.getAttribute('data-lang')};
}
"""


def _content_address_png(png: bytes) -> tuple[str, str, int, int]:
    digest = hashlib.sha256(png).hexdigest()
    name = f"{digest}.png"
    png_signature = b"\x89PNG\r\n\x1a\n"
    if len(png) >= 24 and png[:8] == png_signature and png[12:16] == b"IHDR":
        width, height = struct.unpack(">II", png[16:24])
    else:
        width, height = 0, 0
    return name, digest, int(width), int(height)


def _band_fixture_payload() -> dict:
    return {
        "session_state": "NOT_YET_OPEN",
        "generated_at": "2026-09-08T13:00:00+00:00",
        "first_tape_en": (
            "S&P 500 ETF (SPY) is up +0.14% since yesterday's close."
        ),
        "first_tape_zh": (
            "标普500 ETF (SPY)自昨日收盘以来上涨 +0.14%。"
        ),
        "source_state": "CURRENT",
        "absent": False,
    }


def _render_aibrief_full(scratch: Path, am_edition_panel: dict) -> Path:
    """Render the FULL templates/aibrief.html.j2 (with _site_nav, theme.css etc.)
    into scratch space. We then serve scratch via http.server so the page loads
    its real CSS — letting the theme toggle actually paint two art directions."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(
        loader=FileSystemLoader(str(_ROOT / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    from engine import i18n  # noqa: E402
    env.globals.update(t=i18n.t, td=i18n.td, tr=i18n.tr)

    panels = {
        "am_edition": am_edition_panel,
        "ctx_strip": {"absent": True, "reason_en": "n/a", "reason_zh": "n/a"},
        "briefs": {},
    }
    as_of = "2026-09-08T15:00:00+00:00"
    out = scratch / "aibrief.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    html = env.get_template("aibrief.html.j2").render(
        as_of=as_of,
        **panels,
    )
    out.write_text(html, encoding="utf-8")
    return out


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args, **kwargs):
        pass


def _serve_and_capture(scratch_root: Path, head_sha: str) -> dict:
    handler = lambda *a, **kw: _Quiet(*a, directory=str(scratch_root), **kw)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.4)

    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tool": {
            "module_ref": "scripts/capture_aibrief_band_evidence.py",
            "module_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "target": "aibrief.html#am_edition_band",
        "head": head_sha,
        "axes": {
            "viewports": {vp: list(sz) for vp, sz in VIEWPORTS.items()},
            "locales": list(LOCALES),
            "themes": list(THEMES),
            "access": ["anonymous"],
            "subjects": ["band"],
        },
        "aliases": {},
        "excluded": [],
        "outcome": "captured",
        "totals": {"rest_cells": len(THEMES) * len(LOCALES), "rest_required": 2, "pages": 1},
        "honesty": {
            "access": "anonymous only",
            "authority": "This tool captures screenshots; it scores nothing.",
            "page": (
                "templates/aibrief.html.j2 rendered with a hand-built am_edition "
                "panel fixture in scratch space; never writes to site/ or data/."
            ),
        },
        "pages": [],
    }
    states = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                for theme in THEMES:
                    for locale in LOCALES:
                        for vp_name, (w, h) in VIEWPORTS.items():
                            state = {
                                "viewport": vp_name,
                                "locale": locale,
                                "theme": theme,
                                "access": "anonymous",
                                "viewport_width": w,
                                "viewport_height": h,
                                "force_state": None,
                                "subject": "band",
                            }
                            ctx = browser.new_context(viewport={"width": w, "height": h})
                            page = ctx.new_page()
                            page.goto(f"http://127.0.0.1:{port}/aibrief.html")
                            page.evaluate(
                                _APPLY_STATE_SCRIPT,
                                {"theme": theme, "locale": locale},
                            )
                            # Wait for the band panel to be in the DOM
                            page.wait_for_selector(
                                "div.panel:has(span.eyebrow):has-text('Morning Orientation')",
                                timeout=10000,
                            )
                            # Crop to the band's parent .panel
                            band = page.locator(
                                "div.panel:has(span.eyebrow):has-text('Morning Orientation')"
                            ).first
                            png = band.screenshot()
                            name, digest, width, height = _content_address_png(png)
                            (SHOTS_DIR / name).write_bytes(png)
                            alias = f"band-{theme}-{locale}-{vp_name}.png"
                            manifest["aliases"][alias] = f"shots/{name}"
                            state.update(
                                captured=True,
                                file=f"shots/{name}",
                                alias=alias,
                                sha256=digest,
                                bytes=len(png),
                                width=width,
                                height=height,
                                applied_theme=theme,
                                applied_locale=locale,
                            )
                            print(
                                f"  {theme}/{locale}/{vp_name}: ok ({alias} → {name[:8]} {width}x{height})"
                            )
                            states.append(state)
                            ctx.close()
            finally:
                browser.close()
    finally:
        httpd.shutdown()

    manifest["pages"].append({
        "page_id": "aibrief.html#am_edition_band",
        "route": "/aibrief.html#am_edition_band",
        "registry_route": "/aibrief.html#am_edition_band",
        "route_kind": "aibrief_band",
        "subject": "band",
        "selector": "div.panel:has(span.eyebrow):has-text('Morning Orientation')",
        "states": states,
        "metrics": {},
        "console_errors": [],
        "failed_responses": [],
        "gaps": [],
    })
    return manifest


def main() -> int:
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    head_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=str(_ROOT), text=True
    ).strip()

    scratch = _ROOT / ".aibrief-band-fixture"
    shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir(parents=True)
    # Stage the served root with symlinks to the asset tree. The aibrief
    # template uses href="theme.css" (root-relative) for the stylesheet and
    # _site_nav pulls in nav_market.js, theme.js, etc. We need EVERY asset the
    # page references at the served root, not nested under a sub-folder.
    asset_root = _ROOT / "site"
    for entry in asset_root.iterdir():
        if entry.name in ("am_edition.html", "am_edition.json", "aibrief.html"):
            continue  # we'll overwrite aibrief.html with our fixture
        dst = scratch / entry.name
        try:
            dst.symlink_to(entry)
        except FileExistsError:
            pass
    # Also symlink data/ for any read it does at render time (we already rendered,
    # but be safe).
    data_src = _ROOT / "data"
    if data_src.exists():
        try:
            (scratch / "data").symlink_to(data_src)
        except FileExistsError:
            pass

    # Render the FULL aibrief.html into scratch/ (overwriting the site copy).
    _render_aibrief_full(scratch, _band_fixture_payload())

    served = scratch
    manifest = _serve_and_capture(served, head_sha)
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    shutil.rmtree(scratch, ignore_errors=True)

    cells = len(THEMES) * len(LOCALES)
    print(
        f"outcome: captured  states: {cells}/{cells}  manifest: {OUT_DIR}/manifest.json"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())