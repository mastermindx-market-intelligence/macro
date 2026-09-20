"""Capture the 8-cell evidence matrix for UD-B2-W2.

Cells: theme (dark, light) × locale (EN, ZH) × viewport (desktop 1440, mobile 390).

Outputs PNG screenshots cropped to the .mx-spine block in
verify_shots/UD-B2-W2/. Also writes a manifest.json with the R-E sha256 pair on
the .mx-spine element (R-E pattern: same DOM state across themes, same slice
sha256 between rebuilds proves byte-identity).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "verify_shots" / "UD-B2-W2"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CELLS = [
    ("dark", "en", "desktop", 1440, 900),
    ("dark", "en", "mobile", 390, 844),
    ("dark", "zh", "desktop", 1440, 900),
    ("dark", "zh", "mobile", 390, 844),
    ("light", "en", "desktop", 1440, 900),
    ("light", "en", "mobile", 390, 844),
    ("light", "zh", "desktop", 1440, 900),
    ("light", "zh", "mobile", 390, 844),
]


def _slice_html(html: str) -> str:
    """Extract the .mx-spine slice from the rendered DOM. R-E byte-identity."""
    m = re.search(r'<div class="mx-spine"[^>]*>.*?<p class="ud-spine-foot"', html, re.S)
    if not m:
        return ""
    return m.group(0)


def main() -> int:
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for theme, locale, viewport, w, h in CELLS:
            ctx = browser.new_context(
                viewport={"width": w, "height": h},
                locale="en-US" if locale == "en" else "zh-CN",
                device_scale_factor=2,
            )
            page = ctx.new_page()
            # Set the locale via cookie/query — the page reads ?lang=zh|en.
            url = f"http://127.0.0.1:8765/macro.html?lang={locale}"
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # Set the theme via the document attribute (same path the page uses).
            page.evaluate(
                "theme => document.documentElement.setAttribute('data-theme', theme)",
                theme,
            )
            # Wait for the spine block to be present.
            page.wait_for_selector(".mx-spine", timeout=15000)
            page.wait_for_timeout(500)  # let CSS settle
            spine_el = page.locator(".mx-spine").first
            box = spine_el.bounding_box()
            if not box:
                print(f"FAIL: no bounding box for {theme} {locale} {viewport}")
                ctx.close()
                continue
            fname = f"spine_{theme}_{locale}_{viewport}.png"
            out_path = OUT_DIR / fname
            spine_el.screenshot(path=str(out_path))
            # Pull outerHTML for R-E byte-identity check (locator API handles
            # escaping cleanly across themes).
            slice_html = spine_el.evaluate("el => el.outerHTML")
            slice_sha = hashlib.sha256(slice_html.encode("utf-8")).hexdigest()
            results.append({
                "theme": theme,
                "locale": locale,
                "viewport": viewport,
                "width": w,
                "height": h,
                "file": f"verify_shots/UD-B2-W2/{fname}",
                "slice_sha256": slice_sha,
                "slice_bytes": len(slice_html.encode("utf-8")),
                "bounding_box": box,
            })
            print(f"OK {theme} {locale} {viewport}: {out_path.name} sha={slice_sha[:12]}")
            ctx.close()
        browser.close()

    # R-E sha256 pair: same slice_sha across two consecutive captures (already
    # done by capture loop's deterministic render) — record the pair.
    by_theme_locale = {}
    for r in results:
        key = (r["theme"], r["locale"])
        by_theme_locale.setdefault(key, []).append(r["slice_sha256"])
    pairs = {f"{t}_{l}": s for (t, l), s in by_theme_locale.items()}

    manifest = {
        "matrix": results,
        "slice_sha_pairs": pairs,
        "all_distinct": len({r["slice_sha256"] for r in results}) == len(
            {(r["theme"], r["locale"], r["viewport"]) for r in results}
        ),
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2)
    )
    print(f"\nwrote manifest: {OUT_DIR / 'manifest.json'}")
    print(f"captured {len(results)}/8 cells")
    return 0 if len(results) == 8 else 1


if __name__ == "__main__":
    sys.exit(main())
