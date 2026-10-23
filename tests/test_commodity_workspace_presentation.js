/* Presentation regressions using a deliberately synthetic return fixture. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {JSDOM} = require("jsdom");
const root = path.resolve(__dirname, "..");
const api = require(path.join(root, "templates/commodity-workspace.js"));

assert.equal(api.returnScale([null, undefined, NaN, Infinity, "9", -10, 5, 0]), 10);
assert.deepEqual(api.returnGeometry(-5, 10), {available:true, direction:"negative", width:25});
assert.deepEqual(api.returnGeometry(0, 0), {available:true, direction:"flat", width:0});
for (const missing of [null, undefined, NaN, Infinity, "0"]) {
  assert.deepEqual(api.returnGeometry(missing, 10), {available:false, direction:"unavailable", width:0});
}

// Filtering is an intersection, and unknown states never enter the neutral cell.
const universe = [
  {id:"oil",label:{en:"WTI crude",zh:"原油"},family:"energy",change_1m_pct:0,trend:"up",momentum:"neutral",returns:{"20":0}},
  {id:"gas",label:{en:"Natural gas",zh:"天然气"},family:"energy",change_1m_pct:-4,trend:"down",momentum:"bear",returns:{"20":-3}},
  {id:"gold",label:{en:"Gold",zh:"黄金"},family:"precious",change_1m_pct:null,trend:null,momentum:null,returns:{"20":null}},
  {id:"silver",label:{en:"Silver",zh:"白银"},family:"precious",change_1m_pct:5,trend:"up",momentum:"bull",returns:{"20":5}}
];
const fixture={assets:universe,hypotheses:{},sources:{commodities:{path:"data/commodity/complex_latest.json",fingerprint:"fixture",available_at:null}}};
const filters=patch=>api.normalizeState(patch,fixture);
const ids=patch=>api.filterAssets(universe,filters(patch)).map(a=>a.id);
assert.deepEqual(ids({query:"gas",family:"energy",trend:"down",momentum:"bear"}),["gas"]);
assert.deepEqual(ids({query:"gold",family:"energy"}),[]);
assert.deepEqual(ids({query:"黄金",family:"precious"}),["gold"]);
assert.deepEqual(ids({momentum:"neutral"}),["oil"]);
assert.deepEqual(ids({momentum:"unknown",trend:"unknown"}),["gold"]);
assert.deepEqual(ids({sort:"return_asc"}),["gas","oil","silver","gold"]);
assert.deepEqual(ids({sort:"return_desc"}),["silver","oil","gas","gold"]);
assert.deepEqual(universe.map(a=>a.id),["oil","gas","gold","silver"],"sorting must not reorder producer observations");
const context=filters({tab:"explore",view:"universe",asset:"oil",query:"黄金",family:"precious",sort:"return_desc",momentum:"unknown",layout:"map",compare:["oil","gold"]});
assert.deepEqual(api.readState(api.stateHash(context),fixture),context);
assert.equal(filters({query:"a\u0000b",family:"unowned",trend:"surge",momentum:"flat"}).query,"ab");
assert.equal(filters({query:"x".repeat(100)}).query.length,80);
assert.match(api.comparisonReading(universe,["oil","gas","gold"],"20","en"),/3.0 percentage points apart.*Missing observations are excluded/);
assert.match(api.comparisonReading(universe,["oil","gold"],"20","en"),/Two available observations/);
assert.equal(api.metricReceipt(fixture,"gold","20").value,null);
assert.equal(api.metricReceipt(fixture,"oil","1m").field,"chg_1m_pct");
fixture.assets[0].as_of="2026-10-21";
assert.equal(api.metricReceipt(fixture,"oil","1m").analysis_as_of,"2026-10-21");
assert.equal(api.metricReceipt(fixture,"oil","1m").observation_at,null);
assert.equal(api.metricReceipt(fixture,"oil","1m").source.available_at,null);
assert.equal(api.metricReceipt(fixture,"oil","20").field,"velocity.r20");
assert.equal(api.metricReceipt(fixture,"oil","trend").field,"ts_trend");
assert.equal(api.metricReceipt(fixture,"gold","probability"),null);
fixture.physical={evidence:{crude_z:{value:-0.92,unit:"seasonal_z",observation_at:"2026-10-16",release_at:null,point_in_time_verified:false,source_ids:["crude_stocks"]},days_supply:{value:null,unit:"days",source_ids:["crude_stocks","refinery_inputs"]}},stocks:[{id:"crude",label:{en:"Commercial crude",zh:"商业原油"}}],flows:[],source_dependencies:{}};
assert.equal(api.physicalReceipt(fixture,"crude_z").observation.value,-0.92);
assert.equal(api.physicalReceipt(fixture,"crude_z").observation.release_at,null);
assert.equal(api.physicalReceipt(fixture,"days_supply").observation.value,null);
assert.equal(api.physicalReceipt(fixture,"days_supply").metric_label.en,"Stock / daily flow");
assert.equal(api.physicalReceipt(fixture,"__proto__"),null);
assert.equal(api.physicalReceipt(fixture,"nonexistent"),null);
// The interpretation must follow the selected field, without turning a missing
// observation into zero or borrowing direction from a different state/window.
const oilMonth=api.metricInterpretation(api.metricReceipt(fixture,"oil","1m"),"en");
assert.match(oilMonth.supports,/one-month price change is zero/);
assert.match(oilMonth.supports,/trend is up; momentum is neutral/);
assert.match(oilMonth.doesNot,/physical shortage.*entry signal/);
assert.match(api.metricInterpretation(api.metricReceipt(fixture,"gas","1m"),"en").supports,/negative.*trend is down.*momentum is negative/);
assert.match(api.metricInterpretation(api.metricReceipt(fixture,"silver","1m"),"zh").supports,/变化为正.*趋势向上.*动能偏强/);
for(const metric of ["1m","20","trend","momentum"]){
  const missing=api.metricInterpretation(api.metricReceipt(fixture,"gold",metric),"en");
  assert.match(missing.supports,/unavailable.*no directional conclusion/);
  assert.doesNotMatch(missing.supports,/is zero|is flat|is neutral/);
}
assert.match(api.metricInterpretation(api.metricReceipt(fixture,"gas","20"),"en").supports,/20 trading sessions is negative/);
assert.doesNotMatch(api.metricInterpretation(api.metricReceipt(fixture,"gas","20"),"en").supports,/one-month/);
const mixed=structuredClone(fixture);
Object.assign(mixed.assets[0],{change_1m_pct:-4,trend:"up",momentum:"bear"});
assert.match(api.metricInterpretation(api.metricReceipt(mixed,"oil","trend"),"en").supports,/trend that is up.*Momentum is negative/);
assert.match(api.metricInterpretation(api.metricReceipt(mixed,"oil","momentum"),"zh").supports,/动能偏弱.*趋势向上/);
assert.match(api.physicalInterpretation(api.physicalReceipt(fixture,"crude_z"),"en").supports,/seasonal reference/);
assert.match(api.physicalInterpretation(api.physicalReceipt(fixture,"crude_z"),"en").doesNot,/five-year range.*probability/);
assert.match(api.physicalInterpretation(api.physicalReceipt(fixture,"days_supply"),"en").supports,/unavailable/);
assert.match(api.physicalInterpretation(api.physicalReceipt(fixture,"days_supply"),"en").doesNot,/exhaustion date/);
const zeroCover=structuredClone(fixture);
zeroCover.physical.evidence.days_supply.value=0;
assert.match(api.physicalInterpretation(api.physicalReceipt(zeroCover,"days_supply"),"zh").supports,/库存水平.*日均流量之比/);
assert.doesNotMatch(api.physicalInterpretation(api.physicalReceipt(zeroCover,"days_supply"),"en").supports,/unavailable/);
const physicalKinds={refinery_util:[90,"utilisation",/capacity-use ratio/,/产能使用比例/],spr_chg_4w_mb:[-3,"change_4w",/inventory change/,/库存净变化/],cushing_stocks_mb:[0,"level",/inventory level/,/库存水平/],production_chg_4w:[0,"production_change",/daily production rate/,/日均产量/],production_mbd:[13,"flow",/physical flow/,/实物流量/]};
for(const [key,[value,kind,en,zh]] of Object.entries(physicalKinds)){
  fixture.physical.flows.push({id:key,label:{en:key,zh:key}});
  fixture.physical.evidence[key]={value};
  const receipt=api.physicalReceipt(fixture,key);
  assert.equal(receipt.kind,kind);
  assert.match(api.physicalInterpretation(receipt,"en").supports,en);
  assert.match(api.physicalInterpretation(receipt,"zh").supports,zh);
  if(kind!=="flow")assert.doesNotMatch(api.physicalInterpretation(receipt,"en").supports,/recorded physical flow/);
}
for(const key of ["unknown_field","constructor","toString","__proto__"]){
  fixture.physical.flows.push({id:key,label:{en:key,zh:key}});
  Object.defineProperty(fixture.physical.evidence,key,{value:{value:1},enumerable:true,configurable:true});
  assert.equal(api.physicalReceipt(fixture,key),null);
}
console.log("PASS intersecting universe filters, unknown states, null-last sorting, URL context and field-specific receipts");

const html = fs.readFileSync(path.join(root, "site/commodities.html"), "utf8");
const dom = new JSDOM(html, {url:"https://www.mastermind-x.com/commodities.html#cw/compare/oil?window=1m&compare=oil%2Cgold", runScripts:"outside-only"});
const w = dom.window, d = w.document;
w.HTMLElement.prototype.scrollIntoView = function() {};
w.scrollTo = function() {};
const payload = d.getElementById("cw-data"), data = JSON.parse(payload.textContent);
Object.assign(data.assets.find(a => a.id === "oil"), {change_1m_pct:0, returns:{"5":null,"20":5,"60":null,"252":1}});
Object.assign(data.assets.find(a => a.id === "gold"), {change_1m_pct:null, returns:{"5":null,"20":-10,"60":0,"252":2}});
payload.textContent = JSON.stringify(data);
w.eval(fs.readFileSync(path.join(root, "templates/commodity-workspace.js"), "utf8"));
const q = selector => {const node = d.querySelector(selector); assert.ok(node, selector); return node;};
const change = (selector, value) => {const node=q(selector); node.value=value; node.dispatchEvent(new w.Event("change", {bubbles:true}));};
const mark = asset => q('[data-cw-compare-plot="'+asset+'"] [data-cw-plot-mark]');
const note = () => q("[data-cw-note-window]").textContent;

(async () => {
  change("[data-cw-window]", "20");
  assert.match(q("#cw-compare-status").textContent,/series bases not verified/);
  assert.equal(mark("oil").style.width, "25%");
  assert.equal(mark("gold").style.width, "50%");
  assert.ok(mark("gold").classList.contains("cw-bar-negative"));
  change("[data-cw-window]", "60");
  assert.equal(mark("oil").hidden, true);
  assert.equal(mark("gold").hidden, false);
  assert.equal(mark("gold").style.width, "0%");
  assert.equal(q('[data-cw-compare-plot="gold"] [data-cw-plot-value]').textContent, "0.0%");
  q('[data-cw-compare][value="oil"]').click();
  q('[data-cw-compare][value="gold"]').click();
  assert.equal(q("[data-cw-compare-empty]").hidden, false);
  assert.equal(q(".cw-plot-axis").hidden, true);
  assert.equal(d.querySelectorAll("[data-cw-compare-plot]:not([hidden])").length, 0);

  q("#cw-tab-research").click();
  // A browse-window change must not silently choose the research draft window.
  assert.equal(note(), "Choose a lookback window");
  change('[name="window_sessions"]', "252");
  assert.equal(note(), "252 trading sessions");
  change('#cw-research-form [name="asset"]', "gold");
  change('#cw-research-form [name="asset"]', "oil");
  assert.equal(q('[name="window_sessions"]').value, "252");
  assert.equal(note(), "252 trading sessions");
  d.documentElement.setAttribute("data-lang", "zh");
  await new Promise(resolve => setTimeout(resolve, 10));
  assert.equal(note(), "252个交易日");
  console.log("PASS signed shared scale, null/zero distinction, empty selection, draft context and language");
})().catch(error => {console.error(error);process.exitCode=1;});
