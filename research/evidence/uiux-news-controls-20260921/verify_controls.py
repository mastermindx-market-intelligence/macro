"""Native News controls. Local runs use explicit anonymous 401 fixtures for gated feeds."""
from __future__ import annotations
import argparse, hashlib, json, threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]
ap=argparse.ArgumentParser(); ap.add_argument('--base-url'); ap.add_argument('--output-dir'); args=ap.parse_args()
out=Path(args.output_dir) if args.output_dir else HERE/'browser'; out.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*_): pass
server=None
if args.base_url: base=args.base_url.rstrip('/')
else:
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT/'site')))
    threading.Thread(target=server.serve_forever,daemon=True).start(); base=f'http://127.0.0.1:{server.server_port}'
results=[]
def assert_count(page,lang):
    total=page.locator('#nxFeed .nx-story').count()
    shown=page.locator('#nxFeed .nx-story:visible').count()
    lane=page.locator('#nxSeg [aria-pressed="true"]').get_attribute('data-lane')
    q=page.locator('#nxSearch').input_value().strip().lower()
    matches=page.locator('#nxFeed .nx-story').evaluate_all('(els,p)=>els.filter(e=>(p.lane==="all"||e.dataset.lane===p.lane)&&(!p.q||e.dataset.search.includes(p.q))).length',{'lane':lane,'q':q})
    expected=(f'显示 {shown} / {matches} 条' if shown<matches else f'{matches} 条') if lang=='zh' else (f'{shown} of {matches} headlines' if shown<matches else f'{matches} headline'+('' if matches==1 else 's'))
    assert page.locator('#nxCount').inner_text()==expected,(expected,page.locator('#nxCount').inner_text())
    return {'total':total,'matched':matches,'shown':shown}
