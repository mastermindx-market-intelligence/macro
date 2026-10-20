/* Rendered-DOM journey tests. jsdom supplies DOM semantics; no network or browser profile. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {JSDOM,VirtualConsole} = require("jsdom");
const root = path.resolve(__dirname,"..");
const api = require(path.join(root,"templates/commodity-workspace.js"));
const html = fs.readFileSync(path.join(root,"site/commodities.html"),"utf8").replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi,"");
const output = [];
const consoleErrors = [];
const virtual = new VirtualConsole();
virtual.on("jsdomError",e => consoleErrors.push(e.message));
const dom = new JSDOM(html,{url:"https://commodity-review.test/commodities.html",runScripts:"outside-only",pretendToBeVisual:true,virtualConsole:virtual});
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

(async()=>{
  check("default overview and dated evidence",()=>{
    assert.equal(q('#cw-panel-overview').hidden,false);
    assert.equal(q('#cw-panel-explore').hidden,true);
    assert.ok(api.validDate(data.as_of));assert.equal(data.assets.length,17);
    assert.ok(q('#cw-panel-overview').textContent.includes("Inflation link unconfirmed"));
  });
  click('#cw-panel-overview [data-cw-open="oil"]');
  check("commodity selection hides overview hero and keeps URL context",()=>{
    assert.equal(q('[data-cw-overview-only]').hidden,true);
    assert.equal(q('#cw-panel-explore').hidden,false);
    assert.equal(api.readState(w.location.hash,data).asset,"oil");
  });
  click('[data-cw-hypothesis="oil"] input[value="supply"]');tab("relationships");
  const supplyMechanism = q('#cw-investigation-mechanism').textContent;
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
    assert.equal(api.readState(w.location.hash,data).hypothesis,'demand');
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
    assert.deepEqual(api.validateDraft(exported,data,true).errors,[]);
  });
  check("Gold export retains its regional proxy and excludes petroleum context",()=>{
    const evidence=api.conditionSemantics(data,"gold",20,"rates").as_saved_evidence;
    assert.equal(evidence.gold_physical.method,"close_proxy");
    assert.equal(evidence.gold_physical.clock,"2026-10-14 07:30 UTC");
    assert.equal(evidence.gold_physical.hypothesis_confirmation_eligible,false);
    assert.equal(evidence.physical,null);
  });
  check("incompatible or incomplete imports do not silently change their semantics",()=>{
    for(const key of ["basis","contract","as_of","metric_contract","source_dependencies","as_saved_evidence"]){
      const edited=JSON.parse(JSON.stringify(exported));edited[key]="changed";
      assert.ok(api.validateDraft(edited,data,true).errors.includes(key),key);
    }
    const edited=JSON.parse(JSON.stringify(exported));delete edited.as_saved_evidence;
    assert.ok(api.validateDraft(edited,data,true).errors.includes("as_saved_evidence"));
  });
  tab('explore');click('[data-cw-hypothesis="oil"] input[value="demand"]');
  const importFile=q('#cw-import-file');
  Object.defineProperty(importFile,'files',{configurable:true,value:[{size:output[0].size,text:async()=>JSON.stringify(exported)}]});
  importFile.dispatchEvent(new w.Event('change',{bubbles:true}));await pause();tab('relationships');
  check("import restores the same explanation into relationships and research",()=>{
    assert.equal(api.readState(w.location.hash,data).hypothesis,'supply');
    assert.ok(q('#cw-investigation-title').textContent.includes('Supply disruption'));
    assert.equal(q('#cw-investigation-mechanism').textContent,supplyMechanism);
    assert.ok(q('#cw-research-hypothesis').textContent.includes('Supply disruption'));
  });
  const stale={...exported,snapshot_fingerprint:'other-snapshot'};
  Object.defineProperty(importFile,'files',{configurable:true,value:[{size:100,text:async()=>JSON.stringify(stale)}]});
  importFile.dispatchEvent(new w.Event('change',{bubbles:true}));await pause();
  check("a stale import preserves the active investigation",()=>{
    assert.equal(api.readState(w.location.hash,data).hypothesis,'supply');
    assert.equal(q('#cw-investigation-mechanism').textContent,supplyMechanism);
    assert.ok(q('#cw-export-status').textContent.includes('different research snapshot'));
  });
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
    assert.equal(q('#cw-panel-compare').hidden,false);assert.equal(q('#cw-panel-research').hidden,true);
  });
  check("rendered DOM has no duplicate IDs or event errors",()=>{
    const ids=Array.from(d.querySelectorAll('[id]'),el=>el.id);assert.equal(new Set(ids).size,ids.length);
    assert.deepEqual(consoleErrors,[]);
  });
  fs.writeFileSync(process.env.CW_UI_RECEIPT || '/tmp/commodity-workspace-ui-receipt.json',JSON.stringify({passed,assets:data.assets.length,snapshot:data.fingerprint,export_bytes:output[0].size,visual_layout_verified:false},null,2)+'\n');
  console.log('RESULT',passed,'rendered-DOM journeys passed; this is not a visual-layout proof.');
  dom.window.close();
})().catch(error=>{console.error(error);dom.window.close();process.exitCode=1;});
