'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const html = execFileSync(process.env.INTL_TEST_PYTHON || 'python3',
  [path.join(__dirname, 'test_intl_workspace_integration.py')],
  {cwd:root, env:{...process.env, PYTHONPATH:root}, encoding:'utf8', maxBuffer:1024*1024});

async function pageFixture(fn, {javaScriptEnabled=true, broken=false, width=1440, state="unknown"}={}) {
  const browser = await chromium.launch({headless:true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL ? {channel:process.env.PLAYWRIGHT_CHROMIUM_CHANNEL} : {})});
  const fixtureHtml = state === 'unknown' ? html : execFileSync(process.env.INTL_TEST_PYTHON || 'python3',
    [path.join(__dirname,'test_intl_workspace_integration.py'),'macro',state],
    {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:1024*1024});
  const context = await browser.newContext({javaScriptEnabled, viewport:{width,height:900}});
  const page = await context.newPage();
  page.setDefaultTimeout(2500);
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.hostname !== 'intl.test') return route.abort();
    if (url.pathname === '/intl.html') return route.fulfill({contentType:'text/html',body:fixtureHtml});
    let file = path.resolve(root, 'templates', '.' + url.pathname);
    if (!file.startsWith(path.join(root,'templates') + path.sep)) return route.abort();
    if (broken && url.pathname === '/intl_workspace_entry.js') {
      const body = fs.readFileSync(file,'utf8');
      return route.fulfill({contentType:'text/javascript',body:
        'window.IntlWorkspace.mountIntlWorkspace=function(){throw Error("injected mount failure")};\n' + body});
    }
    if (!fs.existsSync(file) && process.env.INTL_TEST_ASSET_DIR) {
      const assets=path.resolve(process.env.INTL_TEST_ASSET_DIR);
      const candidate=path.resolve(assets,'.'+url.pathname);
      if(candidate.startsWith(assets+path.sep)) file=candidate;
    }
    if (fs.existsSync(file) && fs.statSync(file).isFile()) return route.fulfill({path:file,
      contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':undefined});
    return route.fulfill({status:404,body:''});
  });
  try { await page.goto('http://intl.test/intl.html', {waitUntil:'load'}); await fn(page); }
  finally { await browser.close(); }
}

test('real macro entry mounts one panel, changes exact context, returns with browser history and opens legacy', async()=>{
  await pageFixture(async page=>{
    assert.equal(await page.locator('[data-im-enhanced]').count(),1);
    assert.equal(await page.locator('[data-im-panel]:visible').count(),1);
    assert.equal(await page.locator('[data-im-controls]').evaluate(n=>n.disabled),false);
    assert.equal(await page.locator('#intl-legacy-research').getAttribute('open'),null);
    assert.equal(new URL(page.url()).search,'');
    await page.selectOption('[data-im-action="set_horizon"]','3m');
    await page.selectOption('[data-im-action="set_basis"]','local');
    assert.equal(await page.locator('[data-im-panel]:visible').getAttribute('data-horizon'),'3m');
    assert.equal(await page.locator('[data-im-panel]:visible').getAttribute('data-basis'),'local');
    await page.goBack();
    assert.equal(await page.locator('[data-im-panel]:visible').getAttribute('data-basis'),'usd_unhedged');
    await page.locator('[data-im-expansion-trigger]:visible').click();
    assert.equal(await page.locator('[data-im-panel]:visible [data-im-market-unknown]:visible').count(),7);
    await page.locator('[data-im-workspace] a[href="#intl-legacy-research"]').click();
    assert.notEqual(await page.locator('#intl-legacy-research').getAttribute('open'),null);
    assert.equal(await page.locator('#fixture-owner-fragment').isVisible(),true);
  });
});

for (const options of [{javaScriptEnabled:false},{broken:true}]) {
  test(options.broken?'failed enhancement restores readable page':'no JavaScript retains every roster and legacy research', async()=>{
    await pageFixture(async page=>{
      assert.equal(await page.locator('[data-im-enhanced]').count(),0);
      assert.equal(await page.locator('[data-im-controls]').evaluate(n=>n.disabled),true);
      assert.equal(await page.locator('[data-im-panel]:visible').count(),10);
      assert.equal(await page.locator('[data-im-market-unknown]:visible').count(),70);
      assert.equal(await page.locator('[data-im-expansion-trigger]:visible').count(),0);
      assert.equal(await page.locator('#fixture-owner-fragment').isVisible(),true);
    },options);
  });
}

