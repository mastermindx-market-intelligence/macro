/* Behavior checks for the shipped renderer, without a browser or provider calls. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const {test} = require("node:test");

const source = fs.readFileSync(path.join(__dirname, "../static/capacity-router.js"), "utf8");
const exported = "window.CapacityRouter = {mount,unmount};";
assert.equal(source.split(exported).length, 2);
const context = {window:{}, document:{activeElement:null}, Intl, Date, console};
vm.runInNewContext(source.replace(exported,
  "window.CapacityRouter = {mount,unmount,trend,providerView,consumerView,renderInspector,handleClick};"), context);
const ui = context.window.CapacityRouter;
const now = 1800000000;

function request(id, model, extra={}) {
  return {id, requested_model:model, served_model:model, provider:"pool-a", route_id:"route-a",
    client:"sdk", lane:"direct", agent_id:null, parent_agent_id:null, session_id:id,
    started_at:now-30, ended_at:null, first_content_at:now-20, state:"streaming",
    identity_source:"sdk_session", usage:{input_tokens:10,output_tokens:5}, attempts:[], ...extra};
}
function state(active=[]) {
  return {data:{ok:true,generated_at:now,started_at:now-600,active,recent:[],aliases:{},series:[],
    summary:{models:2,output_tokens:10,usage_known:1},
    routes:[{id:"route-a",provider:"pool-a",models:["model-a","model-b"],wire:"anthropic",
      priority:1,weight:1,served:100,attempt_failed:2,cooling:false}]},
    minutes:5, model:"all",status:"all",query:"",selected:null,view:"consumers",page:0};
}
function attachDom(s) {
  const nodes = new Map();
  for(const key of [".cf-view",".cf-clear",".cf-inspector",".cf-inspector-body","input",
    '[data-field="model"]','[data-field="status"]']) nodes.set(key,{innerHTML:"",value:""});
  s.root = {querySelector:key=>nodes.get(key),querySelectorAll:()=>[],contains:()=>false};
  return nodes;
}

test("mixed known and unknown minutes never label absent usage as zero", () => {
  const s=state();
  s.data.series=[{at:now-120,completed:1,failed:0,usage_known:0,output_tokens:0},
    {at:now-60,completed:1,failed:0,usage_known:1,output_tokens:10}];
  const html=ui.trend(s);
  assert.match(html,/cf-usage-unknown/);
  assert.match(html,/Output usage not reported · 1 finished requests/);
  assert.doesNotMatch(html,/(?<!1)0 reported output tokens/);
  assert.match(html,/10 reported output tokens/);
});

test("a real provider-reported zero remains a reported zero", () => {
  const s=state();s.data.series=[{at:now-60,completed:1,failed:0,usage_known:1,output_tokens:0}];
  const html=ui.trend(s);
  assert.match(html,/0 reported output tokens/);
  assert.doesNotMatch(html,/class="cf-usage-unknown"/);
});

test("chart geometry stays anchored to its retained snapshot", () => {
  const s=state();s.data.series=[{at:now-60,completed:1,failed:0,usage_known:1,output_tokens:10}];
  const before=ui.trend(s),original=context.Date;
  context.Date=class extends Date {static now(){return (now+36000)*1000;}};
  assert.equal(ui.trend(s),before);context.Date=original;
});

test("child selection preserves a retained parent even outside filters", () => {
  const s=state([request("p","model-a",{agent_id:"parent"}),
    request("c","model-b",{agent_id:"child",parent_agent_id:"parent"})]);
  s.selected={kind:"consumer",id:"child"};s.model="model-b";
  const html=ui.consumerView(s);
  assert.match(html,/data-id="parent" data-reveal-parent="true"/);
  assert.match(html,/retained, outside current selection/);
  assert.doesNotMatch(html,/not observed in retained history/);
});

test("session ID collision is not proof that a parent agent was retained", () => {
  const s=state([request("p","model-a",{session_id:"parent"}),
    request("c","model-b",{agent_id:"child",parent_agent_id:"parent"})]);
  const html=ui.consumerView(s);
  assert.match(html,/not observed in retained history/);
  assert.doesNotMatch(html,/data-reveal-parent/);
});

test("following a retained parent reveals it and clears incompatible filters", () => {
  const s=state([request("p","model-a",{agent_id:"parent"}),
    request("c","model-b",{agent_id:"child",parent_agent_id:"parent"})]);
  s.selected={kind:"consumer",id:"child"};s.model="model-b";s.query="child";s.status="waiting";
  const nodes=attachDom(s);
  const selected={dataset:{select:"consumer",id:"parent",revealParent:"true"}};
  ui.handleClick(s,{target:{closest:selector=>selector==="[data-select]"?selected:null}});
  assert.equal(s.selected.id,"parent");assert.equal(s.model,"all");assert.equal(s.status,"all");assert.equal(s.query,"");
  assert.match(nodes.get(".cf-view").innerHTML,/data-id="parent"/);
  assert.match(nodes.get(".cf-inspector-body").innerHTML,/<b>1<\/b><small>Observed calls/);
});

test("provider active count and inspector honor model, state and search filters", () => {
  const s=state([request("a","model-a"),request("b","model-b"),request("c","model-b")]);
  s.model="model-a";s.selected={kind:"provider",id:"pool-a"};
  const nodes=attachDom(s);
  assert.match(ui.providerView(s),/cf-provider-live">1<small>active/);
  ui.renderInspector(s);
  assert.match(nodes.get(".cf-inspector-body").innerHTML,/<b>1<\/b><small>Observed calls/);
  s.status="waiting";
  assert.match(ui.providerView(s),/cf-provider-live">0<small>active/);
  ui.renderInspector(s);
  assert.match(nodes.get(".cf-inspector-body").innerHTML,/<b>0<\/b><small>Observed calls/);
  s.status="all";s.query="absent-consumer";
  ui.renderInspector(s);
  assert.match(nodes.get(".cf-inspector-body").innerHTML,/<b>0<\/b><small>Observed calls/);
});
