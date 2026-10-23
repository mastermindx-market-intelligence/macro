"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const desk = require("../templates/news_desk.js");
const now = Date.parse("2026-10-18T12:00:00Z");
const row = (overrides={}) => desk.normalize(Object.assign({
 id:"a", headline:"Federal Reserve holds its policy rate", url:"https://www.federalreserve.gov/report",
 published_at:"2026-10-18T11:59:00Z", tickers:["NVDA"], brief:"Officials discuss inflation."
},overrides));
const filter = (overrides={})=>Object.assign({},desk.defaults,overrides);
test("official provenance does not infer confirmation",()=>{
 const r=row({stage:"confirmed",source_count:7});
 assert.equal(r.kind,"official");assert.equal(r.category,"central_banks");
 assert.equal(r.important,false);
});
test("unknown and future publication times stay explicit",()=>{
 assert.equal(desk.age("",now,false),"Time unknown");
 assert.equal(desk.age("2026-10-19T12:00:00Z",now,false),"Future timestamp");
 assert.equal(desk.filterRows([row({published_at:"bad"})],filter(),{},now).length,0);
 assert.equal(desk.filterRows([row({published_at:"",provider_indexed_at:"2030-01-01T12:34:00Z"})],filter({time:"all"}),{},now).length,0);
});
test("publication aliases retain a valid evidence clock without rewriting source fields",()=>{
 const published="2026-10-18T11:00:00Z";
 const r=row({published_at:"invalid",ts:"also invalid",evidence:[{name:"Federal Reserve",published_at:published}]});
 assert.equal(r.publishedAt,published);assert.equal(r.published,Date.parse(published));
 assert.equal(r.clock,"published");assert.equal(r.clockAt,published);
 assert.equal(desk.filterRows([r],filter(),{},now).length,1);
 assert.equal(r.raw.published_at,"invalid");assert.equal(r.raw.ts,"also invalid");
 assert.equal(r.raw.evidence[0].published_at,published);
});
test("publication precedence, unknown clocks, and future exclusion remain explicit",()=>{
 const recent="2026-10-18T11:00:00Z",later="2026-10-18T11:30:00Z";
 const primary={published_at:"2026-10-18T11:45:00Z"};
 assert.equal(row({published_at:recent,ts:later,evidence:[primary]}).publishedAt,recent);
 assert.equal(row({published_at:"bad",ts:later,evidence:[primary]}).publishedAt,later);
 const unknown=row({published_at:"bad",ts:"bad",evidence:[{published_at:"bad"}]});
 assert.equal(unknown.published,null);
 assert.equal(desk.filterRows([unknown],filter(),{},now).length,0);
 assert.equal(desk.filterRows([unknown],filter({time:"all"}),{},now).length,1);
 const future=row({published_at:"2026-10-18T12:05:01Z",ts:recent,evidence:[primary]});
 assert.equal(future.publishedAt,"2026-10-18T12:05:01Z");
 assert.equal(desk.filterRows([future],filter({time:"all"}),{},now).length,0);
 assert.equal(desk.filterRows([row({published_at:"2026-10-18T12:05:00Z"})],filter(),{},now).length,1);
});
test("exact phrase, exclusion and typed source/ticker filters compose",()=>{
 const r=row();
 assert.equal(desk.filterRows([r],filter({query:'"Federal Reserve" -cuts ticker:NVDA source:federalreserve'}),{},now).length,1);
 assert.equal(desk.filterRows([r],filter({query:'ticker:NV'}),{},now).length,0);
 assert.equal(desk.filterRows([r],filter({query:'-inflation'}),{},now).length,0);
});
test("regions are mentioned places and do not override source geography",()=>{
 const r=row({headline:"Japan central bank watches inflation",url:"https://bbc.com/report"});
 assert.ok(r.regions.includes("asia"));assert.ok(!r.regions.includes("europe"));
});
test("placeholder and link-only social posts do not become stories",()=>{
 assert.equal(desk.normalize({id:"x",headline:"(Truth Social post)"}),null);
 assert.equal(desk.normalize({id:"x",headline:"RT: https://example.com/x"}),null);
});
test("social claims default off but can be explicitly included",()=>{
 const r=row({url:"https://truthsocial.com/post",headline:"A statement about economic policy"});
 assert.equal(desk.filterRows([r],filter(),{},now).length,0);
 assert.equal(desk.filterRows([r],filter({social:true}),{},now).length,1);
});
test("read, saved and following are independent reader choices",()=>{
 const r=row(),p={read:["a"],saved:["a"],following:["ticker:NVDA"]};
 assert.equal(desk.filterRows([r],filter({unread:true}),p,now).length,0);
 assert.equal(desk.filterRows([r],filter({saved:true}),p,now).length,1);
 assert.equal(desk.filterRows([r],filter({view:"following"}),p,now).length,1);
 assert.equal(desk.filterRows([r],filter({view:"following"}),{},now).length,0);
});
test("display duplicates collapse without multiplying evidence",()=>{
 const r=row(),s=row({id:"b",url:r.url+"?utm_source=wire"});
 assert.equal(desk.combine([r],[s]).length,1);
 assert.equal(desk.combine([r],[s])[0].evidence.length,1);
});
test("corrections and removals count, publication-clock changes do not",()=>{
 const old=row(),clock=row({updated_at:"2026-10-18T12:02:00Z"});
 assert.equal(desk.difference([old],[clock]),0);
 assert.equal(desk.difference([old],[row({headline:"Corrected: Federal Reserve cuts rate"})]),1);
 assert.equal(desk.difference([old],[]),1);
});
test("active seven-day view retains more than the old six-row cap",()=>{
 const rows=Array.from({length:120},(_,i)=>row({id:String(i),headline:"Economic report "+i,url:"https://example.com/"+i}));
 assert.equal(desk.filterRows(rows,filter(),{},now).length,120);
});
test("unsafe source URLs and credential URLs never become links",()=>{
 ["javascript:alert(1)","data:text/html,bad","https://user:secret@example.com","/relative"].forEach(u=>assert.equal(desk.safeURL(u),""));
 assert.equal(desk.safeURL("https://example.com/a"),"https://example.com/a");
});
test("malformed snapshot never replaces the current model",()=>{
 assert.equal(Boolean(desk.validSnapshot({schema:"other",stories:[]})),false);
 assert.equal(Boolean(desk.validSnapshot({schema:"intelligence.desk/v1",stories:[null]})),false);
 assert.equal(Boolean(desk.validSnapshot({schema:"intelligence.desk/v1",stories:[{id:"s"}]})),true);
});
test("Chinese brief search matches displayed translation",()=>{
 assert.equal(desk.filterRows([row({brief_zh:"关注制造业通胀"})],filter({query:"制造业"}),{},now).length,1);
});
test("OR alternatives compose with global exclusions and literal quoted OR",()=>{
 const r=row();
 assert.equal(desk.filterRows([r],filter({query:'ticker:MSFT OR ticker:NVDA -cuts'}),{},now).length,1);
 assert.equal(desk.filterRows([r],filter({query:'ticker:MSFT OR ticker:NVDA -inflation'}),{},now).length,0);
 assert.equal(desk.filterRows([r],filter({query:'"OR"'}),{},now).length,0);
});
test("indexing and publisher amendments never invent publication time",()=>{
 const indexed=row({published_at:"",seendate:"2026-10-18T11:00:00Z"});
 assert.equal(indexed.published,null);assert.equal(indexed.clock,"indexed");
 const amended=row({published_at:"2026-09-01T00:00:00Z",source_updated_at:"2026-10-18T11:30:00Z"});
 assert.equal(amended.clock,"updated");assert.equal(desk.filterRows([amended],filter(),{},now).length,1);
});

