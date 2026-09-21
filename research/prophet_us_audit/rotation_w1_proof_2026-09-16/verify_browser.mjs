// Isolated browser; only this operation's loopback proof app. No provider session.
import {spawn} from 'node:child_process';
import {mkdtemp,writeFile,mkdir,readFile} from 'node:fs/promises';
import {setTimeout as delay} from 'node:timers/promises';
import {createHash} from 'node:crypto';
const root=new URL('.',import.meta.url).pathname;
const out=root+'.rotation-browser-r5'; await mkdir(out,{recursive:true});
const profile=await mkdtemp(out+'/profile-');
const child=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',[
 '--headless','--no-first-run','--disable-background-networking',
 '--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:['ignore','ignore','pipe']});
let socket, buffer=''; const events=[]; const results=[];
try {
 const endpoint=await new Promise((resolve,reject)=>{
  const timer=setTimeout(()=>reject(Error('browser startup timeout')),15000);
  child.stderr.on('data',data=>{buffer+=data;const m=buffer.match(/DevTools listening on (ws:\/\/127\.0\.0\.1:[^\s]+)/);if(m){clearTimeout(timer);resolve(m[1]);}});
  child.on('exit',code=>reject(Error('browser exited '+code)));
 });
 socket=new WebSocket(endpoint); await new Promise((r,j)=>{socket.onopen=r;socket.onerror=j;});
 let seq=0;const pending=new Map();
 socket.onmessage=event=>{const msg=JSON.parse(event.data);const p=pending.get(msg.id);if(p){pending.delete(msg.id);clearTimeout(p.timer);msg.error?p.reject(Error(JSON.stringify(msg.error))):p.resolve(msg.result);}else if(msg.method==='Runtime.exceptionThrown')events.push(msg.params);};
 const call=(method,params={},sessionId)=>new Promise((resolve,reject)=>{
  const id=++seq,timer=setTimeout(()=>{pending.delete(id);reject(Error(method+' timeout'));},20000);
  pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params,...(sessionId?{sessionId}:{})}));
 });
 const target=await call('Target.createTarget',{url:'about:blank'});
 const attached=await call('Target.attachToTarget',{targetId:target.targetId,flatten:true});
 const run=(method,params={})=>call(method,params,attached.sessionId);
 await run('Page.enable'); await run('Runtime.enable');
 const evaluate=async expression=>{const r=await run('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 await run('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 await run('Page.navigate',{url:'http://127.0.0.1:18787/'});
 let ready=false;for(let i=0;i<40;i++){await delay(500);ready=await evaluate("typeof go === 'function' && document.querySelector('#sidenav').childElementCount > 0");if(ready)break;}
 if(!ready)throw Error('existing navigation not ready');
 const nav=await evaluate("Array.from(document.querySelectorAll('#sidenav *')).filter(e=>/^Prophet$/.test(e.textContent.trim())).map(e=>({tag:e.tagName,text:e.textContent.trim(),disabled:e.disabled===true}))");
 if(nav.length===0)throw Error('Prophet control absent: '+JSON.stringify(await evaluate("document.querySelector('#sidenav').innerText.slice(0,1500)")));
 await evaluate("Array.from(document.querySelectorAll('#sidenav *')).find(e=>/^Prophet$/.test(e.textContent.trim())).click()");
 for(let i=0;i<40;i++){await delay(500);ready=await evaluate("document.querySelector('#view').innerText.includes('Rotation diagnostics')");if(ready)break;}
 if(!ready)throw Error('real Prophet renderer did not expose diagnostics');
 const source=await evaluate("fetch('/api/prophet').then(r=>r.json()).then(p=>p.rotation_diagnostics)");
 const probe=()=>evaluate(`(()=>{const v=document.querySelector('#view');const text=v.innerText;const heading=Array.from(v.querySelectorAll('.section')).find(e=>e.textContent.trim()==='Rotation diagnostics');const r=heading.getBoundingClientRect();return {language:document.documentElement.lang,theme:document.documentElement.dataset.theme,width:innerWidth,documentWidth:document.documentElement.scrollWidth,heading:{x:r.x,y:r.y,width:r.width,height:r.height},energy:text.includes('energy_complex')&&text.includes('DINO, VLO'),control:text.includes('AI Infrastructure'),mixedDates:text.includes('Input dates differ'),conversion:text.includes('21 matched / 124 sighted'),notMeasured:text.includes('Not measured'),textHasDoubleEscape:/&amp;|&lt;|&#39;/.test(text),hashClipped:Array.from(v.querySelectorAll('.note')).filter(e=>e.textContent.startsWith('Source SHA:')).some(e=>e.scrollWidth>e.clientWidth+1),tableScrollHint:text.includes('scroll the table to see counts and visibility')}})()`);
 for(const width of [1440,390]){
  await run('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:width<500});
  await evaluate("Array.from(document.querySelectorAll('#view .section')).find(e=>e.textContent.trim()==='Rotation diagnostics').scrollIntoView({block:'start'})");await delay(150);
  const fact=await probe();results.push({kind:'real_endpoint_existing_navigation',...fact});
  const shot=await run('Page.captureScreenshot',{format:'png'});await writeFile(out+'/real-'+width+'.png',Buffer.from(shot.data,'base64'));
 }
 const scenarios=[
  ['source_unavailable',{...source,available:false,status:'unavailable',reasons:['source_missing']},'Source unavailable'],
  ['withheld',{...source,baskets:[],status:'partial',reasons:['basket_source_unavailable']},'Basket evidence unavailable'],
  ['malformed',null,'Rotation diagnostics unavailable'],
  ['empty',{...source,baskets:[],reasons:[]},'No baskets in audit.'],
 ];
 for(const [name,payload,expected] of scenarios){
  await evaluate(`document.querySelector('#view').innerHTML=prophetRotationDiagnosticsHtml(${JSON.stringify(payload)})`);
  const fact=await evaluate("({text:document.querySelector('#view').innerText,width:innerWidth,documentWidth:document.documentElement.scrollWidth})");
  if(!fact.text.includes(expected))throw Error('degraded renderer mismatch '+name);
  if(name==='withheld'&&fact.text.includes('No baskets in audit'))throw Error('withheld falsely empty');
  results.push({kind:'synthetic_browser_failure',name,expected,width:fact.width,documentWidth:fact.documentWidth});
  if(name==='withheld'){const shot=await run('Page.captureScreenshot',{format:'png'});await writeFile(out+'/withheld-390.png',Buffer.from(shot.data,'base64'));}
 }
 const receipt={scope:'local browser only; existing dark/English admin. Synthetic failures separately labeled.',
  source_sha256:source.source.sha256,observed:results,exceptions:events,
  interaction:{method:'semantic DOM click',body_character_keystrokes:0,tab_discovery:0,isolated_profile:true}};
 await writeFile(out+'/receipt.json',JSON.stringify(receipt,null,2));
 console.log(JSON.stringify(receipt,null,2));
 if(results.slice(0,2).some(r=>!r.energy||!r.control||!r.mixedDates||!r.conversion||!r.notMeasured||r.textHasDoubleEscape||r.hashClipped||!r.tableScrollHint))throw Error('real page assertion failed');
 if(events.length)throw Error('browser exceptions observed');
} finally {
 if(socket&&socket.readyState===1)socket.close();
 child.kill('SIGTERM');
 await Promise.race([new Promise(resolve=>child.once('exit',resolve)),delay(3000)]);
 if(child.exitCode===null&&child.signalCode===null)child.kill('SIGKILL');
}
