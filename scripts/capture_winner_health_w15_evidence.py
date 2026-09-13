#!/usr/bin/env python3
"""S1-rig evidence matrix for winner_health W15 r5.

Two data shapes, never blended in one cell:

* production — ``git show origin/main:data/top_maturation/latest.json`` verbatim
  (no ``members`` key; M1 barless degrade is the honest current state).
* production-pinned — production plus a named proof pin (rate39 / libnull).
* members-present — that artifact plus ``members`` / ``basket_id`` from the
  packet's 9-row table (membership.json truths the audit measured). Members-
  fixture copy is fixture-only and is not tonight's shippable state.

Playwright, one fresh page per cell, ``window.__skyDeck``, overlay hide,
reduced-motion, content-addressed PNGs, overlay-clean column, at-rest text
via computed styles. Refuses a dirty tree and stamps ``git rev-parse HEAD``.
SETTLE is raf×2 + fonts.ready before every shot.

Scratch-only render (SEAT RULING 3): never writes ``site/`` or ``data/``.

Usage::

    python3 -m scripts.capture_winner_health_w15_evidence
    python3 -m scripts.capture_winner_health_w15_evidence --smoke
"""
from __future__ import annotations

import hashlib
import http.server
import json
import re
import shutil
import socketserver
import struct
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
REPO = _HERE.parent
sys.path.insert(0, str(REPO))

OUT_DIR = REPO / "mockups" / "evidence" / "winner-health-w15"
CELLS_DIR = OUT_DIR / "cells"

VIEWPORTS = {
    "desktop": (1440, 900),
    "mobile": (390, 844),
}
LOCALES = ("en", "zh")
THEMES = ("dark", "light")

OVERLAY_SELECTORS = (".mx5-aurora", ".sky-fx", "#mmb-root", "#mmb-boot", ".ift-aurora")
FIND_CROP_HIDES = (
    "#t-six-month .ladder",
    '.sec[aria-label="Themes by state"]',
)
SETTLE_NOTE = "raf2+fonts.ready"

# Packet 9-row table (P0-1). Live origin/main membership.json now reports
# Cybersecurity=12 and Non-AI Tech=14; the fixture keeps the audited sizes so
# the inverted pair and the 5-of-10 hatch are the ones the packet named.
PACKET_THEME_MEMBERS = {
    "Cybersecurity": (10, "cybersecurity"),
    "US Energy Complex": (22, "us_energy"),
    "AI Software & Platforms": (17, "ai_software"),
    "Non-AI Tech & Hardware": (13, "non_ai_hw"),
    "AI Infrastructure": (24, "ai_infra"),
    "Managed Care & Insurers": (9, "managed_care"),
    "Non-AI Software": (14, "non_ai_sw"),
    "Semiconductor Equipment (WFE)": (16, "semicap_equipment"),
    "Robotics & Automation": (12, "robotics"),
}

ASSETS = (
    "theme.css",
    "theme.js",
    "data_base.js",
    "navigation-refresh.css",
    "product-nav-icons.css",
    "nav_market.js",
    "live.js",
)

_LIBNULL_TICKERS = ("CXM", "PFGC", "RUSHA")
_FIND_TICKER = "SLS"  # 9th name in primary extended_watch (past the cap)
_FIND_MISS = "ZZZQ"   # no name on the board — the zero-hit null
_RATE39_TICKER = "TPC"
_RATE8_TICKER = "DELL"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_clean_head() -> tuple[str, str]:
    porcelain = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(REPO),
        capture_output=True, text=True, check=False,
    )
    dirty = (porcelain.stdout or "").rstrip("\n")
    if dirty:
        raise SystemExit(
            "capture refused: working tree is dirty. Recapture must run at a "
            "committed head with empty `git status --porcelain`.\n" + dirty
        )
    r = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO),
        capture_output=True, text=True, check=False,
    )
    head = (r.stdout or "").strip()
    if not head:
        raise SystemExit("capture refused: could not resolve HEAD")
    return head, dirty


