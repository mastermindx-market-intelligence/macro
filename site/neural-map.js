/* Canvas presentation for the incumbent curated confluence graph. No scoring,
 * polling, simulated signals, or force simulation runs in the animation loop. */
(function (global) {
  'use strict';
  var owners = new WeakMap();
  var ICONS = {
    plus:'<path d="M8 3v10M3 8h10"/>', minus:'<path d="M3 8h10"/>',
    fit:'<path d="M6 2H2v4m8-4h4v4M2 10v4h4m8-4v4h-4"/>',
    expand:'<path d="M6 2H2v4m8-4h4v4M2 10v4h4m8-4v4h-4M2 2l4 4m8-4-4 4M2 14l4-4m8 4-4-4"/>',
    pause:'<path d="M5 3v10M11 3v10"/>', play:'<path d="m5 3 8 5-8 5Z"/>'
  };
  function icon(name) { return '<svg viewBox="0 0 16 16" aria-hidden="true">' + ICONS[name] + '</svg>'; }
  function esc(value) { return String(value == null ? '' : value).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
  function clamp(value, min, max) { return Math.min(max, Math.max(min, value)); }
  function hash(str) { var h=2166136261; for(var i=0;i<str.length;i++) h=Math.imul(h^str.charCodeAt(i),16777619); return h>>>0; }

  function mount(root, options) {
    if (!root) return null;
    var previous=owners.get(root); if(previous) previous.destroy();
    var graph=options.graph, layout=options.layout;
    var allNodes=graph.defaultNodes.concat(graph.wiringNodes || []);
    var allEdges=graph.defaultEdges.concat(graph.wiringEdges || []);
    var byId=new Map(allNodes.map(function(n){return [n.id,n];}));
    var defaults=new Set(graph.defaultNodes.map(function(n){return n.id;}));
    var adjacency=new Map(allNodes.map(function(n){return [n.id,[]];}));
    allEdges.forEach(function(e){ if(adjacency.has(e.src)&&adjacency.has(e.dst)&&e.src!==e.dst){adjacency.get(e.src).push(e);adjacency.get(e.dst).push(e);} });
    var positions=Object.assign(Object.create(null),layout.positions);
    // Added nodes have stable positions without moving the curated map or running
    // another quadratic force simulation when a layer is toggled.
    (graph.wiringNodes || []).forEach(function(n,i){
      var neighbors=adjacency.get(n.id)||[], anchor=null;
      for(var j=0;j<neighbors.length;j++) { var e=neighbors[j], p=positions[e.src===n.id?e.dst:e.src]; if(p&&defaults.has(e.src===n.id?e.dst:e.src)){anchor=p;break;} }
      anchor=anchor||positions.core||{x:600,y:380};
      var angle=(hash(n.id)%6283)/1000, distance=65+Math.sqrt(i+1)*9;
      positions[n.id]={x:anchor.x+Math.cos(angle)*distance,y:anchor.y+Math.sin(angle)*distance};
    });
    var state={expanded:false,selected:null,region:null,hovered:null,paused:false,scale:1,tx:0,ty:0,width:0,height:0,dpr:1,zh:false,light:false};
    var palette={}, nodes=[], edges=[], relevant=new Set(), renderedPoints=[], sceneDirty=true;
    var frame=0, elapsed=0, lastTime=0, destroyed=false, onscreen=true, pageVisible=!document.hidden, fitted=false;
    var media=global.matchMedia('(prefers-reduced-motion: reduce)'), coarse=global.matchMedia('(pointer: coarse)');
    var cleanups=[], pointers=new Map(), gesture=null, moved=false, suppressClick=false, neighborLimit=12;
    var canvas,ctx,cache,cacheCtx,search,results,inspector,status,tooltip,scene;
    var curveCache=new Map(), motionEdges=[];
    var t=function(en,zh){return state.zh?zh:en;};
    var label=function(n){return state.zh?(n.labelZh||n.label||n.id):(n.label||n.id);};
    var names={core:['Core','核心'],hub:['Hub','枢纽'],engine:['Engine','引擎'],regime:['Regime','周期'],complex:['Sector group','板块组'],sector:['Sector','板块'],thesis:['Thesis','论点'],signal:['Signal endpoint','信号端点'],'wiring-module':['Module','模块'],'wiring-artifact':['Data artifact','数据工件']};
    var relNames={structure:['Structure','结构'],feeds:['Feeds','输入'],confirms:['Confirms','确认'],contradicts:['Contradicts','矛盾']};
    function type(n){var a=names[n.type]||[n.type,n.type];return t(a[0],a[1]);}
    function rel(e){var a=relNames[e.edge_type]||[e.edge_type,e.edge_type];return t(a[0],a[1]);}
    function on(el,event,handler,opts){el.addEventListener(event,handler,opts);cleanups.push(function(){el.removeEventListener(event,handler,opts);});}
    function announce(message){status.textContent=message;}
    function color(n){if(n.type==='core')return palette.text;if(n.type==='engine')return palette[n._lobe]||palette.us;if(n.type==='sector'||n.type==='complex'||n.type==='hub')return palette.intl;if(n.type==='regime')return palette.meta;if(n.type==='thesis')return palette.us;return palette.muted;}
    function radius(n){return n.type==='core'?17:n.type==='engine'?8:n.type==='hub'?9:n.type==='regime'?6:n.type==='signal'?3.5:defaults.has(n.id)?4.5:2.5;}
    function readAppearance(){
      var s=getComputedStyle(root), get=function(v){return s.getPropertyValue(v).trim();};
      state.zh=document.documentElement.getAttribute('data-lang')==='zh';
      state.light=document.documentElement.getAttribute('data-theme')==='light';
      palette={text:get('--text'),muted:get('--muted'),bg:get('--bg'),panel:get('--panel'),line:get('--line'),us:get('--info'),intl:get('--orange'),signals:get('--link'),meta:get('--ok'),confirm:get('--ok'),contradict:get('--act'),font:get('--font-ui')||'sans-serif'};
    }
    readAppearance();
    root.classList.add('neural-map');
    root.setAttribute('data-neural-map-version','living-map-v1');
    root.innerHTML='<header class="nm-header"><div><p class="nm-eyebrow" data-copy="eyebrow"></p><h2 data-copy="title"></h2></div><div class="nm-snapshot"><span data-copy="snapshot"></span><time></time></div></header>'+
      '<div class="nm-toolbar"><div class="nm-search"><label class="nm-status" for="nm-search" data-copy="searchLabel"></label><input id="nm-search" type="search" autocomplete="off" aria-controls="nm-results"><span class="nm-key" aria-hidden="true">/</span><ul id="nm-results" class="nm-results" hidden></ul></div>'+
      '<button type="button" class="nm-btn" id="gc_wire" aria-pressed="false"></button><button type="button" class="nm-btn" id="gc_pause" aria-pressed="false"></button><button type="button" class="nm-btn" id="gc_fs">'+icon('expand')+'<span data-copy="fullscreen"></span></button></div>'+
      '<div class="nm-workspace"><div class="nm-scene"><canvas id="graph_canvas" tabindex="0"></canvas><div class="nm-regions" role="group"></div><div class="nm-stage-bottom"><div class="nm-stage-note" data-copy="gesture"></div><div class="nm-camera" role="group"><button type="button" class="nm-btn" id="gc_minus">'+icon('minus')+'</button><button type="button" class="nm-btn nm-zoom" id="gc_fit"></button><button type="button" class="nm-btn" id="gc_plus">'+icon('plus')+'</button></div></div><div id="graph_tooltip" class="nm-tooltip" hidden></div></div><aside id="graph_info_card" class="nm-inspector"></aside></div>'+
      '<footer class="nm-footer"><div class="nm-legend" id="graph_legend"></div><div class="nm-disclosure" data-copy="disclosure"></div></footer><div class="nm-status" id="nm-status" role="status" aria-live="polite" aria-atomic="true"></div>';
    var $=function(q){return root.querySelector(q);};
    canvas=$('canvas'); ctx=canvas.getContext('2d'); cache=document.createElement('canvas'); cacheCtx=cache.getContext('2d');
    search=$('input');results=$('.nm-results');inspector=$('.nm-inspector');status=$('#nm-status');tooltip=$('.nm-tooltip');scene=$('.nm-scene');

    function motionAllowed(){return !state.paused&&!media.matches&&!coarse.matches;}
    function canDraw(){return !destroyed&&onscreen&&pageVisible&&root.isConnected;}
    function syncMotionButton(){
      var button=$('#gc_pause');
      button.innerHTML=icon(state.paused?'play':'pause')+esc(state.paused?t('Resume motion','继续动态'):t('Pause motion','暂停动态'));
      button.setAttribute('aria-pressed',String(state.paused));
      button.disabled=media.matches||coarse.matches;
      if(button.disabled) {button.innerHTML=icon('pause')+esc(t('Motion off','动态已关闭'));button.title=t('Motion is off for reduced motion or touch input.','尊重减少动态偏好；触屏设备默认静止。');} else button.title='';
    }
    function updateCopy(){
      var copy={eyebrow:t('Neural Web / Synapse map','智脑 / 突触地图'),title:t('Explore the intelligence network.','探索智脑网络。'),snapshot:t('Graph snapshot','图谱快照'),searchLabel:t('Find a node','查找节点'),fullscreen:t('Expand','全屏'),gesture:coarse.matches?t('Drag to explore · Pinch to zoom\nSelect a node to follow its connections.','拖动探索 · 双指缩放\n选择节点，查看它的连接。'):t('Drag to explore · Scroll to zoom\nSelect a node to follow its connections.','拖动探索 · 滚动缩放\n选择节点，查看它的连接。'),disclosure:t('Motion illustrates recorded relationships. Display-only context; no live signal activity.','动态仅展示已记录的关系。仅供参考，不代表实时信号。')};
      root.querySelectorAll('[data-copy]').forEach(function(el){el.textContent=copy[el.dataset.copy];});
      var date=String(options.asof||'').slice(0,10);$('time').textContent=/^\d{4}-\d{2}-\d{2}$/.test(date)?date:t('Date unavailable','日期不可用');
      if(/^\d{4}-\d{2}-\d{2}$/.test(date))$('time').dateTime=date;
      search.placeholder=t('Find an engine, thesis, or signal…','查找引擎、论点或信号…');
      $('#gc_wire').textContent=t('Expanded map','扩展地图');
      $('#gc_wire').title=t('Include additional thesis and data-flow nodes.','显示更多论点和数据流节点。');
      $('#gc_plus').setAttribute('aria-label',t('Zoom in','放大'));$('#gc_minus').setAttribute('aria-label',t('Zoom out','缩小'));
      $('#gc_fit').title=t('Fit map (0)','适配地图 (0)');$('#gc_fit').setAttribute('aria-label',t('Fit map','适配地图'));
      canvas.setAttribute('aria-label',t('Interactive synapse map. Use search or the connection list for accessible node navigation. Arrow keys pan; plus and minus zoom; 0 fits; Escape clears selection.','交互式突触地图。可通过搜索及连接列表浏览节点。方向键平移；加减键缩放；0 适配；Esc 清除选择。'));
      $('.nm-camera').setAttribute('aria-label',t('Map zoom','地图缩放'));$('.nm-regions').setAttribute('aria-label',t('Focus a region','聚焦区域'));
      $('.nm-regions').innerHTML=[['us','US equity','美股'],['intl','China & international','中国及国际'],['signals','Signals & options','信号与期权'],['meta','Macro & policy','宏观与政策']].map(function(a){return '<button type="button" class="nm-region nm-'+a[0]+'" data-region="'+a[0]+'" aria-pressed="'+String(state.region===a[0])+'"><i class="nm-dot" aria-hidden="true"></i>'+esc(t(a[1],a[2]))+'</button>';}).join('');
      $('#graph_legend').innerHTML='<span><i class="nm-line" aria-hidden="true"></i>'+t('Structure','结构')+'</span><span><i class="nm-line nm-line-confirm" aria-hidden="true"></i>'+t('Confirms','确认')+'</span><span><i class="nm-line nm-line-contradict" aria-hidden="true"></i>'+t('Contradicts','矛盾')+'</span>';
      syncMotionButton();renderInspector();renderResults();
    }
    function activate(){
      nodes=state.expanded?allNodes:graph.defaultNodes;
      var ids=new Set(nodes.map(function(n){return n.id;}));
      edges=(state.expanded?allEdges:graph.defaultEdges).filter(function(e){return ids.has(e.src)&&ids.has(e.dst)&&e.src!==e.dst;});
      if(state.selected&&!ids.has(state.selected)) state.selected=null;
      state.hovered=null;tooltip.hidden=true;
      relevant=new Set();
      if(state.selected) {relevant.add(state.selected);edges.forEach(function(e){if(e.src===state.selected||e.dst===state.selected){relevant.add(e.src);relevant.add(e.dst);}});}
      else if(state.region){nodes.forEach(function(n){if(n._lobe===state.region)relevant.add(n.id);});edges.forEach(function(e){if(relevant.has(e.src)&&byId.get(e.src)._lobe===state.region)relevant.add(e.dst);if(relevant.has(e.dst)&&byId.get(e.dst)._lobe===state.region)relevant.add(e.src);});}
      motionEdges=edges.filter(function(e){return (e.edge_type==='confirms'||e.edge_type==='contradicts')&&(!state.selected||e.src===state.selected||e.dst===state.selected);}).slice(0,24);
      $('#gc_wire').setAttribute('aria-pressed',String(state.expanded));
      renderInspector();invalidate();
    }
    function nodeButton(n, subtitle){return '<button type="button" class="nm-neighbor" data-node="'+esc(n.id)+'"><span>'+esc(label(n))+(subtitle?'<small>'+esc(subtitle)+'</small>':'')+'</span><span aria-hidden="true">↗</span></button>';}
    function renderInspector(){
      if(!inspector)return;
      var n=byId.get(state.selected);
      if(!n){
        var engines=nodes.filter(function(x){return x.type==='engine'&&(!state.region||x._lobe===state.region);});
        inspector.innerHTML='<p class="nm-eyebrow">'+t(state.region?'Region in focus':'A connected system',state.region?'聚焦区域':'相互连接的系统')+'</p><h3>'+t('Follow your curiosity.','从好奇心出发。')+'</h3><p>'+t('Choose a node to see what feeds it, what it connects to, and where the evidence agrees or conflicts.','选择节点，查看其数据来源、连接，以及证据之间的确认或矛盾。')+'</p><div class="nm-stat"><strong>'+nodes.length+'</strong><span>'+t('visible nodes','个可见节点')+'</span></div><p>'+edges.length+' '+t('connections in this view','条可见连接')+' · '+graph.engineCount+' '+t('engines','个引擎')+'</p><hr class="nm-divider"><p class="nm-eyebrow">'+t('Start exploring','开始探索')+'</p>'+engines.slice(0,3).map(function(x){return nodeButton(x,type(x));}).join('')+'<p>'+t('Search includes both the curated and expanded map.','搜索同时覆盖精选地图和扩展地图。')+'</p>';
        return;
      }
      var links=edges.filter(function(e){return e.src===n.id||e.dst===n.id;});
      var neighbors=new Map();links.forEach(function(e){var id=e.src===n.id?e.dst:e.src;if(!neighbors.has(id))neighbors.set(id,[]);neighbors.get(id).push(e);});
      var entries=Array.from(neighbors.entries()).sort(function(a,b){return label(byId.get(a[0])).localeCompare(label(byId.get(b[0])));});
      inspector.innerHTML='<div class="nm-inspector-head"><span class="nm-eyebrow">'+esc(type(n))+'</span><button type="button" class="nm-btn nm-close" data-action="clear" aria-label="'+t('Clear selection','清除选择')+'">×</button></div><h3 tabindex="-1">'+esc(label(n))+'</h3><p>'+t('Recorded connections in the selected snapshot. Structure links describe the map; they are not evidence of predictive power.','以下为所选快照中的连接。结构连线用于说明图谱，不代表预测能力。')+'</p><div class="nm-stat"><strong>'+neighbors.size+'</strong><span>'+t('connected nodes','个相连节点')+'</span></div><hr class="nm-divider"><p class="nm-eyebrow">'+t('Follow a connection','沿连接探索')+'</p>'+
        entries.slice(0,neighborLimit).map(function(entry){var neighbor=byId.get(entry[0]);return nodeButton(neighbor,entry[1].map(function(e){return (e.src===n.id?'→ ':'← ')+rel(e);}).join(' · '));}).join('')+
        (entries.length>neighborLimit?'<button type="button" class="nm-btn nm-show-more" data-action="more">'+t('Show all ','显示全部 ')+entries.length+t(' connections',' 个连接')+'</button>':'')+
        '<details class="nm-evidence"><summary>'+t('Node & relationship details','节点与关系详情')+'</summary><p>'+t('Source notes are preserved below, including any display-only or pre-validation caveats.','以下保留来源说明，包括仅供展示或尚未验证的限制。')+'</p><pre>'+esc(JSON.stringify({id:n.id,type:n.type,meta:n.meta||{},connections:links},null,2))+'</pre></details>';
    }
    function renderResults(){
      var query=search.value.trim().toLocaleLowerCase();
      if(!query){results.hidden=true;results.innerHTML='';return;}
      var matches=allNodes.filter(function(n){return [n.label,n.labelZh,n.id].join(' ').toLocaleLowerCase().includes(query);});
      results.hidden=false;
      results.innerHTML=matches.slice(0,30).map(function(n){return '<li><button type="button" class="nm-result" data-node="'+esc(n.id)+'"><span>'+esc(label(n))+'<small>'+esc(type(n))+(defaults.has(n.id)?'':' · '+t('Expanded map','扩展地图'))+'</small></span><span aria-hidden="true">↗</span></button></li>';}).join('')+
        (!matches.length?'<li class="nm-no-results">'+t('No matching nodes. Try an engine name or a broader term.','未找到匹配节点。请尝试引擎名称或更宽泛的词。')+'</li>':matches.length>30?'<li class="nm-no-results">'+t('Showing 30 of ','显示前 30 项，共 ')+matches.length+t(' matches. Keep typing to narrow the list.',' 项。请继续输入以缩小范围。')+'</li>':'');
    }
    function select(id,center){
      if(id&&!byId.has(id))return;
      state.selected=id;state.region=null;neighborLimit=12;
      if(id&&!defaults.has(id))state.expanded=true;
      search.value='';results.hidden=true;activate();updateCopy();
      if(id&&center){var p=positions[id];state.scale=Math.max(state.scale,1);state.tx=state.width/2-p.x*state.scale;state.ty=state.height/2-p.y*state.scale;invalidate();}
      announce(id?label(byId.get(id))+t(' selected. Connections are listed below.',' 已选中。下方列出其连接。'):t('Selection cleared.','已清除选择。'));
    }
    function bounds(items){var x0=Infinity,y0=Infinity,x1=-Infinity,y1=-Infinity;items.forEach(function(n){var p=positions[n.id];if(!p)return;x0=Math.min(x0,p.x-30);y0=Math.min(y0,p.y-30);x1=Math.max(x1,p.x+30);y1=Math.max(y1,p.y+30);});return {x0:x0,y0:y0,x1:x1,y1:y1};}
    function fit(){
      var items=state.region?nodes.filter(function(n){return relevant.has(n.id);}):nodes,b=bounds(items);
      if(!Number.isFinite(b.x0))return;
      var px=state.width<500?28:48,py=84;
      state.scale=clamp(Math.min((state.width-px*2)/Math.max(1,b.x1-b.x0),(state.height-py*2)/Math.max(1,b.y1-b.y0)),.18,2.5);
      state.tx=state.width/2-(b.x0+b.x1)/2*state.scale;state.ty=state.height/2-(b.y0+b.y1)/2*state.scale;fitted=true;invalidate();
    }
    function zoom(factor,x,y){var old=state.scale,next=clamp(old*factor,.18,5);x=x==null?state.width/2:x;y=y==null?state.height/2:y;state.tx=x-(x-state.tx)*next/old;state.ty=y-(y-state.ty)*next/old;state.scale=next;invalidate();}
    function resize(){
      var rect=canvas.getBoundingClientRect(),w=Math.round(rect.width),h=Math.round(rect.height),dpr=Math.min(global.devicePixelRatio||1,2);
      if(!w||!h)return;
      var changed=w!==state.width||h!==state.height||dpr!==state.dpr;
      if(!changed)return;
      if(fitted){state.tx+=(w-state.width)/2;state.ty+=(h-state.height)/2;}
      state.width=w;state.height=h;state.dpr=dpr;
      canvas.width=cache.width=Math.round(w*dpr);canvas.height=cache.height=Math.round(h*dpr);
      if(!fitted)fit();else invalidate();
    }
    function point(id){var p=positions[id];return {x:p.x*state.scale+state.tx,y:p.y*state.scale+state.ty};}
    function curve(e){
      if(!curveCache.has(e)){var a=positions[e.src],b=positions[e.dst],sign=hash(e.src+e.dst)%2?1:-1;curveCache.set(e,{x:(a.x+b.x)/2-(b.y-a.y)*.12*sign,y:(a.y+b.y)/2+(b.x-a.x)*.12*sign});}
      var c=curveCache.get(e);return {x:c.x*state.scale+state.tx,y:c.y*state.scale+state.ty};
    }
    function edgePath(c,e){var a=point(e.src),b=point(e.dst),q=curve(e);c.beginPath();c.moveTo(a.x,a.y);c.quadraticCurveTo(q.x,q.y,b.x,b.y);}
    function highlighted(id){return (!state.selected&&!state.region)||relevant.has(id);}
    function rebuild(){
      sceneDirty=false;if(!ctx||!cacheCtx)return;
      var c=cacheCtx;c.setTransform(state.dpr,0,0,state.dpr,0,0);c.clearRect(0,0,state.width,state.height);
      // Sparse coordinate marks give scale without competing with the network.
      c.fillStyle=palette.muted;c.globalAlpha=state.light?.14:.17;
      for(var gx=24;gx<state.width;gx+=48)for(var gy=36;gy<state.height;gy+=48)c.fillRect(gx,gy,1,1);
      edges.forEach(function(e){
        var special=e.edge_type==='confirms'||e.edge_type==='contradicts';
        var active=state.selected?(e.src===state.selected||e.dst===state.selected):state.region?(relevant.has(e.src)&&relevant.has(e.dst)):true;
        c.globalAlpha=active?(special?.60:(state.light?.22:.26)):.045;
        c.strokeStyle=e.edge_type==='confirms'?palette.confirm:e.edge_type==='contradicts'?palette.contradict:palette.muted;
        c.lineWidth=active&&state.selected?1.6:special?1.1:.65;
        c.setLineDash(e.edge_type==='contradicts'?[4,5]:[]);edgePath(c,e);c.stroke();
      });
      c.setLineDash([]);renderedPoints=[];
      nodes.forEach(function(n){
        var p=point(n.id),r=radius(n)*Math.pow(state.scale,.42),active=highlighted(n.id),selected=n.id===state.selected;
        renderedPoints.push({id:n.id,x:p.x,y:p.y,r:r});
        if(p.x<-30||p.x>state.width+30||p.y<-30||p.y>state.height+30)return;
        c.globalAlpha=active?1:.18;
        if(n.type==='engine'||n.type==='core'||selected){c.beginPath();c.arc(p.x,p.y,r+7,0,Math.PI*2);c.fillStyle=color(n);c.globalAlpha=active?(state.light?.065:.10):.025;c.fill();}
        c.globalAlpha=active?1:.18;c.beginPath();c.arc(p.x,p.y,r,0,Math.PI*2);c.fillStyle=color(n);c.fill();
        if(n.type==='core'){c.beginPath();c.arc(p.x,p.y,r*.35,0,Math.PI*2);c.fillStyle=palette.bg;c.fill();}
        if(selected||n.id===state.hovered){c.beginPath();c.arc(p.x,p.y,r+4,0,Math.PI*2);c.strokeStyle=palette.text;c.lineWidth=1.4;c.stroke();}
      });
      // Label candidates are ranked only on scene changes; collision boxes keep
      // the resting view quiet. Search/inspection always exposes full labels.
      var priority=function(n){return n.id===state.selected?0:n.id===state.hovered?1:n.type==='core'?2:n.type==='engine'?3:n.type==='hub'?4:n.type==='regime'?5:6;};
      var ranked=nodes.slice().sort(function(a,b){return priority(a)-priority(b);}), boxes=[];
      ranked.forEach(function(n){
        if(!highlighted(n.id))return;
        var important=priority(n)<6,forced=n.id===state.selected||n.id===state.hovered;
        if(!important&&!forced&&state.scale<1.15)return;
        var p=point(n.id),r=radius(n)*Math.pow(state.scale,.42),text=label(n),font=n.type==='core'?12:11;
        if(state.width<500&&!forced&&!['core','engine','hub'].includes(n.type)&&state.scale<.8)return;
        c.font=(n.type==='core'||forced?'600 ':'400 ')+font+'px '+palette.font;
        var max=forced?240:140;if(c.measureText(text).width>max){while(text.length>2&&c.measureText(text+'…').width>max)text=text.slice(0,-1);text+='…';}
        var w=c.measureText(text).width,candidates=[{x:p.x-w/2,y:p.y+r+16},{x:p.x-w/2,y:p.y-r-10},{x:p.x+r+9,y:p.y+4},{x:p.x-r-w-9,y:p.y+4}],chosen=null;
        for(var k=0;k<candidates.length;k++){
          var candidate=candidates[k],box={x:candidate.x-4,y:candidate.y-12,w:w+8,h:17};
          if(candidate.x<8||candidate.x+w>state.width-8||candidate.y<78||candidate.y>state.height-65)continue;
          var overlaps=boxes.some(function(b){return box.x<b.x+b.w&&box.x+box.w>b.x&&box.y<b.y+b.h&&box.y+box.h>b.y;});
          var coversNode=renderedPoints.some(function(b){return b.id!==n.id&&box.x<b.x+b.r+2&&box.x+box.w>b.x-b.r-2&&box.y<b.y+b.r+2&&box.y+box.h>b.y-b.r-2;});
          if(!overlaps&&!coversNode){chosen={x:candidate.x,y:candidate.y,box:box};break;}
        }
        if(!chosen)return;
        boxes.push(chosen.box);c.globalAlpha=1;c.strokeStyle=palette.bg;c.lineWidth=3.5;c.lineJoin='round';c.strokeText(text,chosen.x,chosen.y);c.fillStyle=important||forced?palette.text:palette.muted;c.fillText(text,chosen.x,chosen.y);
      });
      c.globalAlpha=1;$('#gc_fit').textContent=Math.round(state.scale*100)+'%';
    }
    function draw(timestamp){
      frame=0;if(!canDraw()) {lastTime=0;return;}
      if(sceneDirty)rebuild();
      if(!ctx)return;
      ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,canvas.width,canvas.height);ctx.drawImage(cache,0,0);
      ctx.setTransform(state.dpr,0,0,state.dpr,0,0);
      if(motionAllowed()){
        elapsed+=lastTime?Math.min(timestamp-lastTime,48):0;lastTime=timestamp;
        var core=positions.core&&point('core'),wave=(Math.sin(elapsed/2200)+1)/2;
        if(core){ctx.globalAlpha=.05+wave*.055;ctx.strokeStyle=palette.text;ctx.lineWidth=1;ctx.beginPath();ctx.arc(core.x,core.y,24+wave*9,0,Math.PI*2);ctx.stroke();}
        motionEdges.forEach(function(e,i){var a=point(e.src),b=point(e.dst),q=curve(e),u=(elapsed/11000+i*.173)%1,v=1-u;
          ctx.globalAlpha=highlighted(e.src)&&highlighted(e.dst)?.75:.08;ctx.fillStyle=e.edge_type==='confirms'?palette.confirm:palette.contradict;ctx.beginPath();ctx.arc(v*v*a.x+2*v*u*q.x+u*u*b.x,v*v*a.y+2*v*u*q.y+u*u*b.y,1.8,0,Math.PI*2);ctx.fill();});
        ctx.globalAlpha=1;frame=global.requestAnimationFrame(draw);
      }else lastTime=0;
    }
    function invalidate(){sceneDirty=true;if(canDraw()&&!frame)frame=global.requestAnimationFrame(draw);}
    function reconcile(){if(!canDraw()){if(frame)global.cancelAnimationFrame(frame);frame=0;lastTime=0;}else invalidate();}
    function local(event){var b=canvas.getBoundingClientRect();return {x:event.clientX-b.left,y:event.clientY-b.top};}
    function hit(p){var best=null,distance=Infinity;renderedPoints.forEach(function(n){var d=Math.hypot(n.x-p.x,n.y-p.y),target=coarse.matches?22:13;if(d<=Math.max(n.r+5,target)&&d<distance){distance=d;best=n.id;}});return best;}
    function resetGesture(){
      var list=Array.from(pointers.values());
      if(list.length>=2){var a=list[0],b=list[1];gesture={kind:'pinch',distance:Math.max(1,Math.hypot(a.x-b.x,a.y-b.y)),x:(a.x+b.x)/2,y:(a.y+b.y)/2};}
      else gesture=list.length?{kind:'pan',x:list[0].x,y:list[0].y,startX:list[0].x,startY:list[0].y}:null;
    }
    on(canvas,'pointerdown',function(e){if(e.button!==0)return;canvas.focus({preventScroll:true});pointers.set(e.pointerId,local(e));canvas.setPointerCapture(e.pointerId);if(pointers.size===1){moved=false;suppressClick=false;}else {moved=true;suppressClick=true;}tooltip.hidden=true;resetGesture();});
    on(canvas,'pointermove',function(e){
      var p=local(e);
      if(!pointers.has(e.pointerId)){
        if(e.pointerType==='touch')return;
        var id=hit(p);if(id!==state.hovered){state.hovered=id;invalidate();}
        tooltip.hidden=!id;if(id){tooltip.textContent=label(byId.get(id))+' · '+type(byId.get(id));tooltip.style.left=clamp(p.x+14,8,Math.max(8,state.width-tooltip.offsetWidth-8))+'px';tooltip.style.top=clamp(p.y+16,8,state.height-tooltip.offsetHeight-8)+'px';}
        return;
      }
      pointers.set(e.pointerId,p);if(!gesture)return;
      if(pointers.size>=2){var list=Array.from(pointers.values()),a=list[0],b=list[1],mx=(a.x+b.x)/2,my=(a.y+b.y)/2,d=Math.max(1,Math.hypot(a.x-b.x,a.y-b.y));zoom(d/gesture.distance,gesture.x,gesture.y);state.tx+=mx-gesture.x;state.ty+=my-gesture.y;gesture={kind:'pinch',distance:d,x:mx,y:my};moved=true;suppressClick=true;}
      else {if(Math.hypot(p.x-gesture.startX,p.y-gesture.startY)>5)moved=true;if(moved){state.tx+=p.x-gesture.x;state.ty+=p.y-gesture.y;}gesture.x=p.x;gesture.y=p.y;}
      invalidate();
    });
    function release(e){
      if(!pointers.has(e.pointerId))return;
      var p=pointers.get(e.pointerId),tap=pointers.size===1&&!moved&&!suppressClick&&e.type==='pointerup';
      pointers.delete(e.pointerId);if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);
      if(tap)select(hit(p),false);else if(e.type!=='pointerup')suppressClick=true;
      resetGesture();
    }
    on(canvas,'pointerup',release);on(canvas,'pointercancel',release);on(canvas,'lostpointercapture',release);
    on(canvas,'pointerleave',function(){state.hovered=null;tooltip.hidden=true;invalidate();});
    on(canvas,'wheel',function(e){e.preventDefault();var p=local(e),delta=e.deltaY*(e.deltaMode===1?16:e.deltaMode===2?state.height:1);zoom(Math.exp(-clamp(delta,-120,120)*.0025),p.x,p.y);},{passive:false});
    on(canvas,'keydown',function(e){
      if(e.key==='+'||e.key==='=')zoom(1.22);else if(e.key==='-')zoom(1/1.22);else if(e.key==='0')fit();else if(e.key==='Escape')select(null,false);
      else if(e.key==='ArrowLeft')state.tx+=40;else if(e.key==='ArrowRight')state.tx-=40;else if(e.key==='ArrowUp')state.ty+=40;else if(e.key==='ArrowDown')state.ty-=40;else if(e.key==='/'){search.focus();}else return;e.preventDefault();invalidate();
    });
    on($('#gc_plus'),'click',function(){zoom(1.25);});on($('#gc_minus'),'click',function(){zoom(.8);});on($('#gc_fit'),'click',fit);
    on($('#gc_wire'),'click',function(){state.expanded=!state.expanded;activate();fit();announce(t('Map layer changed. ','地图图层已切换。')+nodes.length+t(' visible nodes.',' 个可见节点。'));});
    on($('#gc_pause'),'click',function(){state.paused=!state.paused;syncMotionButton();invalidate();});
    on($('#gc_fs'),'click',function(){
      var promise;
      try{promise=document.fullscreenElement===root?document.exitFullscreen():root.requestFullscreen();}catch(e){announce(t('Fullscreen is unavailable here. The map remains usable.','此处无法全屏显示，仍可继续使用地图。'));return;}
      if(promise&&promise.catch)promise.catch(function(){announce(t('Fullscreen is unavailable here. The map remains usable.','此处无法全屏显示，仍可继续使用地图。'));});
    });
    on(document,'fullscreenchange',function(){$('#gc_fs').setAttribute('aria-pressed',String(document.fullscreenElement===root));resize();});
    on($('.nm-regions'),'click',function(e){var b=e.target.closest('[data-region]');if(!b)return;var region=b.dataset.region;state.region=state.region===region?null:region;state.selected=null;activate();updateCopy();fit();$('[data-region="'+region+'"]').focus({preventScroll:true});});
    on(search,'input',renderResults);
    on(search,'keydown',function(e){if(e.key==='Escape'){search.value='';renderResults();canvas.focus();}else if(!results.hidden&&search.value.trim()&&(e.key==='ArrowDown'||e.key==='Enter')){var b=results.querySelector('button');if(b){e.preventDefault();if(e.key==='Enter')b.click();else b.focus();}}});
    on(results,'keydown',function(e){var buttons=Array.from(results.querySelectorAll('button')),i=buttons.indexOf(document.activeElement);if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();var next=i+(e.key==='ArrowDown'?1:-1);if(next<0)search.focus();else if(buttons[next])buttons[next].focus();}else if(e.key==='Escape'){results.hidden=true;search.focus();}});
    on(root,'click',function(e){var b=e.target.closest('[data-node]');if(b){select(b.dataset.node,true);inspector.querySelector('h3').focus({preventScroll:true});return;}var a=e.target.closest('[data-action]');if(!a)return;if(a.dataset.action==='clear'){select(null,false);canvas.focus({preventScroll:true});}if(a.dataset.action==='more'){var previousLimit=neighborLimit;neighborLimit=Infinity;renderInspector();var next=inspector.querySelectorAll('[data-node]')[previousLimit];(next||inspector.querySelector('h3')).focus({preventScroll:true});}});
    on(root,'focusout',function(e){if(!$('.nm-search').contains(e.relatedTarget))results.hidden=true;});
    on(document,'visibilitychange',function(){pageVisible=!document.hidden;reconcile();});
    on(global,'resize',resize);
    var appearance=new MutationObserver(function(){var oldZh=state.zh;readAppearance();if(oldZh!==state.zh)updateCopy();invalidate();});
    appearance.observe(document.documentElement,{attributes:true,attributeFilter:['data-theme','data-lang','class']});
    cleanups.push(function(){appearance.disconnect();});
    var resizeObserver=new ResizeObserver(resize);resizeObserver.observe(canvas);cleanups.push(function(){resizeObserver.disconnect();});
    if(global.IntersectionObserver){var observer=new IntersectionObserver(function(entries){onscreen=entries[0].isIntersecting;reconcile();},{threshold:0});observer.observe(canvas);cleanups.push(function(){observer.disconnect();});}
    [media,coarse].forEach(function(m){var change=function(){syncMotionButton();reconcile();};if(m.addEventListener)on(m,'change',change);});
    function destroy(){if(destroyed)return;destroyed=true;if(frame)global.cancelAnimationFrame(frame);frame=0;pointers.clear();cleanups.forEach(function(fn){fn();});if(owners.get(root)===api)owners.delete(root);}
    var api={destroy:destroy};owners.set(root,api);on(global,'pagehide',function(e){if(!e.persisted)destroy();else{pageVisible=false;reconcile();}});on(global,'pageshow',function(){pageVisible=!document.hidden;reconcile();});
    activate();updateCopy();resize();
    if(!ctx||!cacheCtx){canvas.hidden=true;$('.nm-stage-bottom').hidden=true;var fallback=document.createElement('p');fallback.className='nm-fallback';fallback.textContent=t('Canvas is unavailable. Use search and the connection list to explore every node.','画布不可用。可使用搜索和连接列表浏览所有节点。');scene.appendChild(fallback);}
    return api;
  }
  global.NeuralMap={mount:mount,unmount:function(root){var owner=owners.get(root);if(owner)owner.destroy();}};
})(window);
