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
const omittedGroupHtml = new Map();
for(const [lang,width,theme] of [['en',1440,'dark'],['zh',320,'light']]) {
  for(const allOmitted of [false,true]) {
    test(`Library omitted groups retain readable fallback ${lang} ${width} all=${allOmitted}`,async()=>{
      if(!omittedGroupHtml.has(allOmitted)) omittedGroupHtml.set(allOmitted,
        execFileSync(process.env.INTL_TEST_PYTHON||'python3',['-c',
          `from tests.test_intl_workspace_library_render import render_omitted_group_page; print(render_omitted_group_page(${allOmitted?'True':'False'}))`],
          {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:8*1024*1024}));
      await pageFixture(async page=>{
        await page.waitForSelector('[data-im-enhanced="true"]');
        await page.evaluate(theme=>setTheme(theme),theme);
        const panel=page.locator('[data-im-panel][data-view="library"]:visible');
        const placeholders=panel.locator('[data-im-library-group-unavailable]');
        assert.equal(await placeholders.count(),allOmitted?6:1);
        assert.equal(await panel.locator('[data-im-library-search]').isDisabled(),true);
        assert.equal(await panel.locator('[data-im-library-group-open]:visible').count(),0);
        assert.equal(await panel.locator('[data-im-library-tool]').count(),allOmitted?0:15);
        assert.equal(await panel.locator('[data-im-library-group=""], [data-im-group=""]').count(),0);
        const before=page.url();
        for(const locale of [lang,lang==='en'?'zh':'en']) {
          await page.evaluate(locale=>setLang(locale),locale);
          assert.deepEqual(await placeholders.allInnerTexts(),Array(allOmitted?6:1).fill(
            locale==='en'?'Tool group unavailable for this view.':'此视图的工具分组暂不可用。'));
          assert.equal(await panel.locator('h3').evaluateAll(ns=>ns.every(n=>n.innerText.trim())),true);
          assert.equal(await placeholders.evaluateAll(ns=>ns.every(n=>n.scrollWidth<=n.clientWidth+1)),true);
          assert.equal(page.url(),before);
        }
        assert.doesNotMatch(await panel.innerText(),/Performance & currency|表现与汇率|Find the leaders|寻找领涨者/);
        if(!allOmitted) {
          const link=panel.locator('[data-im-library-tool="country_sectors_stocks"] a');
          await link.focus();
          assert.equal(await link.evaluate(n=>n===document.activeElement),true);
          assert.equal(await link.getAttribute('href'),'/intl_stocks.html');
        }
      },{htmlOverride:omittedGroupHtml.get(allOmitted),bootLanguage:lang,width,initialSearch:'?view=library'});
    });
  }
}
let sourceReferenceHtml;
for(const [lang,width,theme] of [['en',1440,'dark'],['zh',320,'light']]) {
  test(`Macro absent source reference stays readable through locale and keyboard ${lang} ${width}`,async()=>{
    sourceReferenceHtml ||= execFileSync(process.env.INTL_TEST_PYTHON||'python3',['-c',
      'from tests.test_intl_workspace_macro_render import render_source_reference_page; print(render_source_reference_page())'],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:8*1024*1024});
    await pageFixture(async page=>{
      await page.waitForSelector('[data-im-enhanced="true"]');
      await page.evaluate(theme=>setTheme(theme),theme);
      const panel=page.locator('[data-im-panel][data-view="macro"]:visible');
      const slot=panel.locator('[data-im-macro-market="EZ"] .intl-macro__metric-slot[id$="-gdp_yoy"]');
      const disclosure=slot.locator('.intl-macro__evidence');
      const summary=disclosure.locator(':scope > summary');
      await summary.focus();await page.keyboard.press('Enter');
      assert.equal(await disclosure.getAttribute('open'),'');
      const reference=disclosure.locator('.intl-macro__source-reference');
      await page.keyboard.press('Tab');
      assert.equal(await reference.evaluate(n=>n===document.activeElement),true);
      const before=page.url();
      for(const locale of [lang,lang==='en'?'zh':'en',lang]) {
        await page.evaluate(locale=>setLang(locale),locale);
        assert.equal(await reference.innerText(),locale==='en'?'Not supplied':'未提供');
        assert.equal(await reference.evaluate(n=>n===document.activeElement),true);
        assert.equal(await reference.locator('a').count(),0);
        assert.equal(await slot.locator('[data-im-macro-value]').innerText(),'0');
        assert.equal(await slot.locator('.intl-macro__observation').innerText(),'2026-09-10');
        assert.match(await slot.innerText(),locale==='en'?/Stale data/:/数据过期/);
        assert.match(await disclosure.innerText(),/synthetic:gdp-zero/);
        assert.equal(page.url(),before);
        assert.equal(await reference.evaluate(n=>n.scrollWidth<=n.clientWidth+1),true);
      }
      await page.keyboard.press('Shift+Tab');await page.keyboard.press('Space');
      assert.equal(await disclosure.getAttribute('open'),null);
    },{htmlOverride:sourceReferenceHtml,bootLanguage:lang,width,initialSearch:'?view=macro'});
  });
}
let cycleLabelHtml;
for(const [lang,width,theme] of [['en',1440,'dark'],['zh',320,'light']]) {
  test(`Macro admitted cycle names follow locale ${lang} ${width}`,async()=>{
    cycleLabelHtml ||= execFileSync(process.env.INTL_TEST_PYTHON||'python3',['-c',
      'from tests.test_intl_workspace_macro_render import render_cycle_label_page; print(render_cycle_label_page())'],
      {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:8*1024*1024});
    await pageFixture(async page=>{
      await page.waitForSelector('[data-im-enhanced="true"]');
      await page.evaluate(theme=>setTheme(theme),theme);
      const panel=page.locator('[data-im-panel][data-view="macro"]:visible');
      const disclosure=panel.locator('.intl-macro__composite');
      const summary=disclosure.locator(':scope > summary');
      await summary.focus();await page.keyboard.press('Enter');
      assert.equal(await disclosure.getAttribute('open'),'');
      const headings=disclosure.locator(':scope > section > p:first-of-type');
      const expected={en:['Goldilocks','Reflation','Stagflation','Growth-scare'],zh:['金发女孩','再通胀','滞胀','增长恐慌']};
      const before=page.url();
      for(const locale of [lang,lang==='en'?'zh':'en',lang]) {
        await page.evaluate(locale=>setLang(locale),locale);
        assert.deepEqual(await headings.allInnerTexts(),expected[locale]);
        assert.equal(await summary.evaluate(n=>n===document.activeElement),true);
        assert.equal(page.url(),before);
        assert.equal(await headings.evaluateAll(nodes=>nodes.every(n=>n.scrollWidth<=n.clientWidth+1)),true);
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
      }
      assert.match(await disclosure.innerText(),/owner\/economic-cycle@1/);
      await page.keyboard.press('Space');
      assert.equal(await disclosure.getAttribute('open'),null);
    },{htmlOverride:cycleLabelHtml,bootLanguage:lang,width,initialSearch:'?view=macro'});
  });
}
let historyEventFixture;
function historyEventDisclosureFixture() {
  if(!historyEventFixture) historyEventFixture=JSON.parse(execFileSync(process.env.INTL_TEST_PYTHON||'python3',['-c',`
import json
from engine.intl_inputs import countries
from tests.test_intl_workspace_history_render import EVENT_CASES, event_source
from tests.test_intl_workspace_integration import render_history_fixture
cases = [dict(market=market, kind=kind, expected=EVENT_CASES[kind])
         for market, kind in zip(countries(), EVENT_CASES)]
assert len(cases) == len(EVENT_CASES)
sources = {case['market']: event_source(case['kind'], case['market']) for case in cases}
print(json.dumps(dict(html=render_history_fixture(history_sources=sources), cases=cases)))
`],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:8*1024*1024}));
  return historyEventFixture;
}

for(const theme of ['dark','light']) for(const lang of ['en','zh']) {
  test(`History attached-change disclosures preserve their source states ${theme} ${lang}`,async()=>{
    const fixture=historyEventDisclosureFixture();
    await pageFixture(async page=>{
      await page.evaluate(theme=>setTheme(theme),theme);
      await page.waitForSelector('[data-im-enhanced="true"]');
      await page.locator('.sky-fx').waitFor({state:'detached'});
      const panel=page.locator('[data-im-history-panel]');
      const picker=panel.locator('select[data-im-action="select_market"]');
      for(const {market,kind,expected} of fixture.cases) {
        await picker.selectOption(market);
        const article=panel.locator(`[data-im-history-market="${market}"]`);
        assert.equal(await article.isVisible(),true);
        const heading=article.locator('h4').filter({hasText:'Attached changes'});
        const state=heading.locator('xpath=following-sibling::*[1]');
        const text=await state.innerText();
        assert.ok(text.includes(expected[lang==='en'?0:1]),JSON.stringify({market,kind,lang,text}));
        assert.equal(/No qualified changes supplied|此市场尚未提供符合条件的变化记录/.test(text),kind==='empty');
        assert.equal(await article.locator('.intl-history__timeline').count(),kind==='available'?1:0);
        assert.equal(await article.locator('time').count(),kind==='available'?1:0);
        if(kind!=='available') assert.doesNotMatch(await article.textContent(),/MA turn|均线转折|record.turn.events:0/);
        assert.equal(await article.locator('[data-im-history-status]').innerText(),lang==='en'?'Recomputed observations':'重新计算的观测');
        assert.match((await article.locator('tbody th').allTextContents()).join(' '),/2026-01-03T00:00:00\.123456789\+09:00/);
        for(const width of [320,1440]) {
          await page.setViewportSize({width,height:900});
          assert.equal(await state.evaluate(n=>n.scrollWidth<=n.clientWidth+1),true,`${kind} ${lang} ${width}`);
          assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
          if(width===320&&kind==='metadata_denied'&&process.env.INTL_BROWSER_EVIDENCE_DIR) {
            fs.mkdirSync(process.env.INTL_BROWSER_EVIDENCE_DIR,{recursive:true});
            await page.evaluate(()=>document.fonts.ready);
            await article.evaluate(n=>n.scrollIntoView({block:'center',behavior:'instant'}));
            await article.screenshot({path:path.join(process.env.INTL_BROWSER_EVIDENCE_DIR,`history-event-disclosure-${theme}-${lang}-320.png`)});
          }
        }
      }
    },{htmlOverride:fixture.html,width:320,bootLanguage:lang,initialSearch:'?view=history'});
  });
}

