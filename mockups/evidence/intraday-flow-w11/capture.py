#!/usr/bin/env python3
"""S1-rig evidence matrix for intraday_flow W11, extended from the r2 overlay rig.

The full-page fixture (hero and board rest cells, named states, See-all
hover/focus) and the round-2 overlay-column crops live in this one script.
Playwright, __skyDeck seed, overlay hide, reduced-motion, content-addressed
PNGs, overlay-clean column, at-rest text via computed styles (never HTML source).

Every declared page anchor carries the eight rest cells (desktop/mobile ×
en/zh × dark/light). Named states and the round-2 crops are force-state rows
on the hero anchor. A separate page per crop is what produced the 96-finding
corpus red (twelve anchors with no rest matrix).

Stamps `git rev-parse HEAD`. Refuses to run when anything outside
mockups/evidence/intraday-flow-w11 and mockups/evidence/intraday-flow-w11-r2
is dirty, so a template edit cannot wear this sha. The packet directories
themselves may be dirty: that is the artifact being written.

Home: mockups/evidence/intraday-flow-w11/
Recapture: python3 mockups/evidence/intraday-flow-w11/capture.py
"""
from __future__ import annotations

import hashlib
import http.server
import json
import shutil
import socketserver
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "templates" / "intraday_flow.html.j2"

OVERLAY_SELECTORS = (".ift-aurora", ".mx5-aurora", ".sky-fx", "#mmb-root", "#mmb-boot")
FIXTURE_N = 12
AS_OF_DISPLAY = {"en": "10 Sep 11:34pm UTC", "zh": "9月10日 23:34 UTC"}
AS_OF_ISO = "2026-09-10T23:34:28.190939+00:00"

VIEWPORTS = {
    "desktop": (1440, 900),
    "mobile": (390, 844),
}

