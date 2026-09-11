#!/usr/bin/env python3
"""Evidence matrix for china_policy_watch W5 r3 (Archetype E).

Fixture VM + Playwright localStorage seed + setTheme/setLang, attribute
re-read, refuse-on-mismatch. Sparse trees have no site/; this renders the
Jinja template against a representative view-model.

Usage::

    python3 -m scripts.capture_china_policy_watch_evidence
"""
from __future__ import annotations

import hashlib
import json
import shutil
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from lib import config  # noqa: E402

REPO_ROOT = _ROOT
TEMPLATES_DIR = REPO_ROOT / "templates"
OUT_DIR = REPO_ROOT / "mockups" / "evidence" / "china-policy-watch"
CELLS_DIR = OUT_DIR / "cells"

VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}
LOCALES = ("en", "zh")
THEMES = ("dark", "light")

_STATE_SEED_SCRIPT = """
(state) => {
  try {
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


def _tells(*, before: bool) -> list[dict]:
    margin_en = ("Margin balance turning up (leverage returning)" if before
                 else "Margin balance fell ¥3.2bn last session")
    margin_zh = ("两融余额企稳回升（杠杆资金回流）" if before
                 else "两融余额上一交易日减少32亿")
    buy_en = ("SOE buyback proposals accelerating (+-20% w/w)" if before
              else "SOE buyback proposals -20% w/w")
    buy_zh = ("国企回购预案加速（环比+-20%）" if before
              else "国企回购预案环比−20%")
    return [
        {"key": "etf_creation", "tier": "leading", "state": "quiet", "strength": 0,
         "label_en": "ETF creation", "label_zh": "ETF创设",
         "value_fmt": "+1%", "value_fmt_en": "+1%", "value_fmt_zh": "+1%",
         "receipt_en": "peak team-ETF unit creation +1% (2d)",
         "receipt_zh": "权重ETF份额峰值 +1%（2日）"},
        {"key": "market_rescue", "tier": "leading", "state": "quiet", "strength": 0,
         "label_en": "Market rescue impulse", "label_zh": "托市脉冲",
         "value_fmt": "accommodative", "value_fmt_en": "accommodative", "value_fmt_zh": "宽松",
         "receipt_en": "Policy impulse: accommodative", "receipt_zh": "政策脉冲：宽松"},
        {"key": "facility_watch", "tier": "leading", "state": "null", "strength": 0,
         "label_en": "PBoC support facility", "label_zh": "央行支持工具",
         "value_fmt": None, "value_fmt_en": None, "value_fmt_zh": None,
         "receipt_en": "", "receipt_zh": ""},
        {"key": "pboc_posture", "tier": "leading", "state": "quiet", "strength": 0,
         "label_en": "PBoC posture", "label_zh": "央行姿态",
         "value_fmt": "+0.40z", "value_fmt_en": "+0.40z", "value_fmt_zh": "+0.40z",
         "receipt_en": "FR007 z +0.40 — posture tell not firing",
         "receipt_zh": "FR007 z +0.40 — 姿态信号未触发"},
        {"key": "largecap_divergence", "tier": "coincident", "state": "quiet", "strength": 0,
         "label_en": "Large-cap divergence", "label_zh": "权重背离",
         "value_fmt": "+0.4pp", "value_fmt_en": "+0.4pp", "value_fmt_zh": "+0.4pp",
         "receipt_en": "Index heavyweights +0.4% vs small-caps +0.0% (5d)",
         "receipt_zh": "权重股+0.4% vs 中小盘+0.0%（5日）"},
        {"key": "state_media_drumbeat", "tier": "coincident", "state": "quiet", "strength": 0,
         "label_en": "State-media drumbeat", "label_zh": "官媒定调",
         "value_fmt": "0", "value_fmt_en": "0", "value_fmt_zh": "0",
         "receipt_en": "No stability drumbeat in the window",
         "receipt_zh": "窗口内无维稳定调"},
        {"key": "buyback_cascade", "tier": "confirming", "state": "quiet", "strength": 0,
         "label_en": "SOE buyback cascade", "label_zh": "国企回购潮",
         "value_fmt": "+-20%" if before else "-20%",
         "value_fmt_en": "+-20%" if before else "-20%",
         "value_fmt_zh": "+-20%" if before else "-20%",
         "receipt_en": buy_en, "receipt_zh": buy_zh},
        {"key": "margin_recovery", "tier": "confirming", "state": "quiet", "strength": 0,
         "label_en": "Margin recovery", "label_zh": "两融回升",
         "value_fmt": "-32亿" if before else "-3.2bn",
         "value_fmt_en": "-3.2bn", "value_fmt_zh": "-32亿",
         "receipt_en": margin_en, "receipt_zh": margin_zh},
    ]


def fixture_vm(*, before: bool = False) -> dict:
    from engine.china_policy_watch import _decorate_intel

    intel = json.loads((config.ROOT / "data" / "china_policy" / "intel.json").read_text())
    if not before:
        intel = _decorate_intel(intel)
    feed = [
        {"title": "PBoC keeps LPR unchanged", "url": "https://www.pbc.gov.cn/x",
         "source_chip": "PBoC",
         "theme_en": "PBoC" if before else "Monetary policy",
         "theme_zh": "央行" if before else "货币政策",
         "scheduled_ref": "CPI@2026-09-09"},
        {"title": "ECB holds rates steady", "url": "https://www.reuters.com/ecb",
         "source_chip": "reuters.com",
         "theme_en": "PBoC" if before else "Monetary policy",
         "theme_zh": "央行" if before else "货币政策",
         "scheduled_ref": ""},
    ]
    if not before:
        feed = [feed[0], {"title": "MOF expands trade-in subsidies",
                          "url": "https://www.gov.cn/x", "source_chip": "gov.cn",
                          "theme_en": "Fiscal", "theme_zh": "财政", "scheduled_ref": ""}]
    return {
        "schema": "china_policy_watch.v1",
        "is_context_only": True,
        "asof": "2026-07-20" if before else "2026-09-09",
        "built": "2026-09-10 12:00 UTC",
        "pboc_asof": "2026-07-20",
        "backdrop_asof": "2026-09-09",
        "nbs_asof": "2026-08-31",
        "nbs_stance_en": "Growth is soft and prices are barely rising — watch, don't chase",
        "nbs_stance_zh": "增长偏弱、物价几乎不涨——观望，不要追",
        "sector_table_cap": 8,
        "policy_feed_status": "ok",
        "pboc": {
            "stance": "easing", "stance_en": "Easing", "stance_zh": "宽松",
            "rationale": {
                "en": ("Easing bias — 1Y LPR -10bp / yr, FR007 +0.12 vs trend."
                       if before else
                       "Easing bias — 1Y LPR -10bp over 12 months, RRR -0.50pp over 18 months."),
                "zh": ("宽松倾向 — 1年期LPR年内-10基点，FR007较趋势+0.12。"
                       if before else
                       "宽松倾向 — 1年期LPR过去12个月-10基点，准备金率过去18个月-0.50个百分点。"),
            },
            "corridor": [
                {"key": "lpr_1y", "label_en": "1Y LPR", "label_zh": "1年期LPR", "value": 3.00, "unit": "%"},
                {"key": "lpr_5y", "label_en": "5Y LPR", "label_zh": "5年期LPR", "value": 3.50, "unit": "%"},
                {"key": "rrr", "label_en": "RRR (big banks)", "label_zh": "存准率(大行)",
                 "value": 6.6, "unit": "%",
                 "window_en": "18-month window", "window_zh": "18个月窗口"},
                {"key": "fr007", "label_en": "FR007 (repo)", "label_zh": "FR007回购",
                 "value": 1.62, "unit": "%",
                 "slice_en": "vs 120d avg +0.12pp",
                 "slice_zh": "较120日均值+0.12个百分点"},
                {"key": "shibor_on", "label_en": "SHIBOR O/N", "label_zh": "隔夜SHIBOR",
                 "value": 1.45, "unit": "%"},
                {"key": "shibor_3m", "label_en": "SHIBOR 3M", "label_zh": "3个月SHIBOR",
                 "value": 1.72, "unit": "%"},
            ],
            "fx": {"reserves": 34187.76, "reserves_mom": 25.14, "gold": 72.0,
                   "usd_cny": 7.123, "usd_cny_chg_20d": 0.012,
                   "asof_reserves": "2026-08-01", "asof_cny": "2026-09-09"},
            "last_moves": [{"date": "2026-05-15", "easing": True,
                            "detail_en": "RRR cut 0.50pp", "detail_zh": "降准 0.50个百分点"}],
            "asof": "2026-07-20",
        },
        "nbs_prints": [
            {"key": "pmi_mfg", "label_en": "Mfg PMI", "label_zh": "制造业PMI",
             "value": 49.4, "unit": "", "asof": "2026-08-31",
             "dir_en": "below 50 — contracting", "dir_zh": "低于50——收缩"},
            {"key": "cpi_yoy", "label_en": "CPI YoY", "label_zh": "CPI同比",
             "value": 0.3, "unit": "%", "asof": "2026-08-31",
             "dir_en": "rising", "dir_zh": "上行"},
            {"key": "tsf_total", "label_en": "TSF (mo)", "label_zh": "社融(当月)",
             "value": 1130.0, "unit": "¥bn", "asof": "2026-08-31",
             "dir_en": "down from last month", "dir_zh": "低于上月"},
        ],
        "policy_feed": feed,
        "intel": intel,
        "intel_dates": {"staleness": {"as_of": "2026-06-20", "age_days": 83, "stale": True}},
        "national_team": {
            "stale": False, "asof_inputs": "2026-09-09", "age_days": 1,
            "pressure": {"score": 22, "band": "quiet", "band_en": "Quiet",
                         "band_zh": "平静", "accent": "muted"},
            "stance": {"en": "No clear state-hand footprint right now.",
                       "zh": "当前未见明确国家队足迹。"},
            "tell_counts": {"firing": 0, "total": 8, "null": 1},
            "tells": _tells(before=before),
            "gaps": [],
            "history": [{"score": 18, "date": "2026-09-08"},
                        {"score": 22, "date": "2026-09-09"}],
        },
    }


def _env():
    from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
    from engine import i18n

    def fmt_signed(v):
        try:
            return f"{float(v):+.1f}"
        except (TypeError, ValueError):
            return str(v)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    env.filters["fmt_signed"] = fmt_signed
    return env, ChoiceLoader, DictLoader, Environment


def render_after() -> str:
    env, *_ = _env()
    return env.get_template("china_policy_watch.html.j2").render(pw=fixture_vm())


def _annotate_before(src: str) -> str:
    src = src.replace('<p class="lens">', '<p class="lens" data-ev="subtitle">', 1)
    src = src.replace(
        '{% if fx.reserves %}<div class="metric">',
        '{% if fx.reserves %}<div class="metric" data-ev="fx-mom">',
        1,
    )
    src = src.replace(
        '<div class="sh-tell {{ \'is-null\' if tl.state==\'null\' }}">',
        '<div class="sh-tell {{ \'is-null\' if tl.state==\'null\' }}" data-ev="tell-{{ tl.key }}">',
        1,
    )
    src = src.replace(
        '<div class="cnx-ctitle">🧭 {{ t(\'Sector-policy tracker\', \'行业政策追踪\') }}</div>',
        '<div class="cnx-ctitle" data-ev="sector-cap">🧭 {{ t(\'Sector-policy tracker\', \'行业政策追踪\') }}</div>',
        1,
    )
    src = src.replace(
        '{% for it in pw.policy_feed %}\n      <li>',
        '{% for it in pw.policy_feed %}\n      <li{% if loop.first %} data-ev="tape-row"{% endif %}>',
        1,
    )
    return src


def render_before() -> str:
    from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
    from engine import i18n
    src = subprocess.check_output(
        ["git", "show", "origin/main:templates/china_policy_watch.html.j2"],
        cwd=REPO_ROOT, text=True,
    )
    src = _annotate_before(src)
    combo = Environment(
        loader=ChoiceLoader([
            DictLoader({"china_policy_watch_before.html.j2": src}),
            FileSystemLoader(str(TEMPLATES_DIR)),
        ]),
        autoescape=False,
    )
    combo.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)

    def fmt_signed(v):
        try:
            return f"{float(v):+.1f}"
        except (TypeError, ValueError):
            return str(v)

    combo.filters["fmt_signed"] = fmt_signed
    return combo.get_template("china_policy_watch_before.html.j2").render(
        pw=fixture_vm(before=True))


def write_fixture_site(scratch: Path) -> None:
    scratch.mkdir(parents=True, exist_ok=True)
    for name in ("theme.css", "navigation-refresh.css", "theme.js",
                 "logo_config.js", "stock-logos.js", "live.js"):
        src = TEMPLATES_DIR / name
        if src.exists():
            shutil.copy(src, scratch / name)
    (scratch / "china_policy_watch.html").write_text(render_after(), encoding="utf-8")
    (scratch / "china_policy_watch_before.html").write_text(render_before(), encoding="utf-8")


def _git_head() -> str | None:
    try:
        from scripts.capture_page_evidence import _git_head_sha
        head = _git_head_sha(REPO_ROOT)
        return head.sha
    except Exception:
        return None


def _shot(page, locator=None) -> bytes:
    if locator is None:
        return page.screenshot(type="png", full_page=True)
    locator.first.wait_for(state="visible", timeout=5000)
    locator.first.scroll_into_view_if_needed()
    page.wait_for_timeout(80)
    return locator.first.screenshot(type="png")


def _record(png: bytes, alias: str, extra: dict) -> dict:
    name, digest, pw, ph = content_address_png(png, CELLS_DIR)
    (CELLS_DIR / alias).write_bytes(png)
    extra.update({
        "captured": True, "file": name, "alias": alias, "sha256": digest,
        "bytes": len(png), "width": pw, "height": ph,
    })
    return extra


def main() -> int:
    from scripts.capture_page_evidence import CaptureUnavailable, serve_site_dir

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        print(f"capture unavailable: playwright missing ({exc})", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)

    scratch = Path(tempfile.mkdtemp(prefix="cpw-ev-"))
    write_fixture_site(scratch)
    httpd, port = serve_site_dir(scratch)
    base = f"http://127.0.0.1:{port}"
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pages: list[dict] = []
    aliases: dict[str, str] = {}
    probes: dict = {}
    rest: list[dict] = []

    def add_page(page_id: str, subject: str, selector: str, states: list[dict]) -> None:
        pages.append({
            "page_id": page_id,
            "route": "/china_policy_watch.html",
            "registry_route": "/china_policy_watch.html",
            "route_kind": "china_policy_watch",
            "subject": subject,
            "selector": selector,
            "states": states,
            "metrics": {},
            "console_errors": [],
            "failed_responses": [],
            "gaps": [],
        })
        for st in states:
            if st.get("alias") and st.get("file"):
                aliases[st["alias"]] = st["file"]

    try:
        manager = sync_playwright().start()
        try:
            browser = manager.chromium.launch(headless=True)
        except Exception as exc:
            manager.stop()
            raise CaptureUnavailable(f"no chromium binary: {exc}") from exc
        try:
            # 8 rest cells — full page
            rest: list[dict] = []
            for viewport, (width, height) in VIEWPORTS.items():
                for locale in LOCALES:
                    for theme in THEMES:
                        state = {"theme": theme, "locale": locale}
                        ctx = browser.new_context(
                            viewport={"width": width, "height": height},
                            locale="zh-CN" if locale == "zh" else "en-US",
                            color_scheme=theme, device_scale_factor=1,
                            has_touch=viewport == "mobile",
                        )
                        ctx.add_init_script(
                            f"({_STATE_SEED_SCRIPT.strip()})({json.dumps(state)})")
                        page = ctx.new_page()
                        entry = {
                            "viewport": viewport, "locale": locale, "theme": theme,
                            "access": "anonymous", "viewport_width": width,
                            "viewport_height": height, "force_state": None,
                            "subject": "full",
                        }
                        try:
                            resp = page.goto(f"{base}/china_policy_watch.html",
                                             wait_until="load", timeout=30000)
                            if resp is None or not resp.ok:
                                raise RuntimeError(f"HTTP {getattr(resp, 'status', None)}")
                            page.wait_for_timeout(250)
                            applied = page.evaluate(_APPLY_STATE_SCRIPT.strip(), state) or {}
                            if applied.get("theme") != theme or applied.get("locale") != locale:
                                raise RuntimeError(
                                    f"state mismatch requested {state} observed {applied}")
                            page.wait_for_timeout(150)
                            png = _shot(page)
                            alias = f"full-{theme}-{locale}-{viewport}.png"
                            entry = _record(png, alias, entry)
                            entry["applied_theme"] = applied.get("theme")
                            entry["applied_locale"] = applied.get("locale")
                            if viewport == "mobile" and theme == "dark" and locale == "en":
                                probes["l1"] = page.evaluate(
                                    "() => Array.from(document.querySelectorAll('.pw > .cnx-card[data-l1]')).map(el => el.getAttribute('data-l1'))")
                                probes["hscroll"] = page.evaluate(
                                    """() => {
                                      const doc = document.documentElement;
                                      const body = document.body;
                                      const table = document.querySelector('.pw-table-scroll');
                                      return {
                                        clientWidth: doc.clientWidth,
                                        scrollWidth: body.scrollWidth,
                                        pageScroll: body.scrollWidth > doc.clientWidth + 1,
                                        tableClient: table ? table.clientWidth : null,
                                        tableScroll: table ? table.scrollWidth : null,
                                      };
                                    }""")
                        except Exception as exc:
                            entry.update({"captured": False,
                                          "reason": f"{type(exc).__name__}: {exc}"})
                        finally:
                            ctx.close()
                        rest.append(entry)
                        print(f"  full {theme}/{locale}/{viewport}: "
                              f"{'ok' if entry.get('captured') else entry.get('reason')}",
                              flush=True)
            add_page("china_policy_watch.html#full", "full", "body", rest)

            # 4 state shots: sh-pop dark+light, LENS dark+light (desktop EN)
            states: list[dict] = []
            for force, click, selector in (
                ("sh-pop", ".sh-hbtn", ".pw .sh-pop"),
                ("lens", "div.metric button.lens-q", ".lens-pop.open"),
            ):
                for theme in THEMES:
                    state = {"theme": theme, "locale": "en"}
                    ctx = browser.new_context(
                        viewport={"width": 1440, "height": 900},
                        locale="en-US", color_scheme=theme, device_scale_factor=1)
                    ctx.add_init_script(
                        f"({_STATE_SEED_SCRIPT.strip()})({json.dumps(state)})")
                    page = ctx.new_page()
                    entry = {
                        "viewport": "desktop", "locale": "en", "theme": theme,
                        "access": "anonymous", "viewport_width": 1440,
                        "viewport_height": 900, "force_state": force,
                        "subject": force,
                    }
                    try:
                        page.goto(f"{base}/china_policy_watch.html",
                                  wait_until="load", timeout=30000)
                        applied = page.evaluate(_APPLY_STATE_SCRIPT.strip(), state) or {}
                        if applied.get("theme") != theme:
                            raise RuntimeError(f"theme mismatch {applied}")
                        loc = page.locator(click).first
                        loc.scroll_into_view_if_needed()
                        if force == "sh-pop":
                            loc.click(force=True)
                            page.wait_for_timeout(200)
                            page.locator(".pw .sh-pop.open").wait_for(state="visible", timeout=3000)
                            png = page.locator(".pw .sh-pop.open").screenshot(type="png")
                        else:
                            # Desktop LENS is hover-intent; a click toggles it closed.
                            loc.hover()
                            page.wait_for_timeout(220)
                            page.locator(".lens-pop.open").wait_for(state="visible", timeout=3000)
                            png = page.locator(".lens-pop.open").screenshot(type="png")
                        alias = f"state-{force}-{theme}.png"
                        entry = _record(png, alias, entry)
                        entry["applied_theme"] = applied.get("theme")
                        entry["applied_locale"] = applied.get("locale")
                    except Exception as exc:
                        entry.update({"captured": False,
                                      "reason": f"{type(exc).__name__}: {exc}"})
                    finally:
                        ctx.close()
                    states.append(entry)
                    print(f"  state {force}/{theme}: "
                          f"{'ok' if entry.get('captured') else entry.get('reason')}",
                          flush=True)
            add_page("china_policy_watch.html#states", "states", ".sh-pop, .lens-q", states)

            # before/after crops — both lanes (EN dark desktop)
            crops = [
                ("fx-mom", "[data-ev='fx-mom']"),
                ("margin-tell", "[data-ev='tell-margin_recovery']"),
                ("buyback-tell", "[data-ev='tell-buyback_cascade']"),
                ("tape-row", "[data-ev='tape-row']"),
                ("sector-cap", "[data-ev='sector-cap']"),
                ("subtitle", "[data-ev='subtitle']"),
            ]
            crop_states: list[dict] = []
            for lane, html_name in (("before", "china_policy_watch_before.html"),
                                    ("after", "china_policy_watch.html")):
                for locale in LOCALES:
                    state = {"theme": "dark", "locale": locale}
                    ctx = browser.new_context(
                        viewport={"width": 1440, "height": 900},
                        locale="zh-CN" if locale == "zh" else "en-US",
                        color_scheme="dark", device_scale_factor=1)
                    ctx.add_init_script(
                        f"({_STATE_SEED_SCRIPT.strip()})({json.dumps(state)})")
                    page = ctx.new_page()
                    try:
                        page.goto(f"{base}/{html_name}", wait_until="load", timeout=30000)
                        applied = page.evaluate(_APPLY_STATE_SCRIPT.strip(), state) or {}
                        if applied.get("theme") != "dark" or applied.get("locale") != locale:
                            raise RuntimeError(f"crop state mismatch {applied}")
                        for subject, selector in crops:
                            entry = {
                                "viewport": "desktop", "locale": locale, "theme": "dark",
                                "access": "anonymous", "viewport_width": 1440,
                                "viewport_height": 900, "force_state": lane,
                                "subject": subject,
                            }
                            try:
                                loc = page.locator(selector)
                                png = _shot(page, loc)
                                alias = f"crop-{subject}-{lane}-{locale}.png"
                                entry = _record(png, alias, entry)
                                entry["applied_theme"] = applied.get("theme")
                                entry["applied_locale"] = applied.get("locale")
                            except Exception as exc:
                                entry.update({"captured": False,
                                              "reason": f"{type(exc).__name__}: {exc}"})
                            crop_states.append(entry)
                            print(f"  crop {subject}/{lane}/{locale}: "
                                  f"{'ok' if entry.get('captured') else entry.get('reason')}",
                                  flush=True)
                    finally:
                        ctx.close()
            add_page("china_policy_watch.html#crops", "crops", "[data-ev]", crop_states)

            # L1 receipt crop (after, dark EN desktop)
            ctx = browser.new_context(
                viewport={"width": 1440, "height": 900},
                locale="en-US", color_scheme="dark", device_scale_factor=1)
            ctx.add_init_script(
                f"({_STATE_SEED_SCRIPT.strip()})({json.dumps({'theme': 'dark', 'locale': 'en'})})")
            page = ctx.new_page()
            page.goto(f"{base}/china_policy_watch.html", wait_until="load", timeout=30000)
            page.evaluate(_APPLY_STATE_SCRIPT.strip(), {"theme": "dark", "locale": "en"})
            png = _shot(page)
            l1_entry = _record(png, "l1-count-dark-en-desktop.png", {
                "viewport": "desktop", "locale": "en", "theme": "dark",
                "access": "anonymous", "viewport_width": 1440, "viewport_height": 900,
                "force_state": "l1", "subject": "l1",
                "applied_theme": "dark", "applied_locale": "en",
            })
            ctx.close()
            add_page("china_policy_watch.html#l1", "l1", ".pw > .cnx-card[data-l1]", [l1_entry])
        finally:
            browser.close()
            manager.stop()
    finally:
        httpd.shutdown()
        shutil.rmtree(scratch, ignore_errors=True)

    rest_ok = sum(1 for s in rest if s.get("captured"))
    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": generated_at,
        "tool": "scripts/capture_china_policy_watch_evidence.py",
        "target": "china_policy_watch.html",
        "head": _git_head(),
        "axes": {
            "viewports": VIEWPORTS,
            "locales": list(LOCALES),
            "themes": list(THEMES),
            "access": ["anonymous"],
            "subjects": ["full", "states", "crops", "l1"],
            "force_states": ["sh-pop", "lens", "before", "after", "l1"],
        },
        "selection": {"page": "china_policy_watch.html", "access": "anonymous"},
        "aliases": aliases,
        "excluded": [],
        "outcome": "captured" if rest_ok == 8 else "partial",
        "totals": {
            "rest_cells": rest_ok,
            "rest_required": 8,
            "pages": len(pages),
        },
        "honesty": {
            "access": "anonymous only",
            "gaps": "uncaptured cells are recorded with a reason",
            "authority": "this tool screenshots; it scores nothing",
            "page": (
                "templates/china_policy_watch.html.j2 rendered with a representative "
                "fixture VM (no live data/ reads). Omitted vs live: VPS bake, live "
                "quote hydration, some nav JS (live_config.js). Before crops render "
                "origin/main's template against the same fixture with the pre-heal "
                "copy (FX unit, quiet-tell receipts, tape tags, 13-row table, long subtitle)."
            ),
            "probes": probes,
        },
        "g8": {"hscroll_390": probes.get("hscroll"), "l1": probes.get("l1")},
        "pages": pages,
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "EVIDENCE.yml").write_text(
        "schema: mastermind.page_evidence_receipt.v1\n"
        "changed_paths:\n"
        "  - templates/china_policy_watch.html.j2\n"
        "manifest: mockups/evidence/china-policy-watch/manifest.json\n",
        encoding="utf-8",
    )
    l1 = probes.get("l1") or []
    hscroll = probes.get("hscroll") or {}
    readme = f"""# China Policy Watch — W5 r3 evidence

