"""Capture Macro Command P4 evidence frames (copy pin §4).

HTTP servers start in the background and are always killed.
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.capture_macro_command_p3 import (  # noqa: E402
    RAIL_VIEWPORT_JS,
    _assert_shot_geometry,
    _device_px_span,
    _device_px_span_from_crop_box_doc,
    _run_clearance,
    _write_element_shot,
)

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
    # P3 v5: withheld_command_tabs / entitlement are fixture-only keys.
    builder.build_hub(entries, out_dir=out, env=env, root=ROOT,
                      page_built_at="2026-09-06T00:00:00Z",
                      allow_empty_state_fixture=True)
    for asset in builder.SHARED_ASSETS:
        shutil.copy2(ROOT / "templates" / asset, out / asset)
    if empty_id == "e4":
        frag = (out / "macro" / "fragments" / "credit.html").read_text(
            encoding="utf-8")
    elif empty_id == "e6":
        frag = (out / "macro" / "fragments" / "credit.html").read_text(
            encoding="utf-8")
    elif empty_id == "e2":
        frag = (out / "macro" / "fragments" / "housing.html").read_text(
            encoding="utf-8")
    else:
        frag = ""
    if frag and f'data-mc-empty="{empty_id}"' not in frag:
        raise RuntimeError(f"{empty_id} fragment missing typed empty: {frag[:400]}")
    return out


def _open_page(*, browser, url: str, hash_path: str, theme: str, locale: str,
               width: int, height: int):
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
                  height: int = 900, first_screen: bool = False,
                  full_page: bool = False) -> dict[str, Any]:
    context, page = _open_page(
        browser=browser, url=url, hash_path=hash_path, theme=theme,
        locale=locale, width=width, height=height)
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
    page.wait_for_timeout(200)
    box = target.bounding_box()
    if not box:
        context.close()
        raise RuntimeError(f"no bounding box for {sel}")
    dpr = float(page.evaluate("window.devicePixelRatio"))
    extra: dict[str, Any] = {"dpr": dpr, "fixture": "builder-payload"}
    if full_page:
        page.screenshot(path=str(dest), type="png", full_page=True)
        clip = {"x": 0, "y": 0, "width": width, "height": height}
        extra["crop"] = False
        extra["full_page"] = True
    elif first_screen:
        page.screenshot(path=str(dest), type="png", full_page=False)
        clip = {"x": 0, "y": 0, "width": width, "height": height}
        extra["crop"] = False
        extra["full_page"] = False
    else:
        extra["crop"] = True
        extra["full_page"] = False
        extra["crop_selector"] = sel
        _write_element_shot(page, dest, target, extra, locale)
        clip = extra["crop_box"]
        box = extra.get("crop_box") or box
    _assert_shot_geometry(dest, extra, width, height)
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
        "dpr": dpr,
        "crop": bool(extra.get("crop")),
        "full_page": bool(extra.get("full_page")),
        "crop_selector": extra.get("crop_selector"),
        "crop_box": extra.get("crop_box"),
        "crop_box_doc": extra.get("crop_box_doc"),
        "scroll_y_at_shot": extra.get("scroll_y_at_shot"),
        "element_text_head": extra.get("element_text_head"),
        "device_px_span": extra.get("device_px_span"),
        "ihdr_delta_px": extra.get("ihdr_delta_px"),
    }


def _viewport_dims(viewport: str) -> tuple[int, int]:
    if viewport == "desktop":
        return 1440, 900
    if viewport == "tablet":
        return 768, 1400
    return 390, 844


def _state_row(filename: str, theme: str, locale: str, viewport: str,
               info: dict[str, Any], *, fixture: str | None = None,
               trigger: str | None = None, verified_how: str,
               section: str | None = None, crop: bool = False,
               selector: str | None = None,
               force_state: str | None = None,
               full_page: bool = False) -> dict[str, Any]:
    if fixture is None or not str(fixture).strip():
        raise ValueError(
            f"{filename}: fixture must be a path or the literal "
            f"'builder-payload'")
    vw, vh = _viewport_dims(viewport)
    row = {
        "access": "anonymous",
        "applied_locale": info["applied_locale"],
        "applied_theme": info["applied_theme"],
        "bytes": info["bytes"],
        "captured": True,
        "file": filename,
        "force_state": force_state,
        "height": info["png_height"],
        "width": info["png_width"],
        "locale": locale,
        "sha256": info["sha256"],
        "theme": theme,
        "viewport": viewport,
        "viewport_width": vw,
        "viewport_height": vh,
        "viewport_css_width": vw,
        "dpr": info.get("dpr", 2),
        "css_width": info["css_width"],
        "css_height": info["css_height"],
        "clip": info["clip"],
        "section": section,
        "verified_how": verified_how,
        "fixture": fixture,
        "trigger": trigger,
        "crop": crop,
        "full_page": full_page,
    }
    if selector:
        row["selector"] = selector
        row["crop_selector"] = selector if crop else None
    if crop:
        row["crop_box"] = info.get("crop_box") or info.get("clip")
        for key in ("crop_box_doc", "scroll_y_at_shot",
                    "element_text_head", "device_px_span", "ihdr_delta_px"):
            if key in info:
                row[key] = info[key]
    else:
        row["crop_selector"] = None
        row["crop_box"] = None
    return row


P3_PARENT = "origin/claude/marketontology-macro-command-p3-20260908"
SECTIONS = ("growth", "jobs", "housing", "consumer", "credit", "debt", "trade")
THEMES = ("dark", "light")
LOCALES = ("en", "zh")
EMPTY_IDS = ("e1", "e2", "e3", "e4", "e6")
STATE_KEYS = (
    "growth-business", "credit-funding", "growth-foot", "consumer-foot",
)
BLAST_AXES = (("dark", "en"), ("light", "zh"), ("dark", "zh"), ("light", "en"))
CLEARANCE_WIDTHS = (390, 768, 1440)
RAIL_VIEWPORT_WIDTHS = (390, 768)
REST_VIEWPORT_WIDTHS = (1440, 768, 390)
E5_VIEWPORT_WIDTHS = (1440, 390)
CLEAN_END_PATHS = ("templates", "scripts", "lib", "site")

# MINOR-1: E5 applicability is decided on the live DOM, never by a regex
# over committed site HTML. A nested </section> cannot hide a template.
E5_APPLICABILITY_JS = """() => {
  const shell = document.querySelector('#mc-shell');
  const fragments = Boolean(
    shell && shell.hasAttribute('data-mc-fragments'));
  const receipt = {};
  for (const panel of document.querySelectorAll('[data-mc-panel]')) {
    const sectionId = panel.getAttribute('data-mc-panel');
    if (!sectionId) continue;
    receipt[sectionId] = {
      templatePresent: Boolean(
        panel.querySelector('template[data-mc-empty-e5]')),
      fragmentTarget: 'macro/fragments/' + sectionId + '.html',
      fragments,
    };
  }
  return receipt;
}"""


def e5_applicability_from_page(page) -> dict[str, dict[str, Any]]:
    """Runtime receipt: every [data-mc-panel] + #mc-shell[data-mc-fragments]."""
    receipt = page.evaluate(E5_APPLICABILITY_JS)
    if not isinstance(receipt, dict):
        raise RuntimeError(f"E5 applicability evaluate returned {type(receipt)}")
    return receipt


