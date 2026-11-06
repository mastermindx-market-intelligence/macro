#!/usr/bin/env python3
"""Read-only browser checks for the local admin workspace.

Run a local `python3 -m admin --port 8798` from the checkout first. Restart it
when changing static assets: the admin process pins content-addressed assets.
This script refuses non-loopback targets and blocks all API writes. Failure
fixtures below exercise UI recovery, not production integration health.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8798")
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    if urlparse(base).hostname not in {"localhost", "127.0.0.1", "::1"}:
        parser.error("Only an intentional loopback development server may be tested.")
    out = args.evidence_dir
    out.mkdir(parents=True, exist_ok=True)
    receipt: dict = {"asof": datetime.now(timezone.utc).isoformat(), "scope": "local read-only browser; failures injected separately", "checks": [], "errors": [], "blocked_writes": [], "routes": []}

    def check(name: str, condition: bool) -> None:
        receipt["checks"].append({"name": name, "pass": bool(condition)})
        if not condition:
            raise AssertionError(name)

    def guard(route) -> None:
        request = route.request
        if request.method not in {"GET", "HEAD"}:
            receipt["blocked_writes"].append({"method": request.method, "path": urlparse(request.url).path})
            route.abort()
        elif urlparse(request.url).netloc != urlparse(base).netloc:
            route.abort()
        else:
            route.continue_()

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 960}, reduced_motion="reduce")
            context.route("**/*", guard)
            page = context.new_page()
            page.on("pageerror", lambda error: receipt["errors"].append(str(error)))
            page.goto(base, wait_until="domcontentloaded")
            page.wait_for_selector("#admin-home-title", timeout=45000)
            check("13 primary links, all 54 routes retained", page.locator(".nav-item:visible").count() == 13 and page.locator(".nav-item").count() == 54)
            check("Research detail starts collapsed", not page.locator(".admin-secondary").evaluate("el => el.open"))
            page.screenshot(path=str(out / "desktop-overview.png"))
            page.locator("#navSearch").fill("AI Cost")
            check("Search reaches a collapsed specialist page", page.locator(".nav-item:visible").count() == 1)
            page.locator('.nav-item[data-tab="cost"]').focus()
            page.keyboard.press("Enter")
            expect(page).to_have_url(base + "/#/page/cost")
            check("Native keyboard navigation updates URL", page.locator('[aria-current="page"]').get_attribute("data-tab") == "cost")
            page.reload(wait_until="domcontentloaded")
            expect(page.locator("#topbar-title")).to_have_text("AI Cost", timeout=45000)
            check("Reload retains selected page", page.url.endswith("#/page/cost"))
            page.go_back(wait_until="domcontentloaded")
            page.wait_for_selector("#admin-home-title")
            check("Browser Back returns to overview", page.url.endswith("#/page/overview"))
            page.evaluate("location.hash = '#/page/%E0%A4%A'")
            page.wait_for_selector("#adminRetry")
            check("Malformed route is recoverable", page.locator(".admin-page-error").count() == 1)
            page.locator("#adminBackHome").click()
            page.wait_for_selector("#admin-home-title")
            page.evaluate("window.__savedHealthRenderer = RENDER.health; RENDER.health = async () => { throw new Error('Injected read failure'); }; go('health');")
            page.wait_for_selector("#adminRetry")
            page.evaluate("RENDER.health = window.__savedHealthRenderer; delete window.__savedHealthRenderer;")
            page.locator("#adminRetry").click()
            page.locator("#adminRetry").wait_for(state="detached")
            expect(page.locator("#topbar-title")).to_have_text("Data health")
            check("Retry recovers failed page without browser reload", page.url.endswith("#/page/health"))
            page.evaluate("go('overview')")
            page.wait_for_selector("#admin-home-title")
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(200)
            check("Mobile has no horizontal overflow", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            check("Closed mobile navigation is inert", page.locator("#sidebar").evaluate("el => el.inert"))
            page.screenshot(path=str(out / "mobile-overview.png"))
            page.locator("#sidebarToggle").click()
            check("Opening mobile nav focuses search", page.locator("#navSearch").evaluate("el => document.activeElement === el"))
            page.screenshot(path=str(out / "mobile-navigation.png"))
            page.keyboard.press("Escape")
            check("Closing nav returns focus and makes it inert", page.locator("#sidebar").evaluate("el => el.inert") and page.locator("#sidebarToggle").evaluate("el => document.activeElement === el"))
            context.close()

            # Session transport failure must not expose an authenticated-looking app.
            context = browser.new_context()
            context.route("**/*", guard)
            context.route("**/api/session", lambda route: route.abort())
            page = context.new_page()
            page.goto(base, wait_until="domcontentloaded")
            expect(page.locator("#loginErr")).to_contain_text("Unable to verify")
            check("Session failure stays behind login", page.locator("#app").is_hidden() and page.locator("#login").is_visible())
            context.close()

            # A failed landing read can be retried; no poisoned in-flight cache.
            context = browser.new_context()
            context.route("**/*", guard)
            context.route("**/api/summary", lambda route: route.fulfill(status=503, json={"ok": False, "error": "Injected unavailable snapshot"}))
            page = context.new_page()
            page.goto(base, wait_until="domcontentloaded")
            page.wait_for_selector("#adminRetry", timeout=45000)
            context.unroute("**/api/summary")
            page.locator("#adminRetry").click()
            page.wait_for_selector("#admin-home-title", timeout=45000)
            check("Landing retries after temporary server failure", True)
            context.close()

            # Every existing renderer gets a read-only unavailable-backend fixture.
            context = browser.new_context()
            context.route("**/*", guard)
            summary = {"meta": {"deployed": False, "has_token": False, "integrations": {}}, "health": {"healthy": False, "age_hours": None}, "services": {"available": False}, "system": {"available": False}}

            def unavailable(route) -> None:
                if route.request.method != "GET":
                    guard(route)
                    return
                path = urlparse(route.request.url).path
                if path == "/api/session":
                    route.fulfill(json={"auth_enabled": False, "authenticated": True, "deployed": False, "integrations": {}})
                elif path == "/api/summary":
                    route.fulfill(json=summary)
                else:
                    route.fulfill(status=503, json={"ok": False, "available": False, "error": "Read-only outage fixture"})

            context.route("**/api/**", unavailable)
            page = context.new_page()
            page.on("pageerror", lambda error: receipt["errors"].append("outage fixture: " + str(error)))
            page.goto(base, wait_until="domcontentloaded")
            page.wait_for_selector("#admin-home-title")
            ids = page.evaluate("Object.keys(TAB_LABELS)")
            for route_id in ids:
                page.evaluate("id => go(id)", route_id)
                page.wait_for_timeout(60)
                receipt["routes"].append({"id": route_id, "title": page.locator("#topbar-title").inner_text(), "text_length": len(page.locator("#view").inner_text()), "recovery_screen": page.locator("#adminRetry").count() == 1, "iframe": page.locator("#view iframe").count() > 0})
            check("All 54 routes rendered content or their embedded surface under outage fixture", len(receipt["routes"]) == 54 and all(row["text_length"] > 0 or row["iframe"] for row in receipt["routes"]))
            check("No unhandled browser errors", not receipt["errors"])
            check("No writes attempted", not receipt["blocked_writes"])
            context.close()
            browser.close()
    finally:
        (out / "browser-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps({"checks": receipt["checks"], "errors": receipt["errors"], "writes": receipt["blocked_writes"], "routes_checked": len(receipt["routes"])}))


if __name__ == "__main__":
    main()
