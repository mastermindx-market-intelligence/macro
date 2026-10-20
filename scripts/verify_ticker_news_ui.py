"""Render and exercise the shipped ticker-news consumer using labeled fixtures.

No provider, production auth, or external network calls. Uses an installed
Playwright runtime. Screenshots are interaction proof, not live-data proof.
"""
from __future__ import annotations
import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]


def row(story, title, *, low=False, count=1):
    return {
        "sequence": 10+story, "source": "benzinga", "publisher": "Benzinga",
        "source_item_id": str(story), "story_id": "story-"+str(story),
        "source_count": count, "item_count": count, "title": title,
        "url": "https://example.test/report/"+str(story),
        "teaser": "Preview fixture: reporting stays readable with room for context, source attribution and the underlying reports.",
        "published_at": "2026-10-20T10:00:00Z", "updated_at": None,
        "received_at": "2026-10-20T10:00:01Z", "universe_revision": "fixture",
        "quality": {"score": 35 if low else 85, "low_value": low,
                    "reason": "routine_options_template" if low else None},
    }


def snapshot(ticker="NVDA"):
    return {"schema": "ticker_news.snapshot.v1", "ticker": ticker,
            "security_id": "fixture-"+ticker, "state": "live",
            "rows": [row(1,"Nvidia announces a new data-center accelerator",count=2),
                     row(2,"Nvidia receives regulatory approval for a new facility"),
                     row(3,"Nvidia whale alerts from today's trading session",low=True)],
            "next_cursor": 10, "has_more": True,
            "source_health": {"state": "live",
                              "additional_sources": [{"provider":"massive","state":"available"}]}}


def document():
    env = Environment(loader=FileSystemLoader(ROOT/"templates"), autoescape=True)
    env.globals["t"] = lambda en,zh="": Markup('<span class="l-en">')+escape(en)+Markup('</span><span class="l-zh">')+escape(zh or en)+Markup("</span>")
    markup = env.get_template("ticker_news_panel.html.j2").render(ticker="",nav_prefix="")
    css = (ROOT/"templates/ticker_news.css").read_text()
    js = (ROOT/"templates/ticker_news.js").read_text()
    return """<!doctype html><html lang="en" data-theme="dark" data-lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}body{margin:0;padding:24px;background:var(--bg);color:var(--text);font-family:system-ui}
:root{--bg:#080e19;--panel:#101927;--panel2:#192639;--line:#2a384c;--text:#edf3fd;--muted:#a4b2c7;--link:#98bcff;--up:#72ddb7;--warn:#f1c77d}
:root[data-theme=light]{--bg:#f2f5fa;--panel:#fff;--panel2:#edf2f9;--line:#d6dfeb;--text:#1a2b43;--muted:#536781;--link:#285dba;--up:#197d5c;--warn:#936014}
.l-zh{display:none}[data-lang=zh] .l-en{display:none}[data-lang=zh] .l-zh{display:inline}
main{max-width:1180px;margin:auto}.fixture{font:12px/1.6 system-ui;color:var(--muted);margin:0}
@media(max-width:600px){body{padding:12px}}
</style><style>"""+css+"""</style></head><body><main><p class="fixture">INTERACTION PREVIEW · FICTIONAL NEWS FIXTURES · NO PRODUCTION DATA</p>"""+markup+"""</main><script>
window.MDXAuth={client:async()=>({auth:{getSession:async()=>({data:{session:{access_token:"fixture-only"}}})}})};
</script><script>"""+js+"""</script></body></html>"""


