/* Deterministic client lifecycle tests; no real account, credential or HTTP. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
class Target{
  constructor(){this.listeners={};this.dataset={};this.attrs={};this.hidden=false;this.value='';this.classList={add(){},remove(){}};}
  addEventListener(k,f){(this.listeners[k]||(this.listeners[k]=new Set())).add(f);}
  removeEventListener(k,f){this.listeners[k]?.delete(f);}
  emit(k,event={}){for(const f of [...(this.listeners[k]||[])])f(event);}
  setAttribute(k,v){this.attrs[k]=v;}
  querySelectorAll(){return [];}
  contains(){return true;}
  focus(){} scrollIntoView(){} replaceChildren(){} click(){} remove(){}
}
function harness(){
  const root=new Target(),slot=new Target(),lock=new Target(),message=new Target(),actions=new Target(),signIn=new Target();
  const select=new Target(),exporter=new Target(),explorer=new Target(),library=new Target(),selected=new Target(),template=new Target();
  template.content={cloneNode(){return {};}};
  let deep=false,markup='LOCKED',retry=null,session=null;
  Object.defineProperty(slot,'innerHTML',{get:()=>markup,set(v){markup=v;deep=v==='DEEP';}});
  actions.querySelector=s=>s==='a:first-child'?signIn:retry;
  actions.appendChild=n=>{retry=n;n.remove=()=>{retry=null;};};
  lock.querySelector=s=>s==='p'?message:actions;
  const window=new Target();
  window.MDXAuth={hasSession:()=>!!session,client:()=>Promise.resolve({auth:{getSession:()=>Promise.resolve({data:{session}})}})};
  const document={documentElement:new Target(),body:new Target(),createElement:()=>new Target(),getElementById(id){
    if(id==='china-economy')return root;
    if(id==='eco-json')return {textContent:JSON.stringify({economy:null,detail_href:'china_economy_detail.json'})};
    if(id==='eco-detail-slot')return slot;
    if(id==='eco-detail-lock')return deep?null:lock;
    if(!deep)return null;
    return {'eco-metric-select':select,'eco-export':exporter,'eco-explorer':explorer,'eco-library':library,'eco-selected-metric':selected,'eco-template-industrial_sa':template}[id]||null;
  }};
  const requests=[];
  const ctx={window,document,console,AbortController,Promise,setTimeout,clearTimeout,URL,Blob,module:{exports:{}},
    MutationObserver:class{observe(){}disconnect(){}},
    fetch(url,opts){assert.equal(url,'china_economy_detail.json');assert.equal(opts.credentials,'same-origin');assert.equal(opts.cache,'no-store');return new Promise((resolve,reject)=>requests.push({resolve,reject,opts}));}};
  vm.runInNewContext(fs.readFileSync(process.argv[2],'utf8'),ctx);
  function auth(id,event=id?'SIGNED_IN':'SIGNED_OUT'){
    session=id?{user:{id}}:null;window.emit('mdx-auth',{detail:{user:session?.user||null,event}});
  }
  const payload=()=>({schema:'mastermind.china_economy_detail_payload.v1',status:'ok',reference_period:'2026-09',html:'DEEP',client:{economy:{schema:'mastermind.china_economy_lens.v1',reference_period:'2026-09',metrics:{industrial_sa:{chart:{dates:[],vals:[]},unit:'%',definition_id:'fixture'}},groups:[]}}});
  function respond(i,status=200,body=payload()){
    requests[i].resolve({ok:status===200,status,json:()=>Promise.resolve(body)});
  }
  return {root,slot,window,requests,auth,respond,payload,get retry(){return retry;},get deep(){return deep;}};
}
const tick=async()=>{for(let i=0;i<5;i++)await new Promise(setImmediate);};
(async()=>{
  let h=harness();await tick();assert.equal(h.requests.length,0);
  h.auth(null,'INITIAL_SESSION');h.auth('A');await tick();assert.equal(h.requests.length,1);
  h.respond(0);await tick();assert.equal(h.deep,true);assert.equal(h.root.dataset.ecoDetailReady,'true');
  const staleApi=h.window.EconomyLens;
  h.auth('A','TOKEN_REFRESHED');await tick();assert.equal(h.requests.length,1);
  h.auth(null);assert.equal(h.deep,false);assert.equal(h.window.EconomyLens,undefined);
  assert.equal(h.root.dataset.ecoDetailReady,undefined);staleApi.selectMetric('industrial_sa',false);
  h.auth('B');await tick();assert.equal(h.requests.length,2);
  h.auth(null);h.respond(1);await tick();assert.equal(h.deep,false);
  assert.equal(h.requests[1].opts.signal.aborted,true);
  h.auth('A');await tick();h.auth('C');await tick();assert.equal(h.requests.length,4);
  h.respond(2);await tick();assert.equal(h.deep,false);
  h.respond(3);await tick();assert.equal(h.deep,true);
  // A denial cannot be retried by a routine auth event or used as detail HTML.
  for(const status of [401,403,500]){
    h=harness();h.auth('A');await tick();h.respond(0,status);await tick();
    assert.equal(h.deep,false);assert.equal(h.root.dataset.ecoDetailState,status===401?'unauthenticated':status===403?'forbidden':'unavailable');
    h.auth('A','TOKEN_REFRESHED');await tick();assert.equal(h.requests.length,1);
  }
  // Both empty JSON and a wrong-period payload stay unavailable.
  for(const bad of [null,{schema:'bad'}, {...h.payload(),reference_period:'2026-08'}]){
    h=harness();h.auth('A');await tick();h.respond(0,200,bad);await tick();
    assert.equal(h.deep,false);assert.equal(h.root.dataset.ecoDetailState,'unavailable');
  }
  h=harness();h.auth('A');await tick();h.respond(0,500);await tick();
  h.root.emit('click',{target:{closest:()=>h.retry},preventDefault(){}});await tick();
  assert.equal(h.requests.length,2);h.respond(1);await tick();assert.equal(h.deep,true);
  console.log('PASS: anonymous, later sign-in, dedup, sign-out cleanup, stale response, account switch, 401/403/500, malformed JSON, explicit retry');
})().catch(error=>{console.error(error);process.exit(1);});
