"""Element-screenshot evidence for the debt-maturity panel (packet B-F09-3).

META-CEO B ruling (2026-09-07 06:20Z) r4 BLOCKER: each cell is a Playwright
element screenshot of ``#debt-maturity`` taken on the REAL ticker page
produced by the page's own template pipeline (``templates/ticker.html.j2``,
the same render path ``scripts/build_ticker_pages.py`` uses), with the
page's own CSS — ``theme.css`` AND the ``.mod`` / ``.mod-hd`` / ``.mod-ft``
chrome that lives in the ticker template — inside the real ``.page-wrap``
width. No synthetic stylesheet fragment. No fixture page whose only
stylesheet is ``theme.css``.

MAJOR-3: the content-addressed filename and the manifest ``sha256`` are
computed from the FINAL PNG bytes (the element screenshot). A test asserts
every committed cell's digest equals the file on disk.

Isolation: rendered HTML + copies of ``theme.css`` / ``theme.js`` are written
into a scratch directory only (never into ``site/`` or ``data/``). Output
goes only under ``mockups/evidence/debt_maturity/``.

Usage::

    python3 -m scripts.capture_debt_maturity_evidence
"""
from __future__ import annotations

import hashlib
import json
import shutil
import struct
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"
OUT_DIR = REPO_ROOT / "mockups" / "evidence" / "debt_maturity"

# Six statuses that render ``#debt-maturity``. ``not_applicable`` renders
# neither chip nor section — nothing to crop; pinned by tests.
STATUSES = (
    "reported",
    "not_loaded",
    "no_filings",
    "identity_mismatch",
    "unresolved",
    "no_maturity_facts",
)