def _git_show(path: str) -> str:
    r = subprocess.run(
        ["git", "show", f"origin/main:{path}"], cwd=str(REPO),
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0:
        raise SystemExit(
            f"capture refused: git show origin/main:{path} failed\n"
            f"{(r.stderr or r.stdout or '').strip()}"
        )
    return r.stdout


def load_production() -> dict:
    return json.loads(_git_show("data/top_maturation/latest.json"))


def inject_members(prod: dict) -> dict:
    """Production artifact + packet 9-row members/basket_id. No other edits."""
    out = json.loads(json.dumps(prod))
    for tier in out.get("tiers") or []:
        rows = tier.get("theme_counts") or []
        for row in rows:
            name = row.get("basket")
            if name in PACKET_THEME_MEMBERS:
                members, bid = PACKET_THEME_MEMBERS[name]
                row["members"] = members
                row["basket_id"] = bid
    return out


def pin_analog_39(prod: dict, ticker: str = _RATE39_TICKER) -> dict:
    """Production shape (no members). Pins one library card to 39/40."""
    out = json.loads(json.dumps(prod))
    hit = False
    for tier in out.get("tiers") or []:
        for rows in (tier.get("states") or {}).values():
            for row in rows or []:
                if row.get("ticker") == ticker and isinstance(row.get("analog"), dict):
                    row["analog"]["n"] = 40
                    row["analog"]["topped_63td"] = 39
                    hit = True
                    break
            if hit:
                break
        if hit:
            break
    if not hit:
        raise SystemExit(f"capture refused: analog pin ticker {ticker} not found")
    return out


def pin_libnull_front(prod: dict) -> dict:
    """Production shape. Moves the three atr_x-null rows to the front of atrz breaking."""
    out = json.loads(json.dumps(prod))
    for tier in out.get("tiers") or []:
        if tier.get("key") != "atrz":
            continue
        rows = list((tier.get("states") or {}).get("breaking") or [])
        front = [r for r in rows if r.get("ticker") in _LIBNULL_TICKERS]
        rest = [r for r in rows if r.get("ticker") not in _LIBNULL_TICKERS]
        want = list(_LIBNULL_TICKERS)
        ordered = sorted(front, key=lambda r: want.index(r["ticker"]))
        if len(ordered) != 3:
            raise SystemExit(
                f"capture refused: lib-null front expected 3, got "
                f"{[r.get('ticker') for r in ordered]}"
            )
        tier["states"]["breaking"] = ordered + rest
        return out
    raise SystemExit("capture refused: atrz breaking group missing")


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


def _copy_assets(scratch: Path) -> None:
    src_dir = REPO / "templates"
    for name in ASSETS:
        src = src_dir / name
        if src.exists():
            shutil.copyfile(src, scratch / name)


def write_scratch_html(scratch: Path, name: str, ctx: dict) -> Path:
    from scripts import build_winner_health_page as bwh

    fx = scratch / f"{name}.json"
    fx.write_text(json.dumps(ctx, ensure_ascii=False), encoding="utf-8")
    html = bwh.render(REPO, fixture=fx)
    path = scratch / f"{name}.html"
    path.write_text(html, encoding="utf-8")
    return path


_INIT = """
window.__skyDeck = true;
try {
  localStorage.setItem('theme', %(theme)s);
  localStorage.removeItem('themeAuto');
  localStorage.setItem('lang', %(locale)s);
} catch (e) {}
"""

_HIDE = """
() => {
  window.__skyDeck = true;
  const sels = %s;
  sels.forEach((s) => document.querySelectorAll(s).forEach((n) => n.remove()));
  return true;
}
""" % json.dumps(list(OVERLAY_SELECTORS))

_OVERLAY_PROBE = """
() => {
  const sels = %s;
  const hits = [];
  sels.forEach((s) => {
    document.querySelectorAll(s).forEach((n) => {
      const cs = getComputedStyle(n);
      const r = n.getBoundingClientRect();
      if (cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0) return;
      if (r.width < 1 || r.height < 1) return;
      hits.push({sel: s, w: Math.round(r.width), h: Math.round(r.height)});
    });
  });
  return hits;
}
""" % json.dumps(list(OVERLAY_SELECTORS))

_VISIBLE_TEXT = """
() => {
  const lang = document.documentElement.getAttribute('data-lang') || 'en';
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const chunks = [];
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
    const text = (node.textContent || '').replace(/\\s+/g, ' ').trim();
    if (!text) continue;
    const parent = node.parentElement;
    if (!parent || parent.closest('script, style, noscript')) continue;
    if (hidden(parent)) continue;
    chunks.push(text);
  }
  return {
    text: chunks.join(' '),
    bodyClass: document.body.className,
    theme: document.documentElement.getAttribute('data-theme'),
    locale: document.documentElement.getAttribute('data-lang'),
  };
}
"""

_HSCROLL = """
() => {
  const de = document.documentElement;
  const b = document.body;
  const sw = Math.max(de.scrollWidth, b ? b.scrollWidth : 0);
  const cw = de.clientWidth;
  return {scrollWidth: sw, clientWidth: cw, overflow: sw > cw + 1};
}
"""

_CLIP_UNION = """
(sels) => {
  let x = Infinity, y = Infinity, r = -Infinity, b = -Infinity, n = 0;
  const add = (el) => {
    if (!el) return;
    const rect = el.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) return;
    x = Math.min(x, rect.x); y = Math.min(y, rect.y);
    r = Math.max(r, rect.right); b = Math.max(b, rect.bottom); n += 1;
  };
  for (const s of sels) {
    if (s === '.lens-pop.open') {
      add(document.querySelector('.lens-pop.open'));
      continue;
    }
    document.querySelectorAll(s).forEach(add);
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


def _settle(page) -> None:
    """Canvas settle: two animation frames + webfonts, then a short paint wait."""
    page.evaluate(
        """() => Promise.all([
          (document.fonts && document.fonts.ready) ? document.fonts.ready : Promise.resolve(),
          new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))
        ])"""
    )
    page.wait_for_timeout(80)


def _hide_find_extras(page) -> list[str]:
    """Find-crop-only: hide the ladder and theme panel so input + subject share a frame.

    Live page keeps both. Returned list is the per-cell ``hides`` disclosure.
    """
    page.evaluate(
        """(sels) => {
          sels.forEach((s) => {
            document.querySelectorAll(s).forEach((n) => { n.style.display = 'none'; });
          });
        }""",
        list(FIND_CROP_HIDES),
    )
    return list(FIND_CROP_HIDES)


def _offset_b0_tip(page, theme_name: str) -> None:
    """Sit the open b0 tip BELOW the hatch so it does not cover the count."""
    page.evaluate(
        """(name) => {
          const pop = document.querySelector('.lens-pop.open');
          const thm = [...document.querySelectorAll('.thm')]
            .find(el => (el.textContent || '').indexOf(name) !== -1);
          if (!pop || !thm) return false;
          const hatch = thm.querySelector('i.b0');
          const r = (hatch || thm).getBoundingClientRect();
          const pw = pop.offsetWidth, ph = pop.offsetHeight;
          const x = Math.round(Math.max(12, Math.min(
            r.left + r.width / 2 - pw / 2,
            window.innerWidth - pw - 12
          )));
          const y = Math.round(Math.min(
            window.innerHeight - ph - 8,
            r.bottom + 10
          ));
          pop.style.left = x + 'px';
          pop.style.top = y + 'px';
          return true;
        }""",
        theme_name,
    )


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
          var fx = document.querySelector('.sky-fx');
          if (fx && fx.parentNode) fx.parentNode.removeChild(fx);
          return {theme: docEl.getAttribute('data-theme'), locale: docEl.getAttribute('data-lang')};
        }""",
        {"theme": theme, "locale": locale},
    )
    observed = page.evaluate(
        "() => ({theme: document.documentElement.getAttribute('data-theme'),"
        " locale: document.documentElement.getAttribute('data-lang')})"
    )
    got_locale = observed.get("locale") or "en"
    if observed.get("theme") != theme or got_locale != locale:
        raise RuntimeError(f"state mismatch: wanted {theme}/{locale} got {observed}")
    page.evaluate(_HIDE)
    return observed


