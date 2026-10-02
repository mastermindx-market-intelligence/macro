"""R15 real Crypto-builder view proof with synthetic decisions; no live requests.
Writes only controlled fixture files and new evidence, not production site/data.
"""
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
import copy,hashlib,http.server,json,shutil,socketserver,subprocess,sys,threading
from jinja2 import FileSystemLoader
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from lib import config,store
from scripts import build_crypto
HERE=Path(__file__).resolve().parent
SITE=Path('/Volumes/Mastermind/research/crypto-vector-r2-20260926-sol-001/r15_actual')
OLD=Path('/Volumes/Mastermind/research/crypto-vector-r2-20260926-sol-001')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def render():
    SITE.mkdir(parents=True,exist_ok=True)
    original_read=store.read;sig=original_read('vector','signals')
    if sig is None or sig.empty:raise RuntimeError('Stored controlled baseline is absent')
    asof=str(sig.index[-1].date());prev=str(sig.index[-2].date())
    projection={'schema':'btc.decision/v1','status':'ok','as_of':asof,'integrity_ok':True,
                'final_exposure_pct':60,'errors':[],'authority_source':'btc.decision/v1.final.exposure_pct'}
    states={'known':projection,'zero':dict(projection,final_exposure_pct=0),
            'unavailable':dict(projection,status='unavailable',integrity_ok=False,final_exposure_pct=None),
            'stale':dict(projection,as_of=prev),'breakdown':projection,'history_missing':projection,'combined':projection}
    market=build_crypto.build_market_state();market['heat']['funding']['value']=9876.5
    expected={};asset_hashes={};missing=[]
    overlay=SITE/'overlay';overlay.mkdir(exist_ok=True)
    shutil.copy2(HERE/'combined_crypto.html.j2',overlay/'crypto.html.j2')
    for name,pr in states.items():
        work=SITE/('_work_'+name);work.mkdir(exist_ok=True)
        decision=copy.deepcopy(pr);source=sig.copy(deep=True);mk=copy.deepcopy(market)
        if name=='breakdown':source.loc[source.index[-1],'close']=float('nan')
        if name=='history_missing':mk['history']={'dates':[],'vals':[]};mk['regimes']=[]
        (work/'crypto_cockpit.json').write_text(json.dumps({'schema':'crypto.cockpit/v1','display_only':True,'as_of':asof,
            'decision':decision,'hero':{'stance_en':'Fixture only','stance_zh':'仅为示例','exposure_pct':decision['final_exposure_pct']},'axes':[]},ensure_ascii=False))
        def read(g,n,*a,**kw):return source.copy(deep=True) if (g,n)==('vector','signals') else original_read(g,n,*a,**kw)
        with ExitStack() as stack:
            stack.enter_context(patch.object(store,'read',side_effect=read))
            stack.enter_context(patch.object(build_crypto,'build_market_state',return_value=mk))
            if name=='combined':stack.enter_context(patch.object(build_crypto,'FileSystemLoader',side_effect=lambda _:FileSystemLoader([str(overlay),str(ROOT/'templates')])) )
            output=build_crypto.build(work)
        filename='crypto.html' if name=='known' else f'crypto_{name}.html'
        shutil.copy2(output,SITE/filename)
        expected[name]={'filename':filename,'state':'unavailable' if name in ['unavailable','stale'] else 'breakdown-unavailable' if name=='breakdown' else 'available',
                        'budget':None if name in ['unavailable','stale'] else decision['final_exposure_pct'],
                        'decision_date':decision['as_of'],'market_date':market['as_of'],
                        'history':name!='history_missing','html_sha256':sha(SITE/filename)}
    assets=['theme.css','illus.css','illus.js','theme.js','mm_brain.js','navigation-refresh.css','logo_config.js','stock-logos.js','live_config.js','live.js',
            'account.js','terminal-overlay.css','terminal-overlay.js','nav_market.js','product-nav-icons.css','terminal_overlay.js','favicon.svg']
    for name in assets:
        options=[ROOT/'templates'/name,ROOT/'site'/name,OLD/'vector_actual_fixture'/name]
        source=next((p for p in options if p.exists()),None)
        if source:shutil.copy2(source,SITE/name);asset_hashes[name]=sha(source)
        else:missing.append(name)
    for folder in ['fonts','assets']:
        source=OLD/'vector_actual_fixture'/folder
        if source.is_dir():shutil.copytree(source,SITE/folder,dirs_exist_ok=True)
    (SITE/'fonts').mkdir(exist_ok=True)
    for weight in [400,500,600,700,800,900]:
        p=ROOT/f'templates/fonts/Inter-{weight}.woff2'
        if not p.is_file():raise RuntimeError('Canonical Inter unavailable')
        shutil.copy2(p,SITE/'fonts'/p.name);asset_hashes['fonts/'+p.name]=sha(p)
    return expected,{'assets':asset_hashes,'missing_assets':missing,'kind':'Actual builder/stored baseline with controlled decision and funding sentinels; no market fetch.'}


