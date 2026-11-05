const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),test=require('node:test');
const root=require('path').resolve(__dirname,'..');const template=fs.readFileSync(root+'/templates/government-revenue-page.js.j2','utf8');const controller=template.slice(template.indexOf('var priorityEpoch='),template.indexOf('\n  function restoreUrl',template.indexOf('var priorityEpoch=')));const flush=()=>new Promise(r=>setImmediate(r));
function fixture(initial=null){let ticker='LMT',calls=[],pending=[],listeners=[];const secondary=name=>({load(){calls.push([name,ticker]);return Promise.resolve()}});const investor={load(){let resolve;const promise=new Promise(r=>resolve=r);pending.push({promise,resolve});calls.push(['finance',ticker]);return promise},state:()=>({ticker}),loadResearch(){calls.push(['research',ticker])}};const window={__govrevFirstInvestor:initial,MDXAuth:{onChange:cb=>listeners.push(cb),enabled:()=>true}};const ctx={window,state:{mode:'changes',ticker:'',selected:''},Promise,JSON,investorUI:investor,budgetUI:secondary('budget'),programsUI:secondary('programs'),candidateUI:secondary('candidates'),fmsUI:secondary('fms'),sbirUI:secondary('sbir'),themeUI:secondary('themes'),hydrateWorkspace(){calls.push(['workspace',ticker])}};vm.createContext(ctx);vm.runInContext(controller,ctx);return {ctx,calls,pending,listeners,select(t){ticker=t},emit(user,event='SIGNED_IN'){listeners.forEach(f=>f(user,event))}}}
test('finance settles before all eight preserved secondary reads',async()=>{let f=fixture();f.ctx.bindAuthReload();f.emit({id:'a'});assert.deepEqual(f.calls,[['finance','LMT']]);f.pending[0].resolve({ready:true});await flush();assert.deepEqual(f.calls.map(x=>x[0]),['finance','budget','programs','candidates','fms','sbir','research','themes','workspace'])});
test('typed finance failure still loads secondary panels',async()=>{let f=fixture();f.ctx.bindAuthReload();f.emit({id:'a'});f.pending[0].resolve(null);await flush();assert.equal(f.calls.length,9)});
for(const event of ['SIGNED_OUT','SIGNED_IN'])test('old finance cannot start secondary work after '+event,async()=>{let f=fixture();f.ctx.bindAuthReload();f.emit({id:'a'});f.emit(event==='SIGNED_OUT'?null:{id:'b'},event);f.pending[0].resolve({ready:true});await flush();assert.equal(f.calls.length,2);f.pending[1].resolve(null);await flush();assert.equal(f.calls.length,10)});
test('selection changes are guarded before secondary continuation',async()=>{let f=fixture();f.ctx.bindAuthReload();f.emit({id:'a'});f.select('LHX');f.pending[0].resolve({ready:true});await flush();assert.deepEqual(f.calls,[['finance','LMT'],['finance','LHX']]);f.pending[1].resolve({ready:true});await flush();assert(f.calls.slice(2).every(x=>x[1]==='LHX'))});
test('same initial auth notification coalesces while and after settled',async()=>{let f=fixture();f.ctx.bindAuthReload();f.emit({id:'a'},'INITIAL_SESSION');f.emit({id:'a'},'INITIAL_SESSION');assert.equal(f.calls.length,1);f.pending[0].resolve(null);await flush();f.emit({id:'a'},'INITIAL_SESSION');await flush();assert.equal(f.pending.length,1)});
test('first promise is adopted once without another finance fetch',async()=>{let resolve;let first={subject:'a',promise:new Promise(r=>resolve=r),owned:false};let f=fixture(first);f.ctx.bindAuthReload();f.emit({id:'a'},'INITIAL_SESSION');assert(first.owned);assert.equal(f.pending.length,0);resolve({ready:true});await flush();assert.equal(f.calls.length,8);assert.equal(first.promise,null)});
test('first promise from another subject is not adopted',async()=>{let f=fixture({subject:'a',promise:Promise.resolve({ready:true}),owned:false});f.ctx.bindAuthReload();f.emit({id:'b'},'INITIAL_SESSION');assert.equal(f.pending.length,1);assert.equal(f.calls.length,1)});
test('early instance mounts once and stops fetching after page takes ownership',async()=>{let mounts=0,loads=0,listeners=[],sessions=0;const window={createGovernmentRevenueInvestor:()=>({mount(){mounts++},load(){loads++;return Promise.resolve(null)}}),MDXAuth:{onChange:f=>listeners.push(f),client:()=>Promise.resolve({auth:{getSession:()=>{sessions++;return Promise.resolve({data:{session:null}})}}})}};vm.runInNewContext(fs.readFileSync(root+'/templates/government-revenue-investor-start.js','utf8'),{window,Promise,document:{createElement:()=>({setAttribute(){}}),head:{appendChild:s=>queueMicrotask(()=>s.onload())}}});listeners[0]({id:'a'},'INITIAL_SESSION');listeners[0]({id:'a'},'INITIAL_SESSION');assert.equal(mounts,1);assert.equal(loads,1);window.__govrevFirstInvestor.owned=true;listeners[0]({id:'b'},'SIGNED_IN');assert.equal(loads,1);await flush();assert.equal(sessions,1)});
for (const name of ['createGovernmentRevenueBudget','createGovernmentRevenueFms']) {
 function moduleFixture(owned){let events=[],reads=0,resolve;let window={addEventListener:(n,f)=>{if(n==='mdx-auth')events.push(f)},fetch:()=>{reads++;return new Promise(r=>resolve=r)}};window.window=window;let context={window,Promise,URL,Date,console};vm.runInNewContext(fs.readFileSync(root+'/templates/government-revenue-dossiers.js','utf8'),context);let rows=[];let ui=window[name]({authReloadOwner:owned,obj:x=>!!x&&typeof x==='object'&&!Array.isArray(x),arr:x=>Array.isArray(x)?x:[],esc:String,text:x=>String(x||''),n:Number,money:String,date:String,tr:x=>x,safeUrl:x=>x,host:()=>null,onRows:(r,m)=>rows.push(m.status)});return {ui,events,rows,get reads(){return reads},finish(){resolve({ok:false,status:503,json:()=>Promise.resolve({})})}}}
 test(name+' standalone auth reload default remains active',async()=>{let f=moduleFixture(false);f.events.forEach(cb=>cb());await flush();assert.equal(f.reads,1);f.finish();await flush()});
 test(name+' page owner suppresses duplicate auth fetch and invalidates old result',async()=>{let f=moduleFixture(true);let pending=f.ui.load();await flush();assert.equal(f.reads,1);f.events.forEach(cb=>cb());await flush();assert.equal(f.reads,1);f.finish();await pending;assert.equal(f.rows.at(-1),'loading')});
}
function startup(authMode,failed=''){
 let network=0,clientCalls=0,scripts=[],notes=[],callbacks=[];
 let host={innerHTML:'',querySelectorAll:()=>[],querySelector:()=>null,contains:()=>false,insertAdjacentElement:(_,n)=>notes.push(n)};
 let document={documentElement:{getAttribute:()=> 'en'},activeElement:null,getElementById:()=>host,addEventListener(){},createElement:()=>({setAttribute(){}}),head:{appendChild:s=>{scripts.push(s);queueMicrotask(()=>s.src===failed?s.onerror():s.onload())}}};
 let window={document,location:{href:'https://local.test/government_revenue.html'},addEventListener(){},fetch(){network++;return Promise.resolve({ok:false,status:403})}};
 if(authMode!=='missing')window.MDXAuth={enabled:()=>authMode!=='disabled',onChange:f=>callbacks.push(f),client(){clientCalls++;return Promise.resolve({auth:{getSession:()=>Promise.resolve({data:{session:null}})}})}};
 const ctx={window,document,Promise,URL,Date,console:{error(){}},setTimeout};vm.createContext(ctx);vm.runInContext(fs.readFileSync(root+'/templates/government-revenue-investor.js','utf8'),ctx);vm.runInContext(fs.readFileSync(root+'/templates/government-revenue-investor-start.js','utf8'),ctx);
 return {window,scripts,notes,callbacks,get network(){return network},get clientCalls(){return clientCalls}};
}
for(const mode of ['missing','disabled'])test('actual early startup '+mode+' auth settles locked without network and releases every public tool',async()=>{let f=startup(mode);let result=await f.window.__govrevFirstInvestor.modulesReady;assert.equal(f.window.__govrevFirstInvestor.ui.state().status,'locked');assert.equal(f.network,0);assert.equal(f.clientCalls,0);assert.equal(result.state,'ready');assert.equal(f.scripts.length,7);assert(f.scripts.slice(0,6).every(s=>s.async===false));assert.equal(f.scripts[6].type,'module')});
test('actual early typed403 settles then loads modules, with visible partial on one module failure',async()=>{let f=startup('enabled','government-revenue-dossiers.js');f.callbacks[0](null,'INITIAL_SESSION');let result=await f.window.__govrevFirstInvestor.modulesReady;assert.equal(f.network,1);assert.equal(f.window.__govrevFirstInvestor.ui.state().status,'locked');assert.equal(result.state,'partial');assert.deepEqual(Array.from(result.failed),['government-revenue-dossiers.js']);assert.equal(f.notes.length,1);assert.match(f.notes[0].textContent,/could not load/)});

