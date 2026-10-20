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
  async function mount(name,inline=true) {
    await page.evaluate(({name,inline,daily})=>{
      window[name]=StockChart.mount(document.getElementById('host'),name,{intraday:true,...(inline?{data:daily}:{})});
    },{name,inline,daily});
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


for(const initial of ['en','zh']) test(`inline language rebuild retains chart keyboard focus ${initial}`,async t=>{
  const {page,mount}=await setup(t);
  await page.evaluate(initial=>{
    document.documentElement.setAttribute('data-lang',initial);
    document.body.insertAdjacentHTML('afterbegin','<button id="before">Before chart</button>');
    document.body.insertAdjacentHTML('beforeend','<button id="after">After chart</button>');
  },initial);
  await mount('CURRENT');
  await page.locator('[data-tf="1W"]').click();
  await page.locator('[data-k="rsi"]').click();
  let lang=initial;
  async function translate(){
    lang=lang==='en'?'zh':'en';
    await page.evaluate(lang=>{
      document.documentElement.setAttribute('data-lang',lang);
      document.dispatchEvent(new Event('langchange'));
    },lang);
  }
  for(const selector of ['[data-tf="1W"]','[data-k="rsi"]','.bchart-fsbtn']) {
    const action=page.locator(selector);await action.focus();await translate();
    assert.equal(await action.evaluate(n=>n===document.activeElement),true,'locale repaint must retain the focused inline action');
    assert.equal(await page.locator('.bchart').evaluate(n=>n.classList.contains('bchart-full')),false);
    assert.equal(await page.locator('[data-tf="1W"]').getAttribute('aria-pressed'),'true');
    assert.equal(await page.locator('[data-k="rsi"]').getAttribute('aria-pressed'),'false');
    assert.equal(await page.locator('[data-tf="1W"]').innerText(),lang==='zh'?'周':'1W');
  }
  // Locale repaint must not capture focus from the rest of the document.
  await page.locator('#after').focus();await translate();
  assert.equal(await page.locator('#after').evaluate(n=>n===document.activeElement),true);
  // Inline chart remains in the page's tab order, never a fullscreen focus trap.
  await page.locator('.bchart-fsbtn').focus();await page.keyboard.press('Tab');
  assert.equal(await page.locator('#after').evaluate(n=>n===document.activeElement),true);
  await page.locator('[data-tf="4H"]').focus();await page.keyboard.press('Shift+Tab');
  assert.equal(await page.locator('#before').evaluate(n=>n===document.activeElement),true);
  assert.equal(await page.locator('html').evaluate(n=>n.classList.contains('bchart-lock')),false);
  // Continued keyboard operation applies to the same chart instance.
  await page.locator('[data-k="rsi"]').focus();await page.keyboard.press('Enter');
  assert.equal(await page.locator('[data-k="rsi"]').getAttribute('aria-pressed'),'true');
  assert.equal(await page.evaluate(()=>StockChart._cur===CURRENT&&!CURRENT._destroyed),true);
});
