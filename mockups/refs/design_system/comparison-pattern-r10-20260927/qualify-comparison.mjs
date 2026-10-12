import {spawn} from 'node:child_process';
import {mkdtempSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
const root=process.argv[2], profile=mkdtempSync(join(root,'chrome-profile-'));
const child=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless=new','--no-first-run','--no-default-browser-check','--disable-background-networking','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:['ignore','ignore','pipe']});
let ws,seq=0,session;const pending=new Map(),exceptions=[],cells=[];const sleep=ms=>new Promise(r=>setTimeout(r,ms));
writeFileSync(join(root,'browser-process.json'),JSON.stringify({pid:child.pid,profile,operation:'design-system-r10-comparison-qualification-20260927'}));
function send(method,params={},sid=session){return new Promise((resolve,reject)=>{const id=++seq;const timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout '+method));},10000);pending.set(id,{resolve,reject,timer});ws.send(JSON.stringify({id,method,params,...(sid?{sessionId:sid}:{})}));});}
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
const settle=()=>evaluate('document.fonts.ready.then(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))))');
async function key(key,code,v){const p={type:'keyDown',key,code,windowsVirtualKeyCode:v};if(key==='Enter')p.text=p.unmodifiedText='\r';else if(key.length===1)p.text=p.unmodifiedText=key;await send('Input.dispatchKeyEvent',p);await send('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:v});}
async function until(expr){for(let i=0;i<70;i++){if(await evaluate(expr))return;await sleep(60);}throw new Error('Condition timeout '+expr);}
async function shot(file,target){await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(target)});scrollTo(0,e.getBoundingClientRect().top+scrollY-document.querySelector('.bar').getBoundingClientRect().height-16)})()`);await settle();await sleep(250);const d=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});writeFileSync(join(root,file),Buffer.from(d.data,'base64'));}
try{
 const endpoint=await new Promise((resolve,reject)=>{let text='';const timer=setTimeout(()=>reject(new Error('Chrome launch timeout')),15000);child.stderr.on('data',b=>{text+=b.toString();const m=text.match(/DevTools listening on (ws:\/\/\S+)/);if(m){clearTimeout(timer);resolve(m[1]);}});child.on('exit',c=>{if(!text.includes('DevTools listening'))reject(new Error('Chrome exit '+c));});});
 ws=new WebSocket(endpoint);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});ws.onmessage=e=>{const d=JSON.parse(e.data);if(d.id&&pending.has(d.id)){const p=pending.get(d.id);clearTimeout(p.timer);pending.delete(d.id);d.error?p.reject(new Error(JSON.stringify(d.error))):p.resolve(d.result);}else if(d.method==='Runtime.exceptionThrown')exceptions.push(d.params);};
 const target=await send('Target.createTarget',{url:'about:blank'},null);session=(await send('Target.attachToTarget',{targetId:target.targetId,flatten:true},null)).sessionId;
 for(const method of ['Page.enable','Runtime.enable','Network.enable','Accessibility.enable'])await send(method);
 await send('Page.bringToFront');await send('Network.setBlockedURLs',{urls:['http://*','https://*']});await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
 for(const [width,scale] of [[320,1],[390,1],[768,1],[1440,1],[390,2]])for(const theme of ['dark','light'])for(const lang of ['en','zh']){
  const result={width,typeScale:scale,theme,lang,checks:[]};const check=(name,pass,detail)=>result.checks.push({name,pass:!!pass,...(detail===undefined?{}:{detail})});
  await send('Emulation.setDeviceMetricsOverride',{width,height:1050,deviceScaleFactor:1,mobile:false});
  const url=pathToFileURL(join(root,'source/mockups/design_system/specimen.html')).href+'?market=US&case='+cells.length+'#spec-spine-comparison';
  await send('Page.navigate',{url});await until(`location.href===${JSON.stringify(url)}&&document.readyState==='complete'&&!!document.getElementById('spec-spine-inspect')`);
  await evaluate(`(()=>{const r=document.documentElement;if((r.getAttribute('data-theme')||'dark')!==${JSON.stringify(theme)})document.querySelector('#t-theme').click();if(r.getAttribute('data-lang')!==${JSON.stringify(lang)})document.querySelector('#t-lang').click();})()`);await settle();
  if(scale===2){await evaluate("(()=>{const all=[...document.querySelectorAll('body *')].map(e=>[e,parseFloat(getComputedStyle(e).fontSize)]);all.forEach(([e,n])=>e.style.fontSize=(n*2)+'px')})()");await settle();}
  const before=await evaluate('JSON.stringify({url:location.href,local:Object.entries(localStorage),session:Object.entries(sessionStorage)})');
  const summary=await evaluate(`(()=>{const e=document.getElementById('spec-spine-comparison');return {context:e.querySelector('#spec-spine-context').innerText,summary:e.querySelector('#spec-spine-summary').innerText,limit:e.querySelector('#spec-spine-limit').innerText,closed:!e.querySelector('#spec-spine-details').open,lang:document.documentElement.lang,leaks:[...e.querySelectorAll('.l-${lang==='en'?'zh':'en'}')].filter(x=>getComputedStyle(x).display!=='none').length}})()`);
  check('context_visible_before_detail',summary.context.includes(lang==='en'?'Fictional':'虚构')&&summary.closed,summary);
  check('summary_exposes_missing_comparison',summary.summary.includes(lang==='en'?'1 unavailable':'1项暂无数据'));
  check('units_and_not_probability_at_rest',summary.limit.includes(lang==='en'?'not probabilities':'不是概率'));
  check('one_visible_locale_and_document_language',!summary.leaks&&summary.lang===(lang==='zh'?'zh-CN':'en'));
  const geometry=await evaluate(`(()=>{const groups=[...document.querySelectorAll('#spec-spine-comparison [data-spec^="ud-b1"]')];return groups.map(group=>({group:group.dataset.spec,rows:[...group.querySelectorAll(':scope > .mx-spine-row')].map(row=>{const rail=row.querySelector('.mx-spine-rail'),r=rail.getBoundingClientRect(),style=getComputedStyle(rail),origin=r.left+parseFloat(style.borderLeftWidth),unit=rail.clientWidth/100;const mark=row.querySelector('.mx-spine-mark'),prev=row.querySelector('.mx-spine-prev'),conn=row.querySelector('.mx-spine-conn'),delta=row.querySelector('.mx-spine-travel .tnum');const center=e=>{const b=e.getBoundingClientRect();return (b.left+b.width/2-origin)/unit};return {missing:row.dataset.null==='1',current:mark?parseFloat(mark.style.left):null,previous:prev?parseFloat(prev.style.left):null,delta:delta?Number(delta.innerText.replace('−','-')):null,currentPaint:mark?center(mark):null,previousPaint:prev?center(prev):null,connectorStart:conn?(conn.getBoundingClientRect().left-origin)/unit:null,connectorLength:conn?conn.getBoundingClientRect().width/unit:null,unit,markCount:row.querySelectorAll('.mx-spine-mark,.mx-spine-prev,.mx-spine-conn').length};})}));})()`);
  result.geometry=geometry;
  for(const group of geometry)for(const [i,r] of group.rows.entries()){
   const key=group.group+'/'+i;
   if(r.missing){check(key+'/missing_is_not_zero',r.current===null&&r.previous===null&&r.delta===null&&r.markCount===0);continue;}
   check(key+'/stated_delta_agrees',r.current-r.previous===r.delta);
   check(key+'/painted_endpoints_match',Math.abs(r.currentPaint-r.current)*r.unit<=1&&Math.abs(r.previousPaint-r.previous)*r.unit<=1,r);
   check(key+'/line_connects_actual_endpoints',Math.abs(r.connectorStart-Math.min(r.current,r.previous))*r.unit<=1&&Math.abs(r.connectorLength-Math.abs(r.delta))*r.unit<=1);
  }
  check('primary_has_five_and_mobile_has_three',geometry[0].rows.length===5&&geometry[1].rows.length===3);
  const layout=await evaluate(`(()=>{const stage=document.querySelector('.wrap'),primary=document.querySelector('[data-spec="ud-b1"]'),phone=document.querySelector('[data-spec="ud-b1-390"]');return {width:stage.getBoundingClientRect().width,header:getComputedStyle(primary.querySelector('.mx-spine-head')).display,primaryAreas:getComputedStyle(primary.querySelector('.mx-spine-row')).gridTemplateAreas,phoneAreas:getComputedStyle(phone.querySelector('.mx-spine-row')).gridTemplateAreas}})()`);
  check('primary_adapts_instead_of_forcing_phone_layout',layout.width<=640?layout.header==='none'&&layout.primaryAreas.includes('rail'):layout.header!=='none'&&layout.primaryAreas==='none',layout);
  check('explicit_phone_example_stays_stacked',layout.phoneAreas.includes('rail'));
  const refinement=await evaluate("(()=>{const p=document.querySelector('[data-spec=ud-b1]'),r=p.querySelectorAll(':scope > .mx-spine-row'),phone=document.querySelector('[data-spec=ud-b1-390]').parentElement;return {delta:Math.abs(r[0].querySelector('.mx-spine-stance').getBoundingClientRect().left-r[4].querySelector('.mx-spine-stance').getBoundingClientRect().left),phoneWidth:phone.getBoundingClientRect().width}})()");
  check('unavailable_stance_aligned_on_wide',layout.width<=640||refinement.delta<=1,refinement);
  check('explicit_phone_preview_is_phone_width',refinement.phoneWidth<=390+1);


  await evaluate("const s=document.getElementById('spec-spine-inspect');s.scrollIntoView({block:'center'});s.focus()");await key('Enter','Enter',13);await settle();
  check('keyboard_opens_and_retains_focus',await evaluate("document.getElementById('spec-spine-details').open&&document.activeElement.id==='spec-spine-inspect'"));
  const table=await evaluate(`(()=>{const t=document.getElementById('spec-spine-values');return {rows:[...t.tBodies[0].rows].map(r=>({key:r.dataset.specSpineMarket,cells:[...r.cells].map(x=>x.innerText)})),caption:t.caption.innerText,headerScopes:[...t.tHead.querySelectorAll('th')].every(x=>x.scope==='col'),rowScopes:[...t.tBodies[0].querySelectorAll('th')].every(x=>x.scope==='row'),width:t.parentElement.clientWidth,content:t.parentElement.scrollWidth}})()`);result.table=table;
  check('complete_five_row_text_equivalent',table.rows.length===5&&table.headerScopes&&table.rowScopes&&table.caption.length>0);
  check('table_matches_primary_geometry',table.rows.slice(0,4).every((r,i)=>{const values=r.cells.slice(1).map(v=>Number(v.replace('−','-'))),g=geometry[0].rows[i];return values[0]===g.previous&&values[1]===g.current&&values[2]===g.delta;}));
  check('text_equivalent_keeps_unavailable',table.rows[4].cells[1]===(lang==='en'?'Unavailable':'暂无数据'));
  check('ordinary_phone_values_fit',scale!==1||table.content<=table.width+1,{width:table.width,content:table.content});
  const ax=await send('Accessibility.getFullAXTree');check('table_semantics_in_accessibility_tree',ax.nodes.some(n=>!n.ignored&&n.role?.value==='table'&&n.name?.value===table.caption));
  if(width===390&&theme==='light'&&lang==='zh'&&scale===1)await shot('comparison-values-390-light-zh.png','#spec-spine-details');
  if(width===1440&&theme==='dark'&&lang==='en'&&scale===1)await shot('comparison-values-1440-dark.png','#spec-spine-details');
  await evaluate("document.getElementById('spec-spine-inspect').focus()");await key(' ','Space',32);await settle();check('keyboard_closes_and_keeps_initiator',await evaluate("!document.getElementById('spec-spine-details').open&&document.activeElement.id==='spec-spine-inspect'"));
  const fit=await evaluate('({doc:document.documentElement.scrollWidth,client:document.documentElement.clientWidth})');check('document_contained',fit.doc<=fit.client+1,fit);
  check('inspection_has_no_url_or_storage_effect',before===await evaluate('JSON.stringify({url:location.href,local:Object.entries(localStorage),session:Object.entries(sessionStorage)})'));
  const control=await evaluate("(()=>{const b=document.getElementById('t-width').getBoundingClientRect();return {x:b.x+b.width/2,y:b.y+b.height/2}})()");
  for(const type of ['mousePressed','mouseReleased'])await send('Input.dispatchMouseEvent',{type,button:'left',clickCount:1,...control});
  await until("document.body.classList.contains('mobile-sim')&&document.querySelector('.wrap').classList.contains('mockup-spine-390')");await settle();
  check('simulator_uses_narrow_geometry',await evaluate("getComputedStyle(document.querySelector('[data-spec=ud-b1] .mx-spine-head')).display==='none'"));
  for(const type of ['mousePressed','mouseReleased'])await send('Input.dispatchMouseEvent',{type,button:'left',clickCount:1,...control});
  await until("!document.body.classList.contains('mobile-sim')");await settle();
  check('leaving_simulator_restores_matching_geometry',await evaluate("(()=>{const w=document.querySelector('.wrap').getBoundingClientRect().width,h=getComputedStyle(document.querySelector('[data-spec=ud-b1] .mx-spine-head')).display;return w<=640?h==='none':h!=='none'})()"));

  if(width===1440&&lang==='en'&&scale===1)await shot('comparison-1440-'+theme+'-en.png','#spec-spine-comparison');
  if(width===390&&theme==='light'&&lang==='en'&&scale===1)await shot('comparison-390-light-en.png','#spec-spine-comparison');
  if(width===390&&theme==='dark'&&lang==='en'&&scale===2)await shot('comparison-390-doubled-type.png','#spec-spine-comparison');
  result.pass=result.checks.every(x=>x.pass);cells.push(result);console.log('CELL',width,scale,theme,lang,result.pass?'PASS':'FAIL',result.checks.filter(x=>!x.pass).map(x=>x.name));
 }
 const report={scope:'R10 reference comparison on exact source; local-file Chrome; external HTTP(S) blocked; doubled type is not native zoom; accessibility-tree semantics are not assistive-technology certification; no live market/data/persistence effects',cells,exceptions};writeFileSync(join(root,'comparison-browser.json'),JSON.stringify(report,null,2));
 console.log('FINAL',cells.length,cells.filter(x=>x.pass).length,'ASSERTIONS',cells.reduce((n,c)=>n+c.checks.length,0),'EXCEPTIONS',exceptions.length);if(cells.some(x=>!x.pass)||exceptions.length)process.exitCode=1;
 ws.send(JSON.stringify({id:++seq,method:'Browser.close',params:{}}));await sleep(700);
}catch(e){writeFileSync(join(root,'comparison-browser-error.txt'),String(e.stack));console.error(e);process.exitCode=1;}
finally{if(ws)ws.close();for(const p of pending.values())clearTimeout(p.timer);pending.clear();if(child.exitCode===null&&child.signalCode===null)child.kill('SIGTERM');await Promise.race([new Promise(r=>child.once('exit',r)),sleep(1800)]);writeFileSync(join(root,'browser-cleanup.json'),JSON.stringify({pid:child.pid,profile,exitCode:child.exitCode,signalCode:child.signalCode,closed:child.exitCode!==null||child.signalCode!==null}));child.stderr.destroy();child.unref();process.exit(process.exitCode||0);}
