/* Read the existing Radar publication. No detector, local storage or ranking. */
const LIMIT=262144,BUDGET=15000,HEX=/^[a-f0-9]{64}$/,ID=/^[A-Za-z0-9_.:-]{1,160}$/;
const AUTH=['can_gate','can_open_entry','can_originate','can_rank','can_size'];
function fail(){throw new Error('RADAR_RESEARCH_UNAVAILABLE');}
function instant(s){return typeof s==='string' && /(?:Z|[+-]\d\d:\d\d)$/.test(s) && Number.isFinite(Date.parse(s));}
function owner(){try{const id=window.MDXAuth?.user?.()?.id;return typeof id==='string' && id || null;}catch(_){return null;}}
function node(tag,cls,en,zh){const n=document.createElement(tag);if(cls)n.className=cls;if(en!==undefined)for(const [l,t] of [['en',en],['zh',zh]]){const s=document.createElement('span');s.className='l-'+l;s.textContent=t;n.append(s);}return n;}
function note(en,zh){return node('p','ox-note',en,zh);}
function field(dl,en,zh,value){const r=node('div','ox-company-field');r.append(node('dt','',en,zh));const d=node('dd');d.textContent=value;r.append(d);dl.append(r);}
function authority(v){return v && Object.keys(v).sort().join(',')===AUTH.join(',') && AUTH.every(k=>v[k]===false);}
function closed(v,fields){return !!v && typeof v==='object' && !Array.isArray(v) && Object.keys(v).sort().join(',')===[...fields].sort().join(',');}
function same(v,expected){return closed(v,Object.keys(expected)) && Object.keys(expected).every(k=>v[k]===expected[k]);}
function lineageHash(v){return typeof v==='string' && HEX.test(v);}
function decodeQuoteLineage(l,c,v){
  if(!closed(l,['schema','state','source_sha256','episode_binding','research_context_ref','composed_at','quote','observation','identity','origin','live_projection_eligible','rights_state','authority'])
      || l.schema!=='ontology_radar_quote_lineage.v1' || l.state!=='recorded_native_lineage' || !lineageHash(l.source_sha256)
      || !same(l.episode_binding,c.episode_binding) || !closed(l.research_context_ref,['case_ref','context_sha256'])
      || !same(l.research_context_ref.case_ref,c.case_ref) || l.research_context_ref.context_sha256!==c.published_context_sha256
      || l.live_projection_eligible!==false || l.rights_state!=='not_granted_by_provenance' || !authority(l.authority)
      || !instant(l.composed_at) || Date.parse(l.composed_at)<Date.parse(c.evidence_cutoff)
      || Date.parse(l.composed_at)>Date.parse(c.composed_at))fail();
  const q=l.quote,o=l.observation,i=l.identity,r=l.origin,fields={polygon:'tickers[].ticker',yahoo:'spark.result[].symbol'};
  if(!closed(q,['vendor','vendor_symbol','response_field','namespace_basis','provider_identity_attestation','vendor_timestamp','normalized_timestamp','recorded_at','native_basis','normalized_basis','point_sha256'])
      || typeof q.vendor!=='string' || !Object.hasOwn(fields,q.vendor) || typeof q.vendor_symbol!=='string' || !/^[A-Za-z0-9.^=:/_-]{1,64}$/.test(q.vendor_symbol)
      || q.vendor_symbol.toUpperCase()!==v.candidate.ticker || q.response_field!==fields[q.vendor]
      || q.namespace_basis!=='native_endpoint_parser' || q.provider_identity_attestation!=='not_available'
      || !['trade','minute','regular'].includes(q.native_basis) || q.normalized_basis!==null && q.normalized_basis!==q.native_basis
      || !instant(q.vendor_timestamp) || !instant(q.normalized_timestamp) || !instant(q.recorded_at)
      || Date.parse(q.vendor_timestamp)!==Date.parse(q.normalized_timestamp) || Date.parse(q.vendor_timestamp)>Date.parse(q.recorded_at)
      || Date.parse(q.recorded_at)>Date.parse(c.evidence_cutoff) || !lineageHash(q.point_sha256)
      || !closed(o,['sha256','recorded_at','interval_start','pack_hash']) || !lineageHash(o.sha256) || typeof o.pack_hash!=='string' || !/^[a-f0-9]{16}$/.test(o.pack_hash)
      || !instant(o.recorded_at) || !instant(o.interval_start) || Date.parse(o.interval_start)>=Date.parse(c.evidence_cutoff)
      || Date.parse(o.recorded_at)<Date.parse(q.recorded_at) || Date.parse(o.recorded_at)>Date.parse(l.composed_at)
      || !closed(i,['security_id','issuer_id','cik','snapshot_sha256']) || typeof i.security_id!=='string' || !/^SEC:[A-Z0-9_.:/^=-]{1,128}$/.test(i.security_id)
      || typeof i.issuer_id!=='string' || !/^ISS:[A-Z0-9_.:/^=-]{1,128}$/.test(i.issuer_id) || typeof i.cik!=='string' || i.cik!==c.research_subject.key || !lineageHash(i.snapshot_sha256)
      || !closed(r,['event_id','event_sha256','transition_sha256','receipt_scope','event_spool_recorded','transition_spool_recorded'])
      || typeof r.event_id!=='string' || !/^[a-f0-9]{16}$/.test(r.event_id) || !lineageHash(r.event_sha256) || !lineageHash(r.transition_sha256)
      || r.receipt_scope!=='ordinary_ledger_commit_not_spool_replay' || r.event_spool_recorded!==true || r.transition_spool_recorded!==true)fail();
}
export function decodeRadarResearch(v,selection){
  const s=v?.source;
  if(v?.schema!=='ontology_radar_research.v1' || v.selection!==selection || !authority(v.authority)
      || s?.artifact!=='entry_radar.json' || !HEX.test(s.snapshot_sha256) || !instant(s.asof) || !instant(s.captured_at)
      || Date.parse(s.asof)>Date.parse(s.captured_at) || Date.parse(s.captured_at)>Date.now()+1000
      || s.freshness_state!=='owner_reported_only' || typeof s.owner_health!=='string')fail();
  if(selection!==null && (v.candidate?.episode_id!==selection
      || typeof v.candidate.ticker!=='string' || !/^[A-Z0-9][A-Z0-9.-]{0,14}$/.test(v.candidate.ticker)
      || typeof v.candidate.detector_id!=='string' || !instant(v.candidate.candidate_at)
      || Date.parse(v.candidate.candidate_at)>Date.parse(s.asof)))fail();
  if(selection===null){
    if(v.state!=='candidate_list' || !Array.isArray(v.candidates) || v.candidates.length>64
        || !Number.isInteger(v.candidate_count) || v.candidates.length!==Math.min(v.candidate_count,64) || v.candidate_count>8192
        || v.truncated!==(v.candidate_count>64) || v.ordering!=='native_episode_id_not_priority')fail();
    const seen=new Set();
    for(const r of v.candidates){if(!ID.test(r.episode_id) || seen.has(r.episode_id) || typeof r.ticker!=='string'
        || !/^[A-Z0-9][A-Z0-9.-]{0,14}$/.test(r.ticker) || typeof r.detector_id!=='string'
        || !instant(r.candidate_at) || Date.parse(r.candidate_at)>Date.parse(s.asof)
        || !['published','retrospective_context','unqualified'].includes(r.research_state))fail();seen.add(r.episode_id);}
  }else if(v.state==='unqualified'){
    if(v.case!==null || v.reason!=='native_case_not_published')fail();
  }else{
    const c=v.case,b=c?.episode_binding,r=c?.case_ref;
    const retrospective=v.state==='published_context';
    if(!['published_case','published_context'].includes(v.state)
        || c?.schema!==(retrospective?'entry_radar.research_context/v1':'entry_radar.research_case/v1') || c.episode_id!==selection
        || b?.episode_id!==selection || !HEX.test(b.canonical_sha256) || !instant(b.candidate_at)
        || b.candidate_at!==v.candidate.candidate_at
        || Date.parse(b.candidate_at)>Date.parse(s.asof) || r?.schema!=='opportunity_case.research.v1'
        || !/^opc_[a-f0-9]{64}$/.test(r.case_id) || !HEX.test(r.sha256) || !authority(c.authority)
        || !Array.isArray(c.evidence_refs) || !c.evidence_refs.length || c.evidence_refs.length>64
        || !['partial','unavailable','abstained','complete'].includes(c.research_state)
        || !c.company_context || !c.transmission)fail();
    const seen=new Set();
    for(const ref of c.evidence_refs){if(typeof ref.reference_id!=='string' || seen.has(ref.reference_id)
        || typeof ref.owner_store!=='string' || ref.provenance?.pointer_only!==true || ref.provenance.body_embedded!==false
        || !Array.isArray(ref.clocks) || !ref.rights || !ref.freshness)fail();seen.add(ref.reference_id);}
    if(retrospective){
      const o=c.observation,n=c.native_earnings_identity,p=c.source_generation;
      if(c.projection_kind!=='retrospective_earnings_context' || c.live_projection_eligible!==false
          || c.candidate_quote_security_join!=='not_established' || c.research_subject?.key_type!=='cik'
          || !/^[0-9]{10}$/.test(c.research_subject.key) || typeof n?.event_id!=='string'
          || !/^[a-f0-9]{24,64}$/.test(n.generation_id) || p?.schema!=='earnings.generation_pointer.v1'
          || p.generation_id!==n.generation_id || !HEX.test(p.manifest_sha256) || !HEX.test(c.published_context_sha256)
          || !instant(p.captured_at) || Date.parse(p.captured_at)>Date.parse(b.candidate_at)
          || c.evidence_cutoff!==b.candidate_at || !instant(c.composed_at)
          || Date.parse(c.composed_at)<Date.parse(c.evidence_cutoff) || Date.parse(c.composed_at)>Date.parse(s.captured_at)
          || c.research_state!=='partial' || c.company_context.state!=='partial' || c.transmission.state!=='unavailable'
          || o?.metric!=='revenue' || typeof o.value!=='number' || !Number.isFinite(o.value) || o.value<0 || o.value>1e15
          || !['USD','usd_millions'].includes(o.unit) || !['reported','gaap'].includes(o.basis)
          || typeof o.period!=='string' || !/^(?:\d{4}Q[1-4]|\d{4}FY|\d{4}-\d{2}-\d{2})$/.test(o.period)
          || o.lineage_state!=='owner_byte_replay_receipt' || o.locally_replayed!==false)fail();
      if(Object.hasOwn(c,'quote_lineage'))decodeQuoteLineage(c.quote_lineage,c,v);
    }else if(Object.hasOwn(c,'quote_lineage'))fail();
  }
  return v;
}
export function mountRadarResearch(root){
  if(!root)return null;
  const output=root.querySelector('[data-radar-result]'),read=root.querySelector('[data-radar-read]'),clearButton=root.querySelector('[data-radar-clear]');
  let epoch=0,operation=null,disposed=false,subscription=null,canonicalOwner=owner();
  const copy={idle:['Read the existing published candidates to inspect their research evidence.','读取现有已发布候选，查看其研究证据。'],loading:['Reading the native Radar publication…','正在读取原生雷达发布内容…'],signed_out:['Sign in to read private candidate research.','请登录以读取私有候选研究。'],forbidden:['This account does not include private research access.','此账户未包含私有研究权限。'],unavailable:['The published reading is unavailable. No candidate or case is substituted.','已发布读数暂不可用。不会替换候选或案例。'],not_found:['This candidate is no longer in the published candidate set. Read the list again.','此候选已不在发布的候选集合中，请重新读取列表。']};
  function state(s){output.replaceChildren(note(...copy[s]));output.dataset.state=s;output.setAttribute('aria-busy',String(s==='loading'));read.disabled=s==='loading';}
  function cancel(reader){try{void Promise.resolve(reader.cancel()).catch(()=>{});}catch(_){}}
  function clear(){epoch++;if(operation){const op=operation;operation=null;op.abort.abort();if(op.reader)cancel(op.reader);clearTimeout(op.timer);op.reject(new Error('CANCELLED'));}state('idle');}
  function auth(e){canonicalOwner=typeof e.detail?.user?.id==='string'?e.detail.user.id:null;clear();}
  function check(op){if(disposed || epoch!==op.id || document.hidden || op.abort.signal.aborted || performance.now()>=op.deadline || owner()!==op.owner || canonicalOwner!==op.owner)fail();}
  async function checked(op,p){const value=await p;check(op);return value;}
  const authentication=Promise.resolve().then(async()=>{const sdk=await window.MDXAuth?.client?.();if(disposed || typeof sdk?.auth?.onAuthStateChange!=='function')fail();subscription=sdk.auth.onAuthStateChange(clear)?.data?.subscription;if(typeof subscription?.unsubscribe!=='function')fail();return sdk;});void authentication.catch(()=>{});
  async function session(op,prior){const sdk=await checked(op,authentication),r=await checked(op,sdk.auth.getSession()),s=r?.data?.session;if(r?.error || s?.user?.id!==op.owner || typeof s?.access_token!=='string' || !s.access_token || s.access_token.length>32768 || prior && prior!==s.access_token)fail();return s.access_token;}
  async function body(op,response){const h=response.headers,parts=k=>(h.get(k)||'').toLowerCase().split(',').map(x=>x.trim());if(response.redirected || !/^application\/json(?:\s*;|$)/i.test(h.get('Content-Type')||'') || !parts('Cache-Control').includes('private') || !parts('Cache-Control').includes('no-store') || !parts('Vary').includes('authorization') || !parts('Vary').includes('cookie'))fail();const length=h.get('Content-Length');if(length!==null && (!/^\d+$/.test(length)||Number(length)>LIMIT))fail();const reader=response.body?.getReader();if(!reader)fail();op.reader=reader;let size=0,complete=false;const decoder=new TextDecoder('utf-8',{fatal:true}),pieces=[];try{for(;;){const c=await checked(op,reader.read());if(c.done)break;size+=c.value.byteLength;if(size>LIMIT)fail();pieces.push(decoder.decode(c.value,{stream:true}));}pieces.push(decoder.decode());check(op);const value=JSON.parse(pieces.join(''));complete=true;return value;}finally{if(!complete)cancel(reader);if(op.reader===reader)op.reader=null;try{reader.releaseLock();}catch(_){}}}
  function render(v){
    output.replaceChildren();output.dataset.state='ready';output.setAttribute('aria-busy','false');read.disabled=false;
    const source=node('dl','ox-company-fields');
    field(source,'Radar pass time','雷达批次时间',v.source.asof);
    field(source,'Publication status','发布状态',v.source.owner_health);
    output.append(source,note('This is the published snapshot at the displayed time. A read does not establish current market freshness or grant trading authority.','这是所示时间的发布快照。读取行为不证明市场数据的当前新鲜度，也不赋予交易权限。'));
    if(v.state==='candidate_list'){
      output.append(note(v.candidate_count+' native candidates; listed by episode identity, not research priority.',v.candidate_count+' 个原生候选，按事件身份列出，不表示研究优先级。'));
      if(v.truncated)output.append(note('Showing the first 64 native identities.','显示前 64 个原生身份。'));
      const list=node('ul','ox-exposure-members');
      for(const r of v.candidates){
        const li=node('li');li.append(node('span','',r.ticker+' · '+r.detector_id,r.ticker+' · '+r.detector_id));
        const labels=r.research_state==='published'?['Inspect published case','查看已发布案例']:r.research_state==='retrospective_context'?['Read earnings context','读取财报背景']:['Check research availability','检查研究可用性'];
        const button=node('button','ox-cta secondary',...labels);button.type='button';button.dataset.episode=r.episode_id;
        button.addEventListener('click',()=>void inspect(r.episode_id));li.append(button);list.append(li);
      }
      output.append(list);return;
    }
    if(v.state==='unqualified'){
      output.append(note('No qualified research case or earnings context has been published for this exact candidate. Its native lifecycle is unchanged.','此确切候选尚未发布合格研究案例或财报背景。其原生生命周期保持不变。'));return;
    }
    const c=v.case,retrospective=v.state==='published_context',facts=node('dl','ox-company-fields');
    field(facts,'Candidate','候选',v.candidate.ticker+' · '+v.candidate.detector_id);
    if(retrospective){
      const o=c.observation,amount=o.value.toLocaleString('en-US',{maximumFractionDigits:10});
      output.append(node('h3','','Reported earnings context','已披露财报背景'));
      const revenue=node('div','ox-company-field');revenue.append(node('dt','','Reported revenue','已披露营收'));
      revenue.append(node('dd','',amount+(o.unit==='usd_millions'?' million USD':' USD'),amount+(o.unit==='usd_millions'?' 百万美元':' 美元')));facts.append(revenue);
      field(facts,'Fiscal period','财务期间',o.period);
      const basis=node('div','ox-company-field');basis.append(node('dt','','Reporting basis','披露口径'),node('dd','',o.basis==='gaap'?'GAAP':'Reported',o.basis==='gaap'?'GAAP':'已披露'));facts.append(basis);
      field(facts,'Evidence cutoff','证据截止时间',c.evidence_cutoff);field(facts,'Context composed','背景编制时间',c.composed_at);
      output.append(facts);
      output.append(c.quote_lineage
        ? note('Retrospective issuer context only. Radar retained a quote-to-security lineage for this observation. Provider identity is not authenticated here, and earnings causation and trading eligibility remain unestablished.','仅为回溯性发行人背景。雷达保留了此观察的报价至证券来源关联。此处未认证提供方身份，也未确立财报因果关系或交易资格。')
        : note('Retrospective issuer context only. The retained research identity does not establish which security supplied this candidate’s quote, or whether earnings caused the move.','仅为回溯性发行人背景。保留的研究身份无法证明哪只证券提供了此候选的报价，也不证明财报导致了该走势。'));
      output.append(note('Revenue retains the owner’s value, units and fiscal period. Surprise, transmission and trading eligibility are not established. Source-span verification is an owner receipt, not a new source-body replay.','营收保留所有者的数值、单位及财务期间。尚未确立超预期、传导或交易资格。来源片段验证为所有者凭据，并非重新读取来源正文。'));
    }else{
      output.append(node('h3','','Published research case','已发布研究案例'));
      field(facts,'Research state','研究状态',c.research_state);field(facts,'Candidate interval end','候选区间结束',c.episode_binding.candidate_at);
      field(facts,'Company context','公司背景',c.company_context.state);field(facts,'Transmission context','传导背景',c.transmission.state);output.append(facts);
    }
    const detail=node('details','ox-detail');detail.append(node('summary','','Evidence and owner clocks','证据与所有者时钟'));
    const identity=node('dl','ox-company-fields ox-company-references');field(identity,'Case identity','案例身份',c.case_ref.case_id);field(identity,'Case content digest','案例内容摘要',c.case_ref.sha256);
    if(retrospective){
      field(identity,'Issuer CIK','发行人 CIK',c.research_subject.key);field(identity,'Earnings event','财报事件',c.native_earnings_identity.event_id);
      field(identity,'Source generation','来源版本',c.native_earnings_identity.generation_id);field(identity,'Generation first retained','首次保留版本时间',c.source_generation.captured_at);
      field(identity,'Owner fact location','所有者事实位置',c.observation.field_path);field(identity,'Source document','来源文档',c.observation.document_id);
      if(c.quote_lineage){
        const l=c.quote_lineage,q=l.quote;
        field(identity,'Recorded quote symbol','记录的报价代码',q.vendor+' · '+q.vendor_symbol);
        field(identity,'Native security identity','原生证券身份',l.identity.security_id);
        field(identity,'Vendor quote time','提供方报价时间',q.vendor_timestamp);
        field(identity,'Quote admitted by Radar','雷达接纳报价时间',q.recorded_at);
        field(identity,'Observation frozen','观察记录冻结时间',l.observation.recorded_at);
        field(identity,'Originating event','原始事件',l.origin.event_id);
        detail.append(note('The provider namespace is a native-parser declaration. Original ledger commit receipts are recorded; spool content was not re-read. This lineage grants no additional rights or live eligibility.','提供方命名空间为原生解析器声明。已记录原始账本提交凭据，未重新读取缓冲内容。此来源关联不赋予额外权利或实时资格。'));
      }
    }
    detail.append(identity);
    for(const ref of c.evidence_refs){
      const dl=node('dl','ox-company-fields ox-company-references');field(dl,'Native owner','原生所有者',ref.owner_store);field(dl,'Evidence reference','证据引用',ref.reference_id);field(dl,'Owner pointer','所有者指针',ref.provenance.pointer);
      for(const clock of ref.clocks)field(dl,String(clock.class),String(clock.class),clock.value_state==='known'?String(clock.value):'unknown');
      field(dl,'Rights state','权利状态',ref.rights.state);field(dl,'Freshness state','新鲜度状态',ref.freshness.state);detail.append(dl);
    }
    output.append(detail);
  }
  async function inspect(selection){clear();const id=owner();if(!id || id!==canonicalOwner){state('signed_out');return;}const op={id:epoch,owner:id,abort:new AbortController(),deadline:performance.now()+BUDGET,reader:null};const cancellation=new Promise((_,reject)=>{op.reject=reject;});operation=op;op.timer=setTimeout(()=>{op.abort.abort();if(op.reader)cancel(op.reader);op.reject(new Error('TIMEOUT'));},BUDGET);state('loading');try{await Promise.race([(async()=>{const token=await session(op);const response=await checked(op,fetch('/api/ontology/explorer/radar-research/v1',{method:'POST',credentials:'same-origin',cache:'no-store',redirect:'error',signal:op.abort.signal,headers:{Accept:'application/json','Content-Type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify({schema:'ontology_radar_research_request.v1',episode_id:selection})}));const value=await body(op,response);await session(op,token);if(response.status!==200){check(op);state(response.status===401?'signed_out':response.status===403?'forbidden':response.status===404?'not_found':'unavailable');return;}const decoded=decodeRadarResearch(value,selection);await session(op,token);check(op);render(decoded);})(),cancellation]);}catch(_){if(!disposed && epoch===op.id)state(owner()!==op.owner?'signed_out':'unavailable');}finally{op.abort.abort();if(op.reader)cancel(op.reader);clearTimeout(op.timer);if(operation===op)operation=null;}}
  const load=()=>void inspect(null),hidden=()=>{if(document.hidden)clear();};read.addEventListener('click',load);clearButton.addEventListener('click',clear);window.addEventListener('mdx-auth',auth);window.addEventListener('pagehide',clear);document.addEventListener('visibilitychange',hidden);state('idle');return{dispose(){disposed=true;clear();subscription?.unsubscribe();read.removeEventListener('click',load);clearButton.removeEventListener('click',clear);window.removeEventListener('mdx-auth',auth);window.removeEventListener('pagehide',clear);document.removeEventListener('visibilitychange',hidden);}};
}
mountRadarResearch(document.getElementById('ox-radar-research'));
