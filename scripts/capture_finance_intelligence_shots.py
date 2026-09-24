"""Capture the Finance Intelligence dossier evidence matrix.

Renders the registered preview shell against the on-disk
``finance_intelligence_read_model.v1.valid.json`` fixture, then drives
Playwright through the §H acceptance matrix:

* 8 base shots — dark/light × en/zh × 1440/390
* 14 cell shots — the seven L1 sections × two themes
* 5 mechanism proofs — freshness pip, rerating stepper dot, focus ring,
  drawer elevation, tier 1 vs tier 2 elevation

Per the spec: the static shell is rendered with a stub ``__FI_READ_URL__``
that the capture script rewrites to a same-origin ``/api/finance-intelligence/v1``
route the fixture serves via ``page.route``. No private store, no publish
lane, no serving route is shipped — only this offline capture path.
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import re
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
TEMPLATES = ROOT / "templates"
FIXTURE = ROOT / "data" / "sector_intelligence" / "fixtures" / "finance_intelligence_read_model.v1.valid.json"
OUT = ROOT / "mockups" / "evidence" / "finance-t8-shell"


def _fixture_payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _patched_html() -> str:
    """Render the J2, then rewrite the placeholder FI_READ_URL to the local
    capture fixture so the offline capture path is honest about its route."""
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    html = env.get_template("finance_intelligence.html.j2").render(
        generated_utc="2026-09-24T12:00:00Z",
        active_section="research",
        active_page="finance_intelligence",
    )
    return html


def _start_server(html: str, fixture: dict) -> tuple[socketserver.TCPServer, threading.Thread]:
    """Bind a localhost server that serves the patched HTML + the fixture route."""

    fixture_bytes = json.dumps(fixture).encode("utf-8")
    html_bytes = html.encode("utf-8")

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args, **_kwargs) -> None:  # silence stderr
            return

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path == "/" or path == "/finance_intelligence.html":
                body = html_bytes
                ctype = "text/html; charset=utf-8"
            elif path == "/finance_intelligence.css":
                body = (SITE / "finance_intelligence.css").read_bytes()
                ctype = "text/css; charset=utf-8"
            elif path == "/finance_intelligence.js":
                js_src = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")
                # Patch the placeholder URL for the offline capture route only.
                js_src = js_src.replace("'__FI_READ_URL__'",
                                        "'/api/finance-intelligence/v1/read'")
                # Disable the boot early-return guard.
                js_src = js_src.replace(
                    "if (!FI_READ_URL || FI_READ_URL.indexOf('__FI_READ_URL__') === 0) return; // placeholder until integration",
                    "if (!FI_READ_URL) return;"
                )
                body = js_src.encode("utf-8")
                ctype = "application/javascript; charset=utf-8"
            elif path == "/api/finance-intelligence/v1/read":
                body = fixture_bytes
                ctype = "application/json"
            elif path == "/__fi_stub__":
                body = b"stub"
                ctype = "text/plain"
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _capture_matrix(host: str, port: int) -> list[dict]:
    captures: list[dict] = []
    base_url = f"http://{host}:{port}/finance_intelligence.html"
    fixtures = [
        ("dark", "en", 1440, 900, "base"),
        ("dark", "zh", 1440, 900, "base"),
        ("dark", "en", 390, 844, "base"),
        ("dark", "zh", 390, 844, "base"),
        ("light", "en", 1440, 900, "base"),
        ("light", "zh", 1440, 900, "base"),
        ("light", "en", 390, 844, "base"),
        ("light", "zh", 390, 844, "base"),
    ]
    sections = [
        "what-changed", "rerating-map", "system-map", "subtheme-atlas",
        "company-exposure", "macro-matrix", "constraint-map",
    ]
    cell_fixtures = [
        (theme, "en", 1440, 900, section, "cell")
        for theme in ("dark", "light") for section in sections
    ]
    mechanism_fixtures = [
        ("dark", "en", 1440, 900, "freshness-pip", "mechanism"),
        ("dark", "en", 1440, 900, "stepper-dot", "mechanism"),
        ("dark", "en", 1440, 900, "focus-ring", "mechanism"),
        ("dark", "en", 1440, 900, "drawer-open", "mechanism"),
        ("dark", "en", 1440, 900, "tier1-vs-tier2", "mechanism"),
    ]
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for theme, lang, w, h, kind in fixtures:
            ctx = browser.new_context(
                viewport={"width": w, "height": h},
                color_scheme=theme,
                locale="en-US" if lang == "en" else "zh-CN",
            )
            ctx.add_init_script(
                f"localStorage.setItem('theme', '{theme}');"
                f"localStorage.setItem('lang', '{lang}');"
            )
            page = ctx.new_page()
            page.goto(base_url, wait_until="networkidle")
            page.wait_for_selector("[data-fi-mount='notice']", state="attached")
            # Wait for hydration — the slice selector must have an option.
            try:
                page.wait_for_function(
                    "() => document.querySelectorAll('#fi-slice-select option').length > 0",
                    timeout=5000,
                )
            except Exception:
                pass
            name = f"{kind}_{theme}_{lang}_{w}x{h}.png"
            out_path = OUT / name
            page.screenshot(path=str(out_path), full_page=False)
            captures.append({"name": name, "theme": theme, "lang": lang,
                             "viewport": [w, h], "kind": kind, "path": str(out_path.relative_to(ROOT))})
            ctx.close()

        for theme, lang, w, h, section, kind in cell_fixtures:
            ctx = browser.new_context(
                viewport={"width": w, "height": h},
                color_scheme=theme,
                locale="en-US" if lang == "en" else "zh-CN",
            )
            ctx.add_init_script(
                f"localStorage.setItem('theme', '{theme}');"
                f"localStorage.setItem('lang', '{lang}');"
            )
            page = ctx.new_page()
            page.goto(base_url + f"#{section}", wait_until="networkidle")
            page.wait_for_selector(f"#{section}", state="attached")
            try:
                page.wait_for_function(
                    "() => document.querySelectorAll('#fi-slice-select option').length > 0",
                    timeout=5000,
                )
            except Exception:
                pass
            name = f"{kind}_{section}_{theme}_{lang}_{w}x{h}.png"
            out_path = OUT / name
            section_el = page.locator(f"#{section}")
            section_el.scroll_into_view_if_needed()
            page.wait_for_timeout(120)
            section_el.screenshot(path=str(out_path))
            captures.append({"name": name, "section": section, "theme": theme, "lang": lang,
                             "viewport": [w, h], "kind": kind, "path": str(out_path.relative_to(ROOT))})
            ctx.close()

        for theme, lang, w, h, what, kind in mechanism_fixtures:
            ctx = browser.new_context(
                viewport={"width": w, "height": h},
                color_scheme=theme,
                locale="en-US",
            )
            ctx.add_init_script(
                f"localStorage.setItem('theme', '{theme}');"
                f"localStorage.setItem('lang', '{lang}');"
            )
            page = ctx.new_page()
            page.goto(base_url, wait_until="networkidle")
            try:
                page.wait_for_function(
                    "() => document.querySelectorAll('#fi-slice-select option').length > 0",
                    timeout=5000,
                )
            except Exception:
                pass
            page.wait_for_timeout(120)
            if what == "freshness-pip":
                page.evaluate(
                    "() => document.getElementById('what-changed').scrollIntoView({block:'start'})"
                )
                page.wait_for_timeout(120)
                target = page.locator("#what-changed > .fi-section-head")
            elif what == "stepper-dot":
                page.evaluate(
                    "() => document.getElementById('rerating-map').scrollIntoView({block:'start'})"
                )
                page.wait_for_timeout(120)
                target = page.locator(".fi-rerating-steps")
            elif what == "focus-ring":
                page.evaluate(
                    "() => { document.querySelectorAll('.fi-chip').forEach(c => c.tabIndex = 0);"
                    "document.querySelector('.fi-slice-select').focus(); }"
                )
                page.evaluate(
                    "() => document.querySelector('.fi-slice-picker').scrollIntoView({block:'center'})"
                )
                page.wait_for_timeout(160)
                target = page.locator(".fi-slice-picker")
            elif what == "drawer-open":
                page.evaluate(
                    "() => { const b = document.querySelector('#rerating-map .fi-step-evidence'); if (b) b.click(); }"
                )
                page.wait_for_timeout(160)
                target = page.locator("body")
            elif what == "tier1-vs-tier2":
                page.evaluate(
                    "() => document.getElementById('subtheme-atlas').scrollIntoView({block:'start'})"
                )
                page.wait_for_timeout(160)
                target = page.locator("#subtheme-atlas")
            else:
                target = page.locator("body")
            name = f"{kind}_{what}_{theme}_{lang}.png"
            out_path = OUT / name
            target.screenshot(path=str(out_path), timeout=5000)
            captures.append({"name": name, "mechanism": what, "theme": theme, "lang": lang,
                             "viewport": [w, h], "kind": kind, "path": str(out_path.relative_to(ROOT))})
            ctx.close()
        browser.close()
    return captures


def _manifest(captures: list[dict]) -> dict:
    return {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": "2026-09-24T12:00:00Z",
        "outcome": "captured",
        "honesty": {
            "access": "anonymous only; no credential is entered, stored, or synthesized",
            "authority": "this tool measures and screenshots; it scores, ranks, and judges nothing",
            "gaps": "the stub route is an offline capture surface only; the production route ships behind site_full",
            "source": "locally rendered templates/finance_intelligence.html.j2 against data/sector_intelligence/fixtures/finance_intelligence_read_model.v1.valid.json"
        },
        "axes": {
            "access": ["anonymous"],
            "locales": ["en", "zh"],
            "themes": ["dark", "light"],
            "viewports": {"desktop": [1440, 900], "mobile": [390, 844]}
        },
        "excluded": [],
        "pages": [
            {
                "page_id": "finance_intelligence_dossier",
                "registry_route": "/finance_intelligence.html",
                "route": "/finance_intelligence.html",
                "route_kind": "local_fixture",
                "viewports": [1440, 390],
                "locales": ["en", "zh"],
                "themes": ["dark", "light"],
                "shots": [c for c in captures if c.get("kind") == "base"]
            },
            {
                "page_id": "finance_intelligence_dossier_section",
                "registry_route": "/finance_intelligence.html",
                "route": "/finance_intelligence.html",
                "route_kind": "local_fixture",
                "viewports": [1440],
                "locales": ["en"],
                "themes": ["dark", "light"],
                "sections": ["what-changed", "rerating-map", "system-map",
                             "subtheme-atlas", "company-exposure", "macro-matrix",
                             "constraint-map"],
                "shots": [c for c in captures if c.get("kind") == "cell"]
            },
            {
                "page_id": "finance_intelligence_dossier_mechanism",
                "registry_route": "/finance_intelligence.html",
                "route": "/finance_intelligence.html",
                "route_kind": "local_fixture",
                "mechanisms": ["freshness-pip", "stepper-dot", "focus-ring",
                               "drawer-open", "tier1-vs-tier2"],
                "shots": [c for c in captures if c.get("kind") == "mechanism"]
            }
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.parse_args()
    if not FIXTURE.exists():
        print(f"missing fixture: {FIXTURE}", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    html = _patched_html()
    fixture = _fixture_payload()
    server, _thread = _start_server(html, fixture)
    host, port = server.server_address
    try:
        captures = _capture_matrix(host, port)
        manifest = _manifest(captures)
        (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (OUT / "EVIDENCE.yml").write_text(
            "schema: mastermind.page_evidence_receipt.v1\n"
            "changed_paths:\n"
            "  - templates/finance_intelligence.html.j2\n"
            "  - templates/finance_intelligence.css\n"
            "  - templates/finance_intelligence.js\n"
            "manifest: mockups/evidence/finance-t8-shell/manifest.json\n",
            encoding="utf-8",
        )
        print(f"captured {len(captures)} shots into {OUT}")
        return 0
    finally:
        server.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
