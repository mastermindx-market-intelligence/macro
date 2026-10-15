'use strict';
// Real chart controller and bundled Lightweight Charts; synthetic OHLC/network
// ordering isolates disposal. This is not producer, qualification or live proof.
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const {chromium} = require('playwright');
const ROOT = path.resolve(__dirname, '..');
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
  await page.addScriptTag({path:path.join(ROOT,'site/lightweight-charts-v5.js')});
  await page.addScriptTag({path:path.join(ROOT,'site/chart.js')});
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

for(const status of [200,404]) test(`late daily ${status} cannot revive a chart replaced by another ticker`,async t=>{
  const {page,mount,reply,waitRequest}=await setup(t);
  await waitRequest('/ohlc/OLD.json',()=>mount('OLD',false));
  await mount('NEW');
  const retired=await page.evaluate(()=>OLD.wrap.innerHTML);
  await reply('/ohlc/OLD.json',daily,status);
  assert.equal(await page.evaluate(()=>OLD.chart===null),true,'retired chart must not allocate a new canvas');
  assert.equal(await page.evaluate(()=>OLD.wrap.innerHTML),retired,'late response must not repaint retired DOM');
  assert.equal(await page.evaluate(()=>NEW.chart!==null&&StockChart._cur===NEW),true);
  await page.evaluate(()=>document.dispatchEvent(new Event('themechange')));
  assert.equal(await page.evaluate(()=>OLD.chart===null),true,'retired theme listener must not be registered again');
});

test('a failed late daily request does not rewrite a destroyed chart',async t=>{
  const {page,mount,reject,waitRequest}=await setup(t);
  await waitRequest('/ohlc/OLD.json',()=>mount('OLD',false));
  await page.evaluate(()=>OLD.destroy());
  const retired=await page.evaluate(()=>OLD.wrap.innerHTML);
  await reject('/ohlc/OLD.json');
  assert.equal(await page.evaluate(()=>OLD.wrap.innerHTML),retired);
});

test('late 4H data cannot overwrite the replacement chart preferences',async t=>{
  const {page,mount,reply,waitRequest}=await setup(t);
  await mount('OLD');
  await waitRequest('/intraday/OLD.json',()=>page.locator('[data-tf="4H"]').click());
  await mount('NEW'); await page.locator('[data-tf="1W"]').click();
  await reply('/intraday/OLD.json',intra);
  assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('bchart.prefs')).tf),'1W');
  assert.equal(await page.evaluate(()=>OLD.chart===null),true);
  assert.equal(await page.evaluate(()=>NEW.tf),'1W');
});

test('late signals do not mutate a destroyed chart',async t=>{
  const {page,mount,reply,waitRequest}=await setup(t,true);
  await waitRequest('/signals/OLD.json',()=>mount('OLD'));
  await page.evaluate(()=>OLD.destroy());
  await reply('/signals/OLD.json',{markers:[{date:'2026-01-20',type:'buy',quality:'take'}]});
  assert.equal(await page.evaluate(()=>OLD.signals),null);
  assert.equal(await page.locator('[data-sig]').count(),0);
});

test('current chart can still load daily, change to 4H and dispose fullscreen twice',async t=>{
  const {page,mount,reply,waitRequest}=await setup(t);
  await waitRequest('/ohlc/CURRENT.json',()=>mount('CURRENT',false));
  await reply('/ohlc/CURRENT.json',daily);
  await page.waitForFunction(() => CURRENT.chart !== null);
  assert.equal(await page.evaluate(()=>CURRENT.chart!==null),true);
  await waitRequest('/intraday/CURRENT.json',()=>page.locator('[data-tf="4H"]').click());
  await reply('/intraday/CURRENT.json',intra);
  // The requested timeframe commits after its response body has been consumed.
  await page.waitForFunction(() => CURRENT.tf === '4H');
  assert.equal(await page.evaluate(()=>CURRENT.tf),'4H');
  assert.equal(await page.evaluate(()=>CURRENT.view.length),6);
  await page.locator('.bchart-fsbtn').click();
  assert.equal(await page.locator('html').evaluate(n=>n.classList.contains('bchart-lock')),true);
  await page.evaluate(()=>{CURRENT.destroy();CURRENT.destroy();});
  assert.equal(await page.locator('html').evaluate(n=>n.classList.contains('bchart-lock')),false);
  assert.equal(await page.evaluate(()=>CURRENT.chart===null),true);
});


test('disposing the previous chart again does not unlock the current fullscreen chart',async t=>{
  const {page,mount}=await setup(t);
  await mount('OLD'); await mount('NEW');
  await page.locator('.bchart-fsbtn').click();
  await page.evaluate(()=>OLD.destroy());
  assert.equal(await page.locator('html').evaluate(n=>n.classList.contains('bchart-lock')),true);
  assert.equal(await page.evaluate(()=>NEW.chart!==null),true);
});

