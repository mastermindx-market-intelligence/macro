'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const fixture = JSON.parse(fs.readFileSync(path.join(root, 'tests/fixtures/market_memory_retained_owner_wire.json')));
let h;
vm.runInNewContext(fs.readFileSync(path.join(root, 'templates/market_memory_retained.js'), 'utf8'), {__MM_RETAINED_TEST_HOOK__: x => h = x});
const clone = x => JSON.parse(JSON.stringify(x));
function intent(example, mode) {
 const q = example.request.query;
 return {mode, query:q.query_id, subject:q.subject_id, gen:q.generation_id,genSha:q.generation_sha256,
  cutoff:q.query_cutoff,method:q.method_spec_id,context:example.body.owner.context_id};
}
for (const name of ['catalog_historical','catalog_current','catalog_page_one','catalog_page_two']) {
 test('actual owner catalog '+name, () => {
  const raw = fixture.examples[name].body, result = h.normalizeCatalog(raw);
  assert.equal(result.entries.length, raw.entries.length);
  assert.equal(result.entries[0].sourceSession, raw.entries[0].source_session);
  assert.equal(result.requestClock.referenceCutoffUtc, raw.server_reference_cutoff);
  assert.equal(result.selection.continuation === null, raw.selection.continuation === null);
 });
}
for (const [name,mode] of [['retained_historical','historical'],['retained_current','current'],['retained_valid_empty','historical']]) {
 test('actual owner comparison '+name, () => {
  const example=fixture.examples[name], result=h.normalizeCompare(intent(example,mode),example.body);
  assert.equal(result.status,example.body.status);
  assert.equal(result.neighbors.length,example.body.neighbors.length);
  result.neighbors.forEach((n,i)=>{
   assert.equal(n.distanceQ18,example.body.neighbors[i].distance_q18);
   assert.equal(typeof n.distanceQ18,'string');
   assert.equal(n.sourceCard.contextId,n.contextId);
   assert.equal(n.sourceCard.facts.length,5);
  });
 });
}
for (const key of ['query_id','subject_id','requested_subject_id','context_id','generation_id','generation_sha256','query_cutoff']) {
 test('reject changed or missing owner '+key,()=>{
  const example=fixture.examples.retained_historical, selected=intent(example,'historical');
  for (const value of ['deliberately_wrong',undefined]) {
   const body=clone(example.body);body.owner[key]=value;
   assert.throws(()=>h.normalizeCompare(selected,body),e=>e.contractCode==='compare_binding_'+key);
  }
 });
}
test('missing, incomplete and disjoint accounting must reconcile',()=>{
 const example=fixture.examples.retained_historical;
 for (const mutate of [b=>delete b.exclusion_counts,b=>b.denominator.accounted_captures--,b=>b.exclusion_counts.query_self++,b=>b.denominator.returned++]) {
  const b=clone(example.body);mutate(b);
  assert.throws(()=>h.normalizeCompare(intent(example,'historical'),b),e=>e.contractCode==='compare_accounting');
 }
});
test('reject unmatched source cards, invented quote values, duplicate cases and numeric distances',()=>{
 const e=fixture.examples.retained_historical;
 for (const mutate of [b=>b.source_cards.pop(),b=>b.source_cards[0].facts[0].value=99,
  b=>b.neighbors.push(b.neighbors[0]),b=>b.neighbors[0].distance_q18=0.01]) {
  const b=clone(e.body);mutate(b);assert.throws(()=>h.normalizeCompare(intent(e,'historical'),b));
 }
});
test('catalog continuation is exact generation and contiguous offset',()=>{
 const e=fixture.examples.catalog_page_one.body;
 for (const mutate of [b=>b.selection.continuation.generation_sha256='f'.repeat(64),
  b=>b.selection.continuation.offset++,b=>b.selection.continuation=null,b=>b.entries[0].subject_id='wrong']) {
  const b=clone(e);mutate(b);assert.throws(()=>h.normalizeCatalog(b));
 }
});
test('date-only source session is not promoted to an invented instant',()=>{
 const e=clone(fixture.examples.catalog_historical.body.entries[0]);
 e.source_session='2026-02-30';assert.throws(()=>h.normalizeEntry(e));
 e.source_session='2026-02-28';assert.equal(h.normalizeEntry(e).sourceSession,'2026-02-28');
});