let staleMacroComponentHtml;
let historyTrackFixture;
function historyForwardRecordFixture() {
  if(!historyTrackFixture) historyTrackFixture=JSON.parse(execFileSync(process.env.INTL_TEST_PYTHON||'python3',['-c',`
import json
from engine.intl_inputs import countries
from tests.test_intl_workspace_history_render import TRACK_CASES, track_source
from tests.test_intl_workspace_integration import render_history_fixture
kinds = ['available','metadata_denied','value_unknown','not_supplied','wrong_market','failed','zero']
cases = [dict(market=market, kind=kind, expected=TRACK_CASES[kind]) for market, kind in zip(countries(), kinds)]
assert len(cases) == len(kinds)
sources = {case['market']: track_source(case['kind'], case['market']) for case in cases}
print(json.dumps(dict(html=render_history_fixture(history_sources=sources), cases=cases)))
`],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:8*1024*1024}));
  return historyTrackFixture;
}

for(const theme of ['dark','light']) for(const lang of ['en','zh']) {
  test(`History forward record keeps disclosure and zero counts distinct ${theme} ${lang}`,async()=>{
    const fixture=historyForwardRecordFixture();
    await pageFixture(async page=>{
      await page.evaluate(theme=>setTheme(theme),theme);
      await page.waitForSelector('[data-im-enhanced="true"]');
      await page.locator('.sky-fx').waitFor({state:'detached'});
      const panel=page.locator('[data-im-history-panel]');
      const picker=panel.locator('select[data-im-action="select_market"]');
      for(const {market,kind,expected} of fixture.cases) {
        await picker.selectOption(market);
        const article=panel.locator(`[data-im-history-market="${market}"]`);
        const track=article.locator('.intl-history__track');
        assert.equal(await track.isVisible(),true);
        const text=await track.innerText();
        assert.ok(text.includes(expected[lang==='en'?0:1]),JSON.stringify({market,kind,lang,text}));
        const available=['available','zero'].includes(kind);
        assert.deepEqual(await track.locator('dd').allTextContents(),available?(kind==='zero'?['0','0']:['4','1']):[]);
        assert.equal(text.includes('2026-01-15'),available);
        assert.equal(text.includes('forward_log independent read'),available);
        assert.equal(/A failed read|读取失败/.test(text),kind==='failed');
        assert.equal(await article.locator('.intl-history__timeline').count(),1);
        assert.equal(await article.locator('[data-im-history-status]').innerText(),lang==='en'?'Recomputed observations':'重新计算的观测');
        for(const width of [320,1440]) {
          await page.setViewportSize({width,height:900});
          assert.equal(await track.evaluate(n=>n.scrollWidth<=n.clientWidth+1),true,`${kind} ${lang} ${width}`);
          assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
          if(width===320&&kind==='metadata_denied'&&process.env.INTL_BROWSER_EVIDENCE_DIR) {
            fs.mkdirSync(process.env.INTL_BROWSER_EVIDENCE_DIR,{recursive:true});
            await page.evaluate(()=>document.fonts.ready);
            await track.evaluate(n=>n.scrollIntoView({block:'center',behavior:'instant'}));
            await track.screenshot({path:path.join(process.env.INTL_BROWSER_EVIDENCE_DIR,`history-forward-record-${theme}-${lang}-320.png`)});
          }
        }
      }
    },{htmlOverride:fixture.html,width:320,bootLanguage:lang,initialSearch:'?view=history'});
  });
}

let historySnapshotFixture;
function historySnapshotComparisonFixture() {
  if(!historySnapshotFixture) historySnapshotFixture=JSON.parse(execFileSync(process.env.INTL_TEST_PYTHON||'python3',['-c',`
import json
from engine.intl_inputs import countries
from tests.test_intl_workspace_history_render import snapshot_source, SNAPSHOT_ELIGIBLE
from tests.test_intl_workspace_integration import render_history_fixture
kinds = ['zero','reversed','metadata_denied','value_unknown','incomplete_identity','null_score','not_requested']
sources, cases = {}, []
for market, kind in zip(countries(), kinds):
    source = snapshot_source(kind, market)
    sources[market] = source
    query = source['capabilities']['snapshot_compare']
    rows = [next(p for p in source['history_read']['points'] if p['observation_at'] == query[key])
            for key in ('left_observation_at','right_observation_at')] if kind in SNAPSHOT_ELIGIBLE else []
    cases.append(dict(market=market, kind=kind, rows=rows))
assert len(cases) == len(kinds)
print(json.dumps(dict(html=render_history_fixture(history_sources=sources), cases=cases)))
`],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:8*1024*1024}));
  return historySnapshotFixture;
}

for(const theme of ['dark','light']) for(const lang of ['en','zh']) {
  test(`History supplied snapshot comparison preserves eligibility and keyboard access ${theme} ${lang}`,async()=>{
    const fixture=historySnapshotComparisonFixture();
    await pageFixture(async page=>{
      await page.evaluate(theme=>setTheme(theme),theme);
      await page.waitForSelector('[data-im-enhanced="true"]');
      await page.locator('.sky-fx').waitFor({state:'detached'});
      const panel=page.locator('[data-im-history-panel]');
      const picker=panel.locator('select[data-im-action="select_market"]');
      for(const {market,kind,rows} of fixture.cases) {
        await picker.selectOption(market);
        const article=panel.locator(`[data-im-history-market="${market}"]`);
        assert.equal(await article.isVisible(),true);
        const comparison=article.locator('.intl-history__snapshot');
        assert.equal(await comparison.count(),rows.length?1:0,kind);
        if(!rows.length) continue;
        const summary=comparison.locator('summary');
        assert.equal(await summary.innerText(),lang==='en'?'Compare two supplied observations':'比较两条已提供的观测');
        await article.locator('.intl-history__observations > summary').focus();
        await page.keyboard.press('Tab');
        assert.equal(await summary.evaluate(n=>n===document.activeElement),true);
        await page.keyboard.press('Enter');
        assert.equal(await comparison.getAttribute('open'),'');
        assert.deepEqual(await comparison.locator('dt').allTextContents(),rows.map(p=>p.observation_at));
        assert.deepEqual(await comparison.locator('[data-im-snapshot-growth]').allTextContents(),rows.map(p=>String(p.growth_score)));
        assert.deepEqual(await comparison.locator('[data-im-snapshot-inflation]').allTextContents(),rows.map(p=>String(p.inflation_score)));
        const text=await comparison.innerText();
        assert.ok(text.includes(lang==='en'?'not what was known at the time':'不代表当时已知的信息'));
        assert.ok(text.includes(lang==='en'?'Growth score':'增长评分'));
        for(const width of [320,1440]) {
          await page.setViewportSize({width,height:900});
          const overflow=await comparison.locator('summary,p,dt,dd').evaluateAll(ns=>ns.filter(n=>n.scrollWidth>n.clientWidth+1).map(n=>n.innerText));
          assert.deepEqual(overflow,[],`${kind} ${theme} ${lang} ${width}`);
          assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
          if(width===320&&kind==='zero'&&process.env.INTL_BROWSER_EVIDENCE_DIR) {
            fs.mkdirSync(process.env.INTL_BROWSER_EVIDENCE_DIR,{recursive:true});
            await page.evaluate(()=>document.fonts.ready);
            await comparison.evaluate(n=>n.scrollIntoView({block:'center',behavior:'instant'}));
            await comparison.screenshot({path:path.join(process.env.INTL_BROWSER_EVIDENCE_DIR,`history-snapshot-${theme}-${lang}-320.png`)});
          }
        }
        await summary.focus();
        await page.keyboard.press('Space');
        assert.equal(await comparison.getAttribute('open'),null);
        await page.keyboard.press('Tab');
        assert.equal(await article.locator('.intl-history__evidence > summary').evaluate(n=>n===document.activeElement),true);
      }
    },{htmlOverride:fixture.html,width:320,bootLanguage:lang,initialSearch:'?view=history'});
  });
}

let riskBreadthClockFixture;
function riskBreadthClocksFixture() {
  if(!riskBreadthClockFixture) riskBreadthClockFixture=JSON.parse(execFileSync(process.env.INTL_TEST_PYTHON||'python3',['-c',
    'import json; from tests.test_intl_workspace_risk_render import render_breadth_clock_fixture; print(json.dumps(render_breadth_clock_fixture()))'],
    {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:8*1024*1024}));
  return riskBreadthClockFixture;
}

