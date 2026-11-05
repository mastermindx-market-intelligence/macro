import argparse,json,hashlib,sys,traceback
from pathlib import Path
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright
ap=argparse.ArgumentParser();ap.add_argument('stage');ap.add_argument('url');ap.add_argument('server');ap.add_argument('output');a=ap.parse_args();out=Path(a.output);assert not out.exists();out.mkdir()
sys.path.insert(0,'/Volumes/Mastermind/evidence/defense-v3-20261012/o5/performance-priority-build/recovery-o6')
from verify_stage import verify_stage
stage=Path(a.stage);server=Path(a.server);h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();verify_stage(stage);r=json.loads(server.read_text());root=Path(r['source_root']);assert r['stage_receipt_sha256']==h(stage/'INPUT_RECEIPT.json')
def unchanged():
 for p,v in r['api_data_inputs'].items():assert (h(Path(p)) if Path(p).is_file() else None)==v,p
 for p,v in r['api_source_modules'].items():assert h(Path(p))==v,p
unchanged();payload=json.loads((root/'data/government_revenue/program_theme_public_disclosure.json').read_text());rows=[];errors=[]
ready="window.__govrevFirstInvestor&&window.__govrevFirstInvestor.pageState==='ready'&&document.querySelector('#programThemeContext[data-state=ready]')&&document.querySelectorAll('#queueList .queue-row').length===500"
with sync_playwright() as p:
 b=p.chromium.launch()
 for width,height,theme,lang in [(390,844,t,l) for t in ['dark','light'] for l in ['en','zh']]+[(390,600,t,'en') for t in ['dark','light']]+[(1440,1000,t,l) for t in ['dark','light'] for l in ['en','zh']]:
  key=f'{width}x{height}-{theme}-{lang}';row={'case':key,'pass':False};c=b.new_context(viewport={'width':width,'height':height},reduced_motion='reduce');page=c.new_page();pe=[];page.on('pageerror',lambda e:pe.append(str(e)))
  page.add_init_script('localStorage.setItem("theme",'+json.dumps(theme)+');localStorage.setItem("lang",'+json.dumps(lang)+');')
  try:
   page.goto(a.url,wait_until='commit');page.wait_for_function(ready,timeout=60000)
   row['overview']=page.evaluate("()=>({cards:document.querySelectorAll('.gr-theme-item').length,themeHeight:document.querySelector('#programThemeContext').getBoundingClientRect().height,queueHeight:document.querySelector('#queueList').getBoundingClientRect().height,pageHeight:document.documentElement.scrollHeight,rows:document.querySelectorAll('#queueList .queue-row').length,horizontalOverflow:document.documentElement.scrollWidth>innerWidth})")
   assert row['overview']['cards']==6 and row['overview']['rows']==500 and not row['overview']['horizontalOverflow']
   if width<980:assert row['overview']['queueHeight']<=585
   for t in payload['themes']:
    for kind in ['known','missing','next']:
     actual=page.locator('[data-theme-disclosure="'+t['theme_id']+':'+kind+'"] p').text_content();assert actual==t[kind+'_'+lang],(t['theme_id'],kind)
   page.locator('#programThemeTitle').scroll_into_view_if_needed();page.screenshot(path=str(out/(key+'-themes.png')))
   first=payload['themes'][0]['theme_id'];summary=page.locator('[data-theme-focus="'+first+':known"]');summary.focus();page.keyboard.press('Enter');assert page.locator('[data-theme-disclosure="'+first+':known"]').get_attribute('open') is not None
   nextlang='zh' if lang=='en' else 'en';page.evaluate('(lang)=>window.setLang(lang)',nextlang)
   assert page.locator('[data-theme-disclosure="'+first+':known"]').get_attribute('open') is not None
   assert page.evaluate('document.activeElement.getAttribute("data-theme-focus")')==first+':known'
   assert page.locator('[data-theme-disclosure="'+first+':known"] p').text_content()==payload['themes'][0]['known_'+nextlang]
   page.keyboard.press('Enter');page.evaluate('(lang)=>window.setLang(lang)',lang)
   src=page.locator('[data-theme-focus="'+first+':sources"]');src.focus();page.keyboard.press('Space');assert page.locator('[data-theme-disclosure="'+first+':sources"]').get_attribute('open') is not None
   page.screenshot(path=str(out/(key+'-sources-open.png')));page.keyboard.press('Space')
   page.locator('.gr-theme-workspace-link').click();page.locator('#queueList .queue-row').first.focus();page.keyboard.press('End')
   row['end']=page.evaluate("()=>{let q=document.querySelector('#queueList'),e=document.activeElement,rr=e.getBoundingClientRect(),qr=q.getBoundingClientRect(),bar=document.querySelector('.mobile-summary'),br=bar&&getComputedStyle(bar).display!=='none'?bar.getBoundingClientRect():null;return {last:e===q.lastElementChild,selected:e.getAttribute('aria-selected'),rowId:e.dataset.row,row:{top:rr.top,bottom:rr.bottom},queue:{top:qr.top,bottom:qr.bottom,scrollTop:q.scrollTop},viewport:innerHeight,barTop:br?br.top:innerHeight}}")
   e=row['end'];assert e['last'] and e['selected']=='true',e;assert e['row']['top']>=max(0,e['queue']['top'])-1 and e['row']['bottom']<=min(e['barTop'],e['viewport'],e['queue']['bottom'])+1,e
   page.screenshot(path=str(out/(key+'-queue-end.png')));page.keyboard.press('Home');assert page.evaluate("document.activeElement===document.querySelector('#queueList .queue-row')")
   page.locator('.gr-footer').scroll_into_view_if_needed();row['footer']=page.locator('.gr-footer').bounding_box();page.screenshot(path=str(out/(key+'-footer.png')));assert row['footer'] and row['footer']['y']<height
   assert not pe,pe;row['pass']=True
  except Exception as exc:row['error']=str(exc);row['traceback']=traceback.format_exc();page.screenshot(path=str(out/(key+'-failure.png')))
  finally:c.close();rows.append(row);print(json.dumps({'case':key,'pass':row['pass'],'error':row.get('error')}),flush=True)
 # A40: original reviewed program dossier, real same-generation endpoint and URL.
 c=b.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');page=c.new_page();row={'case':'A40-Virginia-class-program-deeplink-reload-back','pass':False}
 try:
  url=a.url+'?'+urlencode({'mode':'programs','item':'program:acq-program:virginia-class-ssn'})
  page.goto(url,wait_until='commit');page.wait_for_function("window.__govrevFirstInvestor&&window.__govrevFirstInvestor.pageState==='ready'&&document.querySelector('#inspector').textContent.includes('Virginia')",timeout=60000)
  row['observed']=page.locator('#inspector').inner_text();assert 'Virginia' in row['observed'];assert 'GD' in row['observed'] and 'HII' in row['observed'];row['url']=page.url
  page.reload(wait_until='commit');page.wait_for_function("document.querySelector('#inspector')&&document.querySelector('#inspector').textContent.includes('Virginia')",timeout=60000)
  page.goto(a.url+'?mode=companies&ticker=RTX&item=company%3ARTX',wait_until='commit');page.wait_for_function("document.querySelector('#inspector')&&document.querySelector('#inspector').textContent.includes('RTX')",timeout=60000);page.go_back(wait_until='commit');page.wait_for_function("document.querySelector('[data-mode=programs][aria-selected=true]')&&document.querySelector('#inspector').textContent.includes('Virginia')",timeout=60000)
  page.screenshot(path=str(out/'A40-program.png'));row['pass']=True
 except Exception as exc:row['error']=str(exc);row['traceback']=traceback.format_exc();page.screenshot(path=str(out/'A40-failure.png'))
 finally:c.close();rows.append(row);print(json.dumps({'case':row['case'],'pass':row['pass'],'error':row.get('error')}),flush=True)
 b.close()
unchanged();verify_stage(stage);result={'scope':'Actual canonical rendered local source ASGI; normal DOM/controller/native keyboard, canonical setLang API; not installed entitlement acceptance','stage_receipt_sha256':h(stage/'INPUT_RECEIPT.json'),'server_receipt_sha256':h(server),'all_pass':all(x['pass'] for x in rows),'cases':rows,'images':{p.name:h(p) for p in out.glob('*.png')}};(out/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['all_pass'] else 1)
