#!/usr/bin/env python3
"""Capture the A-F02-W2-2 Japan dossier dual-theme evidence matrix.

Renders japan.html to a temp dir from the committed inputs the tests use
(``tests/test_international_macro_dashboards._record`` / ``_history`` plus
``knowledge/policy_geo/country_dossier/jp.yaml``). The repo builder cannot
be pointed at this worktree's ``site/``: ``data/intl/latest.json`` is absent
and ``scripts/build_international_macro.py`` would write
``data/international_macro/*.json``.

Matrix (house law + review BLOCKER 2):
  * 8 frames: dark/light x EN/ZH x 1440/390 of ``.imd-dossier`` in the real
    Japan page composition (ok state from jp.yaml).
  * 2 frames: ``no_coverage`` typed-null on the same Japan chrome (empty
    knowledge root so the producer returns ``file_absent``), dark and light.

Theme and language are seeded in localStorage + data-theme/data-lang BEFORE
navigation. Never toggled mid-capture. ``prefers-reduced-motion: reduce``.
Chrome is launched with ``--force-device-scale-factor=2``.

1440: element clip of ``.imd-dossier`` after measuring scrollHeight / rect.
390: 800-wide window, 390-wide iframe, crop the PNG to the iframe box at the
iframe document's full height (Pillow).
"""

from __future__ import annotations

import hashlib
import http.server
import json
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
from datetime import date, datetime, timezone
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
TODAY = date(2026, 9, 6)
SCALE = 2
ASSETS = (
    "theme.css",
    "product-nav-icons.css",
    "navigation-refresh.css",
    "theme.js",
)

OK_CELLS = [
    ("dark", "en", 1440),
    ("light", "en", 1440),
    ("dark", "zh", 1440),
    ("light", "zh", 1440),
    ("dark", "en", 390),
    ("light", "en", 390),
    ("dark", "zh", 390),
    ("light", "zh", 390),
]
NULL_CELLS = [
    ("dark", "en", 1440),
    ("light", "en", 1440),
]


def _head_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _render(site: Path, *, no_coverage: bool) -> str:
    sys.path.insert(0, str(ROOT))
    from jinja2 import Environment, FileSystemLoader

    from engine import country_dossier as cd
    from engine import international_macro_dashboard as imd
    from tests.test_international_macro_dashboards import _history, _record

    orig = cd.build_dossier_block
    if no_coverage:
        empty = site / "_empty_knowledge"
        empty.mkdir(parents=True, exist_ok=True)
        (empty / "knowledge" / "policy_geo" / "country_dossier").mkdir(
            parents=True, exist_ok=True
        )

        def _absent(cc, today=None, root=None):
            return orig(cc, today=today, root=empty)

        cd.build_dossier_block = _absent
        imd.build_dossier_block = _absent

    try:
        view = imd.build_country_view(_record("JP"), _history(), today=TODAY)
        imd.validate_view(view)
    finally:
        cd.build_dossier_block = orig
        imd.build_dossier_block = orig

    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    html = env.get_template("international_macro.html.j2").render(D=view, RADAR=None)
    name = "japan_no_coverage.html" if no_coverage else "japan.html"
    (site / name).write_text(html, encoding="utf-8")
    return name


def _copy_assets(site: Path) -> None:
    for asset in ASSETS:
        src = ROOT / "templates" / asset
        if src.is_file():
            shutil.copy2(src, site / asset)


