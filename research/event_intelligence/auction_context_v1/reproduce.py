from pathlib import Path
import sys, json, hashlib, threading, http.server, datetime
from unittest.mock import patch
import argparse
parser=argparse.ArgumentParser(description="Offline event component acceptance proof; never production auth")
parser.add_argument('--out', required=True, type=Path)
parser.add_argument('--browser', required=True, type=Path)
args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from playwright.sync_api import sync_playwright
from tests.test_dashboard_template_render import _env, _base_vm
from engine import event_calendar as ec
OUT=args.out
OUT.mkdir(parents=True,exist_ok=True)
shutil_source=ROOT/'tests/fixtures/treasury_auction_official_20260917.json'
(OUT/'treasury-upcoming.json').write_bytes(shutil_source.read_bytes())
(OUT/'source-receipt.json').write_bytes((Path(__file__).parent/'source-receipt.json').read_bytes())
rows=json.loads((OUT/'treasury-upcoming.json').read_text())
with patch.object(ec,'_fetch_upcoming_auctions',return_value=rows):
    events=ec._auction_events(datetime.date(2026,9,17),datetime.date(2026,9,30))
assert len(events)==4
vm=_base_vm();vm['macro_catalysts']=events
html=_env().get_template('dashboard.html.j2').render(**vm,mode='macro')
(OUT/'macro.html').write_text(html)
(OUT/'projected-events.json').write_text(json.dumps(events,ensure_ascii=False,indent=2))
# Exercise the actual event component without a synthetic signed-in identity.
# Full-page navigation correctly hit the authentication boundary; it is not bypassed.
from bs4 import BeautifulSoup
soup=BeautifulSoup(html,'html.parser')
dialog=soup.find(id='dlg-events')
dialog['class']=dialog.get('class',[])+['open']
source=(ROOT/'templates/dashboard.html.j2').read_text()
a=source.index('    var RR_MOS_EN =')
z=source.index('    function wireCalendarCards()',a)
z=source.index('\n    }\n',z)+7
selector=source[a:z]
glue="""
var _rrItems=[], _rrInlineDate=null, _rrInlineSignature=null, _rrInlineSwapToken=0, _rrInlineSwapTimer=null;
function _rrInlineBody(){return document.getElementById('rr-inline-body');}
function _rrInlineDateEl(){return document.getElementById('rr-inline-date');}
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function openModal(){throw new Error('No forecast was supplied to this component proof');}
function renderCard(){throw new Error('No forecast was supplied to this component proof');}
"""
html='<html data-theme="dark" data-lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="/theme.css">'+''.join(str(x) for x in soup.find_all('style'))+'</head><body>'+str(dialog)+str(soup.find(id='calendar-event-context-data'))+'<script>'+(ROOT/'templates/calendar_event_context.js').read_text()+'</script><script>'+glue+selector+'\nwireCalendarCards();</script></body></html>'
(OUT/'component.html').write_text(html)
BASE=ROOT/'templates'
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(BASE),**kw)
    def log_message(self,*a):pass
    def do_GET(self):
        p=self.path.split('?')[0]
        if p in ['/macro.html','/theme.css','/macrodata/release_forecast.json']:
            if p=='/macro.html':body=html.encode();typ='text/html; charset=utf-8'
            elif p=='/theme.css':body=(ROOT/'templates/theme.css').read_bytes();typ='text/css'
            else:body=b'{"items":[],"status":"unavailable"}';typ='application/json'
            self.send_response(200);self.send_header('Content-Type',typ);self.end_headers();self.wfile.write(body)
        else:super().do_GET()
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
origin=f'http://127.0.0.1:{server.server_port}'
records=[]
try:
 with sync_playwright() as pw:
    exe=args.browser
    browser=pw.chromium.launch(headless=True,executable_path=str(exe))
    page=browser.new_page(viewport={'width':1440,'height':1100},reduced_motion='reduce')
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('**/*',lambda r:r.continue_() if r.request.url.startswith(origin) else r.abort())
    page.goto(origin+'/macro.html',wait_until='domcontentloaded')
    page.wait_for_function("!!window.MMXCalendarEventContext")
    page.wait_for_selector('#dlg-events .rr-select',timeout=15000)
    for width in (1440,390):
     page.set_viewport_size({'width':width,'height':1100})
     for theme in ('dark','light'):
      for lang in ('en','zh'):
       page.evaluate("v=>{document.documentElement.setAttribute('data-theme',v.theme);document.documentElement.setAttribute('data-lang',v.lang)}",{'theme':theme,'lang':lang})
       page.locator('#dlg-events .mx5-dlg-cal-card[data-cal-date="2026-09-23"]').first.click()
       page.wait_for_function("document.querySelectorAll('#rr-inline-body .eic-card').length===2")
       text=page.locator('#rr-inline-body').inner_text()
       assert '91282CRD5' in text and '91282CRN3' in text
       assert '28,000,000,000' in text
       assert '11:30' in text and '13:00' in text
       assert page.locator('#rr-inline-body .rr-card').count()==0
       bounds=page.locator('#rr-inline-body').evaluate('(el)=>({w:el.clientWidth,scroll:el.scrollWidth})')
       assert bounds['scroll']<=bounds['w']+1,bounds
       page.locator('#rr-inline').scroll_into_view_if_needed()
       if theme == 'light':
        ink=page.locator('#dlg-events .mx5-dlg-title').evaluate('(el)=>getComputedStyle(el).color')
        assert ink not in ('rgb(255, 255, 255)','rgba(255, 255, 255, 0.62)','rgba(255, 255, 255, 0.6)'),ink
       file=f'{width}-{theme}-{lang}.png';page.locator('#dlg-events .mx5-dlg-panel').screenshot(path=str(OUT/file))
       records.append({'viewport_width':width,'theme':theme,'lang':lang,'file':file,'sha256':hashlib.sha256((OUT/file).read_bytes()).hexdigest(),'cards':2,'bounds':bounds})
    # Keyboard disclosure; actual DOM interaction, not just a string assertion.
    summary=page.locator('#rr-inline-body details summary').first
    summary.focus();page.keyboard.press('Enter')
    assert page.locator('#rr-inline-body details').first.get_attribute('open') is not None
    # Same date: no duplicate cards; another date changes the source facts.
    page.locator('#dlg-events .mx5-dlg-cal-card[data-cal-date="2026-09-22"]').click()
    page.wait_for_function("document.querySelectorAll('#rr-inline-body .eic-card').length===1")
    assert '91282CRP8' in page.locator('#rr-inline-body').inner_text()
    browser.close()
