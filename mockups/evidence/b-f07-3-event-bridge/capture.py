import json,threading
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright
root=Path.cwd()
evidence=root/'mockups/evidence/b-f07-3-event-bridge'
class QuietHandler(SimpleHTTPRequestHandler):
 def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
threading.Thread(target=server.serve_forever,daemon=True).start()
port=server.server_address[1]
records=[]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch()
  context=browser.new_context()
  page=context.new_page()
  errors=[]
  page.on('pageerror',lambda error:errors.append(str(error)))
  for state in ['tender-offer','restructuring','null']:
   for viewport,width,height in [('desktop',1440,900),('mobile',390,844)]:
    page.set_viewport_size({'width':width,'height':height})
    page.goto(f'http://127.0.0.1:{port}/mockups/evidence/b-f07-3-event-bridge/hosts/valuation-event-bridge-{state}.html',wait_until='networkidle')
    for theme in ['dark','light']:
     for lang in ['en','zh']:
      page.evaluate('([theme,lang])=>{document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang=lang;document.documentElement.lang=lang;document.dispatchEvent(new Event("langchange"));}',[theme,lang])
      page.evaluate('document.fonts.ready')
      page.wait_for_timeout(200)
      line=page.locator('#va-event-bridge')
      filename=f'valuation-event-bridge-{state}_{viewport}_{theme}_{lang}.png'
      line.screenshot(path=str(evidence/filename))
      metrics=line.evaluate('(e)=>({text:e.innerText,font:getComputedStyle(e).fontSize,color:getComputedStyle(e).color,width:e.clientWidth,scrollWidth:e.scrollWidth,footnoteFont:getComputedStyle(document.querySelector(".va-note")).fontSize})')
      assert metrics['font']=='11px' and metrics['footnoteFont']=='11.5px',metrics
      assert metrics['scrollWidth']<=metrics['width'],metrics
      assert ('No filing on file yet' in metrics['text'] or '该公司暂无备案' in metrics['text']) == (state=='null'),metrics
      records.append({'file':filename,'state':state,'viewport':viewport,'theme':theme,'language':lang,**metrics})
  browser.close()
 assert not errors,errors
 (evidence/'capture-metrics.json').write_text(json.dumps({'page_errors':errors,'cells':records},ensure_ascii=False,indent=2)+'\n')
 print(f'{len(records)} cells captured sequentially; 0 page errors; 11px < 11.5px; no line overflow.')
finally:
 server.shutdown()
