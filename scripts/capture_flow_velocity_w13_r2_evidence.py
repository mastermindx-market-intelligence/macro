#!/usr/bin/env python3
"""Four forward crops for flow_velocity W13 r2 (S1 rig, overlay column).

Captures at the committed HEAD. Fixture-rendered (sparse trees have no site/).
Usage::

    python3 -m scripts.capture_flow_velocity_w13_r2_evidence
"""
from __future__ import annotations

import hashlib
import json
import shutil
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from jinja2 import Environment, FileSystemLoader

from engine import i18n
from engine.flow_observatory.contract import (
    QUADRANT_LABELS,
    STATUS_WORD,
    sigma_meaning,
)
from scripts.build_vector import C
from scripts.capture_page_evidence import CaptureUnavailable, _git_head_sha, serve_site_dir
from tests.test_flow_observatory_contract import _theme, _v2

OUT_DIR = _ROOT / "research" / "flow_observatory" / "w13_r2_evidence"
CELLS_DIR = OUT_DIR / "cells"

_STATE_SEED = """
(state) => {
  try {
    localStorage.setItem('theme', state.theme);
    localStorage.removeItem('themeAuto');
    localStorage.setItem('lang', state.locale);
  } catch (e) {}
  window.__skyDeck = true;
}
"""

_APPLY_STATE = """
(state) => {
  const docEl = document.documentElement;
  if (typeof window.setTheme === 'function') { window.setTheme(state.theme); }
  else { docEl.setAttribute('data-theme', state.theme); }
  if (typeof window.setLang === 'function') { window.setLang(state.locale); }
  else {
    docEl.setAttribute('data-lang', state.locale);
    if (state.locale) docEl.lang = state.locale;
  }
  var fx = document.querySelector('.sky-fx');
  if (fx && fx.parentNode) fx.parentNode.removeChild(fx);
  return {theme: docEl.getAttribute('data-theme'), locale: docEl.getAttribute('data-lang')};
}
"""

