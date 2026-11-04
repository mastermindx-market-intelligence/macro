'use strict';
// INTL-GS deferred contexts (active-page performance repair): the controller
// side of the inert-payload contract.
//
// The Dossier and Coverage contexts are published by the canonical Jinja
// partials as escaped JSON carriers (templates/intl_workspace/shell.html.j2
// + dossier.html.j2). This proof mounts a page whose Dossier and Coverage
// contexts are carried that way and shows that:
//
//   - an inactive context never becomes live DOM, and an inactive
//     jurisdiction never becomes a live article;
//   - selecting a context materializes exactly that context and selecting a
//     jurisdiction materializes exactly that article, with the published
//     identity and content;
//   - a context switch evicts the inactive live DOM and never materializes
//     the same context twice;
//   - a malformed, foreign-generation or duplicated carrier refuses the
//     switch without changing the URL, the state or the live DOM;
//   - destroy returns the page to the canonical no-enhancement state and a
//     remount materializes again;
//   - serialized hostile text never executes;
//   - the strict query contract is unchanged.
const {test, before, after} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');

const root = path.resolve(__dirname, '..');
const stateSource = fs.readFileSync(path.join(root, 'templates/intl_workspace_state.js'), 'utf8');
const adapterSource = fs.readFileSync(path.join(root, 'templates/intl_workspace.js'), 'utf8');

const config = {
  markets: ['JP', 'GB', 'US'],
  horizons: ['1m'],
  bases: ['usd_unhedged'],
  default_horizon: '1m',
  default_basis: 'usd_unhedged',
  source_reference: 'fixture:v1',
  anchor_ids: ['origin'],
  library_group_ids: []
};

const JURISDICTIONS = ['JP', 'GB', 'US'];

// The shell publishes the carriers with Jinja's |tojson, whose HTML-safe
// encoder escapes <, >, & and ' so no closing markup can leave the carrier.
function safeJson(value) {
  return JSON.stringify(value)
    .replace(/&/g, '\\u0026')
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/'/g, '\\u0027');
}

// The carriers below mirror exactly what templates/intl_workspace/shell.html.j2
// publishes: the canonical panel root, hidden, with the escaped markup in a
// <script type="application/json"> carrier and the published jurisdiction
// list on the carrier itself.
function marketCarrier(id, isDefault, body) {
  const markup = `<article class="intl-gs__mkt" data-gs-market="${id}" id="im-gs-dossier-1m-usd_unhedged-${id}"${isDefault ? ' data-gs-market-default' : ''}><p>${body || (id + ' dossier body')}</p></article>`;
  const payload = {
    schema: 'intl-gs-market.v1',
    market_id: id,
    default: !!isDefault,
    markup: markup
  };
  return `<script type="application/json" data-im-gs-market-id="${id}"${isDefault ? ' data-im-gs-market-default' : ''}>${safeJson(payload)}</script>`;
}

function dossierMarkup(contextId, jurisdictions) {
  const scope = jurisdictions.map((id) => marketCarrier(id, id === 'JP')).join('');
  return `<section class="intl-gs__panel intl-gs__view intl-gs__view--dossier" data-im-panel data-gs-panel data-view="dossier" data-horizon="1m" data-basis="usd_unhedged" data-return-basis="price" data-source="fixture:v1" id="${contextId}-dossier" aria-labelledby="${contextId}-dossier-title"><h1 id="${contextId}-dossier-title">Market dossier</h1><nav class="intl-gs__pickerlist"><a data-gs-select-market="JP" href="?view=dossier&amp;market=JP">Japan</a></nav><div class="intl-gs__marketscope" data-gs-market-scope>${scope}</div></section>`;
}

function coverageMarkup(contextId) {
  return `<section class="intl-gs__panel intl-gs__view intl-gs__view--coverage" data-im-panel data-gs-panel data-view="coverage" data-horizon="1m" data-basis="usd_unhedged" data-return-basis="price" data-source="fixture:v1" id="${contextId}-coverage" aria-labelledby="${contextId}-coverage-title"><h1 id="${contextId}-coverage-title">Coverage</h1><p>coverage body</p></section>`;
}

function contextCarrier(view, contextId, markup, markets) {
  const payload = {
    schema: 'intl-gs-deferred.v1',
    view: view,
    context_id: contextId,
    horizon: '1m',
    basis: 'usd_unhedged',
    generation: null,
    markets: markets || [],
    markup: markup
  };
  return `<section class="intl-gs__panel intl-gs__view intl-gs__view--${view}" data-im-panel data-gs-panel data-view="${view}" data-horizon="1m" data-basis="usd_unhedged" data-return-basis="price" data-source="fixture:v1" hidden id="${contextId}-${view}" data-im-deferred="v1" data-im-deferred-markets="${(markets || []).join(',')}"><script type="application/json" data-im-deferred-payload>${safeJson(payload)}</script></section>`;
}

