"""Exercise native chart controls; no private data, render API calls, or model changes."""
from __future__ import annotations
import argparse,hashlib,json,threading
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
parser=argparse.ArgumentParser();parser.add_argument('--base-url');parser.add_argument('--site-dir');parser.add_argument('--output-dir');args=parser.parse_args()
OUT=Path(args.output_dir) if args.output_dir else HERE/'browser';OUT.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*_args):pass
server=None
if args.base_url:base=args.base_url.rstrip('/')
else:
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(Path(args.site_dir) if args.site_dir else ROOT/'site')))
    threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
BASELINE=None if args.base_url else json.loads((HERE/'baseline-geometry.json').read_text())
CHARTS={'gex':['gex-chart','spx-flip-chart'],'sys':['sys-chart'],'cor':['cor-chart']}
HISTORY={'gex':'MSP_GAMMA_HIST','sys':'MSP_SYS_HIST','cor':'MSP_COR_HIST'}
DEFAULT={'gex':126,'sys':252,'cor':252};rows=[]
seed=r"""
  if(!sessionStorage.getItem('__mspSeeded')){
    localStorage.setItem('msp-gex-range','broken');localStorage.setItem('msp-sys-range','126');localStorage.setItem('msp-cor-range','63days');
    sessionStorage.setItem('__mspSeeded','true');
  }
  window.__mspWrites=0;const originalSet=Storage.prototype.setItem;
  Storage.prototype.setItem=function(k,v){if(String(k).startsWith('msp-'))window.__mspWrites++;return originalSet.call(this,k,v);};
"""
def geometry(p,group):
    return {chart:hashlib.sha256(p.locator('#'+chart).inner_html().encode()).hexdigest() for chart in CHARTS[group]}
