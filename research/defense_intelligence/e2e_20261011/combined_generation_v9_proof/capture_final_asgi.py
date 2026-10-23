"""Run the incumbent 24-cell capture against the exact ASGI stage owner.

Caller must launch the loopback source router with the same sealed stage.
This deliberately avoids a static server's API-to-file fallback.
"""
from pathlib import Path
import argparse,sys,json,hashlib
ap=argparse.ArgumentParser();ap.add_argument('stage');ap.add_argument('url');ap.add_argument('server_receipt');ap.add_argument('output_root');a=ap.parse_args()
s=Path(a.stage);o=Path(a.output_root);server=Path(a.server_receipt)
from verify_stage import verify_stage
verify_stage(s)
assert a.url.startswith(('http://127.0.0.1:','https://localhost:')),'Loopback source-stage only'
assert not o.exists(),'Evidence is immutable'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=json.loads((s/'INPUT_RECEIPT.json').read_text());runtime=json.loads(server.read_text())
def verify_router_data():
 for path, expected in runtime.get('api_data_inputs', {}).items():
  actual = hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None
  assert actual == expected, 'Router data changed during qualification: ' + path
 assert runtime.get('api_data_inputs'), 'Use source-data-bound serve_final_asgi.py'
 assert sorted(str(path) for path in Path(runtime['canonical_input_directory']).rglob('*') if path.is_file())==runtime['canonical_input_inventory'], 'Canonical input inventory changed'
 for path, expected in runtime.get('api_source_modules', {}).items():
  assert h(Path(path)) == expected, 'Router source dependency changed: ' + path
verify_router_data()

assert inputs['html_sha256']==h(s/'government_revenue.html')
assert runtime['stage_receipt_sha256']==h(s/'INPUT_RECEIPT.json')
assert runtime['denial_before_finance_validator'] is True
w=Path(runtime['source_root']);assert runtime['api_source_sha256']==h(w/'app/government_revenue.py')
for rel,expected in inputs['material_source_hashes'].items():assert h(w/rel)==expected,rel
sys.path.insert(0,str(w));from scripts.capture_page_evidence import main, playwright_page_driver
o.mkdir(parents=True);d=o/'mockups/evidence/defense-final-local';d.mkdir(parents=True)
readiness=[];final_cell_geometry=[]
def ready_driver_factory(**kwargs):
    # Keep the incumbent capture/manifest/interaction implementation. Add only
    # a readiness wait to its page navigation; no DOM, payload, or screenshot
    # is rewritten and no response is intercepted.
    driver=playwright_page_driver(**kwargs)
    original_context=driver._browser.new_context
    def new_context(*args,**kw):
        context=original_context(*args,**kw)
        original_page=context.new_page
        def new_page(*page_args,**page_kw):
            page=original_page(*page_args,**page_kw)
            original_goto=page.goto
            def goto(*goto_args,**goto_kw):
                response=original_goto(*goto_args,**goto_kw)
                page.wait_for_function("window.__govrevFirstInvestor&&window.__govrevFirstInvestor.pageState==='ready'&&document.querySelector('#defenseInvestor[data-state=ready]')&&document.querySelector('#programThemeContext[data-state=ready]')",timeout=goto_kw.get('timeout',30000))
                row=page.evaluate("()=>({viewport:{width:innerWidth,height:innerHeight},theme:document.documentElement.getAttribute('data-theme'),lang:document.documentElement.getAttribute('data-lang'),finance:document.querySelector('#defenseInvestor').getAttribute('data-state'),theme_context:document.querySelector('#programThemeContext').getAttribute('data-state'),page_controller:window.__govrevFirstInvestor.pageState,failed_modules:window.__govrevFirstInvestor.failedModules.slice(),theme_cards:document.querySelectorAll('.gr-theme-item').length})")
                assert not row['failed_modules'],row
                readiness.append(row)
                return response
            page.goto=goto
            return page
        context.new_page=new_page
        return context
    driver._browser.new_context=new_context
    original_capture=driver.capture
    def capture(*capture_args,**capture_kw):
        observation=original_capture(*capture_args,**capture_kw)
        cell=capture_kw['cell']
        final_cell_geometry.append({'cell_id':cell.cell_id,'viewport':cell.viewport,'theme':cell.theme,'locale':cell.locale,'force_state':cell.force_state.name if cell.force_state else None,'loaded':observation.loaded,'horizontal_overflow':observation.observed.get('horizontal_overflow'),'document_height_px':observation.observed.get('document_height_px')})
        return observation
    driver.capture=capture
    return driver
rc=main(['--base-url',a.url,'--registry',str(w/'data/product_experience/page_registry.json'),'--routes','/government_revenue.html','--output-dir',str(d),'--manifest',str(d/'manifest.json'),'--smells',str(d/'smells.json'),'--viewports','desktop,tablet,mobile','--locales','en,zh','--themes','dark,light','--max-pages','1','--delay-ms','0','--force-state','investor-focus:focus([data-investor-evidence="interpretation"] summary)'],driver_factory=ready_driver_factory)
assert rc==0,rc
manifest=json.loads((d/'manifest.json').read_text())
assert len(manifest['pages'])==1
page_record=manifest['pages'][0]
assert len(page_record['states'])==24 and len(readiness)==24,'Incomplete 24-cell matrix'
assert all(cell.get('captured') for cell in page_record['states']),'Failed capture cell'
assert all(not cell.get('force_state') or cell.get('applied_force_state')==cell['force_state'] for cell in page_record['states']),'Interaction state did not apply'
assert all(cell.get('applied_theme')==cell['theme'] and cell.get('applied_locale')==cell['locale'] for cell in page_record['states']),'Theme/locale mismatch'
assert not page_record['failed_responses'] and not page_record['console_errors'],'Capture carries runtime errors'
assert all(row['theme_cards']==6 for row in readiness),'Incomplete six-theme composition'
assert len(final_cell_geometry)==24 and all(row['loaded'] and row['horizontal_overflow'] is False for row in final_cell_geometry),'Incomplete per-cell geometry or horizontal overflow'
(d/'CELL_GEOMETRY.json').write_text(json.dumps(final_cell_geometry,ensure_ascii=False,indent=2))
(d/'READINESS.json').write_text(json.dumps(readiness,ensure_ascii=False,indent=2))
assert runtime['api_source_sha256']==h(w/'app/government_revenue.py'),'API changed during capture'
for rel,expected in inputs['material_source_hashes'].items():assert h(w/rel)==expected,rel
verify_router_data()
verify_stage(s)
assert h(s/'INPUT_RECEIPT.json')==runtime['stage_receipt_sha256'], 'Stage receipt changed during capture'
(d/'INPUT_RECEIPT.json').write_text(json.dumps(inputs,ensure_ascii=False,indent=2))
(d/'SERVER_RECEIPT.json').write_bytes(server.read_bytes())
(d/'EVIDENCE.yml').write_text('schema: mastermind.page_evidence_receipt.v1\nchanged_paths:\n'+''.join('  - '+p+'\n' for p in inputs['material_source_hashes'])+'manifest: mockups/evidence/defense-final-local/manifest.json\n')
(d/'QUALIFICATION_SCOPE.json').write_text(json.dumps({'scope':'24-cell incumbent capture against actual source ASGI and explicit local test-principal; no production entitlement/customer acceptance','stage_receipt_sha256':h(s/'INPUT_RECEIPT.json'),'server_receipt_sha256':h(server),'manifest_sha256':h(d/'manifest.json'),'source_hashes_checked_before_and_after':True},indent=2))
print('Source-bound ASGI matrix saved',d)
