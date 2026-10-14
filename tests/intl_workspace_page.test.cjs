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
  {cwd:root, env:{...process.env, PYTHONPATH:root}, encoding:'utf8', maxBuffer:4*1024*1024});

async function pageFixture(fn, {javaScriptEnabled=true, broken=false, width=1440, state="unknown", htmlOverride=null, published=false, bootLanguage=null, browserLocale='en-US', initialSearch=''}={}) {
  let fixtureHtml = htmlOverride || (state === 'unknown' ? html : execFileSync(process.env.INTL_TEST_PYTHON || 'python3',
    [path.join(__dirname,'test_intl_workspace_integration.py'),'macro',state],
    {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024}));
  if (published) fixtureHtml = execFileSync(process.env.INTL_TEST_PYTHON || 'python3', ['-c',
    'import sys; from pathlib import Path; from scripts.optimize_assets import make_optimizer; p=Path("templates").resolve(); print(make_optimizer(p)(sys.stdin.read(),p))'],
    {cwd:root,env:{...process.env,PYTHONPATH:root},input:fixtureHtml,encoding:'utf8',maxBuffer:4*1024*1024,timeout:30000});
  const browser = await chromium.launch({headless:true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL ? {channel:process.env.PLAYWRIGHT_CHROMIUM_CHANNEL} : {})});
  const context = await browser.newContext({javaScriptEnabled, locale:browserLocale, viewport:{width,height:900}});
  if (bootLanguage) await context.addInitScript(lang=>localStorage.setItem('lang',lang),bootLanguage);
  const page = await context.newPage();
  page.setDefaultTimeout(2500);
  // Loading the full multi-context server fixture has its own bounded budget;
  // short interaction waits are not a page-load performance assertion.
  page.setDefaultNavigationTimeout(30000);
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
  try { await page.goto('http://intl.test/intl.html'+initialSearch, {waitUntil:'load'}); await fn(page); }
  finally { await browser.close(); }
}

