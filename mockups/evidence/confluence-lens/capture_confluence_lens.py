#!/usr/bin/env python3
"""Capture G4 crops for the confluence LENS packet.

Theme/lang are applied the way theme.js does (window.setTheme / window.setLang)
and then re-read from <html data-theme data-lang> before the shot. Tips are
opened by focusing (desktop) or clicking (mobile 390, hover:none) the rank-01
.lc-wr-big host — the same events theme.js's LENS block listens for. If the
.pop never opens, the script fails closed rather than faking a card.
"""
from __future__ import annotations

import http.server
import json
import shutil
import socketserver
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from scripts.build_confluence_screener import build_context, render_html  # noqa: E402


def _serve(directory: Path) -> tuple[str, socketserver.TCPServer]:
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, fmt, *args):  # noqa: ARG002
            return

    httpd = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    host, port = httpd.server_address[:2]
    return f"http://{host}:{port}/confluence_screener.html", httpd


def _apply(page, theme: str, lang: str) -> dict:
    page.evaluate(
        """([theme, lang]) => {
          if (typeof window.setTheme === 'function') window.setTheme(theme);
          else document.documentElement.setAttribute('data-theme', theme);
          if (typeof window.setLang === 'function') window.setLang(lang);
          else {
            document.documentElement.setAttribute('data-lang', lang);
            document.documentElement.lang = lang === 'zh' ? 'zh-Hans' : 'en';
          }
        }""",
        [theme, lang],
    )
    page.wait_for_timeout(80)
    applied = page.evaluate(
        """() => ({
          theme: document.documentElement.getAttribute('data-theme'),
          lang: document.documentElement.getAttribute('data-lang')
        })"""
    )
    if applied["theme"] != theme or applied["lang"] != lang:
        raise RuntimeError(f"toggle mismatch want {theme}/{lang} got {applied}")
    return applied


def _open_tip(page, *, mobile: bool) -> None:
    host = page.locator(".lc.free .lc-wr-big").first
    host.wait_for(state="visible")
    host.scroll_into_view_if_needed()
    page.wait_for_timeout(80)
    if mobile:
        # Playwright's composed tap (pointerover + click) toggles LENS closed
        # on a hover:none context. Dispatch one bubbling click, which is the
        # event theme.js's touch branch listens for.
        page.evaluate(
            """() => {
              const t = document.querySelector('.lc.free .lc-wr-big');
              t.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
            }"""
        )
    else:
        host.focus()
    page.locator(".lens-pop.open").wait_for(state="visible", timeout=4000)


def _union_clip(page, selectors: list[str], pad: int = 16) -> dict:
    vp = page.viewport_size
    boxes = []
    for sel in selectors:
        loc = page.locator(sel).first
        if loc.count() == 0:
            continue
        box = loc.bounding_box()
        if box:
            boxes.append(box)
    if not boxes:
        return {"x": 0, "y": 0, "width": vp["width"], "height": min(vp["height"], 900)}
    x0 = max(0, min(b["x"] for b in boxes) - pad)
    y0 = max(0, min(b["y"] for b in boxes) - pad)
    x1 = min(vp["width"], max(b["x"] + b["width"] for b in boxes) + pad)
    y1 = min(vp["height"], max(b["y"] + b["height"] for b in boxes) + pad)
    return {"x": x0, "y": y0, "width": max(1, x1 - x0), "height": max(1, y1 - y0)}


