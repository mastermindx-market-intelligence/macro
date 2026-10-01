#!/usr/bin/env python3
"""Supplement advanced-search windows with the account timeline cursor surface."""
from __future__ import annotations
import argparse, gzip, json, os, time, urllib.parse, urllib.request
from pathlib import Path

API = "https://api.twitterapi.io"
KEY_FILE = Path.home()/".config"/"mastermind"/"twitterapi_io.key"
ROOT = Path("/Volumes/Mastermind/vendor-sources/nextsignals")


def key():
    v=os.environ.get("TWITTERAPI_IO_KEY","").strip()
    return v or KEY_FILE.read_text().strip()


def get(k, params):
    url=API+"/twitter/user/last_tweets?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"X-API-Key":k,"User-Agent":"MMX-nextsignals-research/1.0"})
    last=None
    for n in range(7):
        try:
            with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
        except Exception as e:
            last=e; time.sleep(min(45,1.25*(2**n)))
    raise RuntimeError(last)


def rows(body):
    d=body.get("data")
    if isinstance(d,dict): return d.get("tweets") or []
    return d if isinstance(d,list) else body.get("tweets") or []


def cursor(body):
    d=body.get("data") if isinstance(body.get("data"),dict) else {}
    return body.get("next_cursor") or d.get("next_cursor") or body.get("nextCursor") or d.get("nextCursor")


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--handle",required=True); ap.add_argument("--root",type=Path,default=ROOT); ap.add_argument("--pause",type=float,default=.12); ap.add_argument("--max-pages",type=int,default=1000); a=ap.parse_args()
    k=key(); out=a.root/"raw"/"timeline_pages"/a.handle; out.mkdir(parents=True,exist_ok=True)
    seen_cursor=set(); seen_ids=set(); cur=None; page=0
    while page<a.max_pages:
        params={"userName":a.handle}
        if cur: params["cursor"]=cur
        body=get(k,params); page+=1
        rr=[x for x in rows(body) if isinstance(x,dict)]
        for t in rr:
            if t.get("id") is not None: seen_ids.add(str(t["id"]))
        with gzip.open(out/f"page_{page:04d}.json.gz","wt",encoding="utf-8") as f: json.dump(body,f,ensure_ascii=False,separators=(",",":"))
        nxt=cursor(body)
        if page%10==0 or not nxt: print(f"page={page} rows={len(rr)} unique={len(seen_ids)} next={bool(nxt)}",flush=True)
        if not nxt or nxt in seen_cursor: break
        seen_cursor.add(str(nxt)); cur=str(nxt); time.sleep(a.pause)
    (out/"DONE.json").write_text(json.dumps({"handle":a.handle,"pages":page,"unique_ids":len(seen_ids),"next_cursor":cur},indent=2))
    print(f"COMPLETE handle={a.handle} pages={page} unique={len(seen_ids)}",flush=True)
if __name__=="__main__": main()