const coldLocaleHtml = execFileSync(process.env.INTL_TEST_PYTHON || 'python3', ['-c',
  'from tests.test_intl_workspace_integration import render_history_fixture; print(render_history_fixture())'],
  {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Central bank unavailable readings survive Library keyboard return ${theme} ${lang}`,async()=>{
    const cbHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      "from tests.test_intl_central_bank_render import central_bank_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(risk_desk={'cb_desk':central_bank_fixture()}))"],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      const input=page.locator('[data-im-library-search]:visible');const query=lang==='zh'?'央行':'Central';
      await input.fill(query);
      const link=page.locator('[data-im-library-tool="central_banks_liquidity"] a[href="#intl-central-banks"]');
      assert.equal(await link.count(),1);const origin=page.url();
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});await link.focus();await page.keyboard.press('Enter');
        const target=page.locator('#intl-central-banks');assert.equal(await target.evaluate(n=>document.activeElement===n),true);
        assert.equal(new URL(page.url()).hash,'#intl-central-banks');
        const cells=page.locator('.ird-cb tbody tr').first().locator('td');
        assert.equal(await cells.nth(1).innerText(),'0.00%');
        assert.equal(await cells.nth(2).innerText(),lang==='zh'?'不可用':'Unavailable');
        assert.equal(await cells.nth(4).innerText(),lang==='zh'?'不可用':'Unavailable');
        const scroll=page.locator('.ird-cb').locator('..');
        console.log('Central-bank scroll semantics',await scroll.evaluate(n=>({role:n.getAttribute('role'),label:n.getAttribute('aria-labelledby'),tabindex:n.getAttribute('tabindex'),client:n.clientWidth,total:n.scrollWidth})));
        assert.equal(await scroll.getAttribute('role'),'region');
        assert.equal(await scroll.getAttribute('aria-labelledby'),'intl-central-banks');
        for(let i=0;i<5 && !(await scroll.evaluate(n=>document.activeElement===n));i++) await page.keyboard.press('Tab');
        assert.equal(await scroll.evaluate(n=>document.activeElement===n),true,'table scroller is reachable by native Tab');
        if(width===320) {
          assert.ok(await scroll.evaluate(n=>n.scrollWidth>n.clientWidth),'narrow table needs scrolling');
          for(let i=0;i<24;i++) await page.keyboard.press('ArrowRight');await page.waitForFunction(()=>{const n=document.querySelector('.ird-cb-scroll');return n.scrollLeft>=n.scrollWidth-n.clientWidth-2});
          assert.ok(await cells.nth(5).evaluate(n=>{const r=n.getBoundingClientRect(),s=n.closest('.ird-cb-scroll').getBoundingClientRect();return r.right<=s.right+1 && r.left>=s.left-1}),'last column is reachable');
          for(let i=0;i<24;i++) await page.keyboard.press('ArrowLeft');await page.waitForFunction(()=>document.querySelector('.ird-cb-scroll').scrollLeft<1);
        }
        assert.ok(await scroll.evaluate(n=>{const r=n.getBoundingClientRect();return r.left>=0 && r.right<=innerWidth+1}));
        await page.goBack();assert.equal(page.url(),origin);assert.equal(await input.inputValue(),query);
      }
    },{htmlOverride:cbHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Rates observation dates preserve independent clocks ${theme} ${lang}`,async()=>{
    const ratesHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      'from tests.test_intl_rates_dates_render import rates_dates_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(rates=rates_dates_fixture()))'],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{window.setTheme(theme);window.setLang(lang);},{theme,lang});
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const panel=page.locator('#intl-rates-curves').locator('xpath=ancestor::div[contains(concat(" ",normalize-space(@class)," ")," panel ")][1]');
        const anchor=panel.locator('[data-rates-anchor-date]');assert.equal(await anchor.isVisible(),true);
        assert.match(await anchor.innerText(),/2026-09-29/);
        assert.match(await anchor.innerText(),lang==='zh'?/美国10年观测日/:/US 10y observation date/);
        assert.match(await anchor.innerText(),lang==='zh'?/美国2年日期不可用/:/US 2y date unavailable/);
        const dates=panel.locator('[data-rates-dates]');assert.equal(await dates.count(),4);
        assert.match(await dates.nth(0).innerText(),/2026-08[\s\S]*2019-12/);
        assert.match(await dates.nth(0).innerText(),lang==='zh'?/10年观测月[\s\S]*CPI观测月/:/10y observation month[\s\S]*CPI observation month/);
        assert.match(await dates.nth(1).innerText(),lang==='zh'?/不可用[\s\S]*2026-06[\s\S]*3月日期不可用/:/Unavailable[\s\S]*2026-06[\s\S]*3m date unavailable/);
        assert.ok(!(await dates.nth(1).innerText()).includes('2026-08'),'never borrow another market clock');
        for(const el of [anchor,...await dates.all()]) {
          assert.equal(await el.isVisible(),true);
          assert.ok(await el.evaluate(n=>n.scrollWidth<=n.clientWidth+1),'date text stays within its own container');
        }
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:ratesHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-rates-curves'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Rates endpoint geometry stays readable and truthful ${theme} ${lang}`,async()=>{
    const ratesHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      'from tests.test_intl_rates_render import rates_geometry_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(rates=rates_geometry_fixture()))'],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{window.setTheme(theme);window.setLang(lang);},{theme,lang});
      const expected=[[-0.4,-0.1],[2.01,2.02],[8,12],[0,0],[3,3],[-0.2,-0.2],[2.02,2.01],[0,-0.01]];
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const heading=page.locator('#intl-rates-curves');await heading.scrollIntoViewIfNeeded();
        const cards=heading.locator('xpath=ancestor::div[contains(concat(" ",normalize-space(@class)," ")," panel ")][1]').locator('.rdesk > .rcard');
        assert.equal(await cards.count(),expected.length);
        for(let i=0;i<expected.length;i++) {
          const measured=await cards.nth(i).evaluate(card=>{
            const rect=n=>{const r=n.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,w:r.width,h:r.height};};
            return {card:rect(card),dots:[...card.querySelectorAll('.curve .d')].map(rect),
              labels:[...card.querySelectorAll('.curve .lab')].map(n=>({...rect(n),text:n.textContent.trim()}))};
          });
          const [a,b]=measured.labels;
          assert.ok(a.right<=b.x || b.right<=a.x || a.bottom<=b.y || b.bottom<=a.y,`endpoint labels overlap: case${i}/${width}`);
          const [short,y10]=expected[i];
          assert.equal(a.text,`3m ${short.toFixed(2)}%`);assert.equal(b.text,`10y ${y10.toFixed(2)}%`);
          const [s,t]=measured.dots;assert.ok(t.x-s.x>20,'maturity endpoints remain distinct, even for equal yields');
          if(short===y10) assert.ok(Math.abs(s.y-t.y)<0.02,'equal yields stay level');
          else assert.equal(s.y>t.y,short<y10,'yield order is not clipped or reversed');
          for(const box of [...measured.labels,...measured.dots]) {
            assert.ok(box.x>=measured.card.x && box.right<=measured.card.right);
            assert.ok(box.y>=measured.card.y && box.bottom<=measured.card.bottom);
          }
        }
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:ratesHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-rates-curves'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Rates missing endpoints never draw a zero curve ${theme} ${lang}`,async()=>{
    const ratesHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      'from tests.test_intl_rates_render import rates_render_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(rates=rates_render_fixture()))'],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{window.setTheme(theme);window.setLang(lang);},{theme,lang});
      const query=lang==='zh'?'利率、曲线与息差':'Rates, curves & carry';
      const input=page.locator('[data-im-library-search]:visible');await input.fill(query);
      const link=page.locator('[data-im-library-tool="rates_curves_carry"] a');const origin=page.url();
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        await link.focus();await page.keyboard.press('Enter');
        const heading=page.locator('#intl-rates-curves');
        assert.equal(new URL(page.url()).hash,'#intl-rates-curves');
        assert.equal(await heading.isVisible(),true);
        const panel=heading.locator('xpath=ancestor::div[contains(concat(" ",normalize-space(@class)," ")," panel ")][1]');
        const cards=panel.locator('.rdesk > .rcard');assert.equal(await cards.count(),4);
        assert.equal(await cards.nth(0).locator('.curve .d').count(),0,'absent3m must not become a zero endpoint');
        assert.equal(await cards.nth(0).locator('.curve .ln').count(),0);
        assert.match(await cards.nth(0).innerText(),lang==='zh'?/3月数据不可用/:/3m unavailable/);
        assert.match(await cards.nth(0).innerText(),/10y 2\.6/);
        assert.equal(await cards.nth(1).locator('.curve .d').count(),2,'genuine zero remains plotted');
        assert.match(await cards.nth(1).innerText(),/3m 0\.0/);
        assert.equal(await cards.nth(2).locator('.curve .d').count(),2,'negative supplied values remain plotted');
        assert.match(await cards.nth(2).innerText(),/3m -0\.4/);
        assert.equal(await cards.nth(3).locator('.curve .d').count(),0);
        const anchor=await heading.locator('..').innerText();assert.ok(anchor.includes('— 2y'));assert.ok(!anchor.includes('None'));
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
        await page.goBack();assert.equal(page.url(),origin);assert.equal(await input.inputValue(),query);
      }
    },{htmlOverride:ratesHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Market turns full reads are keyboard reachable ${theme} ${lang}`,async()=>{
    const turnsHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      'from tests.test_intl_workspace_integration import render_fixture,library_recovery_fixture; print(render_fixture(turn_board=library_recovery_fixture()))'],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{window.setTheme(theme);window.setLang(lang);},{theme,lang});
      const query=lang==='zh'?'市场转折':'Market turns';
      const input=page.locator('[data-im-library-search]:visible');await input.fill(query);
      const link=page.locator('[data-im-library-tool="market_turns"] a');const origin=page.url();
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        await link.focus();await page.keyboard.press('Enter');
        assert.equal(new URL(page.url()).hash,'#intl-market-turns');
        const heading=page.locator('#intl-market-turns');
        await heading.locator('.help').focus();await page.keyboard.press('Escape');
        const tiles=page.locator('.tb-tile');assert.equal(await tiles.count(),3);
        const names=lang==='zh'?['日本','香港','澳大利亚']:['Japan','Hong Kong','Australia'];
        const phrases=lang==='zh'?['确认仍不完整','修复尝试失败','健康上行']:['confirmation is incomplete','repair attempt as failed','Climbing in good health'];
        for(let i=0;i<3;i++) {
          await page.keyboard.press('Tab');
          const tile=tiles.nth(i);
          assert.equal(await tile.evaluate(n=>document.activeElement===n),true,`native Tab reaches ${names[i]} at ${width}`);
          assert.equal(await page.getByRole('group',{name:names[i]+' '+['JP','HK','AU'][i],exact:true}).count(),1);
          assert.equal(await tile.getAttribute('aria-describedby'),'lensPop');
          const pop=page.locator('#lensPop.open');assert.equal(await pop.count(),1);
          const text=await pop.innerText();assert.ok(text.toLocaleLowerCase().includes(names[i].toLocaleLowerCase()));assert.ok(text.includes(phrases[i]));
          const focus=await tile.evaluate(n=>({visible:n.matches(':focus-visible'),style:getComputedStyle(n).outlineStyle,width:parseFloat(getComputedStyle(n).outlineWidth)}));
          assert.equal(focus.visible,true);assert.notEqual(focus.style,'none');assert.ok(focus.width>=2);
          assert.equal(await page.evaluate(()=>document.documentElement.classList.contains('lens-lock')),width<=640);
          await page.keyboard.press('Escape');
          assert.equal(await page.locator('#lensPop.open').count(),0);
          assert.equal(await tile.evaluate(n=>document.activeElement===n),true);
          assert.equal(await tile.getAttribute('aria-describedby'),null);
          assert.equal(await page.evaluate(()=>document.documentElement.classList.contains('lens-lock')),false);
        }
        await page.keyboard.press('Tab');
        assert.equal(await page.locator('#intl-recovery-quality').evaluate(n=>document.activeElement===n),true);
        await page.goBack();assert.equal(page.url(),origin);assert.equal(await input.inputValue(),query);
      }
    },{htmlOverride:turnsHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Library opens supplied recovery assessments by keyboard ${theme} ${lang}`,async()=>{
    const recoveryHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      'from tests.test_intl_workspace_integration import render_fixture,library_recovery_fixture; print(render_fixture(turn_board=library_recovery_fixture()))'],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{window.setTheme(theme);window.setLang(lang);},{theme,lang});
      const input=page.locator('[data-im-library-search]:visible');
      const query=lang==='zh'?'修复质量':'Recovery quality';
      await input.fill(query);
      const link=page.locator('[data-im-library-tool="recovery_quality"] a[href="#intl-recovery-quality"]');
      assert.equal(await link.count(),1);
      const origin=page.url();
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        await link.focus();await page.keyboard.press('Enter');
        const target=page.locator('#intl-recovery-quality');
        const detail=target.locator('..');
        assert.equal(await detail.evaluate(n=>n.open),true);
        assert.equal(await target.evaluate(n=>document.activeElement===n),true);
        assert.equal(new URL(page.url()).hash,'#intl-recovery-quality');
        assert.equal(await detail.locator('[data-recovery-market]').count(),2);
        assert.equal(await detail.locator('[data-recovery-market="AU"]').count(),0);
        assert.match(await detail.innerText(),lang==='zh'?/部分覆盖/:/Partial coverage/);
        const jp=detail.locator('[data-recovery-market="JP"]');
        const hk=detail.locator('[data-recovery-market="HK"]');
        assert.match(await jp.innerText(),lang==='zh'?/日本[\s\S]*修复尝试[\s\S]*确认仍不完整/:/Japan[\s\S]*Repair attempt[\s\S]*confirmation is incomplete/);
        assert.match(await hk.innerText(),lang==='zh'?/香港[\s\S]*反弹失败/:/Hong Kong[\s\S]*Rebound failed/);
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
        await page.keyboard.press('Space');
        assert.equal(await detail.evaluate(n=>n.open),false);
        await page.keyboard.press('Space');
        assert.equal(await detail.evaluate(n=>n.open),true);
        await page.goBack();assert.equal(page.url(),origin);
        assert.equal(await input.inputValue(),query);
      }
    },{htmlOverride:recoveryHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price'});
  });
}

