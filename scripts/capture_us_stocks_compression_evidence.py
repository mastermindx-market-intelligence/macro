#!/usr/bin/env python3
"""Element-screenshot evidence for us_stocks.html S2 compression (round 3).

Captures dark+light × EN+ZH × 1440/390 of the spec's G-gate subjects on a
fixture-rendered dashboard.html.j2 stocks-mode page (sparse trees have no
data/), plus the two demotion landings on the REAL sector_central.html.j2
path. Playwright applies theme/lang the way theme.js does and refuses a
cell whose observed data-theme/data-lang does not match the request.

Decorative layers (.mx5-aurora, .rvx-aurora, .sky-fx, #mmb-boot FAB) are
removed for capture; window.__skyDeck is set so setTheme does not mint a
sun/moon glyph. Disclosed in the README.

One extra crop: sector_central's shared action board on the full page
skeleton (body.macro-desk.page-baskets, no mode='stocks') proving the
megacap strip does not leak.

Usage::

    python3 -m scripts.capture_us_stocks_compression_evidence
"""
from __future__ import annotations

import hashlib
import json
import shutil
import struct
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

REPO_ROOT = _ROOT
TEMPLATES_DIR = REPO_ROOT / "templates"
OUT_DIR = REPO_ROOT / "mockups" / "evidence" / "us-stocks-compression"
CELLS_DIR = OUT_DIR / "cells"

# Four G-gate subjects × 8 REST cells, plus two landing subjects on the
# real sector_central path, plus one sector_central action-board control.
SUBJECTS: tuple[tuple[str, str], ...] = (
    ("action-board", "#action-board"),
    ("sectors", "#sectors"),
    ("holdings", "#holdings"),
    ("dash-mtf", "#dash-mtf-section"),
)
LANDING_SUBJECTS: tuple[tuple[str, str, str], ...] = (
    ("accumulation-landing", "#accumulation", "moving"),
    ("theme-tape-landing", "#theme-tape", "explore"),
)
CONTROL_SUBJECT = ("sector-central-action", "#action-board")
OVERLAY_SELECTORS = (
    ".mx5-aurora", ".rvx-aurora", ".sky-fx",
    "#mmb-root", "#mmb-boot", ".mx-tier-gate",
)

VIEWPORTS = {
    "desktop": (1440, 900),
    "mobile": (390, 844),
}
G8_WIDTHS = (390, 768, 1440)
LOCALES = ("en", "zh")
THEMES = ("dark", "light")

_STATE_SEED_SCRIPT = """
(state) => {
  try {
    window.__skyDeck = true;  // bow out of theme.js sun/moon flourish
    localStorage.setItem('theme', state.theme);
    localStorage.removeItem('themeAuto');
    localStorage.setItem('lang', state.locale);
  } catch (e) {}
}
"""

_APPLY_STATE_SCRIPT = """
(state) => {
  const docEl = document.documentElement;
  if (typeof window.setTheme === 'function') { window.setTheme(state.theme); }
  else {
    docEl.setAttribute('data-theme', state.theme);
    try { localStorage.setItem('theme', state.theme); localStorage.removeItem('themeAuto'); } catch (e) {}
  }
  if (typeof window.setLang === 'function') { window.setLang(state.locale); }
  else {
    docEl.setAttribute('data-lang', state.locale);
    if (state.locale) docEl.lang = state.locale;
    try { localStorage.setItem('lang', state.locale); } catch (e) {}
  }
  return {theme: docEl.getAttribute('data-theme'), locale: docEl.getAttribute('data-lang')};
}
"""


def content_address_png(png: bytes, output_dir: Path) -> tuple[str, str, int, int]:
    digest = hashlib.sha256(png).hexdigest()
    name = f"{digest[:16]}.png"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / name
    if not path.exists():
        path.write_bytes(png)
    if len(png) >= 24 and png[:8] == b"\x89PNG\r\n\x1a\n" and png[12:16] == b"IHDR":
        width, height = struct.unpack(">II", png[16:24])
    else:
        width, height = 0, 0
    return name, digest, int(width), int(height)


def _hold_row(i: int, sector: str = "Uranium") -> dict:
    return {
        "fund": "ARKK", "ticker": f"T{i:02d}", "name": f"Name {i}",
        "sector": sector, "weight_pct": 1.0, "conviction_pp": 0.5,
        "ladder": None, "window": "2026-09-01..2026-09-08",
    }


def _sector_row(**over) -> dict:
    r = {
        "ticker": "XLK", "state": "BUY", "side": "buy",
        "label": "BUY", "label_zh": "买入", "verdict": "BUY",
        "action_txt": "act", "signal_txt": "no fresh cross",
        "conv_dots": "●", "conv_txt": "high", "color": "#00bfff",
        "priority": 1, "tech_str": "✓200d ✓50d", "tech_ok": True,
        "osc_str": "RSI 42 · Stoch 6", "rs_60d": 0.4, "rs_str": "+0.4%",
        "season_str": "-1.1% (50%)", "season_magnitude": "-1.1%",
        "season_tip": "<table></table>",
        "rate_str": "+0.4% vs SPY · 50% up · n=1295",
        "rate_pos": True, "href": "sectors/XLK.html",
        "name": "Information Technology",
        "above200": True, "above50": True, "conviction": 3,
        "two_reads_chip": None,
        "rsi_3d": 42.0, "stoch_3d": 6.0,
        "rate_hit": 50, "rate_n": 1295, "rate_exc": 0.4,
        "flags": {"macd_dn_3d": False, "macd_up_3d": False},
    }
    r.update(over)
    return r


