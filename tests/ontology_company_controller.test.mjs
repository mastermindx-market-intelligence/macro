import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
// The browser owns module loading. Import the exact source as ESM so the pack's
// Node 20 runtime does not depend on a repo-wide package.json type setting.
const source = readFileSync(new URL('../templates/ontology-company-controller.js', import.meta.url));
const { createCompanyController } = await import('data:text/javascript;base64,' + source.toString('base64'));

const headers = {'Content-Type':'application/json','Cache-Control':'private, no-store','Vary':'Authorization, Cookie'};
const session = () => ({user:{id:'owner-one'},access_token:'fixture-token'});
const context = {issuer_binding:{issuer_id:'ISS:US-XNAS-ONE'}};
const selection = {selections:[{fact_id:'fact-one'},{fact_id:'fact-two'}],generation:'one'};
const decoder = {
  isPrivateCompanySymbol: v=> /^[A-Z]{1,24}$/.test(v),
  decodePrivateCompanyContext: async v => {assert.equal(v.type,'context');return context;},
  decodePrivateIssuerSelections: v => {assert.equal(v.type,'selection');return selection;},
  assertPrivateContextSelection: (c,s)=>{assert.equal(c,context);assert.equal(s,selection);},
  decodePrivateProductIntegration: (v,id)=>{assert.equal(v.id,id);return v;},
  assertPrivateComposition: (s,e,f)=>{assert.equal(s,selection);assert.equal(e.fact_id,f.id);assert.equal(f.generation,s.generation);},
  decodePrivateError: ()=>{throw new Error('closed');},
};
const response = value => new Response(JSON.stringify(value),{headers});
const deferred = () => {let resolve;const promise = new Promise(r=>{resolve=r;});return {resolve,promise};};
const turn = () => new Promise(resolve=>setImmediate(resolve));

function setup(fetchImpl, getSession=async()=>session(), otherDecoder=decoder) {
  const states=[];
  const controller=createCompanyController({fetchImpl,getSession,onState:s=>states.push(s),decoder:otherDecoder});
  return {controller,states};
}

test('a superseded unresolved session cannot start a request',async()=>{
  const pending=deferred();let calls=0,reads=0;
  const {controller,states}=setup(async()=>{calls++;return response({});},()=>++reads===1?pending.promise:Promise.resolve(null));
  const old=controller.lookup('OLD');
  await turn();
  await controller.lookup('NEW');
  pending.resolve(session());await old;
  assert.equal(calls,0);assert.equal(states.at(-1).status,'signed_out');controller.dispose();
});

test('uncooperative old fetch cannot publish after query replacement',async()=>{
  const pending=deferred();let calls=0;
  const {controller,states}=setup(async()=>++calls===1?pending.promise:response({type:calls===2?'context':'selection'}));
  const old=controller.lookup('OLD');await turn();
  await controller.lookup('NEW');
  const count=states.length;assert.equal(states.at(-1).status,'ready');
  pending.resolve(response({type:'context'}));await old;
  assert.equal(states.length,count);assert.equal(calls,3);controller.dispose();
});

test('clear invalidates a body reader which ignores abort',async()=>{
  const pending=deferred();let reads=0;
  const {controller,states}=setup(async()=>({ok:true,status:200,redirected:false,headers:new Headers(headers),
    body:{getReader:()=>({read:()=>++reads===1?pending.promise:Promise.resolve({done:true}),cancel:async()=>{},releaseLock(){}})}}));
  const action=controller.lookup('ONE');await turn();controller.clear();
  const count=states.length;pending.resolve({done:false,value:new TextEncoder().encode('{"type":"context"}')});await action;
  assert.equal(states.length,count);assert.equal(states.at(-1).status,'idle');controller.dispose();
});

test('changed account at final publication clears the result',async()=>{
  let calls=0;let current=session();
  const {controller,states}=setup(async()=>{calls++;return response({type:calls===1?'context':'selection'});},async()=>current,
    {...decoder,decodePrivateIssuerSelections:v=>{current={user:{id:'owner-two'},access_token:'other'};return decoder.decodePrivateIssuerSelections(v);}});
  await controller.lookup('ONE');assert.equal(states.at(-1).status,'signed_out');
  assert.ok(!states.at(-1).context);controller.dispose();
});

test('selected fact requires current selection; no automatic fact request',async()=>{
  let calls=0;const urls=[];
  const {controller,states}=setup(async url=>{urls.push(url);calls++;return response(calls===1?{type:'context'}:calls===2?{type:'selection'}:{id:'fact-one',generation:'one'});});
  await controller.lookup('ONE');assert.equal(calls,2);
  await controller.selectFact('fact-one');assert.equal(calls,3);assert.equal(states.at(-1).fact.id,'fact-one');
  await controller.selectFact('not-in-selection');assert.equal(calls,3);
  assert.ok(!states.at(-1).fact);controller.dispose();
});

