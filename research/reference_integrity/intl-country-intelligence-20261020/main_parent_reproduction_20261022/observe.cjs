const {chromium}=require('../terminal/node_modules/playwright');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const out=__dirname;
const origin='http://127.0.0.1:3100';
const childOrigin='http://127.0.0.1:3102';
const expectedHtml='0d8beabc188333c4bb12d420c4de92c4a7ecaa9e52400fcc577067b7f4f41df8';
const report={schema:'intl.actual_parent_observation.v1',started_at:new Date().toISOString(),parent_source:'e45bde2cac07ac3b29285ff70c40d68900fad62c',child_subject_head:'64c1903c0e3193314b27edca3b662263783a9302',environment:'isolated documented development fixture; guest identity; unmodified parent and child sources',repair_effect:'unresolved; no repair attempted',network_stubs:false,cases:[],screenshots:[],console_errors:[],page_errors:[],external_requests_blocked:[],responses:[],snapshots:[]};
const pending=[];
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
function save(){fs.writeFileSync(path.join(out,'observation.json'),JSON.stringify(report,null,2)+'\n');}
(async()=>{
 let browser;
 try {
  browser=await chromium.launch({channel:'chrome',headless:true});
  report.browser=browser.version();
  const context=await browser.newContext({viewport:{width:1440,height:900},locale:'en-US',colorScheme:'dark'});
  await context.addCookies([{name:'mm_e2e_rs30',value:'1',url:origin},{name:'mm_e2e_guest',value:'1',url:origin}]);
  await context.route('**/*',route=>{
   const u=new URL(route.request().url());
   if(['http:','https:'].includes(u.protocol)&&!['127.0.0.1','localhost'].includes(u.hostname)){
    if(report.external_requests_blocked.length<40)report.external_requests_blocked.push(u.origin+u.pathname);
    return route.abort('blockedbyclient');
   }
   return route.continue();
  });
  await context.addInitScript(()=>{
   window.__intlProofEvents=[];
   window.addEventListener('message',event=>{
    if(event.data&&event.data.protocol==='mmx.shared-shell.v1'){
     const d=event.data;
     window.__intlProofEvents.push({type:d.type,origin:event.origin,generation:d.frameGeneration,href:d.href||d.canonicalPath||null,requestId:d.requestId||null});
     if(window.__intlProofEvents.length>100)window.__intlProofEvents.shift();
    }
   });
  });
  const page=await context.newPage();
  page.setDefaultTimeout(12000);
  page.on('console',m=>{if(m.type()==='error'&&report.console_errors.length<40)report.console_errors.push(m.text().slice(0,700));});
  page.on('pageerror',e=>{if(report.page_errors.length<30)report.page_errors.push(String(e));});
  page.on('response',response=>{
   const u=new URL(response.url());
   if(u.pathname==='/api/shared-shell/status'||(u.origin===childOrigin&&['/intl.html','/shared_shell_bridge.js','/shared_shell.css','/intl_country_cockpit.js'].includes(u.pathname))||(u.origin===origin&&u.pathname.startsWith('/_next/static/'))){
    pending.push((async()=>{
     try {const b=await response.body();const r={url:response.url(),status:response.status(),bytes:b.length,sha256:hash(b)};if(u.pathname==='/api/shared-shell/status')r.body=JSON.parse(b.toString());report.responses.push(r);}catch(e){report.responses.push({url:response.url(),body_error:String(e)});}
    })());
   }
  });
  async function frame(){
   await page.locator('iframe[data-shared-shell-frame][data-response-kind="content"]').waitFor({state:'visible',timeout:40000});
   const f=await (await page.locator('iframe[data-shared-shell-frame]').elementHandle()).contentFrame();
   if(!f)throw new Error('No actual child frame');
   await f.waitForSelector('#intl-analysis-tools',{state:'attached',timeout:15000});
   return f;
  }
  async function snap(label){
   const f=await frame();
   const parent=await page.evaluate(()=>({url:location.href,historyLength:history.length,root:Object.fromEntries(document.documentElement.getAttributeNames().filter(k=>/theme|lang|shell/.test(k)).map(k=>[k,document.documentElement.getAttribute(k)])),frameResponse:document.querySelector('iframe[data-shared-shell-frame]')?.getAttribute('data-response-kind'),events:window.__intlProofEvents||[]}));
   const child=await f.evaluate(()=>({url:location.href,generation:new URL(location.href).searchParams.get('mmx_generation'),historyLength:history.length,root:Object.fromEntries(document.documentElement.getAttributeNames().filter(k=>/theme|lang|shell/.test(k)).map(k=>[k,document.documentElement.getAttribute(k)])),countries:[...document.querySelectorAll('details[id^="imc-country-"]')].map(e=>({id:e.id,open:e.open})),toolsOpen:document.querySelector('#intl-analysis-tools')?.open,legacyOpen:document.querySelector('#intl-legacy-research')?.open,toolsLinks:[...document.querySelectorAll('a[href$="#intl-analysis-tools"]')].map(a=>({href:a.getAttribute('href'),text:a.textContent.trim()})),legacyLinks:[...document.querySelectorAll('a[href*="#"]')].filter(a=>!a.hasAttribute('data-imc-country')&&!a.getAttribute('href').includes('#intl-analysis-tools')).slice(0,24).map(a=>({href:a.getAttribute('href'),text:a.textContent.trim().slice(0,120)})),events:window.__intlProofEvents||[]}));
   const s={label,parent,child};report.snapshots.push(s);save();return s;
  }
  async function shot(name){const p=path.join(out,name+'.png');await page.screenshot({path:p,fullPage:false});const b=fs.readFileSync(p);report.screenshots.push({name:name+'.png',sha256:hash(b),bytes:b.length});}
  await page.goto(origin+'/intl.html#imc-country-JP',{waitUntil:'domcontentloaded',timeout:60000});
  const entry=await snap('parent_japan_deep_link');
  await shot('01-japan-entry');
  report.cases.push({id:'parent_non_default_country_entry',passed:entry.child.countries.some(x=>x.id==='imc-country-JP'&&x.open),expected:'Japan disclosure opens through the actual supported parent'});
  const f=await frame();
  await f.locator('a[data-imc-country="TW"]').first().click({timeout:12000});
  await page.waitForURL(/#imc-country-TW$/,{timeout:12000});
  const selected=await snap('child_taiwan_selection');
  report.cases.push({id:'child_country_selection',passed:selected.child.countries.some(x=>x.id==='imc-country-TW'&&x.open),expected:'Taiwan disclosure opens'});
  report.cases.push({id:'country_selection_one_history_entry',passed:selected.parent.historyLength===entry.parent.historyLength+1,actual_delta:selected.parent.historyLength-entry.parent.historyLength});
  report.cases.push({id:'country_selection_retains_generation',passed:selected.child.generation===entry.child.generation});
  await shot('02-taiwan-selection');
  if(selected.child.toolsOpen!==false)throw new Error('Tools wrapper was not closed before the discriminating click');
  const tool= (await frame()).locator('a[href$="#intl-analysis-tools"]').first();
  report.actual_tools_href=await tool.getAttribute('href');
  await tool.click({timeout:12000});
  await page.waitForURL(/#intl-analysis-tools$/,{timeout:12000});
  await page.waitForTimeout(250);
  const first=await snap('projected_tools_first_click');
  report.cases.push({id:'projected_tools_click_opens_disclosure',passed:first.child.toolsOpen===true,actual_open:first.child.toolsOpen,href:report.actual_tools_href});
  report.cases.push({id:'tools_click_retains_generation',passed:first.child.generation===selected.child.generation});
  report.cases.push({id:'tools_click_one_history_entry',passed:first.parent.historyLength===selected.parent.historyLength+1,actual_delta:first.parent.historyLength-selected.parent.historyLength});
  await shot('03-tools-first-click');
  await (await frame()).locator('a[href$="#intl-analysis-tools"]').first().click({timeout:12000});
  await page.waitForTimeout(250);
  const repeated=await snap('projected_tools_repeated_click');
  report.cases.push({id:'repeated_projected_tools_click_opens_disclosure',passed:repeated.child.toolsOpen===true,actual_open:repeated.child.toolsOpen,history_delta:repeated.parent.historyLength-first.parent.historyLength});
  await shot('04-tools-repeated-click');
  await page.goBack({waitUntil:'domcontentloaded',timeout:15000});
  const back=await snap('parent_back_after_tools');
  report.cases.push({id:'parent_back_returns_taiwan',passed:back.parent.url.endsWith('#imc-country-TW')&&back.child.countries.some(x=>x.id==='imc-country-TW'&&x.open),actual_url:back.parent.url});
  await page.goForward({waitUntil:'domcontentloaded',timeout:15000});
  const forward=await snap('parent_forward_to_tools');
  report.cases.push({id:'parent_forward_opens_tools',passed:forward.parent.url.endsWith('#intl-analysis-tools')&&forward.child.toolsOpen===true,actual_open:forward.child.toolsOpen});
  await shot('05-forward-tools');
  await Promise.allSettled(pending);
  const html=report.responses.filter(r=>r.url.startsWith(childOrigin+'/intl.html')&&r.status===200);
  report.artifact_match=html.length>0&&html.every(r=>r.sha256===expectedHtml);
  report.status=report.cases.every(c=>c.passed)&&report.artifact_match?'pass':'reproduced_failure';
  report.finished_at=new Date().toISOString();save();
  console.log(JSON.stringify({status:report.status,cases:report.cases,artifact_match:report.artifact_match,actual_tools_href:report.actual_tools_href,parent_status:report.responses.filter(r=>r.body).map(r=>r.body),page_errors:report.page_errors,screenshots:report.screenshots,report:path.join(out,'observation.json')},null,2));
 }catch(e){report.status='setup_or_observation_error';report.error=String(e.stack||e);report.finished_at=new Date().toISOString();save();console.error(report.error);process.exitCode=1;}
 finally{if(browser)await browser.close();}
})();