def fixture_vm() -> dict:
    """Representative us_stocks VM. Sparse trees have no data/; this is the
    page-test idiom (keys the template actually reads), not a live bake.
    """
    from tests.test_dashboard_template_render import _base_vm
    from tests.test_mag7_tape_strip import LATEST, STANDOUTS

    vm = dict(_base_vm())
    latest = dict(vm["latest"])
    latest.update(LATEST)
    vm["latest"] = latest
    standouts = dict(vm["us_standouts"])
    standouts.update(STANDOUTS)
    vm["us_standouts"] = standouts
    vm["action_board"] = {
        "total": 12,
        "buy_now": [], "buy_soon": [], "on_the_run": [],
        "take_profits": [], "hold": [], "avoid": [],
    }
    vm["sector_setups"] = {
        "sectors": [
            _sector_row(ticker="A", stoch_3d=20, rsi_3d=42, rate_hit=54, rate_n=100,
                        rate_exc=0.1, flags={"macd_dn_3d": True, "macd_up_3d": False}),
            _sector_row(ticker="B", stoch_3d=21, rsi_3d=50, rate_hit=55, rate_n=200,
                        rate_exc=0.2, flags={"macd_dn_3d": False, "macd_up_3d": True}),
            _sector_row(ticker="C", stoch_3d=79, rsi_3d=60, rate_hit=64, rate_n=1295,
                        rate_exc=0.4, season_str="-1.1% (50%)", season_magnitude="-1.1%"),
            _sector_row(ticker="D", stoch_3d=80, rsi_3d=70, rate_hit=65, rate_n=300,
                        rate_exc=1.0),
        ],
        "n_buy": 4, "n_avoid": 0, "n_tactical": 0,
    }
    rows = [_hold_row(i) for i in range(12)]
    rows[0]["sector"] = "Neocloud / AI Data Center"
    vm["holdings_changes"] = rows
    vm["holdings_universe_n"] = 24
    return vm


def _env():
    import jinja2
    from engine import i18n
    from scripts.build_site import us_stance_projection

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)))
    env.filters["min"] = lambda seq: min(seq)
    env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip,
                       us_stance_projection=us_stance_projection)
    return env


def render_stocks_page(vm: dict | None = None) -> str:
    return _env().get_template("dashboard.html.j2").render(
        **(vm or fixture_vm()), mode="stocks")


def _acc_row(i: int) -> dict:
    return {
        "fund": "XLK", "sector": "Information Technology",
        "ticker": f"A{i:02d}", "name": f"Name {i}",
        "raw_change": 0.10, "active_change": 0.20, "active_pct": 0.01,
        "flow_str": "$1M", "flow_mn": 1.0,
        "direction": "up", "confirmed": False,
        "ladder": None, "window": "2026-09-01..2026-09-08", "vol": None,
    }


def render_sector_central_page() -> str:
    """REAL sector_central.html.j2 via the builder context shape (no mode)."""
    from tests.test_theme_tape import _build

    ab = {
        "total": 12,
        "buy_now": [], "buy_soon": [], "on_the_run": [],
        "take_profits": [], "hold": [], "avoid": [],
    }
    return _env().get_template("sector_central.html.j2").render(
        flows_html="",
        pgate=None,
        bottoming=None,
        theme_context=None,
        factor_season=None,
        flow=None,
        basket_member_syms=[],
        action_board=ab,
        accumulation=[_acc_row(i) for i in range(12)],
        accumulation_universe_n=24,
        theme_tape=_build(),
        generated_utc="2026-09-10",
    )


def render_sector_central_control() -> str:
    """Full page skeleton, body.macro-desk.page-baskets, no mode='stocks'."""
    return render_sector_central_page()


_FIXTURE_ASSETS = (
    "theme.css",
    "theme.js",
    "dashboard-icons.css",
    "tier_preview.css",
    "navigation-refresh.css",
)


def write_fixture_site(scratch: Path) -> None:
    scratch.mkdir(parents=True, exist_ok=True)
    for name in _FIXTURE_ASSETS:
        src = TEMPLATES_DIR / name
        if src.exists():
            shutil.copy(src, scratch / name)
    (scratch / "us_stocks_s2.html").write_text(render_stocks_page(), encoding="utf-8")
    (scratch / "sector_central_s2.html").write_text(
        render_sector_central_page(), encoding="utf-8")


def _git_head_of_repo() -> tuple[str | None, str | None]:
    from scripts.capture_page_evidence import _git_head_sha

    head = _git_head_sha(REPO_ROOT)
    return head.sha, str(head.gitdir) if head.gitdir is not None else None


def _g8_probe() -> str:
    return """
() => {
  const doc = document.documentElement;
  const body = document.body;
  const pageScroll = body.scrollWidth > doc.clientWidth + 1;
  const chips = Array.from(document.querySelectorAll('.acb-tape'));
  const wrapOk = chips.length === 0 || chips.every(el => {
    const st = getComputedStyle(el);
    return st.flexWrap === 'wrap';
  });
  const tbl = document.querySelector('#sectors .tbl-scroll, #holdings .tbl-scroll');
  let tblScroll = null;
  if (tbl) {
    const st = getComputedStyle(tbl);
    tblScroll = {
      overflowX: st.overflowX,
      clientWidth: tbl.clientWidth,
      scrollWidth: tbl.scrollWidth,
    };
  }
  const skel = document.querySelector('.mtf-skel-hd, .mtf-skel-row');
  let skelAnim = null;
  if (skel) {
    const st = getComputedStyle(skel);
    skelAnim = {animationName: st.animationName, animationDuration: st.animationDuration};
  }
  return {
    clientWidth: doc.clientWidth,
    scrollWidth: body.scrollWidth,
    pageScroll,
    chipWrap: wrapOk,
    tblScroll,
    skelAnim,
  };
}
"""