def _open_tip(page, locator, *, dedicated: bool) -> bool:
    """Open a LENS card or a string-tier data-tip.

    `.lens-q` / `.lens-term` pin on click. Bare `[data-tip-en]` hosts (b0 hatch,
    WFE label, .lib-null) are hover-only on desktop — a DOM click is a no-op.
    """
    if locator.count() == 0:
        return False
    loc = locator.first
    loc.scroll_into_view_if_needed()
    page.wait_for_timeout(40)
    if dedicated:
        loc.evaluate("el => el.click()")
    else:
        try:
            loc.hover(timeout=2000)
        except Exception:
            loc.evaluate(
                """el => {
                  const r = el.getBoundingClientRect();
                  el.dispatchEvent(new PointerEvent('pointerover', {
                    bubbles: true, cancelable: true, pointerType: 'mouse',
                    clientX: r.left + Math.max(2, r.width/2),
                    clientY: r.top + Math.max(2, r.height/2)
                  }));
                }"""
            )
        page.wait_for_timeout(160)
    try:
        page.wait_for_selector(".lens-pop.open", timeout=4000)
        return True
    except Exception:
        loc.evaluate(
            """el => {
              const r = el.getBoundingClientRect();
              el.dispatchEvent(new PointerEvent('pointerover', {
                bubbles: true, cancelable: true, pointerType: 'mouse',
                clientX: r.left + Math.max(2, r.width/2),
                clientY: r.top + Math.max(2, r.height/2)
              }));
              el.click();
            }"""
        )
        page.wait_for_timeout(200)
        return page.locator(".lens-pop.open").count() > 0


def _row(page, ticker: str, group: str | None = None):
    sel = f'.row[data-find*="{ticker}"]'
    if group:
        sel = f"{group} {sel}"
    return page.locator(sel).first


def _thm(page, name: str):
    return page.locator(".thm").filter(has_text=name).first


def _do_action(page, job: dict) -> dict:
    action = job.get("action")
    receipt: dict = {"action": action, "opened": False}
    if not action:
        return receipt
    if action == "open-analog":
        row = _row(page, job["ticker"])
        row.scroll_into_view_if_needed()
        receipt["opened"] = _open_tip(page, row.locator(".lens-term.lib"), dedicated=True)
    elif action == "open-b0":
        thm = _thm(page, job["theme_name"])
        thm.scroll_into_view_if_needed()
        receipt["opened"] = _open_tip(page, thm.locator("i.b0"), dedicated=False)
        if job.get("subject") == "p0-1-pair" and receipt["opened"]:
            _offset_b0_tip(page, job["theme_name"])
            receipt["tip_offset"] = "below-hatch"
    elif action == "open-wfe":
        el = page.locator('.tname[data-tip-en]')
        receipt["opened"] = _open_tip(page, el, dedicated=False)
    elif action == "open-libnull":
        # CXM also sits in r63 breaking, past that group's cap. Scope to atrz.
        grp = "#above-trend-changed"
        page.locator(grp).first.evaluate("el => el.scrollIntoView({block: 'start'})")
        row = _row(page, job["ticker"], group=grp)
        row.scroll_into_view_if_needed()
        receipt["opened"] = _open_tip(page, row.locator(".lib-null"), dedicated=False)
    elif action == "open-footer":
        sp = page.locator(".smallprint").first
        sp.scroll_into_view_if_needed()
        receipt["opened"] = _open_tip(page, sp.locator(".lens-q"), dedicated=True)
    elif action == "expand":
        sel = job["group"]
        page.locator(sel).first.scroll_into_view_if_needed()
        btn = page.locator(f"{sel} .wh-more").first
        if btn.count():
            btn.click()
            page.wait_for_timeout(80)
            receipt["opened"] = True
            receipt["aria"] = btn.get_attribute("aria-expanded")
    elif action == "find":
        q = page.locator("#wh-find-q")
        q.fill(job["query"])
        page.wait_for_timeout(80)
        receipt["hides"] = _hide_find_extras(page)
        page.locator("#wh-find").first.evaluate(
            "el => el.scrollIntoView({block: 'start'})"
        )
        row = _row(page, job["query"])
        visible = row.count() > 0 and row.evaluate(
            """el => {
              const cs = getComputedStyle(el);
              return cs.display !== 'none' && !el.classList.contains('is-miss');
            }"""
        )
        receipt["opened"] = bool(visible)
        receipt["found"] = job["query"]
    elif action == "find-miss":
        q = page.locator("#wh-find-q")
        q.fill(job["query"])
        page.wait_for_timeout(80)
        receipt["hides"] = _hide_find_extras(page)
        page.locator("#wh-find").first.evaluate(
            "el => el.scrollIntoView({block: 'start'})"
        )
        nul = page.locator("#wh-find-null")
        shown = nul.count() > 0 and nul.evaluate(
            """el => {
              const cs = getComputedStyle(el);
              return cs.display !== 'none' && !el.hidden;
            }"""
        )
        more_present = page.locator(".wh-more").count() > 0
        receipt["opened"] = bool(shown)
        receipt["found"] = job["query"]
        receipt["null_visible"] = bool(shown)
        receipt["see_all_present"] = more_present
    elif action == "find-placeholder":
        receipt["hides"] = _hide_find_extras(page)
        page.locator("#wh-find").first.evaluate(
            "el => el.scrollIntoView({block: 'start'})"
        )
        ph = page.locator("#wh-find-q").get_attribute("placeholder") or ""
        aria = page.locator("#wh-find-q").get_attribute("aria-label") or ""
        receipt["opened"] = True
        receipt["placeholder"] = ph
        receipt["aria_label"] = aria
    page.wait_for_timeout(120)
    return receipt


