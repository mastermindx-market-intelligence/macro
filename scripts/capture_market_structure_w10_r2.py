#!/usr/bin/env python3
"""W10 r2 evidence crops for market_structure (6 cells: 3 subjects × dark/light EN).

S1 rig: fixture-rendered template, real `body.page-msp` class, seeds
`window.__skyDeck` before setTheme, strips `.sky-fx` / hides `.aurora` and the
theme FAB (disclosed), overlay probe per crop.

Usage::

    python3 -m scripts.capture_market_structure_w10_r2
"""
from __future__ import annotations

import hashlib
import json
import shutil
import struct
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from scripts.build_market_structure_page import render  # noqa: E402

REPO_ROOT = _ROOT
TEMPLATES_DIR = REPO_ROOT / "templates"
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "market_structure_latest.json"
OUT_DIR = REPO_ROOT / "mockups" / "evidence" / "market-structure-w10-r2"
CELLS_DIR = OUT_DIR / "cells"

_STATE_SEED_SCRIPT = """
(state) => {
  window.__skyDeck = true;
  try {
    localStorage.setItem('theme', state.theme);
    localStorage.removeItem('themeAuto');
    localStorage.setItem('lang', state.locale);
  } catch (e) {}
}
"""

_APPLY_STATE_SCRIPT = """
(state) => {
  window.__skyDeck = true;
  document.querySelectorAll('.sky-fx').forEach(function (el) { el.remove(); });
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
  document.querySelectorAll('.sky-fx').forEach(function (el) { el.remove(); });
  // Disclosed hides: page aurora bloom + theme FAB so the crop is the chip,
  // not a decorative overlay. Live visitors still see both.
  ['.aurora', '.mx5-aurora', '.theme-fab', '#themeFab', 'button.theme-toggle'].forEach(function (sel) {
    document.querySelectorAll(sel).forEach(function (el) { el.style.display = 'none'; });
  });
  return {
    theme: docEl.getAttribute('data-theme'),
    locale: docEl.getAttribute('data-lang'),
    bodyClass: document.body.className
  };
}
"""

_OVERLAY_PROBE = """
() => {
  const sels = ['.aurora', '.sky-fx', '.mx5-aurora', '.theme-fab', '#themeFab',
                'span.disc', '.sky-toggle'];
  const hits = [];
  sels.forEach(function (sel) {
    document.querySelectorAll(sel).forEach(function (el) {
      const st = getComputedStyle(el);
      if (st.display === 'none' || st.visibility === 'hidden' || Number(st.opacity) === 0) return;
      const r = el.getBoundingClientRect();
      if (r.width < 1 || r.height < 1) return;
      hits.push({sel: sel, w: Math.round(r.width), h: Math.round(r.height),
                 top: Math.round(r.top), left: Math.round(r.left),
                 display: st.display});
    });
  });
  return hits;
}
"""


def content_address_png(png: bytes, output_dir: Path) -> tuple[str, str, int, int]:
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


def _load_raw() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _write_stub(scratch: Path, name: str, raw: dict) -> Path:
    path = scratch / name
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def write_fixture_site(scratch: Path) -> None:
    scratch.mkdir(parents=True, exist_ok=True)
    for name in ("theme.css", "navigation-refresh.css", "theme.js",
                 "logo_config.js", "nav_market.js", "product-nav-icons.css"):
        src = TEMPLATES_DIR / name
        if src.exists():
            shutil.copy(src, scratch / name)
    fonts_src = TEMPLATES_DIR / "fonts"
    if fonts_src.exists():
        shutil.copytree(fonts_src, scratch / "fonts", dirs_exist_ok=True)

    from engine.market_structure_context import diff_changes

    raw_changed = _load_raw()
    items = diff_changes({"gamma_regime": "long"}, {"gamma_regime": "short"})
    raw_changed["state_changes"] = {"vs_asof": "2026-09-08", "items": items}
    stub_changed = _write_stub(scratch, "changed.json", raw_changed)
    (scratch / "changed.html").write_text(
        render(REPO_ROOT, fixture=stub_changed), encoding="utf-8")

    raw_empty = _load_raw()
    raw_empty["state_changes"] = {
        "vs_asof": "2026-09-08",
        "items": [{
            "key": "gamma_regime", "from": "long", "to": "short",
            "note_en": None, "note_zh": None,
        }],
    }
    stub_empty = _write_stub(scratch, "empty.json", raw_empty)
    (scratch / "empty.html").write_text(
        render(REPO_ROOT, fixture=stub_empty), encoding="utf-8")

    raw_flat = _load_raw()
    raw_flat["systematic"]["cta"]["flow_5d"] = 0.129
    raw_flat["systematic"]["cta"]["state"] = "adding"
    raw_flat["systematic"]["cta"]["cta_near_flat"] = True
    stub_flat = _write_stub(scratch, "nearflat.json", raw_flat)
    (scratch / "nearflat.html").write_text(
        render(REPO_ROOT, fixture=stub_flat), encoding="utf-8")


