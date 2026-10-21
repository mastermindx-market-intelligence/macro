'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { normalizeOutcomeAttachment: normalize, formatRatio } = require('../../templates/market_memory_outcome_contract.js');
const hash = c => c.repeat(64), id = (prefix, c) => prefix + '_' + hash(c);
function fixture() {
  const expected = { retrievalId: id('mmretainedretrieval', 'a'), selectionSha256: hash('a'),
    queryCutoff: '2026-08-20T00:00:00Z', outcomeCutoff: '2026-08-21T00:00:00.000002Z', lens: 'later_observed',
    definitionSha256: hash('d'), neighbors: [{ contextId: id('mmctx', 'b'), captureId: id('mmcapture', 'c'),
      packetSha256: hash('e'), comparisonId: id('mmepisodecomparison', 'f'), distanceQ18: '0.250000000000000000' }] };
  const selected = expected.neighbors[0];
  const raw = { schema: 'market_memory.outcome_inspection.v1', retrieval_id: expected.retrievalId,
    selection_sha256: expected.selectionSha256, query_cutoff: expected.queryCutoff,
    outcome_cutoff: expected.outcomeCutoff, lens: expected.lens, definition_sha256: expected.definitionSha256,
    metric: 'archived_close_ratio', economic_return: false, corporate_action_adjusted: false,
    RTH_close_authenticated: false, effective_n: 'not_estimated', rows: [{ rank: 1, context_id: selected.contextId,
      capture_id: selected.captureId, packet_sha256: selected.packetSha256, comparison_id: selected.comparisonId,
      distance_q18: selected.distanceQ18, status: 'observed', reason: 'exact_retained_source_marks',
      value_q18: '1.024650000000000000', observation: { id: id('mmcontextualobservation', '1'), sha256: hash('2'),
        revision_number: 1, previous_observation_id: null, clocks: { observed_at: '2026-08-21T00:00:00Z',
          published_at: '2026-08-21T00:00:00.000001Z', recorded_at: '2026-08-21T00:00:00.000002Z' } } }] };
  return { raw, expected };
}
test('output detaches and deeply freezes exact values without mutating inputs', () => {
  const {raw,expected} = fixture(), before = JSON.stringify([raw,expected]), result = normalize(raw,expected);
  assert.equal(JSON.stringify([raw,expected]), before);
  assert.equal(result.rows[0].valueQ18, '1.024650000000000000');
  assert(Object.isFrozen(result.rows[0].observation.clocks));
  assert.throws(() => { result.rows[0].observation.clocks.observedAt = 'changed'; }, TypeError);
  raw.rows[0].observation.clocks.observed_at = 'changed';
  assert.equal(result.rows[0].observation.clocks.observedAt, '2026-08-21T00:00:00Z');
});
for (const path of ['root','expected','row','neighbor','observation','clocks']) {
  test('closed fields, accessor rejection: '+path, () => {
    for (const change of ['extra','missing','getter']) {
      const {raw,expected}=fixture();
      const target={root:raw,expected,row:raw.rows[0],neighbor:expected.neighbors[0],
        observation:raw.rows[0].observation,clocks:raw.rows[0].observation.clocks}[path];
      if(change==='extra')target.secret=1;
      if(change==='missing')delete target[Object.keys(target)[0]];
      if(change==='getter')Object.defineProperty(target,Object.keys(target)[0],{get(){throw Error('getter ran');}});
      assert.throws(()=>normalize(raw,expected),/outcome_contract:/);
    }
  });
}
for (const field of ['retrieval_id','selection_sha256','query_cutoff','outcome_cutoff','lens','definition_sha256']) {
  test('reject exact root binding change '+field,()=>{const {raw,expected}=fixture();raw[field]+='x';assert.throws(()=>normalize(raw,expected),/binding/);});
}
for (const field of ['context_id','capture_id','packet_sha256','comparison_id','distance_q18']) {
  test('reject selected row change '+field,()=>{const {raw,expected}=fixture();raw.rows[0][field]+='x';assert.throws(()=>normalize(raw,expected),/row_binding/);});
}
test('count, rank, duplicate, sparse and extra array keys fail',()=>{
  const mutations=[(r,e)=>r.rows.pop(),(r,e)=>r.rows[0].rank=2,(r,e)=>{r.rows.push(structuredClone(r.rows[0]));e.neighbors.push(structuredClone(e.neighbors[0]));},
    (r,e)=>delete r.rows[0],(r,e)=>r.rows.extra=1,(r,e)=>{delete e.neighbors[0];},(r,e)=>e.neighbors.length=9];
  for(const mutate of mutations){const{raw,expected}=fixture();mutate(raw,expected);assert.throws(()=>normalize(raw,expected),/outcome_contract:/);}
});
for(const value of ['2026-02-30T00:00:00Z','2025-02-29T00:00:00Z','2026-13-01T00:00:00Z','2026-01-00T00:00:00Z',
  '2026-01-01T24:00:00Z','2026-01-01T00:60:00Z','2026-01-01T00:00:60Z','2026-01-01T00:00:00.1234567Z',
  '2026-01-01T00:00:00+00:00','0000-01-01T00:00:00Z']) {
  test('reject invalid Gregorian UTC '+value,()=>{const{raw,expected}=fixture();expected.queryCutoff=raw.query_cutoff=value;assert.throws(()=>normalize(raw,expected),/clock/);});
}
test('microsecond ordering and lens boundaries never truncate',()=>{
  for(const mutate of [r=>r.rows[0].observation.clocks.recorded_at='2026-08-21T00:00:00.000003Z',
    r=>r.rows[0].observation.clocks.published_at='2026-08-21T00:00:00.000003Z',
    r=>r.rows[0].observation.clocks.observed_at='2026-08-21T00:00:00.000002Z']) {
    const{raw,expected}=fixture();mutate(raw);assert.throws(()=>normalize(raw,expected),/clock_order/);
  }
  const{raw,expected}=fixture();raw.lens=expected.lens='then_known';assert.throws(()=>normalize(raw,expected),/lens_cutoff/);
});
test('proof pending and censored contain no hidden observation, ratio or authority',()=>{
  for(const [status,reasons] of [['proof_pending',['not_visible_at_query','not_visible_at_cutoff','source_or_observation_proof_pending']],
    ['censored',['outcome_calendar_unavailable','ambiguous_source_observation_clock','source_observation_after_registered_deadline']]]) {
    for(const reason of reasons){const{raw,expected}=fixture();Object.assign(raw.rows[0],{status,reason,value_q18:null,observation:null});
      assert.equal(normalize(raw,expected).rows[0].valueQ18,null);raw.rows[0].value_q18='0.000000000000000000';assert.throws(()=>normalize(raw,expected),/hidden_observation/);}
  }
  for(const field of ['economic_return','corporate_action_adjusted','RTH_close_authenticated']) {
    const{raw,expected}=fixture();raw[field]=true;assert.throws(()=>normalize(raw,expected),/semantics/);
  }
});
test('then-known future and absent rows have identical inert representation',()=>{
  const{raw,expected}=fixture();raw.lens=expected.lens='then_known';raw.outcome_cutoff=expected.outcomeCutoff=expected.queryCutoff;
  Object.assign(raw.rows[0],{status:'proof_pending',reason:'not_visible_at_query',value_q18:null,observation:null});
  assert.equal(normalize(raw,expected).rows[0].observation,null);
});
test('lineage requires a prior nonself identity only for later revisions',()=>{
  const{raw,expected}=fixture(),proof=raw.rows[0].observation;
  proof.revision_number=2;assert.throws(()=>normalize(raw,expected),/identity/);
  proof.previous_observation_id=proof.id;assert.throws(()=>normalize(raw,expected),/revision/);
  proof.previous_observation_id=id('mmcontextualobservation','3');assert.equal(normalize(raw,expected).rows[0].observation.revisionNumber,2);
  proof.revision_number=1;assert.throws(()=>normalize(raw,expected),/revision/);
});
for(const [input,want] of [['1.024650000000000000','1.0246×'],['1.024750000000000000','1.0248×'],
  ['1.999950000000000000','2.0000×'],['0.000000000000000001','0.0000×'],
  ['9007199254740993.123450000000000000','9007199254740993.1234×']]) {
  test('decimal half-even ratio '+input,()=>assert.equal(formatRatio(input),want));
}
test('invalid q18 refuses, and largest supported integer retains precision',()=>{
  for(const value of [null,0,'0.000000000000000000','-1.000000000000000000','01.000000000000000000','1.0','1e18','9'.repeat(401)+'.000000000000000000'])assert.throws(()=>formatRatio(value),/q18/);
  assert.equal(formatRatio('9'.repeat(400)+'.999950000000000000'),'1'+'0'.repeat(400)+'.0000×');
});