test('deep link binds one exact capture tuple in cold and cached catalogs',()=>{
 const e=fixture.examples.retained_historical, i=intent(e,'historical'), c=h.normalizeCatalog(fixture.examples.catalog_historical.body);
 assert.equal(h.deepLinkMismatch(i,c),'');
 for (const key of ['query','subject','context','gen','genSha','method','cutoff']) {
  const partial={...i};delete partial[key];assert.notEqual(h.deepLinkMismatch(partial,c),'',key);
 }
 const another=c.entries.find(e=>e.contextId!==i.context);
 assert.equal(h.deepLinkMismatch({...i,query:another.queryId},c),'query_context');
 assert.equal(h.deepLinkMismatch({...i,method:c.methods.current_contextual_support.methodSpecId},c),'method_spec_id');
 assert.equal(h.deepLinkMismatch({...i,catalogOffset:'20'},c),'catalog_offset');
 assert.equal(h.deepLinkMismatch({mode:'historical'},c),'');
});

test('only a complete historical/current reference can dispatch to the exact endpoint without a catalog',()=>{
 const e=fixture.examples.retained_historical,i=intent(e,'historical'),cu=fixture.examples.retained_current;
 assert.equal(h.completeCompareRef(i),true);
 assert.equal(h.completeCompareRef(intent(cu,'current')),true);
 for (const key of ['query','subject','gen','genSha','method','context','cutoff']) {
  const partial={...i};delete partial[key];
  assert.equal(h.completeCompareRef(partial),false,'a missing '+key+' must go back to the catalog');
 }
 assert.equal(h.completeCompareRef({...i,mode:'saved'}),false,'saved output still needs its catalog capture id');
 assert.equal(h.completeCompareRef({...i,mode:'current',method:cu.body.method_spec.method_spec_id}),true);
 for (const broken of [{genSha:'zz'},{genSha:''},{genSha:64},{cutoff:'2026-08-20T12:00:00'},{cutoff:'2026-02-30T00:00:00Z'},
   {query:'mm query with spaces'},{method:''},{context:'mmctx_'+('x'.repeat(200))}]) {
  assert.equal(h.completeCompareRef({...i,...broken}),false,'malformed '+Object.keys(broken)[0]);
 }
 assert.equal(h.completeCompareRef(null),false);
 assert.equal(h.completeCompareRef(undefined),false);
 assert.equal(h.completeCompareRef({}),false);
 assert.equal(h.completeCompareRef({...i,mode:'not-a-mode'}),false);
});

