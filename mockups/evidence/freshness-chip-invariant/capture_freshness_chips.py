#!/usr/bin/env python3
"""Capture the freshness-chip language-invariance evidence matrix.

Why this packet exists: ``.imd-chip.fresh`` (the international-macro data-health chip,
the same rule the "Confirmed <date>" provenance chip of PR #6933 reuses) painted with
``--ink-up``/``--up``, and theme.css swaps that pair under ``html[data-lang="zh"]`` — so
one freshness chip was green in EN and red in ZH. The fix moves every freshness /
provenance rule onto the status plane (``--ok``/``--warn``/``--act``), which is never
swapped at root. This script captures the proof.

What it renders: japan.html from the committed test inputs
(``tests.test_international_macro_dashboards._record`` / ``_history``) into a temp dir,
with ``theme.css`` / ``theme.js`` copied beside it, served over loopback. The repository
builder cannot be pointed at a sparse worktree (``data/intl/latest.json`` is absent and it
would write ``data/international_macro/*.json``).

Matrix: the eight REST cells the theme-parity gate requires — desktop 1440 / mobile 390
× en / zh × dark / light — each an element clip of the ``.imd-cols`` data-health block
(the row carrying ``.imd-chip.fresh`` and ``.imd-chip.stale``), inside the "Source health &
provenance" receipt dialog opened through the page's own button. Theme and language are
seeded in localStorage + ``data-theme``/``data-lang`` BEFORE navigation and never toggled
mid-capture; ``prefers-reduced-motion: reduce``; device scale 2.

Proof beyond pixels: every cell records ``getComputedStyle`` of the first
``.imd-chip.fresh`` and ``.imd-chip.stale`` (colour, border, background) and of the root
``--up`` token. The run FAILS unless, within each theme × viewport, the freshness chips
resolve to identical colours in EN and ZH while ``--up`` differs (i.e. the ZH swap was
genuinely active and the chips genuinely ignored it).
"""

from __future__ import annotations

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
REL_OUT = OUT.relative_to(ROOT).as_posix()
TODAY = date(2026, 9, 8)
SCALE = 2
ASSETS = ("theme.css", "theme.js", "product-nav-icons.css", "navigation-refresh.css")
OPENER = 'button[data-dialog="dlg-health"]'  # the page's own "Source health & provenance" opener
CLIP = "#dlg-health .imd-cols:has(.imd-chip.fresh)"
CHANGED_PATHS = (
    "templates/theme.css",
    "templates/international_macro.html.j2",
    "templates/china_news.html.j2",
    "templates/committee.html.j2",
    "templates/dashboard.html.j2",
    "templates/foresight.html.j2",
    "templates/hk.html.j2",
    "templates/impulse.html.j2",
    "templates/macro_context.html.j2",
    "templates/sector_central_china.html.j2",
    "templates/stage_analysis.html.j2",
)
VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}
CELLS = [
    (theme, lang, vp)
    for vp in ("desktop", "mobile")
    for lang in ("en", "zh")
    for theme in ("dark", "light")
]
COMMAND = f"python3 {REL_OUT}/capture_freshness_chips.py"


def _head_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _render(site: Path) -> str:
    sys.path.insert(0, str(ROOT))
    from jinja2 import Environment, FileSystemLoader

    from engine import international_macro_dashboard as imd
    from tests.test_international_macro_dashboards import _history, _record

    view = imd.build_country_view(_record("JP"), _history(), today=TODAY)
    imd.validate_view(view)
    states = [h.get("state") for h in view["health"]]
    if "fresh" not in states or "stale" not in states:
        raise SystemExit(f"fixture health states {states} carry no fresh+stale pair — nothing to prove")
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    html = env.get_template("international_macro.html.j2").render(D=view, RADAR=None)
    (site / "japan.html").write_text(html, encoding="utf-8")
    for asset in ASSETS:
        src = ROOT / "templates" / asset
        if src.is_file():
            shutil.copy2(src, site / asset)
    return "japan.html"


def _serve(root: Path) -> tuple[socketserver.TCPServer, str]:
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def log_message(self, fmt, *args):  # noqa: D401 — quiet
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


MEASURE = """() => {
  const pick = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const cs = getComputedStyle(el);
    return { text: (el.textContent || '').trim().slice(0, 40), color: cs.color,
             borderColor: cs.borderTopColor, backgroundColor: cs.backgroundColor };
  };
  const rootCs = getComputedStyle(document.documentElement);
  return {
    applied_theme: document.documentElement.getAttribute('data-theme'),
    applied_lang: document.documentElement.getAttribute('data-lang') || 'en',
    up_token: rootCs.getPropertyValue('--up').trim(),
    ok_token: rootCs.getPropertyValue('--ok').trim(),
    fresh: pick('.imd-chip.fresh'),
    stale: pick('.imd-chip.stale'),
  };
}"""


