/* Capacity Fabric Observatory. Native admin page; no external scripts or fonts. */
(() => {
  "use strict";
  const escape = value => String(value == null ? "" : value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const n = value => value == null ? "—" : new Intl.NumberFormat("en", {notation: value >= 10000 ? "compact" : "standard", maximumFractionDigits: value < 100 ? 1 : 0}).format(value);
  const full = value => value == null ? "Not reported" : Number(value).toLocaleString();
  const seconds = value => value == null ? "—" : value < 1 ? `${Math.round(value * 1000)}ms` : value < 60 ? `${value.toFixed(1)}s` : `${Math.floor(value / 60)}m ${Math.floor(value % 60)}s`;
  const short = value => value ? value.slice(0, 6) : "unknown";
  const clock = value => value ? new Date(value * 1000).toLocaleTimeString([], {hour:"2-digit", minute:"2-digit", second:"2-digit"}) : "—";
  const icon = name => {
    const paths = {
      flow:'<path d="M4 6h6l4 12h6M4 18h6L14 6h6"/><circle cx="4" cy="6" r="2"/><circle cx="20" cy="6" r="2"/><circle cx="4" cy="18" r="2"/><circle cx="20" cy="18" r="2"/>',
      refresh:'<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 7a7 7 0 0 1 12-2l2 3M4 16l2 3a7 7 0 0 0 12-2"/>',
      expand:'<path d="M8 3H3v5M16 3h5v5M21 16v5h-5M3 16v5h5"/>',
      search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
      close:'<path d="m6 6 12 12M18 6 6 18"/>',
      arrow:'<path d="M4 12h16m-5-5 5 5-5 5"/>',
      pause:'<path d="M8 5v14M16 5v14"/>',
      play:'<path d="m8 4 12 8-12 8Z"/>',
      download:'<path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/>',
      layers:'<path d="m12 3 10 6-10 6L2 9Zm-9 11 9 5 9-5M3 19l9 5 9-5"/>',
    };
    return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.flow}</svg>`;
  };
  const consumerKey = r => r.agent_id || r.session_id || "unattributed";
  const consumerName = r => r.agent_id ? `Agent ${short(r.agent_id)}` : r.session_id ? `${r.client} · ${short(r.session_id)}` : `${r.client} · unattributed`;
  const modelName = v => String(v || "Unknown model").replace(/^fabric\//, "").replace(/_/g," ");
  let active = null;

  function mount(host, options = {}) {
    unmount();
    const s = {host, options, data:null, view:"flow", minutes:15, query:"", status:"all", model:"all", selected:null,
      paused:false, pending:false, disposed:false, timer:null, tick:null, controller:null, scale:1, page:0, error:null, received:0};
    active = s;
    host.innerHTML = `<section class="cf-shell" aria-label="Capacity Fabric router">
      <header class="cf-hero"><div><div class="cf-eyebrow"><span class="cf-mark">${icon("flow")}</span> INFRASTRUCTURE <span>/</span> ROUTER</div><h1>Capacity Fabric<span class="cf-title-dot">.</span></h1><p>Follow the intelligence. From capacity to every consumer.</p></div>
        <div class="cf-hero-right"><div class="cf-connection" role="status"><i></i><span>Connecting</span><small></small></div><div class="cf-hero-actions"><button data-action="pause" class="cf-button">${icon("pause")}<span>Pause</span></button><button data-action="refresh" class="cf-icon-button" aria-label="Refresh telemetry">${icon("refresh")}</button><button data-action="fullscreen" class="cf-icon-button" aria-label="Toggle full screen">${icon("expand")}</button></div></div></header>
      <div class="cf-notice" hidden role="status"></div><div class="cf-metrics" aria-label="Router metrics"></div>
      <div class="cf-toolbar"><div class="cf-tabs" role="tablist" aria-label="Router views">${[["flow","Flow map"],["requests","Requests"],["providers","Providers"],["overflow","Overflow"],["claude","Claude lanes"],["consumers","Consumers"]].map(([id,title])=>`<button role="tab" data-view="${id}" aria-selected="${id==="flow"}" class="${id==="flow"?"is-active":""}">${title}<span data-count="${id}"></span></button>`).join("")}</div><div class="cf-toolbar-right"><span class="cf-window-label">Window</span><select aria-label="Observation time window" data-field="window"><option value="5">5 minutes</option><option value="15" selected>15 minutes</option><option value="60">1 hour</option><option value="120">2 hours</option></select><button data-action="export" class="cf-icon-button" aria-label="Export sanitized snapshot">${icon("download")}</button></div></div>
      <div class="cf-filters"><label class="cf-search">${icon("search")}<input data-field="search" placeholder="Find a model, route or session…" aria-label="Search router telemetry"><kbd>/</kbd></label><select data-field="model" aria-label="Filter by model"><option value="all">All models</option></select><select data-field="status" aria-label="Filter by request state"><option value="all">All activity</option><option value="streaming">Streaming</option><option value="waiting">Awaiting output</option><option value="completed">Completed</option><option value="failed">Errors & interruptions</option></select><button class="cf-clear" data-action="clear" hidden>Clear selection ×</button></div>
      <div class="cf-view" role="tabpanel"></div><footer class="cf-footer"><span>Capacity Fabric <i>•</i> Private telemetry</span><span class="cf-footnote">Connecting to the router observer…</span></footer>
      <aside class="cf-inspector" hidden aria-label="Selected traffic details"><div class="cf-inspector-bar"><span>INSPECTOR</span><button class="cf-icon-button" data-action="close" aria-label="Close inspector">${icon("close")}</button></div><div class="cf-inspector-body"></div></aside>
    </section>`;
    s.root = host.querySelector(".cf-shell");
    s.root.addEventListener("click", e => handleClick(s, e));
    s.root.addEventListener("input", e => {
      if (e.target.dataset.field === "search") { s.query = e.target.value; s.page=0; renderView(s); }
    });
    s.root.addEventListener("change", e => {
      const field=e.target.dataset.field;
      if(field==="window") {s.minutes=Number(e.target.value); s.page=0; load(s);}
      if(field==="model" || field==="status") {s[field]=e.target.value; s.page=0; renderView(s);}
    });
    s.keydown = e => {
      if(s.disposed || !s.host.isConnected || (options.isCurrent && !options.isCurrent())) return;
      if(e.key === "Escape") {s.selected=null; renderInspector(s); renderView(s);}
      if(e.key === "/" && !/INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) {e.preventDefault(); s.root.querySelector("input").focus();}
      if((e.key === "Enter" || e.key === " ") && e.target.matches("[data-select]")) {e.preventDefault(); e.target.dispatchEvent(new MouseEvent("click",{bubbles:true}));}
    };
    s.visibility = () => {if(!document.hidden && !s.paused) {clearTimeout(s.timer); load(s);} updateConnection(s);};
    document.addEventListener("keydown", s.keydown);
    document.addEventListener("visibilitychange", s.visibility);
    s.tick=setInterval(()=>updateConnection(s),1000);
    renderMetrics(s); renderView(s); load(s);
    return s;
  }

  function unmount() {
    if(!active) return;
    const s=active; s.disposed=true; clearTimeout(s.timer); clearInterval(s.tick);
    if(s.controller) s.controller.abort();
    document.removeEventListener("keydown",s.keydown); document.removeEventListener("visibilitychange",s.visibility);
    active=null;
  }

  async function load(s) {
    if(s.disposed || s.pending) return;
    if(!s.host.isConnected || (s.options.isCurrent && !s.options.isCurrent())) {unmount(); return;}
    clearTimeout(s.timer);
    if(s.paused || document.hidden) {s.timer=setTimeout(()=>load(s),3000);return;}
    s.pending=true; s.controller=new AbortController();
    const timeout=setTimeout(()=>s.controller.abort(),8000);
    try {
      const response=await fetch(`/api/capacity-router?minutes=${s.minutes}`,{credentials:"same-origin",cache:"no-store",signal:s.controller.signal});
      if(response.status===401) {unmount(); if(s.options.onAuthFailure) s.options.onAuthFailure(); return;}
      if(!response.ok) throw new Error("Telemetry could not be read");
      const data=await response.json();
      if(s.disposed || s.paused) return;
      if(s.data && data.epoch && data.epoch===s.data.epoch && data.sequence<s.data.sequence) return;
      s.data=data; s.received=Date.now(); s.error=null;
      const select=s.root.querySelector('[data-field="model"]');
      const models=[...new Set((data.routes||[]).flatMap(r=>r.models))].sort();
      const keys=models.join("|");
      if(s.modelKeys!==keys) {s.modelKeys=keys;select.innerHTML='<option value="all">All models</option>'+models.map(m=>`<option value="${escape(m)}">${escape(modelName(m))}</option>`).join("");select.value=s.model;}
      renderMetrics(s); renderView(s); renderInspector(s); updateConnection(s);
    } catch(error) {
      if(!s.disposed) {s.error="Telemetry connection interrupted. Last received measurements remain visible."; updateConnection(s); if(!s.data) renderView(s);}
    } finally {
      clearTimeout(timeout); s.pending=false;
      if(!s.disposed) s.timer=setTimeout(()=>load(s),2000);
    }
  }

  function updateConnection(s) {
    if(s.disposed || !s.root.isConnected) return;
    const d=s.data, age=d&&d.generated_at ? Math.max(0,Date.now()/1000-d.generated_at):null;
    const state=s.paused?"paused":s.error?"disconnected":!d?"connecting":!d.ok?"disconnected":age>15?"stale":"live";
    s.root.dataset.connection=state;
    s.root.dataset.hidden=String(document.hidden);
    s.root.querySelector(".cf-connection").innerHTML=`<i></i><span>${{live:"Live telemetry",paused:"Paused",stale:"Telemetry stale",disconnected:"Disconnected",connecting:"Connecting"}[state]}</span><small>${age==null?"":`${Math.floor(age)}s ago`}</small>`;
    const notice=s.root.querySelector(".cf-notice");
    const drops=d&&d.totals&&(d.totals.dropped_requests+d.totals.observer_errors);
    const truncated=d&&d.truncated?Object.values(d.truncated).reduce((a,v)=>a+v,0):0;
    const msg=s.error || (d&&!d.ok?d.message:truncated?`Snapshot compacted to keep live traffic visible: ${n(d.truncated.recent)} older requests, ${n(d.truncated.attempts)} attempt details and ${n(d.truncated.models)} model labels omitted.`:state==="stale"?"The observer has not updated recently. These are the last received measurements; router availability is unknown.":drops?`Observation coverage is partial: ${n(d.totals.dropped_requests)} untracked requests and ${n(d.totals.observer_errors)} observation errors.`:"");
    notice.hidden=!msg; notice.textContent=msg;
    s.root.querySelector(".cf-footnote").textContent=d&&d.ok?`2s snapshots · observed since ${clock(d.started_at)} · ${d.limits.recent} recent requests retained · no prompt content` : "Private, read-only observation of the existing router";
  }

  function renderMetrics(s) {
    const d=s.data, v=d&&d.ok?d.summary:{};
    const cards=[
      ["Concurrent requests",v.active_requests,`${n(v.awaiting_output)} awaiting first output`,"teal"],
      ["Reported output / sec",v.output_tokens_per_s,"Window average · completed usage","blue"],
      ["Output tokens",v.output_tokens,`${n(v.input_tokens)} input · selected window`,"violet"],
      ["First content · p50",v.p50_first_content_ms==null?null:seconds(v.p50_first_content_ms/1000),`p95 ${seconds(v.p95_first_content_ms==null?null:v.p95_first_content_ms/1000)} · ${n(v.first_content_samples)} samples`,""],
      ["Known consumers",v.active_consumers,`${n(v.unattributed_active)} active requests unattributed`,""],
      ["Route capacity",v.ready_routes==null?null:`${v.ready_routes} / ${(d.routes||[]).length}`,`${n(v.cooling_routes)} cooling · ${n(v.providers)} providers`,""],
    ];
    if(d&&d.ok&&(d.overflow||d.claude)) cards.push(["Overflow & lanes",v.overflowing_families==null?null:v.overflowing_families,`${n(v.benched_lanes)} Claude lanes benched · ${n(v.over_target_keys)} seats over target${d.peak&&d.peak.active?" · peak active":""}`,"violet"]);
    s.root.querySelector(".cf-metrics").innerHTML=cards.map(([title,value,sub,color])=>`<article class="cf-metric ${color}"><div>${title}</div><strong>${typeof value==="string"?value:n(value)}</strong><small>${sub}</small></article>`).join("");
    const counts={requests:d&&d.ok?(d.active.length+d.recent.length):null,providers:v.providers,consumers:v.active_consumers,
      overflow:d&&d.ok&&d.overflow?Object.values(d.overflow.families||{}).filter(f=>f.overflowing).length:null,
      claude:d&&d.ok&&d.claude?(d.claude.accounts||[]).length:null};
    Object.entries(counts).forEach(([key,val])=>{s.root.querySelector(`[data-count="${key}"]`).textContent=val==null?"":val;});
  }

  function allRecords(s) {return s.data ? [...(s.data.active||[]),...(s.data.recent||[])]:[];}
  function matchesSelection(r, selection) {
    if(!selection || selection.kind==="request") return true;
    const {kind,id}=selection;
    return kind==="provider"?r.provider===id:kind==="model"?(r.served_model===id||r.requested_model===id):kind==="lane"?r.lane===id:kind==="consumer"?consumerKey(r)===id:kind==="route"?r.route_id===id:true;
  }
  function records(s) {
    const q=s.query.toLowerCase();
    return allRecords(s).filter(r=>matchesSelection(r,s.selected))
      .filter(r=>s.model==="all"||r.served_model===s.model||r.requested_model===s.model)
      .filter(r=>s.status==="all" || (s.status==="waiting"? ["routing","waiting"].includes(r.state):s.status==="failed"?["failed","interrupted","cancelled"].includes(r.state):r.state===s.status))
      .filter(r=>!q||[consumerName(r),r.id,r.served_model,r.requested_model,r.provider,r.route_id,r.lane,r.client,r.project_id||""].join(" ").toLowerCase().includes(q));
  }

  function empty(title, detail) {return `<div class="cf-empty"><span>${icon("flow")}</span><h3>${escape(title)}</h3><p>${escape(detail)}</p></div>`;}

  function renderView(s) {
    const view=s.root.querySelector(".cf-view");
    const focused=document.activeElement;
    const focus=s.root.contains(focused)&&focused.dataset.select?{kind:focused.dataset.select,id:focused.dataset.id}:null;
    s.root.querySelectorAll("[data-view]").forEach(el=>{el.classList.toggle("is-active",el.dataset.view===s.view);el.setAttribute("aria-selected",String(el.dataset.view===s.view));});
    s.root.querySelector(".cf-clear").hidden=!s.selected&&!s.query&&s.model==="all"&&s.status==="all";
    if(!s.data || !s.data.ok) {
      view.innerHTML=`<div class="cf-panel cf-initial">${empty(s.error?"Connection interrupted":s.data?"Waiting for the router":"Opening the fabric",s.data?s.data.message:"Connecting the provider, model and consumer layers.")}<div class="cf-initial-grid"><span>PROVIDERS</span><span>MODELS</span><span>ROUTING LANES</span><span>CONSUMERS</span></div></div>`;
      return;
    }
    if(s.view==="flow") {
      const scroll=view.querySelector(".cf-map-scroll"); const scrollLeft=scroll?scroll.scrollLeft:0;
      const oldSvg=view.querySelector(".cf-topology");const motionTime=oldSvg&&oldSvg.getCurrentTime?oldSvg.getCurrentTime():0;
      view.innerHTML=flowMap(s)+`<div class="cf-lower-grid">${trend(s)}${health(s)}</div>`+requestTable(s,8);
      view.querySelector(".cf-map-scroll").scrollLeft=scrollLeft;
      const newSvg=view.querySelector(".cf-topology");if(newSvg&&newSvg.setCurrentTime)newSvg.setCurrentTime(motionTime);
    } else if(s.view==="requests") view.innerHTML=requestTable(s,50,true);
    else if(s.view==="providers") view.innerHTML=providerView(s);
    else if(s.view==="overflow") view.innerHTML=overflowView(s);
    else if(s.view==="claude") view.innerHTML=claudeView(s);
    else view.innerHTML=consumerView(s);
    if(focus) {const el=[...view.querySelectorAll("[data-select]")].find(x=>x.dataset.select===focus.kind&&x.dataset.id===focus.id);if(el)el.focus({preventScroll:true});}
  }

  function flowMap(s) {
    const d=s.data, rs=records(s), activeIds=new Set(d.active.map(r=>r.id));
    const routes=d.routes.filter(r=>(s.model==="all"||r.models.includes(s.model))&&(!s.query||[r.id,r.provider,...r.models].join(" ").toLowerCase().includes(s.query.toLowerCase())||rs.some(x=>x.route_id===r.id)));
    const weights=new Map();
    const bump=(kind,id,record)=>{const key=kind+":"+id;if(!weights.has(key))weights.set(key,{requests:0,active:0,tokens:0,known:0});const w=weights.get(key);w.requests++;w.active+=activeIds.has(record.id)?1:0;w.tokens+=record.usage.output_tokens||0;w.known+=record.usage.output_tokens!=null?1:0;};
    rs.forEach(r=>{bump("provider",r.provider,r);bump("model",r.served_model||r.requested_model,r);bump("lane",r.lane,r);bump("consumer",consumerKey(r),r);});
    const rank=kind=>(a,b)=>{const x=weights.get(kind+":"+a)||{},y=weights.get(kind+":"+b)||{};return (y.active||0)-(x.active||0)||(y.requests||0)-(x.requests||0)||a.localeCompare(b);};
    const providers=[...new Set(routes.map(r=>r.provider))].sort(rank("provider"));
    const models=[...new Set(routes.flatMap(r=>r.models))].sort(rank("model"));
    const lanes=[...new Set(["direct",...Object.keys(d.aliases),...rs.map(r=>r.lane)])].sort(rank("lane"));
    const consumers=[...new Set(rs.map(consumerKey))].sort(rank("consumer"));
    const columns=[{kind:"provider",title:"PROVIDERS & POOLS",ids:providers,x:124},{kind:"model",title:"MODELS",ids:models,x:387},{kind:"lane",title:"ROUTING LANES",ids:lanes,x:650},{kind:"consumer",title:"DOWNSTREAM CONSUMERS",ids:consumers,x:913}];
    const nodes=[], byKey=new Map();
    columns.forEach(col=>{const ids=col.ids.slice(0,7), step=62, top=90+(7-ids.length)*step/2;ids.forEach((id,i)=>{const node={...col,id,y:top+i*step,weight:weights.get(col.kind+":"+id)||{requests:0,active:0,tokens:0,known:0}};nodes.push(node);byKey.set(col.kind+":"+id,node);});});
    const edges=new Map();
    const edge=(a,b,record)=>{if(!byKey.has(a)||!byKey.has(b))return;const key=a+"|"+b;if(!edges.has(key))edges.set(key,{a:byKey.get(a),b:byKey.get(b),count:0,active:0,tokens:0,known:0});const e=edges.get(key);if(record){e.count++;e.tokens+=record.usage.output_tokens||0;e.known+=record.usage.output_tokens!=null?1:0;e.active+=activeIds.has(record.id)&&record.state==="streaming"?1:0;}};
    routes.forEach(r=>r.models.forEach(m=>edge("provider:"+r.provider,"model:"+m)));
    Object.entries(d.aliases).forEach(([lane,targets])=>targets.forEach(m=>edge("model:"+m,"lane:"+lane)));
    rs.forEach(r=>{const m=r.served_model||r.requested_model;edge("provider:"+r.provider,"model:"+m,r);edge("model:"+m,"lane:"+r.lane,r);edge("lane:"+r.lane,"consumer:"+consumerKey(r),r);});
    let edgeIndex=0;
    const paths=[...edges.values()].map(e=>{const path=`M${e.a.x+91},${e.a.y} C${e.a.x+140},${e.a.y} ${e.b.x-140},${e.b.y} ${e.b.x-91},${e.b.y}`;const id="cf-edge-"+(edgeIndex++);return `<g class="cf-edge ${e.count?"observed":"configured"} ${e.active?"streaming":""}"><path id="${id}" d="${path}" stroke-width="${e.count?Math.min(4,1.3+Math.log2(e.count+1)*.35):1}"/><title>${e.count?`${e.count} observed requests · ${e.known?full(e.tokens):"Unknown"} reported output tokens`:"Configured route; no observed traffic in this window"}</title>${e.active?`<circle r="2.7"><animateMotion dur="${2.2+(edgeIndex%4)*.3}s" repeatCount="indefinite" path="${path}"/></circle>`:""}</g>`;}).join("");
    const nodeMarkup=nodes.map(node=>{
      const {kind,id,x,y,weight}=node;
      const r=rs.find(r=>consumerKey(r)===id);
      const title=kind==="consumer"?(id==="unattributed"?"Unattributed":r?consumerName(r):id):kind==="lane"?(id==="direct"?"Direct model":modelName(id)):kind==="model"?modelName(id):id;
      const meta=kind==="provider"?`${routes.filter(r=>r.provider===id).length} routes · ${weight.active} active`:kind==="model"?`${weight.active} active · ${weight.requests} calls`:kind==="lane"?(id==="direct"?"Exact model selection":`${(d.aliases[id]||[]).length} model cascade`):`${weight.active} active · ${weight.requests} calls`;
      const cooling=kind==="provider"&&routes.filter(r=>r.provider===id).every(r=>r.cooling);
      const sel=s.selected&&s.selected.kind===kind&&s.selected.id===id;
      return `<g class="cf-node ${kind} ${weight.active?"has-activity":""} ${cooling?"cooling":""} ${sel?"selected":""}" role="button" tabindex="0" aria-label="Inspect ${escape(title)}" data-select="${kind}" data-id="${escape(id)}" transform="translate(${x-91},${y-25})"><rect width="182" height="50" rx="10"/><circle cx="15" cy="17" r="3"/><text x="27" y="21" class="cf-node-title">${escape(title.length>23?title.slice(0,21)+"…":title)}</text><text x="15" y="38" class="cf-node-sub">${escape(meta)}</text>${weight.active?`<circle class="cf-node-pulse" cx="166" cy="17" r="3"/>`:""}<title>${escape(title)} · ${weight.known?full(weight.tokens):"Unknown"} reported output tokens</title></g>`;
    }).join("");
    const headers=columns.map(col=>`<text x="${col.x-91}" y="31" class="cf-column-title">${col.title}</text><text x="${col.x+91}" y="31" text-anchor="end" class="cf-column-count">${col.ids.length}</text>${col.ids.length>7?`<text x="${col.x}" y="515" text-anchor="middle" class="cf-overflow">+ ${col.ids.length-7} more · use filters</text>`:""}`).join("");
    const blank=consumers.length?"":`<g><rect x="822" y="230" width="182" height="104" rx="12" class="cf-ghost"/><text x="913" y="269" text-anchor="middle" class="cf-node-title">Awaiting activity</text><text x="913" y="292" text-anchor="middle" class="cf-node-sub">Consumers appear as</text><text x="913" y="309" text-anchor="middle" class="cf-node-sub">requests are observed</text></g>`;
    return `<section class="cf-panel cf-map-panel"><div class="cf-panel-heading"><div><span class="cf-section-kicker">LIVE TOPOLOGY</span><h2>From inference to impact</h2></div><div class="cf-map-legend"><span><i class="teal"></i>Observed activity</span><span><i class="gray"></i>Configured path</span><span><i class="amber"></i>Cooling</span></div></div><div class="cf-map-scroll"><svg class="cf-topology" viewBox="0 0 1040 540" style="width:${s.scale*100}%" role="group" aria-label="Output flows from providers through models and routing lanes to observed consumers"><defs><pattern id="cf-dots" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".7" fill="currentColor"/></pattern><linearGradient id="cf-path" x1="0" x2="1"><stop offset="0" stop-color="#56d9c4"/><stop offset="1" stop-color="#9f91f2"/></linearGradient></defs><rect width="1040" height="540" fill="url(#cf-dots)" class="cf-dot-grid"/>${headers}${paths}${nodeMarkup}${blank}</svg></div><div class="cf-map-bottom"><span>${icon("arrow")} Output direction <b>Provider → Consumer</b><em>Particles represent streaming activity.</em></span><div><button data-action="zoom-out" aria-label="Zoom out">−</button><button data-action="fit">${Math.round(s.scale*100)}%</button><button data-action="zoom-in" aria-label="Zoom in">+</button></div></div></section>`;
  }

  function trend(s) {
    const d=s.data,buckets=d.series||[];const max=Math.max(1,...buckets.map(b=>b.output_tokens));
    const start=Math.max(d.started_at,Date.now()/1000-s.minutes*60),end=Date.now()/1000;
    const width=620,height=102;
    const bars=buckets.map(b=>{const x=Math.max(0,Math.min(width-4,(b.at-start)/(end-start||1)*width));const w=Math.max(2,Math.min(28,width/(s.minutes||1)*.75));const h=b.output_tokens/max*(height-12);return `<rect x="${x.toFixed(2)}" y="${height-h}" width="${w}" height="${Math.max(h,1)}" rx="2"><title>${clock(b.at)} · ${full(b.output_tokens)} output tokens · ${b.completed+b.failed} finished requests</title></rect>`;}).join("");
    return `<section class="cf-panel cf-trend"><div class="cf-panel-heading"><div><span class="cf-section-kicker">THROUGHPUT</span><h2>Reported output</h2></div><strong>${n(d.summary.output_tokens)} <small>tokens</small></strong></div><div class="cf-trend-chart"><span class="cf-chart-max">${n(max)} / min</span><svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Reported output tokens in minute buckets"><path d="M0 25H620M0 63H620M0 102H620" class="cf-grid-line"/>${bars}</svg>${!d.summary.usage_known?'<span class="cf-chart-empty">Awaiting provider usage reports</span>':""}</div><div class="cf-axis"><span>${clock(start)}</span><span>Usage recorded at completion · minute buckets</span><span>Now</span></div></section>`;
  }

  function health(s) {
    const d=s.data,v=d.summary,total=v.completed+v.failed,ratio=total?100*v.completed/total:0;
    return `<section class="cf-panel cf-health"><div class="cf-panel-heading"><div><span class="cf-section-kicker">OBSERVATION QUALITY</span><h2>Know what is known</h2></div><span class="cf-quality">${v.usage_coverage_pct==null?"—":v.usage_coverage_pct+"%"}</span></div><div class="cf-health-row"><span>Requests with output usage</span><b>${v.usage_known} / ${total}</b></div><div class="cf-meter"><i style="width:${v.usage_coverage_pct||0}%"></i></div><div class="cf-health-stats"><div><b>${n(v.completed)}</b><span>Completed</span></div><div><b class="${v.failed?"cf-amber-text":""}">${n(v.failed)}</b><span>Errors / partial</span></div><div><b>${v.recent_count?Math.round(v.attributed_recent/v.recent_count*100)+"%":"—"}</b><span>Known consumer</span></div></div><p>Missing usage stays unknown. Agent relations appear only when the caller reports them.</p></section>`;
  }

  function requestTable(s, limit, paginated=false) {
    const rs=records(s), pages=Math.max(1,Math.ceil(rs.length/limit));s.page=Math.min(s.page,pages-1);
    const rows=rs.slice(paginated?s.page*limit:0,paginated?(s.page+1)*limit:limit);
    const body=rows.map(r=>{const duration=(r.ended_at||s.data.generated_at)-r.started_at;const first=r.first_content_at==null?null:r.first_content_at-r.started_at;return `<tr tabindex="0" role="button" data-select="request" data-id="${r.id}" aria-label="Inspect request ${short(r.id)}"><td><span class="cf-consumer-glyph">${r.agent_id?"A":r.session_id?"S":"?"}</span><div><b>${escape(consumerName(r))}</b><small>${clock(r.started_at)} <span>· ${short(r.id)}</span></small></div></td><td><b>${escape(modelName(r.served_model||r.requested_model))}</b><small>${escape(r.lane==="direct"?"Direct model":r.lane)}</small></td><td><b>${escape(r.provider||"Routing")}</b><small>${escape(r.route_id||"Route not selected")}</small></td><td><span class="cf-state ${r.state}"><i></i>${{routing:"Routing",waiting:"Awaiting output",streaming:"Streaming",completed:"Completed",failed:"Failed",cancelled:"Cancelled",interrupted:"Interrupted"}[r.state]||r.state}</span>${r.attempts.length>1?`<small class="cf-fallback">${r.attempts.length} attempts</small>`:""}</td><td class="cf-mono">${seconds(first)}</td><td class="cf-mono">${n(r.usage.input_tokens)} <span class="cf-slash">/</span> ${n(r.usage.output_tokens)}${r.usage_source==="unavailable"?'<small>Not reported</small>':!r.usage_final?'<small>Partial usage</small>':""}</td><td class="cf-mono">${seconds(duration)}</td></tr>`;}).join("");
    return `<section class="cf-panel cf-request-panel"><div class="cf-panel-heading"><div><span class="cf-section-kicker">REQUEST EXPLORER</span><h2>${paginated?"Every observed request":"Recent traffic"} <span class="cf-count-badge">${rs.length}</span></h2></div>${!paginated?'<button class="cf-text-button" data-view="requests">Explore all requests →</button>':`<span class="cf-muted">${s.data.active.length} in flight · ${s.data.recent.length} retained in window</span>`}</div>${rows.length?`<div class="cf-table-scroll"><table><thead><tr><th>Consumer</th><th>Model / lane</th><th>Provider / route</th><th>State</th><th>First content</th><th>Input / output</th><th>Duration</th></tr></thead><tbody>${body}</tbody></table></div>`:empty("No matching requests",s.query||s.selected||s.model!=="all"?"Clear the filters or choose a different observation window.":"Real requests will appear here as they pass through Capacity Fabric.")}${paginated?`<div class="cf-pagination"><span>Showing ${rs.length? s.page*limit+1:0}–${Math.min(rs.length,(s.page+1)*limit)} of ${rs.length}</span><div><button data-action="previous" ${s.page===0?"disabled":""}>← Previous</button><span>${s.page+1} / ${pages}</span><button data-action="next" ${s.page===pages-1?"disabled":""}>Next →</button></div></div>`:""}</section>`;
  }

  function providerView(s) {
    const d=s.data,eligible=d.routes.filter(r=>s.model==="all"||r.models.includes(s.model)),providers=[...new Set(eligible.map(r=>r.provider))].filter(p=>!s.query||d.routes.some(r=>r.provider===p&&[p,r.id,...r.models].join(" ").toLowerCase().includes(s.query.toLowerCase())));
    const cards=providers.map(p=>{const routes=eligible.filter(r=>r.provider===p),models=[...new Set(routes.flatMap(r=>r.models))];const req=allRecords(s).filter(r=>r.provider===p),live=d.active.filter(r=>r.provider===p).length;return `<article class="cf-provider-card"><button class="cf-provider-top" data-select="provider" data-id="${escape(p)}"><span class="cf-provider-symbol">${escape(p.slice(0,2).toUpperCase())}</span><span><strong>${escape(p)}</strong><small>${routes.length} routes · ${models.length} models</small></span><span class="cf-provider-live">${live}<small>active</small></span></button><div class="cf-provider-models">${models.slice(0,8).map(m=>`<button data-select="model" data-id="${escape(m)}">${escape(modelName(m))}</button>`).join("")}${models.length>8?`<span>+${models.length-8} more</span>`:""}</div><div class="cf-provider-routes">${routes.map(r=>`<button data-select="route" data-id="${escape(r.id)}"><i class="${r.cooling?"cooling":""}"></i><span>${escape(r.id)}<small>${escape(r.wire)} · base priority ${r.priority} · weight ${r.weight}</small></span><b>${r.cooling?"Cooling":"No cooldown"}</b></button>`).join("")}</div><div class="cf-provider-bottom"><span>${n(routes.reduce((a,r)=>a+r.served,0))} responses started</span><span>${n(routes.reduce((a,r)=>a+r.attempt_failed,0))} failed attempts</span></div></article>`;}).join("");
    return `<div class="cf-view-intro"><div><span class="cf-section-kicker">CAPACITY INVENTORY</span><h2>One fabric. Every provider.</h2><p>Actual route configuration and cooldown state. Counters are since the current router process started.</p></div><span>${d.routes.length} routes / ${d.summary.models} models</span></div><div class="cf-provider-grid">${cards||empty("No matching providers","Try a model name or clear your search.")}</div>`;
  }

  function overflowView(s) {
    const d=s.data, ov=d.overflow;
    if(!ov) return `<div class="cf-view-intro"><div><span class="cf-section-kicker">FAMILY DIVERSION</span><h2>Overflow ladders</h2><p>When a family's primary pool cools down, new sessions climb a configured ladder to another family. Sticky sessions never hop rungs mid-flight.</p></div></div>${empty("No overflow observation","The router has not reported overflow state yet. It appears once the observer publishes an enriched snapshot.")}`;
    const families=Object.entries(ov.families||{});
    const cards=families.map(([name,fam])=>{
      const targets=fam.targets||[];
      const rungs=[`<li class="cf-rung ${fam.overflowing?"":"current"}"><span>${escape(name)} primary</span><small>family pool</small></li>`]
        .concat(targets.map((t,i)=>`<li class="cf-rung ${fam.overflowing&&i===0?"current":""}"><button data-select="model" data-id="${escape(t)}">${escape(modelName(t))}</button><small>rung ${i+1}</small></li>`));
      return `<article class="cf-overflow-card ${fam.overflowing?"overflowing":""}">
        <div class="cf-overflow-head"><strong>${escape(name)}</strong>
          <span class="cf-state ${fam.overflowing?"failed":"completed"}"><i></i>${fam.overflowing?"Overflowing":"Primary healthy"}</span>
          ${fam.signal?`<small class="cf-muted">signal: ${escape(fam.signal)}</small>`:""}
          ${fam.proactive_window_open?'<small class="cf-amber-text">proactive window open</small>':""}
        </div>
        <ol class="cf-rungs">${rungs.join("")}</ol>
        <div class="cf-overflow-meta">
          ${fam.overflowing?`<span>overflowing ${seconds(fam.overflowing_for_s)}</span><span>recheck in ${seconds(fam.healthy_in_s)}</span>`:`<span>ladder idle</span>`}
        </div>
      </article>`;
    }).join("");
    const keys=Object.entries(ov.keys||{});
    const keyCards=keys.map(([name,k])=>`<article class="cf-key-card ${k.over_target?"over":""}">
      <strong>${escape(name)}</strong>
      <div class="cf-meter"><i style="width:${Math.min(100,k.used_pct_of_limit||0)}%"></i></div>
      <div class="cf-key-stats"><span>${k.used_pct_of_limit==null?"—":k.used_pct_of_limit+"%"} of limit</span><span>${k.over_target?"over target":"within target"}</span></div>
      <small class="cf-muted">${k.input_tpm_limit!=null?`${n(k.used_or_reserved)} / ${n(k.input_tpm_limit)} TPM · local estimate`:"limit not reported"}</small>
    </article>`).join("");
    const events=(ov.recent||[]).slice(-10).reverse().map(e=>`<tr><td><b>${escape(e.event)}</b><small>${escape(e.kind||"")}</small></td><td>${escape(e.family||"—")}</td><td>${escape(modelName(e.requested_model))} → ${escape(modelName(e.served_model))}</td><td>${escape(e.route||"—")}</td><td class="cf-mono">${clock(e.t)}</td></tr>`).join("");
    return `<div class="cf-view-intro"><div><span class="cf-section-kicker">FAMILY DIVERSION</span><h2>Overflow ladders</h2><p>When a family's primary pool cools down, new sessions climb this ladder. Sticky sessions never hop rungs mid-flight. Seat pressure is a local router estimate, never a provider balance.</p></div>
      <span>${ov.enabled?"enabled":"disabled"} · ${n(ov.diverted_requests)} diverted · ${ov.diversion_share==null?"—":Math.round(ov.diversion_share*100)+"%"} share</span></div>
      <div class="cf-overflow-grid">${cards||empty("No families configured","Overflow families appear when the router policy defines them.")}</div>
      ${keys.length?`<section class="cf-panel cf-keys-panel"><div class="cf-panel-heading"><div><span class="cf-section-kicker">SEAT PRESSURE</span><h2>Token-rate targets</h2></div><span class="cf-muted">${keys.filter(([_,k])=>k.over_target).length} over target</span></div><div class="cf-key-grid">${keyCards}</div></section>`:""}
      ${events?`<section class="cf-panel"><div class="cf-panel-heading"><div><span class="cf-section-kicker">DIVERSION LOG</span><h2>Recent overflow events</h2></div></div><div class="cf-table-scroll"><table><thead><tr><th>Event</th><th>Family</th><th>Requested → served</th><th>Route</th><th>Time</th></tr></thead><tbody>${events}</tbody></table></div></section>`:""}`;
  }

  function claudeView(s) {
    const d=s.data, cl=d.claude;
    if(!cl) return `<div class="cf-view-intro"><div><span class="cf-section-kicker">ANTHROPIC GATEWAY</span><h2>Claude family lanes</h2><p>Weekly budgets per account and family, with the shared 5-hour window. Benched lanes recover at their reset; a reset time alone does not restore capacity.</p></div></div>${empty("No gateway observation","The observer has not cached a gateway lane reading yet. It polls the incumbent gateway every 30 seconds.")}`;
    if(!cl.reachable) return `<div class="cf-view-intro"><div><span class="cf-section-kicker">ANTHROPIC GATEWAY</span><h2>Claude family lanes</h2></div></div>${empty("Gateway unreachable","Lane budgets are unknown. The last observation is not shown as current.")}`;
    const nowS=Date.now()/1000;
    const cards=(cl.accounts||[]).map(a=>{
      const lanes=Object.entries(a.families||{}).map(([name,lane])=>{
        const benched=lane.cooldown_until!=null&&lane.cooldown_until>nowS;
        const pct=lane.budget_weekly&&lane.remaining_weekly!=null?Math.max(0,Math.min(100,lane.remaining_weekly/lane.budget_weekly*100)):null;
        const reset=lane.weekly_resets_at!=null?`resets ${clock(lane.weekly_resets_at)}${lane.weekly_reset_source==="estimated"?" (est.)":""}`:"";
        return `<div class="cf-lane ${benched?"benched":""}">
          <div class="cf-lane-head"><span>${escape(name)}</span>${lane.expiring_soon?'<small class="cf-amber-text">expiring soon</small>':""}${benched?'<small class="cf-red-text">benched</small>':""}</div>
          ${pct!=null?`<div class="cf-meter"><i style="width:${pct}%"></i></div><small>${Math.round(pct)}% left · ${n(lane.remaining_weekly)} / ${n(lane.budget_weekly)}</small>`:'<small class="cf-muted">budget unknown</small>'}
          <small class="cf-muted">${benched?`until ${clock(lane.cooldown_until)}`:reset}</small>
        </div>`;
      }).join("");
      const pct5=a.budget_5h?Math.max(0,Math.min(100,(a.remaining_5h!=null?a.remaining_5h:a.budget_5h-a.used_5h)/a.budget_5h*100)):null;
      return `<article class="cf-claude-card">
        <div class="cf-claude-head"><strong>${escape(a.label||a.id)}</strong>
          ${a.drain?'<span class="cf-state cancelled"><i></i>draining</span>':""}
          ${a.inflight?`<small class="cf-muted">${a.inflight} in flight</small>`:""}
          <small class="cf-muted">${escape(a.last_status||"")}</small></div>
        <div class="cf-claude-5h"><span>Shared 5h window</span>${pct5!=null?`<div class="cf-meter"><i style="width:${pct5}%"></i></div><small>${n(a.used_5h)} used / ${n(a.budget_5h)}</small>`:'<small class="cf-muted">not reported</small>'}</div>
        <div class="cf-lane-grid">${lanes}</div>
      </article>`;
    }).join("");
    return `<div class="cf-view-intro"><div><span class="cf-section-kicker">ANTHROPIC GATEWAY</span><h2>Claude family lanes</h2><p>Weekly budgets per account and family, with the shared 5-hour window. Reset times are provider-reported unless marked estimated. Observed ${clock(cl.observed_at)}.</p></div>
      <span>${(cl.accounts||[]).length} accounts${cl.stranded_family?` · stranded boost: ${escape(cl.stranded_family)}`:""}</span></div>
      ${cl.preferences&&cl.preferences.length?`<p class="cf-muted cf-prefs">Account preferences: ${cl.preferences.map(escape).join(", ")}</p>`:""}
      <div class="cf-claude-grid">${cards||empty("No accounts observed","The gateway reported no accounts.")}</div>`;
  }

  function consumerView(s) {
    const rs=records(s),groups=new Map();rs.forEach(r=>{const id=consumerKey(r);if(!groups.has(id))groups.set(id,[]);groups.get(id).push(r);});
    const known=[...groups.entries()].filter(([id])=>id!=="unattributed"),unknown=groups.get("unattributed")||[];
    const cards=known.map(([id,list])=>{const latest=list[0],active=list.filter(r=>!r.ended_at).length,parent=latest.parent_agent_id;const parentPresent=parent&&groups.has(parent);return `<article class="cf-consumer-card"><button data-select="consumer" data-id="${id}" class="cf-consumer-card-head"><span class="cf-consumer-glyph">${latest.agent_id?"A":"S"}</span><span><strong>${escape(consumerName(latest))}</strong><small>${escape(latest.client)} · ${latest.agent_id?"Caller-reported agent":latest.identity_source==="sdk_session"?"SDK session":"Caller-reported session"}</small></span><span class="cf-active-count">${active}<small>active</small></span></button>${parent?`<div class="cf-parent-line">↳ Parent ${parentPresent?`<button data-select="consumer" data-id="${parent}">Agent ${short(parent)}</button>`:`<span>${short(parent)} · outside retained window</span>`}</div>`:""}<div class="cf-consumer-models">${[...new Set(list.map(r=>r.served_model||r.requested_model))].slice(0,6).map(m=>`<span>${escape(modelName(m))}</span>`).join("")}</div><div class="cf-consumer-stats"><div><b>${list.length}</b><small>Requests</small></div><div><b>${list.some(r=>r.usage.output_tokens!=null)?n(list.reduce((a,r)=>a+(r.usage.output_tokens||0),0)):"—"}</b><small>Reported output</small></div><div><b>${latest.project_id?short(latest.project_id):"—"}</b><small>Project</small></div></div></article>`;}).join("");
    return `<div class="cf-view-intro"><div><span class="cf-section-kicker">DOWNSTREAM VISIBILITY</span><h2>Where the intelligence goes</h2><p>Sessions and agents connected by recorded identity. Parent relationships are shown only when supplied.</p></div><span>${known.length} known consumers</span></div><div class="cf-consumer-grid">${cards||empty("No consumer identity yet","Requests still appear in Traffic. The caller must supply session or agent identity to establish lineage.")}</div>${unknown.length?`<section class="cf-panel cf-unattributed"><span class="cf-consumer-glyph">?</span><div><h3>${unknown.length} unattributed requests</h3><p>${[...new Set(unknown.map(r=>r.client))].map(escape).join(", ")} · Their providers, models and usage remain visible.</p></div><button class="cf-button" data-select="consumer" data-id="unattributed">Inspect traffic</button></section>`:""}<details class="cf-instrumentation"><summary>How downstream attribution works</summary><p>Capacity Fabric observes explicit <code>x-fabric-session-id</code>, <code>x-fabric-agent-id</code>, <code>x-fabric-parent-agent-id</code>, <code>x-fabric-project-id</code> and <code>x-fabric-client</code> headers, or the equivalent fields in <code>metadata.fabric</code>. Existing SDK session metadata is recognized automatically. IDs are pseudonymized before export. These fields describe the caller; they do not grant routing or execution authority.</p></details>`;
  }

  function renderInspector(s) {
    const aside=s.root.querySelector(".cf-inspector"),body=s.root.querySelector(".cf-inspector-body"),sel=s.selected;
    aside.hidden=!sel;if(!sel||!s.data)return;
    const d=s.data;
    if(sel.kind==="request") {
      const r=allRecords(s).find(x=>x.id===sel.id);
      if(!r) {body.innerHTML=empty("Outside retained history","This request is no longer in the bounded observation window.");return;}
      const end=r.ended_at||d.generated_at,duration=Math.max(.001,end-r.started_at);
      const stages=[["Received",r.started_at],["Provider selected",r.attempts[0]&&r.attempts[0].started_at],["First content",r.first_content_at],[r.ended_at?"Finished":"In flight",end]];
      body.innerHTML=`<span class="cf-section-kicker">REQUEST ${short(r.id)}</span><h2>${escape(modelName(r.served_model||r.requested_model))}</h2><span class="cf-state ${r.state}"><i></i>${escape(r.state)}</span><div class="cf-detail-path"><span>${escape(r.provider||"Not routed")}</span>${icon("arrow")}<span>${escape(r.lane)}</span>${icon("arrow")}<span>${escape(consumerName(r))}</span></div><dl class="cf-detail-list"><dt>Requested</dt><dd>${escape(r.requested_model)}</dd><dt>Served model</dt><dd>${escape(r.served_model||"Not observed")}</dd><dt>Provider model ID</dt><dd>${escape(r.wire_model||"Not observed")}</dd><dt>Selected route</dt><dd>${escape(r.route_id||"Not observed")}</dd><dt>Consumer identity</dt><dd>${escape(r.identity_source.replace(/_/g," "))}</dd><dt>Started</dt><dd>${clock(r.started_at)}</dd><dt>HTTP status</dt><dd>${r.status_code||"Awaiting headers"}</dd></dl><h3>Reported token usage</h3><div class="cf-usage-grid">${[["Input",r.usage.input_tokens],["Output",r.usage.output_tokens],["Cache read",r.usage.cache_read_tokens],["Cache write",r.usage.cache_write_tokens]].map(([k,v])=>`<div><small>${k}</small><b>${n(v)}</b></div>`).join("")}</div><p class="cf-detail-note">${r.usage_source==="unavailable"?"The provider has not reported usage.":r.usage_final?"Final provider report. Cache values stay separate from input/output totals.":"Partial provider report. Totals may increase before completion."}</p><h3>Request timeline</h3><div class="cf-waterfall">${stages.map(([name,at])=>`<div><span>${name}</span><b>${at==null?"Not observed":seconds(Math.max(0,at-r.started_at))}</b><div><i style="width:${at==null?0:Math.max(1,Math.min(100,(at-r.started_at)/duration*100))}%"></i></div></div>`).join("")}</div><h3>Routing attempts <span>${r.attempts.length}</span></h3><div class="cf-attempts">${r.attempts.map((a,i)=>`<div><i>${i+1}</i><span><b>${escape(a.route_id)}</b><small>${escape(a.model)} · ${escape(a.state)}</small>${a.reason?`<code>${escape(a.reason)}</code>`:""}</span><em>${a.ended_at?seconds(a.ended_at-a.started_at):"Active"}</em></div>`).join("")||'<p class="cf-muted">No provider attempt observed.</p>'}</div><p class="cf-detail-note">Only usage delivered by the router is measured. Failed upstream attempts may have unreported consumption.</p>`;
      return;
    }
    const rs=allRecords(s).filter(r=>matchesSelection(r,sel)),live=rs.filter(r=>!r.ended_at),route=sel.kind==="route"?d.routes.find(r=>r.id===sel.id):null;
    const related=d.routes.filter(r=>sel.kind==="provider"?r.provider===sel.id:sel.kind==="model"?r.models.includes(sel.id):sel.kind==="route"?r.id===sel.id:false);
    const title=sel.kind==="consumer"?(sel.id==="unattributed"?"Unattributed traffic":rs[0]?consumerName(rs[0]):`Consumer ${short(sel.id)}`):sel.kind==="lane"&&sel.id==="direct"?"Direct model":sel.id;
    body.innerHTML=`<span class="cf-section-kicker">${escape(sel.kind)}</span><h2>${escape(title)}</h2><div class="cf-selection-stats"><div><b>${live.length}</b><small>In flight</small></div><div><b>${rs.length}</b><small>Observed calls</small></div><div><b>${rs.some(r=>r.usage.output_tokens!=null)?n(rs.reduce((a,r)=>a+(r.usage.output_tokens||0),0)):"—"}</b><small>Reported output</small></div></div>${route?`<dl class="cf-detail-list"><dt>Provider</dt><dd>${escape(route.provider)}</dd><dt>Wire</dt><dd>${escape(route.wire)}</dd><dt>Route priority</dt><dd>${route.priority}</dd><dt>Weight</dt><dd>${route.weight}</dd><dt>Cooldown</dt><dd>${route.cooling?"Cooling":"No cooldown"}</dd><dt>Consecutive failures</dt><dd>${route.consecutive_failures}</dd></dl>`:""}${related.length?`<h3>Configured routes</h3><div class="cf-inspector-routes">${related.map(r=>`<button data-select="route" data-id="${escape(r.id)}"><i class="${r.cooling?"cooling":""}"></i><span>${escape(r.id)}<small>${r.models.length} models · priority ${r.priority}</small></span>${icon("arrow")}</button>`).join("")}</div>`:""}${sel.kind==="lane"&&d.aliases[sel.id]?`<h3>Ordered model cascade</h3><ol class="cf-cascade">${d.aliases[sel.id].map(m=>`<li><button data-select="model" data-id="${escape(m)}">${escape(modelName(m))}</button></li>`).join("")}</ol>`:""}<h3>Latest requests</h3><div class="cf-inspector-requests">${rs.slice(0,12).map(r=>`<button data-select="request" data-id="${r.id}"><span><b>${escape(modelName(r.served_model||r.requested_model))}</b><small>${escape(consumerName(r))}</small></span><span class="cf-state ${r.state}"><i></i>${escape(r.state)}</span></button>`).join("")||'<p class="cf-muted">No retained traffic for this selection.</p>'}</div><p class="cf-detail-note">Selection filters the request explorer. Configured paths do not imply observed traffic or verified provider availability.</p>`;
  }

  function handleClick(s,e) {
    const selected=e.target.closest("[data-select]");
    if(selected) {s.selected={kind:selected.dataset.select,id:selected.dataset.id};s.page=0;renderView(s);renderInspector(s);return;}
    const view=e.target.closest("[data-view]");
    if(view) {s.view=view.dataset.view;s.page=0;renderView(s);return;}
    const action=e.target.closest("[data-action]");if(!action)return;
    switch(action.dataset.action) {
      case "pause": s.paused=!s.paused;action.innerHTML=icon(s.paused?"play":"pause")+`<span>${s.paused?"Resume":"Pause"}</span>`;updateConnection(s);if(!s.paused)load(s);break;
      case "refresh": if(!s.paused)load(s);break;
      case "fullscreen": if(document.fullscreenElement)document.exitFullscreen();else if(s.root.requestFullscreen)s.root.requestFullscreen().catch(()=>{});break;
      case "clear":s.selected=null;s.query="";s.model="all";s.status="all";s.page=0;s.root.querySelector("input").value="";s.root.querySelector('[data-field="model"]').value="all";s.root.querySelector('[data-field="status"]').value="all";renderView(s);renderInspector(s);break;
      case "close":s.selected=null;renderInspector(s);renderView(s);break;
      case "zoom-in":s.scale=Math.min(2,s.scale+.2);renderView(s);break;
      case "zoom-out":s.scale=Math.max(1,s.scale-.2);renderView(s);break;
      case "fit":s.scale=1;renderView(s);break;
      case "previous":s.page=Math.max(0,s.page-1);renderView(s);break;
      case "next":s.page++;renderView(s);break;
      case "export":if(s.data&&s.data.ok){const url=URL.createObjectURL(new Blob([JSON.stringify(s.data,null,2)],{type:"application/json"}));const a=document.createElement("a");a.href=url;a.download=`capacity-fabric-${new Date().toISOString().replace(/[:.]/g,"-")}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}break;
    }
  }
  window.CapacityRouter = {mount,unmount};
})();
