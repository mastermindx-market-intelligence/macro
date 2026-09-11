#!/usr/bin/env python3
"""flow_velocity W13 r3 — settled evidence matrix (S1 rig + SETTLE column).

Captures at the committed HEAD with porcelain empty. Fixture-rendered
(sparse trees have no site/ or data/). A cell that fails settle is REFUSED,
not captured.

Usage::

    python3 -m scripts.capture_flow_velocity_w13_r3_evidence
"""
from __future__ import annotations

import hashlib
import json
import shutil
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from jinja2 import Environment, FileSystemLoader

from engine import i18n
from engine.flow_observatory.contract import (
    QUADRANT_LABELS,
    STATUS_WORD,
    sigma_meaning,
)
from scripts.build_vector import C
from scripts.capture_page_evidence import CaptureUnavailable, _git_head_sha, serve_site_dir
from tests.test_flow_observatory_contract import _member, _theme, _v2

OUT_DIR = _ROOT / "research" / "flow_observatory" / "w13_r3_evidence"
CELLS_DIR = OUT_DIR / "cells"
R2_DIR = _ROOT / "research" / "flow_observatory" / "w13_r2_evidence"
SCRATCH = Path("/tmp/fv-w13-r3-capture")

_STATE_SEED = """
(state) => {
  try {
    localStorage.setItem('theme', state.theme);
    localStorage.removeItem('themeAuto');
    localStorage.setItem('lang', state.locale);
  } catch (e) {}
  window.__skyDeck = true;
  window.MMBrain = window.MMBrain || {capture: true};
}
"""

_APPLY_STATE = """
(state) => {
  const docEl = document.documentElement;
  if (typeof window.setTheme === 'function') { window.setTheme(state.theme); }
  else { docEl.setAttribute('data-theme', state.theme); }
  if (typeof window.setLang === 'function') { window.setLang(state.locale); }
  else {
    docEl.setAttribute('data-lang', state.locale);
    if (state.locale) docEl.lang = state.locale;
  }
  if (document.body && !document.body.classList.contains('page-flow-velocity')) {
    document.body.classList.add('page-flow-velocity');
  }
  docEl.classList.add('js');
  for (const cls of ['.sky-fx', '.aurora', '#mmb-root', '#mmb-boot', '.nav-totop']) {
    document.querySelectorAll(cls).forEach((n) => {
      n.style.setProperty('display', 'none', 'important');
      if (n.parentNode) n.parentNode.removeChild(n);
    });
  }
  document.querySelectorAll('.fv-reveal').forEach((el) => el.classList.add('is-in'));
  return {theme: docEl.getAttribute('data-theme'), locale: docEl.getAttribute('data-lang'),
          body: document.body ? document.body.className : ''};
}
"""

_OVERLAY_JS = """
(sel) => {
  const el = document.querySelector(sel) || document.querySelector('.wrap') || document.body;
  if (!el) return {ok: false, reason: 'missing-subject'};
  const r = el.getBoundingClientRect();
  const hits = [];
  for (const cls of ['.sky-fx', '.aurora', '#mmb-root', '#mmb-boot']) {
    document.querySelectorAll(cls).forEach((n) => {
      const b = n.getBoundingClientRect();
      const overlap = !(b.right < r.left || b.left > r.right || b.bottom < r.top || b.top > r.bottom);
      const st = getComputedStyle(n);
      if (overlap && st.display !== 'none' && st.visibility !== 'hidden' && Number(st.opacity) > 0.05) {
        hits.push(cls);
      }
    });
  }
  return {ok: hits.length === 0, hits};
}
"""