function restorationRace(){
 let resolve,notify,loads=0;
 const session=new Promise(r=>{resolve=r});
 const window={createGovernmentRevenueInvestor:()=>({mount(){},load(){loads++;return Promise.resolve(null)}}),MDXAuth:{onChange:f=>{notify=f},client:()=>Promise.resolve({auth:{getSession:()=>session}})}};
 const document={createElement:()=>({setAttribute(){}}),head:{appendChild:s=>queueMicrotask(()=>s.onload())}};
 vm.runInNewContext(fs.readFileSync(root+'/templates/government-revenue-investor-start.js','utf8'),{window,document,Promise});
 return {window,resolve,emit:(user,event)=>notify(user,event),get loads(){return loads}};
}
test('completed initial session starts finance before a delayed auth notification',async()=>{
 const f=restorationRace();f.resolve({data:{session:{user:{id:'restored'}}}});await flush();
 assert.equal(f.loads,1);assert.equal(f.window.__govrevFirstInvestor.subject,'restored');
 f.emit({id:'restored'},'INITIAL_SESSION');await flush();assert.equal(f.loads,1);
});
for(const event of ['SIGNED_OUT','SIGNED_IN'])test('newer '+event+' wins over pending initial session result',async()=>{
 const f=restorationRace();f.emit(event==='SIGNED_OUT'?null:{id:'new-user'},event);
 f.resolve({data:{session:{user:{id:'old-user'}}}});await flush();
 assert.equal(f.loads,1);assert.equal(f.window.__govrevFirstInvestor.subject,event==='SIGNED_OUT'?'':'new-user');
});
test('initial session result cannot reclaim finance from page owner',async()=>{
 const f=restorationRace();f.window.__govrevFirstInvestor.owned=true;f.resolve({data:{session:{user:{id:'restored'}}}});await flush();assert.equal(f.loads,0);
});

