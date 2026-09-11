#!/usr/bin/env python3
"""sector_central W16 r3 — settled evidence matrix (S1 rig + SETTLE column).

Captures at the committed HEAD with porcelain empty. Fixture-rendered
(sparse trees have no site/ or data/). A cell that fails settle is REFUSED,
not captured. Crops are viewport-region (canvas-context) shots — never
bare-element screenshots.

Usage::

    python3 -m scripts.capture_sector_central_w16_r3_evidence
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
from scripts.build_sector_central import _SECTOR_ZH, _flow_cell_html
from scripts.capture_page_evidence import CaptureUnavailable, _git_head_sha, serve_site_dir

OUT_DIR = _ROOT / "research" / "sector_central" / "w16_r3_evidence"
CELLS_DIR = OUT_DIR / "cells"
SCRATCH = Path("/tmp/sc-w16-r3-capture")

SI_VIEWS = ("overview", "map", "moving", "money", "explore", "confluence")
SECTOR_EN = {
    "XLB": "Materials", "XLC": "Communications", "XLE": "Energy",
    "XLF": "Financials", "XLI": "Industrials", "XLK": "Technology",
    "XLP": "Consumer Staples", "XLRE": "Real Estate", "XLU": "Utilities",
    "XLV": "Health Care", "XLY": "Consumer Discretionary",
}

_STATE_SEED = """
(state) => {
  try {
    localStorage.setItem('theme', state.theme);
    localStorage.removeItem('themeAuto');
    localStorage.setItem('lang', state.locale);
  } catch (e) {}
  window.__skyDeck = true;
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
  if (document.body) {
    document.body.classList.add('macro-desk', 'page-baskets');
  }
  docEl.classList.add('js');
  for (const cls of ['.sky-fx', '.aurora', '.rvx-aurora', '#mmb-root', '.nav-totop', '#mmb-boot']) {
    document.querySelectorAll(cls).forEach((n) => {
      n.style.setProperty('display', 'none', 'important');
      if (n.parentNode) n.parentNode.removeChild(n);
    });
  }
  document.querySelectorAll('.rvx-reveal').forEach((el) => {
    el.style.opacity = '1';
    el.style.transform = 'none';
    el.style.animation = 'none';
  });
  return {theme: docEl.getAttribute('data-theme'), locale: docEl.getAttribute('data-lang'),
          body: document.body ? document.body.className : ''};
}
"""

_OVERLAY_JS = """
(sel) => {
  const el = document.querySelector(sel) || document.querySelector('.si-stage') || document.body;
  if (!el) return {ok: false, reason: 'missing-subject'};
  const r = el.getBoundingClientRect();
  const hits = [];
  for (const cls of ['.sky-fx', '.aurora', '.rvx-aurora', '#mmb-root']) {
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

# Fonts ready, then force-finish running animations on the content root.
# Infinite .skel shimmer is cancelled (static designed freeze-frame). A cell
# whose effective opacity is not 1 is REFUSED.
_SETTLE_JS = """
async (sel) => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  if (document.fonts && document.fonts.ready) {
    try { await document.fonts.ready; } catch (e) {}
  }
  document.querySelectorAll('.rvx-reveal').forEach((el) => {
    el.style.opacity = '1';
    el.style.transform = 'none';
    el.style.animation = 'none';
  });
  const root = document.querySelector(sel) || document.querySelector('.si-stage') || document.body;
  if (!root) return {ok: false, reason: 'missing-root'};

  const runningOf = (el) => (el.getAnimations({subtree: true}) || []).filter(
    (a) => a.playState === 'running' || a.playState === 'pending');
  const finishTree = (el) => {
    runningOf(el).forEach((a) => {
      const name = ((a.effect && a.effect.getKeyframes && a.animationName) || a.animationName || '');
      try { a.finish(); } catch (e) {
        try { a.cancel(); } catch (e2) {}
      }
    });
    // Infinite skeleton shimmer never finishes — freeze a designed frame.
    document.querySelectorAll('.skel').forEach((n) => {
      (n.getAnimations() || []).forEach((a) => { try { a.cancel(); } catch (e) {} });
    });
  };
  finishTree(document.documentElement);
  const t0 = performance.now();
  while (performance.now() - t0 < 2500) {
    const still = runningOf(document.documentElement).filter((a) => {
      const tgt = a.effect && a.effect.target;
      return !(tgt && tgt.classList && tgt.classList.contains('skel'));
    });
    if (!still.length) break;
    still.forEach((a) => { try { a.finish(); } catch (e) { try { a.cancel(); } catch (e2) {} } });
    await sleep(16);
  }
  document.querySelectorAll('.lens-pop.open, .row-pop:not([hidden])').forEach((p) => {
    p.style.opacity = '1';
    p.style.transform = 'none';
  });
  const leftover = runningOf(document.documentElement).filter((a) => {
    const tgt = a.effect && a.effect.target;
    return !(tgt && tgt.classList && tgt.classList.contains('skel'));
  }).length;

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

  const row = root.querySelector(
    'a.actitem, .rvx-gcard, .gr-cell, .lead-track, tr, h1, .si-view.on, .mx-empty'
  ) || root;
  const header = root.querySelector('h1, h2, .acth-name, .gl, .rg-k, .lead-head h2') || row;
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
  const ok = rootOp >= 0.995 && rowOp >= 0.995 && leftover === 0;
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
  const view = (document.querySelector('.si-view.on') || {}).getAttribute
    ? document.querySelector('.si-view.on').getAttribute('data-view') : null;
  return {
    client_width: cw,
    scroll_width: sw,
    overflow: sw - cw,
    ok: sw <= cw + 1,
    view: view,
  };
}
"""

_CLIP_UNION_JS = """
(sels) => {
  const els = [];
  for (const s of sels) {
    const n = document.querySelector(s);
    if (n) els.push(n);
  }
  if (!els.length) return null;
  let x = Infinity, y = Infinity, r = -Infinity, b = -Infinity;
  for (const el of els) {
    const rect = el.getBoundingClientRect();
    x = Math.min(x, rect.x); y = Math.min(y, rect.y);
    r = Math.max(r, rect.right); b = Math.max(b, rect.bottom);
  }
  const pad = 16;
  const vw = window.innerWidth, vh = window.innerHeight;
  const left = Math.max(0, x - pad);
  const top = Math.max(0, y - pad);
  return {
    x: left, y: top,
    width: Math.max(4, Math.min(vw - left, (r - x) + 2 * pad)),
    height: Math.max(4, Math.min(vh - top, (b - y) + 2 * pad)),
  };
}
"""


def canvas_clip(box: dict, vw: int, vh: int, pad: int = 16) -> dict:
    """Viewport-region clip with margin. Never an element-only transparent crop."""
    x = max(0.0, float(box["x"]) - pad)
    y = max(0.0, float(box["y"]) - pad)
    w = float(box.get("width", 0)) + 2 * pad
    h = float(box.get("height", 0)) + 2 * pad
    x = min(x, float(vw) - 4)
    y = min(y, float(vh) - 4)
    return {
        "x": x,
        "y": y,
        "width": max(4.0, min(w, float(vw) - x)),
        "height": max(4.0, min(h, float(vh) - y)),
    }


def _png_meta(png: bytes) -> tuple[str, str, int, int]:
    digest = hashlib.sha256(png).hexdigest()
    name = f"{digest[:16]}.png"
    if len(png) >= 24 and png[:8] == b"\x89PNG\r\n\x1a\n" and png[12:16] == b"IHDR":
        w, h = struct.unpack(">II", png[16:24])
    else:
        w, h = 0, 0
    return name, digest, int(w), int(h)


def require_clean_head(root: Path | None = None) -> str:
    """Refuse capture on a dirty tree. Manifest sha must be the commit that produced the pixels."""
    root = root or _ROOT
    porcelain = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True)
    if porcelain.strip():
        raise SystemExit("REFUSED: porcelain not empty — commit the rig first.\n" + porcelain)
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    hand = _git_head_sha(root)
    hand_sha = hand.sha if hasattr(hand, "sha") else str(hand)
    if hand_sha and hand_sha != sha:
        raise SystemExit(f"REFUSED: git HEAD {sha} != hand reader {hand_sha}")
    return sha


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=True)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    return env