const research=require("../templates/news_research.js");
const researchState=extra=>research.cleanState(Object.assign({enabled:true,watching:["v:macro","i:question"],investigations:[{id:"question",name:"Policy question",storyIds:["a"],relation:"question"}]},extra));
const reference=(id,version="one")=>({id,mark:research.marker(version)});
const memberships=[{key:"v:macro",ids:["a"]},{key:"i:question",ids:["a"]}];
test("research storage is a closed reference-only schema, including legacy views",()=>{
 const dirty={enabled:true,watching:["v:macro","i:question"],token:"secret",body:"licensed body",investigations:[{id:"question",name:"Policy\nquestion",storyIds:["a","a",{body:"private"}],relation:"confirmed",brief:"protected brief"}],records:[{id:"a",mark:research.marker("report"),available:true,targets:["i:question","bad"],title:"private headline"}],updates:[{n:1,id:"a",kind:"amendment",targets:["i:question"],at:now,read:false,body:"private copy"},{n:2,id:"a",kind:"arrival",targets:["i:question"],at:1e100}]};
 const cleaned=research.cleanState(dirty),serialized=JSON.stringify(cleaned);
 assert.equal(cleaned.investigations[0].name,"Policy question");assert.equal(cleaned.investigations[0].relation,"question");assert.deepEqual(cleaned.investigations[0].storyIds,["a"]);assert.equal(cleaned.updates.length,1);
 assert.doesNotMatch(serialized,/secret|licensed|private|protected|confirmed/);
 const views=research.cleanViews([{id:"view-1",name:"First",filters:{query:"rates",body:"copied"}},{id:"view-1",name:"Second",filters:{category:"bogus"}},{id:"legacy-view-1-0",name:"Third",filters:{}}],desk.defaults);
 assert.equal(new Set(views.map(v=>v.id)).size,3);assert.equal(views[1].filters.category,"all");assert.doesNotMatch(JSON.stringify(views),/copied/);
});
test("monitoring starts silently and deduplicates overlapping watch targets",()=>{
 let result=research.advance(researchState(),[reference("a")],memberships,{baseline:true,now});
 assert.equal(result.added,0);assert.equal(result.state.updates.length,0);
 result=research.advance(result.state,[reference("a","corrected")],memberships,{now:now+1});
 assert.equal(result.added,1);assert.equal(result.state.updates[0].kind,"amendment");assert.deepEqual(result.state.updates[0].targets,["v:macro","i:question"]);
 result=research.advance(result.state,[reference("a","corrected")],memberships,{now:now+2});assert.equal(result.added,0);assert.equal(result.state.updates.length,1);
});
test("a report leaving a search filter is not a removal, but leaving the full feed is",()=>{
 let state=research.advance(researchState(),[reference("a")],memberships,{baseline:true,now}).state;
 let result=research.advance(state,[reference("a","no longer matches")],[{key:"v:macro",ids:[]},{key:"i:question",ids:["a"]}],{now:now+1});
 assert.equal(result.added,1);assert.equal(result.state.updates[0].kind,"amendment");
 result=research.advance(result.state,[],memberships,{now:now+2});assert.equal(result.added,1);assert.equal(result.state.updates[0].kind,"removal");
 result=research.advance(result.state,[],memberships,{now:now+3});assert.equal(result.added,0);
 result=research.advance(result.state,[reference("a","no longer matches")],memberships,{now:now+4});assert.equal(result.added,1);assert.equal(result.state.updates[0].kind,"return");
});
test("new matches arrive once and only from the supplied live full projection",()=>{
 let state=research.advance(researchState(),[reference("a"),reference("existing")],memberships,{baseline:true,now}).state;
 let result=research.advance(state,[reference("a"),reference("existing"),reference("new")],[{key:"v:macro",ids:["a","existing","new"]},{key:"i:question",ids:["a"]}],{now:now+1});
 assert.equal(result.added,1);assert.equal(result.state.updates[0].id,"new");assert.equal(result.state.updates[0].kind,"arrival");
 result=research.advance(result.state,[reference("a"),reference("existing"),reference("new")],[{key:"v:macro",ids:["a","existing","new"]}],{now:now+2});assert.equal(result.added,0);
});
test("an exact session change cannot be hidden by a compact marker collision",()=>{
 const state=research.advance(researchState(),[reference("a")],memberships,{baseline:true,now}).state;
 const result=research.advance(state,[reference("a")],memberships,{changedIds:new Set(["a"]),now:now+1});assert.equal(result.added,1);assert.equal(result.state.updates[0].kind,"amendment");
});
test("disabled monitoring and renewed baselines do not replay older changes",()=>{
 let state=research.advance(researchState(),[reference("a")],memberships,{baseline:true,now}).state;
 state=research.advance(state,[reference("a","two")],memberships,{now:now+1}).state;
 let result=research.advance(Object.assign({},state,{enabled:false}),[],memberships,{now:now+2});assert.equal(result.added,0);assert.deepEqual(result.state.records,[]);
 result=research.advance(Object.assign({},result.state,{enabled:true}),[reference("a","three")],memberships,{baseline:true,now:now+3});assert.equal(result.added,0);assert.equal(result.state.updates.length,1);
 result=research.advance(Object.assign({},result.state,{updates:[]}),[reference("a","four")],memberships,{baseline:true,now:now+4});assert.equal(result.added,0);assert.equal(result.state.updates.length,0);
});
test("removing a watch prunes its references and inbox targets without touching other watches",()=>{
 let state=research.advance(researchState(),[reference("a")],memberships,{baseline:true,now}).state;
 state=research.advance(state,[reference("a","two")],memberships,{now:now+1}).state;
 state=research.prune(state,["i:question"]);assert.deepEqual(state.watching,["i:question"]);assert.deepEqual(state.updates[0].targets,["i:question"]);
 state=research.prune(state,[]);assert.equal(state.updates.length,0);assert.equal(state.records[0].targets.length,0);
});
test("missing investigation references survive a silent baseline and resolve without invented bodies",()=>{
 const result=research.advance(researchState(),[],memberships,{baseline:true,now});assert.equal(result.added,0);assert.equal(result.state.records[0].available,false);assert.equal(result.state.records[0].mark,"");
 const returned=research.advance(result.state,[reference("a")],memberships,{now:now+1});assert.equal(returned.state.updates[0].kind,"return");assert.equal(returned.state.investigations[0].storyIds[0],"a");
});
test("the compact inbox remains bounded during a full projection change",()=>{
 const rows=Array.from({length:1000},(_,i)=>reference("s"+i)),match=[{key:"v:macro",ids:rows.map(r=>r.id)}];
 let state=research.advance(researchState(),[],[],{baseline:true,now}).state;
 const result=research.advance(state,rows,match,{now:now+1});assert.equal(result.added,1000);assert.equal(result.state.records.length,1000);assert.equal(result.state.updates.length,100);assert.equal(new Set(result.state.updates.map(u=>u.n)).size,100);
});
const historyRevision="a".repeat(64);
const historyDescriptorRaw={state:"available",schema:"intelligence.retained_history/v1",revision:historyRevision,bounds:{retention_hours:72,max_stories:1500,retention_basis:"owner_updated_at"},retained_count:3,displayable_count:2,excluded_count:1};
const historyDescriptor=research.historyDescriptor(historyDescriptorRaw);
const historyQuery=research.historyQuery({q:"Oil OR gas",source:"Publisher",category:"Energy",language:"EN",from_at:"2026-10-18T01:00:00+01:00",to_at:"2026-10-19T00:00:00Z",limit:50});
const historyPage=extra=>Object.assign({schema:"intelligence.history_page/v1",revision:historyRevision,as_of:"2026-10-18T12:00:00Z",collection:"retained_current_packets",order:"recorded_acceptance_desc_then_id",bounds:historyDescriptorRaw.bounds,retained_count:3,displayable_count:2,excluded_count:1,matched_count:2,returned_count:1,stories:[{id:"historic"}],next_cursor:"opaque_page_2",query:Object.assign({},historyQuery,{from_at:"2026-10-18T00:00:00Z",to_at:"2026-10-19T00:00:00Z"})},extra);
test("retained history descriptors require an exact revision and explicit owner bounds",()=>{
 assert.equal(historyDescriptor.state,"available");assert.deepEqual(research.historyDescriptor({state:"unavailable",reason:"not_exported"}),{state:"unavailable"});
 for(const override of [{revision:"old"},{bounds:{retention_hours:73,max_stories:1500,retention_basis:"owner_updated_at"}},{bounds:{retention_hours:72,max_stories:1501,retention_basis:"owner_updated_at"}},{displayable_count:3},{retained_count:null}])assert.equal(research.historyDescriptor(Object.assign({},historyDescriptorRaw,override)).state,"unavailable");
 const smaller=research.historyDescriptor(Object.assign({},historyDescriptorRaw,{bounds:{retention_hours:24,max_stories:200,retention_basis:"owner_updated_at"}}));assert.equal(smaller.bounds.retention_hours,24);
});
test("history query normalization preserves literal grammar and exact publisher text",()=>{
 assert.equal(historyQuery.q,"Oil OR gas");assert.equal(historyQuery.source,"Publisher");assert.equal(historyQuery.category,"energy");assert.equal(historyQuery.language,"en");assert.equal(historyQuery.from_at,"2026-10-18T00:00:00.000Z");
 assert.equal(research.historyQuery({q:"  a  b  "}).q,"a  b");
 for(const raw of [{q:"x".repeat(257)},{limit:101},{from_at:"2026-10-18T00:00"},{from_at:"2026-10-19T00:00:00Z",to_at:"2026-10-18T00:00:00Z"},{from_at:"invalid"}])assert.equal(research.historyQuery(raw),null);
});
test("history pages are bound to the accepted descriptor and immutable request query",()=>{
 assert.equal(research.validHistoryPage(historyPage(),historyDescriptor,historyQuery),true);
 for(const page of [historyPage({revision:"b".repeat(64)}),historyPage({query:Object.assign({},historyQuery,{q:"gas"})}),historyPage({query:Object.assign({},historyQuery,{limit:100})}),historyPage({query:undefined}),historyPage({bounds:{retention_hours:24,max_stories:1500,retention_basis:"owner_updated_at"}}),historyPage({order:"publication_desc"})])assert.equal(research.validHistoryPage(page,historyDescriptor,historyQuery),false);
});
test("history counts, unique IDs, and opaque cursors are checked before display",()=>{
 for(const extra of [{returned_count:2},{matched_count:3},{stories:[{id:"historic"},{id:"historic"}],returned_count:2},{next_cursor:""},{next_cursor:"../token"},{next_cursor:"x".repeat(1025)},{as_of:"unknown"},{as_of:0},{as_of:"2026-10-18T12:00:00"},{stories:[],returned_count:0},{stories:[{id:""}]}])assert.equal(research.validHistoryPage(historyPage(extra),historyDescriptor,historyQuery),false);
 assert.equal(research.validHistoryPage(historyPage({next_cursor:null}),historyDescriptor,historyQuery),true);
});
