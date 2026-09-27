"""Native Dark Pool desk controls; no response interception or backend writes."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import argparse, csv, io, json, hashlib, threading
from playwright.sync_api import sync_playwright
ap=argparse.ArgumentParser();ap.add_argument('--site-dir',type=Path);ap.add_argument('--base-url');ap.add_argument('--cell');ap.add_argument('--output-dir',required=True,type=Path);a=ap.parse_args();a.output_dir.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
srv=None;results=[]
if a.base_url:base=a.base_url.rstrip('/')
else:
 assert a.site_dir
 srv=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(a.site_dir)));threading.Thread(target=srv.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{srv.server_port}'

def tickers(p):
 return p.locator('#dp-tbody tr:not(.dp-empty) td:first-child').evaluate_all('es=>es.map(e=>e.childNodes[0].textContent)')
def click(p,loc,touch):
 loc.scroll_into_view_if_needed()
 if touch:loc.tap()
 else:loc.focus();p.keyboard.press('Enter')

def expected(rows,preset):
 if preset=='heavy-oe':return [r for r in rows if r.get('participation') is not None and r['participation']>=.45]
 if preset=='rising-oe':return [r for r in rows if r.get('participation_trend_pp') is not None and r['participation_trend_pp']>=1 and r.get('participation') is not None and r['participation']>=.02]
 if preset=='short-spike':return [r for r in rows if r.get('ratio_z') is not None and r['ratio_z']>=2]
 if preset=='fading-oe':return [r for r in rows if r.get('participation_trend_pp') is not None and r['participation_trend_pp']<=-1]
 raise AssertionError(preset)
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  for device,width in [('desktop',1440),('tablet',820),('mobile',390),('narrow',320)]:
   for lang in ['en','zh']:
    for theme in ['dark','light']:
     name=f'{device}-{lang}-{theme}';touch=device!='desktop';errors=[];failed=[]
     if a.cell and a.cell!=name:continue
     p=browser.new_page(viewport={'width':width,'height':900},has_touch=touch,is_mobile=touch,reduced_motion='reduce',accept_downloads=True)
     p.on('pageerror',lambda e,errors=errors:errors.append(str(e)))
     p.on('response',lambda r,failed=failed:failed.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
     p.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('lang','{lang}');localStorage.removeItem('themeAuto');")
     response=p.goto(base+'/darkpool.html',wait_until='load',timeout=30000);p.wait_for_timeout(500);assert response and response.status==200
     raw=p.locator('#dp-data').text_content();rows=json.loads(raw);total=len(rows);assert total>0
     directory=p.locator('#dp-table').locator('xpath=ancestor::details[1]');summary=directory.locator(':scope > summary');assert not directory.evaluate('e=>e.open');click(p,summary,touch);assert directory.evaluate('e=>e.open')
     assert len(tickers(p))==total
     presets=p.locator('.presets-row button.preset');assert presets.count()==4
     assert p.locator('#dp-table .dp-sort').count()==13
     assert p.locator('#dp-table th[aria-sort]').count()==1
     assert p.locator('#dp-table th[aria-sort]').get_attribute('data-col')=='participation_z'
     minheight=min(presets.evaluate_all('es=>es.map(e=>e.getBoundingClientRect().height)'));assert minheight>=40
     # Native Tab, Enter and Space expose the same four original filter predicates.
     presets.first.focus();p.keyboard.press('Tab');assert p.evaluate('document.activeElement.dataset.preset')=='rising-oe'
     p.keyboard.press('Space');assert p.locator('[data-preset="rising-oe"]').get_attribute('aria-pressed')=='true'
     assert set(tickers(p))=={r['ticker'] for r in expected(rows,'rising-oe')}
     p.keyboard.press('Space');assert p.evaluate('document.activeElement.dataset.preset')=='rising-oe';assert len(tickers(p))==total
     for preset in ['heavy-oe','rising-oe','short-spike','fading-oe']:
      button=p.locator(f'button[data-preset="{preset}"]');click(p,button,touch)
      assert button.get_attribute('aria-pressed')=='true'
      assert p.locator('.preset[aria-pressed="true"]').count()==1
      assert set(tickers(p))=={r['ticker'] for r in expected(rows,preset)},(name,preset)
      click(p,button,touch);assert button.get_attribute('aria-pressed')=='false';assert len(tickers(p))==total
      assert button.evaluate('e=>document.activeElement===e'),(name,'preset focus')
     # Header button activation runs once. First Ticker activation is descending, next ascending.
     ticker=p.locator('th[data-col="ticker"] .dp-sort');click(p,ticker,touch)
     assert p.locator('th[data-col="ticker"]').get_attribute('aria-sort')=='descending'
     assert tickers(p)==sorted([r['ticker'] for r in rows],reverse=True)
     ticker.focus();p.keyboard.press('Space');assert p.locator('th[data-col="ticker"]').get_attribute('aria-sort')=='ascending'
     assert tickers(p)==sorted([r['ticker'] for r in rows]);assert ticker.evaluate('e=>document.activeElement===e')
     # Adjacent optional help must not activate the sorting control.
     tip=p.locator('th[data-col="participation"] .tip-wrap');tip.click();p.keyboard.press('Escape')
     assert p.locator('th[aria-sort]').get_attribute('data-col')=='ticker'
     assert p.locator('th[aria-sort]').get_attribute('aria-sort')=='ascending'
     # All visible sort columns keep their original values and null-last ascending order.
     sortable=p.locator('#dp-table .dp-sort');checked=[]
     for i in range(sortable.count()):
      button=sortable.nth(i)
      if not button.is_visible():continue
      th=button.locator('xpath=..');col=th.get_attribute('data-col');button.focus();p.keyboard.press('Enter');order=th.get_attribute('aria-sort')
      current=tickers(p);assert len(current)==total and len(set(current))==total
      if col not in ('ticker','asof','top_ats_venue'):
       mapping={r['ticker']:r.get(col) for r in rows};vals=[mapping[t] for t in current];known=[v for v in vals if v is not None];assert known==sorted(known,reverse=order=='descending'),(name,col,order)
       assert all(v is None for v in vals[len(known):]),(name,col,'null-last')
      checked.append(col)
     # Keep the ticker visible at both ends of the real horizontally scrolled table.
     wrapper=p.locator('#dp-table').locator('xpath=..');first=p.locator('#dp-tbody tr:not(.dp-empty) td:first-child').first
     first.scroll_into_view_if_needed()
     for edge in ['start','end']:
      wrapper.evaluate("(e,edge)=>e.scrollTo({left:edge==='start'?0:e.scrollWidth,behavior:'instant'})",edge)
      pos=first.evaluate("e=>{const w=e.closest('.tbl-wrap').getBoundingClientRect(),r=e.getBoundingClientRect();const hit=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return {left:r.left,wrapLeft:w.left,right:r.right,wrapRight:w.right,sticky:getComputedStyle(e).position,topmost:hit===e||e.contains(hit)}}")
      assert pos['sticky']=='sticky' and abs(pos['left']-pos['wrapLeft'])<=2 and pos['right']<=pos['wrapRight']+1 and pos['topmost'],(name,edge,pos)
     wrapper.evaluate("e=>e.scrollTo({left:0,behavior:'instant'})")
     search=p.locator('#dp-search');search.fill('A')
     p.locator('#dp-min-share').fill('40');p.locator('#dp-trend').select_option('all');p.locator('#dp-norm').select_option('all')
     before={'tickers':tickers(p),'query':search.input_value(),'min':p.locator('#dp-min-share').input_value(),'sort':p.locator('th[aria-sort]').get_attribute('data-col'),'dir':p.locator('th[aria-sort]').get_attribute('aria-sort')}
     p.locator('.nav-settings-btn').click();p.locator('.settings-pop .lang-toggle').focus();p.keyboard.press('Enter');other='zh' if lang=='en' else 'en';assert p.locator('html').get_attribute('data-lang')==other;p.keyboard.press('Escape')
     assert tickers(p)==before['tickers'] and search.input_value()==before['query'] and p.locator('#dp-min-share').input_value()==before['min']
     assert p.locator('th[aria-sort]').get_attribute('data-col')==before['sort'] and p.locator('th[aria-sort]').get_attribute('aria-sort')==before['dir']
     for field in ['dp-search','dp-min-share','dp-trend','dp-norm']:
      assert p.locator(f'label[for="{field}"]').is_visible()
     assert p.locator('#dp-min-share').get_attribute('aria-label')==('最低场外占比 (%)' if other=='zh' else 'Minimum off-exchange share (%)')
     assert p.locator('#dp-trend option').first.text_content()==('全部趋势' if other=='zh' else 'All trends')
     assert p.locator('#dp-row-count').get_attribute('role')=='status'
     # Filtered CSV keeps its original columns, values and active sort order.
     with p.expect_download() as dw:click(p,p.locator('#dp-export'),touch)
     download=dw.value;csvfile=a.output_dir/(name+'.csv');download.save_as(str(csvfile));export=list(csv.DictReader(io.StringIO(csvfile.read_text())))
     assert [r['ticker'] for r in export]==tickers(p)
     fields=list(export[0]) if export else [];assert not fields or fields[-1]=='history_rebased'
     source={r['ticker']:r for r in rows}
     for r in export:
      for col in ['asof','participation','participation_z','short_rate','n_days']:
       v=source[r['ticker']].get(col)
       if v is None:assert r[col]==''
       elif isinstance(v,(int,float)):assert float(r[col])==v
       else:assert r[col]==str(v)
     search.fill('__uiux_no_match__');assert p.locator('.dp-empty').is_visible() and not tickers(p)
     click(p,p.locator('#dp-clear'),touch);assert p.evaluate('document.activeElement.id')=='dp-search';assert len(tickers(p))==total
     presets.first.focus();p.keyboard.press('Tab');p.keyboard.press('Shift+Tab');focus=presets.first.evaluate('e=>({active:document.activeElement===e,style:getComputedStyle(e).outlineStyle,width:parseFloat(getComputedStyle(e).outlineWidth)})');assert focus['active'] and focus['style']=='solid' and focus['width']>=2
     summary.scroll_into_view_if_needed();p.screenshot(path=str(a.output_dir/(name+'.png')))
     controls=p.locator('.filters-row input,.filters-row select,.filters-row button');assert min(controls.evaluate_all('es=>es.map(e=>e.getBoundingClientRect().height)'))>=40
     clips=controls.evaluate_all('es=>es.map(e=>({id:e.id,width:e.clientWidth,scroll:e.scrollWidth,right:e.getBoundingClientRect().right,max:e.closest(".sb").getBoundingClientRect().right}))');assert all(x['scroll']<=x['width']+1 and x['right']<=x['max']+1 for x in clips),(name,clips)
     overflow=p.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth')
     if overflow>1:
      offenders=p.evaluate('''[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().width && e.getBoundingClientRect().right>document.documentElement.clientWidth+1 && !e.closest('.tbl-wrap')).slice(0,30).map(e=>({tag:e.tagName,id:e.id,cls:e.className,text:e.innerText?.slice(0,80),rect:{x:e.getBoundingClientRect().x,width:e.getBoundingClientRect().width,right:e.getBoundingClientRect().right},position:getComputedStyle(e).position,display:getComputedStyle(e).display}))''')
      (a.output_dir/(name+'-overflow.json')).write_text(json.dumps(offenders,ensure_ascii=False,indent=2));print('OVERFLOW_DETAILS',name,json.dumps(offenders,ensure_ascii=False),flush=True)
     assert overflow<=1,(name,'overflow',overflow)
     assert not errors,(name,errors)
     row={'cell':name,'http':response.status,'page_sha256':hashlib.sha256(response.body()).hexdigest(),'data_sha256':hashlib.sha256(raw.encode()).hexdigest(),'rows':total,'native_presets':4,'native_sort_buttons':13,'sort_columns_exercised':checked,'preset_predicate_parity':True,'native_touch':touch,'sort_single_activation_and_focus':True,'locale_state_preserved':True,'filtered_csv_parity':True,'clear_focus_restored':True,'minimum_target_height':minheight,'actual_focus':focus,'controls_unclipped':True,'overflow':overflow,'errors':errors,'failed_responses':failed,'ticker_visible_on_horizontal_scroll':True,'passed':True};results.append(row);print(json.dumps(row,ensure_ascii=False),flush=True);p.close()
  browser.close()
finally:
 if srv:srv.shutdown();srv.server_close()
 (a.output_dir/'results.json').write_text(json.dumps({'mode':'public anonymous no interception' if a.base_url else 'immutable public-data candidate fixture, no interception; not production acceptance','cases':results},ensure_ascii=False,indent=2)+'\n')