_OVERLAY_JS = """
(sel) => {
  const el = document.querySelector(sel);
  if (!el) return {ok: false, reason: 'missing-subject'};
  const r = el.getBoundingClientRect();
  const hits = [];
  for (const cls of ['.sky-fx', '.aurora', '#mmb-root']) {
    document.querySelectorAll(cls).forEach((n) => {
      const b = n.getBoundingClientRect();
      const overlap = !(b.right < r.left || b.left > r.right || b.bottom < r.top || b.top > r.bottom);
      const st = getComputedStyle(n);
      if (overlap && st.display !== 'none' && st.visibility !== 'hidden' && Number(st.opacity) > 0.05) {
        hits.push(cls);
      }
    });
  }
  return {ok: hits.length === 0, hits};
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


def _fixture_html() -> str:
    nine = [_theme(i, vel=1.0 + i * 0.15, rate_4wk=-0.9) for i in range(9)]
    v2 = _v2(ashare_sectors={
        "cadence": "daily", "as_of": "2026-09-01", "n": 9, "n_unscored": 0,
        "primary": "4wk", "note": "n", "note_zh": "n", "rows": nine,
    })
    env = Environment(loader=FileSystemLoader(str(_ROOT / "templates")), autoescape=True)
    env.globals.update(td=i18n.td, tr=i18n.tr, quadrant_labels=QUADRANT_LABELS,
                       status_word=STATUS_WORD, sigma_meaning=sigma_meaning)
    return env.get_template("flow_velocity.html.j2").render(C=C, snap=v2, built="w13-r2")


def _prepare_scratch(scratch: Path) -> None:
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "flow_velocity.html").write_text(_fixture_html(), encoding="utf-8")
    for name in ("theme.js", "theme.css", "product-nav-icons.css",
                 "navigation-refresh.css"):
        src = _ROOT / "templates" / name
        if src.exists():
            shutil.copy2(src, scratch / name)


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(f"playwright missing: {exc}") from exc

    sha_read = _git_head_sha(_ROOT)
    sha = sha_read.sha if hasattr(sha_read, "sha") else str(sha_read)
    scratch = Path("/tmp/fv-w13-r2-capture")
    if scratch.exists():
        shutil.rmtree(scratch)
    _prepare_scratch(scratch)
    httpd, port = serve_site_dir(scratch)
    base = f"http://127.0.0.1:{port}/flow_velocity.html"
    CELLS_DIR.mkdir(parents=True, exist_ok=True)

    crops = [
        {"id": "board-head-dark-en", "theme": "dark", "locale": "en",
         "sel": "#groups .fv-board-block", "tip": False, "w": 1440, "h": 900},
        {"id": "board-head-light-en", "theme": "light", "locale": "en",
         "sel": "#groups .fv-board-block", "tip": False, "w": 1440, "h": 900},
        {"id": "footer-tip-light-en", "theme": "light", "locale": "en",
         "sel": ".foot", "tip": True, "w": 1440, "h": 900},
        {"id": "caption-zh", "theme": "dark", "locale": "zh",
         "sel": "#groups .fv-caption", "tip": False, "w": 1440, "h": 900},
    ]
    rows = []
    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        for crop in crops:
            state = {"theme": crop["theme"], "locale": crop["locale"]}
            ctx = browser.new_context(
                viewport={"width": crop["w"], "height": crop["h"]},
                locale="zh-CN" if crop["locale"] == "zh" else "en-US",
                color_scheme=crop["theme"], device_scale_factor=1,
            )
            ctx.add_init_script(f"({_STATE_SEED.strip()})({json.dumps(state)})")
            page = ctx.new_page()
            resp = page.goto(base, wait_until="load", timeout=30000)
            if resp is None or not resp.ok:
                raise RuntimeError(f"HTTP {getattr(resp, 'status', None)}")
            page.wait_for_timeout(250)
            applied = page.evaluate(_APPLY_STATE.strip(), state) or {}
            if applied.get("theme") != crop["theme"] or applied.get("locale") != crop["locale"]:
                raise RuntimeError(f"state mismatch {crop['id']}: {applied}")
            page.wait_for_timeout(200)
            loc = page.locator(crop["sel"]).first
            loc.wait_for(state="visible", timeout=8000)
            loc.scroll_into_view_if_needed()
            if crop["tip"]:
                q = page.locator(".foot .qm, .foot .lens-q").first
                q.click(force=True)
                page.wait_for_timeout(250)
            overlay = page.evaluate(_OVERLAY_JS.strip(), crop["sel"])
            if crop["tip"]:
                png = page.screenshot(type="png")
            else:
                png = loc.screenshot(type="png")
            name, digest, pw_, ph = _png_meta(png)
            (CELLS_DIR / name).write_bytes(png)
            alias = f"{crop['id']}.png"
            (CELLS_DIR / alias).write_bytes(png)
            if not overlay.get("ok"):
                raise RuntimeError(f"overlay over {crop['id']}: {overlay}")
            rows.append({
                "id": crop["id"], "file": name, "alias": alias, "sha256": digest,
                "bytes": len(png), "width": pw_, "height": ph,
                "theme": crop["theme"], "locale": crop["locale"],
                "applied_theme": applied.get("theme"),
                "applied_locale": applied.get("locale"),
                "overlay": "clean", "overlay_hits": overlay.get("hits") or [],
            })
            ctx.close()
        browser.close()
        pw.stop()
    finally:
        httpd.shutdown()

    manifest = {
        "page": "flow_velocity.html",
        "round": "W13-r2",
        "target": {"resolved_sha_or_none": sha},
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "selection": {"n": len(rows), "ids": [r["id"] for r in rows]},
        "totals": {"captured": len(rows), "failed": 0},
        "cells": rows,
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    readme = [
        "# flow_velocity W13 r2 — four forward crops",
        "",
        f"Provenance: committed head `{sha}`.",
        "S1 rig: fixture VM (no live bake), Playwright localStorage seed + setTheme/setLang,",
        "`window.__skyDeck = true`, attribute re-read refuse-on-mismatch, overlay column.",
        "",
        "| id | theme | lang | overlay | alias |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        readme.append(
            f"| {r['id']} | {r['theme']} | {r['locale']} | {r['overlay']} | `{r['alias']}` |"
        )
    readme.append("")
    (OUT_DIR / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    print(json.dumps({"sha": sha, "n": len(rows), "out": str(OUT_DIR)}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CaptureUnavailable as exc:
        print(f"capture unavailable: {exc}", file=sys.stderr)
        raise SystemExit(4) from exc
