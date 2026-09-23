"""Actual dated-event UI proof; stored inputs, no collection or release confirmation."""
from pathlib import Path
import functools, hashlib, http.server, json, subprocess, sys, threading
from playwright.sync_api import sync_playwright, expect
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import capture_page_evidence as capture
PROOF = json.loads(Path(sys.argv[1]).read_text())
OUT = ROOT / 'mockups/evidence/china-event-date-20260923'
OUT.mkdir(parents=True, exist_ok=True)
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
assert len(meta['states']) == 8 and all(s['captured'] for s in meta['states'])
assert not meta['console_errors'] and not meta['failed_responses']
assert all(not m['horizontal_overflow'] for m in meta['metrics']['by_viewport'].values())
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
    functools.partial(Quiet, directory=str(ROOT/'site')))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start(); cases = []
try:
    with sync_playwright() as manager:
        browser = manager.chromium.launch(headless=True, executable_path=CHROME)
        try:
            for width, height in [(1440,900), (390,844)]:
                for theme in ('dark','light'):
                    for lang in ('en','zh'):
                        ctx = browser.new_context(viewport={'width':width,'height':height},
                            **({'is_mobile':True,'has_touch':True} if width==390 else {}))
                        try:
                            ctx.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('lang','{lang}');")
                            page=ctx.new_page(); errors=[]
                            page.on('pageerror', lambda error: errors.append(str(error)))
                            page.goto(f'http://127.0.0.1:{server.server_port}/china.html', wait_until='domcontentloaded')
                            card=page.locator('.cnx-card[onclick="cnxOpenDlg(\'cnx-dlg-events\')"]')
                            reference=card.locator('.cnx-event-reference')
                            expect(reference.locator('time')).to_have_attribute('datetime', PROOF['event_clock']['asof'])
                            expect(reference.locator('.l-'+lang).first).to_be_visible()
                            expect(reference.locator('.l-'+('zh' if lang=='en' else 'en')).first).to_be_hidden()
                            assert PROOF['event_clock']['asof'] in card.text_content()
                            assert 'today' not in card.text_content().lower()
                            card.tap() if width==390 else card.click()
                            dialog=page.locator('#cnx-dlg-events')
                            expect(dialog).to_be_visible()
                            expect(dialog.locator('.cnx-event-reference time')).to_have_attribute('datetime', PROOF['event_clock']['asof'])
                            rows=dialog.locator('.cnx-mt tr')
                            assert rows.count() == len(PROOF['calendar'])+1
                            for i,event in enumerate(PROOF['calendar'], start=1):
                                cells=rows.nth(i).locator('td')
                                assert cells.nth(0).text_content().strip() == event['date']
                                assert cells.nth(1).text_content().startswith('+'+str(event['days_until']))
                            assert 'Days from reference' in dialog.text_content()
                            assert 'not a live countdown' in dialog.text_content()
                            page.wait_for_timeout(450)
                            assert not dialog.locator('.cnx-dlg-panel').evaluate('(el)=>el.scrollWidth>el.clientWidth')
                            assert not page.evaluate('document.documentElement.scrollWidth>document.documentElement.clientWidth')
                            page.keyboard.press('Escape'); expect(dialog).to_be_hidden()
                            if width==390:
                                assert page.evaluate('navigator.maxTouchPoints>0 && matchMedia("(hover: none)").matches')
                            assert not errors, errors
                            cases.append(dict(width=width, theme=theme, locale=lang,
                                dates_match=True, reference_visible=True, opens_and_closes=True,
                                no_overflow=True, calendar_rows=len(PROOF['calendar'])))
                        finally:
                            ctx.close()
        finally:
            browser.close()
finally:
    server.shutdown(); server.server_close(); thread.join(timeout=5)
assert not thread.is_alive() and hashlib.sha256(PAGE.read_bytes()).hexdigest()==BEFORE
receipt=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), page_sha256=BEFORE, cases=cases, production=False, fresh_collection=False, schedule_dates_validated=False, server_closed=True)
(OUT/'interactions.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(captures=8, event_journeys=len(cases), page_sha256=BEFORE, production=False)))