VIEWPORTS = {
    "desktop": (1440, 900),
    "mobile": (390, 844),
}
LOCALES = ("en", "zh")
THEMES = ("dark", "light")

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
  const docEl = document.documentElement;
  if (typeof window.setTheme === 'function') { window.setTheme(state.theme); }
  else {
    docEl.setAttribute('data-theme', state.theme);
    try { localStorage.setItem('theme', state.theme); localStorage.removeItem('themeAuto'); } catch (e) {}
  }
  if (typeof window.setLang === 'function') { window.setLang(state.locale); }
  else {
    docEl.setAttribute('data-lang', state.locale);
    if (state.locale) docEl.lang = state.locale;
    try { localStorage.setItem('lang', state.locale); } catch (e) {}
  }
  return {theme: docEl.getAttribute('data-theme'), locale: docEl.getAttribute('data-lang')};
}
"""


def content_address_png(png: bytes, output_dir: Path) -> tuple[str, str, int, int]:
    """Write PNG named by sha256[:16] of THESE bytes. Return (file, sha256, w, h).

    MAJOR-3: hash and filename are derived from the final bytes, never from a
    pre-trim / pre-crop buffer.
    """
    digest = hashlib.sha256(png).hexdigest()
    name = f"{digest[:16]}.png"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / name
    if not path.exists():
        path.write_bytes(png)
    if len(png) >= 24 and png[:8] == b"\x89PNG\r\n\x1a\n" and png[12:16] == b"IHDR":
        width, height = struct.unpack(">II", png[16:24])
    else:
        width, height = 0, 0
    return name, digest, int(width), int(height)


def _status_contexts() -> dict[str, dict]:
    from engine.debt_maturity import extract_maturity_ladder

    fixture = json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "debt_maturity" / "aapl_trimmed.json").read_text()
    )
    as_of = date(2025, 1, 1)
    reported = extract_maturity_ladder(fixture, cik="0000320193", as_of=as_of)
    no_filings = extract_maturity_ladder(None, cik="0000999999", as_of=as_of)
    not_loaded = {
        "schema": "debt_maturity.v1", "status": "not_loaded", "cik": "0000320193",
        "buckets": [], "total_reported_usd": None, "total_display": None,
        "near_share_pct": None, "buckets_reported": 0, "buckets_total": 6,
        "as_of": as_of.isoformat(),
    }
    identity_mismatch = extract_maturity_ladder(fixture, cik="0000999999", as_of=as_of)
    unresolved = {
        "schema": "debt_maturity.v1", "status": "unresolved", "cik": None,
        "buckets": [], "total_reported_usd": None, "total_display": None,
        "near_share_pct": None, "buckets_reported": 0, "buckets_total": 6,
        "as_of": as_of.isoformat(),
    }
    no_maturity_facts = extract_maturity_ladder(
        {"cik": "0000320193", "facts": {"us-gaap": {}}}, cik="0000320193", as_of=as_of,
    )
    assert reported["status"] == "reported", reported["status"]
    assert no_filings["status"] == "no_filings", no_filings["status"]
    assert identity_mismatch["status"] == "identity_mismatch", identity_mismatch["status"]
    assert no_maturity_facts["status"] == "no_maturity_facts", no_maturity_facts["status"]
    return {
        "reported": reported,
        "not_loaded": not_loaded,
        "no_filings": no_filings,
        "identity_mismatch": identity_mismatch,
        "unresolved": unresolved,
        "no_maturity_facts": no_maturity_facts,
    }


def render_ticker_page(debt_maturity: dict) -> str:
    """Render the real ticker template — same Jinja path as build_ticker_pages.

    Uses ``tests.test_ticker_pages._rich_ctx`` so the page carries the same
    sections the render-path tests already exercise, then injects this
    packet's ``debt_maturity`` block. The template's own ``t`` macro (both
    EN and ZH spans) and the inline ``.mod`` chrome stay intact.
    """
    from tests.test_ticker_pages import _jinja_env, _rich_ctx

    env = _jinja_env()
    ctx = _rich_ctx()
    ctx["debt_maturity"] = debt_maturity
    return env.get_template("ticker.html.j2").render(**ctx)


def _write_real_pages(scratch: Path, contexts: dict[str, dict]) -> None:
    shutil.copy(TEMPLATES_DIR / "theme.css", scratch / "theme.css")
    shutil.copy(TEMPLATES_DIR / "theme.js", scratch / "theme.js")
    (scratch / "data_base.js").write_text("/* capture stub */\n")
    stocks = scratch / "stocks"
    stocks.mkdir()
    for status, dm in contexts.items():
        (stocks / f"{status}.html").write_text(render_ticker_page(dm))


def _git_head_of_repo() -> tuple[str | None, str | None]:
    from scripts.capture_page_evidence import _git_head_sha

    head = _git_head_sha(REPO_ROOT)
    return head.sha, str(head.gitdir) if head.gitdir is not None else None


def _capture_cells(scratch: Path) -> dict:
    from scripts.capture_page_evidence import CaptureUnavailable, serve_site_dir

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise CaptureUnavailable(f"playwright is not importable: {exc}") from exc

    httpd, port = serve_site_dir(scratch)
    base = f"http://127.0.0.1:{port}"
    sha, gitdir = _git_head_of_repo()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pages: list[dict] = []
    written: set[str] = set()

    try:
        manager = sync_playwright().start()
        try:
            browser = manager.chromium.launch(headless=True)
        except Exception as exc:
            manager.stop()
            raise CaptureUnavailable(f"no chromium binary is installed: {exc}") from exc
        try:
            for status in STATUSES:
                states: list[dict] = []
                for viewport, (width, height) in VIEWPORTS.items():
                    for locale in LOCALES:
                        for theme in THEMES:
                            state = {"theme": theme, "locale": locale}
                            context = browser.new_context(
                                viewport={"width": width, "height": height},
                                locale="zh-CN" if locale == "zh" else "en-US",
                                color_scheme=theme,
                                device_scale_factor=1,
                            )
                            context.add_init_script(
                                f"({_STATE_SEED_SCRIPT.strip()})({json.dumps(state)})"
                            )
                            page = context.new_page()
                            entry: dict = {
                                "viewport": viewport,
                                "locale": locale,
                                "theme": theme,
                                "access": "anonymous",
                                "viewport_width": width,
                                "viewport_height": height,
                                "force_state": None,
                            }
                            try:
                                url = f"{base}/stocks/{status}.html"
                                response = page.goto(url, wait_until="load", timeout=30000)
                                if response is None or not response.ok:
                                    raise RuntimeError(
                                        f"HTTP {getattr(response, 'status', 'none')}"
                                    )
                                page.wait_for_timeout(400)
                                applied = page.evaluate(_APPLY_STATE_SCRIPT.strip(), state) or {}
                                page.wait_for_timeout(200)
                                loc = page.locator("#debt-maturity")
                                loc.wait_for(state="attached", timeout=5000)
                                loc.scroll_into_view_if_needed()
                                # Real page: html.has-js .rv starts at opacity 0
                                # until IntersectionObserver adds .in. Wait for
                                # that class (the page's own reveal), then let
                                # the bar transition settle.
                                page.wait_for_function(
                                    """() => {
                                      const el = document.getElementById('debt-maturity');
                                      return el && el.classList.contains('in');
                                    }""",
                                    timeout=5000,
                                )
                                page.wait_for_timeout(650)
                                png = loc.screenshot(type="png")
                                name, digest, pw, ph = content_address_png(png, OUT_DIR)
                                written.add(name)
                                entry.update(
                                    {
                                        "captured": True,
                                        "file": name,
                                        "sha256": digest,
                                        "bytes": len(png),
                                        "width": pw,
                                        "height": ph,
                                        "applied_theme": applied.get("theme"),
                                        "applied_locale": applied.get("locale"),
                                    }
                                )
                            except Exception as exc:
                                entry.update(
                                    {
                                        "captured": False,
                                        "reason": f"{type(exc).__name__}: {exc}",
                                    }
                                )
                            finally:
                                context.close()
                            states.append(entry)
                captured_n = sum(1 for s in states if s.get("captured"))
                pages.append(
                    {
                        "page_id": f"{status}.html",
                        "route": f"/stocks/{status}.html",
                        "registry_route": f"/stocks/{status}.html",
                        "route_kind": "ticker_page_element",
                        "states": states,
                        "metrics": {},
                        "console_errors": [],
                        "failed_responses": [],
                        "gaps": [],
                    }
                )
                print(
                    f"  {status}: {captured_n}/{len(states)} cells",
                    flush=True,
                )
        finally:
            browser.close()
            manager.stop()
    finally:
        httpd.shutdown()

    attempted = sum(len(p["states"]) for p in pages)
    captured = sum(1 for p in pages for s in p["states"] if s.get("captured"))
    outcome = "captured" if captured == attempted and attempted else "partial"
    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": generated_at,
        "tool": {
            "module_ref": "scripts/capture_debt_maturity_evidence.py",
            "version": "r4-element-ticker",
            "capture_method": (
                "playwright locator('#debt-maturity').screenshot() on a "
                "ticker.html.j2 render (theme.css + page-owned .mod chrome, "
                "real .page-wrap). sha256 and filename computed from the "
                "element-screenshot bytes after the shot, never before."
            ),
        },
        "target": {
            "kind": "site_dir",
            "base_url": None,
            "site_dir": str(scratch),
            "resolved_sha_or_none": sha,
            "resolved_gitdir_or_none": gitdir,
            "resolved_sha_source": (
                f"HEAD of the capture checkout ({gitdir}); scratch site-dir "
                "is a throwaway ticker.html.j2 render, not a second evidence plane"
            ),
        },
        "axes": {
            "viewports": {name: list(size) for name, size in VIEWPORTS.items()},
            "locales": list(LOCALES),
            "themes": list(THEMES),
            "access": ["anonymous"],
            "force_states": [],
        },
        "selection": {
            "mode": "explicit_routes",
            "statuses": list(STATUSES),
            "selector": "#debt-maturity",
        },
        "excluded": [],
        "outcome": outcome,
        "totals": {
            "pages": len(pages),
            "states_attempted": attempted,
            "states_captured": captured,
        },
        "honesty": {
            "access": "anonymous only",
            "gaps": "uncaptured cells are recorded with a reason",
            "authority": "this tool screenshots; it scores nothing",
            "page": (
                "real ticker.html.j2 via the same FileSystemLoader path as "
                "scripts/build_ticker_pages.py / tests/test_ticker_pages.py; "
                "no synthetic stylesheet fragment; ambient wash is the page's "
                "own (not disabled). Element screenshot of #debt-maturity "
                "carries .mod / .mod-hd / .mod-ft chrome inside .page-wrap."
            ),
        },
        "pages": pages,
    }
    smells = {
        "schema": "mastermind.page_ux_smells.v1",
        "generated_at": generated_at,
        "disclaimer": "element-screenshot capture; smells not re-censused",
        "pages": [{"page_id": p["page_id"], "route": p["route"]} for p in pages],
    }
    return {"manifest": manifest, "smells": smells, "written": sorted(written), "outcome": outcome}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for stale in OUT_DIR.glob("*.png"):
        stale.unlink()

    scratch = Path(tempfile.mkdtemp(prefix="dm_ticker_evidence_"))
    try:
        print("rendering ticker.html.j2 for", ", ".join(STATUSES), flush=True)
        _write_real_pages(scratch, _status_contexts())
        payloads = _capture_cells(scratch)
        (OUT_DIR / "manifest.json").write_text(
            json.dumps(payloads["manifest"], indent=2) + "\n"
        )
        (OUT_DIR / "smells.json").write_text(
            json.dumps(payloads["smells"], indent=2) + "\n"
        )
        (OUT_DIR / "EVIDENCE.yml").write_text(
            "schema: mastermind.page_evidence_receipt.v1\n"
            "changed_paths:\n"
            "  - templates/theme.css\n"
            "  - templates/_debt_maturity.html.j2\n"
            "  - templates/ticker.html.j2\n"
            "manifest: mockups/evidence/debt_maturity/manifest.json\n"
        )
        totals = payloads["manifest"]["totals"]
        print(
            f"outcome: {payloads['outcome']}\n"
            f"pages: {totals['pages']}  states: "
            f"{totals['states_captured']}/{totals['states_attempted']} captured",
            flush=True,
        )
        return 0 if payloads["outcome"] == "captured" else 1
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