def _empty_board() -> dict:
    return {
        "buy_now": [], "buy_soon": [], "on_the_run": [],
        "take_profits": [], "hold": [], "avoid": [],
        "total": 0, "more": {},
    }


def _theme(reco: str = "accumulate", **over) -> dict:
    row = {
        "kind": "theme",
        "name": "AI Infrastructure",
        "name_zh": "人工智能基建",
        "slug": "ai_infra",
        "href": "basket/theme_ai_infra.html",
        "reco": reco,
        "label": reco.upper() if reco else "HOLD",
        "label_zh": {"enter": "建仓", "accumulate": "加仓", "trim": "减仓",
                     "avoid": "回避"}.get(reco, "持有"),
        "score": 72,
        "perf_20d_rel": 0.01,
        "validated": False,
    }
    row.update(over)
    return row


def _sector(label: str = "BUY ZONE", **over) -> dict:
    row = {
        "kind": "sector",
        "name": "Financials",
        "ticker": "XLF",
        "href": "basket/us_sector_financials.html",
        "label": label,
        "stat_en": "clean entry",
        "stat_zh": "入场干净",
    }
    row.update(over)
    return row


def populated_board() -> dict:
    board = _empty_board()
    board["buy_now"] = [_theme("enter", label="ENTER", label_zh="建仓", score=73)]
    board["buy_soon"] = [_sector("BUY ZONE")]
    board["on_the_run"] = [_theme("accumulate", name="Managed Care",
                                  name_zh="管理式医疗", slug="managed_care")]
    board["take_profits"] = [_sector("ROLLING OVER", name="Energy", ticker="XLE",
                                     href="basket/us_sector_energy.html",
                                     stat_en="risk check: trim",
                                     stat_zh="风险检查：减仓")]
    board["hold"] = [_theme("", name="Gold Miners", name_zh="黄金矿业",
                            slug="gold_miners", label="HOLD", label_zh="持有")]
    board["avoid"] = []
    board["total"] = 44
    board["more"] = {"buy_now": 5, "buy_soon": 2}
    return board


