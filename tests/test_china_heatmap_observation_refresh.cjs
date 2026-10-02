'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
const {harness,clone,payload}=require('./china_heatmap_refresh_harness.cjs');
const base=()=>JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/china_heatmap_refresh/base_snapshot.json'),'utf8'));
const correction=()=>JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/china_heatmap_refresh/corrected_snapshot.json'),'utf8'));
const renderer=fs.readFileSync(process.env.HEATMAP_SOURCE || path.join(__dirname,'../templates/heatmap.js'),'utf8');
const begin=renderer.indexOf('// BEGIN CN_OBSERVATION_TRUTH'),end=renderer.indexOf('// END CN_OBSERVATION_TRUTH',begin);
if(begin<0||end<=begin)throw new Error('Apply observation-truth slice before this test');
const helpers=renderer.slice(begin,end);
const vm=require('node:vm');
function ui(h){vm.runInContext(`function esc(v){return String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;');} function L(a,b){return a+' | '+b;}\n`+helpers+'\nglobalThis.disclose={observationHtml,observationCoverageHtml};',h.context);return h.context.disclose;}
test('same-minute quote correction updates return, interval disclosure and coverage together',async()=>{
 const h=harness([base(),correction()]);const d=await h.load();d._tf='1D';h.start();const renderer=ui(h);
 assert.match(renderer.observationHtml(d,d.tiles[1]),/Last observation: 2026-09-17/);
 assert.match(renderer.observationCoverageHtml(d,'1D'),/2 \/ 5/);
 const events=[];h.context.onEvent=()=>events.push({value:d.tiles[1].perf['1D'],status:d.tiles[1].observation.timeframes['1D'].status,coverage:d.observation_coverage.timeframes['1D'].valid_count});
 await h.tick();assert.equal(d.tiles[1].perf['1D'],0.77);assert.equal(d.tiles[3].perf['1D'],0);
 assert.match(renderer.observationHtml(d,d.tiles[1]),/Observed return: 2026-09-17 → 2026-09-18/);
 assert.match(renderer.observationCoverageHtml(d,'1D'),/3 \/ 5/);
 assert.deepEqual(events,[{value:0.77,status:'VALID',coverage:3}]);
});
test('old source cannot downgrade an accepted observation-truth contract',async()=>{
 const h=harness([base(),payload({generated_utc:'2026-09-18 15:41'})]);const d=await h.load();h.start();await h.tick();
 assert.equal(d.n_tiles,5);assert.equal(d.generated_utc,'2026-09-18 15:40');assert.equal(d.tiles[1].perf['1D'],null);assert.equal(h.events.length,0);
});
for(const [label,mutate] of [
 ['missing tile metadata',f=>{delete f.tiles[0].observation;}],
 ['wrong observation session',f=>{f.tiles[0].observation.observation_session='2026-09-17';}],
 ['non-null return with missing status',f=>{f.tiles[1].perf['1D']=0.78;}],
 ['numeric return with null status',f=>{f.tiles[0].observation.timeframes['1D'].status='CURRENT_MISSING';}],
 ['valid current quote cannot claim a missing current endpoint',f=>{f.tiles[0].observation.timeframes['1D'].status='CURRENT_MISSING';f.tiles[0].perf['1D']=null;}],
 ['missing coverage',f=>{delete f.observation_coverage;}],
 ['invented coverage count',f=>{f.observation_coverage.timeframes['1D'].valid_count=4;f.observation_coverage.timeframes['1D'].missing_count=1;}],
 ['wrong denominator',f=>{f.observation_coverage.membership_count=4;}],
 ['wrong schema',f=>{f.tiles[0].observation.schema='invented';}],
 ['reference session after observation',f=>{f.tiles[0].observation.timeframes['1D'].reference_session='2026-09-21';}],
 ['unequal reference session',f=>{f.tiles[0].observation.timeframes['1D'].reference_session='2026-09-16';}],
 ['last observation after asof',f=>{f.tiles[0].observation.last_observed_session='2026-09-21';}],
]){
 test(`incoherent observation snapshot (${label}) never partially replaces current`,async()=>{
  const f=base();f.generated_utc='2026-09-18 15:41';mutate(f);
  const h=harness([base(),f]);const d=await h.load();h.start();const before=JSON.stringify(d);await h.tick();assert.equal(JSON.stringify(d),before);assert.equal(h.events.length,0);
 });
}
test('legacy payload can upgrade to complete observation metadata',async()=>{
 const h=harness([payload(),base()]);const d=await h.load();h.start();await h.tick();assert.equal(d.n_tiles,5);assert.equal(d.observation_coverage.membership_count,5);assert.equal(h.events.length,1);
});
