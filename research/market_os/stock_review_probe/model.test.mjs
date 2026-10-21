import test from 'node:test';
import assert from 'node:assert/strict';
import {fixtures,filterRows,sortRows,counts,createState,reduce,inspected} from './review-model.mjs';
const sample = [
 {id:'US:A:USD',symbol:'A',name:'Alpha',lane:'Almost ready',price:0,change:0,volume:1.4},
 {id:'HK:A:HKD',symbol:'A',name:'Alpha Hong Kong',lane:'Stand aside',price:null,change:null,volume:null},
 {id:'US:B:USD',symbol:'B',name:'Beta',lane:'In favour',price:20,change:-1,volume:2},
 {id:'US:C:USD',symbol:'C',name:'Gamma',lane:'Almost ready',price:10,change:1,volume:1.4}
];
const init=()=>createState(sample);
const apply=(s,...events)=>events.reduce(reduce,s);
test('fixture contains six distinct identities with one null quote',()=>{assert.equal(fixtures.length,6); assert.equal(new Set(fixtures.map(x=>x.id)).size,6);assert.equal(fixtures.filter(x=>x.price===null).length,1);});
test('search matches normalized symbol/name without regex evaluation',()=>{assert.deepEqual(filterRows(sample,{query:'  ALPHA '}),sample.slice(0,2));assert.deepEqual(filterRows(sample,{query:'.*'}),[]);});
test('search and lane compose rather than replacing one another',()=>{assert.deepEqual(filterRows(sample,{query:'alpha',lane:'Stand aside'}),[sample[1]]);});
test('count summary covers each lane including empty lanes',()=>{const c=counts(sample);assert.equal(c.All,4);assert.equal(c['Buy now'],0);assert.equal(c['Almost ready'],2);});
test('sort is stable for ties and leaves unknown last',()=>{assert.deepEqual(sortRows(sample,'volume').map(x=>x.id),['US:B:USD','US:A:USD','US:C:USD','HK:A:HKD']);assert.equal(sample[0].id,'US:A:USD');});
test('ascending numeric sort also leaves null last and keeps zero',()=>{assert.deepEqual(sortRows(sample,'price-asc').map(x=>x.id),['US:A:USD','US:C:USD','US:B:USD','HK:A:HKD']);});
test('filtering does not erase inspected identity or comparison',()=>{const s=apply(init(),{type:'inspect',id:sample[0].id},{type:'compare',id:sample[0].id},{type:'filter',query:'Beta'});assert.equal(s.selectedId,sample[0].id);assert.equal(inspected(s).name,'Alpha');assert.deepEqual(s.compare,[sample[0].id]);assert.equal(filterRows(s.rows,s).length,1);});
test('same ticker on two venues remains two comparison identities',()=>{const s=apply(init(),{type:'compare',id:sample[0].id},{type:'compare',id:sample[1].id});assert.deepEqual(s.compare,[sample[0].id,sample[1].id]);});
test('comparison toggles without duplicates and rejects nonexistent identity',()=>{const s=apply(init(),{type:'compare',id:sample[0].id},{type:'compare',id:sample[0].id},{type:'compare',id:'BAD'});assert.deepEqual(s.compare,[]);assert.equal(s.rows.length,4);});
test('comparison cap is explicit and preserves the first three',()=>{const s=sample.reduce((s,r)=>reduce(s,{type:'compare',id:r.id}),init());assert.equal(s.compare.length,3);assert.match(s.notice,/three/i);});
test('clear filters keeps selection and compared identities',()=>{const s=apply(init(),{type:'inspect',id:sample[0].id},{type:'compare',id:sample[1].id},{type:'filter',query:'xx',lane:'Stand aside'},{type:'clearFilters'});assert.equal(s.query,'');assert.equal(s.lane,'All');assert.equal(s.selectedId,sample[0].id);assert.deepEqual(s.compare,[sample[1].id]);});
test('close inspector retains selected row identity',()=>{const s=apply(init(),{type:'inspect',id:sample[2].id},{type:'closeInspector'});assert.equal(s.selectedId,sample[2].id);assert.equal(s.inspectorOpen,false);});
test('staging fresh rows does not change current readings or order',()=>{const incoming=sample.map(x=>({...x,volume:5}));const s=reduce(init(),{type:'stage',rows:incoming,revision:2});assert.deepEqual(s.rows,sample);assert.equal(s.pending.revision,2);});
test('apply staged rows keeps the inspected identity and revision',()=>{const incoming=sample.map(x=>({...x,volume:5}));const s=apply(init(),{type:'inspect',id:sample[0].id},{type:'stage',rows:incoming,revision:2},{type:'apply'});assert.equal(s.revision,2);assert.equal(inspected(s).volume,5);assert.equal(s.pending,null);});
test('older staged result cannot replace newer pending or applied result',()=>{let s=apply(init(),{type:'stage',rows:sample,revision:3},{type:'stage',rows:[],revision:2});assert.equal(s.pending?.revision,3);s=apply(s,{type:'apply'},{type:'stage',rows:[],revision:2});assert.equal(s.pending,null);assert.equal(s.rows.length,4);});
test('missing selected row in a new snapshot is not replaced with another',()=>{const s=apply(init(),{type:'inspect',id:sample[0].id},{type:'stage',rows:sample.slice(1),revision:2},{type:'apply'});assert.equal(s.selectedId,sample[0].id);assert.equal(inspected(s),undefined);});
test('a save error does not add to the demo watchlist',()=>{const s=apply(init(),{type:'saveStart',id:sample[0].id},{type:'saveResult',id:sample[0].id,requestId:1,ok:false});assert.deepEqual(s.saved,[]);assert.equal(s.save.status,'error');});
test('a late save result belongs to its original identity, not current selection',()=>{const s=apply(init(),{type:'inspect',id:sample[0].id},{type:'saveStart',id:sample[0].id},{type:'inspect',id:sample[2].id},{type:'saveResult',id:sample[0].id,requestId:1,ok:true});assert.deepEqual(s.saved,[sample[0].id]);assert.equal(s.selectedId,sample[2].id);});
test('unmatched save completion and duplicate starts cannot fake a success',()=>{let s=reduce(init(),{type:'saveResult',id:sample[0].id,requestId:1,ok:true});assert.deepEqual(s.saved,[]);s=apply(s,{type:'saveStart',id:sample[0].id},{type:'saveStart',id:sample[2].id});assert.equal(s.save.id,sample[0].id);});
test('successful repeated saves are idempotent',()=>{const s=apply(init(),{type:'saveStart',id:sample[0].id},{type:'saveResult',id:sample[0].id,requestId:1,ok:true},{type:'saveStart',id:sample[0].id},{type:'saveResult',id:sample[0].id,requestId:1,ok:true});assert.deepEqual(s.saved,[sample[0].id]);});
test('empty search is not confused with failed source data',()=>{let s=reduce(init(),{type:'filter',query:'no match'});assert.deepEqual(filterRows(s.rows,s),[]);assert.equal(s.sourceStatus,'ready');s=reduce(s,{type:'sourceError'});assert.equal(s.sourceStatus,'error');assert.equal(s.rows.length,4);});
test('pure state changes do not mutate input objects or comparison arrays',()=>{const s=init();const next=reduce(s,{type:'compare',id:sample[0].id});assert.deepEqual(s.compare,[]);assert.deepEqual(next.compare,[sample[0].id]);assert.equal(sample[1].price,null);});

