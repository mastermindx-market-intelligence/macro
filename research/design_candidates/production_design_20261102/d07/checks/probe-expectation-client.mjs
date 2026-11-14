import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import crypto from "node:crypto";
if (process.argv.length !== 3) throw Error("Pass the pinned templates/expectation_surface.html.j2 source file");
const source = fs.readFileSync(process.argv[2], "utf8");
const bytes = Buffer.from(source);
const blob = crypto.createHash("sha1").update(Buffer.concat([Buffer.from("blob " + bytes.length + "\0"), bytes])).digest("hex");
assert.equal(blob, "51d99c9ac76557e2dce356a53231416f5fe84a44");
const openSource = source.match(/  function open\(T, opts\) \{[\s\S]*?\n  \}\n  var savedBody/)?.[0].replace(/\n  var savedBody$/, "");
assert.ok(openSource);
const results = [];
const queue = [];
const callbackRecords = [];
const histories = [];
const context = {
  q: {value:""}, VALID: /^[A-Z0-9.\-]{1,12}$/, lastOpts:null, savedBody:null, view:null, viewBody:null, cardT:null,
  syncClear(){}, closeLb(){}, hideNomatch(){}, restoreNodes(){}, showLoading(){}, showError(T){callbackRecords.push({error:T});},
  afterLoad(doc){callbackRecords.push({ticker:doc.ticker, financial_influence:doc.financial_influence});},
  fetch(url){return new Promise(resolve => queue.push({url, resolve}));},
  setTimeout(){return 1;}, clearTimeout(){}, AbortController, encodeURIComponent,
  history:{replaceState(state,title,url){histories.push(url);}},
  $(){return null;}, reduced(){return true;},
};
vm.createContext(context);
vm.runInContext(openSource, context);
context.open("AAA", {from:"pick"});
context.open("BBB", {from:"pick"});
queue[1].resolve({ok:true,json:async()=>({ticker:"BBB",financial_influence:false})});
await new Promise(resolve=>setImmediate(resolve));
queue[0].resolve({ok:true,json:async()=>({ticker:"AAA",financial_influence:false})});
await new Promise(resolve=>setImmediate(resolve));
assert.equal(context.q.value, "BBB");
assert.deepEqual(callbackRecords.map(x=>x.ticker), ["BBB","AAA"]);
assert.equal(histories.at(-1),"?t=BBB#es-explorer");
results.push({case:"late-response-reaches-presentation-callback",query:context.q.value,url:histories.at(-1),afterLoadTicker:callbackRecords.at(-1).ticker,required:"Retain request identity, disregard late completions and verify payload ticker before changing chart/card."});

context.open("CCC", {from:"pick"});
queue[2].resolve({ok:true,json:async()=>({ticker:"WRONG",financial_influence:true})});
await new Promise(resolve=>setImmediate(resolve));
assert.equal(callbackRecords.at(-1).ticker,"WRONG");
results.push({case:"mismatching-successful-payload",requested:"CCC",afterLoadPayload:callbackRecords.at(-1),required:"Validate ticker, reserved authority flags and expected response shape before presentation. Show scoped retrieval failure on mismatch."});

const ensureIndexSource = source.match(/  function ensureIndex\(\) \{[\s\S]*?\n  \}/)?.[0];
assert.ok(ensureIndexSource);
let fetches=0;
const indexContext={idxCache:null,idxLoading:false,fetch(){fetches++;return Promise.reject(new Error("503 source unavailable"));}};
vm.createContext(indexContext);
vm.runInContext(ensureIndexSource,indexContext);
indexContext.ensureIndex();
await new Promise(resolve=>setImmediate(resolve));
indexContext.ensureIndex();
await new Promise(resolve=>setImmediate(resolve));
assert.equal(fetches,1);
assert.equal(indexContext.idxCache.length,0);
results.push({case:"failed-index-frozen-as-empty",fetches,indexAfterFailure:indexContext.idxCache,required:"Distinguish index loading/failure from an authoritative empty index. Offer bounded read retry."});

assert.ok(source.includes("history.replaceState(null, '', '?t=' + encodeURIComponent(T) + '#es-explorer')"));
assert.ok(source.includes("new URLSearchParams(window.location.search).get('t')"));
assert.ok(source.includes("var VALID = /^[A-Z0-9.\\-]{1,12}$/;"));
results.push({case:"source-route-contract",existing:"?t=<SYMBOL>#es-explorer; row/pick replaceState; search/deep source actions differ",required:"Preserve unrelated query keys, document exact selection/history semantics, and reconcile 12-character UI versus 15-character producer symbols without a parallel parser."});
console.log(JSON.stringify({kind:"D07 advisory client diagnostics",status:"BASELINE_REPRODUCED",scope:"Original request/index functions in an isolated VM with controlled completion and a minimal DOM adapter. The substituted afterLoad recorder observes callback delivery. The original afterLoad rendering path is source-inspected, with browser verification pending. Passing probes reproduce baseline behavior.",source_blob:blob,executed:results.length,results},null,2));