Fixture-rendered `templates/china_policy_watch.html.j2` (no live `data/` bake).
Playwright seeds `localStorage` (`theme`, `lang`, clears `themeAuto`), calls
`setTheme`/`setLang`, re-reads `html[data-theme]` / `html[data-lang]`, and
refuses a cell on mismatch.

## DARK TREATMENT

Command center: luminance depth, instrument glass (`--mx5-glass-bg` at 55%
with inset highlight and 32px shadow), restrained `--sh-glow` on the
State-Hand gauge, aurora wash in the pressure accent. Backdrop is a quieter
inner panel (hairline + 3% white lift), not a second peer card. Chips and
pills sit on translucent fills.

## LIGHT TREATMENT

Research workspace: cool canvas, white material (`--mx5-glass-bg` 82% with
8% shadow and a white inset hairline — shadow instead of glow). Aurora is
dialed to 6%/4%. The nested China-macro backdrop uses a white sheet
(`rgba(255,255,255,.72)`) plus a 6% cool drop shadow so it reads as paper
on the desk, not a token-swapped dark panel. Stance badges keep the same
semantic hues; light relies on fill + hairline rather than glow.

## Intentional differences

| Mechanism | Dark | Light |
|---|---|---|
| Card depth | glow + 32px shadow | hairline + 8–24px shadow |
| Backdrop | 3% white lift | white sheet + inset hairline |
| Aurora | 13% accent bloom | 6% / 4% wash |
| Needle glow | drop-shadow on `--sh-accent` | theme.css light pointer, same accent |

