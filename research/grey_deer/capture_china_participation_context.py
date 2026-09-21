"""Local-only real-page evidence; no collector, CI, publication or credentials."""
from pathlib import Path
import functools
import hashlib
import http.server
import json
import subprocess
import sys
import threading
from playwright.sync_api import sync_playwright
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import capture_page_evidence as capture
OUT = ROOT / 'mockups/evidence/china-participation-context-20260921'
OUT.mkdir(parents=True, exist_ok=True)
PAGE = ROOT / 'site/china.html'
BEFORE = hashlib.sha256(PAGE.read_bytes()).hexdigest()
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

def driver_factory(**kwargs):
    manager = sync_playwright().start()
    try:
        browser = manager.chromium.launch(headless=True, executable_path=CHROME)
    except Exception:
        manager.stop()
        raise
    return capture._PlaywrightDriver(manager, browser, kwargs.get('user_agent',capture.USER_AGENT),
        dict(kwargs.get('observer_config') or capture.DEFAULT_OBSERVER_CONFIG),kwargs.get('settle_ms',1400))

code = capture.main([
    '--site-dir', str(ROOT / 'site'), '--routes', '/china.html',
    '--output-dir', str(OUT), '--manifest', str(OUT / 'manifest.json'),
    '--smells', str(OUT / 'smells.json'), '--viewports', 'desktop,mobile',
    '--themes', 'dark,light', '--locales', 'en,zh', '--max-pages', '1',
    '--settle-ms', '1400',
], driver_factory=driver_factory)
assert code == 0, f'capture failed: {code}'
manifest = json.loads((OUT / 'manifest.json').read_text())
page_receipt = manifest['pages'][0]
assert len(page_receipt['states']) == 8
assert all(s['captured'] for s in page_receipt['states'])
assert not page_receipt['console_errors'] and not page_receipt['failed_responses']
assert all(not v['horizontal_overflow'] for v in page_receipt['metrics']['by_viewport'].values())

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
    functools.partial(QuietHandler, directory=str(ROOT / 'site')))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
origin = f'http://127.0.0.1:{server.server_port}'
cases = []
fixture_env = Environment(loader=FileSystemLoader(str(ROOT / 'templates')),autoescape=True)
fixture_template = fixture_env.from_string('{% import "_china_participation_context.html.j2" as c %}{{ c.participation_panel(ctx) }}')
missing_fixture = fixture_template.render(ctx={})
delayed_fixture = fixture_template.render(ctx={'sample':{'status':'delayed','asof':'2026-09-04'}})
try:
    with sync_playwright() as manager:
        browser = manager.chromium.launch(headless=True, executable_path=CHROME)
        try:
            for width, height in [(1440, 900), (390, 844)]:
                for theme in ('dark', 'light'):
                    for lang in ('en', 'zh'):
                        context = browser.new_context(viewport={'width':width, 'height':height})
                        try:
                            context.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('lang','{lang}');")
                            page = context.new_page()
                            errors = []
                            page.on('pageerror', lambda error: errors.append(str(error)))
                            page.goto(origin + '/china.html', wait_until='domcontentloaded')
                            panel = page.locator('#cnx-participation')
                            panel.wait_for(state='visible')
                            assert '-0.89%' in panel.text_content()
                            assert '1711 / 1816' in panel.text_content()
                            assert '28.3%' in panel.text_content()
                            assert panel.locator('details').get_attribute('open') is None
                            panel.locator('summary').click()
                            assert panel.locator('details').get_attribute('open') is not None
                            assert panel.locator('tbody tr').count() == 16
                            semi = panel.locator('tbody tr').filter(has_text='Semiconductors')
                            assert semi.count() == 1
                            assert '-0.36%' in semi.text_content() and '+1.73' in semi.text_content()
                            assert not page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')
                            assert not errors, errors
                            if (width,theme,lang) in [(1440,'dark','en'),(390,'light','zh')]:
                                panel.screenshot(path=str(OUT / f'expanded-{width}-{theme}-{lang}.png'))
                            # Explicit synthetic presentation checks; source-loader absence
                            # and freshness are separately exercised in deterministic tests.
                            panel.evaluate('(el,html)=>{el.outerHTML=html}', missing_fixture)
                            missing = page.locator('#cnx-participation')
                            assert 'Participation unavailable' in missing.text_content()
                            assert 'rose' not in missing.locator('.cnx-part-data').first.text_content()
                            missing.evaluate('(el,html)=>{el.outerHTML=html}', delayed_fixture)
                            delayed = page.locator('#cnx-participation')
                            assert 'Sample behind assessment' in delayed.text_content()
                            assert '2026-09-04' in delayed.text_content()
                            assert 'Recent rebound' not in delayed.text_content()
                            assert not page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')
                            cases.append({'width':width, 'theme':theme, 'locale':lang,
                                'details_open':True, 'sectors':16, 'negative_absolute_positive_gap':True,
                                'synthetic_missing_and_delayed_presentation':True,
                                'page_errors':errors, 'horizontal_overflow':False})
                        finally:
                            context.close()
        finally:
            browser.close()
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
assert not thread.is_alive()
assert hashlib.sha256(PAGE.read_bytes()).hexdigest() == BEFORE
receipt = {'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
           'page_sha256':BEFORE, 'page_bytes':PAGE.stat().st_size,
           'input_receipt':'research/grey_deer/CHINA_PARTICIPATION_REAL_INPUT_20260921.json',
           'kind':'actual no-network builder with stored inputs; no production deployment',
           'assessment_asof':'2026-09-18', 'capture_cases':8,
           'interaction_cases':cases, 'source_page_unchanged':True,
           'server_closed':True, 'production':False, 'fresh_collection':False}
(OUT / 'interaction-proof.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'capture_cases':8,'interaction_cases':len(cases),
                  'page_sha256':BEFORE,'production':False,'server_closed':True}))