test('old fact response cannot replace a later selection',async()=>{
  const pending=deferred();let calls=0;
  const {controller,states}=setup(async()=>{calls++;
    if(calls===3)return pending.promise;
    return response(calls===1?{type:'context'}:calls===2?{type:'selection'}:{id:'fact-two',generation:'one'});
  });
  await controller.lookup('ONE');const old=controller.selectFact('fact-one');await turn();
  await controller.selectFact('fact-two');
  assert.equal(states.at(-1).fact.id,'fact-two');const count=states.length;
  pending.resolve(response({id:'fact-one',generation:'one'}));await old;
  assert.equal(states.length,count);controller.dispose();
});

test('oversize streamed body is refused and cancelled before decoding',async()=>{
  let cancelled=false;
  const {controller,states}=setup(async()=>({ok:true,status:200,redirected:false,headers:new Headers(headers),
    body:{getReader:()=>({read:async()=>({done:false,value:new Uint8Array(65537)}),cancel:async()=>{cancelled=true;},releaseLock(){}})}}));
  await controller.lookup('ONE');assert.equal(states.at(-1).status,'unavailable');assert.ok(cancelled);controller.dispose();
});

test('deadline settles even if fetch ignores abort; dispose prevents all subsequent work',async()=>{
  const original=setTimeout;
  globalThis.setTimeout=(fn,ms,...args)=>original(fn,ms===15000?20:ms,...args);
  try{
    let calls=0;
    const {controller,states}=setup(()=>{calls++;return new Promise(()=>{});});
    const action=controller.lookup('ONE');
    await new Promise(resolve=>original(resolve,60));
    assert.equal(states.at(-1).status,'unavailable');
    controller.dispose();const count=states.length;
    await controller.lookup('TWO');await controller.selectFact('fact-one');
    assert.equal(calls,1);assert.equal(states.length,count);
    await Promise.race([action,new Promise((_,reject)=>original(()=>reject(new Error('action did not settle')),100))]);
  }finally{globalThis.setTimeout=original;}
});

test('expired continuation is refused even before a delayed timer callback',async t=>{
  let clock=0;let calls=0;
  t.mock.method(performance,'now',()=>clock);
  const {controller,states}=setup(async()=>{calls++;return response({type:'context'});},async()=>session(),
    {...decoder,decodePrivateCompanyContext:async value=>{
      clock=15001;return decoder.decodePrivateCompanyContext(value);
    }});
  await controller.lookup('ONE');
  assert.equal(calls,1);assert.equal(states.at(-1).status,'unavailable');
  assert.ok(!states.at(-1).context);controller.dispose();
});

test('header refusal aborts the transport without consuming a private body',async()=>{
  let signal;let reads=0;
  const {controller,states}=setup(async(_url,options)=>{
    signal=options.signal;
    return {status:200,redirected:false,headers:new Headers({'Content-Type':'application/json'}),
      body:{getReader(){reads++;throw new Error('must not read');}}};
  });
  await controller.lookup('ONE');
  assert.equal(reads,0);assert.ok(signal.aborted);
  assert.equal(states.at(-1).status,'unavailable');controller.dispose();
});


test('dated exposure identity mismatch refuses before issuer selections',async()=>{
  let calls=0;
  const currentContext={...context,security_id:'SEC:CURRENT'};
  const {controller,states}=setup(async()=>{calls++;return response({type:'context'});},async()=>session(),
    {...decoder,decodePrivateCompanyContext:async()=>currentContext});
  await controller.lookup('ONE','SEC:DATED');
  assert.equal(calls,1);assert.equal(states.at(-1).status,'unavailable');
  assert.ok(!states.at(-1).context);controller.dispose();
});

test('dated exposure identity must join before explicit fact selection',async()=>{
  let calls=0;
  const currentContext={...context,security_id:'SEC:DATED'};
  const {controller,states}=setup(async()=>{calls++;return response(calls===1?{type:'context'}:{type:'selection'});},async()=>session(),
    {...decoder,decodePrivateCompanyContext:async()=>currentContext,
     assertPrivateContextSelection:(c,s)=>{assert.equal(c,currentContext);assert.equal(s,selection);}});
  await controller.lookup('ONE','SEC:DATED');
  assert.equal(calls,2);assert.equal(states.at(-1).status,'ready');
  assert.ok(!states.at(-1).fact);controller.dispose();
});
