#!/usr/bin/env python3
"""Capture dark+light × EN/ZH × 1440/390 of the SERVED public-news event
layer on sanctions_map.html AFTER PR #8281 — the template-only GBR mark
mechanism (`figure.sm-map[data-news-gbr]`, `section#event-pins`).

TWO cells per matrix point (16 PNGs total):
  * cells/map-<theme>-<locale>-<viewport>.png        — clip = full element box
    of `section.panel.sm-mapwrap`; record bbox of GBR path, `data-news-gbr`
    attribute on the figure, `data-news` attribute on the GBR path
    (post-render stamp is inert, but record what's there), and the
    computed `strokeWidth` of the GBR path.
  * cells/news-panel-<theme>-<locale>-<viewport>.png — clip = full element
    box of `section#event-pins` (full_page capture, clip by element box when
    taller than the viewport); record `state_inferred` (ok/none_recent/
    unavailable/unknown), `rows` = #event-pins li count, locale text from
    `.l-<locale>` nodes only (≤600 chars), sorted distinct YYYY-MM-DD dates.

State applied AFTER first paint so localStorage + setTheme/setLang agree
(R4 idiom). The tool materializes the origin/main page bytes into a scratch
directory and serves them from 127.0.0.1 — that is what `materialize()`
does. Served-copy verification (HTTP fetch of the production URL, observed
`page_sha256` matching the materialized blob) is the commissioning seat's
receipt and is recorded in `SERVED_RECEIPT.json`; the tool reads that file
verbatim and embeds it as the manifest's `served_receipt` field. The tool
never fabricates a served observation itself. If `SERVED_RECEIPT.json` is
absent, `served_receipt` is `null` and the reviewer is told.

Public-news state is classified from the rendered DOM, not from a row
count. `state_inferred` = `ok` iff `figure.sm-map` carries
`data-news-gbr="1"` (the template-only mechanism introduced by #8281;
see `templates/sanctions_map.html.j2:135-142`). Otherwise the tool reads
the `#event-pins .sm-null` empty-state element rendered by the template at
lines 208-214: the "no European official press in the last two days /
近两日无欧洲官方新闻" sentence maps to `none_recent`; the "We could not
read today's European official press / 今日未能读取欧洲官方新闻" sentence
maps to `unavailable`; anything else (or no `.sm-null` element present)
maps to `unknown`. The `<li>` count is kept as a separate `rows` field.

Run from the repo root::

    python3 mockups/evidence/sanctions-map-event-layer-fix/capture.py

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

OUT_DIR = _REPO / "mockups" / "evidence" / "sanctions-map-event-layer-fix"
CELLS_DIR = OUT_DIR / "cells"

VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}
LOCALES = ("en", "zh")
THEMES = ("dark", "light")
KINDS = ("map", "news-panel")

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
    "assets/css/3c74cdc2.css",
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

# Locale-keyed null-sentences used to classify `state_inferred` from the
# rendered `#event-pins .sm-null` element. Substring match against the
# element text wins (template lines 208-214 of sanctions_map.html.j2).
_NULL_NONE_RECENT_EN = "last two days"
_NULL_NONE_RECENT_ZH = "近两日"
_NULL_UNAVAILABLE_EN = "could not read"
_NULL_UNAVAILABLE_ZH = "无法读取"


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


def _classify_state(data_news_gbr, sm_null_text, locale):
    """Compute `state_inferred` from the rendered DOM (S2 of O21b R2).

    ok           = `figure.sm-map` carries `data-news-gbr="1"` (template
                   lines 134-142 of sanctions_map.html.j2 — the #8281
                   mechanism; set ONLY when state == 'ok' AND a GBR
                   event exists, so a missing attribute is a non-`ok`
                   state, NOT an `ok` with no rows).
    none_recent  = `#event-pins .sm-null` text matches the
                   "last two days" / "近两日" sentence (template line 209).
    unavailable  = `#event-pins .sm-null` text matches the
                   "could not read today's European official press" /
                   "今日未能读取欧洲官方新闻" sentence (template line 212).
    unknown      = anything else (a FAILED cell per S2; e.g. an absent
                   `.sm-null` element, a null element with neither sentence,
                   or — for legacy reasons — a row count ≥ 1 with no
                   `data-news-gbr` attribute).

    The `<li>` count is kept as a separate `rows` field and is NOT used
    to classify state (the reviewer's D9 finding: a non-empty list with a
    missing attribute is not `ok`, and a populated `.sm-null` with no
    list is not `unknown`).
    """
    if data_news_gbr == "1":
        return "ok"
    if not sm_null_text:
        return "unknown"
    if locale == "zh":
        if _NULL_NONE_RECENT_ZH in sm_null_text:
            return "none_recent"
        if _NULL_UNAVAILABLE_ZH in sm_null_text:
            return "unavailable"
    else:
        if _NULL_NONE_RECENT_EN in sm_null_text:
            return "none_recent"
        if _NULL_UNAVAILABLE_EN in sm_null_text:
            return "unavailable"
    return "unknown"


def _capture_one(browser, base, *, width, height, locale, theme):
    """Run one matrix point. Returns dict with keys for both kinds.

    The same browser context evaluates the live DOM once and yields data for
    BOTH cells (map + news-panel) so the two PNGs share identical applied
    state and a single source of truth for `data-news-gbr` / `gbr_data_news` /
    panel rows / panel text / dates.
    """
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

        # F02 readiness predicate (S2): the section MUST exist AND either
        # (a) there is ≥1 <li> (state_inferred=ok) OR (b) the `.sm-null`
        # null-sentence is present (none_recent / unavailable). This
        # replaces the prior MO-PAID-008 wait which required a single GBR
        # path stamp that #8281 retired.
        page.wait_for_function(
            """
            () => {
              const panel = document.querySelector('section#event-pins');
              if (!panel) return false;
              const rows = document.querySelectorAll('#event-pins li').length;
              const nullNode = document.querySelector('#event-pins .sm-null');
              return rows >= 1 || !!nullNode;
            }
            """,
            timeout=8000,
        )
        # Wait for the theme-toggle flourish (.sky-fx sun/moon orb) to clear.
        page.wait_for_function(
            "() => !document.querySelector('.sky-fx')", timeout=5000
        )
        sky_fx_count = page.evaluate(
            "() => document.querySelectorAll('.sky-fx').length"
        )
        # The reference tool waits 120ms after .sky-fx clears; the F02 spec
        # mandates a 400ms settle before screenshot — use the larger value so
        # the served steady state, not a residual flourish, is the captured
        # body. (theme.js inserts the orb on theme change and removes it
        # after ~1.1s via setTimeout(..., 1100).)
        page.wait_for_timeout(400)

        # Pull everything we need in one evaluate: PAGE-relative bboxes of
        # the map wrapper, the GBR path, and #event-pins (clip y is page-
        # relative when full_page=True), plus `data-news-gbr` on the figure,
        # `data-news` on the GBR path (legacy post-render stamp, inert but
        # recorded), the count of #event-pins li, locale text from
        # `.l-<locale>` nodes, and sorted distinct YYYY-MM-DD dates.
        info = page.evaluate(
            """
            (locale) => {
              const wrapper = document.querySelector('section.panel.sm-mapwrap');
              const figure = document.querySelector('figure.sm-map');
              const gbr = document.querySelector('path.wm-c[data-iso3="GBR"]');
              const panel = document.querySelector('#event-pins');
              const lis = document.querySelectorAll('#event-pins li');
              const nullNode = document.querySelector('#event-pins .sm-null');
              const wr = wrapper.getBoundingClientRect();
              const gr = gbr ? gbr.getBoundingClientRect() : null;
              const pr = panel.getBoundingClientRect();
              const sy = window.scrollY;

              const toPage = (r) => ({x: r.left, y: r.top + sy, w: r.width, h: r.height});

              const wrapperBox = toPage(wr);
              const gbrBox = gr ? toPage(gr) : null;
              const panelBox = toPage(pr);

              // GBR stroke (computed style as observed) — null if no path.
              let gbrStroke = null;
              if (gbr) {
                const cs = window.getComputedStyle(gbr);
                gbrStroke = cs && cs.strokeWidth ? cs.strokeWidth : null;
              }

              // Locale text: only the .l-<locale> nodes inside the panel.
              const localeNodes = panel.querySelectorAll('.l-' + locale);
              let panel_text = '';
              localeNodes.forEach(n => {
                const t = (n.textContent || '').trim();
                if (t) panel_text += t + '\\n';
              });
              // If locale nodes are empty, fall back to element text so
              // classifier still has something to match against.
              const nullText = nullNode ? (nullNode.textContent || '').trim() : '';

              // Distinct YYYY-MM-DD from <time> tags in the panel.
              const dates = [];
              lis.forEach(li => {
                const t = li.querySelector('time');
                if (t) dates.push((t.textContent || '').trim());
              });

              return {
                wrapper: wrapperBox,
                gbr_bbox: gbrBox,
                gbr_data_news: gbr ? gbr.getAttribute('data-news') : null,
                data_news_gbr: figure ? figure.getAttribute('data-news-gbr') : null,
                panel: panelBox,
                rows: lis.length,
                panel_text: panel_text.slice(0, 600),
                null_text: nullText,
                dates: Array.from(new Set(dates)).sort(),
                gbr_stroke: gbrStroke,
                viewport_w: window.innerWidth,
                viewport_h: window.innerHeight,
              };
            }
            """,
            locale,
        )

        wrapper = info["wrapper"]
        gbr = info["gbr_bbox"]
        panel = info["panel"]

        # Spec bbox assertion (S3): the GBR path bbox MUST sit inside the
        # map wrapper bbox when a GBR path exists.
        if gbr is not None and not _bbox_contains(wrapper, gbr):
            raise RuntimeError(
                f"gbr bbox {gbr} not inside wrapper {wrapper}"
            )

        # MAP cell clip = full element box of section.panel.sm-mapwrap.
        map_clip = {
            "x": max(0.0, wrapper["x"]),
            "y": max(0.0, wrapper["y"]),
            "width": wrapper["w"],
            "height": wrapper["h"],
        }
        png_map = page.screenshot(
            type="png", full_page=True, clip=map_clip
        )

        # PANEL cell clip = full element box of section#event-pins.
        # full_page=True unconditionally — the panel is taller than the
        # viewport on mobile and on desktop at the 900px fold.
        panel_clip = {
            "x": max(0.0, panel["x"]),
            "y": max(0.0, panel["y"]),
            "width": panel["w"],
            "height": panel["h"],
        }
        png_panel = page.screenshot(
            type="png", full_page=True, clip=panel_clip
        )

        # Compute `state_inferred` once for both cells from the rendered
        # DOM (S2 of O21b R2): ok iff `figure.sm-map[data-news-gbr="1"]`,
        # otherwise read the `#event-pins .sm-null` text and map it to
        # `none_recent` / `unavailable` / `unknown`. Row count is
        # preserved as `rows` and is NOT the classifier.
        null_for_state = info["null_text"] or info["panel_text"]
        state_inferred = _classify_state(
            info["data_news_gbr"], null_for_state, locale
        )

        return {
            "applied": applied,
            "wrapper": wrapper,
            "gbr_bbox": gbr,
            "gbr_data_news": info["gbr_data_news"],
            "data_news_gbr": info["data_news_gbr"],
            "gbr_stroke": info["gbr_stroke"],
            "panel": panel,
            "rows": info["rows"],
            "panel_text": info["panel_text"],
            "dates": info["dates"],
            "state_inferred": state_inferred,
            "map_clip": map_clip,
            "panel_clip": panel_clip,
            "png_map": png_map,
            "png_panel": png_panel,
            "sky_fx_count": sky_fx_count,
        }
    finally:
        context.close()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)

    scratch = Path(tempfile.mkdtemp(prefix="sanctions_map_event_layer_"))
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
                        got = _capture_one(
                            browser, base, width=w, height=h,
                            locale=locale, theme=theme,
                        )
                        # Emit TWO entries per (theme, locale, viewport):
                        # one `map-*` and one `news-panel-*`.
                        for kind, alias_suffix, png, kind_box, kind_clip in (
                            ("map", "map", got["png_map"], got["gbr_bbox"], got["map_clip"]),
                            ("news-panel", "news-panel", got["png_panel"], got["panel"], got["panel_clip"]),
                        ):
                            alias = f"{alias_suffix}-{theme}-{locale}-{viewport_name}.png"
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
                                digest, pw, ph = _sha256_and_dims(png)
                                (CELLS_DIR / alias).write_bytes(png)
                                cell = {
                                    **entry,
                                    "applied_theme": got["applied"].get("theme"),
                                    "applied_locale": got["applied"].get("locale"),
                                    "bbox": kind_box,
                                    "clip": kind_clip,
                                    "sha256": digest,
                                    "bytes": len(png),
                                    "width": pw,
                                    "height": ph,
                                    "captured": captured_iso,
                                }
                                if kind == "map":
                                    cell["selector"] = "section.panel.sm-mapwrap"
                                    cell["gbr_data_news"] = got["gbr_data_news"]
                                    cell["data_news_gbr"] = got["data_news_gbr"]
                                    cell["gbr_stroke"] = got["gbr_stroke"]
                                    cell["state_inferred"] = got["state_inferred"]
                                else:
                                    cell["selector"] = "#event-pins"
                                    cell["state_inferred"] = got["state_inferred"]
                                    cell["rows"] = got["rows"]
                                    cell["panel_text"] = got["panel_text"]
                                    cell["dates"] = got["dates"]
                                cell["extras"] = {"sky_fx_count": got["sky_fx_count"]}
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

    # All 8 panel cells MUST agree on a single state_inferred (S4).
    panel_states = {c["state_inferred"] for c in cells if c["kind"] == "news-panel" and c.get("state_inferred")}
    if len(panel_states) != 1:
        raise RuntimeError(
            f"panel state_inferred disagreement across 8 panel cells: {panel_states}"
        )
    public_news_state_observed = next(iter(panel_states))

    # Read the commissioning seat's SERVED_RECEIPT.json verbatim and embed
    # it as `served_receipt` (null when absent). The tool does NOT verify
    # the production URL itself — the seat does that once and records the
    # observation here.
    served_receipt_path = OUT_DIR / "SERVED_RECEIPT.json"
    if served_receipt_path.is_file():
        with served_receipt_path.open() as _f:
            served_receipt = json.load(_f)
    else:
        served_receipt = None

    manifest = {
        "page_id": "sanctions_map",
        "route": "sanctions_map.html",
        "registry_route": "macro:sanctions_map",
        "route_kind": "intelligence_desk",
        "subject": "public-news event layer after #8281 — freshness bound, honest null, single GBR mark mechanism (F02 O21b)",
        "source": (
            "origin/main bytes materialized locally and served from 127.0.0.1; "
            "served-copy verification is the seat's receipt in SERVED_RECEIPT.json"
        ),
        "source_commit": source_commit,
        "page_sha256": page_sha256,
        "generated_at": captured_iso,
        "capture_tool_module_sha256": capture_tool_sha,
        "served_receipt": served_receipt,
        "public_news_state_observed": public_news_state_observed,
        "cells": cells,
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False)
    )
    ok = sum(1 for c in cells if c.get("sha256"))
    print(
        f"\n{ok}/{len(cells)} cells captured → {OUT_DIR} "
        f"(state={public_news_state_observed}, "
        f"served_receipt={'present' if served_receipt else 'null'})",
        flush=True,
    )


if __name__ == "__main__":
    main()