"""Real Chromium qualification of the source-backed review consumer; never a deployment."""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
from render_shared_preview import compile_from_canonical_source, render_html

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path, required=True)
OUT = parser.parse_args().output_dir.resolve()
if OUT.is_relative_to((ROOT / 'site').resolve()):
    parser.error('Review evidence cannot be written into the production site directory')
OUT.mkdir(exist_ok=False)
manifest = compile_from_canonical_source()
content = render_html(manifest)
pagefile = OUT / 'guide.html'
pagefile.write_text(content)
checks, matrix, errors, requests = [], [], [], []

def record(name):
    checks.append(name)
    print('PASS', name, flush=True)

def fit(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'horizontal overflow'

def snap(page, name):
    page.screenshot(path=str(OUT / (name + '.png')), full_page=True)
    matrix.append(name)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width':1440,'height':900})
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: requests.append(request.url) if request.url.startswith(('http:', 'https:')) else None)
    url = pagefile.as_uri()
    page.goto(url)
    assert page.locator('#app h1').inner_text() == 'Market Guide'
    assert page.locator('[data-fixture-only]').get_attribute('data-fixture-only') == 'false'
    record('real registry and real rendered owner-page validators consumed; 46 entries')
    page.keyboard.press('/')
    assert page.locator('#search').evaluate('(node)=>node === document.activeElement')
    page.locator('#search').fill('state dial')
    assert page.locator('#result-list article').count() == 1
    assert page.locator('#result-list a').first.inner_text() == 'Market State Score'
    page.reload()
    assert page.locator('#search').input_value() == 'state dial'
    record('keyboard search, English alias and query reload')
    page.locator('#search').fill('市场状态评分')
    assert page.locator('#result-list article').count() == 1
    page.locator('#search').fill('Regime Badge')
    assert page.locator('#result-list article').count() == 1
    assert page.locator('#result-list a').first.inner_text() == 'Market Regime'
    record('Chinese aliases and coverage names resolve to the canonical record')
    page.goto(url + '#prophet-stock-signals-board')
    assert page.locator('[data-coverage="not_an_indicator"]').is_visible()
    assert page.locator('[data-presentation]').count() == 0
    record('dashboard board names explain their components, not a fabricated indicator')
    page.goto(url + '#risk-radar')
    page.locator('[data-choice="interpretation_up"]').click()
    assert 'not an exit signal' in page.locator('[data-reading-text]').inner_text()
    page.goto(url + '#market-state-score')
    page.locator('[data-choice="interpretation_up"]').click()
    assert 'supportive' in page.locator('[data-reading-text]').inner_text()
    record('risk and strength preserve opposite higher-reading meanings')
    page.goto(url + '#regime-quadrant')
    assert page.locator('[data-choice]').count() == 4
    page.locator('[data-choice="growth-up-inflation-up"]').click()
    page.reload()
    assert page.locator('[data-choice="growth-up-inflation-up"]').get_attribute('aria-pressed') == 'true'
    page.goto(url + '#transition-state')
    assert page.locator('[data-choice]').count() == 0
    record('four-cell quadrant persists selection; confirmation remains non-directional')
    page.goto(url)
    opener = page.locator('[data-help="market-state-score"]:visible')
    opener.scroll_into_view_if_needed()
    scroll = page.evaluate('scrollY')
    opener.click()
    assert page.locator('#help').evaluate('(node)=>node.open')
    for _ in range(12):
        page.keyboard.press('Tab')
        assert page.locator('#help').evaluate('(node)=>node.contains(document.activeElement)')
    page.keyboard.press('Escape')
    assert not page.locator('#help').evaluate('(node)=>node.open')
    assert opener.evaluate('(node)=>node===document.activeElement')
    assert abs(page.evaluate('scrollY') - scroll) < 3
    record('native modal focus trap, Escape, opener focus and scroll restoration')
    page.goto(url + '?q=regime')
    original_ids = page.locator('#result-list [data-entry-link]').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.entryLink)')
    page.locator('#result-list [data-entry-link]').first.click()
    selected_title = page.locator('#app h1').inner_text()
    page.go_back()
    assert page.locator('#search').input_value() == 'regime'
    assert page.locator('#result-list [data-entry-link]').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.entryLink)') == original_ids
    page.go_forward()
    assert page.locator('#app h1').inner_text() == selected_title
    record('real back/forward restores exact query and result membership')
    page.goto(url + '#not-a-real-entry')
    assert page.locator('[data-missing-name]').inner_text() == 'not-a-real-entry'
    snap(page, 'unknown-entry')
    page.goto(url + '?q=no-such-explanation')
    assert page.locator('#result-list article').count() == 0
    assert 'No matching explanation' in page.locator('#result-list').inner_text()
    snap(page, 'zero-results')
    record('unknown-link identity and actionable empty-result recovery')
    assert len(manifest['entries']) == 46
    for width in [1440,390]:
        page.set_viewport_size({'width':width,'height':900 if width==1440 else 844})
        for language in ['en','zh']:
            query = '?lang=zh' if language == 'zh' else ''
            for record_data in manifest['entries']:
                page.goto(url + query + '#' + record_data['id'])
                assert page.locator('#app h1').inner_text() == record_data['label'][language]
                fit(page)
    record('184 real-record detail journeys: 46 entries × both languages × both widths')
    for width in [1440, 390]:
        page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
        for language in ['en', 'zh']:
            query = '?lang=zh' if language == 'zh' else ''
            for theme in ['light', 'dark']:
                for state in ['', 'market-state-score', 'risk-radar', 'regime-quadrant', 'transition-state', 'help']:
                    page.goto(url + query + ('#' + state if state and state != 'help' else ''))
                    # Fragment navigation may retain the existing theme. Select the target, do not blindly toggle.
                    if page.locator('html').get_attribute('data-theme') != theme:
                        page.locator('#theme').click()
                    assert page.locator('html').get_attribute('data-theme') == theme
                    if state == 'help':
                        page.locator('[data-help="market-state-score"]:visible').click()
                        assert page.locator('#help').evaluate('(node)=>node.open')
                    fit(page)
                    snap(page, f'{state or "home"}-{theme}-{language}-{width}')
                    if state == 'help':
                        page.keyboard.press('Escape')
    record('48 current-source screenshots: six views across both themes, languages and widths')
    nojs = browser.new_context(java_script_enabled=False, viewport={'width': 390, 'height': 844})
    fallback = nojs.new_page()
    fallback.goto(url)
    assert fallback.locator('.fallback').is_visible()
    assert fallback.locator('.fallback details').count() == len(manifest['entries'])
    fallback.locator('.fallback summary').first.click()
    assert fallback.locator('.fallback details').first.get_attribute('open') is not None
    fit(fallback)
    snap(fallback, 'no-javascript-mobile')
    nojs.close()
    record('JavaScript-disabled mobile fallback exposes all 46 real definitions')
    assert not errors, errors
    assert not requests, requests
    record('no uncaught browser errors or external requests in the exercised flows')
    version = browser.version
    browser.close()

receipt = {
    'scope': 'Source-backed local Chromium review consumer, not deployed or independently accepted',
    'source_commit': subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
    'browser': version,
    'fixture_only': False,
    'entries': len(manifest['entries']),
    'content_revision': manifest['content_revision'],
    'html_sha256': hashlib.sha256(pagefile.read_bytes()).hexdigest(),
    'checks': checks, 'screenshots': matrix,
    'errors': errors, 'external_requests': requests,
    'not_run': ['real Macro embedded-mode integration', 'independent review', 'production release'],
}
(OUT / 'qualification.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'checks_passed':len(checks),'entries':len(manifest['entries']),'receipt':str(OUT/'qualification.json')}), flush=True)
