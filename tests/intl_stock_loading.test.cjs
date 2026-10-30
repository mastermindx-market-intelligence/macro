'use strict';
// Actual Jinja shell and inline lookup controller. Supplied records and chart/MTF
// doubles isolate lookup ordering; this is not data, chart, or live acceptance.
const test = require('node:test');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const {chromium} = require('playwright');
const ROOT = path.resolve(__dirname, '..');
const html = execFileSync(process.env.INTL_TEST_PYTHON || 'python3', ['-c', `
import json
from jinja2 import Environment, FileSystemLoader
from engine.cycles import STATE_DISPLAY
env = Environment(loader=FileSystemLoader('templates'))
print(env.get_template('intl_stock.html.j2').render(state_display_json=json.dumps(STATE_DISPLAY), generated_utc='fixture UTC'))
`], {cwd: ROOT, encoding: 'utf8', maxBuffer: 4*1024*1024});
let browser;
test.before(async () => { browser = await chromium.launch({headless: true,
  ...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL ? {channel: process.env.PLAYWRIGHT_CHROMIUM_CHANNEL} : {})}); });
test.after(async () => { if (browser) await browser.close(); });

function record(ticker, {limited = false, name = ticker + ' fixture'} = {}) {
  return {ticker, name, asof:'2026-10-01', limited, listed:'2026-09-01', history_days:20,
    ladder:{state:'NEUTRAL', points:[], entry:{}, cycle_plain:{}}, cycle:{}, tech:{price:123},
    fundamentals:{valuation:{pe:17}}, analyst:{}, earnings:{}, positioning:{}};
}
async function renderedStock(page, ticker, name = ticker + ' fixture') {
  // A fulfilled request or network-idle page can precede response.json() and
  // the inline controller's commit. Wait for the actual record being asserted.
  await page.waitForFunction(expected =>
    document.getElementById('r_name').textContent === expected &&
    document.getElementById('result').style.display !== 'none' &&
    document.getElementById('lookup_status').textContent === '', name + ' (' + ticker + ')');
}
async function setup(t, lang = 'en', {initialHash='', indexStatus=200, indexOverrides={}, realChart=false} = {}) {
  const context = await browser.newContext();
  t.after(() => context.close());
  await context.addInitScript(({lang,realChart}) => {
    localStorage.setItem('lang', lang);
    if (!realChart) window.StockChart = {mount(host, ticker) { host.textContent='chart fixture '+ticker; }};
    window.renderMTF = host => { host.textContent='MTF fixture'; };
  }, {lang,realChart});
  const page = await context.newPage(); page.setDefaultTimeout(3000);
  const waiting = new Map(), arrivals = new Map();
  function requested(ticker) { return new Promise(resolve => arrivals.set(ticker, resolve)); }
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.hostname !== 'stock.test') return route.abort();
    if (url.pathname === '/intl_stock.html') return route.fulfill({contentType:'text/html', body:html});
    if (indexOverrides[url.pathname]) return route.fulfill(indexOverrides[url.pathname]);
    if (url.pathname.endsWith('/index.json')) return route.fulfill({status:indexStatus, json:indexStatus!==200 ? {error:'fixture unavailable'} :
      url.pathname.startsWith('/intlstockdata/') ? ['OLD','NEW','RETRY'].map(t=>({t,n:t+' fixture',s:'fixture sector',st:'LIMITED'})) : []});
    if (realChart && ['/chart.js','/lightweight-charts-v5.js'].includes(url.pathname))
      return route.fulfill({contentType:'text/javascript',body:fs.readFileSync(path.join(ROOT,'site',url.pathname.slice(1)),'utf8')});
    if (url.pathname.startsWith('/intlohlc/')) return route.fulfill({json:{o:0,bars:[['2026-10-01',100,1000],['2026-10-02',101,1100]]}});
    if (url.pathname.startsWith('/signals/')) return route.fulfill({status:404,json:{}});
    if (url.pathname.endsWith('/calibration.json')) return route.fulfill({json:{}});
    if (url.pathname.startsWith('/intlstockdata/')) {
      const key = url.pathname.split('/').pop().replace('.json','');
      (waiting.get(key) || waiting.set(key, []).get(key)).push(route);
      if (arrivals.has(key)) { arrivals.get(key)(); arrivals.delete(key); }
      return;
    }
    return route.fulfill({body:'', contentType:url.pathname.endsWith('.js')?'text/javascript':'text/css'});
  });
  const initialRequest=initialHash ? requested(initialHash) : null;
  await page.goto('http://stock.test/intl_stock.html'+(initialHash?'#'+initialHash:''));
  if (!initialHash) await page.waitForLoadState('networkidle');
  async function select(ticker) {
    const pending = requested(ticker);
    await page.evaluate(ticker => { location.hash=ticker; }, ticker);
    await pending;
  }
  async function reply(ticker, payload = record(ticker), status = 200) {
    const routes=waiting.get(ticker);
    assert.ok(routes && routes.length, 'expected retained request for '+ticker);
    await routes.shift().fulfill({status, json:payload});
  }
  return {page, select, reply, requested, initialRequest};
}

