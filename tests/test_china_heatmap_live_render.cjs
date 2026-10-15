'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const source=()=>fs.readFileSync(process.env.LIVE_RENDER_SOURCE||path.join(__dirname,'../templates/heatmap.js'),'utf8');

function helperApi(liveByTicker={}){
 const raw=source();
 const start=raw.indexOf('  function heatmapValue(');
 const end=raw.indexOf('  function sectorLabels(',start);
 assert.ok(start>=0&&end>start,'shared live-value helper boundary missing');
 const context={Math,Number,Array,Object,isNaN,chinaLiveValue:(data,tile,tf)=>tf==='1D'?(Object.hasOwn(liveByTicker,tile.t)?liveByTicker[tile.t]:null):tile.perf[tf]};
 vm.createContext(context);
 vm.runInContext(raw.slice(start,end)+'\nglobalThis.api={heatmapValue,medianPc,weightedPc,sectorAgg,breadth};',context);
 return context.api;
}

test('shared aggregators consume one live 1D value path while longer windows stay daily',()=>{
 const api=helperApi({'A':5,'B':-1});
 const data={market:'china',size_basis:'marketcap'};
 const tiles=[{t:'A',size:3,perf:{'1D':1,'1W':10}},{t:'B',size:1,perf:{'1D':2,'1W':2}}];
 assert.equal(api.heatmapValue(data,tiles[0],'1D'),5);
 assert.equal(api.heatmapValue(data,tiles[0],'1W'),10);
 assert.equal(api.medianPc(data,tiles,'1D'),2);
 assert.equal(api.weightedPc(data,tiles,'1D'),3.5);
 assert.equal(api.sectorAgg(data,tiles,'1D'),3.5);
 assert.deepEqual({...api.breadth(data,tiles,'1D')},{adv:1,dec:1});
});

test('uncovered live name remains null and is excluded from live aggregates',()=>{
 const api=helperApi({'A':5});
 const data={market:'china',size_basis:'marketcap'};
 const tiles=[{t:'A',size:3,perf:{'1D':1,'1W':10}},{t:'B',size:1,perf:{'1D':2,'1W':2}}];
 assert.equal(api.heatmapValue(data,tiles[1],'1D'),null);
 assert.equal(api.medianPc(data,tiles,'1D'),5);
 assert.equal(api.weightedPc(data,tiles,'1D'),5);
 assert.deepEqual({...api.breadth(data,tiles,'1D')},{adv:1,dec:0});
});

test('China and HK use coherent overlays, while Canada retains legacy hidden spans',()=>{
 const raw=source();
 const map=/var _LIVE_MKT\s*=\s*\{([^}]+)\}/.exec(raw);
 assert.ok(map,'legacy market map missing');
 assert.doesNotMatch(map[1],/china\s*:/);
 assert.doesNotMatch(map[1],/hk\s*:/);
 assert.match(map[1],/canada\s*:\s*'ca'/);
});

