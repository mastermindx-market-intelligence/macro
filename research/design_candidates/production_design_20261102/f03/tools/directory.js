'use strict';
const data=JSON.parse(document.getElementById('f03-data').textContent);
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let lang='en';
const tr=(en,zh)=>lang==='zh'?zh:en;
const source=s=>`<span lang="${/[\u3400-\u9fff]/.test(String(s))?'zh-CN':'en'}">${esc(s)}</span>`;
const views=['assignments','references','routes','changes'];
const sessionById=id=>data.sessions.find(s=>s.id===id);
const pageKey=p=>p.paper_file_id+'/'+p.paper_page_id;
const boardKey=b=>'board-'+b.paper_file_id+'-'+b.paper_page_id+'-'+b.artboard_id;
const observationMap=new Map((data.page_observations||[]).map(p=>[p.file_id+'/'+p.page_id,p]));
const observationFor=p=>observationMap.get(pageKey(p));
const observedBoards=(data.page_observations||[]).flatMap(p=>p.artboards.map(b=>({
 paper_file_id:p.file_id,paper_page_id:p.page_id,artboard_id:b.id,name:b.name,
 width:b.width,height:b.height,child_count:b.childCount,product_owner:null,
 page_custodian:'F03',observed_role_labels:[],evidence_kind:'later_structure',observed_at:p.completed_at_utc
})));
const searchableBoards=[...data.artboards,...observedBoards];
const boardMap=new Map();
for(const b of searchableBoards){const k=b.paper_file_id+'/'+b.paper_page_id;if(!boardMap.has(k))boardMap.set(k,[]);boardMap.get(k).push(b);}
const boardsFor=p=>boardMap.get(pageKey(p))||[];
const refsFor=id=>data.pages.filter(p=>p.page_custodian===id||p.artboard_owners.includes(id));
const boardText=b=>[b.artboard_id,b.paper_file_id+'/'+b.paper_page_id+'/'+b.artboard_id,b.name,b.product_owner,b.page_custodian,...b.observed_role_labels].join(' ').toLowerCase();
const refText=p=>[p.name,p.file_name,p.paper_file_id,p.paper_page_id,pageKey(p),p.url,p.page_custodian,p.content_owner,...p.artboard_owners,p.role,observationFor(p)?'structural observation 结构观察':'',observationFor(p)?.page_name||'',observationFor(p)?.file_name||'',...boardsFor(p).map(boardText)].join(' ').toLowerCase();
const searchText=s=>[s.id,s.title,s.title_zh,s.job,...s.aliases,...s.proposed_files,...s.canonical_registry_ids,...s.delegated_registry_ids,...s.source_deltas,s.source_contract||'',s.candidate_ref||'',JSON.stringify(s.return_observation||{}),...refsFor(s.id).map(refText),...data.routes.filter(r=>r.primary_session===s.id||r.delegated_slices.includes(s.id)).map(r=>r.route)].join(' ').toLowerCase();
const title=s=>lang==='zh'?s.title_zh:s.title;
const role=r=>({candidate_unqualified:tr('Candidate / unqualified','候选／未认定'),held:tr('Held','保留待审'),historical:tr('Historical','历史'),redirect:tr('Redirect','迁移指引'),rejected:tr('Rejected','已否决'),source_only:tr('Source only','仅源证据'),specification:tr('Specification','规格参考'),reference_unqualified:tr('Reference / unqualified','参考／未认定'),unexpanded:tr('Not expanded','未展开检查'),live_delta_unqualified:tr('New observation / unqualified','新观察／未认定'),qa_only:tr('QA only','仅测试')})[r]||r;
function state(){const p=new URLSearchParams(location.hash.slice(1));return {view:views.includes(p.get('view'))?p.get('view'):'assignments',q:p.get('q')||'',owner:p.get('owner')||'',session:p.get('session')||'',board:p.get('board')||'',page:p.get('page')||'',inventory:p.get('inventory')||''};}
function hash(st){const p=new URLSearchParams();p.set('view',st.view||'assignments');for(const k of ['q','owner','session','page','board','inventory'])if(st[k])p.set(k,st[k]);return '#'+p;}
function entry(id,st=state(),b=null){return hash({...st,session:id,page:b?b.paper_file_id+'/'+b.paper_page_id:'',board:b?b.artboard_id:''});}
function ownerLink(id,label=''){return `<a href="${esc(entry(id))}">${label?esc(label)+' ':''}${esc(id)}</a>`;}
function matchedBoards(s,q){return q?searchableBoards.filter(b=>(b.product_owner===s.id||b.page_custodian===s.id)&&boardText(b).includes(q)):[];}
function empty(st){return `<div class="empty"><h2>${tr('No matches in this view','此视图没有匹配项')}</h2><p>${tr('Search scope is shown above. A missing match does not mean a resource was removed.','搜索范围见上方。无匹配项不代表资源已删除。')}</p><p><a href="${esc(hash({...st,view:'assignments',session:''}))}">${tr('Search assignments and references','搜索任务与参考')} →</a> · <a href="${esc(hash({...st,view:'routes',session:''}))}">${tr('Search canonical routes and deltas','搜索标准路由与增量')} →</a> · <a href="inventory.html#q=${encodeURIComponent(st.q)}">${tr('Search generated documents','搜索生成文档')} →</a></p><button type="button" data-clear>${tr('Clear filters','清除筛选')}</button></div>`;}
function syncTheme(){const dark=document.documentElement.dataset.theme==='dark';$('theme').textContent=tr(dark?'Light':'Dark',dark?'浅色':'深色');$('theme').setAttribute('aria-label',tr(dark?'Switch to light theme':'Switch to dark theme',dark?'切换至浅色主题':'切换至深色主题'));}
function effectWarning(meta=data.metadata){
 const ids=meta.directory.paper_unresolved_operation_ids||[];
 if(!ids.length)return '';
 return `<strong>${tr('F03 draft additions: Paper outcome unconfirmed','F03 草稿补充：Paper 操作结果尚未确认')}</strong><p>${tr('Previously recorded directory work is retained. Reconcile this exact original-carrier operation before more Paper edits; do not repeat or replace it. This is a saved evidence snapshot, not a live service monitor.','先前已记录的目录工作保留。继续编辑 Paper 前，须在原通道核实此精确操作；勿重复或替换。本提示来自已保存证据，并非实时服务监控。')}</p><details><summary>${tr('Exact pending operation and evidence','精确待核实操作与证据')}</summary>${ids.map(id=>`<p><code>${esc(id)}</code></p>`).join('')}<p>${tr('Recorded','记录时间')}: <time datetime="${esc(meta.native_effect_observed_at)}">${esc(meta.native_effect_observed_at)}</time></p><a href="paper/native-progress.json">${tr('Open original native-effect ledger','打开原生操作记录')} ↗</a></details>`;
}
function paintChrome(st){
 document.documentElement.lang=lang==='zh'?'zh-CN':'en';
 const warning=effectWarning();$('effect-warning').innerHTML=warning;$('effect-warning').hidden=!warning;
 const labels=tr(['Assignments','Paper references','Route coverage','Changes & gaps'],['任务目录','Paper 参考','路由覆盖','变更与缺口']);
 $('nav').innerHTML=views.map((v,i)=>`<a href="${esc(hash({...st,view:v,session:'',page:'',board:''}))}" ${st.view===v&&!st.session?'aria-current="page"':''}>${labels[i]}</a>`).join('');
 $('title').innerHTML=tr('Find the right design.<br>Keep its history.','找到正确设计。<br>保留完整历史。');
 $('subtitle').textContent=tr('Choose a product family. Find exact references, owners and contract status together.','选择产品类别，同时查看精确参考、负责人和合同状态。');
 $('status').textContent=tr('Directory refinements observed · Cross-file organization pending · No new approvals','目录改进已观察 · 跨文件整理待执行 · 无新增批准');
 const prompts={assignments:tr('Search product, route, Paper ID or assignment','搜索产品、路由、Paper ID 或任务'),references:tr('Search Paper titles, file/page/artboard IDs or owners','搜索 Paper 名称、文件／页面／画板 ID 或负责人'),routes:tr('Search canonical routes, source deltas or registry IDs','搜索标准路由、源增量或登记 ID'),changes:tr('Search observed changes, gaps or assignments','搜索观察到的变更、缺口或任务')};
 $('search').placeholder=prompts[st.view];$('search').setAttribute('aria-label',prompts[st.view]);$('search').value=st.q;
 $('clear').textContent=tr('Clear filters','清除筛选');$('locale').textContent=lang==='en'?'中文':'EN';$('locale').setAttribute('aria-label',tr('Switch to Chinese','切换至英语'));
 $('owner').setAttribute('aria-label',tr('Filter by assignment','按任务筛选'));
 $('owner').innerHTML=`<option value="">${tr('All assignments','全部任务')}</option>`+data.sessions.map(s=>`<option value="${s.id}" ${st.owner===s.id?'selected':''}>${s.id} · ${esc(title(s))}</option>`).join('');
 $('metrics').innerHTML=[[36,tr('assignments','任务')],[348,tr('canonical records','标准记录')],[299,tr('baseline pages','基线页面')],[2,tr('additional observations','新增观察')]].map(([n,l])=>`<div class="metric"><strong>${n}</strong><span>${l}</span></div>`).join('');
 $('overview').hidden=!!st.session;$('navlabel').textContent=tr('Programme navigation','计划导航');$('eyebrow').textContent=tr('Production design programme','生产设计计划');$('skip').textContent=tr('Skip to directory','跳至目录');$('snapshot').textContent=tr('Baseline · 2–3 Nov 2026 · Later returns separately observed','基线 · 2026 年 11 月 2–3 日 · 后续返回单独记录');
 $('provenance-label').textContent=tr('Source titles retain their original language.','源名称保留原始语言。');$('md-link').textContent=tr('Text directory ↗','文字目录 ↗');$('contract-link').textContent=tr('F03 contract ↗','F03 合同 ↗');$('inventory-link').textContent=tr('Generated document index ↗','生成文档索引 ↗');$('inventory-link').href='inventory.html';$('return-link').textContent=tr('F03 evidence and return','F03 证据与交付');$('footer-note').textContent=tr('Titles and board counts identify evidence. They do not establish approval, implementation or release.','名称和画板数量用于定位证据，不代表批准、实现或发布。');syncTheme();
}
function boardMatch(b,st){return `<p class="row-sub"><a href="${esc(entry(b.product_owner||b.page_custodian,st,b))}"><code>${esc(b.artboard_id)}</code> · ${source(b.name)}</a> ${b.observed_role_labels.map(r=>`<span class="pill">${role(r)}</span>`).join(' ')}${b.evidence_kind==='later_structure'?` <span class="pill">${tr('Later structural observation','后续结构观察')}</span>`:''}</p>`;}
function pageRole(p){return observationFor(p)&&p.role==='unexpanded'?tr('Baseline listed only','基线仅列出'):role(p.role);}
function structuralEvidence(p){
 const o=observationFor(p);if(!o)return '';
 const evidence=data.metadata.structural_observations;
 return `<div class="reference-return"><p class="row-sub"><span class="pill">${tr('Structural observation','结构观察')}</span> ${o.artboard_count} ${tr('artboards observed','个已观察画板')} · <time datetime="${esc(o.completed_at_utc)}">${esc(o.completed_at_utc)}</time></p>
 <p class="count">${tr('Baseline retained. Product owner, full-content comparison and safe disposal are not established.','基线保留。产品负责人、完整内容比较及安全处置尚未确立。')}</p>
 ${o.initial_returned_artboards<o.artboard_count?`<p class="count">${tr('Initial list was capped; exact root and individual board reads completed the identities.','初始列表有数量上限；已通过精确根节点及逐个画板读取补全身份。')}</p>`:''}
 ${o.warnings.length?`<p class="ownership">${tr('Paper reported a file-size/data-loss warning. No edit was attempted.','Paper 报告文件大小／数据丢失警告。未尝试编辑。')}</p>`:''}
 <details><summary>${tr('Observed names, evidence and limits','观察名称、证据与限制')}</summary><p>${source(o.file_name)} / ${source(o.page_name)}</p><p>${source(evidence.qualification)}</p>${o.warnings.map(w=>`<p>${source(w)}</p>`).join('')}<a href="${esc(evidence.evidence)}">${tr('Exact read evidence','精确读取证据')} ↗</a></details></div>`;
}
function boardOwner(b){return b.product_owner?ownerLink(b.product_owner):`${tr('Not established','尚未确立')} · ${tr('Organization steward','整理负责人')}: ${ownerLink(b.page_custodian)}`;}
function card(s,st,q){const hits=matchedBoards(s,q);return `<article class="family"><a href="${esc(entry(s.id,st,hits.length===1?hits[0]:null))}"><div class="family-head"><span class="eyebrow">${s.id}</span><span aria-hidden="true">↗</span></div><h3>${esc(title(s))}</h3></a><p>${source(s.job)}</p>${s.aliases.length?`<p class="count">${source(s.aliases.join(' · '))}</p>`:''}${hits.slice(0,2).map(b=>boardMatch(b,st)).join('')}${hits.length>2?`<p class="count">${hits.length} ${tr('matching boards; open assignment to inspect','个匹配画板；打开任务查看')}</p>`:''}<div class="meta"><span>${s.canonical_registry_ids.length} ${tr('canonical','标准记录')} · ${s.paper_refs.length} ${tr('baseline page refs','基线参考页面')}</span><span>${tr('Approval not established','批准尚未确立')}</span></div></article>`;}
function assignmentView(st,q){const list=data.sessions.filter(s=>(!st.owner||s.id===st.owner)&&(!q||searchText(s).includes(q)));const order=['10 Workspaces','20 Markets','30 Research','40 Personal','50 Public','60 Internal','01 Foundations','00 Programme'];const groups=[...new Set(list.map(s=>s.folder))].sort((a,b)=>order.indexOf(a)-order.indexOf(b));const shortcuts=!q&&!st.owner?`<p class="quicklinks">${tr('Start with a job:','从任务开始：')} <a href="${entry('D07',st)}">${tr('Company','公司')}</a> · <a href="${entry('D08',st)}">${tr('Options','期权')}</a> · <a href="${entry('D04',st)}">${tr('Heatmaps','热力图')}</a> · <a href="${entry('D07',{...st,q:'Returns'})}">${tr('Returns Calendar','回报日历')}</a></p>`:'';return {n:list.length,html:shortcuts+groups.map(g=>`<div class="group-title"><h2>${source(g)}</h2><span class="count">${list.filter(s=>s.folder===g).length}</span></div><div class="grid">${list.filter(s=>s.folder===g).map(s=>card(s,st,q)).join('')}</div>`).join('')||empty(st)};}
function ownership(p){let msg=p.role==='unexpanded'?tr('Organization steward F03 · product owner unknown','整理负责人 F03 · 产品负责人未知'):tr('Page custodian','页面保管')+' '+p.page_custodian;return `<p class="row-sub">${esc(msg)} · ${tr('Writer unverified','写入者未验证')}</p>${p.artboard_owners.length?`<p class="row-sub">${tr('Board product owners','画板产品负责人')}: ${p.artboard_owners.map(id=>ownerLink(id)).join(', ')}</p>`:''}${!p.listed_in_package?`<p class="ownership">${source(p.ownership_basis)}</p>`:''}`;}
function warnings(p){return p.board_role_warnings.length?`<p class="ownership">${tr('Contains board labels','包含画板标签')}: ${p.board_role_warnings.map(role).join(' · ')}. ${tr('Title evidence; inspect conditions.','名称证据；请查看条件。')}</p>`:'';}
function paperIdentity(url){
 const m=/^https:\/\/app\.paper\.design\/file\/([A-Z0-9]+)\/(p-[A-Za-z0-9-]+)$/.exec(String(url||''));
 return m?{fileId:m[1],pageId:m[2],key:m[1]+'/'+m[2]}:null;
}
function referenceRows(sessions=data.sessions,pages=data.pages){
 // This is a read-only view over existing evidence, not a new registry or census.
 const rows=new Map(pages.map(page=>[pageKey(page),{key:pageKey(page),page,url:page.url,claims:[]} ]));
 for(const s of sessions){
  const obs=s.return_observation;if(!obs)continue;
  const add=(kind,url,fileId,pageId,boardId=null)=>{
   const id=paperIdentity(url);if(!id)return;
   if(kind!=='retained'&&(id.fileId!==fileId||id.pageId!==pageId))return;
   if(!rows.has(id.key))rows.set(id.key,{key:id.key,page:null,url,claims:[]});
   const row=rows.get(id.key);
   if(row.claims.some(c=>c.owner===s.id&&c.kind===kind&&c.board_id===boardId))return;
   row.claims.push({owner:s.id,kind,url,file_id:id.fileId,page_id:id.pageId,board_id:boardId,
    source_head:obs.source_head,observed_at:obs.observed_at_utc,qualification:obs.qualification,
    status:s.status,source_contract:s.source_contract,source_contract_label:s.source_contract_label});
  };
  add('candidate',s.candidate_ref,obs.candidate_file_id,obs.candidate_page_id);
  add('readme',obs.readme_url,obs.readme_file_id,obs.readme_page_id,obs.readme_board_id);
  add('retained',obs.retained_reference_url);
 }
 return [...rows.values()];
}
function returnKind(kind){return ({candidate:tr('Observed candidate','已观察候选'),readme:tr('Read me','设计说明'),retained:tr('Retained original reference','保留的原参考')})[kind];}
function returnedRefText(c){
 const s=sessionById(c.owner);
 return [c.owner,s?.title,s?.title_zh,c.kind,returnKind(c.kind),c.url,c.file_id+'/'+c.page_id,c.board_id,
  c.source_head,c.observed_at,c.status,c.qualification,c.source_contract].join(' ').toLowerCase();
}
function referenceReturnEvidence(claims,st){
 if(!claims.length)return '';
 const owners=[...new Set(claims.map(c=>c.owner))];
 const labels=claims.map(c=>`<span class="pill">${returnKind(c.kind)}</span> ${ownerLink(c.owner)}${c.board_id?` · <code>${esc(c.board_id)}</code>`:''}`).join(' · ');
 const sources=owners.map(owner=>claims.find(c=>c.owner===owner));
 return `<div class="reference-return"><p class="row-sub">${labels}</p><p class="count">${tr('Approval not established · Return evidence is separate from the frozen census.','批准尚未确立 · 返回证据与冻结清单分开记录。')}</p>
 <p class="reference-contracts">${sources.map(c=>evidenceLink(c.source_contract,c.owner+' · '+tr('Source contract','源合同'))).join(' · ')}</p>
 <details><summary>${tr('Source pins, observation times and conditions','来源版本、观察时间与条件')}</summary>${sources.map(c=>`<p>${ownerLink(c.owner)} · <time datetime="${esc(c.observed_at)}">${esc(c.observed_at)}</time><br><code>${esc(c.source_head)}</code></p><p>${source(c.status)}</p><p>${source(c.qualification)}</p>`).join('')}</details></div>`;
}
function referenceView(st,q){
 const list=referenceRows().filter(r=>{
  const p=r.page;
  const owned=!st.owner||(p&&(p.page_custodian===st.owner||p.artboard_owners.includes(st.owner)))||r.claims.some(c=>c.owner===st.owner);
  return owned&&(!q||(p&&refText(p).includes(q))||r.claims.some(c=>returnedRefText(c).includes(q)));
 }).sort((a,b)=>Number(!!b.claims.length)-Number(!!a.claims.length));
 if(!list.length)return {n:0,html:empty(st)};
 return {n:list.length,html:`<p class="count">${tr('Exact pages from the frozen baseline and separately observed returns. Each page appears once; distinct candidate, Read me and retained-reference roles remain explicit.','合并展示冻结基线与单独观察的返回证据。每个页面仅显示一次；候选、设计说明和保留参考的角色仍分别标明。')}</p>`+list.map(r=>{
  const p=r.page,first=r.claims[0],owners=[...new Set(r.claims.map(c=>c.owner))];
  const name=p?source(p.name):owners.map(id=>source(title(sessionById(id)))).join(' · ');
  const fileName=p?.file_name||data.pages.find(x=>x.paper_file_id===first?.file_id)?.file_name||first?.file_id;
  const links=[...new Set([...(p?[p.page_custodian]:[]),...owners])];
  return `<article class="row reference-row"><div class="row-main"><span class="pill">${p?pageRole(p):tr('Returned page / unqualified','返回页面／未认定')}</span><a class="row-title" href="${esc(r.url)}" target="_blank" rel="noopener">${name} ↗</a><p class="row-sub">${source(fileName)} · <code>${esc(r.key)}</code></p>${p?ownership(p)+warnings(p)+structuralEvidence(p):`<p class="row-sub">${tr('Return owner, not a current writer claim','返回负责人，不构成当前写入权证明')}: ${owners.map(id=>ownerLink(id)).join(', ')}</p>`}${p&&q?boardsFor(p).filter(b=>boardText(b).includes(q)).slice(0,8).map(b=>boardMatch(b,st)).join(''):''}${referenceReturnEvidence(r.claims,st)}</div><div class="row-side">${links.map(id=>`<a href="${esc(entry(id,st))}">${esc(id)} · ${tr('History & contract','历史与合同')} →</a>`).join('')}</div></article>`;
 }).join('')};
}
function routeTable(rows,st){return `<div class="table-wrap" tabindex="0" aria-label="${tr('Canonical route responsibility','标准路由职责')}"><table><thead><tr><th>${tr('Registry ID / route','登记 ID／路由')}</th><th>${tr('Design responsibilities','设计职责')}</th><th>${tr('Source / inventory','来源／清单')}</th><th>${tr('Access / payload','访问／数据权限')}</th></tr></thead><tbody>${rows.map(r=>`<tr><td><code>${esc(r.canonical_registry_id)}</code><br><strong>${esc(r.route)}</strong><br><span class="muted">${esc(r.repo)} · ${source(r.route_kind)}</span></td><td>${tr('Primary / integration','主责／整合')}: ${ownerLink(r.primary_session)}${r.delegated_slices.length?'<br>'+tr('Design slices','设计分工')+': '+r.delegated_slices.map(id=>ownerLink(id)).join(', '):''}<br><span class="muted">${tr('Registry source owner','登记源负责人')}: ${source(r.registry_source_owner)}</span></td><td><code>${esc(r.source_template)}</code>${r.family_inventory?`<br><a href="${esc(r.family_inventory)}">${tr('Open member index','打开成员索引')} (${r.inventory_member_count}) →</a>`:r.route_kind==='family'?'<br>'+tr('Native member inventory pending','原生成员清单待补充'):''}</td><td>${source(r.access_shell)}<br>${source(r.payload_tier)}<br><span class="muted">${source(r.lifecycle)}</span></td></tr>`).join('')}</tbody></table></div>`;}
function deltaRow(d){return `<article class="row"><div class="row-main"><strong>${esc(d.route)}</strong><p class="row-sub">${esc(d.repo)} · <code>${esc(d.source)}</code></p><p class="row-sub">${source(d.disposition)}</p><p class="row-sub">${tr('Integration','整合')}: ${ownerLink(d.primary_session)}${d.design_slice?' · '+tr('Design slice','设计分工')+': '+ownerLink(d.design_slice):''}</p></div></article>`;}
function routeView(st,q){const rows=data.routes.filter(r=>(!st.owner||r.primary_session===st.owner||r.delegated_slices.includes(st.owner))&&(!q||JSON.stringify(r).toLowerCase().includes(q)));const ds=data.source_deltas.filter(r=>(!st.owner||r.primary_session===st.owner||r.design_slice===st.owner)&&(!q||JSON.stringify(r).toLowerCase().includes(q)));return {n:rows.length+ds.length,html:`<p class="quicklinks">${tr('This view searches canonical records and source deltas.','此视图搜索标准记录与源增量。')} <a href="inventory.html#q=${encodeURIComponent(st.q)}">${tr('Search all 14,025 tracked HTML paths','搜索全部 14,025 条 HTML 路径')} →</a></p>`+(rows.length?routeTable(rows,st):'')+(ds.length?`<div class="group-title"><h2>${tr('Source deltas · no canonical IDs invented','源增量 · 未虚构标准 ID')}</h2></div>`+ds.map(deltaRow).join(''):'')+(!rows.length&&!ds.length?empty(st):'')};}
function structuralChange(st){
 const n=data.metadata.structural_observations;const total=data.pages.filter(p=>p.listed_in_package&&!p.expanded_in_package).length;
 const observed=n?.observed_pages||0,remaining=total-observed;
 return {owner:'F03',name:tr(`${observed} of ${total} listed-only pages inspected`,`${total} 个基线仅列出页面中已检查 ${observed} 个`),
  text:tr(`${n?.observed_artboards||0} artboard identities observed; ${remaining} pages remain without structural reads. Full-content comparison, product ownership and disposal decisions remain open.`,
  `已观察 ${n?.observed_artboards||0} 个画板身份；${remaining} 个页面尚无结构读取。完整内容比较、产品负责人及处置决定仍待确认。`),
  url:hash({...st,view:'references',owner:'F03',session:'',page:'',board:'',q:observed?'structural observation':'unexpanded'})};
}
function changesView(st,q){const all=[...data.sessions.filter(s=>s.return_observation).map(s=>({owner:s.id,name:s.id+' source return observed',text:s.status+' · '+s.return_observation.observed_at_utc+' · '+s.return_observation.source_head,url:entry(s.id,st)})),...data.changes.map(c=>({owner:c.owner,name:c.file_name+' / '+c.name,text:c.kind+' · '+c.board_count+' boards · '+c.owner_basis,url:c.url})),...data.inventory_gaps.map(g=>({owner:g.design_assignment,name:g.path,text:'Unregistered full document; canonical ID is null. Existing registry/export owner must resolve admission; design assignment does not admit a route.',url:'inventory.html#q='+encodeURIComponent(g.path)})),...data.destinations.filter(d=>d.allocation_gap).map(d=>({owner:d.owner,name:d.name,text:'No dedicated baseline allocation; destination IDs remain null.',url:entry(d.owner,st)})),{owner:'P00',name:'Paper write qualification',text:'Direct catalog qualification and F03 directory refinements observed. Cross-file resource operations remain unqualified and NOT_DISPATCHED.',url:'OPERATIONS.md'},{owner:'F01',name:'Shared shell release',text:'Candidate.4 source-policy return observed; final joint release and native/reference qualification remain open.',url:entry('F01',st)},{owner:'F02',name:'Design system release',text:'Candidate return and policy concurrence observed; original held effect and final joint/native qualification remain open.',url:entry('F02',st)},structuralChange(st),{owner:'F03',name:'Macro inventory / native reconciliation',text:'Fresh Macro HTML inventory plus 29 Terminal modules and seven Mastermind web handlers obtained. Historical native projection is separate; OS feature views and admission remain qualified limits.',url:'inventory.html'}];const rows=all.filter(x=>(!st.owner||st.owner===x.owner)&&(!q||JSON.stringify(x).toLowerCase().includes(q)));return {n:rows.length,html:rows.map(x=>`<article class="row"><div class="row-main"><span class="eyebrow">${x.owner||tr('Unowned','无负责人')}</span><a class="row-title" href="${esc(x.url)}">${source(x.name)}</a><p class="row-sub">${source(x.text)}</p></div></article>`).join('')||empty(st)};}
function lineage(p){let a=[];for(const r of p.recorded_successors)a.push(`<p>${tr('Recorded successor','记录的后继')}: <a href="https://app.paper.design/file/${r.target_file_id}/${r.target_page_id}" target="_blank" rel="noopener"><code>${r.target_file_id} / ${r.target_page_id}</code> ↗</a> · <a href="${r.evidence}">${tr('Evidence','证据')}</a><br>${source(r.qualification)}</p>`);for(const r of p.recorded_predecessors)a.push(`<p>${tr('Recorded predecessor','记录的前身')}: <a href="https://app.paper.design/file/${r.source_file_id}/${r.source_page_id}" target="_blank" rel="noopener"><code>${r.source_file_id} / ${r.source_page_id}</code> ↗</a> · <a href="${r.evidence}">${tr('Evidence','证据')}</a></p>`);for(const n of p.lineage_notes)a.push(`<p>${source(n.statement)} <a href="${n.evidence}">${tr('Evidence','证据')}</a><br>${tr('Missing','缺失')}: ${source(n.missing)} · ${ownerLink(n.owner)}</p>`);if(!a.length)a.push(`<p>${tr('Exact predecessor/successor and decision receipts not established.','精确前身／后继与决定凭证尚未确立。')} ${tr('Resolve with','由以下任务处理')}: ${ownerLink(p.content_owner||'F03')}</p>`);return a.join('');}

