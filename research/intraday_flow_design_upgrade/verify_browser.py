"""Real-browser regression checks for the Intraday Flow redesign.

Runs against an owned loopback preview, using anonymous isolated browser contexts.
Scenario responses are explicitly synthetic TEST FIXTURES; they are never written
to site/ or presented as production market observations. The normal-layout cases
use committed source snapshots. This is functional proof, not Paper or live proof.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
NOW="2026-11-02T15:15:00.000Z"
NOW_MS=1793632500000
results=[]

def check(name, passed, **details):
    results.append({"check":name,"passed":bool(passed),**details})
    print(name+(": PASS" if passed else ": FAIL"),flush=True)
    if not passed:
        raise AssertionError(name+": "+json.dumps(details,ensure_ascii=False))

def visible_count(page):
    return page.locator("#leaders-body tr.lead-row:visible").count()

def source_context(browser, theme="light", locale="en", width=1440):
    context=browser.new_context(viewport={"width":width,"height":900 if width>760 else 844},
        reduced_motion="reduce")
    context.add_init_script("localStorage.setItem('theme',"+json.dumps(theme)+");localStorage.removeItem('themeAuto');localStorage.setItem('lang',"+json.dumps(locale)+");")
    return context

def await_board(page):
    page.wait_for_selector("#leaders-body tr.lead-row:visible",timeout=15000)
    page.wait_for_timeout(500)

def refresh_focus(context,page,selector,key):
    pending=[]
    body=(ROOT/"site/live/quotes.json").read_text()
    context.route("**/live/quotes.json*",lambda route:pending.append(route))
    context.route("**/live/intraday_quotes.json*",lambda route:pending.append(route))
    page.locator("#ift-refresh").click()
    page.wait_for_timeout(100)
    page.evaluate("""() => {
      window.__focusTrace=[];
      if(!window.__focusTraceInstalled){
        for(const event of ['focusin','focusout'])document.addEventListener(event,e=>{window.__focusTrace.push({event,id:e.target.id,tag:e.target.tagName});});
        new MutationObserver(()=>window.__focusTrace.push({event:'mutation',id:document.activeElement.id,tag:document.activeElement.tagName})).observe(document.getElementById('leaders-body'),{childList:true});
        window.__focusTraceInstalled=true;
      }
    }""")
    page.locator(selector).focus()
    check(key+"/requested",bool(pending))
    initial=page.evaluate("(selector)=>document.activeElement===document.querySelector(selector)",selector)
    check(key+"/focused-before-response",initial,active=page.evaluate("document.activeElement.outerHTML.slice(0,240)"))
    for route in pending:route.fulfill(status=200,content_type="application/json",body=body)
    page.wait_for_timeout(250)
    preserved=page.evaluate("(selector)=>document.activeElement===document.querySelector(selector)",selector)
    detail={} if preserved else page.evaluate("({active:document.activeElement.outerHTML.slice(0,240),trace:window.__focusTrace.slice(-15)})")
    check(key+"/preserved",preserved,**detail)
    context.unroute("**/live/quotes.json*");context.unroute("**/live/intraday_quotes.json*")

def menu_not_clipped(page,key):
    page.locator("#ift-theme-menu > summary").click()
    last=page.locator('button[data-basket="power_grid"]')
    last.scroll_into_view_if_needed()
    geometry=last.evaluate("""(el)=>{
      const r=el.getBoundingClientRect(),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
      return {visible:el===hit||el.contains(hit),bottom:r.bottom,viewport:innerHeight};
    }""")
    check(key,geometry["visible"] and geometry["bottom"]<=geometry["viewport"],**geometry)
    page.keyboard.press("Escape")

def layout_and_controls(browser, url, theme, locale, width):
    context=source_context(browser,theme,locale,width)
    page=context.new_page()
    errors=[]
    page.set_default_timeout(6000)
    page.on("pageerror",lambda error:errors.append(str(error)))
    page.goto(url,wait_until="domcontentloaded")
    await_board(page)
    key=f"{width}/{theme}/{locale}"
    check(key+"/language",page.locator("html").get_attribute("data-lang")==locale)
    check(key+"/theme",page.locator("html").get_attribute("data-theme")==theme)
    check(key+"/cap",visible_count(page)==8,count=visible_count(page))
    geometry=page.evaluate("""() => {
      const rows=[...document.querySelectorAll('tr.lead-row')].filter(r=>r.getBoundingClientRect().height>0);
      const nav=document.querySelector('.site-nav');
      const navBottom=nav?nav.getBoundingClientRect().bottom:0;
      return {width:innerWidth,scrollWidth:document.documentElement.scrollWidth,
        navBottom,firstTop:rows[0].getBoundingClientRect().top,
        visibleRows:rows.filter(r=>r.getBoundingClientRect().bottom<=innerHeight).length};
    }""")
    check(key+"/no-overflow",geometry["scrollWidth"]<=width,**geometry)
    if width==1440:
        check(key+"/scan-proximity",geometry["firstTop"]-geometry["navBottom"]<=300,**geometry)
        check(key+"/six-rows",geometry["visibleRows"]>=6,**geometry)
    else:
        check(key+"/metric-labels",page.locator("tr.lead-row:visible .ift-mobile-metric-label").first.is_visible())
        # Query and measure in one browser task: async rendering may replace a
        # previously resolved element between separate protocol calls.
        boxes=page.evaluate("""() => [...document.querySelectorAll('tr.lead-row')]
          .filter(row=>row.getBoundingClientRect().height>0).map(row=>{
            const r=row.querySelector('.expander').getBoundingClientRect();
            return {x:r.x,y:r.y,width:r.width,height:r.height};
          })""")
        check(key+"/touch-target",len(boxes)==8 and all(b["height"]>=44 and b["width"]>=44 for b in boxes),boxes=boxes)
        check(key+"/evidence-clear-of-assistant",all(b["x"]+b["width"]<315 for b in boxes),box=boxes[0])

    if width>760:
        original=page.locator('th[data-col="rvol"]').get_attribute("aria-sort")
        page.locator("#ift-activity-help").press("Enter")
        check(key+"/activity-help-keyboard",page.locator("#ift-activity-tip").evaluate('(el)=>el.matches(":popover-open")'))
        check(key+"/activity-help-does-not-sort",page.locator('th[data-col="rvol"]').get_attribute("aria-sort")==original)
        page.keyboard.press("Escape")
        check(key+"/activity-help-escape",not page.locator("#ift-activity-tip").evaluate('(el)=>el.matches(":popover-open")'))

    search=page.locator("#ift-search")
    search.fill("ZZZ_NO_MATCH")
    check(key+"/empty-filter",page.locator(".ift-empty-row").is_visible() and visible_count(page)==0)
    page.locator("[data-reset-filters]").click()
    check(key+"/reset",visible_count(page)==8 and search.input_value()=="")
    check(key+"/reset-focus",page.evaluate("document.activeElement.id")=="ift-search")

    menu=page.locator("#ift-theme-menu > summary")
    menu.click()
    check(key+"/themes-open",page.locator("#ift-theme-menu").get_attribute("open") is not None)
    page.keyboard.press("Escape")
    check(key+"/themes-escape",page.locator("#ift-theme-menu").get_attribute("open") is None)
    menu.click()
    page.locator('button[data-basket="defense"]').click()
    rows=page.locator("tr.lead-row:visible")
    baskets=rows.evaluate_all("(rows)=>rows.map(r=>r.getAttribute('data-baskets'))")
    check(key+"/theme-filter",bool(baskets) and all("defense" in b.split() for b in baskets),baskets=baskets)
    check(key+"/theme-menu-closes",page.locator("#ift-theme-menu").get_attribute("open") is None)
    page.locator("#ift-reset").click()
    if width>760:page.locator('th[data-col="ticker"] button').click()
    else:page.locator("#ift-mobile-sort").select_option("ticker-asc")
    names=page.locator("tr.lead-row:visible").evaluate_all("(rows)=>rows.map(r=>r.getAttribute('data-ticker'))")
    check(key+"/name-sort",names==sorted(names),names=names)
    check(key+"/sort-aria",page.locator('th[data-col="ticker"]').get_attribute("aria-sort")=="ascending")

    exp=page.locator("tr.lead-row:visible .expander").first
    tk=exp.get_attribute("data-exp")
    search.fill(tk)
    exp=page.locator("tr.lead-row:visible .expander").first
    menu_not_clipped(page,key+"/short-result-menu")
    if width>760:
        check(key+"/selected-name",page.locator("#ift-inspector h2").inner_text()==tk)
        page.locator("#ift-open-evidence").click()
        check(key+"/side-evidence-opens",page.locator('[data-detail="'+tk+'"]').is_visible())
        page.locator("#ift-open-evidence").click()
        check(key+"/side-evidence-closes",not page.locator('[data-detail="'+tk+'"]').is_visible())
        check(key+"/side-evidence-focus",page.evaluate("document.activeElement.id")=="ift-open-evidence")
    exp.press("Enter")
    check(key+"/keyboard-expansion",exp.get_attribute("aria-expanded")=="true")
    check(key+"/full-evidence",page.locator('[data-detail="'+tk+'"]').is_visible())
    states=page.locator('[data-detail="'+tk+'"] .check-state:visible').all_inner_texts()
    check(key+"/seven-explicit-states",len(states)==7 and all(s.strip() in ("Met","Not met","Unavailable","已满足","未满足","不可用") for s in states),states=states)
    for selector in (["#ift-open-evidence","#ift-stock-overview"] if width>760 else [])+["#ift-evidence-"+tk]:
        refresh_focus(context,page,selector,key+"/refresh-"+selector[1:])

    pending_quotes=[]
    quote_body=(ROOT/"site/live/quotes.json").read_text()
    context.route("**/live/quotes.json*",lambda route:pending_quotes.append(route))
    context.route("**/live/intraday_quotes.json*",lambda route:pending_quotes.append(route))
    page.locator("#ift-refresh").click()
    page.wait_for_timeout(100)
    exp=page.locator("tr.lead-row:visible .expander").first
    exp.focus()
    check(key+"/refresh-requested",bool(pending_quotes))
    for route in pending_quotes:route.fulfill(status=200,content_type="application/json",body=quote_body)
    page.wait_for_timeout(250)
    check(key+"/data-refresh-preserves-filter",search.input_value()==tk)
    check(key+"/data-refresh-preserves-expansion",page.locator('[data-detail="'+tk+'"]').is_visible())
    check(key+"/data-refresh-preserves-focus",page.evaluate("document.activeElement.getAttribute('data-exp')")==tk)
    context.unroute("**/live/quotes.json*");context.unroute("**/live/intraday_quotes.json*")
    new_locale="zh" if locale=="en" else "en"
    page.evaluate("(lang)=>window.setLang(lang)",new_locale)
    page.wait_for_timeout(150)
    check(key+"/language-preserves-expansion",page.locator('[data-detail="'+tk+'"]').is_visible())
    check(key+"/language-preserves-focus",page.evaluate("document.activeElement.getAttribute('data-exp')")==tk)
    page.locator('button.expander[data-exp="'+tk+'"]').press("Enter")
    check(key+"/collapse",not page.locator('[data-detail="'+tk+'"]').is_visible())

    search.fill("")
    page.locator("#ift-see-all").click()
    check(key+"/see-all",visible_count(page)==116,count=visible_count(page))
    ninth=page.locator("tr.lead-row:visible").nth(8).get_attribute("data-ticker")
    check(key+"/see-all-focuses-next-name",page.evaluate("document.activeElement.getAttribute('data-select')")==ninth)
    page.keyboard.press("Tab")
    check(key+"/see-all-tab-order",page.evaluate("document.activeElement.getAttribute('data-exp')")==ninth)
    page.locator("#ift-see-all").press("Enter")
    check(key+"/collapse-cap",visible_count(page)==8)
    check(key+"/collapse-focus",page.evaluate("document.activeElement.id")=="ift-see-all")
    refresh_focus(context,page,"#ift-see-all",key+"/refresh-count-control")
    check(key+"/no-script-errors",not errors,errors=errors)
    context.close()

def scenario(browser,url,name):
    base=json.loads((ROOT/"site/flowtracker/base.json").read_text())
    tickers=[r["ticker"] for r in base["leaders"]]
    context=source_context(browser)
    # Fixed session clock makes the existing classifier's time window deterministic.
    context.add_init_script("const RealDate=Date;window.Date=class extends RealDate {constructor(...args){super(...(args.length?args:["+json.dumps(NOW)+"]));}static now(){return "+str(NOW_MS)+";}};")
    if name=="empty":
        html=(ROOT/"site/intraday_flow.html").read_text()
        empty={**base,"leaders":[],"n_leaders":0}
        html=re.sub(r"var BASE_DATA = [\s\S]*?;\nvar RVOL_CONFIRM",lambda _: "var BASE_DATA = "+json.dumps(empty)+";\nvar RVOL_CONFIRM",html,count=1)
        context.route("**/intraday_flow.html",lambda route:route.fulfill(status=200,body=html,content_type="text/html"))
    quotes={tk:{"price":100.0+i,"changePct":0,"vol":100000,"hi":110.0+i,"lo":90.0+i,"ts":NOW_MS,"tsSynthetic":False,"delayMin":15} for i,tk in enumerate(tickers)}
    if name in ("missing","loading"):quotes={}
    elif name=="partial":quotes={tickers[0]:quotes[tickers[0]]}
    pulse={"schema":"flow_pulse/v1","as_of":NOW,"stale":name=="stale","tickers":[
        {"ticker":tk,"bars_today":30,"vwap":99.0+i,"rvol_tod":0.0 if i==0 else 1.4,"vol_durability":0.7,"higher_lows":2}
        for i,tk in enumerate(tickers)]}
    pending=[]
    def serve(route):
        path=urlparse(route.request.url).path
        if path.endswith("/quotes.json") or path.endswith("/intraday_quotes.json"):
            if name=="loading":pending.append(route);return
            route.fulfill(status=200,content_type="application/json",body=json.dumps({"quotes":quotes,"meta":{"source_asof":NOW}}))
        elif path.endswith("/flow_pulse.json"):
            if name=="loading":pending.append(route);return
            route.fulfill(status=200,content_type="application/json",body=json.dumps(pulse))
        elif "live_flow/" in path:
            route.fulfill(status=503,body="test fixture: options unavailable")
        else:route.continue_()
    context.route("**/*.json*",serve)
    page=context.new_page();errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    page.goto(url,wait_until="domcontentloaded")
    page.wait_for_timeout(600)
    title=page.locator("#hero-thesis").inner_text()
    if name=="empty":
        check("fixture/empty",page.locator("tr.lead-row").count()==0 and "scan is unavailable" in title,title=title)
        menu_not_clipped(page,"fixture/empty/menu-not-clipped")
    elif name=="loading":
        check("fixture/loading","Checking the latest observations" in title,title=title)
    elif name in ("missing","partial"):
        check("fixture/"+name,"Current prices are unavailable" in title,title=title)
        if name=="partial":
            page.locator("#ift-search").fill(tickers[0])
            check("fixture/partial-preserves-price","$100.00" in page.locator("tr.lead-row:visible .price-cell").inner_text())
    elif name=="stale":
        check("fixture/stale","Confirmation is incomplete" in title,title=title)
    elif name=="populated":
        check("fixture/populated","latest received observations" in title,title=title)
        page.locator("#ift-search").fill(tickers[0])
        activity=page.locator("tr.lead-row:visible .vol-cell").inner_text()
        check("fixture/zero-is-observed",("0.0" in activity or "0×" in activity) and "Unavailable" not in activity,activity=activity)
    check("fixture/"+name+"/no-current-action-claim","setups live" not in page.locator("main").inner_text())
    check("fixture/"+name+"/no-script-errors",not errors,errors=errors)
    for route in pending:
        try:route.abort()
        except Exception:pass
    page.wait_for_timeout(100)
    context.close()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--base-url",default="http://127.0.0.1:8767")
    parser.add_argument("--output",default="research/intraday_flow_design_upgrade/browser_verification.json")
    args=parser.parse_args()
    if urlparse(args.base_url).hostname not in ("127.0.0.1","localhost"):
        raise SystemExit("This isolated regression harness is restricted to a loopback preview.")
    url=args.base_url.rstrip("/")+"/intraday_flow.html"
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for width in (1440,390):
            for theme in ("light","dark"):
                for locale in ("en","zh"):
                    try:layout_and_controls(browser,url,theme,locale,width)
                    except Exception as e:
                        results.append({"check":f"{width}/{theme}/{locale}/exception","passed":False,"error":str(e)})
        for name in ("empty","loading","missing","partial","stale","populated"):
            try:scenario(browser,url,name)
            except Exception as e:
                results.append({"check":"fixture/"+name+"/exception","passed":False,"error":str(e)})
        browser.close()
    out=ROOT/args.output
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"evidence_kind":"isolated_browser_regression","source":"actual candidate plus explicit synthetic transport fixtures","checks":results},ensure_ascii=False,indent=2)+"\n")
    failures=[r for r in results if not r["passed"]]
    print(json.dumps({"checks":len(results),"passed":len(results)-len(failures),"failures":failures,"output":str(out)},ensure_ascii=False))
    return bool(failures)
if __name__=="__main__":
    raise SystemExit(main())
