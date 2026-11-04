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
  root.setAttribute('data-gmi-lens',ln==='chain'?'chain':'coverage');document.querySelectorAll('[data-gmi-set-lens]').forEach(function(b){b.setAttribute('aria-selected',String(b.getAttribute('data-gmi-set-lens')===root.getAttribute('data-gmi-lens')));});
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
/* Keep index search in the same fragment as lens/open/return context. */
function setIndexQuery(value){
  var q=norm(value);
  if(q&&!iq)isnap=groups.map(function(g){return g.hasAttribute('open');});
  iq=q;indexRender();
  if(!q&&isnap){groups.forEach(function(g,i){if(isnap[i])g.setAttribute('open','');else g.removeAttribute('open');});isnap=null;}
}
var indexInput=document.querySelector('input[data-gmi-filter="index"]');
function restoreIndex(){if(!indexInput)return;indexInput.value=(new URLSearchParams(location.hash.slice(1)).get('q')||'').slice(0,200);setIndexQuery(indexInput.value);}
if(indexInput){indexInput.maxLength=200;restoreIndex();window.addEventListener('hashchange',restoreIndex);window.addEventListener('popstate',restoreIndex);}
var inputs=[].slice.call(document.querySelectorAll('input[data-gmi-filter]'));
inputs.forEach(function(inp){
  var scope=inp.getAttribute('data-gmi-filter');
  inp.addEventListener('input',function(){var q=norm(inp.value);
    if(scope==='index'){
      setIndexQuery(q);
      var params=new URLSearchParams(location.hash.slice(1)),raw=inp.value.slice(0,200);
      if(raw)params.set('q',raw);else params.delete('q');
      history.replaceState(null,'',location.pathname+location.search+(params.size?'#'+params.toString():''));
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

/* Preserve the existing state keys and add confirmed-action success feedback. */
window.GMI_STATES=Object.freeze(['fetch_failed','stale','rights_withheld','purpose_denied','source_paused','unknown','loading','empty','read_updated','path_template','success']);
})();

/* Answer-first research. The existing theme controller owns theme and language.
   URL state owns research selection/filters; no new storage or data authority. */
(function(){
'use strict';
var root=document.documentElement;
var lang=function(){return root.getAttribute('data-lang')==='zh'?'zh':'en';};
var tr=function(en,zh){return lang()==='zh'?zh:en;};
var txt=function(value){return value==null?'':String(value);};
var norm=function(value){return txt(value).normalize('NFKC').toLocaleLowerCase().replace(/\s+/g,' ').trim();};
function el(tag,cls,text){var n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=txt(text);return n;}
function icon(kind){var s=document.createElementNS('http://www.w3.org/2000/svg','svg');s.setAttribute('viewBox','0 0 24 24');s.setAttribute('width','16');s.setAttribute('height','16');s.setAttribute('fill','none');s.setAttribute('stroke','currentColor');s.setAttribute('stroke-width','1.8');s.setAttribute('stroke-linecap','round');s.setAttribute('stroke-linejoin','round');s.setAttribute('aria-hidden','true');var p=document.createElementNS(s.namespaceURI,'path');p.setAttribute('d',kind==='ext'?'M14 4.5h5.5V10M19.5 4.5L11 13M17.5 14v5.5h-13v-13H10':kind==='back'?'M19.5 12h-15M10.5 6l-6 6 6 6':'M4.5 12h15M13.5 6l6 6-6 6');s.append(p);return s;}
function date(value){var parsed=new Date(txt(value).slice(0,10)+'T00:00:00Z');return Number.isNaN(parsed.getTime())?tr('Date not recorded','日期未记录'):new Intl.DateTimeFormat(lang()==='zh'?'zh-CN':'en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(parsed);}
function stage(value){var words={planned:['Planned','计划中'],announced:['Announced','已宣布'],in_production:['In production','量产中'],terminated:['Ended','已终止'],active:['Active in source','来源记载有效']};var v=words[value]||['Stage not recorded','阶段未记录'];return tr(v[0],v[1]);}
function link(label,href,cls,external){var a=el('a',cls,label);try{var u=new URL(href,location.href);if(u.protocol!=='http:'&&u.protocol!=='https:')throw new Error('protocol');a.href=u.href;}catch(e){return el('span','gmi-muted',label);}if(external){a.target='_blank';a.rel='noopener noreferrer';a.append(icon('ext'),el('span','gmi-vh',tr(' opens a new tab',' 在新标签页打开')));}return a;}
function languageOptions(){document.querySelectorAll('[data-option-en]').forEach(function(o){o.textContent=o.getAttribute('data-option-'+lang());});}
languageOptions();
/* Reparent the existing shared launcher; its loader, identity, state and API
   remain owned by theme.js / MMBrain. No second launcher or loading loop. */
function dockBrain(){var slot=document.getElementById('gmi-brain-slot'),component=document.getElementById('mmb-root')||document.getElementById('mmb-boot');if(slot&&component&&component.parentNode!==slot)slot.append(component);}
dockBrain();
document.addEventListener('DOMContentLoaded',dockBrain,{once:true});
window.addEventListener('mm-brain-ready',dockBrain);
document.querySelectorAll('[data-gmi-snapshot]').forEach(function(n){var d=new Date(n.getAttribute('data-gmi-snapshot').slice(0,10)+'T00:00:00Z');var age=Date.now()-d.getTime();var label=n.querySelector('.gmi-snapshot-stale');if(label&&Number.isFinite(age))label.hidden=age<=7*86400000;});

/* Research context stays in the existing URL state. Only two local return routes
   and their presentation keys are accepted; fragments keep search out of requests.
   A catalogue may carry one upstream theme return, never an arbitrary stack. */
function safeReturn(value,nested){
  if(typeof value!=='string'||value.length>4096)return '';
  var route=/^(gmi(?:-companies)?\.html)(?:#([^\r\n]*))?$/.exec(value);if(!route)return '';
  var input=new URLSearchParams(route[2]||''),output=new URLSearchParams();
  function copy(key,valid){var v=input.get(key);if(v&&valid(v))output.set(key,v);}
  if(route[1]==='gmi.html'){
    ['theme','category'].forEach(function(key){copy(key,function(v){return /^[a-z0-9_:.-]{1,160}$/i.test(v);});});
    copy('scope',function(v){return v==='core'||v==='extended';});
    copy('evidence',function(v){return v==='1';});
    copy('lens',function(v){return v==='coverage'||v==='chain';});
  }else if(!nested){
    var upstream=safeReturn(input.get('gmi_return'),true);
    if(upstream.split('#')[0]==='gmi.html')output.set('gmi_return',upstream);
  }
  if(input.get('q'))output.set('q',input.get('q').slice(0,200));
  return route[1]+(output.size?'#'+output.toString():'');
}
function localPage(href){try{var u=new URL(href,location.href);if(u.origin===location.origin&&u.pathname.slice(0,u.pathname.lastIndexOf('/')+1)===location.pathname.slice(0,location.pathname.lastIndexOf('/')+1))return u.pathname.split('/').pop();}catch(error){}return '';}
var originalHrefs=new WeakMap();
function contextPage(page){return ['gmi-coverage.html','gmi-index.html','gmi-relationships.html','gmi-states.html'].includes(page);}
function refreshJourney(){
  var current=localPage(location.href),inherited=safeReturn(new URLSearchParams(location.hash.slice(1)).get('gmi_return'));
  if(current==='gmi-companies.html'&&inherited.split('#')[0]!=='gmi.html')inherited='';
  var source=current==='gmi.html'||current==='gmi-companies.html'?safeReturn(current+location.hash):inherited;
  var catalog=inherited.split('#')[0]==='gmi-companies.html'?inherited:'';
  var research=catalog?safeReturn(new URLSearchParams(catalog.split('#')[1]||'').get('gmi_return'),true):inherited;
  if(research.split('#')[0]!=='gmi.html')research='';
  var nav=document.querySelector('.gmi-product-nav'),holder=document.querySelector('.gmi-return-context');
  var back=inherited&&(current==='gmi-companies.html'||contextPage(current)||/^gmi-issuer-[a-z0-9._-]+\.html$/i.test(current));
  if(back&&nav){
    if(!holder){holder=el('div','gmi-return-context');nav.after(holder);}
    var action=holder.querySelector('[data-gmi-return]');if(!action){action=el('a','gmi-action-secondary');action.setAttribute('data-gmi-return','');holder.append(action);}
    action.href=new URL(inherited,location.href).href;
    action.replaceChildren(icon('back'),el('span','',catalog?tr('Back to company results','返回公司结果'):tr('Back to theme research','返回主题研究')));
  }else if(holder)holder.remove();
  document.querySelectorAll('main a[href]:not([data-gmi-return])').forEach(function(a){
    if(!originalHrefs.has(a))originalHrefs.set(a,a.getAttribute('href'));
    var original=originalHrefs.get(a),page=localPage(original),next=original;
    if(source&&(/^gmi-issuer-[a-z0-9._-]+\.html$/i.test(page)||(page==='gmi-companies.html'&&current!=='gmi-companies.html')||(contextPage(page)&&page!==current))){
      if(page==='gmi-companies.html'&&catalog)next=catalog;
      else{var url=new URL(original,location.href),p=new URLSearchParams(url.hash.slice(1));p.set('gmi_return',source);url.hash=p.toString();next=url.href;}
    }else if(research&&page==='gmi.html'&&a.matches('.gmi-product-name,.gmi-product-tabs a'))next=research;
    if(a.getAttribute('href')!==next)a.setAttribute('href',next);
  });
}

/* Company catalogue uses source-rendered cards and the same URL state owner. */
var companySearch=document.querySelector('[data-company-search]');
function companies(){if(!companySearch)return;var q=norm(companySearch.value),count=0;document.querySelectorAll('[data-company-card]').forEach(function(c){c.hidden=!!q&&!norm(c.getAttribute('data-search')).includes(q);if(!c.hidden)count++;});document.querySelector('[data-company-empty]').hidden=count>0;document.querySelector('[data-company-count]').textContent=tr(count+' '+(count===1?'company':'companies')+' with evidence on file','有收录证据的公司：'+count+' 家');}
function restoreCompanies(){if(companySearch){companySearch.value=txt(new URLSearchParams(location.hash.slice(1)).get('q')).slice(0,200);companies();}refreshJourney();}
function updateCompanies(){var p=new URLSearchParams(location.hash.slice(1)),q=companySearch.value.slice(0,200);if(q)p.set('q',q);else p.delete('q');history.replaceState(null,'',location.pathname+location.search+(p.size?'#'+p.toString():''));companies();refreshJourney();}
if(companySearch){companySearch.maxLength=200;companySearch.addEventListener('input',updateCompanies);document.querySelector('[data-company-reset]').addEventListener('click',function(){companySearch.value='';updateCompanies();companySearch.focus();});}
restoreCompanies();
var workspace=document.querySelector('[data-gmi-explorer]');
if(!workspace){window.addEventListener('hashchange',restoreCompanies);window.addEventListener('popstate',restoreCompanies);new MutationObserver(function(){languageOptions();companies();refreshJourney();}).observe(root,{attributes:true,attributeFilter:['data-lang']});return;}
var answer=document.querySelector('[data-topic-answer]'),notice=document.querySelector('[data-topic-notice]'),announcement=document.querySelector('[data-gmi-announcement]');
var data;
/* Validate the complete presentation shape before replacing the server answer.
   This is a rendering guard, not a publication/permission decision. */
function usableData(value){
  function object(v){return v!==null&&typeof v==='object'&&!Array.isArray(v);}
  function string(v){return typeof v==='string'&&v.trim().length>0;}
  function optional(v){return v==null||typeof v==='string';}
  function labelled(v){return object(v)&&string(v.en)&&string(v.zh);}
  if(!object(value)||!object(value.categories)||!Array.isArray(value.topics)||!value.topics.length)return false;
  var cats=value.categories,ids=new Set();
  function categoryExists(id){return string(id)&&Object.prototype.hasOwnProperty.call(cats,id)&&labelled(cats[id]);}
  if(!Object.values(cats).every(labelled))return false;
  if(!value.topics.every(function(t){
    if(!labelled(t)||!string(t.id)||ids.has(t.id)||!['core','extended'].includes(t.tier)||!categoryExists(t.category)||!categoryExists(t.parent)||!optional(t.position))return false;
    ids.add(t.id);
    if(!Array.isArray(t.paths)||!t.paths.length||!t.paths.every(function(path){return Array.isArray(path)&&path.length&&path.every(function(p){return labelled(p)&&categoryExists(p.id);});}))return false;
    return Array.isArray(t.connections)&&t.connections.every(function(c){return object(c)&&string(c.company)&&string(c.ticker)&&string(c.href)&&/^gmi-issuer-[a-z0-9._-]+\.html$/i.test(localPage(c.href))&&['product','platform','lifecycle','receipt'].every(function(key){return optional(c[key]);})&&labelled(c.source)&&['date','url','key','sha256'].every(function(key){return optional(c.source[key]);});});
  }))return false;
  return ids.has(workspace.getAttribute('data-default-theme'))&&Array.from(document.querySelectorAll('[data-topic-results] [data-topic-select]')).every(function(row){return ids.has(row.getAttribute('data-topic-select'));});
}
function loadFailure(){notice.hidden=false;notice.textContent=tr('Interactive research could not load. The answer below and the full index remain available.','交互研究未能加载。下方答案与完整索引仍可使用。');}
try{data=JSON.parse(document.getElementById('gmi-topic-data').textContent);if(!usableData(data))throw new Error('incomplete presentation data');}catch(error){loadFailure();document.querySelector('[data-browse-home]').hidden=true;var fallback=document.querySelector('[data-browse-open]');fallback.addEventListener('click',function(){location.href='gmi-index.html';});answer.querySelector('[data-gmi-copy]').hidden=true;new MutationObserver(function(){languageOptions();loadFailure();refreshJourney();}).observe(root,{attributes:true,attributeFilter:['data-lang']});return;}
var topics=data.topics,byId=new Map(topics.map(function(t){return[t.id,t];}));
var defaults={theme:workspace.getAttribute('data-default-theme'),q:'',category:'',scope:'all',evidence:false};
var state=Object.assign({},defaults),invalidTheme=false,lastHash=null;
var search=document.querySelector('[data-topic-search]'),category=document.querySelector('[data-topic-category-filter]'),evidence=document.querySelector('[data-evidence-only]'),scopes=Array.from(document.querySelectorAll('input[name="gmi-scope"]'));
var results=document.querySelector('[data-topic-results]'),rows=Array.from(results.querySelectorAll('[data-topic-select]'));
var browse=document.querySelector('[data-gmi-browse]'),home=document.querySelector('[data-browse-home]'),dialog=document.querySelector('[data-browse-dialog]'),openButton=document.querySelector('[data-browse-open]');
var mobile=window.matchMedia('(max-width:820px)');
search.maxLength=200;
var searchText=new Map(topics.map(function(t){return[t.id,norm([t.en,t.zh].concat(t.paths.flat().map(function(p){return p.en+' '+p.zh;}),t.connections.map(function(c){return[c.company,c.ticker,c.product,c.platform].join(' ');})).join(' '))];}));
function label(n){return n[lang()]||n.en;}
function announce(message){announcement.textContent=message;}
function readURL(){var p=new URLSearchParams(location.hash.slice(1));var requested=p.get('theme')||defaults.theme;invalidTheme=!byId.has(requested);state={theme:invalidTheme?defaults.theme:requested,q:txt(p.get('q')).slice(0,200),category:category.querySelector('option[value="'+CSS.escape(p.get('category')||'')+'"]')?(p.get('category')||''):'',scope:['core','extended'].includes(p.get('scope'))?p.get('scope'):'all',evidence:p.get('evidence')==='1'};}
function writeURL(mode){var p=new URLSearchParams(location.hash.slice(1));p.set('theme',state.theme);[['q',state.q],['category',state.category],['scope',state.scope==='all'?'':state.scope],['evidence',state.evidence?'1':'']].forEach(function(pair){if(pair[1])p.set(pair[0],pair[1]);else p.delete(pair[0]);});var next='#'+p.toString();if(next!==location.hash)history[mode==='push'?'pushState':'replaceState'](null,'',next);lastHash=location.hash;refreshJourney();}
function matches(t){return(!state.category||t.paths.some(function(path){return path.length&&path[0].id===state.category;}))&&(state.scope==='all'||t.tier===state.scope)&&(!state.evidence||t.connections.length>0)&&(!norm(state.q)||searchText.get(t.id).includes(norm(state.q)));}
function filters(){search.value=state.q;category.value=state.category;evidence.checked=state.evidence;scopes.forEach(function(s){s.checked=s.value===state.scope;});var count=0,firstVisible=null,selectedVisible=null;rows.forEach(function(row){var t=byId.get(row.getAttribute('data-topic-select'));row.hidden=!matches(t);row.tabIndex=-1;if(!row.hidden){count++;if(!firstVisible)firstVisible=row;if(t.id===state.theme)selectedVisible=row;}if(t.id===state.theme)row.setAttribute('aria-current','true');else row.removeAttribute('aria-current');});if(selectedVisible||firstVisible)(selectedVisible||firstVisible).tabIndex=0;document.querySelector('[data-topic-count]').textContent=tr(count+' of '+topics.length+' topics',topics.length+' 个主题中显示 '+count+' 个');document.querySelector('[data-topic-no-results]').hidden=count>0;results.hidden=count===0;var selected=byId.get(state.theme);notice.hidden=!invalidTheme&&matches(selected);answer.querySelector('[data-topic-category]').textContent=label(data.categories[state.category&&selected.paths.some(function(path){return path.length&&path[0].id===state.category;})?state.category:selected.category]);notice.textContent=invalidTheme?tr('That topic is not available in this snapshot. Showing the available starting topic.','此快照中找不到该主题，现显示可用的起始主题。'):tr('Your selected topic is outside these filters. Clear filters to include it.','当前所选主题不在筛选范围内。清除筛选即可显示。');}
function connection(c,t){var card=el('article','gmi-evidence-card');var top=el('div','gmi-evidence-top'),when=el('div','gmi-evidence-date');top.append(el('span','gmi-eyebrow',tr('Documented connection','有据可查的关联')));when.append(el('span','',tr('Source','来源')+' · '+date(c.source.date)),el('span','gmi-stage',stage(c.lifecycle)));top.append(when);card.append(top);
var claim=el('div','gmi-evidence-claim');var shortCompany=c.company==='Micron Technology'?'Micron':c.company,shortProduct=txt(c.product).includes('HBM3E')?'HBM3E':c.product;var headline=(c.product&&c.lifecycle==='planned')?tr(shortCompany+' planned '+shortProduct+(c.platform?' for '+c.platform:'')+'.',shortCompany+' 曾计划'+(c.platform?'将 '+shortProduct+' 用于 '+c.platform:'推出 '+shortProduct)+'。'):c.company+(c.product?' · '+c.product:'');claim.append(el('h2','',headline),el('p','',tr('This dated source names the product and its context. Current delivery and revenue exposure are not established here.','这份有明确日期的来源记载了产品及其背景。当前交付与营收敞口尚未由此证实。')));card.append(claim);
var path=el('ol','gmi-product-path');path.setAttribute('aria-label',tr('Product context','产品背景'));[[tr('Company','公司'),c.company,c.ticker],[tr('Product named','所述产品'),c.product||tr('Not recorded','未记录'),stage(c.lifecycle)],[tr('Platform named','所述平台'),c.platform||tr('Not recorded','未记录'),tr('As stated in the source','按来源所述')]].forEach(function(v){var li=el('li');li.append(el('span','',v[0]),el('strong','',v[1]),el('small','',v[2]));path.append(li);});card.append(path);
var actions=el('div','gmi-evidence-actions'),source=el('div','gmi-source-link');source.append(el('span','',label(c.source)));if(c.source.url)source.append(link(tr('Read the source','阅读来源'),c.source.url,'',true));else source.append(el('span','',tr('Public source link unavailable','暂无公开来源链接')));var company=link(tr('Open company evidence','查看公司证据'),c.href,'gmi-action-primary');company.append(icon());actions.append(company,source);card.append(actions);
var receipt=el('details','gmi-evidence-receipt'),summary=el('summary','',tr('Source receipt','来源凭证'));summary.append(el('span','',tr('record and source identity','记录与来源标识')));var dl=el('dl');[[tr('Record','记录'),c.receipt],[tr('Source key','来源标识'),c.source.key],[tr('Source text hash','来源文本哈希'),c.source.sha256]].forEach(function(v){var row=el('div');row.append(el('dt','',v[0]),el('dd','',v[1]));dl.append(row);});receipt.append(summary,dl);card.append(receipt);return card;}
function renderAnswer(){var t=byId.get(state.theme);answer.querySelector('.gmi-copy-fallback').hidden=true;answer.setAttribute('aria-busy','true');document.getElementById('gmi-topic-title').textContent=label(t);document.title=label(t)+' — GMI Explorer';answer.querySelector('[data-topic-category]').textContent=label(data.categories[state.category&&t.paths.some(function(path){return path.length&&path[0].id===state.category;})?state.category:t.category]);answer.querySelector('[data-topic-tier]').textContent=t.tier==='core'?tr('Core topic','核心主题'):tr('Extended topic','扩展主题');var parent=data.categories[t.parent];answer.querySelector('[data-topic-description]').textContent=/hbm/i.test(t.en)?tr('High-bandwidth memory stacking and its packaging — a distinct part of the AI semiconductor stack.','高带宽内存的堆叠与封装，是 AI 半导体体系中一个独立的环节。'):tr('A topic within '+label(parent)+'. Explore its classification and the company evidence currently on file.','属于“'+label(parent)+'”的主题。查看其分类位置与目前收录的公司证据。');
var cards=answer.querySelector('[data-topic-connections]');cards.replaceChildren();if(t.connections.length){t.connections.forEach(function(c){cards.append(connection(c,t));});}else{var empty=el('section','gmi-topic-empty');empty.append(el('span','gmi-eyebrow',tr('Research coverage','研究覆盖')),el('h2','',tr('No company evidence yet','暂无公司证据')),el('p','',tr('This topic is mapped. A reviewed company connection has not been published here yet.','此主题已列入体系，但此处尚未发布经审核的公司关联。')),el('p','gmi-note',tr('An empty result does not mean no companies participate in this theme.','没有结果并不表示没有公司参与这一主题。')),link(tr('Browse available evidence','浏览现有证据'),'gmi-companies.html','gmi-action-secondary'));cards.append(empty);}
answer.querySelector('[data-topic-coverage]').textContent=tr(t.connections.length+' documented connection'+(t.connections.length===1?'':'s')+' on file.','已收录 '+t.connections.length+' 条有据可查的关联。');var related=answer.querySelector('[data-topic-related]');related.replaceChildren();var parents=new Set(t.paths.filter(function(p){return p.length;}).map(function(p){return p[p.length-1].id;}));var nearby=topics.filter(function(other){return other.id!==t.id&&other.paths.some(function(p){return p.length&&parents.has(p[p.length-1].id);});}).slice(0,3);nearby.forEach(function(other){var a=link(label(other),'#theme='+encodeURIComponent(other.id));a.setAttribute('data-topic-select',other.id);related.append(a);});if(!nearby.length){related.append(link(tr('Browse this category','浏览此类别'),'#theme='+encodeURIComponent(t.id)+'&category='+encodeURIComponent(t.category)));}
var taxonomy=answer.querySelector('[data-topic-taxonomy]');taxonomy.replaceChildren();t.paths.forEach(function(p){taxonomy.append(el('p','',p.map(label).concat(label(t)).join(' › ')));});var positions={upstream:['Upstream','上游'],midstream:['Midstream','中游'],downstream:['Downstream','下游'],enabler:['Enabler','赋能']},position=positions[t.position];taxonomy.append(el('p','',tr('Value-chain position: ','价值链位置：')+(position?tr(position[0],position[1]):tr('Not recorded','未记录'))));taxonomy.append(el('p','',t.tier==='core'?tr('Core topics form the coverage measurement set.','核心主题构成覆盖率衡量集合。'):tr('Extended topics provide orientation and are excluded from core coverage measures.','扩展主题用于帮助浏览，不计入核心覆盖率衡量。')));answer.setAttribute('aria-busy','false');answer.querySelector('[data-copy-label]').textContent=tr('Copy link','复制链接');}
function sync(){languageOptions();filters();renderAnswer();refreshJourney();}
function restore(){if(lastHash===location.hash)return;readURL();lastHash=location.hash;sync();if(invalidTheme)writeURL('replace');}
function closeBrowse(focusTitle){if(dialog.open)dialog.close();if(focusTitle)requestAnimationFrame(function(){document.getElementById('gmi-topic-title').focus({preventScroll:true});document.getElementById('gmi-topic-title').scrollIntoView({block:'start',behavior:'auto'});});}
function select(id,focusAnswer){if(!byId.has(id))return;state.theme=id;invalidTheme=false;writeURL('push');filters();renderAnswer();refreshJourney();closeBrowse(mobile.matches||focusAnswer);announce(tr('Selected: ','已选择：')+label(byId.get(id)));}
document.addEventListener('click',function(event){var a=event.target.closest('[data-topic-select]');if(!a||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey||event.button!==0)return;event.preventDefault();select(a.getAttribute('data-topic-select'),!results.contains(a));});
results.addEventListener('keydown',function(event){var a=event.target.closest('[data-topic-select]');if(!a)return;var visible=rows.filter(function(r){return!r.hidden;}),i=visible.indexOf(a),target;if(event.key==='ArrowDown')target=visible[Math.min(i+1,visible.length-1)];else if(event.key==='ArrowUp')target=visible[Math.max(i-1,0)];else if(event.key==='Home')target=visible[0];else if(event.key==='End')target=visible[visible.length-1];if(target){event.preventDefault();rows.forEach(function(r){r.tabIndex=-1;});target.tabIndex=0;target.focus();}});
function updateFilters(){state.q=search.value.slice(0,200);state.category=category.value;state.scope=scopes.find(function(s){return s.checked;}).value;state.evidence=evidence.checked;invalidTheme=false;writeURL('replace');filters();answer.querySelector('[data-topic-category]').textContent=label(data.categories[state.category&&byId.get(state.theme).paths.some(function(path){return path.length&&path[0].id===state.category;})?state.category:byId.get(state.theme).category]);}
search.addEventListener('input',updateFilters);category.addEventListener('change',updateFilters);evidence.addEventListener('change',updateFilters);scopes.forEach(function(s){s.addEventListener('change',updateFilters);});
document.querySelectorAll('[data-topic-reset]').forEach(function(b){b.addEventListener('click',function(){state=Object.assign({},defaults,{theme:state.theme});invalidTheme=false;writeURL('replace');filters();search.focus();});});
search.addEventListener('keydown',function(event){if(event.key==='Escape'&&search.value){event.preventDefault();event.stopPropagation();search.value='';updateFilters();}});
openButton.addEventListener('click',function(){if(typeof dialog.showModal!=='function'){location.href='gmi-index.html';return;}document.querySelector('[data-browse-slot]').append(browse);dialog.showModal();search.focus();});
document.querySelector('[data-browse-close]').addEventListener('click',function(){dialog.close();});dialog.addEventListener('close',function(){home.append(browse);(mobile.matches?openButton:search).focus({preventScroll:true});});mobile.addEventListener('change',function(e){if(!e.matches&&dialog.open)dialog.close();});
document.addEventListener('keydown',function(event){if(event.key!=='/'||event.ctrlKey||event.metaKey||event.altKey)return;var a=document.activeElement;if(a&&(a.isContentEditable||/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)))return;event.preventDefault();event.stopImmediatePropagation();if(mobile.matches)openButton.click();else search.focus();},true);
answer.querySelector('[data-gmi-copy]').addEventListener('click',async function(){var button=this;button.disabled=true;writeURL('replace');try{if(!navigator.clipboard||!navigator.clipboard.writeText)throw new Error('clipboard unavailable');await navigator.clipboard.writeText(location.href);answer.querySelector('[data-copy-label]').textContent=tr('Link copied','链接已复制');announce(tr('Link copied to clipboard.','链接已复制到剪贴板。'));setTimeout(function(){answer.querySelector('[data-copy-label]').textContent=tr('Copy link','复制链接');},2500);}catch(error){var fallback=answer.querySelector('.gmi-copy-fallback'),input=document.getElementById('gmi-share-url');fallback.hidden=false;input.value=location.href;input.focus();input.select();announce(tr('Copy was unavailable. Select and copy the address shown.','暂无法自动复制。请选择并复制所显示的地址。'));}finally{button.disabled=false;}});
answer.querySelector('[data-copy-close]').addEventListener('click',function(){answer.querySelector('.gmi-copy-fallback').hidden=true;answer.querySelector('[data-gmi-copy]').focus();});
window.addEventListener('hashchange',restore);window.addEventListener('popstate',restore);
new MutationObserver(function(changes){if(changes.some(function(change){return change.attributeName==='data-lang';})){sync();companies();}else refreshJourney();}).observe(root,{attributes:true,attributeFilter:['data-lang','data-gmi-lens']});
restore();
workspace.setAttribute('data-gmi-ready','');
})();
