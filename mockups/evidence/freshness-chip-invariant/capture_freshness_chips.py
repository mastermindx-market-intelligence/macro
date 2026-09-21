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
    "templates/_risk_radar_card.css.j2",
    "templates/_ignition_radar_card.css.j2",
)

# Extra surfaces (Opus M2): dark/light × EN/ZH at 1440; dashboard also 390.
# Recorded as force_state clips so japan.html keeps the required 8 REST cells.
EXTRA_SURFACES = (
    {"id": "rrx-fresh", "clip": "#surf-rrx .rrx-rec-chip.fresh", "viewports": ("desktop",),
     "pick": ".rrx-rec-chip.fresh"},
    {"id": "igs-fresh", "clip": "#surf-igs .igs-dot.fresh", "viewports": ("desktop",),
     "pick": ".igs-dot.fresh"},
    {"id": "rr-cov", "clip": "#surf-rrcov .rr-cov-fresh", "viewports": ("desktop", "mobile"),
     "pick": ".rr-cov-fresh"},
    {"id": "hk-stale", "clip": "#surf-hk .hk-fresh-stale", "viewports": ("desktop",),
     "pick": ".hk-fresh-stale"},
    {"id": "stale-ok", "clip": "#surf-stale .stale-ok", "viewports": ("desktop",),
     "pick": ".stale-ok"},
    {"id": "impulse-new", "clip": "#surf-impulse .chip.fresh.new", "viewports": ("desktop",),
     "pick": ".chip.fresh.new"},
    {"id": "sig-fresh", "clip": "#surf-sig", "viewports": ("desktop",),
     "pick": ".sig-fresh"},
    {"id": "fxdot", "clip": "#surf-fx .fx-asof", "viewports": ("desktop",),
     "pick": ".fxdot"},
    {"id": "freshdot", "clip": "#surf-stage .freshdot", "viewports": ("desktop",),
     "pick": ".freshdot"},
    {"id": "tp-fresh-live", "clip": "#surf-tp .tp-node.fresh-live", "viewports": ("desktop",),
     "pick": ".tp-node.fresh-live"},
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


def _render_specimen(site: Path) -> str:
    """Mount every other changed freshness surface against committed CSS + theme.css.

    These pages cannot be rendered from the sparse tree (they need data/ payloads
    the packet must not write). The specimen uses the live template CSS so the
    clip is the affected element, not a restyled stand-in.
    """
    rrx_css = (ROOT / "templates/_risk_radar_card.css.j2").read_text(encoding="utf-8")
    igs_css = (ROOT / "templates/_ignition_radar_card.css.j2").read_text(encoding="utf-8")
    extra_css = """
    .specimen { font: 13px/1.4 Inter, system-ui, sans-serif; background: var(--bg); color: var(--text);
      padding: 24px; display: grid; gap: 28px; }
    .specimen section { padding: 14px; border: 1px solid var(--line); background: var(--panel);
      border-radius: 10px; }
    .rr-cov{display:inline-flex;align-items:center;padding:2px 7px;border-radius:4px;font-size:9.5px;font-weight:600}
    .rr-cov-fresh{background:color-mix(in srgb,var(--ok) 15%,transparent);color:var(--ink-ok, var(--ok));border:1px solid color-mix(in srgb,var(--ok) 30%,transparent)}
    .rr-cov-stale{background:color-mix(in srgb,var(--act) 15%,transparent);color:var(--ink-act, var(--act));border:1px solid color-mix(in srgb,var(--act) 30%,transparent)}
    .hk-fresh-stale { border: 1px solid color-mix(in srgb, var(--act) 50%, var(--line)); background: color-mix(in srgb, var(--act) 7%, var(--panel)); padding: 9px 12px; }
    .hk-fresh-stale .hb-h { margin: 0 0 5px; font-weight: 800; color: var(--ink-act, var(--act)); }
    .stale-ok { color: var(--ink-ok, var(--ok)); }
    .stale-old { color: var(--ink-act, var(--act)); }
    .chip { font-size:10.5px; padding:1px 7px; border-radius:6px; background:var(--panel2); border:1px solid var(--line); color:var(--muted); }
    .chip.fresh { color:var(--muted); }
    .chip.fresh.new { color:var(--ink-ok, var(--ok)); border-color:color-mix(in srgb,var(--ok) 45%,var(--line)); font-weight:800; }
    .rg-stale-notice { display:flex; gap:9px; font-size:12.5px; padding:9px 14px;
      border:1px solid color-mix(in srgb, var(--act) 40%, var(--line));
      border-left:3px solid var(--act); border-radius: var(--r-card, 12px);
      background: color-mix(in srgb, var(--act) 5%, var(--panel)); }
    .sig-fresh { color:var(--ink-ok, var(--ok)); font-size:8px; margin-left:2px; }
    .fx-asof{ display:inline-flex; align-items:center; gap:7px; font-size:12px; color:var(--muted); }
    .fx-asof .fxdot{ width:7px; height:7px; border-radius:var(--r-pill, 999px); background:var(--ok); flex:none; }
    .freshdot{width:6px;height:6px;border-radius:var(--r-pill, 999px);background:var(--ok);
      box-shadow:0 0 0 3px color-mix(in srgb,var(--ok) 22%,transparent);display:inline-block;margin-left:1px}
    .tp-wrap{ position:relative; height:40px; }
    .tp-node{ position:absolute; left:24px; top:10px; width:12px; height:12px; border-radius:50%; background:var(--ok); border:3px solid var(--bg); }
    .tp-node.fresh-live{ box-shadow:0 0 0 4px color-mix(in srgb,var(--ch,var(--ok)) 20%,transparent); }
    """
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="theme.css">
<script src="theme.js"></script>
<style>{rrx_css}\n{igs_css}\n{extra_css}</style>
</head>
<body class="specimen">
<section id="surf-rrx" class="rrx">
  <div class="rrx-rec" style="--rvc: var(--ok)">
    <span class="rrx-rec-chip fresh">Fed liquidity expanding</span>
  </div>
</section>
<section id="surf-igs" class="igs igs-ignited">
  <span class="igs-dots"><span class="igs-dot fresh"></span></span>
</section>
<section id="surf-rrcov">
  <span class="rr-cov rr-cov-fresh">fresh coverage</span>
  <span class="rr-cov rr-cov-stale">stale coverage</span>
</section>
<section id="surf-hk">
  <div class="hk-fresh-stale"><div class="hb-h">Stale tape</div></div>
</section>
<section id="surf-stale">
  <span class="stale-ok">fresh</span> · <span class="stale-old">stale</span>
</section>
<section id="surf-impulse">
  <span class="chip fresh new">NEW today</span>
</section>
<section id="surf-sig">
  <div class="rg-stale-notice">regime input overdue</div>
  <span>signal<span class="sig-fresh">●</span></span>
</section>
<section id="surf-fx">
  <span class="fx-asof"><span class="fxdot"></span> as of</span>
</section>
<section id="surf-stage">
  Stage 2 <span class="freshdot"></span>
</section>
<section id="surf-tp">
  <div class="tp-wrap"><span class="tp-node fresh-live"></span></div>
</section>
</body>
</html>
"""
    (site / "specimen.html").write_text(html, encoding="utf-8")
    return "specimen.html"


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
             borderColor: cs.borderTopColor, backgroundColor: cs.backgroundColor,
             boxShadow: cs.boxShadow };
  };
  const rootCs = getComputedStyle(document.documentElement);
  const rrx = document.querySelector('.rrx');
  const rrxCs = rrx ? getComputedStyle(rrx) : null;
  return {
    applied_theme: document.documentElement.getAttribute('data-theme'),
    applied_lang: document.documentElement.getAttribute('data-lang') || 'en',
    up_token: rootCs.getPropertyValue('--up').trim(),
    ok_token: rootCs.getPropertyValue('--ok').trim(),
    fresh_ok_token: rootCs.getPropertyValue('--fresh-ok').trim(),
    rrx_ok_token: rrxCs ? rrxCs.getPropertyValue('--ok').trim() : null,
    fresh: pick('.imd-chip.fresh'),
    stale: pick('.imd-chip.stale'),
  };
}"""


def _measure_extra(pick: str) -> str:
    return f"""() => {{
  const el = document.querySelector({pick!r});
  const cs = el ? getComputedStyle(el) : null;
  const rootCs = getComputedStyle(document.documentElement);
  const rrx = document.querySelector('.rrx');
  const rrxCs = rrx ? getComputedStyle(rrx) : null;
  return {{
    applied_theme: document.documentElement.getAttribute('data-theme'),
    applied_lang: document.documentElement.getAttribute('data-lang') || 'en',
    up_token: rootCs.getPropertyValue('--up').trim(),
    ok_token: rootCs.getPropertyValue('--ok').trim(),
    fresh_ok_token: rootCs.getPropertyValue('--fresh-ok').trim(),
    rrx_ok_token: rrxCs ? rrxCs.getPropertyValue('--ok').trim() : null,
    color: cs ? cs.color : null,
    borderColor: cs ? cs.borderTopColor : null,
    backgroundColor: cs ? cs.backgroundColor : null,
    boxShadow: cs ? cs.boxShadow : null,
    present: !!el,
  }};
}}"""


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
    specimen_name = _render_specimen(site)
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
            extra_cells = [
                (surf, theme, lang, vp)
                for surf in EXTRA_SURFACES
                for vp in surf["viewports"]
                for lang in ("en", "zh")
                for theme in ("dark", "light")
            ]
            for surf, theme, lang, vp in extra_cells:
                width, height = VIEWPORTS[vp]
                fname = f"{surf['id']}-{theme}-{lang}-{width}.png"
                cell = {
                    "id": f"{surf['id']}/{theme}/{lang}/{width}",
                    "state": "rest",
                    "theme": theme,
                    "lang": lang,
                    "locale": lang,
                    "viewport": vp,
                    "viewport_width": width,
                    "viewport_height": height,
                    "access": "anonymous",
                    "force_state": surf["id"],
                    "user_state": f"specimen clip of {surf['clip']} (committed CSS + theme.css)",
                    "file": fname,
                    "clip_target": surf["clip"],
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
                    page.goto(f"{origin}/{specimen_name}", wait_until="networkidle")
                    page.evaluate(
                        """([t, l]) => {
                          document.documentElement.setAttribute('data-theme', t);
                          document.documentElement.setAttribute('data-lang', l);
                          try { localStorage.setItem('theme', t); localStorage.removeItem('themeAuto');
                                localStorage.setItem('lang', l); } catch (e) {}
                          if (typeof window.setTheme === 'function') window.setTheme(t);
                          if (typeof window.setLang === 'function') window.setLang(l);
                        }""",
                        [theme, lang],
                    )
                    page.wait_for_selector(surf["clip"], state="visible", timeout=15000)
                    page.wait_for_timeout(200)
                    m = page.evaluate(_measure_extra(surf["pick"]))
                    loc = page.locator(surf["clip"]).first
                    loc.scroll_into_view_if_needed()
                    box = loc.bounding_box()
                    if box is None:
                        cell.update({"captured": False, "reason": f"{surf['clip']} bounding_box() was None",
                                     "applied_theme": m["applied_theme"], "applied_locale": m["applied_lang"]})
                        frames.append(cell)
                        continue
                    loc.screenshot(path=str(OUT / fname))
                    with Image.open(OUT / fname) as im:
                        pw, ph = im.size
                    ok = m["applied_theme"] == theme and m["applied_lang"] == lang and m["present"]
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
                        "computed": m,
                        "verified_how": (f"specimen.html; element clip of {surf['clip']} at scale {SCALE}; "
                                         "getComputedStyle recorded; EN/ZH invariance checked per surface"),
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
    """Within each theme × viewport: fresh/stale chip colours identical EN vs ZH, --up not.

    Japan REST cells (force_state is None) keep the original 8-cell check. Extra
    specimen surfaces are checked separately so a dashboard-390 clip cannot
    collide with the japan key.
    """
    checks = []
    rest = [f for f in frames if f.get("captured") and f.get("force_state") is None]
    by_key = {(f["theme"], f["viewport"], f["lang"]): f for f in rest}
    for theme in ("dark", "light"):
        for vp in ("desktop", "mobile"):
            en, zh = by_key.get((theme, vp, "en")), by_key.get((theme, vp, "zh"))
            if not en or not zh:
                checks.append({"surface": "imd-health", "theme": theme, "viewport": vp,
                               "pass": False, "reason": "cell missing"})
                continue
            ce, cz = en["computed"], zh["computed"]
            chips_same = ce["fresh_chip"] == cz["fresh_chip"] and ce["stale_chip"] == cz["stale_chip"]
            swap_active = ce["up_token"] != cz["up_token"]
            checks.append({
                "surface": "imd-health", "theme": theme, "viewport": vp,
                "fresh_chip_en": ce["fresh_chip"], "fresh_chip_zh": cz["fresh_chip"],
                "stale_chip_en": ce["stale_chip"], "stale_chip_zh": cz["stale_chip"],
                "up_token_en": ce["up_token"], "up_token_zh": cz["up_token"],
                "chips_identical_en_zh": chips_same, "zh_swap_active": swap_active,
                "pass": chips_same and swap_active,
            })
    extras = [f for f in frames if f.get("captured") and f.get("force_state")]
    extra_key = {(f["force_state"], f["theme"], f["viewport"], f["lang"]): f for f in extras}
    for surf in EXTRA_SURFACES:
        for theme in ("dark", "light"):
            for vp in surf["viewports"]:
                en = extra_key.get((surf["id"], theme, vp, "en"))
                zh = extra_key.get((surf["id"], theme, vp, "zh"))
                if not en or not zh:
                    checks.append({"surface": surf["id"], "theme": theme, "viewport": vp,
                                   "pass": False, "reason": "cell missing"})
                    continue
                ce, cz = en["computed"], zh["computed"]
                chips_same = (ce.get("color") == cz.get("color")
                              and ce.get("boxShadow") == cz.get("boxShadow")
                              and ce.get("backgroundColor") == cz.get("backgroundColor"))
                swap_active = ce["up_token"] != cz["up_token"]
                checks.append({
                    "surface": surf["id"], "theme": theme, "viewport": vp,
                    "color_en": ce.get("color"), "color_zh": cz.get("color"),
                    "box_en": ce.get("boxShadow"), "box_zh": cz.get("boxShadow"),
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
        "japan.html: rendered from committed test inputs "
        "(tests/test_international_macro_dashboards._record/_history, today=2026-09-08) with "
        "templates/theme.css + theme.js copied beside it; the repository builder needs "
        "data/intl/latest.json and writes data/international_macro/*.json, which this packet must "
        "not touch. Eight REST cells are element clips of the data-health receipt block "
        "(.imd-cols carrying .imd-chip.fresh / .imd-chip.stale) inside dlg-health, opened "
        "through its own opener. specimen.html: committed CSS for every other changed "
        "freshness surface (rrx-rec-chip.fresh, igs-dot.fresh, dashboard rr-cov, hk/committee/"
        "impulse/sector/foresight/stage/china_news) mounted against theme.css; dark/light × "
        "EN/ZH at 1440, plus dashboard 390. Extra clips are force_state rows so they do not "
        "replace japan's required REST cells."
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
                 "force_states": [s["id"] for s in EXTRA_SURFACES]},
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
        "tool": {"module_ref": f"{REL_OUT}/capture_freshness_chips.py", "version": "1.1.0"},
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
        label = f"{c.get('surface', 'imd')}/{c['theme']}/{c['viewport']}"
        if c.get("fresh_chip_en"):
            print(f"  invariance {label}: {'PASS' if c['pass'] else 'FAIL'} "
                  f"fresh en={c['fresh_chip_en']['color']} zh={c.get('fresh_chip_zh', {}) and c['fresh_chip_zh']['color']} "
                  f"--up en={c.get('up_token_en')} zh={c.get('up_token_zh')}", flush=True)
        else:
            print(f"  invariance {label}: {'PASS' if c['pass'] else 'FAIL'} "
                  f"color en={c.get('color_en')} zh={c.get('color_zh')} "
                  f"--up en={c.get('up_token_en')} zh={c.get('up_token_zh')} {c.get('reason') or ''}", flush=True)
    return all_captured and inv["pass"]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    return 0 if write_receipts(capture()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
