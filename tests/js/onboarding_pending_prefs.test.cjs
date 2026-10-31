const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const root=path.resolve(__dirname,'../..'), theme=fs.readFileSync(path.join(root,'templates/theme.js'),'utf8');
const current=theme.slice(theme.indexOf('  var SD_MARKETS ='),theme.indexOf('  var _sdDeskMsgTimer ='));
const original=fs.readFileSync(path.join(__dirname,'fixtures/legacy_macro_pending_prefs_51f0.js'),'utf8');
const KEY='mm.pendingPrefs', A={market_focus:['us'],trade_types:['options'],theme_pref:'dark'};
const owned=(prefs=A,owner='account-a')=>JSON.stringify([{prefs,attempts:0,owner_user_id:owner}]);
const tick=()=>new Promise(r=>setImmediate(r));
function setup(source=current,raw=null) {
 const store=new Map(raw===null?[]:[[KEY,raw]]),timers=[],messages=[],writes=[];
 const state={subject:'account-a',response:{error:null},update:null,client:null,lookup:null};
 const client={auth:{getUser:async()=>state.lookup?state.lookup():({data:{user:state.subject?{id:state.subject,email:state.subject+'@example.com'}:null},error:null}),
 updateUser:async data=>{writes.push({subject:state.subject,...data});return state.update?state.update(data):state.response;}}};
 const ctx={console,Promise,Date,JSON,isFinite,localStorage:{getItem:k=>store.get(k)??null,setItem:(k,v)=>store.set(k,v),removeItem:k=>store.delete(k)},
 _curUser:{id:'account-a',email:'account-a@example.com',user_metadata:{}},_authEnabled:true,
 getSupabaseClient:()=>state.client?state.client():Promise.resolve(client),setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout:()=>{},
 _sdDeskMsg:(_el,key,kind)=>messages.push({key,kind}),CustomEvent:function(){},window:{dispatchEvent(){}}};
 vm.createContext(ctx);vm.runInContext(source,ctx);
 ctx.window.MDXAuth={user:()=>ctx._curUser,queueOnboardingPrefs:ctx._queuePendingPrefs,deliverOnboardingPrefs:ctx._deliverPendingPrefs};
 return {ctx,store,state,writes,messages,timers,client,setUser:id=>{state.subject=id;ctx._curUser=id?{id,email:id+'@example.com',user_metadata:{}}:null;},flush:async()=>{for(const fn of timers.splice(0))fn();await tick();}};
}
function actualOnboard(x,pending=false){
 const s=fs.readFileSync(path.join(root,'templates/onboard.js'),'utf8');
 const code=s.slice(s.indexOf('  function persistPrefs()'),s.indexOf('  // ══════════════════════════ STEP 3'));
 Object.assign(x.ctx,{S:{firstName:'Fixture',lastName:'Reader',email:'account-a@example.com',prefs:A,confirmPending:pending,step:3},
 sbClient:()=>Promise.resolve(x.client),LS_PENDING_PREFS:KEY,STEP_DONE:5,stashSave(){},render(){}});
 vm.runInContext(code,x.ctx);return ()=>x.ctx.persistPrefs();
}
test('actual onboard preference writer retains resolved SDK errors and rejected requests',async()=>{
 for(const reject of [false,true]){
  const x=setup();if(reject)x.state.update=async()=>{throw Error('synthetic offline');};else x.state.response={error:{message:'synthetic offline'}};
  const out=await actualOnboard(x)();assert.equal(out.status,'pending');assert.equal(x.writes.length,1);
  assert.equal(JSON.parse(x.store.get(KEY))[0].owner_user_id,'account-a');assert.equal(x.ctx.S.prefsPending,true);
 }
});
test('pending verification uses existing unbound shape and real auth restoration delivers once',async()=>{
 const x=setup();x.setUser(null);await actualOnboard(x,true)();
 assert.equal(Array.isArray(JSON.parse(x.store.get(KEY))),false);assert.equal(x.writes.length,0);
 const onAuth=theme.slice(theme.indexOf('  function _onAuth('),theme.indexOf('  window.MDXAuth ='));
 Object.assign(x.ctx,{_sdPlan:null,_sdPlanFor:null,_sdUsage:null,_sdUsageFor:null,_sdUsageErr:false,_authReady:false,_emitAuth(){},_renderAcct(){}});
 vm.runInContext(onAuth,x.ctx);x.state.subject='account-a';x.ctx._onAuth('SIGNED_IN',{user:{id:'account-a',email:'account-a@example.com'}});
 await tick();assert.equal(x.writes.length,1);assert.equal(x.store.has(KEY),false);
});
test('foreign owner is invisible and cannot be delivered, replaced or cleared',async()=>{
 const raw=owned(),x=setup(current,raw);x.setUser('account-b');
 assert.equal(x.ctx._sdPendingPrefs(),null);assert.equal(x.ctx._queuePendingPrefs(A,'account-b'),false);
 assert.equal((await x.ctx._deliverPendingPrefs()).status,'held');assert.equal(x.writes.length,0);assert.equal(x.store.get(KEY),raw);
});
test('new owned bytes are safe for the original immutable Macro read/load/save consumer',async()=>{
 const raw=owned(),x=setup(original,raw);x.setUser('account-b');
 const loaded=x.ctx._sdLoadDesk();assert.deepEqual(JSON.parse(JSON.stringify(loaded)),{market_focus:[],trade_types:[]});
 // A deliberate new B edit still has the original semantics. It never borrows A's fields.
 x.ctx._sdDesk={market_focus:['hk'],trade_types:['stocks']};x.ctx._sdSaveDesk({});await x.flush();
 assert.equal(x.writes.length,1);assert.deepEqual(JSON.parse(JSON.stringify(x.writes[0].data.market_focus)),['hk']);
 assert.equal('theme_pref' in x.writes[0].data,false);assert.equal(x.store.get(KEY),raw);
});
test('account switch before the debounce retains A and never paints/writes B',async()=>{
 const x=setup();x.ctx._sdDesk={market_focus:['us'],trade_types:['options']};x.ctx._sdSaveDesk({});const raw=x.store.get(KEY);
 x.setUser('account-b');await x.flush();assert.equal(x.writes.length,0);assert.equal(x.messages.length,0);assert.equal(x.store.get(KEY),raw);
 assert.deepEqual(x.ctx._curUser.user_metadata,{});
});
test('account switch while the client loads never recasts A as B',async()=>{
 const x=setup();let release;x.state.client=()=>new Promise(r=>release=r);
 x.ctx._sdDesk={market_focus:['us'],trade_types:['options']};x.ctx._sdSaveDesk({});x.timers.shift()();await tick();
 x.setUser('account-b');release(x.client);await tick();assert.equal(x.writes.length,0);assert.equal(x.messages.length,0);assert.deepEqual(x.ctx._curUser.user_metadata,{});
});
test('account switch during an update prevents stale acknowledgement and status writes',async()=>{
 const raw=owned(),x=setup(current,raw);let release;x.state.update=()=>new Promise(r=>release=r);
 const delivery=x.ctx._deliverPendingPrefs();await tick();x.setUser('account-b');release({error:null});
 assert.equal((await delivery).status,'held');assert.equal(x.store.get(KEY),raw);assert.equal(x.writes[0].subject,'account-a');
});
for(const success of [true,false])test('stale '+(success?'success':'failure')+' cannot clear or rewrite a newer choice',async()=>{
 const x=setup(current,owned());let release;x.state.update=()=>new Promise(r=>release=r);
 const delivery=x.ctx._deliverPendingPrefs();await tick();assert.equal(x.ctx._queuePendingPrefs({market_focus:['hk']},'account-a'),true);
 const newer=x.store.get(KEY);release(success?{error:null}:{error:{message:'offline'}});
 assert.equal((await delivery).status,'held');assert.equal(x.store.get(KEY),newer);
});
test('malformed owned arrays and unknown authority fields never become user metadata',async()=>{
 for(const value of [[],[{}],[{prefs:A}],[{prefs:A,owner_user_id:null}],[{prefs:A,owner_user_id:'account-a'},{}]]){
  const raw=JSON.stringify(value),x=setup(current,raw);await x.ctx._deliverPendingPrefs();assert.equal(x.writes.length,0);assert.equal(x.store.get(KEY),raw);
 }
 const x=setup();x.ctx._queuePendingPrefs({...A,tier:'pro',access_token:'synthetic',role:'admin'},'account-a');await x.ctx._deliverPendingPrefs();
 assert.equal(x.writes.length,1);for(const k of ['tier','access_token','role','owner_user_id'])assert.equal(k in x.writes[0].data,false);
});
test('concurrent auth triggers share one delivery, and a later real trigger retries failure',async()=>{
 const x=setup(current,owned());x.state.response={error:{message:'offline'}};
 await Promise.all([x.ctx._deliverPendingPrefs(),x.ctx._deliverPendingPrefs()]);assert.equal(x.writes.length,1);assert.ok(x.store.has(KEY));
 x.state.response={error:null};await x.ctx._deliverPendingPrefs();assert.equal(x.writes.length,2);assert.equal(x.store.has(KEY),false);
});

