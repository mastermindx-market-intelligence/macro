"""Reproduce the home-hub UX checks locally or on the public VPS route."""
from __future__ import annotations

import argparse
import hashlib
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Existing origin; omitted = local committed site")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    server = None
    if args.base_url:
        base = args.base_url.rstrip("/")
    else:
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self, *_args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT / "site")))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_port}"
    rows = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            for viewport, width, height in [("desktop", 1440, 900), ("mobile", 390, 844)]:
                for lang in ("en", "zh"):
                    for theme in ("dark", "light"):
                        cell = f"{viewport}-{lang}-{theme}"
                        page = browser.new_page(viewport={"width": width, "height": height}, reduced_motion="reduce")
                        errors = []
                        page.on("pageerror", lambda error, errors=errors: errors.append(str(error)))
                        page.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.removeItem('themeAuto');localStorage.setItem('lang','{lang}');")
                        response = page.goto(base + "/start.html", wait_until="domcontentloaded", timeout=30000)
                        assert response and response.status == 200, cell
                        page.wait_for_selector(".hub-snapshot-meta", timeout=15000)
                        page.evaluate("s=>{window.setTheme&&window.setTheme(s.theme);window.setLang&&window.setLang(s.lang);}", {"theme": theme, "lang": lang})
                        page.wait_for_timeout(350)
                        assert page.locator("html").get_attribute("data-theme") == theme, cell
                        assert page.locator("html").get_attribute("data-lang") == lang, cell
                        snapshot = page.locator(".hub-snapshot-meta")
                        assert snapshot.is_visible(), cell
                        expected = "最新市场快照" if lang == "zh" else "latest market snapshot"
                        assert expected in snapshot.inner_text().lower(), (cell, snapshot.inner_text())
                        assert page.locator(".hub-clock").count() == 0, cell
                        dot = page.locator(".snapshot-dot").evaluate("e=>({animation:getComputedStyle(e).animationName,color:getComputedStyle(e).backgroundColor})")
                        assert dot["animation"] == "none" and dot["color"] != "rgba(0, 0, 0, 0)", (cell, dot)
                        if viewport == "mobile":
                            markets = page.locator('.hub-seg-btn[data-v="mk"]')
                            explore = page.locator('.hub-seg-btn[data-v="vc"]')
                            assert markets.is_visible() and explore.is_visible(), cell
                            assert markets.get_attribute("aria-pressed") == "true", cell
                            assert ("探索" if lang == "zh" else "explore") in explore.inner_text().lower(), cell
                            explore.focus()
                            page.keyboard.press("Enter")
                            assert explore.get_attribute("aria-pressed") == "true", cell
                            assert page.locator(".vc-sec").is_visible() and not page.locator(".mk-sec").is_visible(), cell
                        else:
                            assert page.locator(".vc-sec").is_visible() and page.locator(".mk-sec").is_visible(), cell
                            assert not page.locator(".hub-seg").is_visible(), cell
                        expected_ctas = {
                            "bonds.html": "收益率曲线与信用" if lang == "zh" else "Yield curve & credit",
                            "sector_central_china.html": "查看行业轮动" if lang == "zh" else "See sector rotation",
                        }
                        for href, copy in expected_ctas.items():
                            cta = page.locator(f'.vc-sec a.card[href="{href}"] .go-tx .l-{lang}')
                            assert cta.count() == 1 and cta.text_content() == copy, (cell, href)
                        # Mobile intentionally uses compact cards; full CTA text remains in the DOM.
                        page.locator(".vc-sec").scroll_into_view_if_needed()
                        page.screenshot(path=str(args.output_dir / f"{cell}-explore.png"))
                        if viewport == "mobile":
                            markets.focus()
                            page.keyboard.press("Space")
                            assert markets.get_attribute("aria-pressed") == "true", cell
                            assert page.locator(".mk-sec").is_visible() and not page.locator(".vc-sec").is_visible(), cell
                        overflow = page.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")
                        assert overflow <= 1 and not errors, (cell, overflow, errors)
                        row = {"cell": cell, "status": response.status, "html_sha256": hashlib.sha256(response.body()).hexdigest(), "horizontal_overflow": overflow, "page_errors": errors, "passed": True}
                        rows.append(row)
                        print(json.dumps(row), flush=True)
                        page.close()
            browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
        (args.output_dir / "interaction-results.json").write_text(json.dumps({"url": base + "/start.html", "method": "Real browser navigation, theme/language selection, keyboard section switching and visible snapshot checks; no synthetic data or membership state.", "results": rows}, indent=2) + "\n")


if __name__ == "__main__":
    main()
