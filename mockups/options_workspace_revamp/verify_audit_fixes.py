"""Browser regressions for the concrete final audit findings.

The published fixture HTML is immutable during each run. Routing changes only
the isolated test context; no provider, site data, or user browser is touched.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path

from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ORIGIN = "http://127.0.0.1:8768"
FIXTURE = HERE / "fixtures/published/workspace.html"
URL = ORIGIN + "/mockups/options_workspace_revamp/fixtures/published/workspace.html"


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", choices=["baseline", "candidate"], required=True)
    args = parser.parse_args()
    output = HERE / ("audit-fixes-" + args.label + ".json")
    if output.exists():
        raise SystemExit("Evidence already exists; inspect it instead of overwriting.")
    payloads = json.loads((HERE / "fixtures/published/payloads.json").read_text())
    original = payloads["screenerdata/rows.json"]["rows"][0]
    rows = []
    for symbol, day, premium in [
        ("OLD", "2026-08-11", 500), ("NEW", "2026-08-13", 400),
        ("MID", "2026-08-12", 300), ("BAD", "2026-02-30", 200),
        ("MISSING", None, 100),
    ]:
        rows.append(dict(original, ticker=symbol, asof=day, gross_premium_mn=premium))
    payloads["screenerdata/rows.json"] = dict(payloads["screenerdata/rows.json"], rows=rows)
    before = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    report = {"label": args.label, "fixture_html_sha256": before,
              "fixture_manifest": json.loads((HERE / "fixtures/published/manifest.json").read_text()),
              "working_source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                        for name in ["templates/options.html.j2", "scripts/build_options_command.py"]},
              "checks": [], "page_errors": []}

    def check(name, passed, **evidence):
        report["checks"].append(dict(name=name, passed=bool(passed), **evidence))

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 1000},
                                            reduced_motion="reduce", service_workers="block")

        async def route_request(route):
            request_url = route.request.url.split("?")[0]
            key = next((key for key in payloads if request_url.endswith("/" + key)), None)
            if key:
                await route.fulfill(content_type="application/json", body=json.dumps(payloads[key]))
            elif request_url.startswith(ORIGIN + "/"):
                await route.continue_()
            else:
                await route.abort()

        await context.route("**/*", route_request)
        await context.add_init_script("""(() => {
          window.auditScrollRequests = [];
          const elementScroll = Element.prototype.scrollIntoView;
          Element.prototype.scrollIntoView = function(options) {
            window.auditScrollRequests.push({kind:'element', id:this.id, options});
            return elementScroll.call(this, options);
          };
          const viewportScroll = window.scrollTo;
          window.scrollTo = function(...args) {
            window.auditScrollRequests.push({kind:'window', options:args[0]});
            return viewportScroll.apply(this, args);
          };
        })();""")
        page = await context.new_page()
        page.on("pageerror", lambda error: report["page_errors"].append(str(error)))
        await page.goto(URL + "#scanner", wait_until="networkidle")
        await page.locator("#oew-sc-body tr").first.wait_for()
        visible = await page.locator("#oew-sc-body tr").evaluate_all("rows => rows.map(row => ({symbol:row.querySelector('[data-goto]').getAttribute('data-goto'), lag:row.lastElementChild.innerText.trim()}))")
        check("row_lag_values_and_unknowns", {row["symbol"]: row["lag"] for row in visible} ==
              {"OLD": "2d", "NEW": "0d", "MID": "1d", "BAD": "Unknown", "MISSING": "Unknown"}, rows=visible)
        for index, key in enumerate(["Enter", "Space", "Enter", "Space"]):
            header = page.locator('#oew-sc-head [data-sort="asof"]')
            await header.focus()
            await page.keyboard.press(key)
            state = await header.get_attribute("aria-sort")
            focus = await header.evaluate("node => document.activeElement === node")
            order = await page.locator("#oew-sc-body [data-goto]").evaluate_all("nodes => nodes.map(node => node.getAttribute('data-goto'))")
            descending = index % 2 == 0
            expected = (["OLD", "MID", "NEW"] if descending else ["NEW", "MID", "OLD"]) + ["BAD", "MISSING"]
            check("lag_sort_" + str(index + 1), order == expected, key=key, order=order, expected=expected)
            check("sort_keeps_keyboard_focus_" + str(index + 1), focus, key=key)
            check("sort_aria_" + str(index + 1), state == ("descending" if descending else "ascending"), state=state)

        await page.locator("#tab-brief").focus()
        await page.keyboard.press("Enter")
        await page.evaluate("window.auditScrollRequests = []")
        await page.locator('[data-open-details="oew-history"]').focus()
        await page.keyboard.press("Enter")
        disclosure = await page.evaluate("window.auditScrollRequests.filter(x => x.id === 'oew-history')")
        check("reduced_motion_history_disclosure", bool(disclosure) and all(x["options"].get("behavior") in ["auto", "instant"] for x in disclosure), requests=disclosure)

        await page.evaluate("window.auditScrollRequests = []")
        await page.locator('#mode-brief [data-goto="SPY"]').first.focus()
        await page.keyboard.press("Enter")
        await page.wait_for_function("document.querySelector('#tab-ticker').getAttribute('aria-selected') === 'true'")
        viewport = await page.evaluate("window.auditScrollRequests.filter(x => x.kind === 'window')")
        check("reduced_motion_ticker_drilldown", bool(viewport) and all(x["options"].get("behavior") in ["auto", "instant"] for x in viewport), requests=viewport)
        check("ticker_drilldown_finishes", await page.locator("#oew-tk-cnt").inner_text() == "SPY")
        check("no_page_errors", not report["page_errors"], errors=report["page_errors"])
        await context.close()
        await browser.close()

    check("fixture_fixed_during_run", hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == before)
    report["passed"] = sum(item["passed"] for item in report["checks"])
    report["failed"] = [item["name"] for item in report["checks"] if not item["passed"]]
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"label": args.label, "passed": report["passed"], "total": len(report["checks"]), "failed": report["failed"], "output": str(output)}, indent=2))
    raise SystemExit(1 if report["failed"] else 0)


if __name__ == "__main__":
    asyncio.run(main())
