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
