"""Browser contract smoke tests for the isolated design prototype, never production proof."""
from __future__ import annotations
import hashlib,json,threading
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
URL=f'http://127.0.0.1:{server.server_port}/prototype.html'
checks=[]; errors=[]; external_requests=[]
def record(name): checks.append(name); print('PASS',name,flush=True)
def fit(page): assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'horizontal overflow'
try:
  with sync_playwright() as playwright:
    browser=playwright.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1440,'height':900},device_scale_factor=1)
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.on('request',lambda request:external_requests.append(request.url) if not request.url.startswith(f'http://127.0.0.1:{server.server_port}/') else None)
    page.goto(URL);assert page.locator('#app h1').inner_text()=='Understand the signal.'
    assert not page.locator('#results').is_visible();record('question-led home; full catalog not dumped at rest')
    page.keyboard.press('/');assert page.locator('#search').evaluate('(node)=>node===document.activeElement');record('slash focuses search')
    page.locator('#search').fill('state dial');assert page.locator('.result').count()==1;assert 'Market State Score' in page.locator('.result').inner_text();record('English alias search')
    page.reload();assert page.locator('#search').input_value()=='state dial';assert page.locator('.result').count()==1;record('query URL survives reload')
    page.locator('[data-reset]').click();page.locator('#search').fill('市场状态评分');assert page.locator('.result').count()==1;record('Chinese alias search in English UI')
    page.locator('#search').fill('<img src=x onerror=alert(1)>');assert page.locator('.empty').is_visible();assert page.locator('#result-list img').count()==0;record('empty state and inert query markup')
    page.locator('.empty [data-browse]').click();assert page.locator('.result').count()==46;record('all 46 registry entries retained')
    trigger=page.locator('[data-help="market-state-score"]:visible');trigger.scroll_into_view_if_needed();scroll=page.evaluate('scrollY');trigger.click();assert page.locator('#help').evaluate('(node)=>node.open')
    page.locator('#help [data-state="higher"]').click();assert 'More signals align.' in page.locator('#help').inner_text()
    page.keyboard.press('Escape');assert not page.locator('#help').evaluate('(node)=>node.open');assert trigger.evaluate('(node)=>node===document.activeElement');assert abs(page.evaluate('scrollY')-scroll)<3;record('quick help state switch, Escape, focus and scroll restoration')
    page.goto(URL+'#market-state-score');assert page.locator('#app h1').inner_text()=='Market State Score';assert 'Not a prediction.' in page.locator('.caution').inner_text();record('existing entry hash opens the right guide and visible limitation')
    page.locator('[data-home]').click();page.go_back();assert page.locator('#app h1').inner_text()=='Market State Score';record('browser history restores the selected entry')
    page.goto(URL+'#does-not-exist');assert 'not in the guide' in page.locator('#app h1').inner_text();record('unknown entry has actionable fallback')
    # Every shipped illustration can be read at both device widths and in both languages/themes.
    for width in [1440,390]:
      page.set_viewport_size({'width':width,'height':900 if width==1440 else 844})
      for lang in ['en','zh']:
        page.goto(URL+('?lang=zh' if lang=='zh' else ''))
        for theme in ['light','dark']:
          if page.locator('html').get_attribute('data-theme')!=theme:page.locator('#theme').click()
          fit(page);page.screenshot(path=str(ROOT/f'browser-home-{theme}-{lang}-{width}.png'),full_page=True)
          page.locator('[data-id="market-state-score"]').first.click();fit(page)
          page.screenshot(path=str(ROOT/f'browser-detail-{theme}-{lang}-{width}.png'),full_page=True)
          page.locator('[data-home]').click()
          page.locator('[data-help="market-state-score"]:visible').click();fit(page)
          page.screenshot(path=str(ROOT/f'browser-help-{theme}-{lang}-{width}.png'))
          page.keyboard.press('Escape')
    record('24 browser states captured: home/detail/help × light/dark × EN/ZH × 1440/390; no page overflow')
    source_entries=page.locator('#registry').evaluate('(node)=>JSON.parse(node.textContent).entries')
    for language,width in [('en',1440),('zh',390)]:
      page.set_viewport_size({'width':width,'height':900 if width==1440 else 844})
      for entry in source_entries:
        page.goto(URL+('?lang=zh' if language=='zh' else '')+'#'+entry['id'])
        assert page.locator('#app h1').inner_text()==entry['label_'+language]
        fit(page)
    record('all 46 detail routes render in EN desktop and ZH mobile without horizontal overflow')
    nojs=browser.new_context(java_script_enabled=False);fallback=nojs.new_page();fallback.goto(URL)
    assert fallback.locator('.fallback').is_visible();assert fallback.locator('.fallback details').count()==46;fallback.locator('summary').first.click();assert fallback.locator('.fallback details').first.get_attribute('open') is not None
    nojs.close();record('JavaScript-disabled bilingual disclosure fallback retains 46 entries')
    assert not errors,errors;record('no uncaught browser errors')
    assert not external_requests,external_requests;record('zero external requests during guide/search/help flows')
    browser.close()
finally:
  server.shutdown();server.server_close()
result={'scope':'design prototype only; not a production acceptance run','checks':checks,'count':len(checks),'browser_errors':errors,'external_requests':external_requests,'prototype_sha256':hashlib.sha256((ROOT/'prototype.html').read_bytes()).hexdigest()}
(ROOT/'browser-test-receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'passed':len(checks),'errors':errors}))
