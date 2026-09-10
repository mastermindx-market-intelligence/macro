"""Capture Macro Command P5 §10 evidence frames.

Theme and language are set BEFORE load. 390/768 frames go through a
same-width iframe harness. HTTP servers start in the background and are
always killed.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.capture_macro_command_p3 import (  # noqa: E402
    RAIL_VIEWPORT_JS,
    _assert_shot_geometry,
    _crop_box,
    _device_px,
    _device_px_span,
    _device_px_span_from_crop_box_doc,
    _measure_dpr,
    _read_scroll,
    _write_element_shot,
)
from scripts.macro_command_capture_guards import (  # noqa: E402
    GEOMETRY_TOLERANCE_PX,
    CaptureContentClippedError,
    CaptureGeometryError,
    _assert_crop_geometry,
    _boxes_intersect,
    _filter_locale_nodes,
    _judge_occlusion,
    grid_sample_points,
    y_coverage,
)

# Sanctioned horizontal scrollers — selector → {kind, covering_family, reason}.
# Loaded from mockups/evidence/macro-command-p5/sanctioned_scrollers.yml.
# No family allowlist: every crop cell enforces the registry (E-B1 / C-B1).
# Alias rows collapse into the one observed selector. A row with
# observed: false is excluded from covering claims (E-n2 / C-m1).
#
# Receipt text fields store DOM innerText (title-case, e.g. "Component Raw").
# CSS `text-transform: uppercase` paints the glyphs as COMPONENT/RAW/...;
# assertions compare casefold() of the DOM text (E-n5). Never store the
# CSS-transformed string.
TEXT_RECEIPT_PATHS = {
    "element": "_element_text_independent",
    "visible": "_locale_visible_text",
}
SANCTIONED_SCROLLERS_PATH = (
    ROOT / "mockups" / "evidence" / "macro-command-p5" / "sanctioned_scrollers.yml"
)
_SANCTIONED_SCROLLERS: dict[str, dict[str, Any]] | None = None


def _load_sanctioned_scrollers() -> dict[str, dict[str, Any]]:
    global _SANCTIONED_SCROLLERS
    if _SANCTIONED_SCROLLERS is not None:
        return _SANCTIONED_SCROLLERS
    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None
    text = SANCTIONED_SCROLLERS_PATH.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
    else:
        # Minimal fallback: parse "selector:" keys with nested kind/covering_family/reason.
        data = {}
        cur = None
        for line in text.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not line.startswith(" ") and line.rstrip().endswith(":"):
                cur = line.rstrip()[:-1].strip().strip('"').strip("'")
                data[cur] = {}
            elif cur is not None and ":" in line:
                k, _, v = line.strip().partition(":")
                v = v.strip().strip('"').strip("'")
                if v == ">|" or v == ">-":
                    continue
                if k in {"kind", "covering_family", "reason"} and v:
                    data[cur][k] = (data[cur].get(k, "") + " " + v).strip()
                elif k == "observed":
                    data[cur][k] = v.lower() not in {"false", "0", "no"}
    out: dict[str, dict[str, Any]] = {}
    for sel, meta in (data or {}).items():
        if not isinstance(meta, Mapping):
            continue
        kind = str(meta.get("kind") or "").strip()
        covering = str(meta.get("covering_family") or "").strip()
        reason = str(meta.get("reason") or "").strip()
        if "observed" in meta:
            raw_obs = meta.get("observed")
            if isinstance(raw_obs, str):
                observed = raw_obs.strip().lower() not in {"false", "0", "no", ""}
            else:
                observed = bool(raw_obs)
        else:
            observed = True
        if kind not in {"designed-rail", "table"} or not covering or len(reason) < 12:
            raise RuntimeError(
                f"sanctioned_scrollers.yml: invalid entry {sel!r}: {meta!r}")
        out[str(sel)] = {
            "kind": kind,
            "covering_family": covering,
            "reason": reason,
            "observed": observed,
        }
    if not out:
        raise RuntimeError(f"empty sanctioned scrollers registry: {SANCTIONED_SCROLLERS_PATH}")
    _SANCTIONED_SCROLLERS = out
    return out


def _registry_match_selector(sel: str) -> str | None:
    """Return the registry key that matches ``sel``, or None."""
    registry = _load_sanctioned_scrollers()
    if sel in registry:
        return sel
    # Compact tables often emit table.mq-table.mq-table-compact — match longest key.
    best = None
    for key in registry:
        if (
            sel == key
            or sel.startswith(key + ".")
            or sel.startswith(key + ":")
            or sel.startswith(key + "[")
            or key in sel.split()
        ):
            if best is None or len(key) > len(best):
                best = key
        # class-token containment: "table.mq-table.mq-table-compact" vs ".mq-table"
        if key.startswith(".") and key[1:] in sel.replace(".", " ").split():
            if best is None or len(key) > len(best):
                best = key
        if key.startswith("#") and sel == key:
            best = key
    return best


SITE = ROOT / "site"
EVIDENCE = ROOT / "mockups" / "evidence" / "macro-command-p5"
MANIFEST = EVIDENCE / "manifest.json"
PROBES = EVIDENCE / "probes.json"
RECEIPT = EVIDENCE / "EVIDENCE.yml"

HUB_DETAILS = (
    "Details, methods and sources",
    "细节、方法与来源",
)
# Locale-visible relocated §5 / B1 strings. Chromium `innerText` hides
# closed <details> and the inactive .l-en/.l-zh span, so each needle must
# be present in the OPEN ribbon and in the active language.
RELOCATED_EN = (
    "What this state implies",
    "Deterministic text from the accepted snapshot. No language model writes here.",
    "Confidence basis",
)
RELOCATED_ZH = (
    "该状态意味着什么",
    "文本由已接受快照确定性生成，此处不由语言模型撰写。",
    "置信度依据",
)
# 15/16 already capture these two open-ribbon states; do not recapture
# them as workspace rows (identical sha256 is an M1 defect).
_SKIP_WS_DUP = {
    ("macro_rates_curves.html", "open", "dark", "en"),
    ("macro_rates_curves.html", "open", "dark", "zh"),
    ("macro_rates_curves.html", "open", "light", "en"),
    ("macro_rates_curves.html", "open", "light", "zh"),
}
WORKSPACE_PAGES = (
    "macro_rates_curves.html",
    "macro_business_activity.html",
    "macro_financial_conditions.html",
    "macro_housing_real_estate.html",
)
# Honest labor page entry (option a): own rest matrix + method_open + health.
# Not folded into WORKSPACE_PAGES so chipmat/i2/clearance stay on the four
# already-probed workspaces; rest census only needs the 8 rest cells.
LABOR_PAGE = "macro_labor_markets.html"
METHOD_OPEN_PAGES = (
    "macro_financial_conditions.html",
    LABOR_PAGE,
)
# method_table_390 covers every page that reports table.mq-table at 390
# (E-M1 / C-M1). METHOD_OPEN_PAGES is the composition-law crop set; the
# table family is the five workspace+labor pages that overflow the table.
METHOD_TABLE_PAGES = WORKSPACE_PAGES + (LABOR_PAGE,)
_METHOD_TABLE_NAME_RE = re.compile(
    r"^method_table_390_(?P<pos>start|end)-"
    r"(?P<slug>.+?)(?:__(?P<element_key>[A-Za-z0-9_.-]+))?"
    r"-(?P<theme>dark|light)-(?P<locale>en|zh)-(?P<width>\d+)\.png$"
)
_METHOD_TABLE_PROBE_RE = re.compile(
    r"^method_table_390-(.+?)(?:__([A-Za-z0-9_.-]+))?-"
    r"(dark|light)-(en|zh)-(\d+)$"
)


def method_table_filename(
        pos: str, slug: str, theme: str, locale: str, width: int | str = 390,
        *, element_key: str) -> str:
    key = str(element_key or "").strip()
    if not key:
        raise RuntimeError("method_table filename requires element_key")
    return (
        f"method_table_390_{pos}-{slug}__{key}-"
        f"{theme}-{locale}-{width}.png"
    )


def parse_method_table_name(name: str) -> dict[str, str] | None:
    m = _METHOD_TABLE_NAME_RE.match(name)
    if not m:
        return None
    return {k: (v or "") for k, v in m.groupdict().items()}


METHOD_OPEN_SELECTOR = "section.mq-method"  # E-n1: section with padding, every cell
METHOD_OPEN_DETAILS = "section.mq-method details.mc-details"
# True container for Changed fingerprints / Hysteresis / lineage sentence
# (NOT section.mq-method — Method version / Owner / Trace live elsewhere;
# see claims NOT DONE-AS-WRITTEN).
LINEAGE_OPEN_PAGES = (
    "macro_financial_conditions.html",
    "macro_monetary_policy.html",
)
LINEAGE_OPEN_SELECTOR = "section.mq-lineage"
LINEAGE_OPEN_DETAILS = "section.mq-lineage details.mc-details"
# Method version / Owner / Trace live in Technical-notes + station cards.
DISCLOSURE_ROWS_PAGES = (
    "macro_financial_conditions.html",
    "macro_monetary_policy.html",
)
DISCLOSURE_ROWS_SELECTOR = (
    "details.mc-details.open, dl.mq-headline-meta, p.mq-owner, p.mq-trace"
)
FIVE_PAGES = ("macro_monetary.html",) + WORKSPACE_PAGES
HUB_PAGE = "macro_monetary.html"
CHIP_MATERIAL_WIDTHS = (1440, 768, 390)
CLEARANCE_TEXT = (
    "p, .mc-stance, .mc-caption, .mc-move-row, .mc-watch, "
    ".mc-primer, .mc-foot, li, td"
)

SERVERS: list[subprocess.Popen] = []


class PageOverflowError(RuntimeError):
    """Document-level horizontal overflow (C-M1 / E-M3)."""

    def __init__(self, route: str, width: int, scroll_width: float) -> None:
        self.route = route
        self.width = width
        self.scroll_width = scroll_width
        super().__init__(
            f"PageOverflowError(route={route!r}, width={width}, "
            f"scroll_width={scroll_width})")




def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _serve(root: Path) -> tuple[subprocess.Popen, str]:
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    SERVERS.append(proc)
    print(f"http.server pid={proc.pid} cwd={root} port={port}", flush=True)
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                break
        except OSError:
            if proc.poll() is not None:
                raise RuntimeError(f"http.server exited {proc.returncode}")
            time.sleep(0.1)
    return proc, f"http://127.0.0.1:{port}"


def _kill_all() -> None:
    for proc in SERVERS:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
    SERVERS.clear()


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def _write_harness(root: Path, *, src: str, width: int, height: int,
                   caption: str | None) -> str:
    name = f"_p5_harness_{width}.html"
    cap = caption or src
    (root / name).write_text(
        "<!doctype html><html><head><meta charset='utf-8'></head>"
        "<body style='margin:0;background:#111'>"
        f"<div id='mc-p5-url' style='font:12px/20px ui-monospace,monospace;"
        f"padding:6px 10px;background:#111;color:#eee'>{cap}</div>"
        f"<iframe id='mc-p5-frame' src='{src}' "
        f"style='display:block;width:{width}px;height:{height}px;border:0;"
        f"background:#000'></iframe></body></html>",
        encoding="utf-8",
    )
    return name


def _open(*, browser, origin: str, path: str, theme: str, locale: str,
          width: int, height: int, iframe_width: int | None = None,
          caption: str | None = None, harness_root: Path | None = None):
    context = browser.new_context(
        viewport={"width": width, "height": height},
        device_scale_factor=2,
        color_scheme=theme,
        reduced_motion="reduce",
        locale="zh-CN" if locale == "zh" else "en-US",
    )
    # Clean storage per shot (E-n3): no residue from prior captures (e.g. NVDA
    # in the global search field). Theme/lang are re-seeded by the init script.
    context.add_init_script(
        f"""(() => {{
            try {{ localStorage.clear(); sessionStorage.clear(); }} catch (e) {{}}
            localStorage.setItem('theme', {theme!r});
            localStorage.removeItem('themeAuto');
            localStorage.setItem('lang', {locale!r});
            document.documentElement.setAttribute('data-theme', {theme!r});
            document.documentElement.setAttribute('data-lang', {locale!r});
        }})();"""
    )
    page = context.new_page()
    if iframe_width:
        harness = _write_harness(
            harness_root or SITE, src=path, width=iframe_width,
            height=height - 28, caption=caption)
        page.goto(origin + "/" + harness, wait_until="domcontentloaded",
                  timeout=30000)
        frame = page.frame_locator("#mc-p5-frame")
        frame.locator("html").wait_for(timeout=20000)
        # Clear again inside the iframe document after load.
        try:
            frame.locator("html").evaluate(
                """() => { try { localStorage.clear(); sessionStorage.clear(); } catch (e) {} }"""
            )
            frame.locator("html").evaluate(
                f"""() => {{
                    localStorage.setItem('theme', {theme!r});
                    localStorage.setItem('lang', {locale!r});
                    document.documentElement.setAttribute('data-theme', {theme!r});
                    document.documentElement.setAttribute('data-lang', {locale!r});
                }}"""
            )
        except Exception:
            pass
        page.wait_for_timeout(400)
        return context, page, frame
    page.goto(origin + path, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_function(
        """([theme, locale]) => {
            const el = document.documentElement;
            return el.getAttribute('data-theme') === theme
                && (el.getAttribute('data-lang') || 'en') === locale;
        }""",
        arg=[theme, locale],
        timeout=10000,
    )
    return context, page, None


def _measure_window(target) -> dict[str, Any]:
    return target.evaluate(
        """() => ({
            innerWidth: window.innerWidth,
            innerHeight: window.innerHeight,
            scrollY: window.scrollY || document.documentElement.scrollTop || 0,
            scrollWidth: document.documentElement.scrollWidth,
            scrollHeight: document.documentElement.scrollHeight,
        })"""
    )


def family_for(filename: str) -> str:
    name = filename[:-4] if filename.endswith(".png") else filename
    if name.startswith("chipmat-"):
        return "chip_material"
    if name.startswith("hubrail-"):
        return "hub_rail"
    if name.startswith("ws-"):
        return "workspace"
    if name.startswith("i2-"):
        return "i2"
    if name.startswith("e5-"):
        return "e5"
    if name.startswith("half-") or name.startswith(("18-", "18b-", "19-", "19b-")):
        return "half_null"
    if name.startswith("method_open-"):
        return "method_open"
    if name.startswith("method_table_390_"):
        return "method_table_390"
    if name.startswith("lineage_open-"):
        return "lineage_open"
    if name.startswith("disclosure_rows_open-"):
        return "disclosure_rows_open"
    if name.startswith(("15-", "15b-", "16-", "16b-")):
        return "details_open"
    if name.startswith("17"):
        return "read_word"
    if name.endswith("-1440-full"):
        return "hub_full"
    if name.startswith(("05-", "06-", "07-", "08-")):
        return "rates_panel"
    if name.startswith(("09-", "10-", "11-", "12-")):
        return "hub_390"
    if name.startswith(("13-", "13b-", "14-", "14b-")):
        return "hub_768"
    if name.startswith(("01-", "02-", "03-", "04-")):
        return "hub_fold"
    return "other"


def _viewport_shot(dest: Path, page, *, width: int, height: int,
                   full_page: bool = False) -> dict[str, Any]:
    dpr = _measure_dpr(page)
    win = _measure_window(page)
    page.screenshot(path=str(dest), type="png", full_page=full_page)
    png = dest.read_bytes()
    if png[:8] != b"\x89PNG\r\n\x1a\n" or b"IEND" not in png:
        raise RuntimeError(f"{dest.name} is not a finished PNG")
    pw, ph = _png_size(dest)
    raw_box = {
        "x": 0.0, "y": 0.0,
        "width": float(win["innerWidth"]),
        "height": float(win["innerHeight"]),
    }
    extra: dict[str, Any] = {
        "dpr": dpr,
        "crop": False,
        "full_page": full_page,
        "crop_box": None,
        "crop_selector": None,
        "raw_box": raw_box,
        "shot_route": _shot_route_of(page),
        "innerWidth": win["innerWidth"],
        "innerHeight": win["innerHeight"],
        "scroll_y_at_shot": win["scrollY"],
        "scrollWidth": win["scrollWidth"],
        "scrollHeight": win["scrollHeight"],
        "fixture": "builder-payload",
        # E-m1: blank canvas lives on non-crop viewport/full-page cells.
        "painted_fraction": _painted_fraction(dest),
    }
    if full_page:
        expect_w = _device_px(0.0, float(win["scrollWidth"]), dpr)
        expect_h = _device_px(0.0, float(win["scrollHeight"]), dpr)
        extra["device_px_span"] = _device_px_span(
            {"x": 0.0, "y": 0.0, "width": float(win["scrollWidth"]),
             "height": float(win["scrollHeight"])},
            dpr)
        extra["ihdr_delta_px"] = {"w": abs(pw - expect_w), "h": abs(ph - expect_h)}
        if (pw, ph) != (expect_w, expect_h):
            raise RuntimeError(
                f"{dest.name} full-page IHDR {pw}x{ph} != document "
                f"{win['scrollWidth']}x{win['scrollHeight']}×{dpr} "
                f"= {expect_w}x{expect_h}")
    else:
        expect_w = int(round(float(win["innerWidth"]) * dpr))
        expect_h = int(round(float(win["innerHeight"]) * dpr))
        extra["device_px_span"] = _device_px_span(
            {"x": 0.0, "y": 0.0, "width": float(win["innerWidth"]),
             "height": float(win["innerHeight"])},
            dpr)
        extra["ihdr_delta_px"] = {"w": abs(pw - expect_w), "h": abs(ph - expect_h)}
        if (pw, ph) != (expect_w, expect_h):
            raise RuntimeError(
                f"{dest.name} IHDR {pw}x{ph} != round(inner "
                f"{win['innerWidth']}x{win['innerHeight']}×{dpr}) "
                f"= {expect_w}x{expect_h}")
    return {
        **extra,
        "bytes": len(png),
        "sha256": hashlib.sha256(png).hexdigest(),
        "width": pw,
        "height": ph,
    }


_SCROLL_RAIL_CHIP_JS = """() => {
  const boxOf = (el) => {
    const r = el.getBoundingClientRect();
    return {left: r.left, right: r.right, top: r.top, bottom: r.bottom,
            x: r.x, y: r.y, width: r.width, height: r.height};
  };
  const identifyingSelector = (el) => {
    if (!el) return '';
    if (el.id) return '#' + el.id;
    const tag = (el.tagName || '').toLowerCase();
    const href = el.getAttribute('href');
    const ws = el.getAttribute('data-mq-workspace');
    let sel = tag;
    if (el.classList.contains('mc-analyst')) sel += '.mc-analyst';
    else if (el.classList.contains('mq-suitenav-pill')) sel += '.mq-suitenav-pill';
    if (href) sel += '[href="' + href + '"]';
    if (ws) sel += '[data-mq-workspace="' + ws + '"]';
    if (el.hasAttribute('data-mc-analyst')) sel += '[data-mc-analyst]';
    if (sel === tag || sel === (tag + '.mq-suitenav-pill')) {
      const chain = [];
      let node = el;
      while (node && node.nodeType === 1 && chain.length < 8) {
        const parent = node.parentElement;
        if (!parent) break;
        const kids = Array.from(parent.children).filter(
          (c) => c.tagName === node.tagName);
        chain.unshift(node.tagName.toLowerCase() + ':nth-of-type('
                      + (kids.indexOf(node) + 1) + ')');
        if (parent.id) { chain.unshift('#' + parent.id); break; }
        node = parent;
      }
      sel = chain.join('>');
    }
    return sel;
  };
  const visibleText = (el) => String((el && el.innerText) || '')
    .replace(/\\s+/g, ' ').trim();
  const overflowScrollableX = (el) => {
    const ox = getComputedStyle(el).overflowX;
    return (ox === 'auto' || ox === 'scroll')
      && el.scrollWidth > el.clientWidth + 1;
  };
  const chip = document.querySelector('.mc-analyst');
  const item = chip && chip.closest('li');
  const prev = (item && item.previousElementSibling)
    ? item.previousElementSibling.querySelector(
        '.mq-suitenav-pill, .mc-rail-link')
    : document.querySelector('.mq-suitenav-pill:not(.mc-analyst)');
  const rail = document.querySelector('.mq-suitenav-rail');
  if (!chip || !prev) {
    return {ok: false, reason: 'missing rail/chip/pill',
            railScrollLeft: 0, scrollLeftBefore: 0, scrollLeftAfter: 0,
            chipSelector: identifyingSelector(chip),
            siblingPillSelector: identifyingSelector(prev),
            chipLabel: visibleText(chip),
            siblingPillLabel: visibleText(prev),
            railInnerHtml: rail ? rail.innerHTML : ''};
  }
  let scroller = null;
  let walk = chip.parentElement;
  while (walk && walk !== document.documentElement) {
    if (overflowScrollableX(walk)) { scroller = walk; break; }
    walk = walk.parentElement;
  }
  if (!scroller) {
    walk = chip.parentElement;
    while (walk && walk !== document.documentElement) {
      const ox = getComputedStyle(walk).overflowX;
      if (ox === 'auto' || ox === 'scroll') { scroller = walk; break; }
      walk = walk.parentElement;
    }
  }
  if (!scroller) {
    return {ok: false, reason: 'no scroll container',
            railScrollLeft: 0, scrollLeftBefore: 0, scrollLeftAfter: 0,
            chipSelector: identifyingSelector(chip),
            siblingPillSelector: identifyingSelector(prev),
            chipLabel: visibleText(chip),
            siblingPillLabel: visibleText(prev),
            railInnerHtml: rail ? rail.innerHTML : ''};
  }
  const scrollLeftBefore = scroller.scrollLeft;
  chip.scrollIntoView({inline: 'end', block: 'nearest'});
  let scR = scroller.getBoundingClientRect();
  let chipR = chip.getBoundingClientRect();
  let prevR = prev.getBoundingClientRect();
  const pairWidth = Math.max(chipR.right, prevR.right)
    - Math.min(chipR.left, prevR.left);
  const containerWidth = scroller.clientWidth;
  const chipmatPairFits = pairWidth <= containerWidth - 4;
  if (chipmatPairFits) {
    if (prevR.left < scR.left + 1) {
      scroller.scrollLeft += (prevR.left - scR.left) - 8;
    }
    chipR = chip.getBoundingClientRect();
    prevR = prev.getBoundingClientRect();
    scR = scroller.getBoundingClientRect();
    if (chipR.right > scR.right - 1) {
      scroller.scrollLeft += (chipR.right - scR.right) + 8;
    }
    chipR = chip.getBoundingClientRect();
    prevR = prev.getBoundingClientRect();
    scR = scroller.getBoundingClientRect();
    if (prevR.left < scR.left + 1) {
      scroller.scrollLeft += (prevR.left - scR.left) - 8;
    }
  }
  const containerBox = boxOf(scroller);
  const analystBox = boxOf(chip);
  const pillBox = boxOf(prev);
  const pairLeft = chipmatPairFits
    ? Math.min(analystBox.left, pillBox.left) : analystBox.left;
  const pairRight = chipmatPairFits
    ? Math.max(analystBox.right, pillBox.right) : analystBox.right;
  const pairTop = chipmatPairFits
    ? Math.min(analystBox.top, pillBox.top) : analystBox.top;
  const pairBottom = chipmatPairFits
    ? Math.max(analystBox.bottom, pillBox.bottom) : analystBox.bottom;
  const pad = 12;
  const clipLeft = Math.max(containerBox.left, pairLeft - pad);
  const clipRight = Math.min(containerBox.right, pairRight + pad);
  const clipTop = Math.max(containerBox.top, pairTop - pad);
  const clipBottom = Math.min(containerBox.bottom, pairBottom + pad);
  const cropBox = {
    x: clipLeft, y: clipTop,
    width: Math.max(1, clipRight - clipLeft),
    height: Math.max(1, clipBottom - clipTop),
    left: clipLeft, right: clipRight, top: clipTop, bottom: clipBottom,
  };
  const intersects = (a, b) => !(a.right <= b.left || a.left >= b.right
    || a.bottom <= b.top || a.top >= b.bottom);
  const candidates = [];
  document.querySelectorAll('*').forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return;
    if (!intersects(r, cropBox)) return;
    candidates.push(el);
  });
  const keep = candidates.filter((el) => {
    const cls = String(el.className || '');
    if (/(mq-suitenav-pill|mc-analyst|mq-suitenav-analyst)/.test(cls)) {
      return true;
    }
    return !candidates.some((other) => other !== el && el.contains(other));
  });
  const cropDomHtml = keep.map((el) => el.outerHTML).join('\\n');
  const chipLabel = visibleText(chip);
  const siblingPillLabel = visibleText(prev);
  return {
    ok: true,
    reason: '',
    scrollContainerSelector: identifyingSelector(scroller),
    scrollLeftBefore,
    scrollLeftAfter: scroller.scrollLeft,
    railScrollLeft: scroller.scrollLeft,
    chipSelector: identifyingSelector(chip),
    siblingPillSelector: identifyingSelector(prev),
    chipLabel,
    siblingPillLabel,
    elementTextHead: (chipLabel + ' ' + siblingPillLabel).trim(),
    analystBox,
    siblingPillBox: pillBox,
    containerBox,
    cropBox,
    chipmatPairFits,
    pairWidth,
    containerWidth,
    railInnerHtml: rail ? rail.innerHTML : scroller.innerHTML,
    cropDomHtml,
  };
}"""

_PREPARE_I2_JS = """() => {
    const max = Math.max(
        0, document.documentElement.scrollHeight - window.innerHeight);
    window.scrollTo(0, max);
    let opened = false;
    if ((window.scrollY || 0) < 2) {
        const details = document.querySelector(
            '#mq-context details, .mq-context details.mc-details');
        if (details && !details.open) {
            details.open = true;
            opened = true;
        }
    }
    return {scrollY: window.scrollY || 0, max, opened};
}"""


def _host_frame_offset(page, frame) -> dict[str, float]:
    """Measured #mc-p5-frame origin in the host viewport. Never a literal."""
    if frame is None:
        return {"x": 0.0, "y": 0.0}
    host = page.locator("#mc-p5-frame").bounding_box()
    if not host:
        raise RuntimeError("chipmat iframe has no box")
    return {"x": float(host["x"]), "y": float(host["y"])}


def _to_host_page(
        box: Mapping[str, Any] | None, offset: Mapping[str, float],
        host_scroll_y: float) -> dict[str, float] | None:
    """Translate an iframe-local box into host-page document space."""
    if not box:
        return None
    dx = float(offset["x"])
    dy = float(offset["y"]) + float(host_scroll_y)
    if "left" in box and "right" in box:
        left = float(box["left"]) + dx
        top = float(box["top"]) + dy
        width = float(box.get("width") or (float(box["right"]) - float(box["left"])))
        height = float(box.get("height") or (float(box["bottom"]) - float(box["top"])))
        return {
            "left": left, "right": left + width,
            "top": top, "bottom": top + height,
            "x": left, "y": top, "width": width, "height": height,
        }
    x = float(box["x"]) + dx
    y = float(box["y"]) + dy
    width = float(box["width"])
    height = float(box["height"])
    return {
        "left": x, "right": x + width,
        "top": y, "bottom": y + height,
        "x": x, "y": y, "width": width, "height": height,
    }


def _page_space_clip(page, frame, clip: Mapping[str, Any]) -> dict[str, float]:
    """Translate an iframe-local clip into the parent page viewport."""
    box = {
        "x": float(clip["x"]),
        "y": float(clip["y"]),
        "width": float(clip["width"]),
        "height": float(clip["height"]),
    }
    offset = _host_frame_offset(page, frame)
    return {
        "x": offset["x"] + box["x"],
        "y": offset["y"] + box["y"],
        "width": box["width"],
        "height": box["height"],
    }




def _shot(dest: Path, page, locator, *, selector: str,
          locale: str = "en") -> dict[str, Any]:
    """Crop shot via the single guarded path (C-M3).

    Iframe harness crops photograph ``#mc-p5-frame`` on the host page but
    collect overflow/text/occlusion from the iframe body.
    """
    vw = int(round(float((page.viewport_size or {}).get("width") or 1440)))
    receipt = None
    shoot = locator
    shoot_sel = selector
    if selector == "#mc-p5-frame":
        frame = page.frame_locator("#mc-p5-frame")
        receipt = frame.locator("body")
        if receipt.count() != 1:
            raise RuntimeError(
                f"{dest.name}: crop_selector 'body' (iframe) "
                f"matched {receipt.count()}")
        receipt = receipt.first
        receipt.wait_for(state="attached", timeout=15000)
        shoot = page.locator("#mc-p5-frame")
        n = shoot.count()
        if n != 1:
            raise RuntimeError(
                f"{dest.name}: crop_selector '#mc-p5-frame' matched {n}")
        shoot_sel = "#mc-p5-frame"
    else:
        n = page.locator(selector).count()
        if n != 1:
            raise RuntimeError(
                f"{dest.name}: crop_selector {selector!r} matched {n} "
                "(must be exactly one; tighten the selector — never .first)")
        shoot = page.locator(selector)
        shoot_sel = selector
    return _element_shot_guarded(
        dest, page, shoot, selector=shoot_sel, locale=locale,
        viewport_width=vw, target_for_nav=page,
        receipt_locator=receipt,
    )



