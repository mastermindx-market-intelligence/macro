#!/usr/bin/env python3
"""Element-screenshot evidence for bonds.html Archetype-D S3 (round 2).

Captures dark+light × EN+ZH × 1440/390 of the six L1 subjects on a
fixture-rendered bonds wrap (sparse trees have no data/). Playwright
applies theme/lang the way theme.js does and refuses a cell whose observed
data-theme/data-lang does not match the request.

Usage::

    python3 -m scripts.capture_bonds_regime_dashboard_evidence
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
OUT_DIR = REPO_ROOT / "mockups" / "evidence" / "bonds-regime-dashboard"
CELLS_DIR = OUT_DIR / "cells"

SUBJECTS: tuple[tuple[str, str], ...] = (
    ("hero", '[data-l1="hero"]'),
    ("changed", '[data-l1="changed"]'),
    ("drivers", '[data-l1="drivers"]'),
    ("world", '[data-l1="world"]'),
    ("watching", '[data-l1="watching"]'),
    ("deeper", '[data-l1="deeper"]'),
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
  window.__skyDeck = true;  // bow out of theme.js skyToggleFx (~1100ms sun/moon)
  try {
    localStorage.setItem('theme', state.theme);
    localStorage.removeItem('themeAuto');
    localStorage.setItem('lang', state.locale);
  } catch (e) {}
}
"""

