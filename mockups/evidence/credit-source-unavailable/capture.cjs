const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),http=require('http'),crypto=require('crypto');
const out=__dirname,site=path.join(out,'site'),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const server=http.createServer((req,res)=>{const u=new URL(req.url,'http://localhost'),p=path.resolve(site,'.'+u.pathname);if(!p.startsWith(site+path.sep)||!fs.existsSync(p)){res.writeHead(404);return res.end();}res.setHeader('Content-Type',({'.html':'text/html','.css':'text/css','.js':'application/javascript'})[path.extname(p)]||'application/octet-stream');res.end(fs.readFileSync(p));});
(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));const port=server.address().port,browser=await chromium.launch({headless:true}),states=[];
try {for(const viewport of ['desktop','mobile'])for(const theme of ['dark','light'])for(const locale of ['en','zh']){
const width=viewport==='desktop'?1440:390,height=viewport==='desktop'?900:844;
const context=await browser.newContext({viewport:{width,height},reducedMotion:'reduce'});
await context.addInitScript(({theme,locale})=>{localStorage.setItem('theme',theme);localStorage.setItem('lang',locale);localStorage.removeItem('themeAuto');document.addEventListener('DOMContentLoaded',()=>{document.documentElement.setAttribute('data-theme',theme);document.documentElement.setAttribute('data-lang',locale);});},{theme,locale});
const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
await page.goto(`http://127.0.0.1:${port}/unavailable.html`,{waitUntil:'load'});await page.evaluate(({theme,locale})=>{window.setTheme?.(theme);window.setLang?.(locale);},{theme,locale});
const card=page.locator('[data-card="credit-source-unavailable"]');if(await card.count()!==1)throw Error('missing unavailable card');
const text=await page.locator('main').innerText();for(const forbidden of ['Credit stress: low','zero bonds maturing','No new issuance','暂无新发行'])if(text.toLowerCase().includes(forbidden.toLowerCase()))throw Error('invented absent-source claim');
if(!text.toLowerCase().includes(locale==='en'?'credit reading unavailable':'信用读数不可用'))throw Error('missing localized unavailable label '+JSON.stringify({theme,locale,text}));
const state=await page.evaluate(()=>({theme:document.documentElement.getAttribute('data-theme'),locale:document.documentElement.getAttribute('data-lang'),scroll:document.documentElement.scrollWidth,viewport:innerWidth}));if(state.theme!==theme||state.locale!==locale||state.scroll>width+2)throw Error('state/overflow '+JSON.stringify(state));
const main=page.locator('main'),box=await main.boundingBox(),png=await main.screenshot(),file=`unavailable-${theme}-${locale}-${viewport}.png`;fs.writeFileSync(path.join(out,file),png);states.push({theme,locale,viewport,viewport_width:width,viewport_height:height,applied_theme:state.theme,applied_locale:state.locale,captured:true,file,sha256:sha(png),bytes:png.length,width:Math.round(box.width),height:Math.round(box.height),visible_text:text,page_errors:errors});
await page.goto(`http://127.0.0.1:${port}/valid.html`,{waitUntil:'load'});if(await page.locator('[data-card="credit-source-unavailable"]').count())throw Error('valid snapshot suppressed');if(await page.locator('.cc-mkt-chip').count()<4)throw Error('valid gauges missing');if(errors.length)throw Error(errors.join(';'));
console.log(`${theme}/${locale}/${viewport}: unavailable disclosure + valid gauge control passed`);await context.close();}
fs.writeFileSync(path.join(out,'capture-results.json'),JSON.stringify({captured_at:new Date().toISOString(),tool_sha256:sha(fs.readFileSync(__filename)),isolated_actual_credit_fragment:true,states},null,2)+'\n');
}finally{await browser.close();server.close();}})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
