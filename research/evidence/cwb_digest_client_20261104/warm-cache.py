"""Targeted delivery proof using real HTTP cache and unmodified generated pages/assets.
No Playwright routing, production service, login or outbound provider calls.
The loopback origin applies a restrictive response CSP to isolate external dependencies.
"""
from __future__ import annotations
import asyncio, collections, hashlib, json, mimetypes, pathlib, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, unquote, parse_qs
from playwright.async_api import async_playwright

ROOT=pathlib.Path(sys.argv[1]).resolve()
OUT=pathlib.Path(sys.argv[2]).resolve()
OUT.mkdir(parents=True,exist_ok=True)
BASE="7b3a8d4049fa00f3e498589b5468e82a2d2dc0a3"
SITE=ROOT/"site"
PAGES=[
 ("root_loader","macro_business_activity.html"),
 ("root_direct","about-research.html"),
 ("nested_loader","basket/ai_agents.html"),
 ("nested_direct","blog/compound-growth-for-traders.html"),
 ("depth_two_direct","learn/options/charm-and-time-drift.html"),
 ("depth_three_direct","stocks/earnings/weekly/2026-03-09.html"),
]
def sha(data): return hashlib.sha256(data).hexdigest()
def old(rel): return subprocess.check_output(["git","show",BASE+":"+rel],cwd=ROOT)
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==BASE
new_assets={n:(SITE/n).read_bytes() for n in ("theme.js","account.js")}
old_assets={n:old("site/"+n) for n in new_assets}
versions={n:sha(b)[:8] for n,b in new_assets.items()}
assert versions=={"theme.js":"8ca5bdfd","account.js":"fec5541f"},versions
assert b"fec5541f" in new_assets["theme.js"]
old_pages={p:old("site/"+p) for _,p in PAGES}
new_pages={p:(SITE/p).read_bytes() for _,p in PAGES}
phase={"value":"old"}
requests=[]
csp="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self' data:; frame-src 'none'; object-src 'none'; base-uri 'self'"
class Handler(BaseHTTPRequestHandler):
    protocol_version="HTTP/1.1"
    def log_message(self,*args): pass
    def do_GET(self):
        u=urlsplit(self.path); rel=unquote(u.path).lstrip("/")
        status=200; cache="no-store"; asset=None
        if rel in new_assets:
            asset=rel
            is_new=parse_qs(u.query).get("v")==[versions[rel]]
            body=(new_assets if is_new else old_assets)[rel]
            cache="public, max-age=31536000, immutable"
        elif rel in new_pages:
            body=(new_pages if phase["value"]=="new" and parse_qs(u.query).get("fixture")!=["old-control"] else old_pages)[rel]
        else:
            path=(SITE/rel).resolve()
            if path.is_relative_to(SITE) and path.is_file():
                body=path.read_bytes()
                if path.suffix in (".js",".css"): cache="public, max-age=31536000, immutable"
            else:
                body=b"fixture unavailable";status=404
        if asset: requests.append({"phase":phase["value"],"url":self.path,"sha256":sha(body),"status":status})
        self.send_response(status)
        self.send_header("Content-Type",(mimetypes.guess_type(rel)[0] or "application/octet-stream")+"; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Cache-Control",cache)
        self.send_header("Content-Security-Policy",csp)
        self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass

server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
server.daemon_threads=True
thread=threading.Thread(target=server.serve_forever,daemon=True)
thread.start()
origin="http://127.0.0.1:"+str(server.server_port)
cases=[];errors=[];body_tasks=set()
async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch()
        try:
            for name,path in PAGES:
                context=await browser.new_context(viewport={"width":1280,"height":900},service_workers="block")
                page=await context.new_page();page.set_default_timeout(12000)
                cdp=await context.new_cdp_session(page);await cdp.send("Network.enable")
                cache_events=[];responses=[];page_errors=[]
                cdp.on("Network.requestServedFromCache",lambda e:cache_events.append(e))
                page.on("pageerror",lambda e:page_errors.append(str(e)[:300]))
                async def capture(response):
                    if urlsplit(response.url).path in ("/account.js","/theme.js"):
                        try: responses.append({"url":response.url,"status":response.status,"sha256":sha(await response.body())})
                        except Exception as e: errors.append({"kind":"response_body","detail":str(e)[:200]})
                def on_response(r):
                    task=asyncio.create_task(capture(r));body_tasks.add(task)
                    task.add_done_callback(body_tasks.discard)
                page.on("response",on_response)
                async def visit(label):
                    await page.goto(origin+"/"+path+"?fixture="+label,wait_until="load",timeout=20000)
                    await page.wait_for_function("!!window.MMAccount")
                    # Resource completion is the condition; no fixed cache/poll sleep.
                    await page.wait_for_function("Array.from(document.scripts).some(s=>/account\\.js(?:\\?|$)/.test(s.src))")
                    if body_tasks: await asyncio.gather(*list(body_tasks))
                    return await page.evaluate("""() => ({
                      scripts:Array.from(document.scripts).map(s=>s.src).filter(u=>/\\/(account|theme)\\.js(?:\\?|$)/.test(u)),
                      resources:performance.getEntriesByType('resource').filter(e=>/\\/(account|theme)\\.js(?:\\?|$)/.test(e.name)).map(e=>({url:e.name,transferSize:e.transferSize,decodedBodySize:e.decodedBodySize})),
                      moduleReady:!!window.MMAccount
                    })""")
                phase["value"]="old";start=len(requests)
                before=await visit("old-first")
                seed=requests[start:].copy()
                assert any("/theme.js?" in r["url"] for r in seed),seed
                assert any("/account.js?" in r["url"] for r in seed),seed
                for r in seed:
                    n=urlsplit(r["url"]).path.lstrip("/")
                    assert r["sha256"]==sha(old_assets[n]),r
                count=len(requests)
                repeat=await visit("old-repeat")
                assert len(requests)==count,{"unexpected_old_refetch":requests[count:]}
                assert any(e["transferSize"]==0 and e["decodedBodySize"]>0 for e in repeat["resources"]),repeat
                phase["value"]="new"
                control=await visit("old-control")
                assert len(requests)==count,{"control_unexpected_refetch":requests[count:]}
                assert not context.service_workers
                responses.clear();count=len(requests)
                after=await visit("new-first")
                fetched=requests[count:].copy()
                wanted={"/theme.js?v="+versions["theme.js"],"/account.js?v="+versions["account.js"]}
                # Direct and dynamic forms must resolve to the one root resource.
                assert {urlsplit(u).path+"?"+urlsplit(u).query for u in after["scripts"]}==wanted,after
                assert wanted.issubset({r["url"] for r in fetched}),fetched
                for n,body in new_assets.items():
                    assert any(r["url"].endswith("/"+n+"?v="+versions[n]) and r["sha256"]==sha(body) for r in responses),(n,responses)
                count=len(requests)
                new_repeat=await visit("new-repeat")
                assert len(requests)==count,{"unexpected_new_refetch":requests[count:]}
                assert len(new_repeat["resources"])>=2
                assert all(e["transferSize"]==0 and e["decodedBodySize"]>0 for e in new_repeat["resources"]),new_repeat
                cases.append({"case":name,"page":path,"status":"PASS","old_html_sha256":sha(old_pages[path]),"new_html_sha256":sha(new_pages[path]),
                              "seed_requests":seed,"new_requests":fetched,"old_reference_control_after_deployment_change":control,"service_workers_blocked":True,"old_repeat":repeat,"new_first":after,"new_repeat":new_repeat,
                              "chromium_cache_events":len(cache_events),"page_errors":page_errors[:12]})
                print(json.dumps({"case":name,"status":"PASS","old_cache_hit":True,"new_payloads_exact":True,"new_cache_hit":True}),flush=True)
                await context.close()
            return browser.version
        finally:await browser.close()
started=time.monotonic()
result={"base":BASE,"origin":origin,"fixture_scope":"Unmodified generated HTML and JS on loopback with external-dependency CSP; no authenticated production claim","playwright_routing_used":False,"versions":versions,"asset_sha256":{n:sha(b) for n,b in new_assets.items()}}
try:
    result["chromium"]=asyncio.run(asyncio.wait_for(main(),timeout=150))
    assert len(cases)==len(PAGES) and not errors
    result["status"]="PASS"
except BaseException as exc:
    result["status"]="FAIL";result["error"]=type(exc).__name__+": "+str(exc)[:2000]
    raise
finally:
    server.shutdown();server.server_close();thread.join(timeout=3)
    result.update(cases=cases,errors=errors,server_stopped=not thread.is_alive(),seconds=round(time.monotonic()-started,2))
    receipt=OUT/"warm-cache.json";receipt.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"receipt":str(receipt),"sha256":sha(receipt.read_bytes()),"status":result["status"],"cases":len(cases),"server_stopped":result["server_stopped"]}),flush=True)