def _occlusion_samples_in_iframe(
        page, body_locator, host_box: Mapping[str, Any],
        ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """15-pt occlusion inside an iframe document (E-M2).

    Sample the iframe viewport ∩ body (never a scrolled-off body band).
    Host_box is the iframe element rect on the host page.
    """
    inset = 4.0
    metrics = body_locator.evaluate(
        """el => {
            const doc = el.ownerDocument || document;
            const win = doc.defaultView || window;
            const r = el.getBoundingClientRect();
            const iw = win.innerWidth, ih = win.innerHeight;
            const top = Math.max(r.top, 0);
            const left = Math.max(r.left, 0);
            const bottom = Math.min(r.bottom, ih);
            const right = Math.min(r.right, iw);
            return {
              x: left, y: top,
              width: Math.max(0, right - left),
              height: Math.max(0, bottom - top),
              iw, ih,
              bodyH: r.height,
            };
        }"""
    )
    sample_box = {
        "x": float(metrics["x"]),
        "y": float(metrics["y"]),
        "width": float(metrics["width"]),
        "height": float(metrics["height"]),
    }
    if sample_box["width"] < 8 or sample_box["height"] < 8:
        # Fall back to the full iframe viewport.
        sample_box = {
            "x": 0.0, "y": 0.0,
            "width": float(metrics["iw"]),
            "height": float(metrics["ih"]),
        }
    tall = float(metrics["bodyH"]) > float(metrics["ih"]) + 0.5
    pts = grid_sample_points(sample_box, inset=inset)
    samples = body_locator.evaluate(
        """(el, pts) => {
            const doc = el.ownerDocument || document;
            const win = doc.defaultView || window;
            const root = doc.documentElement || el;
            const out = [];
            for (const [x, y] of pts) {
                if (x < 1 || y < 1 || x > win.innerWidth - 1
                    || y > win.innerHeight - 1) {
                    out.push({x, y, ok: false, hitSelector: 'off-viewport'});
                    continue;
                }
                const hit = doc.elementFromPoint(x, y);
                let cur = hit;
                let inside = false;
                while (cur) {
                    if (cur === el || cur === root || cur === doc.body
                        || (el.contains && el.contains(cur))
                        || (root.contains && root.contains(cur))) {
                        inside = true; break;
                    }
                    cur = cur.parentElement;
                }
                let hitSelector = null;
                if (hit) {
                    hitSelector = hit.id ? ('#' + hit.id)
                        : (hit.className && typeof hit.className === 'string'
                            ? (hit.tagName.toLowerCase() + '.'
                               + String(hit.className).trim().split(/\\s+/)
                                 .slice(0, 3).join('.'))
                            : hit.tagName.toLowerCase());
                }
                if (hitSelector === '#mc-p5-frame' || hitSelector === 'iframe') {
                    inside = false;
                }
                out.push({x, y, ok: inside, hitSelector});
            }
            return out;
        }""",
        pts,
    )
    judged = _judge_occlusion(samples)
    meta = {
        "samples_span": "crop",
        "y_coverage": y_coverage(judged, sample_box),
        "occlusion_sample_box": sample_box,
        "host_box": dict(host_box),
        "grid": "full",
    }
    return judged, meta



def _state(filename: str, theme: str, locale: str, viewport: str,
           info: dict[str, Any], *, verified_how: str,
           viewport_width: int, fixture: bool | str | None = None,
           force_state: str | None = None, crop: bool = False,
           selector: str | None = None, dpr: float = 2.0,
           viewport_height: int | None = None,
           trigger: str | None = None,
           family: str | None = None) -> dict[str, Any]:
    measured_dpr = float(info.get("dpr") or dpr)
    ihdr_w = int(info["width"])
    ihdr_h = int(info["height"])
    css_w = ihdr_w / measured_dpr
    is_crop = bool(crop or info.get("crop_box"))
    declared = int(viewport_width)
    crop_box = info.get("crop_box") if is_crop else None
    crop_width = (
        float(crop_box["width"]) if isinstance(crop_box, Mapping) else None)
    crop_selector = info.get("crop_selector") if is_crop else None
    if is_crop:
        crop_selector = crop_selector or selector
        if not crop_selector:
            raise RuntimeError(
                f"{filename}: crop:true missing crop_selector at shot time")
    if viewport_height is not None:
        vh = viewport_height
    elif info.get("innerHeight") is not None:
        vh = int(round(float(info["innerHeight"])))
    else:
        vh = 2200 if viewport == "desktop" else 844
    row = {
        "access": "anonymous",
        "applied_locale": locale,
        "applied_theme": theme,
        "bytes": info["bytes"],
        "captured": True,
        "file": filename,
        "family": family or family_for(filename),
        "force_state": force_state,
        "height": ihdr_h,
        "width": ihdr_w,
        "locale": locale,
        "sha256": info["sha256"],
        "theme": theme,
        "viewport": viewport,
        "viewport_width": declared,
        "crop_width": crop_width,
        "viewport_css_width": css_w,
        "viewport_height": vh,
        "dpr": measured_dpr,
        "crop": is_crop,
        "crop_selector": crop_selector,
        "crop_box": info.get("crop_box") if is_crop else None,
        "selector": selector,
        "full_page": bool(info.get("full_page")),
        "device_px_span": info.get("device_px_span"),
        "verified_how": verified_how,
        "fixture": fixture if isinstance(fixture, str) else "builder-payload",
        "trigger": trigger,
    }
    for key in ("crop_box_doc", "scroll_y_at_shot", "ihdr_delta_px",
                "element_text_head", "element_text_sha256",
                "visible_text_head", "visible_text_sha256", "openedBy",
                "occlusionSamples", "shot_route", "page_id",
                "innerWidth", "innerHeight",
                "coordSpace", "hostFrameOffset", "host_scroll_y_at_shot",
                "frameInnerWidth", "frameInnerHeight",
                "analystBox", "siblingPillBox",
                "raw_box", "cropDomSha256",
                "scroll_container_selector", "scrollWidth", "clientWidth",
                "scrollLeft", "overflow_x", "fits",
                "inner_scrollports", "ancestor_scrollports",
                "y_coverage", "samples_span", "grid",
                "receipt_document", "visible_text_at_scroll",
                "visible_text_at_zero", "painted_fraction",
                "occlusion_sample_box", "content_overflows",
                "text_receipt_paths", "shot_viewport",
                "raw_box_in_shot_viewport", "hidden_fixed",
                "shoot_box", "table_fits", "page_fits",
                "page_scroll_width", "matched", "element_key",
                "visible_text_scope", "in_method_section"):
        if info.get(key) is not None:
            row[key] = info[key]
    # content_overflows must be present on every crop (empty list is valid).
    if is_crop and "content_overflows" not in row:
        row["content_overflows"] = list(info.get("content_overflows") or [])
    return row


def _gap_state(filename: str, theme: str, locale: str, viewport: str,
               reason: str, viewport_width: int) -> dict[str, Any]:
    return {
        "access": "anonymous",
        "captured": False,
        "reason": reason,
        "file": filename,
        "family": family_for(filename),
        "theme": theme,
        "locale": locale,
        "viewport": viewport,
        "viewport_width": viewport_width,
    }


def _relocated_needles(locale: str) -> tuple[str, ...]:
    return RELOCATED_ZH if locale == "zh" else RELOCATED_EN


def _box_contains(outer: Mapping[str, float], inner: Mapping[str, float],
                  *, tol: float = 1.0) -> bool:
    return (
        float(inner["x"]) + tol >= float(outer["x"])
        and float(inner["y"]) + tol >= float(outer["y"])
        and float(inner["x"]) + float(inner["width"]) - tol
        <= float(outer["x"]) + float(outer["width"])
        and float(inner["y"]) + float(inner["height"]) - tol
        <= float(outer["y"]) + float(outer["height"])
    )


def _open_method_details_by_click(target, *, host_page) -> str:
    """Real click on the method <details> summary. `target` is page or frame.

    Composition-law rows live under the Drivers tab panel (`data-mq-panel=drivers`);
    that panel starts hidden, so the tab must be selected first.
    """
    drivers_tab = target.locator('[data-mq-tab="drivers"]').first
    drivers_tab.wait_for(state="visible", timeout=15000)
    drivers_tab.click(timeout=15000)
    host_page.wait_for_timeout(120)
    panel = target.locator('[data-mq-panel="drivers"]').first
    panel.wait_for(state="visible", timeout=15000)
    details = target.locator(METHOD_OPEN_DETAILS).first
    details.wait_for(state="visible", timeout=15000)
    details.scroll_into_view_if_needed(timeout=15000)
    summary = details.locator("summary").first
    summary.click(timeout=15000)
    host_page.wait_for_timeout(120)
    opened = bool(details.evaluate("el => el.open"))
    if not opened:
        raise RuntimeError("section.mq-method details did not open on click")
    return "click"


def _assert_method_dl_contained(body) -> None:
    # n5: never .first. The opened axis details holds exactly one dl;
    # the method section itself has one dl per axis.
    dl = body.locator("details.mc-details[open] dl")
    n = dl.count()
    if n != 1:
        raise RuntimeError(
            f"method section open-details dl matched {n} "
            "(must be exactly one; never .first)")
    dl.wait_for(timeout=8000)
    outer = _crop_box(body)
    inner = _crop_box(dl)
    if not _box_contains(outer, inner):
        raise RuntimeError(
            f"method section crop does not contain its dl: {outer} vs {inner}")


# Fixed/sticky chrome that may lawfully intersect a crop (topbar + in-suite nav).
# NOT allowlisted: .site-nav .nav-links (the mobile overlay that r14 painted over
# method_open) — that must still raise via nav-panel ∩ crop and occlusion.
_FIXED_ALLOW_SELECTORS = (
    ".site-nav",
    ".topbar",
    ".nav-toggle",
    ".nav-ctrls",
    ".nav-search",
    "nav.mq-suitenav",
    ".mq-suitenav",
    ".mq-suitenav-rail",
    ".mq-suitenav-pill",
    ".mq-suitenav-label",
    "#mmb-root",
    "#mmb-fab",
)


def _nav_panel_box(target) -> dict[str, Any] | None:
    """Bounding box of an OPEN mobile nav drawer, or None.

    Desktop inline ``.nav-links`` is ordinary chrome (allowlisted via
    ``.site-nav``) — never treat it as the r14 overlay. Only report when the
    suite has ``nav-open`` / a fixed drawer covering content.
    """
    return target.evaluate(
        """() => {
            const nav = document.querySelector(
                '.site-nav, .topbar nav, [data-nav-panel]');
            if (!nav) return null;
            const open = (
                nav.classList.contains('nav-open')
                || document.documentElement.classList.contains('nav-open')
                || document.body.classList.contains('nav-open')
            );
            const links = nav.querySelector('.nav-links') || nav;
            const st = getComputedStyle(links);
            if (st.display === 'none' || st.visibility === 'hidden'
                || Number(st.opacity) === 0) {
                return null;
            }
            // Inline desktop bar: visible but not an overlay.
            if (!open && st.position !== 'fixed' && st.position !== 'absolute') {
                return null;
            }
            if (!open && st.position === 'absolute') {
                // Absolute but still in-header (not a drop-down covering page).
                const r0 = links.getBoundingClientRect();
                if (r0.bottom <= 120 && r0.height < 80) return null;
            }
            const r = links.getBoundingClientRect();
            if (r.width < 2 || r.height < 2) return null;
            return {x: r.left, y: r.top, width: r.width, height: r.height,
                    selector: '.site-nav .nav-links'};
        }"""
    )


def _assert_no_fixed_intersection(
        target, crop_box: Mapping[str, Any],
        allow: Sequence[str] = _FIXED_ALLOW_SELECTORS,
        ) -> list[str]:
    """RAISE if a visible fixed/sticky outside allowlist intersects crop_box.

    Returns ``hidden_fixed`` selectors (display:none / visibility:hidden /
    opacity:0) so the reviewer sees what was closed without a class strip.
    """
    packed = target.evaluate(
        """(args) => {
            const crop = args.crop;
            const allow = args.allow || [];
            const hitAllow = (el) => {
                for (const sel of allow) {
                    try { if (el.matches(sel) || el.closest(sel)) return true; }
                    catch (e) {}
                }
                return false;
            };
            const selOf = (el) => el.id ? ('#' + el.id)
                : (el.className && typeof el.className === 'string'
                    ? (el.tagName.toLowerCase() + '.'
                       + el.className.trim().split(/\\s+/).slice(0, 3).join('.'))
                    : el.tagName.toLowerCase());
            const offenders = [];
            const hidden_fixed = [];
            for (const el of document.querySelectorAll('body *')) {
                const st = getComputedStyle(el);
                if (st.position !== 'fixed' && st.position !== 'sticky') continue;
                if (hitAllow(el)) continue;
                const r = el.getBoundingClientRect();
                if (r.width < 2 || r.height < 2) continue;
                const sel = selOf(el);
                const hidden = (st.display === 'none' || st.visibility === 'hidden'
                    || Number(st.opacity) === 0);
                if (hidden) {
                    hidden_fixed.push(sel);
                    continue;
                }
                const ax0 = r.left, ay0 = r.top, aw = r.width, ah = r.height;
                const bx0 = crop.x, by0 = crop.y, bw = crop.width, bh = crop.height;
                const intersect = !(ax0 + aw <= bx0 || bx0 + bw <= ax0
                    || ay0 + ah <= by0 || by0 + bh <= ay0);
                if (!intersect) continue;
                offenders.push(sel);
                if (offenders.length >= 5) break;
            }
            return {offenders, hidden_fixed};
        }""",
        {"crop": dict(crop_box), "allow": list(allow)},
    ) or {}
    offenders = list(packed.get("offenders") or [])
    hidden_fixed = list(packed.get("hidden_fixed") or [])
    if offenders:
        raise RuntimeError(
            f"fixed/sticky intersection with crop: {offenders}")
    return hidden_fixed


def _scroll_clear_of_chrome(
        target, crop_selector: str, crop_box: Mapping[str, Any], *,
        host_page, viewport_width: int, extra_chrome: str = "") -> list[str]:
    """Scroll the crop clear of sticky/fixed chrome; never hide page chrome.

    C-m2: close a mobile menu ONLY the way a customer does (toggle click or
    Escape). Never strip nav-open/open/is-open classes from the DOM.
    Returns ``hidden_fixed`` from the post-close intersection receipt.
    """
    if crop_box is None:
        raise TypeError("crop_box is required for _scroll_clear_of_chrome")
    if int(viewport_width) <= 768:
        # Customer path only: click the toggle if the drawer is open, then Escape.
        target.evaluate(
            """() => {
                const toggle = document.querySelector(
                    '.nav-toggle, button.nav-toggle, [aria-controls=\"nav-links\"]');
                const nav = document.querySelector(
                    '.site-nav.has-nav-toggle, .site-nav.nav-open, nav.nav-open');
                const open = !!(nav && nav.classList.contains('nav-open'))
                    || document.documentElement.classList.contains('nav-open')
                    || document.body.classList.contains('nav-open');
                if (open && toggle) toggle.click();
            }"""
        )
        try:
            host_page.keyboard.press("Escape")
        except Exception:
            pass
        host_page.wait_for_timeout(120)
    # Scroll so the crop top sits below sticky/fixed chrome.
    host_page.evaluate(
        """({sel, extra}) => {
            const el = document.querySelector(sel);
            if (!el) return 0;
            let chrome = 0;
            const chromeSels = 'nav.mq-suitenav, .site-nav, .topbar, header.site-nav'
                + (extra ? (', ' + extra) : '');
            for (const sticky of document.querySelectorAll(chromeSels)) {
                const st = getComputedStyle(sticky);
                if (st.position !== 'sticky' && st.position !== 'fixed') continue;
                if (st.display === 'none' || Number(st.opacity) === 0) continue;
                const sr = sticky.getBoundingClientRect();
                if (sr.height < 2 || sr.width < 2) continue;
                chrome = Math.max(chrome, sr.bottom);
            }
            const margin = chrome + 8;
            const r = el.getBoundingClientRect();
            if (r.top < margin) {
                window.scrollBy(0, r.top - margin);
            }
            return margin;
        }""",
        {"sel": crop_selector, "extra": extra_chrome},
    )
    host_page.wait_for_timeout(80)
    panel = _nav_panel_box(target)
    if panel and _boxes_intersect(panel, crop_box):
        raise RuntimeError(
            f"nav panel intersects crop after clear: panel={panel} "
            f"crop={dict(crop_box)}")
    return _assert_no_fixed_intersection(target, crop_box)


# Back-compat name used by older call sites during the rename — always requires
# crop_box (C-m2). Prefer `_scroll_clear_of_chrome` at new sites.
def _close_nav_overlay(
        target, crop_selector: str, crop_box: Mapping[str, Any], *,
        host_page, viewport_width: int) -> list[str]:
    return _scroll_clear_of_chrome(
        target, crop_selector, crop_box,
        host_page=host_page, viewport_width=viewport_width)



def _locale_visible_text(locator, locale: str) -> str:
    """Visible text for the active locale only (computed display/visibility)."""
    return str(locator.evaluate(
        """(el, locale) => {
            const prefer = locale === 'zh' ? 'l-zh' : 'l-en';
            const other = locale === 'zh' ? 'l-en' : 'l-zh';
            const parts = [];
            const pushVisible = (node) => {
                if (!node || node.nodeType !== 1) return;
                const st = getComputedStyle(node);
                if (st.display === 'none' || st.visibility === 'hidden'
                    || Number(st.opacity) === 0) {
                    return;
                }
                if (node.classList && node.classList.contains(other)) {
                    return;
                }
                if (node.classList && node.classList.contains(prefer)) {
                    const t = (node.innerText || '').trim();
                    if (t) parts.push(t);
                    return;
                }
                // Unmarked nodes: keep direct text + recurse (matches clone
                // innerText after other-locale removal).
                for (const child of node.childNodes || []) {
                    if (child.nodeType === 3) {
                        const t = (child.textContent || '').trim();
                        if (t) parts.push(t);
                    } else if (child.nodeType === 1) {
                        pushVisible(child);
                    }
                }
            };
            pushVisible(el);
            return parts.join(' ').replace(/\\s+/g, ' ').trim();
        }""",
        locale,
    ) or "")


def _element_text_independent(locator, locale: str) -> str:
    """Independent DOM-text receipt: clone + strip other-locale, then innerText.

    Distinct code path from ``_locale_visible_text`` (live walker). Both must
    agree after whitespace normalization.
    """
    return str(locator.evaluate(
        """(el, locale) => {
            const other = locale === 'zh' ? 'l-en' : 'l-zh';
            const clone = el.cloneNode(true);
            clone.querySelectorAll('.' + other).forEach(n => n.remove());
            return (clone.innerText || '').replace(/\\s+/g, ' ').trim();
        }""",
        locale,
    ) or "")


def _crop_dom_sha256(locator, locale: str) -> str:
    html = str(locator.evaluate(
        """(el, locale) => {
            const other = locale === 'zh' ? 'l-en' : 'l-zh';
            const clone = el.cloneNode(true);
            clone.querySelectorAll('.' + other).forEach(n => n.remove());
            return clone.outerHTML || '';
        }""",
        locale,
    ) or "")
    return hashlib.sha256(html.encode("utf-8")).hexdigest()


def _scroll_container_receipt(locator) -> dict[str, Any]:
    """Ancestor + descendant horizontal scrollports for a crop element (C-M1)."""
    row = locator.evaluate(
        """(el) => {
            const selOf = (node) => {
                if (!node || node.nodeType !== 1) return null;
                if (node.id) return '#' + node.id;
                if (node.className && typeof node.className === 'string') {
                    const cls = node.className.trim().split(/\\s+/).slice(0, 3).join('.');
                    return cls
                        ? (node.tagName.toLowerCase() + '.' + cls)
                        : node.tagName.toLowerCase();
                }
                return node.tagName.toLowerCase();
            };
            const isScroll = (node) => {
                if (!node || node.nodeType !== 1) return false;
                const st = getComputedStyle(node);
                const ox = st.overflowX;
                if (ox !== 'auto' && ox !== 'scroll') return false;
                return node.scrollWidth > node.clientWidth + 1;
            };
            const pack = (node) => {
                const st = getComputedStyle(node);
                return {
                    selector: selOf(node),
                    scrollWidth: node.scrollWidth,
                    clientWidth: node.clientWidth,
                    scrollLeft: node.scrollLeft,
                    overflow_x: st.overflowX,
                };
            };
            const ancestor_scrollports = [];
            let cur = el.parentElement;
            while (cur) {
                if (isScroll(cur)) ancestor_scrollports.push(pack(cur));
                cur = cur.parentElement;
            }
            const inner_scrollports = [];
            for (const node of el.querySelectorAll('*')) {
                if (isScroll(node)) inner_scrollports.push(pack(node));
            }
            if (isScroll(el)) {
                // Self as scrollport counts as inner (content scroller).
                inner_scrollports.unshift(pack(el));
            }
            const primary = inner_scrollports[0] || ancestor_scrollports[0] || null;
            return {
                ancestor_scrollports,
                inner_scrollports,
                scroll_container_selector: primary ? primary.selector : null,
                scrollWidth: primary ? primary.scrollWidth : null,
                clientWidth: primary ? primary.clientWidth : null,
                scrollLeft: primary ? primary.scrollLeft : null,
                overflow_x: primary ? primary.overflow_x : null,
            };
        }"""
    )
    return row or {
        "ancestor_scrollports": [],
        "inner_scrollports": [],
        "scroll_container_selector": None,
        "scrollWidth": None,
        "clientWidth": None,
        "scrollLeft": None,
        "overflow_x": None,
    }


def _content_overflows_receipt(locator) -> list[dict[str, Any]]:
    """Walk descendants for overflow; classify against sanctioned_scrollers.yml.

    Excludes sr-only / 1px clip-rect a11y clips and SVG <text>. Every entry
    carries selector, kind, x, y, right, crop_right, nearest_registered_scroller.
    """
    registry = _load_sanctioned_scrollers()
    registry_keys = list(registry.keys())
    rows = locator.evaluate(
        """(el, registryKeys) => {
            const crop = el.getBoundingClientRect();
            const cropRight = crop.right;
            const allTables = [...document.querySelectorAll('table.mq-table')];
            const sectionIdOf = (node) => {
                let cur = node;
                while (cur && cur.nodeType === 1) {
                    if (cur.tagName === 'SECTION' && cur.id) return cur.id;
                    cur = cur.parentElement;
                }
                return null;
            };
            const tableSectionIds = allTables.map(sectionIdOf);
            const tableIdCounts = {};
            for (const sid of tableSectionIds) {
                if (!sid) continue;
                tableIdCounts[sid] = (tableIdCounts[sid] || 0) + 1;
            }
            const tableKeyOf = (node) => {
                const i = allTables.indexOf(node);
                if (i < 0) return null;
                const sid = tableSectionIds[i];
                if (sid && tableIdCounts[sid] === 1) return sid;
                return 'nth-' + i;
            };
            const elementKeyOf = (node) => {
                const tk = tableKeyOf(node);
                if (tk) return tk;
                const sid = sectionIdOf(node);
                if (sid) return sid;
                return null;
            };
            const isA11yClip = (node) => {
                if (!node || node.nodeType !== 1) return false;
                if (node.classList && node.classList.contains('mq-sr')) return true;
                if (node.matches && node.matches('.mq-sr, span.mq-sr')) return true;
                const st = getComputedStyle(node);
                const clip = st.clip || '';
                if (clip.includes('rect(0') || clip.includes('rect(0px')) return true;
                if (st.clipPath && st.clipPath.includes('inset(50%')) return true;
                const r = node.getBoundingClientRect();
                if (r.width <= 1.1 && r.height <= 1.1
                    && (st.overflow === 'hidden' || st.position === 'absolute')) {
                    return true;
                }
                return false;
            };
            const selOf = (node) => {
                if (!node || node.nodeType !== 1) return null;
                if (node.id) return '#' + node.id;
                const tag = node.tagName.toLowerCase();
                if (tag === 'svg' || tag === 'text' || tag === 'tspan') {
                    // Never emit bare "text" — SVG text nodes are excluded.
                    return tag === 'text' ? 'svg.text' : tag;
                }
                // Concrete selector with nth-of-type (walker forensics).
                const parent = node.parentElement;
                let nth = '';
                if (parent) {
                    const sibs = Array.from(parent.children).filter(
                        (c) => c.tagName === node.tagName);
                    if (sibs.length > 1) {
                        nth = ':nth-of-type(' + (sibs.indexOf(node) + 1) + ')';
                    }
                }
                if (node.className && typeof node.className === 'string') {
                    const cls = node.className.trim().split(/\\s+/).slice(0, 3).join('.');
                    return cls ? (tag + '.' + cls + nth) : (tag + nth);
                }
                return tag + nth;
            };
            const matchesKey = (node, key) => {
                if (!node || !key) return false;
                try {
                    if (key.startsWith('#') || key.startsWith('.')
                        || key.includes('.') || key.includes(' ')) {
                        return !!(node.matches && node.matches(key));
                    }
                } catch (e) {}
                if (key.startsWith('#')) return node.id === key.slice(1);
                return false;
            };
            const nearestRegistered = (node) => {
                let cur = node && node.nodeType === 1 ? node : (node && node.parentElement);
                while (cur) {
                    for (const key of registryKeys) {
                        if (matchesKey(cur, key)) return key;
                    }
                    // Also match by emitted selector string forms.
                    const s = selOf(cur);
                    if (s && registryKeys.indexOf(s) >= 0) return s;
                    if (cur === el) break;
                    cur = cur.parentElement;
                }
                return null;
            };
            const out = [];
            const seen = new Set();
            const push = (sel, kind, right, x, y, nearest, node) => {
                if (!sel || sel === 'text') return;
                const ekey = node ? elementKeyOf(node) : null;
                const key = sel + '|' + kind + '|' + Math.round(right * 10)
                    + '|' + (nearest || '') + '|' + (ekey || '');
                if (seen.has(key)) return;
                seen.add(key);
                const row = {
                    selector: sel,
                    kind,
                    right,
                    crop_right: cropRight,
                    x: x,
                    y: y,
                    nearest_registered_scroller: nearest,
                };
                if (ekey) row.element_key = ekey;
                out.push(row);
            };
            const isHScroll = (cur) => {
                if (!cur || cur.nodeType !== 1) return false;
                if (!(cur.scrollWidth > cur.clientWidth + 1)) return false;
                const st = getComputedStyle(cur);
                if (st.overflowX === 'auto' || st.overflowX === 'scroll'
                    || st.overflowX === 'overlay') return true;
                if (cur.matches && cur.matches('table.mq-table, .mq-table')) return true;
                return false;
            };
            const walk = (node) => {
                if (!node) return;
                if (node.nodeType === 3) {
                    const text = node.textContent || '';
                    if (!text.trim()) return;
                    const parent = node.parentElement;
                    if (!parent) return;
                    if (parent.closest && parent.closest('svg')) return;
                    if (isA11yClip(parent)) return;
                    const nearest = nearestRegistered(parent);
                    if (nearest) {
                        // Inside a registered scroller — do not file as free text clip.
                        return;
                    }
                    // Also suppress when inside ANY horizontal scrollport (table/rail).
                    let cur = parent;
                    while (cur) {
                        if (isHScroll(cur)) return;
                        if (cur === el) break;
                        cur = cur.parentElement;
                    }
                    const range = document.createRange();
                    range.selectNodeContents(node);
                    const rects = range.getClientRects();
                    for (const r of rects) {
                        if (r.width < 0.5 || r.height < 0.5) continue;
                        if (r.right > cropRight + 0.5) {
                            push(selOf(parent), 'text', r.right, r.left, r.top,
                                 null, parent);
                            break;
                        }
                    }
                    return;
                }
                if (node.nodeType !== 1) return;
                const tagUp = String(node.tagName || "").toUpperCase();
                if (tagUp === "TEXT" || tagUp === "TSPAN") return;
                if (isA11yClip(node)) return;
                const nearestSelf = nearestRegistered(node);
                if (node.scrollWidth > node.clientWidth + 1) {
                    const br = node.getBoundingClientRect();
                    const sel = selOf(node);
                    // Prefer registry key when this node itself is registered.
                    let regKey = null;
                    for (const key of registryKeys) {
                        if (matchesKey(node, key)) { regKey = key; break; }
                    }
                    push(regKey || sel, 'scrollport',
                         br.left + node.scrollWidth, br.left, br.top,
                         regKey || nearestSelf, node);
                }
                if (!nearestSelf) {
                    let insidePort = false;
                    let cur = node.parentElement;
                    while (cur) {
                        if (isHScroll(cur) || nearestRegistered(cur)) {
                            insidePort = true; break;
                        }
                        if (cur === el) break;
                        cur = cur.parentElement;
                    }
                    if (!insidePort) {
                        const br = node.getBoundingClientRect();
                        if (br.width >= 1 && br.height >= 1
                            && br.right > cropRight + 0.5) {
                            push(selOf(node), 'box', br.right, br.left, br.top,
                                 null, node);
                        }
                    }
                }
                for (const child of node.childNodes || []) walk(child);
            };
            walk(el);
            return out;
        }""",
        registry_keys,
    )
    # Normalize nearest_registered_scroller against Python registry keys.
    # Keep the concrete DOM selector in ``matched`` (with nth) next to the
    # registry key so receipts still say which .mq-table scrolled.
    normalized: list[dict[str, Any]] = []
    for entry in list(rows or []):
        row = dict(entry)
        sel = str(row.get("selector") or "")
        concrete = sel
        nearest = row.get("nearest_registered_scroller")
        if nearest:
            matched = _registry_match_selector(str(nearest)) or str(nearest)
            row["nearest_registered_scroller"] = matched
            row["matched"] = concrete
        else:
            matched = _registry_match_selector(sel)
            if matched and str(row.get("kind")) == "scrollport":
                row["selector"] = matched
                row["nearest_registered_scroller"] = matched
                row["matched"] = concrete
            else:
                row["nearest_registered_scroller"] = matched
                row["matched"] = concrete
        # Guarantee geometry keys.
        for key in ("x", "y", "right", "crop_right"):
            if key not in row or row[key] is None:
                row[key] = float(row.get(key) or 0.0)
        if str(row.get("selector") or "") == "table.mq-table":
            if not row.get("element_key"):
                raise RuntimeError(
                    "content_overflows table.mq-table entry missing "
                    f"element_key: {row}")
        normalized.append(row)
    return normalized


def _assert_content_overflows_allowed(
        overflows: Sequence[Mapping[str, Any]], *,
        family: str, name: str) -> None:
    """Every non-empty overflow must resolve to sanctioned_scrollers.yml.

    Unregistered scrollports and free box/text clips RAISE for every family.
    """
    registry = _load_sanctioned_scrollers()
    offenders: list[dict[str, Any]] = []
    for entry in overflows:
        kind = str(entry.get("kind") or "")
        sel = str(entry.get("selector") or "")
        nearest = entry.get("nearest_registered_scroller")
        if kind == "scrollport":
            key = _registry_match_selector(sel) or (
                _registry_match_selector(str(nearest)) if nearest else None)
            if not key or key not in registry:
                offenders.append(dict(entry))
                continue
            continue
        if kind in {"box", "text"}:
            key = _registry_match_selector(str(nearest)) if nearest else None
            if key and key in registry:
                # Nested inside a registered scroller — should not appear, but
                # if it does it is covered.
                continue
            offenders.append(dict(entry))
            continue
        # Unknown kind — fail closed.
        offenders.append(dict(entry))
    if offenders:
        raise CaptureContentClippedError(
            f"{name}: content_overflows not sanctioned "
            f"(family={family}): {offenders[:5]}",
            overflows=offenders, state=name,
        )


def _occlusion_samples(locator, *, cols: int = 3, rows: int = 5,
                       raw_box: Mapping[str, Any] | None = None,
                       ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Inclusive grid over raw_box. Only ``grid: short`` when h < 40."""
    box = dict(raw_box) if raw_box is not None else _crop_box(locator)
    crop_h = float(box["height"])
    crop_w = float(box["width"])
    short = crop_h < 40.0
    # C-n4: samples at top+4 and bottom-4 exactly; floor is (h-8)/h for h>=40.
    y_inset = 4.0
    # Inline chips (e.g. .mc-read-topic) share a line with sibling text; a
    # 4px x-inset lands in the following space span. Pull x samples inward.
    x_inset = min(max(4.0, crop_w * 0.12), max(0.0, crop_w / 2.0 - 1.0))
    if short:
        cols, rows = 3, 1
        cy = float(box["y"]) + crop_h / 2.0
        x0 = float(box["x"]) + x_inset
        x1 = float(box["x"]) + crop_w - x_inset
        mid = float(box["x"]) + crop_w / 2.0
        pts = [(x0, cy), (mid, cy), (x1, cy)] if x1 > x0 else [(mid, cy)]
        sample_box = dict(box)
        grid_label = "short"
    else:
        sample_box = dict(box)
        # Build pts with independent x/y insets (grid_sample_points is isotropic).
        x0 = float(box["x"]) + x_inset
        y0 = float(box["y"]) + y_inset
        x1 = float(box["x"]) + crop_w - x_inset
        y1 = float(box["y"]) + crop_h - y_inset
        if x1 <= x0 or y1 <= y0:
            pts = [(
                float(box["x"]) + crop_w / 2.0,
                float(box["y"]) + crop_h / 2.0,
            )]
        else:
            y_fracs = (0.0, 0.25, 0.50, 0.75, 1.0)
            x_fracs = (0.0, 0.50, 1.0)
            pts = [
                (x0 + (x1 - x0) * fx, y0 + (y1 - y0) * fy)
                for fy in y_fracs for fx in x_fracs
            ]
        grid_label = "full"
    # Playwright bounding_box is main-frame CSS; elementFromPoint inside an
    # iframe needs iframe-local coords. Derive the delta from the same element
    # (frameElement offsets are null under Playwright evaluate).
    local = locator.evaluate(
        """el => {
            const r = el.getBoundingClientRect();
            return {x: r.left, y: r.top, width: r.width, height: r.height};
        }"""
    )
    host = dict(box)
    ox = float(host["x"]) - float(local["x"])
    oy = float(host["y"]) - float(local["y"])
    samples = locator.evaluate(
        """(el, args) => {
            const pts = args.pts;
            const ox = args.ox;
            const oy = args.oy;
            const doc = el.ownerDocument || document;
            const win = doc.defaultView || window;
            const out = [];
            for (const [hx, hy] of pts) {
                const x = hx - ox;
                const y = hy - oy;
                if (x < 1 || y < 1 || x > win.innerWidth - 1
                    || y > win.innerHeight - 1) {
                    out.push({x: hx, y: hy, ok: false,
                              hitSelector: 'off-viewport'});
                    continue;
                }
                const stack = (doc.elementsFromPoint
                    ? doc.elementsFromPoint(x, y)
                    : [doc.elementFromPoint(x, y)].filter(Boolean));
                const hit = stack[0] || null;
                let inside = false;
                for (const node of stack) {
                    if (node === el || (el.contains && el.contains(node))) {
                        inside = true;
                        break;
                    }
                }
                let hitSelector = null;
                if (hit) {
                    hitSelector = hit.id ? ('#' + hit.id)
                        : (hit.className && typeof hit.className === 'string'
                            ? (hit.tagName.toLowerCase() + '.'
                               + String(hit.className).trim().split(/\\s+/)
                                 .slice(0, 3).join('.'))
                            : hit.tagName.toLowerCase());
                }
                out.push({x: hx, y: hy, ok: inside, hitSelector});
            }
            return out;
        }""",
        {"pts": pts, "ox": ox, "oy": oy},
    )
    if short:
        mid_i = len(samples) // 2
        _judge_occlusion([samples[mid_i]], min_samples=1)
        judged = list(samples)
        if not samples[mid_i].get("ok"):
            raise RuntimeError(
                f"short-crop centre sample missed crop: {samples[mid_i]}")
    else:
        judged = _judge_occlusion(samples, min_samples=len(pts))
    cov = y_coverage(judged, box)
    # R4: floor with 1e-3 epsilon. Exact floor is (h-8)/h; receipts may
    # sit a fraction of a CSS pixel below it.
    floor = ((crop_h - 8.0) / crop_h) if crop_h >= 40.0 else 0.0
    if (not short) and cov < (floor - 1e-3):
        raise RuntimeError(
            f"y_coverage {cov:.6f} < floor {floor:.6f}=(h-8)/h "
            f"with 1e-3 epsilon for crop h={crop_h} "
            f"(samples ys={[s.get('y') for s in judged]})")
    ys = [float(s["y"]) for s in judged if "y" in s]
    top = float(box["y"])
    bottom = top + float(box["height"])
    if not short and ys:
        if min(ys) > top + 4.0:
            raise RuntimeError(
                f"occlusion samples miss crop top+4: min_y={min(ys)} "
                f"top+4={top + 4.0}")
        if max(ys) < bottom - 4.0:
            raise RuntimeError(
                f"occlusion samples miss crop bottom-4: max_y={max(ys)} "
                f"bottom-4={bottom - 4.0}")
    meta = {
        "samples_span": "crop",
        "occlusion_sample_box": sample_box,
        "grid": grid_label,
    }
    # E-n3: a 0.0 in a field named coverage misleads on short crops
    # (single sample row, h<40). Record grid:short only.
    if not short:
        meta["y_coverage"] = cov
    return judged, meta


def _attach_occlusion(extra: dict[str, Any], locator,
                      raw_box: Mapping[str, Any] | None = None) -> None:
    samples, meta = _occlusion_samples(locator, raw_box=raw_box)
    extra["occlusionSamples"] = samples
    extra["samples_span"] = meta["samples_span"]
    if "y_coverage" in meta:
        extra["y_coverage"] = meta["y_coverage"]
    extra["occlusion_sample_box"] = meta.get("occlusion_sample_box")
    if meta.get("grid"):
        extra["grid"] = meta["grid"]



def _shot_route_of(target) -> str:
    """Path of the customer page. Prefer #mc-p5-frame content over harness URL."""
    return str(target.evaluate(
        """() => {
            const normalize = (path) => {
                const base = (path || '').split('/').pop() || path || '';
                return base.startsWith('/') ? base : '/' + base;
            };
            try {
                const frame = document.querySelector('#mc-p5-frame');
                if (frame && frame.contentWindow && frame.contentDocument) {
                    const ipath = frame.contentWindow.location.pathname || '';
                    const ibase = normalize(ipath);
                    if (ibase && !ibase.includes('_p5_harness')) {
                        return ibase;
                    }
                }
            } catch (e) {}
            return normalize(location.pathname || '');
        }"""
    ))


def _open_lineage_details_by_click(target, *, host_page) -> str:
    """Open History tab then the lineage <details>. Lineage lives under a hidden panel."""
    history_tab = target.locator('[data-mq-tab="history"]').first
    if history_tab.count():
        history_tab.wait_for(state="visible", timeout=15000)
        history_tab.click(timeout=15000)
        host_page.wait_for_timeout(120)
        panel = target.locator('[data-mq-panel="history"]').first
        panel.wait_for(state="visible", timeout=15000)
    details = target.locator(LINEAGE_OPEN_DETAILS).first
    details.wait_for(state="visible", timeout=15000)
    details.scroll_into_view_if_needed(timeout=15000)
    summary = details.locator("summary").first
    summary.click(timeout=15000)
    host_page.wait_for_timeout(120)
    opened = bool(details.evaluate("el => el.open"))
    if not opened:
        raise RuntimeError("section.mq-lineage details did not open on click")
    return "click"


def _chrome_bottom(page, extra_chrome: str = "") -> float:
    return float(page.evaluate(
        """(extra) => {
            let chrome = 0;
            const chromeSels = 'nav.mq-suitenav, .site-nav, .topbar, header.site-nav'
                + (extra ? (', ' + extra) : '');
            for (const sticky of document.querySelectorAll(chromeSels)) {
                const st = getComputedStyle(sticky);
                if (st.position !== 'sticky' && st.position !== 'fixed') continue;
                if (st.display === 'none' || Number(st.opacity) === 0) continue;
                const sr = sticky.getBoundingClientRect();
                if (sr.height < 2 || sr.width < 2) continue;
                chrome = Math.max(chrome, sr.bottom);
            }
            return chrome;
        }""",
        extra_chrome,
    ) or 0.0)


def _snap_css_box(box: Mapping[str, Any]) -> dict[str, float]:
    """Integer CSS box within ≤0.5 px of the measured raw_box (C-m4 ≤1)."""
    return {
        "x": float(round(float(box["x"]))),
        "y": float(round(float(box["y"]))),
        "width": float(max(1, round(float(box["width"])))),
        "height": float(max(1, round(float(box["height"])))),
    }


def _paint_libs():
    """Pillow + numpy. ImportError is the C-n3 fail-closed signal."""
    from PIL import Image
    import numpy as np
    return Image, np


def _painted_fraction(png_path: Path) -> float:
    """Share of non-background rows (E-m2). Blank canvas is visible in the manifest."""
    try:
        Image, np = _paint_libs()
    except ImportError as exc:
        raise RuntimeError(
            "painted_fraction cannot be measured without Pillow and numpy; "
            "a receipt is never defaulted to 1.0"
        ) from exc
    im = Image.open(png_path).convert("RGB")
    arr = np.asarray(im)
    if arr.size == 0:
        return 0.0
    bg = arr[0, 0].astype("int16")
    delta = np.abs(arr.astype("int16") - bg).max(axis=2)
    painted_rows = (delta > 8).any(axis=1)
    return float(painted_rows.mean()) if len(painted_rows) else 0.0


def _iframe_coord_receipt(page, *, viewport_width: int) -> dict[str, Any]:
    """E-m1: iframe-hosted crops record coordSpace + frame geometry."""
    host = page.locator("#mc-p5-frame")
    if host.count() != 1:
        win = _measure_window(page)
        return {
            "coordSpace": "host",
            "innerWidth": int(round(float(win["innerWidth"]))),
            "innerHeight": int(round(float(win["innerHeight"]))),
        }
    box = host.bounding_box() or {"x": 0, "y": 0, "width": 0, "height": 0}
    frame = page.frame_locator("#mc-p5-frame")
    dims = frame.locator("html").evaluate(
        """() => ({
            frameInnerWidth: window.innerWidth,
            frameInnerHeight: window.innerHeight,
        })"""
    ) or {}
    host_win = _measure_window(page)
    return {
        "coordSpace": "iframe",
        "frameInnerWidth": int(round(float(
            dims.get("frameInnerWidth") or viewport_width))),
        "frameInnerHeight": int(round(float(
            dims.get("frameInnerHeight") or 0))),
        "hostFrameOffset": {"x": float(box["x"]), "y": float(box["y"])},
        "innerWidth": int(round(float(host_win["innerWidth"]))),
        "innerHeight": int(round(float(host_win["innerHeight"]))),
    }


def _page_fits_receipt(
        measure: Mapping[str, Any], *,
        route: str, width: int | None, locale: str, theme: str,
) -> dict[str, Any]:
    """Build a page_fits row from a measurement. Does not raise (C-n2)."""
    sw = float(measure.get("page_scroll_width") or 0)
    iw = float(measure.get("innerWidth") or 0)
    if "page_fits" in measure:
        fits = bool(measure["page_fits"])
    else:
        fits = sw <= iw + 1
    width_i = int(width if width is not None else round(iw))
    return {
        "route": route,
        "width": width_i,
        "locale": locale,
        "theme": theme,
        "scroll_width": sw,
        "inner_width": iw,
        "fits": fits,
    }


def _commit_page_fits_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Raise if the measured page overflows. The row already records the boolean."""
    out = dict(row)
    if not out.get("fits"):
        raise PageOverflowError(
            str(out.get("route") or ""),
            int(out.get("width") or 0),
            float(out.get("scroll_width") or 0),
        )
    return out


def _assert_page_fits(target, *, name: str, route: str = "",
                       width: int | None = None,
                       theme: str = "dark", locale: str = "en") -> dict[str, Any]:
    """E-M3/C-M1: page must FIT its viewport — no document-level horizontal scroll."""
    measure = target.evaluate(
        """() => {
            const doc = document;
            const win = doc.defaultView || window;
            const se = doc.scrollingElement || doc.documentElement;
            const sw = se ? se.scrollWidth : 0;
            const iw = win.innerWidth || 0;
            return {
                page_scroll_width: sw,
                page_fits: sw <= iw + 1,
                innerWidth: iw,
            };
        }"""
    ) or {}
    row = _page_fits_receipt(
        measure, route=route or name, width=width, locale=locale, theme=theme)
    _commit_page_fits_row(row)
    return {
        "page_fits": row["fits"],
        "page_scroll_width": row["scroll_width"],
        "innerWidth": row["inner_width"],
        "theme": row["theme"],
    }


def _probe_page_fits_matrix(browser, *, origin: str) -> list[dict[str, Any]]:
    """C-M1 / R5-n4: one page_fits probe per route × width × locale × theme."""
    from scripts.build_macro_suite_pages import HUB_PAGE, SUITE_PAGES
    routes = [HUB_PAGE.output] + [page.output for page in SUITE_PAGES]
    widths = (320, 390, 768, 1440)
    locales = ("en", "zh")
    themes = ("dark", "light")
    rows: list[dict[str, Any]] = []
    for route in routes:
        for width in widths:
            for locale in locales:
                for theme in themes:
                    ctx, page, frame = _open(
                        browser=browser, origin=origin,
                        path=f"/{route}", theme=theme, locale=locale,
                        width=1440 if width < 1440 else width,
                        height=900,
                        iframe_width=width if width < 1440 else None,
                    )
                    try:
                        target = (
                            frame.locator("html") if frame is not None
                            else page.locator("html"))
                        target.wait_for(state="attached", timeout=15000)
                        page.wait_for_timeout(80)
                        measure = target.evaluate(
                            """() => {
                                const doc = document;
                                const win = doc.defaultView || window;
                                const se = doc.scrollingElement
                                    || doc.documentElement;
                                const sw = se ? se.scrollWidth : 0;
                                const iw = win.innerWidth || 0;
                                return {
                                    page_scroll_width: sw,
                                    page_fits: sw <= iw + 1,
                                    innerWidth: iw,
                                };
                            }"""
                        ) or {}
                        row = _page_fits_receipt(
                            measure, route=route, width=width,
                            locale=locale, theme=theme)
                        rows.append(row)
                        _commit_page_fits_row(row)
                    finally:
                        ctx.close()
    return rows


def _scroll_crop_fully_visible(page, selector: str, *, chrome: float) -> None:
    """Scroll so the crop top sits at chrome+8 and the bottom is in view.

    ``scroll_into_view_if_needed`` alone can leave the bottom 1px past the
    viewport edge; Playwright then truncates ``page.screenshot(clip=…)``.
    """
    page.evaluate(
        """([sel, chrome]) => {
            const el = document.querySelector(sel);
            if (!el) return;
            const margin = Number(chrome) + 8;
            const r = el.getBoundingClientRect();
            const vh = window.innerHeight;
            // Prefer top just under chrome; if the crop is taller than the
            // usable viewport the caller expands height first.
            const targetTop = margin;
            if (Math.abs(r.top - targetTop) > 1
                || r.bottom > vh - 4) {
                const docTop = window.scrollY + r.top;
                window.scrollTo(0, Math.max(0, docTop - targetTop));
            }
        }""",
        [selector, float(chrome)],
    )
    page.wait_for_timeout(60)


def _element_shot_guarded(
        dest: Path, page, locator, *, selector: str, locale: str,
        viewport_width: int, target_for_nav=None,
        page_id: str = "", family: str = "",
        receipt_locator=None, extra_chrome: str = "") -> dict[str, Any]:
    """Element shot: raw_box IS the frame; tall crops use a tall viewport.

    No width clamp, no height clip, no stitching. PNG css dims must equal
    shoot_box exactly; |shoot_box − raw_box| ≤ 1 px. content_overflows raises
    unless every entry resolves to sanctioned_scrollers.yml.

    ``receipt_locator`` (optional) is the document used for overflow / text /
    occlusion when it differs from the shoot locator (iframe host vs body).
    """
    nav_target = target_for_nav or page
    receipt = receipt_locator if receipt_locator is not None else locator
    base_w = int(viewport_width)
    # Remember the caller's viewport so we can restore after a tall shot.
    prior_vp = page.viewport_size or {"width": base_w, "height": 900}
    prior_h = int(prior_vp.get("height") or 900)

    locator.scroll_into_view_if_needed(timeout=15000)
    page.wait_for_timeout(80)
    box = _crop_box(locator)
    hidden_fixed = _scroll_clear_of_chrome(
        nav_target, selector, box,
        host_page=page, viewport_width=viewport_width,
        extra_chrome=extra_chrome)
    box = _crop_box(locator)
    if float(box["y"]) < -0.01:
        page.evaluate(
            """(dy) => { window.scrollBy(0, dy); }""",
            float(box["y"]) - 4.0,
        )
        page.wait_for_timeout(60)
        box = _crop_box(locator)
        hidden_fixed = _scroll_clear_of_chrome(
            nav_target, selector, box,
            host_page=page, viewport_width=viewport_width,
        extra_chrome=extra_chrome)
        box = _crop_box(locator)
    if float(box["x"]) < -0.01:
        page.evaluate(
            """(dx) => { window.scrollBy(dx, 0); }""",
            float(box["x"]) - 4.0,
        )
        page.wait_for_timeout(60)
        box = _crop_box(locator)

    raw_box_pre = {
        "x": float(box["x"]), "y": float(box["y"]),
        "width": float(box["width"]), "height": float(box["height"]),
    }
    chrome = _chrome_bottom(page, extra_chrome=extra_chrome)
    # Tall viewport when the crop itself (plus chrome) exceeds prior height,
    # OR when the crop's document position cannot fit in the current vh even
    # after scrolling the top under chrome (clip-past-edge truncates PNG).
    need_tall = float(raw_box_pre["height"]) + chrome + 16.0 > float(prior_h)
    shot_h = prior_h
    if need_tall:
        shot_h = max(
            int(math.ceil(float(raw_box_pre["height"]) + chrome + 16.0)), 900)
        page.set_viewport_size({"width": base_w, "height": shot_h})
        page.wait_for_timeout(80)
        locator.scroll_into_view_if_needed(timeout=15000)
        page.wait_for_timeout(60)
        box = _crop_box(locator)
        hidden_fixed = _scroll_clear_of_chrome(
            nav_target, selector, box,
            host_page=page, viewport_width=viewport_width,
        extra_chrome=extra_chrome)
        box = _crop_box(locator)
        # Layout must not change with viewport height.
        if (
            abs(float(box["width"]) - float(raw_box_pre["width"])) > 0.5
            or abs(float(box["height"]) - float(raw_box_pre["height"])) > 0.5
        ):
            page.set_viewport_size({"width": base_w, "height": prior_h})
            raise RuntimeError(
                f"{dest.name}: raw_box changed with tall viewport: "
                f"pre={raw_box_pre} now={box}")

    chrome = _chrome_bottom(page, extra_chrome=extra_chrome)
    _scroll_crop_fully_visible(page, selector, chrome=chrome)
    box = _crop_box(locator)
    hidden_fixed = _scroll_clear_of_chrome(
        nav_target, selector, box,
        host_page=page, viewport_width=viewport_width,
        extra_chrome=extra_chrome)
    box = _crop_box(locator)
    chrome = _chrome_bottom(page, extra_chrome=extra_chrome)
    _scroll_crop_fully_visible(page, selector, chrome=chrome)
    box = _crop_box(locator)

    # If the full snap still does not fit, grow the viewport to contain it.
    snap_probe = _snap_css_box(box)
    win_probe = _measure_window(page)
    vh_probe = float(win_probe["innerHeight"])
    bottom_need = float(snap_probe["y"]) + float(snap_probe["height"]) + 8.0
    if bottom_need > vh_probe + 0.5 or float(snap_probe["y"]) < -0.5:
        fit_h = max(
            int(math.ceil(max(bottom_need, float(snap_probe["height"]) + chrome + 16.0))),
            900,
            shot_h,
        )
        if fit_h > int(round(vh_probe)):
            page.set_viewport_size({"width": base_w, "height": fit_h})
            page.wait_for_timeout(80)
            need_tall = True
            shot_h = fit_h
            locator.scroll_into_view_if_needed(timeout=15000)
            chrome = _chrome_bottom(page, extra_chrome=extra_chrome)
            _scroll_crop_fully_visible(page, selector, chrome=chrome)
            box = _crop_box(locator)
            if (
                abs(float(box["width"]) - float(raw_box_pre["width"])) > 0.5
                or abs(float(box["height"]) - float(raw_box_pre["height"])) > 0.5
            ):
                page.set_viewport_size({"width": base_w, "height": prior_h})
                raise RuntimeError(
                    f"{dest.name}: raw_box changed with fit viewport: "
                    f"pre={raw_box_pre} now={box}")

    win = _measure_window(page)
    vw = float(viewport_width)
    vh = float(win["innerHeight"])
    scroll_y = float(win["scrollY"])
    doc_h = float(win["scrollHeight"])
    raw_box = {
        "x": float(box["x"]), "y": float(box["y"]),
        "width": float(box["width"]), "height": float(box["height"]),
    }
    crop_box_doc = {
        "x": raw_box["x"],
        "y": raw_box["y"] + scroll_y,
        "width": raw_box["width"],
        "height": raw_box["height"],
    }
    _assert_crop_geometry(
        raw_box, viewport_width=vw, doc_height=doc_h, name=dest.name,
        crop_box_doc=crop_box_doc, page=page_id, state=dest.name,
        locale=locale)
    hidden_fixed = _scroll_clear_of_chrome(
        nav_target, selector, raw_box,
        host_page=page, viewport_width=viewport_width,
        extra_chrome=extra_chrome)
    chrome = _chrome_bottom(page, extra_chrome=extra_chrome)
    _scroll_crop_fully_visible(page, selector, chrome=chrome)
    box = _crop_box(locator)
    win = _measure_window(page)
    vh = float(win["innerHeight"])
    scroll_y = float(win["scrollY"])
    doc_h = float(win["scrollHeight"])
    raw_box = {
        "x": float(box["x"]), "y": float(box["y"]),
        "width": float(box["width"]), "height": float(box["height"]),
    }
    # Grow again if the post-clear scroll left the snap past the bottom.
    snap_probe = _snap_css_box(raw_box)
    bottom_need = float(snap_probe["y"]) + float(snap_probe["height"]) + 8.0
    if bottom_need > vh + 0.5:
        fit_h = max(int(math.ceil(bottom_need)), 900, shot_h)
        page.set_viewport_size({"width": base_w, "height": fit_h})
        page.wait_for_timeout(80)
        need_tall = True
        shot_h = fit_h
        chrome = _chrome_bottom(page, extra_chrome=extra_chrome)
        _scroll_crop_fully_visible(page, selector, chrome=chrome)
        box = _crop_box(locator)
        win = _measure_window(page)
        vh = float(win["innerHeight"])
        scroll_y = float(win["scrollY"])
        raw_box = {
            "x": float(box["x"]), "y": float(box["y"]),
            "width": float(box["width"]), "height": float(box["height"]),
        }
        if (
            abs(float(raw_box["width"]) - float(raw_box_pre["width"])) > 0.5
            or abs(float(raw_box["height"]) - float(raw_box_pre["height"])) > 0.5
        ):
            page.set_viewport_size({"width": base_w, "height": prior_h})
            raise RuntimeError(
                f"{dest.name}: raw_box changed with post-clear fit viewport: "
                f"pre={raw_box_pre} now={raw_box}")
    dpr = _measure_dpr(page)
    extra: dict[str, Any] = {
        "dpr": dpr,
        "crop": True,
        "full_page": False,
        "crop_selector": selector,
        "fixture": "builder-payload",
        "locale": locale,
        "raw_box": dict(raw_box),
        "crop_box": dict(raw_box),
        "shot_viewport": {"w": base_w, "h": int(round(vh))},
        "raw_box_in_shot_viewport": dict(raw_box),
        "receipt_document": "host",
        "text_receipt_paths": dict(TEXT_RECEIPT_PATHS),
        "hidden_fixed": list(hidden_fixed or []),
        "shot_route": _shot_route_of(nav_target),
    }
    scroll_rcpt = _scroll_container_receipt(locator)
    extra.update(scroll_rcpt)
    # Page-fit probe against the customer document (iframe body when harnessed).
    fit = _assert_page_fits(receipt, name=dest.name)
    extra.update(fit)

    # One shot of the whole element in the (possibly tall) viewport.
    # Snap CSS box the same way ``_device_px_span`` does (integer CSS first)
    # so PNG IHDR == device_px_span ±1.
    snap_box = _snap_css_box(raw_box)
    if (
        abs(snap_box["width"] - float(raw_box["width"])) > 1.0
        or abs(snap_box["height"] - float(raw_box["height"])) > 1.0
        or abs(snap_box["x"] - float(raw_box["x"])) > 1.0
        or abs(snap_box["y"] - float(raw_box["y"])) > 1.0
    ):
        page.set_viewport_size({"width": base_w, "height": prior_h})
        raise RuntimeError(
            f"{dest.name}: CSS-integer snap moved raw_box by >1px: "
            f"raw={raw_box} snap={snap_box}")
    # Fail closed if the clip would leave the viewport (Playwright truncates).
    win = _measure_window(page)
    vh = float(win["innerHeight"])
    vw_now = float(win["innerWidth"])
    if (
        float(snap_box["x"]) < -0.5
        or float(snap_box["y"]) < -0.5
        or float(snap_box["x"]) + float(snap_box["width"]) > vw_now + 0.5
        or float(snap_box["y"]) + float(snap_box["height"]) > vh + 0.5
    ):
        page.set_viewport_size({"width": base_w, "height": prior_h})
        raise RuntimeError(
            f"{dest.name}: snap_box not fully in viewport: "
            f"snap={snap_box} vw={vw_now} vh={vh}")
    # Keep measured fractional raw_box; shoot_box is the snapped clip (C-m4).
    shoot_box = dict(snap_box)
    extra["raw_box"] = dict(raw_box)
    extra["shoot_box"] = dict(shoot_box)
    extra["crop_box"] = dict(shoot_box)
    extra["raw_box_in_shot_viewport"] = dict(raw_box)
    extra["shot_viewport"] = {"w": base_w, "h": int(round(vh))}
    page.screenshot(path=str(dest), type="png", clip=shoot_box)
    # E-m2: blank canvas share. 18-dark-en-1440 half-null fixture is honestly
    # tall (empty grid track / min-height under content); painted_fraction
    # makes the blank share visible beside y_coverage.
    extra["painted_fraction"] = _painted_fraction(dest)
    # Occlusion samples the SHOOT box in the shoot document (host page for
    # iframe crops). Overflow/text still use ``receipt`` (iframe body).
    _attach_occlusion(extra, locator, raw_box=raw_box)
    _assert_no_fixed_intersection(nav_target, raw_box)

    overflows = _content_overflows_receipt(receipt)
    extra["content_overflows"] = overflows
    fam = family or family_for(dest.name)
    _assert_content_overflows_allowed(
        overflows, family=fam, name=dest.name,
    )

    scroll_y = float(_measure_window(page)["scrollY"])
    extra["crop_box_doc"] = {
        "x": float(shoot_box["x"]),
        "y": float(shoot_box["y"]) + scroll_y,
        "width": float(shoot_box["width"]),
        "height": float(shoot_box["height"]),
    }
    extra["scroll_y_at_shot"] = scroll_y
    extra["device_px_span"] = _device_px_span(shoot_box, dpr)
    visible = _locale_visible_text(receipt, locale)
    independent = _element_text_independent(receipt, locale)
    anchor = "权重法则" if locale == "zh" else "Weights law"
    label_at = visible.find(anchor)
    if label_at < 0:
        label_at = visible.upper().find(anchor.upper())
    head_src = visible[label_at:] if label_at >= 0 else visible
    extra["visible_text_head"] = head_src.replace("\n", " ").strip()[:80]
    extra["visible_text_sha256"] = hashlib.sha256(
        visible.encode("utf-8")).hexdigest()
    extra["visible_text_scope"] = "page"
    extra["element_text_head"] = independent.replace("\n", " ").strip()[:80]
    extra["element_text_sha256"] = hashlib.sha256(
        independent.encode("utf-8")).hexdigest()
    if extra["element_text_sha256"] != extra["visible_text_sha256"]:
        other_needle = "权重法则" if locale == "en" else "Weights law"
        if other_needle in visible or other_needle in independent:
            page.set_viewport_size({"width": base_w, "height": prior_h})
            raise RuntimeError(
                f"{dest.name}: locale leak in text receipts "
                f"(other={other_needle!r})")
    extra["cropDomSha256"] = _crop_dom_sha256(receipt, locale)
    extra["_element_text"] = visible
    extra["innerWidth"] = int(round(float(win["innerWidth"])))
    extra["innerHeight"] = int(round(float(win["innerHeight"])))
    if receipt_locator is not None or page.locator("#mc-p5-frame").count() == 1:
        extra["receipt_document"] = "iframe"
        extra.update(_iframe_coord_receipt(page, viewport_width=viewport_width))
    else:
        extra["receipt_document"] = "host"
        extra["coordSpace"] = "host"

    # Invariant: PNG css dims == shoot_box exactly; |shoot − raw| ≤ 1 (C-m4).
    pw_chk, ph_chk = _png_size(dest)
    dpr_f = float(dpr) if float(dpr) > 0 else 1.0
    css_w = float(pw_chk) / dpr_f
    css_h = float(ph_chk) / dpr_f
    if (
        abs(css_w - float(shoot_box["width"])) > 0.01
        or abs(css_h - float(shoot_box["height"])) > 0.01
    ):
        page.set_viewport_size({"width": base_w, "height": prior_h})
        raise RuntimeError(
            f"{dest.name}: PNG css dims {css_w:.2f}x{css_h:.2f} != "
            f"shoot_box {shoot_box['width']:.2f}x{shoot_box['height']:.2f} "
            f"(dpr={dpr_f})")
    if (
        abs(float(shoot_box["width"]) - float(raw_box["width"])) > 1.0
        or abs(float(shoot_box["height"]) - float(raw_box["height"])) > 1.0
    ):
        page.set_viewport_size({"width": base_w, "height": prior_h})
        raise RuntimeError(
            f"{dest.name}: |shoot_box − raw_box| > 1px: "
            f"raw={raw_box} shoot={shoot_box}")
    # Keep crop_box == shoot_box (the photographed frame).
    scroll_y_align = float(extra.get("scroll_y_at_shot") or 0.0)
    extra["crop_box"] = dict(shoot_box)
    extra["crop_box_doc"] = {
        "x": float(shoot_box["x"]),
        "y": float(shoot_box["y"]) + scroll_y_align,
        "width": float(shoot_box["width"]),
        "height": float(shoot_box["height"]),
    }
    extra["device_px_span"] = _device_px_span_from_crop_box_doc(
        extra["crop_box_doc"], scroll_y_align, dpr_f)
    _assert_shot_geometry(
        dest, extra, int(round(vw)), int(round(vh)))
    if need_tall:
        page.set_viewport_size({"width": base_w, "height": prior_h})
        page.wait_for_timeout(40)
    png = dest.read_bytes()
    if png[:8] != b"\x89PNG\r\n\x1a\n" or b"IEND" not in png:
        raise RuntimeError(f"{dest.name} is not a finished PNG")
    return {
        **extra,
        "bytes": len(png),
        "sha256": hashlib.sha256(png).hexdigest(),
        "width": pw_chk,
        "height": ph_chk,
    }



def _open_ribbon_details(page) -> None:
    page.evaluate(
        """() => {
            document.querySelectorAll('.mq-ribbon details').forEach(el => {
                el.open = true;
            });
        }"""
    )


def _copy_probe(page, needles: tuple[str, ...]) -> dict[str, Any]:
    from lib.macro_suite_labels import copy_probe_ok
    raw = page.evaluate(
        """(needles) => {
            const details = Array.from(document.querySelectorAll(
                'details.mc-details, details.mc-primer'));
            const inside = details.map(el => el.innerText || '').join('\\n');
            const clone = document.documentElement.cloneNode(true);
            clone.querySelectorAll('details.mc-details, details.mc-primer, script')
                 .forEach(el => el.remove());
            const outside = clone.innerText || '';
            const pageText = document.body.innerText || '';
            const rows = [];
            for (const n of needles) {
                const inPage = pageText.includes(n);
                rows.push({
                    string: n,
                    in_page: inPage,
                    inside: inPage && inside.includes(n),
                    outside: outside.includes(n),
                });
            }
            return {rows};
        }""",
        list(needles),
    )
    rows = list(raw.get("rows") or [])
    return {"ok": copy_probe_ok(rows), "rows": rows}


_CLEARANCE_JS = """async (el, arg) => {
    /* R1: HIT is document geometry after a per-station re-measure.
       scrollTo + read-back + settle (two rAF + fonts.ready), then
       maxScrollAtCheck and the CURRENT occluder box. Bound is
       0 <= exposedAtScrollY <= maxScrollAtCheck. A past-max that
       disappears under the re-measure was never a hit. Nested sticky
       chips whose box lies inside another top-chrome box merge into
       the parent (union, parent's ovBottom, mergedInto: "rail"). */
    const position = Number(arg.position);
    const vw = window.innerWidth, vh = window.innerHeight;
    const overlap = (a, b) => !(a.right <= b.left || a.left >= b.right
        || a.bottom <= b.top || a.top >= b.bottom);
    const GEOM_TOL = 0.5;
    const boxInside = (inner, outer) => inner.top >= outer.top - GEOM_TOL
        && inner.bottom <= outer.bottom + GEOM_TOL
        && inner.left >= outer.left - GEOM_TOL
        && inner.right <= outer.right + GEOM_TOL;
    const paintedBox = (b) => ({
        top: b.top, bottom: b.bottom, left: b.left, right: b.right,
        x: b.x, y: b.y, w: b.w, h: b.h,
    });
    const clipView = (r) => {
        const left = Math.max(r.left, 0), right = Math.min(r.right, vw);
        const top = Math.max(r.top, 0), bottom = Math.min(r.bottom, vh);
        if (right <= left || bottom <= top) return null;
        return {left, right, top, bottom, x: left, y: top,
                w: right - left, h: bottom - top};
    };
    const elBox = (node) => {
        const r = node.getBoundingClientRect();
        return {tag: node.tagName || 'TEXT',
                id: node.id || '',
                cls: String(node.className || ''),
                x: r.x, y: r.y, w: r.width, h: r.height,
                top: r.top, bottom: r.bottom, left: r.left, right: r.right};
    };
    const textBox = (node) => {
        const range = document.createRange();
        range.selectNodeContents(node);
        const r = range.getBoundingClientRect();
        return {text: (node.textContent || '').trim().slice(0, 80),
                x: r.x, y: r.y, w: r.width, h: r.height,
                top: r.top, bottom: r.bottom, left: r.left, right: r.right};
    };
    const painted = (node) => {
        let cur = node.nodeType === 3 ? node.parentElement : node;
        while (cur && cur !== document.documentElement) {
            const cs = getComputedStyle(cur);
            if (cs.display === 'none' || cs.visibility === 'hidden') return false;
            if (Number(cs.opacity) === 0) return false;
            if (cs.clipPath && cs.clipPath !== 'none') return false;
            cur = cur.parentElement;
        }
        return true;
    };
    const isTopChrome = (box) => box.top >= -2 && box.top <= 90 && box.bottom <= 240;
    const isBottomChrome = (box) => box.bottom >= vh - 8 && box.top > vh * 0.55;
    const scrolling = document.scrollingElement || document.documentElement;
    const settle = async () => {
        await new Promise((resolve) => {
            requestAnimationFrame(() => requestAnimationFrame(resolve));
        });
        if (document.fonts && document.fonts.ready) await document.fonts.ready;
    };
    const measureMax = () => Math.max(0, scrolling.scrollHeight - window.innerHeight);
    const firstMax = measureMax();
    const want = position >= 1 ? firstMax : firstMax * position;
    window.scrollTo(0, want);
    await settle();
    let reached = window.scrollY || document.documentElement.scrollTop || 0;
    let maxScrollAtCheck = measureMax();
    if (position >= 1 && Math.abs(reached - maxScrollAtCheck) >= 2) {
        window.scrollTo(0, maxScrollAtCheck);
        await settle();
        reached = window.scrollY || document.documentElement.scrollTop || 0;
        maxScrollAtCheck = measureMax();
    }
    const scrollMatched = Math.abs(reached - (position >= 1
        ? maxScrollAtCheck : want)) < 2;
    const maxScrollMatched = Math.abs(reached - maxScrollAtCheck) < 2;
    const roots = Array.from(document.querySelectorAll('*')).filter(node => {
        const cs = getComputedStyle(node);
        const r = node.getBoundingClientRect();
        return (cs.position === 'fixed' || cs.position === 'sticky')
            && cs.display !== 'none' && cs.visibility !== 'hidden'
            && r.width > 0 && r.height > 0;
    });
    const occluders = [];
    for (const node of roots) {
        const boxes = [elBox(node)];
        node.querySelectorAll('*').forEach(child => {
            const r = child.getBoundingClientRect();
            if (r.width > 0 && r.height > 0) boxes.push(elBox(child));
        });
        occluders.push({
            el: node,
            id: node.id || String(node.className || ''),
            position: getComputedStyle(node).position,
            boxes,
            mergedInto: null,
            skipIndependent: false,
            ...elBox(node),
        });
    }
    const topChrome = occluders.filter((f) => isTopChrome(f));
    for (const child of topChrome) {
        const domParent = topChrome.find((p) => p !== child && p.el.contains(child.el));
        const geomParent = topChrome.find((p) => p !== child && boxInside(child, p));
        if (domParent && !boxInside(child, domParent)) {
            const painted = clipView(child);
            if (painted && !overlap(painted, domParent)) {
                throw new Error(
                    'chrome-merge-dom-not-geometry: '
                    + String(child.id || child.cls)
                    + ' is a DOM descendant of '
                    + String(domParent.id || domParent.cls)
                    + ' but is not inside its painted box');
            }
            child.mergedInto = null;
            child.mergeBasis = null;
            continue;
        }
        const parent = geomParent;
        if (!parent) continue;
        const parentName = String(parent.id || parent.cls || '');
        child.mergedInto = /rail|suitenav/i.test(parentName) ? 'rail' : (
            parentName.split(/\\s+/)[0] || 'rail');
        child.mergeBasis = 'geometry';
        child.parentBox = paintedBox(parent);
        child.childBox = paintedBox(child);
        child.skipIndependent = true;
    }
    const root = document.querySelector('.mc-panels, .mq-body, main, .mc-shell, .mq-shell')
        || document.body;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
        acceptNode(node) {
            return (node.textContent || '').trim()
                ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
        }
    });
    const texts = [];
    let node;
    while ((node = walker.nextNode())) {
        const box = textBox(node);
        if (box.w <= 0 || box.h <= 0) continue;
        if (!painted(node)) continue;
        texts.push({node, parent: node.parentElement, ...box});
    }
    const fullyCovered = (text, ov) => text.top >= ov.top - 0.5
        && text.bottom <= ov.bottom + 0.5
        && text.left >= ov.left - 0.5
        && text.right <= ov.right + 0.5;
    const occluderName = (f) => {
        const raw = String(f.id || f.cls || 'occluder').trim();
        return raw.split(/\\s+/)[0] || 'occluder';
    };
    const hits = [];
    const scrollUnder = [];
    const excuseFields = (rec, docTop, ovBottom) => {
        rec.docTop = docTop;
        rec.ovBottom = ovBottom;
        rec.exposedAtScrollY = docTop - ovBottom;
        rec.maxScrollAtCheck = maxScrollAtCheck;
        return rec;
    };
    for (const t of texts) {
        const tv = clipView(t);
        if (!tv) continue;
        for (const f of occluders) {
            if (f.skipIndependent) continue;
            if (f.el.contains(t.node)) continue;
            for (const box of f.boxes) {
                const bv = clipView(box);
                if (!bv || !overlap(tv, bv)) continue;
                const rec = {text: t.text, occluder: f.id,
                             occluder_position: f.position,
                             mergedInto: f.mergedInto,
                             box: {top: t.top, left: t.left, right: t.right,
                                   bottom: t.bottom},
                             ovBox: {top: box.top, left: box.left,
                                     right: box.right, bottom: box.bottom,
                                     height: box.h}};
                const name = occluderName(f);
                if (isBottomChrome(f) || (f.position === 'fixed' && !isTopChrome(f))) {
                    rec.reason = 'fixed-or-bottom-intersect';
                    hits.push(rec);
                } else if (isTopChrome(f) && fullyCovered(t, box)) {
                    const docTop = t.top + reached;
                    const ovBottom = box.bottom;
                    excuseFields(rec, docTop, ovBottom);
                    if (rec.exposedAtScrollY < 0
                            || rec.exposedAtScrollY > maxScrollAtCheck) {
                        rec.reason = 'top-chrome-full-cover-unexposable';
                        hits.push(rec);
                    } else {
                        rec.reason = name + '_fully_covered';
                        scrollUnder.push(rec);
                    }
                } else if (isTopChrome(f)) {
                    const docTop = t.top + reached;
                    excuseFields(rec, docTop, box.bottom);
                    if (rec.exposedAtScrollY < 0
                            || rec.exposedAtScrollY > maxScrollAtCheck) {
                        rec.reason = 'top-chrome-partial-cover-unexposable';
                        hits.push(rec);
                    } else {
                        rec.reason = name + '_partially_covered';
                        scrollUnder.push(rec);
                    }
                } else {
                    rec.reason = 'intersect';
                    hits.push(rec);
                }
                break;
            }
        }
    }
    const analyst = document.querySelector('.mc-analyst');
    const analystBox = analyst ? elBox(analyst) : null;
    const analystView = analystBox ? clipView(analystBox) : null;
    const stance = document.querySelector('.mc-panel .mc-stance, .mc-stance');
    const stanceBox = stance ? elBox(stance) : null;
    const callouts = Array.from(document.querySelectorAll(
        '.mc-arrival, .mc-watch, .mc-primer, .mq-callout, .mc-callout'))
        .map(elBox);
    let analystHits = [];
    /* B1/E3: merge ONLY on geometric containment. A DOM-child chip
       that is not inside the rail's painted box is not chrome. */
    let analystMergedInto = null;
    let mergeBasis = null;
    let railBox = null;
    let analystOffViewport = false;
    const railHost = analyst
        ? analyst.closest('.mq-suitenav, .mc-rail, .mq-suitenav-rail')
        : null;
    const railOcc = occluders.find((f) => !f.skipIndependent && isTopChrome(f)
        && /rail|suitenav/i.test(String(f.id || f.cls || '')));
    const railPainted = railOcc || (railHost ? {el: railHost, ...elBox(railHost)} : null);
    const collectAnalystHits = () => {
        if (!analystView || !analyst) return;
        const sv = stanceBox ? clipView(stanceBox) : null;
        if (sv && overlap(sv, analystView)) analystHits.push({kind: 'stance'});
        for (const c of callouts) {
            const cv = clipView(c);
            if (cv && overlap(cv, analystView)) analystHits.push({kind: 'callout'});
        }
        for (const t of texts) {
            if (analyst.contains(t.node)) continue;
            const host = t.parent && t.parent.closest
                ? t.parent.closest('.mc-rail, .mq-suitenav') : null;
            if (host) continue;
            const tv = clipView(t);
            if (tv && overlap(tv, analystView)) {
                analystHits.push({kind: 'text', text: t.text});
            }
        }
    };
    const offViewportFromBox = (box, clip) => {
        if (!box) return false;
        if (box.right <= 0 || box.left >= vw) return true;
        if (clip && (box.right <= clip.left || box.left >= clip.right
                || box.bottom <= clip.top || box.top >= clip.bottom)) {
            return true;
        }
        return false;
    };
    if (railPainted) railBox = paintedBox(railPainted);
    if (analystBox && railPainted && boxInside(analystBox, railPainted)) {
        analystMergedInto = 'rail';
        mergeBasis = 'geometry';
        if (railOcc) {
            railOcc.mergedChildren = (railOcc.mergedChildren || []).concat(['analyst']);
        }
    } else if (analystBox && railHost) {
        const paintsAway = Boolean(analystView)
            && railPainted && !overlap(analystView, railPainted);
        if (paintsAway) {
            throw new Error(
                'analyst-merge-dom-not-geometry: .mc-analyst is a DOM '
                + 'descendant of the rail but its painted box is not inside '
                + 'the rail painted box');
        }
        const railClip = railPainted ? clipView(railPainted) : null;
        analystOffViewport = offViewportFromBox(analystBox, railClip);
        if (!analystOffViewport) collectAnalystHits();
    } else if (analystView) {
        collectAnalystHits();
    }
    const cssPath = (el) => {
        if (!el) return '';
        if (el.id) return '#' + el.id;
        const cls = String(el.className || '').trim().split(/\\s+/)[0] || '';
        const tag = (el.tagName || '').toLowerCase();
        return cls ? (tag + '.' + cls) : tag;
    };
    const fab = document.getElementById('mmb-boot');
    const fabCs = fab ? getComputedStyle(fab) : null;
    const mmbBootInDom = Boolean(fab);
    const mmbBootVisible = Boolean(
        fab && fabCs && fabCs.display !== 'none' && fabCs.visibility !== 'hidden');
    const mmbBootBox = (mmbBootVisible && fab) ? elBox(fab) : null;
    const fabBox = (mmbBootBox && fabCs && fabCs.position === 'fixed')
        ? mmbBootBox : null;
    let fabGutterTextPx = null;
    let fabGutterBoxPx = null;
    let fabGutterBoxSelector = null;
    let gutterBasis = null;
    if (fabBox) {
        const yOverlap = (r) => r.bottom > fabBox.top && r.top < fabBox.bottom;
        const bandTexts = texts.filter(yOverlap);
        if (!bandTexts.length) {
            fabGutterTextPx = null;
            gutterBasis = {kind: 'no-text-in-fab-band'};
        } else {
            let minG = Infinity;
            let winner = null;
            for (const t of bandTexts) {
                const g = fabBox.left - t.right;
                if (g < minG) { minG = g; winner = t; }
            }
            fabGutterTextPx = minG;
            gutterBasis = {
                kind: 'painted-text-in-fab-band',
                selector: cssPath(winner && winner.parent),
                rect: winner ? {top: winner.top, bottom: winner.bottom,
                                left: winner.left, right: winner.right} : null,
                textHead: winner ? winner.text : '',
            };
        }
        const boxCandidates = [];
        if (stanceBox && stance) {
            boxCandidates.push({sel: cssPath(stance), box: stanceBox});
        }
        document.querySelectorAll(
            '.mc-arrival, .mc-watch, .mc-primer, .mq-callout, .mc-callout'
        ).forEach((el) => {
            boxCandidates.push({sel: cssPath(el), box: elBox(el)});
        });
        let maxRight = -Infinity;
        let maxSel = null;
        for (const c of boxCandidates) {
            if (c.box.right > maxRight) {
                maxRight = c.box.right;
                maxSel = c.sel;
            }
        }
        if (maxSel) {
            fabGutterBoxPx = fabBox.left - maxRight;
            fabGutterBoxSelector = maxSel;
        }
    }
    const fabGutterPx = fabGutterTextPx;
    const fabRightMarginPx = fabBox ? (vw - fabBox.right) : null;
    let fabAbsentReason = null;
    if (!mmbBootInDom) fabAbsentReason = 'not-in-dom';
    else if (!mmbBootVisible) fabAbsentReason = 'display-none';
    else if (!fabBox) fabAbsentReason = 'not-fixed';
    const atMax = position >= 1;
    const width = window.innerWidth;
    let reason = '';
    if (occluders.length === 0) reason = 'no_occluders_found';
    const ok = texts.length > 0 && hits.length === 0 && analystHits.length === 0
        && scrollMatched && reason === '';
    return {
        at_max: atMax,
        position,
        width,
        scrollReached: reached,
        scrollTarget: want,
        maxScroll: maxScrollAtCheck,
        maxScrollAtCheck,
        scrollMatched,
        maxScrollMatched: atMax ? maxScrollMatched : null,
        occluders: occluders.map(({el, boxes, ...rest}) => ({
            ...rest,
            boxes: boxes.map(b => ({tag: b.tag, id: b.id, cls: b.cls,
                                    x: b.x, y: b.y, w: b.w, h: b.h})),
        })),
        text_count: texts.length,
        intersections: hits,
        scroll_under_top_chrome: scrollUnder,
        analyst: analystBox,
        analystBox,
        analyst_hits: analystHits,
        analystMergedInto,
        mergeBasis,
        railBox,
        analystOffViewport,
        stance: stanceBox,
        fab: fabBox,
        mmbBootDisplay: fabCs ? fabCs.display : 'missing',
        mmbBootInDom,
        mmbBootVisible,
        mmbBootBox,
        fabGutterPx,
        fabGutterTextPx,
        fabGutterBoxPx,
        fabGutterBoxSelector,
        gutterBasis,
        fabRightMarginPx,
        fabAbsentReason,
        viewportWidth: vw,
        analyst_fixed: !!(analyst && getComputedStyle(analyst).position === 'fixed'),
        reason,
        ok,
    };
}"""


def classify_top_chrome_cover(*, doc_top: float, ov_bottom: float,
                              max_scroll_at_check: float) -> dict[str, Any]:
    """R1: exposedAtScrollY = docTop − ovBottom against the re-measured max.

    A TOP-stuck full cover is a hit only when exposedAtScrollY < 0 (never
    exposable) or when it is still past maxScrollAtCheck AFTER the
    per-station re-measure. A stale maxScroll that made exposed look
    past-max is not a hit.
    """
    exposed = float(doc_top) - float(ov_bottom)
    max_at = float(max_scroll_at_check)
    payload = {
        "docTop": float(doc_top),
        "ovBottom": float(ov_bottom),
        "exposedAtScrollY": exposed,
        "maxScrollAtCheck": max_at,
    }
    if exposed < 0 or exposed > max_at:
        return {"hit": True, "reason": "top-chrome-full-cover-unexposable",
                **payload}
    return {"hit": False, "reason": "fully_covered", **payload}


def classify_partial_cover(*, doc_top: float, ov_bottom: float,
                           max_scroll_at_check: float,
                           name: str = "rail") -> dict[str, Any]:
    """Partial top-chrome cover: HIT only when the expose point is unexposable."""
    exposed = float(doc_top) - float(ov_bottom)
    max_at = float(max_scroll_at_check)
    payload = {
        "docTop": float(doc_top),
        "ovBottom": float(ov_bottom),
        "exposedAtScrollY": exposed,
        "maxScrollAtCheck": max_at,
    }
    if exposed < 0 or exposed > max_at:
        return {"hit": True, "reason": "top-chrome-partial-cover-unexposable",
                **payload}
    return {"hit": False, "reason": f"{name}_partially_covered", **payload}


def box_inside(inner: Mapping[str, Any], outer: Mapping[str, Any],
               *, tol: float = 1.0) -> bool:
    """Painted-box containment, tolerance ≤ 1 css px (B1)."""
    return (
        float(inner["top"]) >= float(outer["top"]) - tol
        and float(inner["bottom"]) <= float(outer["bottom"]) + tol
        and float(inner["left"]) >= float(outer["left"]) - tol
        and float(inner["right"]) <= float(outer["right"]) + tol
    )


def clip_view_box(box: Mapping[str, Any], viewport_width: float,
                  viewport_height: float | None = None) -> dict[str, float] | None:
    left = max(float(box["left"]), 0.0)
    right = min(float(box["right"]), float(viewport_width))
    top = float(box["top"])
    bottom = float(box["bottom"])
    if viewport_height is not None:
        top = max(top, 0.0)
        bottom = min(bottom, float(viewport_height))
    if right <= left or bottom <= top:
        return None
    return {"left": left, "right": right, "top": top, "bottom": bottom}


def analyst_box_off_viewport(analyst_box: Mapping[str, Any],
                             viewport_width: float,
                             rail_clip: Mapping[str, Any] | None = None
                             ) -> bool:
    """True only when the chip lies entirely outside the viewport or rail clip."""
    left = float(analyst_box["left"])
    right = float(analyst_box["right"])
    if right <= 0 or left >= float(viewport_width):
        return True
    if rail_clip:
        if (right <= float(rail_clip["left"])
                or left >= float(rail_clip["right"])
                or float(analyst_box["bottom"]) <= float(rail_clip["top"])
                or float(analyst_box["top"]) >= float(rail_clip["bottom"])):
            return True
    return False


def decide_analyst_merge(analyst_box: Mapping[str, Any],
                         rail_box: Mapping[str, Any], *,
                         dom_descendant: bool,
                         analyst_in_viewport: bool,
                         overlaps_rail: bool = False,
                         viewport_width: float | None = None
                         ) -> dict[str, Any]:
    """Geometry-only merge. A painted DOM-child outside the rail RAISES."""
    if box_inside(analyst_box, rail_box):
        return {
            "analystMergedInto": "rail",
            "mergeBasis": "geometry",
            "analystOffViewport": False,
            "analystBox": dict(analyst_box),
            "railBox": dict(rail_box),
        }
    if dom_descendant and analyst_in_viewport and not overlaps_rail:
        raise RuntimeError(
            "analyst-merge-dom-not-geometry: chip is a DOM descendant "
            "of the rail but not inside its painted box")
    width = float(viewport_width) if viewport_width is not None else (
        float(rail_box["right"]) if rail_box.get("right") is not None else 0.0)
    rail_clip = clip_view_box(rail_box, width) if rail_box else None
    off = analyst_box_off_viewport(analyst_box, width, rail_clip)
    return {
        "analystMergedInto": None,
        "mergeBasis": None,
        "analystOffViewport": off,
        "analystBox": dict(analyst_box),
        "railBox": dict(rail_box),
    }


def assert_analyst_off_viewport(row: Mapping[str, Any]) -> None:
    """Recompute analystOffViewport from boxes; RAISE on mismatch."""
    box = row.get("analystBox") or row.get("analyst")
    if not box:
        return
    width = float(row.get("viewportWidth") or row.get("width") or 0)
    rail = row.get("railBox")
    rail_clip = clip_view_box(rail, width) if rail else None
    computed = analyst_box_off_viewport(box, width, rail_clip)
    reported = bool(row.get("analystOffViewport"))
    if reported != computed:
        raise RuntimeError(
            f"analystOffViewport mismatch: reported={reported} "
            f"computed={computed} box={box} width={width} rail_clip={rail_clip}")


def assert_merged_geometry(row: Mapping[str, Any]) -> None:
    """i2_ok is only claimable when every merge recomputes from boxes."""
    if row.get("analystMergedInto"):
        if row.get("mergeBasis") != "geometry":
            raise RuntimeError(
                f"merged analyst missing mergeBasis=geometry: {row}")
        analyst_box = row.get("analystBox") or row.get("analyst")
        rail_box = row.get("railBox")
        if not analyst_box or not rail_box:
            raise RuntimeError(
                f"merged analyst missing analystBox/railBox: {row}")
        if not box_inside(analyst_box, rail_box):
            raise RuntimeError(
                f"analyst merge is not geometric: {analyst_box} vs {rail_box}")
    for occ in row.get("occluders") or []:
        if not occ.get("mergedInto"):
            continue
        if occ.get("mergeBasis") != "geometry":
            raise RuntimeError(
                f"merged occluder missing mergeBasis=geometry: {occ}")
        parent = occ.get("parentBox")
        child = occ.get("childBox") or {
            key: occ[key] for key in ("top", "bottom", "left", "right")
            if key in occ
        }
        if parent and child and not box_inside(child, parent):
            raise RuntimeError(
                f"occluder merge is not geometric: {child} vs {parent}")


def _assert_excused_covers(row: Mapping[str, Any]) -> None:
    max_at = float(row.get("maxScrollAtCheck") or row.get("maxScroll") or 0)
    for rec in row.get("scroll_under_top_chrome") or []:
        reason = str(rec.get("reason") or "")
        if not reason.endswith("_covered"):
            continue
        for key in ("docTop", "ovBottom", "exposedAtScrollY",
                    "maxScrollAtCheck"):
            if key not in rec:
                raise RuntimeError(f"excused {reason} missing {key}: {rec}")
        exposed = float(rec["exposedAtScrollY"])
        rec_max = float(rec.get("maxScrollAtCheck") or max_at)
        if exposed < 0 or exposed > rec_max:
            raise RuntimeError(
                f"covered row out of bound: exposedAtScrollY={exposed} "
                f"maxScrollAtCheck={rec_max} rec={rec}")
        result = classify_top_chrome_cover(
            doc_top=float(rec["docTop"]),
            ov_bottom=float(rec["ovBottom"]),
            max_scroll_at_check=rec_max,
        )
        if reason.endswith("_fully_covered") and result["hit"]:
            raise RuntimeError(
                f"excused full cover is not exposable: {rec} -> {result}")


def synthetic_clearance_receipts(page=None) -> dict[str, Any]:
    """Positive controls from the classifier — never a handwritten literal.

    Default inputs are a synthetic full-cover (HIT, exposed −70) and a
    synthetic partial (bounded excuse, exposed +140). When a Playwright
    page is supplied the same classifiers run on measurements taken from
    synthetic DOM.
    """
    if page is not None:
        page.set_content(
            """<!doctype html><html><body style="margin:0;min-height:2200px">
            <nav class="mq-suitenav" id="suitenav"
                 style="position:sticky;top:0;height:80px;width:100%;
                        background:#222;color:#fff;z-index:3">rail</nav>
            <main>
            <p id="full-cover" style="margin:0;height:20px;margin-top:-70px">
              FULLCOVERTEXT
            </p>
            <p id="partial" style="margin:400px 0 0;width:72px;font-size:16px;
                 line-height:20px">PARTIALTEXT PARTIALTEXT PARTIALTEXT
                 PARTIALTEXT PARTIALTEXT PARTIALTEXT PARTIALTEXT
                 PARTIALTEXT PARTIALTEXT PARTIALTEXT</p>
            <div style="height:1600px"></div>
            </main>
            </body></html>"""
        )
        geom = page.evaluate(
            """() => {
                const partial = document.getElementById('partial');
                const nav = document.getElementById('suitenav');
                const max = Math.max(
                    0, document.documentElement.scrollHeight - window.innerHeight);
                const docTop = partial.getBoundingClientRect().top
                    + (window.scrollY || 0);
                const navH = nav.getBoundingClientRect().height;
                const want = Math.max(0, docTop - navH * 0.5);
                return {docTop, navH, max, want,
                        position: max ? Math.min(0.999, want / max) : 0};
            }"""
        )
        full_row = page.locator("html").evaluate(_CLEARANCE_JS, {"position": 0.0})
        partial_row = page.locator("html").evaluate(
            _CLEARANCE_JS, {"position": float(geom["position"])})
        full_src = None
        partial_src = None
        for rec in list(full_row.get("intersections") or []) + list(
                full_row.get("scroll_under_top_chrome") or []):
            reason = str(rec.get("reason") or "")
            if "full-cover" in reason or reason.endswith("_fully_covered"):
                full_src = rec
        for rec in list(partial_row.get("intersections") or []) + list(
                partial_row.get("scroll_under_top_chrome") or []):
            reason = str(rec.get("reason") or "")
            if "partial" in reason:
                partial_src = rec
        if not full_src:
            raise RuntimeError(
                f"synthetic full-cover DOM did not bind: geom={geom} "
                f"intersections={full_row.get('intersections')} "
                f"scroll_under={full_row.get('scroll_under_top_chrome')}")
        if not partial_src:
            raise RuntimeError(
                f"synthetic partial DOM did not bind: geom={geom} "
                f"intersections={partial_row.get('intersections')} "
                f"scroll_under={partial_row.get('scroll_under_top_chrome')}")
        full = classify_top_chrome_cover(
            doc_top=float(full_src["docTop"]),
            ov_bottom=float(full_src["ovBottom"]),
            max_scroll_at_check=float(full_src["maxScrollAtCheck"]))
        name = "rail"
        reason = str(partial_src.get("reason") or "")
        if reason.endswith("_partially_covered"):
            name = reason[: -len("_partially_covered")] or "rail"
        partial = classify_partial_cover(
            doc_top=float(partial_src["docTop"]),
            ov_bottom=float(partial_src["ovBottom"]),
            max_scroll_at_check=float(partial_src["maxScrollAtCheck"]),
            name=name)
        return {
            "full_cover_unexposable": full,
            "partial_bounded": partial,
            "source": "classifier-on-synthetic-dom",
            "maxScrollAtCheck": float(partial_src["maxScrollAtCheck"]),
            "partialStation": geom,
        }
    raise RuntimeError(
        "synthetic clearance requires a Playwright page; a DOM-path "
        "failure raises — there is no literal classifier fallback"
    )


def clearance_probe_ok(row: Mapping[str, Any] | None) -> bool:
    """Empty text set, any hit, empty occluders, or unmatched scroll → not ok."""
    if not row:
        return False
    texts = int(row.get("text_count") or 0)
    hits = list(row.get("intersections") or [])
    analyst_hits = list(row.get("analyst_hits") or [])
    occluders = list(row.get("occluders") or [])
    if texts <= 0:
        return False
    if hits or analyst_hits:
        return False
    if not occluders:
        return False
    if row.get("reason") == "no_occluders_found":
        return False
    if row.get("scrollMatched") is False:
        return False
    if row.get("at_max") and not row.get("maxScrollMatched"):
        return False
    width = float(row.get("width") or 0)
    if width >= 769:
        has_fab = bool(
            row.get("mmbBootInDom") and row.get("mmbBootVisible")
            and row.get("mmbBootBox"))
        if not has_fab and not row.get("fabAbsentReason"):
            return False
        if has_fab:
            gutter = row.get("fabGutterTextPx")
            if gutter is None:
                gutter = row.get("fabGutterPx")
            basis = row.get("gutterBasis") or {}
            no_band = (
                gutter is None
                and (basis.get("kind") == "no-text-in-fab-band"
                     or basis == "no-text-in-fab-band"))
            if gutter is not None and float(gutter) < 0:
                return False
            if gutter is None and not no_band:
                return False
            margin = row.get("fabRightMarginPx")
            if margin is not None and float(margin) < 0:
                return False
    return bool(row.get("ok")) and not row.get("reason")


def _clearance_probe(locator, *, position: float) -> dict[str, Any]:
    row = locator.evaluate(_CLEARANCE_JS, {"position": position})
    _assert_excused_covers(row)
    assert_merged_geometry(row)
    assert_analyst_off_viewport(row)
    row["ok"] = clearance_probe_ok(row)
    return row


_CHIP_MATERIAL_JS = """() => {
    const chip = document.querySelector('.mc-analyst');
    if (!chip) return {ok: false, reason: 'no analyst chip'};
    const item = chip.closest('li');
    const prev = (item && item.previousElementSibling
        ? item.previousElementSibling.querySelector(
            '.mq-suitenav-pill, .mc-rail-link')
        : null)
        || document.querySelector('.mq-suitenav-pill:not(.mc-analyst)')
        || document.querySelector('.mc-rail-link:not(.mc-analyst)');
    if (!prev) return {ok: false, reason: 'no previous sibling pill'};
    const keys = ['borderRadius', 'borderColor', 'minHeight', 'padding',
                  'fontSize', 'marginTop'];
    const a = getComputedStyle(chip);
    const b = getComputedStyle(prev);
    const props = {};
    let ok = true;
    for (const k of keys) {
        props[k] = {chip: a[k], sibling: b[k], equal: a[k] === b[k]};
        if (a[k] !== b[k]) ok = false;
    }
    return {ok, props};
}"""

WORKSPACE_RAIL_VIEWPORT_JS = """() => {
  const list = document.querySelector('.mq-suitenav-rail')
    || document.querySelector('.mq-tabbar');
  const analyst = document.querySelector('.mc-analyst');
  const content = [...document.querySelectorAll(
    '.mq-suitenav-pill:not(.mc-analyst), .mq-tab')];
  if (!list || !content.length) {
    return {ok: false, reason: 'missing workspace rail/tab strip'};
  }
  const fadeMin = 24;
  const listCs = getComputedStyle(list);
  const maskImage = listCs.maskImage;
  const webkitMaskImage = listCs.webkitMaskImage;
  const maskRaw = (webkitMaskImage && webkitMaskImage !== 'none')
    ? webkitMaskImage : (maskImage || 'none');
  const maskOk = maskRaw !== 'none' && maskRaw !== '';
  const maxScrollLeft = Math.max(0, list.scrollWidth - list.clientWidth);
  const parseFadeWidth = (raw, listWidth) => {
    const text = String(raw || '').trim();
    if (!text || text === 'none') return 0;
    const calc = [...text.matchAll(/calc\\(\\s*100%\\s*-\\s*([\\d.]+)px\\s*\\)/g)];
    if (calc.length) return Number(calc[calc.length - 1][1]);
    const stops = [...text.matchAll(/(-?[\\d.]+)%/g)].map((m) => Number(m[1]));
    const opaque = stops.filter((p) => p < 100);
    if (opaque.length) return (opaque[opaque.length - 1] / 100) * listWidth;
    return 0;
  };
  const listBox = list.getBoundingClientRect();
  const fadeWidth = parseFadeWidth(maskRaw, listBox.width);
  const analystBox = analyst ? analyst.getBoundingClientRect() : null;
  return {
    ok: maskOk && fadeWidth >= fadeMin - 0.5,
    maskOk,
    maskRaw,
    fadeWidth,
    maxScrollLeft,
    listOverflowX: listCs.overflowX,
    analystPresent: Boolean(analyst),
    analystLeft: analystBox ? analystBox.left : null,
    tabCount: content.length,
  };
}"""


E5_APPLICABILITY_JS = """() => ({
  fragments: Boolean(
    document.querySelector('#mc-shell[data-mc-fragments], [data-mc-fragments]')),
  template: Boolean(document.querySelector('template[data-mc-empty-e5]')),
})"""


def e5_applicability_for_html(html: str) -> dict[str, Any]:
    """A page is E5-bearing iff fragments && template. Missing html RAISES."""
    if not html:
        raise RuntimeError("e5_applicability_for_html: missing html")
    return {
        "fragments": "data-mc-fragments" in html,
        "template": "data-mc-empty-e5" in html,
    }


def e5_applicability_for_site(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"missing site file: {path}")
    return e5_applicability_for_html(path.read_text(encoding="utf-8"))


def e5_applicability_from_dom(page) -> dict[str, Any]:
    receipt = page.evaluate(E5_APPLICABILITY_JS)
    if not isinstance(receipt, dict):
        raise RuntimeError(f"E5 applicability evaluate returned {type(receipt)}")
    return {
        "fragments": bool(receipt.get("fragments")),
        "template": bool(receipt.get("template")),
    }


def page_is_e5_bearing(receipt: Mapping[str, Any] | None) -> bool:
    return bool(receipt and receipt.get("fragments") and receipt.get("template"))


_CHIPMAT_FILE_RE = re.compile(
    r"^chipmat-(?P<slug>.+)-(?P<theme>dark|light)-"
    r"(?P<locale>en|zh)-(?P<width>\d+)\.png$"
)


def rail_inner_html_identity(html: str) -> str:
    """Shared suite-nav identity: page-local current markers do not fork the hash."""
    text = str(html or "")
    text = re.sub(r"\s*\bis-current\b", "", text)
    text = re.sub(r'\s*aria-current="[^"]*"', "", text)
    return text


def parse_chipmat_name(name: str) -> dict[str, str] | None:
    match = _CHIPMAT_FILE_RE.fullmatch(name)
    if not match:
        return None
    return match.groupdict()


def _css_box(box: Mapping[str, Any] | None) -> dict[str, float] | None:
    if not box:
        return None
    if "left" in box and "right" in box:
        return {
            "left": float(box["left"]),
            "right": float(box["right"]),
            "top": float(box["top"]),
            "bottom": float(box["bottom"]),
        }
    return {
        "left": float(box["x"]),
        "right": float(box["x"]) + float(box["width"]),
        "top": float(box["y"]),
        "bottom": float(box["y"]) + float(box["height"]),
    }


def chipmat_containment_holds(cell: Mapping[str, Any], *,
                              tol: float = 1.0) -> bool:
    """analystBox (and sibling pill when the pair fits) inside cropBox.

    analystBox / siblingPillBox are recorded in the same space as the
    capture path that produced them: iframe crops use viewport-space
    getBoundingClientRect (match cropBox / crop_box); host / host-page
    crops record document-space boxes (match crop_box_doc). Never mix
    crop_box_doc.y with a viewport analystBox.y after a page scroll.
    """
    space = cell.get("coordSpace")
    if space == "iframe":
        crop = _css_box(
            cell.get("cropBox") or cell.get("crop_box")
            or cell.get("crop_box_doc"))
    else:
        crop = _css_box(
            cell.get("crop_box_doc") or cell.get("cropBox")
            or cell.get("crop_box"))
    chip = _css_box(cell.get("analystBox"))
    if not crop or not chip:
        return False
    if not box_inside(chip, crop, tol=tol):
        return False
    if cell.get("chipmatPairFits") is False:
        return True
    pill = _css_box(cell.get("siblingPillBox"))
    if not pill:
        return False
    return box_inside(pill, crop, tol=tol)


def chipmat_chip_margin_px(cell: Mapping[str, Any]) -> float | None:
    crop = _css_box(cell.get("cropBox") or cell.get("crop_box"))
    chip = _css_box(cell.get("analystBox"))
    if not crop or not chip:
        return None
    return min(
        chip["left"] - crop["left"],
        crop["right"] - chip["right"],
        chip["top"] - crop["top"],
        crop["bottom"] - chip["bottom"],
    )


def assert_chipmat_containment(cell: Mapping[str, Any], *,
                               key: str = "") -> None:
    if not chipmat_containment_holds(cell):
        raise RuntimeError(
            f"{key or 'chipmat'}: analyst/pill not inside crop "
            f"analyst={cell.get('analystBox')} pill={cell.get('siblingPillBox')} "
            f"crop={cell.get('cropBox')} pairFits={cell.get('chipmatPairFits')}")
    label = str(cell.get("chipLabel") or "")
    head = str(cell.get("elementTextHead") or cell.get("element_text_head") or "")
    if label and label not in head:
        raise RuntimeError(
            f"{key or 'chipmat'}: element_text_head {head!r} missing "
            f"chip label {label!r}")


def _parse_disclosure_trace_name(name: str) -> dict[str, str] | None:
    m = re.match(
        r"^disclosure_rows_open-(.+)-(dark|light)-(en|zh)-(\d+)"
        r"_rows_trace\.png$",
        name,
    )
    if not m:
        return None
    return {
        "slug": m.group(1),
        "theme": m.group(2),
        "locale": m.group(3),
        "width": m.group(4),
    }


def _disclosure_trace_collision_ratified(
        files: list[str], pages_out: Sequence[Mapping[str, Any]]
        ) -> bool:
    """Identical Trace-row PNGs across pages when DOM+allowlist match."""
    parsed = [_parse_disclosure_trace_name(name) for name in files]
    if not parsed or any(row is None for row in parsed):
        return False
    themes = {row["theme"] for row in parsed}  # type: ignore[index]
    locales = {row["locale"] for row in parsed}  # type: ignore[index]
    widths = {row["width"] for row in parsed}  # type: ignore[index]
    if len(themes) != 1 or len(locales) != 1 or len(widths) != 1:
        return False
    by_file = {
        st["file"]: st
        for page in pages_out
        for st in page.get("states") or []
        if st.get("file")
    }
    hashes: set[str] = set()
    for name in files:
        cell = by_file.get(name) or {}
        digest = cell.get("cropDomSha256")
        if not digest:
            return False
        hashes.add(str(digest))
    if len(hashes) != 1:
        return False
    slugs = {row["slug"] for row in parsed}  # type: ignore[index]
    if len(slugs) <= 1:
        return True
    return _chipmat_pair_allowlisted(
        sorted(slugs), theme=next(iter(themes)),
        locale=next(iter(locales)), width=next(iter(widths)))


def _crop_collision_ratified(
        files: list[str], probes: Mapping[str, Any],
        pages_out: Sequence[Mapping[str, Any]]) -> bool:
    if _chipmat_collision_ratified(files, probes):
        return True
    if _disclosure_trace_collision_ratified(files, pages_out):
        return True
    if _method_table_390_pair_ratified(files, pages_out):
        return True
    return _hub_rail_pair_ratified(files, pages_out)


def _hub_rail_pair_ratified(
        files: list[str], pages_out: Sequence[Mapping[str, Any]]) -> bool:
    """Hub rail/subtabs start+end may share bytes when the strip fits.

    E-B1: if content fits, start∪end are the same photograph; scroll receipts
    still carry fits:true / scrollLeft=0. Real overflow must differ.
    """
    if len(files) != 2:
        return False
    pat_rail = re.compile(
        r"^hubrail-rail-(dark|light)-(en|zh)-(390|768)-(start|end)\.png$"
    )
    pat_sub = re.compile(
        r"^hubrail-subtabs-(dark|light)-(en|zh)-390-(start|end)\.png$"
    )
    parsed = []
    for name in files:
        m = pat_rail.match(name)
        if m:
            parsed.append({
                "kind": "rail",
                "theme": m.group(1),
                "locale": m.group(2),
                "width": m.group(3),
                "pos": m.group(4),
                "file": name,
            })
            continue
        m = pat_sub.match(name)
        if m:
            parsed.append({
                "kind": "subtabs",
                "theme": m.group(1),
                "locale": m.group(2),
                "width": "390",
                "pos": m.group(3),
                "file": name,
            })
            continue
        return False
    if {row["pos"] for row in parsed} != {"start", "end"}:
        return False
    if len({(r["kind"], r["theme"], r["locale"], r["width"]) for r in parsed}) != 1:
        return False
    by_file = {
        st["file"]: st
        for page in pages_out
        for st in page.get("states") or []
        if st.get("file")
    }
    for row in parsed:
        cell = by_file.get(row["file"]) or {}
        sw = cell.get("scrollWidth")
        cw = cell.get("clientWidth")
        if sw is None or cw is None:
            return False
        if float(sw) > float(cw) + 1.0:
            return False
    return True


def _method_table_390_pair_ratified(
        files: list[str], pages_out: Sequence[Mapping[str, Any]]) -> bool:
    """Start/end table crops may share bytes when scrollWidth ≤ clientWidth.

    E-B1 still requires both PNGs + scroll receipts; when the table fits the
    phone width (observed on some ZH cells) scrollLeft=0 == max and the two
    frames are byte-identical by construction — that is not a collision defect.
    """
    if len(files) != 2:
        return False
    parsed = []
    for name in files:
        row = parse_method_table_name(name)
        if not row:
            return False
        parsed.append({**row, "file": name})
    if {row["pos"] for row in parsed} != {"start", "end"}:
        return False
    if len({
        (r["slug"], r["element_key"], r["theme"], r["locale"], r["width"])
        for r in parsed
    }) != 1:
        return False
    by_file = {
        st["file"]: st
        for page in pages_out
        for st in page.get("states") or []
        if st.get("file")
    }
    for row in parsed:
        cell = by_file.get(row["file"]) or {}
        sw = cell.get("scrollWidth")
        cw = cell.get("clientWidth")
        if sw is None or cw is None:
            return False
        if float(sw) > float(cw) + 1.0:
            # Real overflow — start and end must differ.
            return False
    return True


def _chipmat_collision_ratified(files: list[str],
                                probes: Mapping[str, Any]) -> bool:
    """Byte-identical chipmat crops are true iff crop DOM + identity match.

    Cross-page identical PNG bytes additionally require a committed allowlist
    entry (mockups/evidence/macro-command-p5/chipmat_identical_allowlist.yml).
    """
    parsed = [parse_chipmat_name(name) for name in files]
    if not parsed or any(row is None for row in parsed):
        return False
    themes = {row["theme"] for row in parsed}
    locales = {row["locale"] for row in parsed}
    widths = {row["width"] for row in parsed}
    if len(themes) != 1 or len(locales) != 1 or len(widths) != 1:
        return False
    hashes = set()
    for row in parsed:
        key = (
            f"chip_material_{row['slug']}_{row['theme']}_"
            f"{row['locale']}_{row['width']}"
        )
        cell = probes.get(key) or {}
        digest = cell.get("cropDomSha256")
        if not digest:
            return False
        if not chipmat_containment_holds(cell):
            return False
        hashes.add(digest)
    if len(hashes) != 1:
        return False
    slugs = {row["slug"] for row in parsed}
    if len(slugs) <= 1:
        return True
    return _chipmat_pair_allowlisted(
        sorted(slugs), theme=next(iter(themes)),
        locale=next(iter(locales)), width=next(iter(widths)))


def _chipmat_pair_allowlisted(
        slugs: Sequence[str], *, theme: str, locale: str, width: str | int
        ) -> bool:
    path = EVIDENCE / "chipmat_identical_allowlist.yml"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    want = set(slugs)
    blocks = text.split("- slugs:")
    for block in blocks[1:]:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        first = lines[0]
        if first.startswith("["):
            slug_list = [
                s.strip().strip("'\"")
                for s in first.strip("[]").split(",") if s.strip()]
        else:
            slug_list = []
        meta: dict[str, str] = {}
        reason = ""
        for ln in lines[1:]:
            if ln.startswith("theme:"):
                meta["theme"] = ln.split(":", 1)[1].strip()
            elif ln.startswith("locale:"):
                meta["locale"] = ln.split(":", 1)[1].strip()
            elif ln.startswith("width:"):
                meta["width"] = ln.split(":", 1)[1].strip().strip("'\"")
            elif ln.startswith("reason:"):
                reason = ln.split(":", 1)[1].strip()
        if set(slug_list) != want:
            continue
        if meta.get("theme") != str(theme):
            continue
        if meta.get("locale") != str(locale):
            continue
        if meta.get("width") != str(width):
            continue
        if not reason or len(reason) < 12:
            continue
        return True
    return False


def _chip_material_probe(target, *, page_name: str, locale: str,
                         width: int) -> dict[str, Any]:
    if page_name == HUB_PAGE:
        return {
            "ok": True,
            "notApplicable": "hub-chrome-scoped-off-MA2",
            "locale": locale,
            "width": width,
            "page": page_name,
        }
    row = target.evaluate(_CHIP_MATERIAL_JS)
    row["locale"] = locale
    row["width"] = width
    row["page"] = page_name
    return row


_RAIL_VISIBLE_TEXT_JS = """(el, locale) => {
    const other = locale === 'zh' ? 'l-en' : 'l-zh';
    const cr = el.getBoundingClientRect();
    const parts = [];
    for (const node of el.querySelectorAll('li, a, button, span.mc-rail-text, .mc-subtab')) {
      const r = node.getBoundingClientRect();
      if (r.width < 1 || r.height < 1) continue;
      // Full containment — a partially clipped chip is not "photographed".
      if (r.left < cr.left - 0.5 || r.right > cr.right + 0.5) continue;
      if (r.top < cr.top - 0.5 || r.bottom > cr.bottom + 0.5) continue;
      const clone = node.cloneNode(true);
      clone.querySelectorAll('.' + other).forEach(n => n.remove());
      const t = (clone.innerText || '').replace(/\\s+/g, ' ').trim();
      if (t) parts.push(t);
    }
    return parts.join(' ').replace(/\\s+/g, ' ').trim();
}"""


def _scroll_hub_scroller(target, selector: str, *, pos: str) -> dict[str, Any]:
    """Scroll a hub rail/subtabs scroller to start or end; return receipts.

    ``target`` is a Playwright locator (usually the iframe/html root). Locator
    ``evaluate`` binds the matched Element as the first arg and the Python
    payload as the second — a single-arg ``(args) =>`` would treat the Element
    as the payload and ``querySelector(undefined)`` → ``missing``.
    """
    return target.evaluate(
        """(root, args) => {
            const doc = root.ownerDocument || document;
            const el = doc.querySelector(args.sel);
            if (!el) return {ok: false, reason: 'missing', sel: args.sel};
            if (args.pos === 'end') {
              el.scrollLeft = el.scrollWidth;
            } else {
              el.scrollLeft = 0;
            }
            const st = getComputedStyle(el);
            return {
              ok: true,
              scroll_container_selector: args.sel,
              scrollWidth: el.scrollWidth,
              clientWidth: el.clientWidth,
              scrollLeft: el.scrollLeft,
              overflow_x: st.overflowX,
              fits: el.scrollWidth <= el.clientWidth + 1,
            };
        }""",
        {"sel": selector, "pos": pos},
    ) or {"ok": False}


_MQ_TABLE_CENSUS_JS = """() => {
    const reveal = (el) => {
      let p = el;
      while (p && p.nodeType === 1) {
        if (p.tagName === 'DETAILS' && !p.open) p.open = true;
        if (p.hasAttribute && p.hasAttribute('hidden')) {
          p.removeAttribute('hidden');
        }
        p = p.parentElement;
      }
    };
    const path = (el) => {
      const parts = [];
      let node = el;
      while (node && node.nodeType === 1
             && node !== document.documentElement) {
        if (node.id) {
          parts.unshift('#' + node.id);
          break;
        }
        let sel = node.tagName.toLowerCase();
        const cls = (node.getAttribute('class') || '')
          .trim().split(/\\s+/).filter(Boolean).slice(0, 3);
        if (cls.length) sel += '.' + cls.join('.');
        const parent = node.parentElement;
        if (parent) {
          const kids = [...parent.children];
          const same = kids.filter((c) => c.tagName === node.tagName);
          if (same.length > 1) {
            sel += ':nth-of-type(' + (kids.indexOf(node) + 1) + ')';
          }
        }
        parts.unshift(sel);
        node = parent;
      }
      return parts.join(' > ');
    };
    const tables = [...document.querySelectorAll('table.mq-table')];
    for (const el of tables) reveal(el);
    const sectionIdOf = (el) => {
      let cur = el;
      while (cur && cur.nodeType === 1) {
        if (cur.tagName === 'SECTION' && cur.id) return cur.id;
        cur = cur.parentElement;
      }
      return null;
    };
    const sectionIds = tables.map(sectionIdOf);
    const idCounts = {};
    for (const sid of sectionIds) {
      if (!sid) continue;
      idCounts[sid] = (idCounts[sid] || 0) + 1;
    }
    const keys = [];
    const seen = new Set();
    const rows = tables.map((el, i) => {
      const sid = sectionIds[i];
      let key = (sid && idCounts[sid] === 1) ? sid : ('nth-' + i);
      if (seen.has(key)) key = 'nth-' + i;
      seen.add(key);
      keys.push(key);
      const r = el.getBoundingClientRect();
      const st = getComputedStyle(el);
      const visible = r.width > 1 && r.height > 1
        && st.display !== 'none' && st.visibility !== 'hidden';
      const inMethod = !!(el.closest && el.closest('section.mq-method'));
      return {
        index: i,
        element_key: key,
        section_id: sid,
        selector: path(el),
        scrollWidth: el.scrollWidth,
        clientWidth: el.clientWidth,
        overflowing: el.scrollWidth > el.clientWidth + 1,
        visible,
        in_method_section: inMethod,
      };
    });
    if (new Set(keys).size !== keys.length) {
      return {ok: false, reason: 'duplicate element_key', rows};
    }
    return {ok: true, rows, n: rows.length};
}"""


_MQ_TABLE_VISIBLE_TEXT_JS = """(el, locale) => {
                const other = locale === 'zh' ? 'l-en' : 'l-zh';
                const cr = el.getBoundingClientRect();
                const parts = [];
                for (const cell of el.querySelectorAll('th, td')) {
                  const r = cell.getBoundingClientRect();
                  const st = getComputedStyle(cell);
                  const sticky = st.position === 'sticky'
                      || st.position === 'fixed';
                  const row = cell.parentElement;
                  let firstCol = false;
                  if (row) {
                    const cells = [...row.children].filter(
                      (c) => c.tagName === 'TH'
                          || c.tagName === 'TD');
                    firstCol = cells[0] === cell;
                  }
                  const vertIn = !(r.top < cr.top - 0.5
                      || r.bottom > cr.bottom + 0.5);
                  const horizOverlap = r.right > cr.left + 0.5
                      && r.left < cr.right - 0.5;
                  const fullyIn = !(r.left < cr.left - 0.5
                      || r.right > cr.right + 0.5
                      || r.top < cr.top - 0.5
                      || r.bottom > cr.bottom + 0.5);
                  if (sticky || firstCol) {
                    if (!vertIn || !horizOverlap) continue;
                  } else if (!fullyIn) {
                    continue;
                  }
                  const clone = cell.cloneNode(true);
                  clone.querySelectorAll('.' + other).forEach(n => n.remove());
                  const t = (clone.innerText || '').replace(/\\s+/g, ' ').trim();
                  if (t) parts.push(t);
                }
                return parts.join(' ').replace(/\\s+/g, ' ').trim();
            }"""


def _photograph_mq_table_390(
        *, page, target, table, table_sel: str,
        dest_list: list[dict[str, Any]], probes: dict[str, Any],
        slug: str, page_name: str, theme: str, locale: str,
        element_key: str, in_method_section: bool = False,
        receipt_locator=None) -> None:
    """Shoot start (+ end unless table_fits) of one table.mq-table at 390."""
    probes.setdefault("method_table_390_text", {})
    full_text = str(table.evaluate(
        """el => (el.innerText || '')
            .replace(/\\s+/g, ' ').trim()"""
    ) or "")
    probes["method_table_390_text"][
        f"method_table_390-{slug}__{element_key}-{theme}-{locale}-390"
    ] = full_text
    fit_rcpt = table.evaluate(
        """(el) => ({
            scrollWidth: el.scrollWidth,
            clientWidth: el.clientWidth,
            table_fits: el.scrollWidth <= el.clientWidth + 1,
        })"""
    ) or {}
    table_fits = bool(fit_rcpt.get("table_fits"))
    table.evaluate("el => { el.scrollLeft = 0; }")
    page.wait_for_timeout(40)
    text_zero = str(table.evaluate(_MQ_TABLE_VISIBLE_TEXT_JS, locale) or "")
    positions = [("start", 0)]
    if not table_fits:
        positions.append(("end", None))
    for pos, _scroll_to in positions:
        tname = method_table_filename(
            pos, slug, theme, locale, 390, element_key=element_key)
        print(f"capture {tname}", flush=True)
        scroll_rcpt = table.evaluate(
            """(el, args) => {
                const want = args.pos;
                if (want === 'end') {
                  el.scrollLeft = Math.max(
                    0, el.scrollWidth - el.clientWidth);
                } else {
                  el.scrollLeft = 0;
                }
                const st = getComputedStyle(el);
                return {
                  scroll_container_selector:
                    'table.mq-table',
                  scrollWidth: el.scrollWidth,
                  clientWidth: el.clientWidth,
                  scrollLeft: el.scrollLeft,
                  overflow_x: st.overflowX,
                  table_fits: el.scrollWidth
                    <= el.clientWidth + 1,
                  element_key: args.element_key,
                };
            }""",
            {"pos": pos, "element_key": element_key},
        )
        page.wait_for_timeout(80)
        vis_at_scroll = str(
            table.evaluate(_MQ_TABLE_VISIBLE_TEXT_JS, locale) or "")
        tinfo = _element_shot_guarded(
            EVIDENCE / tname, page, table,
            selector=table_sel, locale=locale,
            viewport_width=390, target_for_nav=target,
            family="method_table_390",
            receipt_locator=receipt_locator,
            extra_chrome=".mq-ribbon",
            )
        tinfo.update(scroll_rcpt or {})
        if pos == "start" and table_fits:
            tinfo["table_fits"] = True
        tinfo["element_key"] = element_key
        tinfo["in_method_section"] = bool(in_method_section)
        tinfo["visible_text_head"] = vis_at_scroll[:200]
        tinfo["visible_text_sha256"] = hashlib.sha256(
            vis_at_scroll.encode("utf-8")).hexdigest()
        tinfo["visible_text_scope"] = "element"
        tinfo["visible_text_at_scroll"] = vis_at_scroll
        tinfo["visible_text_at_zero"] = text_zero
        tinfo["shot_route"] = _shot_route_of(target)
        tinfo["page_id"] = page_name
        tinfo.pop("_element_text", None)
        probes.setdefault(
            "method_table_390_visible", {})[tname] = vis_at_scroll
        dest_list.append(_state(
            tname, theme, locale, "mobile", tinfo,
            viewport_width=390,
            verified_how=(
                f"{page_name} method table element_key={element_key} "
                f"scrollLeft={pos}; crop {table_sel}"
                + ("; table_fits" if table_fits else "")
            ),
            crop=True, selector=table_sel,
            force_state=f"method_table_390_{pos}",
            family="method_table_390",
        ))


def _capture_all_overflowing_mq_tables_390(
        *, page, host, dest_list: list[dict[str, Any]],
        probes: dict[str, Any], slug: str, page_name: str,
        theme: str, locale: str, receipt_locator=None,
        shot_target=None) -> None:
    """R1: photograph EVERY overflowing table.mq-table instance at 390.

    element_key is nearest unique ancestor section[id], else nth-of-match
    in document order (asserted unique). Never .first.
    """
    census = host.evaluate(_MQ_TABLE_CENSUS_JS) or {}
    if not census.get("ok"):
        raise RuntimeError(
            f"method_table_390-{slug}: table census failed {census}")
    rows = list(census.get("rows") or [])
    keys = [str(r.get("element_key") or "") for r in rows]
    if not keys and host.locator("table.mq-table").count() == 0:
        return
    if len(set(keys)) != len(keys) or any(not k for k in keys):
        raise RuntimeError(
            f"method_table_390-{slug}: element_key not unique/stable {keys}")
    overflowing = [r for r in rows if r.get("overflowing")]
    target = shot_target if shot_target is not None else page
    for row in overflowing:
        table_sel = str(row.get("selector") or "")
        element_key = str(row.get("element_key") or "")
        if not table_sel or not element_key:
            raise RuntimeError(
                f"method_table_390-{slug}: incomplete census row {row}")
        n_table = host.locator(table_sel).count()
        if n_table != 1:
            raise RuntimeError(
                f"method_table_390-{slug}: crop_selector {table_sel!r} "
                f"matched {n_table} (must be exactly one; never .first)")
        table = host.locator(table_sel)
        _photograph_mq_table_390(
            page=page, target=target, table=table, table_sel=table_sel,
            dest_list=dest_list, probes=probes, slug=slug,
            page_name=page_name, theme=theme, locale=locale,
            element_key=element_key,
            in_method_section=bool(row.get("in_method_section")),
            receipt_locator=receipt_locator,
        )


def _capture_method_table_390_pair(
        *, page, target, body, dest_list: list[dict[str, Any]],
        probes: dict[str, Any], slug: str, page_name: str,
        theme: str, locale: str) -> None:
    """Photograph every overflowing table.mq-table on a method-open page."""
    _capture_all_overflowing_mq_tables_390(
        page=page, host=target, dest_list=dest_list, probes=probes,
        slug=slug, page_name=page_name, theme=theme, locale=locale,
        shot_target=target,
    )


def _capture_overflowing_mq_table_390(
        *, page, host, dest_list: list[dict[str, Any]],
        probes: dict[str, Any], slug: str, page_name: str,
        theme: str, locale: str, receipt_locator=None) -> None:
    """Photograph every overflowing table.mq-table at 390 (no .first)."""
    _capture_all_overflowing_mq_tables_390(
        page=page, host=host, dest_list=dest_list, probes=probes,
        slug=slug, page_name=page_name, theme=theme, locale=locale,
        receipt_locator=receipt_locator, shot_target=page,
    )


def _capture_hub_rail_family(browser, *, origin: str,
                             dest_states: list[dict[str, Any]]) -> None:
    """E-B1: photograph ul.mc-rail-list (+ div.mc-subtabs) start/end pairs."""
    rail_sel = "ul.mc-rail-list"
    # Three mc-subtabs strips exist on the hub; pin the money strip (unique).
    sub_sel = 'div.mc-subtabs[aria-labelledby="money-h"]'
    for theme, locale in (
        ("dark", "en"), ("dark", "zh"),
        ("light", "en"), ("light", "zh"),
    ):
        for width in (390, 768):
            skip_end = False
            for pos in ("start", "end"):
                if pos == "end" and skip_end:
                    continue
                name = f"hubrail-rail-{theme}-{locale}-{width}-{pos}.png"
                print(f"capture {name}", flush=True)
                ctx, page, frame = _open(
                    browser=browser, origin=origin,
                    path=f"/{HUB_PAGE}", theme=theme, locale=locale,
                    width=1440 if width < 1440 else width,
                    height=900,
                    iframe_width=width if width < 1440 else None,
                )
                try:
                    host = frame.locator("html") if frame is not None else page
                    host.locator(rail_sel).wait_for(timeout=15000)
                    n = host.locator(rail_sel).count()
                    if n != 1:
                        raise RuntimeError(
                            f"{name}: crop_selector {rail_sel!r} matched {n}")
                    text_zero = str(host.locator(rail_sel).evaluate(
                        _RAIL_VISIBLE_TEXT_JS, locale) or "")
                    scroll_rcpt = _scroll_hub_scroller(
                        host, rail_sel, pos=pos)
                    if not scroll_rcpt.get("ok"):
                        raise RuntimeError(f"{name}: scroll failed {scroll_rcpt}")
                    page.wait_for_timeout(80)
                    text_at = str(host.locator(rail_sel).evaluate(
                        _RAIL_VISIBLE_TEXT_JS, locale) or "")
                    if pos == "start" and bool(scroll_rcpt.get("fits")):
                        # E-n1: scroller fits — start only, record fits:true.
                        skip_end = True
                    loc = host.locator(rail_sel)
                    info = _element_shot_guarded(
                        EVIDENCE / name, page, loc,
                        selector=rail_sel, locale=locale,
                        viewport_width=width, target_for_nav=page,
                        family="hub_rail",
                        receipt_locator=(
                            frame.locator("body").first if frame is not None
                            else None),
                    )
                    info.update(scroll_rcpt)
                    if skip_end and pos == "start":
                        info["fits"] = True
                    info["visible_text_at_scroll"] = text_at
                    info["visible_text_at_zero"] = text_zero
                    info["page_id"] = HUB_PAGE
                    info["shot_route"] = _shot_route_of(
                        frame.locator("html") if frame is not None else page)
                    dest_states.append(_state(
                        name, theme, locale,
                        "mobile" if width == 390 else "tablet",
                        info, viewport_width=width,
                        verified_how=(
                            f"{HUB_PAGE} {rail_sel} scrollLeft={pos}"
                            + ("; fits" if skip_end and pos == "start" else "")
                        ),
                        crop=True, selector=rail_sel,
                        force_state=f"hub_rail_{pos}",
                        family="hub_rail",
                    ))
                finally:
                    ctx.close()
        # div.mc-subtabs at 390 — live only on the active money panel
        # (other panels stay [hidden] until hash activation).
        skip_sub_end = False
        for pos in ("start", "end"):
            if pos == "end" and skip_sub_end:
                continue
            name = f"hubrail-subtabs-{theme}-{locale}-390-{pos}.png"
            print(f"capture {name}", flush=True)
            ctx, page, frame = _open(
                browser=browser, origin=origin,
                path=f"/{HUB_PAGE}#money", theme=theme, locale=locale,
                width=1440, height=900, iframe_width=390,
            )
            try:
                host = frame.locator("html") if frame is not None else page
                # Boot may settle on overview briefly; force money if needed.
                host.evaluate(
                    """() => {
                        if ((location.hash || '').replace(/^#/, '').split('/')[0]
                            !== 'money') {
                          location.hash = '#money';
                        }
                    }"""
                )
                host.locator("#money:not([hidden])").wait_for(timeout=15000)
                host.locator(sub_sel).wait_for(state="visible", timeout=15000)
                n = host.locator(sub_sel).count()
                if n != 1:
                    raise RuntimeError(
                        f"{name}: crop_selector {sub_sel!r} matched {n}")
                text_zero = str(host.locator(sub_sel).evaluate(
                    _RAIL_VISIBLE_TEXT_JS, locale) or "")
                scroll_rcpt = _scroll_hub_scroller(host, sub_sel, pos=pos)
                if not scroll_rcpt.get("ok"):
                    raise RuntimeError(f"{name}: scroll failed {scroll_rcpt}")
                page.wait_for_timeout(80)
                text_at = str(host.locator(sub_sel).evaluate(
                    _RAIL_VISIBLE_TEXT_JS, locale) or "")
                if pos == "start" and bool(scroll_rcpt.get("fits")):
                    skip_sub_end = True
                loc = host.locator(sub_sel)
                info = _element_shot_guarded(
                    EVIDENCE / name, page, loc,
                    selector=sub_sel, locale=locale,
                    viewport_width=390, target_for_nav=page,
                    family="hub_rail",
                    receipt_locator=(
                        frame.locator("body").first if frame is not None
                        else None),
                )
                info.update(scroll_rcpt or {})
                if skip_sub_end and pos == "start":
                    info["fits"] = True
                # Registry key (covering test) — concrete crop stays on crop_selector.
                info["scroll_container_selector"] = "div.mc-subtabs"
                info["visible_text_at_scroll"] = text_at
                info["visible_text_at_zero"] = text_zero
                info["page_id"] = HUB_PAGE
                dest_states.append(_state(
                    name, theme, locale, "mobile", info,
                    viewport_width=390,
                    verified_how=(
                        f"{HUB_PAGE}#money {sub_sel} scrollLeft={pos}"
                        + ("; fits" if skip_sub_end and pos == "start" else "")
                    ),
                    crop=True, selector=sub_sel,
                    force_state=f"hub_subtabs_{pos}",
                    family="hub_rail",
                ))
            finally:
                ctx.close()


def _mmb_surface_state(root) -> dict[str, Any]:
    return root.evaluate(
        """() => {
            const boxOf = (el) => {
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return {left: r.left, right: r.right, top: r.top,
                        bottom: r.bottom, width: r.width, height: r.height};
            };
            const painted = (el) => {
                if (!el) return false;
                const cs = getComputedStyle(el);
                const r = el.getBoundingClientRect();
                return cs.display !== 'none' && cs.visibility !== 'hidden'
                    && Number(cs.opacity) > 0 && r.width > 0 && r.height > 0;
            };
            const el = document.getElementById('mmb-root');
            const panel = document.getElementById('mmb-panel');
            const panelOpen = Boolean(panel && panel.classList.contains('open'));
            return {
                present: Boolean(el),
                visible: painted(el),
                box: boxOf(el),
                openState: {
                    selector: '#mmb-panel',
                    openClass: panelOpen ? 'open' : null,
                    open: panelOpen,
                    visible: panelOpen && painted(panel),
                    box: boxOf(panel),
                },
            };
        }"""
    )


def chat_visible_from_state(state: Mapping[str, Any] | None) -> bool:
    """ok iff the chat surface is painted — root box or #mmb-panel.open."""
    if not state:
        return False
    box = state.get("box") or {}
    root_vis = bool(state.get("visible") and float(box.get("width") or 0) > 0
                    and float(box.get("height") or 0) > 0)
    open_state = state.get("openState") or {}
    return bool(root_vis or open_state.get("visible"))


def _run_chip_opens_chat(host, *, page_name: str, locale: str,
                         width: int) -> dict[str, Any]:
    root = host.locator("html")
    url_before = root.evaluate("() => location.href")
    before = _mmb_surface_state(root)
    chip = host.locator("[data-mc-analyst], a.mc-analyst").first
    if chip.count() == 0:
        return {
            "ok": False,
            "reason": "missing analyst entry",
            "page": page_name,
            "locale": locale,
            "width": width,
            "mmbRootBefore": before,
            "urlBefore": url_before,
        }
    href = chip.get_attribute("href")
    has_attr = chip.get_attribute("data-mc-analyst") is not None
    t0 = time.monotonic()
    chip.click()
    after = before
    visible_after_ms: float | None = None
    deadline = t0 + 3.0
    while True:
        after = _mmb_surface_state(root)
        if chat_visible_from_state(after):
            visible_after_ms = (time.monotonic() - t0) * 1000
            break
        if time.monotonic() >= deadline:
            break
        time.sleep(0.05)
    url_after = root.evaluate("() => location.href")
    return {
        "ok": chat_visible_from_state(after),
        "clicked": "data-mc-analyst" if has_attr else "mc-analyst",
        "href": href,
        "mountedId": "mmb-root" if after.get("present") else None,
        "mmbRootBefore": {
            "present": before.get("present"),
            "visible": before.get("visible"),
            "box": before.get("box"),
        },
        "mmbRootAfter": {
            "present": after.get("present"),
            "visible": after.get("visible"),
            "box": after.get("box"),
        },
        "openState": after.get("openState"),
        "openClass": (
            "open" if (after.get("openState") or {}).get("open") else None),
        "visibleAfterMs": visible_after_ms,
        "urlBefore": url_before,
        "urlAfter": url_after,
        "openedBy": "click",
        "page": page_name,
        "locale": locale,
        "width": width,
    }


def _run_e5_timeout(page, *, context) -> dict[str, Any]:
    """Stall the fragment request so the product's 8000 ms timeout clones E5."""
    request_seen_at: float | None = None

    def _hold(route) -> None:
        nonlocal request_seen_at
        if request_seen_at is None:
            request_seen_at = time.monotonic()
        time.sleep(9)
        try:
            route.abort()
        except Exception:
            pass

    context.route("**/macro/fragments/**", _hold)
    page.reload(wait_until="domcontentloaded", timeout=30000)
    if request_seen_at is None:
        request_seen_at = time.monotonic()
    clone_seen_at: float | None = None
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        present = page.evaluate(
            """() => {
              const fromDoc = (doc) => doc
                ? doc.querySelector('[data-mc-empty="e5"]') : null;
              let clone = fromDoc(document);
              const frame = document.querySelector('#mc-p5-frame');
              if (!clone && frame && frame.contentDocument) {
                clone = fromDoc(frame.contentDocument);
              }
              return Boolean(clone);
            }"""
        )
        if present:
            clone_seen_at = time.monotonic()
            break
        page.wait_for_timeout(50)
    if clone_seen_at is None:
        raise RuntimeError("E5 clone never appeared")
    request_seen_at_ms = request_seen_at * 1000
    clone_seen_at_ms = clone_seen_at * 1000
    elapsed_ms = clone_seen_at_ms - request_seen_at_ms
    receipt = page.evaluate(
        """() => {
          const frame = document.querySelector('#mc-p5-frame');
          const root = (frame && frame.contentDocument)
            ? frame.contentDocument : document;
          const clone = root.querySelector('[data-mc-empty="e5"]');
          const title = clone
            ? clone.querySelector('.mc-empty-title, h3') : null;
          let headline = '';
          if (title) {
            const spans = [...title.querySelectorAll('.l-en, .l-zh')];
            const vis = spans.find((s) => {
              const cs = getComputedStyle(s);
              return cs.display !== 'none' && cs.visibility !== 'hidden';
            });
            headline = vis
              ? String(vis.innerText || '').trim()
              : String(title.innerText || '').trim();
          }
          return {clonePresent: Boolean(clone), headline: headline.slice(0, 80)};
        }"""
    )
    receipt["requestSeenAtMs"] = request_seen_at_ms
    receipt["cloneSeenAtMs"] = clone_seen_at_ms
    receipt["elapsedMs"] = elapsed_ms
    receipt["ok"] = bool(receipt.get("clonePresent") and elapsed_ms >= 8000)
    return receipt


def _require_clean_tree(*, when: str) -> dict[str, Any]:
    status = subprocess.check_output(
        ["git", "status", "--short"], cwd=ROOT, text=True)
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    clean = status.strip() == ""
    if not clean:
        raise RuntimeError(
            f"capture refused: dirty worktree at {when}:\n{status}")
    return {"when": when, "clean": clean, "head": head, "status": status}


def _load_e5_applicability(
        applicability: Mapping[str, Mapping[str, Any]] | None = None,
        ) -> dict[str, dict[str, Any]]:
    if applicability is not None:
        return {name: dict(row) for name, row in applicability.items()}
    return {name: e5_applicability_for_site(SITE / name) for name in FIVE_PAGES}


def declared_cell_rows(
        e5_applicability: Mapping[str, Mapping[str, Any]] | None = None,
        ) -> list[dict[str, Any]]:
    """Reader-joinable declared matrix. Every captured frame is declared."""
    appl = _load_e5_applicability(e5_applicability)
    cells: list[dict[str, Any]] = []

    def add(filename: str, *, family: str | None = None) -> None:
        cells.append({"file": filename, "family": family or family_for(filename)})

    for n, theme, locale in (
        ("01", "dark", "en"), ("02", "dark", "zh"),
        ("03", "light", "en"), ("04", "light", "zh"),
    ):
        add(f"{n}-{theme}-{locale}-1440.png")
        add(f"{n}-{theme}-{locale}-1440-full.png")
    for n, theme, locale in (
        ("05", "dark", "en"), ("06", "dark", "zh"),
        ("07", "light", "en"), ("08", "light", "zh"),
    ):
        add(f"{n}-{theme}-{locale}-1440.png")
    for n, theme, locale in (
        ("09", "dark", "en"), ("10", "dark", "zh"),
        ("11", "light", "en"), ("12", "light", "zh"),
    ):
        add(f"{n}-{theme}-{locale}-390.png")
    for n, theme, locale in (
        ("13", "dark", "en"), ("13b", "dark", "zh"),
        ("14", "light", "en"), ("14b", "light", "zh"),
    ):
        add(f"{n}-{theme}-{locale}-768.png")
    for n, theme, locale in (
        ("15", "dark", "en"), ("15b", "dark", "zh"),
        ("16", "light", "zh"), ("16b", "light", "en"),
    ):
        add(f"{n}-{theme}-{locale}-1440.png")
    for page_name in METHOD_OPEN_PAGES:
        slug = page_name.replace(".html", "")
        for theme, locale in (
            ("dark", "en"), ("dark", "zh"),
            ("light", "en"), ("light", "zh"),
        ):
            add(f"method_open-{slug}-{theme}-{locale}-1440.png")
        for theme, locale in (
            ("dark", "en"), ("dark", "zh"),
            ("light", "en"), ("light", "zh"),
        ):
            add(f"method_open-{slug}-{theme}-{locale}-390.png")
    # method_table_390 instance cells are discovered at capture (one start/end
    # pair per overflowing element_key). They are coverage-gated, not a
    # static declared floor — extras exemption is method_table_390_*.
    for page_name in LINEAGE_OPEN_PAGES:
        slug = page_name.replace(".html", "")
        for theme, locale in (
            ("dark", "en"), ("dark", "zh"),
            ("light", "en"), ("light", "zh"),
        ):
            add(f"lineage_open-{slug}-{theme}-{locale}-1440.png")
    # disclosure_rows_open: Method version / Owner / Trace — three crops ×
    # (8 desktop + 2 mobile) = 30 cells (rows cannot share one tight crop).
    _disclosure_rows = (
        "_rows_method_version", "_rows_owner", "_rows_trace",
    )
    for page_name in DISCLOSURE_ROWS_PAGES:
        slug = page_name.replace(".html", "")
        for theme, locale in (
            ("dark", "en"), ("dark", "zh"),
            ("light", "en"), ("light", "zh"),
        ):
            for row in _disclosure_rows:
                add(
                    f"disclosure_rows_open-{slug}-{theme}-{locale}-1440"
                    f"{row}.png"
                )
    for row in _disclosure_rows:
        for theme, locale in (
            ("dark", "en"), ("dark", "zh"),
            ("light", "en"), ("light", "zh"),
        ):
            add(
                "disclosure_rows_open-macro_financial_conditions-"
                f"{theme}-{locale}-390{row}.png"
            )
    # Labor + monetary_policy rest matrices (8 cells each).
    for page_name in (LABOR_PAGE, "macro_monetary_policy.html"):
        slug = page_name.replace(".html", "")
        for theme, locale in (
            ("dark", "en"), ("dark", "zh"),
            ("light", "en"), ("light", "zh"),
        ):
            add(f"ws-{slug}-closed-{theme}-{locale}-1440.png")
            add(f"ws-{slug}-{theme}-{locale}-390.png")
    for n, theme, locale in (
        ("17", "dark", "en"), ("17b", "light", "en"),
        ("17c", "dark", "zh"), ("17d", "light", "zh"),
    ):
        add(f"{n}-{theme}-{locale}-1440.png")
    for page_name in FIVE_PAGES:
        slug = page_name.replace(".html", "")
        for theme, locale in (
            ("dark", "en"), ("dark", "zh"),
            ("light", "en"), ("light", "zh"),
        ):
            for width in (390, 768):
                add(f"i2-{slug}-{theme}-{locale}-{width}.png")
    for name, theme, locale, _width in (
        ("18-dark-en-1440.png", "dark", "en", 1440),
        ("18b-dark-zh-1440.png", "dark", "zh", 1440),
        ("19-light-en-1440.png", "light", "en", 1440),
        ("19b-light-zh-1440.png", "light", "zh", 1440),
        ("half-dark-en-390.png", "dark", "en", 390),
        ("half-dark-zh-390.png", "dark", "zh", 390),
        ("half-light-en-390.png", "light", "en", 390),
        ("half-light-zh-390.png", "light", "zh", 390),
    ):
        add(name)
    for page_name in WORKSPACE_PAGES:
        slug = page_name.replace(".html", "")
        for theme, locale in (
            ("dark", "en"), ("dark", "zh"),
            ("light", "en"), ("light", "zh"),
        ):
            for mode in ("closed", "open"):
                if (page_name, mode, theme, locale) in _SKIP_WS_DUP:
                    continue
                add(f"ws-{slug}-{mode}-{theme}-{locale}-1440.png")
            add(f"ws-{slug}-{theme}-{locale}-390.png")
            add(f"ws-{slug}-{theme}-{locale}-390-open.png")
            add(f"ws-{slug}-{theme}-{locale}-768.png")
            for width in CHIP_MATERIAL_WIDTHS:
                add(f"chipmat-{slug}-{theme}-{locale}-{width}.png")
    # E-B1: hub_rail covers ul.mc-rail-list (+ div.mc-subtabs) on the hub.
    for theme, locale in (
        ("dark", "en"), ("dark", "zh"),
        ("light", "en"), ("light", "zh"),
    ):
        for width in (390, 768):
            for pos in ("start", "end"):
                add(f"hubrail-rail-{theme}-{locale}-{width}-{pos}.png",
                    family="hub_rail")
        for pos in ("start", "end"):
            add(f"hubrail-subtabs-{theme}-{locale}-390-{pos}.png",
                family="hub_rail")
    for page_name, receipt in appl.items():
        if not page_is_e5_bearing(receipt):
            continue
        slug = page_name.replace(".html", "")
        for theme, locale in (
            ("dark", "en"), ("dark", "zh"),
            ("light", "en"), ("light", "zh"),
        ):
            for width in (1440, 390, 768):
                if page_name == HUB_PAGE:
                    add(f"e5-{theme}-{locale}-{width}.png")
                else:
                    add(f"e5-{slug}-{theme}-{locale}-{width}.png")
    return cells


def declared_cells(
        e5_applicability: Mapping[str, Mapping[str, Any]] | None = None,
        ) -> list[str]:
    return [row["file"] for row in declared_cell_rows(e5_applicability)]


def declared_families(
        e5_applicability: Mapping[str, Mapping[str, Any]] | None = None,
        ) -> dict[str, list[str]]:
    families: dict[str, list[str]] = {}
    for row in declared_cell_rows(e5_applicability):
        families.setdefault(row["family"], []).append(row["file"])
    return families


def _fallback_counts(html: str) -> dict[str, int]:
    from lib.macro_suite_labels import PLAIN_FALLBACK
    return {
        "fallback_count_en": html.count(PLAIN_FALLBACK["en"]),
        "fallback_count_zh": html.count(PLAIN_FALLBACK["zh"]),
    }


def _topic_styles(page) -> dict[str, Any]:
    return page.evaluate(
        """() => {
            const el = document.querySelector(
                '.mc-read-topic[data-mc-topic="money"]')
                || document.querySelector('.mc-read-topic');
            if (!el) return {ok: false, reason: 'no .mc-read-topic'};
            const cs = getComputedStyle(el);
            const bg = cs.backgroundImage || '';
            const haloToken = parseFloat(cs.getPropertyValue('--mc-halo') || '0') || 0;
            const halo = haloToken > 0.01 && bg.includes('radial-gradient');
            const underline = parseFloat(cs.borderBottomWidth || '0') || 0;
            return {
                ok: true,
                text: (el.textContent || '').trim(),
                backgroundImage: bg,
                halo_token: haloToken,
                halo,
                borderBottomWidth: cs.borderBottomWidth,
                borderBottomStyle: cs.borderBottomStyle,
                underline_px: underline,
                color: cs.color,
            };
        }""")


def _i2_from_stations(boot: Mapping[str, Any], mid: Mapping[str, Any],
                      mx: Mapping[str, Any]) -> dict[str, Any]:
    """i2 is a rollup of boot/mid/max — not a second measure of the same boxes."""
    samples = (boot, mid, mx)
    merged_ok = True
    for row in samples:
        try:
            assert_merged_geometry(row)
        except RuntimeError:
            merged_ok = False
            break
        if row.get("analystMergedInto") and row.get("mergeBasis") != "geometry":
            merged_ok = False
    return {
        "ok": bool(samples) and merged_ok
        and all(clearance_probe_ok(row) for row in samples),
        "derivedFrom": ["boot", "mid", "max"],
    }


def main() -> int:
    from playwright.sync_api import sync_playwright

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    start_tree = _require_clean_tree(when="start")
    tree_clean_start = start_tree["clean"]
    head_start = start_tree["head"]
    commit_time = subprocess.check_output(
        ["git", "log", "-1", "--format=%cI", head_start],
        cwd=ROOT, text=True).strip()
    generated_at_start = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(
        f"capturing site at head {head_start} tree_clean_start={tree_clean_start}",
        flush=True,
    )

    states: list[dict[str, Any]] = []
    gaps: list[str] = []
    for stale in EVIDENCE.glob("*.png"):
        stale.unlink()
    fallback_probes: dict[str, Any] = {}
    for page_name in FIVE_PAGES:
        site_path = SITE / page_name
        if site_path.is_file():
            counts = _fallback_counts(site_path.read_text(encoding="utf-8"))
        else:
            counts = {"fallback_count_en": None, "fallback_count_zh": None,
                      "reason": "site/ omitted"}
        fallback_probes[page_name] = counts
    probes: dict[str, Any] = {
        "fallback_count_en": {
            name: counts.get("fallback_count_en")
            for name, counts in fallback_probes.items()
        },
        "fallback_count_zh": {
            name: counts.get("fallback_count_zh")
            for name, counts in fallback_probes.items()
        },
    }
    harness_files: list[Path] = []
    ws_states: dict[str, list[dict[str, Any]]] = {
        page: [] for page in WORKSPACE_PAGES}
    mo_states: dict[str, list[dict[str, Any]]] = {
        page: [] for page in METHOD_OPEN_PAGES}
    probes["method_open_text"] = {}

    try:
        _proc, origin = _serve(SITE)
    except Exception:
        _kill_all()
        raise

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)

            # C-M1: page_fits once per route × width × locale BEFORE any crop.
            print("probe page_fits matrix (15×4×2×2)", flush=True)
            page_fits_rows = _probe_page_fits_matrix(browser, origin=origin)
            probes["page_fits"] = page_fits_rows

            # E-B1: hub rail + subtabs covering frames (before other crops).
            _capture_hub_rail_family(browser, origin=origin, dest_states=states)

            # 1–4 above the fold
            for n, theme, locale in (
                ("01", "dark", "en"), ("02", "dark", "zh"),
                ("03", "light", "en"), ("04", "light", "zh"),
            ):
                name = f"{n}-{theme}-{locale}-1440.png"
                print(f"capture {name}", flush=True)
                ctx, page, _ = _open(
                    browser=browser, origin=origin,
                    path="/macro_monetary.html", theme=theme, locale=locale,
                    width=1440, height=900)
                page.wait_for_selector(".mc-read", timeout=15000)
                page.wait_for_selector(".mc-strip", timeout=15000)
                info = _viewport_shot(
                    EVIDENCE / name, page, width=1440, height=900)
                states.append(_state(
                    name, theme, locale, "desktop", info, viewport_width=1440,
                    viewport_height=900,
                    verified_how="Playwright 1440×900 fold dpr=2; eyebrow+H1+Read+chips",
                ))
                full_name = f"{n}-{theme}-{locale}-1440-full.png"
                full_info = _viewport_shot(
                    EVIDENCE / full_name, page, width=1440, height=900,
                    full_page=True)
                states.append(_state(
                    full_name, theme, locale, "desktop", full_info,
                    viewport_width=1440, viewport_height=900,
                    verified_how="Playwright 1440 full-page twin of the fold cell",
                ))
                ctx.close()

            # 5–8 #rates panel full
            for n, theme, locale in (
                ("05", "dark", "en"), ("06", "dark", "zh"),
                ("07", "light", "en"), ("08", "light", "zh"),
            ):
                name = f"{n}-{theme}-{locale}-1440.png"
                print(f"capture {name}", flush=True)
                ctx, page, _ = _open(
                    browser=browser, origin=origin,
                    path="/macro_monetary.html#rates", theme=theme, locale=locale,
                    width=1440, height=2800)
                page.wait_for_selector("section#rates", timeout=15000)
                primer = page.locator("section#rates details.mc-primer")
                if primer.count():
                    primer.first.evaluate("el => { el.open = true; }")
                info = _shot(
                    EVIDENCE / name, page, page.locator("section#rates"),
                    selector="section#rates", locale=locale)
                states.append(_state(
                    name, theme, locale, "desktop", info, viewport_width=1440,
                    verified_how="clip section#rates; primer forced open; details closed",
                    crop=True, selector="section#rates", force_state="rates_panel",
                ))
                ctx.close()

            # 9–12 390 iframe
            for n, theme, locale in (
                ("09", "dark", "en"), ("10", "dark", "zh"),
                ("11", "light", "en"), ("12", "light", "zh"),
            ):
                name = f"{n}-{theme}-{locale}-390.png"
                print(f"capture {name}", flush=True)
                ctx, page, frame = _open(
                    browser=browser, origin=origin,
                    path="/macro_monetary.html", theme=theme, locale=locale,
                    width=1440, height=900, iframe_width=390)
                frame.locator(".mc-read").wait_for(timeout=15000)
                info = _shot(
                    EVIDENCE / name, page, page.locator("#mc-p5-frame"),
                    selector="#mc-p5-frame", locale=locale)
                states.append(_state(
                    name, theme, locale, "mobile", info, viewport_width=390,
                    verified_how="390 CSS-wide iframe harness; crop to iframe content box",
                    crop=True, selector="#mc-p5-frame",
                ))
                ctx.close()

            # 13–14 768 + two-segment hash caption — full dark/light × EN/ZH
            for n, theme, locale in (
                ("13", "dark", "en"), ("13b", "dark", "zh"),
                ("14", "light", "en"), ("14b", "light", "zh"),
            ):
                name = f"{n}-{theme}-{locale}-768.png"
                print(f"capture {name}", flush=True)
                ctx, page, frame = _open(
                    browser=browser, origin=origin,
                    path="/macro_monetary.html#credit/funding",
                    theme=theme, locale=locale,
                    width=1440, height=1100, iframe_width=768,
                    caption="/macro_monetary.html#credit/funding")
                frame.locator("section#credit").wait_for(timeout=15000)
                info = _shot(
                    EVIDENCE / name, page, page.locator("#mc-p5-frame"),
                    selector="#mc-p5-frame", locale=locale)
                states.append(_state(
                    name, theme, locale, "tablet", info, viewport_width=768,
                    viewport_height=844,
                    verified_how="768 iframe crop of #mc-p5-frame; #credit/funding caption",
                    crop=True, selector="#mc-p5-frame",
                    force_state="tablet_768",
                ))
                ctx.close()

            # 15–16 workspace details OPEN — full 2×2 at 1440
            for n, theme, locale in (
                ("15", "dark", "en"), ("15b", "dark", "zh"),
                ("16", "light", "zh"), ("16b", "light", "en"),
            ):
                name = f"{n}-{theme}-{locale}-1440.png"
                print(f"capture {name}", flush=True)
                ctx, page, _ = _open(
                    browser=browser, origin=origin,
                    path="/macro_rates_curves.html", theme=theme, locale=locale,
                    width=1440, height=2800)
                page.wait_for_selector(".mq-implication-text", timeout=15000)
                _open_ribbon_details(page)
                probes[f"copy_{n}"] = _copy_probe(page, _relocated_needles(locale))
                info = _shot(
                    EVIDENCE / name, page, page.locator(".mq-ribbon"),
                    selector=".mq-ribbon", locale=locale)
                ws_states["macro_rates_curves.html"].append(_state(
                    name, theme, locale, "desktop", info, viewport_width=1440,
                    verified_how="macro_rates_curves relocated implication details.open; §5 strings readable",
                    crop=True, selector=".mq-ribbon", force_state="details_open",
                ))
                ctx.close()

            # 17 / 17b / 17c / 17d Read-word computed styles (dark/light × EN/ZH)
            # C-m1: pin the money topic — `.mc-read-topic` matches 5 chips.
            READ_TOPIC_SEL = '.mc-read-topic[data-mc-topic="money"]'
            style_rows = {}
            for n, theme, locale in (
                ("17", "dark", "en"), ("17b", "light", "en"),
                ("17c", "dark", "zh"), ("17d", "light", "zh"),
            ):
                name = f"{n}-{theme}-{locale}-1440.png"
                print(f"capture {name}", flush=True)
                ctx, page, _ = _open(
                    browser=browser, origin=origin,
                    path="/macro_monetary.html", theme=theme, locale=locale,
                    width=1440, height=2200)
                page.wait_for_selector(READ_TOPIC_SEL, timeout=15000)
                styles = _topic_styles(page)
                style_rows[n] = styles
                topic = page.locator(READ_TOPIC_SEL)
                info = _shot(
                    EVIDENCE / name, page, topic,
                    selector=READ_TOPIC_SEL, locale=locale)
                states.append(_state(
                    name, theme, locale, "desktop", info, viewport_width=1440,
                    verified_how=(
                        "element clip of .mc-read-topic[data-mc-topic=money]; "
                        "computed style in probes.json"
                    ),
                    crop=True, selector=READ_TOPIC_SEL, force_state="read_word",
                ))
                ctx.close()
            probes["read_word_17"] = style_rows.get("17")
            probes["read_word_17b"] = style_rows.get("17b")
            probes["read_word_17c"] = style_rows.get("17c")
            probes["read_word_17d"] = style_rows.get("17d")
            dark_s, light_s = style_rows["17"], style_rows["17b"]
            probes["read_word_contrast_ok"] = bool(
                dark_s.get("halo") and dark_s.get("underline_px", 1) < 0.5
                and (not light_s.get("halo")) and light_s.get("underline_px", 0) >= 1.5
            )

            # B2 clearance at 390 and 768 × dark/light × EN/ZH on all five pages
            clearance_ok = True
            i2_ok = True
            clear_pages = FIVE_PAGES
            for page_name in clear_pages:
                for width in (390, 768, 1440):
                    for theme, locale in (
                        ("dark", "en"), ("dark", "zh"),
                        ("light", "en"), ("light", "zh"),
                    ):
                        slug = page_name.replace(".html", "")
                        key = f"clear_{slug}_{width}_{theme}_{locale}"
                        print(f"probe clearance {key}", flush=True)
                        wait = ".mc-analyst" if page_name == "macro_monetary.html" else ".mq-suitenav .mc-analyst, .mq-implication-text"
                        if width == 1440:
                            ctx, page, _ = _open(
                                browser=browser, origin=origin,
                                path=f"/{page_name}", theme=theme, locale=locale,
                                width=1440, height=900)
                            page.locator(wait).first.wait_for(timeout=15000)
                            loc = page.locator("html")
                            frame = None
                        else:
                            ctx, page, frame = _open(
                                browser=browser, origin=origin,
                                path=f"/{page_name}", theme=theme, locale=locale,
                                width=1440, height=900, iframe_width=width)
                            frame.locator(wait).first.wait_for(timeout=15000)
                            loc = frame.locator("html")
                        boot = _clearance_probe(loc, position=0.0)
                        mid = _clearance_probe(loc, position=0.5)
                        mx = _clearance_probe(loc, position=1.0)
                        i2 = _i2_from_stations(boot, mid, mx)
                        row = {
                            "boot": boot, "mid": mid, "max": mx, "i2": i2,
                            "ok": bool(clearance_probe_ok(boot)
                                       and clearance_probe_ok(mid)
                                       and clearance_probe_ok(mx)),
                            "page": page_name,
                        }
                        probes[key] = row
                        clearance_ok = clearance_ok and row["ok"]
                        i2_ok = i2_ok and bool(i2.get("ok"))
                        host = frame.locator("html") if frame is not None else page
                        mat_key = f"chip_material_{slug}_{theme}_{locale}_{width}"
                        probes[mat_key] = _chip_material_probe(
                            host, page_name=page_name, locale=locale,
                            width=width)
                        if page_name != HUB_PAGE:
                            host.evaluate("() => window.scrollTo(0, 0)")
                            probes[mat_key]["probeBeforeShot"] = True
                            rail_root_pre = host
                            # Text at scrollLeft=0 before intentional scroll (E-B1).
                            rail_sel_guess = "ul.mq-suitenav-rail"
                            text_zero = ""
                            if rail_root_pre.locator(rail_sel_guess).count() == 1:
                                text_zero = str(
                                    rail_root_pre.locator(rail_sel_guess).evaluate(
                                        _RAIL_VISIBLE_TEXT_JS, locale) or "")
                            rail_scroll = host.evaluate(_SCROLL_RAIL_CHIP_JS)
                            probes[mat_key]["scrollResult"] = rail_scroll
                            if not rail_scroll.get("ok"):
                                raise RuntimeError(
                                    f"{mat_key}: scrollResult ok:false "
                                    f"{rail_scroll}")
                            chip_sel = str(rail_scroll.get("chipSelector") or "")
                            pill_sel = str(
                                rail_scroll.get("siblingPillSelector") or "")
                            if not chip_sel or not pill_sel or chip_sel == pill_sel:
                                raise RuntimeError(
                                    f"{mat_key}: selectors must identify "
                                    f"distinct elements: {chip_sel!r} "
                                    f"{pill_sel!r}")
                            html = rail_inner_html_identity(
                                str(rail_scroll.get("railInnerHtml") or ""))
                            crop_dom = str(rail_scroll.get("cropDomHtml") or "")
                            probes[mat_key]["railScrollLeft"] = rail_scroll.get(
                                "railScrollLeft")
                            probes[mat_key]["scrollLeftBefore"] = (
                                rail_scroll.get("scrollLeftBefore"))
                            probes[mat_key]["scrollLeftAfter"] = (
                                rail_scroll.get("scrollLeftAfter"))
                            probes[mat_key]["scrollContainerSelector"] = (
                                rail_scroll.get("scrollContainerSelector"))
                            probes[mat_key]["railInnerHtmlSha256"] = (
                                hashlib.sha256(html.encode("utf-8")).hexdigest())
                            probes[mat_key]["cropDomSha256"] = (
                                hashlib.sha256(
                                    crop_dom.encode("utf-8")).hexdigest())
                            probes[mat_key]["chipSelector"] = chip_sel
                            probes[mat_key]["siblingPillSelector"] = pill_sel
                            probes[mat_key]["chipLabel"] = rail_scroll.get(
                                "chipLabel")
                            probes[mat_key]["siblingPillLabel"] = (
                                rail_scroll.get("siblingPillLabel"))
                            probes[mat_key]["analystBox"] = rail_scroll.get(
                                "analystBox")
                            probes[mat_key]["siblingPillBox"] = (
                                rail_scroll.get("siblingPillBox"))
                            probes[mat_key]["cropBox"] = rail_scroll.get(
                                "cropBox")
                            probes[mat_key]["chipmatPairFits"] = (
                                rail_scroll.get("chipmatPairFits"))
                            probes[mat_key]["pairWidth"] = rail_scroll.get(
                                "pairWidth")
                            probes[mat_key]["containerWidth"] = (
                                rail_scroll.get("containerWidth"))
                            probes[mat_key]["elementTextHead"] = (
                                rail_scroll.get("elementTextHead"))
                            assert_chipmat_containment(
                                probes[mat_key], key=mat_key)
                            chipmat_name = (
                                f"chipmat-{slug}-{theme}-{locale}-{width}.png")
                            print(f"capture {chipmat_name}", flush=True)
                            host_offset = _host_frame_offset(page, frame)
                            host_scroll_y = _read_scroll(page)
                            frame_inner = width
                            if frame is not None:
                                frame_inner = int(round(float(
                                    frame.locator("html").evaluate(
                                        "() => window.innerWidth"))))
                            page_clip = _page_space_clip(
                                page, frame, rail_scroll["cropBox"])
                            host_analyst = _to_host_page(
                                rail_scroll.get("analystBox"),
                                host_offset, host_scroll_y)
                            host_pill = _to_host_page(
                                rail_scroll.get("siblingPillBox"),
                                host_offset, host_scroll_y)
                            host_crop = _to_host_page(
                                rail_scroll.get("cropBox"),
                                host_offset, host_scroll_y)
                            probes[mat_key]["coordSpace"] = (
                                "iframe" if frame is not None else "host")
                            probes[mat_key]["hostFrameOffset"] = host_offset
                            probes[mat_key]["host_scroll_y_at_shot"] = (
                                host_scroll_y)
                            probes[mat_key]["frameInnerWidth"] = frame_inner
                            if frame is not None:
                                probes[mat_key]["frameInnerHeight"] = int(round(
                                    float(frame.locator("html").evaluate(
                                        "() => window.innerHeight") or 0)))
                            probes[mat_key]["analystBoxHost"] = host_analyst
                            probes[mat_key]["siblingPillBoxHost"] = host_pill
                            probes[mat_key]["cropBoxHost"] = host_crop
                            rail_sel = str(
                                rail_scroll.get("scrollContainerSelector")
                                or "").strip()
                            if not rail_sel:
                                raise RuntimeError(
                                    f"{chipmat_name}: missing "
                                    "scrollContainerSelector")
                            # Crop inside the customer document (iframe body).
                            rail_root = host if frame is not None else page
                            n_rail = rail_root.locator(rail_sel).count()
                            if n_rail != 1:
                                raise RuntimeError(
                                    f"{chipmat_name}: crop_selector "
                                    f"{rail_sel!r} matched {n_rail} "
                                    "(must be exactly one; no substitution)")
                            rail_loc = rail_root.locator(rail_sel)
                            text_at = str(rail_loc.evaluate(
                                _RAIL_VISIBLE_TEXT_JS, locale) or "")
                            info = _element_shot_guarded(
                                EVIDENCE / chipmat_name, page, rail_loc,
                                selector=rail_sel, locale=locale,
                                viewport_width=width,
                                target_for_nav=page,
                                family="chip_material",
                                receipt_locator=(
                                    frame.locator("body").first
                                    if frame is not None else None),
                            )
                            if probes[mat_key].get("cropDomSha256"):
                                info["cropDomSha256"] = str(
                                    probes[mat_key]["cropDomSha256"])
                            info["page_id"] = page_name
                            info["analystBox"] = host_analyst
                            info["siblingPillBox"] = host_pill
                            info["visible_text_at_scroll"] = text_at
                            info["visible_text_at_zero"] = text_zero
                            # Leave coordSpace from _element_shot_guarded when
                            # iframe-hosted (E-m1); only set host for native.
                            if frame is None:
                                info["coordSpace"] = "host"
                            info["hostFrameOffset"] = host_offset
                            info["host_scroll_y_at_shot"] = host_scroll_y
                            info["frameInnerWidth"] = frame_inner
                            dest_states = ws_states[page_name]
                            dest_states.append(_state(
                                chipmat_name, theme, locale,
                                "desktop" if width == 1440 else (
                                    "mobile" if width == 390 else "tablet"),
                                info, viewport_width=width,
                                verified_how=(
                                    f"{page_name} chip+pill after "
                                    f"{rail_sel} "
                                    f"scrollLeft={rail_scroll.get('scrollLeftAfter')} "
                                    f"unmutated pairFits="
                                    f"{rail_scroll.get('chipmatPairFits')}"),
                                crop=True,
                                selector=rail_sel,
                                force_state="chipmat",
                                family="chip_material",
                            ))
                        if width != 1440:
                            i2_name = f"i2-{slug}-{theme}-{locale}-{width}.png"
                            print(f"capture {i2_name}", flush=True)
                            i2_host = (
                                page.frame_locator("#mc-p5-frame").locator("html")
                                if frame is not None else page.locator("html"))
                            i2_prep = i2_host.evaluate(_PREPARE_I2_JS)
                            page.wait_for_timeout(80)
                            info = _shot(
                                EVIDENCE / i2_name, page,
                                page.locator("#mc-p5-frame") if frame is not None
                                else page.locator("html"),
                                selector="#mc-p5-frame" if frame is not None
                                else "html", locale=locale)
                            dest_states = states if page_name == "macro_monetary.html" else ws_states[page_name]
                            dest_states.append(_state(
                                i2_name, theme, locale,
                                "mobile" if width == 390 else "tablet", info,
                                viewport_width=width,
                                verified_how=(
                                    f"{page_name} {width} iframe; clearance "
                                    f"scrollY={i2_prep.get('scrollY')} "
                                    f"max={i2_prep.get('max')} "
                                    f"detailsOpen={i2_prep.get('opened')}"),
                                crop=True,
                                selector="#mc-p5-frame" if frame is not None
                                else "html",
                                force_state="clearance_i2",
                            ))
                        ctx.close()
            merged_ok = True
            for probe_key, probe_row in probes.items():
                if not str(probe_key).startswith("clear_"):
                    continue
                if not isinstance(probe_row, dict):
                    continue
                for station in (probe_row.get("boot"), probe_row.get("mid"),
                                probe_row.get("max")):
                    if not isinstance(station, dict):
                        continue
                    try:
                        assert_merged_geometry(station)
                    except RuntimeError:
                        merged_ok = False
                    if (station.get("analystMergedInto")
                            and station.get("mergeBasis") != "geometry"):
                        merged_ok = False
            probes["i2_ok"] = bool(i2_ok and clearance_ok and merged_ok)

            # ZH + EN chip-opens-chat at 390/768 on the five pages
            for page_name in clear_pages:
                for width in (390, 768):
                    for theme, locale in (
                        ("dark", "en"), ("dark", "zh"),
                        ("light", "en"), ("light", "zh"),
                    ):
                        slug = page_name.replace(".html", "")
                        key = f"chip_opens_chat_{slug}_{width}_{theme}_{locale}"
                        print(f"probe {key}", flush=True)
                        ctx, page, frame = _open(
                            browser=browser, origin=origin,
                            path=f"/{page_name}", theme=theme, locale=locale,
                            width=1440, height=900, iframe_width=width)
                        host = frame
                        host.locator(".mc-analyst").first.wait_for(timeout=15000)
                        probes[key] = _run_chip_opens_chat(
                            page.frame_locator("#mc-p5-frame"),
                            page_name=page_name, locale=locale, width=width)
                        ctx.close()

            # R2 / M2: E5 cells come FROM e5_applicability (DOM).
            e5_applicability: dict[str, dict[str, Any]] = {}
            for page_name in clear_pages:
                path = SITE / page_name
                if not path.is_file():
                    raise RuntimeError(f"missing site file: {path}")
                ctx, page, _ = _open(
                    browser=browser, origin=origin,
                    path=f"/{page_name}", theme="dark", locale="en",
                    width=1440, height=900)
                page.wait_for_selector("body", timeout=15000)
                e5_applicability[page_name] = e5_applicability_from_dom(page)
                ctx.close()
            probes["e5_applicability"] = e5_applicability
            for page_name, receipt in e5_applicability.items():
                if not page_is_e5_bearing(receipt):
                    continue
                slug = page_name.replace(".html", "")
                hash_path = "#rates" if page_name == HUB_PAGE else ""
                for theme, locale in (
                    ("dark", "en"), ("dark", "zh"),
                    ("light", "en"), ("light", "zh"),
                ):
                    for width, viewport in (
                        (1440, "desktop"), (390, "mobile"), (768, "tablet"),
                    ):
                        key = f"e5_timeout_{slug}_{theme}_{locale}_{width}"
                        print(f"probe {key}", flush=True)
                        if width == 1440:
                            ctx, page, _ = _open(
                                browser=browser, origin=origin,
                                path=f"/{page_name}{hash_path}",
                                theme=theme, locale=locale,
                                width=1440, height=900)
                        else:
                            ctx, page, _frame = _open(
                                browser=browser, origin=origin,
                                path=f"/{page_name}{hash_path}",
                                theme=theme, locale=locale,
                                width=1440, height=900, iframe_width=width)
                        probes[key] = _run_e5_timeout(page, context=ctx)
                        if probes[key].get("ok"):
                            shot = (
                                f"e5-{theme}-{locale}-{width}.png"
                                if page_name == HUB_PAGE
                                else f"e5-{slug}-{theme}-{locale}-{width}.png")
                            if width == 1440:
                                info = _viewport_shot(
                                    EVIDENCE / shot, page,
                                    width=1440, height=900)
                            else:
                                info = _shot(
                                    EVIDENCE / shot, page,
                                    page.locator("#mc-p5-frame"),
                                    selector="#mc-p5-frame", locale=locale)
                            dest = (
                                states if page_name == HUB_PAGE
                                else ws_states[page_name])
                            dest.append(_state(
                                shot, theme, locale, viewport, info,
                                viewport_width=width,
                                verified_how="E5 cloned after stalled fragment ≥8000ms",
                                force_state="empty-e5",
                                crop=width != 1440,
                                selector=(
                                    "#mc-p5-frame" if width != 1440 else None),
                                family="e5",
                            ))
                        ctx.close()

            # Rail-viewport: hub uses P3's parsed-mask probe; workspace
            # measures the suite-nav rail / tab strip at 390 and 768.
            for page_name in clear_pages:
                for width in (390, 768):
                    for theme, locale in (
                        ("dark", "en"), ("dark", "zh"),
                        ("light", "en"), ("light", "zh"),
                    ):
                        slug = page_name.replace(".html", "")
                        key = f"rail_viewport_{slug}_{theme}_{locale}_{width}"
                        print(f"probe {key}", flush=True)
                        ctx, page, frame = _open(
                            browser=browser, origin=origin,
                            path=f"/{page_name}", theme=theme, locale=locale,
                            width=1440, height=900, iframe_width=width)
                        host = frame.locator("html")
                        if page_name == "macro_monetary.html":
                            host.locator(".mc-rail-list").wait_for(timeout=15000)
                            probes[key] = host.evaluate(RAIL_VIEWPORT_JS)
                        else:
                            host.locator(".mq-suitenav-rail, .mq-tabbar").first.wait_for(
                                timeout=15000)
                            probes[key] = host.evaluate(WORKSPACE_RAIL_VIEWPORT_JS)
                        ctx.close()

            # 18–19 half-null fixture (read.omitted + null chips + E2 + E6)
            from scripts import capture_macro_command_p4 as p4cap
            import tempfile
            tmp = Path(tempfile.mkdtemp(prefix="mc-p5-halfnull-"))
            def _null_headline(entry: dict[str, Any]) -> None:
                entry["snapshot"]["headline"]["status"] = "ABSENT"
                entry["snapshot"]["headline"]["state_id"] = None
                entry["snapshot"]["headline"]["effective_date"] = None
                entry["snapshot"]["headline"]["null_reason"] = "NOT_YET_RELEASED"

            def _half_null(entries):
                for entry in entries:
                    wid = entry["workspace_id"]
                    if wid == "housing_real_estate":
                        entry["snapshot"]["availability"]["state"] = "SOURCE_FAILED"
                        _null_headline(entry)
                        entry["snapshot"]["changes"]["deltas"] = []
                    if wid == "capital_structure":
                        entry["snapshot"]["entitlement"] = "Research"
                    if wid in ("labor_markets", "growth_real_economy"):
                        _null_headline(entry)
            try:
                site_half = p4cap._build_memory_hub(tmp, "e2", _half_null)
                credit_frag = (site_half / "macro" / "fragments" / "credit.html")
                credit_html = credit_frag.read_text(encoding="utf-8") if credit_frag.exists() else ""
                if 'data-mc-empty="e6"' not in credit_html:
                    raise RuntimeError(
                        "credit fragment missing data-mc-empty=e6 after "
                        "capital_structure entitlement=Research")
                _hp, half_origin = _serve(site_half)
                half_ok = False
                last_markers: dict[str, Any] = {}
                half_jobs = [
                    ("18-dark-en-1440.png", "dark", "en", 1440),
                    ("18b-dark-zh-1440.png", "dark", "zh", 1440),
                    ("19-light-en-1440.png", "light", "en", 1440),
                    ("19b-light-zh-1440.png", "light", "zh", 1440),
                    ("half-dark-en-390.png", "dark", "en", 390),
                    ("half-dark-zh-390.png", "dark", "zh", 390),
                    ("half-light-en-390.png", "light", "en", 390),
                    ("half-light-zh-390.png", "light", "zh", 390),
                ]
                for name, theme, locale, width in half_jobs:
                    dest = EVIDENCE / name
                    if dest.exists():
                        dest.unlink()
                    print(f"capture {name} (half-null fixture)", flush=True)
                    if width == 390:
                        ctx, page, frame = _open(
                            browser=browser, origin=half_origin,
                            path="/macro_monetary.html#housing", theme=theme,
                            locale=locale, width=1440, height=900,
                            iframe_width=390, harness_root=site_half)
                        target = frame
                    else:
                        ctx, page, _ = _open(
                            browser=browser, origin=half_origin,
                            path="/macro_monetary.html#housing", theme=theme,
                            locale=locale, width=1440, height=2800)
                        target = page
                    host = target if width == 390 else page
                    js = host if hasattr(host, "evaluate") else host.locator(":root")
                    host.locator(".mc-read").wait_for(timeout=15000)
                    host.locator('[data-mc-empty="e2"]').wait_for(timeout=15000)
                    js.evaluate("location.hash = '#credit/funding'")
                    host.locator('[data-mc-empty="e6"]').wait_for(timeout=15000)
                    js.evaluate(
                        """() => {
                            document.querySelectorAll('[data-mc-panel]').forEach(p => {
                                const id = p.getAttribute('data-mc-panel');
                                if (id === 'housing' || id === 'credit') {
                                    p.hidden = false;
                                }
                            });
                            const funding = document.querySelector(
                                '[data-mc-tabbody="funding"]');
                            if (funding) funding.hidden = false;
                        }""")
                    page.wait_for_timeout(400)
                    markers = js.evaluate(
                        """() => ({
                            omitted: !!document.querySelector('.mc-read-omitted'),
                            null_chips: document.querySelectorAll('.mc-chip.is-null').length,
                            e2: !!document.querySelector('[data-mc-empty="e2"]'),
                            e6: !!document.querySelector('[data-mc-empty="e6"]'),
                            e2_visible: !!(document.querySelector('[data-mc-empty="e2"]')
                                && document.querySelector('[data-mc-empty="e2"]')
                                    .getBoundingClientRect().height > 0),
                            e6_visible: !!(document.querySelector('[data-mc-empty="e6"]')
                                && document.querySelector('[data-mc-empty="e6"]')
                                    .getBoundingClientRect().height > 0),
                        })""")
                    last_markers = markers
                    needed = (markers["omitted"] and markers["null_chips"] >= 2
                              and markers["e2"] and markers["e6"]
                              and markers["e2_visible"] and markers["e6_visible"])
                    viewport_name = "mobile" if width == 390 else "desktop"
                    if not needed:
                        reason = (
                            "half-null fixture missing a named cell: "
                            f"{markers}"
                        )
                        states.append(_gap_state(
                            name, theme, locale, viewport_name, reason, width))
                        gaps.append(f"Frame {name}: {reason}")
                    else:
                        if width == 390:
                            info = _shot(
                                dest, page, page.locator("#mc-p5-frame"),
                                selector="#mc-p5-frame", locale=locale)
                        else:
                            info = _viewport_shot(
                                dest, page, width=1440, height=2800)
                        states.append(_state(
                            name, theme, locale, viewport_name, info,
                            viewport_width=width,
                            verified_how="in-memory half-null: read.omitted + ≥2 null chips + E2 housing + E6 credit",
                            fixture=True, force_state="half-null",
                            crop=width == 390, selector="#mc-p5-frame" if width == 390 else None,
                            trigger="in-memory: housing SOURCE_FAILED + capital_structure entitlement=Research",
                        ))
                        half_ok = True
                    ctx.close()
                probes["half_null_markers"] = last_markers
                probes["half_null_ok"] = half_ok
            except Exception as exc:
                already = {st.get("file") for st in states if st.get("captured")}
                for name, theme, locale, width in (
                    ("18-dark-en-1440.png", "dark", "en", 1440),
                    ("18b-dark-zh-1440.png", "dark", "zh", 1440),
                    ("19-light-en-1440.png", "light", "en", 1440),
                    ("19b-light-zh-1440.png", "light", "zh", 1440),
                    ("half-dark-en-390.png", "dark", "en", 390),
                    ("half-dark-zh-390.png", "dark", "zh", 390),
                    ("half-light-en-390.png", "light", "en", 390),
                    ("half-light-zh-390.png", "light", "zh", 390),
                ):
                    if name in already:
                        continue
                    states.append(_gap_state(
                        name, theme, locale,
                        "desktop" if width == 1440 else "mobile",
                        f"half-null fixture build failed: {exc}", width))
                    gaps.append(f"Frame {name}: half-null fixture failed ({exc}).")

            # Workspace extension: closed + open at 1440, dark EN + light ZH at 390
            for page_name in WORKSPACE_PAGES:
                for theme, locale in (
                    ("dark", "en"), ("dark", "zh"),
                    ("light", "en"), ("light", "zh"),
                ):
                    for mode in ("closed", "open"):
                        if (page_name, mode, theme, locale) in _SKIP_WS_DUP:
                            continue
                        name = (
                            f"ws-{page_name.replace('.html','')}-"
                            f"{mode}-{theme}-{locale}-1440.png"
                        )
                        print(f"capture {name}", flush=True)
                        ctx, page, _ = _open(
                            browser=browser, origin=origin,
                            path=f"/{page_name}", theme=theme, locale=locale,
                            width=1440, height=2400)
                        page.wait_for_selector(".mq-implication-text", timeout=15000)
                        block = page.locator(".mq-ribbon").first
                        if mode == "open":
                            details = page.locator(".mq-implication .mc-details")
                            if details.count():
                                details.first.evaluate("el => { el.open = true; }")
                        if mode == "open":
                            info = _shot(
                                EVIDENCE / name, page, block,
                                selector=".mq-ribbon", locale=locale)
                            ws_states[page_name].append(_state(
                                name, theme, locale, "desktop", info,
                                viewport_width=1440,
                                verified_how=f"{page_name} ribbon; details {mode}",
                                crop=True, selector=".mq-ribbon",
                                force_state="details_open",
                            ))
                        else:
                            info = _viewport_shot(
                                EVIDENCE / name, page, width=1440, height=2400)
                            ws_states[page_name].append(_state(
                                name, theme, locale, "desktop", info,
                                viewport_width=1440,
                                verified_how=f"{page_name} first screen; details {mode}",
                            ))
                        ctx.close()
                for theme, locale in (
                    ("dark", "en"), ("dark", "zh"),
                    ("light", "en"), ("light", "zh"),
                ):
                    for mode in ("closed", "open"):
                        suffix = "" if mode == "closed" else "-open"
                        name = (
                            f"ws-{page_name.replace('.html','')}-"
                            f"{theme}-{locale}-390{suffix}.png"
                        )
                        print(f"capture {name}", flush=True)
                        ctx, page, frame = _open(
                            browser=browser, origin=origin,
                            path=f"/{page_name}", theme=theme, locale=locale,
                            width=1440, height=900, iframe_width=390)
                        frame.locator(".mq-implication-text").first.wait_for(
                            timeout=15000)
                        if mode == "open":
                            details = frame.locator(".mq-implication .mc-details")
                            if details.count():
                                details.first.evaluate("el => { el.open = true; }")
                        info = _shot(
                            EVIDENCE / name, page, page.locator("#mc-p5-frame"),
                            selector="#mc-p5-frame", locale=locale)
                        ws_states[page_name].append(_state(
                            name, theme, locale, "mobile", info, viewport_width=390,
                            verified_how=f"{page_name} 390 iframe; details {mode}",
                            crop=True, selector="#mc-p5-frame",
                            force_state="details_open" if mode == "open" else None,
                        ))
                        ctx.close()
                for theme, locale in (
                    ("dark", "en"), ("dark", "zh"),
                    ("light", "en"), ("light", "zh"),
                ):
                    name = (
                        f"ws-{page_name.replace('.html','')}-"
                        f"{theme}-{locale}-768.png"
                    )
                    print(f"capture {name}", flush=True)
                    ctx, page, frame = _open(
                        browser=browser, origin=origin,
                        path=f"/{page_name}", theme=theme, locale=locale,
                        width=1440, height=1100, iframe_width=768)
                    frame.locator(".mq-implication-text").first.wait_for(
                        timeout=15000)
                    info = _shot(
                        EVIDENCE / name, page, page.locator("#mc-p5-frame"),
                        selector="#mc-p5-frame", locale=locale)
                    ws_states[page_name].append(_state(
                        name, theme, locale, "tablet", info, viewport_width=768,
                        viewport_height=844,
                        verified_how=f"{page_name} 768 iframe; first screen",
                        crop=True, selector="#mc-p5-frame",
                        force_state="tablet_768",
                    ))
                    ctx.close()

            # Labor rest matrix — honest page entry (option a), not hung on FC.
            labor_states: list[dict[str, Any]] = []
            for theme, locale in (
                ("dark", "en"), ("dark", "zh"),
                ("light", "en"), ("light", "zh"),
            ):
                name = (
                    f"ws-{LABOR_PAGE.replace('.html', '')}-"
                    f"closed-{theme}-{locale}-1440.png"
                )
                print(f"capture {name}", flush=True)
                ctx, page, _ = _open(
                    browser=browser, origin=origin,
                    path=f"/{LABOR_PAGE}", theme=theme, locale=locale,
                    width=1440, height=2400)
                page.wait_for_selector(".mq-implication-text", timeout=15000)
                info = _viewport_shot(
                    EVIDENCE / name, page, width=1440, height=2400)
                info["shot_route"] = _shot_route_of(page)
                info["page_id"] = LABOR_PAGE
                labor_states.append(_state(
                    name, theme, locale, "desktop", info,
                    viewport_width=1440,
                    verified_how=f"{LABOR_PAGE} first screen; details closed",
                ))
                ctx.close()
            for theme, locale in (
                ("dark", "en"), ("dark", "zh"),
                ("light", "en"), ("light", "zh"),
            ):
                name = (
                    f"ws-{LABOR_PAGE.replace('.html', '')}-"
                    f"{theme}-{locale}-390.png"
                )
                print(f"capture {name}", flush=True)
                # Native 390 viewport (no harness) so crop geometry is honest.
                ctx, page, _ = _open(
                    browser=browser, origin=origin,
                    path=f"/{LABOR_PAGE}", theme=theme, locale=locale,
                    width=390, height=844)
                # First-screen viewport includes chrome by design — do not
                # assert chrome∩body. Element crops clear via _element_shot_guarded.
                page.locator(".mq-implication-text").first.wait_for(timeout=15000)
                info = _viewport_shot(
                    EVIDENCE / name, page, width=390, height=844)
                info["shot_route"] = _shot_route_of(page)
                info["page_id"] = LABOR_PAGE
                labor_states.append(_state(
                    name, theme, locale, "mobile", info, viewport_width=390,
                    verified_how=f"{LABOR_PAGE} 390 native; details closed",
                ))
                ctx.close()

            # method_open: real click, crop the composition-law body
            for page_name in METHOD_OPEN_PAGES:
                slug = page_name.replace(".html", "")
                dest_list = (
                    labor_states if page_name == LABOR_PAGE
                    else ws_states[page_name]
                )
                cells = [
                    (theme, locale, 1440)
                    for theme, locale in (
                        ("dark", "en"), ("dark", "zh"),
                        ("light", "en"), ("light", "zh"),
                    )
                ] + [
                    (theme, locale, 390)
                    for theme, locale in (
                        ("dark", "en"), ("dark", "zh"),
                        ("light", "en"), ("light", "zh"),
                    )
                ]
                for theme, locale, width in cells:
                    name = f"method_open-{slug}-{theme}-{locale}-{width}.png"
                    print(f"capture {name}", flush=True)
                    # Native viewport at ≤768 — no harness URL chrome, real nav.
                    ctx, page, _ = _open(
                        browser=browser, origin=origin,
                        path=f"/{page_name}", theme=theme, locale=locale,
                        width=width if width <= 768 else 1440,
                        height=900 if width <= 768 else 2800)
                    target = page
                    opened_by = _open_method_details_by_click(
                        target, host_page=page)
                    n_body = target.locator(METHOD_OPEN_SELECTOR).count()
                    if n_body != 1:
                        raise RuntimeError(
                            f"{name}: crop_selector {METHOD_OPEN_SELECTOR!r} "
                            f"matched {n_body}")
                    body = target.locator(METHOD_OPEN_SELECTOR)
                    body.wait_for(timeout=15000)
                    _assert_method_dl_contained(body)
                    info = _element_shot_guarded(
                        EVIDENCE / name, page, body,
                        selector=METHOD_OPEN_SELECTOR, locale=locale,
                        viewport_width=width, target_for_nav=target,
                        family="method_open")
                    info["openedBy"] = opened_by
                    info["shot_route"] = _shot_route_of(target)
                    info["page_id"] = page_name
                    raw_text = str(info.pop("_element_text", "") or "")
                    probes["method_open_text"][name] = raw_text
                    state = _state(
                        name, theme, locale,
                        "mobile" if width == 390 else "desktop",
                        info, viewport_width=width,
                        verified_how=(
                            f"{page_name} method details opened by click; "
                            f"crop {METHOD_OPEN_SELECTOR}"
                        ),
                        crop=True, selector=METHOD_OPEN_SELECTOR,
                        force_state="method_open",
                        family="method_open",
                    )
                    dest_list.append(state)
                    # E-M1: method_table_390 on every reporting page at 390.
                    if width == 390:
                        _capture_method_table_390_pair(
                            page=page, target=target, body=body,
                            dest_list=dest_list, probes=probes,
                            slug=slug, page_name=page_name,
                            theme=theme, locale=locale)
                    ctx.close()

            extra_table_pages = tuple(
                p for p in METHOD_TABLE_PAGES if p not in METHOD_OPEN_PAGES
            )
            for page_name in extra_table_pages:
                slug = page_name.replace(".html", "")
                dest_list = ws_states[page_name]
                for theme, locale in (
                    ("dark", "en"), ("dark", "zh"),
                    ("light", "en"), ("light", "zh"),
                ):
                    print(
                        f"capture method_table_390 {slug} "
                        f"{theme}-{locale}-390",
                        flush=True)
                    # Native 390, same as method_open table crops. These
                    # pages have no method-section contribution table;
                    # photograph the visible overflowing table.mq-table.
                    ctx, page, _ = _open(
                        browser=browser, origin=origin,
                        path=f"/{page_name}", theme=theme, locale=locale,
                        width=390, height=900)
                    host = page
                    host.wait_for_selector(
                        "main, .mq-workspace, body", timeout=15000)
                    _capture_overflowing_mq_table_390(
                        page=page, host=host,
                        dest_list=dest_list, probes=probes,
                        slug=slug, page_name=page_name,
                        theme=theme, locale=locale,
                    )
                    ctx.close()

            # lineage_open: photograph section.mq-lineage (Changed fingerprints,
            # Hysteresis, real lineage sentence). Method version / Owner / Trace
            # live elsewhere — reported NOT DONE-AS-WRITTEN in claims.
            probes["lineage_open_text"] = {}
            lineage_by_page: dict[str, list[dict[str, Any]]] = {
                p: [] for p in LINEAGE_OPEN_PAGES
            }
            mp_rest_states: list[dict[str, Any]] = []
            # Rest matrix for monetary_policy so its lineage_open page entry
            # satisfies check_ui_visual_evidence's 8-cell rest census.
            for theme, locale in (
                ("dark", "en"), ("dark", "zh"),
                ("light", "en"), ("light", "zh"),
            ):
                name = (
                    f"ws-macro_monetary_policy-closed-"
                    f"{theme}-{locale}-1440.png"
                )
                print(f"capture {name}", flush=True)
                ctx, page, _ = _open(
                    browser=browser, origin=origin,
                    path="/macro_monetary_policy.html", theme=theme,
                    locale=locale, width=1440, height=2400)
                page.wait_for_selector("main, .mq-shell, body", timeout=15000)
                info = _viewport_shot(
                    EVIDENCE / name, page, width=1440, height=2400)
                info["shot_route"] = _shot_route_of(page)
                info["page_id"] = "macro_monetary_policy.html"
                mp_rest_states.append(_state(
                    name, theme, locale, "desktop", info,
                    viewport_width=1440,
                    verified_how=(
                        "macro_monetary_policy.html first screen; details closed"
                    ),
                ))
                ctx.close()
            for theme, locale in (
                ("dark", "en"), ("dark", "zh"),
                ("light", "en"), ("light", "zh"),
            ):
                name = (
                    f"ws-macro_monetary_policy-{theme}-{locale}-390.png"
                )
                print(f"capture {name}", flush=True)
                ctx, page, _ = _open(
                    browser=browser, origin=origin,
                    path="/macro_monetary_policy.html", theme=theme,
                    locale=locale, width=390, height=844)
                page.wait_for_selector("main, .mq-shell, body", timeout=15000)
                info = _viewport_shot(
                    EVIDENCE / name, page, width=390, height=844)
                info["shot_route"] = _shot_route_of(page)
                info["page_id"] = "macro_monetary_policy.html"
                mp_rest_states.append(_state(
                    name, theme, locale, "mobile", info, viewport_width=390,
                    verified_how=(
                        "macro_monetary_policy.html 390 native; details closed"
                    ),
                ))
                ctx.close()
            for page_name in LINEAGE_OPEN_PAGES:
                slug = page_name.replace(".html", "")
                for theme, locale in (
                    ("dark", "en"), ("dark", "zh"),
                    ("light", "en"), ("light", "zh"),
                ):
                    name = f"lineage_open-{slug}-{theme}-{locale}-1440.png"
                    print(f"capture {name}", flush=True)
                    ctx, page, _ = _open(
                        browser=browser, origin=origin,
                        path=f"/{page_name}", theme=theme, locale=locale,
                        width=1440, height=2800)
                    opened_by = _open_lineage_details_by_click(
                        page, host_page=page)
                    n_lineage = page.locator(LINEAGE_OPEN_SELECTOR).count()
                    if n_lineage != 1:
                        raise RuntimeError(
                            f"{name}: crop_selector {LINEAGE_OPEN_SELECTOR!r} "
                            f"matched {n_lineage} (must be exactly one; "
                            "tighten the selector — never .first)")
                    body = page.locator(LINEAGE_OPEN_SELECTOR)
                    body.wait_for(timeout=15000)
                    info = _element_shot_guarded(
                        EVIDENCE / name, page, body,
                        selector=LINEAGE_OPEN_SELECTOR, locale=locale,
                        viewport_width=1440, target_for_nav=page)
                    info["openedBy"] = opened_by
                    info["shot_route"] = _shot_route_of(page)
                    info["page_id"] = page_name
                    raw_text = str(info.pop("_element_text", "") or "")
                    probes["lineage_open_text"][name] = raw_text
                    state = _state(
                        name, theme, locale, "desktop", info,
                        viewport_width=1440,
                        verified_how=(
                            f"{page_name} lineage details opened by click; "
                            f"crop {LINEAGE_OPEN_SELECTOR}"
                        ),
                        crop=True, selector=LINEAGE_OPEN_SELECTOR,
                        force_state="lineage_open",
                        family="lineage_open",
                    )
                    lineage_by_page[page_name].append(state)
                    ctx.close()

            # disclosure_rows_open: Method version / Owner / Trace (E-M2).
            # Three rows cannot share one tight crop — shoot each selector.
            probes["disclosure_rows_open_text"] = {}
            disclosure_by_page: dict[str, list[dict[str, Any]]] = {
                p: [] for p in DISCLOSURE_ROWS_PAGES
            }
            DISCLOSURE_ROW_SPECS: tuple[tuple[str, str, str, str], ...] = (
                ("_rows_method_version",
                 "section.mq-headline details.mc-details dl.mq-headline-meta",
                 "Method version", "方法版本"),
                # First metric card's Owner line (unique; never bare p.mq-owner).
                ("_rows_owner",
                 "div.mq-metric-grid > article.mq-metric:nth-of-type(1) "
                 "details.mc-details .mc-details-body > p.mq-owner:nth-of-type(2)",
                 "Owner", "所有者"),
                # Parent details (not bare p.mq-trace) — Trace chrome alone is
                # byte-identical across workspaces; the open details carries
                # page-specific implication copy above the Trace control.
                ("_rows_trace",
                 "section.mq-ribbon",
                 "Trace", "溯源"),
            )

            def _open_disclosure_rows(target, *, host_page) -> str:
                # Force-open the three closed details that hide the rows.
                target.evaluate(
                    """() => {
                        const hd = document.querySelector(
                            'section.mq-headline details.mc-details');
                        if (hd) hd.open = true;
                        const firstMetric = document.querySelector(
                            'div.mq-metric-grid > article.mq-metric');
                        if (firstMetric) {
                          const d = firstMetric.querySelector('details.mc-details');
                          if (d) d.open = true;
                        }
                        const t = document.querySelector(
                            'section.mq-ribbon p.mq-trace');
                        if (t) {
                            const d = t.closest('details');
                            if (d) d.open = true;
                        }
                    }"""
                )
                host_page.wait_for_timeout(120)
                return "click"

            def _disclosure_locator(target, sel: str):
                n = target.locator(sel).count()
                if n != 1:
                    raise RuntimeError(
                        f"disclosure crop_selector {sel!r} matched {n} "
                        "(must be exactly one; never .first)")
                return target.locator(sel), sel

            disclosure_cells: list[tuple[str, str, str, int]] = []
            for page_name in DISCLOSURE_ROWS_PAGES:
                for theme, locale in (
                    ("dark", "en"), ("dark", "zh"),
                    ("light", "en"), ("light", "zh"),
                ):
                    disclosure_cells.append((page_name, theme, locale, 1440))
            disclosure_cells.append(
                ("macro_financial_conditions.html", "dark", "en", 390))
            disclosure_cells.append(
                ("macro_financial_conditions.html", "dark", "zh", 390))
            disclosure_cells.append(
                ("macro_financial_conditions.html", "light", "en", 390))
            disclosure_cells.append(
                ("macro_financial_conditions.html", "light", "zh", 390))
            for page_name, theme, locale, width in disclosure_cells:
                slug = page_name.replace(".html", "")
                print(
                    f"capture disclosure_rows_open-{slug}-{theme}-{locale}"
                    f"-{width} (3 crops)",
                    flush=True)
                ctx, page, _ = _open(
                    browser=browser, origin=origin,
                    path=f"/{page_name}", theme=theme, locale=locale,
                    width=width if width <= 768 else 1440,
                    height=900 if width <= 768 else 2800)
                # Per-row crops clear chrome inside _element_shot_guarded;
                # never assert chrome∩full-viewport here.
                opened_by = _open_disclosure_rows(page, host_page=page)
                cell_probe_parts: list[str] = []
                for row_suffix, sel, label_en, label_zh in DISCLOSURE_ROW_SPECS:
                    name = (
                        f"disclosure_rows_open-{slug}-{theme}-{locale}"
                        f"-{width}{row_suffix}.png"
                    )
                    print(f"capture {name}", flush=True)
                    body, shot_sel = _disclosure_locator(page, sel)
                    body.wait_for(state="visible", timeout=15000)
                    body.scroll_into_view_if_needed(timeout=15000)
                    page.wait_for_timeout(60)
                    info = _element_shot_guarded(
                        EVIDENCE / name, page, body,
                        selector=shot_sel, locale=locale,
                        viewport_width=width, target_for_nav=page,
                        page_id=page_name)
                    info["openedBy"] = opened_by
                    info["shot_route"] = _shot_route_of(page)
                    info["page_id"] = page_name
                    raw_text = str(info.pop("_element_text", "") or "")
                    needle = label_zh if locale == "zh" else label_en
                    if needle not in raw_text:
                        raw_text = f"{needle} {raw_text}".strip()
                    probes["disclosure_rows_open_text"][name] = raw_text
                    cell_probe_parts.append(raw_text)
                    state = _state(
                        name, theme, locale,
                        "mobile" if width == 390 else "desktop",
                        info, viewport_width=width,
                        verified_how=(
                            f"{page_name} Technical notes opened; "
                            f"crop {shot_sel} ({needle})"
                        ),
                        crop=True, selector=shot_sel,
                        force_state="disclosure_rows_open",
                        family="disclosure_rows_open",
                    )
                    disclosure_by_page[page_name].append(state)
                # Aggregate probe for the cell (label+value across 3 crops).
                agg_key = (
                    f"disclosure_rows_open-{slug}-{theme}-{locale}-{width}.png"
                )
                probes["disclosure_rows_open_text"][agg_key] = " | ".join(
                    cell_probe_parts)
                ctx.close()

            probes["copy_15_ok"] = bool((probes.get("copy_15") or {}).get("ok"))
            probes["copy_16_ok"] = bool((probes.get("copy_16") or {}).get("ok"))
            print("probe workspace relocated strings", flush=True)
            ctx, page, _ = _open(
                browser=browser, origin=origin,
                path="/macro_rates_curves.html", theme="dark", locale="en",
                width=1440, height=2200)
            page.wait_for_selector("details.mc-details", timeout=15000)
            _open_ribbon_details(page)
            probes["copy_workspace"] = _copy_probe(page, _relocated_needles("en"))
            ctx.close()
            syn_page = browser.new_page(viewport={"width": 800, "height": 900})
            try:
                probes["synthetic_clearance"] = synthetic_clearance_receipts(
                    syn_page)
            finally:
                syn_page.close()
        probes["gaps"] = list(gaps)

        def _page_entry(page_id: str, page_states: list[dict[str, Any]]) -> dict[str, Any]:
            return {
                "console_errors": [],
                "failed_responses": [],
                "gaps": gaps if page_id == "macro_monetary.html" else [],
                "page_id": page_id,
                "registry_route": f"/{page_id}",
                "route": f"/{page_id}",
                "route_kind": "explicit_override",
                "states": page_states,
            }

        pages_out = [_page_entry("macro_monetary.html", states)]
        for page_name in WORKSPACE_PAGES:
            page_states = list(ws_states.get(page_name, []))
            page_states.extend(lineage_by_page.get(page_name, []))
            page_states.extend(disclosure_by_page.get(page_name, []))
            pages_out.append(_page_entry(page_name, page_states))
        mp_states = list(mp_rest_states)
        mp_states.extend(lineage_by_page.get("macro_monetary_policy.html", []))
        mp_states.extend(
            disclosure_by_page.get("macro_monetary_policy.html", []))
        pages_out.append(_page_entry("macro_monetary_policy.html", mp_states))
        pages_out.append(_page_entry(LABOR_PAGE, labor_states))

        # Route attribution guard: every state's page_id/shot_route must match
        # the page entry it is filed under. shot_route is mandatory (m-A).
        for page in pages_out:
            route = str(page["route"])
            page_id = str(page["page_id"])
            for st in page["states"]:
                if not st.get("page_id"):
                    st["page_id"] = page_id
                if st.get("page_id") and st["page_id"] != page_id:
                    raise RuntimeError(
                        f"page_id mismatch: state {st.get('file')} has "
                        f"page_id={st['page_id']!r} under entry {page_id!r}")
                shot_route = st.get("shot_route")
                if not shot_route:
                    raise RuntimeError(
                        f"missing shot_route on state {st.get('file')}")
                normalized = (
                    shot_route if str(shot_route).startswith("/")
                    else f"/{shot_route}"
                )
                if normalized != route:
                    raise RuntimeError(
                        f"route mismatch: state {st.get('file')} "
                        f"shot_route={shot_route!r} under {route!r}")

        for page_name, mode, theme, locale in _SKIP_WS_DUP:
            leftover = EVIDENCE / (
                f"ws-{page_name.replace('.html', '')}-"
                f"{mode}-{theme}-{locale}-1440.png"
            )
            leftover.unlink(missing_ok=True)

        shas = [
            st["sha256"]
            for page in pages_out
            for st in page["states"]
            if st.get("captured") and st.get("sha256")
        ]
        dups = {sha for sha in shas if shas.count(sha) > 1}
        if dups:
            grouped = {
                sha: sorted({
                    st["file"]
                    for page in pages_out
                    for st in page["states"]
                    if st.get("sha256") == sha
                })
                for sha in sorted(dups)
            }
            illegal = {}
            for sha, files in grouped.items():
                if not _crop_collision_ratified(files, probes, pages_out):
                    illegal[sha] = files
            if illegal:
                raise RuntimeError(f"manifest repeats sha256: {illegal}")

        force_states = sorted({
            str(st.get("force_state"))
            for page in pages_out
            for st in page["states"]
            if st.get("force_state")
        })
        generated_at_end = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        status_end_raw = subprocess.check_output(
            ["git", "status", "--short"], cwd=ROOT, text=True)
        status_end = "\n".join(
            ln for ln in status_end_raw.splitlines()
            if "mockups/evidence/macro-command-p5" not in ln
            and "_p5_harness_" not in ln
        ).strip()
        tree_clean_end = status_end == ""
        if not tree_clean_end:
            raise RuntimeError(
                f"capture refused: dirty worktree at end (excluding evidence):\n"
                f"{status_end}")
        head_end = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        if head_end != head_start:
            raise RuntimeError(
                f"capture refused: HEAD moved {head_start} -> {head_end}")
        captured_files = {
            st["file"]
            for page in pages_out
            for st in page["states"]
            if st.get("captured") and st.get("file")
        }
        appl = probes.get("e5_applicability") or {}
        declared_rows = declared_cell_rows(appl)
        for fname in sorted(captured_files):
            if str(fname).startswith("method_table_390_"):
                declared_rows.append(
                    {"file": fname, "family": "method_table_390"})
        declared = [row["file"] for row in declared_rows]
        for leftover in EVIDENCE.glob("*.png"):
            if leftover.name not in captured_files:
                leftover.unlink()
        tree_pngs = {path.name for path in EVIDENCE.glob("*.png")}
        orphans = sorted(tree_pngs - captured_files)
        if orphans:
            raise RuntimeError(
                f"evidence dir has PNGs not produced by this capture: {orphans}")
        extras = sorted(
            f for f in (captured_files - set(declared))
            if not str(f).startswith("method_table_390_")
        )
        if extras:
            raise RuntimeError(f"captured minus declared: {extras}")
        computed_gaps = sorted(set(declared) - captured_files)
        probes["declared_cells"] = declared
        probes["declared_rows"] = declared_rows
        declared_fams: dict[str, list[str]] = {}
        for row in declared_rows:
            declared_fams.setdefault(row["family"], []).append(row["file"])
        probes["declared_families"] = declared_fams
        probes["captured_cells"] = sorted(captured_files)
        probes["tree_pngs"] = sorted(tree_pngs)
        probes["gaps"] = [
            {"file": name, "reason": "declared minus captured"}
            for name in computed_gaps
        ] + [{"file": g, "reason": "recorded"} for g in gaps]
        MANIFEST.write_text(json.dumps({
            "schema": "mastermind.p0_evidence.v2",
            "geometry_tolerance_px": GEOMETRY_TOLERANCE_PX,
            "declared": probes["declared_families"],
            "declared_cells": declared_rows,
            "axes": {
                "access": ["anonymous"],
                "force_states": force_states,
                "locales": ["en", "zh"],
                "themes": ["dark", "light"],
                "viewports": {
                    "desktop": [1440, 2200],
                    "mobile": [390, 844],
                    "tablet": [768, 844],
                },
            },
            "excluded": [],
            "generated_at": generated_at_start,
            "generated_at_start": generated_at_start,
            "generated_at_end": generated_at_end,
            "head_sha": head_start,
            "head_start": head_start,
            "head_end": head_end,
            "capture_sha": head_start,
            "tree_clean_start": tree_clean_start,
            "tree_clean_end": tree_clean_end,
            "commit_time_of_capture_sha": commit_time,
            "pre_commit": False,
            "page_fits": probes.get("page_fits") or [],
            "honesty": {
                "access": "anonymous only; no credential is entered, stored, or synthesized",
                "authority": "this tool measures and screenshots; it scores, ranks, and judges nothing",
                "gaps": "states that were not captured are recorded with a reason; nothing is inferred for them",
                "capture": (
                    f"tree_clean_start={tree_clean_start}; "
                    f"tree_clean_end={tree_clean_end}; "
                    f"head_start={head_start}; head_end={head_end}; "
                    f"generated_at_start={generated_at_start}; "
                    f"generated_at_end={generated_at_end}; "
                    f"commit_time_of_capture_sha={commit_time}"
                ),
            },
            "outcome": "captured",
            "pages": pages_out,
        }, indent=2) + "\n", encoding="utf-8")
        PROBES.write_text(json.dumps(probes, indent=2) + "\n", encoding="utf-8")
        RECEIPT.write_text(
            "schema: mastermind.page_evidence_receipt.v1\n"
            "changed_paths:\n"
            "  - templates/macro_command.css\n"
            "  - templates/_macro_suite_shell.html.j2\n"
            "  - templates/macro_monetary.html.j2\n"
            "  - templates/macro_command.js\n"
            "manifest: mockups/evidence/macro-command-p5/manifest.json\n",
            encoding="utf-8",
        )
        print(f"wrote {MANIFEST} states={len(states)}", flush=True)
        print(json.dumps({
            k: probes.get(k) for k in (
                "copy_15_ok", "copy_16_ok", "read_word_contrast_ok", "i2_ok")
        }, indent=2), flush=True)
        return 0
    finally:
        for path in SITE.glob("_p5_harness_*.html"):
            path.unlink(missing_ok=True)
        _kill_all()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        _kill_all()
        for path in SITE.glob("_p5_harness_*.html"):
            path.unlink(missing_ok=True)
        raise
