#!/usr/bin/env python3
"""Element-screenshot evidence for commodities.html W6 (round 4).

Captures dark+light × EN+ZH × 1440/390 of the page plus the packet's named
proof crops on a fixture-rendered commodities wrap (sparse trees have no
data/). Playwright applies theme/lang the way theme.js does and refuses a
cell whose observed data-theme/data-lang does not match the request.

Usage::

    python3 -m scripts.capture_commodities_w6_evidence
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
OUT_DIR = REPO_ROOT / "mockups" / "evidence" / "commodities-w6"
CELLS_DIR = OUT_DIR / "cells"

VIEWPORTS = {
    "desktop": (1440, 900),
    "mobile": (390, 844),
}
LOCALES = ("en", "zh")
THEMES = ("dark", "light")

# Current-shaped board (W6 r2 test_hero_current_shaped_board_is_selective).
_STRETCHED = {
    "heating_oil": "Extended — late cycle",
    "corn": "Blowing off — extended",
    "soybeans": "Blowing off — extended",
}

# Heat-grid (shock, mom, chg_1m, cycle_phase). Shock outranks momentum.
_HEAT: dict[str, tuple[str, str, float | None, str | None]] = {
    "oil":         ("normal",  "bull",    4.2,  "Expansion"),
    "natgas":      ("normal",  "bear",   -3.1,  "Downturn"),
    "gasoline":    ("normal",  "bull",    2.0,  "Expansion"),
    "heating_oil": ("normal",  "bull",    5.5,  "Peak"),
    "gold":        ("normal",  "bull",    1.2,  "Expansion"),
    "silver":      ("normal",  "neutral", 0.4,  "Recovery"),
    "platinum":    ("normal",  "bear",   -1.8,  "Downturn"),
    "palladium":   ("washout", "bear",   -8.0,  "Trough"),
    "copper":      ("normal",  "bull",    3.1,  "Expansion"),
    "corn":        ("blowoff", "bull",   14.2,  "Peak"),
    "wheat":       ("normal",  "neutral", 0.1,  "Recovery"),
    "soybeans":    ("blowoff", "bull",    8.1,  "Peak"),
    "live_cattle": ("normal",  "bull",    2.4,  "Expansion"),
    "coffee":      ("normal",  "bear",   -2.2,  "Downturn"),
    "sugar":       ("blowoff", "bull",   11.0,  "Peak"),
    "cocoa":       ("normal",  "bull",    6.3,  "Expansion"),
    "cotton":      ("normal",  "neutral", 0.8,  None),  # missing cycle → detail sentence
}

_STATE_SEED_SCRIPT = """
(state) => {
  try {
    localStorage.setItem('theme', state.theme);
    localStorage.removeItem('themeAuto');
    localStorage.setItem('lang', state.locale);
  } catch (e) {}
  // Skip theme.js skyToggleFx (1.05s sun/moon flourish). Receipt: theme.css
  // `.sky-fx` is a theme-toggle overlay at z-index 2147483600; setTheme()
  // appends it for 1100ms. A 150ms screenshot otherwise captures the disc
  // over the hero (light sun bloom / dark moon).
  window.__skyDeck = true;
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
  var fx = document.querySelector('.sky-fx');
  if (fx && fx.parentNode) fx.parentNode.removeChild(fx);
  var boot = document.getElementById('mmb-boot');
  if (boot && boot.parentNode) boot.parentNode.removeChild(boot);
  return {theme: docEl.getAttribute('data-theme'), locale: docEl.getAttribute('data-lang')};
}
"""

_OVERLAY_PROBE = """
() => {
  const hits = [];
  const push = (kind, el) => {
    if (!el) return;
    const st = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const vis = st.display !== 'none' && st.visibility !== 'hidden'
      && parseFloat(st.opacity || '1') > 0.05 && r.width > 2 && r.height > 2;
    if (vis) hits.push({kind, className: el.className || '', w: r.width, h: r.height});
  };
  push('sky-fx', document.querySelector('.sky-fx'));
  const disc = document.querySelector('.sky-fx .disc, span.disc');
  if (disc && disc.closest('.sky-fx')) push('sky-fx-disc', disc);
  push('mmb-boot', document.getElementById('mmb-boot'));
  document.querySelectorAll('.sky-fx, #mmb-boot, .mx5-aurora').forEach((el) => {
    const st = getComputedStyle(el);
    if (st.display !== 'none' && st.zIndex && parseInt(st.zIndex, 10) > 1000) {
      hits.push({kind: 'high-z', className: el.className || el.id, z: st.zIndex});
    }
  });
  return hits;
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


def fixture_vm() -> dict:
    """Current-shaped commodities VM. Sparse trees have no data/; this is the
    W6 r2 page-test idiom (test_hero_current_shaped_board_is_selective), not a
    live bake.
    """
    from datetime import date as _date

    from engine.commodity_confluence import _lbl
    from scripts.build_commodities import (
        CONVICTION_LABELS,
        MEMBER_LABELS,
        _GRID_GROUPS,
        _chg_tone,
        _conf_action,
        _heat_cell,
        _plain_cycle,
        _plain_cycle_state,
        _sync_read,
        resolve_catalyst_row,
        sector_stance,
    )

    names = [n for _k, _e, _z, ns in _GRID_GROUPS for n in ns]
    members = []
    for n in names:
        state = _STRETCHED.get(n, "Neutral")
        top = 72.0 if n in _STRETCHED else 0.0
        fired = [_lbl("shock_top"), _lbl("cot_long"), _lbl("overbought_ltf")] if n in _STRETCHED else []
        members.append({
            "name": n, "state": state,
            "top_score": top, "bottom_score": 0.0,
            "bottom_fired": [], "top_fired": fired,
        })
    conf = {"members": members, "index": {"state": "Neutral"}}
    breadth = {
        "n_members": 17, "n_up_trend": 11, "n_bull_momentum": 7,
        "n_low_risk": 8, "trend_diversity": 0.304,
    }
    stance = sector_stance(conf, breadth, index_shock="normal")
    sync = _sync_read(0.304)

    grid = []
    for _key, grp_en, grp_zh, grp_members in _GRID_GROUPS:
        cells = []
        for name in grp_members:
            shock, mom, chg, cycle = _HEAT[name]
            tone, st_en, st_zh = _heat_cell(shock, mom, _STRETCHED.get(name, "Neutral"))
            cyc_en, cyc_zh = _plain_cycle_state(cycle, False) if cycle else ("", "")
            en, zh = MEMBER_LABELS[name]
            cells.append({
                "name": name, "label_en": en, "label_zh": zh,
                "chg_1m_pct": chg, "chg_tone": _chg_tone(tone, chg),
                "tone": tone, "state_short_en": st_en, "state_short_zh": st_zh,
                "cycle_phase_en": cyc_en or None, "cycle_phase_zh": cyc_zh or None,
                "dual_read": False, "igniting": False,
            })
        grid.append({"group": _key, "group_en": grp_en, "group_zh": grp_zh, "members": cells})

    def _detail(name: str) -> dict:
        en, zh = MEMBER_LABELS[name]
        shock, mom, chg, cycle = _HEAT[name]
        state = _STRETCHED.get(name, "Neutral")
        action_en, action_zh = _conf_action(state)
        cyc_en, cyc_zh = _plain_cycle_state(cycle, False) if cycle else ("", "")
        shock_en, shock_zh = ("", "")
        if shock == "blowoff":
            shock_en, shock_zh = "Blow-off", "喷发"
        elif shock == "washout":
            shock_en, shock_zh = "Washing out", "洗盘"
        dollar_dir = dollar_eff = None
        if name == "oil":
            dollar_dir, dollar_eff = "up", "headwind"
        top_fired = [_lbl("shock_top"), _lbl("cot_long")] if name in _STRETCHED else []
        return {
            "name": name, "label_en": en, "label_zh": zh, "available": True,
            "price": None, "chg_1m_pct": chg,
            "action_en": action_en, "action_zh": action_zh, "state": state,
            "bot_score": 0, "top_score": 72 if name in _STRETCHED else 12,
            "bottom_fired": [], "top_fired": top_fired,
            "cycle_phase": cycle, "cycle_phase_en": cyc_en or None,
            "cycle_phase_zh": cyc_zh or None, "cycle_hazard": False,
            "shock_state": shock, "shock_en": shock_en, "shock_zh": shock_zh,
            "mtf_rows": [
                {"key": "D", "label": "Daily", "label_zh": "日线",
                 "rsi14": 62, "rsi5": 58, "stoch": 71, "macd": "pos", "trend": "up"},
                {"key": "W", "label": "Weekly", "label_zh": "周线",
                 "rsi14": 55, "rsi5": 51, "stoch": 64, "macd": "up", "trend": "up"},
            ],
            "verdict": {"headline": "Signals mostly agree.", "headline_zh": "信号大体一致。"},
            "is_core4": name in {"gold", "silver", "copper", "oil"},
            "dollar_usd_dir": dollar_dir, "dollar_effect": dollar_eff,
            "basing": False, "igniting": False, "turn_developing": False,
            "conviction": {
                "action": "HOLD", "action_css": "hold", "score": 8,
                "sub": "Weighted by how these calls have actually worked out.",
                "sub_zh": "权重依据这些判断的实际效果。",
            } if name in {"gold", "silver", "copper", "oil"} else None,
        }

    detail = [_detail(n) for n in names]

    tops = []
    for n, state in _STRETCHED.items():
        en, zh = MEMBER_LABELS[n]
        action_en, action_zh = _conf_action(state)
        tops.append({
            "name": n, "label_en": en, "label_zh": zh, "state": state,
            "action_en": action_en, "action_zh": action_zh, "score": 72,
            "receipt": [_lbl("shock_top"), _lbl("cot_long"), _lbl("overbought_ltf")],
        })

    phases: dict[str, list[str]] = {}
    for n, (_s, _m, _c, ph) in _HEAT.items():
        if ph:
            phases.setdefault(ph, []).append(n)
    cycle_summary = []
    for phase, ns in sorted(phases.items()):
        pe, pz = _plain_cycle(phase)
        cycle_summary.append({
            "phase": phase, "phase_en": pe, "phase_zh": pz, "count": len(ns),
            "names_en": [MEMBER_LABELS[n][0] for n in ns],
            "names_zh": [MEMBER_LABELS[n][1] for n in ns],
        })
    cycle_dominant = max(cycle_summary, key=lambda e: e["count"]) if cycle_summary else None

    vm = {
        "stance": stance,
        "breadth": {
            "n_up_trend": 11, "n_members": 17, "n_bull_momentum": 7,
            "n_low_risk": 8, "trend_diversity": 0.30,
            "in_sync": sync["in_sync"], "sync_en": sync["sync_en"],
            "sync_zh": sync["sync_zh"],
        },
        "index": {
            "ew": 412, "chg_1m_pct": 2.4, "ts_trend": "up",
            "mtf_en": "Go with the trend", "mtf_zh": "顺势而为",
            "velocity_20": 0.4, "shock_state": "normal",
            "shock_en": "—", "shock_zh": "—", "benchmarks": {},
        },
        "cycle_summary": cycle_summary, "cycle_dominant": cycle_dominant,
        "board": {"tops": tops, "bottoms": []},
        "grid": grid, "detail": detail,
    }
    assets = [
        {"key": "gold",   "price_fmt": "2,641.20", "chg_1d": 0.4},
        {"key": "silver", "price_fmt": "31.12",    "chg_1d": 0.2},
        {"key": "copper", "price_fmt": "4.52",     "chg_1d": -0.1},
        {"key": "oil",    "price_fmt": "68.40",    "chg_1d": -0.6},
    ]
    complex_vm = {
        "regime": "Neutral", "dollar_dir": "strengthening", "growth_dir": "rising",
    }
    catalysts = [
        resolve_catalyst_row(
            {"date": "2026-09-16", "time_et": "14:00", "type": "FOMC",
             "label": "FOMC decision", "assets": ["gold", "oil"]},
            _date(2026, 9, 11),
        ),
        resolve_catalyst_row(
            {"date": "2026-09-17", "time_et": "10:30", "type": "EIA_WPSR",
             "label": "EIA crude/petroleum inventories", "assets": ["oil"]},
            _date(2026, 9, 11),
        ),
    ]
    timeline = [{
        "day": "2026-09-10", "daylabel": "2026-09-10",
        "events": [
            {"filter": "alloc", "label": "Allocation", "label_zh": "配置",
             "asset_label": "Oil · WTI", "asset_label_zh": "原油",
             "headline": "Model's oil exposure moved to full",
             "headline_zh": "模型原油敞口已调至满仓",
             "time": "14:00 UTC", "severity": "high",
             "detail": "The model's oil sleeve went from 40% to 100%.",
             "detail_zh": "模型原油仓位从 40% 调至 100%。"},
            {"filter": "shock", "label": "Shock", "label_zh": "冲击",
             "asset_label": "Corn", "asset_label_zh": "玉米",
             "headline": "Corn printed a blow-off residual",
             "headline_zh": "玉米出现喷发残差",
             "time": "11:20 UTC", "severity": "medium",
             "detail": "Shock z moved through the blow-off band.",
             "detail_zh": "冲击 z 值进入喷发区间。"},
        ],
    }]
    return {
        "vm": vm, "assets": assets, "complex": complex_vm,
        "catalysts": catalysts, "timeline": timeline,
        "as_of": "Sep 10, 2026", "built": "2026-09-10 12:00 UTC",
        "cal_span": "2000-01-03..2026-09-10",
        "timeline_days": 30, "n_alerts": 2,
        "oil_episode": None, "coverage": None,
        "idx_ew_spark": [380, 385, 390, 398, 392, 405, 410, 412],
        "conviction_labels": CONVICTION_LABELS,
        "order": ["gold", "silver", "copper", "oil"],
    }


def render_page(ctx: dict | None = None) -> str:
    from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
    from engine.i18n import td, tr
    from scripts.build_commodities import C

    stub = DictLoader({
        "_site_nav.html.j2": (
            "<!-- fixture: _site_nav omitted (two global nav families). "
            "theme.js is injected after render so setTheme/setLang exist. -->\n"
        ),
    })
    env = Environment(
        loader=ChoiceLoader([stub, FileSystemLoader(str(TEMPLATES_DIR))]),
        autoescape=True,
    )
    env.globals.update(tr=tr, td=td)
    html = env.get_template("commodities.html.j2").render(
        C=C, **(ctx or fixture_vm()),
    )
    hide = (
        "<style>"
        "#mmb-boot{display:none !important}"
        ".sky-fx{display:none !important}"
        ".dot{opacity:1}"  # skip staggered fade so ATF dots are fully on
        "</style>\n"
        '<script src="theme.js"></script>\n'
        "</body>"
    )
    if "</body>" not in html:
        raise RuntimeError("rendered commodities.html.j2 has no </body>")
    return html.replace("</body>", hide, 1)


def write_fixture_site(scratch: Path) -> None:
    scratch.mkdir(parents=True, exist_ok=True)
    shutil.copy(TEMPLATES_DIR / "theme.js", scratch / "theme.js")
    icons = TEMPLATES_DIR / "product-nav-icons.css"
    if icons.exists():
        shutil.copy(icons, scratch / "product-nav-icons.css")
    (scratch / "commodities_w6.html").write_text(render_page(), encoding="utf-8")


def _git_head_of_repo() -> tuple[str | None, str | None]:
    from scripts.capture_page_evidence import _git_head_sha

    head = _git_head_sha(REPO_ROOT)
    return head.sha, str(head.gitdir) if head.gitdir is not None else None


def _clip_union_js() -> str:
    return """
(sels) => {
  let x = Infinity, y = Infinity, r = -Infinity, b = -Infinity, n = 0;
  for (const s of sels) {
    document.querySelectorAll(s).forEach((el) => {
      const rect = el.getBoundingClientRect();
      if (rect.width < 2 || rect.height < 2) return;
      x = Math.min(x, rect.x); y = Math.min(y, rect.y);
      r = Math.max(r, rect.right); b = Math.max(b, rect.bottom); n += 1;
    });
  }
  if (!n) return null;
  const pad = 10;
  const vx = Math.max(0, x - pad), vy = Math.max(0, y - pad);
  return {
    x: vx, y: vy,
    width: Math.min(window.innerWidth - vx, r - x + 2 * pad),
    height: Math.min(window.innerHeight - vy, b - y + 2 * pad),
  };
}
"""


def _grains_sels() -> list[str]:
    return [".legend", ".grp:nth-of-type(3)", ".hgrid:nth-of-type(3)"]


def _capture_one(page, *, theme: str, locale: str, width: int, height: int,
                 clip_sels: list[str] | None, full_viewport: bool) -> tuple[bytes, list]:
    applied = page.evaluate(_APPLY_STATE_SCRIPT.strip(), {"theme": theme, "locale": locale}) or {}
    if applied.get("theme") != theme or applied.get("locale") != locale:
        raise RuntimeError(
            f"state mismatch: requested theme={theme} locale={locale} observed {applied!r}"
        )
    page.wait_for_timeout(80)
    overlay = page.evaluate(_OVERLAY_PROBE.strip()) or []
    if full_viewport:
        png = page.screenshot(type="png")
        return png, overlay
    if clip_sels:
        for sel in clip_sels:
            loc = page.locator(sel).first
            if loc.count():
                loc.scroll_into_view_if_needed()
        page.wait_for_timeout(60)
        box = page.evaluate(_clip_union_js().strip(), clip_sels)
        if not box or box.get("width", 0) < 4 or box.get("height", 0) < 4:
            png = page.screenshot(type="png")
        else:
            clip = {
                "x": max(0, float(box["x"])),
                "y": max(0, float(box["y"])),
                "width": min(float(width), float(box["width"])),
                "height": min(float(height), float(box["height"])),
            }
            png = page.screenshot(type="png", clip=clip)
        return png, overlay
    png = page.screenshot(type="png")
    return png, overlay


def _new_page(browser, *, width, height, locale, theme, touch=False):
    context = browser.new_context(
        viewport={"width": width, "height": height},
        locale="zh-CN" if locale == "zh" else "en-US",
        color_scheme=theme,
        device_scale_factor=1,
        has_touch=touch,
        is_mobile=touch and width <= 390,
    )
    state = {"theme": theme, "locale": locale}
    # Terminating semicolon: init-script concatenation trap (null-source pageerror).
    context.add_init_script(f"({_STATE_SEED_SCRIPT.strip()})({json.dumps(state)});")
    page = context.new_page()
    return context, page


def _capture(scratch: Path, subjects: set[str] | None = None) -> dict:
    from scripts.capture_page_evidence import CaptureUnavailable, serve_site_dir

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise CaptureUnavailable(f"playwright is not importable: {exc}") from exc

    httpd, port = serve_site_dir(scratch)
    base = f"http://127.0.0.1:{port}/commodities_w6.html"
    sha, gitdir = _git_head_of_repo()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pages: list[dict] = []
    written: set[str] = set()
    aliases: dict[str, str] = {}

    jobs: list[dict] = []
    # 8 base ATF viewport shots.
    for viewport, (width, height) in VIEWPORTS.items():
        for locale in LOCALES:
            for theme in THEMES:
                jobs.append({
                    "subject": "atf", "viewport": viewport, "locale": locale,
                    "theme": theme, "width": width, "height": height,
                    "full_viewport": True, "clip_sels": None, "action": None,
                    "touch": False,
                })
    # (a) heat-grid legend + Sugar/Corn/Soybeans — both art directions, both langs, both widths.
    for viewport, (width, height) in VIEWPORTS.items():
        for locale in LOCALES:
            for theme in THEMES:
                jobs.append({
                    "subject": "a-heat-blowoff", "viewport": viewport, "locale": locale,
                    "theme": theme, "width": width, "height": height,
                    "full_viewport": False, "clip_sels": [".legend", ".grp", ".hgrid"],
                    "action": "scroll-grains", "touch": False,
                })
    # R-M1: heating oil is board-stretched + normal/bull → Extended (amber edge).
    for locale in LOCALES:
        for theme in THEMES:
            jobs.append({
                "subject": "a-heat-extended", "viewport": "desktop", "locale": locale,
                "theme": theme, "width": 1440, "height": 900,
                "full_viewport": False, "clip_sels": [".legend", ".grp", ".hgrid"],
                "action": "scroll-energy-heat", "touch": False,
            })
    # (b) live strip + oil grid cell.
    for theme in THEMES:
        jobs.append({
            "subject": "b-live-oil", "viewport": "desktop", "locale": "en",
            "theme": theme, "width": 1440, "height": 900,
            "full_viewport": False,
            "clip_sels": [".live-strip", ".grp", ".hgrid"],
            "action": "scroll-energy", "touch": False,
        })
    # (d) missing cycle sentence on cotton.
    for theme in THEMES:
        for locale in LOCALES:
            jobs.append({
                "subject": "d-cycle-missing", "viewport": "desktop", "locale": locale,
                "theme": theme, "width": 1440, "height": 900,
                "full_viewport": False, "clip_sels": ['.dpanel[data-detpanel="cotton"]'],
                "action": "open-cotton", "touch": False,
            })
    # (e) dollar value (oil) + omitted (cotton).
    jobs.append({
        "subject": "e-dollar-value", "viewport": "desktop", "locale": "en",
        "theme": "dark", "width": 1440, "height": 900,
        "full_viewport": False, "clip_sels": ['.dpanel[data-detpanel="oil"] .det > .panel'],
        "action": "open-oil", "touch": False,
    })
    jobs.append({
        "subject": "e-dollar-omitted", "viewport": "desktop", "locale": "en",
        "theme": "dark", "width": 1440, "height": 900,
        "full_viewport": False, "clip_sels": ['.dpanel[data-detpanel="cotton"] .det > .panel'],
        "action": "open-cotton", "touch": False,
    })
    # (f) ZH catalysts + timeline, dark+light (art direction).
    for theme in THEMES:
        jobs.append({
            "subject": "f-catalysts-zh", "viewport": "desktop", "locale": "zh",
            "theme": theme, "width": 1440, "height": 900,
            "full_viewport": False, "clip_sels": [".cat-list", ".disclaimer"],
            "action": "scroll-catalysts", "touch": False,
        })
        jobs.append({
            "subject": "f-timeline-zh", "viewport": "desktop", "locale": "zh",
            "theme": theme, "width": 1440, "height": 900,
            "full_viewport": False, "clip_sels": [".timeline", ".tl-filters"],
            "action": "scroll-timeline", "touch": False,
        })
    # (g) keyboard + tap.
    jobs.append({
        "subject": "g-lens-keyboard", "viewport": "desktop", "locale": "en",
        "theme": "dark", "width": 1440, "height": 900,
        "full_viewport": False, "clip_sels": [".sechd", ".board"],
        "action": "focus-lens", "touch": False,
    })
    jobs.append({
        "subject": "g-lens-tap", "viewport": "mobile", "locale": "en",
        "theme": "dark", "width": 390, "height": 844,
        "full_viewport": True, "clip_sels": None,
        "action": "tap-lens", "touch": True,
    })
    if subjects:
        jobs = [j for j in jobs if j["subject"] in subjects]

    try:
        manager = sync_playwright().start()
        try:
            browser = manager.chromium.launch(headless=True)
        except Exception as exc:
            manager.stop()
            raise CaptureUnavailable(f"no chromium binary is installed: {exc}") from exc
        try:
            by_subject: dict[str, list[dict]] = {}
            for job in jobs:
                subject = job["subject"]
                theme, locale = job["theme"], job["locale"]
                width, height = job["width"], job["height"]
                viewport = job["viewport"]
                entry: dict = {
                    "viewport": viewport, "locale": locale, "theme": theme,
                    "access": "anonymous", "viewport_width": width,
                    "viewport_height": height, "force_state": None,
                    "subject": subject, "action": job.get("action"),
                }
                context, page = _new_page(
                    browser, width=width, height=height, locale=locale,
                    theme=theme, touch=bool(job.get("touch")),
                )
                try:
                    response = page.goto(base, wait_until="load", timeout=30000)
                    if response is None or not response.ok:
                        raise RuntimeError(f"HTTP {getattr(response, 'status', 'none')}")
                    page.wait_for_timeout(120)
                    applied0 = page.evaluate(
                        _APPLY_STATE_SCRIPT.strip(),
                        {"theme": theme, "locale": locale},
                    ) or {}
                    if applied0.get("theme") != theme or applied0.get("locale") != locale:
                        raise RuntimeError(
                            f"state mismatch: requested theme={theme} locale={locale} "
                            f"observed {applied0!r}"
                        )
                    page.wait_for_timeout(80)
                    action = job.get("action")
                    if action == "scroll-grains":
                        page.evaluate(
                            """() => {
                              const g = [...document.querySelectorAll('.grp')]
                                .find(el => /Grains|谷物/.test(el.textContent || ''));
                              if (g) g.scrollIntoView({block: 'center'});
                              else {
                                const legend = document.querySelector('.legend');
                                if (legend) legend.scrollIntoView({block: 'start'});
                              }
                            }"""
                        )
                    elif action == "scroll-energy-heat":
                        page.evaluate(
                            """() => {
                              const g = [...document.querySelectorAll('.grp')]
                                .find(el => /Energy|能源/.test(el.textContent || ''));
                              if (g) g.scrollIntoView({block: 'center'});
                              else {
                                const legend = document.querySelector('.legend');
                                if (legend) legend.scrollIntoView({block: 'start'});
                              }
                            }"""
                        )
                    elif action == "scroll-energy":
                        page.evaluate(
                            """() => {
                              const live = document.querySelector('.live-strip');
                              if (live) live.scrollIntoView({block: 'start'});
                            }"""
                        )
                        box = page.evaluate(
                            """() => {
                              const live = document.querySelector('.live-strip');
                              const g = [...document.querySelectorAll('.grp')]
                                .find(el => /Energy|能源/.test(el.textContent || ''));
                              const grid = g ? g.nextElementSibling : null;
                              const els = [live, g, grid].filter(Boolean);
                              if (!els.length) return null;
                              let x=Infinity,y=Infinity,r=-Infinity,b=-Infinity;
                              for (const el of els) {
                                const rect = el.getBoundingClientRect();
                                x=Math.min(x,rect.x); y=Math.min(y,rect.y);
                                r=Math.max(r,rect.right); b=Math.max(b,rect.bottom);
                              }
                              const pad=10;
                              return {
                                x: Math.max(0, x-pad), y: Math.max(0, y-pad),
                                width: Math.min(window.innerWidth, r-x+2*pad),
                                height: Math.min(window.innerHeight, b-y+2*pad)
                              };
                            }"""
                        )
                        if box and box.get("width", 0) >= 4:
                            job["_direct_clip"] = box
                    elif action == "open-cotton":
                        page.locator('.dtab[data-det="cotton"]').click()
                        page.wait_for_timeout(80)
                        page.locator('.dpanel[data-detpanel="cotton"]').first.scroll_into_view_if_needed()
                    elif action == "open-oil":
                        page.locator('.dtab[data-det="oil"]').click()
                        page.wait_for_timeout(80)
                        page.locator('.dpanel[data-detpanel="oil"]').first.scroll_into_view_if_needed()
                    elif action == "scroll-catalysts":
                        page.locator(".cat-list").first.scroll_into_view_if_needed()
                    elif action == "scroll-timeline":
                        page.locator(".timeline").first.scroll_into_view_if_needed()
                    elif action == "focus-lens":
                        page.locator(".board").first.scroll_into_view_if_needed()
                        btn = page.locator(".rcpt-list .lens-q").first
                        btn.focus()
                        page.wait_for_timeout(180)
                        page.wait_for_selector(".lens-pop.open", timeout=4000)
                        box = page.evaluate(
                            """() => {
                              const board = document.querySelector('.board');
                              const pop = document.querySelector('.lens-pop.open');
                              const els = [board, pop].filter(Boolean);
                              let x=Infinity,y=Infinity,r=-Infinity,b=-Infinity;
                              for (const el of els) {
                                const rect = el.getBoundingClientRect();
                                x=Math.min(x,rect.x); y=Math.min(y,rect.y);
                                r=Math.max(r,rect.right); b=Math.max(b,rect.bottom);
                              }
                              const pad=12;
                              return {
                                x: Math.max(0, x-pad),
                                y: Math.max(0, y-pad),
                                width: Math.min(window.innerWidth - Math.max(0, x-pad), r-x+2*pad),
                                height: Math.min(window.innerHeight, b-y+2*pad)
                              };
                            }"""
                        )
                        if box and box.get("width", 0) >= 4:
                            job["_direct_clip"] = box
                    elif action == "tap-lens":
                        page.locator(".board").first.scroll_into_view_if_needed()
                        btn = page.locator(".rcpt-list .lens-q").first
                        btn.scroll_into_view_if_needed()
                        # DOM click, not Playwright tap/hover: pointerover+click on a
                        # non-(hover:none) harness flashes the dedicated .lens-q shut.
                        btn.evaluate("el => el.click()")
                        page.wait_for_selector(".lens-pop.open", timeout=4000)
                        page.wait_for_timeout(280)
                        job["tap_opened"] = True
                        job["hover_none"] = page.evaluate(
                            "() => window.matchMedia('(hover: none)').matches"
                        )
                        box = page.evaluate(
                            """() => {
                              const pop = document.querySelector('.lens-pop.open');
                              if (!pop) return null;
                              const rect = pop.getBoundingClientRect();
                              const pad = 8;
                              return {
                                x: Math.max(0, rect.x - pad),
                                y: Math.max(0, rect.y - pad),
                                width: Math.min(window.innerWidth, rect.width + 2 * pad),
                                height: Math.min(window.innerHeight, rect.height + 2 * pad)
                              };
                            }"""
                        )
                        if box and box.get("width", 0) >= 4 and box.get("height", 0) >= 4:
                            job["_direct_clip"] = box
                            job["full_viewport"] = False
                    clip_sels = job.get("clip_sels")
                    if action in ("scroll-grains", "scroll-energy-heat"):
                        needle = "Energy|能源" if action == "scroll-energy-heat" else "Grains|谷物"
                        box = page.evaluate(
                            """(needle) => {
                              const legend = document.querySelector('.legend');
                              const re = new RegExp(needle);
                              const g = [...document.querySelectorAll('.grp')]
                                .find(el => re.test(el.textContent || ''));
                              const grid = g ? g.nextElementSibling : null;
                              const els = [legend, g, grid].filter(Boolean);
                              if (!els.length) return null;
                              let x=Infinity,y=Infinity,r=-Infinity,b=-Infinity;
                              for (const el of els) {
                                const rect = el.getBoundingClientRect();
                                x=Math.min(x,rect.x); y=Math.min(y,rect.y);
                                r=Math.max(r,rect.right); b=Math.max(b,rect.bottom);
                              }
                              const pad=10;
                              return {
                                x: Math.max(0, x-pad), y: Math.max(0, y-pad),
                                width: Math.min(window.innerWidth, r-x+2*pad),
                                height: Math.min(window.innerHeight, b-y+2*pad)
                              };
                            }""",
                            needle,
                        )
                        if box and box.get("width", 0) >= 4:
                            clip_sels = None
                            job["_direct_clip"] = box
                    overlay = page.evaluate(_OVERLAY_PROBE.strip()) or []
                    if job.get("_direct_clip"):
                        png = page.screenshot(type="png", clip=job["_direct_clip"])
                    elif job.get("full_viewport"):
                        png = page.screenshot(type="png")
                    else:
                        png, overlay = _capture_one(
                            page, theme=theme, locale=locale, width=width, height=height,
                            clip_sels=clip_sels, full_viewport=False,
                        )
                    name, digest, pw, ph = content_address_png(png, CELLS_DIR)
                    alias = f"{subject}-{theme}-{locale}-{viewport}.png"
                    (CELLS_DIR / alias).write_bytes(png)
                    written.add(name)
                    written.add(alias)
                    aliases[alias] = name
                    overlay_clean = not overlay
                    entry.update({
                        "captured": True, "file": name, "alias": alias,
                        "sha256": digest, "bytes": len(png), "width": pw, "height": ph,
                        "applied_theme": theme, "applied_locale": locale,
                        "overlay": overlay, "overlay_clean": overlay_clean,
                    })
                    if "tap_opened" in job:
                        entry["tap_opened"] = job["tap_opened"]
                    if "hover_none" in job:
                        entry["hover_none"] = job["hover_none"]
                except Exception as exc:
                    entry.update({
                        "captured": False,
                        "reason": f"{type(exc).__name__}: {exc}",
                        "overlay_clean": False,
                    })
                finally:
                    context.close()
                by_subject.setdefault(subject, []).append(entry)
                flag = "ok" if entry.get("captured") else "FAIL"
                print(f"  {subject} {theme}/{locale}/{viewport}: {flag}", flush=True)

            for subject, states in by_subject.items():
                pages.append({
                    "page_id": f"commodities.html#{subject}",
                    "route": "/commodities_w6.html",
                    "registry_route": "/commodities.html",
                    "route_kind": "commodities_w6_subject",
                    "subject": subject,
                    "states": states, "metrics": {},
                    "console_errors": [], "failed_responses": [], "gaps": [],
                })
        finally:
            browser.close()
            manager.stop()
    finally:
        httpd.shutdown()

    attempted = sum(len(p["states"]) for p in pages)
    captured = sum(1 for p in pages for s in p["states"] if s.get("captured"))
    outcome = "captured" if captured == attempted and attempted else "partial"
    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": generated_at,
        "tool": {
            "module_ref": "scripts/capture_commodities_w6_evidence.py",
            "version": "w6-r3-element",
            "capture_method": (
                "playwright viewport/clip screenshot on a fixture-rendered "
                "commodities.html.j2 (page CSS + _state_inks + _vector_polish + "
                "theme.js). data-theme/data-lang applied via window.setTheme/"
                "setLang with refuse-on-mismatch. window.__skyDeck skips "
                "skyToggleFx. sha256 from the screenshot bytes."
            ),
        },
        "target": {
            "kind": "fixture_site_dir",
            "base_url": None,
            "site_dir": str(scratch),
            "resolved_sha_or_none": sha,
            "resolved_gitdir_or_none": gitdir,
            "resolved_sha_source": (
                "HEAD of the capture checkout; scratch is a throwaway "
                "fixture render, not live site/commodities.html"
            ),
        },
        "axes": {
            "viewports": {name: list(size) for name, size in VIEWPORTS.items()},
            "locales": list(LOCALES),
            "themes": list(THEMES),
            "access": ["anonymous"],
            "subjects": [p["subject"] for p in pages],
            "force_states": [],
        },
        "selection": {"mode": "explicit_subjects", "subjects": [p["subject"] for p in pages]},
        "aliases": aliases,
        "excluded": [],
        "outcome": outcome,
        "totals": {
            "pages": len(pages),
            "states_attempted": attempted,
            "states_captured": captured,
        },
        "honesty": {
            "access": "anonymous only",
            "gaps": "uncaptured cells are recorded with a reason",
            "authority": "this tool screenshots; it scores nothing",
            "page": (
                "commodities.html.j2 rendered with a current-shaped fixture VM "
                "(3 of 17 stretched → In favour). No data/ reads. Omitted vs live: "
                "_site_nav chrome, live.js quote hydration, oil-episode banner, "
                "coverage matrix, Inter webfonts (system fallback). "
                "Capture sets window.__skyDeck and strips leftover .sky-fx / "
                "#mmb-boot so the 1.05s sun/moon flourish and the brain FAB are "
                "not photographed; live theme toggles still play the flourish."
            ),
        },
        "pages": pages,
    }
    return {"manifest": manifest, "written": sorted(written), "outcome": outcome}