for(const theme of ['dark','light']) for(const lang of ['en','zh']) {
  test(`Risk breadth retains independent observation and membership clocks ${theme} ${lang}`,async()=>{
    const fixture=riskBreadthClocksFixture();
    await pageFixture(async page=>{
      await page.evaluate(theme=>setTheme(theme),theme);
      await page.waitForSelector('[data-im-enhanced="true"]');
      await page.locator('.sky-fx').waitFor({state:'detached'});
      const controls=page.locator('[data-im-controls]');
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        for(const horizon of ['1m','3m']) {
          await controls.locator('select[data-im-action="set_horizon"]').selectOption(horizon);
          const panel=page.locator('[data-im-panel][data-view="risk"]:visible');
          for(const {market,kind} of fixture.cases) {
            const cell=panel.locator(`[data-im-risk-row="${market}"] td:last-child`);
            assert.equal(await cell.isVisible(),true);
            const observation=cell.locator('[data-im-breadth-observation]');
            const membership=cell.locator('[data-im-breadth-membership]');
            const supported=['distinct','zero','stale'].includes(kind);
            assert.equal(await observation.count(),supported||kind==='value_denied'?1:0);
            assert.equal(await membership.count(),supported?1:0);
            if(supported||kind==='value_denied') assert.equal(await observation.innerText(),lang==='en'?'Observation 2026-10-05':'观测 2026-10-05');
            if(supported) {
              assert.equal(await membership.innerText(),lang==='en'?'Membership as of 2026-09-30':'成员名单截至日期 2026-09-30');
              assert.equal(await cell.locator('[data-im-risk-value]').innerText(),kind==='zero'?'0':'+61');
              const valueBox=await cell.locator('[data-im-risk-value]').boundingBox();
              const observationBox=await observation.boundingBox(),membershipBox=await membership.boundingBox();
              assert.ok(observationBox.y>=valueBox.y+valueBox.height-1,'observation date must be separate from value/count');
              assert.ok(membershipBox.y>=observationBox.y+observationBox.height-1,'membership date must have its own readable line');
              assert.equal((await cell.innerText()).includes(lang==='en'?'Stale data':'数据过期'),kind==='stale');
            } else assert.equal(await cell.locator('[data-im-risk-value]').count(),0);
            assert.doesNotMatch(await cell.innerText(),/2026-10-06|2026-10-07/);
            assert.equal(await cell.evaluate(n=>n.scrollWidth<=n.clientWidth+1),true,`${kind} ${width} ${lang}`);
            if(width===320&&horizon==='1m'&&kind==='distinct'&&process.env.INTL_BROWSER_EVIDENCE_DIR) {
              fs.mkdirSync(process.env.INTL_BROWSER_EVIDENCE_DIR,{recursive:true});
              await page.evaluate(()=>document.fonts.ready);
              await cell.evaluate(n=>n.scrollIntoView({block:'center',behavior:'instant'}));
              await cell.screenshot({path:path.join(process.env.INTL_BROWSER_EVIDENCE_DIR,`risk-breadth-clocks-${theme}-${lang}-320.png`)});
            }
          }
          assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
        }
      }
    },{htmlOverride:fixture.html,width:320,bootLanguage:lang,initialSearch:'?view=risk'});
  });
}

let riskAnnualClockFixture;
function riskAnnualClocksFixture() {
  if(!riskAnnualClockFixture) riskAnnualClockFixture=JSON.parse(execFileSync(process.env.INTL_TEST_PYTHON||'python3',['-c',
    'import json; from tests.test_intl_workspace_risk_render import render_annual_clock_fixture; print(json.dumps(render_annual_clock_fixture()))'],
    {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:8*1024*1024}));
  return riskAnnualClockFixture;
}

for(const theme of ['dark','light']) for(const lang of ['en','zh']) {
  test(`Risk annual clocks keep vintage and observation types separate ${theme} ${lang}`,async()=>{
    const fixture=riskAnnualClocksFixture();
    await pageFixture(async page=>{
      await page.evaluate(theme=>setTheme(theme),theme);
      await page.waitForSelector('[data-im-enhanced="true"]');
      await page.locator('.sky-fx').waitFor({state:'detached'});
      const controls=page.locator('[data-im-controls]');
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        for(const [horizon,basis] of [['1m','usd_unhedged'],['3m','local']]) {
          await controls.locator('select[data-im-action="set_horizon"]').selectOption(horizon);
          await controls.locator('select[data-im-action="set_basis"]').selectOption(basis);
          const panel=page.locator('[data-im-panel][data-view="risk"]:visible');
          for(const {market,kind} of fixture.cases) {
            const cell=panel.locator(`[data-im-risk-row="${market}"] td:nth-of-type(3)`);
            assert.equal(await cell.isVisible(),true);
            const observation=cell.locator('[data-im-annual-observation]');
            const calculation=cell.locator('[data-im-annual-calculation]');
            const metadata=kind!=='metadata_denied';
            const supported=metadata&&!['value_denied','missing_observation'].includes(kind);
            assert.equal(await observation.count(),metadata&&kind!=='missing_observation'?1:0);
            assert.equal(await calculation.count(),metadata&&kind!=='no_calculation'?1:0);
            if(await observation.count()) assert.equal(await observation.innerText(),lang==='en'?'Observation 2026-08-21':'观测 2026-08-21');
            if(await calculation.count()) assert.equal(await calculation.innerText(),(lang==='en'?'Calculation time':'计算时间')+' 2026-08-22T05:00:00+00:00');
            const text=await cell.innerText();
            if(supported) {
              assert.ok(text.includes((lang==='en'?'Field year':'字段年份')+' '+(kind==='projection'?'2027':'2024')));
              assert.ok(text.includes((lang==='en'?'Vintage':'版本')+' 2026-07-30'));
              const type=kind==='projection'?(lang==='en'?'Projection':'预测'):(lang==='en'?'Actual':'实际');
              assert.ok(text.split('\n').includes(type));
              assert.equal(await cell.locator('[data-im-risk-value]').innerText(),kind==='stale'?'-1.25':'+3.4');
              assert.equal(text.includes(lang==='en'?'Stale data':'数据过期'),kind==='stale');
            } else {
              assert.equal(await cell.locator('[data-im-risk-value]').count(),0);
              assert.doesNotMatch(text,/2026-07-30/);
            }
            if(kind==='missing_observation') assert.ok(text.includes(lang==='en'?'Missing data':'数据缺失'));
            const lines=await cell.locator('p').evaluateAll(ns=>ns.map(n=>{const r=n.getBoundingClientRect();return {top:r.top,bottom:r.bottom,width:n.clientWidth,scroll:n.scrollWidth};}));
            assert.ok(lines.every((r,i)=>r.scroll<=r.width+1&&(!i||r.top>=lines[i-1].bottom-1)),`${kind} ${lang} ${width}`);
            assert.equal(await cell.evaluate(n=>n.scrollWidth<=n.clientWidth+1),true);
            if(width===320&&horizon==='1m'&&kind==='projection'&&process.env.INTL_BROWSER_EVIDENCE_DIR) {
              fs.mkdirSync(process.env.INTL_BROWSER_EVIDENCE_DIR,{recursive:true});
              await page.evaluate(()=>document.fonts.ready);
              await cell.evaluate(n=>n.scrollIntoView({block:'center',behavior:'instant'}));
              await cell.screenshot({path:path.join(process.env.INTL_BROWSER_EVIDENCE_DIR,`risk-annual-clocks-${theme}-${lang}-320.png`)});
            }
          }
          assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
        }
      }
    },{htmlOverride:fixture.html,width:320,bootLanguage:lang,initialSearch:'?view=risk'});
  });
}

let riskPressureEvidenceFixture;
function riskPressureReferencesFixture() {
  if(!riskPressureEvidenceFixture) riskPressureEvidenceFixture=JSON.parse(execFileSync(process.env.INTL_TEST_PYTHON||'python3',['-c',
    'import json; from tests.test_intl_workspace_risk_render import render_pressure_evidence_fixture; print(json.dumps(render_pressure_evidence_fixture()))'],
    {cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:8*1024*1024}));
  return riskPressureEvidenceFixture;
}

for(const theme of ['dark','light']) for(const lang of ['en','zh']) {
  test(`Risk pressure evidence follows native disclosure and keyboard context ${theme} ${lang}`,async()=>{
    const fixture=riskPressureReferencesFixture();
    const labels=lang==='en'?['Credit evidence','Current account evidence','Breadth evidence']:['信用依据','经常账户依据','广度依据'];
    await pageFixture(async page=>{
      await page.evaluate(theme=>setTheme(theme),theme);
      await page.waitForSelector('[data-im-enhanced="true"]');
      await page.locator('.sky-fx').waitFor({state:'detached'});
      const controls=page.locator('[data-im-controls]');
      for(const [width,horizon,basis] of [[320,'1m','usd_unhedged'],[1440,'3m','local']]) {
        await page.setViewportSize({width,height:900});
        await controls.locator('select[data-im-action="set_horizon"]').selectOption(horizon);
        await controls.locator('select[data-im-action="set_basis"]').selectOption(basis);
        const panel=page.locator('[data-im-panel][data-view="risk"]:visible');
        const url=page.url();
        for(const {market,kind} of fixture.cases) {
          const row=panel.locator(`[data-im-risk-row="${market}"]`);
          const visible=['supplied','stale','value_denied','source_only'].includes(kind);
          const supported=['supplied','stale'].includes(kind);
          for(const [i,field] of fixture.fields.entries()) {
            const cell=row.locator(`td:nth-of-type(${i+2})`);
            const evidence=cell.locator('details.intl-risk__evidence');
            assert.equal(await evidence.count(),visible?1:0,`${kind} ${field}`);
            if(!visible) {
              assert.doesNotMatch(await cell.textContent(),/source:|evidence:|method:|public-members/);
              continue;
            }
            const summary=evidence.locator('summary');
            assert.equal(await summary.innerText(),labels[i]);
            assert.equal(await evidence.evaluate(n=>n.open),false);
            await summary.focus();
            await page.keyboard.press('Enter');
            assert.equal(await evidence.evaluate(n=>n.open),true);
            const refs=await evidence.locator('dd').allTextContents();
            const expected=[`source:${market}:${field}:`+'x'.repeat(96)];
            if(kind!=='source_only') expected.push(`evidence:${market}:${field}`);
            if(supported) expected.push(`method:${market}:${field}`);
            if(supported&&field==='constituent_breadth_50d') expected.push('public-members');
            assert.deepEqual(refs,expected);
            assert.equal(await evidence.locator('a').count(),0,'references do not invent destinations');
            const terms=await evidence.locator('dt').allInnerTexts();
            assert.equal(terms[0],lang==='en'?'Source reference':'来源引用');
            if(supported) assert.equal(await cell.locator('[data-im-risk-value]').innerText(),['0','+3.4','+61'][i]);
            else assert.equal(await cell.locator('[data-im-risk-value]').count(),0);
            assert.equal(await cell.evaluate(n=>n.scrollWidth<=n.clientWidth+1),true,`${field} ${lang} ${width}`);
            assert.equal(await evidence.locator('dd').evaluateAll(ns=>ns.every(n=>n.scrollWidth<=n.clientWidth+1)),true);
            if(width===320&&kind==='supplied'&&i===0&&process.env.INTL_BROWSER_EVIDENCE_DIR) {
              fs.mkdirSync(process.env.INTL_BROWSER_EVIDENCE_DIR,{recursive:true});
              await page.evaluate(()=>document.fonts.ready);
              await cell.evaluate(n=>n.scrollIntoView({block:'center',behavior:'instant'}));
              await cell.screenshot({path:path.join(process.env.INTL_BROWSER_EVIDENCE_DIR,`risk-pressure-evidence-${theme}-${lang}-320.png`)});
            }
            await summary.focus();
            await page.keyboard.press('Space');
            assert.equal(await evidence.evaluate(n=>n.open),false);
            if(i<2) {
              await page.keyboard.press('Tab');
              assert.equal(await row.locator(`td:nth-of-type(${i+3}) summary`).evaluate(n=>n===document.activeElement),true);
            }
          }
        }
        assert.equal(page.url(),url,'disclosures must not change navigation context');
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
      }
    },{htmlOverride:fixture.html,width:320,bootLanguage:lang,initialSearch:'?view=risk'});
  });
}