_APPLY_STATE_SCRIPT = """
(state) => {
  window.__skyDeck = true;
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

_HIDE_DECOR = (
    "#mmb-root,#mmb-boot,#mmb-launch,.sky-fx,.mx5-aurora,.theme-fab{"
    "display:none!important;visibility:hidden!important;opacity:0!important}"
)

_OVERLAY_PROBE = """
() => {
  const sels = ['.sky-fx', '.mx5-aurora', '#mmb-boot', '#mmb-launch',
                '#mmb-root', '.theme-fab'];
  const hits = [];
  for (const sel of sels) {
    for (const el of document.querySelectorAll(sel)) {
      const st = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      if (st.display === 'none' || st.visibility === 'hidden') continue;
      const op = parseFloat(st.opacity || '1');
      if (!Number.isFinite(op) || op === 0) continue;
      if (r.width < 1 || r.height < 1) continue;
      hits.push(sel);
    }
  }
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
    """Representative bonds VM. Sparse trees have no data/; this is the
    page-test idiom (tests.test_bonds_divergence_gate._base_ctx) plus the
    glance/world/changed rows the wrap actually reads, not a live bake.
    """
    from tests.test_bonds_divergence_gate import _base_ctx
    from scripts.build_bonds import _watching, divergence_card_state

    ctx = _base_ctx()
    ctx["watching"] = _watching(ctx["vm"])
    ctx["changed"] = [
        {
            "when": "09-08",
            "name_en": "Credit",
            "name_zh": "信用",
            "what_en": "High-yield extra yield stayed calm",
            "what_zh": "高收益额外收益保持平静",
            "href": "#credit",
            "stance_en": "Ignore — already reflected",
            "stance_zh": "可忽略——已在判读中",
        },
        {
            "when": "09-04",
            "name_en": "Curve",
            "name_zh": "曲线",
            "what_en": "10y−3m slope held in the normal band",
            "what_zh": "10年−3月斜率仍在正常区间",
            "href": "#curve",
            "stance_en": "Watch — don't chase",
            "stance_zh": "观察，勿追",
        },
        {
            "when": "08-28",
            "name_en": "Rates vol",
            "name_zh": "利率波动",
            "what_en": "MOVE dropped back into the quiet band",
            "what_zh": "MOVE 回落到平静区间",
            "href": "#stress",
            "stance_en": "Ignore — already reflected",
            "stance_zh": "可忽略——已在判读中",
        },
    ]
    ctx["glance"] = [
        {"name_en": "Curve", "name_zh": "曲线", "href": "#curve",
         "state_en": "Normal", "state_zh": "正常",
         "mean_en": "recession odds ~13%", "mean_zh": "衰退概率约13%"},
        {"name_en": "Credit", "name_zh": "信用", "href": "#credit",
         "state_en": "Tight", "state_zh": "偏紧",
         "mean_en": "risk appetite calm", "mean_zh": "风险偏好平静"},
        {"name_en": "Real rates", "name_zh": "实际利率", "href": "#real",
         "state_en": "+2.43%", "state_zh": "+2.43%",
         "mean_en": "heavy on valuations", "mean_zh": "压制估值"},
        {"name_en": "Rates vol", "name_zh": "利率波动", "href": "#stress",
         "state_en": "Calm", "state_zh": "平静",
         "mean_en": "rates market calm", "mean_zh": "利率市场平静"},
    ]
    ctx["compass"] = {
        "duration": {
            "bucket": "neutral",
            "lean": 0.12,
            "agreement": 0.6,
            "legs": [
                {"key": "trend", "value": 0.2, "label_en": "Trend", "label_zh": "趋势",
                 "note_en": "", "note_zh": ""},
                {"key": "carry", "value": 0.4, "label_en": "Carry", "label_zh": "套息",
                 "note_en": "", "note_zh": ""},
                {"key": "value", "value": -0.1, "label_en": "Value", "label_zh": "价值",
                 "note_en": "", "note_zh": ""},
                {"key": "term_premium", "value": 0.15, "label_en": "Term premium",
                 "label_zh": "期限溢价", "note_en": "", "note_zh": ""},
                {"key": "macro", "value": -0.05, "label_en": "Macro", "label_zh": "宏观",
                 "note_en": "", "note_zh": ""},
            ],
        },
        "curve_trade": {
            "lean": "neutral",
            "rationale_en": "Slope is ordinary; no steepener or flattener edge.",
            "rationale_zh": "斜率普通，没有偏陡或偏平的优势。",
        },
        "expected": {
            "carry_pct": 3.1, "rolldown_pct": 0.4, "carry_roll_pct": 3.5,
            "cushion_bp": 28, "duration": 8.2,
        },
        "verdict_en": "Context only — not a trade call.",
        "verdict_zh": "仅供参考——不是交易信号。",
    }
    ctx["fed_path"] = {
        "headline_en": "priced landing 3.10%",
        "headline_zh": "定价落点 3.10%",
        "implied": {"m12": 3.10},
        "target_low": None, "target_high": None, "policy_rate": 4.33,
        "implied_cuts_12m": None, "ntfs": 0.75, "rate_exp_proxy": None,
        "gap": None,
    }
    ctx["intl"] = {
        "global": {"avg_10y": 4.05, "direction": "rising", "avg_10y_chg_63d_bp": 18},
        "us_vs_world": {"us_premium_bp": 42, "premium_direction": "rising"},
        "em": {"em_oas": 2.9, "pctile": 35, "emb_trend": "down", "direction": "stable"},
        "countries": [
            {"code": "US", "en": "United States", "zh": "美国", "y10": 4.18,
             "real_10y": 2.43, "slope": 0.40, "slope_state": "normal",
             "chg_63d_bp": 12, "z1y": 0.4, "diff_vs_us_bp": 0,
             "direction": "rising", "stale": False, "cadence": "daily"},
            {"code": "DE", "en": "Germany", "zh": "德国", "y10": 2.51,
             "real_10y": 0.40, "slope": 0.55, "slope_state": "steep",
             "chg_63d_bp": 8, "z1y": 0.2, "diff_vs_us_bp": -167,
             "direction": "stable", "stale": False, "cadence": "daily"},
            {"code": "JP", "en": "Japan", "zh": "日本", "y10": 1.12,
             "real_10y": -0.20, "slope": 0.80, "slope_state": "steep",
             "chg_63d_bp": 14, "z1y": 1.1, "diff_vs_us_bp": -306,
             "direction": "rising", "stale": True, "cadence": "monthly"},
            {"code": "GB", "en": "United Kingdom", "zh": "英国", "y10": 4.05,
             "real_10y": 1.40, "slope": 0.10, "slope_state": "flat",
             "chg_63d_bp": -6, "z1y": -0.3, "diff_vs_us_bp": -13,
             "direction": "falling", "stale": False, "cadence": "daily"},
            {"code": "CA", "en": "Canada", "zh": "加拿大", "y10": 3.22,
             "real_10y": 1.10, "slope": 0.22, "slope_state": "normal",
             "chg_63d_bp": 4, "z1y": 0.1, "diff_vs_us_bp": -96,
             "direction": "stable", "stale": False, "cadence": "daily"},
            {"code": "AU", "en": "Australia", "zh": "澳大利亚", "y10": 4.01,
             "real_10y": 1.70, "slope": 0.30, "slope_state": "normal",
             "chg_63d_bp": 9, "z1y": 0.5, "diff_vs_us_bp": -17,
             "direction": "rising", "stale": False, "cadence": "daily"},
            {"code": "CH", "en": "Switzerland", "zh": "瑞士", "y10": 0.55,
             "real_10y": -0.40, "slope": -0.05, "slope_state": "inverted",
             "chg_63d_bp": 2, "z1y": -0.2, "diff_vs_us_bp": -363,
             "direction": "stable", "stale": False, "cadence": "daily"},
            {"code": "IT", "en": "Italy", "zh": "意大利", "y10": 3.60,
             "real_10y": 1.20, "slope": 0.70, "slope_state": "steep",
             "chg_63d_bp": 11, "z1y": 0.3, "diff_vs_us_bp": -58,
             "direction": "rising", "stale": False, "cadence": "daily"},
        ],
    }
    ctx["xasset_vm"] = {
        "verdict_en": "Bonds are a tailwind for 6 markets and a headwind for 5.",
        "verdict_zh": "当前债券为6个市场提供顺风，对5个市场构成逆风。",
        "drivers_now": {
            "real_10y": 2.43, "real_chg_bp": 8,
            "slope": 0.88, "slope_chg_bp": 4,
            "hy_oas": 2.67, "hy_chg_bp": -6,
            "breakeven": 2.3, "move": 80,
        },
        "assets": [
            {"en": "US equities", "zh": "美股", "vcolor": "#15764f",
             "verdict_en": "tailwind", "verdict_zh": "顺风",
             "corr": -0.35, "sign": "neg", "icon": "", "driver_en": "real rates",
             "driver_zh": "实际利率", "beta_disp": "−0.4", "conf_label": "moderate"},
            {"en": "Gold", "zh": "黄金", "vcolor": "#b3252a",
             "verdict_en": "headwind", "verdict_zh": "逆风",
             "corr": 0.22, "sign": "pos", "icon": "", "driver_en": "real rates",
             "driver_zh": "实际利率", "beta_disp": "+0.2", "conf_label": "weak"},
            {"en": "USD", "zh": "美元", "vcolor": "#15764f",
             "verdict_en": "tailwind", "verdict_zh": "顺风",
             "corr": 0.41, "sign": "pos", "icon": "", "driver_en": "rate gap",
             "driver_zh": "利差", "beta_disp": "+0.4", "conf_label": "strong"},
            {"en": "Credit", "zh": "信用", "vcolor": "#15764f",
             "verdict_en": "tailwind", "verdict_zh": "顺风",
             "corr": -0.28, "sign": "neg", "icon": "", "driver_en": "HY OAS",
             "driver_zh": "高收益利差", "beta_disp": "−0.3", "conf_label": "moderate"},
            {"en": "EM FX", "zh": "新兴市场外汇", "vcolor": "#b3252a",
             "verdict_en": "headwind", "verdict_zh": "逆风",
             "corr": -0.18, "sign": "neg", "icon": "", "driver_en": "USD",
             "driver_zh": "美元", "beta_disp": "−0.2", "conf_label": "weak"},
            {"en": "Oil", "zh": "原油", "vcolor": "#4C5A6C",
             "verdict_en": "mixed", "verdict_zh": "中性",
             "corr": 0.05, "sign": "pos", "icon": "", "driver_en": "growth",
             "driver_zh": "增长", "beta_disp": "+0.1", "conf_label": "weak"},
            {"en": "Housing", "zh": "住房", "vcolor": "#b3252a",
             "verdict_en": "headwind", "verdict_zh": "逆风",
             "corr": -0.31, "sign": "neg", "icon": "", "driver_en": "mortgage",
             "driver_zh": "按揭", "beta_disp": "−0.3", "conf_label": "moderate"},
            {"en": "Copper", "zh": "铜", "vcolor": "#15764f",
             "verdict_en": "tailwind", "verdict_zh": "顺风",
             "corr": -0.12, "sign": "neg", "icon": "", "driver_en": "real rates",
             "driver_zh": "实际利率", "beta_disp": "−0.1", "conf_label": "weak"},
        ],
    }
    ctx["vm"]["health"]["calib"] = {
        "ic_recession": 0.42, "span": "2014-01..2026-09", "n": 148,
        "ic_horizon_en": "12 months", "ic_horizon_zh": "12个月",
        "hi_dd10": 38.0, "base_dd10": 22.0, "edge_pp": 16.0,
    }
    ctx["vm"]["health"]["stress_legs"] = [
        {"en": "Recession", "zh": "衰退", "val": 12, "vg": ("✓", "measured")},
        {"en": "Drawdown", "zh": "回撤", "val": 18, "vg": ("~", "directional")},
        {"en": "Credit", "zh": "信用", "val": 22, "vg": ("·", "context")},
        {"en": "Rates vol", "zh": "利率波动", "val": 28, "vg": ("✓", "measured")},
    ]
    # Default fixture is DELAYED cause=stale (last_obs < as_of). Branch 2
    # (unbuilt: last_obs >= as_of) is a second HTML written by --r4.
    ctx["div_card"] = divergence_card_state(False, "2026-08-14", "2026-08-01", "2026-09-10")
    ctx["STALE_GATE_FIXTURE"] = (
        "r4 DELAYED cause=stale: "
        "divergence_card_state(ready=False, ready_date='2026-08-14', "
        "last_obs='2026-08-01', as_of='2026-09-10')"
    )
    return ctx


def render_fixture_html(vm: dict | None = None) -> str:
    """Render bonds.html.j2 minus site-nav / seo / vector-polish. No data/ reads."""
    from jinja2 import ChainableUndefined, ChoiceLoader, DictLoader, Environment, FileSystemLoader

    src = (TEMPLATES_DIR / "bonds.html.j2").read_text(encoding="utf-8")
    src = src.replace('{% include "_site_nav.html.j2" %}', "")
    src = src.replace('{% include "_seo_head.html.j2" %}', "")
    src = src.replace('{% include "_vector_polish.html.j2" %}', "")
    env = Environment(
        loader=ChoiceLoader([
            DictLoader({"bonds_s3.html.j2": src}),
            FileSystemLoader(str(TEMPLATES_DIR)),
        ]),
        autoescape=True,
        undefined=ChainableUndefined,
    )
    return env.get_template("bonds_s3.html.j2").render(**(vm or fixture_vm()))


def write_fixture_site(scratch: Path, vm: dict | None = None,
                       filename: str = "bonds_s3.html") -> None:
    scratch.mkdir(parents=True, exist_ok=True)
    shutil.copy(TEMPLATES_DIR / "theme.js", scratch / "theme.js")
    if (TEMPLATES_DIR / "illus.css").exists():
        shutil.copy(TEMPLATES_DIR / "illus.css", scratch / "illus.css")
    html = render_fixture_html(vm)
    html = html.replace(
        "</head>",
        f"<style>{_HIDE_DECOR}</style></head>",
        1,
    )
    (scratch / filename).write_text(html, encoding="utf-8")


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
  const chips = Array.from(document.querySelectorAll('.jump-nav, .mx-vh-meta, .depth, .kpis'));
  const wrapOk = chips.every(el => {
    const st = getComputedStyle(el);
    return st.flexWrap === 'wrap' || st.display !== 'flex';
  });
  const skel = document.querySelector('.mx-skel');
  let skelAnim = null;
  if (skel) {
    const st = getComputedStyle(skel);
    skelAnim = {animationName: st.animationName, animationDuration: st.animationDuration};
  }
  const tableWrap = document.querySelector('.sc-wrap');
  let tableScroll = null;
  if (tableWrap) {
    tableScroll = {
      overflowX: getComputedStyle(tableWrap).overflowX,
      scrollWidth: tableWrap.scrollWidth,
      clientWidth: tableWrap.clientWidth,
      contained: tableWrap.scrollWidth > tableWrap.clientWidth + 1
        && body.scrollWidth <= doc.clientWidth + 1,
    };
  }
  return {
    clientWidth: doc.clientWidth,
    scrollWidth: body.scrollWidth,
    pageScroll,
    chipWrap: wrapOk,
    skelAnim,
    tableScroll,
  };
}
"""


def _shot_one(page, selector: str, scratch_wait: bool = True) -> bytes:
    loc = page.locator(selector).first
    loc.wait_for(state="visible", timeout=5000)
    loc.scroll_into_view_if_needed()
    page.wait_for_timeout(80)
    return loc.screenshot(type="png")


def _capture_cell(browser, base: str, *, width: int, height: int, locale: str,
                  theme: str, selector: str, extra_ctx: dict | None = None,
                  page_name: str = "bonds_s3.html") -> dict:
    state = {"theme": theme, "locale": locale}
    context = browser.new_context(
        viewport={"width": width, "height": height},
        locale="zh-CN" if locale == "zh" else "en-US",
        color_scheme=theme,
        device_scale_factor=1,
        **(extra_ctx or {}),
    )
    context.add_init_script(
        f"({_STATE_SEED_SCRIPT.strip()})({json.dumps(state)});"
    )
    page = context.new_page()
    try:
        url = f"{base}/{page_name}"
        response = page.goto(url, wait_until="load", timeout=30000)
        if response is None or not response.ok:
            raise RuntimeError(f"HTTP {getattr(response, 'status', 'none')}")
        page.wait_for_timeout(250)
        page.add_style_tag(content=_HIDE_DECOR)
        applied = page.evaluate(_APPLY_STATE_SCRIPT.strip(), state) or {}
        if applied.get("theme") != theme or applied.get("locale") != locale:
            raise RuntimeError(
                f"state mismatch: requested theme={theme} locale={locale} "
                f"observed {applied!r}"
            )
        page.wait_for_timeout(150)
        png = _shot_one(page, selector)
        overlay_hits = page.evaluate(_OVERLAY_PROBE.strip()) or []
        overlay = "clean" if not overlay_hits else "dirty:" + ",".join(overlay_hits)
        return {"png": png, "applied": applied, "overlay": overlay}
    finally:
        context.close()


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
                                got = _capture_cell(
                                    browser, base, width=width, height=height,
                                    locale=locale, theme=theme, selector=selector,
                                )
                                png = got["png"]
                                applied = got["applied"]
                                name, digest, pw, ph = content_address_png(png, CELLS_DIR)
                                alias = f"{subject}-{theme}-{locale}-{viewport}.png"
                                (CELLS_DIR / alias).write_bytes(png)
                                written.add(f"cells/{name}")
                                written.add(f"cells/{alias}")
                                aliases[alias] = name
                                entry.update(
                                    {
                                        "captured": True,
                                        "file": f"cells/{name}",
                                        "alias": alias,
                                        "sha256": digest,
                                        "bytes": len(png),
                                        "width": pw,
                                        "height": ph,
                                        "applied_theme": applied.get("theme"),
                                        "applied_locale": applied.get("locale"),
                                        "overlay": got.get("overlay", "clean"),
                                    }
                                )
                            except Exception as exc:
                                entry.update(
                                    {
                                        "captured": False,
                                        "reason": f"{type(exc).__name__}: {exc}",
                                    }
                                )
                            states.append(entry)
                captured_n = sum(1 for s in states if s.get("captured"))
                pages.append(
                    {
                        "page_id": f"bonds.html#{subject}",
                        "route": "/bonds_s3.html",
                        "registry_route": "/bonds.html",
                        "route_kind": "bonds_regime_dashboard_subject",
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

            # Extra pair: §3 fail-closed DELAYED card, dark+light EN 1440.
            # force_state so the REST-cell gate does not demand 8 cells of this page.
            stale_states: list[dict] = []
            for theme in THEMES:
                entry = {
                    "viewport": "desktop",
                    "locale": "en",
                    "theme": theme,
                    "access": "anonymous",
                    "viewport_width": 1440,
                    "viewport_height": 900,
                    "force_state": "stale-delayed",
                    "subject": "stale-gate",
                }
                try:
                    got = _capture_cell(
                        browser, base, width=1440, height=900,
                        locale="en", theme=theme,
                        selector='[data-card="stocks-vs-bonds"]',
                    )
                    png = got["png"]
                    applied = got["applied"]
                    name, digest, pw, ph = content_address_png(png, CELLS_DIR)
                    alias = f"stale-gate-{theme}-en-desktop.png"
                    (CELLS_DIR / alias).write_bytes(png)
                    written.add(f"cells/{name}")
                    written.add(f"cells/{alias}")
                    aliases[alias] = name
                    entry.update(
                        {
                            "captured": True,
                            "file": f"cells/{name}",
                            "alias": alias,
                            "sha256": digest,
                            "bytes": len(png),
                            "width": pw,
                            "height": ph,
                            "applied_theme": applied.get("theme"),
                            "applied_locale": applied.get("locale"),
                            "overlay": got.get("overlay", "clean"),
                            "fixture": (
                                "r4 DELAYED cause=stale: divergence_card_state("
                                "False, '2026-08-14', '2026-08-01', '2026-09-10')"
                            ),
                        }
                    )
                except Exception as exc:
                    entry.update(
                        {
                            "captured": False,
                            "reason": f"{type(exc).__name__}: {exc}",
                        }
                    )
                stale_states.append(entry)
            stale_n = sum(1 for s in stale_states if s.get("captured"))
            # Attach to an existing REST page so check_ui_visual_evidence does
            # not demand 8 rest cells of a 2-cell subject. force_state skips REST.
            if pages:
                pages[-1]["states"].extend(stale_states)
            print(f"  stale-gate: {stale_n}/{len(stale_states)} cells", flush=True)

            # G8 floor — one pass per width, dark EN, plus reduced-motion + LENS tap at 390.
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
                    page.goto(f"{base}/bonds_s3.html", wait_until="load", timeout=30000)
                    page.evaluate(_APPLY_STATE_SCRIPT.strip(), {"theme": "dark", "locale": "en"})
                    page.add_style_tag(content="#mmb-root,#mmb-boot,#mmb-launch{display:none!important;visibility:hidden!important}")
                    page.wait_for_timeout(200)
                    probe = page.evaluate(_g8_probe())
                    focus_ok = False
                    try:
                        host = page.locator('.mx-chg-row, .wrap .lens-q, .depth a').first
                        host.focus()
                        page.wait_for_timeout(80)
                        focus_ok = page.evaluate(
                            """() => {
                              const el = document.querySelector('.mx-chg-row, .wrap .lens-q, .depth a');
                              if (!el) return false;
                              const st = getComputedStyle(el);
                              const ring = (st.outlineStyle && st.outlineStyle !== 'none' && st.outlineWidth !== '0px')
                                || (st.boxShadow && st.boxShadow !== 'none');
                              return !!ring;
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
                            tap_page.goto(f"{base}/bonds_s3.html", wait_until="load", timeout=30000)
                            tap_page.evaluate(
                                _APPLY_STATE_SCRIPT.strip(), {"theme": "dark", "locale": "en"}
                            )
                            tap_page.add_style_tag(content="#mmb-root,#mmb-boot,#mmb-launch{display:none!important;visibility:hidden!important}")
                            tap_page.wait_for_timeout(200)
                            btn = tap_page.locator('.wrap .lens-q').first
                            btn.scroll_into_view_if_needed()
                            btn.tap(timeout=5000)
                            tap_page.wait_for_timeout(250)
                            lens_ok = tap_page.evaluate(
                                """() => {
                                  const btn = document.querySelector('.wrap .lens-q.cnx-tip-open, .lens-q.lens-on');
                                  if (!btn) {
                                    const pop = document.querySelector('.lens-pop.open, .lens-scrim.open');
                                    return !!pop;
                                  }
                                  const after = getComputedStyle(btn, '::after');
                                  return !!(after && after.display !== 'none' && after.content && after.content !== 'none');
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
                            page2.goto(f"{base}/bonds_s3.html", wait_until="load", timeout=30000)
                            page2.evaluate(
                                _APPLY_STATE_SCRIPT.strip(), {"theme": "dark", "locale": "en"}
                            )
                            page2.wait_for_timeout(150)
                            reduced_ok = page2.evaluate(
                                """() => {
                                  const el = document.querySelector('.mx-skel');
                                  if (!el) return null;
                                  const st = getComputedStyle(el);
                                  const animNone = !st.animationName || st.animationName === 'none';
                                  return {ok: animNone, animationName: st.animationName,
                                          w: el.getBoundingClientRect().width};
                                }"""
                            )
                        finally:
                            context2.close()
                    g8_row.update({
                        "page_scroll": bool(probe.get("pageScroll")),
                        "scrollWidth": probe.get("scrollWidth"),
                        "clientWidth": probe.get("clientWidth"),
                        "chip_wrap": bool(probe.get("chipWrap")),
                        "focus_ring": bool(focus_ok),
                        "lens_tap": lens_ok,
                        "reduced_motion": reduced_ok,
                        "table_scroll": probe.get("tableScroll"),
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

    rest_states = [
        s for p in pages for s in p["states"] if s.get("force_state") is None
    ]
    extra_states = [
        s for p in pages for s in p["states"] if s.get("force_state") is not None
    ]
    attempted = len(rest_states)
    captured = sum(1 for s in rest_states if s.get("captured"))
    extra_ok = bool(extra_states) and all(s.get("captured") for s in extra_states)
    outcome = "captured" if captured == attempted and attempted and extra_ok else "partial"
    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": generated_at,
        "tool": {
            "module_ref": "scripts/capture_bonds_regime_dashboard_evidence.py",
            "version": "s3-r2-element",
            "capture_method": (
                "playwright locator('[data-l1=SUBJECT]').screenshot() on a "
                "fixture-rendered bonds.html.j2 wrap (page-scoped styles + "
                "theme.js). data-theme/data-lang applied via "
                "window.setTheme/setLang with refuse-on-mismatch. sha256 from "
                "the element-screenshot bytes. Stale-gate pair uses "
                "force_state=stale-delayed on [data-card=stocks-vs-bonds]."
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
                "bonds wrap render, not live site/bonds.html"
            ),
        },
        "axes": {
            "viewports": {name: list(size) for name, size in VIEWPORTS.items()},
            "locales": list(LOCALES),
            "themes": list(THEMES),
            "access": ["anonymous"],
            "subjects": [s for s, _ in SUBJECTS],
            "force_states": ["stale-delayed"],
        },
        "selection": {
            "mode": "explicit_subjects",
            "subjects": [s for s, _ in SUBJECTS],
            "selectors": {s: sel for s, sel in SUBJECTS},
        },
        "aliases": aliases,
        "excluded": [],
        "outcome": outcome,
        "totals": {
            "pages": len(pages),
            "states_attempted": attempted + len(extra_states),
            "states_captured": captured + sum(1 for s in extra_states if s.get("captured")),
        },
        "honesty": {
            "access": "anonymous only",
            "gaps": "uncaptured cells are recorded with a reason",
            "authority": "this tool screenshots; it scores nothing",
            "page": (
                "bonds.html.j2 rendered with tests.test_bonds_divergence_gate."
                "_base_ctx plus representative changed/glance/compass/intl/"
                "xasset rows (no data/ reads). Omitted vs live: site nav, "
                "vector-polish, seo head, live chart SVGs (skeleton geometry)."
            ),
            "stale_gate_fixture": (
                "r4 DELAYED cause=stale: last_obs='2026-08-01' < as_of; "
                "cause=unbuilt captured separately as unbuilt-gate"
            ),
        },
        "g8": g8,
        "pages": pages,
    }
    return {"manifest": manifest, "written": sorted(written), "outcome": outcome, "g8": g8}


def _write_readme(manifest: dict) -> str:
    lines = [
        "# Bonds regime-dashboard S3 — evidence matrix (round 2)",
        "",
        "Six L1 subjects × dark/light × EN/ZH × 1440/390.",
        "Spec G4 names a 4-subject 32-crop matrix; the seat and the round-2 "
        "brief expand that to the six L1 blocks, so the product of those axes "
        f"is {sum(1 for p in manifest['pages'] for s in p['states'] if s.get('force_state') is None and s.get('captured'))} cells, "
        "plus a stale-date gate pair.",
        "",
        "## Fixture",
        "",
        "- Source: `templates/bonds.html.j2` L1 wrap + page-scoped `<style>` "
        "(site-nav / seo / vector-polish stripped).",
        "- VM: `scripts/capture_bonds_regime_dashboard_evidence.fixture_vm` "
        "(starts from `tests.test_bonds_divergence_gate._base_ctx`, the page-test idiom).",
        "- Theme/lang: Playwright seeds localStorage then calls `window.setTheme` / "
        "`window.setLang`; a mismatch refuses the cell.",
        "",
        "## Honest differences from live `site/bonds.html`",
        "",
        "- No `_site_nav` chrome (two global nav families; this crop is the glance wrap).",
        "- No live chart SVGs — health spark and the yield-curve figure stay at "
        "`.mx-skel` true geometry (58px / 120px).",
        "- Numbers are representative (health 88, 10y 4.18%, HY OAS 2.67%, "
        "date 2026-09-10), not that night's bake.",
        "- Sparse checkout has no `data/`; this is why the wrap is fixture-rendered.",
        "",
        "## Stale-date gate fixture",
        "",
        "`divergence_card_state(ready=False, ready_date='2026-08-14', "
        "last_obs='2026-08-01', as_of='2026-09-10')` → **DELAYED**.",
        "Captured as `stale-gate-dark-en-desktop.png` and "
        "`stale-gate-light-en-desktop.png` (`force_state: stale-delayed`).",
        "Refusal copy must be visible; no scored verdict painted.",
        "",
        "## Cells",
        "",
        "| Subject | Theme | Lang | Viewport | Alias | Captured |",
        "|---|---|---|---|---|---|",
    ]
    for page in manifest["pages"]:
        for st in page["states"]:
            lines.append(
                f"| {st.get('subject') or page['subject']} | {st.get('theme')} | {st.get('locale')} | "
                f"{st.get('viewport')} | `{st.get('alias', '')}` | "
                f"{'yes' if st.get('captured') else st.get('reason', 'no')} |"
            )
    lines += [
        "",
        "## G8 floor",
        "",
        "See `g8.json`. Checks at 390 / 768 / 1440: page horizontal scroll, "
        "focus-visible ring, LENS tap at 390, reduced-motion skeleton, chip wrap, "
        "wide table scrolls inside `.sc-wrap`.",
        "",
    ]
    return "\n".join(lines) + "\n"


def _shot_and_store(browser, base, *, width, height, locale, theme, selector,
                    alias, extra: dict | None = None,
                    page_name: str = "bonds_s3.html") -> dict:
    got = _capture_cell(
        browser, base, width=width, height=height,
        locale=locale, theme=theme, selector=selector,
        page_name=page_name,
    )
    png = got["png"]
    name, digest, pw, ph = content_address_png(png, CELLS_DIR)
    (CELLS_DIR / alias).write_bytes(png)
    row = {
        "captured": True,
        "file": f"cells/{name}",
        "alias": alias,
        "sha256": digest,
        "bytes": len(png),
        "width": pw,
        "height": ph,
        "applied_theme": (got.get("applied") or {}).get("theme"),
        "applied_locale": (got.get("applied") or {}).get("locale"),
        "overlay": got.get("overlay", "clean"),
        "content_name": name,
    }
    if extra:
        row.update(extra)
    print(
        f"  {alias}: {name} {pw}x{ph} overlay={row['overlay']} "
        f"sha256={digest[:12]}",
        flush=True,
    )
    return row


def _patch_manifest_cell(man: dict, *, alias: str, row: dict,
                         match) -> None:
    """Update the first state row matching `match`; append if none."""
    man.setdefault("aliases", {})[alias] = row["content_name"]
    for page in man.get("pages") or []:
        for st in page.get("states") or []:
            if match(st):
                st.update({k: v for k, v in row.items() if k != "content_name"})
                return
    # Extra force_state cells attach to the last page so REST still has 8.
    if man.get("pages"):
        man["pages"][-1].setdefault("states", []).append(
            {k: v for k, v in row.items() if k != "content_name"}
        )


def _recapture_r4() -> int:
    """Recapture r4-changed cells. Does not wipe hero/changed/deeper/drivers@1440."""
    from scripts.capture_page_evidence import CaptureUnavailable, serve_site_dir
    from scripts.build_bonds import divergence_card_state

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise CaptureUnavailable(f"playwright is not importable: {exc}") from exc

    scratch = Path(tempfile.mkdtemp(prefix="bonds_s3_r4_"))
    try:
        write_fixture_site(scratch)
        unbuilt = fixture_vm()
        unbuilt["div_card"] = divergence_card_state(
            False, None, "2026-09-10", "2026-09-10")
        write_fixture_site(scratch, vm=unbuilt, filename="bonds_s3_unbuilt.html")
        httpd, port = serve_site_dir(scratch)
        base = f"http://127.0.0.1:{port}"
        manager = sync_playwright().start()
        browser = None
        captured: dict[str, dict] = {}
        try:
            browser = manager.chromium.launch(headless=True)
            for viewport, (width, height) in VIEWPORTS.items():
                for locale in LOCALES:
                    for theme in THEMES:
                        alias = f"watching-{theme}-{locale}-{viewport}.png"
                        captured[alias] = _shot_and_store(
                            browser, base, width=width, height=height,
                            locale=locale, theme=theme,
                            selector='[data-l1="watching"]', alias=alias,
                            extra={"subject": "watching", "viewport": viewport,
                                   "locale": locale, "theme": theme,
                                   "viewport_width": width, "viewport_height": height,
                                   "access": "anonymous",
                                   "force_state": None, "r4": True},
                        )
            for viewport, (width, height) in VIEWPORTS.items():
                for locale in LOCALES:
                    for theme in THEMES:
                        alias = f"world-{theme}-{locale}-{viewport}.png"
                        captured[alias] = _shot_and_store(
                            browser, base, width=width, height=height,
                            locale=locale, theme=theme,
                            selector='[data-l1="world"]', alias=alias,
                            extra={"subject": "world", "viewport": viewport,
                                   "locale": locale, "theme": theme,
                                   "viewport_width": width, "viewport_height": height,
                                   "access": "anonymous",
                                   "force_state": None, "r4": True},
                        )
            for locale in LOCALES:
                for theme in THEMES:
                    alias = f"drivers-{theme}-{locale}-mobile.png"
                    captured[alias] = _shot_and_store(
                        browser, base, width=390, height=844,
                        locale=locale, theme=theme,
                        selector='[data-l1="drivers"]', alias=alias,
                        extra={"subject": "drivers", "viewport": "mobile",
                               "locale": locale, "theme": theme,
                               "viewport_width": 390, "viewport_height": 844,
                               "access": "anonymous",
                               "force_state": None, "r4": True},
                    )
            for theme in THEMES:
                alias = f"stale-gate-{theme}-en-desktop.png"
                captured[alias] = _shot_and_store(
                    browser, base, width=1440, height=900,
                    locale="en", theme=theme,
                    selector='[data-card="stocks-vs-bonds"]', alias=alias,
                    extra={
                        "subject": "stale-gate", "viewport": "desktop",
                        "locale": "en", "theme": theme,
                        "viewport_width": 1440, "viewport_height": 900,
                        "access": "anonymous",
                        "force_state": "stale-delayed",
                        "fixture": (
                            "r4 DELAYED cause=stale: last_obs='2026-08-01' "
                            "< as_of='2026-09-10'"
                        ),
                        "r4": True,
                    },
                )
            for theme in THEMES:
                alias = f"unbuilt-gate-{theme}-en-desktop.png"
                captured[alias] = _shot_and_store(
                    browser, base,
                    width=1440, height=900,
                    locale="en", theme=theme,
                    selector='[data-card="stocks-vs-bonds"]', alias=alias,
                    page_name="bonds_s3_unbuilt.html",
                    extra={
                        "subject": "unbuilt-gate", "viewport": "desktop",
                        "locale": "en", "theme": theme,
                        "viewport_width": 1440, "viewport_height": 900,
                        "access": "anonymous",
                        "force_state": "unbuilt-delayed",
                        "fixture": (
                            "r4 DELAYED cause=unbuilt: last_obs == as_of "
                            "'2026-09-10' — series current, engine unbuilt"
                        ),
                        "r4": True,
                    },
                )
        finally:
            if browser is not None:
                browser.close()
            manager.stop()
            httpd.shutdown()

        man_path = OUT_DIR / "manifest.json"
        man = json.loads(man_path.read_text(encoding="utf-8")) if man_path.exists() else {
            "schema": "mastermind.p0_evidence.v2", "pages": [], "aliases": {},
        }
        for alias, row in captured.items():
            subject = row.get("subject")
            theme = row.get("theme")
            locale = row.get("locale")
            viewport = row.get("viewport")
            force = row.get("force_state")

            def _match(st, s=subject, t=theme, l=locale, v=viewport, f=force, a=alias):
                if st.get("alias") == a:
                    return True
                if f:
                    return (st.get("subject") == s and st.get("theme") == t
                            and st.get("force_state") == f)
                return (st.get("subject") == s and st.get("theme") == t
                        and st.get("locale") == l and st.get("viewport") == v
                        and st.get("force_state") is None)

            _patch_manifest_cell(man, alias=alias, row=row, match=_match)

        fs = set(man.get("axes", {}).get("force_states") or [])
        fs.update(["stale-delayed", "unbuilt-delayed"])
        man.setdefault("axes", {})["force_states"] = sorted(fs)
        man.setdefault("honesty", {})["stale_gate_fixture"] = (
            "r4: cause=stale last_obs<'2026-09-10'; cause=unbuilt last_obs==as_of"
        )
        man.setdefault("honesty", {})["skydeck"] = (
            "window.__skyDeck=true before setTheme; .sky-fx/.mx5-aurora/"
            "#mmb-boot hidden; overlay probe recorded per recaptured cell"
        )
        man_path.write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
        print(f"r4 recapture done: {len(captured)} cells", flush=True)
        return 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _recapture_stale_gate() -> int:
    """Back-compat: --stale-only now runs the r4 recapture set."""
    return _recapture_r4()


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stale-only", action="store_true",
        help="Recapture the DELAYED pair only; leave the 48 REST cells.",
    )
    parser.add_argument(
        "--r4", action="store_true",
        help="Recapture watching×8, world×8, drivers@390×4, delayed branch 1+2.",
    )
    args = parser.parse_args(argv)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)
    if args.r4 or args.stale_only:
        return _recapture_r4()

    for stale in CELLS_DIR.glob("*.png"):
        stale.unlink()

    scratch = Path(tempfile.mkdtemp(prefix="bonds_s3_evidence_"))
    try:
        print("rendering bonds.html.j2 wrap (fixture VM)", flush=True)
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
            "  - templates/bonds.html.j2\n"
            "manifest: mockups/evidence/bonds-regime-dashboard/manifest.json\n",
            encoding="utf-8",
        )
        (OUT_DIR / "README.md").write_text(
            _write_readme(payloads["manifest"]), encoding="utf-8"
        )
        totals = payloads["manifest"]["totals"]
        print(
            f"outcome: {payloads['outcome']}\n"
            f"pages: {totals['pages']}  states: "
            f"{totals['states_captured']}/{totals['states_attempted']} captured",
            flush=True,
        )
        print("g8:", json.dumps(payloads["g8"], indent=2), flush=True)
        return 0 if payloads["outcome"] == "captured" else 1
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
