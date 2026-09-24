"""Exact stored-page proof plus explicitly synthetic recovery-dialog cases."""
from pathlib import Path
import copy, functools, hashlib, http.server, json, subprocess, sys, threading
from unittest.mock import patch
from playwright.sync_api import sync_playwright, expect
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import capture_page_evidence as capture
from engine import risk_radar_recovery as recovery
from tests.test_risk_radar_dlg_partial import _RD, _render
PAGE = ROOT / 'site/china.html'
BEFORE = hashlib.sha256(PAGE.read_bytes()).hexdigest()
OUT = ROOT / 'mockups/evidence/china-recovery-safety-20260924'
OUT.mkdir(parents=True, exist_ok=True)
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
FORBIDDEN = ('Begin scaling exposure back', 'Stop forced de-grossing',
    'ready a buy plan', 'risk easing on its own', '可分批逐步回补敞口', '停止被动减仓')

def factory(**kw):
    manager = sync_playwright().start()
    browser = manager.chromium.launch(headless=True, executable_path=CHROME)
    return capture._PlaywrightDriver(manager, browser,
        kw.get('user_agent', capture.USER_AGENT),
        dict(kw.get('observer_config') or capture.DEFAULT_OBSERVER_CONFIG), kw.get('settle_ms', 1400))

if '--interactions-only' not in sys.argv:
    assert capture.main(['--site-dir', str(ROOT/'site'), '--routes', '/china.html',
        '--output-dir', str(OUT), '--manifest', str(OUT/'manifest.json'),
        '--smells', str(OUT/'smells.json'), '--viewports', 'desktop,mobile',
        '--themes', 'dark,light', '--locales', 'en,zh', '--max-pages', '1'], driver_factory=factory) == 0
meta = json.loads((OUT/'manifest.json').read_text())['pages'][0]
assert len(meta['states']) == 8 and all(s['captured'] for s in meta['states'])
assert not meta['console_errors'] and not meta['failed_responses']
assert all(not m['horizontal_overflow'] for m in meta['metrics']['by_viewport'].values())

def synthetic_dialogs():
    outputs = {}
    for name, eligible, scopes in [('missing_permission', None, []),
            ('foreign_support', True, ['us']), ('local_internals_missing', True, ['cn'])]:
        rr = {'market': 'cn', 'trajectory': {'phase': 'receding', 'reached_risk': True,
            'off_peak': 12, 'velocity': -2, 'odds_now': .4, 'odds_peak': .5,
            'odds_delta': -.1, 'peak_days_ago': 8}}
        if eligible is not None: rr['deescalation'] = {'eligible': eligible}
        cats = [] if not scopes else [dict(key='synthetic', fresh=True,
            confirmation_markets=scopes, icon='', label_en='Synthetic liquidity context',
            label_zh='合成流动性背景', detail_en='Test input only', detail_zh='仅测试输入')]
        with patch.object(recovery, '_liquidity_catalysts', return_value=cats):
            rv = recovery.assess({'risk_radar': rr})
        assert rv['present'] and rv['turn_confirmed'] is False and rv['receding'] is False
        rd = copy.deepcopy(_RD); rd['recovery'] = rv
        outputs[name] = _render(mkt='cn', rd=rd, ctx={})
    return outputs

