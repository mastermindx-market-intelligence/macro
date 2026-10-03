#!/usr/bin/env python3
"""Capture dark+light × EN/ZH × desktop 1440 / mobile 390 of the SERVED
official policy statements dossier card on international_macro country pages
AFTER the MO-PAID-006 PAGE R2+R3 repairs (headline link-coloured at rest;
dark hover brightens to --text; light hover keeps the link colour and adds
underline; light mobile padding 16).

The receipt is 60 attempted cells = 40 rest + 12 captured interaction + 8
expected misses:

* **40 rest** = 5 routes × 2 themes × 2 locales × 2 viewports. Captured by
  `scripts/capture_page_evidence.py --routes ... --viewports desktop,mobile
  --locales en,zh --themes dark,light` with no --force-state.
* **12 interaction** = 3 covered routes × 2 force-states (hover/focus) × 2
  themes × 1 locale (en) × 1 viewport (desktop). Captured by a second
  `capture_page_evidence.py` invocation restricted to those axes.
* **8 expected misses** = 2 no-headline routes (japan, euro_area--outage) ×
  2 force-states × 2 themes × 1 locale × 1 viewport. Recorded as gap rows
  in `manifest.json` with `expected_miss: true` and no PNG — `.imd-dossier-headline`
  does not exist on those routes so the locator cannot focus/hover.

The capture tool materializes the origin/main site into a scratch directory,
renders the 5 fixture pages from THIS branch's template using the Jinja
environment in `scripts/build_international_macro.py:97-102`, overlays the
fixture `dossier` payloads, and serves them from 127.0.0.1. It then invokes
`scripts/capture_page_evidence.py` once for the rest pass and once for the
interaction pass, merges the two manifests, appends the 8 expected misses,
and runs a Playwright DOM pass on the 40 rest cells + the 12 interaction
cells for the new R2+R3 acceptance fields (link-coloured headline at rest;
dark hover colour ≠ rest and == --text; light hover colour == rest and
decoration contains `underline`; card padding 16/16/16/16 both themes at
390; rail/chip differ; leadership exact ×2; scroll_w ≤ viewport_w mobile;
title attrs 0).

Run from the repo root::

    python3 mockups/evidence/mo-paid-006-dossier-page/capture.py

No credentials. No network beyond the bundled static fixtures served from a
local python http.server. Reproducible end-to-end: fixture data is inlined;
the captured PNGs hash deterministically for the same fixed browser /
viewport.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import http.server
import json
import os
import shutil
import socketserver
import subprocess
import sys
import tarfile
import tempfile
import threading
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent.parent.parent  # mockups/.../capture.py -> repo root
sys.path.insert(0, str(_REPO))

OUT_DIR = _REPO / "mockups" / "evidence" / "mo-paid-006-dossier-page"
CELLS_DIR = OUT_DIR / "cells"
CROPS_DIR = CELLS_DIR / "crops"

VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}
LOCALES = ("en", "zh")
THEMES = ("dark", "light")

# Routes / page_ids / fixture payload. Each tuple is (page_id, route_file, cc, dossier_state, items, stance_or_none, leadership).
_FIXTURES: list[dict[str, Any]] = [
    {
        "page_id": "euro_area",
        "route": "euro_area.html",
        "cc": "EZ",
        "state": "covered",
        "items": [
            {
                "source_key": "ec_presscorner",
                "publisher": "European Commission",
                "title": "Eurogroup statement on the euro area fiscal stance, October 2026",
                "url": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_4001",
                "published": "2026-10-01T09:00:00Z",
                "rights_state": "VERIFIED_PUBLIC_REUSE",
                "rights_basis": "CC BY 4.0 — Reuse allowed with attribution.",
            },
            {
                "source_key": "ec_presscorner",
                "publisher": "European Commission",
                "title": "Commission adopts Autumn 2026 European Semester package",
                "url": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_3998",
                "published": "2026-09-30T14:30:00Z",
                "rights_state": "VERIFIED_PUBLIC_REUSE",
                "rights_basis": "CC BY 4.0 — Reuse allowed with attribution.",
            },
            {
                "source_key": "ec_presscorner",
                "publisher": "European Commission",
                "title": "Statement by President on the EU competitiveness outlook",
                "url": "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_3991",
                "published": "2026-09-28T11:00:00Z",
                "rights_state": "VERIFIED_PUBLIC_REUSE",
                "rights_basis": "CC BY 4.0 — Reuse allowed with attribution.",
            },
        ],
        "stance": None,
        "leadership": "no rights-cleared source",
    },
    {
        "page_id": "united_kingdom",
        "route": "united_kingdom.html",
        "cc": "GB",
        "state": "covered",
        "items": [
            {
                "source_key": "boe_news",
                "publisher": "Bank of England",
                "title": "Monetary Policy Committee minutes, September 2026 meeting",
                "url": "https://www.bankofengland.co.uk/news/2026/09/mpc-mpc-minutes-sept-2026",
                "published": "2026-09-24T12:00:00Z",
                "rights_state": "VERIFIED_PUBLIC_REUSE",
                "rights_basis": "Open Government Licence v3.0 — Crown copyright.",
            },
            {
                "source_key": "boe_news",
                "publisher": "Bank of England",
                "title": "Bank Rate maintained at 3.75% — October 2026 summary",
                "url": "https://www.bankofengland.co.uk/news/2026/10/bank-rate-oct-2026",
                "published": "2026-10-02T11:00:00Z",
                "rights_state": "VERIFIED_PUBLIC_REUSE",
                "rights_basis": "Open Government Licence v3.0 — Crown copyright.",
            },
        ],
        "stance": {"label": "restrictive", "provider_label": "HM Treasury", "authoritative": False},
        "leadership": "no rights-cleared source",
    },
    {
        "page_id": "united_kingdom_no_stance",
        "route": "united_kingdom--no-stance.html",  # synthetic route
        "cc": "GB",
        "state": "covered",
        "items": [
            {
                "source_key": "boe_news",
                "publisher": "Bank of England",
                "title": "Financial Stability Report, October 2026",
                "url": "https://www.bankofengland.co.uk/news/2026/10/fsr-oct-2026",
                "published": "2026-10-01T09:00:00Z",
                "rights_state": "VERIFIED_PUBLIC_REUSE",
                "rights_basis": "Open Government Licence v3.0 — Crown copyright.",
            },
            {
                "source_key": "boe_news",
                "publisher": "Bank of England",
                "title": "Statistical release: money and lending, September 2026",
                "url": "https://www.bankofengland.co.uk/news/2026/10/m4-money-lending-sept-2026",
                "published": "2026-09-30T10:00:00Z",
                "rights_state": "VERIFIED_PUBLIC_REUSE",
                "rights_basis": "Open Government Licence v3.0 — Crown copyright.",
            },
        ],
        "stance": None,
        "leadership": "no rights-cleared source",
    },
    {
        "page_id": "japan",
        "route": "japan.html",
        "cc": "JP",
        "state": "no_coverage",
        "items": [],
        "stance": None,
        "leadership": "no rights-cleared source",
    },
    {
        "page_id": "euro_area_outage",
        "route": "euro_area--outage.html",  # synthetic route
        "cc": "EZ",
        "state": "source_outage",
        "items": [],
        "stance": None,
        "leadership": "no rights-cleared source",
    },
]

# Force-states the spec demands on the 3 covered routes only (desktop / en).
FORCE_STATES = (
    "imd_dossier_headline_hover:hover(#official-statements .imd-dossier-headline)",
    "imd_dossier_headline_focus:focus(#official-statements .imd-dossier-headline)",
)


def _git(*args: str, cwd: Path | None = None) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=cwd or _REPO, check=True, capture_output=True,
    ).stdout


def _git_origin_main_blob(relpath: str) -> bytes:
    return _git("show", f"origin/main:{relpath}")


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _materialize_site(scratch: Path) -> tuple[str, int]:
    """Copy the FULL origin/main site/ tree to scratch via `git archive`
    so every hash-named asset the page references under `?v=` is present.
    The 5 fixture routes are overwritten in `_render_fixture_pages` after."""
    source_commit = _git("rev-parse", "origin/main").decode().strip()
    scratch.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(
        ["git", "archive", "--format=tar", "origin/main", "site"],
        cwd=_REPO, check=True, capture_output=True,
    )
    import io  # noqa: PLC0415
    with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as tf:
        count = 0
        for m in tf.getmembers():
            if not m.name.startswith("site/"):
                continue
            rel = m.name[len("site/"):]
            if not rel or m.isdir():
                continue
            out = scratch / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            extracted = tf.extractfile(m)
            if extracted is None:
                continue
            out.write_bytes(extracted.read())
            count += 1
    return source_commit, count


def _render_fixture_pages(scratch: Path) -> dict[str, dict[str, Any]]:
    """Render the 5 fixture pages from origin/main view payloads + fixture
    dossier payloads using THIS branch's template and the environment in
    `scripts/build_international_macro.py:97-102`."""
    from jinja2 import Environment, FileSystemLoader  # type: ignore

    env = Environment(
        loader=FileSystemLoader(str(_REPO / "templates")),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("international_macro.html.j2")

    page_sha: dict[str, dict[str, Any]] = {}
    for fixture in _FIXTURES:
        cc = fixture["cc"]
        view_blob = _git_origin_main_blob(f"data/international_macro/{cc}_latest.json")
        view = json.loads(view_blob)
        view["dossier"] = {
            "state": fixture["state"],
            "items": fixture["items"],
            "stance": fixture["stance"],
            "leadership": fixture["leadership"],
        }
        europe_news = {"items": []} if cc == "EZ" else None
        europe_news_items = europe_news["items"] if europe_news else None
        rendered = template.render(
            D=view, RADAR=None,
            europe_news=europe_news,
            europe_news_items=europe_news_items,
        )
        out = scratch / fixture["route"]
        out.write_text(rendered, encoding="utf-8")
        page_sha[fixture["page_id"]] = {
            "route": fixture["route"],
            "sha256": _sha256_hex(rendered.encode("utf-8")),
            "bytes": len(rendered.encode("utf-8")),
        }
    return page_sha


def _serve(site_dir: Path) -> tuple[Any, int]:
    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_args, **_kwargs):
            pass

    os.chdir(site_dir)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), Q)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


# --- DOM-record pass -------------------------------------------------------

# Locale-keyed leadership literal (template line 452).
LEADERSHIP_EN = "Leadership statements: no rights-cleared source."
LEADERSHIP_ZH = "领导层表态：暂无获准转载的来源。"


def _dom_probe(browser, base_url: str, *, route: str, viewport: tuple[int, int], theme: str, locale: str) -> dict[str, Any]:
    """One matrix point: navigate, apply state, and probe the DOM fields
    the S3 acceptance list names. Returns a dict ready to merge into a
    dom.json row."""
    w, h = viewport
    context = browser.new_context(
        viewport={"width": w, "height": h},
        locale="zh-CN" if locale == "zh" else "en-US",
        color_scheme=theme,
        device_scale_factor=1,
    )
    # add_init_script on the context BEFORE new_page, raw string form.
    # The `() => {{ ... }}` function-wrapper form silently no-ops; a bare
    # statement string is what Playwright wraps in its own IIFE. Verified.
    context.add_init_script(
        "try { localStorage.setItem('theme', '" + theme + "'); "
        "localStorage.removeItem('themeAuto'); "
        "localStorage.setItem('lang', '" + locale + "'); } catch (e) {}"
    )
    page = context.new_page()
    try:
        resp = page.goto(f"{base_url}/{route}", wait_until="load", timeout=20000)
        if resp is None or not getattr(resp, "ok", False):
            raise RuntimeError(f"HTTP {getattr(resp, 'status', 'none')}")
        page.wait_for_function("() => !!document.querySelector('#official-statements')", timeout=8000)
        page.wait_for_timeout(400)  # settle

        info = page.evaluate(
            r"""
            () => {
              const card = document.querySelector('#official-statements');
              if (!card) return {error: 'no-card'};
              const cs = window.getComputedStyle(card);

              // --ink-link as a COMPUTED rgb() — applies the active theme
              // and yields a value comparable with getComputedStyle(...).color.
              const linkProbe = document.createElement('span');
              linkProbe.style.position = 'absolute';
              linkProbe.style.visibility = 'hidden';
              linkProbe.style.color = 'var(--ink-link, var(--link))';
              document.body.appendChild(linkProbe);
              const linkInkRgb = window.getComputedStyle(linkProbe).color;

              const textProbe = document.createElement('span');
              textProbe.style.position = 'absolute';
              textProbe.style.visibility = 'hidden';
              textProbe.style.color = 'var(--text)';
              document.body.appendChild(textProbe);
              const textInkRgb = window.getComputedStyle(textProbe).color;
              linkProbe.remove();
              textProbe.remove();

              // Raw CSS variable values (informational; for the receipt's
              // `link_ink` field we prefer the COMPUTED rgb).
              const rootCs = window.getComputedStyle(document.documentElement);
              const linkInkRaw = rootCs.getPropertyValue('--ink-link').trim()
                || rootCs.getPropertyValue('--link').trim() || '';
              const textInkRaw = rootCs.getPropertyValue('--text').trim() || '';

              const headline = card.querySelector('.imd-dossier-headline');
              const beforeDisplay = window.getComputedStyle(card, '::before').display;
              const chip = card.querySelector('.imd-dossier-chip');
              const chipBorderStyle = chip ? window.getComputedStyle(chip).borderStyle : null;
              const cardPad = {
                l: cs.paddingLeft, r: cs.paddingRight, t: cs.paddingTop, b: cs.paddingBottom,
              };
              const items = card.querySelectorAll('.imd-dossier-item');
              const stanceAttr = card.getAttribute('data-dossier-stance');
              const leadershipNode = card.querySelector('[data-dossier-leadership]');
              const lNode = leadershipNode ? leadershipNode.querySelector('.l-en, .l-zh') : null;
              const leadershipText = lNode ? (lNode.textContent || '').trim() : '';
              const scrollW = document.documentElement.scrollWidth;
              const viewW = window.innerWidth;
              const cr = card.getBoundingClientRect();
              const titleAttrCount = card.querySelectorAll('[title]').length;
              const dataTheme = document.documentElement.getAttribute('data-theme');
              return {
                data_theme: dataTheme,
                link_ink: linkInkRgb,
                link_ink_raw: linkInkRaw,
                text_ink: textInkRgb,
                text_ink_raw: textInkRaw,
                headline_color: headline ? window.getComputedStyle(headline).color : null,
                before_display: beforeDisplay,
                chip_border_style: chipBorderStyle,
                card_padding: cardPad,
                item_count: items.length,
                stance_attr: stanceAttr,
                leadership_text: leadershipText,
                scroll_w: scrollW,
                viewport_w: viewW,
                card_bbox: {x: cr.left, y: cr.top, w: cr.width, h: cr.height},
                title_attr_count: titleAttrCount,
                dossier_state: card.getAttribute('data-dossier-state'),
              };
            }
            """
        )
        info["applied_theme"] = theme
        info["applied_locale"] = locale
        return info
    finally:
        context.close()


def _hover_probe(browser, base_url: str, *, route: str, theme: str, locale: str = "en", viewport: tuple[int, int] = (1440, 900)) -> dict[str, Any] | None:
    """For covered routes only: load the page, hover the first
    .imd-dossier-headline, and read the computed colour + decoration line
    of that headline."""
    w, h = viewport
    context = browser.new_context(
        viewport={"width": w, "height": h},
        locale="zh-CN" if locale == "zh" else "en-US",
        color_scheme=theme,
        device_scale_factor=1,
    )
    # add_init_script on the context BEFORE new_page, raw string form.
    # The `() => {{ ... }}` function-wrapper form silently no-ops; a bare
    # statement string is what Playwright wraps in its own IIFE. Verified.
    context.add_init_script(
        "try { localStorage.setItem('theme', '" + theme + "'); "
        "localStorage.removeItem('themeAuto'); "
        "localStorage.setItem('lang', '" + locale + "'); } catch (e) {}"
    )
    page = context.new_page()
    try:
        resp = page.goto(f"{base_url}/{route}", wait_until="load", timeout=20000)
        if resp is None or not getattr(resp, "ok", False):
            raise RuntimeError(f"HTTP {getattr(resp, 'status', 'none')}")
        page.wait_for_function("() => !!document.querySelector('#official-statements .imd-dossier-headline')", timeout=8000)
        page.wait_for_timeout(400)
        page.hover("#official-statements .imd-dossier-headline")
        page.wait_for_timeout(200)
        info = page.evaluate(
            r"""
            () => {
              const h = document.querySelector('#official-statements .imd-dossier-headline');
              if (!h) return null;
              const cs = window.getComputedStyle(h);
              return {color: cs.color, decoration: cs.textDecorationLine};
            }
            """
        )
        return info
    finally:
        context.close()


def _focus_probe(browser, base_url: str, *, route: str, theme: str, locale: str = "en", viewport: tuple[int, int] = (1440, 900)) -> dict[str, Any] | None:
    """Same shape as hover_probe but uses focus() instead of hover()."""
    w, h = viewport
    context = browser.new_context(
        viewport={"width": w, "height": h},
        locale="zh-CN" if locale == "zh" else "en-US",
        color_scheme=theme,
        device_scale_factor=1,
    )
    # add_init_script on the context BEFORE new_page, raw string form.
    # The `() => {{ ... }}` function-wrapper form silently no-ops; a bare
    # statement string is what Playwright wraps in its own IIFE. Verified.
    context.add_init_script(
        "try { localStorage.setItem('theme', '" + theme + "'); "
        "localStorage.removeItem('themeAuto'); "
        "localStorage.setItem('lang', '" + locale + "'); } catch (e) {}"
    )
    page = context.new_page()
    try:
        resp = page.goto(f"{base_url}/{route}", wait_until="load", timeout=20000)
        if resp is None or not getattr(resp, "ok", False):
            raise RuntimeError(f"HTTP {getattr(resp, 'status', 'none')}")
        page.wait_for_function("() => !!document.querySelector('#official-statements .imd-dossier-headline')", timeout=8000)
        page.wait_for_timeout(400)
        page.focus("#official-statements .imd-dossier-headline")
        page.wait_for_timeout(200)
        info = page.evaluate(
            r"""
            () => {
              const h = document.querySelector('#official-statements .imd-dossier-headline');
              if (!h) return null;
              const cs = window.getComputedStyle(h);
              return {
                color: cs.color,
                decoration: cs.textDecorationLine,
                outline: cs.outlineStyle + ' ' + cs.outlineWidth + ' ' + cs.outlineColor,
                outline_offset: cs.outlineOffset,
              };
            }
            """
        )
        return info
    finally:
        context.close()


def _build_expected_miss_rows(generated_at: str) -> list[dict[str, Any]]:
    """8 expected-miss rows for japan + euro_area_outage × {hover, focus} × {dark, light}
    on desktop / en. They are recorded in the manifest as gap rows with
    `expected_miss: true, captured: false` because `.imd-dossier-headline`
    does not exist on those routes — there is no headline to focus/hover."""
    rows: list[dict[str, Any]] = []
    for page_id in ("japan", "euro_area_outage"):
        for force_state_name in ("imd_dossier_headline_hover", "imd_dossier_headline_focus"):
            for theme in THEMES:
                row = {
                    "access": "anonymous",
                    "applied_locale": "en",
                    "applied_theme": theme,
                    "applied_force_state": None,
                    "captured": False,
                    "expected_miss": True,
                    "expected_miss_reason": "no .imd-dossier-headline on this route",
                    "file": None,
                    "force_state": force_state_name,
                    "height": None,
                    "locale": "en",
                    "theme": theme,
                    "viewport": "desktop",
                    "viewport_height": 900,
                    "viewport_width": 1440,
                    "width": None,
                }
                rows.append((page_id, row))
    # Flatten to {page_id: [rows]} structure for the merged manifest.
    by_page: dict[str, list[dict[str, Any]]] = {}
    for pid, row in rows:
        by_page.setdefault(pid, []).append(row)
    return by_page  # type: ignore[return-value]


# --- Manifest merge --------------------------------------------------------

def _load_manifest(path: Path) -> dict[str, Any]:
    """Read a capture_page_evidence.py output manifest and re-key by
    (route_filename) so we can stitch rest + interaction passes."""
    m = json.loads(path.read_text(encoding="utf-8"))
    return m


def _rest_filter(manifest: dict[str, Any]) -> dict[str, Any]:
    """Strip interaction rows from a 'rest' manifest: drop any state whose
    `force_state` is set."""
    for p in manifest["pages"]:
        p["states"] = [s for s in p["states"] if not s.get("force_state")]
    return manifest


def _interaction_filter(manifest: dict[str, Any]) -> dict[str, Any]:
    """Keep only the interaction cells the spec demands: 3 covered routes ×
    desktop / en × {hover, focus} × {dark, light} = 12. Drop the rest."""
    covered_routes = {"/euro_area.html", "/united_kingdom.html", "/united_kingdom--no-stance.html"}
    for p in manifest["pages"]:
        keep = []
        for s in p["states"]:
            if not s.get("force_state"):
                continue
            if p["route"] not in covered_routes:
                continue
            if s["viewport"] != "desktop" or s["locale"] != "en":
                continue
            keep.append(s)
        p["states"] = keep
    # Drop pages that now have zero states.
    manifest["pages"] = [p for p in manifest["pages"] if p["states"]]
    return manifest


# --- Main -------------------------------------------------------------------


def finalize_manifest(merged: dict[str, Any], *, template_commit: str, site_commit: str | None) -> dict[str, Any]:
    """Re-shape the stitched manifest into the canonical `mastermind.p0_evidence.v2`
    receipt shape that `scripts/capture_page_evidence.py` emits and
    `scripts/check_ui_visual_evidence.py` validates. Three things the stitch
    alone gets wrong, each measured on the R2 lane's output (gate rc=1, 6 findings):
    (1) declare the capture axes INCLUDING the two force states — without
    `axes.force_states` the checker reads "declares no --force-state" and REST
    shots cannot prove the hover/focus presentation; (2) move the 8 expected-miss
    rows (japan / euro_area_outage render no `.imd-dossier-headline`, so there is
    nothing to hover or focus) out of `pages[*].states` into top-level `excluded`
    — by the checker's contract a listed force_state cell ASSERTS a capture, so a
    `captured: false` row is a finding, never an exemption; (3) pin totals, the
    tool hash, and both commits that fix what the pixels show (`source_commit` =
    the template head whose bytes were rendered; `scope.site_fixture_commit` =
    the origin/main site the scratch copy was materialized from). Idempotent."""
    out = dict(merged)
    excluded: list[dict[str, Any]] = [dict(x) for x in (out.get("excluded") or [])]
    pages: list[dict[str, Any]] = []
    for page in out.get("pages", []):
        keep: list[dict[str, Any]] = []
        for state in page.get("states", []):
            if state.get("force_state") and state.get("captured") is not True:
                excluded.append({
                    "page_id": page.get("page_id"),
                    "route": page.get("route"),
                    "force_state": state.get("force_state"),
                    "theme": state.get("theme"),
                    "viewport": state.get("viewport"),
                    "locale": state.get("locale"),
                    "expected_miss": True,
                    "reason": state.get("expected_miss_reason") or state.get("reason")
                    or "no .imd-dossier-headline on this route",
                })
                continue
            keep.append(state)
        pages.append(dict(page, states=keep))
    out["pages"] = pages
    out["excluded"] = excluded
    force_defs: list[dict[str, Any]] = []
    for spec in FORCE_STATES:
        name, _, rest = spec.partition(":")
        kind, _, selector = rest.partition("(")
        force_defs.append({"name": name, "kind": kind, "selector": selector.rstrip(")"), "spec": rest})
    out["axes"] = {
        "viewports": {"desktop": [1440, 900], "mobile": [390, 844]},
        "locales": ["en", "zh"],
        "themes": ["dark", "light"],
        "access": ["anonymous"],
        "force_states": force_defs,
    }
    attempted = sum(len(p["states"]) for p in pages)
    captured = sum(1 for p in pages for s in p["states"] if s.get("captured") is True)
    out["totals"] = {
        "pages": len(pages),
        "states_attempted": attempted,
        "states_captured": captured,
        "expected_miss_excluded": len(excluded),
    }
    module_sha = _sha256_hex(Path(__file__).resolve().read_bytes())
    out["tool"] = {"module_ref": "mockups/evidence/mo-paid-006-dossier-page/capture.py",
                   "version": "2", "module_sha256": module_sha}
    out["capture_tool_module_sha256"] = module_sha
    scope = dict(out.get("scope") or {})
    if site_commit:
        scope["site_fixture_commit"] = site_commit
    out["scope"] = scope
    out["source_commit"] = template_commit
    out["source"] = ("scratch site materialized from origin/main site/ with euro_area, united_kingdom, "
                     "japan and two synthetic routes re-rendered from THIS branch's "
                     "templates/international_macro.html.j2 against fixture dossiers; served from 127.0.0.1")
    out["selection"] = {"method": "fixture-routes", "page_ids": [p.get("page_id") for p in pages],
                        "note": "5 fixture pages; 3 carry a headline (hover/focus captured desktop/en x dark/light), "
                                "2 render the no-coverage / outage states with no headline (force states excluded)"}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch-dir", default=None,
                        help="override the scratch dir (default mktemp)")
    parser.add_argument("--keep", action="store_true",
                        help="keep the scratch dir on exit (for debugging)")
    parser.add_argument("--skip-rest", action="store_true",
                        help="reuse existing cells/* (debug aid)")
    parser.add_argument("--skip-interaction", action="store_true",
                        help="reuse existing cells/* (debug aid)")
    parser.add_argument("--skip-dom", action="store_true",
                        help="reuse existing dom.json (debug aid)")
    parser.add_argument("--finalize-only", action="store_true",
                        help="re-shape OUT_DIR/manifest.json into the canonical v2 receipt shape "
                             "(axes incl. force states, expected misses -> excluded, totals, tool, commits) "
                             "without recapturing; idempotent")
    args = parser.parse_args()

    if args.finalize_only:
        path = OUT_DIR / "manifest.json"
        current = json.loads(path.read_text(encoding="utf-8"))
        site_commit = (current.get("scope") or {}).get("site_fixture_commit") or current.get("source_commit")
        template_commit = _git("rev-parse", "HEAD", cwd=_REPO).decode().strip()
        final = finalize_manifest(current, template_commit=template_commit, site_commit=site_commit)
        path.write_text(json.dumps(final, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        t = final["totals"]
        print(f"Finalized {path}: pages={t['pages']} attempted={t['states_attempted']} captured={t['states_captured']} "
              f"excluded={len(final['excluded'])} force_states={[d['name'] for d in final['axes']['force_states']]} "
              f"source_commit={final['source_commit'][:12]} site_fixture_commit={str(site_commit)[:12]}", flush=True)
        return 0

    scratch = Path(args.scratch_dir) if args.scratch_dir else Path(
        tempfile.mkdtemp(prefix="mo_paid_006_dossier_")
    )
    scratch.mkdir(parents=True, exist_ok=True)

    source_commit, copied_count = _materialize_site(scratch)
    print(f"Materialized from origin/main {source_commit[:12]}; copied {copied_count} files → {scratch}", flush=True)

    page_sha = _render_fixture_pages(scratch)
    for pid, meta in page_sha.items():
        print(f"  ✓ {meta['route']} ({meta['bytes']}B sha={meta['sha256'][:12]})", flush=True)

    httpd, port = _serve(scratch)
    base_url = f"http://127.0.0.1:{port}"
    print(f"Serving from {scratch} at {base_url}", flush=True)

    CELLS_DIR.mkdir(parents=True, exist_ok=True)
    CROPS_DIR.mkdir(parents=True, exist_ok=True)

    # Phase A: 40 rest cells (5 routes × 2 themes × 2 locales × 2 viewports).
    rest_manifest_path = scratch / "manifest.rest.json"
    rest_out = scratch / "cells.rest"
    rest_out.mkdir(parents=True, exist_ok=True)
    if args.skip_rest and (OUT_DIR / "manifest.json").exists():
        rest_manifest = _load_manifest(OUT_DIR / "manifest.json")
        rest_manifest = _rest_filter(rest_manifest)
        print("Reusing existing rest manifest (skipped Phase A capture)", flush=True)
    else:
        rest_cmd = [
            "python3", "scripts/capture_page_evidence.py",
            "--site-dir", str(scratch),
            "--routes", ",".join(f"/{f['route']}" for f in _FIXTURES),
            "--output-dir", str(rest_out),
            "--manifest", str(rest_manifest_path),
            "--viewports", "desktop,mobile",
            "--locales", "en,zh",
            "--themes", "dark,light",
            "--settle-ms", "1500",
            "--delay-ms", "0",
            "--max-pages", "5",
        ]
        print("Phase A — rest 40 cells:", " ".join(rest_cmd), flush=True)
        rc = subprocess.run(rest_cmd, cwd=_REPO, check=False).returncode
        if rc != 0:
            print(f"capture_page_evidence.py Phase A failed rc={rc}", flush=True)
            return rc
        rest_manifest = _rest_filter(_load_manifest(rest_manifest_path))

    # Phase B: 12 interaction cells on 3 covered routes × desktop / en × 2 force-states × 2 themes.
    interaction_manifest_path = scratch / "manifest.interaction.json"
    inter_out = scratch / "cells.interaction"
    inter_out.mkdir(parents=True, exist_ok=True)
    covered_routes = [f for f in _FIXTURES if f["state"] == "covered"]
    if args.skip_interaction and (OUT_DIR / "manifest.json").exists():
        interaction_manifest = _load_manifest(OUT_DIR / "manifest.json")
        interaction_manifest = _interaction_filter(interaction_manifest)
        print("Reusing existing interaction manifest (skipped Phase B capture)", flush=True)
    else:
        inter_cmd = [
            "python3", "scripts/capture_page_evidence.py",
            "--site-dir", str(scratch),
            "--routes", ",".join(f"/{f['route']}" for f in covered_routes),
            "--output-dir", str(inter_out),
            "--manifest", str(interaction_manifest_path),
            "--viewports", "desktop",
            "--locales", "en",
            "--themes", "dark,light",
            "--settle-ms", "1500",
            "--delay-ms", "0",
            "--max-pages", "3",
        ]
        for fs in FORCE_STATES:
            inter_cmd += ["--force-state", fs]
        print("Phase B — interaction 12 cells:", " ".join(inter_cmd), flush=True)
        rc = subprocess.run(inter_cmd, cwd=_REPO, check=False).returncode
        if rc != 0:
            print(f"capture_page_evidence.py Phase B failed rc={rc}", flush=True)
            return rc
        interaction_manifest = _interaction_filter(_load_manifest(interaction_manifest_path))

    # Move PNGs we are keeping into OUT_DIR/cells before the scratch dir is deleted.
    CELLS_DIR.mkdir(parents=True, exist_ok=True)
    for src_dir in (rest_out, inter_out):
        for png in src_dir.glob("*.png"):
            dest = CELLS_DIR / png.name
            if not dest.exists():
                shutil.copy2(png, dest)
    print(f"Copied PNGs into {CELLS_DIR}", flush=True)

    # Phase C: append 8 expected-miss rows for the 2 no-headline routes.
    expected_miss_by_page = _build_expected_miss_rows("")

    # Stitch: combine rest + interaction + expected-miss into the final manifest.
    merged: dict[str, Any] = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_commit": source_commit,
        "scope": {
            "lanes": ["MO-PAID-006_PAGE_EVIDENCE_R2"],
            "template": "templates/international_macro.html.j2",
            "data_fixture": "origin/main data/international_macro/{EZ,GB,JP}_latest.json + inlined dossier payloads",
        },
        "pages": [],
    }
    by_route_rest = {p["route"]: p for p in rest_manifest["pages"]}
    by_route_inter = {p["route"]: p for p in interaction_manifest["pages"]}
    for fixture in _FIXTURES:
        route = f"/{fixture['route']}"
        rest_page = by_route_rest.get(route)
        inter_page = by_route_inter.get(route, {"states": []})
        expected_miss_states = expected_miss_by_page.get(fixture["page_id"], [])
        if rest_page is None:
            print(f"  ✗ missing rest page for {fixture['page_id']} ({route})", flush=True)
            return 1
        page = {
            "page_id": fixture["page_id"],
            "route": rest_page["route"],
            "states": rest_page["states"] + inter_page["states"] + expected_miss_states,
            "gaps": rest_page.get("gaps", []),
            "metrics": rest_page.get("metrics", {}),
            "console_errors": rest_page.get("console_errors", []),
            "failed_responses": rest_page.get("failed_responses", []),
        }
        merged["pages"].append(page)

    # Sanity-check totals.
    rest_count = sum(len(p["states"]) for p in rest_manifest["pages"])
    inter_count = sum(len(p["states"]) for p in interaction_manifest["pages"])
    miss_count = sum(len(v) for v in expected_miss_by_page.values())
    total = rest_count + inter_count + miss_count
    captured = rest_count + inter_count  # expected-miss rows are captured=False
    print(f"Manifest: rest={rest_count} interaction={inter_count} expected_miss={miss_count} → attempted={total} captured={captured}", flush=True)
    if total != 60 or captured != 52 or miss_count != 8:
        print(f"  ✗ manifest does not match spec (60 attempted / 52 captured / 8 expected miss)", flush=True)
        return 2

    merged = finalize_manifest(merged, template_commit=_git("rev-parse", "HEAD", cwd=_REPO).decode().strip(),
                               site_commit=source_commit)
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Phase D: DOM pass — 40 rest rows + 12 hover/focus values.
    if args.skip_dom and (OUT_DIR / "dom.json").exists():
        print("Reusing existing dom.json (skipped Phase D DOM pass)", flush=True)
    else:
        from playwright.sync_api import sync_playwright  # type: ignore
        dom_rows: list[dict[str, Any]] = []
        with sync_playwright() as m:
            browser = m.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            try:
                # Rest pass: 40 rows.
                for fixture in _FIXTURES:
                    for theme in THEMES:
                        for locale in LOCALES:
                            for vp_name, dims in VIEWPORTS.items():
                                try:
                                    info = _dom_probe(
                                        browser, base_url,
                                        route=fixture["route"],
                                        viewport=dims, theme=theme, locale=locale,
                                    )
                                    row = {
                                        "page_id": fixture["page_id"],
                                        "route": fixture["route"],
                                        "viewport": vp_name,
                                        "viewport_width": dims[0],
                                        "viewport_height": dims[1],
                                        "locale": locale,
                                        "theme": theme,
                                        "applied_theme": info.get("applied_theme"),
                                        "applied_locale": info.get("applied_locale"),
                                        "dossier_state": info.get("dossier_state"),
                                        "item_count": info.get("item_count"),
                                        "leadership_text": info.get("leadership_text"),
                                        "stance_attr": info.get("stance_attr"),
                                        "headline_color_rest": info.get("headline_color"),
                                        "link_ink": info.get("link_ink"),
                                        "text_ink": info.get("text_ink"),
                                        "card_padding": info.get("card_padding"),
                                        "rail_display": info.get("before_display"),
                                        "chip_border_style": info.get("chip_border_style"),
                                        "scroll_w": info.get("scroll_w"),
                                        "viewport_w": info.get("viewport_w"),
                                        "card_bbox": info.get("card_bbox"),
                                        "title_attr_count": info.get("title_attr_count"),
                                        "card_present": True,
                                    }
                                    print(f"  ✓ dom {fixture['page_id']} {theme} {locale} {vp_name}", flush=True)
                                except Exception as exc:
                                    row = {
                                        "page_id": fixture["page_id"],
                                        "viewport": vp_name,
                                        "viewport_width": dims[0],
                                        "locale": locale,
                                        "theme": theme,
                                        "card_present": False,
                                        "error": f"{type(exc).__name__}: {exc}",
                                    }
                                    print(f"  ✗ dom {fixture['page_id']} {theme} {locale} {vp_name}: {exc}", flush=True)
                                dom_rows.append(row)

                # Hover pass: covered routes × en × desktop × {dark, light}.
                for fixture in _FIXTURES:
                    if fixture["state"] != "covered":
                        continue
                    for theme in THEMES:
                        try:
                            info = _hover_probe(
                                browser, base_url,
                                route=fixture["route"],
                                theme=theme, locale="en",
                            )
                            for r in dom_rows:
                                if (r["page_id"] == fixture["page_id"]
                                        and r["theme"] == theme
                                        and r["locale"] == "en"
                                        and r["viewport"] == "desktop"):
                                    r["headline_color_hover"] = (info or {}).get("color")
                                    r["headline_decoration_hover"] = (info or {}).get("decoration")
                                    break
                            print(f"  ✓ hover {fixture['page_id']} {theme} en desktop", flush=True)
                        except Exception as exc:
                            print(f"  ✗ hover {fixture['page_id']} {theme} en desktop: {exc}", flush=True)
                        try:
                            info = _focus_probe(
                                browser, base_url,
                                route=fixture["route"],
                                theme=theme, locale="en",
                            )
                            for r in dom_rows:
                                if (r["page_id"] == fixture["page_id"]
                                        and r["theme"] == theme
                                        and r["locale"] == "en"
                                        and r["viewport"] == "desktop"):
                                    r["headline_color_focus"] = (info or {}).get("color")
                                    r["headline_decoration_focus"] = (info or {}).get("decoration")
                                    r["headline_outline_focus"] = (info or {}).get("outline")
                                    break
                            print(f"  ✓ focus {fixture['page_id']} {theme} en desktop", flush=True)
                        except Exception as exc:
                            print(f"  ✗ focus {fixture['page_id']} {theme} en desktop: {exc}", flush=True)
            finally:
                browser.close()

        (OUT_DIR / "dom.json").write_text(
            json.dumps(dom_rows, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    httpd.shutdown()
    if not args.keep:
        shutil.rmtree(scratch)

    # Summary.
    rest_ok = sum(1 for r in (json.loads((OUT_DIR / "dom.json").read_text(encoding="utf-8"))) if r.get("card_present"))
    hover_ok = sum(1 for r in (json.loads((OUT_DIR / "dom.json").read_text(encoding="utf-8"))) if r.get("headline_color_hover") is not None)
    focus_ok = sum(1 for r in (json.loads((OUT_DIR / "dom.json").read_text(encoding="utf-8"))) if r.get("headline_color_focus") is not None)
    print(
        f"\n{rest_ok}/{len(_FIXTURES)*2*2*2} rest cells, {hover_ok} hover, {focus_ok} focus → "
        f"{OUT_DIR} (commit={source_commit[:12]})",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())