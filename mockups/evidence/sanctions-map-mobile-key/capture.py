#!/usr/bin/env python3
"""Capture 390×844 dark+light × EN/ZH of the UK public-news mark on
sanctions_map.html AFTER O28 — the mobile 1 px solid hairline + matched
legend key.

For each of the four cells:
  - cells/{theme}-{lang}-390-ukzoom.png   — clip = GBR bbox ± 10 CSS-px
  - cells/{theme}-{lang}-390-legend.png   — clip = full element box of
                                            `.sm-legend`

Also writes `dom.json` keyed by `{theme}-{lang}` with every measurement
needed to verify the lane: stroke width / dasharray / opacity of the GBR
mark and of the legend key; blue-pixel census in a 21×21 CSS-px box
centred on the GBR bbox; chroma (max(rgb) − min(rgb)) of the GBR mark
and of one rung-3 land cell at the same bbox; `key_mark_parity`
(width/style/opacity agreement); `is_hi_count`; `scroll_w_le_viewport`.

Reuses the materialise-and-serve idiom of
`mockups/evidence/sanctions-map-event-layer-fix/capture.py`: copies
`site/sanctions_map.html` + its referenced CSS asset into a scratch
directory, applies the O28 CSS patch in that scratch, and serves it
from 127.0.0.1. State is applied BEFORE load via the inline `try{
localStorage.getItem('theme') … }` script on `templates/sanctions_map.html.j2`
line 13 — by setting `localStorage.theme` and `localStorage.lang` from
the page's addInitScript.

The cross-origin mm_brain.js widget ("Ask Mastermind" floating button)
is NOT present in the local-served HTML (it loads cross-origin and the
local fixture does not include it) — see `mockups/evidence/sanctions-map-event-layer-fix/README.md`
§"Fixed page chrome — Ask Mastermind button" (D5/D9). This lane does
NOT need to hide it; that fact is disclosed here for the record.
"""
from __future__ import annotations

import hashlib
import http.server
import json
import re
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

OUT_DIR = _REPO / "mockups" / "evidence" / "sanctions-map-mobile-key"
CELLS_DIR = OUT_DIR / "cells"

VIEWPORT = (390, 844)
# LOCALES may be narrowed via O28_LOCALES env (comma list). Default unchanged.
LOCALES = tuple(
    x for x in os.environ.get("O28_LOCALES", "en,zh").split(",") if x
) if "O28_LOCALES" in __import__("os").environ else ("en", "zh")
THEMES = ("dark", "light")

# The page references one CSS asset whose path includes a content hash;
# we patch the actual file in the scratch directory because the inline
# `<style>` block was extracted by the renderer (the legacy O21 lane's
# template inline now lives in site/assets/css/<hash>.css).
CSS_ASSET = "assets/css/5f0e8483.css"

# theme.css carries `--ink-link` / `--ink-act` / panel tokens. Without it
# the served fixture renders with a broken cascade and the figure.sm-map
# is pushed ~13000 px below the main (the SVG path's bbox lands in an
# empty mega-section, not in the visible map).
THEME_CSS = "theme.css"

# Old single-line mobile rule (origin/main dashed 13 8 + 1.5 — the O21
# fix being REPLACED by the new 4-line O28 mobile block).
_OLD_MOBILE = (
    "@media (max-width:600px){.sm-map[data-news-gbr=\"1\"] .wm-c[data-iso3=\"GBR\"],"
    "html[data-theme=\"light\"] .sm-map[data-news-gbr=\"1\"] .wm-c[data-iso3=\"GBR\"]"
    "{stroke-width:1.5;stroke-dasharray:13 8}}"
)


