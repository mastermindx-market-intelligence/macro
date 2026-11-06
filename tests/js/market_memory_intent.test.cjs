'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const sourcePath = path.resolve(__dirname, '../../templates/market_memory_intent.js');
const source = fs.existsSync(sourcePath) ? fs.readFileSync(sourcePath, 'utf8') : '';
function setup(search, saved, unavailable) {
  const location = {origin:'https://macro.example',href:'https://macro.example/market_memory.html'+(search||'')};
  const history = {state:{preserve:'history'},calls:[],replaceState(state,unused,target) {
    this.calls.push({state,target}); location.href = new URL(target,location.origin).href;
  }};
  const backing = saved || {};
  const sessionStorage = {getItem:k=>backing[k]||null,removeItem:k=>{delete backing[k];},setItem:(k,v)=>{if(unavailable)throw new Error("storage unavailable");backing[k]=v;}};
  const window = {location,history,sessionStorage};
  vm.runInNewContext(source,{window,URL,URLSearchParams});
  return {api:window.MarketMemoryIntent,location,history,saved:backing};
}
let count=0;
function test(name,fn) {fn();count++;process.stdout.write('PASS '+name+'\n');}
test('page API exists without automatic history/auth work',()=>{const x=setup();assert.ok(x.api,'MarketMemoryIntent is missing');assert.equal(x.history.calls.length,0);});
test('all retained keys roundtrip exact strings with semantic mapping',()=>{
  const x=setup();const snapshot={mode:'historical',query:'mmquery_a',subject:'mmsecurity_b',gen:'mmgeneration_c',gen_sha:'a'.repeat(64),cutoff:'2026-10-13T12:00:00.123456Z',method:'mmretainedmethod_d',context:'mmctx_e',sourceField:'growth_score',outcomeLens:'then_known'};
  assert.equal(x.api.replace(snapshot).ok,true);const r=x.api.read();for(const k of Object.keys(snapshot))assert.equal(r.intent[k],snapshot[k]);
  const u=new URL(x.location.href);assert.equal(u.searchParams.get('mm_source_field'),'growth_score');assert.equal(u.searchParams.get('mm_outcome'),'then_known');
});
test('issuer marker absence is distinct from explicit empty',()=>{const x=setup('?ticker=AAPL');assert.equal(Object.hasOwn(x.api.read().intent,'issuerInput'),false);assert.equal(x.api.replace({issuerInput:''}).ok,true);assert.equal(x.api.read().intent.issuerInput,'');assert.equal(new URL(x.location.href).searchParams.get('ticker'),'AAPL');});
test('invalid Unicode issuer encodes once and remains exact',()=>{const x=setup();const raw='a/b 雪 & % # %2F';x.api.replace({issuerInput:raw});assert.equal(x.api.read().intent.issuerInput,raw);const inner=new URL(new URL(x.location.href).searchParams.get('ret'),x.location.origin);assert.equal(inner.searchParams.get('mm_issuer_input'),raw);});
test('raw issuer percent sequences never decode repeatedly',()=>{const x=setup('?mm_issuer_input=%252F');assert.equal(x.api.read().intent.issuerInput,'%2F');x.api.syncReturn();assert.equal(x.api.read().intent.issuerInput,'%2F');});
test('language and incomplete invalid reference tuple survive',()=>{const x=setup('?mm_query=&mm_gen_sha=invalid&mm_lang=zh');x.api.syncReturn();const r=x.api.read();assert.equal(r.intent.query,'');assert.equal(r.intent.gen_sha,'invalid');assert.equal(r.intent.language,'zh');assert.equal(Object.hasOwn(r.intent,'subject'),false);});
test('ret and every unknown/auth/token field excluded from both URLs',()=>{const x=setup('?ret=https%3A%2F%2Fevil.invalid&code=secret&access_token=secret&refresh_token=secret&error=secret&signin=1&signup=1&onboard=x&upgrade=1&plan=pro&period=y&unknown=private&ticker=NVDA#access_token=secret');x.api.syncReturn();const u=new URL(x.location.href);assert.deepEqual([...u.searchParams.keys()].sort(),['ret','ticker']);const inner=new URL(u.searchParams.get('ret'),x.location.origin);assert.deepEqual([...inner.searchParams.keys()],['ticker']);assert.equal(inner.hash,'');});
test('incoming external/path/control ret never determines owned destination',()=>{for(const incoming of ['https://evil.invalid','//evil.invalid','/\\evil.invalid','%2F%2Fevil.invalid','\nhttps://evil.invalid']){const x=setup('?ret='+encodeURIComponent(incoming));const r=x.api.syncReturn();assert.equal(r.ok,true);const u=new URL(r.target,x.location.origin);assert.equal(u.origin,x.location.origin);assert.equal(u.pathname,'/market_memory.html');}});
test('repeated sync is bounded and nonrecursive',()=>{const x=setup('?ticker=NVDA');for(let i=0;i<30;i++)assert.equal(x.api.syncReturn().ok,true);const u=new URL(x.location.href);assert.equal(u.searchParams.getAll('ret').length,1);const inner=new URL(u.searchParams.get('ret'),x.location.origin);assert.equal(inner.searchParams.has('ret'),false);assert.ok(x.location.href.length<500);assert.equal(x.history.calls[0].state,x.history.state);});
test('null removes key, undefined preserves, empty stays explicit',()=>{const x=setup('?mm_query=a&mm_context=b');x.api.replace({query:undefined,context:null,cutoff:''});const r=x.api.read().intent;assert.equal(r.query,'a');assert.equal(Object.hasOwn(r,'context'),false);assert.equal(r.cutoff,'');});
test('signin href is canonical fallback with exact same target',()=>{const x=setup('?mm_mode=saved&mm_lang=zh');x.api.syncReturn({issuerInput:''});const href=x.api.signinHref();assert.equal(href.ok,true);const u=new URL(href.href,x.location.origin);assert.equal(u.pathname,'/');assert.equal(u.searchParams.get('signin'),'1');assert.equal(u.searchParams.get('ret'),new URL(x.location.href).searchParams.get('ret'));});
test('duplicate owned query keys and malformed encoding fail explicitly',()=>{const x=setup();assert.equal(x.api.read('?mm_mode=saved&mm_mode=current').ok,false);assert.equal(x.api.read('?mm_issuer_input=%E0%A4').ok,false);});
test('oversize marker and whole URL refuse without truncation/history mutation',()=>{const x=setup('?ticker=AAPL');const before=x.location.href;assert.equal(x.api.replace({issuerInput:'x'.repeat(2049)}).ok,false);assert.equal(x.location.href,before);assert.equal(x.api.replace({query:'x'.repeat(512),subject:'x'.repeat(512),gen:'x'.repeat(512),gen_sha:'x'.repeat(512),cutoff:'x'.repeat(512),method:'x'.repeat(512),context:'x'.repeat(512),sourceField:'x'.repeat(512),outcomeLens:'x'.repeat(512)}).ok,false);assert.equal(x.location.href,before);});
test('unknown snapshot fields are excluded and invalid language refused',()=>{const x=setup();x.api.replace({access_token:'secret',user_id:'private',language:'en'});assert.equal(x.location.href.includes('secret'),false);assert.equal(x.location.href.includes('private'),false);assert.equal(x.api.replace({language:'fr'}).ok,false);});
test('catalog offset roundtrips once with exact generation and context',()=>{
  const x=setup('?mm_gen=mmgeneration_old&mm_gen_sha='+('a'.repeat(64))+'&mm_context=mmctx_old&mm_catalog_offset=20');
  assert.equal(x.api.syncReturn().ok,true);const r=x.api.read();assert.equal(r.intent.catalogOffset,'20');assert.equal(r.intent.gen,'mmgeneration_old');assert.equal(r.intent.context,'mmctx_old');
  const inner=new URL(new URL(x.location.href).searchParams.get('ret'),x.location.origin);assert.equal(inner.searchParams.get('mm_catalog_offset'),'20');
});
test('catalog offset accepts only canonical integers in range0..255',()=>{
  const x=setup();for(const value of ['0','1','20','255']){assert.equal(x.api.replace({catalogOffset:value}).ok,true);assert.equal(x.api.read().intent.catalogOffset,value);}
  for(const value of ['','-1','256','1.5','01','+1',' 1','1e1','NaN','Infinity','20junk']){const before=x.location.href;const result=x.api.replace({catalogOffset:value});assert.equal(result.ok,false,value);assert.equal(x.location.href,before);assert.equal(x.api.read('?mm_catalog_offset='+encodeURIComponent(value)).ok,false,value);}
  assert.equal(x.api.replace({catalogOffset:20}).ok,true);assert.equal(x.api.read().intent.catalogOffset,'20');
  for(const value of [20.5,-1,256,NaN,Infinity,true])assert.equal(x.api.replace({catalogOffset:value}).ok,false);
});
test('catalog offset absent remains absent and null removes it without pin substitution',()=>{
  const x=setup('?mm_gen=old&mm_context=missing');assert.equal(Object.hasOwn(x.api.read().intent,'catalogOffset'),false);
  x.api.replace({catalogOffset:'40'});x.api.replace({catalogOffset:null});const r=x.api.read().intent;assert.equal(Object.hasOwn(r,'catalogOffset'),false);assert.equal(r.gen,'old');assert.equal(r.context,'missing');
});
process.stdout.write('PASS '+count+' codec cases\n');

