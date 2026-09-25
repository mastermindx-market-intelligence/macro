"""Browser proof for the generated cybersecurity detail page.

Run with the site directory served locally, for example:
    python -m http.server 18873 --directory site
    python research/evidence/cybersecurity-basket-integrity-20260923/browser_verify.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


BASE_URL = os.environ.get("MMX_BROWSER_BASE", "http://127.0.0.1:18873")
URL = f"{BASE_URL.rstrip('/')}/basket/cybersecurity.html"
OUT = Path(__file__).resolve().parent / "browser"
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED = {
    "CRWD", "PANW", "FTNT", "OKTA", "QLYS", "ZS", "S", "NET", "RBRK", "TENB",
    "CHKP", "SAIL", "VRNS", "NTSK",
}
FORBIDDEN = {"MSFT", "CSCO", "IBM", "GOOGL", "AMZN", "AVGO"}

CASES = [
    ("desktop", 1440, 1000, "dark", "en"),
    ("desktop", 1440, 1000, "light", "en"),
    ("desktop", 1440, 1000, "dark", "zh"),
    ("desktop", 1440, 1000, "light", "zh"),
    ("mobile", 390, 844, "dark", "en"),
    ("mobile", 390, 844, "light", "en"),
    ("mobile", 390, 844, "dark", "zh"),
    ("mobile", 390, 844, "light", "zh"),
]


def main() -> int:
    results: list[dict] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for device, width, height, theme, lang in CASES:
            console_errors: list[str] = []
            request_failures: list[str] = []
            context = browser.new_context(viewport={"width": width, "height": height})
            page = context.new_page()
            page.on("console", lambda msg, xs=console_errors: xs.append(msg.text) if msg.type == "error" else None)
            page.on("requestfailed", lambda req, xs=request_failures: xs.append(req.url))
            page.add_init_script(
                f"localStorage.setItem('theme', {json.dumps(theme)});"
                f"localStorage.setItem('lang', {json.dumps(lang)});"
            )
            response = page.goto(URL, wait_until="networkidle", timeout=60_000)
            if response is None or not response.ok:
                raise AssertionError(f"navigation failed for {device}/{theme}/{lang}: {response}")
            page.wait_for_selector("#hold tbody tr", timeout=30_000)

            state = page.evaluate(
                """() => {
                    const rows = [...document.querySelectorAll('#hold tbody tr')];
                    const tickerOf = row => {
                        const el = row.querySelector('[data-ticker], .tk');
                        if (!el) return '';
                        return (el.dataset.ticker || el.textContent || '').trim().split(/\\s+/)[0];
                    };
                    const tickers = rows.map(tickerOf).filter(Boolean);
                    const uncovered_tickers = rows
                      .filter(row => row.textContent.includes('not covered yet') || row.textContent.includes('暂未覆盖'))
                      .map(tickerOf).filter(Boolean);
                    const root = document.documentElement;
                    const body = document.body;
                    return {
                        title: document.title,
                        lang: root.getAttribute('data-lang') || '',
                        theme: root.getAttribute('data-theme') || '',
                        row_count: rows.length,
                        tickers,
                        uncovered_tickers,
                        root_client_width: root.clientWidth,
                        root_scroll_width: root.scrollWidth,
                        body_client_width: body.clientWidth,
                        body_scroll_width: body.scrollWidth,
                        heading: document.querySelector('h1')?.textContent?.trim() || '',
                        holdings_heading: [...document.querySelectorAll('h2')]
                          .map(x => x.textContent.trim()).find(x => x.includes('Holdings') || x.includes('成分股')) || '',
                    };
                }"""
            )

            got = set(state["tickers"])
            missing = sorted(EXPECTED - got)
            forbidden = sorted(FORBIDDEN & got)
            uncovered = set(state["uncovered_tickers"])
            overflow = max(state["root_scroll_width"], state["body_scroll_width"]) > width + 1
            if state["row_count"] != 14:
                raise AssertionError(f"{device}/{theme}/{lang}: expected 14 holdings, got {state['row_count']}")
            if missing:
                raise AssertionError(f"{device}/{theme}/{lang}: missing core holdings {missing}; got {sorted(got)}")
            if forbidden:
                raise AssertionError(f"{device}/{theme}/{lang}: diversified names leaked into core {forbidden}")
            if uncovered != {"SAIL", "NTSK"}:
                raise AssertionError(
                    f"{device}/{theme}/{lang}: expected only SAIL/NTSK uncovered, got {sorted(uncovered)}"
                )
            if overflow:
                raise AssertionError(f"{device}/{theme}/{lang}: horizontal overflow {state}")

            stem = f"{device}-{theme}-{lang}"
            full_path = OUT / f"{stem}.jpg"
            page.screenshot(path=str(full_path), full_page=True, type="jpeg", quality=78)
            hold_path = None
            if theme == "dark" and lang == "en":
                hold_path = OUT / f"{stem}-holdings.jpg"
                page.locator("#hold").screenshot(path=str(hold_path), type="jpeg", quality=82)

            results.append(
                {
                    "case": stem,
                    "url": URL,
                    "http_status": response.status,
                    "state": state,
                    "missing_expected": missing,
                    "forbidden_present": forbidden,
                    "uncovered_tickers": sorted(uncovered),
                    "horizontal_overflow": overflow,
                    "console_errors": console_errors,
                    "request_failures": request_failures,
                    "screenshot": str(full_path.relative_to(OUT.parent)),
                    "holdings_screenshot": str(hold_path.relative_to(OUT.parent)) if hold_path else None,
                }
            )
            context.close()
        browser.close()

    receipt = {
        "schema": "cybersecurity_basket_browser_proof.v1",
        "url": URL,
        "expected_core": sorted(EXPECTED),
        "forbidden_adjacent_platforms": sorted(FORBIDDEN),
        "cases": results,
    }
    (OUT.parent / "browser_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