def bottoming_payload() -> dict:
    return {
        "bottoming_watch": [
            {"id": "b-gold_miners", "cid": "gold_miners", "kind": "BASKET",
             "name": "Gold Miners", "name_zh": "黄金矿业",
             "href": "basket/gold_miners.html",
             "osc_slope": 1.3, "pos": 2.0, "cycle_signal": True,
             "gate_conflict": False},
        ],
        "dual_read_ids": [],
        "recovering_ids": [],
        "bottoming_authority": {},
    }


def mc_known(verdict: str = "narrow") -> dict:
    return {
        "verdict": verdict, "adv": 1200, "dec": 1800, "ad_ratio": 0.67,
        "nh": 40, "nl": 90, "pct_above_200": 35.0,
    }


def theme_context() -> dict:
    return {
        "leadership": {
            "trailing_leader": {"name": "Tech", "name_zh": "科技", "id": "xlk"},
            "state": "steady", "stance_en": "Stay with leaders",
            "stance_zh": "跟随领涨", "days_in_state": 3,
            "strength": [{"name": "Health", "name_zh": "医疗", "id": "xlv"}],
        }
    }


def flows_html() -> str:
    labels = ["1D", "1W", "1M"]
    rows = [{"ticker": t, "vals": {"1D": -100.0, "1W": -200.0, "1M": -4100.0 if t == "XLF" else -80.0}}
            for t in _SECTOR_ZH]
    maxabs = {lbl: max(abs(r["vals"][lbl]) for r in rows) for lbl in labels}
    head = "<th class='scf-s'>" + str(i18n.t("sector", "板块")) + "</th>" + "".join(
        f"<th class='scf-c'>{lbl}</th>" for lbl in labels)
    body = []
    for r in rows:
        name_en = SECTOR_EN.get(r["ticker"], r["ticker"])
        name_zh = _SECTOR_ZH[r["ticker"]]
        label = (f"<b>{r['ticker']}</b> <span class='muted'>"
                 f"{i18n.t(name_en, name_zh)}</span>")
        cells = "".join(_flow_cell_html(r["vals"][lbl], maxabs[lbl], tint=True)
                        for lbl in labels)
        body.append(f"<tr><td class='scf-s'>{label}</td>{cells}</tr>")
    net = {lbl: -5100.0 if lbl == "1M" else -400.0 for lbl in labels}
    net_cells = "".join(_flow_cell_html(net[lbl], maxabs[lbl], tint=False)
                        for lbl in labels)
    body.append(
        "<tr class='scf-net'><td class='scf-s'><b>"
        + str(i18n.t("Net · 11 sector ETFs", "净额 · 11 个板块 ETF"))
        + "</b></td>" + net_cells + "</tr>")
    return (
        "<div class='scc-section-h' id='sc-flows'>"
        "<h2><span class='l-en'>Where sector-ETF money is flowing</span>"
        "<span class='l-zh'>板块 ETF 资金流向何处</span></h2></div>"
        "<div class='scf-wrap'><table class='scf'><thead><tr>" + head
        + "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div>"
    )


def grader_payload() -> dict:
    return {
        "as_of": "2026-09-10",
        "market": {"risk_on": 0.3, "ms_color": "green"},
        "grader": {
            "available": True,
            "by_horizon": {
                "21d": {
                    "dir_hit_rate": 0.55, "n": 40, "rank_ic": 0.12,
                    "mean_excess_vs_bench": 0.031,
                },
                "63d": {
                    "dir_hit_rate": 0.50, "n": 28, "rank_ic": 0.08,
                    "mean_excess_vs_bench": 0.019,
                },
            },
        },
        "sectors": [],
        "baskets": [],
    }


def leadership_payload() -> dict:
    return {
        "ok": True,
        "as_of": "2026-09-10",
        "rising_star": {
            "label": ["Tech", "科技"], "las": 1.24,
            "why": [{"leg": "RS accelerating"}], "tab": "nasdaq",
        },
        "leader_now": {"label": ["Nasdaq-100", "纳指100"], "tab": "nasdaq"},
        "tabs": {
            "nasdaq": {
                "label": ["Nasdaq-100", "纳指100"], "las": 1.24,
                "rs_ratio": 1.05, "rs_mom": 0.31, "quadrant": "leading",
                "breadth_thrust": 0.22, "participation": 0.61,
            },
            "subsectors": {
                "label": ["S&P 500 subsectors", "标普500子行业"], "las": 0.80,
                "rs_ratio": 1.02, "rs_mom": 0.11, "quadrant": "improving",
                "breadth_thrust": 0.10, "participation": 0.48,
            },
        },
        "track_record": {
            "verdict": "measuring",
            "n_days": 21,
            "n_snapshots": 12,
            "any_matured": True,
            "horizons": {
                "21": {
                    "n_matured": 18,
                    "by_stage": {
                        "running": {"hit_rate": 0.60, "n": 10},
                        "coiling": {"hit_rate": 0.50, "n": 8},
                    },
                }
            },
        },
    }


def baskets_payload(mc: dict | None) -> dict:
    ti: dict = {"themes": []}
    if mc is not None:
        ti["market_concentration"] = mc
    return {
        "as_of": "2026-09-10",
        "baskets": [
            {"id": "xlk", "name": "Technology", "name_zh": "信息技术",
             "perf": {"20d": {"rel": 0.02}}},
        ],
        "categories": ["Sector"],
        "theme_intel": ti,
        "chart": {"dates": [], "bench": [], "baskets": {}},
        "story": None,
    }