test('every live-sensitive surface is wired to heatmapValue and shared refresh events',()=>{
 const raw=source();
 for(const marker of [
  'heatmapValue(data, t, tf)',
  'heatmapValue(data, t, TF)',
  'heatmapValue(data, rec.t, TF)',
  'heatmapValue(data, tile, tf)',
  'chinaLiveDescriptor(data)',
  "document.addEventListener('hm-live-refresh'",
  'startChinaLiveRefresh(data)'
 ]) assert.ok(raw.includes(marker),`missing ${marker}`);
 assert.ok((raw.match(/document\.addEventListener\('hm-live-refresh'/g)||[]).length>=2,'full and scorecard listeners required');
 assert.ok((raw.match(/startChinaLiveRefresh\(data\)/g)||[]).length>=2,'full and scorecard live owners required');
});

test('source copy distinguishes live break auction closed degraded and daily states with coverage',()=>{
 const raw=source();
 const start=raw.indexOf('  function chinaLiveDescriptor(');
 const end=raw.indexOf('\n  function ',start+10);
 assert.ok(start>=0&&end>start,'China live descriptor missing');
 const block=raw.slice(start,end);
 for(const word of ['morning','afternoon','session_break','closing_auction','closed','degraded','resolved','requested','CST']){
  assert.ok(block.includes(word),`descriptor missing ${word}`);
 }
});

test('critical renderer blocks no longer read China 1D directly from tile.perf',()=>{
 const raw=source();
 const regions=[
  ['function cardBaseHtml(', 'function enrichCard('],
  ['function showMembers(', 'function showSubMembers('],
  ['function tileLabel(t, tw, th)', 'function layoutTree('],
  ['function layoutStocksFlat(', 'function layoutList('],
  ['function computeSummary(', 'function renderDash('],
  ['function renderScorecard(', '/* ====================================================================== */\n  /*  OVERLAY']
 ];
 for(const [from,to] of regions){
  const a=raw.indexOf(from),b=raw.indexOf(to,a+1);assert.ok(a>=0&&b>a,`region missing ${from}`);
  const block=raw.slice(a,b);
  assert.doesNotMatch(block,/\b(?:t|tile|rec\.t)\.perf\[(?:tf|TF|data\._tf)\]/,`direct 1D-capable perf read remains in ${from}`);
 }
});

function integrityApi(){
 const src=source();
 const a=src.indexOf('  function dailyIntegrityDescriptor(');
 const b=src.indexOf('  function hkLiveDescriptor(',a);
 const c=src.indexOf('  function startHKLiveRefresh(',b);
 const d=src.indexOf('  function chinaLiveDescriptor(');
 const e=src.indexOf('  function sectorLabels(',d);
 assert.ok(a>=0&&b>a&&c>b&&d>=0&&e>d,'daily evidence/descriptor boundaries absent');
 const ctx={Number,Math,Array,Object,isFinite,Date,
   chinaLiveMeta:()=>null,hkLiveMeta:()=>null};
 vm.createContext(ctx);
 vm.runInContext(
   src.slice(a,c)+'\n'+src.slice(d,e)
   +'\nglobalThis.integrity={dailyIntegrityDescriptor,chinaLiveDescriptor,hkLiveDescriptor};',
   ctx
 );
 return ctx.integrity;
}

function dailyFixture(market,values,declared=values.filter(x=>x!==null).length){
 const d={market,map_type:'stocks',source:'daily-close',asof:'2026-10-13',
   n_tiles:values.length,
   tiles:values.map((value,i)=>({t:String(i),perf:{'1D':value}}))};
 if(market==='china') d.observation_coverage={
   membership_count:values.length,timeframes:{'1D':{
     valid_count:declared,denominator:values.length,
     missing_count:values.length-declared}}};
 return d;
}

test('zero-coverage China daily cannot masquerade as a settled heatmap',()=>{
 const api=integrityApi(),base=dailyFixture('china',Array(100).fill(null),0);
 const result=api.chinaLiveDescriptor(base);
 assert.equal(result.dot,'degraded');
 assert.match(result.en,/Daily returns unavailable.*0\/100.*2026-10-13/);
 assert.match(result.zh,/日线涨跌不可用.*0\/100/);
});

test('the daily fallback is truthful even if China tile values contradict declared coverage',()=>{
 const api=integrityApi(),base=dailyFixture('china',Array(100).fill(1.3),0);
 const result=api.dailyIntegrityDescriptor(base);
 assert.equal(result.dot,'degraded');
 assert.match(result.en,/0\/100/);
 delete base.observation_coverage;
 assert.match(api.chinaLiveDescriptor(base).en,/Daily returns unavailable/);
});

test('95% verified real daily observations remain eligible for China and HK',()=>{
 const api=integrityApi();
 const values=[...Array(95).fill(-0.2),...Array(5).fill(null)];
 const china=dailyFixture('china',values,95);
 const hk=dailyFixture('hk',values);
 assert.equal(api.dailyIntegrityDescriptor(china),null);
 assert.equal(api.dailyIntegrityDescriptor(hk),null);
 assert.match(api.chinaLiveDescriptor(china).en,/Daily close · 2026-10-13/);
 assert.match(api.hkLiveDescriptor(hk).en,/Daily close · 2026-10-13/);
});

test('Hong Kong no-live view discloses insufficient daily return coverage',()=>{
 const api=integrityApi(),hk=dailyFixture('hk',Array(100).fill(null));
 const d=api.hkLiveDescriptor(hk);
 assert.equal(d.dot,'degraded');
 assert.match(d.en,/Daily returns unavailable.*0\/100.*2026-10-13/);
 assert.match(d.zh,/日线涨跌不可用/);
});


function postCloseDescriptor(meta, asof='2026-10-14') {
 const raw=source();
 const a=raw.indexOf('  function chinaLiveDescriptor(');
 const b=raw.indexOf('  function sectorLabels(',a);
 assert.ok(a>=0&&b>a,'shared China descriptor source region absent');
 const ctx={
  Date,Math,Number,Object,isFinite,
  chinaLiveMeta:()=>meta,dailyIntegrityDescriptor:()=>null,
 };
 vm.createContext(ctx);
 vm.runInContext(raw.slice(a,b)+'\nglobalThis.describe=chinaLiveDescriptor;',ctx);
 return ctx.describe({market:'china',map_type:'stocks',asof});
}

test('post-close source on a prior baseline cannot pretend to be a settled EOD',()=>{
 const meta={
  usable:true,phase:'closed',source:'tencent',fallback:true,
  source_observed_at:'2026-10-15T07:00:00+00:00',
  baseline_asof:'2026-10-14',session_date:'2026-10-15',
  requested:100,resolved:98,breadth:{n:98,adv:10,dec:88,flat:0},
 };
 const d=postCloseDescriptor(meta);
 assert.equal(d.state,'closed');
 assert.match(d.en,/Provisional post-close · not yet settled/);
 assert.match(d.zh,/盘后临时行情 · 尚未确认收盘/);
 assert.match(d.en,/fallback feed.*15:00 CST.*98\/100/);
 assert.doesNotMatch(d.en,/Daily close|Market closed/);
});

test('current validated daily baseline returns the normal closed label',()=>{
 const meta={
  usable:true,phase:'closed',source:'tushare-rt-k',fallback:false,
  source_observed_at:'2026-10-15T07:00:00+00:00',
  baseline_asof:'2026-10-15',session_date:'2026-10-15',
  requested:100,resolved:100,breadth:{n:100,adv:20,dec:80,flat:0},
 };
 const d=postCloseDescriptor(meta,'2026-10-15');
 assert.equal(d.state,'closed');
 assert.match(d.en,/Market closed.*15:00 CST.*100\/100/);
 assert.match(d.zh,/已收盘/);
 assert.doesNotMatch(d.en,/Provisional|fallback feed/);
});

test('unverified post-close quote heartbeat declares pending rather than settled',()=>{
 const meta={
  usable:false,phase:'closed',source:'tencent',fallback:true,
  source_observed_at:null,baseline_asof:'2026-10-14',
  session_date:'2026-10-15',requested:100,resolved:0,
  breadth:{n:0,adv:0,dec:0,flat:0},
 };
 const d=postCloseDescriptor(meta);
 assert.equal(d.state,'degraded');
 assert.equal(d.dot,'degraded');
 assert.match(d.en,/Post-close pending · quotes unverified · 0\/100/);
 assert.match(d.en,/Last verified daily 2026-10-14/);
 assert.match(d.zh,/收盘数据待确认 · 行情未经验证/);
 assert.doesNotMatch(d.en,/Market closed|Daily close/);
});