function actualInvestorRestoration(){
 let user=null,session={user:{id:'restored'},access_token:'fixture-token'},listeners=[],requests=[];
 const document={documentElement:{getAttribute:()=> 'en'},getElementById:()=>null,createElement:()=>({setAttribute(){}}),head:{appendChild:s=>queueMicrotask(()=>s.onload())}};
 const window={document,location:{href:'https://local.test/government_revenue.html'},addEventListener:(name,cb)=>{if(name==='mdx-auth')listeners.push(cb)},fetch:()=>new Promise(resolve=>requests.push(resolve))};
 window.MDXAuth={enabled:()=>true,user:()=>user,onChange:cb=>window.addEventListener('mdx-auth',e=>cb(e.detail.user,e.detail.event)),client:()=>Promise.resolve({auth:{getSession:()=>Promise.resolve({data:{session}})}})};
 const ctx={window,document,Promise,URL,Date,console};vm.createContext(ctx);
 vm.runInContext(fs.readFileSync(root+'/templates/government-revenue-investor.js','utf8'),ctx);
 vm.runInContext(fs.readFileSync(root+'/templates/government-revenue-investor-start.js','utf8'),ctx);
 return {ctx,window,requests,emit(next,event){user=next;session=next?{user:next,access_token:'fixture-token'}:null;listeners.forEach(cb=>cb({detail:{user:next,event}}))},complete(index,status=200){requests[index]({ok:status===200,status,json:()=>Promise.resolve(JSON.parse(fs.readFileSync(root+'/tests/fixtures/defense_economics.json','utf8')))})}};
}
test('actual page reuses the early investor and owns its later account reloads',async()=>{
 const f=actualInvestorRestoration();await flush();const initial=f.window.__govrevFirstInvestor;
 f.complete(0);await initial.promise;
 const start=template.indexOf('  var investorUI='),end=template.indexOf('\n',template.indexOf('if(!(window.__govrevFirstInvestor||{}).ui)investorUI.mount();',start));
 assert(start>=0&&end>start);f.window.createGovernmentRevenueInvestor=()=>{throw new Error('page must reuse the existing instance')};
 vm.runInContext(template.slice(start,end),f.ctx);assert.equal(f.ctx.investorUI,initial.ui);
 // Other panels are independent of investor ownership and stay bounded stubs.
 for(const name of ['budgetUI','programsUI','candidateUI','fmsUI','sbirUI','themeUI'])f.ctx[name]={load(){}};
 f.ctx.state={mode:'changes',ticker:'',selected:''};f.ctx.hydrateWorkspace=()=>{};f.ctx.investorUI.loadResearch=()=>{};
 vm.runInContext(controller,f.ctx);f.ctx.bindAuthReload();assert.equal(initial.owned,true);
 f.emit({id:'restored'},'INITIAL_SESSION');await f.ctx.priorityPending;assert.equal(f.requests.length,1);
 f.emit({id:'second'},'SIGNED_IN');await flush();assert.equal(f.requests.length,2);
 f.complete(1);await f.ctx.priorityPending;assert.equal(initial.ui.state().status,'ready');
 f.emit(null,'SIGNED_OUT');await flush();assert.equal(f.requests.length,3);
 f.complete(2,401);await f.ctx.priorityPending;assert.equal(initial.ui.state().status,'locked');assert.equal(initial.ui.state().content_id,null);
});
for(const eventBeforeResponse of [false,true])test('actual investor retains restored subject when matching INITIAL_SESSION arrives '+(eventBeforeResponse?'during':'after')+' its finance read',async()=>{
 const f=actualInvestorRestoration();await flush();assert.equal(f.requests.length,1);
 const initial=f.window.__govrevFirstInvestor;
 if(eventBeforeResponse)f.emit({id:'restored'},'INITIAL_SESSION');
 f.complete(0);await initial.promise;
 assert.equal(initial.ui.state().status,'ready');const identity=initial.ui.state().content_id;assert.ok(identity);
 if(!eventBeforeResponse)f.emit({id:'restored'},'INITIAL_SESSION');
 assert.equal(initial.ui.state().status,'ready');assert.equal(initial.ui.state().content_id,identity);assert.equal(f.requests.length,1);
});
test('actual investor drops early restored finance on a later sign-out',async()=>{
 const f=actualInvestorRestoration();await flush();const initial=f.window.__govrevFirstInvestor,old=initial.promise;
 f.emit(null,'SIGNED_OUT');await flush();assert.equal(f.requests.length,2);
 f.complete(0);await old;assert.equal(initial.ui.state().content_id,null);
 f.complete(1,403);await initial.promise;assert.equal(initial.ui.state().status,'locked');assert.equal(initial.ui.state().content_id,null);
});
test('actual investor rejects the old restored response after an account change',async()=>{
 const f=actualInvestorRestoration();await flush();const initial=f.window.__govrevFirstInvestor,old=initial.promise;
 f.emit({id:'other-subject'},'SIGNED_IN');await flush();assert.equal(f.requests.length,2);
 f.complete(0);await old;assert.equal(initial.ui.state().content_id,null);
 f.complete(1);await initial.promise;assert.equal(initial.ui.state().status,'ready');assert.equal(initial.subject,'other-subject');
});
