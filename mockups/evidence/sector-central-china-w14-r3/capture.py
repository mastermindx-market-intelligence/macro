#!/usr/bin/env python3
"""S1-rig evidence matrix for sector_central_china W14 r3 (closing round).

Fixture-rendered page (sparse trees have no site/), real body.page-sector-central
classes, Playwright, __skyDeck seed, overlay hide + overlay probe column,
reduced-motion, computed-style text. Refuses a dirty tracked tree and stamps
`git rev-parse HEAD` at capture time so a working-tree edit cannot wear a
prior committed sha.

Recapture (porcelain-empty tracked tree required):

    python3 mockups/evidence/sector-central-china-w14-r3/capture.py
"""
from __future__ import annotations

import hashlib
import http.server
import json
import random
import shutil
import socketserver
import struct
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
R2 = ROOT / "mockups" / "evidence" / "sector-central-china-w14-r2"

OVERLAY_SELECTORS = (
    ".rvx-aurora",
    ".mx5-aurora",
    ".sky-fx",
    "#mmb-root",
    "#mmb-boot",
    ".aurora",
)
ASSETS = (
    "theme.css",
    "theme.js",
    "product-nav-icons.css",
    "dashboard-icons.css",
    "dashboard-icons.js",
    "navigation-refresh.css",
    "nav_market.js",
    "data_base.js",
    "live.js",
    "baskets_desk.js",
    "lightweight-charts.js",
    "sector_cycles.css",
    "si_workspace_china.js",
)
VIEWPORTS = {
    "desktop": (1440, 900),
    "mobile": (390, 844),
}

# ---------------------------------------------------------------------------
# Art direction + §9.13 landing table (written into README at capture time)
# ---------------------------------------------------------------------------

DARK_TREATMENT = (
    "Command center. Luminance tiles (`--panel` / `--panel2`) on a deep canvas, "
    "hairline `--line`, instrument-calm, no glow. `.si-links` is one family of "
    "tagged chips on `--panel2`; `.skel-slot` is a quiet `--panel2` shimmer; "
    "`.mx-error button` is a `--panel2` chip. The Act-Now board and Explore "
    "table sit as inset instruments, not cards with drop shadow."
)
LIGHT_TREATMENT = (
    "Research workspace. White `--panel` paper, hairline `--line`, short cool "
    "shadow instead of glow. `.si-links a` pick up the desk-tile shadow already "
    "used by `.rvx-hero`; `.skel-slot` shimmer mixes `--text` into `--panel` "
    "(paper, not a dark wash); `.mx-error button` is paper with a warn-tinted "
    "hairline. Light Overview / Explore read as a cool canvas with white "
    "material, not a paled command center."
)
INTENTIONAL_DIFFS = (
    "Fill (luminance tile vs paper), depth (none vs short shadow), skeleton mix "
    "target (`--panel2` vs `--panel`). Shared: information architecture, "
    "component semantics, spacing/type scales, state meanings, EN/ZH dual-emit, "
    "density law, interaction. Token substitution alone is not the light design."
)

LANDING_TABLE = """\
| Module | Landing | Receipt |
|---|---|---|
| `#si-explore` desk header (h2 + basket search + count) | L1 KEEP | rest + explore crops |
| 01 Performance table (TABLE_LIMIT=8, counted see-more) | L1 KEEP | `table8-*` |
| 02 Performance chart | L1 KEEP | explore tab crop |
| 03 Baskets by category (+#cards/#details) | L1 KEEP | explore tab crop |
| `.si-links` band (tagged links + LENS `?`) | L1 KEEP; r2 simplified to one idiom | r2 cells `silinks-*` (referenced, not recaptured) |
| `#reversal-sleeve-card` | DEMOTE → one link-band entry `Reversal Sleeve → cn_reversal_sleeve.html` (both lanes); stats in LENS tip | r2 `silinks-*` |
| `#sleeve-chip` | DEMOTE → same Reversal Sleeve link-band entry; `hidden` on the chip | P2a test + explore crop |
| `#entry-radar` | DEMOTE → `<details id="entry-radar-more">` "Entry radar" / 「入场雷达」 at tail of Performance-table (JS mount unchanged) | r2 `details-open-*` |
| `#forming-narratives` | DEMOTE → `<details id="forming-narratives-more">` "Forming narratives" / 「酝酿中的叙事」 at tail of Baskets-by-category | explore crop |
| Theme Rotation Desk / concentration / 5-day rotation / impulse | DEMOTE → compact `<details class="si-more">` (`si_explore_compact`) | r2 `details-open-*` |
| r2 `.si-links-note` (42ch prose) | DEMOTE into LENS tip; band is tagged links + `?` only | r2 `silinks-*` (band unchanged this round) |
"""

R2_SILINKS = (
    ("silinks-dark-en-1440", "4341b686af527d45.png", "dark", "en"),
    ("silinks-light-en-1440", "035bcd140a1f09ec.png", "light", "en"),
    ("silinks-dark-zh-1440", "aef810cbf40c9fd2.png", "dark", "zh"),
)

