'use strict';
const {test, before, after}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'), path=require('node:path');
const {chromium}=require('playwright');
const G='im-workspace-generation:11111111-1111-4111-8111-111111111111';
const G2='im-workspace-generation:22222222-2222-4222-8222-222222222222';
const config={markets:['JP','GB'],horizons:['1m'],bases:['local','usd_unhedged'],default_horizon:'1m',default_basis:'usd_unhedged',source_reference:G,anchor_ids:['origin'],library_group_ids:[]};
let browser;
before(async()=>{browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL?{channel:process.env.PLAYWRIGHT_CHROMIUM_CHANNEL}:{})});});
after(async()=>{await browser.close();});
const source=n=>fs.readFileSync(path.join(__dirname,'../templates',n),'utf8');
function markup(){return `<section data-im-workspace data-im-mode="macro" data-im-binding-version="2"><h1 data-im-heading>Markets</h1><fieldset data-im-controls disabled><button data-im-action="set_view" data-im-view="overview">Overview</button><button data-im-action="set_view" data-im-view="risk">Risk</button><select data-im-action="select_market"><option value="">All markets</option><option>JP</option><option>GB</option></select></fieldset><p data-im-issues></p><p data-im-unavailable hidden>Unavailable</p><button id="origin">Origin</button><section data-im-panel data-im-generation="${G}" data-view="overview" data-horizon="1m" data-basis="usd_unhedged" data-return-basis="price" data-source="" id="overview">Overview</section><section data-im-panel data-im-generation="${G}" data-view="risk" data-horizon="1m" data-basis="usd_unhedged" data-return-basis="price" data-source="" id="risk"><p data-im-risk-prompt><span class="l-en">Select a market to examine the currency channel</span><span class="l-zh">选择市场以查看汇率传导</span></p><article data-im-risk-channel="0" data-im-risk-market="JP">Local 0%; USD 5%<details id="context"><summary id="context-summary">Company exposure requirements</summary><p>No issuer exposure supplied</p><button data-im-risk-close-context>Back</button></details></article><article data-im-risk-channel="1" data-im-risk-market="GB">Other owner returns</article><div data-im-risk-row="JP">Credit unavailable</div><div data-im-risk-row="GB">Annual projection</div><section data-im-workspace id="foreign"><div data-im-risk-channel="0" data-im-risk-market="JP" data-im-risk-selected="foreign">Foreign</div><details open><summary>Foreign context</summary><button data-im-risk-close-context>Foreign back</button></details></section></section><script type="application/json" data-im-config>${JSON.stringify(config)}</script></section>`;}
async function fixture(run,{mutate=null}={}){
 const page=await browser.newPage();page.setDefaultTimeout(2500);
 try{await page.route('http://risk.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><html lang="en"><style>[hidden]{display:none!important}</style><body>'+markup()+'</body></html>'}));await page.goto('http://risk.test/intl.html');await page.evaluate(c=>{window.config=c;window.root=document.querySelector('[data-im-workspace]');},config);if(mutate)await page.evaluate(mutate);for(const n of ['intl_workspace_state.js','intl_workspace.js'])await page.addScriptTag({content:source(n)});await page.evaluate(()=>{window.beforeMount=root.outerHTML;window.h=IntlWorkspace.mountIntlWorkspace(root,config);});await run(page);}finally{await page.close();}
}
test('Risk selection uses the configured slot, retains pins and ignores nested workspaces',async()=>fixture(async p=>{
 await p.evaluate(()=>h.dispatch({type:'set_view',view:'risk'}));
 assert.equal(await p.locator('#risk > [data-im-risk-channel="0"]').isVisible(),false);
 assert.equal(await p.locator('[data-im-risk-prompt]').isVisible(),true);
 await p.evaluate(()=>{h.dispatch({type:'pin',market_id:'GB'});h.dispatch({type:'select_market',market_id:'JP'});});
 assert.equal(await p.locator('#risk > [data-im-risk-channel="0"]').isVisible(),true);
 assert.equal(await p.locator('#risk > [data-im-risk-channel="1"]').isVisible(),false);
 assert.equal(await p.locator('[data-im-risk-prompt]').isVisible(),false);
 assert.equal(await p.locator('[data-im-risk-row="JP"]').getAttribute('data-im-risk-selected'),'true');
 assert.equal(await p.locator('[data-im-risk-row="GB"]').getAttribute('data-im-risk-selected'),'false');
 assert.equal(await p.locator('#foreign [data-im-risk-channel]').getAttribute('data-im-risk-selected'),'foreign');
 assert.deepEqual(await p.evaluate(()=>h.getState().compare_markets),['GB']);
}));
test('a redacted slot shows its withheld content without borrowing another market',async()=>fixture(async p=>{
 await p.evaluate(()=>{h.dispatch({type:'set_view',view:'risk'});h.dispatch({type:'select_market',market_id:'JP'});});
 assert.equal(await p.locator('#risk > [data-im-risk-channel="0"]').isVisible(),true);
 assert.equal(await p.locator('#risk > [data-im-risk-channel="0"]').textContent(),'Withheld');
 assert.equal(await p.locator('#risk > [data-im-risk-channel="1"]').isVisible(),false);
},{mutate:()=>{const n=root.querySelector('[data-im-risk-channel="0"]');n.removeAttribute('data-im-risk-market');n.textContent='Withheld';}}));
for(const [name,mutate] of [
 ['duplicate slot',()=>root.querySelector('[data-im-risk-channel="1"]').setAttribute('data-im-risk-channel','0')],
 ['wrong identity',()=>root.querySelector('[data-im-risk-channel="0"]').setAttribute('data-im-risk-market','GB')]
])test('Risk '+name+' withholds ambiguous currency content',async()=>fixture(async p=>{
 await p.evaluate(()=>{h.dispatch({type:'set_view',view:'risk'});h.dispatch({type:'select_market',market_id:'JP'});});
 assert.equal(await p.locator('#risk > [data-im-risk-channel]').evaluateAll(ns=>ns.every(n=>n.hidden)),true);
 assert.match(await p.locator('[data-im-risk-prompt]').textContent(),/unavailable/);
},{mutate}));
test('failed history commit restores Risk selection and native open evidence',async()=>fixture(async p=>{
 await p.evaluate(()=>{h.dispatch({type:'set_view',view:'risk'});h.dispatch({type:'select_market',market_id:'JP'});document.querySelector('#context').open=true;history.pushState=()=>{throw Error('fixture refusal')};});
 const result=await p.evaluate(()=>h.dispatch({type:'select_market',market_id:'GB'}));assert.equal(result.ok,false);
 assert.equal(await p.locator('#risk > [data-im-risk-channel="0"]').isVisible(),true);
 assert.equal(await p.locator('#risk > [data-im-risk-channel="1"]').isVisible(),false);
 assert.equal(await p.locator('#context').evaluate(n=>n.open),true);
 assert.equal(await p.locator('[data-im-risk-row="JP"]').getAttribute('data-im-risk-selected'),'true');
}));
test('contextual Back closes the same detail and restores focus without changing research state',async()=>fixture(async p=>{
 await p.evaluate(()=>{h.dispatch({type:'set_view',view:'risk'});h.dispatch({type:'select_market',market_id:'JP'});document.querySelector('#context').open=true;window.beforeBack=JSON.stringify(h.getState());});
 await p.locator('#context [data-im-risk-close-context]').click();
 assert.equal(await p.locator('#context').evaluate(n=>n.open),false);
 assert.equal(await p.evaluate(()=>document.activeElement.id),'context-summary');
 assert.equal(await p.evaluate(()=>JSON.stringify(h.getState())===beforeBack),true);
 await p.locator('#foreign [data-im-risk-close-context]').click();assert.equal(await p.locator('#foreign details').evaluate(n=>n.open),true);
}));
test('Risk rejects non-price basis and cannot borrow a stale publication generation',async()=>fixture(async p=>{
 await p.evaluate(()=>h.dispatch({type:'set_view',view:'risk'}));assert.equal(await p.locator('#risk').isVisible(),false);
},{mutate:()=>root.querySelector('#risk').setAttribute('data-return-basis','total_return')}));
test('new publication hides old Risk panels while preserving selected market and pins',async()=>fixture(async p=>{
 await p.evaluate(()=>{h.dispatch({type:'set_view',view:'risk'});h.dispatch({type:'pin',market_id:'GB'});h.dispatch({type:'select_market',market_id:'JP'});});
 await p.evaluate(g=>h.replaceSource(g,config.source_reference),G2);
 assert.equal(await p.locator('#risk').isVisible(),false);assert.equal(await p.evaluate(()=>h.getState().selected_market),'JP');assert.deepEqual(await p.evaluate(()=>h.getState().compare_markets),['GB']);
}));
test('destroy restores server Risk DOM and attributes exactly',async()=>fixture(async p=>{
 await p.evaluate(()=>{h.dispatch({type:'set_view',view:'risk'});h.dispatch({type:'select_market',market_id:'JP'});h.destroy();});
 assert.equal(await p.evaluate(()=>root.outerHTML===beforeMount),true);
}));
