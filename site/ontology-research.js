/* Explicit retrospective event research; no ranking, storage or live-entry signal. */
const LIMIT = 262144, BUDGET = 15000, HEX = /^[a-f0-9]{64}$/;
function fail() { throw new Error('RESEARCH_UNAVAILABLE'); }
function owner() { try { const id=window.MDXAuth?.user?.()?.id; return typeof id==='string' && id || null; } catch (_) { return null; } }
function words(en,zh) { const f=document.createDocumentFragment(); for(const [lang,text] of [['en',en],['zh',zh]]) { const n=document.createElement('span');n.className='l-'+lang;n.textContent=text;f.append(n); } return f; }
function node(tag,cls,en,zh) { const n=document.createElement(tag);if(cls)n.className=cls;if(en!==undefined)n.append(words(en,zh));return n; }
function note(en,zh) { return node('p','ox-note',en,zh); }
function day(v) { return typeof v==='string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0,10)===v; }
export function eventSelectionFromSearch(search) {
  if(typeof search!=='string' || search.length>2048)return null;
  try {
    // URLSearchParams tolerates malformed escapes; the continuation does not.
    decodeURIComponent(search.replace(/\+/g,' '));
    const params=new URLSearchParams(search),keys=['research_date','research_ticker','research_side'];
    if([...params.keys()].some(k=>k.startsWith('research_') && !keys.includes(k))
        || keys.some(k=>params.getAll(k).length!==1))return null;
    const [date,ticker,side]=keys.map(k=>params.get(k));
    if(!day(date) || date.startsWith('0000-') || !/^[A-Z0-9][A-Z0-9.-]{0,14}$/.test(ticker)
        || !['up','down'].includes(side))return null;
    return Object.freeze({date,ticker,side});
  } catch (_) { return null; }
}
function instant(v) { return typeof v==='string' && /(?:Z|[+-]\d\d:\d\d)$/.test(v) && Number.isFinite(Date.parse(v)); }
function cancel(reader) { try { void Promise.resolve(reader.cancel()).catch(()=>{}); } catch (_) {} }
function field(dl,en,zh,value) { const row=node('div','ox-company-field');row.append(node('dt','',en,zh));const dd=node('dd');dd.textContent=value;row.append(dd);dl.append(row); }
function pct(v) { return (v>0?'+':'')+(100*v).toFixed(2)+'%'; }
export function decodeResearch(value, selection) {
  const c=value?.capture,k=value?.case,n=c?.native,id=c?.native_identity,clock=c?.capture;
  if(value?.schema!=='ontology_drl_research.v1' || c?.schema!=='price_pressure.captured_event.v1'
      || !id || Object.keys(id).sort().join(',')!=='date,side,ticker'
      || Object.keys(selection).some(key=>id[key]!==selection[key]) || !day(id.date)
      || !['up','down'].includes(id.side) || !/^[A-Z0-9][A-Z0-9.-]{0,14}$/.test(id.ticker)
      || c.source?.artifact!=='data/price_pressure/latest.json' || c.source.schema!=='price_pressure.v1'
      || !HEX.test(c.source.snapshot_sha256) || !instant(c.source.generated_utc)
      || !instant(clock?.captured_at) || Date.parse(c.source.generated_utc)>Date.parse(clock.captured_at)
      || Date.parse(clock.captured_at)>Date.now()+1000 || id.date>clock.captured_at.slice(0,10)
      || clock.clock_class!=='system_recorded' || clock.historical_availability!=='unknown'
      || clock.scope!=='retrospective_captured_read' || !n
      || !['ret','peer_ret','resid','resid_z'].every(p=>typeof n[p]==='number' && Number.isFinite(n[p]))
      || !['market','sector'].includes(n.peer_basis) || typeof n.edgar_covered!=='boolean'
      || !['earnings-filing','other-filing','no-filing','filing-coverage-unknown'].includes(n.family)
      || !n.edgar_covered && n.family!=='filing-coverage-unknown'
      || k?.schema!=='opportunity_case.research.v1' || !/^opc_[a-f0-9]{64}$/.test(k.case_id)
      || !HEX.test(k.content_sha256) || k.research_state!=='partial'
      || k.evidence_binding?.state!=='exact_owner_native_event' || k.evidence_binding.scope!=='single_owner_event'
      || k.asof?.t0_source!=='drl_captured_read' || k.asof.t0_mode!=='retrospective_research'
      || k.asof.t0_evidence_ref?.owner_store!=='price_pressure.event'
      || ['date','ticker','side'].some(p=>k.asof.t0_evidence_ref.native_identity?.[p]!==id[p])
      || k.asof.t0_evidence_ref.native_digest?.sha256!==c.source.snapshot_sha256
      || k.asof.t0_evidence_ref.recorded_clock?.value!==clock.captured_at
      || k.calibrated?.state!=='unavailable'
      || ['opportunity_score','confidence','probability','impact'].some(p=>k.calibrated[p]!==null)
      || ['transmission','company_context','valuation_context','path_timing','portfolio_intersection'].some(p=>k[p]?.state!=='unavailable')) fail();
  for(const [authority,keys] of [[c.authority,['can_rank','can_size','can_gate','can_originate_signal','can_escalate']],
    [k.authority,['can_rank','can_gate','can_size','can_originate','can_open_entry']]]) {
    if(!authority || Object.keys(authority).sort().join(',')!==keys.sort().join(',') || keys.some(p=>authority[p]!==false))fail();
  }
  return value;
}
export function mountResearch(root) {
  if(!root)return null;
  const form=root.querySelector('form'),output=root.querySelector('[data-research-result]'),clearButton=root.querySelector('[data-research-clear]'),submit=form.querySelector('button[type=submit]');
  const selected=eventSelectionFromSearch(window.location.search);
  if(selected){for(const key of ['date','ticker','side'])form.elements[key].value=selected[key];root.open=true;}
  let epoch=0,operation=null,disposed=false,subscription=null,canonicalOwner=owner();
  const copy={idle:['Choose an event from Pressure Watch, then inspect its evidence here.','从个股承压页面选择事件，然后在此查看其证据。'],
    loading:['Reading the selected event and composing its evidence…','正在读取所选事件并整理其证据…'],
    signed_out:['Sign in before opening a private research case.','请登录后打开私有研究案例。'],
    forbidden:['This account does not include private research access.','此账户未包含私有研究权限。'],
    not_found:['That exact event is not present in the current retained snapshot. Select an event that the native page currently lists.','当前保留快照中没有此确切事件。请选择原生页面当前列出的事件。'],
    unavailable:['This research read is unavailable. The transmission and company views remain usable.','此研究读数暂不可用。传导路径与公司视图仍可使用。']};
  function state(s) { output.replaceChildren(note(...copy[s]));output.dataset.state=s;output.setAttribute('aria-busy',String(s==='loading'));submit.disabled=s==='loading'; }
  function stop() { epoch++;if(operation){const op=operation;operation=null;op.abort.abort();if(op.reader)cancel(op.reader);clearTimeout(op.timer);op.reject(new Error('RESEARCH_CANCELLED'));} }
  function clear() { stop();state('idle'); }
  function auth(event) { canonicalOwner=typeof event.detail?.user?.id==='string'?event.detail.user.id:null;clear(); }
  function check(op) { if(disposed || epoch!==op.id || document.hidden || op.abort.signal.aborted || performance.now()>=op.deadline || owner()!==op.owner || canonicalOwner!==op.owner)fail(); }
  async function checked(op,p) { const value=await p;check(op);return value; }
  const authentication=Promise.resolve().then(async()=>{const sdk=await window.MDXAuth?.client?.();
    if(disposed || typeof sdk?.auth?.onAuthStateChange!=='function')fail();
    subscription=sdk.auth.onAuthStateChange(clear)?.data?.subscription;if(typeof subscription?.unsubscribe!=='function')fail();return sdk;});
  void authentication.catch(()=>{});
  async function session(op,previous) {const sdk=await checked(op,authentication),r=await checked(op,sdk.auth.getSession()),s=r?.data?.session;
    if(r?.error || s?.user?.id!==op.owner || typeof s?.access_token!=='string' || !s.access_token || s.access_token.length>32768 || previous && previous!==s.access_token)fail();return s.access_token;}
  async function body(op,response) { const h=response.headers,parts=k=>(h.get(k)||'').toLowerCase().split(',').map(s=>s.trim());
    if(response.redirected || !/^application\/json(?:\s*;|$)/i.test(h.get('Content-Type')||'') || !parts('Cache-Control').includes('private') || !parts('Cache-Control').includes('no-store') || !parts('Vary').includes('authorization') || !parts('Vary').includes('cookie'))fail();
    const length=h.get('Content-Length');if(length!==null && (!/^\d+$/.test(length) || Number(length)>LIMIT))fail();
    const reader=response.body?.getReader();if(!reader)fail();op.reader=reader;let size=0,complete=false;const decoder=new TextDecoder('utf-8',{fatal:true}),pieces=[];
    try{for(;;){const chunk=await checked(op,reader.read());if(chunk.done)break;size+=chunk.value.byteLength;if(size>LIMIT)fail();pieces.push(decoder.decode(chunk.value,{stream:true}));}
      pieces.push(decoder.decode());check(op);const value=JSON.parse(pieces.join(''));complete=true;return value;
    }finally{if(!complete)cancel(reader);if(op.reader===reader)op.reader=null;try{reader.releaseLock();}catch(_){}}}
  function render(v) {const c=v.capture,k=v.case,n=c.native,id=c.native_identity;output.replaceChildren();output.dataset.state='ready';output.setAttribute('aria-busy','false');submit.disabled=false;
    output.append(node('h3','',id.ticker+' · '+id.date,id.ticker+' · '+id.date));
    output.append(note('Observed price move versus '+(n.peer_basis==='market'?'the market.':'sector peers.'), '已观测价格变动，对照'+(n.peer_basis==='market'?'市场。':'行业同类。')));
    const values=node('dl','ox-company-fields');field(values,'Price move','价格变动',pct(n.ret));field(values,n.peer_basis==='market'?'Market move':'Sector-peer move',n.peer_basis==='market'?'市场变动':'行业同类变动',pct(n.peer_ret));field(values,'Residual difference','残差差异',pct(n.resid));output.append(values);
    output.append(note('This is a captured retrospective reading. Historical availability and the economic cause are unknown; no entry, rank or sizing recommendation follows.', '这是捕获时的回溯读数。历史可用性与经济原因未知；不构成入场、排名或仓位建议。'));
    output.append(note(n.edgar_covered?'The native filing family is context, not proof of cause.':'Filings are not tracked for this event. This does not mean that no filing exists.',n.edgar_covered?'原生披露分类仅提供背景，不证明原因。':'本事件未跟踪披露。这并不表示不存在披露。'));
    output.append(note('Company, valuation, transmission, portfolio and live-entry context are unavailable in this single-event case.', '此单事件案例中的公司、估值、传导、投资组合与实时入场背景均不可用。'));
    const d=node('details','ox-detail');d.append(node('summary','','Evidence and capture time','证据与捕获时间'));const dl=node('dl','ox-company-fields ox-company-references');
    field(dl,'Snapshot built','快照构建',c.source.generated_utc);field(dl,'Captured for this reading','本次读数捕获',c.capture.captured_at);field(dl,'Native event family','原生事件分类',n.family);field(dl,'Source digest','来源摘要',c.source.snapshot_sha256);field(dl,'Research case','研究案例',k.case_id);d.append(dl);output.append(d);
  }
  async function evaluate(event) {event.preventDefault();clear();const id=owner();if(!id || id!==canonicalOwner){state('signed_out');return;}
    const selection={date:form.elements.date.value,ticker:form.elements.ticker.value.trim().toUpperCase(),side:form.elements.side.value};
    if(!day(selection.date) || !/^[A-Z0-9][A-Z0-9.-]{0,14}$/.test(selection.ticker) || !['up','down'].includes(selection.side)){state('unavailable');return;}
    const op={id:epoch,owner:id,abort:new AbortController(),deadline:performance.now()+BUDGET,reader:null};const cancellation=new Promise((_,reject)=>{op.reject=reject;});operation=op;
    op.timer=setTimeout(()=>{op.abort.abort();if(op.reader)cancel(op.reader);op.reject(new Error('RESEARCH_TIMEOUT'));},BUDGET);state('loading');
    try{await Promise.race([(async()=>{const token=await session(op);const response=await checked(op,fetch('/api/ontology/explorer/research/v1',{method:'POST',credentials:'same-origin',cache:'no-store',redirect:'error',signal:op.abort.signal,headers:{Accept:'application/json','Content-Type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify({schema:'ontology_drl_research_request.v1',...selection})}));
      const value=await body(op,response);await session(op,token);check(op);if(response.status!==200){state(response.status===401?'signed_out':response.status===403?'forbidden':response.status===404?'not_found':'unavailable');return;}
      const decoded=decodeResearch(value,selection);await session(op,token);check(op);render(decoded);
    })(),cancellation]);}catch(_){if(!disposed && epoch===op.id)state(owner()!==op.owner?'signed_out':'unavailable');}
    finally{op.abort.abort();if(op.reader)cancel(op.reader);clearTimeout(op.timer);if(operation===op)operation=null;}}
  function hidden(){if(document.hidden)clear();}
  function language(){const lang=document.documentElement.dataset.lang==='zh'?'zh':'en';for(const option of form.querySelectorAll('option'))option.textContent=option.dataset[lang];}
  form.addEventListener('submit',evaluate);form.addEventListener('input',clear);form.addEventListener('change',clear);document.addEventListener('langchange',language);clearButton.addEventListener('click',clear);window.addEventListener('mdx-auth',auth);window.addEventListener('pagehide',clear);document.addEventListener('visibilitychange',hidden);language();state('idle');
  return {dispose(){disposed=true;clear();subscription?.unsubscribe();form.removeEventListener('submit',evaluate);form.removeEventListener('input',clear);form.removeEventListener('change',clear);document.removeEventListener('langchange',language);clearButton.removeEventListener('click',clear);window.removeEventListener('mdx-auth',auth);window.removeEventListener('pagehide',clear);document.removeEventListener('visibilitychange',hidden);}};
}
mountResearch(document.getElementById('ox-research'));