function staleMacroComponentFixture() {
  if (!staleMacroComponentHtml) staleMacroComponentHtml=execFileSync(process.env.INTL_TEST_PYTHON||'python3',['-c',`
from tests.test_intl_workspace_macro_render import component_workspace_fixture
print(component_workspace_fixture(missing_components=True))
`],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024});
  return staleMacroComponentHtml;
}

for(const theme of ['dark','light']) for(const lang of ['en','zh']) {
  test(`Macro stale missing components remain readable ${theme} ${lang}`,async()=>{
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      await page.waitForSelector('[data-im-enhanced="true"]');
      await page.locator('.sky-fx').waitFor({state:'detached'});
      const panel=page.locator('[data-view="macro"]:not([hidden])');
      const composite=panel.locator('.intl-macro__composite');
      const summary=composite.locator(':scope > summary');
      await summary.focus();await summary.press('Enter');
      assert.equal(await composite.evaluate(n=>n.open),true);
      const text=await composite.innerText();
      assert.match(text,lang==='zh'?/未提供分项依据。/:/Component evidence not supplied\./);
      assert.match(text,lang==='zh'?/数据过期/:/Stale data/);
      assert.match(text,lang==='zh'?/未提供方法/:/Method not supplied/);
      assert.doesNotMatch(text,/None|2026-09-10|Goldilocks|Q1/);
      assert.equal(await panel.locator('.intl-macro__table').isVisible(),true);
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        assert.equal(await composite.evaluate(n=>n.scrollWidth<=n.clientWidth+1),true);
        if(process.env.INTL_BROWSER_EVIDENCE_DIR) {
          fs.mkdirSync(process.env.INTL_BROWSER_EVIDENCE_DIR,{recursive:true});
          await page.evaluate(()=>document.fonts.ready);
          await composite.evaluate(n=>n.scrollIntoView({block:'center',behavior:'instant'}));
          await composite.screenshot({path:path.join(process.env.INTL_BROWSER_EVIDENCE_DIR,`macro-components-absent-integrated-${theme}-${lang}-${width}.png`)});
        }
      }
      await summary.focus();await summary.press('Enter');
      assert.equal(await composite.evaluate(n=>n.open),false);
    },{htmlOverride:staleMacroComponentFixture(),width:320,bootLanguage:lang,initialSearch:'?view=macro'});
  });
}

const macroComponentValuesHtml=new Map();
function macroComponentValuesFixture(emptyAxis=false) {
  if(!macroComponentValuesHtml.has(emptyAxis)) macroComponentValuesHtml.set(emptyAxis,execFileSync(process.env.INTL_TEST_PYTHON||'python3',['-c',`
from tests.test_intl_workspace_macro_render import component_workspace_fixture
print(component_workspace_fixture(empty_axes=${emptyAxis ? '("growth",)' : '()'}))
`],{cwd:root,env:{...process.env,PYTHONPATH:root},encoding:'utf8',maxBuffer:4*1024*1024}));
  return macroComponentValuesHtml.get(emptyAxis);
}

for(const emptyAxis of [false,true]) for(const theme of ['dark','light']) for(const lang of ['en','zh']) {
  test(`Macro ${emptyAxis?'empty component axis preserves its supplied neighbor':'component readings distinguish absent and zero'} ${theme} ${lang}`,async()=>{
    await pageFixture(async page=>{
      await page.evaluate(({theme,lang})=>{setTheme(theme);setLang(lang);},{theme,lang});
      await page.waitForSelector('[data-im-enhanced="true"]');
      await page.locator('.sky-fx').waitFor({state:'detached'});
      const panel=page.locator('[data-view="macro"]:not([hidden])');
      const composite=panel.locator('.intl-macro__composite');
      const summary=composite.locator(':scope > summary');
      await summary.focus();await summary.press('Enter');
      assert.equal(await composite.evaluate(n=>n.open),true);
      const readings=composite.locator('dd');
      const missing=await readings.nth(0).innerText();
      if(emptyAxis) {
        assert.equal(missing,lang==='zh'?'未提供分项。':'No components supplied.');
      } else {
        assert.match(missing,lang==='zh'?/评分：\s*未提供/:/Score:\s*Not supplied/);
        assert.match(missing,lang==='zh'?/权重：\s*未提供/:/Weight:\s*Not supplied/);
      }
      const zero=await readings.nth(1).innerText();
      assert.match(zero,lang==='zh'?/评分：\s*0/:/Score:\s*0/);
      assert.match(zero,lang==='zh'?/权重：\s*0/:/Weight:\s*0/);
      assert.doesNotMatch(zero,/Not supplied|未提供|None/);
      assert.equal(await readings.nth(2).innerText(),'2026-09-10T09:00:00Z');
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        assert.equal(await composite.evaluate(n=>n.scrollWidth<=n.clientWidth+1),true);
        assert.equal(await readings.evaluateAll(ns=>ns.every(n=>n.scrollWidth<=n.clientWidth+1)),true);
        if(width===320&&process.env.INTL_BROWSER_EVIDENCE_DIR) {
          fs.mkdirSync(process.env.INTL_BROWSER_EVIDENCE_DIR,{recursive:true});
          await page.evaluate(()=>document.fonts.ready);
          await composite.evaluate(n=>n.scrollIntoView({block:'center',behavior:'instant'}));
          await composite.screenshot({path:path.join(process.env.INTL_BROWSER_EVIDENCE_DIR,`macro-component-${emptyAxis?'empty-growth':'values-settled'}-${theme}-${lang}-320.png`)});
        }
      }
      await summary.focus();await summary.press('Enter');
      assert.equal(await composite.evaluate(n=>n.open),false);
    },{htmlOverride:macroComponentValuesFixture(emptyAxis),width:320,bootLanguage:lang,initialSearch:'?view=macro'});
  });
}

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
    frame, _ = _setup(Path(tmp), omit=${isolated === 'missing-fx' ? "'USDJPY=X'" : 'None'})
    if ${isolated && isolated !== 'missing-fx' ? 'True' : 'False'}:
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

for(const lang of ['en','zh']) {
  test(`Native Compare system colours retain line and point readings ${lang}`,async t=>{
    await pageFixture(async page=>{
      const panel=page.locator('[data-im-compare-panel]:not([hidden])');
      const picker=panel.locator('[data-im-compare-pin]');
      for(const slot of ['0','1','2','4']) await picker.selectOption(slot);
      const chart=panel.locator('[data-im-chart-model]');
      const original={url:page.url(),geometry:await chart.locator('[data-im-chart-series]').evaluateAll(ns=>ns.map(n=>[n.dataset.imChartSeries,n.getAttribute('d'),n.getAttribute('transform')]))};
      for(const scheme of ['light','dark']) {
        await page.emulateMedia({forcedColors:'none',colorScheme:scheme,reducedMotion:'reduce'});
        await page.evaluate(scheme=>setTheme(scheme==='light'?'dark':'light'),scheme);
        const normalStrokes=await chart.locator('svg [stroke]').evaluateAll(ns=>ns.map(n=>getComputedStyle(n).stroke));
        await page.emulateMedia({forcedColors:'active',colorScheme:scheme,reducedMotion:'reduce'});
        // The user's system contrast colours must work independently of the
        // application theme, including a previously saved opposite theme.
        await page.evaluate(scheme=>setTheme(scheme==='light'?'dark':'light'),scheme);
        await page.locator('.sky-fx').waitFor({state:'detached'});
        assert.equal(await page.evaluate(()=>matchMedia('(forced-colors: active)').matches),true);
        for(const width of [320,1440]) {
          await page.setViewportSize({width,height:900});
          const metrics=await chart.evaluate(chart=>{
            const canvas=document.createElement('canvas'),ctx=canvas.getContext('2d',{willReadFrequently:true});
            canvas.width=canvas.height=1;
            const rgb=value=>{ctx.clearRect(0,0,1,1);ctx.fillStyle=value;ctx.fillRect(0,0,1,1);return [...ctx.getImageData(0,0,1,1).data];};
            const luminance=c=>c.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
            const marks=[...chart.querySelectorAll('[data-im-chart-series]:not([hidden])')];
            return marks.map(n=>{
              const point=n.hasAttribute('data-im-chart-point'),mark=point?n.querySelector('path'):n;
              const legend=chart.querySelector(`[data-im-chart-table-market="${n.dataset.imChartSeries}"] ${point?'[data-im-chart-point-key]':'svg line'}`);
              const style=getComputedStyle(mark),key=getComputedStyle(legend),ink=rgb(style.stroke);
              let background=null;
              for(let p=mark;p;p=p.parentElement) {
                const s=getComputedStyle(p),color=rgb(s.backgroundColor);
                if(s.opacity!=='1'||s.backgroundImage!=='none')throw Error('unsupported chart surface');
                if(color[3]===255){background=color;break;}
                if(color[3]!==0)throw Error('translucent chart surface');
              }
              if(!background||ink[3]!==255)throw Error('missing opaque chart pair');
              const a=luminance(ink),b=luminance(background);
              return {market:n.dataset.imChartSeries,point,ink,background,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05),
                pattern:point?mark.getAttribute('d'):style.strokeDasharray,
                legendPattern:point?legend.getAttribute('d'):key.strokeDasharray,
                legendStroke:key.stroke,stroke:style.stroke,vector:style.vectorEffect};
            });
          });
          t.diagnostic(JSON.stringify({scheme,lang,width,metrics}));
          if(width===320&&process.env.INTL_BROWSER_EVIDENCE_DIR) {
            fs.mkdirSync(process.env.INTL_BROWSER_EVIDENCE_DIR,{recursive:true});
            const group=chart.locator('[data-im-chart-cohort]:not([hidden])').first();
            await group.evaluate(n=>n.scrollIntoView({block:'center',behavior:'instant'}));
            await group.screenshot({path:path.join(process.env.INTL_BROWSER_EVIDENCE_DIR,`compare-system-colours-${scheme}-${lang}-320.png`)});
          }
          assert.ok(metrics.some(m=>m.point)&&metrics.some(m=>!m.point),'fixture needs lines and isolated observations');
          assert.ok(metrics.every(m=>m.ratio>=3),JSON.stringify({scheme,lang,width,metrics}));
          const systemForeground=await chart.evaluate(n=>getComputedStyle(n).color);
          assert.equal(await chart.locator('figure > svg > line').first().evaluate(n=>getComputedStyle(n).stroke),systemForeground);
          const keys=new Map();
          for(const m of metrics) {
            assert.equal(m.stroke,systemForeground);
            assert.equal(m.pattern,m.legendPattern);
            assert.equal(m.stroke,m.legendStroke);
            assert.equal(m.vector,'non-scaling-stroke');
            keys.set(m.market,`${m.point}:${m.pattern}`);
          }
          assert.equal(keys.size,4);
          assert.equal(new Set(keys.values()).size,4,'non-colour keys must distinguish every selected market');
          assert.equal(page.url(),original.url);
          assert.deepEqual(await chart.locator('[data-im-chart-series]').evaluateAll(ns=>ns.map(n=>[n.dataset.imChartSeries,n.getAttribute('d'),n.getAttribute('transform')])),original.geometry);
        }
        await page.emulateMedia({forcedColors:'none'});
        assert.deepEqual(await chart.locator('svg [stroke]').evaluateAll(ns=>ns.map(n=>getComputedStyle(n).stroke)),normalStrokes,'leaving forced colours restores the application palette');
      }
    },{htmlOverride:sourceChartFixture(true),width:320,bootLanguage:lang,initialSearch:'?view=compare'});
  });
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