def _write_readme(manifest: dict) -> str:
    lines = [
        "# Commodities W6 — evidence matrix (round 4)",
        "",
        "Packet REQUIRED EVIDENCE MATRIX: dark × light × EN × ZH × 1440/390 "
        "(8 base shots) plus named proof crops (a)–(g).",
        "",
        "## Fixture",
        "",
        "- Source: `templates/commodities.html.j2` + page-scoped `<style>` + "
        "`_state_inks.html.j2` + `_vector_polish.html.j2`.",
        "- VM: `scripts/capture_commodities_w6_evidence.fixture_vm` "
        "(current-shaped board from `tests/test_commodities_w6_truth.py::"
        "test_hero_current_shaped_board_is_selective`: heating oil / corn / "
        "soybeans stretched → hero **In favour — 3 of 17 stretched**).",
        "- Theme/lang: Playwright seeds localStorage then calls `window.setTheme` / "
        "`window.setLang`; a mismatch refuses the cell.",
        "- `window.__skyDeck = true` in the init script (skyToggleFx bow-out) and "
        "any leftover `.sky-fx` is removed after apply.",
        "",
        "## Honest differences from live `site/commodities.html`",
        "",
        "- No `_site_nav` chrome (two global nav families; this crop is the page wrap).",
        "- No live.js hydration — live tiles keep the SSR 1-day change.",
        "- No oil-episode cross-asset banner (so the hero is the first content element).",
        "- No coverage-matrix rows (fixture `coverage=None`).",
        "- Inter webfonts are not copied into the scratch; system UI fonts render.",
        "- Numbers are representative (as of Sep 10, 2026), not that night's bake.",
        "- Sparse checkout has no `data/`; this is why the page is fixture-rendered.",
        "- `#mmb-boot` (brain FAB) and `.sky-fx` are stripped for capture; live still shows both on toggle.",
        "",
        "## Cells",
        "",
        "| Subject | Theme | Lang | Viewport | Alias | Captured | Overlay clean |",
        "|---|---|---|---|---|---|---|",
    ]
    for page in manifest["pages"]:
        for st in page["states"]:
            overlay = "yes" if st.get("overlay_clean") else (
                "NO: " + json.dumps(st.get("overlay") or st.get("reason"))
                if st.get("captured") else st.get("reason", "no")
            )
            lines.append(
                f"| {page['subject']} | {st.get('theme')} | {st.get('locale')} | "
                f"{st.get('viewport')} | `{st.get('alias', '')}` | "
                f"{'yes' if st.get('captured') else st.get('reason', 'no')} | {overlay} |"
            )
    lines += [
        "",
        "## Proof crops (a)–(g)",
        "",
        "Judged from the files after capture. Dark and light are two art directions.",
        "",
        "| Proof | What it must show | Aliases | Overlay | Verdict |",
        "|---|---|---|---|---|",
        "| (a) heat-grid blow-off | Legend (incl. Extended) beside Sugar/Corn/Soybeans; blow-off ≠ green | `a-heat-blowoff-*` | see table | PENDING-JUDGE |",
        "| (a2) Extended member | Heating oil amber-edge Extended, not green Momentum up | `a-heat-extended-*` | see table | PENDING-JUDGE |",
        "| (b) one number per window | Live oil 1-day beside oil grid 1-month | `b-live-oil-*` | see table | PENDING-JUDGE |",
        "| (c) ATF 1440 hero = board | Hero names counted members (Heating Oil, Corn, Soybeans) | `atf-*-desktop` | see table | PENDING-JUDGE |",
        "| (d) missing cycle | Cotton detail shows the sentence, not a dash | `d-cycle-missing-*` | see table | PENDING-JUDGE |",
        "| (e) Dollar row | Oil: value; cotton: omitted (never `Dollar: ·`) | `e-dollar-*` | see table | PENDING-JUDGE |",
        "| (f) ZH catalysts + timeline | Production-shaped label_zh; no EN leaks | `f-catalysts-zh-*`, `f-timeline-zh-*` | see table | PENDING-JUDGE |",
        "| (g) canonical LENS | `.lens-q` tap/focus; machine-term rc visible in `.lens-pop` | `g-lens-*` | see table | PENDING-JUDGE |",
        "",
        "## Capture-harness disclosure",
        "",
        "`theme.js` `skyToggleFx` appends a `.sky-fx` sun/moon disc for ~1100ms "
        "after every `setTheme`. This harness seeds `window.__skyDeck = true` "
        "(landing-hub bow-out) and removes any leftover `.sky-fx` after apply. "
        "The brain FAB (`#mmb-boot`) is stripped so it cannot sit on a crop. "
        "Live toggles still play the flourish. Per-crop overlay column is above.",
        "",
        "Commodities is a vector-family page: it does **not** link `theme.css`. "
        "Material is page `<style>` + `_state_inks` + `_vector_polish`. Loading "
        "`theme.css` in the fixture would be a second art direction, so it is not loaded.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--subjects", default="",
        help="comma-separated subjects to recapture; others are kept on disk",
    )
    args = ap.parse_args(argv)
    wanted = {s.strip() for s in args.subjects.split(",") if s.strip()} or None

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)
    if wanted:
        for stale in CELLS_DIR.glob("*.png"):
            if any(stale.name.startswith(f"{s}-") for s in wanted):
                stale.unlink()
    else:
        for stale in CELLS_DIR.glob("*.png"):
            stale.unlink()

    scratch = Path(tempfile.mkdtemp(prefix="cmdty_w6_evidence_"))
    try:
        print("rendering commodities.html.j2 (fixture VM)", flush=True)
        write_fixture_site(scratch)
        payloads = _capture(scratch, subjects=wanted)
        manifest = payloads["manifest"]
        man_path = OUT_DIR / "manifest.json"
        if wanted and man_path.exists():
            prev = json.loads(man_path.read_text(encoding="utf-8"))
            keep = [p for p in prev.get("pages", []) if p.get("subject") not in wanted]
            merged_pages = keep + manifest["pages"]
            prev.update({
                "generated_at": manifest["generated_at"],
                "pages": merged_pages,
                "aliases": {**prev.get("aliases", {}), **manifest.get("aliases", {})},
                "axes": manifest.get("axes", prev.get("axes")),
                "selection": manifest.get("selection"),
                "outcome": manifest["outcome"] if manifest["outcome"] != "captured"
                else prev.get("outcome", "captured"),
                "totals": {
                    "pages": len(merged_pages),
                    "states_attempted": sum(len(p["states"]) for p in merged_pages),
                    "states_captured": sum(
                        1 for p in merged_pages for s in p["states"] if s.get("captured")
                    ),
                },
            })
            manifest = prev
        man_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (OUT_DIR / "EVIDENCE.yml").write_text(
            "schema: mastermind.page_evidence_receipt.v1\n"
            "changed_paths:\n"
            "  - templates/commodities.html.j2\n"
            "manifest: mockups/evidence/commodities-w6/manifest.json\n",
            encoding="utf-8",
        )
        (OUT_DIR / "README.md").write_text(
            _write_readme(manifest), encoding="utf-8"
        )
        totals = manifest["totals"]
        print(
            f"outcome: {manifest.get('outcome')}\n"
            f"pages: {totals['pages']}  states: "
            f"{totals['states_captured']}/{totals['states_attempted']} captured",
            flush=True,
        )
        return 0 if payloads["outcome"] == "captured" else 1
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
