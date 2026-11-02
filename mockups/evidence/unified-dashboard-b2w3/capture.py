"""Capture the 16-cell evidence matrix for UD-B2-W3 (Drivers fold).

Cells = (hero drivers block + advanced.html section) × dark/light × EN/ZH × 1440/390.

Renders the live templates into a local fixture, serves them, and shoots the
changed surfaces (.ud-drivers on the hero, #vsb-breadth-split-section on
advanced.html). Capture-last: run AFTER the code commit so HEAD is the
capture sha.

Hero fixture MUST paint `body { background:var(--bg); color:var(--text) }`
(the dashboard.html.j2:326 rule). Without it, theme.css `:root` dark ink
(`--text:#d7dce3`) sits on the browser-default white canvas and the dark
cells are not a dark art direction.

390 hero cells element-crop the W3 tiles (breadth/leadership + sentiment)
so the swipe's off-screen cards 2–3 still appear. Desktop 1440 element-crops
the whole `.ud-drivers` 2×2.

Manifest is pages-format mastermind.p0_evidence.v2.
applied_theme / applied_locale are measured from computed paint, not
set-then-read dataset attributes.
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VIEWPORTS = {
    "desktop": (1440, 900),
    "mobile": (390, 844),
}

# Isolated hero fixture: the dashboard.html.j2:326 canvas rule, token-true.
# Without it, dark --text paints onto a white page (review BLOCKER-1).
_HERO_CHROME = (
    "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
    "<meta name='viewport' content='width=device-width, initial-scale=1'>"
    "<link rel='stylesheet' href='theme.css'>"
    "<style>body{background:var(--bg);color:var(--text);margin:0;"
    "padding:var(--sp-4);}</style></head>"
    "<body class='page-macro'>{inner}</body></html>"
)


class QuietHandler:  # placeholder; real handler is defined in main()
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
    return _HERO_CHROME.replace("{inner}", inner)


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


_PAINT_JS = """([t, l]) => {
  document.documentElement.dataset.theme = t;
  document.documentElement.dataset.lang = l;
  document.documentElement.lang = l;
  document.documentElement.setAttribute('data-theme', t);
  document.documentElement.setAttribute('data-lang', l);
}"""

_MEASURE_JS = """() => {
  const parse = (c) => {
    const m = String(c || '').match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
    if (!m) return {r:255,g:255,b:255};
    return {r:+m[1], g:+m[2], b:+m[3]};
  };
  const lin = (c) => {
    c = c / 255;
    return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  };
  const L = (rgb) => 0.2126 * lin(rgb.r) + 0.7152 * lin(rgb.g) + 0.0722 * lin(rgb.b);
  const bg = getComputedStyle(document.body).backgroundColor;
  const fg = getComputedStyle(document.body).color;
  const bgL = L(parse(bg));
  const fgL = L(parse(fg));
  const paintedTheme = bgL < 0.5 ? 'dark' : 'light';
  const en = document.querySelector('.l-en');
  const zh = document.querySelector('.l-zh');
  const enVis = !!(en && getComputedStyle(en).display !== 'none'
                   && getComputedStyle(en).visibility !== 'hidden');
  const zhVis = !!(zh && getComputedStyle(zh).display !== 'none'
                   && getComputedStyle(zh).visibility !== 'hidden');
  let paintedLocale = null;
  if (zhVis && !enVis) paintedLocale = 'zh';
  else if (enVis && !zhVis) paintedLocale = 'en';
  return {paintedTheme, paintedLocale, bg, fg, bgL, fgL, enVis, zhVis};
}"""

_STACK_DRIVERS_JS = """() => {
  const grid = document.querySelector('.ud-driver-grid');
  if (!grid) return;
  grid.style.display = 'flex';
  grid.style.flexDirection = 'column';
  grid.style.flexWrap = 'nowrap';
  grid.style.overflow = 'visible';
  grid.querySelectorAll('.ud-driver').forEach((el) => {
    el.style.flex = '0 0 auto';
    el.style.width = '100%';
    el.style.maxWidth = '100%';
  });
  const root = document.querySelector('.ud-drivers');
  if (root) root.style.background = 'var(--bg)';
}"""


def _stitch_vertical(pngs: list[bytes], bg_rgb: tuple[int, int, int]) -> bytes:
    from io import BytesIO

    from PIL import Image

    imgs = [Image.open(BytesIO(p)).convert("RGB") for p in pngs]
    gap = 8
    width = max(im.width for im in imgs)
    height = sum(im.height for im in imgs) + gap * (len(imgs) - 1)
    canvas = Image.new("RGB", (width, height), bg_rgb)
    y = 0
    for im in imgs:
        canvas.paste(im, (0, y))
        y += im.height + gap
    out = BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue()


def _bg_rgb_from_css(css_color: str) -> tuple[int, int, int]:
    import re

    m = re.search(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", css_color or "")
    if not m:
        return (15, 17, 21)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def main() -> int:
    from http.server import SimpleHTTPRequestHandler

    os.chdir(ROOT)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "theme.css").write_bytes((TEMPLATES / "theme.css").read_bytes())
        (tmp_path / "macro.html").write_text(_hero_html(), encoding="utf-8")
        (tmp_path / "advanced.html").write_text(_advanced_html(), encoding="utf-8")

        class _H(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(tmp_path), **kwargs)

            def log_message(self, *args):  # noqa: ARG002
                pass

        origin = tmp_path.as_uri()

        from playwright.sync_api import sync_playwright

        pages_out: list[dict] = []
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
                            page.evaluate(_PAINT_JS, [theme, locale])
                            page.evaluate("document.fonts.ready")
                            page.wait_for_timeout(200)
                            found = page.locator(selector).count()
                            if found == 0:
                                raise SystemExit(
                                    f"{route} missing {selector!r}; url={page.url} "
                                    f"html_has={selector.strip('#.') in page.content()}"
                                )
                            page.wait_for_selector(selector, state="attached", timeout=8000)
                            measured = page.evaluate(_MEASURE_JS)
                            if measured["paintedTheme"] != theme:
                                raise SystemExit(
                                    f"{route} {theme}/{locale}/{vp_name}: painted "
                                    f"theme is {measured['paintedTheme']!r} "
                                    f"(body bg={measured['bg']} L={measured['bgL']:.3f}). "
                                    "Canvas did not take the requested art direction."
                                )
                            if measured["paintedLocale"] != locale:
                                raise SystemExit(
                                    f"{route} {theme}/{locale}/{vp_name}: painted "
                                    f"locale is {measured['paintedLocale']!r} "
                                    f"(enVis={measured['enVis']} zhVis={measured['zhVis']})."
                                )
                            fname = f"{page_id[:-5]}_{theme}_{locale}_{vp_name}.png"
                            out_path = EVIDENCE / fname

                            if page_id == "macro.html" and vp_name == "mobile":
                                # 390 swipe hides cards 2–3. Stack the live
                                # tiles and element-crop the W3 surfaces so
                                # leadership + sentiment + the AI chip appear.
                                # [data-driver="leadership"] is a leg of
                                # [data-driver="mtf"]; cropping mtf depicts it.
                                page.evaluate(_STACK_DRIVERS_JS)
                                page.wait_for_timeout(80)
                                crops: list[bytes] = []
                                for crop_sel in (
                                    ".ud-drivers .mx-sec",
                                    '[data-driver="mtf"]',
                                    '[data-driver="fear_greed"]',
                                ):
                                    loc = page.locator(crop_sel).first
                                    loc.scroll_into_view_if_needed(timeout=4000)
                                    crops.append(loc.screenshot(type="png"))
                                png = _stitch_vertical(
                                    crops, _bg_rgb_from_css(measured["bg"])
                                )
                                out_path.write_bytes(png)
                            elif page_id == "macro.html":
                                target = page.locator(selector).first
                                target.scroll_into_view_if_needed(timeout=4000)
                                page.wait_for_timeout(80)
                                # Element crop of the 2×2 (leadership is in
                                # the breadth tile; sentiment is card 3;
                                # locked fourth is visible at 1440).
                                target.screenshot(path=str(out_path))
                            else:
                                target = page.locator(selector).first
                                target.scroll_into_view_if_needed(timeout=4000)
                                page.wait_for_timeout(80)
                                target.screenshot(path=str(out_path))

                            png = out_path.read_bytes()
                            w, h = _png_dims(png)
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
                                    "applied_theme": measured["paintedTheme"],
                                    "applied_locale": measured["paintedLocale"],
                                    "computed_bg": measured["bg"],
                                    "computed_bg_luminance": round(measured["bgL"], 4),
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

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": generated_at,
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
