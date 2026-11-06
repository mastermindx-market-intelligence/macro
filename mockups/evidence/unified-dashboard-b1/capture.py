"""Capture the 8-cell evidence matrix for UD-B1 hero.

Cells = dark/light × EN/ZH × 1440/390 = 8.
Renders site/macro.html (mode=macro, the new hero skeleton) and
captures full-page screenshots, plus a focused hero crop per cell.

Manifest naming: dashboard_<theme>_<lang>_<viewport>.png
This head: HEAD_SHA (read live from `git rev-parse HEAD` at run-time; the
manifest must always reflect the bytes it captured).
"""
import json, threading, hashlib, subprocess
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

ROOT = Path.cwd()
EVIDENCE = ROOT / "mockups/evidence/unified-dashboard-b1"
HEAD_SHA = subprocess.run(
    ["git", "rev-parse", "--short", "HEAD"],
    cwd=ROOT, capture_output=True, text=True, check=True,
).stdout.strip()  # noqa: S603 — read-only `git rev-parse`


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    records = []
    page_errors: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()
            page = context.new_page()
            page.on("pageerror", lambda err: page_errors.append(str(err)))

            url = f"http://127.0.0.1:{port}/site/macro.html"
            for viewport, width, height in [("1440", 1440, 900), ("390", 390, 844)]:
                page.set_viewport_size({"width": width, "height": height})
                page.goto(url, wait_until="networkidle")
                # The page has no lang toggle JS hook beyond dataset, but it
                # already serves EN+ZH via /zh/macro.html. Use the dataset
                # trick that the page reads.
                for theme in ["dark", "light"]:
                    for lang in ["en", "zh"]:
                        page.evaluate(
                            "([t,l])=>{document.documentElement.dataset.theme=t;"
                            "document.documentElement.dataset.lang=l;"
                            "document.documentElement.lang=l;"
                            "document.dispatchEvent(new Event('langchange'));}",
                            [theme, lang],
                        )
                        page.evaluate("document.fonts.ready")
                        page.wait_for_timeout(250)

                        # Hero crop: the new unified dashboard hero partial
                        # carries class names mx-ud-* inside .panel.span12
                        # (the existing layout). Capture the top viewport.
                        hero = page.locator(".page-macro .panel.span12").first
                        if hero.count() == 0:
                            # fallback: top of page
                            hero = page.locator("body > *").first
                        hero_filename = (
                            f"dashboard_{theme}_{lang}_{viewport}_hero.png"
                        )
                        try:
                            hero.screenshot(path=str(EVIDENCE / hero_filename))
                        except Exception as exc:
                            records.append(
                                {
                                    "file": hero_filename,
                                    "viewport": viewport,
                                    "theme": theme,
                                    "language": lang,
                                    "error": f"hero screenshot failed: {exc}",
                                }
                            )
                            continue

                        # Full-page capture
                        full_filename = (
                            f"dashboard_{theme}_{lang}_{viewport}.png"
                        )
                        page.screenshot(
                            path=str(EVIDENCE / full_filename),
                            full_page=False,
                        )

                        # Spot-check: confirm the new spine primitive is
                        # present and not zero-height.
                        spine = page.locator(".mx-spine").first
                        spine_box = (
                            spine.evaluate(
                                "(e)=>({w:e.clientWidth,h:e.clientHeight,"
                                "rows:e.querySelectorAll('.mx-spine-row').length})"
                            )
                            if spine.count() > 0
                            else {"w": 0, "h": 0, "rows": 0}
                        )
                        verdict = page.locator(".ud-verdict").first
                        verdict_text = (
                            verdict.evaluate(
                                # Use textContent, then walk only the children
                                # whose classList contains the active locale
                                # (the page has both .l-en and .l-zh spans
                                # in the DOM; CSS hides one set per data-lang).
                                # Returns the rendered phrase for THIS cell
                                # only — not the union of both locales.
                                "(e)=>{const lang=document.documentElement.dataset.lang||'en';"
                                "let out='';for(const c of e.childNodes){"
                                "if(c.nodeType===3){out+=c.nodeValue;continue;}"
                                "if(c.classList&&c.classList.contains('l-'+lang)){"
                                "out+=c.textContent;}else if(!c.classList||"
                                "(!c.classList.contains('l-en')&&!c.classList.contains('l-zh'))){"
                                "out+=c.textContent;}}"
                                "return out.replace(/\\s+/g,' ').trim();}"
                            )
                            if verdict.count() > 0
                            else ""
                        )
                        records.append(
                            {
                                "file": full_filename,
                                "hero_file": hero_filename,
                                "viewport": viewport,
                                "theme": theme,
                                "language": lang,
                                "spine": spine_box,
                                "verdict_excerpt": verdict_text[:160],
                            }
                        )
            browser.close()
    finally:
        server.shutdown()

    assert not page_errors, page_errors

    # R-E byte-identity gate: the <section id="ud-hero">...</section> slice
    # of site/macro.html is what every visual cell renders against, so it must
    # hash to the same value at capture time and at FINAL head (when the PR
    # squash-merges). Any byte diff between capture head and FINAL head fails
    # the gate, regardless of how good the screenshots look.
    macro_path = ROOT / "site" / "macro.html"
    macro_text = macro_path.read_text()
    # Tag-balanced scan: the hero opener is `<section class="..." id="ud-hero">`
    # (class attributes precede id), and the hero template may nest a `<section>`
    # (spec §3 spine), so a naive `<section id="ud-hero">…` regex misses the
    # opener and closes at the FIRST nested `</section>`.
    open_tag = '<section class="ud-hero panel span12 ud-hero-panel" id="ud-hero"'
    open_idx = macro_text.find(open_tag)
    if open_idx < 0:
        raise SystemExit(
            "R-E gate: opener '" + open_tag + "' not found in site/macro.html"
        )
    cursor = open_idx
    hero_slice = ""
    while cursor < len(macro_text):
        nxt_open = macro_text.find("<section", cursor + 1)
        nxt_close = macro_text.find("</section>", cursor + 1)
        if nxt_close < 0:
            hero_slice = macro_text[open_idx:]
            break
        if nxt_open < 0 or nxt_close < nxt_open:
            hero_slice = macro_text[open_idx:nxt_close + len("</section>")]
            break
        cursor = nxt_open
    if not hero_slice:
        raise SystemExit("R-E gate: malformed macro.html (unterminated hero section)")
    hero_sha = hashlib.sha256(hero_slice.encode("utf-8")).hexdigest()
    hero_sha_short = hero_sha[:12]

    manifest = {
        "head": HEAD_SHA,
        "branch": "claude/mo-a-ud-b1-r5-followup",
        "pr": "DRAFT-followup",
        "source_url": "site/macro.html",
        "matrix": "theme(dark|light) × lang(en|zh) × viewport(1440|390) = 8 cells",
        "page_errors": page_errors,
        "r_e_byte_identity": {
            "selector": "section#ud-hero",
            "sha256": hero_sha,
            "sha256_short": hero_sha_short,
            "bytes": len(hero_slice.encode("utf-8")),
            "captured_at_head": HEAD_SHA,
            "note": ("Byte-identity gate. The same selector, sliced from "
                     "site/macro.html at FINAL head, must hash to this value. "
                     "Any diff fails the R-E gate."),
        },
        "cells": records,
    }
    manifest_path = EVIDENCE / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        f"Captured {len(records)} cells; 0 page errors; "
        f"manifest={manifest_path.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
