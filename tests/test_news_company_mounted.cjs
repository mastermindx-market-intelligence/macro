/* Use the same rendered-page / jsdom harness described in NEWS_DESK_REBUILD.md. */
"use strict";
const {JSDOM}=require("jsdom"),test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs");
const company=require("../templates/news_company.js"),markup=fs.readFileSync(process.env.NEWS_DESK_TEST_HTML || require("node:path").join(__dirname,"../site/news.html"),"utf8");
const settle=async()=>{for(let i=0;i<5;i++)await new Promise(r=>setImmediate(r));};
const row=(id="a",sequence=8,extra={})=>Object.assign({story_id:id,sequence,title:"Licensed example "+id,url:"https://example.com/"+id,teaser:"Source excerpt "+id,source:"licensed-provider",source_count:1,item_count:1,published_at:"2026-10-18T03:00:00Z",updated_at:null,received_at:"2026-10-18T03:01:00Z"},extra);
const snapshot=(rows=[row()],extra={})=>Object.assign({schema:"ticker_news.snapshot.v1",ticker:"NVDA",security_id:"security-nvda",rows,has_more:false,next_cursor:null,state:"live",source_health:{state:"live"}},extra);
function harness(t){
 const dom=new JSDOM(markup,{url:"https://example.com/news.html",pretendToBeVisual:true}),win=dom.window,doc=win.document;
 const dialog=doc.getElementById("ndCompany");dialog.showModal=()=>dialog.setAttribute("open","");dialog.close=()=>{dialog.removeAttribute("open");dialog.dispatchEvent(new win.Event("close"));};
 let now=Date.now(),count=0,payload=snapshot(),httpStatus=200,streamStatus=200,hold=null,memberPayload={schema:"ticker_news.story.v1",story_id:"a",members:[row()]};
 const realNow=Date.now;Date.now=()=>now;
 const timers=new Map();win.setTimeout=(fn,ms)=>{const id=++count;timers.set(id,{fn,at:now+ms});return id;};win.clearTimeout=id=>timers.delete(id);
 const calls=[],channels=[];win.MDXAuth={client:async()=>({auth:{getSession:async()=>({data:{session:{access_token:"fixture-session-token"}}})}})};
 win.fetch=async(url,options)=>{
   calls.push({url,options});if(hold&&!url.includes("/stream")){const gate=hold;hold=null;return await gate;}
   if(url.includes("/stream")){
     let controller;const body=new ReadableStream({start(c){controller=c;}});channels.push(controller);
     options.signal.addEventListener("abort",()=>{try{controller.error(new Error("aborted"));}catch(_){}});
     return {ok:streamStatus===200,status:streamStatus,headers:{get:()=>"text/event-stream"},body};
   }
   return {ok:httpStatus===200,status:httpStatus,text:async()=>JSON.stringify(url.includes("/stories/")?memberPayload:payload)};
 };
 const app=company.mount(doc,win);
 t.after(()=>{win.dispatchEvent(new win.Event("pagehide"));Date.now=realNow;dom.window.close();});
 return{app,win,doc,dialog,calls,channels,setPayload:p=>payload=p,setStatus:n=>httpStatus=n,setStreamStatus:n=>streamStatus=n,setMembers:p=>memberPayload=p,hold:p=>hold=p,
  emit:(event,p)=>channels.at(-1).enqueue(new TextEncoder().encode("event: "+event+"\ndata: "+JSON.stringify(p)+"\n\n")),
  heartbeat:()=>channels.at(-1).enqueue(new TextEncoder().encode(": heartbeat\n\n")),
  advance:async ms=>{now+=ms;for(let pass=0;pass<5;pass++){for(const[id,task]of Array.from(timers))if(task.at<=now){timers.delete(id);task.fn();}await settle();}},
  click:id=>{const n=doc.getElementById(id);n.focus();n.click();}};
}
test("company requests use bearer auth and never persist licensed rows",async t=>{
 const h=harness(t);h.app.open("NVDA");await settle();h.heartbeat();await settle();
 assert.equal(h.app.getState().mode,"connected");assert.equal(h.calls[0].options.headers.Authorization,"Bearer fixture-session-token");
 assert.equal(h.calls[0].options.cache,"no-store");assert.equal(h.win.localStorage.length,0);
 assert.match(h.calls[1].url,/after_sequence=8$/);assert.match(h.doc.getElementById("ndCompanyRows").textContent,/Licensed example a/);
});
test("stream changes trigger authoritative snapshots, buffer new groups, and apply corrections",async t=>{
 const h=harness(t);h.app.open("NVDA");await settle();
 h.setPayload(snapshot([row("b",10),row("a",9,{title:"Corrected licensed report"})]));h.emit("upsert",{sequence:10,title:"Must not become a rendered delta"});await settle();await h.advance(1000);
 assert.deepEqual(h.app.getState().ids,["a"]);assert.equal(h.app.getState().pending,1);
 assert.match(h.doc.getElementById("ndCompanyRows").textContent,/Corrected licensed report/);
 assert.doesNotMatch(h.doc.getElementById("ndCompanyRows").textContent,/Must not become|Licensed example b/);
 h.click("ndCompanyUpdates");assert.deepEqual(h.app.getState().ids,["b","a"]);
 h.setPayload(snapshot([row("b",11)]));h.emit("remove",{sequence:11});await settle();await h.advance(1000);
 assert.deepEqual(h.app.getState().ids,["b"]);
});
test("rights revocation clears reporting and activity immediately",async t=>{
 const h=harness(t);h.app.open("NVDA");await settle();h.emit("restricted",{});await settle();
 assert.equal(h.app.getState().mode,"restricted");assert.deepEqual(h.app.getState().ids,[]);
 assert.equal(h.doc.getElementById("ndCompanyRows").textContent,"");assert.equal(h.doc.getElementById("ndCompanyFlow").textContent,"");
});
test("sign-out fences an already pending response and clears both content and source names",async t=>{
 const h=harness(t);let resolve;h.hold(new Promise(r=>resolve=r));h.app.open("NVDA");await settle();
 h.win.dispatchEvent(new h.win.CustomEvent("mdx-auth",{detail:{user:null,event:"SIGNED_OUT"}}));
 resolve({ok:true,status:200,text:async()=>JSON.stringify(snapshot())});await settle();
 assert.deepEqual(h.app.getState().ids,[]);assert.doesNotMatch(h.doc.getElementById("ndCompany").textContent,/licensed-provider|Licensed example/);
});
test("earlier pages pause the change stream and recheck authorization",async t=>{
 const h=harness(t);h.setPayload(snapshot([row()],{has_more:true,next_cursor:8}));h.app.open("NVDA");await settle();
 h.setPayload(snapshot([row("old",4)]));h.click("ndCompanyMore");await settle();
 assert.equal(h.app.getState().mode,"paused");assert.equal(h.app.getState().cursor,8);assert.equal(h.channels.length,1);
 assert.ok(h.calls.some(c=>c.url.includes("cursor=8")));h.setStatus(403);await h.advance(45000);
 assert.equal(h.app.getState().mode,"restricted");assert.deepEqual(h.app.getState().ids,[]);
});
test("unchanged snapshots keep the focused headline and source group DOM",async t=>{
 const h=harness(t);h.setPayload(snapshot([row("a",8,{item_count:2})]));h.app.open("NVDA");await settle();
 const link=h.doc.querySelector(".nd-company-row h3 a"),group=h.doc.querySelector(".nd-company-group");link.focus();
 h.app.accept(snapshot([row("a",8,{item_count:2})]),false);
 assert.equal(h.doc.activeElement,link);assert.equal(h.doc.querySelector(".nd-company-group"),group);
 h.app.accept(snapshot([row("a",9,{title:"Correction"})]),false);
 assert.equal(h.doc.activeElement.textContent,"Correction");
});
test("a lost connection clears protected content and offers bounded recovery",async t=>{
 const h=harness(t);h.app.open("NVDA");await settle();await h.advance(15000);
 assert.equal(h.app.getState().mode,"degraded");assert.deepEqual(h.app.getState().ids,[]);
 await h.advance(10000);assert.ok(h.calls.filter(c=>!c.url.includes("/stream")).length>=2);
});
test("closing a company workspace aborts delivery and removes in-memory reporting",async t=>{
 const h=harness(t);h.app.open("NVDA");await settle();h.dialog.close();await settle();
 assert.equal(h.app.getState().ticker,"");assert.deepEqual(h.app.getState().ids,[]);
 const n=h.calls.length;await h.advance(60000);assert.equal(h.calls.length,n);
});
test("corrections preserve two-story order until the reader restores latest order",async t=>{
 const h=harness(t);h.setPayload(snapshot([row("a",10),row("b",8)]));h.app.open("NVDA");await settle();
 h.app.accept(snapshot([row("b",11,{title:"B correction"}),row("a",10)]),false);
 assert.deepEqual(h.app.getState().ids,["a","b"]);assert.equal(h.doc.getElementById("ndCompanyUpdates").hidden,false);
 h.click("ndCompanyUpdates");assert.deepEqual(h.app.getState().ids,["b","a"]);
});
test("an expanded source group stays open through correction and superseded request failure",async t=>{
 const h=harness(t);h.setPayload(snapshot([row("a",8,{item_count:2})]));h.app.open("NVDA");await settle();
 let reject;h.hold(new Promise((_,r)=>reject=r));const old=h.doc.querySelector(".nd-company-group");old.open=true;old.dispatchEvent(new h.win.Event("toggle"));await settle();
 h.setMembers({schema:"ticker_news.story.v1",story_id:"a",members:[row("a",9,{title:"New source revision"})]});
 h.app.accept(snapshot([row("a",9,{item_count:2,title:"Current revision"})]),false);await settle();
 assert.equal(h.doc.querySelector(".nd-company-group").open,true);assert.match(h.doc.getElementById("ndCompanyRows").textContent,/New source revision/);
 reject(new Error("superseded request timed out"));await settle();assert.deepEqual(h.app.getState().ids,["a"]);
 assert.match(h.doc.getElementById("ndCompanyRows").textContent,/Current revision/);
});
test("a stream rate limit retains its 60-second retry boundary",async t=>{
 const h=harness(t);h.setStreamStatus(429);h.app.open("NVDA");await settle();const n=h.calls.length;
 assert.match(h.doc.getElementById("ndCompanyStatus").textContent,/Request limit/);await h.advance(59999);assert.equal(h.calls.length,n);
 await h.advance(1);assert.ok(h.calls.length>n);
});
test("automatic 429 retry preserves its deadline after background suspension",async t=>{
 const h=harness(t);h.setStreamStatus(429);h.app.open("NVDA");await settle();
 const first=h.calls.length;assert.match(h.doc.getElementById("ndCompanyStatus").textContent,/Request limit/);
 await h.advance(5000);
 Object.defineProperty(h.doc,"hidden",{configurable:true,value:true});
 h.doc.dispatchEvent(new h.win.Event("visibilitychange"));await settle();
 await h.advance(5000);
 Object.defineProperty(h.doc,"hidden",{configurable:true,value:false});
 h.doc.dispatchEvent(new h.win.Event("visibilitychange"));await settle();
 assert.equal(h.calls.length,first);
 await h.advance(49999);assert.equal(h.calls.length,first);
 await h.advance(1);assert.ok(h.calls.length>first);
});
test("automatic 429 retry preserves its deadline after BFCache restoration",async t=>{
 const h=harness(t);h.setStreamStatus(429);h.app.open("NVDA");await settle();
 const first=h.calls.length;await h.advance(5000);
 h.win.dispatchEvent(new h.win.Event("pagehide"));await settle();
 await h.advance(5000);
 const show=new h.win.Event("pageshow");Object.defineProperty(show,"persisted",{value:true});
 h.win.dispatchEvent(show);await settle();
 assert.equal(h.calls.length,first);
 await h.advance(49999);assert.equal(h.calls.length,first);
 await h.advance(1);assert.ok(h.calls.length>first);
});
test("a missing stream endpoint does not enter a terminal-error retry loop",async t=>{
 const h=harness(t);h.setStreamStatus(404);h.app.open("NVDA");await settle();const n=h.calls.length;
 await h.advance(120000);assert.equal(h.calls.length,n);
});