def assert_group(p,group,n,lang):
    wrapper=p.locator('#'+group+'-range-btns')
    assert wrapper.get_attribute('role')=='group'
    assert wrapper.locator('[aria-pressed="true"]').count()==1
    selected=wrapper.locator('[aria-pressed="true"]');assert selected.get_attribute('data-range')==str(n)
    assert selected.get_attribute('aria-controls')==' '.join(CHARTS[group])
    assert selected.get_attribute('type')=='button'
    assert 'on' in selected.get_attribute('class').split()
    history=p.evaluate(HISTORY[group]);cut=history if n>=9000 else history[-n:]
    status=p.locator('#'+group+'-range-status');text=status.inner_text()
    assert str(len(cut)) in text and cut[0]['date'] in text and cut[-1]['date'] in text,(group,n,text)
    assert ('个观测' in text) if lang=='zh' else ('observation' in text)
    for chart in CHARTS[group]:
        svg=p.locator('#'+chart)
        assert svg.get_attribute('role')=='img'
        assert svg.get_attribute('aria-label')==svg.get_attribute('data-chart-label-'+lang)
        assert svg.get_attribute('aria-describedby')==group+'-range-status'
    if BASELINE:assert geometry(p,group)==BASELINE[group+':'+str(n)],(group,n,'numeric geometry changed')
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        for device,width,height in [('desktop',1440,900),('mobile',390,844)]:
            for lang in ['en','zh']:
                for theme in ['dark','light']:
                    label=f'{device}-{lang}-{theme}'
                    p=browser.new_page(viewport={'width':width,'height':height},is_mobile=device=='mobile',has_touch=device=='mobile',reduced_motion='reduce')
                    errors=[];p.on('pageerror',lambda e,errs=errors:errs.append(str(e)))
                    p.add_init_script(f"localStorage.setItem('lang','{lang}');localStorage.setItem('theme','{theme}');localStorage.removeItem('themeAuto');"+seed)
                    response=p.goto(base+'/market_structure.html',wait_until='domcontentloaded',timeout=30000)
                    assert response and response.status==200;response_hash=hashlib.sha256(response.body()).hexdigest();p.wait_for_timeout(200)
                    assert p.evaluate('window.__mspWrites')==0,'initial fallback should not write preferences'
                    for group,n in DEFAULT.items():assert_group(p,group,n,lang)
                    heights=p.locator('.range-btns button').evaluate_all('els=>els.map(b=>({h:b.getBoundingClientRect().height,w:b.getBoundingClientRect().width}))')
                    assert all(x['w']>=44 and x['h']>=(40 if device=='mobile' else 32) for x in heights),heights
                    first=p.locator('#gex-range-btns button').first;first.focus();p.keyboard.press('Tab')
                    second=p.locator('#gex-range-btns button').nth(1);assert second.evaluate('e=>e===document.activeElement')
                    for key in ['Enter','Space']:
                        before=p.evaluate('window.__mspWrites');p.keyboard.press(key)
                        assert p.evaluate('window.__mspWrites')==before+1
                        assert second.evaluate('e=>e===document.activeElement');assert_group(p,'gex',63,lang)
                    count=0
                    for group in CHARTS:
                        choices=p.locator('#'+group+'-range-btns button').evaluate_all('els=>els.map(b=>b.dataset.range)')
                        for value in choices:
                            before_other={g:geometry(p,g) for g in CHARTS if g!=group}
                            button=p.locator('#'+group+'-range-btns button[data-range="'+value+'"]')
                            before=p.evaluate('window.__mspWrites')
                            if device=='mobile':button.tap()
                            else:button.click()
                            assert p.evaluate('window.__mspWrites')==before+1
                            assert_group(p,group,int(value),lang)
                            assert {g:geometry(p,g) for g in before_other}==before_other
                            count+=1
                    wanted={'gex':21,'sys':9999,'cor':63}
                    for group,n in wanted.items():p.locator('#'+group+'-range-btns button[data-range="'+str(n)+'"]').click()
                    p.reload(wait_until='domcontentloaded');p.wait_for_timeout(100)
                    for group,n in wanted.items():assert_group(p,group,n,lang)
                    # Existing shared language-owner event contract. This deliberately
                    # tests the event seam, not the unrelated settings-menu gesture.
                    other='en' if lang=='zh' else 'zh';before={g:geometry(p,g) for g in CHARTS}
                    p.evaluate("lg=>{document.documentElement.setAttribute('data-lang',lg);document.dispatchEvent(new CustomEvent('langchange',{detail:lg}));}",other)
                    for group,n in wanted.items():assert_group(p,group,n,other)
                    assert {g:geometry(p,g) for g in CHARTS}==before
                    p.evaluate("lg=>{document.documentElement.setAttribute('data-lang',lg);document.dispatchEvent(new CustomEvent('langchange',{detail:lg}));}",lang)
                    p.locator('#gex-range-btns button[data-range="21"]').focus();p.wait_for_timeout(100)
                    dates=p.locator('#gex-range-status .l-'+lang+' .msp-range-dates')
                    assert dates.evaluate('e=>e.getBoundingClientRect().width<=e.parentElement.parentElement.clientWidth')
                    overflow=p.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth');assert overflow<=1
                    assert not errors,errors
                    p.screenshot(path=str(OUT/(label+'.png')))
                    row={'cell':label,'http':response.status,'choices_exercised':count,'keyboard_Enter_Space':True,'native_touch':device=='mobile','invalid_preferences_recovered':True,'independent_preferences_reloaded':True,'language_event_without_redraw':True,'geometry_matches_prior_source':BASELINE is not None,'min_height':min(x['h'] for x in heights),'page_errors':errors,'overflow':overflow,'html_sha256':response_hash,'passed':True}
                    rows.append(row);print(json.dumps(row),flush=True);p.close()
        # Storage denial is scoped to the controller's own keys, not an auth bypass.
        p=browser.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
        p.add_init_script("""
          const get=Storage.prototype.getItem,set=Storage.prototype.setItem;
          Storage.prototype.getItem=function(k){if(String(k).startsWith('msp-'))throw new Error('test: denied range storage');return get.call(this,k);};
          Storage.prototype.setItem=function(k,v){if(String(k).startsWith('msp-'))throw new Error('test: denied range storage');return set.call(this,k,v);};
        """)
        p.goto(base+'/market_structure.html',wait_until='domcontentloaded');p.wait_for_timeout(100)
        for group,n in DEFAULT.items():assert_group(p,group,n,'en')
        p.locator('#gex-range-btns button[data-range="21"]').click();assert_group(p,'gex',21,'en');assert not errors
        rows.append({'cell':'range-storage-denied','selected_after_click':21,'page_errors':errors,'passed':True});print(json.dumps(rows[-1]),flush=True);p.close();browser.close()
finally:
    if server:server.shutdown();server.server_close()
    (OUT/'results.json').write_text(json.dumps({'mode':'public production' if args.base_url else 'local current artifact','results':rows},indent=2)+'\n')
