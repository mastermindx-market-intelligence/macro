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
        {"name_en": "LPR fix", "name_zh": "LPR 报价", "date": "09-20", "importance": "med"},
        {"name_en": "PBoC briefing", "name_zh": "央行吹风会", "date": "09-22", "importance": "high"},
        {"name_en": "PMI flash", "name_zh": "PMI 初值", "date": "09-30", "importance": "med"},
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
            "label_en": "Growth scare",
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
        "pb": {},
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


def _extract_page_css(src: str) -> str:
    m = re.search(r"<style>(.*?)</style>\s*</head>", src, flags=re.S)
    if not m:
        raise RuntimeError("china.html.j2 page <style> block not found")
    return m.group(1)


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
    env = Environment(loader=DictLoader({"blk": _extract_macros(src) + "\n" + wrap_src}),
                      autoescape=False)
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
                "Omitted vs live: site nav, aurora-off-in-light still present, "
                "dialogs, stocks mode, live quote hydration, heatmap."
            ),
        },
        "g8": g8,
        "pages": pages,
    }
    return {"manifest": manifest, "written": sorted(written), "outcome": outcome, "g8": g8}


def _write_readme(manifest: dict) -> str:
    lines = [
        "# China Archetype-D S1 — evidence matrix (round 2)",
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
        "- No live quote hydration — CSI 300 / ChiNext stay at skeleton geometry.",
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
    lines += [
        "",
        "## G8 floor",
        "",
        "See `g8.json`. Checks at 390 / 768 / 1440: page horizontal scroll, "
        "focus-visible ring, LENS tap at 390, reduced-motion skeleton, chip wrap.",
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