_HIDE = """
() => {
  window.__skyDeck = true;
  const sels = %s;
  sels.forEach((s) => document.querySelectorAll(s).forEach((n) => n.remove()));
  document.querySelectorAll('.nav-search input, .ticker-input').forEach((el) => {
    el.value = '';
    el.blur();
  });
  return true;
}
""" % (json.dumps(list(OVERLAY_SELECTORS)),)

_OVERLAY_PROBE = """
() => {
  const sels = %s;
  const hits = [];
  sels.forEach((s) => {
    document.querySelectorAll(s).forEach((n) => {
      const cs = getComputedStyle(n);
      const r = n.getBoundingClientRect();
      if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') return;
      if (r.width < 1 || r.height < 1) return;
      hits.push({sel: s, w: Math.round(r.width), h: Math.round(r.height)});
    });
  });
  return hits;
}
""" % (json.dumps(list(OVERLAY_SELECTORS)),)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _refuse_dirty() -> tuple[str, str]:
    porcelain = _git(["status", "--porcelain", "--untracked-files=no"])
    if porcelain:
        raise SystemExit("refuse: dirty tracked tree\n" + porcelain)
    return _git(["rev-parse", "HEAD"]), porcelain


def _blank_row(**kw) -> dict:
    row = {
        "kind": "SECTOR",
        "id": "X",
        "name": "Foo",
        "name_zh": "福",
        "score": None,
        "reco": None,
        "reco_en": None,
        "reco_zh": None,
        "rel20": None,
        "rel5": None,
        "tag": None,
        "tag_zh": None,
        "urgency": None,
        "reasons": [],
        "phase": None,
        "osc_slope": None,
        "pos": None,
        "rs_63d": None,
        "rs_rank": None,
        "dual_read": False,
        "dual_chip_en": None,
        "dual_chip_zh": None,
        "organ_state": None,
        "organ_chip_en": None,
        "organ_chip_zh": None,
        "href": None,
    }
    row.update(kw)
    return row


def _render_html() -> str:
    sys.path.insert(0, str(ROOT))
    from engine import i18n

    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    return env.get_template("sector_central_china.html.j2").render(
        bench_en="CSI 300",
        bench_zh="沪深300",
        sleeve_stats={
            "n_members": 12,
            "sleeve_factor": 0.9,
            "sharpe": 0.57,
            "n_rebalances": 349,
            "excess_per_reb": 0.43,
        },
        theme_context={
            "leadership": {
                "trailing_leader": {
                    "name": "Property",
                    "name_zh": "房地产",
                    "id": "cn_property",
                },
                "state": "steady",
                "stance_en": "Hold the leaders",
                "stance_zh": "守住龙头",
                "days_in_state": 5,
                "strength": [
                    {
                        "name": "AI semis",
                        "name_zh": "人工智能半导体",
                        "id": "cn_ai_semis",
                        "desk_score": 72,
                    }
                ],
            },
            "migration": {
                "note_en": (
                    "One desk for China sectors and themes — the gated board, "
                    "the cycle map, whole-market rotation, every basket in depth."
                ),
                "note_zh": "中国行业与主题的统一看板 — 研判、周期图谱、全市场轮动，以及每个篮子的深读。",
            },
        },
        act_now_v2={
            "as_of": "2026-09-11",
            "notes": [],
            "lanes": {
                "buy_now": [
                    _blank_row(
                        kind="THEME",
                        id="cn_ai",
                        name="AI",
                        name_zh="人工智能",
                        score=72,
                        reco="accumulate",
                        reco_en="Accumulate",
                        reco_zh="积累",
                        rel20=0.082,
                        rel5=0.021,
                    )
                ],
                "wait_pullback": [
                    _blank_row(
                        kind="THEME",
                        id="cn_ev",
                        name="EV chain",
                        name_zh="新能源车",
                        score=55,
                        reco="hold",
                        reco_en="Hold",
                        reco_zh="持有",
                        rel20=0.031,
                        rel5=-0.012,
                    )
                ],
                "bottoming_watch": [
                    _blank_row(
                        kind="SECTOR",
                        id="801080",
                        name="Electronics",
                        name_zh="电子",
                        osc_slope=14.1,
                        rs_63d=-5.2,
                        pos=12,
                    )
                ],
                "reduce_avoid": [
                    _blank_row(
                        kind="SECTOR",
                        id="801010",
                        name="Agriculture",
                        name_zh="农林牧渔",
                        tag="WATCH",
                        tag_zh="观察",
                    )
                ],
            },
        },
        sectors_by_ticker={},
    )


def _levels(n: int, seed: int, drift: float = 0.00035) -> list[float]:
    rng = random.Random(seed)
    v = 100.0
    out: list[float] = []
    for _ in range(n):
        v *= 1.0 + drift + rng.uniform(-0.011, 0.011)
        out.append(round(v, 4))
    return out


