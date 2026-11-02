#!/usr/bin/env python3
"""Capture dark+light × EN/ZH × 1440/390 of the LEGIBLE UK press mark on
sanctions_map.html AFTER PR #8292 — the radius-fixed legend swatch
(`border-radius:0` on `.sm-legend .sm-legend-news i`), the non-scaling
dashed GBR outline (`figure.sm-map[data-news-gbr="1"]`), the legend news
row, the 2-day heading, the ZH note, and the seven-row public-news list.

ONE cell per matrix point (16 PNGs total):
  * cells/<kind>-<theme>-<locale>-<viewport>.png  — clip = full element
    box of `section.panel.sm-mapwrap` (kind=`map`) or `section#event-pins`
    (kind=`news-panel`); record the GBR path stroke (computed style), the
    `data-news-gbr` attribute on the figure, the legend news swatch's
    computed `borderStyle`, the count and locale-bound text of the
    `#event-pins li`, the `data-news-gbr` attribute on `figure.sm-map`,
    and the page-relative bboxes of every clipped element.

Source = fixture render. The R2 radius patch is unmerged, so the served
route would not show it; we materialize the page bytes from a fresh
Jinja2 env wired with `templates/sanctions_map.html.j2` and a
`monkeypatch`-style fixture for `engine.europe_news_intel._events_path`
plus the four OFAC helpers copied from
`tests/test_sanctions_map_event_pins.py` (S2). The HTML + every local
asset the rendered HTML references (`<link href>`/`<script src>` without a
scheme, `?v=` stripped) are copied from `templates/` into the scratch
dir; the serve fails closed naming any missing asset. Theme + locale are
applied BEFORE navigation via `page.add_init_script` so the inlined
`data-theme`/`data-lang` set on `<html>` is consistent with the localStorage
keys `templates/theme.js` reads — never call `window.setTheme` after
load (DSC lesson from #8289: that bakes the toggle flourish into the
still).

Run from the repo root::

    python3 mockups/evidence/sanctions-map-news-mark-legibility/capture.py

No credentials. No network beyond the bundled static fixtures served
from a local python http.server. Reproducible end-to-end.
"""
from __future__ import annotations

import csv
import hashlib
import http.server
import io
import json
import re
import shutil
import socketserver
import struct
import subprocess
import sys
import tempfile
import threading
import yaml
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

_REPO = Path(__file__).resolve().parent.parent.parent.parent  # mockups/.../capture.py -> repo root
sys.path.insert(0, str(_REPO))

OUT_DIR = _REPO / "mockups" / "evidence" / "sanctions-map-news-mark-legibility"
CELLS_DIR = OUT_DIR / "cells"

VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}
LOCALES = ("en", "zh")
THEMES = ("dark", "light")
KINDS = ("map", "news-panel")