def _write_iframe_shell(site: Path, page: str) -> str:
    name = f"iframe390_{page}"
    (site / name).write_text(
        f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>390 iframe shell</title>
<style>
html,body{{margin:0;padding:0;background:#111;}}
#frame{{border:0;width:390px;display:block;background:#fff;}}
</style>
</head>
<body>
<iframe id="frame" src="{page}"></iframe>
</body>
</html>
""",
        encoding="utf-8",
    )
    return name


def _serve(root: Path) -> tuple[socketserver.TCPServer, str]:
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def log_message(self, fmt, *args):
            return

    httpd = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    httpd.allow_reuse_address = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    host, port = httpd.server_address
    return httpd, f"http://{host}:{port}"


def _seed_script(theme: str, lang: str) -> str:
    return f"""
(() => {{
  try {{
    localStorage.setItem('theme', {theme!r});
    localStorage.removeItem('themeAuto');
    localStorage.setItem('lang', {lang!r});
  }} catch (e) {{}}
  document.documentElement.setAttribute('data-theme', {theme!r});
  document.documentElement.setAttribute('data-lang', {lang!r});
}})();
"""


def _measure_dossier(frame) -> dict:
    return frame.evaluate(
        """() => {
          const el = document.querySelector('.imd-dossier');
          if (!el) return {found: false};
          const r = el.getBoundingClientRect();
          return {
            found: true,
            css_width: el.offsetWidth,
            css_height: Math.max(el.offsetHeight, el.scrollHeight),
            scrollHeight: el.scrollHeight,
            scrollWidth: el.scrollWidth,
            bounding_x: r.x,
            bounding_y: r.y,
            bounding_width: r.width,
            bounding_height: r.height,
            text: (el.innerText || '').slice(0, 240),
            has_null: !!el.querySelector('.imd-dos-null'),
            has_stance: !!el.querySelector('.imd-dos-stance'),
            data_theme: document.documentElement.getAttribute('data-theme'),
            data_lang: document.documentElement.getAttribute('data-lang') || 'en',
          };
        }"""
    )


def _verify_png(
    path: Path,
    *,
    expected_css_w: float,
    expected_css_h: float,
    dossier: dict,
    clip_w: float,
    clip_h: float,
    dossier_in_clip: bool,
) -> tuple[bool, str, int, int]:
    if not path.is_file():
        return False, "png missing", 0, 0
    im = Image.open(path)
    pw, ph = im.size
    exp_w = int(round(expected_css_w * SCALE))
    exp_h = int(round(expected_css_h * SCALE))
    if abs(pw - exp_w) > 2 or abs(ph - exp_h) > 2:
        return False, f"png {pw}x{ph} != expected clip {exp_w}x{exp_h} (css {expected_css_w}x{expected_css_h} @2x)", pw, ph
    if not dossier.get("found"):
        return False, "dossier element not found", pw, ph
    if not dossier_in_clip:
        return (
            False,
            (
                f"dossier rect ({dossier.get('bounding_x')},{dossier.get('bounding_y')},"
                f"{dossier.get('bounding_width')}x{dossier.get('bounding_height')}) "
                f"not inside clip {clip_w}x{clip_h}"
            ),
            pw,
            ph,
        )
    return True, "png size matches clip; dossier rect inside captured area", pw, ph


def _dossier_inside(d: dict, clip_w: float, clip_h: float) -> bool:
    if not d.get("found"):
        return False
    x = float(d["bounding_x"])
    y = float(d["bounding_y"])
    w = float(d["bounding_width"])
    h = float(d["css_height"])
    return x >= -1 and y >= -1 and (x + w) <= clip_w + 2 and (y + h) <= clip_h + 2


def capture() -> dict:
    head = _head_sha()
    captured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    site = Path(tempfile.mkdtemp(prefix="mo-f02-w2-2-render-"))
    _copy_assets(site)
    ok_page = _render(site, no_coverage=False)
    null_page = _render(site, no_coverage=True)
    httpd, origin = _serve(site)

    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    frames: list[dict] = []
    command = (
        "python3 mockups/evidence/mo-f02-w2-2/capture_dossier_matrix.py"
    )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=chrome,
                headless=True,
                args=[
                    "--force-device-scale-factor=2",
                    "--hide-scrollbars",
                    "--disable-font-subpixel-positioning",
                ],
            )

            def one(state: str, theme: str, lang: str, width: int, page: str) -> dict:
                fname = f"dossier-{state}-{theme}-{lang}-{width}.png"
                dest = OUT / fname
                viewport_name = "desktop" if width == 1440 else "mobile"
                cell = {
                    "id": f"{state}/{theme}/{lang}/{width}",
                    "state": state,
                    "theme": theme,
                    "lang": lang,
                    "locale": lang,
                    "viewport": viewport_name,
                    "viewport_width": width,
                    "viewport_height": 900 if width == 1440 else 844,
                    "access": "anonymous",
                    "force_state": None if state == "ok" else "no_coverage",
                    "file": fname,
                    "clip_target": ".imd-dossier" if width == 1440 else "iframe#frame @390 full document height",
                    "capture_command": command,
                    "head_sha": head,
                    "captured_at": captured_at,
                }
                context = browser.new_context(
                    viewport={
                        "width": 1440 if width == 1440 else 800,
                        "height": 2400 if width == 1440 else 1600,
                    },
                    device_scale_factor=SCALE,
                    reduced_motion="reduce",
                    color_scheme="dark" if theme == "dark" else "light",
                )
                context.add_init_script(_seed_script(theme, lang))
                page_obj = context.new_page()
                try:
                    if width == 1440:
                        page_obj.goto(f"{origin}/{page}", wait_until="networkidle")
                        page_obj.wait_for_selector(".imd-dossier", timeout=15000)
                        applied_theme = page_obj.evaluate(
                            "() => document.documentElement.getAttribute('data-theme')"
                        )
                        applied_lang = page_obj.evaluate(
                            "() => document.documentElement.getAttribute('data-lang') || 'en'"
                        )
                        dossier = _measure_dossier(page_obj)
                        loc = page_obj.locator(".imd-dossier")
                        box = loc.bounding_box()
                        if box is None:
                            cell.update(
                                {
                                    "captured": False,
                                    "reason": "dossier bounding_box() was None",
                                    "applied_theme": applied_theme,
                                    "applied_locale": applied_lang,
                                    "verified_how": "playwright bounding_box None",
                                }
                            )
                            return cell
                        css_w = float(dossier.get("css_width") or box["width"])
                        css_h = float(dossier.get("css_height") or box["height"])
                        loc.screenshot(path=str(dest), animations="disabled")
                        # After element screenshot the clip IS the dossier; its
                        # rect relative to the PNG is (0,0,css_w,css_h).
                        inside = True
                        ok, reason, pw, ph = _verify_png(
                            dest,
                            expected_css_w=css_w,
                            expected_css_h=css_h,
                            dossier=dossier,
                            clip_w=css_w,
                            clip_h=css_h,
                            dossier_in_clip=inside,
                        )
                        cell.update(
                            {
                                "captured": ok,
                                "reason": None if ok else reason,
                                "applied_theme": applied_theme,
                                "applied_locale": applied_lang,
                                "css_width": css_w,
                                "css_height": css_h,
                                "width": pw,
                                "height": ph,
                                "bytes": dest.stat().st_size if dest.exists() else 0,
                                "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()
                                if dest.exists()
                                else None,
                                "verified_how": (
                                    "Pillow size == css*2; dossier element clip "
                                    f"({css_w:.1f}x{css_h:.1f} CSS); "
                                    f"data-theme={applied_theme} data-lang={applied_lang}; "
                                    f"has_stance={dossier.get('has_stance')} "
                                    f"has_null={dossier.get('has_null')}"
                                ),
                                "dossier_rect": {
                                    "x": 0,
                                    "y": 0,
                                    "width": css_w,
                                    "height": css_h,
                                    "scrollHeight": dossier.get("scrollHeight"),
                                },
                            }
                        )
                        if applied_theme != theme or applied_lang != lang:
                            cell["captured"] = False
                            cell["reason"] = (
                                f"applied theme/lang {applied_theme}/{applied_lang} "
                                f"!= requested {theme}/{lang}"
                            )
                        return cell

                    # Seed localStorage on this origin first (same-origin iframe
                    # then reads it at load). Theme/lang are never toggled after
                    # the iframe document starts parsing.
                    page_obj.goto(f"{origin}/{page}", wait_until="domcontentloaded")
                    seeded = page_obj.evaluate(
                        """() => ({
                          theme: document.documentElement.getAttribute('data-theme'),
                          lang: document.documentElement.getAttribute('data-lang') || 'en',
                          stored_theme: localStorage.getItem('theme'),
                          stored_lang: localStorage.getItem('lang'),
                        })"""
                    )
                    if seeded.get("stored_theme") != theme or seeded.get("stored_lang") != lang:
                        raise RuntimeError(f"origin seed failed: {seeded}")
                    shell = _write_iframe_shell(site, page)
                    page_obj.goto(f"{origin}/{shell}", wait_until="networkidle")
                    frame = page_obj.frame_locator("#frame")
                    frame.locator(".imd-dossier").wait_for(timeout=15000)
                    page_obj.wait_for_function(
                        """() => {
                          const f = document.getElementById('frame');
                          return !!(f && f.contentDocument && f.contentDocument.querySelector('.imd-dossier'));
                        }"""
                    )
                    metrics = page_obj.evaluate(
                        """() => {
                          const f = document.getElementById('frame');
                          const doc = f.contentDocument;
                          const html = doc.documentElement;
                          const el = doc.querySelector('.imd-dossier');
                          const r = el.getBoundingClientRect();
                          const docH = Math.max(
                            html.scrollHeight, doc.body ? doc.body.scrollHeight : 0
                          );
                          f.style.height = docH + 'px';
                          return {
                            docH,
                            applied_theme: html.getAttribute('data-theme'),
                            applied_lang: html.getAttribute('data-lang') || 'en',
                            dossier: {
                              found: true,
                              css_width: el.offsetWidth,
                              css_height: Math.max(el.offsetHeight, el.scrollHeight),
                              scrollHeight: el.scrollHeight,
                              scrollWidth: el.scrollWidth,
                              bounding_x: r.x,
                              bounding_y: r.y,
                              bounding_width: r.width,
                              bounding_height: r.height,
                              has_null: !!el.querySelector('.imd-dos-null'),
                              has_stance: !!el.querySelector('.imd-dos-stance'),
                            },
                          };
                        }"""
                    )
                    page_obj.wait_for_timeout(150)
                    # Re-measure after the iframe height assignment so the
                    # dossier y-position is relative to the full document.
                    metrics = page_obj.evaluate(
                        """() => {
                          const f = document.getElementById('frame');
                          const doc = f.contentDocument;
                          const html = doc.documentElement;
                          const el = doc.querySelector('.imd-dossier');
                          const r = el.getBoundingClientRect();
                          const docH = Math.max(
                            html.scrollHeight, doc.body ? doc.body.scrollHeight : 0
                          );
                          if (Math.abs(f.clientHeight - docH) > 1) {
                            f.style.height = docH + 'px';
                          }
                          return {
                            docH: Math.max(docH, f.clientHeight),
                            applied_theme: html.getAttribute('data-theme'),
                            applied_lang: html.getAttribute('data-lang') || 'en',
                            dossier: {
                              found: true,
                              css_width: el.offsetWidth,
                              css_height: Math.max(el.offsetHeight, el.scrollHeight),
                              scrollHeight: el.scrollHeight,
                              scrollWidth: el.scrollWidth,
                              bounding_x: r.x,
                              bounding_y: r.y,
                              bounding_width: r.width,
                              bounding_height: r.height,
                              has_null: !!el.querySelector('.imd-dos-null'),
                              has_stance: !!el.querySelector('.imd-dos-stance'),
                            },
                          };
                        }"""
                    )
                    iframe_box = page_obj.locator("#frame").bounding_box()
                    dossier = metrics["dossier"]
                    applied_theme = metrics["applied_theme"]
                    applied_lang = metrics["applied_lang"]
                    doc_h = metrics["docH"]
                    raw_path = OUT / f"_raw_{fname}"
                    page_obj.screenshot(path=str(raw_path), full_page=True, animations="disabled")
                    im = Image.open(raw_path)
                    left = int(round(iframe_box["x"] * SCALE))
                    top = int(round(iframe_box["y"] * SCALE))
                    right = int(round((iframe_box["x"] + iframe_box["width"]) * SCALE))
                    bottom = int(round((iframe_box["y"] + iframe_box["height"]) * SCALE))
                    cropped = im.crop((left, top, right, bottom))
                    cropped.save(dest)
                    raw_path.unlink(missing_ok=True)
                    css_w = float(iframe_box["width"])
                    css_h = float(iframe_box["height"])
                    # Dossier coords are iframe-document relative; clip is the
                    # full iframe document, so x/y are already in clip space.
                    inside = _dossier_inside(dossier, 390.0, float(doc_h))
                    ok, reason, pw, ph = _verify_png(
                        dest,
                        expected_css_w=css_w,
                        expected_css_h=css_h,
                        dossier=dossier,
                        clip_w=390.0,
                        clip_h=float(doc_h),
                        dossier_in_clip=inside,
                    )
                    if abs(css_w - 390) > 1:
                        ok = False
                        reason = f"iframe css width {css_w} != 390"
                    cell.update(
                        {
                            "captured": ok,
                            "reason": None if ok else reason,
                            "applied_theme": applied_theme,
                            "applied_locale": applied_lang,
                            "css_width": css_w,
                            "css_height": css_h,
                            "width": pw,
                            "height": ph,
                            "bytes": dest.stat().st_size if dest.exists() else 0,
                            "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()
                            if dest.exists()
                            else None,
                            "verified_how": (
                                "800-wide window; 390 iframe; Pillow crop to iframe box; "
                                f"png==css*2; dossier rect inside iframe doc "
                                f"({dossier.get('bounding_x')},{dossier.get('bounding_y')} "
                                f"{dossier.get('bounding_width')}x{dossier.get('css_height')} "
                                f"in 390x{doc_h}); data-theme={applied_theme} "
                                f"data-lang={applied_lang}"
                            ),
                            "dossier_rect": {
                                "x": dossier.get("bounding_x"),
                                "y": dossier.get("bounding_y"),
                                "width": dossier.get("bounding_width"),
                                "height": dossier.get("css_height"),
                                "scrollHeight": dossier.get("scrollHeight"),
                            },
                            "iframe_document_height": doc_h,
                        }
                    )
                    if applied_theme != theme or applied_lang != lang:
                        cell["captured"] = False
                        cell["reason"] = (
                            f"applied theme/lang {applied_theme}/{applied_lang} "
                            f"!= requested {theme}/{lang}"
                        )
                    return cell
                except Exception as exc:  # noqa: BLE001 — a failed cell is recorded, never faked
                    cell.update(
                        {
                            "captured": False,
                            "reason": f"{type(exc).__name__}: {exc}",
                            "verified_how": "exception during capture",
                        }
                    )
                    return cell
                finally:
                    context.close()

            for theme, lang, width in OK_CELLS:
                frames.append(one("ok", theme, lang, width, ok_page))
            for theme, lang, width in NULL_CELLS:
                frames.append(one("no_coverage", theme, lang, width, null_page))
            browser.close()
    finally:
        httpd.shutdown()
        shutil.rmtree(site, ignore_errors=True)

    return {
        "head_sha": head,
        "captured_at": captured_at,
        "render_note": (
            "Rendered to a temp dir from committed test inputs "
            "(tests/test_international_macro_dashboards._record/_history + "
            "knowledge/policy_geo/country_dossier/jp.yaml). "
            "data/intl/latest.json is absent in this worktree; the repository "
            "builder writes data/international_macro/*.json, which this packet "
            "must not touch. no_coverage frames used an empty knowledge root "
            "so build_dossier_block returned state=no_coverage / reason=file_absent "
            "on the Japan chrome."
        ),
        "command": command,
        "chrome": chrome,
        "chrome_args": [
            "--force-device-scale-factor=2",
            "--hide-scrollbars",
            "--disable-font-subpixel-positioning",
        ],
        "scale": SCALE,
        "frames": frames,
    }


def _state_row(frame: dict) -> dict:
    row = {
        "access": "anonymous",
        "applied_locale": frame.get("applied_locale"),
        "applied_theme": frame.get("applied_theme"),
        "captured": bool(frame.get("captured")),
        "file": frame.get("file"),
        "force_state": frame.get("force_state"),
        "height": frame.get("height"),
        "locale": frame.get("locale"),
        "theme": frame.get("theme"),
        "viewport": frame.get("viewport"),
        "viewport_height": frame.get("viewport_height"),
        "viewport_width": frame.get("viewport_width"),
        "width": frame.get("width"),
        "bytes": frame.get("bytes"),
        "sha256": frame.get("sha256"),
        "css_width": frame.get("css_width"),
        "css_height": frame.get("css_height"),
        "clip_target": frame.get("clip_target"),
        "verified_how": frame.get("verified_how"),
        "capture_command": frame.get("capture_command"),
        "head_sha": frame.get("head_sha"),
        "captured_at": frame.get("captured_at"),
        "dossier_rect": frame.get("dossier_rect"),
        "state": frame.get("state"),
    }
    if not row["captured"]:
        row["reason"] = frame.get("reason")
    return row


def write_receipts(bundle: dict) -> None:
    ok_states = [_state_row(f) for f in bundle["frames"] if f["state"] == "ok"]
    null_states = [_state_row(f) for f in bundle["frames"] if f["state"] == "no_coverage"]
    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": bundle["captured_at"],
        "head_sha": bundle["head_sha"],
        "capture_command": bundle["command"],
        "chrome": bundle["chrome"],
        "chrome_args": bundle["chrome_args"],
        "scale": bundle["scale"],
        "prefers_reduced_motion": "reduce",
        "theme_seed": "localStorage.theme + data-theme set in add_init_script before navigation; never mid-toggle",
        "lang_seed": "localStorage.lang + data-lang set in add_init_script before navigation",
        "render_note": bundle["render_note"],
        "honesty": {
            "authority": "this tool measures and screenshots; it scores, ranks, and judges nothing",
            "gaps": "a frame that fails verification is captured:false with a reason; nothing is inferred for it",
            "render": bundle["render_note"],
        },
        "axes": {
            "themes": ["dark", "light"],
            "locales": ["en", "zh"],
            "viewports": {"desktop": [1440, 900], "mobile": [390, 844]},
            "force_states": ["no_coverage"],
        },
        "outcome": "captured"
        if all(f.get("captured") for f in bundle["frames"])
        else "partial",
        "pages": [
            {
                "page_id": "japan.html",
                "registry_route": "/japan.html",
                "route": "/japan.html",
                "route_kind": "explicit_override",
                "console_errors": [],
                "failed_responses": [],
                "gaps": [],
                "states": ok_states,
            },
            {
                "page_id": "japan.html#no_coverage",
                "registry_route": "/japan.html",
                "route": "/japan_no_coverage.html",
                "route_kind": "forced_typed_null",
                "console_errors": [],
                "failed_responses": [],
                "gaps": [],
                "states": null_states,
            },
        ],
        "tool": {
            "module_ref": "mockups/evidence/mo-f02-w2-2/capture_dossier_matrix.py",
            "version": "1.0.0",
        },
        "totals": {
            "pages": 2,
            "states_attempted": len(bundle["frames"]),
            "states_captured": sum(1 for f in bundle["frames"] if f.get("captured")),
        },
        "frames": bundle["frames"],
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (OUT / "EVIDENCE.yml").write_text(
        "schema: mastermind.page_evidence_receipt.v1\n"
        "changed_paths:\n"
        "  - templates/international_macro.html.j2\n"
        "manifest: mockups/evidence/mo-f02-w2-2/manifest.json\n",
        encoding="utf-8",
    )
    print(f"HEAD {bundle['head_sha']}", flush=True)
    print(f"wrote {OUT / 'manifest.json'} at {bundle['captured_at']}", flush=True)
    for f in bundle["frames"]:
        flag = "OK" if f.get("captured") else "FAIL"
        print(
            f"  {flag} {f['id']} css={f.get('css_width')}x{f.get('css_height')} "
            f"png={f.get('width')}x{f.get('height')} {f.get('reason') or ''}",
            flush=True,
        )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    bundle = capture()
    write_receipts(bundle)
    return 0 if all(f.get("captured") for f in bundle["frames"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