def _git_head() -> str | None:
    try:
        from scripts.capture_page_evidence import _git_head_sha
        head = _git_head_sha(REPO_ROOT)
        return head.sha
    except Exception:
        return None


def _shot(page, locator) -> bytes:
    locator.first.wait_for(state="visible", timeout=5000)
    locator.first.scroll_into_view_if_needed()
    page.wait_for_timeout(80)
    return locator.first.screenshot(type="png")


def _record(png: bytes, alias: str, extra: dict) -> dict:
    name, digest, pw, ph = content_address_png(png, CELLS_DIR)
    (CELLS_DIR / alias).write_bytes(png)
    extra.update({
        "captured": True, "file": name, "alias": alias, "sha256": digest,
        "bytes": len(png), "width": pw, "height": ph,
    })
    return extra


def main() -> int:
    from scripts.capture_page_evidence import CaptureUnavailable, serve_site_dir

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        print(f"capture unavailable: playwright missing ({exc})", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)

    scratch = Path(tempfile.mkdtemp(prefix="mstruct-ev-"))
    write_fixture_site(scratch)
    httpd, port = serve_site_dir(scratch)
    base = f"http://127.0.0.1:{port}"
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    crops: list[dict] = []
    aliases: dict[str, str] = {}
    overlays: dict[str, list] = {}

    subjects = (
        ("changed", "changed.html", ".sc-strip",
         "revived change strip with a real labelled chip"),
        ("empty", "empty.html", ".sc-chip.empty",
         ".sc-chip.empty designed hole"),
        ("near-flat", "nearflat.html", ".rc.adding.near-flat",
         "CTA .near-flat chip"),
    )

    try:
        manager = sync_playwright().start()
        try:
            browser = manager.chromium.launch(headless=True)
        except Exception as exc:
            manager.stop()
            raise CaptureUnavailable(f"no chromium binary: {exc}") from exc
        try:
            for subject, html_name, selector, _label in subjects:
                for theme in ("dark", "light"):
                    state = {"theme": theme, "locale": "en"}
                    ctx = browser.new_context(
                        viewport={"width": 1440, "height": 900},
                        locale="en-US", color_scheme=theme, device_scale_factor=1)
                    ctx.add_init_script(
                        f"({_STATE_SEED_SCRIPT.strip()})({json.dumps(state)})")
                    page = ctx.new_page()
                    entry = {
                        "viewport": "desktop", "locale": "en", "theme": theme,
                        "access": "anonymous", "viewport_width": 1440,
                        "viewport_height": 900, "force_state": subject,
                        "subject": subject,
                    }
                    try:
                        resp = page.goto(f"{base}/{html_name}",
                                         wait_until="load", timeout=30000)
                        if resp is None or not resp.ok:
                            raise RuntimeError(f"HTTP {getattr(resp, 'status', None)}")
                        applied = page.evaluate(_APPLY_STATE_SCRIPT.strip(), state) or {}
                        if applied.get("theme") != theme or applied.get("locale") != "en":
                            raise RuntimeError(
                                f"state mismatch requested {state} observed {applied}")
                        if "page-msp" not in (applied.get("bodyClass") or ""):
                            raise RuntimeError(
                                f"missing real body class page-msp: {applied.get('bodyClass')!r}")
                        page.wait_for_timeout(150)
                        overlay = page.evaluate(_OVERLAY_PROBE.strip()) or []
                        overlays[f"{subject}-{theme}"] = overlay
                        loc = page.locator(selector)
                        if subject == "near-flat":
                            # Crop the containing panel so the muted chip sits in context.
                            loc = page.locator(".panel", has=page.locator(selector))
                        png = _shot(page, loc)
                        alias = f"crop-{subject}-{theme}-en.png"
                        entry = _record(png, alias, entry)
                        entry["applied_theme"] = applied.get("theme")
                        entry["applied_locale"] = applied.get("locale")
                        entry["body_class"] = applied.get("bodyClass")
                        entry["overlay"] = overlay
                        aliases[alias] = entry["file"]
                    except Exception as exc:
                        entry.update({"captured": False,
                                      "reason": f"{type(exc).__name__}: {exc}"})
                    finally:
                        ctx.close()
                    crops.append(entry)
                    print(f"  crop {subject}/{theme}: "
                          f"{'ok' if entry.get('captured') else entry.get('reason')}",
                          flush=True)
        finally:
            browser.close()
            manager.stop()
    finally:
        httpd.shutdown()
        shutil.rmtree(scratch, ignore_errors=True)

    ok = sum(1 for c in crops if c.get("captured"))
    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": generated_at,
        "tool": "scripts/capture_market_structure_w10_r2.py",
        "target": "market_structure.html",
        "head": _git_head(),
        "axes": {
            "viewports": {"desktop": [1440, 900]},
            "locales": ["en"],
            "themes": ["dark", "light"],
            "access": ["anonymous"],
            "subjects": ["changed", "empty", "near-flat"],
        },
        "aliases": aliases,
        "outcome": "captured" if ok == 6 else "partial",
        "totals": {"crops": ok, "crops_required": 6},
        "honesty": {
            "access": "anonymous only",
            "page": (
                "templates/market_structure.html.j2 rendered against the committed "
                "fixture (tests/fixtures/market_structure_latest.json) with three "
                "synthetic overlays: producer long→short note, empty-note hole, "
                "cta_near_flat=true. No live data/ bake. Decorative layers "
                "(.aurora, .sky-fx, theme FAB) hidden with disclosure; "
                "window.__skyDeck seeded so setTheme does not photograph the "
                "sun/moon disc."
            ),
            "overlays": overlays,
        },
        "crops": crops,
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def overlay_cell(key: str) -> str:
        hits = overlays.get(key) or []
        if not hits:
            return "none (aurora/sky-fx/FAB hidden)"
        return "VISIBLE " + ", ".join(h.get("sel", "?") for h in hits)

    rows = []
    for subject, _html, _sel, label in subjects:
        for theme in ("dark", "light"):
            key = f"{subject}-{theme}"
            alias = f"crop-{subject}-{theme}-en.png"
            captured = any(c.get("alias") == alias and c.get("captured") for c in crops)
            rows.append(
                f"| `{alias}` | {label} | {theme} | EN | "
                f"{'yes' if captured else 'NO'} | {overlay_cell(key)} |"
            )

    readme = f"""# Market Structure — W10 r2 evidence (6 crops)

Fixture-rendered `templates/market_structure.html.j2` (no live `data/` bake).
Playwright seeds `localStorage` (`theme`, `lang`, clears `themeAuto`), sets
`window.__skyDeck = true` (bows out of theme.js `skyToggleFx` sun/moon
flourish), calls `setTheme`/`setLang`, re-reads `html[data-theme]` /
`html[data-lang]`, and refuses a cell on mismatch. Fixture HTML carries the
real `body.page-msp` class. Any leftover `.sky-fx` node is removed before
the shot; `.aurora` and the theme FAB are hidden (disclosed below).

Full 16-cell matrix (dark/light × EN/ZH × 1440/390) stays r4.

## DARK TREATMENT

Command center: luminance depth, instrument glass, restrained colour wash.
`.sc-chip.changed` sits on a 12% blue wash against graphite; `.sc-chip.empty`
is a dashed hairline on transparent graphite, no blue, no glow — a designed
hole, not a highlighted blank. `.rc.adding.near-flat` drops the full green
to a 5% wash and muted ink so a grazing CTA add cannot impersonate VC's
real +$11.8B move.

## LIGHT TREATMENT

Research workspace: cool canvas, white material, hairline discipline, shadow
instead of glow. `.sc-chip.empty` uses `--bg` (the canvas, not the white
card `--panel`) so the dashed hole reads as paper-on-desk, not a second
card nested on a card. `.near-flat` in light is a paper chip: canvas fill,
cool up/dn hairline mix, 8% ink shadow, muted ink — never the dark bloom
transplanted onto white, and never "tokens already split the two art
directions."

## Intentional differences

| Mechanism | Dark | Light |
|---|---|---|
| Empty chip ground | transparent on graphite | `--bg` canvas, no card wash |
| Near-flat fill | 5% up/dn wash | canvas `--bg` + 8% ink shadow |
| Near-flat border | faded up/dn mix on graphite | same mix against light hairline |
| Changed chip | 12% blue wash (unchanged) | token `--blue` on white (unchanged) |

## Crops

| File | Subject | Theme | Lang | Captured | Overlay |
|---|---|---|---|---|---|
{chr(10).join(rows)}

## Disclosed hides

- `window.__skyDeck = true` before `setTheme` so the ~1100ms sun/moon disc
  is never photographed.
- `.sky-fx` nodes removed if any survived.
- `.aurora` (page bloom) and the theme FAB set `display:none` for these
  crops so the chip is the subject. Live visitors still see both.

## Honest differences vs live

- Fixture VM, not the VPS bake.
- Shared site nav renders; some nav JS 404s are expected.
- Three synthetic overlays on the committed fixture (producer long→short
  note, empty-note hole, `cta_near_flat=true`).
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    print(f"wrote {ok}/6 crops → {OUT_DIR}", flush=True)
    return 0 if ok == 6 else 1


if __name__ == "__main__":
    raise SystemExit(main())
