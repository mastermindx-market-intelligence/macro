const fs=require('fs'),path=require('path'),http=require('http');
const puppeteer=require('/Users/chriswong/.local/share/desktop-commander-service/vendor/node_modules/puppeteer');
const root=__dirname, results=[];
let browser,server;
(async()=>{
 server=http.createServer((req,res)=>{
  const route=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const file=path.resolve(root,'.'+route);
  if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);return res.end('fixture asset not present');}
  const types={'.html':'text/html; charset=utf-8','.css':'text/css','.woff2':'font/woff2'};
  res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream'});fs.createReadStream(file).pipe(res);
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const base='http://127.0.0.1:'+server.address().port;
 browser=await puppeteer.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',userDataDir:path.join(root,'owned-rest-profile')});
 for(const width of [390,1440])for(const theme of ['dark','light'])for(const lang of ['en','zh'])for(const state of ['normal','correction','missing-prior','rate']){
  const page=await browser.newPage();const errors=[],blocked=[];
  await page.setViewport({width,height:width===390?844:900,deviceScaleFactor:1});
  await page.setUserAgent('mastermind-page-census/1.0 (internal product observability)');
  await page.emulateMediaFeatures([{name:'prefers-reduced-motion',value:'reduce'}]);
  await page.setRequestInterception(true);
  page.on('request',req=>req.url().startsWith(base)||req.url().startsWith('data:')?req.continue():(blocked.push(req.url()),req.abort()));
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/'+state+'.html',{waitUntil:'networkidle0'});
  await page.evaluate(({theme,lang})=>{document.documentElement.dataset.theme=theme;document.documentElement.dataset.lang=lang;document.documentElement.lang=lang;},{theme,lang});
  await page.evaluate(()=>document.fonts.ready);
  const summary=await page.$('[data-news-guidance] summary');if(!summary)throw new Error('summary missing');
  await summary.evaluate(e=>e.scrollIntoView({block:'center'}));
  const restShot=`rest-${state}-${theme}-${lang}-${width}.png`;
  await (await page.$('#news')).screenshot({path:path.join(root,restShot)});
  const applied=await page.evaluate(()=>({theme:document.documentElement.dataset.theme,locale:document.documentElement.dataset.lang}));

  await summary.focus();await page.keyboard.press('Enter');
  const result=await page.evaluate(({width,theme,lang,state})=>{
   const d=document.querySelector('[data-news-guidance]'),n=document.querySelector('#news'),rect=n.getBoundingClientRect();
   const text=d.innerText;const bg=getComputedStyle(n).backgroundColor;
   const hidden=Array.from(d.querySelectorAll(lang==='zh'?'.l-en':'.l-zh')).every(e=>getComputedStyle(e).display==='none');
   return {width,theme,lang,state,opened:d.open,within_panel:n.scrollWidth<=n.clientWidth+1,within_viewport:rect.width<=width+1,language_hidden:hidden,summary:d.querySelector('summary').innerText,text,bg,font:getComputedStyle(d).fontFamily};
  },{width,theme,lang,state});
  if(!result.opened||!result.within_panel||!result.within_viewport||!result.language_hidden||errors.length)throw new Error(JSON.stringify({...result,errors}));
  const marker=state==='missing-prior'?(lang==='zh'?'暂无可比':'No comparable prior'):state==='correction'?(lang==='zh'?'来源更正':'Corrected source'):state==='rate'?(lang==='zh'?'个百分点':'percentage point'):'76,000';
  if(!result.text.includes(marker))throw new Error('missing translated content '+marker);
  const shot=`interaction-${state}-${theme}-${lang}-${width}.png`;
  await (await page.$('#news')).screenshot({path:path.join(root,shot)});
  await summary.focus();await page.keyboard.press('Space');
  result.keyboard_closed=await page.$eval('[data-news-guidance]',e=>!e.open);if(!result.keyboard_closed)throw new Error('keyboard close failed');
  result.screenshot=shot;result.rest_screenshot=restShot;result.applied_theme=applied.theme;result.applied_locale=applied.locale;result.viewport_height=width===390?844:900;result.captured_at=new Date().toISOString();result.errors=errors;result.blocked_external_requests=blocked.length;delete result.text;results.push(result);
  await page.close();
 }
 fs.writeFileSync(path.join(root,'rest-capture-results.json'),JSON.stringify({fixture_only:true,production_acceptance:false,checks:results},null,2));
 console.log('CANONICAL_VIEWPORT_MATRIX_PASS',results.length,'screenshots',results.length);console.log(JSON.stringify(results.filter(x=>x.state==='normal')));
})().catch(e=>{console.error(e.stack||e);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();if(server)await new Promise(r=>server.close(r));});