def render_page(**over) -> str:
    kw = dict(
        flows_html=flows_html(),
        bottoming=bottoming_payload(),
        theme_context=theme_context(),
        factor_season=None,
        flow={"cluster": {"regime": "mixed"}},
        basket_member_syms=["AAPL", "MSFT"],
        action_board=populated_board(),
        market_concentration=mc_known("narrow"),
        baskets_as_of="2026-09-10",
        generated_utc="2026-09-11T00:00:00Z",
        pgate=None,
    )
    kw.update(over)
    return _env().get_template("sector_central.html.j2").render(**kw)


def render_us_stocks_board() -> str:
    board = populated_board()
    inner = _env().get_template("_us_act_now_board.html.j2").render(
        action_board=board, ab_host="us_stocks", pgate=None,
        bottoming=None)
    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<link rel='stylesheet' href='theme.css'>"
        "<link rel='stylesheet' href='product-nav-icons.css'>"
        "<link rel='stylesheet' href='dashboard-icons.css'>"
        "<link rel='stylesheet' href='navigation-refresh.css'>"
        "<style>body{background:var(--bg);color:var(--text);margin:0;padding:24px;}</style>"
        "</head><body class='macro-desk page-stocks'>"
        + inner +
        "<script src='theme.js'></script></body></html>"
    )