test('Library recovery disclosure remains native without JavaScript',async()=>{
  const recoveryHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
    'from tests.test_intl_workspace_integration import render_fixture,library_recovery_fixture; print(render_fixture(turn_board=library_recovery_fixture()))'],
    {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
  await pageFixture(async page=>{
    const link=page.locator('[data-im-library-tool="recovery_quality"] a[href="#intl-recovery-quality"]');
    await link.focus();await page.keyboard.press('Enter');
    const target=page.locator('#intl-recovery-quality');
    const detail=target.locator('..');
    assert.equal(await target.evaluate(n=>document.activeElement===n),true);
    assert.equal(await detail.evaluate(n=>n.open),false);
    await page.keyboard.press('Space');
    assert.equal(await detail.evaluate(n=>n.open),true);
    assert.match(await detail.locator('[data-recovery-market="JP"]').innerText(),/confirmation is incomplete/);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  },{htmlOverride:recoveryHtml,javaScriptEnabled:false,width:320});
});

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Library opens rendered trade links and returns to research ${theme} ${lang}`,async()=>{
    const tradeHtml = execFileSync(process.env.INTL_TEST_PYTHON || 'python3', ['-c',
      'from tests.test_intl_workspace_integration import render_fixture, library_trade_fixture; print(render_fixture(cgl=library_trade_fixture()))'],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{window.setTheme(theme);window.setLang(lang);},{theme,lang});
      const input=page.locator('[data-im-library-search]:visible');
      const query=lang==='zh'?'贸易与供应链联系':'Trade & supply links';
      await input.fill(query);
      const item=page.locator('[data-im-library-results] [data-im-library-tool="trade_supply_links"]');
      assert.match(await item.locator('[data-im-library-scope="model-context"]').innerText(),
        lang==='zh'?/模型背景，并非公司敞口/:/Model context, not company exposure/);
      const link=item.locator('a[href="#intl-trade-supply-links"]');
      assert.equal(await link.count(),1);
      const origin=page.url();
      for (const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        await link.focus();
        await page.keyboard.press('Enter');
        const target=page.locator('#intl-trade-supply-links');
        assert.equal(await target.isVisible(),true);
        assert.equal(await target.evaluate(n=>n.closest('details').open),true);
        const url=new URL(page.url());
        assert.equal(url.hash,'#intl-trade-supply-links');
        for(const [key,value] of [['view','library'],['market','JP'],['horizon','3m'],['basis','local']])
          assert.equal(url.searchParams.get(key),value);
        const panel=target.locator('..').locator('..');
        const text=await panel.innerText();
        assert.match(text,lang==='zh'?/升温/:/Building/);
        assert.match(text,lang==='zh'?/结构权重/:/structural weights/);
        assert.match(text,/38%/);
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
        await page.goBack();
        assert.equal(page.url(),origin);
        assert.equal(await input.inputValue(),query);
        assert.equal(await link.count(),1);
      }
    },{htmlOverride:tradeHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`History selection survives forced colors without hover or focus ${theme} ${lang}`,async t=>{
    await pageFixture(async page=>{
      await page.evaluate(theme=>window.setTheme(theme),theme);
      await page.emulateMedia({forcedColors:'active',colorScheme:theme});
      assert.equal(await page.evaluate(()=>matchMedia('(forced-colors: active)').matches),true);
      await page.selectOption('[data-im-controls] select[data-im-action="set_view"]','history');
      const panel=page.locator('[data-im-history-panel]:visible');
      const appearance=node=>{
        const s=getComputedStyle(node);
        return {decoration:s.textDecorationLine,weight:s.fontWeight,
          borderStyle:s.borderBottomStyle,borderWidth:s.borderBottomWidth};
      };
      for(const width of [390,320]) {
        await page.setViewportSize({width,height:900});
        for(const selected of ['scenario','history']) {
          const target=panel.locator(`[data-im-scenario-tab="${selected}"]`);
          await target.focus();
          await page.keyboard.press(selected==='scenario'?'Space':'Enter');
          assert.equal(await target.getAttribute('aria-pressed'),'true');
          assert.equal(await panel.getAttribute('data-im-history-tab'),selected);
          const focus=await target.evaluate(n=>({visible:n.matches(':focus-visible'),
            style:getComputedStyle(n).outlineStyle,width:parseFloat(getComputedStyle(n).outlineWidth)}));
          assert.equal(focus.visible,true);assert.notEqual(focus.style,'none');assert.ok(focus.width>=2);
          // Move both pointer and focus off the pair: a hover/focus highlight is not selection.
          await page.mouse.move(0,0);
          await page.locator('[data-im-controls] select[data-im-action="set_view"]').focus();
          const chosen=await target.evaluate(appearance);
          const unselected=panel.locator('[data-im-scenario-tab][aria-pressed="false"]');
          assert.equal(await unselected.count(),1);
          assert.notDeepEqual(chosen,await unselected.evaluate(appearance),
            'selected tab needs a non-color cue after focus and hover leave');
          assert.equal(await target.evaluate(n=>n.matches(':focus-visible')||n.matches(':hover')),false);
          assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
          t.diagnostic(JSON.stringify({theme,lang,width,selected,appearance:chosen}));
        }
      }
    },{width:390,htmlOverride:coldLocaleHtml,published:true,bootLanguage:lang});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Library placeholder text contrast ${theme} ${lang}`,async t=>{
    await pageFixture(async page=>{
      await page.evaluate(theme=>window.setTheme(theme),theme);
      await page.selectOption('[data-im-controls] select[data-im-action="set_view"]','library');
      const input=page.locator('[data-im-library-search]:visible');
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const m=await input.evaluate(node=>{
          const style=getComputedStyle(node),placeholder=getComputedStyle(node,'::placeholder');
          const rgb=value=>value.match(/[\d.]+/g).map(Number);
          const ink=rgb(placeholder.color),background=rgb(style.backgroundColor);
          const luminance=c=>c.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4)
            .reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
          const a=luminance(ink),b=luminance(background);
          return {shown:node.matches(':placeholder-shown'),text:node.placeholder,ink,background,opacity:placeholder.opacity,inputOpacity:style.opacity,backgroundImage:style.backgroundImage,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
        });
        assert.equal(m.shown,true);
        assert.equal(m.text,lang==='en'?'Tool name, question or alias':'工具名称、问题或别名');
        assert.equal(m.opacity,'1');assert.equal(m.inputOpacity,'1');assert.equal(m.backgroundImage,'none');
        assert.equal(m.ink.length,3);assert.equal(m.background.length,3);
        assert.ok(m.ratio>=4.5,JSON.stringify({theme,lang,width,...m}));
        t.diagnostic(JSON.stringify({theme,lang,width,ratio:m.ratio}));
      }
    },{published:true,htmlOverride:coldLocaleHtml,bootLanguage:lang,width:320});
  });
  test(`Risk return text contrast ${theme} ${lang}`,async t=>{
    await pageFixture(async page=>{
      await page.evaluate(theme=>window.setTheme(theme),theme);
      await page.selectOption('[data-im-controls] select[data-im-action="set_view"]','risk');
      await page.selectOption('[data-im-panel][data-view="risk"]:visible select[data-im-action="select_market"]','JP');
      const allValues=page.locator('[data-im-panel][data-view="risk"]:visible .intl-risk__value');
      const values=allValues.filter({visible:true});
      const before=await allValues.allTextContents();
      assert.ok(before.length>=3,'fixture must expose actual currency-channel values');
      const context=new URL(page.url()).search;
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const metrics=await values.evaluateAll(nodes=>{
          const canvas=document.createElement('canvas');canvas.width=canvas.height=1;
          const ctx=canvas.getContext('2d',{willReadFrequently:true});
          const rgb=value=>{ctx.clearRect(0,0,1,1);ctx.fillStyle=value;ctx.fillRect(0,0,1,1);return [...ctx.getImageData(0,0,1,1).data];};
          const luminance=c=>c.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4)
            .reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
          return nodes.map(node=>{
            const style=getComputedStyle(node),ink=rgb(style.color);
            // Current Risk values sit on opaque card/section surfaces. Fail if
            // this changes; do not silently measure against the wrong ancestor.
            let background=null;
            for(let p=node;p;p=p.parentElement) {
              const s=getComputedStyle(p),color=rgb(s.backgroundColor);
              if(s.opacity!=='1'||s.backgroundImage!=='none')throw Error('unsupported value surface');
              if(color[3]===255){background=color;break;}
              if(color[3]!==0)throw Error('translucent value surface');
            }
            if(!background||ink[3]!==255)throw Error('missing opaque value pair');
            const a=luminance(ink),b=luminance(background);
            return {text:node.textContent.trim(),direction:node.classList.contains('intl-risk__value--up')?'up':node.classList.contains('intl-risk__value--down')?'down':'flat',ink,background,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
          });
        });
        assert.ok(metrics.some(m=>m.direction==='up')&&metrics.some(m=>m.direction==='down'),'fixture must cover both direction hues');
        assert.ok(metrics.every(m=>m.ratio>=4.5),JSON.stringify({theme,lang,width,metrics}));
        for(const m of metrics.filter(m=>m.direction!=='flat')) {
          const green=(m.direction==='up')===(lang==='en');
          assert.ok(green?m.ink[1]>m.ink[0]:m.ink[0]>m.ink[1],`${lang}: lost directional colour convention`);
        }
        assert.deepEqual(await allValues.allTextContents(),before);
        assert.equal(new URL(page.url()).search,context);
        t.diagnostic(JSON.stringify({theme,lang,width,values:metrics.length,minContrast:Math.min(...metrics.map(m=>m.ratio))}));
      }
    },{published:true,htmlOverride:coldLocaleHtml,bootLanguage:lang,width:320});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Compare calculation-window links keep a full touch target ${theme} ${lang}`,async t=>{
    await pageFixture(async page=>{
      await page.evaluate(theme=>window.setTheme(theme),theme);
      await page.selectOption('[data-im-controls] select[data-im-action="set_view"]','compare');
      await page.evaluate(()=>document.fonts.ready);
      const panel=page.locator('[data-im-compare-panel]:visible');
      const links=panel.locator('.intl-compare__market a');
      assert.ok(await links.count()>=2,'fixture must expose multiple qualified calculation windows');
      for(const width of [320,390,1440]) {
        await page.setViewportSize({width,height:900});
        const metrics=await links.evaluateAll(nodes=>nodes.map(node=>{
          const rect=node.getBoundingClientRect();
          return {width:rect.width,height:rect.height,label:node.innerText.trim()};
        }));
        assert.ok(metrics.every(rect=>rect.width>=44&&rect.height>=44),JSON.stringify({theme,lang,width,metrics}));
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
        t.diagnostic(JSON.stringify({theme,lang,width,links:metrics.length,minHeight:Math.min(...metrics.map(rect=>rect.height))}));
      }
      const link=links.first();
      const destination=await link.getAttribute('href');
      const context=new URL(page.url()).search;
      await link.focus();
      await page.keyboard.press('Enter');
      await page.locator(destination).waitFor({state:'visible'});
      assert.equal(new URL(page.url()).hash,destination);
      assert.equal(new URL(page.url()).search,context);
      assert.equal(await panel.isVisible(),true);
    },{published:true,htmlOverride:coldLocaleHtml,bootLanguage:lang,width:320});
  });
}

// Read Chromium's computed accessibility tree, including browser-resolved names
// and descriptions. This is narrower than screen-reader speech acceptance.
for (const lang of ['en','zh']) for (const width of [1440,320]) {
  test(`Workspace accessibility tree ${lang} ${width}`,async t=>{
    await pageFixture(async page=>{
      const client=await page.context().newCDPSession(page);
      async function snapshot() {
        const document=(await client.send('DOM.getDocument',{depth:-1})).root;
        const owned=new Map();
        function collect(node,inWorkspace=false,inHiddenPanel=false,inControls=false,inDialog=false) {
          const attrs={};
          for(let i=0;i<(node.attributes||[]).length;i+=2) attrs[node.attributes[i]]=node.attributes[i+1];
          inWorkspace ||= Object.hasOwn(attrs,'data-im-workspace');
          inHiddenPanel ||= Object.hasOwn(attrs,'data-im-panel') && Object.hasOwn(attrs,'hidden');
          inControls ||= Object.hasOwn(attrs,'data-im-controls');
          inDialog ||= node.nodeName==='DIALOG' && Object.hasOwn(attrs,'open');
          if(inWorkspace) owned.set(node.backendNodeId,{attrs,inHiddenPanel,inControls,inDialog});
          for(const child of node.children||[]) collect(child,inWorkspace,inHiddenPanel,inControls,inDialog);
        }
        collect(document);
        const nodes=(await client.send('Accessibility.getFullAXTree')).nodes;
        return nodes.filter(node=>owned.has(node.backendDOMNodeId)&&!node.ignored)
          .map(node=>({...node,dom:owned.get(node.backendDOMNodeId)}));
      }
      function prop(node,name) {return node.properties?.find(item=>item.name===name)?.value.value;}
      for(const view of ['overview','compare','macro','risk','history','library']) {
        if(width===320) await page.selectOption('[data-im-controls] select[data-im-action="set_view"]',view);
        else await page.locator(`[data-im-controls] button[data-im-view="${view}"]`).click();
        const panel=page.locator(`[data-im-panel][data-view="${view}"]:visible`);
        await panel.waitFor();
        const nodes=await snapshot();
        assert.equal(nodes.filter(node=>node.dom.inHiddenPanel).length,0,`${view}: inactive panel exposed`);
        const controls=nodes.filter(node=>['button','combobox','textbox','searchbox','link','checkbox','radio'].includes(node.role.value));
        assert.ok(controls.length>=4,`${view}: empty control census`);
        assert.deepEqual(controls.filter(node=>!node.name?.value.trim()).map(node=>node.role.value),[],`${view}: unnamed control`);
        const region=nodes.find(node=>Object.hasOwn(node.dom.attrs,'data-im-workspace'));
        assert.equal(region.role.value,'region');
        assert.equal(region.name.value,lang==='zh'?'国际市场':'International markets');
        const selected=nodes.filter(node=>node.dom.inControls && node.dom.attrs['data-im-action']==='set_view');
        if(width===1440) {
          assert.equal(selected.filter(node=>prop(node,'pressed')==='true').length,1);
          assert.equal(selected.find(node=>prop(node,'pressed')==='true').dom.attrs['data-im-view'],view);
        } else {
          assert.equal(selected.length,1);
          assert.equal(selected[0].role.value,'combobox');
          assert.equal(selected[0].name.value,lang==='zh'?'视图':'Views');
        }
        t.diagnostic(JSON.stringify({view,lang,width,namedControls:controls.length,inactivePanelNodesExposed:0}));
        if(view==='overview') {
          await panel.locator('[data-im-expansion-trigger]').click();
          const trigger=page.locator('[data-im-inspector-origin]:visible')
            .filter({has:page.locator('[data-im-inspector-payload][data-market-id="JP"]')})
            .locator('[data-im-inspector-trigger]');
          await trigger.click();
          const modalNodes=await snapshot();
          const dialog=modalNodes.find(node=>node.role.value==='dialog');
          assert.ok(dialog && dialog.name.value.trim());
          assert.equal(prop(dialog,'modal'),true);
          const exposedControls=modalNodes.filter(node=>['button','combobox','textbox','searchbox','link'].includes(node.role.value));
          assert.ok(exposedControls.length>0);
          assert.ok(exposedControls.every(node=>node.dom.inDialog && node.name?.value.trim()),'modal exposes unnamed or background controls');
          await page.keyboard.press('Escape');
          assert.equal(await trigger.evaluate(node=>node===document.activeElement),true);
          assert.ok((await snapshot()).some(node=>node.dom.inControls),'toolbar absent after modal close');
          t.diagnostic(JSON.stringify({lang,width,inspectorDialogName:dialog.name.value,modalControls:exposedControls.length,backgroundControlsExposed:0}));
        }
        if(view==='history') {
          if(width===320) await panel.locator('[data-im-scenario-tab="scenario"]').click();
          await panel.locator('[data-im-scenario-field="local"]').fill('not a number');
          await panel.locator('[data-im-scenario-field="fx"]').fill('0');
          await panel.locator('[data-im-scenario-action="calculate"]').click();
          const error=await panel.locator('[data-im-scenario-error="local"]').innerText();
          const invalid=(await snapshot()).find(node=>node.dom.attrs['data-im-scenario-field']==='local');
          assert.equal(invalid.role.value,'textbox');
          assert.equal(invalid.name.value,lang==='zh'?'本币价格回报 (%)':'Local-price return (%)');
          assert.equal(prop(invalid,'invalid'),'true');
          assert.ok(error.length>0 && invalid.description.value.includes(error));
          const help=await panel.locator('#im-scenario-format').innerText();
          assert.ok(invalid.description.value.includes(help));
          assert.equal(prop(invalid,'focused'),true);
          // Correcting the input must remove the old error from the computed
          // description and retain the localized instructions.
          await panel.locator('[data-im-scenario-field="local"]').fill('5');
          await panel.locator('[data-im-scenario-action="calculate"]').click();
          const valid=(await snapshot()).find(node=>node.dom.attrs['data-im-scenario-field']==='local');
          assert.equal(prop(valid,'invalid'),'false');
          assert.equal(valid.description.value,help);
          const status=(await snapshot()).find(node=>Object.hasOwn(node.dom.attrs,'data-im-scenario-announcement'));
          assert.equal(status.role.value,'status');
          assert.equal(prop(status,'live'),'polite');
          assert.equal(prop(status,'atomic'),true);
        }
      }
    },{published:true,htmlOverride:coldLocaleHtml,bootLanguage:lang,width});
  });
}

for (const published of [false,true]) for (const boot of [
  {name:'saved English',bootLanguage:'en',browserLocale:'zh-CN',expected:'en'},
  {name:'saved Chinese',bootLanguage:'zh',browserLocale:'en-US',expected:'zh'},
  {name:'browser Chinese',bootLanguage:null,browserLocale:'zh-CN',expected:'zh'}
]) {
  test(`cold-load locale ${boot.name} with ${published?'published':'raw'} script order`,async()=>{
    await pageFixture(async page=>{
      const labels=await page.locator('[data-im-workspace] option[data-im-label-en]').evaluateAll(options=>options.map(option=>({
        actual:option.textContent,expected:option.getAttribute(document.documentElement.dataset.lang==='zh'?'data-im-label-zh':'data-im-label-en')
      })));
      assert.ok(labels.length>10);
      assert.ok(labels.every(label=>label.actual===label.expected),JSON.stringify(labels.filter(label=>label.actual!==label.expected).slice(0,8)));
      assert.match(await page.locator('[data-im-scenario-context]').textContent(),boot.expected==='zh'?/研究口径/:/Research basis/);
      assert.equal(await page.locator('html').getAttribute('lang'),boot.expected==='zh'?'zh-CN':'en');
      const sourceOrder=await page.locator('script[src]').evaluateAll(nodes=>nodes.map(node=>({src:node.getAttribute('src'),defer:node.defer})));
      const theme=sourceOrder.findIndex(node=>node.src.startsWith('theme.js'));
      const entry=sourceOrder.findIndex(node=>node.src.startsWith('intl_workspace_entry.js'));
      assert.ok(theme>entry);
      assert.equal(sourceOrder[theme].defer,published);
      await page.locator('[data-im-controls] button[data-im-view="history"]').click();
      const context=page.locator('[data-im-panel][data-view="history"]:visible [data-im-scenario-context]');
      assert.match(await context.innerText(),boot.expected==='zh'?/研究口径/:/Research basis/);
      assert.equal(new URL(page.url()).searchParams.get('view'),'history');
    },{published,htmlOverride:coldLocaleHtml,...boot});
  });
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

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Library legacy links reflow without risk-desk data at 320px ${theme} ${lang}`,async()=>{
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{window.setTheme(theme);window.setLang(lang);},{theme,lang});
      await page.selectOption('select[data-im-action="set_view"]','library');
      await page.selectOption('[data-im-action="set_horizon"]','3m');
      await page.selectOption('[data-im-action="set_basis"]','local');
      const panel=page.locator('[data-im-library-static]:visible');
      const catalogue=JSON.parse(await panel.locator('[data-im-library-catalogue]').textContent());
      const input=panel.locator('[data-im-library-search]');
      for (const key of ['cross_country','growth_inflation']) {
        const query=catalogue.find(tool=>tool.presentation_key===key)['label_'+lang];
        await input.fill(query);
        const anchor=panel.locator(`[data-im-library-results] [data-im-library-tool="${key}"] a`);
        const hash=await anchor.getAttribute('href');
        await anchor.click();
        assert.equal(await page.locator(hash).isVisible(),true);
        assert.equal(await page.locator(hash).evaluate(node=>{
          for(let parent=node.parentElement;parent;parent=parent.parentElement) {
            if(parent.tagName==='DETAILS'&&!parent.open)return false;
          }
          return true;
        }),true);
        const sizes=await page.evaluate(()=>({viewport:innerWidth,page:document.documentElement.scrollWidth}));
        assert.ok(sizes.page<=sizes.viewport,JSON.stringify({key,theme,lang,...sizes}));
        const summaries=await page.locator('details.ref-fold > summary:visible').evaluateAll(nodes=>nodes.map(node=>({
          summary:node.getBoundingClientRect().width,
          description:node.querySelector('.rf-s').getBoundingClientRect().width
        })));
        assert.ok(summaries.every(row=>row.description>row.summary*0.7),JSON.stringify(summaries));
        assert.equal(new URL(page.url()).searchParams.get('horizon'),'3m');
        assert.equal(new URL(page.url()).searchParams.get('basis'),'local');
        if(key==='cross_country') {
          const table=await page.locator(hash).locator('..').locator('.gridwrap').evaluate(node=>
            ({scrollWidth:node.scrollWidth,clientWidth:node.clientWidth,overflowX:getComputedStyle(node).overflowX}));
          assert.ok(['auto','scroll'].includes(table.overflowX),JSON.stringify(table));
          if(table.scrollWidth>table.clientWidth) {
            assert.ok(await page.locator(hash).locator('..').locator('.gridwrap').evaluate(node=>{node.scrollLeft=30;return node.scrollLeft;})>0);
          }
        }
        await page.goBack();
        assert.equal(new URL(page.url()).hash,'');
        assert.equal(await input.inputValue(),query);
      }
    },{width:320});
  });
}

