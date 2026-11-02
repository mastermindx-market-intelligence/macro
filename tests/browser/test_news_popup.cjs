/* Real-browser checks of the source fixture. No production credentials/network. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'../..'),fixture=fs.readFileSync(path.join(root,'.qa/news-fixture.html'),'utf8');
const tests=[];function test(name,run){tests.push({name,run});}
async function setup(browser,options={}){
 const page=await browser.newPage({viewport:{width:1440,height:1000},...options});
 await page.route('https://**/*',route=>route.abort());
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.errors=errors;
 await page.setContent(fixture);await page.locator('#trigger').click();
 await page.locator('#dlg-news.mx5-dlg-in').waitFor();return page;
}
test('filter and search intersect; no-match and reset states work',async b=>{
 const p=await setup(b);assert.equal(await p.locator('[data-news-item]:visible').count(),7);
 await p.locator('[data-news-filter="priority"]').click();assert.equal(await p.locator('[data-news-item]:visible').count(),2);
 await p.locator('[data-news-search]').fill('GOOG');assert.equal(await p.locator('[data-news-item]:visible').count(),0);assert(await p.locator('[data-news-no-matches]').isVisible());
 await p.locator('[data-news-filter="all"]').click();assert.equal(await p.locator('[data-news-item]:visible').count(),1);
 await p.locator('[data-news-reset]').click();assert.equal(await p.locator('[data-news-item]:visible').count(),7);assert(await p.locator('[data-news-search]').evaluate(e=>e===document.activeElement));
 assert.deepEqual(p.errors,[]);await p.close();
});
test('evidence and reading position survive release refresh and language switch',async b=>{
 const p=await setup(b);await p.locator('.ni-evidence summary').first().click();
 const before=await p.locator('[data-al-row]').first().innerText();
 const readingRow=p.locator('[data-al-row]').nth(2);await readingRow.scrollIntoViewIfNeeded();
 const readingY=(await readingRow.boundingBox()).y;
 await p.evaluate(()=>{const now=new Date();window.__mmReleasePublicationTest.render({built:now.toISOString(),publications:[{event_id:'cpi-test',type:'CPI',date:now.toISOString().slice(0,10),detected_at:now.toISOString(),status:'published_unparsed'}],events:[]},now);});
 assert.equal(await p.locator('[data-al-row]').first().innerText(),before);assert(await p.locator('.ni-evidence').first().evaluate(e=>e.open));
 assert(Math.abs((await readingRow.boundingBox()).y-readingY)<=1,'release refresh moved the reading anchor');
 assert.equal(await p.locator('[data-news-release]').getAttribute('data-state'),'verifying');
 await p.evaluate(()=>document.documentElement.setAttribute('data-lang','zh'));
 assert(await p.locator('.ni-evidence').first().evaluate(e=>e.open));assert((await p.locator('[data-news-count]').innerText()).includes('条动态'));
 assert((await p.locator('[data-news-search]').getAttribute('placeholder')).includes('搜索'));await p.close();
});
test('rapid close/reopen cancels stale close teardown',async b=>{
 const p=await setup(b);await p.evaluate(()=>{mx5CloseDlg();mx5OpenDlg('dlg-news')});await p.waitForTimeout(430);
 assert(await p.locator('#dlg-news').isVisible());assert(await p.locator('#dlg-news').evaluate(e=>e.contains(document.activeElement)));
 await p.keyboard.press('Escape');await p.waitForTimeout(400);assert(await p.locator('#trigger').evaluate(e=>e===document.activeElement));await p.close();
});
test('calendar switch restores the original opener and scroll lock',async b=>{
 const p=await setup(b);await p.locator('[data-news-panel="dlg-events"]').first().click();await p.locator('#dlg-events').waitFor();
 assert(await p.evaluate(()=>document.documentElement.classList.contains('mx5-dlg-lock')));
 await p.keyboard.press('Escape');await p.waitForTimeout(400);
 assert(await p.locator('#trigger').evaluate(e=>e===document.activeElement));assert(!(await p.evaluate(()=>document.documentElement.classList.contains('mx5-dlg-lock'))));await p.close();
});
test('Tab wraps and Escape restores focus with reduced motion',async b=>{
 const p=await setup(b,{reducedMotion:'reduce'});await p.locator('#dlg-news .mx5-dlg-close').focus();await p.keyboard.press('Shift+Tab');
 assert(await p.locator('.ni-feed-link').evaluate(e=>e===document.activeElement));await p.keyboard.press('Tab');assert(await p.locator('#dlg-news .mx5-dlg-close').evaluate(e=>e===document.activeElement));
 await p.keyboard.press('Escape');assert(await p.locator('#trigger').evaluate(e=>e===document.activeElement));await p.close();
});
test('light/dark EN/ZH desktop/mobile have no horizontal overflow',async b=>{
 const p=await setup(b,{reducedMotion:'reduce'});
 for(const width of [1440,390])for(const theme of ['light','dark'])for(const lang of ['en','zh']){
   await p.setViewportSize({width,height:width===390?844:1000});await p.evaluate(({theme,lang})=>{document.documentElement.setAttribute('data-theme',theme);document.documentElement.setAttribute('data-lang',lang)}, {theme,lang});
   await p.evaluate(()=>document.querySelector('#dlg-news .mx5-dlg-body').scrollTop=0);
   const dims=await p.locator('#dlg-news .mx5-dlg-body').evaluate(e=>({scroll:e.scrollWidth,client:e.clientWidth}));assert(dims.scroll<=dims.client+1,JSON.stringify({width,theme,lang,dims}));
   const pageDims=await p.evaluate(()=>({viewport:innerWidth,root:document.documentElement.scrollWidth,body:document.body.scrollWidth}));assert(Math.max(pageDims.root,pageDims.body)<=pageDims.viewport+1,JSON.stringify({width,theme,lang,pageDims}));
   assert(await p.locator('#dlg-news .mx5-dlg-close').isVisible());
   await p.screenshot({path:path.join(root,'.qa',`news-${theme}-${lang}-${width}.png`)});
 }
 assert.deepEqual(p.errors,[]);await p.close();
});
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});let failed=0;for(const t of tests){try{await t.run(browser);console.log('PASS '+t.name)}catch(e){failed++;console.log('FAIL '+t.name+' — '+e.message.split('\n')[0])}}await browser.close();fs.writeFileSync(path.join(root,'.qa','popup-test-result.json'),JSON.stringify({tests:tests.length,failed},null,2));console.log(JSON.stringify({tests:tests.length,failed}));process.exitCode=failed?1:0;})();
