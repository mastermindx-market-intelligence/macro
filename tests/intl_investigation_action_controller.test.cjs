'use strict';
const {test,before,after}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium}=require('playwright');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const gen='im-workspace-generation:4979a6c3-b834-4c69-8f1b-c8961cc5e11a';
const context='intl-workspace-context:sha256:'+'a'.repeat(64),fingerprint='b'.repeat(64);
const config={markets:['JP','EZ','GB'],horizons:['3m'],bases:['local'],default_horizon:'3m',default_basis:'local',source_reference:gen,anchor_ids:['intl-legacy-research'],library_group_ids:[]};
function action(view){
 const field=view==='risk'?'EZ.annual_current_account':'EZ.policy_rate';
 const q=new URLSearchParams({view:'investigations',intl_context:context,intl_generation:gen,intl_fingerprint:fingerprint,intl_field:field,intl_return:'https://www.mastermind-x.com/intl.html?view='+view});
 const href='/analysis?'+q;
 return `<a data-im-investigate data-im-investigate-href="${href.replace(/&/g,'&amp;')}" href="${href.replace(/&/g,'&amp;')}" data-im-native-context="${context}" data-im-native-generation="${gen}" data-im-native-fingerprint="${fingerprint}" data-im-native-field="${field}">Investigate</a>`;
}
function html(){return `<html><body><section data-im-workspace data-im-mode="macro" data-im-binding-version="2"><h1 data-im-heading>International</h1><button data-im-action="set_view" data-im-view="macro">Macro</button><button data-im-action="set_view" data-im-view="risk">Risk</button><p data-im-issues></p><p data-im-unavailable hidden>Unavailable</p>${['overview','macro','risk'].map(view=>`<section data-im-panel data-view="${view}" data-horizon="3m" data-basis="local" data-return-basis="price" data-source="" data-im-generation="${gen}" id="${view}">${view==='overview'?'Overview':action(view)}</section>`).join('')}</section></body></html>`;}
let browser;before(async()=>{browser=await chromium.launch({headless:true});});after(async()=>{await browser.close();});
async function fixture(run,mutate){const page=await browser.newPage();try{
 await page.route('http://action.test/**',r=>r.fulfill({contentType:'text/html',body:html()}));
 await page.goto('http://action.test/intl.html?view=macro&market=JP&pins=JP,GB&horizon=3m&basis=local&return_basis=price&group=#intl-legacy-research');
 await page.addScriptTag({content:fs.readFileSync(path.join(root,'templates/intl_workspace_state.js'),'utf8')});
 await page.addScriptTag({content:fs.readFileSync(path.join(root,'templates/intl_workspace.js'),'utf8')});
 await page.evaluate(cfg=>{window.cfg=cfg;window.root=document.querySelector('[data-im-workspace]');},config);
 if(mutate)await page.evaluate(mutate);
 await page.evaluate(()=>{window.handle=IntlWorkspace.mountIntlWorkspace(root,cfg);});await run(page);
}finally{await page.close();}}

test('permitted reference action keeps financial context with native canonical no-fragment return',async()=>{
 await fixture(async page=>{
  const state=await page.evaluate(()=>({state:handle.getState(),href:document.querySelector('#macro a').getAttribute('href')}));
  const url=new URL(state.href,'https://www.mastermind-x.com');assert.equal(url.pathname,'/analysis');
  assert.equal(url.searchParams.get('intl_context'),context);assert.equal(url.searchParams.get('intl_generation'),gen);
  const ret=new URL(url.searchParams.get('intl_return'));assert.equal(ret.origin,'https://www.mastermind-x.com');assert.equal(ret.pathname,'/intl.html');
  assert.equal(ret.searchParams.get('market'),'JP');assert.equal(ret.searchParams.get('pins'),'JP,GB');assert.equal(ret.searchParams.get('horizon'),'3m');assert.equal(ret.searchParams.get('basis'),'local');assert.equal(ret.hash,'');assert.equal(ret.searchParams.get('group'),'');assert.equal(ret.href.includes('%2C'),false);assert.ok(state.href.length<=2048);
  assert.equal(ret.searchParams.get('mmx_shell'),null);
  const before=state.state;await page.evaluate(()=>handle.dispatch({type:'set_view',view:'risk'}));
  const risk=await page.evaluate(()=>document.querySelector('#risk a').getAttribute('href'));
  assert.equal(new URL(new URL(risk,'https://www.mastermind-x.com').searchParams.get('intl_return')).searchParams.get('view'),'risk');
  assert.equal((await page.evaluate(()=>handle.getState())).selected_market,before.selected_market);
 });
});

test('malformed or foreign reference action never keeps an enabled href',async()=>{
 for(const fault of ['generation','context','duplicate','extra','market']){
  await fixture(async page=>{
   const disabled=await page.evaluate(()=>({href:document.querySelector('#macro a').getAttribute('href'),disabled:document.querySelector('#macro a').getAttribute('aria-disabled')}));
   assert.equal(disabled.href,null,fault);assert.equal(disabled.disabled,'true',fault);
  },new Function(`const link=document.querySelector('#macro a');
   const fault=${JSON.stringify(fault)};
   if(fault==='generation')link.setAttribute('data-im-native-generation','foreign');
   else if(fault==='context')link.setAttribute('data-im-native-context','foreign');
   else if(fault==='market')link.setAttribute('data-im-native-field','US.policy_rate');
   else link.setAttribute('data-im-investigate-href',link.getAttribute('data-im-investigate-href')+(fault==='duplicate'?'&intl_field=EZ.policy_rate':'&question=private'));
  `));
 }
});

test('destroy restores original authored href and no action changes reducer state',async()=>{
 await fixture(async page=>{
  const result=await page.evaluate(()=>{const link=document.querySelector('#macro a'),original=link.getAttribute('data-im-investigate-href'),before=JSON.stringify(handle.getState());handle.destroy();return{original,href:link.getAttribute('href'),before};});
  assert.equal(result.href,result.original);
 });
});

test('native return clears navigation-only group and fragment without changing current state',async()=>{
 await fixture(async page=>{
  const result=await page.evaluate(()=>({state:handle.getState(),href:document.querySelector('#macro a').getAttribute('href')}));
  const target=new URL(result.href,'https://www.mastermind-x.com');const ret=new URL(target.searchParams.get('intl_return'));
  assert.equal(result.state.library_group,'rates');assert.equal(ret.searchParams.get('group'),'');assert.equal(ret.hash,'');
  assert.equal(ret.searchParams.get('market'),'JP');assert.equal(target.searchParams.get('intl_field'),'EZ.policy_rate');
  assert.equal(ret.searchParams.get('pins'),'JP,GB');assert.equal(ret.href.includes('%2C'),false);assert.ok(result.href.length<=2048);
 },()=>{cfg.library_group_ids=['rates'];history.replaceState(null,'',location.href.replace('group=','group=rates'));});
});

test('no-focus Macro return keeps present-empty market without inventing focus',async()=>{
 await fixture(async page=>{
  const result=await page.evaluate(()=>({state:handle.getState(),href:document.querySelector('#macro a').getAttribute('href')}));
  const target=new URL(result.href,'https://www.mastermind-x.com');const ret=new URL(target.searchParams.get('intl_return'));
  assert.equal(result.state.selected_market,null);assert.equal(ret.searchParams.has('market'),true);assert.equal(ret.searchParams.get('market'),'');
  assert.equal(target.searchParams.get('intl_field'),'EZ.policy_rate');assert.equal(ret.hash,'');assert.equal(ret.searchParams.get('group'),'');
 },()=>{history.replaceState(null,'',location.href.replace('market=JP','market='));});
});
