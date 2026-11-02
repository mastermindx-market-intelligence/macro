/* Current-template, JavaScript-disabled source-date proof. No production claim. */
'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert/strict');
const {chromium}=require('playwright');
const ROOT=path.resolve(__dirname,'../../..');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const bind=f=>({path:path.relative(ROOT,f),sha256:hash(fs.readFileSync(f))});
async function main(){
 const browser=await chromium.launch({headless:true,executablePath:process.argv[2]});
 const cases=[],missingCss=new Set();
 try{
  for(const variant of ['stale','undated']) for(const locale of ['en','zh']) for(const width of [390,1440]){
   const htmlFile=path.join(ROOT,'.pytest_cache/US-candidate-'+variant+'.html');
   const source=fs.readFileSync(htmlFile,'utf8');
   const html=source.replace(/<html\b[^>]*>/,`<html lang="${locale}" data-lang="${locale}" data-theme="dark">`);
   assert.notEqual(html,source,'explicit static locale/theme fixture transform must apply');
   const context=await browser.newContext({javaScriptEnabled:false,viewport:{width,height:1000}});
   await context.route('**/*',async route=>{
    const u=new URL(route.request().url());
    if(u.pathname==='/us_stocks.html')return route.fulfill({status:200,body:html,contentType:'text/html'});
    const rel=u.pathname.replace(/^\/+/,''),file=path.resolve(ROOT,'templates',rel);
    if(!file.startsWith(path.join(ROOT,'templates')+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){
     if(u.pathname.endsWith('.css'))missingCss.add(u.pathname);
     return route.fulfill({status:404,body:''});
    }
    return route.fulfill({status:200,body:fs.readFileSync(file),contentType:rel.endsWith('.css')?'text/css':rel.endsWith('.js')?'application/javascript':'application/octet-stream'});
   });
   const page=await context.newPage();await page.goto('http://candidate-proof.invalid/us_stocks.html',{waitUntil:'load'});
   const heading=page.locator('#us-candidates .mx-sec-total .l-'+locale);
   assert(await heading.isVisible(),'requested locale must be visible without JS');
   const text=await heading.innerText();
   if(variant==='stale')assert(text.includes('2026-09-11'));
   else assert(text.includes(locale==='en'?'date unavailable':'日期不可用'));
   const candidateText=await page.locator('#us-candidates').innerText();assert(!/tonight|今晚/i.test(candidateText));
   const layout=await page.locator('#us-candidates .mx-sec-hd').evaluate(el=>({client_width:el.clientWidth,scroll_width:el.scrollWidth}));
   assert(layout.scroll_width<=layout.client_width+1,'heading must wrap inside viewport');
   const image=path.join(__dirname,`${variant}-${locale}-${width}.png`);
   await page.locator('#us-candidates .mx-sec-hd').screenshot({path:image});
   cases.push({variant,locale,width,source_date:variant==='stale'?'2026-09-11':null,text,layout,render_sha256:hash(source),screenshot:bind(image),pass:true});
   await context.close();
  }
  assert.equal(missingCss.size,0,'required stylesheet missing in candidate fixture');
  const result={schema:'mastermind.us_candidate_screen_date_fixture.v1',proof_class:'browser_fixture',production:'none',javascript_enabled:false,
   fixture_transform:'html locale/theme attributes only; candidate template and copy unchanged',browser:browser.version(),
   sources:[bind(path.join(ROOT,'templates/dashboard.html.j2')),bind(path.join(ROOT,'tests/test_p0_prophet_candidate_board.py'))],verifier:bind(__filename),cases,pass:cases.length===8};
  fs.writeFileSync(path.join(__dirname,'receipt.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({pass:result.pass,cases:cases.length,browser:result.browser}));
 }finally{await browser.close();}
}
main().catch(e=>{console.error(e.stack||e);process.exitCode=1;});
