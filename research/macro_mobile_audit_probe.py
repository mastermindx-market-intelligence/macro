"""Read-only live mobile audit; isolated browser, no account or server mutations."""
import json, hashlib, time
from pathlib import Path
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parent / 'macro_mobile_audit_20260920'
ROOT.mkdir(exist_ok=True)
ORIGIN = 'https://www.mastermind-x.com'
ROUTES = ['macro.html','start.html','us_stocks.html','sector_central.html','alerts.html','options.html','china.html','hk.html','canada.html','news.html']
JS = r'''() => {
 const vis=e=>e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}) && e.getBoundingClientRect().width>0;
 const rect=e=>{let r=e.getBoundingClientRect();return {x:Math.round(r.x),y:Math.round(r.y+scrollY),w:Math.round(r.width),h:Math.round(r.height)}};
 const tag=e=>e.tagName.toLowerCase()+(e.id?'#'+e.id:'')+'.'+String(e.className).split(' ').slice(0,3).join('.');
 const txt=e=>(e.innerText||e.getAttribute('aria-label')||e.title||'').trim().replace(/\s+/g,' ').slice(0,110);
 const els=[...document.querySelectorAll('body *')].filter(vis);
 const controls=els.filter(e=>e.matches('button,a,input,select,summary,[role=button],[tabindex="0"]'));
 const overflow=els.filter(e=>{let r=e.getBoundingClientRect();if(r.right<=innerWidth+2&&r.left>=-2)return false;for(let a=e.parentElement;a&&a!==document.body;a=a.parentElement){let s=getComputedStyle(a);if(['auto','scroll','hidden','clip'].includes(s.overflowX))return false;}return true;});
 return {viewport:{w:innerWidth,h:innerHeight,scrollW:document.documentElement.scrollWidth,scrollH:document.documentElement.scrollHeight},attrs:[...document.documentElement.attributes].map(a=>[a.name,a.value]),headings:els.filter(e=>e.matches('h1,h2,h3')).map(e=>({tag:tag(e),text:txt(e),r:rect(e)})),overflow:overflow.slice(0,35).map(e=>({tag:tag(e),text:txt(e),r:rect(e)})),smallControls:controls.filter(e=>{let r=e.getBoundingClientRect();return r.width<40||r.height<40;}).slice(0,65).map(e=>({tag:tag(e),text:txt(e),r:rect(e)})),buttons:controls.filter(e=>e.matches('button,summary,[role=button]')).slice(0,65).map(e=>({tag:tag(e),text:txt(e),r:rect(e)})),links:[...new Set([...document.querySelectorAll('a[href]')].map(e=>e.getAttribute('href')).filter(h=>h&&!h.startsWith('#')))],assets:[...document.querySelectorAll('script[src],link[rel=stylesheet]')].map(e=>e.getAttribute('src')||e.getAttribute('href'))};
}'''
results=[]
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True)
 for route in ROUTES:
  context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=1)
  page=context.new_page(); errors=[]; failed=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('response',lambda r:failed.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
  stamp=datetime.now(timezone.utc).isoformat(); folder=ROOT/route.removesuffix('.html');folder.mkdir(exist_ok=True)
  try:
   response=page.goto(ORIGIN+'/'+route,wait_until='domcontentloaded',timeout=45000)
   page.wait_for_timeout(3000)
   result=page.evaluate(JS)
   result.update(route=route,url=page.url,status=response.status,title=page.title(),time=stamp,browser=browser.version,errors=errors,failed=failed)
   body=response.body();result['html_sha256']=hashlib.sha256(body).hexdigest()
   (folder/'response.html').write_bytes(body)
   (folder/'body.txt').write_text(page.locator('body').inner_text())
   page.screenshot(path=str(folder/'390-top.png'),animations='disabled')
   page.screenshot(path=str(folder/'390-full.jpg'),full_page=True,type='jpeg',quality=75,animations='disabled')
   (folder/'audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
   print(json.dumps({'route':route,'status':result['status'],'title':result['title'],'viewport':result['viewport'],'overflow':result['overflow'][:5],'small_count':len(result['smallControls']),'errors':errors[:4],'failed':failed[:6]},ensure_ascii=False),flush=True)
   results.append(result)
  except Exception as e:
   result={'route':route,'error':str(e),'time':stamp};results.append(result);print(json.dumps(result),flush=True)
  finally:
   context.close()
  (ROOT/'inventory.json').write_text(json.dumps(results,indent=2,ensure_ascii=False))
 browser.close()
print('AUDIT_ROOT='+str(ROOT),flush=True)
