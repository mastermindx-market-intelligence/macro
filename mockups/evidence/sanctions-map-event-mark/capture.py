#!/usr/bin/env python3
"""Capture dark+light × EN/ZH × 1440/390 of the LIVE public-news event mark on
sanctions_map.html (MO-PAID-008 / PR #7377 / D26).

TWO cells per matrix point (16 PNGs total):
  * cells/map-gbr-mark-<theme>-<locale>-<viewport>.png      — clip the SVG
    wrapper that carries `data-news-gbr`; record bbox of GBR path and verify
    it is inside the clip. The JURISDICTION-level mark on the ISO3 base map
    IS the lawful live event pin (D26).
  * cells/event-pins-panel-<theme>-<locale>-<viewport>.png  — clip #event-pins
    (the panel of dated public-news rows); capture the locale-specific text
    (.l-en / .l-zh only) plus the distinct YYYY-MM-DD dates it lists.

State applied AFTER first paint so localStorage + setTheme/setLang agree
(R4 idiom). The page bytes are served byte-identical from origin/main
(measured 2026-10-02, 240,288 B). Run from the repo root::

    python3 mockups/evidence/sanctions-map-event-mark/capture.py

No credentials. No network beyond the bundled static fixtures served from a
local python http.server. Reproducible end-to-end.
"""
from __future__ import annotations

import hashlib
import http.server
import json
import shutil
import socketserver
import struct
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent.parent  # mockups/.../capture.py -> repo root
sys.path.insert(0, str(_REPO))

OUT_DIR = _REPO / "mockups" / "evidence" / "sanctions-map-event-mark"
CELLS_DIR = OUT_DIR / "cells"

VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}
LOCALES = ("en", "zh")
THEMES = ("dark", "light")

# Relative paths under <site>/ that the served page references. Cache-busting
# `?v=` query strings are stripped — the bare paths are what theme.js, the
# link rel="stylesheet" href attrs, and the script src attrs (modulo v) load.
ASSET_RELPATHS = (
    "theme.css",
    "theme.js",
    "navigation-refresh.css",
    "product-nav-icons.css",
    "live.js",
    "live_config.js",
    "logo_config.js",
    "stock-logos.js",
    "wh_banner.js",
    "assets/css/52dc11d5.css",
    "favicon.ico",
    "favicon.svg",
    "apple-touch-icon.png",
)

# State applied AFTER first paint so localStorage + setTheme/setLang agree.
_STATE_SEED = """
() => {
  try {
    const m = (location.search || '').match(/[?&]t=([^&]+)/);
    const l = (location.search || '').match(/[?&]l=([^&]+)/);
    if (m) { localStorage.setItem('theme', m[1]); localStorage.removeItem('themeAuto'); }
    if (l) { localStorage.setItem('lang', l[1]); }
  } catch (e) {}
}
"""

_APPLY_STATE = """
({theme, locale}) => {
  const docEl = document.documentElement;
  if (typeof window.setTheme === 'function') { window.setTheme(theme); }
  else {
    docEl.setAttribute('data-theme', theme);
    try { localStorage.setItem('theme', theme); localStorage.removeItem('themeAuto'); } catch (e) {}
  }
  if (typeof window.setLang === 'function') { window.setLang(locale); }
  else {
    docEl.setAttribute('data-lang', locale);
    if (locale) docEl.lang = locale;
    try { localStorage.setItem('lang', locale); } catch (e) {}
  }
  return {theme: docEl.getAttribute('data-theme'), locale: docEl.getAttribute('data-lang')};
}
"""


def _git(*args, cwd=_REPO):
    return subprocess.check_output(["git", *args], cwd=cwd)


def _git_origin_main_blob(relpath):
    return subprocess.check_output(
        ["git", "show", f"origin/main:{relpath}"], cwd=_REPO
    )


