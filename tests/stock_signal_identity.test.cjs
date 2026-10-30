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




const markers=[{date:'2026-01-20',type:'buy',quality:'take'}];
for(const initial of ['en','zh']) test(`foreign signal identity leaves the current price chart intact ${initial}`,async t=>{
 const {page,mount,waitRequest,reply}=await setup(t,true);
 await page.evaluate(initial=>document.documentElement.setAttribute('data-lang',initial),initial);
 await waitRequest('/signals/REQUESTED.json',()=>mount('REQUESTED',true,{...daily,t:'REQUESTED'}));
 await page.locator('[data-tf="1W"]').click();
 await page.locator('[data-k="rsi"]').focus();
 await page.evaluate(()=>{window.priceChartBefore=REQUESTED.chart;window.barsBefore=JSON.stringify(REQUESTED.S.price.data());});
 await reply('/signals/REQUESTED.json',{ticker:'OTHER',tf:'3D',markers});
 assert.equal(await page.evaluate(()=>REQUESTED.signals),null,'wrong-ticker signals must not attach to the current chart');
 assert.equal(await page.locator('[data-sig]').count(),0);
 assert.equal(await page.locator('.bchart-sig').count(),0);
 assert.equal(await page.evaluate(()=>REQUESTED._sigPrim),null);
 assert.equal(await page.evaluate(()=>REQUESTED.chart===priceChartBefore),true);
 assert.equal(await page.evaluate(()=>JSON.stringify(REQUESTED.S.price.data())===barsBefore),true);
 assert.equal(await page.locator('[data-tf="1W"]').getAttribute('aria-pressed'),'true');
 assert.equal(await page.locator('[data-k="rsi"]').evaluate(n=>n===document.activeElement),true);
 // An explicit new mount with matching metadata can still show the optional panel.
 await waitRequest('/signals/REQUESTED.json',()=>mount('REQUESTED',true,{...daily,t:'REQUESTED'}));
 await reply('/signals/REQUESTED.json',{ticker:'REQUESTED',tf:'3D',markers});
 assert.equal(await page.evaluate(()=>REQUESTED.signals.ticker),'REQUESTED');
 assert.equal(await page.locator('[data-sig]').count(),1);
 assert.equal(await page.locator('.bchart-sig').count(),1);
 assert.equal(await page.evaluate(()=>!!REQUESTED._sigPrim),true);
 assert.equal(await page.locator('[data-sig]').innerText(),initial==='zh'?'信号':'Signals');
});

test('signals match the unsanitized logical ticker and retain anonymous legacy payloads',async t=>{
 const {page,mount,waitRequest,reply}=await setup(t,true);
 await waitRequest('/signals/PAIR_X.json',()=>mount('PAIR=X',true,{...daily,t:'PAIR=X'}));
 await reply('/signals/PAIR_X.json',{ticker:'PAIR=X',markers});
 assert.equal(await page.evaluate(()=>StockChart._cur.signals.ticker),'PAIR=X');
 assert.equal(await page.locator('.bchart-sig').count(),1);
 await waitRequest('/signals/LEGACY.json',()=>mount('LEGACY',true,{...daily,t:'LEGACY'}));
 await reply('/signals/LEGACY.json',{markers});
 assert.equal(await page.evaluate(()=>StockChart._cur.signals.markers.length),1);
 assert.equal(await page.locator('.bchart-sig').count(),1);
});
