"""Capture real Macro Command P3 empty-state frames from the real builder.

E1/E3 travel through ``build_macro_suite_pages.render`` on a remanifested
fixture data root. E4/E6 cannot (snapshot contract is additionalProperties
false) — they are injected on the in-memory entry after ``read_workspace``
and written by ``build_hub``. E5 is a client fetch-timeout and is recorded
``captured: false``. E2 is left as the live #rates capture.

HTTP server is started in the background and always killed.
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
EVIDENCE = ROOT / "mockups" / "evidence" / "macro-command-p3"
FIXTURES = EVIDENCE / "fixtures"
MANIFEST = EVIDENCE / "manifest.json"
ASSETS = (
    "theme.css", "theme.js",
    "macro_suite_boot.js", "macro_suite.css", "macro_suite.js",
    "macro_command.css", "macro_command.js",
    "navigation-refresh.css", "product-nav-icons.css", "nav_market.js",
)


def _remanifest(data_root: Path, workspace_id: str, region: str,
                mutate) -> Path:
    rel = f"workspaces/{workspace_id}/{region}/latest.json"
    body_path = data_root / rel
    snap = json.loads(body_path.read_text(encoding="utf-8"))
    mutate(snap)
    from engine.market_os.macro_workspaces import contract as workspace_contract
    sealed = workspace_contract.finalize(snap)
    raw = json.dumps(sealed, ensure_ascii=False).encode("utf-8")
    body_path.write_bytes(raw)
    manifest_path = data_root / "workspaces" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    key = f"{workspace_id}/{region}"
    manifest["workspaces"][key]["content_sha256"] = sealed["generation"]["content_sha256"]
    manifest["workspaces"][key]["bytes"] = len(raw)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return body_path


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


def _copy_chrome(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name in ASSETS:
        tmpl = ROOT / "templates" / name
        src = tmpl if tmpl.exists() else SITE / name
        if src.exists():
            shutil.copy2(src, out / name)


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
    _remanifest(data_root, "inflation_system", "US", mutate)
    builder.render(ROOT, data_root=data_root, out_dir=out,
                   page_built_at="2026-09-06T00:00:00Z")
    _copy_chrome(out)
    frag = (out / "macro" / "fragments" / "inflation.html").read_text(encoding="utf-8")
    if f'data-mc-empty="{empty_id}"' not in frag:
        raise RuntimeError(f"{empty_id} fragment missing typed empty: {frag[:400]}")
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
                      page_built_at="2026-09-06T00:00:00Z",
                      allow_empty_state_fixture=True)
    for asset in builder.SHARED_ASSETS:
        shutil.copy2(ROOT / "templates" / asset, out / asset)
    if empty_id == "e4":
        frag = (out / "macro" / "fragments" / "money.html").read_text(encoding="utf-8")
    else:
        frag = (out / "macro" / "fragments" / "inflation.html").read_text(encoding="utf-8")
    if f'data-mc-empty="{empty_id}"' not in frag:
        raise RuntimeError(f"{empty_id} fragment missing typed empty: {frag[:400]}")
    return out


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


def _capture_clip(*, browser, url: str, hash_path: str, theme: str, locale: str,
                  empty_sel: str, panel_sel: str, dest: Path,
                  width: int = 1440, height: int = 2200) -> dict[str, Any]:
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
    page.wait_for_selector(empty_sel, timeout=15000)
    empty = page.locator(empty_sel).first
    panel = page.locator(panel_sel).first
    empty_box = empty.bounding_box()
    panel_box = panel.bounding_box()
    if not empty_box or not panel_box:
        context.close()
        raise RuntimeError(f"no bounding box for {empty_sel} / {panel_sel}")
    if empty_box["width"] < 40 or empty_box["height"] < 20:
        context.close()
        raise RuntimeError(f"empty rect too small: {empty_box}")
    # element bounding rect must sit inside the clip (the panel)
    if (empty_box["x"] + 1 < panel_box["x"]
            or empty_box["y"] + 1 < panel_box["y"]
            or empty_box["x"] + empty_box["width"] > panel_box["x"] + panel_box["width"] + 2
            or empty_box["y"] + empty_box["height"] > panel_box["y"] + panel_box["height"] + 2):
        context.close()
        raise RuntimeError(f"empty rect {empty_box} not inside panel {panel_box}")
    text = empty.inner_text()
    if "Empty e" in text:
        context.close()
        raise RuntimeError(f"placeholder copy leaked: {text!r}")
    panel.screenshot(path=str(dest), type="png")
    png = dest.read_bytes()
    if b"IEND" not in png:
        context.close()
        raise RuntimeError(f"{dest.name} missing IEND")
    applied_theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
    applied_locale = page.evaluate(
        "document.documentElement.getAttribute('data-lang') || 'en'")
    context.close()
    # PNG pixel size at 2x is the element's CSS box * 2
    return {
        "bytes": len(png),
        "sha256": hashlib.sha256(png).hexdigest(),
        "empty_box": empty_box,
        "panel_box": panel_box,
        "applied_theme": applied_theme,
        "applied_locale": applied_locale,
        "text": text[:240],
    }


def _capture_viewport(*, browser, url: str, hash_path: str, theme: str,
                      locale: str, dest: Path, width: int, height: int,
                      full_page: bool, wait_sel: str | None = None,
                      scroll_sel: str | None = None) -> dict[str, Any]:
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
    if wait_sel:
        page.wait_for_selector(wait_sel, timeout=15000)
    if scroll_sel:
        page.locator(scroll_sel).first.scroll_into_view_if_needed()
        page.wait_for_timeout(200)
    page.screenshot(path=str(dest), type="png", full_page=full_page)
    png = dest.read_bytes()
    context.close()
    return {
        "bytes": len(png),
        "sha256": hashlib.sha256(png).hexdigest(),
    }


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    # IHDR is 8-byte signature + 4 len + 4 'IHDR' + 4 width + 4 height
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    return width, height


def _upsert_state(manifest: dict[str, Any], filename: str, row: dict[str, Any]) -> None:
    states = manifest["pages"][0]["states"]
    for i, state in enumerate(states):
        if state.get("file") == filename or (
                state.get("force_state") == f"addendum:{filename}"
                and state.get("file") in (filename, None)):
            states[i] = {**state, **row}
            return
    # match captured:false rows that dropped the file
    if row.get("force_state"):
        for i, state in enumerate(states):
            if state.get("force_state") == row["force_state"]:
                states[i] = {**state, **row}
                return
    states.append(row)


def main() -> int:
    from playwright.sync_api import sync_playwright

    tmp = Path(os.environ.get("TMPDIR", "/tmp")) / f"mc-p3-empty-{os.getpid()}"
    tmp.mkdir(parents=True, exist_ok=True)
    servers: list[subprocess.Popen] = []
    try:
        print("building E1 fixture through render()", flush=True)
        site_e1 = _build_json_fixture(tmp, "e1", _mutate_e1)
        print("building E3 fixture through render()", flush=True)
        site_e3 = _build_json_fixture(tmp, "e3", _mutate_e3)

        def _e4(entries):
            for entry in entries:
                if entry["workspace_id"] == "liquidity_central_banks":
                    entry["snapshot"]["withheld_command_tabs"] = ["central_banks"]

        def _e6(entries):
            for entry in entries:
                if entry["workspace_id"] == "inflation_system":
                    entry["snapshot"]["entitlement"] = "Research"

        print("building E4 hub through build_hub()", flush=True)
        site_e4 = _build_memory_hub(tmp, "e4", _e4)
        print("building E6 hub through build_hub()", flush=True)
        site_e6 = _build_memory_hub(tmp, "e6", _e6)

        shots = [
            ("e1", site_e1, "#inflation", "#inflation [data-mc-empty='e1']",
             "#inflation", FIXTURES / "e1_inflation_system.json",
             "Contract-legal inflation_system JSON: no date, no deltas → E1"),
            ("e3", site_e3, "#inflation", "#inflation [data-mc-empty='e3']",
             "#inflation", FIXTURES / "e3_inflation_system.json",
             "Contract-legal inflation_system JSON: dated, no comparable deltas → E3"),
            ("e4", site_e4, "#central_banks", "#money [data-mc-empty='e4']",
             "#money", FIXTURES / "e4_central_banks.json",
             "In-memory withheld_command_tabs=['central_banks'] on liquidity_central_banks → E4"),
            ("e6", site_e6, "#inflation", "#inflation [data-mc-empty='e6']",
             "#inflation", FIXTURES / "e6_inflation_system.json",
             "In-memory entitlement='Research' on inflation_system → E6"),
        ]

        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True, channel="chrome")
            for empty_id, site_dir, hash_path, empty_sel, panel_sel, fixture, trigger in shots:
                proc, origin = _serve(site_dir)
                servers.append(proc)
                try:
                    for theme in ("dark", "light"):
                        dest = EVIDENCE / f"empty-{empty_id}-{theme}.png"
                        print(f"capturing {dest.name}", flush=True)
                        info = _capture_clip(
                            browser=browser,
                            url=f"{origin}/macro_monetary.html",
                            hash_path=hash_path,
                            theme=theme,
                            locale="en",
                            empty_sel=empty_sel,
                            panel_sel=panel_sel,
                            dest=dest,
                        )
                        pw, ph = _png_size(dest)
                        print(
                            f"  {dest.name} {pw}x{ph} {info['bytes']}B "
                            f"empty={info['empty_box']} "
                            f"text={info['text']!r}",
                            flush=True,
                        )
                        _upsert_state(manifest, dest.name, {
                            "access": "anonymous",
                            "applied_locale": info["applied_locale"],
                            "applied_theme": info["applied_theme"],
                            "bytes": info["bytes"],
                            "captured": True,
                            "file": dest.name,
                            "force_state": f"addendum:{dest.name}",
                            "fixture": str(fixture.relative_to(ROOT)),
                            "trigger": trigger,
                            "height": ph,
                            "locale": "en",
                            "sha256": info["sha256"],
                            "theme": theme,
                            "viewport": "desktop",
                            "viewport_height": 2200,
                            "viewport_width": 1440,
                            "width": pw,
                            "empty_box": info["empty_box"],
                            "panel_box": info["panel_box"],
                        })
                finally:
                    _kill(proc)
                    if proc in servers:
                        servers.remove(proc)

            # Production recapture for n5 (768 light rail seam) and n6 (390 dark ZH)
            proc, origin = _serve(SITE)
            servers.append(proc)
            try:
                dest16 = EVIDENCE / "16-light-en-768.png"
                print(f"recapturing {dest16.name}", flush=True)
                info16 = _capture_viewport(
                    browser=browser,
                    url=f"{origin}/macro_monetary.html",
                    hash_path="#overview",
                    theme="light",
                    locale="en",
                    dest=dest16,
                    width=768,
                    height=1024,
                    full_page=True,
                    wait_sel=".mc-rail",
                )
                w16, h16 = _png_size(dest16)
                _upsert_state(manifest, dest16.name, {
                    "access": "anonymous",
                    "applied_locale": "en",
                    "applied_theme": "light",
                    "bytes": info16["bytes"],
                    "captured": True,
                    "file": dest16.name,
                    "force_state": f"addendum:{dest16.name}",
                    "height": h16,
                    "locale": "en",
                    "sha256": info16["sha256"],
                    "theme": "light",
                    "viewport": "desktop",
                    "viewport_height": 1024,
                    "viewport_width": 768,
                    "width": w16,
                })
                dest10 = EVIDENCE / "10-dark-zh-390.png"
                print(f"recapturing {dest10.name}", flush=True)
                info10 = _capture_viewport(
                    browser=browser,
                    url=f"{origin}/macro_monetary.html",
                    hash_path="#overview",
                    theme="dark",
                    locale="zh",
                    dest=dest10,
                    width=390,
                    height=844,
                    full_page=False,
                    wait_sel="#overview .mc-move-row",
                    scroll_sel="#overview .mc-move-list li:nth-child(5)",
                )
                w10, h10 = _png_size(dest10)
                _upsert_state(manifest, dest10.name, {
                    "access": "anonymous",
                    "applied_locale": "zh",
                    "applied_theme": "dark",
                    "bytes": info10["bytes"],
                    "captured": True,
                    "file": dest10.name,
                    "force_state": f"addendum:{dest10.name}",
                    "height": h10,
                    "locale": "zh",
                    "sha256": info10["sha256"],
                    "theme": "dark",
                    "viewport": "mobile",
                    "viewport_height": 844,
                    "viewport_width": 390,
                    "width": w10,
                })
            finally:
                _kill(proc)
                if proc in servers:
                    servers.remove(proc)
            browser.close()

        _upsert_state(manifest, "empty-e5-dark.png", {
            "access": "anonymous",
            "applied_locale": "en",
            "applied_theme": "dark",
            "captured": False,
            "file": None,
            "force_state": "addendum:empty-e5-dark.png",
            "fixture": None,
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
            "viewport": "desktop",
            "viewport_height": 2200,
            "viewport_width": 1440,
        })
        e5 = EVIDENCE / "empty-e5-dark.png"
        if e5.exists():
            e5.unlink()

        manifest["generated_at"] = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {MANIFEST}", flush=True)
        return 0
    finally:
        for proc in servers:
            _kill(proc)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
