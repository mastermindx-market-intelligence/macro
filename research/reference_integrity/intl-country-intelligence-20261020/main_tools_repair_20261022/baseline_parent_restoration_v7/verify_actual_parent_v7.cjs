'use strict';
// Real supported-parent proof. No parent/child source overlay or message/response fabrication.
const { chromium } = require('/Users/chriswong/Documents/Cluade/charting-app/.claude/worktrees/intl-parent-proof-20261022/terminal/node_modules/playwright');
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const arg = name => { const i=process.argv.indexOf('--'+name); return i<0?null:process.argv[i+1]; };
const artifact=path.resolve(arg('artifact')), out=path.resolve(arg('output'));
const phase=arg('phase')||'candidate', matrix=arg('matrix')||'full';
const origin='http://127.0.0.1:3100', childOrigin='http://127.0.0.1:3102';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const expected=Object.fromEntries(['intl.html','shared_shell_bridge.js','shared_shell.css'].map(name=>['/'+name,hash(fs.readFileSync(path.join(artifact,name)))]));
fs.mkdirSync(out,{recursive:true});
if(fs.existsSync(path.join(out,'observation.json')))throw new Error('Existing observation; reconcile it rather than overwrite');
const report={schema:'intl.actual_parent_acceptance.v7',phase,matrix,started_at:new Date().toISOString(),parent_source:'e45bde2cac07ac3b29285ff70c40d68900fad62c',subject:arg('source-sha'),artifact,expected,driver_sha256:hash(fs.readFileSync(__filename)),network_stubs:false,preference_setup:'Existing parent localStorage keys mm.lang and mmx.shell.theme; child context comes through real parent',contexts:[],cases:[],responses:[],screenshots:[],page_errors:[],console_errors:[],external_requests_blocked:[]};
const pending=[];
const runtimePath=path.resolve(arg('runtime'));
const buildReceiptPath=path.resolve(arg('build-receipt'));
const runtime=JSON.parse(fs.readFileSync(runtimePath)), buildReceipt=JSON.parse(fs.readFileSync(buildReceiptPath));
const repository='/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018';
const {execFileSync}=require('node:child_process');
const controllerAt=sha=>execFileSync('git',['-C',repository,'show',sha+':templates/intl_country_cockpit.js']);
const subjectController=controllerAt(report.subject), builtController=controllerAt(buildReceipt.source_commit);
const bridgeAt=(sha,location='templates/shared_shell_bridge.js')=>execFileSync('git',['-C',repository,'show',sha+':'+location]);
const subjectBridge=bridgeAt(report.subject),builtBridge=bridgeAt(buildReceipt.source_commit),pairedBridge=bridgeAt(report.subject,'site/shared_shell_bridge.js');
report.source_binding={runtime_path:runtimePath,runtime_sha256:hash(fs.readFileSync(runtimePath)),build_receipt:buildReceiptPath,build_receipt_sha256:hash(fs.readFileSync(buildReceiptPath)),built_source:buildReceipt.source_commit,subject_controller_sha256:hash(subjectController),built_controller_sha256:hash(builtController),subject_bridge_sha256:hash(subjectBridge),built_bridge_sha256:hash(builtBridge),paired_bridge_sha256:hash(pairedBridge),delivery:'country controller inlined in hash-bound intl.html; external bridge bytes equal the exact source and paired site asset'};
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
check('binding','runtime_and_source_custody',runtime.parent_source===report.parent_source&&runtime.parent_tracked_source_clean===true&&runtime.artifact===artifact&&runtime.html_sha256===expected['/intl.html']&&buildReceipt.html_sha256===expected['/intl.html']&&buildReceipt.exit_code===0&&hash(subjectController)===hash(builtController)&&hash(subjectBridge)===hash(builtBridge)&&hash(subjectBridge)===hash(pairedBridge)&&hash(subjectBridge)===expected['/shared_shell_bridge.js']&&fs.readFileSync(path.join(artifact,'intl.html'),'utf8').includes(subjectController.toString().trim()),report.source_binding);
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
  const child=await f.evaluate(()=>({url:location.href,generation:new URL(location.href).searchParams.get('mmx_generation'),transport:new URL(location.href).searchParams.get('mmx_shell'),theme:document.documentElement.dataset.theme,lang:document.documentElement.dataset.lang,tools:document.getElementById('intl-analysis-tools').open,legacy:document.getElementById('intl-legacy-research').open,countries:[...document.querySelectorAll('details.imc-country[open]')].map(e=>e.id),activeId:document.activeElement?.id||'',activeHref:document.activeElement?.getAttribute('href')||'',activeTag:document.activeElement?.tagName,scroll:{x:scrollX,y:scrollY},fragmentApi:typeof window.MMXSharedShell?.sameDocumentFragment,rail:[...document.querySelectorAll('.imc-country-rail a[aria-current="location"]')].map(a=>a.hash),focusCountry:document.activeElement?.closest('details.imc-country')?.id||'',acks:(window.__intlProofEvents||[]).filter(x=>x.type==='LOCATION_ACCEPTED').length,events:(window.__intlProofEvents||[]).slice(-16)}));
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
async function run(browser,width,lang,theme,query=''){
  const scope=width+'-'+lang+'-'+theme+(query?'-query':'');
  const context=await browser.newContext({viewport:{width,height:width===1440?900:1024},locale:lang==='zh'?'zh-CN':'en-US',colorScheme:theme});
  await context.addCookies([{name:'mm_e2e_rs30',value:'1',url:origin},{name:'mm_e2e_guest',value:'1',url:origin}]);
  await context.addInitScript(({origin,childOrigin,lang,theme})=>{
    if(location.origin===origin){localStorage.setItem('mm.lang',lang);localStorage.setItem('mmx.shell.theme',theme);}
    window.__intlProofEvents=[];
    window.addEventListener('message',event=>{
      const d=event.data;if(!d||d.protocol!=='mmx.shared-shell.v1')return;
      const frame=location.origin===origin?document.querySelector('iframe[data-shared-shell-frame]'):null;
      const fromChild=!!frame&&event.source===frame.contentWindow&&event.origin===childOrigin;
      const fromParent=window!==window.parent&&event.source===window.parent&&event.origin===origin;
      if(!fromChild&&!fromParent)return;
      const boundedView=v=>v&&Number.isFinite(v.x)&&Number.isFinite(v.y)?{x:v.x,y:v.y,...(typeof v.focusId==='string'?{focusId:v.focusId}:{})}:null;
      window.__intlProofEvents.push({type:d.type,origin:event.origin,generation:d.frameGeneration,href:d.href||d.canonicalPath||null,requestId:d.requestId||null,at:Date.now(),...(d.type==='VIEW_STATE'?{view:boundedView(d.view)}:{}),...(d.type==='INIT'?{restore:boundedView(d.restore)}:{})});
      if(window.__intlProofEvents.length>120)window.__intlProofEvents.shift();
    });
  },{origin,childOrigin,lang,theme});
  await context.route('**/*',route=>{
    const u=new URL(route.request().url());
    if(['http:','https:'].includes(u.protocol)&&!['127.0.0.1','localhost'].includes(u.hostname)){report.external_requests_blocked.push({scope,url:u.origin+u.pathname});return route.abort('blockedbyclient');}
    return route.continue();
  });
  const contextPending=[];
  const page=await context.newPage();page.setDefaultTimeout(8000);
  page.on('pageerror',e=>report.page_errors.push({scope,error:String(e)}));
  page.on('console',m=>{if(m.type()==='error')report.console_errors.push({scope,text:m.text().slice(0,600)});});
  page.on('response',response=>{
    const u=new URL(response.url());
    if((u.origin===childOrigin&&expected[u.pathname])||u.pathname==='/api/shared-shell/status'){
      const task=(async()=>{try{const b=await response.body();const row={scope,url:response.url(),status:response.status(),sha256:hash(b),bytes:b.length};if(expected[u.pathname])row.matches=hash(b)===expected[u.pathname];if(u.pathname==='/api/shared-shell/status')row.body=JSON.parse(b.toString());report.responses.push(row);}catch(e){report.responses.push({scope,url:response.url(),body_error:String(e)});}})();pending.push(task);contextPending.push(task);
    }
  });
  const snapshots=[];
  try{
    await page.goto(origin+'/intl.html'+query+'#imc-country-JP',{waitUntil:'domcontentloaded',timeout:60000});
    let f=await actualFrame(page);
    await f.waitForFunction(({lang,theme})=>document.documentElement.dataset.lang===lang&&document.documentElement.dataset.theme===theme,{lang,theme},{timeout:15000});
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
      await tool.click({modifiers:['Meta']});await page.waitForTimeout(350);
      const modifierAfter=await state(page,'modifier_after');snapshots.push(modifierBefore,modifierAfter);
      check(scope,'modified_tools_leaves_current_document_unchanged',!modifierAfter.child.tools&&modifierAfter.parent.url===modifierBefore.parent.url&&modifierAfter.parent.history===modifierBefore.parent.history&&modifierAfter.child.generation===modifierBefore.child.generation&&modifierAfter.child.acks===modifierBefore.child.acks);
      for(const popup of context.pages())if(!beforePages.includes(popup))await popup.close();
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
    const acceptedLibrary=await settledState(page,'library_selected',page.url(),{generation:beforeLibrary.child.generation,acceptedAfter:beforeLibrary.child.acks});
    f=await actualFrame(page);
    await f.locator('a[href$="#intl-leadership-rotation"]').first().waitFor({state:'visible'});
    snapshots.push(acceptedLibrary);
    check(scope,'library_selected_through_real_control',await f.locator('a[href$="#intl-leadership-rotation"]').first().isVisible());
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
    await f.locator('a[href$="#intl-leadership-rotation"]').first().click();
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
    await (await actualFrame(page)).locator('a[href$="#intl-leadership-rotation"]').first().click();
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
      check(scope,'restoration_saved_view_is_discriminating',enabled&&!!restoreSeed.entry&&seeded.child.activeId===restoreSeed.view.focusId&&Math.abs(restoreSeed.view.y-heading.y)>heading.viewport/2&&Math.abs(seeded.child.scroll.y-restoreSeed.view.y)<=2,{seed:restoreSeed});
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
        check(scope,'restoration_entry_and_init_match_saved_view',JSON.stringify(secondRestored.parent.entry)===JSON.stringify(restoreSeed.entry)&&secondRestored.parent.history===restoreSeed.history&&secondRestored.parent.url===restoreSeed.parent_url&&secondRestored.child.generation!==restoreSeed.generation&&JSON.stringify(init?.restore)===JSON.stringify(restoreSeed.view),{seed:restoreSeed,init_restore:init?.restore||null,entry:secondRestored.parent.entry});
        const matches=s=>s.child.activeId===restoreSeed.view.focusId&&Math.abs(s.child.scroll.x-restoreSeed.view.x)<=2&&Math.abs(s.child.scroll.y-restoreSeed.view.y)<=2;
        check(scope,'restoration_scroll_and_focus_stay_stable',matches(firstRestored)&&matches(secondRestored),{expected:restoreSeed.view,samples:[firstRestored,secondRestored].map(s=>({scroll:s.child.scroll,focus:s.child.activeId}))});
        snapshots.push(firstRestored,secondRestored);
      }
    }
  }catch(e){check(scope,'journey_completed',false,{error:String(e.stack||e)});}
  finally{
    await Promise.allSettled(contextPending);
    const observed=report.responses.filter(r=>r.scope===scope);
    const missing=Object.keys(expected).filter(name=>!observed.some(r=>new URL(r.url).origin===childOrigin&&new URL(r.url).pathname===name&&r.status===200&&r.matches===true));
    const bad=observed.filter(r=>r.body_error||r.matches===false||(r.matches!==undefined&&r.status!==200));
    check(scope,'all_child_assets_bound',missing.length===0&&bad.length===0,{missing,bad});
    const statuses=observed.filter(r=>new URL(r.url).pathname==='/api/shared-shell/status');
    const statusGood=r=>r.status===200&&r.body?.enabled===true&&r.body?.protocol==='mmx.shared-shell.v1'&&r.body?.bridgeVersion==='20261018.1'&&r.body?.documentVersion==='20261018.1'&&r.body?.buildId==='development'&&r.body?.registrySha256==='5307ea5a7964fde609a8f20f1af30b6bf483b7631f7232e5db74f9ef1d710023';
    check(scope,'actual_runtime_contract',statuses.length>0&&statuses.every(statusGood),{responses:statuses.length});
    report.contexts.push({scope,width,lang,theme,query,snapshots});save();await context.close();console.log(JSON.stringify({scope,passed:report.cases.filter(c=>c.scope===scope&&c.passed).length,failed:report.cases.filter(c=>c.scope===scope&&!c.passed).map(c=>({id:c.id,error:c.error||null}))}));}
}
(async()=>{
 let browser;
 try{
   browser=await chromium.launch({channel:'chrome',headless:true});report.browser=browser.version();
   for(const width of widths)for(const [lang,theme] of presentations)await run(browser,width,lang,theme);
   if(matrix==='full'||matrix==='contract')await run(browser,1440,'en','dark','?view=history&note=a%20b&note=a+b&list=JP%2cTW&literal=JP,TW&repeat=1&repeat=2&&empty=&flag&');
   await Promise.allSettled(pending);
   const actual=report.responses.filter(r=>r.matches!==undefined);
   check('binding','actual_child_asset_hashes',actual.length>0&&actual.every(r=>r.matches),{responses:actual.length});
   check('runtime','no_page_or_console_errors',report.page_errors.length===0&&report.console_errors.length===0);
   report.passed=report.cases.filter(c=>c.passed).length;report.failed=report.cases.filter(c=>!c.passed).length;
   report.status=report.failed?(phase==='baseline'?'reproduced_failure':'failed'):'pass';
   report.finished_at=new Date().toISOString();save();
   console.log(JSON.stringify({status:report.status,passed:report.passed,failed:report.failed,contexts:report.contexts.length,report:path.join(out,'observation.json')}));
   process.exitCode=report.failed?1:0;
 }catch(e){report.status='setup_error';report.error=String(e.stack||e);save();console.error(report.error);process.exitCode=2;}
 finally{if(browser)await browser.close();}
})();
