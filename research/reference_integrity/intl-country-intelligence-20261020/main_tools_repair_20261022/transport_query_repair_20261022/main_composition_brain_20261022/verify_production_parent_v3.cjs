'use strict';
const bootFs=require('node:fs'),bootPath=require('node:path');
const bootArg=name=>{const i=process.argv.indexOf('--'+name);return i<0?null:process.argv[i+1];};
const bootstrapOutput=bootArg('output')?bootPath.resolve(bootArg('output')):null;
try {
'use strict';
// V3 composition derivative of accepted v13. Real anonymous beta/www journeys; no fixture authentication, routing, or response fabrication.
const { chromium } = require('/Users/chriswong/Documents/Cluade/charting-app/.claude/worktrees/intl-parent-proof-20261022/terminal/node_modules/playwright');
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const arg = name => { const i=process.argv.indexOf('--'+name); return i<0?null:process.argv[i+1]; };
const artifact=path.resolve(arg('artifact')), out=path.resolve(arg('output'));
const phase='candidate', matrix=arg('matrix')||'full';
if(!['full','contract','query'].includes(matrix))throw new Error('Unknown matrix: '+matrix);
const origin='https://beta.mastermind-x.com', childOrigin='https://www.mastermind-x.com';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const manifestPath=path.resolve(arg('release-manifest'));
const release=JSON.parse(fs.readFileSync(manifestPath));
if(release.schema!=='intl.production_release_inputs.v1')throw new Error('Wrong production release manifest schema');
if(release.parent.origin!==origin||release.child_origin!==childOrigin)throw new Error('Production origins must be the supported beta/www pair');
const sha40=value=>typeof value==='string'&&/^[a-f0-9]{40}$/.test(value);
for(const value of [release.accepted_candidate,release.accepted_main,release.acquisition.publication_commit,release.render.source_commit,release.render.publication_commit,release.updater.checkout_commit,release.parent.source_commit])
  if(!sha40(value))throw new Error('Missing immutable release-chain commit');
if(release.render.conclusion!=='success'||!release.render.run_id||!release.acquisition.run_id||release.acquisition.verdict!=='PASS'||release.acquisition.pass_count!==7)throw new Error('Actual accepted acquisition/render receipts required');
const requiredStatusKeys=['enabled','protocol','buildId','bridgeVersion','documentVersion','registrySha256'];
const statusExpected=release.parent.status;
if(!statusExpected||!requiredStatusKeys.every(k=>Object.hasOwn(statusExpected,k))||statusExpected.enabled!==true||statusExpected.protocol!=='mmx.shared-shell.v1'||statusExpected.buildId!==release.parent.source_commit||!sha40(statusExpected.buildId)||!/^[a-f0-9]{64}$/.test(statusExpected.registrySha256)||![statusExpected.bridgeVersion,statusExpected.documentVersion].every(v=>typeof v==='string'&&/^\d{8}\.\d+$/.test(v)))throw new Error('Incomplete production parent identity tuple');
const statusMatches=r=>r.status===200&&!r.body_error&&requiredStatusKeys.every(key=>r.body?.[key]===statusExpected[key])&&/\bprivate\b/.test(r.cache_control||'')&&/\bno-store\b/.test(r.cache_control||'');
if(path.resolve(release.artifact.directory)!==artifact)throw new Error('Artifact directory mismatch');
const files=release.artifact.files;
if(!files||typeof files!=='object'||Object.keys(files).length<5)throw new Error('Missing generated artifact manifest');
const expected={};
for(const [name,row] of Object.entries(files)){
  if(name.startsWith('/')||name.split('/').includes('..')||!/^[a-f0-9]{64}$/.test(row.sha256))throw new Error('Unsafe or unbound artifact name');
  const b=fs.readFileSync(path.join(artifact,name));
  if(hash(b)!==row.sha256||b.length!==row.bytes)throw new Error('Artifact bytes mismatch: '+name);
  expected['/'+name]=row.sha256;
}
const mandatory=['/intl.html','/shared_shell_bridge.js','/shared_shell.css','/intl_workspace.js','/intl_workspace_state.js'];
if(mandatory.some(name=>!expected[name]))throw new Error('Missing mandatory child artifact');
fs.mkdirSync(out,{recursive:true});
if(fs.existsSync(path.join(out,'observation.json')))throw new Error('Existing observation; reconcile it rather than overwrite');
const report={schema:'intl.production_parent_acceptance.v1',environment:'production',phase,matrix,started_at:new Date().toISOString(),
  parent_source:release.parent.source_commit,subject:release.accepted_candidate,accepted_main:release.accepted_main,render:release.render,
  artifact,expected,mandatory,release_manifest:manifestPath,release_manifest_sha256:hash(fs.readFileSync(manifestPath)),
  driver_sha256:hash(fs.readFileSync(__filename)),network_stubs:false,network_interception:false,fixture_cookies:false,
  preference_setup:'Genuine guest presentation caches mm.lang and mmx.shell.theme on beta only; real parent supplies child context',
  contexts:[],cases:[],responses:[],requests:[],request_failures:[],screenshots:[],page_errors:[],console_errors:[]};
const pending=[];let responseSequence=0,requestSequence=0,pageSequence=0;
const pageIds=new WeakMap(),requestRecords=new WeakMap();
const pageId=p=>{if(!pageIds.has(p))pageIds.set(p,++pageSequence);return pageIds.get(p);};
const bounded=async(promise,milliseconds,label)=>{let timer;try{return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error(label+' exceeded '+milliseconds+'ms')),milliseconds);})]);}finally{clearTimeout(timer);}};
const repository='/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018';
const {execFileSync}=require('node:child_process');
const at=(sha,name)=>{
  if(!sha40(sha)||name.startsWith('/')||name.split('/').includes('..'))throw new Error('Unsafe Git object identity');
  const size=Number(execFileSync('git',['-C',repository,'cat-file','-s',sha+':'+name],{maxBuffer:1024,timeout:30000}).toString().trim());
  if(!Number.isSafeInteger(size)||size<0||size>64*1024*1024)throw new Error('Git object exceeds finite 64MiB limit: '+name);
  const bytes=execFileSync('git',['-C',repository,'show',sha+':'+name],{maxBuffer:Math.max(4096,size+1024),timeout:60000});
  if(bytes.length!==size)throw new Error('Truncated Git object: '+name);
  return bytes;
};
const ancestor=(older,newer)=>{try{execFileSync('git',['-C',repository,'merge-base','--is-ancestor',older,newer]);return true;}catch(_){return false;}};
const lineage={
  accepted_main_to_render:ancestor(release.accepted_main,release.render.source_commit),
  acquisition_to_render:ancestor(release.acquisition.publication_commit,release.render.source_commit),
  render_source_to_publication:ancestor(release.render.source_commit,release.render.publication_commit),
  render_publication_to_updater:ancestor(release.render.publication_commit,release.updater.checkout_commit)
};
const releaseCustody=require('./validate_production_release_v3.cjs')({release,at,ancestor,hash,repository,artifact});
report.release_custody=releaseCustody;
report.custody_helper_sha256=hash(fs.readFileSync(path.join(__dirname,'validate_production_release_v3.cjs')));
const sourceNames=releaseCustody.source_paths;
const parentExpected=releaseCustody.parent_static_files;
const runtimeOverlays=releaseCustody.child_runtime_overlays;
if(JSON.stringify(Object.keys(runtimeOverlays))!==JSON.stringify(['logo_config.js'])||expected['/logo_config.js'])throw new Error('Only the independently bound normal logo runtime overlay may supplement generated artifacts');
expected['/logo_config.js']=runtimeOverlays['logo_config.js'].sha256;
report.runtime_overlay_binding=runtimeOverlays;
report.parent_host_receipt=releaseCustody.parent_host_receipt;
report.required_external_completion='Owner must reconcile a fresh post-journey host receipt against this generation before overall served acceptance';
const sourceBindings=sourceNames.map(name=>{
  const candidate=at(release.accepted_candidate,name),adopted=at(release.accepted_main,name),rendered=at(release.render.source_commit,name);
  return {name,candidate_sha256:hash(candidate),adopted_sha256:hash(adopted),rendered_sha256:hash(rendered),equal:candidate.equals(adopted)&&candidate.equals(rendered)};
});
const subjectController=at(report.subject,'templates/intl_country_cockpit.js'),builtController=at(release.render.source_commit,'templates/intl_country_cockpit.js');
const subjectBridge=at(report.subject,'templates/shared_shell_bridge.js'),builtBridge=at(release.render.source_commit,'templates/shared_shell_bridge.js'),pairedBridge=at(report.subject,'site/shared_shell_bridge.js');
const subjectWorkspace=at(report.subject,'templates/intl_workspace.js'),pairedWorkspace=at(report.subject,'site/intl_workspace.js');
const subjectParser=at(report.subject,'templates/intl_workspace_state.js'),pairedParser=at(report.subject,'site/intl_workspace_state.js');
const reviewedParserSource='2d33475adef502ab6b00b8003356c1b0ad1673c0';
const reviewedParser=at(reviewedParserSource,'templates/intl_workspace_state.js');
const artifactBindings=Object.entries(files).map(([name,row])=>{
  const published=at(release.render.publication_commit,'site/'+name);
  return {name,published_sha256:hash(published),expected_sha256:row.sha256,bytes:published.length,equal:hash(published)===row.sha256&&published.length===row.bytes};
});
const updaterPath=path.resolve(release.updater.receipt_path),updaterBytes=fs.readFileSync(updaterPath),updater=JSON.parse(updaterBytes);
const updaterBinding=hash(updaterBytes)===release.updater.receipt_sha256&&updater.checkout_commit===release.updater.checkout_commit&&
  updater.render_publication_commit===release.render.publication_commit&&updater.pass===true&&
  Object.entries(files).every(([name,row])=>updater.served_files?.[name]?.sha256===row.sha256&&updater.served_files?.[name]?.bytes===row.bytes);
