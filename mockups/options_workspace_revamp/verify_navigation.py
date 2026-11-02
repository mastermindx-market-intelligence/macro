"""Independent navigation and request-order proof on the synthetic QA fixture.

Uses an isolated Chromium context and loopback data; never writes market stores.
Assertions observe visible controls and browser history, not implementation names.
"""
import argparse
import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

HERE = Path(__file__).resolve().parent
ORIGIN = "http://127.0.0.1:8768"
URL = ORIGIN + "/mockups/options_workspace_revamp/fixtures/workspace-current.html"
PAYLOADS = json.loads((HERE / "fixtures/payloads.json").read_text())


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="baseline")
    args = parser.parse_args()
    report = {"fixture": "synthetic", "label": args.label, "checks": []}

    def record(name, passed, **evidence):
        report["checks"].append({"name": name, "pass": passed, **evidence})

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        async def context(mode="normal", suffix=""):
            ctx = await browser.new_context(
                viewport={"width": 1440, "height": 1000},
                service_workers="block",
            )
            calls = {}
            old_started = asyncio.Event()

            async def handle(route):
                url = route.request.url.split("?")[0]
                key = next((k for k in PAYLOADS if url.endswith("/" + k)), None)
                if key:
                    calls[key] = calls.get(key, 0) + 1
                    try:
                        if mode.startswith("race") and key.endswith("/SPY.json"):
                            old_started.set()
                            await asyncio.sleep(2)
                            if mode == "race_failure":
                                await route.fulfill(status=503, body="QA delayed failure")
                                return
                        await route.fulfill(
                            status=200,
                            content_type="application/json",
                            body=json.dumps(PAYLOADS[key]),
                        )
                    except Exception:
                        pass  # Closing a context intentionally aborts pending routes.
                elif route.request.url.startswith(ORIGIN + "/"):
                    await route.continue_()
                else:
                    await route.abort()

            await ctx.route("**/*", handle)
            page = await ctx.new_page()
            await page.goto(URL + suffix, wait_until="networkidle")
            return ctx, page, calls, old_started

        async def selected(page):
            return await page.locator('[role="tab"][aria-selected="true"]').get_attribute("data-mode")

        async def choose_qqq(page):
            query = page.locator("#oew-tk-q")
            await query.fill("QQQ")
            await query.press("ArrowDown")
            await query.press("Enter")

        ctx, page, _, _ = await context(suffix="#ticker?t=QQQ")
        initial = await page.locator("#oew-tk-cnt").inner_text()
        await page.reload(wait_until="networkidle")
        reloaded = await page.locator("#oew-tk-cnt").inner_text()
        record("ticker_deep_link_and_reload", initial == reloaded == "QQQ",
               initial=initial, reloaded=reloaded, url=page.url)

        query = page.locator("#oew-tk-q")
        await query.fill("SPY")
        await query.press("ArrowDown")
        active = await query.get_attribute("aria-activedescendant")
        option = page.locator('[role="option"][id="' + active + '"]') if active else None
        record("typeahead_exposes_keyboard_selection", bool(active) and await option.count() == 1,
               active_descendant=active)
        await query.press("Escape")
        record("typeahead_escape_closes", await query.get_attribute("aria-expanded") == "false")

        await page.locator("#tab-brief").click()
        await page.locator("#tab-brief").focus()
        await page.keyboard.press("/")
        outside = await query.evaluate("(el) => document.activeElement === el")
        await page.locator("#tab-ticker").click()
        await page.locator("#tab-ticker").focus()
        await page.keyboard.press("/")
        inside = await query.evaluate("(el) => document.activeElement === el")
        record("ticker_shortcut_scoped_to_visible_task", not outside and inside,
               focused_outside=outside, focused_inside=inside)

        await choose_qqq(page)
        await page.wait_for_timeout(100)
        record("typeahead_keyboard_selection", await page.locator("#oew-tk-cnt").inner_text() == "QQQ",
               url=page.url)
        await page.locator("#tab-brief").click()
        base_history = await page.evaluate("history.length")
        await page.locator("#tab-scanner").click()
        await page.locator("#mode-scanner .oew-tbl tbody tr").first.wait_for(timeout=5000)
        await page.locator("#tab-leaders").click()
        await page.locator("#mode-leaders .oew-skel").wait_for(state="detached", timeout=5000)
        delta = await page.evaluate("history.length") - base_history
        back_mode = forward_mode = None
        if delta >= 2:
            await page.go_back()
            await page.wait_for_timeout(150)
            back_mode = await selected(page)
            await page.go_forward()
            await page.wait_for_timeout(150)
            forward_mode = await selected(page)
        record("task_back_forward_history", delta >= 2 and back_mode == "scanner" and forward_mode == "leaders",
               added_history_entries=delta, back=back_mode, forward=forward_mode)

        await page.locator("#tab-scanner").click()
        await page.evaluate("location.hash = 'leaders'")
        await page.wait_for_timeout(250)
        hash_mode = await selected(page)
        record("hash_change_updates_visible_task", hash_mode == "leaders",
               observed=hash_mode, url=page.url)
        await ctx.close()

        for mode in ("race_success", "race_failure"):
            ctx, page, calls, old_started = await context(mode)
            await page.locator("#tab-ticker").click()
            await asyncio.wait_for(old_started.wait(), timeout=3)
            await choose_qqq(page)
            await page.wait_for_timeout(2500)
            shown = await page.locator("#oew-tk-cnt").inner_text()
            record("new_ticker_survives_old_" + mode.removeprefix("race_"),
                   shown == "QQQ" and "#ticker?t=QQQ" in page.url,
                   observed=shown, url=page.url,
                   spy_requests=calls.get("gex/SPY.json", 0),
                   qqq_requests=calls.get("gex/QQQ.json", 0))
            await ctx.close()
        await browser.close()

    report["passed"] = sum(x["pass"] for x in report["checks"])
    report["failed"] = [x["name"] for x in report["checks"] if not x["pass"]]
    (HERE / ("navigation-" + args.label + ".json")).write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


asyncio.run(main())