# Local relative paths the rendered page references. Cache-busting `?v=`
# query strings are stripped; the bare paths are what theme.js, the link
# rel="stylesheet" href attrs, and the script src attrs (modulo v) load.
# Includes the nav include's chrome (the template includes _site_nav.html.j2
# which references theme.js/navigation-refresh.css/nav_market.js).
ASSET_RELPATHS = (
    "theme.css",
    "theme.js",
    "navigation-refresh.css",
    "nav_market.js",
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

# State applied BEFORE navigation so the inlined <head> script (line 13
# of sanctions_map.html.j2) agrees with localStorage + theme.js on theme
# and lang. Mirrors the F02 idiom: html data-theme/data-lang plus the
# two localStorage keys theme.js reads (`theme` and `lang`).
#
# IMPORTANT — this is an IIFE (note the trailing `();`). Playwright's
# `add_init_script` inserts the source verbatim into a `<script>` tag;
# without an IIFE wrapper the script would *define* a function but
# never *execute* it, leaving localStorage empty when the page's
# inline script runs.
#
# IMPORTANT — `document.documentElement` is `null` when the init script
# runs (init scripts fire before the parser builds the DOM), so we
# MUST NOT call `documentElement.setAttribute` here. Seeding
# `localStorage` only is enough: the page's inline <head> script reads
# it and stamps `data-theme`/`data-lang` on <html> before any CSS loads.
_STATE_SEED = """
(function () {
  try {
    var m = (location.search || '').match(/[?&]t=([^&]+)/);
    var l = (location.search || '').match(/[?&]l=([^&]+)/);
    if (m) {
      localStorage.setItem('theme', m[1]);
      localStorage.removeItem('themeAuto');
    }
    if (l) {
      localStorage.setItem('lang', l[1]);
    }
  } catch (e) {}
})();
"""


# --------------------------------------------------------------------------- #
# Fixture helpers — copied from tests/test_sanctions_map_event_pins.py so the
# capture tool's render path is byte-identical to what the test suite
# verifies. No monkeypatch — we patch `engine.europe_news_intel._events_path`
# in-place for the duration of `materialize()` and revert afterwards.
# --------------------------------------------------------------------------- #
def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _sdn_csv(codes: list[str]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    for i, code in enumerate(codes):
        row = [""] * 8
        row[0] = str(i)
        row[3] = code
        w.writerow(row)
    return buf.getvalue()


def _write_ofac(tmp_path: Path) -> tuple[Path, Path, Path]:
    sdn = tmp_path / "sdn.csv"
    sdn.write_text(_sdn_csv(["RUSSIA-EO14024"]), encoding="utf-8")
    meta = tmp_path / "meta.json"
    meta.write_text("{}", encoding="utf-8")
    cfg = tmp_path / "cfg.yml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "programs": [
                    {
                        "code": "RUSSIA-EO14024",
                        "iso3": "RUS",
                        "country_name_en": "Russia",
                        "country_name_zh": "俄罗斯",
                        "name_en": "Russia — EO 14024",
                        "name_zh": "俄罗斯 — 第14024号行政命令",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return sdn, meta, cfg


def _write_events_parquet(path: Path) -> None:
    """Seven-row fixture the page renders in full (S4 `li count == 7`).

    The engine's `_public_news` keeps only the LATEST `asof` day
    (`engine/sanctions_map.py:286-288`). To render all 7 rows we set
    every row's `asof` to today (`2026-10-02`); the seendate column is
    allowed to vary across the freshness window so the rows demonstrably
    span two dates (the FROZEN SPEC's "asof/`seendate` spanning TWO
    dates"). 4 UK + 3 EU; at least one UK and one EU title ≥ 90
    characters so wrapping at 390×844 is exercised.

    Hard-coded dates (NOT `_today_utc()`) so the fixture is stable across
    re-runs — the capture tool is a verification artifact, not a
    liveness probe, and a re-run must produce the same hashes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    asof = "2026-10-02"
    seendate_old = "2026-10-01"
    rows = [
        # UK — long title ≥ 90 chars (seendate on the second date so the
        # list demonstrably spans both 10-01 and 10-02)
        {
            "title": "Monetary Policy Committee votes to hold Bank Rate at four percent with a divided outlook on services inflation",
            "url": "https://www.bankofengland.co.uk/news/2026/rate-oct-1",
            "source": "boe_news",
            "jurisdiction": "UK",
            "asof": asof,
            "seendate": seendate_old,
        },
        {
            "title": "Financial Stability Report highlights gilt market depth and sterling funding conditions",
            "url": "https://www.bankofengland.co.uk/news/2026/fsr-oct-1",
            "source": "boe_news",
            "jurisdiction": "UK",
            "asof": asof,
            "seendate": seendate_old,
        },
        # UK — second date
        {
            "title": "Bank Rate held; MPC statement on second-round effects",
            "url": "https://www.bankofengland.co.uk/news/2026/rate-oct-2",
            "source": "boe_news",
            "jurisdiction": "UK",
            "asof": asof,
            "seendate": asof,
        },
        {
            "title": "PRA publishes supervisory statement on liquidity risk",
            "url": "https://www.bankofengland.co.uk/news/2026/pra-oct-2",
            "source": "boe_news",
            "jurisdiction": "UK",
            "asof": asof,
            "seendate": asof,
        },
        # EU — long title ≥ 90 chars
        {
            "title": "Commission publishes a trade notice on safeguards for steel imports following a review of the European steel market",
            "url": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1",
            "source": "ec_presscorner",
            "jurisdiction": "EU",
            "asof": asof,
            "seendate": seendate_old,
        },
        {
            "title": "ECB monetary policy statement — fourth session of the year on inflation outlook",
            "url": "https://www.ecb.europa.eu/press/pr/date/2026/html/ecb.pr2601~1.en.html",
            "source": "ec_presscorner",
            "jurisdiction": "EU",
            "asof": asof,
            "seendate": seendate_old,
        },
        {
            "title": "Eurostat release on industrial producer prices",
            "url": "https://ec.europa.eu/eurostat/news/whats-new",
            "source": "ec_presscorner",
            "jurisdiction": "EU",
            "asof": asof,
            "seendate": asof,
        },
    ]
    pd.DataFrame(rows).to_parquet(path, index=False)


# --------------------------------------------------------------------------- #
# Materialize — render via Jinja + OFAC fixtures into a scratch dir, copy
# referenced local assets. Returns source_commit + page_sha256.
# --------------------------------------------------------------------------- #
def _referenced_asset_paths(html_text: str) -> list[str]:
    """Find every `<link href=...>` and `<script src=...>` whose target is
    a relative path (no scheme, no leading `//`); strip any `?v=` query
    string. Fail-closed (raises KeyError on a malformed attribute is not
    what we want here — the caller's `fail-closed naming any missing
    asset` is the real safety net via `(scratch / relpath).write_bytes`
    raising)."""
    out: list[str] = []
    for m in re.finditer(
        r'<(?:link[^>]*href=["\']|script[^>]*src=["\'])([^"\' >]+)',
        html_text,
    ):
        ref = m.group(1)
        if ref.startswith(("http://", "https://", "//", "data:", "/", "#")):
            continue
        ref = ref.split("?", 1)[0]
        if ref:
            out.append(ref)
    # Dedupe preserving order.
    seen = set()
    return [r for r in out if not (r in seen or seen.add(r))]


def _git_blob(ref: str, relpath: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{ref}:{relpath}"], cwd=_REPO
    )


def _render_fixture(tmp_path: Path) -> tuple[str, str, Path, Path, Path]:
    """Render `sanctions_map.html.j2` against an in-memory OFAC + news
    fixture. Returns (html, page_sha256, sdn, meta, cfg) — the latter
    three so we can keep the parquet+SDN alive for the duration of the
    capture (the engine reads them every request, not at module import)."""
    from engine import europe_news_intel, sanctions_map
    from engine.i18n import t, td, tr
    from engine.sanctions_map import rungs_for

    parquet = tmp_path / "europe_news_vector" / "events.parquet"
    _write_events_parquet(parquet)
    # Pin the engine's news path to our fixture for the duration of the
    # render. The path is a function; we wrap it to return our parquet
    # unconditionally. This is what `tests/test_sanctions_map_event_pins.py`
    # does via `monkeypatch.setattr` — we use plain attribute swap since
    # we're a standalone tool.
    _orig_events_path = europe_news_intel._events_path
    europe_news_intel._events_path = lambda: parquet
    try:
        sdn, meta, cfg = _write_ofac(tmp_path)
        vm = sanctions_map.build(sdn_file=sdn, meta_file=meta, programs_config=cfg)
    finally:
        europe_news_intel._events_path = _orig_events_path

    env = Environment(loader=FileSystemLoader(str(_REPO / "templates")), autoescape=True)
    env.globals.update(tr=tr, td=td, t=t)
    rungs = rungs_for(vm, {"RUS", "GBR", "USA"})
    html = env.get_template("sanctions_map.html.j2").render(vm=vm, rungs=rungs)
    page_sha256 = hashlib.sha256(html.encode("utf-8")).hexdigest()
    return html, page_sha256, sdn, meta, cfg


def materialize(scratch: Path):
    """Render the fixture into <scratch>/sanctions_map.html + copy
    referenced assets. Returns (source_commit, page_sha256)."""
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=_REPO
    ).decode().strip()
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "assets" / "css").mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="sanctions_map_fixture_") as _td:
        td_path = Path(_td)
        html, page_sha256, _sdn, _meta, _cfg = _render_fixture(td_path)

    (scratch / "sanctions_map.html").write_text(html, encoding="utf-8")

    referenced = _referenced_asset_paths(html)
    missing: list[str] = []

    def _copy(relpath: str) -> None:
        """Copy `relpath` from `templates/` or `site/` at HEAD into
        `<scratch>/<relpath>`. Records in `missing` if neither has it."""
        candidates = [f"templates/{relpath}", f"site/{relpath}"]
        blob: bytes | None = None
        used_ref: str | None = None
        for ref in candidates:
            try:
                blob = _git_blob("HEAD", ref)
                used_ref = ref
                break
            except subprocess.CalledProcessError:
                continue
        if blob is None or used_ref is None:
            missing.append(relpath)
            return
        dest = scratch / relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob)

    # 1. Static refs in the rendered HTML.
    for relpath in referenced:
        _copy(relpath)

    # 2. Hard-required ASSET_RELPATHS — assets injected by theme.js
    # (navigation-refresh.css, nav_market.js, wh_banner.js) or referenced
    # via the nav include but not in the static <link>/<script> scan.
    for relpath in ASSET_RELPATHS:
        if not (scratch / relpath).is_file():
            _copy(relpath)

    # Hard-require ASSET_RELPATHS too — a referenced asset only checked
    # via the rendered HTML would miss a referenced-via-`{% include %}` or
    # referenced-via-`window.X` asset that the browser only fails on
    # after a deeper walk. The copying loop above already attempted each
    # one; this is the final fail-closed gate.
    for relpath in ASSET_RELPATHS:
        if not (scratch / relpath).is_file():
            missing.append(relpath)

    if missing:
        raise RuntimeError(
            "missing assets for fixture serve (page will 404): " + ", ".join(missing)
        )

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


def _sha256_and_dims(png: bytes):
    digest = hashlib.sha256(png).hexdigest()
    if png[:8] == b"\x89PNG\r\n\x1a\n" and png[12:16] == b"IHDR":
        w, h = struct.unpack(">II", png[16:24])
    else:
        w, h = 0, 0
    return digest, w, h


def _assert_dom_metrics(info: dict, *, kind: str, locale: str, viewport_name: str) -> None:
    """S4 assertions — fail-closed: raise on any miss BEFORE the cell is
    written. The same predicates are recorded under `dom` in the
    manifest so the evidence reader can verify them after the fact."""
    # GBR mark exists (figure + path).
    assert info["figure_news_gbr"] == "1", (
        f"[{kind}/{locale}/{viewport_name}] figure.sm-map data-news-gbr "
        f"expected '1', got {info['figure_news_gbr']!r}"
    )
    assert info["gbr_exists"], (
        f"[{kind}/{locale}/{viewport_name}] GBR path .wm-c[data-iso3='GBR'] missing"
    )
    gbr_style = info["gbr_style"]
    assert gbr_style["vectorEffect"] == "non-scaling-stroke", (
        f"[{kind}/{locale}/{viewport_name}] GBR vector-effect "
        f"expected 'non-scaling-stroke', got {gbr_style['vectorEffect']!r}"
    )
    assert gbr_style["strokeDasharray"] != "none", (
        f"[{kind}/{locale}/{viewport_name}] GBR stroke-dasharray expected "
        f"non-'none', got {gbr_style['strokeDasharray']!r}"
    )
    expected_sw = "1.5px" if viewport_name == "mobile" else "1.25px"
    assert gbr_style["strokeWidth"] == expected_sw, (
        f"[{kind}/{locale}/{viewport_name}] GBR stroke-width expected "
        f"{expected_sw!r}, got {gbr_style['strokeWidth']!r}"
    )

    # Legend news swatch (single instance, dashed border).
    assert info["legend_news_count"] == 1, (
        f"[{kind}/{locale}/{viewport_name}] .sm-legend-news count expected 1, "
        f"got {info['legend_news_count']}"
    )
    assert info["legend_news_i_style"]["borderStyle"] == "dashed", (
        f"[{kind}/{locale}/{viewport_name}] .sm-legend-news i border-style "
        f"expected 'dashed', got {info['legend_news_i_style']['borderStyle']!r}"
    )

    # ZH-only note sm-orig.
    sm_orig_count = info["sm_orig_count"]
    if locale == "zh":
        assert sm_orig_count == 1, (
            f"[{kind}/{locale}/{viewport_name}] .sm-orig count expected 1 (zh), "
            f"got {sm_orig_count}"
        )
        assert info["sm_orig_visible"], (
            f"[{kind}/{locale}/{viewport_name}] .sm-orig must be visible "
            f"(offsetParent != null) in zh"
        )
    else:
        assert sm_orig_count == 1, (
            f"[{kind}/{locale}/{viewport_name}] .sm-orig count expected 1 "
            f"(zh-only node, hidden in en via .l-zh display rule), got "
            f"{sm_orig_count}"
        )
        assert info["sm_orig_visible"] is False, (
            f"[{kind}/{locale}/{viewport_name}] .sm-orig must NOT be visible "
            f"(offsetParent == null) in en"
        )

    # Panel h2 text contains the locale-bound phrase.
    h2 = info["h2_text"]
    if locale == "zh":
        assert "近两日" in h2, (
            f"[{kind}/{locale}/{viewport_name}] h2 expected '近两日' substring, "
            f"got {h2!r}"
        )
    else:
        assert "last 2 days" in h2, (
            f"[{kind}/{locale}/{viewport_name}] h2 expected 'last 2 days' "
            f"substring, got {h2!r}"
        )

    # 7 event rows.
    assert info["li_count"] == 7, (
        f"[{kind}/{locale}/{viewport_name}] #event-pins li count expected 7, "
        f"got {info['li_count']}"
    )

    # No horizontal scroll.
    assert info["scroll_w"] <= info["viewport_w"], (
        f"[{kind}/{locale}/{viewport_name}] documentElement.scrollWidth "
        f"{info['scroll_w']} > window.innerWidth {info['viewport_w']}"
    )

    # Every .sm-events li > span sits on a single line (no wrap).
    assert all(info["single_line_spans"]), (
        f"[{kind}/{locale}/{viewport_name}] at least one .sm-events li > span "
        f"wrapped; expected exactly one client rect per span"
    )


def _capture_one(browser, base, *, width: int, height: int, locale: str, theme: str):
    """Run one matrix point; emit map + news-panel cells + DOM metrics.

    Theme + locale are applied BEFORE load via `page.add_init_script` so
    the inlined <head> script (line 13 of sanctions_map.html.j2) and
    templates/theme.js both agree on `data-theme`/`data-lang` from the
    first paint. After load we additionally re-apply via setTheme/setLang
    as belt-and-braces (theme.js sets these on its DOMContentLoaded
    handler, but a race on first paint would expose a flash of dark
    theme in light captures)."""
    context = browser.new_context(
        viewport={"width": width, "height": height},
        locale="zh-CN" if locale == "zh" else "en-US",
        color_scheme=theme,
        device_scale_factor=1,
        reduced_motion="reduce",
    )
    context.add_init_script(_STATE_SEED.strip())
    page = context.new_page()
    try:
        url = f"{base}/sanctions_map.html?t={theme}&l={locale}"
        resp = page.goto(url, wait_until="load", timeout=30000)
        if resp is None or not resp.ok:
            raise RuntimeError(f"HTTP {getattr(resp, 'status', 'none')}")

        # F02 readiness predicate (S2): the section MUST exist AND the
        # row count must be the full 7 (the fixture is fixed; an empty
        # list means our news path didn't reach the template).
        page.wait_for_function(
            """
            () => {
              const panel = document.querySelector('section#event-pins');
              if (!panel) return false;
              return document.querySelectorAll('#event-pins li').length === 7;
            }
            """,
            timeout=8000,
        )

        # Theme/locale DOM attributes — assert they are the requested ones
        # (the inlined <head> script + our init seed + setTheme/setLang
        # all converge here). Fail closed if any disagrees.
        applied = page.evaluate(
            """
            () => {
              const html = document.documentElement;
              const theme = html.getAttribute('data-theme');
              const lang = html.getAttribute('data-lang');
              let setT = false, setL = false;
              try { setT = !!window.setTheme; } catch (e) {}
              try { setL = !!window.setLang; } catch (e) {}
              return {theme, lang, setTheme: setT, setLang: setL};
            }
            """
        )
        if applied.get("theme") != theme or applied.get("lang") != locale:
            raise RuntimeError(
                f"state mismatch: requested theme={theme} locale={locale} "
                f"observed {applied!r}"
            )

        # Wait for the theme-toggle flourish (.sky-fx sun/moon orb) to
        # clear (DSC lesson from #8289 — never bake it into the still).
        page.wait_for_function(
            "() => !document.querySelector('.sky-fx')", timeout=5000
        )
        sky_fx_count = page.evaluate(
            "() => document.querySelectorAll('.sky-fx').length"
        )
        # Belt-and-braces settle; per the reference tool's idiom.
        page.wait_for_timeout(400)

        # Pull everything S4 needs in one evaluate.
        info = page.evaluate(
            """
            (locale) => {
              const wrapper = document.querySelector('section.panel.sm-mapwrap');
              const figure = document.querySelector('figure.sm-map');
              const gbr = document.querySelector('path.wm-c[data-iso3="GBR"]');
              const panel = document.querySelector('#event-pins');
              const lis = document.querySelectorAll('#event-pins li');
              const legendNewsItems = document.querySelectorAll('.sm-legend-news');
              const legendNewsI = document.querySelector('.sm-legend-news i');
              const smOrig = document.querySelector('.sm-orig');
              const h2 = panel ? panel.querySelector('h2') : null;

              const sy = window.scrollY;
              const toPage = (r) => ({x: r.left, y: r.top + sy, w: r.width, h: r.height});
              const wrapperBox = wrapper ? toPage(wrapper.getBoundingClientRect()) : null;
              const panelBox = panel ? toPage(panel.getBoundingClientRect()) : null;

              let gbr_style = null;
              if (gbr) {
                const cs = window.getComputedStyle(gbr);
                gbr_style = {
                  vectorEffect: cs.vectorEffect,
                  strokeDasharray: cs.strokeDasharray,
                  strokeWidth: cs.strokeWidth,
                };
              }
              let legend_i_style = null;
              if (legendNewsI) {
                const cs = window.getComputedStyle(legendNewsI);
                legend_i_style = {
                  borderStyle: cs.borderStyle,
                  borderRadius: cs.borderRadius,
                };
              }
              let sm_orig_visible = null;
              if (smOrig) {
                sm_orig_visible = smOrig.offsetParent !== null;
              }

              // Every .sm-events li > span must be on a single line.
              const spans = panel ? panel.querySelectorAll('.sm-events li > span') : [];
              const single_line = [];
              spans.forEach(s => {
                single_line.push(s.getClientRects().length === 1);
              });

              return {
                wrapper: wrapperBox,
                panel: panelBox,
                figure_news_gbr: figure ? figure.getAttribute('data-news-gbr') : null,
                gbr_exists: !!gbr,
                gbr_style,
                legend_news_count: legendNewsItems.length,
                legend_news_i_style: legend_i_style,
                sm_orig_count: smOrig ? 1 : 0,
                sm_orig_visible,
                h2_text: h2 ? h2.textContent : '',
                li_count: lis.length,
                single_line_spans: single_line,
                scroll_w: document.documentElement.scrollWidth,
                viewport_w: window.innerWidth,
                viewport_h: window.innerHeight,
              };
            }
            """,
            locale,
        )
        return {
            "info": info,
            "wrapper": info["wrapper"],
            "panel": info["panel"],
            "applied": applied,
            "sky_fx_count": sky_fx_count,
        }
    finally:
        context.close()


def _take_clips(browser, base, *, width, height, locale, theme, wrapper, panel):
    """Re-navigate (we already closed the context above) is too expensive;
    instead take both clips in a single page lifetime. Returns png_map +
    png_panel. S4 has already been checked in `_capture_one` — this
    function trusts the prior DOM read and just shoots."""
    context = browser.new_context(
        viewport={"width": width, "height": height},
        locale="zh-CN" if locale == "zh" else "en-US",
        color_scheme=theme,
        device_scale_factor=1,
        reduced_motion="reduce",
    )
    context.add_init_script(_STATE_SEED.strip())
    page = context.new_page()
    try:
        url = f"{base}/sanctions_map.html?t={theme}&l={locale}"
        page.goto(url, wait_until="load", timeout=30000)
        page.wait_for_function(
            """
            () => {
              const panel = document.querySelector('section#event-pins');
              return panel && document.querySelectorAll('#event-pins li').length === 7;
            }
            """,
            timeout=8000,
        )
        page.wait_for_function(
            "() => !document.querySelector('.sky-fx')", timeout=5000
        )
        page.wait_for_timeout(400)

        map_clip = {
            "x": max(0.0, wrapper["x"]),
            "y": max(0.0, wrapper["y"]),
            "width": wrapper["w"],
            "height": wrapper["h"],
        }
        png_map = page.screenshot(type="png", full_page=True, clip=map_clip)
        panel_clip = {
            "x": max(0.0, panel["x"]),
            "y": max(0.0, panel["y"]),
            "width": panel["w"],
            "height": panel["h"],
        }
        png_panel = page.screenshot(type="png", full_page=True, clip=panel_clip)
        return png_map, png_panel
    finally:
        context.close()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)

    scratch = Path(tempfile.mkdtemp(prefix="sanctions_map_news_mark_legibility_"))
    source_commit, page_sha256 = materialize(scratch)
    httpd, port = _serve(scratch)
    base = f"http://127.0.0.1:{port}"
    print(
        f"Materialized fixture render from HEAD {source_commit[:12]} "
        f"(page {page_sha256[:12]}); serving from {scratch} at {base}",
        flush=True,
    )

    from playwright.sync_api import sync_playwright  # noqa: PLC0415
    cells: list[dict] = []
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
                        # Pass 1 — DOM read + S4 assertions (fail closed
                        # BEFORE any clip is taken).
                        dom = _capture_one(
                            browser, base, width=w, height=h,
                            locale=locale, theme=theme,
                        )
                        info = dom["info"]
                        _assert_dom_metrics(
                            info,
                            kind="matrix",  # both kinds share these invariants
                            locale=locale,
                            viewport_name=viewport_name,
                        )

                        # Pass 2 — clips, in a fresh context to avoid
                        # any settle-state drift from the DOM read.
                        png_map, png_panel = _take_clips(
                            browser, base, width=w, height=h,
                            locale=locale, theme=theme,
                            wrapper=dom["wrapper"],
                            panel=dom["panel"],
                        )

                        for kind, png, box in (
                            ("map", png_map, dom["wrapper"]),
                            ("news-panel", png_panel, dom["panel"]),
                        ):
                            alias = f"{kind}-{theme}-{locale}-{viewport_name}.png"
                            digest, pw, ph = _sha256_and_dims(png)
                            (CELLS_DIR / alias).write_bytes(png)
                            cell = {
                                "file": f"cells/{alias}",
                                "kind": kind,
                                "theme": theme,
                                "locale": locale,
                                "viewport": viewport_name,
                                "viewport_width": w,
                                "viewport_height": h,
                                "selector": (
                                    "section.panel.sm-mapwrap" if kind == "map"
                                    else "section#event-pins"
                                ),
                                "applied_theme": dom["applied"].get("theme"),
                                "applied_locale": dom["applied"].get("lang"),
                                "bbox": box,
                                "sha256": digest,
                                "bytes": len(png),
                                "width": pw,
                                "height": ph,
                                "captured": captured_iso,
                                "extras": {"sky_fx_count": dom["sky_fx_count"]},
                                "dom": {
                                    "figure_data_news_gbr": info["figure_news_gbr"],
                                    "gbr_exists": info["gbr_exists"],
                                    "gbr_vector_effect": (
                                        info["gbr_style"]["vectorEffect"]
                                        if info["gbr_style"] else None
                                    ),
                                    "gbr_stroke_dasharray": (
                                        info["gbr_style"]["strokeDasharray"]
                                        if info["gbr_style"] else None
                                    ),
                                    "gbr_stroke_width": (
                                        info["gbr_style"]["strokeWidth"]
                                        if info["gbr_style"] else None
                                    ),
                                    "legend_news_count": info["legend_news_count"],
                                    "legend_news_i_border_style": (
                                        info["legend_news_i_style"]["borderStyle"]
                                        if info["legend_news_i_style"] else None
                                    ),
                                    "legend_news_i_border_radius": (
                                        info["legend_news_i_style"]["borderRadius"]
                                        if info["legend_news_i_style"] else None
                                    ),
                                    "sm_orig_count": info["sm_orig_count"],
                                    "sm_orig_visible": info["sm_orig_visible"],
                                    "h2_text": info["h2_text"],
                                    "li_count": info["li_count"],
                                    "single_line_spans": all(
                                        info["single_line_spans"]
                                    ) if info["single_line_spans"] else True,
                                    "scroll_w_le_viewport": (
                                        info["scroll_w"] <= info["viewport_w"]
                                    ),
                                },
                            }
                            cells.append(cell)
                            print(
                                f"  ✓ {alias} ({pw}x{ph}, {len(png)}B, "
                                f"theme={cell['applied_theme']} "
                                f"locale={cell['applied_locale']})",
                                flush=True,
                            )
        finally:
            browser.close()

    httpd.shutdown()
    shutil.rmtree(scratch)

    capture_tool_sha = hashlib.sha256(
        Path(__file__).read_bytes()
    ).hexdigest()

    manifest = {
        "page_id": "sanctions_map",
        "route": "sanctions_map.html",
        "registry_route": "macro:sanctions_map",
        "route_kind": "intelligence_desk",
        "subject": (
            "legible UK press mark on sanctions_map.html after #8292 — "
            "radius-fixed legend swatch, non-scaling dashed GBR outline, "
            "2-day heading, ZH note, seven-row public-news list "
            "(F02 O21d R2)"
        ),
        "source": "fixture-render",
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
    print(
        f"\n{ok}/{len(cells)} cells captured → {OUT_DIR} "
        f"(fixture render, source_commit={source_commit[:12]})",
        flush=True,
    )


if __name__ == "__main__":
    main()