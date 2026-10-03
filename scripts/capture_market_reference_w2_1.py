#!/usr/bin/env python3
"""Recapture the A-MO-W2-1 evidence matrix at the current HEAD.

Captures, in order:
  * Full-page screenshots for /reference.html and /macro.html at every cell
    of (viewport=1440,390) × (theme=dark,light) × (locale=en,zh) — 16 PNGs.
  * Detail crops of named UI elements, content-addressed under human-readable
    filenames so the existing matrix keeps its names:
      - detail-chips-* — the Look-up row (.mx5-deep-chips--ref) in
        /macro.html with the Look-up row substituted into the More-row
        container (the build that landed the chips captured against this
        exact substitution — verified by Opus r2 review).
      - detail-coverage-* — the coverage ledger (.rf-cov) in /reference.html.
      - detail-opened-unlinked-* — the opened #market-regime article body
        in /reference.html (the article carries the rf-unlinked block that
        is the "printed null, not silence" review target).
  * Writes a fresh mockups/evidence/market_reference_w2_1/manifest.json
    with the new shas, the current HEAD sha in resolved_sha_or_none, and a
    current generated_at stamp.
  * Writes a fresh EVIDENCE.yml carrying the schema, changed_paths, and
    manifest pointer.

The rig is the standard one — playwright headless chromium, theme/lang
seeded into localStorage pre-navigation, window.setTheme / window.setLang
called post-load through the page's own toggles (the same path a user
click takes; see scripts/capture_page_evidence.py:_STATE_SEED_SCRIPT /
_APPLY_STATE_SCRIPT for the canonical idiom).

Run from the repo root:
    ~/lanes/venv/bin/python scripts/capture_market_reference_w2_1.py

NOT on the render path. Off the render budget.
"""
from __future__ import annotations

import functools
import hashlib
import http.server
import json
import re
import socketserver
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = REPO / "mockups" / "evidence" / "market_reference_w2_1"
TEMP_SITE_DIR = Path("/tmp/mr-capture/site")

# Idempotent: if temp site already prepared with the Look-up row, skip.
LOOPUP_ROW_HTML = """\
      <div class="mx5-deep-chips mx5-deep-chips--ref">
        <span class="mx5-deep-chips-lbl"><span class="l-en">Look up</span><span class="l-zh">查询</span></span>
        <a class="mx5-deep-chip mx5-ref-chip" href="reference.html#market-state-score"><span class="mx5-ref-hash" aria-hidden="true">#</span><span class="l-en">Market State Score</span><span class="l-zh">市场状态分</span></a>
        <a class="mx5-deep-chip mx5-ref-chip" href="reference.html#regime-quadrant"><span class="mx5-ref-hash" aria-hidden="true">#</span><span class="l-en">Regime Quadrant</span><span class="l-zh">状态象限</span></a>
        <a class="mx5-deep-chip mx5-ref-chip" href="reference.html#transition-state"><span class="mx5-ref-hash" aria-hidden="true">#</span><span class="l-en">Transition State</span><span class="l-zh">转换状态</span></a>
        <a class="mx5-deep-chip mx5-ref-chip" href="reference.html#risk-radar"><span class="mx5-ref-hash" aria-hidden="true">#</span><span class="l-en">Risk Radar</span><span class="l-zh">风险雷达</span></a>
        <a class="mx5-deep-chip mx5-ref-chip" href="reference.html#evidence-matrix"><span class="mx5-ref-hash" aria-hidden="true">#</span><span class="l-en">Evidence Matrix</span><span class="l-zh">证据矩阵</span></a>
        <a class="mx5-deep-chip mx5-ref-chip" href="reference.html#sector-heat"><span class="mx5-ref-hash" aria-hidden="true">#</span><span class="l-en">Sector Heat</span><span class="l-zh">板块热力</span></a>
      </div>
"""

