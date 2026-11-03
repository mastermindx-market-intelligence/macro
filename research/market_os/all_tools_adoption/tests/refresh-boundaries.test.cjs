/* Regression of redraw and activation boundaries; recording DOM, not browser proof. */
const test=require('node:test'),assert=require('node:assert/strict');
const Nav=require(process.env.ALL_TOOLS_SOURCE || '../src/all-tools.js');
const {createPage}=require('./dom.cjs');
function setup(){
 const p=createPage(); let notify;
 p.d.defaultView.MutationObserver=class {constructor(cb){notify=cb;}observe(){}disconnect(){}};
 p.a=p.anchor();p.b=p.anchor({href:'reports.html',en:'Research Reports',zh:'研究报告',group:'Research',groupZh:'研究'});
 p.instance=Nav.mount(p.host);p.trigger.focus();p.instance.open();p.notify=()=>notify();return p;
}
const selected=p=>p.list.querySelectorAll('a[data-tools-href]').find(x=>x.dataset.toolsHref.endsWith('/macro.html'));
const redraws={
 language:p=>{p.d.documentElement.setAttribute('data-lang','zh');p.d.fire('langchange');},
 search:p=>{p.query.value='Market';p.query.fire('input');},
 clear:p=>{p.query.value='Market';p.clear.fire('click');},
 category:p=>{const b=p.categories.querySelectorAll('button').find(x=>x.dataset.toolsGroup==='United States');p.categories.fire('click',{target:b});},
 all:p=>p.all.fire('click'),
 refresh:p=>p.instance.refresh()
};
for(const [name,redraw] of Object.entries(redraws)){
 test('withdrawn destination stays unavailable after '+name,()=>{
  const p=setup();p.a.remove();p.notify();assert.equal(selected(p).hasAttribute('href'),false);
  redraw(p);const a=selected(p);assert.ok(a,'keep the inspected snapshot understandable');
  assert.equal(a.hasAttribute('href'),false);assert.equal(a.getAttribute('aria-disabled'),'true');
  assert.match(p.status.textContent,/changed|变化/);
 });
}
for(const kind of ['href','target','hidden','group-disabled'])test('render directly revalidates '+kind+' without observer delivery',()=>{
 const p=setup();if(kind==='href')p.a.href='china.html';if(kind==='target')p.a.target='_blank';if(kind==='hidden')p.a.hidden=true;if(kind==='group-disabled')p.a.closest('.nav-dd').setAttribute('data-nav-disabled','true');
 p.all.fire('click');assert.equal(selected(p).hasAttribute('href'),false);assert.match(p.count.textContent,/1 unavailable/);
});
for(const event of ['click','auxclick','contextmenu'])test(event+' cannot use a withdrawn link before observer flush',()=>{
 const p=setup(),a=selected(p);p.a.href='china.html';const e=p.list.fire(event,{target:a,button:event==='auxclick'?1:2});
 assert.equal(e.prevented,true);assert.equal(a.hasAttribute('href'),false);
});
for(const event of ['click','auxclick','contextmenu'])test(event+' preserves valid native navigation',()=>{
 const p=setup(),a=selected(p),href=a.href;const e=p.list.fire(event,{target:a,ctrlKey:true,button:1});
 assert.equal(e.prevented,false);assert.equal(a.href,href);assert.equal(p.d.defaultView.location.pathname,'/macro.html');
});
test('language change keeps keyboard focus on the same destination',()=>{
 const p=setup();selected(p).focus();p.d.documentElement.setAttribute('data-lang','zh');p.d.fire('langchange');
 assert.ok(p.d.activeElement===selected(p),"focus must remain on matching current destination");assert.equal(p.d.activeElement.isConnected,true);assert.deepEqual(p.d.activeElement.focusOptions,{preventScroll:true});
});
test('a withdrawn focused destination returns to menu heading during repaint',()=>{
 const p=setup();selected(p).focus();p.a.remove();p.instance.refresh();assert.ok(p.d.activeElement===p.title,"focus must return to heading");assert.deepEqual(p.title.focusOptions,{preventScroll:true});
});
test('typing keeps focus in search instead of moving it to a result',()=>{
 const p=setup();p.query.focus();p.query.value='Market';p.query.fire('input');assert.ok(p.d.activeElement===p.query,"typing must retain input focus");
});
test('menu refresh after close cannot leave stale destinations mounted',()=>{
 const p=setup();p.instance.close();p.instance.refresh();assert.equal(p.list.childNodes.length,0);assert.ok(p.d.activeElement===p.trigger,"close must restore opener");
});
test('unavailable snapshot is refreshed only on explicit reopen',()=>{
 const p=setup();p.a.remove();p.notify();p.all.fire('click');assert.ok(selected(p));assert.equal(selected(p).hasAttribute('href'),false);
 p.instance.close();p.instance.open();p.all.fire('click');assert.equal(selected(p),undefined);assert.match(p.list.textContent,/Research Reports/);
});
test('withdrawn state survives source toggle until the menu is reopened',()=>{
 const p=setup();p.a.hidden=true;p.notify();p.a.hidden=false;p.notify();p.instance.refresh();
 assert.equal(selected(p).hasAttribute('href'),false);
 p.instance.close();p.instance.open();assert.equal(selected(p).hasAttribute('href'),true);
});
test('unavailable row is removed from sequential keyboard destinations',()=>{
 const p=setup();p.a.remove();p.notify();p.instance.refresh();assert.equal(selected(p).getAttribute('tabindex'),'-1');
});
test('an unrelated valid destination stays navigable during withdrawal',()=>{
 const p=setup();p.a.remove();p.all.fire('click');const other=p.list.querySelectorAll('a[href]');
 assert.equal(other.length,1);assert.match(other[0].href,/reports.html$/);
 assert.equal(p.list.fire('auxclick',{target:other[0],button:1}).prevented,false);
});
test('cleared search preserves the applied category after withdrawal',()=>{
 const p=setup();p.all.fire('click');const b=p.categories.querySelectorAll('button').find(x=>x.dataset.toolsGroup==='Research');p.categories.fire('click',{target:b});
 p.a.remove();p.notify();p.query.value='Market';p.query.fire('input');p.clear.fire('click');assert.match(p.list.textContent,/Research Reports/);assert.equal(selected(p),undefined);
});
test('count explains displayed snapshot rows rather than calling all of them usable',()=>{
 const p=setup();p.all.fire('click');p.a.remove();p.notify();assert.equal(p.count.textContent,'2 destinations · 1 unavailable');
});
test('locale preserves unavailable count and snapshot ordering',()=>{
 const p=setup();p.all.fire('click');p.a.remove();p.notify();const order=p.list.querySelectorAll('a').map(a=>a.dataset.toolsHref);
 p.d.documentElement.setAttribute('data-lang','zh');p.d.fire('langchange');
 assert.equal(p.count.textContent,'2 个目的地 · 1 个暂不可用');assert.deepEqual(p.list.querySelectorAll('a').map(a=>a.dataset.toolsHref),order);
});