for (const oldStatus of [200, 404, 503]) test(`obsolete lookup ${oldStatus} cannot repaint the newer ticker`, async t => {
  const {page, select, reply}=await setup(t);
  await select('OLD'); await select('NEW');
  await reply('NEW', record('NEW', {limited:true}));
  await page.waitForFunction(() => document.querySelector('#r_name').textContent.includes('(NEW)'));
  await reply('OLD', record('OLD'), oldStatus); await page.waitForLoadState('networkidle');
  assert.equal(await page.locator('#r_name').innerText(), 'NEW fixture (NEW)');
  assert.match(await page.locator('#tvbox').innerText(), /NEW/);
  assert.equal(new URL(page.url()).hash, '#NEW');
});

for (const lang of ['en','zh']) for (const status of [404, 503]) test(`current lookup ${status} hides prior analysis ${lang}`, async t => {
  const {page, select, reply}=await setup(t,lang);
  await select('OLD'); await reply('OLD');
  await page.waitForFunction(() => document.getElementById('r_name').textContent === 'OLD fixture (OLD)');
  assert.equal(await page.locator('#result').isVisible(), true);
  assert.match(await page.locator('#tvbox').innerText(), /OLD/);
  await select('MISSING'); await reply('MISSING', {}, status);
  await page.waitForFunction(() => /NOT IN LIBRARY|不在库中|could not be loaded|暂时无法加载/.test(document.getElementById('lookup_status').textContent));
  assert.equal(await page.locator('#result').isVisible(), false, 'old analysis and chart must not be attributed to the failed selection');
  const message=await page.locator('#lookup_status').innerText();
  assert.match(message, /MISSING/);
  assert.match(message, status===404 ? (lang==='zh'?/不在库中/:/NOT IN LIBRARY/) : (lang==='zh'?/暂时无法加载/:/could not be loaded/));
  if (status!==404) assert.doesNotMatch(message, /NOT IN LIBRARY|不在库中/);
  await select('RECOVERED'); await reply('RECOVERED');
  // Network idle does not imply that response.json() and render() have settled.
  await page.waitForFunction(() => document.getElementById('r_name').textContent === 'RECOVERED fixture (RECOVERED)');
  assert.equal(await page.locator('#result').isVisible(), true);
  assert.equal(await page.locator('#lookup_status').innerText(), '');
  assert.equal(await page.locator('#r_name').innerText(), 'RECOVERED fixture (RECOVERED)');
});

test('pending lookup hides prior analysis without moving input focus', async t => {
  const {page, select, reply}=await setup(t);
  await select('OLD'); await reply('OLD'); await renderedStock(page,'OLD');
  await page.locator('#q').focus(); await select('NEXT');
  assert.equal(await page.locator('#result').isVisible(), false);
  assert.equal(await page.locator('#q').evaluate(n=>n===document.activeElement), true);
  assert.match(await page.locator('#lookup_status').innerText(), /NEXT/);
  await reply('NEXT'); await renderedStock(page,'NEXT');
  assert.equal(await page.locator('#result').isVisible(), true);
});

