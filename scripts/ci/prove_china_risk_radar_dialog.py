#!/usr/bin/env python3
"""Capture immutable proof of the clickable China Risk Radar dialog journey."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import struct
from typing import Any

from playwright.sync_api import sync_playwright

from scripts.capture_page_evidence import serve_site_dir

VIEWPORTS: dict[str, tuple[int, int]] = {
    "desktop": (1440, 900),
    "mobile": (390, 844),
}
LOCALES = ("en", "zh")
THEMES = ("dark", "light")
FORBIDDEN_COPY = (
    "Begin scaling exposure back",
    "回补敞口",
    "risk easing on its own",
    "风险自行回落",
)

APPLY_STATE = """
state => {
  window.__skyDeck = true;
  document.querySelectorAll('.sky-fx').forEach(el => el.remove());
  const root = document.documentElement;
  if (typeof window.setTheme === 'function') window.setTheme(state.theme);
  else root.setAttribute('data-theme', state.theme);
  if (typeof window.setLang === 'function') window.setLang(state.locale);
  else { root.setAttribute('data-lang', state.locale); root.lang = state.locale; }
  document.querySelectorAll('.sky-fx').forEach(el => el.remove());
  return {theme: root.getAttribute('data-theme'), locale: root.getAttribute('data-lang')};
}
"""


def _png_dimensions(payload: bytes) -> tuple[int, int]:
    if payload[:8] == b"\x89PNG\r\n\x1a\n" and payload[12:16] == b"IHDR":
        return tuple(int(value) for value in struct.unpack(">II", payload[16:24]))
    return (0, 0)


def capture_dialog_matrix(
    *,
    site_dir: pathlib.Path,
    output_dir: pathlib.Path,
    candidate_sha: str,
    candidate_tree: str,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cells_dir = output_dir / "dialog_cells"
    cells_dir.mkdir(parents=True, exist_ok=True)
    expected = {
        (viewport, locale, theme)
        for viewport in VIEWPORTS
        for locale in LOCALES
        for theme in THEMES
    }
    records: list[dict[str, Any]] = []

    httpd, port = serve_site_dir(site_dir.resolve())
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for viewport, (width, height) in VIEWPORTS.items():
                    for locale in LOCALES:
                        for theme in THEMES:
                            page = browser.new_page(viewport={"width": width, "height": height})
                            try:
                                page.goto(
                                    f"http://127.0.0.1:{port}/china.html",
                                    wait_until="domcontentloaded",
                                    timeout=60_000,
                                )
                                applied = page.evaluate(
                                    APPLY_STATE,
                                    {"theme": theme, "locale": locale},
                                )
                                if applied != {"theme": theme, "locale": locale}:
                                    raise RuntimeError(f"dialog state mismatch: {applied}")
                                page.wait_for_timeout(700)

                                trigger = page.locator('.cnx-card[onclick*="cnx-dlg-risk"]')
                                if trigger.count() != 1:
                                    raise RuntimeError(
                                        "expected one Risk Radar dialog trigger, "
                                        f"got {trigger.count()}"
                                    )
                                trigger.first.scroll_into_view_if_needed()
                                trigger.first.click()

                                dialog = page.locator("#cnx-dlg-risk")
                                dialog.wait_for(state="visible", timeout=10_000)
                                page.wait_for_timeout(450)
                                if "open" not in (dialog.get_attribute("class") or "").split():
                                    raise RuntimeError(
                                        "Risk Radar dialog is not open after direct click"
                                    )
                                if page.evaluate("document.body.style.overflow") != "hidden":
                                    raise RuntimeError(
                                        "dialog did not lock background scrolling"
                                    )

                                raw = dialog.text_content() or ""
                                unsafe = [value for value in FORBIDDEN_COPY if value in raw]
                                if unsafe:
                                    raise RuntimeError(
                                        f"dialog exposes unsafe recovery copy: {unsafe}"
                                    )

                                title = page.locator("#cnx-dlg-risk-ttl")
                                en_title = title.locator(".l-en")
                                zh_title = title.locator(".l-zh")
                                en_visible = en_title.is_visible()
                                zh_visible = zh_title.is_visible()
                                if en_visible != (locale == "en") or zh_visible != (locale == "zh"):
                                    raise RuntimeError(
                                        "dialog locale visibility mismatch: "
                                        f"locale={locale} en={en_visible} zh={zh_visible}"
                                    )
                                visible_title = (
                                    en_title if locale == "en" else zh_title
                                ).inner_text().strip()
                                if locale == "en" and "pullback risk" not in visible_title.casefold():
                                    raise RuntimeError(
                                        f"English dialog title not visible: {visible_title!r}"
                                    )
                                if locale == "zh" and "回撤风险" not in visible_title:
                                    raise RuntimeError(
                                        f"Chinese dialog title not visible: {visible_title!r}"
                                    )

                                png = page.screenshot(full_page=False)
                                digest = hashlib.sha256(png).hexdigest()
                                relative = pathlib.PurePosixPath("dialog_cells") / f"{digest[:16]}.png"
                                path = output_dir / relative
                                path.write_bytes(png)
                                png_width, png_height = _png_dimensions(png)
                                records.append(
                                    {
                                        "viewport": viewport,
                                        "locale": locale,
                                        "theme": theme,
                                        "file": str(relative),
                                        "sha256": digest,
                                        "bytes": len(png),
                                        "width": png_width,
                                        "height": png_height,
                                        "dialog_visible": True,
                                        "entry_method": "direct_css_click",
                                        "synthetic_key_count": 0,
                                        "tab_discovery_count": 0,
                                        "unsafe_copy_hits": [],
                                    }
                                )
                            finally:
                                page.close()
            finally:
                browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()

    found = {
        (record["viewport"], record["locale"], record["theme"])
        for record in records
    }
    files = {record["file"] for record in records}
    if found != expected or len(records) != 8 or len(files) != 8:
        raise RuntimeError(
            "dialog matrix mismatch: "
            f"found={sorted(found)} records={len(records)} files={len(files)}"
        )
    for record in records:
        path = output_dir / record["file"]
        if not path.is_file():
            raise RuntimeError(f"dialog screenshot missing: {record['file']}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise RuntimeError(
                f"dialog screenshot integrity failure: {record['file']}"
            )

    manifest = {
        "schema": "mastermind.china_risk_radar.dialog_proof.v1",
        "candidate_sha": candidate_sha,
        "candidate_tree": candidate_tree,
        "cells": records,
        "interaction_policy": {
            "entry_method": "direct_css_click",
            "body_character_keystrokes": 0,
            "tab_discovery_count": 0,
        },
    }
    (output_dir / "dialog_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-dir", type=pathlib.Path, required=True)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--candidate-tree", required=True)
    args = parser.parse_args()

    manifest = capture_dialog_matrix(
        site_dir=args.site_dir,
        output_dir=args.output_dir,
        candidate_sha=args.candidate_sha,
        candidate_tree=args.candidate_tree,
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