# Fonts ready, then force-finish running animations/transitions on the content
# root. Reduced-motion alone did not settle fvReveal (0.5s, both fill). A cell
# whose effective opacity is not 1 is REFUSED.
_SETTLE_JS = """
async (sel) => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  if (document.fonts && document.fonts.ready) {
    try { await document.fonts.ready; } catch (e) {}
  }
  document.querySelectorAll('.fv-reveal').forEach((el) => el.classList.add('is-in'));
  const root = document.querySelector(sel) || document.querySelector('.wrap') || document.body;
  if (!root) return {ok: false, reason: 'missing-root'};

  const runningOf = (el) => (el.getAnimations({subtree: true}) || []).filter(
    (a) => a.playState === 'running' || a.playState === 'pending');
  const finishTree = (el) => {
    runningOf(el).forEach((a) => {
      try { a.finish(); } catch (e) {
        try { a.cancel(); } catch (e2) {}
      }
    });
  };
  finishTree(document.documentElement);
  const t0 = performance.now();
  while (performance.now() - t0 < 2500) {
    const still = runningOf(document.documentElement);
    if (!still.length) break;
    still.forEach((a) => { try { a.finish(); } catch (e) { try { a.cancel(); } catch (e2) {} } });
    await sleep(16);
  }
  document.querySelectorAll('.lens-pop.open').forEach((p) => {
    p.style.opacity = '1';
    p.style.transform = 'none';
  });
  const leftover = runningOf(document.documentElement).length;

  const effectiveOpacity = (el) => {
    let o = 1, n = el;
    while (n && n.nodeType === 1) {
      const op = Number(getComputedStyle(n).opacity);
      if (!Number.isNaN(op)) o *= op;
      n = n.parentElement;
    }
    return o;
  };
  const parseColor = (str) => {
    if (!str || str === 'transparent') return null;
    const m = str.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([0-9.]+))?\\)/);
    if (!m) return null;
    const a = m[4] === undefined ? 1 : Number(m[4]);
    if (a === 0) return null;
    return [Number(m[1]), Number(m[2]), Number(m[3]), a];
  };
  const relLum = (rgb) => {
    const f = (c) => { c = c / 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(rgb[0]) + 0.7152 * f(rgb[1]) + 0.0722 * f(rgb[2]);
  };
  const contrastRatio = (fg, bg) => {
    const L1 = relLum(fg), L2 = relLum(bg);
    const hi = Math.max(L1, L2), lo = Math.min(L1, L2);
    return (hi + 0.05) / (lo + 0.05);
  };
  const effectiveBg = (el) => {
    let n = el;
    while (n && n.nodeType === 1) {
      const c = parseColor(getComputedStyle(n).backgroundColor);
      if (c && c[3] > 0.01) return c;
      n = n.parentElement;
    }
    return parseColor(getComputedStyle(document.body).backgroundColor) || [15, 18, 24, 1];
  };

  const row = root.querySelector('tr.sector-row, .mom-row, .fv-src, .fv-hero-eyebrow, h1') || root;
  const header = root.querySelector('thead th, h1, h2, .fv-hero-eyebrow h1, .mom-col-h, .s-name') || row;
  const rootOp = effectiveOpacity(root);
  const rowOp = effectiveOpacity(row);
  let headerContrast = null;
  let headerColor = null;
  if (header) {
    const fg = parseColor(getComputedStyle(header).color);
    const bg = effectiveBg(header);
    if (fg && bg) {
      headerContrast = Math.round(contrastRatio(fg, bg) * 100) / 100;
      headerColor = getComputedStyle(header).color;
    }
  }
  const ok = rootOp >= 0.995 && rowOp >= 0.995;
  return {
    ok, reason: ok ? 'settled' : (leftover ? 'running-anims' : 'opacity-not-1'),
    root_opacity: Math.round(rootOp * 1000) / 1000,
    row_opacity: Math.round(rowOp * 1000) / 1000,
    header_contrast: headerContrast,
    header_color: headerColor,
    running: leftover,
    fonts: (document.fonts && document.fonts.status) || 'unknown',
  };
}
"""

_HSCROLL_JS = """
() => {
  const de = document.documentElement;
  const body = document.body;
  const cw = de.clientWidth;
  const sw = Math.max(de.scrollWidth, body ? body.scrollWidth : 0);
  return {
    client_width: cw,
    scroll_width: sw,
    overflow: sw - cw,
    ok: sw <= cw + 1,
  };
}
"""


def _png_meta(png: bytes) -> tuple[str, str, int, int]:
    digest = hashlib.sha256(png).hexdigest()
    name = f"{digest[:16]}.png"
    if len(png) >= 24 and png[:8] == b"\x89PNG\r\n\x1a\n" and png[12:16] == b"IHDR":
        w, h = struct.unpack(">II", png[16:24])
    else:
        w, h = 0, 0
    return name, digest, int(w), int(h)


