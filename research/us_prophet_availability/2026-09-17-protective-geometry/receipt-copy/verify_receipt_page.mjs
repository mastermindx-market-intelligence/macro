import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {chromium} from '/Users/chriswong/.npm/_npx/fd3bca3c548369c0/node_modules/playwright/index.mjs';
const root=path.dirname(fileURLToPath(import.meta.url));
const templates='/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/prophet-protective-geometry-20260917-sol-001/templates';
const source=fs.readFileSync(path.join(root,'receipt-page-fixture.html'),'utf8');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const results=[];
try {
  for (const theme of ['dark','light']) for (const locale of ['en','zh']) for (const width of [390,1440]) {
    const html=source.replace(/<html\b[^>]*>/,`<html lang="${locale}" data-lang="${locale}" data-theme="${theme}">`);
    const context=await browser.newContext({viewport:{width,height:1000},javaScriptEnabled:false});
    const errors=[],refused=[];
    await context.route('**/*',async route=>{
      const url=new URL(route.request().url());
      if(url.origin==='http://receipt-proof.invalid'&&url.pathname==='/receipt.html')return route.fulfill({status:200,body:html,contentType:'text/html'});
      if(url.origin==='http://receipt-proof.invalid' && url.pathname.endsWith('.css')) {
        const file=path.resolve(templates,'.'+url.pathname);
        if(file.startsWith(templates+path.sep) && fs.existsSync(file))return route.fulfill({status:200,body:fs.readFileSync(file),contentType:'text/css'});
      }
      refused.push(url.pathname);return route.fulfill({status:404,body:''});
    });
    const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://receipt-proof.invalid/receipt.html',{waitUntil:'load',timeout:20000});
    await page.locator('details.pvr > summary').click();
    const group=page.locator('.pvr-g').first();const line=group.locator('.pvr-why .l-'+locale);
    assert(await line.isVisible(),'selected locale hidden');
    const text=await line.innerText();assert.equal(text,locale==='en'?'No entry plan is available — stand aside':'暂无入场计划 — 暂时观望');
    assert.equal((await group.locator('.pvr-n').innerText()).trim(),'3');
    const names=await group.locator('.pvr-tk').allTextContents();assert.deepEqual(names.map(x=>x.trim()),['HON','TRN','RBA']);
    const bounds=await group.evaluate(el=>({width:el.clientWidth,scroll:el.scrollWidth}));
    assert(bounds.scroll<=bounds.width+1,'receipt overflows');assert.equal(errors.length,0);
    const shot=path.join(root,`page-receipt-${theme}-${locale}-${width}.png`);await group.screenshot({path:shot,animations:'disabled'});
    const record={theme,locale,width,text,names,count:3,layout:bounds,screenshot:path.basename(shot),sha256:hash(fs.readFileSync(shot)),external_requests_completed:0,refused_optional_paths:[...new Set(refused)],page_errors:errors,pass:true};
    results.push(record);console.log('RECEIPT_BROWSER_CASE',JSON.stringify(record));await context.close();
  }
  const result={proof_class:'actual_dashboard_template_fixture_with_recorded_real_receipt_and_shared_theme',production:false,authenticated_delivery:false,existing_user_profiles:false,javascript_enabled:false,template:templates+'/_prophet_receipts.html.j2',template_sha256:hash(fs.readFileSync(path.join(templates,'_prophet_receipts.html.j2'))),browser:browser.version(),verifier_sha256:hash(fs.readFileSync(fileURLToPath(import.meta.url))),cases:results,pass:results.length===8};
  fs.writeFileSync(path.join(root,'page-browser-receipt.json'),JSON.stringify(result,null,2)+'\n');
}finally{await browser.close();}