for (const theme of ['dark','light']) {
  test(`Native Compare reference stroke keeps its weight at phone width ${theme}`,async()=>{
    await pageFixture(async page=>{
      await page.emulateMedia({reducedMotion:'reduce'});
      await page.evaluate(theme=>setTheme(theme),theme);
      const panel=page.locator('[data-im-compare-panel]:not([hidden])');
      const picker=panel.locator('[data-im-compare-pin]');
      await picker.selectOption('1');await picker.selectOption('4');
      const group=panel.locator('[data-im-chart-cohort]:not([hidden])');
      const rule=group.locator('figure > svg > line');
      const original=await rule.evaluate(n=>[n.getAttribute('x1'),n.getAttribute('y1'),n.getAttribute('x2'),n.getAttribute('y2')]);
      for(const width of [320,390,1440]) {
        await page.setViewportSize({width,height:900});
        const reading=await rule.evaluate(n=>{
          const s=getComputedStyle(n),m=n.getScreenCTM(),scale=Math.hypot(m.c,m.d);
          return {declared:parseFloat(s.strokeWidth),rendered:parseFloat(s.strokeWidth)*(s.vectorEffect==='non-scaling-stroke'?1:scale),scale,
            coordinates:[n.getAttribute('x1'),n.getAttribute('y1'),n.getAttribute('x2'),n.getAttribute('y2')]};
        });
        assert.ok(Math.abs(reading.rendered-reading.declared)<.01,JSON.stringify({width,...reading}));
        assert.deepEqual(reading.coordinates,original);
        if(width===320&&process.env.INTL_BROWSER_EVIDENCE_DIR) {
          fs.mkdirSync(process.env.INTL_BROWSER_EVIDENCE_DIR,{recursive:true});
          await page.evaluate(()=>document.fonts.ready);
          await group.screenshot({path:path.join(process.env.INTL_BROWSER_EVIDENCE_DIR,`reference-stroke-${theme}-320.png`)});
        }
      }
    },{htmlOverride:sourceChartFixture(),width:320,bootLanguage:'en',initialSearch:'?view=compare'});
  });
}

for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  test(`Native Compare reference label stays readable at phone width ${theme} ${lang}`,async()=>{
    await pageFixture(async page=>{
      await page.emulateMedia({reducedMotion:'reduce'});
      await page.evaluate(theme=>setTheme(theme),theme);
      const panel=page.locator('[data-im-compare-panel]:not([hidden])');
      const picker=panel.locator('[data-im-compare-pin]');
      await picker.selectOption('1');await picker.selectOption('4');
      const group=panel.locator('[data-im-chart-cohort]:not([hidden])');
      for(const width of [320,1440]) {
        await page.setViewportSize({width,height:900});
        const label=await group.evaluate(group=>{
          const n=group.querySelector('[data-im-chart-baseline-label]')||group.querySelector('figure > svg > text');
          const style=getComputedStyle(n),matrix=n instanceof SVGElement?n.getScreenCTM():null;
          const scale=matrix?Math.hypot(matrix.c,matrix.d):1;
          return {text:(n.innerText||n.textContent).trim(),renderedFont:parseFloat(style.fontSize)*scale,
            minimum:parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--fs-sm')),
            scale,rects:n.getClientRects().length};
        });
        assert.ok(label.rects>0&&label.text.includes('100'),JSON.stringify(label));
        assert.ok(label.renderedFont>=label.minimum,JSON.stringify({width,...label}));
        assert.match(label.text,lang==='zh'?/^水平虚线基准：100。$/:/^Horizontal dashed reference line: 100\.$/);
        if(process.env.INTL_BROWSER_EVIDENCE_DIR) {
          fs.mkdirSync(process.env.INTL_BROWSER_EVIDENCE_DIR,{recursive:true});
          await page.evaluate(()=>document.fonts.ready);
          await group.screenshot({path:path.join(process.env.INTL_BROWSER_EVIDENCE_DIR,`baseline-${theme}-${lang}-${width}.png`)});
        }
      }
    },{htmlOverride:sourceChartFixture(),width:320,bootLanguage:lang,initialSearch:'?view=compare'});
  });
  test(`Native Compare chart remains readable with enlarged spaced text ${theme} ${lang}`,async()=>{
    await pageFixture(async page=>{
      const panel=page.locator('[data-im-compare-panel]:not([hidden])');
      const picker=panel.locator('[data-im-compare-pin]');
      await picker.selectOption('1');await picker.selectOption('4');
      const chart=panel.locator('[data-im-chart-model]');
      const group=chart.locator('[data-im-chart-cohort]:not([hidden])');
      const summary=group.locator('summary');
      const before={url:page.url(),marks:await chart.locator('[data-im-chart-series]').evaluateAll(ns=>ns.map(n=>[n.dataset.imChartSeries,n.getAttribute('d'),n.getAttribute('transform')]))};
      await page.evaluate(theme=>{
        setTheme(theme);
        const nodes=Array.from(document.querySelectorAll('[data-im-workspace], [data-im-workspace] *')).filter(n=>n instanceof HTMLElement);
        const sizes=nodes.map(n=>[n,parseFloat(getComputedStyle(n).fontSize)]);
        sizes.forEach(([n,size])=>{n.style.fontSize=size*2+'px';n.style.lineHeight='1.5';n.style.letterSpacing='.12em';n.style.wordSpacing='.16em';});
        nodes.filter(n=>n.tagName==='P').forEach(n=>n.style.marginBottom='2em');
      },theme);
      // Text adjustment is a local reflow check, not native browser zoom.
      const layout=await panel.evaluate(panel=>{
        const root=panel.closest('[data-im-workspace]');
        const table=panel.querySelector('[data-im-chart-cohort]:not([hidden]) [data-im-chart-data-table]');
        return {width:root.clientWidth,scroll:root.scrollWidth,
          cells:Array.from(table.querySelectorAll('th,td')).filter(n=>n.getClientRects().length).map(n=>({text:n.innerText,width:n.clientWidth,scroll:n.scrollWidth})),
          controls:Array.from(panel.querySelectorAll('button,select,summary,a')).filter(n=>n.getClientRects().length).map(n=>({text:n.innerText,height:n.getBoundingClientRect().height}))};
      });
      assert.ok(layout.scroll<=layout.width+1,JSON.stringify(layout));
      assert.ok(layout.cells.length>0);
      for(const cell of layout.cells) assert.ok(cell.scroll<=cell.width+1,JSON.stringify(cell));
      for(const control of layout.controls) assert.ok(control.height>=44,JSON.stringify(control));
      await summary.focus();await page.keyboard.press('Space');
      assert.equal(await group.evaluate(n=>n.open),false);
      assert.equal(await group.locator('figure').isVisible(),false);
      await page.keyboard.press('Enter');
      assert.equal(await group.evaluate(n=>n.open),true);
      assert.equal(await group.locator('figure').isVisible(),true);
      assert.equal(await summary.evaluate(n=>n===document.activeElement),true);
      assert.equal(page.url(),before.url);
      assert.deepEqual(await chart.locator('[data-im-chart-series]').evaluateAll(ns=>ns.map(n=>[n.dataset.imChartSeries,n.getAttribute('d'),n.getAttribute('transform')])),before.marks);
      assert.deepEqual(await group.locator('[data-im-chart-table-market]:not([hidden])').evaluateAll(ns=>ns.map(n=>n.dataset.imChartTableMarket).sort()),['AU','KR']);
    },{htmlOverride:sourceChartFixture(),width:320,bootLanguage:lang,initialSearch:'?view=compare'});
  });
}

