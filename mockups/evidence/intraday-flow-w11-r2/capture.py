#!/usr/bin/env python3
"""S1-rig overlay-column crops for intraday_flow W11 r2.

Six cells: stamp+tip open dark/light EN, counted control dark/light EN,
one ZH tip-row cell, the forced-outage stance cell.

Decorative overlays (.ift-aurora, #mmb-boot, .sky-fx) are removed before
clip; window.__skyDeck is set so setTheme does not mint a sun/moon glyph.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CELLS = OUT / "cells"
TEMPLATE = ROOT / "templates" / "intraday_flow.html.j2"

OVERLAY_SELECTORS = (".ift-aurora", ".mx5-aurora", ".sky-fx", "#mmb-root", "#mmb-boot")

_HIDE = """
() => {
  window.__skyDeck = true;
  const sels = %s;
  sels.forEach((s) => document.querySelectorAll(s).forEach((n) => n.remove()));
  return true;
}
""" % (json.dumps(list(OVERLAY_SELECTORS)),)


def _page_css() -> str:
    src = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r"<style>(.*?)</style>", src, re.S)
    if not m:
        raise SystemExit("no page <style> in template")
    return m.group(1)


def _fixture_html() -> str:
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
          return {theme: docEl.getAttribute('data-theme'), locale: docEl.getAttribute('data-lang')};
        }""",
        {"theme": theme, "locale": locale},
    )
    observed = page.evaluate(
        "() => ({theme: document.documentElement.getAttribute('data-theme'), locale: document.documentElement.getAttribute('data-lang')})"
    )
    if observed["theme"] != theme or (observed["locale"] or "en") != locale:
        raise SystemExit(f"state mismatch: wanted {theme}/{locale} got {observed}")
    page.evaluate(_HIDE)
    return observed


def _open_lens(page):
    page.locator("#stamp-q").scroll_into_view_if_needed()
    page.hover("#stamp-q")
    page.wait_for_selector(".lens-pop.open", timeout=4000)


def _close_lens(page):
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


def _isolate(page, keep: str):
    page.evaluate(
        """(keep) => {
          document.querySelectorAll('.overlay-col > *').forEach((n) => {
            n.style.visibility = (n.id === keep) ? 'visible' : 'hidden';
          });
        }""",
        keep,
    )


def _clip_union(page, *selectors: str) -> dict:
    boxes = []
    for sel in selectors:
        loc = page.locator(sel).first
        box = loc.bounding_box()
        if not box:
            raise SystemExit(f"no box for {sel}")
        boxes.append(box)
    x = min(b["x"] for b in boxes)
    y = min(b["y"] for b in boxes)
    r = max(b["x"] + b["width"] for b in boxes)
    btm = max(b["y"] + b["height"] for b in boxes)
    pad = 10
    return {
        "x": max(0, x - pad),
        "y": max(0, y - pad),
        "width": (r - x) + 2 * pad,
        "height": (btm - y) + 2 * pad,
    }


def main() -> int:
    CELLS.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="iflow-w11-r2-"))
    try:
        (staging / "index.html").write_text(_fixture_html(), encoding="utf-8")
        shutil.copy(ROOT / "templates" / "theme.css", staging / "theme.css")
        shutil.copy(ROOT / "templates" / "theme.js", staging / "theme.js")
        shots = {}
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                device_scale_factor=2,
                reduced_motion="reduce",
            )
            page = context.new_page()
            page.goto((staging / "index.html").as_uri(), wait_until="load")
            page.wait_for_function("() => !!document.getElementById('lens-style')")

            def shot(name: str, theme: str, locale: str, sels: tuple[str, ...],
                     open_tip: bool = False, isolate: str | None = None):
                _close_lens(page)
                _apply(page, theme, locale)
                if isolate:
                    _isolate(page, isolate)
                if open_tip:
                    page.evaluate(
                        """() => document.querySelectorAll('.lens-pop').forEach((n) => {
                          n.style.visibility = '';
                        })"""
                    )
                    _open_lens(page)
                clip = _clip_union(page, *sels)
                dest = CELLS / f"{name}.png"
                page.screenshot(path=str(dest), clip=clip, type="png")
                shots[name] = {
                    "file": f"cells/{name}.png",
                    "theme": theme,
                    "locale": locale,
                    "clip": sels,
                    "bytes": dest.stat().st_size,
                }
                _close_lens(page)
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
        receipt = {
            "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "rig": "S1 overlay-column (Playwright, overlay hide, reduced-motion)",
            "overlays_hidden": list(OVERLAY_SELECTORS),
            "cells": shots,
        }
        (OUT / "cells.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: v["bytes"] for k, v in shots.items()}, indent=2))
        return 0
    finally:
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
