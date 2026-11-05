'use strict';
// Source DOM acceptance only: no browser, navigation server or capture effect.
const test=require('node:test'),assert=require('node:assert/strict');
const {JSDOM}=require('jsdom');
const fs=require('node:fs'),path=require('node:path'),{execFileSync}=require('node:child_process');
const ROOT=path.resolve(__dirname,'..');
const fixture=JSON.parse(execFileSync('python3',['-m','tests.history_browser_fixture'],{cwd:ROOT,encoding:'utf8'}));
function setup(t,change){
 const dom=new JSDOM('<!doctype html><html lang="en"><body>'+fixture.html+'</body></html>',{url:'https://fixture.invalid/intl.html?view=history&market=JP&horizon=1m&basis=usd_unhedged&return_basis=price',runScripts:'outside-only'});
 t.after(()=>dom.window.close());const w=dom.window;
 w.fetch=()=>{throw Error('network forbidden');};w.XMLHttpRequest=function(){throw Error('network forbidden');};
 w.matchMedia=()=>({matches:false,addEventListener(){},removeEventListener(){}});
 w.HTMLElement.prototype.getClientRects=function(){return this.closest('[hidden]')?[]:[{width:100,height:44}];};
 if(change)change(w.document);
 for(const f of ['intl_workspace_state.js','intl_workspace_scenario.js','intl_workspace.js'])w.eval(fs.readFileSync(path.join(ROOT,'templates',f),'utf8'));
 const h=w.IntlWorkspace.mountIntlWorkspace(w.document.querySelector('[data-im-workspace]'),w.JSON.parse(JSON.stringify(fixture.config)));
 const slot=w.document.querySelector('[data-im-history-market="JP"]');
 const q=s=>slot.querySelector(s),event=(node,type)=>node.dispatchEvent(new w.Event(type,{bubbles:true,cancelable:true}));
 function pick(side,value){const el=q('[data-im-snapshot-date="'+side+'"]');el.value=value;event(el,'change');}
 const dates=()=>Array.from(q('[data-im-snapshot-date="left"]').options).slice(1).map(o=>o.value);
 const submit=()=>event(q('[data-im-snapshot-form]'),'submit');
 return {w,h,q,slot,event,pick,dates,submit};
}
test('blank authored controls commit exact ordered pair only on Compare',t=>{
 const x=setup(t),dates=x.dates();assert.ok(dates.length>=2);
 assert.equal(x.q('[data-im-snapshot-date="left"]').value,'');assert.equal(x.q('[data-im-snapshot-date="right"]').value,'');
 assert.equal(x.q('[data-im-snapshot-result]').hidden,true);
 x.pick('left',dates[1]);x.pick('right',dates[0]);assert.equal(x.q('[data-im-snapshot-result]').hidden,true);x.submit();
 assert.equal(x.q('[data-im-snapshot-result]').hidden,false);
 assert.equal(x.q('[data-im-snapshot-at="left"]').textContent,dates[1]);assert.equal(x.q('[data-im-snapshot-at="right"]').textContent,dates[0]);
 const rows=JSON.parse(x.q('[data-im-snapshot-payload]').textContent).points;
 assert.equal(x.q('[data-im-snapshot-score="left-growth_score"]').textContent,rows[1][1]);
 x.pick('left',dates[0]);assert.equal(x.q('[data-im-snapshot-result]').hidden,true);x.submit();
 assert.match(x.q('[data-im-snapshot-status]').textContent,/different/);assert.equal(x.q('[data-im-snapshot-result]').hidden,true);
});
test('missing and null observations withhold and clear earlier pair',t=>{
 const x=setup(t,d=>{const p=d.querySelector('[data-im-snapshot-payload]'),v=JSON.parse(p.textContent);v.points[0][1]=null;p.textContent=JSON.stringify(v);});
 const dates=x.dates();x.pick('left',dates[0]);x.pick('right',dates[1]);x.submit();assert.equal(x.q('[data-im-snapshot-result]').hidden,true);assert.match(x.q('[data-im-snapshot-status]').textContent,/missing scores/);
 x.pick('left','');x.submit();assert.match(x.q('[data-im-snapshot-status]').textContent,/select dates/);
});
test('denied and incompatible source disable selection rather than promote ready rows',t=>{
 for(const reason of ['value_denied','comparability_not_established']){
 const x=setup(t,d=>{const p=d.querySelector('[data-im-snapshot-payload]'),v=JSON.parse(p.textContent);v.selection={eligible:false,reason};p.textContent=JSON.stringify(v);d.querySelectorAll('[data-im-snapshot-date] option:not([value=""])').forEach(n=>n.remove());});
 assert.equal(x.q('[data-im-snapshot-fields]').disabled,true);x.submit();assert.equal(x.q('[data-im-snapshot-result]').hidden,true);
 }
});
test('Scenario and Overview return retain manual draft without importing scores or dates',t=>{
 const x=setup(t),dates=x.dates();x.pick('left',dates[0]);x.pick('right',dates[1]);x.submit();
 const local=x.w.document.querySelector('[data-im-scenario-field="local"]'),fx=x.w.document.querySelector('[data-im-scenario-field="fx"]');
 assert.equal(local.value,'');assert.equal(fx.value,'');local.value='7';x.event(local,'input');fx.value='2';x.event(fx,'input');
 x.q('[data-im-snapshot-result] button').click();assert.equal(x.w.document.querySelector('[data-im-history-panel]').getAttribute('data-im-history-tab'),'scenario');
 assert.equal(local.value,'7');assert.equal(fx.value,'2');assert.equal(x.h.getState().horizon,'1m');
 x.w.document.querySelector('.intl-history__footer button').click();assert.equal(x.h.getState().view,'overview');
 x.w.document.querySelector('[data-im-action="set_view"][data-im-view="history"]').click();assert.equal(x.h.getState().view,'history');
 assert.equal(local.value,'7');assert.equal(x.q('[data-im-snapshot-date="left"]').value,dates[0]);
});
test('new generation or payload invalidates a committed comparison',t=>{
 const x=setup(t),dates=x.dates();x.pick('left',dates[0]);x.pick('right',dates[1]);x.submit();
 const next='im-workspace-generation:99999999-9999-4999-8999-999999999999',old=x.h.getState().source_reference;
 x.w.document.querySelectorAll('[data-im-generation]').forEach(n=>n.setAttribute('data-im-generation',next));
 assert.equal(x.h.replaceSource(next,old).ok,true);assert.equal(x.q('[data-im-snapshot-result]').hidden,true);assert.equal(x.q('[data-im-snapshot-date="left"]').value,'');
 const p=x.q('[data-im-snapshot-payload]');p.textContent='{}';x.event(x.q('[data-im-snapshot-form]'),'submit');assert.equal(x.q('[data-im-snapshot-result]').hidden,true);
});
test('destroy restores blank disabled fallback',t=>{
 const x=setup(t),dates=x.dates();x.pick('left',dates[0]);x.pick('right',dates[1]);x.submit();x.h.destroy();
 assert.equal(x.q('[data-im-snapshot-date="left"]').value,'');assert.equal(x.q('[data-im-snapshot-fields]').disabled,true);assert.equal(x.q('[data-im-snapshot-result]').hidden,true);
});