def main():
    smoke='--smoke' in sys.argv
    prior=json.loads((HERE.parent/'r12/pipeline_proof.json').read_text());data=Path(config.data_dir())
    def unchanged():
        for k,h in prior['inputs'].items():assert (sha(data/k) if (data/k).exists() else None)==h,k
        for k,h in prior['gates'].items():assert sha(data/k)==h,k
        for k,h in prior['prior_evidence'].items():assert sha(ROOT/k)==h,k
    unchanged();expected,assets=render();shots=HERE/('smoke' if smoke else 'reviewed');shots.mkdir(exist_ok=True)
    cases=[];failures=[];resources=[]
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):super().__init__(*a,directory=str(SITE),**kw)
        def log_message(self,*a):pass
    with socketserver.ThreadingTCPServer(('127.0.0.1',0),Handler) as server:
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_address[1]}'
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=True)
                matrix=[(1440,1000,'dark','en'),(390,844,'light','zh'),(320,850,'dark','en')] if smoke else [(w,h,t,l) for w,h in [(320,850),(390,844),(768,1024),(1440,1000)] for t in ['dark','light'] for l in ['en','zh']]
                for name,e in expected.items():
                    if smoke and name!='known':continue
                    for width,height,theme,lang in matrix:
                        page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1);errors=[];bad=[]
                        page.on('pageerror',lambda x:errors.append(str(x)))
                        page.on('requestfailed',lambda x:bad.append(x.url))
                        page.on('response',lambda x:bad.append(f'{x.status} {x.url}') if x.status>=400 else None)
                        page.route('**/*',lambda route:route.continue_() if route.request.url.startswith(base+'/') else route.abort())
                        page.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('lang','{lang}');")
                        response=page.goto(base+'/'+e['filename'],wait_until='networkidle',timeout=30000);page.wait_for_timeout(150)
                        page.evaluate('()=>document.fonts.ready');panel=page.locator('#crypto-overview');budget=panel.locator('[data-desk-budget-state]')
                        readings={'budget_state':budget.get_attribute('data-desk-budget-state'),'budget_value':budget.locator('[data-desk-budget-value]').inner_text(),
                                  'decision_date':budget.locator('[data-desk-decision-date]').inner_text(),'history_state':panel.locator('[data-market-history-state]').get_attribute('data-market-history-state')}
                        assert readings['budget_state']==e['state']
                        assert readings['budget_value']==('—' if e['budget'] is None else f"{e['budget']}%")
                        assert readings['decision_date']==e['decision_date']
                        assert readings['history_state']==('available' if e['history'] else 'unavailable')
                        assert page.locator('[data-shelf]').count()==8 and page.locator('h1').count()==1
                        assert page.locator('#allocation').get_attribute('data-allocation-state')==e['state']
                        assert page.locator('[data-crypto-funding-state] .reading').inner_text()=='—'
                        assert '9876.5' not in page.locator('#leverage-heat').inner_text()
                        assert budget.locator('[data-desk-cash-value]').count()==(0 if e['budget'] is None else 1)
                        if e['budget'] is not None:assert budget.locator('[data-desk-cash-value]').inner_text()==f"{100-e['budget']}%"
                        chart_seen=None
                        if e['history']:
                            figure=panel.locator('.desk-tape .ilx');figure.scroll_into_view_if_needed()
                            page.wait_for_function("document.querySelector('#crypto-overview .desk-tape .ilx').classList.contains('ilx-in')")
                            page.wait_for_timeout(1200)
                            chart_seen=figure.evaluate("e=>({revealed:e.classList.contains('ilx-in'),pathCount:e.querySelectorAll('svg path').length,width:e.getBoundingClientRect().width})")
                            assert chart_seen['pathCount']>0 and chart_seen['width']>100
                        original=panel.inner_text()
                        assert ('Recorded model budget' if lang=='en' else '已记录的模型预算') in original
                        assert ('Recorded model budget' if lang=='zh' else '已记录的模型预算') not in original
                        geom=panel.evaluate('''e=>({pageOverflow:document.documentElement.scrollWidth>innerWidth+1,
                           innerOverflow:[e,...e.querySelectorAll('*')].filter(x=>!(x instanceof SVGElement)&&getComputedStyle(x).display!=='none'&&x.clientWidth>0&&x.scrollWidth>x.clientWidth+2).map(x=>({tag:x.tagName,cls:String(x.className),width:x.clientWidth,scroll:x.scrollWidth})),
                           proseMin:Math.min(...[...e.querySelectorAll('p')].filter(x=>x.offsetHeight).map(x=>parseFloat(getComputedStyle(x).fontSize))),
                           targetWidths:[...e.querySelectorAll('.desk-market-panel,.desk-budget')].map(x=>x.getBoundingClientRect().width)})''')
                        link_heights=[panel.locator('a').nth(i).bounding_box()['height'] for i in range(panel.locator('a').count())]
                        issues=[]
                        if geom['innerOverflow']:issues.append('INNER_OVERFLOW')
                        if geom['pageOverflow']:issues.append('PAGE_OVERFLOW')
                        if min(link_heights)<44:issues.append('SMALL_LINK')
                        if errors:issues.append('JS_ERROR')
                        if geom['proseMin']<12.5:issues.append('SMALL_PROSE')
                        if smoke or (width==1440 and theme=='dark' and lang=='en') or (width==390 and theme=='light' and lang=='zh'):
                            panel.screenshot(path=str(shots/f'{name}_{width}_{theme}_{lang}.png'),animations='disabled')
                        assistant_check=None
                        if name in ['known','combined']:
                            entry=panel.locator('[data-crypto-brain]')
                            assert entry.is_visible()
                            for selector in ['#mmb-boot','#mmb-launch']:
                                assert not page.locator(selector).is_visible()
                            entry.focus();page.keyboard.press('Enter')
                            page.wait_for_selector('#mmb-panel.open',state='visible',timeout=6000)
                            page.wait_for_timeout(350)
                            assert page.evaluate("document.querySelector('#mmb-panel').contains(document.activeElement)")
                            assert not page.locator('#mmb-launch').is_visible()
                            page.keyboard.press('Escape');page.wait_for_timeout(150)
                            print('CLOSE_OBSERVATION',page.locator('#mmb-panel').evaluate("e=>({className:e.className,visibility:getComputedStyle(e).visibility,opacity:getComputedStyle(e).opacity,transition:getComputedStyle(e).transition})"),flush=True)
                            page.wait_for_selector('#mmb-panel',state='hidden',timeout=2000)
                            assert entry.evaluate('e=>document.activeElement===e')
                            assistant_check={'existing_owner_opened':True,'keyboard_focus_returned':True,'floating_hidden':True}
                        links=[]
                        for target in ['money-flows','leverage-heat','allocation']:
                            el=panel.locator(f'.desk-nav a[href="#{target}"]');el.focus();page.keyboard.press('Enter');page.wait_for_timeout(60)
                            assert page.url.endswith('#'+target);assert page.locator('#'+target).count()==1
                            links.append(target)
                        panel.locator('.desk-chart-foot a').click();summary=page.locator('#universe-snapshot .universe-coverage > summary');summary.focus();page.keyboard.press('Enter')
                        assert page.locator('#universe-snapshot .universe-coverage').evaluate('e=>e.open')
                        if name=='combined':assert page.locator('#market-board [role="table"]').count()==1 and 'Daily snapshot' in panel.text_content()
                        cases.append({'scenario':name,'width':width,'theme':theme,'lang':lang,'status':response.status,'readings':readings,
                                      'geometry':geom,'link_min_height':min(link_heights),'keyboard_jumps':links,'source_disclosure':True,'chart_seen':chart_seen,'assistant_check':assistant_check,'page_errors':errors,'issues':issues})
                        if issues:failures.append(cases[-1])
                        resources.extend(bad);page.close()
                    print('R15_BROWSER_SCENARIO',name,len(matrix),'cells',flush=True)
                browser.close()
        finally:server.shutdown();thread.join(timeout=2)
    unchanged()
    result={'classification':'CONTROLLED_ACTUAL_BUILD_NOT_LIVE_MARKET_OR_DEPLOYMENT','source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'sources':{k:sha(ROOT/k) for k in ['templates/crypto.html.j2','scripts/build_crypto.py','templates/_crypto_house_style.html.j2','tests/test_crypto_wave2.py']},
            'inputs':prior['inputs'],'gates':prior['gates'],'prior_evidence':prior['prior_evidence'],'unchanged':True,'expected':expected,'assets':assets,'cases':cases,'failures':failures,
            'resources':sorted(set(resources)),'screenshots':{str(p.relative_to(ROOT)):sha(p) for p in shots.glob('*.png')},
            'limits':['Stored observations and synthetic model-budget/funding sentinel; not current market recommendations.',
                      'All HTTP outside ephemeral loopback server aborted; no collector invocation or external asset fetch.',
                      'Paper remains unchanged behind exact schema gate; current R3 visual was inspected, not applied.',
                      'Same-session tests/visual review, not participant comprehension or independent review.']}
    (HERE/('smoke.json' if smoke else 'browser_proof.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('R15_BROWSER_RESULT',len(cases),'cases',len(failures),'failures')
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
