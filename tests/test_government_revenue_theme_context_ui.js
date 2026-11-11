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

function disclosureHost(doc=()=>global.document){
  let html='',nodes=[],focusNodes=[],anchors=[];
  function node(attrs){const values=Object.fromEntries(Array.from(attrs.matchAll(/([a-z-]+)="([^"]*)"/g),m=>[m[1],m[2].replace(/&amp;/g,'&').replace(/&quot;/g,'"')])),listeners={};return {open:/\bopen(?:\s|=|$)/.test(attrs),getAttribute(name){return values[name]??null},hasAttribute(name){return Object.hasOwn(values,name)},addEventListener(name,fn){listeners[name]=fn},click(event){if(listeners.click)listeners.click(event)},focus(){doc().activeElement=this}};}
  return {get innerHTML(){return html;},set innerHTML(value){html=value;nodes=Array.from(value.matchAll(/<details\b([^>]*)>/g),m=>node(m[1])).filter(n=>n.hasAttribute('data-theme-disclosure'));const tags=Array.from(value.matchAll(/<(?:a|summary)\b[^>]*>/g),m=>{const n=node(m[0]);n.isLink=m[0].startsWith('<a ');const section=value.slice(0,m.index).match(/aria-labelledby="themeTitle-([^"]+)"/g);n.theme=section&&section.at(-1).slice(28,-1);return n;});focusNodes=tags.filter(n=>n.hasAttribute('data-theme-focus'));anchors=tags.filter(n=>n.isLink);},querySelectorAll(selector){if(selector==='[data-theme-disclosure][open]'||selector==='details[open]')return nodes.filter(n=>n.open);if(selector==='[data-theme-disclosure]')return nodes;if(selector==='[data-theme-focus]')return focusNodes;if(selector==='[data-theme-issuer]')return anchors.filter(n=>n.hasAttribute('data-theme-issuer'));if(selector==='a')return anchors;return[];},contains(n){return nodes.includes(n)||focusNodes.includes(n);},querySelector(){return null;}};
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

// Real rendered source anchor -> real issuer controller -> real page restoration.
// This DOM/history harness is offline; it makes no browser or live-auth claim.
function themeJourney(options={}){
  const vm=require('node:vm'),page=fs.readFileSync(process.env.GOV_THEME_PAGE||path.join(__dirname,'../templates/government-revenue-page.js.j2'),'utf8');
  let url=new URL('https://local.test/government_revenue.html?issuer=LHX&mode=awards&ticker=IRDM&item=award%3Akept&agency=Navy&campaign=read#source'),position=0;
  const entries=[{url:url.href,state:options.snapshot||{foreign:{kept:true},governmentRevenue:{schema:1,q:'Navy',truth:'official'}}}],listeners=[];
  const location={get href(){return url.href},get search(){return url.search},get pathname(){return url.pathname},get hash(){return url.hash}};
  const history={get state(){return entries[position].state},replaceState(state,_title,next){url=new URL(next,url);entries[position]={url:url.href,state}},pushState(state,_title,next){url=new URL(next,url);entries.splice(++position);entries.push({url:url.href,state})}};
  const controls={};function control(id){return controls[id]||(controls[id]={value:'',focus(){document.activeElement=this}});}
  const document={activeElement:null,documentElement:{getAttribute(){return options.lang||'en'}},querySelectorAll(){return[]},querySelector(selector){return control(selector)}};
  const ctx={URL,URLSearchParams,console,document,location,history,state:{mode:'awards',selected:'award:kept',ticker:'IRDM',agency:'Navy',q:'Navy',truth:'official'},pendingSelection:'',missingCandidateSelection:'',identityGeneration:null,$:control,preserveFilterValue(){},closeTopOverlay(){},activateMode(){},tr:en=>en,addEventListener(type,fn){if(type==='popstate')listeners.push(fn)}};
  ctx.window=ctx;vm.createContext(ctx);
  for(const file of ['government-revenue-investor.js','government-revenue-theme-context.js'])vm.runInContext(fs.readFileSync(file.endsWith('theme-context.js')&&process.env.GOV_THEME_SOURCE||path.join(__dirname,'../templates',file),'utf8'),ctx);
  ctx.investorUI=ctx.createGovernmentRevenueInvestor({host});ctx.investorUI.mount();
  const h=disclosureHost(()=>document),factory=ctx.createGovernmentRevenueThemeContext;
  ctx.createGovernmentRevenueThemeContext=api=>factory(Object.assign(api,{host:()=>h,authSubject:()=>options.subject||'member-a',fetch:options.fetch||(async()=>({ok:true,json:async()=>options.payload||copy()}))}));
  vm.runInContext(page.slice(page.indexOf('  var themeUI='),page.indexOf('\n  function companyBridgeSection')),ctx);
  for(const name of ['syncUrl','restoreUrl','restoreHistoryView']){const start=page.indexOf('  function '+name+'('),end=page.indexOf('\n  function ',start+1);vm.runInContext(page.slice(start,end),ctx);}
  listeners.push(ctx.restoreHistoryView);ctx.syncUrl(false,true);
  return {ctx,h,entries,document,get url(){return url},move(delta){position+=delta;url=new URL(entries[position].url);listeners.forEach(fn=>fn())},anchor(){return h.querySelectorAll('a').find(n=>n.theme==='munitions_replenishment'&&new URL(n.getAttribute('href'),'https://local.test').searchParams.get('issuer')==='LMT')},open(){for(const n of h.querySelectorAll('[data-theme-disclosure]'))n.open=n.getAttribute('data-theme-disclosure').startsWith('munitions_replenishment:')},opened(){return h.querySelectorAll('details[open]').map(n=>n.getAttribute('data-theme-disclosure'))}};
}
function plainClick(extra={}){return Object.assign({button:0,defaultPrevented:false,preventDefault(){this.defaultPrevented=true}},extra);}
test('theme journey: rendered issuer click and Back/Forward retain desk, disclosures and focus',async()=>{
  for(const lang of ['en','zh']){
    const j=themeJourney({lang});await j.ctx.themeUI.load();j.open();const expected=j.opened(),anchor=j.anchor();assert.ok(anchor,'Actual theme company anchor must exist');anchor.focus();const event=plainClick();anchor.click(event);
    assert.equal(event.defaultPrevented,true);assert.equal(j.entries.length,2);assert.equal(j.url.searchParams.get('issuer'),'LMT');assert.equal(j.url.searchParams.get('ticker'),'IRDM');assert.equal(j.url.searchParams.get('item'),'award:kept');assert.equal(j.url.hash,'#defenseInvestorTitle');assert.equal(j.ctx.history.state.governmentRevenue.q,'Navy');assert.equal(j.ctx.history.state.governmentRevenue.truth,'official');assert.equal(j.ctx.history.state.governmentRevenueTheme,undefined);assert.equal(j.ctx.investorUI.state().ticker,'LMT');
    assert.doesNotMatch(JSON.stringify(j.entries[0].state.governmentRevenueTheme),/https:|member-a|cik:/,'History stores semantic public view state only');
    j.h.innerHTML='';j.move(-1);assert.deepEqual(j.opened(),expected);assert.equal(j.document.activeElement.getAttribute('data-theme-focus'),anchor.getAttribute('data-theme-focus'));assert.equal(j.ctx.state.q,'Navy');assert.equal(j.ctx.state.truth,'official');assert.equal(j.url.hash,'#source');assert.equal(j.ctx.investorUI.state().ticker,'LHX');
    j.move(1);assert.equal(j.document.activeElement,j.document.querySelector('#defenseInvestor [data-investor-ticker="LMT"]'));assert.equal(j.ctx.state.ticker,'IRDM');
    j.move(-1);j.ctx.pendingSelection='';j.ctx.state.selected='award:next';j.ctx.syncUrl(true);assert.equal(j.ctx.history.state.governmentRevenueTheme,undefined);assert.equal(j.entries[0].state.governmentRevenueTheme.content_id,fixture.content_id);
  }
});
test('theme journey: modifiers retain real href and default navigation without history mutation',async()=>{
  const j=themeJourney();await j.ctx.themeUI.load();const anchor=j.anchor();assert.ok(anchor);const before=j.ctx.history.state,url=j.url.href;
  for(const extra of [{ctrlKey:true},{metaKey:true},{shiftKey:true},{altKey:true},{button:1},{defaultPrevented:true}]){const e=plainClick(extra);anchor.click(e);assert.equal(j.ctx.history.state,before);assert.equal(j.url.href,url);assert.equal(j.entries.length,1);}
  assert.equal(new URL(anchor.getAttribute('href'),url).searchParams.get('issuer'),'LMT');
});
test('theme journey: an already rendered anchor uses the current workspace after further filtering',async()=>{
  const j=themeJourney();await j.ctx.themeUI.load();const anchor=j.anchor();
  j.ctx.state.selected='award:new';j.ctx.state.q='ship';j.ctx.state.truth='linked';j.ctx.state.agency='Army';j.ctx.syncUrl(true);anchor.click(plainClick());
  assert.equal(j.url.searchParams.get('item'),'award:new');assert.equal(j.url.searchParams.get('agency'),'Army');assert.equal(j.ctx.history.state.governmentRevenue.q,'ship');assert.equal(j.ctx.history.state.governmentRevenue.truth,'linked');j.move(-1);assert.equal(j.ctx.state.selected,'award:new');assert.equal(j.ctx.state.agency,'Army');assert.equal(j.ctx.state.q,'ship');
});
test('theme journey: cold return requires same validated generation and preserves foreign state',async()=>{
  const j=themeJourney();await j.ctx.themeUI.load();j.open();j.anchor().click(plainClick());assert.ok(j.entries[0].state.governmentRevenueTheme,'Navigation must retain an origin snapshot');const snapshot=structuredClone(j.entries[0].state);
  const cold=themeJourney({snapshot});await cold.ctx.themeUI.load();assert.ok(cold.opened().includes('munitions_replenishment:sources'));assert.equal(cold.document.activeElement.getAttribute('data-theme-focus'),snapshot.governmentRevenueTheme.focus);assert.equal(cold.ctx.history.state.foreign.kept,true);
  const changed=copy();changed.content_id='gptd1-'+'f'.repeat(24);const stale=themeJourney({snapshot,payload:changed});await stale.ctx.themeUI.load();assert.deepEqual(stale.opened(),[]);assert.equal(stale.document.activeElement,null);
  const invalid=themeJourney({snapshot:{...snapshot,governmentRevenueTheme:{...snapshot.governmentRevenueTheme,expanded:['not-a-theme:sources']}}});await invalid.ctx.themeUI.load();assert.deepEqual(invalid.opened(),[]);
});
test('theme journey: late response, changed focus, locked read and account switch cannot resurrect origin focus',async()=>{
  const j=themeJourney();await j.ctx.themeUI.load();j.open();j.anchor().click(plainClick());assert.ok(j.entries[0].state.governmentRevenueTheme,'Navigation must retain an origin snapshot');const snapshot=structuredClone(j.entries[0].state);
  let resolve;const late=themeJourney({snapshot,fetch:()=>new Promise(r=>{resolve=r})});const pending=late.ctx.themeUI.load();await new Promise(setImmediate);late.ctx.state.selected='award:next';late.ctx.syncUrl(true);resolve({ok:true,json:async()=>copy()});await pending;assert.deepEqual(late.opened(),[]);assert.equal(late.document.activeElement,null);
  const focus=themeJourney({snapshot});const focused=focus.document.querySelector('user-selected');focused.focus();await focus.ctx.themeUI.load();assert.equal(focus.document.activeElement,focused);
  const locked=themeJourney({snapshot,fetch:async()=>({ok:false,status:403})});await locked.ctx.themeUI.load();assert.equal(locked.ctx.history.state.governmentRevenueTheme,undefined);assert.equal(locked.ctx.themeUI.state().content_id,null);
  const switched=themeJourney({snapshot});switched.ctx.themeUI.setAuthSubject('member-b');await switched.ctx.themeUI.load();assert.equal(switched.ctx.history.state.governmentRevenueTheme,undefined);assert.deepEqual(switched.opened(),[]);
});
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