report.source_binding={release_manifest_sha256:report.release_manifest_sha256,lineage,source_bindings:sourceBindings,artifact_bindings:artifactBindings,
  updater_receipt:updaterPath,updater_receipt_sha256:hash(updaterBytes),updater_binding:updaterBinding,
  inventory_qualification:releaseCustody.inventory_qualification,
  accepted_candidate:release.accepted_candidate,accepted_main:release.accepted_main,rendered_from:release.render.source_commit,generated_publication:release.render.publication_commit,
  delivery:'Country controller inlined in publication-bound HTML; all ordinary child assets match immutable generated publication; logo_config.js is separately bound to the normal updater host receipt; real public responses are independently tested'};
report.workspace_binding={workspace_sha256:hash(subjectWorkspace),paired_workspace_sha256:hash(pairedWorkspace),parser_sha256:hash(subjectParser),paired_parser_sha256:hash(pairedParser),
  reviewed_parser_source:reviewedParserSource,reviewed_parser_sha256:hash(reviewedParser),reviewed_parser_pin_sha256:'b02a808380c1a1d2c798f1b827707fa07d23679e15bf01753cffaada55f00fd1'};
function businessSearch(input){
  const search=new URL(input).search;if(!search)return '';
  const kept=search.slice(1).split('&').filter(part=>{const key=part.split('=')[0];try{return !['mmx_shell','mmx_generation'].includes(decodeURIComponent(key.replace(/\+/g,' ')));}catch{return true;}});
  return kept.length?'?'+kept.join('&'):'';
}
function canonical(input){const u=new URL(input,origin);return u.pathname+businessSearch(u.href)+u.hash;}
function hashUrl(input,fragment){const u=new URL(input);u.hash=fragment;return u.href;}
function queryCheck(scope,label,snapshot,expectedQuery){
  const actualParent=new URL(snapshot.parent.url).search,actualChild=businessSearch(snapshot.child.url);
  check(scope,label+'_raw_business_query',actualParent===expectedQuery&&actualChild===expectedQuery,{expected:expectedQuery,parent:actualParent,child:actualChild});
}
async function settledState(page,label,expectedUrl,options={}){
  const deadline=Date.now()+15000;let last;
  do{
    last=await state(page,label);
    const locationOk=last.parent.url===expectedUrl&&canonical(last.child.url)===canonical(expectedUrl);
    const generationOk=!options.generation||(options.changed?last.child.generation!==options.generation:last.child.generation===options.generation);
    const ackOk=options.acceptedAfter===undefined||(last.child.acks>options.acceptedAfter&&last.child.events.some(e=>e.type==='LOCATION_ACCEPTED'&&e.origin===origin&&e.generation===last.child.generation&&e.requestId&&canonical(e.href)===canonical(expectedUrl)));
    if(locationOk&&generationOk&&ackOk)return last;
    await page.waitForTimeout(75);
  }while(Date.now()<deadline);
  throw new Error('Destination did not settle: '+JSON.stringify({label,expectedUrl,options,last}));
}
const save=()=>fs.writeFileSync(path.join(out,'observation.json'),JSON.stringify(report,null,2)+'\n');
const check=(scope,id,passed,detail={})=>report.cases.push({scope,id,passed:!!passed,...detail});
check('binding','accepted_main_render_updater_and_source_custody',Object.values(lineage).every(Boolean)&&sourceBindings.every(x=>x.equal)&&artifactBindings.every(x=>x.equal)&&updaterBinding&&hash(subjectController)===hash(builtController)&&hash(subjectBridge)===hash(builtBridge)&&hash(subjectBridge)===hash(pairedBridge)&&hash(subjectBridge)===expected['/shared_shell_bridge.js']&&fs.readFileSync(path.join(artifact,'intl.html'),'utf8').includes(subjectController.toString().trim()),report.source_binding);
check('binding','workspace_and_reviewed_parser_custody',hash(subjectWorkspace)===hash(pairedWorkspace)&&hash(subjectWorkspace)===expected['/intl_workspace.js']&&hash(subjectParser)===hash(pairedParser)&&hash(subjectParser)===expected['/intl_workspace_state.js']&&hash(subjectParser)===report.workspace_binding.reviewed_parser_sha256&&hash(reviewedParser)===report.workspace_binding.reviewed_parser_pin_sha256,report.workspace_binding);
const widths=matrix==='full'?[1440,768,390,320]:[1440];
const presentations=matrix==='full'?[['en','dark'],['en','light'],['zh','dark'],['zh','light']]:[['en','dark']];
async function actualFrame(page){
  const locator=page.locator('iframe[data-shared-shell-frame][data-response-kind="content"]');
  await locator.waitFor({state:'visible',timeout:45000});
  const f=await (await locator.elementHandle()).contentFrame();
  if(!f)throw new Error('Missing actual child');
  await f.waitForFunction(()=>window.MMXSharedShell&&window.MMXSharedShell.active&&document.querySelector('[data-im-country-analysis]')?.dataset.imcEnhanced==='true',null,{timeout:15000});
  return f;
}
async function state(page,label){
  const f=await actualFrame(page);
  const parent=await page.evaluate(()=>({url:location.href,history:history.length,entry:history.state?.mmxSharedShellEntry||null,events:(window.__intlProofEvents||[]).slice(-30),theme:document.documentElement.dataset.theme,lang:document.documentElement.dataset.lang}));
  const child=await f.evaluate(()=>({url:location.href,generation:new URL(location.href).searchParams.get('mmx_generation'),transport:new URL(location.href).searchParams.get('mmx_shell'),theme:document.documentElement.dataset.theme,lang:document.documentElement.dataset.lang,tools:document.getElementById('intl-analysis-tools').open,legacy:document.getElementById('intl-legacy-research').open,countries:[...document.querySelectorAll('details.imc-country[open]')].map(e=>e.id),activeId:document.activeElement?.id||'',activeHref:document.activeElement?.getAttribute('href')||'',activeTag:document.activeElement?.tagName,scroll:{x:scrollX,y:scrollY},fragmentApi:typeof window.MMXSharedShell?.sameDocumentFragment,rail:[...document.querySelectorAll('.imc-country-rail a[aria-current="location"]')].map(a=>a.hash),focusCountry:document.activeElement?.closest('details.imc-country')?.id||'',workspace:window.__intlProofWorkspaceSnapshot?.()||null,preInit:(window.__intlProofPreInit||[]).slice(),locationEvents:(window.__intlProofLocations||[]).slice(),acks:(window.__intlProofEvents||[]).filter(x=>x.type==='LOCATION_ACCEPTED').length,events:(window.__intlProofEvents||[]).slice(-16)}));
  return {label,parent,child};
}
async function visibleInParent(page,selector){
  const f=await actualFrame(page),frameBox=await page.locator('iframe[data-shared-shell-frame]').boundingBox(),viewport=page.viewportSize();
  if(!frameBox)return {visible:false,reason:'no iframe bounds'};
  const r=await f.locator(selector).evaluate((el,{frameBox,viewport})=>{
    const r=el.getBoundingClientRect();
    const left=Math.max(r.left,0,-frameBox.x),right=Math.min(r.right,innerWidth,frameBox.width,viewport.width-frameBox.x);
    const top=Math.max(r.top,0,-frameBox.y),bottom=Math.min(r.bottom,innerHeight,frameBox.height,viewport.height-frameBox.y);
    const rendered=el.getClientRects().length>0&&right>left&&bottom>top;
    const point={x:(left+right)/2,y:(top+bottom)/2};
    const hit=rendered?document.elementFromPoint(point.x,point.y):null;
    return {rect:{top:r.top,bottom:r.bottom,left:r.left,right:r.right},clip:{left,right,top,bottom},point,rendered,child_hit:!!hit&&(hit===el||el.contains(hit)),hit_tag:hit?.tagName||null,hit_id:hit?.id||null};
  },{frameBox,viewport});
  const parentPoint={x:frameBox.x+r.point.x,y:frameBox.y+r.point.y};
  const parentHit=r.rendered&&await page.evaluate(({x,y})=>!!document.elementFromPoint(x,y)?.closest('iframe[data-shared-shell-frame]'),parentPoint);
  return {visible:r.rendered&&r.child_hit&&parentHit,child:r,frame:frameBox,viewport,parent_point:parentPoint,parent_hit:parentHit};
}
async function settledVisibility(page,selector){
  let r;const until=Date.now()+3500;
  do{r=await visibleInParent(page,selector);if(r.visible)return r;await page.waitForTimeout(100);}while(Date.now()<until);
  return r;
}
async function screenshot(page,name){
  const file=path.join(out,name+'.png');await page.screenshot({path:file,fullPage:false});
  const raw=fs.readFileSync(file);report.screenshots.push({path:name+'.png',bytes:raw.length,sha256:hash(raw)});
}
async function ensureTools(page,open){
  const f=await actualFrame(page);
  if(await f.locator('#intl-analysis-tools').evaluate(el=>el.open)!==open)
    await f.locator('#intl-analysis-tools > summary').click();
}
async function nestedState(page){
  const f=await actualFrame(page);
  return f.locator('#intl-leadership-rotation').evaluate(el=>{const a=[];for(let n=el;n;n=n.parentElement)if(n.tagName==='DETAILS')a.push({id:n.id,open:n.open});return {ancestors:a,allOpen:a.every(x=>x.open)};});
}

