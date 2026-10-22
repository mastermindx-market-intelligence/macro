'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {createHash} = require('node:crypto');
const client = require('../templates/market_navigator_client.js');
const wire = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const copy = x => JSON.parse(JSON.stringify(x));
const digest=subject=>createHash('sha256').update(subject,'utf8').digest('hex');
const request = {request_id: wire.request_id, subject:'SPY:ARCX',
  subject_binding_sha256:digest('SPY:ARCX'), horizon:wire.horizon, as_of:wire.requested_as_of};
let checks=0;
function ok(fn) {fn();checks++;}
function refuse(change) {ok(()=>{const w=copy(wire);change(w);assert.throws(()=>client.validate(w,request));});}
ok(()=>assert.equal(client.validate(wire,request).readiness,'research_only'));
ok(()=>assert.equal(Object.isFrozen(client.validate(wire,request).scenarios[0].triggers[0]),true));
refuse(w=>w.subject_binding_sha256='0'.repeat(64));
refuse(w=>{delete w.subject_binding_sha256;});
refuse(w=>w.schema='market_navigator.response/v1');
ok(()=>assert.throws(()=>client.validate(wire,{...request,
   subject_binding_sha256:digest('QQQ:XNAS') })));
refuse(w=>w.request_id='another-request');
refuse(w=>w.horizon='swing');
refuse(w=>w.data.horizon='swing');
refuse(w=>w.requested_as_of='2026-10-21T20:02:00Z');
refuse(w=>w.data.as_of='2026-10-21T20:01:00.000001Z');
refuse(w=>w.data.authority.trading=true);
refuse(w=>w.data.authority.trading=0);
refuse(w=>w.data.authority.new_gate=false);
refuse(w=>w.data.readiness='ready_to_buy');
refuse(w=>w.data.scenarios[0].probability=.99);
refuse(w=>w.data.scenarios[0].status='buy');
refuse(w=>w.data.observations[0].source_ref='private://secret');
refuse(w=>w.data.observations[0].value=NaN);
refuse(w=>w.data.observations[0].value=true);
refuse(w=>w.data.observations[0].status='stale');
refuse(w=>w.data.observations[0].quality='synthetic');
refuse(w=>w.data.observations[0].observed_at='2026-10-21');
refuse(w=>w.data.scenarios[0].triggers[0].threshold='773');
refuse(w=>w.data.scenarios[0].triggers[0].met='yes');
refuse(w=>w.data.observations.push(copy(w.data.observations[0])));
refuse(w=>w.data.scenarios.push(copy(w.data.scenarios[0])));
refuse(w=>w.data.canonical_market.verdict='RISK_ON');
refuse(w=>{w.data.canonical_market.status='current';w.data.canonical_market.verdict='RISK_ON';});
refuse(w=>w.data.scenarios[0].support=[{key:'x',status:'execute'}]);
ok(()=>{const w=copy(wire);w.data.as_of='2026-10-21T16:01:00-04:00';assert.equal(client.validate(w,request).horizon,'intraday');});
ok(()=>{const w=copy(wire);const result=client.validate(w,request);w.data.observations[0].value=1;assert.equal(result.observations[0].value,773.09);});

(async()=>{
  let pending=[],states=[];
  const c=client.createController({read:(r,signal)=>new Promise((resolve,reject)=>pending.push({r,signal,resolve,reject})),render:s=>states.push(s)});
  async function untilPending(n) {
    for (let i=0;i<70;i++) {
      if (pending.length>=n) return;
      await new Promise(resolve=>setTimeout(resolve,1));
    }
    throw new Error('Subject digest / read did not become available');
  }
  function response(r){return {...copy(wire),request_id:r.request_id,requested_as_of:r.as_of,horizon:r.horizon};}
  const q={subject:'SPY:ARCX',horizon:'intraday',as_of:wire.requested_as_of};
  const first=c.load(q);await untilPending(1);
  assert.equal(states.at(-1).status,'loading');assert.equal(states.at(-1).data,null);
  const second=c.load({...q,subject:'QQQ:XNAS'});await untilPending(2);
  assert.equal(pending[0].signal.aborted,true);
  // Identical clock/horizon/epoch-local correlation cannot disguise a replay
  // from a different instrument: this is now a first-class falsifier.
  pending[1].resolve(response(pending[1].r));await second;
  assert.equal(states.at(-1).status,'invalid_response');checks++;
  const count=states.length;pending[0].resolve(response(pending[0].r));await first;
  assert.equal(states.length,count);checks++;
  const third=c.load(q);await untilPending(3);
  pending[2].resolve(response(pending[2].r));await third;
  assert.equal(states.at(-1).status,'recorded_context');checks++;
  const fourth=c.load(q);await untilPending(4);
  assert.equal(states.at(-1).data,null);
  pending[3].reject(new Error('secret source failure'));await fourth;
  assert.deepEqual(states.at(-1),{status:'unavailable',data:null});
  assert.equal(pending.length,4);checks++;
  const fifth=c.load(q);await untilPending(5);
  const malformed=response(pending[4].r);malformed.data.authority.sizing=true;
  pending[4].resolve(malformed);await fifth;
  assert.equal(states.at(-1).status,'invalid_response');checks++;
  const sixth=c.load(q);await untilPending(6);c.clear();
  const afterClear=states.length;
  pending[5].resolve(response(pending[5].r));await sixth;
  assert.equal(states.length,afterClear);
  assert.equal(states.at(-1).data,null);checks++;
  c.dispose();await assert.rejects(()=>c.load(q),/disposed/);checks++;
  assert.equal(JSON.stringify(states).includes('secret source failure'),false);checks++;
  console.log(JSON.stringify({checks,wrong_subject_ignored:true,
    late_response_ignored:true,loading_clears_prior:true,no_retry:true}));
})().catch(err=>{console.error(err);process.exitCode=1;});
