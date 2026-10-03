#!/usr/bin/env python3
"""O28 R2 sweep — measure `uk_box_blue_px` + chroma over a fixed
(W, OD, OL) grid against the same O28 capture tool, written to
`mockups/evidence/sanctions-map-mobile-key/sweep.json`.

Grid (D54 fixed):
  W:  1, 1.25, 1.5
  OD: .7, .85, 1   (dark)
  OL: .55, .7, .85, 1   (light)
Per W: 3 dark × 4 light = 7 measurements × 3 W = 21 measurements
total. Only `en` locale is captured (zh is identical geometry per the
metric definition in capture.py).

Imports `_capture_one` + `_build_mobile` + `_OLD_MOBILE` + scratch
helpers from `capture.py` so the measurement is byte-identical to the
dom.json captures. Each (W, OD, OL) tuple gets its own scratch with
the O28 patch applied — separate CSS per measurement keeps the
classifier output (uk_box_blue_px + chroma) independent across rows.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import importlib.util
import json
import http.server
import os
import shutil
import socketserver
import sys
import tempfile
import threading
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent.parent

# Load capture.py as a module so we share the metric + scratch helpers.
_CAP_PATH = Path(__file__).with_name("capture.py")
_spec = importlib.util.spec_from_file_location("cap_module", _CAP_PATH)
_cap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cap)

_build_mobile = _cap._build_mobile
_copy_local_flat = _cap._copy_local_flat
_capture_one = _cap._capture_one
_GIT = _cap._git
THEME_CSS = _cap.THEME_CSS
CSS_ASSET = _cap.CSS_ASSET
VIEWPORT = _cap.VIEWPORT
DARK_STROKE = _cap._DARK_STROKE
LIGHT_STROKE = _cap._LIGHT_STROKE

WIDTHS = ["1", "1.25", "1.5"]
DARK_OPS = [".7", ".85", "1"]
LIGHT_OPS = [".55", ".7", ".85", "1"]


class _Q(socketserver.TCPServer):
    allow_reuse_address = True

    def log_message(self, *args, **kwargs):
        pass


def _serve(site_dir):
    os.chdir(site_dir)
    httpd = _Q(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def _materialize(scratch, *, width, dark_opacity, light_opacity):
    """Materialize scratch with the O28 CSS patched to (W, OD, OL)."""
    source_commit = _GIT("rev-parse", "origin/main").decode().strip()
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "assets" / "css").mkdir(parents=True, exist_ok=True)

    page_bytes = _copy_local_flat("site/sanctions_map.html", scratch)
    page_sha256 = hashlib.sha256(page_bytes).hexdigest()
    _copy_local_flat(f"site/{THEME_CSS}", scratch)
    _copy_local_flat(f"site/{CSS_ASSET}", scratch)

    css_path = scratch / CSS_ASSET
    css = css_path.read_text()
    new_mobile = _build_mobile(width, dark_opacity, light_opacity)
    n = css.count(_cap._OLD_MOBILE)
    if n != 1:
        raise RuntimeError(
            f"O28 patch: expected 1 occurrence of OLD_MOBILE in {css_path}, got {n}"
        )
    css = css.replace(_cap._OLD_MOBILE, new_mobile)
    css_path.write_text(css)

    return source_commit, page_sha256


def _capture_grid_point(browser, *, theme, width, opacity, source_commit, page_sha256):
    """Capture a single (theme, W, opacity) point. OL is set to opacity
    when theme=='light', OD when theme=='dark'; the unused position is
    filled with the dark default (.7) so the CSS patch shape stays valid.
    """
    if theme == "dark":
        od, ol = opacity, ".7"
    else:
        od, ol = ".7", opacity

    scratch = Path(tempfile.mkdtemp(prefix="o28r2_sweep_"))
    try:
        src, page_sha = _materialize(
            scratch, width=width, dark_opacity=od, light_opacity=ol,
        )
        assert src == source_commit, "source_commit mismatch mid-sweep"
        assert page_sha == page_sha256, "page_sha256 mismatch mid-sweep"
        httpd, port = _serve(scratch)
        try:
            base = f"http://127.0.0.1:{port}"
            # R5: crops go to the sweep's OWN scratch (deleted below) so a grid
            # point can never overwrite cells/{theme}-en-390-*.png, and the grid
            # point's block is the source-parity reference for this capture.
            cells = _capture_one(
                browser, base, locale="en", themes=(theme,),
                mobile_block=_cap._build_mobile(width, od, ol),
                cells_dir=scratch / "sweep_cells",
            )
            cell = cells[f"{theme}-en"]
        finally:
            httpd.shutdown()
    finally:
        shutil.rmtree(scratch)

    return {
        "theme": theme,
        "width": width,
        "opacity": opacity,
        "uk_box_blue_px": cell["uk_box_blue_px"],
        "mark_mean_chroma": cell["mark_mean_chroma"],
        "rung3_mean_chroma": cell["rung3_mean_chroma"],
        # S2 receipt semantics (sweep.json, R2): a SWEEP row's `key_mark_parity`
        # is RENDERED-width parity — getComputedStyle() legend border vs SVG
        # stroke — False for every W != 1 because Chromium rounds the HTML
        # border to whole px (README §Sweep). dom.json's same-named field is
        # SOURCE parity. Recorded explicitly (R5) so a re-run reproduces the
        # committed column; the source form rides alongside under its own key.
        "key_mark_parity": cell["gbr_stroke_width"] == cell["legend_news_i_border_width"],
        "key_mark_parity_source": cell["key_mark_parity"],
        "gbr_stroke_width": cell["gbr_stroke_width"],
        "gbr_stroke_dasharray": cell["gbr_stroke_dasharray"],
        "gbr_stroke_opacity": cell["gbr_stroke_opacity"],
        "legend_news_i_border_width": cell["legend_news_i_border_width"],
        "legend_news_i_opacity": cell["legend_news_i_opacity"],
        "legend_news_i_border_style": cell["legend_news_i_border_style"],
        "gbr_bbox": cell["gbr_bbox"],
        "rung3_bbox": cell["rung3_bbox"],
        "data_news_gbr": cell["data_news_gbr"],
        "is_hi_count": cell["is_hi_count"],
        "scroll_w_le_viewport": cell["scroll_w_le_viewport"],
    }


def main():
    OUT_DIR = _CAP_PATH.parent
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # First page_sha so we can assert per-row consistency.
    seed_scratch = Path(tempfile.mkdtemp(prefix="o28r2_seed_"))
    try:
        source_commit, page_sha256 = _materialize(
            seed_scratch, width="1", dark_opacity=".7", light_opacity=".55",
        )
    finally:
        shutil.rmtree(seed_scratch)

    from playwright.sync_api import sync_playwright

    rows = []
    with sync_playwright() as m:
        browser = m.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            for W in WIDTHS:
                for OD in DARK_OPS:
                    row = _capture_grid_point(
                        browser, theme="dark", width=W, opacity=OD,
                        source_commit=source_commit, page_sha256=page_sha256,
                    )
                    rows.append(row)
                    print(
                        f"W={W} OD={OD} dark  -> uk_box_blue_px={row['uk_box_blue_px']:>3} "
                        f"mark_chroma={row['mark_mean_chroma']:.3f} "
                        f"rung3_chroma={row['rung3_mean_chroma']:.3f} "
                        f"key_parity={row['key_mark_parity']}",
                        flush=True,
                    )
                for OL in LIGHT_OPS:
                    row = _capture_grid_point(
                        browser, theme="light", width=W, opacity=OL,
                        source_commit=source_commit, page_sha256=page_sha256,
                    )
                    rows.append(row)
                    print(
                        f"W={W} OL={OL} light -> uk_box_blue_px={row['uk_box_blue_px']:>3} "
                        f"mark_chroma={row['mark_mean_chroma']:.3f} "
                        f"rung3_chroma={row['rung3_mean_chroma']:.3f} "
                        f"key_parity={row['key_mark_parity']}",
                        flush=True,
                    )
        finally:
            browser.close()

    capture_tool_sha = hashlib.sha256(_CAP_PATH.read_bytes()).hexdigest()
    out = {
        "axes": {
            "widths": WIDTHS,
            "dark_opacities": DARK_OPS,
            "light_opacities": LIGHT_OPS,
            "themes": ["dark", "light"],
            "locales": ["en"],
            "viewport": list(VIEWPORT),
            "device_scale_factor": 1,
        },
        "rows": rows,
        "source_commit": source_commit,
        "page_sha256": page_sha256,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "capture_tool_module_sha256": capture_tool_sha,
    }
    out_path = OUT_DIR / "sweep.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\n21 rows captured → {out_path}", flush=True)


if __name__ == "__main__":
    main()