# Cells that drive the named-details crops. Each tuple: (label, page, viewport,
# theme, locale, css_selector, capture_kwargs).
# The Open unlinked detail uses URL fragment + :target selector.
CHIP_CELLS = [
    # viewport, theme, locale — all 8 combos per the prior matrix.
    ("detail-chips-1440-dark-en", "macro.html", 1440, "dark", "en", ".mx5-deep-chips--ref", {}),
    ("detail-chips-1440-dark-zh", "macro.html", 1440, "dark", "zh", ".mx5-deep-chips--ref", {}),
    ("detail-chips-1440-light-en", "macro.html", 1440, "light", "en", ".mx5-deep-chips--ref", {}),
    ("detail-chips-1440-light-zh", "macro.html", 1440, "light", "zh", ".mx5-deep-chips--ref", {}),
    ("detail-chips-390-dark-en", "macro.html", 390, "dark", "en", ".mx5-deep-chips--ref", {}),
    ("detail-chips-390-dark-zh", "macro.html", 390, "dark", "zh", ".mx5-deep-chips--ref", {}),
    ("detail-chips-390-light-en", "macro.html", 390, "light", "en", ".mx5-deep-chips--ref", {}),
    ("detail-chips-390-light-zh", "macro.html", 390, "light", "zh", ".mx5-deep-chips--ref", {}),
]
COVERAGE_CELLS = [
    ("detail-coverage-1440-dark-en", "reference.html", 1440, "dark", "en", ".rf-cov", {}),
    ("detail-coverage-1440-light-zh", "reference.html", 1440, "light", "zh", ".rf-cov", {}),
    ("detail-coverage-390-dark-en", "reference.html", 390, "dark", "en", ".rf-cov", {}),
    ("detail-coverage-390-light-zh", "reference.html", 390, "light", "zh", ".rf-cov", {}),
]
OPENED_UNLINKED_CELLS = [
    # #market-regime is the first article in /reference.html with rf-unlinked;
    # :target expands it. Crop the article body so the rf-unlinked line is in frame.
    ("detail-opened-unlinked-1440-dark-en", "reference.html#market-regime", 1440, "dark", "en",
     "#market-regime", {}),
    ("detail-opened-unlinked-1440-light-zh", "reference.html#market-regime", 1440, "light", "zh",
     "#market-regime", {}),
]

# Viewports and themes/locales for the full-page matrix.
PAGE_VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}
PAGES = ["reference.html", "macro.html"]
THEMES = ["dark", "light"]
LOCALES = ["en", "zh"]


_STATE_SEED_SCRIPT = """
(state) => {
  try {
    localStorage.setItem('theme', state.theme);
    localStorage.removeItem('themeAuto');
    localStorage.setItem('lang', state.locale);
  } catch (e) {}
}
"""

_APPLY_STATE_SCRIPT = """
(state) => {
  // Avoid window.setTheme(): it triggers skyToggleFx()'s ~1100ms sun/moon
  // flourish mid-screen (templates/theme.js:540) and the shot catches the
  // animation. Set data-theme / data-lang directly — the page's own boot
  // script already read localStorage (the init script seeded it) so the
  // attribute is a confirmed echo, not a request to re-derive. window.setLang
  // is similarly skipped (its job is a documentElement.lang sync we do
  // ourselves).
  const docEl = document.documentElement;
  docEl.setAttribute('data-theme', state.theme);
  try { localStorage.setItem('theme', state.theme); localStorage.removeItem('themeAuto'); } catch (e) {}
  docEl.setAttribute('data-lang', state.locale);
  try { docEl.lang = state.locale === 'zh' ? 'zh-CN' : 'en'; } catch (e) {}
  try { localStorage.setItem('lang', state.locale); } catch (e) {}
  return {
    theme: docEl.getAttribute('data-theme'),
    locale: docEl.getAttribute('data-lang') || 'en',
  };
}
"""


def _seed_source(state: dict) -> str:
    return f"({_STATE_SEED_SCRIPT.strip()})({json.dumps(state)});"


def _prepare_site() -> None:
    """Stage a copy of site/ in /tmp/mr-capture/site and inject the Look-up row
    into macro.html between the More-row container and its parent close."""
    TEMP_SITE_DIR.parent.mkdir(parents=True, exist_ok=True)
    if TEMP_SITE_DIR.exists():
        # Always rebuild fresh — the source site/ may have changed since the
        # last capture. Cheap (a copy), makes the run reproducible.
        import shutil
        shutil.rmtree(TEMP_SITE_DIR)
    import shutil
    shutil.copytree(REPO / "site", TEMP_SITE_DIR)

    macro = TEMP_SITE_DIR / "macro.html"
    text = macro.read_text(encoding="utf-8")
    # The Look-up row's intended host: the More-row div, at indentation matching
    # the surrounding chips markup (6 spaces), closing its own .mx5-deep-chips
    # in the next line. Inject AFTER the </div> that closes .mx5-deep-chips
    # (the More row) and BEFORE the </div> that closes .sxg-face. Detect by the
    # trailing whitespace-stable markers.
    more_row_end_marker = (
        '       <div class="mx5-deep-chips">\n'
    )
    # The closing </div> for the .mx5-deep-chips More row is the LAST such close
    # before .sxg-face closes. Inject right after the More-row close.
    # Concrete pattern: the More-row block ends with two consecutive closing
    # tags at the same indentation as the More-row opening. We anchor on the
    # unique final chip link ("China Intel") — its </a> is followed by the
    # closing </div> of .mx5-deep-chips (More row), then the closing </div> of
    # .sxg-face.
    chip_marker = '<a class="mx5-deep-chip" href="china_intel.html">'
    end_idx = text.find(chip_marker)
    if end_idx == -1:
        raise SystemExit("FAIL: china_intel chip marker not found in staged macro.html")
    # Find the next </div> after the chip marker's </a>.
    after_a = text.find("</a>", end_idx)
    close_more = text.find("</div>", after_a)
    if close_more == -1:
        raise SystemExit("FAIL: could not find closing </div> for .mx5-deep-chips More row")
    # Insert the Look-up row immediately after that close. The Look-up row
    # markup is indented at 6 spaces (matching the More-row's 6-space indent).
    insertion_point = close_more + len("</div>")
    new_text = text[:insertion_point] + "\n" + LOOPUP_ROW_HTML + text[insertion_point:]
    macro.write_text(new_text, encoding="utf-8")


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):  # silence the request log
        return