test('actual theme/language owner, 32 responsive and text-size states, keyboard and touch targets',async()=>{
  await pageFixture(async page=>{
    const observations=[];
    for (const width of [1440,768,390,320]) for(const theme of ['dark','light']) for(const lang of ['en','zh']) for(const scale of [1,2]) {
      await page.setViewportSize({width,height:900});
      await page.evaluate(({theme,lang,scale})=>{
        window.setTheme(theme); window.setLang(lang);
        const nodes=[...document.querySelectorAll('[data-im-workspace], [data-im-workspace] *')];
        nodes.forEach(node=>{node.style.removeProperty('font-size');node.style.removeProperty('line-height');});
        if(scale===2) {
          const sizes=nodes.map(node=>{const s=getComputedStyle(node);return [node,parseFloat(s.fontSize),parseFloat(s.lineHeight)];});
          sizes.forEach(([node,font,line])=>{node.style.fontSize=font*2+'px';if(Number.isFinite(line))node.style.lineHeight=line*2+'px';});
        }
      },{theme,lang,scale});
      const result=await page.evaluate(()=>{
        const root=document.querySelector('[data-im-workspace]');
        const visible=node=>node.getClientRects().length && getComputedStyle(node).visibility!=='hidden';
        const controls=[...root.querySelectorAll('button,select')].filter(visible);
        return {theme:document.documentElement.dataset.theme,lang:document.documentElement.lang,
          overflow:root.scrollWidth>root.clientWidth+1,
          minTarget:Math.min(...controls.map(n=>n.getBoundingClientRect().height)),
          localeLeak:[...root.querySelectorAll(document.documentElement.lang.startsWith('zh')?'.l-en':'.l-zh')].some(visible),
          selectedBasis:root.querySelector('[data-im-action="set_basis"]').selectedOptions[0].textContent};
      });
      assert.equal(result.theme,theme); assert.equal(result.lang.split('-')[0],lang);
      assert.equal(result.overflow,false,JSON.stringify({width,theme,lang,scale,result}));
      assert.equal(result.localeLeak,false);
      assert.ok(result.minTarget>=44,JSON.stringify({width,theme,lang,scale,result}));
      assert.match(result.selectedBasis,lang==='zh'?/美元/:/USD/);
      const observation={width,theme,lang,textScale:scale,...result};
      if(process.env.INTL_BROWSER_EVIDENCE_DIR) {
        fs.mkdirSync(process.env.INTL_BROWSER_EVIDENCE_DIR,{recursive:true});
        const name=`workspace-${width}-${theme}-${lang}-${scale}x.png`;
        await page.waitForTimeout(1250); // Actual shared theme transition settles before visual capture.
        await page.locator('[data-im-workspace]').screenshot({path:path.join(process.env.INTL_BROWSER_EVIDENCE_DIR,name)});
        observation.screenshot=name;
      }
      observations.push(observation);
    }
    await page.locator('[data-im-action="set_horizon"]').focus();
    await page.keyboard.press('Tab');
    assert.equal(await page.locator('[data-im-action="set_basis"]').evaluate(n=>n===document.activeElement),true);
    assert.notEqual(await page.locator('[data-im-action="set_basis"]').evaluate(n=>getComputedStyle(n).outlineStyle),'none');
    if(process.env.INTL_BROWSER_EVIDENCE_DIR) {
      fs.mkdirSync(process.env.INTL_BROWSER_EVIDENCE_DIR,{recursive:true});
      fs.writeFileSync(path.join(process.env.INTL_BROWSER_EVIDENCE_DIR,'responsive.json'),JSON.stringify(observations,null,2));
    }
  });
});

for(const state of ['qualified','negative','denied']) {
  test(`synthetic ${state} actual projection and template remain readable and preserve disclosure`,async()=>{
    await pageFixture(async page=>{
      assert.equal(await page.locator('[data-im-panel]:visible').count(),1);
      assert.equal(await page.locator('[data-im-focus-item]:visible').count(),state==='denied'?0:4);
      await page.locator('[data-im-expansion-trigger]:visible').click();
      assert.equal(await page.locator(state==='denied'?'[data-im-market-denied]:visible':'[data-im-market]:visible').count(),7);
      for(const width of [1440,320]) for(const theme of ['dark','light']) for(const lang of ['en','zh']) {
        await page.setViewportSize({width,height:900});
        await page.evaluate(({theme,lang})=>{window.setTheme(theme);window.setLang(lang);},{theme,lang});
        assert.equal(await page.locator('[data-im-workspace]').evaluate(n=>n.scrollWidth>n.clientWidth+1),false);
        if(state==='negative') assert.match(await page.locator('[data-im-summary]').innerText(),lang==='zh'?/0 \/ 7/:/0 of 7/);
        if(state==='denied') assert.doesNotMatch(await page.locator('[data-im-workspace]').innerText(),/Nikkei|FTSE/);
        if(process.env.INTL_BROWSER_EVIDENCE_DIR) {
          await page.waitForTimeout(1250);
          await page.locator('[data-im-workspace]').screenshot({path:path.join(process.env.INTL_BROWSER_EVIDENCE_DIR,`${state}-${width}-${theme}-${lang}.png`)});
        }
      }
    },{state});
  });
}
