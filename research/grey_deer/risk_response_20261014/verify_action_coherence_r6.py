"""Real-browser integration of the two existing live readers and action card.

Synthetic market records, anonymous offline page, original Jinja and JavaScript.
No production write, credential, trading outcome, or second polling mechanism.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from playwright.sync_api import sync_playwright
    from tests.test_risk_envelope_radar_integration import source_envelope
    from tests.test_macro_risk_dialog import _vm, _render

    session = '2026-10-14'
    settled = source_envelope()
    settled.update(market='US', source_session=session)
    settled['hazard_summary'].update(stage=None, stage_reason='required_coverage_unavailable')
    for source in settled['provenance']['sources']: source['as_of'] = session
    settled['provenance']['sources'][1]['coverage'] = 'MISSING'
    vm = _vm(risk_envelope=settled)
    vm['market_state'].update(asof=session, verdict='RISK_ON', color='green', score=70,
                             label_en='Risk-on', label_zh='偏多', participation_scope=None)
    html = _render(vm)
    html = re.sub(r'<script\b([^>]*)>(.*?)</script>', lambda m:
                  m.group(0) if 'type="application/json"' in m[1] else '', html, flags=re.S | re.I)
    live = deepcopy(settled)
    live.update(source_session='2026-10-15', revision='live_provisional', precedence='live',
                live_active=True, built='2026-10-15 15:00:00 UTC', stale_after_min=5,
                overlays={'settled_bundle_id': settled['bundle_id']},
                live_transition={'candidate_stage': None, 'stable_stage': None, 'pending': None})
    for source in live['provenance']['sources']: source['as_of'] = '2026-10-15'

    def market(verdict: str, score: int) -> dict:
        colors = {'RISK_ON': 'green', 'MIXED': 'yellow', 'RISK_OFF': 'red'}
        labels = {'RISK_ON': ('Risk-on', '偏多'), 'MIXED': ('Mixed', '混合'), 'RISK_OFF': ('Risk-off', '避险')}
        display = {'verdict': verdict, 'score': score, 'raw_score': score,
                   'color': colors[verdict], 'label_en': labels[verdict][0],
                   'label_zh': labels[verdict][1]}
        return {'built': '2026-10-15 15:01:00 UTC', 'nightly_asof': session,
                'live_active': True, 'stale': False, 'display': display,
                'nightly': deepcopy(display), 'realtime': False}

    scripts = {'market': (ROOT / 'templates/risk_state_live.js').read_text(),
               'envelope': (ROOT / 'templates/risk_envelope_live.js').read_text()}
    scenarios = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, channel='chrome')
        try:
            for theme in ('dark', 'light'):
                for lang in ('en', 'zh'):
                    for width in (1440, 390):
                        for order in (('market', 'envelope'), ('envelope', 'market')):
                            page = browser.new_page(viewport={'width': width, 'height': 1000}, reduced_motion='reduce')
                            def serve(route):
                                u = urlsplit(route.request.url)
                                if u.netloc != 'risk-action.invalid': route.abort(); return
                                if u.path == '/macro.html':
                                    route.fulfill(status=200, content_type='text/html', body=html); return
                                if u.path in ('/theme.css', '/tier_preview.css', '/navigation-refresh.css'):
                                    p = ROOT / 'templates' / u.path[1:]
                                    if p.is_file(): route.fulfill(status=200, content_type='text/css', body=p.read_text()); return
                                route.abort()
                            page.route('**/*', serve)
                            page.goto('http://risk-action.invalid/macro.html', wait_until='domcontentloaded')
                            page.evaluate("([theme,lang])=>{document.documentElement.setAttribute('data-theme',theme);document.documentElement.setAttribute('data-lang',lang);document.documentElement.lang=lang;document.body.classList.add('page-macro','mx4-grid');}", [theme,lang])
                            label = page.locator('[data-wtd-primary] .mx5-action-label')
                            en = label.locator('.l-en')
                            assert en.text_content() == 'Review exposure. Respect existing stops.'
                            page.evaluate("([market,envelope])=>{window.__ms=market;window.__env=envelope;window.__envOffline=false;window.__pollers=[];Date.now=()=>Date.parse('2026-10-15T15:01:00Z');window.setInterval=f=>{window.__pollers.push(f);return window.__pollers.length;};window.fetch=url=>{if(String(url).includes('risk_state.json'))return Promise.resolve({ok:true,json:()=>Promise.resolve(JSON.parse(JSON.stringify(window.__ms)))});if(window.__envOffline)return Promise.reject(new Error('offline test'));return Promise.resolve({ok:true,json:()=>Promise.resolve(JSON.parse(JSON.stringify(window.__env)))});};}", [market('RISK_ON',70),live])
                            for name in order: page.add_script_tag(content=scripts[name])
                            page.wait_for_function("document.getElementById('risk-response-date').textContent.includes('2026-10-15')")
                            assert en.text_content() == 'Review exposure. Respect existing stops.'
                            assert label.get_attribute('data-wtd-base-verdict') == 'RISK_ON'
                            assert not page.locator('[data-wtd-primary] .mx5-action-icon').is_visible()
                            # A market-only refresh must not overwrite a visible warning.
                            page.evaluate("m=>{window.__ms=m;window.__pollers.forEach(f=>f());}", market('MIXED',44))
                            page.wait_for_function("document.querySelector('[data-wtd-primary] .mx5-action-label').getAttribute('data-wtd-base-verdict')==='MIXED'")
                            assert en.text_content() == 'Review exposure. Respect existing stops.'
                            # Stronger native Risk-off guidance must survive both reader orders.
                            page.evaluate("m=>{window.__ms=m;window.__pollers.forEach(f=>f());}", market('RISK_OFF',30))
                            page.wait_for_function("document.querySelector('[data-wtd-primary] .mx5-action-label .l-en').textContent==='Reduce risk. Protect capital.'")
                            assert page.locator('[data-wtd-primary] .mx5-action-icon').is_visible()
                            page.evaluate("m=>{window.__ms=m;window.__pollers.forEach(f=>f());}", market('MIXED',44))
                            page.wait_for_function("document.querySelector('[data-wtd-primary] .mx5-action-label').getAttribute('data-wtd-base-verdict')==='MIXED'")
                            assert en.text_content() == 'Review exposure. Respect existing stops.'
                            # Returning dated settled warning after outage never means add risk.
                            page.evaluate("()=>{window.__envOffline=true;window.__pollers.forEach(f=>f());}")
                            page.wait_for_function("document.getElementById('risk-response-date').textContent.includes('2026-10-14')")
                            assert 'Add where' not in en.text_content()
                            quiet = deepcopy(live)
                            quiet['built'] = '2026-10-15 15:01:00 UTC'
                            quiet['hazard_summary'].update(stage='NONE', contributing_sources=[])
                            quiet['live_transition'].update(candidate_stage='NONE', stable_stage='NONE', pending=None)
                            quiet['measured_state']['usable'] = True
                            for source in quiet['provenance']['sources']:
                                source['coverage'] = 'FRESH'
                                if source['role']=='hazard_evidence': source.update(state='calm', hazard_stage='NONE')
                            page.evaluate("e=>{window.__env=e;window.__envOffline=false;window.__pollers.forEach(f=>f());}", quiet)
                            page.wait_for_function("document.getElementById('risk-response-summary').hidden")
                            assert en.text_content() == 'Trade small. Stay selective.'
                            assert page.locator('.mx5-big-score').text_content() == '44'
                            assert label.locator('.l-en' if lang=='en' else '.l-zh').is_visible()
                            assert not label.locator('.l-zh' if lang=='en' else '.l-en').is_visible()
                            box = label.bounding_box()
                            assert box and box['x'] >= -1 and box['x']+box['width'] <= width+1
                            assert page.evaluate('window.__pollers.length') == 2
                            scenarios.append({'theme':theme,'language':lang,'width':width,'load_order':list(order),
                                              'warning_precedence':True,'risk_off_preserved':True,
                                              'outage_not_add_risk':True,'latest_base_restored':True,
                                              'no_extra_poller':True,'bilingual_visibility':True})
                            page.close()
        finally:
            browser.close()
    print(json.dumps({'kind':'offline_two_reader_action_coherence','passed':len(scenarios),
                      'production':False,'synthetic_data':True,'external_network':False,'cases':scenarios},ensure_ascii=False,indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
