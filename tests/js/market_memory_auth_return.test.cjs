'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'../..');
const script=n=>fs.readFileSync(path.join(root,'templates',n),'utf8');
const tick=()=>new Promise(r=>setImmediate(r));
function setup(query) {
 const ids=['mm-macro-state','mm-macro-query','mm-macro-episodes','mm-macro-note','mm-symbol-form','mm-symbol-input','mm-symbol-summary','mm-grid-list'];
 const elements=Object.fromEntries(ids.map(id=>[id,{innerHTML:'',textContent:'',value:'',events:{},addEventListener(t,f){this.events[t]=f;}}]));
 const events={},windowEvents={},pending=[],stored={market_memory_ticker:'AAPL'};
 let lang='en',authChanged,opened=0;
 const location=new URL('https://mastermind-x.com/market_memory.html'+query);
 const history={state:{},replaceState(_a,_b,url){location.href=new URL(url,location).href;}};
 const document={readyState:'complete',documentElement:{getAttribute:()=>lang},getElementById:id=>elements[id],addEventListener(t,f){events[t]=f;}};
 const window={location,history,addEventListener(t,f){windowEvents[t]=f;},setLang(v){lang=v;},MDXAuth:{onChange(f){authChanged=f;},open(){opened++;}}};
 const context={window,document,location,history,URL,URLSearchParams,console,localStorage:{getItem:k=>stored[k],setItem(k,v){stored[k]=v;}},fetch:url=>new Promise(resolve=>pending.push({url,resolve}))};
 vm.createContext(context);vm.runInContext(script('market_memory_intent.js'),context);vm.runInContext(script('market_memory.js'),context);
 return {elements,events,pending,stored,window,location,auth:u=>authChanged(u),get opened(){return opened;},setLang(v){lang=v;events.langchange();},submit(raw){elements['mm-symbol-input'].value=raw;elements['mm-symbol-form'].events.submit({preventDefault(){}});}};
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