def activate(locator,touch):
    if touch: locator.tap()
    else: locator.click()
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        for device,w,h in [('desktop',1440,900),('mobile',390,844)]:
            for lang in ['en','zh']:
                for theme in ['dark','light']:
                    label=f'{device}-{lang}-{theme}'; touch=device=='mobile'
                    p=browser.new_page(viewport={'width':w,'height':h},is_mobile=touch,has_touch=touch,reduced_motion='reduce')
                    errors=[]; p.on('pageerror',lambda e,errors=errors:errors.append(str(e)))
                    p.add_init_script(f"localStorage.setItem('lang','{lang}');localStorage.setItem('theme','{theme}');localStorage.removeItem('themeAuto');")
                    if not args.base_url:
                        for pattern in ['**/live/intelligence.json','**/live/wires.json']:
                            p.route(pattern,lambda route:route.fulfill(status=401,content_type='application/json',body='{}'))
                    response=p.goto(base+'/news.html',wait_until='domcontentloaded',timeout=30000); assert response.status==200
                    p.locator('#nxIntelState strong').wait_for(); p.locator('#nxWireState').wait_for()
                    p.wait_for_function("document.querySelector('#nxWireState')?.innerText.includes('Sign in')||document.querySelector('#nxWireState')?.innerText.includes('登录')")
                    assert not p.locator('#nxIntel .nxi-health').is_visible()
                    assert not p.locator('#nxIntelMetrics').is_visible()
                    assert not p.locator('#nxIntelToolbar').is_visible()
                    assert not p.locator('#nxIntelFooter').is_visible()
                    assert not p.locator('#nxWireList').is_visible()
                    initial=assert_count(p,lang); assert initial['shown']==min(24,initial['total'])
                    assert p.locator('#nxSeg').get_attribute('role')=='group'
                    assert p.locator('#nxCount').get_attribute('role')=='status'
                    assert p.locator('#nxSeg [aria-pressed="true"]').count()==1
                    heights=p.locator('#nxSeg button').evaluate_all('els=>els.map(e=>e.getBoundingClientRect().height)'); assert min(heights)>=40
                    tops=p.locator('#nxSeg button').evaluate_all('els=>els.map(e=>e.getBoundingClientRect().top)'); assert max(tops)-min(tops)<=1
                    search=p.locator('#nxSearch'); search.click(); p.keyboard.press('Shift+Tab')
                    assert p.evaluate("document.activeElement?.dataset.lane==='companies'")
                    p.keyboard.press('Enter'); assert p.locator('#nxSeg [data-lane="companies"]').get_attribute('aria-pressed')=='true'
                    a=assert_count(p,lang); p.keyboard.press('Space'); assert assert_count(p,lang)==a
                    activate(p.locator('#nxSeg [data-lane="all"]'),touch)
                    chinese=p.locator('#nxFeed .nx-story-title .l-zh').first.text_content().strip()
                    query=chinese[:12]; search.fill(query); assert assert_count(p,lang)['matched']>=1
                    before_titles=p.locator('#nxFeed .nx-story:visible .nx-story-title .l-en').all_text_contents()
                    activate(p.locator('.nav-settings-btn'),touch)
                    activate(p.locator('.settings-pop .lang-toggle'),touch)
                    other='zh' if lang=='en' else 'en'
                    assert p.locator('html').get_attribute('data-lang')==other
                    assert search.input_value()==query and p.locator('#nxSeg [data-lane="all"]').get_attribute('aria-pressed')=='true'
                    assert_count(p,other)
                    assert search.get_attribute('placeholder')==('搜索标题、代码…' if other=='zh' else 'Search headlines, tickers…')
                    assert search.get_attribute('aria-label')==('搜索新闻' if other=='zh' else 'Search news')
                    assert p.locator('#nxFeed .nx-story:visible .nx-story-title .l-en').all_text_contents()==before_titles
                    for selector in ['#nxIntelState','#nxWireState']:
                        text=p.locator(selector).inner_text(); assert ('登录' in text) if other=='zh' else ('Sign in' in text)
                    stamp=p.locator('.rel-time').first.inner_text(); assert ('前' in stamp) if other=='zh' else ('ago' in stamp or 'just now' in stamp)
                    p.keyboard.press('Escape')
                    search.fill('__no_headline_matches_uiux__'); assert assert_count(p,other)['matched']==0
                    reset=p.locator('#nxReset'); assert reset.is_visible(); activate(reset,touch)
                    assert search.input_value()=='' and p.evaluate("document.activeElement?.id==='nxSearch'")
                    reset_state=assert_count(p,other); assert reset_state['shown']==min(24,reset_state['total'])
                    more=p.locator('#nxMore')
                    if initial['total']>24:
                        activate(more,touch); expanded=assert_count(p,other); assert expanded['shown']==expanded['total'] and not more.is_visible()
                    for lane in ['markets','macro','fed','companies','all']:
                        activate(p.locator('#nxSeg [data-lane="'+lane+'"]'),touch)
                        assert p.locator('#nxSeg [aria-pressed="true"]').count()==1
                        assert p.locator('#nxSeg [data-lane="'+lane+'"]').get_attribute('aria-pressed')=='true'; assert_count(p,other)
                    overflow=p.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth'); assert overflow<=1
                    assert not errors,errors
                    p.locator('.nx-controls').scroll_into_view_if_needed(); p.wait_for_timeout(200); p.screenshot(path=str(out/(label+'.png')))
                    row={'cell':label,'http':response.status,'html_sha256':hashlib.sha256(response.body()).hexdigest(),'initial':initial,'native_keyboard':True,'native_touch':touch,'native_locale_change':True,'translated_search_matches':True,'query_order_preserved':True,'guest_state_translated':True,'clear_restores_focus':True,'gated_grid_and_flex_hidden':True,'topic_buttons_one_row':True,'filter_min_height':min(heights),'overflow':overflow,'page_errors':errors,'passed':True}
                    results.append(row); print(json.dumps(row),flush=True); p.close()
        browser.close()
finally:
    if server: server.shutdown(); server.server_close()
    (out/'results.json').write_text(json.dumps({'mode':'public, no interception' if args.base_url else 'local source with explicitly simulated anonymous 401 responses for the two gated feeds','cells':results},indent=2)+'\n')
