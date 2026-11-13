const test=require('node:test'),assert=require('node:assert/strict');
const Nav=require(process.env.ALL_TOOLS_SOURCE || '../src/all-tools.js');const {createPage}=require('./dom.cjs');
function setup(o){const p=createPage(o);p.a=p.anchor();p.b=p.anchor({href:'reports.html',en:'Research Reports',zh:'研究报告',group:'Research',groupZh:'研究'});p.instance=Nav.mount(p.host);return p;}
for(const path of ['/macro.html','/sector_central.html','/reports.html'])test('same component mounts in pilot '+path,()=>{const p=setup({path});assert.ok(p.instance);assert.equal(p.trigger.parentElement,p.controls);assert.equal(p.trigger.hidden,false);});
for(const path of ['/index.html','/pricing.html','/sectors/macro.html','/watchlist.html'])test('no unrelated/public route adoption '+path,()=>{const p=setup({path});assert.equal(p.instance,null);assert.equal(p.trigger.hidden,true);});
test('no dialog support leaves original source navigation intact',()=>{const p=setup({supported:false});assert.equal(p.instance,null);assert.equal(p.root.querySelectorAll('a[href]').length,2);});
test('opening copies resolved source links without mutating them',()=>{const p=setup();const before=p.root.textContent;p.instance.open();p.all.fire('click');assert.equal(p.root.textContent,before);assert.equal(p.list.querySelectorAll('a').length,2);assert.equal(p.count.textContent,'2 destinations');});
test('new incumbent source entries are picked up without another route list',()=>{const p=setup();p.anchor({href:'new_feature.html',en:'New feature'});p.instance.open();p.all.fire('click');assert.equal(p.list.querySelectorAll('a').length,3);});
test('disabled source entry never appears',()=>{const p=setup();p.a.setAttribute('aria-disabled','true');p.instance.open();assert.equal(p.list.querySelectorAll('a').length,1);});
test('duplicates are collapsed by exact href and not translated label',()=>{const p=setup();p.anchor({href:'macro.html',en:'Alternate title'});p.instance.open();p.all.fire('click');assert.equal(p.list.querySelectorAll('a').length,2);});
test('desktop opens search without a viewport jump',()=>{const p=setup();p.instance.open();assert.equal(p.d.activeElement,p.query);assert.deepEqual(p.query.focusOptions,{preventScroll:true});});
test('phone opens heading without forcing the virtual keyboard',()=>{const p=setup({phone:true});p.instance.open();assert.equal(p.d.activeElement,p.title);});
test('Escape returns the original focus and releases only own scroll class',()=>{const p=setup();p.trigger.focus();p.d.documentElement.classList.add('another-feature');p.instance.open();const e=p.dialog.fire('cancel');assert.equal(e.prevented,true);assert.equal(p.d.activeElement,p.trigger);assert.equal(p.d.documentElement.classList.contains('mmx-tools-open'),false);assert.equal(p.d.documentElement.classList.contains('another-feature'),true);});
test('one menu instance and one opener survive duplicate mount attempts',()=>{const p=setup();assert.equal(Nav.mount(p.host),p.instance);assert.equal(p.controls.children.filter(x=>x.hasAttribute('data-tools-open')).length,1);});
test('composing Chinese does not render the unfinished query',()=>{const p=setup();p.instance.open();p.query.fire('compositionstart');p.query.value='研究';p.query.fire('input');assert.match(p.list.textContent,/Market Dashboard/);assert.doesNotMatch(p.list.textContent,/Research Reports/);p.query.fire('compositionend');assert.match(p.list.textContent,/Research Reports/);assert.doesNotMatch(p.list.textContent,/Market Dashboard/);});
test('query searches other groups without forcing a category change',()=>{const p=setup();p.instance.open();const b=p.categories.querySelectorAll('button').find(x=>x.dataset.toolsGroup==='United States');p.categories.fire('click',{target:b});p.query.value='research';p.query.fire('input');assert.equal(p.list.querySelectorAll('a').length,1);});
test('no match is tool-specific and query cannot inject nodes',()=>{const p=setup();p.instance.open();p.query.value='<img onerror=bad>';p.query.fire('input');assert.match(p.list.textContent,/No matching tools/);assert.equal(p.list.querySelectorAll('img').length,0);});
test('directory is an in-place full view, not a page transition',()=>{const p=setup();p.instance.open();p.all.fire('click');assert.equal(p.dialog.open,true);assert.equal(p.d.defaultView.location.pathname,'/macro.html');assert.equal(p.list.querySelectorAll('a').length,2);});
test('withdrawn target is stopped at click without substituting a tool',()=>{const p=setup();p.instance.open();const a=p.list.querySelector('a');p.a.remove();const e=p.list.fire('click',{target:a});assert.equal(e.prevented,true);assert.equal(a.hasAttribute('href'),false);assert.match(p.status.textContent,/destination changed/);});
test('changed href is not allowed to navigate to the old or new target silently',()=>{const p=setup();p.instance.open();const a=p.list.querySelector('a');p.a.href='china.html';assert.equal(p.list.fire('click',{target:a}).prevented,true);});
test('valid links retain normal modifier-key semantics',()=>{const p=setup();p.instance.open();const a=p.list.querySelector('a');assert.equal(p.list.fire('click',{target:a,ctrlKey:true}).prevented,false);assert.equal(a.target,'');});
test('cross-product source target and badge remain separate from portfolio',()=>{const p=setup();p.anchor({href:'https://bot.mastermind-x.com',en:'Mastermind Bot',zh:'模拟账户',target:'_blank',badge:'PRO',group:'Research'});p.instance.open();p.all.fire('click');const a=p.list.querySelectorAll('a').find(a=>a.href==='https://bot.mastermind-x.com/');assert.equal(a.target,'_blank');assert.match(a.rel,/noopener/);assert.match(a.textContent,/PRO/);});
test('source labels are copied as text, not interpreted as markup',()=>{const p=setup();p.anchor({href:'test.html',en:'<svg onload=bad>',zh:'<img>'});p.instance.open();assert.match(p.list.textContent,/<svg onload=bad>/);assert.equal(p.list.querySelectorAll('img').length,0);});
test('ordinary language switch keeps current query and hrefs',()=>{const p=setup();p.instance.open();p.query.value='research';p.query.fire('input');p.d.documentElement.setAttribute('data-lang','zh');p.d.fire('langchange');assert.equal(p.query.value,'research');assert.equal(p.list.querySelector('a').href,'https://www.mastermind-x.com/reports.html');assert.match(p.list.textContent,/研究报告/);});
test('reopen clears search but does not change any source selection',()=>{const p=setup();p.instance.open();p.query.value='research';p.query.fire('input');p.instance.close();p.instance.open();assert.equal(p.query.value,'');assert.equal(p.list.querySelectorAll('a').length,1);});
test('an already visible foreign modal is not overlaid',()=>{const p=setup();const other=p.d.createElement('dialog');p.d.body.appendChild(other);other.showModal();assert.equal(p.instance.open(),false);assert.equal(other.open,true);});
test('inactive aria-modal markup does not strand the menu closed',()=>{const p=setup();const other=p.d.createElement('div');other.setAttribute('aria-modal','true');other.hidden=true;p.d.body.appendChild(other);assert.equal(p.instance.open(),true);});
test('delayed close from the old opening does not disturb a new opening',()=>{const p=setup();p.instance.open();p.instance.close();p.instance.open();p.dialog.fire('close');assert.equal(p.dialog.open,true);assert.equal(p.d.documentElement.classList.contains('mmx-tools-open'),true);});
test('empty resolved navigation is not reported as a complete directory',()=>{const p=setup();p.a.remove();p.b.remove();p.instance.open();assert.match(p.count.textContent,/not ready/);assert.equal(p.list.querySelectorAll('a').length,0);});
test('disabled source group cannot leak a child into the menu',()=>{const p=setup();p.a.closest('.nav-dd').setAttribute('data-nav-disabled','true');p.instance.open();assert.doesNotMatch(p.list.textContent,/Market Dashboard/);assert.match(p.list.textContent,/Research Reports/);});
test('language repaint preserves focused category',()=>{const p=setup();p.instance.open();const b=p.categories.querySelectorAll('button')[1];b.focus();const key=b.dataset.toolsGroup;p.d.documentElement.setAttribute('data-lang','zh');p.d.fire('langchange');assert.equal(p.d.activeElement.isConnected,true);assert.equal(p.d.activeElement.dataset.toolsGroup,key);});
test('source withdrawal is reflected before context-menu navigation',()=>{const p=createPage();let observer,stopped=0;p.d.defaultView.MutationObserver=class{constructor(cb){observer=cb;}observe(){}disconnect(){stopped++;}};p.a=p.anchor();p.instance=Nav.mount(p.host);p.instance.open();const a=p.list.querySelector('a');p.a.remove();assert.equal(typeof observer,'function');observer();assert.equal(a.hasAttribute('href'),false);p.instance.close();assert.ok(stopped>0);});
test('an empty live source opens an explanation, not a dead button',()=>{const p=setup();p.a.remove();p.b.remove();p.instance.open();assert.equal(p.dialog.open,true);assert.match(p.list.textContent,/not ready|not available/i);assert.doesNotMatch(p.list.textContent,/No matching/);});
test('invalid host sibling is never treated as the common product header',()=>{const p=createPage();p.anchor();p.nav.className='public-nav';assert.equal(Nav.mount(p.host),null);});
test('source section names survive so a large research group is not a flat wall',()=>{const p=setup();const menu=p.b.parentElement,section=p.d.createElement('section');section.className='nav-mega-section';const heading=p.d.createElement('h2');heading.className='nav-mega-h';heading.textContent='Core research';section.appendChild(heading);menu.appendChild(section);section.appendChild(p.b);p.instance.open();p.all.fire('click');assert.match(p.list.textContent,/Core research/);});
test('opening prepares the current source group rather than unrelated countries',()=>{const p=setup();for(let i=0;i<15;i++)p.anchor({href:'cn-'+i+'.html',en:'China '+i,group:'China'});p.instance.open();assert.doesNotMatch(p.list.textContent,/China 0/);assert.match(p.list.textContent,/Market Dashboard/);});
test('research page starts with its own source group while all destinations remain reachable',()=>{const p=setup({path:'/reports.html'});p.instance.open();assert.match(p.list.textContent,/Research Reports/);assert.doesNotMatch(p.list.textContent,/Market Dashboard/);p.all.fire('click');assert.match(p.list.textContent,/Market Dashboard/);});
test('a source link changing its tab behavior is disabled until refreshed',()=>{const p=createPage();let observe;p.d.defaultView.MutationObserver=class{constructor(cb){observe=cb;}observe(){}disconnect(){}};p.a=p.anchor();p.instance=Nav.mount(p.host);p.instance.open();const a=p.list.querySelector('a');p.a.target='_blank';observe();assert.equal(a.hasAttribute('href'),false);});
test('the renderer does not create more than one active source-driven menu in a document',()=>{const p=setup(),second=p.host.cloneNode(true);p.d.body.appendChild(p.nav.cloneNode(true));p.d.body.appendChild(second);second.appendChild(p.trigger.cloneNode(true));const dialog=second.querySelector('dialog');dialog.showModal=()=>{};assert.equal(Nav.mount(second),null);});
test('missing required component markup preserves original navigation without throwing',()=>{const p=createPage();p.anchor();p.query.remove();assert.equal(Nav.mount(p.host),null);assert.equal(p.trigger.hidden,true);});
test('source blueprint shapes survive but executable SVG nodes do not',()=>{const p=setup();const svg=p.d.createElement('svg');svg.setAttribute('viewBox','0 0 48 48');const path=p.d.createElement('path');path.setAttribute('d','M1 1L2 2');path.setAttribute('onclick','bad()');svg.appendChild(path);svg.appendChild(p.d.createElement('script'));svg.appendChild(p.d.createElement('image'));p.a.appendChild(svg);p.instance.open();const icon=p.list.querySelector('svg');assert.equal(icon.querySelector('path').getAttribute('d'),'M1 1L2 2');assert.equal(icon.querySelector('path').hasAttribute('onclick'),false);assert.equal(icon.querySelector('script'),null);assert.equal(icon.querySelector('image'),null);});
test('closed native dropdown presentation is not confused with withdrawn access',()=>{const p=setup();p.a.parentElement.setAttribute('inert','');p.a.parentElement.setAttribute('aria-hidden','true');p.instance.open();assert.match(p.list.textContent,/Market Dashboard/);});
test('explicitly hidden non-panel source sections are not projected',()=>{const p=setup();const section=p.d.createElement('section');section.hidden=true;p.a.parentElement.appendChild(section);section.appendChild(p.a);p.instance.open();assert.doesNotMatch(p.list.textContent,/Market Dashboard/);});
test('new-tab destination explains that behavior accessibly',()=>{const p=setup();p.a.target='_blank';p.instance.open();const a=p.list.querySelector('a');assert.match(a.getAttribute('aria-label')||a.textContent,/new tab/);});

