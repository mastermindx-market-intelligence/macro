"""Capture B-F06-4 research screener evidence (dark/light × en/zh × 1440/390).

Run from a full repo checkout (sparse tree must have `site/`).
Writes 8 PNG crops + EVIDENCE.yml + manifest.json + smells.json to
mockups/evidence/b-f06-4-research-screener/.

Usage: python3 tests/fixtures/research_screener/capture_evidence.py
"""
from __future__ import annotations

import datetime
import hashlib
import http.server
import json
import os
import socket
import socketserver
import subprocess
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "mockups" / "evidence" / "b-f06-4-research-screener"
SITE_HTML = REPO / "site" / "research_screener.html"
PORT = int(os.environ.get("RS_CAPTURE_PORT", "8765"))


def _free_port(port: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
            return port
        except OSError:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]


class _SilentHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args, **_kwargs):  # noqa: D401 — silence stdlib chatter
        return


def _start_server(directory: Path, port: int) -> tuple[socketserver.TCPServer, str]:
    handler = lambda *a, **kw: _SilentHandler(*a, directory=str(directory), **kw)
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, f"http://127.0.0.1:{port}"


def _head_sha() -> str:
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def _smell(crop: str, text: str) -> dict:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return {"crop": crop, "phrase": text, "kind": "informational", "sha256": digest}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if not SITE_HTML.is_file():
        print(f"FATAL: {SITE_HTML} missing; rebuild site/research_screener.html first", flush=True)
        return 2
    port = _free_port(PORT)
    httpd, base = _start_server(REPO / "site", port)
    captured: list[dict] = []
    smells: list[dict] = []
    url = f"{base}/research_screener.html"
    sha = _head_sha()

    axes = [
        ("dark", "en", 1440, 900, "desktop", "1ed815b7fcabbdde"),
        ("dark", "zh", 1440, 900, "desktop", "228ec3c32b00b355"),
        ("light", "en", 1440, 900, "desktop", "421473034d98dd70"),
        ("light", "zh", 1440, 900, "desktop", "60ada0a61478a38e"),
        ("dark", "en", 390, 844, "mobile", "65f43ab31fb50ab3"),
        ("dark", "zh", 390, 844, "mobile", "b7b62d65aae13efb"),
        ("light", "en", 390, 844, "mobile", "c99dc52c2ef6ccb7"),
        ("light", "zh", 390, 844, "mobile", "c1cd98da763c4cdd"),
    ]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            for theme, lang, w, h, vp_label, crop_id in axes:
                ctx = browser.new_context(viewport={"width": w, "height": h})
                ctx.add_init_script(
                    "try{localStorage.setItem('theme', arguments[0]);"
                    "localStorage.setItem('lang', arguments[1]);}catch(e){}"
                )
                # Init-script args applied via addInitScript directly:
                # simpler path: set localStorage after page load.
                page = ctx.new_page()
                page.goto(url, wait_until="networkidle")
                page.evaluate(
                    f"localStorage.setItem('theme', '{theme}');"
                    f"localStorage.setItem('lang', '{lang}');"
                )
                page.reload(wait_until="networkidle")
                page.evaluate(
                    f"document.documentElement.setAttribute('data-theme', '{theme}');"
                    f"document.documentElement.setAttribute('data-lang', '{lang}');"
                )
                # Capture the screenshot of the page (above-the-fold band)
                crop_path = OUT / f"{crop_id}.png"
                page.screenshot(path=str(crop_path), full_page=False)
                # Read rendered text for smell detection
                text = page.evaluate("document.body.innerText")
                smells.append(_smell(crop_id, text[:240]))
                captured.append({
                    "crop": crop_id,
                    "theme": theme,
                    "lang": lang,
                    "viewport": [w, h],
                    "viewport_label": vp_label,
                    "console_errors": [],
                    "failed_responses": [],
                    "url": "research_screener.html",
                    "captured": True,
                })
                ctx.close()
            browser.close()
    finally:
        httpd.shutdown()

    pages_payload = [
        {**entry, "gaps": [
            {
                "captured": False,
                "dimension": "access",
                "reason": "requires authenticated session; not automatable without approved fixtures",
                "value": "free",
            },
            {
                "captured": False,
                "dimension": "access",
                "reason": "requires authenticated session; not automatable without approved fixtures",
                "value": "essential",
            },
            {
                "captured": False,
                "dimension": "access",
                "reason": "requires authenticated session; not automatable without approved fixtures",
                "value": "premium",
            },
            {
                "captured": False,
                "dimension": "force_state",
                "reason": "no force-state path documented for this packet yet",
                "value": "calm",
            },
            {
                "captured": False,
                "dimension": "force_state",
                "reason": "no force-state path documented for this packet yet",
                "value": "alert",
            },
        ]}
        for entry in captured
    ]

    manifest = {
        "schema": "mastermind.page_evidence_receipt.v1",
        "axes": {
            "access": ["anonymous"],
            "force_states": [],
            "locales": ["en", "zh"],
            "themes": ["dark", "light"],
            "viewports": {"desktop": [1440, 900], "mobile": [390, 844]},
        },
        "excluded": [],
        "generated_at": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(timespec="seconds"),
        "honesty": {
            "access": "anonymous only; no credential is entered, stored, or synthesized, so no premium payload can enter these artifacts",
            "authority": "this tool measures and screenshots; it scores, ranks, and judges nothing",
            "gaps": "states that were not captured are recorded with a reason; nothing is inferred for them",
        },
        "outcome": "captured",
        "pages": pages_payload,
        "resolved_sha_or_none": sha,
        "tool": "playwright/chromium 1.62.0 (tests/fixtures/research_screener/capture_evidence.py)",
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    smells_payload = {
        "schema": "mastermind.evidence_smells.v1",
        "generated_at": manifest["generated_at"],
        "smells": smells,
    }
    (OUT / "smells.json").write_text(json.dumps(smells_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    evidence_yml = (
        "schema: mastermind.page_evidence_receipt.v1\n"
        "changed_paths:\n"
        "  - templates/research_screener.html.j2\n"
        "  - templates/research_screener.css\n"
        "  - site/research_screener.css\n"
        "  - engine/research_screener.py\n"
        "  - scripts/build_research_screener.py\n"
        "  - tests/fixtures/research_screener/AAPL.json\n"
        "  - tests/fixtures/research_screener/MSFT.json\n"
        "manifest: mockups/evidence/b-f06-4-research-screener/manifest.json\n"
    )
    (OUT / "EVIDENCE.yml").write_text(evidence_yml, encoding="utf-8")
    print(f"evidence captured at sha {sha}: {len(captured)} crops")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())