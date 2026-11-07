'use strict';
// Real retained state-machine regression tests; source is evaluated unchanged
// except for VM-local visibility into private functions and its exact locale callback.
// Usage: node this-file.js /path/to/templates/market_memory_retained.js [owner-fixtures.json]
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const sourcePath=process.argv[2];
assert.ok(sourcePath,'Pass actual retained JS source path as first argument');
const original=fs.readFileSync(sourcePath,'utf8');
const examples=JSON.parse(fs.readFileSync(process.argv[3]||path.join(__dirname,'owner-fixtures.json'),'utf8')).examples;
const tick=()=>new Promise(resolve=>setImmediate(resolve));
let unhandledRejections=0;process.on('unhandledRejection',()=>{unhandledRejections++;});
function element(){const attrs={};return {innerHTML:'',textContent:'',hidden:false,_attrs:attrs,classList:{add(){},remove(){},toggle(){}},setAttribute(name,value){attrs[name]=String(value);},removeAttribute(name){delete attrs[name];},querySelector(){return null;},insertAdjacentHTML(){},focus(){this.focused=true;},scrollIntoView(){}};}
function setup(){
 const requests=[],published=[];let responsePayload=null,responseHeaders={},localeLanguage='zh',signinWrites=0;
 let holdResponse=false,holdBody=false,heldResponse=null,heldBody=null;
 const timers=new Map();let timerSeq=0;
 const location={href:'https://example.test/market_memory.html',search:''};
 const window={location:{origin:'https://example.test'},addEventListener(){},MarketMemoryIntent:{target(patch){assert.deepEqual(Object.keys(patch),['language']);return {ok:true,target:'/market_memory.html?mm_lang='+patch.language};},resumeStatus(){return {ok:true};},oauthPreservation(){return {ok:true};},signinHref(){signinWrites++;return {ok:true,href:'/?signin=1&ret=%2Fmarket_memory.html'};},replace(patch){published.push(JSON.parse(JSON.stringify(patch)));let q=new URLSearchParams();Object.keys(patch).forEach(k=>{if(patch[k]!==null&&patch[k]!==undefined)q.set(({sourceField:'mm_source_field',sourceContext:'mm_source_context',catalogOffset:'mm_catalog_offset',outcomeLens:'mm_outcome'})[k]||'mm_'+k,patch[k]);});location.search='?'+q;location.href='https://example.test/market_memory.html'+location.search;return {ok:true};}}};
 const locale=/document\.addEventListener\('langchange', function \(\) \{([\s\S]*?)\n    \}\);/.exec(original);
 assert.ok(locale,'Actual locale callback must be available for this regression');
 const anchor='var ui = {};';assert.equal(original.split(anchor).length,2,'Review anchor must be unique');
 const instrumented=original.replace(anchor,anchor+` globalThis.review={state:state,ui:ui,applyIntent:applyIntent,loadCatalog:loadCatalog,runCurrentIntent:runCurrentIntent,deepLinkMismatch:deepLinkMismatch,onPopState:onPopState,runCompare:runCompare,runSaved:runSaved,loadMoreCatalog:loadMoreCatalog,normalizeCatalog:normalizeCatalog,selectEntry:selectEntry,renderRequestFailure:renderRequestFailure,renderTypedUnavailable:renderTypedUnavailable,authRedact:authRedact,renderCatalogPrompt:renderCatalogPrompt,apiFetch:apiFetch,renderCutoffControl:renderCutoffControl,openSessionObservation:openSessionObservation,sessionObservationsMarkup:sessionObservationsMarkup,stateKindFor:stateKindFor,setMode:setMode,onActionClick:onActionClick,locale:function(){${locale[1]}}};`);
 const responseLike=payload=>({ok:!payload.__httpStatus,status:payload.__httpStatus||200,headers:{get(name){return responseHeaders[name.toLowerCase()]||null;}},json(){return Promise.resolve(payload);}});
 const context={window,URL,URLSearchParams,AbortController,console:{info(){}},location,history:{state:null,pushState(state,title,url){published.push({push:url});}},document:{readyState:'loading',addEventListener(){},documentElement:{getAttribute(){return localeLanguage;}}},
  setTimeout(fn,ms){const id=++timerSeq;timers.set(id,{fn,ms});return id;},
  clearTimeout(id){timers.delete(id);},
  fetch(url,options){requests.push({url,options});
   if(holdResponse){holdResponse=false;return new Promise(resolve=>{heldResponse=resolve;});}
   if(holdBody){holdBody=false;return Promise.resolve({ok:true,headers:{get(name){return responseHeaders[name.toLowerCase()]||null;}},json(){return new Promise(resolve=>{heldBody=resolve;});}});}
   if(responsePayload){const payload=Array.isArray(responsePayload)?responsePayload.shift():responsePayload;if(!Array.isArray(responsePayload)||!responsePayload.length)responsePayload=null;return Promise.resolve(responseLike(payload));}
   return new Promise(()=>{});}};
 context.globalThis=context;vm.runInNewContext(instrumented,context,{filename:sourcePath});
 const r=context.review,s=r.state;
 ['status','resultBody','sourceBody','sourceHeading','captureSelect','cutoffSelect','loadMoreButton','scopeLine','cutoffNote','originalClock','primaryButton','modeNote','sourcePanel'].forEach(k=>r.ui[k]=element());r.ui.tabs={saved:element(),historical:element(),current:element()};
 const catalog=r.normalizeCatalog(examples.catalog_historical.body),a=catalog.entries[0],b=catalog.entries[1];
 const intent={mode:'historical',query:b.queryId,context:b.contextId,subject:catalog.subject.subjectId,gen:catalog.generation.generationId,genSha:catalog.generation.generationSha256,method:catalog.methods.historical_hypothetical.methodSpecId,cutoff:examples.retained_historical.request.query.query_cutoff,catalogOffset:'0'};
 s.catalog=catalog;s.mode='historical';
 return {r,s,catalog,a,b,intent,requests,published,location,window,signinWrites(){return signinWrites;},setLang(value){localeLanguage=value;},respond(payload,headers={}){responsePayload=payload;responseHeaders=headers;},
  hangNextResponse(){holdResponse=true;},releaseResponse(payload){const resolve=heldResponse;heldResponse=null;resolve(responseLike(payload));},
  hangNextBody(){holdBody=true;},releaseBody(payload){const resolve=heldBody;heldBody=null;resolve(payload);},
  pendingDeadlines(){return timers.size;},
  fireDeadline(){let oldest=null;for(const entry of timers){if(oldest===null||entry[0]<oldest[0])oldest=entry;}if(!oldest)return 0;timers.delete(oldest[0]);oldest[1].fn();return 1;},
  fireAllDeadlines(){const list=[...timers.values()];timers.clear();for(const t of list)t.fn();return list.length;},
  deadlineMs(){return [...timers.values()].map(t=>t.ms);}};
}