for (const options of [{javaScriptEnabled:false},{broken:true}]) {
  test(options.broken?'failed enhancement restores readable page':'no JavaScript retains every roster and legacy research', async()=>{
    await pageFixture(async page=>{
      assert.equal(await page.locator('[data-im-enhanced]').count(),0);
      assert.equal(await page.locator('[data-im-controls]').evaluate(n=>n.disabled),true);
      assert.equal(await page.locator('[data-im-panel][data-view="overview"]:visible').count(),10);
      assert.equal(await page.locator('[data-im-compare-panel]:visible').count(),10);
      assert.equal(await page.locator('[data-im-panel][data-view="library"]:visible').count(),1);
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
        if(state==='negative') {
          const positiveReturns=page.locator('[data-im-summary] .intl-overview__stats > div').filter({
            has:page.locator(`dt .l-${lang}:visible`,{hasText:lang==='zh'?/^正回报$/:/^Positive returns$/})
          });
          assert.equal(await positiveReturns.count(),1);
          assert.equal(await positiveReturns.locator('dd').innerText(),'0 / 7');
        }
        if(state==='denied') assert.doesNotMatch(await page.locator('[data-im-workspace]').innerText(),/Nikkei|FTSE/);
        if(process.env.INTL_BROWSER_EVIDENCE_DIR) {
          await page.waitForTimeout(1250);
          await page.locator('[data-im-workspace]').screenshot({path:path.join(process.env.INTL_BROWSER_EVIDENCE_DIR,`${state}-${width}-${theme}-${lang}.png`)});
        }
      }
    },{state});
  });
}

