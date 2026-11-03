/* Browser regression contract against the production release owner. */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname,'../..');
const source = fs.readFileSync(process.env.RELEASE_CLIENT || path.join(root,'templates/release_publications_live.js'),'utf8');
const tests = [];
function test(name,run){tests.push({name,run});}
async function setup(browser,html='') {
 const page = await browser.newPage();
 await page.setContent(html);
 await page.evaluate(()=>{window.fetch=()=>new Promise(()=>{});});
 await page.addScriptTag({content:source});
 return page;
}
test('stale unparsed publications do not qualify as recent',async browser=>{
 const page=await setup(browser);const n=await page.evaluate(()=>window.__mmReleasePublicationTest.recentPublications({publications:[{event_id:'cpi-old',type:'CPI',date:'2026-10-01',status:'published_unparsed',detected_at:'2026-10-01T13:00:00Z'}]},new Date('2026-11-02T12:00:00Z')).length);assert.equal(n,0);await page.close();
});
test('future, invalid and missing detection clocks are not current',async browser=>{
 const page=await setup(browser);const n=await page.evaluate(()=>window.__mmReleasePublicationTest.recentPublications({publications:[{type:'CPI',status:'published',date:'2026-11-02',detected_at:'2026-11-03T13:00:00Z'},{type:'CPI',status:'published',date:'2026-11-02'},{type:'CPI',status:'published_unparsed',detected_at:'nonsense'}]},new Date('2026-11-02T12:00:00Z')).length);assert.equal(n,0);await page.close();
});
test('CPI release cannot overwrite a Jobs snapshot alert via explanatory copy',async browser=>{
 const page=await setup(browser,'<div id="dlg-news"><section><article data-al-row><h3><span class="l-en">A major event on deck</span><span class="l-zh">事件临近</span></h3><p><span class="l-en">Event-risk window: Jobs in 5 days</span><span class="l-zh">就业报告五天后</span></p><p><span class="l-en">CPI, FOMC and jobs are major releases.</span></p></article></section></div>');
 const before=await page.locator('[data-al-row]').innerText();await page.evaluate(()=>window.__mmReleasePublicationTest.patchProspectiveCopy({event_id:'cpi',type:'CPI',label:'CPI',data_ready:false},true));assert.equal(await page.locator('[data-al-row]').innerText(),before);await page.close();
});
test('older source payload cannot roll back an accepted newer payload',async browser=>{
 const page=await setup(browser);const results=await page.evaluate(()=>{const api=window.__mmReleasePublicationTest;const now=new Date('2026-11-02T12:00:00Z');return [api.render({built:'2026-11-02T11:59:50Z',publications:[],events:[]},now),api.render({built:'2026-11-02T11:59:00Z',publications:[],events:[]},now)]});assert.deepEqual(results,[true,false]);await page.close();
});
test('malformed rows do not destroy the valid release state',async browser=>{
 const page=await setup(browser,strip);const value=await page.evaluate(()=>{const api=window.__mmReleasePublicationTest;return api.render({built:'2026-11-02T12:00:00Z',publications:[null,5,{event_id:'cpi',type:'CPI',date:'2026-11-02',status:'published_unparsed',detected_at:'2026-11-02T11:59:30Z'}],events:'invalid'},new Date('2026-11-02T12:00:00Z'));});assert.equal(value,true);assert.equal(await page.locator('[data-news-release]').getAttribute('data-state'),'partial');assert.match(await page.locator('[data-news-release-summary]').innerText(),/1 release awaiting verification.*partial coverage/);await page.close();
});
const strip='<div id="dlg-news"><aside data-news-release data-state="unknown"><p data-news-release-summary></p><span data-news-release-clock></span></aside></div><div id="sx-news-v2"><span class="mx5-card-badge"></span></div>';
test('bad publication clocks are explicit uncertainty; future build cannot poison ordering',async browser=>{
 const page=await setup(browser,strip);const result=await page.evaluate(()=>{const api=window.__mmReleasePublicationTest,now=new Date('2026-11-02T12:00:00Z');const future=api.render({built:'2026-11-02T12:00:01Z',publications:[],events:[]},now);const valid=api.render({built:now.toISOString(),publications:[{event_id:'jobs',type:'Jobs',date:'2026-11-02',status:'published',detected_at:'2026-11-02T24:00:00Z',data_ready:true,actual:{summary_en:'NFP fixture'}}],events:[]},now);return {future,valid,state:document.querySelector('[data-news-release]').dataset.state,text:document.querySelector('[data-news-release-summary] .l-en').textContent}});assert.deepEqual(result,{future:false,valid:true,state:'uncertain',text:'1 release time needs checking'});await page.close();
});
test('empty events does not hide due rows, and distinct release identities stay separate',async browser=>{
 const page=await setup(browser,strip);const count=await page.evaluate(()=>window.__mmReleasePublicationTest.awaitingEvents({events:[],due:[{event_id:'cpi-b',type:'CPI',date:'2026-11-02',status:'awaiting_publication'}],upcoming:[]},new Date('2026-11-02T12:00:00Z'),{'event:cpi-a':true}).length);assert.equal(count,1);await page.close();
});
test('old detection remains explicit delayed verification and is never called verified',async browser=>{
 const page=await setup(browser,strip);const result=await page.evaluate(()=>{const now=new Date('2026-11-02T12:00:00Z');window.__mmReleasePublicationTest.render({built:now.toISOString(),publications:[{event_id:'cpi-old',type:'CPI',date:'2026-10-01',status:'published_unparsed',detected_at:'2026-10-01T13:00:00Z'}],events:[{event_id:'cpi-old',type:'CPI',date:'2026-10-01',status:'published_unparsed'}]},now);return {state:document.querySelector('[data-news-release]').dataset.state,text:document.querySelector('[data-news-release-summary] .l-en').textContent,badge:document.querySelector('.mx5-card-badge .l-en').textContent}});assert.equal(result.state,'delayed');assert.match(result.text,/1 release.*delayed/);assert.doesNotMatch(result.badge,/verified|Live/);await page.close();
});
test('a data_ready flag without readable facts stays unverified',async browser=>{
 const page=await setup(browser,strip);const state=await page.evaluate(()=>{const now=new Date('2026-11-02T12:00:00Z');window.__mmReleasePublicationTest.render({built:now.toISOString(),publications:[{event_id:'cpi-test',type:'CPI',date:'2026-11-02',status:'published',detected_at:now.toISOString(),data_ready:true,actual:{}}],events:[]},now);return document.querySelector('[data-news-release]').dataset.state});assert.equal(state,'verifying');await page.close();
});
test('an explicitly unparsed publication cannot become verified through a contradictory flag',async browser=>{
 const page=await setup(browser,strip);const state=await page.evaluate(()=>{const now=new Date('2026-11-02T12:00:00Z');window.__mmReleasePublicationTest.render({built:now.toISOString(),publications:[{event_id:'cpi-test',type:'CPI',date:'2026-11-02',status:'published_unparsed',detected_at:now.toISOString(),data_ready:true,actual:{summary_en:'Contradictory fixture'}}],events:[]},now);return document.querySelector('[data-news-release]').dataset.state});assert.equal(state,'verifying');await page.close();
});
test('polls are single-flight; a timed-out late response cannot overwrite the next result',async browser=>{
 const page=await browser.newPage();await page.setContent(strip);
 await page.evaluate(()=>{window.pending=[];window.deadlines=[];const realSet=window.setTimeout.bind(window);window.setTimeout=(fn,ms)=>ms===15000?(window.deadlines.push(fn),98765):realSet(fn,ms);window.fetch=()=>new Promise(resolve=>window.pending.push(resolve));});
 await page.addScriptTag({content:source});
 assert.equal(await page.evaluate(()=>{window.__mmReleasePublicationTest.poll();return window.pending.length}),1);
 await page.evaluate(async()=>{window.deadlines.shift()();await window.__mmReleasePublicationTest.poll();});
 await page.evaluate(()=>{window.nextPoll=window.__mmReleasePublicationTest.poll();});
 assert.equal(await page.evaluate(()=>window.pending.length),2);
 await page.evaluate(async()=>{const now=new Date();window.pending[1]({ok:true,json:async()=>({built:new Date(now.getTime()-1000).toISOString(),publications:[],events:[]})});await window.nextPoll;window.pending[0]({ok:true,json:async()=>({built:now.toISOString(),publications:[{event_id:'late-cpi',type:'CPI',date:now.toISOString().slice(0,10),status:'published_unparsed',detected_at:now.toISOString()}],events:[]})});await Promise.resolve();await Promise.resolve();});
 assert.equal(await page.locator('[data-news-release]').getAttribute('data-state'),'empty');await page.close();
});
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH});let failed=0;for(const t of tests){try{await t.run(browser);console.log('PASS '+t.name)}catch(e){failed++;console.log('FAIL '+t.name+' — '+e.message.split('\n')[0])}}await browser.close();console.log(JSON.stringify({tests:tests.length,failed}));process.exitCode=failed?1:0;})();
