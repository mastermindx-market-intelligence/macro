/* Explicit house Theme Map continuation. Uses the selected owner identity and
 * current reading; no symbol join, persistence, telemetry or inferred exposure. */
const HASH = /^sha256:[a-f0-9]{64}$/, HEX = /^[a-f0-9]{64}$/;
const METHOD = 'ontology_house_theme_continuation.v1', LIMIT = 262144, BUDGET = 15000;
const FILES = ['config/theme_sources.yml', ...['edges','evidence','identity_resolution','node_lifecycle','nodes'].map(n => 'data/theme_graph/' + n + '.parquet')].sort();
const IDENTITY_FILES = ['data/reference/_receipt.json','data/reference/security_master.parquet','data/reference/vendor_aliases.parquet'];
const ETF_REASONS = {
  ETF_IDENTITY_INPUTS_UNAVAILABLE: ['Native identity inputs unavailable.', '原生身份输入不可用。'],
  ETF_GRAPH_IDENTITY_UNQUALIFIED: ['Graph identity is not qualified.', '图谱身份尚未合格。'],
  AMBIGUOUS_ACTIVE_COMPANY_WRAPPER: ['An active company binding conflicts with this ETF.', '活动公司绑定与此 ETF 存在冲突。'],
  AMBIGUOUS_CANONICAL_ALIAS: ['Native aliases disagree on identity.', '原生别名的身份绑定不一致。'],
  ETF_CANONICAL_ALIAS_UNAVAILABLE: ['Canonical alias unavailable.', '规范别名不可用。'],
  ETF_CANONICAL_SECURITY_UNAVAILABLE: ['Canonical security unavailable.', '规范证券身份不可用。'],
  ETF_INSTRUMENT_TYPE_UNQUALIFIED: ['Native listing does not qualify the ETF type.', '原生上市记录未确认 ETF 类型。'],
};
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
function knownClock(value, cutoff) {
  return day(value) ? Date.parse(value) + 86400000 <= time(cutoff) : stamp(value) && time(value) <= time(cutoff);
}
function decodeIdentitySources(reads) {
  const paths = reads.map(r => r.path);
  if (new Set(paths).size !== paths.length || FILES.some(p => !paths.includes(p))) fail();
  const extra = paths.filter(p => !FILES.includes(p));
  let observed = null;
  for (const p of extra) {
    if (IDENTITY_FILES.includes(p)) continue;
    const match = /^data\/symbol_directory\/(?:snapshots\/(\d{4}-\d{2}-\d{2})\.parquet|receipts\/snapshots\/(\d{4}-\d{2}-\d{2})\.json)$/.exec(p);
    const value = match?.[1] || match?.[2];
    if (!day(value) || Date.parse(value) > Date.now() || observed && observed !== value) fail();
    observed = value;
  }
  // An unavailable identity may expose the prefix of a failed native read.
  // Available identities require the full five-input generation below.
  const order = [...IDENTITY_FILES, `data/symbol_directory/snapshots/${observed}.parquet`,
    `data/symbol_directory/receipts/snapshots/${observed}.json`];
  if (extra.some(p => !order.slice(0,extra.length).includes(p))) fail();
  return {count:extra.length, observed};
}
function currentMasterClock(v) {
  // The native master producer also emits naive ISO UTC stamps.
  if (stamp(v) && day(v.slice(0,10))) return time(v);
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?$/.test(v)) return NaN;
  return day(v.slice(0,10)) ? Date.parse(v+'Z') : NaN;
}
function decodeEtfIdentity(v, sources) {
  if (v?.status === 'unavailable') {
    if (Object.keys(v).sort().join(',') !== 'reason,status' || !Object.hasOwn(ETF_REASONS,v.reason)) fail();
    return false;
  }
  const keys = ['status','reason','security_id','listing_key','identity_basis','historical_identity_claim',
    'instrument_type','instrument_type_basis','master_generated_at','listing_observed_on','listing_known_at'];
  const generated = currentMasterClock(v?.master_generated_at);
  if (v?.status !== 'available' || v.reason !== null || Object.keys(v).sort().join(',') !== keys.sort().join(',')
      || !str(v.listing_key) || !/^US-[A-Z0-9]{4}-[^\s:]+$/.test(v.listing_key) || v.security_id !== 'SEC:'+v.listing_key
      || v.identity_basis !== 'LATEST_PUBLISHED_DATAOS_VENDOR_ALIAS' || v.historical_identity_claim !== false
      || v.instrument_type !== 'ETF' || v.instrument_type_basis !== 'NATIVE_LISTING_OBSERVATION_ONLY'
      || !Number.isFinite(generated) || generated > Date.now()
      || !stamp(v.listing_known_at) || time(v.listing_known_at) > Date.now()
      || sources.count !== 5 || v.listing_observed_on !== sources.observed) fail();
  return true;
}
function decodeTracking(tracking, map, selected, sources) {
  function relation(v, relationship) {
    const c=v?.clocks;
    if(v?.relationship!==relationship || !str(v.edge_id) || !['observed','reconstruction'].includes(v.era)
        || !['seed_constant','curated_changelog'].includes(v.date_provenance)
        || !c || !day(c.valid_from) || c.valid_from>map.asof
        || !(c.valid_to===null || day(c.valid_to) && c.valid_to>map.asof)
        || !['evidence_time','belief_time','computed_at'].every(k=>knownClock(c[k],map.knowledge_cutoff))
        || !Array.isArray(v.evidence) || !v.evidence.length || v.evidence.length>32) fail();
    const seen=new Set();
    for(const receipt of v.evidence) {
      if(!str(receipt?.evidence_id) || seen.has(receipt.evidence_id)
          || !knownClock(receipt.published_at,map.knowledge_cutoff) || !knownClock(receipt.computed_at,map.knowledge_cutoff)) fail();
      seen.add(receipt.evidence_id);
    }
  }
  const powers = ['can_rank','can_gate','can_size','can_trade','can_originate','can_escalate'];
  if (tracking?.schema !== 'gmi.theme_etf_tracking_display/v1' || tracking.exhaustive !== false
      || tracking.meaning !== 'curated_tracking_reference_not_holdings' || tracking.authority_ceiling !== 'display_only'
      || tracking.holdings?.status !== 'unavailable' || tracking.holdings.asof !== null
      || tracking.weights !== null || tracking.performance !== null || powers.some(k => tracking.authority?.[k] !== false)
      || !Array.isArray(tracking.references) || tracking.references.length > 128) fail();
  if (!tracking.references.length) {
    if (sources.count !== 0 || tracking.security_identity?.status !== 'unavailable' || tracking.security_identity.reason !== 'ETF_SECURITY_IDENTITY_NOT_BOUND'
        || tracking.status !== 'unavailable' || !['NO_QUALIFIED_ETF_TRACKING_REFERENCE','HOUSE_DISPLAY_PERMISSION_UNAVAILABLE','ETF_REFERENCE_BOUND_EXCEEDED'].includes(tracking.reason)) fail();
    return;
  }
  if (tracking.status !== 'available' || tracking.reason !== null) fail();
  const seen = new Set(); let resolved = 0;
  for (const ref of tracking.references) {
    const binding = map.bindings.find(b => b.resolution.node_id === ref?.binding_node_id);
    const basket = ref?.membership?.basket;
    const c = ref?.clocks, permission = ref?.relationship_rights;
    if (!binding || !basket || ref.selected_security_id !== selected.identity_id || ref.selected_security_id !== binding.resolution.security_id
        || ref.relationship !== 'TRACKS' || !str(ref.edge_id) || !str(ref.symbol,24) || !/^[A-Z0-9][A-Z0-9._-]*$/.test(ref.symbol)
        || ref.etf_node_id !== 'etf:' + ref.symbol || !['observed','reconstruction'].includes(ref.era)
        || !['seed_constant','curated_changelog'].includes(ref.date_provenance)
        || permission?.family !== 'mastermind_curated' || permission.public_display_allowed !== true
        || !['direct_display_ok','derived_display_ok'].includes(permission.rights_class)
        || !c || !day(c.valid_from) || c.valid_from > map.asof
        || !(c.valid_to === null || day(c.valid_to) && c.valid_to > map.asof)
        || !['evidence_time','belief_time','computed_at'].every(k => knownClock(c[k],map.knowledge_cutoff))
        || !Array.isArray(ref.evidence) || !ref.evidence.length || ref.evidence.length > 32) fail();
    relation(ref.membership,'MEMBER_OF'); house(basket);
    if(ref.membership.subject_node_id!==binding.resolution.node_id
        || basket.kind!=='basket' || basket.node_id!==ref.basket_node_id
        || basket.rights.rights_class!==permission.rights_class) fail();
    if (decodeEtfIdentity(ref.security_identity,sources)) resolved++;
    const key = JSON.stringify([ref.binding_node_id, ref.basket_node_id, ref.membership.edge_id, ref.edge_id]);
    if (seen.has(key)) fail(); seen.add(key);
    const evidence = new Set();
    for (const receipt of ref.evidence) {
      if (!str(receipt?.evidence_id) || evidence.has(receipt.evidence_id)
          || !knownClock(receipt.published_at,map.knowledge_cutoff) || !knownClock(receipt.computed_at,map.knowledge_cutoff)) fail();
      evidence.add(receipt.evidence_id);
    }
  }
  if (tracking.security_identity?.status !== (resolved === tracking.references.length ? 'available' : resolved ? 'partial' : 'unavailable')
      || tracking.security_identity.reason !== (resolved === tracking.references.length ? null : 'ETF_IDENTITY_NOT_FULLY_RESOLVED')) fail();
}
export async function decodeTheme(value, reading, selected) {
  const s = value?.source, m = value?.theme_map;
  if (value?.schema !== 'ontology_theme_continuation.v1' || !s || !m
      || s.chain !== reading.chain || s.asof !== reading.asof || !stamp(s.built) || time(s.built) !== time(reading.built)
      || s.source_manifest_hash !== reading.source_manifest_hash || s.method !== METHOD || !HASH.test(s.theme_source_manifest_hash)
      || s.policy_binding !== 'AUTHORITATIVE_CODE_REGISTRY_EQUALS_SELECTED_SOURCE'
      || value.selection?.identity_kind !== selected.identity_kind || value.selection?.identity_id !== selected.identity_id
      || m.schema !== 'gmi.theme_security_hierarchy_display/v1' || m.authority_ceiling !== 'display_only'
      || m.query?.kind !== selected.identity_kind || m.query?.id !== selected.identity_id || m.asof !== reading.asof
      || !stamp(m.knowledge_cutoff) || time(m.knowledge_cutoff) !== time(reading.built)
      || m.identity_basis !== 'LATEST_PUBLISHED_OWNER_REFERENCE' || m.identity_owner !== 'gmi.identity_resolution/v1'
      || m.historical_identity_claim !== false || m.knowledge_cutoff_applies_to !== 'GRAPH_PATHS_ONLY'
      || !STATES.includes(m.availability?.state) || !Array.isArray(m.bindings) || m.bindings.length > 64
      || !Array.isArray(s.reads) || s.reads.length < FILES.length || s.reads.length > FILES.length + 5) fail();
  const reads = [...s.reads].sort((a,b) => String(a.path).localeCompare(String(b.path)));
  const identitySources = decodeIdentitySources(reads);
  for (let i = 0; i < reads.length; i++) {
    if (!HEX.test(reads[i].sha256) || !Number.isSafeInteger(reads[i].bytes)
        || reads[i].bytes <= 0 || reads[i].bytes > 33554432) fail();
  }
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode([METHOD,...reads.map(r => r.path + ':' + r.sha256)].join('\n')));
  if (s.theme_source_manifest_hash !== 'sha256:' + [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2,'0')).join('')) fail();
  const ids = new Set(); let available = 0, pathCount = 0;
  for (const b of m.bindings) {
    const r = b.resolution;
    const masterGenerated = currentMasterClock(r?.master_generated_at);
    if (!r || !str(r.node_id) || !r.node_id.startsWith('co:') || ids.has(r.node_id) || r.security_id !== selected.identity_id
        || !(r.issuer_id === null || str(r.issuer_id) && r.issuer_id.startsWith('ISS:'))
        || !str(r.listing_key) || !Number.isSafeInteger(r.graph_identity_epoch) || r.graph_identity_epoch < 1 || !str(r.master_code_version)
        || !day(r.resolution_asof) || !stamp(r.computed_at) || !Number.isFinite(masterGenerated)
        || masterGenerated > Date.now() || time(r.computed_at) > Date.now() || Date.parse(r.resolution_asof) > Date.now()
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
  decodeTracking(m.etf_tracking,m,selected,identitySources);
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
    output.append(node('h3','','Curated ETF tracking references','自有 ETF 跟踪引用'));
    const tracking = v.theme_map.etf_tracking;
    if (!tracking.references.length) output.append(note('No ETF tracking reference is qualified for this reading. Coverage is incomplete.', '本次读数暂无合格的 ETF 跟踪引用。覆盖范围并不完整。'));
    for (const ref of tracking.references) {
      const basket = ref.membership.basket;
      const card=node('article','ox-card'); card.dataset.etfReference='';
      card.append(node('h4','',ref.symbol+' · tracking reference',ref.symbol+' · 跟踪引用'));
      const link=node('p','ox-note');link.append(words('Tracks curated basket: ','跟踪自有组合：'),label(basket));card.append(link);
      card.append(note('The selected company has a separately recorded membership in this basket. This tracking reference does not require a complete theme hierarchy.',
        '所选公司在该组合中另有成员记录。此跟踪引用不要求完整的主题层级。'));
      card.append(note('Effective from '+ref.clocks.valid_from+(ref.clocks.valid_to?' until '+ref.clocks.valid_to:'; no recorded end date')+'.',
        '生效起始：'+ref.clocks.valid_from+(ref.clocks.valid_to?'；结束：'+ref.clocks.valid_to:'；未记录结束日期')+'。'));
      if(ref.era==='reconstruction' || ref.date_provenance==='seed_constant'
          || ref.membership.era==='reconstruction' || ref.membership.date_provenance==='seed_constant') card.append(note(
        'Reconstructed relationship or seed date; not proof of an observation made on that date.', '此关系为重建记录或使用种子日期，不证明该日期当时已有观测。'));
      const identity = ref.security_identity;
      if (identity.status === 'available') card.append(note(
        'ETF identity qualified through current native aliases. The listing observation qualifies instrument type only; this is not a historical identity claim.',
        'ETF 身份已由当前原生别名确认。上市观测仅确认工具类型；这不代表历史身份。'));
      else { card.append(note('ETF identity unavailable.', 'ETF 身份不可用。')); card.append(note(...ETF_REASONS[identity.reason])); }
      const details=node('details','ox-detail');details.append(node('summary','','Tracking evidence and clocks','跟踪凭证与时间'));
      const list=node('dl','ox-company-fields ox-company-references');
      if (identity.status === 'available') {
        field(list,'ETF security','ETF 证券',identity.security_id); field(list,'ETF listing','ETF 上市标识',identity.listing_key);
        field(list,'Identity master generation','身份主表生成时刻',identity.master_generated_at);
        field(list,'Instrument type observation date','工具类型观测日期',identity.listing_observed_on);
        field(list,'Instrument type known at','工具类型获知时刻',identity.listing_known_at);
      }
      field(list,'Selected security','所选证券',ref.selected_security_id);field(list,'Graph edge','图谱边',ref.edge_id);
      field(list,'Company membership edge','公司成员关系边',ref.membership.edge_id);
      field(list,'Membership era / date provenance','成员关系时期 / 日期来源',
        ref.membership.era+' / '+ref.membership.date_provenance);
      field(list,'Membership effective / known / computed','成员关系生效 / 获知 / 计算',
        ref.membership.clocks.valid_from+' / '+ref.membership.clocks.belief_time+' / '+ref.membership.clocks.computed_at);
      for(const receipt of ref.membership.evidence) field(list,'Membership evidence / publication / computation','成员凭证 / 发布 / 计算',
        receipt.evidence_id+' / '+receipt.published_at+' / '+receipt.computed_at);
      field(list,'Evidence time','证据时间',ref.clocks.evidence_time);field(list,'Knowledge time','知识时间',ref.clocks.belief_time);
      field(list,'Computation','计算时刻',ref.clocks.computed_at);field(list,'Era','时期',ref.era);field(list,'Date provenance','日期来源',ref.date_provenance);
      for(const receipt of ref.evidence) field(list,'Evidence reference / publication / computation','凭证引用 / 发布 / 计算',
        receipt.evidence_id+' / '+receipt.published_at+' / '+receipt.computed_at);
      details.append(list);card.append(details);output.append(card);
    }
    output.append(note('These are curated graph tracking references. A qualified ETF identity does not prove that the fund holds the selected company. Holdings, weights and performance are unavailable. Coverage is incomplete; these paths confer no ranking, sizing or trading authority.',
      '这些是自有图谱跟踪引用。合格的 ETF 身份不证明基金持有所选公司。持仓、权重及表现不可用。覆盖范围并不完整；这些路径不赋予排名、仓位或交易权限。'));
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
  function receive(event){reading=null;clear();const r=event.detail;if(!r || !['oil_inflation_duration_derate','dollar_spike_em_multinational'].includes(r.chain) || !HASH.test(r.source_manifest_hash)
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
