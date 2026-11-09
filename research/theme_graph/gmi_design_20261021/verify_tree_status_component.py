"""Bounded GMI tree empty-search status proof using exact generated HTML, JS and CSS inputs.

This harness uses an anonymous Chrome context and blocks every external request.
It extracts committed main content; it does not exercise the shared shell, login,
public admission, live serving or release. It observes persistent status semantics and actual focus/visibility transitions. No screen-reader speech or operating-system clipboard claim is made.
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
parser.add_argument('--case-family',choices=('all','feedback','static'),default='all')
parser.add_argument('--case',default='')
args=parser.parse_args()
args.out=args.root/('baseline-proof' if args.baseline else 'candidate-proof')
args.out.mkdir(exist_ok=True)
source=args.root/('baseline' if args.baseline else 'candidate')
script=(source/'gmi.js').read_text()
style=(args.root/'templates/theme.css').read_text()+'\n'+(source/'gmi.css').read_text()
parts={}
for name in ('gmi.html',):
    soup=BeautifulSoup((source/name).read_text(),'html.parser')
    main=soup.select_one('main#main')
    assert main is not None
    extra=[]
    for selector in ('#gmi-topic-data','[data-gmi-announcement]','[data-browse-dialog]'):
        node=soup.select_one(selector)
        if node is not None and main not in node.parents:
            extra.append(str(node))
    parts[name]=str(main)+''.join(extra)
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

    def context(width=1440,theme='light',language='en',**kwargs):
        c=browser.new_context(viewport={'width':width,'height':1000 if width>800 else 844},device_scale_factor=1,**kwargs)
        report['contexts']+=1
        prefix='/case-'+str(report['contexts'])+'/'
        context_routes[c]=prefix
        for name,part in parts.items():
            documents[prefix+name]='<!doctype html><html data-lang="'+language+'" data-theme="'+theme+'"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+style+'</style></head><body class="page-macro gmi-page gmi-product">'+part+'<script>'+script+'</script></body></html>'
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
    names={'gmi_navigation_fit','tree_status_spacing','tree_status_feedback','tree_status_static'}
    definitions=sorted([n for n in ast.walk(parsed) if isinstance(n,ast.FunctionDef) and n.name in names],key=lambda n:n.lineno)
    assert {n.name for n in definitions}==names and len(definitions)==4
    exec(compile(ast.Module(body=definitions,type_ignores=[]),str(verifier),'exec'),globals())
    matrix=((1440,'en'),(390,'zh')) if args.baseline else tuple((w,l) for w in (1440,390,320) for l in ('en','zh'))
    actions=[]
    if args.case_family!='static':
        actions.extend((f'tree-status-{w}-{l}',lambda w=w,l=l:tree_status_feedback(w,l)) for w,l in matrix)
    if not args.baseline and args.case_family!='feedback':
        actions.extend((f'tree-status-static-{l}',lambda l=l:tree_status_static(l)) for l in ('en','zh'))
    for name,action in actions:
        if args.case and args.case!=name:
            continue
        before=report['contexts']
        try:
            action()
            result={'name':name,'result':'PASS'}
        except Exception:
            result={'name':name,'result':'FAIL','error':traceback.format_exc(limit=4)[-2400:]}
        result['contexts']=report['contexts']-before
        report['cases'].append(result)
        print(json.dumps(result,ensure_ascii=False),flush=True)
    browser.close()
server.shutdown();server.server_close()
report['pass']=all(x['result']=='PASS' for x in report['cases']) and not report['page_errors']
(args.out/'browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'browser':report['browser'],'passed':sum(x['result']=='PASS' for x in report['cases']),'total':len(report['cases']),'contexts':report['contexts'],'page_errors':report['page_errors'],'report':str(args.out/'browser-report.json')},ensure_ascii=False),flush=True)
raise SystemExit(0 if report['pass'] else 1)
