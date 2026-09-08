"""Recapture the Macro Command P3 evidence matrix from one production build.

House method: theme/lang settled before load; 2x device scale; 390/768 through a
same-width iframe harness (headless Chrome clamps --window-size below ~500).
Empty-state frames use fixture builds; E5 is photographed by stalling the fragment request.

HTTP servers are backgrounded and always killed.
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
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
THEMES = ("dark", "light")
LOCALES = ("en", "zh")
EMPTY_IDS = ("e1", "e2", "e3", "e4", "e5", "e6")
EMPTY_VIEWPORTS = ((1440, 900), (390, 844))
DESKTOP_FOLD = (1440, 900)

# Rest cells the visual-evidence checker requires (force_state must be null).
REST_FRAMES = {
    "01-dark-en-1440.png", "02-dark-zh-1440.png",
    "03-light-en-1440.png", "04-light-zh-1440.png",
    "09-dark-en-390.png", "10-dark-zh-390.png",
    "11-light-en-390.png", "12-light-zh-390.png",
}
# R6-B1: recapture the entire matrix at the committed code sha. A
# selective keep is how the last pass documented a page that no longer
# existed. Empty-state crops are rebuilt from fixtures in the same run.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SITE = ROOT / "site"
DATA = SITE / "macrodata"
EVIDENCE = ROOT / "mockups" / "evidence" / "macro-command-p3"
FIXTURES = EVIDENCE / "fixtures"
MANIFEST = EVIDENCE / "manifest.json"
PROBES = EVIDENCE / "probes.json"
ASSETS = (
    "theme.css", "theme.js",
    "macro_suite_boot.js", "macro_suite.css", "macro_suite.js",
    "macro_command.css", "macro_command.js",
    "navigation-refresh.css", "product-nav-icons.css", "nav_market.js",
)

CLEARANCE_AT_JS = """(target) => {
  /* r12-M2: HIT is document geometry, never which stop we are at.
     A sticky full cover is a HIT at ANY target when the node is
     not exposable: exposedAtScrollY = docTop - ovBottom < 0
     (reason sticky-rail-full-cover-unexposable). ovBottom is the
     occupied stick band (rail sits below the 60px site nav).
     A full cover whose 0 <= exposedAtScrollY <= maxScroll is
     excused as rail_fully_covered and records docTop, ovHeight,
     ovBottom, exposedAtScrollY. Partial covers stay
     rail_partially_covered. Fixed overlays remain hits.
     Never scrollBy. */
  const maxY = Math.max(0,
    document.documentElement.scrollHeight - window.innerHeight);
  let want = 0;
  if (target === 'max') want = maxY;
  else if (target === '50') want = maxY * 0.5;
  window.scrollTo(0, want);
  const reached = window.scrollY || document.documentElement.scrollTop;
  const overlays = [];
  const addBox = (el, name) => {
    if (!el) return;
    const cs = getComputedStyle(el);
    const pos = cs.position;
    if (pos !== 'fixed' && pos !== 'sticky') return;
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    const box = el.getBoundingClientRect();
    if (box.width < 1 || box.height < 1) return;
    overlays.push({
      name, pos,
      top: box.top, left: box.left, right: box.right, bottom: box.bottom,
      width: box.width, height: box.height,
    });
  };
  addBox(document.querySelector('.mc-rail'), 'rail');
  document.querySelectorAll('.mc-rail-link').forEach((el) => addBox(el, 'rail-chip'));
  addBox(document.querySelector('.mc-analyst'), 'analyst');
  const boot = document.getElementById('mmb-boot');
  const bootCs = boot ? getComputedStyle(boot) : null;
  const bootDisplay = bootCs ? bootCs.display : null;
  if (bootDisplay && bootDisplay !== 'none') addBox(boot, 'mmb-boot');
  const root = document.querySelector('.mc-panels');
  const base = {
    target, scrollY: reached, scrollWanted: want, maxScroll: maxY,
    maxScrollMatched: Math.abs(reached - want) < 2,
    mmbBootDisplay: bootDisplay, overlays,
  };
  if (!root) {
    return Object.assign({ok: false, reason: 'missing .mc-panels',
            textCount: 0, hits: [], excused: []}, base);
  }
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      return (node.nodeValue || '').replace(/\\s+/g, '').length
        ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
    },
  });
  const texts = [];
  while (walker.nextNode()) texts.push(walker.currentNode);
  if (texts.length === 0) {
    return Object.assign({ok: false, reason: 'empty text-node set',
            textCount: 0, hits: [], excused: []}, base);
  }
  const intersects = (a, b) => !(a.right <= b.left || a.left >= b.right
    || a.bottom <= b.top || a.top >= b.bottom);
  const fullyCovered = (text, ov) => text.top >= ov.top - 0.5
    && text.bottom <= ov.bottom + 0.5
    && text.left >= ov.left - 0.5
    && text.right <= ov.right + 0.5;
  const hits = [];
  const excused = [];
  const note = (list, node, rect, ov, reason, extra) => {
    const row = {
      text: String(node.nodeValue || '').trim().slice(0, 80),
      overlay: ov.name,
      overlayPos: ov.pos,
      box: {top: rect.top, left: rect.left, right: rect.right, bottom: rect.bottom},
      ovBox: {top: ov.top, left: ov.left, right: ov.right, bottom: ov.bottom},
      reason,
    };
    if (extra) Object.assign(row, extra);
    list.push(row);
  };
  for (const node of texts) {
    const range = document.createRange();
    range.selectNodeContents(node);
    for (const rect of range.getClientRects()) {
      if (rect.width < 1 || rect.height < 1) continue;
      if (rect.bottom < 0 || rect.top > window.innerHeight) continue;
      for (const ov of overlays) {
        if (!intersects(rect, ov)) continue;
        const fixed = ov.pos === 'fixed';
        const covered = fullyCovered(rect, ov);
        if (fixed) {
          note(hits, node, rect, ov, 'fixed-overlay-intersects-text');
          continue;
        }
        if (ov.pos === 'sticky' && covered) {
          const docTop = rect.top + window.scrollY;
          const ovHeight = ov.height;
          const ovBottom = ov.bottom;
          /* Rail sticks below the 60px site nav, so the exposable
             scroll is docTop − occupied bottom, not box height. */
          const exposedAtScrollY = docTop - ovBottom;
          const extra = {docTop, ovHeight, ovBottom, exposedAtScrollY};
          /* exposed > maxY cannot occur in-browser: fullyCovered
             requires rect.bottom <= ov.bottom + 0.5, so
             docTop <= ovBottom + scrollY and exposed <= scrollY <= maxY.
             The bound stays as defense if a future overlay reports a
             smaller maxY than the scroll that produced the cover. */
          if (exposedAtScrollY < 0 || exposedAtScrollY > maxY) {
            note(hits, node, rect, ov,
              'sticky-rail-full-cover-unexposable', extra);
          } else {
            note(excused, node, rect, ov,
              ov.name + '_fully_covered', extra);
          }
          continue;
        }
        const docTop = rect.top + window.scrollY;
        const ovHeight = ov.height;
        const ovBottom = ov.bottom;
        const exposedAtScrollY = docTop - ovBottom;
        note(excused, node, rect, ov, ov.name + '_partially_covered',
          {docTop, ovHeight, ovBottom, exposedAtScrollY});
      }
    }
  }
  const analyst = document.querySelector('.mc-analyst');
  const analystCs = analyst ? getComputedStyle(analyst) : null;
  const bootBox = (boot && bootDisplay && bootDisplay !== 'none')
    ? boot.getBoundingClientRect() : null;
  return Object.assign({
    ok: hits.length === 0,
    textCount: texts.length,
    hits,
    excused,
    analystPosition: analystCs ? analystCs.position : null,
    mmbBootInDom: Boolean(boot),
    mmbBootVisible: Boolean(boot && bootDisplay && bootDisplay !== 'none'
      && bootCs && bootCs.visibility !== 'hidden'),
    mmbBootBox: bootBox ? {
      top: bootBox.top, bottom: bootBox.bottom,
      left: bootBox.left, right: bootBox.right,
    } : null,
    scrollHeight: document.documentElement.scrollHeight,
    innerHeight: window.innerHeight,
  }, base);
}"""

RAIL_JS = """() => {
  const rail = document.querySelector('.mc-rail');
  const shell = document.querySelector('.mc-shell');
  const stance = document.querySelector('#overview .mc-stance');
  const list = document.querySelector('.mc-rail-list');
  if (!rail || !shell || !stance) return {ok: false, reason: 'missing'};
  stance.scrollIntoView({block: 'start'});
  window.scrollBy(0, -30);
  const parseAlpha = (color) => {
    const slash = color.match(/\\/\\s*([\\d.]+)\\s*\\)/);
    if (slash) return Number(slash[1]);
    const rgba = color.match(/rgba?\\(([^)]+)\\)/);
    if (rgba && rgba[1].split(',').length === 4) return Number(rgba[1].split(',')[3]);
    return 1;
  };
  const railBg = getComputedStyle(rail).backgroundColor;
  const shellBg = getComputedStyle(shell).backgroundColor;
  const doc = document.documentElement;
  const listStyle = list ? getComputedStyle(list) : null;
  return {
    ok: true,
    railBg, shellBg,
    railAlpha: parseAlpha(railBg),
    equal: railBg === shellBg,
    position: getComputedStyle(rail).position,
    stanceText: (stance.innerText || '').slice(0, 160),
    scrollWidth: doc.scrollWidth,
    clientWidth: doc.clientWidth,
    noDocOverflow: doc.scrollWidth === doc.clientWidth,
    listOverflowX: listStyle ? listStyle.overflowX : null,
    listMaxWidth: listStyle ? listStyle.maxWidth : null,
    listContain: listStyle ? listStyle.contain : null,
  };
}"""

STRIP_VOID_JS = """() => {
  /* R7-M2: at 1440 light EN, no filled rectangle wider than 40px may
     sit in the strip row outside a chip box. The container itself must
     not paint (material belongs to the chips). */
  const strip = document.querySelector('.mc-strip');
  if (!strip) return {ok: false, reason: 'missing strip'};
  const parseAlpha = (color) => {
    if (!color || color === 'transparent') return 0;
    const slash = color.match(/\\/\\s*([\\d.]+)\\s*\\)/);
    if (slash) return Number(slash[1]);
    const rgba = color.match(/rgba?\\(([^)]+)\\)/);
    if (rgba && rgba[1].split(',').length === 4) return Number(rgba[1].split(',')[3].trim());
    return 1;
  };
  const stripBox = strip.getBoundingClientRect();
  const chips = [...strip.querySelectorAll(':scope > .mc-chip')];
  const children = [...strip.children];
  const emptyChildren = children.filter((el) => {
    const text = (el.textContent || '').trim();
    return text.length === 0 && el.children.length === 0;
  }).length;
  const chipBoxes = chips.map((el) => {
    const box = el.getBoundingClientRect();
    return {left: box.left, right: box.right, top: box.top, bottom: box.bottom,
            width: box.width, height: box.height};
  });
  const rows = {};
  for (const box of chipBoxes) {
    const key = String(Math.round(box.top));
    (rows[key] = rows[key] || []).push(box);
  }
  const voids = [];
  for (const [top, boxes] of Object.entries(rows)) {
    boxes.sort((a, b) => a.left - b.left);
    const rightGap = stripBox.right - boxes[boxes.length - 1].right;
    if (rightGap > 40) voids.push({top: Number(top), width: rightGap, side: 'right'});
    const leftGap = boxes[0].left - stripBox.left;
    if (leftGap > 40) voids.push({top: Number(top), width: leftGap, side: 'left'});
    for (let i = 0; i < boxes.length - 1; i += 1) {
      const gap = boxes[i + 1].left - boxes[i].right;
      if (gap > 40) voids.push({top: Number(top), width: gap, side: 'between'});
    }
  }
    const stripBg = getComputedStyle(strip).backgroundColor;
    const stripFilled = parseAlpha(stripBg) > 0.05;
    const bodyBackgroundColor = getComputedStyle(document.body).backgroundColor;
    const bgToken = getComputedStyle(document.documentElement)
      .getPropertyValue('--bg').trim();
  /* r10-n1: one field. A >40px run outside a chip is a void
     whether the container paints (not gated on stripFilled). */
  const voidWiderThan40 = voids.some((v) => v.width > 40);
  return {
    ok: !voidWiderThan40
      && emptyChildren === 0 && chips.length === children.length,
    chipCount: chips.length,
    childCount: children.length,
    emptyChildren,
    stripBg,
    stripFilled,
    bodyBackgroundColor,
    bgToken,
    voids,
    maxVoidWidth: voids.length ? Math.max(...voids.map((v) => v.width)) : 0,
    voidWiderThan40,
    chipBoxes,
    stripBox: {left: stripBox.left, right: stripBox.right,
               top: stripBox.top, bottom: stripBox.bottom,
               width: stripBox.width, height: stripBox.height},
    viewport: {innerWidth: window.innerWidth, stripWidth: stripBox.width},
  };
}"""


HAIRLINE_JS = """() => {
  /* RIDER M2: exactly one hairline between the pill row and the first
     populated row on a light deep-linked sub-tab. Measure rule rects. */
  const figure = document.querySelector('#money .mc-figure');
  const pills = document.querySelector('#money .mc-subtabs');
  const visible = [...document.querySelectorAll('#money .mc-figure-tabbody')]
    .find((el) => !el.hidden && getComputedStyle(el).display !== 'none');
  if (!figure || !pills || !visible) {
    return {populated: false, reason: 'missing figure/pills/tab'};
  }
  const firstRow = visible.querySelector(
    '.mc-move-row, .mx-chg-row, .mc-move, [data-mc-empty]');
  if (!firstRow) {
    return {populated: false, reason: 'no row in visible tab'};
  }
  const pillBottom = pills.getBoundingClientRect().bottom;
  const rowTop = firstRow.getBoundingClientRect().top;
  const figCs = getComputedStyle(figure);
  const tabCs = getComputedStyle(visible);
  const figureBorderTopPx = parseFloat(figCs.borderTopWidth) || 0;
  const tabbodyBorderTopPx = parseFloat(tabCs.borderTopWidth) || 0;
  const rules = [];
  const consider = (el) => {
    const cs = getComputedStyle(el);
    const box = el.getBoundingClientRect();
    const bt = parseFloat(cs.borderTopWidth) || 0;
    if (bt >= 0.5 && box.top >= pillBottom - 2 && box.top <= rowTop + 2) {
      rules.push({
        className: String(el.className || el.tagName),
        top: box.top,
        borderTop: bt,
      });
    }
  };
  consider(figure);
  consider(visible);
  return {
    populated: true,
    hairlineCount: rules.length,
    rules,
    tabbodyBorderTopPx,
    figureBorderTopPx,
    firstRowClass: String(firstRow.className || ''),
    pillBottom,
    rowTop,
    visibleTab: visible.getAttribute('data-mc-tabbody'),
  };
}"""


RAIL_VIEWPORT_JS = """() => {
  /* BLOCKER-E1: measure the RAIL VIEWPORT, not each chip's own box.
     Content-sized chips have scrollWidth==clientWidth by construction;
     truncation is the list scroller + fade + pinned analyst.
     MAJOR-A: fadeWidth is parsed from the computed mask-image, never
     a harness constant echoing itself. */
  const list = document.querySelector('.mc-rail-list');
  const analyst = document.querySelector('.mc-analyst');
  const content = [...document.querySelectorAll('.mc-rail-link:not(.mc-analyst)')];
  if (!list || !analyst || !content.length) {
    return {ok: false, reason: 'missing rail-list/analyst/chips'};
  }
  const fadeMin = 24;
  const listCs = getComputedStyle(list);
  const maskImage = listCs.maskImage;
  const webkitMaskImage = listCs.webkitMaskImage;
  const maskRaw = (webkitMaskImage && webkitMaskImage !== 'none')
    ? webkitMaskImage
    : (maskImage || 'none');
  const maskOk = maskRaw !== 'none' && maskRaw !== '';
  const maxScrollLeft = Math.max(0, list.scrollWidth - list.clientWidth);

  const parseFadeWidth = (raw, listWidth) => {
    const text = String(raw || '').trim();
    if (!text || text === 'none') {
      throw new Error('rail fade mask-image is none/empty: ' + JSON.stringify(raw));
    }
    const calc = [...text.matchAll(/calc\\(\\s*100%\\s*-\\s*([\\d.]+)px\\s*\\)/g)];
    if (calc.length) {
      return Number(calc[calc.length - 1][1]);
    }
    const stops = [...text.matchAll(/(-?[\\d.]+)%/g)].map((m) => Number(m[1]));
    const opaque = stops.filter((p) => p < 100);
    if (opaque.length) {
      return (opaque[opaque.length - 1] / 100) * listWidth;
    }
    throw new Error('unparsable mask-image: ' + text);
  };

  const chipOwn = (el) => {
    const cs = getComputedStyle(el);
    return {
      overflow: cs.overflow,
      whiteSpace: cs.whiteSpace,
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
      selfClips: el.scrollWidth > el.clientWidth + 1,
    };
  };

  const visibleFraction = (el, listBox, analystBox, fadeLeft) => {
    const box = el.getBoundingClientRect();
    const visibleRight = Math.min(listBox.right, fadeLeft, analystBox.left);
    const visibleLeft = listBox.left;
    const left = Math.max(box.left, visibleLeft);
    const right = Math.min(box.right, visibleRight);
    const vis = Math.max(0, right - left);
    const underAnalyst = !(box.right <= analystBox.left || box.left >= analystBox.right
      || box.bottom <= analystBox.top || box.top >= analystBox.bottom);
    return {
      label: (el.innerText || '').replace(/\\s+/g, ' ').trim().slice(0, 80),
      fraction: box.width > 0 ? vis / box.width : 0,
      box: {left: box.left, right: box.right, top: box.top, bottom: box.bottom,
            width: box.width, height: box.height},
      underAnalyst,
      ...chipOwn(el),
    };
  };

  const snapshot = (scrollLeft) => {
    list.scrollLeft = scrollLeft;
    const listBox = list.getBoundingClientRect();
    const analystBox = analyst.getBoundingClientRect();
    const fadeWidth = parseFadeWidth(maskRaw, listBox.width);
    const fadeLeft = listBox.right - fadeWidth;
    const fadeBeginsBeforeAnalyst = analystBox.left - fadeLeft;
    return {
      scrollLeft: list.scrollLeft,
      listBox: {left: listBox.left, right: listBox.right,
                width: listBox.width, height: listBox.height},
      analystBox: {left: analystBox.left, right: analystBox.right,
                   width: analystBox.width, height: analystBox.height},
      fadeWidth,
      fadeLeft,
      fadeBeginsBeforeAnalyst,
      maskRaw,
      chips: content.map((el) => visibleFraction(el, listBox, analystBox, fadeLeft)),
    };
  };

  const at0 = snapshot(0);
  const atMax = snapshot(maxScrollLeft);
  const first = at0.chips[0] || {};
  const firstFullyVisibleAt0 = Boolean(
    first.fraction >= 0.99 && !first.underAnalyst);

  const fullyVisibleAt = [];
  for (let i = 0; i < content.length; i += 1) {
    const el = content[i];
    const visibleW = Math.max(1, list.clientWidth - at0.fadeWidth);
    const lo = Math.max(0, el.offsetLeft + el.offsetWidth - visibleW);
    const candidates = [0, lo, el.offsetLeft, maxScrollLeft];
    for (let d = -24; d <= 24; d += 4) {
      candidates.push(lo + d, el.offsetLeft + d);
    }
    let best = {fraction: -1, underAnalyst: true};
    let bestSL = 0;
    for (const raw of candidates) {
      const sl = Math.max(0, Math.min(maxScrollLeft, raw));
      const row = snapshot(sl);
      const chip = row.chips[i] || {};
      const better = chip.fraction > best.fraction
        || (chip.fraction === best.fraction && !chip.underAnalyst
            && best.underAnalyst);
      if (better) {
        best = chip;
        bestSL = row.scrollLeft;
      }
    }
    fullyVisibleAt.push({
      label: best.label,
      fullyVisibleAtScrollLeft: bestSL,
      fraction: best.fraction,
      underAnalyst: best.underAnalyst,
      fullyVisible: best.fraction >= 0.99 && !best.underAnalyst,
      overflow: best.overflow,
      whiteSpace: best.whiteSpace,
      scrollWidth: best.scrollWidth,
      clientWidth: best.clientWidth,
      selfClips: best.selfClips,
    });
  }

  const fadeBandOk = at0.fadeWidth >= fadeMin - 0.5
    && at0.fadeBeginsBeforeAnalyst >= fadeMin - 0.5
    && maskOk;
  const everyReachable = fullyVisibleAt.every((row) => row.fullyVisible);
  const ownLabelOk = fullyVisibleAt.every(
    (row) => !row.selfClips && row.whiteSpace === 'nowrap'
      && row.overflow !== 'hidden');
  /* (d) alone is never a pass. */
  const ok = firstFullyVisibleAt0 && everyReachable && fadeBandOk;
  return {
    ok,
    firstFullyVisibleAt0,
    everyReachable,
    fadeBandOk,
    maskOk,
    ownLabelOk,
    maskImage,
    webkitMaskImage,
    maskRaw,
    fadeWidth: at0.fadeWidth,
    fadeLeft: at0.fadeLeft,
    fadeBeginsBeforeAnalyst: at0.fadeBeginsBeforeAnalyst,
    maxScrollLeft,
    at0,
    atMax,
    chips: fullyVisibleAt,
  };
}"""


CHIP_MATERIAL_JS = """() => {
  const analyst = document.querySelector('.mc-analyst');
  const sibling = document.querySelector(
    '.mc-rail-link:not(.mc-analyst):not(.is-current)');
  if (!analyst || !sibling) return {ok: false, reason: 'missing chips'};
  const props = [
    'borderRadius', 'borderTopWidth', 'borderRightWidth',
    'borderBottomWidth', 'borderLeftWidth', 'borderTopStyle',
    'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
    'fontSize',
  ];
  const read = (el) => {
    const cs = getComputedStyle(el);
    const out = {};
    for (const key of props) out[key] = cs[key];
    return out;
  };
  const a = read(analyst);
  const s = read(sibling);
  const mismatches = props.filter((key) => a[key] !== s[key]);
  return {ok: mismatches.length === 0, analyst: a, sibling: s, mismatches};
}"""


def _run_clearance(page) -> dict[str, Any]:
    """R9: measure at scroll 0, 50%, max. Fail on any hit, empty text,
    or scrollReached != target at every position (r9-m2)."""
    positions: dict[str, Any] = {}
    for target in ("0", "50", "max"):
        row = page.evaluate(CLEARANCE_AT_JS, target)
        positions[target] = row
        if row.get("textCount", 0) == 0:
            raise RuntimeError(f"clearance empty text-node set at {target}: {row}")
        if not row.get("maxScrollMatched"):
            raise RuntimeError(
                f"clearance scrollReached != target at {target}: {row}")
        if not row.get("ok"):
            raise RuntimeError(f"clearance hits at {target}: {row.get('hits')}")
        max_scroll = float(row.get("maxScroll") or 0)
        for item in row.get("excused") or []:
            reason = str(item.get("reason") or "")
            if not (reason.endswith("_fully_covered")
                    or reason.endswith("_partially_covered")):
                continue
            exposed = item.get("exposedAtScrollY")
            if exposed is None or not (0 <= float(exposed) <= max_scroll):
                raise RuntimeError(
                    f"{reason} excuse names unreachable "
                    f"exposedAtScrollY={exposed} at {target} "
                    f"(maxScroll={max_scroll}): {item}")
            for key in ("docTop", "ovBottom", "exposedAtScrollY"):
                if key not in item:
                    raise RuntimeError(
                        f"{reason} excuse missing {key} at {target}: {item}")
    return {
        "ok": all(pos.get("ok") for pos in positions.values()),
        "textCount": positions["0"].get("textCount"),
        "positions": positions,
        "analystPosition": positions["0"].get("analystPosition"),
        "mmbBootInDom": positions["0"].get("mmbBootInDom"),
        "mmbBootVisible": positions["0"].get("mmbBootVisible"),
        "mmbBootDisplay": positions["0"].get("mmbBootDisplay"),
        "mmbBootBox": positions["0"].get("mmbBootBox"),
        "excusedCounts": {
            key: len(pos.get("excused") or []) for key, pos in positions.items()
        },
    }


def _run_chip_opens_chat(page) -> dict[str, Any]:
    """r10 evidence m4: click the ≤768 analyst chip and assert the
    same chat surface the FAB would have booted (`#mmb-root`)."""
    chip = page.query_selector("[data-mc-analyst]")
    if chip is None:
        raise RuntimeError("chip-opens-chat: missing [data-mc-analyst]")
    href = chip.get_attribute("href")
    chip.click()
    # theme.js mounts #mmb-root hidden until the panel opens; attached
    # is the mount the FAB would have booted (r10 evidence m4).
    page.wait_for_selector("#mmb-root", state="attached", timeout=30000)
    mounted = page.evaluate("""() => {
      const root = document.getElementById('mmb-root');
      const panel = document.getElementById('mmb-panel');
      const cs = root ? getComputedStyle(root) : null;
      return {
        mountedId: root ? root.id : null,
        mountedClass: root ? (root.className || '') : null,
        mountedDisplay: cs ? cs.display : null,
        mountedVisibility: cs ? cs.visibility : null,
        mmbPanelPresent: Boolean(panel),
        mmBrainMounted: Boolean(window.MMBrain && window.MMBrain.mounted),
      };
    }""")
    if not mounted.get("mountedId"):
        raise RuntimeError(f"chip-opens-chat: #mmb-root did not mount: {mounted}")
    return {
        "ok": True,
        "clicked": "data-mc-analyst",
        "href": href,
        "mountedId": mounted.get("mountedId"),
        "mountedClass": mounted.get("mountedClass"),
        "mmbPanelPresent": mounted.get("mmbPanelPresent"),
        "mmBrainMounted": mounted.get("mmBrainMounted"),
    }


def _colour_close(pixel: tuple[int, int, int], canvas: tuple[int, int, int],
                  tol: int = 10) -> bool:
    return all(abs(a - b) <= tol for a, b in zip(pixel, canvas))


def _pixel_scan_strip_void(path: Path, probe: dict[str, Any],
                           scale: int = 2) -> dict[str, Any]:
    """R8-m1: scan the captured strip-row band. Any run ≥40 CSS px of
    non-canvas colour outside a chip box is a void."""
    from PIL import Image
    image = Image.open(path).convert("RGB")
    strip = probe.get("stripBox") or {}
    chips = probe.get("chipBoxes") or []
    if not strip or not chips:
        return {"ok": False, "reason": "missing strip/chip boxes",
                "pixelVoidWiderThan40": True, "pixelVoids": []}
    # First chip row only — the coverage chip is a full-width second row.
    row_top = min(box["top"] for box in chips)
    row_boxes = [box for box in chips if abs(box["top"] - row_top) < 4]
    y0 = int(min(box["top"] for box in row_boxes) * scale)
    y1 = int(max(box["bottom"] for box in row_boxes) * scale)
    x0 = int(strip["left"] * scale)
    x1 = int(strip["right"] * scale)
    y0 = max(0, y0)
    y1 = min(image.height, y1)
    x0 = max(0, x0)
    x1 = min(image.width, x1)
    chip_dev = [
        (int(box["left"] * scale) - 1, int(box["right"] * scale) + 1,
         int(box["top"] * scale) - 1, int(box["bottom"] * scale) + 1)
        for box in row_boxes
    ]

    def in_chip(x: int, y: int) -> bool:
        return any(l <= x <= r and t <= y <= b for l, r, t, b in chip_dev)

    canvas, canvas_source = _choose_strip_canvas(
        image, row_boxes, scale, in_chip, probe.get("bgToken"))
    bg_token_rgb = _rgb_token((probe.get("bgToken") or "").strip())
    canvas_delta = (
        [abs(int(a) - int(b)) for a, b in zip(canvas, bg_token_rgb)]
        if bg_token_rgb is not None else None
    )

    threshold = 40 * scale
    voids: list[dict[str, Any]] = []
    for y in range(y0, y1):
        run = 0
        run_x = x0
        for x in range(x0, x1):
            if in_chip(x, y):
                if run >= threshold:
                    voids.append({"y": y, "x": run_x, "widthCss": run / scale})
                run = 0
                run_x = x
                continue
            pixel = image.getpixel((x, y))
            if _colour_close(pixel, canvas):
                if run >= threshold:
                    voids.append({"y": y, "x": run_x, "widthCss": run / scale})
                run = 0
                run_x = x
                continue
            if run == 0:
                run_x = x
            run += 1
        if run >= threshold:
            voids.append({"y": y, "x": run_x, "widthCss": run / scale})
    return {
        "ok": len(voids) == 0,
        "pixelVoidWiderThan40": len(voids) > 0,
        "pixelVoids": voids[:12],
        "pixelVoidCount": len(voids),
        "canvasRgb": list(canvas),
        "canvasSource": canvas_source,
        "bgTokenRgb": list(bg_token_rgb) if bg_token_rgb is not None else None,
        "delta": canvas_delta,
        "band": {"x0": x0, "x1": x1, "y0": y0, "y1": y1},
    }


def _choose_strip_canvas(image, row_boxes, scale: int, in_chip,
                         bg_token: Any) -> tuple[tuple[int, int, int], str]:
    """Pick the strip canvas: inter-chip gap, else the --bg token.

    Fallback reads getComputedStyle(document.documentElement)
    .getPropertyValue('--bg') (passed in as bg_token) and labels the
    source "--bg custom property". bodyBackgroundColor is a separate
    receipt field, never the canvasSource label.
    """
    row_boxes_sorted = sorted(row_boxes, key=lambda box: box["left"])
    if len(row_boxes_sorted) >= 2:
        gap_left = row_boxes_sorted[0]["right"]
        gap_right = row_boxes_sorted[1]["left"]
        gap_css = gap_right - gap_left
        sample_x_css = (gap_left + gap_right) / 2
        sample_y_css = (
            min(box["top"] for box in row_boxes)
            + max(box["bottom"] for box in row_boxes)
        ) / 2
        sample_x = int(sample_x_css * scale)
        sample_y = int(sample_y_css * scale)
        sample_x = min(max(0, sample_x), image.width - 1)
        sample_y = min(max(0, sample_y), image.height - 1)
        if gap_css >= 8 and not in_chip(sample_x, sample_y):
            sampled = image.getpixel((sample_x, sample_y))
            token = (bg_token or "").strip()
            parsed = _rgb_token(token)
            if parsed is None:
                raise RuntimeError(
                    "strip-void canvas: gap sample has no parsable --bg token")
            delta = [abs(int(a) - int(b)) for a, b in zip(sampled, parsed)]
            if any(channel > 2 for channel in delta):
                raise RuntimeError(
                    f"strip-void canvas sample {list(sampled)} != --bg "
                    f"{list(parsed)} delta={delta} at "
                    f"({sample_x_css:.2f}css,{sample_y_css:.2f}css)")
            return sampled, (
                f"strip-inter-chip-gap ({sample_x_css:.2f}css,"
                f"{sample_y_css:.2f}css) gapCss={gap_css:.2f}")
    token = (bg_token or "").strip()
    parsed = _rgb_token(token)
    if parsed is None:
        raise RuntimeError(
            "strip-void canvas: gap <8px or in_chip and --bg did not parse")
    return parsed, "--bg custom property"


def _paint_alpha(pixel: tuple[int, ...], paint: tuple[int, ...],
                 canvas: tuple[int, ...]) -> float:
    """Recover paint fraction assuming P = a*C + (1-a)*B."""
    num = sum((int(p) - int(b)) * (int(c) - int(b))
              for p, c, b in zip(pixel, paint, canvas))
    den = sum((int(c) - int(b)) ** 2 for c, b in zip(paint, canvas))
    if den <= 0:
        return 0.0
    return max(0.0, min(1.0, num / den))


def _confirm_rail_fade_visual(page, viewport: dict[str, Any]) -> dict[str, Any]:
    """MAJOR-A: pixel-scan the fade band and compare to the parsed fadeLeft."""
    from PIL import Image

    fade_left = float(viewport.get("fadeLeft") or (viewport.get("at0") or {}).get("fadeLeft"))
    fade_width = float(viewport.get("fadeWidth") or (viewport.get("at0") or {}).get("fadeWidth"))
    live = page.evaluate(
        """(fadeWidth) => {
      const list = document.querySelector('.mc-rail-list');
      const content = [...document.querySelectorAll('.mc-rail-link:not(.mc-analyst)')];
      if (!list || !content.length) return {ok: false, reason: 'missing'};
      const listBox = list.getBoundingClientRect();
      const fadeLeft = listBox.right - fadeWidth;
      const maxSL = Math.max(0, list.scrollWidth - list.clientWidth);
      let placed = false;
      for (const el of content) {
        const target = el.offsetLeft + el.offsetWidth * 0.35
          - (fadeLeft - listBox.left);
        list.scrollLeft = Math.max(0, Math.min(maxSL, target));
        const box = el.getBoundingClientRect();
        if (box.left < fadeLeft - 12 && box.right > fadeLeft + 8) {
          placed = true;
          break;
        }
      }
      if (!placed) {
        list.scrollLeft = maxSL;
      }
      const chips = content.map((node) => {
        const box = node.getBoundingClientRect();
        return {left: box.left, right: box.right, top: box.top, bottom: box.bottom};
      });
      return {
        ok: true,
        fadeLeft,
        listBox: {left: listBox.left, right: listBox.right,
                  width: listBox.width, height: listBox.height},
        chips,
      };
    }""",
        fade_width,
    )
    if not live.get("ok"):
        raise RuntimeError(f"fade visual: live rail geometry failed: {live}")
    fade_left = float(live["fadeLeft"])
    list_box = live.get("listBox") or {}
    chips = live.get("chips") or []
    page.wait_for_timeout(80)
    dpr = float(page.evaluate("window.devicePixelRatio"))
    bg_token = page.evaluate(
        "getComputedStyle(document.documentElement).getPropertyValue('--bg')")
    canvas = _rgb_token((bg_token or "").strip())
    if canvas is None:
        raise RuntimeError(f"fade visual: --bg did not parse: {bg_token!r}")
    paint_box = None
    for box in chips:
        if float(box.get("left") or 0) < fade_left and float(box.get("right") or 0) > fade_left - 8:
            paint_box = box
            break
    if paint_box is None:
        paint_box = chips[-1] if chips else None
    if not paint_box:
        raise RuntimeError("fade visual: no chip box after scroll")
    tmp = Path(os.environ.get("TMPDIR", "/tmp")) / f"mc-fade-{os.getpid()}.png"
    page.screenshot(path=str(tmp), type="png", full_page=False)
    try:
        image = Image.open(tmp).convert("RGB")
        y0 = max(0, int(float(paint_box["top"]) * dpr))
        y1 = min(image.height, int(float(paint_box["bottom"]) * dpr))
        sample_right = min(float(paint_box["right"]), fade_left - 2)
        x0 = max(0, int(float(paint_box["left"]) * dpr))
        x1 = min(image.width, int(sample_right * dpr))
        paint = None
        best = -1
        for y in range(y0, max(y0 + 1, y1)):
            for x in range(x0, max(x0 + 1, x1)):
                pixel = image.getpixel((x, y))
                dist = sum((int(a) - int(b)) ** 2 for a, b in zip(pixel, canvas))
                if dist > best:
                    best = dist
                    paint = pixel
        if paint is None or best < 20:
            raise RuntimeError(
                f"fade visual: no chip/label paint distinct from canvas "
                f"{canvas} in {paint_box}")

        def column_alpha(x_css: float) -> float:
            xd = int(x_css * dpr)
            if xd < 0 or xd >= image.width:
                return 0.0
            values = [
                _paint_alpha(image.getpixel((xd, y)), paint, canvas)
                for y in range(y0, max(y0 + 1, y1))
                if 0 <= y < image.height
            ]
            return max(values) if values else 0.0

        start = fade_left - 16
        end = float(list_box.get("right") or fade_left + fade_width)
        xs = [start + step for step in range(int(math.ceil(end - start)) + 1)]
        raw = [column_alpha(x) for x in xs]
        # Glyph gaps are not the fade. Take a 3-css-px max so a letter
        # hole cannot look like the mask.
        smooth = []
        for i, alpha in enumerate(raw):
            window = raw[max(0, i - 1): i + 2]
            smooth.append(max(window))
        opaque_run = 0
        fade_visual = None
        fade_half = None
        for x_css, alpha in zip(xs, smooth):
            if alpha >= 0.92:
                opaque_run += 1
            if opaque_run >= 3 and fade_visual is None and alpha < 0.92:
                fade_visual = x_css
            if opaque_run >= 3 and fade_half is None and alpha < 0.5:
                fade_half = x_css
                break
        if fade_visual is None or fade_half is None:
            # No chip paint in the band (list does not overflow). The
            # mask still applies; the band is canvas-on-canvas, so the
            # parsed stop is the visual start.
            band_paint = max(raw) if raw else 0.0
            if band_paint >= 0.5:
                raise RuntimeError(
                    f"fade visual: paint in the band never crossed 50% "
                    f"[{start}, {end}] fadeLeft={fade_left} maxAlpha={band_paint}")
            fade_visual = fade_left
            fade_half = fade_left
        if abs(fade_visual - fade_left) > 4:
            raise RuntimeError(
                f"fade visual start {fade_visual:.2f} != fadeLeft "
                f"{fade_left:.2f} (tol 4 css px) half={fade_half}")
        return {
            "fadeVisualStartX": fade_visual,
            "fadeVisualHalfX": fade_half,
            "fadeLeft": fade_left,
            "fadeWidth": fade_width,
            "maskRaw": viewport.get("maskRaw") or (viewport.get("at0") or {}).get("maskRaw"),
        }
    finally:
        tmp.unlink(missing_ok=True)


def _sticky_cover_verdict(doc_top: float, ov_bottom: float,
                          max_scroll: float | None = None) -> tuple[str, float]:
    """Document-geometry HIT/excuse for a sticky full cover (r12-M2).

    exposedAtScrollY = docTop − ovBottom (occupied stick band, not
    box height — the rail sits below the 60px site nav).
    exposed > maxScroll cannot occur in-browser (fullyCovered implies
    docTop <= ovBottom + scrollY <= ovBottom + maxScroll); the bound
    stays as defense if a future overlay reports a smaller maxY.
    """
    exposed = doc_top - ov_bottom
    unreachable = max_scroll is not None and exposed > max_scroll
    if exposed < 0 or unreachable:
        return "sticky-rail-full-cover-unexposable", exposed
    return "rail_fully_covered", exposed


SYNTHETIC_CLEARANCE_HTML = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
  body { margin: 0; font: 16px/20px sans-serif; padding-top: 60px; }
  .site-nav {
    position: fixed; top: 0; left: 0; right: 0; height: 60px;
    background: #222; color: #fff; z-index: 5;
  }
  .mc-rail {
    position: sticky; top: 60px; z-index: 4; height: 200px;
    background: #c00; color: #fff;
  }
  .mc-panels { margin-top: -80px; }
  .stuck { height: 20px; margin: 0; padding: 0; }
  .below { height: 20px; margin: 80px 0 0; }
  .under-pill { height: 20px; margin: 570px 0 0; }
  .spacer { height: 110px; }
  #mmb-boot {
    position: fixed; bottom: 0; left: 0; right: 0; height: 40px;
    background: #00c; color: #fff; z-index: 6;
  }
</style></head>
<body>
  <div class="site-nav">NAV</div>
  <div class="mc-rail">RAIL</div>
  <div class="mc-panels">
    <p class="stuck">inside zone</p>
    <p class="below">below zone</p>
    <p class="under-pill">under pill</p>
    <div class="spacer"></div>
  </div>
  <div id="mmb-boot">PILL</div>
</body></html>
"""


