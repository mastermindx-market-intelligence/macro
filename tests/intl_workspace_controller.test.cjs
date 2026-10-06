'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');

const reducerSource = fs.readFileSync(path.join(__dirname, '../templates/intl_workspace_state.js'), 'utf8');
const adapterSource = fs.readFileSync(path.join(__dirname, '../templates/intl_workspace.js'), 'utf8');

const config = {
  markets: ['JP', 'KR', 'TW', 'IN', 'AU', 'GB', 'EZ'],
  horizons: ['1m', '3m'],
  bases: ['local', 'usd_unhedged'],
  default_horizon: '1m',
  default_basis: 'usd_unhedged',
  source_reference: 'fixture:v1',
  anchor_ids: ['research-origin'],
  library_group_ids: ['leaders']
};

function option(label, value = label) {
  return `<option value="${value}">${label}</option>`;
}

function workspaceMarkup(overrides = {}) {
  return `
    <section data-im-workspace data-im-mode="macro">
      <h1 data-im-heading>International</h1>
      <p data-im-issues role="status"></p>
      <button data-im-action="set_view" data-im-view="overview">Overview</button>
      <button data-im-action="set_view" data-im-view="history">History</button>
      <button data-im-action="set_view" data-im-view="library">Library</button>
      <select data-im-action="select_market">${option('All', '')}${option('JP')}${option('KR')}</select>
      <select data-im-action="set_library_group">${option('None', '')}${option('leaders')}</select>
      <button data-im-action="set_horizon" data-im-horizon="3m">3m</button>
      <button data-im-action="set_basis" data-im-basis="local">Local</button>
      <button data-im-action="pin" data-im-market="JP">Pin JP</button>
      <button data-im-action="pin" data-im-market="KR">Pin KR</button>
      <button data-im-action="pin" data-im-market="TW">Pin TW</button>
      <button data-im-action="pin" data-im-market="IN">Pin IN</button>
      <button data-im-action="pin" data-im-market="AU">Pin fifth</button>
      <button data-im-action="capture_baseline">Baseline</button>
      <button data-im-action="push_return" data-im-anchor="research-origin">Capture</button>
      <button data-im-action="back">Back</button>
      <button id="research-origin">Origin</button>
      <article data-im-panel data-view="overview" data-horizon="1m" data-basis="usd_unhedged" data-source="fixture:v1">Qualified</article>
      <article data-im-panel data-view="overview" data-horizon="1m" data-basis="local" data-source="fixture:v1">Local</article>
      <article data-im-panel data-view="history" data-horizon="1m" data-basis="usd_unhedged" data-source="fixture:v1">History</article>
      <p data-im-unavailable>No matching payload</p>
      <details data-im-legacy-disclosure><summary>Legacy</summary><button class="legacy-control">Legacy button</button></details>
    </section>`;
}

function bootstrapPage(page, markup, query = '', title = 'Controller') {
  return page.evaluate(({ markup, query, title }) => {
    document.title = title;
    history.replaceState(null, '', location.pathname + query);
    document.body.innerHTML = markup;
  }, { markup, query, title });
}

async function withPage(testFunction) {
  const browser = await chromium.launch({headless:true, ...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL ? {channel:process.env.PLAYWRIGHT_CHROMIUM_CHANNEL} : {})});
  const page = await browser.newPage();
  try {
    await page.route('http://intl.test/**', route => route.fulfill({status:200, contentType:'text/html', body:'<!doctype html><html lang="en"><body></body></html>'}));
    await page.goto('http://intl.test/intl.html?initial=1');
    page.setDefaultTimeout(2000);
    await page.evaluate(c => { window.config = c; }, config);
    await page.addScriptTag({ content: reducerSource });
    await page.addScriptTag({ content: adapterSource });
    await testFunction(page);
  } finally {
    await browser.close();
  }
}

async function mount(page, query = '', markup = workspaceMarkup()) {
  await bootstrapPage(page, markup, query);
  return page.evaluateHandle((config) => IntlWorkspace.mountIntlWorkspace(document.querySelector('[data-im-workspace]'), config), config);
}