def _require_clean_head() -> str:
    """Refuse capture on a dirty tree. Manifest sha must be the commit that produced the pixels."""
    porcelain = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=_ROOT, text=True)
    if porcelain.strip():
        raise SystemExit("REFUSED: porcelain not empty — commit the rig first.\n" + porcelain)
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=_ROOT, text=True).strip()
    hand = _git_head_sha(_ROOT)
    hand_sha = hand.sha if hasattr(hand, "sha") else str(hand)
    if hand_sha and hand_sha != sha:
        raise SystemExit(f"REFUSED: git HEAD {sha} != hand reader {hand_sha}")
    return sha


def _paint_degraded_sources(v2: dict) -> None:
    """Force the four designed degraded chip treatments onto the trust strip.

    CSS keys off .fv-src--{ui_state}. Labels match _STATE_WORDS so the chips
    read as the designed states, not as current-wearing-a-class.
    """
    words = {
        "stale": ("stale — showing 2026-08-17", "已过期 · 显示2026-08-17数据"),
        "unavailable": ("unavailable", "不可用"),
        "behind": ("behind — showing 2026-09-01 data", "滞后 · 显示2026-09-01数据"),
        "historical": ("historical only — ended 2024-08-16", "仅历史 · 止于2024-08-16"),
        "current": ("current", "最新"),
    }
    order = ["current", "stale", "unavailable", "behind", "historical"]
    sources = list(v2.get("sources") or [])
    for src, ui in zip(sources, order):
        src["ui_state"] = ui
        en, zh = words[ui]
        src["state_word_en"] = en
        src["state_word_zh"] = zh


def _fixture_html() -> str:
    members = [_member(ticker="600104.SS", name="SAIC Motor")]
    nine = [
        _theme(0, vel=0.45, rate_4wk=-0.9, rate_rel=0.45, accel=0.01,
               name="Close pace", name_zh="接近常态", members=members),
        _theme(1, vel=3.40, rate_4wk=1.4, rate_rel=3.40, accel=0.04,
               name="Rare high", name_zh="罕见高位"),
        _theme(2, vel=None, rate_4wk=None, rate_rel=None, accel=None,
               name="Thin cover", name_zh="覆盖不足",
               state="insufficient coverage", state_zh="覆盖不足",
               n_covered=1, n_members=20, coverage_pct=5.0,
               coverage_state="insufficient_coverage"),
    ]
    for i in range(3, 9):
        nine.append(_theme(i, vel=1.0 + (i - 3) * 0.2, rate_4wk=-0.9,
                           rate_rel=0.4 + i * 0.1))
    aggregate = [
        {"key": "southbound", "label": "Southbound — mainland money into HK",
         "label_zh": "南向 · 内地资金入港", "live": True, "as_of": "2026-09-01",
         "spark": None, "flow_1m_b": 23.6, "pos_days_20": 12,
         "vel": {"1w": 0.45, "1m": 3.40, "3m": 1.2}, "accel": -0.05,
         "vel_primary": 3.40, "primary": "1m",
         "state": "above norm, rising", "state_zh": "高于常态·升温"},
        {"key": "northbound", "label": "Northbound — foreign money into A-shares",
         "label_zh": "北向 · 外资入A股", "live": False, "as_of": None,
         "spark": None, "frozen_since": "2024-08-16",
         "note": "Aggregate northbound net disclosure ended 2024-08-16 (Stock Connect "
                 "home-market rule) — historical only, no live velocity.",
         "note_zh": "北向资金净额披露于2024-08-16停止（互联互通本地市场规则）——仅历史，无实时流速。"},
    ]
    momentum = {
        "accel_in": [{"ticker": "000001.SZ", "name": "Accel Co", "vel": 1.6}],
        "cooling": [{"ticker": "000002.SZ", "name": "Cool Co", "vel": 1.7}],
        "easing": [{"ticker": "000003.SZ", "name": "Ease Co", "vel": -1.5, "rate_4wk": -2.0}],
        "buying_slowing": [{"ticker": "000004.SZ", "name": "Buyer Fade",
                            "vel": -1.5, "rate_4wk": 7.1}],
        "n_accel_in": 1, "n_cooling": 1, "n_easing": 1, "n_buying_slowing": 1,
    }
    v2 = _v2(
        ashare_sectors={
            "cadence": "daily", "as_of": "2026-09-01", "n": 9, "n_unscored": 0,
            "primary": "4wk", "note": "n", "note_zh": "n", "rows": nine,
        },
        aggregate=aggregate,
        momentum=momentum,
    )
    _paint_degraded_sources(v2)
    rows = v2.get("ashare_sectors", {}).get("rows") or []
    if len(rows) > 2:
        rows[2]["coverage_state"] = "insufficient_coverage"
        rows[2]["n_covered"] = 1
        rows[2]["n_members"] = 20
        rows[2]["coverage_pct"] = 5.0
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=True)
    env.globals.update(td=i18n.td, tr=i18n.tr, quadrant_labels=QUADRANT_LABELS,
                       status_word=STATUS_WORD, sigma_meaning=sigma_meaning)
    return env.get_template("flow_velocity.html.j2").render(C=C, snap=v2, built="w13-r3")


