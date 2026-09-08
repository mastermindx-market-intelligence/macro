"""Capture Macro Command P5 §10 evidence frames.

Theme and language are set BEFORE load. 390/768 frames go through a
same-width iframe harness. HTTP servers start in the background and are
always killed.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
    "This page publishes no dual-axis state and no headline quadrant",
    "What this state implies",
    "Deterministic text from the accepted snapshot. No language model writes here.",
    "Confidence basis",
)
RELOCATED_ZH = (
    "本页不发布双轴状态,也不发布头条象限",
    "该状态意味着什么",
    "文本由已接受快照确定性生成，此处不由语言模型撰写。",
    "置信度依据",
)
# 15/16 already capture these two open-ribbon states; do not recapture
# them as workspace rows (identical sha256 is an M1 defect).
_SKIP_WS_DUP = {
    ("macro_rates_curves.html", "open", "dark", "en"),
    ("macro_rates_curves.html", "open", "light", "zh"),
}
WORKSPACE_PAGES = (
    "macro_rates_curves.html",
    "macro_business_activity.html",
    "macro_financial_conditions.html",
    "macro_housing_real_estate.html",
)
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


def _shot(dest: Path, locator) -> dict[str, Any]:
    locator.screenshot(path=str(dest), type="png")
    png = dest.read_bytes()
    if png[:8] != b"\x89PNG\r\n\x1a\n" or b"IEND" not in png:
        raise RuntimeError(f"{dest.name} is not a finished PNG")
    pw, ph = _png_size(dest)
    return {
        "bytes": len(png),
        "sha256": hashlib.sha256(png).hexdigest(),
        "width": pw,
        "height": ph,
    }


def _state(filename: str, theme: str, locale: str, viewport: str,
           info: dict[str, Any], *, verified_how: str,
           viewport_width: int, fixture: bool | str | None = None,
           force_state: str | None = None, crop: bool = False,
           selector: str | None = None, dpr: float = 2.0,
           viewport_height: int | None = None,
           trigger: str | None = None) -> dict[str, Any]:
    ihdr_w = int(info["width"])
    ihdr_h = int(info["height"])
    css_w = ihdr_w / float(dpr)
    declared = int(round(css_w)) if crop else int(viewport_width)
    return {
        "access": "anonymous",
        "applied_locale": locale,
        "applied_theme": theme,
        "bytes": info["bytes"],
        "captured": True,
        "file": filename,
        "force_state": force_state,
        "height": ihdr_h,
        "width": ihdr_w,
        "locale": locale,
        "sha256": info["sha256"],
        "theme": theme,
        "viewport": viewport,
        "viewport_width": declared,
        "viewport_css_width": css_w,
        "viewport_height": (
            viewport_height if viewport_height is not None
            else (2200 if viewport == "desktop" else 844)
        ),
        "dpr": dpr,
        "crop": crop,
        "selector": selector,
        "verified_how": verified_how,
        "fixture": True if fixture else False,
        "trigger": trigger,
    }


def _gap_state(filename: str, theme: str, locale: str, viewport: str,
               reason: str, viewport_width: int) -> dict[str, Any]:
    return {
        "access": "anonymous",
        "captured": False,
        "reason": reason,
        "file": filename,
        "theme": theme,
        "locale": locale,
        "viewport": viewport,
        "viewport_width": viewport_width,
    }


def _relocated_needles(locale: str) -> tuple[str, ...]:
    return RELOCATED_ZH if locale == "zh" else RELOCATED_EN


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


_CLEARANCE_JS = """(el, arg) => {
    const position = Number(arg.position);
    const vw = window.innerWidth, vh = window.innerHeight;
    const overlap = (a, b) => !(a.right <= b.left || a.left >= b.right
        || a.bottom <= b.top || a.top >= b.bottom);
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
    const maxY = Math.max(0,
        document.documentElement.scrollHeight - window.innerHeight);
    const target = position >= 1 ? maxY : maxY * position;
    window.scrollTo(0, target);
    const reached = window.scrollY || document.documentElement.scrollTop || 0;
    const scrollMatched = Math.abs(reached - target) < 2;
    const maxScrollMatched = Math.abs(reached - maxY) < 2;
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
            ...elBox(node),
        });
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
    const hits = [];
    const scrollUnder = [];
    for (const t of texts) {
        const tv = clipView(t);
        if (!tv) continue;
        for (const f of occluders) {
            if (f.el.contains(t.node)) continue;
            for (const box of f.boxes) {
                const bv = clipView(box);
                if (!bv || !overlap(tv, bv)) continue;
                const rec = {text: t.text, occluder: f.id,
                             occluder_position: f.position};
                if (!isBottomChrome(f) && isTopChrome(f) && position > 0) {
                    scrollUnder.push(rec);
                } else {
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
    if (analystView && !(position > 0 && isTopChrome(analystBox))) {
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
    }
    const fab = document.getElementById('mmb-boot');
    const fabCs = fab ? getComputedStyle(fab) : null;
    const fabBox = fab && fabCs && fabCs.position === 'fixed'
        && fabCs.display !== 'none' ? elBox(fab) : null;
    const atMax = position >= 1;
    const width = window.innerWidth;
    let reason = '';
    if (width <= 768 && occluders.length === 0) reason = 'no_occluders_found';
    const ok = texts.length > 0 && hits.length === 0 && analystHits.length === 0
        && scrollMatched && reason === '';
    return {
        at_max: atMax,
        position,
        width,
        scrollReached: reached,
        scrollTarget: target,
        maxScroll: maxY,
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
        analyst_hits: analystHits,
        stance: stanceBox,
        fab: fabBox,
        mmbBootDisplay: fabCs ? fabCs.display : 'missing',
        analyst_fixed: !!(analyst && getComputedStyle(analyst).position === 'fixed'),
        reason,
        ok,
    };
}"""


def clearance_probe_ok(row: Mapping[str, Any] | None) -> bool:
    """Empty text set, any hit, empty occluders at ≤768, or unmatched scroll → not ok."""
    if not row:
        return False
    texts = int(row.get("text_count") or 0)
    hits = list(row.get("intersections") or [])
    analyst_hits = list(row.get("analyst_hits") or [])
    occluders = list(row.get("occluders") or [])
    width = float(row.get("width") or 0)
    if texts <= 0:
        return False
    if hits or analyst_hits:
        return False
    if width <= 768 and not occluders:
        return False
    if row.get("reason") == "no_occluders_found":
        return False
    if row.get("scrollMatched") is False:
        return False
    if row.get("at_max") and not row.get("maxScrollMatched"):
        return False
    return bool(row.get("ok")) and not row.get("reason")


def _clearance_probe(locator, *, position: float) -> dict[str, Any]:
    row = locator.evaluate(_CLEARANCE_JS, {"position": position})
    row["ok"] = clearance_probe_ok(row)
    return row


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


def _i2_probe(locator) -> dict[str, Any]:
    samples = []
    for position in (0.0, 0.5, 1.0):
        row = _clearance_probe(locator, position=position)
        samples.append(row)
    return {
        "ok": bool(samples) and all(clearance_probe_ok(row) for row in samples),
        "samples": samples,
    }


def main() -> int:
    from playwright.sync_api import sync_playwright

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    status_start = subprocess.check_output(
        ["git", "status", "--short"], cwd=ROOT, text=True).strip()
    tree_clean_start = status_start == ""
    head_start = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    commit_time = subprocess.check_output(
        ["git", "log", "-1", "--format=%cI", head_start],
        cwd=ROOT, text=True).strip()
    generated_at_start = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(
        f"capturing site at head {head_start} tree_clean_start={tree_clean_start}",
        flush=True,
    )

    states: list[dict[str, Any]] = []
    gaps: list[str] = [
        "E5 remains a disclosed gap: the empty-e5 node is a <template> the "
        "client mounts on fragment failure, not a builder-triggerable fixture.",
    ]
    probes: dict[str, Any] = {}
    harness_files: list[Path] = []
    ws_states: dict[str, list[dict[str, Any]]] = {
        page: [] for page in WORKSPACE_PAGES}

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
                    width=1440, height=2200)
                page.wait_for_selector(".mc-read", timeout=15000)
                page.wait_for_selector(".mc-strip", timeout=15000)
                info = _shot(EVIDENCE / name, page.locator("body"))
                page.screenshot(path=str(EVIDENCE / name), type="png",
                                full_page=False)
                png = (EVIDENCE / name).read_bytes()
                info = {
                    "bytes": len(png),
                    "sha256": hashlib.sha256(png).hexdigest(),
                    "width": _png_size(EVIDENCE / name)[0],
                    "height": _png_size(EVIDENCE / name)[1],
                }
                states.append(_state(
                    name, theme, locale, "desktop", info, viewport_width=1440,
                    verified_how="Playwright 1440 first screen dpr=2; eyebrow+H1+Read+chips",
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
                info = _shot(EVIDENCE / name, page.locator("section#rates"))
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
                info = _shot(EVIDENCE / name, page.locator("#mc-p5-frame"))
                states.append(_state(
                    name, theme, locale, "mobile", info, viewport_width=390,
                    verified_how="390 CSS-wide iframe harness; crop to iframe content box",
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
                info = _shot(EVIDENCE / name, page.locator("#mc-p5-frame"))
                states.append(_state(
                    name, theme, locale, "tablet", info, viewport_width=768,
                    viewport_height=844,
                    verified_how="768 iframe crop of #mc-p5-frame; #credit/funding caption",
                    force_state="tablet_768",
                ))
                ctx.close()

            # 15–16 workspace details OPEN on the relocated §5 / B1 block
            for n, theme, locale in (("15", "dark", "en"), ("16", "light", "zh")):
                name = f"{n}-{theme}-{locale}-1440.png"
                print(f"capture {name}", flush=True)
                ctx, page, _ = _open(
                    browser=browser, origin=origin,
                    path="/macro_rates_curves.html", theme=theme, locale=locale,
                    width=1440, height=2800)
                page.wait_for_selector(".mq-implication-text", timeout=15000)
                _open_ribbon_details(page)
                probes[f"copy_{n}"] = _copy_probe(page, _relocated_needles(locale))
                info = _shot(EVIDENCE / name, page.locator(".mq-ribbon"))
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
                info = _shot(EVIDENCE / name, topic)
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
            clear_pages = ("macro_monetary.html",) + WORKSPACE_PAGES
            for page_name in clear_pages:
                for width in (390, 768):
                    for theme, locale in (
                        ("dark", "en"), ("dark", "zh"),
                        ("light", "en"), ("light", "zh"),
                    ):
                        slug = page_name.replace(".html", "")
                        key = f"clear_{slug}_{width}_{theme}_{locale}"
                        print(f"probe clearance {key}", flush=True)
                        wait = ".mc-analyst" if page_name == "macro_monetary.html" else ".mq-suitenav .mc-analyst, .mq-implication-text"
                        ctx, page, frame = _open(
                            browser=browser, origin=origin,
                            path=f"/{page_name}", theme=theme, locale=locale,
                            width=1440, height=900, iframe_width=width)
                        frame.locator(wait).first.wait_for(timeout=15000)
                        loc = frame.locator("html")
                        boot = _clearance_probe(loc, position=0.0)
                        mid = _clearance_probe(loc, position=0.5)
                        mx = _clearance_probe(loc, position=1.0)
                        i2 = _i2_probe(loc)
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
                        i2_name = f"i2-{slug}-{theme}-{locale}-{width}.png"
                        print(f"capture {i2_name}", flush=True)
                        info = _shot(EVIDENCE / i2_name, page.locator("#mc-p5-frame"))
                        dest_states = states if page_name == "macro_monetary.html" else ws_states[page_name]
                        dest_states.append(_state(
                            i2_name, theme, locale,
                            "mobile" if width == 390 else "tablet", info,
                            viewport_width=width,
                            verified_how=f"{page_name} {width} iframe; clearance at 0 / 50% / max",
                            force_state="clearance_i2",
                        ))
                        ctx.close()
            probes["i2_ok"] = bool(i2_ok and clearance_ok)

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
                            info = _shot(dest, page.locator("#mc-p5-frame"))
                        else:
                            page.screenshot(path=str(dest), type="png",
                                            full_page=False)
                            png = dest.read_bytes()
                            info = {
                                "bytes": len(png),
                                "sha256": hashlib.sha256(png).hexdigest(),
                                "width": _png_size(dest)[0],
                                "height": _png_size(dest)[1],
                            }
                        states.append(_state(
                            name, theme, locale, viewport_name, info,
                            viewport_width=width,
                            verified_how="in-memory half-null: read.omitted + ≥2 null chips + E2 housing + E6 credit",
                            fixture=True, force_state="half-null",
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
                            info = _shot(EVIDENCE / name, block)
                            ws_states[page_name].append(_state(
                                name, theme, locale, "desktop", info,
                                viewport_width=1440,
                                verified_how=f"{page_name} ribbon; details {mode}",
                                crop=True, selector=".mq-ribbon",
                                force_state="details_open",
                            ))
                        else:
                            page.screenshot(path=str(EVIDENCE / name), type="png",
                                            full_page=False)
                            png = (EVIDENCE / name).read_bytes()
                            info = {
                                "bytes": len(png),
                                "sha256": hashlib.sha256(png).hexdigest(),
                                "width": _png_size(EVIDENCE / name)[0],
                                "height": _png_size(EVIDENCE / name)[1],
                            }
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
                        info = _shot(EVIDENCE / name, page.locator("#mc-p5-frame"))
                        ws_states[page_name].append(_state(
                            name, theme, locale, "mobile", info, viewport_width=390,
                            verified_how=f"{page_name} 390 iframe; details {mode}",
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
                    info = _shot(EVIDENCE / name, page.locator("#mc-p5-frame"))
                    ws_states[page_name].append(_state(
                        name, theme, locale, "tablet", info, viewport_width=768,
                        viewport_height=844,
                        verified_how=f"{page_name} 768 iframe; first screen",
                        force_state="tablet_768",
                    ))
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
            pages_out.append(_page_entry(page_name, ws_states.get(page_name, [])))

        for page_name, mode, theme, locale in _SKIP_WS_DUP:
            leftover = EVIDENCE / (
                f"ws-{page_name.replace('.html', '')}-"
                f"{mode}-{theme}-{locale}-1440.png"
            )
            leftover.unlink(missing_ok=True)
        (EVIDENCE / "16-light-en-1440.png").unlink(missing_ok=True)

        shas = [
            st["sha256"]
            for page in pages_out
            for st in page["states"]
            if st.get("captured") and st.get("sha256")
        ]
        dups = {sha for sha in shas if shas.count(sha) > 1}
        if dups:
            raise RuntimeError(f"manifest repeats sha256: {sorted(dups)}")

        force_states = sorted({
            str(st.get("force_state"))
            for page in pages_out
            for st in page["states"]
            if st.get("force_state")
        })
        generated_at_end = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        status_end = subprocess.check_output(
            ["git", "status", "--short"], cwd=ROOT, text=True).strip()
        tree_clean_end = status_end == ""
        head_end = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        MANIFEST.write_text(json.dumps({
            "schema": "mastermind.p0_evidence.v2",
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
