'use strict';
const {test,before,after}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require('playwright');
const config={markets:['JP','KR','TW','IN','AU','GB','EZ'],horizons:['1m','3m'],bases:['local','usd_unhedged'],default_horizon:'1m',default_basis:'usd_unhedged',source_reference:'synthetic:v1',anchor_ids:[],library_group_ids:[]};
const source=n=>fs.readFileSync(path.join(__dirname,'../templates',n),'utf8');
let browser;
before(async()=>{browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL?{channel:process.env.PLAYWRIGHT_CHROMIUM_CHANNEL}:{})});});
after(async()=>{await browser.close();});
function panel(basis='usd_unhedged',ref='synthetic:v1'){
  const cohorts=[{id:'c0',order_slots:[3,1,0,2]},{id:'c1',order_slots:[4]}];
  return `<section data-im-panel data-im-compare-panel data-view="compare" data-horizon="1m" data-basis="${basis}" data-return-basis="price" data-source="${ref}">
  <p data-im-compare-status><span>Native facts</span></p><div data-im-compare-controls hidden><select data-im-compare-pin><option value="" data-im-label-en="Choose" data-im-label-zh="选择">Choose</option>${config.markets.slice(0,6).map((m,i)=>`<option value="${i}" data-im-label-en="${m}" data-im-label-zh="市场${i}">${m}</option>`).join('')}</select></div>
  <table><tbody data-im-compare-rows>${config.markets.map((m,i)=>`<tr data-im-compare-slot="${i}"${i<6?` data-im-compare-cohort-id="${i<4?'c0':i===4?'c1':''}"`:''}><th>${i===6?'Unavailable':m}<button data-im-compare-remove="${i}" hidden>Remove</button></th><td><span data-im-compare-value>${['10.00','10.00','2.00','11.00','20.00','Unavailable','Withheld'][i]}</span></td></tr>`).join('')}</tbody></table>
  <details><summary>Windows</summary>${cohorts.map(c=>`<section data-im-compare-cohort="${c.id}">${c.id}</section>`).join('')}</details>
  <script type="application/json" data-im-compare-catalogue>${JSON.stringify({schema:'intl-compare-catalogue.v1',slot_order:[0,1,2,3,4,5,6],cohorts})}</script></section>`;
}
function markup(){return `<section data-im-workspace data-im-mode="macro"><h1 data-im-heading>International</h1><p data-im-issues></p><p data-im-unavailable hidden>Unavailable</p><button data-im-action="set_view" data-im-view="compare">Compare</button><article data-im-panel data-view="overview" data-horizon="1m" data-basis="usd_unhedged" data-source="synthetic:v1">Overview</article>${panel()}${panel('local')}</section>`;}
async function fixture(run,{mutate=null,two=false}={}){
 const page=await browser.newPage();page.setDefaultTimeout(3000);
 try{
  await page.route('http://compare.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><html lang="en"><meta charset="utf-8"><style>[hidden]{display:none!important}</style><body>'+markup()+(two?markup():'')+'</body></html>'}));
  await page.goto('http://compare.test/intl.html');
  if(mutate)await page.evaluate(mutate);
  await page.addScriptTag({content:source('intl_workspace_state.js')});await page.addScriptTag({content:source('intl_workspace.js')});
  await page.evaluate(c=>{window.roots=[...document.querySelectorAll('[data-im-workspace]')];window.h=IntlWorkspace.mountIntlWorkspace(roots[0],c);if(roots[1])window.h2=IntlWorkspace.mountIntlWorkspace(roots[1],c);h.dispatch({type:'set_view',view:'compare'});},config);
  await run(page);
 }finally{await page.close();}
}
const active='[data-im-compare-panel]:not([hidden])';
async function rows(page){return page.locator('[data-im-workspace]').first().locator(active+' [data-im-compare-slot]:not([hidden])').evaluateAll(ns=>ns.map(n=>Number(n.dataset.imCompareSlot)));}
async function pin(page,market){return page.evaluate(m=>h.dispatch({type:'pin',market_id:m}),market);}

