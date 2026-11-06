'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');

const reducerSource = fs.readFileSync(path.join(__dirname, '../templates/intl_workspace_state.js'), 'utf8');
const adapterSource = fs.readFileSync(path.join(__dirname, '../templates/intl_workspace.js'), 'utf8');
const searchSource = fs.readFileSync(path.join(__dirname, '../templates/intl_library_search.js'), 'utf8');
const stateSource = fs.readFileSync(path.join(__dirname, '../templates/intl_workspace_state.js'), 'utf8');

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

const libraryGroups = ['leaders', 'recovery', 'policy', 'backdrop', 'pressure', 'challenge'];
const libraryCatalogue = [
  {presentation_key:'performance_currency',group_id:'leaders',order:0,label_en:'Performance & currency',label_zh:'表现与汇率',question_en:'Find the leaders',question_zh:'寻找领涨者',aliases:['currency','returns','FX','USD','rank','回报','汇率']},
  {presentation_key:'leadership_rotation',group_id:'leaders',order:1,label_en:'Leadership rotation',label_zh:'领涨轮动',question_en:'Find the leaders',question_zh:'寻找领涨者',aliases:['rank','momentum','排名','动量','轮动']},
  {presentation_key:'cross_country',group_id:'leaders',order:2,label_en:'Cross-country comparison',label_zh:'跨经济体比较',question_en:'Find the leaders',question_zh:'寻找领涨者',aliases:['country','economy','comparison','经济体','比较']},
  {presentation_key:'market_turns',group_id:'recovery',order:3,label_en:'Market turns',label_zh:'市场转折',question_en:'Check the recovery',question_zh:'检查修复',aliases:['trend','repair','turns','拐点','趋势','修复']},
  {presentation_key:'recovery_quality',group_id:'recovery',order:4,label_en:'Recovery quality',label_zh:'修复质量',question_en:'Check the recovery',question_zh:'检查修复',aliases:['recovery','confirmation','quality','修复','确认']},
  {presentation_key:'participation_concentration',group_id:'recovery',order:5,label_en:'Participation & concentration',label_zh:'参与度与集中度',question_en:'Check the recovery',question_zh:'检查修复',aliases:['breadth','constituents','广度','成分股','集中度']},
  {presentation_key:'rates_curves_carry',group_id:'policy',order:6,label_en:'Rates, curves & carry',label_zh:'利率、曲线与息差',question_en:'Follow policy divergence',question_zh:'跟踪政策分化',aliases:['rates','yield','curve','carry','利率','收益率','曲线','息差']},
  {presentation_key:'central_banks_liquidity',group_id:'policy',order:7,label_en:'Central banks & liquidity',label_zh:'央行与流动性',question_en:'Follow policy divergence',question_zh:'跟踪政策分化',aliases:['central','banks','policy','liquidity','央行','政策','流动性']},
  {presentation_key:'credit_bonds',group_id:'policy',order:8,label_en:'Credit & bonds',label_zh:'信用与债券',question_en:'Follow policy divergence',question_zh:'跟踪政策分化',aliases:['credit','bonds','spreads','信用','债券','利差']},
  {presentation_key:'euro_fragmentation',group_id:'backdrop',order:9,label_en:'Euro-area fragmentation',label_zh:'欧元区分化',question_en:'Understand the backdrop',question_zh:'理解背景',aliases:['euro','fragmentation','欧元区','分化']},
  {presentation_key:'growth_inflation',group_id:'backdrop',order:10,label_en:'Growth & inflation',label_zh:'增长与通胀',question_en:'Understand the backdrop',question_zh:'理解背景',aliases:['growth','inflation','cycle','GDP','CPI','增长','通胀','周期']},
  {presentation_key:'dollar_conditions',group_id:'backdrop',order:11,label_en:'Dollar conditions',label_zh:'美元环境',question_en:'Understand the backdrop',question_zh:'理解背景',aliases:['dollar','funding','USD','美元','融资']},
  {presentation_key:'structural_fragility',group_id:'pressure',order:12,label_en:'Structural fragility',label_zh:'结构性脆弱性',question_en:'Trace the pressure',question_zh:'追踪压力',aliases:['fragility','debt','current','account','脆弱','债务','经常账户']},
  {presentation_key:'contagion',group_id:'pressure',order:13,label_en:'Contagion',label_zh:'传导',question_en:'Trace the pressure',question_zh:'追踪压力',aliases:['contagion','spillover','transmission','传导','溢出']},
  {presentation_key:'trade_supply_links',group_id:'pressure',order:14,label_en:'Trade & supply links',label_zh:'贸易与供应链联系',question_en:'Trace the pressure',question_zh:'追踪压力',aliases:['trade','supply','chain','exposure','贸易','供应链','敞口']},
  {presentation_key:'cross_market_correlation',group_id:'challenge',order:15,label_en:'Cross-market correlation',label_zh:'跨市场相关性',question_en:'Challenge the conclusion',question_zh:'检验结论',aliases:['cross market','correlation','diversification','相关性','分散']},
  {presentation_key:'risk_track_record',group_id:'challenge',order:16,label_en:'Risk-radar track record',label_zh:'风险雷达记录',question_en:'Challenge the conclusion',question_zh:'检验结论',aliases:['track','record','false','alarms','accuracy','记录','误报','验证']},
  {presentation_key:'country_sectors_stocks',group_id:'challenge',order:17,label_en:'Country sectors & stocks',label_zh:'经济体板块与股票',question_en:'Challenge the conclusion',question_zh:'检验结论',aliases:['sectors','stocks','industry','板块','股票','行业']}
];

