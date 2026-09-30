"""Controlled real-template proof for R13; no build main/collector/network call.
Uses the already-created Vector fixture context, existing assets and pure view.
The ephemeral loopback server lives only for this process and is shut down.
"""
from pathlib import Path
from copy import deepcopy
from contextlib import ExitStack
import ast
import hashlib
import http.server
import json
import shutil
import socketserver
import sys
import threading
import subprocess
from jinja2 import Environment,FileSystemLoader,ChainableUndefined
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from scripts.build_vector import _derivatives_flow_view
HERE=Path(__file__).resolve().parent
SITE=Path('/Volumes/Mastermind/research/crypto-vector-r2-20260926-sol-001/r13_actual')
OLD=Path('/Volumes/Mastermind/research/crypto-vector-r2-20260926-sol-001')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def render():
    src=OLD/'render_vector_fixture.py';tree=ast.parse(src.read_text())
    names={'decision','chart_contract','ctx'};functions={'axis','watch','complex_card'}
    keep=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets)]
    ns={};exec(compile(ast.Module(body=keep,type_ignores=[]),str(src),'exec'),ns)
    ctx=ns['ctx'];ctx['leverage']['funding_annual']=1234.5;ctx['leverage']['okx_taker_buy']=.987
    SITE.mkdir(parents=True,exist_ok=True)
    env=Environment(loader=FileSystemLoader(str(ROOT/'templates')),undefined=ChainableUndefined,autoescape=True)
    env.globals.update(td=lambda x:x,tr=lambda x:x)
    raw=dict(ok=True,display_only=True,causally_qualified=False,scope='OKX/BTC/CONTRACTS',asof='2026-01-09 08:00:00',
             evaluated_at='2026-01-09 09:00:00',n_hours=200,window_24h_complete=True,window_72h_complete=True,
             stale=False,gap_detected=False,flow_state='buy_dominant',buy_share_24h=.625,net_flow_24h_native=24.)
    scenarios={'current':{},'stale':{'stale':True,'evaluated_at':'2026-01-12 09:00:00'},
               'gap':{'n_hours':12,'window_24h_complete':False,'window_72h_complete':False,'gap_detected':True},
               'no_activity':{'flow_state':'no_activity','buy_share_24h':None,'net_flow_24h_native':0},
               'only_24h':{'n_hours':48,'window_72h_complete':False,'gap_detected':True},
               'zero_share':{'buy_share_24h':0.},'unavailable':None}
    expected={}
    for name,updates in scenarios.items():
        r={} if updates is None else {'context_legs':{'intraday_cvd':dict(raw,**updates)}}
        view=_derivatives_flow_view(r);expected[name]=view
        c=deepcopy(ctx);c['derivatives_flow']=view
        content=env.get_template('vector.html.j2').render(**c,C={})
        (SITE/('vector.html' if name=='current' else f'vector_{name}.html')).write_text(content)
    assets=['theme.css','illus.css','illus.js','theme.js','mm_brain.js','navigation-refresh.css','logo_config.js','stock-logos.js',
            'live_config.js','live.js','vector_timemachine.js','lightweight-charts-v5.js','vector_chart.js','account.js','terminal-overlay.css','terminal-overlay.js',
            'nav_market.js','product-nav-icons.css','terminal_overlay.js','favicon.svg']
    copied={};missing=[]
    for name in assets:
        candidates=[ROOT/'templates'/name,ROOT/'site'/name,OLD/'vector_actual_fixture'/name]
        path=next((p for p in candidates if p.exists()),None)
        if path is not None:shutil.copy2(path,SITE/name);copied[name]=sha(path)
        else:missing.append(name)
    # Immutable controlled chart data, not current prices or model outcomes.
    for name in ['vector_risk_strategy.json','vector_timeline.json']:
        shutil.copy2(OLD/'vector_actual_fixture'/name,SITE/name)
    for folder in ['fonts','assets']:
        p=OLD/'vector_actual_fixture'/folder
        if p.is_dir():shutil.copytree(p,SITE/folder,dirs_exist_ok=True)
    (SITE/'fonts').mkdir(exist_ok=True)
    for weight in [400,500,600,700,800,900]:
        name=f'fonts/Inter-{weight}.woff2';p=ROOT/'templates'/name
        if not p.is_file():raise RuntimeError('Canonical fixture font unavailable')
        shutil.copy2(p,SITE/name);copied[name]=sha(p)
    return expected,{'fixture_context_source':str(src),'context_source_sha256':sha(src),'copied_assets':copied,'missing_assets':missing}


