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
writeFileSync(join(root,'browser-final-process.json'),JSON.stringify({pid:child.pid,profile,source:'candidate-source',operation:'design-system-r6-mobile-qualification-20260926'}));
try {
 const endpoint=await new Promise((resolve,reject)=>{let text='';const timer=setTimeout(()=>reject(new Error('Chrome launch timeout')),15000);child.stderr.on('data',b=>{text+=b.toString();const m=text.match(/DevTools listening on (ws:\/\/\S+)/);if(m){clearTimeout(timer);resolve(m[1]);}});child.on('exit',code=>{if(!text.includes('DevTools listening'))reject(new Error('Chrome exited '+code));});});
 ws=new WebSocket(endpoint);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
 ws.onmessage=event=>{const d=JSON.parse(event.data);if(d.id&&pending.has(d.id)){const p=pending.get(d.id);clearTimeout(p.timer);pending.delete(d.id);d.error?p.reject(new Error(JSON.stringify(d.error))):p.resolve(d.result);}else if(d.method==='Runtime.exceptionThrown')exceptions.push(d.params);};
 const target=await send('Target.createTarget',{url:'about:blank'},null);session=(await send('Target.attachToTarget',{targetId:target.targetId,flatten:true},null)).sessionId;
 await send('Page.enable');await send('Page.bringToFront');await send('Runtime.enable');await send('Network.enable');await send('Network.setBlockedURLs',{urls:['http://*','https://*']});await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
 await send('Page.navigate',{url:pathToFileURL(join(root,'candidate-source/mockups/design_system/specimen.html')).href});
 for(let i=0;i<50;i++){if(await evaluate('document.readyState==="complete" && !!document.querySelector(".mx-disc summary")'))break;await new Promise(r=>setTimeout(r,100));}
 for(const width of [320,360,390,768,1440])for(const theme of ['dark','light'])for(const lang of ['en','zh']){
  await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});
  await evaluate(`(()=>{const r=document.documentElement;if((r.getAttribute('data-theme')||'dark')!==${JSON.stringify(theme)})document.querySelector('#t-theme').click();if(r.getAttribute('data-lang')!==${JSON.stringify(lang)})document.querySelector('#t-lang').click();document.querySelector('.mx-disc').open=false;document.querySelector('.mx-disc summary').focus();return true;})()`);
  await evaluate("document.fonts.ready.then(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))))");
  await key('Enter','Enter',13);await evaluate("new Promise(r=>requestAnimationFrame(r))");
  const report=await evaluate(`(()=>{const d=document.querySelector('.mx-disc');const tables=[...document.querySelectorAll('.mx-tblbox')].map(e=>{e.scrollLeft=e.scrollWidth;return {width:e.clientWidth,content:e.scrollWidth,reachedEnd:Math.abs(e.scrollLeft-(e.scrollWidth-e.clientWidth))<=1};});const l=document.querySelector('.mx-ladder');const last=l.querySelector('button:last-child');last.focus();const r=last.getBoundingClientRect(),lr=l.getBoundingClientRect();const offending=[...document.querySelectorAll('body *')].filter(e=>{if(!(e.offsetWidth||e.offsetHeight))return false;let p=e.parentElement;while(p&&p!==document.body){if(['auto','scroll','hidden','clip'].includes(getComputedStyle(p).overflowX))return false;p=p.parentElement;}return e.getBoundingClientRect().right>innerWidth+1;}).map(e=>({tag:e.tagName,cls:e.className?.baseVal??e.className,text:(e.innerText||'').slice(0,65),right:e.getBoundingClientRect().right}));d.querySelector('summary').focus();return{viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth,theme:document.documentElement.getAttribute('data-theme')||'dark',locale:document.documentElement.getAttribute('data-lang'),documentLanguage:document.documentElement.lang,open:d.open,focus:document.activeElement===d.querySelector('summary'),disclosureOverflow:d.scrollWidth>d.clientWidth+1,tables,lastLadderVisible:r.right<=lr.right+1&&r.left>=lr.left-1,offending,displayFont:getComputedStyle(document.querySelector('.trow > span')).fontSize};})()`);
  await key(' ','Space',32);await evaluate("new Promise(r=>requestAnimationFrame(r))");report.closed=await evaluate("!document.querySelector('.mx-disc').open && document.activeElement===document.querySelector('.mx-disc summary')");
  report.pass=report.documentWidth<=report.clientWidth+1&&report.theme===theme&&report.locale===lang&&report.documentLanguage===(lang==='zh'?'zh-CN':'en')&&report.open&&report.focus&&!report.disclosureOverflow&&report.closed&&report.tables.every(x=>x.reachedEnd)&&report.lastLadderVisible&&!report.offending.length;
  cells.push(report);console.log(JSON.stringify(report));
  if(width===390&&theme==='light'&&lang==='en'){
   await evaluate("document.querySelector('.trow').scrollIntoView({block:'center'})");const p=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});writeFileSync(join(root,'type-reflow-390-light-en.png'),Buffer.from(p.data,'base64'));
  }
  if(width===390&&theme==='light'&&lang==='zh'){
   await evaluate("document.querySelector('.mx-disc').open=true;document.querySelector('.mx-disc summary').scrollIntoView({block:'center'});document.querySelector('.mx-disc summary').focus()");const p=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});writeFileSync(join(root,'disclosure-fixed-390-light-zh.png'),Buffer.from(p.data,'base64'));
  }
 }
 if(cells.some(x=>!x.pass))process.exitCode=1;
 writeFileSync(join(root,'browser-mobile-final.json'),JSON.stringify({scope:'candidate specimen source; local file transport; external http(s) blocked; actual keyboard activation; bind source hashes separately; not production/assistive-tech proof',cells,exceptions},null,2));
 console.log('QUALIFICATION_CAPTURED',cells.length,'exceptions',exceptions.length);
 ws.send(JSON.stringify({id:++seq,method:'Browser.close',params:{}}));await new Promise(r=>setTimeout(r,500));
} catch(e){writeFileSync(join(root,'browser-final-error.txt'),String(e.stack));console.error(e);process.exitCode=1;}
finally {
 if(ws)ws.close();for(const p of pending.values()){clearTimeout(p.timer);}pending.clear();
 if(child.exitCode===null&&child.signalCode===null)child.kill('SIGTERM');
 await Promise.race([new Promise(r=>child.once('exit',r)),new Promise(r=>setTimeout(r,1800))]);
 writeFileSync(join(root,'browser-final-cleanup.json'),JSON.stringify({pid:child.pid,exitCode:child.exitCode,signalCode:child.signalCode,profile,closed:child.exitCode!==null||child.signalCode!==null}));
 child.stderr.destroy();child.unref();process.exit(process.exitCode||0);
}
