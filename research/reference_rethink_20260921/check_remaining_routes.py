"""Continue independent route checks after a held native-focus assertion; never claim full PASS."""
from pathlib import Path
import hashlib
import json
import subprocess
from playwright.sync_api import sync_playwright
from render_shared_preview import compile_from_canonical_source
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'r3-realpath'
manifest = compile_from_canonical_source()
pagefile = OUT / 'guide.html'
url = pagefile.resolve().as_uri()
checks, errors = [], []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width':1440,'height':900})
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(url + '?q=regime')
    ids = page.locator('#result-list [data-entry-link]').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.entryLink)')
    page.locator('#result-list [data-entry-link]').first.click()
    title = page.locator('#app h1').inner_text()
    page.go_back()
    assert page.locator('#search').input_value() == 'regime'
    assert page.locator('#result-list [data-entry-link]').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.entryLink)') == ids
    page.go_forward()
    assert page.locator('#app h1').inner_text() == title
    checks.append('browser back/forward: exact query, membership and selected entry')
    page.goto(url + '#not-a-real-entry')
    assert page.locator('[data-missing-name]').inner_text() == 'not-a-real-entry'
    checks.append('unknown-link text preserves exact missing identity')
    page.goto(url + '?q=no-such-explanation')
    assert page.locator('#result-list article').count() == 0
    assert 'No matching explanation' in page.locator('#result-list').inner_text()
    checks.append('empty results are explicit with recovery')
    for width in [1440,390]:
        page.set_viewport_size({'width':width,'height':900 if width==1440 else 844})
        for language in ['en','zh']:
            query = '?lang=zh' if language == 'zh' else ''
            for entry in manifest['entries']:
                page.goto(url + query + '#' + entry['id'])
                assert page.locator('#app h1').inner_text() == entry['label'][language]
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    checks.append('46 real entries × 2 languages × 2 widths render without horizontal overflow')
    assert not errors, errors
    version = browser.version
    browser.close()
receipt = {'scope':'Independent remaining routes; prior native Tab assertion remains FAILED/UNRESOLVED',
    'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'browser':version,'fixture_only':False,'entries':len(manifest['entries']),
    'content_revision':manifest['content_revision'],'html_sha256':hashlib.sha256(pagefile.read_bytes()).hexdigest(),
    'checks_passed':checks,'browser_errors':errors,'full_qualification':'NOT_PASSED',
    'held_failure':'qualify_real_guide.py line 82: dialog contains document.activeElement after Tab; cause not yet adjudicated'}
(OUT/'remaining-routes.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt),flush=True)
