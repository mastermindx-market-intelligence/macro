"""Offline real-builder risk reading proof; no collector, CI or deployment."""
from pathlib import Path
import functools
import hashlib
import http.server
import json
import subprocess
import sys
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import capture_page_evidence as capture
OUT = ROOT / 'mockups/evidence/china-risk-reading-20260921'
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
    '--site-dir', str(ROOT/'site'), '--routes', '/china.html',
    '--output-dir', str(OUT), '--manifest', str(OUT/'manifest.json'),
    '--smells', str(OUT/'smells.json'), '--viewports', 'desktop,mobile',
    '--themes', 'dark,light', '--locales', 'en,zh', '--max-pages', '1',
    '--settle-ms', '1400',
], driver_factory=driver_factory)
assert code == 0
meta = json.loads((OUT/'manifest.json').read_text())['pages'][0]
assert len(meta['states']) == 8 and all(s['captured'] for s in meta['states'])
assert not meta['console_errors'] and not meta['failed_responses']
assert all(not m['horizontal_overflow'] for m in meta['metrics']['by_viewport'].values())

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

server = http.server.ThreadingHTTPServer(('127.0.0.1',0),
    functools.partial(QuietHandler,directory=str(ROOT/'site')))
thread = threading.Thread(target=server.serve_forever,daemon=True)
thread.start()
origin = f'http://127.0.0.1:{server.server_port}'
cases = []
try:
    with sync_playwright() as manager:
        browser = manager.chromium.launch(headless=True,executable_path=CHROME)
        try:
            for width,height in [(1440,900),(390,844)]:
                for theme in ('dark','light'):
                    for lang in ('en','zh'):
                        ctx = browser.new_context(viewport={'width':width,'height':height})
                        try:
                            ctx.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('lang','{lang}');")
                            page = ctx.new_page()
                            errors = []
                            page.on('pageerror',lambda e: errors.append(str(e)))
                            page.goto(origin+'/china.html',wait_until='domcontentloaded')
                            card = page.locator('.cnx-rack3 > .cnx-card').filter(has_text='Pullback Risk')
                            assert card.count() == 1
                            card_text = card.text_content()
                            assert 'Weak large-cap participation' in card_text
                            assert '大盘股参与偏弱' in card_text and '94' in card_text and '50%' in card_text
                            assert 'Historical stress' in card_text and 'not a probability' in card_text
                            assert 'all-boats' not in card_text
                            page.locator('button[onclick*="cnx-pop-risk"]').click()
                            pop = page.locator('#cnx-pop-risk')
                            pop.wait_for(state='visible')
                            assert 'state-based estimate' in pop.text_content()
                            assert '21 trading sessions' in pop.text_content()
                            assert 'all-boats' not in pop.text_content()
                            pop.locator('.cnx-pop-link').click()
                            dialog = page.locator('#cnx-dlg-risk')
                            dialog.wait_for(state='visible')
                            text = dialog.text_content()
                            assert 'all-boats' not in text and '广度普跌（普跌）' not in text
                            assert 'not a pullback probability' in text and 'state-based' in text
                            assert 'Shanghai Composite' in text and '21 trading sessions' in text
                            page.wait_for_timeout(450)  # allow the existing sheet animation to settle
                            if (width,theme,lang) in [(1440,'dark','en'),(390,'light','zh')]:
                                dialog.screenshot(path=str(OUT/f'dialog-{width}-{theme}-{lang}.png'))
                            page.keyboard.press('Escape')
                            dialog.wait_for(state='hidden')
                            card.click()
                            dialog.wait_for(state='visible')
                            page.keyboard.press('Escape')
                            dialog.wait_for(state='hidden')
                            assert not page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')
                            assert not errors, errors
                            cases.append({'width':width,'theme':theme,'locale':lang,
                                'score':94,'state_probability_pct':50,'scoped_card':True,
                                'scoped_popover':True,'scoped_shared_dialog':True,
                                'both_entrypoints_open':True,'escape_closes':True,'page_errors':errors})
                        finally:
                            ctx.close()
        finally:
            browser.close()
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
assert not thread.is_alive()
assert hashlib.sha256(PAGE.read_bytes()).hexdigest() == BEFORE
receipt = {'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'page_sha256':BEFORE,'page_bytes':PAGE.stat().st_size,'capture_cases':8,
    'interaction_cases':cases,'source_page_unchanged':True,'server_closed':True,
    'kind':'actual no-network builder with stored inputs; no live deployment',
    'production':False,'fresh_collection':False,'risk_model_changed':False}
(OUT/'interaction-proof.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'capture_cases':8,'interaction_cases':len(cases),
    'page_sha256':BEFORE,'production':False,'server_closed':True}))