function workspaceMarkup(options) {
  const settings = options || {};
  const contextId = settings.contextId || 'im-gs-dossier-1m-usd_unhedged';
  const jurisdictions = settings.jurisdictions || JURISDICTIONS;
  const dossier = settings.dossier === null ? '' : contextCarrier('dossier', contextId, dossierMarkup(contextId, jurisdictions), jurisdictions);
  const coverage = settings.coverage === null ? '' : contextCarrier('coverage', 'im-gs-coverage-1m-usd_unhedged', coverageMarkup('im-gs-coverage-1m-usd_unhedged'), []);
  return `
    <section data-im-workspace data-im-mode="macro">
      <h1 data-im-heading>International</h1>
      <button data-im-action="set_view" data-im-view="overview">Overview</button>
      <button data-im-action="set_view" data-im-view="dossier">Dossiers</button>
      <button data-im-action="set_view" data-im-view="coverage">Coverage</button>
      <p data-im-issues role="status"></p>
      <p data-im-unavailable hidden>Unavailable</p>
      <article data-im-panel data-view="overview" data-horizon="1m" data-basis="usd_unhedged" data-return-basis="price" data-source="fixture:v1" id="im-overview-0-overview">Overview body</article>
      ${dossier}
      ${coverage}
      <script type="application/json" data-im-config>${JSON.stringify(config)}</script>
    </section>`;
}

let browser;
before(async () => {
  browser = await chromium.launch({headless: true, ...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL ? {channel: process.env.PLAYWRIGHT_CHROMIUM_CHANNEL} : {})});
});
after(async () => { await browser.close(); });

async function fixture(run, options) {
  const settings = options || {};
  const page = await browser.newPage();
  page.setDefaultTimeout(4000);
  try {
    await page.route('http://deferred.test/**', (route) => route.fulfill({
      contentType: 'text/html',
      body: '<!doctype html><html lang="en"><meta charset="utf-8"><style>[hidden]{display:none!important}</style><body>' + workspaceMarkup(settings) + '</body></html>'
    }));
    await page.goto('http://deferred.test/intl.html' + (settings.query || ''));
    await page.evaluate((value) => { window.config = value; window.root = document.querySelector('[data-im-workspace]'); }, config);
    await page.addScriptTag({content: stateSource});
    await page.addScriptTag({content: adapterSource});
    if (settings.mutate) await page.evaluate(settings.mutate);
    if (settings.mount !== false) {
      await page.evaluate(() => { window.handle = IntlWorkspace.mountIntlWorkspace(window.root, window.config); });
    }
    await run(page);
  } finally {
    await page.close();
  }
}

function liveArticles(page) {
  return page.evaluate(() => Array.from(document.querySelectorAll('article[data-gs-market]'))
    .filter((node) => !node.closest('[hidden]'))
    .map((node) => node.getAttribute('data-gs-market')));
}

test('an inactive context and its jurisdictions are published inert, never as live DOM', async () => {
  await fixture(async (page) => {
    const before = await page.evaluate(() => ({
      articles: document.querySelectorAll('article[data-gs-market]').length,
      dossierPanels: document.querySelectorAll('[data-im-panel][data-view="dossier"]:not([hidden])').length,
      carriers: document.querySelectorAll('script[data-im-deferred-payload]').length,
      carrierText: document.querySelector('script[data-im-deferred-payload]').textContent,
      rawMarkup: document.body.innerHTML.indexOf('class="intl-gs__mkt"')
    }));
    assert.equal(before.carriers, 2, 'both contexts are published as carriers');
    assert.equal(before.articles, 0, 'no jurisdiction article is live DOM');
    assert.equal(before.dossierPanels, 0, 'the inactive dossier context is hidden');
    assert.ok(before.carrierText.indexOf('dossier body') !== -1, 'the dossier content is published in the carrier');
    assert.equal(before.rawMarkup, -1, 'no jurisdiction markup is parsed into the document');
  });
});