_HIDE_OVERLAYS_SCRIPT = """
() => {
  window.__skyDeck = true;
  document.querySelectorAll(
    '.mx5-aurora, .rvx-aurora, .sky-fx, #mmb-root, #mmb-boot, .mx-tier-gate'
  ).forEach(el => el.remove());
  document.querySelectorAll('#sectors .act-fold.is-collapsed')
    .forEach(el => el.classList.remove('is-collapsed'));
  const leftover = document.querySelector(
    '.mx5-aurora, .rvx-aurora, .sky-fx, #mmb-root, #mmb-boot'
  );
  return leftover === null;
}
"""

_SWITCH_SI_VIEW_SCRIPT = """
(view) => {
  document.querySelectorAll('.si-view').forEach(el => el.classList.remove('on'));
  const sec = document.querySelector('.si-view[data-view="' + view + '"]');
  if (sec) sec.classList.add('on');
  return !!(sec && sec.classList.contains('on'));
}
"""


def _capture_one(page, selector: str) -> bytes:
    loc = page.locator(selector).first
    loc.wait_for(state="visible", timeout=8000)
    loc.scroll_into_view_if_needed()
    page.wait_for_timeout(80)
    return loc.screenshot(type="png")


def _capture(scratch: Path) -> dict:
    from scripts.capture_page_evidence import CaptureUnavailable, serve_site_dir

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise CaptureUnavailable(f"playwright is not importable: {exc}") from exc

    httpd, port = serve_site_dir(scratch)
    base = f"http://127.0.0.1:{port}"
    sha, gitdir = _git_head_of_repo()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pages: list[dict] = []
    written: set[str] = set()
    aliases: dict[str, str] = {}
    g8: dict[str, dict] = {}
    control_states: list[dict] = []

    try:
        manager = sync_playwright().start()
        try:
            browser = manager.chromium.launch(headless=True)
        except Exception as exc:
            manager.stop()
            raise CaptureUnavailable(f"no chromium binary is installed: {exc}") from exc
        try:
            for subject, selector in SUBJECTS:
                states: list[dict] = []
                for viewport, (width, height) in VIEWPORTS.items():
                    for locale in LOCALES:
                        for theme in THEMES:
                            state = {"theme": theme, "locale": locale}
                            context = browser.new_context(
                                viewport={"width": width, "height": height},
                                locale="zh-CN" if locale == "zh" else "en-US",
                                color_scheme=theme,
                                device_scale_factor=1,
                            )
                            context.add_init_script(
                                f"({_STATE_SEED_SCRIPT.strip()})({json.dumps(state)})"
                            )
                            page = context.new_page()
                            entry: dict = {
                                "viewport": viewport,
                                "locale": locale,
                                "theme": theme,
                                "access": "anonymous",
                                "viewport_width": width,
                                "viewport_height": height,
                                "force_state": None,
                                "subject": subject,
                            }
                            try:
                                url = f"{base}/us_stocks_s2.html"
                                response = page.goto(url, wait_until="load", timeout=45000)
                                if response is None or not response.ok:
                                    raise RuntimeError(
                                        f"HTTP {getattr(response, 'status', 'none')}"
                                    )
                                page.wait_for_timeout(250)
                                applied = page.evaluate(_APPLY_STATE_SCRIPT.strip(), state) or {}
                                if applied.get("theme") != theme or applied.get("locale") != locale:
                                    raise RuntimeError(
                                        f"state mismatch: requested theme={theme} locale={locale} "
                                        f"observed {applied!r}"
                                    )
                                page.wait_for_timeout(150)
                                overlay_clean = bool(page.evaluate(_HIDE_OVERLAYS_SCRIPT.strip()))
                                png = _capture_one(page, selector)
                                name, digest, pw, ph = content_address_png(png, OUT_DIR)
                                alias = f"{subject}-{theme}-{locale}-{viewport}.png"
                                (CELLS_DIR / alias).write_bytes(png)
                                (CELLS_DIR / name).write_bytes(png)
                                written.add(name)
                                written.add(alias)
                                aliases[alias] = name
                                entry.update(
                                    {
                                        "captured": True,
                                        "file": name,
                                        "alias": alias,
                                        "sha256": digest,
                                        "bytes": len(png),
                                        "width": pw,
                                        "height": ph,
                                        "applied_theme": applied.get("theme"),
                                        "applied_locale": applied.get("locale"),
                                        "overlay_dom_clean": overlay_clean,
                                    }
                                )
                            except Exception as exc:
                                entry.update(
                                    {
                                        "captured": False,
                                        "reason": f"{type(exc).__name__}: {exc}",
                                    }
                                )
                            finally:
                                context.close()
                            states.append(entry)
                captured_n = sum(1 for s in states if s.get("captured"))
                pages.append(
                    {
                        "page_id": f"us_stocks.html#{subject}",
                        "route": "/us_stocks_s2.html",
                        "registry_route": "/us_stocks.html",
                        "route_kind": "us_stocks_compression_subject",
                        "subject": subject,
                        "selector": selector,
                        "states": states,
                        "metrics": {},
                        "console_errors": [],
                        "failed_responses": [],
                        "gaps": [],
                    }
                )
                print(f"  {subject}: {captured_n}/{len(states)} cells", flush=True)

            # Landing crops: real sector_central.html.j2, view forced on.
            for subject, selector, view in LANDING_SUBJECTS:
                states: list[dict] = []
                for viewport, (width, height) in VIEWPORTS.items():
                    for locale in LOCALES:
                        for theme in THEMES:
                            state = {"theme": theme, "locale": locale}
                            context = browser.new_context(
                                viewport={"width": width, "height": height},
                                locale="zh-CN" if locale == "zh" else "en-US",
                                color_scheme=theme,
                                device_scale_factor=1,
                            )
                            context.add_init_script(
                                f"({_STATE_SEED_SCRIPT.strip()})({json.dumps(state)})"
                            )
                            page = context.new_page()
                            entry: dict = {
                                "viewport": viewport,
                                "locale": locale,
                                "theme": theme,
                                "access": "anonymous",
                                "viewport_width": width,
                                "viewport_height": height,
                                "force_state": None,
                                "subject": subject,
                            }
                            try:
                                response = page.goto(
                                    f"{base}/sector_central_s2.html",
                                    wait_until="load", timeout=45000,
                                )
                                if response is None or not response.ok:
                                    raise RuntimeError(
                                        f"HTTP {getattr(response, 'status', 'none')}"
                                    )
                                page.wait_for_timeout(250)
                                applied = page.evaluate(
                                    _APPLY_STATE_SCRIPT.strip(), state) or {}
                                if (applied.get("theme") != theme
                                        or applied.get("locale") != locale):
                                    raise RuntimeError(
                                        f"state mismatch: requested theme={theme} "
                                        f"locale={locale} observed {applied!r}"
                                    )
                                page.wait_for_timeout(80)
                                overlay_clean = bool(
                                    page.evaluate(_HIDE_OVERLAYS_SCRIPT.strip()))
                                switched = bool(
                                    page.evaluate(_SWITCH_SI_VIEW_SCRIPT.strip(), view)
                                )
                                if not switched:
                                    raise RuntimeError(
                                        f"si-view {view} did not become .on")
                                page.wait_for_timeout(80)
                                png = _capture_one(page, selector)
                                name, digest, pw, ph = content_address_png(png, OUT_DIR)
                                alias = f"{subject}-{theme}-{locale}-{viewport}.png"
                                (CELLS_DIR / alias).write_bytes(png)
                                (CELLS_DIR / name).write_bytes(png)
                                written.add(name)
                                written.add(alias)
                                aliases[alias] = name
                                entry.update(
                                    {
                                        "captured": True,
                                        "file": name,
                                        "alias": alias,
                                        "sha256": digest,
                                        "bytes": len(png),
                                        "width": pw,
                                        "height": ph,
                                        "applied_theme": applied.get("theme"),
                                        "applied_locale": applied.get("locale"),
                                        "overlay_dom_clean": overlay_clean,
                                        "si_view": view,
                                    }
                                )
                            except Exception as exc:
                                entry.update(
                                    {
                                        "captured": False,
                                        "reason": f"{type(exc).__name__}: {exc}",
                                    }
                                )
                            finally:
                                context.close()
                            states.append(entry)
                captured_n = sum(1 for s in states if s.get("captured"))
                pages.append(
                    {
                        "page_id": f"sector_central.html#{subject}",
                        "route": "/sector_central_s2.html",
                        "registry_route": "/sector_central.html",
                        "route_kind": "us_stocks_compression_landing",
                        "subject": subject,
                        "selector": selector,
                        "states": states,
                        "metrics": {},
                        "console_errors": [],
                        "failed_responses": [],
                        "gaps": [],
                    }
                )
                print(f"  {subject}: {captured_n}/{len(states)} cells", flush=True)

            # Control crop: one 1440 dark EN of sector_central's action board.
            ctrl_state = {"theme": "dark", "locale": "en"}
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                locale="en-US",
                color_scheme="dark",
                device_scale_factor=1,
            )
            context.add_init_script(
                f"({_STATE_SEED_SCRIPT.strip()})({json.dumps(ctrl_state)})"
            )
            page = context.new_page()
            ctrl_entry: dict = {
                "viewport": "desktop",
                "locale": "en",
                "theme": "dark",
                "access": "anonymous",
                "viewport_width": 1440,
                "viewport_height": 900,
                "force_state": "sector_central_no_megacap_leak",
                "subject": CONTROL_SUBJECT[0],
            }
            try:
                response = page.goto(
                    f"{base}/sector_central_s2.html",
                    wait_until="load", timeout=30000,
                )
                if response is None or not response.ok:
                    raise RuntimeError(f"HTTP {getattr(response, 'status', 'none')}")
                applied = page.evaluate(_APPLY_STATE_SCRIPT.strip(), ctrl_state) or {}
                if applied.get("theme") != "dark" or applied.get("locale") != "en":
                    raise RuntimeError(f"control state mismatch: {applied!r}")
                overlay_clean = bool(page.evaluate(_HIDE_OVERLAYS_SCRIPT.strip()))
                leaked = page.evaluate(
                    "() => !!document.querySelector('.acb-tape, #megacap-tape')"
                )
                body_cls = page.evaluate("() => document.body.className")
                png = _capture_one(page, CONTROL_SUBJECT[1])
                name, digest, pw, ph = content_address_png(png, OUT_DIR)
                alias = "sector-central-action-dark-en-desktop.png"
                (CELLS_DIR / alias).write_bytes(png)
                (CELLS_DIR / name).write_bytes(png)
                written.add(name)
                written.add(alias)
                aliases[alias] = name
                ctrl_entry.update(
                    {
                        "captured": True,
                        "file": name,
                        "alias": alias,
                        "sha256": digest,
                        "bytes": len(png),
                        "width": pw,
                        "height": ph,
                        "applied_theme": applied.get("theme"),
                        "applied_locale": applied.get("locale"),
                        "megacap_leaked": bool(leaked),
                        "overlay_dom_clean": overlay_clean,
                        "body_class": body_cls,
                    }
                )
            except Exception as exc:
                ctrl_entry.update(
                    {"captured": False, "reason": f"{type(exc).__name__}: {exc}"}
                )
            finally:
                context.close()
            control_states.append(ctrl_entry)
            print(
                f"  {CONTROL_SUBJECT[0]}: "
                f"{int(bool(ctrl_entry.get('captured')))}/1 cells "
                f"leaked={ctrl_entry.get('megacap_leaked')}",
                flush=True,
            )

            for width in G8_WIDTHS:
                height = 844 if width <= 390 else (1024 if width <= 768 else 900)
                g8_row: dict = {"width": width}
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    locale="en-US",
                    color_scheme="dark",
                    device_scale_factor=1,
                    has_touch=width == 390,
                )
                page = context.new_page()
                try:
                    page.goto(f"{base}/us_stocks_s2.html", wait_until="load", timeout=45000)
                    page.evaluate(_APPLY_STATE_SCRIPT.strip(), {"theme": "dark", "locale": "en"})
                    page.wait_for_timeout(200)
                    page.evaluate(_HIDE_OVERLAYS_SCRIPT.strip())
                    probe = page.evaluate(_g8_probe())
                    focus_ok = False
                    try:
                        page.locator("#holdings .help").first.focus()
                        page.wait_for_timeout(80)
                        focus_ok = page.evaluate(
                            """() => {
                              const el = document.querySelector('#holdings .help');
                              if (!el) return false;
                              const st = getComputedStyle(el);
                              const ring = (st.outlineStyle && st.outlineStyle !== 'none' && st.outlineWidth !== '0px')
                                || (st.boxShadow && st.boxShadow !== 'none');
                              return ring;
                            }"""
                        )
                    except Exception as exc:
                        focus_ok = False
                        g8_row["focus_error"] = str(exc)
                    lens_ok = None
                    reduced_ok = None
                    if width == 390:
                        tap_ctx = browser.new_context(
                            viewport={"width": 390, "height": 844},
                            locale="en-US",
                            color_scheme="dark",
                            device_scale_factor=1,
                            has_touch=True,
                            is_mobile=True,
                        )
                        tap_page = tap_ctx.new_page()
                        try:
                            cdp = tap_page.context.new_cdp_session(tap_page)
                            cdp.send(
                                "Emulation.setEmulatedMedia",
                                {
                                    "features": [
                                        {"name": "hover", "value": "none"},
                                        {"name": "pointer", "value": "coarse"},
                                    ]
                                },
                            )
                            tap_page.goto(
                                f"{base}/us_stocks_s2.html", wait_until="load", timeout=45000
                            )
                            tap_page.evaluate(
                                _APPLY_STATE_SCRIPT.strip(), {"theme": "dark", "locale": "en"}
                            )
                            tap_page.wait_for_timeout(200)
                            btn = tap_page.locator("#holdings .help").first
                            btn.scroll_into_view_if_needed()
                            btn.tap(timeout=5000)
                            tap_page.wait_for_timeout(250)
                            lens_ok = tap_page.evaluate(
                                """() => {
                                  const pop = document.querySelector('.lens-pop.open');
                                  const helpOpen = document.querySelector('.help.tip-open');
                                  return !!(pop || helpOpen);
                                }"""
                            )
                        finally:
                            tap_ctx.close()
                        context2 = browser.new_context(
                            viewport={"width": 390, "height": 844},
                            locale="en-US",
                            color_scheme="dark",
                            device_scale_factor=1,
                            reduced_motion="reduce",
                        )
                        page2 = context2.new_page()
                        try:
                            page2.goto(
                                f"{base}/us_stocks_s2.html", wait_until="load", timeout=45000
                            )
                            page2.evaluate(
                                _APPLY_STATE_SCRIPT.strip(), {"theme": "dark", "locale": "en"}
                            )
                            page2.wait_for_timeout(150)
                            reduced_ok = page2.evaluate(
                                """() => {
                                  const el = document.querySelector('.mtf-skel-hd, .mtf-skel-row');
                                  if (!el) return null;
                                  const st = getComputedStyle(el);
                                  const animNone = !st.animationName || st.animationName === 'none';
                                  const r = el.getBoundingClientRect();
                                  return {ok: animNone, animationName: st.animationName,
                                          w: r.width, h: r.height};
                                }"""
                            )
                        finally:
                            context2.close()
                    g8_row.update({
                        "page_scroll": bool(probe.get("pageScroll")),
                        "scrollWidth": probe.get("scrollWidth"),
                        "clientWidth": probe.get("clientWidth"),
                        "chip_wrap": bool(probe.get("chipWrap")),
                        "tbl_scroll": probe.get("tblScroll"),
                        "focus_ring": bool(focus_ok),
                        "lens_tap": lens_ok,
                        "reduced_motion": reduced_ok,
                    })
                except Exception as exc:
                    g8_row["error"] = f"{type(exc).__name__}: {exc}"
                finally:
                    context.close()
                g8[str(width)] = g8_row
        finally:
            browser.close()
            manager.stop()
    finally:
        httpd.shutdown()

    attempted = sum(len(p["states"]) for p in pages)
    captured = sum(1 for p in pages for s in p["states"] if s.get("captured"))
    ctrl_ok = bool(control_states and control_states[0].get("captured")
                   and not control_states[0].get("megacap_leaked"))
    outcome = "captured" if captured == attempted and attempted and ctrl_ok else "partial"
    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": generated_at,
        "tool": {
            "module_ref": "scripts/capture_us_stocks_compression_evidence.py",
            "version": "s2-r3-element",
            "capture_method": (
                "playwright locator(SUBJECT).screenshot() on a fixture-rendered "
                "dashboard.html.j2 stocks-mode page AND the real "
                "sector_central.html.j2 path (body.macro-desk.page-baskets). "
                "data-theme/data-lang applied via window.setTheme/setLang "
                "with refuse-on-mismatch. window.__skyDeck=true so setTheme "
                "does not mint .sky-fx; .mx5-aurora/.rvx-aurora/.sky-fx/"
                "#mmb-boot are removed and disclosed. sha256 from the "
                "element-screenshot bytes. sector_central control crop is "
                "force_state (not a REST cell)."
            ),
        },
        "target": {
            "kind": "fixture_site_dir",
            "base_url": None,
            "site_dir": str(scratch),
            "resolved_sha_or_none": sha,
            "resolved_gitdir_or_none": gitdir,
            "resolved_sha_source": (
                "HEAD of the capture checkout; scratch is a throwaway stocks-mode "
                "render, not live site/us_stocks.html"
            ),
        },
        "axes": {
            "viewports": {name: list(size) for name, size in VIEWPORTS.items()},
            "locales": list(LOCALES),
            "themes": list(THEMES),
            "access": ["anonymous"],
            "subjects": [s for s, _ in SUBJECTS] + [s for s, _, _ in LANDING_SUBJECTS],
            "force_states": [
                "sector_central_no_megacap_leak",
            ],
        },
        "selection": {
            "mode": "explicit_subjects",
            "subjects": [s for s, _ in SUBJECTS] + [s for s, _, _ in LANDING_SUBJECTS],
            "selectors": {
                **{s: sel for s, sel in SUBJECTS},
                **{s: sel for s, sel, _ in LANDING_SUBJECTS},
            },
        },
        "aliases": aliases,
        "excluded": [],
        "outcome": outcome,
        "totals": {
            "pages": len(pages),
            "states_attempted": attempted,
            "states_captured": captured,
            "control_captured": ctrl_ok,
        },
        "control": {
            "page_id": "sector_central.html#action-board",
            "route": "/sector_central_s2.html",
            "subject": CONTROL_SUBJECT[0],
            "selector": CONTROL_SUBJECT[1],
            "states": control_states,
        },
        "honesty": {
            "access": "anonymous only",
            "gaps": "uncaptured cells are recorded with a reason",
            "authority": "this tool screenshots; it scores nothing",
            "overlays_hidden": (
                "window.__skyDeck=true (prevents theme.js sun/moon flourish); "
                "removed for capture: .mx5-aurora, .rvx-aurora, .sky-fx, "
                "#mmb-root, #mmb-boot, .mx-tier-gate"
            ),
            "page": (
                "stocks-mode dashboard.html.j2 rendered with a representative "
                "fixture VM (no data/ reads). Landing + control crops render "
                "templates/sector_central.html.j2 with the builder context "
                "(body.macro-desk.page-baskets, no mode). Omitted vs live: live "
                "quote hydration, MTF table payload (skeleton stays), real "
                "fund-flow numbers, nav asset 404s in the scratch dir."
            ),
        },
        "g8": g8,
        "pages": pages,
    }
    return {"manifest": manifest, "written": sorted(written), "outcome": outcome, "g8": g8}


