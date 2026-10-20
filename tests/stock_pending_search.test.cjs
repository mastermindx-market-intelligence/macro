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
for(const language of ['en','zh'])for(const market of ['home','foreign']) {
  test(`pending ${market} index supplies the already typed query ${language}`,async t=>{
    const {page,reply,search}=await setup(t,language);
    const ticker=market==='home'?'HOME':'USONLY';
    await search.fill(ticker);
    assert.equal(await search.getAttribute('aria-expanded'),'false');
    await reply(market==='home'?'/intlstockdata/index.json':'/stockdata/index.json',[row(ticker)]);
    assert.equal(await search.getAttribute('aria-expanded'),'true','a settled matching index must make the active query usable without another keystroke');
    assert.equal(await page.getByRole('option').count(),1);
    assert.match(await page.getByRole('option').innerText(),new RegExp(ticker));
    assert.equal(await search.inputValue(),ticker);
    assert.equal(await search.evaluate(q=>q===document.activeElement),true);
    assert.equal(new URL(page.url()).hash,'');
    await search.press('ArrowDown');await search.press('Enter');
    await page.waitForURL('http://pending-stock.test/'+(market==='home'?'intl_stock.html':'stock.html')+'#'+ticker);
  });
}
for(const language of ['en','zh']) {
  test(`pending index uses the current query instead of the initial query ${language}`,async t=>{
    const {page,reply,search}=await setup(t,language);
    await search.fill('OLD');await search.fill('NEW');
    await reply('/intlstockdata/index.json',[row('OLD'),row('NEW')]);
    assert.equal(await page.getByRole('option').count(),1);
    assert.match(await page.getByRole('option').innerText(),/NEW/);
    assert.doesNotMatch(await page.getByRole('option').innerText(),/OLD/);
    assert.equal(await search.inputValue(),'NEW');
    assert.equal(await search.evaluate(q=>q===document.activeElement),true);
  });
  test(`a later index cannot replace the keyboard-selected identity ${language}`,async t=>{
    const {page,reply,search}=await setup(t,language);
    await reply('/stockdata/index.json',[row('AZZ')]);
    await search.fill('A');await search.press('ArrowDown');
    const selected=page.getByRole('option',{selected:true});
    assert.match(await selected.innerText(),/AZZ/);
    const before=await search.getAttribute('aria-activedescendant');
    await reply('/intlstockdata/index.json',[row('AAA')]);
    assert.match(await selected.innerText(),/AZZ/,'new earlier-sorting results must not retarget Enter');
    assert.equal(await search.getAttribute('aria-activedescendant'),before);
    assert.equal(await search.evaluate(q=>q===document.activeElement),true);
    await search.press('Enter');await page.waitForURL('http://pending-stock.test/stock.html#AZZ');
  });
  for(const dismissal of ['Escape','blur','clear'])test(`late index respects ${dismissal} while query is pending ${language}`,async t=>{
    const {page,reply,search}=await setup(t,language);
    await search.fill('LATE');
    if(dismissal==='Escape')await search.press('Escape');
    if(dismissal==='blur')await search.evaluate(q=>q.blur());
    if(dismissal==='clear')await search.fill('');
    const active=await page.evaluate(()=>document.activeElement.id);
    await reply('/intlstockdata/index.json',[row('LATE')]);
    assert.equal(await search.getAttribute('aria-expanded'),'false');
    assert.equal(await search.getAttribute('aria-activedescendant'),null);
    assert.equal(await page.locator('#sugg').isVisible(),false);
    assert.equal(await page.evaluate(()=>document.activeElement.id),active);
    assert.equal(new URL(page.url()).hash,'');
    // A new deliberate edit can use the retained settled index.
    await search.fill('LAT');
    assert.equal(await search.getAttribute('aria-expanded'),'true');
    assert.match(await page.getByRole('option').innerText(),/LATE/);
  });
}
