'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'../..');
const script=n=>fs.readFileSync(path.join(root,'templates',n),'utf8');
const tick=()=>new Promise(r=>setImmediate(r));
function setup(query, capsule) {
 const ids=['mm-macro-state','mm-macro-query','mm-macro-episodes','mm-macro-note','mm-symbol-form','mm-symbol-input','mm-symbol-summary','mm-grid-list'];
 const elements=Object.fromEntries(ids.map(id=>[id,{innerHTML:'',textContent:'',value:'',events:{},addEventListener(t,f){this.events[t]=f;}}]));
 const events={},windowEvents={},pending=[],stored={market_memory_ticker:'AAPL'};
 let lang='en',authChanged,opened=0;
 const location=new URL('https://mastermind-x.com/market_memory.html'+query);
 const history={state:{},replaceState(_a,_b,url){location.href=new URL(url,location).href;}};
 const document={readyState:'complete',documentElement:{getAttribute:()=>lang},getElementById:id=>elements[id],addEventListener(t,f){events[t]=f;}};
 const saved=capsule||{};
 const sessionStorage={getItem:k=>saved[k]||null,setItem:(k,v)=>{saved[k]=v;},removeItem:k=>{delete saved[k];}};
 const window={location,history,sessionStorage,addEventListener(t,f){windowEvents[t]=f;},setLang(v){lang=v;},MDXAuth:{onChange(f){authChanged=f;},open(){opened++;}}};
 const context={window,document,location,history,URL,URLSearchParams,console,localStorage:{getItem:k=>stored[k],setItem(k,v){stored[k]=v;}},fetch:url=>new Promise(resolve=>pending.push({url,resolve}))};
 vm.createContext(context);vm.runInContext(script('market_memory_intent.js'),context);vm.runInContext(script('market_memory.js'),context);
 return {elements,events,pending,stored,window,location,saved,auth:u=>authChanged(u),get opened(){return opened;},setLang(v){lang=v;events.langchange();},submit(raw){elements['mm-symbol-input'].value=raw;elements['mm-symbol-form'].events.submit({preventDefault(){}});}};
}
for (const raw of ['', 'a/b', 'A APL']) test('explicit latest invalid input survives login destination: '+JSON.stringify(raw),async()=>{
 const x=setup('?ticker=AAPL&mm_issuer_input='+encodeURIComponent(raw)+'&mm_lang=zh');await tick();
 assert.equal(x.pending.some(p=>p.url.includes('/symbol/')),false);
 assert.equal(x.elements['mm-symbol-input'].value,raw);
 assert.match(x.elements['mm-symbol-summary'].innerHTML,/请检查代码/);
 const ret=new URL(x.location.searchParams.get('ret'),x.location);
 assert.equal(ret.pathname,'/market_memory.html');assert.equal(ret.searchParams.get('mm_issuer_input'),raw);
 assert.equal(ret.searchParams.get('mm_lang'),'zh');assert.equal(ret.searchParams.get('ticker'),'AAPL');
 x.auth({id:'fixture'});await tick();assert.equal(x.pending.some(p=>p.url.includes('/symbol/')),false);
});
test('new valid intent preserves exact raw marker and canonical ticker through 401 and retry',async()=>{
 const x=setup('?ticker=AAPL');await tick();x.submit(' nvda ');await tick();
 const item=x.pending.find(p=>p.url.endsWith('/symbol/NVDA'));assert.ok(item);
 item.resolve({ok:false,status:401,json:()=>Promise.resolve({})});await tick();
 const ret=new URL(x.location.searchParams.get('ret'),x.location);
 assert.equal(ret.searchParams.get('ticker'),'NVDA');assert.equal(ret.searchParams.get('mm_issuer_input'),' nvda ');
 assert.match(x.elements['mm-symbol-summary'].innerHTML,/ret=/);
 x.auth({id:'fixture'});await tick();assert.equal(x.pending.filter(p=>p.url.endsWith('/symbol/NVDA')).length,2);
 assert.equal(x.location.searchParams.get('mm_issuer_input'),' nvda ');
});
test('retained reference survives issuer and language changes without recursive ret',async()=>{
 const x=setup('?mm_mode=historical&mm_query=mmquery_exact&mm_context=mmctx_exact&mm_gen=mmgeneration_exact&mm_gen_sha='+'a'.repeat(64)+'&mm_catalog_offset=40');await tick();
 x.submit('');x.setLang('zh');
 const ret=new URL(x.location.searchParams.get('ret'),x.location);
 assert.equal(ret.searchParams.get('mm_context'),'mmctx_exact');assert.equal(ret.searchParams.get('mm_catalog_offset'),'40');
 assert.equal(ret.searchParams.get('mm_issuer_input'),'');assert.equal(ret.searchParams.get('mm_lang'),'zh');assert.equal(ret.searchParams.has('ret'),false);
});
test('oversized intent clears stale ret and refuses old-symbol retry',async()=>{
 const x=setup('?ticker=AAPL');await tick();const n=x.pending.length;x.submit('x'.repeat(2049));await tick();
 assert.equal(x.pending.length,n);assert.equal(x.location.searchParams.has('ret'),false);
 assert.match(x.elements['mm-symbol-summary'].innerHTML,/Cannot preserve this link/);
 x.auth({id:'fixture'});await tick();assert.equal(x.pending.length,n);
});

