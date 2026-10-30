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



async function setLanguage(page,lang){
  await page.evaluate(lang=>{document.documentElement.setAttribute('data-lang',lang);document.dispatchEvent(new Event('langchange'));},lang);
  await page.evaluate(()=>new Promise(requestAnimationFrame));
}
for(const initial of ['en','zh'])for(const limited of [false,true]) {
  test(`stock language changes retain selected analysis and fullscreen chart ${initial} limited=${limited}`,async t=>{
    const {page,select,reply,requests}=await setup(t,initial,{realChart:true});
    await select('CURRENT');
    const data=record('CURRENT',{limited});data.ladder.summary_line='Synthetic summary';data.ladder.summary_line_zh='合成摘要';
    await reply('CURRENT',data);await renderedStock(page,'CURRENT');
    await page.waitForFunction(()=>StockChart._cur && StockChart._cur.S.price);
    await page.locator('[data-tf="1W"]').click();await page.locator('[data-k="rsi"]').click();
    await page.locator('.bchart-fsbtn').click();await page.locator('[data-tf="1W"]').focus();
    await page.evaluate(()=>{window.originalChart=StockChart._cur;originalChart.chart.timeScale().setVisibleLogicalRange({from:3,to:15});});
    await page.evaluate(()=>new Promise(requestAnimationFrame));
    const range=await page.evaluate(()=>originalChart.chart.timeScale().getVisibleLogicalRange());
    const count=requests.filter(u=>u.endsWith('/CURRENT.json')).length;
    for(const lang of [initial==='en'?'zh':'en',initial]) {
      await setLanguage(page,lang);
      assert.equal(await page.evaluate(()=>originalChart._destroyed),false,'locale repaint must not retire the selected chart');
      assert.equal(await page.evaluate(()=>StockChart._cur===originalChart),true);
      assert.equal(await page.locator('#result').isVisible(),true);
      assert.equal(await page.locator('#lookup_status').innerText(),'');
      assert.equal(requests.filter(u=>u.endsWith('/CURRENT.json')).length,count,'repaint the supplied record without another data request');
      assert.match(await page.locator('#r_asof').innerText(),lang==='zh'?/数据截至/:/data through/);
      if(limited)assert.equal(await page.locator('#r_state').innerText(),lang==='zh'?'历史不足':'LIMITED');
      else assert.equal(await page.locator('#r_summary').textContent(),lang==='zh'?'合成摘要':'Synthetic summary');
      const weekly=page.locator('[data-tf="1W"]');
      assert.equal(await weekly.innerText(),lang==='zh'?'周':'1W');
      assert.equal(await weekly.getAttribute('aria-pressed'),'true');
      assert.equal(await page.locator('[data-k="rsi"]').getAttribute('aria-pressed'),'false');
      assert.equal(await weekly.evaluate(n=>n===document.activeElement),true);
      assert.equal(await page.locator('.bchart').evaluate(n=>n.classList.contains('bchart-full')),true);
      const after=await page.evaluate(()=>originalChart.chart.timeScale().getVisibleLogicalRange());
      assert.ok(Math.abs(after.from-range.from)<0.001 && Math.abs(after.to-range.to)<0.001);
      assert.equal(new URL(page.url()).hash,'#CURRENT');
    }
    // A real ticker change still retires the old chart and cannot reuse its record.
    await select('NEXT');assert.equal(await page.evaluate(()=>originalChart._destroyed),true);
    assert.equal(await page.locator('#result').isVisible(),false);
    await reply('NEXT',record('NEXT',{limited}));await renderedStock(page,'NEXT');
    assert.equal(new URL(page.url()).hash,'#NEXT');
  });
}

