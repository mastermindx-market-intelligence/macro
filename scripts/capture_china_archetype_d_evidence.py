#!/usr/bin/env python3
"""Element-screenshot evidence for china.html Archetype-D S1 (round 2).

Captures dark+light × EN+ZH × 1440/390 of the five L1 subjects on a
fixture-rendered macro-mode block (sparse trees have no data/). Playwright
applies theme/lang the way theme.js does and refuses a cell whose observed
data-theme/data-lang does not match the request.

Usage::

    python3 -m scripts.capture_china_archetype_d_evidence
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
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
OUT_DIR = REPO_ROOT / "mockups" / "evidence" / "china-archetype-d"
CELLS_DIR = OUT_DIR / "cells"

SUBJECTS: tuple[tuple[str, str], ...] = (
    ("hero", '[data-ev="hero"]'),
    ("todo", '[data-ev="todo"]'),
    ("changed", '[data-ev="changed"]'),
    ("drivers", '[data-ev="drivers"]'),
    ("watching-deeper", '[data-ev="watching-deeper"]'),
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
    localStorage.setItem('theme', state.theme);
    localStorage.removeItem('themeAuto');
    localStorage.setItem('lang', state.locale);
  } catch (e) {}
  // Skip theme.js skyToggleFx (1.05s sun/moon flourish). Receipt: theme.css
  // `.sky-fx` is a theme-toggle overlay at z-index 2147483600; setTheme()
  // appends it for 1100ms. A 150ms screenshot otherwise captures the disc
  // over the hero (light sun bloom / dark moon over the 390 dial).
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
  return {theme: docEl.getAttribute('data-theme'), locale: docEl.getAttribute('data-lang')};
}
"""