def _prepare_scratch(scratch: Path) -> None:
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "flow_velocity.html").write_text(_fixture_html(), encoding="utf-8")
    for name in ("theme.js", "theme.css", "product-nav-icons.css",
                 "navigation-refresh.css"):
        src = _ROOT / "templates" / name
        if src.exists():
            shutil.copy2(src, scratch / name)
    fonts_src = _ROOT / "templates" / "fonts"
    if fonts_src.is_dir():
        shutil.copytree(fonts_src, scratch / "fonts", dirs_exist_ok=True)


def _cell_matrix() -> list[dict]:
    cells: list[dict] = []
    for theme in ("dark", "light"):
        for locale in ("en", "zh"):
            cells.append({
                "id": f"baseline-{theme}-{locale}-desktop",
                "family": "baseline", "theme": theme, "locale": locale,
                "w": 1440, "h": 900, "kind": "fullpage",
                "sel": ".wrap", "action": None,
            })
            cells.append({
                "id": f"baseline-{theme}-{locale}-mobile",
                "family": "baseline", "theme": theme, "locale": locale,
                "w": 390, "h": 844, "kind": "fullpage",
                "sel": ".wrap", "action": None, "hscroll": True,
            })
    # (a) banded σ tips OPEN — |σ|<1 and |σ|≥3, row host + channel host.
    # Copy difference → EN+ZH; tip chrome is visual → dark+light for the row host.
    for theme in ("dark", "light"):
        for locale in ("en", "zh"):
            cells.append({
                "id": f"sigma-row-lo-{theme}-{locale}",
                "family": "sigma-row", "theme": theme, "locale": locale,
                "w": 1440, "h": 900, "kind": "union-tip",
                "sel": 'tr.sector-row[data-sector="cn_t00"] .vbar-cell',
                "tip_sel": 'tr.sector-row[data-sector="cn_t00"] .vbar-cell .lens-q',
                "action": "tip",
            })
            cells.append({
                "id": f"sigma-row-hi-{theme}-{locale}",
                "family": "sigma-row", "theme": theme, "locale": locale,
                "w": 1440, "h": 900, "kind": "union-tip",
                "sel": 'tr.sector-row[data-sector="cn_t01"] .vbar-cell',
                "tip_sel": 'tr.sector-row[data-sector="cn_t01"] .vbar-cell .lens-q',
                "action": "tip",
            })
    for locale in ("en", "zh"):
        cells.append({
            "id": f"sigma-chan-lo-dark-{locale}",
            "family": "sigma-chan", "theme": "dark", "locale": locale,
            "w": 1440, "h": 900, "kind": "union-tip",
            "sel": "#channels .vchip",
            "tip_sel": "#channels .vchip:nth-of-type(1) .lens-q",
            "action": "tip",
        })
        cells.append({
            "id": f"sigma-chan-hi-dark-{locale}",
            "family": "sigma-chan", "theme": "dark", "locale": locale,
            "w": 1440, "h": 900, "kind": "union-tip",
            "sel": "#channels .vchip:nth-of-type(2)",
            "tip_sel": "#channels .vchip:nth-of-type(2) .lens-q",
            "action": "tip",
        })
    # (b) four-bucket counters + buying-slowing row (copy EN+ZH, visual dark+light)
    for theme in ("dark", "light"):
        for locale in ("en", "zh"):
            cells.append({
                "id": f"counters-{theme}-{locale}",
                "family": "counters", "theme": theme, "locale": locale,
                "w": 1440, "h": 900, "kind": "element",
                "sel": "#momentum", "action": "open-momentum",
            })
    # (c) rank empty states at rest, tip open (copy)
    for locale in ("en", "zh"):
        cells.append({
            "id": f"rank-firstday-dark-{locale}",
            "family": "rank", "theme": "dark", "locale": locale,
            "w": 1440, "h": 900, "kind": "union-tip",
            "sel": 'tr.sector-row[data-sector="cn_t00"] td.tnum:nth-last-child(2)',
            "tip_sel": 'tr.sector-row[data-sector="cn_t00"] td.tnum .lens-q',
            "action": "tip",
        })
        cells.append({
            "id": f"rank-notranked-dark-{locale}",
            "family": "rank", "theme": "dark", "locale": locale,
            "w": 1440, "h": 900, "kind": "union-tip",
            "sel": 'tr.mrow[data-sector="cn_t00"] td[colspan] .rk.na',
            "tip_sel": 'tr.mrow[data-sector="cn_t00"] td[colspan] .lens-q',
            "action": "open-member-tip",
        })
    # (d) h1 22px/800 with eyebrow in frame (visual)
    for theme in ("dark", "light"):
        for locale in ("en", "zh"):
            cells.append({
                "id": f"h1-{theme}-{locale}",
                "family": "h1", "theme": theme, "locale": locale,
                "w": 1440, "h": 900, "kind": "element",
                "sel": ".fv-hero-eyebrow", "action": None,
            })
    # (e) capped board: 8 rows + See all 9, expanded, sort-reset
    for theme in ("dark", "light"):
        cells.append({
            "id": f"board-cap-{theme}-en",
            "family": "board", "theme": theme, "locale": "en",
            "w": 1440, "h": 900, "kind": "element",
            "sel": "#groups .fv-board-block", "action": None,
        })
        cells.append({
            "id": f"board-expanded-{theme}-en",
            "family": "board", "theme": theme, "locale": "en",
            "w": 1440, "h": 900, "kind": "element",
            "sel": "#groups .fv-board-block", "action": "expand",
        })
    cells.append({
        "id": "board-sortreset-dark-en",
        "family": "board", "theme": "dark", "locale": "en",
        "w": 1440, "h": 900, "kind": "element",
        "sel": "#groups .fv-board-block", "action": "sortreset",
    })
    # (f) MIN-7 a11y: label-as-button focus ring
    cells.append({
        "id": "a11y-focus-dark-en",
        "family": "a11y", "theme": "dark", "locale": "en",
        "w": 1440, "h": 900, "kind": "element",
        "sel": "#groups .fv-see-all", "action": "focus",
    })
    # (g) four designed degraded states, both themes
    for theme in ("dark", "light"):
        cells.append({
            "id": f"degraded-trust-{theme}-en",
            "family": "degraded", "theme": theme, "locale": "en",
            "w": 1440, "h": 900, "kind": "element",
            "sel": "#sources .fv-trust-row", "action": None,
        })
        cells.append({
            "id": f"degraded-insuff-{theme}-en",
            "family": "degraded", "theme": theme, "locale": "en",
            "w": 1440, "h": 900, "kind": "element",
            "sel": 'tr.sector-row[data-sector="cn_t02"]', "action": None,
        })
    return cells


