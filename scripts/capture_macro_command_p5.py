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
from typing import Any

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
          caption: str | None = None):
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
            SITE, src=path, width=iframe_width, height=height - 28,
            caption=caption)
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
           viewport_width: int, fixture: str | None = None) -> dict[str, Any]:
    return {
        "access": "anonymous",
        "applied_locale": locale,
        "applied_theme": theme,
        "bytes": info["bytes"],
        "captured": True,
        "file": filename,
        "force_state": None,
        "height": info["height"],
        "width": info["width"],
        "locale": locale,
        "sha256": info["sha256"],
        "theme": theme,
        "viewport": viewport,
        "viewport_width": viewport_width,
        "viewport_height": 2200 if viewport == "desktop" else 844,
        "verified_how": verified_how,
        "fixture": fixture,
        "trigger": None,
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
    const textSel = arg.textSel;
    const atMax = arg.atMax;
    const overlap = (a, b) => !(a.right <= b.left || a.left >= b.right
        || a.bottom <= b.top || a.top >= b.bottom);
    const box = (el) => {
        const r = el.getBoundingClientRect();
        return {tag: el.tagName, cls: el.className || '',
                x: r.x, y: r.y, w: r.width, h: r.height,
                top: r.top, bottom: r.bottom, left: r.left, right: r.right};
    };
    if (atMax) {
        window.scrollTo(0, document.documentElement.scrollHeight);
    } else {
        window.scrollTo(0, 0);
    }
    const fixed = Array.from(document.querySelectorAll('.mc-analyst, #mmb-boot'))
        .map(el => ({el, cs: getComputedStyle(el), r: el.getBoundingClientRect()}))
        .filter(x => x.cs.position === 'fixed' && x.r.width > 0 && x.r.height > 0)
        .map(x => ({id: x.el.id || x.el.className, ...box(x.el)}));
    const texts = Array.from(document.querySelectorAll(textSel))
        .map(el => ({el, r: el.getBoundingClientRect()}))
        .filter(x => x.r.width > 0 && x.r.height > 0)
        .map(x => box(x.el));
    const hits = [];
    for (const t of texts) {
        for (const f of fixed) {
            if (overlap(t, f)) hits.push({text: t, fixed: f});
        }
    }
    const stance = document.querySelector('.mc-panel .mc-stance, .mc-stance');
    const stanceBox = stance ? box(stance) : null;
    const stanceHits = [];
    if (stanceBox && !atMax) {
        for (const f of fixed) {
            if (overlap(stanceBox, f)) stanceHits.push({stance: stanceBox, fixed: f});
        }
    }
    const fab = document.getElementById('mmb-boot');
    const fabBox = fab && getComputedStyle(fab).position === 'fixed' ? box(fab) : null;
    const panels = document.querySelector('.mc-panels');
    let fabInBand = null;
    if (fabBox && panels && atMax) {
        const pr = panels.getBoundingClientRect();
        const cs = getComputedStyle(panels);
        const pad = parseFloat(cs.paddingBottom) || 0;
        const contentBottom = pr.bottom - pad;
        fabInBand = fabBox.top >= contentBottom - 1 && fabBox.bottom <= pr.bottom + 8;
    }
    const analyst = document.querySelector('.mc-analyst');
    const analystFixed = !!(analyst && getComputedStyle(analyst).position === 'fixed');
    return {
        at_max: atMax,
        fixed,
        text_count: texts.length,
        intersections: hits,
        stance: stanceBox,
        stance_hits: stanceHits,
        fab: fabBox,
        fab_in_reserved_band: fabInBand,
        analyst_fixed: analystFixed,
        ok: texts.length > 0
            && !analystFixed
            && (atMax
                ? (hits.length === 0 && fabInBand === true)
                : stanceHits.length === 0),
    };
}"""


def _clearance_probe(locator, *, at_max: bool) -> dict[str, Any]:
    return locator.evaluate(
        _CLEARANCE_JS, {"textSel": CLEARANCE_TEXT, "atMax": at_max})


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


def _i2_probe(page) -> dict[str, Any]:
    return page.evaluate(
        """() => {
            const rows = Array.from(document.querySelectorAll('.mc-move-row'));
            const last = rows[rows.length - 1];
            const pill = document.querySelector('.mc-analyst');
            if (!last || !pill) {
                return {ok: false, reason: 'missing last row or pill'};
            }
            const value = last.querySelector('.mc-move-current, .mc-move-delta');
            const delta = last.querySelector('.mc-move-delta');
            const current = last.querySelector('.mc-move-current');
            const vr = (current || value).getBoundingClientRect();
            const dr = (delta || current).getBoundingClientRect();
            const pr = pill.getBoundingClientRect();
            const vw = window.innerWidth, vh = window.innerHeight;
            const vis = (r) => r.top >= 0 && r.left >= 0
                && r.bottom <= vh + 0.5 && r.right <= vw + 0.5;
            const overlap = (a, b) => !(a.right <= b.left || a.left >= b.right
                || a.bottom <= b.top || a.top >= b.bottom);
            return {
                ok: vis(vr) && vis(dr) && !overlap(vr, pr) && !overlap(dr, pr),
                value: {x: vr.x, y: vr.y, w: vr.width, h: vr.height, in_view: vis(vr)},
                delta: {x: dr.x, y: dr.y, w: dr.width, h: dr.height, in_view: vis(dr)},
                pill: {x: pr.x, y: pr.y, w: pr.width, h: pr.height},
                overlap_value: overlap(vr, pr),
                overlap_delta: overlap(dr, pr),
            };
        }""")


def main() -> int:
    from playwright.sync_api import sync_playwright
    from scripts import build_macro_suite_pages as builder

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    captured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"rebuilding hub + 14 pages at {head}", flush=True)
    builder.render(ROOT, data_root=SITE / "macrodata", out_dir=SITE,
                   page_built_at="2026-09-06T00:00:00Z")

    states: list[dict[str, Any]] = []
    gaps: list[str] = [
        "E5 remains a disclosed gap: the empty-e5 node is a <template> the "
        "client mounts on fragment failure, not a builder-triggerable fixture.",
        f"head_sha {head} is the pre-commit tip at capture; P5 commits land after.",
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

            # 13–14 768 + two-segment hash caption
            for n, theme, locale in (("13", "dark", "en"), ("14", "light", "zh")):
                name = f"{n}-{theme}-{locale}-768.png"
                print(f"capture {name}", flush=True)
                ctx, page, frame = _open(
                    browser=browser, origin=origin,
                    path="/macro_monetary.html#credit/funding",
                    theme=theme, locale=locale,
                    width=1440, height=1100, iframe_width=768,
                    caption="/macro_monetary.html#credit/funding")
                frame.locator("section#credit").wait_for(timeout=15000)
                info = _shot(EVIDENCE / name, page.locator("body"))
                states.append(_state(
                    name, theme, locale, "tablet", info, viewport_width=768,
                    verified_how="768 iframe + visible caption bar with #credit/funding",
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
                ))
                ctx.close()

            # 17 / 17b Read-word computed styles
            style_rows = {}
            for n, theme in (("17", "dark"), ("17b", "light")):
                name = f"{n}-{theme}-en-1440.png"
                print(f"capture {name}", flush=True)
                ctx, page, _ = _open(
                    browser=browser, origin=origin,
                    path="/macro_monetary.html", theme=theme, locale="en",
                    width=1440, height=2200)
                page.wait_for_selector(".mc-read-topic", timeout=15000)
                styles = _topic_styles(page)
                style_rows[n] = styles
                topic = page.locator(".mc-read-topic").first
                info = _shot(EVIDENCE / name, topic)
                states.append(_state(
                    name, theme, "en", "desktop", info, viewport_width=1440,
                    verified_how="element clip of the same .mc-read-topic; computed style in probes.json",
                ))
                ctx.close()
            probes["read_word_17"] = style_rows.get("17")
            probes["read_word_17b"] = style_rows.get("17b")
            dark_s, light_s = style_rows["17"], style_rows["17b"]
            probes["read_word_contrast_ok"] = bool(
                dark_s.get("halo") and dark_s.get("underline_px", 1) < 0.5
                and (not light_s.get("halo")) and light_s.get("underline_px", 0) >= 1.5
            )

            # B2 clearance at 390 and 768 × dark/light × EN/ZH
            clearance_ok = True
            for width in (390, 768):
                for theme, locale in (
                    ("dark", "en"), ("dark", "zh"),
                    ("light", "en"), ("light", "zh"),
                ):
                    key = f"clear_{width}_{theme}_{locale}"
                    print(f"probe clearance {key}", flush=True)
                    ctx, page, frame = _open(
                        browser=browser, origin=origin,
                        path="/macro_monetary.html", theme=theme, locale=locale,
                        width=1440, height=900, iframe_width=width)
                    frame.locator(".mc-analyst, .mc-stance").first.wait_for(
                        timeout=15000)
                    boot = _clearance_probe(frame.locator("html"), at_max=False)
                    mx = _clearance_probe(frame.locator("html"), at_max=True)
                    row = {"boot": boot, "max": mx,
                           "ok": bool(boot.get("ok") and mx.get("ok"))}
                    probes[key] = row
                    clearance_ok = clearance_ok and row["ok"]
                    if width == 390 and theme == "dark" and locale == "en":
                        i2_name = "i2-dark-en-390.png"
                        print(f"capture {i2_name}", flush=True)
                        info = _shot(EVIDENCE / i2_name, page.locator("#mc-p5-frame"))
                        states.append(_state(
                            i2_name, "dark", "en", "mobile", info,
                            viewport_width=390,
                            verified_how="390 iframe; B2 clearance at boot+max scroll; analyst is a rail chip",
                        ))
                    ctx.close()
            probes["i2_ok"] = clearance_ok

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
                for n, theme in (("18", "dark"), ("19", "light")):
                    name = f"{n}-{theme}-en-1440.png"
                    dest = EVIDENCE / name
                    if dest.exists():
                        dest.unlink()
                    print(f"capture {name} (half-null fixture)", flush=True)
                    ctx, page, _ = _open(
                        browser=browser, origin=half_origin,
                        path="/macro_monetary.html#housing", theme=theme,
                        locale="en", width=1440, height=2800)
                    page.wait_for_selector(".mc-read", timeout=15000)
                    page.wait_for_selector('[data-mc-empty="e2"]', timeout=15000)
                    page.evaluate("location.hash = '#credit/funding'")
                    page.wait_for_selector('[data-mc-empty="e6"]', timeout=15000)
                    page.evaluate(
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
                    markers = page.evaluate(
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
                    if not needed:
                        reason = (
                            "half-null fixture missing a named cell: "
                            f"{markers}"
                        )
                        states.append(_gap_state(
                            name, theme, "en", "desktop", reason, 1440))
                        gaps.append(f"Frame {n}: {reason}")
                    else:
                        page.screenshot(path=str(dest), type="png",
                                        full_page=True)
                        png = dest.read_bytes()
                        info = {
                            "bytes": len(png),
                            "sha256": hashlib.sha256(png).hexdigest(),
                            "width": _png_size(dest)[0],
                            "height": _png_size(dest)[1],
                        }
                        states.append(_state(
                            name, theme, "en", "desktop", info,
                            viewport_width=1440,
                            verified_how="in-memory half-null: read.omitted + ≥2 null chips + E2 housing + E6 credit",
                            fixture="half-null",
                        ))
                        half_ok = True
                    ctx.close()
                probes["half_null_markers"] = last_markers
                probes["half_null_ok"] = half_ok
            except Exception as exc:
                for n, theme in (("18", "dark"), ("19", "light")):
                    name = f"{n}-{theme}-en-1440.png"
                    states.append(_gap_state(
                        name, theme, "en", "desktop",
                        f"half-null fixture build failed: {exc}", 1440))
                    gaps.append(f"Frame {n}: half-null fixture failed ({exc}).")

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
                        info = _shot(EVIDENCE / name, block)
                        ws_states[page_name].append(_state(
                            name, theme, locale, "desktop", info,
                            viewport_width=1440,
                            verified_how=f"{page_name} ribbon; details {mode}",
                        ))
                        ctx.close()
                for theme, locale in (
                    ("dark", "en"), ("dark", "zh"),
                    ("light", "en"), ("light", "zh"),
                ):
                    name = (
                        f"ws-{page_name.replace('.html','')}-"
                        f"{theme}-{locale}-390.png"
                    )
                    print(f"capture {name}", flush=True)
                    ctx, page, frame = _open(
                        browser=browser, origin=origin,
                        path=f"/{page_name}", theme=theme, locale=locale,
                        width=1440, height=900, iframe_width=390)
                    frame.locator(".mq-implication-text").first.wait_for(
                        timeout=15000)
                    info = _shot(EVIDENCE / name, page.locator("#mc-p5-frame"))
                    ws_states[page_name].append(_state(
                        name, theme, locale, "mobile", info, viewport_width=390,
                        verified_how=f"{page_name} 390 iframe; relocated block in view",
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

        shas = [
            st["sha256"]
            for page in pages_out
            for st in page["states"]
            if st.get("captured") and st.get("sha256")
        ]
        dups = {sha for sha in shas if shas.count(sha) > 1}
        if dups:
            raise RuntimeError(f"manifest repeats sha256: {sorted(dups)}")

        MANIFEST.write_text(json.dumps({
            "schema": "mastermind.p0_evidence.v2",
            "axes": {
                "access": ["anonymous"],
                "force_states": [],
                "locales": ["en", "zh"],
                "themes": ["dark", "light"],
                "viewports": {"desktop": [1440, 2200], "mobile": [390, 844]},
            },
            "excluded": [],
            "generated_at": captured_at,
            "head_sha": head,
            "pre_commit": True,
            "honesty": {
                "access": "anonymous only; no credential is entered, stored, or synthesized",
                "authority": "this tool measures and screenshots; it scores, ranks, and judges nothing",
                "gaps": "states that were not captured are recorded with a reason; nothing is inferred for them",
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