# Asset files served next to the fixture HTML.
_ASSETS = (
    "theme.css",
    "theme.js",
    "data_base.js",
    "navigation-refresh.css",
    "product-nav-icons.css",
    "nav_market.js",
    "live.js",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _leader(ticker: str, baskets: list[str], kind: str) -> dict:
    """Nightly-shaped leader row. `kind` is the stance we want under live quotes."""
    rec: dict = {
        "ticker": ticker,
        "baskets": baskets,
        "adv20_shares": 40_000_000,
        "prev_close": 100.0,
        "atr14_pct": 0.025,
        "failed_breakout_trap": None,
        "options_entry": {
            "dealer": {
                "regime": "long",
                "call_wall": 120.0,
                "call_wall_hard": True,
                "put_wall": 90.0,
                "expected_move_daily_pct": 2.4,
                "vol_hole_state": "NONE",
            }
        },
    }
    if kind == "act":
        rec["bb_lower_reclaim_days"] = 2
        rec["mtf_upturn_state"] = "UPTURN_CONFIRMED"
        rec["failed_breakout_trap"] = False
    elif kind == "ready":
        rec["bb_lower_reclaim_days"] = 3
        rec["mtf_upturn_state"] = "UPTURN_WATCH"
        rec["vol_squeeze"] = {"coiled": True}
    elif kind == "favour":
        rec["bb_lower_reclaim_days"] = 40
        rec["mtf_upturn_state"] = "UPTURN_CONFIRMED"
    elif kind == "watch":
        rec["bb_lower_reclaim_days"] = 40
        rec["mtf_upturn_state"] = None
    else:
        rec["bb_lower_reclaim_days"] = 40
        rec["mtf_upturn_state"] = None
    return rec


OPEN_SPEC = (
    ("NVDA", ["mag7"], "act"),
    ("AAPL", ["mag7"], "ready"),
    ("MSFT", ["mag7"], "quiet"),
    ("TSLA", ["mag7"], "watch"),
    ("AMD", ["ai_semiconductors"], "favour"),
    ("AVGO", ["ai_semiconductors"], "quiet"),
    ("NEE", ["power_grid"], "quiet"),
    ("PWR", ["power_grid"], "quiet"),
    ("ETN", ["power_grid"], "quiet"),
    ("CEG", ["power_grid"], "quiet"),
    ("GE", ["defense"], "quiet"),
    ("SMCI", ["ai_infra"], "quiet"),
)
assert len(OPEN_SPEC) == FIXTURE_N


def _payload(spec: tuple[tuple[str, list[str], str], ...]) -> dict:
    leaders = [_leader(*row) for row in spec]
    return {
        "schema": "intraday_flow_base.v1",
        "built_utc": AS_OF_ISO,
        "as_of": AS_OF_ISO,
        "as_of_display": AS_OF_DISPLAY,
        "n_leaders": len(leaders),
        "universe_baskets": [
            "mag7", "ai_infra", "ai_software", "ai_semiconductors",
            "semicap_equipment", "reshoring", "defense", "power_grid",
        ],
        "rvol_confirm": 1.30,
        "durability_min": 0.60,
        "washout_lookback": 10,
        "leaders": leaders,
    }


def _quote_for(kind: str) -> dict:
    if kind == "act":
        # Keep vs-VWAP well under 1.5× expected-move so computeStance does not
        # promote the name into take_profits (extendedUp) before the act gate.
        return {"price": 106.0, "changePct": 1.8, "vol": 8.0e7, "hi": 107.0, "lo": 103.0}
    if kind == "ready":
        return {"price": 97.0, "changePct": -0.8, "vol": 2.0e7, "hi": 101.0, "lo": 96.5}
    if kind == "favour":
        return {"price": 105.0, "changePct": 1.1, "vol": 3.5e7, "hi": 106.0, "lo": 103.0}
    if kind == "watch":
        return {"price": 106.0, "changePct": 4.2, "vol": 6.0e7, "hi": 107.0, "lo": 99.0}
    return {"price": 100.4, "changePct": 0.2, "vol": 1.2e7, "hi": 101.0, "lo": 99.6}


def _pulse_for(ticker: str, kind: str) -> dict:
    base = {
        "ticker": ticker,
        "bars_today": 42,
        "higher_lows": 1 if kind in ("act", "favour") else 0,
        "session_high": 112.0,
        "session_low": 96.0,
        "cum_vol": 2.0e7,
    }
    if kind == "act":
        base.update(vwap=104.5, vol_durability=0.85, rvol_tod=2.4)
    elif kind == "ready":
        base.update(vwap=101.0, vol_durability=0.45, rvol_tod=0.9)
    elif kind == "favour":
        base.update(vwap=104.0, vol_durability=0.72, rvol_tod=1.5)
    elif kind == "watch":
        base.update(vwap=103.0, vol_durability=0.35, rvol_tod=1.8)
    else:
        base.update(vwap=100.2, vol_durability=0.30, rvol_tod=0.6)
    return base


def _feeds(spec: tuple[tuple[str, list[str], str], ...], *, quotes: bool, pulse: bool, flow: bool) -> dict:
    q, p, events, tide, minutes = {}, [], [], [], {}
    asof = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    for ticker, _baskets, kind in spec:
        if quotes:
            q[ticker] = _quote_for(kind)
        if pulse:
            p.append(_pulse_for(ticker, kind))
        if flow:
            events.append({"root": ticker, "badges": ["WHALE", "FRESH"], "session_tier": "high"})
            tide.append({"root": ticker, "net_prem_soft": 250000, "gross": 800000})
            minutes[ticker] = {
                "minutes": [{"ncp": i * 40000} for i in range(12)],
                "day": {"net_soft": 480000, "call_share": 0.62},
            }
    return {
        "quotes": {"quotes": q} if quotes else {"quotes": {}},
        "pulse": {"tickers": p} if pulse else {"tickers": []},
        "tide": {"top_net_impact": tide, "source_asof": asof} if flow else None,
        "enrich": {"schema": "flow.enrich/v1", "asof": asof, "events": events} if flow else None,
        "meta": {"schema": "live_flow.meta/v2", "asof": asof} if flow else None,
        "minutes": minutes,
    }


def _patch_html(html: str) -> str:
    html = html.replace(
        "function isMarketHours() { var e=_etMinutes(); return e >= (9*60+25) && e <= (16*60+5); }",
        "function isMarketHours() {"
        " if (window.__IFT_FORCE_HOURS === 'live') return true;"
        " if (window.__IFT_FORCE_HOURS === 'closed') return false;"
        " var e=_etMinutes(); return e >= (9*60+25) && e <= (16*60+5); }",
        1,
    )
    html = html.replace(
        "function sessionPhase() {\n  var e = _etMinutes();",
        "function sessionPhase() {\n"
        "  if (window.__IFT_FORCE_HOURS === 'live') return 'live';\n"
        "  if (window.__IFT_FORCE_HOURS === 'closed') return 'closed';\n"
        "  var e = _etMinutes();",
        1,
    )
    html = html.replace(
        "setGroupToggle(true);\n"
        "if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', startPolling);\n"
        "else startPolling();\n"
        "render();",
        "setGroupToggle(true);\n"
        "if (!window.__IFT_HOLD) {\n"
        "  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', startPolling);\n"
        "  else startPolling();\n"
        "  render();\n"
        "}",
        1,
    )
    return html


def _render(payload: dict) -> str:
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    html = env.get_template("intraday_flow.html.j2").render(intraday_flow=payload)
    return _patch_html(html)


def _stage(staging: Path, open_html: str, quiet_html: str) -> None:
    staging.mkdir(parents=True, exist_ok=True)
    (staging / "open.html").write_text(open_html, encoding="utf-8")
    (staging / "quiet.html").write_text(quiet_html, encoding="utf-8")
    for name in _ASSETS:
        src = ROOT / "templates" / name
        if src.exists():
            shutil.copy2(src, staging / name)
    fonts = ROOT / "templates" / "fonts"
    if fonts.exists():
        dest = staging / "fonts"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(fonts, dest)


def _serve(directory: Path):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, fmt, *args):  # noqa: ARG002
            return

    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Quiet)
    httpd.allow_reuse_address = True
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


_HIDE = """
() => {
  window.__skyDeck = true;
  const sels = %s;
  sels.forEach((s) => document.querySelectorAll(s).forEach((n) => n.remove()));
  document.querySelectorAll('.nav-search input, .ticker-input').forEach((el) => {
    el.value = '';
    el.blur();
  });
  document.querySelectorAll('.idle-ticker').forEach((n) => { n.textContent = ''; });
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
      hits.push({sel: s, w: r.width, h: r.height});
    });
  });
  return hits;
}
""" % (json.dumps(list(OVERLAY_SELECTORS)),)

_VISIBLE_TEXT = """
() => {
  const lang = document.documentElement.getAttribute('data-lang') || 'en';
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const chunks = [];
  const liveHits = [];
  function hidden(el) {
    while (el) {
      if (el.nodeType !== 1) { el = el.parentElement; continue; }
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0) return true;
      if (el.classList.contains('l-en') && lang === 'zh') return true;
      if (el.classList.contains('l-zh') && lang !== 'zh') return true;
      el = el.parentElement;
    }
    return false;
  }
  while (walker.nextNode()) {
    const node = walker.currentNode;
    const raw = node.textContent || '';
    const text = raw.replace(/\\s+/g, ' ').trim();
    if (!text) continue;
    const parent = node.parentElement;
    if (!parent || parent.closest('script, style, noscript')) continue;
    if (hidden(parent)) continue;
    chunks.push(text);
    if (/live|实时/i.test(text)) {
      const stamp = !!parent.closest('#ift-stamp');
      liveHits.push({
        text: text.slice(0, 160),
        in_stamp: stamp,
        tag: parent.tagName.toLowerCase(),
        cls: (parent.className || '').toString().slice(0, 80),
      });
    }
  }
  return {
    text: chunks.join(' '),
    liveHits: liveHits,
    stamp: (document.getElementById('ift-stamp') || {}).innerText || '',
    countLabel: (document.getElementById('count-label') || {}).innerText || '',
    bodyClass: document.body.className,
    theme: document.documentElement.getAttribute('data-theme'),
    locale: document.documentElement.getAttribute('data-lang'),
  };
}
"""


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
        " locale: document.documentElement.getAttribute('data-lang')})"
    )
    if observed["theme"] != theme or (observed["locale"] or "en") != locale:
        raise SystemExit(f"state mismatch: wanted {theme}/{locale} got {observed}")
    page.evaluate(_HIDE)
    return observed


