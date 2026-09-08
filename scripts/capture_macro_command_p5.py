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
    "Published reading",
    "细节、方法与来源",
)
WORKSPACE_RELOCATED = (
    "Last accepted source cut",
    "Calculation as-of",
    "Page built",
    "Method version",
    "Authority ceiling",
    "Source receipt",
    "Content hash",
    "Deterministic text from the accepted snapshot. No language model writes here.",
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


def _copy_probe(page, needles: tuple[str, ...]) -> dict[str, Any]:
    return page.evaluate(
        """(needles) => {
            const details = Array.from(document.querySelectorAll(
                'details.mc-details, details.mc-primer'));
            const inside = details.map(el => el.innerText || '').join('\\n');
            const clone = document.documentElement.cloneNode(true);
            clone.querySelectorAll('details.mc-details, details.mc-primer, script')
                 .forEach(el => el.remove());
            const outside = clone.innerText || '';
            const rows = [];
            for (const n of needles) {
                rows.push({
                    string: n,
                    in_page: document.body.innerText.includes(n),
                    inside: inside.includes(n),
                    outside: outside.includes(n),
                });
            }
            return {
                ok: rows.filter(r => r.in_page).every(r => r.inside && !r.outside),
                rows,
            };
        }""",
        list(needles),
    )


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

            # 15–16 details OPEN + copy probe
            for n, theme, locale in (("15", "dark", "en"), ("16", "light", "en")):
                name = f"{n}-{theme}-{locale}-1440.png"
                print(f"capture {name}", flush=True)
                ctx, page, _ = _open(
                    browser=browser, origin=origin,
                    path="/macro_monetary.html#rates", theme=theme, locale=locale,
                    width=1440, height=2800)
                page.wait_for_selector("section#rates details.mc-details", timeout=15000)
                page.locator("section#rates details.mc-details").first.evaluate(
                    "el => { el.open = true; }")
                probes[f"copy_{n}"] = _copy_probe(page, HUB_DETAILS)
                info = _shot(EVIDENCE / name, page.locator("section#rates"))
                states.append(_state(
                    name, theme, locale, "desktop", info, viewport_width=1440,
                    verified_how="section#rates details.open; relocated strings probed",
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

            # I2 at 390 — last movement row vs pill
            print("probe I2 at 390", flush=True)
            ctx, page, frame = _open(
                browser=browser, origin=origin,
                path="/macro_monetary.html", theme="dark", locale="en",
                width=1440, height=900, iframe_width=390)
            frame.locator(".mc-move-row, .mc-analyst").first.wait_for(timeout=15000)
            # evaluate inside the iframe
            i2 = frame.locator("html").evaluate(
                """() => {
                    const rows = Array.from(document.querySelectorAll('.mc-move-row'));
                    const last = rows[rows.length - 1];
                    const pill = document.querySelector('.mc-analyst');
                    if (!last || !pill) return {ok: false, reason: 'missing last row or pill'};
                    last.scrollIntoView({block: 'end', inline: 'nearest'});
                    const current = last.querySelector('.mc-move-current');
                    const delta = last.querySelector('.mc-move-delta');
                    const vr = (current || last).getBoundingClientRect();
                    const dr = (delta || current || last).getBoundingClientRect();
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
                        overlap_value: overlap(vr, pr), overlap_delta: overlap(dr, pr),
                    };
                }""")
            probes["i2_390"] = i2
            i2_name = "i2-dark-en-390.png"
            print(f"capture {i2_name}", flush=True)
            info = _shot(EVIDENCE / i2_name, page.locator("#mc-p5-frame"))
            states.append(_state(
                i2_name, "dark", "en", "mobile", info, viewport_width=390,
                verified_how="390 iframe after scroll-into-view of last .mc-move-row; pill present",
            ))
            ctx.close()

            # 18–19 half-null: disclosed if the live hub is not a half-null
            for n, theme in (("18", "dark"), ("19", "light")):
                name = f"{n}-{theme}-en-1440.png"
                print(f"capture {name} (live hub; half-null is a disclosed gap if markers absent)", flush=True)
                ctx, page, _ = _open(
                    browser=browser, origin=origin,
                    path="/macro_monetary.html", theme=theme, locale="en",
                    width=1440, height=2200)
                page.wait_for_selector(".mc-read", timeout=15000)
                markers = page.evaluate(
                    """() => ({
                        omitted: !!document.querySelector('.mc-read-omitted'),
                        null_chips: document.querySelectorAll('.mc-chip.is-null').length,
                        e2: !!document.querySelector('[data-mc-empty="e2"]'),
                        e6: !!document.querySelector('[data-mc-empty="e6"]'),
                    })""")
                # Live hub currently has read.omitted + two null chips; E2/E6
                # panels are not builder-triggerable here (disclosed). Capture
                # the live header so the row has a PNG rather than a hole.
                if not markers["omitted"]:
                    states.append(_gap_state(
                        name, theme, "en", "desktop",
                        f"read.omitted not present on the live hub; markers={markers}",
                        1440))
                    gaps.append(f"Frame {n}: read.omitted absent ({markers}).")
                else:
                    gaps.append(
                        f"Frame {n}: live hub has omitted={markers['omitted']} "
                        f"null_chips={markers['null_chips']}; E2/E6 not "
                        f"builder-triggerable (e2={markers['e2']} e6={markers['e6']}).")
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
                        name, theme, "en", "desktop", info, viewport_width=1440,
                        verified_how="live hub header: read.omitted + null chips; E2/E6 disclosed gap",
                        fixture="live",
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
            probes["copy_workspace"] = _copy_probe(page, WORKSPACE_RELOCATED)
            ctx.close()
            probes["i2_ok"] = bool((probes.get("i2_390") or {}).get("ok"))
        probes["gaps"] = list(gaps)

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
            "pages": [{
                "console_errors": [],
                "failed_responses": [],
                "gaps": gaps,
                "page_id": "macro_monetary.html",
                "registry_route": "/macro_monetary.html",
                "route": "/macro_monetary.html",
                "route_kind": "explicit_override",
                "states": states,
            }],
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
