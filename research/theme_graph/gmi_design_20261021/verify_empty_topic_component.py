"""Empty-topic clarity and the existing company-evidence round trip.

Baseline cases collect layout measurements, not proposed-copy acceptance.
Generated-main fixtures retain production assets and public payload. Server-macro
no-JS fixtures, when present, are explicitly controlled and add no product route.
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
parser.add_argument('--case',default='')
parser.add_argument('--out',type=Path)
args=parser.parse_args()
args.site=args.root/('baseline' if args.baseline else 'candidate')
args.out=args.out or args.root/('baseline-proof' if args.baseline else 'candidate-proof')
args.out.mkdir(exist_ok=True)
source=args.site
script=(source/'gmi.js').read_text()
style=(args.root/'templates/theme.css').read_text()+'\n'+(source/'gmi.css').read_text()
parts={}
for name in ('gmi.html','gmi-index.html','gmi-companies.html','gmi-issuer-mu.html','gmi-coverage.html','gmi-relationships.html','gmi-states.html'):
    soup=BeautifulSoup((source/name).read_text(),'html.parser');main=soup.select_one('main#main');assert main is not None
    extra=[]
    for selector in ('#gmi-topic-data','[data-gmi-announcement]','[data-browse-dialog]'):
        node=soup.select_one(selector)
        if node is not None and main not in node.parents:extra.append(str(node))
    parts[name]=str(main)+''.join(extra)

# A controlled production-macro component fixture; not a published GMI route.
macro_path=args.root/('server-baseline' if args.baseline else 'server-candidate')/'empty-answer.html'
macro_html=macro_path.read_text() if macro_path.exists() else ''
if macro_html:
    parts['gmi-empty-macro.html']='<main id="main" style="padding:16px"><section class="gmi-topic-answer" data-topic-answer aria-labelledby="gmi-topic-title">'+macro_html+'</section></main>'

report={'generated_at':datetime.now(timezone.utc).isoformat(),'baseline':args.baseline,'scope':__doc__.strip(),
        'script_sha256':hashlib.sha256(script.encode()).hexdigest(),
        'gmi_css_sha256':hashlib.sha256((source/'gmi.css').read_bytes()).hexdigest(),
        'verifier_sha256':hashlib.sha256((args.root/'verify_product_browser.py').read_bytes()).hexdigest(),
        'inputs':json.loads((args.root/'input-bindings.json').read_text()),
        'cases':[],'contexts':0,'screenshots':[],'page_errors':[]}
documents={}
class Fixture(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body=documents.get(urlsplit(self.path).path)
        if body is None:self.send_error(404);return
        payload=body.encode()
        self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
    def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Fixture)
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}'
context_routes={}
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=args.executable,headless=True)
    report['browser']=browser.version
    def context(width=1440,theme='light',language='en',**kwargs):
        c=browser.new_context(viewport={'width':width,'height':1000 if width>800 else 844},device_scale_factor=1,**kwargs)
        report['contexts']+=1;prefix='/case-'+str(report['contexts'])+'/'
        context_routes[c]=prefix
        for name,part in parts.items():
            documents[prefix+name]='<!doctype html><html data-lang="'+language+'" data-theme="'+theme+'"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+style+'</style></head><body class="page-macro gmi-page gmi-product">'+part+'<script>'+script+'</script></body></html>'
            documents['/'+name]=documents[prefix+name]
        def serve(route):
            if not route.request.url.startswith(base+'/'):return route.abort()
            route.continue_()
        c.route('**/*',serve)
        c.on('page',lambda p:p.on('pageerror',lambda e:report['page_errors'].append(str(e))))
        return c
    def page_for(c,route='gmi.html'):
        p=c.new_page();p.goto(base+context_routes[c]+route,wait_until='networkidle');return p
    verifier=args.root/'verify_product_browser.py';parsed=ast.parse(verifier.read_text())
    names={'empty_topic_snapshot','empty_topic_workflow','topic_description_paths'}
    definitions=[n for n in ast.walk(parsed) if isinstance(n,ast.FunctionDef) and n.name in names and n.col_offset==4]
    assert {n.name for n in definitions}==names and len(definitions)==len(names)
    exec(compile(ast.Module(body=definitions,type_ignores=[]),str(verifier),'exec'),globals())

    def empty_server_static(width,language):
        assert macro_html,'Production macro fixture is missing; run verify_empty_topic_render.py first'
        with context(width,'dark' if language=='en' else 'light',language,java_script_enabled=False) as c:
            p=page_for(c,'gmi-empty-macro.html')
            public=json.loads(BeautifulSoup((source/'gmi.html').read_text(),'html.parser').select_one('#gmi-topic-data').get_text())
            topic=next(t for t in public['topics'] if t['id']=='theme:conventional_dram');parent=public['categories'][topic['parent']]
            group=('Theme group: '+parent['en']) if language=='en' else ('所属主题组：'+parent['zh'])
            body='No reviewed company connections are published here. This does not mean no companies participate.' if language=='en' else '此处暂无经审核并发布的公司关联，不代表没有公司参与该主题。'
            label='Browse company evidence' if language=='en' else '浏览公司证据'
            empty=p.locator('.gmi-topic-empty');action=empty.locator('a')
            assert p.locator('[data-topic-description]').inner_text().strip()==group
            expect(empty.locator(':scope > p')).to_have_count(1)
            assert empty.locator(':scope > p').inner_text().strip()==body
            expect(empty.locator('.gmi-eyebrow,.gmi-empty-symbol')).to_have_count(0)
            assert action.inner_text().strip()==label and action.get_attribute('href')=='gmi-companies.html'
            assert action.bounding_box()['height']>=44
            expect(p.locator('[data-topic-coverage]')).not_to_be_visible()
            expect(p.locator('.gmi-topic-context .gmi-note')).to_be_visible()
            expect(p.locator('.gmi-topic-receipt summary')).to_be_visible()
            assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
            report.setdefault('empty_server_static',[]).append({'width':width,'language':language,'scope':'Production macro component with scripts disabled; no new served route or no-JS deep-link claim.',
                'macro_sha256':hashlib.sha256(macro_html.encode()).hexdigest(),'description':group,'body':body,'action':label,'native_href':action.get_attribute('href'),'action_height':action.bounding_box()['height']})
            action.click()
            assert urlsplit(p.url).path.endswith('gmi-companies.html') and 'gmi_return' not in parse_qs(urlsplit(p.url).fragment)
            expect(p.locator('[data-company-card]')).to_have_count(1)

    actions=[]
    dimensions=((390,'en'),(320,'zh'),(320,'en'),(390,'zh')) if args.baseline else ((1440,'en'),(1440,'zh'),(390,'en'),(320,'zh'),(320,'en'),(390,'zh'))
    for width,language in dimensions:
        actions.append((f'empty-topic-{width}-{language}',lambda w=width,l=language:empty_topic_workflow(w,l,args.baseline)))
    if not args.baseline:
        for width,language in ((390,'en'),(320,'zh')):
            actions.append((f'empty-topic-identity-{width}-{language}',lambda w=width,l=language:topic_description_paths(w,l)))
    if not args.baseline:
        for width,language in ((390,'en'),(320,'zh')):
            actions.append((f'empty-topic-server-static-{width}-{language}',lambda w=width,l=language:empty_server_static(w,l)))
    actions=[(name,action) for name,action in actions if not args.case or args.case==name];assert actions,'No matching case selected'
    report['expected_cases']=len(actions)
    for name,action in actions:
        before=report['contexts']
        try:action();result={'name':name,'result':'PASS'}
        except Exception:result={'name':name,'result':'FAIL','error':traceback.format_exc(limit=5)[:3500]}
        result['contexts']=report['contexts']-before;report['cases'].append(result);print(json.dumps(result,ensure_ascii=False),flush=True)
        if result['result']=='FAIL' and not args.baseline:break
    browser.close()
server.shutdown();server.server_close()
report['complete']=len(report['cases'])==report['expected_cases']
report['pass']=report['complete'] and all(x['result']=='PASS' for x in report['cases']) and not report['page_errors']
(args.out/'browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'browser':report['browser'],'passed':sum(x['result']=='PASS' for x in report['cases']),'total':len(report['cases']),'expected_cases':report['expected_cases'],'contexts':report['contexts'],'page_errors':report['page_errors'],'report':str(args.out/'browser-report.json')},ensure_ascii=False),flush=True)
raise SystemExit(0 if report['pass'] else 1)
