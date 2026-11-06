#!/usr/bin/env python3
"""Capture dark+light × EN/ZH × 1440/390 of the news.html family_tally LENS tip
OPEN (the .lens-pop element, NOT just the section) for F05-017 R4 evidence.

Round R4 re-captures: the R3 cells framed the .lens-q button only — the open
tip element (`.lens-pop`) was created and visible but sat OUTSIDE the screenshot
because R3 captured `#nxConsequence` rather than the popover. R4 binds every
cell to the .lens-pop element via a union clip = trigger ∪ (tip + 24px pad).

* Open the tip via keyboard focus on `.lens-q` (the manifest's `open_by`).
* Theme via window.setTheme / `data-theme`; locale via window.setLang / `data-lang`.
  Never click `.lang-toggle` (theme.js moves it into a closed drawer).
* Render from the same fixture used by tests/test_news_page_render.py.
* Captures sit beside manifest.json. The tip element's selector + bbox go on
  every cell; the full DOM tip text (`tip_text`) is read at capture time.

Run from the repo root::

    python3 mockups/evidence/news-family-tally/capture.py

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
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent.parent  # mockups/.../capture.py -> repo root
sys.path.insert(0, str(_REPO))

TEMPLATES_DIR = _REPO / "templates"
OUT_DIR = _REPO / "mockups" / "evidence" / "news-family-tally"
CELLS_DIR = OUT_DIR / "cells"

VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}
LOCALES = ("en", "zh")
THEMES = ("dark", "light")

# Hide chrome overlays that would dirty the frame: master brain boot, sky-fx,
# theme-fab launcher, etc. They live above the page in dev only.
_HIDE_DECOR = (
    "#mmb-root,#mmb-boot,#mmb-launch,.sky-fx,.mx5-aurora,.theme-fab{"
    "display:none!important;visibility:hidden!important;opacity:0!important}"
)


def fixture_vm():
    """Non-trivial chronicle_impact payload — 8 rows across 3 families + the
    same six-entry family_tally the live corpus emits. The state phrase
    ``{named} name a stock`` (frozen §7 source string, R3-2 invariant) shows
    up in every EN tip that has at least one named event, and the ZH tip
    carries ``{named}个点名个股``."""
    rows_data = [
        {"event_id": "cev-a", "event_time": "2026-10-01",
         "event_time_en": "1 Oct 2026", "event_time_zh": "2026年10月1日",
         "title_en": "NVDA reported earnings",
         "title_zh": "NVDA公布业绩",
         "direct_tickers": ["NVDA"], "note_en": None, "note_zh": None},
        {"event_id": "cev-b", "event_time": "2026-09-30",
         "event_time_en": "30 Sep 2026", "event_time_zh": "2026年9月30日",
         "title_en": "AAPL reported earnings",
         "title_zh": "AAPL公布业绩",
         "direct_tickers": ["AAPL"], "note_en": None, "note_zh": None},
        {"event_id": "cev-c", "event_time": "2026-09-29",
         "event_time_en": "29 Sep 2026", "event_time_zh": "2026年9月29日",
         "title_en": "MSFT reported earnings",
         "title_zh": "MSFT公布业绩",
         "direct_tickers": ["MSFT"], "note_en": None, "note_zh": None},
        {"event_id": "cev-d", "event_time": "2026-09-28",
         "event_time_en": "28 Sep 2026", "event_time_zh": "2026年9月28日",
         "title_en": "MS: note on semis",
         "title_zh": "摩根士丹利：半导体研究纪要",
         "direct_tickers": ["NVDA", "AMD"], "note_en": None, "note_zh": None},
        {"event_id": "cev-e", "event_time": "2026-09-27",
         "event_time_en": "27 Sep 2026", "event_time_zh": "2026年9月27日",
         "title_en": "GS: note on banks",
         "title_zh": "高盛：银行研究纪要",
         "direct_tickers": ["JPM", "BAC"], "note_en": None, "note_zh": None},
        {"event_id": "cev-f", "event_time": "2026-09-26",
         "event_time_en": "26 Sep 2026", "event_time_zh": "2026年9月26日",
         "title_en": "BAML: note on energy",
         "title_zh": "美银美林：能源研究纪要",
         "direct_tickers": ["XOM"], "note_en": None, "note_zh": None},
        {"event_id": "cev-g", "event_time": "2026-09-25",
         "event_time_en": "25 Sep 2026", "event_time_zh": "2026年9月25日",
         "title_en": "FOMC decision in focus",
         "title_zh": "FOMC决议聚焦",
         "direct_tickers": ["TLT"], "note_en": None, "note_zh": None},
        {"event_id": "cev-h", "event_time": "2026-09-24",
         "event_time_en": "24 Sep 2026", "event_time_zh": "2026年9月24日",
         "title_en": "Jobless claims tracked",
         "title_zh": "初请失业金追踪",
         "direct_tickers": ["SPY"], "note_en": None, "note_zh": None},
    ]
    family_tally = [
        {"family": "earnings", "label_en": "Earnings reports", "label_zh": "业绩公告",
         "state": "no_events", "in_window": 0, "named": 0, "shown": 0},
        {"family": "earnings_call", "label_en": "Earnings calls", "label_zh": "业绩电话会",
         "state": "named", "in_window": 27, "named": 27, "shown": 3},
        {"family": "research_vault", "label_en": "Research notes", "label_zh": "研究纪要",
         "state": "named", "in_window": 12, "named": 8, "shown": 3},
        {"family": "macro_release", "label_en": "Economic data", "label_zh": "经济数据",
         "state": "named", "in_window": 5, "named": 5, "shown": 2},
        {"family": "regime_flip", "label_en": "Macro backdrop shifts", "label_zh": "宏观环境转向",
         "state": "none_named", "in_window": 2, "named": 0, "shown": 0},
        {"family": "risk_band", "label_en": "Risk radar shifts", "label_zh": "风险雷达变化",
         "state": "none_named", "in_window": 1, "named": 0, "shown": 0},
    ]
    from engine.chronicle import impact  # noqa: PLC0415
    tip_en, tip_zh = impact.build_family_tally_tip(family_tally)
    return {
        "stance_en": "Recent market events and the names they touch — shown only when an event maps to a named exposure.",
        "stance_zh": "近期市场事件及其涉及的标的——仅在事件对应到明确标的时显示。",
        "reason_en": None,
        "reason_zh": None,
        "empty_kind": None,
        "window_label_en": "Events from 25 Sep to 2 Oct 2026",
        "window_label_zh": "2026年9月25日至10月2日的事件",
        "window_mode": "last_7_days",
        "rows": rows_data,
        "family_tally": family_tally,
        "family_tally_tip_en": tip_en,
        "family_tally_tip_zh": tip_zh,
        "families": {"earnings_call": 3, "research_vault": 3, "macro_release": 2},
    }


def _news_vm():
    return {
        "chronicle_impact": fixture_vm(),
        "t": lambda en, zh: en,
        "LANG": "en",
        "LANG_EN": "en",
    }


def render_fixture_html(vm=None):
    from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, ChainableUndefined  # noqa: PLC0415
    src = (TEMPLATES_DIR / "news.html.j2").read_text(encoding="utf-8")
    # Strip the shared chrome includes — they're irrelevant to the lens-q tip
    # and a fixture-only render would otherwise need the full site theme.
    for inc in ("_site_nav.html.j2", "_seo_head.html.j2", "_vector_polish.html.j2",
                "_public_chrome_css.html.j2", "_public_chrome_js.html.j2"):
        src = src.replace(f"{{% include \"{inc}\" %}}", "")
    env = Environment(
        loader=ChoiceLoader([
            DictLoader({"news_fixture.html.j2": src}),
            FileSystemLoader(str(TEMPLATES_DIR)),
        ]),
        autoescape=True,
        undefined=ChainableUndefined,
    )
    return env.get_template("news_fixture.html.j2").render(**(vm or _news_vm()))


def write_fixture_site(scratch, vm=None, filename="news_fixture.html"):
    scratch.mkdir(parents=True, exist_ok=True)
    if (TEMPLATES_DIR / "theme.js").exists():
        shutil.copy(TEMPLATES_DIR / "theme.js", scratch / "theme.js")
    for css_name in ("navigation-refresh.css", "news.css", "theme.css"):
        if (TEMPLATES_DIR / css_name).exists():
            shutil.copy(TEMPLATES_DIR / css_name, scratch / css_name)
    html = render_fixture_html(vm)
    html = html.replace("</head>", f"<style>{_HIDE_DECOR}</style></head>", 1)
    (scratch / filename).write_text(html, encoding="utf-8")


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


# State applied AFTER first paint so localStorage + setTheme/setLang agree.
_STATE_SEED = """
() => {
  window.__skyDeck = true;
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


def _open_tip_and_capture(page, *, width, height):
    """Open the lens-q tip via keyboard focus and return (trigger_pixels, tip_box, tip_text).

    trigger_pixels: {x,y,w,h} of the .lens-q button in viewport pixels.
    tip_box:        {x,y,w,h} of the .lens-pop element in viewport pixels.
    tip_text:       full DOM text of the tip.
    """
    # Wait for the lens-q button.
    lens = page.locator(".lens-q").first
    lens.wait_for(state="visible", timeout=8000)
    # Wait for theme.js to install its handlers + CSS so focusin → show works.
    page.wait_for_function(
        "() => !!document.getElementById('lens-style') || "
        "       !!document.querySelector('style') || true",
        timeout=2000,
    )
    # Scroll the section into view, then focus the button and dispatch focusin
    # to mirror what `keyboard_focus` produces in real interaction.
    page.locator("#nxConsequence").first.scroll_into_view_if_needed()
    page.wait_for_timeout(80)
    lens.focus()
    page.evaluate(
        """
        () => {
          const b = document.querySelector('.lens-q');
          if (!b) return;
          b.dispatchEvent(new FocusEvent('focusin', {bubbles: true}));
        }
        """
    )
    # The tip opens with a 90ms hover-intent delay; the focus path is shorter
    # but theme.js still uses requestAnimationFrame to place the pop. Wait.
    page.wait_for_function(
        """
        () => {
          const pop = document.getElementById('lensPop') ||
                    document.querySelector('.lens-pop');
          return pop && pop.classList.contains('open');
        }
        """,
        timeout=4000,
    )
    page.wait_for_timeout(120)
    # On mobile (≤640px) the pop is a bottom sheet — its DOM rect is the
    # full-width sheet at the bottom of the viewport. Read its box.
    info = page.evaluate(
        """
        () => {
          const b = document.querySelector('.lens-q');
          const pop = document.getElementById('lensPop') ||
                    document.querySelector('.lens-pop');
          const tr = b.getBoundingClientRect();
          const pr = pop.getBoundingClientRect();
          return {
            trigger: {x: tr.left, y: tr.top, w: tr.width, h: tr.height},
            tip: {x: pr.left, y: pr.top, w: pr.width, h: pr.height},
            tip_text: pop.innerText || pop.textContent || '',
            tip_is_sheet: pr.bottom > (window.innerHeight - 40) && pr.height > 200,
            viewport_w: window.innerWidth,
            viewport_h: window.innerHeight,
          };
        }
        """
    )
    return info


def _capture_one(browser, base, *, width, height, locale, theme):
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
        url = f"{base}/news_fixture.html?t={theme}&l={locale}"
        resp = page.goto(url, wait_until="load", timeout=30000)
        if resp is None or not resp.ok:
            raise RuntimeError(f"HTTP {getattr(resp, 'status', 'none')}")
        page.wait_for_timeout(250)
        # Belt-and-braces: re-apply via setTheme/setLang (or direct attr).
        applied = page.evaluate(_APPLY_STATE.strip(), state) or {}
        if applied.get("theme") != theme or applied.get("locale") != locale:
            raise RuntimeError(
                f"state mismatch: requested theme={theme} locale={locale} "
                f"observed {applied!r}"
            )
        page.add_style_tag(content=_HIDE_DECOR)
        page.wait_for_timeout(120)

        info = _open_tip_and_capture(page, width=width, height=height)

        # Union clip: bbox of trigger ∪ bbox of tip, padded 24px, clamped to
        # viewport. (24px so the open tip's border + arrow room never gets
        # cropped on the edge case.)
        tr = info["trigger"]
        ti = info["tip"]
        ux = min(tr["x"], ti["x"])
        uy = min(tr["y"], ti["y"])
        ux2 = max(tr["x"] + tr["w"], ti["x"] + ti["w"])
        uy2 = max(tr["y"] + tr["h"], ti["y"] + ti["h"])
        pad = 24
        clip = {
            "x": max(0.0, ux - pad),
            "y": max(0.0, uy - pad),
            "w": min(float(width), ux2 + pad) - max(0.0, ux - pad),
            "h": min(float(height), uy2 + pad) - max(0.0, uy - pad),
        }

        png_bytes = page.screenshot(
            type="png",
            clip={"x": clip["x"], "y": clip["y"],
                  "width": clip["w"], "height": clip["h"]},
        )
        return {
            "png": png_bytes,
            "applied": applied,
            "trigger_box": tr,
            "tip_box": ti,
            "tip_text": info["tip_text"],
            "tip_is_sheet": info["tip_is_sheet"],
            "clip": clip,
        }
    finally:
        context.close()


def _sha256_and_dims(png):
    digest = hashlib.sha256(png).hexdigest()
    if png[:8] == b"\x89PNG\r\n\x1a\n" and png[12:16] == b"IHDR":
        w, h = struct.unpack(">II", png[16:24])
    else:
        w, h = 0, 0
    return digest, w, h


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="news_tally_r4_"))
    write_fixture_site(scratch)
    httpd, port = _serve(scratch)
    base = f"http://127.0.0.1:{port}"
    print(f"Serving from {scratch} at {base}", flush=True)

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
                        alias = f"family-tally-tip-{theme}-{locale}-{viewport_name}.png"
                        entry = {
                            "file": f"cells/{alias}",
                            "theme": theme,
                            "locale": locale,
                            "viewport": viewport_name,
                            "viewport_width": w,
                            "viewport_height": h,
                            "open_by": "keyboard_focus (focus .lens-q → dispatch focusin → theme.js shows .lens-pop)",
                            "selector": ".lens-pop",
                        }
                        try:
                            got = _capture_one(
                                browser, base, width=w, height=h,
                                locale=locale, theme=theme,
                            )
                            png = got["png"]
                            digest, pw, ph = _sha256_and_dims(png)
                            (CELLS_DIR / alias).write_bytes(png)
                            entry.update({
                                "applied_theme": got["applied"].get("theme"),
                                "applied_locale": got["applied"].get("locale"),
                                "bbox": got["tip_box"],
                                "clip": got["clip"],
                                "trigger_box": got["trigger_box"],
                                "tip_is_sheet": got["tip_is_sheet"],
                                "tip_text": got["tip_text"],
                                "sha256": digest,
                                "bytes": len(png),
                                "width": pw,
                                "height": ph,
                                "captured": captured_iso,
                            })
                            print(
                                f"  ✓ {alias} ({pw}x{ph}, {len(png)}B, tip {got['tip_box']['w']:.0f}x{got['tip_box']['h']:.0f})",
                                flush=True,
                            )
                        except Exception as exc:
                            entry.update({
                                "captured": False,
                                "reason": f"{type(exc).__name__}: {exc}",
                            })
                            print(f"  ✗ {viewport_name}-{locale}-{theme}: {exc}", flush=True)
                        cells.append(entry)
        finally:
            browser.close()

    httpd.shutdown()
    shutil.rmtree(scratch)

    manifest = {
        "page_id": "news.html#nxConsequence",
        "route": "/news_fixture.html",
        "registry_route": "/news.html",
        "route_kind": "news_family_tally_tip",
        "subject": ".lens-q (family_tally LENS trigger)",
        "selector": ".lens-pop",
        "open_by": "keyboard_focus (focus .lens-q → dispatch focusin → theme.js shows .lens-pop)",
        "generated_at": captured_iso,
        "fixture": {
            "type": "fixture-rendered news.html.j2",
            "fixture_vm_summary": "8 rows across earnings_call/research_vault/macro_release with non-trivial family_tally (earnings_call named 27/3 shown, research_vault named 12/8/3 shown, macro_release named 5/5/2 shown, regime_flip/risk_band none_named, earnings no_events)",
        },
        "cells": cells,
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False)
    )
    ok = sum(1 for c in cells if c.get("sha256"))
    print(f"\n{ok}/{len(cells)} cells captured → {OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()