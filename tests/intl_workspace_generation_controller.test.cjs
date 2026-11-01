'use strict';
const {test,before,after}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
const G='im-workspace-generation:11111111-1111-4111-8111-111111111111';
const G2='im-workspace-generation:22222222-2222-4222-8222-222222222222';
const config={markets:['JP','GB'],horizons:['1m'],bases:['local','usd_unhedged'],default_horizon:'1m',default_basis:'usd_unhedged',source_reference:G,anchor_ids:['origin'],library_group_ids:[]};
const src=n=>fs.readFileSync(path.join(__dirname,'../templates',n),'utf8');
let browser;
before(async()=>{browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL?{channel:process.env.PLAYWRIGHT_CHROMIUM_CHANNEL}:{})});});
after(async()=>{await browser.close();});
function inspector(basis,source){return `<details data-im-inspector-origin data-im-generation="${G}" data-im-inspector-context="im-${basis}"><summary data-im-inspector-trigger data-im-generation="${G}">JP details</summary><article data-im-inspector-payload data-im-generation="${G}" data-im-inspector-context="im-${basis}" data-market-id="JP" data-horizon="1m" data-basis="${basis}" data-return-basis="price" data-source="${source}" id="article-${basis}"><h3 data-im-inspector-title id="title-${basis}" tabindex="-1">Japan</h3><section data-im-inspector-page="read">Available facts</section><details data-im-inspector-ledger><summary data-im-inspector-ledger-trigger>Evidence</summary><section data-im-inspector-page="ledger"><h4>Evidence</h4></section></details><div data-im-inspector-enhancement hidden><button data-im-inspector-action="close">Close</button></div></article></details>`;}
function markup(){return `<section data-im-workspace data-im-mode="macro" data-im-binding-version="2"><h1 data-im-heading>Markets</h1><fieldset data-im-controls disabled><button data-im-action="set_view" data-im-view="overview">Overview</button><button data-im-action="set_view" data-im-view="library">Library</button></fieldset><p data-im-issues></p><p data-im-unavailable hidden>Unavailable</p><button id="origin">Origin</button>${['usd_unhedged','local'].map(b=>`<section data-im-panel data-im-generation="${G}" data-view="overview" data-horizon="1m" data-basis="${b}" data-return-basis="price" data-source="${b==='local'?'synthetic:financial':''}" id="im-${b}-overview">${b==='local'?'12.00%':'Unavailable'}</section>`).join('')}<section data-im-panel data-im-generation="${G}" data-view="library" data-horizon="1m" data-basis="usd_unhedged" data-source="">Metadata</section><section data-im-inspectors>${inspector('local','synthetic:financial')}${inspector('usd_unhedged','')}<dialog data-im-inspector-shell></dialog></section><script type="application/json" data-im-config>${JSON.stringify(config)}</script></section><details id="intl-legacy-research" open><summary>Existing research</summary>Readable</details>`;}
async function fixture(run,{mutate=null,mount=true,entry=false}={}){
 const p=await browser.newPage();p.setDefaultTimeout(2500);
 try{await p.route('http://generation.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><html lang="en"><meta charset="utf-8"><style>[hidden]{display:none!important}</style><body>'+markup()+'</body></html>'}));await p.goto('http://generation.test/intl.html');await p.evaluate(c=>{window.config=c;window.root=document.querySelector('[data-im-workspace]');},config);if(mutate)await p.evaluate(mutate);for(const n of ['intl_workspace_state.js','intl_workspace.js'])await p.addScriptTag({content:src(n)});if(entry)await p.addScriptTag({content:src('intl_workspace_entry.js')});else if(mount)await p.evaluate(()=>window.h=IntlWorkspace.mountIntlWorkspace(root,config));await run(p);}finally{await p.close();}
}