test('current delayed signals still become available',async t=>{
  const {page,mount,reply,waitRequest}=await setup(t,true);
  await waitRequest('/signals/CURRENT.json',()=>mount('CURRENT'));
  await reply('/signals/CURRENT.json',{markers:[{date:'2026-01-20',type:'buy',quality:'take'}]});
  assert.equal(await page.locator('[data-sig]').count(),1);
  assert.equal(await page.evaluate(()=>CURRENT.signals.markers.length),1);
});

test('a later daily timeframe choice wins over a pending 4H request',async t=>{
  const {page,mount,reply,waitRequest}=await setup(t);
  await mount('CURRENT');
  await waitRequest('/intraday/CURRENT.json',()=>page.locator('[data-tf="4H"]').click());
  await page.locator('[data-tf="1W"]').click();
  await reply('/intraday/CURRENT.json',intra);
  assert.equal(await page.evaluate(()=>CURRENT.tf),'1W');
  assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('bchart.prefs')).tf),'1W');
  assert.equal(await page.locator('[data-tf="1W"]').getAttribute('class'),'on');
});

for (const language of ['en','zh']) test(`chart controls expose committed selection to accessibility APIs ${language}`,async t=>{
  const {page,mount,reply,waitRequest}=await setup(t,true);
  await page.evaluate(language=>document.documentElement.setAttribute('data-lang',language),language);
  await waitRequest('/signals/CURRENT.json',()=>mount('CURRENT'));
  await reply('/signals/CURRENT.json',{markers:[{date:'2026-01-20',type:'buy',quality:'take'}]});
  const weekly=page.locator('[data-tf="1W"]'),dailyButton=page.locator('[data-tf="1D"]');
  assert.equal(await dailyButton.getAttribute('aria-pressed'),'true');
  assert.equal(await weekly.getAttribute('aria-pressed'),'false');
  await weekly.focus();await page.keyboard.press('Enter');
  assert.equal(await weekly.getAttribute('aria-pressed'),'true');
  assert.equal(await dailyButton.getAttribute('aria-pressed'),'false');
  assert.equal(await page.getByRole('button',{name:language==='zh'?'周':'1W',exact:true,pressed:true}).count(),1);
  for(const selector of ['[data-k="ema"]','[data-k="rsi"]','[data-sig]']) {
    const button=page.locator(selector);assert.equal(await button.getAttribute('aria-pressed'),'true');
    await button.focus();await page.keyboard.press('Space');
    assert.equal(await button.getAttribute('aria-pressed'),'false');
    assert.equal(await button.evaluate(n=>n.classList.contains('on')),false);
  }
  await waitRequest('/intraday/CURRENT.json',()=>page.locator('[data-tf="4H"]').click());
  await reply('/intraday/CURRENT.json',{},503);
  assert.equal(await weekly.getAttribute('aria-pressed'),'true','failed request cannot announce an uncommitted timeframe');
  assert.equal(await page.locator('[data-tf="4H"]').getAttribute('aria-pressed'),'false');
  await page.evaluate(()=>document.dispatchEvent(new Event('langchange')));
  assert.equal(await weekly.getAttribute('aria-pressed'),'true');
  for(const selector of ['[data-k="ema"]','[data-k="rsi"]','[data-sig]']) assert.equal(await page.locator(selector).getAttribute('aria-pressed'),'false');
});

for (const language of ['en','zh']) test(`fullscreen exit keeps its truthful name after a language rebuild ${language}`,async t=>{
  const {page,mount}=await setup(t);await mount('CURRENT');
  await page.locator('.bchart-fsbtn').click();
  await page.evaluate(language=>{document.documentElement.setAttribute('data-lang',language);document.dispatchEvent(new Event('langchange'));},language);
  assert.equal(await page.locator('.bchart-fsbtn').getAttribute('aria-label'),language==='zh'?'退出全屏':'Exit full screen');
  assert.equal(await page.locator('.bchart').evaluate(n=>n.classList.contains('bchart-full')),true);
  await page.locator('.bchart-fsbtn').focus();await page.keyboard.press('Enter');
  assert.equal(await page.locator('.bchart-fsbtn').getAttribute('aria-label'),language==='zh'?'全屏':'Full screen');
  assert.equal(await page.locator('html').evaluate(n=>n.classList.contains('bchart-lock')),false);
});

