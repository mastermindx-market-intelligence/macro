'use strict';
// Current combined Jinja shell/controller and bundled chart/LWC.
// plus an MTF double isolate locale lifecycle; no live-data or speech acceptance.
const test = require('node:test');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const html = execFileSync(process.env.INTL_TEST_PYTHON || 'python3', ['-c', `
import json
from jinja2 import Environment, FileSystemLoader
from engine.cycles import STATE_DISPLAY
print(Environment(loader=FileSystemLoader('templates')).get_template('intl_stock.html.j2').render(
    state_display_json=json.dumps(STATE_DISPLAY), generated_utc='synthetic timing fixture UTC'))
`], {cwd: root, encoding:'utf8', maxBuffer:4*1024*1024});
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
  const requests=[];page.on('request',r=>{if(r.url().endsWith('.json'))requests.push(r.url());});
  function requested(ticker) { return new Promise(resolve => arrivals.set(ticker, resolve)); }
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.hostname !== 'stock.test') return route.abort();
    if (url.pathname === '/intl_stock.html') return route.fulfill({contentType:'text/html', body:html});
    if (url.pathname === '/theme.css') return route.fulfill({contentType:'text/css',body:fs.readFileSync(path.join(root, 'templates/theme.css'), 'utf8')});
    if (indexOverrides[url.pathname]) return route.fulfill(indexOverrides[url.pathname]);
    if (url.pathname.endsWith('/index.json')) return route.fulfill({status:indexStatus, json:indexStatus!==200 ? {error:'fixture unavailable'} :
      url.pathname.startsWith('/intlstockdata/') ? ['OLD','NEW','RETRY'].map(t=>({t,n:t+' fixture',s:'fixture sector',st:'LIMITED'})) : []});
    if (realChart && ['/chart.js','/lightweight-charts-v5.js'].includes(url.pathname))
      return route.fulfill({contentType:'text/javascript',body:fs.readFileSync(path.join(root, 'site', url.pathname.slice(1)), 'utf8')});
    if (url.pathname.startsWith('/intlohlc/')) return route.fulfill({json:{o:0,bars:Array.from({length:160},(_,i)=>[new Date(Date.UTC(2026,0,1+i)).toISOString().slice(0,10),100+i/10,1000+i])}});
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
  return {page, select, reply, requested, initialRequest, requests};
}




for(const lang of ['en','zh']) for(const foreign of [false,true]) {
  test(`stock suggestion text remains literal ${lang} foreign=${foreign}`,async t=>{
    const ticker=foreign?'FOREIGN':'LOCAL';
    const entry={t:ticker,n:'Literal <Research> & Partners',s:'Tools <Hardware> & "Equipment"',st:'<i>Supplied state</i>',fl:'<em>Region</em>'};
    const index=foreign?'/stockdata/index.json':'/intlstockdata/index.json';
    const {page,requested,reply}=await setup(t,lang,{indexOverrides:{[index]:{status:200,json:[entry]}}});
    const search=page.locator('#q');await search.fill(ticker);
    const option=page.getByRole('option');await option.waitFor();
    assert.equal(await option.locator('small').textContent(),entry.n+' · '+entry.s,'company and sector text must not be parsed as markup');
    assert.equal(await option.locator('b').textContent(),ticker);
    assert.equal(await option.locator('span.muted').textContent(),entry.st);
    assert.equal(await option.locator('span').first().textContent(),entry.fl);
    assert.equal(await option.locator('research,hardware,i,em').count(),0,'supplied text must not create element nodes');
    await search.press('ArrowDown');
    assert.equal(await option.getAttribute('aria-selected'),'true');
    assert.equal(await search.getAttribute('aria-activedescendant'),await option.getAttribute('id'));
    assert.equal(await search.evaluate(n=>n===document.activeElement),true);
    if(foreign){
      await search.press('Enter');await page.waitForURL('http://stock.test/stock.html#'+ticker);
    }else{
      const arrival=requested(ticker);await search.press('Enter');await arrival;
      await reply(ticker,record(ticker));await renderedStock(page,ticker);
      assert.equal(new URL(page.url()).hash,'#'+ticker);
    }
  });
}

for(const lang of ['en','zh']) test(`stock suggestions preserve entity-like text and ordinary localized state ${lang}`,async t=>{
  const ticker='A&B',entry={t:ticker,n:'O\'Reilly &amp; <Tools> "Research"',s:'',st:'LIMITED'};
  const {page,requested,reply}=await setup(t,lang,{indexOverrides:{'/intlstockdata/index.json':{status:200,json:[entry]}}});
  await page.locator('#q').fill(ticker);
  const option=page.getByRole('option');await option.waitFor();
  assert.equal(await option.locator('small').textContent(),entry.n,'entity-like source text remains literal, without a second decode');
  assert.equal(await option.locator('b').textContent(),ticker);
  assert.equal(await option.locator('span.muted').textContent(),lang==='zh'?'新上市 · 历史不足':'new listing · limited history');
  assert.equal(await option.locator('span').first().textContent(),'🌐');
  assert.equal(await option.locator('tools').count(),0);
  const arrival=requested(ticker);await option.click();await arrival;
  await reply(ticker,record(ticker));await renderedStock(page,ticker);
  assert.equal(decodeURIComponent(new URL(page.url()).hash.slice(1)),ticker);
});