const businessUi=w=>({mounted:w.mounted,controlsDisabled:w.controlsDisabled,view:w.view,horizon:w.horizon,basis:w.basis,market:w.market,historyHidden:w.historyHidden,historyMarkets:w.historyMarkets,pressedViews:w.pressedViews,issues:w.issues});
const invalidWarning=w=>/Invalid URL state restored|无效 URL 状态已还原/.test(w.issues);
const validHistory=w=>w.mounted&&!w.controlsDisabled&&w.view==='history'&&w.market==='TW'&&w.horizon==='3m'&&w.basis==='local'&&w.historyHidden===false&&w.historyMarkets.some(m=>m.market==='TW'&&!m.hidden)&&w.historyMarkets.every(m=>m.market==='TW'||m.hidden);
async function selectRealView(page,view){
  const f=await actualFrame(page),button=f.locator('button[data-im-action="set_view"][data-im-view="'+view+'"]');
  if(await button.isVisible())await button.click();else await f.locator('[data-im-controls] select[data-im-action="set_view"]').selectOption(view);
}
async function fragmentApiJourney(page,scope,label,fragment,snapshots){
  const before=await state(page,label+'_before'),f=await actualFrame(page),target=canonical(hashUrl(before.parent.url,fragment));
  const result=await f.evaluate(target=>window.MMXSharedShell.navigate(target,'replace'),target);
  const after=await settledState(page,label+'_after',origin+target,{generation:before.child.generation,acceptedAfter:before.child.acks});snapshots.push(before,after);
  check(scope,label+'_real_same_generation_ack',result===true&&after.child.generation===before.child.generation&&after.parent.history===before.parent.history&&after.child.acks>before.child.acks&&after.child.locationEvents.length>before.child.locationEvents.length,{mode:'supported navigation API, replace, fragment-only; not a user-click journey',before_url:before.parent.url,after_url:after.parent.url,api_result:result,acks_before:before.child.acks,acks_after:after.child.acks,events_before:before.child.locationEvents.length,events_after:after.child.locationEvents.length});
  queryCheck(scope,label,after,new URL(before.parent.url).search);return {before,after};
}
async function queryJourney(page,scope,query,profile,snapshots){
  const initial=await settledState(page,'query_initial',origin+'/intl.html'+query+'#intl-analysis-tools');snapshots.push(initial);queryCheck(scope,'query_initial',initial,query);
  const w=initial.child.workspace,early=initial.child.preInit.find(e=>e.generation===initial.child.generation);
  check(scope,'query_mount_is_real',w.mounted&&!w.controlsDisabled&&initial.child.transport==='1'&&!!initial.child.generation,{ui:businessUi(w),raw_child_search:w.rawSearch});
  check(scope,'raw_projection_and_url_custody',w.readerType==='function'&&w.projection===query&&w.readerError===null,{expected_query:query,projection:w.projection,reader_type:w.readerType,error:w.readerError,raw_child_search:w.rawSearch});
  check(scope,'projection_available_before_init',!!early&&early.snapshot.mounted&&early.snapshot.readerType==='function'&&early.snapshot.projection===query&&early.snapshot.bridgeActive===false,{pre_init:early||null});
  if(profile==='ordinary'){
    check(scope,'ordinary_defaults_without_false_invalid_warning',w.view==='overview'&&!invalidWarning(w),{ui:businessUi(w),unavailable:w.unavailable});
  }else if(profile.startsWith('invalid-')){
    check(scope,'invalid_business_query_remains_refused',invalidWarning(w)&&w.view==='overview'&&!validHistory(w),{ui:businessUi(w),query});
  }else{
    const correct=validHistory(w)&&!invalidWarning(w);
    check(scope,'nondefault_business_state_applied',correct,{ui:businessUi(w),query});
    check(scope,'nondefault_state_applied_before_init',!!early&&validHistory(early.snapshot)&&!invalidWarning(early.snapshot),{pre_init:early||null});
    if(!correct){check(scope,'query_retention_journeys_have_valid_start',false,{reason:'Initial actual business state is incorrect; no remount or synthetic state repair performed.'});await screenshot(page,scope+'-initial');return;}
    await selectRealView(page,'library');await page.waitForURL(u=>u.searchParams.get('view')==='library');
    const library=await settledState(page,'query_library',page.url(),{generation:initial.child.generation,acceptedAfter:initial.child.acks});snapshots.push(library);
    let f=await actualFrame(page);await f.locator('button[data-im-action="set_library_group"][data-im-group="leaders"]').click();await page.waitForURL(u=>u.searchParams.get('group')==='leaders');
    const leaders=await settledState(page,'query_leaders',page.url(),{generation:library.child.generation,acceptedAfter:library.child.acks});snapshots.push(leaders);
    const libraryOk=(x,group)=>x.child.workspace.mounted&&!x.child.workspace.controlsDisabled&&x.child.workspace.market==='TW'&&x.child.workspace.view==='library'&&x.child.workspace.horizon==='3m'&&x.child.workspace.basis==='local'&&!invalidWarning(x.child.workspace)&&x.child.workspace.library.hidden===false&&x.child.workspace.library.enhanced&&x.child.workspace.library.input.disabled===false&&JSON.stringify(x.child.workspace.library.activeGroups)===JSON.stringify(group?['leaders']:[]);
    check(scope,'query_library_controls_apply_real_state',libraryOk(library,false)&&libraryOk(leaders,true)&&library.parent.history===initial.parent.history+1&&leaders.parent.history===library.parent.history+1,{library:library.child.workspace,leaders:leaders.child.workspace});
    for(const [action,target,kind] of [['goBack',library,'library'],['goBack',initial,'history'],['goForward',library,'library'],['goForward',leaders,'leaders']]){
      const before=await state(page,'query_traversal_before');await page[action]({waitUntil:'domcontentloaded',timeout:20000});
      const after=await settledState(page,'query_'+action+'_'+kind,target.parent.url,{generation:before.child.generation,changed:true});snapshots.push(after);
      const uiOk=kind==='history'?validHistory(after.child.workspace)&&!invalidWarning(after.child.workspace):libraryOk(after,kind==='leaders');
      check(scope,'query_'+action+'_'+kind+'_restores_actual_state',uiOk&&after.parent.history===before.parent.history&&JSON.stringify(after.parent.entry)===JSON.stringify(target.parent.entry),{expected_url:target.parent.url,actual_url:after.parent.url,expected_entry:target.parent.entry,actual_entry:after.parent.entry,ui:after.child.workspace});
      queryCheck(scope,'query_'+action+'_'+kind,after,new URL(target.parent.url).search);
    }
    const beforeHistory=await state(page,'query_before_scenario_view');await selectRealView(page,'history');await page.waitForURL(u=>u.searchParams.get('view')==='history');
    const history=await settledState(page,'query_scenario_view',page.url(),{generation:beforeHistory.child.generation,acceptedAfter:beforeHistory.child.acks});snapshots.push(history);
    f=await actualFrame(page);await f.locator('[data-im-scenario-tab="scenario"]').click();
    await f.locator('[data-im-scenario-field="local"]').fill('5.25');await f.locator('[data-im-scenario-field="fx"]').fill('-1.5');await f.locator('[data-im-scenario-action="calculate"]').click();
    const populated=await state(page,'scenario_populated');snapshots.push(populated);const ps=populated.child.workspace.scenario;
    check(scope,'scenario_retention_is_populated',ps.tab==='true'&&ps.local==='5.25'&&ps.fx==='-1.5'&&!!ps.usd.trim()&&!ps.resultHidden&&ps.confirmContextHidden&&ps.confirmResetHidden,{scenario:ps});
    const sa=await fragmentApiJourney(page,scope,'scenario_fragment','intl-growth-inflation',snapshots);
    check(scope,'scenario_retained_across_fragment_ack',JSON.stringify(sa.before.child.workspace.scenario)===JSON.stringify(sa.after.child.workspace.scenario)&&JSON.stringify(businessUi(sa.before.child.workspace))===JSON.stringify(businessUi(sa.after.child.workspace)),{before:sa.before.child.workspace.scenario,after:sa.after.child.workspace.scenario});
    // A normal fresh entry ends the draft journey; no draft-retention claim across a fresh document.
    const overview='?view=overview&market=TW&pins=&horizon=3m&basis=local&return_basis=price&group=';
    await page.goto(origin+'/intl.html'+overview+'#intl-analysis-tools',{waitUntil:'domcontentloaded'});f=await actualFrame(page);
    const os=await settledState(page,'inspector_overview_entry',origin+'/intl.html'+overview+'#intl-analysis-tools');snapshots.push(os);
    check(scope,'inspector_probe_uses_real_overview_query',os.child.workspace.view==='overview'&&os.child.workspace.horizon==='3m'&&os.child.workspace.basis==='local'&&!invalidWarning(os.child.workspace),{ui:businessUi(os.child.workspace)});
    await f.locator('[data-im-inspector-trigger]:visible').first().click();
    const dialog=f.locator('dialog[data-im-inspector-shell]');await dialog.waitFor({state:'visible'});
    await dialog.locator('[data-im-inspector-action="evidence"]:visible, [data-im-inspector-ledger-trigger]:visible').first().click();
    const piState=await state(page,'inspector_evidence_open');snapshots.push(piState);const pi=piState.child.workspace.inspector;
    check(scope,'inspector_retention_is_nonvacuous',pi.open&&pi.modal&&!!pi.payloadNode&&!!pi.context&&pi.ledger.exists&&!pi.ledger.hidden&&pi.ledger.open&&pi.ledger.rendered&&pi.pages.some(p=>p.page==='read'&&p.hidden)&&pi.pages.some(p=>p.page==='ledger'&&!p.hidden),{inspector:pi});
    const ia=await fragmentApiJourney(page,scope,'inspector_fragment','intl-dollar-conditions',snapshots);
    check(scope,'inspector_retained_across_fragment_ack',JSON.stringify(ia.before.child.workspace.inspector)===JSON.stringify(ia.after.child.workspace.inspector)&&JSON.stringify(businessUi(ia.before.child.workspace))===JSON.stringify(businessUi(ia.after.child.workspace)),{before:ia.before.child.workspace.inspector,after:ia.after.child.workspace.inspector});
  }
  await screenshot(page,scope+'-final');
}

