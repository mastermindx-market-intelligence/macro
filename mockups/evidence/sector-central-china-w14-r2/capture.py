#!/usr/bin/env python3
"""S1-rig forward crops for sector_central_china W14 r2.

Fixture-rendered page (sparse trees have no site/), real body.page-sector-central
classes, Playwright, __skyDeck seed, overlay hide + overlay probe column,
reduced-motion. Refuses a dirty tree and stamps `git rev-parse HEAD` at capture
time so a working-tree edit cannot wear a prior committed sha.

Six forward crops (the closing-round matrix):
  silinks-dark-en-1440 / silinks-light-en-1440
  details-open-dark-en-1440
  mxerror-light-en-1440
  silinks-dark-zh-1440          (the ZH cell)
  details-open-light-en-1440

Recapture: python3 mockups/evidence/sector-central-china-w14-r2/capture.py
"""
from __future__ import annotations

import hashlib
import http.server
import json
import shutil
import socketserver
import struct
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "templates" / "sector_central_china.html.j2"

OVERLAY_SELECTORS = (".rvx-aurora", ".mx5-aurora", ".sky-fx", "#mmb-root", "#mmb-boot", ".aurora")
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
)

VIEWPORTS = {"desktop": (1440, 900)}

CELLS = (
    {"id": "silinks-dark-en-1440", "subject": "si-links", "theme": "dark", "locale": "en",
     "sel": ".si-links", "view": "explore", "open_details": False, "force_error": False},
    {"id": "silinks-light-en-1440", "subject": "si-links", "theme": "light", "locale": "en",
     "sel": ".si-links", "view": "explore", "open_details": False, "force_error": False},
    {"id": "details-open-dark-en-1440", "subject": "si-more-open", "theme": "dark", "locale": "en",
     "sel": "#si-theme-desk-more", "view": "explore", "open_details": True, "force_error": False},
    {"id": "mxerror-light-en-1440", "subject": "mx-error", "theme": "light", "locale": "en",
     "sel": "#csi-baskets-error", "view": "explore", "open_details": False, "force_error": True},
    {"id": "silinks-dark-zh-1440", "subject": "si-links", "theme": "dark", "locale": "zh",
     "sel": ".si-links", "view": "explore", "open_details": False, "force_error": False},
    {"id": "details-open-light-en-1440", "subject": "si-more-open", "theme": "light", "locale": "en",
     "sel": "#si-theme-desk-more", "view": "explore", "open_details": True, "force_error": False},
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
    # Tracked dirt only — the capture script and the PNGs it writes are
    # untracked until the evidence commit, and must not block provenance.
    porcelain = _git(["status", "--porcelain", "--untracked-files=no"])
    if porcelain:
        raise SystemExit("refuse: dirty tracked tree\n" + porcelain)
    return _git(["rev-parse", "HEAD"]), porcelain


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
    )


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


def _prep_view(page, spec: dict) -> None:
    page.evaluate(
        """(view) => {
          document.querySelectorAll('.si-view').forEach((v) => v.classList.remove('on'));
          const el = document.querySelector('.si-view[data-view=\"' + view + '\"]');
          if (el) el.classList.add('on');
          document.querySelectorAll('.si-view-btn').forEach((b) => {
            b.classList.toggle('on', b.getAttribute('data-view') === view);
          });
        }""",
        spec["view"],
    )
    if spec["open_details"]:
        page.evaluate(
            """() => {
              const d = document.getElementById('si-theme-desk-more');
              if (d) d.open = true;
            }"""
        )
    if spec["force_error"]:
        page.evaluate(
            """() => {
              const old = document.getElementById('csi-baskets-error');
              if (old) old.remove();
              const el = document.getElementById('table-section');
              const host = el || document.querySelector('.si-view.on');
              if (!host) return;
              const box = document.createElement('div');
              box.id = 'csi-baskets-error';
              box.className = 'mx-error';
              box.setAttribute('role', 'alert');
              box.innerHTML = '<b>!</b><span>'
                + '<span class="l-en">Basket data did not load. The rest of this page still works.</span>'
                + '<span class="l-zh">篮子数据未能加载。本页其余部分仍可用。</span>'
                + '<button type="button" class="csi-retry"><span class="l-en">Retry</span>'
                + '<span class="l-zh">重试</span></button></span>';
              host.parentNode.insertBefore(box, host);
            }"""
        )