test('zero/one/two/four/fifth pins use server order, never rounded displayed values',async()=>fixture(async p=>{
 assert.deepEqual(await rows(p),[0,1,2,3,4,5,6]);
 await pin(p,'JP');assert.deepEqual(await rows(p),[0]);
 await pin(p,'KR');assert.deepEqual(await rows(p),[1,0]);
 assert.equal(await p.locator(active).getAttribute('data-im-compare-state'),'comparable');
 await pin(p,'TW');await pin(p,'IN');assert.deepEqual(await rows(p),[3,1,0,2]);
 assert.equal((await pin(p,'AU')).ok,false);assert.deepEqual(await rows(p),[3,1,0,2]);
 assert.match(await p.locator('[data-im-issues]').textContent(),/Pin limit/);
 assert.deepEqual(await p.evaluate(()=>h.getState().compare_markets),['JP','KR','TW','IN']);
}));
test('unequal windows and denied/unknown selections remain present without a qualified subset',async()=>fixture(async p=>{
 await pin(p,'JP');await pin(p,'AU');assert.deepEqual(await rows(p),[0,4]);
 assert.equal(await p.locator(active).getAttribute('data-im-compare-reason'),'unequal_windows');
 await pin(p,'EZ');await pin(p,'GB');assert.deepEqual(await rows(p),[0,4,6,5]);
 assert.equal(await p.locator(active).getAttribute('data-im-compare-reason'),'selection_unqualified');
}));
test('native picker and remove use the reducer and language/resize add no history',async()=>fixture(async p=>{
 await p.locator(active+' [data-im-compare-pin]').selectOption('0');
 assert.deepEqual(await rows(p),[0]);
 assert.equal(await p.locator(active+' [data-im-compare-pin]').inputValue(),'');
 assert.equal(await p.locator(active+' option[value="0"]').isDisabled(),true);
 const before=await p.evaluate(()=>({state:h.getState(),history:history.length,url:location.href}));
 await p.evaluate(()=>document.documentElement.lang='zh');await p.setViewportSize({width:390,height:844});
 await p.waitForFunction(()=>document.querySelector('[data-im-compare-panel]:not([hidden]) option[value="0"]').textContent==='市场0');
 assert.deepEqual(await p.evaluate(()=>({state:h.getState(),history:history.length,url:location.href})),before);
 await p.locator(active+' [data-im-compare-remove="0"]').click();assert.deepEqual(await rows(p),[0,1,2,3,4,5,6]);
}));
for(const [name,mutation] of [
 ['duplicate slot',()=>document.querySelector('[data-im-compare-slot="1"]').dataset.imCompareSlot='0'],
 ['wrong cohort',()=>document.querySelector('[data-im-compare-slot="1"]').dataset.imCompareCohortId='c1'],
 ['duplicate group slot',()=>{const n=document.querySelector('[data-im-compare-catalogue]'),v=JSON.parse(n.textContent);v.cohorts[0].order_slots.push(1);n.textContent=JSON.stringify(v);}],
 ['financial JSON',()=>{const n=document.querySelector('[data-im-compare-catalogue]'),v=JSON.parse(n.textContent);v.values=[12];n.textContent=JSON.stringify(v);}],
 ['missing return basis',()=>document.querySelector('[data-im-compare-panel]').removeAttribute('data-return-basis')],
 ['denied picker option',()=>{const n=document.querySelector('[data-im-compare-pin]');n.insertAdjacentHTML('beforeend','<option value="6">Leaked</option>');}]
])test('malformed '+name+' refuses the panel and keeps pins',async()=>fixture(async p=>{
 await pin(p,'JP');assert.deepEqual(await p.evaluate(()=>h.getState().compare_markets),['JP']);
 assert.equal(await p.locator(active).count(),0);assert.equal(await p.locator('[data-im-unavailable]').isVisible(),true);
},{mutate:mutation}));

test('failed history restores original rows, children, state and listeners; destroy restores native order',async()=>fixture(async p=>{
 await p.evaluate(()=>{window.row=document.querySelector('[data-im-compare-slot="0"]');window.hits=0;row.addEventListener('proof',()=>hits++);window.original=[...row.parentNode.children];window.nativeStatus=document.querySelector('[data-im-compare-status]').innerHTML;});
 await pin(p,'JP');
 const out=await p.evaluate(()=>{
  const state=h.getState(),before=document.querySelector('[data-im-compare-panel]').outerHTML,push=history.pushState;
  history.pushState=()=>{throw Error('history failure')};let result;try{result=h.dispatch({type:'pin',market_id:'KR'})}finally{history.pushState=push}
  row.dispatchEvent(new Event('proof'));return {ok:result.ok,same:row===document.querySelector('[data-im-compare-slot="0"]'),hits,state,after:h.getState(),sameDOM:before===document.querySelector('[data-im-compare-panel]').outerHTML};
 });assert.equal(out.ok,false);assert.equal(out.sameDOM,true);assert.equal(out.same,true);assert.equal(out.hits,1);assert.deepEqual(out.state,out.after);
 await pin(p,'KR');await p.evaluate(()=>h.destroy());
 assert.equal(await p.evaluate(()=>original.every((n,i)=>n===row.parentNode.children[i])),true);
 assert.equal(await p.locator('[data-im-compare-controls]').first().isHidden(),true);
 assert.equal(await p.locator('[data-im-compare-status]').first().innerHTML(),'<span>Native facts</span>');
}));
test('two roots remain isolated and popstate restores pins without another history entry',async()=>fixture(async p=>{
 await pin(p,'JP');await pin(p,'KR');const historyLength=await p.evaluate(()=>history.length);
 assert.deepEqual(await p.evaluate(()=>h2.getState().compare_markets),[]);
 await p.goBack();assert.deepEqual(await rows(p),[0]);
 // Each root independently follows the same page URL on popstate.
 assert.deepEqual(await p.evaluate(()=>h2.getState().compare_markets),['JP']);
 assert.equal(await p.evaluate(()=>history.length),historyLength);
},{two:true}));
test('source replacement cannot borrow old panel; local context preserves selections',async()=>fixture(async p=>{
 await pin(p,'JP');await pin(p,'KR');await p.evaluate(()=>h.dispatch({type:'set_basis',currency_basis:'local'}));
 assert.deepEqual(await rows(p),[1,0]);
 const out=await p.evaluate(()=>h.replaceSource('synthetic:v2','synthetic:v1'));assert.equal(out.ok,true);
 assert.equal(await p.locator(active).count(),0);assert.deepEqual(await p.evaluate(()=>h.getState().compare_markets),['JP','KR']);
}));

