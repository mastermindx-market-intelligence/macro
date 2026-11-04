'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { createHash } = require('node:crypto');
const { spawnSync } = require('node:child_process');
const { chromium } = require('playwright');

const root = path.join(__dirname, '..');
const generation = 'im-workspace-generation:3829962a-245d-41a2-ac31-f045b8c95dfa';
const config = { markets:['JP','KR','ZZ'], horizons:['1m','3m'], bases:['local','usd_unhedged'],
  default_horizon:'1m', default_basis:'usd_unhedged', source_reference:generation,
  anchor_ids:['research-home'], library_group_ids:[] };

function panel(view, horizon, basis) {
  const id = `im-${view}-${horizon}-${basis}`;
  const content = view === 'overview' ? '<p>Immediate country research</p>' :
    `<nav><a data-gs-select-market="US" data-gs-open="dossier" href="?view=dossier&market=US">United States</a></nav><div data-gs-market-scope><article data-gs-market="JP" data-gs-market-default id="${id}-JP"><h3>Japan 日本</h3><p data-exact-value>3.17% · 2026-10-30</p><details><summary>Exact evidence</summary><p>Qualified for this calculation window</p></details></article><article data-gs-market="KR" id="${id}-KR" hidden><h3>Korea 韩国</h3><p data-exact-value>Unavailable: not_supplied</p></article><article data-gs-market="US" id="${id}-US" hidden><h3>United States</h3><p>Catalogue only: outside configured research coverage</p></article></div>`;
  return `<section data-im-panel data-view="${view}" data-horizon="${horizon}" data-basis="${basis}" data-return-basis="price" data-source="" data-im-generation="${generation}" id="${id}" aria-labelledby="${id}-title"><h2 id="${id}-title">${view}</h2>${content}</section>`;
}

const panels = ['overview','dossier','scanner','coverage'].flatMap(view => config.horizons.flatMap(horizon => config.bases.map(basis => panel(view,horizon,basis)))).join('');
const initial = `<!doctype html><html lang="en"><head><meta charset="utf-8"><style>[hidden]{display:none!important}.l-zh{display:none}html[lang=zh] .l-en{display:none}html[lang=zh] .l-zh{display:inline}</style></head><body><main data-im-workspace data-im-mode="macro" data-im-binding-version="2"><h1 data-im-heading id="research-home">Research</h1><p data-im-issues></p>${['overview','dossier','scanner','coverage'].map(view=>`<button data-im-action="set_view" data-im-view="${view}">${view}</button>`).join('')}<p data-im-unavailable>No matching payload</p>${panels}</main><script src="/state.js"></script><script src="/controller.js"></script><script>window.config=${JSON.stringify(config)};window.handle=IntlWorkspace.mountIntlWorkspace(document.querySelector('[data-im-workspace]'),window.config);</script></body></html>`;
const generated = spawnSync(process.env.PYTHON || 'python3', ['-c', 'import sys,json; from lib.intl_workspace_fragments import partition_workspace; p=partition_workspace(sys.stdin.read()); print(json.dumps({"html":p.html,"assets":{k:v.decode() for k,v in p.assets.items()}}))'], {cwd:root,input:initial,encoding:'utf8',maxBuffer:4*1024*1024});
assert.equal(generated.status,0,generated.stderr);
const fixture = JSON.parse(generated.stdout);
let browser, server, origin;
let html = fixture.html;
let assets = {...fixture.assets};