def materialize(scratch):
    """Materialize the served fixture from origin/main into <scratch>.

    Returns (source_commit, page_sha256). Fails loudly if any blob is missing.
    """
    source_commit = _git("rev-parse", "origin/main").decode().strip()
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "assets" / "css").mkdir(parents=True, exist_ok=True)

    # Page bytes (240,288 B as measured 2026-10-02).
    page_bytes = _git_origin_main_blob("site/sanctions_map.html")
    (scratch / "sanctions_map.html").write_bytes(page_bytes)
    page_sha256 = hashlib.sha256(page_bytes).hexdigest()

    for relpath in ASSET_RELPATHS:
        try:
            blob = _git_origin_main_blob(f"site/{relpath}")
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"missing blob site/{relpath} on origin/main ({exc}); aborting"
            ) from exc
        (scratch / relpath).write_bytes(blob)

    return source_commit, page_sha256


def _serve(site_dir):
    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args, **kwargs):
            pass

    import os  # noqa: PLC0415
    os.chdir(site_dir)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), Q)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def _sha256_and_dims(png):
    digest = hashlib.sha256(png).hexdigest()
    if png[:8] == b"\x89PNG\r\n\x1a\n" and png[12:16] == b"IHDR":
        w, h = struct.unpack(">II", png[16:24])
    else:
        w, h = 0, 0
    return digest, w, h


def _bbox_contains(outer, inner):
    """Return True iff `inner` is fully inside `outer` (rect ⊆ rect)."""
    return (
        outer["x"] <= inner["x"] - 0.5
        and outer["y"] <= inner["y"] - 0.5
        and outer["x"] + outer["w"] >= inner["x"] + inner["w"] - 0.5
        and outer["y"] + outer["h"] >= inner["y"] + inner["h"] - 0.5
    )


