'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const sourcePath = path.resolve(__dirname, '../../templates/market_memory_intent.js');
const source = fs.existsSync(sourcePath) ? fs.readFileSync(sourcePath, 'utf8') : '';
function setup(search) {
  const location = {origin:'https://macro.example',href:'https://macro.example/market_memory.html'+(search||'')};
  const history = {state:{preserve:'history'},calls:[],replaceState(state,unused,target) {
    this.calls.push({state,target}); location.href = new URL(target,location.origin).href;
  }};
  const window = {location,history};
  vm.runInNewContext(source,{window,URL,URLSearchParams});
  return {api:window.MarketMemoryIntent,location,history};
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