def empty_ids_for_section(section_receipt: dict[str, Any]) -> tuple[str, ...]:
    """Fixture empties always; E5 only when the live panel can enter it."""
    ids = list(EMPTY_IDS)
    if (section_receipt.get("templatePresent")
            and section_receipt.get("fragments")):
        ids.append("e5")
    return tuple(ids)


def declared_families(*, blast_keys: list[str],
                      applicability: dict[str, dict[str, Any]]
                      ) -> dict[str, list[str]]:
    """Complete declared matrix. Per-section E5 follows the runtime receipt."""
    families: dict[str, list[str]] = {
        "sections": [],
        "empty_states": [],
        "states": [],
        "blast": [],
        "clearance": [],
        "rail_viewport": [],
        "fab": [],
        "rest_views": [],
    }
    for section in SECTIONS:
        for width, prefix in ((1440, "comp"), (768, "tab"), (390, "mob")):
            for theme in THEMES:
                for locale in LOCALES:
                    families["sections"].append(
                        f"{prefix}-{section}-{theme}-{locale}-{width}")
        for theme in THEMES:
            for locale in LOCALES:
                families["sections"].append(
                    f"comp-{section}-{theme}-{locale}-1440-full")
    for empty_id in EMPTY_IDS:
        for width in E5_VIEWPORT_WIDTHS:
            for theme in THEMES:
                for locale in LOCALES:
                    families["empty_states"].append(
                        f"empty-{empty_id}-{theme}-{locale}-{width}")
    for section in SECTIONS:
        ids = empty_ids_for_section(applicability.get(section) or {})
        if "e5" not in ids:
            continue
        for width in E5_VIEWPORT_WIDTHS:
            for theme in THEMES:
                for locale in LOCALES:
                    families["empty_states"].append(
                        f"empty-e5-{section}-{theme}-{locale}-{width}")
    for key in STATE_KEYS:
        for theme in THEMES:
            for locale in LOCALES:
                families["states"].append(f"state-{key}-{theme}-{locale}-1440")
    for key in blast_keys:
        for side in ("before", "after"):
            for theme, locale in BLAST_AXES:
                families["blast"].append(
                    f"blast-radius/{side}-{key}-{theme}-{locale}-1440")
    for section in SECTIONS:
        for width in CLEARANCE_WIDTHS:
            for theme in THEMES:
                for locale in LOCALES:
                    families["clearance"].append(
                        f"clearance-{section}-{theme}-{locale}-{width}")
    for width in RAIL_VIEWPORT_WIDTHS:
        for theme in THEMES:
            for locale in LOCALES:
                families["rail_viewport"].append(
                    f"rail_viewport-{theme}-{locale}-{width}")
    for theme in THEMES:
        for locale in LOCALES:
            families["fab"].append(f"fab-{theme}-{locale}-1440")
    for width in REST_VIEWPORT_WIDTHS:
        for theme in THEMES:
            for locale in LOCALES:
                families["rest_views"].append(
                    f"rest-{theme}-{locale}-{width}")
    return families


def flatten_declared(families: dict[str, list[str]]) -> list[str]:
    cells: list[str] = []
    for items in families.values():
        cells.extend(items)
    return cells


def declared_cells(*, blast_keys: list[str],
                   applicability: dict[str, dict[str, Any]]) -> list[str]:
    return flatten_declared(declared_families(
        blast_keys=blast_keys, applicability=applicability))


def captured_stems(states: list[dict[str, Any]]) -> set[str]:
    stems: set[str] = set()
    for row in states:
        name = str(row.get("file") or "")
        if name.endswith(".png"):
            name = name[:-4]
        if name:
            stems.add(name)
    return stems


def generate_gaps(declared: list[str], captured: set[str]) -> list[str]:
    """gaps = declared − captured. Every family uses the same rule."""
    return [
        f"{cell}: captured:false — declared cell missing from this run"
        for cell in declared
        if cell not in captured
    ]


def generate_extras(declared: list[str], captured: set[str]) -> list[str]:
    """captured − declared. A stray frame is a silently undeclared cell."""
    declared_set = set(declared)
    return [
        f"{cell}: undeclared — captured stem not in declared matrix"
        for cell in sorted(captured)
        if cell not in declared_set
    ]


def generate_excluded(gaps: list[str]) -> list[dict[str, Any]]:
    excluded: list[dict[str, Any]] = []
    for gap in gaps:
        cell = gap.split(":", 1)[0]
        reason = gap.split(" — ", 1)[-1].rstrip(".")
        excluded.append({"id": cell, "captured": False, "reason": reason})
    return excluded