for (const lang of ['en','zh']) {
  test(`Native Compare context round trip keeps its own source geometry ${lang}`,async()=>{
    await pageFixture(async page=>{
      const panel=page.locator('[data-im-compare-panel]:not([hidden])');
      const picker=panel.locator('[data-im-compare-pin]');
      const baseline=await page.locator('[data-im-compare-panel]').evaluateAll(panels=>Object.fromEntries(panels.map(p=>[
        p.dataset.horizon+'/'+p.dataset.basis,{
          source:p.dataset.source,generation:p.dataset.imGeneration,
          marks:Array.from(p.querySelectorAll('[data-im-chart-series]')).filter(n=>['AU','KR'].includes(n.dataset.imChartSeries)).map(n=>[n.dataset.imChartSeries,n.getAttribute('d'),n.getAttribute('transform')]),
          windows:Array.from(p.querySelectorAll('[data-im-chart-cohort] > summary time')).map(n=>n.dateTime)
        }
      ])));
      await picker.selectOption('1');await picker.selectOption('4');
      const origin=page.url(),first=await panel.locator('[data-im-chart-model]').innerHTML();
      async function matches(horizon,basis) {
        const expected=baseline[horizon+'/'+basis];assert.ok(expected.marks.length>0);
        assert.equal(await panel.getAttribute('data-horizon'),horizon);
        assert.equal(await panel.getAttribute('data-basis'),basis);
        assert.equal(await panel.getAttribute('data-source'),expected.source);
        assert.equal(await panel.getAttribute('data-im-generation'),expected.generation);
        assert.equal(await page.locator('[data-im-panel]:visible').count(),1);
        const query=new URL(page.url()).searchParams;
        assert.equal(query.get('horizon'),horizon);assert.equal(query.get('basis'),basis);assert.equal(query.get('pins'),'KR,AU');
        const group=panel.locator('[data-im-chart-cohort]:not([hidden])');
        assert.equal(await group.count(),1);
        assert.deepEqual(await group.locator('[data-im-chart-series]:not([hidden])').evaluateAll(ns=>ns.map(n=>[n.dataset.imChartSeries,n.getAttribute('d'),n.getAttribute('transform')])),expected.marks);
        assert.deepEqual(await group.locator('summary time').evaluateAll(ns=>ns.map(n=>n.dateTime)),expected.windows);
        assert.deepEqual(await group.locator('[data-im-chart-table-market]:not([hidden])').evaluateAll(ns=>ns.map(n=>n.dataset.imChartTableMarket).sort()),['AU','KR']);
        assert.equal(await panel.locator('[data-im-chart-benchmark-unavailable]').isVisible(),true);
      }
      await matches('1m','usd_unhedged');
      assert.notDeepEqual(baseline['1m/usd_unhedged'].windows,baseline['3m/usd_unhedged'].windows,'fixture must discriminate horizons');
      assert.notDeepEqual(baseline['3m/usd_unhedged'].marks,baseline['3m/local'].marks,'fixture must discriminate currency bases');
      await page.selectOption('[data-im-action="set_horizon"]','3m');await matches('3m','usd_unhedged');
      await page.selectOption('[data-im-action="set_basis"]','local');await matches('3m','local');
      await page.goBack();await matches('3m','usd_unhedged');
      await page.goBack();await matches('1m','usd_unhedged');
      assert.equal(page.url(),origin);assert.equal(await panel.locator('[data-im-chart-model]').innerHTML(),first);
    },{htmlOverride:sourceChartFixture(),width:lang==='zh'?320:1440,bootLanguage:lang,initialSearch:'?view=compare'});
  });
}

for (const lang of ['en','zh']) {
  test(`Native Compare Scenario review commits only the confirmed chart context ${lang}`,async()=>{
    await pageFixture(async page=>{
      async function view(name) {
        if(lang==='zh') await page.selectOption('[data-im-controls] select[data-im-action="set_view"]',name);
        else await page.locator(`[data-im-controls] button[data-im-view="${name}"]`).click();
      }
      const panel=page.locator('[data-im-compare-panel]:not([hidden])');
      const picker=panel.locator('[data-im-compare-pin]');
      await picker.selectOption('1');await picker.selectOption('4');
      const chart=panel.locator('[data-im-chart-model]');
      const originalChart=await chart.innerHTML();
      const target=page.locator('[data-im-compare-panel][data-horizon="3m"][data-basis="usd_unhedged"]');
      const targetMarks=await target.locator('[data-im-chart-series]').evaluateAll(ns=>ns.filter(n=>['AU','KR'].includes(n.dataset.imChartSeries)).map(n=>[n.dataset.imChartSeries,n.getAttribute('d'),n.getAttribute('transform')]));
      await view('history');
      // Desktop displays History and Scenario together; only narrow screens use tabs.
      if(lang==='zh') await page.locator('[data-im-scenario-tab="scenario"]').click();
      const local=page.locator('[data-im-scenario-field="local"]'),fx=page.locator('[data-im-scenario-field="fx"]');
      await local.fill('5');await fx.fill('-3');
      await page.locator('[data-im-scenario-action="calculate"]').click();
      const initialResult=await page.locator('[data-im-scenario-usd]').innerText();
      await view('compare');
      const originalUrl=page.url(),horizon=page.locator('[data-im-controls] select[data-im-action="set_horizon"]');
      await horizon.selectOption('3m');
      assert.equal(await page.locator('[data-im-scenario-confirm-context]').isVisible(),true);
      assert.equal(new URL(page.url()).searchParams.get('horizon'),'1m');
      assert.equal(await horizon.inputValue(),'1m');
      assert.equal(await page.locator('[data-im-compare-panel]:visible').count(),0);
      await local.fill('12');await local.press('Escape');
      assert.equal(page.url(),originalUrl);
      assert.equal(await chart.innerHTML(),originalChart);
      assert.equal(await local.inputValue(),'5');
      assert.equal(await page.locator('[data-im-scenario-usd]').innerText(),initialResult);
      assert.equal(await horizon.evaluate(n=>n===document.activeElement),true);
      await horizon.selectOption('3m');await local.fill('10');
      await page.locator('[data-im-scenario-action="confirm_context"]').click();
      assert.equal(await panel.getAttribute('data-horizon'),'3m');
      assert.equal(new URL(page.url()).searchParams.get('horizon'),'3m');
      assert.equal(new URL(page.url()).searchParams.get('pins'),'KR,AU');
      assert.deepEqual(await chart.locator('[data-im-chart-series]:not([hidden])').evaluateAll(ns=>ns.map(n=>[n.dataset.imChartSeries,n.getAttribute('d'),n.getAttribute('transform')])),targetMarks);
      assert.equal(await page.locator('[data-im-scenario-confirm-context]').isVisible(),false);
      assert.equal(await page.evaluate(()=>!document.activeElement.closest('[hidden]')),true);
      await view('history');
      assert.equal(await local.inputValue(),'10');assert.equal(await fx.inputValue(),'-3');
      assert.match(await page.locator('[data-im-scenario-usd]').innerText(),/6\.7/);
      assert.match(await page.locator('[data-im-scenario-context]').innerText(),/3m/);
    },{htmlOverride:sourceChartFixture(),width:lang==='zh'?320:1440,bootLanguage:lang,initialSearch:'?view=compare'});
  });
}

for (const lang of ['en','zh']) {
  test(`Native Compare missing FX retains selections across basis and Back ${lang}`,async()=>{
    await pageFixture(async page=>{
      const panel=page.locator('[data-im-compare-panel]:not([hidden])');
      const picker=panel.locator('[data-im-compare-pin]');
      await picker.selectOption('1');await picker.selectOption('4');
      const initialUrl=page.url(),chart=panel.locator('[data-im-chart-model]');
      const initialChart=await chart.innerHTML();
      assert.equal(await panel.getAttribute('data-im-compare-state'),'comparable');
      assert.deepEqual(await chart.locator('[data-im-chart-table-market]:not([hidden])').evaluateAll(ns=>ns.map(n=>n.dataset.imChartTableMarket).sort()),['AU','KR']);
      await picker.selectOption('0');
      // The native owner gives Japan's local-only leg a distinct calendar
      // policy. An available price is not a matching comparison window.
      assert.equal(await panel.getAttribute('data-im-compare-reason'),'unequal_windows');
      assert.equal(await panel.locator('[data-im-chart-cohort]:visible').count(),0);
      const japan=panel.locator('[data-im-compare-slot="0"]');
      const localValue=await japan.locator('[data-im-compare-metric="local"] [data-im-compare-value]').innerText();
      await page.selectOption('[data-im-action="set_basis"]','usd_unhedged');
      assert.equal(new URL(page.url()).searchParams.get('pins'),'KR,AU,JP');
      assert.equal(await panel.getAttribute('data-im-compare-state'),'incomparable');
      assert.equal(await panel.getAttribute('data-im-compare-reason'),'selection_unqualified');
      assert.deepEqual(await panel.locator('[data-im-compare-slot]:not([hidden])').evaluateAll(ns=>ns.map(n=>n.dataset.imCompareSlot)),['1','4','0']);
      assert.equal(await panel.locator('[data-im-chart-cohort]:visible').count(),0);
      assert.equal(await panel.locator('[data-im-chart-series]:visible').count(),0);
      assert.equal(await japan.locator('[data-im-compare-metric="local"] [data-im-compare-value]').innerText(),localValue);
      for(const leg of ['usd','fx_contribution']) assert.equal(await japan.locator(`[data-im-compare-metric="${leg}"] [data-im-compare-value]`).innerText(),lang==='zh'?'不可用':'Unavailable');
      const reading=await panel.locator('[data-im-compare-status]').innerText();
      assert.match(reading,lang==='zh'?/全部选择已保留/:/All selections are retained/);
      const client=await page.context().newCDPSession(page);
      const tree=(await client.send('Accessibility.getFullAXTree')).nodes;
      assert.equal(tree.filter(n=>!n.ignored&&n.role?.value==='image'&&/Same starting point|相同起点/.test(n.name?.value||'')).length,0,'a hidden comparison must not remain exposed as a chart');
      await page.goBack();
      assert.equal(await panel.getAttribute('data-basis'),'local');
      assert.equal(await panel.getAttribute('data-im-compare-reason'),'unequal_windows');
      assert.equal(await panel.locator('[data-im-chart-cohort]:visible').count(),0);
      await page.goBack();await page.waitForURL(initialUrl);
      assert.equal(await panel.getAttribute('data-im-compare-state'),'comparable');
      assert.equal(await chart.innerHTML(),initialChart);
      await page.goForward();
      assert.equal(await panel.getAttribute('data-im-compare-reason'),'unequal_windows');
      await page.goForward();
      assert.equal(new URL(page.url()).searchParams.get('pins'),'KR,AU,JP');
      assert.equal(await panel.getAttribute('data-im-compare-reason'),'selection_unqualified');
      assert.equal(await panel.locator('[data-im-chart-cohort]:visible').count(),0);
    },{htmlOverride:sourceChartFixture('missing-fx'),width:lang==='zh'?320:1440,bootLanguage:lang,initialSearch:'?view=compare&basis=local'});
  });
}