def _synthetic_node_receipts(
        positions: dict[str, Any], needle: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for station, pos in positions.items():
        hits = [row for row in (pos.get("hits") or [])
                if needle in str(row.get("text") or "")]
        excused = [row for row in (pos.get("excused") or [])
                   if needle in str(row.get("text") or "")]
        if hits:
            row = hits[0]
            out[station] = {
                "verdict": "hit",
                "reason": row.get("reason"),
                "exposedAtScrollY": row.get("exposedAtScrollY"),
                "docTop": row.get("docTop"),
                "ovBottom": row.get("ovBottom"),
                "scrollY": pos.get("scrollY"),
                "maxScroll": pos.get("maxScroll"),
            }
        elif excused:
            row = excused[0]
            out[station] = {
                "verdict": "excused",
                "reason": row.get("reason"),
                "exposedAtScrollY": row.get("exposedAtScrollY"),
                "docTop": row.get("docTop"),
                "ovBottom": row.get("ovBottom"),
                "scrollY": pos.get("scrollY"),
                "maxScroll": pos.get("maxScroll"),
            }
        else:
            out[station] = {
                "verdict": "absent",
                "scrollY": pos.get("scrollY"),
                "maxScroll": pos.get("maxScroll"),
            }
    return out


def _assert_synthetic_hit_rule(receipts: dict[str, Any]) -> None:
    inside = receipts["inside zone"]
    below = receipts["below zone"]
    pill = receipts["under pill"]
    for station in ("0", "50", "max"):
        if inside[station].get("verdict") != "hit":
            raise RuntimeError(
                f"synthetic unexposable node not hit at {station}: "
                f"{inside[station]}")
    excused = [row for row in below.values() if row.get("verdict") == "excused"]
    if not excused or excused[0].get("exposedAtScrollY") is None:
        raise RuntimeError(
            f"synthetic exposable node has no excused receipt: {below}")
    if not any(row.get("verdict") == "hit" for row in pill.values()):
        raise RuntimeError(
            f"synthetic bottom-fixed node has no hit: {pill}")


def _run_synthetic_clearance(page) -> dict[str, Any]:
    """MINOR-B: run the SHIPPED CLEARANCE_AT_JS on the three-station page."""
    page.set_content(SYNTHETIC_CLEARANCE_HTML)
    positions: dict[str, Any] = {}
    for target in ("0", "50", "max"):
        positions[target] = page.evaluate(CLEARANCE_AT_JS, target)
    receipts = {
        "inside zone": _synthetic_node_receipts(positions, "inside zone"),
        "below zone": _synthetic_node_receipts(positions, "below zone"),
        "under pill": _synthetic_node_receipts(positions, "under pill"),
    }
    _assert_synthetic_hit_rule(receipts)
    return {
        "ok": True,
        "positions": positions,
        "synthetic_hit_rule": receipts,
    }


def _rgb_token(color: str) -> tuple[int, int, int] | None:
    """Parse rgb/rgba() or #rrggbb (the --bg custom property) into 8-bit RGB."""
    if not color:
        return None
    token = color.strip()
    hex_match = re.fullmatch(r"#([0-9a-fA-F]{6})", token)
    if hex_match:
        raw = hex_match.group(1)
        return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))
    match = re.search(
        r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)", token)
    if not match:
        return None
    return (int(float(match.group(1))), int(float(match.group(2))),
            int(float(match.group(3))))


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def _declared_empty_cells() -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for empty_id in EMPTY_IDS:
        for theme in THEMES:
            for locale in LOCALES:
                for vw, vh in EMPTY_VIEWPORTS:
                    cells.append({
                        "family": "empty_states",
                        "force_state": empty_id,
                        "theme": theme,
                        "locale": locale,
                        "viewport": _viewport_name(vw),
                        "viewport_width": vw,
                        "viewport_height": vh,
                    })
    return cells


