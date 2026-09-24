"""Actual backdrop navigation plus explicitly synthetic missing/zero/transition cases."""
from pathlib import Path
import copy, functools, hashlib, http.server, json, pickle, re, subprocess, sys, threading
from playwright.sync_api import sync_playwright, expect
from jinja2 import Environment, FileSystemLoader
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import capture_page_evidence as capture
from engine import china_tier1, i18n
OUT = ROOT / 'mockups/evidence/china-backdrop-context-20260924'
OUT.mkdir(parents=True, exist_ok=True)
PAGE = ROOT / 'site/china.html'
DIGEST = hashlib.sha256(PAGE.read_bytes()).hexdigest()
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

def factory(**kw):
    manager = sync_playwright().start()
    browser = manager.chromium.launch(headless=True, executable_path=CHROME)
    return capture._PlaywrightDriver(manager, browser, kw.get('user_agent', capture.USER_AGENT),
        dict(kw.get('observer_config') or capture.DEFAULT_OBSERVER_CONFIG), kw.get('settle_ms', 1400))

if '--interactions-only' not in sys.argv:
    code = capture.main(['--site-dir', str(ROOT/'site'), '--routes', '/china.html',
        '--output-dir', str(OUT), '--manifest', str(OUT/'manifest.json'), '--smells', str(OUT/'smells.json'),
        '--viewports', 'desktop,mobile', '--themes', 'dark,light', '--locales', 'en,zh', '--max-pages', '1',
        '--force-state', 'backdrop-focus:focus([data-cn-driver-rail] a)',
        '--force-state', 'backdrop-hover:hover([data-cn-driver-rail] a)'], driver_factory=factory)
    assert code == 0
meta = json.loads((OUT/'manifest.json').read_text())['pages'][0]
assert len(meta['states']) == 24 and all(s['captured'] for s in meta['states'])
assert not meta['console_errors'] and not meta['failed_responses']
assert all(not v['horizontal_overflow'] for v in meta['metrics']['by_viewport'].values())
# This pickle is the debug output of this same local builder invocation only.
with (ROOT/'data/_dev_china_vm.pkl').open('rb') as handle:
    original = pickle.load(handle)
env = Environment(loader=FileSystemLoader(str(ROOT/'templates')), autoescape=False)
env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t, t_pctile=i18n.t_pctile,
    **{k:getattr(china_tier1,k) for k in ('posture_lane','posture_tone','reason_faces',
                                      'hero_clause','connect_flow_face','regime_watch_face')})
variants = {}
for kind, net, pending in [('missing', None, None), ('zero', 0, 'Q2'), ('selling', -123.4, None)]:
    vm = copy.deepcopy(original)
    vm['internals']['southbound'] = {'net':net, 'cum_20d':None, 'pos_days_20':None, 'hold_mktcap':None}
    vm['latest'].update(quad='Q4', pending_quad=pending, pending_days=2 if pending else 0)
    variants[kind] = env.get_template('china.html.j2').render(**dict(vm, mode='macro'))
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass
server = http.server.ThreadingHTTPServer(('127.0.0.1',0), functools.partial(Quiet,directory=str(ROOT/'site')))
thread = threading.Thread(target=server.serve_forever,daemon=True)
thread.start()
cases=[]
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=CHROME)
        try:
            for width,height in ((1440,900),(390,844)):
                for theme in ('dark','light'):
                    for lang in ('en','zh'):
                        ctx=browser.new_context(viewport={'width':width,'height':height},
                            **({'is_mobile':True,'has_touch':True} if width==390 else {}))
                        try:
                            ctx.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('lang','{lang}');")
                            ctx.route('**/live/china_risk_state.json*',lambda route:route.fulfill(json=None))
                            page=ctx.new_page();errors=[]
                            page.on('pageerror',lambda error:errors.append(str(error)))
                            page.goto(f'http://127.0.0.1:{server.server_port}/china.html',wait_until='networkidle')
                            rail=page.locator('[data-cn-driver-rail]')
                            expect(rail.locator('a')).to_have_count(4)
                            expected=('Policy stance','Hong Kong flows','Radar state','Property') if lang=='en' else ('政策立场','港股资金','雷达状态','房地产')
                            for index,target in enumerate(('policy','flows','risk','property')):
                                link=rail.locator('a').nth(index)
                                assert expected[index] in link.inner_text()
                                expect(link.locator('.l-'+lang).first).to_be_visible()
                                expect(link.locator('.l-'+('zh' if lang=='en' else 'en')).first).to_be_hidden()
                                link.tap() if width==390 else link.click()
                                dialog=page.locator('#cnx-dlg-'+target)
                                expect(dialog).to_be_visible()
                                page.keyboard.press('Escape');expect(dialog).to_be_hidden()
                            if width==390:
                                assert page.evaluate("navigator.maxTouchPoints>0 && matchMedia('(hover:none)').matches")
                            assert not page.evaluate('document.documentElement.scrollWidth>document.documentElement.clientWidth')
                            if width==1440:
                                rail.locator('a').first.focus();page.keyboard.press('Enter')
                                expect(page.locator('#cnx-dlg-policy')).to_be_visible();page.keyboard.press('Escape')
                            synthetic=[]
                            for kind,html in variants.items():
                                page.route('**/china.html',lambda route:route.fulfill(status=200,content_type='text/html',body=html))
                                page.reload(wait_until='networkidle')
                                flow=page.locator('[data-cn-driver-rail] a[href="#cnx-dlg-flows"]')
                                expected={'missing':('Unavailable','暂不可用'),'zero':('Flat net flow','净流入为零'),'selling':('Net selling','净卖出')}
                                assert expected[kind][lang=='zh'] in flow.inner_text()
                                flow.tap() if width==390 else flow.click()
                                dialog=page.locator('#cnx-dlg-flows');expect(dialog).to_be_visible()
                                assert not re.search(r'\b(?:None|NaN|Infinity)\b', dialog.inner_text())
                                page.keyboard.press('Escape');expect(dialog).to_be_hidden()
                                chip=page.locator('[data-cn-pending-regime]')
                                expect(chip).to_have_count(1 if kind=='zero' else 0)
                                if kind=='zero':
                                    expect(chip).to_contain_text('Transition pending' if lang=='en' else '周期转变待确认')
                                    assert not chip.evaluate('(el)=>el.scrollWidth>el.clientWidth')
                                assert not page.evaluate('document.documentElement.scrollWidth>document.documentElement.clientWidth')
                                if width==390:
                                    assert page.evaluate("navigator.maxTouchPoints>0 && matchMedia('(hover:none)').matches")
                                synthetic.append(kind);page.unroute('**/china.html')
                            assert not errors,errors
                            cases.append(dict(width=width,theme=theme,locale=lang,deep_links=4,
                                keyboard_enter=width==1440,synthetic=synthetic,touch_preserved=True))
                        finally:
                            ctx.close()
        finally:
            browser.close()
finally:
    server.shutdown();server.server_close();thread.join(timeout=5)
assert not thread.is_alive()
assert hashlib.sha256(PAGE.read_bytes()).hexdigest()==DIGEST
receipt={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'page_sha256':DIGEST,'cases':cases,'static_captures':24,'servers_closed':True,
    'synthetic_states':'missing net, finite zero and selling; pending regime is not confirmed',
    'fresh_collection':False,'production':False}
(OUT/'interactions.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'captures':24,'actual_journeys':len(cases)*4,'synthetic_cases':len(cases)*3,
    'page_sha256':DIGEST,'production':False}))
