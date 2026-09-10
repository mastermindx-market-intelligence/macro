"""Reproduce narrow local homepage layouts and retain legible component crops."""
from pathlib import Path
import hashlib, json
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
results = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    try:
        for language in ('en', 'zh'):
            for theme in ('light', 'dark'):
                for width in (320, 390):
                    context = browser.new_context(viewport={'width': width, 'height': 844}, color_scheme=theme, reduced_motion='reduce')
                    page = context.new_page()
                    page.goto((ROOT / 'site/index.html').as_uri() + '?still&lang=' + language, wait_until='load')
                    page.wait_for_timeout(500)
                    row = {'language': language, 'preference': theme, 'requested_width': width}
                    row['document_width'] = page.evaluate('document.documentElement.scrollWidth')
                    assert row['document_width'] == width, row
                    if width == 320:
                        page.screenshot(path=str(OUT / f'{language}-{theme}-320.png'), full_page=True)
                    for kind, selector in [('footer', 'footer'), ('situations', '#f-sits .demo'), ('dated-caption', '.ph-tagrow')]:
                        target = page.locator(selector)
                        assert target.count() == 1, selector
                        target.screenshot(path=str(OUT / f'{language}-{theme}-{width}-{kind}.png'))
                    row['wider_elements'] = page.evaluate('''() => [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().width > innerWidth + 1).map(e => ({tag:e.tagName,id:e.id,cls:typeof e.className === 'string' ? e.className : '',width:e.getBoundingClientRect().width,clipping:[...function*(p){while(p){if(['hidden','clip','auto','scroll'].includes(getComputedStyle(p).overflowX))yield {tag:p.tagName,id:p.id,cls:p.className,overflowX:getComputedStyle(p).overflowX};p=p.parentElement}}(e.parentElement)]})).slice(0,15)''')
                    results.append(row)
                    context.close()
    finally:
        browser.close()
(OUT / 'narrow-layout.json').write_text(json.dumps({'local_only': True, 'results': results}, indent=2))
paths = ['templates/landing.css', 'site/landing.css', 'templates/index.html', 'site/index.html', 'templates/about.html', 'site/about.html', 'site/products/market-terminal.html', 'site/products/market-dashboards.html', 'site/products/mastermind-ai.html', 'tests/test_landing_mobile_reflow.py']
(OUT / 'source-snapshot.sha256').write_text(''.join(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() + '  ' + p + '\n' for p in paths))
print(json.dumps({'captured_states':len(results),'all_document_widths_match':all(r['document_width']==r['requested_width'] for r in results)},indent=2))
