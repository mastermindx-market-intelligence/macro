"""Local-file browser evidence for the design study, not production or Paper proof."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    target = root / 'research/market_navigator/preview.html'
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for width in (1440, 390):
            for lang in ('en', 'zh'):
                for theme in ('dark','light'):
                    errors = []
                    page = browser.new_page(viewport={'width':width,'height':1100 if width==1440 else 844}, device_scale_factor=1)
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto(target.as_uri(), wait_until='networkidle')
                    if lang == 'zh': page.locator('#language').click()
                    if theme == 'light': page.locator('#theme').click()
                    page.evaluate('document.fonts.ready')
                    overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                    undefined = 'undefined' in page.locator('body').inner_text()
                    assert not overflow, (width,lang,theme,'horizontal overflow')
                    assert not errors, errors
                    assert not undefined
                    name = f'{width}-{lang}-{theme}.png'
                    page.screenshot(path=str(args.output_dir/name), full_page=True)
                    page.locator('#why-wait').click()
                    assert page.locator('#evidence-dialog').is_visible()
                    page.keyboard.press('Escape')
                    assert not page.locator('#evidence-dialog').is_visible()
                    assert page.locator('#why-wait').evaluate('(node)=>node===document.activeElement')
                    page.locator('#change-toggle').click()
                    assert page.locator('#change-detail').is_visible()
                    page.locator('#change-toggle').click()
                    assert not page.locator('#change-detail').is_visible()
                    page.locator('[data-horizon="position"]').click()
                    assert page.locator('#state-message').is_visible()
                    assert not page.locator('.paths').is_visible()
                    assert page.locator('.watch-band button').is_disabled()
                    page.locator('[data-horizon="swing"]').click()
                    assert page.locator('.paths').is_visible()
                    if width == 1440:
                        page.locator('#data-state').click()
                        assert not page.locator('.paths').is_visible()
                        assert page.locator('#state-message').is_visible()
                        if lang=='en' and theme=='dark':
                            page.screenshot(path=str(args.output_dir/'stale-state.png'),full_page=True)
                        page.locator('#data-state').click()
                        assert not page.locator('.decision-layout').is_visible()
                        page.locator('#data-state').click()
                        assert page.locator('.decision-layout').is_visible()
                    results.append({'width':width,'language':lang,'theme':theme,'screenshot':name,
                        'horizontal_overflow':False,'js_errors':errors,'dialog_escape_focus_return':True,
                        'comparison_toggle':True,'unsupported_horizon_abstains':True,'save_disabled':True})
                    page.close()
        version=browser.version
        browser.close()
    report={'schema':'market_navigator.browser_study/v1','browser':version,
        'target':'local-file design study','paper_applied':False,'production_proof':False,
        'matrix':results,'passed':len(results)}
    (args.output_dir/'browser-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':len(results),'browser':version,'output':str(args.output_dir)}))


if __name__=='__main__': main()