test('missing OAuth capsule stops both implicit AAPL and initial private reads',async()=>{const x=setup('?onboard=resume');await tick();assert.equal(x.pending.length,0);assert.match(x.elements['mm-symbol-summary'].innerHTML,/Selection unavailable after sign-in/);});
test('OAuth callback restores invalid issuer before legacy fetch or default fallback',async()=>{const before=setup('?ticker=AAPL&mm_issuer_input=a%2Fb&mm_lang=zh');await tick();const x=setup('?onboard=resume&code=synthetic',before.saved);await tick();assert.equal(x.pending.some(p=>p.url.includes('/symbol/')),false);assert.equal(x.elements['mm-symbol-input'].value,'a/b');assert.equal(x.location.searchParams.get('code'),'synthetic');assert.match(x.elements['mm-symbol-summary'].innerHTML,/请检查代码/);});

function onboardReturnHarness(query) {
 const src=script('onboard.js');
 const helpers=src.slice(src.indexOf('  function oauthRedirect()'),src.indexOf('  // ── Silent wall-resume'));
 const google=src.slice(src.indexOf('  function onGoogle()'),src.indexOf('  // ══════════════════════ PASSWORD RECOVERY'));
 const loc=new URL('https://macro.example/'+query),opens=[],calls=[],stored={};let resolveSession;
 const auth={signInWithOAuth:o=>{calls.push(o);return Promise.resolve({});},getSession:()=>new Promise(resolve=>{resolveSession=resolve;})};
 const nav={get href(){return loc.href;},set href(value){loc.href=new URL(value,loc.href).href;},get origin(){return loc.origin;},get pathname(){return loc.pathname;},get search(){return loc.search;}};
 const ctx={URL,location:nav,retTarget:()=>loc.searchParams.get('ret')||'',loginDest:()=>loc.searchParams.get('ret')||'/start.html',sbClient:()=>Promise.resolve({auth}),openSheet:(...a)=>opens.push(a),showErr:()=>{},tx:x=>x,stashSave:()=>{},localStorage:{setItem:(k,v)=>stored[k]=v},LS_ONBOARD_RESUME:'fixture-wizard',STEP_PREFS:2,S:{mode:'signin'}};
 vm.createContext(ctx);vm.runInContext(helpers+google,ctx);return {ctx,loc,opens,calls,stored,settle:r=>resolveSession(r)};
}
test('actual Google launcher preserves a same-origin exact Market Memory fallback target',async()=>{const target='/market_memory.html?mm_mode=saved&mm_context=exact&mm_lang=zh';const x=onboardReturnHarness('?signin=1&ret='+encodeURIComponent(target));x.ctx.onGoogle();await tick();assert.equal(x.calls.length,1);const ret=new URL(x.calls[0].options.redirectTo);assert.equal(ret.pathname,'/');assert.equal(ret.searchParams.get('onboard'),'resume');assert.equal(ret.searchParams.get('ret'),target);assert.equal(JSON.parse(x.stored['fixture-wizard']).mode,'signin');});
test('Google launcher does not propagate an off-origin return target',async()=>{const x=onboardReturnHarness('?ret='+encodeURIComponent('https://other.invalid/'));x.ctx.onGoogle();await tick();assert.equal(new URL(x.calls[0].options.redirectTo).searchParams.has('ret'),false);});
test('signin resume waits for incumbent session exchange before leaving the callback',async()=>{const target='/market_memory.html?mm_context=exact';const x=onboardReturnHarness('?onboard=resume&code=synthetic&ret='+encodeURIComponent(target));const old=x.loc.href;const p=x.ctx.resumeSignin();await tick();assert.equal(x.loc.href,old);x.settle({data:{session:{user:{id:'fixture'}}}});await p;assert.equal(x.loc.pathname,'/market_memory.html');assert.equal(x.loc.searchParams.get('mm_context'),'exact');assert.equal(x.loc.searchParams.has('code'),false);assert.equal(x.opens.length,0);});
for(const response of [{data:{session:null}},{error:{message:'synthetic failure'},data:{session:{}}}])test('failed provider exchange keeps the callback and exposes signin recovery',async()=>{const x=onboardReturnHarness('?onboard=resume&code=synthetic');const old=x.loc.href;const p=x.ctx.resumeSignin();await tick();x.settle(response);await p;assert.equal(x.loc.href,old);assert.equal(x.opens.length,1);assert.equal(x.opens[0][0],'signin');});

