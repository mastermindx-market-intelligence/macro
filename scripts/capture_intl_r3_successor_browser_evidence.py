#!/usr/bin/env python3
"""Capture and bind the International Markets R3 repair browser evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup
from PIL import Image
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_REL = Path("mockups/refs/institutionalize/intl/reference-r3.html")
ARTIFACT = ROOT / ARTIFACT_REL
STOCKS_REL = Path("site/intl_stocks.html")
STOCKS = ROOT / STOCKS_REL
EVIDENCE = ROOT / "mockups/refs/reference_integrity/intl-vnext-20260924"
PROOF = EVIDENCE / "proposal-r3-successor-browser-proof.json"
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "mobile": {"width": 390, "height": 844},
}
HORIZONS = ["1m", "3m", "6m", "12m", "ytd"]
COUNTRIES = ["JP", "KR", "TW", "IN", "AU", "GB", "EZ"]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *args: object) -> None:
        return


@contextmanager
def static_server(root: Path) -> Iterator[str]:
    handler = partial(QuietHandler, directory=str(root))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha256(commit: str, path: Path) -> str:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path.as_posix()}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return hashlib.sha256(completed.stdout).hexdigest()


def image_metadata(path: Path) -> dict[str, int]:
    with Image.open(path) as image:
        grayscale = image.convert("L")
        low, high = grayscale.getextrema()
        return {
            "width": image.width,
            "height": image.height,
            "paint_dynamic_range": int(high - low),
        }


def parse_rgb(value: str) -> tuple[float, float, float]:
    numbers = [float(part) for part in re.findall(r"[0-9.]+", value)[:3]]
    if len(numbers) != 3:
        raise ValueError(f"Unsupported RGB color: {value!r}")
    if value.strip().startswith("color(srgb"):
        return tuple(numbers)  # type: ignore[return-value]
    return tuple(number / 255.0 for number in numbers)  # type: ignore[return-value]


def luminance(rgb: tuple[float, float, float]) -> float:
    def channel(value: float) -> float:
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (channel(value) for value in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: str, background: str) -> float:
    light_a = luminance(parse_rgb(foreground))
    light_b = luminance(parse_rgb(background))
    high, low = max(light_a, light_b), min(light_a, light_b)
    return round((high + 0.05) / (low + 0.05), 2)


def assert_clean(page: Page, telemetry: dict[str, list[str]], label: str) -> None:
    page.wait_for_timeout(60)
    if telemetry["console_errors"]:
        raise AssertionError(f"{label}: console errors: {telemetry['console_errors']}")
    if telemetry["request_failures"]:
        raise AssertionError(f"{label}: request failures: {telemetry['request_failures']}")
    if telemetry["external_requests"]:
        raise AssertionError(f"{label}: external requests: {telemetry['external_requests']}")


def new_page(browser: Browser, viewport: str) -> tuple[BrowserContext, Page, dict[str, list[str]]]:
    context = browser.new_context(
        viewport=VIEWPORTS[viewport],
        device_scale_factor=1,
        locale="en-US",
        reduced_motion="reduce",
    )
    page = context.new_page()
    telemetry: dict[str, list[str]] = {
        "console_errors": [],
        "request_failures": [],
        "external_requests": [],
    }

    def on_console(message: Any) -> None:
        if message.type == "error":
            telemetry["console_errors"].append(message.text)

    def on_page_error(error: Any) -> None:
        telemetry["console_errors"].append(f"pageerror: {error}")

    def on_request_failed(request: Any) -> None:
        telemetry["request_failures"].append(f"{request.url}: {request.failure or 'failed'}")

    def on_request(request: Any) -> None:
        parsed = urlparse(request.url)
        if parsed.scheme in {"http", "https"} and parsed.hostname not in {"127.0.0.1", "localhost"}:
            telemetry["external_requests"].append(request.url)

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    page.on("requestfailed", on_request_failed)
    page.on("request", on_request)
    return context, page, telemetry


def dimensions(page: Page) -> dict[str, int]:
    return page.evaluate(
        """() => ({
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          scrollHeight: document.documentElement.scrollHeight,
          actCount: document.querySelectorAll('section.act').length
        })"""
    )


def screenshot(
    page: Page,
    filename: str,
    *,
    full_page: bool = True,
    selector: str | None = None,
) -> tuple[str, dict[str, int]]:
    path = EVIDENCE / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    if selector:
        page.locator(selector).screenshot(path=str(path), animations="disabled")
    else:
        page.screenshot(path=str(path), full_page=full_page, animations="disabled")
    meta = image_metadata(path)
    return sha256(path), meta


def load_reference(
    page: Page,
    reference_url: str,
    *,
    theme: str,
    locale: str,
    direct_initial_locale: bool = False,
) -> None:
    target_url = reference_url
    if direct_initial_locale:
        target_url = f"{reference_url}?lang={locale}&theme={theme}"
    page.goto(target_url, wait_until="load")
    page.locator(f'[data-theme-button="{theme}"]').click()
    if not direct_initial_locale:
        page.locator(f'[data-lang-button="{locale}"]').click()
    page.wait_for_timeout(50)
    state = page.evaluate(
        """() => ({
          theme: document.documentElement.dataset.theme,
          locale: document.documentElement.dataset.lang,
          themePressed: document.querySelector('[data-theme-button][aria-pressed="true"]')?.dataset.themeButton,
          localePressed: document.querySelector('[data-lang-button][aria-pressed="true"]')?.dataset.langButton
        })"""
    )
    if state != {
        "theme": theme,
        "locale": locale,
        "themePressed": theme,
        "localePressed": locale,
    }:
        raise AssertionError(f"Reference control mismatch: {state}")


def capture_reference_default(
    browser: Browser,
    reference_url: str,
    viewport: str,
    theme: str,
    locale: str,
) -> dict[str, Any]:
    context, page, telemetry = new_page(browser, viewport)
    try:
        load_reference(page, reference_url, theme=theme, locale=locale)
        dims = dimensions(page)
        expected_width = VIEWPORTS[viewport]["width"]
        if dims["scrollWidth"] != expected_width or dims["clientWidth"] != expected_width:
            raise AssertionError(f"default-{viewport}-{theme}-{locale}: overflow {dims}")
        filename = f"proposal-r3-successor-{viewport}-{theme}-{locale}.png"
        digest, meta = screenshot(page, filename)
        assert_clean(page, telemetry, filename)
        print(f"captured {filename}", flush=True)
        return {
            "kind": "r3-successor-default",
            "viewport": viewport,
            "theme": theme,
            "locale": locale,
            "file": filename,
            "sha256": digest,
            "dimensions": dims,
            "console_errors": telemetry["console_errors"],
            "request_failures": telemetry["request_failures"],
            "image_dimensions": {"width": meta["width"], "height": meta["height"]},
            "paint_dynamic_range": meta["paint_dynamic_range"],
        }
    finally:
        context.close()


def capture_country(
    browser: Browser,
    reference_url: str,
    country: str,
    theme: str,
    locale: str,
) -> dict[str, Any]:
    context, page, telemetry = new_page(browser, "desktop")
    try:
        load_reference(page, reference_url, theme=theme, locale=locale)
        tab = page.locator(f'[data-country-tab="{country}"]')
        tab.click()
        selected_panel_visible = page.locator(f"#country-{country}").is_visible()
        if not selected_panel_visible or tab.get_attribute("aria-selected") != "true":
            raise AssertionError(f"Country {country} did not activate")
        inspector = page.locator("#country-inspector")
        page.evaluate("""() => {
          const node=document.querySelector('#country-inspector');
          const absoluteTop=window.scrollY + node.getBoundingClientRect().top;
          window.scrollTo(0, Math.max(0, absoluteTop - 116));
        }""")
        page.wait_for_timeout(20)
        inspector_top = inspector.evaluate("node => node.getBoundingClientRect().top")
        sticky_bottom = page.evaluate("""() => Math.max(
          ...[...document.querySelectorAll('.product-shell,.act-jump')].map(node => {
            const s=getComputedStyle(node); return s.position === 'sticky' ? node.getBoundingClientRect().bottom : 0;
          })
        )""")
        if inspector_top < sticky_bottom + 4:
            raise AssertionError(
                f"Inspector clipped by sticky chrome: top={inspector_top}, sticky={sticky_bottom}"
            )
        filename = f"proposal-r3-successor-country-{country.lower()}-{theme}-{locale}.png"
        digest, meta = screenshot(page, filename, selector="#country-inspector")
        tab.focus()
        page.keyboard.press("ArrowRight")
        keyboard_next = page.locator('[data-country-tab][aria-selected="true"]').get_attribute(
            "data-country-tab"
        )
        assert_clean(page, telemetry, filename)
        print(f"captured {filename}", flush=True)
        return {
            "kind": "r3-successor-country",
            "viewport": "desktop",
            "theme": theme,
            "locale": locale,
            "country": country,
            "keyboard_next": keyboard_next,
            "selected_panel_visible": selected_panel_visible,
            "inspector_top": inspector_top,
            "sticky_bottom": sticky_bottom,
            "file": filename,
            "sha256": digest,
            "dimensions": dimensions(page),
            "console_errors": telemetry["console_errors"],
            "request_failures": telemetry["request_failures"],
            "image_dimensions": {"width": meta["width"], "height": meta["height"]},
            "paint_dynamic_range": meta["paint_dynamic_range"],
        }
    finally:
        context.close()


def capture_horizon(
    browser: Browser,
    reference_url: str,
    viewport: str,
    theme: str,
    locale: str,
    horizon: str,
) -> dict[str, Any]:
    context, page, telemetry = new_page(browser, viewport)
    try:
        load_reference(page, reference_url, theme=theme, locale=locale)
        value = page.locator('[data-performance-market="KR"] [data-value="usd"]')
        before = value.inner_text()
        page.locator(f'[data-horizon="{horizon}"]').click()
        after = value.inner_text()
        if page.locator(f'[data-horizon="{horizon}"]').get_attribute("aria-pressed") != "true":
            raise AssertionError(f"Horizon {horizon} did not activate")
        dims = dimensions(page)
        expected_width = VIEWPORTS[viewport]["width"]
        if dims["scrollWidth"] != expected_width:
            raise AssertionError(f"Horizon overflow: {dims}")
        filename = f"proposal-r3-successor-{viewport}-{theme}-{locale}-horizon-{horizon}.png"
        digest, meta = screenshot(page, filename)
        assert_clean(page, telemetry, filename)
        print(f"captured {filename}", flush=True)
        return {
            "kind": "r3-successor-horizon",
            "viewport": viewport,
            "theme": theme,
            "locale": locale,
            "horizon": horizon,
            "before": before,
            "after": after,
            "file": filename,
            "sha256": digest,
            "dimensions": dims,
            "console_errors": telemetry["console_errors"],
            "request_failures": telemetry["request_failures"],
            "image_dimensions": {"width": meta["width"], "height": meta["height"]},
            "paint_dynamic_range": meta["paint_dynamic_range"],
        }
    finally:
        context.close()


def capture_fixed_paths(browser: Browser, reference_url: str) -> dict[str, Any]:
    context, page, telemetry = new_page(browser, "desktop")
    try:
        load_reference(page, reference_url, theme="dark", locale="en")
        initial = page.locator(".path-card .sparkline").evaluate_all(
            "nodes => nodes.map(node => node.outerHTML)"
        )
        stable = True
        for horizon in HORIZONS:
            page.locator(f'[data-horizon="{horizon}"]').click()
            current = page.locator(".path-card .sparkline").evaluate_all(
                "nodes => nodes.map(node => node.outerHTML)"
            )
            stable = stable and current == initial
        semantic_direction_ink = page.evaluate(
            """() => [...document.querySelectorAll('.path-card')].every(card => {
              const direction = card.dataset.pathDirection;
              const html = card.querySelector('.sparkline')?.outerHTML || '';
              return html.includes(`var(--ink-${direction})`) && !html.includes('var(--link)');
            })"""
        )
        sparkline_tops = page.locator(".path-card .sparkline").evaluate_all(
            "nodes => nodes.map(node => node.getBoundingClientRect().top)"
        )
        sparkline_top_spread = max(sparkline_tops) - min(sparkline_tops)
        scale_mode = page.locator('[data-chart-role="fixed-84-session"]').get_attribute(
            "data-scale-mode"
        )
        filename = "proposal-r3-successor-fixed-paths-desktop-dark-en.png"
        digest, meta = screenshot(
            page,
            filename,
            selector='[data-chart-role="fixed-84-session"]',
        )
        assert_clean(page, telemetry, filename)
        if (
            not stable
            or not semantic_direction_ink
            or sparkline_top_spread > 2
            or scale_mode != "per-market-normalized-shape-only"
        ):
            raise AssertionError(
                "Fixed paths failed horizon, ink, alignment, or shape-only scale contract"
            )
        print(f"captured {filename}", flush=True)
        return {
            "kind": "r3-successor-fixed-paths",
            "viewport": "desktop",
            "theme": "dark",
            "locale": "en",
            "market_count": len(initial),
            "horizons_verified": HORIZONS,
            "horizon_independent": stable,
            "semantic_direction_ink": semantic_direction_ink,
            "sparkline_top_spread": sparkline_top_spread,
            "scale_mode": scale_mode,
            "file": filename,
            "sha256": digest,
            "dimensions": dimensions(page),
            "console_errors": telemetry["console_errors"],
            "request_failures": telemetry["request_failures"],
            "image_dimensions": {"width": meta["width"], "height": meta["height"]},
            "paint_dynamic_range": meta["paint_dynamic_range"],
        }
    finally:
        context.close()


def capture_initial_zh(browser: Browser, reference_url: str) -> dict[str, Any]:
    context, page, telemetry = new_page(browser, "mobile")
    try:
        load_reference(
            page,
            reference_url,
            theme="dark",
            locale="zh",
            direct_initial_locale=True,
        )
        selected_horizon_labels = page.locator('[data-horizon-label]').evaluate_all(
            "nodes => [...new Set(nodes.map(node => node.textContent.trim()))]"
        )
        english_leaks = page.locator(".l-en").evaluate_all(
            """nodes => nodes.filter(node => {
              const style = getComputedStyle(node);
              return style.display !== 'none' && style.visibility !== 'hidden' && node.textContent.trim();
            }).map(node => node.textContent.trim())"""
        )
        missing_chinese = page.locator(".l-zh").evaluate_all(
            """nodes => nodes.filter(node => {
              const style = getComputedStyle(node);
              return style.display !== 'none' && style.visibility !== 'hidden' && !node.textContent.trim();
            }).map(node => node.outerHTML)"""
        )
        search = page.locator(".nav-search input")
        search_placeholder = search.get_attribute("placeholder")
        search_aria = search.get_attribute("aria-label")
        settings_aria = page.locator(".shell-settings").get_attribute("aria-label")
        locale_button = page.locator('[data-lang-button="zh"]')
        locale_button.focus()
        page.keyboard.press("Shift+Tab")
        page.keyboard.press("Tab")
        focus_style = locale_button.evaluate(
            "node => ({outlineStyle:getComputedStyle(node).outlineStyle, outlineWidth:getComputedStyle(node).outlineWidth})"
        )
        dims = dimensions(page)
        if dims["scrollWidth"] != 390:
            raise AssertionError(f"Initial ZH overflow: {dims}")
        if (
            search_placeholder != "搜索任意股票"
            or search_aria != "搜索股票"
            or settings_aria != "设置"
            or focus_style["outlineStyle"] == "none"
            or focus_style["outlineWidth"] == "0px"
        ):
            raise AssertionError(
                f"Initial ZH shell sync/focus failed: {search_placeholder!r}, {search_aria!r}, "
                f"{settings_aria!r}, {focus_style!r}"
            )
        filename = "proposal-r3-successor-mobile-dark-zh-initial-locale.png"
        digest, meta = screenshot(page, filename)
        assert_clean(page, telemetry, filename)
        print(f"captured {filename}", flush=True)
        return {
            "kind": "r3-successor-initial-locale",
            "viewport": "mobile",
            "theme": "dark",
            "locale": "zh",
            "selected_horizon_labels": selected_horizon_labels,
            "english_leaks": english_leaks,
            "missing_chinese": missing_chinese,
            "search_placeholder": search_placeholder,
            "search_aria": search_aria,
            "settings_aria": settings_aria,
            "locale_focus_style": focus_style,
            "file": filename,
            "sha256": digest,
            "dimensions": dims,
            "console_errors": telemetry["console_errors"],
            "request_failures": telemetry["request_failures"],
            "image_dimensions": {"width": meta["width"], "height": meta["height"]},
            "paint_dynamic_range": meta["paint_dynamic_range"],
        }
    finally:
        context.close()


def visible(page: Page, selector: str) -> bool:
    return page.locator(selector).evaluate(
        "node => { const s=getComputedStyle(node); const r=node.getBoundingClientRect(); return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0; }"
    )


def capture_organ_state(
    browser: Browser,
    reference_url: str,
    state: str,
    theme: str,
) -> dict[str, Any]:
    context, page, telemetry = new_page(browser, "desktop")
    try:
        load_reference(page, reference_url, theme=theme, locale="en")
        page.locator(f'[data-organ-control="{state}"]').last.click()
        active_state_visible = visible(page, f'[data-organ-state="{state}"]')
        act_visibility = page.locator("section.act").evaluate_all(
            """nodes => nodes.map(node => {
              const style=getComputedStyle(node);
              const rect=node.getBoundingClientRect();
              return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
            })"""
        )
        all_acts_visible = len(act_visibility) == 6 and all(act_visibility)
        unrelated_rotation_visible = visible(page, "#rotation-turns")
        independent_turn_board_visible = visible(page, ".turn-grid")
        unrelated_country_visible = visible(page, "#country-inspector")
        unrelated_deep_desks_visible = visible(page, "#deep-desks")
        dims = dimensions(page)
        filename = f"proposal-r3-successor-organ-{state}-{theme}-en.png"
        digest, meta = screenshot(page, filename)
        assert_clean(page, telemetry, filename)
        if not all(
            (
                active_state_visible,
                all_acts_visible,
                unrelated_rotation_visible,
                independent_turn_board_visible,
                unrelated_country_visible,
                unrelated_deep_desks_visible,
            )
        ):
            raise AssertionError(f"Organ locality failed for {state}/{theme}")
        print(f"captured {filename}", flush=True)
        return {
            "kind": "r3-successor-organ-state",
            "viewport": "desktop",
            "theme": theme,
            "locale": "en",
            "state": state,
            "capture_scope": "full-page",
            "act_count": dims["actCount"],
            "all_acts_visible": all_acts_visible,
            "unrelated_rotation_visible": unrelated_rotation_visible,
            "independent_turn_board_visible": independent_turn_board_visible,
            "unrelated_country_visible": unrelated_country_visible,
            "unrelated_deep_desks_visible": unrelated_deep_desks_visible,
            "active_state_visible": active_state_visible,
            "file": filename,
            "sha256": digest,
            "dimensions": dims,
            "console_errors": telemetry["console_errors"],
            "request_failures": telemetry["request_failures"],
            "image_dimensions": {"width": meta["width"], "height": meta["height"]},
            "paint_dynamic_range": meta["paint_dynamic_range"],
        }
    finally:
        context.close()


def settle_stocks(page: Page) -> tuple[bool, int, dict[str, Any]]:
    previous: dict[str, Any] | None = None
    stable_samples = 0
    observation: dict[str, Any] = {}
    for _ in range(30):
        observation = page.evaluate(
            """() => ({
              scrollHeight: document.documentElement.scrollHeight,
              textLength: document.body.innerText.length,
              incompleteImages: [...document.images].filter(image => !image.complete).length,
              fontStatus: document.fonts?.status || 'unsupported',
              busyVisible: [...document.querySelectorAll('[aria-busy="true"]')].filter(node => {
                const s=getComputedStyle(node); return s.display !== 'none' && s.visibility !== 'hidden';
              }).length,
              loadingVisible: [...document.querySelectorAll('.loading,.spinner,[data-loading="true"]')].filter(node => {
                const s=getComputedStyle(node); return s.display !== 'none' && s.visibility !== 'hidden';
              }).length
            })"""
        )
        if observation == previous and observation["incompleteImages"] == 0:
            stable_samples += 1
        else:
            stable_samples = 1
        if stable_samples >= 3:
            return True, stable_samples, observation
        previous = observation
        page.wait_for_timeout(250)
    return False, stable_samples, observation


def load_stocks(page: Page, stocks_url: str, theme: str, locale: str) -> None:
    page.goto(stocks_url, wait_until="load")
    page.wait_for_timeout(100)
    current_theme = page.evaluate("document.documentElement.dataset.theme || 'dark'")
    if current_theme != theme:
        page.locator(".theme-switch").dispatch_event("click")
    current_locale = page.evaluate("document.documentElement.dataset.lang || 'en'")
    if current_locale != locale:
        page.locator(".lang-toggle").dispatch_event("click")
    page.wait_for_timeout(80)
    state = page.evaluate(
        "() => ({theme:document.documentElement.dataset.theme || 'dark',locale:document.documentElement.dataset.lang || 'en'})"
    )
    if state != {"theme": theme, "locale": locale}:
        raise AssertionError(f"Stocks control mismatch: {state}")


def capture_stocks(
    browser: Browser,
    stocks_url: str,
    viewport: str,
    theme: str,
    locale: str,
) -> dict[str, Any]:
    context, page, telemetry = new_page(browser, viewport)
    try:
        load_stocks(page, stocks_url, theme, locale)
        settled, stable_samples, observation = settle_stocks(page)
        dims = dimensions(page)
        expected_width = VIEWPORTS[viewport]["width"]
        if dims["scrollWidth"] != expected_width or dims["clientWidth"] != expected_width:
            raise AssertionError(f"stocks-{viewport}-{theme}-{locale}: overflow {dims}")
        if not settled:
            raise AssertionError(f"stocks-{viewport}-{theme}-{locale}: did not settle: {observation}")
        filename = f"stocks-r3-successor-{viewport}-{theme}-{locale}.png"
        digest, meta = screenshot(page, filename)
        assert_clean(page, telemetry, filename)
        print(f"captured {filename}", flush=True)
        return {
            "kind": "stocks-successor-preservation",
            "viewport": viewport,
            "theme": theme,
            "locale": locale,
            "settled": settled,
            "stable_samples": stable_samples,
            "busy_visible": observation["busyVisible"],
            "loading_visible": observation["loadingVisible"],
            "settle_observation": observation,
            "stocks_sha256": sha256(STOCKS),
            "file": filename,
            "sha256": digest,
            "dimensions": dims,
            "console_errors": telemetry["console_errors"],
            "request_failures": telemetry["request_failures"],
            "image_dimensions": {"width": meta["width"], "height": meta["height"]},
            "paint_dynamic_range": meta["paint_dynamic_range"],
        }
    finally:
        context.close()


def representative_styles(page: Page) -> dict[str, dict[str, str]]:
    return page.evaluate(
        """() => {
          const classes=['state-good','state-caution','state-danger','state-neutral','status-good','status-caution','status-danger','status-neutral','status-info'];
          const out={};
          for (const name of classes) {
            const node=document.querySelector('.'+name);
            if (!node) continue;
            const style=getComputedStyle(node);
            out[name]={color:style.color,backgroundColor:style.backgroundColor,borderColor:style.borderColor};
          }
          return out;
        }"""
    )


def resolved_token_colors(page: Page, tokens: list[str]) -> dict[str, str]:
    return page.evaluate(
        """tokens => {
          const out={};
          for (const token of tokens) {
            const node=document.createElement('span');
            node.style.color=`var(${token})`;
            node.style.position='fixed';
            node.style.left='-9999px';
            document.body.appendChild(node);
            out[token]=getComputedStyle(node).color;
            node.remove();
          }
          return out;
        }""",
        tokens,
    )


def validate_links() -> tuple[int, list[str]]:
    soup = BeautifulSoup(ARTIFACT.read_text(encoding="utf-8"), "html.parser")
    ids = {node.get("id") for node in soup.select("[id]")}
    unresolved: list[str] = []
    hrefs = [anchor.get("href", "").strip() for anchor in soup.select("a[href]")]
    resolved = 0
    for href in hrefs:
        if not href:
            unresolved.append("<empty>")
            continue
        parsed = urlparse(href)
        if parsed.scheme in {"http", "https", "mailto", "javascript"}:
            unresolved.append(href)
            continue
        if parsed.path in {"", "."} and parsed.fragment:
            if parsed.fragment in ids:
                resolved += 1
            else:
                unresolved.append(href)
            continue
        target = ROOT / "site" / unquote(parsed.path)
        if not target.is_file():
            unresolved.append(href)
            continue
        if parsed.fragment:
            target_soup = BeautifulSoup(target.read_text(encoding="utf-8", errors="ignore"), "html.parser")
            if target_soup.select_one(f'#{parsed.fragment}') is None:
                unresolved.append(href)
                continue
        resolved += 1
    return resolved, unresolved


def semantic_checks(browser: Browser, reference_url: str) -> dict[str, Any]:
    context, page, telemetry = new_page(browser, "desktop")
    try:
        load_reference(page, reference_url, theme="light", locale="en")
        styles_en = representative_styles(page)
        direction_en = page.locator(".path-card .sparkline").evaluate_all(
            "nodes => nodes.map(node => getComputedStyle(node.querySelector('polyline[fill=\"none\"]')).stroke)"
        )
        tokens = [
            "--ink-up",
            "--ink-down",
            "--ink-warn",
            "--status-danger-ink",
            "--status-caution-ink",
            "--status-good-ink",
            "--status-neutral-ink",
            "--text",
            "--muted",
        ]
        token_colors = resolved_token_colors(page, tokens)
        background = page.evaluate("getComputedStyle(document.body).backgroundColor")
        contrasts = {
            token: contrast_ratio(color, background) for token, color in token_colors.items()
        }
        heat_pairs_light = page.locator('.correlation-heat td[data-heat-band="high"]').evaluate_all(
            """nodes => nodes.map(node => {
              const s=getComputedStyle(node); return {color:s.color, background:s.backgroundColor};
            })"""
        )
        heat_contrast_light = min(
            contrast_ratio(pair["color"], pair["background"]) for pair in heat_pairs_light
        )
        search = page.locator(".nav-search input")
        search.focus()
        search_focus = search.evaluate(
            "node => ({outlineStyle:getComputedStyle(node).outlineStyle, outlineWidth:getComputedStyle(node).outlineWidth})"
        )
        page.locator('[data-lang-button="zh"]').click()
        page.wait_for_timeout(30)
        styles_zh = representative_styles(page)
        direction_zh = page.locator(".path-card .sparkline").evaluate_all(
            "nodes => nodes.map(node => getComputedStyle(node.querySelector('polyline[fill=\"none\"]')).stroke)"
        )
        shell_locale_accessibility_sync = (
            search.get_attribute("placeholder") == "搜索任意股票"
            and search.get_attribute("aria-label") == "搜索股票"
            and page.locator(".shell-settings").get_attribute("aria-label") == "设置"
        )
        page.locator('[data-theme-button="dark"]').click()
        page.wait_for_timeout(30)
        heat_pairs_dark = page.locator('.correlation-heat td[data-heat-band="high"]').evaluate_all(
            """nodes => nodes.map(node => {
              const s=getComputedStyle(node); return {color:s.color, background:s.backgroundColor};
            })"""
        )
        heat_contrast_dark = min(
            contrast_ratio(pair["color"], pair["background"]) for pair in heat_pairs_dark
        )
        assert_clean(page, telemetry, "semantic-checks")

        mobile_context, mobile_page, mobile_telemetry = new_page(browser, "mobile")
        try:
            load_reference(mobile_page, reference_url, theme="dark", locale="en")
            act_jump_visible = visible(mobile_page, ".act-jump")
            act_hrefs = mobile_page.locator("[data-act-jump]").evaluate_all(
                "nodes => nodes.map(node => node.getAttribute('href'))"
            )
            mobile_page.locator('[data-act-jump][href="#deep-desks"]').click()
            mobile_page.wait_for_timeout(40)
            deep_top = mobile_page.locator("#deep-desks").evaluate(
                "node => node.getBoundingClientRect().top"
            )
            sticky_bottom = mobile_page.evaluate("""() => Math.max(
              ...[...document.querySelectorAll('.product-shell,.act-jump')].map(node => node.getBoundingClientRect().bottom)
            )""")
            mobile_act_navigation = (
                act_jump_visible
                and act_hrefs == [
                    "#global-call", "#global-pulse", "#rotation-turns",
                    "#transmission-fragility", "#macro-comparison", "#deep-desks"
                ]
                and mobile_page.evaluate("location.hash") == "#deep-desks"
                and deep_top >= sticky_bottom - 2
            )
            assert_clean(mobile_page, mobile_telemetry, "mobile-act-navigation")
        finally:
            mobile_context.close()
        artifact_text = BeautifulSoup(ARTIFACT.read_text(encoding="utf-8"), "html.parser").get_text(
            " ", strip=True
        )
        scores = {int(value) for value in re.findall(r"\b(\d{1,3})\s*/\s*100\b", artifact_text)}
        forbidden = [
            phrase
            for phrase in (
                "confidence score",
                "risk budget score",
                "sensitivity score",
                "health score",
                "probability of dip",
            )
            if phrase in artifact_text.lower()
        ]
        zero_score_disclosed = (
            "equity-drawdown leg only" in artifact_text
            and "descriptive stress comparator, not a probability" in artifact_text
        )
        return {
            "status_locale_invariant": styles_en == styles_zh,
            "direction_ink_locale_switches": direction_en != direction_zh,
            "light_theme_contrast_en": contrasts,
            "heatmap_high_contrast_light": heat_contrast_light,
            "heatmap_high_contrast_dark": heat_contrast_dark,
            "heatmap_high_contrast": min(heat_contrast_light, heat_contrast_dark) >= 4.5,
            "search_focus_visible": (
                search_focus["outlineStyle"] != "none"
                and search_focus["outlineWidth"] != "0px"
            ),
            "shell_locale_accessibility_sync": shell_locale_accessibility_sync,
            "mobile_act_navigation": mobile_act_navigation,
            "canonical_light_ink_tokens": (
                min(contrasts.values()) >= 4.5
                and token_colors["--ink-up"] != token_colors["--status-good-ink"]
                and token_colors["--ink-down"] != token_colors["--status-danger-ink"]
            ),
            "no_invented_quantitative_displays": (
                scores <= {0, 61, 66, 81}
                and (0 not in scores or zero_score_disclosed)
                and not forbidden
            ),
            "zero_score_disclosed": zero_score_disclosed,
            "observed_scores_per_100": sorted(scores),
            "forbidden_quantitative_phrases": forbidden,
            "no_regional_indicator_emoji": not bool(
                re.search(r"[🇦-🇿]{2}", ARTIFACT.read_text(encoding="utf-8"))
            ),
            "semantic_console_errors": telemetry["console_errors"],
            "semantic_request_failures": telemetry["request_failures"],
            "semantic_external_requests": telemetry["external_requests"],
        }
    finally:
        context.close()


def capture() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    captures: list[dict[str, Any]] = []
    with static_server(ARTIFACT.parent) as reference_base, static_server(ROOT / "site") as stocks_base:
        reference_url = f"{reference_base}/{ARTIFACT.name}"
        stocks_url = f"{stocks_base}/{STOCKS.name}"
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for viewport in ("desktop", "mobile"):
                    for theme in ("dark", "light"):
                        for locale in ("en", "zh"):
                            captures.append(
                                capture_reference_default(
                                    browser, reference_url, viewport, theme, locale
                                )
                            )

                country_combinations = [(country, "dark", "en") for country in COUNTRIES]
                country_combinations.extend(
                    (country, theme, locale)
                    for country in ("JP", "GB")
                    for theme in ("dark", "light")
                    for locale in ("en", "zh")
                    if (theme, locale) != ("dark", "en")
                )
                for country, theme, locale in country_combinations:
                    captures.append(
                        capture_country(browser, reference_url, country, theme, locale)
                    )

                captures.append(
                    capture_horizon(
                        browser, reference_url, "desktop", "dark", "en", "12m"
                    )
                )
                captures.append(
                    capture_horizon(
                        browser, reference_url, "mobile", "light", "zh", "1m"
                    )
                )
                captures.append(capture_fixed_paths(browser, reference_url))
                captures.append(capture_initial_zh(browser, reference_url))

                for state in ("loading", "empty", "stale", "error"):
                    for theme in ("dark", "light"):
                        captures.append(
                            capture_organ_state(browser, reference_url, state, theme)
                        )

                for viewport in ("desktop", "mobile"):
                    for theme in ("dark", "light"):
                        for locale in ("en", "zh"):
                            captures.append(
                                capture_stocks(
                                    browser, stocks_url, viewport, theme, locale
                                )
                            )

                semantics = semantic_checks(browser, reference_url)
            finally:
                browser.close()

    if len(captures) != 41:
        raise AssertionError(f"Expected 41 captures, got {len(captures)}")

    resolved_link_count, unresolved_links = validate_links()
    overflow_failures = []
    for row in captures:
        if row["kind"] not in {
            "r3-successor-default",
            "r3-successor-horizon",
            "r3-successor-initial-locale",
            "r3-successor-organ-state",
            "stocks-successor-preservation",
        }:
            continue
        expected = VIEWPORTS[row["viewport"]]["width"]
        if row["dimensions"]["scrollWidth"] != expected:
            overflow_failures.append(row["file"])

    direct_initial = next(
        row for row in captures if row["kind"] == "r3-successor-initial-locale"
    )
    fixed_paths = next(
        row for row in captures if row["kind"] == "r3-successor-fixed-paths"
    )
    country_rows = [row for row in captures if row["kind"] == "r3-successor-country"]
    default_mobile_zh = next(
        row
        for row in captures
        if row["kind"] == "r3-successor-default"
        and row["viewport"] == "mobile"
        and row["theme"] == "dark"
        and row["locale"] == "zh"
    )
    organ_rows = [row for row in captures if row["kind"] == "r3-successor-organ-state"]
    stocks_rows = [
        row for row in captures if row["kind"] == "stocks-successor-preservation"
    ]
    all_console_errors = [
        error for row in captures for error in row.get("console_errors", [])
    ]
    all_request_failures = [
        error for row in captures for error in row.get("request_failures", [])
    ]

    checks = {
        **semantics,
        "zero_external_dependencies": not semantics["semantic_external_requests"],
        "resolved_link_count": resolved_link_count,
        "unresolved_links": unresolved_links,
        "all_links_resolved": not unresolved_links,
        "fixed_chart_horizon_independent": fixed_paths["horizon_independent"],
        "fixed_path_grid_aligned": (
            fixed_paths["sparkline_top_spread"] <= 2
            and fixed_paths["scale_mode"] == "per-market-normalized-shape-only"
        ),
        "direct_initial_zh_synchronized": (
            direct_initial["selected_horizon_labels"] == ["3月"]
            and not direct_initial["english_leaks"]
            and not direct_initial["missing_chinese"]
            and direct_initial["search_placeholder"] == "搜索任意股票"
            and direct_initial["search_aria"] == "搜索股票"
            and direct_initial["settings_aria"] == "设置"
        ),
        "direct_initial_pixel_distinct": direct_initial["sha256"] != default_mobile_zh["sha256"],
        "country_inspector_unobscured": all(
            row["inspector_top"] >= row["sticky_bottom"] + 4 for row in country_rows
        ),
        "zero_page_overflow": not overflow_failures,
        "overflow_failures": overflow_failures,
        "zero_console_errors": not all_console_errors,
        "zero_request_failures": not all_request_failures,
        "organ_state_locality": all(
            row["all_acts_visible"]
            and row["unrelated_rotation_visible"]
            and row["independent_turn_board_visible"]
            and row["unrelated_country_visible"]
            and row["unrelated_deep_desks_visible"]
            and row["active_state_visible"]
            for row in organ_rows
        ),
        "stocks_mode_non_regression": all(
            row["settled"]
            and row["busy_visible"] == 0
            and row["loading_visible"] == 0
            and row["stocks_sha256"] == sha256(STOCKS)
            for row in stocks_rows
        ),
        "minimum_paint_dynamic_range": min(
            row["paint_dynamic_range"] for row in captures
        ),
    }

    required_checks = [
        "zero_external_dependencies",
        "all_links_resolved",
        "fixed_chart_horizon_independent",
        "fixed_path_grid_aligned",
        "direct_initial_zh_synchronized",
        "direct_initial_pixel_distinct",
        "country_inspector_unobscured",
        "zero_page_overflow",
        "zero_console_errors",
        "zero_request_failures",
        "organ_state_locality",
        "stocks_mode_non_regression",
        "status_locale_invariant",
        "direction_ink_locale_switches",
        "canonical_light_ink_tokens",
        "heatmap_high_contrast",
        "search_focus_visible",
        "shell_locale_accessibility_sync",
        "mobile_act_navigation",
        "no_regional_indicator_emoji",
        "no_invented_quantitative_displays",
    ]
    failed = [key for key in required_checks if checks.get(key) is not True]
    if failed:
        raise AssertionError(f"Browser evidence checks failed: {failed}; details={checks}")

    proof = {
        "schema": "mastermind.intl_r3_browser_evidence.v4",
        "source_commit": "UNFROZEN_WORKTREE",
        "artifact": ARTIFACT_REL.as_posix(),
        "artifact_sha256": sha256(ARTIFACT),
        "stocks_artifact": STOCKS_REL.as_posix(),
        "stocks_sha256": sha256(STOCKS),
        "stocks_preservation_basis": (
            "Separate production-mode non-regression surface; R3 repair changes no production "
            "source and does not reinterpret Prophet signals."
        ),
        "checks": checks,
        "captures": captures,
    }
    PROOF.write_text(json.dumps(proof, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {PROOF} with {len(captures)} captures", flush=True)


def bind_source(commit: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("--bind-source requires a full 40-character lowercase commit SHA")
    subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=ROOT,
        check=True,
    )
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    artifact_digest = sha256(ARTIFACT)
    committed_digest = git_blob_sha256(commit, ARTIFACT_REL)
    if proof["artifact_sha256"] != artifact_digest or artifact_digest != committed_digest:
        raise AssertionError(
            "Cannot bind: working artifact, captured artifact, and committed artifact differ"
        )
    proof["source_commit"] = commit
    PROOF.write_text(json.dumps(proof, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"bound {PROOF.name} to {commit}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind-source", metavar="SHA")
    args = parser.parse_args()
    if args.bind_source:
        bind_source(args.bind_source)
    else:
        capture()


if __name__ == "__main__":
    main()