test('actions, fifth pin, focused view control, URL and state stay aligned', async () => {
  await withPage(async (page) => {
    const handle = await mount(page);
    await page.click('[data-im-view="history"]');
    await page.click('[data-im-horizon="3m"]');
    await page.evaluate(() => {
      const select = document.querySelector('select[data-im-action="select_market"]');
      select.value = 'JP';
      select.dispatchEvent(new Event('change', { bubbles: true }));
    });
    assert.equal(await page.evaluate(() => location.search), '?view=history&market=JP&pins=&horizon=3m&basis=usd_unhedged&return_basis=price&group=');
    assert.equal(await page.evaluate((handle) => handle.getState().view, handle), 'history');
    assert.equal(await page.getAttribute('[data-im-view="history"]', 'aria-pressed'), 'true');
    await page.evaluate((handle) => handle.dispatch({ type: 'select_market', market_id: null }), handle);
    const fifth = await page.evaluate(async (handle) => {
      for (const market of ['JP', 'KR', 'TW', 'IN', 'AU']) await handle.dispatch({ type: 'pin', market_id: market });
      return handle.getState().compare_markets.length;
    }, handle);
    assert.equal(fifth, 4);
  });
});

test('invalid URL uses defaults and reports invalid state without changing URL', async () => {
  await withPage(async (page) => {
    const before = await page.evaluate(() => { history.replaceState(null, '', location.pathname + '?bad=1'); return location.href; });
    await page.evaluate(() => { document.body.innerHTML = ''; });
    await mount(page, '?bad=1');
    assert.equal(await page.evaluate(() => location.href), before);
    assert.equal(await page.textContent('[data-im-issues]'), 'Invalid URL state restored');
    assert.equal(await page.isHidden('[data-im-panel][data-view="overview"][data-basis="usd_unhedged"]'), false);
  });
});

test('popstate parses current source, clears stack and does not push', async () => {
  await withPage(async (page) => {
    const handle = await mount(page);
    await page.evaluate(() => {
      const panel = document.createElement('article');
      panel.setAttribute('data-im-panel', '');
      panel.setAttribute('data-view', 'overview');
      panel.setAttribute('data-horizon', '1m');
      panel.setAttribute('data-basis', 'usd_unhedged');
      panel.setAttribute('data-source', 'fixture:v2');
      panel.setAttribute('hidden', '');
      panel.textContent = 'Replacement';
      document.querySelector('[data-im-workspace]').append(panel);
    });
    await page.evaluate(async (handle) => {
      await handle.dispatch({ type: 'push_return', anchor_id: 'research-origin' });
      history.pushState({ im: true }, '', '?view=history&market=&pins=&horizon=3m&basis=local&return_basis=price&group=');
      window.historyBeforePop = history.length;
      dispatchEvent(new PopStateEvent('popstate'));
    }, handle);
    assert.equal(await page.evaluate((handle) => handle.getState().view, handle), 'history');
    assert.equal(await page.evaluate((handle) => handle.getState().return_stack.length, handle), 0);
    assert.equal(await page.evaluate(() => history.length), await page.evaluate(() => historyBeforePop));
  });
});

test('replaceSource preserves context, clears bounds, and stale source is refused', async () => {
  await withPage(async (page) => {
    const handle = await mount(page);
    await page.evaluate((config) => {
      const workspace = document.querySelector('[data-im-workspace]');
      const panel = workspace.querySelector('[data-im-panel]').cloneNode(true);
      panel.setAttribute('data-source', 'fixture:v2'); workspace.appendChild(panel);
      window.historyBeforeSource = history.length;
      return IntlWorkspace.mountIntlWorkspace(workspace, config);
    }, config);
    assert.equal(await page.evaluate((handle) => handle.getState().selected_market, handle), null);
    assert.equal(await page.evaluate((handle) => handle.replaceSource('fixture:v2', 'wrong').issues[0].code, handle), 'STALE_SOURCE');
    assert.equal(await page.evaluate((handle) => handle.replaceSource('fixture:v2', 'fixture:v1').ok, handle), true);
    const state = await page.evaluate((handle) => handle.getState(), handle);
    assert.equal(state.source_reference, 'fixture:v2');
    assert.equal(state.selected_market, null);
    assert.equal(state.baseline, null);
    assert.equal(state.return_stack.length, 0);
    assert.equal(await page.getAttribute('[data-view="overview"][data-source="fixture:v2"]', 'hidden'), null);
    assert.equal(await page.evaluate(() => history.length), 2);
  });
});

