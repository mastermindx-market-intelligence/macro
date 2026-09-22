"""Manual official-file proof through existing consumers; no source collection."""
from pathlib import Path
from datetime import datetime, timezone
import functools, hashlib, http.server, json, os, runpy, subprocess, sys, threading
import pandas as pd
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from collectors.china_universe import _close_weight_snapshot
from engine.china_participation import load_index_weight_context
from lib import store
from scripts import capture_page_evidence as capture

RAW=Path(sys.argv[1]).resolve()
OUT=ROOT/'mockups/evidence/china-index-weights-20260921'
OUT.mkdir(parents=True,exist_ok=True)
observed=datetime.now(timezone.utc).isoformat()
weights=_close_weight_snapshot(pd.read_excel(RAW),symbol='000300',observed_at=observed)
original_read=store.read
calls=[]
def injected_read(group,name,*args,**kwargs):
    if (group,name)==('china_search','index_weights'):
        calls.append((group,name)); return weights.copy(deep=True)
    return original_read(group,name,*args,**kwargs)
store.read=injected_read
os.environ.update(RENDER_NO_DRIP='1',CHINA_FAST_RENDER='1')
try:
    result=load_index_weight_context(asof='2026-09-18')
    assert result['eligible']==300 and result['status']=='available'
    try:
        runpy.run_module('scripts.build_china',run_name='__main__')
    except SystemExit as exc:
        if exc.code not in (None,0): raise
finally:
    store.read=original_read
assert len(calls)>=2, 'the real builder did not consume the optional weight reader'
PAGE=ROOT/'site/china.html'
page_hash=hashlib.sha256(PAGE.read_bytes()).hexdigest()
assert 'Fixed-start basket estimate' in PAGE.read_text()
CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
def driver_factory(**kwargs):
    manager=sync_playwright().start()
    try:
        browser=manager.chromium.launch(headless=True,executable_path=CHROME)
    except Exception:
        manager.stop(); raise
    return capture._PlaywrightDriver(manager,browser,kwargs.get('user_agent',capture.USER_AGENT),
        dict(kwargs.get('observer_config') or capture.DEFAULT_OBSERVER_CONFIG),kwargs.get('settle_ms',1400))
code=capture.main(['--site-dir',str(ROOT/'site'),'--routes','/china.html','--output-dir',str(OUT),
    '--manifest',str(OUT/'manifest.json'),'--smells',str(OUT/'smells.json'),
    '--viewports','desktop,mobile','--themes','dark,light','--locales','en,zh','--max-pages','1'],driver_factory=driver_factory)
assert code==0
meta=json.loads((OUT/'manifest.json').read_text())['pages'][0]
assert len(meta['states'])==8 and all(x['captured'] for x in meta['states'])
assert not meta['console_errors'] and not meta['failed_responses']
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(ROOT/'site')))
thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
cases=[]
try:
    with sync_playwright() as manager:
        browser=manager.chromium.launch(headless=True,executable_path=CHROME)
        try:
            for width,height in ((1440,900),(390,844)):
                for theme in ('dark','light'):
                    for lang in ('en','zh'):
                        ctx=browser.new_context(viewport={'width':width,'height':height})
                        try:
                            ctx.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('lang','{lang}');")
                            page=ctx.new_page(); errors=[]
                            page.on('pageerror',lambda e:errors.append(str(e)))
                            page.goto(f'http://127.0.0.1:{server.server_port}/china.html',wait_until='domcontentloaded')
                            page.locator('#cnx-participation summary').click()
                            panel=page.locator('.cnx-index-weights'); panel.wait_for(state='visible')
                            text=panel.text_content()
                            for expected in ['2026-08-31','2026-09-18','23.2%','-2.42%','300 / 300','not official index attribution','obtained after this return window']:
                                assert expected in text, expected
                            assert panel.locator('tbody tr').count()==6
                            assert not errors,errors
                            assert not page.evaluate('document.documentElement.scrollWidth>document.documentElement.clientWidth')
                            panel.screenshot(path=str(OUT/f'weights-{width}-{theme}-{lang}.png'))
                            cases.append({'width':width,'theme':theme,'locale':lang,'visible':True,'rows':6,'page_errors':errors})
                        finally: ctx.close()
        finally: browser.close()
finally:
    server.shutdown(); server.server_close(); thread.join(timeout=5)
assert not thread.is_alive()
assert hashlib.sha256(PAGE.read_bytes()).hexdigest()==page_hash
receipt={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
        ['collectors/china_universe.py','engine/china_participation.py','scripts/build_china.py','templates/_china_participation_context.html.j2']},
    'raw_weight_sha256':hashlib.sha256(RAW.read_bytes()).hexdigest(),
    'input_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
        ['data/china_search/closes.parquet','data/china/510300.SS.parquet']},
    'page_sha256':page_hash,'capture_cases':8,'interaction_cases':cases,'context':result,
    'source_injection':'genuine once-retrieved official workbook at store.read boundary; all other stored inputs unchanged',
    'automatic_ingestion':False,'production':False,'official_index_reconstruction':False,
    'server_closed':True,'weights_table_written':False}
(OUT/'interaction-proof.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print(json.dumps({'captures':8,'interactions':len(cases),'page_sha256':page_hash,'official_input_injected':True,'production':False}))