function sourceTopic(p, anchor, en, zh) {
 const menu=anchor.parentElement, section=p.d.createElement('section');
 section.className='nav-mega-section';
 const heading=p.d.createElement('h2');heading.className='nav-mega-h';
 for(const [lang,value] of [['en',en],['zh',zh]]){
  const label=p.d.createElement('span');label.className='l-'+lang;label.textContent=value;heading.appendChild(label);
 }
 section.appendChild(heading);menu.appendChild(section);section.appendChild(anchor);
}
test('source section topic reaches rendered results without a copied taxonomy',()=>{
 const p=setup();sourceTopic(p,p.b,'Capital & regimes','资本与周期');
 p.instance.open();p.query.value='capital regimes';p.query.fire('input');
 assert.equal(p.list.querySelectorAll('a').length,1);
 assert.equal(p.list.querySelector('a').href,'https://www.mastermind-x.com/reports.html');
 assert.match(p.list.textContent,/Capital & regimes/);
 p.d.documentElement.setAttribute('data-lang','zh');p.d.fire('langchange');
 assert.equal(p.query.value,'capital regimes');assert.match(p.list.textContent,/资本与周期/);
});
test('Chinese topic composition keeps the unfinished query out of results',()=>{
 const p=setup();sourceTopic(p,p.b,'Capital & regimes','资本与周期');
 p.instance.open();p.query.fire('compositionstart');p.query.value='资本';p.query.fire('input');
 assert.match(p.list.textContent,/Market Dashboard/);
 p.query.fire('compositionend');assert.equal(p.list.querySelectorAll('a').length,1);
 assert.equal(p.list.querySelector('a').href,'https://www.mastermind-x.com/reports.html');
});
test('topic redraw cannot revive a withdrawn destination',()=>{
 const p=setup();sourceTopic(p,p.b,'Capital & regimes','资本与周期');
 p.instance.open();p.query.value='capital';p.query.fire('input');p.b.remove();
 p.query.value='regimes';p.query.fire('input');const link=p.list.querySelector('a');
 assert.ok(link);assert.equal(link.hasAttribute('href'),false);
 assert.equal(link.getAttribute('aria-disabled'),'true');
 assert.equal(p.list.fire('click',{target:link}).prevented,true);
 assert.equal(p.d.defaultView.location.pathname,'/macro.html');
});