def main():
    expected,evidence=render();screens=HERE/'reviewed';screens.mkdir(exist_ok=True)
    errors=[];rows=[];requests=[]
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):super().__init__(*a,directory=str(SITE),**kw)
        def log_message(self,*args):pass
    with socketserver.ThreadingTCPServer(('127.0.0.1',0),Handler) as server:
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_address[1]}'
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
                for name,view in expected.items():
                    route='vector.html' if name=='current' else f'vector_{name}.html'
                    for width,height in [(320,850),(390,844),(768,1024),(1440,1000)]:
                        for theme in ['dark','light']:
                            for lang in ['en','zh']:
                                page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
                                local_errors=[];fail=[];bad_status=[]
                                page.on('pageerror',lambda e:local_errors.append(str(e)))
                                page.on('requestfailed',lambda r:fail.append(r.url))
                                page.on('response',lambda r:bad_status.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
                                page.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base+'/') else route.abort())
                                page.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('lang','{lang}');")
                                response=page.goto(base+'/'+route,wait_until='networkidle',timeout=30000)
                                page.wait_for_timeout(100)
                                page.evaluate('()=>document.fonts.ready')
                                hero_geometry=page.locator('.hero-read').evaluate('''e=>({container:e.clientWidth,
                                  copyWidth:e.children[0].getBoundingClientRect().width,
                                  copyBottom:e.children[0].getBoundingClientRect().bottom,
                                  positionTop:e.children[1].getBoundingClientRect().top,
                                  stanceWidth:e.querySelector('.stance').getBoundingClientRect().width,
                                  columns:getComputedStyle(e).gridTemplateColumns})''')
                                if width<=780:
                                    assert hero_geometry['copyWidth']>=hero_geometry['container']-2,hero_geometry
                                    assert hero_geometry['positionTop']>=hero_geometry['copyBottom'],hero_geometry
                                font_status=page.evaluate('()=>({inter400:document.fonts.check("400 14px Inter"),inter700:document.fonts.check("700 14px Inter")})')
                                assert font_status['inter400'] and font_status['inter700'],font_status
                                desk=page.locator('#derivatives-desk');desk.locator(':scope > summary').click()
                                panel=page.locator('[data-flow-context]');panel.scroll_into_view_if_needed()
                                before=panel.inner_text();assert panel.get_attribute('data-flow-state')==view['state']
                                assert page.locator('[data-verdict]').count()==1
                                assert '60%' in page.locator('.hero').inner_text()
                                assert page.locator('#vec-risk-chart').count()==1
                                assert page.locator('[data-funding-qualification] .v').inner_text()=='—'
                                assert '1234.5' not in desk.inner_text() and '98.7%' not in desk.inner_text()
                                share=panel.locator('.flow-share-value').inner_text().replace('\n','')
                                if view['state']=='available':assert share==f"{view['buy_share_pct']:.1f}%",(name,share)
                                else:assert share=='—',(name,share)
                                summary=panel.locator('[data-flow-evidence] > summary');summary.focus();page.keyboard.press('Enter')
                                assert panel.locator('[data-flow-evidence]').evaluate('(e)=>e.open')
                                text=panel.inner_text()
                                phrase='Absolute units' if lang=='en' else '绝对单位'
                                assert phrase in text,(lang,text)
                                if view['observed_at']:assert view['observed_at'] in text
                                geometry=panel.evaluate('''e=>({pageOverflow:document.documentElement.scrollWidth>innerWidth+1,
                                  innerOverflow:[e,...e.querySelectorAll('*')].filter(x=>getComputedStyle(x).display!=='none'&&x.clientWidth>0&&x.scrollWidth>x.clientWidth+2).map(x=>x.className),
                                  proseMinimum:Math.min(...[...e.querySelectorAll('p')].filter(x=>x.offsetHeight).map(x=>parseFloat(getComputedStyle(x).fontSize)))})''')
                                touch=summary.bounding_box()['height'];assert touch>=44
                                assert not geometry['pageOverflow'] and not geometry['innerOverflow'],(name,width,lang,geometry)
                                assert geometry['proseMinimum']>=14 and not local_errors,(geometry,local_errors)
                                if (width==1440 and lang=='en' and theme=='dark') or (width==390 and lang=='zh' and theme=='light'):
                                    panel.screenshot(path=str(screens/f'{name}_{width}_{theme}_{lang}.png'))
                                rows.append({'scenario':name,'width':width,'theme':theme,'lang':lang,'http_status':response.status,
                                    'state':view['state'],'share':share,'keyboard_disclosure':True,'touch_height':touch,'geometry':geometry,
                                    'hero_geometry':hero_geometry,'font_status':font_status,'page_errors':local_errors})
                                requests.extend(fail);requests.extend(json.dumps(x,sort_keys=True) for x in bad_status)
                                page.close()
                    print('R13_BROWSER_SCENARIO',name,'16 cells verified',flush=True)
                browser.close()
        finally:server.shutdown();thread.join(timeout=2)
    result={'classification':'CONTROLLED_GENERATED_TEMPLATE_NOT_DEPLOYMENT_OR_LIVE_DATA','source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_sha256':{n:sha(ROOT/n) for n in ['scripts/build_vector.py','templates/vector.html.j2','engine/btc_intraday_cvd.py']},
        'fixture':evidence,'expected':expected,'cases':rows,'failed_or_unavailable_resources':sorted(set(requests)),
        'screenshots':{str(p.relative_to(ROOT)):sha(p) for p in screens.glob('*.png')},
        'limits':['Synthetic known values; no provider request, receipt store, forecast or model state changed.',
                  'Theme/source assets reused locally; unavailable and blocked remote resource URLs are recorded.',
                  'Render uses pure context/helper/Jinja only, never build_vector.main or its ledger writes.',
                  'Seven contract cases, not exhaustive nonscalar adapter fuzzing or independent reviewer approval.']}
    (HERE/'browser_proof.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('R13_BROWSER_PASS',len(rows),'cases')

if __name__=='__main__':main()
