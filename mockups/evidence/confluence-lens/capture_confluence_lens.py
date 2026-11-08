#!/usr/bin/env python3
"""Capture G4 crops for the confluence LENS packet.

Theme/lang are applied the way theme.js does (window.setTheme / window.setLang)
and then re-read from <html data-theme data-lang> before the shot. Tips are
opened by focusing (desktop) or clicking (mobile 390, hover:none) the rank-01
.lc-wr-big host — the same events theme.js's LENS block listens for. If the
.pop never opens, the script fails closed rather than faking a card.
"""
from __future__ import annotations

import copy
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
    # Live top-3 are all consistent=true, so the healed false-branch ZH
    # copy never appears. Row-8 ZH crops render a disclosed clone: rank-2
    # keeps a positive edge (ratified two-part claim) and rank-3 is forced
    # to edge_test_pp <= 0 (honest recent-half copy). Honesty copy is
    # identical on both documents.
    ctx_row8 = copy.deepcopy(ctx)
    if len(ctx_row8["combos"]) >= 2:
        ctx_row8["combos"][1]["consistent"] = False
        if ctx_row8["combos"][1].get("edge_test_pp", 0) <= 0:
            ctx_row8["combos"][1]["edge_test_pp"] = 8.0
    if len(ctx_row8["combos"]) >= 3:
        ctx_row8["combos"][2]["consistent"] = False
        ctx_row8["combos"][2]["edge_test_pp"] = -2.4
    html_row8 = render_html(ROOT, ctx_row8)
    rank1 = ctx["combos"][0]
    t4_rc = (
        f"{rank1['months_test']} months · {rank1['n_test']} fires · "
        f"{ctx['split_date']} → {ctx['asof']} · win = up after 21 trading days"
    )

    tmp = Path(tempfile.mkdtemp(prefix="confluence-lens-"))
    (tmp / "confluence_screener.html").write_text(html, encoding="utf-8")
    (tmp / "confluence_screener_row8zh.html").write_text(html_row8, encoding="utf-8")
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
                     open_tip: bool, page_url: str | None = None) -> None:
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    device_scale_factor=1,
                    is_mobile=mobile,
                    has_touch=mobile,
                    locale="zh-CN" if lang == "zh" else "en-US",
                )
                page = context.new_page()
                page.goto(page_url or url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_selector(".lc.free .lc-wr-big", timeout=10000)
                applied = _apply(page, theme, lang)
                # Sitewide .sky-fx sun/moon sits at viewport center and occludes
                # the rank-2 consistency chip. Hide it on the row-8 ZH document
                # so the healed copy is actually legible in the crop.
                if (page_url or url).endswith("row8zh.html"):
                    page.evaluate(
                        "() => document.querySelectorAll('.sky-fx')"
                        ".forEach(e => { e.style.display = 'none'; })"
                    )
                if open_tip:
                    _open_tip(page, mobile=mobile)
                    page.wait_for_timeout(200)
                if subject == "honesty":
                    page.locator(".honesty").first.scroll_into_view_if_needed()
                    page.wait_for_timeout(80)
                elif subject == "chips":
                    page.locator(".lc.free .lc-foot").first.scroll_into_view_if_needed()
                    page.wait_for_timeout(80)
                elif subject == "chips-gated":
                    page.locator(".lc.gated .lc-foot").first.scroll_into_view_if_needed()
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
                zh_money = page.evaluate(
                    """() => {
                      const inView = (el) => {
                        const r = el.getBoundingClientRect();
                        return r.width > 0 && r.height > 0 && r.bottom > 0
                          && r.top < window.innerHeight
                          && r.left < window.innerWidth && r.right > 0;
                      };
                      const find = (pred) => [...document.querySelectorAll('.l-zh')]
                        .find(e => pred(e.innerText || '') && inView(e));
                      return {
                        hover_promise_in_view: !!find(t => t.includes('将鼠标移到任一胜率上')),
                        edge_high_in_view: !!find(t => /较随机入场高\\s*-?\\d+\\s*个百分点/.test(t)),
                        older_years_in_view: !!find(t => t.includes('更早年份未能印证')),
                        recent_half_in_view: !!find(t => t.includes('近段未能跑赢随机入场')),
                      };
                    }"""
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
                    "zh_money": zh_money,
                    "page": "row8zh" if (page_url or url).endswith("row8zh.html") else "live",
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

            # G4 8 ZH — live top-3 are consistent=true, so these four use
            # confluence_screener_row8zh.html (disclosed mutation).
            url_row8 = url.rsplit("/", 1)[0] + "/confluence_screener_row8zh.html"
            shot("08e-dark-zh-1440-honesty", theme="dark", lang="zh",
                 width=1440, height=900, mobile=False, subject="honesty",
                 selectors=[".honesty"], open_tip=False, page_url=url_row8)
            shot("08f-dark-zh-1440-chips", theme="dark", lang="zh",
                 width=1440, height=900, mobile=False, subject="chips-gated",
                 selectors=[".lc.gated .lc-foot"], open_tip=False, page_url=url_row8)
            shot("08g-light-zh-1440-honesty", theme="light", lang="zh",
                 width=1440, height=900, mobile=False, subject="honesty",
                 selectors=[".honesty"], open_tip=False, page_url=url_row8)
            shot("08h-light-zh-1440-chips", theme="light", lang="zh",
                 width=1440, height=900, mobile=False, subject="chips-gated",
                 selectors=[".lc.gated .lc-foot"], open_tip=False, page_url=url_row8)

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
        "row8_zh_mutation": {
            "reason": "live top-3 consistent=true; false-branch ZH copy would not appear",
            "rank2": {
                "combo_id": ctx_row8["combos"][1]["combo_id"] if len(ctx_row8["combos"]) > 1 else None,
                "consistent": ctx_row8["combos"][1]["consistent"] if len(ctx_row8["combos"]) > 1 else None,
                "edge_test_pp": ctx_row8["combos"][1]["edge_test_pp"] if len(ctx_row8["combos"]) > 1 else None,
            },
            "rank3": {
                "combo_id": ctx_row8["combos"][2]["combo_id"] if len(ctx_row8["combos"]) > 2 else None,
                "consistent": ctx_row8["combos"][2]["consistent"] if len(ctx_row8["combos"]) > 2 else None,
                "edge_test_pp": ctx_row8["combos"][2]["edge_test_pp"] if len(ctx_row8["combos"]) > 2 else None,
            },
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
    honesty_zh = [r for r in receipts if r["file"] in {
        "08e-dark-zh-1440-honesty.png", "08g-light-zh-1440-honesty.png",
    }]
    chips_zh = [r for r in receipts if r["file"] in {
        "08f-dark-zh-1440-chips.png", "08h-light-zh-1440-chips.png",
    }]
    if len(honesty_zh) != 2 or len(chips_zh) != 2:
        print("FAILED row-8 ZH crop count", file=sys.stderr)
        return 1
    missing_h = [r["file"] for r in honesty_zh if not r["zh_money"]["hover_promise_in_view"]]
    missing_c = [
        r["file"] for r in chips_zh
        if not (r["zh_money"]["edge_high_in_view"] and r["zh_money"]["older_years_in_view"])
    ]
    if missing_h or missing_c:
        print("FAILED ZH money copy not in view", missing_h, missing_c, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
