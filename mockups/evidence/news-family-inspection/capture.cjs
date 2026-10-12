const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),http=require('http'),crypto=require('crypto');
const out=__dirname, site=path.join(out,'site');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const server=http.createServer((req,res)=>{
 const p=path.resolve(site,'.'+new URL(req.url,'http://localhost').pathname);
 if(!p.startsWith(site+path.sep)||!fs.existsSync(p)){res.writeHead(404);res.end();return;}
 res.setHeader('Content-Type',({'.html':'text/html','.js':'application/javascript','.css':'text/css'})[path.extname(p)]||'application/octet-stream');res.end(fs.readFileSync(p));
});
(async()=>{
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const port=server.address().port,browser=await chromium.launch({headless:true});
const states=[];const checks=[];
async function capture(panel,name,entry){
 const png=await panel.screenshot();fs.writeFileSync(path.join(out,name),png);
 states.push({...entry,captured:true,file:name,sha256:sha(png),bytes:png.length,width:png.readUInt32BE(16),height:png.readUInt32BE(20)});
}
try{
for(const viewport of ['desktop','mobile'])for(const theme of ['dark','light'])for(const locale of ['en','zh']){
 const width=viewport==='desktop'?1440:390,height=viewport==='desktop'?900:844;
 const context=await browser.newContext({viewport:{width,height},reducedMotion:'reduce',colorScheme:theme});
 await context.addInitScript(({theme,locale})=>{localStorage.setItem('theme',theme);localStorage.removeItem('themeAuto');localStorage.setItem('lang',locale);},{theme,locale});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
 await page.goto(`http://127.0.0.1:${port}/news.html`,{waitUntil:'load'});
 const observed=await page.evaluate(({theme,locale})=>{window.setTheme?.(theme);window.setLang?.(locale);return{theme:document.documentElement.getAttribute('data-theme'),locale:document.documentElement.getAttribute('data-lang')};},{theme,locale});
 if(observed.theme!==theme||observed.locale!==locale)throw Error('state mismatch');
 const panel=page.locator('#nxConsequence'),family=panel.locator('.nx-family').filter({hasText:'Earnings reports'});
 if(await panel.locator('.nx-family').count()!==6||await panel.locator('.nx-family[open]').count()!==0)throw Error('default disclosure state');
 const entry={viewport,viewport_width:width,viewport_height:height,theme,locale,access:'anonymous',subject:'consequences',applied_theme:observed.theme,applied_locale:observed.locale};
 await capture(panel,`closed-${theme}-${locale}-${viewport}.png`,entry);
 await family.locator('summary').focus();await page.keyboard.press('Enter');
 if(await family.getAttribute('open')===null||await family.locator('.nx-rel').count()!==4)throw Error('keyboard open or card count');
 const text=await family.innerText();
 if(!text.includes(locale==='en'?'Showing 4 of 6 records':'显示6条中的4条'))throw Error('cap disclosure');
 const overflow=await panel.evaluate(e=>({doc:document.documentElement.scrollWidth,viewport:innerWidth,wide:[...e.querySelectorAll('*')].filter(x=>x.getBoundingClientRect().width>innerWidth).length}));
 if(overflow.doc>width+2||overflow.wide)throw Error('overflow '+JSON.stringify(overflow));
 await capture(panel,`open-${theme}-${locale}-${viewport}.png`,{...entry,force_state:'earnings_disclosure_open'});
 await family.locator('summary').focus();await page.keyboard.press('Space');
 if(await family.getAttribute('open')!==null)throw Error('keyboard close failed');
 for(const [label,en,zh]of[['Economic data','Recorded events do not name a market exposure.','已记录事件未点名市场敞口。'],['Research notes','No recorded events of this type in this window.','该时段没有此类已记录事件。']]){
  const f=panel.locator('.nx-family').filter({hasText:label});await f.locator('summary').click();
  if(!(await f.innerText()).includes(locale==='en'?en:zh))throw Error('empty state missing');
  await f.locator('summary').click();
 }
 checks.push({theme,locale,viewport,keyboard_open_close:true,typed_empties:true,overflow,page_errors:errors});
 console.log(`${theme}/${locale}/${viewport}: closed/open captured, keyboard + empties + layout pass`);
 await context.close();
}
const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'}),page=await context.newPage();
await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
await page.goto(`http://127.0.0.1:${port}/actual.html`,{waitUntil:'load'});
await page.evaluate(()=>{setTheme('light');setLang('en');});
const panel=page.locator('#nxConsequence'),calls=panel.locator('.nx-family').filter({hasText:'Earnings calls'});
await calls.locator('summary').click();if(await calls.locator('.nx-rel').count()!==4)throw Error('current corpus call count');
await capture(panel,'actual-light-en-mobile.png',{viewport:'mobile',viewport_width:390,theme:'light',locale:'en',access:'anonymous',subject:'consequences',applied_theme:'light',applied_locale:'en',force_state:'saved_corpus_calls_open'});
await page.goto(`http://127.0.0.1:${port}/unavailable.html`,{waitUntil:'load'});
if(await page.locator('.nx-family').count()!==0)throw Error('unavailable source fabricated family views');
checks.push({saved_corpus_calls:4,unavailable_source_views:0});await context.close();
fs.writeFileSync(path.join(out,'capture-results.json'),JSON.stringify({input:JSON.parse(fs.readFileSync(path.join(out,'input.json'))),tool_sha256:sha(fs.readFileSync(__filename)),states,checks,captured_at:new Date().toISOString()},null,2)+'\n');
}finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
