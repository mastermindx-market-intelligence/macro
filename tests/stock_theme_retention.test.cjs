'use strict';
// Actual Jinja shell and inline lookup controller. Supplied records and chart/MTF
// doubles isolate lookup ordering; this is not data, chart, or live acceptance.
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


for(const lang of ['en','zh'])for(const fullscreen of [false,true]) {
  test(`stock theme changes preserve the active chart ${lang} fullscreen=${fullscreen}`,async t=>{
    const {page,select,reply,requests}=await setup(t,lang,{realChart:true});
    await select('CURRENT');await reply('CURRENT',record('CURRENT',{limited:true}));
    await renderedStock(page,'CURRENT');
    await page.waitForFunction(()=>StockChart._cur && StockChart._cur.S.price);
    const weekly=page.locator('[data-tf="1W"]');await weekly.click();
    await page.locator('[data-k="rsi"]').click();
    if(fullscreen)await page.locator('.bchart-fsbtn').click();
    await weekly.focus();
    await page.evaluate(()=>{
      window.originalChart=StockChart._cur;
      originalChart.chart.timeScale().setVisibleLogicalRange({from:3,to:15});
    });
    await page.evaluate(()=>new Promise(requestAnimationFrame));
    const before=await page.evaluate(()=>originalChart.chart.timeScale().getVisibleLogicalRange());
    const recordRequests=requests.filter(u=>u.endsWith('/CURRENT.json')).length;
    for(const theme of ['light','dark']) {
      await page.evaluate(theme=>{document.documentElement.setAttribute('data-theme',theme);document.dispatchEvent(new Event('themechange'));},theme);
      await page.evaluate(()=>new Promise(requestAnimationFrame));
      assert.equal(await page.evaluate(()=>originalChart._destroyed),false,'a presentation preference must not retire the selected chart');
      assert.equal(await page.evaluate(()=>StockChart._cur===originalChart),true);
      assert.equal(await page.evaluate(()=>originalChart.chart.options().layout.textColor),await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue('--muted').trim()),'the existing chart listener still repaints canonical theme colours');
      assert.equal(await page.locator('#result').isVisible(),true);
      assert.equal(await page.locator('#lookup_status').innerText(),'');
      assert.equal(await weekly.getAttribute('aria-pressed'),'true');
      assert.equal(await page.locator('[data-k="rsi"]').getAttribute('aria-pressed'),'false');
      assert.equal(await weekly.evaluate(n=>n===document.activeElement),true);
      assert.equal(await page.locator('.bchart').evaluate(n=>n.classList.contains('bchart-full')),fullscreen);
      const after=await page.evaluate(()=>originalChart.chart.timeScale().getVisibleLogicalRange());
      assert.ok(Math.abs(before.from-after.from)<0.001 && Math.abs(before.to-after.to)<0.001,'existing visible range survives native theme rerender');
      assert.equal(requests.filter(u=>u.endsWith('/CURRENT.json')).length,recordRequests,'theme changes must not request the same record or OHLC again');
      assert.equal(new URL(page.url()).hash,'#CURRENT');
    }
  });
}

for(const lang of ['en','zh'])test(`theme change preserves pending and failed lookup state ${lang}`,async t=>{
  const {page,select,reply,requests,requested}=await setup(t,lang,{realChart:true});
  await select('RETRY');
  const search=page.locator('#q');await search.focus();
  const loading=await page.locator('#lookup_status').innerText();
  const count=requests.filter(u=>u.endsWith('/RETRY.json')).length;
  await page.evaluate(()=>{document.documentElement.setAttribute('data-theme','light');document.dispatchEvent(new Event('themechange'));});
  await page.evaluate(()=>new Promise(requestAnimationFrame));
  assert.equal(requests.filter(u=>u.endsWith('/RETRY.json')).length,count);
  assert.equal(await page.locator('#lookup_status').innerText(),loading);
  assert.equal(await search.evaluate(n=>n===document.activeElement),true);
  await reply('RETRY',{},503);
  await page.waitForFunction(()=>/could not be loaded|暂时无法加载/.test(document.getElementById('lookup_status').textContent));
  const failed=await page.locator('#lookup_status').innerText();
  await page.evaluate(()=>{document.documentElement.setAttribute('data-theme','dark');document.dispatchEvent(new Event('themechange'));});
  await page.evaluate(()=>new Promise(requestAnimationFrame));
  assert.equal(requests.filter(u=>u.endsWith('/RETRY.json')).length,count);
  assert.equal(await page.locator('#lookup_status').innerText(),failed);
  assert.equal(await search.evaluate(n=>n===document.activeElement),true);
  const retried=requested('RETRY');await search.fill('RETRY');await search.press('Enter');await retried;
  await reply('RETRY',record('RETRY',{limited:true}));await renderedStock(page,'RETRY');
  await page.waitForFunction(()=>StockChart._cur && StockChart._cur.S.price);
  assert.equal(await page.locator('#result').isVisible(),true);
});