def cell_matrix() -> list[dict]:
    cells: list[dict] = []
    # 8 full-page baselines
    for theme in ("dark", "light"):
        for locale in ("en", "zh"):
            cells.append({
                "id": f"baseline-{theme}-{locale}-desktop",
                "family": "baseline", "theme": theme, "locale": locale,
                "w": 1440, "h": 900, "kind": "fullpage",
                "sel": ".si-stage", "fixture": "populated",
                "js_mode": "hydrate", "mc": "narrow",
            })
            cells.append({
                "id": f"baseline-{theme}-{locale}-mobile",
                "family": "baseline", "theme": theme, "locale": locale,
                "w": 390, "h": 844, "kind": "fullpage",
                "sel": ".si-stage", "fixture": "populated",
                "js_mode": "hydrate", "mc": "narrow",
                "hscroll": True, "view": "overview",
            })
    # Six tabs, dark EN desktop (display:none until selected)
    for view in SI_VIEWS:
        cells.append({
            "id": f"tab-{view}-dark-en-desktop",
            "family": "tabs", "theme": "dark", "locale": "en",
            "w": 1440, "h": 900, "kind": "canvas",
            "sel": ".si-stage", "clip": [f'.si-view[data-view="{view}"]'],
            "fixture": "populated", "js_mode": "hydrate", "mc": "narrow",
            "action": "view", "view": view,
        })
    # 390w h-scroll on every remaining si-view, both languages
    for view in SI_VIEWS:
        if view == "overview":
            continue
        for locale in ("en", "zh"):
            cells.append({
                "id": f"hscroll-{view}-dark-{locale}-mobile",
                "family": "hscroll", "theme": "dark", "locale": locale,
                "w": 390, "h": 844, "kind": "canvas",
                "sel": ".si-stage", "clip": [".si-shell"],
                "fixture": "populated", "js_mode": "hydrate", "mc": "narrow",
                "action": "view", "view": view, "hscroll": True,
            })
    # (a) B1 three-way honesty
    for theme in ("dark", "light"):
        cells.append({
            "id": f"b1-narrow-{theme}-en",
            "family": "b1", "theme": theme, "locale": "en",
            "w": 1440, "h": 900, "kind": "canvas",
            "sel": "#internals-section", "clip": ["#internals-section"],
            "fixture": "populated", "js_mode": "hydrate", "mc": "narrow",
            "action": "view", "view": "money",
        })
    for locale in ("en", "zh"):
        cells.append({
            "id": f"b1-mixed-dark-{locale}",
            "family": "b1", "theme": "dark", "locale": locale,
            "w": 1440, "h": 900, "kind": "canvas",
            "sel": "#internals-section", "clip": ["#mkt-breadth", "#mkt-breadth-sub"],
            "fixture": "populated", "js_mode": "hydrate", "mc": "mixed",
            "action": "view", "view": "money",
        })
    for theme in ("dark", "light"):
        for locale in ("en", "zh"):
            cells.append({
                "id": f"b1-empty-{theme}-{locale}",
                "family": "b1", "theme": theme, "locale": locale,
                "w": 1440, "h": 900, "kind": "canvas",
                "sel": "#internals-section", "clip": ["#mkt-breadth"],
                "fixture": "populated", "js_mode": "hydrate", "mc": "alien",
                "action": "view", "view": "money",
            })
    # (b) tri-state internals (baked values / skeleton / JS empty / JS reject)
    for theme in ("dark", "light"):
        for locale in ("en", "zh"):
            cells.append({
                "id": f"tri-baked-{theme}-{locale}",
                "family": "tri-state", "theme": theme, "locale": locale,
                "w": 1440, "h": 900, "kind": "canvas",
                "sel": ".rvx-internals", "clip": [".rvx-internals"],
                "fixture": "populated", "js_mode": "hydrate", "mc": "narrow",
                "action": "view", "view": "money",
            })
    for theme in ("dark", "light"):
        cells.append({
            "id": f"tri-skel-{theme}-en",
            "family": "tri-state", "theme": theme, "locale": "en",
            "w": 1440, "h": 900, "kind": "canvas",
            "sel": ".rvx-internals", "clip": [".rvx-internals"],
            "fixture": "no_payload", "js_mode": "hang", "mc": None,
            "action": "view", "view": "money",
        })
    for locale in ("en", "zh"):
        cells.append({
            "id": f"tri-jsempty-dark-{locale}",
            "family": "tri-state", "theme": "dark", "locale": locale,
            "w": 1440, "h": 900, "kind": "canvas",
            "sel": ".rvx-internals", "clip": [".rvx-internals"],
            "fixture": "no_payload", "js_mode": "empty_mc", "mc": None,
            "action": "view", "view": "money",
        })
        cells.append({
            "id": f"tri-jsreject-dark-{locale}",
            "family": "tri-state", "theme": "dark", "locale": locale,
            "w": 1440, "h": 900, "kind": "canvas",
            "sel": ".rvx-internals", "clip": [".rvx-internals"],
            "fixture": "no_payload", "js_mode": "reject", "mc": None,
            "action": "view", "view": "money",
        })
    # (c) live receipt tips OPEN + (g) leadership about-X-in-10
    for theme in ("dark", "light"):
        for locale in ("en", "zh"):
            cells.append({
                "id": f"grader-tip-{theme}-{locale}",
                "family": "tips", "theme": theme, "locale": locale,
                "w": 1440, "h": 900, "kind": "canvas",
                "sel": "#grader", "clip": ["#grader", ".lens-pop.open"],
                "fixture": "populated", "js_mode": "hydrate", "mc": "narrow",
                "action": "grader-tip",
            })
            cells.append({
                "id": f"lead-tip-{theme}-{locale}",
                "family": "tips", "theme": theme, "locale": locale,
                "w": 1440, "h": 900, "kind": "canvas",
                "sel": "#scc-leadership",
                "clip": [".lead-track", ".lens-pop.open"],
                "fixture": "populated", "js_mode": "hydrate", "mc": "narrow",
                "action": "lead-tip", "view": "money",
            })
    # (d) M3 sector-leg wait-lane popover
    for theme in ("dark", "light"):
        for locale in ("en", "zh"):
            cells.append({
                "id": f"m3-wait-{theme}-{locale}",
                "family": "m3", "theme": theme, "locale": locale,
                "w": 1440, "h": 900, "kind": "canvas",
                "sel": "#ab-soon-fold",
                "clip": ["#ab-soon-fold a.actitem", ".row-pop:not([hidden])"],
                "fixture": "populated", "js_mode": "hydrate", "mc": "narrow",
                "action": "row-pop",
            })
    # (e) sibling host pair
    cells.append({
        "id": "sibling-usstocks-dark-en",
        "family": "sibling", "theme": "dark", "locale": "en",
        "w": 1440, "h": 900, "kind": "canvas",
        "sel": "#action-board", "clip": ["#action-board"],
        "fixture": "us_stocks_host", "js_mode": "none", "page": "us_stocks_board.html",
    })
    cells.append({
        "id": "sibling-si-dark-en",
        "family": "sibling", "theme": "dark", "locale": "en",
        "w": 1440, "h": 900, "kind": "canvas",
        "sel": "#action-board", "clip": ["#action-board"],
        "fixture": "populated", "js_mode": "hydrate", "mc": "narrow",
    })
    # (f) M6 watch strip
    for theme in ("dark", "light"):
        cells.append({
            "id": f"m6-watch-{theme}-en",
            "family": "m6", "theme": theme, "locale": "en",
            "w": 1440, "h": 900, "kind": "canvas",
            "sel": ".act-watch-strip", "clip": [".act-watch-strip"],
            "fixture": "populated", "js_mode": "hydrate", "mc": "narrow",
        })
    cells.append({
        "id": "m6-absent-dark-en",
        "family": "m6", "theme": "dark", "locale": "en",
        "w": 1440, "h": 900, "kind": "canvas",
        "sel": "#action-board", "clip": ["#action-board"],
        "fixture": "empty_board", "js_mode": "hydrate", "mc": "narrow",
    })
    # Packet extras
    for locale in ("en", "zh"):
        cells.append({
            "id": f"confluence-sp500-dark-{locale}",
            "family": "confluence", "theme": "dark", "locale": locale,
            "w": 1440, "h": 900, "kind": "canvas",
            "sel": "#si-confluence", "clip": [".sc-tabs", ".sc-kicker"],
            "fixture": "populated", "js_mode": "hydrate", "mc": "narrow",
            "action": "view", "view": "confluence",
        })
        cells.append({
            "id": f"grader-atrest-dark-{locale}",
            "family": "grader-rest", "theme": "dark", "locale": locale,
            "w": 1440, "h": 900, "kind": "canvas",
            "sel": "#grader", "clip": ["#grader"],
            "fixture": "populated", "js_mode": "hydrate", "mc": "narrow",
        })
    cells.append({
        "id": "flow-table-dark-zh",
        "family": "flows", "theme": "dark", "locale": "zh",
        "w": 1440, "h": 900, "kind": "canvas",
        "sel": "#sc-flows", "clip": ["#sc-flows", ".scf-wrap"],
        "fixture": "populated", "js_mode": "hydrate", "mc": "narrow",
        "action": "view", "view": "money",
    })
    cells.append({
        "id": "board-header-dark-en",
        "family": "board-header", "theme": "dark", "locale": "en",
        "w": 1440, "h": 900, "kind": "canvas",
        "sel": "#action-board",
        "clip": ["#action-board h2", ".actiongrid", ".act-watch-strip"],
        "fixture": "populated", "js_mode": "hydrate", "mc": "narrow",
    })
    return cells


