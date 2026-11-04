// Source-logic regression probes. This is not a browser, layout or accessibility test.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const root=process.argv[2]||'f03-work/deliverable';
const html=fs.readFileSync(root+'/directory.html','utf8');
const payload=html.match(/<script id="f03-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script=html.match(/<script>\n([\s\S]*?)<\/script>/)[1];
const elements=new Map(),events={};
function element(id){if(!elements.has(id))elements.set(id,{id,value:'',innerHTML:'',textContent:'',hidden:false,attrs:{},listeners:{},setAttribute(k,v){this.attrs[k]=v;},addEventListener(k,v){this.listeners[k]=v;},focus(){this.focused=true;},scrollIntoView(){this.scrolled=true;}});return elements.get(id);}
element('f03-data').textContent=payload;
const location={hash:''};
const context=vm.createContext({URLSearchParams,Map,console,location,history:{replaceState(_a,_b,h){location.hash=h;}},document:{documentElement:{dataset:{theme:'dark'},lang:'en'},getElementById:element,addEventListener(k,v){events[k]=v;}},window:{addEventListener(k,v){events[k]=v;},scrollTo(){}}});
vm.runInContext(script,context);
const run=x=>vm.runInContext(x,context),tests=[];
function check(name,fn){fn();tests.push({name,result:'PASS'});}
check('Canonical identity count is separate from nine null-ID deltas',()=>{assert.equal(run('data.routes.length'),348);assert.equal(run('new Set(data.routes.map(r=>r.canonical_registry_id)).size'),348);assert.equal(run('data.source_deltas.filter(d=>d.canonical_registry_id===null).length'),9);});
check('Exact held board search exposes the matched board and role',()=>{const r=run("assignmentView({view:'assignments',q:'1B5H-0',owner:''},'1b5h-0')");assert.equal(r.n,1);assert.match(r.html,/1B5H-0/);assert.match(r.html,/Held/);assert.match(r.html,/board=1B5H-0/);});
check('Reference search and assignment filter include all D17 WTI exceptions',()=>{assert.equal(run("referenceView({view:'references',owner:'',q:'D17'},'d17').n"),4);assert.equal(run("referenceView({view:'references',owner:'D17',q:''},'').n"),4);});
check('Detail navigation preserves originating view, query and owner',()=>{const h=run("entry('D07',{view:'references',q:'1B5H-0',owner:'D07'})");const p=new URLSearchParams(h.slice(1));assert.equal(p.get('view'),'references');assert.equal(p.get('q'),'1B5H-0');assert.equal(p.get('owner'),'D07');const d=run("detail(sessionById('D07'),{view:'references',q:'1B5H-0',owner:'D07',session:'D07',page:'',board:''})");assert.match(d,/Back to results/);assert.match(d,/view=references&amp;q=1B5H-0&amp;owner=D07/);assert.match(d,/<details open>/);});
check('Skip action moves focus without changing router state',()=>{location.hash='#view=routes&q=options&owner=D08';let prevented=false;element('skip').listeners.click({preventDefault(){prevented=true;}});assert.ok(prevented);assert.equal(location.hash,'#view=routes&q=options&owner=D08');assert.ok(element('main').focused);});
check('Exact board detail contains anchor and focus target',()=>{location.hash='#view=references&session=D07&page=01M3NSZGE8JWN2EZCSF0DT05RM%2Fp-Q-0&board=1B5H-0&q=1B5H-0';run('render(true)');const id='board-01M3NSZGE8JWN2EZCSF0DT05RM-p-Q-0-1B5H-0';assert.ok(element(id).focused);assert.match(element('content').innerHTML,new RegExp('id="'+id+'"'));});
check('Equity replay exposes integration D08 and design D08D',()=>{const s=run("deltaRow(data.source_deltas.find(d=>d.route==='/options/equity-replay'))");assert.match(s,/Integration/);assert.match(s,/Design slice/);assert.match(s,/session=D08(?:&|\")/);assert.match(s,/session=D08D(?:&|\")/);});
check('Recorded redirects and Returns history are exposed without approval',()=>{const s=run("detail(sessionById('D07'),{view:'assignments',q:'Returns',owner:'',session:'D07',page:'',board:''})");assert.match(s,/Recorded predecessor/);assert.match(s,/p-15-0/);assert.match(s,/1B5H-0/);assert.match(s,/No approved candidate established/);});
check('Observed historical China role overrides prior candidate classification',()=>{assert.equal(run("data.pages.find(p=>p.paper_file_id==='01M2WGNCX9475G79JRKJTCM08P'&&p.paper_page_id==='p-7-1').role"),'historical');assert.equal(run("data.pages.find(p=>p.paper_file_id==='01M2WGNCX9475G79JRKJTCM08P'&&p.paper_page_id==='p-7-1').baseline_role"),'candidate_unqualified');});
check('Original Earnings and Hub archives link to recorded destinations',()=>{for(const id of ['p-1B-0','p-1A-0'])assert.equal(run(`data.pages.find(p=>p.paper_file_id==='01M2WGNCX9475G79JRKJTCM08P'&&p.paper_page_id==='${id}').recorded_successors[0].kind`),'recorded_original_archive');});
check('Inventory return is bounded to local inventory with its exact state',()=>{const s=run("detail(sessionById('D07'),{view:'routes',q:'',owner:'',session:'D07',page:'',board:'',inventory:'q=NVDA&family=macro%3Astocks_family&kind=included_legacy&page=2'})");assert.match(s,/href="inventory.html#q=NVDA&amp;family=macro%3Astocks_family&amp;kind=included_legacy&amp;page=2"/);});
check('Mixed historical and held pages surface warnings',()=>{assert.match(run("warnings(data.pages.find(p=>p.paper_file_id==='01M2WGNCX9475G79JRKJTCM08P'&&p.paper_page_id==='p-7-1'))"),/Historical/);assert.match(run("warnings(data.pages.find(p=>p.paper_file_id==='01M3NSZGE8JWN2EZCSF0DT05RM'&&p.paper_page_id==='p-Q-0'))"),/Held/);});
check('Family routes expose concrete-member index, never wildcard live URLs',()=>{const s=run("routeTable(data.routes.filter(r=>r.canonical_registry_id==='macro:stocks_family'),{view:'routes'})");assert.match(s,/inventory.html#family=macro:stocks_family/);assert.doesNotMatch(s,/href="\/stocks\//);});
check('Seven unregistered documents are individual gaps with design responsibility',()=>{assert.equal(run('data.inventory_gaps.length'),7);const s=run("changesView({view:'changes',owner:'',q:''},'').html");for(const path of ['/gmi.html','/gmi-states.html','/expectation_surface.html'])assert.ok(s.includes(path));});
check('Chinese chrome retains language-marked source fields and labels',()=>{run("lang='zh';render()");assert.equal(context.document.documentElement.lang,'zh-CN');assert.equal(element('locale').attrs['aria-label'],'切换至英语');assert.match(element('content').innerHTML,/lang="en"/);run("lang='en';render()");});
check('Missing-result state links alternative scopes and member lookup',()=>{const s=run("empty({view:'references',q:'/options/equity-replay',owner:''})");assert.match(s,/Search canonical routes and deltas/);assert.match(s,/inventory.html#q=/);});
check('User search values are escaped and history encoded',()=>{assert.equal(run("esc('<script>')"),'&lt;script&gt;');assert.match(run("hash({view:'references',q:'a&b#c'})"),/q=a%26b%23c/);});
check('Fresh document execution honors an exact saved board URL',()=>{for(const e of elements.values()){e.focused=false;e.scrolled=false;}location.hash='#view=references&session=D07&page=01M3NSZGE8JWN2EZCSF0DT05RM%2Fp-Q-0&board=1B5H-0';vm.runInNewContext(script,{URLSearchParams,Map,console,location,history:context.history,document:context.document,window:context.window});assert.ok(element('board-01M3NSZGE8JWN2EZCSF0DT05RM-p-Q-0-1B5H-0').focused);assert.ok(element('board-01M3NSZGE8JWN2EZCSF0DT05RM-p-Q-0-1B5H-0').scrolled);});
const inventory=fs.readFileSync(root+'/inventory.html','utf8');const compact=JSON.parse(inventory.match(/<script type="application\/json" id="members">([\s\S]*?)<\/script>/)[1]);
check('Default inventory row retains an explicit nonempty return fragment',()=>{assert.ok(inventory.includes("encodeURIComponent(p.toString()||'page=0')"));const s=run("detail(sessionById('D07'),{view:'routes',q:'',owner:'',session:'D07',page:'',board:'',inventory:'page=0'})");assert.match(s,/href="inventory.html#page=0"/);});
check('Complete member index preserves included and excluded rows',()=>{assert.equal(compact.length,14025);assert.equal(compact.filter(x=>x[1]).length,14014);assert.equal(compact.filter(x=>x[2]==='included_legacy').length,13989);assert.equal(compact.filter(x=>x[2]==='unregistered').length,7);assert.equal(new Set(compact.map(x=>x[0])).size,14025);});

check('Eight return observations preserve null native-approval receipts',()=>{assert.equal(run('data.sessions.filter(s=>s.return_observation).length'),8);assert.ok(run('data.sessions.filter(s=>s.return_observation).every(s=>s.rig_receipt===null&&s.rig_state==="draft")'));});
check('D08B and D08C expose direct exact candidate, Read me and source links',()=>{for(const [id,candidate,readme,pin] of [['D08B','p-12-0','p-14-0','a3356474cebbdd88e6448e05ffc3d2e44faa5ca6'],['D08C','p-13-0','p-15-0','291f21aa8e9d757466412549a8d6537d889ab4d8']]){const s=run(`returnEvidence(sessionById('${id}'))`);assert.ok(s.includes('01M3NSZGE8JWN2EZCSF0DT05RM/'+candidate));assert.ok(s.includes('01M3NSZGE8JWN2EZCSF0DT05RM/'+readme));assert.ok(s.includes('/blob/'+pin+'/'));assert.ok(s.includes(id+' returned source/build contract'));assert.doesNotMatch(s,/Open F03 contract/);}});
check('Source-only D08A and D08D remain without admitted native candidates',()=>{for(const id of ['D08A','D08D']){assert.equal(run(`sessionById('${id}').candidate_ref`),null);const s=run(`returnEvidence(sessionById('${id}'))`);assert.match(s,/not admitted/);assert.match(s,/Retained original reference/);assert.match(s,/No approved candidate established/);}});
check('D08 entry provides all four owner contracts without a third directory choice',()=>{const s=run("sliceEvidence(sessionById('D08'))");for(const id of ['D08A','D08B','D08C','D08D'])assert.ok(s.includes(run(`sessionById('${id}').source_contract`)));assert.match(s,/Design packages are not route records/);});
check('New exact Read me board identity is searchable without mutating census',()=>{const r=run("assignmentView({view:'assignments',q:'1PVF-0',owner:''},'1pvf-0')");assert.equal(r.n,1);assert.match(r.html,/D08B/);assert.equal(run("data.artboards.filter(b=>b.artboard_id==='1PVF-0').length"),0);});
check('Changes view exposes immutable return observations and current resource gate',()=>{const s=run("changesView({view:'changes',owner:'',q:''},'').html");assert.match(s,/a3356474cebbdd88e6448e05ffc3d2e44faa5ca6/);assert.match(s,/Cross-file resource operations remain unqualified/);assert.doesNotMatch(s,/Live catalog not accepted/);});
check('Current directory effects do not imply cross-file action application',()=>{assert.ok(run('data.metadata.directory.paper_mutations')>0);assert.match(run("detail(sessionById('F03'),{view:'assignments',q:'',owner:'',session:'F03'})"),/301 cross-file organization actions remain NOT_DISPATCHED/);});
check('Chinese returned-evidence chrome retains exact source identities',()=>{run("lang='zh'");const s=run("returnEvidence(sessionById('D08B'))");assert.match(s,/已返回的合同／资料包/);assert.match(s,/1PVF-0/);assert.match(s,/a3356474cebbdd88e6448e05ffc3d2e44faa5ca6/);assert.match(s,/lang="en"/);run("lang='en'");});
check('Evidence links reject executable or non-evidence URL schemes',()=>{for(const url of ['javascript:alert(1)','data:text/html,x','https://example.com/x','//app.paper.design/x'])assert.doesNotMatch(run(`evidenceLink(${JSON.stringify(url)},'label')`),/<a /);assert.match(run("evidenceLink('CONTRACT.md','F03 <contract>')"),/F03 &lt;contract&gt;/);});
check('Source return refresh does not erase query or owner context',()=>{const h=run("entry('D08B',{view:'assignments',q:'1PVF-0',owner:'D08B'})");const p=new URLSearchParams(h.slice(1));assert.equal(p.get('q'),'1PVF-0');assert.equal(p.get('owner'),'D08B');assert.equal(p.get('session'),'D08B');});


check('Candidate and Read me compound identities use their own pages',()=>{for(const [id,candidate,readme,board] of [['D08B','p-12-0','p-14-0','1PVF-0'],['D08C','p-13-0','p-15-0','1S0R-0']]){const s=run(`returnEvidence(sessionById('${id}'))`);assert.ok(s.includes('Candidate identity: <code>01M3NSZGE8JWN2EZCSF0DT05RM / '+candidate+'</code>'));assert.ok(s.includes('Read me identity: <code>01M3NSZGE8JWN2EZCSF0DT05RM / '+readme+' / '+board+'</code>'));assert.ok(!s.includes(candidate+' / '+board));}});
check('Current D08B/C Read me links are not retained-original claims',()=>{for(const id of ['D08B','D08C']){assert.equal(run(`sessionById('${id}').return_observation.retained_reference_url`),null);assert.doesNotMatch(run(`returnEvidence(sessionById('${id}'))`),/Retained original reference/);}});
check('Evidence links reject normalization outside the immutable source pin',()=>{const head='a3356474cebbdd88e6448e05ffc3d2e44faa5ca6';for(const tail of ['../../blob/main/README.md','x/../README.md','./README.md'])assert.doesNotMatch(run(`evidenceLink('https://github.com/mastermindx-market-intelligence/macro/blob/${head}/${tail}','pin')`),/<a /);});

check('Paper-reference search finds returned Read me board IDs with exact page and contract',()=>{
 for(const [id,board,page,wrongPage] of [['D08B','1PVF-0','p-14-0','p-12-0'],['D08C','1S0R-0','p-15-0','p-13-0']]){
  const r=run(`referenceView({view:'references',q:'${board}',owner:''},'${board.toLowerCase()}')`);
  assert.equal(r.n,1,board+' must be discoverable in Paper references');
  assert.ok(r.html.includes('01M3NSZGE8JWN2EZCSF0DT05RM/'+page));
  assert.ok(!r.html.includes('01M3NSZGE8JWN2EZCSF0DT05RM/'+wrongPage));
  assert.ok(r.html.includes(run(`sessionById('${id}').source_contract`)));
  assert.match(r.html,new RegExp(board));assert.match(r.html,/Read me/);
 }
});
check('Reference search accepts full returned URLs and exact compound identities',()=>{
 for(const page of ['p-14-0','p-15-0'])for(const prefix of ['','https://app.paper.design/file/']){
  const q=prefix+'01M3NSZGE8JWN2EZCSF0DT05RM/'+page;
  assert.equal(run(`referenceView({view:'references',owner:'',q:${JSON.stringify(q)}},${JSON.stringify(q.toLowerCase())}).n`),1);
 }
 const q='01M2WGNCX9475G79JRKJTCM08P/p-1H-0';
 assert.equal(run(`referenceView({view:'references',owner:'',q:'${q}'},'${q.toLowerCase()}').n`),1);
});
check('Returned reference owner filtering and result links preserve query context',()=>{
 const r=run("referenceView({view:'references',q:'1PVF-0',owner:'D08B'},'1pvf-0')");
 assert.equal(r.n,1);assert.match(r.html,/view=references&amp;q=1PVF-0&amp;owner=D08B&amp;session=D08B/);
 assert.equal(run("referenceView({view:'references',q:'1PVF-0',owner:'D08C'},'1pvf-0').n"),0);
});
check('Same-page candidate and Read me roles are retained without duplicate page results',()=>{
 const q='01M2WGNCX9475G79JRKJTCM08P/p-27-0';
 const r=run(`referenceView({view:'references',owner:'F01',q:'${q}'},'${q.toLowerCase()}')`);
 assert.equal(r.n,1);assert.match(r.html,/Observed candidate/);assert.match(r.html,/Read me/);
 assert.equal(run('new Set(referenceRows().map(r=>r.key)).size'),run('referenceRows().length'));
});
check('Retained-only and no-native returns never become native candidates',()=>{
 for(const id of ['D08','D08A','D08D'])assert.equal(run(`referenceRows().flatMap(r=>r.claims).filter(c=>c.owner==='${id}'&&c.kind==='candidate').length`),0);
 const q='01M2WGNCX9475G79JRKJTCM08P/p-25-0';
 const r=run(`referenceView({view:'references',owner:'D08A',q:'${q}'},'${q.toLowerCase()}')`);
 assert.equal(r.n,1);assert.match(r.html,/Retained original reference/);assert.match(r.html,/not an approved candidate/);
});
check('Reference projection leaves all frozen data and approval fields unchanged',()=>{
 const before=run('JSON.stringify([data.pages,data.artboards,data.sessions,data.routes,data.source_deltas])');
 run("referenceView({view:'references',q:'',owner:''},'')");
 assert.equal(run('JSON.stringify([data.pages,data.artboards,data.sessions,data.routes,data.source_deltas])'),before);
 assert.equal(run('data.pages.length'),301);assert.equal(run('data.artboards.length'),2450);
 assert.ok(run('data.sessions.filter(s=>s.return_observation).every(s=>s.rig_receipt===null)'));
});
check('Returned references disclose observed source time and unresolved qualification',()=>{
 const r=run("referenceView({view:'references',q:'1PVF-0',owner:''},'1pvf-0')");
 assert.match(r.html,/2026-11-04T02:38:34Z/);assert.match(r.html,/a3356474cebbdd88e6448e05ffc3d2e44faa5ca6/);
 assert.match(r.html,/not a new native approval/);assert.match(r.html,/Approval not established/);
});
check('Chinese returned-reference labels retain exact identity and source contracts',()=>{
 run("lang='zh'");const r=run("referenceView({view:'references',q:'1S0R-0',owner:'D08C'},'1s0r-0')");
 assert.equal(r.n,1);assert.match(r.html,/设计说明/);assert.match(r.html,/1S0R-0/);
 assert.ok(r.html.includes(run("sessionById('D08C').source_contract")));run("lang='en'");
});
check('Reference projection rejects mismatched identity tuples and untrusted Paper URLs',()=>{
 const s=run("JSON.parse(JSON.stringify(sessionById('D08B')))");
 for(const bad of ['javascript:alert(1)','https://example.com/file/ABC/p-1-0','https://app.paper.design/file/ABC/p-1-0/../p-2-0']){
  s.candidate_ref=bad;s.return_observation.readme_url=null;s.return_observation.retained_reference_url=null;
  assert.equal(run(`referenceRows([${JSON.stringify(s)}],[]).length`),0);
 }
 s.candidate_ref='https://app.paper.design/file/01M3NSZGE8JWN2EZCSF0DT05RM/p-13-0';
 assert.equal(run(`referenceRows([${JSON.stringify(s)}],[]).length`),0);
});
check('Compound page identity keeps equal page IDs in different files distinct',()=>{
 const pages=run('data.pages.filter(p=>p.paper_page_id==="p-1-0")');
 assert.ok(pages.length>1);assert.equal(run(`referenceRows([],${JSON.stringify(pages)}).length`),pages.length);
});
check('Repeated return records deduplicate claims without erasing distinct roles',()=>{
 const s=run("JSON.parse(JSON.stringify(sessionById('F01')))");
 assert.equal(run(`referenceRows([${JSON.stringify(s)},${JSON.stringify(s)}],[]).length`),1);
 assert.equal(run(`referenceRows([${JSON.stringify(s)},${JSON.stringify(s)}],[])[0].claims.length`),2);
});
check('New reference controls include narrow stacking and touch-target source rules',()=>{
 assert.match(html,/\.reference-row\{flex-direction:column;gap:12px\}/);
 assert.match(html,/\.reference-return summary\{[^}]*min-height:44px/);
 assert.match(html,/\.reference-contracts a\{[^}]*min-height:44px/);
});

check('All concrete returned Read me board IDs resolve only to their own page',()=>{
 const returns=run('data.sessions.filter(s=>s.return_observation?.readme_board_id)');
 assert.equal(returns.length,4);
 for(const s of returns){const o=s.return_observation;const rows=run(`referenceRows().filter(r=>r.claims.some(c=>c.board_id===${JSON.stringify(o.readme_board_id)}))`);assert.equal(rows.length,1);assert.equal(rows[0].key,o.readme_file_id+'/'+o.readme_page_id);}
});
check('Returned status and timestamp injection stays escaped and malicious contract stays inert',()=>{
 const c=run("JSON.parse(JSON.stringify(referenceRows().find(r=>r.claims.some(c=>c.owner==='D08B')).claims[0]))");
 c.status='<img src=x onerror=alert(1)>';c.qualification='<script>alert(1)</script>';c.source_head='<svg onload=alert(1)>';
 c.observed_at='2026-11-04T00:00:00Z\" onmouseover=\"alert(1)';c.source_contract='javascript:alert(1)';
 const s=run(`referenceReturnEvidence([${JSON.stringify(c)}],{view:'references'})`);
 assert.doesNotMatch(s,/<(?:img|script|svg)\b|href="javascript:|datetime="[^"]*" onmouseover=/);
 assert.match(s,/&lt;img/);assert.match(s,/&lt;script/);assert.match(s,/&quot; onmouseover=&quot;/);assert.match(s,/Destination not established/);
});
const pendingMeta={directory:{paper_unresolved_operation_ids:['synthetic-pending-operation'],paper_unresolved_effects:1},native_effect_observed_at:'2026-11-04T00:00:00Z'};
check('Synthetic pending native effect is exposed as a snapshot, not approval or a retry action',()=>{
 const ids=run('data.metadata.directory.paper_unresolved_operation_ids');
 const s=run(`effectWarning(${JSON.stringify(pendingMeta)})`);assert.ok(s.includes('synthetic-pending-operation'));assert.match(s,/outcome unconfirmed/);assert.match(s,/not a live service monitor/);assert.doesNotMatch(s,/<button/);
 assert.equal(element('effect-warning').hidden,!ids.length);assert.match(html,/id="effect-warning"[^>]*role="note"/);
});
check('Zero-unknown fixture produces no stale warning or invented pending operation',()=>{
 assert.equal(run("effectWarning({directory:{paper_unresolved_operation_ids:[],paper_unresolved_effects:0}})"),'');
});
check('Effect warning visibility follows the actual ledger on detail views without changing router context',()=>{
 location.hash='#view=references&q=1PVF-0&owner=D08B&session=D08B';run('render()');
 assert.equal(element('overview').hidden,true);assert.equal(element('effect-warning').hidden,!run('data.metadata.directory.paper_unresolved_operation_ids.length'));
 assert.equal(location.hash,'#view=references&q=1PVF-0&owner=D08B&session=D08B');
});
check('Chinese synthetic pending-effect warning preserves the exact operation and evidence link',()=>{
 run("lang='zh'");const warning=run(`effectWarning(${JSON.stringify(pendingMeta)})`);assert.match(warning,/操作结果尚未确认/);
 assert.match(warning,/synthetic-pending-operation/);
 assert.match(warning,/href="paper\/native-progress.json"/);run("lang='en';render()");
});
check('Pending operation display rejects text and timestamp injection',()=>{
 const s=run(`effectWarning(${JSON.stringify({directory:{paper_unresolved_operation_ids:['<img src=x onerror=alert(1)>']},native_effect_observed_at:'" onload="x'})})`);
 assert.doesNotMatch(s,/<img|datetime="" onload=/);assert.match(s,/&lt;img/);assert.match(s,/&quot; onload=&quot;/);
});
check('Later structural reads expose all 106 pages and 1837 compound board identities',()=>{
 assert.equal(run('data.page_observations.length'),106);assert.equal(run('observedBoards.length'),1837);
 assert.equal(run('new Set(observedBoards.map(boardKey)).size'),1837);
 assert.equal(run('data.pages.length'),301);assert.equal(run('data.artboards.length'),2450);
 assert.equal(run("referenceView({view:'references',q:'structural observation',owner:'F03'},'structural observation').n"),106);
 assert.equal(run("referenceView({view:'references',q:'structural observation',owner:'D16'},'structural observation').n"),0);
});
check('Supplemental tail boards are searchable through their exact file/page/board identity',()=>{
 for(const q of ['01M5HVW84WZFE62DREB6QB9ZDJ/p-N-1/6NKK-0','01M3NQQ5KHTEZ50AGPT3RAD4BN/p-12-3/5F9X-0']){
  const st={view:'references',q,owner:'F03'};
  const r=run(`referenceView(${JSON.stringify(st)},${JSON.stringify(q.toLowerCase())})`);
  assert.equal(r.n,1);assert.match(r.html,/Initial list was capped/);assert.match(r.html,/Later structural observation/);
  const a=run(`assignmentView(${JSON.stringify({...st,view:'assignments'})},${JSON.stringify(q.toLowerCase())})`);
  assert.equal(a.n,1);assert.match(a.html,/session=F03/);assert.doesNotMatch(a.html,/session=(?:null|undefined)/);
 }
});
check('Repeated short board IDs do not collapse copied files or inherit product ownership',()=>{
 const all=run('observedBoards');const b=all.find(b=>all.some(x=>x.artboard_id===b.artboard_id&&x.paper_file_id!==b.paper_file_id));
 assert.ok(b);const same=all.filter(x=>x.artboard_id===b.artboard_id);assert.ok(same.length>1);
 for(const x of same){const q=x.paper_file_id+'/'+x.paper_page_id+'/'+x.artboard_id;assert.equal(run(`referenceView({view:'references',q:${JSON.stringify(q)},owner:''},${JSON.stringify(q.toLowerCase())}).n`),1);}
 assert.ok(run('observedBoards.every(b=>b.product_owner===null&&b.page_custodian==="F03"&&b.observed_role_labels.length===0)'));
 const owner=run(`boardOwner(${JSON.stringify(b)})`);assert.match(owner,/Not established/);assert.match(owner,/Organization steward/);
});
check('Observed board navigation preserves query, owner, exact page, focus and Back context',()=>{
 const q='01M5HVW84WZFE62DREB6QB9ZDJ/p-N-1/6NKK-0';
 const b=run(`observedBoards.find(b=>b.paper_file_id+'/'+b.paper_page_id+'/'+b.artboard_id==='${q}')`);
 const st={view:'references',q,owner:'F03'};
 const h=run(`entry('F03',${JSON.stringify(st)},${JSON.stringify(b)})`);const p=new URLSearchParams(h.slice(1));
 assert.equal(p.get('q'),q);assert.equal(p.get('owner'),'F03');assert.equal(p.get('page'),b.paper_file_id+'/'+b.paper_page_id);assert.equal(p.get('board'),b.artboard_id);
 location.hash=h;run('render(true)');assert.ok(element('board-'+b.paper_file_id+'-'+b.paper_page_id+'-'+b.artboard_id).focused);
 const s=element('content').innerHTML;assert.match(s,/Back to results/);assert.ok(s.includes('q='+encodeURIComponent(q)+'&amp;owner=F03'));assert.match(s,/Exact board URL not verified/);
});
check('Zero-artboard observations remain successful reads without becoming completion or disposal',()=>{
 const pages=run('data.page_observations.filter(p=>p.artboard_count===0)');assert.equal(pages.length,12);
 for(const p of pages){const q=p.file_id+'/'+p.page_id;const r=run(`referenceView({view:'references',q:'${q}',owner:''},'${q.toLowerCase()}')`);assert.equal(r.n,1);assert.match(r.html,/0 artboards observed/);assert.match(r.html,/full-content comparison and safe disposal are not established/);}
});
check('Provider data-loss warning stays on the exact duplicate file and does not spread to other copies',()=>{
 for(const [file,page,warn] of [['01M3NQQ5KHTEZ50AGPT3RAD4BN','p-12-3',true],['01M5HVW84WZFE62DREB6QB9ZDJ','p-N-1',false]]){
  const q=file+'/'+page;const r=run(`referenceView({view:'references',q:'${q}',owner:''},'${q.toLowerCase()}')`);
  assert.equal(r.n,1);assert.equal(r.html.includes('Further changes will result in data loss'),warn);
  if(warn)assert.match(r.html,/No edit was attempted/);
 }
});
check('Coverage row reports completed metadata discovery and links the exact observation scope',()=>{
 const r=run("structuralChange({view:'changes',q:'',owner:''})");assert.match(r.name,/106 of 106/);assert.match(r.text,/1837/);assert.match(r.text,/0 pages remain without structural reads/);
 const p=new URLSearchParams(r.url.slice(1));assert.equal(p.get('view'),'references');assert.equal(p.get('owner'),'F03');assert.equal(p.get('q'),'structural observation');
});
check('Chinese structural chrome preserves exact observed identities and cautious ownership',()=>{
 run("lang='zh'");const q='01M5HVW84WZFE62DREB6QB9ZDJ/p-N-1/6NKK-0';
 const r=run(`referenceView({view:'references',q:'${q}',owner:'F03'},'${q.toLowerCase()}')`);
 assert.equal(r.n,1);assert.match(r.html,/结构观察/);assert.match(r.html,/基线仅列出/);assert.match(r.html,/产品负责人/);assert.match(r.html,/6NKK-0/);run("lang='en'");
});
check('Observed names and provider warnings are escaped without executable markup',()=>{
 const q='01M5HVW84WZFE62DREB6QB9ZDJ/p-N-1';
 const old=run(`JSON.parse(JSON.stringify(observationMap.get('${q}')))`);const bad={...old,file_name:'<img src=x onerror=alert(1)>',page_name:'<svg onload=alert(1)>',warnings:['<script>alert(1)</script>'],completed_at_utc:'" onload="x'};
 run(`observationMap.set('${q}',${JSON.stringify(bad)})`);
 try{const s=run(`structuralEvidence(data.pages.find(p=>pageKey(p)==='${q}'))`);assert.doesNotMatch(s,/<(?:img|svg|script)\b|datetime="" onload=/);assert.match(s,/&lt;img/);assert.match(s,/&lt;script/);assert.match(s,/&quot; onload=&quot;/);}finally{run(`observationMap.set('${q}',${JSON.stringify(old)})`);}
});
check('EN and ZH reference views render against recursively frozen source data',()=>{
 run("(function freeze(x){if(x&&typeof x==='object'&&!Object.isFrozen(x)){Object.freeze(x);for(const v of Object.values(x))freeze(v);}})(data)");
 const before=run('JSON.stringify(data)');
 run("referenceView({view:'references',q:'',owner:''},'');lang='zh';referenceView({view:'references',q:'',owner:''},'');lang='en'");
 assert.equal(run('JSON.stringify(data)'),before);
});

console.log(JSON.stringify({kind:'source_logic_regression_probes_not_browser_tests',status:'PASS',tests,limitations:['No rendering, browser interaction, screen-reader, touch, focus-visibility, contrast, zoom or performance acceptance.']},null,2));
