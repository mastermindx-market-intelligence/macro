'use strict';
// Current chart bytes with synthetic responses; no producer or live-data claim.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const blob = name => fs.readFileSync(path.join(root, name), 'utf8');
const chart = blob('site/chart.js');
const library = blob('site/lightweight-charts-v5.js');
const messages = {
  loading:{en:'Loading chart…',zh:'正在加载图表…'},
  absent:{en:'Live chart unavailable for this name — the analysis above stands on its own.',zh:'该标的暂无图表数据 —— 上方分析独立成立。'},
  failed:{en:'Chart failed to load.',zh:'图表加载失败。'}
};
const healthy = {o:0,bars:[['2026-10-01',100,1000],['2026-10-02',101,1100]]};
let browser;
test.before(async()=>{browser=await chromium.launch({headless:true});});
test.after(async()=>{await browser.close();});
async function setup(t,language,mode) {
  const context=await browser.newContext();t.after(()=>context.close());
  const page=await context.newPage();page.setDefaultTimeout(3000);
  let held;
  await page.route('**/*',async route=>{
    const url=new URL(route.request().url());
    if(url.hostname!=='chart-status.test')return route.abort();
    if(url.pathname==='/')return route.fulfill({contentType:'text/html',body:'<!doctype html><html><body><h1>Stock analysis</h1><input id="query"><div id="host" style="width:800px"></div></body></html>'});
    if(url.pathname.startsWith('/signals/'))return route.fulfill({status:404,json:{}});
    if(mode==='loading'){held=route;return;}
    if(mode==='failed')return route.abort('failed');
    if(mode==='missing')return route.fulfill({status:404,json:{}});
    return route.fulfill({json:{o:0,bars:[]}});
  });
  await page.goto('http://chart-status.test/');
  await page.evaluate(language=>document.documentElement.setAttribute('data-lang',language),language);
  await page.addScriptTag({content:library});await page.addScriptTag({content:chart});
  await page.evaluate(()=>window.current=StockChart.mount(document.getElementById('host'),'SYNTHETIC'));
  const expected=messages[mode==='loading'?'loading':mode==='failed'?'failed':'absent'];
  await page.waitForFunction(text=>document.querySelector('.bchart-msg')?.textContent===text,expected[language]);
  return {page,expected,reply:async()=>{assert.ok(held);await held.fulfill({json:healthy});}};
}
for(const initial of ['en','zh'])for(const mode of ['loading','empty','missing','failed']) {
  test(`chart ${mode} status follows actual language changes from ${initial}`,async t=>{
    const {page,expected,reply}=await setup(t,initial,mode);
    await page.locator('#query').focus();
    for(const language of [initial==='en'?'zh':'en',initial]) {
      await page.evaluate(language=>{document.documentElement.setAttribute('data-lang',language);document.dispatchEvent(new Event('langchange'));},language);
      assert.equal(await page.locator('.bchart-msg').innerText(),expected[language]);
      assert.equal(await page.locator('#query').evaluate(n=>n===document.activeElement),true);
      assert.equal(await page.locator('h1').innerText(),'Stock analysis');
    }
    if(mode==='loading') {
      await reply();await page.waitForFunction(()=>!!current.S.price);
      assert.equal(await page.locator('.bchart-msg').count(),0);
      assert.equal(await page.locator('[data-tf="1D"]').getAttribute('aria-pressed'),'true');
      await page.evaluate(()=>document.dispatchEvent(new Event('langchange')));
      assert.equal(await page.locator('.bchart-msg').count(),0,'settled chart cannot revert to the loading message');
    }
  });
}
test('retiring a pending chart removes the early language handler',async t=>{
  const {page,reply}=await setup(t,'en','loading');
  await page.evaluate(()=>current.destroy());
  await page.evaluate(()=>{document.documentElement.setAttribute('data-lang','zh');document.dispatchEvent(new Event('langchange'));});
  assert.equal(await page.locator('.bchart-msg').innerText(),messages.loading.en);
  await reply();await page.waitForLoadState('networkidle');
  assert.equal(await page.evaluate(()=>current.chart),null);
  assert.equal(await page.locator('.bchart-msg').innerText(),messages.loading.en);
});