const wire=JSON.parse(fs.readFileSync(process.argv[4],'utf8'));
const clone=x=>JSON.parse(JSON.stringify(x));
const drain=async()=>{for(let i=0;i<12;i++)await tick();};
function pair(){const x=setup(),s=x.s,r=x.r,cat=r.normalizeCatalog(wire.a_page),a=cat.entries[0];
 s.catalog=cat;s.mode='saved';s.selected=a;s.sourceField='growth_score';s.sourceContext=a.contextId;
 s.intent={mode:'saved',query:a.queryId,context:a.contextId,subject:cat.subject.subjectId,gen:cat.generation.generationId,genSha:cat.generation.generationSha256,cutoff:wire.cutoff,catalogOffset:String(cat.selection.offset),sourceField:'growth_score',sourceContext:a.contextId};
 s.committed={kind:'saved',intent:clone(s.intent),data:{}};return x;}
async function test(name,fn){await fn();console.log('PASS '+name);}
(async()=>{
 await test('native producer catalogs bind cross-page sibling and preserve exact IDs',async()=>{let x=pair();x.setLang('en');let row=x.s.selected.sameSession[0];assert.equal(row.context_id,wire.b_page.entries[0].context_id);assert.notEqual(wire.a_page.selection.offset,wire.b_page.selection.offset);assert.match(x.r.sessionObservationsMarkup(),/not certified corrections/);x.setLang('zh');assert.match(x.r.sessionObservationsMarkup(),/并非经认证/);});
 for(const key of ['subject_id','instrument_id','source_session','family_sha256','generation_id','generation_sha256','context_id'])await test('refuse foreign sibling '+key,async()=>{const page=clone(wire.a_page);page.entries[0].same_session_observations.observations[0][key]=key==='context_id'?page.entries[0].context_id:'wrong';assert.throws(()=>pair().r.normalizeCatalog(page));});
 await test('cutoff blocks explicit target without any fetch/history mutation',async()=>{let x=pair();x.s.intent.cutoff=x.s.selected.earliestSupportedCutoff;assert.equal(x.r.openSessionObservation(wire.b_page.entries[0].context_id),false);assert.equal(x.requests.length,0);assert.equal(x.published.length,0);assert.equal(x.s.selected.contextId,wire.a_page.entries[0].context_id);});
 await test('explicit cross-page catalog lookup then genuine native saved envelope then Back A',async()=>{let x=pair(),r=x.r,s=x.s;let original=clone(s.intent);x.respond([wire.b_page,wire.b_saved]);r.openSessionObservation(wire.b_page.entries[0].context_id);await drain();assert.equal(x.requests.length,2);const catalogURL=new URL(x.requests[0].url,'https://example.test');assert.equal(catalogURL.searchParams.get('query_id'),wire.b_page.entries[0].query_id);assert.equal(catalogURL.searchParams.get('generation_id'),original.gen);assert.equal(s.intent.cutoff,original.cutoff);assert.equal(s.sourceField,'growth_score');assert.equal(s.committed.kind,'saved');assert.equal(s.committed.data.contextId,wire.b_page.entries[0].context_id);assert.equal(r.ui.captureSelect.focused,true,'B announces its exact persistent selector');r.ui.captureSelect.focused=false;assert.equal(x.published.filter(p=>p.push).length,1);x.location.search=new URL(x.published.find(p=>p.push).push).search;x.respond([wire.a_page,wire.a_saved]);r.onPopState();await drain();assert.equal(s.committed.data.contextId,original.context);assert.equal(s.intent.cutoff,original.cutoff);assert.equal(s.sourceContext,original.sourceContext);assert.equal(s.sourceField,original.sourceField);assert.equal(r.ui.captureSelect.focused,true,'Back announces restored A');});
 await test('target same locator wrong packet or family refuses before saved disclosure',async()=>{for(const key of ['packet_sha256','capture_id','source_session','instrument_id']){let x=pair(),bad=clone(wire.b_page);bad.entries[0][key]=key==='packet_sha256'?'f'.repeat(64):'wrong';x.respond(bad);x.r.openSessionObservation(wire.b_page.entries[0].context_id);await drain();assert.equal(x.requests.length,1);assert.equal(x.s.committed,null);assert.equal(x.published.filter(p=>p.push).length,0);}});
 await test('logout while target catalog pending cannot commit/history/source',async()=>{let x=pair();x.hangNextResponse();x.r.openSessionObservation(wire.b_page.entries[0].context_id);await tick();x.r.authRedact();x.releaseResponse(wire.b_page);await drain();assert.equal(x.s.committed,null);assert.equal(x.s.sourceCase,null);assert.equal(x.published.filter(p=>p.push).length,0);assert.equal(x.requests.length,1);});
 await test('changed selected intent suppresses stale target response',async()=>{let x=pair();x.hangNextResponse();x.r.openSessionObservation(wire.b_page.entries[0].context_id);await tick();x.s.epoch++;x.releaseResponse(wire.b_page);await drain();assert.equal(x.s.committed,null);assert.equal(x.requests.length,1);assert.equal(x.published.filter(p=>p.push).length,0);});
 await test('current HTTP403 target refusal renders no saved evidence or history',async()=>{let x=pair();x.respond({__httpStatus:403,detail:{state:'SOURCE_USE_NOT_ADMITTED'}});x.r.openSessionObservation(wire.b_page.entries[0].context_id);await drain();assert.equal(x.s.committed,null);assert.equal(x.s.sourceCase,null);assert.equal(x.requests.length,1);assert.equal(x.published.filter(p=>p.push).length,0);assert.match(x.r.ui.resultBody.innerHTML,/rights_blocked/);});
 await test('target page changing generation refuses without saved read',async()=>{let x=pair(),bad=clone(wire.b_page);bad.generation.generation_sha256='f'.repeat(64);x.respond(bad);x.r.openSessionObservation(wire.b_page.entries[0].context_id);await drain();assert.equal(x.s.committed,null);assert.equal(x.requests.length,1);assert.equal(x.published.filter(p=>p.push).length,0);});
 await test('sibling supported cutoff is offered explicitly without changing current intent',async()=>{let x=pair();x.s.intent.cutoff=x.s.selected.earliestSupportedCutoff;x.r.renderCutoffControl();assert.ok(x.r.ui.cutoffSelect.innerHTML.includes(wire.b_page.entries[0].earliest_supported_cutoff));assert.equal(x.r.ui.cutoffSelect.value,x.s.selected.earliestSupportedCutoff);assert.equal(x.s.intent.cutoff,x.s.selected.earliestSupportedCutoff);assert.equal(x.requests.length,0);});
 for(const key of ['profile','store_id'])await test('target page changed native '+key+' refuses',async()=>{let x=pair(),bad=clone(wire.b_page);bad.generation[key]='wrong';x.respond(bad);x.r.openSessionObservation(wire.b_page.entries[0].context_id);await drain();assert.equal(x.s.committed,null);assert.equal(x.requests.length,1);assert.equal(x.published.filter(p=>p.push).length,0);});
 await test('fifth sibling locator refuses the exact finite wire bound',async()=>{let x=pair(),bad=clone(wire.a_page),r=bad.entries[0].same_session_observations;r.observations=Array(5).fill(r.observations[0]);r.total=5;r.omitted=0;assert.throws(()=>x.r.normalizeCatalog(bad),e=>e.contractCode==='session_accounting');});
 console.log('RESULT session navigation cases passed');
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