def _build_mobile(W, OD, OL):
    """Build the 4-line O28 mobile block with the given (width, dark
    opacity, light opacity). W/OD/OL are passed through verbatim (e.g.
    `1`, `1.25`, `1.5` for width; `.7`, `.85`, `1` for opacity) so the
    rendered CSS matches the template form exactly.
    """
    return (
        "@media (max-width:600px){.sm-map[data-news-gbr=\"1\"] .wm-c[data-iso3=\"GBR\"],"
        "html[data-theme=\"light\"] .sm-map[data-news-gbr=\"1\"] .wm-c[data-iso3=\"GBR\"]"
        "{stroke-width:" + W + ";stroke-dasharray:none;stroke-opacity:" + OD + "}\n"
        "html[data-theme=\"light\"] .sm-map[data-news-gbr=\"1\"] .wm-c[data-iso3=\"GBR\"]"
        "{stroke-opacity:" + OL + "}\n"
        ".sm-legend .sm-legend-news i{border:" + W + "px solid var(--ink-link);opacity:" + OD + "}\n"
        "html[data-theme=\"light\"] .sm-legend .sm-legend-news i{opacity:" + OL + "}}"
    )


# Default new block — R1's (W=1, OD=.7, OL=.55). Refactor keeps this as
# the no-arg default so `python3 capture.py` reproduces R1's run.
_NEW_MOBILE = _build_mobile("1", ".7", ".55")

# The page's inline script (template line 13) reads localStorage on load.
# addInitScript runs before any user script so we set theme/lang before the
# inline script reads them — this is the same idiom as the event-layer-fix
# capture (`_STATE_SEED`).
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

# Theme stroke colours measured on the event-layer-fix capture (D3): the
# per-theme `--ink-link` token renders as these rgb values. Used to count
# "blue" pixels in the 21×21 CSS-px UK box.
_DARK_STROKE = (122, 167, 224)
_LIGHT_STROKE = (41, 90, 234)


def _git(*args, cwd=_REPO):
    return subprocess.check_output(["git", *args], cwd=cwd)


def _git_origin_main_blob(relpath):
    return subprocess.check_output(
        ["git", "show", f"origin/main:{relpath}"], cwd=_REPO
    )


def _copy_local(relpath, scratch):
    src = _REPO / relpath
    if not src.is_file():
        raise RuntimeError(f"missing local blob {relpath}; aborting")
    data = src.read_bytes()
    (scratch / relpath).write_bytes(data)
    return data


def materialize(scratch, *, width="1", dark_opacity=".7", light_opacity=".55", baseline=False):
    """Materialize served fixture from this worktree's site/ into <scratch>.

    The HTTP server's document root is <scratch>, so files are written flat
    (not under site/). Source paths like `site/assets/css/<hash>.css` are
    flattened to `assets/css/<hash>.css` on disk.

    O28 R2 refactor: accepts (width, dark_opacity, light_opacity) so S1/S2
    can capture repeatedly with different candidates. `baseline=True` skips
    the O28 patch entirely (served CSS stays as origin/main's dashed 13 8
    + 1.5 — the mark this change REPLACES).
    """
    source_commit = _git("rev-parse", "origin/main").decode().strip()
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "assets" / "css").mkdir(parents=True, exist_ok=True)

    # Top-level page.
    page_bytes = _copy_local_flat("site/sanctions_map.html", scratch)
    page_sha256 = hashlib.sha256(page_bytes).hexdigest()

    # theme.css is required — without it `--ink-link` / `--panel` are
    # undefined and the figure.sm-map falls to ~y 13000 px in the document
    # (the rendered cascade lays the mega-section out first). Verified on
    # 2026-10-02: with theme.css copied, figure.sm-map lands at y ≈ 480.
    _copy_local_flat(f"site/{THEME_CSS}", scratch)

    # CSS asset — copy then patch the O28 mobile block in place.
    _copy_local_flat(f"site/{CSS_ASSET}", scratch)
    if not baseline:
        css_path = scratch / CSS_ASSET
        css = css_path.read_text()
        new_mobile = _build_mobile(width, dark_opacity, light_opacity)
        n = css.count(_OLD_MOBILE)
        if n != 1:
            raise RuntimeError(
                f"O28 patch: expected 1 occurrence of OLD_MOBILE in {css_path}, got {n}"
            )
        css = css.replace(_OLD_MOBILE, new_mobile)
        css_path.write_text(css)

    return source_commit, page_sha256


def _copy_local_flat(relpath, scratch):
    """Copy repo-relative relpath (e.g. site/foo.html) flat into scratch/foo.html."""
    src = _REPO / relpath
    if not src.is_file():
        raise RuntimeError(f"missing local blob {relpath}; aborting")
    tail = Path(*relpath.split("/")[1:])  # strip the leading `site/`
    dst = scratch / tail
    dst.parent.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes()
    dst.write_bytes(data)
    return data


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