def _capture_one(browser, base, *, width, height, locale, theme):
    """Run one matrix point. Returns dict with keys: applied, gbr_bbox,
    container_box, panel_box, panel_text, rows, dates, png_map, png_panel."""
    from playwright.sync_api import sync_playwright  # noqa: PLC0415
    state = {"theme": theme, "locale": locale}
    context = browser.new_context(
        viewport={"width": width, "height": height},
        locale="zh-CN" if locale == "zh" else "en-US",
        color_scheme=theme,
        device_scale_factor=1,
    )
    context.add_init_script(f"({_STATE_SEED.strip()})();")
    page = context.new_page()
    try:
        url = f"{base}/sanctions_map.html?t={theme}&l={locale}"
        resp = page.goto(url, wait_until="load", timeout=30000)
        if resp is None or not resp.ok:
            raise RuntimeError(f"HTTP {getattr(resp, 'status', 'none')}")
        page.wait_for_timeout(400)

        # Belt-and-braces: re-apply via setTheme/setLang (or direct attr).
        applied = page.evaluate(_APPLY_STATE.strip(), state) or {}
        if applied.get("theme") != theme or applied.get("locale") != locale:
            raise RuntimeError(
                f"state mismatch: requested theme={theme} locale={locale} "
                f"observed {applied!r}"
            )

        # Wait for the predicate structure required by the spec:
        # 1) panel has >=1 <li>, 2) the GBR jurisdiction mark exists.
        page.wait_for_function(
            """
            () => {
              const lis = document.querySelectorAll('#event-pins li');
              const gbr = document.querySelector('path.wm-c[data-iso3="GBR"][data-news="1"]');
              return lis.length >= 1 && !!gbr;
            }
            """,
            timeout=8000,
        )
        page.wait_for_timeout(120)

        # Pull everything we need in one evaluate: PAGE-relative bboxes of map
        # container, GBR path, #event-pins (so the full_page screenshot can
        # clip them correctly — clip y is relative to the page top, not the
        # viewport), plus the GBR data-news attr, the container's data-news-gbr,
        # count of #event-pins li, locale text, and distinct dates.
        info = page.evaluate(
            """
            (locale) => {
              const wrapper = document.querySelector('section.panel.sm-mapwrap');
              const cont = document.querySelector('figure.sm-map[data-news-gbr]');
              const gbr = document.querySelector('path.wm-c[data-iso3="GBR"][data-news="1"]');
              const panel = document.querySelector('#event-pins');
              const lis = document.querySelectorAll('#event-pins li');
              const wr = wrapper.getBoundingClientRect();
              const cr = cont.getBoundingClientRect();
              const gr = gbr.getBoundingClientRect();
              const pr = panel.getBoundingClientRect();
              const sy = window.scrollY;

              const toPage = (r) => ({x: r.left, y: r.top + sy, w: r.width, h: r.height});

              // Locale text: only the .l-<locale> nodes inside the panel.
              const localeNodes = panel.querySelectorAll('.l-' + locale);
              let panel_text = '';
              localeNodes.forEach(n => {
                const t = (n.textContent || '').trim();
                if (t) panel_text += t + '\\n';
              });

              // Distinct YYYY-MM-DD from <time> tags in the panel.
              const dates = [];
              lis.forEach(li => {
                const t = li.querySelector('time');
                if (t) dates.push((t.textContent || '').trim());
              });

              return {
                container: toPage(cr),
                wrapper: toPage(wr),
                gbr_bbox: toPage(gr),
                gbr_data_news: gbr.getAttribute('data-news'),
                data_news_gbr: cont.getAttribute('data-news-gbr'),
                panel: toPage(pr),
                rows: lis.length,
                panel_text: panel_text.slice(0, 600),
                dates: Array.from(new Set(dates)).sort(),
                viewport_w: window.innerWidth,
                viewport_h: window.innerHeight,
              };
            }
            """,
            locale,
        )

        cont = info["container"]
        gbr = info["gbr_bbox"]
        panel = info["panel"]
        wrapper = info["wrapper"]
        # Spec bbox assertion: the GBR path MUST sit inside the map container.
        # The MAP CLIP in this script is the section.panel.sm-mapwrap wrapper
        # (figure + heading + legend), per spec wording "the figure/wrapper of
        # the SVG" — both readings are spec-compliant; the wrapper is what makes
        # locale-distinct content visible inside the cell.
        if not _bbox_contains(wrapper, cont):
            raise RuntimeError(
                f"figure bbox {cont} not inside wrapper {wrapper}"
            )
        if not _bbox_contains(wrapper, gbr):
            raise RuntimeError(
                f"gbr bbox {gbr} not inside wrapper {wrapper}"
            )

        # MAP cell: clip = full element box of the wrapper section. The wrapper
        # bbox is PAGE-RELATIVE (window.scrollY added), so it works correctly
        # with full_page=True (whose clip y is also page-relative).
        map_clip = {
            "x": max(0.0, wrapper["x"]),
            "y": max(0.0, wrapper["y"]),
            "width": wrapper["w"],
            "height": wrapper["h"],
        }
        png_map = page.screenshot(
            type="png", full_page=True, clip=map_clip
        )

        # PANEL cell: clip = full element box of #event-pins (page-relative).
        # Use full_page=True unconditionally — the panel is taller than the
        # viewport on mobile AND extends below the 900px viewport fold on
        # desktop. full_page + page-relative clip captures the entire panel.
        panel_clip = {
            "x": max(0.0, panel["x"]),
            "y": max(0.0, panel["y"]),
            "width": panel["w"],
            "height": panel["h"],
        }
        png_panel = page.screenshot(
            type="png", full_page=True, clip=panel_clip
        )

        return {
            "applied": applied,
            "container": cont,
            "gbr_bbox": gbr,
            "gbr_data_news": info["gbr_data_news"],
            "data_news_gbr": info["data_news_gbr"],
            "panel": panel,
            "rows": info["rows"],
            "panel_text": info["panel_text"],
            "dates": info["dates"],
            "map_clip": map_clip,
            "panel_clip": panel_clip,
            "png_map": png_map,
            "png_panel": png_panel,
        }
    finally:
        context.close()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)

    scratch = Path(tempfile.mkdtemp(prefix="sanctions_map_mark_"))
    source_commit, page_sha256 = materialize(scratch)
    httpd, port = _serve(scratch)
    base = f"http://127.0.0.1:{port}"
    print(
        f"Materialized from origin/main {source_commit[:12]} (page {page_sha256[:12]}); "
        f"serving from {scratch} at {base}",
        flush=True,
    )

    from playwright.sync_api import sync_playwright  # noqa: PLC0415
    cells = []
    captured_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with sync_playwright() as m:
        browser = m.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            for viewport_name, (w, h) in VIEWPORTS.items():
                for locale in LOCALES:
                    for theme in THEMES:
                        for kind in ("map-gbr-mark", "event-pins-panel"):
                            alias = f"{kind}-{theme}-{locale}-{viewport_name}.png"
                            entry = {
                                "file": f"cells/{alias}",
                                "kind": kind,
                                "theme": theme,
                                "locale": locale,
                                "viewport": viewport_name,
                                "viewport_width": w,
                                "viewport_height": h,
                            }
                            try:
                                got = _capture_one(
                                    browser, base, width=w, height=h,
                                    locale=locale, theme=theme,
                                )
                                png = got["png_map"] if kind == "map-gbr-mark" else got["png_panel"]
                                digest, pw, ph = _sha256_and_dims(png)
                                (CELLS_DIR / alias).write_bytes(png)
                                cell = {
                                    **entry,
                                    "applied_theme": got["applied"].get("theme"),
                                    "applied_locale": got["applied"].get("locale"),
                                    "bbox": (
                                        got["gbr_bbox"] if kind == "map-gbr-mark"
                                        else got["panel"]
                                    ),
                                    "clip": (
                                        got["map_clip"] if kind == "map-gbr-mark"
                                        else got["panel_clip"]
                                    ),
                                    "sha256": digest,
                                    "bytes": len(png),
                                    "width": pw,
                                    "height": ph,
                                    "captured": captured_iso,
                                }
                                if kind == "map-gbr-mark":
                                    cell["selector"] = "figure.sm-map[data-news-gbr]"
                                    cell["gbr_data_news"] = got["gbr_data_news"]
                                    cell["data_news_gbr"] = got["data_news_gbr"]
                                    cell["container_box"] = got["container"]
                                else:
                                    cell["selector"] = "#event-pins"
                                    cell["rows"] = got["rows"]
                                    cell["panel_text"] = got["panel_text"]
                                    cell["dates"] = got["dates"]
                                entry = cell
                                print(
                                    f"  ✓ {alias} ({pw}x{ph}, {len(png)}B, "
                                    f"theme={got['applied'].get('theme')} "
                                    f"locale={got['applied'].get('locale')})",
                                    flush=True,
                                )
                            except Exception as exc:
                                entry.update({
                                    "captured": False,
                                    "reason": f"{type(exc).__name__}: {exc}",
                                })
                                print(f"  ✗ {alias}: {type(exc).__name__}: {exc}", flush=True)
                            cells.append(entry)
        finally:
            browser.close()

    httpd.shutdown()
    shutil.rmtree(scratch)

    # sha256 of the capture.py bytes (so an evidence reader can verify the
    # cells came from this exact script).
    capture_tool_sha = hashlib.sha256(
        Path(__file__).read_bytes()
    ).hexdigest()

    manifest = {
        "page_id": "sanctions_map",
        "route": "sanctions_map.html",
        "registry_route": "macro:sanctions_map",
        "route_kind": "intelligence_desk",
        "subject": "public-news event mark (MO-PAID-008 / #7377) over the ISO3 base map (MO-DELTA-031)",
        "source": "origin/main site/sanctions_map.html — served byte-identical 2026-10-02",
        "source_commit": source_commit,
        "page_sha256": page_sha256,
        "generated_at": captured_iso,
        "capture_tool_module_sha256": capture_tool_sha,
        "cells": cells,
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False)
    )
    ok = sum(1 for c in cells if c.get("sha256"))
    print(f"\n{ok}/{len(cells)} cells captured → {OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()