test('monthly precision and large score strings survive explicit intent and locale changes',async t=>{
 const x=setup(t,d=>{
  const script=d.querySelector('[data-im-snapshot-payload]'),p=JSON.parse(script.textContent);
  p.points.forEach((row,i)=>{row[0]='2026-'+String(i+1).padStart(2,'0');});p.points[0][1]='9007199254740993';
  script.textContent=JSON.stringify(p);
  d.querySelectorAll('[data-im-history-market="JP"] [data-im-snapshot-date]').forEach(select=>{Array.from(select.options).slice(1).forEach((o,i)=>{o.value=p.points[i][0];o.textContent=p.points[i][0];});});
 });
 const dates=x.dates();x.pick('left',dates[0]);x.pick('right',dates[1]);x.submit();
 assert.equal(x.q('[data-im-snapshot-at="left"]').textContent,'2026-01');assert.equal(x.q('[data-im-snapshot-score="left-growth_score"]').textContent,'9007199254740993');
 x.w.document.documentElement.lang='zh';await new Promise(resolve=>setImmediate(resolve));
 assert.match(x.q('[data-im-snapshot-status]').textContent,/当前重建/);assert.equal(x.q('[data-im-snapshot-date="left"]').value,'2026-01');
 assert.equal(x.q('[data-im-snapshot-date="left"]').options[0].textContent,'选择观测');
});
test('market change and return cannot revive the prior pair',t=>{
 const x=setup(t),dates=x.dates();x.pick('left',dates[0]);x.pick('right',dates[1]);x.submit();
 const market=x.w.document.querySelector('[data-im-history-panel] select[data-im-action="select_market"]');
 market.value='KR';x.event(market,'change');assert.equal(x.h.getState().selected_market,'KR');
 market.value='JP';x.event(market,'change');assert.equal(x.h.getState().selected_market,'JP');
 assert.equal(x.q('[data-im-snapshot-result]').hidden,true);assert.equal(x.q('[data-im-snapshot-date="left"]').value,'');
});

test('missing payload or partial controls clear the committed pair and disable remaining controls',t=>{
 for(const selector of ['[data-im-snapshot-payload]','[data-im-snapshot-date="right"]']){
  const x=setup(t),dates=x.dates();x.pick('left',dates[0]);x.pick('right',dates[1]);x.submit();
  assert.equal(x.q('[data-im-snapshot-result]').hidden,false);
  x.q(selector).remove();x.pick('left',dates[1]);
  assert.equal(x.q('[data-im-snapshot-result]').hidden,true);
  assert.equal(x.q('[data-im-snapshot-fields]').disabled,true);
  assert.equal(x.q('[data-im-snapshot-date="left"]').disabled,true);
  assert.equal(x.q('[data-im-snapshot-at="right"]').textContent,'');
  assert.equal(x.q('[data-im-snapshot-score="right-growth_score"]').textContent,'');
  assert.equal(x.q('[data-im-snapshot-date="left"]').value,'');
  assert.match(x.q('[data-im-snapshot-status]').textContent,/withheld/);
 }
});
