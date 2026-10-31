/* Deterministic contracts for the shipped workspace API; no live page, DOM or network. */
"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const api = require("../templates/commodity-workspace.js");
const data = {
  as_of: "2026-10-16", fingerprint: "dated-fixture-v1", projection_revision: 6,
  assets: ["oil","gold","copper","silver","natgas"].map(id => ({id, returns:{"20":null}})),
  hypotheses: {oil:[{id:"supply"}], gold:[{id:"rates"}]}, chains: [],
  rates: {real_10y:null}, fx: {direction:null,direction_as_of:null},
  physical: null, gold_physical: null, ratios: [],
  sources: {fx:{as_of:null,available_at:null,state:"unavailable",point_in_time_verified:false}}
};
const raw = {
  schema:"mmx.commodities.research_condition.v1",asset:"oil",metric:"return_pct",unit:"%",
  window_sessions:20,operator:"gte",threshold:0,expires_on:"2026-10-18",
  snapshot_fingerprint:data.fingerprint,hypothesis:"supply"
};
const copy = value => JSON.parse(JSON.stringify(value));
const saved = () => {const result=api.checkDraft(copy(raw),data);assert.deepEqual(result.errors,[]);return result.value;};

test("unknown and inherited asset names are rejected before semantic lookup",()=>{
  for (const asset of ["constructor","__proto__","toString","hasOwnProperty","unknown",null,{},["oil"]]) {
    const result=api.checkDraft({...saved(),asset},data,true);
    assert.equal(result.value,null);assert.ok(result.errors.includes("asset"));
  }
  for (const value of [null,[],{},false,3,"oil"]) assert.equal(api.checkDraft(value,data,true).value,null);
});
test("deep semantic input under the file limit rejects without recursion failure",()=>{
  const draft=saved();let deep={};for(let i=0;i<100;i++)deep={nested:deep};
  draft.as_saved_evidence=deep;
  assert.ok(Buffer.byteLength(JSON.stringify(draft))<131072);
  const result=api.checkDraft(JSON.parse(JSON.stringify(draft)),data,true);
  assert.equal(result.value,null);assert.ok(result.errors.includes("semantic_structure"));
});
test("degraded evidence round trip preserves nulls, clocks and inactive monitoring",()=>{
  const draft=saved(), result=api.checkDraft(copy(draft),data,true);
  assert.deepEqual(result.errors,[]);assert.deepEqual(result.value,draft);
  assert.equal(result.value.threshold,0);
  assert.equal(result.value.as_saved_evidence.physical,null);
  assert.equal(result.value.as_saved_evidence.rates.real_10y,null);
  assert.equal(result.value.source_dependencies.fx.available_at,null);
  assert.equal(result.value.source_dependencies.fx.point_in_time_verified,false);
  assert.equal(result.value.monitoring_active,false);
  for (const key of ["source_dependencies","as_saved_evidence"]) {
    const missing=copy(draft);delete missing[key];assert.ok(api.checkDraft(missing,data,true).errors.includes(key));
  }
  const changed=copy(draft);changed.as_saved_evidence.rates.real_10y=0;
  assert.ok(api.checkDraft(changed,data,true).errors.includes("as_saved_evidence"));
});
test("research expiry is checked against its snapshot without enabling monitoring",()=>{
  assert.deepEqual(api.checkDraft(saved(),data,true).errors,[]);
  for (const expires_on of ["2026-10-15","2026-02-30","not-a-date"]) {
    assert.ok(api.checkDraft({...saved(),expires_on},data,true).errors.includes("expires_on"));
  }
});
test("fragment normalization bounds comparisons and rejects unsupported state",()=>{
  const fallback=api.normalizeState({},data);
  for (const fragment of ["#other","#cw/"+ "x".repeat(2001)]) assert.deepEqual(api.readState(fragment,data),fallback);
  const examples=[
    ["#cw/relationships/constructor?window=9&hypothesis=__proto__&compare=oil,oil,unknown,gold,copper,silver,natgas",
      {tab:"relationships",asset:"oil",window:"1m",hypothesis:"unresolved",compare:["oil","gold","copper","silver"]}],
    ["#cw/research/gold?window=60&hypothesis=rates&compare=",
      {tab:"research",asset:"gold",window:"60",hypothesis:"rates",compare:[]}]
  ];
  for (const [fragment,expected] of examples) {
    const state=api.readState(fragment,data);assert.deepEqual(state,expected);
    assert.deepEqual(api.readState(api.stateHash(state),data),expected);
  }
});
test("company continuation keeps owner identity and encodes an exact bounded return",()=>{
  const original="https://app.mastermind-x.com/analysis?symbol=A&page=intelligence&mo_from=transmission&mo_chain=oil_inflation_duration_derate&mo_channel=long_duration_valuation&mo_asof=2026-10-16&mo_security=SEC%3AUS-XNYS-A";
  const state=api.normalizeState({tab:"relationships",asset:"oil",window:"60",compare:["oil","gold"],hypothesis:"supply"},data);
  const expected="https://www.mastermind-x.com/commodities.html#cw/relationships/oil?window=60&compare=oil%2Cgold&hypothesis=supply";
  const href=api.companyReturnHref(original,state,"https://www.mastermind-x.com/commodities.html?ret=https://evil.example");
  const target=new URL(href);assert.equal(target.searchParams.get("ret"),expected);
  assert.equal(target.searchParams.get("from"),"macro");
  assert.equal(target.searchParams.getAll("ret").length,1);
  for (const [key,value] of new URL(original).searchParams) assert.equal(target.searchParams.get(key),value);
  assert.equal(api.companyReturnHref(href,state,expected),href);
  for (const page of ["https://evil.example/commodities.html","https://www.mastermind-x.com.evil.example/commodities.html","https://user:pass@www.mastermind-x.com/commodities.html","http://www.mastermind-x.com/commodities.html","https://www.mastermind-x.com/other.html"]) {
    assert.equal(api.companyReturnHref(original,state,page),original);
  }
  assert.equal(api.companyReturnHref("https://evil.example/analysis?page=intelligence",state,expected),"https://evil.example/analysis?page=intelligence");
});