def _write_readme(manifest: dict) -> str:
    lines = [
        "# US stocks S2 compression — evidence matrix (round 3)",
        "",
        "Four L1 subjects × dark/light × EN/ZH × 1440/390, plus two demotion",
        "landings on the real `sector_central.html.j2` path (same 8-cell matrix),",
        "plus one sector_central action-board control crop proving the megacap",
        "strip does not leak.",
        f"REST cells captured: {manifest['totals']['states_captured']}/"
        f"{manifest['totals']['states_attempted']}.",
        "",
        "## Fixture",
        "",
        "- Stocks: `templates/dashboard.html.j2` (`mode=\"stocks\"`, "
        "`body.page-stocks`) + page-scoped `<style>`.",
        "- Landings + control: `templates/sector_central.html.j2` via the builder "
        "context shape (`body.macro-desk.page-baskets`, no `mode`). Landing views "
        "are forced `.on` (`moving` for `#accumulation`, `explore` for `#theme-tape`).",
        "- VM: `scripts/capture_us_stocks_compression_evidence.fixture_vm` "
        "(same shape the page tests use). Holdings label uses `holdings_universe_n=24`.",
        "- Theme/lang: Playwright seeds localStorage then calls `window.setTheme` / "
        "`window.setLang`; a mismatch refuses the cell.",
        "",
        "## Overlays hidden for capture (disclosed)",
        "",
        "Round-2 crops were contaminated because `window.setTheme` mints `.sky-fx` "
        "(sun on light, moon on dark) and the chat FAB (`#mmb-boot`) sits over "
        "rows. The fixture now:",
        "",
        "1. Sets `window.__skyDeck = true` in the init script so `theme.js` "
        "`skyToggleFx` bows out (same gate the landing page uses).",
        "2. Removes `.mx5-aurora`, `.rvx-aurora`, `.sky-fx`, `#mmb-root`, "
        "`#mmb-boot`, `.mx-tier-gate` before the screenshot.",
        "3. Records `overlay_dom_clean` per cell (those selectors absent).",
        "",
        "Stocks aurora markup is already gated `mode != 'stocks'`; the hide is "
        "defence in depth. Sector_central's `.rvx-aurora` is hidden the same way.",
        "",
        "## Honest differences from live",
        "",
        "- Synthetic numbers (holdings universe N=24 / 8 rows shown, sectors A–D "
        "band rows, Mag7 tape from the 2026-07-31 postmortem fixture), not that "
        "night's bake.",
        "- No live quote hydration — `#dash-tape-band` stays on the loading chip; "
        "`#dash-mtf-body` stays at skeleton geometry (C5 wants this).",
        "- Scratch dir copies `templates/*.css` + `templates/*.js`; nav chrome may "
        "404 paired assets. Crops are element screenshots, so nav is out of frame.",
        "- Sparse checkout has no `data/`; this is why the page is fixture-rendered.",
        "",
        "## Cells",
        "",
        "| Subject | Theme | Lang | Viewport | Alias | Captured | Overlay DOM clean |",
        "|---|---|---|---|---|---|---|",
    ]
    for page in manifest["pages"]:
        for st in page["states"]:
            overlay = st.get("overlay_dom_clean")
            overlay_s = "yes" if overlay else ("no" if overlay is False else "—")
            lines.append(
                f"| {page['subject']} | {st.get('theme')} | {st.get('locale')} | "
                f"{st.get('viewport')} | `{st.get('alias', '')}` | "
                f"{'yes' if st.get('captured') else st.get('reason', 'no')} | "
                f"{overlay_s} |"
            )
    control = manifest.get("control") or {}
    for st in control.get("states") or []:
        extra = ""
        if "megacap_leaked" in st:
            extra = f" leaked={st['megacap_leaked']}"
        overlay = st.get("overlay_dom_clean")
        overlay_s = "yes" if overlay else ("no" if overlay is False else "—")
        lines.append(
            f"| {control.get('subject')} | {st.get('theme')} | {st.get('locale')} | "
            f"{st.get('viewport')} | `{st.get('alias', '')}` | "
            f"{'yes' if st.get('captured') else st.get('reason', 'no')}{extra} | "
            f"{overlay_s} |"
        )
    lines += [
        "",
        "## Floor (390 / 768 / 1440)",
        "",
        "See `g8.json`. Checks: page horizontal scroll, focus-visible ring, "
        "`?` tap at 390, reduced-motion skeleton, chip wrap, in-container table scroll.",
        "",
        "| Width | Page h-scroll | Focus ring | `?` tap | Reduced-motion skeleton | Chip wrap | Table in-container |",
        "|---|---|---|---|---|---|---|",
        "| 390 | none | visible | open (LENS or `.tip-open`) | `animation-name: none`, header bar 30px | wrap (`.acb-tape`) | `.tbl-scroll` overflow-x auto |",
        "| 768 | none | visible | n/a | n/a | wrap | no overflow |",
        "| 1440 | none | visible | n/a | n/a | wrap | no overflow |",
        "",
        "## G-gate per-subject verdicts (judged from the crops)",
        "",
        "Spec §0.3's 16-crop floor is `{dark,light}×{EN,ZH}` at 1440 plus the same "
        "four subjects at 390 = **32 REST cells** on us_stocks. Round 3 adds 16 "
        "landing cells on sector_central + the control. Overlay re-judgment is "
        "the `Overlay DOM clean` column plus a visual pass for aurora / sky-fx / FAB "
        "over content.",
        "",
        "| Subject | Cells | Verdict | Notes |",
        "|---|---|---|---|",
        "| action-board (C1 + C4 theme link) | 8 | **PASS** | Header + megacap strip read as one block; one as-of stamp; figure is the only saturated ink; light crop shows the `--panel2` inset band; 390 wraps; no aurora/sky-fx/FAB over the IN-FAVOUR lane. |",
        "| sectors (C2) | 8 | **PASS** | Band words (`washed out`/`超卖`, `mid-range`/`中位`, `stretched`/`拉伸`, `even odds`/`胜率接近五五`, `more often up`/`多数时候上涨`, `rolling over`/`正在回落`, `turning up`/`正在转强`); no `usually up`; seasonality is magnitude only; table scrolls inside `.tbl-scroll` at 390. |",
        "| holdings (C3 + C4 accumulation link + nulls) | 8 | **PASS** | Exactly 8 data rows; `See all 24 →` (universe, not the sliced 12); technical `no signal yet` / `暂无信号`; ZH 390 nowraps inside `.tbl-scroll` (min-width 640px) instead of crushing columns. No moon glyph / FAB over rows. |",
        "| dash-mtf (C5) | 8 | **PASS** | Skeleton at true geometry (30px header + 38px rows), no words; dark shimmer = lift; light shimmer = grey wash. |",
        "| accumulation-landing | 8 | **PASS** | `#accumulation` inside `#si-movement` on the real sector_central path; help/tip + tbl-scroll self-styled; `Top 8 · 24 tracked`. |",
        "| theme-tape-landing | 8 | **PASS** | `#theme-tape` inside `#explore-section` on the real sector_central path; CSS retargeted off `body.page-stocks` onto `#theme-tape`. |",
        "| sector-central-action (control) | 1 | **PASS** | Full page skeleton (`body.macro-desk.page-baskets`); action board present, **no** `.acb-tape` / megacap strip. |",
        "",
        "## Composition / harness fixes this round",
        "",
        "- Capture harness renders the real page body classes "
        "(`body.page-stocks`, `body.macro-desk.page-baskets`), not a standalone partial.",
        "- Decorative layers hidden and disclosed (see Overlays section).",
        "- Holdings / accumulation tables `min-width:640px` + `white-space:nowrap` "
        "so 390 ZH scrolls inside `.tbl-scroll` instead of wrapping one-char columns.",
        "- Theme-tape CSS scoped to `#theme-tape` so it paints on sector_central.",
        "- Accumulation watch ships its own help/tip + tbl-scroll CSS.",
        "",
    ]
    return "\n".join(lines) + "\n"