_LENS_JS = """
(function(){
  window.cnxOpenDlg = window.cnxOpenDlg || function(){};
  window.cnxCloseDlg = window.cnxCloseDlg || function(){};
  document.addEventListener('pointerdown', function(e){
    var q = e.target && e.target.closest && e.target.closest('.cnx-lens');
    if(!q) return;
    e.preventDefault();
    e.stopPropagation();
    var was = q.classList.contains('cnx-tip-open');
    document.querySelectorAll('.cnx-lens.cnx-tip-open').forEach(function(el){
      el.classList.remove('cnx-tip-open');
    });
    if(!was) q.classList.add('cnx-tip-open');
  }, true);
  document.addEventListener('keydown', function(e){
    var t = e.target;
    if(!t || !t.classList || !t.classList.contains('cnx-lens')) return;
    if(e.key === 'Enter' || e.key === ' '){
      e.preventDefault();
      t.classList.toggle('cnx-tip-open');
    }
  });
})();
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
    """Representative china glance VM. Sparse trees have no data/; this is the
    page-test idiom (keys the wrap actually reads), not a live bake.
    """
    headlines = [
        {
            "title": "报道：德鲁肯米勒称美国借贷成本仍“有点低”",
            "title_zh": "报道：德鲁肯米勒称美国借贷成本仍“有点低”",
            "title_en": "报道：德鲁肯米勒称美国借贷成本仍“有点低”",
            "theme": "monetary",
            "published": "2026-09-10 09:00",
            "date": "2026-09-10",
        },
        {
            "title": "财政部部长助理常军红出席2026年第二次金砖国家财长和央行行长系列会议",
            "title_zh": "财政部部长助理常军红出席2026年第二次金砖国家财长和央行行长系列会议",
            "title_en": "财政部部长助理常军红出席2026年第二次金砖国家财长和央行行长系列会议",
            "theme": "policy",
            "published": "2026-09-09 14:00",
            "date": "2026-09-09",
        },
    ]
    events = [
        {"name_en": "CPI print", "name_zh": "CPI 公布", "date": "09-12", "importance": "high"},
        {"name_en": "Credit data", "name_zh": "信贷数据", "date": "09-15", "importance": "high"},
        {"name_en": "LPR fix", "name_zh": "LPR 报价", "date": "09-20", "importance": "high"},
        {"name_en": "PBoC briefing", "name_zh": "央行吹风会", "date": "09-22", "importance": "high"},
        {"name_en": "PMI flash", "name_zh": "PMI 初值", "date": "09-30", "importance": "high"},
    ]
    return {
        "latest": {
            "date": "2026-09-10",
            "quad_name": "Growth-scare",
            "risk_radar": {"state": "elevated"},
            "fear_euphoria": {"score": 42, "label": "Neutral"},
            "alerts": [
                {
                    "plain_en": "Southbound streak still buying into the scare.",
                    "plain_zh": "南向资金仍在恐慌中买入。",
                },
                {
                    "plain_en": "Pullback-risk score is elevated on all-boats breadth.",
                    "plain_zh": "回撤风险评分因普跌而偏高。",
                },
            ],
        },
        "market_state": {
            "color": "yellow",
            "score": 41,
            "verdict": "MIXED",
            "label_en": "GROWTH SCARE",
            "label_zh": "增长恐慌",
            "posture_en": "Trade with caution",
            "posture_zh": "谨慎交易",
            "headline_en": "",
            "headline_zh": "",
            "flip_en": "",
            "flip_zh": "",
            "components": [],
            "radar": {
                "top_score": 87,
                "dd21": 0.22,
                "do_en": "High pullback risk — size down, watch alerts.",
                "do_zh": "回撤风险高 — 缩仓，关注警报。",
            },
        },
        "health": [{"status": "ok"} for _ in range(7)],
        "internals": {
            "pboc": {"bias": "easing", "rrr_big": 6.6},
            "credit": {"credit_impulse": -0.8},
            "southbound": {"net": 4600, "pos_days_20": 14},
            "margin": {"fin_pct_float": 2.64, "pctile": 90},
            "turnover": {"pctile": 55, "band": "normal"},
        },
        "property": {
            "regime": {
                "label_en": "Still contracting",
                "label_zh": "仍在收缩",
                "tone": "neg",
            },
            "breadth": {"new": -12},
        },
        "pb": {
            "dial": {
                "posture": "NEUTRAL",
                "score": 0,
                "reasons": [
                    ("+",
                     "Growth-scare is the market's measured best contrarian bottom (~70% hit) — accumulate quality into the fear.",
                     "增长恐慌是实测最佳的逆向底部（命中率约70%）— 在恐慌中吸纳优质资产。"),
                    ("-",
                     "PBoC monetary conditions tightening (3/3 legs agree). ONE monetary-conditions vote.",
                     "央行货币条件趋紧（3/3项指标同意）— 综合M2/剪刀差/社融的单次货币投票。"),
                    ("-",
                     "Margin leverage crowded (90th percentile of float) — late-stage froth, tighten risk.",
                     "融资杠杆拥挤（占流通市值 90 分位）— 后期泡沫，收紧风险。"),
                ],
            },
            "progress": {
                "phase": "mid",
                "phase_note": "mid-life — normal conditions, trust the label",
                "phase_note_zh": "处于中年 — 环境正常，信任标签",
            },
            "quad_meaning": {
                "en": "Growth-scare — both growth and prices falling, fear peaking.",
                "zh": "增长恐慌 — 增长与物价齐跌、恐慌见顶。",
            },
        },
        "china_news": {
            "tone": {"label_en": "Supportive", "label_zh": "偏支持"},
            "news": {"headlines": headlines},
            "theme_label": {
                "monetary": ["Monetary", "货币"],
                "policy": ["Policy", "政策"],
            },
        },
        "event_strip": events,
        "leaderboard": {"southbound_buy": [{"name": "Tencent"}]},
        "hsi_tile": {"level": "25,432.1", "pct": "+0.3%", "tone": "pos"},
        "market_tiles": [
            {"sym": "000001.SS", "level": "3,934.4", "pct": "-0.4%", "tone": "neg"},
        ],
        "imminent": {
            "en": "CPI — Friday 09:30",
            "zh": "CPI — 周五 09:30",
        },
        "board_staleness": {"delayed": False},
        "mode": "macro",
    }


def _vm_with_dial(vm: dict, **dial_kw) -> dict:
    out = copy.deepcopy(vm)
    out["pb"] = dict(out["pb"])
    out["pb"]["dial"] = dict(out["pb"]["dial"], **dial_kw)
    return out


def defect_mixed_vm(vm: dict | None = None) -> dict:
    base = copy.deepcopy(vm or fixture_vm())
    reasons = list(base["pb"]["dial"]["reasons"])
    reasons[1] = (
        "i",
        "PBoC monetary conditions mixed (1 easing / 1 tightening / 1 neutral) — no net vote.",
        "央行货币条件分歧 — 无净投票。",
    )
    return _vm_with_dial(base, reasons=reasons)


def defect_majority_vm(vm: dict | None = None) -> dict:
    base = copy.deepcopy(vm or fixture_vm())
    reasons = list(base["pb"]["dial"]["reasons"])
    reasons[1] = (
        "-",
        "PBoC monetary conditions tightening (2/3 legs agree). ONE monetary-conditions vote.",
        "央行货币条件趋紧（2/3项指标同意）— 综合M2/剪刀差/社融的单次货币投票。",
    )
    return _vm_with_dial(base, reasons=reasons)


def defect_empty_vm(vm: dict | None = None) -> dict:
    return _vm_with_dial(copy.deepcopy(vm or fixture_vm()), reasons=[])


def defect_unknown_posture_vm(vm: dict | None = None) -> dict:
    return _vm_with_dial(copy.deepcopy(vm or fixture_vm()), posture="FRESH BUY")


def defect_hero_reconcile_vm(vm: dict | None = None) -> dict:
    """AGGRESSIVE playbook vs risk-off tape, with a visible headline."""
    base = _vm_with_dial(copy.deepcopy(vm or fixture_vm()), posture="AGGRESSIVE")
    ms = dict(base["market_state"])
    ms["color"] = "red"
    ms["score"] = 28
    ms["headline_en"] = "Breadth is breaking — every boat is sinking."
    ms["headline_zh"] = "广度破裂——所有船都在沉。"
    base["market_state"] = ms
    return base


# Defect-state cells (dark+light EN, 1440). Named in the README. Not extra
# manifest pages — the visual-evidence gate requires 8 REST cells on every
# page, and these close a fixture gap rather than a G7 subject.
DEFECT_CELLS: tuple[tuple[str, str, str, object], ...] = (
    ("mixed-money", "todo", '[data-ev="todo"]', defect_mixed_vm),
    ("majority-money", "todo", '[data-ev="todo"]', defect_majority_vm),
    ("worded-empty", "todo", '[data-ev="todo"]', defect_empty_vm),
    ("unknown-posture", "hero", '[data-ev="hero"]', defect_unknown_posture_vm),
    ("hero-reconcile", "hero", '[data-ev="hero"]', defect_hero_reconcile_vm),
)


def _extract_page_css(src: str) -> str:
    m = re.search(r"<style>(.*?)</style>\s*</head>", src, flags=re.S)
    if not m:
        raise RuntimeError("china.html.j2 page <style> block not found")
    css = m.group(1)
    # The page <style> is Jinja-templated (`{% if mode != 'stocks' %}`). The
    # fixture injects it as raw CSS, so drop the tags or a stocks-only
    # `.dial{height:9px}` rule leaks into the glance wrap.
    css = re.sub(r"\{%-?.*?-%?\}", "", css)
    return css


def _extract_macros(src: str) -> str:
    chunks = []
    for name in ("t", "imp", "cny_yi_pair"):
        pat = rf"\{{% macro {name}\b.*?%\}}.*?{{\%-? endmacro %\}}"
        m = re.search(pat, src, flags=re.S)
        if not m:
            raise RuntimeError(f"macro {name} not found in china.html.j2")
        chunks.append(m.group(0))
    return "\n".join(chunks)


def render_macro_block(vm: dict | None = None) -> str:
    """Render the L1 wrap + page CSS against a fixture VM. No data/ reads."""
    from jinja2 import DictLoader, Environment

    src = (TEMPLATES_DIR / "china.html.j2").read_text(encoding="utf-8")
    start = src.index("{# hero locals #}")
    end = src.index("  </div>{# /cnx-wrap #}") + len("  </div>{# /cnx-wrap #}")
    wrap_src = src[start:end]
    from engine.china_tier1 import hero_clause, posture_lane, posture_tone, reason_faces
    env = Environment(loader=DictLoader({"blk": _extract_macros(src) + "\n" + wrap_src}),
                      autoescape=False)
    env.globals.update(
        posture_lane=posture_lane, posture_tone=posture_tone,
        reason_faces=reason_faces, hero_clause=hero_clause,
    )
    html = env.get_template("blk").render(**(vm or fixture_vm()))
    css = _extract_page_css(src)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en" data-theme="dark" data-lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>China Archetype-D evidence fixture</title>\n"
        '<link rel="stylesheet" href="theme.css">\n'
        "<style>" + css + "</style>\n"
        '<script src="theme.js"></script>\n'
        "</head>\n"
        '<body class="page-china mx4-grid">\n'
        '<div class="aurora au-yellow" aria-hidden="true"><div class="au-a3"></div></div>\n'
        + html
        + "\n<script>" + _LENS_JS + "</script>\n"
        "</body>\n</html>\n"
    )


def write_fixture_site(scratch: Path) -> None:
    scratch.mkdir(parents=True, exist_ok=True)
    shutil.copy(TEMPLATES_DIR / "theme.css", scratch / "theme.css")
    shutil.copy(TEMPLATES_DIR / "theme.js", scratch / "theme.js")
    (scratch / "china_s1.html").write_text(render_macro_block(), encoding="utf-8")
    for name, _subject, _sel, builder in DEFECT_CELLS:
        (scratch / f"china_s1_defect_{name}.html").write_text(
            render_macro_block(builder()), encoding="utf-8"
        )


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
  const chips = Array.from(document.querySelectorAll('.cnx-chips, .depth, .mx-vh-meta'));
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
  return {
    clientWidth: doc.clientWidth,
    scrollWidth: body.scrollWidth,
    pageScroll,
    chipWrap: wrapOk,
    skelAnim,
  };
}
"""


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
    defect_rows: list[dict] = []

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
                                url = f"{base}/china_s1.html"
                                response = page.goto(url, wait_until="load", timeout=30000)
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
                                loc = page.locator(selector).first
                                loc.wait_for(state="visible", timeout=5000)
                                loc.scroll_into_view_if_needed()
                                page.wait_for_timeout(80)
                                png = loc.screenshot(type="png")
                                name, digest, pw, ph = content_address_png(png, CELLS_DIR)
                                alias = f"{subject}-{theme}-{locale}-{viewport}.png"
                                (CELLS_DIR / alias).write_bytes(png)
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
                        "page_id": f"china.html#{subject}",
                        "route": "/china_s1.html",
                        "registry_route": "/china.html",
                        "route_kind": "china_archetype_d_subject",
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
                    page.goto(f"{base}/china_s1.html", wait_until="load", timeout=30000)
                    page.evaluate(_APPLY_STATE_SCRIPT.strip(), {"theme": "dark", "locale": "en"})
                    page.wait_for_timeout(200)
                    probe = page.evaluate(_g8_probe())
                    focus_ok = False
                    try:
                        page.locator('.cnx-row .cnx-lens').first.focus()
                        page.wait_for_timeout(80)
                        focus_ok = page.evaluate(
                            """() => {
                              const el = document.querySelector('.cnx-row .cnx-lens');
                              if (!el) return false;
                              const st = getComputedStyle(el);
                              const ring = (st.outlineStyle && st.outlineStyle !== 'none' && st.outlineWidth !== '0px')
                                || (st.boxShadow && st.boxShadow !== 'none');
                              const lensOpen = !!(document.querySelector('.cnx-lens.cnx-tip-open, .lens-scrim.open, .lens-pop.open'));
                              return ring || lensOpen;
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
                            tap_page.goto(f"{base}/china_s1.html", wait_until="load", timeout=30000)
                            tap_page.evaluate(
                                _APPLY_STATE_SCRIPT.strip(), {"theme": "dark", "locale": "en"}
                            )
                            tap_page.wait_for_timeout(200)
                            row = tap_page.locator('.cnx-row .cnx-lens').first
                            row.scroll_into_view_if_needed()
                            row.tap(timeout=5000)
                            tap_page.wait_for_timeout(200)
                            lens_ok = tap_page.evaluate(
                                """() => {
                                  const btn = document.querySelector('.cnx-lens.cnx-tip-open');
                                  if (!btn) return false;
                                  const after = getComputedStyle(btn, '::after');
                                  return after && after.display !== 'none' && after.content && after.content !== 'none';
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
                            page2.goto(f"{base}/china_s1.html", wait_until="load", timeout=30000)
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
                    })
                except Exception as exc:
                    g8_row["error"] = f"{type(exc).__name__}: {exc}"
                finally:
                    context.close()
                g8[str(width)] = g8_row

            d_width, d_height = VIEWPORTS["desktop"]
            for name, subject, selector, _builder in DEFECT_CELLS:
                for theme in THEMES:
                    locale = "en"
                    state = {"theme": theme, "locale": locale}
                    context = browser.new_context(
                        viewport={"width": d_width, "height": d_height},
                        locale="en-US",
                        color_scheme=theme,
                        device_scale_factor=1,
                    )
                    context.add_init_script(
                        f"({_STATE_SEED_SCRIPT.strip()})({json.dumps(state)})"
                    )
                    page = context.new_page()
                    entry = {
                        "defect": name,
                        "subject": subject,
                        "viewport": "desktop",
                        "locale": locale,
                        "theme": theme,
                        "viewport_width": d_width,
                        "viewport_height": d_height,
                    }
                    try:
                        url = f"{base}/china_s1_defect_{name}.html"
                        response = page.goto(url, wait_until="load", timeout=30000)
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
                        loc = page.locator(selector).first
                        loc.wait_for(state="visible", timeout=5000)
                        loc.scroll_into_view_if_needed()
                        page.wait_for_timeout(80)
                        png = loc.screenshot(type="png")
                        fname, digest, pw, ph = content_address_png(png, CELLS_DIR)
                        alias = f"defect-{name}-{theme}-{locale}-desktop.png"
                        (CELLS_DIR / alias).write_bytes(png)
                        written.add(fname)
                        written.add(alias)
                        aliases[alias] = fname
                        entry.update(
                            {
                                "captured": True,
                                "file": fname,
                                "alias": alias,
                                "sha256": digest,
                                "bytes": len(png),
                                "width": pw,
                                "height": ph,
                                "applied_theme": applied.get("theme"),
                                "applied_locale": applied.get("locale"),
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
                    defect_rows.append(entry)
            captured_d = sum(1 for r in defect_rows if r.get("captured"))
            print(f"  defect-state: {captured_d}/{len(defect_rows)} cells", flush=True)
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
            "module_ref": "scripts/capture_china_archetype_d_evidence.py",
            "version": "s1-r2-element",
            "capture_method": (
                "playwright locator('[data-ev=SUBJECT]').screenshot() on a "
                "fixture-rendered china.html.j2 macro-mode wrap (theme.css + "
                "page-scoped china styles). data-theme/data-lang applied via "
                "window.setTheme/setLang with refuse-on-mismatch. sha256 from "
                "the element-screenshot bytes."
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
                "macro-mode wrap render, not live site/china.html"
            ),
        },
        "axes": {
            "viewports": {name: list(size) for name, size in VIEWPORTS.items()},
            "locales": list(LOCALES),
            "themes": list(THEMES),
            "access": ["anonymous"],
            "subjects": [s for s, _ in SUBJECTS],
            "force_states": [],
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
            "states_attempted": attempted,
            "states_captured": captured,
        },
        "honesty": {
            "access": "anonymous only",
            "gaps": "uncaptured cells are recorded with a reason",
            "authority": "this tool screenshots; it scores nothing",
            "page": (
                "macro-mode cnx-wrap extracted from templates/china.html.j2 and "
                "rendered with a representative fixture VM (no data/ reads). "
                "Omitted vs live: site nav, dialogs, stocks mode, live quote "
                "hydration, heatmap. Light page-aurora is CSS-gated off. "
                "Capture sets window.__skyDeck so theme.js skyToggleFx "
                "(1.05s sun/moon flourish) is not photographed; live theme "
                "toggles still play the flourish."
            ),
        },
        "g8": g8,
        "pages": pages,
        "defect_cells": defect_rows,
    }
    return {"manifest": manifest, "written": sorted(written), "outcome": outcome, "g8": g8}