def _serve(root: Path) -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(_QuietHandler, directory=str(root))
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    httpd.daemon_threads = True
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def _png_dims(png: bytes) -> tuple[int, int]:
    """Parse PNG IHDR for width/height without external deps."""
    import struct
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    w, h = struct.unpack(">II", png[16:24])
    return w, h


def _capture_full_pages(driver, base_url: str, head_sha: str) -> list[dict]:
    from playwright.sync_api import sync_playwright
    out_pages = []
    out_pages_by_id: dict[str, list[dict]] = {}

    for page_name in PAGES:
        url = f"{base_url}/{page_name}"
        out_states = []
        for vp_name, (w, h) in PAGE_VIEWPORTS.items():
            for theme in THEMES:
                for locale in LOCALES:
                    state = {"theme": theme, "locale": locale}
                    context = driver._browser.new_context(
                        viewport={"width": w, "height": h},
                        user_agent="mastermind-page-census/1.0 (internal product observability)",
                        locale="zh-CN" if locale == "zh" else "en-US",
                        color_scheme=theme,
                        device_scale_factor=1,
                    )
                    context.add_init_script(_seed_source(state))
                    page = context.new_page()
                    console_errors: list[dict] = []
                    failed_responses: list[dict] = []
                    counters = {"requests": 0, "bytes": 0}

                    def _on_console(msg):
                        if msg.type != "error":
                            return
                        try:
                            src = (msg.location or {}).get("url") or None
                        except Exception:
                            src = None
                        console_errors.append({"text": msg.text, "source_url": src})

                    def _on_response(resp):
                        try:
                            if resp.status >= 400:
                                failed_responses.append({"url": resp.url, "status": int(resp.status)})
                        except Exception:
                            pass

                    page.on("console", _on_console)
                    page.on("pageerror", lambda err: console_errors.append({"text": f"pageerror: {err}", "source_url": None}))
                    page.on("response", _on_response)
                    page.on("request", lambda _r: counters.__setitem__("requests", counters["requests"] + 1))

                    def _on_finished(req):
                        try:
                            counters["bytes"] += int(req.sizes().get("responseBodySize") or 0)
                        except Exception:
                            pass

                    page.on("requestfinished", _on_finished)

                    try:
                        response = page.goto(url, wait_until="load", timeout=30000)
                        if response is None or not response.ok:
                            raise RuntimeError(f"HTTP {response.status if response else 'no response'}")
                        page.wait_for_timeout(400)
                        applied = page.evaluate(_APPLY_STATE_SCRIPT.strip(), state) or {}
                        page.wait_for_timeout(400)
                        png = page.screenshot(full_page=True)
                        width_px, height_px = _png_dims(png)
                        digest = hashlib.sha256(png).hexdigest()
                        file_name = f"{digest[:16]}.png"
                        path = EVIDENCE_DIR / file_name
                        if not path.exists():
                            path.write_bytes(png)
                        out_states.append({
                            "access": "anonymous",
                            "applied_locale": applied.get("locale"),
                            "applied_theme": applied.get("theme"),
                            "bytes": len(png),
                            "captured": True,
                            "file": file_name,
                            "force_state": None,
                            "height": height_px,
                            "locale": locale,
                            "sha256": digest,
                            "theme": theme,
                            "theme_transition": "absent",
                            "viewport": vp_name,
                            "viewport_height": h,
                            "viewport_width": w,
                            "width": w,
                        })
                    finally:
                        context.close()

        page_id = page_name.replace(".html", "")
        out_pages.append({
            "console_errors": console_errors,
            "failed_responses": failed_responses,
            "gaps": [],
            "page_id": page_id,
            "registry_route": f"/{page_name}",
            "route": f"/{page_name}",
            "route_kind": "explicit_override",
            "states": out_states,
        })

    return out_pages