for(const lang of ['en','zh']) for(const limited of [false,true]) {
  test(`stock lookup refuses a record for another identity ${lang} limited=${limited}`,async t=>{
    const {page,select,reply,requested}=await setup(t,lang);
    await select('OLD');await reply('OLD');await renderedStock(page,'OLD');
    await page.evaluate(()=>{
      const mount=StockChart.mount;
      window.identityChartMounts=[];
      StockChart.mount=function(host,ticker){identityChartMounts.push(ticker);return mount.apply(this,arguments);};
    });
    const search=page.locator('#q');await search.focus();
    await select('NEW');
    await reply('NEW',record('OTHER',{limited,name:'Wrong identity'}));
    await page.waitForFunction(()=>document.getElementById('lookup_status').textContent==='' || /could not be loaded|暂时无法加载/.test(document.getElementById('lookup_status').textContent));
    assert.equal(await page.locator('#result').isVisible(),false,'a current request must not publish analysis for a different ticker');
    assert.match(await page.locator('#lookup_status').innerText(),lang==='zh'?/NEW.*暂时无法加载/:/NEW.*could not be loaded/);
    assert.doesNotMatch(await page.locator('#lookup_status').innerText(),/NOT IN LIBRARY|不在库中/);
    assert.doesNotMatch(await page.locator('#r_name').textContent(),/OTHER|Wrong identity/,'reject before touching analysis content');
    assert.deepEqual(await page.evaluate(()=>identityChartMounts),[],'wrong-identity data must not mount a chart');
    assert.equal(await search.evaluate(n=>n===document.activeElement),true);
    assert.equal(new URL(page.url()).hash,'#NEW');
    // Recovery keeps the requested identity and uses the existing same-ticker retry.
    const retried=requested('NEW');
    await search.fill('NEW');await search.press('Enter');await retried;
    await reply('NEW',record('NEW',{limited}));await renderedStock(page,'NEW');
    assert.deepEqual(await page.evaluate(()=>identityChartMounts),['NEW']);
    assert.equal(new URL(page.url()).hash,'#NEW');
  });
}

test('clearing the route invalidates a pending stock response', async t => {
  const {page, select, reply}=await setup(t);
  await select('OLD'); await page.evaluate(() => { location.hash=''; });
  await reply('OLD'); await page.waitForLoadState('networkidle');
  assert.equal(await page.locator('#result').isVisible(), false);
});

test('latest request wins after an explicit same-ticker reselection', async t => {
  const {page, select, reply, requested}=await setup(t);
  await select('RETRY');
  const second=requested('RETRY');
  await page.locator('#q').fill('RETRY');
  await page.locator('#q').press('Enter'); await second;
  // The old request settles first. It must remain hidden until the current one settles.
  const settled=page.waitForEvent('requestfinished',req=>req.url().endsWith('/RETRY.json'));
  await reply('RETRY', record('RETRY',{name:'Obsolete'})); await settled;
  await page.evaluate(()=>new Promise(requestAnimationFrame));
  assert.equal(await page.locator('#result').isVisible(), false);
  await reply('RETRY', record('RETRY',{name:'Current'})); await renderedStock(page,'RETRY','Current');
  assert.equal(await page.locator('#r_name').innerText(), 'Current (RETRY)');
});

