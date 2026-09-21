'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');
const {harness,payload,clone,flush}=require('./china_heatmap_refresh_harness.cjs');
async function setup(fresh,first=payload()) {const h=harness([first,fresh]);const data=await h.load();h.start();return {h,data};}

test('old session cannot overwrite a newer session even with newer generation stamp',async()=>{
 const {h,data}=await setup(payload({asof:'2026-09-09',generated_utc:'2026-09-19 10:00'}));
 await h.tick();assert.equal(data.asof,'2026-09-18');assert.equal(h.events.length,0);
});
test('same-session correction with equal minute timestamp is rendered',async()=>{
 const corrected=payload();corrected.tiles[0].perf['1D']=5;
 const {h,data}=await setup(corrected);await h.tick();assert.equal(data.tiles[0].perf['1D'],5);assert.equal(h.events.length,1);
});
test('older same-session generation cannot overwrite newer accepted content',async()=>{
 const corrected=payload({generated_utc:'2026-09-18 15:39'});corrected.tiles[0].perf['1D']=5;
 const {h,data}=await setup(corrected);await h.tick();assert.equal(data.tiles[0].perf['1D'],1);assert.equal(h.events.length,0);
});
test('removing optional board breadth really removes it',async()=>{
 const {h,data}=await setup(payload({asof:'2026-09-21',generated_utc:'2026-09-21 10:00'}),
  payload({board_breadth:{n:10,adv:5,dec:4,flat:1,pct_up:50}}));
 await h.tick();assert.equal(Object.hasOwn(data,'board_breadth'),false);
});
test('removing optional non-contract metadata does not leave stale data',async()=>{
 const {h,data}=await setup(payload({generated_utc:'2026-09-18 15:41'}),payload({sector_read:{summary:'prior snapshot'}}));
 await h.tick();assert.equal(Object.hasOwn(data,'sector_read'),false);
});
test('all observers retain root identity and see complete matching snapshot',async()=>{
 const corrected=payload({generated_utc:'2026-09-18 15:41'});corrected.tiles[0].perf['1D']=8;
 const {h,data}=await setup(corrected,payload({board_breadth:{n:10,adv:5,dec:4,flat:1,pct_up:50}}));
 data._tf='1W';const alias=await h.load();const observations=[];
 h.context.onEvent=()=>observations.push({oldBoard:'board_breadth' in data,pc:data.tiles[0].perf['1D'],tf:data._tf});
 await h.tick();assert.equal(alias,data);assert.deepEqual(observations,[{oldBoard:false,pc:8,tf:'1W'}]);assert.equal(data._url,h.url);
});
test('generation-only update does not redraw identical content',async()=>{
 const {h,data}=await setup(payload({generated_utc:'2026-09-18 15:41'}));await h.tick();
 assert.equal(h.events.length,0);assert.equal(data.generated_utc,'2026-09-18 15:41');
});
test('object property order does not manufacture a semantic revision',async()=>{
 const f=payload();f.tiles[0].perf={'1W':3,'1D':1};
 const {h}=await setup(f);await h.tick();assert.equal(h.events.length,0);
});
test('zero is a real correction and never becomes missing',async()=>{
 const f=payload();f.tiles[0].perf['1D']=0;
 const {h,data}=await setup(f);await h.tick();assert.equal(data.tiles[0].perf['1D'],0);assert.equal(h.events.length,1);
});
test('missing observation correction stays null not zero',async()=>{
 const f=payload();f.tiles[0].perf['1D']=null;
 const {h,data}=await setup(f);await h.tick();assert.equal(data.tiles[0].perf['1D'],null);assert.equal(h.events.length,1);
});
for(const [label,mutate] of [
 ['wrong market',f=>{f.market='hk';}],['wrong source',f=>{f.source='polygon-live';}],
 ['wrong map',f=>{f.map_type='themes';}],['impossible day',f=>{f.asof='2026-02-30';}],
 ['missing generation',f=>{delete f.generated_utc;}],['invalid generation',f=>{f.generated_utc='not-a-date';}],
 ['generation predates observation',f=>{f.generated_utc='2026-09-17 15:40';}],
 ['duplicate ticker',f=>{f.tiles[1].t='A';}],['empty ticker',f=>{f.tiles[1].t=' ';}],
 ['missing count',f=>{delete f.n_tiles;}],['wrong count',f=>{f.n_tiles=4;}],
 ['numeric text return',f=>{f.tiles[0].perf['1D']='7';}],['boolean return',f=>{f.tiles[0].perf['1D']=true;}],
 ['negative tile size',f=>{f.tiles[0].size=-1;}],['missing performance object',f=>{delete f.tiles[0].perf;}],
 ['injected client timeframe',f=>{f._tf='1Y';}],['injected URL',f=>{f._url='other';}],
 ['invalid optional board',f=>{f.board_breadth={n:10,adv:8,dec:8,flat:0,pct_up:80};}],
 ['prototype key',f=>{Object.defineProperty(f,'__proto__',{value:{polluted:true},enumerable:true});}],
]) {
 test(`invalid refresh (${label}) keeps accepted data and emits no repaint`,async()=>{
  const f=payload({generated_utc:'2026-09-18 15:41'});mutate(f);
  const {h,data}=await setup(f);const before=JSON.stringify(data);await h.tick();assert.equal(JSON.stringify(data),before);assert.equal(h.events.length,0);
 });
}
test('empty replacement retains last-known content without relabelling it',async()=>{
 const {h,data}=await setup(payload({tiles:[],n_tiles:0,generated_utc:'2026-09-18 15:41'}));
 await h.tick();assert.equal(data.n_tiles,2);assert.equal(data.generated_utc,'2026-09-18 15:40');
});
test('a failed initial load does not permanently poison cached promise',async()=>{
 const h=harness([new Error('network'),payload()]);await assert.rejects(h.load());const good=await h.load();assert.equal(good.n_tiles,2);assert.equal(h.calls.length,2);
});
test('invalid first snapshot is not accepted as China data',async()=>{
 const h=harness([payload({market:'hk'})]);await assert.rejects(h.load());
});
test('transient refresh failure is followed by successful later refresh',async()=>{
 const f=payload();f.tiles[0].perf['1D']=9;
 const h=harness([payload(),new Error('network'),f]);const d=await h.load();h.start();await h.tick();assert.equal(d.tiles[0].perf['1D'],1);await h.tick();assert.equal(d.tiles[0].perf['1D'],9);
});
test('two timer ticks cannot open overlapping China requests',async()=>{
 let resolve;const deferred=new Promise(r=>resolve=r);
 const h=harness([payload(),()=>deferred,payload()]);const d=await h.load();h.start();await h.tick();await h.tick();assert.equal(h.calls.length,2);
 resolve({ok:true,json:async()=>payload({generated_utc:'2026-09-18 15:41'})});await flush();assert.equal(d.generated_utc,'2026-09-18 15:41');
});
test('hung refresh is aborted, keeps last data, and later tick can recover',async()=>{
 let signal;const f=payload();f.tiles[0].perf['1D']=3;
 const h=harness([payload(),opts=>{signal=opts.signal;return new Promise(()=>{});},f]);
 const d=await h.load();h.start();await h.tick();await h.timeout();assert.equal(signal.aborted,true);assert.equal(d.tiles[0].perf['1D'],1);
 await h.tick();assert.equal(d.tiles[0].perf['1D'],3);
});
test('late response after timeout cannot mutate accepted snapshot',async()=>{
 let resolve;const f=payload();f.tiles[0].perf['1D']=3;
 const h=harness([payload(),()=>new Promise(r=>resolve=r),f]);const d=await h.load();h.start();await h.tick();await h.timeout();await h.tick();
 resolve({ok:true,json:async()=>payload({asof:'2026-09-09',generated_utc:'2026-09-19 10:00'})});await flush();assert.equal(d.asof,'2026-09-18');assert.equal(d.tiles[0].perf['1D'],3);
});
test('one refresher remains owned per URL',async()=>{
 const h=harness([payload()]);await h.load();h.start();h.start();assert.equal(h.intervals.length,1);
});
test('hidden tabs do not fetch',async()=>{
 const h=harness([payload()]);await h.load();h.start();h.context.document.hidden=true;await h.tick();assert.equal(h.calls.length,1);
});
test('query-string China URL is still identity-validated',async()=>{
 const h=harness([payload({market:'hk'})]);await assert.rejects(h.load('marketdata/china_heatmap.json?v=1'));
});
for(const [market,url] of [['us','marketdata/sp500_heatmap.json'],['hk','marketdata/hk_heatmap.json'],['canada','marketdata/canada_heatmap.json']]){
 test(`${market} legacy refresh remains timestamp-driven and does not use China validation`,async()=>{
  const first={market,tiles:[{t:'A'}],generated_utc:'1'};const second={market,tiles:[{t:'B'}],generated_utc:'2'};
  const h=harness([first,second]);const d=await h.load(url);h.start(url);await h.tick();assert.equal(d.tiles[0].t,'B');assert.equal(h.events.length,1);
 });
}
for(const [label,mutate] of [
 ['timeframes is object',f=>{f.timeframes={};}],
 ['timeframe has no identity',f=>{f.timeframes=[{available:true}];}],
 ['timeframe availability is string',f=>{f.timeframes[0].available='true';}],
 ['duplicate timeframe',f=>{f.timeframes.push({...f.timeframes[0]});}],
 ['sectors is object',f=>{f.sectors={};}],
 ['sector has no identity',f=>{f.sectors=[{en:'Unknown'}];}],
 ['duplicate sector',f=>{f.sectors.push({...f.sectors[0]});}],
 ['default timeframe missing from catalog',f=>{f.default_tf='BAD';}],
]) {
 test(`render-critical shape (${label}) is rejected before committing`,async()=>{
  const f=payload({generated_utc:'2026-09-18 15:41'});mutate(f);const {h,data}=await setup(f);const before=JSON.stringify(data);await h.tick();assert.equal(JSON.stringify(data),before);assert.equal(h.events.length,0);
 });
}
test('overflow JSON numeric values cannot enter a snapshot',async()=>{
 const broken=payload({generated_utc:'2026-09-18 15:41'});broken.tiles[0].perf['1D']=Infinity;
 const {h,data}=await setup(()=>({ok:true,json:async()=>broken}));await h.tick();assert.equal(data.tiles[0].perf['1D'],1);
});
test('JSON body read timeout is bounded as well as response headers',async()=>{
 const f=payload();f.tiles[0].perf['1D']=4;
 const h=harness([payload(),()=>({ok:true,json:()=>new Promise(()=>{})}),f]);const d=await h.load();h.start();await h.tick();await h.timeout();await h.tick();assert.equal(d.tiles[0].perf['1D'],4);
});
test('first-load timeout is evicted and can retry without new timers',async()=>{
 const h=harness([()=>new Promise(()=>{}),payload()]);const initial=h.load();const rejected=assert.rejects(initial);await h.flush();await h.timeout();await rejected;const d=await h.load();assert.equal(d.n_tiles,2);assert.equal(h.timers.size,0);
});
test('non-OK status response preserves old data',async()=>{
 const {h,data}=await setup(()=>({ok:false,status:503,json:async()=>payload()}));await h.tick();assert.equal(data.generated_utc,'2026-09-18 15:40');assert.equal(h.events.length,0);
});
test('syntax error parsing JSON preserves old data',async()=>{
 const {h,data}=await setup(()=>({ok:true,json:async()=>{throw new SyntaxError('bad json');}}));await h.tick();assert.equal(data.generated_utc,'2026-09-18 15:40');assert.equal(h.events.length,0);
});
test('overlapping mounts share one initial request and same state object',async()=>{
 const h=harness([payload()]);const [a,b]=await Promise.all([h.load(),h.load()]);assert.equal(a,b);assert.equal(h.calls.length,1);
});
test('new payload private arbitrary state is not reflected to client',async()=>{
 const {h,data}=await setup(payload({_isFresh:true,generated_utc:'2026-09-18 15:41'}));await h.tick();assert.equal(data._isFresh,undefined);assert.equal(data.generated_utc,'2026-09-18 15:40');
});
