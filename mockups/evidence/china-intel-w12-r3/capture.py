#!/usr/bin/env python3
"""S1-rig canvas-true evidence matrix for china_intel W12 r3.

Closing-round capture. r1+r2 code is frozen; this file is the rig.

Laws this round:
  * Canvas-context crops — viewport REGIONS (element box + generous page
    margin) via page.screenshot(clip=), never locator.screenshot() on a
    transparent body. A "dark" cell must show the dark canvas.
  * Settle-before-capture (W13): document.fonts.ready, then
    getAnimations({subtree:true}) empty/force-finished on the content root.
    Per-crop SETTLE column asserts computed effective opacity == 1 on the
    content root + a sampled row. Unsettled cells are REFUSED.
  * F3 regime cells use the TILTED fixture (risk_tilt: 1). Neutral is its
    own labeled cell (untinted is honest, not a defect).
  * Capture AFTER the rig commit, on a clean tree. Manifest sha is
    git rev-parse HEAD at capture time.

Usage::

    python3 mockups/evidence/china-intel-w12-r3/capture.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import china_intel_bus as bus
from scripts.capture_page_evidence import serve_site_dir
from tests.test_china_intel_w12_r1 import _b, _cmd, _render, _row, _today
from tests.test_china_intel_w12_r2 import _asof, _feed, _stamp

OUT = Path(__file__).resolve().parent
CELLS = OUT / "cells"

OVERLAY_SELECTORS = (
    ".ift-aurora", ".mx5-aurora", ".sky-fx", "#mmb-root", "#mmb-boot",
)
CANVAS_MARGIN = 72
ASSETS = (
    "theme.css", "theme.js", "product-nav-icons.css", "navigation-refresh.css",
)
LONG_NAME = "中信证券股份有限公司投资银行部研究中心"

_HIDE = """
() => {
  window.__skyDeck = true;
  const sels = %s;
  sels.forEach((s) => document.querySelectorAll(s).forEach((n) => n.remove()));
  return true;
}
""" % (json.dumps(list(OVERLAY_SELECTORS)),)

_SETTLE = """
async (args) => {
  const rootSel = args.rootSel || 'body';
  const sampleSel = args.sampleSel || '';
  if (document.fonts && document.fonts.ready) {
    try { await document.fonts.ready; } catch (e) {}
  }
  const root = document.querySelector(rootSel) || document.body;
  const finish = (node) => {
    const list = (node.getAnimations ? node.getAnimations({subtree: true}) : []) || [];
    for (const a of list) {
      try { a.finish(); } catch (e) {
        try { a.cancel(); } catch (e2) {}
      }
    }
    return list.length;
  };
  finish(root);
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  finish(root);
  await new Promise((r) => requestAnimationFrame(r));
  const running = ((root.getAnimations ? root.getAnimations({subtree: true}) : []) || [])
    .filter((a) => a.playState === 'running' || a.playState === 'pending');
  const effectiveOpacity = (el) => {
    let o = 1;
    let n = el;
    while (n && n.nodeType === 1) {
      const st = getComputedStyle(n);
      const op = Number(st.opacity);
      if (Number.isFinite(op)) o *= op;
      if (st.visibility === 'hidden' || st.display === 'none') o = 0;
      n = n.parentElement;
    }
    return o;
  };
  const sample = (sampleSel && document.querySelector(sampleSel))
    || root.querySelector('h1, h2.sec, .cmd-tbl tbody tr, .pp-card, .ci-stance, .mc, .cmd-name')
    || root;
  const rootOp = effectiveOpacity(root);
  const sampleOp = effectiveOpacity(sample);
  const ok = running.length === 0 && rootOp >= 0.999 && sampleOp >= 0.999;
  return {
    ok,
    fonts_ready: true,
    running_animations: running.length,
    content_root_opacity: rootOp,
    sample_opacity: sampleOp,
    sample_tag: sample && sample.tagName ? sample.tagName : '',
    refused: ok ? false : true,
  };
}
"""

_OVERLAY = """
(sel) => {
  const el = sel ? document.querySelector(sel) : document.body;
  if (!el) return {ok: false, reason: 'missing-subject', hits: ['missing-subject']};
  const r = el.getBoundingClientRect();
  const hits = [];
  const sels = %s;
  sels.forEach((cls) => {
    document.querySelectorAll(cls).forEach((n) => {
      const b = n.getBoundingClientRect();
      const overlap = !(b.right < r.left || b.left > r.right || b.bottom < r.top || b.top > r.bottom);
      const st = getComputedStyle(n);
      if (overlap && st.display !== 'none' && st.visibility !== 'hidden' && Number(st.opacity) > 0.05) {
        hits.push(cls);
      }
    });
  });
  return {ok: hits.length === 0, hits};
}
""" % (json.dumps(list(OVERLAY_SELECTORS)),)

_HSCROLL = """
() => {
  const de = document.documentElement;
  const se = document.scrollingElement || de;
  const client = de.clientWidth || window.innerWidth;
  const scroll = se.scrollWidth || de.scrollWidth;
  return {
    clientWidth: client,
    scrollWidth: scroll,
    innerWidth: window.innerWidth,
    overflow: scroll > client + 1,
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


def _head_sha() -> str:
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    ).strip()
    if dirty:
        raise SystemExit(f"capture refused: dirty tree\n{dirty}")
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _cmd_long(n: int):
    cmd = _cmd(n)
    cmd["command"][0] = _row(0)
    cmd["command"][0]["name"] = LONG_NAME
    cmd["command"][0]["ticker"] = "600030.SS"
    return cmd


def _dated_bits():
    today = str(_today())
    return dict(
        policy_phrase=_feed(today, n_events_recent=0, recent_events=[],
                            cold_start_organs=[]),
        narrative_divergence=_feed(today, divergence_z=0.2, risk_flag=False,
                                   trend_5d="flat"),
        analysis=_feed(today,
                       conviction=[{
                           "sector_en": "Brokers", "sector_zh": "券商",
                           "radar_sign": "positive", "opportunity_score": 50,
                           "stage": "early", "context_conviction": 40,
                           "edge_remaining": 0.4,
                           "conviction_band": ["Moderate", "中等"],
                           "surfaces_confirming": ["radar"],
                           "rationale_en": "Radar leads.",
                           "rationale_zh": "雷达领先。",
                       }],
                       flagged_tickers=[{
                           "ticker": "600030.SS", "name": "中信证券",
                           "side": "long-context", "surfaces": ["radar"],
                       }],
                       chains=[{"band": "forming", "label_en": "Easing chain",
                                "label_zh": "宽松链条", "k": 1, "n": 3,
                                "links": []}]),
        conviction=[{
            "sector_en": "Brokers", "sector_zh": "券商",
            "radar_sign": "positive", "opportunity_score": 50,
            "stage": "early", "context_conviction": 40,
            "edge_remaining": 0.4,
            "conviction_band": ["Moderate", "中等"],
            "surfaces_confirming": ["radar"],
            "rationale_en": "Radar leads.",
            "rationale_zh": "雷达领先。",
        }],
        flagged_tickers=[{
            "ticker": "600030.SS", "name": "中信证券",
            "side": "long-context", "surfaces": ["radar"],
        }],
    )


def _analogs():
    return {
        "query": {"quad": "Q2", "quad_name": "Bull", "liquidity": "easing",
                  "cycle": "mid"},
        "fan": {"h20": {"p25": 0.01, "median": 0.03, "p75": 0.06, "n": 12}},
        "analogs": [{"date": "2015-06-01", "quad": "Q2",
                     "fwd_shcomp": {"h20": 0.04}}],
        "n_analogs": 1,
        "disclaimer_en": "Context only. Historical analogs are descriptive.",
        "disclaimer_zh": "仅供展示。历史类比为描述性分布。",
    }


def _salience():
    return [{
        "kind": "news", "label_en": "Media tone", "label_zh": "媒体语气",
        "detail_en": "Media tone is unusually negative over 90 days.",
        "detail_zh": "近90日媒体语气明显偏消极。",
    }]


def _policy_preds(missing_zh: bool = True):
    preds = [{"en": "Hold the 1-year loan rate.", "zh": "维持一年期贷款利率"}]
    if missing_zh:
        preds.append({"en": "Keep the reserve-requirement ratio on hold.",
                      "zh": "暂无中文摘要"})
    return preds


def _html(kind: str) -> str:
    today = str(_today())
    cmd = _cmd_long(9)
    if kind == "b1-fresh":
        b = _stamp(_b(
            news=_feed(_asof(0)), policy=_feed(_asof(1)), radar=_feed(_asof(2)),
            regime={"roro": 0.0, "risk_tilt": 0, "band_en": "Neutral",
                    "band_zh": "中性"},
        ))
        return _render(b, cmd_full=_cmd(2))
    if kind == "b1-mixed":
        b = _stamp(_b(
            news=_feed(_asof(0), band="steady"),
            policy=_feed(_asof(70), pboc_stance="neutral"),
            radar=_feed(_asof(1)),
            regime={"roro": 0.4, "risk_tilt": 1, "band_en": "Greed",
                    "band_zh": "贪婪"},
        ))
        return _render(b, cmd_full=_cmd(2))
    if kind == "b1-all_stale":
        b = _stamp(_b(
            news=_feed(_asof(70)),
            policy=_feed(_asof(40)),
            altdata=_feed(_asof(30)),
            regime={"roro": 0.4, "risk_tilt": 1, "band_en": "Greed",
                    "band_zh": "贪婪"},
        ))
        return _render(b, cmd_full=_cmd(2))
    if kind == "b1-outage":
        b = _stamp(_b(
            news={"band": "steady"},
            policy={"pboc_stance": "neutral"},
            radar={},
            regime={"roro": 0.0, "risk_tilt": 0, "band_en": "Neutral",
                    "band_zh": "中性"},
        ))
        return _render(b, cmd_full=_cmd(2))
    if kind == "b1-undated":
        b = _stamp(_b(
            news={"band": "steady"},
            policy=_feed(_asof(70), pboc_stance="neutral"),
            regime={"roro": 0.4, "risk_tilt": 1, "band_en": "Greed",
                    "band_zh": "贪婪"},
        ))
        return _render(b, cmd_full=_cmd(2))
    if kind == "regime-tilted":
        b = _stamp(_b(
            news=_feed(today, band="steady"),
            policy=_feed(today, pboc_stance="neutral"),
            radar=_feed(today),
            regime={"roro": 0.4, "risk_tilt": 1, "band_en": "Greed",
                    "band_zh": "贪婪"},
        ))
        return _render(b, cmd_full=_cmd(2))
    if kind == "regime-neutral":
        b = _stamp(_b(
            news=_feed(today, band="steady"),
            policy=_feed(today, pboc_stance="neutral"),
            radar=_feed(today),
            regime={"roro": 0.0, "risk_tilt": 0, "band_en": "Neutral",
                    "band_zh": "中性"},
        ))
        return _render(b, cmd_full=_cmd(2))
    if kind == "foldin":
        b = _stamp(_b(
            news=_feed(today, band="steady"),
            policy=_feed(today, pboc_stance="neutral",
                         predictions=_policy_preds()),
            radar=_feed(today),
            analysis={"chains": [{"band": "forming",
                                  "label_en": "Easing chain",
                                  "label_zh": "宽松链条", "k": 1, "n": 3,
                                  "links": []}]},
            salience=_salience(),
            regime={"roro": 0.4, "risk_tilt": 1, "band_en": "Greed",
                    "band_zh": "贪婪"},
        ))
        return _render(b, cmd_full=_cmd(2))
    if kind == "degraded":
        why = bus._degraded_why("brain_timeout")
        b = _stamp(_b(
            news=_feed(today, band="steady"),
            policy=_feed(today, pboc_stance="neutral"),
            radar=_feed(today),
            analysis={"llm_synthesis": None,
                      "llm_synthesis_degraded_reason": "brain_timeout"},
            llm_synthesis_degraded_why=why,
            salience=_salience(),
            regime={"roro": 0.4, "risk_tilt": 1, "band_en": "Greed",
                    "band_zh": "贪婪"},
        ))
        return _render(b, cmd_full=_cmd(2))
    # baseline / f8 / method — rich mixed page
    # mixed chip: oldest is policy_phrase at 70d, working news/radar
    b = _stamp(_b(
        news=_feed(today, band="steady", band_label_en="Steady",
                   band_label_zh="平稳"),
        policy=_feed(today, pboc_stance="neutral",
                     stance_label_en="Neutral", stance_label_zh="中性",
                     predictions=_policy_preds()),
        radar=_feed(_asof(1)),
        policy_phrase=_feed(_asof(70), n_events_recent=0, recent_events=[],
                            cold_start_organs=[]),
        narrative_divergence=_feed(today, divergence_z=0.2, risk_flag=False,
                                   trend_5d="flat"),
        analysis=_feed(today,
                       conviction=_dated_bits()["conviction"],
                       flagged_tickers=_dated_bits()["flagged_tickers"],
                       chains=_dated_bits()["analysis"]["chains"]),
        conviction=_dated_bits()["conviction"],
        flagged_tickers=_dated_bits()["flagged_tickers"],
        salience=_salience(),
        analogs=_analogs(),
        regime={"roro": 0.4, "risk_tilt": 1, "band_en": "Greed",
                "band_zh": "贪婪"},
        surfaces_present=["news", "policy", "radar", "policy_phrase"],
    ))
    return _render(b, cmd_full=cmd)


def _prepare(scratch: Path) -> None:
    scratch.mkdir(parents=True, exist_ok=True)
    kinds = (
        "baseline", "b1-fresh", "b1-mixed", "b1-all_stale", "b1-outage",
        "b1-undated", "regime-tilted", "regime-neutral", "foldin", "degraded",
    )
    for kind in kinds:
        (scratch / f"{kind}.html").write_text(_html(kind), encoding="utf-8")
    for name in ASSETS:
        src = ROOT / "templates" / name
        if src.exists():
            shutil.copy2(src, scratch / name)


def _apply(page, theme: str, locale: str) -> dict:
    page.evaluate(
        """(state) => {
          window.__skyDeck = true;
          try {
            localStorage.setItem('theme', state.theme);
            localStorage.removeItem('themeAuto');
            localStorage.setItem('lang', state.locale);
          } catch (e) {}
          const docEl = document.documentElement;
          if (typeof window.setTheme === 'function') window.setTheme(state.theme);
          else docEl.setAttribute('data-theme', state.theme);
          if (typeof window.setLang === 'function') window.setLang(state.locale);
          else {
            docEl.setAttribute('data-lang', state.locale);
            if (state.locale) docEl.lang = state.locale;
          }
          return {theme: docEl.getAttribute('data-theme'),
                  locale: docEl.getAttribute('data-lang')};
        }""",
        {"theme": theme, "locale": locale},
    )
    observed = page.evaluate(
        "() => ({theme: document.documentElement.getAttribute('data-theme'),"
        " locale: document.documentElement.getAttribute('data-lang')})"
    )
    if observed["theme"] != theme or (observed["locale"] or "en") != locale:
        raise SystemExit(f"state mismatch: wanted {theme}/{locale} got {observed}")
    page.evaluate(_HIDE)
    body = page.evaluate(
        """() => ({
          bg: getComputedStyle(document.body).backgroundColor,
          classes: document.body.className || '',
        })"""
    )
    if not body.get("bg") or body["bg"] in ("rgba(0, 0, 0, 0)", "transparent"):
        raise SystemExit(f"canvas refused: body background {body.get('bg')!r}")
    return {"applied": observed, "body": body}


def _settle(page, root_sel: str, sample_sel: str = "") -> dict:
    rec = page.evaluate(_SETTLE, {"rootSel": root_sel, "sampleSel": sample_sel})
    if not rec or not rec.get("ok"):
        raise SystemExit(f"SETTLE refused {root_sel}: {rec}")
    rec["column"] = "settled"
    return rec


def _loc(page, sel: str, nth: int = 0):
    loc = page.locator(sel).nth(nth)
    loc.wait_for(state="visible", timeout=8000)
    return loc


def _canvas_clip(page, sels: list[str], nth: int = 0) -> dict:
    """Viewport region covering the subject(s) plus generous page canvas."""
    vp = page.viewport_size
    boxes = []
    for i, sel in enumerate(sels):
        loc = _loc(page, sel, nth if i == 0 else 0)
        loc.scroll_into_view_if_needed()
        box = loc.bounding_box()
        if not box:
            raise SystemExit(f"no box for {sel}")
        boxes.append(box)
    x0 = min(b["x"] for b in boxes) - CANVAS_MARGIN
    y0 = min(b["y"] for b in boxes) - CANVAS_MARGIN
    x1 = max(b["x"] + b["width"] for b in boxes) + CANVAS_MARGIN
    y1 = max(b["y"] + b["height"] for b in boxes) + CANVAS_MARGIN
    x = max(0, x0)
    y = max(0, y0)
    r = min(vp["width"], x1)
    btm = min(vp["height"], y1)
    w = max(1, r - x)
    h = max(1, btm - y)
    return {
        "x": int(round(x)), "y": int(round(y)),
        "width": int(round(w)), "height": int(round(h)),
        "kind": "viewport-region", "margin": CANVAS_MARGIN,
    }


def _open_tip(page, sel: str, nth: int = 0) -> None:
    loc = _loc(page, sel, nth)
    loc.scroll_into_view_if_needed()
    loc.hover(force=True)
    page.wait_for_selector(".lens-pop.open", timeout=4000)
    page.wait_for_timeout(220)


def _close_tip(page) -> None:
    page.keyboard.press("Escape")
    page.mouse.move(0, 0)


def _cells() -> list[dict]:
    """Matrix. Order is fixture-grouped so the runner can reuse a page."""
    cells: list[dict] = []

    def add(**kw):
        cells.append(kw)

    # 8 full-page baselines
    for theme in ("dark", "light"):
        for loc in ("en", "zh"):
            for w, h, vp in ((1440, 900, "desktop"), (390, 844, "mobile")):
                add(id=f"fp-{theme}-{loc}-{w}", fixture="baseline",
                    theme=theme, locale=loc, w=w, h=h, vp=vp,
                    sel=None, full=True, tip=None,
                    sample=".ci-wrap", root="body",
                    judged=("full-page baseline — lead brief above fold, "
                            "B1 chip + as-of, command 8+expander, stances"))

    # B1 five states, both lanes, both themes (copy + visual).
    # state-2 / state-4 union the hero as-of stamp so the chip-beside-stamp
    # frame is in the crop, not only on fp-* / state-1 cells.
    stamp = [".ci-hero .dtp"]
    b1 = (
        ("b1-state1", "b1-fresh", ".cmdbar",
         "state-1 suppressed — labeled absence: cmdbar without the chip",
         []),
        ("b1-state2", "b1-mixed", ".cmdbar .mc.warn",
         "state-2 mixed — names a still-current feed; chip beside as-of stamp",
         stamp),
        ("b1-state3", "b1-all_stale", ".cmdbar .mc.warn",
         "state-3 all-stale — no feed is current",
         []),
        ("b1-state4", "b1-outage", ".cmdbar .mc.warn",
         "state-4 outage — timestamps unavailable, never suppressed; chip beside as-of stamp",
         stamp),
        ("b1-state5", "b1-undated", ".cmdbar .mc.warn",
         "state-5 undated-among — dated oldest + undated named; clause-split",
         []),
    )
    for cid, fx, sel, judged, extra in b1:
        for theme in ("dark", "light"):
            for loc in ("en", "zh"):
                add(id=f"{cid}-{theme}-{loc}", fixture=fx, theme=theme,
                    locale=loc, w=1440, h=900, vp="desktop", sel=sel,
                    extra=extra,
                    full=False, tip=None, sample=".cmdbar", root=".ci-wrap",
                    judged=judged)

    # Regime: tilt is word + signed number + link-tinted ring.
    # Hex is computed-style only on b.on; visible-ink hex parked per packet D8.
    for loc, judged in (
        ("en", "F3 tilted EN — word (Risk-on) + signed number + link-tinted ring; hex is computed-style only; visible-ink hex parked per packet D8"),
        ("zh", "F3 tilted ZH — word (偏好风险) + signed number + link-tinted ring; lane-symmetric; hex is computed-style only; visible-ink hex parked per packet D8"),
    ):
        for theme in ("dark", "light"):
            add(id=f"regime-tilted-{theme}-{loc}", fixture="regime-tilted",
                theme=theme, locale=loc, w=1440, h=900, vp="desktop",
                sel=".cmdbar .regime", full=False, tip=None,
                sample=".cmdbar .regime", root=".ci-wrap",
                judged=judged, colour=True)
    for theme in ("dark", "light"):
        for loc in ("en", "zh"):
            add(id=f"regime-neutral-{theme}-{loc}", fixture="regime-neutral",
                theme=theme, locale=loc, w=1440, h=900, vp="desktop",
                sel=".cmdbar .regime", full=False, tip=None,
                sample=".cmdbar .regime", root=".ci-wrap",
                judged="Neutral tilt — untinted is the honest neutral, not a defect")

    # Dated brief card (as-of + source chip)
    for theme in ("dark", "light"):
        for loc in ("en", "zh"):
            add(id=f"brief-card-{theme}-{loc}", fixture="baseline",
                theme=theme, locale=loc, w=1440, h=900, vp="desktop",
                sel="section[data-l1='dated-cards'] .pp-card",
                full=False, tip=None, sample=".pp-card", root=".ci-wrap",
                judged="Dated brief card with as-of + source chip")

    # Lead-brief fold-in (no-asof)
    for theme in ("dark", "light"):
        for loc in ("en", "zh"):
            add(id=f"foldin-{theme}-{loc}", fixture="foldin",
                theme=theme, locale=loc, w=1440, h=900, vp="desktop",
                sel="section[data-l1='lead-brief'] .pp-card",
                full=False, tip=None, sample=".pp-card", root=".ci-wrap",
                judged="No-asof fold-in — 'kept on the lead brief' line")

    # Degraded-AI why (theme-specific degraded, both lanes)
    for theme in ("dark", "light"):
        for loc in ("en", "zh"):
            add(id=f"degraded-{theme}-{loc}", fixture="degraded",
                theme=theme, locale=loc, w=1440, h=900, vp="desktop",
                sel=".ci-syn-deg", full=False, tip=None,
                sample=".ci-syn-deg", root=".ci-wrap",
                judged="Degraded-AI why — enum→words, never the enum")

    # F8 full-name tip OPEN on truncated name
    for theme in ("dark", "light"):
        for loc in ("en", "zh"):
            add(id=f"f8-tip-{theme}-{loc}", fixture="baseline",
                theme=theme, locale=loc, w=1440, h=900, vp="desktop",
                sel=".cmd-tbl .cmd-name", full=False,
                tip=".cmd-tbl .cmd-name",
                extra=[".lens-pop.open"],
                sample=".cmd-name", root=".ci-wrap",
                judged="F8 full-name tip OPEN on a truncated name")

    # F11 ZH row 「暂无中文摘要」 with EN tip OPEN
    for theme in ("dark", "light"):
        add(id=f"f11-zh-tip-{theme}", fixture="baseline",
            theme=theme, locale="zh", w=1440, h=900, vp="desktop",
            sel="section[data-l1='lead-brief'] .sx[data-tip-en]",
            nth=1,
            full=False, tip="section[data-l1='lead-brief'] .sx[data-tip-en]",
            extra=[".lens-pop.open"],
            sample=".sx", root=".ci-wrap",
            judged="F11 ZH 「暂无中文摘要」 with the EN tip OPEN")

    # Method band post-F9 (no Ignore) + analogs (Watch/Ignore as shipped)
    for theme in ("dark", "light"):
        for loc in ("en", "zh"):
            add(id=f"method-band-{theme}-{loc}", fixture="baseline",
                theme=theme, locale=loc, w=1440, h=900, vp="desktop",
                sel="section[data-l1='method-band']", full=False, tip=None,
                sample="section[data-l1='method-band']", root=".ci-wrap",
                judged="Method band post-F9 — no Ignore stance")
            add(id=f"analogs-{theme}-{loc}", fixture="baseline",
                theme=theme, locale=loc, w=1440, h=900, vp="desktop",
                sel="section[data-l1='analogs']", full=False, tip=None,
                sample="section[data-l1='analogs'] .ci-stance",
                root=".ci-wrap",
                judged="Analogs L1 stance as shipped (Ignore); sibling L1 panels keep Watch; method-band has none")

    return cells


def _write_readme(sha: str, rows: list[dict], hscroll: dict) -> None:
    lines = [
        "# china_intel W12 r3 — canvas-true evidence matrix",
        "",
        f"Provenance: captured at committed head `{sha}`.",
        "Manifest `sha` == `git rev-parse HEAD` at capture time (porcelain-empty).",
        "",
        "S1 rig: real `report_base` page (body `{ background: var(--bg) }`, nav family,",
        "`window.__skyDeck = true`), Playwright `setTheme`/`setLang` (mismatch refuses),",
        "overlay selectors removed, reduced-motion, **canvas-context viewport regions**",
        "(element box + 72px page margin — never a bare-element screenshot on a",
        "transparent body), settle-before-capture (`document.fonts.ready` then",
        "`getAnimations({subtree:true})` force-finished; SETTLE column asserts",
        "effective opacity == 1 on the content root and a sampled row; unsettled",
        "cells REFUSED). Content-addressed twins (`sha256[:16].png` + alias).",
        "Fixture-rendered (sparse tree: no `data/` / `site/`).",
        "",
        "## Art direction",
        "",
        "**DARK TREATMENT:** command center — graphite panels, instrument-calm chips,",
        "restrained amber on the staleness/outage chip, luminance depth on dated",
        "brief cards and the method band. Regime tilt is carried by the WORD",
        "(Risk-on vs Neutral), the SIGNED NUMBER (+0.40 vs +0.00), and a",
        "link-tinted ring on `.mc.hot`. Hex on `b.on` is computed-style only;",
        "visible-ink hex parked per packet D8.",
        "",
        "**LIGHT TREATMENT:** research workspace — cool canvas, white card material,",
        "hairline borders, shadow instead of glow; same IA, chip states, dates,",
        "source chips, and the same word + signed-number + ring tilt. Warn bloom",
        "is suppressed; ink + hairline carry the stale/outage state. Hex remains",
        "computed-style only; visible-ink hex parked per packet D8.",
        "",
        "**Intentional differences:** glow vs shadow; warn bloom vs ink hairline.",
        "Shared: five-state B1 chip, dated-card identity (as-of + source chip),",
        "method-band directory, regime tilt (word + signed number + ring;",
        "ZH-flipped computed-style hex parked per D8).",
        "",
        "Theme-specific degraded states are captured in BOTH themes",
        "(`degraded-dark-*` / `degraded-light-*`).",
        "",
        "## Visible-ink follow-up (F3) — root cause",
        "",
        "r3 named `.cmdbar .mc span { color: var(--muted) }` as outranking",
        "`.regime .on` on `<b class=\"on\">`. That host match is false (`<b>` is",
        "not a `span`; `.cmdbar .mc:not(.regime) b` is excluded by `.regime`).",
        "",
        "Cascade probe (getComputedStyle + CDP `CSS.getMatchedStylesForNode`",
        "on the regime-tilted fixture, dark EN):",
        "- `b.on` computes `rgb(31, 154, 85)` via `.regime .on` (the computed-style",
        "  gate is true of the host).",
        "- Glyphs live in the inner `t()` spans (`span.l-en` / `span.l-zh`). The",
        "  only matched color rule on those spans is `.cmdbar .mc span { color:",
        "  var(--muted) }` → `rgb(139, 147, 161)` (`--muted` `#8b93a1`). Inherited",
        "  `.regime .on` loses to that own-color declaration.",
        "- Hex is computed-style only; visible-ink hex parked per packet D8.",
        "  No CSS change this round.",
        "",
        "## CORRECTIONS (r3 release record)",
        "",
        "- Analogs ship `Ignore` / 「可忽略」 lawfully (packet line 27 doctrine",
        "  vocabulary). The r2 DONE-map line \"Analogs keep Watch\" is superseded.",
        "  No template change.",
        "",
        "## Horizontal page scroll at 390w",
        "",
        f"- EN: overflow={hscroll.get('en', {}).get('overflow')} "
        f"scrollWidth={hscroll.get('en', {}).get('scrollWidth')} "
        f"clientWidth={hscroll.get('en', {}).get('clientWidth')}",
        f"- ZH: overflow={hscroll.get('zh', {}).get('overflow')} "
        f"scrollWidth={hscroll.get('zh', {}).get('scrollWidth')} "
        f"clientWidth={hscroll.get('zh', {}).get('clientWidth')}",
        "",
        "## Cells",
        "",
        "| id | fixture | theme | lang | vp | overlay | SETTLE | judged |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        settle = r.get("SETTLE") or {}
        col = "settled" if settle.get("ok") else "REFUSED"
        lines.append(
            f"| `{r['id']}` | {r.get('fixture')} | {r.get('theme')} | "
            f"{r.get('locale')} | {r.get('vp')} | {r.get('overlay')} | "
            f"{col} op={settle.get('content_root_opacity')} | {r.get('judged', '')} |"
        )
    lines.extend([
        "",
        "Recapture: `python3 mockups/evidence/china-intel-w12-r3/capture.py`",
        "",
    ])
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def _parse_only(argv: list[str] | None) -> set[str] | None:
    parser = argparse.ArgumentParser(prog="capture.py")
    parser.add_argument(
        "--only", default="",
        help="comma-separated cell ids; merge into the existing matrix",
    )
    args = parser.parse_args(argv)
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    return only or None


def _load_existing() -> tuple[dict[str, dict], dict[str, dict]]:
    cells_path = OUT / "cells.json"
    if not cells_path.exists():
        return {}, {}
    payload = json.loads(cells_path.read_text(encoding="utf-8"))
    cells = payload.get("cells") or {}
    hscroll = payload.get("h_scroll_390") or {}
    return cells, hscroll


def _drop_unreferenced_twins(keep: set[str]) -> None:
    keep_names = {Path(p).name for p in keep}
    for png in CELLS.glob("*.png"):
        stem = png.stem
        if len(stem) == 16 and all(c in "0123456789abcdef" for c in stem):
            if png.name not in keep_names:
                png.unlink()


def main(argv: list[str] | None = None) -> int:
    from playwright.sync_api import sync_playwright

    only = _parse_only(argv)
    sha = _head_sha()
    CELLS.mkdir(parents=True, exist_ok=True)

    spec = _cells()
    spec_by_id = {c["id"]: c for c in spec}
    if only:
        missing = sorted(only - set(spec_by_id))
        if missing:
            raise SystemExit(f"unknown cell ids: {missing}")
        spec_run = [c for c in spec if c["id"] in only]
        existing_cells, existing_hscroll = _load_existing()
    else:
        for stale in CELLS.glob("*.png"):
            stale.unlink()
        spec_run = spec
        existing_cells, existing_hscroll = {}, {}

    staging = Path(tempfile.mkdtemp(prefix="chintel-w12-r3-"))
    httpd = None
    rows: list[dict] = []
    hscroll: dict[str, dict] = dict(existing_hscroll)
    try:
        _prepare(staging)
        httpd, port = serve_site_dir(staging)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            current = None  # (fixture, w, h)
            context = None
            page = None
            for cell in spec_run:
                key = (cell["fixture"], cell["w"], cell["h"])
                if current != key:
                    if context is not None:
                        context.close()
                    context = browser.new_context(
                        viewport={"width": cell["w"], "height": cell["h"]},
                        device_scale_factor=2,
                        reduced_motion="reduce",
                        color_scheme=cell["theme"],
                        locale="zh-CN" if cell["locale"] == "zh" else "en-US",
                    )
                    context.add_init_script(
                        f"window.__skyDeck = true; try {{"
                        f"localStorage.setItem('theme', {json.dumps(cell['theme'])});"
                        f"localStorage.removeItem('themeAuto');"
                        f"localStorage.setItem('lang', {json.dumps(cell['locale'])});"
                        f"}} catch (e) {{}}"
                    )
                    page = context.new_page()
                    url = f"http://127.0.0.1:{port}/{cell['fixture']}.html"
                    resp = page.goto(url, wait_until="load", timeout=30000)
                    if resp is None or not resp.ok:
                        raise SystemExit(
                            f"HTTP {getattr(resp, 'status', None)} for {cell['id']}"
                        )
                    current = key
                body = _apply(page, cell["theme"], cell["locale"])
                nth = int(cell.get("nth") or 0)
                if cell.get("tip"):
                    _open_tip(page, cell["tip"], nth)
                settle = _settle(
                    page,
                    cell.get("root") or (".ci-wrap" if not cell.get("full") else "body"),
                    cell.get("sample") or "",
                )
                if cell.get("tip"):
                    pop_op = page.evaluate(
                        """() => {
                          const p = document.querySelector('.lens-pop.open');
                          if (!p) return 0;
                          return Number(getComputedStyle(p).opacity);
                        }"""
                    )
                    if pop_op < 0.999:
                        raise SystemExit(
                            f"SETTLE refused tip opacity {pop_op} on {cell['id']}"
                        )
                    settle["tip_opacity"] = pop_op
                overlay_sel = cell.get("sel") or "body"
                overlay = page.evaluate(_OVERLAY, overlay_sel)
                if not overlay.get("ok"):
                    raise SystemExit(f"overlay over {cell['id']}: {overlay}")

                colour = None
                if cell.get("colour"):
                    colour = page.evaluate(
                        """() => {
                          const b = document.querySelector('.cmdbar .regime b');
                          if (!b) return 'MISSING';
                          return {color: getComputedStyle(b).color,
                                  cls: b.className};
                        }"""
                    )
                    loc = cell["locale"]
                    cls = (colour or {}).get("cls") or ""
                    col = (colour or {}).get("color")
                    if loc == "en" and "on" in cls and col != "rgb(31, 154, 85)":
                        raise SystemExit(f"F3 EN colour {colour} on {cell['id']}")
                    if loc == "zh" and "on" in cls and col != "rgb(210, 63, 63)":
                        raise SystemExit(f"F3 ZH colour {colour} on {cell['id']}")

                if cell.get("full"):
                    png = page.screenshot(type="png", full_page=True)
                    clip = {"kind": "full-page"}
                    if cell["w"] == 390:
                        hs = page.evaluate(_HSCROLL)
                        hscroll[cell["locale"]] = hs
                        if hs.get("overflow"):
                            raise SystemExit(
                                f"page h-scroll at 390w {cell['locale']}: {hs}"
                            )
                else:
                    sels = [cell["sel"]] + list(cell.get("extra") or [])
                    clip = _canvas_clip(page, sels, nth)
                    png = page.screenshot(type="png", clip=clip)
                    if cell.get("tip"):
                        _close_tip(page)

                twin, digest, pw_, ph = _png_meta(png)
                alias = f"{cell['id']}.png"
                (CELLS / twin).write_bytes(png)
                (CELLS / alias).write_bytes(png)
                row = {
                    "id": cell["id"],
                    "file": f"cells/{alias}",
                    "twin": f"cells/{twin}",
                    "sha256": digest,
                    "bytes": len(png),
                    "width": pw_,
                    "height": ph,
                    "theme": cell["theme"],
                    "locale": cell["locale"],
                    "applied_theme": body["applied"]["theme"],
                    "applied_locale": body["applied"]["locale"],
                    "body_bg": body["body"]["bg"],
                    "body_classes": body["body"]["classes"],
                    "vp": cell["vp"],
                    "viewport": [cell["w"], cell["h"]],
                    "fixture": cell["fixture"],
                    "clip": clip,
                    "overlay": "clean",
                    "overlay_hits": overlay.get("hits") or [],
                    "SETTLE": settle,
                    "judged": cell["judged"],
                }
                if colour:
                    row["computed_color"] = colour
                if cell["w"] == 390 and cell.get("full"):
                    row["h_scroll"] = hscroll.get(cell["locale"])
                rows.append(row)
            if context is not None:
                context.close()
            browser.close()
    finally:
        if httpd is not None:
            httpd.shutdown()
        shutil.rmtree(staging, ignore_errors=True)

    captured = {r["id"]: r for r in rows}
    merged: dict[str, dict] = dict(existing_cells)
    merged.update(captured)
    # Caption truth travels with the spec, including cells not recaptured.
    for cid, cell in spec_by_id.items():
        if cid in merged:
            merged[cid]["judged"] = cell["judged"]
    ordered = [merged[c["id"]] for c in spec if c["id"] in merged]
    keep_twins = {r["twin"] for r in ordered if r.get("twin")}
    keep_twins |= {r["file"] for r in ordered if r.get("file")}
    _drop_unreferenced_twins(keep_twins)

    receipt = {
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sha": sha,
        "rig": ("S1 canvas-true (Playwright, real body canvas, overlay hide, "
                "reduced-motion, fonts.ready + getAnimations settle, "
                "viewport-region crops)"),
        "overlays_hidden": list(OVERLAY_SELECTORS),
        "canvas_margin_px": CANVAS_MARGIN,
        "h_scroll_390": hscroll,
        "cells": {r["id"]: r for r in ordered},
    }
    (OUT / "cells.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "manifest.json").write_text(
        json.dumps({
            "schema": "mastermind.p0_evidence.v2",
            "page": "china_intel",
            "round": "w12-r3",
            "sha": sha,
            "rig": receipt["rig"],
            "overlays_hidden": list(OVERLAY_SELECTORS),
            "selection": [r["id"] for r in ordered],
            "totals": {"states": len(ordered), "captured": len(ordered),
                       "failed": 0},
            "h_scroll_390": hscroll,
            "cells": {
                r["id"]: {
                    "file": r["file"], "twin": r["twin"], "sha256": r["sha256"],
                    "theme": r["theme"], "locale": r["locale"],
                    "vp": r["vp"], "fixture": r["fixture"],
                    "overlay": r["overlay"],
                    "SETTLE": (r.get("SETTLE") or {}).get("column"),
                    "clip_kind": (r.get("clip") or {}).get("kind"),
                    "judged": r.get("judged"),
                } for r in ordered
            },
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_readme(sha, ordered, hscroll)
    print(json.dumps({
        "sha": sha, "n": len(ordered), "recaptured": list(captured),
        "h_scroll_390": hscroll,
        "out": str(OUT),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