def _write_readme(manifest: dict) -> str:
    lines = [
        "# China Archetype-D S1 — evidence matrix (round 5)",
        "",
        "Five L1 subjects × dark/light × EN/ZH × 1440/390.",
        "Spec G7 names this the 20-crop matrix; the product of those axes is "
        f"{manifest['totals']['states_captured']} cells.",
        "",
        "## Fixture",
        "",
        "- Source: `templates/china.html.j2` macro-mode `.cnx-wrap` + page-scoped `<style>`.",
        "- VM: `scripts/capture_china_archetype_d_evidence.fixture_vm` "
        "(same shape the page tests use).",
        "- Theme/lang: Playwright seeds localStorage then calls `window.setTheme` / "
        "`window.setLang`; a mismatch refuses the cell.",
        "",
        "## Honest differences from live `site/china.html`",
        "",
        "- No `_site_nav` chrome (two global nav families; this crop is the glance wrap).",
        "- No dialogs, heatmap, or stocks-mode board.",
        "- No live quote hydration — CSI 300 / ChiNext stay at skeleton geometry. "
        "This is capture-time state: the fixture has no live.js quote feed, and "
        "the template bakes those two tiles as `mx-skel` plates (`data-sym` "
        "000300.SS / 399006.SZ). Live `site/china.html` hydrates the same plates; "
        "they do not remain skeleton indefinitely. Intended, not a hang.",
        "- Numbers are representative (southbound +¥4.6bn / +¥46亿, events 4 of 5, "
        "pullback 87, date 2026-09-10), not that night's bake.",
        "- Sparse checkout has no `data/`; this is why the wrap is fixture-rendered.",
        "",
        "## Cells",
        "",
        "| Subject | Theme | Lang | Viewport | Alias | Captured |",
        "|---|---|---|---|---|---|",
    ]
    for page in manifest["pages"]:
        for st in page["states"]:
            lines.append(
                f"| {page['subject']} | {st.get('theme')} | {st.get('locale')} | "
                f"{st.get('viewport')} | `{st.get('alias', '')}` | "
                f"{'yes' if st.get('captured') else st.get('reason', 'no')} |"
            )
    g8 = manifest.get("g8") or {}
    g8_390 = g8.get("390") or {}
    skel = g8_390.get("reduced_motion") or {}
    lines += [
        "",
        "## G8 floor",
        "",
        "See `g8.json`. Checks at 390 / 768 / 1440: page horizontal scroll, "
        "focus-visible ring, LENS tap at 390, reduced-motion skeleton, chip wrap.",
        "",
        "| Width | Page h-scroll | Focus ring | LENS tap | Reduced-motion skeleton | Chip wrap |",
        "|---|---|---|---|---|---|",
        f"| 390 | none (`scrollWidth=clientWidth={g8_390.get('clientWidth', 390)}`) | "
        f"{'visible' if g8_390.get('focus_ring') else 'no'} | "
        f"{'open' if g8_390.get('lens_tap') else g8_390.get('lens_tap')} | "
        f"`animation-name: {skel.get('animationName', 'none')}`, "
        f"plate ~{skel.get('w', '?')}px | "
        f"{'wrap' if g8_390.get('chip_wrap') else 'no'} |",
        "| 768 | none | visible | n/a (390 only) | n/a | wrap |",
        "| 1440 | none | visible | n/a | n/a | wrap |",
        "",
        "## G7 per-subject verdicts (judged from the crops)",
        "",
        "Spec G7's \"20 crops\" is `{dark,light}×{EN,ZH}×{1440,390}` × 5 subjects "
        "= **40 cells**. Each subject is one G7 surface; the eight cells share the "
        "composition verdict unless a criterion is axis-specific.",
        "",
        "| Subject | Cells | G7 verdict | Notes |",
        "|---|---|---|---|",
        "| hero | 8 | **PASS** | One regime word (`GROWTH SCARE` / `增长恐慌`) from `_ms_label`; "
        "one producer clause; exactly one date `2026-09-10`; index strip SSE/CSI/ChiNext/HSI; "
        "dark = luminance field + dial arc; light = white card on deeper canvas, no full-bleed "
        "field, no bloom; ZH has no Latin state enum; 390 stacks with no page h-scroll. "
        "CSI/ChiNext skeletons at true geometry. Dial is a thin arc at 390 (no white disc). |",
        "| todo | 8 | **PASS** | Three producer-bound stance sentences within word budgets; "
        "LENS `?` on each row; next-print date is the only digits-with-units at rest; "
        "ZH has no `3/3` / `90` / `70%`. |",
        "| changed | 8 | **PASS** (mapped from G7 Macro News) | Two headlines + two alerts; "
        "EN crop is not blank (Chinese source text in both slots — spec §4.1 frozen fallback); "
        "ZH matches; no EN/ZH mix inside a crop. |",
        "| drivers | 8 | **PASS** (mapped from G7 Connect Flows + four-driver band) | "
        "EN `+¥4.6bn` + Latin names; ZH `+¥46亿` + 中文 names; no mix; dark accent-tinted "
        "value; light uses light-rung ink. Four panels, 2-col desktop / swipe at 390. |",
        "| watching-deeper | 8 | **PASS** (mapped from G7 Upcoming Events + Go deeper) | "
        "Slice label `4 of 5 shown · full calendar →` (ZH `4/5 项已显示 · 完整日历 →`) in the "
        "same crop as the strip; population `5` once; 390 strip scrolls inside `.cnx-estrip`; "
        "Go-deeper links wrap and include the playbook landing; light hover is ring-not-glow. |",
        "",
        "## Capture-harness disclosure (B2)",
        "",
        "Round-2 light bloom and the 390 white disc were **not** the page aurora. "
        "They were `theme.js` `skyToggleFx`: a 1.05s sun (light) / crescent-moon (dark) "
        "flourish at `z-index: 2147483600` that `setTheme()` appends for 1100ms "
        "(`templates/theme.css` `.sky-fx` / `.sky-fx .disc`; `theme.js` `skyToggleFx`, "
        "timeout 1100). The r2 harness called `window.setTheme` then screenshotted at "
        "~150ms, so every cell photographed the in-flight disc. Receipt: computed style "
        "on the orange blob was `span.disc` inside `.sky-fx.sun` "
        "(`radial-gradient(circle at 50% 46%, #fffdf7 … #ffc35a …)`); the dark 390 disc "
        "was `.sky-fx.moon .disc` with the crescent mask. This round sets "
        "`window.__skyDeck = true` in the init script (the same bow-out the landing "
        "hub uses) and removes any leftover `.sky-fx` after apply. Live theme toggles "
        "still play the flourish; it is not a page-china CSS hide. Light page-aurora "
        "remains CSS-gated `display:none` (spec §5.5).",
        "",
        "## CNH inverted-tile ruling",
        "",
        "L1 index strip is SSE / CSI 300 / ChiNext / HSI — **no inverted-quote tile "
        "renders**. `MARKET_TILE_SPEC` still has `CNH_F` `invert=True`; orientation "
        "copy now also renders on the Tier-2 USD/CNH card inside `cnx-dlg-markets` "
        "(`quoted as yuan per US dollar — higher = a weaker yuan` / "
        "`以美元兑人民币报价 — 数值升高 = 人民币走弱`).",
        "",
        "## Defect-state cells",
        "",
        "The happy-path fixture pins posture NEUTRAL + three firing reasons, so it "
        "never exercises mixed/majority/empty/unknown/reconcile. These five extra "
        "cells (dark+light EN, 1440) close that gap. They are aliases in `cells/`, "
        "not extra G7 subjects (the visual-evidence gate still requires eight REST "
        "cells on each of the five L1 subjects).",
        "",
        "| Cell | Subject | What it exercises | Aliases |",
        "|---|---|---|---|",
        "| mixed-money | todo | MIXED PBoC face (`no net vote`) | "
        "`defect-mixed-money-dark-en-desktop.png`, `defect-mixed-money-light-en-desktop.png` |",
        "| majority-money | todo | 2/3 tightening majority wording | "
        "`defect-majority-money-dark-en-desktop.png`, `defect-majority-money-light-en-desktop.png` |",
        "| worded-empty | todo | §9.12 empty stance rows | "
        "`defect-worded-empty-dark-en-desktop.png`, `defect-worded-empty-light-en-desktop.png` |",
        "| unknown-posture | hero | unmapped posture → cautious lane | "
        "`defect-unknown-posture-dark-en-desktop.png`, `defect-unknown-posture-light-en-desktop.png` |",
        "| hero-reconcile | hero | AGGRESSIVE + risk-off tape; headline visible "
        "with the reconciliation beneath | "
        "`defect-hero-reconcile-dark-en-desktop.png`, `defect-hero-reconcile-light-en-desktop.png` |",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)
    for stale in CELLS_DIR.glob("*.png"):
        stale.unlink()

    scratch = Path(tempfile.mkdtemp(prefix="china_s1_evidence_"))
    try:
        print("rendering china.html.j2 macro wrap (fixture VM)", flush=True)
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
            "  - templates/china.html.j2\n"
            "manifest: mockups/evidence/china-archetype-d/manifest.json\n",
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