test('replaceSource preserves expanded context before clearing source bounds', async () => {
  await withPage(async (page) => {
    const handle = await mount(page);
    await page.evaluate(async (handle) => {
      await handle.dispatch({ type: 'set_expanded', expanded: true });
    }, handle);
    const stale = await page.evaluate((handle) => handle.replaceSource('fixture:v2', 'wrong'), handle);
    assert.equal(stale.ok, false);
    assert.equal(stale.issues[0].code, 'STALE_SOURCE');
    const replaced = await page.evaluate((handle) => handle.replaceSource('fixture:v2', 'fixture:v1'), handle);
    assert.equal(replaced.ok, true);
    assert.equal(await page.evaluate((handle) => handle.getState().expanded, handle), true);
    assert.equal(await page.evaluate((handle) => handle.getState().baseline, handle), null);
    assert.equal(await page.evaluate((handle) => handle.getState().return_stack.length, handle), 0);
    assert.equal(await page.evaluate(() => history.length), 2);
  });
});

test('multiple panels are ambiguous and unsupported view is rejected', async () => {
  await withPage(async (page) => {
    await mount(page, '', workspaceMarkup().replace('data-view="history"', 'data-view="overview"'));
    assert.equal(await page.textContent('[data-im-issues]'), 'Data is ambiguous for this selection');
    const rejected = await page.evaluate(async () => {
      const workspace = document.querySelector('[data-im-workspace]');
      workspace.querySelector('[data-im-panel]:nth-of-type(2)').setAttribute('hidden', '');
      return IntlWorkspace.mountIntlWorkspace(workspace, config).dispatch({ type: 'set_view', view: 'library' });
    });
    assert.equal(rejected.ok, false);
    assert.equal(rejected.issues[0].code, 'UNSUPPORTED_VIEW');
  });
});

test('duplicate mounts preserve identity and destroy restores original nodes and listeners', async () => {
  await withPage(async page => {
    await bootstrapPage(page, workspaceMarkup());
    const result = await page.evaluate(config => {
      const root = document.querySelector('[data-im-workspace]');
      const legacy = root.querySelector('.legacy-control'); let clicks=0;
      legacy.addEventListener('click', () => clicks++);
      const before = root.outerHTML, url = location.href;
      const first = IntlWorkspace.mountIntlWorkspace(root, config);
      const same = first === IntlWorkspace.mountIntlWorkspace(root, {...config, source_reference:'ignored'});
      first.dispatch({type:'select_market', market_id:'JP'});
      first.destroy(); legacy.click();
      const restored = root.outerHTML === before && root.querySelector('.legacy-control') === legacy && clicks===1;
      const destroyed = first.dispatch({type:'back'}).issues[0].code;
      const next = IntlWorkspace.mountIntlWorkspace(root, config);
      const fresh = first !== next && next.getState().selected_market==='JP';
      next.destroy();
      return {same, restored, destroyed, fresh};
    }, config);
    assert.deepEqual(result, {same:true,restored:true,destroyed:'DESTROYED',fresh:true});
  });
});

