"""Capture the 16-cell evidence matrix for UD-B2-W3 (Drivers fold).

Cells = (hero drivers block + advanced.html section) × dark/light × EN/ZH × 1440/390.

Renders the live templates into a local fixture, serves them, and shoots the
changed surfaces (.ud-drivers on the hero, #vsb-breadth-split-section on
advanced.html). Capture-last: run AFTER the code commit so HEAD is the
capture sha.

Manifest is pages-format mastermind.p0_evidence.v2.
"""
from __future__ import annotations

import hashlib
import http.server
import json
import os
import struct
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"

VIEWPORTS = {
    "desktop": (1440, 900),
    "mobile": (390, 844),
}


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: ARG002
        pass


def _png_dims(data: bytes) -> tuple[int, int]:
    return struct.unpack(">II", data[16:24])


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _env():
    import re

    import jinja2

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES)),
        autoescape=True,
        undefined=jinja2.ChainableUndefined,
    )
    env.filters["min"] = lambda seq: min(seq)
    env.filters["regex_replace"] = (
        lambda s, pattern, repl: re.sub(pattern, repl, s) if isinstance(s, str) else s
    )
    try:
        from engine import i18n

        env.globals.update(td=i18n.td, tr=i18n.tr, zip=zip)
    except Exception:  # noqa: BLE001
        env.globals.update(td=lambda en, zh=None: en, tr=lambda en: en, zip=zip)
    return env


def _hero_html() -> str:
    from engine.election_cycle import sector_bias

    sb = sector_bias("2026-09-20")
    vm = {
        "market_state": {
            "verdict": "MIXED",
            "color": "yellow",
            "score": 55,
            "raw_score": 55,
            "label_en": "Mixed",
            "label_zh": "混合",
            "headline_en": "Buyers are still showing up.",
            "headline_zh": "买盘仍在。",
            "flip_en": "Windows, not certainties.",
            "flip_zh": "是窗口，不是定论。",
            "asof": "2026-09-20",
            "mtf": {"indices": [{"confluence_en": "Held", "confluence_zh": "企稳"}]},
            "radar": {"cycle": {"sector_bias": sb}},
        },
        "stance": {"key": "shift"},
        "alerts": [],
        "event_strip": [],
        "ms_history": [],
        "risk_envelope": {},
        "fear_greed": {"label_en": "Neutral", "label_zh": "中性", "dial": 50},
        "fear_euphoria": {"fe_score": 42, "band": "Neutral"},
        "froth_fragility": {
            "band": "watch",
            "band_zh": "关注",
            "quadrant_en": "Calm & broad",
            "quadrant_zh": "平静且广泛",
            "face_a": {"score": 30},
            "face_b": {"score": 20},
        },
        "latest": {"date": "2026-09-20", "quad_name": "Mixed"},
    }
    inner = _env().get_template("_unified_dashboard_hero.html.j2").render(**vm)
    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<link rel='stylesheet' href='theme.css'></head>"
        f"<body class='page-macro'>{inner}</body></html>"
    )


def _advanced_html() -> str:
    ctx = {
        "latest": {
            "date": "2026-09-20",
            "growth_score": 0.1,
            "growth_confidence": 0.5,
            "inflation_score": -0.1,
            "inflation_confidence": 0.5,
            "preference_check": None,
        },
        "generated_utc": "2026-09-20T00:00:00Z",
        "cross_asset": None,
        "portfolio": None,
        "ic_scorecard": None,
        "components_confirming": [],
        "components_contradicting": [],
        "flip_plain": "",
        "internals": [],
        "size_style": [],
        "breadth_div": None,
        "accumulation": [],
        "holdings_changes": [],
        "holdings_threshold": 1,
        "flows_html": None,
        "breadth_split": {
            "stance_en": "AI names leading — watch, don't chase",
            "stance_zh": "AI 相关股领涨，观察而非追高",
            "latest": {"ai_pct50": 72.0, "nonai_pct50": 47.0, "spread_50": 25.0},
            "cohort_sizes": {"ai_total": 100, "universe": 400},
            "young": False,
        },
    }
    return _env().get_template("advanced.html.j2").render(**ctx)


def main() -> int:
    os.chdir(ROOT)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "theme.css").write_bytes((TEMPLATES / "theme.css").read_bytes())
        (tmp_path / "macro.html").write_text(_hero_html(), encoding="utf-8")
        (tmp_path / "advanced.html").write_text(_advanced_html(), encoding="utf-8")

        handler = QuietHandler
        handler.directory = str(tmp_path)  # type: ignore[attr-defined]

        class _H(QuietHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(tmp_path), **kwargs)

        origin = tmp_path.as_uri()

        from playwright.sync_api import sync_playwright

        pages_out: list[dict] = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                for page_id, route, selector in (
                    ("macro.html", "/macro.html", ".ud-drivers"),
                    ("advanced.html", "/advanced.html", "#vsb-breadth-split-section"),
                ):
                    states: list[dict] = []
                    for vp_name, (width, height) in VIEWPORTS.items():
                        page.set_viewport_size({"width": width, "height": height})
                        for theme in ("dark", "light"):
                            for locale in ("en", "zh"):
                                page.goto(origin + route, wait_until="domcontentloaded")
                                page.evaluate(
                                    """([t, l]) => {
                                      document.documentElement.dataset.theme = t;
                                      document.documentElement.dataset.lang = l;
                                      document.documentElement.lang = l;
                                    }""",
                                    [theme, locale],
                                )
                                page.evaluate("document.fonts.ready")
                                page.wait_for_timeout(200)
                                found = page.locator(selector).count()
                                if found == 0:
                                    raise SystemExit(
                                        f"{route} missing {selector!r}; url={page.url} "
                                        f"html_has={selector.strip('#.') in page.content()}"
                                    )
                                page.wait_for_selector(selector, state="attached", timeout=8000)
                                target = page.locator(selector).first
                                target.scroll_into_view_if_needed(timeout=4000)
                                page.wait_for_timeout(100)
                                fname = f"{page_id[:-5]}_{theme}_{locale}_{vp_name}.png"
                                out_path = EVIDENCE / fname
                                page.screenshot(path=str(out_path), full_page=False)
                                png = out_path.read_bytes()
                                w, h = _png_dims(png)
                                applied_theme = page.evaluate(
                                    "document.documentElement.dataset.theme"
                                )
                                applied_locale = page.evaluate(
                                    "document.documentElement.dataset.lang"
                                )
                                states.append(
                                    {
                                        "viewport": vp_name,
                                        "locale": locale,
                                        "theme": theme,
                                        "access": "anonymous",
                                        "viewport_width": width,
                                        "viewport_height": height,
                                        "force_state": None,
                                        "captured": True,
                                        "file": fname,
                                        "sha256": _sha256(png),
                                        "bytes": len(png),
                                        "width": w,
                                        "height": h,
                                        "applied_theme": applied_theme,
                                        "applied_locale": applied_locale,
                                    }
                                )
                    pages_out.append(
                        {
                            "page_id": page_id,
                            "route": route,
                            "states": states,
                            "gaps": [],
                        }
                    )
                browser.close()
        finally:
            pass

    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": "2026-09-21T00:00:00Z",
        "capture_head": head,
        "pages": pages_out,
    }
    (EVIDENCE / "p0_evidence.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"captured {sum(len(p['states']) for p in pages_out)} cells at {head}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
