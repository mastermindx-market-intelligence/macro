#!/usr/bin/env node
/* Reproduce PR #7163's two existing modal-entry routes. Fixture proof only. */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const assert = require('assert/strict');
const {chromium} = require('playwright');
const ROOT = path.resolve(__dirname, '..');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const relative = file => path.relative(ROOT, file).split(path.sep).join('/');
const bind = file => ({path: relative(file), sha256: sha(fs.readFileSync(file))});
const args = {};
for (let i=2; i<process.argv.length; i+=2) {
  assert(process.argv[i].startsWith('--') && process.argv[i+1], 'expected --flag value');
  args[process.argv[i].slice(2)] = process.argv[i+1];
}
const html = path.resolve(args.html);
const fixture = path.resolve(args['fixture-receipt']);
const out = path.resolve(args.out);
const shots = path.dirname(out) + '/screenshots';
const fixtureAssets = path.join(ROOT, 'mockups/evidence/prophet-p0b-zero-fouc/inputs/browser-data');
assert(html.startsWith(ROOT + path.sep) && out.startsWith(ROOT + path.sep));
const fixtureDoc = JSON.parse(fs.readFileSync(fixture));
assert.equal(sha(fs.readFileSync(html)), fixtureDoc.markets.hk.output_sha256);
const MIME = {'.html':'text/html','.js':'application/javascript','.css':'text/css',
  '.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.woff2':'font/woff2'};
async function installRoutes(context) {
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    const rel = url.pathname.replace(/^\/+/, '');
    const override = path.resolve(fixtureAssets, rel);
    const file = url.pathname === '/hk_stocks.html' ? html :
      override.startsWith(fixtureAssets + path.sep) && fs.existsSync(override) ? override :
      path.resolve(ROOT, 'site', rel);
    if (file !== html && !file.startsWith(path.join(ROOT,'site') + path.sep) &&
        !file.startsWith(fixtureAssets + path.sep)) return route.fulfill({status:403,body:''});
    if (!fs.existsSync(file) || !fs.statSync(file).isFile()) return route.fulfill({status:404,body:''});
    await route.fulfill({status:200,body:fs.readFileSync(file),
      contentType:MIME[path.extname(file)] || 'application/octet-stream'});
  });
}
async function main() {
  const browser = await chromium.launch({headless:true, executablePath:args.browser});
  const cases = [], fallback = [], screenshots = [];
  try {
    for (const lang of ['en','zh']) for (const theme of ['dark','light']) {
      const context = await browser.newContext({viewport:{width:1280,height:900}});
      await context.addInitScript(({lang,theme}) => {
        localStorage.setItem('lang',lang);localStorage.setItem('theme',theme);
      },{lang,theme});
      await installRoutes(context);
      const page = await context.newPage();const errors=[],deadRequests=[];
      page.on('pageerror',e=>errors.push(e.message));
      page.on('request',r=>{if(new URL(r.url()).pathname.endsWith('/sector_ranking.html'))deadRequests.push(r.url());});
      await page.goto('http://stock-dashboard.invalid/hk_stocks.html',{waitUntil:'load'});
      await page.waitForSelector('#hk-v37[data-hk-enhanced="true"]');
      await page.waitForTimeout(500);
      const links = page.locator('a[data-hk-expand]');assert.equal(await links.count(),2);
      assert.equal(await page.locator('a[href*="sector_ranking.html"]').count(),0);
      await page.evaluate(()=>{
        window.__modalProofCards = Array.from(document.querySelectorAll('#hk-v37-card-grid .pvcard[data-ticker]'));
      });
      const before = await page.locator('#hk-v37-card-grid .pvcard[data-ticker]').count();assert(before>0);
      for (let index=0; index<2; index++) {
        const beforeUrl=page.url();assert.equal(await links.nth(index).getAttribute('href'),'#hk-v37-expand');
        await links.nth(index).click();
        await page.waitForSelector('#hk-v37-modal.is-open[aria-hidden="false"]');
        const unchanged=await page.evaluate(()=>{
          const now=Array.from(document.querySelectorAll('#hk-v37-card-grid .pvcard[data-ticker]'));
          return now.length===window.__modalProofCards.length && now.every((n,i)=>n===window.__modalProofCards[i]);
        });
        const row={locale:lang,theme,control_index:index,href:'#hk-v37-expand',
          modal_open:await page.locator('#hk-v37-modal').isVisible(),url_unchanged:page.url()===beforeUrl,
          owner_nodes_unchanged:unchanged,owner_preview_count:before,dead_route_requests:deadRequests.length};
        row.pass=row.modal_open && row.url_unchanged && unchanged && !deadRequests.length && !errors.length;
        cases.push(row);assert(row.pass,JSON.stringify({row,errors}));
        if (lang==='en' && index===0) {
          const file=path.join(shots,`sector-modal-${theme}.png`);
          await page.screenshot({path:file,animations:'disabled',caret:'hide'});screenshots.push(bind(file));
        }
        await page.locator('[data-hk-modal-close]').first().click();
        await page.waitForSelector('#hk-v37-modal[aria-hidden="true"]',{state:'attached'});
      }
      await context.close();
    }
    for (let index=0; index<2; index++) {
      const context=await browser.newContext({javaScriptEnabled:false,viewport:{width:1280,height:900}});
      await installRoutes(context);const page=await context.newPage();
      await page.goto('http://stock-dashboard.invalid/hk_stocks.html',{waitUntil:'load'});
      assert.equal(await page.locator('#hk-v37-expand').count(),1);
      await page.locator('a[data-hk-expand]').nth(index).click();
      const u=new URL(page.url());const row={control_index:index,same_page:u.pathname==='/hk_stocks.html',
        fragment:u.hash,target_present:await page.locator('#hk-v37-expand').count()===1};
      row.pass=row.same_page && row.fragment==='#hk-v37-expand' && row.target_present;
      fallback.push(row);assert(row.pass);await context.close();
    }
    const result={schema:'mastermind.hk_sector_modal_fixture.v1',proof_class:'browser_fixture',production:'none',
      verifier:bind(__filename),browser:{engine:'chromium',version:browser.version()},fixture_receipt:bind(fixture),
      inputs:{'templates/hk.html.j2':sha(fs.readFileSync(path.join(ROOT,'templates/hk.html.j2'))),
        'site/hk-stock-v36.js':sha(fs.readFileSync(path.join(ROOT,'site/hk-stock-v36.js')))},
      modal_cases:cases,no_js_cases:fallback,screenshots,pass:cases.length===8&&fallback.length===2};
    fs.writeFileSync(out,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({pass:result.pass,modal_cases:cases.length,no_js_cases:fallback.length}));
  } finally {await browser.close();}
}
main().catch(e=>{console.error(e.stack||String(e));process.exitCode=1;});