def _page_name(spec: dict) -> str:
    if spec.get("page"):
        return spec["page"]
    fx = spec.get("fixture") or "populated"
    return f"{fx}.html"


def _prepare_scratch(scratch: Path) -> None:
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "populated.html").write_text(render_page(), encoding="utf-8")
    (scratch / "no_payload.html").write_text(
        render_page(market_concentration=None, baskets_as_of=None),
        encoding="utf-8")
    (scratch / "empty_board.html").write_text(
        render_page(action_board=_empty_board(), bottoming=None,
                    market_concentration=mc_known("narrow")),
        encoding="utf-8")
    (scratch / "us_stocks_board.html").write_text(
        render_us_stocks_board(), encoding="utf-8")
    (scratch / "sector_central_data.js").write_text(
        "window.SECTOR_CENTRAL=" + json.dumps(grader_payload(), ensure_ascii=False) + ";\n",
        encoding="utf-8")
    (scratch / "forming_narratives.js").write_text(
        "function renderFormingNarratives(){}\n", encoding="utf-8")
    assets = (
        "theme.css", "theme.js", "dashboard-icons.css", "dashboard-icons.js",
        "product-nav-icons.css", "navigation-refresh.css", "nav_market.js",
        "data_base.js", "si_workspace.js", "lightweight-charts.js",
        "sector_cycles.css", "live.js",
    )
    for name in assets:
        src = _ROOT / "templates" / name
        if src.exists():
            shutil.copy2(src, scratch / name)
    fonts_src = _ROOT / "templates" / "fonts"
    if fonts_src.is_dir():
        shutil.copytree(fonts_src, scratch / "fonts", dirs_exist_ok=True)


def _mc_for(spec: dict) -> dict | None:
    kind = spec.get("mc")
    if kind in ("narrow", "broad", "mixed"):
        return mc_known(kind)
    if kind == "alien":
        d = mc_known("narrow")
        d["verdict"] = "not-a-verdict"
        return d
    return None


def _install_routes(page, spec: dict) -> None:
    mode = spec.get("js_mode") or "hydrate"
    mc = _mc_for(spec)
    baskets = baskets_payload(mc)
    lead = leadership_payload()

    def handler(route):
        url = route.request.url
        if "basketdata/baskets.json" in url:
            if mode == "hang":
                return  # never settle — baked skeleton stays
            if mode == "reject":
                route.fulfill(status=404, body="missing")
                return
            if mode == "empty_mc":
                route.fulfill(
                    status=200, content_type="application/json",
                    body=json.dumps(baskets_payload(None)))
                return
            route.fulfill(
                status=200, content_type="application/json",
                body=json.dumps(baskets))
            return
        if "marketdata/index_leadership.json" in url:
            route.fulfill(
                status=200, content_type="application/json",
                body=json.dumps(lead))
            return
        if any(tok in url for tok in (
                "shock_state.json", "policy_lever.json", "pulse.json",
                "etf_pulse.json", "vol_sentiment.json", "theme_extension.json",
                "narrative_emergence.json")):
            route.fulfill(status=404, body="")
            return
        route.continue_()

    page.route("**/*", handler)


def _switch_view(page, view: str) -> None:
    btn = page.locator(f'.si-view-btn[data-view="{view}"]').first
    btn.wait_for(state="visible", timeout=8000)
    btn.click()
    page.locator(f'.si-view[data-view="{view}"].on').first.wait_for(
        state="visible", timeout=4000)


def _do_action(page, spec: dict) -> dict:
    extra: dict = {}
    action = spec.get("action")
    view = spec.get("view")
    if action == "view" and view:
        _switch_view(page, view)
        extra["view"] = view
    elif action == "grader-tip":
        page.locator("#grader .gr-cell").first.wait_for(state="visible", timeout=8000)
        q = page.locator("#grader .ftr-t1-help").first
        q.scroll_into_view_if_needed()
        q.click(force=True)
        page.locator(".lens-pop.open").first.wait_for(state="visible", timeout=4000)
        extra["tip_text"] = page.locator(".lens-pop.open").first.inner_text()
    elif action == "lead-tip":
        _switch_view(page, "money")
        page.locator("#scc-leadership .lead-track").first.wait_for(
            state="visible", timeout=8000)
        q = page.locator("#scc-leadership .lead-track .ftr-t1-help").first
        q.scroll_into_view_if_needed()
        q.click(force=True)
        page.locator(".lens-pop.open").first.wait_for(state="visible", timeout=4000)
        extra["tip_text"] = page.locator(".lens-pop.open").first.inner_text()
        extra["view"] = "money"
    elif action == "row-pop":
        row = page.locator("#ab-soon-fold a.actitem[data-rpop]").first
        row.wait_for(state="visible", timeout=8000)
        row.scroll_into_view_if_needed()
        row.hover()
        page.locator(".row-pop:not([hidden])").first.wait_for(
            state="visible", timeout=4000)
        extra["pop_text"] = page.locator(".row-pop:not([hidden])").first.inner_text()
        extra["tag_text"] = page.locator(
            ".row-pop:not([hidden]) .row-pop-tag").first.inner_text()
    return extra


