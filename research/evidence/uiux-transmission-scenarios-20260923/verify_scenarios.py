"""Native scenario disclosure proof; no page or network response interception."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import argparse,json,hashlib,threading
from playwright.sync_api import sync_playwright
ap=argparse.ArgumentParser();ap.add_argument('--site-dir',type=Path);ap.add_argument('--base-url');ap.add_argument('--output-dir',required=True,type=Path);a=ap.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args): pass
srv=None;result=[]
if a.base_url:base=a.base_url.rstrip('/')
else:
 assert a.site_dir
 srv=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(a.site_dir)));threading.Thread(target=srv.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{srv.server_port}'
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  for device,width in [('desktop',1440),('mobile',390),('narrow',320)]:
   for lang in ['en','zh']:
    for theme in ['dark','light']:
     name=f'{device}-{lang}-{theme}';touch=device!='desktop';errors=[];failed=[]
     p=browser.new_page(viewport={'width':width,'height':900},has_touch=touch,is_mobile=touch,reduced_motion='reduce')
     p.on('pageerror',lambda e,errors=errors:errors.append(str(e)))
     p.on('response',lambda r,failed=failed:failed.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
     p.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('lang','{lang}');localStorage.removeItem('themeAuto');")
     response=p.goto(base+'/transmission.html',wait_until='domcontentloaded',timeout=30000);p.wait_for_timeout(1000);assert response and response.status==200
     cards=p.locator('.sx-card');details=p.locator('.sx-extra');assert cards.count()==4 and details.count()>0
     values=p.locator('.sx-item .v').all_text_contents();assets=p.locator('.sx-item').evaluate_all('es=>es.map(e=>e.dataset.asset)')
     top=p.locator('.sx-col > .sx-item');assert top.count()==28;assert p.locator('.sx-item').count()==32
     for i in range(details.count()):
      d=details.nth(i);s=d.locator('summary');hidden=d.locator('.sx-item');assert d.get_attribute('open') is None and not hidden.first.is_visible();assert s.bounding_box()['height']>=40
      s.scroll_into_view_if_needed()
      if touch:s.tap()
      else:s.focus();p.keyboard.press('Enter')
      assert d.get_attribute('open') is not None and hidden.first.is_visible()
      if touch: assert s.evaluate('e=>document.elementFromPoint(e.getBoundingClientRect().x+e.getBoundingClientRect().width/2,e.getBoundingClientRect().y+e.getBoundingClientRect().height/2)===e || e.contains(document.elementFromPoint(e.getBoundingClientRect().x+e.getBoundingClientRect().width/2,e.getBoundingClientRect().y+e.getBoundingClientRect().height/2))')
     allnames=p.locator('.sx-item .nm').all_inner_texts()
     assert ('比特币' in allnames) if lang=='zh' else ('Bitcoin' in allnames)
     assert any('材料' in n for n in allnames) if lang=='zh' else any('Materials' in n for n in allnames)
     first=details.first;summary=first.locator('summary');summary.scroll_into_view_if_needed();p.wait_for_timeout(600);p.screenshot(path=str(a.output_dir/(name+'-open.png')))
     # Shared Settings changes language without a page-owned event hook or state reset.
     p.locator('.nav-settings-btn').click();p.locator('.settings-pop .lang-toggle').focus();p.keyboard.press('Enter');other='zh' if lang=='en' else 'en';assert p.locator('html').get_attribute('data-lang')==other;p.keyboard.press('Escape')
     assert all(details.nth(i).get_attribute('open') is not None for i in range(details.count()))
     assert p.locator('.sx-item .v').all_text_contents()==values
     assert p.locator('.sx-item').evaluate_all('es=>es.map(e=>e.dataset.asset)')==assets
     newnames=p.locator('.sx-item .nm').all_inner_texts();assert ('比特币' in newnames) if other=='zh' else ('Bitcoin' in newnames)
     summary.focus();p.keyboard.press('Tab');p.keyboard.press('Shift+Tab');focus_style=summary.evaluate('e=>({active:document.activeElement===e,style:getComputedStyle(e).outlineStyle,width:parseFloat(getComputedStyle(e).outlineWidth)})');assert focus_style['active'] and focus_style['style']=='solid' and focus_style['width']>=2,(name,focus_style)
     summary.focus();p.keyboard.press('Space');assert first.get_attribute('open') is None;assert summary.evaluate('e=>document.activeElement===e')
     p.keyboard.press('Enter');assert first.get_attribute('open') is not None
     # Individual rows, names and numbers, not only page overflow.
     clips=p.locator('.sx-item').evaluate_all('es=>es.map(e=>({asset:e.dataset.asset,w:e.clientWidth,s:e.scrollWidth,parts:[...e.querySelectorAll(".nm,.v")].map(x=>({t:x.innerText,w:x.clientWidth,s:x.scrollWidth,right:x.getBoundingClientRect().right,max:e.getBoundingClientRect().right}))}))')
     assert all(c['s']<=c['w']+1 and all(x['s']<=x['w']+1 and x['right']<=x['max']+1 for x in c['parts']) for c in clips),(name,clips)
     overflow=p.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth');assert overflow<=1,(name,overflow)
     assert not errors,(name,errors)
     row={'cell':name,'http':200,'page_sha256':hashlib.sha256(response.body()).hexdigest(),'initial_visible_rows':28,'all_rows':32,'disclosures':details.count(),'native_enter_space':True,'actual_focus_outline':focus_style,'native_touch':touch,'minimum_target_height':40,'locale_and_state_preserved':True,'values_order_and_scale_unchanged':True,'individual_rows_unclipped':True,'overflow':overflow,'errors':errors,'failed_responses':failed,'passed':True};result.append(row);print(json.dumps(row,ensure_ascii=False),flush=True);p.close()
  browser.close()
finally:
 if srv:srv.shutdown();srv.server_close()
 (a.output_dir/'results.json').write_text(json.dumps({'mode':'public anonymous, no interception' if a.base_url else 'immutable current public-page fixture, no response interception','cases':result},ensure_ascii=False,indent=2)+'\n')
