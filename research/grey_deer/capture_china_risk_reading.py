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
CURRENT_SOURCE = '--current-source' in sys.argv
INTEGRATED = '--integrated' in sys.argv or CURRENT_SOURCE
EXPECTED = json.loads(Path(sys.argv[sys.argv.index('--expected')+1]).read_text()) if CURRENT_SOURCE else None
OUT = ROOT / ('mockups/evidence/china-integrated-context-20260921' if INTEGRATED else 'mockups/evidence/china-risk-reading-20260921')
if CURRENT_SOURCE:
    OUT = ROOT / 'mockups/evidence/china-source-current-20260922'
OUT.mkdir(parents=True, exist_ok=True)
PAGE = ROOT / 'site/china.html'
BEFORE = hashlib.sha256(PAGE.read_bytes()).hexdigest()
CAPTURE_CASES = 16 if INTEGRATED else 8
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
] + (['--force-state', 'participation-focus:focus(#cnx-participation summary)'] if INTEGRATED else []), driver_factory=driver_factory)
assert code == 0
meta = json.loads((OUT/'manifest.json').read_text())['pages'][0]
assert len(meta['states']) == CAPTURE_CASES and all(s['captured'] for s in meta['states'])
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
                            assert '大盘股参与偏弱' in card_text
                            score = EXPECTED['radar']['top_score'] if CURRENT_SOURCE else 94
                            probability_pct = round(EXPECTED['radar']['dd21']*100) if CURRENT_SOURCE else 50
                            assert str(score) in card_text and f'{probability_pct}%' in card_text
                            assert 'Historical stress' in card_text and 'not a probability' in card_text
                            assert 'all-boats' not in card_text
                            if INTEGRATED:
                                assert 'Economic slowdown' in card_text and '疲弱' in card_text
                                assert 'Deep-drawdown gauge' not in card_text
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
                            if INTEGRATED:
                                panel = page.locator('#cnx-participation')
                                panel.locator('summary').click()
                                assert panel.locator('details').get_attribute('open') is not None
                                assert ((f"{EXPECTED['sample']['eligible']} / {EXPECTED['sample']['configured']}") if CURRENT_SOURCE else '1711 / 1816') in panel.text_content()
                                cohort = panel.locator('.cnx-index-members')
                                if CURRENT_SOURCE:
                                    assert EXPECTED['cohort']['asof'] in cohort.text_content()
                                    assert f"{EXPECTED['cohort']['five']['eligible']} / 300" in cohort.text_content()
                                    assert 'Starting index weights unavailable' in cohort.text_content()
                                    assert panel.locator('.cnx-index-weights').count() == 0
                                    gaps = EXPECTED['cohort']['five'].get('coverage_detail', {})
                                    if gaps.get('excluded_count'):
                                        assert 'Unavailable' in cohort.locator('.cnx-kv .v').first.text_content()
                                        for row in gaps['members'][:5]:
                                            assert row['ticker'] in cohort.locator('.cnx-member-gaps').first.text_content()
                                        assert f"{gaps['excluded_count']} affected members" in cohort.text_content()
                                    if width == 390:
                                        cohort.screenshot(path=str(OUT/f'coverage-{width}-{theme}-{lang}.png'))
                                else:
                                    assert '300 / 300' in cohort.text_content()
                                    assert '-0.67%' in cohort.text_content() and '+0.07%' in cohort.text_content()
                                assert panel.locator('table').filter(has_text='Sector proxy').locator('tbody tr').count() == 16
                                panel.locator('summary').click()
                                if CURRENT_SOURCE:
                                    from bs4 import BeautifulSoup
                                    trigger = page.locator('.cnx-reason-row .cnx-lens.lens-q').first
                                    raw_tip = trigger.get_attribute('data-tip-'+lang)
                                    trigger.click()
                                    lens = page.locator('.lens-pop.open')
                                    lens.wait_for(state='visible')
                                    plain_tip = ' '.join(BeautifulSoup(raw_tip, 'html.parser').get_text(' ', strip=True).split())
                                    assert plain_tip in ' '.join(lens.inner_text().split())
                                    page.wait_for_timeout(350)
                                    bounds = lens.bounding_box()
                                    assert bounds and bounds['x'] >= -1 and bounds['x']+bounds['width'] <= width+1
                                    assert bounds['y'] >= -1 and bounds['y']+bounds['height'] <= height+1
                                    assert not page.locator('#cnx-dlg-playbook').is_visible()
                                    if (width,theme,lang) in [(1440,'dark','en'),(390,'light','zh')]:
                                        page.screenshot(path=str(OUT/f'lens-{width}-{theme}-{lang}.png'))
                                    page.keyboard.press('Escape')
                                    lens.wait_for(state='hidden')
                                from tests.test_china_archetype_d_s1 import _render_china_risk_case, _risk_card
                                # Explicitly synthetic missing-input component, rendered
                                # by the real full-page template then inspected in Chrome.
                                fragment = str(_risk_card(_render_china_risk_case(None)))
                                card.evaluate('(el,html)=>{el.outerHTML=html}', fragment)
                                missing = page.locator('.cnx-rack3 > .cnx-card').filter(has_text='Pullback Risk')
                                assert 'Unavailable' in missing.text_content()
                                footer = missing.locator('.cnx-foot').text_content()
                                assert 'size down' not in footer and '缩仓' not in footer
                                assert 'unavailable' in footer and '暂不可用' in footer
                            assert not page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')
                            assert not errors, errors
                            cases.append({'width':width,'theme':theme,'locale':lang,
                                'score':score,'state_probability_pct':probability_pct,'scoped_card':True,
                                'scoped_popover':True,'scoped_shared_dialog':True,
                                'both_entrypoints_open':True,'escape_closes':True,'page_errors':errors,
                                'integrated_participation_and_slowdown':INTEGRATED,
                                'synthetic_missing_guidance_and_slowdown':INTEGRATED,
                                'current_source_missing_cohort_proof':CURRENT_SOURCE,
                                'canonical_lens_visible_in_viewport':CURRENT_SOURCE})
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
    'page_sha256':BEFORE,'page_bytes':PAGE.stat().st_size,'capture_cases':CAPTURE_CASES,
    'interaction_cases':cases,'source_page_unchanged':True,'server_closed':True,
    'kind':'actual no-network builder with stored inputs; no live deployment',
    'production':False,'fresh_collection':False,'risk_model_changed':False,
    'expected_input_receipt':EXPECTED, 'weight_injection':False}
(OUT/'interaction-proof.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'capture_cases':CAPTURE_CASES,'interaction_cases':len(cases),
    'page_sha256':BEFORE,'production':False,'server_closed':True}))
