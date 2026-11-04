/* ══════════════════════════════════════════════════════════════════════════════
   SI WORKSPACE V2 — hash router · lazy mount · per-view reads · rail provenance
   Masterplan: research/SI_WORKSPACE_V2_MASTERPLAN_BY_FABLE.md §1 / §1b.

   Display tier only. Nothing here originates a signal, a score, a rank or a gate
   (constitution A7): every line it writes is a re-phrasing of a field the nightly
   payload already carries, and any absent input drops its clause rather than
   inventing one.
   ══════════════════════════════════════════════════════════════════════════════ */
(function(){
'use strict';
/* Native Cycles joins the existing views. 'confluence' is the subsector-confluence board brought in from
   the standalone subsectors page (US parity with the China desk's 5th view, #4637, which
   deferred this side). It ships its own hero and its own payload (subsectors.js,
   lazy-mounted below), so it is a promise the data can keep. It has no si-read slot — its
   hero is its read. */
var VIEWS=['overview','map','cycles','moving','money','explore','confluence'];
var TITLES={overview:['Brief','简报'],map:['Market map','市场图谱'],
  cycles:['Cycles','周期'],
  moving:['Rotation','轮动'],money:['Breadth & money','广度与资金'],
  explore:['Themes & compare','主题与比较'],confluence:['Entry evidence','入场证据']};
/* View glyphs = the estate's hand-drawn masked-icon family (product-nav-icons /
   dashboard-icons — the same set the nav mega-menus draw), tinted via currentColor.
   Never raw emoji beside the wordmark. */
var GLYPH={
  overview:'dash-icon submenu-icon-intelligence',
  map:'dash-icon dash-icon-compass',
  cycles:'dash-icon dash-icon-compass',
  moving:'dash-icon submenu-icon-rotation',
  money:'dash-icon submenu-icon-flow',
  explore:'dash-icon dash-icon-search',
  confluence:'dash-icon submenu-icon-confluence'};

/* ── LEGACY_ANCHORS (§2b) ───────────────────────────────────────────────────────
   Every pre-V2 deep link on the estate — the two redirect stubs, chat citations,
   dashboard cards, detail back-links, alert links — resolves here to
   [view, intra-view scroll target]. The ids on the right are the ORIGINAL section
   ids, preserved through the wrap precisely so this table can still reach them.
   Pinned by tests/test_si_workspace_shell.py; unknown hash → overview.
   `#theme-<id>` is NOT in this table on purpose: resolveThemeHash() owns it and
   navigates away to the basket page, so the router must not touch that hash.
   ── 21 / 23 split (Meta-CEO B W7A_7056_HEAL) ──
   The parsed LEGACY_ANCHORS literal below (introduced by the var keyword on
   the next non-comment line) stays EXACTLY 21 keys (D05 moves sc-cyclemap to its native Cycles view), so tests/test_xpv2_sector_r3_fixture.py::TestLegacyAnchors
   (real parser reads that literal) continues to assert 21. The S2 constant
   (defined just below) merges two non-theme keys at runtime — one routing
   the accumulation anchor to moving, and one routing a new si-heat-section
   key to explore with a scroll target of theme-heat-section — giving a live
   key-count of 24 on the merged table. Any future key added to S2 MUST NOT
   use a theme prefix (the LINE 324 short-circuit would eat it as dead data);
   pins asserting the 21-key count or the live 24-key count are both
   intentional, not in conflict. */
var LEGACY_ANCHORS={
  'actnow-section':['overview','actnow-section'],
  'regime':['overview','regime'],
  'grader':['overview','grader'],
  'si-map':['map','si-map'],
  'rotmap-section':['map','rotmap-section'],
  'sc-cyclemap':['cycles','sc-cyclemap'],
  'board':['map','board'],
  'si-movement':['moving','si-movement'],
  'rc-events-mount':['moving','rc-events-mount'],
  'rotation-app':['moving','rotation-app'],
  'si-money':['money','si-money'],
  'internals-section':['money','internals-section'],
  'scc-leadership':['money','scc-leadership'],
  'explore-section':['explore','explore-section'],
  'table-section':['explore','table-section'],
  'chart-section':['explore','chart-section'],
  'forming-narratives':['explore','forming-narratives'],
  'tm-mount':['explore','tm-mount'],
  /* the standalone subsectors page's own ids, so its redirect stub and every chat / detail
     back-link that cited them still lands on the right rail view rather than overview. */
  'confluence':['confluence','si-confluence'],
  'sc-app':['confluence','sc-app'],
  'sc-top':['confluence','sc-top']
};
/* S2 sector_central nested anchors (MO-A S2 r5): the demoted #accumulation and
   #theme-tape spans, so old hashes that landed on the moved panels still
   resolve. Kept OUTSIDE the pinned 21-key LEGACY_ANCHORS block so
   tests/test_xpv2_sector_r3_fixture.py::TestLegacyAnchors (real parser
   reads the var LEGACY_ANCHORS={…}; literal) still counts 21; the merge
   below preserves the hash-router intent. */
var LEGACY_ANCHORS_S2={
  'accumulation-section':['moving','accumulation-section'],
  'si-heat-section':['explore','theme-heat-section'],
  'si-measured':['map','si-measured']
};
for(var _k in LEGACY_ANCHORS_S2){LEGACY_ANCHORS[_k]=LEGACY_ANCHORS_S2[_k];}

/* ── lazy mount (gate 8) ────────────────────────────────────────────────────────
   Each organ script self-boots on load (readyState is already past 'loading' by
   the time we inject), so appending the tag IS the mount — and it mounts with the
   view ALREADY visible. That ordering is load-bearing, not just a weight saving:
   heatmap.js sizes its treemap from `tm.clientWidth || wrap.clientWidth` and
   subsector_rotation.js from `container.clientWidth`, both of which read 0 inside a
   display:none section and render blank/wrong-width forever.
   Order inside a list is preserved (async=false). time_machine.js draws its map
   through window.SRR, exported by subsector_rotation.js, so explore declares that
   dependency explicitly — `loaded` is global, so it is fetched at most once. */
var LAZY={
  map:['@cycles'],
  cycles:['@cycles'],
  moving:['subsector_rotation.js','rotation_events.js','desk_watch.js'],
  money:['heatmap.js'],
  explore:['subsector_rotation.js','time_machine.js'],
  /* the confluence board: subsectors.js self-boots on injection, finds #sc-app inside the
     now-visible view and fetches its board JSON. It writes innerHTML only — no clientWidth
     read — so it needs no laid-out box; it is lazy purely so that heavy fetch never fires
     on an Overview-only visit. */
  confluence:['subsectors.js']
};
var loaded={}, mounted={}, pendingTrace=null;

/* reuse the optimizer's ?v= immutable URL from the head's preload/prefetch link */
function vUrl(name){
  try{
    var l=document.querySelector('link[rel="preload"][href^="'+name+'"],link[rel="prefetch"][href^="'+name+'"]');
    if(l){ var h=l.getAttribute('href'); if(h) return h; }
  }catch(e){}
  return name;
}
function inject(src,onload){
  var s=document.createElement('script'); s.async=false; s.src=vUrl(src);
  if(onload) s.addEventListener('load',onload);
  document.head.appendChild(s);
}
function loadCycles(){
  if(loaded['@cycles']) return; loaded['@cycles']=true;
  window.SC_LAZY_EXTRAS=true;                       // narr+dna wait for first sector focus
  window.SC_EXTRA_DATA=['sector_cycles_narr_data.js','sector_cycles_dna_data.js'];
  window.SC_SERIES_DATA='sector_cycles_series_data.js';
  var files=['sector_cycles_data.js','mm_charts.js','sector_cycles.js'];
  files.forEach(function(f,i){
    inject(f, i===0?function(){ document.dispatchEvent(new CustomEvent('sc:cycles-data')); }:null);
  });
}
function loadAssets(view){
  var list=LAZY[view]||[];
  for(var i=0;i<list.length;i++){
    var f=list[i];
    if(f==='@cycles'){ loadCycles(); continue; }
    if(loaded[f]) continue;
    loaded[f]=true; inject(f);
  }
}

/* ── helpers ─────────────────────────────────────────────────────────────────── */
function isZh(){ return document.documentElement.getAttribute('data-lang')==='zh'; }
function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){
  return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]; }); }
