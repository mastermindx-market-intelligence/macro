import json
from pathlib import Path
from playwright.sync_api import sync_playwright
HERE=Path('mockups/options_workspace_revamp');SOURCE=HERE/'fixtures/published'
payloads=json.loads((SOURCE/'payloads.json').read_text());origin='http://127.0.0.1:8768'
out={'manifest':json.loads((SOURCE/'manifest.json').read_text()),'scope':'Exact rendered published fixture; historical research, not live quotes','modes':{}}
with sync_playwright() as p:
 b=p.chromium.launch(headless=True);c=b.new_context(viewport={'width':1440,'height':1000},service_workers='block')
 def route(r):
  key=next((k for k in payloads if r.request.url.split('?')[0].endswith('/'+k)),None)
  if key:r.fulfill(status=200,content_type='application/json',body=json.dumps(payloads[key]))
  elif r.request.url.startswith(origin+'/'):r.continue_()
  else:r.abort()
 c.route('**/*',route);q=c.new_page();q.goto(origin+'/mockups/options_workspace_revamp/fixtures/published/workspace.html?theme=light&lang=en#brief',wait_until='networkidle')
 for mode in ['brief','flow','scanner','ticker','leaders']:
  q.mouse.move(12,850);q.locator('#tab-'+mode).evaluate("e=>e.scrollIntoView({block:'center',behavior:'instant'})");q.locator('#tab-'+mode).click()
  q.locator('#mode-'+mode+' .oew-skel').wait_for(state='detached',timeout=20000)
  if mode=='ticker':q.locator('#oew-shelf>summary').click();q.wait_for_function("document.querySelector('#oew-raw-slot')?.textContent.length>0")
  out['modes'][mode]=q.locator('#mode-'+mode).evaluate("""m=>({
    panels:[...m.querySelectorAll('.oew-panel')].map(p=>({title:p.querySelector('h2,summary')?.innerText,text:p.innerText.slice(0,2100),dates:[...p.querySelectorAll('.oew-asof')].map(e=>e.innerText)})),
    rows:[...m.querySelectorAll('tbody tr')].slice(0,8).map(r=>[...r.querySelectorAll('td')].filter(e=>getComputedStyle(e).display!=='none').map(e=>e.innerText)),
    columns:[...m.querySelectorAll('thead th')].filter(e=>getComputedStyle(e).display!=='none').map(e=>e.innerText),
    raw:[...m.querySelectorAll('.oew-raw-item')].map(p=>({title:p.querySelector('h3')?.innerText,text:p.innerText.slice(0,2500),svgs:[...p.querySelectorAll('svg')].map(s=>s.outerHTML)}))
  })""")
 b.close()
(HERE/'paper_actual_samples.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'file':str(HERE/'paper_actual_samples.json'),'bytes':(HERE/'paper_actual_samples.json').stat().st_size,'modes':list(out['modes']),'raw_charts':sum(len(p['svgs']) for p in out['modes']['ticker']['raw'])},indent=2))