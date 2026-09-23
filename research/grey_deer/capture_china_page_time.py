"""Local page-time proof; synthetic intraday responses are separate from stored-page captures."""
from pathlib import Path
import functools, hashlib, http.server, json, subprocess, sys, threading
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts import capture_page_evidence as capture
OUT=ROOT/'mockups/evidence/china-page-time-20260923'
OUT.mkdir(parents=True,exist_ok=True)
PAGE=ROOT/'site/china.html'
BEFORE=hashlib.sha256(PAGE.read_bytes()).hexdigest()
CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
def factory(**kw):
    manager=sync_playwright().start()
    browser=manager.chromium.launch(headless=True,executable_path=CHROME)
    return capture._PlaywrightDriver(manager,browser,kw.get('user_agent',capture.USER_AGENT),
        dict(kw.get('observer_config') or capture.DEFAULT_OBSERVER_CONFIG),kw.get('settle_ms',1400))
code=capture.main(['--site-dir',str(ROOT/'site'),'--routes','/china.html',
    '--output-dir',str(OUT),'--manifest',str(OUT/'manifest.json'),'--smells',str(OUT/'smells.json'),
    '--viewports','desktop,mobile','--themes','dark,light','--locales','en,zh','--max-pages','1'],driver_factory=factory)
assert code==0
meta=json.loads((OUT/'manifest.json').read_text())['pages'][0]
assert len(meta['states'])==8 and all(s['captured'] for s in meta['states'])
assert not meta['console_errors'] and not meta['failed_responses']
assert all(not x['horizontal_overflow'] for x in meta['metrics']['by_viewport'].values())
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'site')))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
cases=[]
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=CHROME)
        try:
            for width,height in [(1440,900),(390,844)]:
                for theme in ('dark','light'):
                    for lang in ('en','zh'):
                        ctx=browser.new_context(viewport={'width':width,'height':height},
                            **({'is_mobile':True,'has_touch':True} if width==390 else {}))
                        try:
                            ctx.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('lang','{lang}');")
                            feed={'value':None}
                            ctx.route('**/live/china_risk_state.json*',lambda route:route.fulfill(json=feed['value']))
                            page=ctx.new_page(); errors=[]
                            page.on('pageerror',lambda e:errors.append(str(e)))
                            page.goto(f'http://127.0.0.1:{server.server_port}/china.html',wait_until='networkidle')
                            kind=page.locator('#ms-snapshot-kind'); stamp=page.locator('#ms-date')
                            baseline=stamp.get_attribute('data-assessment-asof')
                            assert baseline=='2026-09-21'
                            expect(kind).to_contain_text('Saved assessment' if lang=='en' else '已保存评估')
                            assert 'LIVE' not in page.locator('#ms-live-pill').inner_text()
                            health=page.locator('details.cnx-dh'); summary=health.locator('summary')
                            if width==390: assert page.evaluate("matchMedia('(hover:none)').matches && navigator.maxTouchPoints>0")
                            summary.tap() if width==390 else summary.click()
                            assert health.get_attribute('open') is not None
                            assert health.locator('.cnx-dh-row').count()==7
                            assert 'feeds fresh' not in health.inner_text() and '数据新鲜' not in health.inner_text()
                            expect(health).to_contain_text('does not certify' if lang=='en' else '不代表')
                            summary.tap() if width==390 else summary.click()
                            assert health.get_attribute('open') is None
                            if width==390: assert page.evaluate("matchMedia('(hover:none)').matches && navigator.maxTouchPoints>0")
                            scenarios=[]
                            for label,realtime in [('delayed',False),('marked_realtime',True),('unverified',None)]:
                                feed['value']={'built':'2026-09-23T13:45:00Z','nightly_asof':baseline,
                                    'live_active':True,'realtime':realtime,'display':{'verdict':'RISK_OFF',
                                    'score':33,'label_en':'Risk-off','label_zh':'避险'},'live':{},'nightly':{}}
                                page.reload(wait_until='networkidle')
                                expect(kind).to_contain_text('Intraday snapshot' if lang=='en' else '盘中快照')
                                expect(stamp).to_contain_text('2026-09-23 13:45 UTC')
                                assert stamp.get_attribute('data-assessment-asof')==baseline
                                assert 'on' not in page.locator('#ms-live-pill').get_attribute('class').split()
                                expect(page.locator('#mx5-score-numeral')).to_have_text('33')
                                text=stamp.inner_text()
                                expected={'delayed':('Quotes delayed','报价延迟'),
                                    'marked_realtime':('Quote feed marked real-time','报价源标为实时'),
                                    'unverified':('Quote timing unverified','报价时间未核实')}
                                assert expected[label][lang=='zh'] in text
                                scenarios.append(label)
                            feed['value']['built']='2026-09-18T13:45:00Z'
                            page.reload(wait_until='networkidle')
                            expect(kind).to_contain_text('Saved assessment' if lang=='en' else '已保存评估')
                            assert stamp.get_attribute('data-assessment-asof')==baseline
                            assert page.locator('#mx5-score-numeral').inner_text()!='33'
                            assert not page.evaluate('document.documentElement.scrollWidth>document.documentElement.clientWidth')
                            assert not errors, errors
                            cases.append({'width':width,'theme':theme,'locale':lang,'source_rows':7,
                                'health_open_close':True,'snapshot_cases':scenarios,'older_feed_rejected':True})
                            # Observation follows every assertion; screenshots can alter touch emulation.
                            if (width,theme,lang) in [(1440,'dark','en'),(390,'light','zh')]:
                                summary.tap() if width==390 else summary.click()
                                assert health.get_attribute('open') is not None
                                health.screenshot(path=str(OUT/f'sources-{width}-{theme}-{lang}.png'))
                        finally: ctx.close()
        finally: browser.close()
finally:
    server.shutdown();server.server_close();thread.join(timeout=5)
assert not thread.is_alive()
assert hashlib.sha256(PAGE.read_bytes()).hexdigest()==BEFORE
receipt={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'page_sha256':BEFORE,'static_captures':8,'cases':cases,'local_servers_closed':True,
    'intraday_responses':'explicit synthetic fixtures; no live producer acceptance',
    'fresh_collection':False,'production':False,'event_calendar_changed':False}
(OUT/'interactions.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'static_captures':8,'health_journeys':len(cases),'intraday_scenarios':len(cases)*4,
                  'page_sha256':BEFORE,'production':False}))