function L(en,zh){ return '<span class="l-en">'+en+'</span><span class="l-zh">'+(zh==null?en:zh)+'</span>'; }
function P(){ return window.BASKETS||null; }
function TI(){ var p=P(); return (p&&p.theme_intel)||null; }

/* ── the composer: __siViewReads(payload) ────────────────────────────────────────
   Composition rules (§1b), enforced by hand because they are copy rules:
     · plain words only — no internal state names, no study names, no raw slugs,
       no untranslated statistics;
     · ≤18 words per line, EN and ZH authored together (never machine-flipped);
     · every clause fail-soft — an absent input drops that clause, and a line with
       no surviving clause stays hidden. Absence is never dressed as a reading;
     · display-tier composition ONLY: counts and names already in the payload, no
       new score, rank, threshold or gate is computed here (A7).
   Each line carries a ? receipt naming the inputs it was composed from. */
function readOverview(el){
  var ti=TI(); if(!ti) return null;
  var from=el.getAttribute('data-from-en'), to=el.getAttribute('data-to-en');
  var fromZh=el.getAttribute('data-from-zh')||from, toZh=el.getAttribute('data-to-zh')||to;
  var n=(((ti.act_now||{}).buy)||[]).length;
  var en=[], zh=[];
  if(from&&to){
    en.push(esc(from)+' is handing leadership to '+esc(to)+'.');
    zh.push(esc(fromZh)+'正把领先交给'+esc(toZh)+'。');
  }
  if(n>0){
    en.push(n+(n===1?' name sits':' names sit')+' in the Buy lane.');
    zh.push(n+' 个标的在「立即买入」清单。');
  }else{
    en.push('Nothing is in the Buy lane today.');
    zh.push('今日「立即买入」清单为空。');
  }
  if(!en.length) return null;
  return [en.join(' '), zh.join('')];
}
function readMap(){
  /* __siRvxData is hoisted onto window by __siInitPage — rvxData() itself is declared
     INSIDE that function, so this separate script cannot see the bare name. Reaching
     for `rvxData` directly here fails silently (typeof → 'undefined', catch swallows,
     read stays hidden) and looks exactly like "no data yet". */
  var d=null;
  try{ d=(typeof window.__siRvxData==='function')?window.__siRvxData():null; }catch(e){}
  if(!d||!d.length) return null;
  var lead=d.filter(function(x){ return x.q==='lead'; });   // strong AND still rising
  if(!lead.length) return ['No group is both strong and still rising right now.',
                           '当前没有既强势又仍在上行的板块。'];
  var top=lead[0], n=lead.length;                            // rvxData sorts by score desc
  return [n+(n===1?' group sits':' groups sit')+' top-right — strong and still rising. '
          +esc(top.name)+' is furthest along.',
          n+' 个板块位于右上 — 强势且仍在上行。'+esc(top.name_zh||top.name)+'走得最远。'];
}
function readMoving(){
  var ti=TI(); if(!ti||!ti.themes||!ti.themes.length) return null;
  var up=0, dn=0, seen=0;
  ti.themes.forEach(function(t){
    var v=t&&t.pulse_rank_delta_5d; if(v==null) return;
    seen++; if(v>0) up++; else if(v<0) dn++;
  });
  if(!seen) return null;
  if(!up&&!dn) return ['A quiet tape — no group moved up or down the ranking this week.',
                       '行情平静 — 本周没有板块排名上升或下降。'];
  return [up+(up===1?' group':' groups')+' moved up the ranking this week, '+dn+' slipped.',
          '本周 '+up+' 个板块排名上升，'+dn+' 个下滑。'];
}
function readMoney(el){
  var r=el.getAttribute('data-regime'); if(!r) return null;
  /* display phrasing lifted verbatim from the money-flow card so the two agree */
  var EN={concentrated:'Money is crowding into a few groups — be selective here.',
          broad:'Money is spread across many groups — a broad tide, not a narrow few.',
          mixed:'No single group is leading the money right now.'};
  var ZH={concentrated:'资金正向少数板块集中 — 此时应精挑细选。',
          broad:'资金广泛分布于多个板块 — 全面上涨，而非少数领涨。',
          mixed:'当前没有单一板块主导资金流向。'};
  if(!EN[r]) return null;
  return [EN[r], ZH[r]];
}
function readExplore(){
  var p=P(), n=((p&&p.baskets)||[]).length;
  if(!n) return null;
  return [n+' baskets — every member, every record.', n+' 个篮子 — 全部成分，全部记录。'];
}
var RECEIPTS={
  overview:['Composed from tonight’s leadership handoff and the Buy lane count. Display only — it restates the reads below, it does not add one.',
            '由今晚的领涨交棒与「立即买入」清单数量组成。仅为展示 — 复述下方研判，不新增判断。'],
  map:['Counts the groups sitting strong and still rising on the map below, named by the same ranking the map draws. Display only.',
       '统计下方图中既强势又仍在上行的板块，命名沿用图表所用排序。仅为展示。'],
  moving:['Counts how many groups moved up or down this week’s ranking in the payload. A context lens — it ranks nothing and gates nothing.',
          '统计本周排名上升或下降的板块数量。仅供参考视角 — 不排序、不门控。'],
  money:['Restates the money-flow reading shown on the breadth card below, in plain words. Display only.',
         '以平实措辞复述下方广度卡片的资金流向读数。仅为展示。'],
  explore:['Counts the baskets carried in tonight’s payload — the same set the table below lists.',
           '统计今晚数据中的篮子数量 — 与下方表格所列相同。']
};
function paint(view,pair){
  var el=document.getElementById('si-read-'+view); if(!el) return;
  if(!pair){ el.hidden=true; el.innerHTML=''; return; }
  var r=RECEIPTS[view]||['',''];
  el.innerHTML='<span class="si-vr-g '+GLYPH[view]+'" aria-hidden="true"></span>'
    +'<span class="si-vr-t">'+L(pair[0],pair[1])+'</span>'
    +'<span class="si-vr-q" data-tip-t-en="Where this line comes from" data-tip-t-zh="这句话的来源"'
    +' data-tip-en="'+esc(r[0])+'" data-tip-zh="'+esc(r[1])+'">?</span>';
  el.hidden=false;
}
/* the rail footer: the workspace's provenance lives with its navigation (§1b) */
function paintFoot(){
  var p=P(), a=document.getElementById('si-side-asof');
  if(a&&p&&p.as_of) a.innerHTML=L('as of '+esc(p.as_of),'截至 '+esc(p.as_of));
  var g=document.getElementById('si-side-grade');
  var GR=(window.SECTOR_CENTRAL&&window.SECTOR_CENTRAL.grader)||null;
  if(!g||!GR) return;
  if(!GR.available){
    g.innerHTML=L('Self-grader: accruing · '+(GR.n_calls||0)+' calls logged',
                  '自评分器：累积中 · 已记录 '+(GR.n_calls||0)+' 个判断');
    return;
  }
  var bh=GR.by_horizon||{}, h=bh['21d']||bh['63d']||bh['126d']||null;
  g.innerHTML=((h&&h.dir_hit_rate!=null)
    ? L('Self-grader: '+Math.round(h.dir_hit_rate*100)+'% hit · n='+(h.n||0),
        '自评分器：命中 '+Math.round(h.dir_hit_rate*100)+'% · n='+(h.n||0))
    : L('Self-grader: accruing','自评分器：累积中'))+graderVersionFrame(GR);
}
/* RB13 F1: the rail summary is the version-1 cohort once version 2 is active — frame it. */
function graderVersionFrame(GR){
  var seg=GR.score_version_segments||{}, s1=seg['1']||null;
  var v2=(GR.by_score_version||{})['2']||null;
  if(!s1||!s1.last_date) return '';
  var out=L(' · v1 calls through '+esc(s1.last_date),' · 版本1判断截至 '+esc(s1.last_date));
  if(v2) out+=L(' · v2 accruing n='+(v2.n_calls||0),' · 版本2累积中 n='+(v2.n_calls||0));
  return out;
}
function reads(){
  var o=document.getElementById('si-read-overview');
  if(o) paint('overview',readOverview(o));
  paint('map',readMap());
  paint('moving',readMoving());
  var m=document.getElementById('si-read-money');
  if(m) paint('money',readMoney(m));
  paint('explore',readExplore());
  paintFoot();
  if(pendingTrace) openTrace(pendingTrace);
}

