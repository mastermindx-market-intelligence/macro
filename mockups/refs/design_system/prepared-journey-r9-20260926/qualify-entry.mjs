import {spawn} from 'node:child_process';
import {mkdtempSync,writeFileSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
const root=process.argv[2], profile=mkdtempSync(join(root,'chrome-profile-'));
const child=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless=new','--no-first-run','--no-default-browser-check','--disable-background-networking','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:['ignore','ignore','pipe']});
let ws,seq=0;const pending=new Map();let session;const exceptions=[];
function send(method,params={},sid=session){return new Promise((resolve,reject)=>{const id=++seq;const timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout '+method));},10000);pending.set(id,{resolve,reject,timer});ws.send(JSON.stringify({id,method,params,...(sid?{sessionId:sid}:{})}));});}
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
async function key(key,code,virtual,modifiers=0){const p={type:'keyDown',key,code,windowsVirtualKeyCode:virtual,modifiers};if(key==='Enter')p.text=p.unmodifiedText='\r';else if(key.length===1)p.text=p.unmodifiedText=key;await send('Input.dispatchKeyEvent',p);await send('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:virtual,modifiers});}

const cells=[];let loads=0;const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const settle=()=>evaluate('document.fonts.ready.then(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))))');
async function until(expression){for(let i=0;i<80;i++){if(await evaluate(expression))return;await sleep(50);}throw new Error('Condition timeout: '+expression);}
async function click(id){const r=await evaluate(`(()=>{const e=document.getElementById(${JSON.stringify(id)});e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()`);await send('Input.dispatchMouseEvent',{type:'mouseMoved',...r});await send('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...r});await send('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...r});await settle();}
async function state(){return evaluate(`(()=>{const t=[...document.querySelectorAll('#specimen-research-tabs [role=tab]')];const panels=t.map(x=>document.getElementById(x.getAttribute('aria-controls')));return {selected:t.filter(x=>x.getAttribute('aria-selected')==='true').map(x=>x.id),visible:panels.filter(x=>!x.hidden&&getComputedStyle(x).display!=='none').map(x=>x.id),entry:t.filter(x=>x.tabIndex===0).map(x=>x.id),focus:document.activeElement.id,hash:location.hash,search:location.search,reciprocal:panels.every((x,i)=>x.getAttribute('aria-labelledby')===t[i].id),tabHeights:t.map(x=>x.getBoundingClientRect().height),tabWidths:t.map(x=>x.getBoundingClientRect().width),documentWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth}})()`);}
function selected(s,tab,panel){return s.selected.length===1&&s.selected[0]===tab&&s.visible.length===1&&s.visible[0]===panel&&s.entry.length===1&&s.entry[0]===tab;}
writeFileSync(join(root,'browser-r9-process.json'),JSON.stringify({pid:child.pid,profile,operation:'design-system-r9-tab-qualification-20260926',source:'integrated'}));
try{
 const endpoint=await new Promise((resolve,reject)=>{let text='';const timer=setTimeout(()=>reject(new Error('Chrome launch timeout')),15000);child.stderr.on('data',b=>{text+=b.toString();const m=text.match(/DevTools listening on (ws:\/\/\S+)/);if(m){clearTimeout(timer);resolve(m[1]);}});child.on('exit',code=>{if(!text.includes('DevTools listening'))reject(new Error('Chrome exited '+code));});});
 ws=new WebSocket(endpoint);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
 ws.onmessage=event=>{const d=JSON.parse(event.data);if(d.id&&pending.has(d.id)){const p=pending.get(d.id);clearTimeout(p.timer);pending.delete(d.id);d.error?p.reject(new Error(JSON.stringify(d.error))):p.resolve(d.result);}else if(d.method==='Runtime.exceptionThrown')exceptions.push(d.params);else if(d.method==='Page.loadEventFired')loads++;};
 const target=await send('Target.createTarget',{url:'about:blank'},null);session=(await send('Target.attachToTarget',{targetId:target.targetId,flatten:true},null)).sessionId;
 await send('Page.enable');await send('Page.bringToFront');await send('Runtime.enable');await send('Network.enable');await send('Network.setBlockedURLs',{urls:['http://*','https://*']});await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});

 const modes=[... [320,390,768,1440].map(width=>({width,scale:1})),{width:390,scale:2}];
 for(const {width,scale} of modes)for(const theme of ['dark','light'])for(const lang of ['en','zh']){
  const result={width,scale,theme,lang,checks:[]};const check=(name,pass,detail)=>result.checks.push({name,pass:!!pass,...(detail===undefined?{}:{detail})});
  const url=pathToFileURL(join(root,'integrated/mockups/design_system/specimen.html')).href+'?market=US&window=5s&case='+cells.length;
  await send('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:false});
  await send('Page.navigate',{url});await until(`location.href===${JSON.stringify(url)}&&document.readyState==='complete'&&!!document.getElementById('specimen-directory')`);
  await evaluate(`(()=>{if((root.getAttribute('data-theme')||'dark')!==${JSON.stringify(theme)})document.getElementById('t-theme').click();if(root.getAttribute('data-lang')!==${JSON.stringify(lang)})document.getElementById('t-lang').click();if(${scale}===2){const styles=getComputedStyle(root);const keys=['display','num-xl','h1','num-lg','h2','md','body','h3','sm','label','micro'];const values=keys.map(k=>parseFloat(styles.getPropertyValue('--fs-'+k))*2);keys.forEach((k,i)=>root.style.setProperty('--fs-'+k,values[i]+'px'));}return true})()`);await settle();await sleep(240);
  const search=await evaluate('location.search');const stored=await evaluate('JSON.stringify([Object.entries(localStorage),Object.entries(sessionStorage)])');
  check('one_title_and_main',await evaluate("document.querySelectorAll('h1').length===1&&document.querySelectorAll('main').length===1"));
  await evaluate("document.querySelector('.spec-skip').focus()");await key('Enter','Enter',13);await settle();
  check('skip_focuses_main',await evaluate("document.activeElement.id==='specimen-main'"));
  if(width===1440&&scale===1&&theme==='dark'&&lang==='en'){
   await evaluate('scrollTo(0,0)');await settle();await sleep(220);const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});writeFileSync(join(root,'entry-desktop-dark.png'),Buffer.from(shot.data,'base64'));
  }
  await evaluate("document.getElementById('tab-fu').click()");
  for(let i=0;i<6;i++){
   const target=await evaluate(`(()=>{const a=document.querySelectorAll('.spec-jump')[${i}];a.focus();return a.hash.slice(1)})()`);await key('Enter','Enter',13);await settle();
   const d=await evaluate(`(()=>{const e=document.getElementById(${JSON.stringify(target)}),r=e.getBoundingClientRect(),b=document.querySelector('.bar').getBoundingClientRect();return {target:e.id,hash:location.hash,focused:document.activeElement===e,top:r.top,headerBottom:b.bottom,height:r.height,visible:r.top>=b.bottom-1&&r.top<innerHeight-20}})()`);
   check('reachable_'+target,d.focused&&d.visible&&d.hash==='#'+target,d);
   check('tab_selection_survives_'+i,await evaluate("document.getElementById('tab-fu').getAttribute('aria-selected')==='true'"));
  }
  await evaluate("document.querySelector('.spec-jump[href=\"#spec-identity\"]').focus()");await key('Enter','Enter',13);await settle();
  const facts=await evaluate(`(()=>{const box=document.getElementById('spec-identity');const rows=[...box.querySelectorAll('tr[data-spec-change]')];return {count:rows.length,up:rows.filter(r=>Number(r.dataset.specChange)>0).length,downOrFlat:rows.filter(r=>Number(r.dataset.specChange)<=0).length,caveatAtRest:!box.querySelector('.spec-caveat').closest('details'),live:!!box.querySelector('.dtp-chip--live'),locale:root.lang,hiddenLanguage:[...box.querySelectorAll('.l-${lang==='en'?'zh':'en'}')].some(x=>getComputedStyle(x).display!=='none')}})()`);
  check('answer_is_honest_and_reconciled',facts.count===11&&facts.up===3&&facts.downOrFlat===8&&facts.caveatAtRest&&!facts.live&&!facts.hiddenLanguage&&facts.locale===(lang==='zh'?'zh-CN':'en'),facts);
  await evaluate("const d=document.getElementById('spec-sector-breakdown');d.open=false;d.querySelector('summary').focus()");await key('Enter','Enter',13);await settle();
  check('opens_complete_breakdown',await evaluate("(()=>{const d=document.getElementById('spec-sector-breakdown');return d.open&&document.activeElement===d.querySelector('summary')&&d.querySelectorAll('tbody tr').length===11&&d.scrollWidth<=d.clientWidth+1})()"));
  if(width===390&&scale===1&&theme==='light'){
   await evaluate("document.getElementById('spec-answer-title').scrollIntoView({block:'start'})");await settle();await sleep(220);const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});writeFileSync(join(root,`answer-phone-${lang}.png`),Buffer.from(shot.data,'base64'));
  }
  await evaluate("document.querySelector('#spec-sector-breakdown .spec-return').focus()");await key('Enter','Enter',13);await settle();
  check('return_keeps_context_and_focus',await evaluate("(()=>{const h=document.getElementById('spec-answer-title');return document.activeElement===h&&document.getElementById('spec-sector-breakdown').open&&h.getBoundingClientRect().top>=document.querySelector('.bar').getBoundingClientRect().bottom-1})()"));
  check('query_and_storage_preserved',search===await evaluate('location.search')&&stored===await evaluate('JSON.stringify([Object.entries(localStorage),Object.entries(sessionStorage)])'));
  check('document_fits',await evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+1'),await evaluate('({scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth})'));
  const ctrl=await evaluate("({links:[...document.querySelectorAll('.spec-jump')].map(x=>x.getBoundingClientRect().height),summary:document.querySelector('#spec-sector-breakdown summary').getBoundingClientRect().height})");check('controls_at_least_44',ctrl.links.every(x=>x>=44)&&ctrl.summary>=44,ctrl);
  await evaluate("document.querySelector('#spec-sector-breakdown summary').focus()");await key(' ','Space',32);await settle();check('close_retains_focus',await evaluate("!document.getElementById('spec-sector-breakdown').open&&document.activeElement===document.querySelector('#spec-sector-breakdown summary')"));
  check('prior_gallery_preserved',await evaluate("document.querySelectorAll('#specimen-state-actions [data-spec-state]').length===8&&document.querySelectorAll('#specimen-state-actions [data-spec-save]').length===5"));
  result.pass=result.checks.every(x=>x.pass);cells.push(result);console.log('CELL',width,scale,theme,lang,result.pass?'PASS':'FAIL',result.checks.filter(x=>!x.pass).map(x=>x.name));
 }
 const report={scope:'R9 same-file reference entry and inspect-return; current-source composition; 2x cases double the type ramp, not a claimed native zoom or assistive-technology test; isolated Chrome, external HTTP(S) blocked',cells,exceptions};
 writeFileSync(join(root,'browser-journey.json'),JSON.stringify(report,null,2));console.log('FINAL',cells.length,cells.filter(x=>x.pass).length,'ASSERTIONS',cells.reduce((a,c)=>a+c.checks.length,0),'EXCEPTIONS',exceptions.length);
 if(cells.some(x=>!x.pass)||exceptions.length)process.exitCode=1;
 ws.send(JSON.stringify({id:++seq,method:'Browser.close',params:{}}));await sleep(400);
}catch(e){writeFileSync(join(root,'browser-journey-error.txt'),String(e.stack));console.error(e);process.exitCode=1;}
finally{
 if(ws)ws.close();for(const p of pending.values())clearTimeout(p.timer);pending.clear();
 if(child.exitCode===null&&child.signalCode===null)child.kill('SIGTERM');
 await Promise.race([new Promise(r=>child.once('exit',r)),sleep(1800)]);
 writeFileSync(join(root,'browser-journey-cleanup.json'),JSON.stringify({pid:child.pid,profile,exitCode:child.exitCode,signalCode:child.signalCode,closed:child.exitCode!==null||child.signalCode!==null}));child.stderr.destroy();child.unref();process.exit(process.exitCode||0);
}
