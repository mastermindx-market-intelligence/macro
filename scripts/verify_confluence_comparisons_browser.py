#!/usr/bin/env python3
"""Confluence paired baseline comparisons through actual rendered and served pages."""
from __future__ import annotations
import argparse, copy, hashlib, http.server, importlib.util, json, socketserver
import sys, threading, traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_confluence_screener import build_context, build_premium_payload, render_html
from scripts.verify_confluence_screener_browser import AUTH
from scripts.verify_confluence_compatibility_browser import FETCH_OBSERVER

spec = importlib.util.spec_from_file_location("comparison_fixture", ROOT/"tests/test_confluence_screener_page.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

def meta(path):
    b = path.read_bytes()
    return {"bytes":len(b), "sha256":hashlib.sha256(b).hexdigest(),
            "blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browser-executable")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    raw = copy.deepcopy(fixture._make_raw())
    mixed = copy.deepcopy(raw)
    mixed["combos"]["long"][0]["id"] = "L 0001"
    mixed["combos"]["long"][0]["h21"] = dict(fixture._H21_VALID, wr_mc_train=0.9)
    mixed["combos"]["long"][0].update(edge_wr_test=0.2, edge_wr_train=-0.02)
    mixed["combos"]["long"][1].update(edge_wr_test=-0.02, edge_wr_train=0.2)
    missing = copy.deepcopy(raw)
    missing["combos"]["long"][0].update(edge_wr_test=None, edge_wr_train=0.1)
    missing["combos"]["long"][1].update(edge_wr_test=0.15, edge_wr_train=None)
    missing["combos"]["long"][2].update(edge_wr_test=None, edge_wr_train=None)
    small = copy.deepcopy(raw)
    small["combos"]["long"][0].update(edge_wr_test=0, edge_wr_train=-0.0)
    small["combos"]["long"][1].update(edge_wr_test=0.00004, edge_wr_train=-0.00004)
    small["combos"]["long"][2].update(edge_wr_test=1e-12, edge_wr_train=-1e-12)
    variants = {"mixed":mixed,"missing":missing,"small":small}
    contexts = {key:build_context(value,{}) for key,value in variants.items()}
    pages = {key:render_html(ROOT,context).encode() for key,context in contexts.items()}
    expected = {
        "mixed":[("+20.0","-2.0"),("-2.0","+20.0"),("+10.0","+8.0")],
        "missing":[(None,"+10.0"),("+15.0",None),(None,None)],
        "small":[("0.0","0.0"),("+0.004","-0.004"),("+1e-10","-1e-10")],
    }
    real_raw = json.loads((ROOT/"site/factordata/tech_confluence.json").read_text())
    tiles = json.loads((ROOT/"site/marketdata/sp500_heatmap.json").read_text()).get("tiles",[])
    names = {t["t"]:t["name"] for t in tiles if t.get("t") and t.get("name")}
    contexts["served"] = build_context(real_raw,names)
    real_payload = json.loads((ROOT/"site/premiumdata/confluence_screener.json").read_text())
    assert real_payload == build_premium_payload(real_raw,names)
    expected["served"] = [
        tuple(None if c[key] is None else "0.0" if c[key]==0 else format(c[key],"+.2g" if abs(c[key])<0.1 else "+.1f")
              for key in ("edge_test_pp","edge_train_pp"))
        for c in contexts["served"]["combos"]
    ]

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT/"site"),**kw)
        def do_GET(self):
            parsed=urlsplit(self.path)
            if parsed.path.startswith("/premiumdata/"):
                self.send_response(403);self.end_headers();return
            key=parse_qs(parsed.query).get("comparison_fixture",[None])[0]
            if parsed.path=="/confluence_screener.html" and key in pages:
                body=pages[key];self.send_response(200)
                self.send_header("Content-Type","text/html; charset=utf-8")
                self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body);return
            super().do_GET()
        def log_message(self,*_):pass

    server=socketserver.ThreadingTCPServer(("127.0.0.1",0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    origin="http://127.0.0.1:"+str(server.server_address[1])
    plan=[(kind,width,lang,theme) for kind in variants for width,lang,theme in
          ((320,"en","dark"),(320,"zh","light"),(390,"en","light"),(390,"zh","dark"))]
    plan += [("mixed",1440,"en","dark"),("mixed",1440,"zh","light"),
             ("served",1440,"en","dark"),("served",320,"zh","light")]
    cases,captures,errors=[],[],[]
    count=0
    capture_keys={("mixed",320,"en"),("mixed",320,"zh"),("missing",320,"zh"),
                  ("small",320,"en"),("served",1440,"en"),("served",320,"zh")}
    try:
        with sync_playwright() as pw:
            options={"headless":True}
            if args.browser_executable:options["executable_path"]=args.browser_executable
            browser=pw.chromium.launch(**options)
            version=browser.version
            for kind,width,lang,theme in plan:
                name=kind+"-"+str(width)+"-"+lang
                case={"name":name,"kind":kind,"width":width,"lang":lang,"theme":theme}
                count+=1
                context=browser.new_context(viewport={"width":width,"height":900 if width>500 else 844},
                    device_scale_factor=1,is_mobile=width<=500,has_touch=width<=500,reduced_motion="reduce")
                context.route("**/*",lambda route:route.continue_() if urlsplit(route.request.url).hostname=="127.0.0.1" else route.abort())
                context.add_init_script("localStorage.setItem('lang',"+json.dumps(lang)+");localStorage.setItem('theme',"+json.dumps(theme)+");")
                context.add_init_script(FETCH_OBSERVER)
                page=context.new_page();page.set_default_timeout(6000)
                local_errors=[]
                page.on("pageerror",lambda e:(local_errors.append(str(e)),errors.append(str(e))))
                requests=[]
                armed={"value":False}
                def protected(route):
                    if not armed["value"]:
                        route.fulfill(status=403,content_type="application/json",body="{}");return
                    requests.append(route.request.url)
                    route.fulfill(content_type="application/json",body=json.dumps(real_payload))
                page.route("**/premiumdata/confluence_screener.json",protected)
                try:
                    query="" if kind=="served" else "?comparison_fixture="+kind
                    page.goto(origin+"/confluence_screener.html"+query,wait_until="load")
                    card=page.locator(".lc").first
                    case["before"]=page.evaluate("""() => ({
                        overflow:document.documentElement.scrollWidth>innerWidth+1,
                        oldMeters:document.querySelectorAll('.w10').length,
                        cards:Array.from(document.querySelectorAll('.lc')).map(c=>({
                            text:c.innerText,
                            height:c.getBoundingClientRect().height,
                            rateRows:Array.from(c.querySelectorAll('.lc-wr-big,.lc-wr-old')).map(v=>({y:v.getBoundingClientRect().y,height:v.getBoundingClientRect().height})),
                            sampleRows:Array.from(c.querySelectorAll('.lc-sample')).map(v=>({y:v.getBoundingClientRect().y,height:v.getBoundingClientRect().height})),
                            comparisons:Array.from(c.querySelectorAll('.lc-baseline-value')).map(v=>({
                                period:v.dataset.period,state:v.dataset.state,text:v.innerText,
                                box:{x:v.getBoundingClientRect().x,y:v.getBoundingClientRect().y,width:v.getBoundingClientRect().width,height:v.getBoundingClientRect().height},
                                clientWidth:v.clientWidth,scrollWidth:v.scrollWidth,
                                fontSize:getComputedStyle(v).fontSize,color:getComputedStyle(v).color,
                                term:v.previousElementSibling?.textContent
                            }))
                        }))
                    })""")
                    if (kind,width,lang) in capture_keys:
                        file=name+".png"
                        card.screenshot(path=str(out/file))
                        captures.append({"file":file,"kind":kind,"width":width,"lang":lang,"theme":theme})
                    assert not case["before"]["overflow"],case["before"]
                    assert len(case["before"]["cards"])==3,case["before"]
                    for idx,c in enumerate(case["before"]["cards"]):
                        values=c["comparisons"]
                        assert len(c["rateRows"])==2 and abs(c["rateRows"][0]["y"]-c["rateRows"][1]["y"])<1,c
                        assert len(c["sampleRows"])==2 and abs(c["sampleRows"][0]["y"]-c["sampleRows"][1]["y"])<1,c
                        assert len(values)==2,{"classification":"PAIRED_COMPARISON_MISSING","card":idx,"observed":values}
                        assert [v["period"] for v in values]==["recent","older"],values
                        for value,want in zip(values,expected[kind][idx]):
                            target=want if want is not None else ("Unavailable" if lang=="en" else "暂无数据")
                            assert value["text"]==target,{"card":idx,"actual":value,"expected":target}
                            state="missing" if want is None else "zero" if want=="0.0" else "negative" if want.startswith("-") else "positive"
                            assert value["state"]==state,value
                            assert value["scrollWidth"]<=value["clientWidth"]+1,value
                            assert value["term"] and value["box"]["width"]>70,value
                        assert abs(values[0]["box"]["y"]-values[1]["box"]["y"])<1,values
                        assert values[1]["box"]["x"]>values[0]["box"]["x"]+values[0]["box"]["width"],values
                        row=page.locator(".lc").nth(idx)
                        expect(row.locator(".lc-baseline-heading")).to_be_visible()
                        expect(row.locator(".lc-wr-unit")).to_be_visible()
                        assert row.locator(".lc-era").count()==2 and row.locator(".lc-sample").count()==2
                        assert row.locator(".lc-wr-big").count()==1 and row.locator(".lc-wr-old").count()==1
                        for period_index,source_key in ((0,"test"),(1,"train")):
                            era=row.locator(".lc-era").nth(period_index)
                            want=contexts[kind]["combos"][idx]
                            sample=era.locator(".lc-sample").inner_text()
                            assert str(want["months_"+source_key]) in sample and str(want["n_"+source_key]) in sample
                        assert row.locator(".lc-baselines").evaluate("""node => {
                            const refs=(node.getAttribute('aria-labelledby')||'').trim().split(/\\s+/);
                            return refs.length===1 && document.getElementById(refs[0])===node.closest('.lc').querySelector('.lc-baseline-heading');
                        }"""), "Comparison heading must resolve as one ID reference"
                    assert case["before"]["oldMeters"]==0
                    assert "in 10 recently" not in page.locator(".ledger").inner_text()
                    if kind=="missing":
                        assert ("Recent-period comparison unavailable" if lang=="en" else "近年时期比较暂无数据") in card.inner_text()
                    if kind=="mixed":
                        assert ("Above baseline only in the recent period" if lang=="en" else "仅近年高于基准") in card.inner_text()
                        assert "9.0" in card.locator(".lc-wr-old").inner_text()
                    summary=card.locator(".lc-method summary")
                    box=summary.bounding_box();assert box and box["height"]>=44
                    summary.focus();summary.press("Enter")
                    expect(card.locator(".lc-method")).to_have_attribute("open","")
                    method=card.locator(".lc-method").inner_text()
                    assert ("same stocks on random dates" if lang=="en" else "相同股票随机选择日期入场") in method
                    assert ("not investment returns" if lang=="en" else "并非投资收益率") in method
                    summary.press("Enter")
                    expect(card.locator(".lc-method")).not_to_have_attribute("open","")
                    if kind=="served":
                        public_before=page.locator(".lc-wr").all_inner_texts()
                        page.evaluate(AUTH);armed["value"]=True
                        page.evaluate("window.__d04Auth('comparison-owner','SIGNED_IN')")
                        page.wait_for_function("window.__compatJsonReads>0")
                        expect(page.locator("#confluence-access-status")).to_have_attribute("data-state","loaded")
                        paid=page.locator(".lc.gated a.tkr").evaluate_all("nodes=>nodes.map(n=>n.getAttribute('href'))")
                        want=["stocks/"+t["ticker"]+".html" for c in real_payload["combos"] for t in c["active_tickers"]]
                        assert paid==want and len(requests)==1,{"actual":paid,"expected":want,"requests":requests}
                        page.evaluate("window.__d04Auth(null,'SIGNED_OUT')")
                        assert page.locator(".locked[data-confluence-combo]").count()==2
                        assert page.locator(".lc-wr").all_inner_texts()==public_before
                        case["served_pair"]={"actual_saved_files":True,"controlled_auth":True,"requests":len(requests),"matching_protected_links":len(paid),"signout_public_evidence_unchanged":True}
                    link=card.locator("a.tkr").first
                    destination=link.get_attribute("href")
                    page.route("**/stocks/*",lambda route:route.fulfill(content_type="text/html",body="<h1>Local company route proof</h1>"))
                    link.focus();link.press("Enter")
                    page.wait_for_url("**/"+destination)
                    case["company_navigation"]={"href":destination,"final_path":urlsplit(page.url).path}
                    assert not local_errors,local_errors
                    case["status"]="PASS"
                except Exception as exc:
                    case.update(status="FAIL",error=str(exc),trace=traceback.format_exc(limit=3))
                finally:context.close()
                cases.append(case)
            browser.close()
    finally:server.shutdown();server.server_close()
    assert count==len(plan)==16
    for c in captures:c.update(meta(out/c["file"]))
    paths=["templates/confluence_screener.html.j2","tests/test_confluence_screener_page.py",
           "scripts/build_confluence_screener.py","scripts/verify_confluence_comparisons_browser.py",
           "scripts/verify_confluence_compatibility_browser.py","site/confluence_screener.html",
           "site/premiumdata/confluence_screener.json"]
    report={"schema":"confluence_paired_comparisons_browser/v1","observed_at":datetime.now(timezone.utc).isoformat(),
            "browser":version,"contexts":count,"cases":cases,"captures":captures,"page_errors":errors,
            "passed":sum(c["status"]=="PASS" for c in cases),"failed":sum(c["status"]=="FAIL" for c in cases),
            "sources":{p:meta(ROOT/p) for p in paths},
            "scope":"14 synthetic actual-render/template cases plus 2 actual saved current-input HTML/protected-JSON cases. All auth/HTTP controlled; company route intercepted locally. No production deployment or real entitlement claim."}
    (out/"browser-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"passed":report["passed"],"failed":report["failed"],"contexts":count,
        "page_errors":len(errors),"report":str(out/"browser-report.json"),
        "failures":[{"name":c["name"],"error":c["error"][:400]} for c in cases if c["status"]=="FAIL"]},ensure_ascii=False))
    return 1 if report["failed"] else 0

if __name__=="__main__":raise SystemExit(main())
