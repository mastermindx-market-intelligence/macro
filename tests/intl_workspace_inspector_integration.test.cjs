'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
// Exercise the actual records -> Overview -> Inspector -> Jinja shell seam.
// All attestations remain explicitly synthetic, as in the source-owner tests.
const markup = execFileSync('python3', ['-c', `
import importlib.util
from pathlib import Path
p=Path('tests/test_intl_inspector_mount.py')
s=importlib.util.spec_from_file_location('actual_inspector_seam',p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
project,_,_=m.supplied.__wrapped__()
html,_=m.render_international_pages(m.ActualShell(),{'intl_workspace':m.workspace(project)})
print(html)
`], {cwd:root, encoding:'utf8'});
const assets = ['intl_workspace_state.js','intl_library_search.js','intl_workspace.js','intl_workspace_entry.js'];
async function withPage(run) {
  const browser = await chromium.launch({headless:true, ...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL ? {channel:process.env.PLAYWRIGHT_CHROMIUM_CHANNEL} : {})});
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(2500);
    await page.route('http://inspector.test/**', r => r.fulfill({contentType:'text/html',body:'<!doctype html><html lang="en" data-lang="en"><body>'+markup+'</body></html>'}));
    await page.goto('http://inspector.test/intl.html');
    for (const asset of assets) await page.addScriptTag({content:readFileSync(path.join(root,'templates',asset),'utf8')});
    await run(page);
  } finally { await browser.close(); }
}
function trigger(page) { return page.locator('[data-im-inspector-trigger]:visible').first(); }

test('actual server-rendered Inspector opens through entry and preserves financial facts and original nodes', async () => {
  await withPage(async page => {
    const before = await page.evaluate(() => {
      const root=document.querySelector('[data-im-workspace]');
      window.__handle=IntlWorkspace.mountIntlWorkspace(root,JSON.parse(root.querySelector('[data-im-config]').textContent));
      const origin=[...root.querySelectorAll('[data-im-inspector-trigger]')].find(n=>n.getClientRects().length&&!n.closest('[hidden]'));
      window.__origin=origin; window.__article=origin.parentElement.querySelector('[data-im-inspector-payload]');
      window.__parent=__article.parentNode; window.__listener=0;
      __article.addEventListener('synthetic-listener-proof',()=>{window.__listener++});
      return {state:__handle.getState(),url:location.href,history:history.length,values:[...__article.querySelectorAll('[data-im-inspector-metric]')].map(n=>n.textContent)};
    });
    await trigger(page).click();
    assert.equal(await page.locator('dialog').evaluate(n=>n.open),true);
    const open = await page.evaluate(() => ({same:document.querySelector('dialog [data-im-inspector-payload]')===__article,state:__handle.getState(),url:location.href,history:history.length,values:[...__article.querySelectorAll('[data-im-inspector-metric]')].map(n=>n.textContent)}));
    assert.equal(open.same,true);
    assert.deepEqual({...open,same:undefined},{...before,same:undefined});
    assert.match(await page.locator('dialog').textContent(),/Nikkei 225/);
    assert.equal(await page.locator('dialog [data-im-inspector-value]').count(),6);
    await page.locator('dialog [data-im-inspector-action="close"]').click();
    const after=await page.evaluate(()=>{__article.dispatchEvent(new Event('synthetic-listener-proof'));return {same:__article.parentNode===__parent,focus:document.activeElement===__origin,listener:__listener,open:document.querySelector('dialog').open}});
    assert.deepEqual(after,{same:true,focus:true,listener:1,open:false});
  });
});

test('failed real workspace history transaction preserves the modal, successful basis change closes it', async () => {
  await withPage(async page => {
    await trigger(page).click();
    assert.equal(await page.locator('dialog').evaluate(n=>n.open),true);
    const result=await page.evaluate(()=>{
      const root=document.querySelector('[data-im-workspace]'), h=IntlWorkspace.mountIntlWorkspace(root,JSON.parse(root.querySelector('[data-im-config]').textContent));
      const original=history.pushState; const article=root.querySelector('dialog [data-im-inspector-payload]'); const state=h.getState();
      history.pushState=()=>{throw Error('synthetic history failure')};
      let failed;try{failed=h.dispatch({type:'set_basis',currency_basis:'local'})}finally{history.pushState=original}
      const rollback={failed:failed.ok,state:h.getState(),same:root.querySelector('dialog [data-im-inspector-payload]')===article,open:root.querySelector('dialog').open};
      const success=h.dispatch({type:'set_basis',currency_basis:'local'});
      return {state,rollback,success:success.ok,closed:!root.querySelector('dialog').open,basis:h.getState().currency_basis};
    });
    assert.equal(result.rollback.failed,false);
    assert.deepEqual(result.rollback.state,result.state);
    assert.equal(result.rollback.same,true);assert.equal(result.rollback.open,true);
    assert.equal(result.success,true);assert.equal(result.closed,true);assert.equal(result.basis,'local');
  });
});
