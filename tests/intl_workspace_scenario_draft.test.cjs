'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const api = require('../templates/intl_workspace_scenario.js');
const context = {selected_market:'JP',horizon:'1m',currency_basis:'usd_unhedged'};
const next = {...context, selected_market:'DE', horizon:'3m'};
const action = (draft, command) => api.reduceDraft(draft, command, 'en');
const edit = (draft, field, raw) => action(draft,{type:'edit',field,raw}).draft;
function filled() { return edit(edit(api.createDraft(context),'local','5'),'fx','-3'); }
function calculated() { return action(filled(),{type:'calculate'}).draft; }
test('initial assumptions are blank and context is detached',()=>{
  const original={...context}; const d=api.createDraft(original); original.horizon='12m';
  assert.deepEqual(d.raw,{local:'',fx:''}); assert.equal(d.result,null); assert.deepEqual(d.rows,[]);
  assert.deepEqual(d.context,context); assert.equal(d.pending,null); assert.equal(d.tab,'history');
});
test('calculate uses accepted arithmetic and original raw strings',()=>{
  let d=edit(edit(api.createDraft(context),'local','＋５％'),'fx','−3');
  const r=action(d,{type:'calculate'}); assert.equal(r.ok,true);
  assert.equal(r.draft.result.usdPercent,1.85); assert.equal(r.draft.result.fxContributionPp,-3.15);
  assert.deepEqual(r.draft.raw,{local:'＋５％',fx:'−3'}); assert.equal(r.announce,true);
  assert.deepEqual(r.draft.rows.map(x=>x.fxPercent),[-3,0,3]);
});
for(const [field,raw] of [['local',''],['local','-'],['local','-101'],['fx','-100'],['fx','words'],['fx','1,5']]) {
  test('edit immediately clears every result: '+field+' '+raw,()=>{
    const d=edit(calculated(),field,raw); assert.equal(d.result,null); assert.deepEqual(d.rows,[]);
    const r=action(d,{type:'calculate'}); assert.equal(r.ok,false); assert.equal(r.focus,field);
    assert.ok(r.draft.errors[field]); assert.equal(r.announce,false);
  });
}
test('valid edit is not an implicit calculate or live announcement',()=>{
  const r=action(calculated(),{type:'edit',field:'local',raw:'6'});
  assert.equal(r.draft.result,null); assert.deepEqual(r.draft.rows,[]); assert.equal(r.announce,false);
});
test('blank explicit calculate focuses first input and shows both errors',()=>{
  const r=action(api.createDraft(context),{type:'calculate'});
  assert.equal(r.ok,false); assert.equal(r.focus,'local'); assert.ok(r.draft.errors.local); assert.ok(r.draft.errors.fx);
});
test('tabs preserve draft and result but make no announcement',()=>{
  const d=calculated(); const r=action(action(d,{type:'set_tab',tab:'scenario'}).draft,{type:'set_tab',tab:'history'});
  assert.deepEqual(r.draft,d); assert.equal(r.announce,false);
});
test('empty context changes commit directly without confirmation',()=>{
  const r=action(api.createDraft(context),{type:'propose_context',context:next});
  assert.equal(r.ok,true); assert.deepEqual(r.context_commit,next); assert.deepEqual(r.draft.context,next); assert.equal(r.draft.pending,null);
});
test('whitespace raw draft requires confirmation and is not silently erased',()=>{
  const d=edit(api.createDraft(context),'local',' ');
  const r=action(d,{type:'propose_context',context:next}); assert.equal(r.context_commit,null); assert.ok(r.draft.pending);
  assert.equal(r.draft.raw.local,' '); assert.deepEqual(r.draft.context,context);
});
test('same context is a no-op and keeps the calculation',()=>{
  const d=calculated(), r=action(d,{type:'propose_context',context:{...context}});
  assert.deepEqual(r.draft,d); assert.equal(r.context_commit,null); assert.equal(r.announce,false);
});
test('pending context does not overwrite old raw, context or accepted calculation',()=>{
  const d=calculated(), r=action(d,{type:'propose_context',context:next});
  assert.deepEqual(r.draft.raw,d.raw); assert.deepEqual(r.draft.context,d.context); assert.deepEqual(r.draft.result,d.result);
  assert.deepEqual(r.draft.pending,{context:next,raw:{local:'5',fx:'-3'},original_errors:d.errors}); assert.equal(r.context_commit,null);
  assert.equal(r.visible_result,null); assert.deepEqual(r.visible_rows,[]);
});
test('candidate editing and cancel restore exact prior inputs and result',()=>{
  const d=calculated(); let p=action(d,{type:'propose_context',context:next}).draft;
  p=edit(edit(p,'local','7'),'fx','-'); assert.deepEqual(p.raw,d.raw); assert.deepEqual(p.context,d.context);
  const r=action(p,{type:'cancel_context'}); assert.deepEqual(r.draft,d); assert.deepEqual(r.visible_result,d.result);
  assert.equal(r.context_commit,null); assert.equal(r.announce,false);
});
test('confirm invalid context draft does not adopt proposed market or horizon',()=>{
  let p=action(calculated(),{type:'propose_context',context:next}).draft; p=edit(p,'fx','-100');
  const r=action(p,{type:'confirm_context'}); assert.equal(r.ok,false); assert.equal(r.focus,'fx');
  assert.deepEqual(r.draft.context,context); assert.equal(r.context_commit,null); assert.ok(r.draft.pending);
  assert.equal(r.visible_result,null); assert.deepEqual(r.visible_rows,[]);
});
test('confirmed context atomically adopts reviewed inputs without annualization',()=>{
  let p=action(calculated(),{type:'propose_context',context:next}).draft; p=edit(p,'local','10');
  const r=action(p,{type:'confirm_context'}); assert.equal(r.ok,true); assert.deepEqual(r.context_commit,next);
  assert.deepEqual(r.draft.context,next); assert.deepEqual(r.draft.raw,{local:'10',fx:'-3'});
  assert.equal(r.draft.result.usdPercent,6.7); assert.equal(r.draft.pending,null); assert.equal(r.announce,true);
});
test('calculate cannot commit or reveal a pending context',()=>{
  const p=action(calculated(),{type:'propose_context',context:next}).draft;
  const r=action(p,{type:'calculate'}); assert.equal(r.ok,false); assert.deepEqual(r.draft,p);
  assert.equal(r.visible_result,null); assert.equal(r.context_commit,null);
});
test('a second context proposal cannot overwrite an unresolved candidate',()=>{
  const p=action(calculated(),{type:'propose_context',context:next}).draft;
  const r=action(p,{type:'propose_context',context:{...next,horizon:'12m'}});
  assert.equal(r.ok,false); assert.deepEqual(r.draft,p);
});
test('reset asks once, cancel is exact, confirm clears only scenario assumptions',()=>{
  const d=calculated(), p=action(d,{type:'request_reset'}).draft;
  assert.equal(p.reset_pending,true); assert.deepEqual(p.raw,d.raw); assert.deepEqual(p.result,d.result);
  assert.deepEqual(action(p,{type:'request_reset'}).draft,p);
  assert.deepEqual(action(p,{type:'cancel_reset'}).draft,d);
  const r=action(p,{type:'confirm_reset'}); assert.equal(r.ok,true); assert.deepEqual(r.draft.raw,{local:'',fx:''});
  assert.deepEqual(r.draft.context,context); assert.equal(r.draft.result,null); assert.deepEqual(r.draft.rows,[]);
  assert.equal(r.context_commit,null); assert.equal(r.draft.reset_pending,false);
});
test('reset without request cannot clear a draft',()=>{
  const d=calculated(),r=action(d,{type:'confirm_reset'}); assert.equal(r.ok,false); assert.deepEqual(r.draft,d);
});
test('reset and context confirmation are mutually exclusive',()=>{
  const d=calculated(); const c=action(d,{type:'propose_context',context:next}).draft;
  assert.equal(action(c,{type:'request_reset'}).ok,false);
  const r=action(d,{type:'request_reset'}).draft;
  assert.equal(action(r,{type:'propose_context',context:next}).ok,false);
  assert.equal(action(r,{type:'edit',field:'local',raw:'100'}).ok,false);
});
test('total loss still computes while invalid currency endpoint refuses',()=>{
  const d=edit(edit(api.createDraft(context),'local','-100'),'fx','5');
  const r=action(d,{type:'calculate'}); assert.equal(r.draft.result.usdPercent,-100); assert.equal(r.draft.result.fxContributionPp,0);
});
test('large finite assumptions have no arbitrary financial cap',()=>{
  const d=edit(edit(api.createDraft(context),'local','17'+ '0'.repeat(126)), 'fx','-99');
  assert.equal(action(d,{type:'calculate'}).ok,true);
});
test('repeated calculate does not reannounce an unchanged result',()=>{
  const d=calculated(),r=action(d,{type:'calculate'}); assert.equal(r.announce,false); assert.deepEqual(r.draft,d);
});
test('returned snapshots and commands cannot mutate earlier state',()=>{
  const d=calculated(), before=JSON.stringify(d), command={type:'propose_context',context:{...next}};
  const r=action(d,command); command.context.horizon='broken'; r.draft.pending.raw.fx='changed';
  assert.equal(JSON.stringify(d),before); assert.equal(r.draft.pending.context.horizon,'3m');
});
for(const command of [{type:'evil'}, {type:'edit',field:'__proto__',raw:'5'}, {type:'edit',field:'local',raw:5}, {type:'set_tab',tab:'other'}, {type:'confirm_context'}, {type:'propose_context',context:{...next,extra:'bad'}}]) {
  test('malformed or inapplicable command refuses without mutation '+JSON.stringify(command),()=>{
    const d=calculated(),r=action(d,command); assert.equal(r.ok,false); assert.deepEqual(r.draft,d); assert.equal(r.context_commit,null);
  });
}
test('only supported locales can commit a result',()=>{
  const r=api.reduceDraft(filled(),{type:'calculate'},'fr'); assert.equal(r.ok,false); assert.equal(r.draft.result,null);
});
test('input field length bound does not truncate raw or preserve success',()=>{
  const d=edit(calculated(),'local','1'.repeat(129)); const r=action(d,{type:'calculate'});
  assert.equal(d.raw.local.length,129); assert.equal(r.ok,false); assert.equal(r.draft.result,null);
});
test('cancel restores errors belonging to the original invalid draft',()=>{
  let d=action(edit(calculated(),'fx','-100'),{type:'calculate'}).draft;
  let p=action(d,{type:'propose_context',context:next}).draft;
  p=edit(p,'fx','-'); p=action(p,{type:'confirm_context'}).draft;
  assert.deepEqual(action(p,{type:'cancel_context'}).draft,d);
});
test('commands never execute accessors or toJSON hooks',()=>{
  let count=0; const c={type:'edit',field:'local'};
  Object.defineProperty(c,'raw',{enumerable:true,get(){count++; return '20';}});
  const d=calculated(); assert.equal(action(d,c).ok,false); assert.equal(count,0);
  const json={type:'calculate',toJSON(){count++; return {type:'calculate'};}};
  assert.equal(action(d,json).ok,false); assert.equal(count,0);
});
test('tampered draft results and draft accessors are rejected before use',()=>{
  const d=calculated(); d.result.usdPercent=123;
  assert.throws(()=>action(d,{type:'calculate'}),/invalid_scenario_draft/);
  let count=0; const e=calculated(); Object.defineProperty(e,'raw',{enumerable:true,get(){count++;return {};}});
  assert.throws(()=>action(e,{type:'calculate'}),/invalid_scenario_draft/); assert.equal(count,0);
});
