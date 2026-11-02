import hashlib,json
from pathlib import Path
from playwright.sync_api import sync_playwright
import sys
fixture=Path(sys.argv[1]).resolve() / 'quote.html'
out=Path(__file__).resolve().parent
records=[]
with sync_playwright() as p:
 browser=p.chromium.launch()
 for state,theme,locale,width in [('expired','dark','en',390),('unavailable','light','zh',390),('recovery','light','en',1440)]:
  context=browser.new_context(viewport={'width':width,'height':900 if width==1440 else 844})
  context.route('http://**/*',lambda route:route.abort())
  context.route('https://**/*',lambda route:route.abort())
  page=context.new_page(); errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
  page.goto(fixture.as_uri()+'?state='+('expired' if state=='recovery' else state))
  page.evaluate('([theme,lang])=>{document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang=lang;document.documentElement.lang=lang}',[theme,locale])
  if state in ['expired','recovery']:
   page.locator('[data-dq-extended][data-dq-state=stale]').wait_for()
  if state=='recovery':
   page.evaluate('fixturePacket.extended_quote.as_of_ms=fixtureNow-1000;fixturePacket.extended_quote.valid_until_ms=fixtureNow+118000;document.dispatchEvent(new Event("visibilitychange"))')
   page.locator('[data-dq-ext-price]').filter(has_text='$99.00').wait_for()
  else:
   page.locator('[data-dq-ext-values]').wait_for(state='hidden')
  observed=page.evaluate('''()=>({regular:document.querySelector('[data-dq-sym]').textContent,
   extended:document.querySelector('[data-dq-ext-price]').textContent,status:document.querySelector('[data-dq-extended]').dataset.dqState,
   visibleText:document.querySelector('[data-dq-extended]').innerText,overflow:document.documentElement.scrollWidth>innerWidth})''')
  assert observed['regular']=='100.00' and not observed['overflow'] and not errors
  file=f'{state}-{theme}-{locale}-{width}.png';page.screenshot(path=str(out/file),full_page=True)
  records.append({'state':state,'theme':theme,'locale':locale,'width':width,'file':file,'sha256':hashlib.sha256((out/file).read_bytes()).hexdigest(),'observed':observed,'page_errors':errors})
  context.close()
 browser.close()
(out/'negative-states.json').write_text(json.dumps({'synthetic':True,'tool':'capture_negative.py','tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'network':'file fixture with http/https aborted and CSP connect-src none','states':records},indent=2)+'\n')
print(json.dumps(records,ensure_ascii=False))
