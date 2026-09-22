'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Guide = require('../research/reference_rethink_20260921/guide-client.js');
const fixtureJSON = require('node:child_process').execFileSync(process.env.PYTHON || 'python3', [path.join(__dirname,'fixtures/market-guide/compile_fixture.py')], {encoding:'utf8'});
const fixture = () => JSON.parse(fixtureJSON);
const model = () => Guide.createModel(fixture());

test('reads a complete projection without modifying its data',()=>{
  const source=fixture(), original=JSON.stringify(source), m=Guide.createModel(source);
  assert.equal(m.entries.length,8);assert.equal(JSON.stringify(source),original);
  assert.throws(()=>m.entries.push({}),TypeError);
  source.entries[0].definition.en='mutated outside';assert.notEqual(m.entries[0].definition.en,'mutated outside');
});
test('old aliases, coverage labels and punctuation resolve to the same canonical entry',()=>{
  for(const term of ['regime-badge','Regime Badge','市场状态徽标','coverage-regime-badge'])assert.equal(model().resolve(term).id,'market-regime');
  assert.equal(model().resolve('态势标签').id,'posture-dial');
  assert.equal(model().resolve('ＳＴＡＴＥ—ＤＩＡＬ').id,'market-state-score');
});
test('board lookup is a coverage explanation, not a fabricated indicator',()=>{
  const m=model(), r=m.resolve('Prophet Stock Signals Board');
  assert.equal(m.get(r.id).state,'not_an_indicator');assert.equal(m.entries.some(x=>x.id===r.id),false);
});
test('ambiguous aliases remain a choice; exact canonical IDs stay direct',()=>{
  const raw=fixture();raw.lookup['ambiguous']=['market-state-score','risk-radar'];
  const m=Guide.createModel(raw);assert.deepEqual(m.resolve('ambiguous').ids,['market-state-score','risk-radar']);
  assert.equal(m.resolve('market-state-score').id,'market-state-score');
});
test('missing and malicious hashes are data, not executable markup',()=>{
  const r=model().resolve('<img src=x onerror=alert(1)>');assert.equal(r.status,'missing');
  assert.equal(model().resolve('__proto__').status,'missing');
});
test('search deduplicates aliases and returns exact source question membership',()=>{
  assert.deepEqual(model().search('Regime Badge').map(x=>x.id),['market-regime']);
  assert.deepEqual(model().search('', 'risk').map(x=>x.id).sort(),['market-state-score','risk-radar']);
  assert.deepEqual(model().search('风险正在累积吗').map(x=>x.id).sort(),['market-state-score','risk-radar']);
  assert.deepEqual(model().search('zz-no-such-term'),[]);
});
test('risk and market strength never borrow each other’s higher interpretation',()=>{
  assert.match(model().chooseReading('market-state-score','interpretation_up').text.en,/supportive/);
  assert.match(model().chooseReading('risk-radar','interpretation_up').text.en,/not an exit signal/);
  assert.equal(model().chooseReading('risk-radar','unrecognized').id,'interpretation_neutral');
});
test('confirmation does not gain an up/down score',()=>{
  const m=model();assert.equal(m.get('transition-state').presentation.readings.length,1);
  assert.equal(m.chooseReading('transition-state','interpretation_up').id,'interpretation_neutral');
});
test('owner target is same-origin and does not accept an arbitrary referrer',()=>{
  assert.equal(model().ownerURL('risk-radar','https://www.mastermind-x.com/reference.html'),'https://www.mastermind-x.com/macro.html#regime-radar');
  assert.equal(model().ownerURL('risk-radar','javascript:alert(1)'),null);
  assert.equal(model().ownerURL('missing','https://example.com'),null);
});
test('URL roundtrip preserves exact query, selected entry, language and example',()=>{
  const state={query:'Curve & 信用',topic:'',browsing:true,lang:'zh',fragment:'risk-radar',reading:'interpretation_up'};
  const url=Guide.routeURL('https://example.com/reference.html?return=https://evil.invalid',state);
  assert.equal(new URL(url).searchParams.has('return'),false);
  const roundtrip=Guide.readRoute(url,model());
  for(const key of ['query','topic','lang','fragment','reading'])assert.equal(roundtrip[key],state[key]);
});
test('duplicate route query is reported and malformed percent encoding stays safe',()=>{
  assert.equal(Guide.readRoute('https://example.com/reference.html?q=a&q=b',model()).duplicate,true);
  assert.equal(Guide.readRoute('https://example.com/reference.html#%E0%A4%A',model()).resolution.status,'missing');
});
for(const mutate of [
  x=>x.live_values=true,
  x=>x.authority_ceiling='trade',
  x=>x.entries[0].owner_ref='https://evil.invalid/x',
  x=>x.entries[0].owner_ref='macro.html#x\n',
  x=>x.entries[0].public_source_refs=['javascript:alert(1)'],
  x=>x.entries[0].public_source_refs=['https://fred.stlouisfed.org@evil.invalid/'],
  x=>x.entries[0].caveats.zh=[],
  x=>x.entries[0].visible_caveat.en='This is certain.',
  x=>x.entries[0].presentation.thresholds=[0,50,100],
  x=>x.entries[0].presentation.readings.push(x.entries[0].presentation.readings[0]),
  x=>x.entries[0].presentation.readings[0].text.zh='',
  x=>x.entries[0].related_ids=['nonexistent'],
  x=>x.lookup['hello']=['nonexistent'],
  x=>x.coverage[0].target='risk-radar',
  x=>x.coverage[2].reason=null,
  x=>x.questions[0].entry_ids=['nonexistent'],
  x=>x.entries[0].replacement_chain=['market-state-score'],
])test('rejects malformed manifest: '+mutate.toString(),()=>{const raw=fixture();mutate(raw);assert.throws(()=>Guide.createModel(raw));});