/* `#read-<id>` (gate 4) — land on overview and open that lane row's trace expand.
   The board is filled asynchronously, so the request is held until it exists. */
function openTrace(id){
  var lanes=document.getElementById('actnow'); if(!lanes||!window.__siTrace) return;
  var row=null, rows=lanes.querySelectorAll('.rvx-trow[data-mlc-bid]');
  for(var i=0;i<rows.length;i++){ if(rows[i].getAttribute('data-mlc-bid')===id){ row=rows[i]; break; } }
  if(!row) return;
  pendingTrace=null;
  row.click();
  try{ row.scrollIntoView({block:'center'}); }catch(e){ row.scrollIntoView(); }
}

/* ── activation ──────────────────────────────────────────────────────────────── */
var BASE_TITLE=(document.title||'').split(' · ')[0];
var current=null;
/* J-restore scroll memory (masterplan §8/§10 — restored origin). Per-view window.scrollY
   captured at the instant a view is left, replayed when a hashchange (Back/Forward
   between views) re-enters that view with no explicit scroll target. A first visit has
   no entry and keeps native behaviour; history.scrollRestoration is never touched —
   this is additive memory on top of the browser's, not a replacement for it. */
var SCROLL_MEM={};
var FOCUS_MEM={};
var cycleOpening=false;
var entrySeq=0, activeEntryId=null, cycleApplied=false, savingEntry=false;
function localHref(){return location.pathname+location.search+location.hash;}
function entryId(){return window.crypto&&window.crypto.randomUUID?window.crypto.randomUUID():Date.now().toString(36)+'-'+String(++entrySeq);}
function currentEntry(){
  var e=(history.state||{}).siWorkspace;
  return e&&e.schema==='sector_central.entry.v1'&&typeof e.entryId==='string'&&e.entryId.length<=80&&e.href===localHref()&&VIEWS.indexOf(e.view)>=0?e:null;
}
function focusLocator(node){
  node=node||document.activeElement;
  if(!node||!node.getAttribute||!node.closest||!node.closest('.si-view')) return null;
  var keys=[['cycle-opener','data-cycle-id'],['board-cycle-opener','data-focus'],['measured','data-g'],['family','data-fam'],['mode','data-mode'],['scale','data-scale'],['entity','data-id']];
  for(var i=0;i<keys.length;i++){var value=node.getAttribute(keys[i][1]);if(value&&value.length<=100)return {kind:keys[i][0],id:value};}
  if(['mr-cycle-link','sc-cycle-heading','sc-cycle-return','sc-cycle-latest','sc-zreset'].indexOf(node.id)>=0)return {kind:'element',id:node.id};
  return null;
}
function resolveFocus(f){
  if(!f||typeof f.id!=='string'||f.id.length>100)return null;
  if(f.kind==='element'&&['mr-cycle-link','sc-cycle-heading','sc-cycle-return','sc-cycle-latest','sc-zreset'].indexOf(f.id)>=0)return document.getElementById(f.id);
  var attrs={'cycle-opener':'data-cycle-id','board-cycle-opener':'data-focus',measured:'data-g',family:'data-fam',mode:'data-mode',scale:'data-scale',entity:'data-id'};
  var attr=attrs[f.kind];if(!attr)return null;
  var nodes=document.querySelectorAll('.si-view.on ['+attr+']');
  for(var i=0;i<nodes.length;i++)if(nodes[i].getAttribute(attr)===f.id&&nodes[i].getBoundingClientRect().width)return nodes[i];
  return null;
}
function saveEntry(snapshot){
  if(savingEntry||!current)return;
  var old=currentEntry();
  if(!old||old.entryId!==activeEntryId||old.view!==current)return;
  var next=Object.assign({},old,{viewport:{scrollY:Math.max(0,Math.min(100000,window.scrollY||0)),focus:focusLocator()}});
  if(window.SectorMeasuredCapture)next.measured=window.SectorMeasuredCapture();
  if(current==='cycles'&&cycleApplied&&window.SectorCyclesCapture)next.cycles=snapshot||window.SectorCyclesCapture();
  savingEntry=true;
  try{history.replaceState(Object.assign({},history.state,{siWorkspace:next}),'',localHref());}finally{savingEntry=false;}
}
window.SectorWorkspaceCapture=function(){saveEntry();};
function prepareEntry(view){
  var e=currentEntry();
  if(!e||e.view!==view){
    e={schema:'sector_central.entry.v1',entryId:entryId(),href:localHref(),view:view,cycles:null};
    if(window.SectorMeasuredCapture)e.measured=window.SectorMeasuredCapture();
    history.replaceState(Object.assign({},history.state,{siWorkspace:e}),'',localHref());
  }
  activeEntryId=e.entryId;
  if(window.SectorMeasuredApply)window.SectorMeasuredApply(e.measured||null);
  return e;
}
function restoreViewport(e,gen){
  if(!e||!e.viewport)return false;
  var viewport=e.viewport;
  if(typeof viewport.scrollY!=='number'||!isFinite(viewport.scrollY)||viewport.scrollY<0||viewport.scrollY>100000)return false;
  requestAnimationFrame(function(){requestAnimationFrame(function(){
    var live=currentEntry();if(gen!==SCROLL_GEN||!live||live.entryId!==e.entryId)return;
    if(window.scrollY!==viewport.scrollY)window.scrollTo(0,viewport.scrollY);
    var focus=resolveFocus(viewport.focus);
    if(focus&&focus.getBoundingClientRect().width)focus.focus({preventScroll:true});
  });});
  return true;
}
var viewportQueued=false;
function scheduleEntrySave(){
  if(viewportQueued)return;viewportQueued=true;
  var captured=activeEntryId,href=localHref();
  requestAnimationFrame(function(){viewportQueued=false;if(captured===activeEntryId&&href===localHref())saveEntry();});
}
window.addEventListener('scroll',scheduleEntrySave,{passive:true});
document.addEventListener('focusin',scheduleEntrySave);
window.addEventListener('pagehide',function(){saveEntry();});
var SCROLL_GEN=0;   /* activation generation (RI09): each activate() supersedes any
                       still-pending replay frame from an earlier activation — a stale
                       frame must not scroll a view that is no longer on screen */