// Mobile chooser contracts use the production owner. This double records
// state/focus/scroll intent; it does not establish layout or actual OS IME proof.
function phone(){const p=setup({phone:true});p.trigger.focus();p.instance.open();p.toggle=p.host.querySelector('[data-tools-category-toggle]');return p;}
function choose(p,key){if(p.categories.hidden)p.toggle.fire('click');const b=p.categories.querySelectorAll('button').find(x=>x.dataset.toolsGroup===key);assert.ok(b,key);p.categories.fire('click',{target:b});}
test('old pilot hosts gain one collapsed chooser without another category list',()=>{
 const p=phone();assert.ok(p.toggle);assert.equal(p.categories.contains(p.toggle),false);
 assert.equal(p.toggle.getAttribute('aria-controls'),p.categories.getAttribute('id'));
 assert.equal(p.toggle.getAttribute('aria-expanded'),'false');assert.equal(p.categories.hidden,true);
 assert.equal(p.toggle.textContent,'Start here');assert.equal(p.d.activeElement,p.title);
 Nav.mount(p.host);assert.equal(p.host.querySelectorAll('[data-tools-category-toggle]').length,1);
});
test('global query and Clear retain the prior Research category',()=>{
 const p=phone();choose(p,'Research');assert.equal(p.toggle.textContent,'Research');
 p.query.focus();p.query.value='dashboard';p.query.fire('input');assert.equal(p.toggle.textContent,'All categories');
 assert.match(p.list.textContent,/Market Dashboard/);assert.doesNotMatch(p.list.textContent,/Research Reports/);
 p.clear.fire('click');assert.equal(p.query.value,'');assert.equal(p.toggle.textContent,'Research');
 assert.match(p.list.textContent,/Research Reports/);assert.doesNotMatch(p.list.textContent,/Market Dashboard/);assert.equal(p.d.activeElement,p.query);
});
test('whitespace query does not mislabel the current category as a global search',()=>{
 const p=phone();choose(p,'Research');p.query.value=' \u3000 ';p.query.fire('input');
 assert.equal(p.toggle.textContent,'Research');assert.match(p.list.textContent,/Research Reports/);
});
test('choosing a category during search clears only the directory query',()=>{
 const p=phone(),source=p.root.textContent;choose(p,'Research');p.query.value='research';p.query.fire('input');
 choose(p,'United States');assert.equal(p.query.value,'');assert.equal(p.toggle.textContent,'United States');
 assert.equal(p.categories.hidden,true);assert.equal(p.d.activeElement,p.toggle);assert.equal(p.root.textContent,source);
 assert.equal(p.d.defaultView.location.pathname,'/macro.html');assert.match(p.list.textContent,/Market Dashboard/);
});
test('All destinations from a scrolled mobile footer restores visible-control focus',()=>{
 const p=phone();p.dialog.scrollTop=900;p.all.focus();p.all.fire('click');
 assert.equal(p.dialog.scrollTop,0);assert.equal(p.toggle.textContent,'All destinations');
 assert.equal(p.d.activeElement,p.toggle);assert.equal(p.list.querySelectorAll('a').length,2);
});
test('empty-state recovery chooses all destinations and focuses search',()=>{
 const p=phone();choose(p,'Research');p.query.value='no such destination';p.query.fire('input');
 const reset=p.list.querySelector('[data-tools-reset]');reset.focus();p.list.fire('click',{target:reset});
 assert.equal(p.toggle.textContent,'All destinations');assert.equal(p.query.value,'');
 assert.equal(p.d.activeElement,p.query);assert.equal(p.list.querySelectorAll('a').length,2);
});
test('first keyboard Escape closes the chooser, next cancel closes the original dialog',()=>{
 const p=phone();p.toggle.fire('click');p.categories.querySelector('button').focus();
 const first=p.dialog.fire('keydown',{key:'Escape'});assert.equal(first.prevented,true);assert.equal(first.stopped,true);
 assert.equal(p.dialog.open,true);assert.equal(p.categories.hidden,true);assert.equal(p.d.activeElement,p.toggle);
 p.dialog.fire('keyup',{key:'Escape'});p.dialog.fire('cancel');assert.equal(p.dialog.open,false);assert.equal(p.d.activeElement,p.trigger);
});
test('native cancel has the same two-level disclosure ownership',()=>{
 const p=phone();p.toggle.fire('click');const first=p.dialog.fire('cancel');
 assert.equal(first.prevented,true);assert.equal(first.stopped,true);assert.equal(p.dialog.open,true);assert.equal(p.d.activeElement,p.toggle);
 p.dialog.fire('cancel');assert.equal(p.dialog.open,false);assert.equal(p.d.activeElement,p.trigger);
});
test('toggle collapse repairs category focus even without pointer focus transfer',()=>{
 const p=phone();p.toggle.fire('click');p.categories.querySelector('button').focus();p.toggle.fire('click');
 assert.equal(p.categories.hidden,true);assert.equal(p.d.activeElement,p.toggle);assert.equal(p.dialog.open,true);
});
test('repeated Escape cannot consume both levels during one physical press',()=>{
 const p=phone();p.toggle.fire('click');p.dialog.fire('keydown',{key:'Escape'});
 const repeat=p.dialog.fire('keydown',{key:'Escape',repeat:true});assert.equal(repeat.prevented,true);assert.equal(repeat.stopped,true);
 p.dialog.fire('cancel');assert.equal(p.dialog.open,true);assert.equal(p.categories.hidden,true);
 p.dialog.fire('keyup',{key:'Escape'});p.dialog.fire('keydown',{key:'Escape'});p.dialog.fire('cancel');assert.equal(p.dialog.open,false);
});
test('expanded locale repaint preserves stable group focus and expansion',()=>{
 const p=phone();choose(p,'Research');p.toggle.fire('click');
 p.categories.querySelectorAll('button').find(b=>b.dataset.toolsGroup==='Research').focus();
 p.d.documentElement.setAttribute('data-lang','zh');p.d.fire('langchange');
 assert.equal(p.toggle.textContent,'研究');assert.equal(p.toggle.getAttribute('aria-expanded'),'true');assert.equal(p.categories.hidden,false);
 assert.equal(p.d.activeElement.dataset.toolsGroup,'Research');assert.equal(p.d.activeElement.isConnected,true);
 assert.equal(p.d.activeElement.getAttribute('aria-pressed'),'true');
});
test('global Chinese label leaves the original category available after Clear',()=>{
 const p=phone();choose(p,'Research');p.query.value='market';p.query.fire('input');p.query.focus();
 p.d.documentElement.setAttribute('data-lang','zh');p.d.fire('langchange');
 assert.equal(p.toggle.textContent,'所有分类');assert.equal(p.d.activeElement,p.query);
 p.clear.fire('click');assert.equal(p.toggle.textContent,'研究');
});
test('a locale repaint does not restore focus into a collapsed category region',()=>{
 const p=phone();const hidden=p.categories.querySelectorAll('button').find(b=>b.dataset.toolsGroup==='Research');hidden.focus();
 p.d.documentElement.setAttribute('data-lang','zh');p.d.fire('langchange');
 assert.equal(p.d.activeElement,p.toggle);assert.equal(p.categories.hidden,true);
});
test('desktop retains the visible existing categories and footer focus',()=>{
 const p=setup();p.instance.open();const toggle=p.host.querySelector('[data-tools-category-toggle]');
 assert.equal(toggle.hidden,true);assert.equal(p.categories.hidden,false);p.all.focus();p.all.fire('click');assert.equal(p.d.activeElement,p.all);
});
test('mobile to desktop repairs a hidden toggle to its retained category',()=>{
 const p=phone();choose(p,'Research');p.query.value='market';p.query.fire('input');p.toggle.focus();p.dialog.scrollTop=700;p.list.scrollTop=80;
 p.viewport(false);assert.equal(p.toggle.hidden,true);assert.equal(p.categories.hidden,false);
 assert.equal(p.d.activeElement.dataset.toolsGroup,'Research');assert.equal(p.dialog.scrollTop,0);assert.equal(p.list.scrollTop,0);
});
test('desktop to mobile repairs only a newly hidden category focus',()=>{
 const p=setup();p.instance.open();p.categories.querySelector('button').focus();p.list.scrollTop=400;
 p.viewport(true);const toggle=p.host.querySelector('[data-tools-category-toggle]');
 assert.equal(p.categories.hidden,true);assert.equal(p.d.activeElement,toggle);assert.equal(p.list.scrollTop,0);
});
test('viewport transition retains result focus and requests nearest visibility',()=>{
 const p=phone(),a=p.list.querySelector('a');a.focus();const count=a.focusCount;p.dialog.scrollTop=700;
 p.viewport(false);p.viewport(true);assert.equal(p.d.activeElement,a);assert.equal(a.focusCount,count);
 assert.deepEqual(a.scrollOptions,{block:'nearest',inline:'nearest'});assert.equal(p.dialog.scrollTop,0);
});
test('viewport changes do not steal unrelated or closed-dialog focus',()=>{
 const p=phone();p.b.focus();const count=p.b.focusCount;p.viewport(false);assert.equal(p.d.activeElement,p.b);assert.equal(p.b.focusCount,count);
 p.instance.close();p.b.focus();p.viewport(true);assert.equal(p.d.activeElement,p.b);assert.equal(p.toggle.getAttribute('aria-expanded'),'false');
});
test('viewport callback uses the current query rather than a queued event value',()=>{
 const p=phone();p.toggle.focus();p.media.matches=false;p.media.listeners[0]({matches:true});
 assert.equal(p.toggle.hidden,true);assert.equal(p.categories.hidden,false);assert.equal(p.d.activeElement.dataset.toolsGroup,'start');
});
test('an IME-origin Escape survives compositionend before native cancel',()=>{
 const p=phone();p.toggle.fire('click');p.query.focus();p.query.fire('compositionstart');
 const key=p.dialog.fire('keydown',{key:'Escape',isComposing:true});assert.equal(key.prevented,false);assert.equal(key.stopped,true);
 p.query.fire('compositionend');p.query.fire('input');p.dialog.fire('cancel');p.query.fire('input');
 assert.equal(p.dialog.open,true);assert.equal(p.categories.hidden,false);assert.equal(p.d.activeElement,p.query);
 p.dialog.fire('keyup',{key:'Escape'});p.dialog.fire('keydown',{key:'Escape'});assert.equal(p.categories.hidden,true);assert.equal(p.dialog.open,true);
 p.dialog.fire('keyup',{key:'Escape'});p.dialog.fire('keydown',{key:'Escape'});p.dialog.fire('cancel');assert.equal(p.dialog.open,false);
});
test('an IME Escape without native cancel cannot swallow the next ordinary Escape',()=>{
 const p=phone();p.toggle.fire('click');p.dialog.fire('keydown',{key:'Escape',isComposing:true});p.dialog.fire('keyup',{key:'Escape'});
 p.dialog.fire('keydown',{key:'Escape'});assert.equal(p.categories.hidden,true);assert.equal(p.dialog.open,true);
});
test('repeated IME-origin Escape retains its owner after compositionend',()=>{
 const p=phone();p.toggle.fire('click');p.query.focus();p.query.fire('compositionstart');p.dialog.fire('keydown',{key:'Escape',isComposing:true});
 p.query.fire('compositionend');p.query.fire('input');const repeat=p.dialog.fire('keydown',{key:'Escape',repeat:true});
 assert.equal(repeat.prevented,false);assert.equal(repeat.stopped,true);p.dialog.fire('cancel');
 assert.equal(p.categories.hidden,false);assert.equal(p.dialog.open,true);assert.equal(p.d.activeElement,p.query);
 p.dialog.fire('keyup',{key:'Escape'});p.dialog.fire('keydown',{key:'Escape'});assert.equal(p.categories.hidden,true);assert.equal(p.dialog.open,true);
});
test('an IME Process keyup ends the composition-Escape reservation',()=>{
 const p=phone();p.toggle.fire('click');p.dialog.fire('keydown',{key:'Escape',isComposing:true});
 p.dialog.fire('keyup',{key:'Process'});p.dialog.fire('cancel');assert.equal(p.categories.hidden,true);assert.equal(p.dialog.open,true);
});
test('another key ends a composition-Escape reservation after a lost keyup',()=>{
 const p=phone();p.toggle.fire('click');p.dialog.fire('keydown',{key:'Escape',isComposing:true});
 p.dialog.fire('keydown',{key:'Tab'});p.dialog.fire('cancel');assert.equal(p.categories.hidden,true);assert.equal(p.dialog.open,true);
});
test('locale and viewport changes do not render an unfinished composition',()=>{
 const p=phone();choose(p,'Research');p.query.focus();const before=p.list.textContent;
 p.query.fire('compositionstart');p.query.value='market';p.query.fire('input');p.d.documentElement.setAttribute('data-lang','zh');p.d.fire('langchange');p.viewport(false);p.viewport(true);
 assert.equal(p.list.textContent,before);assert.equal(p.toggle.textContent,'Research');assert.equal(p.d.activeElement,p.query);
 p.query.fire('compositionend');assert.equal(p.toggle.textContent,'所有分类');assert.match(p.list.textContent,/市场看板/);assert.equal(p.d.activeElement,p.query);
});
test('the inline chooser does not intercept unrelated pointer actions',()=>{
 const p=phone();p.toggle.fire('click');p.query.focus();const event=p.dialog.fire('pointerdown',{target:p.query});
 assert.equal(event.prevented,false);assert.equal(p.categories.hidden,false);assert.equal(p.d.activeElement,p.query);
});
for(const event of ['click','auxclick','contextmenu'])test('mobile category and locale redraw cannot revive withdrawal before '+event,()=>{
 const p=phone();choose(p,'Research');p.b.remove();p.query.value='research';p.query.fire('input');p.clear.fire('click');
 p.d.documentElement.setAttribute('data-lang','zh');p.d.fire('langchange');p.toggle.fire('click');choose(p,'Research');
 const a=p.list.querySelector('a');assert.equal(a.hasAttribute('href'),false);assert.equal(p.list.fire(event,{target:a}).prevented,true);
 assert.equal(p.toggle.textContent,'研究');
});
test('real close resets the chooser and explicit reopen refreshes the source once',()=>{
 const p=phone();p.toggle.fire('click');p.instance.close();assert.equal(p.toggle.getAttribute('aria-expanded'),'false');
 p.anchor({href:'new.html',en:'New tool',group:'New group'});p.instance.open();
 assert.equal(p.categories.hidden,true);assert.equal(p.toggle.textContent,'Start here');assert.ok(p.categories.querySelectorAll('button').some(b=>b.dataset.toolsGroup==='New group'));
 p.toggle.fire('click');p.dialog.fire('close');assert.equal(p.categories.hidden,false);assert.equal(p.dialog.open,true);
});
test('every source category remains present in the one expanded chooser',()=>{
 const p=setup({phone:true});for(const group of ['China','Hong Kong','Crypto','Futures','Learning'])p.anchor({href:group.replace(/ /g,'-')+'.html',en:group+' workspace',group});
 p.instance.open();const toggle=p.host.querySelector('[data-tools-category-toggle]');toggle.fire('click');
 const choices=p.categories.querySelectorAll('button');assert.equal(choices.length,9);assert.equal(choices[0].dataset.toolsGroup,'start');assert.equal(choices.at(-1).dataset.toolsGroup,'all');
 assert.equal(new Set(choices.map(b=>b.dataset.toolsGroup)).size,9);assert.equal(p.host.querySelectorAll('[data-tools-categories]').length,1);
});
