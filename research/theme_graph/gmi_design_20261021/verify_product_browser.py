"""Exercise generated public GMI pages in a fresh headless browser profile.

Usage: python verify_product_browser.py --site SITE --out PROOF --executable CHROME
No signed-in profile, publication, source data mutation, or service stub is used.
Clipboard outcome/timing, feedback-timer, receipt identity and malformed-payload
cases are explicit fault injections; they do not change published source records.
"""
import argparse
from datetime import datetime, timezone
import functools
import hashlib
import http.server
import json
from pathlib import Path
import re
import threading
import traceback
from urllib.parse import parse_qs, urlencode, urlsplit
from playwright.sync_api import sync_playwright, expect

parser = argparse.ArgumentParser()
parser.add_argument('--site', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--executable', required=True)
parser.add_argument('--case', default='', help='Run one named case after a bounded fix')
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=True)

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(args.site)))
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{server.server_port}'
report = {'scope': 'Generated public pages from current source model; existing shared shell. Live backend/release acceptance is separate.', 'cases': [], 'screenshots': [], 'page_errors': [], 'generated_at': datetime.now(timezone.utc).isoformat(), 'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.site.glob('gmi*')) if p.is_file()}}

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=args.executable, headless=True)
    report['browser'] = browser.version

    def context(width=1440, theme='dark', language='en', **kwargs):
        c = browser.new_context(viewport={'width': width, 'height': 1000 if width > 800 else 844}, device_scale_factor=1, **kwargs)
        c.add_init_script('localStorage.setItem("theme",'+json.dumps(theme)+');localStorage.setItem("lang",'+json.dumps(language)+');')
        return c

    def page_for(c, route='gmi.html'):
        p = c.new_page()
        p.on('pageerror', lambda e: report['page_errors'].append(str(e)))
        p.goto(base+'/'+route, wait_until='networkidle', timeout=45000)
        return p

    def check(name, action):
        if args.case and args.case != name:
            return
        try:
            action()
            report['cases'].append({'name': name, 'result': 'PASS'})
        except Exception as e:
            report['cases'].append({'name': name, 'result': 'FAIL', 'error': traceback.format_exc(limit=4)[-2400:]})
        print(json.dumps(report['cases'][-1]), flush=True)

    def matrix(width, theme, language):
        with context(width, theme, language) as c:
            p = page_for(c)
            expect(p.locator('html')).to_have_attribute('data-theme', theme)
            expect(p.locator('html')).to_have_attribute('data-lang', language)
            expect(p.locator('[data-gmi-ready]')).to_have_count(1)
            assert not p.evaluate('document.documentElement.scrollWidth > innerWidth')
            assert p.locator('h1').inner_text().strip()
            assert p.locator('[data-topic-connections] .gmi-evidence-card').count() == 1
            assert p.evaluate('getComputedStyle(document.querySelector(".gmi-action-primary")).borderRadius') != '0px'
            if language == 'zh':
                assert p.evaluate('getComputedStyle(document.querySelector("h1")).letterSpacing') in ('0px', 'normal')
            path = args.out / f'{width}-{theme}-{language}.png'
            p.screenshot(path=str(path), full_page=True)
            report['screenshots'].append(path.name)

    for width in (1440, 390):
        for theme in ('dark', 'light'):
            for language in ('en', 'zh'):
                check(f'visual-{width}-{theme}-{language}', lambda w=width,t=theme,l=language: matrix(w,t,l))

    def desktop_paths():
        with context() as c:
            p = page_for(c)
            data = p.locator('#gmi-topic-data').text_content()
            topics = json.loads(data)['topics']
            default_id = p.locator('[data-gmi-explorer]').get_attribute('data-default-theme')
            field = p.locator('[data-topic-search]')
            field.fill('Micron')
            p.locator('[data-evidence-only]').check()
            category_id = next(path[0]['id'] for t in topics if t['id'] == default_id for path in t['paths'] if 'Technology' in path[0]['en'])
            p.locator('[data-topic-category-filter]').select_option(category_id)
            assert p.locator('.gmi-topic-option:visible').count() == 1
            assert p.locator('[data-topic-category]').inner_text() == 'Technology & software'
            assert p.locator('.gmi-topic-option[tabindex="0"]:visible').count() == 1
            p.locator('[data-topic-reset]').first.click()
            assert p.locator('[data-topic-category]').inner_text() == 'Semiconductors & hardware'
            target = next(t for t in topics if t['tier'] == 'extended')
            field.fill(target['en'])
            p.locator('input[name="gmi-scope"][value="extended"]').check()
            p.locator('.gmi-topic-option[data-topic-select="'+target['id']+'"]').click()
            expect(p.locator('h1')).to_have_text(target['en'])
            assert 'theme=' in p.url and 'scope=extended' in p.url and 'q=' in p.url
            p.go_back()
            expect(p.locator('h1')).to_have_text(next(t['en'] for t in topics if t['id'] == default_id))
            expect(field).to_have_value(target['en'])
            p.go_forward()
            expect(p.locator('h1')).to_have_text(target['en'])
            assert p.locator('.gmi-topic-empty').is_visible()
            p.locator('[data-topic-reset]').first.click()
            p.locator('.gmi-related-topics [data-topic-select]').first.click()
            expect(p.locator('h1')).to_be_focused()
            p.locator('.gmi-advanced > summary').click()
            p.locator('[data-gmi-set-lens="chain"]').click()
            assert p.locator('html').get_attribute('data-gmi-lens') == 'chain'
            p.evaluate('location.hash="theme="+encodeURIComponent(document.querySelector("[data-gmi-explorer]").dataset.defaultTheme)')
            expect(p.locator('[data-gmi-set-lens="coverage"]')).to_have_attribute('aria-selected','true')
            assert p.locator('html').get_attribute('data-gmi-lens') == 'coverage'
            p.locator('#settings-open').click()
            p.locator('#set-theme-light').click()
            expect(p.locator('html')).to_have_attribute('data-theme','light')
            p.locator('.lang-toggle .zh-opt').click()
            expect(p.locator('html')).to_have_attribute('data-lang','zh')
            assert p.locator('[data-topic-category-filter] option').first.text_content() == '全部类别'
            assert p.locator('[data-topic-search]').get_attribute('aria-label') == '搜索主题、公司或产品'
    check('desktop-search-multiparent-history-keyboard-theme-language', desktop_paths)

    def mobile_paths():
        with context(390, 'light') as c:
            p = page_for(c)
            opener = p.locator('[data-browse-open]')
            opener.click()
            expect(p.locator('[data-browse-dialog]')).to_be_visible()
            expect(p.locator('[data-topic-search]')).to_be_focused()
            p.locator('[data-topic-search]').fill('cloud')
            p.keyboard.press('Escape')
            expect(p.locator('[data-topic-search]')).to_have_value('')
            assert p.locator('[data-browse-dialog]').is_visible()
            p.keyboard.press('Escape')
            expect(opener).to_be_focused()
            opener.click()
            p.locator('[data-topic-search]').fill('cloud')
            p.locator('.gmi-topic-option:visible').first.click()
            expect(p.locator('[data-browse-dialog]')).not_to_be_visible()
            expect(p.locator('h1')).to_be_focused()
            assert p.locator('[data-gmi-browse]').count() == 1
            assert p.locator('h1').bounding_box()['y'] >= 70
            p.screenshot(path=str(args.out/'mobile-selected-empty.png'), full_page=True)
            opener.click()
            p.locator('[data-topic-search]').fill('no-such-topic-78123')
            expect(p.locator('[data-topic-no-results]')).to_be_visible()
            p.screenshot(path=str(args.out/'mobile-search-no-results.png'), full_page=True)
            p.locator('[data-topic-no-results] [data-topic-reset]').click()
            assert p.locator('.gmi-topic-option:visible').count() == 371
            p.locator('[data-browse-close]').click()
            expect(opener).to_be_focused()
    check('mobile-dialog-search-empty-escape-focus', mobile_paths)

    def clipboard_paths():
        with context() as c:
            c.grant_permissions(['clipboard-read','clipboard-write'])
            p = page_for(c)
            p.locator('[data-gmi-copy]').click()
            expect(p.locator('[data-copy-label]')).to_have_text('Link copied')
            assert p.evaluate('navigator.clipboard.readText()') == p.url
            p.evaluate('() => { navigator.clipboard.writeText=()=>Promise.reject(new Error("test denial")); }')
            p.locator('[data-gmi-copy]').click()
            expect(p.locator('.gmi-copy-fallback')).to_be_visible()
            expect(p.locator('#gmi-share-url')).to_have_value(p.url)
            p.locator('.gmi-related-topics [data-topic-select]').first.click()
            expect(p.locator('.gmi-copy-fallback')).not_to_be_visible()
    check('clipboard-real-success-and-injected-denial', clipboard_paths)

    def secondary_paths():
        with context(390, 'light', 'zh', reduced_motion='reduce') as c:
            p = page_for(c, 'gmi-companies.html')
            p.locator('[data-company-search]').fill('not-a-company-78123')
            expect(p.locator('[data-company-empty]')).to_be_visible()
            p.locator('[data-company-reset]').click()
            p.locator('.gmi-company-card a[href*="gmi-issuer-"]').first.click()
            assert p.locator('.gmi-evidence-card').count() == 1
            assert p.locator('.gmi-source-link a').get_attribute('href').startswith('https://')
            p.screenshot(path=str(args.out/'mobile-company-zh.png'),full_page=True)
            p.goto(base+'/gmi-relationships.html',wait_until='networkidle')
            assert '暂无获准公开展示的关系' in p.locator('main').inner_text()
            assert not p.evaluate('document.documentElement.scrollWidth > innerWidth')
            p.screenshot(path=str(args.out/'mobile-publication-zh.png'),full_page=True)
            p.goto(base+'/gmi-index.html',wait_until='networkidle')
            assert p.locator('a.gmi-irow-name').count() == 371
            p.locator('input[data-gmi-filter="index"]').fill('HBM')
            p.locator('a.gmi-irow-name:visible').first.click()
            expect(p.locator('[data-gmi-ready]')).to_have_count(1)
    check('company-source-relationships-index-reduced-motion', secondary_paths)

    def shared_brain():
        for width in (1440, 390):
            language = 'zh' if width == 390 else 'en'
            with context(width, 'light' if width == 390 else 'dark', language) as c:
                p = page_for(c)
                boot = p.locator('#gmi-brain-slot #mmb-boot')
                expect(boot).to_be_visible()
                assert p.locator('#mmb-boot').count() == 1
                assert boot.bounding_box()['y'] < p.locator('h1').bounding_box()['y']
                boot.click()
                expect(p.locator('#mmb-panel')).to_have_class(__import__('re').compile(r'.*open.*'))
                expect(p.locator('#gmi-brain-slot #mmb-launch')).to_have_count(1)
                expect(p.locator('#mmb-panel:focus-within')).to_have_count(1)
                p.keyboard.press('Escape')
                expect(p.locator('#mmb-panel')).not_to_have_class(__import__('re').compile(r'.*open.*'))
                expect(p.locator('#gmi-brain-slot #mmb-launch')).to_be_focused()
                assert p.locator('#mmb-boot').count() == 0
                expect(p.locator('#gmi-brain-slot #mmb-root #mmb-launch')).to_have_count(1)
                live = p.locator('#mmb-launch')
                expect(live).to_have_attribute('aria-label', '问操盘大脑' if language == 'zh' else 'Ask Mastermind')
                palette = live.evaluate('(el) => { const s=getComputedStyle(el); return {token:s.getPropertyValue("--mmb-info"),color:s.backgroundColor,image:s.backgroundImage,font:s.fontFamily}; }')
                assert palette['token'].strip()
                assert 'Inter' in palette['font']
                assert palette['color'] != 'rgba(0, 0, 0, 0)' or palette['image'] != 'none'
                assert not p.evaluate('document.documentElement.scrollWidth > innerWidth')
                p.screenshot(path=str(args.out/f'brain-restored-{width}.png'), full_page=True)
    check('shared-brain-single-launcher-open-close-focus', shared_brain)

    def malformed_payload():
        original = (args.site / 'gmi.html').read_text()
        damaged = re.sub(r'(<script\b[^>]*id="gmi-topic-data"[^>]*>).*?(</script>)',
                         lambda m: m[1] + '{"topics":]' + m[2], original, flags=re.S)
        assert damaged != original
        with context(390, 'light', 'zh') as c:
            c.route('**/gmi.html', lambda route: route.fulfill(status=200, content_type='text/html', body=damaged))
            p = page_for(c)
            expect(p.locator('[data-topic-notice]')).to_be_visible()
            assert '交互研究未能加载' in p.locator('[data-topic-notice]').inner_text()
            assert p.locator('.gmi-evidence-card').count() == 1
            assert not p.locator('[data-browse-open]').is_visible()
            assert not p.locator('[data-gmi-copy]').is_visible()
            p.locator('.gmi-product-tools a[href*="gmi-index.html"]').click()
            expect(p.locator('a.gmi-irow-name')).to_have_count(371)
    check('malformed-payload-preserves-server-answer-and-index', malformed_payload)

    def return_journey(width, theme, language):
        with context(width, theme, language) as c:
            p = page_for(c)
            default_id = p.locator('[data-gmi-explorer]').get_attribute('data-default-theme')
            target = ('theme=' + default_id + '&q=Micron&category=theme:technology_software'
                      '&scope=core&evidence=1&lens=chain')
            p.goto(base+'/gmi.html#'+target, wait_until='networkidle')
            origin = parse_qs(urlsplit(p.url).fragment)
            evidence = p.locator('.gmi-evidence-actions .gmi-action-primary').first
            # A real href must carry context before activation, including new tabs.
            href = evidence.get_attribute('href')
            assert 'gmi_return=' in href
            other = c.new_page()
            other.on('pageerror', lambda e: report['page_errors'].append(str(e)))
            other.goto(href, wait_until='networkidle')
            back = other.locator('[data-gmi-return]')
            expect(back).to_have_text('返回主题研究' if language == 'zh' else 'Back to theme research')
            assert back.bounding_box()['height'] >= 44
            assert back.evaluate('(el) => parseFloat(getComputedStyle(el).opacity)') >= 1
            assert not other.evaluate('document.documentElement.scrollWidth > innerWidth')
            back.focus()
            other.keyboard.press('Tab')
            other.keyboard.press('Shift+Tab')
            expect(back).to_be_focused()
            assert back.evaluate('(el) => el.matches(":focus-visible")')
            name = f'return-{width}-{theme}-{language}.png'
            other.screenshot(path=str(args.out/name), full_page=True)
            report['screenshots'].append(name)
            other.keyboard.press('Enter')
            expect(other.locator('[data-gmi-ready]')).to_have_count(1)
            assert parse_qs(urlsplit(other.url).fragment) == origin
            if width == 390:
                other.locator('[data-browse-open]').click()
            expect(other.locator('[data-topic-search]')).to_have_value('Micron')
            expect(other.locator('[data-topic-category-filter]')).to_have_value('theme:technology_software')
            expect(other.locator('[data-evidence-only]')).to_be_checked()
            expect(other.locator('input[name="gmi-scope"][value="core"]')).to_be_checked()
            assert other.locator('.gmi-topic-option:visible').count() == 1
            assert other.locator('html').get_attribute('data-gmi-lens') == 'chain'
            other.close()
            # Preserve a company search and the upstream theme context on a second hop.
            p.locator('.gmi-product-tabs a').nth(1).click()
            p.locator('[data-company-search]').fill('Micron')
            p.reload(wait_until='networkidle')
            expect(p.locator('[data-company-search]')).to_have_value('Micron')
            catalog_origin = parse_qs(urlsplit(p.url).fragment)
            p.locator('.gmi-company-card a[href*="gmi-issuer-"]').first.click()
            expect(p.locator('[data-gmi-return]')).to_have_text('返回公司结果' if language == 'zh' else 'Back to company results')
            p.locator('[data-gmi-return]').click()
            expect(p.locator('[data-company-search]')).to_have_value('Micron')
            assert parse_qs(urlsplit(p.url).fragment) == catalog_origin
            p.locator('[data-gmi-return]').click()
            expect(p.locator('[data-gmi-ready]')).to_have_count(1)
            assert parse_qs(urlsplit(p.url).fragment) == origin
            # Lens controls use replaceState; contextual hrefs must update as well.
            p.locator('.gmi-advanced > summary').click()
            p.locator('[data-gmi-set-lens="coverage"]').click()
            href = p.locator('.gmi-evidence-actions .gmi-action-primary').first.get_attribute('href')
            return_value = parse_qs(urlsplit(href).fragment)['gmi_return'][0]
            assert parse_qs(urlsplit(return_value).fragment)['lens'] == ['coverage']

    for width in (1440, 390):
        for theme in ('dark', 'light'):
            for language in ('en', 'zh'):
                check(f'return-journey-{width}-{theme}-{language}',
                      lambda w=width,t=theme,l=language: return_journey(w,t,l))

    def secondary_research_return(width, theme, language):
        with context(width, theme, language) as c:
            p = page_for(c)
            topic = p.locator('[data-gmi-explorer]').get_attribute('data-default-theme')
            fragment = 'theme='+topic+'&q=Micron&scope=core&evidence=1&lens=chain'
            origin = parse_qs(fragment)
            for route in ('gmi-coverage.html', 'gmi-index.html', 'gmi-relationships.html'):
                p.goto(base+'/gmi.html#'+fragment, wait_until='networkidle')
                p.locator('main a[href*="'+route+'"]').first.click()
                back = p.locator('[data-gmi-return]')
                expect(back).to_be_visible()
                expect(back).to_have_text('返回主题研究' if language == 'zh' else 'Back to theme research')
                assert back.bounding_box()['height'] >= 44
                assert parse_qs(urlsplit(back.get_attribute('href')).fragment) == origin
                assert not p.evaluate('document.documentElement.scrollWidth > innerWidth')
                if route == 'gmi-coverage.html':
                    name = f'secondary-return-{width}-{theme}-{language}.png'
                    p.screenshot(path=str(args.out/name), full_page=True)
                    report['screenshots'].append(name)
                back.focus()
                p.keyboard.press('Enter')
                expect(p.locator('[data-gmi-ready]')).to_have_count(1)
                assert parse_qs(urlsplit(p.url).fragment) == origin

    def company_results_source_context(width, theme, language):
        with context(width, theme, language) as c:
            p = page_for(c, 'gmi-companies.html')
            card = p.locator('.gmi-company-card').first
            expect(card).to_be_visible()
            assert ('2024年2月26日' if language == 'zh' else '26 Feb 2024') in card.inner_text()
            assert ('计划中' if language == 'zh' else 'Planned') in card.inner_text()
            source = card.locator('a[target="_blank"]').first
            assert source.get_attribute('href').startswith('https://')
            assert 'noopener' in source.get_attribute('rel')
            expect(p.locator('[data-company-guide]')).to_be_visible()
            assert not p.evaluate('document.documentElement.scrollWidth > innerWidth')
            name = f'company-results-{width}-{theme}-{language}.png'
            p.screenshot(path=str(args.out/name), full_page=True)
            report['screenshots'].append(name)
            search = p.locator('[data-company-search]')
            search.fill('NO-MATCH-EXPECTED')
            expect(p.locator('[data-company-card]:visible')).to_have_count(0)
            expect(p.locator('[data-company-empty]')).to_be_visible()
            p.locator('[data-company-reset]').click()
            expect(search).to_be_focused()
            expect(card).to_be_visible()

    def index_saved_search(width):
        with context(width, 'light', 'zh') as c:
            p = page_for(c, 'gmi-index.html#open=all')
            search = p.locator('input[data-gmi-filter="index"]')
            search.fill('HBM')
            expect(p).to_have_url(re.compile(r'[&#]q=HBM(?:&|$)'))
            assert parse_qs(urlsplit(p.url).fragment).get('q') == ['HBM']
            assert parse_qs(urlsplit(p.url).fragment).get('open') == ['all']
            p.reload(wait_until='networkidle')
            expect(search).to_have_value('HBM')
            assert p.locator('a.gmi-irow-name:visible').count() > 0
            search.press('Escape')
            expect(search).to_have_value('')
            expect(p).not_to_have_url(re.compile(r'[&#]q='))
            assert 'q' not in parse_qs(urlsplit(p.url).fragment)
            assert parse_qs(urlsplit(p.url).fragment).get('open') == ['all']
            assert p.locator('a.gmi-irow-name:visible').count() == 371

    for width in (1440, 390):
        for theme in ('dark', 'light'):
            for language in ('en', 'zh'):
                check(f'secondary-research-return-{width}-{theme}-{language}',
                      lambda w=width,t=theme,l=language: secondary_research_return(w,t,l))
                check(f'company-results-source-context-{width}-{theme}-{language}',
                      lambda w=width,t=theme,l=language: company_results_source_context(w,t,l))
        check(f'index-saved-search-{width}', lambda w=width: index_saved_search(w))

    def incomplete_payloads():
        original = (args.site / 'gmi.html').read_text()
        pattern = r'(<script\b[^>]*id="gmi-topic-data"[^>]*>).*?(</script>)'
        payload = json.loads(re.search(pattern, original, re.S)[0].split('>', 1)[1].rsplit('</script>', 1)[0])
        cases = ('categories', 'paths', 'connections', 'source', 'duplicate-id', 'default-id', 'category-label', 'parent')
        with context(390, 'light', 'zh') as c:
            for defect in cases:
                data = json.loads(json.dumps(payload))
                selected = next(t for t in data['topics'] if t['connections'])
                if defect == 'categories':
                    data.pop('categories')
                elif defect in ('paths', 'connections'):
                    selected[defect] = None
                elif defect == 'source':
                    selected['connections'][0]['source'] = None
                elif defect == 'duplicate-id':
                    data['topics'].append(data['topics'][0])
                elif defect == 'default-id':
                    data['topics'].remove(selected)
                elif defect == 'category-label':
                    data['categories'][selected['category']] = None
                elif defect == 'parent':
                    selected['parent'] = 'missing-category'
                damaged = re.sub(pattern, lambda m: m[1]+json.dumps(data)+m[2], original, flags=re.S)
                c.route('**/gmi.html', lambda route: route.fulfill(status=200, content_type='text/html', body=damaged))
                p = page_for(c)
                expect(p.locator('[data-topic-notice]')).to_be_visible()
                assert '交互研究未能加载' in p.locator('[data-topic-notice]').inner_text(), defect
                assert p.locator('.gmi-evidence-card').count() == 1, defect
                expect(p.locator('[data-gmi-ready]')).to_have_count(0)
                assert not p.locator('[data-browse-open]').is_visible()
                assert not p.locator('[data-gmi-copy]').is_visible()
                if defect == 'categories':
                    p.locator('#settings-open').click()
                    p.locator('.lang-toggle .en-opt').click()
                    expect(p.locator('[data-topic-notice]')).to_contain_text('Interactive research could not load')
                    p.keyboard.press('Escape')
                    name = 'incomplete-payload-recovery.png'
                    p.screenshot(path=str(args.out/name), full_page=True)
                    report['screenshots'].append(name)
                p.close()
                c.unroute('**/gmi.html')
            p = page_for(c, 'gmi-index.html')
            expect(p.locator('a.gmi-irow-name')).to_have_count(371)
    check('incomplete-payloads-preserve-server-answer-and-index', incomplete_payloads)

    def return_boundary():
        rejected = ('https://example.invalid/', '//example.invalid/', 'javascript:alert(1)',
                    '../gmi.html#theme=wrong', 'gmi.html?token=private', 'gmi.html/extra',
                    'gmi.html#q='+'a'*5000, 'gmi-issuer-mu.html', 'data:text/html,x')
        with context() as c:
            for value in rejected:
                p = page_for(c, 'gmi-issuer-mu.html#'+urlencode({'gmi_return': value}))
                expect(p.locator('[data-gmi-return]')).to_have_count(0)
                assert p.locator('.gmi-product-tabs a').first.get_attribute('href') == 'gmi.html'
                p.close()
            value = 'gmi.html#theme=theme:hbm_packaging&q='+('a'*250)+'&scope=bogus&unknown=secret&lens=chain'
            p = page_for(c, 'gmi-issuer-mu.html#'+urlencode({'gmi_return': value}))
            back = p.locator('[data-gmi-return]')
            expect(back).to_be_visible()
            href = back.get_attribute('href')
            assert urlsplit(href).netloc == urlsplit(base).netloc
            returned = parse_qs(urlsplit(href).fragment)
            assert set(returned) == {'theme', 'q', 'lens'}
            assert len(returned['q'][0]) == 200
            p.evaluate('location.hash="gmi_return="+encodeURIComponent("https://example.invalid/")')
            expect(back).to_have_count(0)
            assert p.locator('.gmi-product-tabs a').first.get_attribute('href') == 'gmi.html'
    check('return-context-is-bounded-local-and-whitelisted', return_boundary)

    def interaction_captures():
        for theme in ('dark', 'light'):
            with context(1440, theme, 'en') as c:
                p = page_for(c)
                action = p.locator('.gmi-evidence-actions .gmi-action-primary').first
                action.hover()
                name = f'1440-{theme}-en-hover.png'
                p.screenshot(path=str(args.out/name), full_page=True)
                report['screenshots'].append(name)
                p.mouse.move(0, 0)
                action.focus()
                p.keyboard.press('Tab')
                p.keyboard.press('Shift+Tab')
                expect(action).to_be_focused()
                assert action.evaluate('(el) => el.matches(":focus-visible")')
                name = f'1440-{theme}-en-focus.png'
                p.screenshot(path=str(args.out/name), full_page=True)
                report['screenshots'].append(name)
    check('visual-interaction-hover-and-keyboard-focus', interaction_captures)

    def secondary_matrix(route, width, theme, language):
        with context(width, theme, language) as c:
            p = page_for(c, route)
            expect(p.locator('html')).to_have_attribute('data-theme', theme)
            expect(p.locator('html')).to_have_attribute('data-lang', language)
            assert p.locator('h1').count() == 1
            assert p.locator('h1').inner_text().strip()
            assert not p.evaluate('document.documentElement.scrollWidth > innerWidth'), route
            name = f'{route[:-5]}-{width}-{theme}-{language}.png'
            # Long indexes use an initial viewport capture; full-document horizontal
            # geometry is still checked, and every index target is covered by pytest.
            full = p.evaluate('document.documentElement.scrollHeight < 5000')
            p.screenshot(path=str(args.out/name), full_page=full)
            report['screenshots'].append(name)

    for route in ('gmi-companies.html', 'gmi-issuer-mu.html', 'gmi-relationships.html',
                  'gmi-coverage.html', 'gmi-states.html', 'gmi-index.html'):
        for width in (1440, 390):
            for theme in ('dark', 'light'):
                for language in ('en', 'zh'):
                    check(f'visual-{route}-{width}-{theme}-{language}',
                          lambda r=route,w=width,t=theme,l=language: secondary_matrix(r,w,t,l))

    def no_script():
        with browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844}) as c:
            p = page_for(c)
            assert p.locator('.gmi-evidence-card').count() == 1
            assert not p.locator('[data-browse-open]').is_visible()
            assert p.locator('.gmi-product-tools a[href*="gmi-index.html"]').is_visible()
    check('server-answer-without-javascript', no_script)
    def locale_receipts(width):
        """Synthetic multi-record faults exercise the existing locale/render owner.
    
        These clones never enter generated product output or public admission. The
        shared language controller is unchanged; its data-lang notification is the
        explicit input under test. Fresh contexts prevent retained state between cases.
        """
        original = (args.site/'gmi.html').read_text()
        pattern = r'(<script\b[^>]*id="gmi-topic-data"[^>]*>).*?(</script>)'
        payload = json.loads(re.search(pattern, original, flags=re.S)[0].split('>', 1)[1].rsplit('</script>', 1)[0])
        selected_id = re.search(r'data-default-theme="([^"]+)"', original)[1]
        alternate_id = next(t['id'] for t in payload['topics'] if t['id'] != selected_id)
        initial = next(t for t in payload['topics'] if t['id'] == selected_id)['connections'][0]
    
        def fixture(initial_fault=None):
            data = json.loads(json.dumps(payload))
            theme = next(t for t in data['topics'] if t['id'] == selected_id)
            theme['connections'] = []
            for i in range(3):
                record = json.loads(json.dumps(initial))
                record['receipt'] = 'fixture:receipt-'+str(i+1)
                record['source']['key'] = 'fixture:source-'+str(i+1)
                record['source']['sha256'] = str(i+1)*64
                theme['connections'].append(record)
            if initial_fault == 'duplicate':
                theme['connections'][1]['receipt'] = theme['connections'][0]['receipt']
            elif initial_fault == 'missing':
                theme['connections'][0]['source']['sha256'] = None
            return re.sub(pattern, lambda m: m[1]+json.dumps(data).replace('<', '\\u003c')+m[2], original, flags=re.S)
    
        def open_page(c, initial_fault=None):
            body = fixture(initial_fault)
            c.add_init_script('''const originalParse = JSON.parse;
              JSON.parse = function(text, ...rest) {
                const value = originalParse.call(this, text, ...rest);
                if (value && Array.isArray(value.topics) && value.categories) window.__gmiReceiptFixture = value;
                return value;
              };''')
            c.route('**/gmi.html', lambda route: route.fulfill(status=200, content_type='text/html', body=body))
            p = page_for(c)
            expect(p.locator('[data-gmi-ready]')).to_have_count(1)
            expect(p.locator('[data-topic-connections] .gmi-evidence-card')).to_have_count(3)
            return p
    
        def cards(p):
            return p.locator('[data-topic-connections] .gmi-evidence-card')
    
        def opens(p):
            return p.locator('[data-topic-connections] .gmi-evidence-receipt').evaluate_all('(nodes) => nodes.map(n => ({record:n.querySelector("dd").textContent, open:n.open}))')
    
        def change(p, mutation='', language='zh'):
            p.evaluate('''([id, mutation, language]) => {
              const theme = window.__gmiReceiptFixture.topics.find(t => t.id === id);
              if (mutation) new Function('theme', mutation)(theme);
              document.documentElement.setAttribute('data-lang', language);
            }''', [selected_id, mutation, language])
            # One animation frame observes the completed synchronous mutation handler.
            p.evaluate('() => new Promise(resolve => requestAnimationFrame(() => resolve()))')
    
        with context(width) as c:
            p = open_page(c)
            cards(p).nth(0).locator('summary').click()
            cards(p).nth(1).locator('summary').click()
            cards(p).nth(1).locator('summary').focus()
            before = p.url
            change(p, 'theme.connections = [theme.connections[2], theme.connections[0], theme.connections[1]];')
            assert opens(p) == [{'record':'fixture:receipt-3','open':False},{'record':'fixture:receipt-1','open':True},{'record':'fixture:receipt-2','open':True}]
            expect(cards(p).nth(2).locator('summary')).to_be_focused()
            expect(cards(p).nth(2).locator('summary')).to_contain_text('来源凭证')
            change(p, language='en')
            assert [x['open'] for x in opens(p)] == [False, True, True]
            expect(cards(p).nth(2).locator('summary')).to_be_focused()
            assert p.url == before
            # A genuine theme/history transition does not reuse a locale capture.
            p.evaluate('(id) => { const q=new URLSearchParams(location.hash.slice(1)); q.set("theme",id); location.hash=q.toString(); }', alternate_id)
            expect(p.locator('#gmi-topic-title')).not_to_have_text('HBM & advanced packaging')
            p.go_back()
            expect(cards(p)).to_have_count(3)
            assert all(not x['open'] for x in opens(p))
    
        mutations = {
            'source-key': 'theme.connections[0].source.key += ":changed";',
            'source-hash': 'theme.connections[0].source.sha256 = "d".repeat(64);',
            'missing-hash': 'theme.connections[0].source.sha256 = null;',
            'missing-receipt': 'theme.connections[0].receipt = null;',
            'withdrawn': 'theme.connections.shift();',
            'duplicate-record': 'theme.connections[1].receipt = theme.connections[0].receipt;',
        }
        for name, mutation in mutations.items():
            with context(width) as c:
                p = open_page(c)
                cards(p).nth(0).locator('summary').click()
                cards(p).nth(0).locator('summary').focus()
                change(p, mutation)
                assert all(not x['open'] for x in opens(p)), name
                expect(p.locator('#gmi-topic-title')).to_be_focused()
    
        for fault in ('duplicate', 'missing'):
            with context(width) as c:
                p = open_page(c, fault)
                cards(p).nth(0).locator('summary').click()
                if fault == 'duplicate':
                    cards(p).nth(1).locator('summary').click()
                cards(p).nth(0).locator('summary').focus()
                change(p)
                assert all(not x['open'] for x in opens(p)), fault
                expect(p.locator('#gmi-topic-title')).to_be_focused()
    
        for selector, mutation in (
            ('.gmi-source-link a', ''),
            ('.gmi-action-primary', ''),
            ('.gmi-source-link a', 'theme.connections[0].source.url = "https://example.test/changed?x=1#receipt";'),
            ('.gmi-source-link a', 'theme.connections[0].source.url = null;'),
            ('.gmi-action-primary', 'theme.connections[0].href = "gmi-issuer-fixture.html";'),
        ):
            with context(width) as c:
                p = open_page(c)
                cards(p).nth(0).locator('summary').click()
                action = cards(p).nth(0).locator(selector)
                action.focus()
                destination = action.get_attribute('href')
                change(p, mutation)
                assert opens(p)[0]['open']
                if mutation:
                    expect(cards(p).nth(0).locator('summary')).to_be_focused()
                else:
                    expect(cards(p).nth(0).locator(selector)).to_be_focused()
                    assert cards(p).nth(0).locator(selector).get_attribute('href') == destination
    
        with context(width) as c:
            p = open_page(c)
            cards(p).nth(0).locator('summary').click()
            # A surviving control keeps focus; language cannot steal it into a card.
            p.locator('[data-gmi-copy]').focus()
            change(p)
            expect(p.locator('[data-gmi-copy]')).to_be_focused()
            assert opens(p)[0]['open']
    
        with context(width) as c:
            p = open_page(c)
            cards(p).nth(0).locator('summary').focus()
            # If another owner deliberately moves focus during rendering, respect it.
            p.evaluate('''() => {
              const node=document.querySelector('[data-topic-connections]');
              const replace=node.replaceChildren.bind(node);
              node.replaceChildren=(...children) => {replace(...children);document.querySelector('[data-gmi-copy]').focus();};
            }''')
            change(p)
            expect(p.locator('[data-gmi-copy]')).to_be_focused()
    
    for width in (1440, 390):
        check(f'locale-receipt-state-{width}', lambda w=width: locale_receipts(w))

    def clipboard_context_paths(width):
        """Deferred browser callbacks must never publish feedback on another view.

        The clipboard and its 2500 ms feedback timer are explicit fault injections.
        No writes reach the operating system clipboard. Other timers remain native.
        Selection, filtering, lens buttons and history use the existing page owners.
        """
        original = (args.site/'gmi.html').read_text()
        pattern = r'(<script\b[^>]*id="gmi-topic-data"[^>]*>).*?(</script>)'
        data = json.loads(re.search(pattern, original, flags=re.S)[0].split('>', 1)[1].rsplit('</script>', 1)[0])
        selected = re.search(r'data-default-theme="([^"]+)"', original)[1]
        other = next(t['id'] for t in data['topics'] if t['id'] != selected and t['tier'] == 'core')
        names = {t['id']: t['en'] for t in data['topics']}

        def open_page(c):
            c.add_init_script('''(() => {
              const f=window.__gmiCopyFixture={writes:[],timers:[]};
              Object.defineProperty(navigator,'clipboard',{configurable:true,value:{
                writeText(url){return new Promise((resolve,reject)=>f.writes.push({url,resolve,reject}));}
              }});
              const set=window.setTimeout.bind(window),clear=window.clearTimeout.bind(window);
              window.setTimeout=(callback,delay,...rest)=>{
                if(delay!==2500)return set(callback,delay,...rest);
                const timer={id:-(f.timers.length+1),callback:()=>callback(...rest),cancelled:false};
                f.timers.push(timer);return timer.id;
              };
              window.clearTimeout=(id)=>{
                const timer=f.timers.find(t=>t.id===id);
                if(timer)timer.cancelled=true;else clear(id);
              };
            })();''')
            c.route('**/gmi.html*', lambda route: route.fulfill(status=200, content_type='text/html', body=original))
            p = page_for(c, 'gmi.html?fixture=copy&return=one%20two')
            expect(p.locator('[data-gmi-ready]')).to_have_count(1)
            return p

        def frame(p):
            p.evaluate('() => new Promise(resolve => requestAnimationFrame(() => resolve()))')

        def copy(p):
            p.locator('[data-gmi-copy]').click()
            return p.evaluate('window.__gmiCopyFixture.writes.at(-1).url')

        def settle(p, index=0, success=True):
            p.evaluate('''([i,success])=>{
              const write=window.__gmiCopyFixture.writes[i];
              success?write.resolve():write.reject(new Error('fixture clipboard denial'));
            }''', [index, success])
            frame(p)

        def select(p, identifier):
            if width <= 820:
                p.locator('[data-browse-open]').click()
            p.locator('[data-topic-results] [data-topic-select="'+identifier+'"]').click()
            expect(p.locator('#gmi-topic-title')).to_have_text(names[identifier])
            frame(p)

        def search(p, query):
            if width <= 820:
                p.locator('[data-browse-open]').click()
            p.locator('[data-topic-search]').fill(query)
            if width <= 820:
                p.locator('[data-browse-close]').click()
            frame(p)

        def idle(p):
            expect(p.locator('[data-copy-label]')).to_have_text('Copy link')
            expect(p.locator('[data-gmi-copy]')).to_be_enabled()
            expect(p.locator('.gmi-copy-fallback')).not_to_be_visible()
            expect(p.locator('#gmi-share-url')).to_have_value('')

        def lens(p, value):
            disclosure=p.locator('.gmi-advanced')
            if disclosure.count() and not disclosure.get_attribute('open'):
                # Native details.open distinguishes the empty open attribute from closed.
                if not disclosure.evaluate('(node)=>node.open'):
                    disclosure.locator(':scope > summary').click()
            p.locator('[data-gmi-set-lens="'+value+'"]').click()
            frame(p)

        # Both outcomes of the old write are quarantined after an actual row selection.
        for success in (True, False):
            with context(width) as c:
                p=open_page(c)
                attempted=copy(p)
                select(p,other)
                p.locator('#gmi-topic-title').focus()
                before=p.locator('[data-gmi-announcement]').text_content()
                settle(p,success=success)
                idle(p)
                expect(p.locator('#gmi-topic-title')).to_be_focused()
                assert p.locator('[data-gmi-announcement]').text_content()==before
                assert p.evaluate('window.__gmiCopyFixture.writes[0].url')==attempted
                assert attempted!=p.url

        # A return to the same URL is a new visit; URL equality cannot revive the write.
        with context(width) as c:
            p=open_page(c)
            attempted=copy(p)
            select(p,other)
            select(p,selected)
            assert p.url==attempted
            settle(p)
            idle(p)

        # An older finally must not enable the button owned by a newer pending action.
        for success in (True, False):
            with context(width) as c:
                p=open_page(c)
                copy(p)
                select(p,other)
                new_url=copy(p)
                settle(p,success=success)
                expect(p.locator('[data-gmi-copy]')).to_be_disabled()
                expect(p.locator('[data-copy-label]')).to_have_text('Copying…')
                expect(p.locator('.gmi-copy-fallback')).not_to_be_visible()
                settle(p,1)
                expect(p.locator('[data-copy-label]')).to_have_text('Link copied')
                assert p.evaluate('window.__gmiCopyFixture.writes[1].url')==new_url==p.url

        # Filter-only URL changes and an ABA filter sequence also retire the action.
        for reverse in (False, True):
            with context(width) as c:
                p=open_page(c)
                attempted=copy(p)
                search(p,'Micron')
                assert 'q=Micron' in p.url
                if reverse:
                    search(p,'')
                    assert p.url==attempted
                settle(p,success=reverse)
                idle(p)

        # Actual Back/Forward plus a same-URL history entry must retire pending work.
        with context(width) as c:
            p=open_page(c)
            select(p,other)
            copy(p)
            p.go_back()
            expect(p.locator('#gmi-topic-title')).to_have_text(names[selected])
            settle(p)
            idle(p)
            p.go_forward()
            expect(p.locator('#gmi-topic-title')).to_have_text(names[other])
            idle(p)
        with context(width) as c:
            p=open_page(c)
            copy(p)
            p.evaluate('history.pushState({fixture:true},"",location.href)')
            p.go_back()
            frame(p)
            settle(p,success=False)
            idle(p)

        # The lens owner uses replaceState, including changes batched with language.
        with context(width) as c:
            p=open_page(c)
            lens(p,'coverage')
            attempted=copy(p)
            lens(p,'chain')
            lens(p,'coverage')
            assert p.url==attempted
            settle(p)
            idle(p)
        for success in (True, False):
            with context(width) as c:
                p=open_page(c)
                copy(p)
                settle(p,success=success)
                lens(p,'chain')
                idle(p)
        with context(width) as c:
            p=open_page(c)
            copy(p)
            p.evaluate('''()=>{
              document.querySelector('[data-gmi-set-lens="chain"]').click();
              document.documentElement.setAttribute('data-lang','zh');
            }''')
            frame(p)
            settle(p)
            expect(p.locator('[data-copy-label]')).to_have_text('复制链接')
            expect(p.locator('.gmi-copy-fallback')).not_to_be_visible()
            expect(p.locator('[data-gmi-copy]')).to_be_enabled()

        # Timers belong to the action that installed them, even if a stale callback runs.
        with context(width) as c:
            p=open_page(c)
            copy(p)
            settle(p)
            copy(p)
            assert p.evaluate('window.__gmiCopyFixture.timers[0].cancelled')
            p.evaluate('window.__gmiCopyFixture.timers[0].callback()')
            expect(p.locator('[data-copy-label]')).to_have_text('Copying…')
            expect(p.locator('[data-gmi-copy]')).to_be_disabled()
            settle(p,1)
            p.evaluate('window.__gmiCopyFixture.timers[0].callback()')
            expect(p.locator('[data-copy-label]')).to_have_text('Link copied')
            # An unrelated existing announcement cannot be cleared by copy expiry.
            p.locator('[data-gmi-announcement]').evaluate('(node)=>node.textContent="fixture other owner"')
            p.evaluate('window.__gmiCopyFixture.timers[1].callback()')
            idle(p)
            expect(p.locator('[data-gmi-announcement]')).to_have_text('fixture other owner')

        # Current failures expose the captured full URL; user focus wins over recovery.
        for moved_focus in ('none', 'heading', 'body', 'pointer'):
            with context(width) as c:
                p=open_page(c)
                attempted=copy(p)
                if moved_focus in ('heading', 'body'):
                    p.locator('#gmi-topic-title').focus()
                if moved_focus == 'body':
                    p.locator('#gmi-topic-title').evaluate('(node)=>node.blur()')
                if moved_focus == 'pointer':
                    p.locator('[data-topic-description]').click()
                settle(p,success=False)
                expect(p.locator('.gmi-copy-fallback')).to_be_visible()
                expect(p.locator('#gmi-share-url')).to_have_value(attempted)
                assert '?fixture=copy&return=one%20two#theme=' in attempted
                if moved_focus == 'heading':
                    expect(p.locator('#gmi-topic-title')).to_be_focused()
                elif moved_focus in ('body', 'pointer'):
                    assert p.evaluate('document.activeElement===document.body')
                else:
                    expect(p.locator('#gmi-share-url')).to_be_focused()
                    assert p.locator('#gmi-share-url').evaluate('(n)=>n.selectionStart===0&&n.selectionEnd===n.value.length')
                p.locator('[data-copy-close]').click()
                idle(p)
                expect(p.locator('[data-gmi-copy]')).to_be_focused()

        # Locale-only changes preserve this URL's attempt and existing receipt state.
        with context(width) as c:
            p=open_page(c)
            summary=p.locator('[data-topic-connections] .gmi-evidence-receipt summary').first
            summary.click()
            attempted=copy(p)
            summary.focus()
            p.evaluate('document.documentElement.setAttribute("data-lang","zh")')
            frame(p)
            expect(summary).to_be_focused()
            assert summary.locator('..').evaluate('(n)=>n.open')
            expect(p.locator('[data-copy-label]')).to_have_text('正在复制…')
            settle(p)
            expect(p.locator('[data-copy-label]')).to_have_text('链接已复制')
            expect(p.locator('[data-gmi-announcement]')).to_have_text('链接已复制到剪贴板。')
            assert attempted==p.url
        with context(width) as c:
            p=open_page(c)
            attempted=copy(p)
            settle(p,success=False)
            p.evaluate('document.documentElement.setAttribute("data-lang","zh")')
            frame(p)
            expect(p.locator('#gmi-share-url')).to_be_focused()
            expect(p.locator('#gmi-share-url')).to_have_value(attempted)
            expect(p.locator('[data-gmi-announcement]')).to_have_text('暂无法自动复制。请选择并复制所显示的地址。')
            # Context retirement moves focus off a fallback that is about to be hidden.
            p.evaluate('(id)=>{location.hash="theme="+encodeURIComponent(id);}',other)
            frame(p)
            expect(p.locator('[data-gmi-copy]')).to_be_focused()
            expect(p.locator('.gmi-copy-fallback')).not_to_be_visible()

        # This injected lifecycle event verifies retirement, not actual BFCache support.
        with context(width) as c:
            p=open_page(c)
            copy(p)
            p.evaluate('window.dispatchEvent(new PageTransitionEvent("pagehide",{persisted:true}))')
            settle(p)
            idle(p)


    for width in (1440, 390):
        check(f'clipboard-context-races-{width}', lambda w=width: clipboard_context_paths(w))

    def gmi_navigation_fit(p, width, language):
        values=p.locator('.gmi-product-tabs > a').evaluate_all('(nodes)=>nodes.map(n=>{const r=n.getBoundingClientRect();return {text:n.innerText,left:r.left,right:r.right,height:r.height};})')
        assert all(v['left']>=0 and v['right']<=width+0.1 and v['height']>=44 for v in values)
        assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
        report.setdefault('navigation_geometry',[]).append({'width':width,'language':language,'route':urlsplit(p.url).path,'targets':values})


    def taxonomy_keyboard_activation(width, language):
        """Actual generated tree wrappers delegate to the existing topic selection owner."""
        route = 'gmi.html?fixture=keyboard#'+urlencode({'lens':'chain','open':'all','gmi_return':'gmi-companies.html#q=Micron'})
        for key in ('Enter', 'Space'):
            with context(width, 'light', language, reduced_motion='reduce') as c:
                p = page_for(c, route)
                expect(p.locator('[data-gmi-ready]')).to_have_count(1)
                topics = json.loads(p.locator('#gmi-topic-data').text_content())['topics']
                topic = next(t for t in topics if t['id']=='theme:conventional_dram')
                advanced = p.locator('.gmi-advanced')
                advanced.locator(':scope > summary').click()
                parent = p.locator('.gmi-tree [role="treeitem"][aria-expanded]').first
                before = parent.get_attribute('aria-expanded')
                original_url = p.url
                parent.focus(); p.keyboard.press('Enter')
                assert parent.get_attribute('aria-expanded') != before
                p.keyboard.press('Space')
                assert parent.get_attribute('aria-expanded') == before
                assert p.url == original_url
                p.locator('input[data-gmi-filter="tree"]').fill(topic['en'])
                rows = p.locator('.gmi-tree [role="treeitem"]:visible')
                rows.first.focus()
                leaf = p.locator('.gmi-tree [role="treeitem"]').filter(has=p.locator('a[data-topic-select="'+topic['id']+'"]')).first
                for _ in range(rows.count()):
                    if leaf.evaluate('(n)=>n===document.activeElement'):
                        break
                    p.keyboard.press('ArrowDown')
                expect(leaf).to_be_focused()
                initial_length = p.evaluate('history.length')
                initial_url = p.url
                # Explicit keyboard faults: modified/IME input stays with its native owner.
                for modifier in ('ctrlKey','metaKey','altKey','shiftKey','isComposing'):
                    outcome = leaf.evaluate('''(n,modifier)=>{
                      const e=new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true,[modifier]:true});
                      n.dispatchEvent(e);return {prevented:e.defaultPrevented,url:location.href};
                    }''',modifier)
                    assert not outcome['prevented'] and outcome['url']==initial_url, modifier
                # A held Space must be cancelled without selecting or scrolling again.
                repeated = leaf.evaluate('''n=>{
                  const e=new KeyboardEvent('keydown',{key:' ',repeat:true,bubbles:true,cancelable:true});
                  n.dispatchEvent(e);return e.defaultPrevented;
                }''')
                # The baseline deliberately reaches the user-facing activation falsifier first.
                p.keyboard.press(key)
                expect(p.locator('#gmi-topic-title')).to_have_text(topic[language],timeout=1500)
                expect(p.locator('#gmi-topic-title')).to_be_focused()
                assert repeated
                assert p.evaluate('history.length') == initial_length+1
                params = parse_qs(urlsplit(p.url).fragment)
                assert params['theme']==[topic['id']]
                assert params['lens']==['chain'] and params['open']==['all']
                assert params['gmi_return']==['gmi-companies.html#q=Micron']
                assert urlsplit(p.url).query=='fixture=keyboard'
                # A native Enter on the nested anchor must not be converted into a second click.
                other = next(t for t in topics if t['id']=='theme:hbm_packaging')
                p.locator('input[data-gmi-filter="tree"]').fill(other['en'])
                anchor = p.locator('.gmi-tree a[data-topic-select="'+other['id']+'"]:visible').first
                anchor.focus(); prior = p.evaluate('history.length'); p.keyboard.press('Enter')
                expect(p.locator('#gmi-topic-title')).to_have_text(other[language])
                assert p.evaluate('history.length') == prior+1
                # An explicitly empty wrapper acquires no fabricated destination.
                result = p.evaluate('''()=>{
                  const tree=document.querySelector('.gmi-tree'),row=document.createElement('div');
                  row.setAttribute('role','treeitem');row.tabIndex=-1;row.textContent='Empty category fixture';tree.append(row);
                  const before=location.href;
                  const e=new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true});row.dispatchEvent(e);
                  const result={unchanged:before===location.href,prevented:e.defaultPrevented};row.remove();return result;
                }''')
                assert result=={'unchanged':True,'prevented':False}
                gmi_navigation_fit(p,width,language)


    def index_filtered_shortcuts(width, language):
        """Search, focus and queued intersection entries share the existing index groups."""
        with context(width, 'light', language, reduced_motion='reduce') as c:
            # Keep native observation; retain callbacks only to exercise a queued stale entry.
            c.add_init_script('''(()=>{
              const Native=window.IntersectionObserver;window.__gmiJumpObservers=[];
              window.IntersectionObserver=class extends Native {
                constructor(callback,options){super(callback,options);
                  if(options&&options.rootMargin==='-60px 0px -70% 0px')window.__gmiJumpObservers.push(callback);
                }
              };
            })();''')
            route = 'gmi-index.html?fixture=keyboard#'+urlencode({'open':'all','lens':'chain','gmi_return':'gmi.html#theme=theme:hbm_packaging&q=Micron'})
            p = page_for(c, route)
            search = p.locator('input[data-gmi-filter="index"]')
            nav = p.locator('.gmi-jump')
            energy = p.locator('.gmi-jump a[href="#energy_power"]')
            semiconductor = p.locator('.gmi-jump a[href="#semiconductors_hardware"]')
            total = p.locator('.gmi-jump a').count()
            picker=p.locator('[data-gmi-category-picker]');go=p.locator('[data-gmi-category-go]')
            def jump(link):
                if width<=640:
                    picker.select_option(link.get_attribute('href')[1:]);go.click()
                else:link.click()
            def available_shortcuts():
                return p.locator('.gmi-jump a:not([hidden])').count()
            totals = p.locator('[data-gmi-total]').evaluate_all('(nodes)=>nodes.map(n=>({value:n.textContent,total:n.getAttribute("data-gmi-total")}))')
            assert all(x['value']==x['total'] for x in totals)
            expect(p.locator('[data-gmi-index-feedback]')).not_to_be_visible()
            assert ('Full index: 371 micro-themes' if language=='en' else '完整索引：371 个细分主题') in p.locator('.gmi-foot').inner_text()
            # Real sticky geometry is exercised before filtering shortens the document.
            jump(energy)
            p.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            targets=p.locator('[data-gmi-category-picker],[data-gmi-category-go]' if width<=640 else '.gmi-jump a:visible').evaluate_all('(nodes)=>nodes.map(n=>n.getBoundingClientRect().height)')
            assert min(targets)>=44
            if width<=640:
                geometry=p.evaluate('''()=>{const nav=document.querySelector('.gmi-jump').getBoundingClientRect(),head=document.querySelector('#energy_power > summary').getBoundingClientRect();
                  return {navTop:nav.top,navBottom:nav.bottom,headerTop:head.top,scrollMargin:getComputedStyle(document.getElementById('energy_power')).scrollMarginTop};}''')
                assert abs(geometry['navTop'])<1 and geometry['headerTop']>=geometry['navBottom']-0.5
                assert geometry['scrollMargin']=='61px'
                report.setdefault('sticky_geometry',[]).append({'width':width,'language':language,**geometry})
            energy.evaluate('(n)=>n.setAttribute("aria-current","true")')
            search.fill('HBM')
            expect(energy).not_to_be_visible(timeout=1500)
            expect(energy).not_to_have_attribute('aria-current','true')
            assert available_shortcuts()==1
            if width<=640:
                expect(picker).to_be_visible();expect(go).to_be_visible()
                assert picker.locator('option[value="semiconductors_hardware"]').count()==1
                assert not semiconductor.evaluate('(n)=>n.hidden')
            else:expect(semiconductor).to_be_visible()
            expect(search).to_be_focused()
            assert p.locator('[data-gmi-index] > details:visible').count()==1
            assert p.locator('a.gmi-irow-name:visible').count()==2
            expect(semiconductor.locator('small')).to_have_text('2')
            expect(p.locator('#semiconductors_hardware > summary > b')).to_have_text('2')
            assert p.locator('.gmi-index-t:visible [data-gmi-subgroup-count]').all_text_contents()==['1','1']
            assert p.locator('[data-gmi-index-breakdown]').evaluate_all('(nodes)=>nodes.every(n=>n.hidden)')
            feedback=p.locator('[data-gmi-index-feedback]')
            expect(feedback).to_be_visible()
            assert feedback.inner_text().strip()==('2 results' if language=='en' else '2 个结果')
            assert p.locator('[role="status"]:visible').count()==1
            before = p.url
            jump(semiconductor)
            assert p.url==before
            assert p.locator('#semiconductors_hardware').evaluate('(n)=>n.open')
            # Hidden or detached targets may not fall through to a destructive native fragment.
            result = p.evaluate('''()=>{
              const a=document.querySelector('.gmi-jump a[href="#energy_power"]'),g=document.getElementById('energy_power');
              const before=location.href,scroll=scrollY,opened=g.open,parent=g.parentNode,next=g.nextSibling;
              a.click();const hidden={url:location.href,scroll:scrollY,opened:g.open};
              g.remove();a.click();const detached=location.href;parent.insertBefore(g,next);
              return {before,scroll,opened,hidden,detached};
            }''')
            assert result['hidden']=={'url':result['before'],'scroll':result['scroll'],'opened':result['opened']}
            assert result['detached']==result['before']
            stale = p.evaluate('''()=>{
              const callbacks=window.__gmiJumpObservers,good=document.getElementById('semiconductors_hardware'),bad=document.getElementById('energy_power');
              callbacks.forEach(cb=>cb([{target:good,isIntersecting:true}]));
              callbacks.forEach(cb=>cb([{target:bad,isIntersecting:true}]));
              return [...document.querySelectorAll('.gmi-jump [aria-current="true"]')].map(a=>a.getAttribute('href'));
            }''')
            assert stale==['#semiconductors_hardware']
            # Clear restores all groups and shortcuts; a no-match query hides the whole rail.
            search.fill('zz-gmi-no-match-fixture')
            expect(nav).not_to_be_visible()
            expect(p.locator('[data-gmi-nomatch="index"]')).to_be_visible()
            expect(p.locator('[data-gmi-index-count]')).not_to_be_visible()
            assert feedback.inner_text().strip()==('No micro-theme matches that search.' if language=='en' else '没有匹配该搜索的细分主题。')
            assert p.locator('[role="status"]:visible').count()==1
            expect(search).to_be_focused()
            search.press('Escape')
            expect(nav).to_be_visible()
            assert available_shortcuts()==total
            assert p.locator('a.gmi-irow-name:visible').count()==371
            expect(feedback).not_to_be_visible()
            assert p.locator('[data-gmi-total]').evaluate_all('(nodes)=>nodes.map(n=>({value:n.textContent,total:n.getAttribute("data-gmi-total")}))')==totals
            assert p.locator('[data-gmi-index-breakdown]').evaluate_all('(nodes)=>nodes.every(n=>!n.hidden)')
            params = parse_qs(urlsplit(p.url).fragment)
            assert 'q' not in params and params['open']==['all'] and params['lens']==['chain']
            assert params['gmi_return']==['gmi.html#theme=theme:hbm_packaging&q=Micron']
            # Hiding a previously current category must not suppress its next reveal after Clear.
            def reveal_last():
                return p.evaluate('''()=>{
                  const track=document.querySelector('.gmi-jump-track'),g=document.getElementById('crypto_digital_assets');
                  track.scrollLeft=0;window.__gmiJumpObservers.forEach(cb=>cb([{target:g,isIntersecting:true}]));
                  return {overflow:track.scrollWidth>track.clientWidth,scroll:track.scrollLeft};
                }''')
            first = reveal_last()
            if first['overflow']:
                assert first['scroll']>0
            search.fill('HBM');search.press('Escape')
            again = reveal_last()
            if again['overflow']:
                assert again['scroll']>0

            def restore(query):
                p.evaluate('''q=>{const h=new URLSearchParams(location.hash.slice(1));
                  if(q)h.set('q',q);else h.delete('q');location.hash=h.toString();}''',query)
                expect(search).to_have_value(query)

            # History can hide a focused row while another row in its category still matches.
            dram = p.locator('[data-gmi-id="theme:conventional_dram"] a')
            dram.focus();restore('HBM & advanced packaging')
            expect(p.locator('#semiconductors_hardware')).to_be_visible()
            expect(dram).not_to_be_visible()
            assert feedback.inner_text().strip()==('1 result' if language=='en' else '1 个结果')
            expect(semiconductor.locator('small')).to_have_text('1')
            assert p.locator('.gmi-index-t:visible [data-gmi-subgroup-count]').all_text_contents()==['1']
            expect(search).to_be_focused()
            hbm = p.locator('[data-gmi-id="theme:hbm_packaging"] a')
            hbm.focus();restore('HBM')
            expect(hbm).to_be_focused()
            restore('')
            if width<=640:
                picker.select_option('energy_power');go.focus();restore('HBM')
                expect(picker).to_be_focused();expect(picker).to_have_value('');expect(go).to_be_disabled()
            else:
                energy.focus();restore('HBM');expect(search).to_be_focused()
            restore('');p.locator('#energy_power > summary').focus();restore('HBM')
            expect(search).to_be_focused()
            # An unrelated focus owner is not taken over by history restoration.
            restore('')
            p.evaluate('''()=>{const b=document.createElement('button');b.id='gmi-focus-fixture';
              b.textContent='Unrelated focus fixture';document.body.append(b);b.focus();}''')
            restore('HBM')
            expect(p.locator('#gmi-focus-fixture')).to_be_focused()
            p.locator('#gmi-focus-fixture').evaluate('(n)=>n.remove()')
            restore('zz-gmi-no-match-fixture');p.go_back()
            expect(search).to_have_value('HBM')
            assert available_shortcuts()==1
            p.go_forward();expect(search).to_have_value('zz-gmi-no-match-fixture')
            expect(nav).not_to_be_visible()
            restore('HBM')
            p.evaluate('(language)=>document.documentElement.setAttribute("data-lang",language)', 'zh' if language=='en' else 'en')
            assert available_shortcuts()==1
            assert feedback.inner_text().strip()==('2 个结果' if language=='en' else '2 results')
            # Restoring the pre-search collapsed state also releases focus before closing it.
            restore('')
            group = p.locator('#energy_power')
            group.evaluate('(n)=>{n.open=false;}')
            query = group.locator('[data-gmi-q]').first.get_attribute('data-gmi-q')[:200]
            restore(query)
            group.locator('a.gmi-irow-name:visible').first.focus()
            restore('')
            assert not group.evaluate('(n)=>n.open')
            expect(search).to_be_focused()
            restore('HBM')
            p.evaluate('(language)=>document.documentElement.setAttribute("data-lang",language)',language)
            gmi_navigation_fit(p,width,language)
            if (width,language) in ((390,'en'),(320,'zh')):
                path=args.out/f'index-filter-{width}-{language}.png'
                p.screenshot(path=str(path),full_page=True)
                report['screenshots'].append(path.name)


    for width in (1440, 390, 320):
        for language in ('en', 'zh'):
            check(f'taxonomy-keyboard-{width}-{language}', lambda w=width,l=language: taxonomy_keyboard_activation(w,l))
            check(f'index-shortcuts-{width}-{language}', lambda w=width,l=language: index_filtered_shortcuts(w,l))

    def tree_roving_paths(width, language):
        """Native Tab/arrow traversal and owned hide recovery on the generated tree."""
        with context(width,'light',language,reduced_motion='reduce') as c:
            p=page_for(c,'gmi.html?fixture=tree#lens=chain')
            p.locator('.gmi-advanced > summary').click()
            tree=p.locator('.gmi-tree')
            search=p.locator('input[data-gmi-filter="tree"]')
            exit_link=p.locator('.gmi-trow--more')
            expect(tree).to_have_accessible_name('Browse the tree' if language=='en' else '浏览主题树')
            original_url=p.url
            original_title=p.locator('#gmi-topic-title').inner_text()
            destinations=tree.locator('a[data-topic-select]').evaluate_all('(nodes)=>nodes.map(n=>({id:n.getAttribute("data-topic-select"),href:n.getAttribute("href")}))')
            information=tree.locator('button').evaluate_all('(nodes)=>nodes.map(n=>({text:n.textContent,tabindex:n.getAttribute("tabindex")}))')
            # Observe unsafe hide ordering without changing the native hidden setter.
            p.evaluate('''()=>{
              const descriptor=Object.getOwnPropertyDescriptor(HTMLElement.prototype,'hidden');
              window.__gmiTreeUnsafeHides=[];
              Object.defineProperty(HTMLElement.prototype,'hidden',{...descriptor,set(value){
                if(value&&this.closest('.gmi-tree')&&this.contains(document.activeElement))
                  window.__gmiTreeUnsafeHides.push({tag:this.tagName,row:this.getAttribute('data-gmi-q')});
                descriptor.set.call(this,value);
              }});
            }''')

            def invariant(empty=False):
                state=tree.evaluate('''n=>{
                  const rows=[...n.querySelectorAll('[role="treeitem"]')];
                  return {visible:rows.filter(r=>!r.hidden).length,
                    visibleZeros:rows.filter(r=>!r.hidden&&r.tabIndex===0).length,
                    hiddenZeros:rows.filter(r=>r.hidden&&r.tabIndex===0).length,
                    rowValues:rows.every(r=>r.tabIndex===0||r.tabIndex===-1),
                    links:[...n.querySelectorAll('[role="treeitem"] a[data-topic-select]')].every(a=>a.tabIndex===-1)};
                }''')
                assert state['visibleZeros']==(0 if empty else 1),state
                assert state['hiddenZeros']==0 and state['rowValues'] and state['links'],state
                if empty:
                    assert state['visible']==0,state
                assert exit_link.evaluate('(n)=>n.tabIndex')==0
                assert not p.evaluate('window.__gmiTreeUnsafeHides.length')
                return state

            def row(identifier):
                return tree.locator('[role="treeitem"]').filter(has=p.locator('a[data-topic-select="'+identifier+'"]')).first

            def focus_leaf(identifier):
                search.focus();p.keyboard.press('Tab')
                clear=p.locator('[data-gmi-search-clear]')
                if clear.is_visible():
                    expect(clear).to_be_focused();p.keyboard.press('Tab')
                p.keyboard.press('Home')
                target=row(identifier)
                for _ in range(tree.locator('[role="treeitem"]:visible').count()):
                    if target.evaluate('(n)=>n===document.activeElement'):
                        break
                    p.keyboard.press('ArrowDown')
                expect(target).to_be_focused()
                invariant()
                return target

            def query_without_focus(value):
                search.evaluate('''(n,value)=>{n.value=value;n.dispatchEvent(new Event('input',{bubbles:true}));}''',value)

            initial=invariant()
            assert initial['visible']>2
            search.focus();p.keyboard.press('Tab')
            entry=tree.locator('[role="treeitem"][tabindex="0"]')
            expect(entry).to_be_focused()
            p.keyboard.press('Tab');expect(exit_link).to_be_focused()
            p.keyboard.press('Shift+Tab');expect(entry).to_be_focused()
            p.keyboard.press('Shift+Tab');expect(search).to_be_focused()

            search.fill('HBM');expect(search).to_be_focused();invariant()
            leaf=focus_leaf('theme:hbm_packaging')
            p.keyboard.press('Tab');expect(exit_link).to_be_focused()
            p.keyboard.press('Shift+Tab');expect(leaf).to_be_focused()
            parent_id=leaf.get_attribute('data-gmi-tree-parent')
            parent=tree.locator('[data-gmi-tree-id="'+parent_id+'"]')
            p.keyboard.press('ArrowLeft');expect(parent).to_be_focused()
            p.keyboard.press('ArrowLeft')
            expect(parent).to_have_attribute('aria-expanded','false')
            expect(leaf).not_to_be_visible();expect(parent).to_be_focused();invariant()
            p.keyboard.press('ArrowRight')
            expect(parent).to_have_attribute('aria-expanded','true')
            expect(parent).to_be_focused();invariant()
            p.keyboard.press('ArrowRight')
            assert p.evaluate('document.activeElement.getAttribute("data-gmi-tree-parent")')==parent_id
            invariant()

            # A synchronous collapse while a descendant still owns focus must release it
            # before hidden is assigned, not merely repair body focus after the fact.
            leaf=focus_leaf('theme:hbm_packaging')
            parent.evaluate('(n)=>n.click()')
            expect(parent).to_be_focused();expect(leaf).not_to_be_visible();invariant()
            parent.press('ArrowRight')
            leaf=focus_leaf('theme:hbm_packaging')
            query_without_focus('Conventional DRAM (non-HBM)')
            expect(search).to_be_focused();expect(leaf).not_to_be_visible();invariant()
            dram=focus_leaf('theme:conventional_dram')
            # Clearing restores the pre-search closed memory branch; the active leaf
            # cannot remain focused while that original visibility is restored.
            query_without_focus('')
            expect(search).to_be_focused();expect(dram).not_to_be_visible();invariant()

            search.fill('HBM')
            leaf=focus_leaf('theme:hbm_packaging')
            query_without_focus('HBM & advanced packaging')
            expect(leaf).to_be_focused();invariant()
            # A focused nested link that survives filtering keeps its own native focus.
            anchor=leaf.locator('a[data-topic-select]')
            anchor.focus();query_without_focus('HBM')
            expect(anchor).to_be_focused();assert leaf.evaluate('(n)=>n.tabIndex')==0
            query_without_focus('Conventional DRAM (non-HBM)')
            expect(search).to_be_focused();invariant()

            p.locator('[data-gmi-copy]').focus()
            query_without_focus('zz-no-matching-gmi-theme')
            expect(p.locator('[data-gmi-copy]')).to_be_focused()
            expect(p.locator('[data-gmi-nomatch="tree"]')).to_be_visible()
            invariant(empty=True)
            search.fill('');expect(search).to_be_focused();invariant()
            assert tree.locator('[role="treeitem"]:visible').first.evaluate('(n)=>n.tabIndex')==0
            exit_link.focus();query_without_focus('HBM')
            expect(exit_link).to_be_focused();invariant()
            query_without_focus('zz-no-matching-gmi-theme')
            expect(exit_link).to_be_focused();invariant(empty=True)
            query_without_focus('');expect(exit_link).to_be_focused();invariant()
            assert p.url==original_url
            assert p.locator('#gmi-topic-title').inner_text()==original_title

            # Informational controls retain their independent access; only topic links
            # are removed from sequential Tab traversal during enhancement.
            info=tree.locator('button').first
            info_row=info.locator('xpath=..')
            info_query=info_row.get_attribute('data-gmi-q')
            assert info_query
            search.fill(info_query)
            expect(info).to_be_visible();assert info.evaluate('(n)=>n.tabIndex')==0
            info_parent=tree.locator('[data-gmi-tree-id="'+info_row.get_attribute('data-gmi-tree-parent')+'"]')
            info.focus();info_parent.evaluate('(n)=>n.click()')
            expect(info_parent).to_be_focused();expect(info).not_to_be_visible();invariant()
            info_parent.press('ArrowRight');expect(info).to_be_visible()
            info.focus();query_without_focus('zz-no-matching-gmi-theme')
            expect(search).to_be_focused();invariant(empty=True)
            search.fill('')
            assert tree.locator('button').evaluate_all('(nodes)=>nodes.map(n=>({text:n.textContent,tabindex:n.getAttribute("tabindex")}))')==information

            # A real modified pointer activation still opens its unchanged native URL.
            search.fill('Conventional DRAM (non-HBM)')
            dram=focus_leaf('theme:conventional_dram')
            link=dram.locator('a[data-topic-select]')
            destination=link.evaluate('(n)=>n.href')
            modifier='Meta' if p.evaluate('navigator.platform').startswith('Mac') else 'Control'
            with c.expect_page() as opened:
                link.click(modifiers=[modifier])
            popup=opened.value
            popup.wait_for_load_state('domcontentloaded')
            assert popup.url==destination
            expect(popup.locator('#gmi-topic-title')).to_have_text('Conventional DRAM (non-HBM)' if language=='en' else '常规 DRAM（非 HBM）')
            popup.close()
            assert p.url==original_url
            assert tree.locator('a[data-topic-select]').evaluate_all('(nodes)=>nodes.map(n=>({id:n.getAttribute("data-topic-select"),href:n.getAttribute("href")}))')==destinations
            invariant()
            p.evaluate('(language)=>document.documentElement.setAttribute("data-lang",language)', 'zh' if language=='en' else 'en')
            expect(tree).to_have_accessible_name('浏览主题树' if language=='en' else 'Browse the tree')
            p.evaluate('(language)=>document.documentElement.setAttribute("data-lang",language)',language)
            search.fill('HBM');focus_leaf('theme:hbm_packaging')
            if (width,language) in ((390,'en'),(320,'zh')):
                path=args.out/f'tree-roving-{width}-{language}.png'
                tree.screenshot(path=str(path))
                report['screenshots'].append(path.name)

        # Actual script-disabled contexts preserve the original native link fallback.
        # This proves retained link markup, not a complete no-JavaScript research app.
        with context(width,'light',language,java_script_enabled=False,reduced_motion='reduce') as c:
            p=page_for(c)
            p.locator('.gmi-advanced > summary').click()
            links=p.locator('.gmi-tree a[data-topic-select]')
            assert links.count()==371
            assert links.evaluate_all('(nodes)=>nodes.every(n=>!n.hasAttribute("tabindex")&&n.getAttribute("href").startsWith("gmi.html#theme="))')
            expect(p.locator('.gmi-tree a[data-topic-select="theme:hbm_packaging"]')).to_be_visible()
            assert p.locator('.gmi-trow--more').evaluate('(n)=>n.tabIndex')==0
            expect(p.locator('[data-gmi-ready]')).to_have_count(0)


    for width in (1440, 390, 320):
        for language in ('en', 'zh'):
            check(f'tree-roving-{width}-{language}', lambda w=width,l=language: tree_roving_paths(w,l))

    def answer_filter_recovery_paths(width, language):
        """Clear answer-side filters without replacing evidence or reviving old copy UI."""
        for success in (True, False):
            with context(width,'light',language,reduced_motion='reduce') as c:
                c.add_init_script('''(()=>{
                  window.__gmiRecoveryCopy={writes:[]};
                  Object.defineProperty(navigator,'clipboard',{configurable:true,value:{
                    writeText(url){return new Promise((resolve,reject)=>window.__gmiRecoveryCopy.writes.push({url,resolve,reject}));}
                  }});
                })();''')
                returned='gmi-companies.html#q=memory'
                fragment=urlencode({'theme':'theme:hbm_packaging','lens':'chain','gmi_return':returned,'fixture_key':'retained'})
                p=page_for(c,'gmi.html?fixture=answer-recovery#'+fragment)
                title=p.locator('#gmi-topic-title')
                original_title=title.inner_text()
                opener=p.locator('[data-browse-open]')
                dialog=p.locator('[data-browse-dialog]')
                search=p.locator('[data-topic-search]')
                notice=p.locator('[data-topic-notice]')
                recovery=p.locator('[data-topic-notice-reset]')
                if width<=820:
                    opener.click()
                    expect(dialog).to_be_visible()
                search.fill('zz-no-matching-research-topic')
                options=p.locator('[data-topic-category-filter] option').evaluate_all('(nodes)=>nodes.map(n=>n.value).filter(Boolean)')
                p.locator('[data-topic-category-filter]').select_option(options[0])
                p.locator('input[name="gmi-scope"][value="extended"]').check()
                p.locator('[data-evidence-only]').check()
                expect(p.locator('[data-topic-no-results]')).to_be_visible()
                if width<=820:
                    p.locator('[data-browse-close]').click()
                    expect(dialog).not_to_be_visible()
                assert recovery.count()==1,'Selected answer has no directly available filter reset'
                expect(recovery).to_be_visible()
                expect(notice).to_have_text('This topic is outside your filters.' if language=='en' else '当前主题不在筛选范围内。')
                expect(recovery).to_have_accessible_name('Clear filters' if language=='en' else '清除筛选')
                expect(title).to_have_text(original_title)
                bounds=recovery.bounding_box()
                assert bounds and bounds['height']>=44 and bounds['width']>=44
                gmi_navigation_fit(p,width,language)
                filtered_url=p.url
                recovery.focus()
                other='zh' if language=='en' else 'en'
                p.evaluate('(v)=>document.documentElement.setAttribute("data-lang",v)',other)
                expect(recovery).to_have_accessible_name('清除筛选' if other=='zh' else 'Clear filters')
                expect(recovery).to_be_focused()
                assert p.url==filtered_url
                p.evaluate('(v)=>document.documentElement.setAttribute("data-lang",v)',language)
                expect(notice).to_have_text('This topic is outside your filters.' if language=='en' else '当前主题不在筛选范围内。')
                expect(title).to_have_text(original_title)
                expect(recovery).to_be_focused()
                p.evaluate('''()=>{
                  const cards=document.querySelector('[data-topic-connections]');
                  window.__gmiRecoveryNodes=Array.from(cards.children);
                  const receipt=cards.querySelector('details');
                  if(receipt)receipt.open=true;
                }''')
                identities=p.locator('.gmi-evidence-receipt dd').all_text_contents()
                if success and (width,language) in ((390,'en'),(320,'zh')):
                    path=args.out/f'answer-recovery-{width}-{language}.png'
                    p.locator('.gmi-answer-column').screenshot(path=str(path))
                    report['screenshots'].append(path.name)
                p.locator('[data-gmi-copy]').click()
                expect(p.locator('[data-gmi-copy]')).to_be_disabled()
                assert p.evaluate('window.__gmiRecoveryCopy.writes.length')==1
                assert p.evaluate('window.__gmiRecoveryCopy.writes[0].url')==filtered_url
                history_before=p.evaluate('history.length')
                recovery.click()
                expect(recovery).not_to_be_visible()
                expect(notice).not_to_be_visible()
                expect(p.locator('[data-topic-notice-region]')).not_to_be_visible()
                expect(title).to_be_focused()
                expect(title).to_have_text(original_title)
                expect(dialog).not_to_be_visible()
                expect(search).to_have_value('')
                expect(p.locator('[data-topic-category-filter]')).to_have_value('')
                expect(p.locator('input[name="gmi-scope"][value="all"]')).to_be_checked()
                expect(p.locator('[data-evidence-only]')).not_to_be_checked()
                expected={'theme':['theme:hbm_packaging'],'lens':['chain'],'gmi_return':[returned],'fixture_key':['retained']}
                assert parse_qs(urlsplit(p.url).fragment)==expected
                assert urlsplit(p.url).query=='fixture=answer-recovery'
                assert p.evaluate('history.length')==history_before
                assert p.locator('.gmi-evidence-receipt dd').all_text_contents()==identities
                assert p.evaluate('''()=>window.__gmiRecoveryNodes.every((n,i)=>n.isConnected&&n===document.querySelector('[data-topic-connections]').children[i])''')
                assert p.locator('.gmi-evidence-receipt').evaluate('(n)=>n.open')
                p.evaluate('''(success)=>{
                  const write=window.__gmiRecoveryCopy.writes[0];
                  success?write.resolve():write.reject(new Error('explicit fixture denial'));
                }''',success)
                p.evaluate('()=>new Promise(requestAnimationFrame)')
                expect(p.locator('[data-gmi-copy]')).to_be_enabled()
                expect(p.locator('[data-copy-label]')).to_have_text('Copy link' if language=='en' else '复制链接')
                expect(p.locator('.gmi-copy-fallback')).not_to_be_visible()
                expect(p.locator('[data-gmi-announcement]')).to_have_text('')
                expect(title).to_be_focused()

                # Existing sidebar/drawer reset remains a search-local action.
                if width<=820:
                    opener.click()
                search.fill('another-query-with-no-results')
                p.locator('[data-topic-no-results] [data-topic-reset]').click()
                expect(search).to_be_focused()
                expect(search).to_have_value('')
                if width<=820:
                    expect(dialog).to_be_visible()
                    p.locator('[data-browse-close]').click()
                expect(recovery).not_to_be_visible()

                # A visible manual fallback retires through the same URL-change owner.
                if width<=820:
                    opener.click()
                search.fill('manual-copy-filter-context')
                if width<=820:
                    p.locator('[data-browse-close]').click()
                p.locator('[data-gmi-copy]').click()
                p.evaluate('window.__gmiRecoveryCopy.writes.at(-1).reject(new Error("explicit fixture denial"))')
                expect(p.locator('.gmi-copy-fallback')).to_be_visible()
                recovery.click()
                expect(p.locator('.gmi-copy-fallback')).not_to_be_visible()
                expect(title).to_be_focused()
                expect(recovery).not_to_be_visible()
                assert p.locator('.gmi-evidence-receipt dd').all_text_contents()==identities
                assert p.evaluate('''()=>window.__gmiRecoveryNodes.every((n,i)=>n===document.querySelector('[data-topic-connections]').children[i])''')
                gmi_navigation_fit(p,width,language)


    def answer_filter_recovery_guards(language):
        """Missing data/topics and static markup must not promise filter recovery."""
        with context(390,'light',language,reduced_motion='reduce') as c:
            p=page_for(c,'gmi.html#theme=theme%3Amissing-recovery-fixture&q=no-match')
            notice=p.locator('[data-topic-notice]')
            expect(notice).to_contain_text('That topic is not available' if language=='en' else '此快照中找不到该主题')
            expect(p.locator('[data-topic-notice-region]')).to_be_visible()
            expect(p.locator('[data-topic-notice-reset]')).not_to_be_visible()
            other='zh' if language=='en' else 'en'
            p.evaluate('(v)=>document.documentElement.setAttribute("data-lang",v)',other)
            expect(notice).to_contain_text('此快照中找不到该主题' if other=='zh' else 'That topic is not available')
            expect(p.locator('[data-topic-notice-reset]')).not_to_be_visible()
        with context(390,'light',language,reduced_motion='reduce') as c:
            def damage(route):
                response=route.fetch()
                original=response.text()
                damaged=re.sub(r'(<script\b[^>]*id="gmi-topic-data"[^>]*>).*?(</script>)',
                               lambda m:m[1]+'{"topics":]'+m[2],original,flags=re.S)
                assert damaged!=original
                route.fulfill(response=response,body=damaged)
            c.route('**/gmi.html*',damage)
            p=page_for(c)
            expect(p.locator('[data-topic-notice]')).to_contain_text('Interactive research could not load' if language=='en' else '交互研究未能加载')
            expect(p.locator('[data-topic-notice-region]')).to_be_visible()
            expect(p.locator('[data-topic-notice-reset]')).not_to_be_visible()
            expect(p.locator('[data-topic-answer]')).to_be_visible()
            other='zh' if language=='en' else 'en'
            p.evaluate('(v)=>document.documentElement.setAttribute("data-lang",v)',other)
            expect(p.locator('[data-topic-notice]')).to_contain_text('交互研究未能加载' if other=='zh' else 'Interactive research could not load')
            expect(p.locator('[data-topic-notice-reset]')).not_to_be_visible()
        with context(390,'light',language,java_script_enabled=False,reduced_motion='reduce') as c:
            p=page_for(c)
            expect(p.locator('[data-topic-notice-region]')).not_to_be_visible()
            expect(p.locator('[data-topic-notice-reset]')).not_to_be_visible()
            expect(p.locator('#gmi-topic-title')).to_be_visible()


    for width in (1440,390,320):
        for language in ('en','zh'):
            check(f'answer-filter-recovery-{width}-{language}',lambda w=width,l=language:answer_filter_recovery_paths(w,l))
    for language in ('en','zh'):
        check(f'answer-filter-recovery-guards-{language}',lambda l=language:answer_filter_recovery_guards(l))

    def tree_status_spacing(p, empty):
        """The persistent live region must preserve the original panel spacing."""
        geometry=p.locator('.gmi-tree').evaluate("""n=>{
          const search=document.querySelector('[data-gmi-filter="tree"]').closest('.gmi-search');
          const panel=n.closest('.gmi-panel');
          const m=document.querySelector('[data-gmi-nomatch="tree"]');
          const s=getComputedStyle(m);
          return {gap:panel.getBoundingClientRect().top-search.getBoundingClientRect().bottom,
            messageHeight:m.getBoundingClientRect().height,parentGap:parseFloat(getComputedStyle(search.parentElement).gap),
            messageMargins:parseFloat(s.marginTop)+parseFloat(s.marginBottom)};
        }""")
        expected=(geometry['parentGap']*2+geometry['messageHeight']+geometry['messageMargins']) if empty else geometry['parentGap']
        assert abs(geometry['gap']-expected)<0.5,geometry
        return geometry

    def tree_status_feedback(width, language):
        """Persistent empty-search status, stable focus and one visibility update per transition."""
        with context(width,'light',language,reduced_motion='reduce') as c:
            p=page_for(c,'gmi.html?fixture=tree-status#theme=theme%3Ahbm_packaging&lens=chain')
            p.locator('.gmi-advanced > summary').click()
            tree=p.locator('.gmi-tree')
            search=p.locator('input[data-gmi-filter="tree"]')
            status=p.locator('[data-gmi-tree-status]')
            message=p.locator('[data-gmi-nomatch="tree"]')
            assert status.count()==1,'Tree no-match message has no persistent status owner'
            expect(status).to_have_attribute('role','status')
            expect(status).to_have_attribute('aria-live','polite')
            expect(status).to_have_attribute('aria-atomic','true')
            assert status.evaluate('(n)=>!n.hidden&&!n.hasAttribute("aria-hidden")')
            expect(message).not_to_be_visible()
            assert not status.inner_text().strip()
            initial_geometry=tree_status_spacing(p,False)
            original_url=p.url
            original_title=p.locator('#gmi-topic-title').inner_text()
            p.evaluate("""()=>{
              window.__treeStatusOwner=document.querySelector('[data-gmi-tree-status]');
              window.__treeStatusMessage=document.querySelector('[data-gmi-nomatch="tree"]');
              window.__treeStatusChanges=[];
              window.__treeStatusObserver=new MutationObserver(records=>{
                window.__treeStatusChanges.push(...records.map(r=>({attribute:r.attributeName,old:r.oldValue})));
              });
              window.__treeStatusObserver.observe(window.__treeStatusMessage,{attributes:true,attributeFilter:['hidden'],attributeOldValue:true});
              window.__treeStatusCards=[...document.querySelector('[data-topic-connections]').children];
              const receipt=document.querySelector('.gmi-evidence-receipt');
              if(receipt)receipt.open=true;
            }""")
            def stable(changes,empty):
                assert p.evaluate("""()=>window.__treeStatusOwner===document.querySelector('[data-gmi-tree-status]')&&window.__treeStatusMessage===document.querySelector('[data-gmi-nomatch="tree"]')""")
                assert p.evaluate('window.__treeStatusChanges.length')==changes
                tree_status_spacing(p,empty)
                assert p.url==original_url
                expect(search).to_be_focused()
                zeros=tree.locator('[role="treeitem"][tabindex="0"]:visible').count()
                assert zeros==(0 if empty else 1)
                assert tree.locator('[role="treeitem"]:visible').count()>0 if not empty else tree.locator('[role="treeitem"]:visible').count()==0

            search.fill('hbm')
            expect(message).not_to_be_visible()
            stable(0,False)
            search.fill('zz-no-tree-status-match')
            expect(message).to_be_visible()
            expected='No micro-theme matches that search.' if language=='en' else '没有匹配该搜索的细分主题。'
            expect(status).to_have_text(re.compile(re.escape(expected)))
            assert status.inner_text().strip()==expected
            ax=status.aria_snapshot()
            assert 'status' in ax and expected in ax,ax
            inactive='没有匹配该搜索的细分主题。' if language=='en' else 'No micro-theme matches that search.'
            assert inactive not in ax,ax
            stable(1,True)
            empty_geometry=tree_status_spacing(p,True)
            search.fill('zz-another-no-tree-status-match')
            stable(1,True)
            assert p.evaluate("""()=>window.__treeStatusCards.every((n,i)=>document.querySelector('[data-topic-connections]').children[i]===n)""")
            expect(p.locator('#gmi-topic-title')).to_have_text(original_title)
            expect(p.locator('.gmi-evidence-receipt')).to_have_attribute('open','')
            other='zh' if language=='en' else 'en'
            p.evaluate('(language)=>document.documentElement.setAttribute("data-lang",language)',other)
            translated='没有匹配该搜索的细分主题。' if other=='zh' else 'No micro-theme matches that search.'
            assert status.inner_text().strip()==translated
            assert translated in status.aria_snapshot()
            stable(1,True)
            p.evaluate('(language)=>document.documentElement.setAttribute("data-lang",language)',language)
            expect(p.locator('#gmi-topic-title')).to_have_text(original_title)
            assert status.inner_text().strip()==expected
            stable(1,True)
            if (width,language) in ((390,'en'),(320,'zh')):
                path=args.out/f'tree-status-{width}-{language}.png'
                p.locator('.gmi-advanced').screenshot(path=str(path))
                report['screenshots'].append(path.name)
            search.press('Tab')
            expect(p.locator('[data-gmi-search-clear]')).to_be_focused()
            p.keyboard.press('Tab')
            expect(p.locator('.gmi-trow--more')).to_be_focused()
            search.fill('')
            expect(message).not_to_be_visible()
            assert not status.inner_text().strip()
            stable(2,False)
            search.fill('zz-no-tree-status-match')
            expect(message).to_be_visible()
            stable(3,True)
            search.fill('hbm')
            expect(message).not_to_be_visible()
            stable(4,False)
            gmi_navigation_fit(p,width,language)
            report.setdefault('tree_status',[]).append({'width':width,'language':language,'hidden_mutations':4,'status_identity_retained':True,'empty_accessibility_snapshot':ax,'focus_and_url_retained':True,'initial_geometry':initial_geometry,'empty_geometry':empty_geometry})
            p.evaluate('window.__treeStatusObserver.disconnect()')

    def tree_status_static(language):
        """No false no-results status when the actual page scripts are disabled."""
        with context(320,'light',language,java_script_enabled=False,reduced_motion='reduce') as c:
            p=page_for(c,'gmi.html?fixture=tree-status-static')
            p.locator('.gmi-advanced > summary').click()
            status=p.locator('[data-gmi-tree-status]')
            assert status.count()==1
            expect(status).to_have_attribute('role','status')
            assert status.evaluate('(n)=>!n.hidden')
            expect(p.locator('[data-gmi-nomatch="tree"]')).not_to_be_visible()
            assert not status.inner_text().strip()
            ax=status.aria_snapshot()
            assert 'No micro-theme matches' not in ax and '没有匹配' not in ax
            geometry=tree_status_spacing(p,False)
            links=p.locator('.gmi-tree a[data-topic-select]')
            assert links.count()==371
            assert links.evaluate_all('(nodes)=>nodes.every(n=>n.getAttribute("href")&&n.getAttribute("tabindex")===null)')
            assert p.evaluate('typeof window.__treeStatusOwner')=='undefined'
            report.setdefault('tree_status_static',[]).append({'language':language,'native_links':links.count(),'status_empty':True,'java_script_enabled':False,'geometry':geometry})

    for width in (1440,390,320):
        for language in ('en','zh'):
            check(f'tree-status-{width}-{language}',lambda w=width,l=language:tree_status_feedback(w,l))
    for language in ('en','zh'):
        check(f'tree-status-static-{language}',lambda l=language:tree_status_static(l))

    def index_status_spacing(p, active):
        """The persistent status keeps the search-to-key gap and original message layout."""
        g=p.locator('[data-gmi-filter="index"]').evaluate("""n=>{
          const search=n.closest('.gmi-search'),panel=search.parentElement;
          const key=panel.querySelector('.gmi-key'),message=panel.querySelector('[data-gmi-index-feedback]');
          const s=getComputedStyle(message);
          return {gap:key.getBoundingClientRect().top-search.getBoundingClientRect().bottom,
            parentGap:parseFloat(getComputedStyle(panel).gap),messageHeight:message.getBoundingClientRect().height,
            messageMargins:parseFloat(s.marginTop)+parseFloat(s.marginBottom)};
        }""")
        expected=g['parentGap']*2+g['messageHeight']+g['messageMargins'] if active else g['parentGap']
        assert abs(g['gap']-expected)<0.5,g
        return g

    def index_status_feedback(width, language):
        """Persistent index feedback reuses counts, language spans, URL and disclosure owners."""
        with context(width,'light',language,reduced_motion='reduce') as c:
            returned='gmi.html#theme=theme:hbm_packaging&q=Micron'
            p=page_for(c,'gmi-index.html?fixture=index-status#'+urlencode({'open':'all','lens':'chain','gmi_return':returned}))
            search=p.locator('[data-gmi-filter="index"]')
            feedback=p.locator('[data-gmi-index-feedback]')
            status=p.locator('[data-gmi-index-status]')
            initial=index_status_spacing(p,False)
            report.setdefault('index_status_initial_geometry',[]).append({'width':width,'language':language,**initial})
            assert status.count()==1,'Index feedback has no persistent status owner'
            expect(status).to_have_attribute('role','status')
            expect(status).to_have_attribute('aria-live','polite')
            expect(status).to_have_attribute('aria-atomic','true')
            assert status.locator('[role="status"]').count()==0
            assert status.evaluate('(n)=>!n.closest("[hidden],[aria-hidden=true]")&&getComputedStyle(n).display!=="none"')
            expect(feedback).not_to_be_visible()
            assert not status.inner_text().strip()
            p.locator('#energy_power').evaluate('(n)=>{n.open=false;}')
            opened=p.locator('[data-gmi-index] > details').evaluate_all('(nodes)=>nodes.map(n=>n.open)')
            history=p.evaluate('history.length')
            p.evaluate("""()=>{
              window.__indexStatusOwner=document.querySelector('[data-gmi-index-status]');
              window.__indexStatusParagraph=document.querySelector('[data-gmi-index-feedback]');
              window.__indexStatusChanges=[];
              window.__indexStatusObserver=new MutationObserver(records=>window.__indexStatusChanges.push(...records.map(r=>({type:r.type,attribute:r.attributeName}))));
              window.__indexStatusObserver.observe(window.__indexStatusOwner,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['hidden']});
            }""")
            def state(expected, count, current_language=language):
                assert p.evaluate("""()=>window.__indexStatusOwner===document.querySelector('[data-gmi-index-status]')&&window.__indexStatusParagraph===document.querySelector('[data-gmi-index-feedback]')""")
                assert status.evaluate('(n)=>!n.closest("[hidden],[aria-hidden=true]")')
                assert status.inner_text().strip()==expected
                ax=status.aria_snapshot()
                assert 'status' in ax and expected in ax,ax
                if expected:
                    assert ('No micro-theme matches' not in ax if current_language=='zh' else '没有匹配' not in ax)
                assert p.locator('a.gmi-irow-name:visible').count()==count
                expect(search).to_be_focused()
                assert p.evaluate('history.length')==history
                params=parse_qs(urlsplit(p.url).fragment)
                assert params['open']==['all'] and params['lens']==['chain'] and params['gmi_return']==[returned]
                return index_status_spacing(p,bool(expected))

            zero='No micro-theme matches that search.' if language=='en' else '没有匹配该搜索的细分主题。'
            search.fill('zz-no-index-status-match')
            no_match_geometry=state(zero,0)
            mutations=p.evaluate('window.__indexStatusChanges.length')
            search.fill('zz-another-no-index-status-match')
            state(zero,0)
            assert p.evaluate('window.__indexStatusChanges.length')==mutations

            def locale(current, message, count):
                before=p.url
                rows=p.locator('a.gmi-irow-name:visible').evaluate_all('(nodes)=>nodes.map(n=>n.getAttribute("href"))')
                disclosures=p.locator('[data-gmi-index] > details').evaluate_all('(nodes)=>nodes.map(n=>n.open)')
                mutations=p.evaluate('window.__indexStatusChanges.length')
                p.evaluate("""lang=>{
                  document.documentElement.setAttribute('data-lang',lang);
                  document.dispatchEvent(new Event('langchange'));
                  document.dispatchEvent(new Event('langchange'));
                }""",current)
                state(message,count,current)
                assert p.url==before
                assert p.locator('a.gmi-irow-name:visible').evaluate_all('(nodes)=>nodes.map(n=>n.getAttribute("href"))')==rows
                assert p.locator('[data-gmi-index] > details').evaluate_all('(nodes)=>nodes.map(n=>n.open)')==disclosures
                assert p.evaluate('window.__indexStatusChanges.length')==mutations

            other='zh' if language=='en' else 'en'
            locale(other,'没有匹配该搜索的细分主题。' if other=='zh' else 'No micro-theme matches that search.',0)
            locale(language,zero,0)
            search.fill('HBM')
            positive='2 results' if language=='en' else '2 个结果'
            positive_geometry=state(positive,2)
            mutations=p.evaluate('window.__indexStatusChanges.length')
            search.fill('  HBM  ')
            state(positive,2)
            assert p.evaluate('window.__indexStatusChanges.length')==mutations
            locale(other,'2 个结果' if other=='zh' else '2 results',2)
            locale(language,positive,2)
            search.fill('HBM & advanced packaging')
            state('1 result' if language=='en' else '1 个结果',1)
            search.fill('zz-no-index-status-match')
            state(zero,0)
            if (width,language) in ((390,'en'),(320,'zh')):
                path=args.out/f'index-status-{width}-{language}.png'
                p.locator('[data-gmi-filter="index"]').locator('xpath=..').locator('xpath=..').screenshot(path=str(path))
                report['screenshots'].append(path.name)
            search.press('Escape')
            expect(search).to_have_value('')
            expect(feedback).not_to_be_visible()
            assert not status.inner_text().strip()
            assert p.locator('[data-gmi-index] > details').evaluate_all('(nodes)=>nodes.map(n=>n.open)')==opened
            expect(search).to_be_focused()
            assert p.evaluate('history.length')==history
            assert 'q' not in parse_qs(urlsplit(p.url).fragment)
            cleared=index_status_spacing(p,False)
            assert 'result' not in status.aria_snapshot() and '没有匹配' not in status.aria_snapshot()
            gmi_navigation_fit(p,width,language)
            report.setdefault('index_status',[]).append({'width':width,'language':language,'initial':initial,'positive':positive_geometry,'no_match':no_match_geometry,'cleared':cleared,'repeated_query_and_locale_mutations':0,'owner_identity_retained':True})
            p.evaluate('window.__indexStatusObserver.disconnect()')

    def index_status_static(language):
        """Actually disabled scripts expose no false count while native links remain."""
        with context(320,'light',language,java_script_enabled=False,reduced_motion='reduce') as c:
            p=page_for(c,'gmi-index.html?fixture=index-status-static')
            status=p.locator('[data-gmi-index-status]')
            assert status.count()==1
            expect(status).to_have_attribute('role','status')
            assert status.evaluate('(n)=>!n.closest("[hidden],[aria-hidden=true]")')
            expect(p.locator('[data-gmi-index-feedback]')).not_to_be_visible()
            assert not status.inner_text().strip()
            assert 'result' not in status.aria_snapshot() and '没有匹配' not in status.aria_snapshot()
            links=p.locator('a.gmi-irow-name')
            assert links.count()==371
            assert links.evaluate_all('(nodes)=>nodes.every(n=>n.getAttribute("href"))')
            geometry=index_status_spacing(p,False)
            report.setdefault('index_status_static',[]).append({'language':language,'native_links':links.count(),'status_empty':True,'java_script_enabled':False,'geometry':geometry})

    for width in (1440,390,320):
        for language in ('en','zh'):
            check(f'index-status-{width}-{language}',lambda w=width,l=language:index_status_feedback(w,l))
    for language in ('en','zh'):
        check(f'index-status-static-{language}',lambda l=language:index_status_static(l))

    def search_clear_geometry(p, scope):
        field=p.locator('[data-gmi-filter="'+scope+'"]').locator('xpath=..')
        value=field.evaluate("""n=>{
          const input=n.querySelector('input'),button=n.querySelector('[data-gmi-search-clear]'),hint=n.querySelector('kbd');
          const r=x=>{const b=x.getBoundingClientRect();return {left:b.left,right:b.right,top:b.top,bottom:b.bottom,width:b.width,height:b.height};};
          return {field:r(n),input:r(input),button:r(button),hidden:button.hidden,hintVisible:getComputedStyle(hint).display!=='none',ready:n.classList.contains('gmi-search--clearable')};
        }""")
        assert abs(value['field']['height']-44)<0.5,value
        assert value['field']['left']>=-0.5 and value['field']['right']<=p.viewport_size['width']+0.5,value
        if not value['hidden']:
            b=value['button'];f=value['field']
            assert b['width']>=44 and b['height']>=44,value
            assert b['left']>=f['left'] and b['right']<=f['right']+0.5,value
            assert b['top']>=f['top']-0.5 and b['bottom']<=f['bottom']+0.5,value
            assert value['input']['right']<=b['left']-4,value
            assert not value['hintVisible'],value
        else:
            assert value['hintVisible'],value
        return value

    def search_clear_paths(scope, width, language, theme='light'):
        """One native click/key action reuses input state, history, focus and language owners."""
        with context(width,theme,language,reduced_motion='reduce') as c:
            fragment={'lens':'chain','fixture_key':'retained'}
            if scope=='tree':
                fragment.update({'theme':'theme:hbm_packaging','q':'Micron','gmi_return':'gmi-companies.html#q=memory'})
                route='gmi.html'
            else:
                fragment.update({'open':'all','gmi_return':'gmi.html#theme=theme:hbm_packaging&q=Micron'})
                route='gmi-index.html'
            p=page_for(c,route+'?fixture=search-clear#'+urlencode(fragment))
            if scope=='tree':p.locator('.gmi-advanced > summary').click()
            search=p.locator('[data-gmi-filter="'+scope+'"]')
            field=search.locator('xpath=..')
            clear=field.locator('[data-gmi-search-clear]')
            assert clear.count()==1,'Search has no authored clear action'
            expect(clear).not_to_be_visible()
            expect(clear).to_have_attribute('aria-label','Clear search' if language=='en' else '清空搜索')
            original=search_clear_geometry(p,scope)
            if scope=='index':p.locator('#energy_power').evaluate('(n)=>{n.open=false;}')
            snapshot=p.locator('.gmi-tree [aria-expanded]').evaluate_all('(nodes)=>nodes.map(n=>n.getAttribute("aria-expanded"))') if scope=='tree' else p.locator('[data-gmi-index] > details').evaluate_all('(nodes)=>nodes.map(n=>n.open)')
            url_before=p.url
            history=p.evaluate('history.length')
            p.evaluate("""scope=>{
              const input=document.querySelector('[data-gmi-filter="'+scope+'"]');
              window.__searchClearEvents=0;window.__searchClearUnsafeHides=[];
              input.addEventListener('input',()=>window.__searchClearEvents++);
              const d=Object.getOwnPropertyDescriptor(HTMLElement.prototype,'hidden');
              Object.defineProperty(HTMLElement.prototype,'hidden',{...d,set(v){
                if(v&&this.matches('[data-gmi-search-clear]')&&this.contains(document.activeElement))window.__searchClearUnsafeHides.push(true);
                d.set.call(this,v);
              }});
              const cards=document.querySelector('[data-topic-connections]');
              window.__searchClearCards=cards?[...cards.children]:[];
              const receipt=document.querySelector('.gmi-evidence-receipt');if(receipt)receipt.open=true;
            }""",scope)

            def retained():
                expect(search).to_have_value('')
                expect(search).to_be_focused()
                expect(clear).not_to_be_visible()
                g=search_clear_geometry(p,scope)
                assert all(g['field'][key]==original['field'][key] for key in ('left','right','width','height')),g
                assert p.evaluate('history.length')==history
                assert not p.evaluate('window.__searchClearUnsafeHides.length')
                params=parse_qs(urlsplit(p.url).fragment)
                assert params['lens']==['chain'] and params['fixture_key']==['retained'] and params['gmi_return']==[fragment['gmi_return']]
                if scope=='tree':
                    assert p.url==url_before
                    assert p.locator('.gmi-tree [aria-expanded]').evaluate_all('(nodes)=>nodes.map(n=>n.getAttribute("aria-expanded"))')==snapshot
                    assert p.evaluate("""()=>window.__searchClearCards.every((n,i)=>document.querySelector('[data-topic-connections]').children[i]===n)""")
                    expect(p.locator('.gmi-evidence-receipt')).to_have_attribute('open','')
                else:
                    assert 'q' not in params and params['open']==['all']
                    assert p.locator('[data-gmi-index] > details').evaluate_all('(nodes)=>nodes.map(n=>n.open)')==snapshot

            for action in ('click','Enter','Space'):
                search.fill('HBM')
                expect(clear).to_be_visible()
                expect(clear).to_have_accessible_name('Clear search' if language=='en' else '清空搜索')
                geometry=search_clear_geometry(p,scope)
                search.press('Tab');expect(clear).to_be_focused()
                p.keyboard.press('Shift+Tab');expect(search).to_be_focused()
                before=p.evaluate('window.__searchClearEvents')
                if action=='click':clear.click()
                else:clear.focus();clear.press(action)
                assert p.evaluate('window.__searchClearEvents')==before+1
                retained()
            search.fill('   ')
            expect(clear).to_be_visible()
            before=p.evaluate('window.__searchClearEvents')
            clear.click();assert p.evaluate('window.__searchClearEvents')==before+1
            retained()
            # An already-empty authored action has no second input/history effect.
            before=p.evaluate('window.__searchClearEvents')
            clear.evaluate('(n)=>n.click()')
            assert p.evaluate('window.__searchClearEvents')==before
            retained()

            search.fill('HBM')
            guard=p.evaluate("""scope=>{
              const n=document.querySelector('[data-gmi-filter="'+scope+'"]');
              return [{isComposing:true},{keyCode:229},{consumed:true}].map(options=>{
                const e=new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true,...options});
                if(options.consumed)e.preventDefault();
                n.dispatchEvent(e);return {value:n.value,prevented:e.defaultPrevented};
              });
            }""",scope)
            assert all(x['value']=='HBM' for x in guard),guard
            assert [x['prevented'] for x in guard]==[False,False,True]
            before=p.evaluate('window.__searchClearEvents')
            search.press('Escape')
            assert p.evaluate('window.__searchClearEvents')==before+1
            retained()

            search.fill('HBM');clear.focus()
            focused_url=p.url
            other='zh' if language=='en' else 'en'
            p.evaluate('(v)=>document.documentElement.setAttribute("data-lang",v)',other)
            expect(clear).to_have_accessible_name('清空搜索' if other=='zh' else 'Clear search')
            expect(clear).to_be_focused();expect(search).to_have_value('HBM')
            assert p.url==focused_url
            p.evaluate('(v)=>document.documentElement.setAttribute("data-lang",v)',language)
            expect(clear).to_have_accessible_name('Clear search' if language=='en' else '清空搜索')
            expect(clear).to_be_focused()
            if (width,language) in ((390,'en'),(320,'zh')):
                path=args.out/f'search-clear-{scope}-{width}-{language}-{theme}.png'
                field.screenshot(path=str(path));report['screenshots'].append(path.name)
            gmi_navigation_fit(p,width,language)

            if scope=='index':
                # Existing URL restoration may hide the focused suffix.
                p.evaluate("""()=>{const q=new URLSearchParams(location.hash.slice(1));q.delete('q');history.pushState(null,'',location.pathname+location.search+'#'+q);dispatchEvent(new PopStateEvent('popstate'));}""")
                expect(search).to_have_value('');expect(clear).not_to_be_visible();expect(search).to_be_focused()
                assert not p.evaluate('window.__searchClearUnsafeHides.length')
                p.go_back();expect(search).to_have_value('HBM');expect(clear).to_be_visible();expect(search).to_be_focused()
                p.go_forward();expect(search).to_have_value('');expect(clear).not_to_be_visible();expect(search).to_be_focused()
                brand=p.locator('.gmi-product-name');brand.focus()
                p.evaluate("""()=>{const q=new URLSearchParams(location.hash.slice(1));q.set('q','HBM');history.replaceState(null,'',location.pathname+location.search+'#'+q);dispatchEvent(new PopStateEvent('popstate'));}""")
                expect(clear).to_be_visible();expect(brand).to_be_focused()
                p.evaluate("""()=>{const q=new URLSearchParams(location.hash.slice(1));q.delete('q');history.replaceState(null,'',location.pathname+location.search+'#'+q);dispatchEvent(new PopStateEvent('popstate'));}""")
                expect(clear).not_to_be_visible();expect(brand).to_be_focused()
                # Initial restoration precedes binding; raw whitespace must still expose Clear.
                p.evaluate("""()=>{const q=new URLSearchParams(location.hash.slice(1));q.set('q','   ');history.replaceState(null,'',location.pathname+location.search+'#'+q);}""")
                p.reload(wait_until='networkidle')
                expect(search).to_have_value('   ');expect(clear).to_be_visible()
                before_reload_clear=p.evaluate('history.length')
                clear.click();expect(search).to_have_value('');expect(search).to_be_focused();expect(clear).not_to_be_visible()
                assert p.evaluate('history.length')==before_reload_clear
                params=parse_qs(urlsplit(p.url).fragment)
                assert 'q' not in params and params['gmi_return']==[fragment['gmi_return']]
            report.setdefault('search_clear',[]).append({'scope':scope,'width':width,'language':language,'theme':theme,'initial_geometry':original,'active_geometry':geometry,'one_input_per_activation':True,'guarded_escape':guard,'history_and_focus_verified':True})

    def search_clear_static(scope, language):
        with context(320,'light',language,java_script_enabled=False,reduced_motion='reduce') as c:
            p=page_for(c,'gmi.html' if scope=='tree' else 'gmi-index.html')
            if scope=='tree':p.locator('.gmi-advanced > summary').click()
            search=p.locator('[data-gmi-filter="'+scope+'"]');field=search.locator('xpath=..')
            clear=field.locator('[data-gmi-search-clear]')
            assert clear.count()==1
            expect(clear).not_to_be_visible()
            assert not field.evaluate('(n)=>n.classList.contains("gmi-search--clearable")')
            before=field.bounding_box()
            search.fill('HBM');expect(clear).not_to_be_visible()
            after=field.bounding_box()
            assert after and before and all(after[key]==before[key] for key in ('x','width','height'))
            links=p.locator('.gmi-tree a[data-topic-select]' if scope=='tree' else 'a.gmi-irow-name')
            assert links.count()==371 and links.evaluate_all('(nodes)=>nodes.every(n=>n.getAttribute("href"))')
            report.setdefault('search_clear_static',[]).append({'scope':scope,'language':language,'native_links':371,'custom_button_hidden':True,'enhancement_class_absent':True})

    for scope in ('tree','index'):
        for width in (1440,390,320):
            for language in ('en','zh'):
                check(f'search-clear-{scope}-{width}-{language}',lambda s=scope,w=width,l=language:search_clear_paths(s,w,l))
        for language in ('en','zh'):
            check(f'search-clear-static-{scope}-{language}',lambda s=scope,l=language:search_clear_static(s,l))
    check('search-clear-tree-390-en-dark',lambda:search_clear_paths('tree',390,'en','dark'))
    check('search-clear-index-320-zh-dark',lambda:search_clear_paths('index',320,'zh','dark'))

    def index_header_geometry(p):
        """Measure real header/search geometry without changing product state."""
        return p.evaluate('''()=>{
          const rect=n=>{if(!n)return null;const r=n.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top+scrollY,bottom:r.bottom+scrollY,width:r.width,height:r.height};};
          const header=document.querySelector('.gmi-product-head'),title=document.querySelector('h1');
          return {header:rect(header),title:rect(title),brand:rect(document.querySelector('.gmi-product-name')),
            snapshot:rect(document.querySelector('[data-gmi-snapshot]')),nav:rect(document.querySelector('.gmi-product-nav')),
            returned:rect(document.querySelector('.gmi-return-context')),search:rect(document.querySelector('[data-gmi-filter="index"]').closest('.gmi-search')),
            brain:rect(document.querySelector('#gmi-brain-slot #mmb-boot')),
            rightPadding:parseFloat(getComputedStyle(header).paddingRight),titleSize:parseFloat(getComputedStyle(title).fontSize),
            titleTracking:getComputedStyle(title).letterSpacing,overflow:document.documentElement.scrollWidth>innerWidth};
        }''')

    def index_header_paths(width, language, theme='light', stale=False, consolidated=True):
        """Compare real entry states, preserving snapshot, return and Brain owners."""
        research='gmi.html#'+urlencode({'theme':'theme:hbm_packaging','scope':'core','evidence':'1','lens':'chain','q':'Micron'})
        company='gmi-companies.html#'+urlencode({'gmi_return':research,'q':'Micron'})
        entries=(('direct',''),('research',research),('company',company))
        with context(width,theme,language,reduced_motion='reduce') as c:
            # This clock is a fixture: it tests the existing seven-day qualification.
            c.add_init_script('Date.now=()=>Date.UTC(2026,10,'+('20' if stale else '9')+');')
            for entry,returned in entries:
                params={'lens':'chain','fixture_key':'retained'}
                if returned:params['gmi_return']=returned
                p=page_for(c,'gmi-index.html?fixture=index-header#'+urlencode(params))
                initial_url=p.url
                title=p.locator('h1')
                expect(title).to_have_count(1)
                expect(title).to_have_text('All micro-themes全部细分主题')
                assert title.inner_text().strip()==('All micro-themes' if language=='en' else '全部细分主题')
                assert p.locator('.gmi-head').count()==(0 if consolidated else 1)
                assert p.locator('.gmi-product-head > div:first-child > p').count()==(0 if consolidated else 1)
                if consolidated:expect(title).to_have_class('gmi-product-index-title')
                snapshot=p.locator('[data-gmi-snapshot]')
                expect(snapshot).to_have_attribute('data-gmi-snapshot','2026-11-03')
                date='3 Nov 2026' if language=='en' else '2026年11月3日'
                assert snapshot.inner_text().count(date)==1
                assert p.locator('main').inner_text().count(date)==(1 if consolidated else 2)
                if stale:expect(p.locator('.gmi-snapshot-stale')).to_be_visible()
                else:expect(p.locator('.gmi-snapshot-stale')).not_to_be_visible()
                assert p.evaluate('document.activeElement===document.body')
                assert parse_qs(urlsplit(p.url).fragment)=={k:[v] for k,v in params.items()}
                assert p.locator('#gmi-brain-slot').count()==1
                assert p.locator('#gmi-brain-slot').evaluate('(n)=>n.childElementCount')==0
                brand=p.locator('.gmi-product-name')
                if returned:
                    action=p.locator('[data-gmi-return]')
                    expect(action).to_be_visible()
                    expected_label=('Back to company results' if entry=='company' else 'Back to theme research') if language=='en' else ('返回公司结果' if entry=='company' else '返回主题研究')
                    assert action.inner_text().strip()==expected_label
                    actual=urlsplit(action.get_attribute('href'))
                    wanted=urlsplit(returned)
                    assert actual.path.split('/')[-1]==wanted.path and parse_qs(actual.fragment)==parse_qs(wanted.fragment)
                    assert p.locator('.gmi-product-nav').evaluate('(n)=>n.nextElementSibling.classList.contains("gmi-return-context")')
                    b=urlsplit(brand.get_attribute('href'));w=urlsplit(research)
                    assert b.path.split('/')[-1]==w.path and parse_qs(b.fragment)==parse_qs(w.fragment)
                else:
                    expect(p.locator('[data-gmi-return]')).to_have_count(0)
                    assert brand.get_attribute('href')=='gmi.html'
                for brain in ('empty','fixture'):
                    if brain=='fixture':
                        p.evaluate('''()=>{
                          const b=document.createElement('button');b.id='mmb-boot';b.type='button';b.textContent='Brain';
                          b.setAttribute('aria-label','Brain fixture');b.setAttribute('data-header-fixture','');
                          b.style.cssText='width:44px;height:44px;min-width:44px;min-height:44px;padding:0;border:1px solid var(--line);border-radius:12px;background:var(--panel2);color:var(--text);font:11px var(--font-ui)';
                          window.__headerBrainFixture=b;document.body.append(b);dispatchEvent(new Event('mm-brain-ready'));
                        }''')
                        assert p.locator('#gmi-brain-slot #mmb-boot').count()==1
                        assert p.evaluate('document.querySelector("#gmi-brain-slot #mmb-boot")===window.__headerBrainFixture')
                    g=index_header_geometry(p)
                    assert not g['overflow'],g
                    assert g['nav']['top']>=g['header']['bottom']-0.5,g
                    assert g['search']['top']>=(g['returned'] or g['nav'])['bottom'],g
                    if consolidated:
                        assert g['brand']['height']>=44 and g['brand']['width']>=44,g
                        assert g['titleSize']==(24 if width<=820 else 32),g
                        assert abs(g['search']['height']-44)<0.5,g
                    if consolidated and language=='zh':assert g['titleTracking'] in ('0px','normal'),g
                    if width<=820:
                        assert g['rightPadding']==72,g
                        if g['brain']:
                            assert g['brain']['height']>=44 and g['brain']['width']>=44,g
                            # The desktop title has its own lower header; the new H1 shares the reserved column.
                            if consolidated:assert g['title']['right']<=g['brain']['left']-1,g
                            assert g['snapshot']['right']<=g['brain']['left']-1,g
                    targets=p.locator('.gmi-product-nav a').evaluate_all('(ns)=>ns.map(n=>{const r=n.getBoundingClientRect();return {left:r.left,right:r.right,height:r.height};})')
                    assert len(targets)==5 and all(n['left']>=0 and n['right']<=width+0.1 and n['height']>=44 for n in targets),targets
                    report.setdefault('index_header',[]).append({'width':width,'language':language,'theme':theme,'stale_fixture':stale,'entry':entry,'brain':brain,'consolidated':consolidated,'geometry':g})
                    if entry=='direct' and brain=='empty' and not stale and (width,language) in ((390,'en'),(320,'zh')):
                        path=args.out/f'index-header-{width}-{language}-{theme}.png';p.screenshot(path=str(path));report['screenshots'].append(path.name)
                    if consolidated and stale and entry=='company' and brain=='fixture':
                        path=args.out/f'index-header-composite-{width}-{language}.png';p.screenshot(path=str(path));report['screenshots'].append(path.name)
                assert p.url==initial_url
                brand.focus();p.keyboard.press('Tab');expect(p.locator('#mmb-boot')).to_be_focused()
                p.keyboard.press('Tab');expect(p.locator('.gmi-product-tabs a').first).to_be_focused()
                if consolidated:
                    search=p.locator('[data-gmi-filter="index"]');search.focus();search.fill('HBM')
                    expect(p.locator('[data-gmi-index-feedback]')).to_be_visible()
                    expect(p.locator('[data-gmi-search-clear]')).to_be_visible()
                    p.locator('[data-gmi-search-clear]').click();expect(search).to_be_focused();expect(search).to_have_value('')
                    assert parse_qs(urlsplit(p.url).fragment)=={k:[v] for k,v in params.items()}
                p.close()

    def index_header_static(width, language):
        """Static navigation is useful without promising JS-derived stale/return/Brain effects."""
        with context(width,'light',language,java_script_enabled=False,reduced_motion='reduce') as c:
            p=page_for(c,'gmi-index.html#gmi_return=gmi.html%23theme%3Dtheme%253Ahbm_packaging')
            title=p.locator('h1');expect(title).to_have_count(1);expect(title).to_have_class('gmi-product-index-title')
            assert title.inner_text().strip()==('All micro-themes' if language=='en' else '全部细分主题')
            date='3 Nov 2026' if language=='en' else '2026年11月3日'
            assert p.locator('main').inner_text().count(date)==1
            expect(p.locator('[data-gmi-snapshot]')).to_have_attribute('data-gmi-snapshot','2026-11-03')
            expect(p.locator('.gmi-snapshot-stale')).not_to_be_visible()
            expect(p.locator('[data-gmi-return]')).to_have_count(0)
            assert p.locator('#gmi-brain-slot').evaluate('(n)=>n.childElementCount')==0
            assert p.locator('.gmi-product-name').get_attribute('href')=='gmi.html'
            links=p.locator('a.gmi-irow-name');assert links.count()==371
            assert links.evaluate_all('(ns)=>ns.every(n=>n.getAttribute("href"))')
            group=p.locator('.gmi-index-group').first;assert group.evaluate('(n)=>n.open')
            group.locator('summary').click();assert not group.evaluate('(n)=>n.open')
            group.locator('summary').click();assert group.evaluate('(n)=>n.open')
            expect(p.locator('[data-gmi-search-clear]')).not_to_be_visible()
            g=index_header_geometry(p)
            assert not g['overflow'] and g['brand']['height']>=44
            gmi_navigation_fit(p,width,language)
            report.setdefault('index_header_static',[]).append({'width':width,'language':language,'native_links':371,'geometry':g,'no_dynamic_return_or_brain':True})

    for width in (1440,390,320):
        for language in ('en','zh'):
            check(f'index-header-{width}-{language}',lambda w=width,l=language:index_header_paths(w,l))
    for width,language in ((320,'en'),(390,'zh'),(768,'en')):
        check(f'index-header-composite-{width}-{language}',lambda w=width,l=language:index_header_paths(w,l,stale=True))
    for width,language in ((390,'en'),(320,'zh')):
        check(f'index-header-dark-{width}-{language}',lambda w=width,l=language:index_header_paths(w,l,'dark'))
    for width in (1440,320):
        for language in ('en','zh'):
            check(f'index-header-static-{width}-{language}',lambda w=width,l=language:index_header_static(w,l))

    def index_category_picker_paths(width, language, theme='light'):
        """Pending native choice, explicit navigation and filtered focus share existing owners."""
        with context(width,theme,language,reduced_motion='reduce') as c:
            c.add_init_script('''(()=>{
              const Native=window.IntersectionObserver;window.__pickerObservers=[];
              window.IntersectionObserver=class extends Native {
                constructor(callback,options){super(callback,options);
                  if(options&&options.rootMargin==='-60px 0px -70% 0px')window.__pickerObservers.push(callback);
                }
              };
            })();''')
            returned='gmi.html#theme=theme:hbm_packaging&q=Micron'
            fragment={'open':'all','lens':'chain','gmi_return':returned,'fixture_key':'retained'}
            p=page_for(c,'gmi-index.html?fixture=category-picker#'+urlencode(fragment))
            picker=p.locator('[data-gmi-category-picker]');go=p.locator('[data-gmi-category-go]')
            assert picker.count()==1 and go.count()==1,'Mobile index has no category select and Go action'
            nav=p.locator('.gmi-jump');track=p.locator('.gmi-jump-track');search=p.locator('[data-gmi-filter="index"]')
            expect(picker).to_be_visible();expect(go).to_be_visible();expect(track).not_to_be_visible()
            expect(picker).to_have_accessible_name('Category' if language=='en' else '类别')
            expect(go).to_have_accessible_name('Go to category' if language=='en' else '前往类别')
            expect(nav).to_have_accessible_name('Categories' if language=='en' else '类别')
            expect(picker).to_have_value('');expect(go).to_be_disabled()
            ids=['technology_software','semiconductors_hardware','energy_power','materials_mining','industrials_defense','healthcare_lifesciences','financial_services','consumer_cyclical','consumer_defensive','crypto_digital_assets']
            assert picker.locator('option').evaluate_all('(ns)=>ns.map(n=>n.value)')==['']+ids
            assert picker.locator('option').first.inner_text()==('Choose category' if language=='en' else '选择类别')
            assert picker.locator('option[value="crypto_digital_assets"]').inner_text()==('Crypto & digital assets · 0' if language=='en' else '加密与数字资产 · 0')
            assert not picker.locator('option[value="crypto_digital_assets"]').is_disabled()
            geometry=p.evaluate('''()=>{
              const r=s=>{const n=document.querySelector(s),b=n.getBoundingClientRect();return {left:b.left,right:b.right,width:b.width,height:b.height};};
              return {picker:r('[data-gmi-category-picker]'),go:r('[data-gmi-category-go]'),nav:r('.gmi-jump'),overflow:document.documentElement.scrollWidth>innerWidth};
            }''')
            assert geometry['picker']['height']==44 and geometry['go']['height']==44 and geometry['go']['width']==44,geometry
            assert geometry['nav']['height']==61 and not geometry['overflow'],geometry
            assert geometry['picker']['right']<=geometry['go']['left']-8 and geometry['go']['right']<=width,geometry
            if (width,language,theme) in ((390,'en','light'),(320,'zh','dark')):
                path=args.out/f'category-picker-empty-{width}-{language}-{theme}.png'
                p.screenshot(path=str(path),full_page=False);report['screenshots'].append(path.name)
            p.evaluate('''()=>{
              const scroll=Element.prototype.scrollIntoView;window.__pickerJumps=[];window.__pickerUnsafe=[];
              Element.prototype.scrollIntoView=function(options){if(this.matches('[data-gmi-index] > details'))window.__pickerJumps.push(this.id);return scroll.call(this,options);};
              const hidden=Object.getOwnPropertyDescriptor(HTMLElement.prototype,'hidden');
              Object.defineProperty(HTMLElement.prototype,'hidden',{...hidden,set(v){
                if(v&&this.matches('.gmi-jump,.gmi-jump-track,[data-gmi-category-picker-control]')&&this.contains(document.activeElement))window.__pickerUnsafe.push('hide-focused-owner');
                hidden.set.call(this,v);
              }});
              const disabled=Object.getOwnPropertyDescriptor(HTMLButtonElement.prototype,'disabled');
              Object.defineProperty(HTMLButtonElement.prototype,'disabled',{...disabled,set(v){
                if(v&&this.matches('[data-gmi-category-go]')&&this===document.activeElement)window.__pickerUnsafe.push('disable-focused-go');
                disabled.set.call(this,v);
              }});
              document.querySelector('.gmi-jump a[href="#energy_power"]').addEventListener('click',()=>{window.__energyLinkClicks=(window.__energyLinkClicks||0)+1;});
            }''')
            original_url=p.url;history=p.evaluate('history.length')
            opened=p.locator('[data-gmi-index] > details').evaluate_all('(ns)=>ns.map(n=>n.open)')
            picker.focus();before_scroll=p.evaluate('scrollY')
            if language=='en':
                # Real typeahead is observed; OS popup key handling is not simulated or claimed.
                p.keyboard.type('Energy',delay=15)
                expect(picker).to_have_value('energy_power')
            else:
                picker.select_option('energy_power')
            assert p.url==original_url and p.evaluate('history.length')==history
            assert p.evaluate('scrollY')==before_scroll and p.evaluate('window.__pickerJumps')==[]
            assert p.locator('[data-gmi-index] > details').evaluate_all('(ns)=>ns.map(n=>n.open)')==opened
            expect(go).to_be_enabled()
            energy=p.locator('#energy_power')
            for action in ('Enter','Space','click'):
                energy.evaluate('(n)=>{n.open=false;}');p.evaluate('scrollTo(0,0)')
                go.focus();before=p.evaluate('window.__pickerJumps.length')
                if action=='click':go.click()
                else:go.press(action)
                assert energy.evaluate('(n)=>n.open')
                assert p.evaluate('window.__pickerJumps.length')==before+1
                assert p.evaluate('window.__pickerJumps.at(-1)')=='energy_power'
                expect(picker).to_have_value('energy_power');expect(go).to_be_focused()
                assert p.url==original_url and p.evaluate('history.length')==history
                sticky=p.evaluate('''()=>{const n=document.querySelector('.gmi-jump').getBoundingClientRect(),h=document.querySelector('#energy_power > summary').getBoundingClientRect();return {navTop:n.top,navBottom:n.bottom,headingTop:h.top};}''')
                assert abs(sticky['navTop'])<1 and sticky['headingTop']>=sticky['navBottom']-0.5,sticky
            assert p.evaluate('window.__energyLinkClicks')==3
            # An available empty category is still a destination, including the final category.
            picker.select_option('crypto_digital_assets');go.click()
            expect(picker).to_have_value('crypto_digital_assets')
            assert p.locator('#crypto_digital_assets').evaluate('(n)=>n.open')
            last=p.evaluate('''()=>{const n=document.querySelector('.gmi-jump').getBoundingClientRect(),h=document.querySelector('#crypto_digital_assets > summary').getBoundingClientRect();return {navBottom:n.bottom,headingTop:h.top,viewport:innerHeight};}''')
            assert last['navBottom']-0.5<=last['headingTop']<last['viewport'],last
            # Passive current-category observation cannot replace a user's pending destination.
            passive=p.evaluate('''()=>{
              const s=document.querySelector('[data-gmi-category-picker]'),nodes=[...s.options],value=s.value;
              window.__pickerObservers.forEach(cb=>cb([{target:document.getElementById('semiconductors_hardware'),isIntersecting:true}]));
              return {value:s.value,before:value,same:nodes.every((n,i)=>s.options[i]===n)};
            }''')
            assert passive=={'value':'crypto_digital_assets','before':'crypto_digital_assets','same':True}

            def restore(query):
                p.evaluate('''q=>{const h=new URLSearchParams(location.hash.slice(1));if(q)h.set('q',q);else h.delete('q');
                  history.replaceState(null,'',location.pathname+location.search+'#'+h);dispatchEvent(new PopStateEvent('popstate'));}''',query)
                expect(search).to_have_value(query)

            p.evaluate('scrollTo(0,0)')
            disclosure_snapshot=p.locator('[data-gmi-index] > details').evaluate_all('(ns)=>ns.map(n=>n.open)')
            search.fill('HBM')
            assert picker.locator('option').evaluate_all('(ns)=>ns.map(n=>n.value)')==['','semiconductors_hardware']
            expect(picker).to_have_value('');expect(go).to_be_disabled();expect(search).to_be_focused()
            picker.select_option('semiconductors_hardware');go.focus()
            restore('HBM & advanced packaging')
            expect(picker).to_have_value('semiconductors_hardware');expect(go).to_be_focused();expect(go).to_be_enabled()
            assert picker.locator('option').last.inner_text().endswith(' · 1')
            other='zh' if language=='en' else 'en';locale_url=p.url
            p.evaluate('(v)=>document.documentElement.setAttribute("data-lang",v)',other)
            expect(picker).to_have_accessible_name('类别' if other=='zh' else 'Category')
            expect(go).to_have_accessible_name('前往类别' if other=='zh' else 'Go to category')
            expect(nav).to_have_accessible_name('类别' if other=='zh' else 'Categories')
            assert picker.locator('option').last.inner_text()==('半导体与硬件 · 1' if other=='zh' else 'Semiconductors & hardware · 1')
            expect(go).to_be_focused();expect(picker).to_have_value('semiconductors_hardware');assert p.url==locale_url
            repeated=p.evaluate('''()=>{
              const s=document.querySelector('[data-gmi-category-picker]'),nodes=[...s.options];
              document.dispatchEvent(new Event('langchange'));document.dispatchEvent(new Event('langchange'));
              return nodes.every((n,i)=>s.options[i]===n);
            }''')
            assert repeated
            restore('zz-category-no-match');expect(nav).not_to_be_visible();expect(search).to_be_focused()
            p.locator('[data-gmi-search-clear]').click();expect(search).to_be_focused()
            expect(nav).to_be_visible();expect(picker).to_have_value('');expect(go).to_be_disabled()
            assert picker.locator('option').count()==11
            assert p.locator('[data-gmi-index] > details').evaluate_all('(ns)=>ns.map(n=>n.open)')==disclosure_snapshot
            picker.select_option('energy_power');go.focus();restore('HBM')
            expect(picker).to_be_focused();expect(picker).to_have_value('');expect(go).to_be_disabled()
            assert picker.locator('option').count()==2
            picker.select_option('semiconductors_hardware');picker.focus()
            p.evaluate('window.__pendingPickerOptions=[...document.querySelector("[data-gmi-category-picker]").options]')
            restore('  HBM  ')
            expect(picker).to_be_focused();expect(picker).to_have_value('semiconductors_hardware')
            assert p.evaluate('window.__pendingPickerOptions.every((n,i)=>document.querySelector("[data-gmi-category-picker]").options[i]===n)')
            p.evaluate('(v)=>document.documentElement.setAttribute("data-lang",v)',language)
            expect(picker).to_have_accessible_name('Category' if language=='en' else '类别')
            if (width,language,theme) in ((390,'en','light'),(320,'zh','dark'),(320,'en','light'),(390,'zh','light')):
                p.evaluate('scrollTo(0,0)')
                path=args.out/f'category-picker-filtered-{width}-{language}-{theme}.png'
                p.screenshot(path=str(path),full_page=False);report['screenshots'].append(path.name)
            restore('')
            # A destination can disappear between selection and activation. No stale jump or fallback is legal.
            rejected=[]
            for fault in ('group-hidden','group-detached','group-reparented','link-hidden','link-detached','link-reparented'):
                picker.select_option('energy_power');go.focus()
                result=p.evaluate('''fault=>{
                  const link=document.querySelector('.gmi-jump a[href="#energy_power"]'),group=document.getElementById('energy_power');
                  const node=fault.startsWith('group')?group:link,parent=node.parentNode,next=node.nextSibling,hidden=node.hidden;
                  const url=location.href,scroll=scrollY,jumps=window.__pickerJumps.length,opened=group.open;
                  if(fault.endsWith('hidden'))node.hidden=true;else if(fault.endsWith('detached'))node.remove();else document.body.append(node);
                  document.querySelector('[data-gmi-category-go]').click();
                  const result={fault,urlSame:location.href===url,scrollSame:scrollY===scroll,jumps:window.__pickerJumps.length-jumps,openedSame:group.open===opened,
                    value:document.querySelector('[data-gmi-category-picker]').value,disabled:document.querySelector('[data-gmi-category-go]').disabled,
                    focus:document.activeElement.matches('[data-gmi-category-picker]')};
                  if(node.parentNode!==parent)parent.insertBefore(node,next);node.hidden=hidden;document.dispatchEvent(new Event('langchange'));return result;
                }''',fault)
                assert result=={'fault':fault,'urlSame':True,'scrollSame':True,'jumps':0,'openedSame':True,'value':'','disabled':True,'focus':True},result
                rejected.append(result)
            assert not p.evaluate('window.__pickerUnsafe'),p.evaluate('window.__pickerUnsafe')
            assert p.evaluate('history.length')==history
            assert parse_qs(urlsplit(p.url).fragment)=={k:[v] for k,v in fragment.items()}
            assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
            report.setdefault('category_picker',[]).append({'width':width,'language':language,'theme':theme,'geometry':geometry,'native_typeahead':language=='en','native_go_activations':['Enter','Space','click'],
                'delegated_link_clicks':3,'empty_last_category':last,'passive_observer_preserved_pending_choice':True,'invalid_destinations':rejected,'unsafe_focus_transitions':0})

    def index_category_picker_responsive(language):
        """Only the outgoing responsive presentation may transfer focus at 640/641 pixels."""
        with context(1440,'light',language,reduced_motion='reduce') as c:
            p=page_for(c,'gmi-index.html#open=all&lens=chain')
            picker=p.locator('[data-gmi-category-picker]');go=p.locator('[data-gmi-category-go]')
            assert picker.count()==1
            track=p.locator('.gmi-jump-track');holder=p.locator('[data-gmi-category-picker-control]')
            energy=p.locator('.gmi-jump a[href="#energy_power"]');brand=p.locator('.gmi-product-name')
            expect(track).to_be_visible();expect(holder).not_to_be_visible()
            assert p.locator('.gmi-jump a:visible').count()==10
            p.evaluate('''()=>{
              window.__resizeUnsafe=[];const d=Object.getOwnPropertyDescriptor(HTMLElement.prototype,'hidden');
              Object.defineProperty(HTMLElement.prototype,'hidden',{...d,set(v){
                if(v&&this.matches('.gmi-jump-track,[data-gmi-category-picker-control]')&&this.contains(document.activeElement))window.__resizeUnsafe.push(true);
                d.set.call(this,v);
              }});
            }''')
            original=p.url;energy.focus();p.set_viewport_size({'width':640,'height':844})
            expect(picker).to_be_visible();expect(picker).to_be_focused();expect(track).not_to_be_visible()
            expect(picker).to_have_value('energy_power');expect(go).to_be_enabled()
            go.focus();p.set_viewport_size({'width':641,'height':844})
            expect(track).to_be_visible();expect(energy).to_be_focused();expect(holder).not_to_be_visible()
            p.locator('.gmi-jump a[href="#semiconductors_hardware"]').focus()
            p.set_viewport_size({'width':320,'height':844})
            expect(picker).to_be_visible();expect(picker).to_be_focused();expect(picker).to_have_value('semiconductors_hardware')
            brand.focus();p.set_viewport_size({'width':641,'height':844});expect(holder).not_to_be_visible();expect(brand).to_be_focused()
            p.set_viewport_size({'width':640,'height':844});expect(picker).to_be_visible();expect(brand).to_be_focused()
            expect(picker).to_have_value('semiconductors_hardware')
            picker.select_option('energy_power');go.click();expect(go).to_be_focused()
            assert p.evaluate('scrollY')>1000
            p.evaluate('''()=>{
              const focus=HTMLElement.prototype.focus;window.__responsiveFocusDeltas=[];
              HTMLElement.prototype.focus=function(options){const before=scrollY;const result=focus.call(this,options);
                window.__responsiveFocusDeltas.push({before,after:scrollY});return result;};
            }''')
            p.set_viewport_size({'width':641,'height':844});expect(energy).to_be_focused()
            focus_moves=p.evaluate('window.__responsiveFocusDeltas')
            assert focus_moves and all(abs(x['after']-x['before'])<1 for x in focus_moves),focus_moves
            p.set_viewport_size({'width':640,'height':844});expect(picker).to_be_focused()
            go.focus()
            p.locator('[data-gmi-index] > details').evaluate_all('(ns)=>ns.forEach(n=>{n.hidden=true;})')
            p.set_viewport_size({'width':641,'height':844})
            expect(p.locator('[data-gmi-filter="index"]')).to_be_focused();expect(holder).not_to_be_visible()
            assert p.url==original and not p.evaluate('window.__resizeUnsafe')
            assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
            report.setdefault('category_picker_responsive',[]).append({'language':language,'widths':[1440,640,641,320,641,640,641,640,641],'owned_focus_only':True,'focused_destination_preserved':True,'late_category_focus_moves':focus_moves,'all_stale_search_fallback':True,'unsafe_hides':0,'url_preserved':True})

    def index_category_picker_no_observer(language):
        """Progressive category navigation does not require current-category observation."""
        with context(320,'light',language,reduced_motion='reduce') as c:
            c.add_init_script('delete window.IntersectionObserver;')
            p=page_for(c,'gmi-index.html#open=all&lens=chain')
            picker=p.locator('[data-gmi-category-picker]');go=p.locator('[data-gmi-category-go]')
            assert picker.count()==1;expect(picker).to_be_visible();expect(go).to_be_disabled()
            original=p.url;picker.select_option('energy_power');go.click()
            assert p.locator('#energy_power').evaluate('(n)=>n.open') and p.url==original
            p.locator('[data-gmi-filter="index"]').fill('HBM')
            assert picker.locator('option').evaluate_all('(ns)=>ns.map(n=>n.value)')==['','semiconductors_hardware']
            picker.select_option('semiconductors_hardware');go.press('Enter')
            assert p.locator('a.gmi-irow-name:visible').count()==2
            assert parse_qs(urlsplit(p.url).fragment)=={'open':['all'],'lens':['chain'],'q':['HBM']}
            report.setdefault('category_picker_no_observer',[]).append({'language':language,'filtered_navigation':True})

    def index_category_picker_static(width, language):
        """With scripts disabled, authored links and disclosures remain the useful controls."""
        with context(width,'light',language,java_script_enabled=False,reduced_motion='reduce') as c:
            p=page_for(c,'gmi-index.html')
            expect(p.locator('[data-gmi-category-picker-control]')).not_to_be_visible()
            expect(p.locator('[data-gmi-category-go]')).not_to_be_visible()
            expect(p.locator('.gmi-jump-track')).to_be_visible()
            assert p.locator('.gmi-jump a:visible').count()==10
            assert p.locator('a.gmi-irow-name').count()==371
            assert p.locator('a.gmi-irow-name').evaluate_all('(ns)=>ns.every(n=>n.getAttribute("href"))')
            p.locator('.gmi-jump a[href="#energy_power"]').click()
            assert urlsplit(p.url).fragment=='energy_power'
            group=p.locator('#energy_power');assert group.evaluate('(n)=>n.open')
            group.locator('summary').click();assert not group.evaluate('(n)=>n.open')
            assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
            report.setdefault('category_picker_static',[]).append({'width':width,'language':language,'native_categories':10,'native_topics':371,'no_inert_custom_action':True})

    for width in (390,320):
        for language in ('en','zh'):
            check(f'category-picker-{width}-{language}',lambda w=width,l=language:index_category_picker_paths(w,l))
    for width,language in ((390,'en'),(320,'zh')):
        check(f'category-picker-dark-{width}-{language}',lambda w=width,l=language:index_category_picker_paths(w,l,'dark'))
    for language in ('en','zh'):
        check(f'category-picker-responsive-{language}',lambda l=language:index_category_picker_responsive(l))
        check(f'category-picker-no-observer-{language}',lambda l=language:index_category_picker_no_observer(l))
        for width in (1440,320):
            check(f'category-picker-static-{width}-{language}',lambda w=width,l=language:index_category_picker_static(w,l))


    def company_entry_geometry(p):
        return p.evaluate('''()=>{
          const rect=n=>{if(!n)return null;const b=n.getBoundingClientRect();return {left:b.left,right:b.right,top:b.top+scrollY,bottom:b.bottom+scrollY,width:b.width,height:b.height};};
          const header=document.querySelector('.gmi-product-head'),title=document.querySelector('h1');
          return {header:rect(header),title:rect(title),brand:rect(document.querySelector('.gmi-product-name')),
            snapshot:rect(document.querySelector('[data-gmi-snapshot]')),nav:rect(document.querySelector('.gmi-product-nav')),
            returned:rect(document.querySelector('.gmi-return-context')),search:rect(document.querySelector('[data-company-search]').closest('label')),
            firstCard:rect(document.querySelector('[data-company-card]')),brain:rect(document.querySelector('#gmi-brain-slot #mmb-boot')),
            rightPadding:parseFloat(getComputedStyle(header).paddingRight),titleSize:parseFloat(getComputedStyle(title).fontSize),titleTracking:getComputedStyle(title).letterSpacing,
            overflow:document.documentElement.scrollWidth>innerWidth};
        }''')

    def company_entry_header(width, language, theme='light', stale=False, consolidated=True):
        """Move the task title ahead of search while preserving the single snapshot and record dates."""
        research='gmi.html#'+urlencode({'theme':'theme:hbm_packaging','scope':'core','evidence':'1','lens':'chain','q':'Micron'})
        with context(width,theme,language,reduced_motion='reduce') as c:
            c.add_init_script('Date.now=()=>Date.UTC(2026,10,'+('20' if stale else '9')+');')
            for entry,returned in (('direct',''),('research',research)):
                params={'q':'Micron','lens':'chain','fixture_key':'retained'}
                if returned:params['gmi_return']=returned
                p=page_for(c,'gmi-companies.html?fixture=company-entry#'+urlencode(params))
                initial=p.url;title=p.locator('h1');brand=p.locator('.gmi-product-name')
                expect(title).to_have_count(1)
                assert title.inner_text().strip()==('Company evidence' if language=='en' else '公司证据')
                assert p.locator('.gmi-head').count()==(0 if consolidated else 1)
                assert p.locator('.gmi-product-head > div:first-child > p').count()==(0 if consolidated else 1)
                if consolidated:expect(title).to_have_class('gmi-product-page-title')
                snapshot=p.locator('[data-gmi-snapshot]')
                expect(snapshot).to_have_attribute('data-gmi-snapshot','2026-11-03')
                date='3 Nov 2026' if language=='en' else '2026年11月3日'
                assert p.locator('main').inner_text().count(date)==1
                if stale:expect(p.locator('.gmi-snapshot-stale')).to_be_visible()
                else:expect(p.locator('.gmi-snapshot-stale')).not_to_be_visible()
                assert p.evaluate('document.activeElement===document.body')
                assert p.locator('#gmi-brain-slot').count()==1
                card=p.locator('[data-company-card]');expect(card).to_have_count(1);expect(card).to_be_visible()
                assert ('26 Feb 2024' if language=='en' else '2024年2月26日') in card.inner_text()
                assert ('Planned' if language=='en' else '计划中') in card.inner_text()
                expect(p.locator('[data-company-guide]')).to_be_visible()
                if consolidated:
                    expect(p.locator('[data-company-count]')).to_have_text('1 matching company' if language=='en' else '匹配到 1 家公司')
                assert ('current delivery and revenue exposure are not established' if language=='en' else '尚未证实当前交付或营收敞口') in card.inner_text()
                expect(p.locator('.gmi-product-tabs a').nth(1)).to_have_attribute('aria-current','page')
                if returned:
                    back=p.locator('[data-gmi-return]');expect(back).to_be_visible()
                    assert back.inner_text().strip()==('Back to theme research' if language=='en' else '返回主题研究')
                    for link in (back,brand):
                        actual=urlsplit(link.get_attribute('href'));wanted=urlsplit(returned)
                        assert actual.path.split('/')[-1]==wanted.path and parse_qs(actual.fragment)==parse_qs(wanted.fragment)
                    assert p.locator('.gmi-product-nav').evaluate('(n)=>n.nextElementSibling.classList.contains("gmi-return-context")')
                else:
                    expect(p.locator('[data-gmi-return]')).to_have_count(0)
                    assert brand.get_attribute('href')=='gmi.html'
                for brain in ('empty','fixture'):
                    if brain=='fixture':
                        p.evaluate('''()=>{
                          const b=document.createElement('button');b.id='mmb-boot';b.type='button';b.textContent='Brain';b.setAttribute('aria-label','Brain fixture');
                          b.style.cssText='width:44px;height:44px;min-width:44px;min-height:44px;padding:0;border:1px solid var(--line);border-radius:12px;background:var(--panel2);color:var(--text);font:11px var(--font-ui)';
                          window.__companyBrainFixture=b;document.body.append(b);dispatchEvent(new Event('mm-brain-ready'));
                        }''')
                        assert p.evaluate('document.querySelector("#gmi-brain-slot #mmb-boot")===window.__companyBrainFixture')
                    g=company_entry_geometry(p)
                    assert not g['overflow'] and g['nav']['top']>=g['header']['bottom']-0.5,g
                    assert g['search']['top']>=(g['returned'] or g['nav'])['bottom']-0.5,g
                    if consolidated:
                        assert g['brand']['height']>=44 and g['brand']['width']>=44,g
                        assert g['titleSize']==(24 if width<=820 else 32),g
                        if language=='zh':assert g['titleTracking'] in ('normal','0px'),g
                    if width<=820:
                        assert g['rightPadding']==72,g
                        if g['brain']:
                            if consolidated:assert g['title']['right']<=g['brain']['left']-1,g
                            assert g['snapshot']['right']<=g['brain']['left']-1,g
                    gmi_navigation_fit(p,width,language)
                    report.setdefault('company_entry_header',[]).append({'width':width,'language':language,'theme':theme,'stale_fixture':stale,'entry':entry,'brain':brain,'consolidated':consolidated,'geometry':g})
                    if entry=='direct' and brain=='empty' and not stale and (width,language) in ((390,'en'),(320,'zh')):
                        path=args.out/f'company-entry-{width}-{language}-{theme}.png';p.screenshot(path=str(path));report['screenshots'].append(path.name)
                    if consolidated and stale and entry=='research' and brain=='fixture':
                        path=args.out/f'company-entry-composite-{width}-{language}.png';p.screenshot(path=str(path));report['screenshots'].append(path.name)
                assert p.url==initial
                brand.focus();p.keyboard.press('Tab');expect(p.locator('#mmb-boot')).to_be_focused()
                p.keyboard.press('Tab');expect(p.locator('.gmi-product-tabs a').first).to_be_focused()
                p.close()

    def company_entry_focus(width, language):
        """Reset/history release owned focus before hiding; equal counts do not announce again."""
        with context(width,'light',language,reduced_motion='reduce') as c:
            returned='gmi.html#theme=theme:hbm_packaging&q=Micron&scope=core&lens=chain'
            fragment={'gmi_return':returned,'lens':'chain','fixture_key':'retained'}
            p=page_for(c,'gmi-companies.html?fixture=company-focus#'+urlencode(fragment))
            search=p.locator('[data-company-search]');card=p.locator('[data-company-card]');empty=p.locator('[data-company-empty]');reset=p.locator('[data-company-reset]');status=p.locator('[data-company-count]')
            source=card.locator('a[target="_blank"]').first;issuer=card.locator('a[href*="gmi-issuer-"]')
            assert card.count()==1 and source.get_attribute('href').startswith('https://')
            assert 'noopener' in source.get_attribute('rel')
            p.evaluate('''()=>{
              window.__companyUnsafe=[];window.__companyWrites=[];window.__companyCountMutations=[];
              window.__companyOriginalCard=document.querySelector('[data-company-card]');window.__companyOriginalCount=document.querySelector('[data-company-count]');
              const h=Object.getOwnPropertyDescriptor(HTMLElement.prototype,'hidden');
              Object.defineProperty(HTMLElement.prototype,'hidden',{...h,set(value){
                if(this.matches('[data-company-card],[data-company-empty]')){
                  window.__companyWrites.push({card:this.matches('[data-company-card]'),value});
                  if(value&&this.contains(document.activeElement))window.__companyUnsafe.push(this.matches('[data-company-card]')?'card':'empty');
                }
                h.set.call(this,value);
              }});
              window.__companyCountObserver=new MutationObserver(records=>window.__companyCountMutations.push(...records.map(r=>r.type)));
              window.__companyCountObserver.observe(window.__companyOriginalCount,{subtree:true,childList:true,characterData:true});
              const replace=history.replaceState.bind(history);window.__companyReplaceCalls=0;
              history.replaceState=function(...args){window.__companyReplaceCalls++;return replace(...args);};
            }''')
            initial_history=p.evaluate('history.length')
            for activation in ('click','Enter','Space'):
                search.fill('no-company-entry-match');expect(empty).to_be_visible();expect(card).not_to_be_visible()
                reset.focus();before=p.evaluate('window.__companyReplaceCalls')
                if activation=='click':reset.click()
                else:reset.press(activation)
                expect(search).to_be_focused();expect(search).to_have_value('');expect(card).to_be_visible();expect(empty).not_to_be_visible()
                assert p.evaluate('window.__companyReplaceCalls')==before+1
                assert p.evaluate('history.length')==initial_history
                assert parse_qs(urlsplit(p.url).fragment)=={k:[v] for k,v in fragment.items()}
            assert not p.evaluate('window.__companyUnsafe'),'Reset hid its focused empty-state owner before releasing focus'
            expect(status).to_have_text('1 company with evidence on file' if language=='en' else '有收录证据的公司：1 家')
            search.fill('   ')
            expect(status).to_have_text('1 company with evidence on file' if language=='en' else '有收录证据的公司：1 家')
            search.fill('Micron')
            expect(status).to_have_text('1 matching company' if language=='en' else '匹配到 1 家公司')
            search.fill('')
            expect(status).to_have_text('1 company with evidence on file' if language=='en' else '有收录证据的公司：1 家')

            def restore(query):
                p.evaluate('''q=>{const h=new URLSearchParams(location.hash.slice(1));if(q)h.set('q',q);else h.delete('q');location.hash=h.toString();}''',query)
                expect(search).to_have_value(query)

            # Both distinct link purposes inside a hidden card must recover safely.
            for focused in (source,issuer):
                restore('Micron');focused.focus();restore('no-company-entry-match')
                expect(search).to_be_focused();expect(card).not_to_be_visible();expect(empty).to_be_visible()
                reset.focus();restore('Micron')
                expect(search).to_be_focused();expect(card).to_be_visible();expect(empty).not_to_be_visible()
            source.focus();restore('HBM');expect(source).to_be_focused()
            guide=p.locator('[data-company-guide] a').first;guide.focus();restore('no-company-entry-match');expect(guide).to_be_focused()
            brand=p.locator('.gmi-product-name');brand.focus();restore('Micron');expect(brand).to_be_focused()
            # Native back/forward restores queries through the existing listener, without a new writer.
            source.focus();p.go_back();expect(search).to_have_value('no-company-entry-match');expect(search).to_be_focused()
            reset.focus();p.go_forward();expect(search).to_have_value('Micron');expect(search).to_be_focused()

            search.fill('no-company-entry-match')
            before=p.evaluate('({count:window.__companyCountMutations.length,hidden:window.__companyWrites.length})')
            search.fill('another-no-company-entry-match')
            assert p.evaluate('({count:window.__companyCountMutations.length,hidden:window.__companyWrites.length})')==before
            search.fill('Micron');source.focus()
            before=p.evaluate('({count:window.__companyCountMutations.length,hidden:window.__companyWrites.length})')
            restore('  micron  ');expect(source).to_be_focused()
            assert p.evaluate('({count:window.__companyCountMutations.length,hidden:window.__companyWrites.length})')==before
            for current in ('zh' if language=='en' else 'en',language):
                before_url=p.url;before_history=p.evaluate('history.length');before=p.evaluate('({count:window.__companyCountMutations.length,hidden:window.__companyWrites.length})')
                p.evaluate('(value)=>document.documentElement.setAttribute("data-lang",value)',current)
                expect(status).to_have_text('匹配到 1 家公司' if current=='zh' else '1 matching company')
                expect(source).to_be_focused()
                after=p.evaluate('({count:window.__companyCountMutations.length,hidden:window.__companyWrites.length})')
                assert after=={'count':before['count']+1,'hidden':before['hidden']},(before,after)
                p.evaluate('(value)=>{document.documentElement.setAttribute("data-lang",value);document.dispatchEvent(new Event("langchange"));}',current)
                assert p.evaluate('({count:window.__companyCountMutations.length,hidden:window.__companyWrites.length})')==after
                assert p.url==before_url and p.evaluate('history.length')==before_history
            assert p.evaluate('window.__companyOriginalCard===document.querySelector("[data-company-card]")&&window.__companyOriginalCount===document.querySelector("[data-company-count]")')
            assert not p.evaluate('window.__companyUnsafe')
            assert parse_qs(urlsplit(p.url).fragment)['gmi_return']==[returned]
            search.fill('no-company-entry-match');reset.focus()
            expect(reset).to_have_accessible_name('Clear search' if language=='en' else '清空搜索')
            if (width,language) in ((390,'en'),(320,'zh')):
                path=args.out/f'company-entry-empty-search-{width}-{language}.png';p.screenshot(path=str(path));report['screenshots'].append(path.name)
            reset.press('Enter');expect(search).to_be_focused();expect(card).to_be_visible()
            assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
            report.setdefault('company_entry_focus',[]).append({'width':width,'language':language,'native_reset':['click','Enter','Space'],'owned_card_and_empty_focus_recovery':True,'surviving_source_guide_navigation_focus_retained':True,'same_count_and_visibility_writes':0,'locale_count_writes':1,'native_history_restoration':True,'card_and_count_identity_retained':True,'unsafe_hides':0})

    def company_entry_static(width, language):
        """Disabled scripts retain the task title, single snapshot and dated native evidence links."""
        with context(width,'light',language,java_script_enabled=False,reduced_motion='reduce') as c:
            p=page_for(c,'gmi-companies.html#gmi_return=gmi.html%23q%3DMicron')
            title=p.locator('h1');expect(title).to_have_count(1);expect(title).to_have_class('gmi-product-page-title')
            assert title.inner_text().strip()==('Company evidence' if language=='en' else '公司证据')
            assert p.locator('.gmi-head').count()==0
            date='3 Nov 2026' if language=='en' else '2026年11月3日';assert p.locator('main').inner_text().count(date)==1
            expect(p.locator('.gmi-snapshot-stale')).not_to_be_visible();expect(p.locator('[data-gmi-return]')).to_have_count(0)
            assert p.locator('#gmi-brain-slot').evaluate('(n)=>n.childElementCount')==0
            assert p.locator('.gmi-product-name').get_attribute('href')=='gmi.html'
            card=p.locator('[data-company-card]');expect(card).to_be_visible()
            assert ('26 Feb 2024' if language=='en' else '2024年2月26日') in card.inner_text()
            assert ('Planned' if language=='en' else '计划中') in card.inner_text()
            source=card.locator('a[target="_blank"]');assert source.get_attribute('href').startswith('https://') and 'noopener' in source.get_attribute('rel')
            assert card.locator('a[href*="gmi-issuer-"]').get_attribute('href')=='gmi-issuer-mu.html'
            p.locator('[data-company-search]').fill('no-company-entry-match')
            expect(card).to_be_visible();expect(p.locator('[data-company-empty]')).not_to_be_visible()
            g=company_entry_geometry(p);assert not g['overflow'] and g['brand']['height']>=44
            report.setdefault('company_entry_static',[]).append({'width':width,'language':language,'dated_native_evidence_links':True,'dynamic_filter_not_fabricated':True,'geometry':g})

    for width in (1440,390,320):
        for language in ('en','zh'):
            check(f'company-entry-header-{width}-{language}',lambda w=width,l=language:company_entry_header(w,l))
            check(f'company-entry-focus-{width}-{language}',lambda w=width,l=language:company_entry_focus(w,l))
    for width,language in ((320,'en'),(390,'zh'),(768,'en')):
        check(f'company-entry-composite-{width}-{language}',lambda w=width,l=language:company_entry_header(w,l,stale=True))
    for width,language in ((390,'en'),(320,'zh')):
        check(f'company-entry-dark-{width}-{language}',lambda w=width,l=language:company_entry_header(w,l,'dark'))
    for language in ('en','zh'):
        for width in (1440,320):
            check(f'company-entry-static-{width}-{language}',lambda w=width,l=language:company_entry_static(w,l))


    def return_context_focus(route, width, language):
        """Retire invalid context without removing focused content or inventing navigation."""
        research='gmi.html#'+urlencode({'theme':'theme:hbm_packaging','scope':'core','evidence':'1','lens':'chain','q':'Micron'})
        alternate='gmi.html#'+urlencode({'theme':'theme:hbm_packaging','q':'HBM','lens':'coverage'})
        catalogue='gmi-companies.html#'+urlencode({'q':'Micron','gmi_return':research})
        with context(width,'light',language,reduced_motion='reduce') as c:
            def fragment(value):
                d={'fixture_key':'return-recovery'}
                if value:d['gmi_return']=value
                return urlencode(d)
            p=page_for(c,route+'#'+fragment(research))
            back=p.locator('[data-gmi-return]');brand=p.locator('a.gmi-product-name[href]')
            expect(back).to_be_visible()
            p.evaluate('''()=>{
              window.__returnRemovals=[];window.__returnFocusCalls=[];
              const remove=Element.prototype.remove,focus=HTMLElement.prototype.focus;
              Element.prototype.remove=function(...args){
                if(this.matches('.gmi-return-context'))window.__returnRemovals.push({owned:this.contains(document.activeElement),target:document.activeElement.className});
                return remove.apply(this,args);
              };
              HTMLElement.prototype.focus=function(options){
                const before=scrollY,result=focus.call(this,options);
                if(this.matches('.gmi-product-name,.gmi-product-nav a'))window.__returnFocusCalls.push({target:this.className,preventScroll:!!options?.preventScroll,before,after:scrollY});
                return result;
              };
              window.__originalReturn= document.querySelector('[data-gmi-return]');
            }''')
            initial_history=p.evaluate('history.length')
            def restore(value):
                p.evaluate('''hash=>{history.replaceState(null,'',location.pathname+location.search+'#'+hash);dispatchEvent(new PopStateEvent('popstate'));}''',fragment(value))
            # The baseline must fail on this actual focused-node removal.
            back.focus();restore('')
            expect(back).to_have_count(0)
            assert not p.evaluate('window.__returnRemovals.some(x=>x.owned)'), 'Return holder removed its focused link before recovery'
            expect(brand).to_be_focused()
            assert brand.get_attribute('href')=='gmi.html'
            assert p.evaluate('window.__returnFocusCalls.at(-1).preventScroll')
            assert p.evaluate('history.length')==initial_history
            assert parse_qs(urlsplit(p.url).fragment)=={'fixture_key':['return-recovery']}
            for rejected in ('https://example.invalid/','javascript:alert(1)','gmi.html?unqualified=1'):
                restore(research);expect(back).to_be_visible();back.focus();restore(rejected)
                expect(back).to_have_count(0);expect(brand).to_be_focused()
                assert brand.get_attribute('href')=='gmi.html'
            # A still-valid return uses the same anchor and preserves focused ownership.
            restore(research);back.focus();p.evaluate('window.__sameReturn=document.querySelector("[data-gmi-return]")')
            for value in (alternate, catalogue if route!='gmi-companies.html' else research):
                restore(value);expect(back).to_be_focused()
                assert p.evaluate('window.__sameReturn===document.querySelector("[data-gmi-return]")')
                actual=urlsplit(back.get_attribute('href'));wanted=urlsplit(value)
                assert actual.path.split('/')[-1]==wanted.path and parse_qs(actual.fragment)==parse_qs(wanted.fragment)
            other='zh' if language=='en' else 'en'
            before_url=p.url
            p.evaluate('(v)=>document.documentElement.setAttribute("data-lang",v)',other)
            expect(back).to_have_text(('返回主题研究' if route=='gmi-companies.html' else '返回公司结果') if other=='zh' else ('Back to theme research' if route=='gmi-companies.html' else 'Back to company results'))
            expect(back).to_be_focused()
            assert p.evaluate('window.__sameReturn===document.querySelector("[data-gmi-return]")') and p.url==before_url
            p.evaluate('(v)=>document.documentElement.setAttribute("data-lang",v)',language)
            # Unrelated focus is left alone, including the company's source link.
            restore(research)
            unrelated=p.locator('[data-company-card] a[target="_blank"]').first if route=='gmi-companies.html' else p.locator('.gmi-product-tabs a').last
            unrelated.focus();restore('');expect(unrelated).to_be_focused();expect(back).to_have_count(0)
            assert p.evaluate('history.length')==initial_history
            # Real hash navigation plus back/forward reaches the same existing listeners.
            restore(research);back.focus()
            p.evaluate('(hash)=>{location.hash=hash;}',fragment(''));expect(back).to_have_count(0);expect(brand).to_be_focused()
            p.go_back();expect(back).to_be_visible();back.focus()
            p.go_forward();expect(back).to_have_count(0);expect(brand).to_be_focused()
            assert p.evaluate('history.length')==initial_history+1
            assert not p.evaluate('window.__returnRemovals.some(x=>x.owned)')
            exceptional=False;scroll_observation=None
            if route=='gmi-relationships.html':
                # Scroll tail is a focus-test fixture only, never used for layout comparison.
                p.evaluate('''()=>{const tail=document.createElement('div');tail.style.height='1800px';document.body.append(tail);}''')
                restore(research);back.focus();p.evaluate('scrollTo(0,300)');position=p.evaluate('scrollY')
                restore('');expect(brand).to_be_focused()
                focused=p.evaluate('window.__returnFocusCalls.at(-1)')
                assert focused['preventScroll'] and focused['before']==position and focused['after']==position,focused
                scroll_observation={'before':position,'after_focus':focused['after'],'after_layout_removal':p.evaluate('scrollY')}
                # Hidden or removed brand falls back to an existing nav link.
                restore(research);back.focus();brand.evaluate('(n)=>n.hidden=true');restore('')
                expect(p.locator('.gmi-product-tabs a').first).to_be_focused();brand.evaluate('(n)=>n.hidden=false')
                restore(research);back.focus()
                p.evaluate('''()=>{window.__brandNode=document.querySelector('.gmi-product-name');window.__brandParent=window.__brandNode.parentNode;window.__brandNode.remove();}''')
                restore('');expect(p.locator('.gmi-product-tabs a').first).to_be_focused()
                p.evaluate('window.__brandParent.prepend(window.__brandNode)')
                # Respect another focus handler that already moves to a surviving destination.
                restore(research);back.focus()
                p.evaluate('''()=>document.querySelector('.gmi-product-name').addEventListener('focus',()=>document.querySelectorAll('.gmi-product-tabs a')[1].focus(),{once:true})''')
                restore('');expect(p.locator('.gmi-product-tabs a').nth(1)).to_be_focused()
                assert not p.evaluate('window.__returnRemovals.some(x=>x.owned)')
                # Malformed fixture with neither usable destination still removes invalid context.
                restore(research);back.focus();brand.evaluate('(n)=>n.hidden=true')
                p.locator('.gmi-product-nav').evaluate('(n)=>n.hidden=true')
                restore('');expect(back).to_have_count(0)
                assert p.evaluate('window.__returnRemovals.at(-1).owned')
                exceptional=True
            assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
            report.setdefault('return_context_focus',[]).append({'route':route,'width':width,'language':language,'ordinary_owned_removal_safe':True,'rejected_returns':3,'valid_anchor_identity_and_locale_focus':True,'unrelated_focus_preserved':True,'real_back_forward':True,'no_product_history_writer':True,'fallback_and_redirect_cases':route=='gmi-relationships.html','missing_all_targets_still_removes_invalid_holder':exceptional,'focus_scroll_observation':scroll_observation})

    def relationship_entry_geometry(p):
        return p.evaluate('''()=>{
          const rect=n=>{if(!n)return null;const b=n.getBoundingClientRect();return {top:b.top+scrollY,bottom:b.bottom+scrollY,left:b.left,right:b.right,width:b.width,height:b.height};};
          const h=document.querySelector('.gmi-product-head');
          return {header:rect(h),title:rect(document.querySelector('h1')),brand:rect(document.querySelector('.gmi-product-name')),snapshot:rect(document.querySelector('[data-gmi-snapshot]')),nav:rect(document.querySelector('.gmi-product-nav')),returned:rect(document.querySelector('.gmi-return-context')),panel:rect(document.querySelector('.gmi-permission-state')),primary:rect(document.querySelector('.gmi-state-actions .gmi-action-primary')),brain:rect(document.querySelector('#gmi-brain-slot #mmb-boot')),rightPadding:parseFloat(getComputedStyle(h).paddingRight),titleSize:parseFloat(getComputedStyle(document.querySelector('h1')).fontSize),overflow:document.documentElement.scrollWidth>innerWidth};
        }''')

    def relationship_entry_header(width, language, theme='light', crowded=False, upgraded=True):
        """Compact task header and qualified recovery; never fabricate a relationship view."""
        research='gmi.html#'+urlencode({'theme':'theme:hbm_packaging','scope':'core','evidence':'1','lens':'chain','q':'Micron'})
        catalogue='gmi-companies.html#'+urlencode({'q':'Micron','gmi_return':research})
        with context(width,theme,language,reduced_motion='reduce') as c:
            c.add_init_script('Date.now=()=>Date.UTC(2026,10,'+('20' if crowded else '9')+');')
            for entry,returned in (('direct',''),('research',research),('catalogue',catalogue)):
                params={'fixture_key':'relationship-entry'}
                if returned:params['gmi_return']=returned
                p=page_for(c,'gmi-relationships.html#'+urlencode(params));initial=p.url
                title=p.locator('h1');expect(title).to_have_count(1)
                assert title.inner_text().strip()==('Company relationships' if language=='en' else '公司关系')
                assert p.locator('.gmi-head').count()==(0 if upgraded else 1)
                assert p.locator('.gmi-product-head > div:first-child > p').count()==(0 if upgraded else 1)
                expect(p.locator('[data-gmi-snapshot]')).to_have_attribute('data-gmi-snapshot','2026-11-03')
                assert p.locator('main').inner_text().count('3 Nov 2026' if language=='en' else '2026年11月3日')==1
                expect(p.locator('.gmi-product-tabs a').last).to_have_attribute('aria-current','page')
                panel=p.locator('.gmi-permission-state');details=p.locator('.gmi-topic-receipt')
                expected=('Public relationship view unavailable' if language=='en' else '暂无公开关系视图') if upgraded else ('No relationships cleared for public display' if language=='en' else '暂无获准公开展示的关系')
                assert panel.locator('h2').inner_text().strip()==expected
                assert ('This is a publication restriction, not a statement that no relationships exist.' if language=='en' else '这是发布限制，并不表示这些关系不存在。') in panel.inner_text()
                assert not p.locator('main [data-company-card], main [data-relationship], main script[type="application/json"]').count()
                assert 'Micron Technology' not in p.locator('main').inner_text()
                actions=panel.locator('.gmi-state-actions a');expect(actions).to_have_count(3 if upgraded else 2)
                expect(details).not_to_have_attribute('open','')
                primary=actions.first
                if upgraded:
                    assert primary.inner_text().strip()==('Browse company evidence' if language=='en' else '浏览公司证据')
                    wanted=catalogue if entry=='catalogue' else 'gmi-companies.html'+('#'+urlencode({'gmi_return':research}) if entry=='research' else '')
                    href=urlsplit(primary.get_attribute('href'));target=urlsplit(wanted)
                    assert href.path.split('/')[-1]==target.path and parse_qs(href.fragment)==parse_qs(target.fragment)
                if returned:
                    back=p.locator('[data-gmi-return]');expect(back).to_be_visible()
                    href=urlsplit(back.get_attribute('href'));target=urlsplit(returned)
                    assert href.path.split('/')[-1]==target.path and parse_qs(href.fragment)==parse_qs(target.fragment)
                else:expect(p.locator('[data-gmi-return]')).to_have_count(0)
                if crowded:
                    expect(p.locator('.gmi-snapshot-stale')).to_be_visible()
                    p.evaluate('''()=>{const b=document.createElement('button');b.id='mmb-boot';b.type='button';b.textContent='Brain';b.style.cssText='width:44px;height:44px;padding:0;border:1px solid var(--line);border-radius:12px;background:var(--panel2);color:var(--text);font:11px var(--font-ui)';document.body.append(b);dispatchEvent(new Event('mm-brain-ready'));}''')
                else:expect(p.locator('.gmi-snapshot-stale')).not_to_be_visible()
                g=relationship_entry_geometry(p)
                assert not g['overflow'] and g['panel']['top']>=(g['returned'] or g['nav'])['bottom']-0.5
                if upgraded:
                    assert g['brand']['height']>=44 and g['titleSize']==(24 if width<=820 else 32)
                    if width<=820:
                        assert g['rightPadding']==72
                        if g['brain']:assert g['title']['right']<=g['brain']['left']-1 and g['snapshot']['right']<=g['brain']['left']-1
                gmi_navigation_fit(p,width,language)
                for n in range(actions.count()):
                    a=actions.nth(n);box=a.bounding_box()
                    assert box['height']>=44 and box['x']>=0 and box['x']+box['width']<=width+1
                assert p.evaluate('document.activeElement===document.body') and p.url==initial
                report.setdefault('relationship_entry_header',[]).append({'width':width,'language':language,'theme':theme,'crowded':crowded,'entry':entry,'upgraded':upgraded,'geometry':g})
                if upgraded and entry==('catalogue' if crowded else 'direct') and (width,language) in ((390,'en'),(320,'zh'),(320,'en'),(390,'zh')):
                    path=args.out/f'relationship-entry-{width}-{language}-{theme}.png';p.screenshot(path=str(path));report['screenshots'].append(path.name)
                p.close()

    def relationship_recovery_paths(width, language):
        """Use the actual local company destination and incumbent return projection."""
        research='gmi.html#'+urlencode({'theme':'theme:hbm_packaging','scope':'core','evidence':'1','lens':'chain','q':'Micron'})
        catalogue='gmi-companies.html#'+urlencode({'q':'Micron','gmi_return':research})
        with context(width,'light',language,reduced_motion='reduce') as c:
            for entry,returned in (('direct',''),('research',research),('catalogue',catalogue),('invalid','https://example.invalid/')):
                params={'gmi_return':returned} if returned else {}
                p=page_for(c,'gmi-relationships.html'+('#'+urlencode(params) if params else ''))
                details=p.locator('.gmi-topic-receipt');summary=details.locator('summary')
                summary.focus();summary.press('Enter');expect(details).to_have_attribute('open','')
                assert ('Theme research and separately cleared company evidence remain available.' if language=='en' else '主题研究与另行获准展示的公司证据仍可使用。') in details.inner_text()
                summary.press('Space');expect(details).not_to_have_attribute('open','')
                primary=p.locator('.gmi-permission-state .gmi-action-primary');primary.focus();primary.press('Enter')
                expect(p.locator('[data-company-card]')).to_have_count(1)
                assert urlsplit(p.url).path.endswith('/gmi-companies.html')
                expected={'q':['Micron'],'gmi_return':[research]} if entry=='catalogue' else {'gmi_return':[research]} if entry=='research' else {}
                assert parse_qs(urlsplit(p.url).fragment)==expected
                expect(p.locator('[data-company-search]')).to_have_value('Micron' if entry=='catalogue' else '')
                if entry in ('catalogue','research'):
                    p.locator('[data-gmi-return]').click()
                    expect(p.locator('[data-gmi-ready]')).to_have_count(1)
                    assert parse_qs(urlsplit(p.url).fragment)==parse_qs(urlsplit(research).fragment)
                else:expect(p.locator('[data-gmi-return]')).to_have_count(0)
                p.close()
            report.setdefault('relationship_recovery_paths',[]).append({'width':width,'language':language,'entries':['direct','research','catalogue','invalid'],'native_primary_Enter':True,'native_disclosure_Enter_Space':True,'company_query_and_upstream_research_preserved':True,'invalid_return_never_forwarded':True})

    def relationship_entry_static(width, language):
        """Real no-JavaScript pages retain ordinary links and publication disclosure."""
        with context(width,'light',language,java_script_enabled=False) as c:
            p=page_for(c,'gmi-relationships.html#gmi_return=invalid')
            expect(p.locator('h1')).to_have_count(1);expect(p.locator('.gmi-head')).to_have_count(0)
            assert p.locator('h1').inner_text().strip()==('Company relationships' if language=='en' else '公司关系')
            expect(p.locator('[data-gmi-return]')).to_have_count(0)
            expect(p.locator('.gmi-snapshot-stale')).not_to_be_visible()
            assert p.locator('#gmi-brain-slot').evaluate('(n)=>n.childElementCount')==0
            actions=p.locator('.gmi-state-actions a')
            assert actions.evaluate_all('(nodes)=>nodes.map(n=>n.getAttribute("href"))')==['gmi-companies.html','gmi.html','gmi-coverage.html']
            assert not p.locator('main [data-company-card], main [data-relationship], main script[type="application/json"]').count()
            details=p.locator('.gmi-topic-receipt');details.locator('summary').click();expect(details).to_have_attribute('open','')
            assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
            actions.first.click();expect(p.locator('[data-company-card]')).to_have_count(1)
            assert urlsplit(p.url).path.endswith('/gmi-companies.html') and not urlsplit(p.url).fragment
            report.setdefault('relationship_entry_static',[]).append({'width':width,'language':language,'native_three_links':True,'native_disclosure':True,'actual_company_navigation':True,'no_dynamic_return_or_public_projection':True})


    for route in ('gmi-companies.html','gmi-issuer-mu.html','gmi-index.html','gmi-coverage.html','gmi-relationships.html','gmi-states.html'):
        for width,language in ((390,'en'),(320,'zh')):
            check(f'return-context-focus-{route}-{language}',lambda r=route,w=width,l=language:return_context_focus(r,w,l))
    for width in (1440,390,320):
        for language in ('en','zh'):
            check(f'relationship-entry-{width}-{language}',lambda w=width,l=language:relationship_entry_header(w,l))
    for width,language in ((320,'en'),(390,'zh')):
        check(f'relationship-crowded-{width}-{language}',lambda w=width,l=language:relationship_entry_header(w,l,'dark',crowded=True))
    for width,language in ((390,'en'),(320,'zh')):
        check(f'relationship-recovery-{width}-{language}',lambda w=width,l=language:relationship_recovery_paths(w,l))
    for width in (1440,320):
        for language in ('en','zh'):
            check(f'relationship-static-{width}-{language}',lambda w=width,l=language:relationship_entry_static(w,l))


    def coverage_entry_geometry(p):
        return p.evaluate('''()=>{
          const r=n=>{if(!n)return null;const b=n.getBoundingClientRect();return {left:b.left,right:b.right,top:b.top,bottom:b.bottom,width:b.width,height:b.height};};
          const h=document.querySelector('.gmi-product-head');
          const cards=[...document.querySelectorAll('.gmi-coverage-market,.gmi-cov-row')];
          return {brand:r(document.querySelector('.gmi-product-name')),title:r(document.querySelector('h1')),snapshot:r(document.querySelector('.gmi-snapshot')),nav:r(document.querySelector('.gmi-product-nav')),returned:r(document.querySelector('.gmi-return-context')),first:r(cards[0]),second:r(cards[1]),brain:r(document.querySelector('#gmi-brain-slot #mmb-boot')),rightPadding:parseFloat(getComputedStyle(h).paddingRight),titleSize:parseFloat(getComputedStyle(document.querySelector('h1')).fontSize),overflow:document.documentElement.scrollWidth>innerWidth};
        }''')

    def coverage_entry_header(width, language, theme='light', crowded=False, upgraded=True):
        """Separate market units, compact task entry, and unchanged native return ownership."""
        research='gmi.html#'+urlencode({'theme':'theme:hbm_packaging','scope':'core','evidence':'1','lens':'chain','q':'Micron'})
        with context(width,theme,language,reduced_motion='reduce') as c:
            c.add_init_script('Date.now=()=>Date.UTC(2026,10,'+('20' if crowded else '9')+');')
            for entry,returned in (('direct',''),('research',research)):
                params={'fixture_key':'coverage-entry'}
                if returned:params['gmi_return']=returned
                p=page_for(c,'gmi-coverage.html#'+urlencode(params));initial=p.url
                title=p.locator('h1');expect(title).to_have_count(1)
                title_text=('Coverage & methodology' if language=='en' else '覆盖与方法') if upgraded else ('Coverage & receipts' if language=='en' else '覆盖率与凭证')
                assert title.inner_text().strip()==title_text
                assert p.locator('.gmi-head').count()==(0 if upgraded else 1)
                assert p.locator('.gmi-product-head > div:first-child > p').count()==(0 if upgraded else 1)
                expect(p.locator('[data-gmi-snapshot]')).to_have_attribute('data-gmi-snapshot','2026-11-03')
                expect(p.locator('.gmi-product-tools a').last).to_have_attribute('aria-current','page')
                if returned:
                    back=p.locator('[data-gmi-return]');expect(back).to_be_visible()
                    assert parse_qs(urlsplit(back.get_attribute('href')).fragment)==parse_qs(urlsplit(research).fragment)
                else:expect(p.locator('[data-gmi-return]')).to_have_count(0)
                if crowded:
                    expect(p.locator('.gmi-snapshot-stale')).to_be_visible()
                    p.evaluate('''()=>{const b=document.createElement('button');b.id='mmb-boot';b.type='button';b.textContent='Brain';b.style.cssText='width:44px;height:44px;padding:0;border:1px solid var(--line);border-radius:12px;background:var(--panel2);color:var(--text);font:11px var(--font-ui)';document.body.append(b);dispatchEvent(new Event('mm-brain-ready'));}''')
                else:expect(p.locator('.gmi-snapshot-stale')).not_to_be_visible()
                g=coverage_entry_geometry(p)
                assert not g['overflow'] and g['first']['top']>=(g['returned'] or g['nav'])['bottom']-0.5
                if upgraded:
                    assert g['brand']['height']>=44 and g['titleSize']==(24 if width<=820 else 32)
                    if width<=820:
                        assert g['rightPadding']==72
                        if g['brain']:assert g['title']['right']<=g['brain']['left']-1 and g['snapshot']['right']<=g['brain']['left']-1
                        assert g['second']['top']>=g['first']['bottom']+19
                    else:assert abs(g['first']['top']-g['second']['top'])<=0.5
                    expect(p.locator('.gmi-coverage-market')).to_have_count(2)
                    us=p.locator('[data-gmi-coverage-market="us"]');cn=p.locator('[data-gmi-coverage-market="cn"]')
                    assert us.locator('.gmi-coverage-admitted strong').inner_text()=='1'
                    assert cn.locator('.gmi-coverage-admitted strong').inner_text()=='0'
                    assert us.locator('.gmi-coverage-bound dt').inner_text().strip()==('Company count range' if language=='en' else '公司数量范围')
                    assert us.locator('.gmi-coverage-bound dd').inner_text()=='1,928–1,931'
                    assert cn.locator('.gmi-coverage-bound dd').inner_text()=='1–1,019'
                    assert us.locator('.gmi-coverage-matched dd').inner_text()=='1,927'
                    assert cn.locator('.gmi-coverage-matched dd').inner_text()=='0'
                    assert us.locator('.gmi-coverage-unmatched dd').inner_text()=='4'
                    assert cn.locator('.gmi-coverage-unmatched dd').inner_text()=='1,019'
                    assert us.locator('.gmi-coverage-reasons summary').inner_text().strip()==('1,926 companies not counted' if language=='en' else '1,926 家公司未计入')
                    assert cn.locator('.gmi-coverage-reasons').count()==0
                    assert p.locator('.gmi-coverage-theme-totals b').all_inner_texts()==['1','67']
                    assert p.locator('.gmi-big0,.gmi-track,.gmi-stack').count()==0
                    assert p.locator('main').inner_text().count('3 Nov 2026' if language=='en' else '2026年11月3日')==1
                    for summary in p.locator('.gmi-coverage-reasons>summary,.gmi-coverage-method>summary').all():
                        b=summary.bounding_box();assert b['height']>=44 and b['x']>=0 and b['x']+b['width']<=width+0.5
                gmi_navigation_fit(p,width,language)
                assert p.evaluate('document.activeElement===document.body') and p.url==initial
                report.setdefault('coverage_entry_header',[]).append({'width':width,'language':language,'theme':theme,'crowded':crowded,'entry':entry,'upgraded':upgraded,'geometry':g})
                if upgraded and entry==('research' if crowded else 'direct') and ((width,language) in ((1440,'en'),(390,'en'),(320,'zh')) or crowded):
                    path=args.out/f'coverage-entry-{width}-{language}-{theme}.png';p.screenshot(path=str(path),full_page=width>820);report['screenshots'].append(path.name)
                p.close()

    def coverage_details_interaction(width, language, theme='light', scripts=True, reduced=True):
        """Native disclosures work with or without JS; changing locale preserves their state."""
        with context(width,theme,language,java_script_enabled=scripts,reduced_motion='reduce' if reduced else 'no-preference') as c:
            p=page_for(c,'gmi-coverage.html')
            method=p.locator('.gmi-coverage-method');reason=p.locator('.gmi-coverage-reasons')
            ms=method.locator(':scope>summary');rs=reason.locator(':scope>summary')
            expect(method).not_to_have_attribute('open','');expect(reason).not_to_have_attribute('open','')
            original=p.url;history=p.evaluate('history.length')
            ms.focus();ms.press('Enter');expect(method).to_have_attribute('open','');expect(ms).to_be_focused()
            rs.focus();rs.press('Space');expect(reason).to_have_attribute('open','');expect(rs).to_be_focused()
            expect(method).to_have_attribute('open','')
            assert p.locator('.gmi-coverage-reason-list dd b').all_inner_texts()==['722','1,200','4']
            rows=p.locator('.gmi-coverage-sources .gmi-dl>div')
            assert rows.nth(0).locator('time').get_attribute('datetime')=='2026-11-03'
            assert rows.nth(1).locator('time').get_attribute('datetime')=='2026-11-04T02:29:26Z'
            assert rows.nth(2).locator('time').count()==0
            if reduced:
                assert ms.locator('svg').evaluate('(n)=>getComputedStyle(n).transitionDuration')=='0s'
            assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
            assert p.url==original and p.evaluate('history.length')==history
            for current in ('zh' if language=='en' else 'en',language) if scripts else (language,):
                if scripts:p.evaluate('(lang)=>{document.documentElement.setAttribute("data-lang",lang);document.dispatchEvent(new Event("langchange"));}',current)
                expect(method).to_have_attribute('open','');expect(reason).to_have_attribute('open','');expect(rs).to_be_focused()
                assert rows.nth(1).locator('dt').inner_text().strip()==('Coverage model generated' if current=='en' else '覆盖模型生成于')
                assert rs.inner_text().strip()==('1,926 companies not counted' if current=='en' else '1,926 家公司未计入')
                assert p.locator('.gmi-coverage-theme-totals b').all_inner_texts()==['1','67']
                assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
                assert p.url==original and p.evaluate('history.length')==history
            if scripts and reduced:
                p.evaluate('scrollTo(0,0)')
                path=args.out/f'coverage-details-{width}-{language}-{theme}.png';p.screenshot(path=str(path),full_page=True);report['screenshots'].append(path.name)
            rs.press('Enter');expect(reason).not_to_have_attribute('open','');expect(rs).to_be_focused()
            ms.focus();ms.press('Space');expect(method).not_to_have_attribute('open','');expect(ms).to_be_focused()
            assert p.url==original and p.evaluate('history.length')==history
            report.setdefault('coverage_details',[]).append({'width':width,'language':language,'theme':theme,'scripts':scripts,'reduced_motion':reduced,'native_Enter_Space':True,'reason_companies':[722,1200,4],'unresolved_listings_separate':[4,1019],'separate_source_clocks':True,'focus_open_state_and_URL_retained':True,'overflow':False})

    for width in (1440,390,320):
        for language in ('en','zh'):
            check(f'coverage-entry-{width}-{language}',lambda w=width,l=language:coverage_entry_header(w,l))
    for width,language in ((320,'en'),(390,'zh')):
        check(f'coverage-crowded-{width}-{language}',lambda w=width,l=language:coverage_entry_header(w,l,'dark',crowded=True))
    for width,language in ((390,'en'),(320,'zh')):
        for scripts,reduced in ((True,True),(True,False),(False,True)):
            check(f'coverage-disclosure-{language}-{scripts}-{reduced}',lambda w=width,l=language,s=scripts,r=reduced:coverage_details_interaction(w,l,'light',s,r))


    def payload_failure_page(c, defect, fragment=None):
        """Inject only a public-presentation payload fault into the served document."""
        original=(args.site/'gmi.html').read_text()
        pattern=r'(<script\b[^>]*id="gmi-topic-data"[^>]*>)(.*?)(</script>)'
        found=re.search(pattern,original,re.S);assert found
        payload=json.loads(found[2])
        default_id=re.search(r'data-default-theme="([^"]+)"',original)[1]
        default=next(t for t in payload['topics'] if t['id']==default_id)
        target=next(t for t in payload['topics'] if t['id']!=default_id and t['tier']=='core')
        if defect=='malformed':
            damaged_payload='{"topics":]'
        else:
            data=json.loads(json.dumps(payload));selected=next(t for t in data['topics'] if t['id']==default_id)
            if defect=='categories':data.pop('categories')
            elif defect in ('paths','connections'):selected[defect]=None
            elif defect=='source':selected['connections'][0]['source']=None
            elif defect=='duplicate-id':data['topics'].append(data['topics'][0])
            elif defect=='default-id':data['topics'].remove(selected)
            elif defect=='category-label':data['categories'][selected['category']]=None
            elif defect=='parent':selected['parent']='missing-category'
            else:raise AssertionError('Unknown fault '+defect)
            damaged_payload=json.dumps(data)
        def damage(route):
            response=route.fetch();text=response.text()
            changed=re.sub(pattern,lambda m:m[1]+damaged_payload+m[3],text,flags=re.S)
            assert changed!=text
            route.fulfill(response=response,body=changed)
        c.route('**/gmi.html*',damage)
        if fragment is None:
            fragment=urlencode({'theme':target['id'],'q':'remember this','scope':'core','evidence':'1','lens':'coverage'})
        p=page_for(c,'gmi.html#'+fragment)
        return p,{'default':default,'target':target,'fragment':fragment,'defect':defect}

    def payload_failure_recovery(width, language, defect='malformed', theme='light'):
        """A failed deep link identifies its static answer and offers a native action."""
        with context(width,theme,language,reduced_motion='reduce') as c:
            p,fixture=payload_failure_page(c,defect)
            notice=p.locator('[data-topic-notice]');recovery=p.locator('[data-topic-notice-index]')
            title=p.locator('#gmi-topic-title')
            expect(title).to_have_text(fixture['default'][language],use_inner_text=True)
            assert fixture['default']['id']!=fixture['target']['id']
            expect(p.locator('[data-gmi-ready]')).to_have_count(0)
            expect(p.locator('[data-browse-home]')).not_to_be_visible()
            expect(p.locator('[data-browse-open]')).not_to_be_visible()
            expect(p.locator('[data-gmi-copy]')).not_to_be_visible()
            expect(p.locator('[data-topic-notice-reset]')).not_to_be_visible()
            expect(p.locator('.gmi-evidence-card')).to_have_count(len(fixture['default']['connections']))
            assert p.locator('[data-topic-related]').evaluate('(n)=>n.closest("section").hidden')
            expect(p.locator('.gmi-topic-context>section').nth(1)).to_be_visible()
            expect(p.locator('.gmi-topic-receipt>summary')).to_be_visible()
            observed={'width':width,'language':language,'theme':theme,'fault':defect,'requested':fixture['target']['id'],'shown':fixture['default']['id'],'notice':notice.inner_text(),'recovery_links':recovery.count(),'ready':False}
            report.setdefault('payload_failure_observations',[]).append(observed)
            if defect=='malformed':
                path=args.out/f'payload-failure-{width}-{language}-{theme}.png'
                p.screenshot(path=str(path),full_page=True);report['screenshots'].append(path.name)
            expect(notice).to_have_text('Interactive research could not load. The starting topic is shown below.' if language=='en' else '交互研究未能加载。下方显示起始主题。')
            expect(recovery).to_be_visible()
            expect(recovery).to_have_text('Open the full index' if language=='en' else '打开完整索引',use_inner_text=True)
            href=recovery.get_attribute('href')
            assert urlsplit(href).path.endswith('/gmi-index.html')
            returned=parse_qs(urlsplit(href).fragment)['gmi_return'][0]
            assert urlsplit(returned).path=='gmi.html'
            assert parse_qs(urlsplit(returned).fragment)==parse_qs(fixture['fragment'])
            b=recovery.bounding_box();assert b['height']>=44 and b['x']>=0 and b['x']+b['width']<=width+0.5
            assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
            p.locator('a.gmi-product-name[href]').focus()
            for _ in range(20):
                p.keyboard.press('Tab')
                if recovery.evaluate('(n)=>n===document.activeElement'):break
            expect(recovery).to_be_focused()
            p.keyboard.press('Shift+Tab');p.keyboard.press('Tab');expect(recovery).to_be_focused()
            original_url=p.url;history_length=p.evaluate('history.length')
            p.evaluate('window.__payloadRecovery=document.querySelector("[data-topic-notice-index]");window.__payloadAnswer=document.querySelector("[data-topic-answer]")')
            for current in ('zh' if language=='en' else 'en',language):
                p.evaluate('(v)=>document.documentElement.setAttribute("data-lang",v)',current)
                expect(notice).to_have_text('Interactive research could not load. The starting topic is shown below.' if current=='en' else '交互研究未能加载。下方显示起始主题。')
                expect(recovery).to_have_text('Open the full index' if current=='en' else '打开完整索引',use_inner_text=True)
                expect(title).to_have_text(fixture['default'][current],use_inner_text=True);expect(recovery).to_be_focused()
                assert p.evaluate('window.__payloadRecovery===document.querySelector("[data-topic-notice-index]")&&window.__payloadAnswer===document.querySelector("[data-topic-answer]")')
                assert p.url==original_url and p.evaluate('history.length')==history_length
                expect(p.locator('[data-gmi-ready]')).to_have_count(0)
            if defect=='malformed' and (width,language) in ((390,'en'),(320,'zh')):
                for selector in ('.gmi-evidence-receipt','.gmi-topic-receipt'):
                    disclosure=p.locator(selector).first;summary=disclosure.locator(':scope>summary')
                    expect(disclosure).not_to_have_attribute('open','')
                    summary.focus();summary.press('Enter')
                    expect(disclosure).to_have_attribute('open','');expect(summary).to_be_focused()
                    summary.press('Space');expect(disclosure).not_to_have_attribute('open','');expect(summary).to_be_focused()
                assert p.url==original_url and p.evaluate('history.length')==history_length
            observed.update({'empty_related_hidden':True,'coverage_and_native_disclosures_retained':True,'inline_native_action':True,'keyboard_reachable':True,'same_anchor_and_answer':True,'locale_focus_and_URL_retained':True,'height':b['height']})

    def payload_failure_journey(language):
        """Failed initialization still projects current qualified context through one owner."""
        width=390 if language=='en' else 320
        with context(width,'light',language,reduced_motion='reduce') as c:
            p,fixture=payload_failure_page(c,'malformed')
            global_index=p.locator('.gmi-product-tools a[href*="gmi-index.html"]')
            recovery=p.locator('[data-topic-notice-index]')
            def context_is(selector, values):
                if values is None:
                    expect(p.locator(selector)).to_have_attribute('href','gmi-index.html')
                    return
                p.wait_for_function("""({selector,values})=>{
                  const a=document.querySelector(selector);if(!a)return false;
                  const returned=new URLSearchParams(new URL(a.href).hash.slice(1)).get('gmi_return');
                  if(!returned)return false;
                  const u=new URL(returned,location.href),v=Object.fromEntries(new URLSearchParams(u.hash.slice(1)));
                  return u.pathname.endsWith('/gmi.html')&&Object.keys(v).length===Object.keys(values).length&&Object.keys(values).every(k=>v[k]===values[k]);
                }""",arg={'selector':selector,'values':values},timeout=2500)
            gs='.gmi-product-tools a[href*="gmi-index.html"]'
            rs='[data-topic-notice-index]'
            initial={k:v[0] for k,v in parse_qs(fixture['fragment']).items()}
            context_is(gs,initial)
            p.evaluate("""()=>{
              window.__payloadHashEvents=0;window.__payloadHistoryWrites=[];
              addEventListener('hashchange',()=>window.__payloadHashEvents++);
              for(const key of ['pushState','replaceState']){
                const original=history[key].bind(history);
                history[key]=function(...args){window.__payloadHistoryWrites.push(key);return original(...args);};
              }
              window.__failedAnswer=document.querySelector('[data-topic-answer]');
            }""")
            initial_length=p.evaluate('history.length')
            updated={'theme':fixture['target']['id'],'q':'updated query','lens':'coverage'}
            p.evaluate('(v)=>{location.hash=v;}',urlencode(updated))
            p.wait_for_function('window.__payloadHashEvents>=1')
            observed={'language':language,'initial_return':initial,'updated_return':updated,'global_href_after_hash':global_index.get_attribute('href')}
            report.setdefault('payload_failure_journeys',[]).append(observed)
            # The old failure path stops before installing these context listeners.
            context_is(gs,updated)
            expect(recovery).to_be_visible();context_is(rs,updated)
            recovery.focus();p.evaluate('window.__sameRecovery=document.querySelector("[data-topic-notice-index]")')
            p.evaluate('location.hash=""');context_is(gs,{});context_is(rs,{})
            expect(recovery).to_be_focused()
            p.go_back();context_is(gs,updated);context_is(rs,updated)
            p.go_back();context_is(gs,initial);context_is(rs,initial)
            p.go_forward();context_is(gs,updated);context_is(rs,updated)
            expect(recovery).to_be_focused()
            assert p.evaluate('history.length')==initial_length+2
            assert p.evaluate('window.__payloadHistoryWrites')==[]
            # Replacing the current lens does not dispatch hashchange or popstate.
            p.locator('.gmi-advanced>summary').click()
            before_lens_history=p.evaluate('history.length')
            p.locator('[data-gmi-set-lens="chain"]').click()
            with_lens={**updated,'lens':'chain'}
            context_is(gs,with_lens);context_is(rs,with_lens)
            assert p.evaluate('history.length')==before_lens_history
            assert p.evaluate('window.__payloadHistoryWrites')==['replaceState']
            recovery.focus();old_url=p.url
            other='zh' if language=='en' else 'en'
            p.evaluate('(v)=>document.documentElement.setAttribute("data-lang",v)',other)
            expect(recovery).to_have_text('Open the full index' if other=='en' else '打开完整索引',use_inner_text=True)
            expect(recovery).to_be_focused();context_is(rs,with_lens)
            assert p.url==old_url
            p.evaluate('(v)=>document.documentElement.setAttribute("data-lang",v)',language)
            expect(recovery).to_be_focused()
            filtered={'theme':fixture['target']['id'],'q':'a'*250,'scope':'invalid','unknown':'discarded','lens':'coverage'}
            p.evaluate('(v)=>{location.hash=v;}',urlencode(filtered))
            qualified={'theme':fixture['target']['id'],'q':'a'*200,'lens':'coverage'}
            context_is(gs,qualified);context_is(rs,qualified)
            expect(recovery).to_be_focused()
            p.evaluate('(v)=>{location.hash=v;}',urlencode({'q':'a'*5000}))
            try:
                context_is(gs,None);context_is(rs,None)
            except Exception:
                observed['rejected_context_snapshot']=p.evaluate("""()=>{
                  const link=s=>document.querySelector(s)?.getAttribute('href');
                  return {hash_length:location.hash.length,query_length:new URLSearchParams(location.hash.slice(1)).get('q')?.length,
                    global_href:link('.gmi-product-tools a[href*="gmi-index.html"]'),inline_href:link('[data-topic-notice-index]'),
                    history_writes:window.__payloadHistoryWrites,hash_events:window.__payloadHashEvents};
                }""")
                raise
            assert recovery.get_attribute('href')=='gmi-index.html'
            expect(recovery).to_be_focused()
            p.evaluate('(v)=>{location.hash=v;}',urlencode(with_lens))
            context_is(gs,with_lens);context_is(rs,with_lens)
            assert p.evaluate('window.__sameRecovery===document.querySelector("[data-topic-notice-index]")&&window.__failedAnswer===document.querySelector("[data-topic-answer]")')
            expect(p.locator('#gmi-topic-title')).to_have_text(fixture['default'][language],use_inner_text=True)
            expect(p.locator('[data-gmi-ready]')).to_have_count(0)
            assert p.evaluate('window.__payloadHistoryWrites')==['replaceState']
            # Use the native href in a second page, then activate the original with Enter.
            href=recovery.get_attribute('href')
            other_page=c.new_page();other_page.on('pageerror',lambda e:report['page_errors'].append(str(e)));other_page.goto(href,wait_until='networkidle')
            expect(other_page.locator('a.gmi-irow-name')).to_have_count(371)
            back=other_page.locator('[data-gmi-return]');expect(back).to_be_visible()
            assert parse_qs(urlsplit(back.get_attribute('href')).fragment)=={k:[v] for k,v in with_lens.items()}
            other_page.close()
            recovery.focus();p.keyboard.press('Enter')
            expect(p.locator('a.gmi-irow-name')).to_have_count(371)
            back=p.locator('[data-gmi-return]');expect(back).to_be_visible()
            expect(back).to_have_text('Back to theme research' if language=='en' else '返回主题研究')
            assert parse_qs(urlsplit(back.get_attribute('href')).fragment)=={k:[v] for k,v in with_lens.items()}
            back.focus();p.keyboard.press('Enter')
            expect(p.locator('[data-topic-notice-index]')).to_be_visible()
            expect(p.locator('#gmi-topic-title')).to_have_text(fixture['default'][language],use_inner_text=True)
            expect(p.locator('[data-gmi-ready]')).to_have_count(0)
            assert parse_qs(urlsplit(p.url).fragment)=={k:[v] for k,v in with_lens.items()}
            observed.update({'history_back_forward':True,'lens_replaceState':True,'locale_focus_retained':True,'old_fields_removed':True,'overlong_context_rejected':True,'same_anchor_and_answer':True,'native_href_and_Enter_roundtrip':True,'product_history_writes_before_navigation':['replaceState']})

    def payload_failure_boundaries(language):
        """Normal filter recovery, missing topics and actual no-JS keep their existing roles."""
        width=390 if language=='en' else 320
        with context(width,'light',language,reduced_motion='reduce') as c:
            p=page_for(c,'gmi.html#q=payload-fixture-no-match-zzzz')
            expect(p.locator('[data-gmi-ready]')).to_have_count(1)
            expect(p.locator('[data-topic-notice-reset]')).to_be_visible()
            assert not p.locator('[data-topic-related]').evaluate('(n)=>n.closest("section").hidden')
            expect(p.locator('[data-topic-notice-index]')).not_to_be_visible()
            p.evaluate('window.__goodAnswer=document.querySelector("[data-topic-answer]")')
            reset=p.locator('[data-topic-notice-reset]');reset.focus();reset.press('Enter')
            expect(p.locator('[data-topic-notice-region]')).not_to_be_visible()
            expect(p.locator('[data-topic-notice-index]')).not_to_be_visible()
            expect(p.locator('#gmi-topic-title')).to_be_focused()
            assert p.evaluate('window.__goodAnswer===document.querySelector("[data-topic-answer]")')
            p.goto(p.url.split('#')[0]+'#theme=theme%3Amissing-payload-fixture',wait_until='networkidle')
            expect(p.locator('[data-topic-notice]')).to_contain_text('That topic is not available' if language=='en' else '此快照中找不到该主题')
            expect(p.locator('[data-topic-notice-index]')).not_to_be_visible()
            expect(p.locator('[data-topic-notice-reset]')).not_to_be_visible()
            expect(p.locator('[data-gmi-ready]')).to_have_count(1)
        with context(width,'light',language,java_script_enabled=False,reduced_motion='reduce') as c:
            p=page_for(c,'gmi.html#theme=theme%3Astatic-nondefault')
            expect(p.locator('[data-topic-notice-region]')).not_to_be_visible()
            expect(p.locator('[data-topic-notice-index]')).not_to_be_visible()
            expect(p.locator('[data-browse-open]')).not_to_be_visible()
            expect(p.locator('[data-gmi-copy]')).not_to_be_visible()
            expect(p.locator('#gmi-topic-title')).to_be_visible()
            index=p.locator('noscript a[href*="gmi-index.html"]')
            expect(index).to_be_visible();assert index.get_attribute('href')=='gmi-index.html'
            index.focus();index.press('Enter');expect(p.locator('a.gmi-irow-name')).to_have_count(371)
        report.setdefault('payload_failure_boundaries',[]).append({'language':language,'normal_clear_filter_owner':True,'missing_topic_distinct':True,'noJS_native_index':True,'new_failure_action_hidden_outside_payload_failure':True})

    for width in (1440,390,320):
        for language in ('en','zh'):
            check(f'payload-recovery-{width}-{language}',lambda w=width,l=language:payload_failure_recovery(w,l))
    for width,language in ((320,'en'),(390,'zh')):
        check(f'payload-recovery-dark-{width}-{language}',lambda w=width,l=language:payload_failure_recovery(w,l,theme='dark'))
    for number,defect in enumerate(('categories','paths','connections','source','duplicate-id','default-id','category-label','parent')):
        check(f'payload-schema-{defect}',lambda d=defect,n=number:payload_failure_recovery(320 if n%2 else 390,'en' if n%2 else 'zh',d))
    for language in ('en','zh'):
        check(f'payload-journey-{language}',lambda l=language:payload_failure_journey(l))
        check(f'payload-boundaries-{language}',lambda l=language:payload_failure_boundaries(l))


    def primary_escape_contract(width,language,theme='light',only_guard=None):
        """Guard authored Escape effects; synthetic composition is not native IME proof."""
        with context(width,theme,language,reduced_motion='reduce' if width==320 else 'no-preference') as c:
            p=page_for(c,'gmi.html#scope=core&lens=chain')
            field=p.locator('[data-topic-search]');dialog=p.locator('[data-browse-dialog]');opener=p.locator('[data-browse-open]')
            narrow=width<=820
            if narrow:opener.click();expect(dialog).to_be_visible()
            data=json.loads(p.locator('#gmi-topic-data').text_content())
            default_id=p.locator('[data-gmi-explorer]').get_attribute('data-default-theme')
            topic=next(t for t in data['topics'] if t['id']==default_id)
            p.locator('[data-topic-category-filter]').select_option(topic['category'])
            if language=='zh':p.locator('[data-evidence-only]').check()
            field.fill('HBM');expect(field).to_be_focused()
            assert p.locator('.gmi-topic-option:visible').count()>0
            field.evaluate('(n)=>n.setSelectionRange(1,2)')
            p.evaluate("""()=>{
              const s=window.__primaryEscape={writes:[],cancel:0,close:0,bubble:0,sequence:[],
                field:document.querySelector('[data-topic-search]'),answer:document.querySelector('[data-topic-answer]')};
              for(const method of ['pushState','replaceState']){
                const original=history[method].bind(history);history[method]=function(...args){s.writes.push(method);return original(...args);};
              }
              const d=document.querySelector('[data-browse-dialog]');
              d.addEventListener('cancel',()=>{s.cancel++;s.sequence.push('cancel');});
              d.addEventListener('close',()=>{s.close++;s.sequence.push('close');});
              document.addEventListener('keydown',e=>{if(e.key==='Escape')s.bubble++;});
            }""")
            def snapshot():
                return p.evaluate("""()=>{
                  const s=window.__primaryEscape,f=document.querySelector('[data-topic-search]');
                  return {value:f.value,selection:[f.selectionStart,f.selectionEnd],url:location.href,history_length:history.length,
                    category:document.querySelector('[data-topic-category-filter]').value,
                    scope:document.querySelector('input[name="gmi-scope"]:checked').value,
                    evidence:document.querySelector('[data-evidence-only]').checked,lens:document.documentElement.getAttribute('data-gmi-lens'),
                    visible:[...document.querySelectorAll('.gmi-topic-option')].filter(n=>!n.hidden).map(n=>n.getAttribute('data-topic-select')),
                    title:document.querySelector('#gmi-topic-title').textContent,
                    focus_is_field:document.activeElement===f,dialog_open:document.querySelector('[data-browse-dialog]').open,
                    same_nodes:s.field===f&&s.answer===document.querySelector('[data-topic-answer]'),
                    browse_at_home:document.querySelector('[data-browse-home]').contains(document.querySelector('[data-gmi-browse]')),
                    writes:[...s.writes],cancel:s.cancel,close:s.close,bubble:s.bubble,sequence:[...s.sequence]};
                }""")
            observed={'width':width,'language':language,'theme':theme,'narrow':narrow,
                      'composition_proof':'synthetic KeyboardEvent contract; no OS-native IME claim','guards':[]}
            report.setdefault('primary_escape_observations',[]).append(observed)
            def guarded(kind,stage):
                before=snapshot()
                flags=field.evaluate("""(n,kind)=>{
                  const e=new KeyboardEvent('keydown',{key:'Escape',code:'Escape',keyCode:kind==='legacy229'?229:27,
                    bubbles:true,cancelable:true,isComposing:kind==='composing'});
                  if(kind==='consumed')e.preventDefault();
                  const initial=e.defaultPrevented,accepted=n.dispatchEvent(e);
                  return {isTrusted:e.isTrusted,isComposing:e.isComposing,keyCode:e.keyCode,
                    initially_prevented:initial,finally_prevented:e.defaultPrevented,dispatch_accepted:accepted};
                }""",kind)
                after=snapshot()
                item={'kind':kind,'stage':stage,'flags':flags,'state_unchanged':before==after}
                observed['guards'].append(item)
                if before!=after:item.update({'before':before,'after':after})
                assert not flags['isTrusted']
                assert flags['isComposing']==(kind=='composing')
                assert flags['keyCode']==(229 if kind=='legacy229' else 27)
                assert flags['initially_prevented']==(kind=='consumed')
                assert flags['finally_prevented']==flags['initially_prevented'],item
                assert before==after,item
                expect(field).to_be_focused()
            if only_guard:
                guarded(only_guard,'nonempty');return
            for kind in ('composing','legacy229','consumed'):guarded(kind,'nonempty')
            before=snapshot()
            # A real key is consumed at capture; the production bubble handler must respect it.
            field.evaluate("""n=>n.addEventListener('keydown',e=>{
              if(e.key==='Escape'){e.preventDefault();window.__primaryConsumedTrusted=e.isTrusted;}
            },{capture:true,once:true})""")
            p.keyboard.press('Escape')
            assert p.evaluate('window.__primaryConsumedTrusted===true')
            assert snapshot()==before
            if narrow:expect(dialog).to_be_visible()
            observed['real_consumed_nonempty_unchanged']=True
            observed['before_clear']=before
            if (width,language) in ((390,'en'),(320,'zh')):
                path=args.out/f'primary-search-{width}-{language}.png';p.screenshot(path=str(path),full_page=False)
                report['screenshots'].append(path.name)
            # Ordinary Escape still clears only the query through the incumbent owner.
            p.keyboard.press('Escape');expect(field).to_have_value('');expect(field).to_be_focused()
            after=snapshot();observed['after_clear']=after
            assert after['writes']==['replaceState']
            assert after['history_length']==before['history_length']
            assert after['cancel']==after['close']==after['bubble']==0
            assert after['title']==before['title'] and after['same_nodes']
            for name in ('category','scope','evidence','lens'):assert after[name]==before[name]
            old_query=parse_qs(urlsplit(before['url']).fragment);new_query=parse_qs(urlsplit(after['url']).fragment)
            assert new_query=={k:v for k,v in old_query.items() if k!='q'}
            assert len(after['visible'])>=len(before['visible'])
            if language=='en':assert len(after['visible'])>len(before['visible'])
            assert after['dialog_open']==narrow
            for kind in ('composing','legacy229','consumed'):guarded(kind,'empty')
            empty=snapshot()
            field.evaluate("""n=>n.addEventListener('keydown',e=>{
              if(e.key==='Escape'){e.preventDefault();window.__primaryConsumedTrusted=e.isTrusted;}
            },{capture:true,once:true})""")
            p.keyboard.press('Escape')
            assert p.evaluate('window.__primaryConsumedTrusted===true')
            assert snapshot()==empty
            observed['real_consumed_empty_unchanged']=True
            # Empty ordinary Escape is left to the browser, including native dialog cancel.
            p.keyboard.press('Escape')
            if narrow:
                expect(dialog).not_to_be_visible();expect(opener).to_be_focused()
                p.wait_for_function('window.__primaryEscape.close===1')
                closed=snapshot()
                assert closed['cancel']==closed['close']==1 and closed['bubble']==1
                assert closed['sequence']==['cancel','close'] and closed['browse_at_home']
                assert closed['writes']==['replaceState']
                observed['native_clear_then_cancel']=True
                # Independently canceled native close remains the browser's boundary.
                opener.click();expect(dialog).to_be_visible();expect(field).to_be_focused()
                dialog.evaluate("n=>n.addEventListener('cancel',e=>e.preventDefault(),{once:true})")
                p.keyboard.press('Escape')
                expect(dialog).to_be_visible();expect(field).to_be_focused()
                blocked=snapshot()
                assert blocked['cancel']==2 and blocked['close']==1 and not blocked['browse_at_home']
                p.keyboard.press('Escape')
                expect(dialog).not_to_be_visible();expect(opener).to_be_focused()
                p.wait_for_function('window.__primaryEscape.close===2')
                final=snapshot()
                assert final['cancel']==3 and final['close']==2 and final['browse_at_home']
                assert final['writes']==['replaceState']
                observed['native_cancel_prevention_then_recovery']=True
                observed['final_native_sequence']=final['sequence']
            else:
                expect(field).to_be_focused()
                final=snapshot()
                assert final['cancel']==final['close']==0 and final['bubble']==1
                assert final['writes']==['replaceState'] and final['browse_at_home']
                observed['desktop_empty_escape_passed_through']=True
            observed['pass']=True

    for width in (1440,390,320):
        for language in ('en','zh'):
            theme='dark' if (width,language) in ((390,'en'),(320,'zh')) else 'light'
            check(f'primary-escape-{width}-{language}',lambda w=width,l=language,t=theme:primary_escape_contract(w,l,t))


    def browse_focus_hash(p,fragment):
        p.evaluate("""fragment=>new Promise(resolve=>{
          if(location.hash==='#'+fragment){resolve();return;}
          addEventListener('hashchange',()=>requestAnimationFrame(()=>resolve()),{once:true});
          location.hash=fragment;
        })""",fragment)

    def browse_focus_page(c,open_browse=True):
        """Instrument owned hides at mutation time on the actual generated primary Browse."""
        p=page_for(c,'gmi.html')
        data=json.loads(p.locator('#gmi-topic-data').text_content())
        default=p.locator('[data-gmi-explorer]').get_attribute('data-default-theme')
        params={'theme':default,'lens':'chain','gmi_return':'gmi-index.html#q=HBM&lens=coverage','fixture_key':'browse-focus'}
        fixture={'params':params,'a':urlencode(params),'b':urlencode({**params,'q':'zz-no-match-primary-focus'}),
                 'extended':urlencode({**params,'scope':'extended'}),'default':default,'topics':data['topics']}
        browse_focus_hash(p,fixture['a'])
        narrow=p.evaluate('matchMedia("(max-width:820px)").matches');fixture['narrow']=narrow
        if narrow and open_browse:
            p.locator('[data-browse-open]').click()
            expect(p.locator('[data-browse-dialog]')).to_be_visible()
        p.evaluate("""()=>{
          const search=document.querySelector('[data-topic-search]'),results=document.querySelector('[data-topic-results]');
          const empty=document.querySelector('[data-topic-no-results]'),dialog=document.querySelector('[data-browse-dialog]');
          const s=window.__browseFocus={phase:'setup',ownedHides:[],events:[],writes:[],tracked:new Set(),
            answer:document.querySelector('[data-topic-answer]'),browse:document.querySelector('[data-gmi-browse]')};
          s.key=n=>{
            if(!n)return null;
            if(n===search)return 'search';
            if(n===document.querySelector('[data-topic-category-filter]'))return 'category';
            if(n===document.querySelector('[data-browse-close]'))return 'done';
            if(n===document.querySelector('[data-browse-open]'))return 'opener';
            if(n===document.querySelector('#gmi-topic-title'))return 'title';
            if(n===document.querySelector('[data-topic-notice-reset]'))return 'answer-clear';
            if(n===empty.querySelector('[data-topic-reset]'))return 'empty-clear';
            if(n.matches?.('[data-topic-select]')&&results.contains(n))return 'row:'+n.getAttribute('data-topic-select');
            return n.id||n.tagName;
          };
          const desc=Object.getOwnPropertyDescriptor(HTMLElement.prototype,'hidden');
          Object.defineProperty(HTMLElement.prototype,'hidden',{...desc,set(value){
            const managed=this===results||this===empty||this.matches?.('[data-topic-notice-region],[data-topic-notice-reset]')||
              (this.hasAttribute('data-topic-select')&&results.contains(this));
            if(managed){
              const name=this===results?'results':this===empty?'empty':s.key(this),active=s.key(document.activeElement);
              if(value===true&&this.contains(document.activeElement))s.ownedHides.push({phase:s.phase,node:name,active});
              if(this===results||this===empty||s.tracked.has(this.getAttribute('data-topic-select')))
                s.events.push({kind:'hidden',phase:s.phase,node:name,value,active});
            }
            desc.set.call(this,value);
          }});
          const focus=HTMLElement.prototype.focus;
          HTMLElement.prototype.focus=function(options){
            if(this===search||this===document.querySelector('[data-browse-close]')||
               this===document.querySelector('[data-browse-open]')||this===document.querySelector('#gmi-topic-title'))
              s.events.push({kind:'focus',phase:s.phase,target:s.key(this),before:s.key(document.activeElement),preventScroll:!!options?.preventScroll});
            return focus.call(this,options);
          };
          for(const method of ['pushState','replaceState']){
            const original=history[method].bind(history);
            history[method]=function(...args){s.writes.push({phase:s.phase,method});return original(...args);};
          }
          s.read=()=>({
            focus:s.key(document.activeElement),query:search.value,category:document.querySelector('[data-topic-category-filter]').value,
            scope:document.querySelector('input[name="gmi-scope"]:checked').value,evidence:document.querySelector('[data-evidence-only]').checked,
            visible:[...results.querySelectorAll('[data-topic-select]')].filter(n=>!n.hidden).map(n=>n.getAttribute('data-topic-select')),
            resultsHidden:results.hidden,emptyHidden:empty.hidden,count:document.querySelector('[data-topic-count]').textContent,
            title:document.querySelector('#gmi-topic-title').textContent,url:location.href,history_length:history.length,
            dialogOpen:dialog.open,browseAtHome:document.querySelector('[data-browse-home]').contains(s.browse),
            sameAnswer:s.answer===document.querySelector('[data-topic-answer]'),ownedHides:[...s.ownedHides],
            writes:[...s.writes],events:[...s.events]
          });
        }""")
        return p,fixture

    def browse_focus_history(width,language,only=None):
        with context(width,'dark' if width in (390,820) else 'light',language) as c:
            p,f=browse_focus_page(c);field=p.locator('[data-topic-search]')
            observed={'width':width,'language':language,'narrow':f['narrow'],'phases':[]}
            report.setdefault('browse_focus_history',[]).append(observed)
            def saved(phase):
                v=p.evaluate('window.__browseFocus.read()');observed['phases'].append({'phase':phase,**v})
                assert not v['ownedHides'],v['ownedHides'];return v
            if only!='positive':
                browse_focus_hash(p,f['b']);expect(p.locator('[data-topic-no-results]')).to_be_visible()
                browse_focus_hash(p,f['a']);expect(p.locator('.gmi-topic-option:visible')).to_have_count(len(f['topics']))
                length=p.evaluate('history.length')
                if only!='empty':
                    row=p.locator('[data-topic-results] [data-topic-select]').first;row.focus()
                    row.evaluate("(n)=>window.__browseFocus.tracked.add(n.getAttribute('data-topic-select'))")
                else:field.focus()
                p.evaluate("window.__browseFocus.phase='back-result'")
                p.go_back();expect(field).to_have_value('zz-no-match-primary-focus')
                v=saved('back-result');expect(field).to_be_focused()
                assert v['dialogOpen']==f['narrow'] and v['history_length']==length and not v['writes']
                if only is None and (width,language) in ((390,'en'),(320,'zh')):
                    path=args.out/f'browse-focus-recovered-{width}-{language}.png';p.screenshot(path=str(path),full_page=False)
                    report['screenshots'].append(path.name)
                if only=='result':return
                clear=p.locator('[data-topic-no-results] [data-topic-reset]');clear.focus()
                p.evaluate("window.__browseFocus.phase='forward-empty'")
                p.go_forward();expect(field).to_have_value('')
                v=saved('forward-empty');expect(field).to_be_focused()
                assert v['dialogOpen']==f['narrow'] and v['history_length']==length and not v['writes']
                assert parse_qs(urlsplit(p.url).fragment)=={k:[x] for k,x in f['params'].items()}
                if only=='empty':return
            # A focused core row disappears even though the positive-results container stays.
            row=p.locator('[data-topic-results] [data-topic-select="'+f['default']+'"]')
            row.focus();row.evaluate("(n)=>window.__browseFocus.tracked.add(n.getAttribute('data-topic-select'))")
            p.evaluate("window.__browseFocus.phase='positive-to-positive'")
            browse_focus_hash(p,f['extended'])
            v=saved('positive-to-positive');expect(field).to_be_focused()
            assert not v['resultsHidden'] and v['visible'] and f['default'] not in v['visible']
            assert v['dialogOpen']==f['narrow'] and not v['writes']
            if only=='positive':return
            surviving=next(t for t in f['topics'] if t['id'] in v['visible'])
            survivor=p.locator('[data-topic-results] [data-topic-select="'+surviving['id']+'"]');survivor.focus()
            p.evaluate("window.__browseFocus.phase='surviving-row'")
            browse_focus_hash(p,urlencode({**f['params'],'scope':'extended','q':surviving['en']}))
            v=saved('surviving-row');expect(survivor).to_be_focused()
            assert v['sameAnswer'] and not v['writes']
            category=p.locator('[data-topic-category-filter]');category.focus()
            p.evaluate("window.__browseFocus.phase='surviving-category'")
            browse_focus_hash(p,f['a']);v=saved('surviving-category');expect(category).to_be_focused()
            other=p.locator('[data-browse-close]') if f['narrow'] else p.locator('a.gmi-product-name')
            other.focus();p.evaluate("window.__browseFocus.phase='unrelated-control'")
            browse_focus_hash(p,f['b']);v=saved('unrelated-control');expect(other).to_be_focused()
            assert v['dialogOpen']==f['narrow'] and not v['writes']
            observed['pass']=True

    def browse_focus_resets(width,language):
        with context(width,'light',language,reduced_motion='reduce') as c:
            p,f=browse_focus_page(c);field=p.locator('[data-topic-search]')
            observed={'width':width,'language':language,'phases':[]};report.setdefault('browse_focus_resets',[]).append(observed)
            p.evaluate("""()=>{
              const cards=document.querySelector('[data-topic-connections]');window.__browseResetCards=[...cards.children];
              const receipt=cards.querySelector('details');if(receipt)receipt.open=true;
            }""")
            def saved(phase):
                v=p.evaluate('window.__browseFocus.read()');observed['phases'].append({'phase':phase,**v})
                assert not v['ownedHides'],v['ownedHides']
                assert p.evaluate("window.__browseResetCards.every((n,i)=>n.isConnected&&n===document.querySelector('[data-topic-connections]').children[i])")
                assert p.locator('.gmi-evidence-receipt').evaluate('(n)=>n.open')
                return v
            for activation in ('click','Enter','Space'):
                field.fill('reset-no-match-'+activation)
                p.locator('[data-topic-category-filter]').select_option(next(t for t in f['topics'] if t['id']==f['default'])['category'])
                p.locator('input[name="gmi-scope"][value="extended"]').check();p.locator('[data-evidence-only]').check()
                clear=p.locator('[data-topic-no-results] [data-topic-reset]');expect(clear).to_be_visible();clear.focus()
                p.evaluate("(phase)=>window.__browseFocus.phase=phase",'reset-'+activation)
                length=p.evaluate('history.length');writes=p.evaluate('window.__browseFocus.writes.length')
                if activation=='click':clear.click()
                else:clear.press(activation)
                v=saved('reset-'+activation);expect(field).to_be_focused()
                assert v['query']==v['category']=='' and v['scope']=='all' and not v['evidence']
                assert v['dialogOpen']==f['narrow'] and v['history_length']==length
                assert [x['method'] for x in v['writes'][writes:]]==['replaceState']
                assert parse_qs(urlsplit(p.url).fragment)=={k:[x] for k,x in f['params'].items()}
            # The clear action must not focus search a second time after a valid redirect.
            field.fill('redirect-clear-no-match')
            clear=p.locator('[data-topic-no-results] [data-topic-reset]');clear.focus()
            field.evaluate("n=>n.addEventListener('focus',()=>document.querySelector('[data-topic-category-filter]').focus(),{once:true})")
            p.evaluate("window.__browseFocus.phase='reset-redirect'")
            clear.click();v=saved('reset-redirect')
            expect(p.locator('[data-topic-category-filter]')).to_be_focused();assert v['query']==''
            # Answer-side Clear remains a separate title-owned recovery and leaves mobile Browse closed.
            for activation in ('Enter','Space'):
                if f['narrow'] and not p.locator('[data-browse-dialog]').evaluate('(n)=>n.open'):
                    p.locator('[data-browse-open]').click()
                field.fill('answer-no-match-'+activation)
                if f['narrow']:p.locator('[data-browse-close]').click()
                clear=p.locator('[data-topic-notice-reset]');expect(clear).to_be_visible();clear.focus()
                p.evaluate("(phase)=>window.__browseFocus.phase=phase",'answer-'+activation)
                clear.press(activation);v=saved('answer-'+activation)
                expect(p.locator('#gmi-topic-title')).to_be_focused()
                assert not v['dialogOpen'] and v['query']=='' and v['sameAnswer']
            observed['pass']=True

    def browse_focus_edges(width,language):
        with context(width,'dark',language) as c:
            p,f=browse_focus_page(c);field=p.locator('[data-topic-search]')
            observed={'width':width,'language':language,'phases':[]};report.setdefault('browse_focus_edges',[]).append(observed)
            def saved(phase):
                v=p.evaluate('window.__browseFocus.read()');observed['phases'].append({'phase':phase,**v})
                assert not v['ownedHides'],v['ownedHides'];return v
            def focus_default():
                browse_focus_hash(p,f['a'])
                p.locator('[data-topic-results] [data-topic-select="'+f['default']+'"]').focus()
                p.evaluate("(id)=>window.__browseFocus.tracked.add(id)",f['default'])
            focus_default()
            field.evaluate("n=>n.addEventListener('focus',()=>document.querySelector('[data-topic-category-filter]').focus(),{once:true})")
            p.evaluate("window.__browseFocus.phase='redirect-survivor'")
            browse_focus_hash(p,f['b']);v=saved('redirect-survivor')
            expect(p.locator('[data-topic-category-filter]')).to_be_focused()
            assert v['dialogOpen']==f['narrow'] and not v['writes']
            focus_default()
            field.evaluate("""(n,id)=>n.addEventListener('focus',()=>{
              const other=[...document.querySelectorAll('[data-topic-results] [data-topic-select]')].find(r=>r.getAttribute('data-topic-select')!==id&&!r.hidden);
              other.focus();
            },{once:true})""",f['default'])
            p.evaluate("window.__browseFocus.phase='redirect-retiring'")
            browse_focus_hash(p,f['b']);v=saved('redirect-retiring')
            expect(p.locator('[data-browse-close]') if f['narrow'] else p.locator('#gmi-topic-title')).to_be_focused()
            assert v['dialogOpen']==f['narrow'] and not v['writes']
            focus_default();field.evaluate('(n)=>n.disabled=true')
            p.evaluate("window.__browseFocus.phase='disabled-search-fallback'")
            browse_focus_hash(p,f['b']);v=saved('disabled-search-fallback')
            expect(p.locator('[data-browse-close]') if f['narrow'] else p.locator('#gmi-topic-title')).to_be_focused()
            assert v['dialogOpen']==f['narrow'] and not v['writes']
            field.evaluate('(n)=>n.disabled=false')
            # Capture the incumbent normal input result, then require a nested pass to win.
            browse_focus_hash(p,f['a']);field.fill('HBM')
            expected=p.locator('.gmi-topic-option:visible').evaluate_all("(nodes)=>nodes.map(n=>n.getAttribute('data-topic-select'))")
            field.fill('');p.locator('[data-topic-results] [data-topic-select="'+f['default']+'"]').focus()
            field.evaluate("""n=>n.addEventListener('focus',()=>{
              n.value='HBM';n.dispatchEvent(new Event('input',{bubbles:true}));
            },{once:true})""")
            p.evaluate("window.__browseFocus.phase='nested-newer-filter'")
            writes=p.evaluate('window.__browseFocus.writes.length')
            browse_focus_hash(p,f['b']);v=saved('nested-newer-filter')
            expect(field).to_be_focused();assert v['query']=='HBM'
            assert v['visible']==expected and v['emptyHidden'] and not v['resultsHidden']
            assert parse_qs(urlsplit(p.url).fragment)=={k:[x] for k,x in {**f['params'],'q':'HBM'}.items()}
            assert [x['method'] for x in v['writes'][writes:]]==['replaceState']
            assert v['count']==(str(len(expected))+' of '+str(len(f['topics']))+' topics' if language=='en' else str(len(f['topics']))+' 个主题中显示 '+str(len(expected))+' 个')
            assert v['dialogOpen']==f['narrow']
            observed['pass']=True

    def browse_focus_closed(language):
        width=390 if language=='en' else 320
        with context(width,'light',language) as c:
            p,f=browse_focus_page(c,open_browse=False)
            observed={'width':width,'language':language,'phases':[]};report.setdefault('browse_focus_closed',[]).append(observed)
            assert f['narrow'];expect(p.locator('[data-topic-search]')).not_to_be_visible()
            for name,selector,fragment in [('opener','[data-browse-open]',f['b']),('title','#gmi-topic-title',f['a']),('brand','a.gmi-product-name',f['b'])]:
                target=p.locator(selector);target.focus()
                p.evaluate("(phase)=>window.__browseFocus.phase=phase",'closed-'+name)
                browse_focus_hash(p,fragment)
                v=p.evaluate('window.__browseFocus.read()');observed['phases'].append({'phase':name,**v})
                assert not v['ownedHides'] and not v['writes']
                expect(target).to_be_focused()
                assert not v['dialogOpen'] and v['browseAtHome']
                assert not any(e['kind']=='focus' and e['phase']=='closed-'+name and e['target']=='search' for e in v['events'])
            observed['pass']=True

    for width,language in [(w,l) for w in (1440,390,320) for l in ('en','zh')]+[(820,'en'),(821,'zh')]:
        check(f'browse-focus-history-{width}-{language}',lambda w=width,l=language:browse_focus_history(w,l))
    for width,language in ((1440,'en'),(1440,'zh'),(390,'en'),(320,'zh')):
        check(f'browse-focus-reset-{width}-{language}',lambda w=width,l=language:browse_focus_resets(w,l))
    for width in (1440,390):
        for language in ('en','zh'):
            check(f'browse-focus-edges-{width}-{language}',lambda w=width,l=language:browse_focus_edges(w,l))
    for language in ('en','zh'):
        check(f'browse-focus-closed-{language}',lambda l=language:browse_focus_closed(l))

    for width,language in ((820,'en'),(821,'zh')):
        check(f'primary-escape-breakpoint-{width}-{language}',lambda w=width,l=language:primary_escape_contract(w,l))

    def primary_clear_page(c,open_browse=True):
        p,f=browse_focus_page(c,open_browse=open_browse)
        clear=p.locator('[data-topic-search-clear]')
        assert clear.count()==1,'Primary query-only clear action is absent'
        p.evaluate("""()=>{
          const clear=document.querySelector('[data-topic-search-clear]'),field=document.querySelector('[data-topic-search]');
          const s=window.__primaryClear={clear,field,ownedHides:[],hides:[],cards:[],receipt:null,title:null};
          const desc=Object.getOwnPropertyDescriptor(HTMLElement.prototype,'hidden');
          Object.defineProperty(HTMLElement.prototype,'hidden',{...desc,set(value){
            if(this===clear){
              const event={phase:window.__browseFocus.phase,value,focus:document.activeElement===clear?'query-clear':window.__browseFocus.key(document.activeElement)};
              s.hides.push(event);if(value===true&&this.contains(document.activeElement))s.ownedHides.push(event);
            }
            desc.set.call(this,value);
          }});
          s.mark=()=>{
            s.cards=[...document.querySelector('[data-topic-connections]').children];
            s.receipt=document.querySelector('[data-topic-connections] details');if(s.receipt)s.receipt.open=true;
            s.title=document.querySelector('#gmi-topic-title').textContent;
          };
          s.read=()=>{
            const box=field.parentElement,b=clear.getBoundingClientRect(),i=field.getBoundingClientRect();
            return {
              query:field.value,clearHidden:clear.hidden,label:clear.getAttribute('aria-label'),
              inputLabel:field.getAttribute('aria-label'),wrapperTag:box.tagName,enhanced:box.classList.contains('gmi-search--clearable'),
              hintDisplay:getComputedStyle(box.querySelector('kbd')).display,
              target:{x:b.x,y:b.y,width:b.width,height:b.height},inputRight:i.right,
              category:document.querySelector('[data-topic-category-filter]').value,
              scope:document.querySelector('input[name="gmi-scope"]:checked').value,evidence:document.querySelector('[data-evidence-only]').checked,
              url:location.href,historyLength:history.length,dialogOpen:document.querySelector('[data-browse-dialog]').open,
              focus:document.activeElement===clear?'query-clear':window.__browseFocus.key(document.activeElement),
              visibleCount:[...document.querySelectorAll('.gmi-topic-option')].filter(n=>!n.hidden).length,
              emptyHidden:document.querySelector('[data-topic-no-results]').hidden,
              sameClear:clear===s.clear,sameField:field===s.field,
              sameCards:s.cards.length>0&&s.cards.every((n,i)=>n===document.querySelector('[data-topic-connections]').children[i]),
              receiptOpen:!!s.receipt?.open,sameTitle:s.title===document.querySelector('#gmi-topic-title').textContent,
              ownedHides:[...window.__browseFocus.ownedHides,...s.ownedHides],writes:window.__browseFocus.writes.length
            };
          };
        }""")
        return p,f

    def primary_clear_snapshot(p,phase,observed):
        v=p.evaluate('window.__primaryClear.read()')
        observed.append({'phase':phase,**v})
        assert not v['ownedHides'],v['ownedHides']
        assert v['sameClear'] and v['sameField'] and v['wrapperTag']=='DIV' and v['enhanced']
        return v

    def primary_clear_controls(width,language):
        with context(width,'dark' if language=='en' else 'light',language,reduced_motion='reduce' if width==320 else 'no-preference') as c:
            p,f=primary_clear_page(c);field=p.locator('[data-topic-search]');clear=p.locator('[data-topic-search-clear]')
            topic=next(t for t in f['topics'] if t['id']==f['default'])
            params={**f['params'],'category':topic['category'],'scope':'core'}
            if language=='zh':params['evidence']='1'
            browse_focus_hash(p,urlencode({**params,'q':'HBM'}))
            observed=[];report.setdefault('primary_clear_controls',[]).append({'width':width,'language':language,'phases':observed})
            p.evaluate('window.__primaryClear.mark()')
            for activation in ('click','Enter','Space'):
                field.fill('HBM')
                v=primary_clear_snapshot(p,'before-'+activation,observed)
                assert v['label']==('Clear search' if language=='en' else '清空搜索')
                assert v['inputLabel']==('Search themes, companies or products' if language=='en' else '搜索主题、公司或产品')
                assert v['target']['width']==44 and v['target']['height']==44
                assert v['inputRight']<=v['target']['x'] and v['target']['x']+v['target']['width']<=width
                assert v['hintDisplay']=='none' and not v['clearHidden']
                assert v['visibleCount']==(1 if language=='zh' else 3)
                assert not p.evaluate('document.documentElement.scrollWidth>innerWidth')
                if activation=='click' and (width,language) in ((390,'en'),(320,'zh')):
                    path=args.out/f'primary-clear-query-{width}-{language}.png';p.screenshot(path=str(path),full_page=False);report['screenshots'].append(path.name)
                before=p.evaluate('window.__browseFocus.writes.length');length=p.evaluate('history.length')
                p.evaluate("(phase)=>window.__browseFocus.phase=phase",'clear-'+activation)
                if activation=='click':clear.click()
                else:clear.focus();p.keyboard.press(activation)
                expect(field).to_have_value('');expect(field).to_be_focused();expect(clear).not_to_be_visible()
                v=primary_clear_snapshot(p,'after-'+activation,observed)
                assert parse_qs(urlsplit(v['url']).fragment)=={k:[x] for k,x in params.items()}
                assert v['sameCards'] and v['receiptOpen'] and v['sameTitle']
                assert v['visibleCount']==(1 if language=='zh' else 10) and v['dialogOpen']==f['narrow']
                assert v['hintDisplay']!='none' and v['historyLength']==length
                assert p.evaluate('window.__browseFocus.writes.slice('+str(before)+').map(x=>x.method)')==['replaceState']
                if activation=='click' and (width,language) in ((390,'en'),(320,'zh')):
                    path=args.out/f'primary-clear-empty-{width}-{language}.png';p.screenshot(path=str(path),full_page=False);report['screenshots'].append(path.name)
                # A stale/programmatic activation on an already empty action is inert.
                clear.evaluate('(n)=>n.click()')
                assert p.evaluate('window.__browseFocus.writes.length')==v['writes']
                expect(field).to_be_focused()
            field.fill('   ');expect(clear).to_be_visible()
            v=primary_clear_snapshot(p,'whitespace-visible',observed);assert v['query']=='   '
            clear.click();expect(field).to_have_value('')
            v=primary_clear_snapshot(p,'whitespace-cleared',observed)
            assert 'q' not in parse_qs(urlsplit(v['url']).fragment) and v['sameCards'] and v['receiptOpen']
            # Query-only clearing can truthfully leave zero matches under other filters.
            p.locator('input[name="gmi-scope"][value="extended"]').check()
            p.locator('[data-evidence-only]').check();field.fill('HBM')
            expect(p.locator('[data-topic-no-results]')).to_be_visible()
            clear.click();expect(field).to_have_value('')
            v=primary_clear_snapshot(p,'zero-after-query-clear',observed)
            assert v['scope']=='extended' and v['evidence'] and v['category']==topic['category']
            assert v['visibleCount']==0 and not v['emptyHidden'] and v['clearHidden']
            assert v['sameCards'] and v['receiptOpen']
            p.locator('[data-topic-no-results] [data-topic-reset]').click()
            v=primary_clear_snapshot(p,'full-reset',observed)
            assert v['scope']=='all' and not v['evidence'] and v['category']==''
            assert v['visibleCount']==len(f['topics']) and v['sameCards'] and v['receiptOpen']
            assert parse_qs(urlsplit(v['url']).fragment)=={k:[x] for k,x in f['params'].items()}
            expect(field).to_be_focused()
            if (width,language)==(320,'zh'):
                path=args.out/'primary-clear-full-reset-320-zh.png';p.screenshot(path=str(path),full_page=False);report['screenshots'].append(path.name)

    def primary_clear_history(width,language):
        with context(width,'light',language) as c:
            p,f=primary_clear_page(c);field=p.locator('[data-topic-search]');clear=p.locator('[data-topic-search-clear]')
            observed=[];report.setdefault('primary_clear_history',[]).append({'width':width,'language':language,'phases':observed})
            browse_focus_hash(p,urlencode({**f['params'],'q':'HBM'}));clear.focus()
            writes=p.evaluate('window.__browseFocus.writes.length');length=p.evaluate('history.length')
            p.evaluate("window.__browseFocus.phase='clear-back-to-empty'")
            p.go_back();expect(field).to_have_value('');expect(field).to_be_focused()
            v=primary_clear_snapshot(p,'back-empty',observed)
            assert v['clearHidden'] and v['writes']==writes and v['historyLength']==length
            p.locator('[data-topic-category-filter]').focus()
            p.go_forward();expect(field).to_have_value('HBM')
            v=primary_clear_snapshot(p,'forward-query',observed)
            assert not v['clearHidden'] and v['focus']=='category' and v['writes']==writes
            clear.focus();browse_focus_hash(p,urlencode({**f['params'],'q':'chip'}))
            v=primary_clear_snapshot(p,'query-to-query',observed)
            expect(clear).to_be_focused();assert not v['clearHidden'] and v['query']=='chip' and v['writes']==writes
            other='zh' if language=='en' else 'en'
            p.evaluate("(language)=>document.documentElement.setAttribute('data-lang',language)",other)
            expect(clear).to_have_attribute('aria-label','清空搜索' if other=='zh' else 'Clear search')
            v=primary_clear_snapshot(p,'locale',observed);expect(clear).to_be_focused()
            assert v['query']=='chip' and v['writes']==writes
            p.evaluate("document.documentElement.setAttribute('data-theme','dark')")
            v=primary_clear_snapshot(p,'theme',observed);expect(clear).to_be_focused()
            if f['narrow']:
                p.locator('[data-browse-close]').click();expect(p.locator('[data-browse-dialog]')).not_to_be_visible()
                p.locator('a.gmi-product-name').focus()
                browse_focus_hash(p,f['a']);expect(field).to_have_value('')
                v=primary_clear_snapshot(p,'closed-history',observed)
                expect(p.locator('a.gmi-product-name')).to_be_focused()
                assert not v['dialogOpen'] and v['clearHidden'] and v['writes']==writes

    def primary_clear_edges(width,language):
        with context(width,'dark',language) as c:
            p,f=primary_clear_page(c);field=p.locator('[data-topic-search]');clear=p.locator('[data-topic-search-clear]')
            observed=[];report.setdefault('primary_clear_edges',[]).append({'width':width,'language':language,'phases':observed})
            field.fill('HBM');clear.focus()
            field.evaluate("""n=>n.addEventListener('focus',()=>document.querySelector('[data-topic-category-filter]').focus(),{once:true})""")
            clear.click();expect(field).to_have_value('')
            v=primary_clear_snapshot(p,'surviving-focus-redirect',observed)
            expect(p.locator('[data-topic-category-filter]')).to_be_focused()
            assert v['clearHidden']
            # A synchronous focus callback projects a newer query; the original click yields.
            field.fill('HBM');clear.focus();before=p.evaluate('window.__browseFocus.writes.length')
            field.evaluate("""n=>n.addEventListener('focus',()=>{
              n.value='Micron';n.dispatchEvent(new Event('input',{bubbles:true}));
            },{once:true})""")
            clear.click();expect(field).to_have_value('Micron')
            v=primary_clear_snapshot(p,'nested-query-wins',observed)
            assert not v['clearHidden'] and v['writes']==before+1
            assert parse_qs(urlsplit(v['url']).fragment)['q']==['Micron']
            # Hash restoration is asynchronous: href must also protect the click's context.
            field.fill('HBM');clear.focus();before=p.evaluate('window.__browseFocus.writes.length')
            field.evaluate("""(n,fragment)=>n.addEventListener('focus',()=>{location.hash=fragment;},{once:true})""",f['b'])
            clear.click();expect(field).to_have_value('zz-no-match-primary-focus')
            v=primary_clear_snapshot(p,'focus-history-wins',observed)
            assert not v['clearHidden'] and v['writes']==before
            assert parse_qs(urlsplit(v['url']).fragment)==parse_qs(f['b'])
            # The pre-hide projection itself can be reentered by recovery focus.
            browse_focus_hash(p,f['a']);browse_focus_hash(p,urlencode({**f['params'],'q':'HBM'}));clear.focus()
            before=p.evaluate('window.__browseFocus.writes.length')
            field.evaluate("""n=>n.addEventListener('focus',()=>{
              n.value='Micron';n.dispatchEvent(new Event('input',{bubbles:true}));
            },{once:true})""")
            p.go_back();expect(field).to_have_value('Micron')
            v=primary_clear_snapshot(p,'history-projection-newer-pass',observed)
            assert not v['clearHidden'] and v['writes']==before+1 and v['emptyHidden']
            # Redirect into another retiring subtree continues to the existing fallback.
            browse_focus_hash(p,f['b']);clear.focus()
            field.evaluate("""n=>n.addEventListener('focus',()=>{
              document.querySelector('[data-topic-no-results] [data-topic-reset]').focus();
            },{once:true})""")
            browse_focus_hash(p,f['a']);expect(field).to_have_value('')
            v=primary_clear_snapshot(p,'redirect-to-retiring-action',observed)
            expect(p.locator('[data-browse-close]') if f['narrow'] else p.locator('#gmi-topic-title')).to_be_focused()
            assert v['clearHidden'] and v['emptyHidden'] and v['dialogOpen']==f['narrow']

    def primary_clear_unenhanced(language):
        width=390 if language=='en' else 320;observed=[]
        report.setdefault('primary_clear_unenhanced',[]).append({'language':language,'phases':observed})
        with context(width,'light',language,java_script_enabled=False) as c:
            p=page_for(c,'gmi.html#q=HBM')
            clear=p.locator('[data-topic-search-clear]');assert clear.count()==1
            assert clear.get_attribute('hidden') is not None
            assert 'gmi-search--clearable' not in p.locator('.gmi-topic-search').get_attribute('class')
            assert p.locator('[data-gmi-ready]').count()==0 and p.locator('.gmi-topic-option').count()==371
            assert p.locator('[data-topic-search]').get_attribute('aria-label')=='Search themes, companies or products'
            observed.append({'phase':'no-js','clear_hidden':True,'enhanced':False,'native_theme_links':371})
        with context(width,'dark',language) as c:
            p,f=payload_failure_page(c,'malformed')
            clear=p.locator('[data-topic-search-clear]');assert clear.count()==1
            assert clear.get_attribute('hidden') is not None
            assert 'gmi-search--clearable' not in p.locator('.gmi-topic-search').get_attribute('class')
            expect(p.locator('[data-topic-notice-index]')).to_be_visible()
            expect(p.locator('[data-browse-open]')).not_to_be_visible()
            assert p.locator('[data-gmi-ready]').count()==0
            observed.append({'phase':'failed-payload','clear_hidden':True,'enhanced':False,'native_index_visible':True})

    for width,language in [(w,l) for w in (1440,390,320) for l in ('en','zh')]+[(820,'en'),(821,'zh')]:
        check(f'primary-clear-controls-{width}-{language}',lambda w=width,l=language:primary_clear_controls(w,l))
    for width,language in ((1440,'en'),(1440,'zh'),(390,'en'),(320,'zh')):
        check(f'primary-clear-history-{width}-{language}',lambda w=width,l=language:primary_clear_history(w,l))
        check(f'primary-clear-edges-{width}-{language}',lambda w=width,l=language:primary_clear_edges(w,l))
    for language in ('en','zh'):
        check(f'primary-clear-unenhanced-{language}',lambda l=language:primary_clear_unenhanced(l))

    browser.close()
server.shutdown()
report['pass'] = all(c['result']=='PASS' for c in report['cases']) and not report['page_errors']
(args.out/'browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'passed':sum(c['result']=='PASS' for c in report['cases']),'total':len(report['cases']),'page_errors':report['page_errors'],'report':str(args.out/'browser-report.json')}),flush=True)
raise SystemExit(0 if report['pass'] else 1)
