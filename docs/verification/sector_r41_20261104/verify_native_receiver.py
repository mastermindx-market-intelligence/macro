#!/usr/bin/env python3
"""Component integration with the exact existing producer/verifier; no route worker.

Immutable dependency snapshots stay in this workspace's ignored fixture directory.
No producer model run, network endpoint, shared branch write or real user data.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, os, runpy, subprocess, sys
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
UPSTREAM = 'a97b8f50cdf3a16ad8cba3a52edf76fc9ef30f14'
parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=True)
snapshot = ROOT / '.pytest_cache/r41-native-dependencies'
snapshot.mkdir(parents=True, exist_ok=True)
paths = ['scripts/__init__.py', 'scripts/_cycles_payload.py', 'engine/__init__.py',
         'engine/sector_generation_guard.py', 'templates/sector_cycles.js']
digests = {}
for path in paths:
    data = subprocess.check_output(['git', '-C', str(ROOT), 'show', UPSTREAM + ':' + path])
    dest = snapshot / path; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(data)
    digests[path] = hashlib.sha256(data).hexdigest()
prelude = runpy.run_path(str(ROOT / 'tests/test_sector_dossier_cycle_js.py'))['PRELUDE']
fixture = json.loads(subprocess.check_output(['node', '-e', prelude + ';console.log(JSON.stringify(fixture()));',
                                            str(ROOT / 'templates/sector_dossier_cycle.js')], text=True))
fixture['meta'].update(today=2026.83, xDomain=[2024, 2026.9], xDomainDefault=[2024, 2026.9],
                       window_years=3, default_window_years=3, rebaseDate='2024-01-01')
fixture['phases'] = {'Downturn': {'label': 'Downturn', 'short': 'Rolling over', 'hue': '#7aa7e0'},
                     'Expansion': {'label': 'Expansion', 'short': 'Trending', 'hue': '#45b873'}}
fixture['sectors'][0].update(turns=[], group='Cyclical', short='Energy', accent='#7aa7e0')
basket = copy.deepcopy(fixture['sectors'][0]); basket.update(id='energy-basket',kind='basket',name='Energy basket')
basket['series_provenance'].update(membership='current_membership',point_in_time=False)
fixture['baskets']=[basket]
code = "from scripts._cycles_payload import publication_scripts;import sys,json;print(json.dumps(publication_scripts(json.load(sys.stdin),{},{})))"
env = dict(os.environ, PYTHONPATH=str(snapshot), PYTHONDONTWRITEBYTECODE='1')
parts = json.loads(subprocess.check_output([sys.executable, '-c', code], input=json.dumps(fixture),
                                          text=True, env=env, cwd=snapshot))
receiver = (snapshot / 'templates/sector_cycles.js').read_text()
component = (ROOT / 'templates/sector_dossier_cycle.js').read_text()
chart = subprocess.check_output(['git', '-C', str(ROOT), 'show', UPSTREAM + ':site/mm_charts.js'], text=True)
results = []
try:
    with sync_playwright() as tool:
        browser = tool.chromium.launch(headless=True, chromium_sandbox=True)
        try:
            for scenario in ['verified', 'mixed_sector_series', 'mixed_basket_series', 'tampered_core']:
                page = browser.new_page(viewport={'width': 768, 'height': 1000}, reduced_motion='reduce')
                errors = []; page.on('pageerror', lambda error: errors.append(str(error)))
                def route(request):
                    if request.request.url == 'http://127.0.0.1/r41-consumer':
                        request.fulfill(content_type='text/html', body='<!doctype html><html data-theme="dark" data-lang="en"><head><meta charset="utf-8"></head><body style="background:var(--bg);color:var(--text);margin:24px"><p>R4.1 NATIVE CONTRACT FIXTURE · NOT LIVE</p><div class="si-view" hidden></div><main id="dossier"></main></body></html>')
                    else:
                        url = urlsplit(request.request.url); name = url.path.lstrip('/')
                        if url.hostname != '127.0.0.1': request.abort(); return
                        allowed = name == 'product-nav-icons.css' or (name.startswith('fonts/Inter-') and name.endswith('.woff2'))
                        source = ROOT / ('templates' if name == 'product-nav-icons.css' else 'site') / name
                        if allowed and source.is_file():
                            request.fulfill(body=source.read_bytes(), content_type='text/css' if name.endswith('.css') else 'font/woff2')
                        else: request.abort()
                page.route('**/*', route); page.goto('http://127.0.0.1/r41-consumer')
                page.add_style_tag(content=(ROOT/'templates/theme.css').read_text())
                page.add_style_tag(content=(ROOT/'templates/sector_dossier_cycle.css').read_text())
                page.add_script_tag(content=chart); page.add_script_tag(content=component)
                page.add_script_tag(content=parts['core']); page.add_script_tag(content=parts['series'])
                page.evaluate("window.SC_LAZY_EXTRAS=true;window.SectorCyclesHost={};window.actionCalls=[];")
                if scenario.startswith('mixed_'):
                    page.evaluate("SECTOR_CYCLES_SERIES_PUBLICATION.publication_id='cycp1-'+'f'.repeat(64)")
                if scenario == 'tampered_core':
                    page.evaluate("SECTOR_CYCLES_PUBLICATION.payload_json+=' '")
                page.add_script_tag(content=receiver)
                page.evaluate('''(scenario)=>{
                  window.hostOptions={accessState:'allowed',dataState:'ready',family:'sectors',id:'xle',locale:'en',
                    expectedAsOf:'2026-10-30',expectedPublicationId:SECTOR_CYCLES_PUBLICATION.id,
                    expectedSpine:SECTOR_CYCLES_PUBLICATION.sector_spine,
                    onMembers:selection=>actionCalls.push(selection),
                    renderChart:(root,ctx)=>(window.testNativeChart=MMChart.create(root,{xDomain:[2026,2026.3],yDomain:[0,100],yTicks:[{v:0,label:'0'},{v:50,label:'50'},{v:100,label:'100'}],zoom:true,
                      animate:false,series:[{id:ctx.record.id,color:'var(--link)',hist:ctx.record.osc.map(p=>({x:p.x,y:p.v})),proj:[],markers:[]}]}))};
                  if(scenario==='mixed_basket_series'){hostOptions.family='baskets';hostOptions.id='energy-basket';delete hostOptions.expectedSpine;}
                  window.adapter=SectorDossierCycle.mountFromNative(document.querySelector('#dossier'),window,hostOptions);
                }''',scenario)
                page.wait_for_function("SectorCyclesEvidence().status!=='pending'")
                if scenario == 'tampered_core':
                    page.wait_for_function("document.querySelector('.sdc').dataset.state==='unavailable'")
                    assert '+6.1%' not in page.locator('#dossier').inner_text()
                    assert page.locator('.sdc-chart svg').count() == 0
                else:
                    assert page.evaluate('SectorCyclesEvidence().status') == 'verified'
                    page.evaluate('SectorCyclesHydrateSeries()')
                    page.wait_for_function("SectorCyclesEvidence().parts.series!=='pending'")
                    assert page.locator('.sdc').get_attribute('data-state') == 'ready'
                    if scenario.startswith('mixed_'):
                        assert page.evaluate('SectorCyclesEvidence().parts.series') == 'incompatible_publication'
                        if scenario=='mixed_sector_series': page.locator('.sdc-chart svg').wait_for()
                        else: assert page.locator('.sdc-chart svg').count() == 0
                        assert '+6.1%' in page.locator('#dossier').inner_text()
                    else:
                        page.locator('.sdc-chart svg').wait_for()
                        page.locator('.sdc-values > summary').click()
                        assert page.locator('.sdc-values tbody tr').count() == 2
                        page.locator('.sdc-sources > summary').click()
                        assert page.evaluate('SECTOR_CYCLES_PUBLICATION.id') in page.locator('.sdc-sources').inner_text()
                        page.locator('.sdc-action').first.click()
                        assert page.evaluate('actionCalls[0].publicationId===SECTOR_CYCLES_PUBLICATION.id')
                        assert page.evaluate('actionCalls[0].actionKey==="members" && actionCalls[0].invoker===document.activeElement')
                        page.evaluate('testNativeChart.setView([2026.05,2026.2],false);document.dispatchEvent(new CustomEvent("sc:extras-ready"))')
                        assert page.evaluate('testNativeChart.getView()')==[2026.05,2026.2], 'native chart zoom must survive annotation hydration'
                        assert page.locator('.sdc-values').get_attribute('open') is not None,'annotation hydration must not close Exact values'
                        assert page.locator('.sdc-sources').get_attribute('open') is not None,'annotation hydration must not close Sources'
                        assert page.evaluate('document.activeElement.classList.contains("sdc-action")'),'annotation hydration must preserve keyboard focus'
                        page.screenshot(path=str(args.out/'verified-native-consumer.png'), full_page=True)
                        # Active owner rejects replacement without an event. Clicking a
                        # previously-rendered action must still detect that supersession.
                        page.evaluate('window.originalCore=SECTOR_CYCLES;window.SECTOR_CYCLES=structuredClone(SECTOR_CYCLES)')
                        page.locator('.sdc-action').first.click()
                        assert page.locator('.sdc').get_attribute('data-state') == 'incompatible_generation'
                        assert page.evaluate('actionCalls.length') == 1
                        assert page.evaluate('document.activeElement===document.querySelector(".sdc-state .sdc-title")'), 'supersession must keep focus on the replacement state, not body'
                        page.evaluate('window.SECTOR_CYCLES=originalCore;adapter.update({...hostOptions,expectedPublicationId:"cycp1-"+"e".repeat(64)})')
                        assert page.locator('.sdc').get_attribute('data-state') == 'incompatible_generation'
                        page.evaluate('adapter.update(hostOptions)')
                        assert page.locator('.sdc').get_attribute('data-state') == 'ready'
                        # Refreshing a component must not steal focus from an unrelated control.
                        page.evaluate('''()=>{const outside=document.createElement('button');outside.id='outside-dossier';outside.textContent='Other task';document.body.append(outside);outside.focus();document.dispatchEvent(new CustomEvent('sc:extras-ready'));}''')
                        assert page.evaluate('document.activeElement.id') == 'outside-dossier'
                        page.locator('.sdc-action').first.focus()
                        page.evaluate('adapter.update({...hostOptions,accessState:"forbidden"})')
                        assert page.locator('.sdc').get_attribute('data-state') == 'denied'
                        assert '+6.1%' not in page.locator('#dossier').inner_text()
                        assert page.evaluate('document.activeElement===document.querySelector(".sdc-state .sdc-title")'), 'denial must retain focus on its explanation'
                        page.evaluate('adapter.update(hostOptions)')
                        assert page.evaluate('document.activeElement===document.querySelector(".sdc-heading .sdc-title")'), 'recovery must focus the restored subject'
                        # A malformed transport facade must not keep a stale action live;
                        # actual publication hashing still belongs to the native verifier.
                        page.evaluate('''()=>{adapter.destroy();window.facadeBad=false;window.facade={get SECTOR_CYCLES(){return window.SECTOR_CYCLES},SectorCyclesEvidence(){const r=window.SectorCyclesEvidence();return facadeBad?{...r,parts:{...r.parts,core:'pending'}}:r;}};adapter=SectorDossierCycle.mountFromNative(document.querySelector('#dossier'),facade,hostOptions);facadeBad=true;}''')
                        before = page.evaluate('actionCalls.length')
                        page.locator('.sdc-action').first.click()
                        assert page.evaluate('actionCalls.length') == before, 'action must revalidate the core-part receipt'
                        assert page.locator('.sdc').get_attribute('data-state') == 'unavailable'
                page.evaluate('adapter.destroy();document.dispatchEvent(new CustomEvent("sc:series-ready"))')
                assert page.locator('#dossier').inner_html() == ''
                assert not errors, errors
                results.append({'scenario':scenario,'status':'passed','receipt':page.evaluate('SectorCyclesEvidence()')})
                page.close()
        finally: browser.close()
    result={'status':'passed','source_ref':UPSTREAM,'dependency_sha256':digests,'scenarios':results,
            'scope':'Dossier component consumes real producer/verifier; not full native route or production proof'}
    (args.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':'passed','scenarios':len(results),'upstream':UPSTREAM}))
except Exception as error:
    (args.out/'result.json').write_text(json.dumps({'status':'failed','completed':results,'error':str(error)},indent=2)+'\n')
    raise
