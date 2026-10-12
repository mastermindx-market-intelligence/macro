'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = () => fs.readFileSync(process.env.HK_HEATMAP_SOURCE ||
  path.join(__dirname, '../templates/heatmap.js'), 'utf8');
const NOW = Date.UTC(2026, 9, 12, 8, 45);  // Mon 16:45 HKT, after HK closing auction
const LAST_PRINT = Date.UTC(2026, 9, 12, 8, 8); // HK 16:08 closing auction
const FRI_PRINT = Date.UTC(2026, 9, 9, 8, 8);
function prepare() {
  const clock={now:NOW};
  class FixedDate extends Date { static now() { return clock.now; } }
  const events=[],timers=[];
  const js = source();
  const start = js.indexOf('  /* HK quote marks reuse');
  const end = js.indexOf('  /* ---- per-timeframe', start);
  assert.ok(start > 0 && end > start, 'HK source block missing');
  const ctx = vm.createContext({Date: FixedDate, Math, Number, Object, Array,
    Intl, Promise, console, clearTimeout, window: {},
    setTimeout:fn=>{timers.push(fn);return timers.length;},
    CustomEvent:function(name,opts){this.type=name;this.detail=opts.detail;},
    document: {hidden: false, addEventListener:()=>{}, dispatchEvent:e=>events.push(e)}});
  vm.runInContext(js.slice(start, end), ctx);
  const f = {
    project: vm.runInContext('hkLiveProject', ctx),
    meta: vm.runInContext('hkLiveMeta', ctx),
    state: vm.runInContext('_hkLiveStates', ctx),
    start: vm.runInContext('startHKLiveRefresh', ctx),
    clock, events, timers, ctx,
  };
  const a = js.indexOf('  function heatmapValue(data, tile, tf)');
  const b = js.indexOf('  function medianPc(', a);
  assert.ok(a > 0 && b > a, 'shared value gateway missing');
  vm.runInContext(js.slice(a, b), ctx);
  f.value = vm.runInContext('heatmapValue', ctx);
  return f;
}
function fixture(n = 158, quoteCount = n, quoteTs = LAST_PRINT) {
  const tiles = Array.from({length: n}, (_,i) => ({
    t: String(i + 1).padStart(4, '0') + '.HK',
    perf: {'1D': 9, '1W': 7}
  }));
  const quotes = Object.create(null);
  for (let i = 0; i < quoteCount; i++) {
    quotes[tiles[i].t] = {source: 'yahoo', basis: 'regular', price: 102,
      prevClose: 100, changePct: 2, ts: quoteTs};
  }
  const base = {market:'hk', map_type:'stocks', asof:'2026-10-09',
    n_tiles:n, tiles, _url:'marketdata/hk_heatmap.json'};
  return {base, feed:{source:'snapshot',ts:NOW-60000, quotes}};
}
test('current HK delayed closing-auction cohort replaces 1D, not 1W or daily data', () => {
  const f=prepare(), {base,feed}=fixture();
  const m=f.project(feed,base,NOW);
  assert.equal(m.asof,'2026-10-12');
  assert.equal(m.baselineAsOf,'2026-10-09');
  assert.equal(m.resolved,158);
  assert.equal(m.usable,true);
  f.state[base._url]={data:m,base};
  assert.ok(Math.abs(f.value(base,base.tiles[0],'1D')-2)<1e-9);
  assert.equal(f.value(base,base.tiles[0],'1W'),7);
  assert.equal(base.tiles[0].perf['1D'],9,'canonical daily remains untouched');
});
test('rejects low-coverage and mixed-date cohorts without painting hybrid colors',()=>{
  const f=prepare(), {base,feed}=fixture(158,150);
  const m=f.project(feed,base,NOW);
  assert.equal(m.resolved,150);
  assert.equal(m.usable,false);
  f.state[base._url]={data:m,base};
  assert.equal(f.value(base,base.tiles[0],'1D'),9,'daily fallback remains coherent');
  const ok=fixture(158,158);
  ok.feed.quotes[ok.base.tiles[0].t].ts=FRI_PRINT;
  const mixed=f.project(ok.feed,ok.base,NOW);
  assert.equal(mixed.resolved,157);
  assert.equal(mixed.usable,true);
  f.state[ok.base._url]={data:mixed,base:ok.base};
  assert.equal(f.value(ok.base,ok.base.tiles[0],'1D'),null,'unknown quote is null, not stale daily');
});
test('stale Friday source cannot masquerade as a Monday quote',()=>{
  const f=prepare(),{base,feed}=fixture(158,158,FRI_PRINT);
  assert.equal(f.project(feed,base,NOW),null);
});
test('post-close quote must be after the Hong Kong closing-auction window',()=>{
  const f=prepare(),{base,feed}=fixture(158,158,Date.UTC(2026,9,12,7,35));
  assert.equal(f.project(feed,base,NOW),null);
});
test('rejects expired producer, future quote, synthetic quote, invalid basis and bad returns',()=>{
  const f=prepare();
  for (const bad of ['expired','future','synthetic','basis','return']) {
    const {base,feed}=fixture(10);
    if (bad==='expired') feed.ts=NOW-13*60000;
    if (bad==='future') feed.quotes['0001.HK'].ts=NOW+10000;
    if (bad==='synthetic') feed.quotes['0001.HK'].ts=null;
    if (bad==='basis') feed.quotes['0001.HK'].basis='prev';
    if (bad==='return') feed.quotes['0001.HK'].changePct=29;
    const meta=f.project(feed,base,NOW);
    if (bad==='expired') assert.equal(meta,null);
    else {assert.equal(meta.resolved,9); assert.equal(meta.usable,false);}
  }
});
test('later stale heartbeat cannot keep an accepted map live',()=>{
  const f=prepare(),{base,feed}=fixture();
  const m=f.project(feed,base,NOW);
  m.generatedAt=NOW-13*60000;
  f.state[base._url]={data:m,base};
  assert.equal(f.meta(base),null);
  assert.equal(f.value(base,base.tiles[0],'1D'),9);
});
test('both renderer owners share HK live state and never open a second vendor lane',()=>{
  const js=source();
  assert.equal((js.match(/startHKLiveRefresh\(data\);/g)||[]).length,2);
  assert.match(js,/HK_LIVE_URL = 'live\/quotes.json'/);
  assert.match(js,/chinaLiveFetch\(HK_LIVE_URL, generation\)/);
  assert.ok((js.match(/hkLiveDescriptor\(data\)/g)||[]).length>=3);
  assert.match(js,/data\.market !== 'china' && data\.market !== 'hk'/);
  const match=js.match(/var _LIVE_MKT = \{[^}]*\};/);
  assert.ok(match);
  assert.doesNotMatch(match[0],/hk\s*:/);
  assert.match(match[0],/canada:\s*'ca'/);
});

test('HK live expiry repaints the daily fallback even when the next request fails', async()=>{
  const f=prepare(),{base,feed}=fixture();
  f.ctx.chinaLiveFetch=()=>Promise.resolve(feed);
  f.start(base);
  assert.equal(f.timers.length,1);
  f.timers.shift()();
  for(let i=0;i<6;i++) await new Promise(resolve=>setImmediate(resolve));
  assert.equal(f.events.length,1,'first accepted live snapshot repaints');
  assert.equal(f.state[base._url].data.usable,true);
  f.clock.now += 13*60000;
  f.ctx.chinaLiveFetch=()=>Promise.reject(new Error('connection lost'));
  f.timers.shift()();
  for(let i=0;i<6;i++) await new Promise(resolve=>setImmediate(resolve));
  assert.equal(f.events.length,2,'expiry repaints despite transport failure');
  assert.equal(f.meta(base),null);
  assert.equal(f.value(base,base.tiles[0],'1D'),9);
});