def _jobs(*, smoke: bool) -> list[dict]:
    jobs: list[dict] = []

    def four(subject, *, html, shape, viewport="desktop", action=None, clip=None,
             full_page=False, **extra):
        w, h = VIEWPORTS[viewport]
        for locale in LOCALES:
            for theme in THEMES:
                jobs.append({
                    "id": f"{subject}-{theme}-{locale}-{w}",
                    "subject": subject, "html": html, "shape": shape,
                    "viewport": viewport, "locale": locale, "theme": theme,
                    "width": w, "height": h, "action": action,
                    "clip": clip, "full_page": full_page, **extra,
                })

    # 8 full-page baselines — production shape (M1 degrade visible).
    for viewport in ("desktop", "mobile"):
        four("baseline", html="prod", shape="production",
             viewport=viewport, full_page=True)

    # P0-1 members-present: pair + partial hatch.
    four("p0-1-pair", html="members", shape="members-present",
         action="open-b0", theme_name="AI Infrastructure",
         clip=[".sec[aria-label='Themes by state']", ".lens-pop.open"])
    four("p0-1-partial", html="members", shape="members-present",
         action="open-b0", theme_name="Cybersecurity",
         clip=[".thm", ".lens-pop.open"])  # refined in action via Cyber row

    # P0-2: 39/40 nearly-all (production-pinned rate39); 8-in-10 verbatim production.
    four("p0-2-nearly-all", html="rate39", shape="production-pinned", pin="rate39",
         action="open-analog", ticker=_RATE39_TICKER,
         clip=[".row", ".lens-pop.open"])
    four("p0-2-8in10", html="prod", shape="production",
         action="open-analog", ticker=_RATE8_TICKER,
         clip=[".row", ".lens-pop.open"])

    # P1-1: n=1 survivor suppression on the 39/40 pin; n>=5 on DELL.
    four("p1-1-n1", html="rate39", shape="production-pinned", pin="rate39",
         action="open-analog", ticker=_RATE39_TICKER,
         clip=[".row", ".lens-pop.open"])
    four("p1-1-nge5", html="prod", shape="production",
         action="open-analog", ticker=_RATE8_TICKER,
         clip=[".row", ".lens-pop.open"])

    # P1-2 three lib-null rows, tip on CXM.
    four("p1-2-libnull", html="libnull", shape="production-pinned", pin="libnull",
         action="open-libnull", ticker="CXM",
         clip=["#above-trend-changed .row", ".lens-pop.open"])

    # P1-3 WFE tip — needs basket_id, so members-present.
    four("p1-3-wfe", html="members", shape="members-present",
         action="open-wfe",
         clip=[".thm", ".lens-pop.open"])

    # P1-4 footer + LENS.
    four("p1-4-footer", html="prod", shape="production",
         action="open-footer",
         clip=[".smallprint", ".lens-pop.open"])

    # P1-5 backdrop + shelf.
    four("p1-5-209s", html="prod", shape="production",
         clip=[".backdrop", ".shelf"])

    # P1-6 cap / expand / find (desktop) + find at 390w.
    four("p1-6-capped", html="prod", shape="production",
         clip=["#g-wear"])
    four("p1-6-expanded", html="prod", shape="production",
         action="expand", group="#g-wear",
         clip=["#g-wear"])
    four("p1-6-find", html="prod", shape="production",
         action="find", query=_FIND_TICKER,
         clip=["#wh-find", "#g-wear"], hides=list(FIND_CROP_HIDES))
    four("p1-6-find", html="prod", shape="production",
         viewport="mobile", action="find", query=_FIND_TICKER,
         clip=["#wh-find", "#g-wear"], hides=list(FIND_CROP_HIDES))

    # MAJOR-1 zero-hit null: 4 desktop theme×lane + one 390.
    four("find-zerohit", html="prod", shape="production",
         action="find-miss", query=_FIND_MISS,
         clip=["#wh-find", "#wh-find-null"], hides=list(FIND_CROP_HIDES))
    jobs.append({
        "id": "find-zerohit-dark-en-390",
        "subject": "find-zerohit", "html": "prod", "shape": "production",
        "viewport": "mobile", "locale": "en", "theme": "dark",
        "width": 390, "height": 844, "action": "find-miss",
        "query": _FIND_MISS, "clip": ["#wh-find", "#wh-find-null"],
        "full_page": False, "hides": list(FIND_CROP_HIDES),
    })

    # MINOR-2: empty ZH find input showing the ZH placeholder (the missing pixel).
    jobs.append({
        "id": "find-placeholder-dark-zh-1440",
        "subject": "find-placeholder", "html": "prod", "shape": "production",
        "viewport": "desktop", "locale": "zh", "theme": "dark",
        "width": 1440, "height": 900, "action": "find-placeholder",
        "clip": ["#wh-find"], "full_page": False,
        "hides": list(FIND_CROP_HIDES),
    })

    # M1 degrade — production theme panel, barless.
    four("m1-degrade", html="prod", shape="production",
         clip=[".sec[aria-label='Themes by state']"])

    if smoke:
        want = {
            ("baseline", "desktop"),
            ("p0-1-pair", "desktop"),
            ("p0-2-nearly-all", "desktop"),
            ("p1-6-find", "mobile"),
        }
        keep = []
        for j in jobs:
            if j["theme"] != "dark" or j["locale"] != "en":
                continue
            if (j["subject"], j["viewport"]) in want:
                keep.append(j)
        return keep
    return jobs


def _refine_clip(page, job: dict) -> list[str] | None:
    """Tighten clip selectors now that the page is in the right state."""
    clip = list(job.get("clip") or [])
    action = job.get("action")
    if job["subject"] == "p0-1-partial":
        return None  # computed below
    if action == "open-analog" and job.get("ticker"):
        return None
    if action == "open-libnull":
        return None
    if action == "open-wfe":
        return None
    if action == "open-b0" and job["subject"] == "p0-1-pair":
        return [".sec[aria-label='Themes by state']", ".lens-pop.open"]
    return clip or None