for (const lang of ['en','zh']) {
  test(`Native Compare bookmark reload adopts the served source and recovers ${lang}`,async()=>{
    const originalHtml=sourceChartFixture(),missingFxHtml=sourceChartFixture('missing-fx');
    await pageFixture(async page=>{
      const panel=page.locator('[data-im-compare-panel]:not([hidden])');
      const picker=panel.locator('[data-im-compare-pin]');
      await picker.selectOption('0');await picker.selectOption('1');
      await page.selectOption('[data-im-action="set_horizon"]','3m');
      const bookmark=page.url();
      const original={source:await panel.getAttribute('data-source'),generation:await panel.getAttribute('data-im-generation'),
        chart:await panel.locator('[data-im-chart-model]').innerHTML()};
      assert.equal(await panel.getAttribute('data-im-compare-state'),'comparable');
      const expected=await page.evaluate(html=>{
        const doc=new DOMParser().parseFromString(html,'text/html');
        const p=doc.querySelector('[data-im-compare-panel][data-horizon="3m"][data-basis="usd_unhedged"]');
        return {source:p.dataset.source,generation:p.dataset.imGeneration};
      },missingFxHtml);
      assert.notEqual(expected.source,original.source,'the next native publication must have a different source binding');
      // Replace only the local document response. Reload the actual bookmark:
      // no dispatch, invented admission, or source identity in URL state.
      let servedHtml=missingFxHtml;
      await page.route('http://intl.test/intl.html*',route=>route.fulfill({contentType:'text/html',body:servedHtml}));
      await page.reload({waitUntil:'load'});
      assert.equal(page.url(),bookmark);
      assert.equal(await page.locator('[data-im-enhanced]').count(),1);
      assert.equal(await page.locator('[data-im-panel]:visible').count(),1);
      assert.equal(await panel.getAttribute('data-source'),expected.source);
      assert.equal(await panel.getAttribute('data-im-generation'),expected.generation);
      assert.equal(await panel.getAttribute('data-horizon'),'3m');
      assert.equal(await panel.getAttribute('data-basis'),'usd_unhedged');
      assert.equal(new URL(page.url()).searchParams.get('pins'),'JP,KR');
      assert.equal(await panel.getAttribute('data-im-compare-reason'),'selection_unqualified');
      assert.equal(await panel.locator('[data-im-chart-cohort]:visible').count(),0);
      assert.deepEqual(await panel.locator('[data-im-compare-slot]:not([hidden])').evaluateAll(ns=>ns.map(n=>n.dataset.imCompareSlot)),['0','1']);
      const japan=panel.locator('[data-im-compare-slot="0"]');
      assert.equal(await japan.locator('[data-im-compare-metric="usd"] [data-im-compare-value]').innerText(),lang==='zh'?'不可用':'Unavailable');
      assert.doesNotMatch(await japan.locator('[data-im-compare-metric="local"] [data-im-compare-value]').innerText(),/Unavailable|不可用/);
      servedHtml=originalHtml;
      await page.reload({waitUntil:'load'});
      assert.equal(page.url(),bookmark);
      assert.equal(await page.locator('[data-im-enhanced]').count(),1);
      assert.equal(await page.locator('[data-im-panel]:visible').count(),1);
      assert.equal(await panel.getAttribute('data-source'),original.source);
      assert.equal(await panel.getAttribute('data-im-generation'),original.generation);
      assert.equal(await panel.getAttribute('data-im-compare-state'),'comparable');
      assert.equal(await panel.locator('[data-im-chart-model]').innerHTML(),original.chart);
    },{htmlOverride:originalHtml,width:lang==='zh'?320:1440,bootLanguage:lang,initialSearch:'?view=compare'});
  });
}

for (const bootLanguage of ['en','zh']) {
  test(`Native Compare remove names identify the localized market ${bootLanguage}`,async()=>{
    await pageFixture(async page=>{
      const panel=page.locator('[data-im-compare-panel]:not([hidden])');
      const picker=panel.locator('[data-im-compare-pin]');
      await picker.selectOption('0');await picker.selectOption('1');
      const bookmark=page.url();
      const removeKorea=panel.locator('[data-im-compare-remove="1"]');
      await removeKorea.focus();
      for(const lang of [bootLanguage,bootLanguage==='en'?'zh':'en',bootLanguage]) {
        await page.evaluate(lang=>setLang(lang),lang);
        const marketNames=[];
        for(const slot of ['0','1']) {
          const name=await picker.locator(`option[value="${slot}"]`).getAttribute(`data-im-label-${lang}`);
          marketNames.push(name);
          const label=(lang==='zh'?'移除选择':'Remove selection')+' '+name;
          assert.equal(await panel.getByRole('button',{name:label,exact:true}).count(),1,label);
        }
        assert.equal(new Set(marketNames).size,2);
        assert.equal(page.url(),bookmark);
        assert.equal(await removeKorea.evaluate(n=>document.activeElement===n),true);
      }
      await removeKorea.press('Enter');
      assert.equal(new URL(page.url()).searchParams.get('pins'),'JP');
      assert.equal(await picker.evaluate(n=>document.activeElement===n),true);
      assert.equal(await panel.locator('[data-im-compare-remove="0"]').isVisible(),true);
      assert.equal(await removeKorea.isVisible(),false);
    },{htmlOverride:sourceChartFixture(),width:bootLanguage==='zh'?320:1440,bootLanguage,initialSearch:'?view=compare'});
  });
}

for (const lang of ['en','zh']) {
  test(`Native Compare refused additions preserve chart and recover ${lang}`,async()=>{
    await pageFixture(async page=>{
      const panel=page.locator('[data-im-compare-panel]:not([hidden])');
      const picker=panel.locator('[data-im-compare-pin]');
      const chart=panel.locator('[data-im-chart-model]');
      for(const slot of ['1','4','0','2']) await picker.selectOption(slot);
      assert.equal(await panel.getAttribute('data-im-compare-state'),'comparable');
      async function snapshot() {
        return {url:page.url(),history:await page.evaluate(()=>history.length),chart:await chart.innerHTML(),rows:await panel.locator('[data-im-compare-rows]').innerHTML()};
      }
      let before=await snapshot();
      await picker.focus();await picker.selectOption('3');
      assert.deepEqual(await snapshot(),before);
      assert.equal(await picker.inputValue(),'');
      assert.equal(await picker.evaluate(n=>n===document.activeElement),true);
      assert.match(await page.locator('[data-im-issues]').textContent(),lang==='zh'?/已达固定上限/:/Pin limit reached/);
      await panel.locator('[data-im-compare-remove="2"]').click();
      before=await snapshot();
      await page.evaluate(()=>{window.originalPush=history.pushState;history.pushState=()=>{throw Error('synthetic history failure')};});
      try { await picker.selectOption('3'); }
      finally { await page.evaluate(()=>history.pushState=originalPush); }
      assert.deepEqual(await snapshot(),before);
      assert.equal(await picker.inputValue(),'');
      assert.equal(await picker.evaluate(n=>n===document.activeElement),true);
      await picker.selectOption('3');
      assert.equal(await picker.inputValue(),'');
      assert.deepEqual(await chart.locator('[data-im-chart-table-market]:not([hidden])').evaluateAll(ns=>ns.map(n=>n.dataset.imChartTableMarket).sort()),['AU','IN','JP','KR']);
      assert.equal(await chart.locator('[data-im-chart-cohort]:not([hidden]) [data-im-chart-market-count]').textContent(),'4');
    },{htmlOverride:sourceChartFixture(),width:lang==='zh'?320:1440,bootLanguage:lang,initialSearch:'?view=compare'});
  });
}

