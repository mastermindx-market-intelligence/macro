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
    CaptureGeometryError,
    _assert_crop_geometry,
    _boxes_intersect,
    _filter_locale_nodes,
    _judge_occlusion,
    grid_sample_points,
    y_coverage,
)

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
METHOD_OPEN_SELECTOR = "section.mq-method .mq-axis-method"
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
    context.add_init_script(
        f"localStorage.setItem('theme', {theme!r});"
        "localStorage.removeItem('themeAuto');"
        f"localStorage.setItem('lang', {locale!r});"
        f"document.documentElement.setAttribute('data-theme', {theme!r});"
        f"document.documentElement.setAttribute('data-lang', {locale!r});"
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


def _shot_chipmat_clip(dest: Path, page, clip: Mapping[str, Any], *,
                       selector: str, locale: str, text_head: str,
                       frame_inner_width: int | None = None,
                       host_offset: Mapping[str, float] | None = None,
                       crop_dom_sha256: str | None = None,
                       host_for_occlusion=None,
                       ) -> dict[str, Any]:
    """Viewport clip of the visible chip(+pill) — never scrollIntoView."""
    extra: dict[str, Any] = {
        "dpr": _measure_dpr(page),
        "crop": True,
        "full_page": False,
        "crop_selector": selector,
        "fixture": "builder-payload",
        "locale": locale,
    }
    vw = float((page.viewport_size or {}).get("width") or 1440)
    vh = float((page.viewport_size or {}).get("height") or 900)
    raw_box = {
        "x": float(clip["x"]), "y": float(clip["y"]),
        "width": float(clip["width"]), "height": float(clip["height"]),
    }
    extra["raw_box"] = raw_box
    host_scroll_y = _read_scroll(page)
    doc_h = float(page.evaluate(
        "() => document.documentElement.scrollHeight") or (vh + host_scroll_y))
    _assert_crop_geometry(
        raw_box, viewport_width=vw, doc_height=doc_h,
        name=dest.name, crop_box_doc={
            "x": raw_box["x"],
            "y": raw_box["y"] + host_scroll_y,
            "width": raw_box["width"],
            "height": raw_box["height"],
        }, state=dest.name, locale=locale)
    raw_x = max(0.0, float(clip["x"]))
    raw_y = max(0.0, float(clip["y"]))
    raw_w = max(1.0, min(float(clip["width"]), vw - raw_x))
    raw_h = max(1.0, min(float(clip["height"]), vh - raw_y))
    x = float(math.floor(raw_x))
    y = float(math.floor(raw_y))
    x1 = min(vw, float(math.ceil(raw_x + raw_w)))
    y1 = min(vh, float(math.ceil(raw_y + raw_h)))
    page_clip = {
        "x": x,
        "y": y,
        "width": max(1.0, x1 - x),
        "height": max(1.0, y1 - y),
    }
    page.screenshot(path=str(dest), type="png", clip=page_clip)
    extra["coordSpace"] = "host-page"
    extra["hostFrameOffset"] = {
        "x": float((host_offset or {}).get("x") or 0.0),
        "y": float((host_offset or {}).get("y") or 0.0),
    }
    extra["host_scroll_y_at_shot"] = host_scroll_y
    extra["crop_box"] = page_clip
    extra["crop_box_doc"] = {
        "x": page_clip["x"],
        "y": page_clip["y"] + host_scroll_y,
        "width": page_clip["width"],
        "height": page_clip["height"],
    }
    extra["crop_width"] = page_clip["width"]
    extra["scroll_y_at_shot"] = host_scroll_y
    # Independent clone-strip vs live-walker receipts (C-M2) — never alias.
    loc = page.locator(selector).first
    if loc.count():
        visible = _locale_visible_text(loc, locale)
        independent = _element_text_independent(loc, locale)
    else:
        visible = text_head
        independent = text_head
    extra["visible_text_head"] = visible.replace("\n", " ").strip()[:80]
    extra["visible_text_sha256"] = hashlib.sha256(
        visible.encode("utf-8")).hexdigest()
    extra["element_text_head"] = independent.replace("\n", " ").strip()[:80]
    extra["element_text_sha256"] = hashlib.sha256(
        independent.encode("utf-8")).hexdigest()
    if crop_dom_sha256:
        extra["cropDomSha256"] = crop_dom_sha256
    extra["device_px_span"] = _device_px_span(page_clip, extra["dpr"])
    # Snap crop_box to PNG device span so schema recompute matches.
    pw_pre, ph_pre = _png_size(dest)
    dpr_f = float(extra["dpr"]) if float(extra["dpr"]) > 0 else 1.0
    span0 = extra["device_px_span"]
    x0 = int(span0["x0"]); y0 = int(span0["y0"])
    extra["device_px_span"] = {
        "x0": x0, "y0": y0,
        "x1": x0 + int(pw_pre), "y1": y0 + int(ph_pre),
    }
    extra["crop_box"] = {
        "x": float(x0) / dpr_f,
        "y": float(y0) / dpr_f,
        "width": float(pw_pre) / dpr_f,
        "height": float(ph_pre) / dpr_f,
    }
    extra["crop_box_doc"] = {
        "x": float(extra["crop_box"]["x"]),
        "y": float(extra["crop_box"]["y"]) + host_scroll_y,
        "width": float(extra["crop_box"]["width"]),
        "height": float(extra["crop_box"]["height"]),
    }
    extra["crop_width"] = extra["crop_box"]["width"]
    extra["scroll_y_at_shot"] = host_scroll_y
    extra["innerWidth"] = (
        int(frame_inner_width) if frame_inner_width is not None
        else int(round(vw)))
    extra["innerHeight"] = int(round(vh))
    extra["frameInnerWidth"] = extra["innerWidth"]
    extra["shot_route"] = _shot_route_of(page)
    # Occlusion: sample the rail's own box (chip+pill live there). The full
    # nav.mq-suitenav box extends into #mq-shell and false-fails the grid.
    if host_for_occlusion is not None:
        root = host_for_occlusion.locator(
            ".mq-suitenav-rail, nav.mq-suitenav .mq-suitenav-rail, "
            + selector
        ).first
        if not root.count():
            root = host_for_occlusion.locator("nav.mq-suitenav").first
        if not root.count():
            raise RuntimeError(f"{dest.name}: no suite-nav root for occlusion")
        # Measure + sample entirely inside the host document (iframe-local
        # when harnessed). Never mix Playwright host-frame bounding_box with
        # iframe elementFromPoint — that shifted y_coverage by the iframe top.
        packed = root.evaluate(
            """(el) => {
                const doc = el.ownerDocument || document;
                const win = doc.defaultView || window;
                const nav = doc.querySelector('nav.mq-suitenav') || el;
                const r = el.getBoundingClientRect();
                const inset = 4;
                const box = {
                  x: r.left, y: r.top, width: r.width, height: r.height,
                };
                const x0 = r.left + inset, x1 = r.right - inset;
                const y0 = r.top + inset, y1 = r.bottom - inset;
                const yFracs = [0, 0.25, 0.5, 0.75, 1];
                const xFracs = [0, 0.5, 1];
                const pts = [];
                for (const fy of yFracs) {
                  for (const fx of xFracs) {
                    const x = x0 + (x1 - x0) * fx;
                    const y = y0 + (y1 - y0) * fy;
                    if (x < 1 || y < 1 || x > win.innerWidth - 1
                        || y > win.innerHeight - 1) {
                      pts.push({x, y, ok: false, hitSelector: 'off-viewport'});
                      continue;
                    }
                    const hit = doc.elementFromPoint(x, y);
                    let ok = false;
                    let cur = hit;
                    while (cur) {
                      if (cur === el || cur === nav
                          || (el.contains && el.contains(cur))
                          || (nav.contains && nav.contains(cur))) {
                        ok = true; break;
                      }
                      cur = cur.parentElement;
                    }
                    pts.push({
                      x, y, ok,
                      hitSelector: hit
                        ? (hit.id ? '#' + hit.id : hit.tagName.toLowerCase())
                        : null,
                    });
                  }
                }
                return {box, samples: pts};
            }"""
        )
        samples = _judge_occlusion(packed.get("samples") or [])
        sample_box = {
            "x": float((packed.get("box") or {}).get("x") or 0.0),
            "y": float((packed.get("box") or {}).get("y") or 0.0),
            "width": float((packed.get("box") or {}).get("width") or 0.0),
            "height": float((packed.get("box") or {}).get("height") or 1.0),
        }
        extra["occlusionSamples"] = samples
        extra["samples_span"] = "crop"
        extra["occlusion_sample_box"] = sample_box
        extra["y_coverage"] = y_coverage(samples, sample_box)
        extra["receipt_document"] = (
            "iframe" if host_offset and (
                float(host_offset.get("x") or 0) != 0
                or float(host_offset.get("y") or 0) != 0)
            else "host"
        )
    _assert_shot_geometry(dest, extra, int(round(vw)), int(round(vh)))
    png = dest.read_bytes()
    if png[:8] != b"\x89PNG\r\n\x1a\n" or b"IEND" not in png:
        raise RuntimeError(f"{dest.name} is not a finished PNG")
    pw, ph = _png_size(dest)
    return {
        **extra,
        "bytes": len(png),
        "sha256": hashlib.sha256(png).hexdigest(),
        "width": pw,
        "height": ph,
    }


def _shot(dest: Path, page, locator, *, selector: str,
          locale: str = "en") -> dict[str, Any]:
    """Element shot with raw_box geometry, occlusion, locale text, cropDomSha256.

    When ``selector`` is ``#mc-p5-frame`` (harness iframe), every text /
    cropDom / occlusion receipt is measured INSIDE the iframe document
    (E-M2) — never on the empty host-document iframe node.
    """
    extra: dict[str, Any] = {
        "dpr": _measure_dpr(page),
        "crop": True,
        "full_page": False,
        "crop_selector": selector,
        "fixture": "builder-payload",
        "locale": locale,
    }
    iframe_hosted = selector == "#mc-p5-frame"
    receipt = locator
    if iframe_hosted:
        frame = page.frame_locator("#mc-p5-frame")
        receipt = frame.locator("body").first
        receipt.wait_for(state="attached", timeout=15000)
    locator.scroll_into_view_if_needed(timeout=15000)
    box = _crop_box(locator)  # host-page box of the iframe (or element)
    win = _measure_window(page)
    vw = float(win["innerWidth"])
    doc_h = float(win["scrollHeight"])
    scroll_y = float(win["scrollY"])
    raw_box = {
        "x": float(box["x"]), "y": float(box["y"]),
        "width": float(box["width"]), "height": float(box["height"]),
    }
    crop_box_doc = {
        "x": raw_box["x"], "y": raw_box["y"] + scroll_y,
        "width": raw_box["width"], "height": raw_box["height"],
    }
    scroll_rcpt = _scroll_container_receipt(receipt)
    extra.update(scroll_rcpt)
    assert_box = raw_box
    client_w = scroll_rcpt.get("clientWidth")
    if client_w is not None and float(raw_box["width"]) > float(client_w) + 0.5:
        assert_box = {
            **raw_box,
            "width": float(client_w),
        }
    _assert_crop_geometry(
        assert_box, viewport_width=vw, doc_height=doc_h, name=dest.name,
        crop_box_doc=crop_box_doc, state=dest.name, locale=locale)
    _scroll_clear_of_chrome(
        page, selector, assert_box,
        host_page=page, viewport_width=int(round(vw)))
    # Re-measure after chrome clear so raw_box matches occlusion samples.
    box = _crop_box(locator)
    win = _measure_window(page)
    scroll_y = float(win["scrollY"])
    raw_box = {
        "x": float(box["x"]), "y": float(box["y"]),
        "width": float(box["width"]), "height": float(box["height"]),
    }
    crop_box_doc = {
        "x": raw_box["x"], "y": raw_box["y"] + scroll_y,
        "width": raw_box["width"], "height": raw_box["height"],
    }
    assert_box = raw_box
    if client_w is not None and float(raw_box["width"]) > float(client_w) + 0.5:
        assert_box = {**raw_box, "width": float(client_w)}
    _write_element_shot(page, dest, locator, extra, locale)
    visible = _locale_visible_text(receipt, locale)
    independent = _element_text_independent(receipt, locale)
    extra["visible_text_head"] = visible.replace("\n", " ").strip()[:80]
    extra["visible_text_sha256"] = hashlib.sha256(
        visible.encode("utf-8")).hexdigest()
    extra["element_text_head"] = independent.replace("\n", " ").strip()[:80]
    extra["element_text_sha256"] = hashlib.sha256(
        independent.encode("utf-8")).hexdigest()
    if not extra["visible_text_head"]:
        raise RuntimeError(
            f"{dest.name}: empty visible_text_head for selector={selector}")
    extra["cropDomSha256"] = _crop_dom_sha256(receipt, locale)
    extra["raw_box"] = raw_box
    if iframe_hosted:
        # Occlusion inside the iframe document; sample points are frame-local.
        samples, meta = _occlusion_samples_in_iframe(page, receipt, raw_box)
        extra["occlusionSamples"] = samples
        extra["samples_span"] = meta["samples_span"]
        extra["y_coverage"] = meta["y_coverage"]
        extra["occlusion_sample_box"] = meta.get("occlusion_sample_box")
        extra["receipt_document"] = "iframe"
    else:
        _attach_occlusion(extra, receipt)
        extra["receipt_document"] = "host"
    extra["shot_route"] = _shot_route_of(page)
    extra["_element_text"] = visible
    extra.setdefault("crop_box", dict(assert_box))
    extra.setdefault("crop_box_doc", crop_box_doc)
    extra.setdefault("scroll_y_at_shot", scroll_y)
    win2 = locator.evaluate(
        """el => {
            const doc = (el && el.contentDocument) || el.ownerDocument || document;
            const win = (el && el.contentWindow) || doc.defaultView || window;
            return {
                innerWidth: win.innerWidth,
                innerHeight: win.innerHeight,
                scrollY: win.scrollY || doc.documentElement.scrollTop || 0,
                scrollWidth: doc.documentElement.scrollWidth,
                scrollHeight: doc.documentElement.scrollHeight,
            };
        }"""
    )
    extra["innerWidth"] = win2["innerWidth"]
    extra["innerHeight"] = win2["innerHeight"]
    _assert_shot_geometry(
        dest, extra, int(round(float(win2["innerWidth"]))),
        int(round(float(win2["innerHeight"]))))
    png = dest.read_bytes()
    if png[:8] != b"\x89PNG\r\n\x1a\n" or b"IEND" not in png:
        raise RuntimeError(f"{dest.name} is not a finished PNG")
    pw, ph = _png_size(dest)
    return {
        **extra,
        "bytes": len(png),
        "sha256": hashlib.sha256(png).hexdigest(),
        "width": pw,
        "height": ph,
    }


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
        "samples_span": "crop∩viewport" if tall else "crop",
        "y_coverage": y_coverage(judged, sample_box),
        "occlusion_sample_box": sample_box,
        "host_box": dict(host_box),
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
                "frameInnerWidth", "analystBox", "siblingPillBox",
                "raw_box", "cropDomSha256",
                "scroll_container_selector", "scrollWidth", "clientWidth",
                "scrollLeft", "overflow_x",
                "inner_scrollports", "ancestor_scrollports",
                "y_coverage", "samples_span", "stitched",
                "receipt_document", "visible_text_at_scroll",
                "occlusion_sample_box"):
        if info.get(key) is not None:
            row[key] = info[key]
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
    dl = body.locator("dl").first
    dl.wait_for(timeout=8000)
    outer = _crop_box(body)
    inner = _crop_box(dl)
    if not _box_contains(outer, inner):
        raise RuntimeError(
            f"mq-axis-method crop does not contain its dl: {outer} vs {inner}")


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
        allow: Sequence[str] = _FIXED_ALLOW_SELECTORS) -> None:
    """RAISE if a fixed/sticky element outside allowlist intersects crop_box."""
    offenders = target.evaluate(
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
            const out = [];
            for (const el of document.querySelectorAll('body *')) {
                const st = getComputedStyle(el);
                if (st.position !== 'fixed' && st.position !== 'sticky') continue;
                if (hitAllow(el)) continue;
                const r = el.getBoundingClientRect();
                if (r.width < 2 || r.height < 2) continue;
                if (st.display === 'none' || st.visibility === 'hidden'
                    || Number(st.opacity) === 0) continue;
                const box = {x: r.left, y: r.top, width: r.width, height: r.height};
                const ax0 = box.x, ay0 = box.y, aw = box.width, ah = box.height;
                const bx0 = crop.x, by0 = crop.y, bw = crop.width, bh = crop.height;
                const intersect = !(ax0 + aw <= bx0 || bx0 + bw <= ax0
                    || ay0 + ah <= by0 || by0 + bh <= ay0);
                if (!intersect) continue;
                const sel = el.id ? ('#' + el.id)
                    : (el.className && typeof el.className === 'string'
                        ? (el.tagName.toLowerCase() + '.'
                           + el.className.trim().split(/\\s+/).slice(0, 3).join('.'))
                        : el.tagName.toLowerCase());
                out.push(sel);
                if (out.length >= 5) break;
            }
            return out;
        }""",
        {"crop": dict(crop_box), "allow": list(allow)},
    )
    if offenders:
        raise RuntimeError(
            f"fixed/sticky intersection with crop: {offenders}")


def _scroll_clear_of_chrome(
        target, crop_selector: str, crop_box: Mapping[str, Any], *,
        host_page, viewport_width: int) -> None:
    """Scroll the crop clear of sticky/fixed chrome; never hide page chrome.

    C-M3 / C-m2: ``crop_box`` is required. The frame is what the customer sees —
    do not set visibility:hidden on ``nav.mq-suitenav``. Mobile hamburger may
    still be closed (class strip + Escape) because a customer can close it.
    """
    if crop_box is None:
        raise TypeError("crop_box is required for _scroll_clear_of_chrome")
    if int(viewport_width) <= 768:
        target.evaluate(
            """() => {
                document.documentElement.classList.remove('nav-open');
                document.body.classList.remove('nav-open');
                document.querySelectorAll('.nav-open').forEach(el => {
                    el.classList.remove('nav-open');
                });
                document.querySelectorAll(
                    '.nav-dd.open, .nav-sub.open, .nav-drill.is-open'
                ).forEach(el => {
                    el.classList.remove('open');
                    el.classList.remove('is-open');
                });
                const toggle = document.querySelector(
                    '.nav-toggle, button.nav-toggle, [aria-controls=\"nav-links\"]');
                const nav = document.querySelector('.site-nav.has-nav-toggle');
                if (nav && nav.classList.contains('nav-open') && toggle) {
                    toggle.click();
                }
                nav && nav.classList.remove('nav-open');
            }"""
        )
        try:
            host_page.keyboard.press("Escape")
        except Exception:
            pass
        host_page.wait_for_timeout(120)
        target.evaluate(
            """() => {
                document.querySelectorAll('.nav-open').forEach(el => {
                    el.classList.remove('nav-open');
                });
            }"""
        )
        host_page.wait_for_timeout(80)
    # Scroll so the crop top sits below sticky/fixed chrome.
    host_page.evaluate(
        """(sel) => {
            const el = document.querySelector(sel);
            if (!el) return 0;
            let chrome = 0;
            for (const sticky of document.querySelectorAll(
                'nav.mq-suitenav, .site-nav, .topbar, header.site-nav')) {
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
        crop_selector,
    )
    host_page.wait_for_timeout(80)
    panel = _nav_panel_box(target)
    if panel and _boxes_intersect(panel, crop_box):
        raise RuntimeError(
            f"nav panel intersects crop after clear: panel={panel} "
            f"crop={dict(crop_box)}")
    _assert_no_fixed_intersection(target, crop_box)


# Back-compat name used by older call sites during the rename — always requires
# crop_box (C-m2). Prefer `_scroll_clear_of_chrome` at new sites.
def _close_nav_overlay(
        target, crop_selector: str, crop_box: Mapping[str, Any], *,
        host_page, viewport_width: int) -> None:
    _scroll_clear_of_chrome(
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


def _occlusion_samples(locator, *, cols: int = 3, rows: int = 5
                       ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """15-point inclusive grid over crop∩viewport; hits must be crop/descendant."""
    box = _crop_box(locator)
    win = locator.evaluate(
        """() => ({iw: window.innerWidth, ih: window.innerHeight})"""
    )
    iw = float(win["iw"])
    ih = float(win["ih"])
    inset = 4.0
    crop_top = float(box["y"])
    crop_bottom = float(box["y"]) + float(box["height"])
    crop_left = float(box["x"])
    crop_right = float(box["x"]) + float(box["width"])
    vis_top = max(crop_top, 0.0)
    vis_bottom = min(crop_bottom, ih)
    vis_left = max(crop_left, 0.0)
    vis_right = min(crop_right, iw)
    sample_box = {
        "x": vis_left,
        "y": vis_top,
        "width": max(0.0, vis_right - vis_left),
        "height": max(0.0, vis_bottom - vis_top),
    }
    if sample_box["width"] < 8 or sample_box["height"] < 8:
        raise RuntimeError(
            f"occlusion visible intersection too small: box={box} "
            f"sample={sample_box} vw={iw} vh={ih}")
    tall = float(box["height"]) > ih + 0.5
    samples_span = "crop∩viewport" if tall else "crop"
    pts = grid_sample_points(sample_box, cols=cols, rows=rows, inset=inset)
    samples = locator.evaluate(
        """(el, pts) => {
            const doc = el.ownerDocument || document;
            const win = doc.defaultView || window;
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
                    if (cur === el) { inside = true; break; }
                    cur = cur.parentElement;
                }
                if (!inside && hit && el.contains && hit.contains
                    && hit.contains(el)) {
                    inside = true;
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
                out.push({x, y, ok: inside, hitSelector});
            }
            return out;
        }""",
        pts,
    )
    judged = _judge_occlusion(samples, min_samples=cols * rows)
    meta = {
        "samples_span": samples_span,
        "y_coverage": y_coverage(judged, sample_box),
        "occlusion_sample_box": sample_box,
    }
    return judged, meta


def _attach_occlusion(extra: dict[str, Any], locator) -> None:
    samples, meta = _occlusion_samples(locator)
    extra["occlusionSamples"] = samples
    extra["samples_span"] = meta["samples_span"]
    extra["y_coverage"] = meta["y_coverage"]
    extra["occlusion_sample_box"] = meta.get("occlusion_sample_box")



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


def _chrome_bottom(page) -> float:
    return float(page.evaluate(
        """() => {
            let chrome = 0;
            for (const sticky of document.querySelectorAll(
                'nav.mq-suitenav, .site-nav, .topbar, header.site-nav')) {
                const st = getComputedStyle(sticky);
                if (st.position !== 'sticky' && st.position !== 'fixed') continue;
                if (st.display === 'none' || Number(st.opacity) === 0) continue;
                const sr = sticky.getBoundingClientRect();
                if (sr.height < 2 || sr.width < 2) continue;
                chrome = Math.max(chrome, sr.bottom);
            }
            return chrome;
        }"""
    ) or 0.0)


def _stitch_png_bytes(chunks: Sequence[bytes]) -> bytes:
    """Vertically concatenate PNG strips (Pillow)."""
    from io import BytesIO
    from PIL import Image
    images = [Image.open(BytesIO(b)).convert("RGBA") for b in chunks]
    width = max(im.width for im in images)
    height = sum(im.height for im in images)
    out = Image.new("RGBA", (width, height))
    y = 0
    for im in images:
        out.paste(im, (0, y))
        y += im.height
    buf = BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


def _element_shot_guarded(
        dest: Path, page, locator, *, selector: str, locale: str,
        viewport_width: int, target_for_nav=None,
        page_id: str = "") -> dict[str, Any]:
    """Element shot: chrome scrolled clear, RAW geometry, 15-pt occlusion.

    Tall crops (height > viewport − chrome) are captured as N viewport strips
    stitched vertically (C-M3); each strip carries its own occlusion grid and
    fixed-intersection assertion.
    """
    nav_target = target_for_nav or page
    locator.scroll_into_view_if_needed(timeout=15000)
    page.wait_for_timeout(80)
    box = _crop_box(locator)
    _scroll_clear_of_chrome(
        nav_target, selector, box,
        host_page=page, viewport_width=viewport_width)
    box = _crop_box(locator)
    if float(box["y"]) < -0.01:
        page.evaluate(
            """(dy) => { window.scrollBy(0, dy); }""",
            float(box["y"]) - 4.0,
        )
        page.wait_for_timeout(60)
        box = _crop_box(locator)
        _scroll_clear_of_chrome(
            nav_target, selector, box,
            host_page=page, viewport_width=viewport_width)
        box = _crop_box(locator)
    if float(box["x"]) < -0.01:
        page.evaluate(
            """(dx) => { window.scrollBy(dx, 0); }""",
            float(box["x"]) - 4.0,
        )
        page.wait_for_timeout(60)
        box = _crop_box(locator)
    win = _measure_window(page)
    vw = float(viewport_width)
    vh = float(win["innerHeight"])
    scroll_y = float(win["scrollY"])
    doc_h = float(win["scrollHeight"])
    raw_box = {
        "x": float(box["x"]), "y": float(box["y"]),
        "width": float(box["width"]), "height": float(box["height"]),
    }
    scroll_rcpt = _scroll_container_receipt(locator)
    shoot_box = dict(raw_box)
    client_w = scroll_rcpt.get("clientWidth")
    has_hscroll = (
        client_w is not None
        and float(raw_box["width"]) > float(client_w) + 0.5
    ) or bool(scroll_rcpt.get("inner_scrollports"))
    if client_w is not None and float(raw_box["width"]) > float(client_w) + 0.5:
        shoot_box["width"] = float(client_w)
        if float(shoot_box["x"] + shoot_box["width"]) > vw + GEOMETRY_TOLERANCE_PX:
            shoot_box["width"] = max(1.0, vw - float(shoot_box["x"]))
    crop_box_doc = {
        "x": shoot_box["x"],
        "y": shoot_box["y"] + scroll_y,
        "width": shoot_box["width"],
        "height": shoot_box["height"],
    }
    assert_box = shoot_box if has_hscroll else raw_box
    try:
        _assert_crop_geometry(
            assert_box, viewport_width=vw, doc_height=doc_h, name=dest.name,
            crop_box_doc=crop_box_doc, page=page_id, state=dest.name,
            locale=locale)
    except CaptureGeometryError:
        if not has_hscroll:
            raise
        _assert_crop_geometry(
            shoot_box, viewport_width=vw, doc_height=doc_h, name=dest.name,
            crop_box_doc=crop_box_doc, page=page_id, state=dest.name,
            locale=locale)
    _scroll_clear_of_chrome(
        nav_target, selector, shoot_box,
        host_page=page, viewport_width=viewport_width)
    dpr = _measure_dpr(page)
    extra: dict[str, Any] = {
        "dpr": dpr,
        "crop": True,
        "full_page": False,
        "crop_selector": selector,
        "fixture": "builder-payload",
        "locale": locale,
        "raw_box": raw_box,
    }
    extra.update(scroll_rcpt)
    chrome = _chrome_bottom(page)
    usable_h = max(64.0, vh - chrome - 8.0)
    needs_stitch = float(raw_box["height"]) > usable_h + 1.0 and not has_hscroll
    stitch_meta: list[dict[str, Any]] = []
    if needs_stitch:
        # Walk the document-y of the crop in usable_h steps.
        doc_y0 = float(raw_box["y"]) + scroll_y
        doc_y1 = doc_y0 + float(raw_box["height"])
        strips: list[bytes] = []
        y_cursor = doc_y0
        while y_cursor < doc_y1 - 0.5:
            page.evaluate(
                """(y) => { window.scrollTo(0, Math.max(0, y)); }""",
                y_cursor - chrome - 8.0,
            )
            page.wait_for_timeout(60)
            strip_box = {
                "x": max(0.0, float(raw_box["x"])),
                "y": max(chrome + 4.0, float(_crop_box(locator)["y"])),
                "width": min(
                    float(raw_box["width"]),
                    vw - max(0.0, float(raw_box["x"]))),
                "height": min(
                    usable_h,
                    doc_y1 - (float(page.evaluate(
                        "() => window.scrollY || document.documentElement.scrollTop || 0"
                    )) + chrome + 4.0)),
            }
            if strip_box["height"] < 8:
                break
            _scroll_clear_of_chrome(
                nav_target, selector, strip_box,
                host_page=page, viewport_width=viewport_width)
            strip_path = dest.with_suffix(f".strip{len(strips)}.png")
            page.screenshot(path=str(strip_path), type="png", clip=strip_box)
            samples, meta = _occlusion_samples(locator)
            stitch_meta.append({
                "clip": dict(strip_box),
                "occlusionSamples": samples,
                "samples_span": meta["samples_span"],
                "y_coverage": meta["y_coverage"],
            })
            strips.append(strip_path.read_bytes())
            strip_path.unlink(missing_ok=True)
            y_cursor += usable_h * 0.92  # slight overlap
            if len(strips) > 20:
                raise RuntimeError(f"{dest.name}: stitch runaway")
        dest.write_bytes(_stitch_png_bytes(strips))
        extra["stitched"] = len(strips)
        extra["stitch_strips"] = stitch_meta
        extra["crop_box"] = dict(raw_box)
        extra["occlusionSamples"] = stitch_meta[0]["occlusionSamples"]
        extra["samples_span"] = "crop∩viewport"
        extra["y_coverage"] = max(
            float(s.get("y_coverage") or 0) for s in stitch_meta)
    elif (
        float(raw_box["x"]) >= -0.01
        and float(raw_box["x"]) + float(raw_box["width"])
            <= vw + GEOMETRY_TOLERANCE_PX
        and float(raw_box["y"]) >= -0.01
        and not has_hscroll
    ):
        locator.screenshot(path=str(dest), type="png")
        extra["crop_box"] = dict(raw_box)
        _attach_occlusion(extra, locator)
        extra["stitched"] = 1
    else:
        clip = {
            "x": max(0.0, float(shoot_box["x"])),
            "y": max(0.0, float(shoot_box["y"])),
            "width": min(
                float(shoot_box["width"]),
                vw - max(0.0, float(shoot_box["x"]))),
            "height": min(
                float(shoot_box["height"]),
                vh - max(0.0, float(shoot_box["y"]))),
        }
        page.screenshot(path=str(dest), type="png", clip=clip)
        extra["crop_box"] = dict(clip)
        _attach_occlusion(extra, locator)
        extra["stitched"] = 1
    scroll_y = float(_measure_window(page)["scrollY"])
    extra["crop_box_doc"] = {
        "x": float(extra["crop_box"]["x"]),
        "y": float(extra["crop_box"]["y"]) + scroll_y,
        "width": float(extra["crop_box"]["width"]),
        "height": float(extra["crop_box"]["height"]),
    }
    extra["scroll_y_at_shot"] = scroll_y
    extra["device_px_span"] = _device_px_span(extra["crop_box"], dpr)
    visible = _locale_visible_text(locator, locale)
    independent = _element_text_independent(locator, locale)
    anchor = "权重法则" if locale == "zh" else "Weights law"
    label_at = visible.find(anchor)
    if label_at < 0:
        label_at = visible.upper().find(anchor.upper())
    head_src = visible[label_at:] if label_at >= 0 else visible
    extra["visible_text_head"] = head_src.replace("\n", " ").strip()[:80]
    extra["visible_text_sha256"] = hashlib.sha256(
        visible.encode("utf-8")).hexdigest()
    extra["element_text_head"] = independent.replace("\n", " ").strip()[:80]
    extra["element_text_sha256"] = hashlib.sha256(
        independent.encode("utf-8")).hexdigest()
    if extra["element_text_sha256"] != extra["visible_text_sha256"]:
        other_needle = "权重法则" if locale == "en" else "Weights law"
        if other_needle in visible or other_needle in independent:
            raise RuntimeError(
                f"{dest.name}: locale leak in text receipts "
                f"(other={other_needle!r})")
    extra["cropDomSha256"] = _crop_dom_sha256(locator, locale)
    extra["_element_text"] = visible
    extra["innerWidth"] = int(round(float(win["innerWidth"])))
    extra["innerHeight"] = int(round(float(win["innerHeight"])))
    # Align device_px_span + crop_box(_doc) to the PNG actually written
    # (stitch / element screenshot can differ from getBoundingClientRect).
    # Snap CSS box to integer device/dpr so floor/ceil recompute matches PNG.
    pw_chk, ph_chk = _png_size(dest)
    span0 = extra.get("device_px_span") or _device_px_span(extra["crop_box"], dpr)
    dpr_f = float(dpr) if float(dpr) > 0 else 1.0
    x0 = int(span0["x0"])
    y0 = int(span0["y0"])
    extra["device_px_span"] = {
        "x0": x0,
        "y0": y0,
        "x1": x0 + int(pw_chk),
        "y1": y0 + int(ph_chk),
    }
    extra["crop_box"] = {
        "x": float(x0) / dpr_f,
        "y": float(y0) / dpr_f,
        "width": float(pw_chk) / dpr_f,
        "height": float(ph_chk) / dpr_f,
    }
    scroll_y_align = float(extra.get("scroll_y_at_shot") or 0.0)
    extra["crop_box_doc"] = {
        "x": float(extra["crop_box"]["x"]),
        "y": float(extra["crop_box"]["y"]) + scroll_y_align,
        "width": float(extra["crop_box"]["width"]),
        "height": float(extra["crop_box"]["height"]),
    }
    _assert_shot_geometry(
        dest, extra, int(round(vw)), int(round(vh)))
    png = dest.read_bytes()
    if png[:8] != b"\x89PNG\r\n\x1a\n" or b"IEND" not in png:
        raise RuntimeError(f"{dest.name} is not a finished PNG")
    pw, ph = pw_chk, ph_chk
    return {
        **extra,
        "bytes": len(png),
        "sha256": hashlib.sha256(png).hexdigest(),
        "width": pw,
        "height": ph,
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
    """analystBox (and sibling pill when the pair fits) inside cropBox."""
    if cell.get("coordSpace") == "host-page":
        crop = _css_box(cell.get("crop_box_doc") or cell.get("cropBox")
                        or cell.get("crop_box"))
    else:
        crop = _css_box(cell.get("cropBox") or cell.get("crop_box"))
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
    return _method_table_390_pair_ratified(files, pages_out)


def _method_table_390_pair_ratified(
        files: list[str], pages_out: Sequence[Mapping[str, Any]]) -> bool:
    """Start/end table crops may share bytes when scrollWidth ≤ clientWidth.

    E-B1 still requires both PNGs + scroll receipts; when the table fits the
    phone width (observed on some ZH cells) scrollLeft=0 == max and the two
    frames are byte-identical by construction — that is not a collision defect.
    """
    if len(files) != 2:
        return False
    pat = re.compile(
        r"^method_table_390_(start|end)-(.+)-(dark|light)-(en|zh)-(\d+)\.png$"
    )
    parsed = []
    for name in files:
        m = pat.match(name)
        if not m:
            return False
        parsed.append({
            "pos": m.group(1), "slug": m.group(2), "theme": m.group(3),
            "locale": m.group(4), "width": m.group(5), "file": name,
        })
    if {row["pos"] for row in parsed} != {"start", "end"}:
        return False
    if len({(r["slug"], r["theme"], r["locale"], r["width"]) for r in parsed}) != 1:
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
        add(f"method_open-{slug}-dark-en-390.png")
        add(f"method_open-{slug}-dark-zh-390.png")
        add(f"method_open-{slug}-light-zh-390.png")
        for locale in ("en", "zh"):
            add(f"method_table_390_start-{slug}-dark-{locale}-390.png")
            add(f"method_table_390_end-{slug}-dark-{locale}-390.png")
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
        add(
            "disclosure_rows_open-macro_financial_conditions-dark-en-390"
            f"{row}.png"
        )
        add(
            "disclosure_rows_open-macro_financial_conditions-dark-zh-390"
            f"{row}.png"
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
            const el = document.querySelector('.mc-read-topic');
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
                page.wait_for_selector(".mc-read-topic", timeout=15000)
                styles = _topic_styles(page)
                style_rows[n] = styles
                topic = page.locator(".mc-read-topic").first
                info = _shot(
                    EVIDENCE / name, page, topic,
                    selector=".mc-read-topic", locale=locale)
                states.append(_state(
                    name, theme, locale, "desktop", info, viewport_width=1440,
                    verified_how="element clip of the same .mc-read-topic; computed style in probes.json",
                    crop=True, selector=".mc-read-topic", force_state="read_word",
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
                            probes[mat_key]["coordSpace"] = "host-page"
                            probes[mat_key]["hostFrameOffset"] = host_offset
                            probes[mat_key]["host_scroll_y_at_shot"] = (
                                host_scroll_y)
                            probes[mat_key]["frameInnerWidth"] = frame_inner
                            probes[mat_key]["analystBoxHost"] = host_analyst
                            probes[mat_key]["siblingPillBoxHost"] = host_pill
                            probes[mat_key]["cropBoxHost"] = host_crop
                            info = _shot_chipmat_clip(
                                EVIDENCE / chipmat_name, page, page_clip,
                                selector=str(
                                    rail_scroll.get("scrollContainerSelector")
                                    or ".mq-suitenav-rail"),
                                locale=locale,
                                text_head=str(
                                    rail_scroll.get("elementTextHead") or ""),
                                frame_inner_width=frame_inner,
                                host_offset=host_offset,
                                crop_dom_sha256=str(
                                    probes[mat_key].get("cropDomSha256") or ""),
                                host_for_occlusion=host,
                            )
                            info["page_id"] = page_name
                            info["analystBox"] = host_analyst
                            info["siblingPillBox"] = host_pill
                            info["coordSpace"] = "host-page"
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
                                    f"{rail_scroll.get('scrollContainerSelector')} "
                                    f"scrollLeft={rail_scroll.get('scrollLeftAfter')} "
                                    f"unmutated pairFits="
                                    f"{rail_scroll.get('chipmatPairFits')}"),
                                crop=True,
                                selector=str(
                                    rail_scroll.get("scrollContainerSelector")
                                    or ".mq-suitenav-rail"),
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
                    ("dark", "en", 390), ("dark", "zh", 390),
                    ("light", "zh", 390),
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
                    body = target.locator(METHOD_OPEN_SELECTOR).first
                    body.wait_for(timeout=15000)
                    _assert_method_dl_contained(body)
                    info = _element_shot_guarded(
                        EVIDENCE / name, page, body,
                        selector=METHOD_OPEN_SELECTOR, locale=locale,
                        viewport_width=width, target_for_nav=target)
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
                    # E-B1(3): photograph the whole table via start+end scrolls
                    # for the four dark method_open 390 cells (FC/labor × EN/ZH).
                    if width == 390 and theme == "dark":
                        probes.setdefault("method_table_390_text", {})
                        table = body.locator("table.mq-table, .mq-table").first
                        if table.count():
                            table_sel = (
                                f"{METHOD_OPEN_SELECTOR} .mq-table"
                            )
                            full_text = str(table.evaluate(
                                """el => (el.innerText || '')
                                    .replace(/\\s+/g, ' ').trim()"""
                            ) or "")
                            probes["method_table_390_text"][
                                f"method_table_390-{slug}-dark-{locale}-390"
                            ] = full_text
                            for pos, scroll_to in (
                                ("start", 0),
                                ("end", None),
                            ):
                                tname = (
                                    f"method_table_390_{pos}-{slug}-"
                                    f"dark-{locale}-390.png"
                                )
                                print(f"capture {tname}", flush=True)
                                scroll_rcpt = table.evaluate(
                                    """(el, args) => {
                                        const want = args.pos;
                                        if (want === 'end') {
                                          el.scrollLeft = el.scrollWidth;
                                        } else {
                                          el.scrollLeft = 0;
                                        }
                                        const st = getComputedStyle(el);
                                        return {
                                          scroll_container_selector:
                                            el.classList.contains('mq-table')
                                              ? '.mq-table' : 'table.mq-table',
                                          scrollWidth: el.scrollWidth,
                                          clientWidth: el.clientWidth,
                                          scrollLeft: el.scrollLeft,
                                          overflow_x: st.overflowX,
                                        };
                                    }""",
                                    {"pos": pos},
                                )
                                page.wait_for_timeout(80)
                                # Visible text at THIS scrollLeft — only cells
                                # whose box intersects the scrollport client.
                                vis_at_scroll = str(table.evaluate(
                                    """(el, locale) => {
                                        const prefer = locale === 'zh' ? 'l-zh' : 'l-en';
                                        const other = locale === 'zh' ? 'l-en' : 'l-zh';
                                        const cr = el.getBoundingClientRect();
                                        const parts = [];
                                        for (const cell of el.querySelectorAll('th, td')) {
                                          const r = cell.getBoundingClientRect();
                                          if (r.right < cr.left + 1 || r.left > cr.right - 1) continue;
                                          if (r.bottom < cr.top + 1 || r.top > cr.bottom - 1) continue;
                                          const clone = cell.cloneNode(true);
                                          clone.querySelectorAll('.' + other).forEach(n => n.remove());
                                          const t = (clone.innerText || '').replace(/\\s+/g, ' ').trim();
                                          if (t) parts.push(t);
                                        }
                                        return parts.join(' ').replace(/\\s+/g, ' ').trim();
                                    }""",
                                    locale,
                                ) or "")
                                tinfo = _element_shot_guarded(
                                    EVIDENCE / tname, page, table,
                                    selector=table_sel, locale=locale,
                                    viewport_width=390, target_for_nav=target)
                                tinfo.update(scroll_rcpt or {})
                                tinfo["visible_text_head"] = vis_at_scroll[:200]
                                tinfo["visible_text_sha256"] = hashlib.sha256(
                                    vis_at_scroll.encode("utf-8")).hexdigest()
                                tinfo["visible_text_at_scroll"] = vis_at_scroll
                                tinfo["shot_route"] = _shot_route_of(target)
                                tinfo["page_id"] = page_name
                                tinfo.pop("_element_text", None)
                                probes.setdefault(
                                    "method_table_390_visible", {})[tname] = (
                                    vis_at_scroll)
                                dest_list.append(_state(
                                    tname, theme, locale, "mobile", tinfo,
                                    viewport_width=390,
                                    verified_how=(
                                        f"{page_name} method table "
                                        f"scrollLeft={pos}; crop {table_sel}"
                                    ),
                                    crop=True, selector=table_sel,
                                    force_state=f"method_table_390_{pos}",
                                    family="method_table_390",
                                ))
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
                    body = page.locator(LINEAGE_OPEN_SELECTOR).first
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
                ("_rows_owner", "p.mq-owner", "Owner", "所有者"),
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
                        const owners = Array.from(
                            document.querySelectorAll('p.mq-owner'));
                        const o = owners.find(el =>
                            /Owner|所有者/.test(el.textContent || ''));
                        if (o) {
                            const d = o.closest('details');
                            if (d) d.open = true;
                        }
                        const t = document.querySelector('p.mq-trace');
                        if (t) {
                            const d = t.closest('details');
                            if (d) d.open = true;
                        }
                    }"""
                )
                host_page.wait_for_timeout(120)
                return "click"

            def _disclosure_locator(target, sel: str):
                if sel == "p.mq-owner":
                    return target.locator("p.mq-owner").filter(
                        has_text=re.compile(r"Owner|所有者")
                    ).first, "p.mq-owner"
                if sel == "section.mq-ribbon":
                    return target.locator("section.mq-ribbon").first, sel
                if "p.mq-trace" in sel:
                    loc = target.locator("details.mc-details").filter(
                        has=target.locator("p.mq-trace")
                    ).first
                    return loc, "details.mc-details:has(p.mq-trace)"
                return target.locator(sel).first, sel

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
        declared = [row["file"] for row in declared_rows]
        for leftover in EVIDENCE.glob("*.png"):
            if leftover.name not in captured_files:
                leftover.unlink()
        tree_pngs = {path.name for path in EVIDENCE.glob("*.png")}
        orphans = sorted(tree_pngs - captured_files)
        if orphans:
            raise RuntimeError(
                f"evidence dir has PNGs not produced by this capture: {orphans}")
        extras = sorted(captured_files - set(declared))
        if extras:
            raise RuntimeError(f"captured minus declared: {extras}")
        computed_gaps = sorted(set(declared) - captured_files)
        probes["declared_cells"] = declared
        probes["declared_rows"] = declared_rows
        probes["declared_families"] = declared_families(appl)
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
