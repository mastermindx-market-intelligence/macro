"""R3 native source-disclosure browser proof; fixtures never touch live feed files."""
from __future__ import annotations
import functools
import hashlib
import json
import threading
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
import verify_browser as existing

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'mockups/refs/intraday-flow-upgrade/source-details-r3'
checks=[]
NOW='2026-11-02T15:15:00.000Z'

def check(name,passed,**details):
    checks.append({'check':name,'passed':bool(passed),**details})
    print(name+(': PASS' if passed else ': FAIL'),flush=True)
    assert passed,name+': '+json.dumps(details,ensure_ascii=False)

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def fixture(context,state):
    leaders=json.loads((ROOT/'site/flowtracker/base.json').read_text())['leaders']
    names=[r['ticker'] for r in leaders]
    quotes={tk:{'price':0 if i==0 else 100+i,'vol':0,'changePct':0,'hi':110+i,'lo':90+i,'ts':1793632500000,'tsSynthetic':False,'delayMin':15} for i,tk in enumerate(names)}
    if state.get('partial'):quotes={names[0]:quotes[names[0]]}
    if state.get('missing'):quotes={}
    pulse={'schema':'flow_pulse/v1','as_of':NOW,'stale':not state.get('missing'),'tickers':[] if state.get('missing') else [
        {'ticker':tk,'bars_today':30,'vwap':99+i,'rvol_tod':0,'vol_durability':0.7,'higher_lows':2} for i,tk in enumerate(names)]}
    def quote_body():return json.dumps({'quotes':quotes,'meta':{'source_asof':state.get('quote_clock')}})
    state.update(counts={'quotes':0,'volume':0,'options':0},pending=[],quote_body=quote_body)
    def serve(route):
        path=urlparse(route.request.url).path
        if path.endswith(('/quotes.json','/intraday_quotes.json')):
            state['counts']['quotes']+=1
            if state.get('hold_quotes'):state['pending'].append(route);return
            body=quote_body()
        elif path.endswith('/flow_pulse.json'):
            state['counts']['volume']+=1;body=json.dumps(pulse)
        elif 'live_flow/' in path:
            # Existing off-hours model accepts a delivered legacy object. Model
            # unavailable transport with the same explicit503 used by baseline tests.
            state['counts']['options']+=1
            route.fulfill(status=503,content_type='text/plain',body='TEST FIXTURE: options source unavailable')
            return
        else:route.continue_();return
        route.fulfill(status=200,content_type='application/json',body=body)
    context.route('**/*.json*',serve)
    return names

def open_panel(page):
    page.locator('#ift-source-details-open').click()
    page.wait_for_function("document.getElementById('ift-source-panel').matches(':popover-open')")

def closed(page):
    page.wait_for_function("!document.getElementById('ift-source-panel').matches(':popover-open')")