function evidenceLink(url,label){
 const safe=!String(url||'').split('/').some(part=>part==='.'||part==='..')&&(url==='CONTRACT.md'||/^https:\/\/github\.com\/mastermindx-market-intelligence\/macro\/blob\/[0-9a-f]{40}\/[A-Za-z0-9_./-]+$/.test(url||'')||/^https:\/\/app\.paper\.design\/file\/[A-Z0-9]+\/p-[A-Za-z0-9-]+$/.test(url||''));
 return safe?`<a href="${esc(url)}" target="_blank" rel="noopener">${esc(label)} ↗</a>`:`<span>${tr('Destination not established','目标尚未确立')}</span>`;
}
function returnEvidence(s){
 const obs=s.return_observation||{},candidate=s.candidate_ref;
 const candidateIds=[obs.candidate_file_id,obs.candidate_page_id].filter(Boolean).join(' / ');
 const readmeIds=[obs.readme_file_id,obs.readme_page_id,obs.readme_board_id].filter(Boolean).join(' / ');
 return `<section class="entry"><div><h2>${tr('Candidate & reference review','候选与参考审核')}</h2><p>${tr('No approved candidate established in the inspected package.','所检查的资料尚未确立获批候选。')}</p><p>${source(s.status)}</p>
 ${candidate?`<p>${evidenceLink(candidate,tr('Observed candidate / directory','已观察候选／目录'))}</p>`:`<p>${tr('New native candidate not admitted or not established by this return.','本次返回尚未建立或获准建立新的原生候选稿。')}</p>`}
 ${obs.readme_url&&obs.readme_url!==candidate?`<p>${evidenceLink(obs.readme_url,tr('Read me / candidate entry','设计说明／候选入口'))}</p>`:''}
 ${obs.retained_reference_url?`<p>${evidenceLink(obs.retained_reference_url,tr('Retained original reference','保留的原参考'))}</p>`:''}
 ${candidateIds?`<p class="return-ids">${tr('Candidate identity','候选身份')}: <code>${esc(candidateIds)}</code></p>`:''}
 ${readmeIds?`<p class="return-ids">${tr('Read me identity','设计说明身份')}: <code>${esc(readmeIds)}</code></p>`:''}
 <p>${tr('RIG receipt: not observed. Writer custody is not established by this directory.','RIG 凭证：未观察。本目录不构成当前写入权证明。')} ${s.rig_state?source('RIG: '+s.rig_state):''}</p></div>
 <div><h2>${tr('Returned contract / package','已返回的合同／资料包')}</h2>${s.source_contract?`<p>${evidenceLink(s.source_contract,s.source_contract_label||tr('Returned source/build package','已返回的构建资料包'))}</p>`:`<p>${tr('Not returned. The assignment describes requirements; it is not a completed build contract.','尚未返回。任务说明列出要求，不等于完整构建合同。')}</p>`}
 ${obs.source_head?`<p>${tr('Immutable source','不可变来源')}: <code>${esc(obs.source_head)}</code></p><p>${tr('Observed','观察时间')}: ${esc(obs.observed_at_utc)}</p>`:''}
 <p>${source(s.shell_version||'F01 final release not observed')}</p><p>${source(s.system_version||'F02 final release not observed')}</p>
 <p><a href="${esc(s.handoff_url)}" target="_blank" rel="noopener">${tr('Original requirements','原始要求')} ↗</a></p></div></section>
 <p class="return-next"><strong>${tr('Next action','下一步')}:</strong> ${source(s.next_action)}</p>`;
}
function sliceEvidence(s){
 if(s.id!=='D08')return '';
 return `<section class="detail-section"><h2>${tr('Four separately owned design packages','四个独立负责的设计包')}</h2><p class="count">${tr('Design packages are not route records. Open the design reference or source contract directly; ownership and review remain separate.','设计包不等于路由记录。可直接打开设计参考或源合同；负责人和审核状态保持独立。')}</p><div class="return-grid">${['D08A','D08B','D08C','D08D'].map(id=>{const child=sessionById(id),obs=child.return_observation||{};return `<article class="return-package"><span class="eyebrow">${id}</span><h3>${esc(title(child))}</h3><p>${source(child.status)}</p><p>${obs.readme_url||child.candidate_ref?evidenceLink(obs.readme_url||child.candidate_ref,tr('Read me / design reference','设计说明／参考')):tr('Native candidate not admitted','原生候选稿尚未获准建立')}</p>${!child.candidate_ref&&obs.retained_reference_url?`<p>${evidenceLink(obs.retained_reference_url,tr('Retained original reference','保留的原参考'))}</p>`:''}<p>${child.source_contract?evidenceLink(child.source_contract,child.source_contract_label):tr('Contract not returned','合同尚未返回')}</p><p>${ownerLink(id,tr('Owner details','负责人详情'))}</p></article>`;}).join('')}</div></section>`;
}