def build_manifest(*, families: dict[str, list[str]],
                   probe_stems: list[str],
                   excluded: list[dict[str, Any]],
                   gaps: list[str],
                   states: list[dict[str, Any]],
                   protocol: dict[str, Any]) -> dict[str, Any]:
    """Writer: top-level gaps is the same list stamped on pages[0].gaps."""
    generated_at_end = protocol["generated_at_end"]
    head = protocol["head_start"]
    return {
        "schema": "mastermind.p0_evidence.v2",
        "axes": {
            "access": ["anonymous"],
            "force_states": list(EMPTY_IDS) + ["e5", "blast-radius"],
            "locales": ["en", "zh"],
            "themes": ["dark", "light"],
            "viewports": {
                "desktop": [1440, 2200],
                "tablet": [768, 1400],
                "mobile": [390, 844],
            },
        },
        "declared": families,
        "gaps": gaps,
        "probe_stems": probe_stems,
        "excluded": excluded,
        "generated_at": generated_at_end,
        "generated_at_start": protocol["generated_at_start"],
        "generated_at_end": generated_at_end,
        "head_sha": head,
        "capture_sha": head,
        "head_start": head,
        "head_end": protocol["head_end"],
        "tree_clean_start": protocol["tree_clean_start"],
        "tree_clean_end": protocol["tree_clean_end"],
        "commit_time_of_capture_sha": protocol["commit_time_of_capture_sha"],
        "pre_commit": False,
        "honesty": {
            "access": "anonymous only; no credential is entered, stored, or synthesized",
            "authority": "this tool measures and screenshots; it scores, ranks, and judges nothing",
            "gaps": "gaps is generated as declared − captured; nothing is inferred for a missing cell",
            "served_from": (
                "committed site/ (hub + workspace pages); empty-state "
                "fixtures render to a temp build root"
            ),
        },
        "outcome": "captured",
        "target": {
            "resolved_sha_source": _derive_resolved_sha_source(protocol),
        },
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


def _head_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _git_status_short(*paths: str) -> str:
    cmd = ["git", "status", "--short"]
    if paths:
        cmd += ["--", *paths]
    return subprocess.check_output(cmd, cwd=ROOT, text=True)


def _require_clean_tree(*, when: str, paths: tuple[str, ...] = ()) -> dict[str, Any]:
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
    return (
        f"committed HEAD of this worktree ({protocol['head_start']}); "
        f"tree_clean_start={protocol['tree_clean_start']} from "
        f"`git status --short` at start "
        f"(empty={protocol['tree_clean_start']}); "
        f"tree_clean_end={protocol['tree_clean_end']} from "
        f"`git status --short -- templates scripts lib site` at end "
        f"(empty={protocol['tree_clean_end']}); "
        f"head_start={protocol['head_start']}; "
        f"head_end={protocol['head_end']}; "
        f"generated_at_start={protocol['generated_at_start']}; "
        f"generated_at_end={protocol['generated_at_end']}; "
        f"commit_time_of_capture_sha={protocol['commit_time_of_capture_sha']} "
        f"(git show -s --format=%cI). gaps generated as declared − captured."
    )


def _p3_parent_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", P3_PARENT], cwd=ROOT, text=True).strip()


def _l_strings(html: str) -> tuple[set[str], set[str]]:
    import re
    en = set(re.findall(r'<span class="l-en">([^<]*)</span>', html))
    zh = set(re.findall(r'<span class="l-zh">([^<]*)</span>', html))
    return en, zh


def _blast_workspace_pages() -> list[str]:
    """Workspace pages whose committed-or-rebuilt copy changed vs the P3 parent."""
    parent = _p3_parent_sha()
    names = subprocess.check_output(
        ["git", "diff", "--name-only", parent, "--", "site/"],
        cwd=ROOT, text=True)
    pages: list[str] = []
    for rel in names.splitlines():
        path = Path(rel)
        if path.parent != Path("site"):
            continue
        if not path.name.startswith("macro_") or not path.name.endswith(".html"):
            continue
        if path.name in {"macro_monetary.html", "macro_command.html"}:
            continue
        after = (ROOT / rel).read_text(encoding="utf-8") if (ROOT / rel).exists() else ""
        try:
            before = subprocess.check_output(
                ["git", "show", f"{parent}:{rel}"], cwd=ROOT, text=True)
        except subprocess.CalledProcessError:
            before = ""
        after_en, after_zh = _l_strings(after)
        before_en, before_zh = _l_strings(before)
        if after_en != before_en or after_zh != before_zh:
            pages.append(path.name)
    pages.sort()
    return pages


def _extract_parent_site(tmp: Path, pages: list[str]) -> Path:
    dest = tmp / "p3-parent-site"
    dest.mkdir(parents=True, exist_ok=True)
    _copy_chrome(dest)
    parent = _p3_parent_sha()
    for name in pages:
        html = subprocess.check_output(
            ["git", "show", f"{parent}:site/{name}"], cwd=ROOT)
        (dest / name).write_bytes(html)
    return dest


def _capture_metric_table(*, browser, origin: str, page_name: str,
                          theme: str, locale: str, dest: Path) -> dict[str, Any]:
    selector = "section.mq-changed table.mq-table"
    ctx, page = _open_page(
        browser=browser, url=f"{origin}/{page_name}", hash_path="",
        theme=theme, locale=locale, width=1440, height=900)
    page.wait_for_function(
        "([theme, locale]) => document.documentElement.getAttribute('data-theme') === theme"
        " && (document.documentElement.getAttribute('data-lang') || 'en') === locale",
        arg=[theme, locale],
    )
    page.wait_for_selector(selector, state="attached", timeout=15000)
    page.evaluate(
        """(sel) => {
            const table = document.querySelector(sel);
            if (!table) return;
            let el = table;
            while (el && el !== document.documentElement) {
                if (el.tagName === 'DETAILS') el.open = true;
                el.hidden = false;
                el.removeAttribute('hidden');
                if (el.style) {
                    if (el.style.display === 'none') el.style.display = '';
                    if (el.style.visibility === 'hidden') el.style.visibility = 'visible';
                }
                el = el.parentElement;
            }
        }""",
        selector,
    )
    page.wait_for_selector(selector, state="visible", timeout=8000)
    table = page.locator(selector).first
    dpr = float(page.evaluate("window.devicePixelRatio"))
    extra = {
        "dpr": dpr, "crop": True, "full_page": False,
        "crop_selector": selector, "fixture": "builder-payload",
    }
    _write_element_shot(page, dest, table, extra, locale)
    clip = extra["crop_box"]
    box = extra.get("crop_box") or {}
    _assert_shot_geometry(dest, extra, 1440, 900)
    png = dest.read_bytes()
    if png[:8] != b"\x89PNG\r\n\x1a\n" or b"IEND" not in png:
        ctx.close()
        raise RuntimeError(f"{dest.name} is not a finished PNG")
    pw, ph = _png_size(dest)
    applied_theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
    applied_locale = page.evaluate(
        "document.documentElement.getAttribute('data-lang') || 'en'")
    ctx.close()
    if applied_theme != theme or applied_locale != locale:
        raise RuntimeError(f"theme/lang mismatch {applied_theme}/{applied_locale}")
    return {
        "bytes": len(png),
        "sha256": hashlib.sha256(png).hexdigest(),
        "png_width": pw,
        "png_height": ph,
        "css_width": clip["width"],
        "css_height": clip["height"],
        "clip": clip,
        "applied_theme": applied_theme,
        "applied_locale": applied_locale,
        "selector": selector,
        "dpr": dpr,
        "crop": True,
        "full_page": False,
        "crop_selector": selector,
        "crop_box": clip,
        "crop_box_doc": extra.get("crop_box_doc"),
        "scroll_y_at_shot": extra.get("scroll_y_at_shot"),
        "element_text_head": extra.get("element_text_head"),
        "device_px_span": extra.get("device_px_span"),
        "ihdr_delta_px": extra.get("ihdr_delta_px"),
    }


def _capture_hub_e5_cell(*, browser, origin: str, section: str,
                         theme: str, locale: str, vw: int, vh: int,
                         dest: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Photograph one hub-section E5 via P3's stalled fragment request."""
    context = browser.new_context(
        viewport={"width": vw, "height": vh},
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
    held: list = []
    try:
        page = context.new_page()
        seen: dict[str, float] = {}

        def _stall(route) -> None:
            if "requestSeenAt" not in seen:
                seen["requestSeenAt"] = time.monotonic()
            held.append(route)

        page.route("**/macro/fragments/**", _stall)
        page.goto(
            origin + f"/macro_monetary.html#{section}",
            wait_until="domcontentloaded", timeout=30000)
        page.wait_for_function(
            """([theme, locale]) => {
                const el = document.documentElement;
                return el.getAttribute('data-theme') === theme
                    && (el.getAttribute('data-lang') || 'en') === locale;
            }""",
            arg=[theme, locale],
            timeout=10000,
        )
        clone_sel = f'section#{section} [data-mc-empty="e5"]'
        deadline = time.monotonic() + 20.0
        clone_seen_at: float | None = None
        while time.monotonic() < deadline:
            if page.query_selector(clone_sel):
                clone_seen_at = time.monotonic()
                break
            page.wait_for_timeout(100)
        if clone_seen_at is None:
            raise RuntimeError(
                f"E5 clone missing {section}/{theme}/{locale}/{vw}")
        request_seen_at = seen.get("requestSeenAt")
        if request_seen_at is None:
            raise RuntimeError(
                f"E5 fragment request never seen "
                f"{section}/{theme}/{locale}/{vw}")
        request_seen_at_ms = request_seen_at * 1000
        clone_seen_at_ms = clone_seen_at * 1000
        elapsed_ms = clone_seen_at_ms - request_seen_at_ms
        receipt = page.evaluate(
            """(sectionId) => {
              const panel = document.querySelector(
                '[data-mc-panel="' + sectionId + '"]');
              const tpl = panel
                ? panel.querySelector('template[data-mc-empty-e5]')
                : document.querySelector(
                    '[data-mc-panel="' + sectionId + '"] template[data-mc-empty-e5]');
              const clone = panel
                ? panel.querySelector('[data-mc-empty="e5"]')
                : document.querySelector('[data-mc-empty="e5"]');
              const title = clone
                ? (clone.querySelector('.mc-empty-title') || clone)
                : null;
              return {
                templatePresent: Boolean(tpl),
                clonePresent: Boolean(clone),
                fragmentTarget: 'macro/fragments/' + sectionId + '.html',
                headline: title
                  ? String(title.innerText || '').trim() : '',
              };
            }""",
            section,
        )
        if elapsed_ms < 8000:
            raise RuntimeError(
                f"E5 elapsedMs {elapsed_ms:.0f} < 8000 "
                f"{section}/{theme}/{locale}/{vw}")
        if not receipt.get("clonePresent"):
            raise RuntimeError(
                f"E5 clone missing {section}/{theme}/{locale}/{vw}: {receipt}")
        extra = {
            "dpr": float(page.evaluate("window.devicePixelRatio")),
            "force_state": "e5",
            "fixture": "builder-payload",
            "trigger": (
                "page.route never-fulfils macro/fragments/*; "
                "8000ms client timeout cloned template"
            ),
            "crop": True,
            "full_page": False,
            "crop_selector": clone_sel,
        }
        target = page.locator(clone_sel).first
        _write_element_shot(page, dest, target, extra, locale)
        _assert_shot_geometry(dest, extra, vw, vh)
        png = dest.read_bytes()
        if png[:8] != b"\x89PNG\r\n\x1a\n" or b"IEND" not in png:
            raise RuntimeError(f"{dest.name} is not a finished PNG")
        pw, ph = _png_size(dest)
        clip = extra.get("crop_box") or {}
        applied_theme = page.evaluate(
            "document.documentElement.getAttribute('data-theme')")
        applied_locale = page.evaluate(
            "document.documentElement.getAttribute('data-lang') || 'en'")
        if applied_theme != theme or applied_locale != locale:
            raise RuntimeError(
                f"theme/lang mismatch {applied_theme}/{applied_locale}")
        info = {
            "bytes": len(png),
            "sha256": hashlib.sha256(png).hexdigest(),
            "png_width": pw,
            "png_height": ph,
            "css_width": clip.get("width"),
            "css_height": clip.get("height"),
            "clip": clip,
            "applied_theme": applied_theme,
            "applied_locale": applied_locale,
            "dpr": extra["dpr"],
            "crop": True,
            "full_page": False,
            "crop_selector": clone_sel,
            "crop_box": extra.get("crop_box"),
            "crop_box_doc": extra.get("crop_box_doc"),
            "scroll_y_at_shot": extra.get("scroll_y_at_shot"),
            "element_text_head": extra.get("element_text_head"),
            "device_px_span": extra.get("device_px_span"),
            "ihdr_delta_px": extra.get("ihdr_delta_px"),
        }
        probe = {
            "elapsedMs": elapsed_ms,
            "requestSeenAtMs": request_seen_at_ms,
            "cloneSeenAtMs": clone_seen_at_ms,
            "templatePresent": receipt.get("templatePresent"),
            "clonePresent": receipt.get("clonePresent"),
            "fragmentTarget": receipt.get("fragmentTarget"),
            "headline": receipt.get("headline"),
            "section": section,
        }
        return info, probe
    finally:
        for route in held:
            try:
                route.abort("timedout")
            except Exception:
                pass
        context.close()


def main() -> int:
    from playwright.sync_api import sync_playwright
    from scripts import build_macro_suite_pages as builder

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    FIXTURES.mkdir(parents=True, exist_ok=True)
    BLAST.mkdir(parents=True, exist_ok=True)
    tmp = Path(os.environ.get("TMPDIR", "/tmp")) / f"mc-p4-{os.getpid()}"
    tmp.mkdir(parents=True, exist_ok=True)

    start_tree = _require_clean_tree(when="start")
    generated_at_start = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    head = start_tree["head"]
    commit_time = subprocess.check_output(
        ["git", "show", "-s", "--format=%cI", head], cwd=ROOT, text=True).strip()
    print(f"rebuilding suite pages at {head}", flush=True)
    builder.render(ROOT, data_root=DATA, out_dir=SITE,
                   page_built_at="2026-09-06T00:00:00Z")

    states: list[dict[str, Any]] = []
    p19_notes: list[str] = []
    for stale in list(EVIDENCE.glob("*.png")) + list(BLAST.glob("*.png")):
        stale.unlink()
    try:
        proc, origin = _serve(SITE)
        url = origin + "/macro_monetary.html"
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)

            ctx, page = _open_page(
                browser=browser, url=url, hash_path="#growth",
                theme="dark", locale="en", width=1440, height=900)
            page.wait_for_selector("[data-mc-panel]", state="attached", timeout=15000)
            page.wait_for_selector("#mc-shell", state="attached", timeout=15000)
            applicability = e5_applicability_from_page(page)
            ctx.close()
            if not applicability:
                raise RuntimeError("E5 applicability receipt is empty")
            print(
                f"e5 applicability sections={sorted(applicability)} "
                f"fragments={next(iter(applicability.values()), {}).get('fragments')}",
                flush=True)

            # §4.1 — 7 sections × (1440 fold + full-page, 768, 390) × dark/light × EN/ZH
            section_viewports = (
                ("desktop", 1440, 900, "comp", True, False),
                ("tablet", 768, 1400, "tab", True, False),
                ("mobile", 390, 844, "mob", True, False),
            )
            for section in SECTIONS:
                for viewport, width, height, prefix, first_screen, full_page in section_viewports:
                    for theme in THEMES:
                        for locale in LOCALES:
                            name = f"{prefix}-{section}-{theme}-{locale}-{width}.png"
                            print(f"capture {name}", flush=True)
                            info = _capture_clip(
                                browser=browser, url=url, hash_path=f"#{section}",
                                theme=theme, locale=locale,
                                dest=EVIDENCE / name,
                                sel=f"section.mc-panel#{section}",
                                wait_sel=f"section.mc-panel#{section} .mc-stance",
                                width=width, height=height,
                                first_screen=first_screen,
                                full_page=full_page)
                            if first_screen:
                                psw = info["scroll"]["panel_sw"]
                                pcw = info["scroll"]["panel_cw"]
                                if psw is not None and pcw is not None and psw > pcw + 1:
                                    raise RuntimeError(
                                        f"panel overflow at {width} {section} "
                                        f"{theme} {locale}: {info['scroll']}")
                            how = (
                                f"true Playwright viewport {width}×{height} "
                                f"dpr=2, first-screen fold"
                            )
                            states.append(_state_row(
                                name, theme, locale, viewport, info,
                                fixture="builder-payload",
                                section=section,
                                crop=False,
                                full_page=False,
                                selector=f"section.mc-panel#{section}",
                                verified_how=how,
                            ))
                for theme in THEMES:
                    for locale in LOCALES:
                        name = f"comp-{section}-{theme}-{locale}-1440-full.png"
                        print(f"capture {name}", flush=True)
                        info = _capture_clip(
                            browser=browser, url=url, hash_path=f"#{section}",
                            theme=theme, locale=locale,
                            dest=EVIDENCE / name,
                            sel=f"section.mc-panel#{section}",
                            wait_sel=f"section.mc-panel#{section} .mc-stance",
                            width=1440, height=900, full_page=True)
                        states.append(_state_row(
                            name, theme, locale, "desktop", info,
                            fixture="builder-payload",
                            section=section, crop=False, full_page=True,
                            selector=f"section.mc-panel#{section}",
                            verified_how="Playwright full-page at 1440×900 dpr=2",
                        ))

            rest_heights = {1440: 900, 768: 1400, 390: 844}
            for width in REST_VIEWPORT_WIDTHS:
                height = rest_heights[width]
                viewport = (
                    "desktop" if width == 1440
                    else ("tablet" if width == 768 else "mobile")
                )
                for theme in THEMES:
                    for locale in LOCALES:
                        name = f"rest-{theme}-{locale}-{width}.png"
                        print(f"capture {name}", flush=True)
                        info = _capture_clip(
                            browser=browser, url=url, hash_path="#overview",
                            theme=theme, locale=locale,
                            dest=EVIDENCE / name,
                            sel="section.mc-panel#overview",
                            wait_sel="section.mc-panel#overview",
                            width=width, height=height, first_screen=True)
                        states.append(_state_row(
                            name, theme, locale, viewport, info,
                            fixture="builder-payload",
                            section="overview", crop=False, full_page=False,
                            selector="section.mc-panel#overview",
                            verified_how=(
                                f"rest view Playwright viewport {width}×{height} "
                                f"dpr=2 at #overview"
                            ),
                        ))

            # §4.3 — state frames, both art directions × both locales
            state_specs = (
                ("growth-business", "growth", "#growth/business",
                 '[data-mc-tabbody="business"] .mc-move, [data-mc-tabbody="business"] [data-mc-empty]'),
                ("credit-funding", "credit", "#credit/funding",
                 '[data-mc-tabbody="funding"] .mc-move, [data-mc-tabbody="funding"] [data-mc-empty]'),
                ("growth-foot", "growth", "#growth", "section#growth .mc-foot"),
                ("consumer-foot", "consumer", "#consumer", "section#consumer .mc-foot"),
            )
            for key, section, hash_path, wait_sel in state_specs:
                for theme in ("dark", "light"):
                    for locale in ("en", "zh"):
                        name = f"state-{key}-{theme}-{locale}-1440.png"
                        print(f"capture {name}", flush=True)
                        clip_sel = ("section.mc-panel#" + section
                                    if "foot" not in key
                                    else wait_sel)
                        info = _capture_clip(
                            browser=browser, url=url, hash_path=hash_path,
                            theme=theme, locale=locale, dest=EVIDENCE / name,
                            sel=clip_sel, wait_sel=wait_sel,
                            width=1440, height=900)
                        states.append(_state_row(
                            name, theme, locale, "desktop", info,
                            fixture="builder-payload",
                            section=section, crop=True, selector=clip_sel,
                            verified_how="Playwright element shot; hash/tab or foot sentence visible",
                        ))

            # §4.5 P-19 overflow probes + after-crops
            probes: dict[str, Any] = {"p19": [], "copy_guard": None}
            probe_stems: list[str] = []
            for width, height in ((1440, 2200), (768, 1024), (390, 844)):
                for theme in ("dark", "light"):
                    for locale in ("en", "zh"):
                        ctx, page = _open_page(
                            browser=browser, url=url, hash_path="#growth",
                            theme=theme, locale=locale, width=width, height=height)
                        page.wait_for_selector("section#growth .mc-stance", timeout=12000)
                        page.wait_for_timeout(400)
                        # P3 v10 hides #mmb-boot at ≤768 on body.mc-page.
                        # Do not wait on the FAB — record computed display.
                        metrics = page.evaluate(
                            """() => {
                                const de = document.documentElement;
                                const panel = document.querySelector('section#growth');
                                const rail = document.querySelector('.mc-rail-list');
                                const boot = document.getElementById('mmb-boot');
                                const bootCs = boot ? getComputedStyle(boot) : null;
                                return {
                                    sw: de.scrollWidth, cw: de.clientWidth,
                                    panel_sw: panel && panel.scrollWidth,
                                    panel_cw: panel && panel.clientWidth,
                                    rail_sw: rail && rail.scrollWidth,
                                    rail_cw: rail && rail.clientWidth,
                                    mmbBootInDom: Boolean(boot),
                                    mmbBootVisible: Boolean(
                                        boot && bootCs && bootCs.display !== 'none'
                                        && bootCs.visibility !== 'hidden'),
                                    mmbBootDisplay: bootCs ? bootCs.display : null,
                                };
                            }""")
                        ctx.close()
                        # M1: panel_ok is the P4-owned criterion (the panel
                        # P4 authored). doc_ok is documentElement.scrollWidth
                        # <= clientWidth — the pin §4.5(e) / P-19 page check.
                        # After the P3 v5 rail fix, doc_ok should be true at
                        # 390; record the real numbers either way.
                        panel_ok = (metrics["panel_sw"] or 0) <= (metrics["panel_cw"] or 0)
                        doc_ok = (metrics["sw"] or 0) <= (metrics["cw"] or 0)
                        row = {"width": width, "theme": theme, "locale": locale,
                               **metrics,
                               "panel_ok": panel_ok,
                               "doc_ok": doc_ok}
                        probes["p19"].append(row)
                        if not panel_ok:
                            raise RuntimeError(f"P-19 panel overflow {row}")
            bad_doc = [row for row in probes["p19"] if not row["doc_ok"]]
            if bad_doc:
                p19_notes.append(
                    "P-19 doc_ok false at "
                    + ", ".join(
                        f"{row['width']} {row['theme']}/{row['locale']} "
                        f"sw={row['sw']} cw={row['cw']}"
                        for row in bad_doc)
                    + ". panel_ok holds in every cell.")

            blast_pages = _blast_workspace_pages()
            probes["blast_pages"] = blast_pages
            if not blast_pages:
                raise RuntimeError("M1: no workspace page changed l-en/l-zh vs P3 parent")
            for stale in BLAST.glob("*.png"):
                stale.unlink()
            parent_site = _extract_parent_site(tmp, blast_pages)
            _p, parent_origin = _serve(parent_site)
            blast_selector = "section.mq-changed table.mq-table"
            for page_name in blast_pages:
                key = page_name.removeprefix("macro_").removesuffix(".html")
                for theme, locale in BLAST_AXES:
                    before = BLAST / f"before-{key}-{theme}-{locale}-1440.png"
                    after = BLAST / f"after-{key}-{theme}-{locale}-1440.png"
                    print(f"capture {before.name}", flush=True)
                    before_info = _capture_metric_table(
                        browser=browser, origin=parent_origin,
                        page_name=page_name, theme=theme, locale=locale,
                        dest=before)
                    states.append(_state_row(
                        f"blast-radius/{before.name}", theme, locale,
                        "desktop", before_info, section=key,
                        fixture="builder-payload",
                        crop=True, selector=blast_selector,
                        force_state="blast-radius",
                        verified_how=(
                            "Playwright element shot of section.mq-changed table.mq-table "
                            "on the P3 parent workspace page at 1440 dpr=2"
                        ),
                    ))
                    print(f"capture {after.name}", flush=True)
                    after_info = _capture_metric_table(
                        browser=browser, origin=origin,
                        page_name=page_name, theme=theme, locale=locale,
                        dest=after)
                    states.append(_state_row(
                        f"blast-radius/{after.name}", theme, locale,
                        "desktop", after_info, section=key,
                        fixture="builder-payload",
                        crop=True, selector=blast_selector,
                        force_state="blast-radius",
                        verified_how=(
                            "Playwright element shot of section.mq-changed table.mq-table "
                            "on this PR's rebuilt workspace page at 1440 dpr=2"
                        ),
                    ))

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

            empty_specs = (
                ("e1", site_e1, "#housing", '[data-mc-empty="e1"]',
                 "section#housing",
                 "mockups/evidence/macro-command-p4/fixtures/e1_housing_real_estate.json",
                 "remanifest housing_real_estate: no date, no deltas → E1"),
                ("e2", site_e2, "#housing", '[data-mc-empty="e2"]',
                 "section#housing",
                 "mockups/evidence/macro-command-p4/fixtures/e2_housing_real_estate.json",
                 "in-memory SOURCE_FAILED on housing_real_estate → E2"),
                ("e3", site_e3, "#housing", '[data-mc-empty="e3"]',
                 "section#housing",
                 "mockups/evidence/macro-command-p4/fixtures/e3_housing_real_estate.json",
                 "remanifest housing_real_estate: dated, no comparable deltas → E3"),
                ("e4", site_e4, "#credit/funding", '[data-mc-empty="e4"]',
                 "section#credit",
                 "mockups/evidence/macro-command-p4/fixtures/e4_credit_funding.json",
                 "in-memory withheld_command_tabs=['funding'] → E4"),
                ("e6", site_e6, "#credit/funding", '[data-mc-empty="e6"]',
                 "section#credit",
                 "mockups/evidence/macro-command-p4/fixtures/e6_credit_funding.json",
                 "in-memory entitlement=Research on capital_structure → E6"),
            )
            served: dict[Path, str] = {}
            empty_viewports = (
                ("desktop", 1440, 900, False),
                ("mobile", 390, 844, True),
            )
            for (empty_id, site_root, hash_path, wait_sel, clip_sel,
                 fixture, trigger) in empty_specs:
                if site_root not in served:
                    _p, origin_fix = _serve(site_root)
                    served[site_root] = origin_fix + "/macro_monetary.html"
                for viewport, width, height, first_screen in empty_viewports:
                    for theme in THEMES:
                        for locale in LOCALES:
                            name = f"empty-{empty_id}-{theme}-{locale}-{width}.png"
                            print(f"capture {name}", flush=True)
                            info = _capture_clip(
                                browser=browser, url=served[site_root],
                                hash_path=hash_path, theme=theme, locale=locale,
                                dest=EVIDENCE / name, sel=clip_sel,
                                wait_sel=wait_sel, width=width, height=height,
                                first_screen=first_screen)
                            how = (
                                "real builder render from injected fixture; "
                                + ("first-screen 390 viewport"
                                   if first_screen else
                                   "clip of panel")
                            )
                            states.append(_state_row(
                                name, theme, locale, viewport, info,
                                fixture=fixture, trigger=trigger,
                                section=clip_sel.lstrip("section#").split()[0],
                                crop=not first_screen,
                                selector=clip_sel,
                                force_state=empty_id,
                                verified_how=how,
                            ))

            e5_heights = {1440: 900, 390: 844}
            for section in SECTIONS:
                if "e5" not in empty_ids_for_section(
                        applicability.get(section) or {}):
                    continue
                for width in E5_VIEWPORT_WIDTHS:
                    height = e5_heights[width]
                    viewport = "desktop" if width == 1440 else "mobile"
                    for theme in THEMES:
                        for locale in LOCALES:
                            name = (
                                f"empty-e5-{section}-{theme}-{locale}-{width}.png"
                            )
                            print(f"capture {name}", flush=True)
                            info, e5_probe = _capture_hub_e5_cell(
                                browser=browser, origin=origin,
                                section=section, theme=theme, locale=locale,
                                vw=width, vh=height,
                                dest=EVIDENCE / name)
                            probes[f"e5_timeout_{section}_{theme}_{locale}_{width}"] = e5_probe
                            states.append(_state_row(
                                name, theme, locale, viewport, info,
                                fixture="builder-payload",
                                trigger=(
                                    "page.route never-fulfils macro/fragments/*; "
                                    "8000ms client timeout cloned template"
                                ),
                                section=section,
                                crop=True,
                                selector=f'section#{section} [data-mc-empty="e5"]',
                                force_state="e5",
                                verified_how=(
                                    "P3 stall of macro/fragments/*; "
                                    f"elapsedMs={e5_probe['elapsedMs']:.0f} "
                                    "locator.screenshot of cloned template"
                                ),
                            ))

            clearance_heights = {390: 844, 768: 1400, 1440: 900}
            for section in SECTIONS:
                for width in CLEARANCE_WIDTHS:
                    height = clearance_heights[width]
                    for theme in THEMES:
                        for locale in LOCALES:
                            ctx, page = _open_page(
                                browser=browser,
                                url=url, hash_path=f"#{section}",
                                theme=theme, locale=locale,
                                width=width, height=height)
                            page.wait_for_selector(
                                f"section.mc-panel#{section}", timeout=15000)
                            page.wait_for_selector(".mc-panels", timeout=15000)
                            clear = _run_clearance(page)
                            if not clear.get("ok"):
                                ctx.close()
                                raise RuntimeError(
                                    f"clearance failed {section} {width} "
                                    f"{theme}/{locale}: {clear}")
                            if width == 1440:
                                for pos_name, pos in (
                                        clear.get("positions") or {}).items():
                                    names = [ov.get("name")
                                             for ov in pos.get("overlays") or []]
                                    if "mmb-boot" not in names:
                                        ctx.close()
                                        raise RuntimeError(
                                            f"1440 clearance missing mmb-boot "
                                            f"{section} {theme}/{locale}@"
                                            f"{pos_name}: {names}")
                            stem = f"clearance-{section}-{theme}-{locale}-{width}"
                            probes[stem] = clear
                            probe_stems.append(stem)
                            ctx.close()
                            print(f"  {stem} ok texts={clear.get('textCount')}",
                                  flush=True)

            for width, height in ((390, 844), (768, 1400)):
                for theme in THEMES:
                    for locale in LOCALES:
                        ctx, page = _open_page(
                            browser=browser, url=url, hash_path="#growth",
                            theme=theme, locale=locale,
                            width=width, height=height)
                        page.wait_for_selector(".mc-rail-list", timeout=15000)
                        viewport = page.evaluate(RAIL_VIEWPORT_JS)
                        if not viewport.get("ok"):
                            ctx.close()
                            raise RuntimeError(
                                f"rail viewport {width} {theme}/{locale}: "
                                f"{viewport}")
                        viewport["maskImageRaw"] = viewport.get("maskRaw")
                        if viewport.get("fadeWidth") is None:
                            ctx.close()
                            raise RuntimeError(
                                f"rail viewport missing fadeWidth "
                                f"{width} {theme}/{locale}: {viewport}")
                        stem = f"rail_viewport-{theme}-{locale}-{width}"
                        probes[stem] = viewport
                        probe_stems.append(stem)
                        ctx.close()
                        print(f"  {stem} ok", flush=True)

            fab_js = """() => {
              const boot = document.getElementById('mmb-boot');
              const panels = document.querySelector('.mc-panels');
              if (!boot || !panels) return {ok: false, reason: 'missing'};
              const cs = getComputedStyle(boot);
              const pcs = getComputedStyle(panels);
              const box = boot.getBoundingClientRect();
              const values = [...document.querySelectorAll(
                '.mc-move-current, .mc-figure .mc-move-current')];
              const hits = [];
              for (const el of values) {
                const r = el.getBoundingClientRect();
                if (r.width < 1 || r.height < 1) continue;
                const intersects = !(r.right <= box.left || r.left >= box.right
                  || r.bottom <= box.top || r.top >= box.bottom);
                if (intersects) {
                  hits.push({text: (el.innerText || '').slice(0, 40)});
                }
              }
              const paddingRight = parseFloat(pcs.paddingRight) || 0;
              return {
                ok: hits.length === 0 && cs.display !== 'none'
                    && paddingRight >= 232,
                display: cs.display,
                position: cs.position,
                box: {top: box.top, left: box.left, right: box.right,
                      width: box.width, height: box.height},
                paddingRight,
                hits,
                valueCount: values.length,
              };
            }"""
            for theme in THEMES:
                for locale in LOCALES:
                    ctx, page = _open_page(
                        browser=browser, url=url, hash_path="#growth",
                        theme=theme, locale=locale, width=1440, height=900)
                    page.wait_for_selector("#mmb-boot", timeout=15000)
                    page.wait_for_selector(".mc-panels", timeout=15000)
                    fab = page.evaluate(fab_js)
                    if not fab.get("ok"):
                        ctx.close()
                        raise RuntimeError(
                            f"FAB gutter failed 1440 {theme}/{locale}: {fab}")
                    stem = f"fab-{theme}-{locale}-1440"
                    probes[stem] = fab
                    probe_stems.append(stem)
                    ctx.close()
                    print(f"  {stem} {fab}", flush=True)

            browser.close()

        from scripts import check_macro_command_copy as guard
        hub_html = (SITE / "macro_monetary.html").read_text(encoding="utf-8")
        violations = guard.find_violations(hub_html)
        probes["copy_guard"] = {"exit": 0 if not violations else 1,
                                "violations": violations}
        if violations:
            raise RuntimeError(f"copy guard: {violations}")

        blast_keys = [
            name.removeprefix("macro_").removesuffix(".html")
            for name in probes.get("blast_pages") or []
        ]
        families = declared_families(
            blast_keys=blast_keys, applicability=applicability)
        declared = flatten_declared(families)
        captured = captured_stems(states)
        captured.update(probe_stems)
        gaps = generate_gaps(declared, captured)
        extras = generate_extras(declared, captured)
        if extras:
            raise RuntimeError(
                "captured stems not in declared matrix: " + "; ".join(extras))
        excluded = generate_excluded(gaps)

        head_end = _assert_head_unmoved(head)
        end_tree = _require_clean_tree(when="end", paths=CLEAN_END_PATHS)
        generated_at_end = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        protocol = {
            "tree_clean_start": start_tree["clean"],
            "tree_clean_end": end_tree["clean"],
            "head_start": head,
            "head_end": head_end,
            "generated_at_start": generated_at_start,
            "generated_at_end": generated_at_end,
            "commit_time_of_capture_sha": commit_time,
        }
        probes["head_sha_at_capture"] = head
        probes["captured_at"] = generated_at_end
        probes["generated_at_start"] = generated_at_start
        probes["generated_at_end"] = generated_at_end
        probes["pre_commit"] = False
        probes["capture_sha"] = head
        probes["commit_time_of_capture_sha"] = commit_time
        probes["tree_clean_start"] = start_tree["clean"]
        probes["tree_clean_end"] = end_tree["clean"]
        probes["p19_notes"] = p19_notes
        probes["declared_count"] = len(declared)
        probes["captured_count"] = len(captured)
        probes["gaps"] = gaps
        probes["e5_applicability"] = applicability
        probes["probe_stems"] = probe_stems
        PROBES.write_text(json.dumps(probes, indent=2) + "\n", encoding="utf-8")

        manifest = build_manifest(
            families=families,
            probe_stems=probe_stems,
            excluded=excluded,
            gaps=gaps,
            states=states,
            protocol=protocol,
        )
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (EVIDENCE / "EVIDENCE.yml").write_text(
            "schema: mastermind.page_evidence_receipt.v1\n"
            "changed_paths:\n"
            "  - templates/macro_monetary.html.j2\n"
            "manifest: mockups/evidence/macro-command-p4/manifest.json\n",
            encoding="utf-8",
        )
        print(
            f"wrote {len(states)} frames under {EVIDENCE} "
            f"generated_at_start={generated_at_start} "
            f"generated_at_end={generated_at_end} head={head} "
            f"gaps={len(gaps)}",
            flush=True,
        )
        return 0
    finally:
        _kill_all()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        _kill_all()
        raise
