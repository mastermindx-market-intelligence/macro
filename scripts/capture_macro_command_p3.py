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

CLEARANCE_JS = """() => {
  const last = document.querySelector('#overview .mc-caption')
    || document.querySelector('#overview .mc-move-count')
    || document.querySelector('#overview .mc-move-list li:last-child');
  const pill = document.querySelector('.mc-analyst');
  if (!last || !pill) {
    return {lastBottom: null, pillTop: null, gap: null, clear: false,
            reason: 'missing last or pill'};
  }
  const need = last.getBoundingClientRect().bottom - pill.getBoundingClientRect().top;
  if (need > -2) window.scrollBy(0, Math.ceil(need) + 4);
  const lastBottom = last.getBoundingClientRect().bottom;
  const pillTop = pill.getBoundingClientRect().top;
  const present = lastBottom > 0 && pillTop > 0;
  return {
    lastBottom,
    pillTop,
    gap: pillTop - lastBottom,
    clear: Boolean(present && lastBottom <= pillTop),
    pad: getComputedStyle(document.querySelector('#overview') || last).paddingBottom,
    pillBg: getComputedStyle(pill).backgroundColor,
    lastTag: last.className,
  };
}"""

RAIL_JS = """() => {
  const rail = document.querySelector('.mc-rail');
  const shell = document.querySelector('.mc-shell');
  const stance = document.querySelector('#overview .mc-stance');
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
  return {
    ok: true,
    railBg, shellBg,
    railAlpha: parseAlpha(railBg),
    equal: railBg === shellBg,
    position: getComputedStyle(rail).position,
    stanceText: (stance.innerText || '').slice(0, 160),
  };
}"""


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _head_sha() -> str:
    out = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True)
    return out.strip()


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


def _open_direct(context, url: str, hash_path: str, theme: str, locale: str):
    page = context.new_page()
    page.goto(url + hash_path, wait_until="domcontentloaded", timeout=30000)
    _wait_theme(page, theme, locale)
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