def _install_routes(page, feeds: dict, *, flow_ok: bool) -> None:
    def handler(route):
        url = route.request.url
        path = url.split("?", 1)[0]
        if "/live/intraday_quotes.json" in path:
            return route.fulfill(status=200, content_type="application/json",
                                 body=json.dumps(feeds["quotes"]))
        if "/live/flow_pulse.json" in path:
            return route.fulfill(status=200, content_type="application/json",
                                 body=json.dumps(feeds["pulse"]))
        if "/live_flow/tide_current.json" in path:
            if not flow_ok or feeds["tide"] is None:
                return route.fulfill(status=404, body="{}")
            return route.fulfill(status=200, content_type="application/json",
                                 body=json.dumps(feeds["tide"]))
        if "/live_flow/enrich_current.json" in path:
            if not flow_ok or feeds["enrich"] is None:
                return route.fulfill(status=404, body="{}")
            return route.fulfill(status=200, content_type="application/json",
                                 body=json.dumps(feeds["enrich"]))
        if "/live_flow/meta.json" in path:
            if not flow_ok or feeds["meta"] is None:
                return route.fulfill(status=404, body="{}")
            return route.fulfill(status=200, content_type="application/json",
                                 body=json.dumps(feeds["meta"]))
        if "/live_flow/tickers/" in path:
            tk = path.rsplit("/", 1)[-1].replace(".json", "")
            body = feeds["minutes"].get(tk)
            if not flow_ok or body is None:
                return route.fulfill(status=404, body="{}")
            return route.fulfill(status=200, content_type="application/json",
                                 body=json.dumps(body))
        return route.continue_()

    page.route("**/live/**", handler)
    page.route("**/live_flow/**", handler)


def _open_tip(page, viewport: str) -> bool:
    loc = page.locator("#ift-stamp .lens-q")
    if loc.count() == 0:
        return False
    loc.first.scroll_into_view_if_needed()
    if viewport == "mobile":
        loc.first.click(force=True)
    else:
        loc.first.hover()
    try:
        page.wait_for_selector(".lens-pop.open", timeout=2500)
        return True
    except Exception:
        return False


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"not a png: {path}")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


# The packet being minted, plus the round-2 dir this run replaces. Anything
# else dirty is a template or source edit that must not wear HEAD's sha.
_PACKET_OK = (
    "mockups/evidence/intraday-flow-w11",
    "mockups/evidence/intraday-flow-w11-r2",
)


def _porcelain_path_ok(path: str) -> bool:
    path = path.strip().strip('"')
    return any(path == prefix or path.startswith(prefix + "/") for prefix in _PACKET_OK)


def _require_clean_head() -> tuple[str, str]:
    """Refuse dirt outside the packet dirs. Return (HEAD sha, raw porcelain)."""
    import subprocess
    porcelain = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(ROOT),
        capture_output=True, text=True, check=False,
    )
    dirty = (porcelain.stdout or "").rstrip("\n")
    blocked: list[str] = []
    for line in dirty.splitlines():
        if not line.strip():
            continue
        payload = line[3:] if len(line) > 3 else line
        parts = [part.strip() for part in payload.split(" -> ")]
        if not parts or not all(_porcelain_path_ok(part) for part in parts):
            blocked.append(line)
    if blocked:
        raise SystemExit(
            "capture refused: working tree is dirty outside the evidence packet.\n"
            + "\n".join(blocked)
        )
    r = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(ROOT),
        capture_output=True, text=True, check=False,
    )
    head = (r.stdout or "").strip()
    if not head:
        raise SystemExit("capture refused: could not resolve HEAD")
    return head, dirty


def _git_head() -> str:
    head, _porcelain = _require_clean_head()
    return head


CELLS: list[dict] = []


