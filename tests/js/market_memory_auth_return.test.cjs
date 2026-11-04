'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'../..');
const script=n=>fs.readFileSync(path.join(root,'templates',n),'utf8');
const tick=()=>new Promise(r=>setImmediate(r));
// The isolated entry points retain their real lexical shell dependencies.
// Loading the production helpers also exercises candidate ownership instead
// of assuming that every return/auth test runs outside the Shared Shell.
function sharedShellHelpers(owner) {
 const src=script(owner+'.js');
 const start=owner==='theme'?'  function _mmShellBridge(':'  function _mmShellPresent(';
 const end=owner==='theme'?'  function curTheme(':'  function _acctKey(';
 const from=src.indexOf(start),to=src.indexOf(end,from);
 assert.ok(from>=0&&to>from,owner+' shell helper source boundaries must exist');
 return src.slice(from,to);
}
function setup(query, capsule, legacy) {
 const ids=['mm-macro-state','mm-macro-query','mm-macro-episodes','mm-macro-note','mm-symbol-form','mm-symbol-input','mm-symbol-summary','mm-grid-list'];
 const elements=Object.fromEntries(ids.map(id=>[id,{innerHTML:'',textContent:'',value:'',events:{},addEventListener(t,f){this.events[t]=f;}}]));
 if(legacy)elements['mmr-legacy']=legacy;
 const events={},windowEvents={},pending=[],stored={market_memory_ticker:'AAPL'};
 let lang='en',authChanged,opened=0,capsuleWrites=0;
 const location=new URL('https://mastermind-x.com/market_memory.html'+query);
 const history={state:{},replaceState(_a,_b,url){location.href=new URL(url,location).href;}};
 const document={readyState:'complete',documentElement:{getAttribute:()=>lang},getElementById:id=>elements[id],addEventListener(t,f){events[t]=f;}};
 const saved=capsule||{};
 const sessionStorage={getItem:k=>saved[k]||null,setItem:(k,v)=>{capsuleWrites++;saved[k]=v;},removeItem:k=>{delete saved[k];}};
 const window={location,history,sessionStorage,addEventListener(t,f){(windowEvents[t]||(windowEvents[t]=[])).push(f);},setLang(v){lang=v;},MDXAuth:{onChange(f){authChanged=f;},open(){opened++;}}};
 const context={window,document,location,history,URL,URLSearchParams,console,localStorage:{getItem:k=>stored[k],setItem(k,v){stored[k]=v;}},fetch:url=>new Promise(resolve=>pending.push({url,resolve}))};
 vm.createContext(context);vm.runInContext(script('market_memory_intent.js'),context);vm.runInContext(script('market_memory.js'),context);
 return {elements,events,pending,stored,window,location,saved,auth:u=>authChanged(u),get lang(){return lang;},get opened(){return opened;},get capsuleWrites(){return capsuleWrites;},setLang(v){lang=v;events.langchange();},navigate(query){location.href=new URL(query,location).href;(windowEvents.popstate||[]).forEach(f=>f());},submit(raw){elements['mm-symbol-input'].value=raw;elements['mm-symbol-form'].events.submit({preventDefault(){}});}};
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

function lazyFallbackHarness(query, bridge) {
 const src=script('theme.js'),code=src.slice(src.indexOf('  function _mmOpenOnboard('),src.indexOf('  function _sdWireCta('));
 const loc=new URL('https://macro.example/market_memory.html'+query),timers=[],scripts=[];
 const nav={get href(){return loc.href;},set href(value){loc.href=new URL(value,loc.href).href;},get origin(){return loc.origin;},get pathname(){return loc.pathname;},get search(){return loc.search;}};
 const ctx={URL,location:nav,window:{MMXSharedShell:bridge},_mmSharedAssetRoot:'/',setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout:()=>{},document:{createElement:()=>({}),head:{appendChild:s=>scripts.push(s)}}};
 vm.createContext(ctx);vm.runInContext(sharedShellHelpers('theme')+code,ctx);ctx._mmOpenOnboard('signin');return {loc,timers,scripts};
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
for(const outcome of [true,false,'throw'])test('shell auth candidate owns the handoff without a legacy fallback: '+outcome,()=>{
 const calls=[],bridge={openAuth(intent){calls.push(intent);if(outcome==='throw')throw new Error('synthetic refusal');return outcome;}};
 const query='?ret='+encodeURIComponent('/market_memory.html?mm_context=exact&mm_lang=zh');
 const x=lazyFallbackHarness(query,bridge);
 assert.deepEqual(calls,['signin']);assert.equal(x.scripts.length,0);assert.equal(x.timers.length,0);
 assert.equal(x.loc.href,'https://macro.example/market_memory.html'+query);
});


// Real 2026-10-14 Google return regression: global Settings bypassed the
// retained panel's sign-in handler while its catalogue request was pending.
function settingsEntryHarness(query, ready) {
 const live=new URL('https://macro.example/market_memory.html'+query),saved={},opens=[],scripts=[],timers=[];
 const location={get href(){return live.href;},set href(value){live.href=new URL(value,live.href).href;},get origin(){return live.origin;},get pathname(){return live.pathname;},get search(){return live.search;},get searchParams(){return live.searchParams;}};
 const window={location,history:{state:null,replaceState(_s,_u,target){location.href=new URL(target,location.origin).href;}},
  sessionStorage:{getItem:k=>saved[k]||null,setItem:(k,v)=>{saved[k]=v;},removeItem:k=>{delete saved[k];}}};
 const ctx={window,location,URL,URLSearchParams,_mmSharedAssetRoot:'/',setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout:()=>{},
  document:{createElement:()=>({}),head:{appendChild:s=>scripts.push(s)}}};
 vm.createContext(ctx);vm.runInContext(script('market_memory_intent.js'),ctx);
 // Preserve an older ordinary SPY intent, then navigate to the exact source.
 const incoming=location.href;location.href='https://macro.example/market_memory.html?ticker=SPY';window.MarketMemoryIntent.syncReturn();location.href=incoming;
 if(ready)window.MMOnboard={open:mode=>opens.push(mode)};
 const theme=script('theme.js');vm.runInContext(sharedShellHelpers('theme')+theme.slice(theme.indexOf('  function _mmOpenOnboard('),theme.indexOf('  function _sdWireCta(')),ctx);
 const expected=window.MarketMemoryIntent.target();ctx._mmOpenOnboard('signin');
 return {ctx,window,location,saved,opens,scripts,timers,expected};
}
const exactSettingsQuery='?ticker=SPY&mm_mode=saved&mm_query=exact-query&mm_subject=exact-subject&mm_gen=exact-generation&mm_gen_sha='+('a'.repeat(64))+'&mm_cutoff=2026-10-13T09%3A17%3A41.967527Z&mm_context=exact-context&mm_source_field=growth_score&mm_source_context=exact-context';
for(const ready of [false,true])test('global Settings sign-in preserves the current exact source before '+(ready?'opening an existing sheet':'lazy loading the sheet'),()=>{
 const x=settingsEntryHarness(exactSettingsQuery,ready);assert.equal(x.expected.ok,true);
 assert.equal(x.location.searchParams.get('ret'),x.expected.target);
 const capsule=Object.values(x.saved).map(v=>JSON.parse(v)).find(v=>v.schema==='market_memory.intent.oauth.v1');
 assert.equal(capsule.target,x.expected.target);assert.equal(ready?x.opens.length:x.scripts.length,1);
 const callback={...x.ctx,window:{...x.window,location:new URL('https://macro.example/market_memory.html?onboard=resume&code=synthetic')}};
 callback.window.history={state:null,replaceState(_s,_u,target){callback.window.location.href=new URL(target,callback.window.location.origin).href;}};
 vm.createContext(callback);vm.runInContext(script('market_memory_intent.js'),callback);
 assert.equal(callback.window.MarketMemoryIntent.resumeStatus().restored,true);
 for(const [key,value] of new URL(x.expected.target,x.location.origin).searchParams)assert.equal(callback.window.location.searchParams.get(key),value);
});
for(const edge of ['error','timeout'])test('Settings lazy '+edge+' fallback retains an exact source even without an incoming ret',()=>{
 const x=settingsEntryHarness(exactSettingsQuery,false);if(edge==='error')x.scripts[0].onerror();else x.timers[0]();
 assert.equal(x.location.pathname,'/index.html');assert.equal(x.location.searchParams.get('ret'),x.expected.target);
});
test('Settings cannot reuse an older capsule when the current source is ambiguous',()=>{
 const x=settingsEntryHarness('?mm_query=first&mm_query=second',true);assert.equal(x.expected.ok,false);
 assert.equal(Object.keys(x.saved).length,0);assert.equal(x.opens.length,0);
});


// Actual Chinese sign-out -> English left the expanded legacy panels in Chinese.
// Exercise the complete client with its real intent/capsule codec.
function replyLegacy(item, status, payload={}) {
 item.resolve({ok:status===200,status,json:()=>Promise.resolve(payload)});
}
function assertLegacySigninTarget(x, language) {
 for(const id of ['mm-macro-query','mm-symbol-summary']) {
  const href=x.elements[id].innerHTML.match(/href="([^"]+)"/)[1].replaceAll('&amp;','&');
  const ret=new URL(new URL(href,x.location).searchParams.get('ret'),x.location);
  for(const key of ['mm_mode','mm_query','mm_context','mm_gen','mm_gen_sha','mm_source_field','mm_source_context','mm_issuer_input']) {
   assert.equal(ret.searchParams.get(key),x.location.searchParams.get(key),key);
  }
  assert.equal(ret.searchParams.get('mm_lang'),language);
 }
}
const legacyLocaleQuery='?ticker=SPY&mm_issuer_input=spy&mm_mode=historical&mm_query=query-exact&mm_context=context-exact&mm_gen=generation-exact&mm_gen_sha='+('b'.repeat(64))+'&mm_source_field=growth_score&mm_source_context=context-exact&mm_lang=zh';
test('legacy sign-out notices translate both ways without reads, private revival, or extra capsule writes',async()=>{
 const x=setup(legacyLocaleQuery);await tick();
 const before=x.pending.length;x.auth(null);
 for(const language of ['en','zh','en']) {
  const writes=x.capsuleWrites;x.setLang(language);await tick();
  assert.equal(x.pending.length,before);
  assert.equal(x.capsuleWrites-writes,1,'only existing language intent sync writes');
  assert.match(x.elements['mm-macro-state'].textContent,language==='zh'?/需要登录/:/Sign in required/);
  assert.match(x.elements['mm-macro-query'].innerHTML,language==='zh'?/退出登录后/:/cleared when you sign out/);
  assert.match(x.elements['mm-macro-note'].textContent,language==='zh'?/未保留历史载荷/:/No historical payload/);
  assert.match(x.elements['mm-symbol-summary'].innerHTML,language==='zh'?/退出登录后/:/cleared when you sign out/);
  assertLegacySigninTarget(x,language);
 }
 // Pending successful responses from before sign-out must remain retired.
 for(const item of x.pending) replyLegacy(item,200,{ticker:'PRIVATE_OLD',as_of:'PRIVATE_OLD',context_note:'PRIVATE_OLD',query:{},grids:{}});
 await tick();x.setLang('zh');
 assert.equal(x.elements['mm-macro-episodes'].innerHTML,'');assert.equal(x.elements['mm-grid-list'].innerHTML,'');
 assert.equal(JSON.stringify(x.elements).includes('PRIVATE_OLD'),false);
 x.auth({id:'fixture'});await tick();assert.equal(x.pending.length,before+2,'sign-in retries only the two blocked reads');
});
for(const status of [401,402,403,404,503])test('legacy '+status+' notices redraw current language without refetch or stale payload',async()=>{
 const x=setup(legacyLocaleQuery);await tick();
 for(const item of x.pending)replyLegacy(item,status,{detail:'PRIVATE_ERROR'});
 await tick();const before=x.pending.length;
 for(const language of ['en','zh']) {
  const writes=x.capsuleWrites;x.setLang(language);await tick();
  assert.equal(x.pending.length,before);assert.equal(x.capsuleWrites-writes,1);
  assert.match(x.elements['mm-macro-state'].textContent,language==='zh'?/记忆暂不可用/:/Memory unavailable/);
  assert.match(x.elements['mm-macro-query'].innerHTML,language==='zh'?/宏观记忆暂不可用|登录以打开市场记忆/:/Macro memory unavailable|Sign in to open Market Memory/);
  assert.match(x.elements['mm-symbol-summary'].innerHTML,language==='zh'?/暂无记忆|个股记忆暂不可用|登录以打开个股记忆/:/No memory for SPY|Symbol memory unavailable|Sign in to open symbol memory/);
  assert.equal(JSON.stringify(x.elements).includes('PRIVATE_ERROR'),false);
  if(status===401)assertLegacySigninTarget(x,language);
  if(status===402||status===403)assert.match(x.elements['mm-symbol-summary'].innerHTML,language==='zh'?/查看方案/:/View plans/);
 }
 x.auth({id:'fixture'});await tick();assert.equal(x.pending.length,before+(status===401?2:0));
});
test('legacy invalid and unpreservable intent notices retain their cause through language changes',async()=>{
 const x=setup('?ticker=AAPL');await tick();
 x.submit('x'.repeat(2049));const before=x.pending.length;x.setLang('zh');
 assert.equal(x.location.searchParams.has('ret'),false,'do not restore an older valid auth target');
 assert.match(x.elements['mm-symbol-summary'].innerHTML,/无法保留此链接/);
 x.auth(null);x.setLang('en');assert.match(x.elements['mm-macro-query'].innerHTML,/href="#mm-symbol-form"/);
 assert.equal(x.location.searchParams.has('ret'),false);
 x.submit('!');x.setLang('en');assert.match(x.elements['mm-symbol-summary'].innerHTML,/Check the ticker/);
 x.auth({id:'fixture'});await tick();assert.equal(x.pending.length,before+1,'only blocked macro read retries');
 assert.equal(x.pending.filter(p=>p.url.includes('/symbol/')).length,1,'no retry of the previous issuer');
});
test('missing OAuth selection keeps its specific notice after locale changes with no private reads',async()=>{
 const x=setup('?onboard=resume');await tick();x.setLang('zh');
 assert.equal(x.pending.length,0);assert.match(x.elements['mm-symbol-summary'].innerHTML,/登录后无法恢复选择/);
});


test('macro sign-in retry renders pending in both languages until the current request settles',async()=>{
 const x=setup(legacyLocaleQuery);await tick();
 for(const item of x.pending)replyLegacy(item,401);
 await tick();x.auth({id:'fixture'});await tick();const count=x.pending.length;
 for(const language of ['en','zh']) {
  const writes=x.capsuleWrites;x.setLang(language);await tick();
  assert.equal(x.pending.length,count);assert.equal(x.capsuleWrites-writes,1);
  assert.match(x.elements['mm-macro-state'].textContent,language==='zh'?/正在加载宏观记忆/:/Loading macro memory/);
  assert.doesNotMatch(x.elements['mm-macro-query'].innerHTML,/signin|登录/);
  assert.equal(x.elements['mm-macro-note'].textContent,'');
 }
 const retry=x.pending.filter(p=>p.url.includes('/macro?')).at(-1);
 replyLegacy(retry,200,{as_of:'2026-10-14',query:{},episodes:[],context_note:'CURRENT_CONTEXT_NOTE'});
 await tick();assert.match(x.elements['mm-macro-note'].textContent,/CURRENT_CONTEXT_NOTE/);
 x.setLang('en');assert.match(x.elements['mm-macro-state'].textContent,/State through 2026-10-14/);
 x.auth(null);x.auth({id:'fixture'});await tick();
 assert.equal(x.elements['mm-macro-note'].textContent,'','retry cannot retain prior context note');
 replyLegacy(x.pending.filter(p=>p.url.includes('/macro?')).at(-1),503);await tick();
 assert.equal(x.elements['mm-macro-note'].textContent,'');
 assert.match(x.elements['mm-macro-state'].textContent,/Memory unavailable/);
});

// Run both actual preference readers against the actual page intent/client.
// Server hydration used to replace an explicit OAuth return language and rewrite ret.
function profileReader(x, owner) {
 x.window.setLang=v=>x.setLang(v);
 const docEl={getAttribute:()=>x.lang};
 const context={window:x.window,document:{documentElement:docEl},docEl,_prefSyncing:false,_hydrating:false,curTheme:()=> 'light',setTheme(){},setThemeAuto(){},setLang:v=>x.setLang(v)};
 const theme=script('theme.js'),account=script('account.js');
 const body=owner==='theme' ? theme.slice(theme.indexOf('function _sharedPref('),theme.indexOf('/* Save ONLY the atomics')) : account.slice(account.indexOf('function applyPrefs('),account.indexOf('// S1-01: theme/lang edits'));
 vm.createContext(context);vm.runInContext(sharedShellHelpers(owner)+body,context);
 return language=>owner==='theme' ? context._applyServerPrefs({user_metadata:{lang:language}}) : context.applyPrefs({authenticated:true,prefs:{lang:language}});
}
for(const owner of ['theme','account']) {
 for(const language of ['en','zh']) test(owner+' profile hydration preserves explicit OAuth language and source intent: '+language,async()=>{
  const prior=setup(legacyLocaleQuery.replace('mm_lang=zh','mm_lang='+language));await tick();
  const x=setup('?onboard=resume&code=synthetic',prior.saved);await tick();
  const apply=profileReader(x,owner),before=x.location.href,writes=x.capsuleWrites,reads=x.pending.length;
  apply(language==='en'?'zh':'en');await tick();
  assert.equal(x.lang,language);assert.equal(x.location.href,before);assert.equal(x.capsuleWrites,writes);assert.equal(x.pending.length,reads);
  const next=language==='en'?'zh':'en';
  x.navigate('?ticker=SPY&mm_issuer_input=SPY&mm_lang='+next);await tick();
  const navigation=x.location.href;apply(language);assert.equal(x.lang,next);assert.equal(x.location.href,navigation,'Back/Forward language must replace the earlier navigation preference');
 });
 test(owner+' profile default remains available without incoming language; later user choice wins',async()=>{
  const x=setup('?ticker=SPY');await tick();const apply=profileReader(x,owner);
  apply('zh');assert.equal(x.lang,'zh','initial generated URL must not suppress the account default');
  x.setLang('en');const before=x.location.href,writes=x.capsuleWrites,reads=x.pending.length;apply('zh');await tick();
  assert.equal(x.lang,'en');assert.equal(x.location.href,before);assert.equal(x.capsuleWrites,writes);assert.equal(x.pending.length,reads);
 });
 test(owner+' profile language behavior is unchanged without the page intent API',async()=>{
  const x=setup('?ticker=SPY');await tick();delete x.window.MarketMemoryIntent;const apply=profileReader(x,owner);
  apply('zh');assert.equal(x.lang,'zh');apply('en');assert.equal(x.lang,'en');
 });
 test(owner+' profile hydration defers to an existing shell candidate',async()=>{
  const x=setup('?ticker=SPY');await tick();
  x.window.MMXSharedShell={openAuth(){throw new Error('profile hydration must not request auth');}};
  const apply=profileReader(x,owner),before=x.location.href,writes=x.capsuleWrites,reads=x.pending.length;
  apply('zh');await tick();
  assert.equal(x.lang,'en');assert.equal(x.location.href,before);assert.equal(x.capsuleWrites,writes);assert.equal(x.pending.length,reads);
 });
}

// U5 legacy demand: the retained page keeps the legacy study panels inside a
// closed <details id="mmr-legacy">. Hidden panels must not start data reads
// until that section is first opened; standalone pages keep the eager boot.
function legacyDetails() {
 const listeners={};
 const el={addEventListener(t,f){(listeners[t]||(listeners[t]=[])).push(f);},hasAttribute(name){return name==='open'&&!!el.open;}};
 let open=false;
 Object.defineProperty(el,'open',{get:()=>open,set:v=>{v=!!v;if(v===open)return;open=v;(listeners.toggle||[]).forEach(f=>f());}});
 return el;
}
const openLegacy=x=>{x.elements['mmr-legacy'].open=true;};
const closeLegacy=x=>{x.elements['mmr-legacy'].open=false;};
test('closed legacy section boots with zero hidden reads',async()=>{
 const x=setup('?ticker=SPY&mm_issuer_input=SPY&mm_lang=zh',null,legacyDetails());await tick();
 assert.equal(x.pending.length,0);
 assert.equal(x.elements['mm-symbol-input'].value,'SPY');
 assert.equal(x.location.searchParams.get('mm_lang'),'zh');
});
test('first open starts exactly the two legacy reads for the latest valid intent',async()=>{
 const x=setup('?ticker=SPY',null,legacyDetails());await tick();
 assert.equal(x.pending.length,0);
 openLegacy(x);await tick();
 assert.equal(x.pending.length,2);
 assert.equal(x.pending.filter(p=>p.url.includes('/macro?')).length,1);
 assert.equal(x.pending.filter(p=>p.url.endsWith('/symbol/SPY')).length,1);
 replyLegacy(x.pending[0],200,{as_of:'M1',query:{},episodes:[],context_note:'CTX'});replyLegacy(x.pending[1],200,{ticker:'SPY',as_of:'S1',grids:{}});
 await tick();
 assert.match(x.elements['mm-macro-state'].textContent,/State through M1/);
 assert.match(x.elements['mm-symbol-summary'].innerHTML,/SPY/);
});
test('repeated toggle while pending never duplicates an in-flight load',async()=>{
 const x=setup('?ticker=SPY',null,legacyDetails());await tick();
 assert.equal(x.pending.length,0);
 openLegacy(x);await tick();assert.equal(x.pending.length,2);
 closeLegacy(x);openLegacy(x);closeLegacy(x);openLegacy(x);await tick();
 assert.equal(x.pending.length,2);
});
test('reopen of already loaded panels does not refetch',async()=>{
 const x=setup('?ticker=SPY',null,legacyDetails());await tick();
 assert.equal(x.pending.length,0);
 openLegacy(x);await tick();
 for(const item of x.pending)replyLegacy(item,200,{as_of:'M1',query:{},episodes:[],ticker:'SPY',grids:{}});
 await tick();closeLegacy(x);openLegacy(x);await tick();
 assert.equal(x.pending.length,2);
 assert.match(x.elements['mm-macro-state'].textContent,/State through M1/);
});
test('closed popstate adopts the latest issuer and stale responses cannot revive',async()=>{
 const x=setup('?ticker=SPY',null,legacyDetails());await tick();
 assert.equal(x.pending.length,0);
 openLegacy(x);await tick();
 const spy=x.pending.find(p=>p.url.endsWith('/symbol/SPY'));
 closeLegacy(x);
 x.navigate('?ticker=AAPL&mm_issuer_input=AAPL');await tick();
 assert.equal(x.pending.length,2,'closing after first open must defer the new issuer read');
 assert.equal(x.elements['mm-symbol-input'].value,'AAPL');
 replyLegacy(spy,200,{ticker:'OLD_SPY',as_of:'OLD',grids:{}});
 await tick();
 assert.equal(JSON.stringify(x.elements).includes('OLD_SPY'),false);
 openLegacy(x);await tick();
 assert.equal(x.pending.filter(p=>p.url.endsWith('/symbol/AAPL')).length,1,'reopen fetches only the latest issuer');
 assert.equal(x.pending.filter(p=>p.url.endsWith('/symbol/SPY')).length,1,'the superseded request is never repeated');
});
for(const raw of ['a/b',''])test('closed popstate to invalid issuer '+JSON.stringify(raw)+' adopts it without fallback reads',async()=>{
 const x=setup('?ticker=SPY&mm_issuer_input=SPY',null,legacyDetails());await tick();
 x.navigate('?ticker=AAPL&mm_issuer_input='+encodeURIComponent(raw));await tick();
 assert.equal(x.pending.length,0);
 assert.equal(x.elements['mm-symbol-input'].value,raw);
 assert.match(x.elements['mm-symbol-summary'].innerHTML,/Check the ticker/);
 openLegacy(x);await tick();
 assert.equal(x.pending.filter(p=>p.url.includes('/symbol/')).length,0);
});
test('sign-out stays immediate while closed and sign-in fetches nothing until open',async()=>{
 const x=setup('?ticker=SPY',null,legacyDetails());await tick();
 assert.equal(x.pending.length,0);
 x.auth(null);await tick();
 assert.match(x.elements['mm-macro-state'].textContent,/Sign in required/);
 assert.match(x.elements['mm-symbol-summary'].innerHTML,/cleared when you sign out/);
 x.auth({id:'fixture'});await tick();
 assert.equal(x.pending.length,0,'sign-in while closed must not fetch hidden panels');
 openLegacy(x);await tick();
 assert.equal(x.pending.length,2,'the next open performs the needed authenticated loads');
});
test('closed language redraw stays fetch-free and the restored language is retained',async()=>{
 const x=setup('?ticker=SPY&mm_lang=zh',null,legacyDetails());await tick();
 assert.equal(x.pending.length,0);
 x.setLang('en');await tick();
 assert.equal(x.pending.length,0);
 assert.equal(x.lang,'en');
 assert.equal(x.location.searchParams.get('mm_lang'),'en');
 openLegacy(x);await tick();
 assert.equal(x.pending.length,2);
 for(const item of x.pending)replyLegacy(item,200,{as_of:'M1',query:{},episodes:[],ticker:'SPY',grids:{}});
 await tick();closeLegacy(x);
 x.setLang('zh');await tick();
 assert.equal(x.pending.length,2,'language changes never refetch');
 assert.match(x.elements['mm-symbol-summary'].innerHTML,/事件记忆/);
});
test('sign-in after a previously opened section closes defers refreshed legacy reads',async()=>{
 const x=setup('?ticker=SPY',null,legacyDetails());await tick();
 openLegacy(x);await tick();
 for(const item of x.pending)replyLegacy(item,200,{as_of:'M1',query:{},episodes:[],ticker:'SPY',grids:{}});
 await tick();closeLegacy(x);
 x.auth(null);await tick();
 assert.match(x.elements['mm-symbol-summary'].innerHTML,/cleared when you sign out/);
 x.auth({id:'fixture'});await tick();
 assert.equal(x.pending.length,2,'sign-in must not read a section that has closed again');
 openLegacy(x);await tick();
 assert.equal(x.pending.length,4,'opening performs exactly the two required refreshed reads');
});
test('pages without the legacy section keep the eager boot reads',async()=>{
 const x=setup('?ticker=SPY');await tick();
 assert.equal(x.pending.length,2);
});
