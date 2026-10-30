'use strict';
// Current full-shell source with synthetic index records; no live-service or
// qualification claim.
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
const row=t=>({t,n:t+' synthetic fixture',s:'Fixture sector',st:'LIMITED'});
let browser;
test.before(async()=>{browser=await chromium.launch({headless:true});});
test.after(async()=>{await browser.close();});
async function setup(t,language) {
  const context=await browser.newContext({viewport:{width:language==='zh'?320:1440,height:900}});
  t.after(()=>context.close());
  await context.addInitScript(language=>{
    localStorage.setItem('lang',language);
    window.fixtureIndexRead={};
    const nativeFetch=window.fetch;
    window.fetch=function(...args){return nativeFetch.apply(this,args).then(response=>{
      if(new URL(response.url).pathname.endsWith('/index.json')) {
        const json=response.json.bind(response);
        response.json=()=>json().then(data=>{window.fixtureIndexRead[new URL(response.url).pathname]=true;return data;});
      }
      return response;
    });};
  },language);
  const page=await context.newPage();page.setDefaultTimeout(3000);
  const held=new Map();let allRequested;
  const requested=new Promise(resolve=>{allRequested=resolve;});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.route('**/*',async route=>{
    const url=new URL(route.request().url());
    if(url.hostname!=='pending-stock.test')return route.abort();
    if(url.pathname==='/intl_stock.html')return route.fulfill({contentType:'text/html',body:html});
    if(url.pathname.endsWith('/index.json')) {
      held.set(url.pathname,route);if(held.size===5)allRequested();return;
    }
    if(url.pathname==='/stock.html')return route.fulfill({contentType:'text/html',body:'<!doctype html><title>Synthetic destination</title>'});
    if(url.pathname.endsWith('/calibration.json'))return route.fulfill({json:{}});
    if(url.pathname.endsWith('.json'))return route.fulfill({status:503,json:{error:'synthetic unavailable'}});
    return route.fulfill({body:'',contentType:url.pathname.endsWith('.js')?'text/javascript':'text/css'});
  });
  await page.goto('http://pending-stock.test/intl_stock.html',{waitUntil:'domcontentloaded'});
  await requested;
  async function reply(index,rows) {
    assert.ok(held.has(index),'expected original retained index request');
    const route=held.get(index);held.delete(index);await route.fulfill({json:rows});
    await page.waitForFunction(index=>window.fixtureIndexRead[index],index);
    // json() completion precedes the controller's .then; observe the next frame.
    await page.evaluate(()=>new Promise(requestAnimationFrame));
    assert.deepEqual(errors,[]);
  }
  return {page,reply,search:page.locator('#q')};
}

const labels={en:'new listing · limited history',zh:'新上市 · 历史不足'};
async function language(page,lang) {
  await page.evaluate(lang=>{
    document.documentElement.setAttribute('data-lang',lang);
    document.dispatchEvent(new Event('langchange'));
  },lang);
}
for(const initial of ['en','zh']) {
  test(`visible search results follow locale without changing selected identity ${initial}`,async t=>{
    const {page,reply,search}=await setup(t,initial);
    await reply('/stockdata/index.json',[row('AAA'),row('AQQ')]);
    await search.fill('A');await search.press('ArrowDown');await search.press('ArrowDown');
    const id=await search.getAttribute('aria-activedescendant');
    await page.evaluate(()=>window.originalSelected=document.querySelector('[aria-selected="true"]'));
    for(const lang of [initial==='en'?'zh':'en',initial]) {
      await language(page,lang);
      const options=page.getByRole('option');
      assert.equal(await options.count(),2);
      for(const option of await options.all()) {
        assert.match(await option.innerText(),new RegExp(labels[lang]),'every result uses the active locale without another input event');
      }
      assert.equal(await search.getAttribute('aria-expanded'),'true');
      assert.equal(await search.getAttribute('aria-activedescendant'),id);
      assert.match(await page.getByRole('option',{selected:true}).innerText(),/AQQ/);
      assert.equal(await page.evaluate(()=>originalSelected===document.querySelector('[aria-selected="true"]')),true);
      assert.equal(await search.evaluate(q=>q===document.activeElement),true);
      assert.equal(await search.inputValue(),'A');
      assert.equal(new URL(page.url()).hash,'');
    }
    await search.press('Enter');await page.waitForURL('http://pending-stock.test/stock.html#AQQ');
  });
  test(`locale repaint cannot reopen a dismissed search ${initial}`,async t=>{
    const {page,reply,search}=await setup(t,initial);
    await reply('/stockdata/index.json',[row('AAA')]);
    await search.fill('A');await search.press('Escape');
    await language(page,initial==='en'?'zh':'en');
    await reply('/intlstockdata/index.json',[row('AQQ')]);
    assert.equal(await search.getAttribute('aria-expanded'),'false');
    assert.equal(await page.locator('#sugg').isVisible(),false);
    assert.equal(await search.getAttribute('aria-activedescendant'),null);
    assert.equal(await search.evaluate(q=>q===document.activeElement),true);
    await search.fill('AA');
    assert.match(await page.getByRole('option').innerText(),new RegExp(labels[initial==='en'?'zh':'en']));
  });
  test(`an index settling after a locale change uses current language ${initial}`,async t=>{
    const {page,reply,search}=await setup(t,initial);
    await search.fill('NEW');
    const next=initial==='en'?'zh':'en';await language(page,next);
    await reply('/intlstockdata/index.json',[row('NEW')]);
    assert.equal(await search.getAttribute('aria-expanded'),'true');
    assert.match(await page.getByRole('option').innerText(),new RegExp(labels[next]));
    assert.equal(await search.evaluate(q=>q===document.activeElement),true);
    assert.equal(new URL(page.url()).hash,'');
  });
}
