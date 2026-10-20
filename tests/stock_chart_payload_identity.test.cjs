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



// A supplied wrong ticker is distinct from retired response ordering. The native
// daily producer writes t; preserve legacy anonymous inline data in a separate case.
for(const initial of ['en','zh']) for(const inline of [false,true])
 test(`mismatched chart payload cannot acquire the requested identity ${initial} ${inline?'inline':'fetched'}`,async t=>{
  const {page,mount,waitRequest,reply}=await setup(t);
  await page.evaluate(initial=>document.documentElement.setAttribute('data-lang',initial),initial);
  const wrong={...daily,t:'OTHER',bars:daily.bars.map(b=>[b[0],900,902,899,901,1000])};
  if(inline) await mount('REQUESTED',true,wrong);
  else {
    await waitRequest('/ohlc/REQUESTED.json',()=>mount('REQUESTED',false));
    await reply('/ohlc/REQUESTED.json',wrong);
  }
  const state=await page.evaluate(()=>({
    data:REQUESTED.data,rows:REQUESTED.rows,chart:!!REQUESTED.chart,
    plotted:document.querySelectorAll('.bchart-canvas').length,
    message:document.querySelector('.bchart-msg')?.textContent,
    signals:performance.getEntriesByType('resource').filter(r=>r.name.includes('/signals/')).length
  }));
  assert.equal(state.chart,false,'foreign prices must not be plotted under the requested ticker');
  assert.equal(state.data,null);assert.equal(state.rows,null);assert.equal(state.plotted,0);
  assert.equal(state.message,initial==='zh'?'该标的暂无图表数据 —— 上方分析独立成立。':'Live chart unavailable for this name — the analysis above stands on its own.');
  assert.equal(state.signals,0,'rejected daily payload must not initiate downstream signals');
  // A subsequent explicit valid mount still works; rejection does not mutate data.
  await mount('REQUESTED',true,{...daily,t:'REQUESTED'});
  assert.equal(await page.evaluate(()=>REQUESTED.S.price.data().at(-1).close),160);
  assert.equal(await page.evaluate(()=>REQUESTED.data.t),'REQUESTED');
  assert.match(await page.locator('.bchart-legend').innerText(),/REQUESTED/);
});

test('matching ticker uses logical identity, preserves anonymous inline compatibility and does not infer from filename',async t=>{
 const {page,mount,waitRequest,reply}=await setup(t);
 await waitRequest('/ohlc/PAIR_X.json',()=>mount('PAIR=X',false));
 await reply('/ohlc/PAIR_X.json',{...daily,t:'PAIR=X'});
 assert.equal(await page.evaluate(()=>StockChart._cur.data.t),'PAIR=X');
 assert.equal(await page.evaluate(()=>StockChart._cur.S.price.data().at(-1).close),160);
 await mount('LEGACY_INLINE',true,daily);
 assert.equal(await page.evaluate(()=>StockChart._cur.data.t),undefined);
 assert.equal(await page.evaluate(()=>StockChart._cur.S.price.data().at(-1).close),160);
 assert.match(await page.locator('.bchart-legend').innerText(),/LEGACY_INLINE/);
});