function detail(s,st){const q=st.q.trim().toLowerCase();let refs=refsFor(s.id);const hits=refs.filter(p=>refText(p).includes(q));if(q&&hits.length)refs=[...hits,...refs.filter(p=>!hits.includes(p))];else refs.sort((a,b)=>({candidate_unqualified:0,reference_unqualified:1,specification:2,live_delta_unqualified:3,source_only:4,held:5,rejected:6,historical:7,redirect:8,unexpanded:9}[a.role]??10)-({candidate_unqualified:0,reference_unqualified:1,specification:2,live_delta_unqualified:3,source_only:4,held:5,rejected:6,historical:7,redirect:8,unexpanded:9}[b.role]??10));const rr=data.routes.filter(r=>r.primary_session===s.id||r.delegated_slices.includes(s.id)),ds=data.source_deltas.filter(r=>s.source_deltas.includes(r.route));return `<div class="detail"><div class="detail-heading"><a class="back" href="${esc(st.inventory?'inventory.html#'+st.inventory:hash({...st,session:'',board:'',page:''}))}">← ${tr('Back to results','返回结果')}</a><span class="eyebrow">${s.id}</span><h1>${esc(title(s))}</h1><p>${source(s.job)}</p>${q?`<p class="count">${tr('Search context retained','已保留搜索条件')}: <code>${esc(st.q)}</code></p>`:''}</div>${returnEvidence(s)}${sliceEvidence(s)}<section class="detail-section"><h2>${tr('Frozen baseline Paper references','冻结基线的 Paper 参考')} <span class="count">${refs.length}</span></h2><p class="count">${tr('Direct links remain visible. Role labels and recorded history are not approvals.','直接链接始终可见。角色标签与历史记录不等于批准。')}</p>${refs.map(p=>{const bs=boardsFor(p),match=!!q&&refText(p).includes(q);return `<article><div class="row"><div class="row-main"><span class="pill">${pageRole(p)}</span><a class="row-title" href="${p.url}" target="_blank" rel="noopener">${source(p.name)} ↗</a><p class="row-sub">${source(p.file_name)} · <code>${pageKey(p)}</code></p>${ownership(p)}${warnings(p)}${structuralEvidence(p)}</div></div>${p.recorded_successors.length||p.recorded_predecessors.length||p.lineage_notes.length?`<div class="history-summary">${lineage(p)}</div>`:''}<details ${(match||st.page===pageKey(p))?'open':''}><summary>${tr('Artboards, history and retention conditions','画板、历史与保留条件')}</summary>${!(p.recorded_successors.length||p.recorded_predecessors.length||p.lineage_notes.length)?lineage(p):''}<p>${source(p.conditions)}</p>${bs.length?`<div class="boards" tabindex="0" aria-label="${tr('Artboard identities','画板身份')}">${bs.map(b=>`<div class="board" id="${boardKey(b)}" tabindex="-1"><code>${b.artboard_id}</code> · ${source(b.name)} ${b.observed_role_labels.map(r=>`<span class="pill">${role(r)}</span>`).join(' ')}<br><span class="muted">${b.width??tr('unmeasured','未测量')} × ${b.height??tr('unmeasured','未测量')} · ${b.child_count} ${tr('children','子节点')} · ${tr('product owner','产品负责人')} ${boardOwner(b)}</span><br><a href="${p.url}" target="_blank" rel="noopener">${tr('Open containing Paper page','打开所在 Paper 页面')} ↗</a> <span class="muted">${tr('Exact board URL not verified; select this ID in Paper.','精确画板 URL 未验证；请在 Paper 中选择此 ID。')}</span></div>`).join('')}</div>`:`<p>${(observationFor(p)?.artboard_count??p.board_count)===0?tr('Zero artboards observed; design completion is not established.','观察到零画板；设计完成尚未确立。'):tr('Page contents not expanded.','页面内容未展开检查。')}</p>`}</details></article>`;}).join('')||`<p>${tr('No dedicated reference allocated; owner must return an exact candidate.','尚未分配专用参考；负责人需返回精确候选。')}</p>`}</section>${rr.length?`<section class="detail-section"><h2>${tr('Canonical route responsibility','标准路由职责')}</h2>${routeTable(rr,st)}</section>`:''}${ds.length?`<section class="detail-section"><h2>${tr('Source deltas','源增量')}</h2>${ds.map(deltaRow).join('')}</section>`:''}<section class="detail-section"><h2>${tr('Proposed working families','拟议工作文件')}</h2><p>${source(s.proposed_files.join(' · '))}</p><p class="count">${tr('Actual destinations pending verified reuse or creation.','实际目标待验证复用或创建。')}</p></section><p class="count">${source(s.dependencies)} · ${source(s.partners)}</p><p class="count">${tr('Directory refinements and label edits are recorded in paper/native-progress.json. All 301 cross-file organization actions remain NOT_DISPATCHED.','目录改进和标签编辑见 paper/native-progress.json。全部 301 项跨文件整理操作仍未发出。')}</p></div>`;}
function render(focus=false){const st=state();paintChrome(st);if(st.session){const s=sessionById(st.session);$('content').innerHTML=s?detail(s,st):empty(st);}else{const r=({assignments:assignmentView,references:referenceView,routes:routeView,changes:changesView}[st.view])(st,st.q.trim().toLowerCase());$('content').innerHTML=r.html;$('results').textContent=r.n+' '+tr('results in this view','条当前视图结果');}if(focus){$('main').focus({preventScroll:true});window.scrollTo({top:0,behavior:'instant'});if(st.board){const el=document.getElementById('board-'+st.page.replace('/','-')+'-'+st.board);if(el){el.focus({preventScroll:true});el.scrollIntoView({block:'center'});}}}}
function filter(){const st=state();history.replaceState(null,'',hash({...st,q:$('search').value,owner:$('owner').value,session:'',page:'',board:''}));render();}
$('search').addEventListener('input',filter);$('owner').addEventListener('change',filter);
function clearFilters(){const st=state();location.hash=hash({view:st.view});}
$('clear').addEventListener('click',clearFilters);document.addEventListener('click',e=>{if(e.target.matches('[data-clear]'))clearFilters();});
$('skip').addEventListener('click',e=>{e.preventDefault();$('main').focus();});
$('theme').addEventListener('click',()=>{document.documentElement.dataset.theme=document.documentElement.dataset.theme==='dark'?'light':'dark';syncTheme();});
$('locale').addEventListener('click',()=>{lang=lang==='en'?'zh':'en';render();});window.addEventListener('hashchange',()=>render(true));render(!!state().board);