def _baskets_payload() -> dict:
    n = 340
    start = datetime(2025, 7, 1)
    dates = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n)]
    names = [
        ("b01", "Rare earth", "稀土", "Materials", 81),
        ("b02", "AI semis", "人工智能半导体", "Tech", 74),
        ("b03", "EV chain", "新能源车", "Tech", 61),
        ("b04", "Pharma CXO", "医药CXO", "Health", 58),
        ("b05", "Liquor", "白酒", "Materials", 44),
        ("b06", "Banks", "银行", "Materials", 39),
        ("b07", "Solar", "光伏", "Tech", 52),
        ("b08", "Property", "房地产", "Materials", 28),
        ("b09", "Robotics", "机器人", "Tech", 66),
        ("b10", "TCM", "中药", "Health", 41),
        ("b11", "Gold", "黄金", "Materials", 70),
        ("b12", "Cloud", "云计算", "Tech", 63),
    ]
    baskets = []
    chart_baskets = {}
    for i, (bid, en, zh, cat, score) in enumerate(names):
        baskets.append(
            {
                "id": bid,
                "name": en,
                "name_zh": zh,
                "category": cat,
                "score": score,
                "members": [{"symbol": f"00000{i}.SZ", "name": en}],
            }
        )
        chart_baskets[bid] = _levels(n, seed=100 + i, drift=0.0002 + i * 0.00003)
    return {
        "as_of": "2026-09-11",
        "benchmark_label": "CSI 300",
        "benchmark_label_zh": "沪深300",
        "categories": ["Tech", "Health", "Materials"],
        "categories_zh": ["科技", "医疗", "材料"],
        "baskets": baskets,
        "chart": {
            "dates": dates,
            "bench": _levels(n, seed=1, drift=0.00015),
            "baskets": chart_baskets,
        },
    }


def _data_js(*, stale: bool) -> str:
    market: dict = {"risk_on": 0.04}
    if stale:
        market.update({"any_stale": True, "leg_stale": {"credit": 90, "vol": 20}})
    payload = {"market": market, "sectors": [], "baskets": []}
    return "window.SECTOR_CENTRAL=" + json.dumps(payload, ensure_ascii=False) + ";\n"