test('selecting the dossier materializes that context and only the default jurisdiction', async () => {
  await fixture(async (page) => {
    const result = await page.evaluate(() => window.handle.dispatch({type: 'set_view', view: 'dossier'}));
    assert.equal(result.ok, true);
    const state = await page.evaluate(() => ({
      panels: document.querySelectorAll('[data-im-panel][data-view="dossier"]:not([hidden])').length,
      carriersMarked: document.querySelectorAll('[data-im-panel][data-view="dossier"][data-im-deferred-live]').length,
      carriersHidden: document.querySelectorAll('[data-im-panel][data-view="dossier"][data-im-deferred]:not([hidden])').length,
      id: document.querySelector('[data-im-panel][data-view="dossier"]:not([hidden])').getAttribute('id'),
      source: document.querySelector('[data-im-panel][data-view="dossier"]:not([hidden])').getAttribute('data-source'),
      generation: document.querySelector('[data-im-panel][data-view="dossier"]:not([hidden])').getAttribute('data-im-generation'),
      heading: document.querySelector('[data-im-panel][data-view="dossier"] h1').textContent
    }));
    assert.equal(state.panels, 1, 'exactly one live dossier panel');
    assert.equal(state.carriersMarked, 1, 'the carrier is marked as materialized');
    assert.equal(state.carriersHidden, 0, 'the carrier itself stays hidden');
    assert.equal(state.id, 'im-gs-dossier-1m-usd_unhedged-dossier', 'the published context identity is kept');
    assert.equal(state.source, 'fixture:v1', 'the published source binding is kept');
    assert.equal(state.generation, null, 'the published generation sidecar is kept');
    assert.equal(state.heading, 'Market dossier', 'the canonical panel content is materialized');
    assert.deepEqual(await liveArticles(page), ['JP'], 'only the default jurisdiction is live');
  });
});

test('selecting a jurisdiction materializes it and evicts the previous one', async () => {
  await fixture(async (page) => {
    await page.evaluate(() => window.handle.dispatch({type: 'set_view', view: 'dossier'}));
    const selected = await page.evaluate(() => window.handle.dispatch({type: 'select_market', market_id: 'GB'}));
    assert.equal(selected.ok, true);
    assert.deepEqual(await liveArticles(page), ['GB'], 'the selected jurisdiction replaces the previous one');
    const body = await page.evaluate(() => document.querySelector('article[data-gs-market="GB"] p').textContent);
    assert.equal(body, 'GB dossier body', 'the published jurisdiction content is materialized verbatim');
    const visited = await page.evaluate(() => window.handle.dispatch({type: 'select_market', market_id: 'JP'}));
    assert.equal(visited.ok, true);
    assert.deepEqual(await liveArticles(page), ['JP'], 'a visited jurisdiction is not kept live');
  });
});

test('a context switch evicts the inactive live DOM', async () => {
  await fixture(async (page) => {
    await page.evaluate(() => window.handle.dispatch({type: 'set_view', view: 'dossier'}));
    assert.deepEqual(await liveArticles(page), ['JP']);
    await page.evaluate(() => window.handle.dispatch({type: 'set_view', view: 'coverage'}));
    const after = await page.evaluate(() => ({
      articles: document.querySelectorAll('article[data-gs-market]').length,
      dossierPanels: document.querySelectorAll('[data-im-panel][data-view="dossier"]:not([hidden])').length,
      coveragePanels: document.querySelectorAll('[data-im-panel][data-view="coverage"]:not([hidden])').length,
      carriers: document.querySelectorAll('script[data-im-deferred-payload]').length
    }));
    assert.equal(after.articles, 0, 'the dossier jurisdiction leaves the live DOM');
    assert.equal(after.dossierPanels, 0, 'the dossier context leaves the live DOM');
    assert.equal(after.coveragePanels, 1, 'the coverage context is live');
    assert.equal(after.carriers, 2, 'both carriers stay published');
  });
});

test('the same context is never materialized twice', async () => {
  await fixture(async (page) => {
    for (const view of ['dossier', 'overview', 'dossier', 'overview', 'dossier']) {
      await page.evaluate((value) => window.handle.dispatch({type: 'set_view', view: value}), view);
    }
    const state = await page.evaluate(() => ({
      panels: document.querySelectorAll('[data-im-panel][data-view="dossier"]:not([hidden])').length,
      marked: document.querySelectorAll('[data-im-panel][data-view="dossier"][data-im-deferred-live]').length,
      articles: document.querySelectorAll('article[data-gs-market]').length
    }));
    assert.equal(state.panels, 1, 'one live dossier panel');
    assert.equal(state.marked, 1, 'the carrier of the live context is marked once');
    assert.equal(state.articles, 1, 'one live jurisdiction article');
  });
});

