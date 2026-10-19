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
  return {base, feed:{source:'snapshot',baseline_asof:'2026-10-09',ts:NOW-60000, quotes, session:calendarSession()}};
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
  assert.match(js,/HK_LIVE_URL = 'live\/hk_heatmap.json'/);
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

test('HK cannot splice a valid quote cohort into a mismatched daily baseline',()=>{
 const f=prepare(), {base,feed}=fixture();
 feed.baseline_asof='2026-10-08';
 assert.equal(f.project(feed,base,NOW),null);
});


function calendarSession(overrides={}) {
 return {schema:'hk_heatmap_session.v1',calendar_date:'2026-10-12',session_date:'2026-10-12',
  previous_session:'2026-10-09',is_session:true,phase:'post_close',close_minute:970,
  settled_asof:'2026-10-09',next_open_at:'2026-10-13T09:30:00+08:00',...overrides};
}
test('HK live refuses unqualified calendar envelopes rather than inventing a trading day',()=>{
 const f=prepare(),{base,feed}=fixture();delete feed.session;
 assert.equal(f.project(feed,base,NOW),null);
});
test('HK holiday heartbeat cannot originate a current-session quote',()=>{
 const f=prepare(),{base,feed}=fixture();const now=Date.UTC(2026,9,19,3);
 base.asof='2026-10-16';feed.baseline_asof=base.asof;feed.ts=now;
 feed.session=calendarSession({calendar_date:'2026-10-19',session_date:'2026-10-16',previous_session:'2026-10-15',is_session:false,phase:'holiday',settled_asof:'2026-10-16',next_open_at:'2026-10-20T09:30:00+08:00'});
 for(const q of Object.values(feed.quotes))q.ts=now-60000;
 assert.equal(f.project(feed,base,now),null);
});
test('HK post-close 15:46 prints do not impersonate closing-auction observations',()=>{
 const f=prepare(),{base,feed}=fixture(158,158,Date.UTC(2026,9,12,7,46));feed.session=calendarSession();
 assert.equal(f.project(feed,base,NOW),null);
});
test('HK source expires despite a younger heartbeat and before the next request',()=>{
 const f=prepare(),now=Date.UTC(2026,9,12,3,0),{base,feed}=fixture(158,158,Date.UTC(2026,9,12,2,30));
 f.clock.now=now;feed.ts=now;feed.session=calendarSession({phase:'morning'});
 const m=f.project(feed,base,now);assert.ok(m&&m.usable);f.state[base._url]={data:m,base};
 f.clock.now=now+6*60000;
 assert.equal(f.meta(base),null,'source exceeds 15-minute delay plus 20-minute allowance');
 assert.equal(f.value(base,base.tiles[0],'1D'),9);
});
test('HK current cohort requires the adjacent prior exchange-session baseline',()=>{
 const f=prepare(),{base,feed}=fixture();base.asof='2026-10-08';feed.baseline_asof=base.asof;feed.session=calendarSession();
 assert.equal(f.project(feed,base,NOW),null);
});
test('HK half-day closed state rejects afternoon heartbeat prints',()=>{
 const f=prepare(),now=Date.UTC(2026,11,24,5,30),{base,feed}=fixture(158,158,Date.UTC(2026,11,24,5));
 base.asof='2026-12-23';feed.baseline_asof=base.asof;feed.ts=now;
 feed.session=calendarSession({calendar_date:'2026-12-24',session_date:'2026-12-24',previous_session:'2026-12-23',close_minute:730,settled_asof:'2026-12-24',next_open_at:'2026-12-28T09:30:00+08:00'});
 assert.equal(f.project(feed,base,now),null);
});


function snapshotApi(fetcher=()=>Promise.reject(new Error('offline'))) {
 const raw=source(),a=raw.indexOf("  var JSON_URL ="),b=raw.indexOf('  /* ---- China current-session overlay:',a);
 assert.ok(a>=0&&b>a);
 const ctx=vm.createContext({Date,Math,Number,Object,Array,String,JSON,Promise,Error,isNaN,isFinite,
  setTimeout,clearTimeout,setInterval:()=>1,clearInterval:()=>{},AbortController,
  fetch:fetcher,document:{hidden:false,dispatchEvent:()=>{}},window:{}});
 vm.runInContext(raw.slice(a,b),ctx);
 assert.equal(vm.runInContext('typeof validateHKSnapshot',ctx),'function','HK daily schema guard is missing');
 return {validate:vm.runInContext('validateHKSnapshot',ctx),load:vm.runInContext('loadData',ctx),
  commit:vm.runInContext('commitChinaSnapshot',ctx)};
}
function dailyHK() {
 return {market:'hk',map_type:'stocks',source:'daily-close',asof:'2026-10-16',generated_utc:'2026-10-16 12:00',
  n_tiles:2,default_tf:'1D',timeframes:[{key:'1D',available:true}],sectors:[{key:'Tech',en:'Tech',zh:'科技'}],
  tiles:[{t:'0700.HK',sector:'Tech',size:10,perf:{'1D':2}},{t:'9988.HK',sector:'Tech',size:8,perf:{'1D':null}}]};
}
test('HK daily validator refuses foreign, duplicate, malformed or fabricated-zero inputs',()=>{
 const api=snapshotApi();assert.equal(api.validate(dailyHK()).tiles.length,2);
 for(const change of [d=>d.market='china',d=>d.asof='2026-02-30',d=>d.tiles[1].t='0700.HK',
  d=>d.n_tiles=999,d=>d.tiles[0].perf['1D']='0',d=>d.tiles[0].size=Infinity,d=>d.asof='2099-01-01',d=>d.generated_utc='2099-01-01 12:00']) {
  const d=dailyHK();change(d);assert.throws(()=>api.validate(d));
 }
});
test('HK member 401 is retryable after login and does not poison the shared promise cache',async()=>{
 let calls=0;
 const api=snapshotApi(()=>{calls++;return Promise.resolve(calls===1?{ok:false,status:401}:{ok:true,status:200,json:async()=>dailyHK()})});
 await assert.rejects(api.load('marketdata/hk_heatmap.json'),e=>e.status===401);
 assert.equal((await api.load('marketdata/hk_heatmap.json')).market,'hk');assert.equal(calls,2);
});
test('HK same-session corrections update atomically without allowing a backward daily session',()=>{
 const api=snapshotApi(),current=dailyHK(),correction=dailyHK();correction.tiles[0].perf['1D']=3;
 assert.equal(api.commit(current,correction,'marketdata/hk_heatmap.json'),true);
 assert.equal(current.tiles[0].perf['1D'],3);
 const older=dailyHK();older.asof='2026-10-15';older.generated_utc='2026-10-18 12:00';
 assert.equal(api.commit(current,older,'marketdata/hk_heatmap.json'),false);
 assert.equal(current.asof,'2026-10-16');
});
test('member failures expose an explicit retry and preserve the public summary',()=>{
 assert.match(source(),/data-hm-retry/);assert.match(source(),/Sign in to load/);
});