def _row(filename: str, dest: Path, theme: str, locale: str,
         vw: int, vh: int, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    w, h = _png_size(dest)
    row = {
        "access": "anonymous",
        "applied_locale": locale,
        "applied_theme": theme,
        "bytes": dest.stat().st_size,
        "captured": True,
        "file": filename,
        "force_state": (
            None if filename in REST_FRAMES else f"addendum:{filename}"
        ),
        "height": h,
        "locale": locale,
        "sha256": _sha(dest),
        "theme": theme,
        "viewport": "mobile" if vw <= 390 else "desktop",
        "viewport_height": vh,
        "viewport_width": vw,
        "width": w,
    }
    if extra:
        row.update(extra)
    return row


def _upsert(manifest: dict[str, Any], filename: str, row: dict[str, Any]) -> None:
    states = manifest["pages"][0]["states"]
    for i, state in enumerate(states):
        if state.get("file") == filename or state.get("force_state") == f"addendum:{filename}":
            states[i] = {**state, **row}
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


def main() -> int:
    from playwright.sync_api import sync_playwright

    tmp = Path(os.environ.get("TMPDIR", "/tmp")) / f"mc-p3-r3-{os.getpid()}"
    tmp.mkdir(parents=True, exist_ok=True)
    servers: list[subprocess.Popen] = []
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    head = _head_sha()
    probes: dict[str, Any] = {}
    if PROBES.exists():
        probes = json.loads(PROBES.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    try:
        print("building empty-state fixture sites", flush=True)

        def _e1(snap: dict[str, Any]) -> None:
            snap["headline"]["effective_date"] = None
            snap["headline"]["status"] = "ABSENT"
            snap["headline"]["null_reason"] = "NOT_YET_RELEASED"
            snap["changes"]["deltas"] = []
            snap["changes"]["comparability"] = "NO_PRIOR"
            snap["changes"]["status"] = "ABSENT"
            snap["changes"]["null_reason"] = "INSUFFICIENT_HISTORY"

        def _e3(snap: dict[str, Any]) -> None:
            snap["changes"]["deltas"] = []
            snap["changes"]["comparability"] = "NO_PRIOR"
            snap["changes"]["status"] = "ABSENT"
            snap["changes"]["null_reason"] = "INSUFFICIENT_HISTORY"

        site_e1 = _build_json_empty(tmp, "e1", _e1)
        site_e3 = _build_json_empty(tmp, "e3", _e3)
        site_e4 = _build_flag_empty(tmp, "e4_central_banks.json", "e4", "money.html")
        site_e6 = _build_flag_empty(tmp, "e6_inflation_system.json", "e6", "inflation.html")
        site_e3ov = _build_e3_overview(tmp)

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
            ("09-dark-en-390.png", "dark", "en", 390, 844, "#overview", "iframe", None),
            ("10-dark-zh-390.png", "dark", "zh", 390, 844, "#overview", "iframe", None),
            ("11-light-en-390.png", "light", "en", 390, 844, "#overview", "iframe", None),
            ("12-light-zh-390.png", "light", "zh", 390, 844, "#overview", "iframe", None),
            ("13-dark-en-390-end.png", "dark", "en", 390, 844, "#overview", "iframe-end", None),
            ("14-light-zh-390-end.png", "light", "zh", 390, 844, "#overview", "iframe-end", None),
            ("15-dark-en-768.png", "dark", "en", 768, 1024, "#overview", "iframe-full", None),
            ("16-light-en-768.png", "light", "en", 768, 1024, "#overview", "iframe-full", None),
            ("17-dark-en-1440-arrival.png", "dark", "en", 1440, 2200, "#rates", "arrival", None),
            ("18-light-en-1440-arrival.png", "light", "en", 1440, 2200, "#rates", "arrival", None),
            ("19-dark-en-1440-dest-hover.png", "dark", "en", 1440, 2200, "#overview", "hover", None),
            ("20-light-en-1440-dest-hover.png", "light", "en", 1440, 2200, "#overview", "hover", None),
            ("21-dark-en-1440-heading-focus.png", "dark", "en", 1440, 2200, "#overview", "focus", None),
            ("22-light-en-1440-heading-focus.png", "light", "en", 1440, 2200, "#overview", "focus", None),
            ("23-dark-en-1440-money-central-banks.png", "dark", "en", 1440, 2200, "#money/central_banks", "full", None),
            ("24-dark-en-1440-inflation-foot.png", "dark", "en", 1440, 2200, "#inflation", "full", None),
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
                        if kind in ("full",) and hash_path == "#overview" and vw == 1440:
                            html = target.content()
                            if "Every desk reported today" in html:
                                raise RuntimeError(f"{filename} still has the false-green stance")
                            if "Some desks have not reported yet" not in html and locale == "en":
                                raise RuntimeError(f"{filename} missing warn stance")
                        if kind == "iframe-end":
                            target.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
                            target.wait_for_timeout(200)
                            page.screenshot(path=str(dest), type="png", full_page=False)
                        elif kind in ("iframe-full", "iframe"):
                            page.screenshot(path=str(dest), type="png", full_page=False)
                        elif kind == "arrival":
                            target.wait_for_selector("[data-mc-arrival]:not([hidden])", timeout=8000)
                            target.locator("#rates").screenshot(path=str(dest), type="png")
                        elif kind == "hover":
                            card = target.locator("#overview .mc-dest").first
                            card.hover()
                            target.wait_for_timeout(150)
                            card.screenshot(path=str(dest), type="png")
                        elif kind == "focus":
                            heading = target.locator("#overview-h")
                            heading.focus()
                            target.wait_for_timeout(150)
                            heading.screenshot(path=str(dest), type="png")
                        else:
                            page.screenshot(path=str(dest), type="png", full_page=True)
                        _assert_png(dest)
                        _upsert(manifest, filename, _row(filename, dest, theme, locale, vw, vh, extra))
                        print(f"  {filename} {dest.stat().st_size}B {_sha(dest)[:12]}", flush=True)
                    finally:
                        context.close()

                # B1 rail probe + M1 clearance at 390, four theme/lang cells
                for theme, locale in (("dark", "en"), ("dark", "zh"),
                                      ("light", "en"), ("light", "zh")):
                    context = _new_context(browser, theme, locale, 390, 844)
                    try:
                        page = _open_direct(
                            context, origin + "/macro_monetary.html",
                            "#overview", theme, locale)
                        page.wait_for_selector("#overview .mc-caption", timeout=15000)
                        rail = page.evaluate(RAIL_JS)
                        if not rail.get("ok") or rail.get("railAlpha") != 1 or not rail.get("equal"):
                            raise RuntimeError(f"B1 rail probe failed {theme}/{locale}: {rail}")
                        probes[f"rail_{theme}_{locale}"] = rail
                        clear = page.evaluate(CLEARANCE_JS)
                        if clear.get("lastBottom") is None or clear.get("lastBottom") <= 0:
                            raise RuntimeError(f"M1 lastBottom missing/negative {theme}/{locale}: {clear}")
                        if not clear.get("clear"):
                            raise RuntimeError(f"M1 not clear {theme}/{locale}: {clear}")
                        probes[f"clearance_{theme}_{locale}"] = clear
                        print(f"  probe {theme}/{locale} lastBottom={clear['lastBottom']} "
                              f"pillTop={clear['pillTop']} clear={clear['clear']}", flush=True)
                    finally:
                        context.close()

                # 768 rail probe both themes
                for theme, locale in (("dark", "en"), ("light", "en")):
                    context = _new_context(browser, theme, locale, 768, 1024)
                    try:
                        page = _open_direct(
                            context, origin + "/macro_monetary.html",
                            "#overview", theme, locale)
                        page.wait_for_selector(".mc-rail", timeout=15000)
                        rail = page.evaluate(RAIL_JS)
                        if not rail.get("ok") or rail.get("railAlpha") != 1 or not rail.get("equal"):
                            raise RuntimeError(f"B1 768 rail probe failed {theme}: {rail}")
                        probes[f"rail_768_{theme}_{locale}"] = rail
                    finally:
                        context.close()
            finally:
                _kill(proc)
                if proc in servers:
                    servers.remove(proc)

            # E3 overview frames 25/26 from the fixture build
            proc, origin = _serve(site_e3ov)
            servers.append(proc)
            try:
                for filename, theme in (("25-dark-en-1440-e3.png", "dark"),
                                        ("26-light-en-1440-e3.png", "light")):
                    dest = EVIDENCE / filename
                    print(f"capturing {filename}", flush=True)
                    context = _new_context(browser, theme, "en", 1440, 2200)
                    try:
                        page = _open_direct(context, origin + "/macro_monetary.html",
                                            "#overview", theme, "en")
                        if 'data-mc-empty="e3"' not in page.content():
                            raise RuntimeError(f"{filename} is not the E3 overview")
                        page.locator("#overview").screenshot(path=str(dest), type="png")
                        _assert_png(dest)
                        _upsert(manifest, filename, _row(
                            filename, dest, theme, "en", 1440, 2200,
                            {"fixture": "in-memory: hub.changes.entries=[] → E3",
                             "trigger": "Overview figure slot empty; directory untouched"}))
                    finally:
                        context.close()
            finally:
                _kill(proc)
                if proc in servers:
                    servers.remove(proc)

            empty_jobs = [
                ("e1", site_e1, "#inflation", "#inflation [data-mc-empty='e1']",
                 "#inflation", FIXTURES / "e1_inflation_system.json",
                 "Contract-legal inflation_system JSON: no date, no deltas → E1"),
                ("e2", SITE, "#rates", "#rates [data-mc-empty='e2']",
                 "#rates", FIXTURES / "e2_rates_curves.json",
                 "Live #rates workspace context.state is SOURCE_FAILED / STALE_SOURCE"),
                ("e3", site_e3, "#inflation", "#inflation [data-mc-empty='e3']",
                 "#inflation", FIXTURES / "e3_inflation_system.json",
                 "Contract-legal inflation_system JSON: dated, no comparable deltas → E3"),
                ("e4", site_e4, "#central_banks", "#money [data-mc-empty='e4']",
                 "#money", FIXTURES / "e4_central_banks.json",
                 " --empty-state-fixture e4_central_banks.json → withheld_command_tabs"),
                ("e6", site_e6, "#inflation", "#inflation [data-mc-empty='e6']",
                 "#inflation", FIXTURES / "e6_inflation_system.json",
                 "--empty-state-fixture e6_inflation_system.json → entitlement=Research"),
            ]
            for empty_id, site_dir, hash_path, empty_sel, panel_sel, fixture, trigger in empty_jobs:
                proc, origin = _serve(site_dir)
                servers.append(proc)
                try:
                    for theme in ("dark", "light"):
                        dest = EVIDENCE / f"empty-{empty_id}-{theme}.png"
                        print(f"capturing {dest.name}", flush=True)
                        context = _new_context(browser, theme, "en", 1440, 2200)
                        try:
                            page = _open_direct(
                                context, origin + "/macro_monetary.html",
                                hash_path, theme, "en")
                            page.wait_for_selector(empty_sel, timeout=15000)
                            # Arrival chrome is a different frame (17/18). Hide
                            # it here so an empty-slot clip is not a byte copy
                            # of the deep-link arrival crop.
                            page.evaluate(
                                """() => {
                                  document.querySelectorAll('[data-mc-arrival]')
                                    .forEach((el) => { el.hidden = true; });
                                }""")
                            page.locator(panel_sel).first.screenshot(
                                path=str(dest), type="png")
                            _assert_png(dest)
                            text = page.locator(empty_sel).first.inner_text()
                            if "Empty e" in text:
                                raise RuntimeError(f"placeholder leaked: {text!r}")
                            if "Each row shows the last two readings" in page.locator(panel_sel).first.inner_text():
                                raise RuntimeError(f"{dest.name} still prints the row caption")
                            _upsert(manifest, dest.name, _row(
                                dest.name, dest, theme, "en", 1440, 2200,
                                {"fixture": str(fixture.relative_to(ROOT)),
                                 "trigger": trigger}))
                        finally:
                            context.close()
                finally:
                    _kill(proc)
                    if proc in servers:
                        servers.remove(proc)

            browser.close()

        _upsert(manifest, "empty-e5-dark.png", {
            "access": "anonymous",
            "applied_locale": "en",
            "applied_theme": "dark",
            "bytes": None,
            "captured": False,
            "file": None,
            "sha256": None,
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

        # Distinct-frame sha check
        by_sha: dict[str, list[str]] = {}
        for state in manifest["pages"][0]["states"]:
            if state.get("captured") and state.get("sha256") and state.get("file"):
                by_sha.setdefault(state["sha256"], []).append(state["file"])
        dupes = {sha: names for sha, names in by_sha.items() if len(names) > 1}
        if dupes:
            raise RuntimeError(f"duplicate evidence blobs: {dupes}")

        manifest["generated_at"] = generated_at
        manifest.setdefault("target", {})
        manifest["target"]["resolved_sha_or_none"] = head
        manifest["target"]["resolved_sha_source"] = (
            f"pre-commit HEAD of this worktree ({head}); the capture ran on "
            "this working tree after the r3 CSS/builder edits and one "
            "scripts/build_macro_suite_pages.py rebuild"
        )
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        probes["generated_at"] = generated_at
        probes["resolved_sha_or_none"] = head
        PROBES.write_text(json.dumps(probes, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {MANIFEST} generated_at={generated_at} head={head}", flush=True)
        return 0
    finally:
        for proc in servers:
            _kill(proc)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