async function settled(page){await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));}
for(const initial of ['en','zh']) {
  test(`stock language translates pending and error states without retry or stale resurrection ${initial}`,async t=>{
    const {page,select,reply,requests,requested}=await setup(t,initial,{realChart:true});
    const other=initial==='en'?'zh':'en';
    const loading=lang=>lang==='zh'?/加载/:/Loading/;
    const notlib=lang=>lang==='zh'?/不在库中/:/NOT IN LIBRARY/;
    const unavailable=lang=>lang==='zh'?/暂时无法加载/:/could not be loaded/;
    await select('OLD');await select('RETRY');
    const before=requests.length;await page.locator('#q').focus();
    await setLanguage(page,other);
    assert.equal(requests.length,before,'pending locale change must reuse original in-flight lookup');
    assert.match(await page.locator('#lookup_status').innerText(),loading(other));
    assert.equal(await page.locator('#result').isVisible(),false);
    assert.equal(await page.locator('#q').evaluate(n=>n===document.activeElement),true);
    await reply('OLD',record('OLD'));await settled(page);
    assert.match(await page.locator('#lookup_status').innerText(),/^RETRY/);
    assert.equal(await page.locator('#result').isVisible(),false);
    await reply('RETRY',{},404);
    await page.waitForFunction(()=>/NOT IN LIBRARY|不在库中/.test(document.getElementById('lookup_status').textContent));
    assert.match(await page.locator('#lookup_status').innerText(),notlib(other));
    await setLanguage(page,initial);
    assert.equal(requests.length,before);assert.match(await page.locator('#lookup_status').innerText(),notlib(initial));
    async function retry(){
      await page.locator('#q').fill('RETRY');
      await page.waitForFunction(()=>document.getElementById('sugg').style.display==='block');
      const arrival=requested('RETRY');await page.locator('#q').press('Enter');await arrival;
    }
    await retry();
    await reply('RETRY',initial==='en'?{}:record('WRONG'),initial==='en'?500:200);
    await page.waitForFunction(()=>/could not be loaded|暂时无法加载/.test(document.getElementById('lookup_status').textContent));
    assert.match(await page.locator('#lookup_status').innerText(),unavailable(initial));
    const failed=requests.length;await setLanguage(page,other);
    assert.equal(requests.length,failed);assert.match(await page.locator('#lookup_status').innerText(),unavailable(other));
    assert.equal(await page.locator('#result').isVisible(),false);
    await retry();await setLanguage(page,initial);
    await reply('RETRY',record('RETRY'));await renderedStock(page,'RETRY');
    await page.waitForFunction(()=>StockChart._cur && StockChart._cur.S.price);
    await page.evaluate(()=>window.previous=StockChart._cur);
    await select('PENDING');assert.equal(await page.evaluate(()=>previous._destroyed),true);
    await page.evaluate(()=>location.hash='');
    await page.waitForFunction(()=>document.getElementById('lookup_status').textContent==='');
    await setLanguage(page,other);await reply('PENDING',record('PENDING'));await settled(page);
    assert.equal(await page.locator('#result').isVisible(),false);
    assert.equal(await page.locator('#lookup_status').innerText(),'');
    await page.evaluate(()=>location.hash='%E0%A4%A');
    await page.waitForFunction(()=>document.getElementById('lookup_status').textContent.length>0);
    const invalid=await page.locator('#lookup_status').innerText(),end=requests.length;
    await setLanguage(page,initial);
    assert.notEqual(await page.locator('#lookup_status').innerText(),invalid);
    assert.equal(requests.length,end);assert.equal(await page.locator('#result').isVisible(),false);
  });
}


test('explicit same-ticker reselection preserves latest-request ordering across locale change',async t=>{
  const {page,select,reply,requested,requests}=await setup(t,'en',{realChart:true});
  await select('RETRY');
  await page.locator('#q').fill('RETRY');
  await page.waitForFunction(()=>document.getElementById('sugg').style.display==='block');
  const second=requested('RETRY');await page.locator('#q').press('Enter');await second;
  const before=requests.length;await setLanguage(page,'zh');
  assert.equal(requests.length,before,'only explicit selection should start another lookup');
  await reply('RETRY',record('RETRY',{name:'Obsolete'}));await settled(page);
  assert.equal(await page.locator('#result').isVisible(),false);
  await reply('RETRY',record('RETRY',{name:'Current'}));await renderedStock(page,'RETRY','Current');
  assert.match(await page.locator('#r_asof').innerText(),/数据截至/);
});