def _serve(directory: Path):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(directory), **kw)

        def log_message(self, *_a):
            return

    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Quiet)
    httpd.allow_reuse_address = True
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def _png_meta(png: bytes) -> tuple[int, int]:
    if len(png) >= 24 and png[:8] == b"\x89PNG\r\n\x1a\n" and png[12:16] == b"IHDR":
        return struct.unpack(">II", png[16:24])
    return 0, 0


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
            docEl.lang = state.locale === 'zh' ? 'zh-CN' : 'en';
          }
          return {theme: docEl.getAttribute('data-theme'), locale: docEl.getAttribute('data-lang')};
        }""",
        {"theme": theme, "locale": locale},
    )
    observed = page.evaluate(
        "() => ({theme: document.documentElement.getAttribute('data-theme'),"
        " locale: document.documentElement.getAttribute('data-lang'),"
        " body: document.body.className})"
    )
    if observed["theme"] != theme or (observed["locale"] or "en") != locale:
        raise SystemExit(f"state mismatch: wanted {theme}/{locale} got {observed}")
    if "page-sector-central" not in (observed["body"] or ""):
        raise SystemExit(f"missing body.page-sector-central: {observed['body']!r}")
    page.evaluate(_HIDE)
    return observed


def _set_view(page, view: str) -> None:
    page.evaluate(
        """(view) => {
          document.querySelectorAll('.si-view').forEach((v) => v.classList.remove('on'));
          const el = document.querySelector('.si-view[data-view=\"' + view + '\"]');
          if (el) el.classList.add('on');
          document.querySelectorAll('.si-view-btn').forEach((b) => {
            const on = b.getAttribute('data-view') === view;
            b.classList.toggle('on', on);
            if (on) b.setAttribute('aria-current', 'page');
            else b.removeAttribute('aria-current');
          });
        }""",
        view,
    )


def _computed_text(page, sel: str) -> dict:
    return page.evaluate(
        """(sel) => {
          const el = document.querySelector(sel);
          if (!el) return {sel, missing: true};
          const cs = getComputedStyle(el);
          return {
            sel,
            text: (el.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 480),
            color: cs.color,
            backgroundColor: cs.backgroundColor,
            fontSize: cs.fontSize,
            fontFamily: (cs.fontFamily || '').split(',')[0].replace(/[\"']/g, '').trim(),
            boxShadow: cs.boxShadow,
            borderColor: cs.borderColor,
          };
        }""",
        sel,
    )


def _wait_table(page) -> None:
    page.wait_for_function(
        "() => { const t = document.getElementById('btable'); return t && t.querySelectorAll('tbody tr').length >= 8; }",
        timeout=12_000,
    )


def _prep(page, spec: dict) -> None:
    view = spec.get("view") or "overview"
    _set_view(page, view)
    kind = spec["kind"]
    if kind in ("table8", "sigma", "p0", "explore"):
        _set_view(page, "explore")
        _wait_table(page)
    if kind == "sigma":
        page.evaluate(
            """() => {
              const host = document.getElementById('btbl-mode');
              if (!host) return;
              const btn = [...host.querySelectorAll('button')].find((b) => b.dataset.v === 'sigma');
              if (btn) btn.click();
            }"""
        )
        page.wait_for_timeout(120)
    if kind == "p0":
        # Composition crop (disclosed): both CSI-300 strings live in Explore but
        # not in one 900px frame (mode tab on the table, "versus CSI 300" inside
        # the demoted 5-day-rotation details). Copy the LIVE nodes into a visible
        # strip at the top of #table-section so the healed contradiction is the
        # whole frame. Never invent the strings.
        page.evaluate(
            """() => {
              const table = document.getElementById('table-section');
              if (!table) return;
              const old = document.getElementById('p0-csi-frame');
              if (old) old.remove();
              const rot = document.getElementById('si-rotation-more');
              if (rot) rot.open = true;
              const tab = document.querySelector('#btbl-mode button[data-v="rel"]');
              const versus = document.querySelector('#si-rotation-more .sub');
              const strip = document.createElement('div');
              strip.id = 'p0-csi-frame';
              strip.style.cssText = 'display:flex;flex-direction:column;gap:8px;padding:10px 12px;margin:0 0 12px;border:1px solid var(--line);border-radius:10px;background:var(--panel);';
              if (tab) {
                const row = document.createElement('div');
                row.className = 'tabs';
                row.appendChild(tab.cloneNode(true));
                strip.appendChild(row);
              }
              if (versus) strip.appendChild(versus.cloneNode(true));
              table.insertBefore(strip, table.firstChild);
            }"""
        )
        page.wait_for_timeout(80)
    if kind == "confluence":
        _set_view(page, "confluence")
        page.evaluate(
            """() => {
              const el = document.getElementById('sc-asof');
              if (el && !el.textContent.trim()) el.textContent = 'as of 2026-09-11';
            }"""
        )
    if kind == "empty":
        _set_view(page, "moving")
        page.wait_for_selector("#rc-events-cn-content .rc-quiet-cn, #rc-events-cn-content .mx-error", timeout=8_000)
    if kind == "error":
        _set_view(page, "explore")
        page.wait_for_selector("#csi-baskets-error", timeout=8_000)
    if kind == "stale":
        page.wait_for_selector("#regime .rg-stale-notice, #regime", timeout=8_000)
        page.wait_for_timeout(200)
    if kind == "skeleton":
        _set_view(page, "confluence")
    if kind == "footer":
        page.evaluate("() => { const f = document.querySelector('footer'); if (f) f.scrollIntoView(); }")
    if kind in ("bottoming", "actnow"):
        _set_view(page, "overview")
        page.evaluate(
            """() => {
              const el = document.getElementById('act-now') || document.getElementById('actnow-section');
              if (el) el.scrollIntoView();
            }"""
        )


def _clip_union(page, selectors: list[str]) -> dict | None:
    box = page.evaluate(
        """(sels) => {
          let x = Infinity, y = Infinity, r = -Infinity, b = -Infinity, n = 0;
          sels.forEach((s) => {
            const el = document.querySelector(s);
            if (!el) return;
            el.scrollIntoView({block: 'nearest'});
            const rec = el.getBoundingClientRect();
            if (rec.width < 1 || rec.height < 1) return;
            n += 1;
            x = Math.min(x, rec.x);
            y = Math.min(y, rec.y);
            r = Math.max(r, rec.right);
            b = Math.max(b, rec.bottom);
          });
          if (!n) return null;
          const pad = 8;
          return {
            x: Math.max(0, Math.floor(x - pad)),
            y: Math.max(0, Math.floor(y - pad)),
            width: Math.ceil(r - x + 2 * pad),
            height: Math.ceil(b - y + 2 * pad),
          };
        }""",
        selectors,
    )
    return box


def _shot_bytes(page, spec: dict) -> bytes:
    kind = spec["kind"]
    if kind == "rest":
        return page.screenshot(type="png", full_page=True)
    if kind == "p0":
        loc = page.locator("#p0-csi-frame").first
        loc.wait_for(state="visible", timeout=8_000)
        return loc.screenshot(type="png")
    sel = spec.get("sel")
    if sel:
        loc = page.locator(sel).first
        loc.wait_for(state="visible", timeout=8_000)
        loc.scroll_into_view_if_needed()
        page.wait_for_timeout(80)
        return loc.screenshot(type="png")
    return page.screenshot(type="png")


def _cell_specs() -> list[dict]:
    specs: list[dict] = []
    for viewport, (w, h) in VIEWPORTS.items():
        for locale in ("en", "zh"):
            for theme in ("dark", "light"):
                specs.append(
                    {
                        "id": f"rest-{theme}-{locale}-{w}",
                        "kind": "rest",
                        "subject": "full-page-overview",
                        "theme": theme,
                        "locale": locale,
                        "viewport": viewport,
                        "view": "overview",
                        "sel": None,
                        "force_state": None,
                        "stale": False,
                        "abort_baskets": False,
                        "computed_sel": "body",
                    }
                )

    def crop(cid, kind, subject, sel, theme, locale, view, *, force, extra=None):
        row = {
            "id": cid,
            "kind": kind,
            "subject": subject,
            "theme": theme,
            "locale": locale,
            "viewport": "desktop",
            "view": view,
            "sel": sel,
            "force_state": force,
            "stale": False,
            "abort_baskets": False,
            "computed_sel": sel or "body",
        }
        if extra:
            row.update(extra)
        specs.append(row)

    for theme in ("dark", "light"):
        for locale in ("en", "zh"):
            crop(
                f"p0-{theme}-{locale}-1440",
                "p0",
                "p0-versus-csi300",
                "#p0-csi-frame",
                theme,
                locale,
                "explore",
                force="p0",
            )
            crop(
                f"bottoming-{theme}-{locale}-1440",
                "bottoming",
                "bottoming-watch",
                "#anv2-bot",
                theme,
                locale,
                "overview",
                force="bottoming",
            )
            crop(
                f"actnow-{theme}-{locale}-1440",
                "actnow",
                "act-now-chip",
                "#anv2-red",
                theme,
                locale,
                "overview",
                force="actnow",
            )
            crop(
                f"explore-{theme}-{locale}-1440",
                "explore",
                "explore-tab",
                ".si-view[data-view='explore']",
                theme,
                locale,
                "explore",
                force="explore",
            )
            crop(
                f"footer-{theme}-{locale}-1440",
                "footer",
                "one-sentence-footer",
                "footer",
                theme,
                locale,
                "overview",
                force="footer",
            )
        crop(
            f"table8-{theme}-en-1440",
            "table8",
            "table-limit-8",
            "#table-section",
            theme,
            "en",
            "explore",
            force="table8",
        )
        crop(
            f"sigma-{theme}-en-1440",
            "sigma",
            "sigma-mode",
            "#table-section",
            theme,
            "en",
            "explore",
            force="sigma",
        )
        crop(
            f"confluence-{theme}-en-1440",
            "confluence",
            "confluence-one-stamp",
            "#si-confluence .sc-head",
            theme,
            "en",
            "confluence",
            force="confluence",
        )
        crop(
            f"skel-{theme}-en-1440",
            "skeleton",
            "degraded-skeleton",
            "#sc-app .skel-slot",
            theme,
            "en",
            "confluence",
            force="skeleton",
        )
        crop(
            f"empty-{theme}-en-1440",
            "empty",
            "degraded-empty",
            "#rc-events-cn",
            theme,
            "en",
            "moving",
            force="empty",
        )
        crop(
            f"stale-{theme}-en-1440",
            "stale",
            "degraded-stale",
            "#regime",
            theme,
            "en",
            "overview",
            force="stale",
            extra={"stale": True},
        )
        crop(
            f"error-{theme}-en-1440",
            "error",
            "degraded-error",
            "#csi-baskets-error",
            theme,
            "en",
            "explore",
            force="error",
            extra={"abort_baskets": True},
        )
    return specs


def _write_png(png_dir: Path, png: bytes) -> tuple[str, str, int, int]:
    digest = hashlib.sha256(png).hexdigest()
    fname = f"{digest[:16]}.png"
    dest = png_dir / fname
    if not dest.exists():
        dest.write_bytes(png)
    w, h = _png_meta(png)
    return fname, digest, w, h


def _hscroll_receipts(context, origin: str) -> list[dict]:
    views = ("overview", "map", "moving", "explore", "confluence")
    out: list[dict] = []
    page = context.new_page()
    page.add_init_script("window.__skyDeck = true;")
    page.goto(f"{origin}/sector_central_china.html", wait_until="domcontentloaded", timeout=30_000)
    for locale in ("en", "zh"):
        _apply(page, "dark", locale)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(80)
        for view in views:
            _set_view(page, view)
            page.wait_for_timeout(60)
            rec = page.evaluate(
                """() => {
                  const de = document.documentElement;
                  const body = document.body;
                  const client = de.clientWidth;
                  const scroll = Math.max(de.scrollWidth, body ? body.scrollWidth : 0);
                  return {
                    clientWidth: client,
                    scrollWidth: scroll,
                    overflow: scroll > client + 1,
                    view: document.querySelector('.si-view.on')?.getAttribute('data-view') || null,
                  };
                }"""
            )
            rec.update({"locale": locale, "theme": "dark", "viewport_width": 390, "si_view": view})
            out.append(rec)
    page.close()
    return out


def _write_readme(head: str, shots: list[dict], hscroll: list[dict], generated: str) -> None:
    def row(s: dict) -> str:
        return (
            f"| `{s['id']}` | {s['subject']} | {s['theme']} | {s['locale']} | "
            f"{s['viewport_width']} | `{s['file']}` | {s['overlay']} | "
            f"{s.get('computed_text', {}).get('text', '')[:80]} |"
        )

    rest = [s for s in shots if s["kind"] == "rest"]
    families = [
        ("(a) P0 CSI 300 frame", "p0"),
        ("(b) Bottoming Watch", "bottoming"),
        ("(c) Act-Now Early sign", "actnow"),
        ("(d) Explore tab post-P2a", "explore"),
        ("(e) TABLE_LIMIT=8 see-more", "table8"),
        ("(f) σ mode (no MTD/YTD dash wall)", "sigma"),
        ("(g) Confluence one stamp", "confluence"),
        ("(h) one-sentence footer + disclaimer", "footer"),
    ]
    deg = [
        ("loading skeleton", "skeleton"),
        ("empty (quiet tape)", "empty"),
        ("stale regime input", "stale"),
        ("error-with-retry", "error"),
    ]
    lines = [
        "# W14 r3 — sector_central_china evidence matrix",
        "",
        f"Provenance: `capture_sha` == `{head}`. Rig: S1 fixture-render + real "
        "`body.page-sector-central`; `__skyDeck`; overlay hide `.rvx-aurora` / "
        "`.mx5-aurora` / `.sky-fx` / `#mmb-root` / `#mmb-boot` / `.aurora`; "
        "overlay column populated; computed-style text on every cell. "
        "Light forced via `data-theme=\"light\"` on `<html>` (and `setTheme`). "
        "Never opted into `site/` or `data/`.",
        "",
        f"Generated `{generated}`.",
        "",
        "## DARK TREATMENT",
        "",
        DARK_TREATMENT,
        "",
        "## LIGHT TREATMENT",
        "",
        LIGHT_TREATMENT,
        "",
        "## Which mechanisms intentionally differ",
        "",
        INTENTIONAL_DIFFS,
        "",
        "Reference: templates/sector_central_china.html.j2 W14 r2 chrome comment "
        "(lines ~130–142) plus the live light rules under "
        "`html[data-theme=\"light\"] body.page-sector-central`.",
        "",
        "## §9.13 landing table (P2a + r2 band note)",
        "",
        LANDING_TABLE,
        "",
        "## 8 full-page baselines (rest cells)",
        "",
        "| id | subject | theme | locale | vw | file | overlay | computed text |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in rest:
        lines.append(row(s))
    lines += ["", "## Per-fix crops", ""]
    for title, kind in families:
        lines += [f"### {title}", "", "| id | subject | theme | locale | vw | file | overlay | computed text |", "|---|---|---|---|---|---|---|---|"]
        for s in shots:
            if s["kind"] == kind:
                lines.append(row(s))
        lines.append("")
    lines += [
        "### (h continued) simplified `.si-links` band — referenced from r2, not recaptured",
        "",
        "The band is unchanged this round (r1 landing table + r2 one-idiom simplification). "
        f"r2 capture_sha `21546c85ed8af3e286abfdd4214a8c99b607efe9`. Directory `{R2.relative_to(ROOT)}`.",
        "",
        "| id | file | theme | locale |",
        "|---|---|---|---|",
    ]
    for cid, fname, theme, locale in R2_SILINKS:
        lines.append(f"| `{cid}` (r2) | `{fname}` | {theme} | {locale} |")
    lines += ["", "## Theme-specific degraded states", ""]
    for title, kind in deg:
        lines += [f"### {title}", "", "| id | subject | theme | locale | vw | file | overlay | computed text |", "|---|---|---|---|---|---|---|---|"]
        for s in shots:
            if s["kind"] == kind:
                lines.append(row(s))
        lines.append("")
    lines += [
        "## 390w no-page-h-scroll receipts (every si-view × both languages)",
        "",
        "| si-view | locale | clientWidth | scrollWidth | page overflow |",
        "|---|---|---|---|---|",
    ]
    for rec in hscroll:
        lines.append(
            f"| `{rec['si_view']}` | {rec['locale']} | {rec['clientWidth']} | "
            f"{rec['scrollWidth']} | {str(rec['overflow']).lower()} |"
        )
    overflowed = [r for r in hscroll if r["overflow"]]
    lines += [
        "",
        (
            "All ten receipts report no page-level horizontal overflow."
            if not overflowed
            else "OVERFLOW: " + ", ".join(f"{r['si_view']}/{r['locale']}" for r in overflowed)
        ),
        "",
        "Container `overflow-x: auto` on `.si-side` (mobile rail) and `.ts` (table) is the "
        "§9.10 in-container scroll, not page scroll.",
        "",
    ]
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    head, porcelain = _refuse_dirty()
    html = _render_html()
    for needle in (
        "not investment advice",
        "versus CSI 300",
        "Early sign",
        "turning up",
        "page-sector-central",
        "const TABLE_LIMIT = 8;",
        "How unusual",
    ):
        if needle not in html:
            raise SystemExit(f"fixture missing {needle!r} — refusing capture")

    staging = Path(tempfile.mkdtemp(prefix="scchina-w14r3-"))
    try:
        (staging / "sector_central_china.html").write_text(html, encoding="utf-8")
        for name in ASSETS:
            src = ROOT / "templates" / name
            if src.exists():
                shutil.copy2(src, staging / name)
        (staging / "chinabasketdata").mkdir()
        (staging / "chinabasketdata" / "baskets.json").write_text(
            json.dumps(_baskets_payload(), ensure_ascii=False), encoding="utf-8"
        )
        (staging / "marketdata").mkdir()
        (staging / "marketdata" / "rotation_events_china.json").write_text(
            json.dumps({"active": [], "as_of": "2026-09-11"}), encoding="utf-8"
        )
        (staging / "chinastatedata").mkdir()
        (staging / "chinastatedata" / "participation.json").write_text(
            json.dumps({"southbound_z": 0.4}), encoding="utf-8"
        )
        (staging / "sector_central_china_data.js").write_text(_data_js(stale=False), encoding="utf-8")

        httpd, port = _serve(staging)
        origin = f"http://127.0.0.1:{port}"
        shots: list[dict] = []
        for old in OUT.glob("*.png"):
            old.unlink()

        specs = _cell_specs()
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            contexts = {}
            for vp_name, (w, h) in VIEWPORTS.items():
                contexts[vp_name] = browser.new_context(
                    viewport={"width": w, "height": h},
                    device_scale_factor=1,
                    reduced_motion="reduce",
                )
            for spec in specs:
                vp_name = spec["viewport"]
                w, h = VIEWPORTS[vp_name]
                context = contexts[vp_name]
                page = context.new_page()
                page.add_init_script(
                    "window.__skyDeck = true;\n"
                    "try {\n"
                    f"  localStorage.setItem('theme', {json.dumps(spec['theme'])});\n"
                    "  localStorage.removeItem('themeAuto');\n"
                    f"  localStorage.setItem('lang', {json.dumps(spec['locale'])});\n"
                    "} catch (e) {}\n"
                )
                def _fulfill_data(route, *_unused, _stale=bool(spec.get("stale"))):
                    # Playwright may call handler(route) or handler(route, request).
                    # Never bind the request object as the stale flag.
                    route.fulfill(
                        body=_data_js(stale=_stale),
                        content_type="application/javascript; charset=utf-8",
                    )

                page.route("**/sector_central_china_data.js", _fulfill_data)
                if spec.get("abort_baskets"):
                    page.route("**/chinabasketdata/**", lambda route: route.abort())
                page.route("**/subsectors_china.js", lambda route: route.abort())
                page.route("**/subsector_rotation.js", lambda route: route.abort())
                page.goto(
                    f"{origin}/sector_central_china.html",
                    wait_until="domcontentloaded",
                    timeout=30_000,
                )
                observed = _apply(page, spec["theme"], spec["locale"])
                _prep(page, spec)
                page.wait_for_timeout(180)
                page.evaluate(_HIDE)
                overlay_hits = page.evaluate(_OVERLAY_PROBE)
                png = _shot_bytes(page, spec)
                fname, digest, pw_, ph = _write_png(OUT, png)
                computed = _computed_text(page, spec.get("computed_sel") or "body")
                if spec["kind"] == "p0":
                    text = page.evaluate(
                        "() => (document.getElementById('p0-csi-frame')?.textContent || '')"
                    )
                    if spec["locale"] == "en":
                        if "versus CSI 300" not in text or "vs CSI 300" not in text:
                            raise SystemExit(
                                f"P0 frame missing both strings: {spec['id']!r} text={text[:400]!r}"
                            )
                    else:
                        if "沪深300" not in text:
                            raise SystemExit(f"P0 ZH frame missing 沪深300: {spec['id']}")
                if spec["kind"] == "sigma":
                    heads = page.evaluate(
                        "() => [...document.querySelectorAll('#btable thead th')].map(t => t.textContent)"
                    )
                    joined = " ".join(heads)
                    if "MTD" in joined or "YTD" in joined or "月至今" in joined or "年至今" in joined:
                        raise SystemExit(f"sigma mode still shows MTD/YTD: {heads}")
                if spec["kind"] == "table8":
                    more = page.evaluate(
                        "() => document.getElementById('table-more')?.textContent || ''"
                    )
                    if "See more" not in more and "查看更多" not in more:
                        raise SystemExit(f"see-more missing: {more!r}")
                if spec["kind"] == "footer":
                    foot = page.evaluate("() => document.querySelector('footer')?.innerText || ''")
                    if "not investment advice" not in foot and "非投资建议" not in foot:
                        raise SystemExit(f"footer missing disclaimer: {foot!r}")
                cell = {
                    "id": spec["id"],
                    "kind": spec["kind"],
                    "subject": spec["subject"],
                    "file": fname,
                    "sha256": digest,
                    "bytes": len(png),
                    "width": pw_,
                    "height": ph,
                    "theme": spec["theme"],
                    "locale": spec["locale"],
                    "viewport": spec["viewport"],
                    "viewport_width": w,
                    "viewport_height": h,
                    "access": "anonymous",
                    "force_state": spec["force_state"],
                    "applied_theme": observed["theme"],
                    "applied_locale": observed["locale"] or "en",
                    "body_class": observed["body"],
                    "overlay": "clean" if overlay_hits == [] else "dirty:" + ",".join(
                        hit["sel"] for hit in overlay_hits
                    ),
                    "overlay_clean": overlay_hits == [],
                    "overlay_hits": overlay_hits,
                    "selector": spec.get("sel"),
                    "computed_text": computed,
                    "captured": True,
                }
                shots.append(cell)
                print(
                    f"{spec['id']}: {fname} overlay={cell['overlay']} "
                    f"{pw_}x{ph} theme={observed['theme']} lang={observed['locale']}",
                    flush=True,
                )
                page.close()

            hscroll = _hscroll_receipts(contexts["mobile"], origin)
            for ctx in contexts.values():
                ctx.close()
            browser.close()
        httpd.shutdown()
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    dirty = [s["id"] for s in shots if not s["overlay_clean"]]
    if dirty:
        raise SystemExit("overlay dirty: " + ", ".join(dirty))
    overflowed = [r for r in hscroll if r["overflow"]]
    if overflowed:
        raise SystemExit(
            "page h-scroll at 390w: "
            + ", ".join(f"{r['si_view']}/{r['locale']}" for r in overflowed)
        )
    rest_keys = {
        (s["viewport"], s["locale"], s["theme"])
        for s in shots
        if s["force_state"] is None
    }
    required = {
        (vp, loc, th)
        for vp in ("desktop", "mobile")
        for loc in ("en", "zh")
        for th in ("dark", "light")
    }
    if rest_keys != required:
        raise SystemExit(f"rest cells incomplete: have={sorted(rest_keys)}")

    generated = _now_iso()
    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "tool": "mockups/evidence/sector-central-china-w14-r3/capture.py",
        "generated_at": generated,
        "capture_sha": head,
        "resolved_gitdir": _git(["rev-parse", "--git-dir"]),
        "porcelain_at_capture": porcelain,
        "rig": (
            "S1 fixture-render + real body.page-sector-central "
            "(Playwright, overlay hide, __skyDeck, reduced-motion, computed-style text)"
        ),
        "overlays_hidden": list(OVERLAY_SELECTORS),
        "outcome": "captured",
        "honesty": {
            "access": "anonymous only; fixture render, no live site/ bake",
            "authority": "this tool measures and screenshots; it scores, ranks, and judges nothing",
            "gaps": (
                "si-links band referenced from r2 (unchanged); confluence as-of text "
                "seeded when the lazy board is not mounted; P0 crop clones the LIVE "
                "rel-mode tab and the 5-day-rotation .sub into #p0-csi-frame so both "
                "CSI-300 strings share one frame (they do not sit together at rest)"
            ),
        },
        "axes": {
            "access": ["anonymous"],
            "themes": ["dark", "light"],
            "locales": ["en", "zh"],
            "viewports": {"desktop": [1440, 900], "mobile": [390, 844]},
        },
        "hscroll_390": hscroll,
        "r2_silinks_reference": [
            {
                "id": cid,
                "file": fname,
                "theme": theme,
                "locale": locale,
                "capture_sha": "21546c85ed8af3e286abfdd4214a8c99b607efe9",
                "path": "mockups/evidence/sector-central-china-w14-r2/" + fname,
            }
            for cid, fname, theme, locale in R2_SILINKS
        ],
        "art_direction": {
            "dark": DARK_TREATMENT,
            "light": LIGHT_TREATMENT,
            "intentional_differences": INTENTIONAL_DIFFS,
        },
        "pages": [
            {
                "page_id": "sector_central_china",
                "route": "/sector_central_china.html",
                "capture_route": "/sector_central_china.html",
                "gaps": [],
                "states": [
                    {
                        "id": s["id"],
                        "access": "anonymous",
                        "theme": s["theme"],
                        "locale": s["locale"],
                        "viewport": s["viewport"],
                        "viewport_width": s["viewport_width"],
                        "viewport_height": s["viewport_height"],
                        "force_state": s["force_state"],
                        "captured": True,
                        "file": s["file"],
                        "sha256": s["sha256"],
                        "bytes": s["bytes"],
                        "width": s["width"],
                        "height": s["height"],
                        "applied_theme": s["applied_theme"],
                        "applied_locale": s["applied_locale"],
                        "overlay": s["overlay"],
                        "subject": s["subject"],
                    }
                    for s in shots
                ],
            }
        ],
        "cells": shots,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (OUT / "EVIDENCE.yml").write_text(
        "schema: mastermind.page_evidence_receipt.v1\n"
        "changed_paths:\n"
        "  - templates/sector_central_china.html.j2\n"
        "  - templates/_baskets_desk.html.j2\n"
        "  - templates/_china_act_now_board.html.j2\n"
        "manifest: mockups/evidence/sector-central-china-w14-r3/manifest.json\n",
        encoding="utf-8",
    )
    _write_readme(head, shots, hscroll, generated)
    print(
        f"capture_sha={head} n={len(shots)} overlay_all_clean hscroll_ok={len(hscroll)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
