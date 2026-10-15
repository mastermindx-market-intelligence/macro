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

// LENS deliberately closes on resize and fragment navigation. Wait for the
// native event's handlers before opening a new disclosure: viewport/URL changes
// can be observable before those queued events have been delivered.
async function afterWindowEvent(page, event, action) {
  await page.evaluate(event => {
    window.__intlTestWindowEventDone = false;
    window.addEventListener(event, () => requestAnimationFrame(() => {
      window.__intlTestWindowEventDone = true;
    }), {once:true});
  }, event);
  await action();
  await page.waitForFunction(() => window.__intlTestWindowEventDone === true);
}

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

const sourceChartHtml = new Map();
function sourceChartFixture(isolated=false) {
  // Actual publisher/renderer with existing synthetic parquet inputs. This is
  // source composition evidence, never live data or a new disclosure grant.
  if (!sourceChartHtml.has(isolated)) sourceChartHtml.set(isolated,execFileSync(process.env.INTL_TEST_PYTHON||'python3',['-c',`
from pathlib import Path
from tempfile import TemporaryDirectory
from tests.test_intl_eod_publication import _setup, EVALUATED
from tests.test_intl_workspace_integration import render_fixture
from engine.intl_inputs import countries
from scripts import build_intl
with TemporaryDirectory(prefix='intl-chart-page-') as tmp:
    frame, _ = _setup(Path(tmp))
    if ${isolated ? 'True' : 'False'}:
        for market in ('AU', 'KR'):
            symbol = countries()[market]['fx']
            frame.loc[frame.index[${isolated === 'edges' ? '[-21, -2]' : '[-12, -10]'}], symbol] = float('nan')
            filename = symbol.replace('^', '_').replace('=', '_').replace('/', '_') + '.parquet'
            frame[[symbol]].rename(columns={symbol:'close'}).to_parquet(Path(tmp)/'intl'/filename)
    sink = {}
    workspace = build_intl._publication_workspace(frame, data_root=Path(tmp), evaluated_at=EVALUATED, chart_source_sink=sink)
    print(render_fixture(workspace_payload=workspace, chart_sources=sink['sources']))
`],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:8*1024*1024}));
  return sourceChartHtml.get(isolated);
}

for (const bootLanguage of ['en','zh']) {
  test(`Source chart accessible reading follows locale and selection ${bootLanguage}`,async()=>{
    await pageFixture(async page=>{
      const panel=page.locator('[data-im-compare-panel]:not([hidden])');
      const picker=panel.locator('[data-im-compare-pin]');
      await picker.selectOption('1');await picker.selectOption('4');
      const chart=panel.locator('[data-im-chart-model]');
      const geometry=await chart.locator('[data-im-chart-series]').evaluateAll(ns=>ns.map(n=>[n.getAttribute('d'),n.getAttribute('transform')]));
      const client=await page.context().newCDPSession(page);
      async function reading(lang,count) {
        const prefix=lang==='zh'?'相同起点，不同走势。 可比市场组 1':'Same starting point. Different paths. Comparable group 1';
        const snapshot=(await client.send('Accessibility.getFullAXTree')).nodes;
        const image=snapshot.find(n=>!n.ignored&&n.role?.value==='image'&&n.name?.value.startsWith(prefix));
        assert.ok(image,'chart must expose the current language and selected count: '+JSON.stringify(snapshot.filter(n=>!n.ignored&&n.role?.value==='image').map(n=>n.name?.value)));
        assert.match(image.name.value,new RegExp('·\\s*'+count+'\\s*'+(lang==='zh'?'个市场':'markets')));
        assert.match(image.name.value,/2026-09-08.*2026-10-07/);
        assert.match(image.description?.value||'',lang==='zh'?/每组从可观测起点基准化至 100.*未填补缺失的价格或汇率/:/Price levels rebased to 100 at each observed start.*no missing price or FX value was filled/);
        if(lang==='en') assert.doesNotMatch(image.name.value+image.description.value,/[\u4e00-\u9fff]/);
        else assert.doesNotMatch(image.name.value+image.description.value,/Rebased|market|observed|missing/i);
      }
      await reading(bootLanguage,2);
      for(const lang of [bootLanguage==='en'?'zh':'en',bootLanguage]) {
        const before=page.url();
        await page.evaluate(lang=>setLang(lang),lang);
        await reading(lang,2);assert.equal(page.url(),before);
      }
      await picker.selectOption('2');await reading(bootLanguage,3);
      await page.goBack();await reading(bootLanguage,2);
      assert.deepEqual(await chart.locator('[data-im-chart-series]').evaluateAll(ns=>ns.map(n=>[n.getAttribute('d'),n.getAttribute('transform')])),geometry);
    },{htmlOverride:sourceChartFixture(),width:320,bootLanguage,initialSearch:'?view=compare'});
  });
}

test('Source chart endpoint symbols remain unclipped',async()=>{
  await pageFixture(async page=>{
    await page.emulateMedia({reducedMotion:'reduce'});
    const panel=page.locator('[data-im-compare-panel]:not([hidden])');
    const picker=panel.locator('[data-im-compare-pin]');
    await picker.selectOption('1');await picker.selectOption('4');
    const chart=panel.locator('[data-im-chart-model]');
    for(const width of [320,1440]) {
      await page.setViewportSize({width,height:900});
      const marks=await chart.locator('[data-im-chart-point]:not([hidden])').evaluateAll(ns=>ns.map(n=>{
        const s=n.ownerSVGElement, box=s.getBoundingClientRect(), point=n.getBoundingClientRect();
        const outside=point.left<box.left||point.right>box.right||point.top<box.top||point.bottom>box.bottom;
        return {market:n.dataset.imChartSeries,position:n.getAttribute('transform'),clipped:outside&&getComputedStyle(s).overflow!=='visible'};
      }));
      assert.equal(marks.length,4,'each selected series has two isolated endpoints');
      assert.ok(marks.some(m=>m.position.startsWith('translate(0.0 ')));
      assert.ok(marks.some(m=>m.position.startsWith('translate(640.0 ')));
      assert.ok(marks.every(m=>!m.clipped),'the SVG viewport must not cut endpoint symbols in half: '+JSON.stringify(marks));
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    }
  },{htmlOverride:sourceChartFixture('edges'),width:320,initialSearch:'?view=compare'});
});