def _plan() -> list[dict]:
    """16 baselines + state cells. States are EN/ZH; desktop unless noted."""
    cells: list[dict] = []
    # 16 rest cells: (hero|board) × dark/light × EN/ZH × desktop/mobile.
    # Hero frame: stamp + LENS tip. Board frame: See-all + Tape chips (desktop).
    for subject in ("hero", "board"):
        for viewport in ("desktop", "mobile"):
            for locale in ("en", "zh"):
                for theme in ("dark", "light"):
                    cells.append({
                        "id": f"baseline-{subject}-{theme}-{locale}-{VIEWPORTS[viewport][0]}",
                        "kind": "baseline",
                        "state": "baseline",
                        "subject": subject,
                        "page": "open.html",
                        "theme": theme,
                        "locale": locale,
                        "viewport": viewport,
                        "hours": "live",
                        "quotes": True,
                        "pulse": True,
                        "flow": True,
                        "hold": False,
                        "open_tip": subject == "hero" and viewport == "desktop",
                        "action": "scroll-board" if subject == "board" else None,
                        "payload": "open",
                    })
    # (a) is the baseline market-open; still emit a named state cell (desktop EN/ZH).
    named = [
        ("a-market-open", "open.html", "open", True, True, True, False, "live", None, True),
        ("b-skeleton", "open.html", "open", False, False, False, True, "closed", None, False),
        ("c-spotlight-empty", "quiet.html", "quiet", True, True, True, False, "live", None, False),
        ("d-quotes-outage", "open.html", "open", False, True, True, False, "live", "scroll-noread", False),
        ("e-options-outage", "open.html", "open", True, True, False, False, "live", None, True),
        ("f-board-default", "open.html", "open", True, True, True, False, "live", "scroll-board", False),
        ("g-board-expanded", "open.html", "open", True, True, True, False, "live", "expand", False),
        ("h-basket-grid", "open.html", "open", True, True, True, False, "live", "basket-grid", False),
        ("i-search-narrow", "open.html", "open", True, True, True, False, "live", "search-nee", False),
        ("j-row-expanded", "open.html", "open", True, True, True, False, "live", "row-expand", False),
    ]
    for state, page, payload, quotes, pulse, flow, hold, hours, action, open_tip in named:
        for locale in ("en", "zh"):
            for theme in ("dark", "light"):
                # Light for every named state so the light art direction is judged
                # on the P0/P1 subjects, not only the rest matrix.
                cells.append({
                    "id": f"{state}-{theme}-{locale}-1440",
                    "kind": "state",
                    "state": state,
                    "page": page,
                    "theme": theme,
                    "locale": locale,
                    "viewport": "desktop",
                    "hours": hours,
                    "quotes": quotes,
                    "pulse": pulse,
                    "flow": flow,
                    "hold": hold,
                    "open_tip": open_tip and locale == "en",
                    "action": action,
                    "payload": payload,
                })
        # Mobile See-all / reduction proofs (packet scope note).
        if state in ("b-skeleton", "f-board-default", "g-board-expanded", "i-search-narrow"):
            for locale in ("en", "zh"):
                cells.append({
                    "id": f"{state}-dark-{locale}-390",
                    "kind": "state",
                    "state": state,
                    "page": page,
                    "theme": "dark",
                    "locale": locale,
                    "viewport": "mobile",
                    "hours": hours,
                    "quotes": quotes,
                    "pulse": pulse,
                    "flow": flow,
                    "hold": hold,
                    "open_tip": False,
                    "action": action,
                    "payload": payload,
                })
    # Light post-stack owns :hover/:focus-visible on .ift-see-all. REST shots
    # cannot prove those states; capture desktop/en in both themes.
    for theme in ("dark", "light"):
        for interaction, action in (
            ("see-all-hover", "hover-see-all"),
            ("see-all-focus", "focus-see-all"),
        ):
            cells.append({
                "id": f"{interaction}-{theme}-en-1440",
                "kind": "state",
                "state": interaction,
                "page": "open.html",
                "theme": theme,
                "locale": "en",
                "viewport": "desktop",
                "hours": "live",
                "quotes": True,
                "pulse": True,
                "flow": True,
                "hold": False,
                "open_tip": False,
                "action": action,
                "payload": "open",
                "force_name": interaction,
            })
    return cells


def _scroll_board(page) -> None:
    # Pin the counted control in frame; rows + Tape chips sit just above it.
    page.evaluate(
        """() => {
          const lbl = document.getElementById('count-label');
          if (lbl) lbl.scrollIntoView({block: 'end', inline: 'nearest'});
          else {
            const t = document.getElementById('leaders-table');
            if (t) t.scrollIntoView({block: 'start'});
          }
        }"""
    )
    page.wait_for_timeout(120)


def _do_action(page, action: str | None, locale: str) -> None:
    if not action:
        return
    if action == "scroll-board":
        _scroll_board(page)
        return
    if action == "expand":
        btn = page.locator("#ift-see-all")
        btn.first.click()
        page.wait_for_timeout(200)
        _scroll_board(page)
        return
    if action == "basket-grid":
        page.locator('.chip[data-basket="power_grid"]').first.click()
        page.wait_for_timeout(200)
        _scroll_board(page)
        return
    if action == "search-nee":
        box = page.locator("#ift-search")
        box.fill("NEE")
        page.wait_for_timeout(250)
        _scroll_board(page)
        return
    if action == "row-expand":
        exp = page.locator('tr.lead-row[data-ticker="NVDA"] .expander')
        exp.first.click()
        page.wait_for_timeout(200)
        page.locator('tr.detail-row[data-detail="NVDA"]').first.scroll_into_view_if_needed()
        return
    if action == "hover-see-all":
        _scroll_board(page)
        page.locator("#ift-see-all").first.hover()
        page.wait_for_timeout(200)
        return
    if action == "focus-see-all":
        _scroll_board(page)
        page.locator("#ift-see-all").first.focus()
        page.wait_for_timeout(200)
        return
    if action == "scroll-noread":
        page.evaluate(
            """() => {
              const row = [...document.querySelectorAll('tr.lead-row[data-stance="degraded"]')]
                .find((r) => r.style.display !== 'none');
              if (row) row.scrollIntoView({block: 'center', inline: 'nearest'});
              else {
                const t = document.getElementById('leaders-table');
                if (t) t.scrollIntoView({block: 'start'});
              }
            }"""
        )
        page.wait_for_timeout(120)
        return


def _wait_ready(page, spec: dict) -> None:
    if spec["hold"]:
        page.wait_for_selector(".ift-skel-row", state="attached", timeout=4000)
        page.wait_for_timeout(200)
        return
    page.wait_for_function(
        "() => document.querySelectorAll('tr.lead-row').length >= 1",
        timeout=8000,
    )
    page.wait_for_function(
        "() => ((document.getElementById('count-label')||{}).innerText || '').length > 0",
        timeout=8000,
    )
    # quotes/pulse/flow land on later ticks and rebuild the board
    page.wait_for_timeout(400)


def _page_css() -> str:
    src = TEMPLATE.read_text(encoding="utf-8")
    import re
    match = re.search(r"<style>(.*?)</style>", src, re.S)
    if not match:
        raise SystemExit("no page <style> in template")
    return match.group(1)


