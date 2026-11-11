#!/usr/bin/env node
// Exact current selection and URL helpers, with no DOM, fetch, authentication or real storage.
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const crypto = require("node:crypto");
const assert = require("node:assert/strict");
const base = __dirname;
const fixture = JSON.parse(fs.readFileSync(path.join(base,"BIOCATALYST_SELECTION_FIXTURES.json"),"utf8"));
const sourcePath = process.argv[2] || path.join(base,"source_inputs/biocatalyst.js");
const outputPath = process.argv[3] || path.join(base,"BIOCATALYST_SELECTION_CHARACTERIZATION.json");
const source = fs.readFileSync(sourcePath,"utf8");
const digest = crypto.createHash("sha256").update(source).digest("hex");
assert.equal(digest,fixture.source_sha256);
const names = ["str","clean","valueAt","nctOf","unique","dateParts","fullDate","isTrialId","parseCohort","defaultFilters",
  "isMilestonesMode","isChangeMode","isProspectiveMode","isScreenMode","isPeerMode","activeChangeKind",
  "milestoneIdentity","changeIdentity","prospectiveIdentity","screenIdentity","rowIdentity","rowTrial",
  "selectedRow","readUrl","writeUrl"];
const extracted = names.map(name => {
  const start = source.indexOf("function "+name+"(");
  assert(start >= 0, name);
  const end = source.indexOf("\n  function ", start + 1);
  assert(end > start, name+" boundary");
  const code = source.slice(start,end);
  return {name,code,first_line:source.slice(0,start).split("\n").length,last_line:source.slice(0,end).split("\n").length};
});
const constantNames = ["TRIAL_ID","DATE_PARTS","WINDOW_VALUES","RADAR_HORIZON_VALUES","DEFAULT_RADAR_HORIZON","FIELD_VALUES",
  "CHANGE_KIND_VALUES","TAPE_REVIEW_VALUES","STUDY_TYPE_VALUES","PEER_MAX_COHORT","PROSPECTIVE_CHANGE_KIND_VALUES","MODE_VALUES"];