for(const theme of ['dark','light']) for(const lang of ['en','zh']) {
  test(`Source chart isolated observations retain market identity ${theme} ${lang}`,async()=>{
    await pageFixture(async page=>{
      await page.emulateMedia({reducedMotion:'reduce'});
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang)},{theme,lang});
      const panel=page.locator('[data-im-compare-panel]:not([hidden])');
      const picker=panel.locator('[data-im-compare-pin]');
      await picker.selectOption('1');await picker.selectOption('4');
      const chart=panel.locator('[data-im-chart-model]');
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const marks=await chart.evaluate(c=>Array.from(c.querySelectorAll('[data-im-chart-series]:not([hidden])')).filter(n=>!n.getAttribute('d')).map(n=>{
          const shape=n.querySelector('path')||n;
          const legend=c.querySelector('[data-im-chart-table-market="'+n.dataset.imChartSeries+'"] [data-im-chart-point-key]');
          return {market:n.dataset.imChartSeries,shape:shape.getAttribute('d')||shape.tagName,legend:legend?.getAttribute('d'),position:n.getAttribute('transform'),bounds:shape.getBoundingClientRect().toJSON()};
        }));
        assert.deepEqual(marks.map(m=>m.market).sort(),['AU','KR']);
        assert.notEqual(marks[0].shape,marks[1].shape,'isolated points must identify the market without color alone');
        for(const m of marks) {
          assert.equal(m.shape,m.legend,'the named key must identify the isolated observation');
          assert.ok(m.bounds.width>=5&&m.bounds.height>=5,'phone symbols must remain visible');
        }
        assert.deepEqual(marks.map(m=>[m.market,m.position]).sort(),[['AU','translate(331.03 107.05)'],['KR','translate(331.03 176.41)']]);
        const rows=await chart.locator('[data-im-chart-table-market]:not([hidden])').allTextContents();
        assert.ok(rows.every(r=>/20\s+2/.test(r)),rows.join('|'));
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
      await panel.locator('[data-im-compare-remove="4"]').click();
      await page.goBack();
      assert.equal(await chart.locator('[data-im-chart-series="KR"]:not([hidden])').count(),3);
      assert.equal(await chart.locator('[data-im-chart-benchmark-unavailable]').isVisible(),true);
    },{htmlOverride:sourceChartFixture(true),width:320,bootLanguage:lang,initialSearch:'?view=compare'});
  });
  test(`Source chart reused colors retain distinct line keys ${theme} ${lang}`,async()=>{
    await pageFixture(async page=>{
      await page.emulateMedia({reducedMotion:'reduce'});
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang)},{theme,lang});
      const panel=page.locator('[data-im-compare-panel]:not([hidden])');
      const picker=panel.locator('[data-im-compare-pin]');
      // The full publisher cohort gives Australia and Korea the same hue.
      await picker.selectOption('1');await picker.selectOption('4');
      const chart=panel.locator('[data-im-chart-model]');
      assert.match(await chart.locator('figcaption').first().innerText(),lang==='zh'?/线型和点形用于区分市场。未观测日期中断曲线/:/Line and point styles identify markets\. Unobserved dates break the series/);
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const keys=await chart.evaluate(c=>Array.from(c.querySelectorAll('[data-im-chart-series]:not([hidden])')).map(n=>{
          const style=getComputedStyle(n);
          const legend=c.querySelector('[data-im-chart-table-market="'+n.dataset.imChartSeries+'"] svg line');
          const label=getComputedStyle(legend);
          return {market:n.dataset.imChartSeries,key:[style.stroke,style.strokeDasharray],legend:[label.stroke,label.strokeDasharray],vector:style.vectorEffect,legendWidth:legend.ownerSVGElement.getBoundingClientRect().width};
        }));
        assert.deepEqual(keys.map(k=>k.market).sort(),['AU','KR']);
        assert.notDeepEqual(keys[0].key,keys[1].key,'selected series must not share the same line key');
        for(const k of keys) {
          assert.deepEqual(k.key,k.legend,'the named legend must match its actual series');
          assert.equal(k.vector,'non-scaling-stroke','phone scaling must preserve the distinguishing pattern');
          assert.ok(k.legendWidth>=30,'legend must show the complete distinguishing pattern');
        }
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:sourceChartFixture(),width:320,bootLanguage:lang,initialSearch:'?view=compare'});
  });
  test(`Source chart heading counts committed visible markets ${theme} ${lang}`,async()=>{
    await pageFixture(async page=>{
      await page.emulateMedia({reducedMotion:'reduce'});
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang)},{theme,lang});
      const active='[data-im-compare-panel]:not([hidden])';
      const panel=page.locator(active),picker=panel.locator('[data-im-compare-pin]');
      await picker.selectOption('0');await picker.selectOption('1');
      const chart=panel.locator('[data-im-chart-model]'),group=chart.locator('[data-im-chart-cohort]:not([hidden])');
      async function countIs(n) {
        assert.match(await group.locator('summary').innerText(),new RegExp('·\\s*'+n+'\\s*(?:markets|个市场)'));
        assert.equal(await group.locator('[data-im-chart-table-market]:not([hidden])').count(),n);
        assert.equal(await group.locator('[data-im-chart-series]:not([hidden])').evaluateAll(ns=>new Set(ns.map(n=>n.dataset.imChartSeries)).size),n);
      }
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        await countIs(2);
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
      await picker.selectOption('2');await countIs(3);
      const before=await chart.innerHTML(),url=page.url();
      const geometry=await chart.locator('[data-im-chart-series]').evaluateAll(ns=>ns.map(n=>n.getAttribute('d')));
      await page.evaluate(()=>{window.__chartPagePush=history.pushState;history.pushState=()=>{throw Error('synthetic navigation failure')}});
      try {await panel.locator('[data-im-compare-remove="2"]').click();}
      finally {await page.evaluate(()=>{history.pushState=window.__chartPagePush;delete window.__chartPagePush});}
      await countIs(3);assert.equal(await chart.innerHTML(),before);assert.equal(page.url(),url);
      await panel.locator('[data-im-compare-remove="2"]').click();await countIs(2);
      assert.deepEqual(await chart.locator('[data-im-chart-series]').evaluateAll(ns=>ns.map(n=>n.getAttribute('d'))),geometry);
      await page.goBack();await countIs(3);
      await page.locator('[data-im-action="set_basis"]').selectOption('local');await countIs(3);
      await page.goBack();await countIs(3);
      assert.equal(await chart.locator('[data-im-chart-benchmark-unavailable]').isVisible(),true);
    },{htmlOverride:sourceChartFixture(),width:320,bootLanguage:lang,initialSearch:'?view=compare'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Correlation cell readings remain legible ${theme} ${lang}`,async t=>{
    const h=execFileSync('python3',['-c',"from tests.test_intl_correlation_coverage_render import correlation_fixture; from tests.test_intl_workspace_integration import render_fixture; c=correlation_fixture(); c['cells'][0][2]=c['cells'][2][0]=0.; c['cells'][1][2]=c['cells'][2][1]=.5; print(render_fixture(perf={'correlation':c}))"],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      const panel=page.locator('#intl-cross-market-correlation').locator('..').locator('..');
      const cells=panel.locator('tbody td');const before=await cells.allTextContents();
      assert.ok(before.includes('0.00')&&before.includes('0.50')&&before.includes('1.00'));
      assert.equal(await panel.locator('[data-correlation-unavailable]').count(),7);
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const readings=await cells.evaluateAll(nodes=>{
          const c=document.createElement('canvas');c.width=c.height=1;const ctx=c.getContext('2d',{willReadFrequently:true});
          const rgb=value=>{ctx.clearRect(0,0,1,1);ctx.fillStyle=value;ctx.fillRect(0,0,1,1);return [...ctx.getImageData(0,0,1,1).data];};
          const lum=c=>c.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
          return nodes.map(n=>{const s=getComputedStyle(n),ink=rgb(s.color),bg=rgb(s.backgroundColor),a=lum(ink),b=lum(bg);return {text:n.textContent.trim(),diag:n.classList.contains('diag'),opacity:s.opacity,ink,bg,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};});
        });
        t.diagnostic(JSON.stringify({theme,lang,width,readings}));
        assert.ok(readings.every(m=>m.opacity==='1'&&m.ink[3]===255&&m.bg[3]===255&&m.ratio>=4.5),JSON.stringify({theme,lang,width,readings}));
        assert.deepEqual(await cells.allTextContents(),before);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{published:true,htmlOverride:h,bootLanguage:lang,width:320,initialSearch:'?view=library#intl-cross-market-correlation'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Reference unknown contrast and correlation limits ${theme} ${lang}`,async t=>{
    const h=execFileSync('python3',['-c',"from tests.test_intl_cross_country_reading_render import country_fixture; from tests.test_intl_correlation_coverage_render import correlation_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(records=country_fixture(),perf={'correlation':correlation_fixture()}))"],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});await page.goto('http://intl.test/intl.html?view=library#intl-cross-country');
        await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
        const chip=page.locator('table.cmp .q-unknown').first();
        const reading=await chip.evaluate(node=>{
          const rgb=value=>value.match(/[\d.]+/g).map(Number);
          const style=getComputedStyle(node),ink=rgb(style.color);let parent=node,background;
          while(parent){const bg=rgb(getComputedStyle(parent).backgroundColor);if(bg.length===3 || bg[3]===1){background=bg;break;}parent=parent.parentElement;}
          const lum=c=>c.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
          const a=lum(ink),b=lum(background);return {ink,background,opacity:style.opacity,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
        });
        assert.ok(reading.ratio>=4.5,JSON.stringify({theme,lang,width,...reading}));assert.equal(reading.opacity,'1');
        t.diagnostic(JSON.stringify({theme,lang,width,...reading}));
        await page.goto('http://intl.test/intl.html?view=library#intl-cross-market-correlation');
        const panel=page.locator('#intl-cross-market-correlation').locator('..').locator('..');
        const text=await panel.innerText();assert.ok(text.includes(lang==='zh'?'相反的成对关系':'opposing pairwise relationships'));
        assert.ok(!text.includes(lang==='zh'?'分散价值显著':'meaningful diversification'));assert.equal(await panel.locator('td.diag').count(),3);
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:h,published:true,bootLanguage:lang,width:320,initialSearch:'?view=library#intl-cross-country'});
  });
}

