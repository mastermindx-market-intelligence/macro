/* Rendered-DOM journey tests. jsdom supplies DOM semantics; no network or browser profile. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {JSDOM,VirtualConsole} = require("jsdom");
const {spawnSync} = require("node:child_process");
const root = path.resolve(__dirname,"..");
const api = require(path.join(root,"templates/commodity-workspace.js"));
const publishedHTML = fs.readFileSync(path.join(root,"site/commodities.html"),"utf8").replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi,"");
// The live publisher may honestly have no identity-qualified companies. Keep
// that data honest and test the link contract with explicitly synthetic cohorts.
// Render the real component; hand-built anchors would miss a broken template.
const cohortRenderer = [
  "import json, sys",
  "from pathlib import Path",
  "from jinja2 import Environment, FileSystemLoader, StrictUndefined",
  "root = Path(sys.argv[1])",
  "payloads = json.load(sys.stdin)",
  "env = Environment(loader=FileSystemLoader(root / 'templates'), autoescape=True, undefined=StrictUndefined)",
  "macro = '{% macro t(en,zh) %}<span class=\"l-en\">{{ en }}</span><span class=\"l-zh\">{{ zh }}</span>{% endmacro %}'",
  "template = env.from_string(macro + '{% include \"_commodity_decision_workspace.html.j2\" %}')",
  "json.dump({name: template.render(commodity_workspace=payload) for name, payload in payloads.items()}, sys.stdout)"
].join("\n");
function assertPublishedGoldLinks(source, document) {
  // Match the canonical template's chain.id-to-asset mapping.
  const expected = source.chains.filter(chain => chain.id.includes("gold")).flatMap(
    chain => (chain.cohorts || []).flatMap(
      cohort => (cohort.companies?.linked || []).slice(0,6).map(company => company.href)));
  const actual = Array.from(document.querySelectorAll(
    '[data-cw-chain-asset="gold"] a[data-cw-company-href]'), link => link.dataset.cwCompanyHref);
  assert.deepEqual(actual.sort(), expected.sort(), "published Gold company links differ from source");
}

function renderCompanyCohortFixtures(publishedHTML) {
  const source = new JSDOM(publishedHTML,{includeNodeLocations:true});
  const mount = source.window.document.getElementById("commodity-workspace");
  assert.ok(mount,"published workspace mount");
  assert.equal(source.window.document.querySelectorAll("#commodity-workspace").length,1);
  assert.equal(mount.querySelectorAll("#cw-data").length,1);
  const location = source.nodeLocation(mount);
  assert.ok(location && location.endOffset > location.startOffset,"bounded workspace source");
  const published = JSON.parse(mount.querySelector("#cw-data").textContent);
  // Keep the actual publisher boundary independently of the controlled cohort.
  const publishedOwnerLinked = published.chains.some(chain => (chain.cohorts || []).some(
    cohort => (cohort.companies?.linked || []).length > 0));
  const publishedCompanyLinks = mount.querySelectorAll('a[data-cw-company-href]').length;
  if (publishedOwnerLinked) assert.ok(publishedCompanyLinks > 0, "owner-backed company links omitted");
  else assert.equal(publishedCompanyLinks, 0, "unqualified company link was published");
  assertPublishedGoldLinks(published, source.window.document);
  const payloads = {};
  for (const mode of ["linked","empty","unavailable"]) {
    const payload = JSON.parse(JSON.stringify(published));
    // Do not let whichever real cohorts happen to be published supply coverage.
    payload.chains = payload.chains.map(chain => ({...chain,cohorts:[]}));
    const cohort = {
      label:{en:"SYNTHETIC TEST COHORT",zh:"合成测试群组"},
      note:{en:"Fixture only; no publisher identity or investment claim.",zh:"仅用于测试，不构成发布方身份或投资结论。"},
      count:mode === "linked" ? 1 : null,unevaluable:null,
      companies:{
        state:mode === "linked" ? "available" : "unavailable",
        linked_count:mode === "linked" ? 1 : 0,
        linked:mode === "linked" ? [{
          symbol:"TEST",
          href:"https://app.mastermind-x.com/analysis?page=intelligence&entity_id=SYNTHETIC-COMPANY&symbol=TEST&owner=fixture"
        }] : []
      }
    };
    payload.chains.push({
      id:"gold_company_return_fixture",title:{en:"SYNTHETIC company-return fixture",zh:"合成企业返回测试"},
      applicability:"unavailable",source_state:"unavailable",as_of:payload.as_of,
      conflicts:[],nodes:[],hops:[],current_checks_met:0,current_checks_total:0,
      episode_id:null,cohorts:mode === "empty" ? [] : [cohort]
    });
    payload.test_fixture="company-return-cohort:"+mode;
    payload.fingerprint=require("node:crypto").createHash("sha256").update(JSON.stringify(payload)).digest("hex");
    payloads[mode]=payload;
  }
  source.window.close();
  const rendered=spawnSync(process.env.PYTHON || "python3",["-c",cohortRenderer,root],{
    input:JSON.stringify(payloads),encoding:"utf8",maxBuffer:8*1024*1024,timeout:15000
  });
  assert.ifError(rendered.error);
  assert.equal(rendered.status,0,"actual Jinja component render: "+rendered.stderr);
  const components=JSON.parse(rendered.stdout),html={};
  for (const mode of Object.keys(payloads)) {
    assert.equal(typeof components[mode],"string",mode+" render result");
    html[mode]=publishedHTML.slice(0,location.startOffset)+components[mode]+publishedHTML.slice(location.endOffset);
  }
  return {html,publishedFingerprint:published.fingerprint,publishedCompanyLinks,publishedOwnerLinked};
}
const cohortFixtures=renderCompanyCohortFixtures(publishedHTML);
const html=cohortFixtures.html.linked;

const output = [];
const consoleErrors = [];
const virtual = new VirtualConsole();
virtual.on("jsdomError",e => consoleErrors.push(e.message));
const dom = new JSDOM(html,{url:"https://www.mastermind-x.com/commodities.html?ret=https%3A%2F%2Fevil.example",runScripts:"outside-only",pretendToBeVisual:true,virtualConsole:virtual});
const {window:w} = dom;
const d = w.document;
w.HTMLElement.prototype.scrollIntoView=function(){};
w.scrollTo=function(){};
w.Blob=Blob;
w.URL.createObjectURL=blob => {output.push(blob);return "blob:commodity-review";};
w.URL.revokeObjectURL=function(){};
const originalAnchorClick=w.HTMLAnchorElement.prototype.click;
w.HTMLAnchorElement.prototype.click=function(){if(!this.download)originalAnchorClick.call(this);};
for(const script of d.querySelectorAll("script:not([src])")){
  if(script.textContent.includes("dataset.detpanel") && !script.textContent.includes('getElementById("cw-data")'))w.eval(script.textContent);
}
w.eval(fs.readFileSync(path.join(root,"templates/commodity-workspace.js"),"utf8"));
const data=JSON.parse(d.getElementById("cw-data").textContent);
const q=s=>{const el=d.querySelector(s);assert.ok(el,s);return el;};
const click=s=>q(s).click();
const change=(s,value)=>{const el=q(s);el.value=value;el.dispatchEvent(new w.Event("change",{bubbles:true}));};
const tab=name=>click('#cw-tab-'+name);
const pause=()=>new Promise(resolve=>setTimeout(resolve,35));
let passed=0;
function check(name,fn){fn();passed++;console.log("PASS",name);}
function checkCompanyReturn(selector='[data-cw-company-href]') {
  const link=q(selector), original=new URL(link.dataset.cwCompanyHref), current=new URL(link.href);
  for (const [key,value] of original.searchParams) assert.equal(current.searchParams.get(key),value,key);
  assert.deepEqual(Array.from(current.searchParams.keys()).sort(),Array.from(original.searchParams.keys()).concat("from","ret").sort());
  assert.equal(current.searchParams.get("from"),"macro");
  assert.equal(current.searchParams.getAll("ret").length,1);
  const back=new URL(current.searchParams.get("ret"));
  assert.equal(back.origin,w.location.origin);assert.equal(back.pathname,"/commodities.html");assert.equal(back.search,"");
  assert.deepEqual(api.readState(back.hash,data),api.readState(w.location.hash,data));
  assert.equal(link.target,"_blank");assert.equal(link.rel,"noopener");
  return current.href;
}

async function checkMissingCompanyCohort(mode) {
  const errors=[],vc=new VirtualConsole();
  vc.on("jsdomError",error=>errors.push(error.message));
  const fixture=new JSDOM(cohortFixtures.html[mode],{
    url:"https://www.mastermind-x.com/commodities.html",runScripts:"outside-only",
    pretendToBeVisual:true,virtualConsole:vc
  });
  const fw=fixture.window,fd=fw.document;
  fw.HTMLElement.prototype.scrollIntoView=function(){};
  fw.scrollTo=function(){};
  try {
    fw.eval(fs.readFileSync(path.join(root,"templates/commodity-workspace.js"),"utf8"));
    const payload=JSON.parse(fd.getElementById("cw-data").textContent);
    assert.equal(payload.test_fixture,"company-return-cohort:"+mode);
    const get=selector=>{const el=fd.querySelector(selector);assert.ok(el,selector);return el;};
    const noCompanyLink=()=>{
      assert.equal(fd.querySelectorAll("[data-cw-company-href]").length,0,mode);
      assert.equal(fd.querySelectorAll(".cw-cohorts a").length,0,mode);
    };
    noCompanyLink();
    assert.equal(fd.querySelectorAll(".cw-cohorts").length,mode === "empty" ? 0 : 1);
    get("#cw-tab-relationships").click();
    const select=get("[data-cw-relationship-asset]");
    select.value="gold";select.dispatchEvent(new fw.Event("change",{bubbles:true}));
    assert.equal(api.readState(fw.location.hash,payload).asset,"gold");
    assert.equal(get("#cw-panel-relationships").hidden,false);
    noCompanyLink();
    get("#cw-tab-research").click();
    assert.equal(get("#cw-panel-research").hidden,false);
    assert.equal(get('#cw-research-form [name="asset"]').value,"gold");
    get("#cw-tab-compare").click();
    const windowSelect=get("[data-cw-window]");
    windowSelect.value="60";windowSelect.dispatchEvent(new fw.Event("change",{bubbles:true}));
    assert.equal(get("#cw-panel-compare").hidden,false);
    assert.equal(api.readState(fw.location.hash,payload).window,"60");
    fd.documentElement.dataset.lang="zh";
    fd.dispatchEvent(new fw.Event("langchange"));
    await new Promise(resolve=>setTimeout(resolve,35));
    noCompanyLink();
    assert.deepEqual(errors,[]);
  } finally {
    fixture.window.close();
  }
}

(async()=>{
  check("another chain cannot conceal omitted authorized Gold links",()=>{
    const mixed = d.createElement("div");
    const other = d.createElement("section");other.dataset.cwChainAsset="oil";
    const link = d.createElement("a");link.dataset.cwCompanyHref="https://app.mastermind-x.com/analysis?symbol=A";
    other.appendChild(link);mixed.appendChild(other);
    const source = {chains:[{id:"real_rate_peak_gold_rerate",cohorts:[{companies:{linked:[{href:link.dataset.cwCompanyHref}]}}]}]};
    assert.throws(()=>assertPublishedGoldLinks(source,mixed),/published Gold company links differ from source/);
  });
  check("source-backed company links obey the publisher's honest absence",()=>{
    assert.equal(cohortFixtures.publishedCompanyLinks > 0, cohortFixtures.publishedOwnerLinked);
  });
  check("controlled company links come from the actual template",()=>{
    assert.equal(data.test_fixture,"company-return-cohort:linked");
    assert.equal(d.querySelectorAll("[data-cw-company-href]").length,1);
    assert.equal(new URL(q("[data-cw-company-href]").dataset.cwCompanyHref).searchParams.get("owner"),"fixture");
  });
  check("default overview and dated evidence",()=>{
    assert.equal(q('#cw-panel-overview').hidden,false);
    assert.equal(q('#cw-panel-explore').hidden,true);
    assert.ok(api.validDate(data.as_of));assert.equal(data.assets.length,17);
    for (const id of data.attention) {
      const asset = data.assets.find(a => a.id === id);
      assert.ok(q('#cw-panel-overview .cw-focus[data-cw-open="'+id+'"]').textContent.includes(asset.read.headline.en));
    }
  });
  click('#cw-panel-overview [data-cw-open="oil"]');
  check("commodity selection hides overview hero and keeps URL context",()=>{
    assert.equal(q('[data-cw-overview-only]').hidden,true);
    assert.equal(q('#cw-panel-explore').hidden,false);
    assert.equal(api.readState(w.location.hash,data).asset,"oil");
  });
  click('[data-cw-hypothesis="oil"] input[value="supply"]');tab("relationships");
  const supplyMechanism = q('#cw-investigation-mechanism').textContent;
  check("company continuation preserves owner fields and the current investigation",()=>{checkCompanyReturn();});
  check("relationships carries a selected explanation without treating it as evidence",()=>{
    assert.ok(q('#cw-investigation-title').textContent.includes("Supply disruption"));
    assert.ok(q('#cw-investigation-state').textContent.includes("has not established"));
    assert.equal(q('#cw-investigation-tests').hidden,false);
    assert.ok(q('#cw-investigation-support').textContent.length>20);
    assert.ok(q('#cw-investigation-invalidate').textContent.length>20);
  });
  tab('explore');click('[data-cw-hypothesis="oil"] input[value="demand"]');tab('relationships');
  check("changing explanation changes the mechanism and its evidence questions together",()=>{
    assert.ok(q('#cw-investigation-title').textContent.includes("Demand expansion"));
    assert.notEqual(q('#cw-investigation-mechanism').textContent,supplyMechanism);
    assert.equal(api.readState(w.location.hash,data).hypothesis,'demand');checkCompanyReturn();
  });
  check("company return transport is bounded, single-encoded and idempotent",()=>{
    const original=q('[data-cw-company-href]').dataset.cwCompanyHref, state=api.readState(w.location.hash,data);
    for (const origin of ["https://www.mastermind-x.com","https://mastermind-x.com","https://beta.mastermind-x.com"]) {
      const current=api.companyReturnHref(original,state,origin+"/commodities.html?ret=https://evil.example");
      assert.equal(new URL(current).searchParams.get("ret"),origin+"/commodities.html"+api.stateHash(state));
      assert.equal(api.companyReturnHref(current,state,origin+"/commodities.html"),current);
    }
    for (const page of ["https://evil.example/commodities.html","https://www.mastermind-x.com.evil.example/commodities.html","http://www.mastermind-x.com/commodities.html","http://127.0.0.1:8000/commodities.html","https://www.mastermind-x.com/other.html","https://name:pass@www.mastermind-x.com/commodities.html"]) {
      assert.equal(api.companyReturnHref(original,state,page),original,page);
    }
    for (const target of ["https://app.mastermind-x.com.evil.example/analysis?page=intelligence","https://name:pass@app.mastermind-x.com/analysis?page=intelligence","https://app.mastermind-x.com/terminal?page=intelligence","https://app.mastermind-x.com/analysis?page=other"]) {
      assert.equal(api.companyReturnHref(target,state,w.location.href),target,target);
    }
  });
  tab('explore');click('[data-cw-hypothesis="oil"] input[value="supply"]');tab("research");
  check("research exposes explanation and requires a session window",()=>{
    assert.ok(q('#cw-research-hypothesis').textContent.includes("Supply disruption"));
    assert.equal(q('[name="window_sessions"]').value,"");
    assert.equal(q('#cw-research-form').checkValidity(),false);
  });
  change('[name="window_sessions"]','20');change('[name="threshold"]','0');change('[name="expires_on"]','2099-01-01');
  change('#cw-research-form [name="asset"]','copper');change('#cw-research-form [name="asset"]','oil');
  check("per-commodity draft preserves its explanation and exact numeric condition",()=>{
    assert.equal(q('[name="threshold"]').value,"0");assert.equal(q('[name="window_sessions"]').value,"20");
    assert.equal(api.readState(w.location.hash,data).hypothesis,"supply");
  });
  q('#cw-research-form').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
  const exported=JSON.parse(await output[0].text());
  check("export includes a recoverable evidence appendix and stays inactive",()=>{
    assert.equal(exported.threshold,0);assert.equal(exported.metric_contract.field,"velocity.r20");
    assert.equal(exported.as_saved_evidence.asset.id,"oil");assert.equal(exported.as_saved_evidence.hypothesis.id,"supply");
    assert.equal(exported.monitoring_active,false);assert.equal(exported.effect,"export_only");
    assert.ok(output[0].size<=131072,"own export must fit the import limit");
    assert.deepEqual(api.checkDraft(exported,data,true).errors,[]);
  });
  check("Gold export retains its regional proxy and excludes petroleum context",()=>{
    const evidence=api.conditionSemantics(data,"gold",20,"rates").as_saved_evidence;
    assert.deepEqual(evidence.gold_physical,data.gold_physical);
    assert.equal(evidence.gold_physical.hypothesis_confirmation_eligible,false);
    assert.equal(evidence.physical,null);
  });
  check("incompatible or incomplete imports do not silently change their semantics",()=>{
    for(const key of ["basis","contract","as_of","metric_contract","source_dependencies","as_saved_evidence"]){
      const edited=JSON.parse(JSON.stringify(exported));edited[key]="changed";
      assert.ok(api.checkDraft(edited,data,true).errors.includes(key),key);
    }
    const edited=JSON.parse(JSON.stringify(exported));delete edited.as_saved_evidence;
    assert.ok(api.checkDraft(edited,data,true).errors.includes("as_saved_evidence"));
  });
  tab('explore');click('[data-cw-hypothesis="oil"] input[value="demand"]');
  const importFile=q('#cw-import-file');
  Object.defineProperty(importFile,'files',{configurable:true,value:[{size:output[0].size,text:async()=>JSON.stringify(exported)}]});
  importFile.dispatchEvent(new w.Event('change',{bubbles:true}));await pause();tab('relationships');
  check("import restores the same explanation into relationships and research",()=>{
    assert.equal(api.readState(w.location.hash,data).hypothesis,'supply');
    assert.ok(q('#cw-investigation-title').textContent.includes('Supply disruption'));
    assert.equal(q('#cw-investigation-mechanism').textContent,supplyMechanism);
    assert.ok(q('#cw-research-hypothesis').textContent.includes('Supply disruption'));checkCompanyReturn();
  });
  const beforeStaleReturn=checkCompanyReturn();
  const stale={...exported,snapshot_fingerprint:'other-snapshot'};
  Object.defineProperty(importFile,'files',{configurable:true,value:[{size:100,text:async()=>JSON.stringify(stale)}]});
  importFile.dispatchEvent(new w.Event('change',{bubbles:true}));await pause();
  check("a stale import preserves the active investigation",()=>{
    assert.equal(api.readState(w.location.hash,data).hypothesis,'supply');
    assert.equal(q('#cw-investigation-mechanism').textContent,supplyMechanism);
    assert.ok(q('#cw-export-status').textContent.includes('different research snapshot'));assert.equal(checkCompanyReturn(),beforeStaleReturn);
  });
  const preservedHash=w.location.hash, preservedReturn=checkCompanyReturn();
  const malformedAssets=["constructor","__proto__","toString",{},["oil"],"unknown"];
  for (const asset of malformedAssets) {
    Object.defineProperty(importFile,'files',{configurable:true,value:[{size:1000,text:async()=>JSON.stringify({...exported,asset})}]});
    importFile.dispatchEvent(new w.Event('change',{bubbles:true}));await pause();
    assert.equal(w.location.hash,preservedHash);assert.equal(checkCompanyReturn(),preservedReturn);
    assert.ok(q('#cw-export-status').textContent.includes('failed validation'));
    assert.equal(importFile.value,"");
  }
  let deep={};for(let i=0;i<100;i++)deep={nested:deep};
  const deepDraft=JSON.stringify({...exported,as_saved_evidence:deep});
  assert.ok(Buffer.byteLength(deepDraft)<131072);
  Object.defineProperty(importFile,'files',{configurable:true,value:[{size:Buffer.byteLength(deepDraft),text:async()=>deepDraft}]});
  importFile.dispatchEvent(new w.Event('change',{bubbles:true}));await pause();
  check("malformed assets and deeply nested imports reject without changing the investigation",()=>{
    assert.equal(w.location.hash,preservedHash);assert.equal(checkCompanyReturn(),preservedReturn);
    assert.equal(q('[name="threshold"]').value,"0");
    assert.ok(q('#cw-export-status').textContent.includes('failed validation'));assert.equal(importFile.value,"");
  });
  let completeOld;
  Object.defineProperty(importFile,'files',{configurable:true,value:[{size:1000,text:()=>new Promise(resolve=>{completeOld=resolve;})}]});
  importFile.dispatchEvent(new w.Event('change',{bubbles:true}));
  const newerDraft={...exported,threshold:17};
  Object.defineProperty(importFile,'files',{configurable:true,value:[{size:1000,text:async()=>JSON.stringify(newerDraft)}]});
  importFile.dispatchEvent(new w.Event('change',{bubbles:true}));await pause();
  const newerStatus=q('#cw-export-status').textContent;
  completeOld(JSON.stringify(exported));await pause();
  check("a delayed earlier import cannot overwrite the most recent file selection",()=>{
    assert.equal(q('[name="threshold"]').value,"17");assert.equal(q('#cw-export-status').textContent,newerStatus);
    assert.equal(api.readState(w.location.hash,data).tab,"research");checkCompanyReturn();
  });
  let rejectOld;
  Object.defineProperty(importFile,'files',{configurable:true,value:[{size:1000,text:()=>new Promise((resolve,reject)=>{rejectOld=reject;})}]});
  importFile.dispatchEvent(new w.Event('change',{bubbles:true}));
  Object.defineProperty(importFile,'files',{configurable:true,value:[{size:1000,text:async()=>JSON.stringify(newerDraft)}]});
  importFile.dispatchEvent(new w.Event('change',{bubbles:true}));await pause();
  rejectOld(new Error("outdated file read failed"));await pause();
  check("a rejected outdated file read cannot clear the newer import status",()=>{
    assert.equal(q('[name="threshold"]').value,"17");assert.equal(q('#cw-export-status').textContent,newerStatus);
  });
  Object.defineProperty(importFile,'files',{configurable:true,value:[{size:1000,text:async()=>JSON.stringify(exported)}]});
  importFile.dispatchEvent(new w.Event('change',{bubbles:true}));await pause();
  tab('compare');
  click('[data-cw-compare][value="natgas"]');
  check("comparison selection is bounded to four without losing the chosen assets",()=>{
    assert.equal(q('[data-cw-compare][value="natgas"]').checked,false);
    assert.equal(api.readState(w.location.hash,data).compare.length,4);
  });
  change('[data-cw-window]','60');
  check("comparison uses the selected exact publisher window",()=>{
    const oil=data.assets.find(a=>a.id==='oil');
    assert.equal(q('[data-cw-return-cell="oil"]').textContent,(oil.returns['60']>0?'+':'')+oil.returns['60'].toFixed(1)+'%');
  });
  click('#cw-panel-compare [data-cw-open="gold"]');
  click('#cw-panel-explore [data-cw-asset="gold"] [data-cw-evidence="physical"]');
  await pause();
  check("gold physical handoff opens its real owner panel",()=>{
    assert.equal(q('#commodity-advanced').open,true);
    assert.equal(q('[data-detpanel="gold"]').hidden,false);
    assert.equal(d.activeElement.id,'gold-china-premium');
  });
  click('#cw-return');
  check("return restores the selected commodity and closes advanced analytics",()=>{
    assert.equal(q('#commodity-advanced').open,false);assert.equal(api.readState(w.location.hash,data).asset,'gold');
    assert.equal(q('#cw-panel-explore').hidden,false);
  });
  check("company return follows Gold and the selected comparison window",()=>{
    checkCompanyReturn('[data-cw-chain-asset="gold"] [data-cw-company-href]');
    assert.equal(api.readState(w.location.hash,data).asset,"gold");assert.equal(api.readState(w.location.hash,data).window,"60");
  });
  tab('relationships');change('[data-cw-relationship-asset]','corn');
  check("partial coverage has a real selected-commodity fallback",()=>{
    assert.equal(q('[data-cw-relationship-asset]').value,'corn');assert.equal(q('[data-cw-no-chain]').hidden,false);
    assert.ok(q('#cw-investigation-title').textContent.includes('Corn'));assert.equal(q('#cw-investigation-tests').hidden,true);
    assert.equal(q('#cw-investigation-support').textContent,'');assert.notEqual(q('#cw-investigation-mechanism').textContent,supplyMechanism);
  });
  d.documentElement.dataset.lang='zh';d.dispatchEvent(new w.Event('langchange'));
  check("Chinese native controls show Chinese labels",()=>{
    assert.equal(q('[data-cw-relationship-asset] option[value="corn"]').textContent,'玉米');
    assert.ok(q('#cw-investigation-title').textContent.includes('玉米'));assert.ok(q('#cw-investigation-mechanism').textContent.includes('实物市场'));
    assert.ok(q('[name="operator"] option[value="gte"]').textContent.includes('大于等于'));
  });
  tab('explore');q('#cw-tab-explore').dispatchEvent(new w.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));
  check("keyboard tabs move selection and focus together",()=>{
    assert.equal(q('#cw-tab-relationships').getAttribute('aria-selected'),'true');assert.equal(d.activeElement.id,'cw-tab-relationships');
  });
  tab('compare');tab('research');
  const historyRestored=new Promise((resolve,reject)=>{w.addEventListener('popstate',resolve,{once:true});setTimeout(()=>reject(new Error('History event did not arrive')),2000).unref();});
  w.history.back();await historyRestored;
  check("browser history restores the previous view",()=>{
    assert.equal(q('#cw-panel-compare').hidden,false);assert.equal(q('#cw-panel-research').hidden,true);checkCompanyReturn();
  });
  const directState=api.normalizeState({tab:"relationships",asset:"gold",window:"5",compare:["oil","gold"],hypothesis:"rates"},data);
  w.location.hash=api.stateHash(directState);await pause();
  check("direct hash and repeated language renders keep the exact company return",()=>{
    const before=checkCompanyReturn('[data-cw-chain-asset="gold"] [data-cw-company-href]');
    d.dispatchEvent(new w.Event('langchange'));d.dispatchEvent(new w.Event('langchange'));
    assert.equal(checkCompanyReturn('[data-cw-chain-asset="gold"] [data-cw-company-href]'),before);
    assert.deepEqual(api.readState(new URL(new URL(before).searchParams.get("ret")).hash,data),directState);
  });
  for (const mode of ["empty","unavailable"]) {
    await checkMissingCompanyCohort(mode);
    passed++;console.log("PASS",mode+" company cohort keeps navigation usable without fabricating links");
  }
  check("rendered DOM has no duplicate IDs or event errors",()=>{
    const ids=Array.from(d.querySelectorAll('[id]'),el=>el.id);assert.equal(new Set(ids).size,ids.length);
    assert.deepEqual(consoleErrors,[]);
  });
  fs.writeFileSync(process.env.CW_UI_RECEIPT || '/tmp/commodity-workspace-ui-receipt.json',JSON.stringify({passed,assets:data.assets.length,snapshot:data.fingerprint,published_snapshot:cohortFixtures.publishedFingerprint,source_company_links:cohortFixtures.publishedCompanyLinks,company_cohort_cases:["linked","empty","unavailable"],fixture_only:true,export_bytes:output[0].size,visual_layout_verified:false},null,2)+'\n');
  console.log('RESULT',passed,'rendered-DOM journeys passed; this is not a visual-layout proof.');
  dom.window.close();
})().catch(error=>{console.error(error);dom.window.close();process.exitCode=1;});
