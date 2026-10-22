'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path');
const {execFileSync}=require('node:child_process');
const ROOT=path.resolve(__dirname,'..');
const fixture=JSON.parse(execFileSync('python3',['-m','tests.history_browser_fixture'],{cwd:ROOT,encoding:'utf8',maxBuffer:4*1024*1024}));
let browser;
test.before(async()=>{browser=await chromium.launch({headless:true,channel:process.env.PLAYWRIGHT_CHROMIUM_CHANNEL||undefined});});
test.after(async()=>{await browser.close();});
async function setup(t){
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(3000);t.after(()=>page.close());
 await page.route('http://fixture.test/**',r=>r.fulfill({contentType:'text/html',body:'<!doctype html><html lang="en"><body>'+fixture.html+'</body></html>'}));
 await page.goto('http://fixture.test/intl.html?view=history&market=JP&horizon=1m&basis=usd_unhedged&return_basis=price');
 for(const file of ['intl_workspace_state.js','intl_workspace_scenario.js','intl_workspace.js'])await page.addScriptTag({content:fs.readFileSync(path.join(ROOT,'templates',file),'utf8')});
 await page.evaluate(c=>{window.handle=IntlWorkspace.mountIntlWorkspace(document.querySelector('[data-im-workspace]'),c);},fixture.config);
 return page;
}
async function calculate(page,local='5',fx='-3'){
 await page.locator('[data-im-scenario-field="local"]').fill(local);await page.locator('[data-im-scenario-field="fx"]').fill(fx);
 await page.locator('[data-im-scenario-action="calculate"]').click();
}
test('real mounted form starts blank and calculates accepted arithmetic',async t=>{
 const p=await setup(t);assert.equal(await p.locator('[data-im-scenario-field="local"]').inputValue(),'');
 await calculate(p);assert.match(await p.locator('[data-im-scenario-usd]').innerText(),/1\.85/);
 assert.match(await p.locator('[data-im-scenario-contribution]').innerText(),/-3\.15/);
 assert.equal(await p.locator('[data-im-scenario-rows] li').count(),3);
});
test('market selection paints only the exact configured history',async t=>{
 const p=await setup(t);assert.equal(await p.locator('[data-im-history-market="JP"]').isVisible(),true);
 assert.equal(await p.locator('[data-im-history-market="KR"]').isVisible(),false);
 await p.locator('[data-im-history-panel] [data-im-action="select_market"]').selectOption('KR');
 assert.equal(await p.locator('[data-im-history-market="KR"]').isVisible(),true);
});
test('invalid edit clears the former result and calculate focuses its field',async t=>{
 const p=await setup(t);await calculate(p);await p.locator('[data-im-scenario-field="fx"]').fill('-100');
 assert.equal(await p.locator('[data-im-scenario-result]').isVisible(),false);
 await p.locator('[data-im-scenario-action="calculate"]').click();
 assert.equal(await p.evaluate(()=>document.activeElement.id),'im-scenario-fx');
 assert.equal(await p.locator('#im-scenario-fx').getAttribute('aria-invalid'),'true');
});
test('horizon proposal preserves old context and raw; cancel restores exact result',async t=>{
 const p=await setup(t);await calculate(p);const old=await p.evaluate(()=>handle.getState());
 await p.locator('[data-im-action="set_horizon"]').selectOption('3m');
 assert.equal((await p.evaluate(()=>handle.getState())).horizon,'1m');
 assert.equal(await p.locator('[data-im-scenario-result]').isVisible(),false);
 assert.equal(await p.locator('[data-im-scenario-confirm-context]').isVisible(),true);
 await p.locator('#im-scenario-local').fill('12');await p.locator('[data-im-scenario-action="cancel_context"]').click();
 assert.deepEqual(await p.evaluate(()=>handle.getState()),old);assert.equal(await p.locator('#im-scenario-local').inputValue(),'5');
 assert.equal(await p.locator('[data-im-scenario-result]').isVisible(),true);
});
test('confirm commits reviewed inputs and context with no annualization',async t=>{
 const p=await setup(t);await calculate(p);await p.locator('[data-im-action="set_horizon"]').selectOption('3m');
 await p.locator('#im-scenario-local').fill('10');await p.locator('[data-im-scenario-action="confirm_context"]').click();
 assert.equal((await p.evaluate(()=>handle.getState())).horizon,'3m');assert.match(await p.locator('[data-im-scenario-usd]').innerText(),/6\.7/);
 assert.match(await p.locator('[data-im-scenario-context]').innerText(),/3m/);
});
test('invalid confirm keeps original research tuple and focuses candidate',async t=>{
 const p=await setup(t);await calculate(p);await p.locator('[data-im-action="set_horizon"]').selectOption('3m');
 await p.locator('#im-scenario-local').fill('-101');await p.locator('[data-im-scenario-action="confirm_context"]').click();
 assert.equal((await p.evaluate(()=>handle.getState())).horizon,'1m');assert.equal(await p.evaluate(()=>document.activeElement.id),'im-scenario-local');
 assert.equal(await p.locator('[data-im-scenario-result]').isVisible(),false);
});
test('internal tab and route roundtrips retain the manual draft',async t=>{
 const p=await setup(t);await calculate(p);await p.locator('[data-im-scenario-action="set_tab"][data-im-scenario-tab="scenario"]').click({force:true});
 await p.evaluate(()=>handle.dispatch({type:'set_view',view:'overview'}));await p.evaluate(()=>handle.dispatch({type:'set_view',view:'history'}));
 assert.equal(await p.locator('#im-scenario-local').inputValue(),'5');assert.equal(await p.locator('[data-im-scenario-result]').isVisible(),true);
});
test('reset confirms once, cancellation keeps state and confirmation preserves research context',async t=>{
 const p=await setup(t);await calculate(p);await p.evaluate(()=>handle.dispatch({type:'pin',market_id:'JP'}));const old=await p.evaluate(()=>handle.getState());
 await p.locator('[data-im-scenario-action="request_reset"]').click();await p.locator('[data-im-scenario-action="cancel_reset"]').click();
 assert.equal(await p.locator('#im-scenario-local').inputValue(),'5');
 await p.locator('[data-im-scenario-action="request_reset"]').click();await p.locator('[data-im-scenario-action="confirm_reset"]').click();
 assert.deepEqual(await p.evaluate(()=>handle.getState()),old);assert.equal(await p.locator('#im-scenario-local').inputValue(),'');
});
test('context proposal from another view reveals review without silently changing market',async t=>{
 const p=await setup(t);await calculate(p);await p.evaluate(()=>handle.dispatch({type:'set_view',view:'overview'}));
 await p.evaluate(()=>handle.dispatch({type:'select_market',market_id:'KR'}));
 assert.equal((await p.evaluate(()=>handle.getState())).selected_market,'JP');assert.equal(await p.locator('[data-im-scenario-confirm-context]').isVisible(),true);
 await p.locator('[data-im-scenario-action="cancel_context"]').click();assert.equal((await p.evaluate(()=>handle.getState())).view,'overview');
});
test('failed URL commit rolls back both research and scenario draft',async t=>{
 const p=await setup(t);await calculate(p);await p.locator('[data-im-action="set_horizon"]').selectOption('3m');
 await p.locator('#im-scenario-local').fill('10');
 await p.evaluate(()=>{window.savedPush=history.pushState;history.pushState=()=>{throw new Error('blocked');};});
 await p.locator('[data-im-scenario-action="confirm_context"]').click();
 assert.equal((await p.evaluate(()=>handle.getState())).horizon,'1m');assert.equal(await p.locator('[data-im-scenario-confirm-context]').isVisible(),true);
 assert.equal(await p.locator('#im-scenario-local').inputValue(),'10');assert.equal(await p.locator('[data-im-scenario-result]').isVisible(),false);
 await p.evaluate(()=>history.pushState=window.savedPush);
});
test('source refresh preserves raw draft and admits no old generation result data',async t=>{
 const p=await setup(t);await calculate(p);const newSource='im-workspace-generation:99999999-9999-4999-8999-999999999999';
 const r=await p.evaluate(n=>{const old=handle.getState().source_reference;document.querySelectorAll('[data-im-generation]').forEach(el=>el.setAttribute('data-im-generation',n));return handle.replaceSource(n,old);},newSource);
 assert.equal(r.ok,true);assert.equal(await p.locator('#im-scenario-local').inputValue(),'5');assert.equal(await p.locator('[data-im-scenario-result]').isVisible(),true);
});
test('language change preserves raw and calculation and translates field errors',async t=>{
 const p=await setup(t);await calculate(p);await p.evaluate(()=>document.documentElement.lang='zh');
 await p.locator('#im-scenario-fx').fill('-100');await p.locator('[data-im-scenario-action="calculate"]').click();
 assert.match(await p.locator('#im-scenario-fx-error').innerText(),/[\u3400-\u9fff]/);
 assert.equal(await p.locator('#im-scenario-local').inputValue(),'5');
});
test('destroy restores blank disabled fallback and a new mount starts blank',async t=>{
 const p=await setup(t);await calculate(p);await p.evaluate(()=>handle.destroy());
 assert.equal(await p.locator('#im-scenario-local').inputValue(),'');assert.equal(await p.locator('[data-im-scenario-fields]').evaluate(el=>el.disabled),true);assert.equal(await p.locator('#im-scenario-local').isDisabled(),true);
 await p.evaluate(c=>{window.handle=IntlWorkspace.mountIntlWorkspace(document.querySelector('[data-im-workspace]'),c);},fixture.config);
 assert.equal(await p.locator('#im-scenario-local').inputValue(),'');
});
test('Escape cancels staged context and restores focus to the initiating control',async t=>{
 const p=await setup(t);await calculate(p);await p.locator('[data-im-action="set_horizon"]').selectOption('3m');
 await p.locator('#im-scenario-local').press('Escape');
 assert.equal(await p.locator('[data-im-scenario-confirm-context]').isVisible(),false);
 assert.equal((await p.evaluate(()=>handle.getState())).horizon,'1m');
 assert.equal(await p.evaluate(()=>document.activeElement.getAttribute('data-im-action')),'set_horizon');
});
test('Escape cancels reset without clearing assumptions',async t=>{
 const p=await setup(t);await calculate(p);await p.locator('[data-im-scenario-action="request_reset"]').click();
 await p.keyboard.press('Escape');assert.equal(await p.locator('[data-im-scenario-confirm-reset]').isVisible(),false);
 assert.equal(await p.locator('#im-scenario-local').inputValue(),'5');
});
test('browser Back stages changed context, restores URL, and cancel keeps original context',async t=>{
 const p=await setup(t);await p.locator('[data-im-action="set_horizon"]').selectOption('3m');await calculate(p);
 await p.goBack();await p.waitForFunction(()=>document.querySelector('[data-im-scenario-confirm-context]').hidden===false);
 assert.equal((await p.evaluate(()=>handle.getState())).horizon,'3m');assert.match(p.url(),/horizon=3m/);
 await p.locator('[data-im-scenario-action="cancel_context"]').click();assert.equal((await p.evaluate(()=>handle.getState())).horizon,'3m');
});
test('source replacement while pending cannot resurrect the prior generation on confirm',async t=>{
 const p=await setup(t);await calculate(p);await p.locator('[data-im-action="set_horizon"]').selectOption('3m');
 const fresh='im-workspace-generation:99999999-9999-4999-8999-999999999999';
 await p.evaluate(n=>{const old=handle.getState().source_reference;document.querySelectorAll('[data-im-generation]').forEach(x=>x.setAttribute('data-im-generation',n));handle.replaceSource(n,old);},fresh);
 await p.locator('[data-im-scenario-action="confirm_context"]').click();const state=await p.evaluate(()=>handle.getState());
 assert.equal(state.horizon,'3m');assert.equal(state.source_reference,fresh);assert.equal(await p.locator('#im-scenario-local').inputValue(),'5');
});
test('a pending confirmation does not allow pin or another context to overwrite its origin',async t=>{
 const p=await setup(t);await calculate(p);await p.locator('[data-im-action="set_horizon"]').selectOption('3m');
 assert.equal((await p.evaluate(()=>handle.dispatch({type:'pin',market_id:'JP'}))).ok,false);
 assert.equal((await p.evaluate(()=>handle.dispatch({type:'set_basis',currency_basis:'local'}))).ok,false);
 await p.locator('[data-im-scenario-action="confirm_context"]').click();const state=await p.evaluate(()=>handle.getState());
 assert.equal(state.currency_basis,'usd_unhedged');assert.deepEqual(state.compare_markets,[]);
});
test('successful confirm leaves focus on a visible control',async t=>{
 const p=await setup(t);await calculate(p);await p.locator('[data-im-action="set_horizon"]').selectOption('3m');
 await p.locator('[data-im-scenario-action="confirm_context"]').click();
 assert.equal(await p.evaluate(()=>document.activeElement!==document.body&&!document.activeElement.closest('[hidden]')),true);
});
test('nested workspace events cannot edit the owning workspace draft',async t=>{
 const p=await setup(t);await calculate(p);
 await p.evaluate(()=>{const nested=document.createElement('section');nested.setAttribute('data-im-workspace','');nested.innerHTML='<input data-im-scenario-field="local" value="99">';document.querySelector('[data-im-history-panel]').appendChild(nested);nested.firstElementChild.dispatchEvent(new Event('input',{bubbles:true}));});
 assert.equal(await p.locator('#im-scenario-local').inputValue(),'5');assert.equal(await p.locator('[data-im-scenario-result]').isVisible(),true);
});