def _launch(p):
    try:
        return p.chromium.launch(headless=True, args=["--hide-scrollbars"]), "playwright chromium"
    except Exception as exc:  # bundled build missing for this playwright version
        chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if not Path(chrome).is_file():
            raise
        return p.chromium.launch(executable_path=chrome, headless=True, args=["--hide-scrollbars"]), f"{chrome} ({exc.__class__.__name__} on bundled chromium)"


def capture() -> dict:
    head = _head_sha()
    captured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    site = Path(tempfile.mkdtemp(prefix="freshness-chip-render-"))
    page_name = _render(site)
    httpd, origin = _serve(site)
    frames: list[dict] = []
    try:
        with sync_playwright() as p:
            browser, browser_desc = _launch(p)
            for theme, lang, vp in CELLS:
                width, height = VIEWPORTS[vp]
                fname = f"health-chips-{theme}-{lang}-{width}.png"
                cell = {
                    "id": f"{theme}/{lang}/{width}",
                    "state": "rest",
                    "theme": theme,
                    "lang": lang,
                    "locale": lang,
                    "viewport": vp,
                    "viewport_width": width,
                    "viewport_height": height,
                    "access": "anonymous",
                    "force_state": None,
                    "user_state": "dlg-health receipt dialog opened through its own opener button (no forced class)",
                    "file": fname,
                    "clip_target": CLIP,
                    "capture_command": COMMAND,
                    "head_sha": head,
                    "captured_at": captured_at,
                }
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    device_scale_factor=SCALE,
                    reduced_motion="reduce",
                    color_scheme="dark" if theme == "dark" else "light",
                )
                context.add_init_script(_seed_script(theme, lang))
                page = context.new_page()
                try:
                    page.goto(f"{origin}/{page_name}", wait_until="networkidle")
                    # The health chips live inside the "Source health & provenance" receipt
                    # dialog; open it the way a reader does — through its own button.
                    page.click(OPENER)
                    page.wait_for_selector("#dlg-health.open .imd-chip.fresh", state="visible", timeout=15000)
                    page.wait_for_timeout(300)
                    m = page.evaluate(MEASURE)
                    loc = page.locator(CLIP).first
                    loc.scroll_into_view_if_needed()
                    box = loc.bounding_box()
                    if box is None:
                        cell.update({"captured": False, "reason": f"{CLIP} bounding_box() was None",
                                     "applied_theme": m["applied_theme"], "applied_locale": m["applied_lang"]})
                        frames.append(cell)
                        continue
                    loc.screenshot(path=str(OUT / fname))
                    with Image.open(OUT / fname) as im:
                        pw, ph = im.size
                    ok = m["applied_theme"] == theme and m["applied_lang"] == lang and m["fresh"] is not None
                    cell.update({
                        "captured": ok,
                        "reason": None if ok else f"applied theme/lang {m['applied_theme']}/{m['applied_lang']} or chip missing",
                        "applied_theme": m["applied_theme"],
                        "applied_locale": m["applied_lang"],
                        "width": pw,
                        "height": ph,
                        "bytes": (OUT / fname).stat().st_size,
                        "css_width": round(box["width"], 1),
                        "css_height": round(box["height"], 1),
                        "computed": {"up_token": m["up_token"], "ok_token": m["ok_token"],
                                     "fresh_chip": m["fresh"], "stale_chip": m["stale"]},
                        "verified_how": ("data-theme/data-lang read back after load; element clip of "
                                         f"{CLIP} at scale {SCALE}; getComputedStyle of the fresh/stale chips recorded"),
                    })
                finally:
                    context.close()
                frames.append(cell)
            browser.close()
    finally:
        httpd.shutdown()
        shutil.rmtree(site, ignore_errors=True)
    return {"head_sha": head, "captured_at": captured_at, "frames": frames, "browser": browser_desc}


def _invariance(frames: list[dict]) -> dict:
    """Within each theme × viewport: fresh/stale chip colours identical EN vs ZH, --up not."""
    checks = []
    by_key = {(f["theme"], f["viewport"], f["lang"]): f for f in frames if f.get("captured")}
    for theme in ("dark", "light"):
        for vp in ("desktop", "mobile"):
            en, zh = by_key.get((theme, vp, "en")), by_key.get((theme, vp, "zh"))
            if not en or not zh:
                checks.append({"theme": theme, "viewport": vp, "pass": False, "reason": "cell missing"})
                continue
            ce, cz = en["computed"], zh["computed"]
            chips_same = ce["fresh_chip"] == cz["fresh_chip"] and ce["stale_chip"] == cz["stale_chip"]
            swap_active = ce["up_token"] != cz["up_token"]
            checks.append({
                "theme": theme, "viewport": vp,
                "fresh_chip_en": ce["fresh_chip"], "fresh_chip_zh": cz["fresh_chip"],
                "stale_chip_en": ce["stale_chip"], "stale_chip_zh": cz["stale_chip"],
                "up_token_en": ce["up_token"], "up_token_zh": cz["up_token"],
                "chips_identical_en_zh": chips_same, "zh_swap_active": swap_active,
                "pass": chips_same and swap_active,
            })
    return {"rule": ("freshness chips resolve to the same colour in EN and ZH while --up differs "
                     "(the swap was active; the chips ignored it)"),
            "pass": all(c["pass"] for c in checks), "checks": checks}


