"""Real UI acceptance checks on isolated synthetic HTTP fixtures.
Captures behavior only; never contacts production services or the user's browser.
Baseline failures are retained for comparison with the candidate build.
"""
import argparse,asyncio,csv,io,json,re
from pathlib import Path
from playwright.async_api import async_playwright,TimeoutError as PlaywrightTimeout
HERE=Path(__file__).resolve().parent
ORIGIN="http://127.0.0.1:8768"
URL=ORIGIN+"/mockups/options_workspace_revamp/fixtures/workspace-current.html"
PAYLOADS=json.loads((HERE/"fixtures/payloads.json").read_text())
async def main():
    ap=argparse.ArgumentParser();ap.add_argument("--label",default="baseline");ap.add_argument("--only",choices=["all","source_clocks"],default="all");args=ap.parse_args()
    report={"fixture":"synthetic","label":args.label,"checks":[]}
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        async def context(mode="normal"):
            ctx=await browser.new_context(viewport={"width":1440,"height":1000},accept_downloads=True,service_workers="block")
            calls={}
            async def handle(route):
                url=route.request.url.split("?")[0]
                key=next((k for k in PAYLOADS if url.endswith("/"+k)),None)
                if key:
                    calls[key]=calls.get(key,0)+1
                    try:
                        if mode=="hang" and key=="screenerdata/rows.json" and calls[key]==1:await asyncio.sleep(45)
                        if mode=="dedupe" and key=="screenerdata/rows.json":await asyncio.sleep(1)
                        if mode=="race" and key=="gex/SPY.json":await asyncio.sleep(2)
                        await route.fulfill(status=200,content_type="application/json",body=json.dumps(PAYLOADS[key]))
                    except Exception:pass
                elif route.request.url.startswith(ORIGIN+"/"):await route.continue_()
                else:await route.abort()
            await ctx.route("**/*",handle)
            page=await ctx.new_page()
            await page.goto(URL,wait_until="networkidle")
            return ctx,page,calls
        async def check_leader_clock(page):
            await page.locator('#tab-leaders').click()
            await page.locator('#mode-leaders .oew-skel').wait_for(state="detached",timeout=5000)
            stamps=await page.locator('#mode-leaders .oew-asof').all_text_contents()
            report["checks"].append({"name":"leaders_session_not_build_clock","pass":bool(stamps) and all(x.strip()=="2026-08-12" for x in stamps),"observed_dates":stamps,"session_date":"2026-08-12","build_date":"2026-11-02"})
        ctx,page,calls=await context()
        if args.only=="source_clocks":
            await check_leader_clock(page)
            await ctx.close();await browser.close()
            report["passed"]=sum(x["pass"] for x in report["checks"]);report["failed"]=[x["name"] for x in report["checks"] if not x["pass"]]
            (HERE/("runtime-"+args.label+".json")).write_text(json.dumps(report,indent=2),encoding="utf-8")
            print(json.dumps(report,indent=2));return
        await page.locator('#tab-brief').focus();await page.keyboard.press("ArrowRight")
        selected=await page.locator('.oew-tab[aria-selected="true"]').get_attribute("data-mode")
        report["checks"].append({"name":"keyboard_tabs","pass":selected=="flow","observed":selected})
        await page.locator('#tab-scanner').click()
        await page.locator('#mode-scanner .oew-tbl tbody tr').first.wait_for(timeout=5000)
        details=page.locator('#oew-sc-more')
        if await details.count():
            if not await details.get_attribute("open"):await details.locator('summary').click()
        await page.locator('#oew-f-q').fill("AAPL")
        rows=await page.locator('#mode-scanner .oew-tbl tbody tr').all_text_contents()
        async with page.expect_download() as downloaded:await page.locator('#oew-sc-csv').click()
        download=await downloaded.value
        path=await download.path();csv_text=Path(path).read_text()
        csv_rows=list(csv.reader(io.StringIO(csv_text)))
        report["checks"].append({"name":"scanner_filter_csv","pass":len(rows)==1 and "AAPL" in rows[0] and len(csv_rows)==2 and any("AAPL" in c for c in csv_rows[1]),"rows":len(rows),"csv_rows":len(csv_rows)})
        await page.locator('#oew-f-clear').click()
        reset_rows=await page.locator('#mode-scanner .oew-tbl tbody tr').count()
        report["checks"].append({"name":"scanner_clear","pass":reset_rows==4,"rows":reset_rows})
        for tab in ["flow","leaders","ticker"]:
            await page.locator('#tab-'+tab).click()
            await page.locator('#mode-'+tab+' .oew-skel').wait_for(state="detached",timeout=5000)
            text=await page.locator('#mode-'+tab).inner_text()
            report["checks"].append({"name":tab+"_loads","pass":len(text)>100 and "That data did not load" not in text,"characters":len(text)})
        await check_leader_clock(page)
        await ctx.close()
        ctx,page,calls=await context("race")
        await page.goto(URL+"#ticker?t=SPY",wait_until="domcontentloaded")
        await page.goto(URL+"#ticker?t=QQQ",wait_until="domcontentloaded")
        await page.wait_for_timeout(2600)
        shown=await page.locator('#oew-tk-cnt').inner_text()
        report["checks"].append({"name":"ticker_latest_request_wins","pass":shown=="QQQ","observed":shown,"url":page.url})
        await ctx.close()
        ctx,page,calls=await context("dedupe")
        await page.locator('#tab-scanner').click();await page.locator('#tab-brief').click();await page.locator('#tab-scanner').click()
        await page.locator('#mode-scanner .oew-tbl tbody tr').first.wait_for(timeout=5000)
        n=calls.get("screenerdata/rows.json",0)
        report["checks"].append({"name":"dedupe_inflight_scanner","pass":n==1,"requests":n})
        await ctx.close()
        ctx,page,calls=await context("hang")
        await page.locator('#tab-scanner').click()
        retry=page.locator('#mode-scanner').get_by_role("button",name=re.compile("retry|try again",re.I))
        try:
            await retry.first.wait_for(timeout=25000)
            await retry.first.click()
            await page.locator('#mode-scanner .oew-tbl tbody tr').first.wait_for(timeout=5000)
            recovered=True
        except PlaywrightTimeout:recovered=False
        report["checks"].append({"name":"hanging_request_recovers_with_retry","pass":recovered,"requests":calls.get("screenerdata/rows.json",0)})
        await ctx.close();await browser.close()
    report["passed"]=sum(x["pass"] for x in report["checks"]);report["failed"]=[x["name"] for x in report["checks"] if not x["pass"]]
    out=HERE/("runtime-"+args.label+".json");out.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
asyncio.run(main())
