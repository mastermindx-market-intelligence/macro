from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from threading import Thread
import json,hashlib
from playwright.sync_api import sync_playwright
R=Path.cwd();E=R/'mockups/evidence/container-edge-removal/published-interactions';E.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(R/'site')))
Thread(target=server.serve_forever,daemon=True).start();origin=f'http://127.0.0.1:{server.server_port}'
results=[]
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  for viewport in [dict(width=1440,height=900),dict(width=390,height=844)]:
   for theme in ['dark','light']:
    context=browser.new_context(viewport=viewport,color_scheme=theme)
    context.route('**/*',lambda route: route.continue_() if route.request.url.startswith(origin) else route.abort())
    page=context.new_page()
    page.goto(origin+'/products/market-terminal.html',wait_until='domcontentloaded');page.wait_for_timeout(500)
    page.evaluate("(theme)=>{document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang='en'}",theme)
    row=page.locator('.mt-wl .r.sel').first;row.scroll_into_view_if_needed()
    page.wait_for_function("document.querySelector('#watchlists.mm-scene-visible')?.dataset.mmPhase === 'reason' && document.querySelector('.mt-wl .r.sel').getAnimations().some(a => a.animationName === 'mm-terminal-tick')")
    animations=row.evaluate("""el=>el.getAnimations().filter(a=>a.animationName==='mm-terminal-tick').map(a=>{const t=a.effect.getTiming();a.pause();a.currentTime=0;return {name:a.animationName,delay:t.delay,duration:t.duration,currentTime:a.currentTime};})""")
    page.wait_for_timeout(80)
    state=row.evaluate("el=>{const s=getComputedStyle(el);const c=new OffscreenCanvas(1,1).getContext('2d');c.fillStyle=s.backgroundColor;c.fillRect(0,0,1,1);return {background:s.backgroundColor,backgroundAlpha:c.getImageData(0,0,1,1).data[3],shadow:s.boxShadow,symbolWeight:getComputedStyle(el.querySelector('.sy')).fontWeight}}")
    state['animations']=animations
    assert state['backgroundAlpha']==0,state
    assert 'inset' in state['shadow'] and '0px 0px 0px 1px' in state['shadow'],state
    assert int(state['symbolWeight'])>=700,state
    state['phase']=page.locator('#watchlists').get_attribute('data-mm-phase')
    assert state['phase']=='reason' and len(animations)==1,state
    assert page.locator('.chap-x.on').evaluate("el=>getComputedStyle(el).fontWeight")=='800'
    name=f"terminal-selected-{viewport['width']}-{theme}.png";page.screenshot(path=str(E/name),clip=page.locator('.mt-wl').first.bounding_box(),animations='allow')
    results.append(dict(page='products/market-terminal.html',viewport=viewport,theme=theme,state='scene tick transparent start',computed=state,screenshot=name))
    page.goto(origin+'/products/market-dashboards.html',wait_until='domcontentloaded');page.wait_for_timeout(400)
    page.evaluate("(theme)=>{document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang='en'}",theme)
    tile=page.locator('.md-tile').first;tile.scroll_into_view_if_needed();page.keyboard.press('Tab');tile.focus()
    state=tile.evaluate("el=>{const s=getComputedStyle(el);return {pseudo:getComputedStyle(el,'::before').content,focusVisible:el.matches(':focus-visible'),outline:s.outlineStyle,outlineWidth:s.outlineWidth,shadow:s.boxShadow}}")
    assert state['pseudo']=='none' and state['focusVisible'],state
    assert (state['outline']!='none' and state['outlineWidth']!='0px') or state['shadow']!='none',state
    name=f"dashboard-focus-{viewport['width']}-{theme}.png";tile.screenshot(path=str(E/name))
    results.append(dict(page='products/market-dashboards.html',viewport=viewport,theme=theme,state='keyboard focus',computed=state,screenshot=name))
    page.goto(origin+'/products/market-dashboards.html#access',wait_until='domcontentloaded');page.wait_for_timeout(400)
    page.evaluate("(theme)=>{document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang='en'}",theme)
    card=page.locator('.callout').first;card.scroll_into_view_if_needed()
    state=card.evaluate("el=>{const s=getComputedStyle(el);return {left:s.borderLeftWidth,right:s.borderRightWidth,leftColor:s.borderLeftColor,rightColor:s.borderRightColor}}")
    assert state['left']==state['right']=='1px' and state['leftColor']==state['rightColor'],state
    name=f"dashboard-callout-{viewport['width']}-{theme}.png";card.screenshot(path=str(E/name))
    results.append(dict(page='products/market-dashboards.html',viewport=viewport,theme=theme,state='neutral callout',computed=state,screenshot=name))
    context.close()
  browser.close()
 for row in results:
  data=(E/row['screenshot']).read_bytes();row['sha256']=hashlib.sha256(data).hexdigest()
 (E/'receipt.json').write_text(json.dumps(dict(schema='mastermind.container_edge_published_interactions.v1',honesty='Loopback static public UI; external requests aborted; no account. Actual scene-motion mm-terminal-tick animation observed during reason, paused at its transparent start; no source styles or phase attributes overridden. Current product chapter font-weight verified as 800.',cases=results,passed=len(results)),indent=2)+'\n')
 print(json.dumps(dict(passed=len(results),screenshots=len(results))),flush=True)
finally:server.shutdown()
