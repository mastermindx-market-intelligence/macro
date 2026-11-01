"""Real-browser component checks; synthetic fixtures, not route or market acceptance."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def verify(site: Path, output: Path) -> dict:
    cases = []
    with sync_playwright() as manager:
        browser = manager.chromium.launch(headless=True)
        try:
            # An SSR chart must not remain invisible below the fold or without JS.
            static_cases = []
            for market in ('cn', 'us'):
                context = browser.new_context(viewport={'width':390,'height':900}, java_script_enabled=False, reduced_motion='no-preference')
                page = context.new_page()
                page.goto((site / f'{market}.html').resolve().as_uri(), wait_until='load')
                ink = page.locator('.rrp-chart .ilx-path').first.evaluate('el=>({dash:parseFloat(getComputedStyle(el).strokeDashoffset),animation:getComputedStyle(el).animationName})')
                assert ink['dash'] == 0, ink
                label_opacity = page.locator('.rrp-chart .ilx-tag').first.evaluate('el=>parseFloat(getComputedStyle(el).opacity)')
                assert label_opacity == 1, label_opacity
                static_cases.append({'market':market,'javascript':False,'motion':'normal','visible_ink':True})
                context.close()
            for market in ('cn', 'us'):
                view = json.loads((site / f'{market}-view.json').read_text())
                deadline = datetime.fromisoformat(view['observation']['valid_until']).timestamp() * 1000
                for width in (1440, 390):
                    for theme in ('dark', 'light'):
                        for locale in ('en', 'zh'):
                            context = browser.new_context(viewport={'width':width,'height':900}, reduced_motion='no-preference')
                            page = context.new_page()
                            page.clock.install()
                            page.goto((site / f'{market}.html').resolve().as_uri(), wait_until='load')
                            page.evaluate('([theme,lang])=>{document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang=lang}', [theme,locale])
                            root = page.locator('.rrp')
                            assert root.get_attribute('data-pb-phase') == 'underway'
                            geometry = root.evaluate('el=>({padding:parseFloat(getComputedStyle(el.querySelector(".rrp-heading")).paddingLeft),radius:parseFloat(getComputedStyle(el).borderTopLeftRadius),overflow:document.documentElement.scrollWidth-innerWidth})')
                            assert geometry['padding'] == (24 if width > 680 else 20), geometry
                            assert geometry['radius'] == 14, geometry
                            assert geometry['overflow'] <= 1, geometry
                            assert root.locator(f'h2 .l-{locale}').is_visible()
                            assert root.locator('[data-metric="current"]').inner_text() == '−6.8%'
                            assert root.locator('[data-metric="worst"]').inner_text() == '−7.4%'
                            assert root.locator('[data-metric="rebound"]').inner_text() == '+0.6%'
                            summary = root.locator('.rrp-method summary').first
                            summary.focus()
                            summary.press('Enter')
                            assert summary.locator('..').get_attribute('open') is not None
                            summary.press('Enter')
                            assert summary.locator('..').get_attribute('open') is None
                            before = page.evaluate('Date.now()')
                            assert deadline > before, 'fixture deadline expired before the test'
                            page.clock.fast_forward(int(deadline - before + 50))
                            assert root.get_attribute('data-pb-phase') == 'unavailable'
                            assert root.locator('.pbx-expiry').is_visible()
                            assert not root.locator('[data-metric="current"]').is_visible()
                            assert root.locator('[data-forecast-status="unavailable"]').is_visible()
                            cases.append({'market':market,'width':width,'theme':theme,'locale':locale,
                                          'geometry':geometry,'disclosure_keyboard':'pass','native_expiry':'pass',
                                          'input':'synthetic, native observer; not live prices'})
                            context.close()
        finally:
            browser.close()
    result={'kind':'synthetic_component_behavior_not_production','cases':cases,'passed':len(cases),'static_chart_cases':static_cases}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--site-dir',type=Path,required=True)
    p.add_argument('--output-json',type=Path,required=True)
    a=p.parse_args()
    result=verify(a.site_dir,a.output_json)
    print(f"{result['passed']}/16 component behavior cases passed")