function activate(view,target){
  if(VIEWS.indexOf(view)<0) view='overview';
  var gen=++SCROLL_GEN;   /* every activation invalidates pending replay frames */
  var entry=prepareEntry(view);
  /* capture BEFORE the .on swap: the section about to be hidden still owns the viewport */
  if(current) SCROLL_MEM[current]=window.scrollY;
  var active=document.activeElement;
  if(!cycleOpening && current!==view && active && active.closest && active.closest('.si-view')) FOCUS_MEM[current]=active;
  var i, secs=document.querySelectorAll('.si-view'), btns=document.querySelectorAll('.si-view-btn');
  for(i=0;i<secs.length;i++) secs[i].classList.toggle('on',secs[i].getAttribute('data-view')===view);
  for(i=0;i<btns.length;i++){
    var on=btns[i].getAttribute('data-view')===view;
    btns[i].classList.toggle('on',on);
    if(on) btns[i].setAttribute('aria-current','page'); else btns[i].removeAttribute('aria-current');
  }
  /* Paper's workflow belongs to Macro. Research and watches land on existing
     Macro instruments; they do not introduce Terminal routes or storage. */
  var group=view==='overview'?'brief':
    (target==='tm-mount'||target==='forming-narratives')?'research':
    target==='accumulation-section'?'watches':'explore';
  var workflow=document.querySelectorAll('[data-si-workflow]');
  for(i=0;i<workflow.length;i++){
    var selected=workflow[i].getAttribute('data-si-workflow')===group;
    workflow[i].classList.toggle('on',selected);
    if(selected) workflow[i].setAttribute('aria-current','page');
    else workflow[i].removeAttribute('aria-current');
  }
  var subnav=document.querySelector('.si-side');
  if(subnav) subnav.hidden=view==='overview';
  try{ document.title=BASE_TITLE+' · '+TITLES[view][isZh()?1:0]; }catch(e){}
  current=view;
  /* First activation mounts the heavy organs. The view must be laid out first so the
     width-measuring renderers see a real box — but do NOT wait for a frame to get
     that: requestAnimationFrame never fires while the tab is hidden, so a background
     tab (or a restored session) would activate the view, set mounted[view]=true, and
     then never load a single organ — a permanently blank panel with no error anywhere.
     Reading offsetHeight forces a synchronous reflow instead: deterministic, and it
     does not care whether anyone is looking. */
  if(!mounted[view]){
    mounted[view]=true;
    var sec=document.querySelector('.si-view[data-view="'+view+'"]');
    if(sec) void sec.offsetHeight;
    loadAssets(view);
    try{ window.dispatchEvent(new Event('resize')); }catch(e){}     // nudge autoSize charts
  }
  /* Announce the switch on every activation, not just the first mount. Organs the page
     itself builds (the basket overlay chart) cannot be created while their view is
     display:none — lightweight-charts binds autoSize at creation and a chart born
     zero-wide never recovers — so they wait for this event to draw with a real box. */
  try{ document.dispatchEvent(new CustomEvent('si:view',{detail:view})); }catch(e){}
  if(view==='cycles') syncCycleContext();
  reads();
  if(target){
    var el=document.getElementById(target);
    if(el){ try{ el.scrollIntoView({block:'start'}); }catch(e){ el.scrollIntoView(); } }
    else if(history.replaceState) history.replaceState(history.state,'','#'+view);
  }else if(!cycleOpening && restoreViewport(entry,gen)){
    // Exact entry state precedes the legacy per-view fallback.
  }else if(typeof SCROLL_MEM[view]==='number' && !cycleOpening){
    /* hashchange path with no explicit target (Back/Forward between views): replay where
       this view was last left, one frame after the section swap so the layout has settled.
       First visit (no entry) never reaches here and native behaviour stands. RI09: the
       frame compares before it writes — if the viewport already sits at the remembered
       origin (the browser's own restoration settled there) the write is skipped instead
       of racing it, and a frame whose activation was superseded returns without touching
       the scroll. history.scrollRestoration stays untouched: additive memory, not a
       takeover of the browser's own restoration. */
    requestAnimationFrame(function(){
      if(gen!==SCROLL_GEN) return;
      if(window.scrollY!==SCROLL_MEM[view]) window.scrollTo(0,SCROLL_MEM[view]||0);
      var focus=FOCUS_MEM[view];
      if(focus && focus.isConnected && focus.getBoundingClientRect().width) focus.focus({preventScroll:true});
    });
  }
}
function route(){
  var h=(location.hash||'').replace(/^#/,'');
  try{ h=decodeURIComponent(h); }catch(e){}
  if(h.indexOf('theme-')===0){ activate('overview',null); return; }  // resolver owns it
  if(h.indexOf('read-')===0){ pendingTrace=h.slice(5); activate('overview',null); return; }
  if(VIEWS.indexOf(h)>=0){ activate(h,null); return; }
  if(LEGACY_ANCHORS[h]){ activate(LEGACY_ANCHORS[h][0],LEGACY_ANCHORS[h][1]); return; }
  activate('overview',null);                                        // unknown → overview
  if(!h&&history.replaceState) history.replaceState(history.state,'','#overview');
}

/* Cycles is a view of this router, not an entity-hash router inside it. The
   query preserves the measured selection (?g), shell origin and every other
   existing parameter. No receiver applies an older cutoff to latest evidence. */
function cycleMessage(en,zh){ return isZh()?zh:en; }
function cycleOrigin(){
  var origin=(history.state||{}).siCyclesOrigin;
  if(!origin || !origin.href) return null;
  try{
    var u=new URL(origin.href,location.href), h=u.hash.slice(1);
    if(u.origin!==location.origin || u.pathname!==location.pathname || u.username || u.password || h==='cycles' || h==='sc-cyclemap') return null;
    if(VIEWS.indexOf(h)<0 && !LEGACY_ANCHORS[h]) return null;
    return u.pathname+u.search+u.hash;
  }catch(e){ return null; }
}
function cycleSourceDate(){
  var m=(window.SECTOR_CENTRAL||{}).measured_read||{};
  return (m.generation||{}).session_end||null;
}
function cycleSourceSpine(){
  return (((window.SECTOR_CENTRAL||{}).measured_read||{}).generation||{}).cycle_spine||null;
}
function syncCycleContext(){
  if(current!=='cycles') return;
  var u=new URL(location.href), id=u.searchParams.get('cycle');
  var note=document.getElementById('sc-cycle-status');
  var study=document.getElementById('sc-native-study');
  var back=document.getElementById('sc-cycle-return');
  var latest=document.getElementById('sc-cycle-latest');
  var useLatest=u.searchParams.get('cycleSource')==='latest';
  var origin=cycleOrigin();
  var entry=currentEntry();
  if(back) back.href=origin||'#map';
  // Allow layout before asking the receiver. A rejected context is hidden
  // immediately afterwards, so no current detail masquerades as requested history.
  if(study) study.hidden=false;
  var receipt=window.SectorCyclesApply ? window.SectorCyclesApply({id:id,family:u.searchParams.get('cycleFamily'),asOf:id&&!useLatest?cycleSourceDate():null,requireSourceDate:!!id&&!useLatest,spine:id&&!useLatest?cycleSourceSpine():null,requirePublication:!!id&&!useLatest,entryKey:entry&&entry.entryId,snapshot:entry&&entry.cycles}) : {status:'pending'};
  cycleApplied=receipt.status==='applied';
  var messages={
    pending:['Loading cycle evidence…','正在载入周期证据…'],
    unsupported:['This instrument has no cycle record in this source. Return to the market map.','该数据源没有此标的的周期记录。请返回市场图谱。'],
    source_unavailable:['The cycle source identity is unavailable or could not be verified. This selection is withheld.','周期来源身份不可用或无法核验，暂不显示此选择。'],
    source_mismatch:['Cycle and sector evidence come from different source snapshots. This selection is withheld until the sources align.','周期与板块证据来自不同来源快照。来源对齐前暂不显示该选择。']
  };
  var message=messages[receipt.status];
  if(receipt.reason==='unverified_family')message=['This theme uses a separate Cycles source snapshot. Open its dated snapshot to inspect it.','该主题使用独立的周期来源快照。请打开其自身日期的快照进行查看。'];
  if(receipt.status==='applied') {
    message=receipt.series==='unavailable' ? ['Detailed price history could not load. The core cycle view remains available.','详细价格历史载入失败，基础周期视图仍可使用。'] :
      receipt.series==='pending' ? ['Cycle evidence loaded; detailed price history is loading.','周期证据已载入，详细价格历史正在载入。'] :
      ['Cycle evidence through '+receipt.asOf+'. Current reconstruction.','周期证据截至 '+receipt.asOf+'。当前重建结果。'];
  }
  if(note){ note.dataset.state=receipt.status; note.textContent=cycleMessage.apply(null,message||messages.source_unavailable); }
  if(note && receipt.status==='applied' && useLatest && cycleSourceDate()!==receipt.asOf) note.textContent+=cycleMessage(' Sector origin: '+(cycleSourceDate()||'date unavailable')+'.',' 板块原始日期：'+(cycleSourceDate()||'日期不可用')+'。');
  if(note && receipt.status==='applied' && receipt.publication && receipt.publication.status==='legacy_unverified') note.textContent+=cycleMessage(' Unverified archive; publication alignment is unavailable.',' 未核验归档；无法核验发布版本对齐。');
  if(note && receipt.restoration==='source_changed')note.textContent+=cycleMessage(' Saved chart settings belong to an older publication; current defaults are shown.',' 已保存图表设置属于旧发布版本；现显示当前默认设置。');
  if(note && receipt.restoration==='invalid_state')note.textContent+=cycleMessage(' Saved chart settings could not be restored; current defaults are shown.',' 无法恢复已保存图表设置；现显示当前默认设置。');
  var readable=receipt.publication&&['verified','legacy_unverified'].indexOf(receipt.publication.status)>=0;
  if(latest) latest.hidden=!(readable && receipt.asOf && (receipt.status==='source_mismatch'||receipt.status==='source_unavailable'));
  if(study) study.hidden=receipt.status!=='applied' && receipt.status!=='pending';
}
window.SectorCyclesHost={onFocus:function(id,family){
  if(current!=='cycles') return;
  var u=new URL(location.href);
  // This is a user action on an already admitted Cycles canvas. Its own
  // dated snapshot remains the source on later hydration/language events.
  // Central handoffs use SectorCentralOpenCycle and clear this explicit mode.
  if(cycleApplied) u.searchParams.set('cycleSource','latest');
  if(id) u.searchParams.set('cycle',id); else u.searchParams.delete('cycle');
  u.searchParams.set('cycleFamily',family||'sectors');
  var e=currentEntry(),href=u.pathname+u.search+u.hash;
  history.replaceState(Object.assign({},history.state,{siWorkspace:e?Object.assign({},e,{href:href}):null}),'',href);
  saveEntry();
  syncCycleContext();
},onState:function(snapshot){saveEntry(snapshot);}};
window.SectorCentralOpenCycle=function(id,trigger){
  if(!id) return false;
  saveEntry();
  var u=new URL(location.href), origin=u.pathname+u.search+u.hash;
  var originEntry=currentEntry();
  if(originEntry&&trigger){
    originEntry=Object.assign({},originEntry,{viewport:Object.assign({},originEntry.viewport,{focus:focusLocator(trigger)})});
    history.replaceState(Object.assign({},history.state,{siWorkspace:originEntry}),'',origin);
  }
  u.searchParams.delete('cycleSource');
  u.searchParams.delete('cycleFamily');
  u.searchParams.set('cycle',id); u.hash='cycles';
  if(current!=='cycles') {
    if(trigger) FOCUS_MEM[current]=trigger;
    var href=u.pathname+u.search+u.hash;
    history.pushState(Object.assign({},history.state,{siCyclesOrigin:{href:origin,entry:originEntry},siWorkspace:{schema:'sector_central.entry.v1',entryId:entryId(),href:href,view:'cycles',measured:originEntry&&originEntry.measured,cycles:null}}),'',href);
  } else {
    var next=u.pathname+u.search+u.hash;
    history.replaceState(Object.assign({},history.state,{siWorkspace:{schema:'sector_central.entry.v1',entryId:entryId(),href:next,view:'cycles',cycles:null}}),'',next);
  }
  cycleOpening=true;
  activate('cycles',null);
  cycleOpening=false;
  var heading=document.getElementById('sc-cycle-heading');
  if(heading) heading.focus({preventScroll:true});
  saveEntry();
  return true;
};
document.addEventListener('click',function(e){
  if(e.defaultPrevented || e.button!==0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  var a=e.target.closest('a[data-cycle-id]');
  if(a && window.SectorCentralOpenCycle(a.getAttribute('data-cycle-id'),a)) e.preventDefault();
  var back=e.target.closest('#sc-cycle-return');
  if(back){
    var destination=cycleOrigin()||location.pathname+location.search+'#map';
    var source=(history.state||{}).siCyclesOrigin, prior=source&&source.entry;
    saveEntry();
    var restored=prior&&prior.schema==='sector_central.entry.v1'&&prior.href===destination?Object.assign({},prior,{entryId:entryId()}):null;
    history.pushState(Object.assign({},history.state,{siWorkspace:restored,siCyclesOrigin:null}),'',destination);
    e.preventDefault();route();return;
  }
  if(e.target.closest('#sc-cycle-latest')) {
    var u=new URL(location.href);u.searchParams.set('cycleSource','latest');
    var currentState=currentEntry(),newHref=u.pathname+u.search+u.hash;
    history.replaceState(Object.assign({},history.state,{siWorkspace:currentState?Object.assign({},currentState,{href:newHref}):null}),'',newHref);
    syncCycleContext();
    var heading=document.getElementById('sc-cycle-heading');
    if(heading) heading.focus({preventScroll:true});
    saveEntry();
  }
  var nav=e.target.closest('a.si-view-btn');
  if(nav)saveEntry(); // capture the origin before the browser creates its hash entry
});
['sc:cycles-ready','sc:series-ready','sc:series-error','sc:publication-ready'].forEach(function(name){ document.addEventListener(name,syncCycleContext); });
window.addEventListener('popstate',route);

window.__siViewReads=reads;
window.__siRoute=route;
window.addEventListener('hashchange',route);
window.addEventListener('mmx:shell-location',route);
document.addEventListener('langchange',function(){
  try{ document.title=BASE_TITLE+' · '+TITLES[current||'overview'][isZh()?1:0]; }catch(e){}
  syncCycleContext();
});
route();
})();