const CAPSULE='market_memory.intent.oauth.v1';
test('OAuth resume restores only the latest same-tab intent and keeps SDK controls live',()=>{
 const before=setup('?mm_mode=saved&ticker=AAPL'); before.api.replace({issuerInput:' nvda ',ticker:'NVDA',mode:'historical',gen:'exact-generation',gen_sha:'a'.repeat(64),cutoff:'2026-10-13T12:00:00.123456Z',language:'zh'});
 const capsule=JSON.parse(before.saved[CAPSULE]);assert.deepEqual(Object.keys(capsule).sort(),['savedAt','schema','target']);
 const after=setup('?onboard=resume&code=synthetic-code#access_token=synthetic-token',before.saved);
 assert.equal(after.api.resumeStatus().ok,true);assert.equal(after.api.resumeStatus().restored,true);
 assert.equal(after.api.read().intent.issuerInput,' nvda ');assert.equal(after.api.read().intent.gen,'exact-generation');
 assert.equal(after.api.read().intent.cutoff,'2026-10-13T12:00:00.123456Z');assert.equal(JSON.parse(before.saved[CAPSULE]).target,capsule.target);
 after.api.syncReturn();const url=new URL(after.location.href);assert.equal(url.searchParams.get('code'),'synthetic-code');assert.equal(url.searchParams.get('onboard'),'resume');assert.equal(url.hash,'#access_token=synthetic-token');
 const stored=before.saved[CAPSULE];assert.equal(stored.includes('synthetic-code'),false);assert.equal(stored.includes('synthetic-token'),false);assert.equal(stored.includes('onboard'),false);
 const ret=url.searchParams.get('ret');assert.equal(ret.includes('code='),false);assert.equal(ret.includes('#'),false);
});
test('ordinary navigation never restores a stale capsule',()=>{
 const old=setup('?ticker=AAPL');old.api.syncReturn();const fresh=setup('?ticker=NVDA',old.saved);assert.equal(fresh.history.calls.length,0);assert.equal(fresh.api.read().intent.ticker,'NVDA');assert.equal(fresh.api.resumeStatus().restored,false);
});
test('callback without a same-tab capsule refuses implicit defaults',()=>{const x=setup('?onboard=resume');assert.equal(x.api.resumeStatus().ok,false);assert.equal(x.history.calls.length,0);});
test('invalid expired external and noncanonical capsules refuse and are consumed',()=>{
 for(const corrupt of [v=>v.target='https://other.invalid/market_memory.html?ticker=AAPL',v=>v.target='/market_memory.html?ticker=AAPL&access_token=secret',v=>v.target+='&ticker=NVDA',v=>v.savedAt=Date.now()-31*60*1000,v=>v.savedAt=Date.now()+60000,v=>v.extra='private',v=>v.schema='wrong']){
  const before=setup('?ticker=AAPL');before.api.syncReturn();let v=JSON.parse(before.saved[CAPSULE]);corrupt(v);before.saved[CAPSULE]=JSON.stringify(v);
  const after=setup('?onboard=resume',before.saved);assert.equal(after.api.resumeStatus().ok,false);assert.equal(after.history.calls.length,0);assert.equal(before.saved[CAPSULE],undefined);
 }
});
test('invalid replacement clears old capsule and storage refusal is explicit',()=>{
 const x=setup('?ticker=AAPL');x.api.syncReturn();assert.ok(x.saved[CAPSULE]);assert.equal(x.api.syncReturn({issuerInput:'x'.repeat(2049)}).ok,false);assert.equal(x.saved[CAPSULE],undefined);
 const y=setup('?ticker=NVDA',{},true);const result=y.api.syncReturn();assert.equal(result.ok,true);assert.equal(result.oauthPreserved,false);assert.equal(y.api.oauthPreservation().reason,'intent_session_storage_unavailable');
});
test('callback with conflicting explicit intent refuses instead of overwriting it',()=>{
 const x=setup('?ticker=AAPL');x.api.syncReturn();const y=setup('?onboard=resume&mm_mode=current',x.saved);assert.equal(y.api.resumeStatus().ok,false);assert.equal(y.history.calls.length,0);
});
test('empty invalid issuer and incomplete exact pin survive OAuth without reinterpretation',()=>{
 for(const raw of ['', 'a/b']){const x=setup('?ticker=AAPL');x.api.replace({issuerInput:raw,gen:'old',gen_sha:'invalid',language:'zh'});const y=setup('?onboard=resume',x.saved);assert.equal(y.api.resumeStatus().ok,true);assert.equal(y.api.read().intent.issuerInput,raw);assert.equal(y.api.read().intent.gen_sha,'invalid');}
});
process.stdout.write(count+' total intent and OAuth tests passed\n');
test('reload of already restored callback uses current exact URL without stale recovery',()=>{
 const x=setup('?ticker=NVDA&mm_mode=saved');x.api.syncReturn();const y=setup('?onboard=resume',x.saved);y.api.syncReturn();
 const query=new URL(y.location.href).search;const z=setup(query,{});assert.equal(z.api.resumeStatus().ok,true);assert.equal(z.api.resumeStatus().restored,false);assert.equal(z.api.read().intent.ticker,'NVDA');assert.equal(z.history.calls.length,0);
});
process.stdout.write(count+' final intent and OAuth tests passed\n');

