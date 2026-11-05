"""Actual browser QA of changed confluence/rotation consumers, deterministic local data."""
from pathlib import Path
import importlib.util,json,os,re,shutil,sys
from jinja2 import ChoiceLoader,DictLoader,Environment,FileSystemLoader
from playwright.sync_api import sync_playwright
w=Path(__file__).resolve().parent
root=Path(os.environ.get('D05_SOURCE_ROOT',str(w.parents[2])))
candidate=w/'route-regression' if (w/'route-regression').exists() else root
out=w/'site'/'d05-route-fixtures';out.mkdir(exist_ok=True)
proof=w/'route-browser';proof.mkdir(exist_ok=True)
def fixture_html(html):
 return html.replace('</body>','<div style="position:fixed;bottom:0;left:0;z-index:100000;background:var(--panel);color:var(--muted);padding:3px 8px;font:10px sans-serif">D05 CONSUMER FIXTURE · NOT LIVE</div></body>')
spec=importlib.util.spec_from_file_location('d05_route_tests',candidate/'tests/test_d05_route_evidence_semantics.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
env=Environment(loader=ChoiceLoader([DictLoader({'_site_nav.html.j2':'','_seo_head.html.j2':''}),FileSystemLoader(candidate/'templates'),FileSystemLoader(root/'templates')]),autoescape=True)
group=m._group(n_priced=0,members=[{'ticker':'XOM','price':100,'ret_20d':4.2,'vs_basket':1.7,'stock_tier':'T1','stock_buyable':True,'stock_state':'Confirmed'}])
detail=env.get_template('subsector_detail.html.j2').render(detail_json=json.dumps({'group':group,'kind':'subsector'}),group_name='Energy',chart_key=None,has_signals=False)
(out/'subsector').mkdir(exist_ok=True);(out/'subsector'/'energy.html').write_text(fixture_html(detail))
(out/'subsectors.html').write_text(fixture_html(env.get_template('subsectors.html.j2').render()))
(out/'subsectors.js').write_text((candidate/'templates/subsectors.js').read_text())
for asset in ['theme.css','theme.js','stock_chart.js','stock_chart.css','supabase.js']:
 src=w/'site'/asset
 if src.exists():shutil.copyfile(src,out/asset)
# Import the actual candidate builder helpers, leaving the model unchanged.
spec=importlib.util.spec_from_file_location('d05_rotation_builder',candidate/'scripts/build_subsector_rotation_pages.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
env.globals['fmt_pc']=b._fmt_pc
sub=m._sub();members=sorted(sub['members'],key=lambda x:x['1M'],reverse=True)[:30]
lede=b._lede(sub)
rot=env.get_template('subsector_rotation_detail.html.j2').render(sub=sub,n_total=1,members=members,perf_rows=b.PERF_ROWS,q_cls='q-lead',q_en='Leading',q_zh='领先',qx_en='strong & rising',qx_zh='强且上行',lede_en=lede[0],lede_zh=lede[1],asof='2026-10-30',members_available=31,member_limit=30)
(out/'rotation').mkdir(exist_ok=True);(out/'rotation'/'energy.html').write_text(fixture_html(rot))
payload={'ok':True,'as_of':'2026-10-30','subsectors':[group],'baskets':[group],'entry_now':['energy'],'forming':[],'headwind':[],'sectors':[],'double_gated':[],'coverage':{'n_subsectors':10,'n_listed':10,'n_gateable':1,'n_thin':9}}
base='http://localhost:8765/d05-route-fixtures'
results={'fixture_only':True,'source':'explicit D05 candidate renderers; current producer semantics','cases':[],'errors':[]}
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,chromium_sandbox=True)
 for width,theme,lang in [(1440,'dark','en'),(1440,'light','zh'),(390,'light','zh'),(320,'dark','en')]:
  ctx=browser.new_context(viewport={'width':width,'height':1000 if width>1000 else 844},reduced_motion='reduce')
  ctx.add_init_script("localStorage.setItem('theme',"+json.dumps(theme)+");localStorage.setItem('lang',"+json.dumps(lang)+");")
  def route(r):
   if '/marketdata/' in r.request.url:
    r.fulfill(status=200,content_type='application/json',body=json.dumps(payload if 'confluence' in r.request.url else None));return
   if r.request.url.startswith('http://localhost:8765/'):r.continue_()
   else:r.abort()
  ctx.route('**/*',route)
  page=ctx.new_page();page.on('pageerror',lambda e:results['errors'].append(str(e)))
  for path,ready,scroll in [('subsectors.html','#sc-fulltable','#sc-fulltable'),('subsector/energy.html','.id-evidence','#members'),('rotation/energy.html','.sd-member-coverage','.sd-grid')]:
   page.goto(base+'/'+path,wait_until='domcontentloaded')
   page.locator(ready).wait_for(state='attached')
   page.locator(scroll).scroll_into_view_if_needed()
   assert page.evaluate('document.documentElement.dataset.theme')==theme
   assert page.evaluate('document.documentElement.dataset.lang')==lang
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(path,width,'document overflow')
   name=str(width)+'-'+theme+'-'+lang+'-'+path.replace('/','-')
   page.screenshot(path=str(proof/(name+'.png')),full_page=False)
   results['cases'].append({'path':path,'width':width,'theme':theme,'lang':lang,'screenshot':name+'.png','passed':True})
  ctx.close()
 browser.close()
results['passed']=not results['errors']
(proof/'result.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({'passed':results['passed'],'cases':len(results['cases']),'errors':results['errors']}))
if not results['passed']:raise SystemExit(1)