def _theme_locale_cells(family: str, widths: tuple[int, ...],
                        heights: dict[int, int] | None = None
                        ) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    height_of = heights or {1440: 900, 768: 1400, 390: 844}
    for theme in THEMES:
        for locale in LOCALES:
            for vw in widths:
                cells.append({
                    "family": family,
                    "theme": theme,
                    "locale": locale,
                    "viewport": _viewport_name(vw),
                    "viewport_width": vw,
                    "viewport_height": height_of[vw],
                })
    return cells


def _declared_force_state_cells() -> list[dict[str, Any]]:
    """Intended force-state photograph cells — not a cartesian of axes."""
    spec: list[tuple[str, int, int]] = [
        ("arrival", 1440, 900), ("arrival", 390, 844),
        ("dest_hover", 1440, 900),
        ("heading_focus", 1440, 900),
        ("rates", 1440, 900),
        ("money_central_banks", 1440, 900),
        ("inflation_foot", 1440, 900),
        ("scroll_max", 390, 844),
    ]
    cells: list[dict[str, Any]] = []
    for force_state, vw, vh in spec:
        for theme in THEMES:
            for locale in LOCALES:
                cells.append({
                    "family": "force_states",
                    "force_state": force_state,
                    "theme": theme,
                    "locale": locale,
                    "viewport": _viewport_name(vw),
                    "viewport_width": vw,
                    "viewport_height": vh,
                })
    return cells