test('selecting the same ticker retries a failed lookup through the native search control', async t => {
  const {page, select, reply, requested}=await setup(t);
  await select('RETRY'); await reply('RETRY', {}, 503);
  await page.waitForFunction(()=>document.getElementById('lookup_status').textContent.includes('could not be loaded'));
  const retry=requested('RETRY');
  await page.locator('#q').fill('RETRY'); await page.locator('#q').press('Enter');
  // The visible loading state is the bounded assertion; do not await a request
  // that the broken same-hash path never issued.
  await page.waitForFunction(()=>document.getElementById('lookup_status').textContent.includes('Loading'));
  await retry; await reply('RETRY');
  await page.waitForFunction(()=>document.getElementById('r_name').textContent==='RETRY fixture (RETRY)');
  assert.equal(await page.locator('#r_name').innerText(), 'RETRY fixture (RETRY)');
  assert.equal(await page.locator('#result').isVisible(), true);
});

for (const lang of ['en','zh']) test(`deep-linked record can load when the optional search index fails ${lang}`, async t => {
  const {page, reply, initialRequest}=await setup(t,lang,{initialHash:'DIRECT',indexStatus:503});
  await page.waitForFunction(()=>document.getElementById('lookup_status').textContent.includes('DIRECT'));
  await initialRequest; await reply('DIRECT',record('DIRECT',{limited:true}));
  await renderedStock(page,'DIRECT');
  assert.equal(await page.locator('#r_name').innerText(), 'DIRECT fixture (DIRECT)');
  assert.equal(await page.locator('#result').isVisible(), true);
});

for(const lang of ['en','zh']) test(`foreign stock search survives an unavailable home index ${lang}`,async t=>{
  const {page}=await setup(t,lang,{indexStatus:503,indexOverrides:{
    '/stockdata/index.json':{status:200,json:[{t:'USONLY',n:'US fixture',s:'Fixture sector',st:'LIMITED'}]}
  }});
  const search=page.locator('#q');await search.fill('USONLY');
  assert.equal(await search.getAttribute('aria-expanded'),'true','the failed International index must not suppress a supplied US result');
  const option=page.getByRole('option');
  assert.equal(await option.count(),1);assert.match(await option.innerText(),/USONLY/);
  await search.press('ArrowDown');
  assert.equal(await search.getAttribute('aria-activedescendant'),await option.getAttribute('id'));
  await search.press('Enter');
  await page.waitForURL('http://stock.test/stock.html#USONLY');
  assert.equal(page.url(),'http://stock.test/stock.html#USONLY');
});

test('home and foreign stock indexes both remain searchable when supplied',async t=>{
  const {page,requested,reply}=await setup(t,'en',{indexOverrides:{
    '/stockdata/index.json':{status:200,json:[{t:'USONLY',n:'US fixture',s:'Fixture sector',st:'LIMITED'}]}
  }});
  const search=page.locator('#q');
  await search.fill('USONLY');assert.match(await page.getByRole('option').innerText(),/USONLY/);
  await search.fill('NEW');assert.match(await page.getByRole('option').innerText(),/NEW/);
  const loaded=requested('NEW');await search.press('Enter');await loaded;await reply('NEW');
  await renderedStock(page,'NEW');assert.equal(new URL(page.url()).hash,'#NEW');
});


for (const limited of [false,true]) test(`leaving a ${limited?'limited':'full'} stock retires its fullscreen chart before the next lookup settles`,async t=>{
  const {page,select,reply}=await setup(t,'en',{realChart:true});
  await select('OLD'); await reply('OLD',record('OLD',{limited})); await renderedStock(page,'OLD');
  await page.locator('.bchart-fsbtn').click();
  assert.equal(await page.locator('html').evaluate(n=>n.classList.contains('bchart-lock')),true);
  await page.evaluate(()=>{window.retiredChart=StockChart._cur;});
  await select('NEXT');
  assert.equal(await page.locator('html').evaluate(n=>n.classList.contains('bchart-lock')),false,'pending selection must release hidden fullscreen chart');
  assert.equal(await page.evaluate(()=>retiredChart.chart===null),true);
  await reply('NEXT',record('NEXT',{limited}));
  await page.waitForFunction(()=>StockChart._cur!==retiredChart&&StockChart._cur.ticker==='NEXT'&&StockChart._cur.chart!==null);
  assert.equal(await page.evaluate(()=>StockChart._cur!==retiredChart&&StockChart._cur.chart!==null),true);
});

