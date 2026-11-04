/* Local fixture proof, deliberately separate from source/unit acceptance.
   Run only on an admitted browser host. No production navigation or writes. */
const fs=require('node:fs'), path=require('node:path'), os=require('node:os'), assert=require('node:assert/strict');
let playwright;
try { playwright=require('playwright'); }
catch(e) { if(!process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES) throw e; playwright=require(path.join(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES,'playwright')); }
const base=process.env.D05_BASE_URL||'http://127.0.0.1:8765';
assert(['127.0.0.1','localhost','[::1]'].includes(new URL(base).hostname),'Use a local fixture server only.');
const out=process.env.D05_EVIDENCE_DIR||fs.mkdtempSync(path.join(os.tmpdir(),'d05-browser-proof-'));
fs.mkdirSync(out,{recursive:true});
const cases=[[1440,1000,'dark','en'],[1440,1000,'light','zh'],[1024,900,'dark','en'],[768,1024,'light','en'],[390,844,'dark','en'],[390,844,'light','zh'],[320,740,'dark','zh']];
const results=[];
(async()=>{
 const browser=await playwright.chromium.launch({headless:true,...(process.env.D05_CHROMIUM_EXECUTABLE?{executablePath:process.env.D05_CHROMIUM_EXECUTABLE}:{})});
 try {
  for(const [width,height,theme,lang] of cases) {
   const context=await browser.newContext({viewport:{width,height},reducedMotion:'reduce'}), page=await context.newPage();
   await context.addInitScript(({theme,lang})=>{localStorage.setItem('theme',theme);localStorage.setItem('lang',lang);},{theme,lang});
   const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/*',r=>new URL(r.request().url()).origin===new URL(base).origin&&r.request().method()==='GET'?r.continue():r.abort());
   await page.goto(base+'/sector_central.html?g=XLE#map',{waitUntil:'networkidle'});
   assert.equal(await page.locator('body').getAttribute('data-d05-fixture'),'archived-source');
   await page.locator('#mr-cycle-link').waitFor();
   assert.equal(await page.locator('#sc-chart svg').count(),0,'map must not create the hidden native chart');
   await page.locator('.mr-segbtn[data-h="obs"]').click();
   await page.locator('#mr-cycle-link').click();
   await page.waitForFunction(()=>['applied','source_mismatch','source_unavailable','unsupported'].includes(document.querySelector('#sc-cycle-status').dataset.state));
   const sourceState=await page.locator('#sc-cycle-status').getAttribute('data-state');
   if(sourceState==='source_mismatch') {
    assert.equal(await page.locator('#sc-native-study').isVisible(),false);
    await page.screenshot({path:path.join(out,`${width}-${theme}-${lang}-mismatch.jpg`),type:'jpeg',quality:80});
    await page.locator('#sc-cycle-latest').click();
   }
   await page.waitForFunction(()=>document.querySelector('#sc-cycle-status').dataset.state==='applied');
   assert.equal(new URL(page.url()).hash,'#cycles');
   assert.equal(new URL(page.url()).searchParams.get('g'),'XLE');
   await page.locator('#sc-chart svg').waitFor();
   assert.equal(await page.locator('#sc-chart svg').count(),1);
   assert.ok((await page.locator('#sc-chart').boundingBox()).width>200);
   assert.equal(await page.locator('.cyc-chip[data-id="xle"]').getAttribute('class').then(c=>c.includes('on')),true);
   await page.locator('#sc-adv-toggle').click();
   await page.locator('#sc-modes [data-mode="price"]').click();
   await page.locator('#sc-scale [data-scale="linear"]').click();
   await page.locator('#sc-zoom [data-i="3"]').click();
   await page.locator('#sc-zreset').click();
   assert.equal(await page.locator('#sc-scale [data-scale="linear"]').getAttribute('aria-pressed'),'true');
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
   assert.equal(overflow,false,'page must not overflow horizontally');
   await page.locator('#sc-cycle-heading').scrollIntoViewIfNeeded();
   await page.screenshot({path:path.join(out,`${width}-${theme}-${lang}.jpg`),type:'jpeg',quality:85});
   await page.locator('#sc-tabs [data-fam="baskets"]').click();
   assert.equal(new URL(page.url()).searchParams.get('cycleFamily'),'baskets');
   assert.equal(new URL(page.url()).searchParams.has('cycle'),false);
   await page.locator('#sc-cycle-return').click();
   await page.waitForURL('**/sector_central.html?g=XLE#map');
   assert.equal(await page.locator('.mr-segbtn[data-h="obs"]').getAttribute('aria-pressed'),'true');
   await page.waitForFunction(()=>document.activeElement.id==='mr-cycle-link');
   await page.goForward();
   await page.waitForURL('**#cycles');
   assert.equal(await page.locator('#sc-tabs [data-fam="baskets"]').getAttribute('aria-pressed'),'true');
   assert.equal(await page.locator('#sc-chart svg').count(),1);
   assert.deepEqual(errors,[],'page exceptions must be resolved or explicitly classified');
   results.push({width,height,theme,lang,sourceState,status:'passed'});
   await context.close();
  }
 } finally { await browser.close(); }
 fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({status:'passed',cases:results},null,2));
 console.log(JSON.stringify({evidence:out,cases:results.length,status:'passed'}));
})().catch(e=>{fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({status:'failed',completed:results,error:String(e)},null,2));console.error(e);process.exitCode=1;});
