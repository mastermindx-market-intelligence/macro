"""
MO-PAID-011 DOM receipt for the UNTOUCHED natural premarket run on the served
URL https://www.mastermind-x.com/am_edition.html. Loads the served URL once per
(theme, locale) pair at 1440x900 desktop, applies setTheme/setLang through the
page's own toggle, waits for the .sky-fx flourish to clear (1.1s theme.js
sun/moon animation) before recording, and writes probe.json.

Captured per cell: fetched_at (UTC), HTTP status, response cache-control and
last-modified headers, the "Built at …" / "构建时间 …" header line text,
html lang/data-theme/data-lang, .sky-fx element count after settle, and per
.panel block: h2 text, state-chip text (dtp-pill|pill|chip|state class match),
<tr>/<li> row counts, and any nested "Built at …" text.

Identifies panels by h2 (the template does not emit a data-key); records raw
text so the seat maps blocks downstream.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


URL = "https://www.mastermind-x.com/am_edition.html"
OUT = Path(__file__).resolve().parent / "probe.json"
STATE_CHIP_CLASS_RE = ("dtp-pill", "pill", "chip", "state")
THEME_LOCALE_GRID = (("dark", "en"), ("dark", "zh"), ("light", "en"), ("light", "zh"))


def _panel_data(page) -> list[dict]:
    panels: list[dict] = []
    for el in page.query_selector_all(".panel"):
        h2_el = el.query_selector("h2")
        h2_text = (h2_el.inner_text() if h2_el else "").strip()
        chip_texts: list[str] = []
        for sub in el.query_selector_all("span, div"):
            cls = (sub.get_attribute("class") or "").split()
            if not cls:
                continue
            joined = " ".join(cls)
            if any(tok in joined for tok in STATE_CHIP_CLASS_RE):
                txt = (sub.inner_text() or "").strip()
                if txt:
                    chip_texts.append(txt)
        # de-dup while preserving order
        seen: set[str] = set()
        unique_chips: list[str] = []
        for t in chip_texts:
            if t not in seen:
                seen.add(t)
                unique_chips.append(t)
        rows = len(el.query_selector_all("tr")) + len(el.query_selector_all("li"))
        nested_built = []
        for inner in el.query_selector_all("p"):
            t = (inner.inner_text() or "").strip()
            if "Built at" in t or "构建时间" in t:
                nested_built.append(t)
        panels.append({
            "h2": h2_text,
            "state_chip_texts": unique_chips,
            "row_count": rows,
            "inner_built_at_texts": nested_built,
        })
    return panels


def _header_built_text(page) -> str:
    # the page template (line 107) wraps "Built at {{payload.generated_at}}" /
    # "构建时间 {{payload.generated_at}}" in a <p class="muted sm">.
    for p in page.query_selector_all("p"):
        text = (p.inner_text() or "").strip()
        if ("Built at" in text) or ("构建时间" in text):
            return text
    return ""


def main() -> int:
    out: dict = {
        "schema": "mastermind.am-edition-probe.v1",
        "url": URL,
        "probes": [],
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for theme, locale in THEME_LOCALE_GRID:
                ctx = browser.new_context(viewport={"width": 1440, "height": 900})
                # Seed theme+locale like the page's own toggle would.
                ctx.add_init_script(
                    f"try {{ localStorage.setItem('theme', '{theme}'); "
                    f"localStorage.removeItem('themeAuto'); "
                    f"localStorage.setItem('lang', '{locale}'); }} catch (e) {{}}"
                )
                page = ctx.new_page()
                resp = page.goto(URL, wait_until="networkidle", timeout=45_000)
                # Re-apply post-load so the page's own setTheme/setLang fire
                # (these trigger theme.js's skyToggleFx 1.1s flourish).
                page.evaluate(
                    "({t,l}) => { try { window.setTheme && window.setTheme(t); "
                    "window.setLang && window.setLang(l); } catch (e) {} }",
                    {"t": theme, "l": locale},
                )
                # Wait for the .sky-fx flourish to clear.
                try:
                    page.wait_for_function(
                        "() => !document.querySelector('.sky-fx')",
                        timeout=5_000,
                    )
                except Exception:
                    pass
                page.wait_for_timeout(800)  # extra settle beyond the wait_for

                status = resp.status if resp else None
                headers = (resp.headers if resp else {}) or {}
                built_text = _header_built_text(page)
                html_lang = page.evaluate("document.documentElement.lang || ''")
                data_theme = page.evaluate("document.documentElement.getAttribute('data-theme') || ''")
                data_lang = page.evaluate("document.documentElement.getAttribute('data-lang') || ''")
                sky_count = page.evaluate("document.querySelectorAll('.sky-fx').length")
                panels = _panel_data(page)

                out["probes"].append({
                    "theme": theme,
                    "locale": locale,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "response_status": status,
                    "cache_control": headers.get("cache-control", ""),
                    "last_modified": headers.get("last-modified", ""),
                    "built_at_text": built_text,
                    "html_lang": html_lang,
                    "data_theme": data_theme,
                    "data_lang": data_lang,
                    "sky_fx_count": sky_count,
                    "panels": panels,
                })
                ctx.close()
        finally:
            browser.close()

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) probes={len(out['probes'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())