for(const lang of ['en','zh']) for(const ime of ['composing','legacy229']) test(`stock search Enter does not select a suggestion during IME composition ${lang}/${ime}`,async t=>{
  const {page,requested,reply}=await setup(t,lang);
  await page.locator('#q').fill('NEW');
  await page.locator('#q').evaluate((q,ime)=>q.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',code:'Enter',isComposing:ime==='composing',keyCode:ime==='legacy229'?229:13,bubbles:true,cancelable:true})),ime);
  await page.evaluate(()=>new Promise(requestAnimationFrame));
  assert.equal(new URL(page.url()).hash,'','composition confirmation must not navigate');
  assert.equal(await page.locator('#q').inputValue(),'NEW');
  assert.equal(await page.locator('#sugg').isVisible(),true);
  const loaded=requested('NEW');
  await page.locator('#q').press('Enter'); await loaded; await reply('NEW');
  await page.waitForFunction(()=>document.getElementById('r_name').textContent==='NEW fixture (NEW)');
});

for(const lang of ['en','zh']) test(`stock search exposes its keyboard selection and closes on Escape or blur ${lang}`,async t=>{
  const {page}=await setup(t,lang);
  const search=page.getByRole('combobox',{name:lang==='zh'?'搜索任意 日/韩/台/英/欧 个股…':'Search any JP / KR / TW / UK / EU stock…',exact:true});
  await search.fill('N');
  assert.equal(await search.getAttribute('aria-expanded'),'true');
  const list=page.getByRole('listbox',{name:lang==='zh'?'股票搜索结果':'Stock search results',exact:true});
  assert.equal(await list.getByRole('option').count(),1);
  await search.press('ArrowDown');
  const selected=list.getByRole('option',{selected:true});
  assert.match(await selected.innerText(),/NEW/);
  assert.equal(await search.getAttribute('aria-activedescendant'),await selected.getAttribute('id'));
  assert.equal(await search.evaluate(n=>n===document.activeElement),true);
  await search.press('Escape');
  assert.equal(await search.getAttribute('aria-expanded'),'false');
  assert.equal(await search.getAttribute('aria-activedescendant'),null);
  assert.equal(await list.isVisible(),false);
  await search.fill('NE'); await search.press('Tab');
  assert.equal(await search.getAttribute('aria-expanded'),'false');
  assert.equal(await list.isVisible(),false);
});

for(const lang of ['en','zh']) test(`a malformed stock link leaves search usable ${lang}`,async t=>{
  const {page,requested,reply}=await setup(t,lang,{initialHash:'BAD%'});
  await page.waitForLoadState('networkidle');
  assert.match(await page.locator('#lookup_status').innerText(),lang==='zh'?/链接无效/:/Invalid stock link/);
  assert.equal(await page.locator('#result').isVisible(),false);
  const loaded=requested('NEW');
  await page.locator('#q').fill('NEW'); await page.locator('#q').press('Enter');
  await page.waitForFunction(()=>location.hash==='#NEW');
  await loaded; await reply('NEW');
  await page.waitForFunction(()=>document.getElementById('r_name').textContent==='NEW fixture (NEW)');
});

// Synthetic MMXSharedShell routing double for the shell-hosting cases below.
// Mirrors the page-visible bridge contract only: accepted navigations are
// applied synchronously while acceptance is notified later, as the incumbent
// fragment bridge does. Same-value navigation stays silent. No real handshake,
// parent, or store is simulated; delayed acceptance/refusal are explicit controls.
function installShellDouble() {
  window.__shellNav = [];
  window.__shellEvents = [];
  window.__nativeHashChanges = [];
  window.__shellRefusals = 0;
  window.__shellAcks = [];
  window.__shellQueued = [];
  window.__shellAcceptNext = function () { window.__shellAcks.shift()(); };
  window.__shellActivate = function () {
    window.__shellInactive = false;
    window.__shellQueued.splice(0).forEach(function (apply) { apply(); });
  };
  window.addEventListener('hashchange', function () {
    window.__nativeHashChanges.push(location.hash);
  });
  window.MMXSharedShell = Object.freeze({
    __mmxBridge: 'synthetic-double',
    get active() { return !window.__shellInactive; },
    navigate(href, mode) {
      if (mode !== 'push' && mode !== 'replace') { window.__shellRefusals += 1; return false; }
      if (window.__shellRefuseNext) { window.__shellRefuseNext = false; window.__shellRefusals += 1; return false; }
      var before = location.hash || '';
      window.__shellNav.push({href: href, mode: mode});
      function apply() {
        if (href === before) return;
        history.replaceState(null, '', href || location.pathname);
        function accept() {
          window.__shellEvents.push(href);
          window.dispatchEvent(new Event('mmx:shell-location'));
        }
        if (window.__shellHoldAck) window.__shellAcks.push(accept);
        else queueMicrotask(accept);
      }
      if (window.__shellInactive) window.__shellQueued.push(apply);
      else apply();
      return true;
    },
    openAuth() { return false; }
  });
}

async function shellSetup(t) {
  const h = await setup(t, 'en');
  await h.page.addInitScript(installShellDouble);
  await h.page.goto('http://stock.test/intl_stock.html?shell=1');
  // Plain-host boot: wait for the fixture index like setup does before input.
  await h.page.waitForLoadState('networkidle');
  return h;
}

test('boot deep link loads under the shared shell while the search index is pending', async t => {
  const h = await setup(t, 'en');
  await h.page.addInitScript(installShellDouble);
  // Hold the fresh document's search index: the boot deep link must not wait for it.
  let heldIndex = null;
  await h.page.route('**/intlstockdata/index.json', route => { heldIndex = route; });
  const direct = h.requested('DIRECT');
  await h.page.goto('http://stock.test/intl_stock.html?boot=1#DIRECT');
  await direct;
  await h.reply('DIRECT', record('DIRECT', {limited:true}));
  await renderedStock(h.page, 'DIRECT');
  assert.ok(heldIndex, 'the pending search index must have reached the held route');
  assert.equal(await h.page.evaluate(() => window.__shellNav.length), 0, 'boot reads the canonical hash without a shell navigate');
  assert.deepEqual(await h.page.evaluate(() => window.__nativeHashChanges), []);
  // A query typed against the pending index stays open and completes when it arrives.
  const search = h.page.locator('#q');
  await search.fill('NEW');
  assert.equal(await search.getAttribute('aria-expanded'), 'false');
  await heldIndex.fulfill({status:200, json:['OLD','NEW','RETRY'].map(x=>({t:x,n:x+' fixture',s:'fixture sector',st:'LIMITED'}))});
  await h.page.waitForFunction(() => document.getElementById('q').getAttribute('aria-expanded') === 'true');
  assert.match(await h.page.getByRole('option').innerText(), /NEW/);
});

test('accepted shell routes drive selection and a stale response cannot replace the accepted identity', async t => {
  const {page, requested, reply} = await shellSetup(t);
  const search = page.locator('#q');
  const oldReq = requested('OLD');
  await search.fill('OLD'); await search.press('Enter'); await oldReq;
  const newReq = requested('NEW');
  await search.fill('NEW'); await search.press('Enter'); await newReq;
  await reply('NEW', record('NEW', {name:'Accepted NEW'}));
  await renderedStock(page, 'NEW', 'Accepted NEW');
  await reply('OLD', record('OLD'));
  await page.waitForFunction(() => document.getElementById('r_name').textContent === 'Accepted NEW (NEW)');
  assert.equal(await page.locator('#result').isVisible(), true);
  assert.equal(await page.evaluate(() => location.hash), '#NEW');
  assert.deepEqual(await page.evaluate(() => window.__shellNav), [{href:'#OLD',mode:'push'},{href:'#NEW',mode:'push'}]);
  assert.deepEqual(await page.evaluate(() => window.__shellEvents), ['#OLD', '#NEW']);
  assert.deepEqual(await page.evaluate(() => window.__nativeHashChanges), []);
});

test('same-hash shell reselection still refreshes and a refused navigate changes nothing', async t => {
  const {page, requested, reply} = await shellSetup(t);
  const search = page.locator('#q');
  const first = requested('NEW');
  await search.fill('NEW'); await search.press('Enter'); await first;
  await reply('NEW', record('NEW'));
  await renderedStock(page, 'NEW');
  // The same-value acceptance carries no mmx:shell-location, so re-picking the
  // already-selected ticker must refresh explicitly on its own.
  const refresh = requested('NEW');
  await search.fill('NEW'); await search.press('Enter'); await refresh;
  await reply('NEW', record('NEW', {name:'Refreshed NEW'}));
  await renderedStock(page, 'NEW', 'Refreshed NEW');
  assert.deepEqual(await page.evaluate(() => window.__shellEvents), ['#NEW']);
  assert.deepEqual(await page.evaluate(() => window.__nativeHashChanges), []);
  // A refused navigate must not fall back to a direct hash write or a request.
  await page.evaluate(() => { window.__shellRefuseNext = true; });
  await search.fill('OLD'); await search.press('Enter');
  await page.waitForTimeout(50);
  assert.equal(await page.evaluate(() => location.hash), '#NEW');
  assert.equal(await page.locator('#r_name').innerText(), 'Refreshed NEW (NEW)');
  assert.equal(await page.locator('#result').isVisible(), true);
  await assert.rejects(() => reply('OLD'), /expected retained request/);
  assert.equal(await page.evaluate(() => window.__shellRefusals), 1);
  assert.deepEqual(await page.evaluate(() => window.__nativeHashChanges), []);
});


test('new shell ticker waits for delayed acceptance after synchronous fragment replacement', async t => {
  const {page, select, requested, reply} = await shellSetup(t);
  const search = page.locator('#q');
  await select('OLD');
  await reply('OLD'); await renderedStock(page, 'OLD');
  const requests = [];
  page.on('request', request => { if (request.url().endsWith('/NEW.json')) requests.push(request.url()); });
  await page.evaluate(() => { window.__shellHoldAck = true; });
  await search.fill('NEW'); await search.press('Enter');
  assert.equal(await page.evaluate(() => location.hash), '#NEW', 'bridge has already replaced the fragment');
  await search.fill('NEW'); await search.press('Enter');
  await page.waitForTimeout(50);
  assert.equal(requests.length, 0, 'neither first selection nor a same-fragment repeat may fetch before acceptance');
  assert.equal(await page.locator('#r_name').innerText(), 'OLD fixture (OLD)');
  const accepted = requested('NEW');
  await page.evaluate(() => window.__shellAcceptNext()); await accepted;
  await reply('NEW'); await renderedStock(page, 'NEW');
  assert.equal(requests.length, 1);
});

test('inactive shell queues same-selection navigation without refreshing before activation', async t => {
  const {page, select, requested, reply} = await shellSetup(t);
  const search = page.locator('#q');
  await select('NEW');
  await reply('NEW'); await renderedStock(page, 'NEW');
  const requests = [];
  page.on('request', request => { if (request.url().endsWith('/NEW.json')) requests.push(request.url()); });
  await page.evaluate(() => { window.__shellInactive = true; });
  await search.fill('NEW'); await search.press('Enter');
  await page.waitForTimeout(50);
  assert.equal(requests.length, 0, 'enqueue return is not acceptance of a refresh');
  assert.equal(await page.evaluate(() => window.__shellQueued.length), 1);
  await page.evaluate(() => window.__shellActivate());
  assert.equal(await page.locator('#r_name').innerText(), 'NEW fixture (NEW)');
  assert.deepEqual(await page.evaluate(() => window.__shellEvents), []);
});
