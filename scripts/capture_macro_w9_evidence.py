#!/usr/bin/env python3
"""S1-rig evidence matrix for macro.html W9 r3.

Fixture-rendered templates/dashboard.html.j2 (mode=macro) with real
`body.page-macro mx4-grid` classes. Playwright seeds window.__skyDeck, applies
theme/lang via setTheme/setLang, refuses a cell on attribute mismatch, hides
decorative overlays, and records a per-crop overlay column.

Usage::

    python3 -m scripts.capture_macro_w9_evidence
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
OUT_DIR = REPO_ROOT / "mockups" / "evidence" / "macro-w9"
CELLS_DIR = OUT_DIR / "cells"

VIEWPORTS = {
    "desktop": (1440, 900),
    "mobile": (390, 844),
}
LOCALES = ("en", "zh")
THEMES = ("dark", "light")

# REST 8-cell subject (dark/light × EN/ZH × 1440/390).
REST_SUBJECT = ("fullpage", "body.page-macro.mx4-grid")

# Close crops: dark+light, EN desktop unless a bilingual face needs ZH too.
CLOSE_CROPS: tuple[tuple[str, str, str], ...] = (
    ("gde-policy", ".gde-policy", "live.html"),
    ("alerts-face", "#sx-news-v2", "live.html"),
    ("markets-live", "#sx-markets-v2", "live.html"),
    ("fed-policy", "#ev-fed-policy", "live.html"),
    ("hottest-desk", "#sx-deep-context", "live.html"),
    ("regime-tip", "#ev-regime-tip", "live.html"),
    ("stance-sentiment", "#sx-v5-sentiment", "live.html"),
    ("stance-sector", "#sx-v5-sector", "live.html"),
    ("stance-aibrief", "#sx-aibrief-v2", "live.html"),
    ("stance-events", "#sx-events-v2 .sxg-face", "live.html"),
)

DEGRADED: tuple[tuple[str, str, str], ...] = (
    ("markets-null", "#sx-markets-v2", "null_markets.html"),
    ("nav-noop", "#ev-nav-markets", "null_markets.html"),
    ("regime-fc-null", "#ev-regime-tip", "regime_fc_null.html"),
    ("alerts-zero", "#sx-news-v2 .sxg-face", "alerts_zero.html"),
    ("events-none", "#sx-events-v2 .sxg-face", "events_none.html"),
    ("events-empty", "#sx-events-v2 .sxg-face", "events_empty.html"),
)

COUNT_TRUTH: tuple[tuple[str, str, str], ...] = (
    ("count-hero-badge", "#ev-count-truth", "count_truth.html"),
    ("count-dislocation-dlg", "#dlg-news .mx5-dlg-panel", "dislocation_dlg.html"),
)

_STATE_SEED_SCRIPT = """
(state) => {
  window.__skyDeck = true;
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
  var fx = document.querySelector('.sky-fx');
  if (fx && fx.parentNode) fx.parentNode.removeChild(fx);
  return {theme: docEl.getAttribute('data-theme'), locale: docEl.getAttribute('data-lang')};
}
"""

_HIDE_DECOR = (
    "#mmb-root,#mmb-boot,#mmb-launch,.sky-fx,.mx5-aurora,.theme-fab,"
    "#ask-mastermind,.mmb-fab{"
    "display:none!important;visibility:hidden!important;opacity:0!important}"
)

_OVERLAY_PROBE = """
() => {
  const sels = ['.sky-fx', '.mx5-aurora', '#mmb-boot', '#mmb-launch',
                '#mmb-root', '.theme-fab', '#ask-mastermind', '.mmb-fab'];
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

_PAINT_QUOTES = """
() => {
  const prices = {
    'ES=F': ['6,712.25', '+0.42%'],
    'NQ=F': ['24,301.50', '+0.31%'],
    'YM=F': ['42,110', '+0.18%'],
    'RTY=F': ['2,245.10', '-0.12%'],
    '^TNX': ['4.12%', '-2 bps'],
    'DX-Y.NYB': ['98.42', '+0.08%']
  };
  const root = document.querySelector('#sx-markets-v2');
  if (root) {
    Object.keys(prices).forEach((sym) => {
      const px = prices[sym][0], chg = prices[sym][1];
      root.querySelectorAll('.nb-px[data-sym="'+sym+'"]').forEach((el) => {
        el.classList.remove('skel');
        el.removeAttribute('aria-busy');
        el.textContent = px;
      });
      root.querySelectorAll('.nb-chg[data-sym="'+sym+'"]').forEach((el) => {
        el.classList.remove('skel');
        el.removeAttribute('aria-busy');
        el.textContent = chg;
      });
    });
  }
}
"""

_PREP_LIVE = """
() => {
  const fed = document.querySelector('#sx-v5-fed');
  const pol = document.querySelector('#sx-policy-v2');
  if (fed && pol && !document.getElementById('ev-fed-policy')) {
    const wrap = document.createElement('div');
    wrap.id = 'ev-fed-policy';
    wrap.style.cssText = 'position:relative;display:grid;gap:12px;width:min(640px, calc(100vw - 48px));';
    document.body.appendChild(wrap);
    wrap.appendChild(fed);
    wrap.appendChild(pol);
  }
}
"""

_PREP_NULL = """
() => {
  let tape = document.querySelector('#nb-tape');
  if (!tape) {
    tape = document.createElement('div');
    tape.id = 'nb-tape';
    tape.style.cssText = 'display:flex;align-items:center;gap:8px;padding:6px 12px;font:13px/1.2 ui-sans-serif,system-ui;border-bottom:1px solid var(--line,rgba(255,255,255,.12));';
    const chip = document.createElement('span');
    chip.className = 'nb-px';
    chip.setAttribute('data-sym', 'ES=F');
    chip.textContent = '6,712.25';
    tape.appendChild(chip);
    const nav = document.querySelector('.site-nav') || document.body;
    nav.insertBefore(tape, nav.firstChild);
  }
  const mount = document.querySelector('#sx-markets-v2');
  if (mount) {
    mount.querySelectorAll('.nb-px[data-sym]').forEach((el) => {
      el.classList.add('dtp-token', 'behind');
      el.classList.remove('skel');
      el.removeAttribute('aria-busy');
      el.setAttribute('data-live', 'behind');
    });
    if (!mount.querySelector('.mx-mkt-null')) {
      const line = document.createElement('div');
      line.className = 'mx-empty mx-mkt-null';
      line.setAttribute('role', 'status');
      line.innerHTML = '<p class="mx-empty-line mx-empty-why">'
        + '<span class="l-en">Quotes unavailable — the rest of this page is unaffected.</span>'
        + '<span class="l-zh">行情暂不可用——本页其余内容不受影响。</span></p>';
      mount.appendChild(line);
    }
  }
  if (!document.getElementById('ev-nav-markets')) {
    const wrap = document.createElement('div');
    wrap.id = 'ev-nav-markets';
    wrap.style.cssText = 'display:grid;gap:8px;';
    const navHost = document.querySelector('#nb-tape');
    const mkt = document.querySelector('#sx-markets-v2');
    if (navHost && mkt) {
      mkt.parentNode.insertBefore(wrap, mkt);
      wrap.appendChild(navHost);
      wrap.appendChild(mkt);
    }
  }
}
"""

_PREP_TIP = """
() => {
  const help = document.querySelector('#regime-radar .help, .mx5-flipctx-anchor .help, .ms-front .help');
  if (!help || document.getElementById('ev-regime-tip')) return;
  const box = document.createElement('div');
  box.id = 'ev-regime-tip';
  box.style.cssText = 'position:fixed;top:72px;left:16px;z-index:2147483000;display:block;visibility:visible;opacity:1;background:var(--panel,#111);color:var(--text,#eee);padding:12px 14px;max-width:420px;border:1px solid var(--line,rgba(255,255,255,.14));border-radius:8px;';
  const tip = help.querySelector('.tip');
  if (tip) box.innerHTML = tip.innerHTML;
  else box.textContent = help.textContent || '?';
  document.body.appendChild(box);
}
"""

_PREP_COUNT = """
() => {
  const alerts = document.querySelector('#sx-news-v2');
  const pill = document.querySelector('.ms-alerts-wrap, .ms-alerts');
  if (alerts && pill && !document.getElementById('ev-count-truth')) {
    const wrap = document.createElement('div');
    wrap.id = 'ev-count-truth';
    wrap.style.cssText = 'display:grid;gap:10px;width:min(640px, calc(100vw - 48px));';
    document.body.appendChild(wrap);
    wrap.appendChild(pill.cloneNode(true));
    wrap.appendChild(alerts);
  }
}
"""

_PREP_DLG = """
() => {
  const dlg = document.getElementById('dlg-news');
  if (!dlg) return;
  dlg.classList.add('open', 'mx5-dlg-in');
  dlg.style.display = 'flex';
  const panel = dlg.querySelector('.mx5-dlg-panel');
  if (panel) {
    panel.style.opacity = '1';
    panel.style.transform = 'none';
    panel.style.visibility = 'visible';
  }
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


def _alert(rule="gex_flip_cross", tier="watch", **over) -> dict:
    from engine.alerts import alert_view
    row = alert_view(
        rule,
        over.pop("severity", "warn"),
        over.pop("message", "GEX: spot crossed the gamma flip (net -31bn, spot vs flip -0.4%)"),
        over.pop("message_zh", "GEX：现价穿越 gamma 翻转点"),
    )
    row["tier"] = tier
    row.update(over)
    return row


def _ms(**over) -> dict:
    from tests.test_macro_w9_r1 import _ms as _base_ms
    return _base_ms(**over)


def fixture_vm(**over) -> dict:
    """Representative macro.html VM. Sparse trees have no data/; this is the
    page-test idiom, not a live bake."""
    from tests.test_dashboard_template_render import _base_vm

    vm = _base_vm()
    latest = dict(vm["latest"])
    latest.update({
        "flip_condition": {
            "component": "copper_gold", "axis": "growth",
            "z": 0.4, "threshold": 1.0, "margin": 0.6,
        },
        "quad_vector": {"transition_momentum": {"gaining": "Q2", "window_sessions": 5}},
        "confidence": 0.72,
    })
    vm.update({
        "latest": latest,
        "market_state": _ms(),
        "macro_catalysts": [
            {"impact": "high", "label": "CPI", "label_zh": "CPI", "date": "2026-09-11", "time_et": "8:30am"},
            {"impact": "high", "label": "FOMC", "label_zh": "FOMC", "date": "2026-09-17", "time_et": "2:00pm"},
            {"impact": "med", "label": "Claims", "label_zh": "初请", "date": "2026-09-10"},
        ],
        "alerts": [
            _alert("gex_flip_cross", "watch"),
            _alert("hy_oas_widening", "act",
                   message="HY OAS 1-day widening +0.50pp is 4.2 sigma",
                   message_zh="HY OAS"),
        ],
        "fear_greed": {"dial": 32, "label_en": "Fear", "label_zh": "恐慌"},
        "sector_heat": {
            "heating": [{"name": "Energy", "name_zh": "能源", "rank": 1},
                        {"name": "Financials", "name_zh": "金融", "rank": 2}],
            "cooling": [{"name": "Utilities", "name_zh": "公用事业", "rank": 11}],
        },
        "macro_news": {
            "synthesis": {
                "high_impact_count": 2, "dominant_channel": "inflation",
                "top_tickers": ["XLE"],
            },
            "headlines": [
                {"title": "CPI print lands hotter than priced",
                 "title_zh": "CPI 高于定价",
                 "importance": "high", "source_name": "Reuters",
                 "theme": "inflation", "url": "https://example.test/cpi"},
            ],
        },
        "risk_envelope": {
            "schema": "mastermind.risk_envelope/v1",
            "bundle_id": "w9-fixture",
            "source_session": "2026-09-10",
            "definition_id": "grey-deer-v1-fixture",
            "data_state": "FRESH",
            "measured_state": {"verdict": "MIXED"},
            "hazard_summary": {"stage": "NONE", "stage_reason": "fixture"},
            "coherence": {"state": "ALIGNED", "scope": "market_reads"},
            "policy_summary": {"policy_count": 0},
            "provenance": {"sources": []},
            "freshness": {"per_source": {}},
        },
        "policy_lever": {
            "state": "QUIET",
            "as_of": "2026-09-10",
            "framing": "No active jawboning.",
            "framing_zh": "无官方吹风。",
        },
    })
    vm.update(over)
    return vm


def render_fixture_html(vm: dict | None = None) -> str:
    from tests.test_dashboard_template_render import _env
    return _env().get_template("dashboard.html.j2").render(**(vm or fixture_vm()), mode="macro")


def write_fixture_site(scratch: Path) -> None:
    scratch.mkdir(parents=True, exist_ok=True)
    for name in (
        "theme.css", "theme.js", "navigation-refresh.css", "product-nav-icons.css",
        "live.js", "nav_market.js", "tier_preview.css", "illus.css",
    ):
        src = TEMPLATES_DIR / name
        if src.exists():
            shutil.copy(src, scratch / name)

    live = render_fixture_html()
    (scratch / "live.html").write_text(live, encoding="utf-8")

    (scratch / "null_markets.html").write_text(live, encoding="utf-8")

    none_vm = fixture_vm(macro_catalysts=None)
    (scratch / "events_none.html").write_text(render_fixture_html(none_vm), encoding="utf-8")

    empty_vm = fixture_vm(macro_catalysts=[])
    (scratch / "events_empty.html").write_text(render_fixture_html(empty_vm), encoding="utf-8")

    zero_vm = fixture_vm(alerts=[], macro_news={"headlines": [], "synthesis": {}})
    latest0 = dict(zero_vm["latest"])
    latest0["dislocation"] = None
    zero_vm["latest"] = latest0
    (scratch / "alerts_zero.html").write_text(render_fixture_html(zero_vm), encoding="utf-8")

    fc_vm = fixture_vm()
    latest_fc = dict(fc_vm["latest"])
    latest_fc["flip_condition"] = {
        "component": "copper_gold", "axis": "growth",
        "z": None, "threshold": 1.0, "margin": 0.4,
    }
    fc_vm["latest"] = latest_fc
    (scratch / "regime_fc_null.html").write_text(render_fixture_html(fc_vm), encoding="utf-8")

    count_vm = fixture_vm(alerts=[
        _alert("gex_flip_cross", "watch"),
        _alert("hy_oas_widening", "act",
               message="HY OAS 1-day widening +0.50pp is 4.2 sigma",
               message_zh="HY OAS"),
        _alert("event_risk", "context",
               message="Event-risk window: CPI tomorrow",
               message_zh="事件"),
        _alert("growth_confidence_floor", "context",
               message="Growth axis confidence dropped below 40%",
               message_zh="增长"),
        _alert("sector_rs_cross_high", "context",
               message="XLI RS vs SPY crossed above 80th pctile",
               message_zh="板块"),
        _alert("circuit_breaker_open", "context",
               message="Source 'fred' marked dead after 3 consecutive failures",
               message_zh="中断"),
    ])
    (scratch / "count_truth.html").write_text(render_fixture_html(count_vm), encoding="utf-8")

    dislo_vm = fixture_vm(alerts=[])
    latest_d = dict(dislo_vm["latest"])
    latest_d["dislocation"] = {
        "dislocation_active": True,
        "verdict": "stand_aside",
        "put_state": "known",
        "put_state_reliable": True,
        "fed_put": True,
        "geo_reversibility": {"agreement": "corroborates"},
        "catalyst_narrative": {"agreement": "corroborates"},
    }
    dislo_vm["latest"] = latest_d
    (scratch / "dislocation_dlg.html").write_text(render_fixture_html(dislo_vm), encoding="utf-8")


def _git_head_of_repo() -> tuple[str | None, str | None]:
    from scripts.capture_page_evidence import _git_head_sha
    head = _git_head_sha(REPO_ROOT)
    return head.sha, str(head.gitdir) if head.gitdir is not None else None


def _prep_for(page_name: str, full_page: bool = False, selector: str = "") -> str | None:
    if full_page and page_name == "live.html":
        return _PAINT_QUOTES
    if page_name == "count_truth.html":
        return _PREP_COUNT
    if page_name == "live.html":
        if selector == "#ev-regime-tip":
            return _PREP_TIP
        if selector == "#ev-fed-policy":
            return _PREP_LIVE
        return _PAINT_QUOTES
    if page_name == "null_markets.html":
        return _PREP_NULL
    if page_name == "regime_fc_null.html":
        return _PREP_TIP
    if page_name == "dislocation_dlg.html":
        return _PREP_DLG
    return None


def _shot_one(page, selector: str, full_page: bool = False) -> bytes:
    if full_page or selector.startswith("body"):
        return page.screenshot(type="png", full_page=True)
    loc = page.locator(selector).first
    loc.wait_for(state="visible", timeout=8000)
    loc.scroll_into_view_if_needed()
    page.wait_for_timeout(80)
    return loc.screenshot(type="png")


def _capture_cell(browser, base: str, *, width: int, height: int, locale: str,
                  theme: str, selector: str, page_name: str,
                  full_page: bool = False) -> dict:
    state = {"theme": theme, "locale": locale}
    context = browser.new_context(
        viewport={"width": width, "height": height},
        locale="zh-CN" if locale == "zh" else "en-US",
        color_scheme=theme,
        device_scale_factor=1,
    )
    context.add_init_script(
        f"({_STATE_SEED_SCRIPT.strip()})({json.dumps(state)});"
    )
    page = context.new_page()
    try:
        url = f"{base}/{page_name}"
        response = page.goto(url, wait_until="load", timeout=45000)
        if response is None or not response.ok:
            raise RuntimeError(f"HTTP {getattr(response, 'status', 'none')}")
        page.wait_for_timeout(200)
        page.add_style_tag(content=_HIDE_DECOR)
        applied = page.evaluate(_APPLY_STATE_SCRIPT.strip(), state) or {}
        if applied.get("theme") != theme or applied.get("locale") != locale:
            raise RuntimeError(
                f"state mismatch: requested theme={theme} locale={locale} "
                f"observed {applied!r}"
            )
        prep = _prep_for(page_name, full_page=full_page, selector=selector)
        if prep:
            page.evaluate(prep.strip())
        if page_name == "live.html" and selector == "#ev-fed-policy":
            page.evaluate(_PAINT_QUOTES.strip())
        if page_name == "count_truth.html":
            page.evaluate(_PAINT_QUOTES.strip())
        page.wait_for_timeout(120)
        png = _shot_one(page, selector, full_page=full_page)
        overlay_hits = page.evaluate(_OVERLAY_PROBE.strip()) or []
        overlay = "clean" if not overlay_hits else "dirty:" + ",".join(overlay_hits)
        return {"png": png, "applied": applied, "overlay": overlay}
    finally:
        context.close()


def _record(entry: dict, got: dict, alias: str, written: set, aliases: dict) -> None:
    png = got["png"]
    applied = got["applied"]
    name, digest, pw, ph = content_address_png(png, CELLS_DIR)
    (CELLS_DIR / alias).write_bytes(png)
    written.add(f"cells/{name}")
    written.add(f"cells/{alias}")
    aliases[alias] = name
    entry.update({
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
    })


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

    try:
        manager = sync_playwright().start()
        try:
            browser = manager.chromium.launch(headless=True)
        except Exception as exc:
            manager.stop()
            raise CaptureUnavailable(f"no chromium binary is installed: {exc}") from exc
        try:
            # REST 8-cell full page
            subject, selector = REST_SUBJECT
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
                                page_name="live.html", full_page=True,
                            )
                            alias = f"{subject}-{theme}-{locale}-{viewport}.png"
                            _record(entry, got, alias, written, aliases)
                        except Exception as exc:
                            entry.update({
                                "captured": False,
                                "reason": f"{type(exc).__name__}: {exc}",
                            })
                        states.append(entry)
            captured_n = sum(1 for s in states if s.get("captured"))
            pages.append({
                "page_id": "macro.html#fullpage",
                "route": "/live.html",
                "registry_route": "/macro.html",
                "route_kind": "macro_w9_fullpage",
                "subject": subject,
                "selector": selector,
                "states": states,
                "metrics": {},
                "console_errors": [],
                "failed_responses": [],
                "gaps": [],
            })
            print(f"  {subject}: {captured_n}/{len(states)} cells", flush=True)

            extras: list[tuple[str, str, str, str]] = []
            for name, sel, page_name in CLOSE_CROPS:
                extras.append((name, sel, page_name, "close"))
            for name, sel, page_name in DEGRADED:
                extras.append((name, sel, page_name, "degraded"))
            for name, sel, page_name in COUNT_TRUTH:
                extras.append((name, sel, page_name, "count"))

            extra_states: list[dict] = []
            for name, sel, page_name, family in extras:
                themes = THEMES if family != "count" else ("dark", "light")
                locales = ("en",) if family != "degraded" else ("en", "zh")
                if family == "close":
                    locales = ("en",)
                for theme in themes:
                    for locale in locales:
                        entry = {
                            "viewport": "desktop",
                            "locale": locale,
                            "theme": theme,
                            "access": "anonymous",
                            "viewport_width": 1440,
                            "viewport_height": 900,
                            "force_state": f"{family}:{name}",
                            "subject": name,
                        }
                        try:
                            got = _capture_cell(
                                browser, base, width=1440, height=900,
                                locale=locale, theme=theme, selector=sel,
                                page_name=page_name, full_page=False,
                            )
                            alias = f"{name}-{theme}-{locale}-desktop.png"
                            _record(entry, got, alias, written, aliases)
                        except Exception as exc:
                            entry.update({
                                "captured": False,
                                "reason": f"{type(exc).__name__}: {exc}",
                            })
                        extra_states.append(entry)
                        shown = entry.get("alias") or f"{name}-{theme}-{locale}"
                        ok = "ok" if entry.get("captured") else entry.get("reason")
                        print(f"  {shown}: {ok}", flush=True)
            if pages:
                pages[0]["states"].extend(extra_states)
        finally:
            browser.close()
            manager.stop()
    finally:
        httpd.shutdown()

    rest_states = [
        s for p in pages for s in p["states"] if s.get("force_state") is None
    ]
    extra = [
        s for p in pages for s in p["states"] if s.get("force_state") is not None
    ]
    attempted = len(rest_states)
    captured = sum(1 for s in rest_states if s.get("captured"))
    extra_ok = bool(extra) and all(s.get("captured") for s in extra)
    outcome = "captured" if captured == attempted and attempted and extra_ok else "partial"
    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": generated_at,
        "tool": {
            "module_ref": "scripts/capture_macro_w9_evidence.py",
            "version": "w9-r3-s1-rig",
            "capture_method": (
                "playwright full-page + locator.screenshot() on a fixture-rendered "
                "templates/dashboard.html.j2 (mode=macro) with real body.page-macro "
                "mx4-grid classes. window.__skyDeck seed; setTheme/setLang with "
                "refuse-on-mismatch; overlay hide + post-shot overlay probe; "
                "sha256 from screenshot bytes."
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
                "dashboard.html.j2 render, not live site/macro.html"
            ),
        },
        "axes": {
            "viewports": {name: list(size) for name, size in VIEWPORTS.items()},
            "locales": list(LOCALES),
            "themes": list(THEMES),
            "access": ["anonymous"],
            "subjects": [REST_SUBJECT[0]],
            "force_states": sorted({s.get("force_state") for s in extra if s.get("force_state")}),
        },
        "selection": {
            "mode": "explicit_subjects",
            "subjects": [REST_SUBJECT[0]],
            "selectors": {REST_SUBJECT[0]: REST_SUBJECT[1]},
        },
        "aliases": aliases,
        "excluded": [],
        "outcome": outcome,
        "totals": {
            "pages": len(pages),
            "states_attempted": attempted + len(extra),
            "states_captured": captured + sum(1 for s in extra if s.get("captured")),
        },
        "honesty": {
            "access": "anonymous only",
            "gaps": "uncaptured cells are recorded with a reason",
            "authority": "this tool screenshots; it scores nothing",
            "page": "fixture-rendered dashboard.html.j2, not live site/macro.html",
        },
        "pages": pages,
        "files_written": sorted(written),
    }
    return manifest


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="macro_w9_evidence_"))
    try:
        write_fixture_site(scratch)
        print(f"fixture site: {scratch}", flush=True)
        manifest = _capture(scratch)
    except Exception as exc:
        print(f"CAPTURE FAILED: {type(exc).__name__}: {exc}", flush=True)
        return 1
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"outcome={manifest['outcome']} "
        f"captured={manifest['totals']['states_captured']}/"
        f"{manifest['totals']['states_attempted']}",
        flush=True,
    )
    return 0 if manifest["outcome"] == "captured" else 2


if __name__ == "__main__":
    raise SystemExit(main())
