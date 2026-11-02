import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {chromium} from '/Users/chriswong/.npm/_npx/fd3bca3c548369c0/node_modules/playwright/index.mjs';
const out=path.dirname(fileURLToPath(import.meta.url));
const root='/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/prophet-us-panel-authority-20260916-sol-001';
const source=fs.readFileSync(path.join(out,'real-gated-page.html'),'utf8');
const recorded=JSON.parse(fs.readFileSync(path.join(out,'real-render-comparison.json')));
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const mime={'.html':'text/html','.css':'text/css','.js':'application/javascript','.json':'application/json','.svg':'image/svg+xml','.woff2':'font/woff2'};
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
const records=[];
try{
 for(const theme of ['dark','light'])for(const locale of ['en','zh'])for(const width of [390,1440]){
  const context=await browser.newContext({viewport:{width,height:1000}});
  await context.addInitScript(({theme,locale})=>{localStorage.setItem('theme',theme);localStorage.setItem('lang',locale);},{theme,locale});
  const missing=new Set(),errors=[];
  await context.route('**/*',async route=>{
   const u=new URL(route.request().url());
   if(u.hostname!=='prophet-copy.invalid')return route.abort();
   if(u.pathname.startsWith('/premiumdata/')||u.pathname==='/api/me')return route.fulfill({status:401,body:'{}',contentType:'application/json'});
   if(u.pathname.startsWith('/live/')||u.pathname.startsWith('/stockdata/')||u.pathname.endsWith('.json')){missing.add(u.pathname);return route.fulfill({status:404,body:''});}
   if(u.pathname==='/us_stocks.html'){
    const html=source.replace(/<html\b[^>]*>/,`<html lang="${locale}" data-lang="${locale}" data-theme="${theme}">`);
    return route.fulfill({status:200,body:html,contentType:'text/html'});
   }
   const relative=u.pathname.replace(/^\/+/, '');
   for(const dir of ['templates','site']){
    const base=path.join(root,dir),file=path.resolve(base,relative);
    if(file.startsWith(base+path.sep)&&fs.existsSync(file)&&fs.statSync(file).isFile())return route.fulfill({status:200,body:fs.readFileSync(file),contentType:mime[path.extname(file)]||'application/octet-stream'});
   }
   missing.add(u.pathname);return route.fulfill({status:404,body:''});
  });
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://prophet-copy.invalid/us_stocks.html',{waitUntil:'domcontentloaded'});await page.waitForTimeout(600);
  const candidate=page.locator('#us-candidates .us-tier-wall');assert(await candidate.isVisible());
  const candText=await candidate.locator('.us-tw-h .l-'+locale).innerText();
  const tooltip=await page.locator('#us-src-toggle').getAttribute('data-tip-'+locale);
  assert(!/tonight|今晚/i.test(candText+' '+tooltip));assert(candText.includes(String(recorded.candidate_gate.locked)));
  assert.equal(await page.locator('#us-cand-grid a[data-ticker]').count(),3);
  const heading=await page.locator('#us-candidates .mx-sec-total .l-'+locale).innerText();assert(heading.includes('2026-09-16'));
  let img=path.join(out,`candidate-wall-${theme}-${locale}-${width}.png`);await candidate.screenshot({path:img,animations:'disabled',caret:'hide'});
  const candImage={path:path.basename(img),sha256:sha(fs.readFileSync(img))};
  // Ordinary source-view switch only; do not manipulate access tier or expand locked cards.
  await page.locator('#us-src-btn-plan').click();const plans=page.locator('#us-life-wall');await plans.waitFor({state:'visible'});
  const planText=await plans.locator('.us-tw-h .l-'+locale).innerText();
  assert(!/tonight|今晚|2026-09-16/i.test(planText));assert(planText.includes(String(recorded.visible_plan_locked)));
  assert.equal(await page.locator('#us-life-grid a[data-ticker]').count(),3);
  img=path.join(out,`plan-wall-${theme}-${locale}-${width}.png`);await plans.screenshot({path:img,animations:'disabled',caret:'hide'});
  const planImage={path:path.basename(img),sha256:sha(fs.readFileSync(img))};
  const layout=await plans.evaluate(el=>({width:el.clientWidth,scroll:el.scrollWidth}));assert(layout.scroll<=layout.width+1);assert.equal(errors.length,0);
  const record={theme,locale,width,source_heading:heading,candidate_message:candText,tooltip,plan_message:planText,preview_candidate_cards:3,preview_plan_cards:3,source_switch_clicks:1,access_tier_changes:0,layout,missing_optional:[...missing],page_errors:errors,screenshots:[candImage,planImage],pass:true};
  records.push(record);console.log('GATED_COPY_BROWSER_CASE',JSON.stringify(record));await context.close();
 }
 const result={proof_class:'local_actual_output_gated_page_browser','production':false,authenticated_delivery_proven:false,existing_profiles_used:false,protected_payload_response:401,live_overlay_response:404,source_html_sha256:sha(source),template_sha256:recorded.source_template_sha256,verifier_sha256:sha(fs.readFileSync(fileURLToPath(import.meta.url))),browser_version:browser.version(),cases:records,pass:records.length===8};
 fs.writeFileSync(path.join(out,'browser-receipt.json'),JSON.stringify(result,null,2)+'\n');
}finally{await browser.close();}
