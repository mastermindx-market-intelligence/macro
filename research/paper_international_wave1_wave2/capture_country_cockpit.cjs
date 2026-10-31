'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.INTL_BROWSER_RUNTIME || 'playwright');
const root = path.resolve(__dirname,'../..');
const output = path.join(__dirname,'country_cockpit_preview');
const html = fs.readFileSync(path.join(output,'intl_country_preview.html'),'utf8');
(async()=>{
 const browser = await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHROMIUM_CHANNEL?{channel:process.env.PLAYWRIGHT_CHROMIUM_CHANNEL}:{})});
 const receipts=[];
 for (const width of [1440,390]) for (const theme of ['dark','light']) for (const lang of ['en','zh']) {
  const context=await browser.newContext({viewport:{width,height:1000},deviceScaleFactor:1});
  const page=await context.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',async route=>{
   const url=new URL(route.request().url());
   if(url.hostname!=='intl.test') return route.abort();
   if(url.pathname==='/intl.html') return route.fulfill({contentType:'text/html',body:html});
   const file=path.resolve(root,'templates','.'+url.pathname);
   if(!file.startsWith(path.join(root,'templates')+path.sep)) return route.abort();
   if(fs.existsSync(file)&&fs.statSync(file).isFile()) return route.fulfill({path:file,
    contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':undefined});
   return route.fulfill({status:404,body:''});
  });
  await page.goto('http://intl.test/intl.html',{waitUntil:'load'});
  await page.evaluate(({theme,lang})=>{
   document.documentElement.dataset.theme=theme;
   document.documentElement.dataset.lang=lang;
  },{theme,lang});
  await page.evaluate(()=>document.fonts.ready);
  const geometry=await page.evaluate(()=>({
    viewport:innerWidth,scroll:document.documentElement.scrollWidth,
    title:document.querySelector('#imc-title').innerText,
    background:getComputedStyle(document.body).background,
    countryCount:document.querySelectorAll('.imc-country').length
  }));
  const file='country_cockpit_'+width+'_'+theme+'_'+lang+'.png';
  await page.screenshot({path:path.join(output,file),fullPage:true});
  const viewportFile='country_cockpit_'+width+'_'+theme+'_'+lang+'_viewport.png';
  await page.screenshot({path:path.join(output,viewportFile)});
  receipts.push({width,theme,lang,...geometry,errors,file,viewportFile});
  await context.close();
 }
 await browser.close();
 fs.writeFileSync(path.join(output,'visual_receipts.json'),JSON.stringify(receipts,null,2)+'\n');
 console.log(JSON.stringify(receipts));
})().catch(e=>{console.error(e);process.exitCode=1});
