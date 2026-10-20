'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const ui=require('../templates/government-revenue-theme-context.js'),fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/theme_public_disclosure.json')));
function copy(){return structuredClone(fixture);}
function host(){return {innerHTML:'',querySelectorAll(){return[]},querySelector(){return null}};}
function env(lang='en'){global.location={href:'https://local.test/government_revenue.html?issuer=LHX&mode=programs&ticker=IRDM&agency=Navy&campaign=r#source'};global.document={activeElement:null,documentElement:{getAttribute(){return lang}}};global.addEventListener=()=>{};}
test('actual frozen public disclosure is accepted with independent gptd identity',()=>assert.equal(ui.validate(copy()),true));
test('closed contract clocks, authority, source private fields and unknown states fail closed',()=>{for(const mutate of [x=>delete x.content_id,x=>x.contract='government_program_theme_context.v1',x=>x.as_of='bad',x=>x.authority.can_rank=true,x=>x.authority.can_trade=true,x=>x.themes[0].pi_name='private',x=>x.themes[0].sources[0].address1='private',x=>x.themes[0].rail_states.exposure='constructor',x=>x.themes[0].theme_id='constructor',x=>x.themes[1].theme_id=x.themes[0].theme_id]){const x=copy();mutate(x);assert.equal(ui.validate(x),false);}});
test('source links reject unsafe origins, credentials and future source clocks',()=>{for(const mutate of [x=>x.themes[0].sources[0].url='javascript:alert(1)',x=>x.themes[0].sources[0].url='https://sec.gov.evil.test/a',x=>x.themes[0].sources[0].url='https://secret@www.sec.gov/a',x=>x.themes[0].sources[0].house_known_at='2099-01-01T00:00:00Z',x=>x.themes[0].sources[0].documentary_class='funded_revenue']){const x=copy();mutate(x);assert.equal(ui.validate(x),false);}});
test('all six visible stories preserve source-native allocation, policy, notification and segment limits',async()=>{for(const lang of ['en','zh']){env(lang);const h=host(),before=global.location.href,c=ui.create({host:()=>h,fetch:async()=>({ok:true,json:async()=>copy()})});await c.load();assert.equal(c.state().status,'ready');assert.equal((h.innerHTML.match(/class="gr-theme-item"/g)||[]).length,6);assert.match(h.innerHTML,lang==='en'?/Known source context/:/已知来源背景/);assert.match(h.innerHTML,lang==='en'?/What is missing/:/缺少什么/);assert.match(h.innerHTML,lang==='en'?/What to watch/:/接下来观察/);assert.match(h.innerHTML,lang==='en'?/allocation-plan context/:/分配计划/);assert.match(h.innerHTML,lang==='en'?/estimated upper bound/:/估计上限/);assert.match(h.innerHTML,lang==='en'?/reported segment evidence/:/分部证据/);assert.match(h.innerHTML,lang==='en'?/does not refresh the underlying sources/:/不会刷新底层来源/);assert.doesNotMatch(h.innerHTML,/must admit missing evidence|current owner evidence|所有者接纳/);assert.equal(global.location.href,before);}});
test('qualified issuer links change only independent issuer; program/FMS links use exact IDs',()=>{const t=fixture.themes.find(t=>t.theme_id==='munitions_replenishment'),s=t.sources.find(s=>s.security_id==='xnys:LMT');let n=ui.sourceNavigation('https://local.test/?issuer=LHX&ticker=IRDM&mode=programs&campaign=r#source',s),u=new URL(n.href,'https://local.test');assert.equal(n.kind,'company');assert.equal(u.searchParams.get('issuer'),'LMT');assert.equal(u.searchParams.get('ticker'),'IRDM');assert.equal(u.searchParams.get('mode'),'programs');assert.equal(u.searchParams.get('campaign'),'r');assert.equal(u.hash,'#defenseInvestorTitle');const ship=fixture.themes.find(t=>t.theme_id==='shipbuilding').sources.find(s=>s.program_id);n=ui.sourceNavigation('https://local.test/?issuer=LHX&ticker=IRDM&agency=Navy&campaign=r#source',ship);u=new URL(n.href,'https://local.test');assert.equal(u.searchParams.get('item'),'program:'+ship.program_id);assert.equal(u.searchParams.get('issuer'),'LHX');assert.equal(u.searchParams.get('mode'),'programs');assert.equal(u.searchParams.has('ticker'),false);const fms=fixture.themes.find(t=>t.theme_id==='nato_fms_demand').sources.find(s=>s.documentary_class==='congressional_notification');n=ui.sourceNavigation(u.href,fms);assert.equal(n.kind,'fms');assert.equal(new URL(n.href,'https://local.test').searchParams.get('item'),'fms:'+fms.row_id);assert.equal(ui.sourceNavigation(u.href,{program_id:'shipbuilding',security_id:null,issuer_id:null,row_id:'shipbuilding',documentary_class:null}),null);});
test('primary sources and public copy are escaped; technical pointers remain optional',async()=>{env();const x=copy();x.themes[0].known_en='<script>bad</script>';x.themes[0].sources[0].title='<img src=x>';const h=host(),c=ui.create({host:()=>h,fetch:async()=>({ok:true,json:async()=>x})});await c.load();assert.match(h.innerHTML,/&lt;script&gt;bad/);assert.match(h.innerHTML,/&lt;img src=x&gt;/);assert.doesNotMatch(h.innerHTML,/<script>|<img src=x>/);assert.match(h.innerHTML,/Source clocks and references/);assert.match(h.innerHTML,/target="_blank" rel="noopener noreferrer"/);});
test('per-call auth, same-principal last-good refresh and403 clearing',async()=>{env();let answer={ok:true,json:async()=>copy()},headers=0;const h=host(),c=ui.create({host:()=>h,authHeaders:async()=>{headers++;return {test:'current'};},fetch:async(url,opts)=>{assert.equal(url,'/api/government-revenue/theme-context');assert.equal(opts.headers.test,'current');assert.equal(opts.credentials,'same-origin');return answer;}});await c.load();answer={ok:false,status:503};await c.load(true);assert.equal(c.state().status,'unavailable');assert.match(h.innerHTML,/last verified source context/);answer={ok:true,json:async()=>({})};await c.load(true);assert.equal(c.state().status,'invalid');answer={ok:false,status:403};await c.load(true);assert.equal(c.state().status,'locked');assert.equal(c.state().content_id,null);assert.doesNotMatch(h.innerHTML,/gr-theme-item/);assert.equal(headers,4);});
test('logout/account switch discards delayed old read and cannot overwrite new403',async()=>{env();let subject='fixture-a',resolves=[];const h=host(),listeners={};global.addEventListener=(name,fn)=>{listeners[name]=fn;};const c=ui.create({host:()=>h,authSubject:()=>subject,fetch:()=>new Promise(r=>resolves.push(r))});c.mount();const old=c.load();await new Promise(setImmediate);subject='';listeners['mdx-auth']({detail:{user:null}});assert.equal(c.state().status,'locked');subject='fixture-b';c.setAuthSubject(subject);const current=c.load();await new Promise(setImmediate);resolves[1]({ok:false,status:403});await current;resolves[0]({ok:true,json:async()=>copy()});await old;assert.equal(c.state().status,'locked');assert.equal(c.state().content_id,null);assert.doesNotMatch(h.innerHTML,/gr-theme-item/);});
test('source context completeness cannot be inferred from labels or source count',()=>{const x=copy();x.themes[0].research_state='SOURCE_CONTEXT_COMPLETE';assert.equal(ui.validate(x),false);});