test('a malformed carrier refuses the switch without changing URL, state or live DOM', async () => {
  await fixture(async (page) => {
    const outcome = await page.evaluate(() => {
      const carrier = document.querySelector('script[data-im-deferred-payload]');
      carrier.textContent = '{"schema":"intl-gs-deferred.v1","markup":';
      const before = {url: location.href, state: JSON.stringify(window.handle.getState())};
      const result = window.handle.dispatch({type: 'set_view', view: 'dossier'});
      return {
        ok: result.ok,
        code: result.issues[0] && result.issues[0].code,
        url: location.href,
        state: JSON.stringify(window.handle.getState()),
        before: before,
        live: document.querySelectorAll('[data-im-panel][data-view="dossier"]:not([hidden])').length,
        articles: document.querySelectorAll('article[data-gs-market]').length
      };
    });
    assert.equal(outcome.ok, false, 'the switch is refused');
    assert.equal(outcome.code, 'NO_MATCHING_PANEL');
    assert.equal(outcome.url, outcome.before.url, 'the URL is unchanged');
    assert.equal(outcome.state, outcome.before.state, 'the state is unchanged');
    assert.equal(outcome.live, 0, 'no live dossier panel leaks');
    assert.equal(outcome.articles, 0, 'no live jurisdiction article leaks');
  });
});

test('a foreign-generation carrier refuses the switch', async () => {
  await fixture(async (page) => {
    const outcome = await page.evaluate(() => {
      const carrier = document.querySelector('script[data-im-deferred-payload]');
      const payload = JSON.parse(carrier.textContent);
      payload.generation = 'im-workspace-generation:99999999-9999-4999-8999-999999999999';
      carrier.textContent = JSON.stringify(payload);
      const before = {url: location.href, state: JSON.stringify(window.handle.getState())};
      const result = window.handle.dispatch({type: 'set_view', view: 'dossier'});
      return {ok: result.ok, url: location.href, state: JSON.stringify(window.handle.getState()), before: before};
    });
    assert.equal(outcome.ok, false, 'the switch is refused');
    assert.equal(outcome.url, outcome.before.url, 'the URL is unchanged');
    assert.equal(outcome.state, outcome.before.state, 'the state is unchanged');
  });
});

test('a duplicated carrier for the same context refuses the switch', async () => {
  await fixture(async (page) => {
    const outcome = await page.evaluate(() => {
      const carrier = document.querySelector('[data-im-deferred]');
      const clone = carrier.cloneNode(true);
      carrier.parentNode.appendChild(clone);
      const before = {url: location.href, state: JSON.stringify(window.handle.getState())};
      const result = window.handle.dispatch({type: 'set_view', view: 'dossier'});
      return {ok: result.ok, url: location.href, state: JSON.stringify(window.handle.getState()), before: before,
        live: document.querySelectorAll('[data-im-panel][data-view="dossier"]:not([hidden])').length};
    });
    assert.equal(outcome.ok, false, 'the switch is refused');
    assert.equal(outcome.url, outcome.before.url, 'the URL is unchanged');
    assert.equal(outcome.state, outcome.before.state, 'the state is unchanged');
    assert.equal(outcome.live, 0, 'no live dossier panel leaks');
  });
});

test('destroy returns the canonical no-enhancement state and a remount materializes again', async () => {
  await fixture(async (page) => {
    await page.evaluate(() => window.handle.dispatch({type: 'set_view', view: 'dossier'}));
    const after = await page.evaluate(() => {
      window.handle.destroy();
      return {
        enhanced: document.querySelector('[data-im-workspace]').hasAttribute('data-im-enhanced'),
        panels: document.querySelectorAll('[data-im-panel][data-view="dossier"]:not([hidden])').length,
        articles: document.querySelectorAll('article[data-gs-market]').length,
        marked: document.querySelectorAll('[data-im-deferred-live]').length,
        carriers: document.querySelectorAll('script[data-im-deferred-payload]').length
      };
    });
    assert.equal(after.enhanced, false, 'the workspace is not enhanced any more');
    assert.equal(after.panels, 0, 'the materialized context leaves the DOM');
    assert.equal(after.articles, 0, 'the materialized jurisdiction leaves the DOM');
    assert.equal(after.marked, 0, 'no carrier keeps a live marker');
    assert.equal(after.carriers, 2, 'the published carriers are restored');
    const remounted = await page.evaluate(() => {
      const handle = IntlWorkspace.mountIntlWorkspace(window.root, window.config);
      handle.dispatch({type: 'set_view', view: 'dossier'});
      return {
        panels: document.querySelectorAll('[data-im-panel][data-view="dossier"]:not([hidden])').length,
        articles: document.querySelectorAll('article[data-gs-market]').length
      };
    });
    assert.equal(remounted.panels, 1, 'the remount materializes the context again');
    assert.equal(remounted.articles, 1, 'the remount materializes one jurisdiction again');
  });
});