// BEGIN exact cached-response custody
function cachedResponseEvidence(row, observed) {
  let url;
  try { url = new URL(row.url); } catch { return null; }
  if (row.status !== 304 || row.method !== 'GET' || row.body_error ||
      !Number.isSafeInteger(row.sequence) || row.sequence < 1 ||
      url.origin !== childOrigin || !expected[url.pathname]) return null;
  const prior = observed.find(candidate => {
    if (candidate.scope !== row.scope || candidate.url !== row.url ||
        !Number.isSafeInteger(candidate.sequence) || candidate.sequence < 1 ||
        candidate.sequence >= row.sequence || candidate.status !== 200 ||
        candidate.method !== 'GET' || candidate.matches !== true ||
        candidate.body_error || candidate.sha256 !== expected[url.pathname]) return false;
    // If-None-Match takes precedence when both conditional headers are present.
    if (row.if_none_match !== null) {
      return !!candidate.etag && row.if_none_match === candidate.etag;
    }
    return !!row.if_modified_since && !!candidate.last_modified &&
      row.if_modified_since === candidate.last_modified;
  });
  if (!prior) return null;
  return {
    kind: '304 revalidation of an earlier exact-URL, hash-verified 200 response',
    prior_sequence: prior.sequence,
    cached_sha256: prior.sha256,
    validator: row.if_none_match !== null ? 'If-None-Match' : 'If-Modified-Since',
    validator_value: row.if_none_match !== null ? row.if_none_match : row.if_modified_since
  };
}
// END exact cached-response custody

// BEGIN final captured-asset custody
function finalChildAssetCustody(responses) {
  const actual = responses.filter(row => {
    try { const url = new URL(row.url); return url.origin === childOrigin && !!expected[url.pathname]; }
    catch { return false; }
  });
  for (const row of actual) {
    if (row.status === 304) {
      row.revalidation = cachedResponseEvidence(row, actual);
      row.matches = !!row.revalidation;
    }
  }
  const bad = actual.filter(row => row.body_error || row.method !== 'GET' ||
    !(row.status === 200 && row.matches === true && row.sha256 === expected[new URL(row.url).pathname] ||
      row.status === 304 && row.matches === true && row.revalidation));
  return { actual, bad };
}
// END final captured-asset custody