function lazyFallbackHarness(query) {
 const src=script('theme.js'),code=src.slice(src.indexOf('  function _mmOpenOnboard('),src.indexOf('  function _sdWireCta('));
 const loc=new URL('https://macro.example/market_memory.html'+query),timers=[],scripts=[];
 const nav={get href(){return loc.href;},set href(value){loc.href=new URL(value,loc.href).href;},get origin(){return loc.origin;},get pathname(){return loc.pathname;},get search(){return loc.search;}};
 const ctx={URL,location:nav,window:{},_mmSharedAssetRoot:'/',setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout:()=>{},document:{createElement:()=>({}),head:{appendChild:s=>scripts.push(s)}}};
 vm.createContext(ctx);vm.runInContext(code,ctx);ctx._mmOpenOnboard('signin');return {loc,timers,scripts};
}
for(const edge of ['error','timeout'])test('shared lazy signin '+edge+' preserves exact Market Memory fallback intent',()=>{
 const target='/market_memory.html?mm_mode=saved&mm_query=exact&mm_issuer_input=&mm_lang=zh';
 const x=lazyFallbackHarness('?ret='+encodeURIComponent(target));
 if(edge==='error')x.scripts[0].onerror();else x.timers[0]();
 assert.equal(x.loc.pathname,'/index.html');assert.equal(x.loc.searchParams.get('signin'),'1');assert.equal(x.loc.searchParams.get('ret'),target);
});
for(const query of ['?ret='+encodeURIComponent('https://other.invalid/'),'?ret=%2Fone&ret=%2Ftwo'])test('shared signin fallback refuses ambiguous or off-origin target: '+query,()=>{
 const x=lazyFallbackHarness(query);x.scripts[0].onerror();assert.equal(x.loc.pathname,'/index.html');assert.equal(x.loc.searchParams.has('ret'),false);
});