for (const lang of ['en','zh']) {
  test(`Performance unavailable period remains useful ${lang}`,async()=>{
    const h=execFileSync('python3',['-c',"from tests.test_intl_performance_reading_render import performance_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(perf=performance_fixture(short_only=True)))"],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      const board=page.locator('#lb-board');assert.equal(await board.locator('.lb-row').count(),0);
      assert.ok((await board.innerText()).includes(lang==='zh'?'所选期间暂无可用收益':'No returns available for the selected period'));
      await page.locator('#lb-seg button[data-h="1m"]').focus();await page.keyboard.press('Enter');
      assert.equal(await board.locator('.lb-row').count(),3);assert.equal(await board.locator('[data-lb-empty]').count(),0);
      await page.locator('#lb-seg button[data-h="12m"]').focus();await page.keyboard.press('Enter');assert.equal(await board.locator('[data-lb-empty]').count(),1);
    },{htmlOverride:h,published:true,bootLanguage:lang,width:320,initialSearch:'?view=library#lb-board'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Cross-country composite and unknown extension ${theme} ${lang}`,async()=>{
    const h=execFileSync('python3',['-c',"from tests.test_intl_cross_country_reading_render import country_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(records=country_fixture()))"],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});await page.goto('http://intl.test/intl.html?view=library&market=JP&horizon=3m&basis=local&return_basis=price');
        await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
        const input=page.locator('[data-im-library-search]'),query=lang==='zh'?'跨经济体':'Cross-country';await input.fill(query);
        const link=page.locator('[data-im-library-results] a[href="#intl-cross-country"]');await link.focus();await page.keyboard.press('Enter');
        const heading=page.locator('#intl-cross-country');assert.equal(await heading.evaluate(n=>n===document.activeElement),true);
        const panel=heading.locator('..'),region=panel.locator('[data-cross-country-scroll]');await region.focus();assert.equal(await region.evaluate(n=>n===document.activeElement),true);
        assert.equal(await panel.locator('tbody tr').count(),3);const last=panel.locator('tbody tr').last().locator('td').last();assert.ok((await last.innerText()).includes(lang==='zh'?'不可用':'Unavailable'));
        if(width===320)assert.ok(await region.evaluate(n=>n.scrollWidth>n.clientWidth+1),'focused region must own narrow overflow');
        if(await region.evaluate(n=>n.scrollWidth>n.clientWidth+1)){await page.keyboard.press('ArrowRight');await page.waitForFunction(()=>document.querySelector('[data-cross-country-scroll]').scrollLeft>0);}
        await region.scrollIntoViewIfNeeded();await region.evaluate(n=>n.scrollLeft=n.scrollWidth);
        await page.waitForFunction(()=>{const n=document.querySelector('[data-cross-country-scroll]');return n.scrollLeft>=n.scrollWidth-n.clientWidth-1;});
        assert.ok(await last.evaluate(n=>{const r=n.getBoundingClientRect();const top=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return top===n||n.contains(top);}), 'rightmost extension reading must not be covered by the Economy column');
        const text=await panel.innerText();assert.ok(text.includes(lang==='zh'?'市场压力':'Market stress'));assert.ok(text.includes(lang==='zh'?'波动率':'volatility'));
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.goBack();assert.equal(new URL(page.url()).hash,'');assert.equal(await input.inputValue(),query);
      }
    },{htmlOverride:h,published:true,bootLanguage:lang,width:320,initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Performance FX contribution keyboard ${theme} ${lang}`,async()=>{
    const h=execFileSync('python3',['-c',"from tests.test_intl_performance_reading_render import performance_fixture; from tests.test_intl_rotation_reading_render import rotation_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(perf=performance_fixture(),rotation_ranks=rotation_fixture()))"],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});await page.goto('http://intl.test/intl.html?view=library&market=JP&horizon=3m&basis=local&return_basis=price');
        await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
        const input=page.locator('[data-im-library-search]'),query=lang==='zh'?'汇率':'currency';await input.fill(query);
        const link=page.locator('[data-im-library-results] a[href="#lb-board"]');await link.focus();await page.keyboard.press('Enter');
        const board=page.locator('#lb-board');assert.equal(await board.evaluate(n=>n===document.activeElement),true);
        assert.equal(await board.locator('.lb-row').count(),3);assert.ok((await board.innerText()).includes(lang==='zh'?'12月美元不可用':'12m USD unavailable'));
        await page.keyboard.press('Shift+Tab');assert.equal(await page.evaluate(()=>document.activeElement.dataset.h),'12m');await page.keyboard.press('Enter');
        assert.equal(await board.locator('.lb-row').count(),2);
        const text=await board.innerText();assert.ok(text.includes(lang==='zh'?'汇率贡献 -3.2百分点':'FX contribution -3.2pp'),text);assert.ok(text.includes(lang==='zh'?'汇率贡献 +0.0百分点':'FX contribution +0.0pp'),text);
        const bars=await board.locator('.lb-bar').evaluateAll(ns=>ns.map(n=>n.getBoundingClientRect().width));assert.ok(bars.every(w=>w>=80),JSON.stringify({width,bars}));
        const one=page.locator('#lb-seg button[data-h="1m"]');await one.focus();await page.keyboard.press('Enter');assert.equal(await board.locator('.lb-row').count(),3);
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
        await page.goBack();assert.equal(new URL(page.url()).hash,'');assert.equal(await input.inputValue(),query);assert.equal(new URL(page.url()).searchParams.get('market'),'JP');
      }
    },{htmlOverride:h,published:true,bootLanguage:lang,width:320,initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Leadership composite reading keyboard ${theme} ${lang}`,async()=>{
    const h=execFileSync('python3',['-c',"from tests.test_intl_rotation_reading_render import rotation_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(rotation_ranks=rotation_fixture()))"],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        await page.goto('http://intl.test/intl.html?view=library&market=JP&horizon=3m&basis=local&return_basis=price');
        await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
        const input=page.locator('[data-im-library-search]');const query=lang==='zh'?'轮动':'rotation';await input.fill(query);
        const link=page.locator('[data-im-library-results] a[href="#intl-leadership-rotation"]');assert.equal(await link.count(),1);
        await link.focus();await page.keyboard.press('Enter');
        const heading=page.locator('#intl-leadership-rotation');assert.equal(await heading.evaluate(n=>n===document.activeElement),true);
        const panel=heading.locator('..');const region=panel.locator('[data-rotation-scroll]');
        assert.deepEqual(await panel.locator('[data-rotation-market]').evaluateAll(ns=>ns.map(n=>n.dataset.rotationMarket)),['JP','KR','IN','TW']);
        const scores=await panel.locator('[data-rotation-score]').allTextContents();assert.equal(scores[2],'0.000');assert.equal(scores[3],'-6.600');assert.ok(Number(scores[0])>Number(scores[1])&&Number(scores[1])>3);
        assert.ok((await panel.innerText()).includes(lang==='zh'?'缺失窗口在模型中按零计入':'Missing windows enter the model as zero'));
        await page.keyboard.press('Tab');const lens=page.locator('.lens-pop.open');await lens.waitFor({state:'visible'});
        const method=await lens.innerText();for(const term of ['50%','30%','20%','MACD'])assert.ok(method.includes(term),method);
        assert.ok(method.includes(lang==='zh'?'基准':'benchmark'));assert.ok(method.includes(lang==='zh'?'绝对':'absolute'));
        await page.keyboard.press('Escape');await region.focus();assert.equal(await region.evaluate(n=>n===document.activeElement),true);
        assert.equal(await region.locator('.tbl-scroll').count(),0,'no inaccessible nested scroller');
        if(width===320 && lang==='en')assert.ok(await region.evaluate(n=>n.scrollWidth>n.clientWidth+1),'focused region must own narrow overflow');
        if(width===320 && lang==='zh')assert.ok(await region.evaluate(n=>n.querySelector('table').getBoundingClientRect().width<=n.clientWidth+1 && n.scrollWidth<=n.clientWidth+1),'short Chinese content fits without scrolling');
        if(await region.evaluate(n=>n.scrollWidth>n.clientWidth+1)){await page.keyboard.press('ArrowRight');await page.waitForFunction(()=>document.querySelector('[data-rotation-scroll]').scrollLeft>0);}
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
        await page.goBack();assert.equal(new URL(page.url()).hash,'');assert.equal(await input.inputValue(),query);
        for(const [key,value] of [['market','JP'],['horizon','3m'],['basis','local']])assert.equal(new URL(page.url()).searchParams.get(key),value);
      }
    },{htmlOverride:h,published:true,bootLanguage:lang,width:320,initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Correlation availability keyboard journey ${theme} ${lang}`,async()=>{
    const h=execFileSync('python3',['-c',"from tests.test_intl_correlation_coverage_render import correlation_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(perf={'correlation':correlation_fixture()}))"],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        await page.goto('http://intl.test/intl.html?view=library&market=JP&horizon=3m&basis=local&return_basis=price');
        await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
        const input=page.locator('[data-im-library-search]');const query=lang==='zh'?'相关':'correlation';await input.fill(query);
        const link=page.locator('[data-im-library-results] a[href="#intl-cross-market-correlation"]');assert.equal(await link.count(),1);
        await link.focus();await page.keyboard.press('Enter');
        const heading=page.locator('#intl-cross-market-correlation');assert.equal(await heading.evaluate(n=>n===document.activeElement),true);
        const panel=heading.locator('xpath=ancestor::div[contains(concat(" ",normalize-space(@class)," ")," panel ")][1]');
        assert.equal(await panel.locator('td.diag').count(),3);assert.equal(await panel.locator('[data-correlation-unavailable]').count(),7);
        assert.ok((await panel.locator('[data-correlation-coverage]').innerText()).includes('3 / 6'));
        const region=panel.locator('[data-correlation-scroll]');await region.focus();assert.equal(await region.evaluate(n=>n===document.activeElement),true);
        assert.equal(await region.getAttribute('aria-labelledby'),'intl-cross-market-correlation');
        if(width===320)assert.ok(await region.evaluate(n=>n.scrollWidth>n.clientWidth+1),'focused region must own narrow overflow');
        if(await region.evaluate(n=>n.scrollWidth>n.clientWidth+1)){
          await page.keyboard.press('ArrowRight');await page.waitForFunction(()=>document.querySelector('[data-correlation-scroll]').scrollLeft>0);
        }
        const text=await panel.innerText();assert.ok(text.includes(lang==='zh'?'美元周收益':'weekly USD returns'));assert.ok(text.includes(lang==='zh'?'配置窗口':'Configured window'));
        await heading.focus();await page.keyboard.press('Tab');const lens=page.locator('.lens-pop.open');await lens.waitFor({state:'visible'});assert.ok((await lens.innerText()).includes(lang==='zh'?'缺失值':'Missing values'));
        await page.keyboard.press('Escape');await page.goBack();assert.equal(new URL(page.url()).hash,'');assert.equal(await input.inputValue(),query);
        assert.equal(new URL(page.url()).searchParams.get('market'),'JP');assert.equal(new URL(page.url()).searchParams.get('horizon'),'3m');assert.equal(new URL(page.url()).searchParams.get('basis'),'local');
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:h,published:true,bootLanguage:lang,width:320,initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Regime map missing coordinate journey ${theme} ${lang}`,async()=>{
    const h=execFileSync('python3',['-c',"from tests.test_intl_regime_map_absence_render import map_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(heatmap=map_fixture()))"],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        await page.goto('http://intl.test/intl.html?view=library&market=JP&horizon=3m&basis=local&return_basis=price');
        await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
        const input=page.locator('[data-im-library-search]');const query=lang==='zh'?'增长':'growth';await input.fill(query);
        const link=page.locator('[data-im-library-results] a[href="#intl-growth-inflation"]');assert.equal(await link.count(),1);
        await link.focus();await page.keyboard.press('Enter');
        const heading=page.locator('#intl-growth-inflation');assert.equal(await heading.evaluate(n=>n===document.activeElement),true);
        const panel=heading.locator('xpath=ancestor::div[contains(concat(" ",normalize-space(@class)," ")," panel ")][1]');
        assert.equal(await panel.locator('.scatter .pt').count(),3);
        assert.deepEqual(await panel.locator('.scatter .pt .n').allTextContents(),['JP','CA','AU']);
        assert.ok((await panel.locator('[data-regime-coverage]').innerText()).includes('3 / 7'));
        const details=panel.locator('[data-regime-missing]');const summary=details.locator('summary');
        assert.equal(await details.getAttribute('open'),null);await summary.focus();await page.keyboard.press('Enter');
        assert.equal(await details.getAttribute('open'),'');assert.equal(await summary.evaluate(n=>n===document.activeElement),true);
        assert.equal(await panel.locator('[data-regime-unplotted]:visible').count(),4);
        const text=await details.innerText();for(const term of ['GB','KR','TW','IN','0.3','-0.2','-0.5',lang==='zh'?'不可用':'Unavailable'])assert.ok(text.includes(term),text);
        const rows=details.locator('[data-regime-unplotted]');
        assert.equal(await rows.evaluateAll(ns=>ns.every(n=>{const r=n.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&n.scrollWidth<=n.clientWidth+1;})),true);
        await page.keyboard.press('Space');assert.equal(await details.getAttribute('open'),null);
        await page.goBack();assert.equal(new URL(page.url()).hash,'');assert.equal(await input.inputValue(),query);
        assert.equal(new URL(page.url()).searchParams.get('market'),'JP');assert.equal(new URL(page.url()).searchParams.get('horizon'),'3m');assert.equal(new URL(page.url()).searchParams.get('basis'),'local');
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:h,published:true,bootLanguage:lang,width:320,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Trade method keyboard read ${theme} ${lang}`,async()=>{
    const h=execFileSync('python3',['-c',"from tests.test_intl_trade_pressure_method_render import method_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(cgl=method_fixture()))"],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        await page.goto('http://intl.test/intl.html?view=library&market=JP&horizon=3m&basis=local&return_basis=price');
        await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
        const input=page.locator('[data-im-library-search]');const query=lang==='zh'?'贸易':'trade';await input.fill(query);
        const link=page.locator('[data-im-library-results] a[href="#intl-trade-supply-links"]');assert.equal(await link.count(),1);
        await link.focus();await page.keyboard.press('Enter');
        const heading=page.locator('#intl-trade-supply-links');assert.equal(await heading.evaluate(n=>n===document.activeElement),true);
        const panel=heading.locator('xpath=ancestor::div[contains(concat(" ",normalize-space(@class)," ")," panel ")][1]');
        const text=await panel.innerText();
        assert.ok(text.includes(lang==='zh'?'来源百分比是关联权重，并非压力占比。':'Source percentages are linkage weights, not shares of pressure.'));
        assert.ok(text.includes(lang==='zh'?'等级是历史区间，并非趋势。':'Levels are historical bands, not a trend.'));
        assert.ok(text.includes('35%'));
        await page.keyboard.press('Tab');const lens=page.locator('.lens-pop.open');await lens.waitFor({state:'visible'});
        const method=await lens.innerText();
        for(const term of (lang==='zh'?['ETF波动率','21期','10期','最多采用504','至少需要252','并非因果','不是预测']:['ETF volatility','21-observation','10-observation','up to 504','at least 252','not causal','not a forecast']))assert.ok(method.includes(term),method);
        assert.doesNotMatch(method,/actually falling|真实下跌市场/);
        assert.ok(await lens.evaluate(n=>{const r=n.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&n.scrollWidth<=n.clientWidth+1;}));
        await page.keyboard.press('Escape');await lens.waitFor({state:'hidden'});
        await page.goBack();assert.equal(new URL(page.url()).hash,'');
        assert.equal(await input.inputValue(),query);assert.equal(new URL(page.url()).searchParams.get('market'),'JP');
        assert.equal(new URL(page.url()).searchParams.get('horizon'),'3m');assert.equal(new URL(page.url()).searchParams.get('basis'),'local');
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:h,published:true,bootLanguage:lang,width:320,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price'});
  });
}

test('Trade pressure bars survive absent Risk desk',async()=>{
  for(const withRisk of [false,true]) {
    const h=execFileSync('python3',['-c',`from tests.test_intl_trade_pressure_absence_render import mixed_pressure_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(cgl=mixed_pressure_fixture(),risk_desk=${withRisk?"{'built':'synthetic:fixture'}":"None"}))`],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      const panel=page.locator('#intl-trade-supply-links').locator('xpath=ancestor::div[contains(concat(" ",normalize-space(@class)," ")," panel ")][1]');
      const bars=panel.locator('.ird-tx-bar-wrap');assert.equal(await bars.count(),3);
      const geometry=await bars.evaluateAll(ns=>ns.map(n=>({track:n.getBoundingClientRect().toJSON(),fill:n.firstElementChild.getBoundingClientRect().toJSON()})));
      assert.ok(geometry.every(g=>g.track.height>=6&&g.track.width>=40),JSON.stringify({withRisk,geometry}));
      assert.ok(geometry[0].fill.width>0&&geometry[1].fill.width>0&&geometry[2].fill.width===0);
    },{htmlOverride:h,published:true,width:320,initialSearch:'?view=library#intl-trade-supply-links'});
  }
});

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Trade pressure missing history ${theme} ${lang}`,async()=>{
    const h=execFileSync('python3',['-c',"from tests.test_intl_trade_pressure_absence_render import mixed_pressure_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(cgl=mixed_pressure_fixture()))"],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        await page.goto('http://intl.test/intl.html?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-trade-supply-links');
        await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
        const panel=page.locator('#intl-trade-supply-links').locator('xpath=ancestor::div[contains(concat(" ",normalize-space(@class)," ")," panel ")][1]');
        const rows=panel.locator('.ird-tx-row');assert.equal(await rows.count(),11);
        const labels=await rows.locator('span.chip').allInnerTexts();
        assert.deepEqual(labels.slice(0,3),lang==='zh'?['高','升温','低']:['High','Building','Low']);
        assert.deepEqual(labels.slice(3).filter(t=>t!==(lang==='zh'?'风险输出方':'exporting risk')),Array(8).fill(lang==='zh'?'不可用':'Unavailable'));
        assert.equal(await panel.locator('.ird-tx-bar-wrap').count(),3);
        assert.ok((await panel.innerText()).includes(lang==='zh'?'缺少历史比较不代表压力低。':'A missing historical comparison is not a low reading.'));
        assert.ok((await panel.innerText()).includes('35%'));
        assert.ok((await panel.innerText()).includes(lang==='zh'?'已报告数据缺口：42':'Reported data gaps: 42'));
        assert.ok(!(await panel.innerText()).includes(lang==='zh'?'今晚':'tonight'));
        for(let i=0;i<11;i++) {
          const row=rows.nth(i);await row.scrollIntoViewIfNeeded();assert.equal(await row.isVisible(),true);
          assert.ok(await row.evaluate(n=>{const r=n.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1;}));
          assert.equal(await row.locator('.rrx-rec-chip').evaluateAll(ns=>ns.every(n=>{const r=n.getBoundingClientRect(),p=n.closest('.ird-tx-row').getBoundingClientRect();return r.left>=p.left&&r.right<=p.right+1&&n.scrollWidth<=n.clientWidth+1;})),true,'source chips stay inside their row');
        }
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
        assert.equal(new URL(page.url()).searchParams.get('market'),'JP');
      }
    },{htmlOverride:h,published:true,bootLanguage:lang,width:320,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-trade-supply-links'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Fragility disclosure warning details ${theme} ${lang}`,async()=>{
    const fixture=JSON.parse(execFileSync('python3',['-c',"import json; from tests.test_intl_fragility_disclosure_render import disclosure_fixture; from tests.test_intl_workspace_integration import render_fixture; p=disclosure_fixture(); print(json.dumps({'html':render_fixture(risk_desk=p),'countries':p['vulnerability']['countries']}))"],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024}));
    await pageFixture(async page=>{
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        await page.goto('http://intl.test/intl.html?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-structural-fragility');
        await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
        const panel=page.locator('#intl-structural-fragility').locator('xpath=ancestor::div[contains(concat(" ",normalize-space(@class)," ")," panel ")][1]');
        const disclosure=panel.locator('details');const summary=disclosure.locator('summary');
        const hiddenRows=disclosure.locator('.ird-frag-row');assert.equal(await hiddenRows.count(),2);
        assert.equal(await hiddenRows.first().isVisible(),false);
        await summary.focus();await page.keyboard.press('Enter');
        assert.equal(await disclosure.getAttribute('open'),'');
        const rows=panel.locator('.ird-frag-row');assert.equal(await rows.count(),5);
        for(let i=0;i<fixture.countries.length;i++) {
          const expected=fixture.countries[i];const row=rows.nth(i);
          assert.equal(await row.isVisible(),true);
          assert.ok((await row.innerText()).includes(expected['name_'+lang]));
          assert.deepEqual(await row.locator('.ird-frag-tags .chip').allInnerTexts(),expected.tags.map(t=>t[lang]),expected.iso3);
          assert.equal(await row.locator('.ird-frag-tags .chip').evaluateAll(nodes=>nodes.every(n=>{const r=n.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&n.scrollWidth<=n.clientWidth+1;})),true,'warning text stays readable within the viewport');
        }
        assert.equal(await summary.evaluate(n=>n===document.activeElement),true);
        await page.keyboard.press('Space');assert.equal(await disclosure.getAttribute('open'),null);
        assert.equal(await hiddenRows.first().isVisible(),false);
        assert.equal(await summary.evaluate(n=>n===document.activeElement),true);
        await page.keyboard.press('Space');assert.equal(await hiddenRows.last().isVisible(),true);
        await page.keyboard.press('Enter');assert.equal(await hiddenRows.last().isVisible(),false);
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
        assert.equal(new URL(page.url()).searchParams.get('market'),'JP');
      }
    },{htmlOverride:fixture.html,published:true,bootLanguage:lang,width:320,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-structural-fragility'});
  });
}

for (const scenario of ['partial','flagged']) for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Fragility supplied scope ${scenario} ${theme} ${lang}`,async()=>{
    const h=execFileSync('python3',['-c',`from tests.test_intl_fragility_scope_render import fragility_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(risk_desk=fragility_fixture('${scenario}')))`],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        await page.goto('http://intl.test/intl.html?view=library&market=JP&horizon=3m&basis=local&return_basis=price');
        await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
        const query=lang==='zh'?'脆弱':'fragility';
        const input=page.locator('[data-im-library-search]');await input.fill(query);
        const link=page.locator('[data-im-library-results] a[href="#intl-structural-fragility"]');assert.equal(await link.count(),1);
        await link.focus();await page.keyboard.press('Enter');
        const heading=page.locator('#intl-structural-fragility');assert.equal(await heading.evaluate(n=>n===document.activeElement),true);
        const panel=heading.locator('xpath=ancestor::div[contains(concat(" ",normalize-space(@class)," ")," panel ")][1]');
        const text=await panel.innerText();assert.ok(text.includes(lang==='zh'?'已提供数据的国家：1':'Countries with supplied data: 1'));
        assert.ok(text.includes(lang==='zh'?'缺失输入不代表已全面排除预警':'Incomplete inputs do not establish an all-clear'));
        assert.ok(!/map is clear|next WEO release|IMF WEO 2025|暂无标记/.test(text));
        assert.ok(text.includes(scenario==='partial'?'2022–2022':'2024–2024'));
        assert.equal(await panel.locator('.ird-frag-row').count(),scenario==='flagged'?1:0);
        if(scenario==='flagged') assert.ok(text.includes(lang==='zh'?'美国':'United States'));
        await page.keyboard.press('Tab');const lens=page.locator('.lens-pop.open');await lens.waitFor({state:'visible'});
        assert.ok(!(await lens.innerText()).includes('2025'));await page.keyboard.press('Escape');await lens.waitFor({state:'hidden'});
        await page.goBack();assert.equal(new URL(page.url()).hash,'');assert.equal(await input.inputValue(),query);
        assert.equal(new URL(page.url()).searchParams.get('market'),'JP');
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:h,published:true,bootLanguage:lang,width:320,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Contagion keyboard method journey ${theme} ${lang}`,async()=>{
    const h=execFileSync('python3',['-c',"from tests.test_intl_connectedness_scope_render import connectedness_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(risk_desk=connectedness_fixture('matrix')))"],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        await page.goto('http://intl.test/intl.html?view=library&market=JP&horizon=3m&basis=local&return_basis=price');
        await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
        const query=lang==='zh'?'传导':'contagion';
        const input=page.locator('[data-im-library-search]');await input.fill(query);
        const link=page.locator('[data-im-library-results] a[href="#intl-contagion"]');assert.equal(await link.count(),1);
        await link.focus();await page.keyboard.press('Enter');
        const heading=page.locator('#intl-contagion');assert.equal(await heading.evaluate(n=>n===document.activeElement),true);
        assert.ok(await heading.evaluate(n=>getComputedStyle(n).outlineStyle!=='none'));
        const panel=heading.locator('xpath=ancestor::div[contains(concat(" ",normalize-space(@class)," ")," panel ")][1]');
        assert.equal(await panel.locator('.ird-tx-row .help.help-upgraded[tabindex="0"]').count(),3,'each contribution method has the canonical keyboard trigger');
        const lens=page.locator('.lens-pop.open');
        await page.keyboard.press('Tab');await lens.waitFor({state:'visible'});
        assert.ok((await lens.innerText()).includes(lang==='zh'?'逐行归一化':'row-normalized'));
        await page.keyboard.press('Escape');await lens.waitFor({state:'hidden'});
        for(const value of ['160.0','20.0','20.0']) {
          await page.keyboard.press('Tab');await lens.waitFor({state:'visible'});
          const text=await lens.innerText();assert.ok(text.includes(value)&&text.includes(lang==='zh'?'可超过100':'may exceed 100'),text);
          await page.keyboard.press('Escape');await lens.waitFor({state:'hidden'});
        }
        await page.keyboard.press('Tab');await lens.waitFor({state:'visible'});
        assert.ok((await lens.innerText()).includes(lang==='zh'?'分母':'Denominator'));
        await page.keyboard.press('Escape');await lens.waitFor({state:'hidden'});
        await page.goBack();assert.equal(new URL(page.url()).hash,'');
        assert.equal(await input.inputValue(),query);assert.equal(new URL(page.url()).searchParams.get('market'),'JP');
        assert.equal(new URL(page.url()).searchParams.get('horizon'),'3m');assert.equal(new URL(page.url()).searchParams.get('basis'),'local');
        assert.equal(await page.locator('.lens-pop.open').count(),0);
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:h,published:true,bootLanguage:lang,width:320,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Connectedness read keeps model scope ${theme} ${lang}`,async()=>{
    const kind=theme==='dark'?'matrix':'absent';
    const connectedHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      `from tests.test_intl_connectedness_scope_render import connectedness_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(risk_desk=connectedness_fixture('${kind}')))`],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      const panel=page.locator('#intl-contagion').locator('xpath=ancestor::div[contains(concat(" ",normalize-space(@class)," ")," panel ")][1]');assert.ok(await panel.isVisible());
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});const text=await panel.innerText();
        assert.ok(text.includes(lang==='zh'?'模型波动率关联':'Modelled volatility links'),text);
        const clock=await panel.locator('[data-connectedness-clock]').innerText();
        assert.ok(clock.includes(lang==='zh'?'模型快照日期':'Model snapshot date'),clock);
        if(kind==='absent') {
          assert.equal(await panel.locator('.dc-num,.ur-num').count(),0);
          assert.ok(clock.includes(lang==='zh'?'不可用':'Unavailable'));
        } else {
          assert.equal(await panel.locator('.dc-num').innerText(),'67');assert.equal(await panel.locator('.ur-num').innerText(),'20.0%');
          assert.ok(text.includes(lang==='zh'?'SPY波动率方差份额':'SPY volatility variance share'));
          assert.ok(text.includes(lang==='zh'?'模型序列：3':'Model series: 3'));
          const tip=await panel.locator('.ird-tx-row').first().getAttribute(lang==='zh'?'data-tip-zh':'data-tip-en');
          assert.ok(tip.includes('160.0')&&tip.includes(lang==='zh'?'可超过100':'may exceed 100'),tip);
        }
        assert.ok(!/shocks travel fast|quickly reach|压力可快速蔓延/.test(text));
        assert.ok(await panel.evaluate(n=>n.scrollWidth<=n.clientWidth+1));
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:connectedHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-contagion'});
  });
}

for (const [available,hot] of [[0,0],[3,0],[6,3]]) for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`EM headline coverage stays scoped ${available} ${theme} ${lang}`,async()=>{
    const emHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      `from tests.test_intl_em_coverage_render import em_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(risk_desk=em_fixture(${available},${hot})))`],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      const chip=page.locator('.ird-hchip').first();assert.ok(await chip.isVisible());
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const text=await chip.innerText();
        assert.ok(text.includes(lang==='zh'?`${available}/6项指标可用`:`${available}/6 signals available`),text);
        assert.ok(text.includes(lang==='zh'?`${hot}项触发`:`${hot} triggered`),text);
        const state=available===0?(lang==='zh'?'不可用':'Unavailable'):available===3?(lang==='zh'?'平静':'Calm'):(lang==='zh'?'压力较高':'Stressed');
        assert.ok((await chip.locator('.hc-state').innerText()).includes(state),text);
        assert.ok(text.includes(lang==='zh'?'同步指标':'Coincident indicator'),text);
        assert.ok(!/All stress|No action|Watch|EM positions|所有压力|无需操作|仓位|明日再查/.test(text));
        assert.ok(!(await chip.getAttribute('class')).split(' ').includes('state-ok'));
        assert.ok(await chip.evaluate(n=>n.scrollWidth<=n.clientWidth+1),'coverage fits');
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:emHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-contagion'});
  });
}

for (const kind of ['absent','complete_hot']) for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Transmission coverage stays honest ${kind} ${theme} ${lang}`,async()=>{
    const transmissionHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      `from tests.test_intl_transmission_coverage_render import transmission_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(risk_desk=transmission_fixture('${kind}')))`],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      const chip=page.locator('.ird-hchip').nth(1);
      const panel=page.locator('#intl-contagion').locator('xpath=ancestor::div[contains(concat(" ",normalize-space(@class)," ")," panel ")][1]');
      assert.ok(await chip.isVisible() && await panel.isVisible());
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const n=kind==='absent'?0:4,text=await chip.innerText();
        assert.ok(text.includes(lang==='zh'?`${n}/4已评估`:`${n}/4 assessed`),text);
        assert.ok(text.includes(lang==='zh'?`${n}项触发`:`${n} triggered`),text);
        if(kind==='absent') assert.ok(text.includes(lang==='zh'?'不可用':'Unavailable'));
        assert.ok(!/Ignore|Tighten stops|Not reaching|可忽略|收紧.*止损|5 US|5个/.test(text));
        const legs=panel.locator('[data-transmission-leg]');assert.equal(await legs.count(),4);
        for(const leg of await legs.all()) {
          const reading=await leg.innerText();assert.ok(reading.includes(kind==='absent'?(lang==='zh'?'不可用':'Unavailable'):(lang==='zh'?'已触发':'Triggered')),reading);
          assert.ok(!(await leg.getAttribute('class')).split(' ').includes('ok'));
        }
        const safety=await panel.locator('[data-transmission-safety]').innerText();
        assert.ok(safety.includes(lang==='zh'?'信息项':'Informational'));
        assert.ok(safety.includes(kind==='absent'?(lang==='zh'?'不可用':'Unavailable'):(lang==='zh'?'已标记':'Flagged')));
        for(const el of [chip,panel]) assert.ok(await el.evaluate(n=>n.scrollWidth<=n.clientWidth+1),'summary and channel readings fit');
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:transmissionHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-contagion'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`ECB balance read separates policy and weekly-bin clock ${theme} ${lang}`,async()=>{
    const kind=theme==='dark'?'flat':'down';
    const ecbHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      `from tests.test_intl_ecb_scope_render import ecb_scope_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(rates=ecb_scope_fixture('${kind}')))`],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      const card=page.locator('.rcard').filter({hasText:'ECB balance-sheet impulse'});
      assert.equal(await card.count(),1);assert.ok(await card.isVisible());
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const text=await card.innerText();
        assert.ok(text.includes(kind==='flat'?(lang==='zh'?'所供精度下未下降':'Non-decreasing at supplied precision'):
          (lang==='zh'?'低于52周前':'Lower than 52 weeks ago')),text);
        assert.ok(!/\beasing\b|\bQT\b|宽松|缩表/.test(text));
        assert.ok(text.includes(lang==='zh'?'周分箱结束日':'Weekly bin ending') && text.includes('2026-04-05'));
        assert.ok(text.includes(lang==='zh'?'观测日期不可用':'Observation date unavailable'));
        assert.ok(!text.includes('2026-03-30'),'source observation date is not supplied by owner output');
        assert.ok(await card.evaluate(n=>n.scrollWidth<=n.clientWidth+1 && n.scrollHeight<=n.clientHeight+1),'ECB card content fits');
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:ecbHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-rates-curves'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Periphery keeps supplied precision and Bund clock scope ${theme} ${lang}`,async()=>{
    const peripheryHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      "from tests.test_intl_periphery_scope_render import periphery_scope_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(rates=periphery_scope_fixture()))"],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      const panel=page.locator('#intl-euro-fragmentation').locator('..');
      assert.ok(await panel.isVisible());
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const reads=await panel.locator('tbody tr td:last-child').allInnerTexts();
        assert.deepEqual(reads,lang==='zh'?['不可用','所供精度下未走阔','所供精度下未走阔','走阔','收窄','走阔']:
          ['Unavailable','Non-widening at supplied precision','Non-widening at supplied precision','widening','tightening','widening']);
        const clock=await panel.locator('[data-periphery-date]').innerText();
        assert.ok(clock.includes(lang==='zh'?'德债序列日期：':'Bund series date:') && clock.includes('2026-04-08'));
        assert.ok(clock.includes(lang==='zh'?'各项利差观测日期不可用':'Individual spread observation dates unavailable'));
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'document must fit');
        const layout=await panel.evaluate(n=>({width:innerWidth,box:n.getBoundingClientRect().toJSON(),scroll:n.scrollWidth,client:n.clientWidth}));
        assert.ok(layout.scroll<=layout.client+1,JSON.stringify(layout));
      }
    },{htmlOverride:peripheryHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-euro-fragmentation'});
  });
}