def _declared_rest_view_cells() -> list[dict[str, Any]]:
    spec = (
        (1440, 900),
        (390, 844),
        (768, 1400),
    )
    return [
        {
            "family": "rest_views",
            "theme": theme,
            "locale": locale,
            "viewport": _viewport_name(vw),
            "viewport_width": vw,
            "viewport_height": vh,
        }
        for vw, vh in spec
        for theme in THEMES
        for locale in LOCALES
    ]


def _declared_families() -> dict[str, list[dict[str, Any]]]:
    return {
        "force_states": _declared_force_state_cells(),
        "empty_states": _declared_empty_cells(),
        "clearance": _theme_locale_cells("clearance", (390, 768, 1440)),
        "chip_opens_chat": _theme_locale_cells("chip_opens_chat", (390,)),
        "strip_void": _theme_locale_cells("strip_void", (1440,)),
        "rail_viewport": _theme_locale_cells("rail_viewport", (390, 768)),
        "e5": _theme_locale_cells("e5", (1440, 390)),
        "fab": _theme_locale_cells("fab", (1440,)),
        "rest_views": _declared_rest_view_cells(),
        "full_page": _theme_locale_cells("full_page", (1440,)),
        "movement_row": _theme_locale_cells("movement_row", (1440,)),
    }


def _declared_cell_key(cell: dict[str, Any]) -> tuple[Any, ...]:
    return (
        cell.get("family"),
        cell.get("force_state"),
        cell.get("theme"),
        cell.get("locale"),
        cell.get("viewport_width"),
    )


def _captured_declared_keys(
        states: list[dict[str, Any]],
        probes: dict[str, Any]) -> set[tuple[Any, ...]]:
    keys: set[tuple[Any, ...]] = set()
    for state in states:
        if not state.get("captured"):
            continue
        fs = state.get("force_state")
        if fs in EMPTY_IDS:
            keys.add(("empty_states", fs, state.get("theme"),
                      state.get("locale"), state.get("viewport_width")))
        elif fs:
            keys.add(("force_states", fs, state.get("theme"),
                      state.get("locale"), state.get("viewport_width")))
    for theme in THEMES:
        for locale in LOCALES:
            for vw in (390, 768, 1440):
                if probes.get(f"clearance_{vw}_{theme}_{locale}"):
                    keys.add(("clearance", None, theme, locale, vw))
            if probes.get(f"chip_opens_chat_390_{theme}_{locale}"):
                keys.add(("chip_opens_chat", None, theme, locale, 390))
            strip = (probes.get("strip_void_probes") or {}).get(
                f"{theme}_{locale}")
            if strip:
                keys.add(("strip_void", None, theme, locale, 1440))
            for vw in (390, 768):
                if probes.get(f"rail_viewport_{theme}_{locale}_{vw}"):
                    keys.add(("rail_viewport", None, theme, locale, vw))
            if probes.get(f"e5_timeout_{theme}_{locale}_1440"):
                keys.add(("e5", None, theme, locale, 1440))
            if probes.get(f"e5_timeout_{theme}_{locale}_390"):
                keys.add(("e5", None, theme, locale, 390))
            if probes.get(f"fab_display_1440_{theme}_{locale}"):
                keys.add(("fab", None, theme, locale, 1440))
    for state in states:
        if not state.get("captured"):
            continue
        theme = state.get("theme")
        locale = state.get("locale")
        vw = state.get("viewport_width")
        filename = str(state.get("file") or "")
        if state.get("full_page"):
            keys.add(("full_page", None, theme, locale, vw))
        if filename.startswith("movement-row-"):
            keys.add(("movement_row", None, theme, locale, vw))
        if filename in REST_FRAMES or (
                vw == 768 and not state.get("force_state")
                and not state.get("crop") and not state.get("full_page")
                and filename.endswith(".png") and "-max" not in filename):
            keys.add(("rest_views", None, theme, locale, vw))
    return keys


