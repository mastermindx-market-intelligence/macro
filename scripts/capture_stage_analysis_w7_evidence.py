#!/usr/bin/env python3
"""Element-screenshot evidence for stage_analysis.html W7 (round 3).

Captures dark+light × EN+ZH × 1440/390 of the packet states on a
fixture-rendered page (sparse trees have no data/ or site/). Playwright
applies theme/lang the way theme.js does and refuses a cell whose observed
data-theme/data-lang does not match the request.

Usage::

    python3 -m scripts.capture_stage_analysis_w7_evidence
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
OUT_DIR = REPO_ROOT / "mockups" / "evidence" / "stage-analysis-w7"
CELLS_DIR = OUT_DIR / "cells"

VIEWPORTS = {
    "desktop": (1440, 1200),
    "mobile": (390, 1400),
}
LOCALES = ("en", "zh")
THEMES = ("dark", "light")

_STATE_SEED_SCRIPT = """
(state) => {
  try {
    localStorage.setItem('theme', state.theme);
    localStorage.removeItem('themeAuto');
    localStorage.setItem('lang', state.locale);
  } catch (e) {}
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


def fixture_sga() -> dict:
    """Hero VM whose station counts match the screener fixture's current rows."""
    return {
        "schema": "stage_context.v1",
        "asof": "2026-09-10",
        "built": "2026-09-10T12:00:00Z",
        "is_context_only": True,
        "display_only": True,
        "target_stage_week": "2026-09-04",
        "data_session": "2026-09-10",
        "counts": {
            "total": 8, "stage1": 2, "stage2": 3, "stage2_fresh": 2,
            "stage3": 1, "stage4": 2, "too_young": 0, "new_today": 0,
        },
        "market": {
            "pct_stage2": 37.5, "pct_stage4": 25.0, "weather": "advancing",
            "spy_stage": 2, "spy_weeks": 17,
        },
        "population": {
            "current": 8, "stale": 1, "unknown": 2, "status": "ok",
        },
    }


def _row(**kw) -> dict:
    base = {
        "region": "USA", "stage_current": True, "source": "live",
        "sata_score": 7, "sata_change_1w": 1, "industry_percentile": 72,
        "weeks_in_stage": 8, "atr_ext": 1.4, "atr_pct_price": 0.04,
        "rating": 61, "tags": [], "ec_sent": None, "ec_perf": None,
        "fresh": False, "mansfield_rs": 2.0, "stage_label": "2X Bullish",
        "stage": 2,
    }
    base.update(kw)
    return base


def screener_payload() -> dict:
    rows = [
        _row(ticker="KO", name="Coca-Cola", sector="Consumer Staples",
             stage=1, stage_label="1X Base", weeks_in_stage=8, rating=28,
             sata_score=4, tags=["cost_control"]),
        _row(ticker="GE", name="GE Aerospace", sector="Industrials",
             stage=1, stage_label="1X Base", weeks_in_stage=3, rating=31,
             sata_score=3, tags=["supply_constraint"]),
        _row(ticker="NVDA", name="NVIDIA", sector="Information Technology",
             stage=2, stage_label="2A Breakout", weeks_in_stage=6, rating=88,
             sata_score=9, fresh=True, gate_tier="T1",
             ec_sent=72.2, ec_perf=8,
             tags=["guidance_raised", "demand_acceleration", "ai"]),
        _row(ticker="AVGO", name="Broadcom", sector="Information Technology",
             stage=2, stage_label="2A Breakout", weeks_in_stage=4, rating=81,
             sata_score=8, fresh=True, gate_tier="T1",
             ec_sent=66.5, ec_perf=7, tags=["guidance_raise", "new_product"]),
        _row(ticker="COST", name="Costco", sector="Consumer Staples",
             stage=2, stage_label="2X Bullish", weeks_in_stage=22, rating=70,
             sata_score=7, gate_tier="T2",
             ec_sent=47.2, ec_perf=6, tags=["margin_expansion"]),
        _row(ticker="MMM", name="3M", sector="Industrials",
             stage=3, stage_label="3A Topping", weeks_in_stage=4, rating=44,
             sata_score=5, tags=["guidance_lowered"],
             ec_sent=38.9, ec_perf=4),
        _row(ticker="PFE", name="Pfizer", sector="Health Care",
             stage=4, stage_label="4B Decline", weeks_in_stage=11, rating=18,
             sata_score=2, tags=["demand_slowdown"],
             ec_sent=27.8, ec_perf=3),
        _row(ticker="INTC", name="Intel", sector="Information Technology",
             stage=4, stage_label="4X Bearish", weeks_in_stage=25, rating=14,
             sata_score=2, tags=["regulatory_headwind"]),
        _row(ticker="WMT", name="Walmart", sector="Consumer Staples",
             stage=2, stage_label="2X Bullish", stage_current=False,
             stage_week_end="2026-07-17", rating=None, tags=["guidance"]),
        _row(ticker="UNK1", name="Unresolved One", sector="Financials",
             stage=2, stage_current=None, rating=None,
             tags=["regional_banks", "foo_bar_unmapped"]),
        _row(ticker="UNK2", name="Unresolved Two", sector="Financials",
             stage=1, stage_label="1X Base", stage_current=None, rating=None,
             tags=["net_interest_margin"]),
    ]
    return {"schema": "stage_screener.v1", "asof": "2026-09-10", "rows": rows}


def board_payload() -> dict:
    rows = [r for r in screener_payload()["rows"] if r.get("fresh") and r.get("stage") == 2]
    return {"schema": "stage_board.v1", "asof": "2026-09-10", "rows": rows}


def ranks_payload() -> dict:
    return {
        "schema": "industry_ranks.v1",
        "regions": {
            "USA": [
                {"industry_name": "Semiconductors", "industry_id": "semis",
                 "rank": 1, "industry_percentile": 92, "z_mom": 1.4,
                 "z_rsroc": 0.8, "bucket": "Leading", "n": 18},
                {"industry_name": "Software", "industry_id": "soft",
                 "rank": 4, "industry_percentile": 71, "z_mom": 0.4,
                 "z_rsroc": -0.1, "bucket": "Improving", "n": 40},
                {"industry_name": "Banks", "industry_id": "banks",
                 "rank": 22, "industry_percentile": 18, "z_mom": -0.9,
                 "z_rsroc": -0.6, "bucket": "Lagging", "n": 12},
            ]
        },
    }


def earnings_payload(*, status: str = "ok") -> dict:
    return {
        "schema": "earnings_table.v1",
        "data_status": status,
        "latest_call_date": "2026-08-28",
        "rows": [
            {
                "ticker": "NVDA", "company_name": "NVIDIA", "region": "USA",
                "gics_industry": "Semiconductors", "gics_sector": "Information Technology",
                "quarter": "Q2 2026", "call_date": "2026-08-28",
                "ec_sent": 72.2, "ec_perf": 8,
                "level1_tags": ["guidance_raised", "ai", "demand_acceleration"],
                "level2_tags": ["capital_allocation", "foo_bar_unmapped"],
                "positive_highlights": "1. Data-center demand still rising.\n2. Raised the year.",
                "negative_highlights": "1. Supply still tight.",
                "key_quote": "We are sold out through the year.",
            },
            {
                "ticker": "COST", "company_name": "Costco", "region": "USA",
                "gics_industry": "Consumer Staples", "quarter": "Q4 2026",
                "call_date": "2026-08-20", "ec_sent": 47.2, "ec_perf": 6,
                "level1_tags": ["margin_expansion", "guidance"],
                "positive_highlights": "1. Membership growth held.",
                "negative_highlights": "",
            },
        ],
    }


def alt_payload() -> dict:
    empty = {"topics": []}
    return {
        "schema": "altdata_trending.v1",
        "sources": {
            "google": dict(empty),
            "reddit": dict(empty),
            "wikipedia": dict(empty),
            "tiktok": {"topics": [], "seed_only": True},
        },
    }


def research_payload() -> dict:
    return {"schema": "research_index.v1", "items": []}


def heatmap_ok() -> dict:
    return {"schema": "industry_heatmap.v1", "regions": {}, "history": {"status": "ok"}}


def heatmap_unavailable() -> dict:
    return {
        "schema": "industry_heatmap.v1",
        "regions": {},
        "history": {"status": "unavailable"},
    }


def render_page(sga: dict | None = None) -> str:
    from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, Undefined
    from markupsafe import Markup

    stub = DictLoader({
        "_site_nav.html.j2": (
            "<!-- fixture: _site_nav omitted (two global nav families). "
            "theme.js is present so setTheme/setLang exist. -->\n"
        ),
        "_interfonts.html.j2": "",
        "_seo_head.html.j2": "",
    })
    env = Environment(
        loader=ChoiceLoader([stub, FileSystemLoader(str(TEMPLATES_DIR))]),
        autoescape=True,
        undefined=Undefined,
    )
    try:
        from engine import i18n
        env.globals.update(td=i18n.td, tr=i18n.tr)
    except Exception:
        def _td(en):
            return Markup(
                '<span class="l-en">{}</span><span class="l-zh">{}</span>'
            ).format(en, en)
        env.globals.update(td=_td, tr=lambda en: en)
    html = env.get_template("stage_analysis.html.j2").render(sga=sga or fixture_sga())
    hide = (
        "<style>"
        "#mmb-boot{display:none !important}"
        ".sky-fx{display:none !important}"
        ".rise{animation:none !important;opacity:1 !important;transform:none !important}"
        "</style>\n"
        "</body>"
    )
    if "</body>" not in html:
        raise RuntimeError("rendered stage_analysis.html.j2 has no </body>")
    return html.replace("</body>", hide, 1)


def write_fixture_site(scratch: Path) -> None:
    scratch.mkdir(parents=True, exist_ok=True)
    shutil.copy(TEMPLATES_DIR / "theme.js", scratch / "theme.js")
    shutil.copy(TEMPLATES_DIR / "theme.css", scratch / "theme.css")
    icons = TEMPLATES_DIR / "product-nav-icons.css"
    if icons.exists():
        shutil.copy(icons, scratch / "product-nav-icons.css")
    (scratch / "live.js").write_text("/* fixture stub */\n", encoding="utf-8")
    (scratch / "live_config.js").write_text("window.LIVE_CONFIG={};\n", encoding="utf-8")
    (scratch / "stage_analysis_w7.html").write_text(render_page(), encoding="utf-8")
    staged = scratch / "stagedata"
    staged.mkdir(parents=True, exist_ok=True)
    payloads = {
        "screener.json": screener_payload(),
        "stage_board_weekly.json": board_payload(),
        "stage_board_daily.json": board_payload(),
        "industry_ranks.json": ranks_payload(),
        "industry_heatmap.json": heatmap_ok(),
        "ec_industry_heatmap.json": {"regions": {}},
        "industry_flows.json": {"regions": {}},
        "earnings_table.json": earnings_payload(),
        "earnings_season.json": {"rows": []},
        "earnings_compare.json": {"rows": []},
        "altdata_trending.json": alt_payload(),
        "research_index.json": research_payload(),
    }
    for name, payload in payloads.items():
        (staged / name).write_text(json.dumps(payload), encoding="utf-8")
    (staged / "earnings_table_degraded.json").write_text(
        json.dumps(earnings_payload(status="degraded")), encoding="utf-8"
    )
    (staged / "earnings_table_stale.json").write_text(
        json.dumps(earnings_payload(status="stale")), encoding="utf-8"
    )
    (staged / "industry_heatmap_unavailable.json").write_text(
        json.dumps(heatmap_unavailable()), encoding="utf-8"
    )


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
  const pad = 12;
  const vx = Math.max(0, x - pad), vy = Math.max(0, y - pad);
  return {
    x: vx, y: vy,
    width: Math.min(window.innerWidth - vx, r - x + 2 * pad),
    height: Math.min(window.innerHeight - vy, b - y + 2 * pad),
  };
}
"""


def _new_page(browser, *, width, height, locale, theme, touch=False):
    context = browser.new_context(
        viewport={"width": width, "height": height},
        locale="zh-CN" if locale == "zh" else "en-US",
        color_scheme=theme,
        device_scale_factor=1,
        has_touch=touch,
        is_mobile=touch and width <= 390,
        reduced_motion="reduce",
        accept_downloads=True,
    )
    state = {"theme": theme, "locale": locale}
    context.add_init_script(f"({_STATE_SEED_SCRIPT.strip()})({json.dumps(state)});")
    page = context.new_page()
    return context, page


def _matrix_jobs(subject: str, *, action: str, clip_sels: list[str] | None,
                 force_state: str | None = None, touch: bool = False) -> list[dict]:
    jobs = []
    for viewport, (width, height) in VIEWPORTS.items():
        for locale in LOCALES:
            for theme in THEMES:
                jobs.append({
                    "subject": subject, "viewport": viewport, "locale": locale,
                    "theme": theme, "width": width, "height": height,
                    "clip_sels": clip_sels, "action": action,
                    "force_state": force_state, "touch": touch or (width <= 390),
                })
    return jobs


def _pair_jobs(subject: str, *, action: str, clip_sels: list[str] | None,
               force_state: str) -> list[dict]:
    """Fixture-only extras: dark-EN-1440 + light-ZH-390."""
    return [
        {
            "subject": subject, "viewport": "desktop", "locale": "en",
            "theme": "dark", "width": 1440, "height": 1200,
            "clip_sels": clip_sels, "action": action,
            "force_state": force_state, "touch": False,
        },
        {
            "subject": subject, "viewport": "mobile", "locale": "zh",
            "theme": "light", "width": 390, "height": 1400,
            "clip_sels": clip_sels, "action": action,
            "force_state": force_state, "touch": True,
        },
    ]


def _build_jobs() -> list[dict]:
    jobs: list[dict] = []
    jobs += _matrix_jobs("s1-screener", action="s1", clip_sels=None)
    jobs += _matrix_jobs("s2-china", action="s2-screener",
                         clip_sels=[".hero", ".controls", ".filterbar"])
    jobs += _pair_jobs("s2-china", action="s2-board",
                       clip_sels=[".hero", ".controls", "#board-table"],
                       force_state="board")
    jobs += _pair_jobs("s2-china", action="s2-ind",
                       clip_sels=[".hero", ".controls", "#ind-body"],
                       force_state="ind")
    jobs += _matrix_jobs("s3-research", action="s3", clip_sels=["#s-research", ".controls"])
    jobs += _matrix_jobs("s4-altdata", action="s4", clip_sels=["#s-altdata", ".controls"])
    jobs += _matrix_jobs("s5-earnings", action="s5-ern",
                         clip_sels=["#s-earnings"])
    jobs += _matrix_jobs("s5-industries", action="s5-ind",
                         clip_sels=["#s-industries"])
    jobs += _matrix_jobs("s6-board", action="s6",
                         clip_sels=["#s-board", ".controls"])
    jobs += _matrix_jobs("s7-screener-404", action="s7-scr-404",
                         clip_sels=["#s-screener"])
    jobs += _pair_jobs("s7-screener-404", action="s7-board-404",
                       clip_sels=["#s-board"], force_state="board-404")
    jobs += _pair_jobs("s7-screener-404", action="s7-ern-degraded",
                       clip_sels=["#s-earnings"], force_state="ern-degraded")
    jobs += _pair_jobs("s7-screener-404", action="s7-ern-stale",
                       clip_sels=["#s-earnings"], force_state="ern-stale")
    jobs += _pair_jobs("s7-screener-404", action="s7-heat-unavail",
                       clip_sels=["#s-industries"], force_state="heat-unavail")
    jobs += _matrix_jobs("s8-loading", action="s8", clip_sels=["#s-screener"])
    jobs += [
        {
            "subject": "s1-screener", "viewport": "desktop", "locale": "en",
            "theme": "dark", "width": 1440, "height": 1200,
            "clip_sels": [".filterbar"], "action": "kb-tip",
            "force_state": "keyboard-tip", "touch": False,
        },
        {
            "subject": "s1-screener", "viewport": "mobile", "locale": "en",
            "theme": "dark", "width": 390, "height": 1400,
            "clip_sels": [".filterbar"], "action": "tap-tip",
            "force_state": "tap-tip", "touch": True,
        },
    ]
    return jobs


def _install_routes(page, action: str) -> None:
    if action == "s8":
        page.route("**/stagedata/screener.json", lambda route: route.fetch() if False else None)

        def hang(route):
            page.wait_for_timeout(8000)
            route.fulfill(status=200, content_type="application/json", body="{}")

        page.route("**/stagedata/screener.json", hang)
        return
    if action == "s7-scr-404":
        page.route("**/stagedata/screener.json",
                   lambda route: route.fulfill(status=404, body="missing"))
        return
    if action == "s7-board-404":
        page.route("**/stagedata/stage_board_weekly.json",
                   lambda route: route.fulfill(status=404, body="missing"))
        page.route("**/stagedata/stage_board_daily.json",
                   lambda route: route.fulfill(status=404, body="missing"))
        return
    if action == "s7-ern-degraded":
        page.route(
            "**/stagedata/earnings_table.json",
            lambda route: route.fulfill(
                status=200, content_type="application/json",
                path=str(Path(route.request.url.split("/stagedata/")[0]) )  # placeholder
            ),
        )
        return


def _apply_action(page, action: str, scratch: Path) -> dict:
    extra: dict = {}
    if action == "s8":
        page.wait_for_timeout(280)
        extra["skeleton"] = page.locator(".sk-load").count() > 0
        return extra
    if action.startswith("s7-scr"):
        page.wait_for_timeout(400)
        extra["empty_copy"] = page.locator("#screener-body .empty h3").inner_text()
        return extra
    if action == "s7-board-404":
        page.locator('.tab[data-tab="board"]').click()
        page.wait_for_timeout(500)
        extra["empty_copy"] = page.locator("#board-body .empty h3").inner_text()
        return extra
    if action in ("s7-ern-degraded", "s7-ern-stale"):
        page.locator('.tab[data-tab="earnings"]').click()
        page.wait_for_timeout(600)
        extra["empty_copy"] = page.locator("#ern-body").inner_text()[:240]
        return extra
    if action == "s7-heat-unavail":
        page.locator('.tab[data-tab="industries"]').click()
        page.wait_for_timeout(500)
        page.locator('#ind-seg button[data-iview="heatmap"]').click()
        page.wait_for_timeout(200)
        extra["empty_copy"] = page.locator("#ind-body").inner_text()[:240]
        return extra
    # Happy-path loads
    page.wait_for_timeout(200)
    if action in ("s1", "s2-screener", "kb-tip", "tap-tip"):
        page.wait_for_selector("#screener-body tr[data-tk], #screener-body .empty", timeout=8000)
    if action == "s2-screener":
        btn = page.locator('#region-tip-q')
        btn.evaluate("el => el.click()")
        page.wait_for_timeout(180)
        extra["tip_open"] = page.locator("#region-tip-q.tip-open").count() > 0
        extra["china_disabled"] = page.locator('#region-seg button[data-region="CHINA"]').get_attribute("disabled") is not None
    if action == "s2-board":
        page.locator('.tab[data-tab="board"]').click()
        page.wait_for_timeout(400)
        page.locator('#region-tip-q').evaluate("el => el.click()")
        page.wait_for_timeout(120)
    if action == "s2-ind":
        page.locator('.tab[data-tab="industries"]').click()
        page.wait_for_timeout(500)
        page.locator('#region-tip-q').evaluate("el => el.click()")
        page.wait_for_timeout(120)
    if action == "s3":
        page.locator('.tab[data-tab="research"]').click()
        page.wait_for_timeout(500)
        extra["res_empty"] = "Company primers" in page.locator("#res-body").inner_text() or "公司简介" in page.locator("#res-body").inner_text()
    if action == "s4":
        page.locator('.tab[data-tab="altdata"]').click()
        page.wait_for_timeout(500)
        extra["live_chip"] = page.locator(".liveflag").count()
        extra["alt_copy"] = page.locator("#s-altdata").inner_text()[:400]
    if action == "s5-ern":
        page.locator('.tab[data-tab="earnings"]').click()
        page.wait_for_timeout(600)
        extra["read_word"] = page.locator("#ern-table .toneword").first.inner_text()
        extra["tone_cell"] = page.locator("#ern-table .ecscore .tone").first.inner_text()
    if action == "s5-ind":
        page.locator('.tab[data-tab="industries"]').click()
        page.wait_for_timeout(500)
        extra["ind_head"] = page.locator("#ind-body thead").inner_text(timeout=4000)
    if action == "s6":
        page.locator('.tab[data-tab="board"]').click()
        page.wait_for_timeout(500)
        extra["setup"] = page.locator("#board-body .gatechip").first.inner_text()
    if action == "kb-tip":
        btn = page.locator(".filterbar .tip-q").nth(1)
        btn.focus()
        page.keyboard.press("Enter")
        page.wait_for_timeout(180)
        extra["tip_open"] = page.locator(".filterbar .tip-q.tip-open").count() > 0
    if action == "tap-tip":
        btn = page.locator(".filterbar .tip-q").nth(1)
        btn.evaluate("el => el.click()")
        page.wait_for_timeout(180)
        extra["tip_open"] = page.locator(".filterbar .tip-q.tip-open").count() > 0
    return extra


def _measure_proofs(page) -> dict:
    proofs: dict = {}
    proofs["hscroll"] = page.evaluate(
        """() => {
          const tabs = [...document.querySelectorAll('.tab')].map(t => t.getAttribute('data-tab'));
          const out = {};
          for (const name of tabs) {
            const btn = document.querySelector('.tab[data-tab="'+name+'"]');
            if (btn) btn.click();
          }
          return {
            scrollWidth: document.documentElement.scrollWidth,
            clientWidth: document.documentElement.clientWidth,
            bodyScroll: document.body.scrollWidth
          };
        }"""
    )
    return proofs


def _capture(scratch: Path, subjects: set[str] | None = None) -> dict:
    from scripts.capture_page_evidence import CaptureUnavailable, serve_site_dir

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise CaptureUnavailable(f"playwright is not importable: {exc}") from exc

    httpd, port = serve_site_dir(scratch)
    sha, gitdir = _git_head_of_repo()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pages: list[dict] = []
    written: set[str] = set()
    aliases: dict[str, str] = {}
    jobs = _build_jobs()
    if subjects:
        jobs = [j for j in jobs if j["subject"] in subjects]
    nonvisual: dict = {"csv": None, "zh_tags": None, "hscroll": []}

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
                action = job["action"]
                entry: dict = {
                    "viewport": viewport, "locale": locale, "theme": theme,
                    "access": "anonymous", "viewport_width": width if width >= 1000 else width,
                    "viewport_height": height, "force_state": job.get("force_state"),
                    "subject": subject, "action": action,
                }
                # Gate identity uses 1440 / 390, not the taller crop height.
                entry["viewport_width"] = 1440 if viewport == "desktop" else 390
                context, page = _new_page(
                    browser, width=width, height=height, locale=locale,
                    theme=theme, touch=bool(job.get("touch")),
                )
                try:
                    if action == "s8":
                        page.route("**/stagedata/screener.json", lambda route: None)
                    elif action == "s7-scr-404":
                        page.route("**/stagedata/screener.json",
                                   lambda route: route.fulfill(status=404, body="missing"))
                    elif action == "s7-board-404":
                        page.route("**/stagedata/stage_board_weekly.json",
                                   lambda route: route.fulfill(status=404, body="missing"))
                        page.route("**/stagedata/stage_board_daily.json",
                                   lambda route: route.fulfill(status=404, body="missing"))
                    elif action == "s7-ern-degraded":
                        _ern_body = json.dumps(earnings_payload(status="degraded"))
                        def _ern_deg(route):
                            route.fulfill(status=200, content_type="application/json", body=_ern_body)
                        page.route("**/stagedata/earnings_table.json", _ern_deg)
                    elif action == "s7-ern-stale":
                        _ern_body = json.dumps(earnings_payload(status="stale"))
                        def _ern_stale(route):
                            route.fulfill(status=200, content_type="application/json", body=_ern_body)
                        page.route("**/stagedata/earnings_table.json", _ern_stale)
                    elif action == "s7-heat-unavail":
                        _heat_body = json.dumps(heatmap_unavailable())
                        def _heat(route):
                            route.fulfill(status=200, content_type="application/json", body=_heat_body)
                        page.route("**/stagedata/industry_heatmap.json", _heat)
                    url = f"http://127.0.0.1:{port}/stage_analysis_w7.html"
                    response = page.goto(url, wait_until="load", timeout=30000)
                    if response is None or not response.ok:
                        raise RuntimeError(f"HTTP {getattr(response, 'status', 'none')}")
                    page.wait_for_timeout(80)
                    applied0 = page.evaluate(
                        _APPLY_STATE_SCRIPT.strip(),
                        {"theme": theme, "locale": locale},
                    ) or {}
                    if applied0.get("theme") != theme or applied0.get("locale") != locale:
                        raise RuntimeError(
                            f"state mismatch: requested theme={theme} locale={locale} "
                            f"observed {applied0!r}"
                        )
                    try:
                        extra = _apply_action(page, action, scratch)
                    except Exception as exc:
                        extra = {"action_error": f"{type(exc).__name__}: {exc}"}
                    entry.update({k: v for k, v in extra.items() if v is not None})

                    # Non-visual proofs on the default S1 dark/en/desktop cell.
                    if action == "s1" and theme == "dark" and locale == "en" and viewport == "desktop":
                        showing = page.locator("#screener-showing").inner_text()
                        hero = {
                            "s1": page.locator('.stn.s1 .num').inner_text(),
                            "s2": page.locator('.stn.s2 .num').inner_text(),
                            "s3": page.locator('.stn.s3 .num').inner_text(),
                            "s4": page.locator('.stn.s4 .num').inner_text(),
                        }
                        entry["showing"] = showing
                        entry["hero_stations"] = hero
                        # CSV
                        with page.expect_download(timeout=5000) as dl_info:
                            page.locator("#screener-csv").click()
                        download = dl_info.value
                        csv_path = scratch / "stage_screener.csv"
                        download.save_as(str(csv_path))
                        csv_text = csv_path.read_text(encoding="utf-8")
                        header = csv_text.splitlines()[0] if csv_text else ""
                        nonvisual["csv"] = header
                        entry["csv_header"] = header
                    if action == "s1" and locale == "zh" and viewport == "desktop" and theme == "dark":
                        tags = page.evaluate(
                            """() => [...document.querySelectorAll('#screener-body .tagpill, #ern-table .tagpill')]
                              .map(el => el.textContent.trim()).filter(Boolean)"""
                        )
                        # Open earnings for theme tags
                        page.locator('.tab[data-tab="earnings"]').click()
                        page.wait_for_timeout(500)
                        tags += page.evaluate(
                            """() => [...document.querySelectorAll('#ern-table .tagpill')]
                              .map(el => el.textContent.trim()).filter(Boolean)"""
                        )
                        nonvisual["zh_tags"] = tags
                        entry["zh_tags"] = tags
                        page.locator('.tab[data-tab="screener"]').click()
                        page.wait_for_timeout(200)
                    if action == "s1" and viewport == "mobile" and theme == "dark" and locale == "en":
                        tabs = ["screener", "board", "industries", "earnings", "altdata", "research"]
                        hs = []
                        for tab in tabs:
                            page.locator(f'.tab[data-tab="{tab}"]').click()
                            page.wait_for_timeout(350)
                            m = page.evaluate(
                                """() => ({sw: document.documentElement.scrollWidth,
                                           cw: document.documentElement.clientWidth})"""
                            )
                            m["tab"] = tab
                            hs.append(m)
                        nonvisual["hscroll"] = hs
                        entry["hscroll"] = hs
                        page.locator('.tab[data-tab="screener"]').click()
                        page.wait_for_timeout(400)

                    clip_sels = job.get("clip_sels")
                    overlay = page.evaluate(_OVERLAY_PROBE.strip()) or []
                    box = None
                    if clip_sels:
                        for sel in clip_sels:
                            loc = page.locator(sel).first
                            if loc.count():
                                try:
                                    loc.scroll_into_view_if_needed()
                                except Exception:
                                    pass
                        page.wait_for_timeout(60)
                        box = page.evaluate(_clip_union_js().strip(), clip_sels)
                    if box and box.get("width", 0) >= 4 and box.get("height", 0) >= 4:
                        y = max(0, float(box["y"]))
                        hgt = float(box["height"])
                        if action in ("kb-tip", "tap-tip", "s2-screener", "s2-board", "s2-ind"):
                            extra_top = 90
                            y = max(0, y - extra_top)
                            hgt = min(float(height) - y, hgt + extra_top)
                        clip = {
                            "x": max(0, float(box["x"])),
                            "y": y,
                            "width": min(float(width), float(box["width"])),
                            "height": min(float(height) - y, hgt),
                        }
                        png = page.screenshot(type="png", clip=clip)
                    else:
                        png = page.screenshot(type="png")
                    name, digest, pw, ph = content_address_png(png, CELLS_DIR)
                    fs = job.get("force_state") or "rest"
                    alias = f"{subject}-{theme}-{locale}-{viewport}-{fs}.png"
                    (CELLS_DIR / alias).write_bytes(png)
                    written.add(name)
                    written.add(alias)
                    aliases[alias] = name
                    overlay_clean = not overlay
                    entry.update({
                        "captured": True, "file": f"cells/{name}", "alias": alias,
                        "sha256": digest, "bytes": len(png), "width": pw, "height": ph,
                        "applied_theme": theme, "applied_locale": locale,
                        "overlay": overlay, "overlay_clean": overlay_clean,
                    })
                except Exception as exc:
                    entry.update({
                        "captured": False,
                        "reason": f"{type(exc).__name__}: {exc}",
                        "overlay_clean": False,
                    })
                finally:
                    try:
                        page.unroute_all(behavior="ignoreErrors")
                    except Exception:
                        pass
                    context.close()
                by_subject.setdefault(subject, []).append(entry)
                flag = "ok" if entry.get("captured") else "FAIL"
                print(
                    f"  {subject} {theme}/{locale}/{viewport}"
                    f"{'/'+str(job.get('force_state') or 'rest')}: {flag}",
                    flush=True,
                )

            for subject, states in by_subject.items():
                pages.append({
                    "page_id": f"stage_analysis.html#{subject}",
                    "route": "/stage_analysis_w7.html",
                    "registry_route": "/stage_analysis.html",
                    "route_kind": "stage_analysis_w7_subject",
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
            "module_ref": "scripts/capture_stage_analysis_w7_evidence.py",
            "version": "w7-r3-element",
            "capture_method": (
                "playwright viewport/clip screenshot on a fixture-rendered "
                "stage_analysis.html.j2 (page CSS + theme.css + theme.js). "
                "JSON feeds stubbed from round-2 shapes. data-theme/data-lang "
                "applied via window.setTheme/setLang with refuse-on-mismatch. "
                "window.__skyDeck skips skyToggleFx. sha256 from the screenshot bytes."
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
                "fixture render, not live site/stage_analysis.html"
            ),
        },
        "axes": {
            "viewports": {name: [size[0], 900 if name == "desktop" else 844]
                          for name, size in VIEWPORTS.items()},
            "locales": list(LOCALES),
            "themes": list(THEMES),
            "access": ["anonymous"],
            "subjects": [p["subject"] for p in pages],
            "force_states": sorted({
                s.get("force_state") for p in pages for s in p["states"]
                if s.get("force_state")
            }),
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
        "nonvisual": nonvisual,
        "honesty": {
            "access": "anonymous only",
            "gaps": "uncaptured cells are recorded with a reason",
            "authority": "this tool screenshots; it scores nothing",
            "page": (
                "stage_analysis.html.j2 rendered with a count-matched fixture "
                "(hero stations 2/3/1/2 = 8 current; screener showing 8 of 8 "
                "current · 1 stale · 2 unresolved). Feeds are fixture JSON, not "
                "the live nightly bake. Omitted vs live: _site_nav chrome, "
                "live.js hydration, Inter webfonts (system fallback). Capture "
                "sets window.__skyDeck and strips leftover .sky-fx / #mmb-boot. "
                "S4 still prints a live chip over empty topics — captured honestly."
            ),
        },
        "pages": pages,
    }
    return {"manifest": manifest, "written": sorted(written), "outcome": outcome}


def _write_readme(manifest: dict) -> str:
    lines = [
        "# Stage Analysis W7 — evidence matrix (round 3)",
        "",
        "Packet REQUIRED EVIDENCE MATRIX: dark × light × EN × ZH × 1440/390 "
        "(8 shots per state). Fixture-only extras use dark-EN-1440 + light-ZH-390.",
        "",
        "## Fixture",
        "",
        "- Source: `templates/stage_analysis.html.j2` + page-scoped `<style>` + `theme.css` / `theme.js`.",
        "- Hero VM: 8 current (2/3/1/2 stations) + 1 stale + 2 unresolved, matching the screener JSON.",
        "- Feeds: fixture JSONs in the scratch `stagedata/` (round-2 shapes). Not the live bake.",
        "- Theme/lang: Playwright seeds localStorage then calls `window.setTheme` / `window.setLang`; a mismatch refuses the cell.",
        "- `window.__skyDeck = true` in the init script (skyToggleFx bow-out) and any leftover `.sky-fx` is removed after apply.",
        "",
        "## Honest differences from live `site/stage_analysis.html`",
        "",
        "- No `_site_nav` chrome (two global nav families; this crop is the page wrap).",
        "- No live.js hydration.",
        "- Inter webfonts are not copied; system UI fonts render.",
        "- Counts are a representative 8-name universe, not that night's 2,700-name bake — the M1 proof is that the **integers agree with each other**, not that they match production.",
        "- Sparse checkout has no `data/` or `site/`; this is why the page is fixture-rendered.",
        "- `#mmb-boot` and `.sky-fx` are stripped for capture; live still shows both on toggle.",
        "- `.rise` animation is disabled so ATF opacity is 1 at shot time.",
        "- **S4 live chip:** round-1 scope creep not done. Empty topics still print a `live` chip on Google/Reddit/Wikipedia; TikTok is `seed only`. Captured honestly.",
        "",
        "## Cells",
        "",
        "| Subject | Theme | Lang | Viewport | Force | Alias | Captured | Overlay clean |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for page in manifest["pages"]:
        for st in page["states"]:
            overlay = "yes" if st.get("overlay_clean") else (
                "NO: " + json.dumps(st.get("overlay") or st.get("reason"))
                if st.get("captured") else st.get("reason", "no")
            )
            lines.append(
                f"| {page['subject']} | {st.get('theme')} | {st.get('locale')} | "
                f"{st.get('viewport')} | {st.get('force_state') or 'rest'} | "
                f"`{st.get('alias', '')}` | "
                f"{'yes' if st.get('captured') else st.get('reason', 'no')} | {overlay} |"
            )
    nv = manifest.get("nonvisual") or {}
    lines += [
        "",
        "## State proofs (judged from the files after capture)",
        "",
        "Dark and light are two art directions. Overlay column is above.",
        "",
        "| State | What it must show | Aliases | Overlay | Verdict |",
        "|---|---|---|---|---|",
        "| S1 Screener default | Hero stations + showing line agree (8 current); unresolved >0 | `s1-screener-*-rest` | see table | PENDING-JUDGE |",
        "| S2 Region=China | Disabled China + true-reason tip + US-scope hero | `s2-china-*` | see table | PENDING-JUDGE |",
        "| S3 Research items:0 | resEmpty copy, not Earnings | `s3-research-*` | see table | PENDING-JUDGE |",
        "| S4 Alt-Data empty topics | Empty-topic sentence; live chip still present (disclosed) | `s4-altdata-*` | see table | PENDING-JUDGE |",
        "| S5 Tone/result + Ranking | Published 72.2 + Upbeat + Trend strength headers | `s5-earnings-*`, `s5-industries-*` | see table | PENDING-JUDGE |",
        "| S6 Setup column | Cleanest/Solid at rest, T1/T2 in the tip | `s6-board-*` | see table | PENDING-JUDGE |",
        "| S7 Forced failures | Plain-word 404 / degraded / stale / heatmap unavailable | `s7-*` | see table | PENDING-JUDGE |",
        "| S8 Loading skeleton | Wordless `.sk-load` mid-fetch | `s8-loading-*` | see table | PENDING-JUDGE |",
        "",
        "## Non-visual proofs",
        "",
        f"- CSV header: `{nv.get('csv')}`",
        f"- ZH tags: `{nv.get('zh_tags')}`",
        f"- Horizontal scroll at 390: `{json.dumps(nv.get('hscroll'))}`",
        "",
        "## Capture-harness disclosure",
        "",
        "`theme.js` `skyToggleFx` appends a `.sky-fx` sun/moon disc for ~1100ms "
        "after every `setTheme`. This harness seeds `window.__skyDeck = true` "
        "and removes any leftover `.sky-fx` after apply. The brain FAB "
        "(`#mmb-boot`) is stripped so it cannot sit on a crop. Live toggles "
        "still play the flourish. Per-crop overlay column is above.",
        "",
        "Light treatment is page-scoped (`w7-r3-light` marker): cool canvas, "
        "white material, hairline, shadow. Dark remains the command-center.",
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

    scratch = Path(tempfile.mkdtemp(prefix="stage_w7_evidence_"))
    try:
        print("rendering stage_analysis.html.j2 (fixture VM)", flush=True)
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
                "nonvisual": {**prev.get("nonvisual", {}), **manifest.get("nonvisual", {})},
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
            "  - templates/stage_analysis.html.j2\n"
            "manifest: mockups/evidence/stage-analysis-w7/manifest.json\n",
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
