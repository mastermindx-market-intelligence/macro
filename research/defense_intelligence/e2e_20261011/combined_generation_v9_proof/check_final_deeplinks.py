"""Actual issuer/company deep-link functional coverage; no second budget batch."""
import argparse,json,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
from verify_stage import verify_stage
ap=argparse.ArgumentParser();ap.add_argument('url');ap.add_argument('stage');ap.add_argument('server_receipt');ap.add_argument('output');a=ap.parse_args()
s=Path(a.stage);out=Path(a.output);assert not out.exists();bound,parity=verify_stage(s);server=Path(a.server_receipt);runtime=json.loads(server.read_text());h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert runtime['stage_receipt_sha256']==h(s/'INPUT_RECEIPT.json')
def inputs_unchanged():
 assert sorted(str(path) for path in Path(runtime['canonical_input_directory']).rglob('*') if path.is_file())==runtime['canonical_input_inventory'], 'Canonical input inventory changed'
 for path,expected in runtime['api_source_modules'].items():assert h(path)==expected,path
 for path,expected in runtime['api_data_inputs'].items():assert (h(path) if Path(path).is_file() else None)==expected,path
inputs_unchanged();failures=[];errors=[];rows=[]
with sync_playwright() as p:
 b=p.chromium.launch();c=b.new_context(viewport={'width':390,'height':844},ignore_https_errors=True);page=c.new_page()
 page.on('response',lambda r:failures.append({'url':r.url,'status':r.status}) if r.status>=400 else None);page.on('pageerror',lambda e:errors.append(str(e)))
 url=a.url+'?mode=companies&ticker=RTX&item=company%3ARTX'
 response=page.goto(url,wait_until='commit');assert response is not None and response.status==200
 page.wait_for_function("window.__govrevFirstInvestor&&window.__govrevFirstInvestor.pageState==='ready'&&document.querySelector('#defenseInvestor[data-state=ready] [data-investor-ticker=RTX][aria-pressed=true]')&&document.querySelector('#inspector .inspect-id')&&document.querySelector('#inspector .inspect-id').textContent.trim()==='RTX'",timeout=60000)
 observed=page.evaluate("()=>({url:location.href,issuer:document.querySelector('[data-investor-ticker][aria-pressed=true]').textContent.trim(),value:document.querySelector('#defenseInvestor .gr-investor-primary dd').textContent.trim(),period:document.querySelector('#defenseInvestor .gr-investor-primary dt').textContent.trim(),company:document.querySelector('#inspector .inspect-id').textContent.trim(),ticker_filter:document.querySelector('#tickerFilter').value,failed_modules:window.__govrevFirstInvestor.failedModules.slice()})")
 assert observed['value']=='8269 USD millions' and observed['period'].endswith(' · 2026Q2') and observed['ticker_filter']=='RTX' and not observed['failed_modules'],observed
 rows.append({'case':'Actual company RTX deep link with qualified reported numeric finance','observation':observed,'passed':True})
 page.locator('[data-investor-ticker=LMT]').click();page.wait_for_function("document.querySelector('[data-investor-ticker=LMT][aria-pressed=true]')")
 page.go_back(wait_until='commit');page.wait_for_function("document.querySelector('[data-investor-ticker=RTX][aria-pressed=true]')")
 rows.append({'case':'Investor selection then browser back preserves issuer URL state','passed':True,'url':page.url})
 assert not failures and not errors,{'http_errors':failures,'page_errors':errors}
 c.close();b.close()
inputs_unchanged();verify_stage(s);assert runtime['stage_receipt_sha256']==h(s/'INPUT_RECEIPT.json');result={'scope':'Actual source ASGI local test-principal, unmodified normal publisher bytes; functional deep-link checks, no per-URL performance acceptance claim','stage_receipt_sha256':h(s/'INPUT_RECEIPT.json'),'server_receipt_sha256':h(server),'cases':rows,'http_errors':failures,'page_errors':errors}
out.write_text(json.dumps(result,indent=2));print(json.dumps({'cases_n':len(rows),'all_pass':True}))
