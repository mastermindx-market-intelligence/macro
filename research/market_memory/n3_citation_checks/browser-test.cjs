const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert/strict');
(async()=>{
 const root=process.argv[2],out=process.argv[3],citations=JSON.parse(fs.readFileSync(path.join(out,'N3_GATEWAY_LINK_FIXTURE.json')));
 const browser=await chromium.launch({headless:true});const cells=[];
 for(const theme of ['dark','light'])for(const lang of ['en','zh'])for(const width of [1440,390]){
  const ctx=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'}),p=await ctx.newPage(),errors=[];
  p.on('pageerror',e=>errors.push(e.message));
  await p.route('**/*',async route=>{
   const u=new URL(route.request().url());let body={};
   if(u.pathname==='/')return route.fulfill({contentType:'text/html',body:`<html data-theme="${theme}" data-lang="${lang}"><head></head><body></body></html>`});
   if(u.pathname==='/api/brain/stream'){
    const events=[{type:'meta',thread_id:'11111111-1111-1111-1111-111111111111'},{type:'delta',text:'Fixture retained evidence with original source locators.'},{type:'done',citations}];
    return route.fulfill({contentType:'text/event-stream',body:events.map(x=>'data: '+JSON.stringify(x)+'\n\n').join('')});
   }
   if(u.pathname.endsWith('/me'))body={tier:'pro',quotas:{fast:{limit:-1},pro:{limit:-1}}};
   if(u.pathname.endsWith('/threads'))body={threads:[]};
   return route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
  });
  await p.goto('http://market-memory-citation.test/');
  await p.evaluate(()=>{window.MDXAuth={onChange:fn=>fn({id:'synthetic-fixture-user'}),enabled:()=>true};window.MM_BRAIN_CFG={anchor:'top',page:'terminal',api:''};});
  await p.addScriptTag({path:path.join(root,'templates/mm_brain.js')});
  await p.evaluate(()=>{MMBrain.open();MMBrain.expand();});
  await p.locator('#mmb-ta').fill('Read the exact retained fixture source.');await p.locator('#mmb-send').click();
  await p.waitForFunction(()=>document.querySelectorAll('.mmb-cites a[href]').length===3);
  const links=await p.locator('.mmb-cites a').evaluateAll(els=>els.map(e=>({href:e.href,label:e.textContent,target:e.target,rel:e.rel,rect:e.getBoundingClientRect().toJSON()})));
  assert.deepEqual(links.map(x=>x.href),citations);assert.equal(errors.length,0);
  for(const a of links){assert.ok(a.label.startsWith(lang==='zh'?'市场记忆来源':'Market memory source'));assert.ok(!a.label.includes('<span'));assert.equal(a.target,'_blank');assert.ok(a.rect.width>0);}
  const overflow=await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);assert.equal(overflow,false);
  const screenshot=`N3_WIDGET_${theme}_${lang}_${width}.png`;await p.screenshot({path:path.join(out,screenshot)});
  cells.push({theme,lang,width,links:links.map(({rect,...x})=>x),pageErrors:errors,overflow,screenshot,pass:true});await ctx.close();
 }
 await browser.close();const source=fs.readFileSync(path.join(root,'templates/mm_brain.js'));
 fs.writeFileSync(path.join(out,'N3_WIDGET_BROWSER_RECEIPT.json'),JSON.stringify({fixtureOnly:true,source_sha256:crypto.createHash('sha256').update(source).digest('hex'),cells},null,2));
 console.log(JSON.stringify({cells:cells.length,allPassed:true,fixtureOnly:true}));
})().catch(e=>{console.error(e.stack);process.exit(1);});
