"""Controlled qbus-commit-to-SSE fanout benchmark; not provider-to-screen latency."""
from __future__ import annotations
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import ticker_news
from app.ticker_news_stream import SharedChangeReader
from engine.qbus_news_contract import normalize_news
from engine.qbus_news_store import NewsStore, RoutedRevision


def distribution(values):
    values=sorted(values)
    def percentile(p):return values[min(len(values)-1,round((len(values)-1)*p))]
    return {"samples":len(values),"p50_ms":round(statistics.median(values),2),
            "p95_ms":round(percentile(.95),2),"p99_ms":round(percentile(.99),2),
            "max_ms":round(max(values),2)}


async def measure(path, *, readers, events, interval, shared):
    now=datetime.now(timezone.utc); db=path/"q.db"; receipt=path/"rights.json"
    with NewsStore(db, source_key="benchmark"):pass
    receipt.write_text(json.dumps({
        "schema":"qbus.news_rights_receipt.v1","receipt_id":"benchmark-fixture","owner_ref":"fixture-only",
        "source":"benzinga","provider":"alpaca","status":"approved","product_id":"fixture",
        "audiences":["site_full"],"effective_at":(now-timedelta(hours=1)).isoformat(),
        "expires_at":(now+timedelta(hours=1)).isoformat(),
        "capabilities":{"internal_ingestion":True,"historical_retention":True,"headline_display":True,
                        "source_link_display":True,"teaser_display":True,"derivative_processing":False},
    }))
    os.environ.update(MM_TICKER_NEWS_DB=str(db),MM_TICKER_NEWS_RIGHTS=str(receipt),
                      MM_TICKER_NEWS_ADDITIONAL_RIGHTS="[]")
    ticker_news._security_or_404=lambda *args,**kwargs:("NVDA","sec-NVDA")
    actual_reads=0;calls=0;ready=asyncio.Event()
    class Reader:
        def __init__(self):self.shared=SharedChangeReader(ttl_seconds=.05)
        async def read(self,key,fn):
            nonlocal actual_reads,calls
            calls+=1
            if calls>=readers:ready.set()
            def counted():
                nonlocal actual_reads
                actual_reads+=1
                return fn()
            return await self.shared.read(key,counted) if shared else await asyncio.to_thread(counted)
    ticker_news._STREAM_CHANGE_READER=Reader()
    started={};delays=[];commit_cost=[]
    async def consume():
        seen=set()
        async for chunk in ticker_news._sse_events(ticker="NVDA",user={},after_sequence=0,poll_seconds=interval):
            if chunk.startswith("event: upsert"):
                p=json.loads(next(line[6:] for line in chunk.splitlines() if line.startswith("data: ")))
                key=p["source_item_id"]
                if key in started and key not in seen:
                    seen.add(key);delays.append((time.perf_counter()-started[key])*1000)
                if len(seen)==events:return
    tasks=[asyncio.create_task(consume()) for _ in range(readers)]
    await asyncio.wait_for(ready.wait(),5)
    await asyncio.sleep(.03)
    for n in range(events):
        stamp=datetime.now(timezone.utc);item=str(n)
        revision=normalize_news({
            "id":item,"title":"Nvidia wins $"+str(1000+n)+" million supply contract",
            "url":"https://example.test/"+item,"created":stamp.isoformat(),
            "updated":stamp.isoformat(),"stocks":["NVDA"],
        },transport="benzinga_rest",received_at=stamp)
        def commit():
            with NewsStore(db, source_key="benchmark") as store:
                store.commit_observations((RoutedRevision(revision,("sec-NVDA",),"fixture"),))
        started[item]=time.perf_counter()
        await asyncio.to_thread(commit)
        commit_cost.append((time.perf_counter()-started[item])*1000)
        await asyncio.sleep(.025)
    await asyncio.wait_for(asyncio.gather(*tasks),10)
    return {"poll_seconds":interval,"shared_reads":shared,"subscribers":readers,"events":events,
            "receive_before_commit_to_sse":distribution(delays),"commit_duration":distribution(commit_cost),
            "database_reads":actual_reads,"subscriber_read_requests":calls}


async def main(output,readers,events):
    with tempfile.TemporaryDirectory(prefix="ticker-news-benchmark-") as temporary:
        root=Path(temporary);(root/"control").mkdir();(root/"candidate").mkdir()
        control=await measure(root/"control",readers=readers,events=events,interval=1.0,shared=False)
        candidate=await measure(root/"candidate",readers=readers,events=events,interval=.1,shared=True)
    result={"schema":"qbus.news_latency_benchmark.v1","observed_at":datetime.now(timezone.utc).isoformat(),
            "platform":platform.platform(),"proof_scope":"controlled local SQLite-to-SSE fanout; both arms use current projection and authorization; excludes vendor, WAN, Terminal BFF and browser paint",
            "control":control,"candidate":candidate}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
    p.add_argument("--readers",type=int,default=32);p.add_argument("--events",type=int,default=24)
    args=p.parse_args();asyncio.run(main(args.output,args.readers,args.events))
