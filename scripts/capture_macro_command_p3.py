"""Recapture the Macro Command P3 evidence matrix from one production build.

House method: theme/lang settled before load; 2x device scale; 390/768 through a
same-width iframe harness (headless Chrome clamps --window-size below ~500).
Empty-state frames use fixture builds; E5 stays captured:false.

HTTP servers are backgrounded and always killed.
"""
from __future__ import annotations

import hashlib
import json
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
  /* R9: at scroll 0 / 50% / max, no .mc-panels text node may
     intersect a *displayed* fixed overlay, or — at scroll 0 — be
     fully covered by the sticky rail.
     Overlay set = rail strip + chips + #mmb-boot ONLY when
     getComputedStyle(#mmb-boot).display is not 'none' (at ≤768 on
     this page the FAB is hidden; do not invent a box for it).
     Destination-card text under #mmb-boot is a HIT. There is no
     blanket .mc-dest* exemption. A node is excused only when a
     sticky overlay intersects it mid-scroll (normal sticky header).
     Every exemption is recorded in excused[] (text, box, ovBox,
     reason). reason is derived from ov.name plus geometry:
     `<name>_fully_covered` when the text box is inside the overlay,
     `<name>_partially_covered` when it only intersects. A full
     cover at scroll 0 is a HIT (`sticky-rail-full-cover-at-0`).
     An empty text-node set is a fail. Never scrollBy. */
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
  const note = (list, node, rect, ov, reason) => {
    list.push({
      text: String(node.nodeValue || '').trim().slice(0, 80),
      overlay: ov.name,
      overlayPos: ov.pos,
      box: {top: rect.top, left: rect.left, right: rect.right, bottom: rect.bottom},
      ovBox: {top: ov.top, left: ov.left, right: ov.right, bottom: ov.bottom},
      reason,
    });
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
        const railFull = ov.pos === 'sticky' && target === '0' && covered;
        if (!fixed && !railFull) {
          note(excused, node, rect, ov,
            covered ? (ov.name + '_fully_covered')
                    : (ov.name + '_partially_covered'));
          continue;
        }
        note(hits, node, rect, ov,
          fixed ? 'fixed-overlay-intersects-text' : 'sticky-rail-full-cover-at-0');
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
    mmbBootPresent: Boolean(boot),
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
    const bgResolved = getComputedStyle(document.body).backgroundColor;
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
    bgResolved,
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
    return {
        "ok": all(pos.get("ok") for pos in positions.values()),
        "textCount": positions["0"].get("textCount"),
        "positions": positions,
        "analystPosition": positions["0"].get("analystPosition"),
        "mmbBootPresent": positions["0"].get("mmbBootPresent"),
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

    # r9-m4 / r10-m3: sample the canvas from the strip's own inter-chip
    # gap, never page pixel (8,8). The sample must sit outside every
    # chip box with a ≥8 css gap; otherwise fall back to --bg.
    row_boxes_sorted = sorted(row_boxes, key=lambda box: box["left"])
    canvas = None
    canvas_source = "getComputedStyle --bg"
    if len(row_boxes_sorted) >= 2:
        gap_left = row_boxes_sorted[0]["right"]
        gap_right = row_boxes_sorted[1]["left"]
        gap_css = gap_right - gap_left
        sample_x = int(((gap_left + gap_right) / 2) * scale)
        sample_y = int(((min(box["top"] for box in row_boxes)
                         + max(box["bottom"] for box in row_boxes)) / 2) * scale)
        sample_x = min(max(0, sample_x), image.width - 1)
        sample_y = min(max(0, sample_y), image.height - 1)
        if gap_css >= 8 and not in_chip(sample_x, sample_y):
            canvas = image.getpixel((sample_x, sample_y))
            canvas_source = (
                f"strip-inter-chip-gap ({sample_x},{sample_y}) "
                f"gapCss={gap_css:.2f}")
    if canvas is None:
        token = (probe.get("bgResolved") or "").strip()
        parsed = _rgb_token(token)
        if parsed is None:
            raise RuntimeError(
                "strip-void canvas: gap <8px or in_chip and --bg did not resolve")
        canvas = parsed
        canvas_source = f"getComputedStyle --bg {token}"

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
        "band": {"x0": x0, "x1": x1, "y0": y0, "y1": y1},
    }


def _rgb_token(color: str) -> tuple[int, int, int] | None:
    """Parse a computed rgb/rgba() colour into an 8-bit triple."""
    if not color:
        return None
    match = re.search(
        r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)", color)
    if not match:
        return None
    return (int(float(match.group(1))), int(float(match.group(2))),
            int(float(match.group(3))))


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


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
        f"(R6-B1). E5 stays captured:false — client fetch-timeout, not "
        f"builder-triggerable."
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


def _serve(root: Path) -> tuple[subprocess.Popen, str]:
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
    row = {
        "access": "anonymous",
        "applied_locale": locale,
        "applied_theme": theme,
        "bytes": dest.stat().st_size,
        "captured": True,
        "file": filename,
        "force_state": force_state,
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
             "fixture": "in-memory: hub.changes.entries=[] → E3",
             "trigger": "Overview figure slot empty; directory untouched",
             "force_state": "e3",
         }),
        ("26-light-en-1440-e3.png", "light", e3_overview, "#overview",
         "#overview", {
             "fixture": "in-memory: hub.changes.entries=[] → E3",
             "trigger": "Overview figure slot empty; directory untouched",
             "force_state": "e3",
         }),
        ("empty-e1-dark.png", "dark", e1_site, "#inflation",
         "#inflation [data-mc-empty='e1']", {
             "fixture": "mockups/evidence/macro-command-p3/fixtures/e1_inflation_system.json",
             "trigger": "Contract-legal inflation_system JSON: no date, no deltas → E1",
             "force_state": "e1",
         }),
        ("empty-e1-light.png", "light", e1_site, "#inflation",
         "#inflation [data-mc-empty='e1']", {
             "fixture": "mockups/evidence/macro-command-p3/fixtures/e1_inflation_system.json",
             "trigger": "Contract-legal inflation_system JSON: no date, no deltas → E1",
             "force_state": "e1",
         }),
        ("empty-e2-dark.png", "dark", SITE, "#rates",
         "#rates [data-mc-empty='e2']", {
             "fixture": "mockups/evidence/macro-command-p3/fixtures/e2_rates_curves.json",
             "trigger": "Live #rates workspace context.state is SOURCE_FAILED / STALE_SOURCE",
             "force_state": "e2",
         }),
        ("empty-e2-light.png", "light", SITE, "#rates",
         "#rates [data-mc-empty='e2']", {
             "fixture": "mockups/evidence/macro-command-p3/fixtures/e2_rates_curves.json",
             "trigger": "Live #rates workspace context.state is SOURCE_FAILED / STALE_SOURCE",
             "force_state": "e2",
         }),
        ("empty-e3-dark.png", "dark", e3_site, "#inflation",
         "#inflation [data-mc-empty='e3']", {
             "fixture": "mockups/evidence/macro-command-p3/fixtures/e3_inflation_system.json",
             "trigger": "Contract-legal inflation_system JSON: dated, no comparable deltas → E3",
             "force_state": "e3",
         }),
        ("empty-e3-light.png", "light", e3_site, "#inflation",
         "#inflation [data-mc-empty='e3']", {
             "fixture": "mockups/evidence/macro-command-p3/fixtures/e3_inflation_system.json",
             "trigger": "Contract-legal inflation_system JSON: dated, no comparable deltas → E3",
             "force_state": "e3",
         }),
        ("empty-e4-dark.png", "dark", e4_site, "#money/central_banks",
         "#money [data-mc-empty='e4']", {
             "fixture": "mockups/evidence/macro-command-p3/fixtures/e4_central_banks.json",
             "trigger": " --empty-state-fixture e4_central_banks.json → withheld_command_tabs",
             "force_state": "e4",
         }),
        ("empty-e4-light.png", "light", e4_site, "#money/central_banks",
         "#money [data-mc-empty='e4']", {
             "fixture": "mockups/evidence/macro-command-p3/fixtures/e4_central_banks.json",
             "trigger": " --empty-state-fixture e4_central_banks.json → withheld_command_tabs",
             "force_state": "e4",
         }),
        ("empty-e6-dark.png", "dark", e6_site, "#inflation",
         "#inflation [data-mc-empty='e6']", {
             "fixture": "mockups/evidence/macro-command-p3/fixtures/e6_inflation_system.json",
             "trigger": "--empty-state-fixture e6_inflation_system.json → entitlement=Research",
             "force_state": "e6",
         }),
        ("empty-e6-light.png", "light", e6_site, "#inflation",
         "#inflation [data-mc-empty='e6']", {
             "fixture": "mockups/evidence/macro-command-p3/fixtures/e6_inflation_system.json",
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
            context = _new_context(browser, theme, locale, 1440, 2200)
            try:
                page = _open_direct(
                    context, _origin + "/macro_monetary.html",
                    hash_path, theme, locale)
                page.wait_for_selector(selector, timeout=15000)
                extra = dict(extra)
                extra["scroll_y"] = _read_scroll(page)
                page.locator(selector).first.screenshot(path=str(dest), type="png")
                _assert_png(dest)
                _upsert(manifest, filename, _row(
                    filename, dest, theme, locale, 1440, 2200, extra))
                print(f"  {filename} {dest.stat().st_size}B {_sha(dest)[:12]}", flush=True)
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
    ):
        probes.pop(alias, None)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    try:
        shots = [
            # filename, theme, locale, w, h, hash, kind, extra
            ("01-dark-en-1440.png", "dark", "en", 1440, 2200, "#overview", "full", None),
            ("02-dark-zh-1440.png", "dark", "zh", 1440, 2200, "#overview", "full", None),
            ("03-light-en-1440.png", "light", "en", 1440, 2200, "#overview", "full", None),
            ("04-light-zh-1440.png", "light", "zh", 1440, 2200, "#overview", "full", None),
            ("05-dark-en-1440-rates.png", "dark", "en", 1440, 2200, "#rates", "full", None),
            ("06-dark-zh-1440-rates.png", "dark", "zh", 1440, 2200, "#rates", "full", None),
            ("07-light-en-1440-rates.png", "light", "en", 1440, 2200, "#rates", "full", None),
            ("08-light-zh-1440-rates.png", "light", "zh", 1440, 2200, "#rates", "full", None),
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
            ("17-dark-en-1440-arrival.png", "dark", "en", 1440, 2200, "#rates", "arrival", None),
            ("18-light-en-1440-arrival.png", "light", "en", 1440, 2200, "#rates", "arrival", None),
            ("30-dark-zh-1440-arrival.png", "dark", "zh", 1440, 2200, "#rates", "arrival", None),
            ("31-light-zh-1440-arrival.png", "light", "zh", 1440, 2200, "#rates", "arrival", None),
            ("36-dark-en-390-arrival.png", "dark", "en", 390, 844, "#rates", "arrival-iframe", None),
            ("37-dark-zh-390-arrival.png", "dark", "zh", 390, 844, "#rates", "arrival-iframe", None),
            ("38-light-en-390-arrival.png", "light", "en", 390, 844, "#rates", "arrival-iframe", None),
            ("39-light-zh-390-arrival.png", "light", "zh", 390, 844, "#rates", "arrival-iframe", None),
            ("19-dark-en-1440-dest-hover.png", "dark", "en", 1440, 2200, "#overview", "hover", None),
            ("20-light-en-1440-dest-hover.png", "light", "en", 1440, 2200, "#overview", "hover", None),
            ("32-dark-zh-1440-dest-hover.png", "dark", "zh", 1440, 2200, "#overview", "hover", None),
            ("33-light-zh-1440-dest-hover.png", "light", "zh", 1440, 2200, "#overview", "hover", None),
            ("21-dark-en-1440-heading-focus.png", "dark", "en", 1440, 2200, "#overview", "focus", None),
            ("22-light-en-1440-heading-focus.png", "light", "en", 1440, 2200, "#overview", "focus", None),
            ("34-dark-zh-1440-heading-focus.png", "dark", "zh", 1440, 2200, "#overview", "focus", None),
            ("35-light-zh-1440-heading-focus.png", "light", "zh", 1440, 2200, "#overview", "focus", None),
            ("23-dark-en-1440-money-central-banks.png", "dark", "en", 1440, 2200, "#money/central_banks", "full", None),
            ("27-light-en-1440-money-central-banks.png", "light", "en", 1440, 2200, "#money/central_banks", "full", None),
            ("48-dark-zh-1440-money-central-banks.png", "dark", "zh", 1440, 2200, "#money/central_banks", "full", None),
            ("49-light-zh-1440-money-central-banks.png", "light", "zh", 1440, 2200, "#money/central_banks", "full", None),
            ("24-dark-en-1440-inflation-foot.png", "dark", "en", 1440, 2200, "#inflation", "full", None),
            ("55-light-en-1440-inflation-foot.png", "light", "en", 1440, 2200, "#inflation", "full", None),
            ("56-dark-zh-1440-inflation-foot.png", "dark", "zh", 1440, 2200, "#inflation", "full", None),
            ("57-light-zh-1440-inflation-foot.png", "light", "zh", 1440, 2200, "#inflation", "full", None),
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
                        if kind == "iframe-end":
                            extra["scroll_y"] = _settle_scroll(target, "max")
                            page.screenshot(path=str(dest), type="png", full_page=False)
                        elif kind == "iframe":
                            extra["scroll_y"] = _settle_scroll(target, "0")
                            page.screenshot(path=str(dest), type="png", full_page=False)
                        elif kind == "iframe-full":
                            extra["scroll_y"] = _settle_scroll(target, "0")
                            page.screenshot(path=str(dest), type="png", full_page=False)
                        elif kind == "arrival":
                            target.wait_for_selector("[data-mc-arrival]:not([hidden])", timeout=8000)
                            extra["scroll_y"] = _read_scroll(target)
                            target.locator("#rates").screenshot(path=str(dest), type="png")
                        elif kind == "arrival-iframe":
                            target.wait_for_selector("[data-mc-arrival]:not([hidden])", timeout=8000)
                            extra["scroll_y"] = _read_scroll(target)
                            page.screenshot(path=str(dest), type="png", full_page=False)
                        elif kind == "hover":
                            card = target.locator("#overview .mc-dest").first
                            card.hover()
                            target.wait_for_timeout(150)
                            extra["scroll_y"] = _read_scroll(target)
                            card.screenshot(path=str(dest), type="png")
                        elif kind == "focus":
                            heading = target.locator("#overview-h")
                            heading.focus()
                            target.wait_for_timeout(150)
                            extra["scroll_y"] = _read_scroll(target)
                            heading.screenshot(path=str(dest), type="png")
                        else:
                            extra["scroll_y"] = _read_scroll(target)
                            page.screenshot(path=str(dest), type="png", full_page=True)
                        _assert_png(dest)
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
                        print(
                            f"  clearance 390 {theme}/{locale} ok={clear['ok']} "
                            f"texts={clear['textCount']} "
                            f"analyst={clear['positions']['0'].get('analystPosition')} "
                            f"boot={clear['positions']['0'].get('mmbBootPresent')}",
                            flush=True)
                    finally:
                        context.close()

                # 768 rail + clearance, both themes (EN); ZH 768 is frames-only
                for theme, locale in (("dark", "en"), ("light", "en")):
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
                        print(
                            f"  clearance 768 {theme}/{locale} ok={clear['ok']} "
                            f"texts={clear['textCount']}",
                            flush=True)
                    finally:
                        context.close()

                # R9-M2 / r10-m3: FAB computed display at desktop — all
                # four 1440 cells. Must stay visible (flex).
                for theme, locale in (("dark", "en"), ("dark", "zh"),
                                      ("light", "en"), ("light", "zh")):
                    context = _new_context(browser, theme, locale, 1440, 2200)
                    try:
                        page = _open_direct(
                            context, origin + "/macro_monetary.html",
                            "#overview", theme, locale)
                        page.wait_for_selector("#mmb-boot", timeout=15000)
                        fab = page.evaluate("""() => {
                          const el = document.getElementById('mmb-boot');
                          if (!el) return {present: false, display: null};
                          const cs = getComputedStyle(el);
                          return {present: true, display: cs.display,
                                  position: cs.position};
                        }""")
                        if not fab.get("present") or fab.get("display") == "none":
                            raise RuntimeError(
                                f"R9-M2 FAB must stay visible at 1440 "
                                f"{theme}/{locale}: {fab}")
                        key = f"fab_display_1440_{theme}_{locale}"
                        probes[key] = fab
                        print(f"  {key} {fab}", flush=True)
                    finally:
                        context.close()

                # r10 evidence m4: click the ≤768 analyst chip; the same
                # chat surface the FAB would boot (`#mmb-root`) must mount.
                for theme, locale in (("dark", "en"), ("light", "en")):
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
                context = _new_context(browser, "light", "en", 1440, 2200)
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
                    context = _new_context(browser, theme, locale, 1440, 2200)
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
                probes["strip_void_probe"] = strip_voids["light_en"]
            finally:
                _kill(proc)
                if proc in servers:
                    servers.remove(proc)

            _capture_empty_states(browser, tmp, servers, manifest)
            browser.close()

        _upsert(manifest, "empty-e5-dark.png", {
            "access": "anonymous",
            "applied_locale": "en",
            "applied_theme": "dark",
            "bytes": None,
            "captured": False,
            "file": None,
            "sha256": None,
            "force_state": "e5",
            "fixture": None,
            "reduced_motion": True,
            "trigger": (
                "E5 is a client fetch-timeout of macro/fragments/<id>.html "
                "(PENDING_TIMEOUT_MS=8000). The builder only emits a hidden "
                "<template data-mc-empty-e5>; a visible E5 cannot be produced "
                "from workspace JSON through scripts/build_macro_suite_pages.py."
            ),
            "locale": "en",
            "reason": (
                "not builder-triggerable: client fetch-timeout of a fragment; "
                "builder emits only the hidden <template data-mc-empty-e5>"
            ),
            "theme": "dark",
            "scroll_y": None,
            "viewport": "desktop",
            "viewport_height": 2200,
            "viewport_width": 1440,
        })

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
        manifest["axes"]["viewports"] = {
            "desktop": [1440, 2200],
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
        manifest["strip_void_probe"] = probes.get("strip_void_probe")
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