FIXTURES = synthetic_dialogs()
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT/'site')))
thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
cases = []
try:
    with sync_playwright() as manager:
        browser = manager.chromium.launch(headless=True, executable_path=CHROME)
        try:
            for width, height in [(1440, 900), (390, 844)]:
                for theme in ('dark', 'light'):
                    for lang in ('en', 'zh'):
                        ctx = browser.new_context(viewport={'width': width, 'height': height},
                            **({'is_mobile': True, 'has_touch': True} if width == 390 else {}))
                        try:
                            ctx.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('lang','{lang}');")
                            ctx.route('**/live/china_risk_state.json*', lambda r: r.fulfill(json=None))
                            page = ctx.new_page(); errors = []
                            page.on('pageerror', lambda e: errors.append(str(e)))
                            page.goto(f'http://127.0.0.1:{server.server_port}/china.html', wait_until='networkidle')
                            if width == 390: assert page.evaluate("matchMedia('(hover:none)').matches && navigator.maxTouchPoints>0")
                            page.locator('button[onclick*="cnx-pop-risk"]').click()
                            page.locator('#cnx-pop-risk .cnx-pop-link').click()
                            dialog = page.locator('#cnx-dlg-risk'); dialog.wait_for(state='visible')
                            assert not any(x in dialog.text_content() for x in FORBIDDEN)
                            assert 'all-boats' not in dialog.text_content()
                            page.keyboard.press('Escape'); dialog.wait_for(state='hidden')
                            card = page.locator('.cnx-rack3 > .cnx-card').filter(has_text='Pullback Risk')
                            card.tap() if width == 390 else card.click()
                            dialog.wait_for(state='visible')
                            actual_recovery_visible = dialog.locator('.rrx-rec').count() > 0
                            assert not any(x in dialog.text_content() for x in FORBIDDEN)
                            page.keyboard.press('Escape'); dialog.wait_for(state='hidden')
                            synthetic = []
                            for name, fragment in FIXTURES.items():
                                dialog.evaluate('(el,html)=>{el.outerHTML=html}', fragment)
                                card.tap() if width == 390 else card.click()
                                dialog.wait_for(state='visible')
                                rec = dialog.locator('.rrx-rec'); rec.wait_for(state='visible')
                                expect(rec.locator('.rrx-rec-ttl')).to_contain_text('Recovery not confirmed' if lang == 'en' else '修复尚未确认')
                                assert rec.locator('.rrx-rec-ttl .l-'+lang).is_visible()
                                assert not rec.locator('.rrx-rec-ttl .l-'+('zh' if lang == 'en' else 'en')).is_visible()
                                assert 'is-turn' not in rec.get_attribute('class')
                                assert rec.locator('.rrx-rec-tag').count() == 0
                                assert not any(x in rec.text_content() for x in FORBIDDEN)
                                assert 'does not authorize exposure changes' in rec.text_content()
                                if name == 'missing_permission':
                                    assert 'Liquidity support unconfirmed' in rec.text_content()
                                bounds = dialog.locator('.cnx-dlg-panel').bounding_box()
                                assert bounds and bounds['x'] >= -1 and bounds['x']+bounds['width'] <= width+1
                                assert not page.evaluate('document.documentElement.scrollWidth>document.documentElement.clientWidth')
                                page.keyboard.press('Escape'); dialog.wait_for(state='hidden')
                                synthetic.append(name)
                            if width == 390: assert page.evaluate("matchMedia('(hover:none)').matches && navigator.maxTouchPoints>0")
                            assert not errors, errors
                            cases.append(dict(width=width, theme=theme, locale=lang,
                                actual_both_entrypoints=True, actual_recovery_visible=actual_recovery_visible,
                                unsafe_copy_hits=[], synthetic_scenarios=synthetic,
                                synthetic_context_not_production=True, source_page_unchanged=True))
                            # Screenshots only after all touch/gesture assertions.
                            if (width, theme, lang) in [(1440, 'dark', 'en'), (390, 'light', 'zh')]:
                                card.tap() if width == 390 else card.click()
                                dialog.wait_for(state='visible'); page.wait_for_timeout(450)
                                page.screenshot(path=str(OUT/f'synthetic-unconfirmed-{width}-{theme}-{lang}.png'))
                        finally:
                            ctx.close()
        finally:
            browser.close()
finally:
    server.shutdown(); server.server_close(); thread.join(timeout=5)
assert not thread.is_alive()
assert hashlib.sha256(PAGE.read_bytes()).hexdigest() == BEFORE
receipt = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    page_sha256=BEFORE, cases=cases, static_captures=8, synthetic_cases=len(cases)*len(FIXTURES),
    production=False, fresh_collection=False, servers_closed=True,
    screenshot_after_gestures=True, risk_formula_changed=False)
(OUT/'interactions.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps({'static_captures': 8, 'actual_dialog_journeys': len(cases),
    'synthetic_recovery_cases': receipt['synthetic_cases'], 'page_sha256': BEFORE, 'production': False}))