function libraryMarkup() {
  const rows = libraryCatalogue.map(tool => `
    <li class="intl-library__tool" data-im-library-tool="${tool.presentation_key}" data-im-library-order="${tool.order}">
      <p><span class="l-en">${tool.label_en}</span><span class="l-zh">${tool.label_zh}</span></p>
      <p><span class="l-en">${tool.question_en}</span><span class="l-zh">${tool.question_zh}</span></p>
    </li>`).join('');
  const groups = libraryGroups.map((groupId, index) => `
    <section class="intl-library__group" data-im-library-group="${groupId}">
      <button class="intl-library__group-open" type="button" data-im-library-group-open data-im-action="set_library_group" data-im-group="${groupId}" hidden>Open ${groupId}</button>
      <h3 class="intl-library__group-heading" tabindex="-1">${groupId}</h3>
      <ol class="intl-library__tools" data-im-library-tools="${groupId}">${libraryCatalogue.filter(tool => tool.group_id === groupId).map(tool => rows.match(new RegExp(`<li[^>]*data-im-library-tool="${tool.presentation_key}"[\\s\\S]*?</li>`))[0]).join('')}</ol>
    </section>`).join('');
  return `
    <section class="intl-library" data-im-panel data-view="library" data-im-library-static data-horizon="1m" data-basis="usd_unhedged" data-source="fixture:v1" data-im-library-generation="test-generation">
      <h2><span class="l-en">Library</span><span class="l-zh">工具库</span></h2>
      <form data-im-library-search-form role="search" action="#"><label><span class="l-en">Search tools and questions</span><span class="l-zh">搜索工具与研究问题</span></label><input type="search" data-im-library-search autocomplete="off" disabled><button type="button" data-im-library-clear disabled>Clear</button><p data-im-library-status role="status" aria-live="polite"></p></form>
      <div data-im-library-groups>${groups}</div>
      <ol data-im-library-results hidden></ol>
      <p data-im-library-empty hidden>No tools match</p>
      <button type="button" data-im-library-back data-im-action="set_library_group" hidden>Back</button>
      <script type="application/json" data-im-library-catalogue>${JSON.stringify(libraryCatalogue)}</script>
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
    await page.addScriptTag({ content: searchSource });
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

function libraryConfig() {
  return { ...config, library_group_ids: libraryGroups };
}

function libraryWorkspace() {
  return workspaceMarkup().replace(
    /<p data-im-unavailable>No matching payload<\/p>/,
    `${libraryMarkup()}<p data-im-unavailable>No matching payload</p>`
  );
}

async function mountLibrary(page, query = '?view=library&market=&pins=&horizon=1m&basis=usd_unhedged&return_basis=price&group=') {
  await bootstrapPage(page, libraryWorkspace(), query);
  return page.evaluateHandle(config => IntlWorkspace.mountIntlWorkspace(document.querySelector('[data-im-workspace]'), config), libraryConfig());
}


const keys = page => page.locator('[data-im-library-results] [data-im-library-tool]').evaluateAll(nodes => nodes.map(n => n.dataset.imLibraryTool));

test('Library mount enables search and preserves the exact original row identities on destroy', async () => {
  await withPage(async page => {
    await bootstrapPage(page, libraryWorkspace(), '?view=library');
    const result = await page.evaluate(cfg => {
      const root=document.querySelector('[data-im-workspace]'), rows=[...root.querySelectorAll('[data-im-library-tool]')];
      const original=root.outerHTML; let clicks=0; rows[0].addEventListener('click',()=>clicks++);
      const handle=IntlWorkspace.mountIntlWorkspace(root,cfg);
      const enabled=!root.querySelector('[data-im-library-search]').disabled;
      const sameHandle=handle===IntlWorkspace.mountIntlWorkspace(root,cfg);
      const input=root.querySelector('[data-im-library-search]'); input.value='currency';input.dispatchEvent(new Event('input',{bubbles:true}));
      handle.destroy(); rows[0].click();
      return {enabled,sameHandle,dom:root.outerHTML===original,same:rows.every((n,i)=>n===root.querySelectorAll('[data-im-library-tool]')[i]),clicks};
    },libraryConfig());
    assert.deepEqual(result,{enabled:true,sameHandle:true,dom:true,same:true,clicks:1});
  });
});

test('search uses accepted bilingual ranking and conjunction without putting the query in the URL', async () => {
  await withPage(async page => {
    await mountLibrary(page); const url=page.url();
    for (const [query,want] of [['cross　market correlation',['cross_market_correlation']],['rank momentum',['leadership_rotation']],['汇率',['performance_currency']]]) {
      await page.fill('[data-im-library-search]',query); assert.deepEqual(await keys(page),want);
    }
    assert.equal(page.url(),url);
    await page.click('[data-im-library-clear]');
    assert.equal(await page.inputValue('[data-im-library-search]'),'');
    assert.equal(await page.locator('[data-im-library-tools] > [data-im-library-tool]').count(),18);
  });
});

test('invalid and empty matches hide stale results without truncating the draft', async () => {
  await withPage(async page => {
    await mountLibrary(page); await page.fill('[data-im-library-search]','currency');
    await page.fill('[data-im-library-search]','unmatched-xyzz');
    assert.deepEqual(await keys(page),[]); assert.equal(await page.locator('[data-im-library-empty]').isVisible(),true);
    await page.fill('[data-im-library-search]','a'.repeat(257));
    assert.equal(await page.inputValue('[data-im-library-search]'),'a'.repeat(257));
    assert.equal(await page.locator('[data-im-library-results]').isHidden(),true);
    assert.equal(await page.locator('[data-im-library-empty]').isHidden(),true);
    assert.match(await page.textContent('[data-im-library-status]'),/invalid/i);
  });
});

test('IME keeps committed results throughout interim input and language changes', async () => {
  await withPage(async page => {
    await mountLibrary(page); await page.fill('[data-im-library-search]','currency');
    await page.locator('[data-im-library-search]').evaluate(input=>{
      input.dispatchEvent(new CompositionEvent('compositionstart',{bubbles:true})); input.value='轮';
      input.dispatchEvent(new InputEvent('input',{bubbles:true,isComposing:true}));
    });
    assert.deepEqual(await keys(page),['performance_currency']);
    await page.evaluate(()=>document.documentElement.setAttribute('lang','zh-CN'));
    assert.deepEqual(await keys(page),['performance_currency']);
    await page.locator('[data-im-library-search]').evaluate(input=>{input.value='轮动';input.dispatchEvent(new CompositionEvent('compositionend',{bubbles:true}));});
    assert.deepEqual(await keys(page),['leadership_rotation']);
    assert.equal(await page.getAttribute('[data-im-library-search]','placeholder'),'工具名称、问题或别名');
  });
});

test('group navigation focuses visible destinations, Clear preserves group and Back preserves draft', async () => {
  await withPage(async page => {
    const handle=await mountLibrary(page);
    await page.click('[data-im-group="leaders"][data-im-library-group-open]');
    assert.equal(await page.evaluate(()=>document.activeElement.tagName),'H3');
    assert.equal(await page.locator('[data-im-library-group]:visible').count(),1);
    await page.fill('[data-im-library-search]','rank momentum');
    await page.click('[data-im-library-clear]');
    assert.equal(await page.evaluate(h=>h.getState().library_group,handle),'leaders');
    assert.equal(await page.evaluate(()=>document.activeElement.hasAttribute('data-im-library-search')),true);
    await page.fill('[data-im-library-search]','rank momentum');
    await page.click('[data-im-library-back]');
    assert.equal(await page.inputValue('[data-im-library-search]'),'rank momentum');
    assert.equal(await page.evaluate(h=>h.getState().library_group,handle),null);
    assert.equal(await page.evaluate(()=>document.activeElement.hasAttribute('data-im-library-search')),true);
    await page.click('[data-im-library-clear]');
    await page.click('[data-im-group="recovery"][data-im-library-group-open]');
    await page.click('[data-im-library-back]');
    assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('data-im-group')),'recovery');
  });
});

test('browser history restores group state while preserving the local search draft', async () => {
  await withPage(async page => {
    const handle=await mountLibrary(page);
    await page.click('[data-im-group="leaders"][data-im-library-group-open]');
    await page.fill('[data-im-library-search]','rank momentum');
    await page.click('[data-im-library-back]');
    await page.goBack();
    assert.equal(await page.evaluate(h=>h.getState().library_group,handle),'leaders');
    assert.equal(await page.inputValue('[data-im-library-search]'),'rank momentum');
    assert.deepEqual(await keys(page),['leadership_rotation']);
  });
});

test('one metadata panel follows horizon and basis without changing source identity', async () => {
  await withPage(async page => {
    const handle=await mountLibrary(page);
    await page.evaluate(h=>h.dispatch({type:'set_horizon',horizon:'3m'}),handle);
    await page.evaluate(h=>h.dispatch({type:'set_basis',currency_basis:'local'}),handle);
    assert.equal(await page.locator('[data-im-library-static]').isVisible(),true);
    assert.equal(await page.getAttribute('[data-im-library-static]','data-horizon'),'3m');
    assert.equal(await page.getAttribute('[data-im-library-static]','data-basis'),'local');
    assert.equal(await page.getAttribute('[data-im-library-static]','data-source'),'fixture:v1');
    await page.evaluate(h=>h.replaceSource('fixture:v2','fixture:v1'),handle);
    assert.equal(await page.locator('[data-im-library-static]').isHidden(),true);
    assert.equal(await page.getAttribute('[data-im-library-static]','data-source'),'fixture:v1');
  });
});

test('history failure restores moved rows, exact DOM and third-party listeners', async () => {
  await withPage(async page => {
    const handle=await mountLibrary(page); await page.fill('[data-im-library-search]','rank');
    const result=await page.evaluate(h=>{
      const root=document.querySelector('[data-im-workspace]'),row=root.querySelector('[data-im-library-tool="leadership_rotation"]');
      let clicks=0;row.addEventListener('click',()=>clicks++);
      const before=root.outerHTML,prev=h.getState(),parent=row.parentNode,next=row.nextSibling,push=history.pushState;
      history.pushState=()=>{throw Error('history refusal');}; let outcome;
      try{outcome=h.dispatch({type:'set_library_group',group_id:'recovery'});}finally{history.pushState=push;}
      row.click();return {ok:outcome.ok,dom:before===root.outerHTML,state:JSON.stringify(prev)===JSON.stringify(h.getState()),same:parent===row.parentNode&&next===row.nextSibling,clicks};
    },handle);
    assert.deepEqual(result,{ok:false,dom:true,state:true,same:true,clicks:1});
  });
});

for (const kind of ['malformed','duplicate','wrong-group']) test(`catalogue ${kind} refuses enhancement but keeps approved static rows readable`, async()=>{
  await withPage(async page=>{
    await bootstrapPage(page,libraryWorkspace(),'?view=library');
    await page.evaluate(kind=>{
      const script=document.querySelector('[data-im-library-catalogue]');
      if(kind==='malformed')script.textContent='{broken';
      else{const c=JSON.parse(script.textContent);if(kind==='duplicate')c[1]={...c[0]};else c[0].group_id='policy';script.textContent=JSON.stringify(c);}
    },kind);
    await page.evaluate(cfg=>IntlWorkspace.mountIntlWorkspace(document.querySelector('[data-im-workspace]'),cfg),libraryConfig());
    assert.equal(await page.locator('[data-im-library-search]').isDisabled(),true);
    assert.equal(await page.getAttribute('[data-im-library-static]','data-im-library-enhanced'),null);
    assert.equal(await page.locator('[data-im-library-tool]:visible').count(),18);
  });
});

test('failed setup restores original rows, control attributes and node identity', async()=>{
  await withPage(async page=>{
    await bootstrapPage(page,libraryWorkspace(),'?view=library');
    const result=await page.evaluate(cfg=>{
      const root=document.querySelector('[data-im-workspace]'),before=root.outerHTML,rows=[...root.querySelectorAll('[data-im-library-tool]')],Observer=MutationObserver;
      window.MutationObserver=class{constructor(){throw Error('setup refused');}};let refused=false;
      try{IntlWorkspace.mountIntlWorkspace(root,cfg);}catch{refused=true;}finally{window.MutationObserver=Observer;}
      return {refused,dom:root.outerHTML===before,same:rows.every((n,i)=>n===root.querySelectorAll('[data-im-library-tool]')[i])};
    },libraryConfig());
    assert.deepEqual(result,{refused:true,dom:true,same:true});
  });
});

test('nested workspaces cannot supply catalogue rows or controls to the parent', async()=>{
  await withPage(async page=>{
    const nested='<section data-im-workspace data-im-mode="macro" id="nested"><input data-im-library-search value="private"><li data-im-library-tool="private" data-im-library-order="99">private</li></section>';
    await bootstrapPage(page,libraryWorkspace().replace('<div data-im-library-groups>',nested+'<div data-im-library-groups>'),'?view=library');
    const before=await page.locator('#nested').evaluate(n=>n.outerHTML);
    const handle=await page.evaluateHandle(cfg=>IntlWorkspace.mountIntlWorkspace(document.querySelector('[data-im-workspace]'),cfg),libraryConfig());
    await page.locator('[data-im-library-search-form] input').fill('currency');
    assert.deepEqual(await keys(page),['performance_currency']);
    await page.evaluate(h=>h.destroy(),handle);
    assert.equal(await page.locator('#nested').evaluate(n=>n.outerHTML),before);
  });
});

test('submitting the search form stays local and hash navigation retains query state', async()=>{
  await withPage(async page=>{
    const handle=await mountLibrary(page);await page.fill('[data-im-library-search]','currency');const before=page.url();
    await page.locator('[data-im-library-search]').press('Enter');assert.equal(page.url(),before);
    await page.evaluate(()=>{history.pushState(null,'',location.pathname+location.search+'#research-origin');dispatchEvent(new PopStateEvent('popstate'));});
    assert.equal(await page.inputValue('[data-im-library-search]'),'currency');
    assert.deepEqual(await keys(page),['performance_currency']);
    assert.equal(await page.evaluate(h=>h.getState().view,handle),'library');
  });
});

test('failed search paint restores the committed draft and matching result nodes',async()=>{
  await withPage(async page=>{
    await mountLibrary(page);await page.fill('[data-im-library-search]','currency');
    const result=await page.evaluate(()=>{
      const input=document.querySelector('[data-im-library-search]'),results=document.querySelector('[data-im-library-results]');
      const node=results.firstElementChild,append=results.appendChild;
      results.appendChild=()=>{throw Error('paint refused');};
      try{input.value='growth';input.dispatchEvent(new Event('input',{bubbles:true}));}finally{results.appendChild=append;}
      return {query:input.value,same:results.firstElementChild===node,key:results.firstElementChild?.getAttribute('data-im-library-tool')};
    });
    assert.deepEqual(result,{query:'currency',same:true,key:'performance_currency'});
  });
});

test('a group outside the search-owned container refuses enhancement',async()=>{
  await withPage(async page=>{
    await bootstrapPage(page,libraryWorkspace(),'?view=library');
    await page.evaluate(()=>{document.querySelector('[data-im-library-static]').appendChild(document.querySelector('[data-im-library-group]'));});
    await page.evaluate(cfg=>IntlWorkspace.mountIntlWorkspace(document.querySelector('[data-im-workspace]'),cfg),libraryConfig());
    assert.equal(await page.locator('[data-im-library-search]').isDisabled(),true);
    assert.equal(await page.locator('[data-im-library-tool]:visible').count(),18);
  });
});

for (const query of ['', 'currency']) test('focused Library item survives resize and language repaint: '+(query||'groups'),async()=>{
  await withPage(async page=>{
    await mountLibrary(page);
    if(query)await page.fill('[data-im-library-search]',query);
    const row=page.locator('[data-im-library-tool="performance_currency"]');
    await row.evaluate(n=>{const a=document.createElement('a');a.href='#research-origin';a.textContent='Open';n.appendChild(a);a.focus();});
    await page.evaluate(()=>dispatchEvent(new Event('resize')));
    assert.equal(await row.locator('a').evaluate(n=>document.activeElement===n),true);
    await page.evaluate(()=>document.documentElement.setAttribute('lang','zh'));
    await page.waitForTimeout(20);
    assert.equal(await row.locator('a').evaluate(n=>document.activeElement===n),true);
  });
});
