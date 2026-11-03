"""R2 browser acceptance: query recovery vs missing watchlist, never live-feed proof."""
from __future__ import annotations
import functools
import hashlib
import json
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright
import verify_browser as existing

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'mockups/refs/intraday-flow-upgrade/recovery-r2'
checks=[]

def check(name, condition, **details):
    checks.append({'check':name,'passed':bool(condition),**details})
    print(name+(': PASS' if condition else ': FAIL'), flush=True)
    assert condition, name+': '+json.dumps(details,ensure_ascii=False)

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

def geometry(page, key, width):
    g=page.evaluate('''() => ({width:document.documentElement.scrollWidth,
      actions:[...document.querySelectorAll('.ift-empty-actions button')].map(el=>({
       height:el.getBoundingClientRect().height,right:el.getBoundingClientRect().right}))})''')
    check(key+'/no-overflow',g['width']<=width,geometry=g)
    check(key+'/44px-targets',all(x['height']>=44 for x in g['actions']),geometry=g)
    if width<=390:
        check(key+'/launcher-clearance',all(x['right']<=315 for x in g['actions']),geometry=g)

def filtered(browser, url, width, theme, locale):
    key=f'{width}/{theme}/{locale}/filtered'
    context=existing.source_context(browser,theme,locale,width)
    page=context.new_page();page.goto(url,wait_until='networkidle');existing.await_board(page)
    page.locator('#ift-theme-menu > summary').click()
    page.locator('button[data-basket="defense"]').click()
    stance=page.locator('tr.lead-row:visible').first.get_attribute('data-stance')
    page.locator('.stance-card[data-stance="'+stance+'"]').click()
    check(key+'/starting-population',existing.visible_count(page)>0)
    if width<760:
        page.locator('#ift-mobile-sort').select_option('ticker-desc')
    else:
        page.locator('th[data-col="ticker"] .ift-sort').click()
        page.locator('th[data-col="ticker"] .ift-sort').click()
    before=page.locator('#ift-mobile-sort').input_value()
    search=page.locator('#ift-search');search.fill('ZZZ_NO_MATCH')
    page.locator('[data-ift-empty-kind="filtered"]').wait_for()
    check(key+'/distinct-query-action',page.locator('#ift-empty-clear-search').is_visible())
    check(key+'/full-reset-action',page.locator('#ift-empty-reset').is_visible())
    check(key+'/not-watchlist-failure',page.locator('[data-reload-board]').count()==0)
    geometry(page,key,width)
    before_checks=len(existing.results)
    existing.refresh_focus(context,page,'#ift-empty-clear-search',key+'/refresh-focus')
    checks.extend(existing.results[before_checks:])
    page.locator('#ift-empty-clear-search').press('Enter')
    check(key+'/clear-query',search.input_value()=='')
    check(key+'/focus-search',page.evaluate('document.activeElement.id')=='ift-search')
    check(key+'/theme-retained',page.locator('button[data-basket="defense"]').get_attribute('aria-pressed')=='true')
    check(key+'/setup-retained',page.locator('.stance-card[data-stance="'+stance+'"]').get_attribute('aria-pressed')=='true')
    check(key+'/sort-retained',page.locator('#ift-mobile-sort').input_value()==before)
    check(key+'/population-restored',existing.visible_count(page)>0)
    search.fill('<img src=x onerror="window.__iftInjected=1">'*8)
    check(key+'/html-escaped',page.locator('.ift-empty img').count()==0 and page.evaluate('window.__iftInjected === undefined'))
    geometry(page,key+'/long-query',width)
    search.fill('ZZZ_NO_MATCH')
    image=OUT/f'filtered-{width}-{theme}-{locale}.png';page.screenshot(path=str(image),full_page=True)
    page.locator('#ift-empty-reset').click()
    check(key+'/reset-all',page.locator('button[data-basket="all"]').get_attribute('aria-pressed')=='true' and
          page.locator('.stance-card[aria-pressed="true"]').count()==0 and search.input_value()=='')
    check(key+'/reset-focus',page.evaluate('document.activeElement.id')=='ift-search')
    context.close()

def missing_watchlist(browser,url,width,theme,locale):
    key=f'{width}/{theme}/{locale}/no-watchlist'
    context=existing.source_context(browser,theme,locale,width)
    base=json.loads((ROOT/'site/flowtracker/base.json').read_text());base.update(leaders=[],n_leaders=0)
    html=(ROOT/'site/intraday_flow.html').read_text()
    html,count=re.subn(r'var BASE_DATA = [\s\S]*?;\nvar RVOL_CONFIRM',lambda _: 'var BASE_DATA = '+json.dumps(base)+';\nvar RVOL_CONFIRM',html,count=1)
    assert count==1
    navigations=[]
    def serve(route):
        navigations.append(route.request.url)
        route.fulfill(status=200,body=html,content_type='text/html')
    context.route('**/intraday_flow.html',serve)
    page=context.new_page();page.goto(url,wait_until='networkidle')
    page.locator('[data-ift-empty-kind="unavailable"]').wait_for()
    check(key+'/unknown-counts',page.locator('[data-count]').all_text_contents()==['—']*6)
    check(key+'/no-filter-reset',page.locator('[data-reset-filters],[data-clear-search]').count()==0)
    check(key+'/reload-offered',page.locator('[data-reload-board]').is_visible())
    check(key+'/no-permanent-loading-row',page.locator('tr.loading-row,tr.ift-skel-row').count()==0)
    expected='观察名单不可用' if locale=='zh' else 'Watchlist unavailable'
    check(key+'/truthful-footer',expected in page.locator('#count-label').inner_text())
    check(key+'/truthful-inspector',expected in page.locator('#ift-inspector').text_content())
    geometry(page,key,width)
    page.screenshot(path=str(OUT/f'unavailable-{width}-{theme}-{locale}.png'),full_page=True)
    with page.expect_navigation(wait_until='networkidle'):
        page.locator('[data-reload-board]').click()
    check(key+'/reload-same-page',len(navigations)==2 and page.url==url)
    context.close()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(ROOT/'site')))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url=f'http://127.0.0.1:{server.server_port}/intraday_flow.html'
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch()
            for width in (1440,390):
                for theme in ('light','dark'):
                    for locale in ('en','zh'):
                        for fn in (filtered,missing_watchlist):
                            try:fn(browser,url,width,theme,locale)
                            except Exception as exc:
                                checks.append({'check':f'{fn.__name__}/{width}/{theme}/{locale}/exception','passed':False,'error':str(exc)})
            browser.close()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
    images=[{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(OUT.glob('*.png'))]
    report={'kind':'isolated_browser_recovery_r2','fixture_note':'Missing watchlist is a synthetic TEST FIXTURE served only inside isolated browser; filtered query uses committed recorded board. No feed or producer writes.',
       'source_page_sha256':hashlib.sha256((ROOT/'site/intraday_flow.html').read_bytes()).hexdigest(),
       'checks':checks,'images':images}
    (OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    failures=[x for x in checks if not x['passed']]
    print(json.dumps({'checks':len(checks),'passed':len(checks)-len(failures),'failures':failures,'images':len(images)},ensure_ascii=False))
    return bool(failures)

if __name__=='__main__':
    raise SystemExit(main())