def _dist2(a, b):
    return sum((ai - bi) ** 2 for ai, bi in zip(a, b))


def _crop_names(cell_key, theme, *, baseline):
    """Committed crop filenames for one cell.

    R4: a `--baseline` run used to write the SAME `{theme}-{locale}-390-*.png`
    names as the final-rung run, so whichever ran last silently overwrote the
    other's crops (R3's orphan pass then deleted the baseline crops the README
    lists). Baseline crops now carry the `baseline-` prefix the README and the
    committed receipt have always used — `cells/baseline-{theme}-390.png` for
    the UK zoom; the legend crop gains `-legend`.
    """
    if baseline:
        return f"baseline-{theme}-390.png", f"baseline-{theme}-390-legend.png"
    return f"{cell_key}-390-ukzoom.png", f"{cell_key}-390-legend.png"


def _capture_one(browser, base, *, locale, themes=THEMES, mobile_block=None, baseline=False,
                 cells_dir=None):
    """Capture one locale across `themes`; crops land in `cells_dir` (default
    the committed CELLS_DIR). R5: sweep.py passes its own scratch directory so a
    grid-point capture can never overwrite the committed final-rung crops —
    the same collision class R4 closed for `--baseline` runs."""
    theme_results = {}
    for theme in themes:
        context = browser.new_context(
            viewport={"width": VIEWPORT[0], "height": VIEWPORT[1]},
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

            # Focus the IRN row so the figure carries data-hi (S4 row_hi force).
            # We DO NOT scroll into view here — scrollIntoView would push
            # the GBR mark way above the viewport and full_page screenshots
            # sometimes clip that. Instead we set the focus class via a hover
            # event so the CSS `figure[data-hi]` rule engages; then we read
            # the GBR bbox before the screenshot to confirm scrollY is 0.
            page.evaluate(
                """() => {
                  const tr = document.querySelector('tr[data-iso3=\"IRN\"]');
                  if (tr) {
                    // dispatch a mouseover on the row to engage data-hi
                    const ev = new MouseEvent('mouseover', {bubbles:true});
                    tr.dispatchEvent(ev);
                  }
                  // also: scroll back to the top so the GBR bbox is the
                  // "true" map position (used for clip computation).
                  window.scrollTo(0, 0);
                }"""
            )
            page.wait_for_timeout(400)

            # Pull everything in one shot — DOM + computed styles + bbox.
            info = page.evaluate(
                """
                () => {
                  const figure = document.querySelector('figure.sm-map');
                  const gbr = document.querySelector('path.wm-c[data-iso3=\"GBR\"]');
                  const key = document.querySelector('.sm-legend .sm-legend-news i');
                  // Pick the first wm-c with data-rung="3" — RUS (a known rung-3).
                  const rung3Nodes = document.querySelectorAll('.wm-c[data-rung=\"3\"]');
                  const rung3 = rung3Nodes.length ? rung3Nodes[0] : null;
                  const isHi = figure && figure.hasAttribute('data-hi');
                  const isHiCount = document.querySelectorAll('tr.is-hi').length;

                  const cs = (el) => el ? window.getComputedStyle(el) : null;
                  const gbrCs = cs(gbr);
                  const keyCs = cs(key);
                  const rung3Cs = cs(rung3);

                  const toPage = (r) => ({x:r.left, y:r.top + window.scrollY, w:r.width, h:r.height});
                  const gbrBox = gbr ? toPage(gbr.getBoundingClientRect()) : null;
                  const keyBox = key ? toPage(key.getBoundingClientRect()) : null;
                  const rung3Box = rung3 ? toPage(rung3.getBoundingClientRect()) : null;
                  const legendBox = toPage(document.querySelector('.sm-legend').getBoundingClientRect());

                  return {
                    applied_theme: document.documentElement.getAttribute('data-theme'),
                    applied_locale: document.documentElement.getAttribute('data-lang'),
                    data_news_gbr: figure ? figure.getAttribute('data-news-gbr') : null,
                    data_hi: isHi,
                    is_hi_count: isHiCount,
                    gbr_box: gbrBox,
                    gbr_stroke: gbrCs ? gbrCs.stroke : null,
                    gbr_stroke_width: gbrCs ? gbrCs.strokeWidth : null,
                    gbr_stroke_dasharray: gbrCs ? gbrCs.strokeDasharray : null,
                    gbr_stroke_opacity: gbrCs ? gbrCs.strokeOpacity : null,
                    key_box: keyBox,
                    key_border_style: keyCs ? keyCs.borderStyle : null,
                    key_border_width: keyCs ? keyCs.borderWidth : null,
                    key_opacity: keyCs ? keyCs.opacity : null,
                    rung3_box: rung3Box,
                    rung3_fill: rung3Cs ? rung3Cs.fill : null,
                    rung3_fill_opacity: rung3Cs ? rung3Cs.fillOpacity : null,
                    legend_box: legendBox,
                    scroll_w_le_viewport: document.scrollingElement.scrollWidth <= window.innerWidth,
                    viewport_w: window.innerWidth,
                  };
                }
                """
            )

            # UK zoom clip = GBR bbox ± 10 CSS-px.
            gbr = info["gbr_box"]
            uk_clip = {
                "x": max(0, gbr["x"] - 10),
                "y": max(0, gbr["y"] - 10),
                "width": gbr["w"] + 20,
                "height": gbr["h"] + 20,
            }
            png_uk = page.screenshot(type="png", full_page=True, clip=uk_clip)

            # Legend clip = full element box of .sm-legend.
            lb = info["legend_box"]
            legend_clip = {
                "x": max(0, lb["x"]),
                "y": max(0, lb["y"]),
                "width": lb["w"],
                "height": lb["h"],
            }
            png_legend = page.screenshot(type="png", full_page=True, clip=legend_clip)

            # 21×21 CSS-px box centred on GBR; count < 60 RGB distance to
            # the per-theme stroke colour.
            stroke_rgb = _DARK_STROKE if theme == "dark" else _LIGHT_STROKE
            cx = gbr["x"] + gbr["w"] / 2
            cy = gbr["y"] + gbr["h"] / 2
            # Capture the box at DPR 1 for an honest pixel census.
            sample_clip = {
                "x": cx - 10.5,
                "y": cy - 10.5,
                "width": 21,
                "height": 21,
            }
            png_sample = page.screenshot(type="png", full_page=True, clip=sample_clip)

            # Decode the 21×21 PNG to raw RGB via Pillow if available,
            # else via a tiny inline PNG parser (we keep Pillow as a hard
            # dep — `playwright` already pulls it in, and the seat
            # measurements were already Pillow-based).
            try:
                from PIL import Image  # noqa: PLC0415
                import io  # noqa: PLC0415
                im = Image.open(io.BytesIO(png_sample)).convert("RGB")
                blue_pixels = 0
                chroma_pixels = []
                for x in range(im.width):
                    for y in range(im.height):
                        r, g, b = im.getpixel((x, y))
                        if _dist2((r, g, b), stroke_rgb) < 60 ** 2:
                            blue_pixels += 1
                        chroma_pixels.append(max(r, g, b) - min(r, g, b))
                uk_box_blue_px = blue_pixels
                # Mean chroma of the UK box (every pixel).
                mark_mean_chroma = sum(chroma_pixels) / max(1, len(chroma_pixels))
            except Exception as exc:
                raise RuntimeError(f"Pillow required for chroma census: {exc}") from exc

            # Rung-3 chroma: capture a 21×21 box on the rung-3 element
            # using the same method, then mean chroma.
            r3 = info["rung3_box"]
            r3_clip = {"x": r3["x"] - 10.5, "y": r3["y"] - 10.5, "width": 21, "height": 21}
            png_r3 = page.screenshot(type="png", full_page=True, clip=r3_clip)
            from PIL import Image  # noqa: PLC0415
            import io as _io  # noqa: PLC0415
            im3 = Image.open(_io.BytesIO(png_r3)).convert("RGB")
            chroma3 = []
            for x in range(im3.width):
                for y in range(im3.height):
                    r_, g_, b_ = im3.getpixel((x, y))
                    chroma3.append(max(r_, g_, b_) - min(r_, g_, b_))
            rung3_mean_chroma = sum(chroma3) / max(1, len(chroma3))

            # key_mark_parity: width mark == key (both follow W), style
            # solid ↔ dasharray none, opacity values equal. R1 hard-coded
            # W=1 ("1px"); R2 (D54) measures W ∈ {1, 1.25, 1.5}.
            #
            # NOTE: Chromium rounds HTML `border-width` to integer pixels
            # in `getComputedStyle()` (`border:1.25px solid` reports as
            # `borderWidth='1px'`) but preserves SVG `stroke-width` as
            # written (`stroke-width:1.25` reports `strokeWidth='1.25px'`).
            # So computing parity from getComputedStyle() always reads
            # a false-positive mismatch for any W ≠ 1. The parity check
            # must be made against the CSS SOURCE — both `stroke-width:W`
            # and `border:Wpx solid` are written by _build_mobile() from
            # the same W string, so they're equal by construction.
            import re as _re
            css_src = (_REPO / "site" / CSS_ASSET).read_text()
            css_src = css_src.replace(_OLD_MOBILE, mobile_block or _NEW_MOBILE)
            mm = _re.search(
                r"@media\s*\(max-width:600px\)\s*\{.*?\.sm-map\[data-news-gbr=\"1\"\][^{]*\{[^}]*stroke-width:([\d.]+).*?"
                r"\.sm-legend\s+\.sm-legend-news\s+i\{[^}]*border:([\d.]+)px",
                css_src,
                _re.S,
            )
            if mm:
                src_mark_w = float(mm.group(1))
                src_key_w = float(mm.group(2))
            else:
                src_mark_w = src_key_w = -1.0
            key_mark_parity = (
                abs(src_mark_w - src_key_w) < 1e-6
                and info["gbr_stroke_dasharray"] == "none"
                and info["key_border_style"] in ("solid",)
                and abs(float(info["gbr_stroke_opacity"]) - float(info["key_opacity"])) < 1e-6
            )
            info["key_mark_parity_src_mark_w"] = src_mark_w
            info["key_mark_parity_src_key_w"] = src_key_w

            cell_key = f"{theme}-{locale}"
            digest_uk, w_uk, h_uk = _sha256_and_dims(png_uk)
            digest_leg, w_leg, h_leg = _sha256_and_dims(png_legend)
            uk_name, legend_name = _crop_names(cell_key, theme, baseline=baseline)
            out_dir = Path(cells_dir) if cells_dir else CELLS_DIR
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / uk_name).write_bytes(png_uk)
            (out_dir / legend_name).write_bytes(png_legend)
            theme_results[cell_key] = {
                "applied_theme": info["applied_theme"],
                "applied_locale": info["applied_locale"],
                "viewport_w": info["viewport_w"],
                "data_news_gbr": info["data_news_gbr"],
                "map_data_hi": info["data_hi"],
                "is_hi_count": info["is_hi_count"],
                "scroll_w_le_viewport": info["scroll_w_le_viewport"],
                "gbr_bbox": gbr,
                "gbr_stroke": info["gbr_stroke"],
                "gbr_stroke_width": info["gbr_stroke_width"],
                "gbr_stroke_dasharray": info["gbr_stroke_dasharray"],
                "gbr_stroke_opacity": info["gbr_stroke_opacity"],
                "legend_news_i_border_style": info["key_border_style"],
                "legend_news_i_border_width": info["key_border_width"],
                "legend_news_i_opacity": info["key_opacity"],
                "key_mark_parity": key_mark_parity,
                "uk_box_blue_px": uk_box_blue_px,
                "mark_mean_chroma": mark_mean_chroma,
                "rung3_bbox": r3,
                "rung3_mean_chroma": rung3_mean_chroma,
                "ukzoom_file": f"cells/{uk_name}",
                "ukzoom_sha256": digest_uk,
                "ukzoom_size": [w_uk, h_uk],
                "legend_file": f"cells/{legend_name}",
                "legend_sha256": digest_leg,
                "legend_size": [w_leg, h_leg],
            }
        finally:
            context.close()
    return theme_results


