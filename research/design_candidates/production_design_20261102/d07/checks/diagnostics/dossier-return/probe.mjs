import assert from "node:assert/strict";
import crypto from "node:crypto";
import vm from "node:vm";
import fs from "node:fs";
import { stripTypeScriptTypes } from "node:module";
const dossier = fs.readFileSync(process.argv[2], "utf8");
const planner = fs.readFileSync(process.argv[3], "utf8");
function blob(source) {
  const bytes = Buffer.from(source);
  return crypto.createHash("sha1").update(Buffer.concat([Buffer.from("blob " + bytes.length + "\0"), bytes])).digest("hex");
}
assert.equal(blob(dossier), "f211bb2aa8fa5cbfe78c522159402231c1267840");
assert.equal(blob(planner), "131b7c0a6881d65d8a7023363969748542a495aa");
function originalFunction(source, name, exported = false) {
  const start = (exported ? "export function " : "  function ") + name + "(";
  const index = source.indexOf(start);
  assert.ok(index >= 0, name);
  const ending = exported ? "\n}" : "\n  }";
  const end = source.indexOf(ending, index);
  assert.ok(end > index, name);
  return source.slice(index, end + ending.length);
}
const requested = "?from=earnings-wire&tx=2026Q3";
const selected = [];
const context = {
  ticker:"AAPL", window:{location:{search:requested},dispatchEvent(){}},
  URLSearchParams, URL, payload:null, events:[],
  loading:{},empty:{},content:{},root:{attrs:{},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(){}},
  receipt:{},footNote:{}, setState(){}, showEmpty(){throw Error("unexpected empty");},
  renderHistory(){},renderEvent(event){selected.push(String(event.fiscal_year)+"Q"+String(event.fiscal_quarter));},
  generatedLabel(){return "";},clear(){},pair(){},
};
vm.createContext(context);
vm.runInContext(["eventPeriodKey","eventIdentifiers","showPayload"].map(name=>originalFunction(dossier,name)).join("\n"), context);
context.showPayload({available:true,status:"ready",latest_event:{fiscal_year:2026,fiscal_quarter:4,call_date:"2026-10-29",sources:[]}});
assert.deepEqual(selected,["2026Q4"]);
assert.equal(context.window.location.search,requested);
const v1={requested:"2026Q3",renderEventCallback:selected[0],query:context.window.location.search};

// Positive control uses the same public latest_event shape with a matching tx.
const matchingRequested = "?from=earnings-wire&tx=2026Q4";
context.window.location.search = matchingRequested;
selected.length = 0;
context.showPayload({
  available: true,
  status: "ready",
  latest_event: {
    fiscal_year: 2026,
    fiscal_quarter: 4,
    call_date: "2026-10-29",
    sources: [],
  },
});
assert.deepEqual(selected, ["2026Q4"]);
assert.equal(context.window.location.search, matchingRequested);
const v1Matching = {
  requested: "2026Q4",
  renderEventCallback: selected[0],
  callbackCount: selected.length,
  query: context.window.location.search,
};

const c2 = {
  ticker:"AAPL",window:{location:{search:requested},dispatchEvent(){}},URL,
  root:{attrs:{},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(){}},
  period:{},summary:null,tags:null,history:{hidden:false},
  document:{createElement(){return {appendChild(){}};}},
  v2Host:{appendChild(){}},metrics:null,terminalUpgrade:{},transcript:{},
  loading:{},empty:{},content:{},receipt:{},footNote:{},announcer:null,
  clear(){},pair(){},setState(){},setPair(){},
  generatedLabel(){return "";},
  displayDate(){return "";},
};
vm.createContext(c2);
vm.runInContext(["v2PeriodPair","analysisUrl","renderV2"].map(name=>originalFunction(dossier,name)).join("\n"),c2);
c2.renderV2({schema:"event_workspace_public_glance.v1",available:true,ticker:"AAPL",event_id:"evt_cik0000320193_2026q4_results",event_alias:"AAPL/2026Q4",generation_id:"fixture-g2",fiscal_period:{year:2026,quarter:4},event_date:"2026-10-29",reported:[],guidance:[],watch:[],coverage_states:[]});
assert.equal(c2.root.attrs["data-ci-event-id"],"evt_cik0000320193_2026q4_results");
assert.equal(new URL(c2.transcript.href).searchParams.get("tx"),"2026Q4");
assert.equal(new URL(c2.terminalUpgrade.href).searchParams.get("tx"),null);
assert.equal(c2.window.location.search,requested);
const v2={requested:"2026Q3",rootEventAttribute:c2.root.attrs["data-ci-event-id"],transcriptHref:c2.transcript.href,fullEventHref:c2.terminalUpgrade.href,historyHidden:c2.history.hidden};

const seenDefinition=planner.match(/export const sessionSeenDays[^\n]+/)[0];
const ts=[originalFunction(planner,"eventIdentity",true),seenDefinition,originalFunction(planner,"noteReschedule",true)].join("\n");
const compiled=stripTypeScriptTypes(ts);
const p=await import("data:text/javascript;base64,"+Buffer.from(compiled).toString("base64"));
const event={id:p.eventIdentity("AAPL",null),symbol:"AAPL",kind:"earnings",period:null,confirmation:"unstated",sourceAsOf:"2026-11-03",previousDay:null};
const before=p.noteReschedule({...event,when:{precision:"date",day:"2026-11-05"}});
const after=p.noteReschedule({...event,when:{precision:"date",day:"2027-02-05"}});
assert.equal(before.id,"earnings:AAPL:next");
assert.equal(after.id,before.id);
assert.equal(after.previousDay,"2026-11-05");
console.log(JSON.stringify({status:"SOURCE_BOUNDARIES_REPRODUCED",sourceBlobs:{dossier:blob(dossier),planner:blob(planner)},witnesses:[{case:"requested-call-missing-from-latest-dossier",v1,v1Matching,v2,scope:"Original showPayload and renderV2 functions. v1 renderEvent is a recorder. v2 uses a minimal DOM adapter. Browser verification remains pending."},{case:"unknown-period-date-change",id:after.id,previousDay:after.previousDay,shownDay:after.when.day,scope:"Original eventIdentity and noteReschedule function bodies after TypeScript type erasure. The output records a date change without establishing which issuer event changed."}]},null,2));
