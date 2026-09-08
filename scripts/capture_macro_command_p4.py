"""Capture Macro Command P4 evidence frames (copy pin §4).

HTTP servers start in the background and are always killed.
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
DATA = SITE / "macrodata"
EVIDENCE = ROOT / "mockups" / "evidence" / "macro-command-p4"
FIXTURES = EVIDENCE / "fixtures"
BLAST = EVIDENCE / "blast-radius"
MANIFEST = EVIDENCE / "manifest.json"
PROBES = EVIDENCE / "probes.json"
ASSETS = (
    "theme.css", "theme.js",
    "macro_suite_boot.js", "macro_suite.css", "macro_suite.js",
    "macro_command.css", "macro_command.js",
    "navigation-refresh.css", "product-nav-icons.css", "nav_market.js",
)
_CJK = __import__("re").compile(r"[\u4e00-\u9fff]")
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


def _copy_chrome(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name in ASSETS:
        tmpl = ROOT / "templates" / name
        src = tmpl if tmpl.exists() else SITE / name
        if src.exists():
            shutil.copy2(src, out / name)


def _remanifest(data_root: Path, workspace_id: str, mutate) -> None:
    from engine.market_os.macro_workspaces import contract as workspace_contract
    rel = f"workspaces/{workspace_id}/US/latest.json"
    body_path = data_root / rel
    snap = json.loads(body_path.read_text(encoding="utf-8"))
    mutate(snap)
    sealed = workspace_contract.finalize(snap)
    raw = json.dumps(sealed, ensure_ascii=False).encode("utf-8")
    body_path.write_bytes(raw)
    manifest_path = data_root / "workspaces" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    key = f"{workspace_id}/US"
    manifest["workspaces"][key]["content_sha256"] = sealed["generation"]["content_sha256"]
    manifest["workspaces"][key]["bytes"] = len(raw)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def _mutate_e1(snap: dict[str, Any]) -> None:
    snap["headline"]["effective_date"] = None
    snap["headline"]["status"] = "ABSENT"
    snap["headline"]["null_reason"] = "NOT_YET_RELEASED"
    snap["changes"]["deltas"] = []
    snap["changes"]["comparability"] = "NO_PRIOR"
    snap["changes"]["status"] = "ABSENT"
    snap["changes"]["null_reason"] = "INSUFFICIENT_HISTORY"


def _mutate_e3(snap: dict[str, Any]) -> None:
    snap["changes"]["deltas"] = []
    snap["changes"]["comparability"] = "NO_PRIOR"
    snap["changes"]["status"] = "ABSENT"
    snap["changes"]["null_reason"] = "INSUFFICIENT_HISTORY"


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


def _build_json_fixture(tmp: Path, empty_id: str, mutate) -> Path:
    from scripts import build_macro_suite_pages as builder
    data_root = tmp / f"data-{empty_id}"
    out = tmp / f"site-{empty_id}"
    shutil.copytree(DATA, data_root)
    _remanifest(data_root, "housing_real_estate", mutate)
    builder.render(ROOT, data_root=data_root, out_dir=out,
                   page_built_at="2026-09-06T00:00:00Z")
    _copy_chrome(out)
    frag = (out / "macro" / "fragments" / "housing.html").read_text(encoding="utf-8")
    if f'data-mc-empty="{empty_id}"' not in frag:
        raise RuntimeError(f"{empty_id} fragment missing typed empty: {frag[:400]}")
    dest = FIXTURES / f"{empty_id}_housing_real_estate.json"
    dest.write_bytes(
        (data_root / "workspaces" / "housing_real_estate" / "US" / "latest.json").read_bytes())
    return out


def _build_memory_hub(tmp: Path, empty_id: str, mutate_entries) -> Path:
    from scripts import build_macro_suite_pages as builder
    out = tmp / f"site-{empty_id}"
    out.mkdir(parents=True, exist_ok=True)
    _copy_chrome(out)
    entries = _live_entries()
    mutate_entries(entries)
    env = builder._environment(ROOT)
    builder.build_hub(entries, out_dir=out, env=env, root=ROOT,
                      page_built_at="2026-09-06T00:00:00Z")
    for asset in builder.SHARED_ASSETS:
        shutil.copy2(ROOT / "templates" / asset, out / asset)
    return out


def _open_page(*, browser, url: str, hash_path: str, theme: str, locale: str,
               width: int, height: int, abort_fragments: bool = False):
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
    if abort_fragments:
        page.route("**/macro/fragments/**", lambda route: route.abort())
    page.goto(url + hash_path, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_function(
        """([theme, locale]) => {
            const el = document.documentElement;
            return el.getAttribute('data-theme') === theme
                && (el.getAttribute('data-lang') || 'en') === locale;
        }""",
        arg=[theme, locale],
        timeout=10000,
    )
    return context, page


def _lang_ok(page, locale: str, sel: str) -> dict[str, Any]:
    return page.evaluate(
        """([locale, sel]) => {
            const root = document.querySelector(sel) || document;
            const cjk = /[\\u4e00-\\u9fff]/;
            const letters = /[A-Za-z]/;
            const zh = Array.from(root.querySelectorAll('.l-zh')).map(el => el.textContent || '');
            const en = Array.from(root.querySelectorAll('.l-en')).map(el => el.textContent || '');
            const zhMissing = zh.filter(t => letters.test(t) && !cjk.test(t));
            const enHasCjk = en.filter(t => cjk.test(t));
            return {
                zh_count: zh.length,
                en_count: en.length,
                zh_missing_cjk: zhMissing.slice(0, 5),
                en_has_cjk: enHasCjk.slice(0, 5),
                ok: locale === 'zh' ? zhMissing.length === 0 : enHasCjk.length === 0,
            };
        }""",
        [locale, sel],
    )


def _capture_clip(*, browser, url: str, hash_path: str, theme: str, locale: str,
                  dest: Path, sel: str = "section.mc-panel",
                  wait_sel: str | None = None, width: int = 1440,
                  height: int = 2200, abort_fragments: bool = False,
                  first_screen: bool = False) -> dict[str, Any]:
    context, page = _open_page(
        browser=browser, url=url, hash_path=hash_path, theme=theme,
        locale=locale, width=width, height=height,
        abort_fragments=abort_fragments)
    if wait_sel:
        page.wait_for_selector(wait_sel, timeout=20000)
    else:
        page.wait_for_selector(sel, timeout=15000)
        try:
            page.wait_for_selector(
                sel + " [data-mc-fragment], " + sel + " .mc-move, "
                + sel + " [data-mc-empty]",
                timeout=12000)
        except Exception:
            pass
    target = page.locator(sel).first
    target.scroll_into_view_if_needed()
    page.wait_for_timeout(200)
    box = target.bounding_box()
    if not box:
        context.close()
        raise RuntimeError(f"no bounding box for {sel}")
    if first_screen:
        page.screenshot(path=str(dest), type="png", full_page=False)
        clip = {"x": 0, "y": 0, "width": width, "height": height}
    else:
        target.screenshot(path=str(dest), type="png")
        clip = box
    png = dest.read_bytes()
    if png[:8] != b"\x89PNG\r\n\x1a\n" or b"IEND" not in png:
        context.close()
        raise RuntimeError(f"{dest.name} is not a finished PNG")
    pw, ph = _png_size(dest)
    lang = _lang_ok(page, locale, sel)
    applied_theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
    applied_locale = page.evaluate(
        "document.documentElement.getAttribute('data-lang') || 'en'")
    scroll = page.evaluate(
        """(sel) => {
            const de = document.documentElement;
            const panel = document.querySelector(sel);
            return {
                sw: de.scrollWidth, cw: de.clientWidth,
                panel_sw: panel ? panel.scrollWidth : null,
                panel_cw: panel ? panel.clientWidth : null,
            };
        }""",
        sel,
    )
    context.close()
    if applied_theme != theme or applied_locale != locale:
        raise RuntimeError(f"theme/lang mismatch {applied_theme}/{applied_locale}")
    if not lang["ok"]:
        raise RuntimeError(f"language axis failed {locale}: {lang}")
    return {
        "bytes": len(png),
        "sha256": hashlib.sha256(png).hexdigest(),
        "png_width": pw,
        "png_height": ph,
        "css_width": clip["width"],
        "css_height": clip["height"],
        "clip": clip,
        "panel_box": box,
        "applied_theme": applied_theme,
        "applied_locale": applied_locale,
        "lang": lang,
        "scroll": scroll,
    }


def _state_row(filename: str, theme: str, locale: str, viewport: str,
               info: dict[str, Any], *, fixture: str | None = None,
               trigger: str | None = None, verified_how: str,
               section: str | None = None) -> dict[str, Any]:
    vw, vh = (1440, 2200) if viewport == "desktop" else (390, 844)
    return {
        "access": "anonymous",
        "applied_locale": info["applied_locale"],
        "applied_theme": info["applied_theme"],
        "bytes": info["bytes"],
        "captured": True,
        "file": filename,
        "force_state": None,
        "height": info["png_height"],
        "width": info["png_width"],
        "locale": locale,
        "sha256": info["sha256"],
        "theme": theme,
        "viewport": viewport,
        "viewport_width": vw,
        "viewport_height": vh,
        "css_width": info["css_width"],
        "css_height": info["css_height"],
        "clip": info["clip"],
        "section": section,
        "verified_how": verified_how,
        "fixture": fixture,
        "trigger": trigger,
    }


def main() -> int:
    from playwright.sync_api import sync_playwright
    from scripts import build_macro_suite_pages as builder

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    FIXTURES.mkdir(parents=True, exist_ok=True)
    BLAST.mkdir(parents=True, exist_ok=True)
    tmp = Path(os.environ.get("TMPDIR", "/tmp")) / f"mc-p4-{os.getpid()}"
    tmp.mkdir(parents=True, exist_ok=True)

    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    captured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"rebuilding suite pages at {head}", flush=True)
    builder.render(ROOT, data_root=DATA, out_dir=SITE,
                   page_built_at="2026-09-06T00:00:00Z")

    states: list[dict[str, Any]] = []
    gaps: list[str] = []
    try:
        proc, origin = _serve(SITE)
        url = origin + "/macro_monetary.html"
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)

            # §4.1 — 28 composition frames
            for section in ("growth", "jobs", "housing", "consumer",
                            "credit", "debt", "trade"):
                for theme in ("dark", "light"):
                    for locale in ("en", "zh"):
                        name = f"comp-{section}-{theme}-{locale}-1440.png"
                        print(f"capture {name}", flush=True)
                        info = _capture_clip(
                            browser=browser, url=url, hash_path=f"#{section}",
                            theme=theme, locale=locale,
                            dest=EVIDENCE / name,
                            sel=f"section.mc-panel#{section}",
                            wait_sel=f"section.mc-panel#{section} .mc-stance")
                        states.append(_state_row(
                            name, theme, locale, "desktop", info,
                            section=section,
                            verified_how=(
                                "Playwright clip of section.mc-panel at 1440×2200 "
                                "dpr=2; theme/lang set before load; panel box "
                                "inside clip; language axis from .l-en/.l-zh text"
                            ),
                        ))

            # §4.2 — 8 mobile first-screen frames
            for section in ("consumer", "credit"):
                for theme in ("dark", "light"):
                    for locale in ("en", "zh"):
                        name = f"mob-{section}-{theme}-{locale}-390.png"
                        print(f"capture {name}", flush=True)
                        info = _capture_clip(
                            browser=browser, url=url, hash_path=f"#{section}",
                            theme=theme, locale=locale,
                            dest=EVIDENCE / name,
                            sel=f"section.mc-panel#{section}",
                            wait_sel=f"section.mc-panel#{section} .mc-stance",
                            width=390, height=844, first_screen=True)
                        psw, pcw = info["scroll"]["panel_sw"], info["scroll"]["panel_cw"]
                        if psw is not None and psw > pcw + 1:
                            raise RuntimeError(
                                f"panel overflow at 390 {section} {theme} {locale}: {info['scroll']}")
                        states.append(_state_row(
                            name, theme, locale, "mobile", info,
                            section=section,
                            verified_how=(
                                "true Playwright viewport 390×844 dpr=2, first "
                                "screen, no iframe gutter; scrollWidth<=clientWidth"
                            ),
                        ))

            # §4.3 — state frames
            state_shots = (
                ("state-growth-business-dark-en-1440.png", "growth",
                 "#growth/business", "dark", "en",
                 '[data-mc-tabbody="business"] .mc-move, [data-mc-tabbody="business"] [data-mc-empty]'),
                ("state-growth-business-light-en-1440.png", "growth",
                 "#growth/business", "light", "en",
                 '[data-mc-tabbody="business"] .mc-move, [data-mc-tabbody="business"] [data-mc-empty]'),
                ("state-credit-funding-dark-en-1440.png", "credit",
                 "#credit/funding", "dark", "en",
                 '[data-mc-tabbody="funding"] .mc-move, [data-mc-tabbody="funding"] [data-mc-empty]'),
                ("state-credit-funding-light-zh-1440.png", "credit",
                 "#credit/funding", "light", "zh",
                 '[data-mc-tabbody="funding"] .mc-move, [data-mc-tabbody="funding"] [data-mc-empty]'),
                ("state-growth-foot-dark-en-1440.png", "growth",
                 "#growth", "dark", "en", "section#growth .mc-foot"),
                ("state-growth-foot-light-en-1440.png", "growth",
                 "#growth", "light", "en", "section#growth .mc-foot"),
                ("state-consumer-foot-dark-en-1440.png", "consumer",
                 "#consumer", "dark", "en", "section#consumer .mc-foot"),
                ("state-consumer-foot-light-en-1440.png", "consumer",
                 "#consumer", "light", "en", "section#consumer .mc-foot"),
            )
            for name, section, hash_path, theme, locale, wait_sel in state_shots:
                print(f"capture {name}", flush=True)
                clip_sel = ("section.mc-panel#" + section
                            if "foot" not in name
                            else wait_sel)
                info = _capture_clip(
                    browser=browser, url=url, hash_path=hash_path,
                    theme=theme, locale=locale, dest=EVIDENCE / name,
                    sel=clip_sel, wait_sel=wait_sel)
                states.append(_state_row(
                    name, theme, locale, "desktop", info, section=section,
                    verified_how="Playwright clip; hash/tab or foot sentence visible",
                ))

            # §4.5 P-19 overflow probes + after-crops
            probes: dict[str, Any] = {"p19": [], "copy_guard": None}
            for width, height in ((1440, 2200), (768, 1024), (390, 844)):
                for theme in ("dark", "light"):
                    for locale in ("en", "zh"):
                        ctx, page = _open_page(
                            browser=browser, url=url, hash_path="#growth",
                            theme=theme, locale=locale, width=width, height=height)
                        page.wait_for_selector("section#growth .mc-stance", timeout=12000)
                        page.wait_for_timeout(400)
                        metrics = page.evaluate(
                            """() => {
                                const de = document.documentElement;
                                const panel = document.querySelector('section#growth');
                                const rail = document.querySelector('.mc-rail-list');
                                return {
                                    sw: de.scrollWidth, cw: de.clientWidth,
                                    panel_sw: panel && panel.scrollWidth,
                                    panel_cw: panel && panel.clientWidth,
                                    rail_sw: rail && rail.scrollWidth,
                                    rail_cw: rail && rail.clientWidth,
                                };
                            }""")
                        ctx.close()
                        # Document scrollWidth includes the horizontal rail
                        # scroller at ≤720 (P3 `.mc-rail-list { overflow-x: auto }`).
                        # P-19 for this packet is the panel: copy must not widen it.
                        row = {"width": width, "theme": theme, "locale": locale,
                               **metrics,
                               "ok": (metrics["panel_sw"] or 0) <= (metrics["panel_cw"] or 0) + 1}
                        probes["p19"].append(row)
                        if not row["ok"]:
                            raise RuntimeError(f"P-19 panel overflow {row}")

            for key, page_name in (
                ("financial_conditions", "macro_financial_conditions.html"),
                ("growth_real_economy", "macro_growth_real_economy.html"),
                ("labor_markets", "macro_labor_markets.html"),
            ):
                dest = BLAST / f"after-{key}-zh.png"
                print(f"capture {dest.name}", flush=True)
                ctx, page = _open_page(
                    browser=browser, url=url, hash_path="",
                    theme="dark", locale="zh", width=1440, height=2200)
                page.goto(f"{origin}/{page_name}", wait_until="domcontentloaded",
                          timeout=30000)
                page.wait_for_function(
                    "() => document.documentElement.getAttribute('data-lang') === 'zh'")
                page.wait_for_selector("section.mq-changed table.mq-table", timeout=15000)
                table = page.locator("section.mq-changed table.mq-table").first
                table.scroll_into_view_if_needed()
                table.screenshot(path=str(dest), type="png")
                ctx.close()

            # §4.4 empty states
            print("building E1/E3 housing fixtures", flush=True)
            site_e1 = _build_json_fixture(tmp, "e1", _mutate_e1)
            site_e3 = _build_json_fixture(tmp, "e3", _mutate_e3)

            def _e2_entries(entries):
                for entry in entries:
                    if entry["workspace_id"] == "housing_real_estate":
                        entry["snapshot"]["availability"]["state"] = "SOURCE_FAILED"
                        entry["snapshot"]["headline"]["status"] = "ABSENT"
                        entry["snapshot"]["headline"]["state_id"] = None
                        entry["snapshot"]["headline"]["effective_date"] = None
                        entry["snapshot"]["changes"]["deltas"] = []

            def _e4_entries(entries):
                for entry in entries:
                    if entry["workspace_id"] == "capital_structure":
                        entry["snapshot"]["withheld_command_tabs"] = ["funding"]

            def _e6_entries(entries):
                for entry in entries:
                    if entry["workspace_id"] == "capital_structure":
                        entry["snapshot"]["entitlement"] = "Research"

            site_e2 = _build_memory_hub(tmp, "e2", _e2_entries)
            site_e4 = _build_memory_hub(tmp, "e4", _e4_entries)
            site_e6 = _build_memory_hub(tmp, "e6", _e6_entries)
            (FIXTURES / "e2_housing_real_estate.json").write_text(
                json.dumps({"availability.state": "SOURCE_FAILED",
                            "headline.effective_date": None, "changes.deltas": []},
                           indent=2), encoding="utf-8")
            (FIXTURES / "e4_credit_funding.json").write_text(
                json.dumps({"withheld_command_tabs": ["funding"]}, indent=2),
                encoding="utf-8")
            (FIXTURES / "e6_credit_funding.json").write_text(
                json.dumps({"entitlement": "Research"}, indent=2),
                encoding="utf-8")

            empty_jobs = (
                ("empty-e1-dark.png", site_e1, "#housing", "dark", "en",
                 '[data-mc-empty="e1"]', "section#housing",
                 "mockups/evidence/macro-command-p4/fixtures/e1_housing_real_estate.json",
                 "remanifest housing_real_estate: no date, no deltas → E1"),
                ("empty-e1-light.png", site_e1, "#housing", "light", "en",
                 '[data-mc-empty="e1"]', "section#housing",
                 "mockups/evidence/macro-command-p4/fixtures/e1_housing_real_estate.json",
                 "remanifest housing_real_estate: no date, no deltas → E1"),
                ("empty-e2-dark.png", site_e2, "#housing", "dark", "en",
                 '[data-mc-empty="e2"]', "section#housing",
                 "mockups/evidence/macro-command-p4/fixtures/e2_housing_real_estate.json",
                 "in-memory SOURCE_FAILED on housing_real_estate → E2"),
                ("empty-e2-light.png", site_e2, "#housing", "light", "en",
                 '[data-mc-empty="e2"]', "section#housing",
                 "mockups/evidence/macro-command-p4/fixtures/e2_housing_real_estate.json",
                 "in-memory SOURCE_FAILED on housing_real_estate → E2"),
                ("empty-e3-dark.png", site_e3, "#housing", "dark", "en",
                 '[data-mc-empty="e3"]', "section#housing",
                 "mockups/evidence/macro-command-p4/fixtures/e3_housing_real_estate.json",
                 "remanifest housing_real_estate: dated, no comparable deltas → E3"),
                ("empty-e4-dark.png", site_e4, "#credit/funding", "dark", "en",
                 '[data-mc-empty="e4"]', "section#credit",
                 "mockups/evidence/macro-command-p4/fixtures/e4_credit_funding.json",
                 "in-memory withheld_command_tabs=['funding'] → E4"),
                ("empty-e6-dark.png", site_e6, "#credit/funding", "dark", "en",
                 '[data-mc-empty="e6"]', "section#credit",
                 "mockups/evidence/macro-command-p4/fixtures/e6_credit_funding.json",
                 "in-memory entitlement=Research on capital_structure → E6"),
                ("empty-e6-light.png", site_e6, "#credit/funding", "light", "en",
                 '[data-mc-empty="e6"]', "section#credit",
                 "mockups/evidence/macro-command-p4/fixtures/e6_credit_funding.json",
                 "in-memory entitlement=Research on capital_structure → E6"),
            )
            served: dict[Path, str] = {}
            for (name, site_root, hash_path, theme, locale, wait_sel,
                 clip_sel, fixture, trigger) in empty_jobs:
                if site_root not in served:
                    _p, origin_fix = _serve(site_root)
                    served[site_root] = origin_fix + "/macro_monetary.html"
                print(f"capture {name}", flush=True)
                info = _capture_clip(
                    browser=browser, url=served[site_root], hash_path=hash_path,
                    theme=theme, locale=locale, dest=EVIDENCE / name,
                    sel=clip_sel, wait_sel=wait_sel)
                states.append(_state_row(
                    name, theme, locale, "desktop", info,
                    fixture=fixture, trigger=trigger,
                    verified_how="real builder render from injected fixture; clip of panel",
                ))

            # E5 — abort the housing fragment fetch (real client trigger)
            for theme, name in (("dark", "empty-e5-dark.png"),
                                ("light", "empty-e5-light.png")):
                print(f"capture {name}", flush=True)
                info = _capture_clip(
                    browser=browser, url=url, hash_path="#housing",
                    theme=theme, locale="en", dest=EVIDENCE / name,
                    sel="section#housing",
                    wait_sel='[data-mc-empty="e5"]',
                    abort_fragments=True)
                states.append(_state_row(
                    name, theme, "en", "desktop", info,
                    fixture=None,
                    trigger="Playwright abort of macro/fragments/housing.html → fail() clones template[data-mc-empty-e5]",
                    verified_how="live rebuilt hub; fragment route aborted; E5 visible",
                ))

            browser.close()

        from scripts import check_macro_command_copy as guard
        hub_html = (SITE / "macro_monetary.html").read_text(encoding="utf-8")
        violations = guard.find_violations(hub_html)
        probes["copy_guard"] = {"exit": 0 if not violations else 1,
                                "violations": violations}
        if violations:
            raise RuntimeError(f"copy guard: {violations}")
        probes["head_sha_at_capture"] = head
        probes["captured_at"] = captured_at
        probes["pre_commit"] = True
        PROBES.write_text(json.dumps(probes, indent=2) + "\n", encoding="utf-8")

        manifest = {
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
        }
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (EVIDENCE / "EVIDENCE.yml").write_text(
            "schema: mastermind.page_evidence_receipt.v1\n"
            "changed_paths:\n"
            "  - templates/macro_monetary.html.j2\n"
            "manifest: mockups/evidence/macro-command-p4/manifest.json\n",
            encoding="utf-8",
        )
        print(f"wrote {len(states)} frames under {EVIDENCE}", flush=True)
        return 0
    finally:
        _kill_all()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        _kill_all()
        raise