def _union_clip(a: dict, b: dict, vw: int, vh: int) -> dict:
    x1 = max(0, min(a["x"], b["x"]))
    y1 = max(0, min(a["y"], b["y"]))
    x2 = min(vw, max(a["x"] + a["width"], b["x"] + b["width"]))
    y2 = min(vh, max(a["y"] + a["height"], b["y"] + b["height"]))
    return {
        "x": int(x1), "y": int(y1),
        "width": max(1, int(x2 - x1)), "height": max(1, int(y2 - y1)),
    }


def _do_action(page, spec: dict) -> dict:
    extra: dict = {}
    action = spec.get("action")
    if action == "tip":
        # Desktop LENS is hover-intent (90ms). A Playwright click on .lens-q is a
        # pin-toggle: hover-open then click-close, so the pop never stays .open.
        q = page.locator(spec["tip_sel"]).first
        q.wait_for(state="visible", timeout=8000)
        q.scroll_into_view_if_needed()
        q.hover()
        page.locator(".lens-pop.open").first.wait_for(state="visible", timeout=4000)
    elif action == "open-momentum":
        loc = page.locator("#momentum summary").first
        loc.wait_for(state="visible", timeout=8000)
        loc.scroll_into_view_if_needed()
        loc.click()
        page.locator("#momentum .fv-mom").first.wait_for(state="visible", timeout=4000)
    elif action == "open-member-tip":
        row = page.locator('tr.sector-row[data-sector="cn_t00"]').first
        row.wait_for(state="visible", timeout=8000)
        row.scroll_into_view_if_needed()
        if row.get_attribute("aria-expanded") != "true":
            row.click()
        mrow = page.locator('tr.mrow[data-sector="cn_t00"]').first
        mrow.wait_for(state="visible", timeout=4000)
        q = page.locator(spec["tip_sel"]).first
        q.hover()
        page.locator(".lens-pop.open").first.wait_for(state="visible", timeout=4000)
    elif action == "expand":
        lab = page.locator("#groups .fv-see-all").first
        lab.wait_for(state="visible", timeout=8000)
        lab.scroll_into_view_if_needed()
        lab.click()
        extra["aria_expanded"] = lab.get_attribute("aria-expanded")
        extra["visible_heads"] = page.evaluate(
            """() => document.querySelectorAll('#sectortbl tr.sector-row:not([style*="display: none"])').length""")
    elif action == "sortreset":
        lab = page.locator("#groups .fv-see-all").first
        lab.wait_for(state="visible", timeout=8000)
        lab.scroll_into_view_if_needed()
        lab.click()
        extra["expanded_before_sort"] = lab.get_attribute("aria-expanded")
        th = page.locator("#sectortbl th[data-c='4']").first
        th.click()
        extra["aria_expanded"] = lab.get_attribute("aria-expanded")
        extra["toggle_checked"] = page.evaluate(
            """() => { const t = document.querySelector('#fv-cap-sectortbl'); return t ? t.checked : null; }""")
        extra["sort_class"] = th.get_attribute("class")
    elif action == "focus":
        lab = page.locator("#groups .fv-see-all").first
        lab.wait_for(state="visible", timeout=8000)
        lab.scroll_into_view_if_needed()
        lab.focus()
        extra["focus_tag"] = page.evaluate(
            "() => document.activeElement && document.activeElement.className")
    return extra