test.before(async () => {
  server = http.createServer((req,res) => {
    const name = new URL(req.url,'http://localhost').pathname.slice(1);
    const body = name === 'state.js' ? fs.readFileSync(path.join(root,'templates/intl_workspace_state.js')) :
      name === 'controller.js' ? fs.readFileSync(path.join(root,'templates/intl_workspace.js')) :
      name === 'intl.html' ? html : assets[name];
    res.writeHead(body === undefined ? 404 : 200, {'Content-Type':name.endsWith('.json')?'application/json':name.endsWith('.js')?'application/javascript':'text/html','Cache-Control':'no-store'});
    res.end(body === undefined ? 'Missing' : body);
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  origin = `http://127.0.0.1:${server.address().port}`;
  browser = await chromium.launch({headless:true});
});
test.beforeEach(()=>{ html=fixture.html; assets={...fixture.assets}; });
test.after(async()=>{ await browser?.close(); if(server) await new Promise(resolve=>server.close(resolve)); });

async function visit(query='') {
  const page=await browser.newPage();
  await page.goto(`${origin}/intl.html${query}`);
  assert.equal(await page.locator('[data-im-workspace]').getAttribute('data-im-enhanced'),'true');
  return page;
}
async function dispatch(page, action) { return page.evaluate(action=>handle.dispatch(action), action); }
async function ready(page, view) {
  await page.waitForFunction(view=>!!document.querySelector(`[data-im-panel][data-view="${view}"]:not([hidden])[data-im-deferred-state="ready"]`), view);
  return page.locator(`[data-im-panel][data-view="${view}"]:visible`);
}
function replacePayload(name, mutate) {
  const value=JSON.parse(assets[name]);
  mutate(value);
  assets[name]=JSON.stringify(value);
  const sha=createHash('sha256').update(assets[name]).digest('hex');
  html=html.replace(/(<script type="application\/json" data-im-deferred-manifest>)(.*?)(<\/script>)/g,(_,start,text,end)=>{
    const manifest=JSON.parse(text);
    for(const ref of Object.values(manifest.variants)) if(ref.url===name) Object.assign(ref,{sha256:sha,bytes:Buffer.byteLength(assets[name])});
    return start+JSON.stringify(manifest).replace(/</g,'\\u003c')+end;
  });
}

test('country rest makes no fragment request; dossiers preserve values and reuse context bundle',async()=>{
  const page=await visit();
  try {
    assert.equal(await page.evaluate(()=>performance.getEntriesByType('resource').filter(r=>r.name.includes('/intl-workspace/')).length),0);
    assert.equal(await page.locator('[data-view="dossier"] [data-gs-market]').count(),0);
    await dispatch(page,{type:'set_view',view:'dossier'});
    let active=await ready(page,'dossier');
    assert.equal(await active.locator('[data-gs-market]').count(),1);
    assert.equal(await active.locator('[data-exact-value]').innerText(),'3.17% · 2026-10-30');
    assert.equal(await active.locator('[data-gs-select-market="US"]').getAttribute('aria-disabled'),'true');
    assert.equal(await active.locator('[data-gs-select-market="US"]').getAttribute('href'),null);
    await active.locator('summary').click();
    await dispatch(page,{type:'set_horizon',horizon:'3m'}); await ready(page,'dossier');
    await dispatch(page,{type:'set_basis',currency_basis:'local'}); await ready(page,'dossier');
    assert.equal(await page.evaluate(()=>performance.getEntriesByType('resource').filter(r=>r.name.includes('dossier-JP.json')).length),1);
    await dispatch(page,{type:'select_market',market_id:'KR'}); active=await ready(page,'dossier');
    assert.equal(await active.locator('[data-exact-value]').innerText(),'Unavailable: not_supplied');
    await dispatch(page,{type:'select_market',market_id:'JP'});
    await dispatch(page,{type:'set_horizon',horizon:'1m'});
    await dispatch(page,{type:'set_basis',currency_basis:'usd_unhedged'});
    active=await ready(page,'dossier');
    assert.equal(await active.locator('details').getAttribute('open'),'');
  } finally { await page.close(); }
});

test('deep links require emitted market membership and Back/Forward preserve the chosen view',async()=>{
  const page=await visit('?view=dossier&market=KR');
  try {
    let active=await ready(page,'dossier');
    assert.equal(await active.locator('[data-gs-market]').getAttribute('data-gs-market'),'KR');
    await dispatch(page,{type:'set_view',view:'coverage'}); await ready(page,'coverage');
    await page.goBack(); active=await ready(page,'dossier');
    assert.equal(await active.locator('[data-gs-market]').getAttribute('data-gs-market'),'KR');
    await page.goForward(); await ready(page,'coverage');
    await page.goto(`${origin}/intl.html?view=dossier&market=ZZ`); active=await ready(page,'dossier');
    assert.equal((await page.evaluate(()=>handle.getState())).selected_market,null);
    assert.equal(await active.locator('[data-gs-market]').getAttribute('data-gs-market'),'JP');
  } finally { await page.close(); }
});

test('late dossier responses cannot overwrite a newer Coverage selection',async()=>{
  const page=await visit();
  try {
    await page.route('**/dossier-JP.json*',async route=>{await new Promise(resolve=>setTimeout(resolve,300));try{await route.fulfill({body:assets['assets/intl-workspace/dossier-JP.json'],contentType:'application/json'});}catch{}});
    await dispatch(page,{type:'set_view',view:'dossier'});
    await page.waitForFunction(()=>!!document.querySelector('[data-im-deferred-state="loading"]'));
    await dispatch(page,{type:'set_view',view:'coverage'}); await ready(page,'coverage');
    await page.waitForTimeout(350);
    assert.equal((await page.evaluate(()=>handle.getState())).view,'coverage');
    assert.equal(await page.locator('[data-view="dossier"] [data-gs-market]').count(),0);
  } finally { await page.close(); }
});

test('network failure offers a localized retry and returns keyboard focus after loading',async()=>{
  const page=await visit();
  try {
    await page.evaluate(()=>document.documentElement.lang='zh');
    await page.route('**/dossier-JP.json*',route=>route.fulfill({status:404,body:'Missing'}));
    await dispatch(page,{type:'set_view',view:'dossier'});
    const failed=page.locator('[data-im-panel][data-view="dossier"]:visible');
    await page.waitForFunction(()=>!!document.querySelector('[data-im-deferred-state="error"]'));
    assert.match(await failed.locator('[data-im-deferred-status]').innerText(),/您的选择已保留/);
    await page.unroute('**/dossier-JP.json*');
    const retry=failed.locator('[data-im-deferred-retry]');await retry.focus();await page.keyboard.press('Enter');
    await ready(page,'dossier');
    assert.equal(await page.evaluate(()=>document.activeElement.tagName),'H2');
  } finally { await page.close(); }
});

test('publication rollover rejects changed bytes instead of mixing snapshots',async()=>{
  assets['assets/intl-workspace/dossier-JP.json']=assets['assets/intl-workspace/dossier-JP.json'].replace('3.17%','9.99%');
  const page=await visit('?view=dossier&market=JP');
  try {
    await page.waitForFunction(()=>!!document.querySelector('[data-im-deferred-state="changed"]'));
    assert.equal(await page.locator('[data-view="dossier"] [data-exact-value]').count(),0);
    assert.equal(await page.locator('[data-im-deferred-reload]:visible').count(),1);
  } finally { await page.close(); }
});

for (const [name,mutate] of Object.entries({
  generation:bundle=>{bundle.generation=generation.replace('3829962a','4829962a');},
  context:bundle=>{Object.values(bundle.fragments)[0].horizon='12m';},
  membership:bundle=>{Object.values(bundle.fragments)[0].markets=['KR'];},
  duplicate:bundle=>{const item=Object.values(bundle.fragments)[0];item.html+=item.html;},
  executable:bundle=>{const item=Object.values(bundle.fragments)[0];item.html=item.html.replace('</section>','<script>window.unwanted=true</script></section>');},
  eventHandler:bundle=>{const item=Object.values(bundle.fragments)[0];item.html=item.html.replace('<h3>','<h3 onclick="window.unwanted=true">');}
})) test(`bound but invalid ${name} fragment fails closed`,async()=>{
  replacePayload('assets/intl-workspace/dossier-JP.json',mutate);
  const page=await visit('?view=dossier&market=JP&basis=local');
  try {
    await page.waitForFunction(()=>!!document.querySelector('[data-im-deferred-state="changed"]'));
    assert.equal(await page.locator('[data-view="dossier"] [data-gs-market]').count(),0);
    assert.equal(await page.evaluate(()=>window.unwanted),undefined);
  } finally { await page.close(); }
});

test('failed history transaction starts no request and leaves the previous selection intact',async()=>{
  const page=await visit();
  try {
    await page.evaluate(()=>{history.pushState=()=>{throw new Error('test history refusal');};});
    assert.equal((await dispatch(page,{type:'set_view',view:'dossier'})).ok,false);
    await page.waitForTimeout(80);
    assert.equal((await page.evaluate(()=>handle.getState())).view,'overview');
    assert.equal(await page.evaluate(()=>performance.getEntriesByType('resource').filter(r=>r.name.includes('/intl-workspace/')).length),0);
  } finally { await page.close(); }
});

test('a failure immediately after insertion restores a visible retry path',async()=>{
  const page=await visit();
  try {
    await page.evaluate(()=>{
      const panel=document.querySelector('[data-view="dossier"][data-horizon="1m"][data-basis="usd_unhedged"]');
      const original=panel.replaceChildren;
      panel.replaceChildren=function(...nodes){const result=original.apply(this,nodes);panel.replaceChildren=original;throw new Error('one insertion failure');};
    });
    await dispatch(page,{type:'set_view',view:'dossier'});
    await page.waitForFunction(()=>!!document.querySelector('[data-im-deferred-state="error"]'));
    assert.equal(await page.locator('[data-im-deferred-retry]:visible').count(),1);
    assert.equal(await page.locator('[data-view="dossier"] [data-gs-market]').count(),0);
    await page.locator('[data-im-deferred-retry]:visible').click();await ready(page,'dossier');
  } finally { await page.close(); }
});

test('a source-cleanup exception rolls back the actual source and attached dossier',async()=>{
  const page=await visit('?view=dossier&market=JP');
  try {
    await ready(page,'dossier');
    const before=await page.evaluate(()=>handle.getState());
    await page.evaluate(()=>{
      const panel=document.querySelector('[data-view="dossier"]:not([hidden])');const original=panel.replaceChildren;
      panel.replaceChildren=function(...nodes){const result=original.apply(this,nodes);panel.replaceChildren=original;throw new Error('one cleanup failure');};
    });
    const result=await page.evaluate(source=>handle.replaceSource(source,config.source_reference),generation.replace('3829962a','4829962a'));
    assert.equal(result.ok,false);
    assert.deepEqual(await page.evaluate(()=>handle.getState()),before);
    assert.equal(await page.locator('[data-view="dossier"]:visible [data-exact-value]').innerText(),'3.17% · 2026-10-30');
  } finally { await page.close(); }
});

test('evicted dossier nodes are collectable and repeated context changes keep live DOM bounded',async()=>{
  const page=await visit('?view=dossier&market=JP');
  try {
    await ready(page,'dossier');
    await page.evaluate(()=>window.evicted=new WeakRef(document.querySelector('[data-im-panel]:not([hidden]) [data-gs-market]')));
    await dispatch(page,{type:'set_view',view:'coverage'});await ready(page,'coverage');
    const cdp=await page.context().newCDPSession(page);
    await cdp.send('HeapProfiler.collectGarbage');await cdp.send('HeapProfiler.collectGarbage');
    assert.equal(await page.evaluate(()=>!!window.evicted.deref()),false);
    for(let i=0;i<18;i++) {
      await dispatch(page,{type:'set_view',view:i%2?'dossier':'scanner'});
      await dispatch(page,{type:'set_horizon',horizon:i%3?'1m':'3m'});
      await ready(page,i%2?'dossier':'scanner');
      assert.ok(await page.locator('[data-im-panel][data-im-deferred-state="ready"]').count()<=1);
      assert.ok(await page.locator('*').count()<700);
    }
  } finally { await page.close(); }
});

test('destroy and replaceSource invalidate pending requests without late DOM writes',async()=>{
  const page=await visit();
  try {
    await page.route('**/dossier-JP.json*',async route=>{await new Promise(resolve=>setTimeout(resolve,250));try{await route.fulfill({body:assets['assets/intl-workspace/dossier-JP.json'],contentType:'application/json'});}catch{}});
    await dispatch(page,{type:'set_view',view:'dossier'});
    await page.waitForFunction(()=>!!document.querySelector('[data-im-deferred-state="loading"]'));
    assert.equal(await page.evaluate(()=>handle.destroy()),true);
    await page.waitForTimeout(300);
    assert.equal(await page.locator('[data-view="dossier"] [data-gs-market]').count(),0);
    await page.evaluate(()=>window.handle=IntlWorkspace.mountIntlWorkspace(document.querySelector('[data-im-workspace]'),config));
    await page.waitForFunction(()=>!!document.querySelector('[data-im-deferred-state="loading"]'));
    const result=await page.evaluate(source=>handle.replaceSource(source,config.source_reference),generation.replace('3829962a','4829962a'));
    assert.equal(result.ok,true);
    await page.waitForTimeout(300);
    assert.equal(await page.locator('[data-view="dossier"] [data-gs-market]').count(),0);
  } finally { await page.close(); }
});