def main():
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(
        description="Capture UK public-news mark on sanctions_map.html mobile."
    )
    parser.add_argument("--width", default="1",
                        help="GBR stroke width, passed verbatim (default: 1)")
    parser.add_argument("--dark-opacity", default=".7",
                        help="dark opacity, passed verbatim (default: .7)")
    parser.add_argument("--light-opacity", default=".55",
                        help="light opacity, passed verbatim (default: .55)")
    parser.add_argument("--baseline", action="store_true",
                        help="skip O28 patch (use origin/main's dashed 13 8 + 1.5)")
    parser.add_argument("--theme", choices=["dark", "light", "both"], default="both")
    parser.add_argument("--locale", choices=["en", "zh", "both"], default="both")
    parser.add_argument("--output", default=None,
                        help="output file name (default: dom.json)")
    args = parser.parse_args()

    themes = THEMES if args.theme == "both" else (args.theme,)
    locales = LOCALES if args.locale == "both" else (args.locale,)
    output_name = args.output or "dom.json"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)

    scratch = Path(tempfile.mkdtemp(prefix="sanctions_map_mobile_key_"))
    # The O28 mobile block (built from the chosen W/OD/OL) is the
    # parity reference — pass it into _capture_one so the source-vs-
    # computed parity check uses the SAME block the scratch CSS carries.
    mobile_block = (
        _build_mobile(args.width, args.dark_opacity, args.light_opacity)
        if not args.baseline else _OLD_MOBILE
    )
    source_commit, page_sha256 = materialize(
        scratch,
        width=args.width,
        dark_opacity=args.dark_opacity,
        light_opacity=args.light_opacity,
        baseline=args.baseline,
    )
    httpd, port = _serve(scratch)
    base = f"http://127.0.0.1:{port}"
    print(
        f"Materialized from {source_commit[:12]} (page {page_sha256[:12]}); "
        f"serving from {scratch} at {base}; "
        f"W={args.width} OD={args.dark_opacity} OL={args.light_opacity} "
        f"baseline={args.baseline} themes={themes} locales={locales}",
        flush=True,
    )

    from playwright.sync_api import sync_playwright  # noqa: PLC0415
    captured_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    dom = {"axes": {
        "themes": list(themes),
        "locales": list(locales),
        "viewport": list(VIEWPORT),
        "device_scale_factor": 1,
    }, "cells": {}}
    with sync_playwright() as m:
        browser = m.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            for locale in locales:
                cells = _capture_one(
                    browser, base, locale=locale, themes=themes,
                    mobile_block=mobile_block, baseline=args.baseline,
                )
                for k, v in cells.items():
                    dom["cells"][k] = v
        finally:
            browser.close()

    httpd.shutdown()
    shutil.rmtree(scratch)

    capture_tool_sha = hashlib.sha256(
        Path(__file__).read_bytes()
    ).hexdigest()

    dom["source_commit"] = source_commit
    dom["page_sha256"] = page_sha256
    dom["generated_at"] = captured_iso
    dom["capture_tool_module_sha256"] = capture_tool_sha
    if args.baseline:
        # R5: materialize(baseline=True) ignores (W, OD, OL) and renders
        # _OLD_MOBILE — the dashed D6 rule. Record THAT block (parsed from
        # the constant, never typed), not the argument defaults.
        import re as _re
        m_old = _re.search(r"stroke-width:([\d.]+);stroke-dasharray:([^}]+)\}", _OLD_MOBILE)
        assert m_old, "_OLD_MOBILE no longer carries stroke-width/dasharray"
        dom["o28_block"] = {
            "width": m_old.group(1),
            "dark_opacity": None,
            "light_opacity": None,
            "stroke_dasharray": m_old.group(2),
            "baseline": True,
            "block": "_OLD_MOBILE",
        }
    else:
        dom["o28_block"] = {
            "width": args.width,
            "dark_opacity": args.dark_opacity,
            "light_opacity": args.light_opacity,
            "baseline": False,
        }
    (OUT_DIR / output_name).write_text(
        json.dumps(dom, indent=2, ensure_ascii=False)
    )

    n_cells = len(dom["cells"])
    print(f"\n{n_cells} cells captured → {OUT_DIR}/{output_name}", flush=True)


if __name__ == "__main__":
    main()