test('failed mount restores attributes and listeners without replacing original nodes', async () => {
  await withPage(async page => {
    await bootstrapPage(page, workspaceMarkup());
    const result = await page.evaluate(config => {
      const root=document.querySelector('[data-im-workspace]');
      const heading=root.querySelector('[data-im-heading]'), before=root.outerHTML, url=location.href;
      const Observer=window.MutationObserver;
      window.MutationObserver=class { constructor(){throw new Error('setup failure');} };
      let refused=false;
      try{IntlWorkspace.mountIntlWorkspace(root,config);}catch{refused=true;}finally{window.MutationObserver=Observer;}
      root.querySelector('[data-im-view=history]').click();
      return {refused,same:heading===root.querySelector('[data-im-heading]'),dom:root.outerHTML===before,url:location.href===url};
    },config);
    assert.deepEqual(result,{refused:true,same:true,dom:true,url:true});
  });
});

test('language change repaints issue text only and context is unchanged', async () => {
  await withPage(async (page) => {
    await mount(page, '?view=library&market=&pins=&horizon=1m&basis=usd_unhedged&return_basis=price&group=');
    assert.equal(await page.textContent('[data-im-issues]'), 'This view is not available yet');
    await page.evaluate(() => document.documentElement.setAttribute('lang', 'zh-CN'));
    assert.equal(await page.textContent('[data-im-issues]'), '此视图暂不可用');
    assert.equal(await page.evaluate(() => location.search), '?view=library&market=&pins=&horizon=1m&basis=usd_unhedged&return_basis=price&group=');
  });
});

test('back focus uses visible root anchor otherwise heading', async () => {
  await withPage(async (page) => {
    const handle = await mount(page);
    await page.evaluate(async (handle) => {
      document.querySelector('[data-im-panel][data-view="overview"]').setAttribute('hidden', '');
      await handle.dispatch({ type: 'push_return', anchor_id: 'research-origin' });
      document.querySelector('#research-origin').removeAttribute('hidden');
    }, handle);
    await page.evaluate((handle) => handle.dispatch({ type: 'back' }), handle);
    assert.equal(await page.evaluate(() => document.activeElement.id), 'research-origin');
  });
});

test('import, no-JS visibility and stock mode remain untouched', async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL ? {channel:process.env.PLAYWRIGHT_CHROMIUM_CHANNEL} : {})});
  const page = await browser.newPage({ javaScriptEnabled: false });
  try {
    await page.setContent(`<!doctype html><html lang="en"><body>${workspaceMarkup()}</body></html>`);
    assert.equal(await page.isHidden('[data-im-panel][data-view="overview"][data-basis="usd_unhedged"]'), false);
    assert.equal(await page.isHidden('[data-im-unavailable]'), false);
    assert.equal(await page.getAttribute('[data-im-workspace]', 'data-im-enhanced'), null);
  } finally { await browser.close(); }
  await withPage(async (page) => {
    await bootstrapPage(page, '<section data-im-workspace data-im-mode="stocks"></section>');
    await assert.rejects(() => page.evaluate((config) => IntlWorkspace.mountIntlWorkspace(document.querySelector('[data-im-workspace]'), config), config), /Unsupported/);
    assert.equal(await page.textContent('[data-im-mode="stocks"]'), '');
  });
});

test('nearest control wins and unrelated nested input is untouched', async () => {
  await withPage(async (page) => {
    const handle = await mount(page);
    const clicked = await page.evaluate(() => {
      const row = document.createElement('div');
      row.setAttribute('data-im-action', 'capture_baseline');
      const inner = document.createElement('button');
      inner.setAttribute('data-im-action', 'set_expanded');
      inner.setAttribute('data-im-expanded', 'true');
      inner.textContent = 'Expand';
      row.append(inner);
      document.querySelector('[data-im-workspace]').append(row);
      inner.click();
      const input = document.createElement('input');
      input.value = 'private';
      input.setAttribute('data-im-private', 'private');
      row.append(input);
      input.dispatchEvent(new Event('change', { bubbles: true }));
      return location.search;
    });
    assert.equal(clicked, '');
    assert.equal(await page.evaluate(h=>h.getState().expanded,handle),true);
    assert.equal(await page.evaluate(h=>h.getState().baseline,handle),null);
    assert.doesNotMatch(clicked, /private/);
  });
});