test('an old failed-attempt response cannot settle a newer save for the same listing',()=>{
 let s=reduce(init(),{type:'saveStart',id:sample[0].id});
 const first=s.save.requestId;
 s=reduce(s,{type:'saveResult',id:sample[0].id,requestId:first,ok:false});
 s=reduce(s,{type:'saveStart',id:sample[0].id});
 const second=s.save.requestId;
 assert.notEqual(first,second);
 s=reduce(s,{type:'saveResult',id:sample[0].id,requestId:first,ok:true});
 assert.equal(s.save.status,'pending');assert.deepEqual(s.saved,[]);
 s=reduce(s,{type:'saveResult',id:sample[0].id,requestId:second,ok:true});
 assert.deepEqual(s.saved,[sample[0].id]);
});
test('uncorrelated save completion is ignored',()=>{
 let s=reduce(init(),{type:'saveStart',id:sample[0].id});
 s=reduce(s,{type:'saveResult',id:sample[0].id,ok:true});
 assert.equal(s.save.status,'pending');assert.deepEqual(s.saved,[]);
});
test('applying a buffered snapshot does not falsely declare the source recovered',()=>{
 const s=apply(init(),{type:'stage',rows:sample,revision:2},{type:'sourceError'},{type:'apply'});
 assert.equal(s.sourceStatus,'error');assert.equal(s.revision,2);
 assert.match(s.notice,/unavailable/i);
});

