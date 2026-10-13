#!/usr/bin/env node
/* Observe the real loopback admin server. No session interception, synthetic API
   responses, login submission, or administrative mutation is used here. */
const fs = require('node:fs');
const path = require('node:path');
const modulePath = process.env.PLAYWRIGHT_MODULE || 'playwright';
const {chromium} = require(modulePath);
const base = process.env.ADMIN_OBSERVE_URL || 'http://127.0.0.1:8799';
const out = process.env.ADMIN_EVIDENCE_DIR || 'research/evidence/admin-workspace-20261013';
if (!['127.0.0.1','localhost','::1'].includes(new URL(base).hostname)) throw new Error('Only an intentional loopback admin server may be observed.');
const evidence = {asof:new Date().toISOString(),scope:'Actual loopback development server; no authenticated production acceptance',checks:[],errors:[],apiMethods:[]};
function check(name, pass) { evidence.checks.push({name,pass:!!pass}); if (!pass) throw new Error(name); }
(async () => {
 fs.mkdirSync(out,{recursive:true});
 const browser = await chromium.launch({headless:true});
 try {
  const page = await browser.newPage({viewport:{width:1440,height:960},reducedMotion:'reduce'});
  page.on('pageerror',error=>evidence.errors.push(error.message));
  page.on('request',request=>{if(new URL(request.url()).pathname.startsWith('/api/')) evidence.apiMethods.push(request.method());});
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.locator('#admin-home-title, #adminRetry, #login.show').first().waitFor({timeout:60000});
  check('Local server is not a simulated authenticated response', !(await page.locator('#login.show').count()));
  await page.screenshot({path:path.join(out,'after-desktop.png')});
  check('All 54 source navigation routes remain present', await page.locator('.nav-item').count()===54);
  await page.locator('#workspaceOpen').click();
  await page.locator('#workspaceDialog[open]').waitFor();
  check('Command dialog focuses the search field', await page.locator('#workspaceSearch').evaluate(el=>el===document.activeElement));
  await page.locator('#workspaceSearch').fill('customer help');
  check('Task search resolves customer help', (await page.locator('#workspaceResults').innerText()).includes('Support Tickets'));
  await page.screenshot({path:path.join(out,'task-search.png')});
  await page.keyboard.press('Escape');
  await page.locator('#workspaceDialog').waitFor({state:'hidden'});
  await page.waitForFunction(() => document.activeElement.id === 'workspaceOpen', null, {timeout:2000}).catch(async () => { console.log('FOCUS_DIAGNOSTIC', await page.evaluate(() => ({id:document.activeElement.id,tag:document.activeElement.tagName,open:document.getElementById('workspaceDialog').open}))); });
  check('Closing dialog returns focus to its trigger', await page.locator('#workspaceOpen').evaluate(el=>el===document.activeElement));
  await page.locator('#workspacePin').click();
  check('Page can be pinned without an API mutation', await page.locator('#workspacePin').getAttribute('aria-pressed')==='true');
  await page.reload({waitUntil:'domcontentloaded'});
  await page.locator('#admin-home-title, #adminRetry').first().waitFor({timeout:60000});
  check('Pinned page survives reload', await page.locator('#workspacePin').getAttribute('aria-pressed')==='true');
  await page.keyboard.press('Control+k');
  await page.locator('#workspaceSearch').fill('zzzz_no_such_tool');
  check('Empty task search has a visible recovery', await page.locator('#workspaceEmpty').isVisible());
  await page.locator('#workspaceReset').click();
  check('All-tools reset restores every tool', await page.locator('#workspaceResults [role=option]').count()===54);
  await page.keyboard.press('Escape');
  await page.context().setOffline(true);
  await page.locator('#workspaceRefresh').click();
  await page.locator('#workspaceStatus[data-state="failed"]').waitFor();
  check('Failed refresh stays visible beside the retained snapshot', (await page.locator('#workspaceStatusText').innerText()).includes('previous snapshot'));
  check('A failed refresh cannot retain a healthy status badge', (await page.locator('#adminHealthStatus').innerText()).includes('Read failed'));
  await page.screenshot({path:path.join(out,'failed-refresh.png')});
  await page.context().setOffline(false);
  await page.locator('#workspaceRefresh').click();
  await page.locator('#workspaceStatus[data-state="current"]').waitFor();
  check('Successful retry clears the persistent failure state', !(await page.locator('#adminHealthStatus').innerText()).includes('Read failed'));
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:path.join(out,'after-mobile.png')});
  check('Mobile shell has no horizontal overflow', await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  check('Mobile tool search has a full-width hit target on the title row', await page.locator('#workspaceOpen').evaluate(el=>{const a=el.getBoundingClientRect(),b=document.getElementById('topbar-title').getBoundingClientRect();return a.width>=80&&a.right<=innerWidth&&Math.abs(a.top-b.top)<20;}));
  await page.locator('#workspaceOpen').click();
  await page.screenshot({path:path.join(out,'mobile-tools.png')});
  check('Mobile dialog has no horizontal overflow', await page.locator('#workspaceDialog').evaluate(el=>el.scrollWidth<=el.clientWidth));
  await page.keyboard.press('Escape');
  await page.locator('#workspacePin').click();
  check('Pin is reversible', await page.locator('#workspacePin').getAttribute('aria-pressed')==='false');
  check('No JavaScript exceptions were observed', evidence.errors.length===0);
  check('Navigation observation used no API writes', evidence.apiMethods.every(method=>['GET','HEAD'].includes(method)));
 } finally { await browser.close(); fs.writeFileSync(path.join(out,'observation.json'),JSON.stringify(evidence,null,2)+'\n'); }
 console.log(JSON.stringify({checks:evidence.checks.length,passed:evidence.checks.filter(x=>x.pass).length,errors:evidence.errors,evidence:out}));
})().catch(error=>{console.error(error.message);process.exitCode=1;});
