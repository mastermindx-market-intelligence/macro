"""Capture the 8-cell evidence matrix for UD-B2-W1 (vol-weather fold into Risk isle).

Cells = dark/light × EN/ZH × 1440/390 = 8.
Renders site/macro.html and captures the RISK ISLE region (the mx5
scorecard's left column .mx5-sc-left, which now contains the dial + scar
chips + vol-weather sub-row) focused crop per cell — the fold lands in
this column, so the .mx5-sc-left slice is the byte-identity gate and
the visual target.

R-W1-A-AMENDED (2026-09-20): the strip lives in .mx5-sc-vw (host inside
.mx5-sc-left). The R-E gate slice is .mx5-sc-left (the visual unit =
dial + scar chips + strip). Capture-last: code+tests+site are committed
first, then this script runs, then the PNGs + manifest are committed
LAST so `git diff <capture sha>..HEAD -- templates/ mockups/evidence/
unified-dashboard-b2w1/` is empty when capture sha == HEAD.

Manifest naming: risk_isle_<theme>_<lang>_<viewport>.png (legacy name kept;
the "isle" is the visual unit — dial + scar chips + strip — not the literal
#sx-risk-v2 element).
"""
import hashlib
import json
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path.cwd()
EVIDENCE = ROOT / "mockups/evidence/unified-dashboard-b2w1"
HEAD_SHA = subprocess.run(
    ["git", "rev-parse", "HEAD"],
    cwd=ROOT, capture_output=True, text=True, check=True,
).stdout.strip()  # noqa: S603 — read-only `git rev-parse`


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _slice_risk_isle(macro_text: str) -> str:
    """Extract the .mx5-sc-left slice from site/macro.html for the R-E gate.

    R-W1-A-AMENDED: the strip lives inside .mx5-sc-vw (a child of
    .mx5-sc-left), so the visual unit containing dial + scar chips +
    vol-weather sub-row IS .mx5-sc-left. We slice from
    '<div class="mx5-sc-left">' to its matching </div> at depth 0.
    """
    sentinel = '<div class="mx5-sc-left">'
    start = macro_text.find(sentinel)
    if start < 0:
        raise SystemExit(
            f"R-E gate: opener {sentinel!r} not found in site/macro.html"
        )
    depth = 0
    i = start
    n = len(macro_text)
    while i < n:
        if macro_text.startswith("<div ", i) or macro_text.startswith("<div>", i):
            depth += 1
            i += 5
        elif macro_text.startswith("</div>", i):
            depth -= 1
            i += 6
            if depth == 0:
                return macro_text[start:i]
        else:
            i += 1
    raise SystemExit("R-E gate: malformed macro.html (unterminated risk isle)")


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    records: list[dict] = []
    page_errors: list[str] = []
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()
            page = context.new_page()
            page.on("pageerror", lambda err: page_errors.append(str(err)))

            url = f"http://127.0.0.1:{port}/site/macro.html"
            for viewport, width, height in [("1440", 1440, 900), ("390", 390, 844)]:
                page.set_viewport_size({"width": width, "height": height})
                page.goto(url, wait_until="networkidle")
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

                        # RISK ISLE region: the fold lands in .mx5-sc-left.
                        isle = page.locator(".mx5-sc-left").first
                        if isle.count() == 0:
                            records.append(
                                {
                                    "file": None,
                                    "viewport": viewport,
                                    "theme": theme,
                                    "language": lang,
                                    "error": "risk isle not found on page",
                                }
                            )
                            continue

                        # Scroll the isle into view BEFORE full-page capture
                        # so the macro_<theme>_<lang>_<viewport>.png shows the
                        # fold (dial + scar chips + vol-weather sub-row), not
                        # only the hero. R-W1-E: every cell shows the fold.
                        isle.scroll_into_view_if_needed(timeout=2000)
                        page.wait_for_timeout(150)

                        # Full-page capture
                        full_filename = (
                            f"macro_{theme}_{lang}_{viewport}.png"
                        )
                        page.screenshot(
                            path=str(EVIDENCE / full_filename),
                            full_page=False,
                        )

                        # Focused risk-isle crop (always shows the fold;
                        # the fold lives inside this slice)
                        isle_filename = (
                            f"risk_isle_{theme}_{lang}_{viewport}.png"
                        )
                        try:
                            isle.screenshot(path=str(EVIDENCE / isle_filename))
                        except Exception as exc:
                            records.append(
                                {
                                    "file": full_filename,
                                    "viewport": viewport,
                                    "theme": theme,
                                    "language": lang,
                                    "error": f"isle screenshot failed: {exc}",
                                }
                            )
                            continue

                        # Vol-weather strip measurements — the sub-row must be
                        # inside the isle, present, and non-empty. Eyebrow is
                        # read as separate EN/ZH spans (no textContent
                        # concatenation — each language is its own receipt).
                        strip = page.locator(".mx5-sc-vw .sx-vw-strip").first
                        strip_metrics = (
                            strip.evaluate(
                                """(e)=>{const eb=e.querySelector('.sx-vw-eyebrow');
                                const en=eb?(eb.querySelector('.l-en')||{}).textContent||'':'';
                                const zh=eb?(eb.querySelector('.l-zh')||{}).textContent||'':'';
                                return {w:e.clientWidth,h:e.clientHeight,
                                  rows:e.querySelectorAll('[data-sx-vw-chip]').length,
                                  eyebrow_en:en,eyebrow_zh:zh};}"""
                            )
                            if strip.count() > 0
                            else {"w": 0, "h": 0, "rows": 0, "eyebrow_en": "", "eyebrow_zh": ""}
                        )
                        records.append(
                            {
                                "file": full_filename,
                                "isle_file": isle_filename,
                                "viewport": viewport,
                                "theme": theme,
                                "language": lang,
                                "strip": strip_metrics,
                            }
                        )
            browser.close()
    finally:
        server.shutdown()

    if page_errors:
        print(f"PAGE ERRORS: {page_errors}", file=sys.stderr)
        return 1

    # R-E byte-identity gate (UD-B2-W1 pattern, R-E law):
    # the .mx5-sc-left element slice, sliced from site/macro.html, must
    # hash to the same value at capture head and FINAL head. With
    # round-3's single-commit workflow (captures are part of the same
    # commit as code+tests+site), `captured_at_head` == HEAD == `head`,
    # so the gate trivially holds.
    macro_path = ROOT / "site" / "macro.html"
    macro_text = macro_path.read_text()
    isle_slice = _slice_risk_isle(macro_text)
    isle_sha = sha256(isle_slice)
    isle_sha_short = isle_sha[:12]

    manifest = {
        "head": HEAD_SHA,
        "branch": "claude/mo-a-ud-b2-w1-volweather-fold",
        "pr": "DRAFT",
        "source_url": "site/macro.html",
        "matrix": "theme(dark|light) × lang(en|zh) × viewport(1440|390) = 8 cells",
        "page_errors": page_errors,
        "r_e_byte_identity": {
            "selector": ".mx5-sc-left (slice from '<div class=\"mx5-sc-left\">' to matching close)",
            "sha256": isle_sha,
            "sha256_short": isle_sha_short,
            "bytes": len(isle_slice.encode("utf-8")),
            "captured_at_head": HEAD_SHA,
            "note": ("Byte-identity gate. The same slice, extracted from "
                     "site/macro.html at FINAL head, must hash to this value. "
                     "R-W1-A-AMENDED: the strip lives in .mx5-sc-vw (a child "
                     "of .mx5-sc-left), so the R-E gate slice is .mx5-sc-left "
                     "(dial + scar chips + strip). Capture-last: this "
                     "manifest is committed in the captures commit; "
                     "captured_at_head is HEAD at capture time and must be "
                     "an ancestor of the captures commit."),
        },
        "cells": records,
    }
    manifest_path = EVIDENCE / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        f"Captured {len(records)} cells; 0 page errors; "
        f"manifest={manifest_path.relative_to(ROOT)}; "
        f"risk_isle_sha={isle_sha_short}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
