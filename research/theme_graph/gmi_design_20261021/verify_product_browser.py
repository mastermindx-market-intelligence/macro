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
            totals = p.locator('[data-gmi-total]').evaluate_all('(nodes)=>nodes.map(n=>({value:n.textContent,total:n.getAttribute("data-gmi-total")}))')
            assert all(x['value']==x['total'] for x in totals)
            expect(p.locator('[data-gmi-index-feedback]')).not_to_be_visible()
            assert ('Full index: 371 micro-themes' if language=='en' else '完整索引：371 个细分主题') in p.locator('.gmi-foot').inner_text()
            # Real sticky geometry is exercised before filtering shortens the document.
            energy.click()
            p.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            targets=p.locator('.gmi-jump a:visible').evaluate_all('(nodes)=>nodes.map(n=>n.getBoundingClientRect().height)')
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
            assert p.locator('.gmi-jump a:visible').count()==1
            expect(semiconductor).to_be_visible()
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
            semiconductor.click()
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
            assert p.locator('.gmi-jump a:visible').count()==total
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
            restore('');energy.focus();restore('HBM')
            expect(search).to_be_focused()
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
            assert p.locator('.gmi-jump a:visible').count()==1
            p.go_forward();expect(search).to_have_value('zz-gmi-no-match-fixture')
            expect(nav).not_to_be_visible()
            restore('HBM')
            p.evaluate('(language)=>document.documentElement.setAttribute("data-lang",language)', 'zh' if language=='en' else 'en')
            assert p.locator('.gmi-jump a:visible').count()==1
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

    browser.close()
server.shutdown()
report['pass'] = all(c['result']=='PASS' for c in report['cases']) and not report['page_errors']
(args.out/'browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'passed':sum(c['result']=='PASS' for c in report['cases']),'total':len(report['cases']),'page_errors':report['page_errors'],'report':str(args.out/'browser-report.json')}),flush=True)
raise SystemExit(0 if report['pass'] else 1)
