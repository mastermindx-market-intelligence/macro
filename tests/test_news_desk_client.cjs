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