def _clip_box(page, job: dict, width: int, height: int) -> dict | None:
    subject = job["subject"]
    action = job.get("action")
    sels: list[str] = []
    if subject == "p0-1-partial":
        # Union of the Cybersecurity row + open tip.
        box = page.evaluate(
            """() => {
              const thm = [...document.querySelectorAll('.thm')]
                .find(el => /Cybersecurity|网络安全/.test(el.textContent || ''));
              const pop = document.querySelector('.lens-pop.open');
              const els = [thm, pop].filter(Boolean);
              if (!els.length) return null;
              let x=Infinity,y=Infinity,r=-Infinity,b=-Infinity;
              for (const el of els) {
                const rect = el.getBoundingClientRect();
                x=Math.min(x,rect.x); y=Math.min(y,rect.y);
                r=Math.max(r,rect.right); b=Math.max(b,rect.bottom);
              }
              const pad=12;
              return {
                x: Math.max(0, x-pad), y: Math.max(0, y-pad),
                width: Math.min(window.innerWidth, r-x+2*pad),
                height: Math.min(window.innerHeight, b-y+2*pad)
              };
            }"""
        )
        return box
    if action == "open-analog" and job.get("ticker"):
        ticker = job["ticker"]
        box = page.evaluate(
            """(tk) => {
              const row = document.querySelector('.row[data-find*="'+tk+'"]');
              const pop = document.querySelector('.lens-pop.open');
              const els = [row, pop].filter(Boolean);
              if (!els.length) return null;
              let x=Infinity,y=Infinity,r=-Infinity,b=-Infinity;
              for (const el of els) {
                const rect = el.getBoundingClientRect();
                x=Math.min(x,rect.x); y=Math.min(y,rect.y);
                r=Math.max(r,rect.right); b=Math.max(b,rect.bottom);
              }
              const pad=12;
              return {
                x: Math.max(0, x-pad), y: Math.max(0, y-pad),
                width: Math.min(window.innerWidth, r-x+2*pad),
                height: Math.min(window.innerHeight, b-y+2*pad)
              };
            }""",
            ticker,
        )
        return box
    if action == "open-libnull":
        box = page.evaluate(
            """(tickers) => {
              const root = document.querySelector('#above-trend-changed') || document;
              const rows = tickers.map(tk =>
                root.querySelector('.row[data-find*="'+tk+'"]')).filter(Boolean);
              const pop = document.querySelector('.lens-pop.open');
              const hd = document.querySelector('#above-trend-changed .grp-hd');
              const els = [hd, ...rows, pop].filter(Boolean);
              if (!els.length) return null;
              let x=Infinity,y=Infinity,r=-Infinity,b=-Infinity;
              for (const el of els) {
                const rect = el.getBoundingClientRect();
                x=Math.min(x,rect.x); y=Math.min(y,rect.y);
                r=Math.max(r,rect.right); b=Math.max(b,rect.bottom);
              }
              const pad=12;
              return {
                x: Math.max(0, x-pad), y: Math.max(0, y-pad),
                width: Math.min(window.innerWidth, r-x+2*pad),
                height: Math.min(window.innerHeight, b-y+2*pad)
              };
            }""",
            list(_LIBNULL_TICKERS),
        )
        return box
    if action == "open-wfe":
        box = page.evaluate(
            """() => {
              const thm = [...document.querySelectorAll('.thm')]
                .find(el => /WFE|晶圆厂/.test(el.textContent || ''));
              const pop = document.querySelector('.lens-pop.open');
              const els = [thm, pop].filter(Boolean);
              if (!els.length) return null;
              let x=Infinity,y=Infinity,r=-Infinity,b=-Infinity;
              for (const el of els) {
                const rect = el.getBoundingClientRect();
                x=Math.min(x,rect.x); y=Math.min(y,rect.y);
                r=Math.max(r,rect.right); b=Math.max(b,rect.bottom);
              }
              const pad=12;
              return {
                x: Math.max(0, x-pad), y: Math.max(0, y-pad),
                width: Math.min(window.innerWidth, r-x+2*pad),
                height: Math.min(window.innerHeight, b-y+2*pad)
              };
            }"""
        )
        return box
    sels = _refine_clip(page, job)
    if not sels:
        return None
    box = page.evaluate(_CLIP_UNION, sels)
    return box


def _screenshot(page, job: dict) -> bytes:
    width, height = job["width"], job["height"]
    if job.get("full_page"):
        return page.screenshot(type="png", full_page=True)
    # Scroll section hosts into view. Do not scroll generic `.row` / `.thm` —
    # those match the first row on the page and can push the real subject off.
    for sel in job.get("clip") or []:
        if sel in {".lens-pop.open", ".row", ".thm"}:
            continue
        loc = page.locator(sel).first
        if loc.count():
            try:
                loc.scroll_into_view_if_needed(timeout=5000)
            except Exception:
                pass
    if job.get("subject") == "p0-1-pair" and job.get("theme_name"):
        _offset_b0_tip(page, job["theme_name"])
    page.wait_for_timeout(80)
    box = _clip_box(page, job, width, height)
    if box and box.get("width", 0) >= 4 and box.get("height", 0) >= 4:
        x = max(0.0, min(float(box["x"]), float(width) - 4))
        y = max(0.0, min(float(box["y"]), float(height) - 4))
        clip = {
            "x": x,
            "y": y,
            "width": max(4.0, min(float(box["width"]), float(width) - x)),
            "height": max(4.0, min(float(box["height"]), float(height) - y)),
        }
        if clip["width"] >= 4 and clip["height"] >= 4:
            return page.screenshot(type="png", clip=clip)
    return page.screenshot(type="png")


def _gate_html(html: str) -> dict:
    h1 = len(re.findall(r"<h1\b", html))
    one_in_one = len(re.findall(r"about 1 in 1[^0-9]", html))
    bare_em = html.count(">—<")
    return {
        "h1": h1,
        "about_1_in_1": one_in_one,
        "bare_em_dash": bare_em,
        "h1_ok": h1 == 1,
        "one_in_one_ok": one_in_one == 0,
        "bare_em_ok": bare_em == 0,
    }


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