function disclosureHost(){
  let html='',nodes=[],focusNodes=[];
  return {get innerHTML(){return html;},set innerHTML(value){html=value;nodes=Array.from(value.matchAll(/<details\b([^>]*)>/g),m=>{const key=/data-theme-disclosure="([^"]+)"/.exec(m[1]);return key?{open:/\bopen(?:\s|=|$)/.test(m[1]),getAttribute(name){return name==='data-theme-disclosure'?key[1]:null;}}:null;}).filter(Boolean);focusNodes=Array.from(value.matchAll(/<[^>]+data-theme-focus="([^"]+)"[^>]*>/g),m=>({getAttribute(name){return name==='data-theme-focus'?m[1]:null;},focus(){global.document.activeElement=this;}}));},querySelectorAll(selector){if(selector==='[data-theme-disclosure][open]'||selector==='details[open]')return nodes.filter(n=>n.open);if(selector==='[data-theme-disclosure]')return nodes;if(selector==='[data-theme-focus]')return focusNodes;return[];},contains(node){return nodes.includes(node)||focusNodes.includes(node);},querySelector(){return null;}};
}
function defaultText(html){
  let at=0,result='',closed=[];
  for(const match of html.matchAll(/<\/?details\b[^>]*>/g)){
    if(!closed.some(Boolean))result+=html.slice(at,match.index);
    if(match[0].startsWith('</'))closed.pop();else closed.push(!/\bopen(?:\s|=|>)/.test(match[0]));
    at=match.index+match[0].length;
  }
  if(!closed.some(Boolean))result+=html.slice(at);
  return result.replace(/<[^>]+>/g,'');
}
test('theme narratives and sources stay complete inside native closed disclosures while typed reasons remain visible',async()=>{
  for(const lang of ['en','zh']){
    env(lang);const x=copy(),h=disclosureHost(),c=ui.create({host:()=>h,fetch:async()=>({ok:true,json:async()=>x})});await c.load();
    for(const theme of x.themes){
      for(const field of ['known','missing','next'])assert.ok(h.innerHTML.includes(theme[field+'_'+lang].replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))),'Complete supplied narrative must survive '+field);
      for(const part of ['known','missing','next','sources'])assert.ok(h.querySelectorAll('[data-theme-disclosure]').some(n=>n.getAttribute('data-theme-disclosure')===theme.theme_id+':'+part),'Missing semantic disclosure '+theme.theme_id+':'+part);
      const visible=defaultText(h.innerHTML);assert.ok(!visible.includes(theme['known_'+lang]),'Full known narrative must not dominate default composition');assert.ok(!visible.includes(theme['missing_'+lang]),'Full gap narrative must not dominate default composition');assert.ok(!visible.includes(theme['next_'+lang]),'Full next narrative must remain accessible through its disclosure');
      const card=h.innerHTML.split('aria-labelledby="themeTitle-'+theme.theme_id+'"')[1].split('</article>')[0];assert.match(defaultText(card),/gr-theme-overview|Funding stage|资金阶段/);
    }
    const keys=h.querySelectorAll('[data-theme-disclosure]').map(n=>n.getAttribute('data-theme-disclosure'));assert.equal(new Set(keys).size,keys.length);assert.ok(h.innerHTML.includes('href="#gov-workspace"'));assert.match(fs.readFileSync(path.join(__dirname,'../templates/government_revenue.html.j2'),'utf8'),/id="gov-workspace"/);
  }
});
test('new narrative disclosure openness and focused summary survive an actual language refresh',async()=>{
  env();const h=disclosureHost(),c=ui.create({host:()=>h,fetch:async()=>({ok:true,json:async()=>copy()})});await c.load();
  const key=fixture.themes[0].theme_id+':known',detail=h.querySelectorAll('[data-theme-disclosure]').find(n=>n.getAttribute('data-theme-disclosure')===key);assert.ok(detail,'Known-source disclosure must exist');detail.open=true;global.document.activeElement=h.querySelectorAll('[data-theme-focus]').find(n=>n.getAttribute('data-theme-focus')===key);assert.ok(global.document.activeElement);
  global.document.documentElement.getAttribute=()=> 'zh';c.refresh();assert.ok(h.querySelectorAll('[data-theme-disclosure]').find(n=>n.getAttribute('data-theme-disclosure')===key).open);assert.equal(global.document.activeElement.getAttribute('data-theme-focus'),key);assert.match(h.innerHTML,/已知来源背景/);
});
test('mobile queue keeps a bounded scroll surface instead of expanding every retained record',()=>{
  const source=fs.readFileSync(path.join(__dirname,'../templates/government_revenue.html.j2'),'utf8'),rules=Array.from(source.matchAll(/\.queue-list\{([^}]+)\}/g)),mobile=rules.at(-1)[1];assert.doesNotMatch(mobile,/height:\s*auto|max-height:\s*none/,'Mobile breakpoint must not unbound the retained500-row queue');assert.match(mobile,/overflow:\s*auto|height:/);assert.match(mobile,/min-height:\s*[1-9]/,'Short viewport scroll surface must remain nonzero');
});