function documentedAnonymousRefusal(row){
  const u=new URL(row.url);
  return u.origin===childOrigin&&!u.search&&['/api/me','/api/account'].includes(u.pathname)&&row.method==='GET'&&row.status===401&&!row.body_error&&row.body_state==='complete'&&row.anonymous_missing_bearer===true&&/application\/json/i.test(row.content_type||'')&&/\bprivate\b/i.test(row.cache_control||'')&&/\bno-store\b/i.test(row.cache_control||'');
}
function cachedParentEvidence(row,observed){
  const url=new URL(row.url),expectedRow=parentExpected[url.pathname];
  if(url.origin!==origin||!expectedRow||row.status!==304||row.method!=='GET'||row.body_error||!Number.isSafeInteger(row.sequence))return null;
  const prior=observed.find(r=>r.scope===row.scope&&r.url===row.url&&r.sequence<row.sequence&&r.sequence>0&&r.status===200&&r.method==='GET'&&r.parent_matches===true&&!r.body_error&&r.sha256===expectedRow.sha256&&r.bytes===expectedRow.bytes&&(row.if_none_match!==null?!!r.etag&&row.if_none_match===r.etag:!!row.if_modified_since&&!!r.last_modified&&row.if_modified_since===r.last_modified));
  return prior?{kind:'Exact-URL parent static revalidation against earlier host-bound200',prior_sequence:prior.sequence,cached_sha256:prior.sha256,validator:row.if_none_match!==null?'If-None-Match':'If-Modified-Since',validator_value:row.if_none_match!==null?row.if_none_match:row.if_modified_since}:null;
}
function parentDocumentIdentity(body,row){
  const html=body.toString(),htmlIds=[...html.matchAll(/data-dpl-id=["']([^"']+)["']/g)].map(x=>x[1]);
  const urls=[...html.matchAll(/(?:src|href)=["']([^"']*\/_next\/static\/[^"']+)["']/g)].map(x=>new URL(x[1].replace(/&amp;/g,'&'),origin).href);
  const parameters=urls.map(x=>new URL(x).searchParams.get('dpl')).filter(Boolean);
  const values=[...htmlIds,...parameters,...(row.deployment_header?[row.deployment_header]:[])];
  const urlsBound=urls.length>0&&urls.every(x=>{const u=new URL(x);return u.origin===origin&&!!parentExpected[u.pathname]&&(!u.searchParams.has('dpl')||u.searchParams.get('dpl')===release.parent.source_commit);});
  return {html_ids:htmlIds,static_urls:urls,query_ids:parameters,header:row.deployment_header,urls_bound_to_parent_host:urlsBound,verified:values.length>0&&values.every(x=>x===release.parent.source_commit)&&urlsBound};
}
function finalParentCustody(responses){
  const actual=responses.filter(r=>new URL(r.url).origin===origin&&(r.resource_type==='document'||new URL(r.url).pathname.startsWith('/_next/static/')));
  for(const row of actual)if(row.status===304){row.parent_revalidation=cachedParentEvidence(row,actual);row.parent_matches=!!row.parent_revalidation;}
  const bad=actual.filter(r=>{
    const u=new URL(r.url),dpl=u.searchParams.get('dpl');
    if(r.method!=='GET'||r.body_error||dpl&&dpl!==release.parent.source_commit)return true;
    if(r.resource_type==='document')return r.status!==200||!Number.isSafeInteger(r.page_id)||r.page_id<1||!r.sha256||!r.document_identity?.verified||!actual.some(a=>a.scope===r.scope&&Number.isSafeInteger(a.page_id)&&a.page_id===r.page_id&&new URL(a.url).pathname.startsWith('/_next/static/')&&a.status===200&&a.parent_matches===true&&!a.body_error);
    const pin=parentExpected[u.pathname];
    return !pin||!(r.status===200&&r.parent_matches===true&&r.sha256===pin.sha256&&r.bytes===pin.bytes||r.status===304&&r.parent_revalidation);
  });
  return {actual,bad};
}
async function drainNetwork(tasks,scope,pageFilter=null){
  const until=Date.now()+20000;
  let previous=-1;
  while(Date.now()<until){
    const count=tasks.length;
    await Promise.allSettled(tasks.slice());
    const active=report.requests.filter(r=>r.scope===scope&&r.first_party&&(pageFilter===null||r.page_id===pageFilter)&&r.terminal==='pending');
    if(count===tasks.length&&previous===count&&active.length===0)return {settled:true};
    previous=count;
    await new Promise(resolve=>setTimeout(resolve,100));
  }
  return {settled:false,pending:report.requests.filter(r=>r.scope===scope&&r.first_party&&(pageFilter===null||r.page_id===pageFilter)&&r.terminal==='pending').map(r=>({id:r.request_id,url:r.url,type:r.resource_type}))};
}

async function run(browser,width,lang,theme,query='',profile=''){
  const scope=width+'-'+lang+'-'+theme+(profile?'-'+profile:query?'-query':'');
  const context=await browser.newContext({viewport:{width,height:width===1440?900:1024},locale:lang==='zh'?'zh-CN':'en-US',colorScheme:theme});
  await context.addInitScript(({origin,childOrigin,lang,theme})=>{
    if(location.origin!==origin&&location.origin!==childOrigin)return;
    if(location.origin===origin){localStorage.setItem('mm.lang',lang);localStorage.setItem('mmx.shell.theme',theme);}
    window.__intlProofEvents=[];window.__intlProofPreInit=[];window.__intlProofLocations=[];
    const identities=new WeakMap();let nextIdentity=0;
    const identity=node=>{if(!node)return null;if(!identities.has(node))identities.set(node,++nextIdentity);return identities.get(node);};
    const ancestorState=node=>{
      const rows=[];for(let n=node;n&&n.nodeType===1;n=n.parentElement){
        const s=getComputedStyle(n);
        if(n.hidden||n.inert||s.display==='none'||s.visibility==='hidden'||n.tagName==='DETAILS'&&!n.open)
          rows.push({tag:n.tagName,id:n.id,hidden:n.hidden===true,inert:n.inert===true,display:s.display,visibility:s.visibility,closed:n.tagName==='DETAILS'&&!n.open});
      }return rows;
    };
    window.__intlProofWorkspaceSnapshot=()=>{
      const root=document.querySelector('[data-im-workspace][data-im-mode="macro"]'),q=s=>root?.querySelector(s);
      const control=a=>q('[data-im-controls] select[data-im-action="'+a+'"]')?.value??null;
      const library=q('#im-catalogue-library'),input=q('#im-catalogue-library-search'),hp=q('[data-im-history-panel]');
      const box=input?.getBoundingClientRect(),style=input?getComputedStyle(input):null;
      let projection=null,readerError=null;const reader=window.MMXSharedShell?.readPageSearch;
      if(typeof reader==='function'){try{projection=reader.call(window.MMXSharedShell);}catch(e){readerError=String(e);}}
      const dialog=q('dialog[data-im-inspector-shell]'),payload=dialog?.querySelector('[data-im-inspector-payload]');
      const scenario=q('[data-im-history-subview="scenario"]');
      return {readyState:document.readyState,rawSearch:location.search,bridgeActive:window.MMXSharedShell?.active===true,readerType:typeof reader,projection,readerError,
        mounted:root?.getAttribute('data-im-enhanced')==='true',controlsDisabled:q('[data-im-controls]')?.disabled??null,
        view:control('set_view'),horizon:control('set_horizon'),basis:control('set_basis'),market:hp?.querySelector('select[data-im-action="select_market"]')?.value??null,
        historyHidden:hp?.hidden??null,historyMarkets:[...(hp?.querySelectorAll('[data-im-history-market]')||[])].map(n=>({market:n.getAttribute('data-im-history-market'),hidden:n.hidden})),
        pressedViews:[...(root?.querySelectorAll('button[data-im-action="set_view"][aria-pressed="true"]')||[])].map(n=>n.getAttribute('data-im-view')),
        issues:q('[data-im-issues]')?.textContent||'',unavailable:q('[data-im-unavailable]')?.textContent||'',
        library:{exists:!!library,hidden:library?.hidden??null,enhanced:library?.getAttribute('data-im-library-enhanced')==='true',activeGroups:[...(library?.querySelectorAll('[data-im-library-group][data-im-library-active]')||[])].map(n=>n.getAttribute('data-im-library-group')),
          input:{exists:!!input,disabled:input?.disabled??null,matchesDisabled:input?.matches(':disabled')??null,rects:input?.getClientRects().length??0,rect:box?{x:box.x,y:box.y,width:box.width,height:box.height}:null,display:style?.display||null,visibility:style?.visibility||null,blockedAncestors:ancestorState(input)}},
        scenario:{node:identity(scenario),tab:q('[data-im-scenario-tab="scenario"]')?.getAttribute('aria-pressed')||null,local:q('[data-im-scenario-field="local"]')?.value??null,fx:q('[data-im-scenario-field="fx"]')?.value??null,
          resultNode:identity(q('[data-im-scenario-result]')),result:q('[data-im-scenario-result]')?.textContent||'',resultHidden:q('[data-im-scenario-result]')?.hidden??null,usd:q('[data-im-scenario-usd]')?.textContent||'',context:q('[data-im-scenario-context]')?.textContent||'',
          confirmContextHidden:q('[data-im-scenario-confirm-context]')?.hidden??null,confirmResetHidden:q('[data-im-scenario-confirm-reset]')?.hidden??null},
        inspector:{dialogNode:identity(dialog),open:dialog?.open===true,modal:dialog?.matches(':modal')===true,payloadNode:identity(payload),payloadId:payload?.id||null,market:payload?.getAttribute('data-market-id')||null,context:payload?.getAttribute('data-im-inspector-context')||null,
          ledger:(()=>{const n=payload?.querySelector('details[data-im-inspector-ledger]');return {exists:!!n,node:identity(n),hidden:n?.hidden??null,open:n?.open??null,rendered:!!n&&n.getClientRects().length>0&&getComputedStyle(n).display!=='none'&&getComputedStyle(n).visibility!=='hidden'};})(),pages:[...(payload?.querySelectorAll('[data-im-inspector-page]')||[])].map(n=>({page:n.getAttribute('data-im-inspector-page'),hidden:n.hidden})),focus:identity(document.activeElement),focusId:document.activeElement?.id||'',focusTag:document.activeElement?.tagName||null}
      };
    };
    window.addEventListener('mmx:shell-location',()=>{window.__intlProofLocations.push({at:Date.now(),href:location.href,generation:new URL(location.href).searchParams.get('mmx_generation')});if(window.__intlProofLocations.length>120)window.__intlProofLocations.shift();},true);
    window.addEventListener('message',event=>{
      const d=event.data;if(!d||d.protocol!=='mmx.shared-shell.v1')return;
      const frame=location.origin===origin?document.querySelector('iframe[data-shared-shell-frame]'):null;
      const fromChild=!!frame&&event.source===frame.contentWindow&&event.origin===childOrigin;
      const fromParent=window!==window.parent&&event.source===window.parent&&event.origin===origin;
      if(!fromChild&&!fromParent)return;
      const boundedView=v=>v&&Number.isFinite(v.x)&&Number.isFinite(v.y)?{x:v.x,y:v.y,...(typeof v.focusId==='string'?{focusId:v.focusId}:{})}:null;
      if(fromParent&&d.type==='INIT'&&d.frameGeneration===new URL(location.href).searchParams.get('mmx_generation')){
        window.__intlProofPreInit.push({at:Date.now(),generation:d.frameGeneration,canonicalPath:d.canonicalPath,restore:boundedView(d.restore),snapshot:window.__intlProofWorkspaceSnapshot()});
        if(window.__intlProofPreInit.length>8)window.__intlProofPreInit.shift();
      }
      const frameExposure=fromChild?{hidden:frame.hidden,inert:frame.inert,ariaHidden:frame.getAttribute('aria-hidden'),rects:frame.getClientRects().length,ancestors:ancestorState(frame)}:null;
      window.__intlProofEvents.push({frameExposure,type:d.type,origin:event.origin,generation:d.frameGeneration,href:d.href||d.canonicalPath||null,requestId:d.requestId||null,at:Date.now(),...(d.type==='VIEW_STATE'?{view:boundedView(d.view)}:{}),...(d.type==='INIT'?{restore:boundedView(d.restore)}:{})});
      if(window.__intlProofEvents.length>120)window.__intlProofEvents.shift();
    },true);
  },{origin,childOrigin,lang,theme});
  const contextPending=[];
  const diagnosticPages=new WeakSet();
  function attachDiagnostics(p){
    if(diagnosticPages.has(p))return;diagnosticPages.add(p);const id=pageId(p);
    p.on('pageerror',e=>report.page_errors.push({scope,page_id:id,error:String(e)}));
    p.on('console',m=>{if(m.type()==='error')report.console_errors.push({scope,page_id:id,text:m.text().slice(0,600),location:m.location()});});
  }
  context.on('page',attachDiagnostics);
  const requestRecord=request=>{
    if(requestRecords.has(request)){
      const existing=requestRecords.get(request);
      if(existing.page_id===null){
        try{existing.page_id=pageId(request.frame().page());}catch{}
        if(existing.page_id!==null)for(const responseRow of report.responses)if(responseRow.request_id===existing.request_id)responseRow.page_id=existing.page_id;
      }
      return existing;
    }
    const u=new URL(request.url());let id=null;try{id=pageId(request.frame().page());}catch{}
    const row={scope,request_id:++requestSequence,page_id:id,url:request.url(),method:request.method(),resource_type:request.resourceType(),first_party:u.origin===origin||u.origin===childOrigin,started_at:new Date().toISOString(),terminal:'pending'};
    requestRecords.set(request,row);report.requests.push(row);return row;
  };
  context.on('request',requestRecord);
  context.on('requestfinished',request=>{const row=requestRecord(request);row.terminal='finished';row.finished_at=new Date().toISOString();});
  context.on('requestfailed',request=>{
    const row=requestRecord(request);row.terminal='failed';row.finished_at=new Date().toISOString();row.error=request.failure()?.errorText||'Unspecified request failure';
    report.request_failures.push({...row,classification:'Unwaived failure; navigation or cleanup does not automatically excuse it'});
  });
  context.on('response',response=>{
    const u=new URL(response.url()),request=requestRecord(response.request());
    if(u.origin!==origin&&u.origin!==childOrigin)return;
    const headers=response.headers();
    const row={scope,url:response.url(),sequence:++responseSequence,request_id:request.request_id,page_id:request.page_id,status:response.status(),method:request.method,resource_type:request.resource_type,body_state:'pending',
      content_type:headers['content-type']||null,cache_control:headers['cache-control']||null,csp:headers['content-security-policy']||null,x_frame_options:headers['x-frame-options']||null,
      deployment_header:headers['x-nextjs-deployment-id']||null,last_modified:headers['last-modified']||null,etag:headers.etag||null};
    request.response_sequence=row.sequence;report.responses.push(row);
    const task=(async()=>{
      try{
        if(row.status===304){
          const requestHeaders=await bounded(response.request().allHeaders(),15000,'Conditional headers');
          row.if_modified_since=requestHeaders['if-modified-since']||null;row.if_none_match=requestHeaders['if-none-match']||null;
          row.body_not_read='304 has no representation body; exact earlier verified200 and matching validator required';row.body_state='bodyless304';
        }else{
          if((row.content_type||'').includes('text/event-stream'))throw new Error('Unexpected streaming first-party endpoint; requires explicit contract rather than an unbounded body read');
          const b=await bounded(response.body(),15000,'Finite first-party response body');
          if(b.length>64*1024*1024)throw new Error('First-party body exceeds finite64MiB limit');
          row.sha256=hash(b);row.bytes=b.length;row.body_state='complete';
          if(u.origin===childOrigin&&expected[u.pathname])row.matches=row.sha256===expected[u.pathname];
          if(u.origin===origin&&u.pathname.startsWith('/_next/static/'))row.parent_matches=!!parentExpected[u.pathname]&&row.sha256===parentExpected[u.pathname].sha256&&row.bytes===parentExpected[u.pathname].bytes;
          if(u.origin===origin&&row.resource_type==='document')row.document_identity=parentDocumentIdentity(b,row);
          if(u.origin===origin&&u.pathname==='/api/shared-shell/status')row.body=JSON.parse(b.toString());
          if(u.origin===childOrigin&&!u.search&&['/api/me','/api/account'].includes(u.pathname)&&row.status===401){
            const auth=JSON.parse(b.toString());
            row.anonymous_missing_bearer=auth&&typeof auth==='object'&&!Array.isArray(auth)&&Object.keys(auth).length===1&&auth.detail==='missing bearer token';
          }
        }
      }catch(e){row.body_state='failed';row.body_error=String(e);}
    })();pending.push(task);contextPending.push(task);
  });
  const page=await context.newPage();page.setDefaultTimeout(8000);attachDiagnostics(page);
  const snapshots=[];
  try{
    await page.goto(origin+'/intl.html'+query+(profile?'#intl-analysis-tools':'#imc-country-JP'),{waitUntil:'domcontentloaded',timeout:60000});
    let f=await actualFrame(page);
    await f.waitForFunction(({lang,theme})=>document.documentElement.dataset.lang===lang&&document.documentElement.dataset.theme===theme,{lang,theme},{timeout:15000});
    if(profile){await queryJourney(page,scope,query,profile,snapshots);return;}
    const entry=await settledState(page,'entry',origin+'/intl.html'+query+'#imc-country-JP');snapshots.push(entry);queryCheck(scope,'entry',entry,query);
    check(scope,'parent_and_child_context',entry.parent.lang===lang&&entry.parent.theme===theme&&entry.child.lang===lang&&entry.child.theme===theme);
    check(scope,'nondefault_country_entry',entry.child.countries.length===1&&entry.child.countries[0]==='imc-country-JP');
    await f.locator('a[data-imc-country="TW"]').first().click();
    await page.waitForURL(/#imc-country-TW$/);
    const country=await settledState(page,'country',hashUrl(entry.parent.url,'imc-country-TW'),{generation:entry.child.generation,acceptedAfter:entry.child.acks});snapshots.push(country);queryCheck(scope,'country',country,query);
    check(scope,'country_selection_and_focus',country.child.countries.length===1&&country.child.countries[0]==='imc-country-TW'&&country.child.focusCountry==='imc-country-TW'&&country.child.activeTag==='SUMMARY'&&country.child.rail.length===1&&country.child.rail[0]==='#imc-country-TW');
    check(scope,'country_history_and_generation',country.parent.history===entry.parent.history+1&&country.child.generation===entry.child.generation&&country.child.transport===entry.child.transport);
    await ensureTools(page,false);
    f=await actualFrame(page);
    const tool=f.locator('a[href$="#intl-analysis-tools"]').first();
    const actualHref=await tool.getAttribute('href');
    check(scope,'actual_projected_tools_href',new URL(actualHref).origin===origin&&new URL(actualHref).pathname==='/intl.html',{actualHref});
    check(scope,'projected_tools_query',new URL(actualHref).search===query,{actual:actualHref,expected_query:query});
    if(width===1440&&lang==='en'&&theme==='dark'&&!query){
      const modifierBefore=await state(page,'modifier_before'),beforePages=context.pages();
      const popupPromise=context.waitForEvent('page',{timeout:20000});
      await tool.click({modifiers:['Meta']});
      const popup=await popupPromise;attachDiagnostics(popup);
      await popup.waitForURL(actualHref,{timeout:45000,waitUntil:'domcontentloaded'});
      await actualFrame(popup);
      const popupDrain=await drainNetwork(contextPending,scope);
      check(scope,'modified_tools_popup_actual_destination_settled',popup.url()===actualHref&&popupDrain.settled,{url:popup.url(),expected:actualHref,page_id:pageId(popup),drain:popupDrain});
      const modifierAfter=await state(page,'modifier_after');snapshots.push(modifierBefore,modifierAfter);
      check(scope,'modified_tools_leaves_current_document_unchanged',!modifierAfter.child.tools&&modifierAfter.parent.url===modifierBefore.parent.url&&modifierAfter.parent.history===modifierBefore.parent.history&&modifierAfter.child.generation===modifierBefore.child.generation&&modifierAfter.child.acks===modifierBefore.child.acks);
      for(const opened of context.pages())if(!beforePages.includes(opened))await bounded(opened.close(),15000,'Settled popup close');
    }
    const span=tool.locator('span:visible').first();
    if(await span.count())await span.click();else await tool.click();
    await page.waitForURL(/#intl-analysis-tools$/);
    await page.waitForTimeout(250);
    const first=await settledState(page,'tools_first',hashUrl(country.parent.url,'intl-analysis-tools'),{generation:country.child.generation,acceptedAfter:country.child.acks});snapshots.push(first);queryCheck(scope,'tools_first',first,query);
    check(scope,'tools_first_opens',first.child.tools);
    check(scope,'tools_keeps_anchor_focus',first.child.activeTag==='A'&&first.child.activeHref.endsWith('#intl-analysis-tools'));
    check(scope,'tools_first_history_and_generation',first.parent.history===country.parent.history+1&&first.child.generation===country.child.generation&&first.child.transport===country.child.transport);
    const visibility=await settledVisibility(page,'#intl-analysis-tools > summary');
    check(scope,'tools_arrival_visible',visibility.visible,visibility);
    if(width===1440&&lang==='en'||width===390&&lang==='zh')await screenshot(page,scope+'-tools');
    await ensureTools(page,true);
    await ensureTools(page,false);
    const closed=await state(page,'tools_manually_closed');snapshots.push(closed);
    check(scope,'tools_repeat_closed_precondition',!closed.child.tools&&closed.parent.url===first.parent.url&&closed.child.generation===first.child.generation);
    await (await actualFrame(page)).locator('a[href$="#intl-analysis-tools"]').first().click();
    await page.waitForTimeout(250);
    const repeated=await state(page,'tools_repeated');snapshots.push(repeated);queryCheck(scope,'tools_repeat',repeated,query);
    check(scope,'tools_repeat_reopens_without_ack',repeated.child.tools&&repeated.child.acks===closed.child.acks,{acks_before:closed.child.acks,acks_after:repeated.child.acks});
    check(scope,'tools_repeat_no_history_or_generation',repeated.parent.history===closed.parent.history&&repeated.child.generation===closed.child.generation);
    const repeatedVisible=await settledVisibility(page,'#intl-analysis-tools > summary');
    check(scope,'tools_repeat_arrival_visible',repeatedVisible.visible,repeatedVisible);
    for(const [action,expectedUrl,kind] of [['goBack',country.parent.url,'country'],['goForward',first.parent.url,'tools']]){
      const beforeHistory=await state(page,'history_before');
      await page[action]({waitUntil:'domcontentloaded',timeout:20000});
      await page.waitForURL(expectedUrl,{timeout:12000});
      const afterHistory=await settledState(page,action+'_'+kind,expectedUrl,{generation:beforeHistory.child.generation,changed:true});snapshots.push(afterHistory);queryCheck(scope,action+'_'+kind,afterHistory,query);
      const opened=kind==='tools'?afterHistory.child.tools:afterHistory.child.countries.includes('imc-country-TW');
      check(scope,action+'_'+kind+'_opens_fresh_generation',opened&&afterHistory.child.generation!==beforeHistory.child.generation&&afterHistory.parent.history===beforeHistory.parent.history,{parent_url:afterHistory.parent.url,expected_url:expectedUrl});
    }
    if(query){
      const preserved=await state(page,'query_preservation_before_view_change');snapshots.push(preserved);
      check(scope,'business_query_preserved',new URL(preserved.parent.url).search===query,{actual_search:new URL(preserved.parent.url).search,expected_query:query});
    }
    await ensureTools(page,true);
    f=await actualFrame(page);
    const beforeLibrary=await state(page,'before_library');
    const libraryButton=f.locator('button[data-im-action="set_view"][data-im-view="library"]');
    if(await libraryButton.isVisible())await libraryButton.click();
    else await f.locator('select[data-im-action="set_view"]').selectOption('library');
    await page.waitForURL(u=>u.searchParams.get('view')==='library');
    const selectedLibrary=await settledState(page,'library_selected',page.url(),{generation:beforeLibrary.child.generation,acceptedAfter:beforeLibrary.child.acks});
    snapshots.push(selectedLibrary);
    let acceptedLibrary=selectedLibrary;
    f=await actualFrame(page);
    const libraryLink=f.locator('[data-im-library-group="leaders"] a[href$="#intl-leadership-rotation"]').first();
    const libraryBefore=await f.locator('[data-im-library-group="leaders"]').evaluate(group=>({
      id:group.id,active:group.hasAttribute('data-im-library-active'),hidden:group.hidden,
      mobile:matchMedia('(max-width:600px)').matches,
      links:[...group.querySelectorAll('a[href$="#intl-leadership-rotation"]')].map(a=>({
        href:a.getAttribute('href'),visible:a.checkVisibility({checkVisibilityCSS:true}),
        ancestors:[...function*(n){for(;n&&n!==document.body;n=n.parentElement)yield n;}(a)].map(n=>({
          tag:n.tagName,id:n.id,display:getComputedStyle(n).display,visibility:getComputedStyle(n).visibility,
          hidden:n.hidden===true,open:n.tagName==='DETAILS'?n.open:null
        }))
      }))
    }));
    if(!await libraryLink.isVisible()){
      // Below 600px the actual Library hides tools until their real group control
      // is selected. Exercise that user action and its genuine accepted location.
      const groupControl=f.locator('button[data-im-action="set_library_group"][data-im-group="leaders"]');
      await groupControl.waitFor({state:'visible'});
      const control=await groupControl.evaluate(el=>({action:el.getAttribute('data-im-action'),group:el.getAttribute('data-im-group'),text:el.innerText}));
      await groupControl.click();
      await page.waitForURL(u=>u.searchParams.get('view')==='library'&&u.searchParams.get('group')==='leaders');
      acceptedLibrary=await settledState(page,'library_group_selected',page.url(),{generation:selectedLibrary.child.generation,acceptedAfter:selectedLibrary.child.acks});
      snapshots.push(acceptedLibrary);
      await libraryLink.waitFor({state:'visible'});
      const active=await f.locator('[data-im-library-group="leaders"]').evaluate(el=>el.hasAttribute('data-im-library-active'));
      check(scope,'library_group_selected_through_real_control',libraryBefore.mobile&&active&&await libraryLink.isVisible()&&acceptedLibrary.parent.history===selectedLibrary.parent.history+1&&acceptedLibrary.child.generation===selectedLibrary.child.generation,{before:libraryBefore,control,accepted_url:acceptedLibrary.parent.url});
    }
    await libraryLink.waitFor({state:'visible'});
    check(scope,'library_selected_through_real_control',await libraryLink.isVisible(),{before:libraryBefore,accepted_url:acceptedLibrary.parent.url});
    await ensureTools(page,false);
    const afterViewClosed=await state(page,'tools_after_view_closed');snapshots.push(afterViewClosed);
    f=await actualFrame(page);
    const afterViewTool=f.locator('a[href$="#intl-analysis-tools"]').first();
    const afterViewHref=await afterViewTool.getAttribute('href');
    check(scope,'tools_after_view_closed_precondition',!afterViewClosed.child.tools&&afterViewClosed.parent.url===acceptedLibrary.parent.url&&afterViewClosed.child.generation===acceptedLibrary.child.generation,{projected_href:afterViewHref,business_query:new URL(acceptedLibrary.parent.url).search});
    if(phase==='candidate')check(scope,'candidate_fragment_api_present',afterViewClosed.child.fragmentApi==='function');
    await afterViewTool.click();
    const afterViewOpen=await settledState(page,'tools_after_view',hashUrl(acceptedLibrary.parent.url,'intl-analysis-tools'),{generation:acceptedLibrary.child.generation,acceptedAfter:acceptedLibrary.child.acks});snapshots.push(afterViewOpen);
    check(scope,'tools_after_query_change_opens',afterViewOpen.child.tools,{projected_href:afterViewHref,accepted_url:afterViewOpen.parent.url});
    check(scope,'tools_after_query_change_history',afterViewOpen.parent.history===acceptedLibrary.parent.history+1&&afterViewOpen.child.generation===acceptedLibrary.child.generation);
    queryCheck(scope,'tools_after_query_change',afterViewOpen,new URL(acceptedLibrary.parent.url).search);
    await ensureTools(page,true);await ensureTools(page,false);
    const afterViewRepeatClosed=await state(page,'tools_after_view_repeat_closed');
    check(scope,'tools_after_view_repeat_closed_precondition',!afterViewRepeatClosed.child.tools&&afterViewRepeatClosed.parent.url===afterViewOpen.parent.url);
    await (await actualFrame(page)).locator('a[href$="#intl-analysis-tools"]').first().click();await page.waitForTimeout(250);
    const afterViewRepeat=await state(page,'tools_after_view_repeated');snapshots.push(afterViewRepeat);
    check(scope,'tools_after_query_repeat_opens_without_navigation',afterViewRepeat.child.tools&&afterViewRepeat.child.acks===afterViewRepeatClosed.child.acks&&afterViewRepeat.parent.history===afterViewRepeatClosed.parent.history&&afterViewRepeat.child.generation===afterViewRepeatClosed.child.generation);
    queryCheck(scope,'tools_after_query_repeat',afterViewRepeat,new URL(acceptedLibrary.parent.url).search);
    await ensureTools(page,true);
    f=await actualFrame(page);
    const beforeNested=await state(page,'before_nested_after_view_tools');snapshots.push(beforeNested);
    await f.locator('[data-im-library-group="leaders"] a[href$="#intl-leadership-rotation"]').first().click();
    await page.waitForURL(/#intl-leadership-rotation$/);
    await page.waitForTimeout(250);
    const nested=await settledState(page,'nested_first',hashUrl(beforeNested.parent.url,'intl-leadership-rotation'),{generation:beforeNested.child.generation,acceptedAfter:beforeNested.child.acks});snapshots.push(nested);queryCheck(scope,'nested_first',nested,new URL(beforeNested.parent.url).search);
    const nestedOpen=await nestedState(page);
    check(scope,'nested_first_opens_all_ancestors',nestedOpen.allOpen,nestedOpen);
    check(scope,'nested_keeps_anchor_focus',nested.child.activeTag==='A'&&nested.child.activeHref.endsWith('#intl-leadership-rotation'));
    check(scope,'nested_first_history_and_generation',nested.parent.history===beforeNested.parent.history+1&&nested.child.generation===beforeNested.child.generation);
    const nestedVisible=await settledVisibility(page,'#intl-leadership-rotation');
    check(scope,'nested_arrival_visible',nestedVisible.visible,nestedVisible);
    if(width===1440&&lang==='en'||width===390&&lang==='zh')await screenshot(page,scope+'-nested');
    f=await actualFrame(page);
    const fold=f.locator('#intl-leadership-rotation').locator('xpath=ancestor::details[1]');
    if(await fold.evaluate(el=>el.open))await fold.locator(':scope > summary').click();
    if(await f.locator('#intl-legacy-research').evaluate(el=>el.open))await f.locator('#intl-legacy-research > summary').click();
    const nestedClosed=await state(page,'nested_manually_closed');snapshots.push(nestedClosed);
    const closedAncestors=await nestedState(page);
    check(scope,'nested_repeat_closed_precondition',closedAncestors.ancestors.filter(x=>x.id!=='intl-analysis-tools').every(x=>!x.open)&&closedAncestors.ancestors.some(x=>x.id==='intl-legacy-research'&&!x.open)&&nestedClosed.child.tools&&nestedClosed.parent.url===nested.parent.url&&nestedClosed.child.generation===nested.child.generation,closedAncestors);
    await (await actualFrame(page)).locator('[data-im-library-group="leaders"] a[href$="#intl-leadership-rotation"]').first().click();
    await page.waitForTimeout(250);
    const nestedRepeat=await state(page,'nested_repeated');snapshots.push(nestedRepeat);queryCheck(scope,'nested_repeat',nestedRepeat,new URL(beforeNested.parent.url).search);
    const reopened=await nestedState(page);
    check(scope,'nested_repeat_reopens_without_ack',reopened.allOpen&&nestedRepeat.child.acks===nestedClosed.child.acks,reopened);
    check(scope,'nested_repeat_no_history_or_generation',nestedRepeat.parent.history===nestedClosed.parent.history&&nestedRepeat.child.generation===nestedClosed.child.generation);
    const nestedRepeatVisible=await settledVisibility(page,'#intl-leadership-rotation');
    check(scope,'nested_repeat_arrival_visible',nestedRepeatVisible.visible,nestedRepeatVisible);
    // One discriminating restoration probe: save a real focused view far from the
    // URL fragment, then let the actual parent own Back/Forward restoration.
    let restoreSeed=null;
    if(width===1440&&lang==='en'&&theme==='dark'&&!query){
      f=await actualFrame(page);
      if(!await f.locator('#intl-legacy-research').evaluate(el=>el.open))await f.locator('#intl-legacy-research > summary').click();
      const restoreFold=f.locator('#intl-leadership-rotation').locator('xpath=ancestor::details[1]');
      if(!await restoreFold.evaluate(el=>el.open))await restoreFold.locator(':scope > summary').click();
      const heading=await f.locator('#intl-leadership-rotation').evaluate(el=>({y:scrollY+el.getBoundingClientRect().top,viewport:innerHeight}));
      const input=f.locator('#im-catalogue-library-search'),enabled=await input.isEnabled();
      if(!enabled)throw new Error('The existing Library search input is not enabled');
      const seedStart=Date.now();
      await input.click();
      await page.mouse.wheel(0,80);
      const deadline=Date.now()+5000;let seeded,viewEvent;
      do{
        await page.waitForTimeout(100);
        seeded=await state(page,'restoration_seed');
        viewEvent=seeded.parent.events.filter(e=>e.type==='VIEW_STATE'&&e.generation===seeded.child.generation&&e.at>=seedStart&&e.view?.focusId==='im-catalogue-library-search').at(-1);
        if(viewEvent&&seeded.child.activeId===viewEvent.view.focusId&&Math.abs(seeded.child.scroll.y-viewEvent.view.y)<=2&&Math.abs(seeded.child.scroll.x-viewEvent.view.x)<=2)break;
      }while(Date.now()<deadline);
      if(!viewEvent)throw new Error('No actual parent-observed VIEW_STATE for the focused Library input');
      restoreSeed={parent_url:seeded.parent.url,entry:seeded.parent.entry,history:seeded.parent.history,generation:seeded.child.generation,view:viewEvent.view,heading,observed_at:viewEvent.at};
      check(scope,'restoration_saved_view_is_discriminating',enabled&&!!restoreSeed.entry&&seeded.child.activeId===restoreSeed.view.focusId&&heading.y>restoreSeed.view.y+heading.viewport+64&&Math.abs(seeded.child.scroll.y-restoreSeed.view.y)<=2,{seed:restoreSeed});
      snapshots.push(seeded);
    }
    for(const [action,expectedUrl,kind] of [['goBack',beforeNested.parent.url,'library'],['goForward',nested.parent.url,'nested']]){
      const before=await state(page,'history_before');
      await page[action]({waitUntil:'domcontentloaded',timeout:20000});
      await page.waitForURL(expectedUrl,{timeout:12000});
      const after=await settledState(page,action+'_'+kind,expectedUrl,{generation:before.child.generation,changed:true});snapshots.push(after);queryCheck(scope,action+'_'+kind,after,new URL(expectedUrl).search);
      const opened=kind==='nested'?(await nestedState(page)).allOpen:true;
      check(scope,action+'_'+kind+'_restores_url_and_generation',opened&&after.parent.url===expectedUrl&&after.child.generation!==before.child.generation&&after.parent.history===before.parent.history,{parent_url:after.parent.url,expected_url:expectedUrl});
      if(kind==='nested'&&restoreSeed){
        await page.waitForTimeout(1300);
        const firstRestored=await state(page,'restoration_after_corrections');
        await page.waitForTimeout(200);
        const secondRestored=await state(page,'restoration_stable');
        const init=secondRestored.child.events.find(e=>e.type==='INIT'&&e.generation===secondRestored.child.generation);
        const early=secondRestored.child.preInit.find(e=>e.generation===secondRestored.child.generation&&e.restore?.focusId===restoreSeed.view.focusId),earlyInput=early?.snapshot?.library?.input;
        check(scope,'restoration_pre_init_input_readiness',!!early&&early.snapshot.bridgeActive===false&&early.snapshot.mounted&&!early.snapshot.controlsDisabled&&early.snapshot.readerType==='function'&&early.snapshot.projection===new URL(restoreSeed.parent_url).search&&early.snapshot.view==='library'&&early.snapshot.library.hidden===false&&early.snapshot.library.enhanced&&earlyInput.exists&&!earlyInput.disabled&&!earlyInput.matchesDisabled&&earlyInput.rects>0&&earlyInput.blockedAncestors.length===0,{pre_init:early||null,parent_exposure_events:secondRestored.parent.events.filter(e=>e.generation===secondRestored.child.generation&&e.frameExposure)});
        check(scope,'restoration_entry_and_init_match_saved_view',JSON.stringify(secondRestored.parent.entry)===JSON.stringify(restoreSeed.entry)&&secondRestored.parent.history===restoreSeed.history&&secondRestored.parent.url===restoreSeed.parent_url&&secondRestored.child.generation!==restoreSeed.generation&&JSON.stringify(init?.restore)===JSON.stringify(restoreSeed.view),{seed:restoreSeed,init_restore:init?.restore||null,entry:secondRestored.parent.entry});
        const samples=[firstRestored,secondRestored];
        const scrollMatches=s=>Math.abs(s.child.scroll.x-restoreSeed.view.x)<=2&&Math.abs(s.child.scroll.y-restoreSeed.view.y)<=2;
        const focusMatches=samples.every(s=>s.child.activeId===restoreSeed.view.focusId);
        const baselineBody=samples.every(s=>s.child.activeId===''&&s.child.activeTag==='BODY');
        check(scope,'restoration_scroll_stays_stable',samples.every(scrollMatches),{expected:restoreSeed.view,samples:samples.map(s=>s.child.scroll)});
        check(scope,'restoration_focus_matches_saved_view',focusMatches,{expected_focus:restoreSeed.view.focusId,samples:samples.map(s=>({id:s.child.activeId,tag:s.child.activeTag})),known_baseline_failure:!focusMatches&&baselineBody,baseline_evidence:'baseline_parent_restoration_v7/observation.json',baseline_driver_sha256:'6eb5f118cdd7a64ba00465030b2ef12e04268c01e0af71793570e6f7b320e6c6'});
        check(scope,'restoration_settled_focus_not_changed_by_controller',focusMatches||baselineBody,{observation_window:'two settled samples after1300ms and another200ms; transient changes are not measured',samples:samples.map(s=>({id:s.child.activeId,tag:s.child.activeTag}))});
        snapshots.push(firstRestored,secondRestored);
      }
    }
  }catch(e){check(scope,'journey_completed',false,{error:String(e.stack||e)});}
  finally{
    const networkDrain=await drainNetwork(contextPending,scope);
    check(scope,'finite_network_settled_before_cleanup',networkDrain.settled,networkDrain);
    const observed=report.responses.filter(r=>r.scope===scope);
    for(const row of observed){
      if(row.status===304&&new URL(row.url).origin===childOrigin&&expected[new URL(row.url).pathname]){row.revalidation=cachedResponseEvidence(row,observed);row.matches=!!row.revalidation;}
    }
    const missing=mandatory.filter(name=>!observed.some(r=>new URL(r.url).origin===childOrigin&&new URL(r.url).pathname===name&&r.status===200&&r.matches===true));
    const bad=observed.filter(r=>new URL(r.url).origin===childOrigin&&expected[new URL(r.url).pathname]&&(r.body_error||r.matches===false||(r.matches!==undefined&&!(r.status===200||r.status===304&&r.revalidation))));
    check(scope,'all_child_assets_bound',missing.length===0&&bad.length===0,{missing,bad});
    const statuses=observed.filter(r=>new URL(r.url).origin===origin&&new URL(r.url).pathname==='/api/shared-shell/status');
    const statusGood=statusMatches;
    check(scope,'actual_runtime_contract',statuses.length>0&&statuses.every(statusGood),{responses:statuses.length});
    report.contexts.push({scope,width,lang,theme,query,profile,snapshots});save();await bounded(context.close(),15000,'Settled context close');console.log(JSON.stringify({scope,passed:report.cases.filter(c=>c.scope===scope&&c.passed).length,failed:report.cases.filter(c=>c.scope===scope&&!c.passed).map(c=>({id:c.id,error:c.error||null}))}));}
}
(async()=>{
 let browser;
 try{
   browser=await chromium.launch({channel:'chrome',headless:true});report.browser=browser.version();
   for(const width of widths)for(const [lang,theme] of presentations)await run(browser,width,lang,theme);
   if(matrix==='full'||matrix==='contract')await run(browser,1440,'en','dark','?view=history&note=a%20b&note=a+b&list=JP%2cTW&literal=JP,TW&repeat=1&repeat=2&&empty=&flag&');
   if(matrix==='full'||matrix==='query'){
     const valid='?view=history&market=%54W&pins=&horizon=3m&basis=local&return_basis=price&group=';
     for(const [profile,query] of [['ordinary',''],['valid-nondefault',valid],['invalid-unknown',valid+'&unexpected=1'],['invalid-empty',valid+'&&']])await run(browser,390,'zh','dark',query,profile);
   }
   await Promise.allSettled(pending);
   // All contexts have closed. Reclassify the complete captured population,
   // including responses that arrived after a per-context drain snapshot.
   const custody=finalChildAssetCustody(report.responses);
   check('binding','actual_child_asset_hashes',custody.actual.length>0&&custody.bad.length===0,{responses:custody.actual.length,bad:custody.bad});
   const parentResponses=report.responses.filter(r=>new URL(r.url).origin===origin);
   const parentCustody=finalParentCustody(report.responses);
   check('binding','actual_parent_document_and_static_responses',parentCustody.actual.some(r=>r.resource_type==='document'&&r.status===200)&&parentCustody.bad.length===0,{responses:parentCustody.actual.length,bad:parentCustody.bad});
   const unboundChildResources=report.responses.filter(r=>new URL(r.url).origin===childOrigin&&['script','stylesheet','font'].includes(r.resource_type)&&!expected[new URL(r.url).pathname]);
   check('binding','no_unbound_child_presentation_resources',unboundChildResources.length===0,{unbound:unboundChildResources});
   const finalStatuses=parentResponses.filter(r=>new URL(r.url).pathname==='/api/shared-shell/status');
   check('binding','complete_parent_status_contract',finalStatuses.length>0&&finalStatuses.every(statusMatches),{responses:finalStatuses.length});
   const failedRequiredRequests=report.requests.filter(r=>r.first_party&&(r.terminal!=='finished'||!r.response_sequence));
   const failedBodies=report.responses.filter(r=>r.body_error||r.body_state==='pending');
   check('binding','complete_first_party_request_and_body_settlement',failedRequiredRequests.length===0&&failedBodies.length===0,{failed_requests:failedRequiredRequests,failed_bodies:failedBodies});
   const unsupportedStatuses=report.responses.filter(r=>!(r.status>=200&&r.status<300||r.status===304&&(r.revalidation||r.parent_revalidation)||documentedAnonymousRefusal(r)));
   check('binding','explicit_first_party_http_status_contract',unsupportedStatuses.length===0,{unsupported:unsupportedStatuses,policy:'Finite successful responses;304 only with strict exact prior verified representation; only anonymous GET www/api/me and /api/account may return the exact missing-bearer401 JSON under private,no-store. No generic redirect/auth/error exemptions.'});
   const consoleFailures=report.console_errors.filter(error=>{
     const refused=report.responses.some(row=>row.scope===error.scope&&row.page_id===error.page_id&&row.url===error.location?.url&&documentedAnonymousRefusal(row));
     error.documented_anonymous_resource_notice=refused&&/^Failed to load resource: the server responded with a status of 401\b/.test(error.text);
     return !error.documented_anonymous_resource_notice;
   });
   check('runtime','no_unexpected_page_or_console_errors',report.page_errors.length===0&&consoleFailures.length===0,{page_errors:report.page_errors,console_errors:consoleFailures});
   report.passed=report.cases.filter(c=>c.passed).length;report.failed=report.cases.filter(c=>!c.passed).length;
   report.known_baseline_failures=report.cases.filter(c=>!c.passed&&c.known_baseline_failure===true).length;
   report.repair_scope_failures=report.failed-report.known_baseline_failures;
   report.status='pending_cleanup'; // A passing result is emitted only after bounded browser cleanup.
   // A known baseline focus failure remains a failure and keeps the overall exit
   // nonzero. The separate count supports scoped repair review without hiding it.
   report.finished_at=new Date().toISOString();save();
   console.log(JSON.stringify({status:report.status,passed:report.passed,failed:report.failed,contexts:report.contexts.length,report:path.join(out,'observation.json')}));
   process.exitCode=report.failed?1:0;
 }catch(e){report.status='setup_error';report.error=String(e.stack||e);save();console.error(report.error);process.exitCode=2;}
 finally{
   if(browser){
     try{await bounded(browser.close(),15000,'Owned browser cleanup');report.browser_closed=true;}
     catch(error){report.browser_closed=false;check('runtime','owned_browser_cleanup',false,{error:String(error)});}
   }
   report.passed=report.cases.filter(c=>c.passed).length;report.failed=report.cases.filter(c=>!c.passed).length;
   report.known_baseline_failures=report.cases.filter(c=>!c.passed&&c.known_baseline_failure===true).length;
   report.repair_scope_failures=report.failed-report.known_baseline_failures;
   if(report.status!=='setup_error'){report.status=report.failed||report.browser_closed!==true?'failed':'pass';process.exitCode=report.status==='pass'?0:1;}
   report.finished_at=new Date().toISOString();save();
   console.log(JSON.stringify({status:report.status,passed:report.passed,failed:report.failed,browser_closed:report.browser_closed===true,report:path.join(out,'observation.json')}));
 }

})();

} catch(error) {
  const failure={schema:'intl.production_parent_setup_failure.v1',status:'failed',failed_at:new Date().toISOString(),error:String(error.stack||error)};
  if(bootstrapOutput){
    bootFs.mkdirSync(bootstrapOutput,{recursive:true});
    const name=bootPath.join(bootstrapOutput,'setup_failure-'+Date.now()+'.json');
    bootFs.writeFileSync(name,JSON.stringify(failure,null,2)+'\n',{flag:'wx'});
    console.error(JSON.stringify({status:'setup_failed',receipt:name,error:failure.error}));
  } else console.error(JSON.stringify(failure));
  process.exitCode=2;
}
