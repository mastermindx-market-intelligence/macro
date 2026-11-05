#!/usr/bin/env python3
"""Real DOM tests of the incumbent Members template. Fixture display data only."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json,traceback
ROOT=Path(__file__).resolve().parent
variants=json.loads((ROOT/'site/member_variants.json').read_text())
BASE='http://localhost:8765'
report={'fixture_only':True,'cases':[],'errors':[]}
def ok(name,detail=None):
 report['cases'].append({'name':name,'detail':detail});print('PASS',name,flush=True)
def export(page):return page.evaluate('SectorMembersExport()')
def apply(page,view):
 return page.evaluate("""v=>new Promise(resolve=>SectorMembersApplyCurrent(v,{expectedHref:location.pathname+location.search+location.hash,onResult:resolve}))""",view)
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,chromium_sandbox=True)
 ctx=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce',has_touch=True)
 ctx.add_init_script("localStorage.setItem('lang','en');localStorage.setItem('theme','dark');")
 def route(r):
  path=r.request.url.split('?',1)[0]
  selected=next((v for v in variants.values() if r.request.url==BASE+v['path']+'?variant='+next(k for k,x in variants.items() if x is v)),None)
  if selected:
   r.fulfill(status=200,content_type='text/html',body=Path(selected['file']).read_text());return
  if r.request.url.startswith(BASE+'/'):r.continue_();return
  r.abort()
 ctx.route('**/*',route)
 page=ctx.new_page();page.on('pageerror',lambda e:report['errors'].append(str(e)))
 try:
  page.goto(BASE+'/basket/us_sector_energy.html#hold',wait_until='domcontentloaded')
  page.wait_for_function("window.SectorMembersExport?.()")
  current=export(page);assert current['region']=='us' and current['basketId']=='us_sector_energy'
  assert current['sourceId'].startswith('members1-') and not current['sourceId'].startswith('cycp1-')
  page.evaluate("(()=>{const x=SectorMembersExport();x.sort.col='bad';x.viewport.y=99;x.focus={kind:'listing',symbol:'bad'};})()")
  assert export(page)==current
  ok('detached emitted-display identity and settings projection')
  page.locator('#hold button[data-hold-sort="r20"]').click()
  page.locator('#hold button[data-hold-sort="r20"]').click()
  page.locator('#hold a[data-member-symbol="XOM"]').focus()
  page.evaluate("membersTableScroller().scrollLeft=80;window.scrollTo(0,document.querySelector('#hold').getBoundingClientRect().top+scrollY)")
  saved=export(page);assert saved['sort']=={'col':'r20','dir':1} and saved['viewport']['tableX']==80
  assert saved['focus']=={'kind':'listing','symbol':'XOM'}
  page.locator('#hold button[data-hold-sort="recommend"]').click()
  receipt=apply(page,saved);assert receipt['status']=='applied',receipt;assert export(page)==saved
  ok('exact sort direction, listing focus and horizontal/vertical viewport restored',receipt)
  page.locator('#hold a[data-member-symbol="CVX"]').focus()
  page.evaluate("membersTableScroller().scrollLeft=120;render()")
  later=export(page);assert later['focus']=={'kind':'listing','symbol':'CVX'} and later['viewport']['tableX']==120
  ok('asynchronous incumbent rerender preserves the current focus and table position')
  before=export(page)
  bads=[
   {**before,'sourceId':'members1-'+'f'*64},
   {**before,'basketId':'another'},
   {**before,'region':'canada'},
   {**before,'asOf':'2020-01-01'},
   {**before,'extra':True},
   {**before,'sort':{'col':'future','dir':1}},
   {**before,'sort':{'col':'r20','dir':0}},
   {**before,'viewport':{'x':0,'y':-1,'tableX':0}},
   {**before,'focus':{'kind':'listing','symbol':'XOM\n'}},
  ]
  for i,bad in enumerate(bads):
   receipt=apply(page,bad);assert receipt['status']=='rejected',(i,receipt);assert export(page)==before
  ok('nine invalid or different-source projections rejected before view effects')
  missing={**before,'focus':{'kind':'listing','symbol':'NO_SUCH_LISTING'}}
  receipt=apply(page,missing);assert receipt['status']=='partial' and receipt['focus']=='unavailable',receipt
  ok('missing exact listing is partial, never fully restored',receipt)
  interrupted=page.evaluate("""v=>new Promise(resolve=>{
   let calls=[];const op=SectorMembersApplyCurrent(v,{onResult:r=>calls.push(r)});
   document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true}));
   requestAnimationFrame(()=>requestAnimationFrame(()=>resolve(calls)));
  })""",before)
  assert len(interrupted)==1 and interrupted[0]['status']=='rejected' and interrupted[0]['reason']=='user_input',interrupted
  ok('input before application cancels once with no late success',interrupted)
  late=page.evaluate("""v=>new Promise(resolve=>{
   const calls=[];SectorMembersApplyCurrent(v,{onResult:r=>calls.push(r)});
   requestAnimationFrame(()=>{document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true}));requestAnimationFrame(()=>resolve(calls));});
  })""",before)
  assert len(late)==1 and late[0]['status']=='partial' and late[0]['reason']=='user_input',late
  ok('input after application reports the interrupted partial state once',late)
  newer=page.evaluate("""v=>new Promise(resolve=>{
   const calls=[];SectorMembersApplyCurrent(v,{onResult:r=>calls.push(['first',r])});
   SectorMembersApplyCurrent(v,{onResult:r=>{calls.push(['second',r]);resolve(calls)}});
  })""",before)
  assert len(newer)==2 and newer[0][1]['reason']=='new_intent' and newer[1][1]['status']=='applied',newer
  ok('new intent retires the old operation before the successor result')
  page.screenshot(path=str(ROOT/'members-dom-restored-390.png'),full_page=False)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  ok('390px table scroll stays within the page')
  for name,v in variants.items():
   page.goto(BASE+v['path']+'?variant='+name,wait_until='domcontentloaded')
   page.wait_for_function("typeof SectorMembersExport==='function' && document.querySelector('#hold')")
   data=export(page)
   if name=='unavailable':
    assert data is None
    assert 'Member source unavailable for this snapshot.' in page.locator('#hold').inner_text()
    ok('missing membership remains unavailable rather than zero members');continue
   assert data['sourceId']==v['sourceId'] and data['asOf'] is None
   if name=='empty':
    assert page.locator('#hold a[data-member-symbol]').count()==0
    assert 'No members supplied in this snapshot.' in page.locator('#hold').inner_text()
    ok('explicit empty membership remains a known empty set');continue
   symbols=page.locator('#hold a[data-member-symbol]').evaluate_all("nodes=>nodes.map(n=>n.dataset.memberSymbol)")
   assert symbols==v['symbols'],(name,symbols,v['symbols'])
   target={**data,'focus':{'kind':'listing','symbol':symbols[0]}}
   receipt=apply(page,target)
   if name=='duplicate':
    assert receipt['status']=='partial' and receipt['focus']=='unavailable',receipt
    ok('ambiguous duplicate listing is partial')
   else:
    assert receipt['status']=='applied',receipt
    assert export(page)['focus']['symbol']==symbols[0]
    href=page.locator('#hold a[data-member-symbol]').first.get_attribute('href')
    assert href.split('#')[1]==symbols[0],href
    ok(name+' preserves exact region, suffix and leading-zero listing identity',{'symbols':symbols,'href':href})
  assert not report['errors'],report['errors']
  report['passed']=True
 except Exception:
  report['passed']=False;report['failure']=traceback.format_exc();print(report['failure'],flush=True)
  try:page.screenshot(path=str(ROOT/'members-dom-failure.png'),full_page=False)
  except Exception:pass
 finally:
  (ROOT/'members_dom_result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
  print(json.dumps({'passed':report['passed'],'cases':len(report['cases']),'errors':report['errors']},ensure_ascii=False),flush=True)
  browser.close()
if not report['passed']:raise SystemExit(1)
