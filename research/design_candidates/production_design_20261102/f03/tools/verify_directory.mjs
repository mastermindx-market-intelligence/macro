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

check('Fourteen return observations preserve null native-approval receipts',()=>{assert.equal(run('data.sessions.filter(s=>s.return_observation).length'),14);assert.ok(run('data.sessions.filter(s=>s.return_observation).every(s=>s.rig_receipt===null&&s.rig_state==="draft")'));});
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
  assert.equal(returns.length,7);
  assert.deepEqual(Array.from(returns,s=>s.id).sort(),['D04','D05','D07','D08B','D08C','D14','F02']);
 for(const s of returns){const o=s.return_observation;const rows=run(`referenceRows().filter(r=>r.claims.some(c=>c.board_id===${JSON.stringify(o.readme_board_id)}))`);assert.equal(rows.length,1);assert.equal(rows[0].key,o.readme_file_id+'/'+o.readme_page_id);}
});
check('D05 discovery separates provisional Read me, proposed page and retained reference',()=>{
 const file='01M6FAXA774QT1VRDMAG7DFQ2W';
 const s=run("sessionById('D05')"),o=s.return_observation;
 assert.equal(o.readme_board_id,'BML-0');assert.equal(o.readme_page_id,'p-3-0');assert.equal(o.candidate_page_id,'p-6-0');
 for(const [page,kind] of [['p-3-0','readme'],['p-6-0','candidate'],['p-1-0','retained']]){
  const rows=run(`referenceRows().filter(r=>r.key==='${file}/${page}')`);
  assert.equal(rows.length,1);assert.ok(rows[0].claims.some(c=>c.owner==='D05'&&c.kind===kind));
 }
 const readme=run("referenceView({view:'references',q:'BML-0',owner:'D05'},'bml-0')");
 assert.equal(readme.n,1);assert.ok(readme.html.includes(file+'/p-3-0'));assert.ok(!readme.html.includes(file+'/p-6-0'));
 const candidate=run(`referenceView({view:'references',q:'${file}/p-6-0',owner:'D05'},'${file.toLowerCase()}/p-6-0')`);
 assert.equal(candidate.n,1);assert.match(candidate.html,/unqualified comparison-return proposal/);assert.match(candidate.html,/Approval not established/);
 assert.ok(!run('data.artboards.some(b=>b.artboard_id==="BML-0"&&b.paper_file_id==="'+file+'")'));
});
check('Candidate board short and full identities resolve to their exact containing page',()=>{
 const file='01M6FAXA774QT1VRDMAG7DFQ2W',tuple=file+'/p-6-0/GPL-0';
 for(const q of ['GPL-0',tuple]){
  const ref=run(`referenceView({view:'references',q:${JSON.stringify(q)},owner:'D05'},${JSON.stringify(q.toLowerCase())})`);
  assert.equal(ref.n,1);assert.ok(ref.html.includes(file+'/p-6-0'));assert.match(ref.html,/GPL-0/);assert.match(ref.html,/Exact board URL not verified/);
  const assignment=run(`assignmentView({view:'assignments',q:${JSON.stringify(q)},owner:'D05'},${JSON.stringify(q.toLowerCase())})`);
  assert.equal(assignment.n,1);assert.match(assignment.html,/Observed candidate board/);assert.ok(assignment.html.includes(file+' / p-6-0 / GPL-0'));
  assert.doesNotMatch(assignment.html,/board=GPL-0/);assert.doesNotMatch(ref.html,/board=GPL-0|\/p-6-0\/GPL-0["#?]/);
 }
 for(const q of [file+'/p-3-0/GPL-0','WRONG/p-6-0/GPL-0',file+'/p-6-0/BML-0']){
  assert.equal(run(`referenceView({view:'references',q:'${q}',owner:'D05'},'${q.toLowerCase()}').n`),0);
  assert.equal(run(`assignmentView({view:'assignments',q:'${q}',owner:'D05'},'${q.toLowerCase()}').n`),0);
 }
 assert.equal(run("referenceView({view:'references',q:'GPL-0',owner:'D07'},'gpl-0').n"),0);
 const readme=file+'/p-3-0/BML-0';assert.equal(run(`referenceView({view:'references',q:'${readme}',owner:'D05'},'${readme.toLowerCase()}').n`),1);
});
check('Missing and null candidate board have identical legacy claims, search and rendering',()=>{
 const missing=run("JSON.parse(JSON.stringify(sessionById('D05')))");delete missing.return_observation.candidate_board_id;
 const explicit=JSON.parse(JSON.stringify(missing));explicit.return_observation.candidate_board_id=null;
 for(const expression of ['JSON.stringify(referenceRows([S],[]))','returnSearchText(S)','searchText(S)','returnEvidence(S)',"card(S,{view:'assignments',q:'GPL-0',owner:'D05'},'gpl-0')"]){
  assert.equal(run(expression.replace(/\bS\b/g,()=>JSON.stringify(missing))),run(expression.replace(/\bS\b/g,()=>JSON.stringify(explicit))));
 }
 assert.doesNotMatch(run(`returnSearchText(${JSON.stringify(explicit)})`),/candidate_board_id/);
});
check('Invalid candidate board suppresses only its candidate claim and never creates a locator',()=>{
 for(const value of ['', ' ', 'GPL-0\n', 'GPL/0', 'GPL_0', '../GPL-0', 'GPL-0#x', '<b>GPL-0</b>', '`GPL-0`', 0, true, [], {}]){
  const s=run("JSON.parse(JSON.stringify(sessionById('D05')))");s.return_observation.candidate_board_id=value;
  const claims=run(`referenceRows([${JSON.stringify(s)}],[]).flatMap(r=>r.claims)`);
  assert.equal(claims.filter(c=>c.kind==='candidate').length,0);assert.equal(claims.filter(c=>c.kind==='readme').length,1);assert.equal(claims.filter(c=>c.kind==='retained').length,1);
  assert.equal(run(`candidateIdentity(${JSON.stringify(s)})`),null);
  assert.doesNotMatch(run(`returnEvidence(${JSON.stringify(s)})`),/Candidate identity|board=GPL-0/);
 }
 for(const change of ['missing','mismatched','newline']){
  const s=run("JSON.parse(JSON.stringify(sessionById('D05')))");
  if(change==='missing'){s.candidate_ref=null;s.return_observation.candidate_file_id=null;s.return_observation.candidate_page_id=null;}
  if(change==='mismatched')s.return_observation.candidate_page_id='p-3-0';
  if(change==='newline')s.candidate_ref+='\n';
  assert.equal(run(`referenceRows([${JSON.stringify(s)}],[]).flatMap(r=>r.claims).filter(c=>c.kind==='candidate').length`),0);
 }
});
check('Equal candidate board IDs in separate files stay distinct; repeated claims deduplicate',()=>{
 const a=run("JSON.parse(JSON.stringify(sessionById('D05')))");a.return_observation.readme_url=null;a.return_observation.retained_reference_url=null;
 const b=JSON.parse(JSON.stringify(a));b.return_observation.candidate_file_id='OTHERFILE';b.candidate_ref='https://app.paper.design/file/OTHERFILE/p-6-0';
 const rows=run(`referenceRows(${JSON.stringify([a,b,a])},[])`);assert.equal(rows.length,2);assert.ok(rows.every(r=>r.claims.length===1));
 for(const file of ['01M6FAXA774QT1VRDMAG7DFQ2W','OTHERFILE'])assert.equal(rows.filter(r=>run(`returnedRefText(${JSON.stringify(r.claims[0])})`).includes((file+'/p-6-0/GPL-0').toLowerCase())).length,1);
 a.return_observation.readme_url=a.candidate_ref;a.return_observation.readme_file_id=a.return_observation.candidate_file_id;a.return_observation.readme_page_id='p-6-0';a.return_observation.readme_board_id='GPL-0';
 const same=run(`referenceRows([${JSON.stringify(a)},${JSON.stringify(a)}],[])`);assert.equal(same.length,1);assert.equal(same[0].claims.length,2);assert.ok(same[0].claims.some(c=>c.kind==='candidate'));assert.ok(same[0].claims.some(c=>c.kind==='readme'));
});
check('Candidate board detail and Back preserve context without inventing a focus target',()=>{
 const q='01M6FAXA774QT1VRDMAG7DFQ2W/p-6-0/GPL-0',st={view:'references',q,owner:'D05'};
 const h=run(`entry('D05',${JSON.stringify(st)})`),p=new URLSearchParams(h.slice(1));
 assert.equal(p.get('q'),q);assert.equal(p.get('owner'),'D05');assert.equal(p.get('view'),'references');assert.equal(p.get('page'),null);assert.equal(p.get('board'),null);
 const detail=run(`detail(sessionById('D05'),${JSON.stringify({...st,session:'D05',page:'',board:''})})`);
 assert.ok(detail.includes('01M6FAXA774QT1VRDMAG7DFQ2W / p-6-0 / GPL-0'));assert.match(detail,/Exact board URL not verified/);assert.doesNotMatch(detail,/id="board-01M6FAXA774QT1VRDMAG7DFQ2W-p-6-0-GPL-0"/);
 assert.ok(detail.includes(run(`hash(${JSON.stringify(st)})`).replaceAll('&','&amp;')));
});
check('Chinese candidate board discovery retains exact locator and page-navigation limit',()=>{
 run("lang='zh'");
 const a=run("assignmentView({view:'assignments',q:'GPL-0',owner:'D05'},'gpl-0')");assert.match(a.html,/已观察候选画板/);assert.match(a.html,/GPL-0/);
 const d=run("returnEvidence(sessionById('D05'))");assert.match(d,/候选身份/);assert.match(d,/精确画板 URL 尚未验证/);assert.ok(d.includes('01M6FAXA774QT1VRDMAG7DFQ2W / p-6-0 / GPL-0'));
 run("lang='en'");
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
const proposalRefs=[
 {id:'D04',file:'01M3NSZGE8JWN2EZCSF0DT05RM',page:'p-1D-0',board:'22UK-0',entryPage:'p-8-1',entryBoard:'N71-1'},
 {id:'D14',file:'01M3P1QEHS5XXQY85BJT6QR2E1',page:'p-B-0',board:'72Y-0',entryPage:'p-9-0',entryBoard:'1MO-0'},
 {id:'D06',file:'01M3NSZGE8JWN2EZCSF0DT05RM',page:'p-1E-0',board:'23MJ-0',entryPage:null,entryBoard:null},
 {id:'D22',file:'01M3NSZGE8JWN2EZCSF0DT05RM',page:'p-1F-0',board:'261Q-0',entryPage:null,entryBoard:null,sourceHead:'aca1d87854bfc643f5a01f0892b383ebc8baf6d6',phrase:'personal holdings'},
 {id:'D25',file:'01M32XYWDYSFTNDZVJKQ5QHT33',page:'p-8-0',board:'44J-0',entryPage:null,entryBoard:null,sourceHead:'aca1d87854bfc643f5a01f0892b383ebc8baf6d6',phrase:'guide return'}
];
for(const p of proposalRefs){
 const tuple=p.file+'/'+p.page+'/'+p.board;
 check(p.id+' proposal is searchable by short board and exact tuple in both views',()=>{
  for(const q of [p.board,tuple])for(const [view,fn] of [['references','referenceView'],['assignments','assignmentView']]){
   const r=run(`${fn}(${JSON.stringify({view,q,owner:p.id})},${JSON.stringify(q.toLowerCase())})`);
   assert.equal(r.n,1);assert.ok(r.html.includes(p.board));
   assert.doesNotMatch(r.html,new RegExp('board='+p.board+'|/'+p.page+'/'+p.board+'["#?]'));
   if(view==='references'){assert.ok(r.html.includes(p.file+'/'+p.page));assert.match(r.html,/Exact board URL not verified/);}
   else{assert.ok(r.html.includes(p.file+' / '+p.page+' / '+p.board));assert.match(r.html,/Observed candidate board/);}
  }
 });
 check(p.id+' proposal rejects mismatched file and page tuples',()=>{
  for(const q of ['WRONG/'+p.page+'/'+p.board,p.file+'/p-NOTTHIS-0/'+p.board])for(const [view,fn] of [['references','referenceView'],['assignments','assignmentView']])
   assert.equal(run(`${fn}(${JSON.stringify({view,q,owner:p.id})},${JSON.stringify(q.toLowerCase())}).n`),0);
 });
 check(p.id+' proposal exposes published source, draft status and exact identity in EN and ZH',()=>{
   const s=run(`sessionById('${p.id}')`);assert.equal(s.return_observation.source_head,p.sourceHead||'6324c7281ec91a343c5a8c78b3679f93b1cd11e6');
  for(const language of ['en','zh']){run(`lang='${language}'`);const detail=run(`returnEvidence(sessionById('${p.id}'))`);
   assert.ok(detail.includes(s.source_contract));assert.ok(detail.includes(p.file+' / '+p.page+' / '+p.board));assert.ok(detail.includes(s.status));assert.ok(detail.includes(s.return_observation.qualification));
   assert.equal(s.rig_state,'draft');assert.equal(s.rig_receipt,null);
  }run("lang='en'");
 });
 check(p.id+' proposal History and Back preserve search without inventing a board focus',()=>{
  for(const view of ['references','assignments']){
   const st={view,q:tuple,owner:p.id},h=run(`entry('${p.id}',${JSON.stringify(st)})`),params=new URLSearchParams(h.slice(1));
   assert.equal(params.get('view'),view);assert.equal(params.get('q'),tuple);assert.equal(params.get('owner'),p.id);assert.equal(params.get('session'),p.id);assert.equal(params.get('board'),null);assert.equal(params.get('page'),null);
   const detail=run(`detail(sessionById('${p.id}'),${JSON.stringify({...st,session:p.id,page:'',board:''})})`);
   assert.match(detail,/Back to results/);assert.ok(detail.includes('view='+view+'&amp;q='+encodeURIComponent(tuple)+'&amp;owner='+p.id));
  }
 });
}
check('D04 and D14 builder entries resolve to their own verified pages and boards',()=>{
 for(const p of proposalRefs.filter(p=>p.entryBoard)){
  const q=p.file+'/'+p.entryPage+'/'+p.entryBoard,r=run(`referenceView(${JSON.stringify({view:'references',q,owner:p.id})},${JSON.stringify(q.toLowerCase())})`);
  assert.equal(r.n,1);assert.ok(r.html.includes(p.file+'/'+p.entryPage));assert.ok(!r.html.includes(p.file+'/'+p.page));
  assert.equal(run(`sessionById('${p.id}').return_observation.readme_board_id`),p.entryBoard);
 }
 assert.equal(run("sessionById('D14').return_observation.readme_board_id"),'1MO-0');
 assert.ok(!run("referenceRows().some(r=>r.claims.some(c=>c.owner==='D14'&&c.kind==='readme'&&c.board_id==='5VN-0'))"));
});
check('D06 candidate remains discoverable without an invented Read me or retained original',()=>{
 const s=run("sessionById('D06')"),o=s.return_observation;
 for(const key of ['readme_url','readme_file_id','readme_page_id','readme_board_id','retained_reference_url'])assert.equal(o[key],null);
 const claims=run("referenceRows().flatMap(r=>r.claims).filter(c=>c.owner==='D06')");assert.equal(claims.filter(c=>c.kind==='candidate').length,1);assert.equal(claims.filter(c=>c.kind==='readme'||c.kind==='retained').length,0);
 assert.doesNotMatch(run("returnEvidence(sessionById('D06'))"),/Read me identity|1W4S-0|Retained original reference/);
});
for(const p of proposalRefs.filter(p=>p.sourceHead)){
 check(p.id+' supplementary pointer does not invent a full Read me or retained original',()=>{
  const s=run("sessionById('"+p.id+"')"),o=s.return_observation;
  for(const key of ['readme_url','readme_file_id','readme_page_id','readme_board_id','retained_reference_url'])assert.equal(o[key],null);
  const claims=run("referenceRows().flatMap(r=>r.claims).filter(c=>c.owner==='"+p.id+"')");
  assert.equal(claims.filter(c=>c.kind==='candidate').length,1);
  assert.equal(claims.filter(c=>c.kind==='readme'||c.kind==='retained').length,0);
  assert.doesNotMatch(run("returnEvidence(sessionById('"+p.id+"'))"),/Read me identity|Retained original reference/);
 });
 check(p.id+' source terminology finds the bounded proposal in both views',()=>{
  for(const [view,fn] of [['references','referenceView'],['assignments','assignmentView']]){
   const r=run(fn+"("+JSON.stringify({view,q:p.phrase,owner:p.id})+","+JSON.stringify(p.phrase)+")");
   assert.equal(r.n,1,p.id+' '+view+' '+p.phrase);
   assert.ok(r.html.includes(p.id));
   assert.ok(r.html.includes(run("esc(sessionById('"+p.id+"').source_contract_label)")));
   if(view==='references')assert.ok(r.html.includes(p.board));
   else assert.ok(r.html.includes('session='+p.id));
  }
 });
}
for(const [id,q] of [['D22','provisional valuation'],['D25','horizon wording']]){
 check(id+' visible source label or status terms are searchable across both views',()=>{
  for(const [view,fn] of [['references','referenceView'],['assignments','assignmentView']]){
   const r=run(fn+"("+JSON.stringify({view,q,owner:id})+","+JSON.stringify(q)+")");
   assert.equal(r.n,1,id+' '+view+' '+q);
  }
 });
}
check('Observed source labels remain escaped in assignment and reference results',()=>{
 const original=run("sessionById('D25').source_contract_label");
 const label='<img src=x onerror=alert(1)> Guide return';
 run("sessionById('D25').source_contract_label="+JSON.stringify(label));
 try{
  for(const fn of ['assignmentView','referenceView']){
   const r=run(fn+"({owner:'D25',q:'guide return'},'guide return')");
   assert.equal(r.n,1);assert.ok(r.html.includes('&lt;img src=x onerror=alert(1)&gt; Guide return'));
   assert.ok(!r.html.includes(label));
  }
 }finally{run("sessionById('D25').source_contract_label="+JSON.stringify(original));}
});
check('EN and ZH reference views render against recursively frozen source data',()=>{
 run("(function freeze(x){if(x&&typeof x==='object'&&!Object.isFrozen(x)){Object.freeze(x);for(const v of Object.values(x))freeze(v);}})(data)");
 const before=run('JSON.stringify(data)');
 run("referenceView({view:'references',q:'',owner:''},'');lang='zh';referenceView({view:'references',q:'',owner:''},'');lang='en'");
 assert.equal(run('JSON.stringify(data)'),before);
});

console.log(JSON.stringify({kind:'source_logic_regression_probes_not_browser_tests',status:'PASS',tests,limitations:['No rendering, browser interaction, screen-reader, touch, focus-visibility, contrast, zoom or performance acceptance.']},null,2));
