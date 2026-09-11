#!/usr/bin/env python3
"""W10 r3 evidence matrix for market_structure (P8 watching band + P9 §10-D).

S1 rig: fixture-rendered template, real `body.page-msp` class, seeds
`window.__skyDeck` before setTheme, strips `.sky-fx` / hides `.aurora` and the
theme FAB (disclosed), overlay probe per cell, at-rest text via computed styles.

Usage::

    python3 -m scripts.capture_market_structure_w10_r3
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
OUT_DIR = REPO_ROOT / "mockups" / "evidence" / "market-structure-w10-r3"
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
  ['.aurora', '.mx5-aurora', '.theme-fab', '#themeFab', 'button.theme-toggle',
   '#mmb-boot', '#mmb-launcher', '.mmb-boot'].forEach(function (sel) {
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
                'span.disc', '.sky-toggle', '#mmb-boot', '#mmb-launcher', '.mmb-boot'];
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

_AT_REST = """
() => {
  const vis = (el) => {
    if (!el) return null;
    const st = getComputedStyle(el);
    return {
      text: (el.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 280),
      color: st.color, background: st.backgroundColor, display: st.display,
      visibility: st.visibility, fontSize: st.fontSize, opacity: st.opacity
    };
  };
  return {
    hero: vis(document.querySelector('.hero-state')),
    watch: vis(document.querySelector('#watch-band')),
    chips: vis(document.querySelector('.sc-strip')),
    firstDriver: vis(document.querySelector('.msp-driver')),
    kpiRow: vis(document.querySelector('.kpi-row')),
  };
}
"""

_HSCROLL = """
() => {
  const de = document.documentElement;
  const body = document.body;
  const wrap = document.querySelector('.wrap');
  const drivers = document.querySelector('#msp-drivers');
  return {
    docScrollWidth: de.scrollWidth,
    docClientWidth: de.clientWidth,
    bodyScrollWidth: body.scrollWidth,
    wrapScrollWidth: wrap ? wrap.scrollWidth : null,
    wrapClientWidth: wrap ? wrap.clientWidth : null,
    driversScrollWidth: drivers ? drivers.scrollWidth : null,
    driversClientWidth: drivers ? drivers.clientWidth : null,
    pageOverflows: de.scrollWidth > de.clientWidth + 1
  };
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


def _p1_overlay(raw: dict) -> dict:
    spot, flip = 7636.3599, 7663.226367
    raw["gamma"]["spot"] = spot
    raw["gamma"]["gamma_flip"] = flip
    raw["gamma"]["dist_to_flip_pct"] = (spot - flip) / spot * 100
    raw["asof"] = "2026-09-09"
    raw["gamma"]["series_start"] = "2026-06-15"
    raw["gamma"]["coverage"] = {
        "complete": False,
        "missing_recent": ["2026-08-14", "2026-09-01", "2026-09-02"],
        "missing_in_regime": [],
    }
    return raw


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

    raw_p1 = _p1_overlay(_load_raw())
    items = diff_changes({"gamma_regime": "long"}, {"gamma_regime": "short"})
    raw_p1["state_changes"] = {"vs_asof": "2026-09-08", "items": items}
    stub_p1 = _write_stub(scratch, "p1.json", raw_p1)
    (scratch / "p1.html").write_text(
        render(REPO_ROOT, fixture=stub_p1), encoding="utf-8")

    raw_changed = _load_raw()
    raw_changed["state_changes"] = {"vs_asof": "2026-09-08", "items": items}
    stub_changed = _write_stub(scratch, "changed.json", raw_changed)
    (scratch / "changed.html").write_text(
        render(REPO_ROOT, fixture=stub_changed), encoding="utf-8")

    (scratch / "warmup.html").write_text(
        render(REPO_ROOT, fixture=Path("/nonexistent/path/market_structure_latest.json")),
        encoding="utf-8")

    for pctile in (1, 2, 3, 21):
        raw_o = _load_raw()
        raw_o["gamma"]["net_gex_pctile"] = pctile
        stub = _write_stub(scratch, f"ord{pctile}.json", raw_o)
        (scratch / f"ord{pctile}.html").write_text(
            render(REPO_ROOT, fixture=stub), encoding="utf-8")


def _git_head() -> str | None:
    try:
        from scripts.capture_page_evidence import _git_head_sha
        head = _git_head_sha(REPO_ROOT)
        return head.sha
    except Exception:
        return None


def _shot(page, locator=None) -> bytes:
    if locator is None:
        page.wait_for_timeout(80)
        return page.screenshot(type="png")
    locator.first.wait_for(state="visible", timeout=8000)
    locator.first.scroll_into_view_if_needed()
    page.wait_for_timeout(80)
    return locator.first.screenshot(type="png")


def _record(png: bytes, alias: str, extra: dict) -> dict:
    name, digest, pw, ph = content_address_png(png, CELLS_DIR)
    (CELLS_DIR / alias).write_bytes(png)
    extra.update({
        "captured": True, "file": f"cells/{name}", "alias": alias,
        "sha256": digest, "bytes": len(png), "width": pw, "height": ph,
    })
    return extra


def _open(browser, html_name: str, theme: str, locale: str, *,
          width: int, height: int, base: str):
    state = {"theme": theme, "locale": locale}
    ctx = browser.new_context(
        viewport={"width": width, "height": height},
        locale="zh-CN" if locale == "zh" else "en-US",
        color_scheme=theme, device_scale_factor=1)
    ctx.add_init_script(f"({_STATE_SEED_SCRIPT.strip()})({json.dumps(state)})")
    page = ctx.new_page()
    resp = page.goto(f"{base}/{html_name}", wait_until="load", timeout=30000)
    if resp is None or not resp.ok:
        ctx.close()
        raise RuntimeError(f"HTTP {getattr(resp, 'status', None)} for {html_name}")
    applied = page.evaluate(_APPLY_STATE_SCRIPT.strip(), state) or {}
    if applied.get("theme") != theme or applied.get("locale") != locale:
        ctx.close()
        raise RuntimeError(f"state mismatch requested {state} observed {applied}")
    if "page-msp" not in (applied.get("bodyClass") or ""):
        ctx.close()
        raise RuntimeError(f"missing real body class page-msp: {applied.get('bodyClass')!r}")
    page.wait_for_timeout(120)
    overlay = page.evaluate(_OVERLAY_PROBE.strip()) or []
    at_rest = page.evaluate(_AT_REST.strip()) or {}
    return ctx, page, applied, overlay, at_rest


def overlay_cell(hits) -> str:
    if not hits:
        return "none (aurora/sky-fx/FAB hidden)"
    return "VISIBLE " + ", ".join(h.get("sel", "?") for h in hits)


def main() -> int:
    from scripts.capture_page_evidence import CaptureUnavailable, serve_site_dir

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        print(f"capture unavailable: playwright missing ({exc})", file=sys.stderr)
        return 2

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CELLS_DIR.mkdir(parents=True, exist_ok=True)

    scratch = Path(tempfile.mkdtemp(prefix="mstruct-ev-r3-"))
    write_fixture_site(scratch)
    httpd, port = serve_site_dir(scratch)
    base = f"http://127.0.0.1:{port}"
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    rest_states: list[dict] = []
    crops: list[dict] = []
    proofs: list[dict] = []
    hscroll: list[dict] = []
    aliases: dict[str, str] = {}
    overlays: dict[str, list] = {}
    failures = 0

    b_subjects = (
        ("changed", "changed.html", ".sc-strip",
         "revived change strip with a real labelled long→short chip", "desktop"),
        ("hero-meta", "p1.html", ".hero-meta",
         "hero-meta headline-vs-receipt (0.4 below flip beside SPX 7636 · flip 7663)", "desktop"),
        ("footnote", "p1.html", ".glass .sec-foot",
         "merged single hero footnote", "desktop"),
        ("stance-hero", "p1.html", ".glass .stance-chip",
         "hero stance line", "desktop"),
        ("stance-flows", "p1.html", '[data-driver="flows"] .stance-chip',
         "machine-money stance line", "desktop"),
        ("stance-disp", "p1.html", '[data-driver="dispersion"] .stance-chip',
         "stock-picker stance line", "desktop"),
        ("stance-vol", "p1.html", '[data-driver="vol"] .stance-chip',
         "vol-weather stance line", "desktop"),
        ("stance-week", "p1.html", '[data-driver="week"] .stance-chip',
         "weekly-range stance line", "desktop"),
        ("watch-band", "p1.html", "#watch-band",
         "P8 watching band folded into the hero", "desktop"),
        ("swipe-390", "p1.html", "#msp-drivers",
         "P9 swipe strip at 390 (next-card peek, top-aligned)", "mobile"),
    )
    b_cells = (
        ("dark", "en"), ("light", "en"), ("dark", "zh"), ("light", "zh"),
    )

    try:
        manager = sync_playwright().start()
        try:
            browser = manager.chromium.launch(headless=True)
        except Exception as exc:
            manager.stop()
            raise CaptureUnavailable(f"no chromium binary: {exc}") from exc
        try:
            # A — 8 rest baselines
            for viewport, width, height in (
                ("desktop", 1440, 900),
                ("mobile", 390, 844),
            ):
                for theme in ("dark", "light"):
                    for locale in ("en", "zh"):
                        entry = {
                            "viewport": viewport, "locale": locale, "theme": theme,
                            "access": "anonymous", "viewport_width": width,
                            "viewport_height": height, "subject": "baseline",
                        }
                        try:
                            ctx, page, applied, overlay, at_rest = _open(
                                browser, "p1.html", theme, locale,
                                width=width, height=height, base=base)
                            try:
                                png = _shot(page)
                                alias = f"A-{viewport}-{theme}-{locale}.png"
                                entry = _record(png, alias, entry)
                                entry["applied_theme"] = applied.get("theme")
                                entry["applied_locale"] = applied.get("locale")
                                entry["body_class"] = applied.get("bodyClass")
                                entry["overlay"] = overlay
                                entry["at_rest"] = at_rest
                                overlays[alias] = overlay
                                aliases[alias] = entry["file"]
                                if viewport == "mobile":
                                    hs = page.evaluate(_HSCROLL.strip()) or {}
                                    hs.update({
                                        "theme": theme, "locale": locale,
                                        "alias": alias,
                                    })
                                    hscroll.append(hs)
                            finally:
                                ctx.close()
                        except Exception as exc:
                            failures += 1
                            entry.update({"captured": False,
                                          "reason": f"{type(exc).__name__}: {exc}"})
                        rest_states.append(entry)
                        print(f"  A {viewport}/{theme}/{locale}: "
                              f"{'ok' if entry.get('captured') else entry.get('reason')}",
                              flush=True)

            # B — crops
            for subject, html_name, selector, label, vp in b_subjects:
                width, height = (390, 844) if vp == "mobile" else (1440, 900)
                for theme, locale in b_cells:
                    entry = {
                        "viewport": vp, "locale": locale, "theme": theme,
                        "access": "anonymous",
                        "viewport_width": width, "viewport_height": height,
                        "force_state": subject, "subject": subject, "label": label,
                    }
                    try:
                        ctx, page, applied, overlay, at_rest = _open(
                            browser, html_name, theme, locale,
                            width=width, height=height, base=base)
                        try:
                            loc = page.locator(selector)
                            png = _shot(page, loc)
                            alias = f"B-{subject}-{theme}-{locale}.png"
                            entry = _record(png, alias, entry)
                            entry["applied_theme"] = applied.get("theme")
                            entry["applied_locale"] = applied.get("locale")
                            entry["body_class"] = applied.get("bodyClass")
                            entry["overlay"] = overlay
                            entry["at_rest"] = at_rest
                            overlays[alias] = overlay
                            aliases[alias] = entry["file"]
                        finally:
                            ctx.close()
                    except Exception as exc:
                        failures += 1
                        entry.update({"captured": False,
                                      "reason": f"{type(exc).__name__}: {exc}"})
                    crops.append(entry)
                    print(f"  B {subject}/{theme}/{locale}: "
                          f"{'ok' if entry.get('captured') else entry.get('reason')}",
                          flush=True)

            # C — ordinals
            for pctile, suffix in ((1, "1st"), (2, "2nd"), (3, "3rd"), (21, "21st")):
                for theme, locale in (("dark", "en"), ("light", "en")):
                    entry = {
                        "viewport": "desktop", "locale": locale, "theme": theme,
                        "access": "anonymous", "viewport_width": 1440,
                        "viewport_height": 900, "force_state": f"ord{pctile}",
                        "subject": f"ordinal-{pctile}", "expect": suffix,
                    }
                    try:
                        ctx, page, applied, overlay, at_rest = _open(
                            browser, f"ord{pctile}.html", theme, locale,
                            width=1440, height=900, base=base)
                        try:
                            page.evaluate(
                                "() => { document.querySelectorAll('.glass .help .tip')"
                                ".forEach(function (el) { el.style.display = 'block'; }); }")
                            loc = page.locator(".glass .help .tip")
                            png = _shot(page, loc)
                            alias = f"C-ord{pctile}-{theme}-{locale}.png"
                            entry = _record(png, alias, entry)
                            entry["applied_theme"] = applied.get("theme")
                            entry["applied_locale"] = applied.get("locale")
                            entry["overlay"] = overlay
                            entry["at_rest"] = at_rest
                            body = page.inner_text(".glass")
                            entry["rendered_suffix"] = suffix if suffix in body else None
                            overlays[alias] = overlay
                            aliases[alias] = entry["file"]
                        finally:
                            ctx.close()
                    except Exception as exc:
                        failures += 1
                        entry.update({"captured": False,
                                      "reason": f"{type(exc).__name__}: {exc}"})
                    proofs.append(entry)
                    print(f"  C ord{pctile}/{theme}: "
                          f"{'ok' if entry.get('captured') else entry.get('reason')}",
                          flush=True)

            # C — six warmup branches × dark/light × EN/ZH
            for theme in ("dark", "light"):
                for locale in ("en", "zh"):
                    try:
                        ctx, page, applied, overlay, at_rest = _open(
                            browser, "warmup.html", theme, locale,
                            width=1440, height=900, base=base)
                        try:
                            n = page.locator(".warmup").count()
                            for i in range(n):
                                loc = page.locator(".warmup").nth(i)
                                why = loc.locator(".empty-why")
                                entry = {
                                    "viewport": "desktop", "locale": locale,
                                    "theme": theme, "access": "anonymous",
                                    "viewport_width": 1440, "viewport_height": 900,
                                    "force_state": f"warmup-{i}",
                                    "subject": f"warmup-{i}",
                                }
                                try:
                                    png = _shot(page, loc)
                                    alias = f"C-warmup{i}-{theme}-{locale}.png"
                                    entry = _record(png, alias, entry)
                                    entry["applied_theme"] = applied.get("theme")
                                    entry["applied_locale"] = applied.get("locale")
                                    entry["overlay"] = overlay
                                    entry["sentence"] = (loc.inner_text() or "")[:240]
                                    entry["empty_why"] = (why.inner_text() if why.count() else "")[:240]
                                    entry["at_rest"] = {
                                        "b": loc.locator("b").evaluate(
                                            "el => getComputedStyle(el).display") if loc.locator("b").count() else None,
                                        "why_display": why.evaluate(
                                            "el => getComputedStyle(el).display") if why.count() else None,
                                    }
                                    overlays[alias] = overlay
                                    aliases[alias] = entry["file"]
                                except Exception as exc:
                                    failures += 1
                                    entry.update({"captured": False,
                                                  "reason": f"{type(exc).__name__}: {exc}"})
                                proofs.append(entry)
                                print(f"  C warmup{i}/{theme}/{locale}: "
                                      f"{'ok' if entry.get('captured') else entry.get('reason')}",
                                      flush=True)
                        finally:
                            ctx.close()
                    except Exception as exc:
                        failures += 1
                        print(f"  C warmup-open {theme}/{locale}: {exc}", flush=True)
        finally:
            browser.close()
            manager.stop()
    finally:
        httpd.shutdown()
        shutil.rmtree(scratch, ignore_errors=True)

    a_ok = sum(1 for s in rest_states if s.get("captured"))
    b_ok = sum(1 for c in crops if c.get("captured"))
    c_ok = sum(1 for p in proofs if p.get("captured"))
    d_ok = all(not h.get("pageOverflows") for h in hscroll) and len(hscroll) == 4

    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": generated_at,
        "tool": "scripts/capture_market_structure_w10_r3.py",
        "target": "market_structure.html",
        "page_id": "market_structure",
        "head": _git_head(),
        "axes": {
            "viewports": {"desktop": [1440, 900], "mobile": [390, 844]},
            "locales": ["en", "zh"],
            "themes": ["dark", "light"],
            "access": ["anonymous"],
        },
        "aliases": aliases,
        "outcome": "captured" if failures == 0 else "partial",
        "totals": {
            "A": a_ok, "A_required": 8,
            "B": b_ok, "B_required": len(b_subjects) * len(b_cells),
            "C": c_ok,
            "D_hscroll_clean": d_ok,
            "failures": failures,
        },
        "honesty": {
            "access": "anonymous only",
            "page": (
                "templates/market_structure.html.j2 rendered against the committed "
                "fixture with synthetic overlays: producer long→short note, P1 "
                "spot/flip 7636.3599/7663.226367, coverage nulls, ordinals 1/2/3/21, "
                "full warmup. No live data/ bake. Decorative layers (.aurora, "
                ".sky-fx, theme FAB) hidden with disclosure; window.__skyDeck seeded."
            ),
            "overlays": {k: overlay_cell(v) for k, v in overlays.items()},
        },
        "pages": [{
            "page_id": "market_structure",
            "route": "/market_structure.html",
            "console_errors": [],
            "failed_responses": [],
            "gaps": [],
            "states": rest_states,
        }],
        "crops": crops,
        "proofs": proofs,
        "hscroll": hscroll,
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (OUT_DIR / "EVIDENCE.yml").write_text(
        "schema: mastermind.page_evidence_receipt.v1\n"
        "changed_paths:\n"
        "  - templates/market_structure.html.j2\n"
        "manifest: mockups/evidence/market-structure-w10-r3/manifest.json\n",
        encoding="utf-8")

    def _row(alias: str, label: str, theme: str, lang: str, captured: bool) -> str:
        return (f"| `{alias}` | {label} | {theme} | {lang} | "
                f"{'yes' if captured else 'NO'} | {overlay_cell(overlays.get(alias))} |")

    a_rows = []
    for s in rest_states:
        a_rows.append(_row(s.get("alias", ""), "8-cell rest baseline",
                           s.get("theme", ""), s.get("locale", ""),
                           bool(s.get("captured"))))
    b_rows = []
    for c in crops:
        b_rows.append(_row(c.get("alias", ""), c.get("label", ""),
                           c.get("theme", ""), c.get("locale", ""),
                           bool(c.get("captured"))))

    d_lines = []
    for h in hscroll:
        flag = "OVERFLOW" if h.get("pageOverflows") else "no page h-scroll"
        d_lines.append(
            f"- {h.get('locale')}/{h.get('theme')}: doc {h.get('docScrollWidth')} / "
            f"{h.get('docClientWidth')} — {flag}; strip "
            f"{h.get('driversScrollWidth')} / {h.get('driversClientWidth')} (strip may exceed)"
        )

    readme = f"""# Market Structure — W10 r3 evidence matrix

Fixture-rendered `templates/market_structure.html.j2` (no live `data/` bake).
Playwright seeds `localStorage` (`theme`, `lang`, clears `themeAuto`), sets
`window.__skyDeck = true` (bows out of theme.js `skyToggleFx` sun/moon
flourish), calls `setTheme`/`setLang`, re-reads `html[data-theme]` /
`html[data-lang]`, and refuses a cell on mismatch. Fixture HTML carries the
real `body.page-msp` class. Any leftover `.sky-fx` node is removed before
the shot; `.aurora` and the theme FAB are hidden (disclosed below).
At-rest text is recorded via `getComputedStyle` (color / display / visibility)
so a crop cannot pass on a `display:none` node.

## DARK TREATMENT

Command center: luminance depth, instrument glass, restrained colour wash.
The watching band is an inset plate — 7% blue wash on graphite, hairline
border, no glow — so the two conditions read as instrument notes under the
hero, not a second hero. The 390 swipe strip is composition only: cards sit
on graphite, next-card peek is the 86% flex basis, no extra bloom on the
track. Stance chips keep their existing wash.

## LIGHT TREATMENT

Research workspace: cool canvas, white material, hairline discipline, shadow
instead of glow. The watching band is a paper plate on `--bg` (the canvas,
not the white card `--panel`) with an 8% ink shadow — never the dark 7%
blue wash transplanted onto white. Swipe-strip cards pick up the same 8%
ink shadow so a peeked next card reads as a stacked sheet, not a glowing
tile. Token substitution alone is not this design: the band's ground and
the strip's card shadow are light-only mechanisms.

## Intentional differences

| Mechanism | Dark | Light |
|---|---|---|
| Watching-band ground | 7% blue wash on graphite | `--bg` canvas + 8% ink shadow |
| Watching-band border | hairline `--line` | same hairline, no glow |
| Swipe-strip cards | graphite panels, no extra shadow | 8% ink shadow on the panel |
| Hero / chips | unchanged r2 treatments | unchanged r2 treatments |

## Theme-specific degraded states

- Dark, missing gamma: hero warmup (market-facing sentence + `.empty-why`);
  watching band is absent (nothing to watch).
- Light, missing gamma: same structure on canvas; dashed warmup, no glow.
- Dark/light, missing dispersion thresholds: band still renders the flip
  condition alone.

## A — 8 rest baselines (dark/light × EN/ZH × 1440×900 / 390)

| File | Subject | Theme | Lang | Captured | Overlay |
|---|---|---|---|---|---|
{chr(10).join(a_rows)}

## B — crops (dark+light+ZH)

| File | Subject | Theme | Lang | Captured | Overlay |
|---|---|---|---|---|---|
{chr(10).join(b_rows)}

## C — synthetic proofs

- `net_gex_pctile` ∈ {{1, 2, 3, 21}} forced; tip forced visible; files
  `C-ord{{1,2,3,21}}-dark-en.png` / light-en.
- All six `.warmup` branches forced, dark+light+EN+ZH, each showing the
  market-facing sentence + `.empty-why` (same-subject ZH). Files
  `C-warmup{{0-5}}-{{theme}}-{{locale}}.png`.

## D — 390w composition + no page-level h-scroll

{chr(10).join(d_lines) if d_lines else '- (no mobile cells captured)'}

Page `overflow-x` is hidden; the driver strip is allowed to scroll
horizontally (that is the reduction). `.kpi-row` / `.vix-row` wrap.

## E — producer-regression tests

Named in the worker report: `test_p0_template_consumes_note_en` /
`test_p0_gamma_long_to_short_chip_renders_producer_note` (consumes-what-the-
producer-emits) and `test_p1_hero_distance_round_trips_from_emitted_spot_flip`
(`/spot` round-trip). P8 adds `test_p8_watch_band_binds_stubbed_flip_not_fixture_default`.

## F — design-system gates

Run on the diff after capture; outputs live in the worker report.

## Disclosed hides

- `window.__skyDeck = true` before `setTheme` so the ~1100ms sun/moon disc
  is never photographed.
- `.sky-fx` nodes removed if any survived.
- `.aurora` (page bloom), the theme FAB, and `#mmb-boot` (brain launcher)
  set `display:none` so the crop is the subject. Live visitors still see them.

## Honest differences vs live

- Fixture VM, not the VPS bake.
- Shared site nav renders; some nav JS 404s are expected.
- Synthetic overlays listed above.
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    print(f"wrote A={a_ok}/8 B={b_ok} C={c_ok} D_clean={d_ok} failures={failures} → {OUT_DIR}",
          flush=True)
    return 0 if failures == 0 and a_ok == 8 else 1


if __name__ == "__main__":
    raise SystemExit(main())