def _screenshot(page, spec: dict) -> bytes:
    kind = spec["kind"]
    if kind == "fullpage":
        return page.screenshot(type="png", full_page=True)
    loc = page.locator(spec["sel"]).first
    loc.wait_for(state="visible", timeout=8000)
    loc.scroll_into_view_if_needed()
    if kind == "union-tip":
        host = loc.bounding_box()
        pop = page.locator(".lens-pop.open").first
        pop.wait_for(state="visible", timeout=4000)
        box = pop.bounding_box()
        if host is None or box is None:
            return page.screenshot(type="png")
        clip = _union_clip(host, box, spec["w"], spec["h"])
        pad = 8
        clip["x"] = max(0, clip["x"] - pad)
        clip["y"] = max(0, clip["y"] - pad)
        clip["width"] = min(spec["w"] - clip["x"], clip["width"] + 2 * pad)
        clip["height"] = min(spec["h"] - clip["y"], clip["height"] + 2 * pad)
        return page.screenshot(type="png", clip=clip)
    return loc.screenshot(type="png")


def _write_readme(sha: str, rows: list[dict], hscroll: dict, r2_deleted: list[str]) -> str:
    lines = [
        "# flow_velocity W13 r3 — settled evidence matrix",
        "",
        f"Provenance: committed head `{sha}`. Porcelain empty at capture.",
        "S1 rig: fixture VM (no live bake), real `body.page-flow-velocity`, Playwright",
        "localStorage seed + setTheme/setLang, `window.__skyDeck = true`, attribute",
        "re-read refuse-on-mismatch, overlay column, SETTLE column.",
        "",
        "## DARK TREATMENT",
        "",
        "Command center. r1/r2 surfaces sit on the existing luminous card — hairline",
        "`--grid`, `--card` fill, `--ink` / `--muted` / `--faint` as instrument captions.",
        "The h1 is ink at 22px/800 (a real title, not the 11px muted eyebrow). The",
        "See-all chip is a flat hairline control. `.fv-caption` and `.empty-why` are",
        "muted captions. The footer is faint on a `--grid` rule; `<b>` is muted.",
        "Monoline icons inherit currentColor (restrained glow lives on the hero card,",
        "not the glyph). STALE chips: desaturated amber ring + dimmed body.",
        "UNAVAILABLE: dashed border. DEGRADED/behind: amber wash + glow.",
        "",
        "## LIGHT TREATMENT",
        "",
        "Research workspace. Same information architecture, different material.",
        "Paper `--card`, hairline `--line`, SHORT SHADOW instead of glow on the",
        "See-all chip. Caption / empty-why / footer ink is mixed toward `--ink`",
        "because `--muted`/`--faint` wash out on white. The h1 stays 22px ink, no",
        "uppercase tracking. Footer `<b>` is `--ink` (a source label on paper, not a",
        "faint caption). STALE: tinted paper + inset amber rule + deepened ink.",
        "UNAVAILABLE: hatched/dashed hairline — must not read as a dirty smudge.",
        "DEGRADED/behind: amber-tinted paper + inset rule.",
        "",
        "## Mechanisms that INTENTIONALLY differ",
        "",
        "1. See-all depth — dark = flat hairline chip; light = paper chip + 1px shadow.",
        "2. Caption contrast — dark can use `--muted`/`--faint`; light deepens toward `--ink`.",
        "3. Footer label weight — dark muted, light ink.",
        "4. Degraded chips — dark = glow/desaturate; light = tinted paper + hatch/inset,",
        "   never a token-swap of the glow.",
        "Shared on purpose: spacing, type scale, chip geometry, icon stroke",
        "(currentColor), interaction (checkbox latch, LENS `?`).",
        "",
        f"## SETTLE gate",
        "",
        "`document.fonts.ready`, then `getAnimations({subtree:true})` empty-or-finished",
        "on the content root (force-finish). Effective opacity == 1 on the board/content",
        "root AND a sampled row. Header-cell contrast recorded. A cell that fails settle",
        "is REFUSED, not captured. Reduced-motion is not the settle mechanism.",
        "",
        "## Horizontal page scroll at 390w",
        "",
    ]
    for lang, rec in (hscroll or {}).items():
        lines.append(
            f"- {lang}: client={rec.get('client_width')} scroll={rec.get('scroll_width')} "
            f"overflow={rec.get('overflow')} → {'none' if rec.get('ok') else 'FAIL'}"
        )
    lines += [
        "",
        "## Deleted r2 PNGs (content-addressed reconciliation)",
        "",
        "Faded r2 cells captured mid-`fvReveal` (~15% effective contrast) are unjudgeable.",
        "Removed in this evidence commit:",
        "",
    ]
    for name in r2_deleted:
        lines.append(f"- `{name}`")
    lines += [
        "",
        "## Cells",
        "",
        "| id | family | theme | lang | overlay | settle | root opacity | row opacity | header contrast | alias |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        st = r.get("settle") or {}
        lines.append(
            f"| {r['id']} | {r.get('family','')} | {r['theme']} | {r['locale']} | "
            f"{r.get('overlay')} | {st.get('reason','')} | {st.get('root_opacity')} | "
            f"{st.get('row_opacity')} | {st.get('header_contrast')} | `{r['alias']}` |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(f"playwright missing: {exc}") from exc

    sha = _require_clean_head()
    _prepare_scratch(SCRATCH)
    httpd, port = serve_site_dir(SCRATCH)
    base = f"http://127.0.0.1:{port}/flow_velocity.html"
    if CELLS_DIR.exists():
        shutil.rmtree(CELLS_DIR)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)

    specs = _cell_matrix()
    rows: list[dict] = []
    hscroll: dict = {}
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        for spec in specs:
            state = {"theme": spec["theme"], "locale": spec["locale"]}
            ctx = browser.new_context(
                viewport={"width": spec["w"], "height": spec["h"]},
                locale="zh-CN" if spec["locale"] == "zh" else "en-US",
                color_scheme=spec["theme"], device_scale_factor=1,
            )
            ctx.add_init_script(f"({_STATE_SEED.strip()})({json.dumps(state)})")
            page = ctx.new_page()
            resp = page.goto(base, wait_until="load", timeout=30000)
            if resp is None or not resp.ok:
                raise RuntimeError(f"HTTP {getattr(resp, 'status', None)} on {spec['id']}")
            applied = page.evaluate(_APPLY_STATE.strip(), state) or {}
            if applied.get("theme") != spec["theme"] or applied.get("locale") != spec["locale"]:
                raise RuntimeError(f"state mismatch {spec['id']}: {applied}")
            extra = _do_action(page, spec)
            settle = page.evaluate(_SETTLE_JS.strip(), spec["sel"]) or {}
            if not settle.get("ok"):
                raise RuntimeError(f"SETTLE REFUSED {spec['id']}: {settle}")
            overlay = page.evaluate(_OVERLAY_JS.strip(), spec["sel"])
            if not overlay.get("ok"):
                raise RuntimeError(f"overlay over {spec['id']}: {overlay}")
            if spec.get("hscroll"):
                hs = page.evaluate(_HSCROLL_JS.strip()) or {}
                hscroll[spec["locale"]] = hs
                extra["hscroll"] = hs
                if not hs.get("ok"):
                    raise RuntimeError(f"page h-scroll at 390w {spec['locale']}: {hs}")
            png = _screenshot(page, spec)
            name, digest, pw_, ph = _png_meta(png)
            (CELLS_DIR / name).write_bytes(png)
            alias = f"{spec['id']}.png"
            (CELLS_DIR / alias).write_bytes(png)
            rows.append({
                "id": spec["id"], "family": spec["family"],
                "file": name, "alias": alias, "sha256": digest,
                "bytes": len(png), "width": pw_, "height": ph,
                "theme": spec["theme"], "locale": spec["locale"],
                "viewport": f"{spec['w']}x{spec['h']}",
                "applied_theme": applied.get("theme"),
                "applied_locale": applied.get("locale"),
                "body_class": applied.get("body"),
                "overlay": "clean", "overlay_hits": overlay.get("hits") or [],
                "settle": {
                    "ok": True,
                    "reason": settle.get("reason"),
                    "root_opacity": settle.get("root_opacity"),
                    "row_opacity": settle.get("row_opacity"),
                    "header_contrast": settle.get("header_contrast"),
                    "header_color": settle.get("header_color"),
                    "running": settle.get("running"),
                    "fonts": settle.get("fonts"),
                },
                "receipts": extra,
            })
            ctx.close()
        browser.close()
        pw.stop()
    finally:
        httpd.shutdown()

    r2_deleted: list[str] = []
    if R2_DIR.exists():
        cells = R2_DIR / "cells"
        if cells.is_dir():
            for p in sorted(cells.iterdir()):
                r2_deleted.append(str(p.relative_to(_ROOT)))
                p.unlink()
            cells.rmdir()
        for leftover in ("manifest.json", "README.md"):
            lp = R2_DIR / leftover
            if lp.exists():
                r2_deleted.append(str(lp.relative_to(_ROOT)))
                lp.unlink()
        try:
            R2_DIR.rmdir()
        except OSError:
            pass

    manifest = {
        "page": "flow_velocity.html",
        "round": "W13-r3",
        "target": {
            "resolved_sha_or_none": sha,
            "porcelain": "empty",
            "capture_sha_equals_head": True,
        },
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "selection": {"n": len(rows), "ids": [r["id"] for r in rows]},
        "totals": {"captured": len(rows), "failed": 0, "refused_settle": 0},
        "hscroll_390w": hscroll,
        "r2_deleted": r2_deleted,
        "cells": rows,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "README.md").write_text(
        _write_readme(sha, rows, hscroll, r2_deleted), encoding="utf-8")
    print(json.dumps({
        "sha": sha, "n": len(rows), "out": str(OUT_DIR),
        "hscroll": hscroll, "r2_deleted": len(r2_deleted),
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CaptureUnavailable as exc:
        print(f"capture unavailable: {exc}", file=sys.stderr)
        raise SystemExit(4) from exc
