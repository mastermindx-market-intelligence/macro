#!/usr/bin/env python3
"""Capture the AM Edition page's required eight-cell REST evidence matrix."""
from __future__ import annotations

import hashlib
import json
import shutil
import struct
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from scripts.build_am_edition import build_payload  # noqa: E402
from tests.test_am_edition_page import _fresh_tree  # noqa: E402

OUT_DIR = _ROOT / "mockups" / "evidence" / "am_edition"
SHOTS_DIR = OUT_DIR / "shots"
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
  const root = document.documentElement;
  if (typeof window.setTheme === 'function') window.setTheme(state.theme);
  else root.setAttribute('data-theme', state.theme);
  if (typeof window.setLang === 'function') window.setLang(state.locale);
  else {
    root.setAttribute('data-lang', state.locale);
    root.lang = state.locale === 'zh' ? 'zh' : 'en';
  }
  return {theme: root.getAttribute('data-theme'), locale: root.getAttribute('data-lang')};
}
"""


def _content_address_png(png: bytes) -> tuple[str, str, int, int]:
    digest = hashlib.sha256(png).hexdigest()
    name = f"{digest}.png"
    png_signature = b"\x89PNG\r\n\x1a\n"
    if len(png) >= 24 and png[:8] == png_signature and png[12:16] == b"IHDR":
        width, height = struct.unpack(">II", png[16:24])
    else:
        width, height = 0, 0
    return name, digest, int(width), int(height)


def _fixture_view_model() -> dict:
    scratch = _ROOT / ".am-edition-evidence-fixture"
    site = scratch / "site"
    data = scratch / "data"
    shutil.rmtree(scratch, ignore_errors=True)
    _fresh_tree(
        scratch,
        tape_asof="2026-09-08T13:00:00Z",
        session_date="2026-09-08",
    )
    payload = build_payload(
        site,
        data,
        now=datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc),
    )
    payload["morning_source_feasibility"] = "DEGRADED"
    payload["morning_source_feasibility_cause_en"] = (
        "The morning source is degraded, so the page shows its latest known readings."
    )
    payload["morning_source_feasibility_cause_zh"] = (
        "晨间数据源已降级，页面展示最新已知读数。"
    )
    return payload


def _remove_stale_fixture() -> None:
    shutil.rmtree(_ROOT / ".am-edition-evidence-fixture", ignore_errors=True)


def _render_fixture_site(scratch: Path) -> None:
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    environment = Environment(
        loader=FileSystemLoader(str(_ROOT / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    html = environment.get_template("am_edition.html.j2").render(
        payload=_fixture_view_model(),
        as_of="2026-09-08T15:00Z",
    )
    scratch.mkdir(parents=True, exist_ok=True)
    for name in (
        "theme.css",
        "navigation-refresh.css",
        "nav_market.js",
        "theme.js",
        "logo_config.js",
        "stock-logos.js",
        "live.js",
    ):
        source = _ROOT / "templates" / name
        if source.exists():
            shutil.copy(source, scratch / name)
    (scratch / "am_edition.html").write_text(html, encoding="utf-8")


def _git_head() -> str | None:
    from scripts.capture_page_evidence import _git_head_sha

    return _git_head_sha(_ROOT).sha


def _record(png: bytes, alias: str, state: dict) -> dict:
    name, digest, width, height = _content_address_png(png)
    (SHOTS_DIR / name).write_bytes(png)
    result = dict(state)
    result.update(
        captured=True,
        file=f"shots/{name}",
        alias=alias,
        sha256=digest,
        bytes=len(png),
        width=width,
        height=height,
    )
    return result


def _module_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def main() -> int:
    from playwright.sync_api import sync_playwright
    from scripts.capture_page_evidence import serve_site_dir

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    for existing in SHOTS_DIR.glob("*.png"):
        existing.unlink()
    _remove_stale_fixture()

    scratch = Path(tempfile.mkdtemp(prefix="am-edition-evidence-"))
    _render_fixture_site(scratch)
    httpd, port = serve_site_dir(scratch)
    states: list[dict] = []
    aliases: dict[str, str] = {}

    try:
        manager = sync_playwright().start()
        try:
            browser = manager.chromium.launch(headless=True)
            for viewport, (width, height) in VIEWPORTS.items():
                for locale in LOCALES:
                    for theme in THEMES:
                        requested = {"theme": theme, "locale": locale}
                        context = browser.new_context(
                            viewport={"width": width, "height": height},
                            locale="zh-CN" if locale == "zh" else "en-US",
                            color_scheme=theme,
                            device_scale_factor=1,
                            has_touch=viewport == "mobile",
                        )
                        context.add_init_script(
                            f"({_STATE_SEED_SCRIPT.strip()})({json.dumps(requested)})"
                        )
                        page = context.new_page()
                        entry = {
                            "viewport": viewport,
                            "locale": locale,
                            "theme": theme,
                            "access": "anonymous",
                            "viewport_width": width,
                            "viewport_height": height,
                            "force_state": None,
                            "subject": "full",
                        }
                        try:
                            response = page.goto(
                                f"http://127.0.0.1:{port}/am_edition.html",
                                wait_until="load",
                                timeout=30000,
                            )
                            if response is None or not response.ok:
                                raise RuntimeError(
                                    f"HTTP {getattr(response, 'status', None)}"
                                )
                            observed = page.evaluate(
                                _APPLY_STATE_SCRIPT.strip(), requested
                            ) or {}
                            if observed.get("theme") != theme:
                                raise RuntimeError(
                                    f"requested theme {theme!r}, observed {observed!r}"
                                )
                            if observed.get("locale") != locale:
                                raise RuntimeError(
                                    f"requested lang {locale!r}, observed {observed!r}"
                                )
                            page.wait_for_timeout(150)
                            alias = f"full-{theme}-{locale}-{viewport}.png"
                            entry = _record(
                                page.screenshot(type="png", full_page=True),
                                alias,
                                entry,
                            )
                            entry["applied_theme"] = observed["theme"]
                            entry["applied_locale"] = observed["locale"]
                            aliases[alias] = entry["file"]
                        except Exception as exc:
                            entry.update(
                                captured=False,
                                reason=f"{type(exc).__name__}: {exc}",
                            )
                        finally:
                            context.close()
                        states.append(entry)
                        outcome = "ok" if entry.get("captured") else entry.get("reason")
                        print(f"  {theme}/{locale}/{viewport}: {outcome}", flush=True)
        finally:
            browser.close()
            manager.stop()
    finally:
        httpd.shutdown()
        shutil.rmtree(scratch, ignore_errors=True)
        _remove_stale_fixture()

    captured = sum(1 for state in states if state.get("captured"))
    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "tool": {
            "module_ref": "scripts/capture_am_edition_evidence.py",
            "module_sha256": _module_sha256(),
        },
        "target": "am_edition.html",
        "head": _git_head(),
        "axes": {
            "viewports": VIEWPORTS,
            "locales": list(LOCALES),
            "themes": list(THEMES),
            "access": ["anonymous"],
            "subjects": ["full"],
        },
        "selection": {"page": "am_edition.html", "access": "anonymous"},
        "aliases": aliases,
        "excluded": [],
        "outcome": "captured" if captured == 8 else "partial",
        "totals": {
            "rest_cells": captured,
            "rest_required": 8,
            "pages": 1,
        },
        "honesty": {
            "access": "anonymous only",
            "gaps": "Uncaptured cells are retained with a failure reason.",
            "authority": "This tool captures screenshots; it scores nothing.",
            "page": (
                "templates/am_edition.html.j2 rendered from the am_edition.v1 "
                "fixture view-model (no live data/ or site/ reads). Omitted "
                "from live: the daily bake, write_page asset optimization, and "
                "dynamic live-quote hydration."
            ),
        },
        "pages": [
            {
                "page_id": "am_edition.html",
                "route": "/am_edition.html",
                "registry_route": "/am_edition.html",
                "route_kind": "am_edition",
                "subject": "full",
                "selector": "body",
                "states": states,
                "metrics": {},
                "console_errors": [],
                "failed_responses": [],
                "gaps": [],
            }
        ],
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (OUT_DIR / "EVIDENCE.yml").write_text(
        "schema: mastermind.page_evidence_receipt.v1\n"
        "changed_paths:\n"
        "  - templates/am_edition.html.j2\n"
        "manifest: mockups/evidence/am_edition/manifest.json\n",
        encoding="utf-8",
    )
    print(
        f"outcome: {manifest['outcome']}  states: {captured}/8  "
        f"manifest: {OUT_DIR / 'manifest.json'}"
    )
    return 0 if captured == 8 else 3


if __name__ == "__main__":
    raise SystemExit(main())
