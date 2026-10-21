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
function harness(t,{mobile=false,hash="",preferences}={}){
 const dom=new JSDOM(markup,{url:"https://example.com/news.html"+hash,pretendToBeVisual:true});
 const win=dom.window,doc=win.document;doc.getElementById("ndSeed").textContent='{"stories":[]}';
 if(preferences)win.localStorage.setItem("mm.newsDesk.preferences.v1",JSON.stringify(preferences));
 let now=initialTime,sequence=0,requests=0,status=200,payload=snapshot([story()]);
 const realNow=Date.now;Date.now=()=>now;
 const timeouts=new Map(),intervals=[];win.setTimeout=(fn,delay)=>{const id=++sequence;timeouts.set(id,{fn,at:now+delay});return id;};win.clearTimeout=id=>timeouts.delete(id);win.setInterval=fn=>{intervals.push(fn);return intervals.length;};
 const media={matches:mobile,listeners:[],addEventListener:(name,fn)=>media.listeners.push(fn)};win.matchMedia=()=>media;
 const historyRequests=[];let historyResponder=async()=>({ok:false,status:503,text:async()=>"{}"});
 win.fetch=async(url,options)=>{if(String(url).startsWith("/api/news-desk/history?")){historyRequests.push({url:String(url),options});return historyResponder(String(url),options);}requests++;return{ok:status===200,status,text:async()=>JSON.stringify(payload)};};
 const streams=[];win.EventSource=class{constructor(){this.listeners={};this.closed=false;streams.push(this);}addEventListener(n,fn){this.listeners[n]=fn;}close(){this.closed=true;}emit(n,p){if(this.listeners[n])this.listeners[n]({data:JSON.stringify(p)});}};
 doc.querySelectorAll("dialog").forEach(d=>{d.showModal=()=>d.setAttribute("open","");d.close=()=>d.removeAttribute("open");});
 win.HTMLElement.prototype.scrollIntoView=function(){}; // jsdom has no layout viewport.
 const app=desk.mount(doc,win);
 const click=id=>{const n=doc.getElementById(id);n.focus();n.click();};
 t.after(()=>{win.dispatchEvent(new win.Event("pagehide"));Date.now=realNow;dom.window.close();});
 return{app,win,doc,streams,click,setPayload:p=>payload=p,setStatus:n=>status=n,requests:()=>requests,setHistory:fn=>historyResponder=fn,historyRequests:()=>historyRequests,
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
test("initial stream handshake deadline preserves reporting and fences obsolete frames after polling",async t=>{
 const h=harness(t);await settle();selected(h);
 const requests=h.requests(),stalled=h.streams[0];
 const expectStory=(headline,brief)=>{
  assert.deepEqual(Array.from(h.doc.querySelectorAll("#ndFeed .nd-row"),n=>n.dataset.id),["a"]);
  assert.equal(h.doc.querySelector("#ndFeed .nd-title").textContent,headline);
  assert.equal(h.app.getState().selected,"a");
  assert.equal(h.doc.getElementById("ndStoryTitle").textContent,headline);
  assert.equal(h.doc.querySelector("#ndStorySection .nd-section p").textContent,brief);
 };
 expectStory("Source report a","Source details a");
 await h.advance(11999);assert.equal(h.app.getState().mode,"connecting");
 assert.equal(stalled.closed,false);assert.equal(h.requests(),requests);
 await h.advance(1);assert.equal(stalled.closed,true);assert.equal(h.app.getState().mode,"polling");
 assert.deepEqual(["ndConnection","ndConnectionMobile"].map(id=>h.doc.getElementById(id).textContent),["Auto refresh · 10s","Auto refresh · 10s"]);
 expectStory("Source report a","Source details a");assert.equal(h.requests(),requests);
 h.setPayload(snapshot([story("a",{headline:"Newer poll report",brief:"Newer poll details"})]));
 await h.advance(9999);assert.equal(h.requests(),requests);
 await h.advance(1);assert.equal(h.requests(),requests+1);assert.equal(h.streams.length,1);
 expectStory("Newer poll report","Newer poll details");
 stalled.emit("snapshot",snapshot([story("a",{headline:"Obsolete report",brief:"Obsolete details"})]));await settle();
 expectStory("Newer poll report","Newer poll details");
 assert.equal(h.app.getState().mode,"polling");assert.equal(h.requests(),requests+1);assert.equal(h.streams.length,1);
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
test("mobile story Tab confinement follows actual sequential focus order",async t=>{
 const h=harness(t,{mobile:true});await settle();selected(h);
 const panel=h.doc.getElementById("ndDetail");
 assert.equal(panel.getAttribute("aria-modal"),"true");
 const inactive=h.doc.getElementById("ndStoryTab-timeline");assert.equal(inactive.tabIndex,-1);
 const roving=h.doc.createElement("button");roving.tabIndex=-1;panel.appendChild(roving);
 const hidden=h.doc.createElement("div");hidden.hidden=true;
 const hiddenButton=h.doc.createElement("button");hidden.appendChild(hiddenButton);panel.appendChild(hidden);
 const disabled=h.doc.createElement("button");disabled.disabled=true;panel.appendChild(disabled);
 const nodes=Array.from(panel.querySelectorAll("button,a[href]")).filter(n=>n.tabIndex>=0&&!n.matches(":disabled")&&!n.hidden&&!n.closest("[hidden],[inert],[aria-hidden='true']"));
 const first=nodes[0],last=nodes.at(-1);assert.ok(first&&last);assert.notEqual(last,disabled);
 last.focus();const tab=h.doc.dispatchEvent(new h.win.KeyboardEvent("keydown",{key:"Tab",bubbles:true,cancelable:true}));
 assert.equal(tab,false);assert.equal(h.doc.activeElement,first);
 first.focus();const reverse=h.doc.dispatchEvent(new h.win.KeyboardEvent("keydown",{key:"Tab",shiftKey:true,bubbles:true,cancelable:true}));
 assert.equal(reverse,false);assert.equal(h.doc.activeElement,last);
 h.doc.getElementById("ndSearch").focus();
 const outside=h.doc.dispatchEvent(new h.win.KeyboardEvent("keydown",{key:"Tab",shiftKey:true,bubbles:true,cancelable:true}));
 assert.equal(outside,false);assert.equal(h.doc.activeElement,last);
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

const readPreferences=h=>JSON.parse(h.win.localStorage.getItem("mm.newsDesk.preferences.v1")||"{}");
const submit=(h,id)=>h.doc.getElementById(id).dispatchEvent(new h.win.Event("submit",{bubbles:true,cancelable:true}));
const close=(h,id)=>{const button=h.doc.querySelector("#"+id+" [data-close-dialog]");button.focus();button.click();};
function chooseReport(h,id){const row=Array.from(h.doc.querySelectorAll("#ndFeed .nd-row")).find(row=>row.dataset.id===id);assert.ok(row,"report is in the feed: "+id);const pick=row.querySelector(".nd-report-pick");assert.ok(pick,"report has a stable selectable ID");pick.focus();pick.click();}
function createInvestigation(h,name){h.doc.getElementById("ndInvestigationName").value=name;submit(h,"ndInvestigationForm");return readPreferences(h).research.investigations.at(-1);}
const monitoredPreferences={views:[{id:"reports",name:"Report search",filters:{query:"report",time:"all"}}],research:{enabled:true,quiet:true,watching:["v:reports","i:question"],investigations:[{id:"question",name:"An open question",storyIds:["a"],relation:"question"}]}};

test("comparison refreshes corrections in place, keeps distinct clocks and never revives a removed report",async t=>{
 const h=harness(t);await settle();
 const original=story("a",{brief:"Original protected brief",source_updated_at:"2026-10-18T03:56:00Z",provider_indexed_at:"2026-10-18T03:57:00Z",first_seen:"2026-10-18T03:58:00Z",accepted_revision_at:"2026-10-18T03:59:00Z",revision_history:[{accepted_at:"2026-10-18T03:50:00Z",headline:"Earlier retained headline"}]});
 h.app.accept(snapshot([original,story("b")]));h.click("ndUpdates");chooseReport(h,"a");chooseReport(h,"b");h.click("ndCompareOpen");
 const comparison=h.doc.getElementById("ndCompareReports");assert.equal(comparison.querySelectorAll(".nd-comparison-report").length,2);assert.match(comparison.textContent,/Publisher updated/);assert.match(comparison.textContent,/Provider indexed/);assert.match(comparison.textContent,/First seen by desk/);assert.match(comparison.textContent,/Earlier retained headline/);assert.match(h.doc.getElementById("ndCompare").textContent,/does not establish independent confirmation/);
 const focused=comparison.querySelector("a");focused.focus();const focusKey=focused.dataset.researchFocus;comparison.closest(".nd-dialog-body").scrollTop=137;
 h.app.accept(snapshot([story("a",{headline:"Corrected report a",brief:"Corrected protected brief"}),story("b")]));
 assert.match(comparison.textContent,/Corrected protected brief/);assert.doesNotMatch(comparison.textContent,/Original protected brief/);assert.equal(h.doc.activeElement.dataset.researchFocus,focusKey);assert.equal(comparison.closest(".nd-dialog-body").scrollTop,137);
 h.app.accept(snapshot([story("b")]));assert.match(comparison.textContent,/Report outside the current feed/);assert.doesNotMatch(comparison.textContent,/Corrected protected brief/);
 h.doc.documentElement.dataset.lang="zh";h.doc.dispatchEvent(new h.win.Event("langchange"));assert.match(comparison.textContent,/报道不在当前新闻流中/);
 assert.doesNotMatch(JSON.stringify(readPreferences(h)),/protected brief|Earlier retained headline|Private publisher/);
});
test("the comparison selection is limited to three reader-chosen reports",async t=>{
 const h=harness(t);await settle();h.app.accept(snapshot(["a","b","c","d"].map(id=>story(id))));h.click("ndUpdates");["a","b","c","d"].forEach(id=>chooseReport(h,id));
 assert.match(h.doc.getElementById("ndCompareCount").textContent,/^3 /);assert.match(h.doc.getElementById("ndAnnounce").textContent,/up to three/);h.click("ndCompareOpen");
 assert.deepEqual(Array.from(h.doc.querySelectorAll("#ndCompareReports .nd-comparison-report")).map(n=>n.dataset.storyId),["a","b","c"]);
 close(h,"ndCompare");h.click("ndCompareClear");assert.equal(h.doc.getElementById("ndCompareTray").hidden,true);assert.equal(h.doc.getElementById("ndCompareOpen").disabled,true);
});
test("named investigations persist IDs and reader relationships, then resolve corrections and missing references",async t=>{
 const h=harness(t);await settle();h.app.accept(snapshot([story("a"),story("b")]));h.click("ndUpdates");chooseReport(h,"a");chooseReport(h,"b");h.click("ndCompareOpen");
 h.doc.getElementById("ndCompareRelation").value="accounts";h.doc.getElementById("ndCompareRelation").dispatchEvent(new h.win.Event("change"));h.click("ndCompareSave");
 const saved=createInvestigation(h,"Two accounts to examine");assert.deepEqual(saved.storyIds,["a","b"]);assert.equal(saved.relation,"accounts");
 h.app.accept(snapshot([story("a",{headline:"Amended source report a",brief:"Revised licensed briefing"})]));
 assert.match(h.doc.getElementById("ndInvestigationReports").textContent,/Amended source report a/);assert.match(h.doc.getElementById("ndInvestigationReports").textContent,/Outside the live feed/);assert.deepEqual(readPreferences(h).research.investigations[0].storyIds,["a","b"]);
 h.doc.getElementById("ndInvestigationRename").value="Working question";submit(h,"ndInvestigationRenameForm");assert.equal(readPreferences(h).research.investigations[0].name,"Working question");
 const persisted=JSON.stringify(readPreferences(h));assert.doesNotMatch(persisted,/Amended source report|Revised licensed|Private publisher/);
 const reloaded=harness(t,{preferences:readPreferences(h)});await settle();reloaded.click("ndInvestigationsOpen");assert.match(reloaded.doc.getElementById("ndInvestigationReports").textContent,/Source report a/);assert.match(reloaded.doc.getElementById("ndInvestigationReports").textContent,/Saved report 2/);
 h.click("ndInvestigationDelete");assert.equal(readPreferences(h).research.investigations.length,0);assert.equal(h.doc.activeElement.id,"ndInvestigationName");
});
test("stable investigation IDs survive the feed's visual duplicate collapse",async t=>{
 const h=harness(t,{preferences:{research:{investigations:[{id:"case",name:"Saved reference",storyIds:["b"],relation:"question"}]}}});await settle();
 h.app.accept(snapshot([story("a",{url:"https://example.com/shared"}),story("b",{url:"https://example.com/shared",headline:"The second stable report"})]));h.click("ndInvestigationsOpen");
 assert.match(h.doc.getElementById("ndInvestigationReports").textContent,/The second stable report/);assert.doesNotMatch(h.doc.getElementById("ndInvestigationReports").textContent,/Outside the live feed/);
 h.doc.querySelector('[data-research-focus="investigation-read-b"]').click();assert.equal(h.doc.getElementById("ndStoryTitle").textContent,"The second stable report");
 h.app.accept(snapshot([story("a",{url:"https://example.com/shared"}),story("b",{url:"https://example.com/shared",headline:"Corrected second stable report",brief:"Corrected deduplicated body"})]));assert.equal(h.doc.getElementById("ndStoryTitle").textContent,"Corrected second stable report");assert.match(h.doc.getElementById("ndDetailBody").textContent,/Corrected deduplicated body/);
 h.app.accept(snapshot([story("a",{url:"https://example.com/shared"})]));h.doc.documentElement.dataset.lang="zh";h.doc.dispatchEvent(new h.win.Event("langchange"));assert.doesNotMatch(h.doc.getElementById("ndDetailBody").textContent,/Corrected second stable report|Corrected deduplicated body/);
});
test("mobile investigation inputs retain focus and unfinished text through live updates and language changes",async t=>{
 const h=harness(t,{mobile:true});await settle();selected(h);h.doc.querySelector('[data-action="detail-action-4"]').click();
 assert.equal(h.doc.getElementById("ndInvestigations").open,true);const name=h.doc.getElementById("ndInvestigationName");name.focus();name.value="Unfinished question";
 h.app.accept(snapshot([story("a",{headline:"Corrected source report"})]));h.doc.documentElement.dataset.lang="zh";h.doc.dispatchEvent(new h.win.Event("langchange"));
 assert.equal(h.doc.activeElement,name);assert.equal(name.value,"Unfinished question");h.key("Tab");assert.equal(h.doc.activeElement,name);assert.equal(h.doc.getElementById("ndDetail").getAttribute("aria-modal"),"true");
 close(h,"ndInvestigations");assert.equal(h.doc.activeElement.dataset.action,"detail-action-4");
});
test("monitoring has a silent baseline and one inbox update per report across overlapping targets",async t=>{
 const h=harness(t,{preferences:monitoredPreferences});await settle();h.click("ndMonitorOpen");assert.equal(readPreferences(h).research.updates.length,0);
 const amended=story("a",{headline:"Corrected report a",brief:"Private amended body"});h.app.accept(snapshot([amended,story("b")]));
 let updates=readPreferences(h).research.updates;assert.equal(updates.length,2);assert.equal(updates.find(u=>u.id==="a").kind,"amendment");assert.deepEqual(updates.find(u=>u.id==="a").targets,["v:reports","i:question"]);assert.equal(updates.find(u=>u.id==="b").kind,"arrival");
 h.app.accept(snapshot([amended,story("b")]));assert.equal(readPreferences(h).research.updates.length,2);
 h.app.accept(snapshot([story("b")]));updates=readPreferences(h).research.updates;assert.equal(updates.length,3);assert.equal(updates[0].kind,"removal");assert.match(h.doc.getElementById("ndMonitorItems").textContent,/does not establish a withdrawal/);assert.doesNotMatch(h.doc.getElementById("ndMonitorItems").textContent,/Private amended body|Corrected report a/);
 h.click("ndMonitorReadAll");assert.equal(h.doc.getElementById("ndMonitorCount").hidden,true);assert.ok(readPreferences(h).research.updates.every(u=>u.read));
 const unread=h.doc.querySelector('[data-research-focus="update-read-'+updates[0].n+'"]');unread.focus();unread.click();assert.equal(h.doc.activeElement.dataset.researchFocus,unread.dataset.researchFocus);assert.equal(h.doc.getElementById("ndMonitorCount").textContent,"1");
 h.click("ndMonitorQuiet");assert.equal(readPreferences(h).research.quiet,false);assert.doesNotMatch(JSON.stringify(readPreferences(h)),/Private amended body|Corrected report a|Private publisher/);
});
test("monitoring enable, pause, reset and auth renewal never replay earlier reporting",async t=>{
 const preferences=JSON.parse(JSON.stringify(monitoredPreferences));preferences.research.enabled=false;
 const h=harness(t,{preferences});await settle();h.click("ndMonitorOpen");h.app.accept(snapshot([story("a",{headline:"First amended report"})]));assert.equal(readPreferences(h).research.updates.length,0);
 h.click("ndMonitorEnable");assert.equal(readPreferences(h).research.updates.length,0);h.app.accept(snapshot([story("a",{headline:"Second amended report"})]));assert.equal(readPreferences(h).research.updates.length,1);
 h.click("ndMonitorEnable");h.app.accept(snapshot([story("a",{headline:"Third amended report"})]));h.click("ndMonitorEnable");assert.equal(readPreferences(h).research.updates.length,1);h.click("ndMonitorReset");assert.equal(readPreferences(h).research.updates.length,0);
 h.win.dispatchEvent(new h.win.CustomEvent("mdx-auth",{detail:{user:null,event:"SIGNED_OUT"}}));assert.equal(h.doc.getElementById("ndMonitor").open,false);assert.equal(readPreferences(h).research.records.length,0);assert.equal(readPreferences(h).research.updates.length,0);assert.equal(readPreferences(h).research.investigations[0].storyIds[0],"a");
 h.setPayload(snapshot([story("a",{headline:"Current report after renewal"})]));h.win.dispatchEvent(new h.win.CustomEvent("mdx-auth",{detail:{user:{id:"new-session"},event:"SIGNED_IN"}}));await h.advance(0);assert.equal(readPreferences(h).research.updates.length,0);h.click("ndMonitorOpen");assert.doesNotMatch(h.doc.getElementById("ndMonitorItems").textContent,/First amended|Second amended|Third amended/);
});

const retainedRevision="a".repeat(64),retainedRevisionNext="b".repeat(64);
const retainedDescriptor=(revision=retainedRevision)=>({state:"available",schema:"intelligence.retained_history/v1",revision,bounds:{retention_hours:72,max_stories:1500,retention_basis:"owner_updated_at"},retained_count:3,displayable_count:3,excluded_count:0});
const retainedSnapshot=(stories=[story()],revision=retainedRevision)=>Object.assign(snapshot(stories),{retained_history:retainedDescriptor(revision)});
const queryEcho=url=>{const p=new URL(url,"https://example.com").searchParams;return{q:p.get("q")||"",source:p.get("source")||"",feed_id:p.get("feed_id")||"",category:p.get("category")||"",language:p.get("language")||"",from_at:p.get("from_at"),to_at:p.get("to_at"),limit:Number(p.get("limit")||50)};};
const retainedPage=(url,stories,extra={})=>Object.assign({schema:"intelligence.history_page/v1",revision:retainedRevision,as_of:"2026-10-18T04:00:00Z",collection:"retained_current_packets",order:"recorded_acceptance_desc_then_id",bounds:retainedDescriptor().bounds,retained_count:3,displayable_count:3,excluded_count:0,matched_count:stories.length+(extra.next_cursor?1:0),returned_count:stories.length,stories,next_cursor:null,query:queryEcho(url)},extra);
const response=(status,payload={})=>({ok:status>=200&&status<300,status,text:async()=>JSON.stringify(payload)});
async function prepareHistory(t,options){const h=harness(t,options);await settle();const payload=retainedSnapshot();h.setPayload(payload);h.app.accept(payload);return h;}

test("retained search is deliberate, literal and paginated with the same query and no live arrivals",async t=>{
 const h=await prepareHistory(t,{preferences:monitoredPreferences});h.click("ndHistoryOpen");assert.equal(h.historyRequests().length,0);assert.match(h.doc.getElementById("ndHistoryBounds").textContent,/72 hours and 1500/);
 h.doc.getElementById("ndHistoryQuery").value="Oil OR gas";h.doc.getElementById("ndHistorySource").value="Exact publisher";h.doc.getElementById("ndHistoryFrom").value="2026-10-18T00:00";
 h.setHistory(async url=>response(200,retainedPage(url,[story(new URL(url,"https://example.com").searchParams.has("cursor")?"retained-two":"retained-one",{headline:"Retained literal report",brief:"Protected retained body"})],{matched_count:2,next_cursor:new URL(url,"https://example.com").searchParams.has("cursor")?null:"opaque_page_2"})));
 submit(h,"ndHistoryForm");await settle();assert.equal(h.historyRequests().length,1);const request=h.historyRequests()[0];assert.equal(new URL(request.url,"https://example.com").searchParams.get("q"),"Oil OR gas");assert.equal(request.options.credentials,"same-origin");assert.equal(request.options.cache,"no-store");assert.equal(request.options.headers.Accept,"application/json");assert.equal(h.doc.querySelectorAll("#ndHistoryResults .nd-history-row").length,1);
 const details=h.doc.querySelector("#ndHistoryResults .nd-history-report");
 // Lazy content is rendered by the native toggle task; setImmediate passes do not await it.
 const toggled=new Promise(resolve=>details.addEventListener("toggle",resolve,{once:true}));details.open=true;await toggled;assert.match(details.textContent,/Protected retained body/);
 const body=h.doc.querySelector("#ndHistory .nd-dialog-body");body.scrollTop=113;h.click("ndHistoryMore");await settle();assert.equal(h.doc.querySelectorAll("#ndHistoryResults .nd-history-row").length,2);assert.equal(body.scrollTop,113);
 const next=new URL(h.historyRequests()[1].url,"https://example.com").searchParams;assert.equal(next.get("q"),"Oil OR gas");assert.equal(next.get("source"),"Exact publisher");assert.equal(next.get("cursor"),"opaque_page_2");assert.equal(next.get("from_at"),new Date("2026-10-18T00:00").toISOString());
 assert.doesNotMatch(h.doc.getElementById("ndFeed").textContent,/Retained literal report/);assert.equal(readPreferences(h).research.updates.length,0);assert.doesNotMatch(JSON.stringify(readPreferences(h)),/Protected retained|Retained literal|Exact publisher/);
});
test("a changed history descriptor clears an open historical comparison and preserves saved IDs",async t=>{
 const h=await prepareHistory(t);chooseReport(h,"a");h.click("ndHistoryOpen");h.setHistory(async url=>response(200,retainedPage(url,[story("historical",{headline:"Historical source title",brief:"Historical protected body"})])));submit(h,"ndHistoryForm");await settle();h.doc.querySelector('[data-research-focus="history-pick-historical"]').click();h.click("ndHistoryCompare");assert.match(h.doc.getElementById("ndCompareReports").textContent,/Historical protected body/);
 h.click("ndCompareSave");const saved=createInvestigation(h,"Cross-window question");close(h,"ndInvestigations");h.app.accept(retainedSnapshot([story("a",{headline:"Current amended live report"})],retainedRevisionNext));
 assert.equal(h.doc.getElementById("ndCompare").open,true);assert.match(h.doc.getElementById("ndCompareReports").textContent,/Current amended live report/);assert.match(h.doc.getElementById("ndCompareReports").textContent,/Report outside the current feed/);assert.doesNotMatch(h.doc.getElementById("ndCompareReports").textContent,/Historical protected body|Historical source title/);assert.deepEqual(readPreferences(h).research.investigations[0].storyIds,saved.storyIds);assert.equal(h.doc.getElementById("ndHistoryResults").textContent,"");assert.equal(h.doc.getElementById("ndHistoryMore").hidden,true);assert.equal(h.historyRequests().length,1);
});
test("returning to an open comparison closes later dialogs and a new query clears its historical body immediately",async t=>{
 const h=await prepareHistory(t);h.app.accept(retainedSnapshot([story("a"),story("b")]));h.click("ndUpdates");chooseReport(h,"a");chooseReport(h,"b");h.click("ndCompareOpen");h.click("ndCompareSave");createInvestigation(h,"A retained question");h.click("ndInvestigationHistory");
 h.setHistory(async url=>response(200,retainedPage(url,[story("historical",{brief:"Old query protected body"})])));submit(h,"ndHistoryForm");await settle();h.doc.querySelector('[data-research-focus="history-pick-historical"]').click();h.click("ndHistoryCompare");
 assert.equal(h.doc.getElementById("ndCompare").open,true);assert.equal(h.doc.getElementById("ndHistory").open,false);assert.equal(h.doc.getElementById("ndInvestigations").open,false);assert.equal(h.doc.activeElement.closest("dialog").id,"ndCompare");assert.match(h.doc.getElementById("ndCompareReports").textContent,/Old query protected body/);
 h.click("ndCompareSave");h.click("ndInvestigationHistory");let finish,request;h.setHistory(url=>{request=url;return new Promise(resolve=>finish=resolve);});h.doc.getElementById("ndHistoryQuery").value="another phrase";submit(h,"ndHistoryForm");assert.doesNotMatch(h.doc.getElementById("ndCompareReports").textContent,/Old query protected body/);assert.match(h.doc.getElementById("ndCompareReports").textContent,/Report outside the current feed/);
 close(h,"ndHistory");close(h,"ndInvestigations");finish(response(200,retainedPage(request,[story("late-query",{brief:"Late query protected body"})])));await settle();assert.doesNotMatch(h.doc.getElementById("ndCompareReports").textContent,/Old query protected body|Late query protected body/);
});
test("a 409 history cursor clears prior results and needs an explicit restart",async t=>{
 const h=await prepareHistory(t);h.click("ndHistoryOpen");h.setHistory(async url=>response(200,retainedPage(url,[story("old-history")],{next_cursor:"cursor_2"})));submit(h,"ndHistoryForm");await settle();
 h.setHistory(async()=>response(409,{detail:{code:"history_revision_changed",restart_required:true}}));h.click("ndHistoryMore");await settle();assert.equal(h.doc.getElementById("ndHistoryResults").textContent,"");assert.equal(h.doc.getElementById("ndHistoryMore").hidden,true);assert.match(h.doc.getElementById("ndHistoryStatus").textContent,/Restart the search/);assert.equal(h.historyRequests().length,2);
 h.app.accept(retainedSnapshot([story()],retainedRevisionNext));assert.equal(h.historyRequests().length,2);h.setHistory(async url=>response(200,retainedPage(url,[story("current-history")],{revision:retainedRevisionNext})));h.click("ndHistoryRestart");await settle();assert.equal(h.historyRequests().length,3);assert.match(h.doc.getElementById("ndHistoryResults").textContent,/current-history/);assert.equal(new URL(h.historyRequests()[2].url,"https://example.com").searchParams.has("cursor"),false);
});
test("a newer history page waits for the accepted live descriptor without rendering its bodies",async t=>{
 const h=await prepareHistory(t);h.click("ndHistoryOpen");h.setHistory(async url=>response(200,retainedPage(url,[story("leading-history")],{revision:retainedRevisionNext})));submit(h,"ndHistoryForm");await settle();assert.equal(h.doc.getElementById("ndHistoryResults").textContent,"");assert.equal(h.doc.getElementById("ndHistoryRestart").disabled,true);assert.match(h.doc.getElementById("ndHistoryStatus").textContent,/Waiting for the live feed/);
 h.app.accept(retainedSnapshot([story()],retainedRevisionNext));assert.equal(h.doc.getElementById("ndHistoryRestart").disabled,false);assert.equal(h.historyRequests().length,1);h.click("ndHistoryRestart");await settle();assert.match(h.doc.getElementById("ndHistoryResults").textContent,/leading-history/);
});
test("a fresh accepted snapshot permits a deliberate retry after a transient history revision",async t=>{
 const h=await prepareHistory(t);h.click("ndHistoryOpen");h.setHistory(async url=>response(200,retainedPage(url,[story("transient-history")],{revision:retainedRevisionNext})));submit(h,"ndHistoryForm");await settle();assert.equal(h.doc.getElementById("ndHistoryRestart").disabled,true);
 h.app.accept(retainedSnapshot());assert.equal(h.doc.getElementById("ndHistoryRestart").disabled,false);assert.equal(h.historyRequests().length,1);assert.doesNotMatch(h.doc.getElementById("ndHistoryResults").textContent,/transient-history/);
 h.setHistory(async url=>response(200,retainedPage(url,[story("current-history")])));h.click("ndHistoryRestart");await settle();assert.match(h.doc.getElementById("ndHistoryResults").textContent,/current-history/);assert.equal(h.historyRequests().length,2);
});
test("history pagination rejects a changed match total within the same revision",async t=>{
 const h=await prepareHistory(t);h.click("ndHistoryOpen");h.setHistory(async url=>response(200,retainedPage(url,[story("first-history")],{matched_count:2,next_cursor:"cursor_2"})));submit(h,"ndHistoryForm");await settle();
 h.setHistory(async url=>response(200,retainedPage(url,[story("inconsistent-history")],{matched_count:3})));h.click("ndHistoryMore");await settle();assert.equal(h.doc.getElementById("ndHistoryResults").textContent,"");assert.match(h.doc.getElementById("ndHistoryStatus").textContent,/could not be completed/);assert.equal(h.doc.getElementById("ndHistoryMore").hidden,true);assert.equal(h.historyRequests().length,2);
});
test("retained search generations abort and ignore superseded queries",async t=>{
 const h=await prepareHistory(t);h.click("ndHistoryOpen");const pending=[];h.setHistory((url,options)=>new Promise(resolve=>pending.push({url,options,resolve})));
 h.doc.getElementById("ndHistoryQuery").value="first phrase";submit(h,"ndHistoryForm");h.doc.getElementById("ndHistoryQuery").value="second phrase";submit(h,"ndHistoryForm");assert.equal(pending.length,2);assert.equal(pending[0].options.signal.aborted,true);
 pending[1].resolve(response(200,retainedPage(pending[1].url,[story("new-query",{headline:"Second phrase report"})])));await settle();pending[0].resolve(response(200,retainedPage(pending[0].url,[story("old-query",{headline:"Stale first phrase report"})])));await settle();
 assert.match(h.doc.getElementById("ndHistoryResults").textContent,/Second phrase report/);assert.doesNotMatch(h.doc.getElementById("ndHistoryResults").textContent,/Stale first phrase/);assert.match(h.doc.getElementById("ndHistoryQuerySummary").textContent,/second phrase/);
});
test("retained search has a real deadline even when a late fixture ignores abort",async t=>{
 const h=await prepareHistory(t);h.click("ndHistoryOpen");let finish,requested;h.setHistory((url,options)=>{requested={url,options};return new Promise(resolve=>finish=resolve);});submit(h,"ndHistoryForm");await h.advance(10000);assert.equal(requested.options.signal.aborted,true);assert.match(h.doc.getElementById("ndHistoryStatus").textContent,/could not be completed/);assert.equal(h.doc.getElementById("ndHistoryResults").textContent,"");
 finish(response(200,retainedPage(requested.url,[story("late-history")])));await settle();assert.doesNotMatch(h.doc.getElementById("ndHistoryResults").textContent,/late-history/);assert.equal(h.historyRequests().length,1);
});
for(const status of [401,403])test("history HTTP "+status+" clears protected dialogs and fences the active stream",async t=>{
 const h=await prepareHistory(t);const stream=h.streams[0];chooseReport(h,"a");h.click("ndHistoryOpen");h.setHistory(async url=>response(200,retainedPage(url,[story("private-history",{brief:"Private historical body"})],{next_cursor:"cursor_2"})));submit(h,"ndHistoryForm");await settle();h.doc.querySelector('[data-research-focus="history-pick-private-history"]').click();
 let finish;h.setHistory(()=>new Promise(resolve=>finish=resolve));h.click("ndHistoryMore");h.click("ndHistoryCompare");assert.equal(h.doc.getElementById("ndCompare").open,true);finish(response(status));await settle();
 assert.equal(h.app.getState().mode,"restricted");assert.equal(stream.closed,true);for(const id of ["ndHistory","ndCompare","ndInvestigations","ndMonitor"])assert.equal(h.doc.getElementById(id).open,false);assert.equal(h.doc.getElementById("ndCompareReports").textContent,"");assert.equal(h.doc.getElementById("ndHistoryResults").textContent,"");assert.equal(h.doc.getElementById("ndHistoryQuerySummary").textContent,"");assert.doesNotMatch(h.doc.getElementById("ndHistoryBounds").textContent,/1500/);assert.doesNotMatch(h.doc.getElementById("ndFeed").textContent,/Source report/);assert.equal(h.doc.getElementById("ndCompareTray").hidden,true);
 stream.emit("snapshot",retainedSnapshot([story("obsolete")]));h.doc.documentElement.dataset.lang="zh";h.doc.dispatchEvent(new h.win.Event("langchange"));assert.doesNotMatch(h.doc.body.textContent,/Private historical body|obsolete/);
 const requests=h.requests();h.win.dispatchEvent(new h.win.Event("online"));await h.advance(0);assert.equal(h.requests(),requests);h.win.dispatchEvent(new h.win.CustomEvent("mdx-auth",{detail:{user:{id:"renewed-session"},event:"SIGNED_IN"}}));await h.advance(0);assert.equal(h.requests(),requests+1);assert.notEqual(h.app.getState().mode,"restricted");assert.doesNotMatch(h.doc.body.textContent,/Private historical body/);
});
test("a 503 retained page does not keep the last successful historical body",async t=>{
 const h=await prepareHistory(t);h.click("ndHistoryOpen");h.setHistory(async url=>response(200,retainedPage(url,[story("prior-success")],{next_cursor:"cursor_2"})));submit(h,"ndHistoryForm");await settle();h.setHistory(async()=>response(503));h.click("ndHistoryMore");await settle();assert.equal(h.doc.getElementById("ndHistoryResults").textContent,"");assert.match(h.doc.getElementById("ndHistoryStatus").textContent,/unavailable/);assert.match(h.doc.getElementById("ndFeed").textContent,/Source report a/);assert.equal(h.doc.getElementById("ndHistoryMore").hidden,true);
});
test("coverage keeps missing collection counters unknown and updates an open disclosure without taking focus",async t=>{
 const h=harness(t);await settle();const source={id:"source-a",publisher:"Observed publisher",enabled:true,status:"observed",last_fetch_success_at:"2026-10-18T03:59:00Z"};h.app.accept(Object.assign(snapshot([story("a",{feed_id:"source-a",language:"en",category:"energy"})]),{source_health:[source]}));h.click("ndCoverageOpen");
 const details=h.doc.querySelector(".nd-coverage-source-details");details.open=true;details.querySelector("summary").focus();const key=h.doc.activeElement.dataset.researchFocus;assert.match(details.textContent,/Items observedUnknown/);assert.match(h.doc.getElementById("ndCoverageBody").textContent,/Previously checked/);
 h.app.accept(Object.assign(snapshot([story("a",{feed_id:"source-a",language:"en",category:"energy"})]),{source_health:[Object.assign({},source,{last_outcome:"unchanged",last_observed_item_count:0,last_http_status:200,last_attempt_duration_ms:73})]}));assert.equal(h.doc.activeElement.dataset.researchFocus,key);assert.equal(h.doc.querySelector(".nd-coverage-source-details").open,true);assert.match(h.doc.querySelector(".nd-coverage-source-details").textContent,/Items observed0/);assert.match(h.doc.getElementById("ndCoverageBody").textContent,/No reporting changes/);
});


test("embedded News sign-in delegates once to the shell while initialization is pending",async t=>{
 const h=harness(t);await settle();const intents=[];
 h.win.MMXSharedShell={active:false,openAuth:mode=>intents.push(mode)};
 for(const id of ["ndSignIn","ndCompanySignIn"]){
  const link=h.doc.getElementById(id),href=link.getAttribute("href");
  const event=new h.win.MouseEvent("click",{button:0,bubbles:true,cancelable:true});
  assert.equal(link.dispatchEvent(event),false);
  assert.equal(event.defaultPrevented,true);
  assert.equal(link.getAttribute("href"),href);
  assert.equal(href,"/?signin=1&ret=news.html");
 }
 assert.deepEqual(intents,["signin","signin"]);
});

test("News sign-in retains standalone and modified-link navigation",async t=>{
 const h=harness(t);await settle();const intents=[];
 function inspect(id,options){
  const link=h.doc.getElementById(id);let handled;
  // Observe the application decision, then stop jsdom's unimplemented navigation.
  link.addEventListener("click",event=>{handled=event.defaultPrevented;event.preventDefault();},{once:true});
  link.dispatchEvent(new h.win.MouseEvent("click",Object.assign({button:0,bubbles:true,cancelable:true},options)));
  assert.equal(handled,false);assert.equal(link.getAttribute("href"),"/?signin=1&ret=news.html");
 }
 for(const id of ["ndSignIn","ndCompanySignIn"]){
  delete h.win.MMXSharedShell;inspect(id,{});
  h.win.MMXSharedShell={active:false};inspect(id,{});
  h.win.MMXSharedShell={active:true,openAuth:mode=>intents.push(mode)};
  for(const options of [{ctrlKey:true},{metaKey:true},{shiftKey:true},{altKey:true},{button:1},{button:2}])inspect(id,options);
  const link=h.doc.getElementById(id);
  link.setAttribute("target","_blank");inspect(id,{});link.removeAttribute("target");
  link.setAttribute("download","");inspect(id,{});link.removeAttribute("download");
 }
 assert.deepEqual(intents,[]);
});

test("News sign-in respects a previously handled click",async t=>{
 const h=harness(t);await settle();const intents=[];
 h.win.MMXSharedShell={openAuth:mode=>intents.push(mode)};
 for(const id of ["ndSignIn","ndCompanySignIn"]){
  const link=h.doc.getElementById(id);
  link.addEventListener("click",event=>event.preventDefault(),{capture:true,once:true});
  link.dispatchEvent(new h.win.MouseEvent("click",{button:0,bubbles:true,cancelable:true}));
 }
 assert.deepEqual(intents,[]);
});


test("a claimed News sign-in never starts a second route after shell refusal or failure",async t=>{
 const h=harness(t);await settle();let attempts=0,localAuth=0;
 h.win.MDXAuth={open:()=>localAuth++};
 for(const throws of [false,true]){
  h.win.MMXSharedShell={openAuth:mode=>{attempts++;assert.equal(mode,"signin");if(throws)throw new Error("shell unavailable");return false;}};
  for(const id of ["ndSignIn","ndCompanySignIn"]){
   const link=h.doc.getElementById(id),event=new h.win.MouseEvent("click",{button:0,bubbles:true,cancelable:true});
   assert.equal(link.dispatchEvent(event),false);assert.equal(event.defaultPrevented,true);
   assert.equal(link.getAttribute("href"),"/?signin=1&ret=news.html");
  }
 }
 assert.equal(attempts,4);assert.equal(localAuth,0);
});