finally:
 server.shutdown();server.server_close()
manifest={'scope':'real official API capture -> calendar adapter -> full production template -> extracted real event component + actual selector/renderer in local browser; surrounding VM synthetic; full app authentication NOT bypassed; NOT deployed/authenticated production acceptance',
 'generated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':json.loads((OUT/'source-receipt.json').read_text()),
 'html_sha256':hashlib.sha256(html.encode()).hexdigest(),'source_file_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'engine/event_calendar.py',ROOT/'engine/calendar_event_context.py',ROOT/'templates/dashboard.html.j2',ROOT/'templates/calendar_event_context.js',ROOT/'templates/_calendar_event_context.html.j2']},
 'cases':records,'page_errors':errors,'keyboard_disclosure':True,'cross_date':True,'same_date_multi_event':True,'forecast_payload':'explicitly unavailable'}
(OUT/'browser-manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({'status':'PASS','cases':len(records),'page_errors':errors,'manifest':str(OUT/'browser-manifest.json')},indent=2))

# Reuse the canonical capture owner for committed theme-evidence receipts.
# The injected driver is the SAME real driver; only the installed binary differs.
from scripts import capture_page_evidence as cap
from playwright.sync_api import sync_playwright
import shutil
capture_site=OUT/'canonical-page';capture_site.mkdir(exist_ok=True)
page_html=(OUT/'component.html').read_text().replace('wireCalendarCards();</script>',
    "wireCalendarCards();selectInlineDate('2026-09-23',null,true);document.querySelector('#rr-inline').scrollIntoView();</script>")
# Canonical REST theme matrix captures the dossier component without modal
# geometry. Real modal selection/disclosure was exercised above separately.
# Do not qualify empty/offscreen full-page captures as useful visual evidence.
from bs4 import BeautifulSoup as Soup
stage=Soup(page_html,'html.parser')
panel=stage.find(id='rr-inline')
data=stage.find(id='calendar-event-context-data')
style=''.join(str(x) for x in stage.find_all('style'))
page_html='<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="/theme.css">'+style+'</head><body><main id="dlg-events" style="max-width:980px;margin:24px auto;padding:16px">'+str(panel)+'</main>'+str(data)+'<script>'+(ROOT/'templates/calendar_event_context.js').read_text()+'</script><script>'+glue+selector+"selectInlineDate('2026-09-23',null,true);</script></body></html>"
(capture_site/'event-context-proof.html').write_text(page_html)
shutil.copy2(ROOT/'templates/theme.css',capture_site/'theme.css')
evidence=OUT/'canonical-evidence';evidence.mkdir(exist_ok=True)
def canonical_driver(**kw):
    manager=sync_playwright().start()
    try:
        browser=manager.chromium.launch(headless=kw['headless'],executable_path=str(args.browser))
    except Exception:
        manager.stop()
        raise
    return cap._PlaywrightDriver(manager,browser,kw['user_agent'],
        kw['observer_config'] or cap.DEFAULT_OBSERVER_CONFIG,kw['settle_ms'])
rc=cap.main(['--site-dir',str(capture_site),'--routes','/event-context-proof.html',
    '--output-dir',str(evidence/'captures'),'--manifest',str(evidence/'manifest.json'),
    '--smells',str(evidence/'smells.json'),'--viewports','desktop,mobile',
    '--locales','en,zh','--themes','dark,light','--max-pages','1','--delay-ms','0'],
    driver_factory=canonical_driver)
assert rc==0,rc

canonical_manifest=json.loads((evidence/'manifest.json').read_text())
cells=canonical_manifest['pages'][0]['states']
assert len({c['sha256'] for c in cells if c.get('captured')})==8, 'locale/theme matrix contains identical captures; inspect the page'
