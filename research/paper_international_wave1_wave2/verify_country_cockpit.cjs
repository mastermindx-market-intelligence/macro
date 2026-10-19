'use strict';
/* Isolated public fixture: no signed-in profile, external network or publication. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require(process.env.INTL_BROWSER_RUNTIME || 'playwright');
const root=path.resolve(__dirname,'../..');
const output=path.join(__dirname,'country_cockpit_preview');
const html=fs.readFileSync(path.join(output,'intl_integrated_preview.html'),'utf8');
const legacyAssets=new Set(['intl_workspace.css','intl_workspace_macro.css','intl_workspace_risk.css','intl_workspace_history.css','intl_workspace_state.js','intl_library_search.js','intl_workspace_scenario.js','intl_workspace.js','intl_workspace_entry.js']);
async function fixture(browser,{width=1440,js=true,denied=false}={}){
 const context=await browser.newContext({viewport:{width,height:width<600?844:1000},deviceScaleFactor:1,javaScriptEnabled:js});
 const page=await context.newPage();
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url());
  if(url.hostname!=='intl.test') return route.abort();
  if(url.pathname==='/intl.html') return route.fulfill({contentType:'text/html',body:html});
  if(denied && legacyAssets.has(path.basename(url.pathname))) return route.fulfill({status:401,body:'Authentication required'});
  const file=path.resolve(root,'templates','.'+url.pathname);
  if(!file.startsWith(path.join(root,'templates')+path.sep)) return route.abort();
  if(fs.existsSync(file)&&fs.statSync(file).isFile()) return route.fulfill({path:file,
    contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':undefined});
  return route.fulfill({status:404,body:''});
 });
 return {context,page,errors};
}
let activeBrowser;
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL?{channel:process.env.PLAYWRIGHT_CHROMIUM_CHANNEL}:{})});
 activeBrowser=browser;
 const receipts=[];
 for(const width of [1440,390,320]) for(const theme of ['dark','light']) for(const lang of ['en','zh']){
  const {context,page,errors}=await fixture(browser,{width});
  await page.goto('http://intl.test/intl.html',{waitUntil:'load'});
  await page.evaluate(({theme,lang})=>{document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang=lang;},{theme,lang});
  await page.evaluate(()=>document.fonts.ready);
  const geometry=await page.evaluate(()=>({
   viewport:innerWidth,scroll:document.documentElement.scrollWidth,
   countryCount:document.querySelectorAll('.imc-country').length,
   openCountry:document.querySelector('.imc-country[open]')?.id,
   toolsOpen:document.querySelector('#intl-analysis-tools').open,
   countryTop:Math.round(document.querySelector('.imc-country[open]').getBoundingClientRect().top),
   countryPadding:getComputedStyle(document.querySelector('.imc-country')).padding,
   firstCountryTitle:document.querySelector('.imc-country[open] .imc-country-thesis').innerText,
   background:getComputedStyle(document.body).backgroundColor,
   assistantPosition:document.querySelector('#mmb-boot,#mmb-launch') ? getComputedStyle(document.querySelector('#mmb-boot,#mmb-launch')).position : null,
   assistantAfterResearch:!document.querySelector('#mmb-boot,#mmb-launch') || document.querySelector('#mmb-boot,#mmb-launch').getBoundingClientRect().top >= document.querySelector('.imc').getBoundingClientRect().bottom
  }));
  assert.equal(geometry.scroll,width,'horizontal page overflow');
  assert.equal(await page.locator('body.imc-page').count(),1);
  assert.equal(geometry.countryCount,7);
  assert.ok(!['fixed','absolute'].includes(geometry.assistantPosition),'assistant obscures research');
  assert.equal(geometry.assistantAfterResearch,true);
  assert.equal(geometry.openCountry,'imc-country-KR');
  assert.equal(geometry.toolsOpen,false);
  assert.equal(errors.length,0,'page errors: '+errors.join(';'));
  const file='integrated_'+width+'_'+theme+'_'+lang+'.png';
  await page.screenshot({path:path.join(output,file),fullPage:width===1440});
  receipts.push({width,theme,lang,...geometry,errors,file});
  await context.close();
 }
 // All seven economic paths and the fiscal/reporting-period details are readable.
 {
  const {context,page,errors}=await fixture(browser);
  await page.goto('http://intl.test/intl.html');
  const world=await page.locator('#imc-world').innerText();
  assert.ok(world.includes('3.1%') && world.includes('3.4%'),'world brief must use the IMF world aggregate');
  assert.ok(world.includes('2026-10-01'),'world information cutoff is visible');
  assert.ok((await page.locator('#imc-world a[href]').getAttribute('href')).includes('imf.org'));
  for(const [cc,value] of [['JP','0.7'],['KR','3.3'],['TW','10.7'],['IN','7.0'],['AU','1.9'],['GB','1.3'],['EZ','1.1']]){
   await page.locator('.imc-country-rail [data-imc-country="'+cc+'"]').click();
   const panel=page.locator('#imc-country-'+cc);
   assert.ok((await panel.locator('.imc-outlook-panel').innerText()).includes(value));
   assert.ok((await panel.locator('.imc-inflation-path').innerText()).includes('Annual average'));
   assert.ok((await panel.locator('.imc-outlook-panel').innerText()).includes('2026-10-13'));
  }
  await page.locator('.imc-country-rail [data-imc-country="IN"]').click();
  assert.ok((await page.locator('#imc-country-IN .imc-forecast-path').innerText()).includes('FY2026/27'));
  await page.locator('.imc-country-rail [data-imc-country="JP"]').click();
  assert.equal(await page.locator('#imc-country-JP .imc-balance-row').count(),3);
  assert.ok((await page.locator('#imc-country-JP .imc-balances').innerText()).includes('199.4%'));
  await page.locator('.imc-country-rail [data-imc-country="TW"]').click();
  await page.locator('#imc-country-TW .imc-evidence > summary').click();
  assert.ok((await page.locator('#imc-country-TW .imc-evidence').innerText()).includes('DGBAS'));
  assert.ok((await page.locator('#imc-country-TW .imc-evidence').innerText()).includes('CBC'));
  for(const [cc,instrument,value,source] of [['GB','Bank Rate','3.75','bankofengland.co.uk'],['TW','Discount rate','2.00','cbc.gov.tw']]){
   await page.locator('.imc-country-rail [data-imc-country="'+cc+'"]').click();
   const policy=page.locator('#imc-country-'+cc+' .imc-policy-decision');
   const content=await policy.innerText();
   assert.ok(content.includes(instrument) && content.includes(value) && content.includes('2026-09-17'));
   assert.ok((await policy.locator('a').getAttribute('href')).includes(source));
   assert.equal(await page.locator('#imc-country-'+cc+' .imc-vitals > div').count(),2,'latest policy replaces the duplicate historical policy vital');
  }
  assert.equal(errors.length,0);
  receipts.push({journey:'world-country-paths-fiscal-basis-independent-forecasts-national-decisions',passed:true});
  await context.close();
 }
 // Inspect the actual narrow-screen analysis, below the opening viewport.
 for(const [width,theme,cc] of [[320,'dark','KR'],[390,'light','TW'],[390,'dark','GB']]){
  const {context,page,errors}=await fixture(browser,{width});
  await page.goto('http://intl.test/intl.html');
  await page.evaluate(theme=>document.documentElement.dataset.theme=theme,theme);
  await page.locator('.imc-country-rail [data-imc-country="'+cc+'"]').click();
  const panel=page.locator('#imc-country-'+cc);
  const chart=panel.locator('.imc-growth-chart');
  const labels=await chart.locator('.imc-chart-value,.imc-chart-year').evaluateAll(nodes=>nodes.map(el=>{
   const box=el.getBoundingClientRect(), svg=el.ownerSVGElement.getBoundingClientRect();
   return {text:el.textContent,pixels:parseFloat(getComputedStyle(el).fontSize)*svg.width/440,left:box.left,right:box.right};
  }));
  assert.ok(labels.every(x=>x.pixels>=10 && x.left>=0 && x.right<=width),'chart labels must be readable and within the viewport');
  const outlookFile='analysis_'+width+'_'+theme+'_'+cc+'.png';
  await panel.locator('.imc-outlook-panel').screenshot({path:path.join(output,outlookFile)});
  let policyFile=null;
  if(cc!=='KR'){
   policyFile='policy_'+width+'_'+theme+'_'+cc+'.png';
   await panel.locator('.imc-policy-decision').screenshot({path:path.join(output,policyFile)});
  }
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),width);
  assert.equal(errors.length,0);
  receipts.push({journey:'mobile-analysis-legibility',width,theme,cc,labels,outlookFile,policyFile,passed:true});
  await context.close();
 }
 // The real country selection, keyboard focus and browser history journey.
 {
  const {context,page,errors}=await fixture(browser);
  await page.goto('http://intl.test/intl.html');
  await page.locator('.imc-country-rail [data-imc-country="JP"]').click();
  assert.equal(await page.locator('#imc-country-JP').getAttribute('open'),'');
  assert.equal(await page.evaluate(()=>document.activeElement.parentElement.id),'imc-country-JP');
  await page.locator('.imc-country-rail [data-imc-country="TW"]').click();
  await page.goBack();
  assert.equal(await page.locator('#imc-country-JP').getAttribute('open'),'');
  assert.equal(await page.locator('#imc-country-TW').getAttribute('open'),null);
  await page.locator('#imc-country-JP .imc-evidence > summary').focus();
  await page.keyboard.press('Enter');
  assert.equal(await page.locator('#imc-country-JP .imc-evidence').getAttribute('open'),'');
  await page.locator('.imc-tools-link').click();
  assert.equal(await page.locator('#intl-analysis-tools').getAttribute('open'),'');
  assert.equal(errors.length,0);
  receipts.push({journey:'country-select-history-keyboard-sources-tools',passed:true});
  await context.close();
 }
 // Existing deep links remain reachable inside the subordinate tools.
 for(const suffix of ['#intl-cross-country','?view=compare&market=JP']){
  const {context,page}=await fixture(browser);
  await page.goto('http://intl.test/intl.html'+suffix);
  assert.equal(await page.locator('#intl-analysis-tools').getAttribute('open'),'');
  receipts.push({journey:'legacy-deep-link',suffix,passed:true});
  await context.close();
 }
 // Missing legacy assets cannot erase the core analysis.
 {
  const {context,page,errors}=await fixture(browser,{width:390,denied:true});
  await page.goto('http://intl.test/intl.html');
  await page.locator('.imc-country-rail [data-imc-country="JP"]').click();
  assert.equal(await page.locator('#imc-country-JP').getAttribute('open'),'');
  assert.ok(await page.locator('#imc-country-JP').innerText().then(t=>t.includes('Bank of Japan')));
  receipts.push({journey:'legacy-assets-401-core-remains-readable',passed:true,errors});
  await context.close();
 }
 // The incumbent assistant can still load, open and return focus from footer flow.
 {
  const {context,page,errors}=await fixture(browser,{width:390});
  await page.goto('http://intl.test/intl.html');
  await page.locator('#mmb-boot').click();
  await page.waitForFunction(()=>window.MMBrain && window.MMBrain.mounted);
  assert.equal(await page.locator('#mmb-boot').count(),0);
  assert.ok(await page.locator('#mmb-panel').evaluate(el=>el.classList.contains('open')));
  assert.equal(await page.locator('#mmb-launch').evaluate(el=>getComputedStyle(el).position),'relative');
  await page.evaluate(()=>window.MMBrain.close());
  assert.equal(await page.locator('#mmb-panel').evaluate(el=>el.classList.contains('open')),false);
  assert.ok(await page.locator('#mmb-launch').isVisible());
  await page.locator('#mmb-launch').focus();
  await page.keyboard.press('Enter');
  assert.equal(errors.length,0);
  assert.ok(await page.locator('#mmb-panel').evaluate(el=>el.classList.contains('open')));
  receipts.push({journey:'incumbent-assistant-footer-load-open-reopen',passed:true});
  await context.close();
 }
 // Native disclosure operation remains complete with all scripts disabled.
 {
  const {context,page}=await fixture(browser,{width:390,js:false});
  await page.goto('http://intl.test/intl.html');
  await page.locator('#imc-country-JP > summary').click();
  assert.equal(await page.locator('#imc-country-JP').getAttribute('open'),'');
  await page.locator('#imc-country-JP .imc-evidence > summary').click();
  assert.equal(await page.locator('#imc-country-JP .imc-evidence table').count(),2);
  assert.ok(await page.locator('#imc-country-JP .imc-evidence table').nth(0).isVisible());
  assert.ok(await page.locator('#imc-country-JP .imc-evidence table').nth(1).isVisible());
  receipts.push({journey:'no-javascript-country-and-evidence',passed:true});
  await context.close();
 }
 await browser.close();
 fs.writeFileSync(path.join(output,'integrated_receipts.json'),JSON.stringify(receipts,null,2)+'\n');
 console.log(JSON.stringify(receipts));
})().catch(async e=>{console.error(e);if(activeBrowser)await activeBrowser.close();process.exitCode=1;});