test('captured Macro actor retains choices before client and identity lookup failure',async()=>{
 for(const failure of ['client','error','null','reject']){
  const x=setup(),save=actualOnboard(x);
  if(failure==='client')x.ctx.sbClient=()=>Promise.reject(Error('synthetic client unavailable'));
  else x.state.lookup=async()=>{if(failure==='reject')throw Error('synthetic offline');return {data:{user:null},error:failure==='error'?{message:'synthetic offline'}:null};};
  await save();const record=JSON.parse(x.store.get(KEY))[0];
  assert.equal(record.owner_user_id,'account-a');assert.deepEqual(record.prefs.market_focus,['us']);
  assert.equal(x.writes.length,0);assert.equal(x.ctx.S.prefsPending,true);
 }
});
test('canonical Auto survives pending failure and the later successful retry',async()=>{
 const x=setup(),save=actualOnboard(x);x.ctx._curUser.user_metadata.theme_pref='dark';
 x.ctx.S.prefs={...A,theme_pref:'auto'};x.state.response={error:{message:'synthetic offline'}};
 await save();assert.equal(JSON.parse(x.store.get(KEY))[0].prefs.theme_pref,'auto');
 x.state.response={error:null};await x.ctx._deliverPendingPrefs();assert.equal(x.writes.at(-1).data.theme_pref,'auto');
});
test('queue decodes and compares the same storage snapshot during an interleaved account write',()=>{
 const rawA=owned(),rawB=owned({market_focus:['hk'],trade_types:['stocks']},'account-b'),x=setup(current,rawA);
 const get=x.ctx.localStorage.getItem;let first=true;
 x.ctx.localStorage.getItem=k=>{const value=get(k);if(first&&k===KEY){first=false;x.store.set(KEY,rawB);}return value;};
 assert.equal(x.ctx._queuePendingPrefs({trade_types:['crypto']},'account-a'),false);
 assert.equal(x.store.get(KEY),rawB);
});
