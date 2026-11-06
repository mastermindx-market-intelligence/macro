"""Offline full-template foreground proof; not authenticated production evidence.

Serve only fixture HTML and existing local styles to Chromium. Keep the real
Radar dialog runtime, inject explicit synthetic auth and live-feed fixtures, and
exercise the actual existing reader. No real accounts, network or market writes.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
EVIDENCE = Path(__file__).resolve().parent / "foreground_browser"


def main() -> int:
    from playwright.sync_api import sync_playwright
    from tests.test_risk_envelope_radar_integration import source_envelope, _foreground_render

    settled = source_envelope()
    settled['source_session'] = '2026-10-14'
    settled['measured_state'].update(verdict='MIXED', score=50, as_of='2026-10-14')
    settled['hazard_summary'].update(stage=None, stage_reason='required_coverage_unavailable')
    for source in settled['provenance']['sources']:
        source['as_of'] = '2026-10-14'
    settled['provenance']['sources'][1]['coverage'] = 'MISSING'
    html = _foreground_render(settled)
    html = re.sub(r'<script\b([^>]*)>(.*?)</script>', lambda match:
                  match.group(0) if ('type="application/json"' in match[1]
                                      or 'window.mx5OpenDlg = function' in match[2]) else '',
                  html, flags=re.S | re.I)
    live = copy.deepcopy(settled)
    live.update(source_session='2026-10-15', revision='live_provisional', precedence='live',
                live_active=True, built='2026-10-15 15:00:00 UTC', stale_after_min=5,
                overlays={'settled_bundle_id': settled['bundle_id']},
                live_transition={'candidate_stage': None, 'stable_stage': None, 'pending': None})
    for source in live['provenance']['sources']:
        source['as_of'] = '2026-10-15'
    js = (ROOT / 'templates/risk_envelope_live.js').read_text()
    cases = []
    EVIDENCE.mkdir(exist_ok=True)
    def serve(route):
        url = urlsplit(route.request.url)
        if url.netloc != 'risk-fixture.invalid':
            route.abort(); return
        if url.path == '/macro.html':
            route.fulfill(status=200, content_type='text/html', body=html); return
        if url.path in ('/theme.css', '/tier_preview.css', '/navigation-refresh.css'):
            css = ROOT / 'templates' / url.path[1:]
            if css.is_file():
                route.fulfill(status=200, content_type='text/css', body=css.read_text()); return
        route.abort()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, channel='chrome')
        try:
            for theme in ('dark', 'light'):
                for language in ('en', 'zh'):
                    for width in (1440, 390):
                        page = browser.new_page(viewport={'width': width, 'height': 1000}, reduced_motion='reduce')
                        page.route('**/*', serve)
                        page.goto('http://risk-fixture.invalid/macro.html', wait_until='domcontentloaded')
                        page.evaluate("([theme,lang])=>{document.documentElement.setAttribute('data-theme',theme);document.documentElement.setAttribute('data-lang',lang);document.documentElement.lang=lang;document.body.classList.add('page-macro','mx4-grid');window.__signin=0;window.MMXAccessPreview={isAnon:()=>true,openSignin:()=>window.__signin++};}", [theme, language])
                        summary = page.locator('#risk-response-summary')
                        assert summary.is_visible()
                        assert page.locator('.mx5-big-score').inner_text() == '50'
                        assert summary.get_attribute('data-state') == 'partial-warning'
                        summary.scroll_into_view_if_needed()
                        sbox = summary.bounding_box()
                        gbox = page.locator('.mx5-sc-gauge-row').first.bounding_box()
                        assert sbox and gbox and sbox['y'] + sbox['height'] <= gbox['y'] + 2
                        assert sbox['x'] >= -1 and sbox['x'] + sbox['width'] <= width + 1
                        selected = '.l-en' if language == 'en' else '.l-zh'
                        other = '.l-zh' if language == 'en' else '.l-en'
                        assert page.locator('#risk-response-title ' + selected).is_visible()
                        assert not page.locator('#risk-response-title ' + other).is_visible()
                        button = summary.locator('button[aria-controls="dlg-risk"]')
                        button.focus(); page.keyboard.press('Enter')
                        assert page.evaluate('window.__signin') == 1
                        assert not page.locator('#dlg-risk').evaluate("e=>e.classList.contains('open')")
                        page.evaluate('window.MMXAccessPreview.isAnon=()=>false')
                        button.focus(); page.keyboard.press('Enter')
                        assert page.locator('#dlg-risk').evaluate("e=>e.classList.contains('open')")
                        page.keyboard.press('Escape')
                        assert not page.locator('#dlg-risk').evaluate("e=>e.classList.contains('open')")
                        assert button.evaluate('e=>document.activeElement===e')
                        page.evaluate("feed=>{window.__riskFeed=feed;Date.now=()=>Date.parse('2026-10-15T15:01:00Z');window.fetch=()=>Promise.resolve({ok:true,json:()=>Promise.resolve(window.__riskFeed)});window.__riskTimers=[];window.setInterval=f=>{window.__riskTimers.push(f);return window.__riskTimers.length;};}", live)
                        page.add_script_tag(content=js)
                        page.wait_for_function("document.getElementById('risk-response-date').textContent.includes('2026-10-15')")
                        assert summary.is_visible() and summary.get_attribute('data-state') == 'partial-warning'
                        assert 'Credit stress: building' in page.locator('#risk-response-cause').text_content()
                        assert not page.locator('#dlg-risk').evaluate("e=>e.classList.contains('open')")
                        summary.scroll_into_view_if_needed()
                        image = EVIDENCE / f'{theme}-{language}-{width}.png'
                        summary.screenshot(path=str(image))
                        page.evaluate("()=>{window.fetch=()=>Promise.reject(new Error('offline fixture'));window.__riskTimers[0]();}")
                        page.wait_for_function("document.getElementById('risk-response-date').textContent.includes('2026-10-14')")
                        assert summary.is_visible() and summary.get_attribute('data-state') == 'partial-warning'
                        cases.append({'theme': theme, 'language': language, 'width': width,
                                      'visible_above_gauge': True, 'fits_viewport': True,
                                      'anonymous_gate_preserved': True, 'keyboard_dialog_and_return': True,
                                      'live_updates_with_dialog_closed': True, 'dated_fallback': True,
                                      'screenshot': str(image.relative_to(ROOT))})
                        page.close()
            # Additional real-DOM transitions start without a dated warning. This
            # checks the actual initially empty bilingual nodes, not a mock DOM.
            for initial in ('quiet', 'unavailable'):
                quiet = copy.deepcopy(settled)
                quiet['hazard_summary'].update(stage='NONE', contributing_sources=[])
                for item in quiet['provenance']['sources']:
                    item['coverage'] = 'FRESH'
                    if item['role'] == 'hazard_evidence':
                        item.update(state='calm', hazard_stage='NONE')
                initial_payload = quiet if initial == 'quiet' else {}
                html = _foreground_render(initial_payload, '2026-10-14')
                html = re.sub(r'<script\b([^>]*)>(.*?)</script>', lambda match:
                    match.group(0) if ('type="application/json"' in match[1]
                                      or 'window.mx5OpenDlg = function' in match[2]) else '',
                    html, flags=re.S | re.I)
                # A missing envelope has no live band/reader by existing contract;
                # unavailable uses a dated incomplete envelope instead.
                if initial == 'unavailable':
                    unknown = copy.deepcopy(settled)
                    unknown['hazard_summary']['contributing_sources'] = []
                    html = _foreground_render(unknown, '2026-10-14')
                    html = re.sub(r'<script\b([^>]*)>(.*?)</script>', lambda match:
                        match.group(0) if ('type="application/json"' in match[1]
                                          or 'window.mx5OpenDlg = function' in match[2]) else '',
                        html, flags=re.S | re.I)
                page = browser.new_page(viewport={'width':390,'height':900}, reduced_motion='reduce')
                page.route('**/*', serve)
                page.goto('http://risk-fixture.invalid/macro.html', wait_until='domcontentloaded')
                page.evaluate("()=>{document.documentElement.setAttribute('data-theme','light');document.documentElement.setAttribute('data-lang','en');document.body.classList.add('page-macro','mx4-grid');}")
                summary = page.locator('#risk-response-summary')
                assert summary.get_attribute('data-state') == initial
                initial_background = summary.evaluate('e=>getComputedStyle(e).backgroundColor')
                page.evaluate("feed=>{window.__riskFeed=feed;Date.now=()=>Date.parse('2026-10-15T15:01:00Z');window.fetch=()=>Promise.resolve({ok:true,json:()=>Promise.resolve(window.__riskFeed)});window.__riskTimers=[];window.setInterval=f=>{window.__riskTimers.push(f);return window.__riskTimers.length;};}", live)
                page.add_script_tag(content=js)
                page.wait_for_function("document.getElementById('risk-response-date').textContent.includes('2026-10-15')")
                assert summary.is_visible() and summary.get_attribute('data-state') == 'partial-warning'
                assert page.locator('#risk-response-date .l-en').is_visible()
                if initial == 'unavailable':
                    assert initial_background != summary.evaluate('e=>getComputedStyle(e).backgroundColor'), 'Light unavailable state still uses warning material'
                page.evaluate("()=>{window.fetch=()=>Promise.reject(new Error('offline fixture'));window.__riskTimers[0]();}")
                page.wait_for_function("document.getElementById('risk-response-summary').getAttribute('data-state')==='unavailable'")
                assert summary.is_visible()
                if initial == 'quiet':
                    assert page.locator('#risk-response-date .l-en').is_visible()
                    assert '2026-10-14' in page.locator('#risk-response-date').text_content()
                recovered = copy.deepcopy(live)
                # Recovery is a newer issued response, not changed content at
                # the warning's existing publication identity.
                recovered['built'] = '2026-10-15 15:01:00 UTC'
                recovered['hazard_summary'].update(stage='NONE', contributing_sources=[])
                recovered['live_transition'].update(candidate_stage='NONE',stable_stage='NONE',pending=None)
                for item in recovered['provenance']['sources']:
                    item['coverage'] = 'FRESH'
                    if item['role'] == 'hazard_evidence': item.update(state='calm',hazard_stage='NONE')
                page.evaluate("feed=>{window.__riskFeed=feed;window.fetch=()=>Promise.resolve({ok:true,json:()=>Promise.resolve(window.__riskFeed)});window.__riskTimers[0]();}", recovered)
                page.wait_for_function("document.getElementById('risk-response-summary').hidden")
                cases.append({'initial_state':initial,'live_date_physically_visible':True,
                              'outage_not_all_clear':True,'validated_quiet_can_clear':True})
                page.close()
        finally:
            browser.close()
    print(json.dumps({'kind': 'offline_real_template_foreground_browser_proof', 'passed': len(cases),
                      'synthetic_auth_and_market_inputs': True, 'external_network': False,
                      'production': False, 'cases': cases}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
