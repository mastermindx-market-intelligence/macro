"""Bounded native footer-clearance proof; preserves shared launcher and real input/layout."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from datetime import datetime
import json,sys,threading,time
from playwright.sync_api import sync_playwright
r=Path(__file__).resolve().parent;stage=sys.argv[1];assert stage in ('parent','candidate')
out=r/('footer-clearance-'+stage+'-proof');assert not out.exists();out.mkdir();(out/'captures').mkdir()
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(r/'site')))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
origin=f'http://127.0.0.1:{server.server_address[1]}'
obs={'stage':stage,'contexts':0,'pages':0,'page_errors':[],'blocked_external_requests':0,'blocked_websockets':0}
records=[];started=time.monotonic()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
  obs['browser']=browser.version
  for width,lang in ((320,'en'),(320,'zh'),(1440,'en'),(1440,'zh')):
   context=browser.new_context(viewport={'width':width,'height':844},is_mobile=width==320 and lang=='zh',has_touch=width==320 and lang=='zh')
   obs['contexts']+=1
   def request(route):
    if route.request.url.startswith(origin+'/'):route.continue_()
    else:obs['blocked_external_requests']+=1;route.abort()
   def socket(route):
    obs['blocked_websockets']+=1;route.close()
   context.route('**/*',request);context.route_web_socket('**/*',socket)
   page=context.new_page();obs['pages']+=1
   page.on('pageerror',lambda e:obs['page_errors'].append(str(e)));page.set_default_timeout(4500)
   page.clock.set_fixed_time(datetime.fromisoformat('2026-10-18T12:00:00+00:00'))
   page.add_init_script("localStorage.setItem('lang',"+json.dumps(lang)+");localStorage.setItem('theme',"+json.dumps('dark' if lang=='en' else 'light')+")")
   page.goto(origin+'/crypto-r4.html?lang='+lang+'#overview',wait_until='load')
   for view in ('overview','bitcoin','markets','scenarios'):
    if view!='overview':page.locator('nav.cri-tabs [data-route="'+view+'"]').click()
    page.wait_for_function("document.getElementById('crypto-intelligence').dataset.renderedAddress===location.href")
    page.evaluate("()=>document.fonts.ready");page.mouse.move(0,0)
    page.wait_for_function("()=>{const n=document.getElementById('mmb-boot');return n&&getComputedStyle(n).visibility==='visible'&&getComputedStyle(n).transform==='none'}")
    footer=page.locator('.cri-footer button')
    footer.focus();page.keyboard.press('Shift+Tab');page.keyboard.press('Tab')
    assert footer.evaluate('n=>document.activeElement===n')
    page.evaluate("()=>{window.scrollTo(0,document.documentElement.scrollHeight);return new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))}")
    record=page.evaluate("""(view)=>{
     const rect=n=>{const b=n.getBoundingClientRect();return {left:b.left,right:b.right,top:b.top,bottom:b.bottom,width:b.width,height:b.height}};
     const n=document.querySelector('.cri-footer button'),b=rect(n),launcher=document.getElementById('mmb-boot'),l=rect(launcher),style=getComputedStyle(n);
     const pts=[[b.left+b.width/2,b.top+b.height/2],[b.left+4,b.top+4],[b.right-4,b.top+4],[b.left+4,b.bottom-4],[b.right-4,b.bottom-4]];
     const hits=pts.map(([x,y])=>{const hit=document.elementFromPoint(x,y);return{x,y,clear:!!hit&&(hit===n||n.contains(hit)),hitTag:hit?.tagName,hitId:hit?.id}});
     const horizontalOverlap=b.right>l.left&&b.left<l.right;
     const focusExtent=parseFloat(style.outlineWidth)+parseFloat(style.outlineOffset);
     return {view,width:innerWidth,height:innerHeight,scrollY,maxScroll:document.documentElement.scrollHeight-innerHeight,pageWidth:document.documentElement.scrollWidth,footer:b,launcher:l,
      launcherStyle:{position:getComputedStyle(launcher).position,bottom:getComputedStyle(launcher).bottom,right:getComputedStyle(launcher).right,pointerEvents:getComputedStyle(launcher).pointerEvents,zIndex:getComputedStyle(launcher).zIndex},
      text:n.innerText,fontSize:style.fontSize,fontFamily:style.fontFamily,focusVisible:n.matches(':focus-visible'),focusExtent,
      verticalGap:l.top-b.bottom,focusGap:l.top-b.bottom-focusExtent,horizontalOverlap,hits,
      bodyView:rect(document.querySelector('[data-view="'+view+'"]')),footerContainer:rect(document.querySelector('.cri-footer')),
      paddingBottom:getComputedStyle(document.getElementById('crypto-intelligence')).paddingBottom,
      safeAreaFormulaSupported:CSS.supports('padding-bottom','calc(96px + env(safe-area-inset-bottom,0px))'),
      version:document.querySelector('link[href^="crypto_intelligence_r4.css"]').href.split('?v=')[1],
      summary:[...document.querySelectorAll('.cri-watch-meta')].map(x=>({text:x.innerText,fontSize:getComputedStyle(x).fontSize,fontFamily:getComputedStyle(x).fontFamily}))};
    }""",view)
    record.update(lang=lang)
    record['at_end']=abs(record['scrollY']-record['maxScroll'])<=1
    record['clear']=all(x['clear'] for x in record['hits']) and (not record['horizontalOverlap'] or record['focusGap']>=8)
    if view=='overview':page.screenshot(path=str(out/'captures'/f'overview-bottom-{lang}-{width}.png'),full_page=False)
    if record['clear']:
     footer.click();page.wait_for_function("document.getElementById('cri-dialog').open&&document.getElementById('cri-dialog-body').dataset.panel==='model'")
     page.locator('#cri-dialog-close').click()
     page.wait_for_function("(view)=>location.hash==='#'+view&&!document.getElementById('cri-dialog').open",arg=view)
     assert footer.evaluate('n=>document.activeElement===n')
     record['model_close_focus']=True
    else:record['model_close_focus']='not attempted: clearance failed'
    records.append(record)
   assert page.evaluate("localStorage.getItem('mmx.crypto.r4.scenarios.v1')") is None
   context.close()
  browser.close()
finally:
 server.shutdown();server.server_close();thread.join(timeout=5)
obs['seconds']=round(time.monotonic()-started,3)
report={'observations':obs,'cases':records}
(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'observations':obs,'cases':[{'view':x['view'],'width':x['width'],'lang':x['lang'],'clear':x['clear'],'gap':x['verticalGap'],'focusGap':x['focusGap'],'actions':x['model_close_focus']} for x in records]}))
assert not obs['page_errors'] and obs['blocked_external_requests']==obs['blocked_websockets']==0
assert all(x['at_end'] and x['pageWidth']<=x['width'] and x['focusVisible'] for x in records)
if stage=='candidate':assert all(x['clear'] and x['model_close_focus'] is True and x['paddingBottom']=='96px' for x in records)