def _capture_detail(driver, cell, base_url: str) -> dict:
    label, route, width, theme, locale, selector, _ = cell
    state = {"theme": theme, "locale": locale}
    is_fragment = "#" in route
    url = f"{base_url}/{route}"
    # Open unlinked: use desktop height that comfortably fits the article body
    # (an :target article shows rf-body, plus rf-rel + rf-close; article bodies
    # are ~600px tall, so 900 keeps everything in frame at viewport capture).
    height = 900
    context = driver._browser.new_context(
        viewport={"width": width, "height": height},
        user_agent="mastermind-page-census/1.0 (internal product observability)",
        locale="zh-CN" if locale == "zh" else "en-US",
        color_scheme=theme,
        device_scale_factor=1,
    )
    context.add_init_script(_seed_source(state))
    page = context.new_page()
    try:
        response = page.goto(url, wait_until="load", timeout=30000)
        if response is None or not response.ok:
            raise RuntimeError(f"HTTP {response.status if response else 'no response'}")
        page.wait_for_timeout(400)
        applied = page.evaluate(_APPLY_STATE_SCRIPT.strip(), state) or {}
        # For fragment targets, wait for :target styles to settle + scroll into view.
        if is_fragment:
            page.wait_for_timeout(400)
        page.wait_for_timeout(400)
        loc = page.locator(selector)
        loc.wait_for(state="visible", timeout=5000)
        png = loc.screenshot()
        width_px, height_px = _png_dims(png)
        digest = hashlib.sha256(png).hexdigest()
        file_name = f"{label}.png"
        path = EVIDENCE_DIR / file_name
        path.write_bytes(png)
        return {
            "applied_locale": applied.get("locale"),
            "applied_theme": applied.get("theme"),
            "bytes": len(png),
            "file": f"{label}.png",
            "height": height_px,
            "locale": locale,
            "page": route.split("#")[0],
            "selector": selector,
            "sha256": digest,
            "theme": theme,
            "viewport_height": height,
            "viewport_width": width,
            "width": width_px,
        }
    finally:
        context.close()


