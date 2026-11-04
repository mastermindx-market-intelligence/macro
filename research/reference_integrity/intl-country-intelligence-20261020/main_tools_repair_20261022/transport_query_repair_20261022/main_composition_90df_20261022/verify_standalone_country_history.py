"""Actual same-document country links, history restoration, and rapid destination changes."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import argparse, importlib.util, json
from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout
ROOT = Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018")
OUT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--label', required=True)
args = parser.parse_args()
build = json.loads((OUT / ('repair_' + args.label + '_build_receipt.json')).read_text())
assert build['exit_code'] == 0 and not build['source_overlays']
spec = importlib.util.spec_from_file_location('reference_capture', Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020") / 'capture_complete_reference.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.ASSETS = OUT / ('proposed_' + args.label + '_repair')
assert sha256((module.ASSETS / 'intl.html').read_bytes()).hexdigest() == build['html_sha256']
checks = []

def country_state(page, cc):
    return page.evaluate("""cc => {
      const id='imc-country-'+cc, target=document.getElementById(id);
      const top=target.getBoundingClientRect().top, bottom=document.querySelector('.imc-toolbar').getBoundingClientRect().bottom;
      const open=[...document.querySelectorAll('.imc-country[open]')].map(e=>e.id);
      const active=[...document.querySelectorAll('.imc-country-rail a[aria-current="location"]')].map(e=>e.hash);
      return {hash:location.hash,scrollY,top,toolbarBottom:bottom,open,active,
        clear:top>=bottom+8 && top<innerHeight-30,
        correct:location.hash==='#'+id && open.length===1 && open[0]===id && active.length===1 && active[0]==='#'+id};
    }""", cc)

def verify_country(page, cc, name):
    timeout = False
    try:
        page.wait_for_function("""cc => {
          const e=document.getElementById('imc-country-'+cc), bar=document.querySelector('.imc-toolbar');
          return location.hash==='#imc-country-'+cc && e.open && e.getBoundingClientRect().top>=bar.getBoundingClientRect().bottom+8 && e.getBoundingClientRect().top<innerHeight-30;
        }""", arg=cc, timeout=2000)
    except BrowserTimeout:
        timeout = True
    page.wait_for_timeout(180)
    state = country_state(page, cc)
    checks.append({'id':name, 'passed':not timeout and state['clear'] and state['correct'], 'timed_out':timeout, 'actual':state})

with sync_playwright() as runtime:
    browser = runtime.chromium.launch(channel='chrome', headless=True)
    for viewport,width,height,locales,themes in [('desktop',1440,900,['en'],['light']),('narrow',320,720,['zh'],['dark'])]:
        for locale in locales:
            for theme in themes:
                name = viewport+'-'+locale+'-'+theme
                context = module.context_for(browser,width,height,locale,theme)
                page = context.new_page()
                errors = []
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto('http://intl.test/intl.html',wait_until='domcontentloaded')
                module.settle(page,locale,theme)
                initial = page.evaluate("({historyLength:history.length,country:document.querySelector('.imc-country[open]').id,scrollY})")
                for target in ['intl-growth-inflation','intl-central-banks','intl-credit-bonds','lb-board']:
                    page.goto('http://intl.test/intl.html#'+target,wait_until='domcontentloaded')
                    page.wait_for_timeout(250)
                for cc in ['JP','KR','TW','IN','AU','GB','EZ']:
                    page.goto('http://intl.test/intl.html#imc-country-'+cc,wait_until='domcontentloaded')
                    verify_country(page,cc,'same-document-'+cc+'-'+name)
                for direction,cc in [('back','GB'),('back','AU'),('forward','GB'),('forward','EZ')]:
                    if direction=='back': page.go_back(wait_until='domcontentloaded')
                    else: page.go_forward(wait_until='domcontentloaded')
                    verify_country(page,cc,'history-'+direction+'-'+cc+'-'+name)
                page.evaluate("() => {location.hash='imc-country-JP';location.hash='imc-country-IN';location.hash='imc-country-EZ';}")
                verify_country(page,'EZ','rapid-latest-destination-'+name)
                page.evaluate('length => history.go(length-history.length)',initial['historyLength'])
                empty_timeout = False
                try: page.wait_for_function('location.hash === ""',timeout=2000)
                except BrowserTimeout: empty_timeout=True
                page.wait_for_timeout(250)
                restored = page.evaluate("({hash:location.hash,scrollY,open:[...document.querySelectorAll('.imc-country[open]')].map(e=>e.id)})")
                checks.append({'id':'empty-hash-restoration-'+name,'passed':not empty_timeout and restored['hash']=='' and abs(restored['scrollY']-initial['scrollY'])<=1 and restored['open']==[initial['country']],'actual':restored,'initial':initial})
                checks.append({'id':'no-page-exceptions-'+name,'passed':not errors,'actual':errors})
                context.close()
    browser.close()
receipt = {'recorded_at':datetime.now(timezone.utc).isoformat(),'driver_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'matrix':'representative desktop English light and 320px Chinese dark','source_commit':build['source_commit'],'html_sha256':build['html_sha256'],'checks':checks,'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),'limits':['Actual anonymous isolated browser with immutable production asset files. No manual scroll correction, source acquisition or authenticated state.','Direct country fragments, native browser Back/Forward, rapid fragment changes and empty-hash restoration are exercised.']}
p = OUT / ('country_history_'+args.label+'.json')
assert not p.exists()
p.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='checks'}))
print(json.dumps({'failed_checks':[c for c in checks if not c['passed']]}))
raise SystemExit(bool(receipt['failed']))