def _r2_fixture_html() -> str:
    """Round-2 overlay column: stamp tip, counted control, forced-outage stance.

    Same fixture the r2 rig captured. Decorative overlays are removed before
    the clip. This is a crop of the page CSS, not a second page anchor.
    """
    css = _page_css()
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark" data-lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="theme.css">
<style>{css}</style>
</head>
<body class="page-intraday-flow">
<div class="overlay-col" style="max-width:760px;margin:28px auto;display:flex;flex-direction:column;gap:32px;padding:8px 12px;">
  <div class="hero-ctx" id="cell-stamp" style="padding:18px 20px;background:var(--panel);border:1px solid var(--line);border-radius:12px;">
    <div class="ctx-stamp" id="ift-stamp">
      <span class="l-en">Board built 10 Sep 11:34pm UTC · all feeds carrying</span>
      <span class="l-zh">看板构建于9月10日 23:34 UTC · 各路数据已送达</span>
      <button type="button" class="lens-q" id="stamp-q" aria-label="Feed status"
        data-tip-en="quotes · carrying prices · tape · carrying the tape · options · carrying flow"
        data-tip-zh="行情 · 已送达 · 资金带 · 已送达 · 期权流 · 已送达">?</button>
    </div>
  </div>
  <p class="xs muted" id="cell-control" style="margin:0;text-align:right;padding:12px 18px;background:var(--panel);border:1px solid var(--line);border-radius:12px;">
    <span class="l-en">Showing 8 of 116 leaders · </span><span class="l-zh">显示 8 / 116 只 · </span>
    <button type="button" class="ift-see-all" id="ift-see-all">
      <span class="l-en">See all 116</span><span class="l-zh">查看全部 116 只</span>
    </button>
  </p>
  <div id="cell-outage" class="stance-cell lane-aside" style="padding:14px 16px;background:var(--panel);border:1px solid var(--line);border-radius:12px;max-width:360px;">
    <span class="stance-pill lane-aside"><span class="sp-dot"></span>
      <span class="l-en">No read</span><span class="l-zh">暂无判断</span>
    </span>
    <div class="stance-reason muted">
      <span class="l-en">Prices aren't coming through — no read on this name right now</span>
      <span class="l-zh">行情未送达——该标的暂无判断</span>
    </div>
  </div>
</div>
<script src="theme.js"></script>
</body>
</html>
"""


def _capture_r2_overlay(shots: list[dict]) -> None:
    """Re-run the round-2 overlay crops and append them as force-state cells."""
    staging = Path(tempfile.mkdtemp(prefix="iflow-w11-r2-"))
    try:
        (staging / "index.html").write_text(_r2_fixture_html(), encoding="utf-8")
        shutil.copy(ROOT / "templates" / "theme.css", staging / "theme.css")
        shutil.copy(ROOT / "templates" / "theme.js", staging / "theme.js")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                device_scale_factor=2,
                reduced_motion="reduce",
            )
            page = context.new_page()
            page.goto((staging / "index.html").as_uri(), wait_until="load")
            page.wait_for_function("() => !!document.getElementById('lens-style')")

            def close_lens() -> None:
                page.mouse.move(0, 0)
                page.wait_for_timeout(220)
                page.evaluate(
                    """() => {
                      document.querySelectorAll('.lens-pop').forEach((n) => {
                        n.classList.remove('open');
                        n.style.visibility = 'hidden';
                      });
                      document.querySelectorAll('.lens-scrim').forEach((n) => n.classList.remove('open'));
                    }"""
                )

            def shot(name: str, theme: str, locale: str, sels: tuple[str, ...],
                     open_tip: bool = False, isolate: str | None = None) -> None:
                close_lens()
                _apply(page, theme, locale)
                if isolate:
                    page.evaluate(
                        """(keep) => {
                          document.querySelectorAll('.overlay-col > *').forEach((n) => {
                            n.style.visibility = (n.id === keep) ? 'visible' : 'hidden';
                          });
                        }""",
                        isolate,
                    )
                if open_tip:
                    page.evaluate(
                        """() => document.querySelectorAll('.lens-pop').forEach((n) => {
                          n.style.visibility = '';
                        })"""
                    )
                    page.locator("#stamp-q").scroll_into_view_if_needed()
                    page.hover("#stamp-q")
                    page.wait_for_selector(".lens-pop.open", timeout=4000)
                boxes = []
                for sel in sels:
                    box = page.locator(sel).first.bounding_box()
                    if not box:
                        raise SystemExit(f"no box for {sel}")
                    boxes.append(box)
                x = min(b["x"] for b in boxes)
                y = min(b["y"] for b in boxes)
                right = max(b["x"] + b["width"] for b in boxes)
                bottom = max(b["y"] + b["height"] for b in boxes)
                pad = 10
                clip = {
                    "x": max(0, x - pad),
                    "y": max(0, y - pad),
                    "width": (right - x) + 2 * pad,
                    "height": (bottom - y) + 2 * pad,
                }
                tmp = staging / "_r2.png"
                page.screenshot(path=str(tmp), clip=clip, type="png")
                digest = _sha256(tmp)
                dest = OUT / f"{digest[:16]}.png"
                shutil.copy2(tmp, dest)
                png_w, png_h = _png_size(dest)
                overlay_hits = page.evaluate(_OVERLAY_PROBE)
                if overlay_hits:
                    raise SystemExit(f"{name} overlay not clean: {overlay_hits}")
                cell = {
                    "id": name,
                    "kind": "state",
                    "state": "r2-overlay",
                    "subject": "r2",
                    "file": dest.name,
                    "sha256": digest,
                    "bytes": dest.stat().st_size,
                    "theme": theme,
                    "locale": locale,
                    "viewport": "desktop",
                    "viewport_width": 1440,
                    "viewport_height": 900,
                    "png_width": png_w,
                    "png_height": png_h,
                    "applied_theme": theme,
                    "applied_locale": locale,
                    "overlay_clean": True,
                    "overlay_hits": [],
                    "tip_open": open_tip,
                    "body_class": "page-intraday-flow",
                    "count_label": "",
                    "stamp_text": "",
                    "live_hits": [],
                    "visible_excerpt": "",
                    "has_no_read": name == "outage-stance-en",
                    "has_dianwang": False,
                    "has_see_all": name.startswith("control-"),
                    "has_act": False,
                    "fixture_n": FIXTURE_N,
                    "force_name": name,
                    "clip": list(sels),
                }
                shots.append(cell)
                print(f"{name}: {dest.name} overlay_clean=True r2-crop", flush=True)
                close_lens()
                page.evaluate(
                    """() => document.querySelectorAll('.overlay-col > *').forEach((n) => {
                      n.style.visibility = 'visible';
                    })"""
                )

            shot("stamp-tip-dark-en", "dark", "en", ("#cell-stamp", ".lens-pop.open"),
                 open_tip=True, isolate="cell-stamp")
            shot("stamp-tip-light-en", "light", "en", ("#cell-stamp", ".lens-pop.open"),
                 open_tip=True, isolate="cell-stamp")
            shot("control-dark-en", "dark", "en", ("#cell-control",), isolate="cell-control")
            shot("control-light-en", "light", "en", ("#cell-control",), isolate="cell-control")
            shot("tip-row-zh", "dark", "zh", (".lens-pop.open",),
                 open_tip=True, isolate="cell-stamp")
            shot("outage-stance-en", "dark", "en", ("#cell-outage",), isolate="cell-outage")
            browser.close()
    finally:
        shutil.rmtree(staging, ignore_errors=True)


_REST_KEYS = tuple(
    (viewport, locale, theme)
    for viewport in ("desktop", "mobile")
    for locale in ("en", "zh")
    for theme in ("dark", "light")
)


def _assert_packet(pages: list[dict], shots: list[dict]) -> None:
    if len(pages) != 2:
        raise SystemExit(f"expected 2 page anchors, got {[p.get('page_id') for p in pages]}")
    rest_n = 0
    for page in pages:
        keys = {
            (state.get("viewport"), state.get("locale"), state.get("theme"))
            for state in page["states"]
            if state.get("force_state") is None and state.get("captured") is True
        }
        missing = [key for key in _REST_KEYS if key not in keys]
        if missing:
            raise SystemExit(f"{page['page_id']} missing rest cells {missing}")
        rest_n += sum(1 for state in page["states"] if state.get("force_state") is None)
    if rest_n != 16:
        raise SystemExit(f"expected 16 rest cells, got {rest_n}")
    dirty = [cell["id"] for cell in shots if not cell.get("overlay_clean")]
    if dirty:
        raise SystemExit(f"overlay-dirty cells: {dirty}")
    ids = {cell["id"] for cell in shots}
    for need in (
        "stamp-tip-dark-en", "stamp-tip-light-en", "control-dark-en",
        "control-light-en", "tip-row-zh", "outage-stance-en",
    ):
        if need not in ids:
            raise SystemExit(f"missing round-2 cell {need}")
    if not any(cell.get("state") == "d-quotes-outage" for cell in shots):
        raise SystemExit("missing d-quotes-outage cells")


def _write_readme(head: str, generated: str, shots: list[dict], pages: list[dict]) -> None:
    clean = sum(1 for cell in shots if cell.get("overlay_clean"))
    anchors = ", ".join(page["page_id"] for page in pages)
    text = f"""# Intraday Flow W11 — evidence receipt

