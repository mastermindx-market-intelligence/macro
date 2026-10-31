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
const report={schema:'intl.actual_parent_acceptance.v2',phase,matrix,started_at:new Date().toISOString(),parent_source:'e45bde2cac07ac3b29285ff70c40d68900fad62c',subject:arg('source-sha'),artifact,expected,driver_sha256:hash(fs.readFileSync(__filename)),network_stubs:false,preference_setup:'Existing parent localStorage keys mm.lang and mmx.shell.theme; child context comes through real parent',contexts:[],cases:[],responses:[],screenshots:[],page_errors:[],console_errors:[],external_requests_blocked:[]};
const pending=[];
const save=()=>fs.writeFileSync(path.join(out,'observation.json'),JSON.stringify(report,null,2)+'\n');
const check=(scope,id,passed,detail={})=>report.cases.push({scope,id,passed:!!passed,...detail});
const widths=matrix==='smoke'?[1440]:[1440,768,390,320];
const presentations=matrix==='smoke'?[['en','dark']]:[['en','dark'],['en','light'],['zh','dark'],['zh','light']];
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
  const parent=await page.evaluate(()=>({url:location.href,history:history.length,theme:document.documentElement.dataset.theme,lang:document.documentElement.dataset.lang}));
  const child=await f.evaluate(()=>({url:location.href,generation:new URL(location.href).searchParams.get('mmx_generation'),transport:new URL(location.href).searchParams.get('mmx_shell'),theme:document.documentElement.dataset.theme,lang:document.documentElement.dataset.lang,tools:document.getElementById('intl-analysis-tools').open,legacy:document.getElementById('intl-legacy-research').open,countries:[...document.querySelectorAll('details.imc-country[open]')].map(e=>e.id),activeId:document.activeElement?.id||'',activeHref:document.activeElement?.getAttribute('href')||'',activeTag:document.activeElement?.tagName,focusCountry:document.activeElement?.closest('details.imc-country')?.id||'',acks:(window.__intlProofEvents||[]).filter(x=>x.type==='LOCATION_ACCEPTED').length,events:(window.__intlProofEvents||[]).slice(-16)}));
  return {label,parent,child};
}
async function visibleInParent(page,selector){
  const f=await actualFrame(page);
  const r=await f.locator(selector).evaluate(el=>{const r=el.getBoundingClientRect();return {top:r.top,bottom:r.bottom,left:r.left,right:r.right,rendered:el.getClientRects().length>0,width:r.width,height:r.height};});
  const frameBox=await page.locator('iframe[data-shared-shell-frame]').boundingBox();
  const viewport=page.viewportSize();
  return {visible:!!frameBox&&r.rendered&&r.width>0&&r.height>0&&frameBox.y+r.top<viewport.height&&frameBox.y+r.bottom>0&&frameBox.x+r.left<viewport.width&&frameBox.x+r.right>0,child_rect:r,frame:frameBox,viewport};
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
  await context.addInitScript(({origin,lang,theme})=>{
    if(location.origin===origin){localStorage.setItem('mm.lang',lang);localStorage.setItem('mmx.shell.theme',theme);}
    window.__intlProofEvents=[];
    window.addEventListener('message',event=>{
      const d=event.data;if(!d||d.protocol!=='mmx.shared-shell.v1')return;
      window.__intlProofEvents.push({type:d.type,origin:event.origin,generation:d.frameGeneration,href:d.href||d.canonicalPath||null,requestId:d.requestId||null});
      if(window.__intlProofEvents.length>120)window.__intlProofEvents.shift();
    });
  },{origin,lang,theme});
  await context.route('**/*',route=>{
    const u=new URL(route.request().url());
    if(['http:','https:'].includes(u.protocol)&&!['127.0.0.1','localhost'].includes(u.hostname)){report.external_requests_blocked.push({scope,url:u.origin+u.pathname});return route.abort('blockedbyclient');}
    return route.continue();
  });
  const page=await context.newPage();page.setDefaultTimeout(8000);
  page.on('pageerror',e=>report.page_errors.push({scope,error:String(e)}));
  page.on('console',m=>{if(m.type()==='error')report.console_errors.push({scope,text:m.text().slice(0,600)});});
  page.on('response',response=>{
    const u=new URL(response.url());
    if((u.origin===childOrigin&&expected[u.pathname])||u.pathname==='/api/shared-shell/status'){
      pending.push((async()=>{try{const b=await response.body();const row={scope,url:response.url(),status:response.status(),sha256:hash(b),bytes:b.length};if(expected[u.pathname])row.matches=hash(b)===expected[u.pathname];if(u.pathname==='/api/shared-shell/status')row.body=JSON.parse(b.toString());report.responses.push(row);}catch(e){report.responses.push({scope,url:response.url(),body_error:String(e)});}})());
    }
  });
  const snapshots=[];
  try{
    await page.goto(origin+'/intl.html'+query+'#imc-country-JP',{waitUntil:'domcontentloaded',timeout:60000});
    let f=await actualFrame(page);
    await f.waitForFunction(({lang,theme})=>document.documentElement.dataset.lang===lang&&document.documentElement.dataset.theme===theme,{lang,theme},{timeout:15000});
    const entry=await state(page,'entry');snapshots.push(entry);
    check(scope,'parent_and_child_context',entry.parent.lang===lang&&entry.parent.theme===theme&&entry.child.lang===lang&&entry.child.theme===theme);
    check(scope,'nondefault_country_entry',entry.child.countries.length===1&&entry.child.countries[0]==='imc-country-JP');
    await f.locator('a[data-imc-country="TW"]').first().click();
    await page.waitForURL(/#imc-country-TW$/);
    const country=await state(page,'country');snapshots.push(country);
    check(scope,'country_selection_and_focus',country.child.countries.length===1&&country.child.countries[0]==='imc-country-TW'&&country.child.focusCountry==='imc-country-TW'&&country.child.activeTag==='SUMMARY');
    check(scope,'country_history_and_generation',country.parent.history===entry.parent.history+1&&country.child.generation===entry.child.generation&&country.child.transport===entry.child.transport);
    await ensureTools(page,false);
    f=await actualFrame(page);
    const tool=f.locator('a[href$="#intl-analysis-tools"]').first();
    const actualHref=await tool.getAttribute('href');
    check(scope,'actual_projected_tools_href',new URL(actualHref).origin===origin&&new URL(actualHref).pathname==='/intl.html',{actualHref});
    const span=tool.locator('span:visible').first();
    if(await span.count())await span.click();else await tool.click();
    await page.waitForURL(/#intl-analysis-tools$/);
    await page.waitForTimeout(250);
    const first=await state(page,'tools_first');snapshots.push(first);
    check(scope,'tools_first_opens',first.child.tools);
    check(scope,'tools_first_history_and_generation',first.parent.history===country.parent.history+1&&first.child.generation===country.child.generation&&first.child.transport===country.child.transport);
    const visibility=await settledVisibility(page,'#intl-analysis-tools > summary');
    check(scope,'tools_arrival_visible',visibility.visible,visibility);
    if(width===1440&&lang==='en'||width===390&&lang==='zh')await screenshot(page,scope+'-tools');
    await ensureTools(page,true);
    await ensureTools(page,false);
    const closed=await state(page,'tools_manually_closed');snapshots.push(closed);
    await (await actualFrame(page)).locator('a[href$="#intl-analysis-tools"]').first().click();
    await page.waitForTimeout(250);
    const repeated=await state(page,'tools_repeated');snapshots.push(repeated);
    check(scope,'tools_repeat_reopens_without_ack',repeated.child.tools&&repeated.child.acks===closed.child.acks,{acks_before:closed.child.acks,acks_after:repeated.child.acks});
    check(scope,'tools_repeat_no_history_or_generation',repeated.parent.history===closed.parent.history&&repeated.child.generation===closed.child.generation);
    await ensureTools(page,true);
    f=await actualFrame(page);
    await f.locator('a[href$="#intl-leadership-rotation"]').first().click();
    await page.waitForURL(/#intl-leadership-rotation$/);
    await page.waitForTimeout(250);
    const nested=await state(page,'nested_first');snapshots.push(nested);
    const nestedOpen=await nestedState(page);
    check(scope,'nested_first_opens_all_ancestors',nestedOpen.allOpen,nestedOpen);
    check(scope,'nested_first_history_and_generation',nested.parent.history===repeated.parent.history+1&&nested.child.generation===repeated.child.generation);
    const nestedVisible=await settledVisibility(page,'#intl-leadership-rotation');
    check(scope,'nested_arrival_visible',nestedVisible.visible,nestedVisible);
    if(width===1440&&lang==='en'||width===390&&lang==='zh')await screenshot(page,scope+'-nested');
    f=await actualFrame(page);
    const fold=f.locator('#intl-leadership-rotation').locator('xpath=ancestor::details[1]');
    if(await fold.evaluate(el=>el.open))await fold.locator(':scope > summary').click();
    if(await f.locator('#intl-legacy-research').evaluate(el=>el.open))await f.locator('#intl-legacy-research > summary').click();
    const nestedClosed=await state(page,'nested_manually_closed');snapshots.push(nestedClosed);
    await (await actualFrame(page)).locator('a[href$="#intl-leadership-rotation"]').first().click();
    await page.waitForTimeout(250);
    const nestedRepeat=await state(page,'nested_repeated');snapshots.push(nestedRepeat);
    const reopened=await nestedState(page);
    check(scope,'nested_repeat_reopens_without_ack',reopened.allOpen&&nestedRepeat.child.acks===nestedClosed.child.acks,reopened);
    check(scope,'nested_repeat_no_history_or_generation',nestedRepeat.parent.history===nestedClosed.parent.history&&nestedRepeat.child.generation===nestedClosed.child.generation);
    for(const [action,hash,kind] of [['goBack','#intl-analysis-tools','tools'],['goBack','#imc-country-TW','country'],['goForward','#intl-analysis-tools','tools'],['goForward','#intl-leadership-rotation','nested']]){
      const before=await state(page,'history_before');
      await page[action]({waitUntil:'domcontentloaded',timeout:20000});
      await page.waitForURL(u=>u.hash===hash,{timeout:12000});
      const after=await state(page,action+'_'+kind);snapshots.push(after);
      const opened=kind==='tools'?after.child.tools:kind==='country'?after.child.countries.includes('imc-country-TW'):(await nestedState(page)).allOpen;
      check(scope,action+'_'+kind+'_opens_fresh_generation',opened&&after.child.generation!==before.child.generation,{parent_url:after.parent.url});
    }
    if(query){
      const last=await state(page,'query_preservation');
      check(scope,'business_query_preserved',new URL(last.parent.url).search===query,{actual_search:new URL(last.parent.url).search,expected_query:query});
    }
  }catch(e){check(scope,'journey_completed',false,{error:String(e.stack||e)});}
  finally{report.contexts.push({scope,width,lang,theme,query,snapshots});save();await context.close();console.log(JSON.stringify({scope,passed:report.cases.filter(c=>c.scope===scope&&c.passed).length,failed:report.cases.filter(c=>c.scope===scope&&!c.passed).map(c=>({id:c.id,error:c.error||null}))}));}
}
(async()=>{
 let browser;
 try{
   browser=await chromium.launch({channel:'chrome',headless:true});report.browser=browser.version();
   for(const width of widths)for(const [lang,theme] of presentations)await run(browser,width,lang,theme);
   if(matrix==='full')await run(browser,1440,'en','dark','?view=history');
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
