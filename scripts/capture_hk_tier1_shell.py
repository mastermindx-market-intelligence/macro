"""Element-screenshot evidence for the HK Tier-1 shell plain-language pass (H2).

Renders templates/hk.html.j2 with the same fixture VM as
tests/test_hk_tier1_shell.py (no data/ or site/ required), serves it from a
scratch dir with the page's own theme.css, and captures dark/light × EN/ZH ×
desktop 1440 / mobile 390 crops of the hero, the cross-market strip, and one
What To Do signal row.

Usage::

    python3 scripts/capture_hk_tier1_shell.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

OUT_DIR = _ROOT / "mockups" / "evidence" / "hk-tier1-shell"
REGIONS = (
    ("hero", "#hkx-hero-card"),
    ("strip", ".hkx-cas-strip"),
    ("signal-row", ".hkx-rack2 .hkx-row"),
)
VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}
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


def _render_html() -> str:
    from tests.test_hk_tier1_shell import _render
    return _render()


def _write_scratch(scratch: Path) -> None:
    html = _render_html()
    (scratch / "hk.html").write_text(html, encoding="utf-8")
    templates = _ROOT / "templates"
    for name in ("theme.css", "theme.js", "navigation-refresh.css",
                 "product-nav-icons.css", "illus.css"):
        src = templates / name
        if src.exists():
            shutil.copy(src, scratch / name)
    (scratch / "data_base.js").write_text("/* capture stub */\n")


def main() -> int:
    from scripts.capture_debt_maturity_evidence import content_address_png
    from scripts.capture_page_evidence import CaptureUnavailable, _git_head_sha, serve_site_dir

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        _write_failure_readme(f"playwright is not importable: {exc}")
        print(f"CAPTURE UNAVAILABLE: {exc}", file=sys.stderr)
        return 2

    scratch = Path(tempfile.mkdtemp(prefix="hk-tier1-shell-"))
    _write_scratch(scratch)
    httpd, port = serve_site_dir(scratch)
    base = f"http://127.0.0.1:{port}/hk.html"
    sha_info = _git_head_sha(_ROOT)
    sha = sha_info.sha if sha_info else None
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pages: list[dict] = []
    crop_list: list[str] = []

    try:
        manager = sync_playwright().start()
        try:
            browser = manager.chromium.launch(headless=True)
        except Exception as exc:
            manager.stop()
            _write_failure_readme(f"no chromium binary is installed: {exc}")
            print(f"CAPTURE UNAVAILABLE: {exc}", file=sys.stderr)
            return 2
        try:
            for region, selector in REGIONS:
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
                                reduced_motion="reduce",
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
                                response = page.goto(base, wait_until="load", timeout=30000)
                                if response is None or not response.ok:
                                    raise RuntimeError(
                                        f"HTTP {getattr(response, 'status', 'none')}"
                                    )
                                page.wait_for_timeout(250)
                                applied = page.evaluate(_APPLY_STATE_SCRIPT.strip(), state) or {}
                                # setTheme fires skyToggleFx (~1100ms sun/moon overlay). It is a
                                # toggle flourish, not page content; a 150ms wait used to shoot
                                # the crescent mid-animation on 390-dark (M3). Prefer-reduced-motion
                                # skips the mount; stripping .sky-fx is the fail-closed remainder.
                                page.evaluate(
                                    "() => document.querySelectorAll('.sky-fx').forEach(n => n.remove())"
                                )
                                page.wait_for_timeout(150)
                                loc = page.locator(selector).first
                                loc.wait_for(state="visible", timeout=8000)
                                png = loc.screenshot(type="png")
                                name, digest, pw, ph = content_address_png(png, OUT_DIR)
                                crop_list.append(
                                    f"{region}/{viewport}/{locale}/{theme} -> {name}"
                                )
                                entry.update({
                                    "captured": True,
                                    "file": name,
                                    "sha256": digest,
                                    "bytes": len(png),
                                    "width": pw,
                                    "height": ph,
                                    "applied_theme": applied.get("theme"),
                                    "applied_locale": applied.get("locale"),
                                })
                            except Exception as exc:
                                entry.update({
                                    "captured": False,
                                    "reason": f"{type(exc).__name__}: {exc}",
                                })
                            finally:
                                context.close()
                            states.append(entry)
                captured_n = sum(1 for s in states if s.get("captured"))
                pages.append({
                    "page_id": f"hk-tier1-{region}",
                    "route": "/hk.html",
                    "registry_route": "/hk.html",
                    "route_kind": "hk_tier1_shell_crop",
                    "selector": selector,
                    "states": states,
                    "metrics": {},
                    "console_errors": [],
                    "failed_responses": [],
                    "gaps": [],
                })
                print(f"  {region}: {captured_n}/{len(states)} cells", flush=True)
        finally:
            browser.close()
            manager.stop()
    finally:
        httpd.shutdown()
        shutil.rmtree(scratch, ignore_errors=True)

    attempted = sum(len(p["states"]) for p in pages)
    captured = sum(1 for p in pages for s in p["states"] if s.get("captured"))
    outcome = "captured" if captured == attempted and attempted else "partial"
    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": generated_at,
        "tool": {
            "module_ref": "scripts/capture_hk_tier1_shell.py",
            "version": "h2-fixture-render",
            "capture_method": (
                "playwright element screenshot on a templates/hk.html.j2 render "
                "with the tests/test_hk_tier1_shell.py fixture VM + theme.css. "
                "Sparse tree: no live data/ or site/ bake. Context prefers-reduced-motion "
                "and strips .sky-fx after setTheme so the ~1100ms theme-toggle flourish "
                "cannot occlude a crop (M3)."
            ),
        },
        "target": {
            "kind": "fixture_render",
            "base_url": None,
            "resolved_sha_or_none": sha,
            "resolved_gitdir_or_none": str(getattr(sha_info, "gitdir", None)),
        },
        "axes": {
            "viewports": {name: list(size) for name, size in VIEWPORTS.items()},
            "locales": list(LOCALES),
            "themes": list(THEMES),
            "access": ["anonymous"],
            "force_states": [],
        },
        "selection": {
            "mode": "explicit_regions",
            "regions": [r[0] for r in REGIONS],
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
            "page": (
                "fixture VM, not a live bake. Numbers (VHSI 18.4, A/H 28.4%, "
                "Growth-scare) are the packet exemplars, not tonight's tape. "
                "Strip tiles use DISTINCT per-kind fixture values (peg negative, "
                "yuan-quote negative, overnight rate as points-only)."
            ),
        },
        "pages": pages,
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (OUT_DIR / "EVIDENCE.yml").write_text(
        "schema: mastermind.page_evidence_receipt.v1\n"
        "changed_paths:\n"
        "  - templates/hk.html.j2\n"
        "manifest: mockups/evidence/hk-tier1-shell/manifest.json\n",
        encoding="utf-8",
    )
    keep = {s["file"] for p in pages for s in p["states"] if s.get("file")}
    for png in OUT_DIR.glob("*.png"):
        if png.name not in keep:
            png.unlink()
    _write_readme(outcome, captured, attempted, crop_list, fixture=True)
    print(f"wrote {captured}/{attempted} cells -> {OUT_DIR}", flush=True)
    return 0 if outcome == "captured" else 1


def _write_failure_readme(reason: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "README.md").write_text(
        "# HK Tier-1 shell evidence — capture unavailable\n\n"
        f"Playwright/Chromium did not run: `{reason}`.\n\n"
        "Closest honest substitute: the fixture HTML is what "
        "`tests/test_hk_tier1_shell.py` renders (producer-pinned copy, "
        "not tonight's tape). Re-run "
        "`python3 scripts/capture_hk_tier1_shell.py` once Chromium is "
        "installed (`python3 -m playwright install chromium`).\n",
        encoding="utf-8",
    )


def _write_readme(outcome: str, captured: int, attempted: int,
                  crop_list: list[str], *, fixture: bool) -> None:
    lines = [
        "# HK Tier-1 shell — visual evidence (H2)",
        "",
        f"Outcome: **{outcome}** ({captured}/{attempted} cells).",
        "",
        "Crops are Playwright element screenshots of a `templates/hk.html.j2` "
        "render with the packet's fixture VM (Growth-scare, VHSI 32nd / "
        "mid-range, A/H 28.4% about average, DISTINCT per-tile strip values: "
        "peg negative / yuan-quote negative / overnight rate as points-only). "
        "Not a live `site/hk.html` bake — this worktree is sparse "
        "(`data/` and `site/` omitted).",
        "",
        "Matrix: dark + light × EN + ZH × desktop 1440 × mobile 390, for "
        "the hero (`#hkx-hero-card`), the cross-market strip "
        "(`.hkx-cas-strip`), and one What To Do signal row "
        "(`.hkx-rack2 .hkx-row`) showing the monoline icons.",
        "",
        "Harness note (M3): `window.setTheme()` fires `skyToggleFx()` — a "
        "~1100ms crescent-moon (dark) / sun (light) overlay at z-index "
        "2147483600. That flourish is toggle chrome, not page content. The "
        "r1 390-dark strip crop caught it mid-animation. Capture now sets "
        "`prefers-reduced-motion: reduce` (the flourish's own skip) and "
        "strips leftover `.sky-fx` nodes before shooting. Page CSS z-index "
        "is unchanged.",
        "",
        "## Crops",
        "",
    ]
    lines.extend(f"- `{line}`" for line in crop_list)
    lines.append("")
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
