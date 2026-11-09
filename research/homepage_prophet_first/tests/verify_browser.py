"""In-memory rendering only. No browser navigation, HTTP server or production access."""
from __future__ import annotations
import hashlib, json, os, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence'

def main() -> None:
    EVIDENCE.mkdir(exist_ok=True)
    source=(ROOT/'prototype.html').read_text(encoding='utf-8')
    results=[]; screenshots=[]
    try:
        with sync_playwright() as p:
            executable = os.environ.get('CHROMIUM_BIN') or shutil.which('chromium') or shutil.which('google-chrome')
            launch_options = {'headless': True}
            if executable: launch_options['executable_path'] = executable
            if os.name == 'posix' and hasattr(os, 'geteuid') and os.geteuid() == 0:
                launch_options['args'] = ['--no-sandbox']
            browser=p.chromium.launch(**launch_options)
            try:
                for width in (320,390,768,1024,1440,1920):
                    for lang in ('en','zh'):
                        context=browser.new_context(viewport={'width':width,'height':1000},device_scale_factor=1,reduced_motion='reduce')
                        page=context.new_page(); errors=[]; external=[]
                        page.on('pageerror',lambda err:errors.append(str(err)))
                        def route(r):
                            external.append(r.request.url); r.abort()
                        page.route('**/*',route)
                        page.set_content(source,wait_until='load')
                        page.locator(f'[data-lang="{lang}"]').click()
                        assert page.locator('html').get_attribute('lang')==lang
                        assert page.locator('.hero .eyebrow').is_visible()
                        assert page.locator('h1').is_visible()
                        assert page.locator('nav .product-link').is_visible()
                        assert page.locator('#signal-example').is_visible()
                        assert page.locator('#prepared-read').is_visible()
                        for state in ('historical','empty','unavailable'):
                            if state!='historical': page.locator(f'a[data-state="{state}"]').click()
                            assert page.locator('body').get_attribute('data-state')==state
                            for other in ('historical','empty','unavailable'):
                                assert page.locator(f'#{other}-state').is_visible()==(state==other)
                            doc=page.evaluate('({width:innerWidth, scroll:document.documentElement.scrollWidth})')
                            assert doc['scroll']<=doc['width']+1, (width,lang,state,doc)
                            assert not errors, (width,lang,state,errors)
                            assert not external, (width,lang,state,external)
                            cta=page.locator('#primary-cta')
                            assert cta.get_attribute('href')=='https://www.mastermind-x.com/us_stocks.html'
                            if state=='historical':
                                for sel,text in [('#signal-ticker','HOOD'),('#signal-label','BUY'),('#signal-price','$108.13'),('#edge-grade','61'),('#zone-low','$103.00'),('#zone-high','$108.10')]:
                                    assert page.locator(sel).inner_text()==text
                                assert '2026-08-21' in page.locator('#sample-disclosure').inner_text()
                            results.append({'width':width,'language':lang,'state':state,'horizontal_overflow_px':doc['scroll']-doc['width'],'page_errors':list(errors),'external_requests':list(external),'passed':True})
                            capture=(state=='historical' and width in (390,1024,1440)) or (state=='empty' and width==390 and lang=='en') or (state=='unavailable' and width==1440 and lang=='en')
                            if capture:
                                page.evaluate('window.scrollTo(0,0)')
                                name=f'{state}-{width}-{lang}.png'; path=EVIDENCE/name
                                page.screenshot(path=str(path),full_page=True)
                                screenshots.append({'file':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'state':state,'width':width,'language':lang})
                        # Correctly unknown state, rather than silently presenting a historical BUY.
                        page.locator('a[data-state="unavailable"]').evaluate("e => e.dataset.state = 'not-known'")
                        page.locator('a[data-state="not-known"]').click()
                        assert page.locator('#unavailable-state').is_visible()
                        # Exact values and disclosure survive repeated language changes.
                        page.locator('a[data-state="historical"]').click()
                        for next_lang in ('zh','en','zh','en'):
                            page.locator(f'[data-lang="{next_lang}"]').click()
                            assert page.locator('#signal-price').inner_text()=='$108.13'
                            assert page.locator('#zone-high').inner_text()=='$108.10'
                            assert '2026-08-21' in page.locator('#sample-disclosure').inner_text()
                        assert not errors
                        context.close()
                nojs=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':1000})
                np=nojs.new_page();np.set_content(source,wait_until='load')
                assert np.locator('#signal-example').is_visible() and np.locator('#prepared-read').is_visible()
                assert np.locator('#primary-cta').get_attribute('href').endswith('/us_stocks.html')
                assert np.locator('#sample-disclosure').is_visible()
                nojs.close()
                keyboard=browser.new_context(viewport={'width':1440,'height':1000});kp=keyboard.new_page()
                kp.set_content(source,wait_until='load')
                kp.locator('[data-lang="zh"]').focus();kp.keyboard.press('Enter')
                assert kp.locator('html').get_attribute('lang')=='zh'
                kp.locator('a[data-state="empty"]').focus();kp.keyboard.press('Enter')
                assert kp.locator('#empty-state').is_visible()
                keyboard.close()
                receipt={'schema':'design-review-receipt/v1','source_sha256':hashlib.sha256((ROOT/'prototype.html').read_bytes()).hexdigest(),'browser':browser.version,'browser_path':executable or 'playwright-bundled','scope':'In-memory set_content of standalone prototype; no URL navigation, original homepage, production or route proof','navigation_attempt':'Local URL rejected with ERR_BLOCKED_BY_ADMINISTRATOR; not retried','render_transport':'in_memory_document','cases':results,'unknown_state_cases':12,'language_roundtrip_contexts':12,'no_js':'passed','keyboard':'passed','screenshots':screenshots,'production_visited':False,'account_or_subscription_actions':False,'independent_product_acceptance':False}
                (EVIDENCE/'browser-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                print(f'{len(results)} responsive/language/state cases passed; 12 unknown-state cases; 12 language-roundtrip contexts; no-JS and keyboard passed.')
                print('Production not visited; external board destination verified as a link only.')
            finally: browser.close()
    finally:
        pass

if __name__=='__main__': main()