function prototypeFixture(){const x=copy();x.schema_version='1.1.0';x.as_of='2026-10-18T04:20:00+00:00';const t=x.themes[0];t.rail_states.funding_stage='partial';t.research_state='EVIDENCE_INSUFFICIENT';const s=structuredClone(t.sources[0]);Object.assign(s,{row_id:'prog-agreement:'+'a'.repeat(24),pointer:'/public_agreement_assertions/0',url:'https://www.sda.mil/example/',title:'Synthetic prototype agreement announcement',program_id:null,issuer_id:null,security_id:null,documentary_class:'prototype_agreement',native_reason_code:'prototype_agreement_only',source_publication_date:'2026-07-13',source_available_at:'2026-10-18T02:55:55+00:00',house_known_at:'2026-10-18T04:10:00+00:00'});t.sources=[s];return x;}
test('prototype documentary sources require the new reader version and preserve legacy refusal',()=>{const x=prototypeFixture();assert.equal(ui.validate(x),true);x.schema_version='1.0.0';assert.equal(ui.validate(x),false);x.schema_version='1.2.0';assert.equal(ui.validate(x),false);});
test('prototype source cannot become reviewed programme, issuer or financial attribution',()=>{for(const key of ['program_id','issuer_id','security_id']){const x=prototypeFixture();x.themes[0].sources[0][key]='invented';assert.equal(ui.validate(x),false);}const x=prototypeFixture();x.themes[0].rail_states.funding_stage='supported';assert.equal(ui.validate(x),false);});
test('prototype issuer-source link is restricted to the literal admitted corporate host',()=>{assert.equal(ui.safeSource('https://www.l3harris.com/newsroom/example'),'');assert.equal(ui.safeSource('https://www.l3harris.com/newsroom/example',true),'https://www.l3harris.com/newsroom/example');assert.equal(ui.safeSource('https://www.l3harris.com.evil.test/a'),'');assert.equal(ui.safeSource('https://secret@www.l3harris.com/a'),'');});
test('prototype documentary class renders in both languages without inventing canonical navigation',async()=>{for(const lang of ['en','zh']){env(lang);const h=host(),c=ui.create({host:()=>h,fetch:async()=>({ok:true,json:async()=>prototypeFixture()})});await c.load();assert.equal(c.state().status,'ready');assert.match(h.innerHTML,lang==='en'?/Prototype agreement announcement/:/原型协议公告/);assert.equal(ui.sourceNavigation(global.location.href,prototypeFixture().themes[0].sources[0]),null);}});
test('theme FMS navigation selects the exact row produced by the shipped FMS module',async()=>{
  const vm=require('node:vm');
  const graph=JSON.parse(fs.readFileSync(path.join(__dirname,'defense_o2_source_contracts/fixtures/fms_case_graph.json')));
  const window={fetch:async()=>({ok:true,json:async()=>graph})};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../templates/government-revenue-dossiers.js'),'utf8'),{window});
  const fms=window.createGovernmentRevenueFms({obj:x=>!!x&&typeof x==='object'&&!Array.isArray(x),arr:x=>Array.isArray(x)?x:[],text:(x,f='')=>x==null?f:String(x),tr:en=>en});
  const rows=await fms.load();
  assert.equal(rows.length,68);
  for(const caseKey of ['fms:transmittal:25-104','fms:transmittal:26-82']){
    const nav=ui.sourceNavigation('https://local.test/government_revenue.html?mode=changes',{documentary_class:'congressional_notification',row_id:caseKey});
    const selected=new URL(nav.href,'https://local.test').searchParams.get('item');
    const row=rows.find(row=>row.id===selected);
    assert.ok(row,'Theme source navigation must resolve to a real FMS row, not the first-case fallback');
    assert.equal(row.case.case_key,caseKey);
  }
});


test('theme program navigation resolves the shipped program module view identity',async()=>{
  const vm=require('node:vm');
  const graph=JSON.parse(fs.readFileSync(path.join(__dirname,'defense_o2_source_contracts/fixtures/program_dossier.json')));
  let rows=[];
  const window={fetch:async()=>({ok:true,status:200,json:async()=>graph})};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../templates/government-revenue-dossiers.js'),'utf8'),{window});
  const program=window.createGovernmentRevenueProgramDossier({obj:x=>!!x&&typeof x==='object'&&!Array.isArray(x),arr:x=>Array.isArray(x)?x:[],text:(x,f='')=>x==null?f:String(x),tr:en=>en,onRows:value=>{rows=value;}});
  await program.load();
  assert.equal(rows.length,1);
  const nav=ui.sourceNavigation('https://local.test/government_revenue.html?mode=changes',{program_id:'acq-program:virginia-class-ssn'});
  const selected=new URL(nav.href,'https://local.test').searchParams.get('item');
  assert.ok(rows.some(row=>row.id===selected&&row.dossier.program_id==='acq-program:virginia-class-ssn'),'Theme source must select the exact program rather than the first row');
});