async def verify(destination: Path):
    destination.mkdir(parents=True,exist_ok=True)
    checks=[]; errors=[]; requests=[]
    state={"packet":snapshot(),"status":200,"stream_event":None,"snapshot_count":0}
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True)
        context=await browser.new_context(viewport={"width":1440,"height":1100},device_scale_factor=1)
        page=await context.new_page()
        page.on("pageerror",lambda error:errors.append(str(error)))
        async def route(request):
            url=request.request.url
            if url.startswith("https://news-fixture.test/api/ticker-news/"):
                requests.append({"url":url,"authorized":request.request.headers.get("authorization")=="Bearer fixture-only"})
                if "/stream?" in url:
                    event=state["stream_event"]
                    state["stream_event"]=None
                    body=": heartbeat\n\n" if event is None else "event: upsert\ndata: "+json.dumps(event)+"\n\n"
                    await request.fulfill(status=200,content_type="text/event-stream",body=body)
                elif "/stories/" in url:
                    story=url.split("/")[-1]
                    members=[deepcopy(state["packet"]["rows"][0]),deepcopy(state["packet"]["rows"][0])]
                    members[1].update(source="massive:reuters.com",publisher="Reuters",source_item_id="wire-1",title="Second publisher's report on the same event")
                    await request.fulfill(json={"schema":"ticker_news.story.v1","story_id":story,"source_count":2,"item_count":2,"members":members})
                else:
                    state["snapshot_count"]+=1
                    packet=deepcopy(state["packet"])
                    ticker=url.split("/api/ticker-news/")[1].split("?")[0]
                    packet["ticker"]=ticker
                    if "cursor=" in url:
                        packet["rows"]=[row(4,"Earlier reporting remains accessible")]
                        packet["has_more"]=False;packet["next_cursor"]=None
                    if ticker=="AAPL":packet["rows"]=[row(5,"Apple reporting after a ticker change")]
                    await request.fulfill(status=state["status"],json=packet if state["status"]==200 else {"detail":"fixture access denied"})
            elif url.startswith("https://news-fixture.test/"):
                await request.fulfill(content_type="text/html",body=document())
            else:
                await request.abort()
        await page.route("**/*",route)
        await page.goto("https://news-fixture.test/#NVDA")
        await page.locator(".tn-row").first.wait_for()
        assert await page.locator(".tn-row").count()==2
        checks.append("high signal retains event reporting and all reporting remains available")
        await page.locator('[data-tn-filter="all"]').click()
        assert await page.locator(".tn-row").count()==3
        await page.locator('[data-tn-filter="signal"]').click()
        await page.locator(".tn-group summary").focus()
        await page.keyboard.press("Enter")
        await page.get_by_text("Second publisher's report on the same event",exact=True).wait_for()
        assert await page.locator(".tn-member").count()==2
        checks.append("keyboard expansion retrieves both publisher reports from shared story API")
        await page.screenshot(path=str(destination/"desktop-dark.png"),full_page=True)
        await page.locator("[data-tn-more]").click()
        await page.get_by_text("Earlier reporting remains accessible",exact=True).wait_for()
        assert await page.locator("[data-tn-latest]").is_visible()
        await page.locator("[data-tn-latest]").click()
        await page.locator(".tn-row").first.wait_for()
        checks.append("earlier reporting and return to live view")
        await page.evaluate("document.documentElement.dataset.theme='light'")
        await page.set_viewport_size({"width":390,"height":844})
        assert await page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        await page.screenshot(path=str(destination/"phone-light.png"),full_page=True)
        checks.append("390px phone layout has no horizontal overflow")
        await page.evaluate("document.documentElement.dataset.lang='zh';document.dispatchEvent(new Event('langchange'))")
        await page.set_viewport_size({"width":1440,"height":1100})
        await page.screenshot(path=str(destination/"desktop-chinese.png"),full_page=True)
        assert await page.locator(".tn-filters").get_attribute("aria-label")=="新闻覆盖"
        checks.append("Chinese labels and dynamic accessibility labels")
        await page.evaluate("location.hash='AAPL'")
        await page.get_by_text("Apple reporting after a ticker change",exact=True).wait_for()
        assert not await page.get_by_text("Nvidia announces a new data-center accelerator",exact=True).count()
        checks.append("ticker changes purge prior company content")
        state["status"]=403
        await page.locator("[data-tn-retry]").evaluate("(node)=>{node.hidden=false;node.click()}")
        await page.wait_for_function("document.querySelector('[data-tn-status]').dataset.state==='restricted'")
        assert await page.locator(".tn-row").count()==0
        checks.append("denied access immediately purges stories")
        await page.screenshot(path=str(destination/"restricted.png"),full_page=True)
        state["status"]=200
        state["packet"]["rows"][0]["title"]='<img src=x onerror="window.fixtureXSS=true"> Safe plain headline'
        await page.evaluate("location.hash='NVDA'")
        await page.get_by_text(state["packet"]["rows"][0]["title"],exact=True).wait_for()
        assert await page.locator(".tn-rows img").count()==0
        assert not await page.evaluate("Boolean(window.fixtureXSS)")
        checks.append("provider text renders as text without script or image execution")
        assert all(x["authorized"] for x in requests)
        assert not errors, errors
        await context.close();await browser.close()
    report={"schema":"ticker_news.ui_verification.v1","observed_at":datetime.now(timezone.utc).isoformat(),
            "proof_scope":"headless browser, fictional fixtures, shipped consumer bytes; no production/auth/provider claim",
            "checks":checks,"page_errors":errors,"request_count":len(requests),
            "source_sha256":{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
                             ("templates/ticker_news.js","templates/ticker_news.css","templates/ticker_news_panel.html.j2")},
            "screenshots":["desktop-dark.png","phone-light.png","desktop-chinese.png","restricted.png"]}
    (destination/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--evidence-dir",type=Path,required=True)
    asyncio.run(verify(parser.parse_args().evidence_dir))
