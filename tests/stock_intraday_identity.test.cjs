'use strict';
// Real chart controller and bundled Lightweight Charts; synthetic OHLC/network
// ordering isolates disposal. This is not producer, qualification or live proof.
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const {chromium} = require('playwright');
const ROOT = path.resolve(__dirname, '..');
const {execFileSync} = require('node:child_process');
const fs = require('node:fs');
const chartSource = fs.readFileSync(path.join(ROOT, 'site/chart.js'), 'utf8');
const lwc = fs.readFileSync(path.join(ROOT, 'site/lightweight-charts-v5.js'), 'utf8');
const daily = {o:1,bars:Array.from({length:60}, (_,i)=>[
  new Date(Date.UTC(2026,0,i+1)).toISOString().slice(0,10),100+i,102+i,99+i,101+i,1000])};
const intra = {bars:Array.from({length:24},(_,i)=>[1767225600+i*3600,100+i,102+i,99+i,101+i,1000])};
let browser;
test.before(async()=>{browser=await chromium.launch({headless:true,
  ...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL?{channel:process.env.PLAYWRIGHT_CHROMIUM_CHANNEL}:{})});});
test.after(async()=>{if(browser) await browser.close();});
async function setup(t, holdSignals=false) {
  const context=await browser.newContext(); t.after(()=>context.close());
  const page=await context.newPage(); page.setDefaultTimeout(3000);
  const pending=new Map();
  await page.route('**/*',async route=>{
    const url=new URL(route.request().url());
    if(url.hostname!=='chart.test') return route.abort();
    if(url.pathname==='/') return route.fulfill({contentType:'text/html',body:'<!doctype html><html><body><div id="host" style="width:800px"></div></body></html>'});
    if(url.pathname.startsWith('/signals/')&&!holdSignals) return route.fulfill({status:404,json:{}});
    pending.set(url.pathname,route);
  });
  await page.goto('http://chart.test/');
  await page.addScriptTag({content:lwc});
  await page.addScriptTag({content:chartSource});
  async function mount(name,inline=true,data=daily) {
    await page.evaluate(({name,inline,daily})=>{
      window[name]=StockChart.mount(document.getElementById('host'),name,{intraday:true,...(inline?{data:daily}:{})});
    },{name,inline,daily:data});
  }
  async function reply(url,data,status=200) {
    assert.ok(pending.has(url),'expected queued request '+url);
    await pending.get(url).fulfill({status,json:data}); pending.delete(url);
    await page.waitForLoadState('networkidle');
  }
  async function waitRequest(url,action) {
    const arrived=page.waitForRequest(req=>new URL(req.url()).pathname===url);
    await action(); await arrived;
    // The Playwright request event precedes route handling; flush one browser task.
    await page.evaluate(()=>new Promise(resolve=>setTimeout(resolve,0)));
    assert.ok(pending.has(url),'route handler retained '+url);
  }
  async function reject(url) {
    assert.ok(pending.has(url),'expected queued request '+url);
    await pending.get(url).abort(); pending.delete(url);
    await page.waitForLoadState('networkidle');
  }
  return {page,mount,reply,reject,waitRequest};
}




for(const initial of ['en','zh']) test(`wrong intraday identity cannot replace the selected daily chart ${initial}`,async t=>{
 const {page,mount,waitRequest,reply}=await setup(t);
 await page.evaluate(initial=>document.documentElement.setAttribute('data-lang',initial),initial);
 await mount('REQUESTED',true,{...daily,t:'REQUESTED'});
 await page.locator('[data-tf="1W"]').click();
 await page.evaluate(()=>{window.priceChartBefore=REQUESTED.chart;window.barsBefore=JSON.stringify(REQUESTED.S.price.data());window.prefsBefore=localStorage.getItem('bchart.prefs');});
 await waitRequest('/intraday/REQUESTED.json',()=>page.locator('[data-tf="4H"]').click());
 await reply('/intraday/REQUESTED.json',{...intra,t:'OTHER'});
 assert.equal(await page.evaluate(()=>REQUESTED.tf),'1W','wrong-ticker intraday bars must not commit a timeframe switch');
 assert.equal(await page.evaluate(()=>REQUESTED.intradayRows),null,'do not retain foreign bars for later reuse');
 assert.equal(await page.evaluate(()=>REQUESTED.chart===priceChartBefore),true);
 assert.equal(await page.evaluate(()=>JSON.stringify(REQUESTED.S.price.data())===barsBefore),true);
 assert.equal(await page.evaluate(()=>localStorage.getItem('bchart.prefs')===prefsBefore),true);
 assert.equal(await page.locator('[data-tf="1W"]').getAttribute('aria-pressed'),'true');
 assert.equal(await page.locator('[data-tf="4H"]').getAttribute('aria-pressed'),'false');
 assert.equal(await page.locator('[data-tf="4H"]').evaluate(n=>n===document.activeElement),true);
 // An explicit second selection requests fresh data and may commit a matching response.
 await waitRequest('/intraday/REQUESTED.json',()=>page.locator('[data-tf="4H"]').click());
 await reply('/intraday/REQUESTED.json',{...intra,t:'REQUESTED'});
 await page.waitForFunction(()=>REQUESTED.tf==='4H');
 assert.equal(await page.evaluate(()=>REQUESTED.intradayRows.length),24);
 assert.equal(await page.evaluate(()=>REQUESTED.view.length),6);
 assert.equal(await page.evaluate(()=>REQUESTED.S.price.data().at(-1).close),124);
 assert.equal(await page.locator('[data-tf="4H"]').getAttribute('aria-pressed'),'true');
 assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('bchart.prefs')).tf),'4H');
});

test('4H uses logical ticker identity and retains legacy anonymous response compatibility',async t=>{
 const {page,mount,waitRequest,reply}=await setup(t);
 await mount('PAIR=X',true,{...daily,t:'PAIR=X'});
 await waitRequest('/intraday/PAIR_X.json',()=>page.locator('[data-tf="4H"]').click());
 await reply('/intraday/PAIR_X.json',{...intra,t:'PAIR=X'});
 await page.waitForFunction(()=>StockChart._cur.tf==='4H');
 assert.equal(await page.evaluate(()=>StockChart._cur.S.price.data().at(-1).close),124);
 await mount('LEGACY',true,{...daily,t:'LEGACY'});
 await waitRequest('/intraday/LEGACY.json',()=>page.locator('[data-tf="4H"]').click());
 await reply('/intraday/LEGACY.json',intra);
 await page.waitForFunction(()=>StockChart._cur.tf==='4H');
 assert.equal(await page.evaluate(()=>StockChart._cur.S.price.data().at(-1).close),124);
});