// A mouse can stay on the sheet scrim while its trigger owns keyboard focus.
// Hover grace must not dismiss that reader's explanation.
for (const width of [320,1440]) test(`Focused LENS survives pointer exit and closes after focus leaves ${width}`,async()=>{
  const lensHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
    "from tests.test_intl_dollar_method_render import five_day_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(risk_desk=five_day_fixture()))"],
    {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
  await pageFixture(async page=>{
    await page.clock.install();
    const help=page.locator('#intl-dollar-conditions .help.help-upgraded');
    await help.focus();await help.press('Enter');
    await page.mouse.move(1,1);
    await page.clock.runFor(220); // exercise the real180ms hover-close deadline
    const pop=page.locator('#lensPop');
    assert.equal(await pop.evaluate(n=>n.classList.contains('open')),true,'focused explanation survives unrelated pointer movement');
    const close=pop.locator('.lens-x');await close.focus();
    await page.mouse.move(2,2);await page.clock.runFor(220);
    assert.equal(await pop.evaluate(n=>n.classList.contains('open')),true,'focus inside the explanation also retains it');
    await page.locator('[data-im-library-search]:visible').focus();
    await page.clock.runFor(220);
    assert.equal(await pop.evaluate(n=>n.classList.contains('open')),false,'leaving both trigger and explanation closes it');
    await help.focus();await help.press('Enter');await page.keyboard.press('Escape');
    assert.equal(await pop.evaluate(n=>n.classList.contains('open')),false,'explicit Escape still wins');
    await page.locator('[data-im-library-search]:visible').focus();
    await help.hover();await page.clock.runFor(120);
    assert.equal(await pop.evaluate(n=>n.classList.contains('open')),true,'pointer-only disclosure still opens');
    await page.mouse.move(1,1);await page.clock.runFor(220);
    assert.equal(await pop.evaluate(n=>n.classList.contains('open')),false,'pointer-only disclosure still closes');
    await help.focus();await help.press('Enter');await page.mouse.click(1,1);
    assert.equal(await pop.evaluate(n=>n.classList.contains('open')),false,'explicit outside click still wins');
  },{width,htmlOverride:lensHtml,initialSearch:'?view=library#intl-dollar-conditions'});
});

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Mobile LENS hides resting launcher and restores it ${theme} ${lang}`,async()=>{
    const lensHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      "from tests.test_intl_dollar_method_render import five_day_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(risk_desk=five_day_fixture()))"],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      const brainRequests=[];
      page.on('request',req=>{if(new URL(req.url()).pathname.endsWith('/mm_brain.js'))brainRequests.push(req.url());});
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      const boot=page.locator('#mmb-boot');assert.ok(await boot.isVisible(),'real resting launcher exists');
      for(const width of [320,390]) {
        await afterWindowEvent(page,'resize',()=>page.setViewportSize({width,height:900}));
        const help=page.locator('#intl-dollar-conditions .help.help-upgraded');
        await help.focus();await help.press('Enter');
        const lens=page.locator('.lens-pop.open');await lens.waitFor({state:'visible'});
        assert.ok(await page.evaluate(()=>document.documentElement.classList.contains('lens-lock')));
        assert.equal(await boot.isVisible(),false,'resting launcher must not cover the sheet');
        await lens.evaluate(n=>Promise.all(n.getAnimations({subtree:true}).map(a=>a.finished.catch(()=>{}))));
        const closeGeometry=await lens.evaluate(n=>{
          const close=n.querySelector('.lens-x').getBoundingClientRect(), overlaps=[];
          const body=n.querySelector('.lens-body'),walker=document.createTreeWalker(body,NodeFilter.SHOW_TEXT);
          while(walker.nextNode()){
            const node=walker.currentNode;if(!node.textContent.trim())continue;
            const range=document.createRange();range.selectNodeContents(node);
            for(const r of range.getClientRects())if(r.width && r.height && r.left<close.right && r.right>close.left && r.top<close.bottom && r.bottom>close.top) overlaps.push({text:node.textContent,box:r.toJSON()});
          }
          return {width:close.width,height:close.height,overlaps};
        });
        assert.deepEqual(closeGeometry.overlaps,[],'native close control must not cover body text');
        assert.ok(closeGeometry.width>=44 && closeGeometry.height>=44,'native close control has44px target');

        assert.ok((await lens.innerText()).includes(lang==='zh'?'分子不减均值':'without subtracting the mean'));
        await page.keyboard.press('Escape');await lens.waitFor({state:'hidden'});
        assert.ok(await boot.isVisible(),'launcher returns when the sheet closes');
        assert.ok(!(await page.evaluate(()=>document.documentElement.classList.contains('lens-lock'))));
      }
      assert.deepEqual(brainRequests,[],'reading the sheet must not activate the assistant');
      assert.equal(await page.locator('#mmb-root').count(),0);
    },{htmlOverride:lensHtml,published:true,bootLanguage:lang,width:390,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-dollar-conditions'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Funding header retains corridor and swap scope ${theme} ${lang}`,async()=>{
    const kind=theme==='dark'?'absent':'triggered';
    const fundingHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      `from tests.test_intl_dollar_funding_render import funding_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(risk_desk=funding_fixture('${kind}',1.2)))`],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const chip=page.locator('.ird-hchip').nth(3);
        assert.ok(await chip.isVisible(),'funding summary is rendered in the opened reference view');
        const text=await chip.innerText();
        assert.ok(text.includes(kind==='absent'?(lang==='zh'?'不可用':'Unavailable'):(lang==='zh'?'阈值已触发':'Threshold triggered')),JSON.stringify({kind,lang,text}));
        assert.ok(!/Calm|spreads normal|no funding stress|平静|息差正常/.test(text));
        assert.ok(text.includes(lang==='zh'?'12.0亿美元':'$1.2bn'));
        if(kind==='triggered'){
          assert.ok(text.includes('+2.0 bp'));
          assert.ok((await chip.getAttribute('class')).includes('state-caut'));
          assert.equal(await chip.locator('.hc-state').getAttribute('class'),'hc-state info');
        }
        assert.ok(await chip.evaluate(n=>n.scrollWidth<=n.clientWidth+1 && n.scrollHeight<=n.clientHeight+1),'funding header fits');
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:fundingHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-dollar-conditions'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Dollar five-day flag shows index points ${theme} ${lang}`,async()=>{
    const dollarHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      "from tests.test_intl_dollar_method_render import five_day_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(risk_desk=five_day_fixture()))"],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const tags=[page.locator('.ird-hchip').nth(2).locator('.ird-safety-tag'),page.locator('.ird-dollar-card .ird-safety-tag')];
        for(const tag of tags) {
          const text=await tag.innerText();
          assert.ok(text.includes(lang==='zh'?'+1.2点':'+1.2 pts') && !text.includes('1.2%'));
          assert.ok(text.includes(lang==='zh'?'5日标志':'Five-day flag'));
          assert.ok(!/today|今日/.test(text));
          assert.ok(await tag.evaluate(n=>n.scrollWidth<=n.clientWidth+1),'five-day tag fits');
        }
        assert.ok((await page.locator('.ird-dollar-card').innerText()).includes(lang==='zh'?'残差在区间内':'Within residual band'));
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:dollarHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-dollar-conditions'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Dollar method and build clock retain their scope ${theme} ${lang}`,async()=>{
    const dollarHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      "from tests.test_intl_dollar_method_render import method_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(risk_desk=method_fixture()))"],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const chip=page.locator('.ird-hchip').nth(2), card=page.locator('.ird-dollar-card');
        for(const el of [chip,card]) {
          const text=await el.innerText();
          assert.ok(text.includes(lang==='zh'?'残差在区间内':'Within residual band'));
          assert.ok(!/not fear|flight to safety|主因|避险资产被买入/.test(text));
          assert.ok(await el.evaluate(n=>n.scrollWidth<=n.clientWidth+1 && n.scrollHeight<=n.clientHeight+1),'model explanation fits');
        }
        const panel=page.locator('#intl-dollar-conditions').locator('xpath=ancestor::div[contains(concat(" ",normalize-space(@class)," ")," panel ")][1]');
        const clock=panel.locator('.ird-asof'), text=await clock.innerText();
        assert.ok(text.includes(lang==='zh'?'模型生成：':'Model built:'));
        assert.ok(text.includes('2026-10-12T04:05:06Z') && !text.includes('2026-10-14'));
        assert.ok(text.includes(lang==='zh'?'观测日：不可用':'Observation date: Unavailable'));
        assert.ok(await clock.evaluate(n=>n.scrollWidth<=n.clientWidth+1),'clock fits');
        const tip=await panel.locator('.tip').textContent();
        assert.ok(tip.includes('120-observation') && tip.includes('60-observation'));
        assert.ok(!tip.includes('Dual-window confirmed') && !tip.includes('DXY vs VIX'));
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:dollarHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-dollar-conditions'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Dollar unavailable owner never becomes a mixed read ${theme} ${lang}`,async()=>{
    const dollarHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      "from tests.test_intl_dollar_absence_render import dollar_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(risk_desk=dollar_fixture()))"],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const chip=page.locator('.ird-hchip').nth(2), card=page.locator('.ird-dollar-card');
        for(const el of [chip,card]) {
          const text=await el.innerText();
          assert.ok(text.includes(lang==='zh'?'不可用':'Unavailable'));
          assert.ok(!/Mixed picture|信号混合|tonight|今晚/.test(text));
          assert.ok(await el.evaluate(n=>n.scrollWidth<=n.clientWidth+1),'unavailable explanation fits');
        }
        assert.ok(!(await chip.getAttribute('class')).includes('state-ok'));
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:dollarHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-dollar-conditions'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Credit observation dates remain independent ${theme} ${lang}`,async()=>{
    const creditHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      "from tests.test_intl_credit_dates_render import credit_dates_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(risk_desk=credit_dates_fixture()))"],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const clocks=page.locator('[data-credit-observation]');
        assert.equal(await clocks.count(),4);
        const expected=['2026-10-13','2026-10-09','2026-09-30',lang==='zh'?'不可用':'Unavailable'];
        for(let i=0;i<4;i++) {
          const clock=clocks.nth(i),text=await clock.innerText();
          assert.ok(text.includes(expected[i]));
          assert.ok(text.includes(lang==='zh'?'观测日：':'Observed:'));
          for(let j=0;j<3;j++)if(i!==j)assert.ok(!text.includes(expected[j]));
          assert.ok(await clock.evaluate(n=>n.scrollWidth<=n.clientWidth+1 && n.scrollHeight<=n.clientHeight+1),'own clock fits its card');
        }
        assert.deepEqual(await page.locator('.ird-spread-card .sc-val').allInnerTexts(),['4.25%','1.75%','0.00%','2.50%']);
        const footer=page.locator('#intl-credit-bonds').locator('xpath=ancestor::div[contains(concat(" ",normalize-space(@class)," ")," panel ")][1]').locator('.ird-asof');
        assert.ok(!(await footer.innerText()).includes('2026-10-13'),'EM date must not masquerade as a shared clock');
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:creditHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-credit-bonds'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Credit standardized change never claims raw direction ${theme} ${lang}`,async()=>{
    const creditHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      "from tests.test_intl_credit_velocity_render import credit_velocity_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(risk_desk=credit_velocity_fixture()))"],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const labels=page.locator('.ird-spread-card .sc-vel');
        const expected=lang==='zh'?['20日变动高于常态','20日变动低于常态','20日变动接近常态','不可用']:['Above usual 20d change','Below usual 20d change','Near usual 20d change','Unavailable'];
        assert.deepEqual(await labels.allInnerTexts(),expected);
        for(const el of await labels.all()) {
          assert.equal(await el.getAttribute('class'),'sc-vel vel-flat');
          assert.ok(await el.evaluate(n=>n.scrollWidth<=n.clientWidth+1),'score meaning fits existing card');
        }
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    },{htmlOverride:creditHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-credit-bonds'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Credit absent observations stay unavailable on Library return ${theme} ${lang}`,async()=>{
    const creditHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      "from tests.test_intl_credit_absence_render import credit_absence_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(risk_desk=credit_absence_fixture()))"],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      const input=page.locator('[data-im-library-search]:visible');const query=lang==='zh'?'信用':'Credit';
      await input.fill(query);
      const link=page.locator('[data-im-library-tool="credit_bonds"] a[href="#intl-credit-bonds"]');
      assert.equal(await link.count(),1);const origin=page.url();
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});await link.focus();await page.keyboard.press('Enter');
        const heading=page.locator('#intl-credit-bonds');const panel=heading.locator('xpath=ancestor::div[contains(concat(" ",normalize-space(@class)," ")," panel ")][1]');
        const velocities=panel.locator('.sc-vel');const values=panel.locator('.sc-val');
        for(const index of [0,1,3])assert.equal(await velocities.nth(index).innerText(),lang==='zh'?'不可用':'Unavailable');
        assert.match(await velocities.nth(2).innerText(),lang==='zh'?/20日变动接近常态/:/Near usual 20d change/);
        assert.deepEqual(await values.allInnerTexts(),['0.00%','—','0.00%','1.25%']);
        const inversion=panel.locator('.ird-inv-row');assert.match(await inversion.innerText(),lang==='zh'?/不可用/:/Unavailable/);
        assert.equal(await inversion.locator('.inv-num').innerText(),'—');
        assert.equal(await heading.evaluate(n=>document.activeElement===n),true);
        for(const el of [...await velocities.all(),inversion])assert.ok(await el.evaluate(n=>n.scrollWidth<=n.clientWidth+1),'absence copy fits its container');
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
        await page.goBack();assert.equal(page.url(),origin);assert.equal(await input.inputValue(),query);
      }
    },{htmlOverride:creditHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Central bank clocks keep independent owner dates ${theme} ${lang}`,async()=>{
    const cbHtml=execFileSync(process.env.INTL_TEST_PYTHON || 'python3',['-c',
      "from tests.test_intl_central_bank_clocks_render import central_bank_clocks_fixture; from tests.test_intl_workspace_integration import render_fixture; print(render_fixture(risk_desk={'cb_desk':central_bank_clocks_fixture()}))"],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const dates=page.locator('[data-cb-rate-observation]');assert.equal(await dates.count(),3);
        assert.match(await dates.nth(0).innerText(),/2026-10-13/);
        assert.match(await dates.nth(1).innerText(),/2026-09-01/);
        assert.match(await dates.nth(2).innerText(),/2026-06-01/);
        assert.match(await dates.nth(0).innerText(),lang==='zh'?/日度/:/Daily/);
        assert.match(await dates.nth(1).innerText(),lang==='zh'?/月度/:/Monthly/);
        assert.match(await dates.nth(2).innerText(),lang==='zh'?/陈旧/:/Stale/);
        assert.ok(!(await dates.nth(0).innerText()).includes(lang==='zh'?'陈旧':'Stale'));
        const bs=page.locator('[data-cb-balance-observation]');assert.equal(await bs.count(),2);
        assert.match(await bs.nth(0).innerText(),/2026-10-07/);assert.match(await bs.nth(1).innerText(),/2026-09-30/);
        const region=page.locator('.ird-cb-scroll');
        for(const d of [...await dates.all(),...await bs.all()])assert.ok(await d.evaluate(n=>n.scrollWidth<=n.clientWidth+1 && n.scrollHeight<=n.clientHeight+1));
        assert.ok(await region.evaluate(n=>{const r=n.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1}));
        assert.equal(await page.locator('.ird-cb tbody tr').nth(2).locator('[data-cb-balance-observation]').count(),0,'no borrowed clock for missing balance sheet');
      }
    },{htmlOverride:cbHtml,published:true,bootLanguage:lang,
      initialSearch:'?view=library&market=JP&horizon=3m&basis=local&return_basis=price#intl-central-banks'});
  });
}

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
        assert.equal(await cells.nth(1).locator('b').innerText(),'0.00%');
        assert.equal(await cells.nth(2).innerText(),lang==='zh'?'不可用':'Unavailable');
        assert.equal(await cells.nth(4).locator(':scope > span').first().innerText(),lang==='zh'?'不可用':'Unavailable');
        const scroll=page.locator('.ird-cb').locator('..');
        console.log('Central-bank scroll semantics',await scroll.evaluate(n=>({role:n.getAttribute('role'),label:n.getAttribute('aria-labelledby'),tabindex:n.getAttribute('tabindex'),client:n.clientWidth,total:n.scrollWidth})));
        assert.equal(await scroll.getAttribute('role'),'region');
        assert.equal(await scroll.getAttribute('aria-labelledby'),'intl-central-banks');
        for(let i=0;i<5 && !(await scroll.evaluate(n=>document.activeElement===n));i++) await page.keyboard.press('Tab');
        assert.equal(await scroll.evaluate(n=>document.activeElement===n),true,'table scroller is reachable by native Tab');
        if(width===320) {
          assert.ok(await scroll.evaluate(n=>n.scrollWidth>n.clientWidth),'narrow table needs scrolling');
          // Let native smooth scrolling advance between real key events; never set scrollLeft.
          for(let i=0;i<40 && !(await scroll.evaluate(n=>n.scrollLeft>=n.scrollWidth-n.clientWidth-2));i++){await page.keyboard.press('ArrowRight');await page.waitForTimeout(50);}
          // Native smooth scrolling may still be moving inside the 2px distance
          // allowance. Wait for the actual 1px visibility contract below.
          await page.waitForFunction(()=>{
            const n=document.querySelector('.ird-cb tbody tr:first-child td:last-child');
            const r=n.getBoundingClientRect(),s=n.closest('.ird-cb-scroll').getBoundingClientRect();
            return r.right<=s.right+1 && r.left>=s.left-1;
          });
          assert.ok(await cells.nth(5).evaluate(n=>{const r=n.getBoundingClientRect(),s=n.closest('.ird-cb-scroll').getBoundingClientRect();return r.right<=s.right+1 && r.left>=s.left-1}),'last column is reachable');
          for(let i=0;i<40 && !(await scroll.evaluate(n=>n.scrollLeft<1));i++){await page.keyboard.press('ArrowLeft');await page.waitForTimeout(50);}
          console.log('Central-bank keyboard return',await scroll.evaluate(n=>({left:n.scrollLeft,max:n.scrollWidth-n.clientWidth,focused:n===document.activeElement})));
          await page.waitForFunction(()=>document.querySelector('.ird-cb-scroll').scrollLeft<1);
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
        await afterWindowEvent(page,'resize',()=>page.setViewportSize({width,height:900}));
        await link.focus();await afterWindowEvent(page,'hashchange',()=>page.keyboard.press('Enter'));
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
        assert.match(text,lang==='zh'?/已报告数据缺口：1/:/Reported data gaps: 1/);
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
