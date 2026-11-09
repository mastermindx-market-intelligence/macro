/* Design-only consumer of the existing measured_read_v1 synthetic fixture.
   No engine math, forecast, score, membership or entitlement is created here. */
(() => {
'use strict';
const main = document.querySelector('#main');
const dialog = document.querySelector('#source-dialog');
const stateControl = document.querySelector('#state-select');
let data = null, archive = null, archiveError = null, loadError = null, reviewState = 'source';
const filters={leadership:'',rotation:'',confluence:''};
const text = (en,zh) => document.documentElement.dataset.lang === 'zh' ? zh : en;
const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const measured = value => typeof value === 'number' && Number.isFinite(value);
const pct = value => measured(value) ? (value>0?'+':value<0?'−':'')+Math.abs(value).toFixed(1)+'%' : text('Not measured','未测量');
const direction = value => measured(value) ? (value>0?'up':value<0?'down':'') : '';
const name = g => text(g.name_en,g.name_zh || g.name_en);
const all = () => Array.isArray(data?.groups) ? data.groups : [];
const ranked = () => all().filter(g=>g.current?.status==='measured' && measured(g.current?.rs_63d)).slice().sort((a,b)=>(a.current.rank ?? Infinity)-(b.current.rank ?? Infinity));
const reason = code => ({missing_input:text('Price data unavailable','价格数据不可用'),thin_history:text('More history needed','需要更多历史数据'),non_finite_input:text('Data could not be checked','数据无法校验')})[code] || text('Not measured in this snapshot','此快照尚未测量');
function selection() {
 const url = new URL(location.href), id = url.searchParams.get('group');
 return all().find(g=>g.group_id===id) || ranked()[0] || all()[0] || null;
}
function task() {
 const hash = location.hash.slice(1);
 return hash==='research' ? 'research' : ['moving','turns','map','money','explore','confluence'].includes(hash) ? 'explore' : 'brief';
}
function detailTab() { const v = new URL(location.href).searchParams.get('detail'); return ['measure','record','companies'].includes(v)?v:'measure'; }
function navigate(group,hash,detail) {
 const url = new URL(location.href);
 if(group && all().some(g=>g.group_id===group)){url.searchParams.set('group',group);url.searchParams.set('investigation','measurement');}
 if(detail) url.searchParams.set('detail',detail);
 url.hash=hash || url.hash;
 history.pushState({sectorReference:true},'',url);
 render();
}
function translate() {
 document.querySelectorAll('[data-en][data-zh]').forEach(el=>el.textContent=text(el.dataset.en,el.dataset.zh));
 document.querySelector('#theme-toggle').textContent=document.documentElement.dataset.theme==='light'?text('Dark mode','深色模式'):text('Light mode','浅色模式');
 document.querySelector('#lang-toggle').textContent=document.documentElement.dataset.lang==='en'?'中文':'English';
}
function sourceRecord() {
 document.querySelector('#source-json').textContent=JSON.stringify({
  reference_only:true,live:false,applied_to_paper:false,
  fixture:'tests/fixtures/leadership_rotation/measured_read_v1.json',
  active_lens:lens(),investigation:investigationContext(),archive_sources:archive?.sources,
  schema:data?.schema,definition_id:data?.definition_id,
  generation:data?.generation,cohort:data?.cohort,authority:data?.authority,selected_group:selection()
 },null,2);
 dialog.showModal();
}
function valueBar(v,cap=5) {
 if(!measured(v)) return '<span class="fine">'+esc(text('Not measured','未测量'))+'</span>';
 return '<div class="bar-track"><i class="bar-fill '+(v<0?'down':'')+'" style="width:'+Math.min(100,Math.abs(v)/cap*100)+'%"></i></div>';
}
function miniBar(v,cap) {
 if(!measured(v)) return '';
 const width=Math.min(48,Math.abs(v)/cap*48),left=v<0?50-width:50;
 return '<div class="mini-bars" aria-hidden="true"><i class="mini-bar '+(v<0?'negative':'')+'" style="left:'+left+'%;width:'+width+'%"></i></div>';
}
function sourceLink() { return '<button class="secondary" type="button" data-source>'+esc(text('Inspect source record','查看来源记录'))+' <span aria-hidden="true">↗</span></button>'; }
function emptyPanel(title,why,action=true) {
 return '<section class="ref-panel state-panel"><span class="inline-state"><i class="state-dot"></i>'+esc(text('Data availability','数据可用情况'))+'</span><h2>'+esc(title)+'</h2><p>'+esc(why)+'</p>'+(action?'<button class="secondary" data-reset>'+esc(text('Return to fixture','返回测试样本'))+'</button>':'')+'</section>';
}
function brief() {
 const leaders=ranked(),lead=leaders[0],cohort=data.cohort || {};
 if(!lead) return emptyPanel(text('No measured groups','暂无已测量板块'),text('This snapshot contains no usable group measurements.','此快照没有可用的板块测量。'),false);
 const windows=[['21 sessions','21个交易日','rs_21d'],['63 sessions','63个交易日','rs_63d']];
 const max=Math.max(1,...windows.map(w=>Math.abs(lead.current[w[2]] || 0)));
 return '<section class="hero-grid"><div class="hero"><span class="inline-state"><i class="state-dot"></i>'+esc(text('Measured leadership','已测量的领涨表现'))+'</span><h2>'+esc(text(name(lead)+' leads the measured groups.',name(lead)+'领跑已测量板块。'))+'</h2><p class="lead">'+esc(text('Relative performance is an investigation starting point. It does not qualify a stock entry.','相对表现是研究的起点，不代表个股已具备入场条件。'))+'</p><button class="primary" data-group="'+esc(lead.group_id)+'">'+esc(text('Explore the leadership','探索领涨板块'))+' <span aria-hidden="true">→</span></button></div><div class="ref-panel"><div class="panel-head"><div><h3>'+esc(text(name(lead)+' versus S&P 500',name(lead)+'对比标普500'))+'</h3><p>'+esc(text('Relative wealth · total return basis','相对财富回报 · 含股息总回报口径'))+'</p></div><span class="subject-id">'+esc(lead.group_id)+'</span></div>'+windows.map(w=>'<div class="chart-label"><span>'+esc(text(w[0],w[1]))+'</span><span class="tnum value-lg '+direction(lead.current[w[2]])+'">'+pct(lead.current[w[2]])+'</span></div>'+valueBar(lead.current[w[2]],max)).join('')+'<p class="chart-foot">'+esc(text('A measured return comparison, not money flowing into the sector.','这是已测量的回报对比，并非板块资金流入。'))+'</p></div></section>'+
 '<section class="brief-support"><div class="ref-panel"><div class="panel-head"><div><h2>'+esc(text('Start your investigation','开始研究'))+'</h2><p>'+esc(text('First three groups in the source’s 63-session ranking','来源中63个交易日排名的前三个板块'))+'</p></div><a class="small-link" href="#explore">'+esc(text('Explore all','查看全部'))+'</a></div>'+leaders.slice(0,3).map((g,i)=>'<button class="priority-row" data-group="'+esc(g.group_id)+'"><span class="row-order tnum">'+String(i+1).padStart(2,'0')+'</span><span class="row-info"><span class="row-name">'+esc(name(g))+'</span><span class="row-sub" style="display:block">'+esc(g.group_id+' · '+text('Sector group','板块组'))+'</span></span><span class="tnum row-value '+direction(g.current.rs_63d)+'">'+pct(g.current.rs_63d)+'</span><span class="chevron" aria-hidden="true">›</span></button>').join('')+'</div>'+
 '<div class="ref-panel"><div class="panel-head"><div><h2>'+esc(text('Read with coverage','结合覆盖率解读'))+'</h2><p>'+esc(text('Missing data stays visible','缺失数据始终可见'))+'</p></div></div><div class="coverage-value tnum">'+esc(cohort.measured_n)+' <span class="fine">'+esc(text('of','/'))+'</span> '+esc(cohort.expected_n)+'</div><div class="fine">'+esc(text('sector groups measured','个板块组已测量'))+'</div><div class="coverage-grid" aria-hidden="true">'+Array.from({length:Math.min(30,cohort.expected_n || 0)},(_,i)=>'<i class="'+(i<(cohort.measured_n||0)?'':'missing')+'"></i>').join('')+'</div><p class="fine">'+esc(text('Unmeasured groups are kept outside the ranking. They are not treated as flat or negative.','未测量板块不参与排名，也不会被当作零涨幅或下跌。'))+'</p><a class="small-link" href="#explore">'+esc(text('See missing coverage','查看缺失覆盖'))+'</a></div></section>';
}
function briefComplete() {const content=brief(),at=content.indexOf('<section class="brief-support">');return at<0?content+changeBrief():content.slice(0,at)+changeBrief()+content.slice(at);}
function inspector(g) {
 const c=g.current || {},tab=detailTab(),r=g.reconstruction || {};
 let content='';
 if(tab==='measure') {
  content='<div class="measure-pair">'+[['21 sessions','21个交易日','rs_21d'],['63 sessions','63个交易日','rs_63d']].map(w=>'<div><small>'+esc(text(w[0],w[1]))+'</small><strong class="tnum '+direction(c[w[2]])+'">'+pct(c[w[2]])+'</strong></div>').join('')+'</div><div class="context-note"><strong>'+esc(c.status==='measured'?text('Leadership and entry are separate','领涨表现与入场条件不同'):reason(c.reason))+'</strong><p>'+esc(text('This record describes group performance. Check each stock’s own entry conditions before acting.','此记录描述板块表现；行动前需单独核查个股入场条件。'))+'</p></div>';
 } else if(tab==='record') {
  content='<div class="context-note"><strong>'+esc(text('Reconstructed history','重建历史'))+'</strong><p>'+esc(text('Rebuilt from price history. It is not proof of what the system displayed at that time.','根据历史价格重建，不证明系统当时曾显示这些信息。'))+'</p></div><dl class="record"><dt>'+esc(text('Available span','可用区间'))+'</dt><dd>'+esc((r.first || text('Unavailable','不可用'))+' → '+(r.last || text('Unavailable','不可用')))+'</dd><dt>'+esc(text('Retained points','保留观测点'))+'</dt><dd>'+esc(r.points ?? text('Not stated','未注明'))+'</dd><dt>'+esc(text('Observed then','当时已观察'))+'</dt><dd>'+esc(r.naturally_observed===true?text('Yes','是'):r.naturally_observed===false?text('No','否'):text('Not stated','未注明'))+'</dd></dl><p class="fine">'+esc(text('The fixture carries history metadata only. No time-series path is invented.','样本仅含历史元数据，不虚构时间序列曲线。'))+'</p>';
 } else {
  content='<div class="context-note"><strong>'+esc(text('Member evidence is not in this snapshot','此快照不含成分股证据'))+'</strong><p>'+esc(text('Verified company membership is unavailable for this snapshot. A sector proxy alone does not establish the roster.','此快照缺少已核实的公司成分数据，板块代理不能代替成分股名单。'))+'</p></div><button class="secondary" disabled>'+esc(text('Company data unavailable','成分股数据不可用'))+'</button><p class="fine">'+esc(text('Open a verified company to review its own entry conditions in Prophet.','选择已核实的公司，再到Prophet查看该股的独立入场条件。'))+'</p>';
 }
 return '<aside class="ref-panel inspector" aria-label="'+esc(text('Selected sector','已选板块'))+'"><div class="subject"><div><div class="eyebrow">'+esc(text('SELECTED GROUP','已选板块组'))+'</div><h2>'+esc(name(g))+'</h2><p class="fine">'+esc(text('United States · Sector group','美国 · 板块组'))+'</p></div><span class="subject-id">'+esc(g.group_id)+'</span></div><div class="detail-tabs" role="tablist" aria-label="'+esc(text('Group evidence','板块证据'))+'">'+[['measure','Measurement','测量'],['record','Record','记录'],['companies','Companies','成分股']].map(([id,en,zh])=>'<button id="detail-tab-'+id+'" role="tab" tabindex="'+(tab===id?'0':'-1')+'" aria-selected="'+(tab===id)+'" aria-controls="detail-panel" data-detail="'+id+'">'+esc(text(en,zh))+'</button>').join('')+'</div><div id="detail-panel" role="tabpanel" aria-labelledby="detail-tab-'+tab+'" tabindex="0">'+content+'</div>'+sourceLink()+'</aside>';
}
function explore() {
 const sel=selection();
 return '<section class="section-title"><div><h2>'+esc(text('Follow the measured leadership.','追踪已测量的领涨表现。'))+'</h2><p>'+esc(text('Compare first. Open the evidence when something matters.','先比较，再查看重要变化的证据。'))+'</p></div><span class="fine">'+esc(text('Measured leadership lens','已测量领涨视图'))+'</span></section><div class="controls"><input id="group-search" class="search" type="search" aria-label="'+esc(text('Find a sector','查找板块'))+'" placeholder="'+esc(text('Find a sector or symbol…','搜索板块或代码…'))+'"><span class="pill">'+esc(text('63 sessions','63个交易日'))+'</span><span class="pill">'+esc(text('Versus S&P 500','对比标普500'))+'</span></div><section class="explore-grid"><div class="ref-panel rank-panel"><div class="panel-head"><div><h2>'+esc(text('Relative leadership','相对领涨表现'))+'</h2><p>'+esc(text('Source ranking · relative wealth, total return','来源排名 · 相对财富回报，含股息'))+'</p></div><span class="fine" id="filter-count"></span></div><div class="rank-head"><span>'+esc(text('SECTOR GROUP','板块组'))+'</span><span class="bar-heading">'+esc(text('RELATIVE TO S&P 500','相对标普500'))+'</span><span style="text-align:right">63 '+esc(text('SESSIONS','交易日'))+'</span></div><div id="group-list"></div><div class="unmeasured"><h3>'+esc(text('Not measured','未测量'))+'</h3><div id="unmeasured-list"></div></div><p class="chart-foot">'+esc(text(data.cohort.measured_n+' of '+data.cohort.expected_n+' groups measured. Search changes the list, never the coverage denominator.',data.cohort.expected_n+'个板块组中，'+data.cohort.measured_n+'个已测量。搜索仅过滤列表，不改变覆盖率分母。'))+'</p></div>'+inspector(sel)+'</section>';
}
function populateList(query='') {
 const list=document.querySelector('#group-list'); if(!list)return;
 const needle=query.trim().toLowerCase();
 const match=g=>(name(g)+' '+g.group_id).toLowerCase().includes(needle);
 const rows=ranked().filter(match),max=Math.max(1,...ranked().map(g=>Math.abs(g.current.rs_63d))),sel=selection();
 list.innerHTML=rows.length?rows.map(g=>'<button class="rank-row" data-select="'+esc(g.group_id)+'" aria-pressed="'+(g.group_id===sel.group_id)+'"><span class="row-info"><span class="row-name">'+esc(name(g))+'</span><span class="row-sub" style="display:block">'+esc(g.group_id)+'</span></span>'+miniBar(g.current.rs_63d,max)+'<span class="row-value tnum '+direction(g.current.rs_63d)+'">'+pct(g.current.rs_63d)+'</span></button>').join(''):'<p class="fine">'+esc(text('No matching measured groups. Try another name or symbol.','没有匹配的已测量板块。请尝试其他名称或代码。'))+'</p>';
 const missing=all().filter(g=>g.current?.status!=='measured').filter(match);
 document.querySelector('#unmeasured-list').innerHTML=missing.length?missing.map(g=>'<button data-select="'+esc(g.group_id)+'">'+esc(name(g)+' · '+reason(g.current?.reason))+'</button>').join(''):'<span class="fine">'+esc(text('No unmeasured groups match this search.','此次搜索没有匹配的未测量板块。'))+'</span>';
 document.querySelector('#filter-count').textContent=query?text(rows.length+' matches',rows.length+'项匹配'):'';
}
function research() {
 const g=selection(),gen=data.generation;
 return '<section class="section-title"><div><h2>'+esc(text('Keep the investigation connected.','让研究保持连贯。'))+'</h2><p>'+esc(text('The question travels with its subject and source.','问题、研究对象与来源一同保留。'))+'</p></div></section><section class="research-grid"><div class="ref-panel"><span class="source-tag">'+esc(name(g)+' · '+g.group_id)+'</span><h3 class="question">'+esc(text('What supports this group’s relative leadership—and what remains unmeasured?','哪些证据支持该板块的相对表现？还有什么尚未测量？'))+'</h3><div class="context-note"><strong>'+esc(text('Measurement, observation, estimate','测量、观察、估计'))+'</strong><p>'+esc(text('These are different evidence classes. A research summary cannot return as an independent confirming signal.','这是三种不同证据。研究总结不能作为独立确认信号再次计票。'))+'</p></div><a class="secondary" style="margin-top:24px" href="#explore">'+esc(text('Return to the selected group','返回已选板块'))+' →</a></div><div class="ref-panel"><div class="panel-head"><h2>'+esc(text('Context retained','已保留的上下文'))+'</h2></div><dl class="record"><dt>'+esc(text('Subject','对象'))+'</dt><dd>'+esc(g.group_id+' · '+name(g))+'</dd><dt>'+esc(text('Benchmark','基准'))+'</dt><dd>'+esc(gen.benchmark)+'</dd><dt>'+esc(text('Horizon','周期'))+'</dt><dd>'+esc(text('63 trading sessions','63个交易日'))+'</dd><dt>'+esc(text('Basis','口径'))+'</dt><dd>'+esc(text('Total return','含股息总回报'))+'</dd><dt>'+esc(text('Snapshot','快照'))+'</dt><dd>'+esc(gen.id)+'</dd><dt>'+esc(text('Action authority','行动权限'))+'</dt><dd>'+esc(text('None in this measured record','此测量记录不提供行动权限'))+'</dd></dl>'+sourceLink()+'</div></section>';
}

/* Native analytical lenses. Archived fixtures keep their own source clocks. */
const lens = () => ({moving:'rotation',turns:'turns',explore:'leadership',money:'money',confluence:'confluence',map:'cycles'})[location.hash.slice(1)] || 'leadership';
const params = () => new URL(location.href).searchParams;
function route(hash,values={}) {
 const url=new URL(location.href);
 Object.entries(values).forEach(([key,value])=>value==null?url.searchParams.delete(key):url.searchParams.set(key,String(value)));
 url.hash=hash;history.pushState({sectorReference:true},'',url);render();
}
function lensNavigation() {
 return '<nav class="lens-nav" aria-label="'+esc(text('Explore lenses','探索视图'))+'">'+
 [['rotation','moving','Rotation','轮动'],['turns','turns','Turns','拐点'],['leadership','explore','Leadership','领涨'],['money','money','Money','资金'],['confluence','confluence','Confluence','共振'],['cycles','map','Cycles','周期']]
 .map(([id,hash,en,zh])=>'<a href="#'+hash+'"'+(lens()===id?' aria-current="page"':'')+'>'+esc(text(en,zh))+'</a>').join('')+'</nav>';
}
function archiveNotice() {
 return '<div class="archive-note"><span class="source-tag">'+esc(text('Retained archive','保留存档'))+'</span><p>'+esc(text('These views use the preserved August 2026 source snapshots. The Brief uses a separate October test fixture. Their dates and measures remain separate.','这些视图采用2026年8月保留的来源快照。简报使用独立的10月测试样本；两者日期与口径分别展示。'))+'</p></div>';
}
function changeBrief() {
 const e=data.confirmed_events || {},rows=Array.isArray(e.rows)?e.rows:[];
 return '<section class="ref-panel change-brief"><div class="panel-head"><div><div class="eyebrow">'+esc(text('WHAT CHANGED','发生了什么变化'))+'</div><h2>'+esc(text('Changes deserve their own read.','变化值得单独解读。'))+'</h2><p>'+esc(text('Event observations are separate from today’s leadership ranking.','事件观察与当前领涨排名分开展示。'))+'</p></div><a class="small-link" href="#turns">'+esc(text('Inspect turns','查看拐点'))+' →</a></div>'+
 (e.status==='available'?'<div class="event-summary"><strong class="tnum">'+esc(e.n_active)+'</strong><span>'+esc(text('active events in this fixture','项样本中的活跃事件'))+'</span></div><div class="event-brief-list">'+rows.map(row=>'<button data-event="'+esc(row.id)+'"><span>'+esc(row.from_key)+' <span aria-hidden="true">→</span> '+esc(row.to_key)+'</span><span class="fine">'+esc(row.started)+' · '+esc(text('Day '+row.day_n,'第'+row.day_n+'天'))+'</span></button>').join('')+'</div>':
 '<p class="fine">'+esc(text('An event record is unavailable. A turn is not inferred from a rank.','事件记录不可用；不从排名推断拐点。'))+'</p>')+'</section>';
}
function eventObservation(row) {
 return '<article class="event-card"><div class="event-card-head"><span class="source-tag">'+esc(row.severity || text('Not classified','未分类'))+'</span><span class="fine tnum">'+esc(row.asof)+'</span></div><h3>'+esc(row.from_key)+' <span aria-hidden="true">→</span> '+esc(row.to_key)+'</h3><p class="fine">'+esc(row.sector)+'</p><dl class="record"><dt>'+esc(text('First recorded','首次记录'))+'</dt><dd>'+esc(row.started)+'</dd><dt>'+esc(text('Event age','事件持续'))+'</dt><dd>'+esc(text('Day '+row.day_n,'第'+row.day_n+'天'))+'</dd><dt>'+esc(text('Event type','事件类型'))+'</dt><dd>'+esc(row.event_type || text('Not specified by source','来源未注明'))+'</dd></dl><button class="secondary" data-event-research="'+esc(row.id)+'">'+esc(text('Research this change','研究这一变化'))+' →</button></article>';
}
function turnsLens() {
 const e=data.confirmed_events || {},rows=Array.isArray(e.rows)?e.rows:[];
 return '<section class="section-title"><div><h2>'+esc(text('Separate change from leadership.','区分变化与领涨。'))+'</h2><p>'+esc(text('Inspect the event, its date, and what the source actually observed.','查看事件、日期，以及来源实际观察到的内容。'))+'</p></div><span class="fine tnum">'+esc(e.as_of || text('Date unavailable','日期不可用'))+'</span></section>'+
 (e.status==='available'?'<div class="event-grid">'+rows.map(eventObservation).join('')+'</div>':emptyPanel(text('Event observations unavailable','事件观察不可用'),text('The ranked performance view cannot substitute for a turn record.','表现排名不能代替拐点记录。'),false))+
 '<div class="ref-panel method-note"><h3>'+esc(text('A turn is a recorded change.','拐点是一项被记录的变化。'))+'</h3><p>'+esc(text('These source events do not add a stock-entry vote. The native Turn Desk and early tape observations retain their own qualification and confirmation status.','这些来源事件不会增加个股入场票数。原生拐点工作台与早期盘面观察保留各自的资格及确认状态。'))+'</p>'+sourceLink()+'</div>';
}
function rotationUniverse() { const v=params().get('rotation_universe');return ['sectors','subsectors','themes'].includes(v)?v:'sectors'; }
const rotationKey = g => g.key || g.theme;
function rotationRows() { return archive?.rotation?.[rotationUniverse()] || []; }
function rotationSelection() {
 const rows=rotationRows(),key=params().get('rotation_group');
 return rows.find(g=>rotationKey(g)===key) || rows.find(g=>rotationKey(g)===selection()?.group_id) || rows[0] || null;
}
function nativeName(g) { return text(g.name || g.label || g.theme || rotationKey(g),g.name_zh || g.label_zh || g.theme_zh || g.name || g.label || g.theme || rotationKey(g)); }
function sourceNumber(v) { return measured(v)?v.toFixed(2):text('Not measured','未测量'); }
function quadrantLabel(q) { return ({leading:text('Leading','领先'),improving:text('Improving','改善'),weakening:text('Weakening','走弱'),lagging:text('Lagging','落后')})[q] || text('Not classified','未分类'); }
function rotationPlot(rows,selected) {
 const valid=rows.filter(g=>measured(g.rs_ratio)&&measured(g.rs_mom));
 // A v2 tail cannot be combined with these original coordinates.
 const points=valid.map(g=>[g.rs_ratio,g.rs_mom]);
 const bound=Math.max(1,...points.map(p=>Math.max(Math.abs(p[0]),Math.abs(p[1]))))*1.08;
 const x=v=>300+v/bound*240,y=v=>235-v/bound*177;
 const labels=[['Leading','领先',455,64],['Improving','改善',145,64],['Weakening','走弱',455,402],['Lagging','落后',145,402]];
 const path='';
 return '<svg class="rotation-plot" viewBox="0 0 600 470" role="img" aria-label="'+esc(text('Native relative strength and momentum. An accessible list follows the chart.','原生相对强弱与动量。图表后附有无障碍列表。'))+'"><rect x="40" y="30" width="520" height="397" rx="12" class="plot-surface"/><line x1="300" x2="300" y1="40" y2="415" class="plot-axis"/><line x1="55" x2="545" y1="235" y2="235" class="plot-axis"/>'+labels.map(q=>'<text x="'+q[2]+'" y="'+q[3]+'" text-anchor="middle" class="quadrant-label">'+esc(text(q[0],q[1]))+'</text>').join('')+path+
 valid.map(g=>'<g class="plot-point'+(rotationKey(g)===(selected?rotationKey(selected):null)?' selected':'')+'" data-rotation="'+esc(rotationKey(g))+'" role="button" tabindex="0" aria-label="'+esc(nativeName(g)+' · '+quadrantLabel(g.quadrant))+'"><title>'+esc(nativeName(g)+' · '+quadrantLabel(g.quadrant))+'</title><circle cx="'+x(g.rs_ratio).toFixed(1)+'" cy="'+y(g.rs_mom).toFixed(1)+'" r="'+(rotationKey(g)===(selected?rotationKey(selected):null)?'6':'3.5')+'"/></g>').join('')+
 '<text x="300" y="457" text-anchor="middle" class="axis-label">'+esc(text('Weaker ← Relative strength → Stronger','较弱 ← 相对强弱 → 较强'))+'</text><text x="18" y="237" text-anchor="middle" transform="rotate(-90 18 237)" class="axis-label">'+esc(text('Cooling ← Momentum → Heating','降温 ← 动量 → 升温'))+'</text></svg>';
}
function rotationLens() {
 if(!archive)return emptyPanel(text('Rotation source unavailable','轮动来源不可用'),text('No point or path is filled in without its source record.','没有来源记录，就不会补入点位或路径。'),false);
 const rows=rotationRows(),g=rotationSelection();
 if(!g)return emptyPanel(text('No groups in this source','此来源没有板块组'),text('Choose a different universe.','请选择其他范围。'),false);
 return '<section class="section-title"><div><h2>'+esc(text('See the rotation take shape.','看清轮动的形态。'))+'</h2><p>'+esc(text('Where groups stand, how their pace differs, and what their recorded turn status says.','板块组的位置、变化速度，以及记录的拐点状态。'))+'</p></div><span class="fine">'+esc(text('Native rotation view','原生轮动视图'))+'</span></section>'+archiveNotice()+
 '<div class="controls"><label class="select-label">'+esc(text('Universe','范围'))+' <select id="rotation-universe">'+[['sectors','Sector ETFs','板块ETF'],['subsectors','Industries','细分行业'],['themes','Themes','主题']].map(([id,en,zh])=>'<option value="'+id+'"'+(id===rotationUniverse()?' selected':'')+'>'+esc(text(en,zh))+'</option>').join('')+'</select></label><input id="rotation-search" class="search" type="search" placeholder="'+esc(text('Find a group…','查找板块组…'))+'" aria-label="'+esc(text('Find a rotation group','查找轮动板块组'))+'"><span class="fine">'+esc(rows.length+' '+text('source groups','个来源板块组'))+'</span></div>'+
 '<section class="explore-grid"><div class="ref-panel plot-panel">'+rotationPlot(rows,g)+'<p class="chart-foot">'+esc(text('Positions use the original source coordinates. A historical trail is unavailable for this coordinate basis. Missing positions remain visible in the list.','点位采用原始来源坐标；此坐标口径未提供历史轨迹。缺失点位仍在列表中可见。'))+'</p></div><aside class="ref-panel inspector"><div class="eyebrow">'+esc(text('SELECTED GROUP','已选板块组'))+'</div><div class="subject"><div><h2>'+esc(nativeName(g))+'</h2><p class="fine">'+esc(rotationKey(g))+'</p></div></div><span class="source-tag">'+esc(quadrantLabel(g.quadrant))+'</span><div class="measure-pair"><div><small>'+esc(text('Relative strength','相对强弱'))+'</small><strong class="tnum">'+sourceNumber(g.rs_ratio)+'</strong></div><div><small>'+esc(text('Momentum','动量'))+'</small><strong class="tnum">'+sourceNumber(g.rs_mom)+'</strong></div></div><p class="fine">'+esc(text('Native coordinates; neither value is a percentage return.','原生坐标；两项数值均非回报百分比。'))+'</p><div class="context-note"><strong>'+esc(text(g.turn_label || 'Turn status unavailable',g.turn_label_zh || g.turn_label || '拐点状态不可用'))+'</strong><p>'+esc(text(g.turn_say || 'No source explanation.',g.turn_say_zh || g.turn_say || '来源没有解释。'))+'</p></div><dl class="record"><dt>'+esc(text('Source session','来源交易日'))+'</dt><dd>'+esc(archive.rotation.asof)+'</dd><dt>'+esc(text('Turn since','状态始于'))+'</dt><dd>'+esc(g.turn_since || text('Not stated','未注明'))+'</dd></dl><button class="secondary" data-rotation-research="'+esc(rotationKey(g))+'">'+esc(text('Continue the investigation','继续研究'))+' →</button>'+sourceLink()+'</aside></section>'+
 '<section class="ref-panel rotation-list-panel"><div class="panel-head"><h2>'+esc(text('All groups in this view','本视图中的全部板块组'))+'</h2><span class="fine" id="rotation-count"></span></div><div class="table-scroll"><table class="source-table"><thead><tr><th>'+esc(text('Group','板块组'))+'</th><th>'+esc(text('Position','位置'))+'</th><th>'+esc(text('Strength','强弱'))+'</th><th>'+esc(text('Momentum','动量'))+'</th></tr></thead><tbody id="rotation-rows"></tbody></table></div></section>';
}
function populateRotation(query='') {
 const target=document.querySelector('#rotation-rows');if(!target)return;
 const rows=rotationRows(),matches=rows.filter(g=>(nativeName(g)+' '+rotationKey(g)).toLowerCase().includes(query.trim().toLowerCase()));
 target.innerHTML=matches.length?matches.map(g=>'<tr'+(rotationKey(g)===(rotationSelection()?rotationKey(rotationSelection()):null)?' class="is-selected"':'')+'><td><button data-rotation="'+esc(rotationKey(g))+'">'+esc(nativeName(g))+'</button><span class="row-sub">'+esc(rotationKey(g))+'</span></td><td>'+esc(quadrantLabel(g.quadrant))+'</td><td class="tnum">'+sourceNumber(g.rs_ratio)+'</td><td class="tnum">'+sourceNumber(g.rs_mom)+'</td></tr>').join(''):'<tr><td colspan="4">'+esc(text('No matching groups. Your universe and source counts are unchanged.','没有匹配的板块组；范围及来源数量保持不变。'))+'</td></tr>';
 document.querySelector('#rotation-count').textContent=matches.length+' / '+rows.length;
}
function moneyLens() {
 if(!archive)return emptyPanel(text('Money evidence unavailable','资金证据不可用'),text('Returns cannot substitute for flow or participation.','回报不能替代资金流或市场参与度。'),false);
 const m=archive.money,b=m.market_concentration || {},flow=m.flow?.cluster?.regime;
 const flowLabel=({broad:text('Spread across many','广泛分布'),concentrated:text('Crowding into a few','集中于少数'),mixed:text('No single group leads','没有单一板块领跑')})[flow] || text('Not measured','未测量');
 const count=v=>measured(v)?String(v):text('Unavailable','不可用');
 return '<section class="section-title"><div><h2>'+esc(text('Look beneath the market’s move.','观察市场涨跌背后。'))+'</h2><p>'+esc(text('Read participation and flow under their own definitions.','依据各自定义，解读市场参与度与资金流。'))+'</p></div></section>'+archiveNotice()+
 '<section class="money-grid"><div class="ref-panel flow-lead"><div class="eyebrow">'+esc(text('NATIVE FLOW REGIME','原生资金流状态'))+'</div><h2>'+esc(flowLabel)+'</h2><p>'+esc(text('A source classification of concentration. It is not a dollar amount or a direct measurement of fund inflows.','来源对集中程度的分类，不是美元金额，也不直接代表基金净流入。'))+'</p><span class="fine">'+esc(m.generated_utc || text('Date unavailable','日期不可用'))+'</span></div>'+
 '<div class="ref-panel"><div class="panel-head"><h2>'+esc(text('Participation','市场参与度'))+'</h2><span class="fine">'+esc(m.as_of)+'</span></div><div class="participation-counts"><div><strong class="tnum up">'+count(b.adv)+'</strong><span>'+esc(text('Advancing','上涨'))+'</span></div><div><strong class="tnum down">'+count(b.dec)+'</strong><span>'+esc(text('Declining','下跌'))+'</span></div></div><dl class="record"><dt>'+esc(text('Advance / decline','涨跌比'))+'</dt><dd class="tnum">'+count(b.ad_ratio)+'</dd><dt>'+esc(text('New highs / lows','新高 / 新低'))+'</dt><dd class="tnum">'+count(b.nh)+' / '+count(b.nl)+'</dd></dl></div>'+
 '<div class="ref-panel"><div class="panel-head"><h2>'+esc(text('Trend participation','趋势参与度'))+'</h2></div>'+[['Above 50-day average','高于50日均线',b.pct_above_50],['Above 200-day average','高于200日均线',b.pct_above_200]].map(([en,zh,v])=>'<div class="chart-label"><span>'+esc(text(en,zh))+'</span><strong class="tnum">'+(measured(v)?v.toFixed(1)+'%':text('Unavailable','不可用'))+'</strong></div>'+valueBar(v,100)).join('')+'<p class="chart-foot">'+esc(text('The native coverage and price basis govern these readings. They are separate from the Brief’s 9/11 sector cohort.','读数依据原生覆盖范围及价格口径，与简报中的9/11板块样本分别解读。'))+'</p></div>'+
 '<div class="ref-panel"><div class="panel-head"><h2>'+esc(text('ETF flows & live market heat','ETF资金流与实时市场热度'))+'</h2></div><div class="context-note"><strong>'+esc(text('Not included in this retained snapshot','此保留快照不包含这些数据'))+'</strong><p>'+esc(text('These feeds keep their original source and refresh cadence. No treemap, flow amount, or polling clock is synthesized for this reference.','这些数据源保留原有来源与刷新频率，本参考稿不生成热力图、资金流金额或轮询时钟。'))+'</p></div>'+sourceLink()+'</div></section>';
}
function confluenceUniverse() {const v=params().get('universe');return ['sp500','nasdaq','russell','baskets'].includes(v)?v:'sp500';}
function confluenceData() {return archive?.confluence?.[confluenceUniverse()] || null;}
function confluenceSelection() {const rows=confluenceData()?.groups || [];return rows.find(g=>g.key===params().get('confluence_group')) || rows[0] || null;}
function classLabel(value) {return ({entry_now:text('Entry now','现可入场'),forming:text('Forming','形成中'),tailwind:text('Tailwind','顺风'),neutral:text('Neutral','中性'),late:text('Late','偏晚'),headwind:text('Headwind','逆风')})[value] || text('Not classified','未分类');}
function confluenceLens() {
 const d=confluenceData(),g=confluenceSelection();if(!d||!g)return emptyPanel(text('Confluence source unavailable','共振来源不可用'),text('Universe-specific evidence is required before groups can be compared.','比较前需要各范围独立的证据。'),false);
 const c=d.coverage || {},raw=c.n_subsectors,eligible=c.n_gateable,thin=c.n_thin;
 const coverage=raw!=null&&eligible!=null?text(eligible+' of '+raw+' groups have enough data for timing; '+thin+' do not appear in this timed table.',raw+'个板块组中有'+eligible+'个具备足够数据进行择时；'+thin+'个未进入本择时表。'):
 text('The source reports '+c.n_baskets+' baskets. A gateable or thin denominator is not supplied.', '来源报告'+c.n_baskets+'个主题篮子，未提供可择时或数据不足的分母。');
 return '<section class="section-title"><div><h2>'+esc(text('Read the agreement—and the tension.','同时查看一致与分歧。'))+'</h2><p>'+esc(text('Entry conditions and regime are distinct source judgments.','入场条件与市场状态是不同的来源判断。'))+'</p></div></section>'+archiveNotice()+
 '<div class="controls"><label class="select-label">'+esc(text('Universe','范围'))+' <select id="confluence-universe">'+[['sp500','S&P 500','标普500'],['nasdaq','Nasdaq-100','纳斯达克100'],['russell','Russell-2000','罗素2000'],['baskets','Thematic baskets','主题篮子']].map(([id,en,zh])=>'<option value="'+id+'"'+(id===confluenceUniverse()?' selected':'')+'>'+esc(text(en,zh))+'</option>').join('')+'</select></label><input id="confluence-search" class="search" type="search" placeholder="'+esc(text('Find a group…','查找板块组…'))+'" aria-label="'+esc(text('Find a confluence group','查找共振板块组'))+'"></div><p class="coverage-note">'+esc(coverage)+'</p>'+
 '<section class="explore-grid"><div class="ref-panel"><div class="panel-head"><h2>'+esc(text('Native source order','原生来源排序'))+'</h2><span class="fine" id="confluence-count"></span></div><div class="table-scroll"><table class="source-table"><thead><tr><th>'+esc(text('Group','板块组'))+'</th><th>'+esc(text('Class','分类'))+'</th><th>'+esc(text('Entry tier','入场层级'))+'</th><th>'+esc(text('Regime','状态'))+'</th></tr></thead><tbody id="confluence-rows"></tbody></table></div></div>'+
 '<aside class="ref-panel inspector"><div class="eyebrow">'+esc(text('SELECTED GROUP','已选板块组'))+'</div><h2 class="dossier-title">'+esc(nativeName(g))+'</h2><p class="fine">'+esc(g.kind+' · '+d.universe)+'</p><div class="evidence-pair"><div><span>'+esc(text('Entry tier','入场层级'))+'</span><strong>'+esc(g.entry?.tier || text('None','无'))+'</strong><p class="fine">'+esc(g.entry?.reason || text('No entry explanation supplied','来源未提供入场解释'))+'</p></div><div><span>'+esc(text('Regime','状态'))+'</span><strong>'+esc(text(g.regime?.label || 'Unavailable',g.regime?.label_zh || g.regime?.label || '不可用'))+'</strong><p class="fine">'+esc(text(g.regime?.action || '',g.regime?.action_zh || g.regime?.action || ''))+'</p></div></div><dl class="record"><dt>'+esc(text('Source session','来源交易日'))+'</dt><dd>'+esc(d.as_of)+'</dd><dt>'+esc(text('Priced / members','已定价 / 成分数'))+'</dt><dd>'+esc(g.n_priced+' / '+g.n_members)+'</dd><dt>'+esc(text('Reliability','可靠度'))+'</dt><dd>'+esc(g.reliability || text('Unavailable','不可用'))+'</dd></dl><p class="fine">'+esc(text('A group entry tier does not qualify any member stock. The company’s own entry conditions remain required.','板块组入场层级不代表任一成分股已符合条件，仍需个股独立入场判断。'))+'</p><button class="secondary" data-confluence-research="'+esc(g.key)+'">'+esc(text('Research this group','研究这一板块组'))+' →</button>'+sourceLink()+'</aside></section>';
}
function populateConfluence(query='') {
 const target=document.querySelector('#confluence-rows');if(!target)return;
 const rows=confluenceData()?.groups || [],matches=rows.filter(g=>(nativeName(g)+' '+g.key).toLowerCase().includes(query.trim().toLowerCase()));
 target.innerHTML=matches.length?matches.map(g=>'<tr'+(g.key===confluenceSelection()?.key?' class="is-selected"':'')+'><td><button data-confluence="'+esc(g.key)+'">'+esc(nativeName(g))+'</button></td><td>'+esc(classLabel(g.class))+'</td><td>'+esc(g.entry?.tier || '—')+'</td><td>'+esc(text(g.regime?.label || 'Unavailable',g.regime?.label_zh || g.regime?.label || '不可用'))+'</td></tr>').join(''):'<tr><td colspan="4">'+esc(text('No matches in this universe. The source counts are unchanged.','此范围没有匹配项；来源数量保持不变。'))+'</td></tr>';
 document.querySelector('#confluence-count').textContent=matches.length+' / '+rows.length;
}
function cyclesLens() {
 return '<section class="section-title"><div><h2>'+esc(text('Place today in the longer cycle.','将今天放回长期周期中。'))+'</h2><p>'+esc(text('Price, oscillator, historical legs, and detected turns retain their native definitions.','价格、振荡指标、历史区段与已识别拐点保留原生定义。'))+'</p></div></section>'+emptyPanel(text('Cycle history is not in this reference.','此参考稿不含周期历史。'),text('The production migration keeps the existing cycle engine and its history controls. No illustrative cycle path replaces that record here.','生产迁移将保留现有周期引擎与历史控制，不以示意曲线代替原始记录。'),false);
}
function investigationContext() {
 const type=params().get('investigation');
 if(type==='rotation'&&archive){const g=rotationSelection();return {type,subject:g?nativeName(g):'',identity:g?rotationKey(g):null,universe:rotationUniverse(),source_session:archive.rotation.asof,source:'marketdata/subsector_rotation.json',evidence_class:'retained_archive',authority:'display_only',record:g};}
 if(type==='confluence'&&archive){const g=confluenceSelection(),d=confluenceData();return {type,subject:g?nativeName(g):'',identity:g?.key,universe:d?.universe,source_session:d?.as_of,source:'marketdata/'+({sp500:'subsector_confluence.json',nasdaq:'subsector_confluence_nasdaq.json',russell:'subsector_confluence_russell.json',baskets:'basket_confluence.json'})[confluenceUniverse()],evidence_class:'retained_archive',authority:'group_judgment_not_stock_entry',record:g};}
 if(type==='turn'){const g=data.confirmed_events?.rows?.find(r=>r.id===params().get('event')) || data.confirmed_events?.rows?.[0];return {type,subject:g?g.from_key+' → '+g.to_key:'',identity:g?.id,universe:'source_event_keys',source_session:g?.asof,source:data.confirmed_events?.source,evidence_class:'synthetic_fixture',authority:'display_only',record:g};}
 const g=selection();return {type:'measurement',subject:g?name(g):'',identity:g?.group_id,universe:data.cohort?data.generation?.cohort:'',source_session:data.generation?.session_end,source:'tests/fixtures/leadership_rotation/measured_read_v1.json',evidence_class:'synthetic_fixture',authority:'display_only',record:g};
}
function researchConnected() {
 const c=investigationContext(),returnHash=({rotation:'moving',confluence:'confluence',turn:'turns',measurement:'explore'})[c.type];
 return '<section class="section-title"><div><h2>'+esc(text('Carry the evidence forward.','让证据伴随研究。'))+'</h2><p>'+esc(text('The selected subject, source, and question remain together.','已选对象、来源与问题保持关联。'))+'</p></div></section><section class="research-grid"><div class="ref-panel"><span class="source-tag">'+esc(c.subject)+'</span><h3 class="question">'+esc(text('What supports this observation, what disagrees, and what must happen next?','哪些证据支持这一观察？有哪些分歧？接下来需满足什么条件？'))+'</h3><div class="context-note"><strong>'+esc(text('Keep each evidence class distinct','区分各类证据'))+'</strong><p>'+esc(text('Measurements, recorded events, and estimates answer different questions. A generated explanation adds no independent confirming vote.','测量、记录事件与估计回答不同问题，生成的解释不会增加独立确认票数。'))+'</p></div><a class="secondary research-return" href="#'+returnHash+'">'+esc(text('Return to the selected evidence','返回已选证据'))+' →</a></div><div class="ref-panel"><div class="panel-head"><h2>'+esc(text('Context retained','已保留的上下文'))+'</h2></div><dl class="record">'+[[text('Subject','对象'),c.identity],[text('Source session','来源交易日'),c.source_session],[text('Evidence class','证据类别'),c.evidence_class==='retained_archive'?text('Retained source archive','保留来源存档'):text('Synthetic test fixture','合成测试样本')],[text('Native source','原生来源'),c.source]].map(([label,value])=>'<dt>'+esc(label)+'</dt><dd>'+esc(value || text('Not stated','未注明'))+'</dd>').join('')+'</dl><div class="context-note"><strong>'+esc(text('Company entry remains a separate step','个股入场仍需单独确认'))+'</strong><p>'+esc(text('A verified member and its own Prophet entry conditions are required. This reference does not claim a live Prophet connection.','需要已核实的成分股及其独立Prophet入场条件。本参考稿不代表已接通实时Prophet。'))+'</p></div>'+sourceLink()+'</div></section>';
}
function exploreLenses() {
 const renderer={leadership:explore,rotation:rotationLens,turns:turnsLens,money:moneyLens,confluence:confluenceLens,cycles:cyclesLens}[lens()];
 return lensNavigation()+renderer();
}

function render() {
 translate();
 document.querySelectorAll('[data-task]').forEach(a=>{if(a.dataset.task===task())a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
 if(reviewState==='loading'||(!data&&!loadError)){ main.innerHTML='<div class="skeleton-layout" role="status" aria-label="'+esc(text('Loading sector data','正在加载板块数据'))+'"><div class="skel skel-title"></div><div class="skel skel-chart"></div></div>';return; }
 if(loadError||reviewState==='error'){main.innerHTML=emptyPanel(text('Sector data could not load.','板块数据加载失败。'),text('The reference keeps your selected group and task. Return to the fixture to continue.','参考稿保留已选板块与任务。返回测试样本即可继续。'));return;}
 if(reviewState==='empty'){main.innerHTML=emptyPanel(text('No measurements in this snapshot.','此快照没有测量数据。'),text('No value is substituted for missing evidence. Your filters and selection remain intact.','缺失证据不会被替换成数值，筛选与选择保持不变。'));return;}
 if(reviewState==='signed-out'){main.innerHTML=emptyPanel(text('Member evidence needs access.','成分股证据需要访问权限。'),text('Your selected group is kept while you sign in. Member evidence appears when access is confirmed.','登录时保留已选板块，确认访问权限后显示成分股证据。'));return;}
 const active=lens(),context=task()==='research'?investigationContext():null;
 const archived=context?context.evidence_class==='retained_archive':task()==='explore'&&['rotation','money','confluence'].includes(active);
 const sourceDate=context?context.source_session:archived?(active==='rotation'?archive?.rotation?.asof:active==='money'?archive?.money?.as_of:confluenceData()?.as_of):data.generation.session_end;
 document.querySelector('#source-date').textContent=sourceDate || text('Unavailable','不可用');
 document.querySelector('#source-basis').textContent=archived?text('Retained archive · Not live','保留存档 · 非实时'):text('Synthetic fixture · Not live','合成测试样本 · 非实时');
 let content=task()==='brief'?briefComplete():task()==='explore'?exploreLenses():researchConnected();
 if(reviewState==='stale')content='<div class="state-banner"><strong>'+esc(text('This source snapshot is old.','来源快照已过期。'))+'</strong>'+esc(text('Inspect its dated evidence. It is not a current decision read.','可查看有日期依据的证据，但不能视为当前决策读数。'))+'</div>'+content;
 main.innerHTML=content;
 if(task()==='explore'){populateList(filters.leadership);populateRotation(filters.rotation);populateConfluence(filters.confluence);[['group-search','leadership'],['rotation-search','rotation'],['confluence-search','confluence']].forEach(([id,key])=>{const input=document.getElementById(id);if(input)input.value=filters[key];});}
}
document.addEventListener('click',event=>{
 const el=event.target.closest('button,a,[data-rotation]');if(!el)return;
 if(el.dataset.event){route('turns',{event:el.dataset.event,investigation:'turn'});return;}
 if(el.dataset.eventResearch){route('research',{event:el.dataset.eventResearch,investigation:'turn'});return;}
 if(el.dataset.rotation){const tag=el.tagName;route('moving',{rotation_group:el.dataset.rotation,investigation:'rotation'});Array.from(document.querySelectorAll('[data-rotation]')).find(x=>x.dataset.rotation===el.dataset.rotation&&x.tagName===tag)?.focus();return;}
 if(el.dataset.rotationResearch){route('research',{rotation_group:el.dataset.rotationResearch,investigation:'rotation'});return;}
 if(el.dataset.confluence){route('confluence',{confluence_group:el.dataset.confluence,investigation:'confluence'});Array.from(document.querySelectorAll('[data-confluence]')).find(x=>x.dataset.confluence===el.dataset.confluence)?.focus();return;}
 if(el.dataset.confluenceResearch){route('research',{confluence_group:el.dataset.confluenceResearch,investigation:'confluence'});return;}
 if(el.hasAttribute('data-source')||el.getAttribute('href')==='#sources'){event.preventDefault();sourceRecord();return;}
 if(el.dataset.group){navigate(el.dataset.group,'explore');return;}
 if(el.dataset.select){const query=document.querySelector('#group-search')?.value || '';navigate(el.dataset.select,'explore');const search=document.querySelector('#group-search');if(search){search.value=query;populateList(query);}Array.from(document.querySelectorAll('[data-select]')).find(x=>x.dataset.select===el.dataset.select)?.focus();return;}
 if(el.dataset.detail){navigate(selection().group_id,'explore',el.dataset.detail);document.querySelector('[data-detail="'+el.dataset.detail+'"]')?.focus();return;}
 if(el.hasAttribute('data-reset')){reviewState='source';stateControl.value='source';if(loadError)load();else render();}
});
document.addEventListener('input',event=>{if(event.target.id==='group-search'){filters.leadership=event.target.value;populateList(event.target.value);}if(event.target.id==='rotation-search'){filters.rotation=event.target.value;populateRotation(event.target.value);}if(event.target.id==='confluence-search'){filters.confluence=event.target.value;populateConfluence(event.target.value);}});
document.addEventListener('change',event=>{if(event.target.id==='rotation-universe')route('moving',{rotation_universe:event.target.value,rotation_group:null,investigation:'rotation'});if(event.target.id==='confluence-universe')route('confluence',{universe:event.target.value,confluence_group:null,investigation:'confluence'});});
document.addEventListener('keydown',event=>{
 const point=event.target.closest('g[data-rotation]');if(point&&['Enter',' '].includes(event.key)){event.preventDefault();route('moving',{rotation_group:point.dataset.rotation,investigation:'rotation'});return;}
 const tab=event.target.closest('[data-detail]');if(!tab||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
 const ids=['measure','record','companies'];let i=ids.indexOf(tab.dataset.detail);
 i=event.key==='Home'?0:event.key==='End'?2:(i+(event.key==='ArrowRight'?1:2))%3;
 event.preventDefault();navigate(selection().group_id,'moving',ids[i]);document.querySelector('[data-detail="'+ids[i]+'"]').focus();
});
document.querySelector('#theme-toggle').onclick=()=>{document.documentElement.dataset.theme=document.documentElement.dataset.theme==='light'?'dark':'light';render();};
document.querySelector('#lang-toggle').onclick=()=>{const lang=document.documentElement.dataset.lang==='en'?'zh':'en';document.documentElement.dataset.lang=lang;document.documentElement.lang=lang;render();};
stateControl.onchange=()=>{reviewState=stateControl.value;render();};
window.addEventListener('hashchange',()=>{if(location.hash==='#sources')sourceRecord();else render();});
window.addEventListener('popstate',render);
async function load() {
 loadError=null;render();
 try {
  const response=await fetch('../../tests/fixtures/leadership_rotation/measured_read_v1.json');
  if(!response.ok)throw new Error('Fixture unavailable');
  const raw=await response.json();
  if(raw.schema!=='leadership_rotation_context.measured_group_read/v1'||!Array.isArray(raw.groups)||!raw.generation||!raw.cohort)throw new Error('Fixture schema mismatch');
  data=raw;
 } catch(error){loadError=String(error.message || error);}
 try {
  const archiveResponse=await fetch('archive_sources.json');
  if(!archiveResponse.ok)throw new Error('Archive unavailable');
  archive=await archiveResponse.json();
  if(archive.reference_only!==true||!archive.rotation||!archive.confluence)throw new Error('Archive shape mismatch');
 } catch(error){archive=null;archiveError=String(error.message || error);}
 render();
}
load();
})();