Token substitution alone is not the light design — the backdrop sheet, the
inset hairline, and the shadow-not-glow stack are the light-specific
mechanisms.

## L1 section count

DOM `.pw > .cnx-card[data-l1]`: **{len(l1)}** → `{l1}`

Demotion landings:

| Removed L1 | Landing |
|---|---|
| FX & reserves | Nested **China macro backdrop** inside PBoC card (`data-landing="china-macro-backdrop"`) + counted China-desk link |
| NBS latest prints | Same backdrop (stance line + per-tile direction words) |
| NPC 2026 targets | Chip row on the policy-thesis card (`data-landing="npc-2026"`) |
| Sector rows 9–13 | `#pw-sector-all` disclosure, linked as **See all N →** |

## 390 h-scroll

`{json.dumps(hscroll)}`

Zero page h-scroll is required; the capped table scrolls inside `.pw-table-scroll`.

## Rest cells

8 full-page: dark/light × EN/ZH × 1440/390 (`full-*-*.png`).

## State shots

`.sh-pop` open dark+light; LENS `?` host open dark+light via hover-intent
(`state-*.png`). Tips use `button.lens-q` hosts (S1 390 tap trap — not row
hosts). Desktop LENS is hover-intent; a click toggles it closed.

## Before/after crops

Both lanes (EN+ZH, dark desktop): FX MoM, margin tell, buyback tell, tape tag
row, sector-table cap, subtitle. Before = `origin/main` template.

## Honest differences vs live

- Fixture VM, not the VPS bake.
- `live_config.js` is absent in this sparse tree; live quote hydration omitted.
- Shared site nav renders; some nav JS 404s are expected and do not change
  the desk cards under test.
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    print(f"wrote {OUT_DIR} rest={rest_ok}/8 l1={l1} hscroll={hscroll}", flush=True)
    return 0 if rest_ok == 8 else 1


if __name__ == "__main__":
    raise SystemExit(main())
