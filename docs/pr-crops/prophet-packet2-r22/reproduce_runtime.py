#!/usr/bin/env python3
"""F1/F2 discriminating Chromium proof, actual shared macro and bound controller.
Synthetic records; all network requests aborted; no account or production proof.
"""
from pathlib import Path
import argparse, hashlib, json, subprocess
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[3])
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--baseline', default='e59a7baeaa1ab9542f65e73eda5f43ca13c14f34')
args = parser.parse_args()
W, ROOT, BASE = args.repo.resolve(), args.out.resolve(), args.baseline
ROOT.mkdir(parents=True, exist_ok=True)
env = Environment(loader=FileSystemLoader(str(W/'templates')), autoescape=True)
env.globals['tr'] = lambda x: x
m = env.get_template('_prophet_card.html.j2').module
base = {'tk':'REVIEW_FIXTURE','href':'stock.html#REVIEW_FIXTURE','mkt':'us','verb':'wait',
        'record_only':True,'id':'review-only','record_detail':{
        'plan_id':'review-only','created_date':'2026-09-24','lifecycle_en':'Waiting',
        'lifecycle_zh':'等待','horizon_days':5,'entry':100,'invalidation':95,
        't1':110,'t2':115,'history_available':False}}
marker = '/* Packet2: enhance existing entitled row details;'
results, bindings = [], {}
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    try:
        for path in ('templates/theme.js','site/theme.js'):
            old = subprocess.check_output(['git','-C',str(W),'show',BASE+':'+path],text=True)
            new = (W/path).read_text()
            bindings[path] = {'before':hashlib.sha256(old.encode()).hexdigest(),
                              'after':hashlib.sha256(new.encode()).hexdigest()}
            for revision, full in (('r21',old),('r22',new)):
                assert full.count(marker) == 1
                controller = marker + full.split(marker,1)[1]
                cases = [('us-positive','us-standouts','stock.html#REVIEW_FIXTURE'),
                         ('pool-positive','us-candidate-pool','stock.html#REVIEW_FIXTURE'),
                         ('hk-unopted','hk-standouts','stock.html#REVIEW_FIXTURE'),
                         ('ca-unopted','canada-standouts','stock.html#REVIEW_FIXTURE'),
                         ('china-unopted','china-standouts','stock.html#REVIEW_FIXTURE'),
                         ('no-host','unopted','stock.html#REVIEW_FIXTURE'),
                         ('root-relative','us-standouts','/stock.html#REVIEW_FIXTURE'),
                         ('foreign-link','us-standouts','https://example.invalid/stock.html#REVIEW_FIXTURE'),
                         ('missing-link','us-standouts',None)]
                for label, scope, href in cases:
                    page = browser.new_page(viewport={'width':1100,'height':850})
                    errors, network = [], []
                    page.on('pageerror',lambda e:errors.append(str(e)))
                    page.route('**/*',lambda r:(network.append(r.request.url),r.abort()))
                    cx = dict(base,href=href or base['href'],mkt={'hk-standouts':'hk','canada-standouts':'canada','china-standouts':'china'}.get(scope,'us'))
                    html = '<html lang="en"><head>'+str(m.pv_css())+'<style>.l-zh{display:none}body{padding:20px}.pvcard{width:300px}</style></head><body><section id="'+scope+'">'+str(m.pv_card(cx))+'</section></body></html>'
                    page.set_content(html)
                    if href is None:
                        page.locator('.pv-record-link').evaluate('(e)=>e.remove()')
                    page.evaluate('''()=>{const d=document.querySelector('.pv-record-detail');
                      window.originalNodes=Array.from(d.children).filter(n=>n.localName!=='summary');
                      window.defaultPrevented=null;}''')
                    page.add_script_tag(content=controller)
                    page.evaluate('''()=>document.addEventListener('click',e=>{window.defaultPrevented=e.defaultPrevented})''')
                    trigger = page.locator('.pv-record-detail>summary')
                    trigger.click()
                    page.wait_for_timeout(30)
                    got = page.evaluate('''()=>({nativeOpen:document.querySelector('.pv-record-detail').open,
                      modalOpen:!!document.querySelector('.pv-setup-dialog[open]'),
                      allocated:document.querySelectorAll('.pv-setup-dialog').length,
                      prevented:window.defaultPrevented,
                      nativeBodyRemains:window.originalNodes.every(n=>n.parentElement===document.querySelector('.pv-record-detail'))})''')
                    enhanced = label.endswith('positive') or (revision=='r21' and label.endswith('unopted')) or (revision=='r21' and label=='no-host')
                    if enhanced:
                        assert got['modalOpen'] and not got['nativeOpen'] and got['prevented'],(revision,label,got)
                        page.keyboard.press('Escape')
                        page.wait_for_timeout(20)
                        assert trigger.evaluate('(e)=>e===document.activeElement')
                        assert page.evaluate("window.originalNodes.every(n=>n.parentElement===document.querySelector('.pv-record-detail'))")
                    elif revision == 'r22':
                        assert got == {'nativeOpen':True,'modalOpen':False,'allocated':0,'prevented':False,'nativeBodyRemains':True},(path,label,got)
                    else:
                        assert not got['nativeOpen'] and not got['modalOpen'] and got['prevented'] and got['allocated']==1,(path,label,got)
                    assert not errors and not network,(errors,network)
                    results.append({'path':path,'revision':revision,'case':label,'result':got,'errors':errors,
                                    'external_requests':len(network),'expected_behavior_verified':True})
                    page.close()
    finally:
        version=browser.version
        browser.close()
report={'proof_class':'actual_shared_macro_controlled_chromium_no_network_or_account',
        'base':BASE,'bindings':bindings,'browser':version,'cases':results,
        'baseline_defects_reproduced':True,'r22_f1_f2_pass':True}
(ROOT/'scope-fallback-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'cases':len(results),'baseline':18,'repaired':18,'pass':True,'bindings':bindings},indent=2))
