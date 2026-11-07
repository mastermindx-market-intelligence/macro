"""Inspect expanded research states against the exact published-data fixture.
No provider requests, live browser sessions, or production writes.
"""
import hashlib,json,subprocess
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs
from playwright.sync_api import sync_playwright
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCE=HERE/"fixtures"/"published"
PAYLOADS=json.loads((SOURCE/"payloads.json").read_text())
OUT=HERE/"visual-candidate-expanded";OUT.mkdir(exist_ok=True)
ORIGIN="http://127.0.0.1:8768"
checks=[]
def record(case,name,passed,**evidence):
    checks.append({"case":case,"name":name,"pass":bool(passed),**evidence})
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    for w,h,theme,lang in [(1440,1000,"light","en"),(390,844,"dark","zh"),(390,844,"light","en")]:
        case=f"{w}-{theme}-{lang}"
        ctx=browser.new_context(viewport={"width":w,"height":h},service_workers="block")
        def route(r):
            clean=r.request.url.split("?")[0]
            key=next((k for k in PAYLOADS if clean.endswith("/"+k)),None)
            if key:r.fulfill(status=200,content_type="application/json",body=json.dumps(PAYLOADS[key]))
            elif r.request.url.startswith(ORIGIN+"/"):r.continue_()
            else:r.abort()
        ctx.route("**/*",route)
        page=ctx.new_page();errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.goto(ORIGIN+"/mockups/options_workspace_revamp/fixtures/published/workspace.html?"+urlencode({"theme":theme,"lang":lang})+"#brief",wait_until="networkidle")
        def capture(name,selector):
            page.locator(selector).first.evaluate("e=>e.scrollIntoView({block:'center',behavior:'instant'})")
            page.screenshot(path=str(OUT/f"{case}-{name}.png"),animations="disabled")
            size=page.evaluate("({width:innerWidth,scroll:document.documentElement.scrollWidth})")
            record(case,name+" document containment",size["scroll"]<=w+1,**size)
        summary=page.locator("#oew-sources>summary");summary.focus();page.keyboard.press("Enter")
        record(case,"sources opens by keyboard",page.locator("#oew-sources").get_attribute("open") is not None and summary.evaluate("e=>document.activeElement===e"),dates=page.locator(".oew-source-row time").all_text_contents())
        capture("sources","#oew-sources")
        page.keyboard.press("Enter")
        page.locator('[data-open-details="oew-history"]').click()
        record(case,"history action opens and focuses disclosure",page.locator("#oew-history").get_attribute("open") is not None and page.locator("#oew-history>summary").evaluate("e=>document.activeElement===e"))
        capture("history","#oew-history")
        spy=page.locator(".oew-ic").filter(has=page.locator('[data-goto="SPY"]'))
        lab=spy.locator(".oew-lab>summary");lab.focus();page.keyboard.press("Enter")
        record(case,"payoff retains both source dates",spy.locator(".oew-lab").get_attribute("open") is not None and spy.locator(".oew-lab-foot time").count()==2,dates=spy.locator(".oew-lab-foot time").all_text_contents())
        if w<760:
            sizes=spy.evaluate("e=>({card:e.getBoundingClientRect().width,grid:e.parentElement.clientWidth})")
            record(case,"expanded mobile payoff uses full card row",abs(sizes["card"]-sizes["grid"])<2,**sizes)
        capture("payoff",".oew-ic:has([data-goto=SPY]) .oew-lab")
        lab.focus();page.keyboard.press("Enter")
        spy.evaluate("e=>e.scrollIntoView({block:'center',behavior:'instant'})")
        reach=spy.evaluate("""card=>{
          const orb=document.querySelector('#mmb-boot,#mmb-launch'),box=orb?.getBoundingClientRect();
          const items=[...card.querySelectorAll('.oew-ic-px,.oew-ic-regime,.oew-ic-levels .v,.oew-ic-em')].map(e=>{
          const r=e.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2;return {text:e.innerText,in_view:r.top>=0&&r.bottom<=innerHeight,covered:!!box&&x>=box.left&&x<=box.right&&y>=box.top&&y<=box.bottom}});
          return {items,all_reachable:items.every(x=>x.in_view&&!x.covered)};}""")
        record(case,"index evidence reachable with shared assistant",reach["all_reachable"],**reach)
        for mode in ["flow","scanner","ticker","leaders"]:
            page.mouse.move(12,h-120)
            page.locator("#tab-"+mode).evaluate("e=>e.scrollIntoView({block:\'center\',behavior:\'instant\'})")
            page.locator("#tab-"+mode).click()
            page.locator("#mode-"+mode+" .oew-skel").wait_for(state="detached",timeout=20000)
            if mode=="flow":
                count=page.locator("#mode-flow canvas").count()
                empty=page.locator("#oew-fl-unfold .oew-fl-null").count()
                record(case,"tide history and honest intraday availability",page.locator("#oew-fl-spark").count()==1 and (count==2 or empty==1),canvas_count=count,intraday_unavailable=bool(empty))
                capture("tides","#oew-fl-spark")
            elif mode=="scanner":
                more=page.locator("#oew-sc-more>summary");more.focus();page.keyboard.press("Enter")
                number=page.locator("#oew-sc-more input[type=number]").count()
                record(case,"advanced ranges remain available",number==21,count=number)
                capture("filters","#oew-sc-more")
                for view in ["ovr","flow","pos"]:
                    page.locator('.oew-seg button[data-view="'+view+'"]').click()
                    wrap=page.locator(".oew-tblwrap")
                    dims=wrap.evaluate("e=>{e.scrollLeft=e.scrollWidth;return {width:e.clientWidth,scroll:e.scrollWidth,left:e.scrollLeft}}")
                    count=page.locator(".oew-tbl th:visible").count()
                    record(case,"scanner "+view+" columns reachable",count>=7 and (dims["scroll"]<=dims["width"]+1 or dims["left"]>0),visible_headers=count,**dims)
                    capture("scanner-"+view,".oew-tblwrap")
            elif mode=="ticker":
                shelf=page.locator("#oew-shelf>summary");shelf.focus();page.keyboard.press("Enter")
                page.wait_for_function("document.querySelector('#oew-raw-slot')?.textContent.length>0")
                svg=page.locator("#oew-raw-slot svg").count()
                record(case,"raw structure rendered on disclosure",page.locator("#oew-shelf").get_attribute("open") is not None and svg>=1,svg=svg,sections=page.locator("#oew-raw-slot h3").all_text_contents())
                capture("structure","#oew-raw-slot")
                link=page.locator("#mode-ticker .oew-handoff a")
                href=link.get_attribute("href")
                query=parse_qs(urlparse(href).query)
                record(case,"live terminal has selected symbol and exact return path",query.get("sym")==["SPY"] and query.get("ret")==[page.url] and query.get("from")==["macro"],href=href)
            else:
                count=page.locator("#mode-leaders [data-expand]").count()
                for i in range(count):
                    b=page.locator("#mode-leaders [data-expand]").nth(i);b.click()
                    record(case,"leader expansion "+str(i),b.get_attribute("aria-expanded")=="true")
                capture("leaders","#mode-leaders .oew-panel")
        record(case,"expanded-state browser has no page errors",not errors,errors=errors)
        ctx.close()
    browser.close()
report={"git_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"template_sha256":hashlib.sha256((ROOT/"templates/options.html.j2").read_bytes()).hexdigest(),"builder_sha256":hashlib.sha256((ROOT/"scripts/build_options_command.py").read_bytes()).hexdigest(),"fixture_manifest":json.loads((SOURCE/"manifest.json").read_text()),"checks":checks}
(OUT/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps({"checks":len(checks),"passed":sum(c["pass"] for c in checks),"failed":[c for c in checks if not c["pass"]]},indent=2))
raise SystemExit(0 if all(c["pass"] for c in checks) else 1)