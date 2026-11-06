"""Controlled local HTML proof. No profile, server, external I/O or watch writes."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parent
results = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for case in ('known_zero_risk', 'missing_risk'):
        source = root / case / 'site' / 'forex.html'
        snapshot = json.loads((root / case / 'data/forex/latest.json').read_text())
        for width, height in ((1440, 1050), (390, 844)):
            context = browser.new_context(viewport={'width': width, 'height': height}, locale='en-US', reduced_motion='reduce')
            # Even if the generated page includes external widgets, they have no
            # access to networks, logged-in accounts or live state in this proof.
            context.route('http://**/*', lambda route: route.abort())
            context.route('https://**/*', lambda route: route.abort())
            page = context.new_page()
            page.goto(source.as_uri(), wait_until='load')
            page.add_style_tag(content='*,*::before,*::after{animation:none!important;transition:none!important}')
            embedded = json.loads(page.locator('#forex-decision-context').text_content())
            assert embedded == snapshot['decision_context']
            assert page.locator('.smile-dot').count() == (0 if case == 'missing_risk' else 1)
            if case == 'missing_risk':
                assert page.get_by_text('Risk context unavailable', exact=True).first.is_visible()
            summary = page.locator('details[data-fx-decision-readiness] summary')
            summary.focus()
            page.keyboard.press('Enter')
            assert page.locator('details[data-fx-decision-readiness]').get_attribute('open') is not None
            for theme in ('light', 'dark'):
                page.evaluate('(value)=>document.documentElement.setAttribute("data-theme",value)', theme)
                tooltip = page.locator('[data-tip-en][tabindex="0"]').first
                tooltip.focus()
                popup = tooltip.locator('.tip-pop')
                popup.wait_for(state='visible')
                style = popup.evaluate('(e)=>({color:getComputedStyle(e).color,background:getComputedStyle(e).backgroundColor,opacity:getComputedStyle(e).opacity})')
                assert style['color'] != style['background']
                assert float(style['opacity']) > 0
                page.screenshot(path=str(root / f'{case}-{width}-{theme}.png'), full_page=False)
                results.append({'case': case, 'viewport': [width, height], 'theme': theme,
                    'html_json_parity': True, 'keyboard_summary': True, 'focus_tooltip': True,
                    'tooltip_style': style,
                    'horizontal_overflow': page.evaluate('document.documentElement.scrollWidth > innerWidth'),
                    'snapshot_id': embedded['snapshot_id'],
                    'screenshot': f'{case}-{width}-{theme}.png'})
            context.close()
    browser.close()
report = {'status': 'PASS', 'scope': 'local generated HTML, synthetic builder inputs, external requests blocked; not production/full-widget acceptance', 'cases': results, 'live_io': False}
(root/'browser-smoke.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