for (const lang of ['en','zh']) for (const width of [320,1440]) {
  test(`Native Compare chart survives Overview evidence round trip ${lang} ${width}`,async()=>{
    await pageFixture(async page=>{
      await page.emulateMedia({reducedMotion:'reduce'});
      await page.evaluate(lang=>setTheme(lang==='en'?'dark':'light'),lang);
      const panel=page.locator('[data-im-compare-panel]:not([hidden])');
      const picker=panel.locator('[data-im-compare-pin]');
      await picker.selectOption('1');await picker.selectOption('4');
      const chart=panel.locator('[data-im-chart-model]');
      const before=await chart.innerHTML(),origin=page.url();
      const generation=await panel.getAttribute('data-im-generation');
      assert.match(generation,/^im-workspace-generation:[0-9a-f-]{36}$/);
      const source=await panel.getAttribute('data-source');
      assert.ok(source,'Compare must retain an actual disclosed source reference');
      assert.deepEqual(await chart.locator('[data-im-chart-table-market]:not([hidden])').evaluateAll(ns=>ns.map(n=>n.dataset.imChartTableMarket).sort()),['AU','KR']);
      assert.ok(await chart.locator('[data-im-chart-series]:not([hidden])').count()>0);
      if(width===320) await page.selectOption('[data-im-controls] select[data-im-action="set_view"]','overview');
      else await page.locator('[data-im-controls] button[data-im-view="overview"]').click();
      const overview=page.locator('[data-im-panel][data-view="overview"]:visible');
      await overview.locator('[data-im-expansion-trigger]').click();
      const trigger=page.locator('[data-im-inspector-origin]:visible')
        .filter({has:page.locator('[data-im-inspector-payload][data-market-id="KR"]')})
        .locator('[data-im-inspector-trigger]');
      await trigger.focus();await page.keyboard.press('Enter');
      const dialog=page.locator('dialog:visible');
      const article=dialog.locator('[data-im-inspector-payload]');
      assert.equal(await article.getAttribute('data-market-id'),'KR');
      assert.equal(await article.getAttribute('data-im-generation'),generation);
      const evidenceSource=await article.getAttribute('data-source');
      assert.ok(evidenceSource,'Inspector must retain its actual disclosed source');
      assert.equal(evidenceSource,await overview.getAttribute('data-source'));
      const tuple=await article.evaluate(n=>['data-horizon','data-basis','data-return-basis'].map(k=>n.getAttribute(k)));
      const query=new URL(origin).searchParams;
      assert.deepEqual(tuple,[query.get('horizon'),query.get('basis'),query.get('return_basis')]);
      const facts=await article.locator('[data-im-inspector-metric]').allTextContents();
      const evidence=dialog.locator('[data-im-inspector-action="evidence"]');
      await evidence.focus();await page.keyboard.press('Enter');
      assert.equal(await dialog.locator('[data-im-inspector-page="ledger"]').isVisible(),true);
      await dialog.locator('[data-im-inspector-action="back"]').click();
      assert.deepEqual(await article.locator('[data-im-inspector-metric]').allTextContents(),facts);
      await page.keyboard.press('Escape');
      assert.equal(await trigger.evaluate(n=>n===document.activeElement),true);
      await page.goBack();await page.waitForURL(origin);
      assert.equal(await panel.isVisible(),true);
      assert.equal(await chart.innerHTML(),before,'chart identity, selection, data and accessible context survive the supported return path');
      assert.equal(await panel.getAttribute('data-im-generation'),generation);
      assert.equal(await panel.getAttribute('data-source'),source);
      assert.equal(await page.locator('dialog:visible').count(),0);
    },{htmlOverride:sourceChartFixture(),width,bootLanguage:lang,initialSearch:'?view=compare'});
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

for(const [bootLanguage,width] of [['en',1440],['zh',320]]) {
  test(`Scenario result status follows locale without repeated announcements ${bootLanguage} ${width}`,async()=>{
    await pageFixture(async page=>{
      await page.waitForSelector('[data-im-enhanced="true"]');
      const panel=page.locator('[data-im-history-panel]');
      if(width===320) await panel.locator('[data-im-scenario-tab="scenario"]').click();
      const local=panel.locator('#im-scenario-local'),fx=panel.locator('#im-scenario-fx');
      const calculate=panel.locator('[data-im-scenario-action="calculate"]');
      const status=panel.locator('[data-im-scenario-announcement]');
      const expected=lang=>lang==='en'?'Conditional USD return 5.84%; FX contribution -2.16 pp':'条件美元回报 5.84%; 汇率贡献 -2.16 个百分点';
      await local.fill('8');await fx.fill('-2');await calculate.click();
      assert.equal(await status.innerText(),expected(bootLanguage));
      const url=page.url();
      await fx.focus();
      await status.evaluate(node=>{
        window.__scenarioStatusChanges=[];
        window.__scenarioStatusObserver=new MutationObserver(records=>window.__scenarioStatusChanges.push(...records.map(()=>node.textContent)));
        window.__scenarioStatusObserver.observe(node,{childList:true,characterData:true,subtree:true});
      });
      const lang=bootLanguage==='en'?'zh':'en';
      await page.evaluate(lang=>setLang(lang),lang);
      await page.waitForFunction(lang=>document.querySelector('[data-im-scenario-contribution]').textContent.includes(lang==='zh'?'个百分点':'pp'),lang);
      assert.equal(await status.innerText(),expected(lang));
      assert.equal(await local.inputValue(),'8');assert.equal(await fx.inputValue(),'-2');
      assert.equal(await fx.evaluate(n=>n===document.activeElement),true);
      assert.equal(page.url(),url);
      assert.deepEqual(await page.evaluate(()=>__scenarioStatusChanges),[expected(lang)]);
      await page.evaluate(lang=>setLang(lang),lang);
      await calculate.click();
      await page.evaluate(()=>setTheme('light'));
      assert.deepEqual(await page.evaluate(()=>__scenarioStatusChanges),[expected(lang)],'same locale, theme and unchanged calculation must not rewrite the status');
      await page.locator('[data-im-controls] select[data-im-action="set_horizon"]').selectOption('3m');
      assert.equal(await panel.locator('[data-im-scenario-confirm-context]').isVisible(),true);
      assert.equal(await status.textContent(),'');
      await page.evaluate(lang=>setLang(lang),bootLanguage);
      await page.waitForFunction(lang=>document.querySelector('[data-im-scenario-candidate-context]').textContent.includes(lang==='zh'?'研究口径':'Research basis'),bootLanguage);
      assert.equal(await status.textContent(),'','locale change must not resurrect an unconfirmed result');
      await panel.locator('[data-im-scenario-action="cancel_context"]').click();
      await local.fill('9');await calculate.click();
      assert.equal(await status.innerText(),bootLanguage==='en'?'Conditional USD return 6.82%; FX contribution -2.18 pp':'条件美元回报 6.82%; 汇率贡献 -2.18 个百分点');
      await panel.locator('[data-im-scenario-action="request_reset"]').click();
      await panel.locator('[data-im-scenario-action="confirm_reset"]').click();
      assert.equal(await status.textContent(),'');
      await page.evaluate(()=>__scenarioStatusObserver.disconnect());
    },{htmlOverride:coldLocaleHtml,bootLanguage,width,initialSearch:'?view=history&market=JP'});
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
  test(`Native Compare source stays readable after ${options.broken?'failed enhancement':'JavaScript loss'}`,async()=>{
    await pageFixture(async page=>{
      assert.equal(await page.locator('[data-im-enhanced]').count(),0);
      assert.equal(await page.locator('[data-im-controls]').evaluate(n=>n.disabled),true);
      const charts=page.locator('[data-im-compare-panel]:visible [data-im-chart-model]');
      assert.ok(await charts.count()>0,'the real publisher must supply at least one chart');
      for (const chart of await charts.all()) {
        const panel=chart.locator('..');
        assert.match(await panel.getAttribute('data-source'),/^intl-supplied-close:sha256:[0-9a-f]{64}$/);
        const groups=chart.locator('[data-im-chart-cohort]');
        assert.ok(await groups.count()>0);
        for (const group of await groups.all()) {
          if(!await group.evaluate(n=>n.open)) await group.locator('summary').click();
          const rows=group.locator('[data-im-chart-table-market]:visible');
          const markets=await rows.evaluateAll(ns=>ns.map(n=>n.dataset.imChartTableMarket).sort());
          assert.equal(markets.length,7,'unenhanced charts retain the full supplied cohort, not a fabricated URL selection');
          assert.equal(Number(await group.locator('[data-im-chart-market-count]').textContent()),markets.length);
          const plotted=await group.locator('[data-im-chart-series]:not([hidden])').evaluateAll(ns=>[...new Set(ns.map(n=>n.dataset.imChartSeries))].sort());
          assert.deepEqual(plotted,markets);
          const svg=group.locator('figure > svg');
          assert.equal(await svg.getAttribute('role'),'img');
          const labelled=await svg.evaluate(n=>(n.getAttribute('aria-labelledby')||'').split(/\s+/).map(id=>!!document.getElementById(id)));
          assert.ok(labelled.length>=2&&labelled.every(Boolean));
        }
        assert.equal(await chart.locator('[data-im-chart-selection-unavailable]').isVisible(),false);
        assert.equal(await chart.locator('[data-im-chart-benchmark-unavailable]').isVisible(),true);
      }
    },{...options,htmlOverride:sourceChartFixture(),width:320,initialSearch:'?view=compare&pins=1,4'});
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

for(const [lang,width] of [['en',1440],['zh',320]]) {
  test(`Library settled search status changes only with its message ${lang} ${width}`,async()=>{
    await pageFixture(async page=>{
      await page.waitForSelector('[data-im-library-enhanced="true"]');
      const input=page.locator('[data-im-library-search]');
      const status=page.locator('[data-im-library-status]');
      await status.evaluate(node=>{
        window.__libraryStatusChanges=[];
        window.__libraryStatusObserver=new MutationObserver(records=>window.__libraryStatusChanges.push(...records.map(()=>node.textContent)));
        window.__libraryStatusObserver.observe(node,{childList:true,characterData:true,subtree:true});
      });
      const originalURL=page.url();
      for(const query of ['currency','unmatched-xyzz','a'.repeat(257)]) {
        await input.fill(query);
        const message=await status.textContent();
        assert.ok(message);
        assert.deepEqual(await page.evaluate(()=>__libraryStatusChanges),[message],'a new settled message updates once');
        const keys=await page.locator('[data-im-library-results] [data-im-library-tool]').evaluateAll(ns=>ns.map(n=>n.dataset.imLibraryTool));
        await page.evaluate(()=>{__libraryStatusChanges.length=0;});
        // A native resize and a no-op locale application repaint the workspace,
        // but neither changes the committed search result or its status.
        await afterWindowEvent(page,'resize',()=>page.setViewportSize({width:width+1,height:900}));
        await afterWindowEvent(page,'resize',()=>page.setViewportSize({width,height:900}));
        await page.evaluate(lang=>setLang(lang),lang);
        assert.deepEqual(await page.evaluate(()=>__libraryStatusChanges),[],'unchanged search status must not be rewritten by unrelated repaint');
        assert.equal(await input.inputValue(),query);
        assert.equal(await input.evaluate(n=>n===document.activeElement),true);
        assert.deepEqual(await page.locator('[data-im-library-results] [data-im-library-tool]').evaluateAll(ns=>ns.map(n=>n.dataset.imLibraryTool)),keys);
        assert.equal(page.url(),originalURL);
        const other=lang==='en'?'zh':'en';
        await page.evaluate(other=>setLang(other),other);
        const translated=await status.textContent();
        assert.notEqual(translated,message);
        assert.deepEqual(await page.evaluate(()=>__libraryStatusChanges),[translated],'a new locale still updates the status once');
        await page.evaluate(lang=>setLang(lang),lang);
        assert.equal(await status.textContent(),message);
        await page.evaluate(()=>{__libraryStatusChanges.length=0;});
      }
      await page.locator('[data-im-library-clear]').click();
      assert.equal(await status.textContent(),'');
      assert.deepEqual(await page.evaluate(()=>__libraryStatusChanges),['']);
      await page.evaluate(()=>__libraryStatusObserver.disconnect());
    },{bootLanguage:lang,width,initialSearch:'?view=library'});
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
