"""Stored-input clock-panel proof only; not Lens, production or forecast acceptance."""
from pathlib import Path
import functools, hashlib, http.server, json, subprocess, sys, threading
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import capture_page_evidence as capture
OUT = ROOT / 'mockups/evidence/china-participation-clock-20260923'
OUT.mkdir(parents=True, exist_ok=True)
PROOF = json.loads(Path(sys.argv[1]).read_text())
PAGE = ROOT / 'site/china.html'
BEFORE = hashlib.sha256(PAGE.read_bytes()).hexdigest()
assert BEFORE == PROOF['page_sha256']
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

def driver_factory(**kwargs):
    manager = sync_playwright().start()
    browser = manager.chromium.launch(headless=True, executable_path=CHROME)
    return capture._PlaywrightDriver(manager, browser,
        kwargs.get('user_agent', capture.USER_AGENT),
        dict(kwargs.get('observer_config') or capture.DEFAULT_OBSERVER_CONFIG),
        kwargs.get('settle_ms', 1400))

code = capture.main(['--site-dir', str(ROOT/'site'), '--routes', '/china.html',
    '--output-dir', str(OUT), '--manifest', str(OUT/'manifest.json'),
    '--smells', str(OUT/'smells.json'), '--viewports', 'desktop,mobile',
    '--themes', 'dark,light', '--locales', 'en,zh', '--max-pages', '1',
    '--settle-ms', '1400'], driver_factory=driver_factory)
assert code == 0
meta = json.loads((OUT/'manifest.json').read_text())['pages'][0]
assert len(meta['states']) == 8 and all(state['captured'] for state in meta['states'])
assert not meta['console_errors'] and not meta['failed_responses']
assert all(not row['horizontal_overflow'] for row in meta['metrics']['by_viewport'].values())
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
    functools.partial(Quiet, directory=str(ROOT/'site')))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
cases = []
try:
    with sync_playwright() as manager:
        browser = manager.chromium.launch(headless=True, executable_path=CHROME)
        try:
            for width, height in [(1440,900), (390,844)]:
                for theme in ('dark','light'):
                    for language in ('en','zh'):
                        context = browser.new_context(viewport={'width':width,'height':height},
                            **({'is_mobile':True,'has_touch':True} if width==390 else {}))
                        try:
                            context.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('lang','{language}');")
                            page = context.new_page(); errors = []
                            page.on('pageerror', lambda error: errors.append(str(error)))
                            page.goto(f'http://127.0.0.1:{server.server_port}/china.html', wait_until='domcontentloaded')
                            panel = page.locator('#cnx-participation')
                            panel.wait_for(state='visible')
                            text = panel.inner_text()
                            assert ('Dated snapshot' if language=='en' else '历史快照') in text
                            assert PROOF['timing']['expected_session'] in text and '2026-09-21' in text
                            assert 'Recent rebound, uneven recovery' not in text
                            summary = panel.locator('summary')
                            summary.tap() if width==390 else summary.click()
                            assert panel.locator('details').get_attribute('open') is not None
                            text = panel.inner_text()
                            assert ('Check source timing' if language=='en' else '核对来源时间') in text
                            assert ('2 sessions behind expected' if language=='en' else '2 个交易日落后于预期') in text
                            assert not page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')
                            assert not panel.evaluate('(el)=>el.scrollWidth>el.clientWidth')
                            if (width,theme,language) in [(1440,'dark','en'),(390,'light','zh')]:
                                panel.screenshot(path=str(OUT/f'clock-detail-{width}-{theme}-{language}.png'))
                            summary.tap() if width==390 else summary.click()
                            assert panel.locator('details').get_attribute('open') is None
                            assert not errors, errors
                            cases.append({'width':width,'theme':theme,'language':language,
                                'dated_state_visible':True,'expected_date_visible':True,
                                'disclosure_opens_and_closes':True,'overflow':False})
                        finally:
                            context.close()
        finally:
            browser.close()
finally:
    server.shutdown(); server.server_close(); thread.join(timeout=5)
assert hashlib.sha256(PAGE.read_bytes()).hexdigest() == BEFORE
receipt = {'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'page_sha256':BEFORE,'cases':cases,'lens_tested':False,'production':False,'fresh_collection':False}
(OUT/'clock-interactions.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'captures':8,'clock_interactions':len(cases),'page_sha256':BEFORE,'lens_acceptance':False}))