const constants = constantNames.map(name => {
  const match = source.match(new RegExp("  var "+name+" = [\\s\\S]*?;"));
  assert(match,name); return match[0];
}).join("\n");
const helpers = constants + "\n" + extracted.map(x=>x.code).join("\n");
assert(!/\b(fetch|fetchJson|localStorage|sessionStorage|document)\b/.test(helpers));
const clone = v => JSON.parse(JSON.stringify(v));
function contextFor(mode,rows) {
  const location = {href:"https://fixture.invalid/biocatalyst.html",search:""};
  const window = {location,history:{replaceState(_state,_title,value){
    const next = new URL(value,location.href); location.href=next.href; location.search=next.search;
  }}};
  const context = {window,URL,URLSearchParams,state:{}};
  vm.createContext(context);
  vm.runInContext(helpers,context,{timeout:1000});
  context.state = {mode,filters:context.defaultFilters(),cohort:[],cohortText:"",rows:clone(rows),
    selectedId:fixture.trial_id,selectedKey:""};
  context.state.filters.condition = fixture.clinical_condition_filter;
  return context;
}
function selectedKey(context) {
  const row = context.selectedRow();
  return row ? context.rowIdentity(row) : null;
}
const cases = [];
{
  const c=contextFor("milestones",fixture.milestones);
  c.state.selectedKey=c.rowIdentity(c.state.rows[1]);
  assert.equal(selectedKey(c),fixture.milestones[1].event_id);
  cases.push({id:"exact_row_key_control",selected:selectedKey(c)});
}
{
  const c=contextFor("milestones",fixture.milestones);
  c.state.selectedKey="nct:NCT00000001:absent_kind";
  assert.equal(selectedKey(c),fixture.milestones[0].event_id);
  cases.push({id:"missing_exact_key_falls_back_by_trial",requested:c.state.selectedKey,selected:selectedKey(c),
    required_future:"A saved exact-row reference that is absent must remain unavailable, with an explicit current-trial action."});
}
{
  const c=contextFor("milestones",[fixture.milestones[1],fixture.milestones[0]]);
  assert.equal(selectedKey(c),fixture.milestones[1].event_id);
  cases.push({id:"trial_only_fallback_depends_on_row_order",selected:selectedKey(c),
    required_future:"Preserve exact incumbent row identity, not only NCT or array position."});
}
{
  const c=contextFor("milestones",fixture.milestones);
  const changed=clone(fixture.milestones[0]); changed.milestone.date="2026-11-12";
  const before=c.milestoneIdentity(fixture.milestones[0]), after=c.milestoneIdentity(changed);
  assert.equal(before,after);
  cases.push({id:"event_identity_is_not_a_source_version",before_identity:before,after_identity:after,
    before_date:fixture.milestones[0].milestone.date,after_date:changed.milestone.date,
    required_future:"Keep stable event identity. Bind safe evidence/version metadata separately; do not add the mutable date to the canonical ID."});
}
for(const [mode,rows] of [["milestones",fixture.milestones],["changes",fixture.changes],["prospective",fixture.prospective]]) {
  const c=contextFor(mode,rows); c.state.selectedKey=c.rowIdentity(c.state.rows[1]);
  const requested=c.state.selectedKey; c.writeUrl();
  const serialized=c.window.location.href;
  c.state={mode:"milestones",filters:c.defaultFilters(),cohort:[],cohortText:"",rows:clone(rows),selectedId:"",selectedKey:""};
  c.readUrl();
  const selected=selectedKey(c), first=c.rowIdentity(c.state.rows[0]);
  assert.equal(c.state.selectedId,fixture.trial_id);
  assert.equal(c.state.selectedKey,"");
  assert.equal(selected,first);
  assert.notEqual(selected,requested);
  assert.equal(c.state.filters.condition,fixture.clinical_condition_filter);
  cases.push({id:mode+"_url_roundtrip_loses_exact_row",requested,selected,serialized_url:serialized,
    selected_key_after_read:c.state.selectedKey,clinical_condition_filter_preserved:c.state.filters.condition,
    required_future:"Extend the existing URL/selection owner for exact saved-row context; the current condition query remains a clinical filter."});
}
{
  const c=contextFor("milestones",fixture.milestones); c.state.selectedId="NCT00000002";
  assert.equal(selectedKey(c),null);
  cases.push({id:"missing_trial_control",selected:null});
}
const report={
  status:"CURRENT_EXACT_ROW_RESTORE_GAP_REPRODUCED_NOT_FIX_ACCEPTANCE",
  source:{repository:fixture.source_repo,commit:fixture.source_commit,path:fixture.source_path,sha256:digest},
  extraction:{constants:constantNames,functions:extracted.map(({name,first_line,last_line})=>({name,first_line,last_line})),
    sha256:crypto.createHash("sha256").update(helpers).digest("hex")},
  execution:{node:process.version,environment:"Node vm with controlled window location/history",browser_playback:false,
    dom_calls:0,network_calls:0,auth_calls:0,real_storage_calls:0,app_initialization_executed:false},
  cases,
  limits:["Source fixtures are controlled and fictional.","Existing trial-level fallback may be intentional for the workbench; it is insufficient for the proposed exact saved-row return contract.",
    "No live misrouting, dossier-generation mismatch or persistence success was observed.",
    "The current dossier endpoint remains a current projection; exact historical retrieval is separate unimplemented integration.",
    "This script does not implement local research conditions, issuer resolution, alerts or a new identity owner."]
};
fs.writeFileSync(outputPath,JSON.stringify(report,null,2)+"\n");
process.stdout.write(JSON.stringify({status:report.status,cases:cases.length,source_sha256:digest,output:outputPath})+"\n");