for (const language of ['en','zh']) test(`fullscreen keyboard navigation stays on visible chart controls ${language}`,async t=>{
  const {page,mount}=await setup(t);
  await page.setViewportSize({width:language==='zh'?320:1440,height:800});
  await page.evaluate(language=>{
    document.documentElement.setAttribute('data-lang',language);
    document.getElementById('host').style.width='100%';
    document.body.insertAdjacentHTML('afterbegin','<button id="before">Before chart</button>');
    document.body.insertAdjacentHTML('beforeend','<button id="after">After chart</button>');
  },language);
  await mount('CURRENT');
  const full=page.locator('.bchart-fsbtn'),first=page.locator('[data-tf="4H"]');
  await full.focus();await page.keyboard.press('Enter');
  await page.keyboard.press('Tab');
  assert.equal(await first.evaluate(n=>n===document.activeElement),true,'Tab from the final control must not reach the covered page');
  await page.keyboard.press('Shift+Tab');
  assert.equal(await full.evaluate(n=>n===document.activeElement),true,'reverse traversal stays in the visible overlay');
  const controlCount=await page.locator('.bchart button').count();
  for(let i=0;i<controlCount*2;i++) {
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(()=>CURRENT.wrap.contains(document.activeElement)),true);
  }
  await page.locator('[data-tf="1W"]').focus();await page.keyboard.press('Enter');
  assert.equal(await page.evaluate(()=>CURRENT.tf),'1W','visible controls remain operable');
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('.bchart-full').count(),0);
  assert.equal(await full.evaluate(n=>n===document.activeElement),true,'Escape returns to the inline fullscreen launcher');
  await page.keyboard.press('Tab');
  assert.equal(await page.locator('#after').evaluate(n=>n===document.activeElement),true,'normal document traversal resumes after exit');
  await first.focus();await page.keyboard.press('Shift+Tab');
  assert.equal(await page.locator('#before').evaluate(n=>n===document.activeElement),true,'inline chart does not trap reverse navigation');
});

for (const language of ['en','zh']) test(`fullscreen language rebuild retains the focused chart action ${language}`,async t=>{
  const {page,mount}=await setup(t);await mount('CURRENT');
  await page.locator('.bchart-fsbtn').focus();await page.keyboard.press('Enter');
  const weekly=page.locator('[data-tf="1W"]');
  await weekly.focus();await page.keyboard.press('Enter');
  await page.evaluate(language=>{
    document.documentElement.setAttribute('data-lang',language);
    document.dispatchEvent(new Event('langchange'));
  },language);
  assert.equal(await weekly.evaluate(n=>n===document.activeElement),true,'replacing localized controls must not strand focus on the covered document');
  assert.equal(await weekly.getAttribute('aria-pressed'),'true');
  assert.equal(await weekly.innerText(),language==='zh'?'周':'1W');
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('.bchart-fsbtn').evaluate(n=>n===document.activeElement),true);
  assert.equal(await page.locator('html').evaluate(n=>n.classList.contains('bchart-lock')),false);
});

test('fullscreen traversal includes late signals and respects composition and handled keys',async t=>{
  const {page,mount,reply,waitRequest}=await setup(t,true);
  await waitRequest('/signals/CURRENT.json',()=>mount('CURRENT'));
  await page.locator('.bchart-fsbtn').focus();await page.keyboard.press('Enter');
  await reply('/signals/CURRENT.json',{markers:[{date:'2026-01-20',type:'buy',quality:'take'}]});
  await page.keyboard.press('Tab');
  const summary=page.locator('.bchart-sig summary');
  assert.equal(await summary.evaluate(n=>n===document.activeElement),true,'the newly available disclosure remains reachable');
  await page.keyboard.press('Enter');
  assert.equal(await page.locator('.bchart-sig').getAttribute('open'),'');
  await page.evaluate(()=>{
    document.documentElement.setAttribute('data-lang','zh');
    document.dispatchEvent(new Event('langchange'));
  });
  assert.equal(await summary.evaluate(n=>n===document.activeElement),true);
  await page.keyboard.press('Tab');
  assert.equal(await page.locator('[data-tf="4H"]').evaluate(n=>n===document.activeElement),true);
  await page.keyboard.press('Shift+Tab');
  assert.equal(await summary.evaluate(n=>n===document.activeElement),true);
  for(const event of [{key:'Escape',isComposing:true},{key:'Escape',keyCode:229},{key:'Escape',handled:true},{key:'Tab',ctrlKey:true}]) {
    const prevented=await page.evaluate(event=>{
      const e=new KeyboardEvent('keydown',{bubbles:true,cancelable:true,...event});
      if(event.handled)e.preventDefault();
      document.activeElement.dispatchEvent(e);return e.defaultPrevented;
    },event);
    assert.equal(prevented,!!event.handled,'composition and browser shortcuts keep their original handling');
    assert.equal(await page.locator('.bchart-full').count(),1);
    assert.equal(await summary.evaluate(n=>n===document.activeElement),true);
  }
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('.bchart-full').count(),0);
  assert.equal(await page.locator('.bchart-fsbtn').evaluate(n=>n===document.activeElement),true);
});
