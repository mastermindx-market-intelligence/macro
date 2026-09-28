'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');
const {harness,base,live,clone,NOW}=require('./china_heatmap_live_refresh_harness.cjs');

function registered(h,b=base()) {b._url='marketdata/china_heatmap.json';h.start(b);return b;}

test('valid live snapshot adopts outside the canonical daily object',()=>{
 const h=harness(),b=registered(h),p=live();
 const checked=h.validate(p,b);assert.equal(checked.usable,true);
 assert.equal(h.commit(b._url,p),true);assert.equal(h.events.length,1);
 assert.equal(h.events[0].type,'hm-live-refresh');assert.equal(h.events[0].detail.url,b._url);
 assert.equal(h.meta(b).source,'tushare-rt-k');assert.equal(h.value(b,b.tiles[0],'1D'),p.quotes['600519.SS'].changePct);
 assert.equal(h.value(b,b.tiles[0],'1W'),3);assert.equal(Object.hasOwn(b,'live'),false);
});

test('uncovered name is null only while a usable live overlay is active',()=>{
 const h=harness(),b=registered(h),p=live();delete p.quotes['000001.SZ'];p.resolved=1;p.coverage=.5;p.usable=false;p.breadth={n:1,adv:1,dec:0,flat:0,pctUp:100};
 assert.equal(h.commit(b._url,p),true);assert.equal(h.value(b,b.tiles[1],'1D'),-1);
 const good=live();assert.equal(h.commit(b._url,good),true);delete h.context.api._chinaLiveStates[b._url].data.quotes['000001.SZ'];
 assert.equal(h.value(b,b.tiles[1],'1D'),null);
});

for(const [label,mutate] of [
 ['wrong schema',p=>p.schema='bad'],['wrong market',p=>p.market='hk'],['wrong baseline',p=>p.baseline_asof='2026-09-23'],
 ['malformed date',p=>p.session_date='2026-02-30'],['future heartbeat',p=>p.generated_at='2026-09-28T02:15:50+00:00'],
 ['stale heartbeat',p=>p.generated_at='2026-09-28T02:13:00+00:00'],['count drift',p=>p.requested=3],
 ['coverage drift',p=>p.coverage=.5],['breadth drift',p=>p.breadth.adv=2],
 ['foreign quote',p=>p.quotes['600000.SS']=clone(p.quotes['600519.SS'])],
 ['noncanonical duplicate',p=>p.quotes['600519.ss']=clone(p.quotes['600519.SS'])],
 ['wrong percentage',p=>p.quotes['600519.SS'].changePct=99],['leaky field',p=>p.vendor_body={secret:true}],
]) test(`invalid live contract (${label}) is rejected`,()=>{const h=harness(),b=base(),p=live();mutate(p);assert.throws(()=>h.validate(p,b));});

test('running phases reject a stale source even under a fresh producer heartbeat',()=>{
 const h=harness(),b=base(),p=live({source_observed_at:'2026-09-28T02:12:00+00:00'});
 for(const q of Object.values(p.quotes))q.ts=Date.parse('2026-09-28T02:12:00Z');
 assert.throws(()=>h.validate(p,b));
});

test('source-clock regression cannot replace accepted state',()=>{
 const h=harness(),b=registered(h),first=live();assert.equal(h.commit(b._url,first),true);
 const older=live({generated_at:'2026-09-28T02:15:41+00:00',source_observed_at:'2026-09-28T02:15:20+00:00'});
 for(const q of Object.values(older.quotes))q.ts=Date.parse('2026-09-28T02:15:20Z');
 assert.equal(h.commit(b._url,older),false);assert.equal(h.meta(b).source_observed_at,first.source_observed_at);assert.equal(h.events.length,1);
});


test('one refresher owner is shared across overlapping mounts',()=>{
 const h=harness([live()]),b=base();b._url='marketdata/china_heatmap.json';
 const first=h.start(b),second=h.start(b);assert.equal(first,second);assert.equal(h.timers.size,1);
});

test('running snapshot fetches immediately then schedules two seconds',async()=>{
 const h=harness([live()]),b=registered(h);
 assert.equal(await h.runTimer(t=>t.delay===0),0);assert.equal(h.calls.length,1);
 assert.match(h.calls[0].url,/^live\/china_heatmap\.json\?hm_live=/);assert.equal(h.calls[0].opts.cache,'no-store');
 assert.equal(h.meta(b).phase,'morning');assert.equal([...h.timers.values()][0].delay,2000);
});

test('break snapshot uses heartbeat cadence without treating the source as stale',async()=>{
 const p=live({phase:'session_break',status:'break',generated_at:'2026-09-28T04:00:00Z',source_observed_at:'2026-09-28T03:29:59Z'});
 for(const q of Object.values(p.quotes))q.ts=Date.parse(p.source_observed_at);
 const h=harness([p]),b=registered(h);h.setNow(Date.parse(p.generated_at));
 await h.runTimer(t=>t.delay===0);assert.equal(h.meta(b).status,'break');assert.equal([...h.timers.values()][0].delay,30000);
});