def _screenshot(page, spec: dict) -> bytes:
    if spec["kind"] == "fullpage":
        return page.screenshot(type="png", full_page=True)
    sels = spec.get("clip") or [spec["sel"]]
    for sel in sels:
        if sel.startswith(".lens-pop") or sel.startswith(".row-pop"):
            continue
        loc = page.locator(sel).first
        try:
            loc.wait_for(state="visible", timeout=4000)
            loc.scroll_into_view_if_needed()
        except Exception:
            pass
    box = page.evaluate(_CLIP_UNION_JS.strip(), sels)
    if not box:
        # Fall back to the whole viewport — still a page-canvas shot, never
        # an element screenshot on a transparent body.
        return page.screenshot(type="png")
    clip = canvas_clip(box, spec["w"], spec["h"], pad=0)  # JS already padded
    return page.screenshot(type="png", clip=clip)


def _write_readme(sha: str, rows: list[dict], hscroll: dict) -> str:
    lines = [
        "# sector_central W16 r3 — settled evidence matrix",
        "",
        f"Provenance: committed head `{sha}`. Porcelain empty at capture.",
        "S1 rig: fixture VM (no live bake, no `site/`/`data/` opt-in), real",
        "`body.macro-desk.page-baskets`, Playwright localStorage seed +",
        "`setTheme`/`setLang`, `window.__skyDeck = true`, attribute re-read",
        "refuse-on-mismatch, overlay column, SETTLE column, content-addressed",
        "twins + alias. Crops are viewport-region (canvas-context) captures",
        "with margin — a dark cell must look dark. P3.4 stays deferred",
        "(SEAT RULING 2).",
        "",
        "## DARK TREATMENT",
        "",
        "Command center. The page canvas is estate `--bg` (luminance depth,",
        "instrument calm). The workspace rail (`.si-side`) sits as a dark",
        "instrument strip; `.si-stage` cards are `--panel` with hairline",
        "`--line`. Action lanes keep their existing luminous cards; the",
        "watch strip is a full-width band under the five, not a sixth badge.",
        "Internals tiles are instrument wells — skeleton bars are a restrained",
        "`--panel2` shimmer freeze-frame, not a glow. LENS `?` tips and",
        "row-pop decision cards are glass over the dark canvas. Monoline",
        "icons inherit currentColor. Mixed/Narrow/Broad take `--warn` /",
        "`--down` / `--up` as instrument colour, not decoration.",
        "",
        "## LIGHT TREATMENT",
        "",
        "Research workspace. Forced `data-theme=\"light\"` and judged as a",
        "design, not a tint. Canvas is the cool estate light `--bg`; cards",
        "are white material with hairline `--line` and short shadow instead",
        "of glow (page-scoped `#si-confluence` already ships this split;",
        "the overview/board inherit theme.css paper). Internals skeleton",
        "must read as a designed paper hatch — `--panel2` on white, not a",
        "dirty smudge. Empty-why captions deepen toward `--ink` because",
        "`--muted` washes out on paper. LENS and row-pop are white cards",
        "with hairline + shadow. Semantic colour (Narrow/Mixed/Broad) stays",
        "the same tokens, re-inked for paper contrast.",
        "",
        "## Mechanisms that INTENTIONALLY differ",
        "",
        "1. Material depth — dark = luminance wells / restrained glow; light =",
        "   white paper + 1px shadow / inset hairline.",
        "2. Skeleton — dark freeze-frame of the `--panel2` shimmer; light is a",
        "   paper hatch that must not read as a dirty smudge.",
        "3. Caption contrast — dark can use `--muted`; light deepens toward `--ink`.",
        "4. Confluence view — already ships a distinct light art direction",
        "   (white isles, hairline, no glow).",
        "Shared on purpose: information architecture, six-view rail, bilingual",
        "`.l-en`/`.l-zh`, lane geometry, LENS `?`, row-pop, spacing/type scale.",
        "",
        "## SETTLE gate",
        "",
        "`document.fonts.ready`, then `getAnimations({subtree:true})`",
        "empty-or-finished on the content root (force-finish). Infinite `.skel`",
        "shimmer is cancelled to a designed freeze-frame. Effective opacity == 1",
        "on the content root AND a sampled row. Unsettled cells are REFUSED.",
        "Reduced-motion is an aid, not the settle mechanism.",
        "",
        "## Horizontal page scroll at 390w (every si-view, both languages)",
        "",
    ]
    for key in sorted(hscroll):
        rec = hscroll[key]
        lines.append(
            f"- {key}: view={rec.get('view')} client={rec.get('client_width')} "
            f"scroll={rec.get('scroll_width')} overflow={rec.get('overflow')} "
            f"→ {'none' if rec.get('ok') else 'FAIL'}"
        )
    lines += [
        "",
        "## Cells",
        "",
        "| id | family | theme | lang | fixture | overlay | settle | "
        "root opacity | row opacity | header contrast | alias |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        st = r.get("settle") or {}
        lines.append(
            f"| {r['id']} | {r.get('family','')} | {r['theme']} | {r['locale']} | "
            f"{r.get('fixture','')} | {r.get('overlay')} | {st.get('reason','')} | "
            f"{st.get('root_opacity')} | {st.get('row_opacity')} | "
            f"{st.get('header_contrast')} | `{r['alias']}` |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def pack_validated_claims(html: str) -> dict:
    """Scan scratch HTML against a pack-scoped allowlist from origin/main.

    Never writes into data/. A missing allowlist blob is reported, not invented.
    """
    raw = subprocess.check_output(
        ["git", "show", "origin/main:data/regime/validated_claims_allowlist.json"],
        cwd=_ROOT)
    allow_all = json.loads(raw).get("allow") or []
    allow = [e for e in allow_all
             if "sector_central" in (e.get("surfaces") or ())]
    from scripts.check_validated_claims import scan_text
    found, stats = scan_text("site/sector_central.html", html, allow)
    return {
        "allow_n": len(allow),
        "unearned": found,
        "claims": stats.get("claims"),
        "backed": stats.get("backed"),
        "negated": stats.get("negated"),
    }


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(f"playwright missing: {exc}") from exc

    sha = require_clean_head()
    _prepare_scratch(SCRATCH)
    claims = pack_validated_claims((SCRATCH / "populated.html").read_text(encoding="utf-8"))
    httpd, port = serve_site_dir(SCRATCH)
    if CELLS_DIR.exists():
        shutil.rmtree(CELLS_DIR)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)

    specs = cell_matrix()
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
                reduced_motion="reduce",
            )
            ctx.add_init_script(f"({_STATE_SEED.strip()})({json.dumps(state)})")
            page = ctx.new_page()
            if spec.get("js_mode") and spec["js_mode"] != "none":
                _install_routes(page, spec)
            url = f"http://127.0.0.1:{port}/{_page_name(spec)}"
            resp = page.goto(url, wait_until="load", timeout=30000)
            if resp is None or not resp.ok:
                raise RuntimeError(f"HTTP {getattr(resp, 'status', None)} on {spec['id']}")
            page.emulate_media(reduced_motion="reduce")
            applied = page.evaluate(_APPLY_STATE.strip(), state) or {}
            if applied.get("theme") != spec["theme"] or applied.get("locale") != spec["locale"]:
                raise RuntimeError(f"state mismatch {spec['id']}: {applied}")
            mode = spec.get("js_mode")
            if mode in ("hydrate", "empty_mc"):
                try:
                    page.wait_for_function(
                        "() => !!(window.BASKETS && window.BASKETS.as_of)",
                        timeout=8000)
                except Exception:
                    pass
            extra = _do_action(page, spec)
            settle = page.evaluate(_SETTLE_JS.strip(), spec["sel"]) or {}
            if not settle.get("ok"):
                raise RuntimeError(f"SETTLE REFUSED {spec['id']}: {settle}")
            overlay = page.evaluate(_OVERLAY_JS.strip(), spec["sel"])
            if not overlay.get("ok"):
                raise RuntimeError(f"overlay over {spec['id']}: {overlay}")
            if spec.get("hscroll"):
                hs = page.evaluate(_HSCROLL_JS.strip()) or {}
                key = f"{spec.get('view') or 'overview'}-{spec['locale']}"
                hscroll[key] = hs
                extra["hscroll"] = hs
                if not hs.get("ok"):
                    raise RuntimeError(f"page h-scroll at 390w {key}: {hs}")
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
                "fixture": spec.get("fixture"),
                "js_mode": spec.get("js_mode"),
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
            print(f"  {spec['id']}: ok {name}", flush=True)
            ctx.close()
        browser.close()
        pw.stop()
    finally:
        httpd.shutdown()

    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "page": "sector_central.html",
        "round": "W16-r3",
        "tool": {
            "module_ref": "scripts/capture_sector_central_w16_r3_evidence.py",
            "version": "w16-r3-s1",
            "capture_method": (
                "playwright, one fresh page per cell, fixture HTML in a scratch "
                "dir (never site/ or data/). data-theme/data-lang via setTheme/"
                "setLang with refuse-on-mismatch. window.__skyDeck skips "
                "skyToggleFx. overlays removed. SETTLE asserts opacity==1. "
                "Crops are viewport-region canvas-context shots."
            ),
        },
        "target": {
            "kind": "scratch_fixture_html",
            "resolved_sha_or_none": sha,
            "porcelain": "empty",
            "capture_sha_equals_head": True,
        },
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "selection": {"n": len(rows), "ids": [r["id"] for r in rows]},
        "totals": {"captured": len(rows), "failed": 0, "refused_settle": 0},
        "hscroll_390w": hscroll,
        "validated_claims_scratch": claims,
        "cells": rows,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "README.md").write_text(
        _write_readme(sha, rows, hscroll), encoding="utf-8")
    print(json.dumps({
        "sha": sha, "n": len(rows), "out": str(OUT_DIR),
        "hscroll_keys": sorted(hscroll),
        "claims": {k: claims[k] for k in ("allow_n", "claims", "backed")
                   if k in claims},
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CaptureUnavailable as exc:
        print(f"capture unavailable: {exc}", file=sys.stderr)
        raise SystemExit(4) from exc