test('duplicate or empty identities cannot enter the snapshot',()=>{
 assert.throws(()=>createState([sample[0],sample[0]]),TypeError);
 assert.throws(()=>createState([{id:'',symbol:'A'}]),TypeError);
 const s=reduce(init(),{type:'stage',rows:[sample[0],sample[0]],revision:2});
 assert.equal(s.pending,null);assert.deepEqual(s.rows,sample);assert.match(s.notice,/invalid/i);
});
test('non-numeric and out-of-order revisions cannot be promoted',()=>{
 for(const revision of ['2',NaN,Infinity,1,-1,1.5]){
  const s=reduce(init(),{type:'stage',rows:[],revision});assert.equal(s.pending,null);
 }
});
test('clearing comparison does not clear inspection or query',()=>{
 const s=apply(init(),{type:'inspect',id:sample[0].id},{type:'filter',query:'Alpha'},
  {type:'compare',id:sample[0].id},{type:'compare',id:sample[1].id},{type:'openCompare'},{type:'clearCompare'});
 assert.deepEqual(s.compare,[]);assert.equal(s.compareOpen,false);assert.equal(s.selectedId,sample[0].id);assert.equal(s.query,'Alpha');
});
test('a disappeared comparison member stays explicitly identified until removed',()=>{
 const s=apply(init(),{type:'compare',id:sample[0].id},{type:'compare',id:sample[1].id},
  {type:'stage',rows:sample.slice(1),revision:2},{type:'apply'});
 assert.deepEqual(s.compare,[sample[0].id,sample[1].id]);
 assert.deepEqual(reduce(s,{type:'compare',id:sample[0].id}).compare,[sample[1].id]);
});
test('source failure prevents starting a new demo save',()=>{
 const s=apply(init(),{type:'sourceError'},{type:'saveStart',id:sample[0].id});
 assert.equal(s.save.status,'idle');assert.deepEqual(s.saved,[]);
});
test('truthy nonboolean completions never count as acknowledged saves',()=>{
 for(const ok of ['true',1,{},[]]){
  const s=apply(init(),{type:'saveStart',id:sample[0].id},
    {type:'saveResult',id:sample[0].id,requestId:1,ok});
  assert.deepEqual(s.saved,[]);assert.equal(s.save.status,'error');
 }
});
test('query strings are literal and bounded, not executable input',()=>{
 const s=reduce(init(),{type:'filter',query:'<script>'.repeat(100)});
 assert.equal(s.query.length,200);assert.deepEqual(filterRows(s.rows,s),[]);
});
test('snapshot staging copies caller records before later mutations',()=>{
 const incoming=sample.map(row=>({...row}));
 let s=reduce(init(),{type:'stage',rows:incoming,revision:2});
 incoming[0].symbol='MUTATED';s=reduce(s,{type:'apply'});
 assert.equal(s.rows[0].symbol,'A');assert.equal(sample[0].symbol,'A');
});
test('unknown lanes are counted explicitly, never relabeled as a valid buy',()=>{
 const c=counts([{id:'x',symbol:'X',lane:'UNRECOGNIZED'}]);
 assert.equal(c.All,1);assert.equal(c.Unclassified,1);assert.equal(c['Buy now'],0);
});
test('numeric sorting respects permutation, ordering and null-last across deterministic fixtures',()=>{
 for(let count=1;count<=40;count++){
  const rs=Array.from({length:count},(_,i)=>({id:`X:${i}`,symbol:`S${i}`,volume:i%7===0?null:((i*17)%23)-10,price:i%5===0?NaN:i%9}));
  for(const mode of ['volume','price-asc']){
   const result=sortRows(rs,mode);assert.deepEqual(result.map(r=>r.id).sort(),rs.map(r=>r.id).sort());
   const key=mode==='volume'?'volume':'price';let seenUnknown=false,prev=mode==='volume'?Infinity:-Infinity;
   for(const row of result){const v=row[key];if(typeof v!=='number'||!Number.isFinite(v)){seenUnknown=true;continue;}
    assert.equal(seenUnknown,false);assert.ok(mode==='volume'?v<=prev:v>=prev);prev=v;}
  }
 }
});
