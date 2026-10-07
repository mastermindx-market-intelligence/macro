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
      <article data-im-panel data-view="overview" data-horizon="1m" data-basis="usd_unhedged" data-source="fixture:v1" id="im-overview-0-overview">Qualified</article>
      <article data-im-panel data-view="overview" data-horizon="1m" data-basis="local" data-source="fixture:v1" id="im-overview-1-overview">Local</article>
      <article data-im-panel data-view="history" data-horizon="1m" data-basis="usd_unhedged" data-source="fixture:v1" id="im-history-0-history">History</article>
      <p data-im-unavailable>No matching payload</p>
      <details data-im-legacy-disclosure><summary>Legacy</summary><button class="legacy-control">Legacy button</button></details>
    </section>`;
}

function inspectorPanel(overrides = {}) {
  const market = overrides.market || 'JP';
  const horizon = overrides.horizon || '1m';
  const basis = overrides.basis || 'usd_unhedged';
  const returnBasis = overrides.return_basis || 'price';
  const context = overrides.context || 'im-overview-0';
  const payloadId = overrides.payloadId || `${context}-payload`;
  const source = Object.prototype.hasOwnProperty.call(overrides, 'source') ? overrides.source : 'fixture:v1';
  const sourceAttr = source === null ? '' : ` data-source="${source}"`;
  const deeper = overrides.deeper === false ? '' : `
            <section class="intl-inspector__deeper" data-im-inspector-page="deeper" aria-labelledby="${payloadId}-deeper-title">
              <h4 id="${payloadId}-deeper-title" tabindex="-1"><span class="l-en">Go deeper</span><span class="l-zh" lang="zh">深入研究</span></h4>
              <ul><li><a href="#research-origin"><span class="l-en">Japan dossier</span><span class="l-zh" lang="zh">日本档案</span></a></li></ul>
            </section>`;
  if (overrides.denied) {
    return `<p data-im-inspector-unavailable><span class="l-en">Market details unavailable for this selection.</span><span class="l-zh" lang="zh">此选择暂无市场详情。</span></p>`;
  }
  return `
        <details class="intl-inspector-disclosure intl-inspector__fallback" data-im-inspector-origin data-im-inspector-context="${context}">
          <summary data-im-inspector-trigger aria-controls="${payloadId}"><span class="l-en">${market} read</span><span class="l-zh" lang="zh">${market} 解读</span></summary>
          <article class="intl-inspector" data-im-inspector-payload data-im-inspector-context="${context}" data-market-id="${market}" data-horizon="${horizon}" data-basis="${basis}" data-return-basis="${returnBasis}"${sourceAttr} id="${payloadId}" aria-labelledby="${payloadId}-title">
            <header class="intl-inspector__header">
              <div class="intl-inspector__nav" data-im-inspector-enhancement hidden>
                <button type="button" data-im-inspector-action="back"><span class="l-en">Back</span><span class="l-zh" lang="zh">返回</span></button>
                <button type="button" data-im-inspector-action="close"><span class="l-en">Close</span><span class="l-zh" lang="zh">关闭</span></button>
              </div>
              <h3 id="${payloadId}-title" data-im-inspector-title tabindex="-1"><span class="l-en">${market} title</span><span class="l-zh" lang="zh">${market} 标题</span></h3>
            </header>
            <section class="intl-inspector__read" data-im-inspector-page="read" aria-labelledby="${payloadId}-read-title">
              <h4 id="${payloadId}-read-title"><span class="l-en">What the returns show</span><span class="l-zh" lang="zh">回报所显示的信息</span></h4>
            </section>
            <details class="intl-inspector__ledger" data-im-inspector-ledger>
              <summary data-im-inspector-ledger-trigger><span class="l-en">Evidence ledger</span><span class="l-zh" lang="zh">依据清单</span></summary>
              <section data-im-inspector-page="ledger" aria-labelledby="${payloadId}-ledger-title">
                <h4 id="${payloadId}-ledger-title" tabindex="-1"><span class="l-en">Evidence ledger</span><span class="l-zh" lang="zh">依据清单</span></h4>
                <details class="intl-inspector__field" data-im-inspector-field="local">
                  <summary data-im-inspector-field-trigger>Local</summary>
                  <section data-im-inspector-page="field" aria-labelledby="${payloadId}-local-title">
                    <h5 id="${payloadId}-local-title" tabindex="-1">Local price return</h5>
                    <p data-im-inspector-window>2024-01-01–2024-01-31</p>
                    <dl data-im-inspector-clocks><div data-im-inspector-clock="observation"><dt>Observation</dt><dd>Not supplied</dd></div></dl>
                  </section>
                </details>
                <details class="intl-inspector__field" data-im-inspector-field="usd">
                  <summary data-im-inspector-field-trigger>USD</summary>
                  <section data-im-inspector-page="field" aria-labelledby="${payloadId}-usd-title">
                    <h5 id="${payloadId}-usd-title" tabindex="-1">USD price return</h5>
                  </section>
                </details>
                <details class="intl-inspector__field" data-im-inspector-field="fx_contribution">
                  <summary data-im-inspector-field-trigger>FX</summary>
                  <section data-im-inspector-page="field" aria-labelledby="${payloadId}-fx-title">
                    <h5 id="${payloadId}-fx-title" tabindex="-1">Currency contribution</h5>
                  </section>
                </details>
              </section>
            </details>
            ${deeper}
            <button type="button" class="nested-listener">nested</button>
          </article>
        </details>`;
}

function workspaceWithInspector(extra = '') {
  return workspaceMarkup().replace(
    '>Qualified</article>',
    `>Qualified
        <button type="button" data-im-inspector-open data-market-id="JP" data-source="fixture:v1">Open JP</button>
        <section class="intl-inspectors" data-im-inspectors>
          <h2 id="root-inspectors-title">Inspect a market</h2>
          ${inspectorPanel()}
          ${extra}
          <dialog class="intl-inspector-shell" data-im-inspector-shell aria-label="Market Inspector" data-im-label-en="Market Inspector" data-im-label-zh="市场详情"></dialog>
        </section>
      </article>`
  );
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

test('inspector open/read/ledger/field/deeper/back/escape/close leave history and reducer state untouched', async () => {
  await withPage(async page => {
    const handle = await mount(page, '', workspaceWithInspector());
    const outcome = await page.evaluate(async h => {
      const article = document.querySelector('[data-im-inspector-payload]');
      const origin = document.querySelector('[data-im-inspector-origin]');
      const shell = document.querySelector('[data-im-inspector-shell]');
      const trigger = document.querySelector('[data-im-inspector-trigger]');
      const nested = article.querySelector('.nested-listener');
      let nestedClicks = 0;
      nested.addEventListener('click', () => { nestedClicks += 1; });
      const historyBefore = history.length;
      const urlBefore = location.href;
      const stateBefore = JSON.stringify(h.getState());
      trigger.focus();
      trigger.click();
      const afterOpen = {
        ok: shell.matches(':modal'),
        mode: h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' }).inspector.mode,
        parent: article.parentNode === shell,
        sameArticle: document.querySelector('[data-im-inspector-payload]') === article,
        sameNested: document.querySelector('.nested-listener') === nested,
        heading: document.activeElement.hasAttribute('data-im-inspector-title'),
        selected: h.getState().selected_market,
        inspectorInState: 'inspector' in h.getState(),
        ancestorInert: document.querySelector('[data-im-workspace]').hasAttribute('inert'),
        read: !document.querySelector('[data-im-inspector-page="read"]').hidden,
        ledgerHidden: document.querySelector('[data-im-inspector-ledger]').hidden,
        deeperHidden: document.querySelector('[data-im-inspector-page="deeper"]').hidden
      };
      document.querySelector('[data-im-inspector-action="evidence"]').click();
      const afterEvidence = {
        mode: !document.querySelector('[data-im-inspector-page="read"]').hidden ? 'read' : 'ledger',
        ledgerVisible: !document.querySelector('[data-im-inspector-ledger]').hidden,
        focused: document.activeElement.id.endsWith('-ledger-title'),
        fieldClosed: !document.querySelector('[data-im-inspector-field="local"]').open
      };
      document.querySelector('[data-im-inspector-field="local"] [data-im-inspector-field-trigger]').click();
      const afterField = {
        fieldVisible: !document.querySelector('[data-im-inspector-field="local"]').hidden && document.querySelector('[data-im-inspector-field="local"]').open,
        usdHidden: document.querySelector('[data-im-inspector-field="usd"]').hidden,
        window: !!document.querySelector('[data-im-inspector-window]'),
        clock: !!document.querySelector('[data-im-inspector-clock="observation"]'),
        focused: document.activeElement.id.endsWith('-local-title')
      };
      document.querySelector('[data-im-inspector-action="back"]').click();
      const backToLedger = document.activeElement.hasAttribute('data-im-inspector-field-trigger') || document.activeElement.id.endsWith('-ledger-title');
      document.querySelector('[data-im-inspector-action="deeper"]').click();
      const afterDeeper = {
        visible: !document.querySelector('[data-im-inspector-page="deeper"]').hidden,
        readHidden: document.querySelector('[data-im-inspector-page="read"]').hidden,
        focused: document.activeElement.id.endsWith('-deeper-title')
      };
      shell.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }));
      const escapeToRead = !document.querySelector('[data-im-inspector-page="read"]').hidden && shell.matches(':modal');
      document.querySelector('[data-im-inspector-action="evidence"]').click();
      document.querySelector('[data-im-inspector-field="usd"] [data-im-inspector-field-trigger]').click();
      document.querySelector('[data-im-inspector-action="close"]').click();
      nested.click();
      return {
        afterOpen, afterEvidence, afterField, backToLedger, afterDeeper, escapeToRead,
        closed: !shell.open && !shell.matches(':modal'),
        articleHome: article.parentNode === origin,
        focusBack: document.activeElement === trigger,
        history: history.length === historyBefore,
        url: location.href === urlBefore,
        state: JSON.stringify(h.getState()) === stateBefore,
        nestedClicks,
        enhancementHidden: document.querySelector('[data-im-inspector-enhancement]').hidden
      };
    }, handle);
    assert.equal(outcome.afterOpen.ok, true);
    assert.equal(outcome.afterOpen.mode, 'read');
    assert.equal(outcome.afterOpen.parent, true);
    assert.equal(outcome.afterOpen.sameArticle, true);
    assert.equal(outcome.afterOpen.sameNested, true);
    assert.equal(outcome.afterOpen.heading, true);
    assert.equal(outcome.afterOpen.selected, null);
    assert.equal(outcome.afterOpen.inspectorInState, false);
    assert.equal(outcome.afterOpen.ancestorInert, false);
    assert.equal(outcome.afterOpen.read, true);
    assert.equal(outcome.afterOpen.ledgerHidden, true);
    assert.equal(outcome.afterOpen.deeperHidden, true);
    assert.equal(outcome.afterEvidence.ledgerVisible, true);
    assert.equal(outcome.afterEvidence.focused, true);
    assert.equal(outcome.afterField.fieldVisible, true);
    assert.equal(outcome.afterField.usdHidden, true);
    assert.equal(outcome.afterField.window, true);
    assert.equal(outcome.afterField.clock, true);
    assert.equal(outcome.backToLedger, true);
    assert.equal(outcome.afterDeeper.visible, true);
    assert.equal(outcome.escapeToRead, true);
    assert.equal(outcome.closed, true);
    assert.equal(outcome.articleHome, true);
    assert.equal(outcome.focusBack, true);
    assert.equal(outcome.history, true);
    assert.equal(outcome.url, true);
    assert.equal(outcome.state, true);
    assert.equal(outcome.nestedClicks, 1);
    assert.equal(outcome.enhancementHidden, true);
  });
});

test('inspector matching refuses borrowed source, denied payload, wrong tuple and accessors', async () => {
  await withPage(async page => {
    const extra = inspectorPanel({ market: 'JP', source: null, payloadId: 'unknown-jp', context: 'unknown-jp', deeper: false }) +
      inspectorPanel({ market: 'KR', horizon: '3m', payloadId: 'kr-3m', context: 'kr-3m' });
    const deniedMarkup = workspaceMarkup().replace(
      '>Qualified</article>',
      `>Qualified<section class="intl-inspectors" data-im-inspectors>${inspectorPanel({ denied: true })}${extra}<dialog class="intl-inspector-shell" data-im-inspector-shell aria-label="Market Inspector" data-im-label-en="Market Inspector" data-im-label-zh="市场详情"></dialog></section></article>`
    );
    const handle = await mount(page, '', deniedMarkup);
    const out = await page.evaluate(h => {
      let getterCalls = 0;
      const accessor = h.openInspector({ get market_id() { getterCalls += 1; return 'JP'; }, expected_source: 'fixture:v1' });
      const extraKey = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1', extra: true });
      const stale = h.openInspector({ market_id: 'JP', expected_source: 'other' });
      const unknown = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      const denied = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      const wrongHorizon = h.openInspector({ market_id: 'KR', expected_source: 'fixture:v1' });
      const nativeUnknown = document.querySelector('[data-im-inspector-payload]:not([data-source])');
      const origin = nativeUnknown.closest('[data-im-inspector-origin]');
      origin.open = true;
      return {
        getterCalls,
        accessor: accessor.issues[0].code,
        extraKey: extraKey.issues[0].code,
        stale: stale.issues[0].code,
        unknown: unknown.ok,
        denied: denied.ok,
        wrongHorizon: wrongHorizon.ok,
        payloadExposed: !!document.querySelector('[data-im-inspector-shell] [data-im-inspector-payload]'),
        unknownFallback: origin.open && nativeUnknown.parentNode === origin,
        stateMarket: h.getState().selected_market
      };
    }, handle);
    assert.equal(out.getterCalls, 0);
    assert.equal(out.accessor, 'INVALID_ACTION');
    assert.equal(out.extraKey, 'INVALID_ACTION');
    assert.equal(out.stale, 'STALE_SOURCE');
    assert.equal(out.unknown, false);
    assert.equal(out.denied, false);
    assert.equal(out.wrongHorizon, false);
    assert.equal(out.payloadExposed, false);
    assert.equal(out.unknownFallback, true);
    assert.equal(out.stateMarket, null);
  });
});

test('inspector failed showModal rolls back to native fallback without cloning', async () => {
  await withPage(async page => {
    const handle = await mount(page, '', workspaceWithInspector());
    const out = await page.evaluate(h => {
      const article = document.querySelector('[data-im-inspector-payload]');
      const origin = document.querySelector('[data-im-inspector-origin]');
      const nested = article.querySelector('.nested-listener');
      let clicks = 0;
      nested.addEventListener('click', () => { clicks += 1; });
      const proto = HTMLDialogElement.prototype.showModal;
      HTMLDialogElement.prototype.showModal = function () { throw new Error('modality refused'); };
      let result;
      try { result = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' }); }
      finally { HTMLDialogElement.prototype.showModal = proto; }
      origin.querySelector('[data-im-inspector-trigger]').click();
      nested.click();
      return {
        ok: result.ok,
        code: result.issues[0].code,
        home: article.parentNode === origin,
        same: document.querySelector('[data-im-inspector-payload]') === article,
        nested: document.querySelector('.nested-listener') === nested,
        clicks,
        nativeOpen: origin.open,
        modal: document.querySelector('[data-im-inspector-shell]').open
      };
    }, handle);
    assert.deepEqual(out, { ok: false, code: 'UI_UPDATE_FAILED', home: true, same: true, nested: true, clicks: 1, nativeOpen: true, modal: false });
  });
});

test('failed workspace pushState and failed replaceSource keep inspector modal payload and focus', async () => {
  await withPage(async page => {
    const handle = await mount(page, '', workspaceWithInspector());
    const out = await page.evaluate(h => {
      const article = document.querySelector('[data-im-inspector-payload]');
      const shell = document.querySelector('[data-im-inspector-shell]');
      h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      document.querySelector('[data-im-inspector-action="evidence"]').click();
      const focused = document.activeElement;
      const url = location.href;
      const state = JSON.stringify(h.getState());
      const push = history.pushState;
      history.pushState = () => { throw new Error('history refused'); };
      let pushed;
      try { pushed = h.dispatch({ type: 'select_market', market_id: 'JP' }); }
      finally { history.pushState = push; }
      const afterPush = {
        ok: pushed.ok,
        modal: shell.matches(':modal'),
        same: document.querySelector('[data-im-inspector-payload]') === article,
        parent: article.parentNode === shell,
        ledger: !document.querySelector('[data-im-inspector-ledger]').hidden,
        focus: document.activeElement === focused,
        url: location.href === url,
        state: JSON.stringify(h.getState()) === state
      };
      const orig = HTMLButtonElement.prototype.setAttribute;
      HTMLButtonElement.prototype.setAttribute = function (name, value) {
        if (name === 'aria-pressed') {
          HTMLButtonElement.prototype.setAttribute = orig;
          throw new Error('paint refused');
        }
        return orig.call(this, name, value);
      };
      let replaced;
      try { replaced = h.replaceSource('fixture:v2', 'fixture:v1'); }
      finally { HTMLButtonElement.prototype.setAttribute = orig; }
      return {
        afterPush,
        replacedOk: replaced.ok,
        stillModal: shell.matches(':modal'),
        stillSame: document.querySelector('[data-im-inspector-payload]') === article,
        stillLedger: !document.querySelector('[data-im-inspector-ledger]').hidden,
        source: h.getState().source_reference
      };
    }, handle);
    assert.equal(out.afterPush.ok, false);
    assert.equal(out.afterPush.modal, true);
    assert.equal(out.afterPush.same, true);
    assert.equal(out.afterPush.parent, true);
    assert.equal(out.afterPush.ledger, true);
    assert.equal(out.afterPush.focus, true);
    assert.equal(out.afterPush.url, true);
    assert.equal(out.afterPush.state, true);
    assert.equal(out.replacedOk, false);
    assert.equal(out.stillModal, true);
    assert.equal(out.stillSame, true);
    assert.equal(out.stillLedger, true);
    assert.equal(out.source, 'fixture:v1');
  });
});

test('successful context change and replaceSource close inspector; stale source leaves it open', async () => {
  await withPage(async page => {
    const handle = await mount(page, '', workspaceWithInspector());
    const first = await page.evaluate(h => {
      h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      const stale = h.replaceSource('fixture:v2', 'wrong');
      return {
        stale: stale.issues[0].code,
        modal: document.querySelector('[data-im-inspector-shell]').matches(':modal'),
        source: h.getState().source_reference
      };
    }, handle);
    assert.equal(first.stale, 'STALE_SOURCE');
    assert.equal(first.modal, true);
    const closedByView = await page.evaluate(h => {
      const result = h.dispatch({ type: 'set_view', view: 'history' });
      return {
        ok: result.ok,
        modal: document.querySelector('[data-im-inspector-shell]').matches(':modal'),
        home: document.querySelector('[data-im-inspector-payload]').closest('[data-im-inspector-origin]') !== null,
        view: h.getState().view
      };
    }, handle);
    assert.equal(closedByView.ok, true);
    assert.equal(closedByView.modal, false);
    assert.equal(closedByView.home, true);
    assert.equal(closedByView.view, 'history');
    await page.evaluate(h => {
      h.dispatch({ type: 'set_view', view: 'overview' });
      h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
    }, handle);
    const replaced = await page.evaluate(h => {
      document.querySelector('[data-im-panel][data-view="overview"]').insertAdjacentHTML('afterend', '<article data-im-panel data-view="overview" data-horizon="1m" data-basis="usd_unhedged" data-source="fixture:v2">V2</article>');
      const result = h.replaceSource('fixture:v2', 'fixture:v1');
      return {
        ok: result.ok,
        modal: document.querySelector('[data-im-inspector-shell]').matches(':modal'),
        source: h.getState().source_reference
      };
    }, handle);
    assert.equal(replaced.ok, true);
    assert.equal(replaced.modal, false);
    assert.equal(replaced.source, 'fixture:v2');
  });
});

test('popstate closes inspector without restoring prior inspector context', async () => {
  await withPage(async page => {
    const handle = await mount(page, '', workspaceWithInspector());
    const out = await page.evaluate(h => {
      h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      document.querySelector('[data-im-inspector-action="evidence"]').click();
      const article = document.querySelector('[data-im-inspector-payload]');
      history.pushState({ im: true }, '', '?view=history&market=&pins=&horizon=3m&basis=local&return_basis=price&group=');
      dispatchEvent(new PopStateEvent('popstate'));
      return {
        view: h.getState().view,
        horizon: h.getState().horizon,
        modal: document.querySelector('[data-im-inspector-shell]').matches(':modal'),
        home: article.closest('[data-im-inspector-origin]') !== null,
        ledgerHiddenAfter: article.querySelector('[data-im-inspector-ledger]').hidden === false ? 'still-ledger' : 'restored-or-closed',
        focusHeading: document.activeElement.hasAttribute('data-im-heading')
      };
    }, handle);
    assert.equal(out.view, 'history');
    assert.equal(out.horizon, '3m');
    assert.equal(out.modal, false);
    assert.equal(out.home, true);
    assert.equal(out.focusHeading, true);
  });
});

test('inspector nested roots, remount, resize and language preserve the live article', async () => {
  await withPage(async page => {
    const nested = `<section data-im-workspace data-im-mode="macro" id="nested-inspector">${inspectorPanel({ market: 'KR', payloadId: 'child-kr', context: 'child-kr' })}<dialog class="intl-inspector-shell" data-im-inspector-shell aria-label="Child" data-im-label-en="Child" data-im-label-zh="子"></dialog><h1 data-im-heading>Child</h1><p data-im-issues></p><p data-im-unavailable></p><article data-im-panel data-view="overview" data-horizon="1m" data-basis="usd_unhedged" data-source="fixture:v1" id="child-kr-overview">Child panel</article></section>`;
    const markup = workspaceWithInspector().replace('<h1 data-im-heading>', nested + '<h1 data-im-heading>');
    const handle = await mount(page, '', markup);
    const out = await page.evaluate(async h => {
      const parentArticle = document.querySelector('[data-im-inspectors] [data-market-id="JP"]');
      const parentShell = document.querySelector('[data-im-inspectors] [data-im-inspector-shell]');
      const childArticle = document.querySelector('#nested-inspector [data-im-inspector-payload]');
      const childTrigger = document.querySelector('#nested-inspector [data-im-inspector-trigger]');
      childTrigger.click();
      const ignoredChild = {
        parentModal: parentShell.matches(':modal'),
        childStillHome: childArticle.closest('[data-im-inspector-origin]') !== null && document.getElementById('nested-inspector').contains(childArticle)
      };
      const opened = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      parentArticle.querySelector('[data-im-inspector-action="evidence"]').click();
      window.dispatchEvent(new Event('resize'));
      const afterResize = {
        mode: opened.inspector && parentArticle.querySelector('[data-im-inspector-ledger]').hidden === false,
        same: parentArticle.isConnected && parentArticle.parentNode === parentShell,
        modal: parentShell.matches(':modal')
      };
      document.documentElement.setAttribute('lang', 'zh-CN');
      await new Promise(resolve => setTimeout(resolve, 30));
      const afterLang = {
        label: parentShell.getAttribute('aria-label'),
        same: parentArticle.parentNode === parentShell,
        ledger: !parentArticle.querySelector('[data-im-inspector-ledger]').hidden
      };
      const beforeDestroy = parentArticle;
      h.destroy();
      const restored = {
        home: beforeDestroy.parentNode && beforeDestroy.parentNode.closest('[data-im-inspector-origin]') !== null,
        enhancement: beforeDestroy.querySelector('[data-im-inspector-enhancement]').hidden,
        addedGone: !beforeDestroy.querySelector('[data-im-inspector-action="evidence"]')
      };
      const next = IntlWorkspace.mountIntlWorkspace(document.querySelector('[data-im-workspace]:not(#nested-inspector)'), window.config);
      const remounted = next.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      next.destroy();
      return { ignoredChild, afterResize, afterLang, restored, remounted: remounted.ok && remounted.inspector.mode === 'read' };
    }, handle);
    assert.equal(out.ignoredChild.parentModal, false);
    assert.equal(out.ignoredChild.childStillHome, true);
    assert.equal(out.afterResize.mode, true);
    assert.equal(out.afterResize.same, true);
    assert.equal(out.afterResize.modal, true);
    assert.equal(out.afterLang.label, '市场详情');
    assert.equal(out.afterLang.same, true);
    assert.equal(out.afterLang.ledger, true);
    assert.equal(out.restored.home, true);
    assert.equal(out.restored.enhancement, true);
    assert.equal(out.restored.addedGone, true);
    assert.equal(out.remounted, true);
  });
});

test('inspector no-JS fallback keeps native details and hidden enhancement', async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL ? {channel:process.env.PLAYWRIGHT_CHROMIUM_CHANNEL} : {})});
  const page = await browser.newPage({ javaScriptEnabled: false });
  try {
    await page.setContent(`<!doctype html><html lang="en"><body>${workspaceWithInspector()}</body></html>`);
    assert.equal(await page.getAttribute('[data-im-inspector-enhancement]', 'hidden'), '');
    assert.equal(await page.locator('[data-im-inspector-page="read"]').isVisible(), false);
    await page.locator('[data-im-inspector-trigger]').click();
    assert.equal(await page.locator('[data-im-inspector-page="read"]').isVisible(), true);
    await page.locator('[data-im-inspector-ledger-trigger]').click();
    assert.equal(await page.locator('[data-im-inspector-page="ledger"]').isVisible(), true);
    assert.equal(await page.locator('[data-im-inspector-page="deeper"]').isVisible(), true);
    assert.equal(await page.locator('[data-im-inspector-shell]').evaluate(node => node.open), false);
  } finally { await browser.close(); }
});

test('inspector empty deeper destinations are honest and external open uses named trigger', async () => {
  await withPage(async page => {
    const markup = workspaceMarkup().replace(
      '>Qualified</article>',
      `>Qualified<button type="button" data-im-inspector-open data-market-id="JP" data-source="fixture:v1">Open JP</button>
        <section class="intl-inspectors" data-im-inspectors>
          ${inspectorPanel({ deeper: false })}
          <dialog class="intl-inspector-shell" data-im-inspector-shell aria-label="Market Inspector" data-im-label-en="Market Inspector" data-im-label-zh="市场详情"></dialog>
        </section></article>`
    );
    const handle = await mount(page, '', markup);
    const out = await page.evaluate(h => {
      document.querySelector('[data-im-inspector-open]').click();
      document.querySelector('[data-im-inspector-action="deeper"]').click();
      const unavailable = document.querySelector('[data-im-inspector-deeper-unavailable]');
      const text = unavailable ? unavailable.textContent : '';
      document.querySelector('[data-im-inspector-page="deeper"] a, a[href="#research-origin"]');
      return {
        modal: document.querySelector('[data-im-inspector-shell]').matches(':modal'),
        unavailable: !!unavailable && !unavailable.hidden,
        bilingual: text.indexOf('No deeper destinations') !== -1 && text.indexOf('深入研究') !== -1,
        selected: h.getState().selected_market
      };
    }, handle);
    assert.equal(out.modal, true);
    assert.equal(out.unavailable, true);
    assert.equal(out.bilingual, true);
    assert.equal(out.selected, null);
  });
});

test('following a deeper destination closes the inspector without restoring old scroll', async () => {
  await withPage(async page => {
    const handle = await mount(page, '', workspaceWithInspector());
    const out = await page.evaluate(h => {
      const article = document.querySelector('[data-im-inspector-payload]');
      window.scrollTo(0, 40);
      h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      document.querySelector('[data-im-inspector-action="deeper"]').click();
      const yBefore = window.scrollY;
      const link = document.querySelector('[data-im-inspector-page="deeper"] a');
      link.addEventListener('click', event => event.preventDefault());
      link.click();
      return {
        modal: document.querySelector('[data-im-inspector-shell]').matches(':modal'),
        home: article.closest('[data-im-inspector-origin]') !== null,
        y: window.scrollY,
        yBefore
      };
    }, handle);
    assert.equal(out.modal, false);
    assert.equal(out.home, true);
    assert.equal(out.y, out.yBefore);
  });
});

test('ambiguous inspector payloads are refused and null source matches only empty public binding', async () => {
  await withPage(async page => {
    const extra = inspectorPanel({ payloadId: 'dup-a', context: 'im-overview-0' }) + inspectorPanel({ payloadId: 'dup-b', context: 'im-overview-0' });
    const markup = workspaceMarkup().replace(
      '>Qualified</article>',
      `>Qualified<section class="intl-inspectors" data-im-inspectors>${extra}<dialog class="intl-inspector-shell" data-im-inspector-shell aria-label="Market Inspector" data-im-label-en="Market Inspector" data-im-label-zh="市场详情"></dialog></section></article>`
    );
    const handle = await mount(page, '', markup);
    const ambiguous = await page.evaluate(h => h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' }), handle);
    assert.equal(ambiguous.ok, false);
    assert.equal(ambiguous.issues[0].code, 'AMBIGUOUS_PANEL');
    const nullMarkup = workspaceMarkup({}).replace(
      'data-source="fixture:v1"',
      'data-source=""'
    ).replace(
      '>Qualified</article>',
      `>Qualified<section class="intl-inspectors" data-im-inspectors>${inspectorPanel({ source: null })}<dialog class="intl-inspector-shell" data-im-inspector-shell aria-label="Market Inspector" data-im-label-en="Market Inspector" data-im-label-zh="市场详情"></dialog></section></article>`
    );
    await bootstrapPage(page, nullMarkup);
    const nullHandle = await page.evaluateHandle(cfg => {
      cfg = JSON.parse(JSON.stringify(cfg));
      cfg.source_reference = null;
      return IntlWorkspace.mountIntlWorkspace(document.querySelector('[data-im-workspace]'), cfg);
    }, config);
    const nullOpen = await page.evaluate(h => h.openInspector({ market_id: 'JP', expected_source: null }), nullHandle);
    assert.equal(nullOpen.ok, true);
    const borrowed = await page.evaluate(h => h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' }), nullHandle);
    assert.equal(borrowed.ok, false);
    assert.equal(borrowed.issues[0].code, 'STALE_SOURCE');
  });
});

test('openInspector refuses coerced toJSON, valueOf, nested objects, functions, symbols and nonfinite numbers', async () => {
  await withPage(async page => {
    const handle = await mount(page, '', workspaceWithInspector());
    const out = await page.evaluate(h => {
      const shell = document.querySelector('[data-im-inspector-shell]');
      const origin = document.querySelector('[data-im-inspector-origin]');
      const article = document.querySelector('[data-im-inspector-payload]');
      let marketToJSON = 0, sourceToJSON = 0, marketValueOf = 0, sourceValueOf = 0;
      const forgedMarket = h.openInspector({
        market_id: { toJSON() { marketToJSON += 1; return 'JP'; }, valueOf() { marketValueOf += 1; return 'JP'; } },
        expected_source: 'fixture:v1'
      });
      const forgedSource = h.openInspector({
        market_id: 'JP',
        expected_source: { toJSON() { sourceToJSON += 1; return 'fixture:v1'; }, valueOf() { sourceValueOf += 1; return 'fixture:v1'; } }
      });
      const nanSource = h.openInspector({ market_id: 'JP', expected_source: Number.NaN });
      const infSource = h.openInspector({ market_id: 'JP', expected_source: Number.POSITIVE_INFINITY });
      const negInf = h.openInspector({ market_id: 'JP', expected_source: Number.NEGATIVE_INFINITY });
      const fnMarket = h.openInspector({ market_id: function () { return 'JP'; }, expected_source: 'fixture:v1' });
      const symMarket = h.openInspector({ market_id: Symbol('JP'), expected_source: 'fixture:v1' });
      const nested = h.openInspector({ market_id: { market: 'JP' }, expected_source: 'fixture:v1' });
      const afterRefuse = {
        modal: shell.matches(':modal'),
        articleHome: article.parentNode === origin,
        inspector: h.closeInspector && document.querySelector('[data-im-inspector-shell] [data-im-inspector-payload]')
      };
      const primitive = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      return {
        marketToJSON, sourceToJSON, marketValueOf, sourceValueOf,
        forgedMarket: { ok: forgedMarket.ok, code: forgedMarket.issues[0] && forgedMarket.issues[0].code },
        forgedSource: { ok: forgedSource.ok, code: forgedSource.issues[0] && forgedSource.issues[0].code },
        nanSource: { ok: nanSource.ok, code: nanSource.issues[0] && nanSource.issues[0].code, field: nanSource.issues[0] && nanSource.issues[0].field },
        infSource: { ok: infSource.ok, code: infSource.issues[0] && infSource.issues[0].code },
        negInf: { ok: negInf.ok, code: negInf.issues[0] && negInf.issues[0].code },
        fnMarket: { ok: fnMarket.ok, code: fnMarket.issues[0] && fnMarket.issues[0].code },
        symMarket: { ok: symMarket.ok, code: symMarket.issues[0] && symMarket.issues[0].code },
        nested: { ok: nested.ok, code: nested.issues[0] && nested.issues[0].code },
        afterRefuseModal: afterRefuse.modal,
        afterRefuseHome: afterRefuse.articleHome,
        afterRefusePayload: !!afterRefuse.inspector,
        primitiveOk: primitive.ok,
        primitiveMode: primitive.inspector && primitive.inspector.mode
      };
    }, handle);
    assert.equal(out.marketToJSON, 0);
    assert.equal(out.sourceToJSON, 0);
    assert.equal(out.marketValueOf, 0);
    assert.equal(out.sourceValueOf, 0);
    assert.equal(out.forgedMarket.ok, false);
    assert.equal(out.forgedMarket.code, 'INVALID_ACTION');
    assert.equal(out.forgedSource.ok, false);
    assert.equal(out.forgedSource.code, 'INVALID_ACTION');
    assert.equal(out.nanSource.ok, false);
    assert.equal(out.nanSource.code, 'INVALID_ACTION');
    assert.equal(out.infSource.ok, false);
    assert.equal(out.infSource.code, 'INVALID_ACTION');
    assert.equal(out.negInf.ok, false);
    assert.equal(out.negInf.code, 'INVALID_ACTION');
    assert.equal(out.fnMarket.ok, false);
    assert.equal(out.symMarket.ok, false);
    assert.equal(out.nested.ok, false);
    assert.equal(out.afterRefuseModal, false);
    assert.equal(out.afterRefuseHome, true);
    assert.equal(out.afterRefusePayload, false);
    assert.equal(out.primitiveOk, true);
    assert.equal(out.primitiveMode, 'read');
  });
});

test('openInspector requires the active Overview panel and exact inspector-context join', async () => {
  await withPage(async page => {
    const four = workspaceMarkup().replace(
      '>Qualified</article>',
      `>Qualified<section class="intl-inspectors" data-im-inspectors>
        ${inspectorPanel({ context: 'im-overview-0', payloadId: 'im-workspace-inspector-0' })}
        ${inspectorPanel({ market: 'JP', horizon: '1m', basis: 'local', context: 'im-overview-1', payloadId: 'im-workspace-inspector-1' })}
        ${inspectorPanel({ market: 'JP', horizon: '3m', basis: 'usd_unhedged', context: 'im-overview-2', payloadId: 'im-workspace-inspector-2' })}
        ${inspectorPanel({ market: 'JP', horizon: '3m', basis: 'local', context: 'im-overview-3', payloadId: 'im-workspace-inspector-3' })}
        <dialog class="intl-inspector-shell" data-im-inspector-shell aria-label="Market Inspector" data-im-label-en="Market Inspector" data-im-label-zh="市场详情"></dialog>
      </section></article>`
    ).replace(
      '<article data-im-panel data-view="overview" data-horizon="1m" data-basis="local" data-source="fixture:v1" id="im-overview-1-overview">Local</article>',
      '<article data-im-panel data-view="overview" data-horizon="1m" data-basis="local" data-source="fixture:v1" id="im-overview-1-overview">Local</article>' +
      '<article data-im-panel data-view="overview" data-horizon="3m" data-basis="usd_unhedged" data-source="fixture:v1" id="im-overview-2-overview">3m usd</article>' +
      '<article data-im-panel data-view="overview" data-horizon="3m" data-basis="local" data-source="fixture:v1" id="im-overview-3-overview">3m local</article>'
    );
    const handle = await mount(page, '', four);
    const first = await page.evaluate(h => {
      const opened = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      return {
        ok: opened.ok,
        mode: opened.inspector && opened.inspector.mode,
        context: document.querySelector('[data-im-inspector-shell] [data-im-inspector-payload]').getAttribute('data-im-inspector-context'),
        panel: document.getElementById('im-overview-0-overview') && !document.getElementById('im-overview-0-overview').hidden
      };
    }, handle);
    assert.equal(first.ok, true);
    assert.equal(first.mode, 'read');
    assert.equal(first.context, 'im-overview-0');
    await page.evaluate(h => h.closeInspector(), handle);
    const historySwitch = await page.evaluate(h => {
      const originOpen = document.querySelector('[data-im-inspector-origin]').open;
      const switched = h.dispatch({ type: 'set_view', view: 'history' });
      const historyAfterView = history.length;
      const urlAfterView = location.href;
      const stateAfterView = JSON.stringify(h.getState());
      const refused = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      return {
        switched: switched.ok,
        view: h.getState().view,
        refusedOk: refused.ok,
        refusedCode: refused.issues[0] && refused.issues[0].code,
        inspector: refused.inspector,
        modal: document.querySelector('[data-im-inspector-shell]').matches(':modal'),
        payloadInShell: !!document.querySelector('[data-im-inspector-shell] [data-im-inspector-payload]'),
        originOpen: document.querySelector('[data-im-inspector-origin]').open === originOpen,
        historyUnchanged: history.length === historyAfterView,
        urlUnchanged: location.href === urlAfterView,
        stateUnchanged: JSON.stringify(h.getState()) === stateAfterView,
        urlIsHistory: location.search.indexOf('view=history') !== -1,
        selected: h.getState().selected_market
      };
    }, handle);
    assert.equal(historySwitch.switched, true);
    assert.equal(historySwitch.view, 'history');
    assert.equal(historySwitch.refusedOk, false);
    assert.equal(historySwitch.refusedCode, 'NO_MATCHING_PANEL');
    assert.equal(historySwitch.inspector, null);
    assert.equal(historySwitch.modal, false);
    assert.equal(historySwitch.payloadInShell, false);
    assert.equal(historySwitch.originOpen, true);
    assert.equal(historySwitch.historyUnchanged, true);
    assert.equal(historySwitch.urlUnchanged, true);
    assert.equal(historySwitch.stateUnchanged, true);
    assert.equal(historySwitch.urlIsHistory, true);
    assert.equal(historySwitch.selected, null);
    const mismatch = await page.evaluate(h => {
      h.dispatch({ type: 'set_view', view: 'overview' });
      document.querySelector('[data-im-inspector-payload]').setAttribute('data-im-inspector-context', 'im-overview-2');
      const historyBefore = history.length;
      const urlBefore = location.href;
      const stateBefore = JSON.stringify(h.getState());
      const refused = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      return {
        ok: refused.ok,
        code: refused.issues[0] && refused.issues[0].code,
        modal: document.querySelector('[data-im-inspector-shell]').matches(':modal'),
        history: history.length === historyBefore,
        url: location.href === urlBefore,
        state: JSON.stringify(h.getState()) === stateBefore,
        view: h.getState().view
      };
    }, handle);
    assert.equal(mismatch.ok, false);
    assert.equal(mismatch.code, 'NO_MATCHING_PANEL');
    assert.equal(mismatch.modal, false);
    assert.equal(mismatch.history, true);
    assert.equal(mismatch.url, true);
    assert.equal(mismatch.state, true);
    assert.equal(mismatch.view, 'overview');
    const ambiguousOverview = await page.evaluate(h => {
      const panel = document.getElementById('im-overview-0-overview');
      const clone = panel.cloneNode(true);
      clone.id = 'im-overview-0b-overview';
      panel.after(clone);
      const refused = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      return { ok: refused.ok, code: refused.issues[0] && refused.issues[0].code, modal: document.querySelector('[data-im-inspector-shell]').matches(':modal') };
    }, handle);
    assert.equal(ambiguousOverview.ok, false);
    assert.equal(ambiguousOverview.code, 'AMBIGUOUS_PANEL');
    assert.equal(ambiguousOverview.modal, false);
  });
});

test('failed inspector mode restores owned presentation and openInspector does not succeed after false', async () => {
  await withPage(async page => {
    const handle = await mount(page, '', workspaceWithInspector());
    const evidence = await page.evaluate(h => {
      const article = document.querySelector('[data-im-inspector-payload]');
      const origin = document.querySelector('[data-im-inspector-origin]');
      const nested = article.querySelector('.nested-listener');
      let nestedClicks = 0;
      nested.addEventListener('click', () => { nestedClicks += 1; });
      h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      const read = article.querySelector('[data-im-inspector-page="read"]');
      const ledger = article.querySelector('[data-im-inspector-ledger]');
      const heading = article.querySelector('[data-im-inspector-title]');
      heading.focus();
      const before = {
        readHidden: !!read.hidden,
        ledgerHidden: !!ledger.hidden,
        ledgerOpen: !!ledger.open,
        mode: h.closeInspector && null,
        focus: document.activeElement,
        modal: document.querySelector('[data-im-inspector-shell]').matches(':modal')
      };
      const live = (function () {
        const opened = { mode: 'read' };
        return opened;
      }());
      live.mode = document.querySelector('[data-im-inspector-page="read"]').hidden ? 'other' : 'read';
      const desc = Object.getOwnPropertyDescriptor(HTMLDetailsElement.prototype, 'open');
      Object.defineProperty(ledger, 'open', {
        configurable: true,
        get() { return desc.get.call(ledger); },
        set(value) { if (value) throw new Error('ledger open refused'); desc.set.call(ledger, value); }
      });
      document.querySelector('[data-im-inspector-action="evidence"]').click();
      nested.click();
      return {
        okMode: live.mode,
        readHidden: !!read.hidden,
        ledgerHidden: !!ledger.hidden,
        ledgerOpen: !!ledger.open,
        focusSame: document.activeElement === heading,
        modal: document.querySelector('[data-im-inspector-shell]').matches(':modal'),
        sameArticle: document.querySelector('[data-im-inspector-payload]') === article,
        sameNested: document.querySelector('.nested-listener') === nested,
        nestedClicks,
        originHome: article.parentNode !== origin,
        before
      };
    }, handle);
    assert.equal(evidence.readHidden, false);
    assert.equal(evidence.ledgerHidden, true);
    assert.equal(evidence.ledgerOpen, false);
    assert.equal(evidence.focusSame, true);
    assert.equal(evidence.modal, true);
    assert.equal(evidence.sameArticle, true);
    assert.equal(evidence.sameNested, true);
    assert.equal(evidence.nestedClicks, 1);
    const deeperLeak = await page.evaluate(h => {
      const article = document.querySelector('[data-im-inspector-payload]');
      const deeper = article.querySelector('[data-im-inspector-page="deeper"]');
      deeper.remove();
      const read = article.querySelector('[data-im-inspector-page="read"]');
      const desc = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'hidden');
      Object.defineProperty(read, 'hidden', {
        configurable: true,
        get() { return desc.get.call(read); },
        set(value) { if (value) throw new Error('read hidden refused'); desc.set.call(read, value); }
      });
      document.querySelector('[data-im-inspector-action="deeper"]').click();
      return {
        leaked: !!article.querySelector('[data-im-inspector-deeper-unavailable]'),
        readHidden: !!read.hidden,
        addedInDom: !!document.querySelector('[data-im-inspector-deeper-unavailable]')
      };
    }, handle);
    assert.equal(deeperLeak.leaked, false);
    assert.equal(deeperLeak.readHidden, false);
    assert.equal(deeperLeak.addedInDom, false);
    await page.evaluate(h => h.closeInspector(), handle);
    const failedOpen = await page.evaluate(h => {
      const article = document.querySelector('[data-im-inspector-payload]');
      const origin = document.querySelector('[data-im-inspector-origin]');
      const ledger = article.querySelector('[data-im-inspector-ledger]');
      const desc = Object.getOwnPropertyDescriptor(HTMLDetailsElement.prototype, 'open');
      Object.defineProperty(ledger, 'hidden', {
        configurable: true,
        get() { return Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'hidden').get.call(ledger); },
        set(value) {
          if (value) throw new Error('ledger hidden refused');
          Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'hidden').set.call(ledger, value);
        }
      });
      const result = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      return {
        ok: result.ok,
        code: result.issues[0] && result.issues[0].code,
        inspector: result.inspector,
        modal: document.querySelector('[data-im-inspector-shell]').matches(':modal') || document.querySelector('[data-im-inspector-shell]').open,
        home: article.parentNode === origin,
        enhancementHidden: document.querySelector('[data-im-inspector-enhancement]').hidden
      };
    }, handle);
    assert.equal(failedOpen.ok, false);
    assert.equal(failedOpen.code, 'UI_UPDATE_FAILED');
    assert.equal(failedOpen.inspector, null);
    assert.equal(failedOpen.modal, false);
    assert.equal(failedOpen.home, true);
  });
});

test('failed inspector heading focus after showModal closes native dialog and later open recovers', async () => {
  await withPage(async page => {
    const handle = await mount(page, '', workspaceWithInspector());
    const out = await page.evaluate(h => {
      const article = document.querySelector('[data-im-inspector-payload]');
      const origin = document.querySelector('[data-im-inspector-origin]');
      const shell = document.querySelector('[data-im-inspector-shell]');
      const trigger = document.querySelector('[data-im-inspector-trigger]');
      const nested = article.querySelector('.nested-listener');
      let nestedClicks = 0;
      nested.addEventListener('click', () => { nestedClicks += 1; });
      trigger.focus();
      const spacer = document.createElement('div');
      spacer.style.height = '4000px';
      document.body.appendChild(spacer);
      window.scrollTo(0, 80);
      const yBefore = window.scrollY;
      const historyBefore = history.length;
      const urlBefore = location.href;
      const stateBefore = JSON.stringify(h.getState());
      const heading = article.querySelector('[data-im-inspector-title]');
      const origFocus = heading.focus;
      heading.focus = function () { throw new Error('heading focus refused'); };
      let result;
      try { result = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' }); }
      finally { heading.focus = origFocus; }
      nested.click();
      const afterFail = {
        ok: result.ok,
        code: result.issues[0] && result.issues[0].code,
        inspector: result.inspector,
        dialogOpen: shell.open,
        modal: shell.matches(':modal'),
        payloadInShell: !!shell.querySelector('[data-im-inspector-payload]'),
        home: article.parentNode === origin,
        sameArticle: document.querySelector('[data-im-inspector-payload]') === article,
        sameNested: document.querySelector('.nested-listener') === nested,
        nestedClicks,
        originHidden: origin.hidden,
        originOpen: origin.open,
        enhancementHidden: article.querySelector('[data-im-inspector-enhancement]').hidden,
        history: history.length === historyBefore,
        url: location.href === urlBefore,
        state: JSON.stringify(h.getState()) === stateBefore,
        selected: h.getState().selected_market,
        focusBack: document.activeElement === trigger,
        scrollY: window.scrollY,
        yBefore
      };
      const recovered = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      return {
        afterFail,
        recovered: {
          ok: recovered.ok,
          mode: recovered.inspector && recovered.inspector.mode,
          modal: shell.matches(':modal'),
          parent: article.parentNode === shell,
          sameArticle: document.querySelector('[data-im-inspector-payload]') === article
        }
      };
    }, handle);
    assert.equal(out.afterFail.ok, false);
    assert.equal(out.afterFail.code, 'UI_UPDATE_FAILED');
    assert.equal(out.afterFail.inspector, null);
    assert.equal(out.afterFail.dialogOpen, false);
    assert.equal(out.afterFail.modal, false);
    assert.equal(out.afterFail.payloadInShell, false);
    assert.equal(out.afterFail.home, true);
    assert.equal(out.afterFail.sameArticle, true);
    assert.equal(out.afterFail.sameNested, true);
    assert.equal(out.afterFail.nestedClicks, 1);
    assert.equal(out.afterFail.originHidden, false);
    assert.equal(out.afterFail.enhancementHidden, true);
    assert.equal(out.afterFail.history, true);
    assert.equal(out.afterFail.url, true);
    assert.equal(out.afterFail.state, true);
    assert.equal(out.afterFail.selected, null);
    assert.equal(out.afterFail.focusBack, true);
    assert.equal(out.afterFail.yBefore > 0, true);
    assert.equal(out.afterFail.scrollY, out.afterFail.yBefore);
    assert.equal(out.recovered.ok, true);
    assert.equal(out.recovered.mode, 'read');
    assert.equal(out.recovered.modal, true);
    assert.equal(out.recovered.parent, true);
    assert.equal(out.recovered.sameArticle, true);
  });
});

test('native dialog.close restores article home and same-article open reopens', async () => {
  await withPage(async page => {
    const handle = await mount(page, '', workspaceWithInspector());
    const out = await page.evaluate(async h => {
      const article = document.querySelector('[data-im-inspector-payload]');
      const origin = document.querySelector('[data-im-inspector-origin]');
      const shell = document.querySelector('[data-im-inspector-shell]');
      const trigger = document.querySelector('[data-im-inspector-trigger]');
      const nested = article.querySelector('.nested-listener');
      let nestedClicks = 0;
      nested.addEventListener('click', () => { nestedClicks += 1; });
      trigger.focus();
      const historyBefore = history.length;
      const urlBefore = location.href;
      const stateBefore = JSON.stringify(h.getState());
      h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      const closed = new Promise(resolve => {
        shell.addEventListener('close', () => resolve(true), { once: true });
      });
      shell.close();
      await closed;
      nested.click();
      const afterNative = {
        dialogOpen: shell.open,
        modal: shell.matches(':modal'),
        home: article.parentNode === origin,
        originHidden: origin.hidden,
        payloadInShell: !!shell.querySelector('[data-im-inspector-payload]'),
        sameArticle: document.querySelector('[data-im-inspector-payload]') === article,
        sameNested: document.querySelector('.nested-listener') === nested,
        nestedClicks,
        focusBack: document.activeElement === trigger,
        history: history.length === historyBefore,
        url: location.href === urlBefore,
        state: JSON.stringify(h.getState()) === stateBefore,
        selected: h.getState().selected_market
      };
      const reopened = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      const afterReopen = {
        ok: reopened.ok,
        mode: reopened.inspector && reopened.inspector.mode,
        modal: shell.matches(':modal'),
        parent: article.parentNode === shell,
        sameArticle: document.querySelector('[data-im-inspector-payload]') === article
      };
      h.destroy();
      nested.click();
      let destroyCloseThrew = null;
      try { shell.dispatchEvent(new Event('close')); } catch (error) { destroyCloseThrew = String(error && error.message || error); }
      const afterDestroy = {
        home: article.parentNode === origin,
        nestedAlive: document.querySelector('.nested-listener') === nested,
        nestedClicks,
        threw: destroyCloseThrew,
        originHidden: origin.hidden
      };
      const next = IntlWorkspace.mountIntlWorkspace(document.querySelector('[data-im-workspace]'), window.config);
      const remounted = next.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      next.destroy();
      return { afterNative, afterReopen, afterDestroy, remounted: remounted.ok && remounted.inspector.mode === 'read' };
    }, handle);
    assert.equal(out.afterNative.dialogOpen, false);
    assert.equal(out.afterNative.modal, false);
    assert.equal(out.afterNative.home, true);
    assert.equal(out.afterNative.originHidden, false);
    assert.equal(out.afterNative.payloadInShell, false);
    assert.equal(out.afterNative.sameArticle, true);
    assert.equal(out.afterNative.sameNested, true);
    assert.equal(out.afterNative.nestedClicks, 1);
    assert.equal(out.afterNative.focusBack, true);
    assert.equal(out.afterNative.history, true);
    assert.equal(out.afterNative.url, true);
    assert.equal(out.afterNative.state, true);
    assert.equal(out.afterNative.selected, null);
    assert.equal(out.afterReopen.ok, true);
    assert.equal(out.afterReopen.mode, 'read');
    assert.equal(out.afterReopen.modal, true);
    assert.equal(out.afterReopen.parent, true);
    assert.equal(out.afterReopen.sameArticle, true);
    assert.equal(out.afterDestroy.home, true);
    assert.equal(out.afterDestroy.nestedAlive, true);
    assert.equal(out.afterDestroy.nestedClicks, 2);
    assert.equal(out.afterDestroy.threw, null);
    assert.equal(out.afterDestroy.originHidden, false);
    assert.equal(out.remounted, true);
  });
});

test('rapid native close then reopen survives queued close', async () => {
  await withPage(async page => {
    const handle = await mount(page, '', workspaceWithInspector());
    const out = await page.evaluate(async h => {
      const article = document.querySelector('[data-im-inspector-payload]');
      const origin = document.querySelector('[data-im-inspector-origin]');
      const shell = document.querySelector('[data-im-inspector-shell]');
      const nested = article.querySelector('.nested-listener');
      let nestedClicks = 0;
      nested.addEventListener('click', () => { nestedClicks += 1; });
      h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      shell.close();
      const immediate = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      const afterImmediate = {
        ok: immediate.ok,
        mode: immediate.inspector && immediate.inspector.mode,
        modal: shell.matches(':modal'),
        parent: article.parentNode === shell,
        sameArticle: document.querySelector('[data-im-inspector-payload]') === article
      };
      await new Promise(resolve => setTimeout(resolve, 40));
      const afterQueued = {
        modal: shell.matches(':modal'),
        parent: article.parentNode === shell,
        home: article.parentNode === origin,
        sameArticle: document.querySelector('[data-im-inspector-payload]') === article
      };
      h.closeInspector();
      const second = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      await new Promise(resolve => setTimeout(resolve, 40));
      nested.click();
      return {
        afterImmediate,
        afterQueued,
        afterCloseReopen: {
          ok: second.ok,
          modal: shell.matches(':modal'),
          parent: article.parentNode === shell,
          sameNested: document.querySelector('.nested-listener') === nested,
          nestedClicks
        }
      };
    }, handle);
    assert.equal(out.afterImmediate.ok, true);
    assert.equal(out.afterImmediate.mode, 'read');
    assert.equal(out.afterImmediate.modal, true);
    assert.equal(out.afterImmediate.parent, true);
    assert.equal(out.afterImmediate.sameArticle, true);
    assert.equal(out.afterQueued.modal, true);
    assert.equal(out.afterQueued.parent, true);
    assert.equal(out.afterQueued.home, false);
    assert.equal(out.afterCloseReopen.ok, true);
    assert.equal(out.afterCloseReopen.modal, true);
    assert.equal(out.afterCloseReopen.parent, true);
    assert.equal(out.afterCloseReopen.sameNested, true);
    assert.equal(out.afterCloseReopen.nestedClicks, 1);
  });
});

test('failed history transaction delayed close does not destroy rehydrated inspector', async () => {
  await withPage(async page => {
    const handle = await mount(page, '', workspaceWithInspector());
    const out = await page.evaluate(async h => {
      const article = document.querySelector('[data-im-inspector-payload]');
      const origin = document.querySelector('[data-im-inspector-origin]');
      const shell = document.querySelector('[data-im-inspector-shell]');
      const nested = article.querySelector('.nested-listener');
      let nestedClicks = 0;
      nested.addEventListener('click', () => { nestedClicks += 1; });
      h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      document.querySelector('[data-im-inspector-action="evidence"]').click();
      const focused = document.activeElement;
      const url = location.href;
      const state = JSON.stringify(h.getState());
      const push = history.pushState;
      history.pushState = () => { throw new Error('history refused'); };
      let pushed;
      try { pushed = h.dispatch({ type: 'select_market', market_id: 'JP' }); }
      finally { history.pushState = push; }
      const afterPush = {
        ok: pushed.ok,
        modal: shell.matches(':modal'),
        parent: article.parentNode === shell,
        ledger: !document.querySelector('[data-im-inspector-ledger]').hidden,
        focus: document.activeElement === focused,
        url: location.href === url,
        state: JSON.stringify(h.getState()) === state
      };
      await new Promise(resolve => setTimeout(resolve, 40));
      nested.click();
      return {
        afterPush,
        afterDelayedClose: {
          modal: shell.matches(':modal'),
          parent: article.parentNode === shell,
          home: article.parentNode === origin,
          ledger: !document.querySelector('[data-im-inspector-ledger]').hidden,
          sameArticle: document.querySelector('[data-im-inspector-payload]') === article,
          sameNested: document.querySelector('.nested-listener') === nested,
          nestedClicks,
          focus: document.activeElement === focused
        }
      };
    }, handle);
    assert.equal(out.afterPush.ok, false);
    assert.equal(out.afterPush.modal, true);
    assert.equal(out.afterPush.parent, true);
    assert.equal(out.afterPush.ledger, true);
    assert.equal(out.afterPush.focus, true);
    assert.equal(out.afterPush.url, true);
    assert.equal(out.afterPush.state, true);
    assert.equal(out.afterDelayedClose.modal, true);
    assert.equal(out.afterDelayedClose.parent, true);
    assert.equal(out.afterDelayedClose.home, false);
    assert.equal(out.afterDelayedClose.ledger, true);
    assert.equal(out.afterDelayedClose.sameArticle, true);
    assert.equal(out.afterDelayedClose.sameNested, true);
    assert.equal(out.afterDelayedClose.nestedClicks, 1);
    assert.equal(out.afterDelayedClose.focus, true);
  });
});

test('failed rehydrate showModal during pushState and replaceSource returns accessible original payload', async () => {
  await withPage(async page => {
    const handle = await mount(page, '', workspaceWithInspector());
    const out = await page.evaluate(async h => {
      const article = document.querySelector('[data-im-inspector-payload]');
      const origin = document.querySelector('[data-im-inspector-origin]');
      const shell = document.querySelector('[data-im-inspector-shell]');
      const nested = article.querySelector('.nested-listener');
      let nestedClicks = 0;
      nested.addEventListener('click', () => { nestedClicks += 1; });
      const foreign = document.createElement('span');
      foreign.className = 'foreign-keep';
      foreign.textContent = 'foreign';
      origin.appendChild(foreign);
      let foreignClicks = 0;
      foreign.addEventListener('click', () => { foreignClicks += 1; });
      h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      document.querySelector('[data-im-inspector-action="evidence"]').click();
      const url = location.href;
      const state = JSON.stringify(h.getState());
      const historyBefore = history.length;
      const push = history.pushState;
      history.pushState = () => { throw new Error('history refused'); };
      shell.showModal = () => { throw new Error('rehydrate showModal failed'); };
      let pushed;
      try { pushed = h.dispatch({ type: 'select_market', market_id: 'JP' }); }
      finally { history.pushState = push; delete shell.showModal; }
      nested.click();
      foreign.click();
      const afterPush = {
        ok: pushed.ok,
        modal: shell.matches(':modal'),
        open: shell.open,
        inShell: article.parentNode === shell,
        originHidden: origin.hidden,
        originOpen: origin.open,
        articleVisible: article.getClientRects().length > 0,
        home: article.parentNode === origin,
        sameArticle: document.querySelector('[data-im-inspector-payload]') === article,
        sameNested: document.querySelector('.nested-listener') === nested,
        nestedClicks,
        foreignSame: origin.querySelector('.foreign-keep') === foreign,
        foreignClicks,
        enhancementHidden: article.querySelector('[data-im-inspector-enhancement]').hidden,
        url: location.href === url,
        state: JSON.stringify(h.getState()) === state,
        selected: h.getState().selected_market,
        history: history.length === historyBefore,
        payloadInShell: !!shell.querySelector('[data-im-inspector-payload]')
      };
      await new Promise(resolve => setTimeout(resolve, 40));
      nested.click();
      const afterDelayed = {
        home: article.parentNode === origin,
        modal: shell.matches(':modal'),
        sameArticle: document.querySelector('[data-im-inspector-payload]') === article,
        sameNested: document.querySelector('.nested-listener') === nested,
        nestedClicks,
        articleVisible: article.getClientRects().length > 0,
        originHidden: origin.hidden
      };
      const recovered = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      const recoveredSnap = { ok: recovered.ok, modal: shell.matches(':modal'), parent: article.parentNode === shell };
      document.querySelector('[data-im-inspector-action="evidence"]').click();
      const orig = HTMLButtonElement.prototype.setAttribute;
      HTMLButtonElement.prototype.setAttribute = function (name, value) {
        if (name === 'aria-pressed') {
          HTMLButtonElement.prototype.setAttribute = orig;
          throw new Error('paint refused');
        }
        return orig.call(this, name, value);
      };
      shell.showModal = () => { throw new Error('rehydrate showModal failed'); };
      let replaced;
      try { replaced = h.replaceSource('fixture:v2', 'fixture:v1'); }
      finally {
        HTMLButtonElement.prototype.setAttribute = orig;
        delete shell.showModal;
      }
      nested.click();
      return {
        afterPush,
        afterDelayed,
        recovered: recoveredSnap,
        afterReplace: {
          ok: replaced.ok,
          modal: shell.matches(':modal'),
          inShell: article.parentNode === shell,
          originHidden: origin.hidden,
          articleVisible: article.getClientRects().length > 0,
          home: article.parentNode === origin,
          sameArticle: document.querySelector('[data-im-inspector-payload]') === article,
          sameNested: document.querySelector('.nested-listener') === nested,
          nestedClicks,
          foreignSame: origin.querySelector('.foreign-keep') === foreign,
          source: h.getState().source_reference,
          url: location.href === url,
          enhancementHidden: article.querySelector('[data-im-inspector-enhancement]').hidden
        }
      };
    }, handle);
    assert.equal(out.afterPush.ok, false);
    assert.equal(out.afterPush.modal, false);
    assert.equal(out.afterPush.open, false);
    assert.equal(out.afterPush.inShell, false);
    assert.equal(out.afterPush.originHidden, false);
    assert.equal(out.afterPush.articleVisible, true);
    assert.equal(out.afterPush.home, true);
    assert.equal(out.afterPush.sameArticle, true);
    assert.equal(out.afterPush.sameNested, true);
    assert.equal(out.afterPush.nestedClicks, 1);
    assert.equal(out.afterPush.foreignSame, true);
    assert.equal(out.afterPush.foreignClicks, 1);
    assert.equal(out.afterPush.enhancementHidden, true);
    assert.equal(out.afterPush.url, true);
    assert.equal(out.afterPush.state, true);
    assert.equal(out.afterPush.selected, null);
    assert.equal(out.afterPush.history, true);
    assert.equal(out.afterPush.payloadInShell, false);
    assert.equal(out.afterDelayed.home, true);
    assert.equal(out.afterDelayed.modal, false);
    assert.equal(out.afterDelayed.sameArticle, true);
    assert.equal(out.afterDelayed.sameNested, true);
    assert.equal(out.afterDelayed.nestedClicks, 2);
    assert.equal(out.afterDelayed.articleVisible, true);
    assert.equal(out.afterDelayed.originHidden, false);
    assert.equal(out.recovered.ok, true);
    assert.equal(out.recovered.modal, true);
    assert.equal(out.recovered.parent, true);
    assert.equal(out.afterReplace.ok, false);
    assert.equal(out.afterReplace.modal, false);
    assert.equal(out.afterReplace.inShell, false);
    assert.equal(out.afterReplace.originHidden, false);
    assert.equal(out.afterReplace.articleVisible, true);
    assert.equal(out.afterReplace.home, true);
    assert.equal(out.afterReplace.sameArticle, true);
    assert.equal(out.afterReplace.sameNested, true);
    assert.equal(out.afterReplace.nestedClicks, 3);
    assert.equal(out.afterReplace.foreignSame, true);
    assert.equal(out.afterReplace.source, 'fixture:v1');
    assert.equal(out.afterReplace.url, true);
    assert.equal(out.afterReplace.enhancementHidden, true);
  });
});

test('failed rehydrate mode restore during pushState and replaceSource returns accessible original payload', async () => {
  await withPage(async page => {
    const handle = await mount(page, '', workspaceWithInspector());
    const out = await page.evaluate(async h => {
      const article = document.querySelector('[data-im-inspector-payload]');
      const origin = document.querySelector('[data-im-inspector-origin]');
      const shell = document.querySelector('[data-im-inspector-shell]');
      const nested = article.querySelector('.nested-listener');
      const headings = [
        article.querySelector('[data-im-inspector-title]'),
        article.querySelector('[data-im-inspector-page="ledger"] [tabindex="-1"]'),
        article.querySelector('[data-im-inspector-page="ledger"] h4')
      ].filter((node, index, list) => node && list.indexOf(node) === index);
      const headingIds = headings.map(node => node.getAttribute('id'));
      function poisonHeadings() {
        headings.forEach(node => {
          Object.defineProperty(node, 'id', {
            configurable: true,
            get() { throw new Error('mode restore refused'); }
          });
        });
      }
      function restoreHeadings() {
        headings.forEach((node, index) => {
          delete node.id;
          if (headingIds[index]) node.setAttribute('id', headingIds[index]);
        });
      }
      let nestedClicks = 0;
      nested.addEventListener('click', () => { nestedClicks += 1; });
      h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      document.querySelector('[data-im-inspector-action="evidence"]').click();
      const url = location.href;
      const state = JSON.stringify(h.getState());
      poisonHeadings();
      const push = history.pushState;
      history.pushState = () => { throw new Error('history refused'); };
      let pushed;
      try { pushed = h.dispatch({ type: 'select_market', market_id: 'JP' }); }
      finally {
        history.pushState = push;
        restoreHeadings();
      }
      nested.click();
      const afterPush = {
        ok: pushed.ok,
        modal: shell.matches(':modal'),
        inShell: article.parentNode === shell,
        originHidden: origin.hidden,
        articleVisible: article.getClientRects().length > 0,
        home: article.parentNode === origin,
        sameArticle: document.querySelector('[data-im-inspector-payload]') === article,
        sameNested: document.querySelector('.nested-listener') === nested,
        nestedClicks,
        enhancementHidden: article.querySelector('[data-im-inspector-enhancement]').hidden,
        url: location.href === url,
        state: JSON.stringify(h.getState()) === state,
        selected: h.getState().selected_market
      };
      await new Promise(resolve => setTimeout(resolve, 40));
      const afterDelayed = {
        home: article.parentNode === origin,
        modal: shell.matches(':modal'),
        sameArticle: document.querySelector('[data-im-inspector-payload]') === article,
        articleVisible: article.getClientRects().length > 0
      };
      const recovered = h.openInspector({ market_id: 'JP', expected_source: 'fixture:v1' });
      const recoveredSnap = { ok: recovered.ok, modal: shell.matches(':modal'), parent: article.parentNode === shell };
      document.querySelector('[data-im-inspector-action="evidence"]').click();
      poisonHeadings();
      const orig = HTMLButtonElement.prototype.setAttribute;
      HTMLButtonElement.prototype.setAttribute = function (name, value) {
        if (name === 'aria-pressed') {
          HTMLButtonElement.prototype.setAttribute = orig;
          throw new Error('paint refused');
        }
        return orig.call(this, name, value);
      };
      let replaced;
      try { replaced = h.replaceSource('fixture:v2', 'fixture:v1'); }
      finally {
        HTMLButtonElement.prototype.setAttribute = orig;
        restoreHeadings();
      }
      nested.click();
      return {
        afterPush,
        afterDelayed,
        recovered: recoveredSnap,
        afterReplace: {
          ok: replaced.ok,
          modal: shell.matches(':modal'),
          inShell: article.parentNode === shell,
          originHidden: origin.hidden,
          articleVisible: article.getClientRects().length > 0,
          home: article.parentNode === origin,
          sameArticle: document.querySelector('[data-im-inspector-payload]') === article,
          sameNested: document.querySelector('.nested-listener') === nested,
          nestedClicks,
          source: h.getState().source_reference,
          enhancementHidden: article.querySelector('[data-im-inspector-enhancement]').hidden
        }
      };
    }, handle);
    assert.equal(out.afterPush.ok, false);
    assert.equal(out.afterPush.modal, false);
    assert.equal(out.afterPush.inShell, false);
    assert.equal(out.afterPush.originHidden, false);
    assert.equal(out.afterPush.articleVisible, true);
    assert.equal(out.afterPush.home, true);
    assert.equal(out.afterPush.sameArticle, true);
    assert.equal(out.afterPush.sameNested, true);
    assert.equal(out.afterPush.nestedClicks, 1);
    assert.equal(out.afterPush.enhancementHidden, true);
    assert.equal(out.afterPush.url, true);
    assert.equal(out.afterPush.state, true);
    assert.equal(out.afterPush.selected, null);
    assert.equal(out.afterDelayed.home, true);
    assert.equal(out.afterDelayed.modal, false);
    assert.equal(out.afterDelayed.sameArticle, true);
    assert.equal(out.afterDelayed.articleVisible, true);
    assert.equal(out.recovered.ok, true);
    assert.equal(out.recovered.modal, true);
    assert.equal(out.recovered.parent, true);
    assert.equal(out.afterReplace.ok, false);
    assert.equal(out.afterReplace.modal, false);
    assert.equal(out.afterReplace.inShell, false);
    assert.equal(out.afterReplace.originHidden, false);
    assert.equal(out.afterReplace.articleVisible, true);
    assert.equal(out.afterReplace.home, true);
    assert.equal(out.afterReplace.sameArticle, true);
    assert.equal(out.afterReplace.sameNested, true);
    assert.equal(out.afterReplace.nestedClicks, 2);
    assert.equal(out.afterReplace.source, 'fixture:v1');
    assert.equal(out.afterReplace.enhancementHidden, true);
  });
});
