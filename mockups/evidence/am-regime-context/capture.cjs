const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),http=require('http'),crypto=require('crypto');
const out=__dirname, site=path.join(out,'site');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const server=http.createServer((req,res)=>{
  const url=new URL(req.url,'http://localhost');
  const p=path.resolve(site,'.'+url.pathname);
  if(!p.startsWith(site+path.sep)||!fs.existsSync(p)){res.writeHead(404);res.end();return;}
  const types={'.html':'text/html','.js':'application/javascript','.css':'text/css'};
  res.setHeader('Content-Type',types[path.extname(p)]||'application/octet-stream');
  res.end(fs.readFileSync(p));
});
(async()=>{
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const port=server.address().port, browser=await chromium.launch({headless:true});
const input=JSON.parse(fs.readFileSync(path.join(out,'input.json'))), states=[];
try {
for(const viewport of ['desktop','mobile']) for(const theme of ['dark','light']) for(const locale of ['en','zh']){
  const width=viewport==='desktop'?1440:390, height=viewport==='desktop'?900:844;
  const context=await browser.newContext({viewport:{width,height},reducedMotion:'reduce'});
  await context.addInitScript(({theme,locale})=>{localStorage.setItem('theme',theme);localStorage.removeItem('themeAuto');localStorage.setItem('lang',locale);},{theme,locale});
  const page=await context.newPage(); const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',route=>new URL(route.request().url()).hostname==='127.0.0.1'?route.continue():route.abort());
  const response=await page.goto(`http://127.0.0.1:${port}/am_edition.html`,{waitUntil:'load'});
  if(!response.ok())throw Error('page response '+response.status());
  const observed=await page.evaluate(({theme,locale})=>{
    window.setTheme?.(theme);window.setLang?.(locale);
    return {theme:document.documentElement.getAttribute('data-theme'),locale:document.documentElement.getAttribute('data-lang')};
  },{theme,locale});
  if(observed.theme!==theme||observed.locale!==locale) throw Error('state mismatch');
  const observations=[];
  for(const block of input.blocks){
    const title=block.key==='market_state'?(locale==='en'?'Market regime':'市场周期'):(locale==='en'?'Macroeconomic regime':'宏观周期');
    const panel=page.locator('.panel').filter({has:page.getByRole('heading',{name:title,exact:true})});
    if(await panel.count()!==1)throw Error('ambiguous regime panel');
    const text=await panel.innerText();
    const row=block.rows[0],label=block.key==='market_state'?row['label_'+locale]:row['quad_name_'+locale];
    for(const expected of [label,block['state_reason_'+locale],'2026-10-08',locale==='en'?'Stale — last known':'已滞后 — 最新已知'])
      if(!text.includes(expected))throw Error('missing '+block.key+' '+expected);
    if(text.includes('2026-10-08T00:00'))throw Error('day precision fabricated time');
    const geometry=await panel.evaluate(e=>({panel:e.getBoundingClientRect().width,scroll:e.scrollWidth,document:document.documentElement.scrollWidth,viewport:innerWidth}));
    if(geometry.scroll>geometry.panel+2||geometry.document>geometry.viewport+2)throw Error('horizontal overflow '+JSON.stringify(geometry));
    await panel.evaluate(e=>e.scrollIntoView({block:'start',behavior:'instant'}));
    const name=`${block.key}-${theme}-${locale}-${viewport}.png`,png=await panel.screenshot();
    fs.writeFileSync(path.join(out,name),png);
    observations.push({key:block.key,file:name,sha256:sha(png),bytes:png.length,geometry,visible_text:text});
  }
  if(errors.length)throw Error('page errors '+errors.join(';'));
  states.push({theme,locale,viewport,viewport_width:width,captured:true,applied_theme:observed.theme,applied_locale:observed.locale,observations,page_errors:errors});
  console.log(`${theme}/${locale}/${viewport}: two dated last-known regime panels, no overflow`);
  await context.close();
}
fs.writeFileSync(path.join(out,'capture-results.json'),JSON.stringify({input,tool_sha256:sha(fs.readFileSync(__filename)),captured_at:new Date().toISOString(),local_saved_payload_render:true,states},null,2)+'\n');
} finally {await browser.close();server.close();}
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