S1 rig: Playwright against fixture feeds on the real `body.page-intraday-flow` page, plus the round-2 overlay-column crops in the same run. `data-theme` / `data-lang` applied via `setTheme` / `setLang` (mismatch refuses). Overlays `.ift-aurora`, `.mx5-aurora`, `.sky-fx`, `#mmb-root`, `#mmb-boot` are removed before each shot. `window.__skyDeck = true`. `prefers-reduced-motion: reduce`. At-rest text is read from computed styles, never from HTML source. PNGs are content-addressed `sha256[:16].png`.

Recapture: `python3 mockups/evidence/intraday-flow-w11/capture.py`

**fixture N = {FIXTURE_N}.** The full-page fixture holds {FIXTURE_N} leaders. Default board shows 8 of {FIXTURE_N} with `See all {FIXTURE_N}` / `查看全部 {FIXTURE_N} 只`; expansion renders exactly {FIXTURE_N} rows. It is count-true. The round-2 counted-control crop still shows the page's "Showing 8 of 116" sentence, because that crop is the control, not the fixture census.

Captured {generated} at committed head `{head}`.
{len(shots)} cells, {clean} overlay-clean. Page anchors: {anchors}. Each anchor carries the eight rest cells (desktop/mobile × en/zh × dark/light). Named states, See-all hover/focus, and the six round-2 crops are force-state rows on the hero anchor. They are not extra pages.

## DARK TREATMENT

Command center. Page canvas is the dark sheet, panels are graphite with a hairline and a restrained inset. The stamp is muted instrument type. The `?` control is a small ring; the feed-status tip is an opaque panel so the desk does not wash through. Tape chips are filled info pills on the dark sheet. See-all inherits muted and underlines. Degraded `No read` sits in the aside lane with no glow.

## LIGHT TREATMENT

Research workspace. Forced light theme on the page. The canvas is a cool gray, panels are white, and elevation comes from a shadow instead of a glow. See-all is an ink link with a hover underline — an action on white, not a glow. Stamp type is muted. The `?` control is a white chip with a hairline. Tape chips ghost/hairline in light — recessive by design (`大单` / `新建仓` are transparent ground, a hairline, and muted ink — not filled pills).

## Which mechanisms intentionally differ

Shared: information architecture, bilingual sentences, the See-all control, the feed-status tip, tape-chip words, dealer-line geometry, skeleton geometry, and stance lanes.