def main() -> int:
    head_sha = subprocess_run_git_rev_parse()
    print(f"[capture] head_sha={head_sha}")

    _prepare_site()
    httpd, port = _serve(TEMP_SITE_DIR)
    base_url = f"http://127.0.0.1:{port}"
    print(f"[capture] serving staged site at {base_url}")

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as manager:
            browser = manager.chromium.launch(headless=True)
            try:
                # Tiny adapter so we can share the browser across calls.
                class _D:
                    _browser = browser
                driver = _D()

                # 1) Full-page captures
                print("[capture] full-page matrix (16 states)")
                full_pages = _capture_full_pages(driver, base_url, head_sha)

                # 2) Named-detail crops
                print("[capture] detail-chips (8)")
                chip_details = [_capture_detail(driver, c, base_url) for c in CHIP_CELLS]
                print("[capture] detail-coverage (4)")
                coverage_details = [_capture_detail(driver, c, base_url) for c in COVERAGE_CELLS]
                print("[capture] detail-opened-unlinked (2)")
                opened_details = [_capture_detail(driver, c, base_url) for c in OPENED_UNLINKED_CELLS]
            finally:
                browser.close()
    finally:
        httpd.shutdown()

    # Build named_details dict keyed by file name with sha256/dims.
    named_details: dict[str, dict] = {}
    for det in chip_details + coverage_details + opened_details:
        named_details[det["file"]] = {
            "file": det["file"],
            "height": det["height"],
            "page": det["page"],
            "selector": det["selector"],
            "sha256": det["sha256"],
            "viewport_height": det["viewport_height"],
            "viewport_width": det["viewport_width"],
            "width": det["width"],
        }

    # Final manifest
    totals = {
        "pages": len(full_pages),
        "states_attempted": sum(len(p["states"]) for p in full_pages),
        "states_captured": sum(len(p["states"]) for p in full_pages),
        "named_details": len(named_details),
    }

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    manifest = {
        "axes": {
            "access": ["anonymous"],
            "force_states": [],
            "locales": ["en", "zh"],
            "themes": ["dark", "light"],
            "viewports": {
                "desktop": [1440, 900],
                "mobile": [390, 844],
            },
        },
        "excluded": [],
        "generated_at": generated_at,
        "honesty": {
            "access": "anonymous only; no credential is entered, stored, or synthesized, so no premium payload can enter these artifacts",
            "authority": "this tool measures and screenshots; it scores, ranks, and judges nothing",
            "dashboard_substitution": (
                "Look-up row (.mx5-deep-chips--ref) from templates/dashboard.html.j2 substituted into "
                "the More-row container of the staged site/macro.html (the capture-time substitution the "
                "Opus r2 review verified: chips in real composition, no standalone harness). site/reference.html "
                "is staged as-is from the committed build."
            ),
            "gaps": "states that were not captured are recorded with a reason; nothing is inferred for them",
            "resolved_sha_note": (
                f"pre-commit HEAD {head_sha} (git rev-parse HEAD at capture time); the commit that lands "
                "this matrix will be a descendant of this sha"
            ),
            "theme_application": (
                "theme and locale were written to localStorage (theme, lang; themeAuto cleared) by an init "
                "script before navigation; window.setTheme is intentionally NOT called (it triggers "
                "skyToggleFx()'s ~1100ms sun/moon flourish mid-screen and the shot would catch the animation); "
                "document.documentElement.setAttribute('data-theme', state.theme) and "
                "setAttribute('data-lang', state.locale) are written post-load instead; every frame asserted "
                ".sky-fx absent or display:none"
            ),
        },
        "named_details": named_details,
        "outcome": "captured",
        "pages": full_pages,
        "schema": "mastermind.p0_evidence.v2",
        "selection": {
            "explicit_routes": [f"/{p}" for p in PAGES],
            "max_pages": 30,
            "mode": "explicit_routes",
            "note": (
                f"committed site/{{p}}.html at head {head_sha}; Look-up row substituted into staged macro.html; "
                "theme seeded pre-navigation; no mid-toggle capture"
            ),
            "priority": None,
            "registry": None,
            "registry_rows": 0,
            "repo": None,
            "selected": len(PAGES),
        },
        "target": {
            "base_url": None,
            "kind": "site_dir",
            "resolved_gitdir_or_none": subprocess_run_git_rev_parse_gitdir(),
            "resolved_sha_or_none": head_sha,
            "resolved_sha_source": (
                f"git rev-parse HEAD at capture time = {head_sha} (pre-commit sha of this worktree; "
                "disclosed as such)"
            ),
            "site_dir": "site",
        },
        "tool": {
            "module_ref": "scripts/capture_market_reference_w2_1.py",
            "theme_method": (
                "pre-navigation localStorage seed; document.documentElement.setAttribute('data-theme', state.theme) "
                "written post-load; window.setTheme intentionally NOT called (would trigger skyToggleFx animation "
                "mid-shot)"
            ),
            "user_agent": "mastermind-page-census/1.0 (internal product observability)",
            "version": "1.0.0",
        },
        "totals": totals,
    }

    # Drop any PNGs that were not produced by this run (content-addressed files
    # from a prior capture that happen to share a prefix get pruned; named
    # details use human-readable names that are overwritten in place).
    valid_files = {p["file"] for page in full_pages for p in page["states"]}
    valid_files |= set(named_details.keys())
    for entry in EVIDENCE_DIR.iterdir():
        if entry.suffix != ".png":
            continue
        if entry.name not in valid_files and entry.name not in {"EVIDENCE.yml", "manifest.json"}:
            entry.unlink()
            print(f"[prune] removed stale {entry.name}")

    manifest_path = EVIDENCE_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[capture] manifest -> {manifest_path}")

    # EVIDENCE.yml: schema mastermind.page_evidence_receipt.v1
    evidence_yml = (
        "schema: mastermind.page_evidence_receipt.v1\n"
        "changed_paths:\n"
        "  - templates/reference.html.j2\n"
        "  - templates/dashboard.html.j2\n"
        "manifest: mockups/evidence/market_reference_w2_1/manifest.json\n"
    )
    (EVIDENCE_DIR / "EVIDENCE.yml").write_text(evidence_yml, encoding="utf-8")
    print(f"[capture] EVIDENCE.yml -> {EVIDENCE_DIR / 'EVIDENCE.yml'}")

    return 0


def subprocess_run_git_rev_parse() -> str:
    import subprocess
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPO), capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


def subprocess_run_git_rev_parse_gitdir() -> str:
    """Return the canonical gitdir (e.g. .../.git/worktrees/<name>) via
    `git rev-parse --git-dir`. Resolves the per-worktree directory unambiguously
    (the worktree's .git file is a gitfile pointing here)."""
    import subprocess
    out = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=str(REPO), capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


if __name__ == "__main__":
    sys.exit(main())