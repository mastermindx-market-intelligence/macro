"""Loopback-only visual test harness. All headlines below are illustrative fixtures."""
from __future__ import annotations
import json
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

import jinja2
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from app import news_desk

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / ".tmp" / "news-desk-preview"
PREVIEW.mkdir(parents=True, exist_ok=True)
now = datetime.now(timezone.utc)
fixtures = [
("Energy markets weigh supply risks as shipping routes face renewed disruption","能源市场评估供应风险，航运路线再受干扰","Reuters","https://reuters.com/example-energy","energy",["XOM","CVX"],"Oil markets are assessing the possible effect of shipping delays on supply. The extent and duration of any disruption remain uncertain.","Energy costs can transmit into inflation, transport margins and rate expectations. Watch physical flows and official statements before extrapolating.",True),
("Central bank minutes point to a cautious path for the next policy decision","央行会议纪要显示下次政策决定将保持审慎","Federal Reserve","https://federalreserve.gov/example-minutes","central_banks",[],"Committee members discussed the balance between inflation progress and employment risks. The minutes describe a range of views.","Policy communication may influence rate expectations. These minutes are a record of a prior meeting, not a new rate decision.",True),
("Semiconductor companies outline a new round of investment in capacity","半导体企业规划新一轮产能投资","Bloomberg","https://bloomberg.com/example-chips","technology",["NVDA","TSM"],"Several chipmakers discussed capacity plans and demand visibility at an industry event.","Separate announced plans from committed capital spending and delivered capacity.",True),
("European officials discuss changes to trade and industrial policy","欧洲官员讨论贸易与产业政策调整","Financial Times","https://ft.com/example-trade","geopolitics",[],"Officials outlined proposals for consultation. Final measures and implementation dates have not been announced.","Monitor the official text and consultation timetable. Proposals may change before implementation.",False),
("Japan manufacturers report mixed demand across export markets","日本制造商报告出口市场需求分化","Nikkei Asia","https://asia.nikkei.com/example-demand","economy",[],"Manufacturers described differences between domestic and overseas order books.","The reporting provides company-level observations rather than an economy-wide forecast.",False),
("Major US lender reports quarterly results and updates its outlook","美国大型银行发布季度业绩并更新展望","CNBC","https://cnbc.com/example-results","companies",["JPM"],"The lender discussed credit conditions, funding costs and customer activity.","Compare management's forward-looking statements with the reported period and previous guidance.",False),
("Negotiators continue ceasefire talks as humanitarian access remains limited","停火谈判继续，人道援助通道仍受限制","BBC News","https://bbc.com/example-talks","geopolitics",[],"Diplomatic discussions continued, with several terms still under negotiation.","Distinguish confirmed official agreements from negotiating positions and attributed statements.",False),
("Brazil policymakers review inflation risks ahead of the next meeting","巴西政策制定者在下次会议前评估通胀风险","Reuters","https://reuters.com/example-brazil","central_banks",[],"Policymakers highlighted inflation expectations and external financial conditions.","The next official statement will provide the current policy decision.",False),
("European natural-gas traders monitor storage and weather forecasts","欧洲天然气交易员关注库存与天气预报","Bloomberg","https://bloomberg.com/example-gas","energy",[],"Markets assessed seasonal storage levels alongside changing weather forecasts.","Weather expectations can change quickly; compare forecasts with actual consumption.",False),
("India services businesses describe resilient domestic orders","印度服务业企业表示国内订单保持韧性","Reuters","https://reuters.com/example-india","economy",[],"Businesses reported differences across domestic and international demand.","Survey responses describe the sample's conditions and are subject to revision.",False),
("African finance ministers discuss infrastructure funding priorities","非洲财长讨论基础设施融资重点","IMF","https://imf.org/example-africa","economy",[],"Officials discussed the sequencing and financing of infrastructure programmes.","Funding proposals are distinct from approved projects or committed disbursements.",False),
("Software companies face closer scrutiny of contract renewal rates","软件公司合同续约率受到更密切关注","Financial Times","https://ft.com/example-software","companies",["MSFT"],"Investors examined renewal commentary and the timing of large customer contracts.","Contract definitions and reporting periods differ; compare like-for-like measures.",False),
("China publishes an update on industrial production and retail activity","中国发布工业生产与零售活动更新","Reuters","https://reuters.com/example-china","economy",[],"The statistical release covered industrial and consumer activity across the latest reporting period.","Use the official release's units and revision notes for quantitative comparisons.",True),
("Copper producers describe changing demand from power and construction","铜生产商描述电力与建筑需求变化","Financial Times","https://ft.com/example-copper","energy",[], "Companies reported contrasting demand patterns across end markets.","Distinguish management observations from independently reported industry totals.",False),
]
stories = []
for i,(title,zh,name,url,category,tickers,brief,why,important) in enumerate(fixtures):
    published = (now - timedelta(minutes=2+i*7)).isoformat()
    stories.append({"schema":"intelligence.story_packet/v1","id":"preview-story-"+str(i),
      "headline":title,"headline_zh":zh,"category":category,"stage":"high_impact" if important else "developing",
      "source_name":name,"url":url,"first_seen":published,"updated_at":published,"published_at":published,
      "brief":brief,"why_it_matters_en":why,"tickers":tickers,"source_count":1,
      "evidence":[{"event_id":"preview-event-"+str(i),"name":name,"url":url,"headline":title,"published_at":published}]})
