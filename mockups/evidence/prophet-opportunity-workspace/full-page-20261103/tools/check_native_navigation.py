"""Exercise the actual emitted navigation offline, including keyboard and no-JS paths."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse,hashlib,json,subprocess,sys,time
from playwright.sync_api import sync_playwright
cli=argparse.ArgumentParser(description=__doc__)
cli.add_argument("--workspace",type=Path,required=True)
cli.add_argument("--site",type=Path,required=True)
cli.add_argument("--source-head",required=True)
cli.add_argument("--output",type=Path,required=True)
a=cli.parse_args()
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=a.workspace,text=True).strip()==a.source_head
assert not a.output.exists(),"Use a new evidence directory; do not overwrite an earlier observation."
a.output.mkdir(parents=True)
sys.path.insert(0,str(a.workspace))
from scripts.capture_page_evidence import serve_site_dir,state_seed_source
server,port=serve_site_dir(a.site)
origin=f"http://127.0.0.1:{port}"
results=[]
def rect_script():
    return """() => {
 const rect=e=>{if(!e)return null;const r=e.getBoundingClientRect();const s=getComputedStyle(e);return {x:r.x,y:r.y,width:r.width,height:r.height,display:s.display,visibility:s.visibility,opacity:s.opacity}};
 const nav=document.querySelector('.site-nav,.topbar');
 return {viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,
 layout:nav?.getAttribute('data-nav-layout'),nav:rect(nav),
 search:rect(nav?.querySelector('.nav-search')),controls:rect(nav?.querySelector('.nav-ctrls')),
 wordmark:rect(nav?.querySelector('.brand-word')),
 links:[...(nav?.querySelector('.nav-links')?.children||[])].filter(e=>getComputedStyle(e).display!=='none').map(e=>({text:e.innerText.slice(0,60),rect:rect(e)}))};
}"""
def check(row,name,condition,details=None):
    row["checks"].append({"name":name,"passed":bool(condition),"details":details})
def new_page(browser,width,js=True,theme="light"):
    c=browser.new_context(viewport={"width":width,"height":900 if width>900 else 844},java_script_enabled=js,color_scheme=theme,service_workers="block")
    c.route("**/*",lambda r:r.continue_() if urlsplit(r.request.url).netloc==f"127.0.0.1:{port}" and not urlsplit(r.request.url).path.startswith("/premiumdata/") else r.abort())
    if js:c.add_init_script(state_seed_source({"theme":theme,"locale":"en"}))
    p=c.new_page()
    return c,p
try:
 with sync_playwright() as pw:
    browser=pw.chromium.launch()
    for width in (768,1000,1100,1101,1440):
      row={"case":f"native-{width}","scope":"Native anonymous inventory, no DOM changes","checks":[]}
      context,page=new_page(browser,width)
      try:
        page.goto(origin+"/us_stocks.html",wait_until="domcontentloaded")
        page.locator(".nav-search[data-ticker-search-ready='1']").wait_for(state="visible")
        page.evaluate("document.fonts.ready");page.wait_for_timeout(500)
        m=page.evaluate(rect_script());row["metrics"]=m
        check(row,"no page overflow",m["documentWidth"]<=width+1,m["documentWidth"])
        if width==768:
          check(row,"tablet search fills navigation",abs(m["search"]["width"]-m["nav"]["width"])<2,m["search"])
        search=page.locator(".nav-search .search-trigger")
        search.click()
        field=page.locator(".nav-search .ticker-input")
        field.wait_for(state="visible");field.fill("AAPL")
        check(row,"search accepts input",field.input_value()=="AAPL")
        check(row,"search advertises expanded",search.get_attribute("aria-expanded")=="true")
        page.keyboard.press("Escape");page.wait_for_timeout(100)
        check(row,"Escape closes search",search.get_attribute("aria-expanded")=="false")
        check(row,"Escape restores trigger focus",search.evaluate("(e)=>document.activeElement===e"))
        if width<=900:
          toggle=page.locator(".nav-toggle")
          toggle.click()
          check(row,"mobile menu opens",toggle.get_attribute("aria-expanded")=="true" and page.locator(".nav-links").is_visible())
          toggle.click()
          check(row,"mobile menu closes",toggle.get_attribute("aria-expanded")=="false")
        page.screenshot(path=str(a.output/(row["case"]+".png")))
        if width in (1000,1100,1101):
          # Controlled geometry fixture, not an authenticated user preference.
          page.evaluate("""() => {
            const links=document.querySelector('.nav-links');let marketKept=false;
            [...links.children].forEach(e=>{
              if(e.classList.contains('nav-brand'))return;
              if(e.classList.contains('nav-dd')&&!marketKept){marketKept=true;return;}
              e.style.display='none';
            });
            document.dispatchEvent(new Event('mmx-markets-change'));
          }""")
          page.wait_for_timeout(120)
          short=page.evaluate(rect_script());row["controlled_short_inventory"]=short
          check(row,"short inventory chooses one row",short["layout"]=="single",short["layout"])
          check(row,"short inventory restores wordmark",short["wordmark"]["display"]!="none" and short["wordmark"]["width"]>0,short["wordmark"])
          check(row,"short inventory stays within viewport",short["documentWidth"]<=width+1)
          page.screenshot(path=str(a.output/(row["case"]+"-controlled-short.png")))
      except Exception as exc:
        check(row,"browser flow completes",False,str(exc))
      finally:
        results.append(row);context.close()
    for route in ("us_stocks.html","chat.html"):
      for width in (390,1000):
        row={"case":f"no-js-{route[:-5]}-{width}","scope":"Native emitted HTML with browser JavaScript disabled","checks":[]}
        context,page=new_page(browser,width,js=False)
        try:
          page.goto(origin+"/"+route,wait_until="domcontentloaded")
          m=page.evaluate(rect_script());row["metrics"]=m
          check(row,"no page overflow",m["documentWidth"]<=width+1,m["documentWidth"])
          check(row,"market inventory displayed",page.locator(".site-nav .nav-links").is_visible())
          seen=[];reached=False
          for step in range(75):
            page.keyboard.press("Tab")
            focus=page.evaluate("""() => {const e=document.activeElement;const r=e.getBoundingClientRect();const s=getComputedStyle(e);return {tag:e.tagName,href:e.getAttribute('href'),text:e.innerText?.slice(0,70),visible:!!r.width&&!!r.height&&s.visibility!=='hidden'&&Number(s.opacity)>0}}""")
            seen.append(focus)
            if focus["href"]=="us_stocks.html":
              reached=focus["visible"];break
          row["keyboard_path"]=seen
          check(row,"Stock Dashboard reachable by Tab",reached,seen[-1] if seen else None)
          page.screenshot(path=str(a.output/(row["case"]+".png")))
        except Exception as exc:check(row,"browser flow completes",False,str(exc))
        finally:results.append(row);context.close()
    # The vector family retains its own stylesheet and was not changed by this patch.
    # Capture its native navigation to detect spillover from shared partials.
    for width in (390,1000):
      row={"case":f"vector-{width}","scope":"Self-contained vector family, native enhancement","checks":[]}
      context,page=new_page(browser,width)
      try:
        page.goto(origin+"/vector.html",wait_until="domcontentloaded")
        page.wait_for_timeout(900)
        m=page.evaluate(rect_script());row["metrics"]=m
        check(row,"navigation exists",m["nav"] is not None)
        check(row,"navigation stays within viewport",m["nav"] and m["nav"]["x"]>=-1 and m["nav"]["x"]+m["nav"]["width"]<=width+1,m["nav"])
        page.screenshot(path=str(a.output/(row["case"]+".png")))
      except Exception as exc:check(row,"browser flow completes",False,str(exc))
      finally:results.append(row);context.close()
    browser.close()
finally:
 server.shutdown();server.server_close()
report={"source_head":a.source_head,"completed_at":time.time(),
 "html_sha256":{name:hashlib.sha256((a.site/name).read_bytes()).hexdigest() for name in ("us_stocks.html","chat.html","vector.html")},
 "scope":"Offline anonymous native publication paths. No account preference or authenticated entitlement acceptance. Controlled short-inventory cases test layout geometry only.",
 "results":results}
(a.output/"navigation-behavior.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
failed=[{"case":r["case"],"check":c} for r in results for c in r["checks"] if not c["passed"]]
print(json.dumps({"cases":len(results),"checks":sum(len(r["checks"]) for r in results),"failed":failed}),flush=True)
raise SystemExit(1 if failed else 0)