test('hidden tabs do not fetch and stay on idle cadence',async()=>{
 const h=harness([live()]),b=registered(h);h.context.document.hidden=true;
 await h.runTimer(t=>t.delay===0);assert.equal(h.calls.length,0);assert.equal([...h.timers.values()][0].delay,30000);
});

test('an in-flight request owns the lane until it resolves or times out',async()=>{
 let resolve;const h=harness([()=>new Promise(r=>resolve=r)]),b=registered(h);
 await h.runTimer(t=>t.delay===0);assert.equal(h.calls.length,1);assert.notEqual(h.start(b).inFlight,null);
 assert.equal([...h.timers.values()].filter(t=>t.delay===5000).length,1);
 resolve({ok:true,status:200,json:async()=>live()});await h.flush();assert.equal(h.meta(b).phase,'morning');
});

test('timed-out request aborts and a later cadence recovers',async()=>{
 let signal;const h=harness([opts=>{signal=opts.signal;return new Promise(()=>{});},live()]),b=registered(h);
 await h.runTimer(t=>t.delay===0);await h.runTimer(t=>t.delay===5000);assert.equal(signal.aborted,true);assert.equal(h.meta(b),null);
 assert.equal([...h.timers.values()][0].delay,30000);await h.runTimer(t=>t.delay===30000);assert.equal(h.meta(b).source,'tushare-rt-k');
});

test('transient transport failure retries without destroying accepted state',async()=>{
 const h=harness([live(),new Error('network'),live({generated_at:'2026-09-28T02:15:41+00:00'})]),b=registered(h);
 await h.runTimer(t=>t.delay===0);const accepted=h.meta(b).source_observed_at;
 await h.runTimer(t=>t.delay===2000);assert.equal(h.meta(b).source_observed_at,accepted);
 await h.runTimer(t=>t.delay===2000);assert.equal(h.meta(b).source_observed_at,accepted);
});


test('one fresh name cannot bless a stale neighbor',()=>{
 const h=harness(),p=live();p.quotes['000001.SZ'].ts-=86400000;
 assert.throws(()=>h.validate(p,base()),/clock|fresh|quote|usab/i);
});
test('source expiry removes live values even while producer heartbeat is recent',()=>{
 const h=harness(),b=base();h.start(b);h.commit('marketdata/china_heatmap.json',live());
 h.setNow(NOW+36000);assert.equal(h.value(b,b.tiles[0],'1D'),b.tiles[0].perf['1D']);
});
test('failed poll emits the transition to daily fallback without a new payload',async()=>{
 const h=harness([new Error('offline')]),b=base();h.start(b);h.commit('marketdata/china_heatmap.json',live());
 const count=h.events.length;h.setNow(NOW+36000);await h.runTimer(t=>t.delay===0);
 assert.equal(h.events.length,count+1);assert.equal(h.value(b,b.tiles[0],'1D'),1);
});
test('explicit unavailable response clears a live claim immediately',()=>{
 const h=harness(),b=base();h.start(b);h.commit('marketdata/china_heatmap.json',live());
 h.setNow(NOW+2000);
 const p=live({generated_at:'2026-09-28T02:15:42Z',source:null,status:'unavailable',source_observed_at:null,quotes:{},resolved:0,coverage:0,usable:false,breadth:{n:0,adv:0,dec:0,flat:0,pctUp:0}});
 assert.equal(h.commit('marketdata/china_heatmap.json',p),true);
 assert.equal(h.value(b,b.tiles[0],'1D'),1);
});
test('individual quote cannot regress inside a batch with a newer maximum timestamp',()=>{
 const h=harness(),b=base();h.start(b);h.commit('marketdata/china_heatmap.json',live());
 const p=live({generated_at:'2026-09-28T02:15:41Z',source_observed_at:'2026-09-28T02:15:31Z'});
 p.quotes['600519.SS'].ts+=1000;p.quotes['000001.SZ'].ts-=1000;
 assert.equal(h.commit('marketdata/china_heatmap.json',p),false);
});


test('a break label cannot excuse a quote from the prior trading day',()=>{
 const h=harness(),p=live({phase:'session_break',status:'break',generated_at:'2026-09-28T04:00:00Z',source_observed_at:'2026-09-24T07:00:00Z'});
 for(const q of Object.values(p.quotes))q.ts=Date.parse(p.source_observed_at);
 h.setNow(Date.parse(p.generated_at));assert.throws(()=>h.validate(p,base()));
});
test('a morning label expires at the lunch boundary even with a recent heartbeat',()=>{
 const h=harness(),b=base(),p=live({generated_at:'2026-09-28T03:29:59Z',source_observed_at:'2026-09-28T03:29:58Z'});
 for(const q of Object.values(p.quotes))q.ts=Date.parse(p.source_observed_at);
 h.setNow(Date.parse(p.generated_at));h.start(b);h.commit('marketdata/china_heatmap.json',p);
 h.setNow(Date.parse('2026-09-28T03:30:01Z'));assert.equal(h.value(b,b.tiles[0],'1D'),1);
});
test('valid but wrong session date cannot be called live',()=>{
 const h=harness(),p=live({session_date:'2026-09-29'});assert.throws(()=>h.validate(p,base()));
});