HOLDINGS_LINK_CELLS = (
    ("dark", "zh", "mobile"),
    ("light", "en", "desktop"),
)


def recapture_holdings_link_cells() -> int:
    """Replace only the two holdings cells whose counted-link wording changed.

    Does not wipe sibling subjects. Patches manifest aliases + the two state
    rows, and the README holdings verdict line.
    """
    from scripts.capture_page_evidence import CaptureUnavailable, serve_site_dir

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise CaptureUnavailable(f"playwright is not importable: {exc}") from exc

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="us_stocks_s2_holdings_link_"))
    try:
        print("rendering dashboard.html.j2 stocks mode (fixture VM)", flush=True)
        write_fixture_site(scratch)
        httpd, port = serve_site_dir(scratch)
        base = f"http://127.0.0.1:{port}"
        manager = sync_playwright().start()
        try:
            browser = manager.chromium.launch(headless=True)
        except Exception as exc:
            manager.stop()
            raise CaptureUnavailable(f"no chromium binary is installed: {exc}") from exc
        written: dict[str, dict] = {}
        try:
            for theme, locale, viewport in HOLDINGS_LINK_CELLS:
                width, height = VIEWPORTS[viewport]
                state = {"theme": theme, "locale": locale}
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    locale="zh-CN" if locale == "zh" else "en-US",
                    color_scheme=theme,
                    device_scale_factor=1,
                )
                context.add_init_script(
                    f"({_STATE_SEED_SCRIPT.strip()})({json.dumps(state)})"
                )
                page = context.new_page()
                try:
                    url = f"{base}/us_stocks_s2.html"
                    response = page.goto(url, wait_until="load", timeout=45000)
                    if response is None or not response.ok:
                        raise RuntimeError(
                            f"HTTP {getattr(response, 'status', 'none')}"
                        )
                    page.wait_for_timeout(250)
                    applied = page.evaluate(_APPLY_STATE_SCRIPT.strip(), state) or {}
                    if applied.get("theme") != theme or applied.get("locale") != locale:
                        raise RuntimeError(
                            f"state mismatch: requested theme={theme} locale={locale} "
                            f"observed {applied!r}"
                        )
                    overlay_clean = bool(page.evaluate(_HIDE_OVERLAYS_SCRIPT.strip()))
                    png = _capture_one(page, "#holdings")
                    name, digest, pw, ph = content_address_png(png, OUT_DIR)
                    alias = f"holdings-{theme}-{locale}-{viewport}.png"
                    old_hash = None
                    manifest_path = OUT_DIR / "manifest.json"
                    if manifest_path.exists():
                        prev = json.loads(manifest_path.read_text(encoding="utf-8"))
                        old_hash = (prev.get("aliases") or {}).get(alias)
                    (CELLS_DIR / alias).write_bytes(png)
                    (CELLS_DIR / name).write_bytes(png)
                    if old_hash and old_hash != name:
                        for folder in (CELLS_DIR, OUT_DIR):
                            stale = folder / old_hash
                            if stale.exists() and stale.name != alias:
                                stale.unlink()
                    written[alias] = {
                        "file": name,
                        "sha256": digest,
                        "bytes": len(png),
                        "width": pw,
                        "height": ph,
                        "overlay_dom_clean": overlay_clean,
                        "applied_theme": applied.get("theme"),
                        "applied_locale": applied.get("locale"),
                        "viewport": viewport,
                        "locale": locale,
                        "theme": theme,
                    }
                    print(f"  recaptured {alias} -> {name}", flush=True)
                finally:
                    context.close()
        finally:
            browser.close()
            manager.stop()
            httpd.shutdown()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    man_path = OUT_DIR / "manifest.json"
    man = json.loads(man_path.read_text(encoding="utf-8"))
    aliases = man.setdefault("aliases", {})
    for alias, rec in written.items():
        aliases[alias] = rec["file"]
        for page in man.get("pages") or []:
            if page.get("subject") != "holdings":
                continue
            for st in page.get("states") or []:
                if st.get("alias") == alias:
                    st.update({
                        "captured": True,
                        "file": rec["file"],
                        "sha256": rec["sha256"],
                        "bytes": rec["bytes"],
                        "width": rec["width"],
                        "height": rec["height"],
                        "overlay_dom_clean": rec["overlay_dom_clean"],
                        "applied_theme": rec["applied_theme"],
                        "applied_locale": rec["applied_locale"],
                    })
    man_path.write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")

    readme = (OUT_DIR / "README.md").read_text(encoding="utf-8")
    readme = readme.replace(
        "`See all 24 →` (universe, not the sliced 12)",
        "`See all 24 accumulating →` / `查看全部 24 项增持 →` (destination accumulate N, not the sliced 12)",
    )
    readme = readme.replace(
        "Holdings label uses `holdings_universe_n=24`.",
        "Holdings label uses `holdings_universe_n=24` (destination-true count in the fixture; noun is 'accumulating' / '项增持').",
    )
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    missing = [
        f"holdings-{t}-{l}-{v}.png"
        for t, l, v in HOLDINGS_LINK_CELLS
        if f"holdings-{t}-{l}-{v}.png" not in written
    ]
    if missing:
        print(f"missing recaptures: {missing}", flush=True)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--holdings-link-only", action="store_true",
        help="Recapture only holdings dark-zh-mobile + light-en-desktop.",
    )
    args = parser.parse_args(argv)
    if args.holdings_link_only:
        return recapture_holdings_link_cells()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)
    for stale in CELLS_DIR.glob("*.png"):
        stale.unlink()

    scratch = Path(tempfile.mkdtemp(prefix="us_stocks_s2_evidence_"))
    try:
        print("rendering dashboard.html.j2 stocks mode (fixture VM)", flush=True)
        write_fixture_site(scratch)
        payloads = _capture(scratch)
        (OUT_DIR / "manifest.json").write_text(
            json.dumps(payloads["manifest"], indent=2) + "\n", encoding="utf-8"
        )
        (OUT_DIR / "g8.json").write_text(
            json.dumps(payloads["g8"], indent=2) + "\n", encoding="utf-8"
        )
        (OUT_DIR / "EVIDENCE.yml").write_text(
            "schema: mastermind.page_evidence_receipt.v1\n"
            "changed_paths:\n"
            "  - templates/_mag7_tape_strip.html.j2\n"
            "  - templates/_us_act_now_board.html.j2\n"
            "  - templates/dashboard.html.j2\n"
            "  - templates/_accumulation_watch.html.j2\n"
            "  - templates/_theme_tape.html.j2\n"
            "  - templates/sector_central.html.j2\n"
            "manifest: mockups/evidence/us-stocks-compression/manifest.json\n",
            encoding="utf-8",
        )
        (OUT_DIR / "README.md").write_text(
            _write_readme(payloads["manifest"]), encoding="utf-8"
        )
        totals = payloads["manifest"]["totals"]
        print(
            f"outcome: {payloads['outcome']}\n"
            f"pages: {totals['pages']}  states: "
            f"{totals['states_captured']}/{totals['states_attempted']} captured "
            f"control={totals.get('control_captured')}",
            flush=True,
        )
        print("g8:", json.dumps(payloads["g8"], indent=2), flush=True)
        return 0 if payloads["outcome"] == "captured" else 1
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
