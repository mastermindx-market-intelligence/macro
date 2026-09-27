import {spawn} from 'node:child_process';
import {mkdtempSync,writeFileSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
const root=process.argv[2], profile=mkdtempSync(join(root,'chrome-profile-'));
const child=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless=new','--no-first-run','--no-default-browser-check','--disable-background-networking','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:['ignore','ignore','pipe']});
let ws,seq=0;const pending=new Map();let session;const exceptions=[];
function send(method,params={},sid=session){return new Promise((resolve,reject)=>{const id=++seq;const timer=setTimeout(()=>{pending.delete(id);reject(new Error('CDP timeout '+method));},10000);pending.set(id,{resolve,reject,timer});ws.send(JSON.stringify({id,method,params,...(sid?{sessionId:sid}:{})}));});}
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
async function key(key,code,virtual){await send('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode:virtual,text:key==='Enter'?'\r':key,unmodifiedText:key==='Enter'?'\r':key});await send('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:virtual});}
const cells=[];
writeFileSync(join(root,'browser-final-process.json'),JSON.stringify({pid:child.pid,profile,source:'integrated',operation:'design-system-r7-state-pattern-qualification-20260926'}));
try {
 const endpoint=await new Promise((resolve,reject)=>{let text='';const timer=setTimeout(()=>reject(new Error('Chrome launch timeout')),15000);child.stderr.on('data',b=>{text+=b.toString();const m=text.match(/DevTools listening on (ws:\/\/\S+)/);if(m){clearTimeout(timer);resolve(m[1]);}});child.on('exit',code=>{if(!text.includes('DevTools listening'))reject(new Error('Chrome exited '+code));});});
 ws=new WebSocket(endpoint);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
 ws.onmessage=event=>{const d=JSON.parse(event.data);if(d.id&&pending.has(d.id)){const p=pending.get(d.id);clearTimeout(p.timer);pending.delete(d.id);d.error?p.reject(new Error(JSON.stringify(d.error))):p.resolve(d.result);}else if(d.method==='Runtime.exceptionThrown')exceptions.push(d.params);};
 const target=await send('Target.createTarget',{url:'about:blank'},null);session=(await send('Target.attachToTarget',{targetId:target.targetId,flatten:true},null)).sessionId;
 await send('Page.enable');await send('Page.bringToFront');await send('Runtime.enable');await send('Network.enable');await send('Network.setBlockedURLs',{urls:['http://*','https://*']});await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
 await send('Page.navigate',{url:pathToFileURL(join(root,'integrated/mockups/design_system/specimen.html')).href});
 for(let i=0;i<50;i++){if(await evaluate('document.readyState==="complete" && !!document.querySelector(".mx-disc summary")'))break;await new Promise(r=>setTimeout(r,100));}

 for(const width of [320,360,390,768,1440])for(const theme of ['dark','light'])for(const lang of ['en','zh']){
  await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});
  await evaluate(`(()=>{const r=document.documentElement;if((r.getAttribute('data-theme')||'dark')!==${JSON.stringify(theme)})document.querySelector('#t-theme').click();if(r.getAttribute('data-lang')!==${JSON.stringify(lang)})document.querySelector('#t-lang').click();document.querySelectorAll('#specimen-state-actions details').forEach(d=>d.open=false);return true})()`);
  await evaluate("document.fonts.ready.then(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))))");
  const result=await evaluate(`(()=>{const box=document.querySelector('#specimen-state-actions');const cs=[...box.querySelectorAll('article')];const d=document.documentElement;return {viewport:${width},clientWidth:d.clientWidth,documentWidth:d.scrollWidth,theme:d.getAttribute('data-theme')||'dark',locale:d.getAttribute('data-lang'),documentLanguage:d.lang,stateCount:box.querySelectorAll('[data-spec-state]').length,saveCount:box.querySelectorAll('[data-spec-save]').length,buttonsDisabled:[...box.querySelectorAll('button')].every(b=>b.disabled&&b.type==='button'),caseOverflow:cs.filter(x=>x.scrollWidth>x.clientWidth+1).map(x=>x.dataset.specState||x.dataset.specSave),languageLeak:[...box.querySelectorAll('.l-${lang==='en'?'zh':'en'}')].some(e=>getComputedStyle(e).display!=='none'),summaries:box.querySelectorAll('summary').length,partialAtRest:box.querySelector('[data-spec-state="partial"] > p').getBoundingClientRect().height>0,unknownText:box.querySelector('[data-spec-save="unknown"] button').innerText,href:location.href,storageCount:localStorage.length};})()`);
  result.inspections=[];
  for(let i=0;i<result.summaries;i++){
   await evaluate(`(()=>{const s=document.querySelectorAll('#specimen-state-actions summary')[${i}];s.parentElement.open=false;s.scrollIntoView({block:'center'});s.focus();return true})()`);
   await key('Enter','Enter',13);await evaluate('new Promise(r=>requestAnimationFrame(r))');
   const opened=await evaluate(`(()=>{const s=document.querySelectorAll('#specimen-state-actions summary')[${i}];return {name:s.dataset.specInspect,open:s.parentElement.open,focus:document.activeElement===s,overflow:s.parentElement.scrollWidth>s.parentElement.clientWidth+1}})()`);
   await key(' ','Space',32);await evaluate('new Promise(r=>requestAnimationFrame(r))');
   opened.closed=await evaluate(`(()=>{const s=document.querySelectorAll('#specimen-state-actions summary')[${i}];return !s.parentElement.open&&document.activeElement===s})()`);result.inspections.push(opened);
  }
  const noEffect=await evaluate("(()=>{const before=location.href,stored=localStorage.length;document.querySelectorAll('#specimen-state-actions button').forEach(b=>b.click());return before===location.href&&stored===localStorage.length})()");
  result.noFictionalAction=noEffect;
  result.pass=result.documentWidth<=result.clientWidth+1&&result.theme===theme&&result.locale===lang&&result.documentLanguage===(lang==='zh'?'zh-CN':'en')&&result.stateCount===8&&result.saveCount===5&&result.buttonsDisabled&&!result.caseOverflow.length&&!result.languageLeak&&result.partialAtRest&&result.summaries===7&&result.inspections.every(x=>x.open&&x.focus&&!x.overflow&&x.closed)&&noEffect;
  cells.push(result);console.log('CELL',width,theme,lang,result.pass?'PASS':'FAIL');
  if(width===1440&&theme==='dark'&&lang==='en'){
   await evaluate("document.querySelector('#specimen-state-actions').scrollIntoView({block:'start'});scrollBy(0,-65)");
   const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});writeFileSync(join(root,'state-gallery-desktop-dark.png'),Buffer.from(shot.data,'base64'));
   await evaluate("document.querySelector('#specimen-state-actions .spec-outcome-title').scrollIntoView({block:'start'});scrollBy(0,-65)");
   const actions=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});writeFileSync(join(root,'action-outcomes-desktop-dark.png'),Buffer.from(actions.data,'base64'));
  }
  if(width===390&&theme==='light'&&lang==='zh'){
   await evaluate("document.querySelector('#specimen-state-actions').scrollIntoView({block:'start'});scrollBy(0,-125)");
   const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});writeFileSync(join(root,'recovery-mobile-light-zh.png'),Buffer.from(shot.data,'base64'));
  }
  if(width===390&&theme==='light'&&lang==='en'){
   await evaluate("const s=document.querySelector('[data-spec-save=unknown] summary');s.parentElement.open=true;s.scrollIntoView({block:'center'});s.focus()");
   const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});writeFileSync(join(root,'save-unknown-mobile-light-en.png'),Buffer.from(shot.data,'base64'));
  }
 }
 if(cells.some(x=>!x.pass)||exceptions.length)process.exitCode=1;
 writeFileSync(join(root,'browser-r7-final.json'),JSON.stringify({scope:'R7 additions on current-main integrated specimen; local file transport; external HTTP(S) blocked; static action examples have no persistence service; keyboard details are real; no production or human-comprehension claim',cells,exceptions},null,2));
 console.log('FINAL',cells.length,cells.filter(x=>x.pass).length,'EXCEPTIONS',exceptions.length);
 ws.send(JSON.stringify({id:++seq,method:'Browser.close',params:{}}));await new Promise(r=>setTimeout(r,500));
} catch(e){writeFileSync(join(root,'browser-r7-error.txt'),String(e.stack));console.error(e);process.exitCode=1;}
finally {
 if(ws)ws.close();for(const p of pending.values())clearTimeout(p.timer);pending.clear();
 if(child.exitCode===null&&child.signalCode===null)child.kill('SIGTERM');
 await Promise.race([new Promise(r=>child.once('exit',r)),new Promise(r=>setTimeout(r,1800))]);
 writeFileSync(join(root,'browser-r7-cleanup.json'),JSON.stringify({pid:child.pid,exitCode:child.exitCode,signalCode:child.signalCode,profile,closed:child.exitCode!==null||child.signalCode!==null}));
 child.stderr.destroy();child.unref();process.exit(process.exitCode||0);
}
