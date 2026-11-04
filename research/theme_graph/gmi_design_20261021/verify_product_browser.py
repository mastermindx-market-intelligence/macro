"""Exercise generated public GMI pages in a fresh headless browser profile.

Usage: python verify_product_browser.py --site SITE --out PROOF --executable CHROME
No signed-in profile, publication, source data mutation, or service stub is used.
The clipboard-denied and malformed-payload cases are explicit fault injections.
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
            p.locator('.gmi-company-card a').first.click()
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
            p.locator('.gmi-product-tools a[href="gmi-index.html"]').click()
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
            p.locator('.gmi-company-card a').first.click()
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
            assert p.locator('.gmi-product-tools a[href="gmi-index.html"]').is_visible()
    check('server-answer-without-javascript', no_script)
    browser.close()
server.shutdown()
report['pass'] = all(c['result']=='PASS' for c in report['cases']) and not report['page_errors']
(args.out/'browser-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'passed':sum(c['result']=='PASS' for c in report['cases']),'total':len(report['cases']),'page_errors':report['page_errors'],'report':str(args.out/'browser-report.json')}),flush=True)
raise SystemExit(0 if report['pass'] else 1)
