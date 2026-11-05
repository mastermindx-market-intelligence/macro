import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync(process.env.WATCHSTORE_SOURCE || new URL('../templates/watchstore.js', import.meta.url),'utf8');
if (!process.env.WATCHSTORE_HARNESS) throw new Error('Run through the registered pytest wrapper to reuse its harness.');
const harness=JSON.parse(readFileSync(process.env.WATCHSTORE_HARNESS,'utf8'));
const plain=x=>JSON.parse(JSON.stringify(x));
function boot(){
 const c=vm.createContext({setTimeout,clearTimeout,console,module:{exports:{}}});
 vm.runInContext('global=globalThis;'+harness.SHIM+harness.FAKE_DB+source,c);
 const db=c.makeDb({watchlists:[{id:'a',user_id:'A',name:'Daily review'},{id:'b',user_id:'A',name:'AI research'},{id:'foreign',user_id:'B',name:'Private B'}],watchlist_symbols:[{watchlist_id:'a',symbol:'NVDA',position:0}],portfolio_positions:[{id:'p',user_id:'A',ticker:'AMD',shares:2}]});
 const ws=c.module.exports;ws._setTestSession({id:'A'},db.client);ws._setTestLists({lists:db.tables.watchlists.filter(x=>x.user_id==='A'),activeId:'a',cloud:{}});
 const events=[];c.document.addEventListener('ws-save',e=>events.push(e.detail.state));
 return {c,db,ws,events};
}
async function inspect(e,list='a',symbol='NVDA'){
 assert.equal(typeof e.ws.symbols.inspect,'function','the exact-membership reader is not implemented');
 return plain(await e.ws.symbols.inspect(list,symbol));
}
function holdNext(db,table){
 let release,start;const gate=new Promise(r=>release=r),seen=new Promise(r=>start=r);const from=db.client.from;let used=false;
 db.client.from=function(t){const q=from(t),run=q.__run;let result;q.__run=function(){if(result)return result;if(t!==table||used)return run();used=true;result=run().then(v=>{start();return gate.then(()=>v);});return result;};return q;};
 return {release,seen};
}
test('public symbols namespace exposes explicit membership observation',()=>{assert.equal(typeof boot().ws.symbols.inspect,'function');});
test('present means observed membership, not a claimed insertion',async()=>{const e=boot(),r=await inspect(e);assert.equal(r.state,'present');assert.equal(r.membership,'present');assert.equal(r.listName,'Daily review');assert.equal(r.listId,'a');assert.equal(r.symbol,'NVDA');assert.equal(r.inserted,undefined);assert.ok(Number.isFinite(Date.parse(r.observedAt)));});
test('absent is not-confirmed, never a retry authorization',async()=>{const r=await inspect(boot(),'b');assert.equal(r.state,'not-confirmed');assert.equal(r.membership,'absent');assert.equal(r.writeRetryAllowed,false);});
test('checking membership performs only two exact-scope selects',async()=>{
 const e=boot();await inspect(e);assert.equal(e.db.ops.length,2);assert.ok(e.db.ops.every(x=>x.kind==='select'));
 assert.deepEqual(plain(e.db.ops[0].filters),[{op:'eq',col:'id',val:'a'},{op:'eq',col:'user_id',val:'A'}]);
 assert.deepEqual(plain(e.db.ops[1].filters),[{op:'eq',col:'watchlist_id',val:'a'},{op:'eq',col:'symbol',val:'NVDA'}]);
});
test('does not switch the active list, mutate caches, or change holdings',async()=>{
 const e=boot();e.c.localStorage.setItem('mdash.wl.b.v1',JSON.stringify({v:1,items:[],pendingInserts:{b:{NVDA:'old'}}}));
 const storage=JSON.stringify(e.c.__store),state=plain(e.ws._testState()),book=plain(e.db.tables.portfolio_positions);
 await inspect(e,'b');assert.equal(JSON.stringify(e.c.__store),storage);assert.deepEqual(plain(e.ws._testState()),state);assert.deepEqual(plain(e.db.tables.portfolio_positions),book);assert.deepEqual(e.events,[]);
});
test('foreign list is unavailable without reading its symbols or disclosing its name',async()=>{
 const e=boot(),r=await inspect(e,'foreign');assert.equal(r.state,'unavailable');assert.equal(r.membership,'unknown');assert.equal(r.listName,null);assert.equal(e.db.ops.length,1);
});
test('removed list is unavailable, not an empty usable destination',async()=>{const e=boot(),r=await inspect(e,'removed');assert.equal(r.state,'unavailable');assert.equal(r.membership,'unknown');assert.equal(e.db.ops.length,1);});
test('no-session performs no provider call and does not silently use local storage',async()=>{const e=boot();e.ws._setTestSession(null,null);const r=await inspect(e);assert.equal(r.state,'no-session');assert.equal(r.listName,null);assert.equal(e.db.ops.length,0);});
for(const [list,symbol] of [['','NVDA'],['a',''],[null,'NVDA'],['a',{}],[{},'NVDA'],['a',123]]){
 test('invalid input is refused before provider use '+JSON.stringify([list,symbol]),async()=>{const e=boot(),r=await inspect(e,list,symbol);assert.equal(r.state,'invalid');assert.equal(e.db.ops.length,0);});
}
test('sign-out before the first continuation prevents provider dispatch',async()=>{
 const e=boot();assert.equal(typeof e.ws.symbols.inspect,'function');const p=e.ws.symbols.inspect('a','NVDA');e.ws.onAuthUser(null);const r=plain(await p);assert.equal(r.state,'stale-session');assert.equal(e.db.ops.length,0);assert.equal(r.listName,null);
});
test('late ownership result is discarded after account change',async()=>{
 const e=boot(),h=holdNext(e.db,'watchlists');const p=inspect(e);await h.seen;e.ws.onAuthUser(null);h.release();const r=await p;assert.equal(r.state,'stale-session');assert.equal(r.listName,null);assert.equal(r.listId,null);assert.equal(e.db.ops.length,1);
});
test('late membership result is discarded after account change',async()=>{
 const e=boot(),h=holdNext(e.db,'watchlist_symbols');const p=inspect(e);await h.seen;e.ws.onAuthUser(null);const signOutEvents=e.events.slice();h.release();const r=await p;assert.equal(r.state,'stale-session');assert.equal(r.listName,null);assert.equal(r.observedAt,null);assert.deepEqual(signOutEvents,['local']);assert.deepEqual(e.events,signOutEvents);
});
function overrideRead(e,table,resolve){const from=e.db.client.from;e.db.client.from=function(t){const q=from(t),run=q.__run;q.__run=function(){return t===table?resolve():run();};return q;};}
test('ownership read failure is unavailable and reveals no list name',async()=>{const e=boot();overrideRead(e,'watchlists',()=>Promise.reject(new Error('secret SQL detail')));const r=await inspect(e);assert.equal(r.state,'unavailable');assert.equal(r.listName,null);assert.equal(JSON.stringify(r).includes('secret'),false);});
test('membership read failure is unavailable, not absent',async()=>{const e=boot();overrideRead(e,'watchlist_symbols',()=>Promise.resolve({data:null,error:{code:'42501'}}));const r=await inspect(e);assert.equal(r.state,'unavailable');assert.equal(r.membership,'unknown');assert.equal(r.writeRetryAllowed,false);});
test('wrong list in the returned membership is rejected',async()=>{const e=boot();overrideRead(e,'watchlist_symbols',()=>Promise.resolve({data:[{watchlist_id:'foreign',symbol:'NVDA'}],error:null}));assert.equal((await inspect(e)).state,'unavailable');});
test('wrong symbol in the returned membership is rejected',async()=>{const e=boot();overrideRead(e,'watchlist_symbols',()=>Promise.resolve({data:[{watchlist_id:'a',symbol:'AMD'}],error:null}));assert.equal((await inspect(e)).state,'unavailable');});
test('null membership response is not converted to empty',async()=>{const e=boot();overrideRead(e,'watchlist_symbols',()=>Promise.resolve({data:null,error:null}));assert.equal((await inspect(e)).membership,'unknown');});
test('malformed ownership response is rejected before symbol lookup',async()=>{const e=boot();overrideRead(e,'watchlists',()=>Promise.resolve({data:[{id:'a',user_id:'B',name:'Private B'}],error:null}));const r=await inspect(e);assert.equal(r.state,'unavailable');assert.equal(r.listName,null);assert.equal(e.db.ops.length,1);});
test('same account returning cannot adopt an earlier observation',async()=>{const e=boot(),h=holdNext(e.db,'watchlists');const p=inspect(e);await h.seen;e.ws.onAuthUser(null);e.ws._setTestSession({id:'A'},e.db.client);h.release();assert.equal((await p).state,'stale-session');});
test('parallel inspections retain their own destination names',async()=>{const e=boot(),[a,b]=await Promise.all([inspect(e,'a'),inspect(e,'b')]);assert.equal(a.listName,'Daily review');assert.equal(b.listName,'AI research');assert.equal(e.ws.lists.activeId(),'a');});
test('symbol identity is not uppercased or remapped',async()=>{const e=boot();await inspect(e,'a','brk.b');assert.equal(e.db.ops[1].filters[1].val,'brk.b');});
test('read deadline reaches a terminal unavailable result without provider writes',async()=>{
 const e=boot();e.ws._setCloudDeadlineMs(5);overrideRead(e,'watchlists',()=>new Promise(()=>{}));
 const r=await Promise.race([inspect(e),new Promise(resolve=>setTimeout(()=>resolve({state:'test-timeout'}),60))]);
 assert.equal(r.state,'unavailable');assert.ok(e.db.ops.every(x=>x.kind==='select'));
});
test('timed-out ownership response cannot start a later membership query',async()=>{
 const e=boot();e.ws._setCloudDeadlineMs(5);const h=holdNext(e.db,'watchlists'),p=inspect(e);await h.seen;const r=await p;assert.equal(r.state,'unavailable');h.release();await new Promise(resolve=>setTimeout(resolve,2));assert.equal(e.db.ops.length,1);
});
test('timed-out membership response does not update any cache or emit status',async()=>{
 const e=boot();e.ws._setCloudDeadlineMs(5);const h=holdNext(e.db,'watchlist_symbols'),p=inspect(e);await h.seen;const before=plain(e.ws._testState());assert.equal((await p).state,'unavailable');h.release();await new Promise(resolve=>setTimeout(resolve,2));assert.deepEqual(plain(e.ws._testState()),before);assert.deepEqual(e.events,[]);
});
test('replaced client cannot finish an observation under the same user ID',async()=>{
 const e=boot(),h=holdNext(e.db,'watchlists'),p=inspect(e);await h.seen;e.ws._setTestSession({id:'A'},{from(){throw new Error('must not be used');}});h.release();assert.equal((await p).state,'stale-session');assert.equal(e.db.ops.length,1);
});
test('observed presence does not clear the original pending save marker',async()=>{
 const e=boot();e.c.localStorage.setItem('mdash.wl.a.v1',JSON.stringify({v:1,items:[],pendingInserts:{a:{NVDA:'original'}}}));const before=JSON.stringify(e.c.__store);const r=await inspect(e);assert.equal(r.state,'present');assert.equal(JSON.stringify(e.c.__store),before);assert.deepEqual(e.events,[]);
});
test('no private provider error fields are exposed in the observation',async()=>{
 const e=boot();overrideRead(e,'watchlist_symbols',()=>Promise.reject({message:'sensitive detail',user_id:'B',name:'Private B',sql:'private'}));const r=await inspect(e);assert.equal(r.state,'unavailable');assert.equal(JSON.stringify(r).includes('Private B'),false);assert.equal(r.error,undefined);
});
test('input whitespace is trimmed but original symbol syntax is retained',async()=>{const e=boot(),r=await inspect(e,' a ',' BRK.B ');assert.equal(r.listId,'a');assert.equal(r.symbol,'BRK.B');assert.equal(r.state,'not-confirmed');});
test('rechecking a read is distinct from repeating a write',async()=>{
 const r=await inspect(boot(),'b');assert.equal(r.readRetryAllowed,true);assert.equal(r.writeRetryAllowed,false);assert.equal(r.retryable,undefined);
});
test('an unavailable read offers a read-only recheck',async()=>{
 const e=boot();overrideRead(e,'watchlist_symbols',()=>Promise.resolve({data:null,error:{code:'unavailable'}}));const r=await inspect(e);assert.equal(r.readRetryAllowed,true);assert.equal(r.writeRetryAllowed,false);
});
test('stale session requires new context rather than rechecking old identifiers',async()=>{
 const e=boot(),h=holdNext(e.db,'watchlists'),p=inspect(e);await h.seen;e.ws.onAuthUser(null);h.release();const r=await p;assert.equal(r.readRetryAllowed,false);assert.equal(r.writeRetryAllowed,false);
});
