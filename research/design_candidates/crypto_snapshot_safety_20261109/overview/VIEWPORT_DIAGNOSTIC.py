from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from datetime import datetime
from urllib.parse import urlsplit
import json,threading,time
from playwright.sync_api import sync_playwright
r=Path(__file__).resolve().parent
out=r/'overview-labels-viewport-proof-v2';assert not out.exists();out.mkdir();(out/'captures').mkdir()
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(r/'site')))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
origin=f'http://127.0.0.1:{server.server_address[1]}'
obs={'contexts':0,'pages':0,'page_errors':[],'blocked_external_requests':0,'blocked_websockets':0}
records=[];started=time.monotonic()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
  obs['browser']=browser.version
  for width in (320,1440):
   context=browser.new_context(viewport={'width':width,'height':844})
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
   page.add_init_script("localStorage.setItem('lang','en');localStorage.setItem('theme','dark')")
   page.goto(origin+'/crypto-r4.html?lang=en#overview',wait_until='load')
   page.wait_for_function("document.getElementById('crypto-intelligence').dataset.renderedAddress===location.href")
   page.evaluate("()=>document.fonts.ready")
   page.evaluate("()=>{window.scrollTo(0,document.documentElement.scrollHeight);return new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))}")
   record=page.evaluate("""()=>{
    const rect=n=>{const b=n.getBoundingClientRect();return {left:b.left,right:b.right,top:b.top,bottom:b.bottom,width:b.width,height:b.height}};
    const identity=n=>({tag:n.tagName,id:n.id,classes:n.className?.baseVal??n.className,text:(n.innerText||'').slice(0,120)});
    const fixed=[...document.querySelectorAll('body *')].filter(n=>getComputedStyle(n).position==='fixed'&&getComputedStyle(n).visibility!=='hidden'&&n.getBoundingClientRect().width>0&&n.getBoundingClientRect().height>0).map(n=>({...identity(n),rect:rect(n),pointerEvents:getComputedStyle(n).pointerEvents,zIndex:getComputedStyle(n).zIndex}));
    const nodes=[document.querySelector('[data-view="overview"] [data-open="asset:SOL"]'),document.querySelector('.cri-footer button')];
    return {width:innerWidth,height:innerHeight,scrollY,maxScroll:document.documentElement.scrollHeight-innerHeight,documentHeight:document.documentElement.scrollHeight,fixed,
     targets:nodes.map(n=>{const b=rect(n),pts=[[b.left+b.width/2,b.top+b.height/2],[b.left+4,b.top+4],[b.right-4,b.top+4],[b.left+4,b.bottom-4],[b.right-4,b.bottom-4]];
      return {...identity(n),rect:b,points:pts.map(([x,y])=>{const hit=document.elementFromPoint(x,y);return{x,y,clear:!!hit&&(hit===n||n.contains(hit)),hit:hit?identity(hit):null}})};
     })};
   }""")
   record['at_document_end']=abs(record['scrollY']-record['maxScroll'])<=1
   record['targets_clear']=all(t['rect']['top']>=0 and t['rect']['bottom']<=844 and all(point['clear'] for point in t['points']) for t in record['targets'])
   page.screenshot(path=str(out/'captures'/f'viewport-bottom-en-{width}.png'),full_page=False)
   if record['at_document_end'] and record['targets_clear']:
    for selector,panel in (('[data-view="overview"] [data-open="asset:SOL"]','asset:SOL'),('.cri-footer button','model')):
     opener=page.locator(selector);opener.click()
     page.wait_for_function("(panel)=>document.getElementById('cri-dialog').open&&document.getElementById('cri-dialog-body').dataset.panel===panel",arg=panel)
     page.locator('#cri-dialog-close').click()
     page.wait_for_function("location.hash==='#overview'&&!document.getElementById('cri-dialog').open")
     assert opener.evaluate('n=>document.activeElement===n')
    record['actions_and_focus']=True
   else:
    record['actions_and_focus']='not attempted: clearance observation first'
   records.append(record);context.close()
  browser.close()
finally:
 server.shutdown();server.server_close();thread.join(timeout=5)
obs['seconds']=round(time.monotonic()-started,3)
assert not obs['page_errors'] and obs['blocked_external_requests']==obs['blocked_websockets']==0
(out/'result.json').write_text(json.dumps({'observations':obs,'cases':records},indent=2)+'\n')
print(json.dumps({'observations':obs,'cases':[{'width':r['width'],'targets':[{**t,'points':len(t['points'])} for t in r['targets']],'fixed':r['fixed']} for r in records]}))