test('a DOM failure during sort rolls back every row and leaves original listeners intact',async()=>fixture(async p=>{
 await pin(p,'JP');
 const out=await p.evaluate(()=>{
  const panel=document.querySelector('[data-im-compare-panel]'),body=panel.querySelector('tbody'),original=body.appendChild;
  const before=panel.outerHTML,state=h.getState();let once=true;
  body.appendChild=function(n){if(once){once=false;throw Error('synthetic DOM failure')}return original.call(this,n)};
  let result;try{result=h.dispatch({type:'pin',market_id:'KR'})}finally{body.appendChild=original}
  return {ok:result.ok,unchanged:panel.outerHTML===before,state,after:h.getState()};
 });assert.equal(out.ok,false);assert.equal(out.unchanged,true);assert.deepEqual(out.state,out.after);
}));

for (const failHistory of [false,true]) test('focused Remove survives row movement '+(failHistory?'and history rollback':'on successful pin'),async()=>fixture(async p=>{
 await pin(p,'JP');await p.locator(active+' [data-im-compare-remove="0"]').focus();
 const out=await p.evaluate(fail=>{
  const focused=document.activeElement,before=h.getState(),push=history.pushState;
  if(fail)history.pushState=()=>{throw Error('synthetic history failure')};
  let result;try{result=h.dispatch({type:'pin',market_id:'KR'})}finally{history.pushState=push}
  return {ok:result.ok,same:document.activeElement===focused,connected:focused.isConnected,before,state:h.getState()};
 },failHistory);
 assert.equal(out.ok,!failHistory);assert.equal(out.same,true);assert.equal(out.connected,true);
 if(failHistory)assert.deepEqual(out.state,out.before);
}));

test('actual records, catalogue and Jinja reach the browser with unchanged financial text and canonical order',async()=>{
 const {execFileSync}=require('node:child_process');
 const html=execFileSync(process.env.INTL_TEST_PYTHON||'python3',['-c',`
import importlib.util
from pathlib import Path
p=Path('tests/test_intl_inspector_mount.py');s=importlib.util.spec_from_file_location('actual_compare',p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
project,_,_=m.supplied.__wrapped__()
print(m.render_international_pages(m.ActualShell(),{'intl_workspace':m.workspace(project)})[0])
`],{cwd:path.resolve(__dirname,'..'),encoding:'utf8',maxBuffer:4*1024*1024});
 const page=await browser.newPage();
 try{
  await page.route('http://actual.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><html lang="en"><meta charset="utf-8"><style>[hidden]{display:none!important}</style><body>'+html+'</body></html>'}));
  await page.goto('http://actual.test/intl.html');
  for(const asset of ['intl_workspace_state.js','intl_library_search.js','intl_workspace.js','intl_workspace_entry.js'])await page.addScriptTag({content:source(asset)});
  const out=await page.evaluate(()=>{
   const root=document.querySelector('[data-im-workspace]'),h=IntlWorkspace.mountIntlWorkspace(root,JSON.parse(root.querySelector('[data-im-config]').textContent));
   h.dispatch({type:'set_view',view:'compare'});
   const panel=root.querySelector('[data-im-compare-panel]:not([hidden])'),nodes=[...panel.querySelectorAll('[data-im-compare-slot]')],values=nodes.map(n=>n.textContent);
   const catalogue=JSON.parse(panel.querySelector('[data-im-compare-catalogue]').textContent);
   h.dispatch({type:'pin',market_id:'JP'});h.dispatch({type:'pin',market_id:'GB'});
   return {state:panel.dataset.imCompareState,slots:[...panel.querySelectorAll('[data-im-compare-slot]:not([hidden])')].map(n=>Number(n.dataset.imCompareSlot)),expected:catalogue.cohorts[0].order_slots,same:nodes.every(n=>root.contains(n)),values,after:nodes.map(n=>n.textContent)};
  });assert.equal(out.state,'comparable');assert.deepEqual(out.slots,out.expected);assert.equal(out.same,true);assert.deepEqual(out.after,out.values);
 }finally{await page.close();}
});
