"""Capture complete unchanged-builder output and exercise retained research navigation."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
from contextlib import redirect_stdout,redirect_stderr
from urllib.parse import urlparse,unquote
import json,sys
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
ASSETS=(OUT/'proposed').resolve()
SHOTS=ROOT/'mockups/refs/reference_integrity/intl-country-intelligence-20261020/after_full'
sys.path.insert(0,str(ROOT))
from scripts import capture_page_evidence as capture
from playwright.sync_api import sync_playwright

def route_assets(context):
    def serve(route):
        url=urlparse(route.request.url)
        if url.scheme!='http' or url.hostname!='intl.test':
            return route.abort()
        path=(ASSETS/unquote(url.path).lstrip('/')).resolve()
        if not path.is_relative_to(ASSETS): return route.abort()
        if path.is_file(): return route.fulfill(path=str(path))
        return route.fulfill(status=404,body='')
    context.route('**/*',serve)

class IsolatedBrowser:
    def __init__(self,browser): self.browser=browser
    def new_context(self,**kwargs):
        context=self.browser.new_context(**kwargs)
        route_assets(context)
        return context
    def close(self): self.browser.close()

def chrome_driver(*,headless,user_agent,observer_config,settle_ms):
    manager=sync_playwright().start()
    try: browser=manager.chromium.launch(channel='chrome',headless=headless)
    except Exception as exc:
        manager.stop()
        raise capture.CaptureUnavailable(str(exc)) from exc
    return capture._PlaywrightDriver(manager,IsolatedBrowser(browser),user_agent,observer_config,settle_ms)

def context_for(browser,width,height,locale,theme):
    context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1)
    route_assets(context)
    context.add_init_script("""(({theme,locale})=>{
        localStorage.setItem('theme',theme);
        localStorage.setItem('lang',locale);
        localStorage.removeItem('themeAuto');
    })(SETTINGS)""".replace('SETTINGS',json.dumps({'theme':theme,'locale':locale})))
    return context

def settle(page,locale,theme):
    page.evaluate("""({locale,theme})=>{
        if(typeof window.setLang==='function')window.setLang(locale);
        if(typeof window.setTheme==='function')window.setTheme(theme);
    }""",{'locale':locale,'theme':theme})
    page.wait_for_timeout(700)
    page.evaluate('()=>document.fonts.ready.then(()=>true)')

def shot(page,name,extra=None):
    path=SHOTS/name
    page.screenshot(path=str(path),full_page=False,animations='disabled')
    return {'path':str(path.relative_to(ROOT)),'sha256':sha256(path.read_bytes()).hexdigest(),
        'bytes':path.stat().st_size,'captured_at':datetime.now(timezone.utc).isoformat(),**(extra or {})}

def main():
    SHOTS.mkdir(parents=True,exist_ok=True)
    build=json.loads((OUT/'complete_build_receipt.json').read_text())
    assert build['exit_code']==0
    assert sha256((ASSETS/'intl.html').read_bytes()).hexdigest()==build['html_sha256']
    args=['--repo',str(ROOT),'--base-url','http://intl.test','--routes','/intl.html',
        '--output-dir',str(SHOTS),'--manifest',str(OUT/'complete_capture_manifest.json'),
        '--smells',str(OUT/'complete_capture_census.json'),
        '--viewports','desktop,mobile','--locales','en,zh','--themes','light,dark',
        '--max-pages','1','--delay-ms','500','--settle-ms','700','--timeout-s','30']
    if '--direct-only' in sys.argv:
        assert (OUT/'complete_capture_manifest.json').is_file()
        exit_code=0
    else:
        with (OUT/'complete_capture.log').open('w') as log,redirect_stdout(log),redirect_stderr(log):
            exit_code=capture.main(args,driver_factory=chrome_driver)
    rows=[]
    checks=[]
    with sync_playwright() as runtime:
        browser=runtime.chromium.launch(channel='chrome',headless=True)
        for viewport,width,height in [('desktop',1440,900),('mobile',390,844),('narrow',320,720)]:
            for locale in ['en','zh']:
                for theme in ['light','dark']:
                    context=context_for(browser,width,height,locale,theme)
                    page=context.new_page()
                    errors=[]
                    page.on('pageerror',lambda error:errors.append(str(error)))
                    response=page.goto('http://intl.test/intl.html',wait_until='domcontentloaded')
                    settle(page,locale,theme)
                    state=page.evaluate(r"""()=>({
                        locale:document.documentElement.dataset.lang,
                        theme:document.documentElement.dataset.theme,
                        overflow:document.documentElement.scrollWidth>innerWidth,
                        toolsOpen:document.getElementById('intl-analysis-tools').open,
                        countryCount:document.querySelectorAll('[id^="imc-country-"]').length,
                        visibleWords:document.body.innerText.trim().split(/\s+/).length,
                        height:document.documentElement.scrollHeight
                    })""")
                    rows.append(shot(page,f'viewport-{viewport}-{locale}-{theme}.png',
                        {'viewport':viewport,'width':width,'height':height,'locale':locale,'theme':theme,
                         'response_sha256':sha256(response.body()).hexdigest(),'actual':state,'page_errors':errors}))
                    checks.append({'id':f'default-{viewport}-{locale}-{theme}',
                        'passed':response.status==200 and not state['overflow'] and not state['toolsOpen']
                            and state['locale']==locale and state['theme']==theme and not errors})
                    context.close()
        for viewport,width,height,locale,theme in [('desktop',1440,900,'en','light'),('mobile',390,844,'zh','dark')]:
            context=context_for(browser,width,height,locale,theme)
            page=context.new_page()
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            for view in ['overview','compare','macro','risk','history','library']:
                page.goto('http://intl.test/intl.html?view='+view,wait_until='domcontentloaded')
                settle(page,locale,theme)
                tools=page.locator('#intl-analysis-tools')
                panels=page.locator('[data-im-panel][data-view="'+view+'"]:visible')
                state={'tools_open':tools.get_attribute('open') is not None,'visible_panels':panels.count(),
                    'url':page.url,'control_enabled':page.locator('button[data-im-action="set_view"][data-im-view="'+view+'"]').first.is_enabled()}
                if panels.count(): panels.first.scroll_into_view_if_needed()
                rows.append(shot(page,f'tools-{view}-{viewport}-{locale}-{theme}.png',{'task':view,**state}))
                checks.append({'id':f'query-view-{view}-{viewport}','passed':state['tools_open'] and state['visible_panels']==1 and state['control_enabled'],'actual':state})
            page.goto('http://intl.test/intl.html',wait_until='domcontentloaded')
            settle(page,locale,theme)
            if page.locator('#intl-analysis-tools').get_attribute('open') is None:
                page.locator('#intl-analysis-tools > summary').click()
            for view in ['macro','risk','history','library','overview','compare']:
                control=page.locator('button[data-im-action="set_view"][data-im-view="'+view+'"]').first
                enabled=control.is_enabled()
                if enabled:
                    if control.is_visible():
                        control.click()
                    else:
                        page.locator('select[data-im-action="set_view"]').select_option(view)
                    page.wait_for_timeout(150)
                panels=page.locator('[data-im-panel][data-view="'+view+'"]:visible').count()
                checks.append({'id':f'click-view-{view}-{viewport}','passed':enabled and panels==1,'enabled':enabled,'visible_panels':panels,'url':page.url})
            for anchor in ['intl-growth-inflation','intl-central-banks','intl-credit-bonds','lb-board']:
                page.goto('http://intl.test/intl.html#'+anchor,wait_until='domcontentloaded')
                settle(page,locale,theme)
                target=page.locator('#'+anchor)
                state={'exists':target.count(),'visible':target.is_visible() if target.count() else False,
                    'tools_open':page.locator('#intl-analysis-tools').get_attribute('open') is not None}
                checks.append({'id':f'legacy-anchor-{anchor}-{viewport}','passed':bool(state['exists']) and state['visible'] and state['tools_open'],'actual':state})
            checks.append({'id':f'tools-page-exceptions-{viewport}','passed':not errors,'errors':errors})
            context.close()
        browser.close()
    receipt={'schema':'intl.reference_complete_browser.v1','build_receipt':'complete_build_receipt.json',
        'source_commit':build['source_commit'],'html_sha256':build['html_sha256'],
        'canonical_capture_exit':exit_code,'states':rows,'checks':checks,
        'passed':sum(bool(c['passed']) for c in checks),'failed':sum(not c['passed'] for c in checks),
        'limits':['Anonymous isolated browser; external calls aborted.',
            'Input copy does not acquire new source observations or qualify unknown FX receipts.',
            'No authenticated tier state was forced. Separate stock routes retain source identity but are not part of this page capture.']}
    (OUT/'complete_browser_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['states','checks']}))
    print(json.dumps({'failed_checks':[c for c in checks if not c['passed']]}))
    return exit_code or bool(receipt['failed'])
if __name__=='__main__':
    raise SystemExit(main())
