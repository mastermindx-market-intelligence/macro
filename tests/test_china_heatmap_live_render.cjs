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

test('China leaves the legacy live.js hidden-span overlay while HK and Canada retain it',()=>{
 const raw=source();
 const map=/var _LIVE_MKT\s*=\s*\{([^}]+)\}/.exec(raw);
 assert.ok(map,'legacy market map missing');
 assert.doesNotMatch(map[1],/china\s*:/);
 assert.match(map[1],/hk\s*:\s*'hk'/);
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