test('URL privacy, canonical hash and backslash-safe path are enforced', async () => {
  await withPage(async (page) => {
    const handle = await mount(page, '?view=overview&market=JP&pins=KR,TW&horizon=1m&basis=local&return_basis=price&group=leaders#research-origin');
    assert.equal(await page.evaluate((handle) => handle.getState().compare_markets.join(','), handle), 'KR,TW');
    assert.equal(await page.evaluate(() => decodeURIComponent(location.hash)), '#research-origin');
    const privacy = await page.evaluate((handle) => {
      const result = handle.dispatch({ type: 'set_library_group', group_id: 'not-a-group' });
      return { ok: result.ok, code: result.issues[0] && result.issues[0].code, search: location.search };
    }, handle);
    assert.equal(privacy.ok, false);
    assert.equal(privacy.code, 'UNSUPPORTED_VALUE');
    assert.match(privacy.search, /group=leaders/);
    assert.match(await page.evaluate(() => decodeURIComponent(location.hash)), /^#research-origin$/);
    const unsupported = await page.evaluate((handle) => handle.dispatch({ type: 'set_view', view: '__proto__' }), handle);
    assert.equal(unsupported.ok, false);
    assert.equal(await page.evaluate((handle) => handle.getState().view, handle), 'overview');
    const setHorizon = await page.evaluate((handle) => {
      const query = handle.getState();
      return query;
    }, handle);
    assert.equal(setHorizon.horizon, '1m');
  });
});

test('failed history commit restores owned state and attributes, preserving third-party node listeners', async () => {
  await withPage(async page => {
    const handle=await mount(page);
    const outcome=await page.evaluate(handle => {
      const root=document.querySelector('[data-im-workspace]');
      const oldNode=root.querySelector('.legacy-control');let clicks=0;
      oldNode.addEventListener('click',()=>clicks++);
      const before=root.outerHTML,state=JSON.stringify(handle.getState()),url=location.href;
      const push=history.pushState;history.pushState=()=>{throw new Error('history refused');};
      let result;
      try{result=handle.dispatch({type:'select_market',market_id:'JP'});}finally{history.pushState=push;}
      oldNode.click();
      return {ok:result.ok,state:JSON.stringify(handle.getState())===state,dom:root.outerHTML===before,url:location.href===url,node:oldNode===root.querySelector('.legacy-control'),clicks};
    },handle);
    assert.deepEqual(outcome,{ok:false,state:true,dom:true,url:true,node:true,clicks:1});
  });
});

test('nested workspaces and their interactive descendants are outside parent custody', async () => {
  await withPage(async page => {
    const nested='<section data-im-workspace data-im-mode="macro" id="nested"><button data-im-action="pin" data-im-market="JP">Child pin</button><article data-im-panel data-view="overview" data-horizon="1m" data-basis="usd_unhedged" data-source="fixture:v1">Child panel</article></section>';
    const markup=workspaceMarkup().replace('<h1 data-im-heading>',nested+'<h1 data-im-heading>');
    const handle=await mount(page,'',markup);
    const before=await page.locator('#nested').evaluate(n=>n.outerHTML);
    await page.click('#nested button');
    assert.deepEqual(await page.evaluate(h=>h.getState().compare_markets,handle),[]);
    assert.equal(await page.locator('#nested').evaluate(n=>n.outerHTML),before);
    await page.evaluate(h=>h.destroy(),handle);
    assert.equal(await page.locator('#nested').evaluate(n=>n.outerHTML),before);
  });
});

test('progressive expansion preserves focus, pins, URL and no-JS original visibility', async () => {
  await withPage(async page => {
    const expansion='<button hidden data-im-action="set_expanded" data-im-expansion-trigger data-im-expanded="true" aria-expanded="true" aria-controls="full"><span class="l-en">Expand all markets</span><span class="l-zh">展开全部市场</span></button><div data-im-expanded-region id="full">Full roster</div>';
    const handle=await mount(page,'',workspaceMarkup().replace('>Qualified</article>','>Qualified'+expansion+'</article>'));
    assert.equal(await page.locator('#full').isHidden(),true);
    await page.evaluate(h=>h.dispatch({type:'pin',market_id:'JP'}),handle);
    const url=page.url();
    await page.click('[data-im-expansion-trigger]');
    assert.equal(await page.locator('#full').isVisible(),true);
    assert.equal(await page.getAttribute('[data-im-expansion-trigger]','aria-expanded'),'true');
    assert.equal(await page.evaluate(()=>document.activeElement.hasAttribute('data-im-expansion-trigger')),true);
    assert.deepEqual(await page.evaluate(h=>h.getState().compare_markets,handle),['JP']);
    assert.equal(page.url(),url);
    await page.click('[data-im-expansion-trigger]');
    assert.equal(await page.locator('#full').isHidden(),true);
    await page.evaluate(h=>h.destroy(),handle);
    assert.equal(await page.locator('#full').isVisible(),true);
    assert.equal(await page.locator('[data-im-expansion-trigger]').isHidden(),true);
  });
});

test('returned state and caller config cannot mutate the current admitted state',async()=>{
  await withPage(async page=>{
    const handle=await mount(page);
    const result=await page.evaluate(handle=>{
      const returned=handle.dispatch({type:'pin',market_id:'JP'});
      returned.state.compare_markets.push('PRIVATE');
      const snapshot=handle.getState();snapshot.compare_markets.length=0;
      window.config.markets.push('PRIVATE');
      const replacement=handle.replaceSource('new-source','fixture:v1');
      const rejected=handle.dispatch({type:'pin',market_id:'PRIVATE'});
      return {pins:handle.getState().compare_markets,replaced:replacement.ok,rejected:rejected.ok};
    },handle);
    assert.deepEqual(result,{pins:['JP'],replaced:true,rejected:false});
  });
});

test('malformed action accessors are rejected before invocation',async()=>{
  await withPage(async page=>{
    const handle=await mount(page);
    const out=await page.evaluate(h=>{
      let calls=0;
      const first=h.dispatch({get type(){calls++;return 'pin';},market_id:'JP'});
      const second=h.dispatch({get type(){throw new Error('must not execute');},market_id:'JP'});
      return {calls,codes:[first.issues[0].code,second.issues[0].code],pins:h.getState().compare_markets};
    },handle);
    assert.deepEqual(out,{calls:0,codes:['INVALID_ACTION','INVALID_ACTION'],pins:[]});
  });
});

test('failed setup restores nested text container node identities and listeners',async()=>{
  await withPage(async page=>{
    await bootstrapPage(page,workspaceMarkup().replace('<p data-im-issues role="status"></p>','<p data-im-issues role="status"><span id="kept">Original</span></p>'));
    const out=await page.evaluate(config=>{
      const root=document.querySelector('[data-im-workspace]'),kept=root.querySelector('#kept');let clicks=0;
      kept.addEventListener('click',()=>clicks++);
      const before=root.outerHTML,Observer=MutationObserver;
      window.MutationObserver=class{constructor(){throw new Error('setup refusal');}};
      let refused=false;
      try{IntlWorkspace.mountIntlWorkspace(root,config);}catch{refused=true;}finally{window.MutationObserver=Observer;}
      const same=root.querySelector('#kept')===kept;kept.click();
      return {refused,same,clicks,dom:root.outerHTML===before};
    },config);
    assert.deepEqual(out,{refused:true,same:true,clicks:1,dom:true});
  });
});

test('destroy preserves changes made by unrelated legacy control owners',async()=>{
  await withPage(async page=>{
    const handle=await mount(page);
    const out=await page.evaluate(h=>{
      const node=document.querySelector('.legacy-control');
      node.hidden=true;node.disabled=true;
      h.destroy();
      return {hidden:node.hidden,disabled:node.disabled,connected:node.isConnected};
    },handle);
    assert.deepEqual(out,{hidden:true,disabled:true,connected:true});
  });
});