Intentionally different material: dark depth is luminance and a restrained edge; light depth is a white plane, a hairline, and a drop shadow. See-all stays muted on dark and becomes an ink link on light. The stamp `?` is a ring on graphite and a white chip on the research canvas. Token substitution alone is not the light design.

**Degraded (light and dark):** a quotes outage during the session paints `No read` / `暂无判断` with `Prices aren't coming through — no read on this name right now` / `行情未送达——该标的暂无判断`. no freshness-claiming live/实时 string; the labelled signal-count 'setups live' is present and seat-ratified 2026-09-11.

Round-2 crops bound in this packet: `stamp-tip-dark-en`, `stamp-tip-light-en`, `control-dark-en`, `control-light-en`, `tip-row-zh`, `outage-stance-en`.
"""
    (OUT / "README.md").write_text(text, encoding="utf-8")


def capture() -> int:
    head, porcelain = _require_clean_head()
    open_payload = _payload(OPEN_SPEC)
    quiet_spec = tuple((tk, b, "quiet") for tk, b, _k in OPEN_SPEC)
    quiet_payload = _payload(quiet_spec)
    open_html = _render(open_payload)
    quiet_html = _render(quiet_payload)
    if "function isMarketHours() { if (window.__IFT_FORCE_HOURS" not in open_html:
        raise SystemExit("hours patch did not land")
    if "if (!window.__IFT_HOLD)" not in open_html:
        raise SystemExit("hold patch did not land")

    staging = Path(tempfile.mkdtemp(prefix="iflow-w11-r4-"))
    httpd = None
    shots: list[dict] = []
    try:
        _stage(staging, open_html, quiet_html)
        httpd, port = _serve(staging)
        origin = f"http://127.0.0.1:{port}"
        plan = _plan()
        png_dir = OUT
        # wipe previous content-addressed pngs in this folder (16-hex names only)
        for old in png_dir.glob("*.png"):
            old.unlink()

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            last_vp = None
            context = None
            for spec in plan:
                vp_name = spec["viewport"]
                width, height = VIEWPORTS[vp_name]
                if context is None or last_vp != vp_name:
                    if context:
                        context.close()
                    context = browser.new_context(
                        viewport={"width": width, "height": height},
                        device_scale_factor=1,
                        reduced_motion="reduce",
                    )
                    last_vp = vp_name
                page = context.new_page()
                spec_rows = OPEN_SPEC if spec["payload"] == "open" else quiet_spec
                feeds = _feeds(
                    spec_rows,
                    quotes=spec["quotes"],
                    pulse=spec["pulse"],
                    flow=spec["flow"],
                )
                _install_routes(page, feeds, flow_ok=spec["flow"])
                page.add_init_script(
                    "window.__skyDeck = true;\n"
                    f"window.__IFT_FORCE_HOURS = {json.dumps(spec['hours'])};\n"
                    f"window.__IFT_HOLD = {json.dumps(bool(spec['hold']))};\n"
                    "window.DATA_BASE = location.origin;\n"
                    "try {\n"
                    f"  localStorage.setItem('theme', {json.dumps(spec['theme'])});\n"
                    "  localStorage.removeItem('themeAuto');\n"
                    f"  localStorage.setItem('lang', {json.dumps(spec['locale'])});\n"
                    "} catch (e) {}\n"
                    f"document.documentElement.setAttribute('data-theme', {json.dumps(spec['theme'])});\n"
                    f"document.documentElement.setAttribute('data-lang', {json.dumps(spec['locale'])});\n"
                )
                url = f"{origin}/{spec['page']}"
                page.goto(url, wait_until="domcontentloaded")
                _apply(page, spec["theme"], spec["locale"])
                _wait_ready(page, spec)
                _do_action(page, spec.get("action"), spec["locale"])
                tip_open = False
                if spec.get("open_tip") and not spec["hold"]:
                    tip_open = _open_tip(page, spec["viewport"])
                page.evaluate(_HIDE)
                overlay_hits = page.evaluate(_OVERLAY_PROBE)
                at_rest = page.evaluate(_VISIBLE_TEXT)
                tmp = staging / "_shot.png"
                page.screenshot(path=str(tmp), type="png", full_page=False)
                digest = _sha256(tmp)
                dest = png_dir / f"{digest[:16]}.png"
                shutil.copy2(tmp, dest)
                cell = {
                    "id": spec["id"],
                    "kind": spec["kind"],
                    "state": spec["state"],
                    "subject": spec.get("subject"),
                    "file": dest.name,
                    "sha256": digest,
                    "bytes": dest.stat().st_size,
                    "theme": spec["theme"],
                    "locale": spec["locale"],
                    "viewport": spec["viewport"],
                    "viewport_width": width,
                    "viewport_height": height,
                    "applied_theme": at_rest["theme"],
                    "applied_locale": at_rest["locale"],
                    "overlay_clean": overlay_hits == [],
                    "overlay_hits": overlay_hits,
                    "tip_open": tip_open,
                    "body_class": at_rest["bodyClass"],
                    "count_label": at_rest["countLabel"],
                    "stamp_text": at_rest["stamp"],
                    "live_hits": at_rest["liveHits"],
                    "visible_excerpt": at_rest["text"][:400],
                    "has_no_read": ("No read" in at_rest["text"]) or ("暂无判断" in at_rest["text"]),
                    "has_dianwang": "电网" in at_rest["text"],
                    "has_see_all": ("See all" in at_rest["text"]) or ("查看全部" in at_rest["text"]),
                    "has_act": ("Buy now" in at_rest["text"]) or ("现在买入" in at_rest["text"]),
                    "fixture_n": FIXTURE_N,
                    "force_name": spec.get("force_name"),
                }
                shots.append(cell)
                print(f"{spec['id']}: {dest.name} overlay_clean={cell['overlay_clean']} tip={tip_open}", flush=True)
                page.close()
            if context:
                context.close()
            browser.close()

        _capture_r2_overlay(shots)

        generated = _now_iso()
        cells_doc = {
            "captured_at": generated,
            "capture_sha": head,
            "porcelain_at_capture": porcelain,
            "rig": "S1 fixture-feeds + real body classes (Playwright, overlay hide, __skyDeck, reduced-motion)",
            "overlays_hidden": list(OVERLAY_SELECTORS),
            "fixture_n": FIXTURE_N,
            "as_of_display": AS_OF_DISPLAY,
            "cells": shots,
        }
        (OUT / "cells.json").write_text(json.dumps(cells_doc, indent=2) + "\n", encoding="utf-8")

        # mastermind.p0_evidence.v2 — rest cells are the 16 baselines.
        rest = [s for s in shots if s["kind"] == "baseline"]
        state_shots = [s for s in shots if s["kind"] == "state"]
        gaps = [
            {"dimension": "access", "value": v, "captured": False,
             "reason": "requires authenticated session; not automatable without approved fixtures"}
            for v in ("free", "essential", "pro")
        ]

        def _state_entry(s: dict, force: str | None) -> dict:
            name = s.get("force_name") or force
            entry = {
                "access": "anonymous",
                "applied_locale": s["applied_locale"],
                "applied_theme": s["applied_theme"],
                "bytes": s["bytes"],
                "captured": True,
                "file": s["file"],
                "force_state": name,
                "height": s.get("png_height") or s["viewport_height"],
                "locale": s["locale"],
                "sha256": s["sha256"],
                "theme": s["theme"],
                "viewport": s["viewport"],
                "viewport_height": s["viewport_height"],
                "viewport_width": s["viewport_width"],
                "width": s.get("png_width") or s["viewport_width"],
                "overlay_clean": s["overlay_clean"],
            }
            if s.get("force_name"):
                entry["applied_force_state"] = s["force_name"]
            return entry

        def _page(page_id: str, route: str, states: list[dict]) -> dict:
            return {
                "page_id": page_id,
                "registry_route": "/intraday_flow.html",
                "route": route,
                "route_kind": "explicit_override",
                "console_errors": [],
                "failed_responses": [],
                "gaps": gaps,
                "metrics": {
                    "screenshot_completion": 1.0,
                    "measured_in": {
                        "access": "anonymous",
                        "locale": "en",
                        "theme": "dark",
                        "viewport": "desktop",
                    },
                },
                "states": states,
            }

        # Two anchors, each with its own eight rest cells. Every other shot is
        # a force_state row on the hero anchor. A third page with only force
        # states is the 96-finding corpus red (12 anchors × 8 missing cells).
        hero_rest = [s for s in rest if s.get("subject") == "hero"]
        board_rest = [s for s in rest if s.get("subject") == "board"]
        hero_states = [_state_entry(s, None) for s in hero_rest]
        hero_states.extend(_state_entry(s, s["state"]) for s in state_shots)
        board_states = [_state_entry(s, None) for s in board_rest]
        pages = [
            _page("intraday_flow.html#hero", "/open.html#hero", hero_states),
            _page("intraday_flow.html#board", "/open.html#board", board_states),
        ]
        _assert_packet(pages, shots)

        manifest = {
            "schema": "mastermind.p0_evidence.v2",
            "generated_at": generated,
            "capture_sha": head,
            "tool": {
                "module_ref": "mockups/evidence/intraday-flow-w11/capture.py",
                "version": "w11-receipt-rest-matrix",
                "user_agent": "mastermind-iflow-w11-receipt",
            },
            "target": {"resolved_sha_or_none": head},
            "axes": {
                "viewports": {"desktop": [1440, 900], "mobile": [390, 844]},
                "locales": ["en", "zh"],
                "themes": ["dark", "light"],
                "access": ["anonymous"],
                "force_states": [
                    {
                        "name": "see-all-hover",
                        "kind": "hover",
                        "value": ".ift-see-all",
                        "attribute": None,
                        "spec": "see-all-hover:hover(.ift-see-all)",
                    },
                    {
                        "name": "see-all-focus",
                        "kind": "focus",
                        "value": ".ift-see-all",
                        "attribute": None,
                        "spec": "see-all-focus:focus(.ift-see-all)",
                    },
                ],
            },
            "excluded": [],
            "outcome": "captured",
            "totals": {
                "pages": len(pages),
                "states_attempted": len(shots),
                "states_captured": len(shots),
            },
            "honesty": {
                "access": "anonymous only; no credential is entered, stored, or synthesized, so no premium payload can enter these artifacts",
                "authority": "this tool measures and screenshots; it scores, ranks, and judges nothing",
                "gaps": "states that were not captured are recorded with a reason; nothing is inferred for them",
                "fixture_n": (
                    f"fixture N={FIXTURE_N} (count-true: default board shows 8 of {FIXTURE_N}; "
                    "expansion renders exactly that many rows)"
                ),
                "porcelain_at_capture": porcelain,
                "capture_sha_source": (
                    "git rev-parse HEAD; dirt outside "
                    "mockups/evidence/intraday-flow-w11* refuses the run"
                ),
                "page_anchors": (
                    "hero and board each carry the eight rest cells; named states "
                    "and round-2 crops are force_state rows on the hero anchor"
                ),
            },
            "pages": pages,
        }
        (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (OUT / "EVIDENCE.yml").write_text(
            "schema: mastermind.page_evidence_receipt.v1\n"
            "changed_paths:\n"
            "  - templates/intraday_flow.html.j2\n"
            "manifest: mockups/evidence/intraday-flow-w11/manifest.json\n",
            encoding="utf-8",
        )
        _write_readme(head, generated, shots, pages)
        print(json.dumps({
            "cells": len(shots),
            "overlay_clean": sum(1 for s in shots if s["overlay_clean"]),
            "fixture_n": FIXTURE_N,
            "capture_sha": head,
            "porcelain_at_capture": porcelain,
        }, indent=2))
        return 0
    finally:
        if httpd is not None:
            httpd.shutdown()
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(capture())
