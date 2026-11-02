/* gmi.js — GMI explorer behaviour. Ported from mockups/refs/gmi_explorer/build_specimens.py
   (HASH_JS lens part, TABS_JS, JUMP_JS, INDEX_JS) per mockups/refs/gmi_explorer/SPECS.md §9/§11.
   Loaded `defer` after theme.js. Presentation only: no style injection, no theme/lang mutation
   (theme.js owns those), no network, no storage. Bilingual labels are swapped in markup by the
   .l-en/.l-zh classes; this file only mirrors active language into aria-label/placeholder. */
(function(){
'use strict';
var root=document.documentElement;

/* LENS: html[data-gmi-lens] from the URL hash; only coverage|chain accepted, anything
   else ignored. Theme and language are NOT read from the hash: theme.js owns them. */
function applyLens(){
  var ln=new URLSearchParams(location.hash.slice(1)).get('lens');
  if(ln==='coverage'||ln==='chain')root.setAttribute('data-gmi-lens',ln);
}
applyLens();
window.addEventListener('hashchange',applyLens);

/* TABS_JS (specimen, verbatim): lens buttons set the attribute, sync aria-selected,
   and history.replaceState the hash so lens state survives without a navigation. */
(function(){var r=document.documentElement,bs=[].slice.call(document.querySelectorAll('[data-gmi-set-lens]'));
function sync(){bs.forEach(function(b){b.setAttribute('aria-selected',String(r.getAttribute('data-gmi-lens')===b.getAttribute('data-gmi-set-lens')));});}
bs.forEach(function(b){b.addEventListener('click',function(){var v=b.getAttribute('data-gmi-set-lens');r.setAttribute('data-gmi-lens',v);sync();
var h=new URLSearchParams(location.hash.slice(1));h.set('lens',v);history.replaceState(null,'','#'+h.toString());});});sync();})();

/* JUMP_JS (specimen, verbatim): jump-nav intercepts chip clicks (scrollIntoView, never a
   hash navigation, so lens state is not clobbered) and tracks the current category. */
(function(){var nav=document.querySelector('.gmi-jump');if(!nav)return;
var tr=nav.querySelector('.gmi-jump-track'),links=[].slice.call(nav.querySelectorAll('a'));
links.forEach(function(a){a.addEventListener('click',function(e){var g=document.getElementById(a.getAttribute('href').slice(1));
if(!g)return;e.preventDefault();g.setAttribute('open','');g.scrollIntoView({block:'start'});});});
if(!('IntersectionObserver' in window))return;var cur=null;
var io=new IntersectionObserver(function(es){es.forEach(function(en){if(!en.isIntersecting)return;var id=en.target.id;
links.forEach(function(a){var on=a.getAttribute('href')==='#'+id;if(on)a.setAttribute('aria-current','true');else a.removeAttribute('aria-current');
if(on&&cur!==a){cur=a;if(tr.scrollWidth>tr.clientWidth)tr.scrollLeft=a.offsetLeft-16;}});});},{rootMargin:'-60px 0px -70% 0px'});
[].forEach.call(document.querySelectorAll('[data-gmi-index] > details'),function(g){io.observe(g);});})();

/* INDEX_JS (specimen, verbatim): on phones collapse all index groups but the first,
   unless the hash carries open=all. */
(function(){var gs=[].slice.call(document.querySelectorAll('[data-gmi-index] > details'));
var all=new URLSearchParams(location.hash.slice(1)).get('open')==='all';
if(!all&&window.matchMedia('(max-width:640px)').matches){gs.forEach(function(g,i){if(i>0)g.removeAttribute('open');});}})();

/* TREE ACCORDION + SEARCH (orchestrator rulings G-UI-11/G-UI-12). The S2 tree renders EVERY
   row; rows under a closed parent carry `hidden`. Rows declare their place with
   data-gmi-tree-id / data-gmi-tree-parent, and every searchable row carries data-gmi-q
   ("<en> <zh>"). A search box is input[data-gmi-filter=<scope>]: scope "index" filters the
   [data-gmi-index] rows, any other scope filters the .gmi-tree rows. Its no-match line is
   [data-gmi-nomatch=<scope>]. The "See all" row (.gmi-trow--more) is never touched. */
(function(){
function norm(s){return String(s||'').toLowerCase().replace(/\s+/g,' ').trim();}
function hit(el,q){return norm(el.getAttribute('data-gmi-q')).indexOf(q)!==-1;}
function noMatch(scope,on){[].forEach.call(document.querySelectorAll('[data-gmi-nomatch="'+scope+'"]'),function(p){p.hidden=!on;});}

/* ---- tree ---- */
var tree=document.querySelector('.gmi-tree');
var trows=tree?[].slice.call(tree.querySelectorAll('[data-gmi-tree-id],[data-gmi-tree-parent]')):[];
var byId={};trows.forEach(function(r){var id=r.getAttribute('data-gmi-tree-id');if(id)byId[id]=r;});
function parent(r){var p=r.getAttribute('data-gmi-tree-parent');return p&&byId[p]?byId[p]:null;}
function expandable(r){return r.hasAttribute('aria-expanded');}
function isOpen(r){return r.getAttribute('aria-expanded')==='true';}
function setOpen(r,on){if(!expandable(r))return;r.setAttribute('aria-expanded',String(on));r.classList.toggle('gmi-trow--open',on);}
var tq='',snap=null;
function treeRender(){
  var keep=null,n=0;
  if(tq){keep={};trows.forEach(function(r){if(!hit(r,tq))return;n++;
    for(var a=r;a;a=parent(a)){keep[a.getAttribute('data-gmi-tree-id')||('#'+trows.indexOf(a))]=true;}});}
  trows.forEach(function(r){var vis=true;
    if(keep&&!keep[r.getAttribute('data-gmi-tree-id')||('#'+trows.indexOf(r))])vis=false;
    for(var a=parent(r);vis&&a;a=parent(a)){if(!isOpen(a))vis=false;}
    r.hidden=!vis;});
  noMatch('tree',!!tq&&n===0);
  var items=visibleItems();
  if(items.length&&!items.some(function(r){return r.tabIndex===0;})){
    trows.forEach(function(r){if(r.getAttribute('role')==='treeitem')r.tabIndex=-1;});items[0].tabIndex=0;}
}
function visibleItems(){return tree?[].slice.call(tree.querySelectorAll('[role="treeitem"]')).filter(function(r){return !r.hidden;}):[];}
function focusItem(r){if(!r)return;visibleItems().forEach(function(x){x.tabIndex=-1;});r.tabIndex=0;r.focus();}
function toggle(r){setOpen(r,!isOpen(r));treeRender();}
if(tree){
  tree.addEventListener('click',function(e){var r=e.target.closest('[role="treeitem"]');
    if(!r||!tree.contains(r)||e.target.closest('a,button,input'))return;
    if(expandable(r))toggle(r);focusItem(r);});
  tree.addEventListener('keydown',function(e){var r=e.target.closest('[role="treeitem"]');if(!r||e.target!==r)return;
    var items=visibleItems(),i=items.indexOf(r),k=e.key;
    if(k==='Enter'||k===' '){if(expandable(r)){e.preventDefault();toggle(r);}}
    else if(k==='ArrowDown'){e.preventDefault();focusItem(items[i+1]);}
    else if(k==='ArrowUp'){e.preventDefault();focusItem(items[i-1]);}
    else if(k==='Home'){e.preventDefault();focusItem(items[0]);}
    else if(k==='End'){e.preventDefault();focusItem(items[items.length-1]);}
    else if(k==='ArrowRight'){e.preventDefault();if(expandable(r)&&!isOpen(r))toggle(r);else if(isOpen(r))focusItem(visibleItems()[i+1]);}
    else if(k==='ArrowLeft'){e.preventDefault();if(expandable(r)&&isOpen(r))toggle(r);else focusItem(parent(r));}});
  treeRender();
}

/* ---- index ---- */
var idx=document.querySelector('[data-gmi-index]');
var groups=idx?[].slice.call(idx.querySelectorAll(':scope > details')):[];
var iq='',isnap=null;
function indexRender(){
  var n=0;
  groups.forEach(function(g){var any=false,h=null,hv=false;
    [].forEach.call(g.children,function(el){
      if(el.tagName==='SUMMARY')return;
      if(el.classList.contains('gmi-index-t')){if(h)h.hidden=!!iq&&!hv;h=el;hv=false;return;}
      var m=!iq||(el.hasAttribute('data-gmi-q')&&hit(el,iq));
      el.hidden=!m;if(m&&el.hasAttribute('data-gmi-q')){hv=true;any=true;if(iq)n++;}});
    if(h)h.hidden=!!iq&&!hv;
    g.hidden=!!iq&&!any;
    if(iq&&any)g.setAttribute('open','');});
  noMatch('index',!!iq&&n===0);
}

/* ---- inputs ---- */
var inputs=[].slice.call(document.querySelectorAll('input[data-gmi-filter]'));
inputs.forEach(function(inp){
  var scope=inp.getAttribute('data-gmi-filter');
  inp.addEventListener('input',function(){var q=norm(inp.value);
    if(scope==='index'){
      if(q&&!iq)isnap=groups.map(function(g){return g.hasAttribute('open');});
      iq=q;indexRender();
      if(!q&&isnap){groups.forEach(function(g,i){if(isnap[i])g.setAttribute('open','');else g.removeAttribute('open');});isnap=null;}
    }else{
      if(q&&!tq)snap=trows.map(function(r){return isOpen(r);});
      tq=q;
      if(q){trows.forEach(function(r){if(!hit(r,q))return;for(var a=parent(r);a;a=parent(a))setOpen(a,true);});}
      else if(snap){trows.forEach(function(r,i){setOpen(r,snap[i]);});snap=null;}
      treeRender();
    }});
  inp.addEventListener('keydown',function(e){if(e.key==='Escape'&&inp.value){e.preventDefault();inp.value='';
    inp.dispatchEvent(new Event('input'));}});
});
/* "/" focuses the page's first search box unless the user is already typing somewhere. */
if(inputs.length){document.addEventListener('keydown',function(e){
  if(e.key!=='/'||e.metaKey||e.ctrlKey||e.altKey)return;
  var a=document.activeElement;
  if(a&&(a.isContentEditable||/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)))return;
  e.preventDefault();inputs[0].focus();});}
})();

/* ARIA/PLACEHOLDER SWAP: mirror the active language (html[data-lang], owned by theme.js)
   into aria-label / placeholder. Never touches title. Run on load, on the langchange
   event theme.js dispatches on document, and from a data-lang MutationObserver. */
function apply(){
  var lang=root.getAttribute('data-lang')==='zh'?'zh':'en';
  [].slice.call(document.querySelectorAll('[data-aria-en],[data-aria-zh]')).forEach(function(el){
    var v=el.getAttribute('data-aria-'+lang);if(v!==null)el.setAttribute('aria-label',v);});
  [].slice.call(document.querySelectorAll('[data-ph-en],[data-ph-zh]')).forEach(function(el){
    var v=el.getAttribute('data-ph-'+lang);if(v!==null)el.setAttribute('placeholder',v);});
}
apply();
document.addEventListener('langchange',apply);
if('MutationObserver' in window){
  new MutationObserver(apply).observe(root,{attributes:true,attributeFilter:['data-lang']});
}

/* SPECS §10 state keys, in table order — the single state enum for the explorer. */
window.GMI_STATES=Object.freeze(['fetch_failed','stale','rights_withheld','purpose_denied','source_paused','unknown','loading','empty','read_updated','path_template']);
})();