function savedPair() {
 const e=fixture.examples.saved,q=e.request.query;
 const entry=h.normalizeCatalog(fixture.examples.catalog_saved.body).entries.find(v=>v.contextId===q.context_id);
 return {e,entry,i:{mode:'saved',query:q.query_id,context:q.context_id,subject:q.subject_id,gen:q.generation_id,genSha:q.generation_sha256,cutoff:q.query_cutoff}};
}
test('actual owner saved envelope preserves five original values and citations',()=>{
 const {e,entry,i}=savedPair(),v=h.normalizePlayback(entry,e.body,e.headers.etag,i);
 assert.equal(v.contextId,i.context);assert.equal(v.facts.length,5);
 assert.deepEqual(clone(v.state),e.body.feature_projection.state);
 const reordered=clone(e.body);reordered.feature_projection.original_feature_ref=Object.fromEntries(Object.entries(reordered.feature_projection.original_feature_ref).reverse());
 assert.equal(h.normalizePlayback(entry,reordered,e.headers.etag,i).contextId,i.context);
});
test('saved output rejects mismatched selection, refs, projection and quote identity',()=>{
 const {e,entry,i}=savedPair();
 for(const mutate of [b=>b.selection.context_id='wrong',b=>b.generation.generation_sha256='f'.repeat(64),b=>b.feature_projection.state.confidence=1,
  b=>b.feature_snapshot={},b=>b.exact_refs.feature.bytes++,b=>b.feature_projection.original_feature_ref.snapshot_id='wrong',
  b=>b.source_facts[0].citation.snapshot_id='wrong',b=>b.source_facts[0].value=999,b=>b.source_facts.pop(),b=>b.clocks.captured_at='2026-02-30T00:00:00Z']){
  const b=clone(e.body);mutate(b);assert.throws(()=>h.normalizePlayback(entry,b,e.headers.etag,i));
 }
 const b=clone(e.body),other={...i,context:'mmctx_other',query:'mmquery_other'};b.selection.context_id=other.context;b.selection.query_id=other.query;
 assert.throws(()=>h.normalizePlayback(entry,b,e.headers.etag,other),e=>e.contractCode==='saved_exact_binding');
});
test('saved cutoff retains microsecond precision',()=>{
 const {e,entry,i}=savedPair(),b=clone(e.body),base='2026-08-20T12:00:00';
 b.clocks.captured_at=b.capture_receipt.captured_at=base+'.000002Z';b.earliest_supported_cutoff=base+'.000002Z';
 b.selection.query_cutoff=base+'.000001Z';const early={...i,cutoff:b.selection.query_cutoff};
 assert.throws(()=>h.normalizePlayback(entry,b,e.headers.etag,early),e=>e.contractCode==='saved_clocks_binding');
 b.selection.query_cutoff=base+'.000002Z';assert.equal(h.normalizePlayback(entry,b,e.headers.etag,{...i,cutoff:b.selection.query_cutoff}).contextId,i.context);
 b.earliest_supported_cutoff=base+'.000001Z';assert.throws(()=>h.normalizePlayback(entry,b,e.headers.etag,{...i,cutoff:b.selection.query_cutoff}));
});
test('catalog missing fields follow owner unavailable enum',()=>{
 const e=clone(fixture.examples.catalog_saved.body.entries[0]);e.field_status.growth_score='unavailable';
 assert.equal(h.normalizeEntry(e).fieldsPresent.growth_score,false);
 e.field_status.growth_score='missing';assert.throws(()=>h.normalizeEntry(e));
});

// Real edge response: Caddy keeps the packet digest and adds its encoding suffix.
for (const encoding of ['gzip','zstd']) test('saved output accepts exact '+encoding+' representation tag',()=>{
 const {e,entry,i}=savedPair();
 const etag='"'+entry.packetSha256+'-'+encoding+'"';
 const v=h.normalizePlayback(entry,e.body,etag,i,encoding);
 assert.equal(v.contextId,i.context);assert.deepEqual(clone(v.state),e.body.feature_projection.state);
 const wrong=clone(e.body);wrong.exact_refs.packet.sha256='f'.repeat(64);
 assert.throws(()=>h.normalizePlayback(entry,wrong,etag,i,encoding),e=>e.contractCode==='saved_original_refs');
});
for(const [suffix,encoding] of [['gzip',null],['gzip','zstd'],['zstd','gzip'],['gzip','gzip, br'],['br','br'],['gzip-extra','gzip']])test('reject nonmatching encoded saved validator '+suffix+'/'+encoding,()=>{
 const {e,entry,i}=savedPair();
 assert.throws(()=>h.normalizePlayback(entry,e.body,'"'+entry.packetSha256+'-'+suffix+'"',i,encoding),e=>e.contractCode==='saved_etag');
});
test('encoding cannot excuse a different digest or weak/malformed validator',()=>{
 const {e,entry,i}=savedPair();
 for(const etag of ['"'+('f'.repeat(64))+'-gzip"','W/"'+entry.packetSha256+'-gzip"',entry.packetSha256+'-gzip','"'+entry.packetSha256+'-gzip", "other"'])
  assert.throws(()=>h.normalizePlayback(entry,e.body,etag,i,'gzip'),e=>e.contractCode==='saved_etag');
});