for (const width of [1440,390]) test(`actual Library search and retained research link work at ${width}px`,async()=>{
  await pageFixture(async page=>{
    if(width===1440)await page.click('button[data-im-view="library"]');
    else await page.selectOption('select[data-im-action="set_view"]','library');
    assert.equal(await page.locator('[data-im-library-static]:visible').count(),1);
    assert.equal(await page.locator('[data-im-library-search]').isEnabled(),true);
    await page.fill('[data-im-library-search]','cross country');
    assert.equal(await page.locator('[data-im-library-results] [data-im-library-tool]').count(),1);
    const link=page.locator('[data-im-library-results] a');
    assert.equal(await link.getAttribute('href'),'#intl-cross-country');
    await link.click();
    assert.equal(await page.locator('#intl-cross-country').isVisible(),true);
    assert.equal(new URL(page.url()).searchParams.get('view'),'library');
    await page.fill('[data-im-library-search]','增长');
    assert.equal(await page.locator('[data-im-library-results] [data-im-library-tool]').getAttribute('data-im-library-tool'),'growth_inflation');
    await page.selectOption('[data-im-action="set_horizon"]','3m');
    await page.selectOption('[data-im-action="set_basis"]','local');
    assert.equal(await page.locator('[data-im-library-static]:visible').count(),1);
    assert.equal(await page.inputValue('[data-im-library-search]'),'增长');
  },{width});
});

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Compass verdict remains readable at narrow widths and enlarged text ${theme} ${lang}`,async()=>{
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{window.setTheme(theme);window.setLang(lang);},{theme,lang});
      await page.locator('[data-im-workspace] a[href="#intl-legacy-research"]').click();
      await page.evaluate(()=>document.fonts.ready);
      for (const width of [320,390,820,821,1440]) for (const scale of [1,2]) {
        await page.setViewportSize({width,height:900});
        await page.locator('.wc-gside').evaluate((side,scale)=>{
          const nodes=[side,...side.querySelectorAll('*')];
          nodes.forEach(n=>n.style.removeProperty('font-size'));
          const sizes=nodes.map(n=>[n,parseFloat(getComputedStyle(n).fontSize)]);
          if(scale===2)sizes.forEach(([n,size])=>n.style.fontSize=size*2+'px');
        },scale);
        const metrics=await page.locator('.wc').evaluate(card=>{
          const rect=n=>{const r=n.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width};};
          const side=card.querySelector('.wc-gside'),walker=document.createTreeWalker(side,NodeFilter.SHOW_TEXT);
          const lines=[];let text;
          while((text=walker.nextNode())) {
            if(!text.textContent.trim())continue;
            const range=document.createRange();range.selectNodeContents(text);
            for(const r of range.getClientRects())if(r.width&&r.height)lines.push({left:r.left,right:r.right,top:r.top,bottom:r.bottom});
          }
          return {card:rect(card),gauge:rect(card.querySelector('.wc-gauge')),side:rect(side),lines,
            verdictFont:parseFloat(getComputedStyle(card.querySelector('.wc-verdict')).fontSize),
            pageWidth:document.documentElement.scrollWidth,viewport:innerWidth};
        });
        assert.ok(metrics.lines.length>0);
        assert.ok(metrics.lines.every(r=>r.left>=metrics.card.left&&r.right<=metrics.card.right&&
          r.top>=metrics.card.top&&r.bottom<=metrics.card.bottom),JSON.stringify({width,scale,theme,lang,...metrics}));
        assert.ok(metrics.pageWidth<=metrics.viewport,JSON.stringify({width,scale,...metrics}));
        assert.equal(metrics.verdictFont,22*scale);
        if(width===1440&&scale===1)assert.ok(metrics.side.top<metrics.gauge.bottom&&metrics.side.bottom>metrics.gauge.top);
      }
    });
  });
}

for (const reading of [null,0,54]) {
  test(`Compass accessible name follows locale and reading ${reading}`,async()=>{
    const risk=reading===null?null:{score:reading,label_en:reading===0?'Risk-off':'Neutral',label_zh:reading===0?'风险规避':'中性',tone:reading===0?'down':'flat',coverage_pct:null,top_drags:[]};
    const htmlOverride=execFileSync(process.env.INTL_TEST_PYTHON||'python3',[
      '-c','import json,sys; from tests.test_intl_workspace_integration import _render_compass; print(_render_compass(json.loads(sys.argv[1])))',JSON.stringify(risk)],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.locator('[data-im-workspace] a[href="#intl-legacy-research"]').click();
      for(const lang of ['en','zh','en']) {
        await page.evaluate(lang=>window.setLang(lang),lang);
        const caption=lang==='zh'?'全球风险偏好':'World risk appetite';
        const verdict=reading===null?(lang==='zh'?'暂无数据':'Unavailable'):(lang==='zh'?risk.label_zh:risk.label_en);
        const name=[caption,...(reading===null?[]:[String(reading),'/ 100']),verdict].join(' ');
        assert.equal(await page.locator('.wc-gauge').getByRole('img',{name,exact:true}).count(),1,
          await page.locator('.wc-gauge').ariaSnapshot());
      }
    },{width:320,htmlOverride});
  });
}


for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`History dated table preserves readable cells and keyboard scrolling ${theme} ${lang}`,async()=>{
    const htmlOverride=execFileSync(process.env.INTL_TEST_PYTHON||'python3',[
      '-c','from tests.test_intl_workspace_integration import render_history_fixture; print(render_history_fixture())'],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      await page.selectOption('select[data-im-action="set_view"]','history');
      await page.selectOption('[data-im-history-panel] select[data-im-action="select_market"]','JP');
      const observations=page.locator('[data-im-history-market="JP"] .intl-history__observations');
      await observations.locator('summary').click();
      const dates=await observations.locator('tbody th').allTextContents();
      assert.ok(dates.some(date=>date.includes('.123456789+09:00')));
      const baseFont=await observations.locator('table').evaluate(n=>parseFloat(getComputedStyle(n).fontSize));
      for(const width of [320,390,768,1440]) for(const scale of [1,2]) {
        await page.setViewportSize({width,height:900});
        await observations.locator('table').evaluate((n,size)=>n.style.fontSize=size+'px',baseFont*scale);
        const lines=await observations.locator('tbody th').evaluateAll(nodes=>nodes.map(n=>{
          const range=document.createRange();range.selectNodeContents(n);return range.getClientRects().length;
        }));
        assert.deepEqual(lines,[1,1,1],JSON.stringify({width,scale,theme,lang,lines}));
        assert.deepEqual(await observations.locator('tbody th').allTextContents(),dates);
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
        const name=lang==='zh'?'当前重建 · 保留来源日期':'Current reconstruction · source dates preserved';
        const region=observations.getByRole('region',{name,exact:true});
        await observations.locator('summary').focus();await page.keyboard.press('Tab');
        assert.equal(await region.evaluate(n=>n===document.activeElement),true);
        assert.ok(await region.evaluate(n=>parseFloat(getComputedStyle(n).outlineWidth)>=2));
        const overflow=await region.evaluate(async n=>{
          n.scrollTo({left:0,behavior:'instant'});
          // Commit the resize/scroll reset before testing a new native key scroll.
          await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);
          return n.scrollWidth>n.clientWidth;
        });
        if(overflow){
          await page.keyboard.press('ArrowRight');
          try {await page.waitForFunction(()=>{
            const n=document.activeElement;return n?.getAttribute('role')==='region'&&n.scrollLeft>0;
          });} catch(error) {
            throw new Error(JSON.stringify({width,scale,theme,lang,scroll:await region.evaluate(n=>({left:n.scrollLeft,client:n.clientWidth,total:n.scrollWidth,active:n===document.activeElement}))}),{cause:error});
          }
        }
        await region.evaluate(n=>n.scrollLeft=n.scrollWidth);
        const bounds=await region.evaluate(n=>{
          const r=n.getBoundingClientRect(),last=n.querySelector('tbody tr td:last-child').getBoundingClientRect();
          return {left:r.left,right:r.right,lastLeft:last.left,lastRight:last.right,scroll:n.scrollLeft,max:n.scrollWidth-n.clientWidth};
        });
        assert.ok(bounds.lastRight<=bounds.right+1&&bounds.lastLeft>=bounds.left-1,JSON.stringify({width,scale,...bounds}));
        assert.equal(await observations.locator('.tbl-scroll').count(),1);

      }
      await page.locator('[data-im-history-panel] footer button[data-im-view="overview"]').click();
      assert.equal(new URL(page.url()).searchParams.get('market'),'JP');
      assert.equal(await page.locator('[data-im-history-panel]').isVisible(),false);
    },{width:320,htmlOverride});
  });
}