test('serialized hostile text never executes', async () => {
  await fixture(async (page) => {
    const outcome = await page.evaluate(() => {
      const carrier = document.querySelector('script[data-im-deferred-payload]');
      const payload = JSON.parse(carrier.textContent);
      payload.markup = payload.markup.replace('</h1>',
        '</h1><script>window.__pwned = "script";</script><img src="x" onerror="window.__pwned = \'handler\'">');
      carrier.textContent = JSON.stringify(payload);
      window.handle.dispatch({type: 'set_view', view: 'dossier'});
      const panel = document.querySelector('[data-im-panel][data-view="dossier"]:not([hidden])');
      return {
        pwned: window.__pwned === undefined ? null : window.__pwned,
        executable: Array.from(panel.querySelectorAll('script'))
          .filter((node) => (node.getAttribute('type') || '').trim().toLowerCase() !== 'application/json').length,
        handlers: panel.querySelectorAll('[onerror]').length,
        carriers: panel.querySelectorAll('script[data-im-gs-market-id]').length
      };
    });
    assert.equal(outcome.pwned, null, 'nothing from the serialized markup executes');
    assert.equal(outcome.executable, 0, 'no executable script is materialized');
    assert.equal(outcome.handlers, 0, 'no inline event handler is materialized');
    assert.equal(outcome.carriers, 3, 'the jurisdiction carriers stay inert JSON');
  });
});

test('the strict query contract is unchanged', async () => {
  await fixture(async (page) => {
    assert.equal(await page.textContent('[data-im-issues]'), '', 'a clean query reports no issue');
  }, {query: '?view=overview&market=&pins=&horizon=1m&basis=usd_unhedged&return_basis=price&group='});
  await fixture(async (page) => {
    assert.equal(await page.textContent('[data-im-issues]'), 'Invalid URL state restored',
      'an unknown query field is still refused');
  }, {query: '?bad=1'});
  await fixture(async (page) => {
    assert.equal(await page.textContent('[data-im-issues]'), 'Invalid URL state restored',
      'a duplicated query field is still refused');
  }, {query: '?view=overview&view=dossier&market=&pins=&horizon=1m&basis=usd_unhedged&return_basis=price&group='});
});

test('post-materialization history failure restores prior jurisdiction and URL', async () => {
  await fixture(async (page) => {
    assert.equal((await page.evaluate(() => window.handle.dispatch({type:'set_view',view:'dossier'}))).ok, true);
    const outcome = await page.evaluate(() => {
      const before={url:location.href,state:JSON.stringify(handle.getState())};
      const original=history.pushState; history.pushState=()=>{throw new Error('test history failure');};
      const result=handle.dispatch({type:'select_market',market_id:'GB'});
      history.pushState=original;
      return {ok:result.ok,before,url:location.href,state:JSON.stringify(handle.getState())};
    });
    assert.equal(outcome.ok,false); assert.equal(outcome.url,outcome.before.url);
    assert.equal(outcome.state,outcome.before.state); assert.deepEqual(await liveArticles(page),['JP']);
  });
});

test('duplicate jurisdiction/default and context mismatch cannot materialize', async () => {
  for (const mutation of ['duplicate','default','context']) {
    await fixture(async(page)=>{
      const result=await page.evaluate((kind)=>{
        const script=document.querySelector('script[data-im-deferred-payload]'),payload=JSON.parse(script.textContent);
        if(kind==='context') payload.context_id='foreign';
        else {
          const template=document.createElement('template');template.innerHTML=payload.markup;
          const first=template.content.querySelector('script[data-im-gs-market-id]');
          if(kind==='duplicate') first.after(first.cloneNode(true));
          else template.content.querySelectorAll('script[data-im-gs-market-id]')[1].setAttribute('data-im-gs-market-default','');
          payload.markup=template.innerHTML;
        }
        script.textContent=JSON.stringify(payload);
        return handle.dispatch({type:'set_view',view:'dossier'});
      },mutation);
      assert.equal(result.ok,false);assert.deepEqual(await liveArticles(page),[]);
    });
  }
});

test('configured markets remain authoritative over a broader inert domain', async()=>{
  await fixture(async(page)=>{
    assert.equal((await page.evaluate(()=>handle.dispatch({type:'set_view',view:'dossier'}))).ok,true);
    const result=await page.evaluate(()=>handle.dispatch({type:'select_market',market_id:'CN'}));
    assert.equal(result.ok,false);assert.deepEqual(await liveArticles(page),['JP']);
  },{jurisdictions:['JP','GB','US','CN']});
});