test('empty restored selection remains explicit and survives callback reload',()=>{const x=setup();x.api.syncReturn();const y=setup('?onboard=resume',x.saved);const z=setup(new URL(y.location.href).search,{});assert.equal(z.api.resumeStatus().ok,true);});
test('successful restoration renews only its exact intent for another same-tab sign-in',()=>{const x=setup('?ticker=NVDA&mm_mode=saved');x.api.syncReturn();const y=setup('?onboard=resume&code=first-synthetic',x.saved);assert.equal(y.api.oauthPreservation().ok,true);const z=setup('?onboard=resume&code=second-synthetic',x.saved);assert.equal(z.api.resumeStatus().ok,true);assert.equal(z.api.read().intent.ticker,'NVDA');assert.equal(x.saved[CAPSULE].includes('synthetic'),false);});
test('fallback signin link preserves latest intent even without earlier URL sync',()=>{const x=setup('?ticker=NVDA');assert.equal(x.api.signinHref().ok,true);assert.ok(x.saved[CAPSULE]);});
process.stdout.write(count+' reviewed intent and OAuth tests passed\n');

test('provider-preserved ret must match the capsule and may never substitute another selection',()=>{const x=setup('?ticker=NVDA');x.api.syncReturn();const target=x.api.target().target;const y=setup('?onboard=resume&ret='+encodeURIComponent(target),x.saved);assert.equal(y.api.resumeStatus().ok,true);const z=setup('?onboard=resume&ret='+encodeURIComponent('/market_memory.html?ticker=AAPL'),x.saved);assert.equal(z.api.resumeStatus().ok,false);});

console.log('29 reviewed intent and OAuth tests passed');
