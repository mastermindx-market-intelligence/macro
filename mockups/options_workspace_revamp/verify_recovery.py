"""Focused recovery/history acceptance on the real rendered workspace.
Uses isolated Chromium and loopback fixtures. Never contacts production services.
"""
import asyncio, hashlib, json
from pathlib import Path
from playwright.async_api import async_playwright
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGIN="http://127.0.0.1:8768"
URL=ORIGIN+"/mockups/options_workspace_revamp/fixtures/workspace-current.html"
PAYLOADS=json.loads((HERE/"fixtures/payloads.json").read_text())
OUT=HERE/"visual-candidate-states"
OUT.mkdir(exist_ok=True)
async def main():
    checks=[]
    def record(name, passed, **evidence):
        checks.append({"name":name,"pass":bool(passed),**evidence})
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        async def context(mode="normal",suffix=""):
            ctx=await browser.new_context(viewport={"width":1440,"height":1000},service_workers="block")
            await ctx.add_init_script('localStorage.setItem("theme","light");localStorage.setItem("lang","en");')
            calls={}
            async def handle(route):
                url=route.request.url.split("?")[0]
                key=next((k for k in PAYLOADS if url.endswith("/"+k)),None)
                if key:
                    calls[key]=calls.get(key,0)+1
                    if mode=="ticker-error" and key=="gex/QQQ.json":
                        await route.fulfill(status=503,body="Unavailable");return
                    if mode=="bad-scanner" and key=="screenerdata/rows.json" and calls[key]==1:
                        await route.fulfill(status=200,content_type="application/json",body='{"rows":"invalid"}');return
                    if mode=="optional" and key=="flowdata/cohorts.json":
                        if calls[key]==1:
                            await route.fulfill(status=503,body="Unavailable");return
                        await asyncio.sleep(.5)
                    await route.fulfill(status=200,content_type="application/json",body=json.dumps(PAYLOADS[key]))
                elif route.request.url.startswith(ORIGIN+"/"):await route.continue_()
                else:await route.abort()
            await ctx.route("**/*",handle)
            page=await ctx.new_page()
            await page.goto(URL+suffix)
            return ctx,page,calls
        async def pick(page,symbol):
            q=page.locator("#oew-tk-q")
            await q.fill(symbol);await q.press("ArrowDown");await q.press("Enter")
        ctx,page,calls=await context(suffix="#ticker")
        await page.locator(".oew-tk-sym").wait_for()
        await pick(page,"QQQ")
        await page.wait_for_function("document.querySelector('.oew-tk-sym')?.textContent === 'QQQ'")
        await page.go_back()
        await page.wait_for_function("document.querySelector('.oew-tk-sym')?.textContent === 'SPY'")
        record("bare_ticker_history_restores_default",True,ticker=await page.locator(".oew-tk-sym").inner_text(),url=page.url)
        q=page.locator("#oew-tk-q")
        await q.focus();await q.press("Escape");await q.press("ArrowDown")
        record("arrow_down_reopens_typeahead",await q.get_attribute("aria-expanded")=="true" and bool(await q.get_attribute("aria-activedescendant")))
        await ctx.close()

        ctx,page,calls=await context(suffix="#scanner")
        origin=page.locator("#mode-scanner [data-goto='SPY']")
        await origin.wait_for();await origin.focus();await origin.press("Enter")
        await page.locator(".oew-tk-sym").wait_for()
        record("keyboard_drilldown_moves_focus",await page.locator("#oew-tk-q").evaluate("(e)=>e===document.activeElement"))
        await page.locator("#tab-leaders").click();await page.locator("#mode-leaders .oew-ldrow").first.wait_for()
        await page.go_back()
        await page.wait_for_function("document.querySelector('#tab-ticker').getAttribute('aria-selected') === 'true'")
        destination=await page.locator("#oew-tk-back").get_attribute("data-workspace-mode")
        await page.locator("#oew-tk-back").click()
        restored=await page.locator("#tab-scanner").get_attribute("aria-selected")=="true"
        focus=await origin.evaluate("(e)=>e===document.activeElement")
        record("history_preserves_research_origin_and_focus",destination=="scanner" and restored and focus,destination=destination,focus_restored=focus)
        await ctx.close()

        ctx,page,calls=await context("ticker-error","#ticker?t=SPY")
        await page.locator(".oew-tk-sym").wait_for();await pick(page,"QQQ")
        await page.locator("#oew-tk-body [data-retry-mode]").wait_for()
        symbol=await page.locator("#oew-tk-cnt").inner_text()
        record("failed_ticker_keeps_selected_symbol",symbol=="QQQ",selected=symbol)
        await page.screenshot(path=str(OUT/"ticker-error-1440-light-en.png"))
        await ctx.close()

        ctx,page,calls=await context("bad-scanner","#scanner")
        await page.locator("#mode-scanner [data-retry-mode]").wait_for()
        await page.screenshot(path=str(OUT/"scanner-recovery-1440-light-en.png"))
        await page.locator("#mode-scanner [data-retry-mode]").click()
        await page.locator("#oew-sc-body tr").first.wait_for()
        rows=await page.locator("#oew-sc-body tr").count()
        record("retry_refetches_invalid_cached_payload",calls.get("screenerdata/rows.json")==2 and rows==len(PAYLOADS["screenerdata/rows.json"]["rows"]),requests=calls.get("screenerdata/rows.json"),rows=rows)
        await ctx.close()

        ctx,page,calls=await context("optional","#flow")
        retry=page.locator("#mode-flow [data-retry-optional]")
        await retry.wait_for()
        panels_before=await page.locator("#mode-flow .oew-panel").count()
        await page.screenshot(path=str(OUT/"flow-partial-recovery-1440-light-en.png"),full_page=True)
        await retry.click()
        retained=await page.locator("#mode-flow .oew-panel").count()==panels_before and await page.locator("#mode-flow .oew-skel").count()==0
        await page.wait_for_function("!document.querySelector('#mode-flow [data-retry-optional]')")
        record("optional_retry_preserves_primary_evidence",retained and calls.get("flow_desk.json")==1 and calls.get("flowdata/cohorts.json")==2,primary_requests=calls.get("flow_desk.json"),support_requests=calls.get("flowdata/cohorts.json"),panels_retained=retained)
        await ctx.close()
        await browser.close()
    report={"fixture":"synthetic","template_sha256":hashlib.sha256((ROOT/"templates/options.html.j2").read_bytes()).hexdigest(),"checks":checks,"passed":sum(c["pass"] for c in checks),"failed":[c["name"] for c in checks if not c["pass"]]}
    (HERE/"recovery-candidate.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if report["failed"]:raise SystemExit(1)
asyncio.run(main())