def main() -> int:
    head, porcelain = _refuse_dirty()
    html = _render_html()
    if "not investment advice" not in html:
        raise SystemExit("fixture missing disclaimer — refusing capture")
    if "si-links-note" in html:
        raise SystemExit("fixture still has si-links-note — band not simplified")
    if "page-sector-central" not in html:
        raise SystemExit("fixture missing body.page-sector-central")

    staging = Path(tempfile.mkdtemp(prefix="scchina-w14r2-"))
    try:
        (staging / "sector_central_china.html").write_text(html, encoding="utf-8")
        for name in ASSETS:
            src = ROOT / "templates" / name
            if src.exists():
                shutil.copy2(src, staging / name)

        httpd, port = _serve(staging)
        origin = f"http://127.0.0.1:{port}"
        shots = []
        png_dir = OUT
        for old in png_dir.glob("*.png"):
            old.unlink()

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                device_scale_factor=1,
                reduced_motion="reduce",
            )
            for spec in CELLS:
                page = context.new_page()
                page.add_init_script(
                    "window.__skyDeck = true;\n"
                    "try {\n"
                    f"  localStorage.setItem('theme', {json.dumps(spec['theme'])});\n"
                    "  localStorage.removeItem('themeAuto');\n"
                    f"  localStorage.setItem('lang', {json.dumps(spec['locale'])});\n"
                    "} catch (e) {}\n"
                )
                page.route("**/chinabasketdata/**", lambda route: route.abort())
                page.route("**/marketdata/**", lambda route: route.abort())
                page.goto(
                    f"{origin}/sector_central_china.html",
                    wait_until="domcontentloaded",
                    timeout=30_000,
                )
                observed = _apply(page, spec["theme"], spec["locale"])
                _prep_view(page, spec)
                page.wait_for_timeout(250)
                page.evaluate(_HIDE)
                overlay_hits = page.evaluate(_OVERLAY_PROBE)
                loc = page.locator(spec["sel"]).first
                loc.wait_for(state="visible", timeout=8_000)
                loc.scroll_into_view_if_needed()
                page.wait_for_timeout(120)
                png = loc.screenshot(type="png")
                digest = hashlib.sha256(png).hexdigest()
                fname = f"{digest[:16]}.png"
                (png_dir / fname).write_bytes(png)
                w, h = _png_meta(png)
                cell = {
                    "id": spec["id"],
                    "subject": spec["subject"],
                    "file": fname,
                    "sha256": digest,
                    "bytes": len(png),
                    "width": w,
                    "height": h,
                    "theme": spec["theme"],
                    "locale": spec["locale"],
                    "viewport": "desktop",
                    "viewport_width": 1440,
                    "viewport_height": 900,
                    "applied_theme": observed["theme"],
                    "applied_locale": observed["locale"] or "en",
                    "body_class": observed["body"],
                    "overlay": "clean" if overlay_hits == [] else "dirty:" + ",".join(
                        h["sel"] for h in overlay_hits
                    ),
                    "overlay_clean": overlay_hits == [],
                    "overlay_hits": overlay_hits,
                    "selector": spec["sel"],
                    "captured": True,
                }
                shots.append(cell)
                print(
                    f"{spec['id']}: {fname} overlay={cell['overlay']} "
                    f"{w}x{h} theme={observed['theme']} lang={observed['locale']}",
                    flush=True,
                )
                page.close()
            context.close()
            browser.close()
        httpd.shutdown()
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    if len(shots) != 6:
        raise SystemExit(f"expected 6 crops, got {len(shots)}")
    dirty = [s["id"] for s in shots if not s["overlay_clean"]]
    if dirty:
        raise SystemExit("overlay dirty: " + ", ".join(dirty))

    generated = _now_iso()
    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "tool": "mockups/evidence/sector-central-china-w14-r2/capture.py",
        "generated_at": generated,
        "capture_sha": head,
        "resolved_gitdir": _git(["rev-parse", "--git-dir"]),
        "porcelain_at_capture": porcelain,
        "rig": (
            "S1 fixture-render + real body.page-sector-central "
            "(Playwright, overlay hide, __skyDeck, reduced-motion)"
        ),
        "overlays_hidden": list(OVERLAY_SELECTORS),
        "outcome": "captured",
        "honesty": {
            "access": "anonymous only; fixture render, no live site/ bake",
            "authority": "this tool measures and screenshots; it scores, ranks, and judges nothing",
            "gaps": "forward crops only — the full 8-cell rest matrix stays the closing round",
        },
        "axes": {
            "access": ["anonymous"],
            "themes": ["dark", "light"],
            "locales": ["en", "zh"],
            "viewports": {"desktop": [1440, 900]},
        },
        "pages": [
            {
                "page_id": "sector_central_china",
                "route": "/sector_central_china.html",
                "capture_route": "/sector_central_china.html",
                "states": [
                    {
                        "id": s["id"],
                        "access": "anonymous",
                        "theme": s["theme"],
                        "locale": s["locale"],
                        "viewport": s["viewport"],
                        "viewport_width": s["viewport_width"],
                        "captured": True,
                        "file": s["file"],
                        "sha256": s["sha256"],
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
        "manifest: mockups/evidence/sector-central-china-w14-r2/manifest.json\n",
        encoding="utf-8",
    )
    print(f"capture_sha={head} n={len(shots)} overlay_all_clean", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