test('partial disclosure permits both contexts without rewriting financial source or URL',async()=>fixture(async p=>{
 assert.equal(await p.locator('#im-usd_unhedged-overview').isVisible(),true);
 await p.evaluate(()=>h.dispatch({type:'set_basis',currency_basis:'local'}));assert.equal(await p.locator('#im-local-overview').isVisible(),true);assert.equal(await p.locator('#im-local-overview').getAttribute('data-source'),'synthetic:financial');
 await p.evaluate(()=>h.dispatch({type:'set_view',view:'library'}));assert.equal(await p.locator('[data-view="library"]').isVisible(),false); // tuple remains USD: no borrowed context
 assert.equal(await p.evaluate(()=>location.search.includes('generation')||location.search.includes('financial')),false);
}));
test('NULL Inspector joins exact NULL panel; nonnull context uses its own source',async()=>fixture(async p=>{
 assert.equal((await p.evaluate(()=>h.openInspector({market_id:'JP',expected_source:config.source_reference}))).ok,true);
 await p.evaluate(()=>h.closeInspector());await p.evaluate(()=>h.dispatch({type:'set_basis',currency_basis:'local'}));
 assert.equal((await p.evaluate(()=>h.openInspector({market_id:'JP',expected_source:config.source_reference}))).ok,true);
}));
test('NULL is not a wildcard into nonnull Overview, including fallback',async()=>fixture(async p=>{
 await p.evaluate(()=>h.dispatch({type:'set_basis',currency_basis:'local'}));
 assert.equal((await p.evaluate(()=>h.openInspector({market_id:'JP',expected_source:config.source_reference}))).ok,false);
 assert.equal(await p.locator('#article-local').evaluate(n=>n.closest('details').hidden),true);
},{mutate:()=>document.querySelector('#article-local').removeAttribute('data-source')}));
for(const [name,mutate] of [
 ['unknown version',()=>root.dataset.imBindingVersion='3'],['boolean version',()=>root.dataset.imBindingVersion='true'],
 ['noncanonical nonce',()=>config.source_reference='im-workspace-generation:NOT-A-NONCE'],
 ['missing panel generation',()=>root.querySelector('[data-im-panel]').removeAttribute('data-im-generation')],
 ['mixed panel generation',()=>root.querySelector('[data-im-panel]').dataset.imGeneration='im-workspace-generation:22222222-2222-4222-8222-222222222222'],
 ['missing article generation',()=>root.querySelector('[data-im-inspector-payload]').removeAttribute('data-im-generation')],
 ['missing trigger generation',()=>root.querySelector('[data-im-inspector-trigger]').removeAttribute('data-im-generation')],
 ['missing origin generation',()=>root.querySelector('[data-im-inspector-origin]').removeAttribute('data-im-generation')],
 ['v1 with generation sidecars',()=>root.removeAttribute('data-im-binding-version')]
])test(name+' refuses atomically',async()=>fixture(async p=>{
 const out=await p.evaluate(()=>{const before=root.outerHTML,n=root.querySelector('[data-im-panel]');let refused=false;try{IntlWorkspace.mountIntlWorkspace(root,config)}catch(_){refused=true}return {refused,unchanged:root.outerHTML===before,same:n===root.querySelector('[data-im-panel]'),enhanced:root.hasAttribute('data-im-enhanced')};});assert.deepEqual(out,{refused:true,unchanged:true,same:true,enhanced:false});
},{mutate,mount:false}));
test('entry keeps native research readable when version refuses',async()=>fixture(async p=>{assert.equal(await p.locator('[data-im-controls]').evaluate(n=>n.disabled),true);assert.equal(await p.locator('#intl-legacy-research').evaluate(n=>n.open),true);assert.equal(await p.locator('[data-im-workspace]').getAttribute('data-im-enhanced'),null);},{mutate:()=>root.dataset.imBindingVersion='9',entry:true}));
test('same numerical source new generation rejects old nodes, clears bounds and retains selections',async()=>fixture(async p=>{
 const out=await p.evaluate(g=>{h.dispatch({type:'pin',market_id:'JP'});h.dispatch({type:'select_market',market_id:'JP'});h.dispatch({type:'capture_baseline'});h.dispatch({type:'push_return',anchor_id:'origin'});const result=h.replaceSource(g,config.source_reference);return {ok:result.ok,state:h.getState(),visible:[...root.querySelectorAll('[data-im-panel]')].filter(n=>!n.hidden).length,fallbacks:[...root.querySelectorAll('[data-im-inspector-origin]')].filter(n=>!n.hidden).length};},G2);
 assert.equal(out.ok,true);assert.equal(out.visible,0);assert.equal(out.fallbacks,0);assert.deepEqual(out.state.compare_markets,['JP']);assert.equal(out.state.selected_market,'JP');assert.equal(out.state.baseline,null);assert.deepEqual(out.state.return_stack,[]);
}));
test('fresh publication nodes with same numerical source activate after replace',async()=>fixture(async p=>{
 const out=await p.evaluate(g=>{root.querySelectorAll('[data-im-generation]').forEach(n=>n.dataset.imGeneration=g);return h.replaceSource(g,config.source_reference);},G2);assert.equal(out.ok,true);assert.equal(await p.locator('#im-usd_unhedged-overview').isVisible(),true);assert.equal((await p.evaluate(g=>h.openInspector({market_id:'JP',expected_source:g}),G2)).ok,true);
}));
test('stale trigger never silently uses current generation',async()=>fixture(async p=>{
 await p.evaluate(g=>root.querySelector('#article-usd_unhedged').parentNode.querySelector('summary').dataset.imGeneration=g,G2);
 await p.locator('#article-usd_unhedged').locator('..').locator('summary').first().click();assert.equal(await p.locator('dialog').evaluate(n=>n.open),false);assert.equal(await p.locator('#article-usd_unhedged').evaluate(n=>n.parentNode.open),false);
}));
test('invalid replacement nonce refuses without changes',async()=>fixture(async p=>{
 const out=await p.evaluate(()=>{const before=root.outerHTML,state=h.getState();let r;try{r=h.replaceSource('synthetic:financial',config.source_reference)}catch(_){r={ok:false}}return {ok:r.ok,same:root.outerHTML===before,state,after:h.getState()};});assert.equal(out.ok,false);assert.equal(out.same,true);assert.deepEqual(out.state,out.after);
}));
test('failed replacement preserves original modal article, state and focus',async()=>fixture(async p=>{
 const out=await p.evaluate(g=>{h.openInspector({market_id:'JP',expected_source:config.source_reference});const article=root.querySelector('dialog article'),focus=document.activeElement,state=h.getState(),panel=root.querySelector('[data-im-unavailable]'),original=panel.setAttribute;Object.defineProperty(panel,'hidden',{configurable:true,get(){return this.hasAttribute('hidden')},set(){throw Error('synthetic paint failure')}});let result;try{result=h.replaceSource(g,config.source_reference)}finally{delete panel.hidden}return {ok:result.ok,same:root.querySelector('dialog article')===article,modal:root.querySelector('dialog').matches(':modal'),focus:document.activeElement===focus,state,after:h.getState()};},G2);assert.equal(out.ok,false);assert.equal(out.same,true);assert.equal(out.modal,true);assert.equal(out.focus,true);assert.deepEqual(out.state,out.after);
}));
test('nested foreign version never belongs to outer generation validation',async()=>fixture(async p=>{assert.equal(await p.locator('#im-usd_unhedged-overview').first().isVisible(),true);assert.equal(await p.locator('[data-im-workspace] [data-im-workspace]').getAttribute('data-im-enhanced'),null);},{mutate:()=>root.insertAdjacentHTML('beforeend','<section data-im-workspace data-im-binding-version="9"><div data-im-panel>Nested native</div></section>')}));
test('language and resize preserve generation state and history',async()=>fixture(async p=>{const before=await p.evaluate(()=>({state:h.getState(),history:history.length,url:location.href}));await p.evaluate(()=>document.documentElement.lang='zh');await p.setViewportSize({width:390,height:844});assert.deepEqual(await p.evaluate(()=>({state:h.getState(),history:history.length,url:location.href})),before);}));
