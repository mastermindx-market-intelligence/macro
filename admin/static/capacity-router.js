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
  const consumerKey = r => r.agent_id ? `agent:${r.agent_id}` : r.session_id ? `session:${r.session_id}` : "unattributed";
  const consumerName = r => r.agent_id ? `Agent ${short(r.agent_id)}` : r.session_id ? `${r.client} · ${short(r.session_id)}` : `${r.client} · unattributed`;
  const modelName = v => String(v || "Unknown model").replace(/^fabric\//, "").replace(/_/g," ");
  let active = null;

  function mount(host, options = {}) {
    unmount();
    const s = {host, options, data:null, view:"flow", minutes:15, query:"", status:"all", model:"all", selected:null,
      paused:false, pending:false, disposed:false, timer:null, tick:null, controller:null, scale:1, page:0, error:null, received:0, stream:null, transport:"connecting", requestGeneration:0, changes:new Map(), nodeOrder:{}, arrivals:0, updates:0, history:null, intelligence:null, settings:null, detailTimer:null, detailPending:false, custom:null, chartField:"output_tokens", showConfigured:true, mapFitted:false};
    active = s;
    host.innerHTML = `<section class="cf-shell" aria-label="Capacity Fabric router">
      <header class="cf-hero"><div><div class="cf-eyebrow"><span class="cf-mark">${icon("flow")}</span> INFRASTRUCTURE <span>/</span> ROUTER</div><h1>Capacity Fabric<span class="cf-title-dot">.</span></h1><p>Follow the intelligence. From capacity to every consumer.</p></div>
        <div class="cf-hero-right"><div class="cf-connection" role="status"><i></i><span>Connecting</span><small></small></div><div class="cf-hero-actions"><button data-action="pause" class="cf-button">${icon("pause")}<span>Pause</span></button><button data-action="refresh" class="cf-icon-button" aria-label="Refresh telemetry">${icon("refresh")}</button><button data-action="fullscreen" class="cf-icon-button" aria-label="Toggle full screen">${icon("expand")}</button></div></div></header>
      <div class="cf-notice" hidden role="status"></div><div class="cf-metrics" aria-label="Router metrics"></div>
      <div class="cf-toolbar"><div class="cf-tabs" role="tablist" aria-label="Router views">${[["flow","Topology"],["requests","Live requests"],["history","Usage history"],["intelligence","Capacity intelligence"],["providers","Pools"],["overflow","Overflow"],["claude","Claude lanes"],["consumers","Consumers"],["settings","Settings"]].map(([id,title])=>`<button role="tab" data-view="${id}" aria-selected="${id==="flow"}" class="${id==="flow"?"is-active":""}">${title}<span data-count="${id}"></span></button>`).join("")}</div><div class="cf-toolbar-right"><span class="cf-window-label">Window</span><select aria-label="Observation time window" data-field="window"><option value="5">5 minutes</option><option value="15" selected>15 minutes</option><option value="60">1 hour</option><option value="120">2 hours</option><option value="360">6 hours</option><option value="1440">24 hours</option><option value="10080">7 days</option><option value="43200">30 days</option><option value="129600">90 days</option><option value="0">All recorded time</option><option value="custom">Custom range</option></select><button data-action="export" class="cf-icon-button" aria-label="Export sanitized snapshot">${icon("download")}</button></div></div>
      <div class="cf-filters"><label class="cf-search">${icon("search")}<input data-field="search" placeholder="Find a model, route or session…" aria-label="Search router telemetry"><kbd>/</kbd></label><select data-field="model" aria-label="Filter by model"><option value="all">All models</option></select><select data-field="status" aria-label="Filter by request state"><option value="all">All activity</option><option value="streaming">Streaming</option><option value="waiting">Awaiting output</option><option value="completed">Completed</option><option value="failed">Errors & interruptions</option></select><button class="cf-clear" data-action="clear" hidden>Clear selection ×</button></div>
      <p class="cf-scope-note">Summary covers the whole router. Filters apply to traffic views and the inspector. Live concurrency is current; historical totals are recorded observations.</p><div class="cf-custom-range" hidden><label>From <input type="datetime-local" data-field="from" aria-label="History start in local time"></label><label>To <input type="datetime-local" data-field="to" aria-label="History end in local time"></label><button class="cf-button" data-action="apply-range">Apply range</button><span>Local time · minute-resolution boundaries</span></div><div class="cf-live-announcer" role="status" aria-live="polite" aria-atomic="true"></div><div class="cf-view" role="tabpanel"></div><footer class="cf-footer"><span>Capacity Fabric <i>•</i> Private telemetry</span><span class="cf-footnote">Connecting to the router observer…</span></footer>
      <aside class="cf-inspector" hidden aria-label="Selected traffic details"><div class="cf-inspector-bar"><span>INSPECTOR</span><button class="cf-icon-button" data-action="close" aria-label="Close inspector">${icon("close")}</button></div><div class="cf-inspector-body"></div></aside>
    </section>`;
    s.root = host.querySelector(".cf-shell");
    s.root.addEventListener("click", e => handleClick(s, e));
    s.root.addEventListener("input", e => {
      if(e.target.dataset.setting)markSettingsEdited(s);
      if (e.target.dataset.field === "search") { s.query = e.target.value; s.page=0; renderView(s); renderInspector(s); }
    });
    s.root.addEventListener("change", e => {
      const field=e.target.dataset.field;
      if(e.target.dataset.setting)markSettingsEdited(s);
      if(field==="window") {
        const custom=e.target.value==="custom";s.root.querySelector(".cf-custom-range").hidden=!custom;
        if(custom){s.view="history";renderView(s);return;}
        s.custom=null;s.minutes=Number(e.target.value);s.page=0;s.history=null;s.intelligence=null;
        restartConnection(s);loadSupplement(s);
      }
      if(field==="chart") {s.chartField=e.target.value;renderView(s);}
      if(field==="configured") {s.showConfigured=e.target.checked;renderView(s);}
      if(field==="model" || field==="status") {s[field]=e.target.value; s.page=0; renderView(s); renderInspector(s);}
    });
    s.keydown = e => {
      if(s.disposed || !s.host.isConnected || (options.isCurrent && !options.isCurrent())) return;
      if(e.key === "Escape") {s.selected=null; renderInspector(s); renderView(s);}
      if(e.key === "/" && !/INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) {e.preventDefault(); s.root.querySelector("input").focus();}
      if((e.key === "Enter" || e.key === " ") && e.target.matches("[data-select]")) {e.preventDefault(); e.target.dispatchEvent(new MouseEvent("click",{bubbles:true}));}
    };
    s.visibility = () => {if(document.hidden){closeStream(s);clearTimeout(s.timer);}else if(!s.paused)restartConnection(s);updateConnection(s);};
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
    closeStream(s);clearTimeout(s.detailTimer);if(s.detailController)s.detailController.abort();
    document.removeEventListener("keydown",s.keydown); document.removeEventListener("visibilitychange",s.visibility);
    active=null;
  }

  function closeStream(s) {if(s.stream){s.stream.close();s.stream=null;}}
  function restartConnection(s) {
    closeStream(s);clearTimeout(s.timer);if(s.controller)s.controller.abort();
    s.requestGeneration++;s.pending=false;load(s);
  }
  function mergeDelta(previous, delta) {
    if(!previous || previous.epoch!==delta.epoch)return null;
    const next={...previous,...delta};
    for(const kind of ["active","recent"]) {
      const map=new Map((previous[kind]||[]).map(r=>[r.id,r]));
      for(const row of delta[kind+"_upsert"]||[])map.set(row.id,row);
      next[kind]=(delta[kind+"_ids"]||[]).map(id=>map.get(id)).filter(Boolean);
      delete next[kind+"_ids"];delete next[kind+"_upsert"];
    }
    return next;
  }
  function acceptData(s,data) {
    if(s.disposed||s.paused||!data)return;
    if(s.data&&data.epoch===s.data.epoch&&data.sequence<s.data.sequence)return;
    const before=new Map(allRecords(s).map(r=>[r.id,r])),now=Date.now();let arrivals=0,updates=0;
    for(const row of [...(data.active||[]),...(data.recent||[])]) {
      const old=before.get(row.id);
      if(s.data&&!old){s.changes.set(row.id,{kind:"arrival",at:now});arrivals++;}
      else if(old&&(old.state!==row.state||old.content_events!==row.content_events||old.usage.output_tokens!==row.usage.output_tokens)){
        s.changes.set(row.id,{kind:"change",at:now});updates++;
      }
    }
    for(const [id,value] of s.changes)if(now-value.at>6000)s.changes.delete(id);
    s.arrivals=arrivals;s.updates=updates;s.data=data;s.received=now;s.error=null;
    const select=s.root.querySelector('[data-field="model"]');
    const models=[...new Set((data.routes||[]).flatMap(r=>r.models))].sort(),keys=models.join("|");
    if(s.modelKeys!==keys){s.modelKeys=keys;select.innerHTML='<option value="all">All models</option>'+models.map(m=>`<option value="${escape(m)}">${escape(modelName(m))}</option>`).join("");select.value=s.model;}
    renderMetrics(s);renderView(s);renderInspector(s);updateConnection(s);
    if(arrivals)s.root.querySelector(".cf-live-announcer").textContent=`${arrivals} new observed requests`;
    if(["history","intelligence","settings"].includes(s.view)&&!s[s.view])loadSupplement(s);
  }
  function startStream(s) {
    if(s.stream||s.disposed||s.paused||document.hidden||typeof EventSource==="undefined")return false;
    const source=new EventSource(`/api/capacity-router/events?minutes=${s.minutes}`,{withCredentials:true});
    s.stream=source;s.transport="connecting";
    source.addEventListener("snapshot",event=>{if(s.stream!==source)return;try{s.transport="stream";acceptData(s,JSON.parse(event.data));}catch(_){source.close();s.stream=null;s.transport="polling";load(s);}});
    source.addEventListener("delta",event=>{if(s.stream!==source)return;try{const data=mergeDelta(s.data,JSON.parse(event.data));if(data){s.transport="stream";acceptData(s,data);}else restartConnection(s);}catch(_){restartConnection(s);}});
    source.addEventListener("auth-expired",()=>{unmount();if(s.options.onAuthFailure)s.options.onAuthFailure();});
    source.onerror=()=>{
      if(s.stream!==source||s.disposed)return;
      closeStream(s);s.transport="polling";s.streamRetryAt=Date.now()+15000;
      clearTimeout(s.timer);s.timer=setTimeout(()=>load(s),1500);updateConnection(s);
    };
    return true;
  }
  async function load(s) {
    if(s.disposed||s.pending)return;
    if(!s.host.isConnected||(s.options.isCurrent&&!s.options.isCurrent())){unmount();return;}
    clearTimeout(s.timer);if(s.paused||document.hidden)return;
    s.pending=true;s.controller=new AbortController();const generation=++s.requestGeneration;
    const timeout=setTimeout(()=>s.controller.abort(),8000);
    try {
      const response=await fetch(`/api/capacity-router?minutes=${s.minutes}`,{credentials:"same-origin",cache:"no-store",signal:s.controller.signal});
      if(response.status===401){unmount();if(s.options.onAuthFailure)s.options.onAuthFailure();return;}
      if(!response.ok)throw new Error("Telemetry could not be read");
      const data=await response.json();if(generation!==s.requestGeneration)return;
      acceptData(s,data);
      if(!s.stream&&Date.now()>=(s.streamRetryAt||0))startStream(s);
    } catch(error) {
      if(!s.disposed&&generation===s.requestGeneration){s.error="Telemetry connection interrupted. Last received measurements remain visible.";updateConnection(s);if(!s.data)renderView(s);}
    } finally {
      clearTimeout(timeout);
      if(generation===s.requestGeneration){s.pending=false;if(!s.disposed&&!s.stream&&!s.paused&&!document.hidden){s.transport="polling";s.timer=setTimeout(()=>load(s),2000);}}
    }
  }
  async function loadSupplement(s) {
    clearTimeout(s.detailTimer);
    if(s.disposed||s.paused||s.detailPending||!["history","intelligence","settings"].includes(s.view))return;
    const view=s.view,query=new URLSearchParams({minutes:String(s.minutes),resolution:"auto"});
    if(s.custom){query.set("from",String(s.custom.start));query.set("to",String(s.custom.end));}
    const endpoint=view==="history"?"history":view;
    s.detailPending=true;s.detailController=new AbortController();const timeout=setTimeout(()=>s.detailController.abort(),10000);
    try {
      const response=await fetch(`/api/capacity-router/${endpoint}?${query}`,{credentials:"same-origin",cache:"no-store",signal:s.detailController.signal});
      if(response.status===401){unmount();if(s.options.onAuthFailure)s.options.onAuthFailure();return;}
      const data=await response.json();if(s.disposed)return;
      if(view==="settings"&&s.settingsEditing&&s.settings){s.latestSettings=data;}
      else s[view]=response.ok?data:{ok:false,message:data.error||"This observation is unavailable."};
      if(s.view===view)renderView(s);
    } catch(_){if(!s.disposed){s[view]={ok:false,message:"Connection interrupted. Refresh to retry this view."};if(s.view===view)renderView(s);}}
    finally {clearTimeout(timeout);s.detailPending=false;if(!s.disposed)s.detailTimer=setTimeout(()=>loadSupplement(s),15000);}
  }

  // Keyed reconciliation preserves row identity, selection, scroll and SVG motion.
  // No third-party renderer or remote scripts; all markup is escaped at its source.
  function patchMarkup(parent,html) {
    const template=document.createElement("template");template.innerHTML=html;
    const key=node=>node&&node.nodeType===1?(node.getAttribute("data-key")||(node.hasAttribute("data-select")?node.getAttribute("data-select")+":"+node.getAttribute("data-id"):null)):null;
    const same=(a,b)=>a&&a.nodeType===b.nodeType&&a.nodeName===b.nodeName;
    const patch=(target,source)=>{
      const keyed=new Map([...target.childNodes].map(n=>[key(n),n]).filter(([k])=>k));let cursor=target.firstChild;
      for(const fresh of [...source.childNodes]){
        const k=key(fresh);let old=k?keyed.get(k):(!key(cursor)&&same(cursor,fresh)?cursor:null);
        if(!same(old,fresh))old=null;
        if(!old){old=fresh.cloneNode(true);target.insertBefore(old,cursor);}
        else {
          if(old!==cursor)target.insertBefore(old,cursor);
          if(old.nodeType===3){if(old.nodeValue!==fresh.nodeValue)old.nodeValue=fresh.nodeValue;}
          else if(old.nodeType===1){
            const changed=old.getAttribute("data-version")!==fresh.getAttribute("data-version");
            for(const attr of [...old.attributes])if(!fresh.hasAttribute(attr.name))old.removeAttribute(attr.name);
            for(const attr of [...fresh.attributes])if(old.getAttribute(attr.name)!==attr.value)old.setAttribute(attr.name,attr.value);
            patch(old,fresh);
            if(changed&&fresh.hasAttribute("data-version")&&old.animate&&!window.matchMedia("(prefers-reduced-motion: reduce)").matches){
              old.animate([{opacity:.5},{opacity:1}],{duration:420,easing:"ease-out"});
            }
          }
        }
        cursor=old.nextSibling;
      }
      while(cursor){const next=cursor.nextSibling;cursor.remove();cursor=next;}
    };
    patch(parent,template.content);
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
    const svg=s.root.querySelector(".cf-topology");
    if(svg&&svg.pauseAnimations){if(state!=="live"||document.hidden||window.matchMedia("(prefers-reduced-motion: reduce)").matches)svg.pauseAnimations();else svg.unpauseAnimations();}
    s.root.querySelector(".cf-footnote").textContent=d&&d.ok?`${s.transport==="stream"?"Push stream":"Polling fallback"} · source age ${age==null?"unknown":Math.floor(age)+"s"} · ${d.limits.recent} recent requests retained · ${d.history_state==="recorded"?"durable history recording":d.history_state==="degraded"?"history storage degraded":"history not yet recording"} · no prompt content` : "Private, read-only observation of the existing router";
  }

  function renderMetrics(s) {
    const d=s.data, v=d&&d.ok?d.summary:{};
    const cards=[
      ["Concurrent requests",v.active_requests,`${n(v.awaiting_output)} awaiting first output`,"teal"],
      ["Reported output / sec",v.output_tokens_per_s,"Approx. selected-window average","blue"],
      ["Output tokens",v.output_tokens,`${n(v.input_tokens)} input · selected window`,"violet"],
      ["First content · p50",v.p50_first_content_ms==null?null:seconds(v.p50_first_content_ms/1000),`p95 ${seconds(v.p95_first_content_ms==null?null:v.p95_first_content_ms/1000)} · ${n(v.first_content_samples)} samples`,""],
      ["Known consumers",v.active_consumers,`${n(v.unattributed_active)} active requests unattributed`,""],
      ["Routes outside cooldown",v.ready_routes==null?null:`${v.ready_routes} / ${(d.routes||[]).length}`,`${n(v.cooling_routes)} cooling · ${n(v.providers)} providers`,""],
    ];
    if(d&&d.ok&&(d.overflow||d.claude)) cards.push(["Overflow & lanes",v.overflowing_families==null?null:v.overflowing_families,`${n(v.benched_lanes)} Claude lanes benched · ${n(v.over_target_keys)} seats over target${d.peak&&d.peak.active?" · peak active":""}`,"violet"]);
    patchMarkup(s.root.querySelector(".cf-metrics"),cards.map(([title,value,sub,color])=>`<article data-key="${title}" class="cf-metric ${color}"><div>${title}</div><strong>${typeof value==="string"?value:n(value)}</strong><small>${sub}</small></article>`).join(""));
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
  function records(s, selection=s.selected) {
    const q=s.query.toLowerCase();
    return allRecords(s).filter(r=>matchesSelection(r,selection))
      .filter(r=>s.model==="all"||r.served_model===s.model||r.requested_model===s.model)
      .filter(r=>s.status==="all" || (s.status==="waiting"? ["routing","waiting"].includes(r.state):s.status==="failed"?["failed","interrupted","cancelled"].includes(r.state):r.state===s.status))
      .filter(r=>!q||[consumerName(r),r.id,r.served_model,r.requested_model,r.provider,r.route_id,r.lane,r.client,r.project_id||""].join(" ").toLowerCase().includes(q));
  }

  function empty(title, detail) {return `<div class="cf-empty"><span>${icon("flow")}</span><h3>${escape(title)}</h3><p>${escape(detail)}</p></div>`;}

  function renderView(s) {
    const view=s.root.querySelector(".cf-view");
    s.root.querySelectorAll("[data-view]").forEach(el=>{el.classList.toggle("is-active",el.dataset.view===s.view);el.setAttribute("aria-selected",String(el.dataset.view===s.view));});
    s.root.querySelector(".cf-clear").hidden=!s.selected&&!s.query&&s.model==="all"&&s.status==="all";
    if(!s.data||!s.data.ok){patchMarkup(view,`<div class="cf-panel cf-initial">${empty(s.error?"Connection interrupted":s.data?"Waiting for the router":"Opening the fabric",s.data?s.data.message:"Connecting the provider, model and consumer layers.")}</div>`);return;}
    let html;
    if(s.view==="flow")html=flowMap(s)+`<div class="cf-lower-grid" data-key="flow-metrics">${trend(s)}${health(s)}</div>`+requestTable(s,8);
    else if(s.view==="requests")html=requestTable(s,50,true);
    else if(s.view==="history")html=historyView(s);
    else if(s.view==="intelligence")html=intelligenceView(s);
    else if(s.view==="settings"){if(s.settingsEditing&&view.querySelector(".cf-settings-form"))return;html=settingsView(s);}
    else if(s.view==="providers")html=providerView(s);
    else if(s.view==="overflow")html=overflowView(s);
    else if(s.view==="claude")html=claudeView(s);
    else html=consumerView(s);
    patchMarkup(view,html);updateConnection(s);
  }
  function stableIds(s,kind,ids) {
    const present=new Set(ids),previous=s.nodeOrder[kind]||[];
    const ordered=previous.filter(id=>present.has(id)),known=new Set(ordered);
    ordered.push(...[...present].filter(id=>!known.has(id)).sort());s.nodeOrder[kind]=ordered;return ordered;
  }
  function flowMap(s) {
    const d=s.data,rs=records(s),activeIds=new Set(d.active.map(r=>r.id));
    const routes=d.routes.filter(r=>(s.model==="all"||r.models.includes(s.model))&&(!s.query||[r.id,r.provider,...r.models].join(" ").toLowerCase().includes(s.query.toLowerCase())||rs.some(x=>x.route_id===r.id)));
    const weights=new Map();
    const bump=(kind,id,r)=>{const key=kind+":"+id,w=weights.get(key)||{requests:0,active:0,tokens:0,known:0};w.requests++;w.active+=activeIds.has(r.id)?1:0;w.tokens+=r.usage.output_tokens||0;w.known+=r.usage.output_tokens!=null?1:0;weights.set(key,w);};
    rs.forEach(r=>{bump("provider",r.provider||"unassigned",r);bump("route",r.route_id||"unassigned",r);bump("model",r.served_model||r.requested_model,r);bump("lane",r.lane,r);bump("consumer",consumerKey(r),r);});
    const columns=[
      {kind:"provider",title:"PROVIDERS / POOLS",ids:[...routes.map(r=>r.provider),...rs.map(r=>r.provider||"unassigned")],x:132},
      {kind:"route",title:"LIVE ROUTES",ids:[...routes.map(r=>r.id),...rs.map(r=>r.route_id||"unassigned")],x:390},
      {kind:"model",title:"SERVED MODELS",ids:[...routes.flatMap(r=>r.models),...rs.map(r=>r.served_model||r.requested_model)],x:648},
      {kind:"lane",title:"ROUTING CLASSES",ids:["direct",...Object.keys(d.aliases),...rs.map(r=>r.lane)],x:906},
      {kind:"consumer",title:"CONSUMERS / PARENTS",ids:[...rs.map(consumerKey),...rs.filter(r=>r.parent_agent_id).map(r=>"agent:"+r.parent_agent_id)],x:1164}
    ];
    columns.forEach(c=>c.ids=stableIds(s,c.kind,c.ids));
    const width=1320,height=Math.max(540,130+Math.max(...columns.map(c=>c.ids.length))*62),nodes=[],byKey=new Map();
    for(const col of columns)col.ids.forEach((id,i)=>{const node={...col,id,y:90+i*62,weight:weights.get(col.kind+":"+id)||{requests:0,active:0,tokens:0,known:0}};nodes.push(node);byKey.set(col.kind+":"+id,node);});
    const edges=new Map();
    const edge=(a,b,r,relation=false)=>{if(!byKey.has(a)||!byKey.has(b))return;const key=a+"|"+b,e=edges.get(key)||{key,a:byKey.get(a),b:byKey.get(b),count:0,active:0,tokens:0,known:0,relation};if(r){e.count++;e.tokens+=r.usage.output_tokens||0;e.known+=r.usage.output_tokens!=null?1:0;e.active+=activeIds.has(r.id)&&r.state==="streaming"?1:0;}edges.set(key,e);};
    routes.forEach(r=>{edge("provider:"+r.provider,"route:"+r.id);r.models.forEach(m=>{edge("route:"+r.id,"model:"+m);edge("model:"+m,"lane:direct");});});
    Object.entries(d.aliases).forEach(([lane,targets])=>targets.forEach(m=>edge("model:"+m,"lane:"+lane)));
    rs.forEach(r=>{const model=r.served_model||r.requested_model;edge("provider:"+(r.provider||"unassigned"),"route:"+(r.route_id||"unassigned"),r);edge("route:"+(r.route_id||"unassigned"),"model:"+model,r);edge("model:"+model,"lane:"+r.lane,r);edge("lane:"+r.lane,"consumer:"+consumerKey(r),r);if(r.agent_id&&r.parent_agent_id&&r.agent_id!==r.parent_agent_id)edge("consumer:agent:"+r.parent_agent_id,"consumer:agent:"+r.agent_id,r,true);});
    const visibleEdges=[...edges.values()].filter(e=>s.showConfigured||e.count);
    const paths=visibleEdges.map(e=>{
      const path=e.relation?`M${e.a.x+91},${e.a.y} C${width-10},${e.a.y} ${width-10},${e.b.y} ${e.b.x+91},${e.b.y}`:`M${e.a.x+91},${e.a.y} C${e.a.x+140},${e.a.y} ${e.b.x-140},${e.b.y} ${e.b.x-91},${e.b.y}`;
      return `<g data-key="${escape(e.key)}" class="cf-edge ${e.count?"observed":"configured"} ${e.active?"streaming":""} ${e.relation?"cf-parent-edge":""}"><path d="${path}" stroke-width="${e.count?Math.min(4,1.3+Math.log2(e.count+1)*.35):1}"/><title>${e.relation?"Caller-reported parent relationship · ":""}${e.count?`${e.count} observed requests · ${e.known?full(e.tokens):"Unknown"} reported output tokens`:"Configured path; no observed traffic in this window"}</title>${e.active?`<circle data-key="particle" r="2.7"><animateMotion dur="1.8s" repeatCount="indefinite" path="${path}"/></circle>`:""}</g>`;
    }).join("");
    const nodeMarkup=nodes.map(({kind,id,x,y,weight})=>{
      const request=rs.find(r=>consumerKey(r)===id),route=routes.find(r=>r.id===id);
      const title=kind==="consumer"?(id==="unattributed"?"Unattributed":request?consumerName(request):"Referenced parent "+short(id.replace(/^agent:/,""))):kind==="lane"?(id==="direct"?"Direct selection":modelName(id)):kind==="model"?modelName(id):id;
      const meta=kind==="provider"?`${routes.filter(r=>r.provider===id).length} routes · ${weight.active} active`:kind==="route"?`${route?route.wire:"Retained observation"} · ${weight.active} active`:kind==="lane"&&id!=="direct"?`${(d.aliases[id]||[]).length} configured alternatives`:`${weight.active} active · ${weight.requests} calls`;
      const cooling=kind==="route"?route&&route.cooling:kind==="provider"&&routes.some(r=>r.provider===id)&&routes.filter(r=>r.provider===id).every(r=>r.cooling),sel=s.selected&&s.selected.kind===kind&&s.selected.id===id;
      return `<g data-key="${escape(kind+":"+id)}" class="cf-node ${kind} ${weight.active?"has-activity":""} ${cooling?"cooling":""} ${sel?"selected":""}" role="button" tabindex="0" aria-label="Inspect ${escape(title)}" data-select="${kind}" data-id="${escape(id)}" transform="translate(${x-91},${y-25})"><rect width="182" height="50" rx="10"/><circle cx="15" cy="17" r="3"/><text x="27" y="21" class="cf-node-title">${escape(title.length>23?title.slice(0,21)+"…":title)}</text><text x="15" y="38" class="cf-node-sub">${escape(meta)}</text>${weight.active?'<circle class="cf-node-pulse" cx="166" cy="17" r="3"/>':""}<title>${escape(title)} · ${weight.known?full(weight.tokens):"Unknown"} reported output tokens</title></g>`;
    }).join("");
    if(!s.mapFitted){s.scale=Math.max(.2,Math.min(1,(s.root.clientWidth||1200)/width));s.mapFitted=true;}
    s.mapWidth=width;s.mapHeight=height;
    const headers=columns.map(c=>`<g data-key="header:${c.kind}"><text x="${c.x-91}" y="31" class="cf-column-title">${c.title}</text><text x="${c.x+91}" y="31" text-anchor="end" class="cf-column-count">${c.ids.length}</text></g>`).join("");
    return `<section data-key="topology" class="cf-panel cf-map-panel"><div class="cf-panel-heading"><div><span class="cf-section-kicker">COMPLETE LIVE TOPOLOGY</span><h2>Every observed connection</h2><p class="cf-muted">${nodes.length} nodes · ${visibleEdges.length} connections · no hidden-node cap</p></div><label class="cf-check"><input type="checkbox" data-field="configured" ${s.showConfigured?"checked":""}> Configured paths</label></div><div class="cf-map-scroll" tabindex="0" aria-label="Scrollable complete topology"><svg data-key="topology-svg" class="cf-topology" viewBox="0 0 ${width} ${height}" style="width:${width*s.scale}px;height:${height*s.scale}px" role="group" aria-label="All available pools, routes, models, routing classes, consumers and reported parents"><g data-key="headers">${headers}</g><g data-key="edges">${paths}</g><g data-key="nodes">${nodeMarkup}</g></svg></div><div class="cf-map-bottom"><span>${icon("arrow")} Pool → Route → Model → Class → Consumer <em>Animation = observed streaming, not token counts.</em></span><div><button data-action="zoom-out" aria-label="Zoom out">−</button><button data-action="fit">Fit all</button><button data-action="readable">Readable</button><button data-action="zoom-in" aria-label="Zoom in">+</button><small>${Math.round(s.scale*100)}%</small></div></div></section>`;
  }

  function trend(s) {
    const d=s.data,start=d.window_start||d.started_at,end=d.window_end||d.generated_at;
    return `<section class="cf-panel cf-trend"><div class="cf-panel-heading"><div><span class="cf-section-kicker">RECORDED THROUGHPUT</span><h2>Reported output</h2></div><strong>${n(d.summary.output_tokens)} <small>tokens</small></strong></div>${usageChart(d.series||[],start,end,"output_tokens",102)}<p class="cf-history-foot">Recorded at completion · missing usage remains unknown</p></section>`;
  }
  function health(s) {
    const d=s.data,v=d.summary,total=v.completed+v.failed,ratio=total?100*v.completed/total:0;
    return `<section class="cf-panel cf-health"><div class="cf-panel-heading"><div><span class="cf-section-kicker">OBSERVATION QUALITY</span><h2>Know what is known</h2></div><span class="cf-quality">${v.usage_coverage_pct==null?"—":v.usage_coverage_pct+"%"}</span></div><div class="cf-health-row"><span>Requests with output usage</span><b>${v.usage_known} / ${total}</b></div><div class="cf-meter"><i style="width:${v.usage_coverage_pct||0}%"></i></div><div class="cf-health-stats"><div><b>${n(v.completed)}</b><span>Completed</span></div><div><b class="${v.failed?"cf-amber-text":""}">${n(v.failed)}</b><span>Errors / partial</span></div><div><b>${v.recent_count?Math.round(v.attributed_recent/v.recent_count*100)+"%":"—"}</b><span>Known consumer</span></div></div><p>Missing usage stays unknown. Agent relations appear only when the caller reports them.</p></section>`;
  }

  function requestTable(s, limit, paginated=false) {
    const rs=records(s), pages=Math.max(1,Math.ceil(rs.length/limit));s.page=Math.min(s.page,pages-1);
    const rows=rs.slice(paginated?s.page*limit:0,paginated?(s.page+1)*limit:limit);
    const body=rows.map(r=>{const duration=(r.ended_at||s.data.generated_at)-r.started_at;const first=r.first_content_at==null?null:r.first_content_at-r.started_at;return `<tr data-key="request:${r.id}" data-version="${r.state}:${r.content_events}:${r.usage.output_tokens}" class="${s.changes.has(r.id)?"cf-row-"+s.changes.get(r.id).kind:""}" tabindex="0" role="button" data-select="request" data-id="${r.id}" aria-label="Inspect request ${short(r.id)}"><td><span class="cf-consumer-glyph">${r.agent_id?"A":r.session_id?"S":"?"}</span><div><b>${escape(consumerName(r))}</b><small>${clock(r.started_at)} <span>· ${short(r.id)}</span></small></div></td><td><b>${escape(modelName(r.served_model||r.requested_model))}</b><small>${escape(r.lane==="direct"?"Direct model":r.lane)}</small></td><td><b>${escape(r.provider||"Routing")}</b><small>${escape(r.route_id||"Route not selected")}</small></td><td><span class="cf-state ${r.state}"><i></i>${{routing:"Routing",waiting:"Awaiting output",streaming:"Streaming",completed:"Completed",failed:"Failed",cancelled:"Cancelled",interrupted:"Interrupted"}[r.state]||r.state}</span>${r.state==="streaming"?`<small class="cf-event-count">${n(r.content_events)} response events</small>`:""}${r.attempts.length>1?`<small class="cf-fallback">${r.attempts.length} attempts</small>`:""}</td><td class="cf-mono">${seconds(first)}</td><td class="cf-mono">${n(r.usage.input_tokens)} <span class="cf-slash">/</span> ${n(r.usage.output_tokens)}${r.usage_source==="unavailable"?'<small>Not reported</small>':!r.usage_final?'<small>Partial usage</small>':""}</td><td class="cf-mono">${seconds(duration)}</td></tr>`;}).join("");
    return `<section data-key="request-explorer" class="cf-panel cf-request-panel"><div class="cf-panel-heading"><div><span class="cf-section-kicker">REQUEST EXPLORER</span><h2>${paginated?"Live request explorer":"Recent traffic"} <span class="cf-count-badge">${rs.length}</span></h2></div>${!paginated?'<button class="cf-text-button" data-view="requests">Explore all requests →</button>':`<span class="cf-feed-meta"><b>${s.arrivals?"+"+s.arrivals+" new":s.updates?s.updates+" updated":"Following live traffic"}</b><small>${s.data.active.length} in flight · ${s.data.recent.length} retained · ${s.transport==="stream"?"push stream":"polling"}</small></span>`}</div>${rows.length?`<div class="cf-table-scroll"><table><thead><tr><th>Consumer</th><th>Model / lane</th><th>Provider / route</th><th>State</th><th>First content</th><th>Input / output</th><th>Duration</th></tr></thead><tbody>${body}</tbody></table></div>`:empty("No matching requests",s.query||s.selected||s.model!=="all"?"Clear the filters or choose a different observation window.":"Real requests will appear here as they pass through Capacity Fabric.")}${paginated?`<div class="cf-pagination"><span>Showing ${rs.length? s.page*limit+1:0}–${Math.min(rs.length,(s.page+1)*limit)} of ${rs.length}</span><div><button data-action="previous" ${s.page===0?"disabled":""}>← Previous</button><span>${s.page+1} / ${pages}</span><button data-action="next" ${s.page===pages-1?"disabled":""}>Next →</button></div></div>`:""}</section>`;
  }

  function providerView(s) {
    const d=s.data,filtered=records(s),activeIds=new Set(d.active.map(r=>r.id)),eligible=d.routes.filter(r=>s.model==="all"||r.models.includes(s.model)),providers=[...new Set(eligible.map(r=>r.provider))].filter(p=>!s.query||d.routes.some(r=>r.provider===p&&[p,r.id,...r.models].join(" ").toLowerCase().includes(s.query.toLowerCase())));
    const cards=providers.map(p=>{const routes=eligible.filter(r=>r.provider===p),models=[...new Set(routes.flatMap(r=>r.models))];const live=filtered.filter(r=>r.provider===p&&activeIds.has(r.id)).length;return `<article class="cf-provider-card"><button class="cf-provider-top" data-select="provider" data-id="${escape(p)}"><span class="cf-provider-symbol">${escape(p.slice(0,2).toUpperCase())}</span><span><strong>${escape(p)}</strong><small>${routes.length} routes · ${models.length} models</small></span><span class="cf-provider-live">${live}<small>active</small></span></button><div class="cf-provider-models">${models.map(m=>`<button data-select="model" data-id="${escape(m)}">${escape(modelName(m))}</button>`).join("")}</div><div class="cf-provider-routes">${routes.map(r=>`<button data-select="route" data-id="${escape(r.id)}"><i class="${r.cooling?"cooling":""}"></i><span>${escape(r.id)}<small>${escape(r.wire)} · base priority ${r.priority} · weight ${r.weight}</small></span><b>${r.cooling?"Cooling":"No cooldown"}</b></button>`).join("")}</div><div class="cf-provider-bottom"><span>${n(routes.reduce((a,r)=>a+r.served,0))} responses started</span><span>${n(routes.reduce((a,r)=>a+r.attempt_failed,0))} failed attempts</span></div></article>`;}).join("");
    return `<div class="cf-view-intro"><div><span class="cf-section-kicker">CAPACITY INVENTORY</span><h2>One fabric. Every provider.</h2><p>Active counts follow the filters. Route configuration and response/attempt counters cover the current router process.</p></div><span>${d.routes.length} routes / ${d.summary.models} models</span></div><div class="cf-provider-grid">${cards||empty("No matching providers","Try a model name or clear your search.")}</div>`;
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
    const rs=records(s),retainedAgents=new Set(allRecords(s).map(r=>r.agent_id).filter(Boolean)),groups=new Map();rs.forEach(r=>{const id=consumerKey(r);if(!groups.has(id))groups.set(id,[]);groups.get(id).push(r);});
    const known=[...groups.entries()].filter(([id])=>id!=="unattributed"),unknown=groups.get("unattributed")||[];
    const cards=known.map(([id,list])=>{const latest=list[0],active=list.filter(r=>!r.ended_at).length,parent=latest.parent_agent_id;const parentPresent=parent&&retainedAgents.has(parent);return `<article class="cf-consumer-card"><button data-select="consumer" data-id="${id}" class="cf-consumer-card-head"><span class="cf-consumer-glyph">${latest.agent_id?"A":"S"}</span><span><strong>${escape(consumerName(latest))}</strong><small>${escape(latest.client)} · ${latest.agent_id?"Caller-reported agent":latest.identity_source==="sdk_session"?"SDK session":"Caller-reported session"}</small></span><span class="cf-active-count">${active}<small>active</small></span></button>${parent?`<div class="cf-parent-line">↳ Parent ${parentPresent?`<button data-select="consumer" data-id="agent:${parent}" data-reveal-parent="true">Agent ${short(parent)}</button>`:`<span>${short(parent)} · not observed in retained history</span>`}</div>`:""}<div class="cf-consumer-models">${[...new Set(list.map(r=>r.served_model||r.requested_model))].map(m=>`<span>${escape(modelName(m))}</span>`).join("")}</div><div class="cf-consumer-stats"><div><b>${list.length}</b><small>Requests</small></div><div><b>${list.some(r=>r.usage.output_tokens!=null)?n(list.reduce((a,r)=>a+(r.usage.output_tokens||0),0)):"—"}</b><small>Reported output</small></div><div><b>${latest.project_id?short(latest.project_id):"—"}</b><small>Project</small></div></div></article>`;}).join("");
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
    const rs=records(s),live=rs.filter(r=>!r.ended_at),route=sel.kind==="route"?d.routes.find(r=>r.id===sel.id):null;
    const related=d.routes.filter(r=>sel.kind==="provider"?r.provider===sel.id:sel.kind==="model"?r.models.includes(sel.id):sel.kind==="route"?r.id===sel.id:false);
    const title=sel.kind==="consumer"?(sel.id==="unattributed"?"Unattributed traffic":rs[0]?consumerName(rs[0]):`Consumer ${short(sel.id.replace(/^(agent|session):/,""))}`):sel.kind==="lane"&&sel.id==="direct"?"Direct model":sel.id;
    body.innerHTML=`<span class="cf-section-kicker">${escape(sel.kind)}</span><h2>${escape(title)}</h2><div class="cf-selection-stats"><div><b>${live.length}</b><small>In flight</small></div><div><b>${rs.length}</b><small>Observed calls</small></div><div><b>${rs.some(r=>r.usage.output_tokens!=null)?n(rs.reduce((a,r)=>a+(r.usage.output_tokens||0),0)):"—"}</b><small>Reported output</small></div></div>${route?`<dl class="cf-detail-list"><dt>Provider</dt><dd>${escape(route.provider)}</dd><dt>Wire</dt><dd>${escape(route.wire)}</dd><dt>Route priority</dt><dd>${route.priority}</dd><dt>Weight</dt><dd>${route.weight}</dd><dt>Cooldown</dt><dd>${route.cooling?"Cooling":"No cooldown"}</dd><dt>Consecutive failures</dt><dd>${route.consecutive_failures}</dd></dl>`:""}${related.length?`<h3>Configured routes</h3><div class="cf-inspector-routes">${related.map(r=>`<button data-select="route" data-id="${escape(r.id)}"><i class="${r.cooling?"cooling":""}"></i><span>${escape(r.id)}<small>${r.models.length} models · priority ${r.priority}</small></span>${icon("arrow")}</button>`).join("")}</div>`:""}${sel.kind==="lane"&&d.aliases[sel.id]?`<h3>Ordered model cascade</h3><ol class="cf-cascade">${d.aliases[sel.id].map(m=>`<li><button data-select="model" data-id="${escape(m)}">${escape(modelName(m))}</button></li>`).join("")}</ol>`:""}<h3>Latest requests</h3><div class="cf-inspector-requests">${rs.slice(0,12).map(r=>`<button data-select="request" data-id="${r.id}"><span><b>${escape(modelName(r.served_model||r.requested_model))}</b><small>${escape(consumerName(r))}</small></span><span class="cf-state ${r.state}"><i></i>${escape(r.state)}</span></button>`).join("")||'<p class="cf-muted">No retained traffic for this selection.</p>'}</div><p class="cf-detail-note">Traffic totals follow the current filters and selection. Configured paths do not imply observed traffic or verified provider availability.</p>`;
  }

  const dated = value => value == null ? "Not reported" : new Date(value*1000).toLocaleString([], {month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"});
  const tokenLabel = key => ({input_tokens:"Input tokens",output_tokens:"Output tokens",cache_read_tokens:"Cache reads",cache_write_tokens:"Cache writes"}[key]||key);
  function usageChart(buckets,start,end,field,height=180) {
    const width=1040,knownKey=field+"_known",known=buckets.filter(b=>(b[knownKey]??(field==="output_tokens"?b.usage_known:0))>0),max=Math.max(1,...known.map(b=>b[field]||0)),span=Math.max(60,end-start);
    const bars=buckets.map(b=>{
      const reported=(b[knownKey]??(field==="output_tokens"?b.usage_known:0))>0;
      const x=Math.max(0,(b.at-start)/span*width),interval=b.interval_s||60,w=Math.max(.8,Math.min(34,interval/span*width*.82));
      const h=reported?Math.max(1,(b[field]||0)/max*(height-20)):4;
      return `<rect data-key="bucket:${b.at}" class="${reported?"cf-usage-reported":"cf-usage-unknown"}" x="${x.toFixed(2)}" y="${height-h}" width="${w.toFixed(2)}" height="${h.toFixed(2)}" rx="1"><title>${escape(dated(b.at))} · ${reported?full(b[field])+" "+tokenLabel(field):"Usage not reported"} · ${b.completed+b.failed} terminal requests · ${interval/60} minute bin</title></rect>`;
    }).join("");
    return `<div class="cf-history-chart"><div class="cf-chart-scale">${n(max)} / recorded bin</div><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escape(tokenLabel(field))} over recorded time" preserveAspectRatio="none"><path class="cf-grid-line" d="M0 ${height/3}H${width}M0 ${height*2/3}H${width}M0 ${height}H${width}"/>${bars}</svg>${!buckets.length?'<div class="cf-history-chart-empty">No recorded buckets in this range. Missing history is not zero usage.</div>':""}</div><div class="cf-axis"><span>${dated(start)}</span><span>${dated(end)}</span></div>`;
  }
  function historyView(s) {
    const h=s.history;
    if(!h)return `<section data-key="history" class="cf-panel cf-initial">${empty("Opening durable usage history","Reading recorded counters across router process restarts.")}</section>`;
    if(!h.ok)return `<section data-key="history" class="cf-panel cf-initial">${empty("History is not available",h.message||"The live feed is independent of historical storage.")}</section>`;
    const v=h.summary,c=h.coverage;
    const cards=["input_tokens","output_tokens","cache_read_tokens","cache_write_tokens"].map(k=>`<article class="cf-history-metric" data-key="metric:${k}"><span>${tokenLabel(k)}</span><strong>${n(v[k])}</strong><small>${v[k+"_coverage_pct"]==null?"Coverage not fully reported":v[k+"_coverage_pct"]+"% request coverage"}</small></article>`).join("");
    const ranking=(rows,title)=>`<section class="cf-panel"><div class="cf-panel-heading"><h2>${title}</h2><span class="cf-muted">Captured request ledger</span></div><div class="cf-table-scroll"><table class="cf-history-table"><thead><tr><th>${title==="Model demand"?"Model":"Pool"}</th><th>Requests</th><th>Input</th><th>Output</th><th>Failures</th></tr></thead><tbody>${rows.map(r=>`<tr data-key="rank:${escape(r.id)}"><td><b>${escape(r.id)}</b></td><td>${n(r.requests)}</td><td>${n(r.input_tokens_known?r.input_tokens:null)}</td><td>${n(r.output_tokens_known?r.output_tokens:null)}</td><td>${n(r.failed)}</td></tr>`).join("")||'<tr><td colspan="5">No captured model/pool observations in this range.</td></tr>'}</tbody></table></div></section>`;
    return `<div data-key="history" class="cf-history-view"><div class="cf-view-intro"><div><span class="cf-section-kicker">DURABLE USAGE LEDGER</span><h2>${h.all_time?"All recorded consumption":"Consumption over time"}</h2><p>Provider-reported usage, retained across router restarts. Cache fields stay separate from input totals.</p></div><span>${n(v.requests)} terminal requests · ${c.epochs} process epochs</span></div><div class="cf-history-metrics">${cards}</div><section class="cf-panel"><div class="cf-panel-heading"><div><span class="cf-section-kicker">RECORDED TIME SERIES</span><h2>${tokenLabel(s.chartField)}</h2></div><label class="cf-chart-selector">Measure <select data-field="chart" aria-label="Chart token measure">${["output_tokens","input_tokens","cache_read_tokens","cache_write_tokens"].map(k=>`<option value="${k}" ${k===s.chartField?"selected":""}>${tokenLabel(k)}</option>`).join("")}</select></label></div>${usageChart(h.series,h.start,h.end,s.chartField,240)}<div class="cf-history-foot">${h.resolution_s/60}-minute bins · observed through ${dated(h.observed_through)} · hover a bar for counts and reporting coverage</div></section><div class="cf-history-coverage"><b>Coverage, not invented history</b><span>Lifetime counters since ${dated(c.totals_since)}; recorded chart since ${dated(c.time_series_since)}. Model/pool ledger captured ${n(c.model_pool_requests)} of ${n(c.counter_requests)} terminal requests in the selected range. ${n(c.ingestion_gaps)} observed transport gap(s). Detail retention: ${c.detailed_retention_days} days; chart retention: ${c.series_retention_days} days; lifetime counters retained separately.</span></div><div class="cf-lower-grid">${ranking(h.models,"Model demand")}${ranking(h.pools,"Pool demand")}</div></div>`;
  }
  function intelligenceView(s) {
    const d=s.intelligence;
    if(!d)return `<section class="cf-panel cf-initial" data-key="intelligence">${empty("Learning from observed demand","Comparing live model classes, pool concentration, quota windows and resets.")}</section>`;
    if(!d.ok)return `<section class="cf-panel cf-initial" data-key="intelligence">${empty("Capacity intelligence unavailable",d.message||"Live telemetry is required for capacity advice.")}</section>`;
    const recommendations=d.recommendations.map((r,i)=>`<article class="cf-advice-card" data-key="advice:${i}:${escape(r.target)}"><div class="cf-advice-meta"><span>${escape(r.target)}</span><span class="cf-state ${r.severity==="warning"?"waiting":"completed"}">${escape(r.confidence.replace(/_/g," "))}</span></div><h3>${escape(r.title)}</h3><p>${escape(r.detail)}</p><small>${escape(r.action)}</small>${r.additional_subscriptions!=null?`<strong class="cf-seat-scenario">+${r.additional_subscriptions} <small>conditional equivalent-seat scenario</small></strong>`:""}</article>`).join("");
    const modelRows=d.models.map(m=>`<tr data-key="demand:${escape(m.model)}"><td><button class="cf-text-button" data-select="model" data-id="${escape(m.model)}">${escape(modelName(m.model))}</button><small>${m.classes.map(escape).join(" · ")||"Direct model selection"}</small></td><td><b>${n(m.requests)}</b><small>${m.share_pct==null?"No captured usage":m.share_pct+"% of captured requests"}</small></td><td><div class="cf-pool-chips">${m.primary_pools.map(p=>`<button data-select="provider" data-id="${escape(p.pool)}">${escape(p.pool)} <b>${n(p.requests)}</b></button>`).join("")||'<span class="cf-muted">No captured demand</span>'}</div><small>${m.pool_concentration_pct==null?"":m.pool_concentration_pct+"% in the primary pool"}</small></td><td><div class="cf-pool-chips">${m.same_model_pools.map(p=>`<span title="Quota availability is not reported">${escape(p.pool)} · ${p.routes_outside_cooldown?"outside cooldown":"cooling"}</span>`).join("")||"No configured route"}</div></td><td><div class="cf-alternative-list">${m.alternatives.map(a=>`<span><b>${escape(modelName(a.model))}</b><small>${a.routes_outside_cooldown} route(s) outside cooldown · ${a.pools.map(escape).join(", ")}</small></span>`).join("")||'<span class="cf-muted">No configured class alternative</span>'}</div></td></tr>`).join("");
    const quota=d.quota_families.map(f=>`<tr data-key="quota:${escape(f.family)}"><td><b>${escape(f.family)}</b><small>${f.observed_accounts} observed accounts · ${f.temporarily_unavailable_accounts} temporarily unavailable</small></td><td><b>${n(f.weekly_remaining_units)} / ${n(f.weekly_budget_units)}</b><small>Gateway budget units, not tokens</small></td><td>${f.used_pct==null?"Not reported":f.used_pct+"%"}</td><td><b>${dated(f.next_reset_at)}</b><small>${f.reset_sources.map(escape).join(" / ")||"Not reported"}</small></td><td><b>${f.units_per_hour==null?"Learning":n(f.units_per_hour)+" units / hour"}</b><small>${f.sample_hours==null?"Needs comparable samples spanning one hour":f.sample_hours+" hours observed"}</small></td><td><b>${f.suggested_additional_subscriptions==null?"Not enough evidence":f.suggested_additional_subscriptions?"+"+f.suggested_additional_subscriptions:"No increase indicated"}</b><small>${f.fresh?"Conditional scenario; no purchase":"Stale quota observation; no purchase advice"}</small></td></tr>`).join("");
    return `<div data-key="intelligence" class="cf-intelligence-view"><div class="cf-view-intro"><div><span class="cf-section-kicker">ADAPTIVE CAPACITY INTELLIGENCE</span><h2>Understand demand before buying capacity</h2><p>Live catalog-driven analysis. New models and pools are discovered from router configuration, not a fixed model list.</p></div><span>${d.model_count} models · ${d.pool_count} pools · ${n(d.captured_requests)} captured requests</span></div>${d.stale?'<div class="cf-history-coverage">Source telemetry is stale. Treat recommendations as historical observations, not current availability.</div>':""}<div class="cf-advice-grid">${recommendations}</div><section class="cf-panel"><div class="cf-panel-heading"><div><span class="cf-section-kicker">PRIMARY MODELS & POOL CONCENTRATION</span><h2>Demand, spare routes and configured alternatives</h2></div><span class="cf-muted">${d.basis==="retained_request_sample"?"Recent retained sample":"Durable captured-request ledger"}</span></div><div class="cf-table-scroll"><table class="cf-intelligence-table"><thead><tr><th>Model / routing class</th><th>Demand</th><th>Primary consumed pools</th><th>Same-model pools</th><th>Configured class alternatives</th></tr></thead><tbody>${modelRows}</tbody></table></div><p class="cf-history-foot">Class membership is configured routing eligibility, not a guarantee of equivalent quality, tools or available quota. A route outside cooldown is not a confirmed free subscription.</p></section><section class="cf-panel"><div class="cf-panel-heading"><div><span class="cf-section-kicker">SHARED QUOTA & RESET INTELLIGENCE</span><h2>Family budget scenarios</h2></div></div><div class="cf-table-scroll"><table class="cf-history-table"><thead><tr><th>Family</th><th>Weekly remaining / budget</th><th>Consumed</th><th>Next observed reset</th><th>Measured burn</th><th>Expansion scenario</th></tr></thead><tbody>${quota||'<tr><td colspan="6">Comparable quota telemetry is not available. Unknown limits are never converted to invented subscription counts.</td></tr>'}</tbody></table></div><p class="cf-history-foot">Families share each account’s five-hour window. Weekly family budgets are not independent subscriptions. Scenarios assume the measured workload continues, include 20% headroom, and never buy or reroute automatically.</p></section></div>`;
  }
  function settingsView(s) {
    const d=s.settings;
    if(!d)return `<section class="cf-panel cf-initial" data-key="settings">${empty("Reading live router controls","Checking the incumbent configuration owner and its effective revision.")}</section>`;
    const routes=d.routes||s.data.routes||[],editable=!!d.writable;
    return `<section class="cf-panel" data-key="settings"><div class="cf-panel-heading"><div><span class="cf-section-kicker">LIVE ROUTER SETTINGS</span><h2>Explicit changes. Verified application.</h2></div><span class="cf-state ${editable?"completed":"waiting"}">${editable?"Connected control owner":"Read-only until control owner is connected"}</span></div><p class="cf-history-foot">${escape(d.message||"Changes target the existing router configuration and affect future admissions. Credentials, provider enrollment and paid-routing permissions are not editable here.")}</p><div class="cf-settings-revision"><span>Configured revision <code>${escape(d.revision||"Not reported")}</code></span><span>Effective revision <code>${escape(d.effective_revision||"Not reported")}</code></span></div><div class="cf-settings-form"><div class="cf-settings-global"><label>Telemetry update interval <select data-setting="interval" ${!editable?"disabled":""}>${[.25,.5,1,2,5].map(v=>`<option value="${v}" ${v===(d.interval_s||2)?"selected":""}>${v} seconds</option>`).join("")}</select><small>Observation only; does not change inference limits.</small></label><label>Apply safety <strong>Shared writer lock + revision check</strong><small>The native writers serialize changes and reject stale revisions.</small></label></div><div class="cf-table-scroll"><table class="cf-history-table"><thead><tr><th>Route</th><th>Pool</th><th>Base priority</th><th>Base weight</th><th>Effective models</th></tr></thead><tbody>${routes.map(r=>`<tr data-key="setting:${escape(r.id)}"><td><b>${escape(r.id)}</b></td><td>${escape(r.provider||"")}</td><td><input type="number" min="0" max="100000" step="1" data-route="${escape(r.id)}" data-setting="priority" aria-label="Priority for ${escape(r.id)}" value="${r.priority}" ${!editable?"disabled":""}></td><td><input type="number" min="0" max="1000" step="0.1" data-route="${escape(r.id)}" data-setting="weight" aria-label="Weight for ${escape(r.id)}" value="${r.weight}" ${!editable?"disabled":""}></td><td><details class="cf-route-overrides"><summary>${(r.models||[]).length} models / per-model overrides</summary>${(r.models||[]).map(m=>`<div class="cf-override-row"><b>${escape(m)}</b><label>Priority <input type="number" min="0" max="100000" step="1" data-route="${escape(r.id)}" data-model="${escape(m)}" data-setting="model_priority" aria-label="${escape(m)} priority on ${escape(r.id)}" value="${(r.model_priority||{})[m]??r.priority}" ${!editable?"disabled":""}></label><label>Weight <input type="number" min="0" max="1000" step="0.1" data-route="${escape(r.id)}" data-model="${escape(m)}" data-setting="model_weight" aria-label="${escape(m)} weight on ${escape(r.id)}" value="${(r.model_weight||{})[m]??r.weight}" ${!editable?"disabled":""}></label></div>`).join("")}</details></td></tr>`).join("")}</tbody></table></div><div class="cf-settings-actions"><button type="button" class="cf-button" data-action="preview-settings" ${!editable?"disabled":""}>Validate changes</button><button type="button" class="cf-button" data-action="apply-settings" disabled>Apply validated changes</button><button type="button" class="cf-text-button" data-action="discard-settings">Reload effective settings</button><span class="cf-settings-result" role="status">${d.last_operation?"Last operation: "+escape(d.last_operation.state)+" / "+escape(d.last_operation.operation_id):s.lastSettingsReceipt?"Verified operation: "+escape(s.lastSettingsReceipt.state)+" / "+escape(s.lastSettingsReceipt.operation_id):"No changes applied."}</span></div></div></section>`;
  }

  function markSettingsEdited(s) {
    s.settingsEditing=true;s.validatedSettings=null;
    const button=s.root.querySelector('[data-action="apply-settings"]');if(button)button.disabled=true;
    const result=s.root.querySelector('.cf-settings-result');if(result&&!s.settingsPending)result.textContent="Unapplied edits. Validate the exact changes before applying.";
  }
  function settingsPatch(s) {
    const current=s.settings,patch={},routes=new Map((current.routes||[]).map(r=>[r.id,r])),changes=new Map();
    const interval=Number(s.root.querySelector('[data-setting="interval"]').value);
    if(interval!==current.interval_s)patch.interval_s=interval;
    for(const input of s.root.querySelectorAll('input[data-route][data-setting]')) {
      const row=routes.get(input.dataset.route),name=input.dataset.setting,value=Number(input.value),model=input.dataset.model;
      if(!row||!input.checkValidity()||input.value.trim()===""||!Number.isFinite(value))throw new Error("Every edited routing value must be a valid number within the displayed bounds.");
      const base=model?(row[name]||{})[model]??row[name.replace("model_","")]:row[name];
      if(value===base)continue;
      const change=changes.get(row.id)||{id:row.id};
      if(model){change[name]=change[name]||{};change[name][model]=value;}else change[name]=value;
      changes.set(row.id,change);
    }
    if(changes.size)patch.routes=[...changes.values()];
    if(!Object.keys(patch).length)throw new Error("No setting has changed.");
    return patch;
  }
  async function changeSettings(s,action) {
    if(s.settingsPending||!s.settings||!s.settings.writable)return;
    const result=s.root.querySelector('.cf-settings-result');let patch;
    try {patch=settingsPatch(s);}catch(error){result.textContent=error.message;return;}
    const fingerprint=JSON.stringify({revision:s.settings.revision,patch});
    if(action==="apply"&&(!s.validatedSettings||s.validatedSettings.fingerprint!==fingerprint)){
      result.textContent="The form changed after validation. Validate again before applying.";return;
    }
    s.settingsPending=true;s.settingsEditing=true;s.validatedSettings=action==="validate"?null:s.validatedSettings;
    const inputs=[...s.root.querySelectorAll('.cf-settings-form input,.cf-settings-form select,.cf-settings-form button')];
    inputs.forEach(el=>el.disabled=true);result.textContent=action==="validate"?"Validating against the live configuration owner...":"Applying the validated revision; waiting for an effective-state receipt...";
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),12000);
    try {
      const cookie=document.cookie.split(';').map(v=>v.trim()).find(v=>v.startsWith('admin_csrf='));
      const headers={'Content-Type':'application/json'};if(cookie)headers['X-CSRF-Token']=decodeURIComponent(cookie.slice('admin_csrf='.length));
      const response=await fetch('/api/capacity-router/settings',{method:'POST',credentials:'same-origin',cache:'no-store',headers,
        body:JSON.stringify({action,expected_revision:s.settings.revision,patch}),signal:controller.signal});
      const data=await response.json();if(s.disposed)return;
      if(response.status===401){unmount();if(s.options.onAuthFailure)s.options.onAuthFailure();return;}
      const operation=data.operation_id?` Operation ${data.operation_id.slice(0,10)}.`:"";
      if(data.state==="VALIDATED"&&data.ok&&action==="validate"){
        s.validatedSettings={fingerprint,patch};result.textContent="Validated by the native router. Review the values, then choose Apply validated changes."+operation;
      } else if(data.state==="APPLIED"&&data.ok){
        s.settingsEditing=false;s.validatedSettings=null;s.settings=null;result.textContent="Applied and verified against the effective router revision."+operation;
        s.lastSettingsReceipt=data;loadSupplement(s);
      } else {
        s.validatedSettings=null;result.textContent=(data.error||data.code||data.state||"No application confirmed")+operation;
        if(data.state==="EFFECT_UNKNOWN"||response.status===202){
          s.settings.writable=false;s.settingsEffectUnknown=true;s.settings.last_operation=data;
          result.textContent+=" Do not repeat the write. Reload effective settings to reconcile the receipt.";
        }
      }
    } catch(error) {
      if(!s.disposed){s.settings.writable=false;s.settingsEffectUnknown=true;s.validatedSettings=null;
        result.textContent="No application receipt was received. The request may have reached the router; reload effective settings to reconcile rather than repeating it.";}
    } finally {
      clearTimeout(timeout);s.settingsPending=false;
      if(!s.disposed&&s.root.isConnected){
        inputs.forEach(el=>{if(el.isConnected)el.disabled=!s.settings?.writable;});
        const apply=s.root.querySelector('[data-action="apply-settings"]');if(apply)apply.disabled=!s.validatedSettings||!s.settings?.writable;
        const reload=s.root.querySelector('[data-action="discard-settings"]');if(reload)reload.disabled=false;
      }
    }
  }

  async function reloadSettings(s) {
    if(s.settingsPending)return;
    s.settingsPending=true;s.validatedSettings=null;
    const terminal=new Set(["VALIDATED","APPLIED","NOT_APPLIED","CONFLICT","ROLLED_BACK"]);
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
    const options={credentials:"same-origin",cache:"no-store",signal:controller.signal};
    try {
      let response=await fetch("/api/capacity-router/settings",options);
      if(response.status===401){unmount();if(s.options.onAuthFailure)s.options.onAuthFailure();return;}
      if(!response.ok)throw new Error("Effective settings are unavailable.");
      let current=await response.json();
      const pending=current.last_operation;
      if(pending&&pending.operation_id&&!terminal.has(pending.state)) {
        const cookie=document.cookie.split(';').map(v=>v.trim()).find(v=>v.startsWith('admin_csrf='));
        const headers={'Content-Type':'application/json'};
        if(cookie)headers['X-CSRF-Token']=decodeURIComponent(cookie.slice('admin_csrf='.length));
        response=await fetch('/api/capacity-router/settings',{...options,method:'POST',headers,
          body:JSON.stringify({action:'reconcile',operation_id:pending.operation_id})});
        if(response.status===401){unmount();if(s.options.onAuthFailure)s.options.onAuthFailure();return;}
        const receipt=await response.json();
        if(terminal.has(receipt.state))s.lastSettingsReceipt=receipt;
        response=await fetch('/api/capacity-router/settings',options);
        if(!response.ok)throw new Error('Settings readback is unavailable. The original operation remains fenced.');
        current=await response.json();
      }
      if(s.disposed)return;
      s.settings=current;s.settingsEditing=false;
      s.settingsEffectUnknown=!!(current.last_operation&&!terminal.has(current.last_operation.state));
    } catch(error) {
      if(!s.disposed&&s.settings){s.settings.writable=false;s.settings.message='Unable to reconcile the native owner. No configuration write was repeated.';}
    } finally {
      clearTimeout(timeout);s.settingsPending=false;
      if(!s.disposed&&s.root.isConnected)renderView(s);
    }
  }

  function handleClick(s,e) {
    const selected=e.target.closest("[data-select]");
    if(selected) {if(selected.dataset.revealParent){s.query="";s.model="all";s.status="all";s.root.querySelector("[data-field=search]").value="";s.root.querySelector("[data-field=model]").value="all";s.root.querySelector("[data-field=status]").value="all";}s.selected={kind:selected.dataset.select,id:selected.dataset.id};s.page=0;renderView(s);renderInspector(s);return;}
    const view=e.target.closest("[data-view]");
    if(view) {s.view=view.dataset.view;s.page=0;renderView(s);loadSupplement(s);return;}
    const action=e.target.closest("[data-action]");if(!action)return;
    switch(action.dataset.action) {
      case "preview-settings":changeSettings(s,"validate");break;
      case "apply-settings":changeSettings(s,"apply");break;
      case "discard-settings":reloadSettings(s);break;
      case "pause": s.paused=!s.paused;action.innerHTML=icon(s.paused?"play":"pause")+`<span>${s.paused?"Resume":"Pause"}</span>`;updateConnection(s);if(s.paused){closeStream(s);clearTimeout(s.timer);}else{restartConnection(s);loadSupplement(s);}break;
      case "refresh": if(!s.paused){restartConnection(s);loadSupplement(s);}break;
      case "fullscreen": if(document.fullscreenElement)document.exitFullscreen();else if(s.root.requestFullscreen)s.root.requestFullscreen().catch(()=>{});break;
      case "clear":s.selected=null;s.query="";s.model="all";s.status="all";s.page=0;s.root.querySelector("input").value="";s.root.querySelector('[data-field="model"]').value="all";s.root.querySelector('[data-field="status"]').value="all";renderView(s);renderInspector(s);break;
      case "close":s.selected=null;renderInspector(s);renderView(s);break;
      case "zoom-in":s.scale=Math.min(3,s.scale*1.25);renderView(s);break;
      case "zoom-out":s.scale=Math.max(.05,s.scale/1.25);renderView(s);break;
      case "fit":s.scale=Math.max(.05,Math.min(1,(s.root.clientWidth||1200)/(s.mapWidth||1320),560/(s.mapHeight||540)));renderView(s);break;
      case "readable":s.scale=1;renderView(s);break;
      case "apply-range":{
        const start=new Date(s.root.querySelector('[data-field="from"]').value).getTime()/1000,end=new Date(s.root.querySelector('[data-field="to"]').value).getTime()/1000;
        if(!Number.isFinite(start)||!Number.isFinite(end)||start>=end||end>Date.now()/1000+10){s.root.querySelector(".cf-live-announcer").textContent="Choose a valid past time range.";break;}
        s.custom={start,end};s.view="history";s.history=null;renderView(s);loadSupplement(s);break;
      }
      case "previous":s.page=Math.max(0,s.page-1);renderView(s);break;
      case "next":s.page++;renderView(s);break;
      case "export":if(s.data&&s.data.ok){const url=URL.createObjectURL(new Blob([JSON.stringify(s.data,null,2)],{type:"application/json"}));const a=document.createElement("a");a.href=url;a.download=`capacity-fabric-${new Date().toISOString().replace(/[:.]/g,"-")}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}break;
    }
  }
  window.CapacityRouter = {mount,unmount};
})();