def capture(*, smoke: bool = False) -> dict:
    from playwright.sync_api import sync_playwright

    head, porcelain = _require_clean_head()
    generated_at = _now_iso()

    prod = load_production()
    members = inject_members(prod)
    rate39 = pin_analog_39(prod)
    libnull = pin_libnull_front(prod)

    scratch = Path(tempfile.mkdtemp(prefix="wh_w15_evidence_"))
    _copy_assets(scratch)
    html_paths = {
        "prod": write_scratch_html(scratch, "prod", prod),
        "members": write_scratch_html(scratch, "members", members),
        "rate39": write_scratch_html(scratch, "rate39", rate39),
        "libnull": write_scratch_html(scratch, "libnull", libnull),
    }
    gates = {name: _gate_html(p.read_text(encoding="utf-8"))
             for name, p in html_paths.items()}

    # Programmatic packet assertion on every scratch render.
    for name, g in gates.items():
        if g["about_1_in_1"] != 0:
            raise SystemExit(
                f"capture refused: {name}.html still has "
                f"{g['about_1_in_1']} 'about 1 in 1' hits"
            )
        if g["h1"] != 1:
            raise SystemExit(f"capture refused: {name}.html h1 count={g['h1']}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)
    if not smoke:
        for stale in CELLS_DIR.glob("*.png"):
            stale.unlink()

    jobs = _jobs(smoke=smoke)
    httpd, port = _serve(scratch)
    cells: list[dict] = []
    written: set[str] = set()
    aliases: dict[str, str] = {}

    try:
        manager = sync_playwright().start()
        try:
            browser = manager.chromium.launch(headless=True)
            for job in jobs:
                theme, locale = job["theme"], job["locale"]
                width, height = job["width"], job["height"]
                entry: dict = {
                    "id": job["id"],
                    "subject": job["subject"],
                    "shape": job["shape"],
                    "pin": job.get("pin") or "",
                    "html": job["html"],
                    "viewport": job["viewport"],
                    "locale": locale,
                    "theme": theme,
                    "viewport_width": width,
                    "viewport_height": height,
                    "action": job.get("action"),
                    "hides": list(job.get("hides") or []),
                    "settle": SETTLE_NOTE,
                }
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    locale="zh-CN" if locale == "zh" else "en-US",
                    color_scheme=theme,
                    device_scale_factor=1,
                    reduced_motion="reduce",
                    has_touch=job["viewport"] == "mobile",
                    is_mobile=job["viewport"] == "mobile",
                )
                context.add_init_script(
                    (_INIT % {
                        "theme": json.dumps(theme),
                        "locale": json.dumps(locale),
                    }).strip() + ";"
                )
                page = context.new_page()
                try:
                    url = f"http://127.0.0.1:{port}/{job['html']}.html"
                    response = page.goto(url, wait_until="load", timeout=45000)
                    if response is None or not response.ok:
                        raise RuntimeError(f"HTTP {getattr(response, 'status', 'none')}")
                    page.wait_for_timeout(120)
                    observed = _apply(page, theme, locale)
                    page.wait_for_timeout(80)
                    action_receipt = _do_action(page, job)
                    overlay = page.evaluate(_OVERLAY_PROBE) or []
                    at_rest = page.evaluate(_VISIBLE_TEXT) or {}
                    hscroll = page.evaluate(_HSCROLL) or {}
                    # Re-open after probes: hover tips schedule-close on pointerout
                    # and the overlay/text evaluates can steal the pointer.
                    if job.get("action") in {
                        "open-analog", "open-b0", "open-wfe",
                        "open-libnull", "open-footer",
                    }:
                        action_receipt = _do_action(page, job)
                    hides = list(job.get("hides") or action_receipt.get("hides") or [])
                    entry["hides"] = hides
                    _settle(page)
                    png = _screenshot(page, job)
                    name, digest, pw, ph = content_address_png(png, CELLS_DIR)
                    alias = f"{job['id']}.png"
                    (CELLS_DIR / alias).write_bytes(png)
                    written.add(name)
                    written.add(alias)
                    aliases[alias] = name
                    overlay_clean = not overlay
                    visible = (at_rest.get("text") or "")
                    entry.update({
                        "captured": True,
                        "file": name,
                        "alias": alias,
                        "sha256": digest,
                        "bytes": len(png),
                        "width": pw,
                        "height": ph,
                        "applied_theme": observed.get("theme"),
                        "applied_locale": observed.get("locale"),
                        "body_class": at_rest.get("bodyClass") or "",
                        "overlay": overlay,
                        "overlay_clean": overlay_clean,
                        "action_receipt": action_receipt,
                        "h_scroll": hscroll,
                        "visible_has_nearly_all": "nearly all" in visible or "几乎全部" in visible,
                        "visible_has_8in10": "about 8 in 10" in visible or "大约 10 段里有 8 段" in visible,
                        "visible_has_suppressed": (
                            "too few to call typical" in visible
                            or "不足以称作典型" in visible
                            or "too few to call a typical drop" in visible
                        ),
                        "visible_has_across": "across those" in visible or "基于这" in visible,
                        "visible_has_zerohit": (
                            "isn't tracked here" in visible
                            or "不在跟踪范围内" in visible
                        ),
                        "visible_text_head": visible[:240],
                    })
                    flag = "ok" if overlay_clean else "OVERLAY"
                except Exception as exc:  # noqa: BLE001
                    entry.update({
                        "captured": False,
                        "reason": f"{type(exc).__name__}: {exc}",
                        "overlay_clean": False,
                    })
                    flag = "FAIL"
                finally:
                    context.close()
                cells.append(entry)
                print(f"  {entry['id']}: {flag}", flush=True)
        finally:
            browser.close()
            manager.stop()
    finally:
        httpd.shutdown()
        shutil.rmtree(scratch, ignore_errors=True)

    attempted = len(cells)
    captured_n = sum(1 for c in cells if c.get("captured"))
    overlay_n = sum(1 for c in cells if c.get("overlay_clean"))
    outcome = "captured" if captured_n == attempted and attempted else "partial"
    by_sha: dict[str, list[str]] = {}
    for c in cells:
        digest = c.get("sha256") or ""
        if digest and c.get("captured"):
            by_sha.setdefault(digest, []).append(c["id"])
    for c in cells:
        siblings = [i for i in by_sha.get(c.get("sha256") or "", []) if i != c["id"]]
        c["reused_image"] = siblings[0] if siblings else ""
    hscroll_390 = [
        {"id": c["id"], "locale": c["locale"], "overflow": (c.get("h_scroll") or {}).get("overflow")}
        for c in cells if c.get("viewport") == "mobile" and c.get("captured")
    ]

    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": generated_at,
        "tool": {
            "module_ref": "scripts/capture_winner_health_w15_evidence.py",
            "version": "w15-r5-s1",
            "capture_method": (
                "playwright, one fresh page per cell, fixture HTML in a scratch "
                "dir (never site/ or data/). data-theme/data-lang via setTheme/"
                "setLang with refuse-on-mismatch. window.__skyDeck skips "
                "skyToggleFx. overlays removed. sha256 from screenshot bytes. "
                "at-rest text via computed styles. SETTLE is raf×2 + fonts.ready "
                "before every shot."
            ),
        },
        "target": {
            "kind": "scratch_fixture_html",
            "resolved_sha_or_none": head,
            "porcelain_at_capture": porcelain,
            "capture_sha_source": "git rev-parse HEAD after empty git status --porcelain",
        },
        "shapes": {
            "production": (
                "origin/main data/top_maturation/latest.json verbatim; no members "
                "key; theme bars absent by design until the nightly emits members "
                "(M1 degrade)"
            ),
            "production-pinned": (
                "production shape plus a named proof pin (see per-cell pin). "
                "rate39 = TPC analog 39/40; libnull = CXM/PFGC/RUSHA moved to "
                "the front of atrz breaking. Members still absent."
            ),
            "members-present": (
                "production artifact + members/basket_id injected from the packet "
                "9-row table (membership.json truths the audit measured: "
                "Cybersecurity=10, AI Infrastructure=24, …). Live origin/main "
                "membership.json now reports Cybersecurity=12 / Non-AI Tech=14; "
                "the fixture keeps the packet table so the inverted pair and the "
                "5-of-10 hatch are the ones the packet named. Cells on this shape "
                "carry fixture-only copy and are not tonight's shippable state."
            ),
            "production_pins": {
                "rate39": (
                    f"TPC analog pinned to 39/40 for the packet's named nearly-all "
                    f"/ n=1-survivor fixture; members still absent"
                ),
                "libnull": (
                    "CXM/PFGC/RUSHA moved to the front of atrz breaking so the "
                    "three lib-null rows share a frame (they sit at indices "
                    "12/43/52 past the cap in the verbatim artifact); members still absent"
                ),
            },
        },
        "axes": {
            "viewports": {k: list(v) for k, v in VIEWPORTS.items()},
            "locales": list(LOCALES),
            "themes": list(THEMES),
        },
        "selection": {
            "mode": "explicit_subjects",
            "subjects": sorted({c["subject"] for c in cells}),
        },
        "aliases": aliases,
        "outcome": outcome,
        "totals": {
            "states_attempted": attempted,
            "states_captured": captured_n,
            "overlay_clean": overlay_n,
        },
        "gates": gates,
        "h_scroll_390": hscroll_390,
        "find_ticker": _FIND_TICKER,
        "find_miss": _FIND_MISS,
        "overlays_hidden": list(OVERLAY_SELECTORS),
        "find_crop_hides": list(FIND_CROP_HIDES),
        "settle": SETTLE_NOTE,
        "cells": cells,
        "honesty": {
            "page": (
                "templates/winner_health.html.j2 rendered through "
                "scripts.build_winner_health_page.render against scratch JSON. "
                "write_page is not used (it would touch site/data_base.js). "
                "Live body has no page-* class; the fixture matches that. "
                "Overlays .mx5-aurora/.sky-fx/#mmb-root/#mmb-boot/.ift-aurora "
                "are removed. Find crops hide #t-six-month .ladder and the "
                "theme panel so the input and the matched/null row share a "
                "frame (per-cell hides). Inter webfonts are not copied; system "
                "UI fonts render. Members-present cells carry fixture-only "
                "copy (packet 9-row table) and are not tonight's shippable state."
            ),
        },
    }
    return {"manifest": manifest, "written": sorted(written), "outcome": outcome}


