'use strict';
const {test,before,after}=require('node:test');
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..');
const fixtures=JSON.parse(execFileSync(process.env.INTL_TEST_PYTHON||'python3',['-c',`
import importlib.util,json
from pathlib import Path

def module(name,file):
 s=importlib.util.spec_from_file_location(name,Path('tests')/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
owner=module('generation_actual_producer','test_intl_workspace_overview.py')
render=module('generation_actual_renderer','test_intl_inspector_mount.py')
cat=json.loads(Path('config/intl_library_catalogue.json').read_text())
out={}
for state in ['local_only','unknown','denied','one_horizon']:
 frame,inputs,ref=owner._production_fixture()
 if state=='unknown':inputs['disclosure_decisions']=[]
 elif state=='denied':
  for item in inputs['disclosure_decisions']:item['metadata']='denied'
 elif state=='one_horizon':inputs['disclosure_decisions']=[x for x in inputs['disclosure_decisions'] if x['horizon']=='1m']
 ws=owner._production_workspace(frame,inputs)
 html,stocks=render.render_international_pages(render.ActualShell(),{'intl_workspace':ws},catalogue=cat)
 out[state]={'html':html,'source':ref,'generation':ws['config']['source_reference'],'stocks':stocks}
print(json.dumps(out))
`],{cwd:root,encoding:'utf8',maxBuffer:8*1024*1024}));
let browser;
before(async()=>{browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL?{channel:process.env.PLAYWRIGHT_CHROMIUM_CHANNEL}:{})});});
after(async()=>{await browser.close();});
async function fixture(state,run){const p=await browser.newPage();p.setDefaultTimeout(3000);try{await p.route('http://generation-integration.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><html lang="en"><meta charset="utf-8"><style>[hidden]{display:none!important}</style><body>'+fixtures[state].html+'</body></html>'}));await p.goto('http://generation-integration.test/intl.html');for(const a of ['intl_workspace_state.js','intl_library_search.js','intl_workspace.js','intl_workspace_entry.js'])await p.addScriptTag({content:fs.readFileSync(path.join(root,'templates',a),'utf8')});await p.evaluate(()=>{window.root=document.querySelector('[data-im-workspace]');window.h=IntlWorkspace.mountIntlWorkspace(root,JSON.parse(root.querySelector('[data-im-config]').textContent));});await run(p);}finally{await p.close();}}
const overview='[data-im-panel][data-view="overview"]:not([hidden])';
const compare='[data-im-compare-panel]:not([hidden])';
test('actual partial-grant producer mounts Overview, Compare, Inspector and null-source Library',async()=>fixture('local_only',async p=>{
 assert.equal(await p.locator('[data-im-workspace]').getAttribute('data-im-enhanced'),'true');assert.equal(await p.locator(overview).getAttribute('data-source'),'');
 await p.evaluate(()=>h.dispatch({type:'set_basis',currency_basis:'local'}));assert.equal(await p.locator(overview).getAttribute('data-source'),fixtures.local_only.source);
 const before=await p.locator(overview).textContent();assert.match(before,/Nikkei 225/);
 assert.equal((await p.evaluate(()=>h.openInspector({market_id:'JP',expected_source:h.getState().source_reference}))).ok,true);assert.equal(await p.locator('dialog article').getAttribute('data-source'),fixtures.local_only.source);await p.evaluate(()=>h.closeInspector());
 await p.evaluate(()=>{h.dispatch({type:'set_view',view:'compare'});h.dispatch({type:'pin',market_id:'JP'});h.dispatch({type:'pin',market_id:'GB'});});assert.equal(await p.locator(compare+' [data-im-compare-slot]:not([hidden])').count(),2);assert.equal(await p.locator(compare).getAttribute('data-im-compare-state'),'incomparable');
 await p.evaluate(()=>h.dispatch({type:'set_basis',currency_basis:'usd_unhedged'}));assert.equal(await p.locator(compare).getAttribute('data-source'),'');assert.deepEqual(await p.evaluate(()=>h.getState().compare_markets),['JP','GB']);
 await p.evaluate(()=>h.dispatch({type:'set_view',view:'library'}));assert.equal(await p.locator('[data-im-library-static]').isVisible(),true);assert.equal(await p.locator('[data-im-library-static]').getAttribute('data-source'),'');assert.equal(await p.locator('[data-im-library-tool]').count(),18);assert.equal(await p.evaluate(()=>document.body.innerText.includes(h.getState().source_reference)),false);assert.equal(await p.evaluate(()=>location.search.includes('generation')||location.search.includes('sha256')),false);assert.equal(fixtures.local_only.stocks,'Incumbent stocks');
}));
for(const state of ['unknown','denied'])test('actual '+state+' keeps unavailable values and exact NULL Inspector semantics',async()=>fixture(state,async p=>{
 await p.evaluate(()=>h.dispatch({type:'set_basis',currency_basis:'local'}));assert.equal(await p.locator(overview).getAttribute('data-source'),'');assert.doesNotMatch(await p.locator(overview).textContent(), /[+-]?\d+\.\d{2}%/);
 const result=await p.evaluate(()=>h.openInspector({market_id:'JP',expected_source:h.getState().source_reference}));assert.equal(result.ok,state==='unknown');if(state==='unknown'){assert.equal(await p.locator('dialog article').getAttribute('data-source'),null);await p.evaluate(()=>h.closeInspector());}else assert.equal(await p.locator('[data-im-inspector-payload][data-market-id="JP"][data-basis="local"]').count(),0);
 await p.evaluate(()=>{h.dispatch({type:'set_view',view:'compare'});h.dispatch({type:'pin',market_id:'JP'});});assert.equal(await p.locator(compare+' [data-im-compare-slot]:not([hidden])').count(),1);assert.doesNotMatch(await p.locator(compare).textContent(), /[+-]?\d+\.\d{2}(?:%| pp)/);
}));
test('actual one-horizon permission never supplies source to another horizon',async()=>fixture('one_horizon',async p=>{
 await p.evaluate(()=>h.dispatch({type:'set_basis',currency_basis:'local'}));assert.equal(await p.locator(overview).getAttribute('data-source'),fixtures.one_horizon.source);await p.evaluate(()=>h.dispatch({type:'set_horizon',horizon:'3m'}));assert.equal(await p.locator(overview).getAttribute('data-source'),'');assert.equal((await p.evaluate(()=>h.openInspector({market_id:'JP',expected_source:h.getState().source_reference}))).ok,true);assert.equal(await p.locator('dialog article').getAttribute('data-source'),null);
}));
test('actual producer v2 fallback stays native and readable without controller',async()=>{const p=await browser.newPage();try{await p.setContent(fixtures.local_only.html);assert.equal(await p.locator('[data-im-workspace]').getAttribute('data-im-enhanced'),null);assert.equal(await p.locator('[data-im-panel][data-view="overview"]:visible').count(),10);assert.equal(await p.locator('[data-im-controls]').evaluate(n=>n.disabled),true);}finally{await p.close();}});
