/* Run with NODE_PATH=<jsdom 26.1.0 node_modules> NEWS_DESK_TEST_HTML=<rendered
 * news.html> node --test tests/test_news_desk_mounted.cjs. No browser/network. */
"use strict";
const {JSDOM}=require("jsdom"),test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs");
const desk=require("../templates/news_desk.js");
const markup=fs.readFileSync(process.env.NEWS_DESK_TEST_HTML || require("node:path").join(__dirname,"../site/news.html"),"utf8");
const initialTime=Date.parse("2026-10-18T04:00:00Z");
const story=(id="a",extra={})=>Object.assign({id,headline:"Source report "+id,source_name:"Private publisher",url:"https://example.com/"+id,published_at:"2026-10-18T03:55:00Z",evidence:[],brief:"Source details "+id},extra);
const snapshot=stories=>({schema:"intelligence.desk/v1",stories,health:{last_source_published_at:"2026-10-18T03:55:00Z"}});
const settle=async()=>{for(let i=0;i<4;i++)await new Promise(r=>setImmediate(r));};
function harness(t,{mobile=false,hash=""}={}){
 const dom=new JSDOM(markup,{url:"https://example.com/news.html"+hash,pretendToBeVisual:true});
 const win=dom.window,doc=win.document;doc.getElementById("ndSeed").textContent='{"stories":[]}';
 let now=initialTime,sequence=0,requests=0,status=200,payload=snapshot([story()]);
 const realNow=Date.now;Date.now=()=>now;
 const timeouts=new Map(),intervals=[];win.setTimeout=(fn,delay)=>{const id=++sequence;timeouts.set(id,{fn,at:now+delay});return id;};win.clearTimeout=id=>timeouts.delete(id);win.setInterval=fn=>{intervals.push(fn);return intervals.length;};
 const media={matches:mobile,listeners:[],addEventListener:(name,fn)=>media.listeners.push(fn)};win.matchMedia=()=>media;
 win.fetch=async()=>{requests++;return{ok:status===200,status,text:async()=>JSON.stringify(payload)};};
 const streams=[];win.EventSource=class{constructor(){this.listeners={};this.closed=false;streams.push(this);}addEventListener(n,fn){this.listeners[n]=fn;}close(){this.closed=true;}emit(n,p){if(this.listeners[n])this.listeners[n]({data:JSON.stringify(p)});}};
 doc.querySelectorAll("dialog").forEach(d=>{d.showModal=()=>d.setAttribute("open","");d.close=()=>d.removeAttribute("open");});
 const app=desk.mount(doc,win);
 const click=id=>{const n=doc.getElementById(id);n.focus();n.click();};
 t.after(()=>{win.dispatchEvent(new win.Event("pagehide"));Date.now=realNow;dom.window.close();});
 return{app,win,doc,streams,click,setPayload:p=>payload=p,setStatus:n=>status=n,requests:()=>requests,
  resize:value=>{media.matches=value;media.listeners.forEach(fn=>fn({matches:value}));},
  advance:async ms=>{now+=ms;intervals.forEach(fn=>fn());for(let pass=0;pass<4;pass++){for(const[id,task]of Array.from(timeouts)){if(task.at<=now){timeouts.delete(id);task.fn();}}await settle();}},
  key:key=>doc.dispatchEvent(new win.KeyboardEvent("keydown",{key,bubbles:true,cancelable:true}))};
}
function selected(h){h.doc.querySelector(".nd-row .nd-title").focus();h.doc.querySelector(".nd-row .nd-title").click();}

