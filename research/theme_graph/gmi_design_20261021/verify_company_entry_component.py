"""GMI company-entry comparison and focused search recovery on generated pages.

Anonymous isolated loopback contexts use exact accepted-model output and shared
theme/GMI CSS, with external requests blocked. The company-empty fixture is a
production-rendered deep copy with issuers=[], never a replacement public model.
November9/20 clocks and a 44px Brain launcher are explicit layout fixtures. No
full shared-shell/font, live-account, shared Brain-runtime, spoken AT, public
admission, current hosted CI or deployment acceptance is established here.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import http.server
import json
import re
from pathlib import Path
import threading
import traceback
from urllib.parse import parse_qs, urlencode, urlsplit
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, expect

parser=argparse.ArgumentParser()
parser.add_argument('--root',type=Path,required=True)
parser.add_argument('--executable',required=True)
parser.add_argument('--baseline',action='store_true')
parser.add_argument('--case-family',choices=('all','header','focus','static','empty','regression'),default='all')
parser.add_argument('--case',default='')
args=parser.parse_args()
args.out=args.root/('baseline-proof' if args.baseline else 'candidate-proof')
args.out.mkdir(exist_ok=True)
source=args.root/('baseline' if args.baseline else 'candidate')
script=(source/'gmi.js').read_text()
style=(args.root/'templates/theme.css').read_text()+'\n'+(source/'gmi.css').read_text()
parts={}
for name in ('gmi.html','gmi-index.html','gmi-companies.html','gmi-issuer-mu.html','gmi-coverage.html','gmi-relationships.html','gmi-states.html'):
    soup=BeautifulSoup((source/name).read_text(),'html.parser')
    main=soup.select_one('main#main')
    assert main is not None
    extra=[]
    for selector in ('#gmi-topic-data','[data-gmi-announcement]','[data-browse-dialog]'):
        node=soup.select_one(selector)
        if node is not None and main not in node.parents:
            extra.append(str(node))
    parts[name]=str(main)+''.join(extra)
empty_source=args.root/('baseline-empty' if args.baseline else 'candidate-empty')/'gmi-companies.html'
empty_main=str(BeautifulSoup(empty_source.read_text(),'html.parser').select_one('main#main'))
report={'generated_at':datetime.now(timezone.utc).isoformat(),'baseline':args.baseline,'case_family':args.case_family,'scope':__doc__.strip(),
        'script_sha256':hashlib.sha256(script.encode()).hexdigest(),
        'gmi_css_sha256':hashlib.sha256((source/'gmi.css').read_bytes()).hexdigest(),
        'verifier_sha256':hashlib.sha256((args.root/'verify_product_browser.py').read_bytes()).hexdigest(),
        'inputs':json.loads((args.root/'input-bindings.json').read_text()),
        'cases':[],'contexts':0,'screenshots':[],'page_errors':[]}

# Real loopback serving also covers Chrome's first modified-click navigation,
# which is not observed by the fictional-origin route interceptor on this host.
documents={}
class Fixture(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body=documents.get(urlsplit(self.path).path)
        if body is None:
            self.send_error(404);return
        payload=body.encode()
        self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length',str(len(payload)))
        self.end_headers();self.wfile.write(payload)
    def log_message(self,*args):
        pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Fixture)
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}'
context_routes={}

with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=args.executable,headless=True)
    report['browser']=browser.version

    def context(width=1440,theme='light',language='en',empty_catalogue=False,**kwargs):
        c=browser.new_context(viewport={'width':width,'height':1000 if width>800 else 844},device_scale_factor=1,**kwargs)
        report['contexts']+=1
        prefix='/case-'+str(report['contexts'])+'/'
        context_routes[c]=prefix
        for name,part in parts.items():
            if empty_catalogue and name=='gmi-companies.html':part=empty_main
            documents[prefix+name]='<!doctype html><html data-lang="'+language+'" data-theme="'+theme+'"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+style+'</style></head><body class="page-macro gmi-page gmi-product">'+part+'<script>'+script+'</script></body></html>'
            documents['/'+name]=documents[prefix+name]
        def serve(route):
            if not route.request.url.startswith(base+'/'):
                return route.abort()
            route.continue_()
        c.route('**/*',serve)
        c.on('page',lambda p:p.on('pageerror',lambda e:report['page_errors'].append(str(e))))
        return c

    def page_for(c,route='gmi.html'):
        p=c.new_page()
        p.goto(base+context_routes[c]+route,wait_until='networkidle')
        return p

    # Execute the actual named definitions from the one canonical verifier.
    verifier=args.root/'verify_product_browser.py'
    parsed=ast.parse(verifier.read_text())
    names={'gmi_navigation_fit','company_results_source_context','return_journey','company_entry_geometry','company_entry_header','company_entry_focus','company_entry_static','index_category_picker_paths'}
    definitions=sorted([n for n in ast.walk(parsed) if isinstance(n,ast.FunctionDef) and n.name in names],key=lambda n:n.lineno)
    assert {n.name for n in definitions}==names and len(definitions)==len(names)
    exec(compile(ast.Module(body=definitions,type_ignores=[]),str(verifier),'exec'),globals())
    # This explicit empty-model fixture belongs to this harness, not the full-site context.
    def company_entry_empty_catalogue(language):
        """A production-rendered issuers=[] fixture keeps no evidence distinct from no match."""
        with context(320,'light',language,reduced_motion='reduce',empty_catalogue=True) as c:
            p=page_for(c,'gmi-companies.html#q=Micron')
            search=p.locator('[data-company-search]');empty=p.locator('[data-company-empty]');reset=p.locator('[data-company-reset]')
            expect(p.locator('[data-company-card]')).to_have_count(0);expect(empty).to_be_visible();expect(reset).not_to_be_visible()
            title=empty.locator('h2');expect(title).to_have_text('No company evidence yet暂无公司证据')
            assert title.inner_text().strip()==('No company evidence yet' if language=='en' else '暂无公司证据')
            explore=empty.locator('a');assert explore.get_attribute('href')=='gmi.html'
            expect(p.locator('[data-company-count]')).to_have_text('0 matching companies' if language=='en' else '匹配到 0 家公司')
            explore.focus()
            p.evaluate('''()=>{const h=new URLSearchParams(location.hash.slice(1));h.set('q','HBM');history.replaceState(null,'','#'+h);dispatchEvent(new PopStateEvent('popstate'));}''')
            expect(search).to_have_value('HBM');expect(explore).to_be_focused();expect(reset).not_to_be_visible()
            other='zh' if language=='en' else 'en';p.evaluate('(v)=>document.documentElement.setAttribute("data-lang",v)',other)
            expect(p.locator('[data-company-count]')).to_have_text('匹配到 0 家公司' if other=='zh' else '0 matching companies')
            expect(explore).to_be_focused();expect(reset).not_to_be_visible()
            assert title.inner_text().strip()==('暂无公司证据' if other=='zh' else 'No company evidence yet')
            search.fill('');expect(reset).not_to_be_visible();expect(empty).to_be_visible()
            expect(p.locator('[data-company-count]')).to_have_text('有收录证据的公司：0 家' if other=='zh' else '0 companies with evidence on file')
            assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
            report.setdefault('company_entry_empty_catalogue',[]).append({'language':language,'fixture':'production-rendered deep copy of accepted model with issuers=[]','cards':0,'reset_hidden':True,'distinct_empty_message':True,'native_explore_route':'gmi.html'})
    
    
    matrix=tuple((w,l) for w in (1440,390,320) for l in ('en','zh'))
    actions=[]
    if args.case_family in ('all','header'):
        actions.extend((f'company-entry-header-{w}-{l}',lambda w=w,l=l:company_entry_header(w,l,consolidated=not args.baseline)) for w,l in matrix)
        actions.extend((f'company-entry-composite-{w}-{l}',lambda w=w,l=l:company_entry_header(w,l,stale=True,consolidated=not args.baseline)) for w,l in ((320,'en'),(390,'zh'),(768,'en')))
        actions.extend((f'company-entry-dark-{w}-{l}',lambda w=w,l=l:company_entry_header(w,l,'dark',consolidated=not args.baseline)) for w,l in ((390,'en'),(320,'zh')))
    if args.case_family in ('all','focus'):
        focus_matrix=((390,'en'),(320,'zh')) if args.baseline else matrix
        actions.extend((f'company-entry-focus-{w}-{l}',lambda w=w,l=l:company_entry_focus(w,l)) for w,l in focus_matrix)
    if not args.baseline:
        if args.case_family in ('all','static'):
            actions.extend((f'company-entry-static-{w}-{l}',lambda w=w,l=l:company_entry_static(w,l)) for w in (1440,320) for l in ('en','zh'))
        if args.case_family in ('all','empty'):
            actions.extend((f'company-entry-empty-{l}',lambda l=l:company_entry_empty_catalogue(l)) for l in ('en','zh'))
        if args.case_family in ('all','regression'):
            actions.extend((f'company-source-context-{w}-{l}',lambda w=w,l=l:company_results_source_context(w,'light',l)) for w,l in ((390,'en'),(320,'zh')))
            actions.extend((f'company-return-journey-{w}-{l}',lambda w=w,l=l:return_journey(w,'light',l)) for w,l in ((1440,'en'),(390,'zh')))
            actions.extend((f'index-category-regression-{w}-{l}',lambda w=w,l=l:index_category_picker_paths(w,l)) for w,l in ((390,'en'),(320,'zh')))
    actions=[(name,action) for name,action in actions if not args.case or args.case==name]
    assert actions,'No matching case selected'
    report['expected_cases']=len(actions)
    for name,action in actions:
        before=report['contexts']
        try:
            action()
            result={'name':name,'result':'PASS'}
        except Exception:
            result={'name':name,'result':'FAIL','error':traceback.format_exc(limit=4)[:2400]}
        result['contexts']=report['contexts']-before
        report['cases'].append(result)
        print(json.dumps(result,ensure_ascii=False),flush=True)
        if result['result']=='FAIL' and not args.baseline:
            break
    browser.close()
server.shutdown();server.server_close()
report['complete']=len(report['cases'])==report['expected_cases']
report['pass']=report['complete'] and all(x['result']=='PASS' for x in report['cases']) and not report['page_errors']
report['baseline_header_observations_and_expected_focus_failures']=args.baseline
if not args.baseline and args.case_family=='all' and not args.case and report['pass']:
    try:
        previous=json.loads((args.root/'baseline-proof/browser-report.json').read_text())
        assert previous['complete'] and not previous['page_errors']
        assert all(row['result']=='PASS' for row in previous['cases'] if 'focus' not in row['name'])
        failed=[row for row in previous['cases'] if row['result']=='FAIL']
        assert len(failed)==2 and all('Reset hid its focused empty-state owner' in row['error'] for row in failed),failed
        fields=('width','language','theme','stale_fixture','entry','brain')
        before={tuple(row[k] for k in fields):row for row in previous['company_entry_header']}
        pairs=[]
        for row in report['company_entry_header']:
            old=before[tuple(row[k] for k in fields)]
            gain=old['geometry']['search']['top']-row['geometry']['search']['top']
            assert gain>=(64 if row['width']>820 else 80),(row,gain)
            pairs.append({**{k:row[k] for k in fields},'before_search_top':old['geometry']['search']['top'],'after_search_top':row['geometry']['search']['top'],'saved_px':gain})
        assert len(pairs)==44,len(pairs)
        report['matched_comparison']={'pass':True,'pairs':pairs,'min_saved_px':min(p['saved_px'] for p in pairs),'max_saved_px':max(p['saved_px'] for p in pairs)}
    except Exception:
        report['pass']=False
        report['matched_comparison']={'pass':False,'error':traceback.format_exc(limit=4)[:3000]}

(args.out/'browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'browser':report['browser'],'passed':sum(x['result']=='PASS' for x in report['cases']),'total':len(report['cases']),'contexts':report['contexts'],'page_errors':report['page_errors'],'report':str(args.out/'browser-report.json')},ensure_ascii=False),flush=True)
raise SystemExit(0 if report['pass'] else 1)
