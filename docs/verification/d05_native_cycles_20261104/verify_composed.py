#!/usr/bin/env python3
"""D05 actual browser composition. Local fixture identity/data; no production access."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from urllib.parse import urlsplit
import argparse,base64,json,time,traceback,hashlib
p=argparse.ArgumentParser();p.add_argument('--width',type=int,default=1440);p.add_argument('--height',type=int,default=1000)
p.add_argument('--theme',default='dark');p.add_argument('--lang',default='en');p.add_argument('--proof-label',default='');args=p.parse_args()
if args.proof_label and not all(c.isalnum() or c=='-' for c in args.proof_label):raise ValueError('Invalid proof label')
OUT=Path(__file__).resolve().parent/('composed-%s-%s-%s'%(args.width,args.theme,args.lang)+('-'+args.proof_label if args.proof_label else ''));OUT.mkdir(exist_ok=True)
base='http://localhost:3100';child='http://localhost:8765'
user={'id':'e2e-user-default','email':'responsive@example.com','aud':'authenticated','app_metadata':{},'user_metadata':{}}
session={'access_token':'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJlMmUtdXNlci1kZWZhdWx0In0.fixture-only','refresh_token':'d05-fixture-only','expires_in':3600,'expires_at':int(time.time())+3600,'token_type':'bearer','user':user}
cookie='base64-'+base64.urlsafe_b64encode(json.dumps(session,separators=(',',':')).encode()).decode().rstrip('=')
results={'fixture_only':True,'proof_label':args.proof_label,'fixture_manifest_sha256':hashlib.sha256((Path(__file__).resolve().parent/'site/fixture_provenance.json').read_bytes()).hexdigest(),'viewport':[args.width,args.height],'theme':args.theme,'lang':args.lang,'steps':[],'errors':[],'restore_receipts':[]}
def step(name,details=None):
 results['steps'].append({'name':name,'details':details});print('PASS',name,flush=True)
def frame(page):
 page.wait_for_function("document.querySelector('main[data-shared-shell-phase]')?.dataset.sharedShellPhase==='ready'",timeout=45000)
 f=page.locator('iframe[data-shared-shell-frame]').element_handle().content_frame()
 assert f
 return f
def restored(page):
 page.wait_for_function("['applied','partial','rejected'].includes(document.querySelector('main[data-shared-shell-phase]')?.dataset.sharedShellRestore)",timeout=20000)
 state=page.locator('main[data-shared-shell-phase]').get_attribute('data-shared-shell-restore')
 assert state=='applied',state
def canonical_origin(value):
 value=json.loads(json.dumps(value))
 if value is None:return None
 for owner in (value,value['entry']):
  u=urlsplit(owner['href'])
  query='&'.join(part for part in u.query.split('&') if part.split('=',1)[0] not in ('mmx_shell','mmx_generation'))
  owner['href']=u.path+('?' + query if query else '')+('#' + u.fragment if u.fragment else '')
 return value
def state(page):return page.evaluate("JSON.parse(JSON.stringify(history.state.mmxOriginEntry))")
def snap(page,name):
 expected_theme='dark' if page.url.split('?')[0].endswith('/terminal') else args.theme
 assert page.evaluate('document.documentElement.dataset.theme')==expected_theme,'actual theme differs from route presentation contract: '+name
 assert page.evaluate('document.documentElement.dataset.lang')==args.lang,'actual locale differs from requested case: '+name
 results.setdefault('rendered_presentation',[]).append({'capture':name,'path':urlsplit(page.url).path,'theme':expected_theme,'lang':args.lang,'boundary':'native Company dark' if expected_theme!=args.theme else 'shared presentation'})
 page.screenshot(path=str(OUT/(name+'.png')),full_page=False)
 assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),'outer horizontal overflow: '+name
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,chromium_sandbox=True)
 ctx=browser.new_context(viewport={'width':args.width,'height':args.height},reduced_motion='reduce',has_touch=args.width<1024)
 ctx.add_init_script("""(({theme,lang})=>{
 localStorage.setItem('theme',theme);localStorage.setItem('lang',lang);
 localStorage.setItem('mm.theme',theme);localStorage.setItem('mm.lang',lang);
 if(location.port==='8765'){window.MM_TERMINAL_BASE='https://app.mastermind-x.com/terminal';window.SUPABASE_CFG={url:'http://localhost:8765/fixture-auth',anonKey:'d05-fixture-only',ref:'d05-native-fixture'};}
 window.__d05RestoreReceipts=[];window.addEventListener('message',e=>{if(e.data&&e.data.type==='RESTORE_RESULT')window.__d05RestoreReceipts.push(e.data);});

})("""+json.dumps({'theme':args.theme,'lang':args.lang})+");")
 ctx.add_cookies([{'name':'sb-d05-native-fixture-auth-token','value':cookie,'url':child},{'name':'mm_e2e_rs30','value':'1','url':base}])
 def route(r):
  u=r.request.url
  if u.startswith(child+'/fixture-auth/auth/v1/user'):
   r.fulfill(status=200,content_type='application/json',body=json.dumps(user));return
  if u.startswith((child+'/',base+'/')):r.continue_();return
  r.abort()
 ctx.route('**/*',route)
 page=ctx.new_page();page.on('pageerror',lambda e:results['errors'].append(str(e)))
 try:
  page.goto(base+'/sector_central.html?g=XLE#map',wait_until='domcontentloaded',timeout=90000)
  f=frame(page);f.wait_for_function("window.BASKETS && document.querySelector('#mr-cycle-link')")
  # Exercise the actual shared toolbar: account hydration may override boot storage.
  if page.evaluate("document.documentElement.dataset.theme")!=args.theme:
   theme_name='浅色主题' if page.evaluate("document.documentElement.dataset.lang")=='zh' else 'Light theme'
   page.get_by_role('button',name=theme_name,exact=True).filter(visible=True).click()
  page.wait_for_function("(expected)=>document.documentElement.dataset.theme===expected",arg=args.theme)
  f.wait_for_function("(expected)=>document.documentElement.dataset.theme===expected",arg=args.theme)
  assert page.evaluate("document.documentElement.dataset.lang")==args.lang
  results['observed_presentation']={'theme':page.evaluate("document.documentElement.dataset.theme"),'lang':page.evaluate("document.documentElement.dataset.lang")}

  f.locator('#si-map-tabs [data-fam="sectors"]').click()
  f.locator('.mr-segbtn[data-h="obs"]').click()
  f.locator('#mr-cycle-link').click()
  page.wait_for_function("location.hash==='#cycles'")
  f.wait_for_function("window.SectorCyclesCapture?.()?.focus==='xle'")
  assert f.evaluate("!!MDXAuth.user()"),'native fixture identity not settled'
  assert state(page)['ownerKey']=='account:e2e-user-default'
  step('market map to native Cycles through actual Next same-document commit')
  if f.locator('#sc-adv-toggle').is_visible():f.locator('#sc-adv-toggle').click()
  f.locator('#sc-modes [data-mode="price"]').click()
  f.locator('#sc-scale [data-scale="linear"]').click()
  f.locator('#sc-zoom [data-i="3"]').click()
  # A state-only chart edit must reach the parent before any later scroll or navigation.
  scale_control=f.locator('#sc-scale [data-scale="log"]');scale_control.scroll_into_view_if_needed()
  quiet_y=f.evaluate('scrollY');quiet_entry=state(page)['entryKey']
  scale_control.click()
  page.wait_for_function("history.state.mmxOriginEntry?.view?.page?.value?.siWorkspace?.cycles?.scale==='log'")
  assert f.evaluate('scrollY')==quiet_y
  assert state(page)['entryKey']==quiet_entry
  quiet_saved=state(page)['view']['page']['value']
  page.reload(wait_until='domcontentloaded',timeout=90000)
  f=frame(page);restored(page)
  quiet_after=f.evaluate('SectorWorkspaceExport()')
  assert quiet_after['siWorkspace']['cycles']==quiet_saved['siWorkspace']['cycles']
  assert canonical_origin(quiet_after['siCyclesOrigin'])==quiet_saved['siCyclesOrigin']
  step('State-only chart edit survives a parent reload without a new navigation entry')
  if f.locator('#sc-adv-toggle').is_visible() and not f.locator('#sc-scale [data-scale="linear"]').is_visible():f.locator('#sc-adv-toggle').click()
  f.locator('#sc-scale [data-scale="linear"]').click()
  f.locator('#sc-dossier-toggle').click()
  f.locator('#sc-dossier-mount .sdc-action').first.wait_for()
  if args.width<=880:
   results['sheet_readback']=f.evaluate("""()=>({open:document.getElementById('sc-dossier').open,studyClass:document.getElementById('sc-native-study').className,parent:document.getElementById('sc-detail').parentElement.className,contained:document.getElementById('sc-native-study').contains(document.getElementById('sc-detail')),display:getComputedStyle(document.getElementById('sc-detail')).display,width:innerWidth,matchingRules:[...document.styleSheets].flatMap(sheet=>{try{return [...sheet.cssRules].map(r=>r.cssText).filter(t=>t.includes('sc-dossier-active'))}catch(e){return []}})})""")
   assert not f.locator('#sc-detail').is_visible(),results['sheet_readback']
   selected=f.evaluate('SectorCyclesCapture().focus')
   f.locator('#sc-dossier-toggle').click()
   assert f.locator('#sc-detail').is_visible(),'closing the Dossier must return the original selected Cycle sheet'
   assert f.evaluate('SectorCyclesCapture().focus')==selected
   f.locator('#sc-dossier-toggle').click()
   f.locator('#sc-dossier-mount .sdc-action').first.wait_for()
   assert not f.locator('#sc-detail').is_visible()

  f.locator('#sc-dossier-mount [data-sdc-focus="values"]').click()
  f.locator('#sc-dossier-mount [data-sdc-focus="next"]').click()
  f.locator('#sc-dossier-mount [data-sdc-focus="sources"]').click()
  f.wait_for_function("SectorWorkspaceExport()?.siWorkspace.dossier?.view?.valuesOffset===50")
  f.locator('#sc-dossier').evaluate("el=>el.scrollIntoView({block:'start'})")
  if args.width<=880:assert not f.locator('#sc-detail').is_visible(),'native Cycle sheet must not obscure the Dossier'
  assert page.evaluate("document.documentElement.dataset.theme")==args.theme
  assert f.evaluate("document.documentElement.dataset.theme")==args.theme
  snap(page,'01-central-dossier')
  assert f.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),'native Dossier overflow'
  member_button=f.locator('#sc-dossier-mount [data-sdc-focus="action-members"]')
  member_button.scroll_into_view_if_needed();member_button.focus()
  before=f.evaluate("SectorWorkspaceExport()")
  assert before['siWorkspace']['dossier']['view']['valuesOpen']
  assert before['siWorkspace']['dossier']['view']['sourcesOpen']
  step('actual Dossier, chart settings and both evidence disclosures')
  member_button.click()
  page.wait_for_function("location.pathname==='/basket/us_sector_energy.html'")
  f=frame(page);f.wait_for_function("window.SectorMembersExport?.()")
  saved=state(page)['centralOrigin']
  assert saved and saved['view']['page']['value']['siWorkspace']['dossier']['view']['valuesOffset']==50
  assert saved['view']['page']['value']['siWorkspace']['viewport']['focus']=={'kind':'dossier','id':'action-members'}
  assert saved['view']['page']['value']['siWorkspace']['cycles']==before['siWorkspace']['cycles']
  step('Dossier Members action preserves the Central snapshot',{'href':page.url,'owner':state(page)['ownerKey']})
  f.locator('#hold button[data-hold-sort="r20"]').click()
  f.locator('#hold button[data-hold-sort="r20"]').click()
  listing=f.locator('#hold a[data-member-symbol="XOM"]');listing.scroll_into_view_if_needed();listing.focus()
  f.evaluate("membersTableScroller().scrollLeft=Math.min(80,membersTableScroller().scrollWidth-membersTableScroller().clientWidth)")
  member_before=f.evaluate("SectorMembersExport()")
  assert member_before['sort']=={'col':'r20','dir':1}
  assert member_before['focus']=={'kind':'listing','symbol':'XOM'}
  snap(page,'02-members')
  listing.click()
  page.wait_for_function("location.pathname==='/terminal'",timeout=60000)
  back_name='返回成分股' if args.lang=='zh' else 'Back to Members'
  back=page.get_by_role('button',name=back_name,exact=True);back.first.wait_for(state='visible',timeout=60000)
  company=state(page)
  assert company['ownerKey']=='account:e2e-user-default'
  assert company['returnTo']['view']['page']['kind']=='d05-sector-members'
  assert company['returnTo']['view']['page']['value']['sort']==member_before['sort']
  assert company['centralOrigin']==saved
  assert 'XOM' in page.url
  snap(page,'03-company')
  if args.theme=='light':assert page.evaluate("localStorage.getItem('mmx.shell.theme')")=='light','Company overwrote public light preference'
  step('Members to actual Company route retains both destinations',{'href':page.url,'entry':company['entryKey']})
  page.reload(wait_until='domcontentloaded',timeout=90000)
  back=page.get_by_role('button',name=back_name,exact=True);back.first.wait_for(state='visible',timeout=60000)
  assert state(page)['returnTo']==company['returnTo']
  assert state(page)['centralOrigin']==saved
  assert page.evaluate("document.documentElement.dataset.theme")=='dark','Company reload must preserve native chart presentation'
  assert page.evaluate("document.documentElement.dataset.lang")==args.lang
  if args.theme=='light':assert page.evaluate("localStorage.getItem('mmx.shell.theme')")=='light'
  step('Company reload preserves entry-owned return context and native dark presentation')
  back.first.click()
  page.wait_for_function("location.pathname==='/basket/us_sector_energy.html'",timeout=60000)
  f=frame(page);restored(page)
  member_after=f.evaluate("SectorMembersExport()")
  assert member_after==company['returnTo']['view']['page']['value'],(member_after,company['returnTo']['view']['page']['value'])
  assert state(page)['centralOrigin']==saved
  snap(page,'04-members-returned')
  step('Back to Members restores source, exact sort, listing focus and viewport')
  central_name='返回周期研究' if args.lang=='zh' else 'Return to Cycles investigation'
  page.get_by_role('button',name=central_name,exact=True).first.click()
  page.wait_for_function("location.pathname==='/sector_central.html' && location.hash==='#cycles'",timeout=60000)
  f=frame(page);restored(page)
  after=f.evaluate("SectorWorkspaceExport()")
  expected=saved['view']['page']['value']['siWorkspace']
  assert after['siWorkspace']['cycles']==expected['cycles']
  assert after['siWorkspace']['dossier']==expected['dossier']
  results['central_viewport_readback']={'actual':after['siWorkspace']['viewport'],'expected':expected['viewport']}
  assert after['siWorkspace']['viewport']==expected['viewport'],results['central_viewport_readback']
  assert canonical_origin(after['siCyclesOrigin'])==saved['view']['page']['value']['siCyclesOrigin'],{'actual':after['siCyclesOrigin'],'expected':saved['view']['page']['value']['siCyclesOrigin']}
  assert f.locator('#si-restore-status').count()==1
  snap(page,'05-central-returned')
  step('Return to Cycles restores chart, Dossier values page, sources and exact focus')
  f.locator('#sc-cycle-return').click()
  page.wait_for_function("location.hash==='#map'")
  assert f.evaluate("SectorWorkspaceExport().siWorkspace.measured.historyMode")=='obs'
  step('Cycles to original market map restores observed-history mode')
  results['restore_receipts']=page.evaluate("window.__d05RestoreReceipts")
  assert not results['errors'],results['errors']
  results['passed']=True
 except Exception as e:
  results['passed']=False;results['failure']=str(e);results['traceback']=traceback.format_exc()
  results['last_url']=page.url
  try:results['last_state']=state(page);results['restore_receipts']=page.evaluate("window.__d05RestoreReceipts");snap(page,'failure')
  except Exception:pass
  print('FAIL',results['traceback'],flush=True)
 finally:
  (OUT/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
  print(json.dumps({'passed':results.get('passed'),'steps':len(results['steps']),'errors':results['errors'],'out':str(OUT)},ensure_ascii=False),flush=True)
  browser.close()
if not results.get('passed'):raise SystemExit(1)