test("new arrivals buffer, but existing report amendments update immediately",async t=>{
 const h=harness(t);await settle();selected(h);
 h.app.accept(snapshot([story("b"),story("a",{headline:"Amended source report"})]));
 assert.ok(h.doc.getElementById("ndFeed").textContent.includes("Amended source report"));
 assert.ok(!h.doc.getElementById("ndFeed").textContent.includes("Source report b"));
 assert.equal(h.doc.getElementById("ndStoryTitle").textContent,"Amended source report");
 assert.ok(h.app.getState().pending>0);h.click("ndUpdates");
 assert.ok(h.doc.getElementById("ndFeed").textContent.includes("Source report b"));
});
test("removed live content stays unavailable across language, save and redraw",async t=>{
 const h=harness(t);await settle();selected(h);h.app.accept(snapshot([]));
 h.doc.documentElement.dataset.lang="zh";h.doc.dispatchEvent(new h.win.Event("langchange"));h.key("s");
 assert.ok(!h.doc.getElementById("ndFeed").textContent.includes("Source report a"));
 assert.ok(!h.doc.getElementById("ndDetailBody").textContent.includes("Source details a"));
});
test("auth loss clears open coverage and mobile modal protected state",async t=>{
 const h=harness(t,{mobile:true});await settle();selected(h);h.click("ndDetailClose");h.click("ndCoverageOpen");
 assert.ok(h.doc.getElementById("ndCoverageBody").textContent.includes("Private publisher"));
 h.setStatus(401);h.click("ndRetry");await settle();
 assert.ok(!h.doc.getElementById("ndCoverageBody").textContent.includes("Private publisher"));
 assert.ok(!h.doc.getElementById("ndCoverageBody").textContent.includes("18 Oct 2026"));
 assert.equal(h.doc.getElementById("ndDetail").getAttribute("aria-modal"),null);
});
test("heartbeat expiry schedules an actual generation-fenced recovery",async t=>{
 const h=harness(t);await settle();h.streams[0].emit("snapshot",snapshot([story()]));
 const requests=h.requests();await h.advance(46000);
 assert.ok(h.streams[0].closed);assert.ok(h.requests()>requests);
 h.streams[0].emit("snapshot",snapshot([story("obsolete")]));
 assert.ok(!h.doc.getElementById("ndFeed").textContent.includes("obsolete"));
});
test("repeated stream errors switch to bounded polling and language changes retain its deadline",async t=>{
 const h=harness(t);await settle();
 for(let i=0;i<3;i++){h.streams.at(-1).onerror();await h.advance(10000);}
 assert.equal(h.app.getState().mode,"polling");assert.equal(h.streams.length,3);
 await h.advance(4000);const requests=h.requests();
 for(const [locale,label] of [["zh","自动刷新 · 10秒"],["en","Auto refresh · 10s"]]){
  h.doc.documentElement.dataset.lang=locale;h.doc.dispatchEvent(new h.win.Event("langchange"));
  assert.deepEqual(["ndConnection","ndConnectionMobile"].map(id=>h.doc.getElementById(id).textContent),[label,label]);
  assert.equal(h.app.getState().mode,"polling");assert.equal(h.requests(),requests);assert.equal(h.streams.length,3);
 }
 await h.advance(5999);assert.equal(h.requests(),requests);
 await h.advance(1);assert.equal(h.requests(),requests+1);assert.equal(h.streams.length,3);
});
test("language changes retain the live channel and current failure wording",async t=>{
 const h=harness(t);await settle();const stream=h.streams[0];stream.emit("snapshot",snapshot([story()]));
 const requests=h.requests();h.click("ndCoverageOpen");
 h.doc.documentElement.dataset.lang="zh";h.doc.dispatchEvent(new h.win.Event("langchange"));
 assert.deepEqual(["ndConnection","ndConnectionMobile"].map(id=>h.doc.getElementById(id).textContent),["新闻流已连接","新闻流已连接"]);
 assert.equal(h.doc.querySelector("#ndCoverageBody .nd-section p").textContent,"新闻流已连接");
 assert.equal(h.app.getState().mode,"connected");assert.equal(stream.closed,false);assert.equal(h.streams.length,1);assert.equal(h.requests(),requests);
 stream.emit("unavailable");assert.equal(h.doc.getElementById("ndConnection").textContent,"新闻流不可用");
 h.doc.documentElement.dataset.lang="en";h.doc.dispatchEvent(new h.win.Event("langchange"));
 assert.deepEqual(["ndConnection","ndConnectionMobile"].map(id=>h.doc.getElementById(id).textContent),["Feed unavailable","Feed unavailable"]);
 assert.equal(h.doc.querySelector("#ndCoverageBody .nd-section p").textContent,"Feed unavailable");
 assert.equal(h.app.getState().mode,"degraded");assert.equal(stream.closed,true);assert.equal(h.streams.length,1);assert.equal(h.requests(),requests);
});
test("mobile save, detail tabs and updates preserve usable focus",async t=>{
 const h=harness(t,{mobile:true});await settle();selected(h);
 const save=h.doc.querySelector('[data-action="detail-action-1"]');save.focus();save.click();
 assert.equal(h.doc.activeElement.dataset.action,"detail-action-1");
 const tab=h.doc.querySelector('[data-action="detail-tab-evidence"]');tab.focus();tab.click();
 assert.equal(h.doc.activeElement.dataset.action,"detail-tab-evidence");
 h.app.accept(snapshot([story("a",{headline:"Updated source report"})]));
 assert.equal(h.doc.activeElement.dataset.action,"detail-tab-evidence");
 h.key("/");assert.notEqual(h.doc.activeElement.id,"ndSearch");
 h.click("ndDetailClose");assert.ok(h.doc.activeElement.classList.contains("nd-title"));
});
test("closed shared dialogs allow search shortcuts while a visible dialog owns them",async t=>{
 const h=harness(t);await settle();
 const panel=h.doc.createElement("div");panel.setAttribute("role","dialog");h.doc.body.appendChild(panel);
 h.click("ndDensity");const trigger=h.doc.getElementById("ndDensity");
 for(const state of [
  {css:"display:block;visibility:hidden;opacity:1",aria:null},
  {css:"display:block;visibility:visible;opacity:1",aria:"true"}
 ]){
  panel.style.cssText=state.css;
  if(state.aria===null)panel.removeAttribute("aria-hidden");else panel.setAttribute("aria-hidden",state.aria);
  trigger.focus();h.key("/");assert.equal(h.doc.activeElement.id,"ndSearch",state.css+" aria-hidden="+state.aria);
 }
 panel.removeAttribute("aria-hidden");
 for(const opacity of ["0","1"]){
  panel.style.cssText="display:flex;visibility:visible;opacity:"+opacity;
  trigger.focus();h.key("/");assert.equal(h.doc.activeElement,trigger,"visible dialog opacity="+opacity);
 }
});
test("CSS-hidden shared dialogs leave the mobile story focus trap active",async t=>{
 const h=harness(t,{mobile:true});await settle();selected(h);
 const panel=h.doc.createElement("div");panel.setAttribute("role","dialog");panel.style.cssText="display:block;visibility:hidden;opacity:1";h.doc.body.appendChild(panel);
 h.doc.getElementById("ndDensity").focus();
 const event=new h.win.KeyboardEvent("keydown",{key:"Tab",bubbles:true,cancelable:true});h.doc.dispatchEvent(event);
 assert.equal(event.defaultPrevented,true);assert.equal(h.doc.activeElement.id,"ndDetailClose");
});
test("breakpoint changes synchronize modal semantics",async t=>{
 const h=harness(t);await settle();selected(h);h.resize(true);
 assert.equal(h.doc.getElementById("ndDetail").getAttribute("aria-modal"),"true");h.resize(false);
 assert.equal(h.doc.getElementById("ndDetail").getAttribute("aria-modal"),null);
});
test("an amended read story reappears in Unread",async t=>{
 const h=harness(t);await settle();selected(h);h.click("ndFilterOpen");h.doc.getElementById("ndUnread").checked=true;
 h.doc.getElementById("ndFiltersForm").dispatchEvent(new h.win.Event("submit",{bubbles:true,cancelable:true}));
 assert.ok(!h.doc.getElementById("ndFeed").textContent.includes("Source report a"));
 h.app.accept(snapshot([story("a",{headline:"Amended source report"})]));
 assert.ok(h.doc.getElementById("ndFeed").textContent.includes("Amended source report"));
});
test("live snapshots preserve the focused headline and lost rows recover to the feed",async t=>{
 const h=harness(t);await settle();selected(h);
 h.app.accept(snapshot([story("b"),story("a",{headline:"Amended report"})]));
 assert.equal(h.doc.activeElement.closest(".nd-row").dataset.id,"a");
 h.app.accept(snapshot([]));assert.equal(h.doc.activeElement.id,"ndFeedPanel");
});
test("detail tabs support arrows, Home and End after DOM replacement",async t=>{
 const h=harness(t);await settle();selected(h);h.click("ndStoryTab-brief");
 const key=k=>h.doc.activeElement.dispatchEvent(new h.win.KeyboardEvent("keydown",{key:k,bubbles:true,cancelable:true}));
 key("ArrowRight");assert.equal(h.doc.activeElement.id,"ndStoryTab-evidence");
 key("End");assert.equal(h.doc.activeElement.id,"ndStoryTab-timeline");
 key("Home");assert.equal(h.doc.activeElement.id,"ndStoryTab-brief");
});
test("live-only deep links select their exact story after the first snapshot",async t=>{
 const h=harness(t,{hash:"#story=a"});await settle();
 assert.equal(h.app.getState().selected,"a");
 const missing=harness(t,{hash:"#story=missing"});await settle();
 assert.equal(missing.app.getState().selected,null);
 assert.match(missing.doc.getElementById("ndDetailBody").textContent,/outside the loaded window/);
});
test("timeline uses retained editorial and source amendment events with honest clocks",async t=>{
 const h=harness(t);await settle();h.app.accept(snapshot([story("a",{published_at:"2026-09-18T03:00:00Z",source_updated_at:"2026-10-18T03:57:00Z",timeline:[{ts:"2026-10-18T03:00:00Z",label_en:"First independent report",label_zh:"首条独立报道"},{at:"2026-10-18T03:57:00Z",kind:"amendment"}]})]));
 selected(h);h.click("ndStoryTab-timeline");
 assert.match(h.doc.getElementById("ndStorySection").textContent,/Source amendment received/);
 assert.match(h.doc.getElementById("ndStorySection").textContent,/First independent report/);
 assert.match(h.doc.querySelector(".nd-row time").title,/Source updated/);
 h.doc.documentElement.dataset.lang="zh";h.doc.dispatchEvent(new h.win.Event("langchange"));
 assert.match(h.doc.getElementById("ndStorySection").textContent,/首条独立报道/);
});
test("shared authentication events immediately clear the desk and fence previous streams",async t=>{
 const h=harness(t);await settle();const prior=h.streams[0];
 h.win.dispatchEvent(new h.win.CustomEvent("mdx-auth",{detail:{user:null,event:"SIGNED_OUT"}}));
 prior.emit("snapshot",snapshot([story("obsolete")]));await h.advance(1000);
 assert.equal(h.app.getState().mode,"restricted");assert.doesNotMatch(h.doc.getElementById("ndFeed").textContent,/Source report|obsolete/);
});
test("a native dialog above a mobile story owns Tab and Escape",async t=>{
 const h=harness(t,{mobile:true});await settle();selected(h);const d=h.doc.getElementById("ndCompany");d.showModal();h.doc.getElementById("ndCompanyTicker").focus();
 h.key("Tab");assert.equal(h.doc.activeElement.id,"ndCompanyTicker");h.key("Escape");
 assert.equal(h.doc.getElementById("ndDetail").dataset.open,"true");
});
