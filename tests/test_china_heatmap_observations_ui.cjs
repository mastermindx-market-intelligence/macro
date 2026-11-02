const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const test=require('node:test'),assert=require('node:assert/strict');
const target=process.env.HEATMAP_SOURCE || path.join(__dirname,'../templates/heatmap.js');
function load(){
 const c={esc:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;'),
  L:(en,zh)=>`<span class="l-en">${en}</span><span class="l-zh">${zh}</span>`};
 const source=fs.readFileSync(target,'utf8');
 const a=source.indexOf('  // BEGIN CN_OBSERVATION_TRUTH'),b=source.indexOf('  // END CN_OBSERVATION_TRUTH');
 assert.ok(a>=0 && b>a,'Observation helpers are wired into the existing renderer');
 vm.createContext(c);vm.runInContext(source.slice(a,b),c);return c;
}
const data={market:'china',_tf:'1D',default_tf:'1D'};
const tile=(status='CURRENT_MISSING')=>({perf:{'1D':null},observation:{schema:'china_heatmap_observations.v1',observation_session:'2026-09-18',last_observed_session:'2026-09-17',timeframes:{'1D':{status,observation_session:'2026-09-18',reference_session:'2026-09-17'}}}});
test('missing current quote discloses last observation, never suspended',()=>{
 const s=load().observationHtml(data,tile());assert.match(s,/Current-session return unavailable/);assert.match(s,/Last observation: 2026-09-17/);assert.doesNotMatch(s,/suspend|停牌/i);
});
test('missing reference labels reference rather than assuming missing today',()=>{const s=load().observationHtml(data,tile('REFERENCE_MISSING'));assert.match(s,/Reference-session quote unavailable/);assert.match(s,/2026-09-17/);});
test('valid zero remains a valid interval',()=>{const t=tile('VALID');t.perf['1D']=0.;const s=load().observationHtml(data,t);assert.match(s,/2026-09-17.*2026-09-18/);assert.doesNotMatch(s,/unavailable/);});
test('never observed uses explicit wording',()=>{const t=tile();t.observation.last_observed_session=null;assert.match(load().observationHtml(data,t),/No valid observation in supplied history/);});
test('invalid prices have unusable quote disclosure',()=>assert.match(load().observationHtml(data,tile('CURRENT_INVALID')),/unusable/));
test('unknown schema refuses precision',()=>{const t=tile();t.observation.schema='other';assert.match(load().observationHtml(data,t),/metadata unavailable/);});
test('legacy payloads remain untouched',()=>assert.equal(load().observationHtml(data,{perf:{'1D':2}}),''));
test('other markets remain untouched',()=>assert.equal(load().observationHtml({...data,market:'hk'},tile()),''));
test('hostile date content cannot inject HTML',()=>{const t=tile();t.observation.last_observed_session='<img src=x onerror=alert(1)>';const s=load().observationHtml(data,t);assert.doesNotMatch(s,/<img|onerror/);});
test('malformed valid state with null return cannot claim valid interval',()=>assert.match(load().observationHtml(data,tile('VALID')),/unavailable/));
test('selected timeframe uses its own reference',()=>{const t=tile();t.perf['1W']=2;t.observation.timeframes['1W']={status:'VALID',observation_session:'2026-09-18',reference_session:'2026-09-11'};assert.match(load().observationHtml({...data,_tf:'1W'},t),/2026-09-11/);});
test('coverage exposes member denominator and missing names',()=>{
 const d={...data,observation_coverage:{basis:'current_membership',membership_count:1706,timeframes:{'1D':{denominator:1706,valid_count:1700,missing_count:6}}}};
 const s=load().observationCoverageHtml(d,'1D');assert.match(s,/1700 \/ 1706/);assert.match(s,/6 unavailable/);assert.match(s,/1700 \/ 1706 个标的具备有效区间行情/);assert.match(s,/6 个不可用/);
});
test('bad coverage accounting is not displayed as success',()=>{const d={...data,observation_coverage:{membership_count:3,timeframes:{'1D':{denominator:3,valid_count:4,missing_count:-1}}}};assert.match(load().observationCoverageHtml(d,'1D'),/coverage unavailable/);});
test('coverage is not automatically inherited by other markets',()=>assert.equal(load().observationCoverageHtml({market:'hk'},'1D'),''));
test('future last observation cannot be presented as historical evidence',()=>{const t=tile();t.observation.last_observed_session='2026-09-21';assert.match(load().observationHtml(data,t),/metadata unavailable/);});
test('reference cannot be after the current endpoint',()=>{const t=tile();t.observation.timeframes['1D'].reference_session='2026-09-21';assert.match(load().observationHtml(data,t),/metadata unavailable/);});
test('tile session must agree with payload session',()=>assert.match(load().observationHtml({...data,asof:'2026-09-21'},tile()),/metadata unavailable/));