def _write_readme(manifest: dict) -> str:
    head = manifest["target"]["resolved_sha_or_none"]
    porcelain = manifest["target"]["porcelain_at_capture"]
    porcelain_s = "(empty)" if porcelain == "" else porcelain
    overlay_sels = manifest.get("overlays_hidden") or list(OVERLAY_SELECTORS)
    find_hides = manifest.get("find_crop_hides") or list(FIND_CROP_HIDES)
    lines = [
        "# Winner Health W15 r5 — evidence matrix",
        "",
        "S1 rig: Playwright against scratch-rendered `winner_health.html.j2` on the "
        "real page skeleton (`_site_nav` included; live `<body>` has no `page-*` "
        "class, and the fixture matches that). `data-theme` / `data-lang` applied "
        "via `setTheme` / `setLang` (mismatch refuses). Overlays "
        "`.mx5-aurora`, `.sky-fx`, `#mmb-root`, `#mmb-boot`, `.ift-aurora` are "
        "removed before each shot. `window.__skyDeck = true`. "
        "`prefers-reduced-motion: reduce`. At-rest text is read from computed "
        "styles (display/visibility/opacity + inactive `.l-en`/`.l-zh` spans "
        "skipped), never from HTML source. PNGs are content-addressed "
        "`sha256[:16].png` plus an alias twin. SETTLE is two animation frames "
        "+ `document.fonts.ready` before every shot.",
        "",
        f"Recapture: `python3 -m scripts.capture_winner_health_w15_evidence`",
        "",
        f"Captured {manifest['generated_at']} at committed head `{head}` "
        f"with empty `git status --porcelain` (rig-enforced). "
        f"Porcelain receipt: `{porcelain_s}`. "
        f"{manifest['totals']['states_captured']}/{manifest['totals']['states_attempted']} "
        f"cells captured, {manifest['totals']['overlay_clean']} overlay-clean.",
        "",
        "## TWO DATA SHAPES (never blended in one cell)",
        "",
        "**Production shape** (the committed artifact verbatim): "
        "`git show origin/main:data/top_maturation/latest.json`. Today's "
        "committed artifact has **no `members` key**, so the production-shaped "
        "render exercises the r2 M1 degrade — barless count-only theme rows, "
        "no width note. Theme bars absent by design until the nightly emits "
        "`members` (M1 degrade). The 8 full-page baselines and every "
        "`shape=production` cell run on this.",
        "",
        "**Production-pinned** (12 cells): production shape plus a named proof "
        "pin, disclosed per-cell in the Pin column. `rate39` = TPC analog "
        "pinned to 39/40 (p0-2-nearly-all, p1-1-n1). `libnull` = CXM/PFGC/RUSHA "
        "moved to the front of atrz breaking (p1-2-libnull). Members still absent. "
        "p0-2-8in10 and p1-1-nge5 stay `production` — DELL is 8-in-10 / n≥5 in "
        "the verbatim artifact.",
        "",
        "**Members-present fixture** (production artifact + `members` injected "
        "from `data/baskets/membership.json` truths — the packet's own 9-row "
        "table): Cybersecurity 10, US Energy Complex 22, AI Software & Platforms "
        "17, Non-AI Tech & Hardware 13, AI Infrastructure 24, Managed Care & "
        "Insurers 9, Non-AI Software 14, Semiconductor Equipment (WFE) 16, "
        "Robotics & Automation 12, plus `basket_id` so the WFE tip keys. Live "
        "`origin/main` membership.json now reports Cybersecurity=12 and Non-AI "
        "Tech=14; the fixture keeps the packet table so the inverted pair and "
        "the 5-of-10 hatch are the ones the packet named. **These cells carry "
        "fixture-only copy and are not tonight's shippable state** — once the "
        "nightly emits `members`, Cybersecurity will read 12 and Non-AI Tech 14, "
        "not 10 and 13. The geometry claim (bar width = members) is invariant "
        "to that drift. P0-1 and P1-3 run on this.",
        "",
        "## DARK TREATMENT",
        "",
        "Command center. Page canvas is the estate `--bg` with the maturation "
        "ramp (`--m1` slate-teal → `--m2` brass → `--m3` ochre → `--m4` violet "
        "ash) as wear, not a siren. Hero/nullhero sit in luminance depth with "
        "restrained glass, no drop shadow. Unobserved tail (`.bar .b0`) is a "
        "muted hatch in the well. LENS is a glass card. Instrument calm: "
        "counts are tabular, stances are one clause.",
        "",
        "## LIGHT TREATMENT",
        "",
        "Research workspace. Forced `data-theme=\"light\"` on `<html>` and judged "
        "as a design, not a tint. Canvas is the cool estate light `--bg`; panels "
        "are white material. Depth is shadow instead of glow: "
        "`html[data-theme=\"light\"] .hero` / `.nullhero` carry "
        "`box-shadow: 0 1px 2px …, 0 10px 26px -18px …`. Hairline discipline: "
        "`.bar` and `.wear i` get inset 1px rings; `.leg` border is re-inked. "
        "Sparkline underlay opacity is raised to `.23` (`.sp-uw`). Unobserved "
        "tail is a hairline hatch plus inset ring — not a token-swapped well. "
        "Verified in r1 against those three mechanisms (shadow / hairline / "
        "underlay) and re-used here.",
        "",
        "## Which mechanisms intentionally differ",
        "",
        "Shared: information architecture, bilingual `.l-en`/`.l-zh`, theme "
        "panel, LENS, group cap + find, shelf vs backdrop population words, "
        "one-sentence footer.",
        "",
        "Intentionally different material: dark depth is luminance + restrained "
        "glass; light depth is white plane + hairline + drop shadow. Hatch of "
        "the unobserved tail is a muted well on dark and a hairline hatch + "
        "inset ring on light. Token substitution alone is not the light design.",
        "",
        "**Degraded (both themes):** when `members` is absent, theme rows are "
        "count-only (board-presence copy) and the width note is withheld. That "
        "is the honest current production state.",
        "",
        "## Cells",
        "",
        "| ID | Subject | Shape | Pin | Theme | Lang | Viewport | Overlay | SETTLE | hides | reused-image | Captured |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for c in manifest["cells"]:
        overlay = "yes" if c.get("overlay_clean") else (
            "NO: " + json.dumps(c.get("overlay") or c.get("reason"))
        )
        hides = c.get("hides") or []
        hides_s = ", ".join(f"`{s}`" for s in hides) if hides else "—"
        reused = c.get("reused_image") or "—"
        lines.append(
            f"| `{c.get('id','')}` | {c.get('subject')} | {c.get('shape')} | "
            f"{c.get('pin') or '—'} | {c.get('theme')} | {c.get('locale')} | "
            f"{c.get('viewport')} | {overlay} | {c.get('settle') or SETTLE_NOTE} | "
            f"{hides_s} | {reused} | "
            f"{'yes' if c.get('captured') else c.get('reason','no')} |"
        )
    h390 = manifest.get("h_scroll_390") or []
    h390_ok = all(not row.get("overflow") for row in h390) if h390 else False
    lines += [
        "",
        "## P1-6 390w find receipt",
        "",
        f"Find query `{manifest.get('find_ticker')}` (9th name in primary "
        "`extended_watch`, past the cap of 8). Cells `p1-6-find-*-390` type "
        "that needle; the group uncaps and the row is not `.is-miss`.",
        "",
        f"Zero-hit query `{manifest.get('find_miss')}`: cells `find-zerohit-*` "
        "type a miss; groups stay `.is-quiet`, the null sentence is visible "
        "both lanes, and the counted See-all node remains in the DOM.",
        "",
        "## No page h-scroll at 390",
        "",
        f"Probe `documentElement.scrollWidth > clientWidth+1` on every 390w "
        f"cell: {'PASS (no overflow)' if h390_ok else 'see table'}.",
        "",
    ]
    if h390:
        lines += [
            "| Cell | Locale | Overflow |",
            "|---|---|---|",
        ]
        for row in h390:
            lines.append(
                f"| `{row['id']}` | {row['locale']} | "
                f"{'YES' if row.get('overflow') else 'no'} |"
            )
        lines.append("")
    gates = manifest.get("gates") or {}
    lines += [
        "## Scratch-render gates",
        "",
        "| HTML | shape | `grep -c '<h1'` | `about 1 in 1` | `>—<` |",
        "|---|---|---|---|---|",
    ]
    shape_for = {
        "prod": "production",
        "members": "members-present",
        "rate39": "production (TPC 39/40 pin)",
        "libnull": "production (lib-null front pin)",
    }
    for name, g in gates.items():
        lines.append(
            f"| `{name}.html` | {shape_for.get(name, name)} | {g.get('h1')} | "
            f"{g.get('about_1_in_1')} | {g.get('bare_em_dash')} |"
        )
    lines += [
        "",
        "Packet assertion: `grep -c 'about 1 in 1[^0-9]'` == 0 on every scratch render.",
        "",
        "## Capture-harness disclosure",
        "",
        "`theme.js` `skyToggleFx` appends a `.sky-fx` sun/moon disc for ~1100ms "
        "after every `setTheme`. This harness seeds `window.__skyDeck = true` "
        "and removes leftover `.sky-fx` / `#mmb-boot` / `.mx5-aurora` after apply. "
        "Live toggles still play the flourish. Per-crop overlay column is above.",
        "",
        "Find / zero-hit / placeholder crops additionally hide the primary "
        "ladder and the theme panel (they sit between `#wh-find` and the groups) "
        "so the input and the matched row or the null sentence share a frame. "
        "Live page keeps both. Those extra hides are named per-cell in the "
        "`hides` column; every other cell is empty there.",
        "",
        "Full hide-selector list used by the rig (verbatim):",
        "",
        f"- overlays removed on every cell: `{', '.join(overlay_sels)}`",
        f"- find-crop extras (find / find-zerohit / find-placeholder only): "
        f"`{', '.join(find_hides)}`",
        "",
        "Content-addressed twins: 8 cells in r3 were byte-identical pairs "
        "(p1-1-n1 ≡ p0-2-nearly-all; p1-1-nge5 ≡ p0-2-8in10). The `reused-image` "
        "column names the sibling cell that shares the same `sha256[:16].png`. "
        "Coverage is still counted per cell.",
        "",
        "SEAT RULING 3: production JSON is copied via `git show origin/main:…` "
        "into a scratch dir; the builder's `render()` writes HTML there. This "
        "worktree never opts into `site/` or `data/`.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smoke", action="store_true",
                    help="capture a handful of dark/EN cells and stop")
    args = ap.parse_args(argv)

    print("winner_health W15 r5 capture", flush=True)
    payloads = capture(smoke=args.smoke)
    manifest = payloads["manifest"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    readme = _write_readme(manifest)
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    print(
        f"wrote {OUT_DIR} outcome={payloads['outcome']} "
        f"captured={manifest['totals']['states_captured']}/"
        f"{manifest['totals']['states_attempted']} "
        f"overlay_clean={manifest['totals']['overlay_clean']} "
        f"sha={manifest['target']['resolved_sha_or_none']}",
        flush=True,
    )
    return 0 if payloads["outcome"] == "captured" else 1


if __name__ == "__main__":
    sys.exit(main())
