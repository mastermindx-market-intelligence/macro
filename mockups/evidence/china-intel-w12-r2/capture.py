#!/usr/bin/env python3
"""S1-rig overlay-column crops for china_intel W12 r2.

Six cells: B1 state-3 and state-4 chips dark EN, one dated brief card
dark/light EN, the regime colour probe per lane (EN + ZH).

Run AFTER the code commit, on a clean tree. Manifest sha is `git rev-parse HEAD`
at capture time. Decorative overlays are removed; window.__skyDeck is set.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CELLS = OUT / "cells"
TEMPLATE = ROOT / "templates" / "china_intel.html.j2"

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
    m = re.search(r"\{% block base_css %\}(.*?)\{% endblock %\}", src, re.S)
    if not m:
        raise SystemExit("no {% block base_css %} in china_intel template")
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
<body>
<div class="overlay-col" style="max-width:760px;margin:28px auto;display:flex;flex-direction:column;gap:32px;padding:8px 12px;">
  <div class="cmdbar" id="cell-b1-s3">
    <span class="mc warn"
          data-tip-en="Oldest dated feed on this desk. Other desks keep their own as-of stamps."
          data-tip-zh="本台最旧的有日期数据源。其余面板保留各自的截至日。">
      <span class="l-en">No feed is current — oldest 70d.</span>
      <span class="l-zh">所有数据源均非最新——最旧 70 天。</span>
    </span>
  </div>
  <div class="cmdbar" id="cell-b1-s4">
    <span class="mc warn stale-chip">
      <span class="l-en">Feed timestamps unavailable.</span>
      <span class="l-zh">数据源时间不可用。</span>
    </span>
  </div>
  <div class="pp-card" id="cell-brief">
    <div class="ci-card-head">
      <div class="ci-card-title">
        <span class="l-en">Policy language shifts</span>
        <span class="l-zh">政策表述变化</span>
      </div>
      <span class="ci-card-asof">2026-09-11</span>
      <span class="surf">
        <span class="l-en">Policy language</span>
        <span class="l-zh">政策表述</span>
      </span>
    </div>
    <p style="font-size:12px;color:var(--muted);margin:2px 0 0">
      <span class="l-en">Official-language new / dropped / lead-topic events, last 14d · 0 events</span>
      <span class="l-zh">官方文件 14 天内新增/消失/头版转向事件 · 0 条</span>
    </p>
  </div>
  <div class="cmdbar" id="cell-regime">
    <span class="regime mc hot">
      <span class="rk">
        <span class="l-en">Risk appetite</span>
        <span class="l-zh">风险偏好</span>
      </span>
      <b class="on">
        <span class="l-en">Risk-on</span>
        <span class="l-zh">偏好风险</span>
      </b>
    </span>
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


def _clip(page, sel: str) -> dict:
    box = page.locator(sel).first.bounding_box()
    if not box:
        raise SystemExit(f"no box for {sel}")
    pad = 10
    return {
        "x": max(0, box["x"] - pad),
        "y": max(0, box["y"] - pad),
        "width": box["width"] + 2 * pad,
        "height": box["height"] + 2 * pad,
    }


def _head_sha() -> str:
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    ).strip()
    if dirty:
        raise SystemExit(f"capture refused: dirty tree\n{dirty}")
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def main() -> int:
    sha = _head_sha()
    CELLS.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="chintel-w12-r2-"))
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

            def shot(name: str, theme: str, locale: str, sel: str):
                _apply(page, theme, locale)
                clip = _clip(page, sel)
                dest = CELLS / f"{name}.png"
                page.screenshot(path=str(dest), clip=clip, type="png")
                shots[name] = {
                    "file": f"cells/{name}.png",
                    "theme": theme,
                    "locale": locale,
                    "clip": [sel],
                    "bytes": dest.stat().st_size,
                }

            shot("b1-state3-dark-en", "dark", "en", "#cell-b1-s3")
            shot("b1-state4-dark-en", "dark", "en", "#cell-b1-s4")
            shot("brief-card-dark-en", "dark", "en", "#cell-brief")
            shot("brief-card-light-en", "light", "en", "#cell-brief")
            shot("regime-en", "dark", "en", "#cell-regime")
            _apply(page, "dark", "en")
            en_c = page.evaluate(
                "() => getComputedStyle(document.querySelector('.cmdbar .regime b.on')).color"
            )
            shot("regime-zh", "dark", "zh", "#cell-regime")
            _apply(page, "dark", "zh")
            zh_c = page.evaluate(
                "() => getComputedStyle(document.querySelector('.cmdbar .regime b.on')).color"
            )
            browser.close()

        if en_c != "rgb(31, 154, 85)" or zh_c != "rgb(210, 63, 63)":
            raise SystemExit(f"regime colour mismatch EN={en_c} ZH={zh_c}")
        shots["regime-en"]["computed_color"] = en_c
        shots["regime-zh"]["computed_color"] = zh_c

        receipt = {
            "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sha": sha,
            "rig": "S1 overlay-column (Playwright, overlay hide, reduced-motion)",
            "overlays_hidden": list(OVERLAY_SELECTORS),
            "cells": shots,
        }
        (OUT / "cells.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
        )
        (OUT / "manifest.json").write_text(
            json.dumps({
                "schema": "mastermind.p0_evidence.v2",
                "page": "china_intel",
                "round": "w12-r2",
                "sha": sha,
                "rig": receipt["rig"],
                "overlays_hidden": list(OVERLAY_SELECTORS),
                "selection": list(shots.keys()),
                "totals": {"states": len(shots)},
                "cells": {k: {"file": v["file"], "theme": v["theme"],
                              "locale": v["locale"]} for k, v in shots.items()},
            }, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"sha": sha, "bytes": {k: v["bytes"] for k, v in shots.items()},
                          "regime": {"en": en_c, "zh": zh_c}}, indent=2))
        return 0
    finally:
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
