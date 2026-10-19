/* Explicit house Theme Map continuation. Uses the selected owner identity and
 * current reading; no symbol join, persistence, telemetry or inferred exposure. */
const HASH = /^sha256:[a-f0-9]{64}$/, HEX = /^[a-f0-9]{64}$/;
const METHOD = 'ontology_house_theme_continuation.v1', LIMIT = 262144, BUDGET = 15000;
const FILES = ['config/theme_sources.yml', ...['edges','evidence','identity_resolution','node_lifecycle','nodes'].map(n => 'data/theme_graph/' + n + '.parquet')].sort();
const STATES = ['AVAILABLE','PARTIAL','NO_QUALIFIED_HOUSE_PATH','NO_GRAPH_BINDING','IDENTITY_OWNER_UNAVAILABLE'];
function fail() { throw new Error('THEME_UNAVAILABLE'); }
function owner() { try { const u = window.MDXAuth?.user?.(); return typeof u?.id === 'string' && u.id || null; } catch (_) { return null; } }
function stamp(v) { return typeof v === 'string' && v.length <= 64 && /(?:Z|[+-]\d\d:\d\d| UTC)$/.test(v) && Number.isFinite(time(v)); }
function time(v) { return Date.parse(v.replace(' UTC','Z').replace(' ','T')); }
function day(v) { return typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0,10) === v; }
function str(v, bound = 512) { return typeof v === 'string' && v.length > 0 && v.length <= bound && !/[\x00-\x1f]/.test(v); }
function identity(v) { return v?.identity_kind === 'security' && str(v.identity_id) && /^SEC:\S+$/.test(v.identity_id) && str(v.symbol,24); }
function words(en, zh) { const out = document.createDocumentFragment(); for (const [lang,value] of [['en',en],['zh',zh]]) { const n = document.createElement('span'); n.className = 'l-' + lang; n.textContent = value; out.append(n); } return out; }
function node(tag, cls, en, zh) { const n = document.createElement(tag); if (cls) n.className = cls; if (en !== undefined) n.append(words(en,zh)); return n; }
function note(en,zh) { return node('p','ox-note',en,zh); }
function field(list,en,zh,value) { const row = node('div','ox-company-field'); row.append(node('dt','',en,zh)); const dd = node('dd'); dd.textContent = value; row.append(dd); list.append(row); }
function cancel(reader) { try { void Promise.resolve(reader.cancel()).catch(() => {}); } catch (_) { /* best effort */ } }
function house(n) {
  if (!n || !str(n.node_id) || !['theme','basket'].includes(n.kind)
      || !(n.tier === null || str(n.tier,80))
      || !['name_en','name_zh'].every(k => n[k] === null || n[k] === '' || str(n[k],1024))
      || n.rights?.family !== 'mastermind_curated' || n.rights.public_display_allowed !== true
      || !['direct_display_ok','derived_display_ok'].includes(n.rights.rights_class)) fail();
}
export async function decodeTheme(value, reading, selected) {
  const s = value?.source, m = value?.theme_map;
  if (value?.schema !== 'ontology_theme_continuation.v1' || !s || !m
      || s.chain !== reading.chain || s.asof !== reading.asof || !stamp(s.built) || time(s.built) !== time(reading.built)
      || s.source_manifest_hash !== reading.source_manifest_hash || s.method !== METHOD || !HASH.test(s.theme_source_manifest_hash)
      || value.selection?.identity_kind !== selected.identity_kind || value.selection?.identity_id !== selected.identity_id
      || m.schema !== 'gmi.theme_security_hierarchy_display/v1' || m.authority_ceiling !== 'display_only'
      || m.query?.kind !== selected.identity_kind || m.query?.id !== selected.identity_id || m.asof !== reading.asof
      || !stamp(m.knowledge_cutoff) || time(m.knowledge_cutoff) !== time(reading.built)
      || m.identity_basis !== 'LATEST_PUBLISHED_OWNER_REFERENCE' || m.identity_owner !== 'gmi.identity_resolution/v1'
      || m.historical_identity_claim !== false || m.knowledge_cutoff_applies_to !== 'GRAPH_PATHS_ONLY'
      || m.etf_tracking?.status !== 'unavailable' || m.etf_tracking.reason !== 'ETF_DISPLAY_BINDING_NOT_COMPOSED'
      || !STATES.includes(m.availability?.state) || !Array.isArray(m.bindings) || m.bindings.length > 64
      || !Array.isArray(s.reads) || s.reads.length !== FILES.length) fail();
  const reads = [...s.reads].sort((a,b) => String(a.path).localeCompare(String(b.path)));
  for (let i = 0; i < reads.length; i++) {
    if (reads[i]?.path !== FILES[i] || !HEX.test(reads[i].sha256) || !Number.isSafeInteger(reads[i].bytes)
        || reads[i].bytes <= 0 || reads[i].bytes > 33554432) fail();
  }
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode([METHOD,...reads.map(r => r.path + ':' + r.sha256)].join('\n')));
  if (s.theme_source_manifest_hash !== 'sha256:' + [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2,'0')).join('')) fail();
  const ids = new Set(); let available = 0, pathCount = 0;
  for (const b of m.bindings) {
    const r = b.resolution;
    if (!r || !str(r.node_id) || !r.node_id.startsWith('co:') || ids.has(r.node_id) || r.security_id !== selected.identity_id
        || !(r.issuer_id === null || str(r.issuer_id) && r.issuer_id.startsWith('ISS:'))
        || !str(r.listing_key) || !Number.isSafeInteger(r.graph_identity_epoch) || r.graph_identity_epoch < 1 || !str(r.master_code_version)
        || !day(r.resolution_asof) || !stamp(r.computed_at) || !stamp(r.master_generated_at)
        || time(r.computed_at) > Date.now() || Date.parse(r.resolution_asof) > Date.now()
        || !Array.isArray(b.paths) || b.paths.length > 128) fail();
    ids.add(r.node_id); pathCount += b.paths.length; if (pathCount > 256) fail();
    if (b.paths.length) { available++; if (b.status !== 'available' || b.reason !== null) fail(); }
    else if (b.status !== 'unavailable' || b.reason !== 'NO_QUALIFIED_HOUSE_PATH') fail();
    for (const p of b.paths) {
      if (!p || !Array.isArray(p.path) || !p.path.length || p.path.length > 32
          || !Array.isArray(p.parent_of_edge_ids) || p.parent_of_edge_ids.length !== p.path.length - 1
          || p.parent_of_edge_ids.some(id => !str(id)) || new Set(p.parent_of_edge_ids).size !== p.parent_of_edge_ids.length
          || !str(p.anchor_node_id) || p.anchor_node_id !== p.path[p.path.length-1].node_id
          || new Set(p.path.map(n => n?.node_id)).size !== p.path.length
          || !Array.isArray(p.via) || !p.via.length || p.via.length > 2) fail();
      p.path.forEach(house); if (p.path.some(n => n.kind !== 'theme')) fail();
      for (const hop of p.via) { if (!['MEMBER_OF','EXPRESSES'].includes(hop?.type) || !str(hop.edge_id)) fail(); house(hop.node); }
    }
  }
  if (m.bindings.length) {
    if (m.availability.state !== (available === m.bindings.length ? 'AVAILABLE' : available ? 'PARTIAL' : 'NO_QUALIFIED_HOUSE_PATH')) fail();
  } else if (!['NO_GRAPH_BINDING','IDENTITY_OWNER_UNAVAILABLE'].includes(m.availability.state)) fail();
  return value;
}
export function mountTheme(root) {
  if (!root) return null;
  const output = root.querySelector('[data-theme-result]'), read = root.querySelector('[data-theme-read]'), clearButton = root.querySelector('[data-theme-clear]');
  const company = document.getElementById('ox-company');
  if (!output || !read || !clearButton || !company) return null;
  let reading = null, selected = null, operation = null, epoch = 0, disposed = false, subscription = null, canonicalOwner = owner();
  function status(state) {
    output.replaceChildren(); output.dataset.state = state; output.setAttribute('aria-busy', state === 'loading' ? 'true' : 'false');
    const copy = {
      no_reading: ['Load a current path reading first.', '请先加载当前路径读数。'],
      no_company: ['Select a company in Company research above.', '请先在上方公司研究中选择公司。'],
      idle: ['Read the selected company’s house-curated paths when ready.', '准备就绪后，读取所选公司的自有主题路径。'],
      loading: ['Reading qualified house theme paths…', '正在读取合格的自有主题路径…'],
      signed_out: ['Sign in again before reading the company Theme Map.', '请重新登录后读取公司主题图谱。'],
      forbidden: ['This account does not include private Theme Map research.', '此账户未包含私有主题图谱研究权限。'],
      changed: ['The selected source changed. Reload the path before reading again.', '所选数据源已变化，请重新加载路径后再读取。'],
      unavailable: ['The house Theme Map is unavailable for this reading.', '本次自有主题图谱读数不可用。'],
    };
    output.append(note(...copy[state])); read.disabled = !reading || !selected || state === 'loading';
  }
  function stop() { epoch++; if (operation) { const old=operation; operation=null; old.abort.abort(); if(old.reader)cancel(old.reader); clearTimeout(old.timer); old.reject(new Error('THEME_CANCELLED')); } }
  function clear() { stop(); status(!reading ? 'no_reading' : !selected ? 'no_company' : 'idle'); }
  function invalidate() { reading=null; selected=null; clear(); }
  function auth(event) { canonicalOwner=typeof event.detail?.user?.id === 'string' ? event.detail.user.id : null; selected=null; if (reading?.owner_id !== canonicalOwner || canonicalOwner !== owner()) reading=null; clear(); }
  function check(op) { if (disposed || epoch !== op.id || document.hidden || reading !== op.reading || selected !== op.selected
      || op.abort.signal.aborted || performance.now() >= op.deadline || owner() !== op.owner || canonicalOwner !== op.owner) fail(); }
  async function checked(op,promise) { const value=await promise; check(op); return value; }
  const authentication=Promise.resolve().then(async()=>{ const sdk=await window.MDXAuth?.client?.();
    if(disposed || typeof sdk?.auth?.onAuthStateChange !== 'function')fail();
    const result=sdk.auth.onAuthStateChange(()=>{ selected=null; clear(); }); subscription=result?.data?.subscription;
    if(typeof subscription?.unsubscribe !== 'function')fail();return sdk; });
  void authentication.catch(()=>{});
  async function session(op,token) { const sdk=await checked(op,authentication), result=await checked(op,sdk.auth.getSession()), s=result?.data?.session;
    if(result?.error || s?.user?.id !== op.owner || !str(s?.access_token,32768))fail();
    if(token && token !== s.access_token) { selected=null; clear(); fail(); } return s.access_token; }
  async function body(op,response) {
    const h=response.headers, parts=k=>(h.get(k)||'').toLowerCase().split(',').map(s=>s.trim());
    if(response.redirected || !/^application\/json(?:\s*;|$)/i.test(h.get('Content-Type')||'')
        || !parts('Cache-Control').includes('private') || !parts('Cache-Control').includes('no-store')
        || !parts('Vary').includes('authorization') || !parts('Vary').includes('cookie'))fail();
    const length=h.get('Content-Length');if(length !== null && (!/^\d+$/.test(length) || Number(length)>LIMIT))fail();
    const reader=response.body?.getReader();if(!reader)fail();op.reader=reader;
    const decoder=new TextDecoder('utf-8',{fatal:true}),pieces=[];let size=0,complete=false;
    try { for(;;) { const chunk=await checked(op,reader.read());if(chunk.done)break;if(!(chunk.value instanceof Uint8Array))fail();
      size+=chunk.value.byteLength;if(size>LIMIT)fail();pieces.push(decoder.decode(chunk.value,{stream:true})); }
      pieces.push(decoder.decode());check(op);const v=JSON.parse(pieces.join(''));complete=true;return v;
    } finally { if(!complete)cancel(reader);if(op.reader===reader)op.reader=null;try{reader.releaseLock();}catch(_){/* abandoned read */} }
  }
  function label(n) { return words(n.name_en && n.name_en !== n.node_id ? n.name_en : 'Name unavailable', n.name_zh && n.name_zh !== n.node_id ? n.name_zh : '名称不可用'); }
  function render(v) {
    output.replaceChildren();output.dataset.state='ready';output.setAttribute('aria-busy','false');read.disabled=false;
    output.append(node('h3','',selected.symbol+' · house Theme Map',selected.symbol+' · 自有主题图谱'));
    output.append(note('Graph effective date: '+v.theme_map.asof+'. Graph knowledge cutoff: '+v.theme_map.knowledge_cutoff+'.', '图谱生效日期：'+v.theme_map.asof+'。图谱知识截止：'+v.theme_map.knowledge_cutoff+'。'));
    output.append(note('Identity uses the latest published owner binding, not historical identity. Share classes and graph bindings stay separate.', '身份使用数据方最新发布的绑定，不代表历史身份。各股份类别与图谱绑定分别保留。'));
    if(!v.theme_map.bindings.length) output.append(note('No qualified graph binding is available. This does not establish that the company has no themes.', '暂无合格的图谱绑定。这不证明该公司没有相关主题。'));
    for(const binding of v.theme_map.bindings) {
      const card=node('article','ox-card'), r=binding.resolution;
      card.append(note('Listing: '+r.listing_key, '上市标识：'+r.listing_key));
      if(!binding.paths.length)card.append(note('No house path is qualified for this binding and reading.', '该绑定与读数暂无合格的自有主题路径。'));
      for(const path of binding.paths) {
        const line=node('p','ox-note');path.path.forEach((n,i)=>{if(i)line.append(document.createTextNode(' → '));line.append(label(n));});card.append(line);
        for(const via of path.via) { const row=node('p','ox-note');row.append(words(via.type==='MEMBER_OF'?'Member of: ':'Expresses: ',via.type==='MEMBER_OF'?'所属成员组：':'表达主题：'),label(via.node));card.append(row); }
      }
      const details=node('details','ox-detail');details.append(node('summary','','Identity references and clocks','身份引用与时间'));
      const list=node('dl','ox-company-fields ox-company-references');field(list,'Security','证券',r.security_id);if(r.issuer_id)field(list,'Issuer','发行人',r.issuer_id);
      field(list,'Graph binding','图谱绑定',r.node_id);field(list,'Identity evidence date','身份凭证日期',r.resolution_asof);
      field(list,'Identity computation','身份计算时刻',r.computed_at);field(list,'Identity master generation','身份主表生成时刻',r.master_generated_at);details.append(list);card.append(details);output.append(card);
    }
    output.append(note('ETF tracking is not available in this continuation. These paths confer no ranking, sizing or trading authority.', '本次续接尚不提供 ETF 跟踪。这些路径不赋予排名、仓位或交易权限。'));
    const details=node('details','ox-detail');details.append(node('summary','','Selected source references','所选来源引用'));
    const list=node('dl','ox-company-fields ox-company-references');field(list,'Path reading','路径读数',v.source.source_manifest_hash);field(list,'Theme source generation','主题来源版本',v.source.theme_source_manifest_hash);details.append(list);output.append(details);
  }
  async function evaluate() {
    clear();if(!reading || !selected || document.hidden)return;const user=owner();
    if(!user || user!==canonicalOwner || user!==reading.owner_id || user!==selected.owner_id){invalidate();status('signed_out');return;}
    const op={id:epoch,owner:user,reading,selected,abort:new AbortController(),reader:null,deadline:performance.now()+BUDGET};
    const cancellation=new Promise((_,reject)=>{op.reject=reject;});operation=op;
    op.timer=setTimeout(()=>{op.abort.abort();if(op.reader)cancel(op.reader);op.reject(new Error('THEME_TIMEOUT'));},BUDGET);status('loading');
    try { await Promise.race([(async()=>{
      const token=await session(op),raw=JSON.stringify({schema:'ontology_theme_request.v1',chain:reading.chain,source_manifest_hash:reading.source_manifest_hash,
        identity_kind:selected.identity_kind,identity_id:selected.identity_id});
      if(new TextEncoder().encode(raw).length>4096)fail();
      const response=await checked(op,fetch('/api/ontology/explorer/theme/v1',{method:'POST',credentials:'same-origin',cache:'no-store',redirect:'error',signal:op.abort.signal,
        headers:{Accept:'application/json','Content-Type':'application/json',Authorization:'Bearer '+token},body:raw}));
      const value=await checked(op,body(op,response));await session(op,token);
      if(response.status!==200){if(response.status===401){invalidate();status('signed_out');}else if(response.status===403)status('forbidden');
        else if(response.status===409 && value?.detail?.code==='source_changed'){invalidate();status('changed');}else status('unavailable');return;}
      const result=await checked(op,decodeTheme(value,op.reading,op.selected));
      await session(op,token);render(result);
    })(),cancellation]); } catch(_){if(!disposed && epoch===op.id){if(owner()!==op.owner || canonicalOwner!==op.owner){invalidate();status('signed_out');}else status('unavailable');}}
    finally{op.abort.abort();if(op.reader)cancel(op.reader);clearTimeout(op.timer);if(operation===op)operation=null;}
  }
  function receive(event){reading=null;clear();const r=event.detail;if(!r || r.chain!=='oil_inflation_duration_derate' || !HASH.test(r.source_manifest_hash)
    || !day(r.asof) || !stamp(r.built) || !r.owner_id || r.owner_id!==owner() || r.owner_id!==canonicalOwner)return;
    reading={chain:r.chain,source_manifest_hash:r.source_manifest_hash,asof:r.asof,built:r.built,owner_id:r.owner_id};clear();}
  function select(event){const s=event.detail;if(identity(s) && s.owner_id===owner() && s.owner_id===canonicalOwner){
    if(selected && Object.keys(selected).every(k=>selected[k]===s[k]))return;
    selected={identity_kind:s.identity_kind,identity_id:s.identity_id,symbol:s.symbol,owner_id:s.owner_id};
    }else selected=null;clear();}
  function hidden(){if(document.hidden){selected=null;clear();}}
  root.addEventListener('ontology-reading',receive);root.addEventListener('ontology-source-changed',invalidate);company.addEventListener('ontology-company-identity',select);
  window.addEventListener('mdx-auth',auth);window.addEventListener('pagehide',invalidate);document.addEventListener('visibilitychange',hidden);
  read.addEventListener('click',evaluate);clearButton.addEventListener('click',clear);status('no_reading');
  root.dispatchEvent(new CustomEvent('ontology-consumer-ready'));company.dispatchEvent(new CustomEvent('ontology-identity-ready'));
  return {dispose(){disposed=true;invalidate();output.replaceChildren();subscription?.unsubscribe();
    root.removeEventListener('ontology-reading',receive);root.removeEventListener('ontology-source-changed',invalidate);company.removeEventListener('ontology-company-identity',select);
    window.removeEventListener('mdx-auth',auth);window.removeEventListener('pagehide',invalidate);document.removeEventListener('visibilitychange',hidden);
    read.removeEventListener('click',evaluate);clearButton.removeEventListener('click',clear);}};
}
mountTheme(document.getElementById('ox-theme'));