def main() -> int:
    raw = json.loads(Path("/tmp/tech_confluence.json").read_text(encoding="utf-8"))
    ctx = build_context(raw, {})
    html = render_html(ROOT, ctx)
    rank1 = ctx["combos"][0]
    t4_rc = (
        f"{rank1['months_test']} months · {rank1['n_test']} fires · "
        f"{ctx['split_date']} → {ctx['asof']} · win = up after 21 trading days"
    )

    tmp = Path(tempfile.mkdtemp(prefix="confluence-lens-"))
    (tmp / "confluence_screener.html").write_text(html, encoding="utf-8")
    shutil.copy(ROOT / "templates" / "theme.css", tmp / "theme.css")
    shutil.copy(ROOT / "templates" / "theme.js", tmp / "theme.js")
    for extra in (
        "navigation-refresh.css",
        "product-nav-icons.css",
        "nav_market.js",
    ):
        src = ROOT / "templates" / extra
        if src.exists():
            shutil.copy(src, tmp / extra)

    url, httpd = _serve(tmp)
    receipts: list[dict] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            def shot(name: str, *, theme: str, lang: str, width: int, height: int,
                     mobile: bool, subject: str, selectors: list[str],
                     open_tip: bool) -> None:
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    device_scale_factor=1,
                    is_mobile=mobile,
                    has_touch=mobile,
                    locale="zh-CN" if lang == "zh" else "en-US",
                )
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_selector(".lc.free .lc-wr-big", timeout=10000)
                applied = _apply(page, theme, lang)
                if open_tip:
                    _open_tip(page, mobile=mobile)
                    page.wait_for_timeout(200)
                if subject == "honesty":
                    page.locator(".honesty").first.scroll_into_view_if_needed()
                    page.wait_for_timeout(80)
                elif subject == "chips":
                    page.locator(".lc.free .lc-foot").first.scroll_into_view_if_needed()
                    page.wait_for_timeout(80)
                dest = OUT / f"{name}.png"
                # Desktop G4 crops must be ≥1200px wide — take the full
                # 1440 viewport rather than a sub-1200 card clip. Mobile
                # stays device-width (390). Tight clips remain for the
                # paired at-rest numeral so dotted vs hairline is readable.
                if subject == "at-rest-numeral":
                    clip = _union_clip(page, selectors, pad=18)
                    page.screenshot(path=str(dest), clip=clip)
                else:
                    clip = {"x": 0, "y": 0, "width": width, "height": height}
                    page.screenshot(path=str(dest))
                pop_open = page.locator(".lens-pop.open").count() > 0
                sheet = page.evaluate(
                    "() => !!(document.querySelector('.lens-scrim.open') && "
                    "document.documentElement.classList.contains('lens-lock'))"
                )
                t4_attr = page.locator(".lc.free .lc-wr-big").first.get_attribute(
                    "data-tip-rc-en"
                )
                receipts.append({
                    "file": dest.name,
                    "want_theme": theme,
                    "want_lang": lang,
                    "applied_theme": applied["theme"],
                    "applied_lang": applied["lang"],
                    "viewport": f"{width}x{height}",
                    "subject": subject,
                    "open_tip": open_tip,
                    "pop_open": pop_open,
                    "sheet_scrim_lock": sheet,
                    "t4_rc_en": t4_attr,
                    "bytes": dest.stat().st_size,
                    "clip": {k: round(v, 1) for k, v in clip.items()},
                })
                context.close()

            # G4 1–4 dark, 5–7 light, tip OPEN on .lc-wr-big
            shot("01-dark-en-1440-tip-open", theme="dark", lang="en",
                 width=1440, height=900, mobile=False, subject="tip-open",
                 selectors=[".lc.free", ".lens-pop.open"], open_tip=True)
            shot("02-dark-zh-1440-tip-open", theme="dark", lang="zh",
                 width=1440, height=900, mobile=False, subject="tip-open",
                 selectors=[".lc.free", ".lens-pop.open"], open_tip=True)
            shot("03-dark-en-390-tip-open", theme="dark", lang="en",
                 width=390, height=844, mobile=True, subject="tip-open-sheet",
                 selectors=[], open_tip=True)
            shot("04-dark-zh-390-tip-open", theme="dark", lang="zh",
                 width=390, height=844, mobile=True, subject="tip-open-sheet",
                 selectors=[], open_tip=True)
            shot("05-light-en-1440-tip-open", theme="light", lang="en",
                 width=1440, height=900, mobile=False, subject="tip-open",
                 selectors=[".lc.free", ".lens-pop.open"], open_tip=True)
            shot("06-light-zh-1440-tip-open", theme="light", lang="zh",
                 width=1440, height=900, mobile=False, subject="tip-open",
                 selectors=[".lc.free", ".lens-pop.open"], open_tip=True)
            shot("07-light-en-390-tip-open", theme="light", lang="en",
                 width=390, height=844, mobile=True, subject="tip-open-sheet",
                 selectors=[], open_tip=True)

            # G4 8 — healed honesty bullet + chips; one crop per theme
            shot("08a-dark-en-1440-honesty", theme="dark", lang="en",
                 width=1440, height=900, mobile=False, subject="honesty",
                 selectors=[".honesty"], open_tip=False)
            shot("08b-dark-en-1440-chips", theme="dark", lang="en",
                 width=1440, height=900, mobile=False, subject="chips",
                 selectors=[".lc.free .lc-foot"], open_tip=False)
            shot("08c-light-en-1440-honesty", theme="light", lang="en",
                 width=1440, height=900, mobile=False, subject="honesty",
                 selectors=[".honesty"], open_tip=False)
            shot("08d-light-en-1440-chips", theme="light", lang="en",
                 width=1440, height=900, mobile=False, subject="chips",
                 selectors=[".lc.free .lc-foot"], open_tip=False)

            # Paired at-rest numeral so dotted (dark) vs solid hairline (light)
            # is visible without the open card covering the rule.
            shot("rest-dark-en-1440-numeral", theme="dark", lang="en",
                 width=1440, height=900, mobile=False, subject="at-rest-numeral",
                 selectors=[".lc.free .lc-wr"], open_tip=False)
            shot("rest-light-en-1440-numeral", theme="light", lang="en",
                 width=1440, height=900, mobile=False, subject="at-rest-numeral",
                 selectors=[".lc.free .lc-wr"], open_tip=False)

            browser.close()
    finally:
        httpd.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)

    payload = {
        "t4_receipt_from_context": t4_rc,
        "rank01": {
            "combo_id": rank1["combo_id"],
            "months_test": rank1["months_test"],
            "n_test": rank1["n_test"],
            "split_date": ctx["split_date"],
            "asof": ctx["asof"],
        },
        "crops": receipts,
    }
    (OUT / "toggle_receipts.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    failed = [r for r in receipts if r["open_tip"] and not r["pop_open"]]
    if failed:
        print("FAILED open_tip crops:", [r["file"] for r in failed], file=sys.stderr)
        return 1
    mismatch = [r for r in receipts if r["t4_rc_en"] != t4_rc]
    if mismatch:
        print("FAILED T4 receipt mismatch", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