def _compute_gaps_from_declared(
        declared: dict[str, list[dict[str, Any]]],
        captured: set[tuple[Any, ...]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for family, cells in declared.items():
        for cell in cells:
            key = _declared_cell_key(cell)
            if key in captured:
                continue
            row = dict(cell)
            row["captured"] = False
            row["reason"] = cell.get("reason") or "declared cell was not captured"
            row.setdefault("family", family)
            gaps.append(row)
    return gaps


def _empty_filename(empty_id: str, theme: str, locale: str, vw: int) -> str:
    suffix = "" if locale == "en" else "-zh"
    if vw <= 390:
        return f"empty-{empty_id}-{theme}{suffix}-390.png"
    return f"empty-{empty_id}-{theme}{suffix}.png"


def _compute_gaps(declared: list[dict[str, Any]],
                  states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    captured: set[tuple[Any, ...]] = set()
    for state in states:
        if not state.get("captured"):
            continue
        captured.add((
            state.get("force_state"),
            state.get("theme"),
            state.get("locale"),
            state.get("viewport_width"),
        ))
    gaps: list[dict[str, Any]] = []
    for cell in declared:
        key = (
            cell.get("force_state"),
            cell.get("theme"),
            cell.get("locale"),
            cell.get("viewport_width"),
        )
        if key in captured:
            continue
        gaps.append({
            "captured": False,
            "force_state": cell.get("force_state"),
            "theme": cell.get("theme"),
            "locale": cell.get("locale"),
            "viewport": cell.get("viewport"),
            "viewport_width": cell.get("viewport_width"),
            "viewport_height": cell.get("viewport_height"),
            "reason": cell.get("reason") or "declared cell was not captured",
        })
    return gaps


def _device_px(origin: float, size: float, dpr: float) -> int:
    """Playwright device-pixel span: ceil((origin+size)×dpr) − floor(origin×dpr)."""
    return int(math.ceil((origin + size) * dpr) - math.floor(origin * dpr))


def _assert_shot_geometry(dest: Path, extra: dict[str, Any],
                          vw: int, vh: int) -> None:
    dpr = extra.get("dpr")
    if dpr is None:
        raise RuntimeError(f"{dest.name}: missing dpr")
    w, h = _png_size(dest)
    scale = float(dpr)
    if extra.get("crop"):
        span = extra.get("device_px_span")
        if span:
            exp_w = int(span["x1"]) - int(span["x0"])
            exp_h = int(span["y1"]) - int(span["y0"])
            if (w, h) != (exp_w, exp_h):
                raise RuntimeError(
                    f"{dest.name}: crop IHDR {w}x{h} != device_px_span "
                    f"{exp_w}x{exp_h} span={span} dpr={dpr}")
        else:
            box = extra.get("crop_box") or {}
            exp_w = _device_px(float(box.get("x") or 0),
                               float(box.get("width") or 0), scale)
            exp_h = _device_px(float(box.get("y") or 0),
                               float(box.get("height") or 0), scale)
            if (w, h) != (exp_w, exp_h):
                raise RuntimeError(
                    f"{dest.name}: crop IHDR {w}x{h} != crop_box×dpr {exp_w}x{exp_h} "
                    f"box={box} dpr={dpr}")
        if not extra.get("crop_selector"):
            raise RuntimeError(f"{dest.name}: crop:true missing crop_selector")
    elif extra.get("full_page"):
        exp_w = _device_px(0.0, float(vw), scale)
        if w != exp_w:
            raise RuntimeError(
                f"{dest.name}: full_page IHDR width {w} != {vw}×{dpr}={exp_w}")
    else:
        exp_w = _device_px(0.0, float(vw), scale)
        exp_h = _device_px(0.0, float(vh), scale)
        if (w, h) != (exp_w, exp_h):
            raise RuntimeError(
                f"{dest.name}: viewport IHDR {w}x{h} != {vw}x{vh}×{dpr} "
                f"({exp_w}x{exp_h})")


def _measure_dpr(page) -> float:
    return float(page.evaluate("window.devicePixelRatio"))


def _crop_box(locator) -> dict[str, float]:
    box = locator.bounding_box()
    if not box:
        raise RuntimeError("crop locator has no box")
    return {
        "x": box["x"], "y": box["y"],
        "width": box["width"], "height": box["height"],
    }


def _boxes_moved(before: dict[str, float], after: dict[str, float],
                 tol: float = 0.5) -> bool:
    return any(
        abs(float(before[key]) - float(after[key])) > tol
        for key in ("x", "y", "width", "height")
    )


def _empty_headline(empty_id: str, locale: str) -> str:
    from lib import macro_suite_labels as labels
    title = labels.EMPTY_STATES[empty_id]["title"]
    return str(title[locale])


def _device_px_span(box: dict[str, float], dpr: float) -> dict[str, int]:
    scale = float(dpr)
    x0 = int(math.floor(float(box["x"]) * scale))
    y0 = int(math.floor(float(box["y"]) * scale))
    x1 = int(math.ceil((float(box["x"]) + float(box["width"])) * scale))
    y1 = int(math.ceil((float(box["y"]) + float(box["height"])) * scale))
    return {"x0": x0, "x1": x1, "y0": y0, "y1": y1}


def _write_element_shot(page, dest: Path, locator, extra: dict[str, Any],
                        locale: str) -> None:
    """BLOCKER-1: Playwright element screenshot, never a full-page crop."""
    locator.scroll_into_view_if_needed()
    page.wait_for_timeout(80)
    box_before = _crop_box(locator)
    scroll_before = _read_scroll(page)
    text = str(locator.inner_text() or "")
    locator.screenshot(path=str(dest), type="png")
    box_after = _crop_box(locator)
    scroll_after = _read_scroll(page)
    # Playwright may scroll internally to shoot an element taller than
    # the viewport. Compare DOCUMENT boxes so a scroll is not a move.
    doc_before = {
        "x": box_before["x"],
        "y": box_before["y"] + scroll_before,
        "width": box_before["width"],
        "height": box_before["height"],
    }
    doc_after = {
        "x": box_after["x"],
        "y": box_after["y"] + scroll_after,
        "width": box_after["width"],
        "height": box_after["height"],
    }
    if _boxes_moved(doc_before, doc_after):
        raise RuntimeError(
            f"{dest.name}: element box moved during shot "
            f"{doc_before} -> {doc_after}")
    scroll_y = scroll_before
    extra["crop_box"] = box_before
    extra["crop_box_doc"] = {
        "x": box_before["x"],
        "y": box_before["y"] + scroll_y,
        "width": box_before["width"],
        "height": box_before["height"],
    }
    extra["scroll_y_at_shot"] = scroll_y
    extra["element_text_head"] = text.replace("\n", " ").strip()[:80]
    width, height = _png_size(dest)
    origin = _device_px_span(box_before, extra["dpr"])
    extra["device_px_span"] = {
        "x0": origin["x0"],
        "x1": origin["x0"] + width,
        "y0": origin["y0"],
        "y1": origin["y0"] + height,
    }
    selector = str(extra.get("crop_selector") or "")
    match = re.search(r'data-mc-empty=["\'](e[1-6])["\']', selector)
    if match:
        empty_id = match.group(1)
        headline = _empty_headline(empty_id, locale)
        if headline not in text:
            raise RuntimeError(
                f"{dest.name}: data-mc-empty={empty_id} innerText missing "
                f"{headline!r}: {text[:160]!r}")


def _write_shot(page, dest: Path, extra: dict[str, Any], vw: int, vh: int, *,
                crop_locator=None, crop_selector: str | None = None,
                full_page: bool = False,
                locale: str | None = None) -> dict[str, Any]:
    extra = dict(extra)
    extra["dpr"] = _measure_dpr(page)
    extra.setdefault("fixture", "builder-payload")
    if extra.get("fixture") is None:
        extra["fixture"] = "builder-payload"
    if locale:
        extra["locale"] = locale
    if crop_locator is not None:
        extra["crop"] = True
        extra["full_page"] = False
        extra["crop_selector"] = crop_selector
        _write_element_shot(
            page, dest, crop_locator, extra,
            locale=str(extra.get("locale") or locale or "en"))
    elif full_page:
        extra["crop"] = False
        extra["full_page"] = True
        page.screenshot(path=str(dest), type="png", full_page=True)
    else:
        extra["crop"] = False
        extra["full_page"] = False
        page.screenshot(path=str(dest), type="png", full_page=False)
    _assert_png(dest)
    _assert_shot_geometry(dest, extra, vw, vh)
    return extra


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _head_sha() -> str:
    out = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True)
    return out.strip()


def _git_status_short(*paths: str) -> str:
    cmd = ["git", "status", "--short"]
    if paths:
        cmd += ["--", *paths]
    return subprocess.check_output(cmd, cwd=ROOT, text=True)


def _require_clean_tree(*, when: str, paths: tuple[str, ...] = ()) -> dict[str, Any]:
    """Run `git status --short` (optionally scoped) and abort if dirty.

    r10-M1: the manifest must not claim a clean-tree check the script
    never ran. Start of run = whole tree. End of run = templates /
    scripts / lib (the capture writes evidence under mockups/).
    """
    status = _git_status_short(*paths)
    head = _head_sha()
    clean = status.strip() == ""
    measured = {
        "when": when,
        "status": status,
        "clean": clean,
        "head": head,
        "paths": list(paths),
    }
    if not clean:
        scope = " ".join(paths) if paths else "(whole tree)"
        raise RuntimeError(
            f"capture refused: dirty worktree at {when} {scope}:\n{status}")
    return measured


def _assert_head_unmoved(head_start: str) -> str:
    head_end = _head_sha()
    if head_end != head_start:
        raise RuntimeError(
            f"capture refused: HEAD moved during the run "
            f"{head_start} -> {head_end}")
    return head_end


def _derive_resolved_sha_source(protocol: dict[str, Any]) -> str:
    """Every sentence is derived from measured protocol fields."""
    return (
        f"committed HEAD of this worktree ({protocol['head_start']}); "
        f"tree_clean_start={protocol['tree_clean_start']} from "
        f"`git status --short` at start "
        f"(empty={protocol['tree_clean_start']}); "
        f"tree_clean_end={protocol['tree_clean_end']} from "
        f"`git status --short -- templates scripts lib` at end "
        f"(empty={protocol['tree_clean_end']}); "
        f"head_start={protocol['head_start']}; "
        f"head_end={protocol['head_end']}; "
        f"generated_at_start={protocol['generated_at_start']}; "
        f"generated_at_end={protocol['generated_at_end']}; "
        f"commit_time_of_capture_sha={protocol['commit_time_of_capture_sha']} "
        f"(git show -s --format=%cI). "
        f"Every composition, state and empty frame was recaptured in this run "
        f"(R6-B1). E5 is photographed by stalling the fragment request until "
        f"the 8000 ms client timeout clones template[data-mc-empty-e5]."
    )


def _commit_iso(sha: str) -> str:
    return subprocess.check_output(
        ["git", "show", "-s", "--format=%cI", sha], cwd=ROOT, text=True
    ).strip()


def _read_scroll(page) -> float:
    return float(page.evaluate(
        "window.scrollY || document.documentElement.scrollTop || 0"))


def _settle_scroll(page, mode: str) -> float:
    """Hold the page at scroll 0 or max. Hash navigation to #overview
    otherwise leaves the rail pinned (R9-M1)."""
    if mode == "max":
        page.evaluate(
            "window.scrollTo(0, document.documentElement.scrollHeight)")
    else:
        page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(200)
    reached = _read_scroll(page)
    if mode == "0" and abs(reached) >= 2:
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(200)
        reached = _read_scroll(page)
        if abs(reached) >= 2:
            raise RuntimeError(f"failed to hold scroll 0: {reached}")
    return reached


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _serve(root: Path, port: int | None = None) -> tuple[subprocess.Popen, str]:
    """Threaded static server. The stdlib ``-m http.server`` is single-thread
    and has died mid-E5 (CONNECTION_REFUSED) on two recapture runs."""
    if port is None:
        port = _free_port()
    code = (
        "from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler\n"
        "import os\n"
        "class H(SimpleHTTPRequestHandler):\n"
        "    def handle(self):\n"
        "        try:\n"
        "            super().handle()\n"
        "        except (BrokenPipeError, ConnectionResetError):\n"
        "            pass\n"
        "    def log_message(self, *args):\n"
        "        pass\n"
        f"os.chdir({str(root.resolve())!r})\n"
        f"ThreadingHTTPServer(('127.0.0.1', {int(port)}), H).serve_forever()\n"
    )
    log = Path(os.environ.get("TMPDIR", "/tmp")) / f"mc-p3-http-{port}.log"
    proc = subprocess.Popen(
        [sys.executable, "-c", code],
        stdout=subprocess.DEVNULL,
        stderr=log.open("w"),
        start_new_session=True)
    print(
        f"http.server pid={proc.pid} cwd={root} port={port} threaded",
        flush=True)
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                break
        except OSError:
            if proc.poll() is not None:
                tail = log.read_text(encoding="utf-8", errors="replace")[-400:]
                raise RuntimeError(
                    f"http.server exited {proc.returncode}: {tail}")
            time.sleep(0.1)
    else:
        raise RuntimeError(f"http.server did not bind :{port}")
    return proc, f"http://127.0.0.1:{port}"


def _origin_port(origin: str) -> int:
    return int(origin.rsplit(":", 1)[-1])


def _origin_alive(origin: str) -> bool:
    port = _origin_port(origin)
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def _ensure_origin(origin: str, root: Path,
                   servers: list) -> None:
    if _origin_alive(origin):
        return
    proc, _ = _serve(root, port=_origin_port(origin))
    servers.append(proc)


def _kill(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def _copy_chrome(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name in ASSETS:
        tmpl = ROOT / "templates" / name
        src = tmpl if tmpl.exists() else SITE / name
        if src.exists():
            shutil.copy2(src, out / name)


def _new_context(browser, theme: str, locale: str, width: int, height: int):
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
    return context


def _wait_theme(page, theme: str, locale: str) -> None:
    page.wait_for_function(
        """([theme, locale]) => {
            const el = document.documentElement;
            return el.getAttribute('data-theme') === theme
                && (el.getAttribute('data-lang') || 'en') === locale;
        }""",
        arg=[theme, locale],
        timeout=15000,
    )


def _wait_hash_ready(page, hash_path: str) -> None:
    """Money figures live in a fetched fragment — wait for a real row
    on the *visible* tab (a hidden sibling's `.mc-move` is not enough).

    E4 withholds the destination tab, so the visible thing is the typed
    empty, not a movement row. Accept either.
    """
    if not hash_path.startswith("#money"):
        return
    page.wait_for_selector(
        "#money [data-mc-figure], #money [data-mc-empty]",
        timeout=15000,
    )
    tab = "central_banks" if "/central_banks" in hash_path else "liquidity"
    page.wait_for_selector(
        f"#{tab} .mc-move-row, #{tab} .mc-move-current-only, "
        f"#money [data-mc-empty], #{tab} [data-mc-empty]",
        state="visible",
        timeout=15000,
    )


def _open_direct(context, url: str, hash_path: str, theme: str, locale: str):
    page = context.new_page()
    page.goto(url + hash_path, wait_until="domcontentloaded", timeout=30000)
    _wait_theme(page, theme, locale)
    _wait_hash_ready(page, hash_path)
    return page


def _open_iframe(context, origin: str, hash_path: str, theme: str, locale: str,
                 width: int, height: int):
    """390/768 capture through a same-width iframe (Chrome CLI clamps
    ``--window-size`` below ~500). Playwright's viewport is already the
    target width; the iframe is the house crop so the PNG is the iframe
    box, not a clamped desktop window. Theme/lang are waited on the
    INNER document, never the wrapper."""
    page = context.new_page()
    src = origin + "/macro_monetary.html" + hash_path
    page.set_content(
        "<!doctype html><html><head><meta charset='utf-8'></head>"
        f"<body style='margin:0;background:transparent'>"
        f"<iframe id='f' src='{src}' "
        f"style='width:{width}px;height:{height}px;border:0;display:block'>"
        "</iframe></body></html>",
        wait_until="domcontentloaded",
    )
    page.wait_for_selector("iframe#f", timeout=15000)
    inner = None
    deadline = time.time() + 15
    while time.time() < deadline:
        for frame in page.frames:
            if "macro_monetary.html" in (frame.url or ""):
                inner = frame
                break
        if inner is not None:
            break
        page.wait_for_timeout(100)
    if inner is None:
        raise RuntimeError(
            "iframe never loaded macro_monetary.html; "
            f"frames={[frame.url for frame in page.frames]}")
    inner.wait_for_load_state("domcontentloaded")
    _wait_theme(inner, theme, locale)
    inner.wait_for_selector(".mc-shell", timeout=15000)
    return page, inner


def _viewport_name(vw: int) -> str:
    if vw <= 390:
        return "mobile"
    if vw <= 768:
        return "tablet"
    return "desktop"


def _force_state_for(filename: str, extra: dict[str, Any] | None) -> str | None:
    if extra and "force_state" in extra:
        return extra["force_state"]
    if filename in REST_FRAMES:
        return None
    named = {
        "17-dark-en-1440-arrival.png": "arrival",
        "18-light-en-1440-arrival.png": "arrival",
        "30-dark-zh-1440-arrival.png": "arrival",
        "31-light-zh-1440-arrival.png": "arrival",
        "36-dark-en-390-arrival.png": "arrival",
        "37-dark-zh-390-arrival.png": "arrival",
        "38-light-en-390-arrival.png": "arrival",
        "39-light-zh-390-arrival.png": "arrival",
        "19-dark-en-1440-dest-hover.png": "dest_hover",
        "20-light-en-1440-dest-hover.png": "dest_hover",
        "32-dark-zh-1440-dest-hover.png": "dest_hover",
        "33-light-zh-1440-dest-hover.png": "dest_hover",
        "21-dark-en-1440-heading-focus.png": "heading_focus",
        "22-light-en-1440-heading-focus.png": "heading_focus",
        "34-dark-zh-1440-heading-focus.png": "heading_focus",
        "35-light-zh-1440-heading-focus.png": "heading_focus",
        "28-dark-zh-768.png": None,
        "29-light-zh-768.png": None,
        "05-dark-en-1440-rates.png": "rates",
        "06-dark-zh-1440-rates.png": "rates",
        "07-light-en-1440-rates.png": "rates",
        "08-light-zh-1440-rates.png": "rates",
        "44-dark-en-390-max.png": "scroll_max",
        "45-dark-zh-390-max.png": "scroll_max",
        "46-light-en-390-max.png": "scroll_max",
        "47-light-zh-390-max.png": "scroll_max",
        "23-dark-en-1440-money-central-banks.png": "money_central_banks",
        "48-dark-zh-1440-money-central-banks.png": "money_central_banks",
        "49-light-zh-1440-money-central-banks.png": "money_central_banks",
        "24-dark-en-1440-inflation-foot.png": "inflation_foot",
        "55-light-en-1440-inflation-foot.png": "inflation_foot",
        "56-dark-zh-1440-inflation-foot.png": "inflation_foot",
        "57-light-zh-1440-inflation-foot.png": "inflation_foot",
        "25-dark-en-1440-e3.png": "e3",
        "26-light-en-1440-e3.png": "e3",
        "40-dark-zh-1440-e3.png": "e3",
        "41-light-zh-1440-e3.png": "e3",
        "27-light-en-1440-money-central-banks.png": "money_central_banks",
    }
    if filename in named:
        return named[filename]
    empty = filename.startswith("empty-e")
    if empty:
        # empty-e1-dark.png → e1
        parts = filename.split("-")
        if len(parts) >= 2 and parts[1].startswith("e"):
            return parts[1]
    return None


def _row(filename: str, dest: Path, theme: str, locale: str,
         vw: int, vh: int, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    w, h = _png_size(dest)
    extra = dict(extra or {})
    force_state = _force_state_for(filename, extra)
    extra.pop("force_state", None)
    extra.pop("locale", None)
    fixture = extra.pop("fixture", "builder-payload")
    if fixture is None:
        fixture = "builder-payload"
    row = {
        "access": "anonymous",
        "applied_locale": locale,
        "applied_theme": theme,
        "bytes": dest.stat().st_size,
        "captured": True,
        "crop": extra.pop("crop", False),
        "dpr": extra.pop("dpr", None),
        "file": filename,
        "fixture": fixture,
        "force_state": force_state,
        "full_page": extra.pop("full_page", False),
        "height": h,
        "locale": locale,
        "reduced_motion": True,
        "scroll_y": extra.pop("scroll_y", 0),
        "sha256": _sha(dest),
        "theme": theme,
        "viewport": _viewport_name(vw),
        "viewport_height": vh,
        "viewport_width": vw,
        "width": w,
    }
    row.update(extra)
    return row


def _upsert(manifest: dict[str, Any], filename: str, row: dict[str, Any]) -> None:
    states = manifest["pages"][0]["states"]
    for i, state in enumerate(states):
        if state.get("file") == filename:
            states[i] = row
            return
        if filename == "empty-e5-dark.png" and (
                state.get("force_state") in ("e5", "addendum:empty-e5-dark.png")
                and not state.get("captured")):
            states[i] = row
            return
    states.append(row)


def _assert_png(path: Path) -> None:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or b"IEND" not in data:
        raise RuntimeError(f"{path.name} is not a finished PNG")


def _live_entries():
    from scripts import build_macro_suite_pages as builder
    entries = []
    for page in builder.SUITE_PAGES:
        identity = builder._identity(page)
        snapshot, _ = builder.read_workspace(DATA, page)
        entries.append({
            "workspace_id": page.workspace_id,
            "region": page.region,
            "output": page.output,
            "title": identity["title"],
            "subtitle": identity["subtitle"],
            "snapshot": snapshot,
            "failure": None,
        })
    return entries


def _build_e3_overview(tmp: Path) -> Path:
    from scripts import build_macro_suite_pages as builder
    out = tmp / "site-e3-overview"
    out.mkdir(parents=True, exist_ok=True)
    _copy_chrome(out)
    entries = _live_entries()
    for entry in entries:
        snap = entry.get("snapshot")
        if isinstance(snap, dict) and isinstance(snap.get("changes"), dict):
            snap["changes"]["deltas"] = []
            snap["changes"]["comparability"] = "NO_PRIOR"
    env = builder._environment(ROOT)
    builder.build_hub(entries, out_dir=out, env=env, root=ROOT,
                      page_built_at="2026-09-06T00:00:00Z")
    for asset in builder.SHARED_ASSETS:
        shutil.copy2(ROOT / "templates" / asset, out / asset)
    html = (out / "macro_monetary.html").read_text(encoding="utf-8")
    if 'data-mc-empty="e3"' not in html:
        raise RuntimeError("overview E3 fixture did not emit the empty slot")
    return out


def _remanifest(data_root: Path, workspace_id: str, mutate) -> None:
    rel = data_root / "workspaces" / workspace_id / "US" / "latest.json"
    snap = json.loads(rel.read_text(encoding="utf-8"))
    mutate(snap)
    from engine.market_os.macro_workspaces import contract as workspace_contract
    sealed = workspace_contract.finalize(snap)
    raw = json.dumps(sealed, ensure_ascii=False).encode("utf-8")
    rel.write_bytes(raw)
    manifest_path = data_root / "workspaces" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    key = f"{workspace_id}/US"
    manifest["workspaces"][key]["content_sha256"] = sealed["generation"]["content_sha256"]
    manifest["workspaces"][key]["bytes"] = len(raw)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def _build_json_empty(tmp: Path, empty_id: str, mutate) -> Path:
    from scripts import build_macro_suite_pages as builder
    data_root = tmp / f"data-{empty_id}"
    out = tmp / f"site-{empty_id}"
    shutil.copytree(DATA, data_root)
    _remanifest(data_root, "inflation_system", mutate)
    builder.render(ROOT, data_root=data_root, out_dir=out,
                   page_built_at="2026-09-06T00:00:00Z")
    _copy_chrome(out)
    frag = (out / "macro" / "fragments" / "inflation.html").read_text(encoding="utf-8")
    if f'data-mc-empty="{empty_id}"' not in frag:
        raise RuntimeError(f"{empty_id} missing from fragment")
    return out


def _build_flag_empty(tmp: Path, fixture_name: str, empty_id: str, frag: str) -> Path:
    from scripts import build_macro_suite_pages as builder
    out = tmp / f"site-{empty_id}"
    builder.render(
        ROOT, data_root=DATA, out_dir=out,
        page_built_at="2026-09-06T00:00:00Z",
        empty_state_fixture=FIXTURES / fixture_name,
    )
    _copy_chrome(out)
    body = (out / "macro" / "fragments" / frag).read_text(encoding="utf-8")
    if f'data-mc-empty="{empty_id}"' not in body:
        raise RuntimeError(f"{empty_id} missing after --empty-state-fixture")
    return out


def _build_mutated_hub(tmp: Path, tag: str, mutate, *,
                       allow_fixture: bool = False) -> Path:
    from scripts import build_macro_suite_pages as builder
    out = tmp / f"site-{tag}"
    out.mkdir(parents=True, exist_ok=True)
    _copy_chrome(out)
    entries = _live_entries()
    mutate(entries)
    env = builder._environment(ROOT)
    builder.build_hub(
        entries, out_dir=out, env=env, root=ROOT,
        page_built_at="2026-09-06T00:00:00Z",
        allow_empty_state_fixture=allow_fixture)
    for asset in builder.SHARED_ASSETS:
        shutil.copy2(ROOT / "templates" / asset, out / asset)
    return out


def _mutate_inflation_e1(entries) -> None:
    for entry in entries:
        if entry.get("workspace_id") != "inflation_system":
            continue
        snap = entry.get("snapshot")
        if not isinstance(snap, dict):
            continue
        headline = snap.setdefault("headline", {})
        headline["effective_date"] = None
        headline["status"] = "ABSENT"
        headline["null_reason"] = "NOT_YET_RELEASED"
        changes = snap.setdefault("changes", {})
        changes["deltas"] = []
        changes["comparability"] = "NO_PRIOR"
        changes["status"] = "ABSENT"
        changes["null_reason"] = "INSUFFICIENT_HISTORY"


def _mutate_inflation_e3(entries) -> None:
    for entry in entries:
        if entry.get("workspace_id") != "inflation_system":
            continue
        snap = entry.get("snapshot")
        if not isinstance(snap, dict):
            continue
        changes = snap.setdefault("changes", {})
        changes["deltas"] = []
        changes["comparability"] = "NO_PRIOR"
        changes["status"] = "ABSENT"
        changes["null_reason"] = "INSUFFICIENT_HISTORY"


def _capture_e5_cells(browser, origin: str, probes: dict[str, Any],
                      manifest: dict[str, Any], *, site_root: Path,
                      servers: list) -> None:
    """Photograph E5 by stalling the fragment request (no product change)."""
    for theme in THEMES:
        for locale in LOCALES:
            for vw, vh in EMPTY_VIEWPORTS:
                filename = _empty_filename("e5", theme, locale, vw)
                dest = EVIDENCE / filename
                print(
                    f"capturing {filename} (e5 timeout {theme} {locale} {vw})",
                    flush=True)
                _ensure_origin(origin, site_root, servers)
                context = _new_context(browser, theme, locale, vw, vh)
                held: list = []
                try:
                    page = context.new_page()
                    seen: dict[str, float] = {}

                    def _stall(route) -> None:
                        if "requestSeenAt" not in seen:
                            seen["requestSeenAt"] = time.monotonic()
                        # Hold the request (never fulfil) so the product
                        # 8000ms timeout clones the template. Abort after
                        # the clone is photographed so Playwright's route
                        # task can finish — a never-returning handler
                        # leaked pending tasks and killed later cells.
                        held.append(route)

                    page.route("**/macro/fragments/**", _stall)
                    page.goto(
                        origin + "/macro_monetary.html#inflation",
                        wait_until="domcontentloaded", timeout=30000)
                    _wait_theme(page, theme, locale)
                    deadline = time.monotonic() + 20.0
                    clone_seen_at: float | None = None
                    while time.monotonic() < deadline:
                        if page.query_selector('[data-mc-empty="e5"]'):
                            clone_seen_at = time.monotonic()
                            break
                        page.wait_for_timeout(100)
                    if clone_seen_at is None:
                        raise RuntimeError(
                            f"E5 clone missing {theme}/{locale}/{vw}")
                    request_seen_at = seen.get("requestSeenAt")
                    if request_seen_at is None:
                        raise RuntimeError(
                            f"E5 fragment request never seen "
                            f"{theme}/{locale}/{vw}")
                    request_seen_at_ms = request_seen_at * 1000
                    clone_seen_at_ms = clone_seen_at * 1000
                    elapsed_ms = clone_seen_at_ms - request_seen_at_ms
                    receipt = page.evaluate("""() => {
                      const tpl = document.querySelector(
                        'template[data-mc-empty-e5]');
                      const clone = document.querySelector(
                        '[data-mc-empty="e5"]');
                      const title = clone
                        ? (clone.querySelector('.mc-empty-title') || clone)
                        : null;
                      return {
                        templatePresent: Boolean(tpl),
                        clonePresent: Boolean(clone),
                        headline: title
                          ? String(title.innerText || '').trim() : '',
                      };
                    }""")
                    if elapsed_ms < 8000:
                        raise RuntimeError(
                            f"E5 elapsedMs {elapsed_ms:.0f} < 8000 "
                            f"{theme}/{locale}/{vw}")
                    if not receipt.get("clonePresent"):
                        raise RuntimeError(
                            f"E5 clone missing {theme}/{locale}/{vw}: {receipt}")
                    probes[f"e5_timeout_{theme}_{locale}_{vw}"] = {
                        "elapsedMs": elapsed_ms,
                        "requestSeenAtMs": request_seen_at_ms,
                        "cloneSeenAtMs": clone_seen_at_ms,
                        "templatePresent": receipt.get("templatePresent"),
                        "clonePresent": receipt.get("clonePresent"),
                        "headline": receipt.get("headline"),
                    }
                    extra = {
                        "force_state": "e5",
                        "fixture": "builder-payload",
                        "trigger": (
                            "page.route never-fulfils macro/fragments/*; "
                            "8000ms client timeout cloned template"
                        ),
                        "scroll_y": _read_scroll(page),
                    }
                    extra = _write_shot(
                        page, dest, extra, vw, vh,
                        crop_locator=page.locator('[data-mc-empty="e5"]').first,
                        crop_selector='[data-mc-empty="e5"]',
                        locale=locale)
                    _upsert(manifest, filename, _row(
                        filename, dest, theme, locale, vw, vh, extra))
                    print(
                        f"  {filename} {dest.stat().st_size}B {_sha(dest)[:12]} "
                        f"elapsedMs={elapsed_ms:.0f}",
                        flush=True)
                finally:
                    for route in held:
                        try:
                            route.abort("timedout")
                        except Exception:
                            pass
                    context.close()


def _capture_empty_states(browser, tmp: Path, servers: list, manifest: dict) -> None:
    """Recapture every empty-state crop from a fixture build (R6-B1)."""
    from scripts import build_macro_suite_pages as builder

    e3_overview = _build_e3_overview(tmp)
    e1_site = _build_mutated_hub(tmp, "e1", _mutate_inflation_e1)
    e3_site = _build_mutated_hub(tmp, "e3-inflation", _mutate_inflation_e3)
    e4_site = _build_flag_empty(tmp, "e4_central_banks.json", "e4", "money.html")
    e6_site = _build_flag_empty(tmp, "e6_inflation_system.json", "e6", "inflation.html")

    empty_shots = [
        # filename, theme, site, hash, selector, extra
        ("25-dark-en-1440-e3.png", "dark", e3_overview, "#overview",
         "#overview", {
             "fixture": "builder-payload",
             "trigger": "Overview figure slot empty; directory untouched",
             "force_state": "e3",
         }),
        ("26-light-en-1440-e3.png", "light", e3_overview, "#overview",
         "#overview", {
             "fixture": "builder-payload",
             "trigger": "Overview figure slot empty; directory untouched",
             "force_state": "e3",
         }),
        ("empty-e1-dark.png", "dark", e1_site, "#inflation",
         "#inflation [data-mc-empty='e1']", {
             "fixture": "builder-payload",
             "trigger": "Contract-legal inflation_system JSON: no date, no deltas → E1",
             "force_state": "e1",
         }),
        ("empty-e1-light.png", "light", e1_site, "#inflation",
         "#inflation [data-mc-empty='e1']", {
             "fixture": "builder-payload",
             "trigger": "Contract-legal inflation_system JSON: no date, no deltas → E1",
             "force_state": "e1",
         }),
        ("empty-e2-dark.png", "dark", SITE, "#rates",
         "#rates [data-mc-empty='e2']", {
             "fixture": "builder-payload",
             "trigger": "Live #rates workspace context.state is SOURCE_FAILED / STALE_SOURCE",
             "force_state": "e2",
         }),
        ("empty-e2-light.png", "light", SITE, "#rates",
         "#rates [data-mc-empty='e2']", {
             "fixture": "builder-payload",
             "trigger": "Live #rates workspace context.state is SOURCE_FAILED / STALE_SOURCE",
             "force_state": "e2",
         }),
        ("empty-e3-dark.png", "dark", e3_site, "#inflation",
         "#inflation [data-mc-empty='e3']", {
             "fixture": "builder-payload",
             "trigger": "Contract-legal inflation_system JSON: dated, no comparable deltas → E3",
             "force_state": "e3",
         }),
        ("empty-e3-light.png", "light", e3_site, "#inflation",
         "#inflation [data-mc-empty='e3']", {
             "fixture": "builder-payload",
             "trigger": "Contract-legal inflation_system JSON: dated, no comparable deltas → E3",
             "force_state": "e3",
         }),
        ("empty-e4-dark.png", "dark", e4_site, "#money/central_banks",
         "#money [data-mc-empty='e4']", {
             "fixture": "fixtures/e4_central_banks.json",
             "trigger": " --empty-state-fixture e4_central_banks.json → withheld_command_tabs",
             "force_state": "e4",
         }),
        ("empty-e4-light.png", "light", e4_site, "#money/central_banks",
         "#money [data-mc-empty='e4']", {
             "fixture": "fixtures/e4_central_banks.json",
             "trigger": " --empty-state-fixture e4_central_banks.json → withheld_command_tabs",
             "force_state": "e4",
         }),
        ("empty-e6-dark.png", "dark", e6_site, "#inflation",
         "#inflation [data-mc-empty='e6']", {
             "fixture": "fixtures/e6_inflation_system.json",
             "trigger": "--empty-state-fixture e6_inflation_system.json → entitlement=Research",
             "force_state": "e6",
         }),
        ("empty-e6-light.png", "light", e6_site, "#inflation",
         "#inflation [data-mc-empty='e6']", {
             "fixture": "fixtures/e6_inflation_system.json",
             "trigger": "--empty-state-fixture e6_inflation_system.json → entitlement=Research",
             "force_state": "e6",
         }),
    ]
    zh_shots = []
    for filename, theme, site, hash_path, selector, extra in empty_shots:
        if filename.startswith("empty-"):
            zh_name = filename.replace(".png", "-zh.png")
        elif filename == "25-dark-en-1440-e3.png":
            zh_name = "40-dark-zh-1440-e3.png"
        elif filename == "26-light-en-1440-e3.png":
            zh_name = "41-light-zh-1440-e3.png"
        else:
            continue
        zh_shots.append((zh_name, theme, site, hash_path, selector, extra, "zh"))
    empty_shots = [
        (*shot, "en") for shot in empty_shots
    ] + zh_shots

    served: dict[str, tuple] = {}
    try:
        for filename, theme, site, hash_path, selector, extra, locale in empty_shots:
            dest = EVIDENCE / filename
            print(f"capturing {filename} (empty {extra.get('force_state')} {locale})", flush=True)
            key = str(site)
            if key not in served:
                proc, origin = _serve(site)
                servers.append(proc)
                served[key] = (proc, origin)
            _origin = served[key][1]
            context = _new_context(browser, theme, locale, 1440, 900)
            try:
                page = _open_direct(
                    context, _origin + "/macro_monetary.html",
                    hash_path, theme, locale)
                page.wait_for_selector(selector, timeout=15000)
                extra = dict(extra)
                extra.setdefault("fixture", extra.get("fixture") or "builder-payload")
                extra["scroll_y"] = _read_scroll(page)
                extra = _write_shot(
                    page, dest, extra, 1440, 900,
                    crop_locator=page.locator(selector).first,
                    crop_selector=selector,
                    locale=locale)
                _upsert(manifest, filename, _row(
                    filename, dest, theme, locale, 1440, 900, extra))
                print(f"  {filename} {dest.stat().st_size}B {_sha(dest)[:12]}", flush=True)
            finally:
                context.close()
        # Same empty cells at 390 (E-M2).
        for filename, theme, site, hash_path, selector, extra, locale in empty_shots:
            if not filename.startswith("empty-"):
                continue
            mobile_name = filename.replace(".png", "-390.png")
            dest = EVIDENCE / mobile_name
            print(f"capturing {mobile_name} (empty {extra.get('force_state')} {locale} 390)", flush=True)
            key = str(site)
            _origin = served[key][1]
            context = _new_context(browser, theme, locale, 390, 844)
            try:
                page = _open_direct(
                    context, _origin + "/macro_monetary.html",
                    hash_path, theme, locale)
                page.wait_for_selector(selector, timeout=15000)
                extra390 = dict(extra)
                extra390.setdefault("fixture", extra.get("fixture") or "builder-payload")
                extra390["scroll_y"] = _read_scroll(page)
                extra390 = _write_shot(
                    page, dest, extra390, 390, 844,
                    crop_locator=page.locator(selector).first,
                    crop_selector=selector,
                    locale=locale)
                _upsert(manifest, mobile_name, _row(
                    mobile_name, dest, theme, locale, 390, 844, extra390))
                print(f"  {mobile_name} {dest.stat().st_size}B {_sha(dest)[:12]}", flush=True)
            finally:
                context.close()
    finally:
        for proc, _origin in served.values():
            _kill(proc)
            if proc in servers:
                servers.remove(proc)
    del builder


def main() -> int:
    from playwright.sync_api import sync_playwright

    tmp = Path(os.environ.get("TMPDIR", "/tmp")) / f"mc-p3-r3-{os.getpid()}"
    tmp.mkdir(parents=True, exist_ok=True)
    servers: list[subprocess.Popen] = []
    start_tree = _require_clean_tree(when="start")
    generated_at_start = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    head = start_tree["head"]
    probes: dict[str, Any] = {}
    if PROBES.exists():
        probes = json.loads(PROBES.read_text(encoding="utf-8"))
    # r10 evidence m2: viewport-less clearance_* aliases were byte
    # duplicates of clearance_390_*. One key per cell.
    for alias in (
        "clearance_dark_en", "clearance_dark_zh",
        "clearance_light_en", "clearance_light_zh",
        "strip_void_probe",
    ):
        probes.pop(alias, None)
    for theme in THEMES:
        for locale in LOCALES:
            for vw in (390, 768):
                probes.pop(f"rail_clip_{theme}_{locale}_{vw}", None)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    try:
        shots = [
            # filename, theme, locale, w, h, hash, kind, extra
            ("01-dark-en-1440.png", "dark", "en", 1440, 900, "#overview", "viewport", None),
            ("02-dark-zh-1440.png", "dark", "zh", 1440, 900, "#overview", "viewport", None),
            ("03-light-en-1440.png", "light", "en", 1440, 900, "#overview", "viewport", None),
            ("04-light-zh-1440.png", "light", "zh", 1440, 900, "#overview", "viewport", None),
            ("01-dark-en-1440-full.png", "dark", "en", 1440, 900, "#overview", "fullpage", None),
            ("02-dark-zh-1440-full.png", "dark", "zh", 1440, 900, "#overview", "fullpage", None),
            ("03-light-en-1440-full.png", "light", "en", 1440, 900, "#overview", "fullpage", None),
            ("04-light-zh-1440-full.png", "light", "zh", 1440, 900, "#overview", "fullpage", None),
            ("05-dark-en-1440-rates.png", "dark", "en", 1440, 900, "#rates", "viewport", None),
            ("06-dark-zh-1440-rates.png", "dark", "zh", 1440, 900, "#rates", "viewport", None),
            ("07-light-en-1440-rates.png", "light", "en", 1440, 900, "#rates", "viewport", None),
            ("08-light-zh-1440-rates.png", "light", "zh", 1440, 900, "#rates", "viewport", None),
            ("09-dark-en-390.png", "dark", "en", 390, 844, "#overview", "iframe", {"scroll": 0}),
            ("10-dark-zh-390.png", "dark", "zh", 390, 844, "#overview", "iframe", {"scroll": 0}),
            ("11-light-en-390.png", "light", "en", 390, 844, "#overview", "iframe", {"scroll": 0}),
            ("12-light-zh-390.png", "light", "zh", 390, 844, "#overview", "iframe", {"scroll": 0}),
            ("44-dark-en-390-max.png", "dark", "en", 390, 844, "#overview", "iframe-end", {"scroll": "max"}),
            ("45-dark-zh-390-max.png", "dark", "zh", 390, 844, "#overview", "iframe-end", {"scroll": "max"}),
            ("46-light-en-390-max.png", "light", "en", 390, 844, "#overview", "iframe-end", {"scroll": "max"}),
            ("47-light-zh-390-max.png", "light", "zh", 390, 844, "#overview", "iframe-end", {"scroll": "max"}),
            ("15-dark-en-768.png", "dark", "en", 768, 1400, "#overview", "iframe-full", None),
            ("16-light-en-768.png", "light", "en", 768, 1400, "#overview", "iframe-full", None),
            ("28-dark-zh-768.png", "dark", "zh", 768, 1400, "#overview", "iframe-full", None),
            ("29-light-zh-768.png", "light", "zh", 768, 1400, "#overview", "iframe-full", None),
            ("17-dark-en-1440-arrival.png", "dark", "en", 1440, 900, "#rates", "arrival", None),
            ("18-light-en-1440-arrival.png", "light", "en", 1440, 900, "#rates", "arrival", None),
            ("30-dark-zh-1440-arrival.png", "dark", "zh", 1440, 900, "#rates", "arrival", None),
            ("31-light-zh-1440-arrival.png", "light", "zh", 1440, 900, "#rates", "arrival", None),
            ("36-dark-en-390-arrival.png", "dark", "en", 390, 844, "#rates", "arrival-iframe", None),
            ("37-dark-zh-390-arrival.png", "dark", "zh", 390, 844, "#rates", "arrival-iframe", None),
            ("38-light-en-390-arrival.png", "light", "en", 390, 844, "#rates", "arrival-iframe", None),
            ("39-light-zh-390-arrival.png", "light", "zh", 390, 844, "#rates", "arrival-iframe", None),
            ("19-dark-en-1440-dest-hover.png", "dark", "en", 1440, 900, "#overview", "hover", None),
            ("20-light-en-1440-dest-hover.png", "light", "en", 1440, 900, "#overview", "hover", None),
            ("32-dark-zh-1440-dest-hover.png", "dark", "zh", 1440, 900, "#overview", "hover", None),
            ("33-light-zh-1440-dest-hover.png", "light", "zh", 1440, 900, "#overview", "hover", None),
            ("21-dark-en-1440-heading-focus.png", "dark", "en", 1440, 900, "#overview", "focus", None),
            ("22-light-en-1440-heading-focus.png", "light", "en", 1440, 900, "#overview", "focus", None),
            ("34-dark-zh-1440-heading-focus.png", "dark", "zh", 1440, 900, "#overview", "focus", None),
            ("35-light-zh-1440-heading-focus.png", "light", "zh", 1440, 900, "#overview", "focus", None),
            ("23-dark-en-1440-money-central-banks.png", "dark", "en", 1440, 900, "#money/central_banks", "viewport", None),
            ("27-light-en-1440-money-central-banks.png", "light", "en", 1440, 900, "#money/central_banks", "viewport", None),
            ("48-dark-zh-1440-money-central-banks.png", "dark", "zh", 1440, 900, "#money/central_banks", "viewport", None),
            ("49-light-zh-1440-money-central-banks.png", "light", "zh", 1440, 900, "#money/central_banks", "viewport", None),
            ("24-dark-en-1440-inflation-foot.png", "dark", "en", 1440, 900, "#inflation", "viewport", None),
            ("55-light-en-1440-inflation-foot.png", "light", "en", 1440, 900, "#inflation", "viewport", None),
            ("56-dark-zh-1440-inflation-foot.png", "dark", "zh", 1440, 900, "#inflation", "viewport", None),
            ("57-light-zh-1440-inflation-foot.png", "light", "zh", 1440, 900, "#inflation", "viewport", None),
            ("movement-row-dark-en.png", "dark", "en", 1440, 900, "#inflation", "movement-row", None),
            ("movement-row-dark-zh.png", "dark", "zh", 1440, 900, "#inflation", "movement-row", None),
            ("movement-row-light-en.png", "light", "en", 1440, 900, "#inflation", "movement-row", None),
            ("movement-row-light-zh.png", "light", "zh", 1440, 900, "#inflation", "movement-row", None),
        ]

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, channel="chrome")
            proc, origin = _serve(SITE)
            servers.append(proc)
            try:
                for filename, theme, locale, vw, vh, hash_path, kind, extra in shots:
                    dest = EVIDENCE / filename
                    print(f"capturing {filename} ({kind})", flush=True)
                    context = _new_context(browser, theme, locale, vw, vh)
                    inner = None
                    page = None
                    try:
                        # Playwright's viewport already is the device width
                        # (CDP Emulation.setDeviceMetricsOverride), so 390/768
                        # media queries fire without an iframe. The Chrome CLI
                        # iframe harness is only needed for --window-size.
                        page = _open_direct(context, origin + "/macro_monetary.html",
                                            hash_path, theme, locale)
                        target = page
                        page.wait_for_selector(".mc-shell", timeout=15000)
                        if hash_path == "#overview" and locale == "en":
                            html = target.content()
                            if "Every desk reported today" in html:
                                raise RuntimeError(f"{filename} still has the false-green stance")
                            if "Some desks have not reported yet" not in html:
                                raise RuntimeError(f"{filename} missing warn stance")
                            if "What moved below is what we do have" in html:
                                raise RuntimeError(
                                    f"{filename} still promises movement on a current-only deck")
                            if "The latest readings are below" not in html:
                                raise RuntimeError(
                                    f"{filename} missing current-only deck sentence")
                            if "and what moved?" in html:
                                raise RuntimeError(
                                    f"{filename} still asks what moved")
                        extra = dict(extra or {})
                        extra.setdefault("fixture", "builder-payload")
                        extra["locale"] = locale
                        if kind == "iframe-end":
                            extra["scroll_y"] = _settle_scroll(target, "max")
                            extra = _write_shot(page, dest, extra, vw, vh, locale=locale)
                        elif kind in ("iframe", "iframe-full", "viewport"):
                            extra["scroll_y"] = _settle_scroll(target, "0")
                            extra = _write_shot(page, dest, extra, vw, vh, locale=locale)
                        elif kind == "fullpage":
                            extra["scroll_y"] = _settle_scroll(target, "0")
                            extra = _write_shot(
                                page, dest, extra, vw, vh, full_page=True,
                                locale=locale)
                        elif kind == "arrival":
                            target.wait_for_selector("[data-mc-arrival]:not([hidden])", timeout=8000)
                            extra["scroll_y"] = _read_scroll(target)
                            extra = _write_shot(
                                target, dest, extra, vw, vh,
                                crop_locator=target.locator("#rates"),
                                crop_selector="#rates",
                                locale=locale)
                        elif kind == "arrival-iframe":
                            target.wait_for_selector("[data-mc-arrival]:not([hidden])", timeout=8000)
                            extra["scroll_y"] = _read_scroll(target)
                            extra = _write_shot(page, dest, extra, vw, vh, locale=locale)
                        elif kind == "hover":
                            card = target.locator("#overview .mc-dest").first
                            card.hover()
                            target.wait_for_timeout(150)
                            extra["scroll_y"] = _read_scroll(target)
                            extra = _write_shot(
                                target, dest, extra, vw, vh,
                                crop_locator=card,
                                crop_selector="#overview .mc-dest",
                                locale=locale)
                        elif kind == "focus":
                            heading = target.locator("#overview-h")
                            heading.focus()
                            target.wait_for_timeout(150)
                            extra["scroll_y"] = _read_scroll(target)
                            extra = _write_shot(
                                target, dest, extra, vw, vh,
                                crop_locator=heading,
                                crop_selector="#overview-h",
                                locale=locale)
                        elif kind == "movement-row":
                            target.wait_for_selector(
                                "#inflation .mc-move-words", timeout=15000)
                            row_loc = target.locator(
                                "#inflation .mc-move-row:not(.mc-move-current-only)").first
                            row_loc.wait_for(state="visible", timeout=8000)
                            extra["scroll_y"] = _read_scroll(target)
                            extra = _write_shot(
                                target, dest, extra, vw, vh,
                                crop_locator=row_loc,
                                crop_selector="#inflation .mc-move-row:not(.mc-move-current-only)",
                                locale=locale)
                            text_head = str(extra.get("element_text_head") or "")
                            if not re.search(r"\d", text_head):
                                raise RuntimeError(
                                    f"{filename} movement row missing a value: {text_head!r}")
                            if "mc-move-words" not in (
                                    row_loc.evaluate(
                                        "el => el.innerHTML") or ""):
                                raise RuntimeError(
                                    f"{filename} movement row missing the phrase")
                        else:
                            extra["scroll_y"] = _read_scroll(target)
                            extra = _write_shot(
                                page, dest, extra, vw, vh, full_page=True,
                                locale=locale)
                        _upsert(manifest, filename, _row(filename, dest, theme, locale, vw, vh, extra))
                        print(f"  {filename} {dest.stat().st_size}B {_sha(dest)[:12]}", flush=True)
                    finally:
                        context.close()

                # B1 rail probe + R8-M1 clearance at 390, four theme/lang cells
                for theme, locale in (("dark", "en"), ("dark", "zh"),
                                      ("light", "en"), ("light", "zh")):
                    context = _new_context(browser, theme, locale, 390, 844)
                    try:
                        page = _open_direct(
                            context, origin + "/macro_monetary.html",
                            "#overview", theme, locale)
                        page.wait_for_selector(".mc-analyst", timeout=15000)
                        page.wait_for_selector(".mc-panels", timeout=15000)
                        rail = page.evaluate(RAIL_JS)
                        if not rail.get("ok") or rail.get("railAlpha") != 1 or not rail.get("equal"):
                            raise RuntimeError(f"B1 rail probe failed {theme}/{locale}: {rail}")
                        if not rail.get("noDocOverflow"):
                            raise RuntimeError(
                                f"I1 document overflow {theme}/{locale}: "
                                f"scrollWidth={rail.get('scrollWidth')} "
                                f"clientWidth={rail.get('clientWidth')}")
                        probes[f"rail_{theme}_{locale}"] = rail
                        clear = _run_clearance(page)
                        if not clear.get("ok"):
                            raise RuntimeError(
                                f"R8-M1 clearance failed 390 {theme}/{locale}: {clear}")
                        probes[f"clearance_390_{theme}_{locale}"] = clear
                        viewport = page.evaluate(RAIL_VIEWPORT_JS)
                        if not viewport.get("ok"):
                            raise RuntimeError(
                                f"rail viewport 390 {theme}/{locale}: {viewport}")
                        viewport.update(_confirm_rail_fade_visual(page, viewport))
                        probes[f"rail_viewport_{theme}_{locale}_390"] = viewport
                        probes.pop(f"rail_clip_{theme}_{locale}_390", None)
                        material = page.evaluate(CHIP_MATERIAL_JS)
                        if not material.get("ok"):
                            raise RuntimeError(
                                f"chip material 390 {theme}/{locale}: {material}")
                        probes[f"chip_material_{theme}_{locale}_390"] = material
                        print(
                            f"  clearance 390 {theme}/{locale} ok={clear['ok']} "
                            f"texts={clear['textCount']} "
                            f"analyst={clear['positions']['0'].get('analystPosition')} "
                            f"bootInDom={clear['positions']['0'].get('mmbBootInDom')} "
                            f"bootVisible={clear['positions']['0'].get('mmbBootVisible')}",
                            flush=True)
                    finally:
                        context.close()

                # 768 rail + clearance, both themes × both locales
                for theme, locale in (("dark", "en"), ("dark", "zh"),
                                      ("light", "en"), ("light", "zh")):
                    context = _new_context(browser, theme, locale, 768, 1400)
                    try:
                        page = _open_direct(
                            context, origin + "/macro_monetary.html",
                            "#overview", theme, locale)
                        page.wait_for_selector(".mc-rail", timeout=15000)
                        rail = page.evaluate(RAIL_JS)
                        if not rail.get("ok") or rail.get("railAlpha") != 1 or not rail.get("equal"):
                            raise RuntimeError(f"B1 768 rail probe failed {theme}: {rail}")
                        probes[f"rail_768_{theme}_{locale}"] = rail
                        clear = _run_clearance(page)
                        if not clear.get("ok"):
                            raise RuntimeError(
                                f"R8-M1 clearance failed 768 {theme}/{locale}: {clear}")
                        probes[f"clearance_768_{theme}_{locale}"] = clear
                        viewport = page.evaluate(RAIL_VIEWPORT_JS)
                        if not viewport.get("ok"):
                            raise RuntimeError(
                                f"rail viewport 768 {theme}/{locale}: {viewport}")
                        viewport.update(_confirm_rail_fade_visual(page, viewport))
                        probes[f"rail_viewport_{theme}_{locale}_768"] = viewport
                        probes.pop(f"rail_clip_{theme}_{locale}_768", None)
                        material = page.evaluate(CHIP_MATERIAL_JS)
                        if not material.get("ok"):
                            raise RuntimeError(
                                f"chip material 768 {theme}/{locale}: {material}")
                        probes[f"chip_material_{theme}_{locale}_768"] = material
                        print(
                            f"  clearance 768 {theme}/{locale} ok={clear['ok']} "
                            f"texts={clear['textCount']}",
                            flush=True)
                    finally:
                        context.close()

                # R9-M2 / MAJOR-E1: FAB visible at 1440 and clearance
                # ladder with #mmb-boot as a fixed occluder.
                for theme, locale in (("dark", "en"), ("dark", "zh"),
                                      ("light", "en"), ("light", "zh")):
                    context = _new_context(browser, theme, locale, 1440, 900)
                    try:
                        page = _open_direct(
                            context, origin + "/macro_monetary.html",
                            "#overview", theme, locale)
                        page.wait_for_selector("#mmb-boot", timeout=15000)
                        page.wait_for_selector(".mc-panels", timeout=15000)
                        fab = page.evaluate("""() => {
                          const el = document.getElementById('mmb-boot');
                          if (!el) return {present: false, display: null};
                          const cs = getComputedStyle(el);
                          const box = el.getBoundingClientRect();
                          return {present: true, display: cs.display,
                                  position: cs.position,
                                  box: {top: box.top, bottom: box.bottom,
                                        left: box.left, right: box.right,
                                        width: box.width, height: box.height}};
                        }""")
                        if not fab.get("present") or fab.get("display") == "none":
                            raise RuntimeError(
                                f"R9-M2 FAB must stay visible at 1440 "
                                f"{theme}/{locale}: {fab}")
                        key = f"fab_display_1440_{theme}_{locale}"
                        probes[key] = fab
                        clear = _run_clearance(page)
                        if not clear.get("ok"):
                            raise RuntimeError(
                                f"clearance failed 1440 {theme}/{locale}: {clear}")
                        for pos_name, pos in (clear.get("positions") or {}).items():
                            names = [ov.get("name") for ov in pos.get("overlays") or []]
                            if "mmb-boot" not in names:
                                raise RuntimeError(
                                    f"1440 clearance missing mmb-boot overlay "
                                    f"{theme}/{locale}@{pos_name}: {names}")
                        probes[f"clearance_1440_{theme}_{locale}"] = clear
                        print(
                            f"  {key} {fab} clearance texts="
                            f"{clear.get('textCount')} "
                            f"bootBox={clear.get('mmbBootBox')}",
                            flush=True)
                    finally:
                        context.close()

                # MINOR-C1: shipped CLEARANCE_AT_JS on a synthetic page.
                syn_ctx = _new_context(browser, "dark", "en", 1440, 900)
                try:
                    syn_page = syn_ctx.new_page()
                    probes["synthetic_clearance"] = _run_synthetic_clearance(
                        syn_page)
                    print("  synthetic_clearance ok", flush=True)
                finally:
                    syn_ctx.close()

                # r10 evidence m4: click the ≤768 analyst chip; the same
                # chat surface the FAB would boot (`#mmb-root`) must mount.
                for theme, locale in (("dark", "en"), ("dark", "zh"),
                                      ("light", "en"), ("light", "zh")):
                    context = _new_context(browser, theme, locale, 390, 844)
                    try:
                        page = _open_direct(
                            context, origin + "/macro_monetary.html",
                            "#overview", theme, locale)
                        page.wait_for_selector("[data-mc-analyst]", timeout=15000)
                        chat = _run_chip_opens_chat(page)
                        key = f"chip_opens_chat_390_{theme}_{locale}"
                        probes[key] = chat
                        print(
                            f"  {key} mounted={chat.get('mountedId')} "
                            f"class={chat.get('mountedClass')!r} "
                            f"panel={chat.get('mmbPanelPresent')}",
                            flush=True)
                    finally:
                        context.close()

                # RIDER M2: one hairline on a populated light sub-tab.
                context = _new_context(browser, "light", "en", 1440, 900)
                try:
                    page = _open_direct(
                        context, origin + "/macro_monetary.html",
                        "#money/central_banks", "light", "en")
                    page.wait_for_selector(
                        "#central_banks .mc-move-row, "
                        "#central_banks .mc-move-current-only",
                        state="visible",
                        timeout=15000)
                    hair = page.evaluate(HAIRLINE_JS)
                    if not hair.get("populated"):
                        raise RuntimeError(f"RIDER M2 hairline probe not populated: {hair}")
                    if hair.get("hairlineCount") != 1:
                        raise RuntimeError(
                            f"RIDER M2 expected one hairline, got {hair}")
                    if hair.get("tabbodyBorderTopPx") != 0:
                        raise RuntimeError(
                            f"RIDER M2 tabbody still draws a top rule: {hair}")
                    if hair.get("figureBorderTopPx") != 1:
                        raise RuntimeError(
                            f"RIDER M2 figure fence missing: {hair}")
                    probes["m2_hairline_light_en"] = hair
                    print(
                        f"  probe m2_hairline_light_en count={hair['hairlineCount']} "
                        f"figTop={hair['figureBorderTopPx']} "
                        f"tabTop={hair['tabbodyBorderTopPx']} "
                        f"tab={hair.get('visibleTab')}",
                        flush=True)
                finally:
                    context.close()

                # R8-m1: strip-void at 1440 dark+light × EN+ZH, JS + PNG scan.
                strip_voids: dict[str, Any] = {}
                frame_for = {
                    ("dark", "en"): "01-dark-en-1440.png",
                    ("dark", "zh"): "02-dark-zh-1440.png",
                    ("light", "en"): "03-light-en-1440.png",
                    ("light", "zh"): "04-light-zh-1440.png",
                }
                for theme, locale in (("dark", "en"), ("dark", "zh"),
                                      ("light", "en"), ("light", "zh")):
                    context = _new_context(browser, theme, locale, 1440, 900)
                    try:
                        page = _open_direct(
                            context, origin + "/macro_monetary.html",
                            "#overview", theme, locale)
                        page.wait_for_selector(".mc-strip .mc-chip", timeout=15000)
                        void_probe = page.evaluate(STRIP_VOID_JS)
                        png = EVIDENCE / frame_for[(theme, locale)]
                        pixel = _pixel_scan_strip_void(png, void_probe)
                        void_probe["pixelVoidWiderThan40"] = pixel["pixelVoidWiderThan40"]
                        void_probe["pixelVoids"] = pixel.get("pixelVoids")
                        void_probe["pixelVoidCount"] = pixel.get("pixelVoidCount")
                        void_probe["canvasRgb"] = pixel.get("canvasRgb")
                        void_probe["canvasSource"] = pixel.get("canvasSource")
                        void_probe["bgTokenRgb"] = pixel.get("bgTokenRgb")
                        void_probe["delta"] = pixel.get("delta")
                        void_probe["ok"] = bool(
                            void_probe.get("ok") and pixel.get("ok"))
                        if not void_probe.get("ok"):
                            raise RuntimeError(
                                f"R8-m1 strip void {theme}/{locale}: {void_probe}")
                        if void_probe.get("voidWiderThan40"):
                            raise RuntimeError(
                                f"R8-m1 void wider than 40 {theme}/{locale}: {void_probe}")
                        key = f"{theme}_{locale}"
                        strip_voids[key] = void_probe
                        print(
                            f"  strip_void {key} chips={void_probe['chipCount']} "
                            f"maxVoid={void_probe.get('maxVoidWidth')} "
                            f"pixelVoids={pixel.get('pixelVoidCount')} "
                            f"canvas={pixel.get('canvasRgb')} "
                            f"src={pixel.get('canvasSource')} "
                            f"ok={void_probe['ok']}",
                            flush=True)
                    finally:
                        context.close()
                probes["strip_void_probes"] = strip_voids
                probes.pop("strip_void_probe", None)
                _capture_e5_cells(
                    browser, origin, probes, manifest,
                    site_root=SITE, servers=servers)
            finally:
                _kill(proc)
                if proc in servers:
                    servers.remove(proc)

            _capture_empty_states(browser, tmp, servers, manifest)
            browser.close()

        # Distinct-frame sha check; drop the r4 stray row.
        states = [
            state for state in manifest["pages"][0]["states"]
            if state.get("file") not in {
                "rates-curves-zh-after.png",
                "27-light-en-1440-growth-business.png",
                "13-dark-en-390-end.png",
                "14-light-zh-390-end.png",
            }
            and state.get("force_state") not in {
                "addendum:rates-curves-zh-after.png",
                "growth_business",
            }
        ]
        manifest["pages"][0]["states"] = states
        for stray_name in (
            "rates-curves-zh-after.png",
            "27-light-en-1440-growth-business.png",
            "13-dark-en-390-end.png",
            "14-light-zh-390-end.png",
        ):
            stray = EVIDENCE / stray_name
            if stray.exists():
                stray.unlink()

        by_sha: dict[str, list[str]] = {}
        force_states: set[str] = set()
        for state in states:
            fs = state.get("force_state")
            if fs:
                if str(fs).startswith("addendum:"):
                    raise RuntimeError(f"N-M2 leftover addendum force_state: {fs}")
                force_states.add(str(fs))
            if not state.get("reduced_motion"):
                raise RuntimeError(
                    f"N-M2 missing reduced_motion on {state.get('file') or fs}")
            if state.get("viewport_width") == 768 and state.get("viewport") != "tablet":
                raise RuntimeError(
                    f"N-M2 768 frame must be viewport=tablet: {state.get('file')}")
            if state.get("captured") and state.get("sha256") and state.get("file"):
                by_sha.setdefault(state["sha256"], []).append(state["file"])
        dupes = {sha: names for sha, names in by_sha.items() if len(names) > 1}
        if dupes:
            raise RuntimeError(f"duplicate evidence blobs: {dupes}")

        manifest["axes"]["force_states"] = sorted(force_states)
        declared = _declared_families()
        captured_keys = _captured_declared_keys(states, probes)
        manifest["declared"] = declared
        manifest["gaps"] = _compute_gaps_from_declared(declared, captured_keys)
        manifest.setdefault("honesty", {})
        manifest["honesty"]["gaps"] = (
            "every declared family cell that was not captured is recorded "
            "in gaps with a reason; force_states, empty_states, clearance, "
            "chip_opens_chat, strip_void, rail_viewport, e5, fab, "
            "rest_views, full_page, and movement_row are "
            "published as data and gaps is computed from that structure"
        )
        manifest["pages"][0]["gaps"] = _compute_gaps(
            _declared_empty_cells(), states)
        for gap in list(manifest["gaps"]) + list(manifest["pages"][0]["gaps"]):
            if not gap.get("reason"):
                raise RuntimeError(f"gap missing reason: {gap}")
            if gap.get("captured") is not False:
                raise RuntimeError(f"gap must be captured:false: {gap}")
        manifest["axes"]["viewports"] = {
            "desktop": [1440, 900],
            "tablet": [768, 1400],
            "mobile": [390, 844],
        }
        generated_at_end = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        head_end = _assert_head_unmoved(head)
        end_tree = _require_clean_tree(
            when="end", paths=("templates", "scripts", "lib"))
        commit_time = _commit_iso(head)
        protocol = {
            "tree_clean_start": start_tree["clean"],
            "tree_clean_end": end_tree["clean"],
            "head_start": head,
            "head_end": head_end,
            "generated_at_start": generated_at_start,
            "generated_at_end": generated_at_end,
            "commit_time_of_capture_sha": commit_time,
        }
        manifest["generated_at"] = generated_at_end
        manifest["generated_at_start"] = generated_at_start
        manifest["generated_at_end"] = generated_at_end
        manifest["tree_clean_start"] = protocol["tree_clean_start"]
        manifest["tree_clean_end"] = protocol["tree_clean_end"]
        manifest["head_start"] = head
        manifest["head_end"] = head_end
        manifest["capture_sha"] = head
        manifest["commit_time_of_capture_sha"] = commit_time
        manifest.pop("strip_void_probe", None)
        manifest["strip_void_probes"] = probes.get("strip_void_probes")
        manifest.setdefault("target", {})
        manifest["target"]["resolved_sha_or_none"] = head
        manifest["target"]["resolved_sha_source"] = _derive_resolved_sha_source(
            protocol)
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        probes["generated_at"] = generated_at_end
        probes["generated_at_start"] = generated_at_start
        probes["generated_at_end"] = generated_at_end
        probes["tree_clean_start"] = protocol["tree_clean_start"]
        probes["tree_clean_end"] = protocol["tree_clean_end"]
        probes["head_start"] = head
        probes["head_end"] = head_end
        probes["capture_sha"] = head
        probes["commit_time_of_capture_sha"] = commit_time
        probes["resolved_sha_or_none"] = head
        probes.pop("strip_void_probe", None)
        PROBES.write_text(json.dumps(probes, indent=2) + "\n", encoding="utf-8")
        print(
            f"wrote {MANIFEST} generated_at_start={generated_at_start} "
            f"generated_at_end={generated_at_end} head={head} "
            f"tree_clean_start={protocol['tree_clean_start']} "
            f"tree_clean_end={protocol['tree_clean_end']}",
            flush=True)
        return 0
    finally:
        for proc in servers:
            _kill(proc)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