def matrix(browser,url,width,theme,locale):
    key=f'{width}/{theme}/{locale}'
    context=existing.source_context(browser,theme,locale,width)
    state={};names=fixture(context,state)
    page=context.new_page();errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url,wait_until='domcontentloaded');existing.await_board(page)
    page.wait_for_function("document.querySelector('[data-source-lane=quotes] .is-received')!==null")
    page.wait_for_function("document.querySelector('[data-source-lane=options] .is-unavailable')!==null")
    page.locator('#ift-search').fill(names[0])
    check(key+'/observed-zero-preserved','$0.00' in page.locator('tr.lead-row:visible .price-cell').inner_text())
    open_panel(page)
    check(key+'/labelled-dialog',page.locator('#ift-source-panel').get_attribute('role')=='dialog' and page.locator('#ift-source-title').inner_text().strip()==('数据来源' if locale=='zh' else 'Source details'))
    check(key+'/expanded',page.locator('#ift-source-details-open').get_attribute('aria-expanded')=='true')
    check(key+'/initial-focus',page.evaluate('document.activeElement.id')=='ift-source-close')
    check(key+'/three-independent-feeds',page.locator('#ift-source-detail-rows [data-source-lane]').count()==3)
    check(key+'/price-received',page.locator('[data-source-lane=quotes] .is-received').count()==1)
    check(key+'/volume-stale',page.locator('[data-source-lane=tape] .is-stale').count()==1)
    check(key+'/options-unavailable',page.locator('[data-source-lane=options] .is-unavailable').count()==1)
    check(key+'/clock-not-invented',('时间不可用' if locale=='zh' else 'time unavailable') in page.locator('[data-source-lane=quotes] .ift-source-time').inner_text())
    check(key+'/volume-clock-retained','2026-11-02 15:15 UTC' in page.locator('[data-source-lane=tape] .ift-source-time').inner_text())
    bounds=page.evaluate('''() => {const panel=document.getElementById('ift-source-panel').getBoundingClientRect();return {
      pageWidth:document.documentElement.scrollWidth,top:panel.top,bottom:panel.bottom,left:panel.left,right:panel.right,
      height:innerHeight,actions:[...document.querySelectorAll('.ift-source-actions button,#ift-source-close')].map(el=>{
        const r=el.getBoundingClientRect();return {id:el.id,height:r.height,right:r.right,bottom:r.bottom};})};}''')
    check(key+'/viewport-fit',bounds['pageWidth']<=width and bounds['left']>=0 and bounds['right']<=width and bounds['top']>=0 and bounds['bottom']<=bounds['height'],bounds=bounds)
    check(key+'/44px-actions',all(x['height']>=44 and x['bottom']<=bounds['height'] for x in bounds['actions']),bounds=bounds)
    if width==390:check(key+'/assistant-clearance',all(x['right']<=315 for x in bounds['actions'] if x['id']!='ift-source-close'),bounds=bounds)
    page.screenshot(path=str(OUT/f'fixture-{width}-{theme}-{locale}.png'),full_page=False)
    page.keyboard.press('Escape');closed(page)
    check(key+'/escape-focus-return',page.evaluate('document.activeElement.id')=='ift-source-details-open')
    open_panel(page)
    before=dict(state['counts']);state['hold_quotes']=True
    page.locator('#ift-source-refresh').click();page.wait_for_timeout(100)
    check(key+'/refresh-existing-handler',len(state['pending'])==1 and state['counts']['quotes']-before['quotes']==1 and state['counts']['volume']-before['volume']==1,counts=state['counts'],before=before)
    state['quote_clock']=NOW;state['hold_quotes']=False
    for route in state['pending']:route.fulfill(status=200,content_type='application/json',body=state['quote_body']())
    page.wait_for_function("document.querySelector('[data-source-lane=quotes] .ift-source-time').textContent.includes('2026-11-02 15:15 UTC')")
    check(key+'/refresh-keeps-open',page.locator('#ift-source-panel').evaluate("el=>el.matches(':popover-open')"))
    check(key+'/refresh-keeps-focus',page.evaluate('document.activeElement.id')=='ift-source-refresh')
    check(key+'/scan-query-preserved',page.locator('#ift-search').input_value()==names[0])
    other='zh' if locale=='en' else 'en'
    page.evaluate("lang=>{document.documentElement.setAttribute('data-lang',lang);document.dispatchEvent(new Event('langchange'));}",other)
    check(key+'/language-keeps-open',page.locator('#ift-source-panel').evaluate("el=>el.matches(':popover-open')"))
    check(key+'/language-label',page.locator('#ift-source-close').get_attribute('aria-label')==('关闭数据来源' if other=='zh' else 'Close source details'))
    page.locator('#ift-source-back').click();closed(page)
    check(key+'/back-focus-return',page.evaluate('document.activeElement.id')=='ift-source-details-open')
    open_panel(page);page.locator('#ift-source-close').click();closed(page)
    check(key+'/close-focus-return',page.evaluate('document.activeElement.id')=='ift-source-details-open')
    open_panel(page);page.mouse.click(2,2);closed(page)
    check(key+'/light-dismiss',not page.locator('#ift-source-panel').evaluate("el=>el.matches(':popover-open')"))
    check(key+'/filter-retained-after-close',page.locator('#ift-search').input_value()==names[0])
    check(key+'/no-script-errors',not errors,errors=errors)
    context.close()

def adverse(browser,url,name):
    context=existing.source_context(browser,'light','en',390)
    state={name:True};names=fixture(context,state)
    page=context.new_page();page.goto(url,wait_until='domcontentloaded');existing.await_board(page)
    kind='limited' if name=='partial' else 'unavailable'
    page.wait_for_function("kind=>document.querySelector('[data-source-lane=quotes] .is-'+kind)!==null",arg=kind)
    open_panel(page)
    check('fixture/'+name+'/truthful-price-state',page.locator('[data-source-lane=quotes] .is-'+kind).count()==1)
    check('fixture/'+name+'/separate-options-state',page.locator('[data-source-lane=options] .is-unavailable').count()==1)
    page.keyboard.press('Escape');closed(page)
    if name=='partial':
        page.locator('#ift-search').fill(names[0])
        check('fixture/partial/zero-price-retained','$0.00' in page.locator('tr.lead-row:visible .price-cell').inner_text())
    context.close()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    before=hashlib.sha256((ROOT/'site/intraday_flow.html').read_bytes()).hexdigest()
    handler=functools.partial(QuietHandler,directory=str(ROOT/'site'))
    server=ThreadingHTTPServer(('127.0.0.1',0),handler);threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch();url=f'http://127.0.0.1:{server.server_port}/intraday_flow.html'
            for width in (1440,390):
                for theme in ('light','dark'):
                    for locale in ('en','zh'):matrix(browser,url,width,theme,locale)
            for name in ('partial','missing'):adverse(browser,url,name)
            browser.close()
    finally:server.shutdown();server.server_close()
    assert hashlib.sha256((ROOT/'site/intraday_flow.html').read_bytes()).hexdigest()==before
    images=[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'explicit_test_fixture':True} for p in sorted(OUT.glob('fixture-*.png'))]
    report={'evidence_kind':'isolated_source_details_browser_test','html_sha256':before,'fixtures':'explicit synthetic transport observations; no feed writes or live-market proof','checks':checks,'images':images}
    (OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'checks':len(checks),'passed':sum(x['passed'] for x in checks),'images':len(images),'html_sha256':before}))
if __name__=='__main__':main()