path = PREVIEW / "intelligence.json"
if not path.exists():
    path.write_text(json.dumps({"schema":"intelligence.desk/v1","updated_at":now.isoformat(),
      "health":{"state":"quiet","last_source_published_at":stories[0]["published_at"]},"stories":stories}))
os.environ["MM_NEWS_DESK_SNAPSHOT"] = str(path)
env = jinja2.Environment(loader=jinja2.FileSystemLoader(ROOT / "templates"),autoescape=False)
env.globals.update(td=lambda x:x,tr=lambda x:x)
app = FastAPI()
app.include_router(news_desk.router)
app.dependency_overrides[news_desk.require_desk_user] = lambda: {"id":"loopback-visual-test"}
@app.get("/news.html")
def preview_page():
    html = env.get_template("news.html.j2").render(news_feed=stories,macro_news={"fetched_at":now.isoformat()})
    html = html.replace('Intelligence / Global coverage','Design preview / Illustrative reporting').replace('情报 / 全球报道','设计预览 / 示例报道')
    html = html.replace('Publication times are shown in your local time.','Design specimen · Illustrative reporting').replace('发布时间按你的本地时间显示。','设计样本 · 示例报道')
    # Fixture-only broker; this module is never imported by app.main or a service.
    html = html.replace('</body>', '<script>window.MDXAuth = Object.assign({}, window.MDXAuth, {client: async function(){return {auth:{getSession: async function(){return {data:{session:{access_token:"visual-fixture-only"}}};}}};}});</script></body>')
    return HTMLResponse(html,headers={"Cache-Control":"no-store"})
from fastapi import HTTPException
from fastapi.responses import FileResponse
PUBLIC_ASSETS = {"theme.css","theme.js","navigation-refresh.css","product-nav-icons.css",
 "logo_config.js","stock-logos.js","dashboard-icons.css","dashboard-icons.js",
 "supabase.js","account.js","nav_market.js","data_base.js","live.js","live_config.js","favicon.svg"}
@app.get("/api/ticker-news/{ticker}")
def company_fixture(ticker: str, cursor: int | None = None):
    symbol = ticker.upper()
    titles = ["Semiconductor company outlines its next generation of data-center systems", "Suppliers discuss capacity plans as demand for advanced chips develops", "Investors examine margins, order visibility and the timing of new products"]
    rows = [{"story_id":"specimen-company-"+str(i), "sequence":30-i, "title":title, "teaser":"Illustrative reporting for interface review. This is a design fixture, not a current company announcement.", "url":"https://example.com/report-"+str(i), "source":"Example wire", "source_count":1, "item_count":1, "published_at":(now-timedelta(minutes=4+i*17)).isoformat(), "updated_at":None, "received_at":now.isoformat()} for i,title in enumerate(titles)]
    return {"schema":"ticker_news.snapshot.v1", "ticker":symbol, "security_id":"specimen-security", "state":"quiet", "rows":rows, "has_more":False, "next_cursor":None, "source_health":{"state":"specimen"}, "flow":{"schema":"ticker_news.flow.v1", "state":"ok", "coverage":"complete", "as_of":now.strftime("%Y-%m-%dT%H:%M:%SZ"), "reports_24h":24, "stories_24h":8, "reports_7d":118, "daily_counts_28d":[4,8,5,9,6,7,3,12,9,14,8,6,10,5,7,9,8,18,15,9,12,7,11,14,9,16,21,24], "comparison":"busier", "provenance":{"windows":{"daily_28d":{"start_date":"2026-09-20","end_date":"2026-10-17"}}}}}

@app.get("/api/ticker-news/{ticker}/stream")
def company_stream_fixture(ticker: str):
    import asyncio
    from fastapi.responses import StreamingResponse
    async def frames():
        for _ in range(50):
            yield ": " + (" " * 2048) + "\n\n"
            await asyncio.sleep(1)
    return StreamingResponse(frames(), media_type="text/event-stream", headers={"Cache-Control":"private, no-store", "X-Accel-Buffering":"no"})

@app.get("/{asset:path}")
def preview_asset(asset: str):
    target = (ROOT / "templates" / asset).resolve()
    fonts = (ROOT / "templates" / "fonts").resolve()
    if asset not in PUBLIC_ASSETS and not (target.is_relative_to(fonts) and target.suffix == ".woff2"):
        raise HTTPException(404)
    if not target.is_file():
        raise HTTPException(404)
    return FileResponse(target)