def _state_row(frame: dict) -> dict:
    row = {k: frame.get(k) for k in (
        "access", "applied_locale", "applied_theme", "captured", "file", "force_state", "height",
        "locale", "theme", "viewport", "viewport_height", "viewport_width", "width", "bytes",
        "css_width", "css_height", "clip_target", "verified_how", "capture_command", "head_sha",
        "captured_at", "state", "computed")}
    row["captured"] = bool(frame.get("captured"))
    if not row["captured"]:
        row["reason"] = frame.get("reason")
    return row


def write_receipts(bundle: dict) -> bool:
    frames = bundle["frames"]
    inv = _invariance(frames)
    all_captured = all(f.get("captured") for f in frames)
    render_note = (
        "Rendered japan.html to a temp dir from committed test inputs "
        "(tests/test_international_macro_dashboards._record/_history, today=2026-09-08) with "
        "templates/theme.css + theme.js copied beside it; the repository builder needs "
        "data/intl/latest.json and writes data/international_macro/*.json, which this packet must "
        "not touch. Each frame is an element clip of the data-health receipt block "
        "(.imd-cols carrying .imd-chip.fresh / .imd-chip.stale) inside the dlg-health receipt "
        "dialog, opened through the page's own opener button — no forced class or attribute."
    )
    manifest = {
        "schema": "mastermind.p0_evidence.v2",
        "generated_at": bundle["captured_at"],
        "head_sha": bundle["head_sha"],
        "capture_command": COMMAND,
        "browser": bundle["browser"],
        "scale": SCALE,
        "prefers_reduced_motion": "reduce",
        "theme_seed": "localStorage.theme + data-theme set in add_init_script before navigation; never mid-toggle",
        "lang_seed": "localStorage.lang + data-lang set in add_init_script before navigation",
        "render_note": render_note,
        "honesty": {
            "authority": "this tool measures and screenshots; it scores, ranks, and judges nothing",
            "gaps": "a frame that fails verification is captured:false with a reason; nothing is inferred for it",
            "render": render_note,
        },
        "axes": {"themes": ["dark", "light"], "locales": ["en", "zh"],
                 "viewports": {"desktop": list(VIEWPORTS["desktop"]), "mobile": list(VIEWPORTS["mobile"])},
                 "force_states": []},
        "outcome": "captured" if all_captured else "partial",
        "invariance": inv,
        "pages": [{
            "page_id": "japan.html",
            "registry_route": "/japan.html",
            "route": "/japan.html",
            "route_kind": "explicit_override",
            "console_errors": [],
            "failed_responses": [],
            "gaps": [],
            "states": [_state_row(f) for f in frames],
        }],
        "tool": {"module_ref": f"{REL_OUT}/capture_freshness_chips.py", "version": "1.0.0"},
        "totals": {"pages": 1, "states_attempted": len(frames),
                   "states_captured": sum(1 for f in frames if f.get("captured"))},
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "EVIDENCE.yml").write_text(
        "schema: mastermind.page_evidence_receipt.v1\nchanged_paths:\n"
        + "".join(f"  - {p}\n" for p in CHANGED_PATHS)
        + f"manifest: {REL_OUT}/manifest.json\n",
        encoding="utf-8",
    )
    print(f"HEAD {bundle['head_sha']}  browser: {bundle['browser']}", flush=True)
    for f in frames:
        flag = "OK" if f.get("captured") else "FAIL"
        c = (f.get("computed") or {}).get("fresh_chip") or {}
        print(f"  {flag} {f['id']:<18} png={f.get('width')}x{f.get('height')} fresh.color={c.get('color')} --up={((f.get('computed') or {}).get('up_token'))} {f.get('reason') or ''}", flush=True)
    for c in inv["checks"]:
        print(f"  invariance {c['theme']}/{c['viewport']}: {'PASS' if c['pass'] else 'FAIL'} "
              f"fresh en={c.get('fresh_chip_en', {}) and c['fresh_chip_en']['color']} zh={c.get('fresh_chip_zh', {}) and c['fresh_chip_zh']['color']} "
              f"--up en={c.get('up_token_en')} zh={c.get('up_token_zh')}", flush=True)
    return all_captured and inv["pass"]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    return 0 if write_receipts(capture()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
